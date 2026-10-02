# -*- coding: utf-8 -*-
"""
 test_k6_tarif.py  --  v3 K6: malzeme asistani tarifleri ve dogrulama adimi
                       (cekirdek/malzeme_tarif.py)

 KABUL: asistanla kurulan UO2 = katalog UO2 (bilesim, yogunluk, sicaklik, S(a,b)
 ve OpenMC'nin hesapladigi nuklid yogunluklari birebir). k aynılığı YAVAS
 testte kisa bir Monte Carlo kosusuyla (ayni tohum) denetlenir.
"""

import os
import tempfile
from unittest import mock

import pytest

from testler.ortak_test import KOK, ISLEM_PARCACIGI  # noqa: F401


def _openmc_yogunluklari(m):
    from cekirdek import kurucu
    nesneler, _mats, _renk = kurucu.malzemeleri_kur({"malzemeler": [m]})
    return nesneler[m["ad"]].get_nuclide_atom_densities()


def test_kategoriler_ve_her_tarif_varsayilanla_gecerli():
    from cekirdek import malzeme_tarif as mt
    from cekirdek import malzeme_hesap as mh
    from cekirdek import malzeme_kullanici as mku
    assert [k for k, _e in mt.KATEGORILER] == ["yakit", "kilif", "moderator", "emici",
                                               "yapi", "ozel"]
    for kat, _e in mt.KATEGORILER:
        if kat == "ozel":
            continue
        assert mt.tarifler(kat), kat
        for anahtar in mt.tarifler(kat):
            m = mt.uret(anahtar, mt.varsayilanlar(anahtar))
            assert mku.malzeme_sorunu(m) is None, anahtar
            assert mh.turetilmis(m)["N_toplam"] > 0, anahtar
            assert all(a["etiket"] for a in mt.alanlar(anahtar)), anahtar


def test_asistan_uo2_katalog_uo2_ile_ayni():
    from cekirdek import malzeme_tarif as mt
    from cekirdek import malzeme_kutup as mk
    from cekirdek import kurucu
    katalog = mk.uo2(zenginlik=3.2, yogunluk=10.40, sicaklik=900.0)
    asistan = mt.uret("uo2", {"zenginlik": 3.2, "yogunluk_yolu": "dogrudan",
                              "yogunluk": 10.40, "sicaklik": 900.0})
    for alan in ("bilesim", "yogunluk", "sicaklik", "sab"):
        assert asistan[alan] == katalog[alan], alan
    asistan["ad"] = katalog["ad"]
    assert _openmc_yogunluklari(asistan) == _openmc_yogunluklari(katalog)
    nesne = kurucu.malzemeleri_kur({"malzemeler": [asistan]})[0][katalog["ad"]]
    assert nesne.temperature == 900.0


def test_uo2_td_yolu_ve_om():
    from cekirdek import malzeme_tarif as mt
    m = mt.uret("uo2", {"zenginlik": 4.95, "yogunluk_yolu": "td", "td_yuzde": 95.0,
                        "om": 2.0, "sicaklik": 900.0})
    assert m["yogunluk"]["deger"] == pytest.approx(0.95 * 10.97)          # 10.4215
    m = mt.uret("uo2", dict(mt.varsayilanlar("uo2"), om=2.01))
    assert [b["miktar"] for b in m["bilesim"]] == [1.0, 2.01]
    with pytest.raises(ValueError, match="O/M"):
        mt.uret("uo2", dict(mt.varsayilanlar("uo2"), om=3.5))


