# -*- coding: utf-8 -*-
"""
 test_y7_yuzey.py  --  v3 Y7: yuzey akimi tally'leri (sinir kacagi, kutu agi)

 HIZLI: tanimlar, kurucu kancasi (SurfaceFilter vakum yuzeyleri /
        MeshSurfaceFilter + denge tally'si), uretilen betigin AYNI tally'leri
        kurmasi, dogrulama, saf hesaplar (dis yuzler, denge, kacak spektrumu)
        sentetik tablolarla el hesabi.
 YAVAS: sabit kaynakta korunum (giren - cikan + S + X = A; birim kaynak
        parcacigi basina ve kaynak siddetiyle), sinir akimi = global sizinti,
        betik esdegerligi (testler/test_y7_fizik.py).
"""

import importlib.util
import math
import os
import tempfile

from cekirdek import sema
from testler.ortak_test import kontrol
from testler.regresyon_ortak import ORNEK

_TOL = 1e-12


def _kure(*filtreler, ad="kacak"):
    spec = sema.yukle(os.path.join(ORNEK, "zirh_kure.json"))
    spec["tallyler"] = [dict(sema.tally(ad, ["current"]), filtreler=list(filtreler))]
    return spec


def _betik_modeli(spec):
    from cekirdek import kod_uret
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, "model.py")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(kod_uret.uret(spec, "model.py"))
        eski = os.getcwd()
        os.chdir(d)
        try:
            sm = importlib.util.spec_from_file_location("y7_yuzey_betik", yol)
            mod = importlib.util.module_from_spec(sm)
            sm.loader.exec_module(mod)
        finally:
            os.chdir(eski)
    return mod.model


def _filtre_ozeti(f):
    import openmc
    if isinstance(f, openmc.SurfaceFilter):
        return ("surface", tuple(sorted(
            (type(s).__name__, tuple(sorted(s.coefficients.items()))) for s in f.bins)))
    if isinstance(f, openmc.MeshSurfaceFilter) or isinstance(f, openmc.MeshFilter):
        m = f.mesh
        return (type(f).__name__, tuple(m.dimension), tuple(m.lower_left), tuple(m.upper_right))
    if isinstance(f, openmc.EnergyFilter):
        return ("energy", tuple(float(x) for x in f.values))
    return (type(f).__name__,)


def _tally_ozeti(model):
    return {t.name: (tuple(t.scores), tuple(_filtre_ozeti(f) for f in t.filters))
            for t in model.tallies}


# ---------------------------------------------------------------------------
# tanimlar ve kurucu
# ---------------------------------------------------------------------------

def test_yuzey_filtre_yapicilari_ve_tanima():
    print("\n[Y7Y-1] yuzey filtresi yapicilari ve yuzey tally'si tanima")
    from cekirdek import yuzey_akim as y
    # Act
    s = y.filtre_sinir()
    k = y.filtre_kutu([2, 2, 1])
    e = y.filtre_kutu([1, 1, 1], alt=[-5, -5, -5], ust=[5, 5, 5])
    # Assert
    kontrol("sinir filtresi", s == {"tur": y.FILTRE_SINIR})
    kontrol("kutu otomatik", k == {"tur": y.FILTRE_KUTU, "boyut": [2, 2, 1], "otomatik": True})
    kontrol("kutu elle sinirli", e["alt"] == [-5.0, -5.0, -5.0] and "otomatik" not in e)
    kontrol("yuzey tally'si taninir", y.yuzey_tally_mi({"filtreler": [s]}))
    kontrol("hacim tally'si yuzey degil", not y.yuzey_tally_mi(sema.tally("t", ["flux"])))


def test_kurucu_sinir_tallysi_vakum_yuzeyleri():
    print("\n[Y7Y-2] kurucu: sinir tally'si = SurfaceFilter(vakum yuzeyleri) + current")
    import openmc
    from cekirdek import kurucu, yuzey_akim as y
    # Arrange
    spec = _kure(y.filtre_sinir(), sema.filtre_enerji([1e-5, 1e6, 2e7]))
    # Act
    model, _b = kurucu.kur(spec)
    t = next(t for t in model.tallies if t.name == "kacak")
    yuzeyler = t.filters[0].bins
    # Assert
    kontrol("SurfaceFilter ilk", isinstance(t.filters[0], openmc.SurfaceFilter))
    kontrol("hepsi vakum", all(s.boundary_type == "vacuum" for s in yuzeyler) and yuzeyler)
    kontrol("dis kure r=35", any(isinstance(s, openmc.Sphere) and s.r == 35.0
                                 for s in yuzeyler))
    kontrol("enerji filtresi korunur", isinstance(t.filters[1], openmc.EnergyFilter))
    kontrol("skor current", list(t.scores) == ["current"])


