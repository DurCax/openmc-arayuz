# -*- coding: utf-8 -*-
"""Y9 ornek dosyalarini uretir (ornekler/htgr_*.json, zirh_agirlik_pencere.json).
Kullanim: python araclar/y9_ornek_uret.py  -- depo kokunden. Kaynaklar cekirdek/triso.py ve
ornek dosyalarinin aciklamalarinda."""

import copy
import json
import os

from cekirdek import triso

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORNEK = os.path.join(KOK, "ornekler")
DILIM_CM = 0.5          # eksenel dilim yuksekligi [cm]
SICAKLIK_K = 900.0     # tipik HTGR yakit sicakligi (varsayim; ornek aciklamasinda yazili)


def _mal(ad, gorunen, yogunluk, bilesim, renk, sab=(), sicaklik=SICAKLIK_K):
    return {"ad": ad, "gorunen_ad": gorunen, "yogunluk": {"birim": "g/cm3", "deger": yogunluk},
            "sicaklik": sicaklik, "bilesim": bilesim, "sab": list(sab), "renk": list(renk)}


def _el(isim, miktar, **ek):
    return dict({"tur": "element", "isim": isim, "miktar": miktar, "birim": "ao"}, **ek)


def _nuk(isim, miktar):
    return {"tur": "nuklid", "isim": isim, "miktar": miktar, "birim": "ao"}


def htgr_malzemeleri():
    return [
        _mal("uco", "UCO çekirdek %19.74 U-235 (AGR-1)", 10.9,
             [_nuk("U235", 0.19944), _nuk("U238", 0.80056), _el("O", 1.5), _el("C", 0.4)], (222, 93, 40)),
        _mal("tampon", "Gözenekli karbon tampon", 1.05, [_el("C", 1.0)], (110, 110, 110),
             ["c_Graphite"]),
        _mal("pyc_ic", "IPyC", 1.90, [_el("C", 1.0)], (70, 70, 70), ["c_Graphite"]),
        _mal("sic", "SiC", 3.20, [_el("Si", 1.0), _el("C", 1.0)], (150, 190, 120)),
        _mal("pyc_dis", "OPyC", 1.91, [_el("C", 1.0)], (50, 50, 50), ["c_Graphite"]),
        _mal("matris", "Kompakt grafit matrisi", 1.40, [_el("C", 1.0)], (130, 130, 140),
             ["c_Graphite"]),
        _mal("grafit", "Nükleer grafit", 1.74, [_el("C", 1.0)], (170, 170, 175), ["c_Graphite"]),
    ]


def _taban():
    with open(os.path.join(ORNEK, "kafes_tamburlu_yansitici.json"), encoding="utf-8") as f:
        d = json.load(f)
    for k in ("tallyler",):
        d[k] = []
    d["cubuklar"], d["plakalar"], d["demetler"], d["tamburlar"] = [], [], [], []
    d["referans"] = None
    d.pop("referans")
    return d


def htgr_kompakt():
    d = _taban()
    d.update(ad="HTGR kompakt (TRISO, AGR-1 ölçüleri)", baslik="HTGR TRISO kompakt",
             baslik_en="HTGR TRISO compact", kategori="arastirma", seviye="ileri",
             aciklama=(
                 "Silindirik TRISO yakıt kompaktı (AGR-1 taban parçacığı, UCO çekirdek) grafit "
                 "kılıfın içinde, yansıtıcı sınır = sonsuz kafes. Parçacıklar rastgele paketlenir "
                 "(pack_spheres) ve create_triso_lattice kafesine konur; paketleme oranı %35. "
                 "Gerçek HTGR bloğu değildir: tek kompakt hücresi, helyum kanalı yok.\n"
                 "Kaynaklar: katman ölçüleri INL AGR-1 taban tasarımı (Petti vd.); kompakt çapı "
                 "12.45 mm; model, z'de yansıtıcı sınırlı 5 mm'lik dilimdir (eksenel sonsuz kompakt)."),
             aciklama_en=(
                 "Cylindrical TRISO fuel compact (AGR-1 baseline particle, UCO kernel) in a "
                 "graphite sleeve with reflective boundaries (infinite lattice). Particles are "
                 "randomly packed (pack_spheres) at 35 % packing fraction. Not a real HTGR block: "
                 "single compact cell, no helium channel. The model is a 5 mm slice with reflective z faces "
                 "(an axially infinite compact)."))
    d["malzemeler"] = htgr_malzemeleri()
    t = triso.sablon("agr1", "agr1_kompakt", {"kernel": "uco", "buffer": "tampon",
                                              "ipyc": "pyc_ic", "sic": "sic", "opyc": "pyc_dis",
                                              "matris": "matris"})
    # z sinirlari yansitici: model eksenel sonsuz bir kompakti temsil eder, uzunluk k'yi
    # degistirmez; kisa dilim (5 mm, ~850 parcacik) kurulumu hizli tutar.
    t["yukseklik"] = DILIM_CM
    d["trisolar"] = [t]
    d["geometri"] = {
        "kok": {"tur": "kap", "id": "kok",
                "kesit": {"sekil": "silindir", "yaricap": t["yaricap"]},
                "ic": {"tur": "bilesen", "ad": "agr1_kompakt"}, "yerlesimler": [],
                "halkalar": [{"kalinlik": 0.30, "icerik": {"tur": "malzeme", "ad": "grafit"},
                              "yerlesimler": []}],
                "yukseklik": t["yukseklik"],
                "sinir": {"yan": "reflective", "alt": "reflective", "ust": "reflective"}},
        "parcalar": [], "gruplar": []}
    d["ayarlar"] = copy.deepcopy(d["ayarlar"])
    d["ayarlar"].update(parcacik=4000, cevrim=60, pasif=15)
    # nokta kaynak: kutu + fissionable kisiti kernel hacim oraninda (~%2.7 < OpenMC'nin %5
    # reddetme siniri) "Too few source sites" hatasi verir
    d["ayarlar"]["kaynak"] = dict(d["ayarlar"]["kaynak"], tur="nokta", konum=[0.0, 0.0, 0.0])
    d["ayarlar"]["kaynak"].pop("alt", None)
    d["ayarlar"]["kaynak"].pop("ust", None)
    d["calistirma"] = dict(d["calistirma"], dizin="kosu_htgr_kompakt")
    return d


