# -*- coding: utf-8 -*-
"""
vv/lct008.py -- LEU-COMP-THERM-008 (B&W Core XI) ek durumlari (v3 Y11).

KAYNAK: mit-crpg/benchmarks (MIT lisansi, (c) 2011-2024 Paul Romano ve katkida
bulunanlar) icsbep/leu-comp-therm-008/openmc/case-N girdileri; E +- sigma ayni
deponun uncertainties.csv tablosundan (butun durumlar 1.0007 +- 0.0012).
Depoda OpenMC modeli olan durumlar: 1, 2, 5, 7, 8, 11. Durum 1 v2'de
ornekler/kriter_lct008.json olarak vardir ve SABLON olarak kullanilir: ayni
cubuk, tank ve kafes; durumlar yalniz su boru, cubuk haritasi ve pertürbe
cubuklar (pyrex: 5, 7, 8; Al2O3: 11) ile ayrilir.

  DURUMLAR                                  -> {no: alt dizin}
  harita_uret(bulucu, n, adim)              -> [str] (ilk satir en ust, +y)
  spec_olustur(sablon, no, su, ek, harita)  -> YENI spec (saf; sablon degismez)
  birim_hucre_h_x(spec)                     -> H / U-235 (kafes birim hucresi)
  spec(depo, no)                            -> spec (mit-crpg girdilerini okur)
"""

import copy
import math
import os
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from cekirdek.ceviri import _

SERI = "LEU-COMP-THERM-008"
E, SIGMA_E = 1.0007, 0.0012                      # mit-crpg uncertainties.csv
# Durum 1 de yeniden uretilir (ornekler/vv/kriter_lct008_01.json): v2 dosyasi
# (ornekler/kriter_lct008.json) AOA'da h_x tasimaz; V&V kumesinde onun yerine
# bu dosya kullanilir (cekirdek/vv/kume.py VV_YERINE).
DURUMLAR = {1: "case-1", 2: "case-2", 5: "case-5", 7: "case-7", 8: "case-8", 11: "case-11"}
N_KAFES, ADIM = 93, 1.63576                      # sablonla ayni (kriter_lct008.json)
SABLON = "kriter_lct008.json"
# mit-crpg geometry.xml evren kimligi -> harita harfi
# DISARIDA: konum merkezi tankin (r = 76.2 cm) disinda -- sablonda da su ('s'),
# tank siniri spec'te ayrica kesilir.
DISARIDA = -1
EVREN_HARF = {DISARIDA: "s", 1: "s", 2: "y", 3: "p", 5: "a"}
# mit-crpg geometry.xml yuzeyleri 3 (pyrex OR), 6/7 (Al2O3 OR / kilif OR) [cm]
PERTURBE = {"p": ("pyrex_cubugu", ((0.585, "pyrex"), (None, "su_borlu"))),
            "a": ("al2o3_cubugu", ((0.4665, "al2o3"), (0.5555, "al2o3_kilif"),
                                   (None, "su_borlu")))}
# mit-crpg materials.xml malzeme kimligi -> spec malzeme adi (1 su, 2 yakit, 3 kilif sablonda)
MALZEME_ADI = {4: {"p": "pyrex", "a": "al2o3"}, 5: {"a": "al2o3_kilif"}}
RENK = {"pyrex": [240, 200, 60], "al2o3": [200, 200, 200], "al2o3_kilif": [150, 150, 160]}
SICAKLIK_K = 293.6
KOSU = {"parcacik": 100000, "cevrim": 200, "pasif": 50}   # sigma_c ~ 24 pcm (<= 30 pcm)
KAYNAK_MODEL = ("mit-crpg/benchmarks (MIT lisansı) icsbep/leu-comp-therm-008/openmc/%s; "
                "E ± σ: aynı depo icsbep/icsbep/uncertainties.csv (ICSBEP değeri)")
LISANS = ("Model girdisi MIT lisanslıdır; ICSBEP el kitabı metni yeniden dağıtılmaz, "
          "yalnız açık model ve yayımlanmış E ± σ kullanılır (STANDARTLAR.md §6 md. 13).")


def harita_uret(bulucu: Callable[[float, float], int], n: int = N_KAFES,
                adim: float = ADIM) -> List[str]:
    """bulucu(x, y) -> evren kimligi; kafes konum merkezlerinde sorgulanir."""
    satirlar = []
    for j in range(n):
        y = (0.5 * (n - 1) - j) * adim
        satir = []
        for i in range(n):
            x = (i - 0.5 * (n - 1)) * adim
            evren = bulucu(x, y)
            if evren not in EVREN_HARF:
                raise ValueError(_("LCT-008 haritası: (%.3f, %.3f) konumunda bilinmeyen "
                                   "evren %r") % (x, y, evren))
            satir.append(EVREN_HARF[evren])
        satirlar.append("".join(satir))
    return satirlar


