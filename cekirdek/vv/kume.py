# -*- coding: utf-8 -*-
"""
vv/kume.py -- kayitli kriter (benchmark) olcumlerinden V&V ozeti (vv_arayuz.VVOzeti).

Kume: ornekler/kriter_*.json, ornekler/godiva_kriter.json ve ornekler/vv/kriter_*.json
icinden referans.tur == "deney" olup referans.olcum (bu aracin hesabi) bulunanlar.
Hesap-hesap kriterleri (tur = "hesap") kumeye GIRMEZ: E olculmus bir deney degildir.

  vakalar(dosyalar=None, filtre=None) -> [istatistik.Vaka]
  ozet(vakalar=None, filtre=None, uygulama=None, delta_sm=0.05, delta_aoa=0.0) -> VVOzeti
  uygulama(spec, kosu_dizini=None) -> AOA parametreleri (aoa.parametreler)
  aoa_filtresi(uygulama) -> {"bolunebilir", "fiziksel_bicim", "tayf"[, "zenginlik"]}
      | None   (uygulamaya uygun alt kume; bir anahtar eksikse None)
  uygulama_ozeti(spec, kosu_dizini=None, uygulama=None) -> (VVOzeti, uygulama)
      arayuz paneli, rapor eki ve CLI'nin ortak yolu: uygulamanin AOA'sina
      uygun alt kumeden USL; uygun alt kume yoksa usl None ve neden
      "bu uygulama için USL yok (AOA dışında)".

filtre: {parametre: deger | (deger, ...) | ("aralik", alt, ust)} -- AOA'ya gore alt
kume secimi (6698: USL her AOA icin ayri hesaplanir).
"""

import dataclasses
import glob
import json
import os
from collections import Counter

from cekirdek import yollar
from cekirdek.ceviri import _, N_, pgettext
from cekirdek.gunluk import kaydedici
from cekirdek.uygunluk_denetimi.vv_arayuz import AOA_KATEGORILERI, VVOzeti
from cekirdek.vv import aoa as _aoa
from cekirdek.vv import istatistik as _ist

# Alt kume secimi (6698 §2.5, Tablo 2.3): USL yalniz uygulamayla ayni bolunebilir
# tur, fiziksel bicim ve notron tayfini paylasan kriterlerden hesaplanir; U-235'te
# ayrica zenginlik sinifi (ZENGINLIK_SINIFLARI) ayni olmalidir. Uygun alt kume
# n < 10 ise (6698 §2.2) USL VERILMEZ -- depodaki kume kucukse dogru cevap budur.
# Yansitici ve H/X alt kumeyi daraltmaz; onlari K6-AOA ve K12 ayrica denetler.
AOA_FILTRE_ANAHTARLARI = ("bolunebilir", "fiziksel_bicim", "tayf")
# ICSBEP Handbook adlandirmasi (Introduction, "Fissile Material"): LEU <= %10,
# IEU %10-60, HEU >= %60 kutlece U-235. (ad, alt, ust) -- aralik kapali.
ZENGINLIK_SINIFLARI = {"U-235": (("LEU", 0.0, 10.0), ("IEU", 10.0, 60.0),
                                 ("HEU", 60.0, 100.0))}

_log = kaydedici(__name__)

KOK = yollar.veri_koku()
ORNEK = yollar.ornekler_dizini()
SAYISAL = ("zenginlik", "h_x", "ealf")
DELTA_SM_VARSAYILAN = 0.05
DELTA_SM_KAYNAK = (N_("ΔSM = 0.05: NUREG-1718 §6.4.3.3.4 / NUREG-1520 Bl. 5 Ek B'de ek gerekçesiz "
                   "kabul edildiği bildirilen değer (DOĞRULANMADI); alt sınır 0.02 "
                   "(NUREG/CR-6698 §2.4.5)"))
KAYNAK = (N_("NUREG/CR-6698 (2001) yöntemi; kriter modelleri mit-crpg/benchmarks (MIT lisansı) "
          "ve ICSBEP E ± σ (uncertainties.csv)"))


def kriter_dosyalari():
    """Kumeye aday JSON dosyalari (sirali)."""
    yollar = glob.glob(os.path.join(ORNEK, "kriter_*.json"))
    yollar += [os.path.join(ORNEK, "godiva_kriter.json")]
    yollar += glob.glob(os.path.join(ORNEK, "vv", "kriter_*.json"))
    return sorted(y for y in yollar if os.path.exists(y))


