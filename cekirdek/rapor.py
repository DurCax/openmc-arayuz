# -*- coding: utf-8 -*-
"""
rapor.py -- model ve kosu raporu (HTML ve PDF).

SOZLESME (DONUK; testler/test_rapor_sozlesme.py):

    from cekirdek import rapor
    try:
        sonuc = rapor.olustur(spec, kosu_dizini, "rapor.pdf", "pdf")
    except rapor.RaporHatasi as e:       # ValueError alt sinifi
        goster(str(e))                   # kullaniciya gosterilecek Turkce metin
    sonuc.yol       # yazilan dosyanin mutlak yolu
    sonuc.uyarilar  # tuple[str, ...] (ornek: "tekrarlanabilirlik: ... bilinmiyor")

- spec DEGISMEZ (okunur; islemler derin kopya uzerinde yapilir).
- kosu_dizini None -> yalniz model raporu (kosu sonucu bolumleri yok).
- bicim: "html" | "pdf" (BICIMLER). PDF cekirdek/rapor_pdf.py'de, Qt TEMBEL
  import edilir; bu modul modul duzeyinde PySide6 ice aktarmaz.
- Bilinmeyen tekrarlanabilirlik alani "bilinmiyor" yazilir ve loglanir.

YAPI
  icerik_topla(spec, kosu_dizini)    -> duz sozluk (sayilar + PNG gorseller)
  rapor_sablon.html(icerik, gomulu)  -> HTML metni (stdlib string.Template)
  rapor_sablon.grafik                -> matplotlib Figure + Agg (pyplot YOK)
  rapor_pdf.yaz(icerik, yol)         -> QTextDocument + QPdfWriter
  uygunluk_eki(...)                  -> cekirdek/rapor_uygunluk (Dalga S-2)
  Yeni bagimlilik yok: matplotlib, openmc, PySide6 zaten kurulu.

KOMUT SATIRI
  openmc-arayuz-kosu rapor <kosu_dizini> -o rapor.pdf   (cekirdek/giris.py)
"""

import copy
import datetime
import getpass
import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple

from cekirdek.ceviri import _, etkin_dil, KAYNAK_DIL
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

BICIMLER = ("html", "pdf")
BILINMIYOR = "bilinmiyor"
LOG_ADI = "kosu.log"
TUKENME_H5 = "depletion_results.h5"
_LOG_AZAMI_BAYT = 4_000_000        # buyuk loglarin yalniz basi okunur
_TALLY_AZAMI_SATIR = 40


class RaporHatasi(ValueError):
    """Rapor olusturulamadi; metni kullaniciya gosterilir."""


@dataclass(frozen=True)
class RaporSonucu:
    yol: str
    uyarilar: Tuple[str, ...] = ()


# ============================================================================
# YARDIMCILAR
# ============================================================================

def _kisa_yol(yol):
    """Ev dizinini "~" ile kisaltir (paylasilan raporda kullanici yolu kalmasin)."""
    if not yol:
        return yol
    ev = os.path.expanduser("~")
    return "~" + yol[len(ev):] if yol == ev or yol.startswith(ev + os.sep) else yol


_SHA_ONBELLEK = {}


def _sha256(yol):
    """Dosyanin sha256'si; okunamazsa None (loglanir). Onbellek: yol+boyut+zaman."""
    try:
        bilgi = os.stat(yol)
        anahtar = (os.path.abspath(yol), bilgi.st_size, bilgi.st_mtime)
        if anahtar not in _SHA_ONBELLEK:
            h = hashlib.sha256()
            with open(yol, "rb") as f:
                for parca in iter(lambda: f.read(1 << 20), b""):
                    h.update(parca)
            _SHA_ONBELLEK[anahtar] = h.hexdigest()
        return _SHA_ONBELLEK[anahtar]
    except OSError:
        _log.info("sha256 okunamadı: %s", yol, exc_info=True)
        return None