def _malzeme(ad: str, bilesim: Sequence[Tuple[str, float]], sab: Sequence[str] = ()) -> dict:
    return {"ad": ad, "gorunen_ad": ad, "sicaklik": SICAKLIK_K, "sab": list(sab),
            "yogunluk": {"birim": "atom/b-cm", "deger": float(sum(d for _n, d in bilesim))},
            "bilesim": [{"tur": "nuklid", "isim": n, "miktar": float(d), "birim": "ao"}
                        for n, d in bilesim],
            "renk": list(RENK.get(ad, [128, 128, 128]))}


def _su(eski: Mapping, bilesim: Sequence[Tuple[str, float]], b_ppm: str) -> dict:
    yeni = _malzeme(eski["ad"], bilesim, eski.get("sab") or ())
    return dict(yeni, gorunen_ad="Su, %s ppm B" % b_ppm, renk=list(eski.get("renk") or []),
                sicaklik=eski.get("sicaklik", SICAKLIK_K))


def _ppm(su: Sequence[Tuple[str, float]]) -> str:
    """Bilgi icin: B kutlesi / su kutlesi (ppm)."""
    kutle = {"H1": 1.008, "O16": 15.995, "B10": 10.013, "B11": 11.009}
    toplam = sum(kutle.get(n, 0.0) * d for n, d in su)
    bor = sum(kutle[n] * d for n, d in su if n in ("B10", "B11"))
    return "%.0f" % (1e6 * bor / toplam) if toplam else "?"


def _cubuklar(sablon: Mapping, harfler: set) -> list:
    cubuklar = copy.deepcopy(list(sablon.get("cubuklar") or []))
    for harf in sorted(harfler & set(PERTURBE)):
        ad, bolgeler = PERTURBE[harf]
        cubuklar.append({"ad": ad, "tur": "silindirik",
                         "bolgeler": [{"r": r, "malzeme": m} for r, m in bolgeler]})
    return cubuklar


def spec_olustur(sablon: Mapping, no: int, su: Sequence[Tuple[str, float]],
                 ek_malzemeler: Mapping[str, Sequence[Tuple[str, float]]],
                 harita: Sequence[str]) -> dict:
    """Durum 1 sablonundan durum no spec'i (YENI; sablon degismez)."""
    if no not in DURUMLAR:
        raise ValueError(_("bilinmeyen LCT-008 durumu: %r") % (no,))
    spec = copy.deepcopy(dict(sablon))
    harfler = set("".join(harita))
    malzemeler = [(_su(m, su, _ppm(su)) if m["ad"] == "su_borlu" else m)
                  for m in spec["malzemeler"]]
    malzemeler += [_malzeme(ad, b) for ad, b in sorted(ek_malzemeler.items())]
    demet = dict(spec["demetler"][0], harita=list(harita))
    demet["anahtar"] = dict(demet["anahtar"], **{h: PERTURBE[h][0]
                                                for h in sorted(harfler & set(PERTURBE))})
    spec.update(malzemeler=malzemeler, demetler=[demet] + spec["demetler"][1:],
                cubuklar=_cubuklar(sablon, harfler))
    spec["ayarlar"] = dict(spec["ayarlar"], **KOSU)
    from cekirdek.vv import aoa
    spec["tallyler"] = [aoa.ealf_tally_tanimi()]     # tayf (AOA) icin EALF
    _metinler(spec, no, harfler, _ppm(su))
    spec["referans"] = _referans(no, birim_hucre_h_x(spec))
    return spec


def _metinler(spec: dict, no: int, harfler: set, ppm: str) -> None:
    ek = {"p": "pyrex çubukları", "a": "Al2O3 çubukları"}
    ek_en = {"p": "pyrex rods", "a": "Al2O3 rods"}
    pert = ", ".join(ek[h] for h in sorted(harfler & set(ek))) or "pertürbe çubuk yok"
    pert_en = ", ".join(ek_en[h] for h in sorted(harfler & set(ek_en))) or "no perturbing rods"
    n_yakit = sum(s.count("y") for s in spec["demetler"][0]["harita"])
    spec["ad"] = "%s, durum %d" % (SERI, no)
    spec["baslik"] = "B&W kritik kafesi (LCT-008, durum %d)" % no
    spec["baslik_en"] = "B&W critical lattice (LCT-008, case %d)" % no
    spec["aciklama"] = (
        "ICSBEP kriteri %s, durum %d (B&W Core XI): %d UO2 çubuğu (%%2.459), %s ppm borlu "
        "su, %s. Deneysel kriter değeri k = %.4f ± %.4f.\nModel: mit-crpg/benchmarks "
        "icsbep/leu-comp-therm-008/openmc/%s (MIT lisansı); çubuk haritası özgün geometriden "
        "nokta sorgusuyla, atom yoğunlukları kayıpsız aktarıldı. Durum 1 ile aynı tank ve "
        "çubuk (ornekler/kriter_lct008.json)." % (SERI, no, n_yakit, ppm, pert, E, SIGMA_E,
                                                   DURUMLAR[no]))
    spec["aciklama_en"] = (
        "ICSBEP benchmark %s case %d (B&W Core XI): %d UO2 pins (2.459 wt%%), %s ppm borated "
        "water, %s; k-eff = %.4f ± %.4f; model from mit-crpg/benchmarks (MIT license)."
        % (SERI, no, n_yakit, ppm, pert_en, E, SIGMA_E))