def test_hafif_su_if97_ve_bor():
    from cekirdek import malzeme_tarif as mt
    from cekirdek import malzeme_hesap as mh
    from cekirdek import malzeme_sogutucu as ms
    m = mt.uret("h2o", {"sicaklik": 580.0, "basinc": 15.5, "bor_ppm": 1000.0,
                        "b10_yuzde": None})
    assert m["yogunluk"]["deger"] == pytest.approx(ms.su_yogunlugu(580.0, 15.5), rel=1e-12)
    assert m["bilesim"] == mh.borlu_su_bilesimi(1000.0)
    assert m["sab"] == ["c_H_in_H2O"]
    z = mt.uret("h2o", {"sicaklik": 580.0, "basinc": 15.5, "bor_ppm": 1000.0,
                        "b10_yuzde": 90.0})
    assert {b["isim"] for b in z["bilesim"]} == {"H", "O", "B10", "B11"}
    saf = mt.uret("h2o", {"sicaklik": 300.0, "basinc": 0.1, "bor_ppm": 0.0, "b10_yuzde": None})
    assert [(b["isim"], b["miktar"]) for b in saf["bilesim"]] == [("H", 2.0), ("O", 1.0)]
    with pytest.raises(ValueError, match="buhar"):
        mt.uret("h2o", {"sicaklik": 600.0, "basinc": 5.0, "bor_ppm": 0.0, "b10_yuzde": None})


def test_agir_su_sodyum_grafit():
    from cekirdek import malzeme_tarif as mt
    from cekirdek import malzeme_sogutucu as ms
    d = mt.uret("d2o", {"sicaklik": 340.0, "basinc": 0.1, "saflik": 99.75})
    assert d["yogunluk"]["deger"] == pytest.approx(
        ms.agir_su_karisim_yogunlugu(340.0, 0.1, 0.9975), rel=1e-12)
    h = {b["isim"]: b["miktar"] for b in d["bilesim"]}
    assert h["H2"] == pytest.approx(2 * 0.9975) and h["H1"] == pytest.approx(2 * 0.0025)
    assert d["sab"] == ["c_D_in_D2O"]
    na = mt.uret("na", {"sicaklik": 673.0})
    assert na["yogunluk"]["deger"] == pytest.approx(0.8577659873807998, rel=1e-12)
    g = mt.uret("grafit", mt.varsayilanlar("grafit"))
    assert g["sab"] == ["c_Graphite"]


def test_b4c_ve_uo2_gd2o3_ve_mox():
    from cekirdek import malzeme_tarif as mt
    from cekirdek import malzeme_hesap as mh
    b = mt.uret("b4c", {"b10_yuzde": 90.0, "td_yuzde": 70.0, "sicaklik": 600.0})
    v = {s["isim"]: s["miktar"] for s in b["bilesim"]}
    assert v["B10"] == pytest.approx(4 * 0.9) and v["C"] == 1.0
    assert b["yogunluk"]["deger"] == pytest.approx(0.70 * 2.52)
    gd = mt.uret("uo2_gd", {"zenginlik": 3.2, "gd2o3_yuzde": 8.0, "td_yuzde": 95.0,
                            "sicaklik": 900.0})
    assert gd["bilesim"] == mh.uo2_gd2o3_bilesimi(3.2, 0.08)
    assert gd["yogunluk"]["deger"] == pytest.approx(0.95 * 10.56349030946277)
    p = dict(mt.varsayilanlar("mox"), yas_yil=5.0)
    mox = mt.uret("mox", p)
    toplam = sum(s["miktar"] for s in mox["bilesim"])
    assert toplam == pytest.approx(100.0)
    assert any(s["isim"] == "Am241" for s in mox["bilesim"])
    taze = mt.uret("mox", dict(p, yas_yil=0.0, am241=0.0))
    assert not any(s["isim"] == "Am241" for s in taze["bilesim"])
    with pytest.raises(ValueError, match="Pu"):
        mt.uret("mox", dict(p, pu239=10.0))                 # vektor toplami %100 degil


def test_yeni_sablonlar_m5_ss304():
    from cekirdek import malzeme_tarif as mt
    for k in ("m5", "ss304"):
        m = mt.uret(k, mt.varsayilanlar(k))
        assert sum(b["miktar"] for b in m["bilesim"]) == pytest.approx(100.0), k
    assert mt.uret("ss304", mt.varsayilanlar("ss304"))["yogunluk"]["deger"] == 7.94


