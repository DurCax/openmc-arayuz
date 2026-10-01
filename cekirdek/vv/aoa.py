# -*- coding: utf-8 -*-
"""
vv/aoa.py -- uygulanabilirlik alani (AOA) parametreleri (NUREG/CR-6698 §2.5, Tablo 2.3).

Bir modelin (uygulama ya da kriter) AOA parametrelerini spec'ten ve (varsa)
kosu dizinindeki statepoint'ten OTOMATIK cikarir; cikarilamayan parametre
sozlukte YER ALMAZ (tahmin edilmez -- kullanici girer).

  parametreler(spec, kosu_dizini=None) -> {
      "bolunebilir":    "U-235" | "U-233" | "Pu" | "karisik"     (kategorik)
      "zenginlik":      kutlece % (asagiya bakin)                  (sayisal)
      "h_x":            H / bolunebilir atom orani (homojen ise)   (sayisal)
      "fiziksel_bicim": "metal" | "cozelti" | "oksit" | "bilesik"  (kategorik)
      "ealf":           eV, fisyona yol acan notronun ortalama letarji enerjisi
      "tayf":           "termal" | "ara" | "hizli" (EALF'tan)       (kategorik)
  }

Tanimlar (bu aracin; 6698 kavramlarini somutlastirir):
  * zenginlik: tek bolunebilir turde, bolunebilir izotopun (U-235, U-233 ya da
    Pu-239 + Pu-241) kendi elementindeki kutle yuzdesi; "karisik"ta toplam
    bolunebilir kutlenin agir metale (Th + U + Pu) orani.
  * h_x: bolunebilir malzemelerin kendisinde H varsa (cozelti, homojen karisim)
    H atomu / bolunebilir atom. Hicbir malzemede H yoksa 0. H yalniz moderator
    gibi AYRI malzemedeyse (heterojen kafes) hacim gerekeceginden VERILMEZ.
  * fiziksel_bicim: bolunebilir malzemede agir olmayan atom kesri < %10 ->
    metal; H ve H_in_H2O S(a,b) -> cozelti; H yok ve O/agir metal 1.8-2.2 ->
    oksit; digerleri -> bilesik.
  * tayf: EALF < 1 eV termal; 1 eV - 100 keV ara; >= 100 keV hizli (6698 §2.5).
    EALF yalniz kosuda EALF_TALLY adli fisyon/enerji tally'si varsa hesaplanir.
"""

import glob
import math
import os

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

BOLUNEBILIR = {"U233": "U-233", "U235": "U-235", "Pu239": "Pu", "Pu241": "Pu"}
AGIR_ELEMENTLER = ("Th", "Pa", "U", "Np", "Pu", "Am", "Cm")
EALF_TALLY = "vv_ealf"
TERMAL_UST_EV = 1.0              # 6698 §2.5: termal 0-1 eV
ARA_UST_EV = 1.0e5               # ara 1 eV - 100 keV; hizli 100 keV - 20 MeV
KARISIK_ESIK = 0.10              # ikinci bolunebilir tur atom payi > %10 -> karisik
METAL_HAFIF_ESIK = 0.10
OKSIT_ARALIGI = (1.8, 2.2)
YAKIT_ESIGI = 0.01               # bolunebilir / agir metal atom payi
EALF_GRUP_SAYISI = 300           # 1e-5 eV - 20 MeV logaritmik
EALF_ALT_EV, EALF_UST_EV = 1.0e-5, 2.0e7


def _element(nuklid):
    harf = "".join(c for c in nuklid if c.isalpha())
    return harf.split("_")[0]


def _kutle(nuklid):
    import openmc.data
    return openmc.data.atomic_mass(nuklid)


def malzeme_yogunluklari(spec):
    """{malzeme adi: {nuklid: atom/b-cm}} -- kurucu.malzemeleri_kur uzerinden."""
    from cekirdek import kurucu
    nesneler, _m, _r = kurucu.malzemeleri_kur(spec)
    return {ad: dict(mat.get_nuclide_atom_densities()) for ad, mat in nesneler.items()}


def _kullanilan(spec):
    from cekirdek import sema
    return set(sema.kullanilan_malzemeler(spec))


def _sab_adlari(spec, ad):
    from cekirdek import sema
    m = sema.malzeme_bul(spec, ad) or {}
    return [s.lower() for s in m.get("sab") or []]