def _referans(no: int, h_x: float) -> dict:
    return {"k": E, "sigma": SIGMA_E, "tur": "deney", "seri": SERI,
            "kaynak": "ICSBEP %s, durum %d (B&W Core XI)" % (SERI, no),
            "kaynak_model": KAYNAK_MODEL % DURUMLAR[no], "lisans": LISANS,
            "aoa_girdi": {"fiziksel_bicim": "oksit", "yansitici": "su", "h_x": round(h_x, 6),
                          "h_x_not": "birim hücre H/U-235 (heterojen)"}}


def _yogunluk(spec: Mapping, ad: str, nuklid: str) -> float:
    for m in spec["malzemeler"]:
        if m["ad"] == ad:
            return sum(b["miktar"] for b in m["bilesim"] if b["isim"] == nuklid)
    raise ValueError(_("malzeme yok: %s") % ad)


def birim_hucre_h_x(spec: Mapping) -> float:
    """H / U-235: (p² - π r_kilif²) N_H / (π r_yakit² N_U235); yakit_cubugu tanimindan."""
    cubuk = [c for c in spec["cubuklar"] if c["ad"] == "yakit_cubugu"][0]
    r_yakit, r_kilif = cubuk["bolgeler"][0]["r"], cubuk["bolgeler"][1]["r"]
    adim = spec["demetler"][0]["adim"]
    v_su = adim ** 2 - math.pi * r_kilif ** 2
    v_yakit = math.pi * r_yakit ** 2
    su = cubuk["bolgeler"][-1]["malzeme"]
    yakit = cubuk["bolgeler"][0]["malzeme"]
    return v_su * _yogunluk(spec, su, "H1") / (v_yakit * _yogunluk(spec, yakit, "U235"))


def _mitcrpg_malzemeler(mats: Any) -> Dict[int, List[Tuple[str, float]]]:
    return {m.id: sorted((n, float(d)) for n, d in m.get_nuclide_atom_densities().items())
            for m in mats}


def _oku_mitcrpg(dizin: str) -> Tuple[Any, Callable[[float, float], int]]:
    """(openmc.Materials, bulucu): malzemeler BIR KEZ okunur (kimlik cakismasi uyarisi yok)."""
    import openmc
    openmc.reset_auto_ids()
    mats = openmc.Materials.from_xml(os.path.join(dizin, "materials.xml"))
    geo = openmc.Geometry.from_xml(os.path.join(dizin, "geometry.xml"), mats)

    def bul(x: float, y: float) -> int:
        yol = geo.find((x, y, 0.0))
        return yol[-2].id if len(yol) >= 2 else DISARIDA     # en icteki evren
    return mats, bul


def spec(depo: str, no: int) -> dict:
    """mit-crpg/benchmarks dizininden durum no spec'i (sablon: ornekler/kriter_lct008.json)."""
    import json
    from cekirdek import yollar
    if no not in DURUMLAR:
        raise ValueError(_("bilinmeyen LCT-008 durumu: %r") % (no,))
    dizin = os.path.join(depo, "icsbep", "leu-comp-therm-008", "openmc", DURUMLAR[no])
    with open(os.path.join(yollar.ornekler_dizini(), SABLON), encoding="utf-8") as f:
        sablon = json.load(f)
    openmc_mats, bulucu = _oku_mitcrpg(dizin)
    mats = _mitcrpg_malzemeler(openmc_mats)
    harita = harita_uret(bulucu)
    harfler = set("".join(harita))
    ek = {}
    for kimlik, adlar in MALZEME_ADI.items():
        for harf, ad in adlar.items():
            if harf in harfler and kimlik in mats:
                ek[ad] = mats[kimlik]
    return spec_olustur(sablon, no, mats[1], ek, harita)