def test_kurucu_kutu_tallysi_ve_denge():
    print("\n[Y7Y-3] kurucu: kutu agi = MeshSurfaceFilter; esli denge tally'si ayni ag")
    import openmc
    from cekirdek import kurucu, yuzey_akim as y
    # Arrange
    spec = _kure(y.filtre_kutu([1, 1, 1], alt=[-10, -10, -10], ust=[10, 10, 10]))
    # Act
    model, _b = kurucu.kur(spec)
    adlar = {t.name: t for t in model.tallies}
    t, d = adlar["kacak"], adlar.get(y.denge_adi("kacak"))
    # Assert
    kontrol("MeshSurfaceFilter", isinstance(t.filters[0], openmc.MeshSurfaceFilter))
    kontrol("sinirlar elle", tuple(t.filters[0].mesh.lower_left) == (-10, -10, -10))
    kontrol("denge tally'si var", d is not None)
    kontrol("denge: MeshFilter ayni ag", isinstance(d.filters[0], openmc.MeshFilter)
            and d.filters[0].mesh is t.filters[0].mesh)
    kontrol("denge skorlari: absorption, nu-fission, (n,2n) ...",
            {"absorption", "nu-fission", "(n,2n)"} <= set(d.scores))


def test_kutu_otomatik_sinirlari_model_kutusu():
    print("\n[Y7Y-4] kutu otomatik: sinirlar kurucu.tally_mesh_sinirlari ile ayni")
    from cekirdek import kurucu, yuzey_akim as y
    # Arrange
    spec = _kure(y.filtre_kutu([2, 2, 2]))
    # Act
    model, bilgi = kurucu.kur(spec)
    t = next(t for t in model.tallies if t.name == "kacak")
    alt, ust = kurucu.tally_mesh_sinirlari(spec, spec["tallyler"][0]["filtreler"][0],
                                           bilgi["sinir_kutu"])
    # Assert
    kontrol("ayni sinirlar", list(t.filters[0].mesh.lower_left) == list(alt)
            and list(t.filters[0].mesh.upper_right) == list(ust))


def test_vakum_yoksa_sinir_tallysi_kurulmaz():
    print("\n[Y7Y-5] yansiticili pin hucrede sinir tally'si kurulmaz (kacak tanimca 0)")
    from cekirdek import kurucu, yuzey_akim as y
    # Arrange
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    spec["tallyler"] = [dict(sema.tally("kacak", ["current"]), filtreler=[y.filtre_sinir()])]
    # Act
    model, _b = kurucu.kur(spec)
    # Assert
    kontrol("tally yok", "kacak" not in {t.name for t in model.tallies})


def test_kurucu_ve_betik_ayni_yuzey_tallyleri():
    print("\n[Y7Y-6] kurucu ve uretilen betik AYNI yuzey tally'lerini kurar")
    from cekirdek import kurucu, yuzey_akim as y
    # Arrange
    spec = _kure(y.filtre_sinir(), sema.filtre_enerji([1e-5, 1.0, 2e7]))
    spec["tallyler"].append(dict(sema.tally("kutu", ["current"]),
                                 filtreler=[y.filtre_kutu([2, 1, 1])]))
    # Act
    a = _tally_ozeti(kurucu.kur(spec)[0])
    b = _tally_ozeti(_betik_modeli(spec))
    # Assert
    kontrol("ayni adlar", set(a) == set(b), "-> %s / %s" % (sorted(a), sorted(b)))
    kontrol("ayni skor ve filtreler", a == b,
            "-> fark %s" % {k for k in set(a) | set(b) if a.get(k) != b.get(k)})
    kontrol("denge tally'si betikte de", y.denge_adi("kutu") in b)


# ---------------------------------------------------------------------------
# dogrulama
# ---------------------------------------------------------------------------

def _bulgular(spec):
    from cekirdek.dogrula import yuzey
    return yuzey.yuzey_kontrol(spec)


def test_dogrula_yuzey_skoru_yalniz_current():
    print("\n[Y7Y-7] yuzey tally'sinde current disi skor -> hata (OpenMC durur)")
    from cekirdek import yuzey_akim as y
    # Arrange
    spec = _kure(y.filtre_kutu([1, 1, 1]))
    spec["tallyler"][0]["skorlar"] = ["current", "flux"]
    # Act
    b = _bulgular(spec)
    # Assert
    kontrol("hata", any(x.seviye == "hata" and "current" in x.mesaj for x in b),
            "-> %s" % [x.mesaj for x in b])


