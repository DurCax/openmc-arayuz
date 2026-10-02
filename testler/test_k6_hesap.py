# -*- coding: utf-8 -*-
"""
 test_k6_hesap.py  --  v3 K6: malzeme hesaplayicilari (cekirdek/malzeme_hesap.py)

 HER BEKLENEN DEGER BAGIMSIZ EL HESABIDIR: modulu kullanmadan, yalnizca
 asagidaki sabitlerle (AME2020 kutleleri ve IUPAC 2013 bolluklari -- openmc.data
 ile ayni sayilar) duz aritmetikle hesaplanip buraya yazildi. Formul her testin
 yorumundadir; kaynaklar malzeme_hesap.py basligindadir.

   M(U234)=234.040950296  M(U235)=235.043928117  M(U236)=236.04556613
   M(U238)=238.050786936  M(B10)=10.012936862    M(B11)=11.009305166
   M_ort(O)=15.999304509  M_ort(H)=1.007981749   M_ort(B)=10.811824968
   N_A*1e-24 = 0.602214076
"""

import math

import pytest

from testler.ortak_test import KOK  # noqa: F401  (sys.path)

_GORELI = 1e-9


def _yakin(a, b, goreli=_GORELI):
    return a == pytest.approx(b, rel=goreli)


# ---------------------------------------------------------------------------
# kuramsal yogunluk, gozeneklilik
# ---------------------------------------------------------------------------

def test_td_ve_gozeneklilikten_yogunluk():
    from cekirdek import malzeme_hesap as mh
    # %95 TD UO2: 0.95 x 10.97 = 10.4215 ; p = 0.05 ayni sonuc
    assert _yakin(mh.yogunluk_td(mh.UO2_TD, td_orani=0.95), 10.4215)
    assert _yakin(mh.yogunluk_td(mh.UO2_TD, gozeneklilik=0.05), 10.4215)
    assert _yakin(mh.td_orani(10.40, mh.UO2_TD), 10.40 / 10.97)
    for hatali in ({"td_orani": 1.2}, {"gozeneklilik": 1.0}, {},
                   {"td_orani": 0.9, "gozeneklilik": 0.1}):
        with pytest.raises(ValueError):
            mh.yogunluk_td(mh.UO2_TD, **hatali)


# ---------------------------------------------------------------------------
# zenginlik <-> izotopik vektor
# ---------------------------------------------------------------------------

def test_uranyum_vektoru_ornl_bagintisi():
    from cekirdek import malzeme_hesap as mh
    # e = 3.2 wt%: w234 = 0.0089e, w236 = 0.0046e, w238 = 1 - 1.0135e
    w = mh.uranyum_vektoru(3.2)
    assert _yakin(w["U234"], 0.0089 * 0.032) and _yakin(w["U236"], 0.0046 * 0.032)
    assert _yakin(w["U238"], 1 - 1.0135 * 0.032)
    # atom kesri a_i = (w_i/M_i)/sum(w/M) -- el hesabi
    a = mh.wo_to_ao(w)
    assert _yakin(a["U235"], 0.03239590764627883)
    assert _yakin(a["U234"], 0.00028955918299063973)
    assert _yakin(a["U238"], 0.9671661443534377)
    # ters yon: ao -> wo -> ayni zenginlik
    assert _yakin(mh.zenginlik(a, "U235", birim="wo"), 0.032)
    with pytest.raises(ValueError):
        mh.uranyum_vektoru(99.5)          # 1.0135 e > 100


def test_uranyum_vektoru_openmc_ile_ayni():
    """Capraz denetim: OpenMC Element.expand (kesit kutuphanesi suzgeci olmadan)."""
    import openmc
    from cekirdek import malzeme_hesap as mh
    beklenen = {n: a for n, a, _t in
                openmc.Element("U").expand(1.0, "ao", enrichment=4.95, cross_sections=None)}
    a = mh.element_vektoru("U", 4.95)
    for n, deger in beklenen.items():
        assert _yakin(a[n], deger, 1e-12), n