def htgr_pebble():
    """HTR-10 pebble'i (IAEA-TECDOC-1382 olculeri) Wigner-Seitz kuresinde: 3.0 cm pebble +
    helyum kabugu (yatak paketlemesi 0.61 -> hucre yaricapi 3.0 * (1/0.61)^(1/3) = 3.54 cm),
    yansitici sinir (sonsuz yatak yaklasimi, kuresel hucre)."""
    d = _taban()
    d.update(ad="HTR-10 pebble (TRISO, Wigner–Seitz)", baslik="HTR-10 pebble",
             baslik_en="HTR-10 pebble", kategori="arastirma", seviye="ileri",
             aciklama=(
                 "HTR-10 yakıt küresi: 2.5 cm yarıçaplı yakıt kısmında ~8335 TRISO parçacığı "
                 "(UO2 çekirdek, çapı 500 µm; tampon 90, IPyC 40, SiC 35, OPyC 40 µm), 0.5 cm "
                 "grafit kabuk; çevresinde helyum kabuğu (yatağın 0.61 paketlemesine denk gelen "
                 "Wigner–Seitz hücresi) ve yansıtıcı sınır. Sonsuz yatağın küresel hücre "
                 "yaklaşımıdır; gerçek yatağın k_inf'i değildir. Kaynak: IAEA-TECDOC-1382, "
                 "HTR-10 kriterlik benchmark. Helyum yoğunluğu ideal gaz (3 MPa, 900 K)."),
             aciklama_en=(
                 "HTR-10 fuel pebble: 2.5 cm fuel zone with ~8335 TRISO particles (UO2 kernel, "
                 "500 um diameter; buffer 90, IPyC 40, SiC 35, OPyC 40 um), 0.5 cm graphite shell, "
                 "surrounded by a helium shell (Wigner-Seitz cell matching the 0.61 bed packing) "
                 "with reflective boundary. A spherical-cell approximation of the infinite "
                 "bed, not the k_inf of the real bed. Source: IAEA-TECDOC-1382 HTR-10 benchmark. "
                 "Helium density from the ideal gas law (3 MPa, 900 K)."))
    d["malzemeler"] = [
        _mal("uo2", "UO2 çekirdek %17 U-235 (HTR-10)", 10.4,
             [_nuk("U235", 0.17), _nuk("U238", 0.83), _el("O", 2.0)], (222, 93, 40)),
        _mal("tampon", "Gözenekli karbon tampon", 1.1, [_el("C", 1.0)], (110, 110, 110), ["c_Graphite"]),
        _mal("pyc_ic", "IPyC", 1.9, [_el("C", 1.0)], (70, 70, 70), ["c_Graphite"]),
        _mal("sic", "SiC", 3.18, [_el("Si", 1.0), _el("C", 1.0)], (150, 190, 120)),
        _mal("pyc_dis", "OPyC", 1.9, [_el("C", 1.0)], (50, 50, 50), ["c_Graphite"]),
        _mal("matris", "Pebble grafit matrisi", 1.73, [_el("C", 1.0)], (130, 130, 140), ["c_Graphite"]),
        _mal("grafit", "Pebble grafit kabuk", 1.73, [_el("C", 1.0)], (170, 170, 175), ["c_Graphite"]),
        _mal("helyum", "Helyum (3 MPa, 900 K)", 0.0016, [_el("He", 1.0)], (230, 230, 120)),
    ]
    d["malzemeler"][0]["bilesim"] = [_nuk("U235", 0.17 / 235.04 / (0.17 / 235.04 + 0.83 / 238.05)),
                                      _nuk("U238", 0.83 / 238.05 / (0.17 / 235.04 + 0.83 / 238.05)),
                                      _el("O", 2.0)]
    t = triso.sablon("htr10", "htr10_pebble", {"kernel": "uo2", "buffer": "tampon",
                                              "ipyc": "pyc_ic", "sic": "sic", "opyc": "pyc_dis",
                                              "matris": "matris", "kabuk": "grafit", "dis": "helyum"})
    d["trisolar"] = [t]
    kabuk_kalinlik = round(3.0 * ((1.0 / 0.61) ** (1.0 / 3.0) - 1.0), 2)
    d["geometri"] = {
        "kok": {"tur": "kap", "id": "kok", "kesit": {"sekil": "kure", "yaricap": t["dis_yaricap"]},
                "ic": {"tur": "bilesen", "ad": "htr10_pebble"}, "yerlesimler": [],
                "halkalar": [{"kalinlik": kabuk_kalinlik,
                              "icerik": {"tur": "malzeme", "ad": "helyum"}, "yerlesimler": []}],
                "yukseklik": None,
                "sinir": {"yan": "reflective", "alt": "reflective", "ust": "reflective"}},
        "parcalar": [], "gruplar": []}
    d["ayarlar"] = copy.deepcopy(d["ayarlar"])
    d["ayarlar"].update(parcacik=4000, cevrim=60, pasif=15)
    d["ayarlar"]["entropi_mesh"] = dict(d["ayarlar"].get("entropi_mesh") or {}, var=False)
    d["ayarlar"]["kaynak"] = dict(d["ayarlar"]["kaynak"], tur="nokta", konum=[0.0, 0.0, 0.0])
    d["ayarlar"]["kaynak"].pop("alt", None)
    d["ayarlar"]["kaynak"].pop("ust", None)
    d["calistirma"] = dict(d["calistirma"], dizin="kosu_htgr_pebble")
    return d