def _kullanici():
    try:
        return getpass.getuser()
    except (KeyError, OSError):
        _log.info("rapor: kullanıcı adı %s", BILINMIYOR, exc_info=True)
        return BILINMIYOR


# ============================================================================
# TEKRARLANABILIRLIK
# ============================================================================

_LOG_DESENLERI = {
    "openmc_surum": re.compile(r"^\s*Version \|\s*(\S+)", re.M),
    "openmc_commit": re.compile(r"^\s*Commit Hash \|\s*(\S+)", re.M),
    "is_parcacigi": re.compile(r"^\s*OpenMP Threads \|\s*(\d+)", re.M),
    "zincir": re.compile(r"^\s*Reading chain file:\s*(.+?)\.\.\.\s*$", re.M),
    "nuklid_dosyasi": re.compile(r"^\s*Reading \S+ from (\S+\.h5)\s*$", re.M),
}


def log_bilgisi(kosu_dizini):
    """kosu.log'un basliginda OpenMC'nin yazdigi alanlar (YENI sozluk; log
    yoksa bos). Anahtarlar: openmc_surum, openmc_commit, is_parcacigi,
    zincir, kutuphane_dizini."""
    yol = os.path.join(kosu_dizini, LOG_ADI) if kosu_dizini else None
    if not yol or not os.path.exists(yol):
        return {}
    try:
        with open(yol, encoding="utf-8", errors="replace") as f:
            metin = f.read(_LOG_AZAMI_BAYT)
    except OSError:
        _log.warning("koşu logu okunamadı: %s", yol, exc_info=True)
        return {}
    bilgi = {}
    for ad, desen in _LOG_DESENLERI.items():
        m = desen.search(metin)
        if m:
            bilgi[ad] = m.group(1).strip()
    nuklid = bilgi.pop("nuklid_dosyasi", None)
    if nuklid:      # .../<kutuphane>/neutron/U235.h5 -> .../<kutuphane>
        bilgi["kutuphane_dizini"] = os.path.dirname(os.path.dirname(nuklid))
    return bilgi


def _statepoint_meta(kosu_dizini):
    """Statepoint'in kimlik alanlari + cevrim k'leri (k_nesil); kosu yoksa ya
    da okunamazsa {}. summary.h5 BAGLANMAZ (autolink=False): hizli."""
    if not kosu_dizini:
        return {}
    from cekirdek import kosucu
    yol = kosucu.son_statepoint(kosu_dizini)
    if not yol:
        return {}
    try:
        import openmc
        sp = openmc.StatePoint(yol, autolink=False)
        ozdeger = sp.run_mode == "eigenvalue"
        meta = {"openmc_surum": ".".join(str(int(x)) for x in sp.version),
                "tohum": int(sp.seed), "parcacik": int(sp.n_particles),
                "cevrim": int(sp.n_batches), "tarih": str(sp.date_and_time),
                "statepoint": yol}
        meta["pasif"] = int(sp.n_inactive) if ozdeger else 0
        meta["k_nesil"] = [float(x) for x in sp.k_generation] if ozdeger else []
        return meta
    except Exception:
        _log.warning("statepoint kimlik alanları okunamadı: %s", yol, exc_info=True)
        return {}


def _kutuphane_metni(log):
    if log.get("kutuphane_dizini"):
        d = log["kutuphane_dizini"]
        return "%s (%s)" % (os.path.basename(d.rstrip("/")), _kisa_yol(d))
    xs = os.environ.get("OPENMC_CROSS_SECTIONS")
    if xs:
        d = os.path.dirname(os.path.abspath(xs))
        return _("%s (%s; rapor anındaki ortam)") % (os.path.basename(d), _kisa_yol(xs))
    return None