def test_bor_lityum_gadolinyum_zenginlestirme():
    from cekirdek import malzeme_hesap as mh
    # B-10 %90 at: a10 = 0.9 ; wo: 0.9 M10 / (0.9 M10 + 0.1 M11)
    b = mh.zenginlestir("B", "B10", 0.90)
    assert _yakin(b["B10"], 0.90) and _yakin(b["B11"], 0.10)
    assert _yakin(mh.zenginlik(b, "B10", birim="wo"), 0.8911325098745739)
    # B-10 %40 wt -> at: (0.4/M10)/(0.4/M10 + 0.6/M11)
    b40 = mh.zenginlestir("B", "B10", 0.40, birim="wo")
    assert _yakin(b40["B10"], 0.42296775260309877)
    # dogal bor: IUPAC 2013 B-10 = 0.1982
    assert _yakin(mh.zenginlik(mh.dogal_vektor("B"), "B10"), 0.1982)
    # Li-6 %95 at
    li = mh.zenginlestir("Li", "Li6", 0.95)
    assert _yakin(li["Li6"], 0.95) and _yakin(li["Li7"], 0.05)
    # Gd-157 %50 at; digerleri dogal oranla: Gd155 = 0.148 x 0.5 / (1 - 0.1565)
    gd = mh.zenginlestir("Gd", "Gd157", 0.50)
    assert _yakin(gd["Gd155"], 0.0877296976882039)
    assert _yakin(sum(gd.values()), 1.0)
    with pytest.raises(ValueError):
        mh.zenginlestir("B", "B12", 0.5)
    with pytest.raises(ValueError):
        mh.zenginlestir("B", "B10", 1.5)


# ---------------------------------------------------------------------------
# turetilmis degerler
# ---------------------------------------------------------------------------

def _uo2(zeng=3.2, yog=10.40):
    from cekirdek.sema import malzeme, bilesen
    return malzeme("uo2", [bilesen("U", 1.0, zenginlik=zeng), bilesen("O", 2.0)], yog)


def test_uo2_turetilmis_degerler_el_hesabi():
    from cekirdek import malzeme_hesap as mh
    # M_U = 1/sum(w/M) = 237.95191837803 ; M_UO2 = M_U + 2 M_O = 269.95052739649
    # N_UO2 = rho N_A / M_UO2 = 10.40 x 0.602214076 / 269.9505 = 0.023200645136
    t = mh.turetilmis(_uo2())
    assert _yakin(t["N_toplam"], 0.06960193540797348)
    assert _yakin(t["nuklidler"]["U235"], 0.0007516059571596578)
    o = sum(v for k, v in t["nuklidler"].items() if k.startswith("O"))
    assert _yakin(o, 0.046401290271982316)
    assert _yakin(t["ortalama_kutle"], 89.98350913216875)
    # gHM/cm3 = rho M_U / M_UO2 = 9.16723510414
    assert _yakin(t["agir_metal_gcm3"], 9.167235104144238)
    assert _yakin(t["yogunluk_gcm3"], 10.40)
    assert t["H_X"] is None                         # hidrojen yok


def test_turetilmis_openmc_ile_ayni():
    """Capraz denetim: openmc.Material.get_nuclide_atom_densities."""
    import openmc
    from cekirdek import malzeme_hesap as mh
    m = openmc.Material()
    m.add_element("U", 1.0, enrichment=3.2, cross_sections=None)
    m.add_element("O", 2.0, cross_sections=None)
    m.set_density("g/cm3", 10.40)
    beklenen = m.get_nuclide_atom_densities()
    t = mh.turetilmis(_uo2())
    for n, deger in beklenen.items():
        assert _yakin(t["nuklidler"][n], deger, 1e-10), n


