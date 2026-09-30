# -*- coding: utf-8 -*-
"""
 test_geometri_genislet.py  --  G-1: sablon -> agac genisletici (§6)

 27 ornekte genislet hatasiz, SAF (girdi degismez) ve yapisal denetimden
 temiz; turetilmis "_" alanlari diske yazilmaz.
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri).
"""

import copy
import glob
import json
import os
import tempfile

from testler.ortak_test import kontrol, ORNEK


def _ornekler():
    from cekirdek import sema
    return [(os.path.basename(p)[:-5], sema.yukle(p))
            for p in sorted(glob.glob(os.path.join(ORNEK, "*.json")))]


def test_genislet_27_ornek():
    print("\n[GG1] genislet: 27 ornek hatasiz, saf, yapisal denetimden temiz")
    from cekirdek import geometri
    ornekler = _ornekler()
    kontrol("27 ornek", len(ornekler) == 27)
    for ad, spec in ornekler:
        once = copy.deepcopy(spec)
        agac = geometri.genislet(spec)
        hatalar = [b for b in geometri.yapisal_denetim(spec) if b.seviye == "hata"]
        kontrol("%s: saf, kok kap, hata yok" % ad,
                spec == once and agac["kok"]["tur"] == "kap" and not hatalar,
                "-> %s" % [str(b) for b in hatalar[:2]])
        agac["kok"]["id"] = "degisti"
        kontrol("%s: sonuc kopya (ikinci cagri etkilenmez)" % ad,
                geometri.genislet(spec)["kok"]["id"] == "kok")


def test_genislet_sablon_ozellikleri():
    print("\n[GG2] genislet: tamburlu -> halka yerlesimi + donme grubu; kuresel; altigen R3b")
    from cekirdek import geometri, sema
    t = sema.yukle(os.path.join(ORNEK, "tamburlu_kor.json"))
    a = geometri.genislet(t)
    y = a["kok"]["halkalar"][0]["yerlesimler"][0]
    kontrol("tamburlu: 8 tamburluk halka yerlesimi", y["mod"] == "halka" and y["sayi"] == 8)
    kontrol("tamburlu: grup degeri = kor.tambur.donme",
            a["gruplar"] == [{"ad": "tamburlar", "tur": "donme", "deger": 180.0,
                              "uyeler": ["tamburlar"]}])
    kontrol("tamburlu: uretilen tambur tanimi",
            a["_uretilen_tanimlar"]["tamburlar"][0]["ad"] == "tambur")
    g = sema.yukle(os.path.join(ORNEK, "godiva_kriter.json"))
    kontrol("kuresel: kok kesiti kure, 2B", geometri.genislet(g)["kok"]["kesit"]["sekil"] == "kure"
            and geometri.genislet(g)["kok"]["yukseklik"] is None)
    v = sema.yukle(os.path.join(ORNEK, "vver1000_kor.json"))
    va = geometri.genislet(v)
    kontrol("altigen_kafes: kafes_zarfi + eksenel yigin + altigen yansitici halkasi",
            va["kok"]["kesit"] == {"sekil": "kafes_zarfi"}
            and va["kok"]["ic"]["tur"] == "eksenel"
            and va["kok"]["halkalar"][0]["dis"]["sekil"] == "altigen")
    kontrol("model yuksekligi = kor_yuksekligi (vver1000)",
            geometri.yukseklik(geometri.model(v)) == sema.kor_yuksekligi(v["kor"]))


def test_turetilmis_alan_diske_yazilmaz():
    print("\n[GG3] agac modunda kaydet: '_' ile baslayan alanlar yazilmaz")
    from cekirdek import geometri, sema
    t = sema.yukle(os.path.join(ORNEK, "tamburlu_kor.json"))
    agac_spec = copy.deepcopy(t)
    agac_spec["geometri"] = geometri.genislet(t)
    agac_spec["kor"] = {"tur": "agac"}
    agac_spec["tamburlar"] = agac_spec["geometri"]["_uretilen_tanimlar"]["tamburlar"]
    d = tempfile.mkdtemp(prefix="gg3_")
    yol = sema.kaydet(agac_spec, os.path.join(d, "a.json"))
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    kontrol("_kutu / _sablon yazilmadi", "_kutu" not in metin and "_sablon" not in metin)
    geri = sema.yukle(yol)
    kontrol("geri yuklenen agac modunda, kor yalniz tur",
            geri["kor"] == {"tur": "agac"} and geri["geometri"]["kok"]["tur"] == "kap")
    kontrol("json gecerli", isinstance(json.loads(metin), dict))
    g = geometri.gelismise_gec(t)
    kontrol("gelismise_gec: saf, tambur kutuphanede, '_' yok",
            t["kor"]["tur"] == "tamburlu" and g["kor"] == {"tur": "agac"}
            and [x["ad"] for x in g["tamburlar"]] == ["tambur"]
            and "_kutu" not in json.dumps(g["geometri"]))
    kontrol("gelismise_gec: yapisal denetim temiz",
            not [b for b in geometri.yapisal_denetim(g) if b.seviye == "hata"])


HIZLI = [test_genislet_27_ornek, test_genislet_sablon_ozellikleri,
         test_turetilmis_alan_diske_yazilmaz]
YAVAS = []
