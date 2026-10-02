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


def _kayit(no, ad, yogunluk, satirlar, yorum=()):
    metin = ['"%d.  ","%s",,,,,' % (no, ad), '"Formula =","-",,,,,',
             '"Density (g/cm3) =",,%s,,,,' % yogunluk,
             '"Element","Neutron ZA","Photon ZA","Fraction","Fraction","Density",']
    metin += ['"%s",1,1,%s,0.5,0.1,' % (e, w) for e, w in satirlar]
    metin += ['"Total",,,1.0,1.0,0.1,', '"Comments & references:",,,,,,']
    metin += ['"%s",,,,,,' % y for y in yorum] + ["0,,,,,,"]
    return "\n".join(metin) + "\n"


def test_nan_negatif_toplam_ve_yinelenen_kayitlar_atlanir():
    from cekirdek import malzeme_pnnl as mp
    icerik = (_kayit(1, "Iyi", "1.0", [("H", "0.5"), ("O", "0.5")])
              + _kayit(2, "NaN agirlik", "1.0", [("H", "nan"), ("O", "0.5")])
              + _kayit(3, "Negatif", "1.0", [("H", "-0.5"), ("O", "1.5")])
              + _kayit(4, "Sonsuz yogunluk", "inf", [("H", "1.0")])
              + _kayit(5, "Asiri yogun", "45.0", [("H", "1.0")])
              + _kayit(6, "Toplam 0.99", "1.0", [("H", "0.49"), ("O", "0.50")])
              + _kayit(1, "Yinelenen", "1.0", [("H", "1.0")]))
    malz, sorunlar = mp.oku(_dosya(icerik))
    assert [m["ad"] for m in malz] == ["Iyi"]
    assert len(sorunlar) == 6
    assert any("toplam" in s for s in sorunlar) and any("daha önce" in s for s in sorunlar)


def test_yorumdaki_numara_sahte_kayit_acmaz():
    from cekirdek import malzeme_pnnl as mp
    icerik = (_kayit(1, "Bir", "1.0", [("H", "1.0")], yorum=("12.  ", "Kaynak metni."))
              + _kayit(2, "Iki", "2.0", [("O", "1.0")]))
    malz, sorunlar = mp.oku(_dosya(icerik))
    assert [m["no"] for m in malz] == [1, 2] and not sorunlar
    assert "Kaynak metni." in malz[0]["kaynak"]


def test_boyut_ve_bilesen_sinirlari(monkeypatch):
    from cekirdek import malzeme_pnnl as mp
    yol = _dosya(_kayit(1, "A", "1.0", [("H", "0.5"), ("O", "0.3"), ("C", "0.2")]))
    monkeypatch.setattr(mp, "AZAMI_BILESEN", 2)
    with pytest.raises(mp.PnnlHatasi):
        mp.oku(yol)
    monkeypatch.setattr(mp, "AZAMI_BOYUT", 10)
    with pytest.raises(mp.PnnlHatasi, match="büyük"):
        mp.oku(yol)


def test_utf8_bom_okunur(tmp_path):
    from cekirdek import malzeme_pnnl as mp
    yol = tmp_path / "pnnl.csv"
    yol.write_bytes(_kayit(7, "Çelik ünlü", "7.9", [("Fe", "1.0")]).encode("utf-8-sig"))
    malz, _s = mp.oku(str(yol))
    assert malz[0]["ad"] == "Çelik ünlü" and malz[0]["no"] == 7


HIZLI = [test_csv_okunur_malzemeler_ve_sorunlar, test_ara_ad_ve_formulde_buyuk_kucuk_harf_duyarsiz,
         test_malzemeye_cevir_sema_bicimi_ve_kurulabilir, test_dosya_yok_ya_da_bicim_disi_acik_hata,
         test_nan_negatif_toplam_ve_yinelenen_kayitlar_atlanir, test_yorumdaki_numara_sahte_kayit_acmaz,
         test_boyut_ve_bilesen_sinirlari, test_utf8_bom_okunur]