def test_yogunluk_birimleri_ve_sum():
    from cekirdek import malzeme_hesap as mh
    from cekirdek.sema import malzeme, bilesen
    uo2 = _uo2()
    n = mh.turetilmis(uo2)["N_toplam"]
    # atom/b-cm verilince ayni g/cm3'e donmeli; kg/m3 = 1000 x g/cm3
    for birim, deger in (("atom/b-cm", n), ("atom/cm3", n * 1e24), ("kg/m3", 10400.0)):
        m = dict(uo2, yogunluk={"birim": birim, "deger": deger})
        assert _yakin(mh.turetilmis(m)["yogunluk_gcm3"], 10.40, 1e-12), birim
    # "sum": her satir atom/b-cm (ao) -> N_toplam = toplam
    s = malzeme("s", [bilesen("H1", 0.04, tur="nuklid"), bilesen("O16", 0.02, tur="nuklid")],
                0.0, birim="sum")
    t = mh.turetilmis(s)
    assert _yakin(t["N_toplam"], 0.06) and _yakin(t["nuklidler"]["H1"], 0.04)
    with pytest.raises(ValueError):
        mh.turetilmis(dict(uo2, yogunluk={"birim": "macro", "deger": 1.0}))
    # g/cm3 <-> atom/b-cm
    assert _yakin(mh.atom_bcm_to_gcm3(mh.gcm3_to_atom_bcm(2.0, 12.0), 12.0), 2.0)
    assert _yakin(mh.gcm3_to_atom_bcm(1.0, 0.602214076), 1.0)


def test_karisik_birim_ve_negatif_reddedilir():
    from cekirdek import malzeme_hesap as mh
    from cekirdek.sema import malzeme, bilesen
    with pytest.raises(ValueError):
        mh.turetilmis(malzeme("x", [bilesen("H", 1.0), bilesen("O", 1.0, birim="wo")], 1.0))
    with pytest.raises(ValueError):
        mh.turetilmis(malzeme("x", [bilesen("H", -1.0)], 1.0))
    with pytest.raises(ValueError):
        mh.turetilmis(malzeme("x", [], 1.0))


def test_h_x_orani():
    from cekirdek import malzeme_hesap as mh
    from cekirdek.sema import malzeme, bilesen
    # 100 H atomu / 1 U-235 atomu (ao) -> H/X = 100
    m = malzeme("cozelti", [bilesen("H1", 100.0, tur="nuklid"), bilesen("O16", 50.0, tur="nuklid"),
                            bilesen("U235", 1.0, tur="nuklid")], 1.0)
    assert _yakin(mh.turetilmis(m)["H_X"], 100.0)


# ---------------------------------------------------------------------------
# bor ppm
# ---------------------------------------------------------------------------

def test_bor_ppm_donusumleri():
    from cekirdek import malzeme_hesap as mh
    # 1000 ppm (kutle) B, rho = 0.7 g/cm3: N_B = 0.7 x 1e-3 x 0.602214076 / 10.811825
    assert _yakin(mh.bor_sayi_yogunlugu(1000.0, 0.7), 3.898970381428956e-05)
    # atom ppm (cozeltinin butun atomlarina gore): n_B/(n_B + 3 n_H2O)
    assert _yakin(mh.ppm_wo_to_ao(1000.0), 555.6656986078677)
    # ters: 100 atom ppm -> 180.03 kutle ppm
    assert _yakin(mh.ppm_ao_to_wo(100.0), 180.02995470640272)
    assert _yakin(mh.ppm_ao_to_wo(mh.ppm_wo_to_ao(1300.0)), 1300.0)
    with pytest.raises(ValueError):
        mh.ppm_wo_to_ao(-1.0)


def test_borlu_su_bilesimi():
    from cekirdek import malzeme_hesap as mh
    b = mh.borlu_su_bilesimi(1000.0)
    w = {s["isim"]: s["miktar"] for s in b}
    assert all(s["birim"] == "wo" for s in b)
    assert _yakin(w["B"], 1e-3 * 100.0)                     # yuzde
    assert _yakin(w["H"] + w["O"] + w["B"], 100.0)
    # B-10 zenginlestirilmis bor: nuklid satirlari, B10+B11 = bor kutlesi
    bz = {s["isim"]: s["miktar"] for s in mh.borlu_su_bilesimi(1000.0, b10_ao=0.9)}
    assert _yakin(bz["B10"] + bz["B11"], 0.1)
    assert _yakin(bz["B10"] / (bz["B10"] + bz["B11"]), 0.8911325098745739)


# ---------------------------------------------------------------------------
# karisim (wo / ao / vo)
# ---------------------------------------------------------------------------