def zirh_agirlik_pencere():
    """Derin nufuz zirhi (varyans azaltma dersi): D-T kaynagi, su/celik/su katmanlari, en disi
    ayri adli (ayni bilesimli) 'dedektor' suyu; tally o malzemedeki aki."""
    with open(os.path.join(ORNEK, "zirh_kure.json"), encoding="utf-8") as f:
        d = json.load(f)
    su = next(m for m in d["malzemeler"] if m["ad"] == "su")
    dedektor = dict(copy.deepcopy(su), ad="dedektor", gorunen_ad="Dedektör suyu (H2O)",
                    renk=[60, 200, 230])
    d["malzemeler"].append(dedektor)
    d["baslik"] = "Derin nüfuz zırhı (ağırlık penceresi)"
    d["baslik_en"] = "Deep-penetration shield (weight windows)"
    d["kategori"], d["seviye"] = "zirh", "ileri"
    d["ad"] = "Derin nüfuz zırhı: su/çelik/su + dedektör (ağırlık penceresi dersi)"
    d["aciklama"] = (
        "Sabit kaynak: merkezde 14.1 MeV D-T nokta kaynağı; 35 cm su, 40 cm çelik, 30 cm su "
        "ve en dışta 5 cm'lik dedektör suyu. Tally dedektör malzemesindeki akıdır. Analog "
        "koşuda dedektöre ulaşan parçacık çok azdır; Hesap ayarları > Gelişmiş > Varyans "
        "azaltma ile MAGIC ağırlık pencereleri üretilip uygulanır ve FOM karşılaştırılır. "
        "Sonuç yanlılıksızdır: iki yöntem istatistik içinde aynı değeri verir. "
        "Sertifika değildir; ölçülen FOM ders 5.21'de yazılıdır.")
    d["aciklama_en"] = (
        "Fixed source: a 14.1 MeV D-T point source at the centre; 35 cm water, 40 cm steel, "
        "30 cm water and a 5 cm detector water shell at the outside. The tally is the flux in the "
        "detector material. In an analog run very few particles reach the detector; generate and "
        "apply MAGIC weight windows under Settings > Advanced > Variance reduction and compare "
        "the FOM. The result is unbiased: both methods agree within statistics. Not a "
        "certification.")
    d["kor"]["kabuklar"] = [{"r": 35.0, "malzeme": "su"}, {"r": 75.0, "malzeme": "celik"},
                            {"r": 105.0, "malzeme": "su"}, {"r": 110.0, "malzeme": "dedektor"}]
    d["tallyler"] = [{"ad": "aki_dedektor", "skorlar": ["flux"], "nuklidler": [],
                      "filtreler": [{"tur": "malzeme", "adlar": ["dedektor"]}]}]
    d["ayarlar"]["parcacik"], d["ayarlar"]["cevrim"] = 20000, 40
    d["calistirma"] = dict(d["calistirma"], dizin="kosu_zirh_agirlik")
    return d


def yaz(ad, d):
    yol = os.path.join(ORNEK, ad)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return yol


if __name__ == "__main__":
    print(yaz("htgr_kompakt.json", htgr_kompakt()))
    print(yaz("htgr_pebble.json", htgr_pebble()))
    print(yaz("zirh_agirlik_pencere.json", zirh_agirlik_pencere()))