def _zincir_metni(spec, log, kosu_dizini=None):
    yol, kaynak = log.get("zincir"), ""
    if not yol:
        yol = os.environ.get("OPENMC_CHAIN_FILE")
        kaynak = _("; rapor anındaki ortam") if yol else ""
    if not yol:
        return None
    ozet = _sha256(os.path.expanduser(yol))
    sha = ("sha256 %s" % ozet) if ozet else _("sha256 %s") % BILINMIYOR
    kullanim = "" if (spec.get("tukenme") or {}).get("var") else _("; tükenme kapalı")
    return "%s (%s%s%s), %s%s" % (os.path.basename(yol), _kisa_yol(os.path.expanduser(yol)),
                                  kaynak, kullanim, sha, _zincir_secim_metni(spec, kosu_dizini))


def _zincir_secim_metni(spec, kosu_dizini=None):
    """Tukenme aciksa zincir seciminin gerekcesi (tukenme.zincir_secimi)."""
    if not (spec.get("tukenme") or {}).get("var"):
        return ""
    from cekirdek import tukenme
    try:
        zs = tukenme.zincir_secimi(spec, kosu_dizini)
    except (KeyError, ValueError, OSError) as e:
        from cekirdek.gunluk import kaydedici
        kaydedici(__name__).warning("zincir seçimi rapora yazılamadı: %s", e)
        return ""
    return _("; seçim: %s zincir — %s") % (tukenme.spektrum_adi(zs["temel"]), zs["gerekce"])


def _git_metni(derleme):
    commit = derleme.get("git_commit")
    if not commit:
        return None
    if derleme.get("git_degisiklik"):
        return _("%s (commit edilmemiş değişiklik var)") % commit
    return commit


def _openmc_metni(meta, log):
    surum = meta.get("openmc_surum") or log.get("openmc_surum")
    if not surum:
        try:
            import openmc
            return _("%s (kurulu; koşu yok)") % openmc.__version__
        except ImportError:           # OpenMC kurulu degil: alan "bilinmiyor" olur (uyari)
            return None
    if log.get("openmc_commit"):
        return "%s (commit %s)" % (surum, log["openmc_commit"][:12])
    return surum


def _alan_listesi(spec, kosu_dizini):
    """[(etiket, deger | None)] -- None 'bilinmiyor' olarak yazilir."""
    from cekirdek import surum as _surum
    derleme = _surum.derleme_bilgisi()
    meta, log = _statepoint_meta(kosu_dizini), log_bilgisi(kosu_dizini)
    ayar, calis = spec.get("ayarlar") or {}, spec.get("calistirma") or {}
    kosu_var = bool(meta)

    def kaynaktan(anahtar, spec_degeri):
        deger = meta.get(anahtar) if kosu_var else spec_degeri
        return None if deger is None else str(deger)
    pasif = kaynaktan("pasif", ayar.get("pasif"))
    cevrim = kaynaktan("cevrim", ayar.get("cevrim"))
    alanlar = [
        (_("Uygulama sürümü"), "%s %s" % (_(derleme["uygulama"]), derleme["surum"])),
        (_("Git commit"), _git_metni(derleme)),
        (_("Python / platform"), "%s / %s" % (derleme["python"], derleme["platform"])),
        (_("OpenMC sürümü"), _openmc_metni(meta, log)),
        (_("Tesir kesiti kütüphanesi"), _kutuphane_metni(log)),
        (_("Zincir dosyası"), _zincir_metni(spec, log, kosu_dizini)),
        (_("Tohum"), kaynaktan("tohum", ayar.get("tohum"))),
        (_("Parçacık / çevrim"), kaynaktan("parcacik", ayar.get("parcacik"))),
        (_("Çevrim (pasif)"), (_("%s (%s pasif)") % (cevrim, pasif)) if cevrim else None),
        (_("İş parçacığı"), log.get("is_parcacigi") if kosu_var
         else (str(calis["is_parcacigi"]) if calis.get("is_parcacigi") else None)),
    ]
    if kosu_var:
        alanlar += [(_("Koşu tarihi"), meta.get("tarih")),
                    (_("Statepoint"), _kisa_yol(os.path.abspath(meta["statepoint"])))]
    # S-4: koşu anındaki ortamın kapsülü (kapsul.json); eski koşularda yok -> satır yok
    from cekirdek import kapsul as _kapsul
    kapsul_metni = _kapsul.ozet_metni(kosu_dizini)
    if kapsul_metni:
        alanlar.append((_("Tekrarlanabilirlik kapsülü"), kapsul_metni))
    return alanlar