def test_katalog_tarifleri_parametrik_kayit_tasir():
    """Katalogdan gelen tarifler (Zr-4 ...) 'kutup' kaydiyla uretilir: Duzenle ayni formu acar."""
    from cekirdek import malzeme_tarif as mt
    from cekirdek import malzeme_kutup as mk
    m = mt.uret("zirkaloy4", {"yogunluk": 6.56, "sicaklik": 600.0})
    assert mk.parametrik_mi(m) and m["kutup"]["anahtar"] == "zirkaloy4"


def test_aralik_disi_parametre_alan_adiyla_hata():
    from cekirdek import malzeme_tarif as mt
    with pytest.raises(ValueError, match="U-235"):
        mt.uret("uo2", dict(mt.varsayilanlar("uo2"), zenginlik=120.0))
    with pytest.raises(ValueError):
        mt.uret("yok_boyle", {})


def test_karisim_tarifi():
    from cekirdek import malzeme_tarif as mt
    from cekirdek.sema import malzeme, bilesen
    a = malzeme("a", [bilesen("H1", 1.0, tur="nuklid")], 1.0)
    b = malzeme("b", [bilesen("O16", 1.0, tur="nuklid")], 3.0)
    m = mt.karisim_malzemesi([a, b], [0.5, 0.5], "vo", ad="k", sicaklik=300.0)
    assert m["yogunluk"]["deger"] == pytest.approx(2.0)
    assert {s["isim"] for s in m["bilesim"]} == {"H1", "O16"}
    assert all(s["tur"] == "nuklid" and s["birim"] == "ao" for s in m["bilesim"])


def _sahte_kesit(dizin, nuklidler, termal=()):
    yol = os.path.join(dizin, "cross_sections.xml")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("<?xml version='1.0'?>\n<cross_sections>\n")
        for n in nuklidler:
            f.write('<library materials="%s" path="%s.h5" type="neutron"/>\n' % (n, n))
        for t in termal:
            f.write('<library materials="%s" path="%s.h5" type="thermal"/>\n' % (t, t))
        f.write("</cross_sections>\n")
    return yol


def _onbelleksiz():
    """veri_bilgi'nin surec geneli onbellekleri sahte kutuphaneyle kirlenmesin."""
    import contextlib
    from cekirdek import veri_bilgi
    yigin = contextlib.ExitStack()
    for o in (veri_bilgi._YOL_ONBELLEK, veri_bilgi._NUKLID_ONBELLEK, veri_bilgi._SAB_ONBELLEK):
        yigin.enter_context(mock.patch.dict(o, clear=True))
    return yigin


def test_dogrulama_adimi():
    from cekirdek import malzeme_tarif as mt
    su = mt.uret("h2o", {"sicaklik": 300.0, "basinc": 0.1, "bor_ppm": 0.0, "b10_yuzde": None})
    # kesit yolu yok: nuklid denetimi UYARIYLA atlanir (hata degil)
    with mock.patch.dict(os.environ, {"OPENMC_CROSS_SECTIONS": ""}):
        b = mt.dogrula_malzeme(su)
    assert any(s == "uyari" and "atlandı" in m for s, m in b)
    assert not any(s == "hata" for s, m in b)
    # kutuphanede B10/B11 yok -> zenginlestirilmis borlu suda eksik nuklid hatasi;
    # O17/O18 yok ama O16 var -> OpenMC O16'ya katar (hata degil)
    yol = _sahte_kesit(tempfile.mkdtemp(prefix="k6_xs_"), ["H1", "H2", "O16"],
                       ["c_H_in_H2O"])
    borlu = mt.uret("h2o", {"sicaklik": 300.0, "basinc": 0.1, "bor_ppm": 500.0,
                            "b10_yuzde": 40.0})
    with mock.patch.dict(os.environ, {"OPENMC_CROSS_SECTIONS": yol}), _onbelleksiz():
        assert not any(s == "hata" for s, _m in mt.dogrula_malzeme(su))
        b = mt.dogrula_malzeme(borlu)
    assert any(s == "hata" and "B10" in m and "B11" in m for s, m in b), b
    # S(a,b) kutuphanede yoksa hata
    with mock.patch.dict(os.environ, {"OPENMC_CROSS_SECTIONS": yol}), _onbelleksiz():
        b = mt.dogrula_malzeme(dict(su, sab=["c_H_in_CH2"]))
    assert any(s == "hata" and "c_H_in_CH2" in m for s, m in b), b
    # S(a,b) unutulmus su: oneri (dogrula kurali)
    sabsiz = dict(su, sab=[])
    with mock.patch.dict(os.environ, {"OPENMC_CROSS_SECTIONS": ""}):
        b = mt.dogrula_malzeme(sabsiz)
    assert any("c_H_in_H2O" in m for _s, m in b), b
    # bos bilesim: hata
    with mock.patch.dict(os.environ, {"OPENMC_CROSS_SECTIONS": ""}):
        assert any(s == "hata" for s, _m in mt.dogrula_malzeme(dict(su, bilesim=[])))