def test_dogrula_kutu_sinirlari_ve_boyut():
    print("\n[Y7Y-8] kutu: alt >= ust ya da boyut < 1 -> hata")
    from cekirdek import yuzey_akim as y
    # Arrange
    ters = _kure(y.filtre_kutu([1, 1, 1], alt=[5, 0, 0], ust=[0, 1, 1]))
    sifir = _kure(y.filtre_kutu([0, 1, 1]))
    # Act / Assert
    kontrol("ters sinir hata", any(x.seviye == "hata" for x in _bulgular(ters)))
    kontrol("sifir bolme hata", any(x.seviye == "hata" for x in _bulgular(sifir)))


def test_dogrula_iki_yuzey_filtresi_ve_onek():
    print("\n[Y7Y-9] iki yuzey filtresi bir arada ya da y7_ oneki -> hata")
    from cekirdek import yuzey_akim as y
    # Arrange
    iki = _kure(y.filtre_sinir(), y.filtre_kutu([1, 1, 1]))
    onek = _kure(y.filtre_sinir(), ad="y7_benim")
    # Act / Assert
    kontrol("iki filtre hata", any(x.seviye == "hata" for x in _bulgular(iki)))
    kontrol("onek hata", any(x.seviye == "hata" and "y7_" in x.mesaj for x in _bulgular(onek)))


def test_dogrula_vakumsuz_modelde_sinir_uyarisi():
    print("\n[Y7Y-10] vakum siniri olmayan modelde sinir tally'si -> uyari")
    from cekirdek import yuzey_akim as y
    # Arrange
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    spec["tallyler"] = [dict(sema.tally("kacak", ["current"]), filtreler=[y.filtre_sinir()])]
    # Act
    b = _bulgular(spec)
    # Assert
    kontrol("uyari", any(x.seviye == "uyari" for x in b), "-> %s" % [x.mesaj for x in b])


def test_temiz_yuzey_tallysi_bulgusuz_ve_tum_kontrollerde():
    print("\n[Y7Y-11] gecerli yuzey tally'si temiz; dogrula.tum_kontroller kurali calistirir")
    from cekirdek import dogrula, yuzey_akim as y
    # Arrange
    temiz = _kure(y.filtre_sinir())
    bozuk = _kure(y.filtre_kutu([0, 1, 1]))
    # Act
    b = _bulgular(temiz)
    t = dogrula.tum_kontroller(bozuk, veri_kontrolu=False)
    # Assert
    kontrol("temiz", not [x for x in b if x.seviye in ("hata", "uyari")],
            "-> %s" % [x.mesaj for x in b])
    kontrol("tum_kontroller hata", any(x.yer == "tally:kacak" and x.seviye == "hata" for x in t))


# ---------------------------------------------------------------------------
# saf hesaplar
# ---------------------------------------------------------------------------

def _kutu_df(nx=1, akim=None):
    """Sentetik MeshSurfaceFilter tablosu (OpenMC sutun duzeni)."""
    import pandas as pd
    yuzler = ("x-min out", "x-min in", "x-max out", "x-max in", "y-min out", "y-min in",
              "y-max out", "y-max in", "z-min out", "z-min in", "z-max out", "z-max in")
    satirlar = []
    for ix in range(1, nx + 1):
        for yuz in yuzler:
            deger = (akim or {}).get((ix, yuz), 0.0)
            satirlar.append({("mesh 1", "x"): ix, ("mesh 1", "y"): 1, ("mesh 1", "z"): 1,
                             ("mesh 1", "surf"): yuz, ("nuclide", ""): "total",
                             ("score", ""): "current", ("mean", ""): deger,
                             ("std. dev.", ""): 0.1 * deger})
    df = pd.DataFrame(satirlar)
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    return df


def test_kutu_dis_yuzleri_ic_yuzleri_saymaz():
    print("\n[Y7Y-12] iki hucreli kutu: ic yuz (1 x-max / 2 x-min) giren/cikana katilmaz")
    from cekirdek import yuzey_akim as y
    # Arrange: 1. hucre x-min'den 0.3 cikar, ic yuzden 2. hucreye 0.5 gecer
    df = _kutu_df(nx=2, akim={(1, "x-min out"): 0.3, (1, "x-max out"): 0.5,
                              (2, "x-min in"): 0.5, (2, "x-max out"): 0.1,
                              (2, "y-max in"): 0.2})
    # Act
    o = y.kutu_akimlari(df, (2, 1, 1))
    # Assert
    kontrol("cikan = 0.3 + 0.1", abs(o["cikan"].ort - 0.4) < _TOL, "-> %r" % (o["cikan"],))
    kontrol("giren = 0.2", abs(o["giren"].ort - 0.2) < _TOL)
    kontrol("x-max cikan (dis yuz) 0.1", abs(o["yuzler"]["x-max"]["cikan"].ort - 0.1) < _TOL)
    kontrol("sapma karelerle", abs(o["cikan"].sapma - math.hypot(0.03, 0.01)) < _TOL)