def tekrarlanabilirlik(spec, kosu_dizini):
    """
    Tekrarlanabilirlik blogu: ([(etiket, deger)], uyarilar). Kosu varsa
    degerler statepoint ve kosu.log'dan, yoksa spec'ten ve ortamdan gelir.
    Bulunamayan alan "bilinmiyor" yazilir, loglanir ve uyarilara eklenir.
    """
    sonuc, uyarilar = [], []
    for etiket, deger in _alan_listesi(spec, kosu_dizini):
        if not deger:
            _log.info("rapor tekrarlanabilirlik alanı %s: %s", BILINMIYOR, etiket)
            uyarilar.append(_("tekrarlanabilirlik: %s bilinmiyor") % etiket)
            deger = BILINMIYOR
        sonuc.append((etiket, deger))
    return sonuc, uyarilar


# ============================================================================
# MODEL BOLUMLERI
# ============================================================================

def _sayi(x):
    """Kisa sayi metni (%.6g); sayi degilse oldugu gibi."""
    return "%.6g" % x if isinstance(x, (int, float)) and not isinstance(x, bool) else str(x)


def _bilesen_metni(b):
    ad = b.get("isim", "?")
    if b.get("zenginlik") is not None:
        ad += _(" (%%%s zengin)") % _sayi(b["zenginlik"])
    return "%s %s %s" % (ad, _sayi(b.get("miktar", "")), b.get("birim", ""))


def _renk(m):
    """spec malzeme rengi [r, g, b] -> "#rrggbb" (geometri kesitinin gostergesi)."""
    try:
        return "#%02x%02x%02x" % tuple(int(c) for c in m["renk"][:3])
    except (KeyError, TypeError, ValueError):     # renksiz malzeme: gosterge bos
        return ""


def _malzeme_satirlari(spec):
    satirlar = []
    for m in spec.get("malzemeler") or []:
        y = m.get("yogunluk") or {}
        satirlar.append({
            "ad": m.get("gorunen_ad") or m.get("ad", ""),
            "kimlik": m.get("ad", ""),
            "yogunluk": "%s %s" % (_sayi(y.get("deger", "")), y.get("birim", "")),
            "sicaklik": "%s K" % m.get("sicaklik", "") if m.get("sicaklik") else "",
            "bilesim": ", ".join(_bilesen_metni(b) for b in m.get("bilesim") or []),
            "sab": ", ".join(m.get("sab") or []),
            "renk": _renk(m),
        })
    return satirlar


def _sinir_kosullari(spec, kor):
    """Sinir kosullari: sablonda kor.sinir, gelismis modda agac kokunun siniri
    (yuz basina sinir varsa o da)."""
    from cekirdek import sema
    if not sema.agac_modu(spec):
        return kor.get("sinir") or {}
    from cekirdek import geometri
    sb = geometri.sinir_bilgisi(geometri.model(spec))
    sinir = {k: v for k, v in (("yan", sb.yan), ("alt", sb.alt), ("ust", sb.ust)) if v}
    if isinstance(sb.yuzler, dict):
        sinir.update(sb.yuzler)
    elif sb.yuzler:
        sinir.update(zip(sb.yuz_adlari, sb.yuzler))
    return sinir