def _fisil_payi(n):
    agir = sum(d for nk, d in n.items() if _element(nk) in AGIR_ELEMENTLER)
    fisil = sum(d for nk, d in n.items() if nk in BOLUNEBILIR)
    return fisil / agir if agir > 0 else 0.0


def _fisil_malzemeler(yog, kullanilan):
    """Bolunebilir nuklid iceren kullanilan malzemeler; bolunebilir/agir metal
    atom payi YAKIT_ESIGI'nin altindakiler (dogal/fakir U yansitici) yakit
    sayilmaz -- hicbiri esigi gecmezse (dogal U yakitli sistem) hepsi alinir."""
    adaylar = {ad: n for ad, n in yog.items()
               if ad in kullanilan and any(nk in BOLUNEBILIR and d > 0 for nk, d in n.items())}
    yakit = {ad: n for ad, n in adaylar.items() if _fisil_payi(n) >= YAKIT_ESIGI}
    return yakit or adaylar


def _toplam(fisil, kosul):
    return sum(d for n in fisil.values() for nk, d in n.items() if kosul(nk))


def _bolunebilir_turu(fisil):
    paylar = {}
    for n in fisil.values():
        for nk, d in n.items():
            if nk in BOLUNEBILIR:
                paylar[BOLUNEBILIR[nk]] = paylar.get(BOLUNEBILIR[nk], 0.0) + d
    toplam = sum(paylar.values())
    sirali = sorted(paylar.items(), key=lambda t: -t[1])
    if len(sirali) > 1 and sirali[1][1] / toplam > KARISIK_ESIK:
        return "karisik"
    return sirali[0][0]


def _kutle_toplami(fisil, kosul):
    return sum(d * _kutle(nk) for n in fisil.values() for nk, d in n.items() if kosul(nk))


def _zenginlik(fisil, tur):
    if tur == "karisik":
        pay = _kutle_toplami(fisil, lambda nk: nk in BOLUNEBILIR)
        payda = _kutle_toplami(fisil, lambda nk: _element(nk) in AGIR_ELEMENTLER)
    else:
        izo = [nk for nk, t in BOLUNEBILIR.items() if t == tur]
        el = _element(izo[0])
        pay = _kutle_toplami(fisil, lambda nk: nk in izo)
        payda = _kutle_toplami(fisil, lambda nk: _element(nk) == el)
    return float(100.0 * pay / payda) if payda > 0 else None


def _h_x(yog, fisil, kullanilan):
    h_fisil = _toplam(fisil, lambda nk: _element(nk) == "H")
    x = _toplam(fisil, lambda nk: nk in BOLUNEBILIR)
    if h_fisil > 0:
        return float(h_fisil / x)
    h_her_yer = sum(d for ad, n in yog.items() if ad in kullanilan
                    for nk, d in n.items() if _element(nk) == "H")
    return 0.0 if h_her_yer == 0 else None


def _fiziksel_bicim(spec, fisil):
    agir = _toplam(fisil, lambda nk: _element(nk) in AGIR_ELEMENTLER)
    hepsi = _toplam(fisil, lambda nk: True)
    h = _toplam(fisil, lambda nk: _element(nk) == "H")
    o = _toplam(fisil, lambda nk: _element(nk) == "O")
    if hepsi > 0 and (hepsi - agir) / hepsi < METAL_HAFIF_ESIK:
        return "metal"
    sab = [s for ad in fisil for s in _sab_adlari(spec, ad)]
    if h > 0 and any("h_in_h2o" in s or s.startswith("lwtr") for s in sab):
        return "cozelti"
    if h == 0 and agir > 0 and OKSIT_ARALIGI[0] <= o / agir <= OKSIT_ARALIGI[1]:
        return "oksit"
    return "bilesik"


def tayf_sinifi(ealf):
    """EALF [eV] -> 'termal' | 'ara' | 'hizli' (6698 §2.5)."""
    if ealf < TERMAL_UST_EV:
        return "termal"
    return "ara" if ealf < ARA_UST_EV else "hizli"


def ealf_tally_tanimi():
    """Kriter/uygulama spec'ine eklenecek EALF tally'si (fisyon, log enerji gruplari)."""
    from cekirdek import sema
    oran = (EALF_UST_EV / EALF_ALT_EV) ** (1.0 / EALF_GRUP_SAYISI)
    gruplar = [EALF_ALT_EV * oran ** i for i in range(EALF_GRUP_SAYISI + 1)]
    return sema.tally(EALF_TALLY, ["fission"], [sema.filtre_enerji(gruplar)])