def test_karisim_hacim_ve_agirlik():
    from cekirdek import malzeme_hesap as mh
    a = ({"H1": 1.0}, 1.0)
    b = ({"O16": 1.0}, 3.0)
    # vo 50/50: rho = 0.5x1 + 0.5x3 = 2 ; kutle oranlari 0.5:1.5
    v, rho = mh.karistir([a, b], [0.5, 0.5], "vo")
    assert _yakin(rho, 2.0)
    assert _yakin(mh.ao_to_wo(v)["H1"], 0.25)
    # wo 50/50: 1/rho = 0.5/1 + 0.5/3 -> 1.5
    v, rho = mh.karistir([a, b], [0.5, 0.5], "wo")
    assert _yakin(rho, 1.5) and _yakin(mh.ao_to_wo(v)["H1"], 0.5)
    with pytest.raises(ValueError):
        mh.karistir([a, b], [0.5, 0.6], "vo")              # toplam 1 degil
    with pytest.raises(ValueError):
        mh.karistir([a, b], [1.2, -0.2], "wo")


def test_karisim_openmc_mix_materials_ile_ayni():
    import openmc
    from cekirdek import malzeme_hesap as mh
    from cekirdek.sema import malzeme, bilesen
    su = malzeme("su", [bilesen("H", 2.0), bilesen("O", 1.0)], 0.7)
    uo2 = _uo2()
    for tur in ("ao", "wo", "vo"):
        om = []
        for m in (su, uo2):
            o = openmc.Material()
            for s in m["bilesim"]:
                o.add_element(s["isim"], s["miktar"], enrichment=s.get("zenginlik"),
                              cross_sections=None)
            o.set_density("g/cm3", m["yogunluk"]["deger"])
            om.append(o)
        k = openmc.Material.mix_materials(om, [0.3, 0.7], tur)
        beklenen = k.get_nuclide_atom_densities()
        v, rho = mh.karistir([(mh.nuklid_atom_kesirleri(m["bilesim"]), m["yogunluk"]["deger"])
                              for m in (su, uo2)], [0.3, 0.7], tur)
        n = mh.gcm3_to_atom_bcm(rho, mh.ortalama_kutle(v))
        for nk, deger in beklenen.items():
            assert _yakin(v[nk] * n, deger, 1e-9), (tur, nk)


# ---------------------------------------------------------------------------
# UO2-Gd2O3, MOX, Am-241 yaslanmasi
# ---------------------------------------------------------------------------

def test_uo2_gd2o3_bilesimi():
    from cekirdek import malzeme_hesap as mh
    # %8 Gd2O3 (kutle): w_U = 0.92 M_U/M_UO2 ; w_Gd = 0.08 x 2M_Gd/(2M_Gd + 3M_O)
    b = {s["isim"]: s for s in mh.uo2_gd2o3_bilesimi(3.2, 0.08)}
    assert _yakin(b["U"]["miktar"], 81.0947720751221)
    assert b["U"]["zenginlik"] == 3.2
    assert _yakin(b["Gd"]["miktar"], 6.940742049842756)
    assert _yakin(b["O"]["miktar"], 11.964485875035143)
    # ideal karisim kuramsal yogunlugu: 1/(0.92/10.97 + 0.08/7.407)
    assert _yakin(mh.karisim_td([0.92, 0.08], [mh.UO2_TD, mh.GD2O3_TD]), 10.56349030946277)
    with pytest.raises(ValueError):
        mh.uo2_gd2o3_bilesimi(3.2, 1.2)


def test_mox_bilesimi():
    from cekirdek import malzeme_hesap as mh
    pu = {"Pu238": 0.02, "Pu239": 0.55, "Pu240": 0.25, "Pu241": 0.10, "Pu242": 0.08}
    # HM: %92 U (e=0.25) + %8 Pu ; O = 2 M_O sum(w_i/M_i) (MO2)
    b = {s["isim"]: s for s in mh.mox_bilesimi(0.08, pu, 0.25)}
    toplam = sum(s["miktar"] for s in b.values())
    assert _yakin(toplam, 100.0)
    assert _yakin(b["U"]["miktar"], 81.10382968572537)
    assert _yakin(b["O"]["miktar"], 11.843663385081121)
    assert _yakin(b["Pu239"]["miktar"], 3.878878811056431)
    with pytest.raises(ValueError):
        mh.mox_bilesimi(0.08, {"Pu239": 0.5}, 0.25)         # vektor toplami 1 degil