def _ayar_satirlari(spec):
    from cekirdek import dogrula, kaynak as _kaynak, sema
    from cekirdek.dogrula.kor import _yon_adi
    a, kor = spec.get("ayarlar") or {}, spec.get("kor") or {}
    ent = a.get("entropi_mesh") or {}
    g, t = spec.get("guc_dagilimi") or {}, spec.get("tukenme") or {}
    h = sema.model_yuksekligi(spec)
    sinir = _sinir_kosullari(spec, kor)
    satirlar = [
        (_("Kor türü"), dogrula._kor_turu_adi(kor.get("tur"))),
        (_("Yükseklik"), ("%.2f cm" % h) if h else _("2B (eksenel sonsuz)")),
        (_("Sınır koşulları"), ", ".join("%s: %s" % (_yon_adi(k), v) for k, v in sinir.items())),
        (_("Hesap modu"), str(a.get("mod", ""))),
        (_("Parçacık / çevrim"), str(a.get("parcacik", ""))),
        (_("Çevrim (pasif)"), "%s (%s)" % (a.get("cevrim", ""), a.get("pasif", ""))),
        (_("Tohum"), str(a.get("tohum", ""))),
        (_("Sıcaklık yöntemi"), str(a.get("sicaklik_yontemi", ""))),
        (_("Kaynak"), _kaynak.ozet(a.get("kaynak"))),
        (_("Shannon entropisi"), (" × ".join(str(x) for x in ent.get("boyut") or [])
                                 if ent.get("var") else _("kapalı"))),
        (_("Güç dağılımı"), (_("açık: %s, %s dilim, %s") % (
            g.get("cubuk"), g.get("eksenel_dilim"), g.get("skor"))) if g.get("var")
         else _("kapalı")),
        (_("Tükenme"), (_("açık: %s W/gHM, %d adım") % (
            t.get("guc_yogunlugu"), len(t.get("adimlar") or []))) if t.get("var")
         else _("kapalı")),
    ]
    return satirlar


def model_bolumleri(spec):
    """{"malzemeler", "ayarlar", "spec_json"} -- spec'ten, kosu gerektirmez."""
    return {"malzemeler": _malzeme_satirlari(spec), "ayarlar": _ayar_satirlari(spec),
            "spec_json": json.dumps(spec, ensure_ascii=False, indent=1, default=str)}


def bulgular(spec):
    """Dogrulama bulgulari [{"seviye","yer","mesaj","oneri"}], uyarilar."""
    from cekirdek import dogrula
    try:
        liste = dogrula.tum_kontroller(spec)
    except Exception as e:
        _log.warning("rapor: doğrulama çalıştırılamadı", exc_info=True)
        return [], [_("doğrulama çalıştırılamadı: %s") % e]
    return [{"seviye": b.seviye, "yer": dogrula.yer_etiketi(b.yer), "mesaj": b.mesaj,
             "oneri": b.oneri or ""} for b in liste], []


# ============================================================================
# KOSU BOLUMLERI
# ============================================================================

def _kosu_ozeti(spec, sonuc, k_nesil):
    from cekirdek import kosucu, uygunluk
    from cekirdek.rapor_sablon import bicim
    k, s = sonuc["keff"] if sonuc.get("keff") else (None, None)
    ozet = {"mod": sonuc["mod"], "keff": k, "sigma": s, "cevrim": sonuc["cevrim"],
            "pasif": sonuc["pasif"], "parcacik": sonuc["parcacik"],
            "k_nesil": k_nesil, "entropi": list(sonuc.get("entropi") or []),
            "kinetik": sonuc.get("kinetik"), "durum": "", "ayrinti": "", "yakinsama": ""}
    if k is not None:
        beta = (sonuc.get("kinetik") or {}).get("beta_eff")
        sonsuz = uygunluk.sonsuz_ortam(spec)
        ozet["durum"], ayrinti = kosucu.keff_yorumu(k, s, beta, sonsuz=sonsuz)
        ozet["ayrinti"] = bicim.kosu_ayrintisi(ayrinti, k, s, sonsuz)     # K5 (GUM)
        if ozet["entropi"]:
            ozet["yakinsama"] = kosucu.entropi_yakinsama(ozet["entropi"], ozet["pasif"])[1]
        elif sonuc.get("entropi_hata"):
            ozet["yakinsama"] = _("Shannon entropisi okunamadı: %s") % sonuc["entropi_hata"]
        else:
            ozet["yakinsama"] = _("Shannon entropisi kapalı — kaynak yakınsaması doğrulanamıyor")
    if ozet["kinetik"]:
        kin = ozet["kinetik"]
        ozet["lambda_metni"] = bicim.zaman_metni(kin["lambda"], kin["lambda_sapma"])
    return ozet