def ealf_tanimi_gecerli(tanim):
    """Spec'teki tally tanimi EALF icin kullanilabilir mi: tek enerji filtresi
    ve 'fission' skoru (elle eklenmis olabilir; grup sayisi serbest)."""
    filtreler = (tanim or {}).get("filtreler") or []
    return ("fission" in ((tanim or {}).get("skorlar") or []) and len(filtreler) == 1
            and filtreler[0].get("tur") == "enerji")


def ealf_hesapla(kenarlar, fisyon):
    """EALF = exp(Σ F_g ln E_g / Σ F_g); E_g grup sinirlarinin geometrik ortasi."""
    toplam = float(sum(fisyon))
    if toplam <= 0:
        return None
    ln = [0.5 * (math.log(kenarlar[i]) + math.log(kenarlar[i + 1]))
          for i in range(len(kenarlar) - 1)]
    return math.exp(sum(f * l for f, l in zip(fisyon, ln)) / toplam)


def _statepoint(kosu_dizini):
    adaylar = sorted(glob.glob(os.path.join(kosu_dizini, "statepoint.*.h5")))
    return adaylar[-1] if adaylar else None


def ealf_oku(kosu_dizini):
    """Kosu dizinindeki statepoint'ten EALF [eV]; tally ya da statepoint yoksa None."""
    return ealf_ayrintili(kosu_dizini)[0]


def _tally_verisi(t):
    """(kenarlar, fisyon) ya da kullanilamazsa neden metni (str). Elle eklenen
    tally de tanınır: tek EnergyFilter ve 'fission' skoru yeterlidir."""
    import openmc
    enerji = [f for f in t.filters if isinstance(f, openmc.EnergyFilter)]
    if not enerji:
        return _("'%s' tally'sinde enerji filtresi yok") % EALF_TALLY
    if len(t.filters) != 1:
        return _("'%s' tally'sinde enerji filtresinden başka filtre var") % EALF_TALLY
    if "fission" not in list(t.scores):
        return _("'%s' tally'sinde 'fission' skoru yok") % EALF_TALLY
    return list(enerji[0].values), list(t.get_values(scores=["fission"]).ravel())


def ealf_ayrintili(kosu_dizini):
    """(EALF [eV] | None, neden | None). neden: tally VAR ama kullanilamiyorsa
    (filtre/skor eksik) kullaniciya gosterilecek metin; tally hic yoksa None."""
    yol = _statepoint(kosu_dizini) if kosu_dizini else None
    if yol is None:
        return None, None
    import openmc
    try:
        with openmc.StatePoint(yol) as sp:
            veri = _tally_verisi(sp.get_tally(name=EALF_TALLY))
    except LookupError:
        _log.info("statepoint'te %s tally'si yok: EALF hesaplanmadı (%s)", EALF_TALLY, yol)
        return None, None
    if isinstance(veri, str):
        _log.warning("EALF hesaplanamadı (%s): %s", yol, veri)
        return None, veri
    return ealf_hesapla(*veri), None


def parametreler(spec, kosu_dizini=None):
    """Bkz. modul basligi. Cikarilamayan parametre sozlukte yer almaz."""
    yog = malzeme_yogunluklari(spec)
    kullanilan = _kullanilan(spec)
    fisil = _fisil_malzemeler(yog, kullanilan)
    sonuc = {}
    if fisil:
        tur = _bolunebilir_turu(fisil)
        sonuc["bolunebilir"] = tur
        zeng = _zenginlik(fisil, tur)
        if zeng is not None:
            sonuc["zenginlik"] = zeng
        hx = _h_x(yog, fisil, kullanilan)
        if hx is not None:
            sonuc["h_x"] = hx
        sonuc["fiziksel_bicim"] = _fiziksel_bicim(spec, fisil)
    else:
        _log.info(_("modelde bölünebilir nüklid içeren malzeme yok: AOA parametresi yok"))
    ealf = ealf_oku(kosu_dizini)
    if ealf is not None:
        sonuc["ealf"] = ealf
        sonuc["tayf"] = tayf_sinifi(ealf)
    return sonuc
