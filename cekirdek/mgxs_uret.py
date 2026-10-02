# -*- coding: utf-8 -*-
"""
================================================================================
 mgxs_uret.py  --  Cok gruplu tesir kesiti (grup sabiti) uretimi (v3 Y8)
================================================================================

 Surekli enerji (CE) Monte Carlo koşusunda openmc.mgxs.Library tally'leri
 toplanir; koşu bitince aki agirlikli grup sabitleri, tablo/CSV ve OpenMC
 MG modu kutuphanesi (mgxs.h5) uretilir.

 AYAR  spec["ayarlar"]["mgxs"] (sema.VARSAYILAN_AYARLAR'a YAZILMAZ: kapali
 modellerin spec'i ve onbellek kimligi degismesin). Arayuz ayari yalniz
 MGXS koşusunun KOPYA spec'ine yazar (arayuz/analiz/mgxs.py).
   {"var": bool,
    "bolge": "malzeme" | "hucre" | "demet",   # OpenMC domain_type
    "grup_yapisi": "CASMO-2" ...,              # openmc.mgxs.GROUP_STRUCTURES
    "turler": [...],                           # ISTEGE BAGLI ek turler
    "duzeltme": "P0" | "yok"}                  # tasima duzeltmesi

   bolge "demet" = kok evren: modelin TAMAMI tek bolgede homojenlestirilir.
   Yansitici sinirli tek demet / pin modelinde bu sonsuz kafesin demet
   sabitleridir (cekirdekte demet basina: cekirdek/alt_model.demet_alt_modeli).

 TANIMLAR (OpenMC 0.16 openmc.mgxs; kilavuz 4.12 ve ders 5.19)
   Sx_g    = <Sx phi>_g / <phi>_g  (hacim ve grup uzerinden aki agirlikli)
   chi_g   = nu-fisyon agirlikli cikis tayfi: sum_E' nuSf(E') phi(E') chi(E'->g)
             / sum nuSf phi (EnergyoutFilter); toplam 1.
   P0 duzeltmesi (out-scatter yaklasimi): Str_g = St_g - Ss1_g (Ss1_g: g'den
             CIKAN P1 sacilma momenti), sacilma matrisinin kosegeni ayni Ss1_g
             kadar azaltilir -> kaldirma degismez, D = 1/(3 Str). "yok": St ve
             duzeltmesiz P0 matris (izotropik sacilma varsayimi).
   nu-scatter matrix (n,xn) cogalmasini icerir; scatter matrix ile birlikte
             cogalma matrisi (multiplicity) kurulur.

 ESDEGERLIK  kurucu kancasi (tally_ekle) ve betik (kod_uret/mgxs.py) ayni
 parametrelerden (parametreler) kurar; testler/test_y8_mgxs.py.
================================================================================
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple

from cekirdek import mgxs_k
from cekirdek.ceviri import _, N_
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

# --- secenekler -------------------------------------------------------------
BOLGELER = {"malzeme": "material", "hucre": "cell", "demet": "universe"}
BOLGE_ADLARI = {"malzeme": N_("Malzeme"), "hucre": N_("Hücre"),
                "demet": N_("Demet (tüm model, tek bölge)")}
# Homojenlestirme 2-8 grup; MG yeniden koşu icin ince yapilar (>= 70 grup
# kendini koruma etkisini grup icinde kucuk tutar; CASMO-70/XMAS-172).
GRUP_YAPILARI = ("CASMO-2", "CASMO-4", "CASMO-8", "CASMO-16", "CASMO-25",
                 "CASMO-40", "CASMO-70", "XMAS-172")
VARSAYILAN_GRUP = "CASMO-2"
DUZELTMELER = ("yok", "P0")
# Varsayilan "yok": P0 duzeltmesi ince grupta kosegeni NEGATIF yapabilir; MG
# Monte Carlo negatif sacilma olasiligini ornekleyemez (olculdu, Y8: pin hucre
# CASMO-70'te MG MC -7600 pcm; random ray kosegen kararlastirmasiyla dogru).
VARSAYILAN_DUZELTME = "yok"
# MG kutuphanesi (create_mg_library) icin her zaman: toplam + sogurma +
# nu-fisyon + chi + nu-sacilma ve sacilma matrisi (cogalma matrisi).
SACILMA_TURU = "consistent nu-scatter matrix"
NUSUZ_SACILMA_TURU = "consistent scatter matrix"
ZORUNLU_TURLER = ("total", "absorption", "nu-fission", "chi", NUSUZ_SACILMA_TURU,
                  SACILMA_TURU)
SECMELI_TURLER = ("fission", "kappa-fission", "capture", "inverse-velocity",
                  "diffusion-coefficient")
TUR_ADLARI = {
    "total": N_("Toplam Σt"), "nu-transport": N_("Taşıma Σtr (P0, ν)"),
    "absorption": N_("Soğurma Σa"), "nu-fission": N_("ν-fisyon νΣf"),
    "chi": N_("Fisyon tayfı χ"), "scatter matrix": N_("Saçılma matrisi Σs(g→g')"),
    "nu-scatter matrix": N_("ν-saçılma matrisi νΣs(g→g')"),
    "consistent scatter matrix": N_("Saçılma matrisi Σs(g→g') (tutarlı)"),
    "consistent nu-scatter matrix": N_("ν-saçılma matrisi νΣs(g→g') (tutarlı)"), "fission": N_("Fisyon Σf"),
    "kappa-fission": N_("κ-fisyon κΣf [eV/cm]"), "capture": N_("Yakalama Σc"),
    "inverse-velocity": N_("Ters hız 1/v [s/cm]"),
    "diffusion-coefficient": N_("Difüzyon katsayısı D [cm]"),
}
_TUR_SIRASI = ("nu-transport",) + ZORUNLU_TURLER + SECMELI_TURLER

# Bellek tahmini: OpenMC her tally kutusu icin sum, sum_sq (+ gecici deger)
# tutar -> 3 x 8 bayt (openmc/src/tallies/tally.cpp results_ boyutu 3).
_KUTU_BAYT = 24
_P0_LEGENDRE = 2              # P0 duzeltmesi: LegendreFilter(order=1) -> 2 moment
ROOM_K = 294.0                # MG kutuphanesi sicakligi (openmc ROOM_TEMPERATURE_KELVIN)

H5_ADI, CSV_ADI, OZET_ADI = "mgxs.h5", "mgxs.csv", "mgxs_ozet.json"


@dataclass(frozen=True)
class MgxsAyar:
    var: bool = False
    bolge: str = "malzeme"
    grup_yapisi: str = VARSAYILAN_GRUP
    turler: Tuple[str, ...] = ()
    duzeltme: str = "yok"

    @property
    def etkin_turler(self) -> Tuple[str, ...]:
        """Library.mgxs_types: zorunlular + secilenler (+ P0'da nu-transport)."""
        istenen = set(ZORUNLU_TURLER) | set(self.turler)
        if self.duzeltme == "P0":
            istenen.add("nu-transport")
        return tuple(t for t in _TUR_SIRASI if t in istenen)

    @property
    def domain_turu(self) -> str:
        return BOLGELER[self.bolge]

    @property
    def openmc_duzeltme(self) -> Optional[str]:
        return "P0" if self.duzeltme == "P0" else None

    def sozluk(self) -> dict:
        return {"var": self.var, "bolge": self.bolge, "grup_yapisi": self.grup_yapisi,
                "turler": list(self.turler), "duzeltme": self.duzeltme}


def _secenek(deger: Any, gecerli: tuple, mesaj: str) -> str:
    if deger not in gecerli:
        raise ValueError(mesaj % (deger, ", ".join(gecerli)))
    return deger


def ayar(spec: Mapping) -> MgxsAyar:
    """spec["ayarlar"]["mgxs"] -> dogrulanmis MgxsAyar. Alan yoksa kapali.
    Gecersiz secenek ValueError (kapaliyken de: elle yazilmis bozuk ayar)."""
    ham = ((spec or {}).get("ayarlar") or {}).get("mgxs")
    if not isinstance(ham, Mapping):
        return MgxsAyar()
    bolge = _secenek(ham.get("bolge", "malzeme"), tuple(BOLGELER),
                     _("bilinmeyen MGXS bölge türü: %s (geçerli: %s)"))
    grup = _secenek(ham.get("grup_yapisi", VARSAYILAN_GRUP), GRUP_YAPILARI,
                    _("bilinmeyen MGXS grup yapısı: %s (geçerli: %s)"))
    duz = _secenek(ham.get("duzeltme", VARSAYILAN_DUZELTME), DUZELTMELER,
                   _("bilinmeyen taşıma düzeltmesi: %s (geçerli: %s)"))
    turler = tuple(ham.get("turler") or ())
    for t in turler:
        _secenek(t, SECMELI_TURLER + ZORUNLU_TURLER,
                 _("bilinmeyen MGXS türü: %s (geçerli: %s)"))
    return MgxsAyar(bool(ham.get("var")), bolge, grup, tuple(dict.fromkeys(turler)), duz)


def ile(spec: Mapping, a: MgxsAyar) -> dict:
    """spec'in MGXS ayari a olan YENI sig kopyasi (girdi degismez)."""
    ayarlar = dict(spec.get("ayarlar") or {})
    ayarlar["mgxs"] = a.sozluk()
    return dict(spec, ayarlar=ayarlar)


def etkin_mi(spec: Mapping) -> bool:
    """Kurucu bu spec'e MGXS tally'si ekler mi (tukenmede eklenmez)."""
    try:
        a = ayar(spec)
    except ValueError:
        return False
    return a.var and not (spec.get("tukenme") or {}).get("var")


def grup_sayisi(a: MgxsAyar) -> int:
    from openmc.mgxs import GROUP_STRUCTURES
    return len(GROUP_STRUCTURES[a.grup_yapisi]) - 1


def bellek_tahmini(a: MgxsAyar, bolge_sayisi: int) -> int:
    """MGXS tally'lerinin kaba bellek tahmini [bayt]. Baskin terim sacilma
    matrisleri: bolge x G x G (x 2 Legendre momenti P0'da) x skor."""
    g = grup_sayisi(a)
    moment = _P0_LEGENDRE if a.duzeltme == "P0" else 1
    matris = sum(1 for t in a.etkin_turler if t.endswith("matrix"))
    vektor = len(a.etkin_turler) - matris
    kutular = bolge_sayisi * (matris * g * g * moment * 2 + vektor * g * 2)
    return kutular * _KUTU_BAYT


# ----------------------------------------------------------------------------
# kutuphane (kurucu ve betik ortak parametreleri)
# ----------------------------------------------------------------------------

def domainler(a: MgxsAyar, geometri: "openmc.Geometry") -> list:
    """Deterministik bolge listesi (kimlik sirasi). Betik ayni ifadeyi yazar."""
    if a.bolge == "malzeme":
        return sorted(geometri.get_all_materials().values(), key=lambda m: m.id)
    if a.bolge == "hucre":
        return sorted(geometri.get_all_material_cells().values(), key=lambda c: c.id)
    return [geometri.root_universe]


def kutuphane_kur(a: MgxsAyar, geometri: "openmc.Geometry") -> "openmc.mgxs.Library":
    """Tally'leri kurulmus (build_library) yeni Library."""
    import openmc.mgxs
    lib = openmc.mgxs.Library(geometri)
    lib.energy_groups = openmc.mgxs.EnergyGroups(a.grup_yapisi)
    lib.mgxs_types = list(a.etkin_turler)
    lib.domain_type = a.domain_turu
    lib.domains = domainler(a, geometri)
    lib.correction = a.openmc_duzeltme
    lib.legendre_order = 0
    lib.build_library()
    return lib


def tally_ekle(spec: Mapping, model: "openmc.Model") -> Optional["openmc.mgxs.Library"]:
    """kurucu.kur kancasi. MGXS tally'leri model.tallies'e eklenir (kullanici
    tally'leriyle BIRLESTIRILMEZ); DONER Library ya da None (kapali/tukenme)."""
    if not etkin_mi(spec):
        return None
    import openmc
    lib = kutuphane_kur(ayar(spec), model.geometry)
    yeni = openmc.Tallies()
    lib.add_to_tallies(yeni, merge=True)
    model.tallies = openmc.Tallies(list(model.tallies) + list(yeni))
    return lib


def _guvenli(metin: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", metin or "")[:40].strip("_")


def xsdata_adlari(lib: "openmc.mgxs.Library") -> Dict[int, str]:
    """{domain kimligi: xsdata adi} -- HDF5 guvenli, kimlikle tekil."""
    onek = {"material": "m", "cell": "c", "universe": "u"}[lib.domain_type]
    adlar = {}
    for d in lib.domains:
        govde = _guvenli(getattr(d, "name", ""))
        adlar[d.id] = "%s%d_%s" % (onek, d.id, govde) if govde else "%s%d" % (onek, d.id)
    return adlar


def bolge_adi(domain: Any) -> str:
    ad = getattr(domain, "name", "") or ""
    tur = type(domain).__name__
    return "%s %d%s" % (tur, domain.id, (" (%s)" % ad) if ad else "")


# ----------------------------------------------------------------------------
# sonuc
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class Satir:
    """Tablo/CSV satiri: bolge, tur, gelen grup (1 = en hizli), giden grup."""
    bolge: str
    xsdata: str
    tur: str
    grup: int
    giden: Optional[int]
    deger: float
    sapma: float

    @property
    def bagil(self) -> float:
        return self.sapma / abs(self.deger) if self.deger else math.nan


@dataclass(frozen=True)
class MgxsSonuc:
    ayar: MgxsAyar
    grup_kenarlari: Tuple[float, ...]          # eV, artan
    adlar: Mapping[int, str]
    satirlar: Tuple[Satir, ...]
    k_ce: Optional[mgxs_k.Deger]
    k_oran: Optional[mgxs_k.Deger]
    k_ozdeger: Optional[mgxs_k.Deger]
    dizin: str
    notlar: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def h5(self) -> str:
        return os.path.join(self.dizin, H5_ADI)

    @property
    def csv(self) -> str:
        return os.path.join(self.dizin, CSV_ADI)


def _diziler(m: "openmc.mgxs.MGXS") -> Tuple[Any, Any]:
    import numpy as np
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)      # 0/0 (aki yok) -> nan
        ort = np.squeeze(np.asarray(m.get_xs(value="mean"), dtype=float))
        sap = np.squeeze(np.asarray(m.get_xs(value="std_dev"), dtype=float))
    return np.atleast_1d(ort), np.atleast_1d(sap)


def _satirlar(lib: "openmc.mgxs.Library", adlar: Mapping[int, str]) -> List[Satir]:
    satirlar = []
    for d in lib.domains:
        for tur in lib.mgxs_types:
            ort, sap = _diziler(lib.get_mgxs(d, tur))
            if ort.ndim == 2:
                for g in range(ort.shape[0]):
                    for h in range(ort.shape[1]):
                        satirlar.append(Satir(bolge_adi(d), adlar[d.id], tur, g + 1, h + 1,
                                              float(ort[g, h]), float(sap[g, h])))
            else:
                for g in range(ort.shape[0]):
                    satirlar.append(Satir(bolge_adi(d), adlar[d.id], tur, g + 1, None,
                                          float(ort[g]), float(sap[g])))
    return satirlar


def _hiz(lib: "openmc.mgxs.Library", tur: str) -> List[Tuple[float, float]]:
    hizlar = []
    for d in lib.domains:
        t = lib.get_mgxs(d, tur).rxn_rate_tally
        hizlar.extend(zip(t.mean.ravel().tolist(), t.std_dev.ravel().tolist()))
    return hizlar


def _sabitler(lib: "openmc.mgxs.Library", a: MgxsAyar):
    """Tek bolgenin (GrupSabitleri, GrupSapmalari, nu'suz sacilma matrisi)."""
    d = lib.domains[0]
    toplam_turu = "nu-transport" if a.duzeltme == "P0" else "total"
    alanlar = {"toplam": toplam_turu, "absorpsiyon": "absorption",
               "nu_fisyon": "nu-fission", "chi": "chi", "sacilma": SACILMA_TURU,
               "sacilma_nusuz": NUSUZ_SACILMA_TURU}
    ort, sap = {}, {}
    for alan, tur in alanlar.items():
        o, s = _diziler(lib.get_mgxs(d, tur))
        ort[alan] = tuple(map(tuple, o)) if o.ndim == 2 else tuple(o)
        sap[alan] = tuple(map(tuple, s)) if s.ndim == 2 else tuple(s)
    nusuz = ort.pop("sacilma_nusuz")
    return mgxs_k.GrupSabitleri(**ort), mgxs_k.GrupSapmalari(**sap), nusuz


def k_tahminleri(lib: "openmc.mgxs.Library", a: MgxsAyar) -> Tuple[Optional[mgxs_k.Deger],
                                                                    Optional[mgxs_k.Deger],
                                                                    Tuple[str, ...]]:
    """(k_oran, k_ozdeger, notlar). k_ozdeger yalniz tek bolgede (homojen)."""
    notlar = []
    k_oran = mgxs_k.k_oran(_hiz(lib, "nu-fission"), _hiz(lib, "absorption"))
    k_oz = None
    if len(lib.domains) == 1:
        try:
            sab, sap, nusuz = _sabitler(lib, a)
            k_oz = mgxs_k.k_ozdeger_belirsiz(sab, sap, nusuz)
        except ValueError as e:
            notlar.append(_("k∞ özdeğeri hesaplanamadı: %s") % e)
    return k_oran, k_oz, tuple(notlar)


def negatif_kosegen(lib: "openmc.mgxs.Library") -> int:
    """nu-sacilma matrisinde negatif kosegen ogesi sayisi (butun bolgeler)."""
    import numpy as np
    sayi = 0
    for d in lib.domains:
        o, _s = _diziler(lib.get_mgxs(d, SACILMA_TURU))
        if o.ndim == 2:
            sayi += int(np.sum(np.diag(o) < 0.0))
    return sayi


def csv_yaz(satirlar: Tuple[Satir, ...], yol: str, a: MgxsAyar) -> str:
    with open(yol, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["# grup_yapisi=%s duzeltme=%s bolge=%s (grup 1 = en yuksek enerji)"
                    % (a.grup_yapisi, a.duzeltme, a.bolge)])
        w.writerow(["bolge", "xsdata", "tur", "grup", "giden_grup", "deger", "sapma",
                    "bagil_sapma"])
        for s in satirlar:
            w.writerow([s.bolge, s.xsdata, s.tur, s.grup, "" if s.giden is None else s.giden,
                        "%.8e" % s.deger, "%.8e" % s.sapma, "%.4e" % s.bagil])
    return yol


def _ozet_yaz(sonuc: MgxsSonuc) -> None:
    def _d(d):
        return None if d is None else [d.ort, d.sapma]
    veri = {"ayar": sonuc.ayar.sozluk(), "grup_kenarlari": list(sonuc.grup_kenarlari),
            "adlar": {str(k): v for k, v in sonuc.adlar.items()}, "k_ce": _d(sonuc.k_ce),
            "k_oran": _d(sonuc.k_oran), "k_ozdeger": _d(sonuc.k_ozdeger),
            "notlar": list(sonuc.notlar)}
    with open(os.path.join(sonuc.dizin, OZET_ADI), "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)


def _isle(statepoint: str, spec: Mapping, dizin: str) -> MgxsSonuc:
    import openmc
    from cekirdek import kurucu
    _model, bilgi = kurucu.kur(spec)        # kimlikler kosu modeliyle ayni (reset_auto_ids)
    lib = bilgi.get("mgxs")
    if lib is None:
        raise ValueError(_("bu spec'te MGXS açık değil"))
    a = ayar(spec)
    with openmc.StatePoint(statepoint) as sp:
        k = sp.keff if sp.run_mode == "eigenvalue" else None
        with warnings.catch_warnings(record=True) as uyarilar:
            warnings.simplefilter("always")
            lib.load_from_statepoint(sp)
            adlar = xsdata_adlari(lib)
            mg = lib.create_mg_library(xs_type="macro",
                                       xsdata_names=[adlar[d.id] for d in lib.domains])
    for u in uyarilar:
        _log.info("openmc.mgxs: %s", u.message)
    mg.export_to_hdf5(os.path.join(dizin, H5_ADI))
    k_ce = None if k is None else mgxs_k.Deger(float(k.n), float(k.s))
    k_oran, k_oz, notlar = k_tahminleri(lib, a)
    negatif = negatif_kosegen(lib)
    if negatif:
        notlar = notlar + (_("%d bölge/grup için saçılma köşegeni negatif (P0 düzeltmesi): "
                             "MG Monte Carlo bunu doğru işleyemez, random ray "
                             "köşegen kararlılaştırması uygular") % negatif,)
    satirlar = tuple(_satirlar(lib, adlar))
    sonuc = MgxsSonuc(a, tuple(float(e) for e in lib.energy_groups.group_edges), adlar,
                      satirlar, k_ce, k_oran, k_oz, dizin, notlar)
    csv_yaz(satirlar, sonuc.csv, a)
    _ozet_yaz(sonuc)
    return sonuc


def isle(statepoint: str, spec: Mapping, dizin: str) -> MgxsSonuc:
    """CE statepoint -> grup sabitleri + mgxs.h5 + mgxs.csv + mgxs_ozet.json
    (dizin'e). Kuyruk iscisinden cagrilir: openmc Python API'si is parcacigi
    guvenli olmadigi icin model kurulumu kuyrugun hazirlik kilidiyle seri."""
    from cekirdek import kuyruk
    with kuyruk._HAZIRLIK_KILIDI:      # noqa: SLF001 (Y10 kilidi; bkz. kuyruk._hazirla)
        return _isle(statepoint, spec, dizin)


def ozet_oku(dizin: str) -> dict:
    """mgxs_ozet.json (MG/RR koşusu kurulurken adlar ve bolge buradan)."""
    with open(os.path.join(dizin, OZET_ADI), encoding="utf-8") as f:
        return json.load(f)