def _guc_ozeti(spec, sonuc):
    from cekirdek import geometri, guc as _guc, kosucu
    g = sonuc.get("guc")
    if not g or not g.get("faktorler"):
        return ({"hata": sonuc["guc_hata"]} if sonuc.get("guc_hata") else None)
    f = g["faktorler"]
    m = _guc.mutlak_guc(f, (spec.get("guc_dagilimi") or {}).get("toplam_guc"),
                        geometri.hedef_yuksekligi(spec), hedef_payi=g.get("hedef_payi"))
    yorum = kosucu.korunum_satirlari(g) + _guc.yorumla(
        f, m, hedef_payi=g.get("hedef_payi"), hedef_payi_hata=g.get("hedef_payi_hata"),
        kategori=spec.get("kategori"))
    sicak = _guc.konum_metni(f["sicak_cubuk"], f.get("kafes_turu"), f.get("kafes_turleri"))
    return {"faktorler": f, "mutlak": m, "yorum": yorum, "sicak_cubuk": sicak,
            "dagilim": g["dagilim"], "korunum": g.get("korunum")}


def _tally_tablosu(ad, df):
    """{"ad", "sutunlar", "satirlar", "kirpildi", "hata"} -- DataFrame metne."""
    if isinstance(df, str):
        return {"ad": ad, "sutunlar": [], "satirlar": [], "kirpildi": 0, "hata": df}
    duz = df.copy()
    duz.columns = [" ".join(str(p) for p in (c if isinstance(c, tuple) else (c,)) if p)
                   for c in duz.columns]
    satirlar = []
    for _i, r in duz.head(_TALLY_AZAMI_SATIR).iterrows():
        hucre = []
        for c in duz.columns:
            v = r[c]
            hucre.append("%.4e" % v if isinstance(v, float) else str(v))
        ort, sap = float(r.get("mean", 0.0)), float(r.get("std. dev.", 0.0))
        hucre.append("%.2f%%" % (100.0 * sap / abs(ort)) if ort else "—")
        satirlar.append(hucre)
    return {"ad": ad, "sutunlar": list(duz.columns) + [_("bağıl hata")],
            "satirlar": satirlar, "kirpildi": max(0, len(duz) - _TALLY_AZAMI_SATIR),
            "hata": ""}


def _tukenme_h5(spec, kosu_dizini):
    adaylar = [kosu_dizini, kosu_dizini.rstrip(os.sep) + "_tukenme"]
    for d in adaylar:
        if os.path.exists(os.path.join(d, TUKENME_H5)):
            return d
    return None