# ---------------------------------------------------------------------------
# YAVAS: k aynılığı (kisa MC, ayni tohum)
# ---------------------------------------------------------------------------

def _pin_modeli(yakit):
    import openmc
    from cekirdek import kurucu, malzeme_kutup as mk
    spec_m = [yakit, mk.su(sicaklik=293.6), mk.zirkaloy4(sicaklik=293.6)]
    nes, mats, _r = kurucu.malzemeleri_kur({"malzemeler": spec_m})
    y, s, z = nes[yakit["ad"]], nes["su"], nes["zirkaloy4"]
    r1, r2 = openmc.ZCylinder(r=0.41), openmc.ZCylinder(r=0.475)
    kutu = openmc.model.RectangularPrism(1.26, 1.26, boundary_type="reflective")
    hucreler = [openmc.Cell(fill=y, region=-r1), openmc.Cell(fill=z, region=+r1 & -r2),
                openmc.Cell(fill=s, region=+r2 & -kutu)]
    ayar = openmc.Settings()
    ayar.batches, ayar.inactive, ayar.particles, ayar.seed = 25, 5, 400, 1
    ayar.temperature = {"method": "interpolation"}
    ayar.source = openmc.IndependentSource(space=openmc.stats.Point())
    return openmc.Model(openmc.Geometry(hucreler), mats, ayar)


def test_asistan_uo2_k_ayni(gecici):
    from cekirdek import malzeme_tarif as mt
    from cekirdek import malzeme_kutup as mk
    katalog = mk.uo2(zenginlik=3.2, yogunluk=10.40, sicaklik=900.0)
    asistan = mt.uret("uo2", {"zenginlik": 3.2, "yogunluk_yolu": "dogrudan",
                              "yogunluk": 10.40, "sicaklik": 900.0})
    asistan["ad"] = katalog["ad"]
    kler = []
    for i, m in enumerate((katalog, asistan)):
        d = os.path.join(gecici, str(i))
        os.makedirs(d)
        sp = _pin_modeli(m).run(cwd=d, threads=ISLEM_PARCACIGI, output=False)
        import openmc
        with openmc.StatePoint(sp) as s:
            kler.append((s.keff.n, s.keff.s))
    # ayni girdi + ayni tohum -> ayni parcacik gecmisleri; cok is parcacikli
    # toplama sirasi yalnizca son basamaklari oynatir (olculen fark 2e-15)
    assert kler[0][0] == pytest.approx(kler[1][0], rel=1e-12), kler
    assert kler[0][1] == pytest.approx(kler[1][1], rel=1e-9), kler
    assert 1.0 < kler[0][0] < 1.6


HIZLI = [test_kategoriler_ve_her_tarif_varsayilanla_gecerli, test_asistan_uo2_katalog_uo2_ile_ayni,
         test_uo2_td_yolu_ve_om, test_hafif_su_if97_ve_bor, test_agir_su_sodyum_grafit,
         test_b4c_ve_uo2_gd2o3_ve_mox, test_yeni_sablonlar_m5_ss304,
         test_katalog_tarifleri_parametrik_kayit_tasir, test_aralik_disi_parametre_alan_adiyla_hata,
         test_karisim_tarifi, test_dogrulama_adimi]
YAVAS = [test_asistan_uo2_k_ayni]