def test_denge_artigi_el_hesabi():
    print("\n[Y7Y-13] denge: S + giren - cikan + X - A = artik (birlesik sapma)")
    from cekirdek import yuzey_akim as y
    from cekirdek.spektrum import Deger
    # Act
    d = y.denge(giren=Deger(0.2, 0.01), cikan=Deger(0.9, 0.02), kaynak=Deger(1.0, 0.0),
                xn=Deger(0.01, 0.001), sogurma=Deger(0.31, 0.01))
    # Assert
    kontrol("artik 0", abs(d["artik"].ort) < _TOL, "-> %r" % (d["artik"],))
    kontrol("sapma", abs(d["artik"].sapma - math.sqrt(0.01**2 + 0.02**2 + 0.001**2 + 0.01**2))
            < _TOL)
    kontrol("kaynak bilinmiyorsa artik None",
            y.denge(Deger(1, 0), Deger(1, 0), None, Deger(0, 0), Deger(0, 0))["artik"] is None)


def test_kacak_spektrumu_yuzeyler_toplanir():
    print("\n[Y7Y-14] sinir tally'si: yuzeyler toplanir, enerji gruplari ayri")
    import pandas as pd
    from cekirdek import yuzey_akim as y
    # Arrange: iki yuzey, iki grup
    df = pd.DataFrame({"surface": [1, 1, 2, 2],
                       "energy low [eV]": [0.0, 1.0, 0.0, 1.0],
                       "energy high [eV]": [1.0, 2e7, 1.0, 2e7],
                       "nuclide": ["total"] * 4, "score": ["current"] * 4,
                       "mean": [0.1, 0.2, -0.05, -0.15], "std. dev.": [0.01] * 4})
    # Act
    o = y.sinir_akimlari(df)
    # Assert
    kontrol("yuzey 1 = 0.3", abs(o["yuzeyler"][1].ort - 0.3) < _TOL)
    kontrol("yuzey 2: |-0.2| (vakumda her gecis disari, isaret normalden)",
            abs(o["yuzeyler"][2].ort - 0.2) < _TOL)
    kontrol("toplam kacak 0.5", abs(o["toplam"].ort - 0.5) < _TOL)
    kontrol("spektrum: kenarlar ve degerler",
            o["spektrum"]["kenarlar"] == [0.0, 1.0, 2e7]
            and all(abs(a - b) < _TOL for a, b in zip(o["spektrum"]["deger"], [0.15, 0.35])))


def test_kaynak_payi_nokta_kaynak():
    print("\n[Y7Y-15] kutu icindeki nokta kaynak payi: sabit kaynakta siddet, disarida 0")
    from cekirdek import yuzey_akim as y
    # Arrange
    spec = _kure(y.filtre_kutu([1, 1, 1], alt=[-10, -10, -10], ust=[10, 10, 10]))
    disarida = _kure(y.filtre_kutu([1, 1, 1], alt=[1, 1, 1], ust=[10, 10, 10]))
    # Act
    ic = y.kutu_kaynagi(spec, ([-10, -10, -10], [10, 10, 10]))
    dis = y.kutu_kaynagi(disarida, ([1, 1, 1], [10, 10, 10]))
    # Assert
    kontrol("icerde = kuvvet", ic is not None and ic.ort == spec["ayarlar"]["kaynak"]["kuvvet"])
    kontrol("disarida 0", dis is not None and dis.ort == 0.0)


HIZLI = [test_yuzey_filtre_yapicilari_ve_tanima, test_kurucu_sinir_tallysi_vakum_yuzeyleri,
         test_kurucu_kutu_tallysi_ve_denge, test_kutu_otomatik_sinirlari_model_kutusu,
         test_vakum_yoksa_sinir_tallysi_kurulmaz, test_kurucu_ve_betik_ayni_yuzey_tallyleri,
         test_dogrula_yuzey_skoru_yalniz_current, test_dogrula_kutu_sinirlari_ve_boyut,
         test_dogrula_iki_yuzey_filtresi_ve_onek, test_dogrula_vakumsuz_modelde_sinir_uyarisi,
         test_temiz_yuzey_tallysi_bulgusuz_ve_tum_kontrollerde,
         test_kutu_dis_yuzleri_ic_yuzleri_saymaz, test_denge_artigi_el_hesabi,
         test_kacak_spektrumu_yuzeyler_toplanir, test_kaynak_payi_nokta_kaynak]
YAVAS = []
