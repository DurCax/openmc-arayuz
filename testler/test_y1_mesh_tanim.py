# -*- coding: utf-8 -*-
"""
 test_y1_mesh_tanim.py  --  v3 Y1: mesh tally TANIMI (cekirdek/mesh_tally/tanim.py)

 Mesh turu (duzenli / silindirik / kuresel), sinir kutusundan otomatik oneri,
 OpenMC mesh nesnesi kurulumu, enerji grup yapilari ve BETIK ESDEGERLIGI
 (arayuzun kurdugu model = uretilen betigin modeli; ayni tanim islevi iki
 yoldan da cagrilir). Hexagonal mesh OpenMC 0.16.0'da YOK (bkz. tanim.py).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import importlib.util
import math
import os

import numpy as np

from testler.ortak_test import kontrol, ORNEK, ISLEM_PARCACIGI

_ORNEK = "pwr_mesh_aki.json"


def _spec(ad="pwr_17x17.json"):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad))


def _betik_modeli(spec, dizin):
    """Uretilen betigi calistirmadan yukler; betigin `model` nesnesi."""
    from cekirdek import kod_uret
    yol = os.path.join(dizin, "model.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kod_uret.uret(spec, "model.py"))
    sm = importlib.util.spec_from_file_location("y1_betik_%d" % id(spec), yol)
    mod = importlib.util.module_from_spec(sm)
    sm.loader.exec_module(mod)
    return mod.model


def _mesh_ozeti(model):
    """{tally adi: [(sinif, boyut, izgaralar...)]} -- karsilastirma icin."""
    import openmc
    ozet = {}
    for t in model.tallies:
        for f in t.filters:
            if isinstance(f, openmc.MeshFilter):
                m = f.mesh
                izg = tuple(np.asarray(g, dtype=float).tolist() for g in m._grids)
                ozet.setdefault(t.name, []).append(
                    (type(m).__name__, tuple(int(n) for n in m.dimension), izg,
                     tuple(np.asarray(getattr(m, "origin", (0, 0, 0)), float).tolist())))
    return ozet


# ---------------------------------------------------------------------------
# tur ve dogrulama
# ---------------------------------------------------------------------------

def test_mesh_turu_eski_dosyada_duzenli():
    print("\n[Y1-T1] mesh_turu yoksa duzenli (eski dosyalar); bilinmeyen tur hata")
    from cekirdek import mesh_tally as mt
    # Arrange
    eski = {"tur": "mesh", "boyut": [4, 4, 1], "otomatik": True}
    # Act / Assert
    kontrol("eski filtre duzenli", mt.mesh_turu(eski) == mt.DUZENLI)
    kontrol("tur listesi: duzenli, silindirik, kuresel",
            mt.MESH_TURLERI == (mt.DUZENLI, mt.SILINDIRIK, mt.KURESEL))
    try:
        mt.mesh_turu({"tur": "mesh", "mesh_turu": "altigen", "boyut": [1, 1, 1]})
        hata = None
    except ValueError as e:
        hata = str(e)
    kontrol("altigen (OpenMC'de yok) acik hata", hata is not None and "altigen" in hata)
    kontrol("Hexagonal notu belgeli", "HexagonalMesh" in mt.HEKSAGONAL_NOTU)


def test_filtre_hatalari():
    print("\n[Y1-T2] filtre_hatalari: boyut, yaricap, eksenel aralik")
    from cekirdek import mesh_tally as mt
    kontrol("gecerli duzenli temiz", mt.filtre_hatalari(mt.filtre_duzenli([3, 3, 1])) == [])
    kontrol("gecerli silindirik temiz",
            mt.filtre_hatalari(mt.filtre_silindirik([5, 4, 2], r_ust=10.0,
                                                    z_alt=-5.0, z_ust=5.0)) == [])
    kontrol("sifir bolme hata", bool(mt.filtre_hatalari(mt.filtre_duzenli([0, 3, 1]))))
    kontrol("iki elemanli boyut hata",
            bool(mt.filtre_hatalari({"tur": "mesh", "boyut": [3, 3], "otomatik": True})))
    kontrol("negatif yaricap hata",
            bool(mt.filtre_hatalari(mt.filtre_kuresel([3, 1, 1], r_ust=-1.0))))
    kontrol("z_ust <= z_alt hata",
            bool(mt.filtre_hatalari(mt.filtre_silindirik([2, 1, 1], r_ust=1.0,
                                                         z_alt=3.0, z_ust=3.0))))
    kontrol("duzenli alt >= ust hata",
            bool(mt.filtre_hatalari({"tur": "mesh", "boyut": [1, 1, 1],
                                     "alt": [0, 0, 0], "ust": [1, -1, 1]})))


# ---------------------------------------------------------------------------
# sinir onerisi ve tanim
# ---------------------------------------------------------------------------

def test_sinir_onerisi_sinir_kutusundan():
    print("\n[Y1-T3] sinir onerisi modelin sinir kutusundan (duzenli = kurucu ile ayni)")
    from cekirdek import kurucu, mesh_tally as mt
    spec = _spec()
    kutu = (21.42, 21.42)
    # Act
    d = mt.sinir_onerisi(spec, kutu, mt.DUZENLI)
    s = mt.sinir_onerisi(spec, kutu, mt.SILINDIRIK)
    k = mt.sinir_onerisi(spec, kutu, mt.KURESEL)
    alt, ust = kurucu.tally_mesh_sinirlari(spec, {"otomatik": True}, kutu)
    # Assert
    kontrol("duzenli = kurucu.tally_mesh_sinirlari", d == {"alt": alt, "ust": ust}, "-> %s" % d)
    kontrol("silindirik r = max(gx, gy)/2", math.isclose(s["r_ust"], 10.71), "-> %s" % s)
    kontrol("2B modelde z = +/-1 cm (duzenli ile ayni)",
            (s["z_alt"], s["z_ust"]) == (alt[2], ust[2]))
    kontrol("kuresel r = max(gx, gy)/2", math.isclose(k["r_ust"], 10.71))


def test_tanim_ve_mesh_kurulumu():
    print("\n[Y1-T4] mesh_tanimi -> openmc mesh: tur, boyut, izgara, otomatik/acik sinir")
    import openmc
    from cekirdek import mesh_tally as mt
    spec = _spec()
    kutu = (20.0, 10.0)
    # duzenli otomatik
    m = mt.mesh_kur(mt.mesh_tanimi(spec, mt.filtre_duzenli([4, 2, 1]), kutu))
    kontrol("RegularMesh", isinstance(m, openmc.RegularMesh))
    kontrol("duzenli sinirlar kutudan",
            list(m.lower_left) == [-10.0, -5.0, -1.0] and list(m.upper_right) == [10.0, 5.0, 1.0])
    # silindirik acik sinirlar
    f = mt.filtre_silindirik([5, 8, 2], r_ust=7.5, z_alt=-3.0, z_ust=3.0)
    c = mt.mesh_kur(mt.mesh_tanimi(spec, f, kutu))
    kontrol("CylindricalMesh", isinstance(c, openmc.CylindricalMesh))
    kontrol("silindirik boyut (nr, nphi, nz)", tuple(c.dimension) == (5, 8, 2))
    kontrol("r izgarasi 0..7.5 esit", np.allclose(c.r_grid, np.linspace(0, 7.5, 6)))
    kontrol("phi izgarasi 0..2pi", math.isclose(c.phi_grid[-1], 2 * math.pi)
            and len(c.phi_grid) == 9)
    kontrol("z izgarasi -3..3", list(c.z_grid) == [-3.0, 0.0, 3.0])
    # silindirik otomatik
    co = mt.mesh_kur(mt.mesh_tanimi(spec, mt.filtre_silindirik([2, 1, 1]), kutu))
    kontrol("otomatik silindirik r = 10", math.isclose(co.r_grid[-1], 10.0))
    # kuresel
    s = mt.mesh_kur(mt.mesh_tanimi(spec, mt.filtre_kuresel([3, 2, 4], r_ust=6.0), kutu))
    kontrol("SphericalMesh", isinstance(s, openmc.SphericalMesh))
    kontrol("kuresel theta 0..pi, phi 0..2pi",
            math.isclose(s.theta_grid[-1], math.pi) and math.isclose(s.phi_grid[-1], 2 * math.pi))
    # gecersiz tanim
    try:
        mt.mesh_tanimi(spec, mt.filtre_duzenli([0, 1, 1]), kutu)
        hata = False
    except ValueError:
        hata = True
    kontrol("gecersiz filtre ValueError", hata)


def test_tanim_girdiyi_degistirmez():
    print("\n[Y1-T5] mesh_tanimi girdi filtresini yerinde degistirmez")
    import copy
    from cekirdek import mesh_tally as mt
    f = mt.filtre_silindirik([2, 2, 1])
    once = copy.deepcopy(f)
    mt.mesh_tanimi(_spec(), f, (10.0, 10.0))
    kontrol("filtre ayni", f == once)


def test_grup_yapilari():
    print("\n[Y1-T6] grup yapilari OpenMC'den (CASMO-2/4/8 ...); ad bulma")
    from cekirdek import mesh_tally as mt
    kontrol("CASMO-2/4/8 listede", all(a in mt.GRUP_YAPILARI
                                       for a in ("CASMO-2", "CASMO-4", "CASMO-8")))
    c2 = mt.grup_sinirlari("CASMO-2")
    kontrol("CASMO-2 = 0, 0.625, 2e7", c2 == [0.0, 0.625, 2.0e7], "-> %s" % c2)
    kontrol("CASMO-8: 9 sinir, artan", len(mt.grup_sinirlari("CASMO-8")) == 9
            and mt.grup_sinirlari("CASMO-8") == sorted(mt.grup_sinirlari("CASMO-8")))
    kontrol("yapi_bul geri bulur", mt.yapi_bul(mt.grup_sinirlari("CASMO-4")) == "CASMO-4")
    kontrol("elle sinir -> None", mt.yapi_bul([0.0, 1.0, 2.0e7]) is None)
    try:
        mt.grup_sinirlari("YOK-3")
        hata = False
    except ValueError:
        hata = True
    kontrol("bilinmeyen yapi ValueError", hata)


# ---------------------------------------------------------------------------
# betik esdegerligi (kosmadan: mesh tanimlari birebir ayni)
# ---------------------------------------------------------------------------

def test_betik_esdegerligi_mesh_tanimlari(gecici=None):
    print("\n[Y1-T7] betik esdegerligi: kurucu ve uretilen betik AYNI mesh'leri kurar")
    import tempfile
    from cekirdek import kurucu
    spec = _spec(_ORNEK)
    model_a, _n = kurucu.kur(spec)
    eski = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        try:
            os.chdir(d)
            model_b = _betik_modeli(spec, d)
        finally:
            os.chdir(eski)
    a, b = _mesh_ozeti(model_a), _mesh_ozeti(model_b)
    turler = sorted({x[0] for v in a.values() for x in v})
    kontrol("ornekte duzenli + silindirik mesh var",
            turler == ["CylindricalMesh", "RegularMesh"], "-> %s" % turler)
    kontrol("kurucu = betik (tur, boyut, izgara, merkez birebir)", a == b,
            "-> %s\n   %s" % (a, b))


def test_yavas_betik_esdegerligi_kosu(gecici):
    print("\n[Y1-T8] YAVAS: kurucu ve betik ayni tohumla ayni k ve mesh tally degerleri")
    import openmc
    from cekirdek import kurucu
    spec = _spec(_ORNEK)
    spec["ayarlar"].update(parcacik=1000, cevrim=12, pasif=4)
    eski = os.getcwd()
    try:
        ya = os.path.join(gecici, "a"); os.makedirs(ya)
        os.chdir(ya)
        ma, _n = kurucu.kur(spec)
        spa = openmc.StatePoint(ma.run(threads=ISLEM_PARCACIGI, output=False))
        yb = os.path.join(gecici, "b"); os.makedirs(yb)
        os.chdir(yb)
        mb = _betik_modeli(spec, yb)
        spb = openmc.StatePoint(mb.run(threads=ISLEM_PARCACIGI, output=False))
    finally:
        os.chdir(eski)
    fark = abs(spa.keff.nominal_value - spb.keff.nominal_value)
    kontrol("k farki < 1e-10", fark < 1e-10, "-> %.2e" % fark)
    for t in ma.tallies:
        if any(isinstance(f, openmc.MeshFilter) for f in t.filters):
            va = spa.get_tally(name=t.name).mean
            vb = spb.get_tally(name=t.name).mean
            # Ayni tohum: ayni gecmisler; is parcacigi toplama sirasi yalniz
            # yuvarlama farki birakir (k farki da ~1e-15).
            fark = float(np.max(np.abs(va - vb) / np.maximum(np.abs(va), 1e-300)))
            kontrol("'%s' mesh degerleri ayni (bagil < 1e-10)" % t.name,
                    va.shape == vb.shape and fark < 1e-10, "-> %.2e" % fark)


HIZLI = [test_mesh_turu_eski_dosyada_duzenli, test_filtre_hatalari,
         test_sinir_onerisi_sinir_kutusundan, test_tanim_ve_mesh_kurulumu,
         test_tanim_girdiyi_degistirmez, test_grup_yapilari,
         test_betik_esdegerligi_mesh_tanimlari]
YAVAS = [test_yavas_betik_esdegerligi_kosu]
