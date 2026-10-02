# -*- coding: utf-8 -*-
"""
 test_k6_pnnl.py  --  v3 K6: PNNL-15870 malzeme derlemesi ICE AKTARIMI
                      (cekirdek/malzeme_pnnl.py)

 LISANS: PNNL-15870 (Rev.1 2011, Rev.2 2021) acik bir lisans ya da kamu malı
 beyani tasimiyor (yalnizca DOE/Battelle sorumluluk reddi; 02.10.2026'da
 OSTI ve rapor PDF'inde denetlendi). Bu yuzden veri programla DAGITILMAZ;
 kullanicinin kendi indirdigi CSV'den (PNNL Rev.1 Excel cikisi; PyNE
 materials_compendium.csv ile ayni bicim) ice aktarilir.

 Asagidaki CSV parcasi o bicimin SENTETIK bir ornegidir (degerler kurmaca,
 PNNL verisi degildir).
"""

import os
import tempfile

import pytest

from testler.ortak_test import KOK  # noqa: F401

_ORNEK = '''"1.  ","Deneme Plastigi (DP)",,,,,
"Formula =","-",,,"Molecular weight (g/mole) =",,"-"
"Density (g/cm3) =",,1.250000,,"Total atoms/b-cm =",,1.000E-01
"The above density is estimated to be accurate to 4 significant digits.",,,,,,
"The following data was calculated from the input weight fractions.",,,,,,
,,,,,,
,,,"Weight","Atom","Atom",
"Element","Neutron ZA","Photon ZA","Fraction","Fraction","Density",
"H",1001,1000,0.100000,0.500000,0.050000,
"C",6000,6000,0.600000,0.400000,0.040000,
"AL",13027,13000,0.300000,0.100000,0.010000,
,,,,,,
"Total",,,1.000000,1.000000,0.100000,
,,,,,,
"MCNP Form","Weight Fractions",,"Atom Fractions",,"Atom Densities",
"Neutrons",1001,-0.100000,1001,0.500000,1001,0.050000
,,,,,,
,"matname","Deneme Plastigi (DP)",,,,
,"density",1.250000,,,,
"Comments & references:",,,,,,
"Kurmaca kaynak satiri bir.",,,,,,
"Kurmaca kaynak satiri iki.",,,,,,
0,,,,,,
"Baska malzemenin yorumu.",,,,,,
,,,,,,
"2.  ","Uranyum Oksit Denemesi",,,,,
"Formula =","U3O8",,"Molecular weight (g/mole) =","Molecular weight (g/mole) =",,841.87
"Density (g/cm3) =",,8.300000,"Total atom density (atoms/b-cm) =",,,6.531E-02
,,,"Weight","Atom","Atom",
"Element","Neutron ZA","Photon ZA","Fraction","Fraction","Density",
"O",8016,8000,0.152000,0.727000,0.047000,
"U-235",92235,92000,0.025000,0.008000,0.000500,
"U-238",92238,92000,0.823000,0.265000,0.017000,
"Total",,,1.000000,1.000000,0.065000,
,"matname","Uranyum Oksit Denemesi",,,,
"Comments & references:",,,,,,
"Kurmaca.",,,,,,
"3.  ","Bozuk Kayit",,,,,
"Formula =","-",,,,,
"Density (g/cm3) =",,abc,,,,
"Element","Neutron ZA","Photon ZA","Fraction","Fraction","Density",
"Xx",1,1,0.5,0.5,0.1,
"Total",,,1.0,1.0,0.1,
'''


def _dosya(icerik=_ORNEK):
    yol = os.path.join(tempfile.mkdtemp(prefix="k6_pnnl_"), "materials_compendium.csv")
    with open(yol, "w", encoding="latin-1") as f:
        f.write(icerik)
    return yol


def test_csv_okunur_malzemeler_ve_sorunlar():
    from cekirdek import malzeme_pnnl as mp
    malz, sorunlar = mp.oku(_dosya())
    assert [m["no"] for m in malz] == [1, 2]
    dp = malz[0]
    assert dp["ad"] == "Deneme Plastigi (DP)" and dp["formul"] is None
    assert dp["yogunluk"] == pytest.approx(1.25)
    assert dp["bilesim"] == (("H", "element", 0.1), ("C", "element", 0.6), ("Al", "element", 0.3))
    assert dp["kaynak"] == "Kurmaca kaynak satiri bir. Kurmaca kaynak satiri iki."
    u = malz[1]
    assert u["formul"] == "U3O8"
    assert ("U235", "nuklid", 0.025) in u["bilesim"]
    # bozuk 3. kayit atlanir ama SESSIZ degil: sorun listesinde
    assert len(sorunlar) == 1 and "3" in sorunlar[0]


def test_ara_ad_ve_formulde_buyuk_kucuk_harf_duyarsiz():
    from cekirdek import malzeme_pnnl as mp
    malz, _s = mp.oku(_dosya())
    assert [m["no"] for m in mp.ara(malz, "plastiğ")] == []          # tr harf: eslesmez
    assert [m["no"] for m in mp.ara(malz, "PLASTIG")] == [1]
    assert [m["no"] for m in mp.ara(malz, "u3o8")] == [2]
    assert len(mp.ara(malz, "")) == 2


def test_malzemeye_cevir_sema_bicimi_ve_kurulabilir():
    import openmc
    from cekirdek import malzeme_pnnl as mp
    from cekirdek import malzeme_kullanici as mku
    malz, _s = mp.oku(_dosya())
    m = mp.malzemeye_cevir(malz[1], ad="u3o8")
    assert mku.malzeme_sorunu(m) is None
    assert m["yogunluk"] == {"birim": "g/cm3", "deger": 8.3}
    assert {s["birim"] for s in m["bilesim"]} == {"wo"}
    assert sum(s["miktar"] for s in m["bilesim"]) == pytest.approx(100.0)
    o = openmc.Material()
    for s in m["bilesim"]:
        if s["tur"] == "nuklid":
            o.add_nuclide(s["isim"], s["miktar"], "wo")
        else:
            o.add_element(s["isim"], s["miktar"], "wo", cross_sections=None)
    o.set_density("g/cm3", 8.3)
    assert o.get_mass_density() == pytest.approx(8.3)


def test_dosya_yok_ya_da_bicim_disi_acik_hata():
    from cekirdek import malzeme_pnnl as mp
    with pytest.raises(mp.PnnlHatasi):
        mp.oku("/yok/boyle/bir/dosya.csv")
    with pytest.raises(mp.PnnlHatasi):
        mp.oku(_dosya("a,b,c\n1,2,3\n"))


HIZLI = [test_csv_okunur_malzemeler_ve_sorunlar, test_ara_ad_ve_formulde_buyuk_kucuk_harf_duyarsiz,
         test_malzemeye_cevir_sema_bicimi_ve_kurulabilir, test_dosya_yok_ya_da_bicim_disi_acik_hata]
