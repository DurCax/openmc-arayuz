# -*- coding: utf-8 -*-
"""
kapsul.py -- tekrarlanabilirlik kapsulu (Dalga S-4, Y2; Ek oneri M4).

Her kosu dizinine spec.json'un yanina `kapsul.json` yazilir:
  spec        spec.json'un BAYT sha256'si (kosuda kullanilan model)
  uygulama    surum, git commit, commit edilmemis degisiklik
  openmc      surum + calistirilabilir yolu
  kutuphane   cross_sections.xml (yol + sha256) + dizin ozeti (dosya sayisi,
              toplam boyut, en yeni mtime) -- 13 GB'lik h5'ler karmalanmaz
  zincir      tukenme zinciri (yol + sha256; BUYUK_DOSYA_SINIRI ustunde yalniz
              boyut + mtime); tukenme kapaliysa None
  tohum       etkin tohum (spec'te yoksa OpenMC varsayilani 1)
  is_parcacigi, python, platform
  ortam       `conda list --export` karmasi (yoksa `pip freeze`)

  openmc-arayuz-kosu yeniden <kosu_dizini> [--hedef DIZIN] [--kuru] [-s N]
    kapsuldeki spec'i dogrular (karma), bugunku ortamla farki listeler,
    --kuru degilse ayni spec + tohum + is parcacigiyla HEDEF dizinde kosar ve
    k-eff farkini raporlar. Kaynak kosu dizinine yazmaz.

Kapsul bir kanittir, bir garanti degildir: ayni ortam + ayni tohum OpenMC'de
ayni sonucu verir; farkli ortamda fark beklenir ve listelenir.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

KAPSUL_ADI = "kapsul.json"
KAPSUL_SURUMU = 1
SPEC_ADI = "spec.json"
BUYUK_DOSYA_SINIRI = 64 * 1024 * 1024     # bayt; ustunde yalniz boyut + mtime
OPENMC_VARSAYILAN_TOHUM = 1               # openmc.Settings.seed varsayilani
_KOMUT_SURESI = 60.0                      # s; conda list ~2 s (olculdu 01.10.2026)
_YOK_SAYILAN = ("olusturma",)             # farklar(): her kapsulde farkli
_YUVARLAMA_TOLERANSI = 1e-9               # goreli; k-eff "ayni" esigi

_SHA_ONBELLEK = {}
_ORTAM_ONBELLEK = {}


class KapsulHatasi(Exception):
    """Kapsul yok, okunamiyor ya da spec ile tutarsiz."""


# ============================================================================
# KIMLIKLER
# ============================================================================

def _sha256(yol):
    bilgi = os.stat(yol)
    anahtar = (os.path.abspath(yol), bilgi.st_size, bilgi.st_mtime)
    if anahtar not in _SHA_ONBELLEK:
        h = hashlib.sha256()
        with open(yol, "rb") as f:
            for parca in iter(lambda: f.read(1 << 20), b""):
                h.update(parca)
        _SHA_ONBELLEK[anahtar] = h.hexdigest()
    return _SHA_ONBELLEK[anahtar]


def dosya_kimligi(yol, sinir=BUYUK_DOSYA_SINIRI):
    """{"yol", "boyut", "mtime", "sha256", "karma_yontemi"} ya da
    {"yol", "durum": "yok"}. sinir'dan buyuk dosyada sha256 None'dir."""
    yol = os.path.abspath(os.path.expanduser(yol))
    try:
        bilgi = os.stat(yol)
        buyuk = bilgi.st_size > sinir
        sha = None if buyuk else _sha256(yol)
    except OSError as e:
        _log.info("kapsül: dosya okunamadı: %s (%s)", yol, e)
        return {"yol": yol, "durum": "yok"}
    return {"yol": yol, "boyut": bilgi.st_size, "mtime": bilgi.st_mtime, "sha256": sha,
            "karma_yontemi": "boyut+mtime" if buyuk else "tam"}


def _dizin_ozeti(dizin):
    sayi, toplam, en_yeni = 0, 0, 0.0
    for kok, _alt, dosyalar in os.walk(dizin):
        for ad in dosyalar:
            try:
                b = os.stat(os.path.join(kok, ad))
            except OSError as e:
                _log.info("kapsül: kütüphane dosyası okunamadı: %s (%s)", ad, e)
                continue
            sayi, toplam, en_yeni = sayi + 1, toplam + b.st_size, max(en_yeni, b.st_mtime)
    return {"dosya_sayisi": sayi, "toplam_boyut": toplam, "en_yeni_mtime": en_yeni}


def kutuphane_kimligi(xs_yolu=None):
    """Tesir kesiti kutuphanesi: cross_sections.xml tam karmasi + dizin ozeti."""
    if xs_yolu is None:
        from cekirdek import veri_yolu
        xs_yolu = veri_yolu.cross_sections().deger
    if not xs_yolu or not os.path.isfile(xs_yolu):
        return {"durum": "yok", "cross_sections": xs_yolu or None}
    dizin = os.path.dirname(os.path.abspath(xs_yolu))
    return dict({"cross_sections": dosya_kimligi(xs_yolu), "dizin": dizin},
                **_dizin_ozeti(dizin))


def zincir_kimligi(spec):
    """Tukenme aciksa secilen zincirin kimligi, degilse None."""
    if not (spec.get("tukenme") or {}).get("var"):
        return None
    from cekirdek import tukenme
    return dosya_kimligi(tukenme.zincir_secimi(spec)["yol"])


def _varsayilan_adaylar():
    adaylar = []
    conda = os.environ.get("CONDA_EXE") or shutil.which("conda")
    if conda:
        onek = os.environ.get("CONDA_PREFIX") or sys.prefix
        adaylar.append(("conda list --export", [conda, "list", "--export", "-p", onek]))
    adaylar.append(("pip freeze", [sys.executable, "-m", "pip", "freeze"]))
    return adaylar


def ortam_kilidi_hesapla(adaylar):
    """Ilk calisan komutun ciktisinin karmasi: {"yontem", "sha256",
    "satir_sayisi"}; hicbiri calismazsa yontem/sha256 None + "neden"."""
    nedenler = []
    for ad, komut in adaylar:
        try:
            cikti = subprocess.run(komut, capture_output=True, text=True,
                                   timeout=_KOMUT_SURESI, check=True).stdout
        except (OSError, subprocess.SubprocessError) as e:
            _log.info("kapsül: ortam kilidi komutu çalışmadı (%s): %s", ad, e)
            nedenler.append("%s: %s" % (ad, e))
            continue
        satirlar = [s.rstrip() for s in cikti.splitlines() if s.strip()]
        metin = "".join(s + "\n" for s in satirlar)
        return {"yontem": ad, "sha256": hashlib.sha256(metin.encode("utf-8")).hexdigest(),
                "satir_sayisi": sum(1 for s in satirlar if not s.startswith("#"))}
    _log.warning("kapsül: ortam kilidi alınamadı: %s", "; ".join(nedenler))
    return {"yontem": None, "sha256": None, "satir_sayisi": 0, "neden": "; ".join(nedenler)}


def ortam_kilidi():
    """Surec basina onbellekli ortam kilidi; conda ortami degisince
    (conda-meta/history) yeniden hesaplanir."""
    onek = os.environ.get("CONDA_PREFIX") or sys.prefix
    tarih = os.path.join(onek, "conda-meta", "history")
    anahtar = (onek, os.path.getmtime(tarih) if os.path.exists(tarih) else None)
    if anahtar not in _ORTAM_ONBELLEK:
        _ORTAM_ONBELLEK[anahtar] = ortam_kilidi_hesapla(_varsayilan_adaylar())
    return dict(_ORTAM_ONBELLEK[anahtar])


def _openmc_kimligi():
    try:
        import openmc
        surum = openmc.__version__
    except ImportError as e:
        _log.warning("kapsül: openmc içe aktarılamadı: %s", e)
        surum = None
    return {"surum": surum, "calistirilabilir": shutil.which("openmc")}


# ============================================================================
# OLUSTUR / YAZ / OKU
# ============================================================================

def olustur(spec, spec_yolu, is_parcacigi=None):
    """Bugunku ortamin kapsulu (YENI sozluk; spec degismez)."""
    from cekirdek import surum
    d = surum.derleme_bilgisi()
    tohum = (spec.get("ayarlar") or {}).get("tohum")
    n = is_parcacigi or (spec.get("calistirma") or {}).get("is_parcacigi")
    return {
        "kapsul_surumu": KAPSUL_SURUMU,
        "olusturma": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "spec": {"dosya": os.path.basename(spec_yolu), "sha256": _sha256(spec_yolu)},
        "uygulama": {"ad": d["uygulama"], "surum": d["surum"], "git_commit": d["git_commit"],
                     "git_degisiklik": d["git_degisiklik"]},
        "python": d["python"],
        "platform": d["platform"],
        "openmc": _openmc_kimligi(),
        "kutuphane": kutuphane_kimligi(),
        "zincir": zincir_kimligi(spec),
        "tohum": int(tohum) if tohum else OPENMC_VARSAYILAN_TOHUM,
        "tohum_kaynagi": "spec" if tohum else "openmc_varsayilani",
        "is_parcacigi": int(n) if n else None,
        "ortam": ortam_kilidi(),
    }


def yaz(dizin, spec, is_parcacigi=None):
    """dizin/kapsul.json'u yazar (spec.json ZATEN yazilmis olmali). Yazilamazsa
    uyari loglanir ve None doner -- kosu kapsul yuzunden durmaz."""
    yol = os.path.join(dizin, KAPSUL_ADI)
    try:
        veri = olustur(spec, os.path.join(dizin, SPEC_ADI), is_parcacigi)
        gecici = yol + ".yaziliyor"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(gecici, yol)
    except OSError as e:
        _log.warning("kapsül yazılamadı: %s (%s)", yol, e)
        return None
    return yol


def oku(dizin):
    yol = os.path.join(dizin, KAPSUL_ADI)
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise KapsulHatasi(_("%s bulunamadı: %s") % (KAPSUL_ADI, dizin)) from None
    except (OSError, ValueError) as e:
        raise KapsulHatasi(_("%s okunamadı: %s") % (yol, e)) from e


def spec_eslesiyor(dizin, kapsul):
    """Kosu dizinindeki spec.json kapsuldeki karmayla ayni mi."""
    yol = os.path.join(dizin, kapsul["spec"]["dosya"])
    try:
        return _sha256(yol) == kapsul["spec"]["sha256"]
    except OSError as e:
        _log.info("kapsül: spec okunamadı: %s (%s)", yol, e)
        return False


def ozet_metni(dizin):
    """Rapor tekrarlanabilirlik satiri; kapsul yoksa None."""
    if not dizin or not os.path.exists(os.path.join(dizin, KAPSUL_ADI)):
        return None
    try:
        k = oku(dizin)
    except KapsulHatasi as e:
        _log.warning("rapor: %s", e)
        return str(e)
    durum = _("eşleşiyor") if spec_eslesiyor(dizin, k) else _("EŞLEŞMİYOR")
    ortam = k.get("ortam") or {}
    ortam_metni = ("%s sha256 %s" % (ortam["yontem"], ortam["sha256"][:12])
                   if ortam.get("sha256") else _("ortam kilidi yok"))
    return _("%s (%s); spec sha256 %s… %s; %s") % (
        KAPSUL_ADI, k.get("olusturma"), k["spec"]["sha256"][:12], durum, ortam_metni)


# ============================================================================
# KARSILASTIRMA
# ============================================================================

def _duz(d, onek=""):
    sonuc = {}
    for anahtar, deger in d.items():
        ad = onek + anahtar
        if isinstance(deger, dict):
            sonuc.update(_duz(deger, ad + "."))
        else:
            sonuc[ad] = deger
    return sonuc


def farklar(eski, yeni, yok_say=_YOK_SAYILAN):
    """[(alan, eski, yeni)] -- duzlestirilmis alanlarda farkli olanlar."""
    a, b = _duz(eski), _duz(yeni)
    return [(alan, a.get(alan), b.get(alan)) for alan in sorted(set(a) | set(b))
            if not alan.startswith(yok_say) and a.get(alan) != b.get(alan)]


# ============================================================================
# YENIDEN URET (openmc-arayuz-kosu yeniden)
# ============================================================================

def _argumanlar(argv):
    p = argparse.ArgumentParser(
        prog="openmc-arayuz-kosu yeniden",
        description=_("Bir koşuyu kapsüldeki spec, tohum ve iş parçacığıyla yeniden üretir."))
    p.add_argument("kosu_dizini")
    p.add_argument("--hedef", help=_("yeni koşu dizini (varsayılan <koşu_dizini>_yeniden)"))
    p.add_argument("--kuru", action="store_true",
                   help=_("koşmadan planı ve ortam farkını göster (dry-run)"))
    p.add_argument("-s", "--is-parcacigi", type=int, default=None)
    return p.parse_args(argv)


def _keff(dizin):
    from cekirdek import kosucu
    sp = kosucu.son_statepoint(dizin)
    return kosucu.sonuc_oku(sp).get("keff") if sp else None


def _k_farki_satiri(eski, yeni):
    if not eski or not yeni:
        return _("k-eff karşılaştırılamadı (özdeğer koşusu değil ya da statepoint yok)")
    if tuple(eski) == tuple(yeni):
        return _("k-eff birebir aynı: %.6f ± %.6f") % tuple(yeni)
    fark = yeni[0] - eski[0]
    if abs(fark) <= _YUVARLAMA_TOLERANSI * abs(eski[0]):
        # OpenMP indirgeme sirasi son bitleri oynatir (olculdu 01.10.2026: |Δ| 4e-16 .. 6e-15)
        return _("k-eff aynı (yalnız kayan nokta yuvarlama düzeyinde fark, |Δ| = %.1e): "
                 "%.6f ± %.6f") % (abs(fark), yeni[0], yeni[1])
    sigma = (eski[1] ** 2 + yeni[1] ** 2) ** 0.5
    return _("k-eff farkı: %.6f → %.6f (Δ = %+.6f, %.2fσ birleşik)") % (
        eski[0], yeni[0], fark, abs(fark) / sigma if sigma else float("inf"))


def _ortam_farklarini_yaz(kapsul, simdiki):
    fark = farklar(kapsul, simdiki)
    if not fark:
        print(_("Ortam farkı yok: kapsül ile bugünkü ortam aynı."))
    for alan, e, y in fark:
        print("  %-36s %s → %s" % (alan, e, y))
    return fark


def _hazirla(a):
    """(kapsul, spec, hedef) ya da hata metni."""
    from cekirdek import sema
    kaynak = os.path.abspath(a.kosu_dizini)
    hedef = os.path.abspath(a.hedef or kaynak.rstrip(os.sep) + "_yeniden")
    if hedef == kaynak:
        return _("hedef dizin kaynak koşu diziniyle aynı olamaz: %s") % hedef
    try:
        kapsul = oku(kaynak)
    except KapsulHatasi as e:
        return str(e)
    if not spec_eslesiyor(kaynak, kapsul):
        return _("%s kapsülden sonra değişmiş (sha256 farklı); yeniden üretim reddedildi") \
            % os.path.join(kaynak, kapsul["spec"]["dosya"])
    return kapsul, sema.yukle(os.path.join(kaynak, kapsul["spec"]["dosya"])), hedef


def yeniden_komutu(argv):
    """Cikis: 0 tamam, 1 kosu basarisiz, 2 kullanim/kapsul hatasi."""
    try:
        a = _argumanlar(argv)
    except SystemExit as cikis:          # argparse --help (0) / hatali arguman (2)
        return cikis.code if isinstance(cikis.code, int) else 2
    hazir = _hazirla(a)
    if isinstance(hazir, str):
        print(hazir, file=sys.stderr)
        return 2
    kapsul, spec, hedef = hazir
    kaynak = os.path.abspath(a.kosu_dizini)
    n = a.is_parcacigi or kapsul.get("is_parcacigi")
    print(_("Kapsül: %s (oluşturma %s)") % (os.path.join(kaynak, KAPSUL_ADI),
                                            kapsul.get("olusturma")))
    simdiki = olustur(spec, os.path.join(kaynak, kapsul["spec"]["dosya"]), n)
    _ortam_farklarini_yaz(kapsul, simdiki)
    print(_("Plan: tohum %s, iş parçacığı %s, hedef %s") % (kapsul.get("tohum"), n, hedef))
    if a.kuru:
        print(_("Kuru çalışma (--kuru): koşu başlatılmadı."))
        return 0
    from cekirdek import kosucu
    sonuc = kosucu.calistir(spec, hedef, is_parcacigi=n)
    if not sonuc["basarili"]:
        print(_("Yeniden koşu başarısız (çıkış kodu %s); log: %s")
              % (sonuc["cikis_kodu"], sonuc["log"]), file=sys.stderr)
        return 1
    try:
        yeni = oku(hedef)
        if yeni["spec"]["sha256"] != kapsul["spec"]["sha256"]:
            print(_("Not: yeni spec.json baytları farklı (şema göçü ya da biçim); model "
                    "aynı spec'ten kuruldu."))
    except KapsulHatasi as e:
        print(_("Not: yeni koşunun kapsülü okunamadı: %s") % e)
    print(_k_farki_satiri(_keff(kaynak), _keff(hedef)))
    return 0