def _tukenme_ozeti(spec, kosu_dizini):
    """(tukenme ozeti | None, uyarilar). Sonuc tukenme.onceki_sonuc ile okunur."""
    d = _tukenme_h5(spec, kosu_dizini)
    if d is None:
        return None, []
    from cekirdek import tukenme
    try:
        kayit = tukenme.onceki_sonuc(spec, d)
    except Exception as e:
        _log.warning("rapor: tükenme sonucu okunamadı: %s", d, exc_info=True)
        return None, [_("tükenme sonucu okunamadı: %s") % e]
    s = kayit["sonuc"]
    satirlar = [(i, s["zaman_d"][i], s["yanma"][i], s["k"][i], s["k_sapma"][i])
                for i in range(len(s["zaman_d"]))]
    toplam = {}
    for nuklidler in s["atomlar"].values():
        for n, dizi in nuklidler.items():
            eski = toplam.get(n, [0.0] * len(dizi))
            toplam[n] = [a + b for a, b in zip(eski, dizi)]
    uyari = []
    if kayit["durum"] != "guncel":
        uyari.append(_("tükenme sonucu bu modele ait olmayabilir (%s)") % kayit["durum"])
    return {"satirlar": satirlar, "yanma": s["yanma"], "k": s["k"], "atomlar": toplam,
            "bulunamayan": s.get("bulunamayan") or [], "durum": kayit["durum"]}, uyari


def kosu_bolumleri(spec, kosu_dizini):
    """{"kosu","guc","tallyler","tukenme","gorseller","uyarilar"} -- kosu
    dizininden. Statepoint yoksa ya da okunamazsa RaporHatasi."""
    from cekirdek import kosucu
    from cekirdek.rapor_sablon import grafik
    sp_yolu = kosucu.son_statepoint(kosu_dizini)
    if not sp_yolu:
        raise RaporHatasi(_("Koşu dizininde statepoint dosyası yok: %s") % kosu_dizini)
    try:
        sonuc = kosucu.sonuc_oku(sp_yolu)
    except Exception as e:
        _log.warning("rapor: statepoint okunamadı: %s", sp_yolu, exc_info=True)
        raise RaporHatasi(_("Statepoint okunamadı: %s (%s)") % (sp_yolu, e)) from e
    kosu = _kosu_ozeti(spec, sonuc, _statepoint_meta(kosu_dizini).get("k_nesil", []))
    guc = _guc_ozeti(spec, sonuc)
    tuk, uyarilar = _tukenme_ozeti(spec, kosu_dizini)
    gorsel, u = grafik.kosu_gorselleri(kosu, guc, tuk)
    tallyler = [_tally_tablosu(ad, df) for ad, df in sonuc["tallyler"].items()]
    return {"kosu": kosu, "guc": guc, "tallyler": tallyler, "tukenme": tuk,
            "gorseller": gorsel, "uyarilar": uyarilar + u}


# ============================================================================
# ICERIK + YAZMA
# ============================================================================

def _yerel_aciklama(spec):
    """Model aciklamasi etkin dilde: Turkce disinda varsa `aciklama_en`
    (sema.META_ALANLARI), yoksa `aciklama` (kullanici verisi, cevrilmez)."""
    if etkin_dil() != KAYNAK_DIL and spec.get("aciklama_en"):
        return spec["aciklama_en"]
    return spec.get("aciklama") or ""


def _kapak(spec):
    return {"baslik": spec.get("ad") or _("adsız model"),
            "aciklama": _yerel_aciklama(spec),
            "tarih": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "kullanici": _kullanici()}


