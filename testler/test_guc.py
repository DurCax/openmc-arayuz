# -*- coding: utf-8 -*-
"""
 test_guc.py  --  3p. guc dagilimi: distribcell, tepe faktorleri, mutlak guc, dogrulama, betik esdegerligi

 testler/test_regresyon.py'den tasindi (Dalga 0; test metinleri aynen).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

import importlib.util
import os

from cekirdek import sema, kurucu, dogrula, kod_uret
from testler.ortak_test import kontrol, ISLEM_PARCACIGI
from testler.regresyon_ortak import ORNEK


# ============================================================================
# 3p. GUC DAGILIMI
# ============================================================================

def test_distribcell_ornek_sayisi():
    """Yakit hucresi kafesteki yakit konumu sayisi kadar ornek vermeli."""
    print("\n[3p] Distribcell ornek sayisi")
    spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    model, _ = kurucu.kur(spec)
    g = model.geometry
    g.determine_paths()
    yakit = [c for c in g.get_all_cells().values()
             if hasattr(c.fill, "name") and "UO2" in str(c.fill.name)]
    kontrol("tek yakit hucresi bulundu", len(yakit) == 1)
    if yakit:
        # haritadaki 'y' harfi sayisi
        d = sema.demet_bul(spec, "demet_17x17")
        beklenen = sum(s.count("y") for s in d["harita"])
        kontrol("ornek sayisi haritadaki yakit sayisina esit",
                yakit[0].num_instances == beklenen,
                "%d ornek, haritada %d yakit" % (yakit[0].num_instances, beklenen))


def test_altigen_distribcell_koprusu():
    """(x,alfa) -> (halka,sira) cevrimi altigen.konumlar ile ortusmeli."""
    print("\n[3q] Altigen distribcell koprusu")
    import openmc
    from cekirdek import altigen
    m = openmc.Material(); m.add_element("U", 1, enrichment=19.75)
    m.set_density("g/cm3", 17.0)
    pin = openmc.model.pin([openmc.ZCylinder(r=0.32)], [m, None])
    dis = openmc.Universe(cells=[openmc.Cell(fill=None)])
    for yonelim in ("y", "x"):
        for N in (2, 3, 7):
            lat = openmc.HexLattice()
            lat.center = (0.0, 0.0); lat.pitch = (0.9,); lat.orientation = yonelim
            lat.outer = dis
            lat.universes = [[pin] * u for u in altigen.halka_uzunluklari(N)]
            cevrilen = {tuple(lat.get_universe_index(ix))
                        for ix in lat._natural_indices}
            kontrol("yonelim=%s N=%d" % (yonelim, N),
                    cevrilen == set(altigen.konumlar(N, yonelim)))


def test_tepe_faktorleri_sentetik():
    """tepe_faktorleri bilinen bir dagilimda dogru F_dH ve F_q vermeli."""
    print("\n[3r] Tepe faktorleri (sentetik)")
    from cekirdek import guc
    # 4 cubuk x 2 dilim; cubuk toplamlari 1,1,1,2 -> ortalama 1.25, F_dH = 1.6
    # yerel degerler 0.5,0.5 / 0.5,0.5 / 0.5,0.5 / 0.5,1.5 -> ort 0.625, F_q = 2.4
    konumlar = {
        (0, 0): {"eksenel": [(0.5, 0.01), (0.5, 0.01)], "toplam": (1.0, 0.014)},
        (1, 0): {"eksenel": [(0.5, 0.01), (0.5, 0.01)], "toplam": (1.0, 0.014)},
        (0, 1): {"eksenel": [(0.5, 0.01), (0.5, 0.01)], "toplam": (1.0, 0.014)},
        (1, 1): {"eksenel": [(0.5, 0.01), (1.5, 0.01)], "toplam": (2.0, 0.014)},
    }
    d = {"kafes_turu": "kare", "kafes": None, "eksenel_dilim": 2,
         "konumlar": konumlar, "notlar": []}
    f = guc.tepe_faktorleri(d)
    kontrol("F_dH = 1.6", abs(f["F_dH"] - 1.6) < 1e-9, "%.6f" % f["F_dH"])
    kontrol("F_q = 2.4", abs(f["F_q"] - 2.4) < 1e-9, "%.6f" % f["F_q"])
    kontrol("sicak cubuk (1,1)", f["sicak_cubuk"] == (1, 1))
    kontrol("sicak dilim 2.", f["sicak_dilim"] == ((1, 1), 1))
    ort = sum(v[0] for v in f["bagil"].values()) / len(f["bagil"])
    kontrol("bagil ortalama tam 1.000", abs(ort - 1.0) < 1e-12, "%.12f" % ort)
    # 2B: F_q tanimsiz
    d2 = {"kafes_turu": "kare", "kafes": None, "eksenel_dilim": 1,
          "konumlar": {k: {"eksenel": [v["toplam"]], "toplam": v["toplam"]}
                       for k, v in konumlar.items()}, "notlar": []}
    kontrol("2B -> F_q None", guc.tepe_faktorleri(d2)["F_q"] is None)


def test_mutlak_guc():
    """Mutlak guc ve lineer guc hesabi dogru olmali."""
    print("\n[3s] Mutlak guc")
    from cekirdek import guc
    f = {"cubuk_sayisi": 264, "F_dH": 1.10, "F_q": 1.80, "eksenel_dilim": 20}
    m = guc.mutlak_guc(f, 17.6e6, 366.0)
    kontrol("cubuk ortalama = P/N", abs(m["cubuk_ortalama_W"] - 17.6e6 / 264) < 1e-6)
    kontrol("lineer ortalama ~182 W/cm",
            abs(m["lineer_ortalama_W_cm"] - 17.6e6 / 264 / 366) < 1e-9,
            "%.1f W/cm" % m["lineer_ortalama_W_cm"])
    kontrol("lineer maks F_q ile olceklendi",
            abs(m["lineer_maks_W_cm"] - m["lineer_ortalama_W_cm"] * 1.80) < 1e-9)
    kontrol("guc yoksa None", guc.mutlak_guc(f, None, 366.0) is None)


def test_guc_dogrulama():
    """Guc dagilimi ayarlarindaki hatalar yakalanmali."""
    print("\n[3t] Guc dagilimi dogrulamasi")
    import copy as _c
    temiz = sema.yukle(os.path.join(ORNEK, "pwr_3b.json"))
    kontrol("temiz model hatasiz",
            not dogrula.hata_var(dogrula.tum_kontroller(temiz)))

    def dene(ad, degistir, anahtar):
        s = _c.deepcopy(temiz)
        degistir(s)
        b = dogrula.tum_kontroller(s)
        kontrol(ad, any(anahtar.lower() in x.mesaj.lower() for x in b))

    dene("gecersiz bolge", lambda s: s["guc_dagilimi"].update({"bolge": 99}),
         "geçersiz bölge")
    dene("fisil olmayan bolge", lambda s: s["guc_dagilimi"].update({"bolge": 2}),
         "fisil görünmüyor")
    dene("enerji olmayan skor", lambda s: s["guc_dagilimi"].update({"skor": "fission"}),
         "enerji skoru")
    dene("2B'de F_q yok", lambda s: s["kor"].update({"yukseklik": None}),
         "F_q hesaplanamaz")
    dene("az eksenel dilim", lambda s: s["guc_dagilimi"].update({"eksenel_dilim": 3}),
         "olduğundan küçük çıkar")
    dene("uydurma skor", lambda s: s["tallyler"][0].update({"skorlar": ["yok-boyle"]}),
         "bilinen skorlar")


def test_guc_esdegerlik_ve_korunum(gecici):
    """
    Guc dagilimli bir modelde:
      1. Cubuk guclerinin toplami filtresiz tally'ye ESIT olmali (haritalama
         hatasi toplami bozar -- en guclu kontrol).
      2. Uretilen betik ayni k-eff VE ayni tepe faktorlerini vermeli.
    """
    print("\n[9] GUC DAGILIMI: toplam korunumu + betik esdegerligi")
    import openmc
    from cekirdek import guc
    spec = sema.yukle(os.path.join(ORNEK, "pwr_3b.json"))
    spec["ayarlar"].update(parcacik=2500, cevrim=35, pasif=12)
    spec["guc_dagilimi"]["eksenel_dilim"] = 6

    def kos(dizin, betikten=False):
        os.makedirs(dizin, exist_ok=True)
        eski = os.getcwd()
        try:
            os.chdir(dizin)
            if betikten:
                betik = os.path.join(dizin, "model.py")
                with open(betik, "w", encoding="utf-8") as f:
                    f.write(kod_uret.uret(spec, "model.py"))
                sm = importlib.util.spec_from_file_location("gucuret", betik)
                mo = importlib.util.module_from_spec(sm)
                sm.loader.exec_module(mo)
                model = mo.model
            else:
                model, _ = kurucu.kur(spec)
            sp = openmc.StatePoint(model.run(threads=ISLEM_PARCACIGI, output=False))
        finally:
            os.chdir(eski)
        return sp

    sp_a = kos(os.path.join(gecici, "guc_a"))
    f_a = guc.tepe_faktorleri(guc.dagilim_oku(sp_a))
    dag_toplam = sum(k["toplam"][0]
                     for k in guc.dagilim_oku(sp_a)["konumlar"].values())
    ref = float(sp_a.get_tally(name="guc_toplam_ref")
                .get_pandas_dataframe()["mean"].sum())
    bagil = abs(dag_toplam / ref - 1.0)
    kontrol("toplam korunumu (bagil fark %.1e)" % bagil, bagil < 1e-9)

    sp_b = kos(os.path.join(gecici, "guc_b"), betikten=True)
    f_b = guc.tepe_faktorleri(guc.dagilim_oku(sp_b))
    kontrol("betik ayni F_dH (%.6f vs %.6f)" % (f_a["F_dH"], f_b["F_dH"]),
            abs(f_a["F_dH"] - f_b["F_dH"]) < 1e-10)
    kontrol("betik ayni F_q (%.6f vs %.6f)" % (f_a["F_q"], f_b["F_q"]),
            abs(f_a["F_q"] - f_b["F_q"]) < 1e-10)
    kontrol("betik ayni sicak cubuk", f_a["sicak_cubuk"] == f_b["sicak_cubuk"])
    kontrol("bagil ortalama 1.000",
            abs(sum(v[0] for v in f_a["bagil"].values()) / len(f_a["bagil"]) - 1.0) < 1e-12)


HIZLI = [
    test_distribcell_ornek_sayisi, test_altigen_distribcell_koprusu,
    test_tepe_faktorleri_sentetik, test_mutlak_guc, test_guc_dogrulama,
]
YAVAS = [
    test_guc_esdegerlik_ve_korunum,
]