def _oku(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise ValueError(_("kriter dosyası okunamadı: %s (%s)") % (yol, e)) from e


def _vaka(yol, ham):
    ref = ham.get("referans") or {}
    olc = ref.get("olcum") or {}
    if ref.get("tur") != "deney" or "k" not in olc:
        return None
    return _ist.Vaka(ad=os.path.basename(yol), k=float(olc["k"]),
                     sigma_calc=float(olc["sigma"]), k_exp=float(ref["k"]),
                     sigma_exp=float(ref["sigma"]), parametreler=dict(ref.get("aoa") or {}),
                     seri=ref.get("seri") or ref.get("kaynak", ""))


def _uyar(vaka, filtre):
    for ad, kosul in (filtre or {}).items():
        deger = vaka.parametreler.get(ad)
        if isinstance(kosul, tuple) and kosul and kosul[0] == "aralik":
            if deger is None or not kosul[1] <= float(deger) <= kosul[2]:
                return False
        elif isinstance(kosul, (tuple, list, set, frozenset)):
            if deger not in kosul:
                return False
        elif deger != kosul:
            return False
    return True


def vakalar(dosyalar=None, filtre=None):
    """Deney kriterlerinden olcumu olanlar -> [Vaka] (filtreye uyanlar)."""
    sonuc = []
    for yol in dosyalar or kriter_dosyalari():
        v = _vaka(yol, _oku(yol))
        if v is None:
            _log.info("V&V kümesine alınmadı (deney değil ya da ölçüm yok): %s", yol)
            continue
        if _uyar(v, filtre):
            sonuc.append(v)
    return sonuc


def _aralik(vlar):
    sonuc = {}
    for ad in SAYISAL:
        degerler = [float(v.parametreler[ad]) for v in vlar if v.parametreler.get(ad) is not None]
        if degerler:
            sonuc[ad] = (min(degerler), max(degerler))
    return sonuc


def _kategorik(vlar):
    sonuc = {}
    for ad in AOA_KATEGORILERI:
        degerler = sorted({v.parametreler[ad] for v in vlar if v.parametreler.get(ad)})
        if degerler:
            sonuc[ad] = tuple(degerler)
    return sonuc


def ozet(vlar=None, filtre=None, uygulama=None, delta_sm=DELTA_SM_VARSAYILAN,
         delta_aoa=0.0, egilim_parametreleri=SAYISAL, n_usl_asgari=_ist.N_USL_ASGARI):
    """Kume -> VVOzeti (NUREG/CR-6698). uygulama verilirse bant yonteminde USL
    uygulamanin parametre degerinde hesaplanir."""
    vlar = vakalar(filtre=filtre) if vlar is None else [v for v in vlar if _uyar(v, filtre)]
    d = _ist.degerlendir(vlar, delta_sm=delta_sm, delta_aoa=delta_aoa,
                         egilim_parametreleri=egilim_parametreleri, uygulama=uygulama,
                         n_usl_asgari=n_usl_asgari)
    neden = d["usl_neden"]
    if d.get("usl_noktasi"):
        neden = _("USL tolerans bandından, %s noktasında") % d["usl_noktasi"]
    norm = d["normallik"]
    return VVOzeti(
        n=d["n"], yontem=d["yontem"], usl=d["usl"], usl_neden=neden, bias=d["bias"],
        bias_kullanilan=d["bias_kullanilan"], delta_sm=delta_sm, delta_aoa=delta_aoa,
        guven=d["guven"], normallestirildi=d["normallestirildi"],
        normallik=None if norm is None else dict(norm),
        egilim=d["egilim"], aralik=_aralik(vlar), aoa_kategorik=_kategorik(vlar),
        seriler=dict(Counter(v.seri for v in vlar)),
        kaynak=_(KAYNAK) + "; " + _(DELTA_SM_KAYNAK))


def uygulama(spec, kosu_dizini=None):
    """Uygulamanin AOA parametreleri (spec + kosu dizini; cikarilamayan yok)."""
    return _aoa.parametreler(spec, kosu_dizini)


def zenginlik_sinifi(tur, zenginlik):
    """(ad, alt, ust) -- tur icin sinif tanimli degilse None."""
    for ad, alt, ust in ZENGINLIK_SINIFLARI.get(tur, ()):
        if alt <= float(zenginlik) <= ust:
            return ad, alt, ust
    return None


def aoa_eksikleri(uyg):
    """Alt kume secimi icin uygulamada eksik AOA anahtarlari (sirali)."""
    uyg = uyg or {}
    eksik = [a for a in AOA_FILTRE_ANAHTARLARI if not uyg.get(a)]
    if uyg.get("bolunebilir") in ZENGINLIK_SINIFLARI and uyg.get("zenginlik") is None:
        eksik.append("zenginlik")
    return eksik


def aoa_filtresi(uyg):
    """Uygulamanin AOA'sina uygun alt kume filtresi: bolunebilir tur + fiziksel
    bicim + tayf (+ U-235'te zenginlik sinifi). Bir anahtar eksikse None."""
    if aoa_eksikleri(uyg):
        return None
    filtre = {a: uyg[a] for a in AOA_FILTRE_ANAHTARLARI}
    sinif = zenginlik_sinifi(uyg["bolunebilir"], uyg.get("zenginlik") or 0.0)
    if sinif is not None:
        filtre["zenginlik"] = ("aralik", sinif[1], sinif[2])
    return filtre


def _tayf_metni(tayf):
    adlar = {"termal": pgettext("spektrum", "termal"), "ara": _("ara enerji"),
             "hizli": pgettext("spektrum", "hızlı")}
    return adlar.get(tayf, str(tayf))


def _bicim_metni(bicim):
    adlar = {"metal": _("metal"), "cozelti": _("çözelti"), "oksit": _("oksit"),
             "bilesik": _("bileşik")}
    return adlar.get(bicim, str(bicim))


def alt_kume_metni(filtre):
    """Filtrenin okunur betimi: 'U-235, oksit, termal, LEU (%0–10)'."""
    parcalar = [str(filtre.get("bolunebilir", "?")),
                _bicim_metni(filtre.get("fiziksel_bicim")), _tayf_metni(filtre.get("tayf"))]
    z = filtre.get("zenginlik")
    if z:
        sinif = zenginlik_sinifi(filtre["bolunebilir"], 0.5 * (z[1] + z[2]))
        parcalar.append("%s (%%%g–%g)" % (sinif[0] if sinif else "?", z[1], z[2]))
    return ", ".join(parcalar)


def _eksik_neden(eksik, kosu_dizini=None):
    if "tayf" in eksik:
        _ealf, tally_sorunu = _aoa.ealf_ayrintili(kosu_dizini)
        if tally_sorunu:
            return _("bu uygulama için USL yok (AOA belirlenemedi): nötron tayfı bilinmiyor; "
                     "%s — tally'yi silip Uygunluk kartındaki öneriyle ('%s') yeniden ekleyin "
                     "ve koşun") % (tally_sorunu, _aoa.EALF_TALLY)
        return _("bu uygulama için USL yok (AOA belirlenemedi): nötron tayfı bilinmiyor; "
                 "EALF tally'sini ('%s') ekleyip yeniden koşun") % _aoa.EALF_TALLY
    return _("bu uygulama için USL yok (AOA belirlenemedi): %s çıkarılamadı; "
             "uygunluk girdisinde verin") % ", ".join(eksik)


def uygulama_ozeti(spec, kosu_dizini=None, uygulama=None, vlar=None,
                   delta_sm=DELTA_SM_VARSAYILAN):
    """(VVOzeti, uygulama). uygulama: spec + kosu dizininden cikarilan AOA
    parametreleri, verilen sozlukle (kullanici girdisi) GUNCELLENIR. Alt kume
    aoa_filtresi ile secilir; secilemiyorsa butun kume betimsel ozetlenir.
    Iki durumda da USL cikmiyorsa usl None ve neden durustce yazilir.
    Girdi spec DEGISMEZ."""
    uyg = dict(_aoa.parametreler(spec, kosu_dizini) if spec is not None else {})
    uyg.update(uygulama or {})
    filtre = aoa_filtresi(uyg)
    if filtre is None:
        # Alt kume secilemez: kumenin TAMAMI betimsel olarak ozetlenir (K6-AOA, K12
        # uygulamayi yine kumeyle karsilastirir) ama USL VERILMEZ.
        oz = ozet(vlar, uygulama=uyg, delta_sm=delta_sm)
        return dataclasses.replace(oz, usl=None,
                                   usl_neden=_eksik_neden(aoa_eksikleri(uyg), kosu_dizini)), uyg
    metin = alt_kume_metni(filtre)
    oz = dataclasses.replace(ozet(vlar, filtre=filtre, uygulama=uyg, delta_sm=delta_sm),
                             alt_kume=metin)
    if oz.usl is None:
        oz = dataclasses.replace(oz, usl_neden=_(
            "bu uygulama için USL yok (AOA dışında): kümede alt kümeye (%s) uyan %d vaka "
            "var; %s") % (metin, oz.n, oz.usl_neden))
    return oz, uyg