def icerik_topla(spec, kosu_dizini):
    """
    Raporun butun verisi (YENI sozluk; spec degismez):
      kapak, tekrar [(etiket, deger)], malzemeler, ayarlar, spec_json,
      bulgular, kosu (None | keff, sigma, ...), guc (None | faktorler, ...),
      tallyler, tukenme (None | ...), gorseller {ad: PNG bayt}, uyarilar,
      uygunluk (rapor_uygunluk.ek_verisi: profiller, gruplar, cerceve, ...)
    """
    from cekirdek.rapor_sablon import grafik
    spec = copy.deepcopy(spec)
    icerik = {"kapak": _kapak(spec), "kosu_dizini": kosu_dizini,
              "kosu": None, "guc": None, "tukenme": None, "tallyler": []}
    icerik["tekrar"], uyarilar = tekrarlanabilirlik(spec, kosu_dizini)
    icerik.update(model_bolumleri(spec))
    icerik["bulgular"], u = bulgular(spec)
    icerik["gorseller"], u2 = grafik.geometri_gorselleri(spec)
    uyarilar += u + u2
    if kosu_dizini is not None:
        kosu = kosu_bolumleri(spec, kosu_dizini)
        icerik.update({k: kosu[k] for k in ("kosu", "guc", "tallyler", "tukenme")})
        icerik["gorseller"] = dict(icerik["gorseller"], **kosu["gorseller"])
        uyarilar += kosu["uyarilar"]
    icerik["uyarilar"] = uyarilar
    icerik["uygunluk"] = uygunluk_eki(spec, kosu_dizini, icerik)
    if icerik["uygunluk"]["hata"]:
        uyarilar.append(icerik["uygunluk"]["hata"])
    return icerik


def uygunluk_eki(spec, kosu_dizini, icerik):
    """Uygunluk eki verisi (cekirdek/rapor_uygunluk.ek_verisi). Profil D'nin K5
    kurali EKSIZ rapor metnini denetler (ek, bulgularin kendisini aktarir)."""
    from cekirdek import rapor_sablon, rapor_uygunluk
    taslak = rapor_sablon.html(dict(icerik, uygunluk=None), gomulu=False)
    return rapor_uygunluk.ek_verisi(spec, kosu_dizini, rapor_metni=taslak)


def _girdileri_denetle(spec, kosu_dizini, bicim):
    if bicim not in BICIMLER:
        raise RaporHatasi(_("Bilinmeyen rapor biçimi: %s (geçerli: %s)")
                          % (bicim, ", ".join(BICIMLER)))
    if not isinstance(spec, dict) or not spec:
        raise RaporHatasi(_("Rapor için model (spec) gerekli."))
    if kosu_dizini is not None and not os.path.isdir(kosu_dizini):
        raise RaporHatasi(_("Koşu dizini bulunamadı: %s") % kosu_dizini)


def _ust_dizini_hazirla(yol):
    ust = os.path.dirname(yol)
    try:
        os.makedirs(ust, exist_ok=True)
    except OSError as e:
        _log.warning("rapor dizini oluşturulamadı: %s", ust, exc_info=True)
        raise RaporHatasi(_("Rapor dizini oluşturulamadı: %s (%s)") % (ust, e)) from e


def _html_yaz(icerik, yol):
    from cekirdek import rapor_sablon
    metin = rapor_sablon.html(icerik, gomulu=True)
    try:
        with open(yol, "w", encoding="utf-8") as f:
            f.write(metin)
    except OSError as e:
        _log.warning("HTML rapor yazılamadı: %s", yol, exc_info=True)
        raise RaporHatasi(_("Rapor yazılamadı: %s (%s)") % (yol, e)) from e


def _pdf_yaz(icerik, yol):
    from cekirdek import rapor_pdf
    try:
        rapor_pdf.yaz(icerik, yol)
    except rapor_pdf.PdfHatasi as e:
        raise RaporHatasi(str(e)) from e


def olustur(spec: dict, kosu_dizini: Optional[str], yol: str, bicim: str) -> RaporSonucu:
    """spec (+ varsa kosu_dizini sonuclari) icin `yol`a `bicim` biciminde rapor yazar."""
    _girdileri_denetle(spec, kosu_dizini, bicim)
    yol = os.path.abspath(yol)
    _ust_dizini_hazirla(yol)
    icerik = icerik_topla(spec, kosu_dizini)
    (_html_yaz if bicim == "html" else _pdf_yaz)(icerik, yol)
    _log.info("rapor yazıldı: %s (%s, %d uyarı)", yol, bicim, len(icerik["uyarilar"]))
    return RaporSonucu(yol=yol, uyarilar=tuple(icerik["uyarilar"]))
