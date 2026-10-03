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
        _mal("uco", "UCO cekirdek %19.74 U-235 (AGR-1)", 10.9,
             [_nuk("U235", 0.19944), _nuk("U238", 0.80056), _el("O", 1.5), _el("C", 0.4)], (222, 93, 40)),
        _mal("tampon", "Gozenekli karbon tampon", 1.05, [_el("C", 1.0)], (110, 110, 110),
             ["c_Graphite"]),
        _mal("pyc_ic", "IPyC", 1.90, [_el("C", 1.0)], (70, 70, 70), ["c_Graphite"]),
        _mal("sic", "SiC", 3.20, [_el("Si", 1.0), _el("C", 1.0)], (150, 190, 120)),
        _mal("pyc_dis", "OPyC", 1.91, [_el("C", 1.0)], (50, 50, 50), ["c_Graphite"]),
        _mal("matris", "Kompakt grafit matrisi", 1.40, [_el("C", 1.0)], (130, 130, 140),
             ["c_Graphite"]),
        _mal("grafit", "Nukleer grafit", 1.74, [_el("C", 1.0)], (170, 170, 175), ["c_Graphite"]),
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
    d.update(ad="HTGR kompakt (TRISO, AGR-1 olculeri)", baslik="HTGR TRISO kompakt",
             baslik_en="HTGR TRISO compact", kategori="arastirma", seviye="ileri",
             aciklama=(
                 "Silindirik TRISO yakit kompakti (AGR-1 taban parcacigi, UCO cekirdek) grafit "
                 "kilifin icinde, yansitici sinir = sonsuz kafes. Parcaciklar rastgele paketlenir "
                 "(pack_spheres) ve create_triso_lattice kafesine konur; paketleme orani %35. "
                 "Gercek HTGR blogu degildir: tek kompakt hucresi, helyum kanali yok.\n"
                 "Kaynaklar: katman olculeri INL AGR-1 taban tasarimi (Petti vd.); kompakt capi "
                 "12.45 mm, boyu 25 mm."),
             aciklama_en=(
                 "Cylindrical TRISO fuel compact (AGR-1 baseline particle, UCO kernel) in a "
                 "graphite sleeve with reflective boundaries (infinite lattice). Particles are "
                 "randomly packed (pack_spheres) at 35 % packing fraction. Not a real HTGR block: "
                 "single compact cell, no helium channel."))
    d["malzemeler"] = htgr_malzemeleri()
    t = triso.sablon("agr1", "agr1_kompakt", {"kernel": "uco", "buffer": "tampon",
                                              "ipyc": "pyc_ic", "sic": "sic", "opyc": "pyc_dis",
                                              "matris": "matris"})
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
    d["ayarlar"]["kaynak"] = dict(d["ayarlar"]["kaynak"], tur="kutu", konum=[0.0, 0.0, 0.0])
    d["ayarlar"]["kaynak"].pop("alt", None)
    d["ayarlar"]["kaynak"].pop("ust", None)
    d["calistirma"] = dict(d["calistirma"], dizin="kosu_htgr_kompakt")
    return d


def yaz(ad, d):
    yol = os.path.join(ORNEK, ad)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return yol


if __name__ == "__main__":
    print(yaz("htgr_kompakt.json", htgr_kompakt()))