def test_pu_yaslandirma_am241():
    from cekirdek import malzeme_hesap as mh
    pu = {"Pu238": 0.02, "Pu239": 0.55, "Pu240": 0.25, "Pu241": 0.10, "Pu242": 0.08}
    # 5 yil: N_i = N_i0 exp(-l_i t); Am = N241_0 l_p/(l_a-l_p) (e^-l_p t - e^-l_a t)
    y = mh.pu_yaslandir(pu, 5.0)
    assert _yakin(y["Am241"], 0.021469480622143475, 1e-7)
    assert _yakin(y["Pu241"], 0.07854865851325853, 1e-7)
    assert _yakin(y["Pu238"], 0.019245765342008815, 1e-7)
    assert _yakin(sum(y.values()), 1.0)
    assert mh.pu_yaslandir(pu, 0.0)["Am241"] == 0.0
    with pytest.raises(ValueError):
        mh.pu_yaslandir(pu, -1.0)


def test_nan_ve_sonsuz_girdiler_degerhatasi():
    from cekirdek import malzeme_hesap as mh
    from cekirdek.sema import malzeme, bilesen
    nan, inf = float("nan"), float("inf")
    a, b = ({"H1": 1.0}, 1.0), ({"O16": 1.0}, 3.0)
    hatali = [
        lambda: mh.karistir([a, b], [nan, 0.5], "vo"),
        lambda: mh.karistir([a, ({"O16": 1.0}, inf)], [0.5, 0.5], "wo"),
        lambda: mh.karistir([a, ({"O16": 1.0}, 0.0)], [0.5, 0.5], "wo"),     # sifira bolme
        lambda: mh.ao_to_wo({"H1": nan}),
        lambda: mh.turetilmis(malzeme("x", [bilesen("H", inf)], 1.0)),
        lambda: mh.yogunluk_td(nan, td_orani=0.9),
        lambda: mh.pu_yaslandir({"Pu239": 1.0}, inf),
        lambda: mh.mox_bilesimi(nan, {"Pu239": 1.0}, 0.25),
        lambda: mh.mox_bilesimi(0.1, {"Pu239": 1.0}, 0.25, om=nan),
        lambda: mh.kutle("Xx999"),
    ]
    for i, f in enumerate(hatali):
        with pytest.raises(ValueError):
            f()


def test_sifir_miktarli_satir_atlanir():
    from cekirdek import malzeme_hesap as mh
    from cekirdek.sema import malzeme, bilesen
    m = malzeme("x", [bilesen("H1", 2.0, tur="nuklid"), bilesen("O16", 1.0, tur="nuklid"),
                      bilesen("B10", 0.0, tur="nuklid")], 1.0)
    assert "B10" not in mh.turetilmis(m)["nuklidler"]
    with pytest.raises(ValueError):
        mh.turetilmis(malzeme("x", [bilesen("H1", 0.0, tur="nuklid")], 1.0))


HIZLI = [test_nan_ve_sonsuz_girdiler_degerhatasi, test_sifir_miktarli_satir_atlanir,
         test_td_ve_gozeneklilikten_yogunluk, test_uranyum_vektoru_ornl_bagintisi,
         test_uranyum_vektoru_openmc_ile_ayni, test_bor_lityum_gadolinyum_zenginlestirme,
         test_uo2_turetilmis_degerler_el_hesabi, test_turetilmis_openmc_ile_ayni,
         test_yogunluk_birimleri_ve_sum, test_karisik_birim_ve_negatif_reddedilir,
         test_h_x_orani, test_bor_ppm_donusumleri, test_borlu_su_bilesimi,
         test_karisim_hacim_ve_agirlik, test_karisim_openmc_mix_materials_ile_ayni,
         test_uo2_gd2o3_bilesimi, test_mox_bilesimi, test_pu_yaslandirma_am241]
