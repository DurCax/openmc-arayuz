# -*- coding: utf-8 -*-
"""
 test_y4_betik.py  --  v3 Y4: betik esdegerligi (cekirdek/kod_uret/tukenme*.py)

   [Y4-B1] Her entegrator: betikteki sinif = tukenme_ayar.ENTEGRATORLER; SI-*
           icin n_steps; adim plani tukenme_ayar.zaman_plani ile AYNI.
   [Y4-B2] Sogutma: betikteki guc listesi sonda sifirlar; hizli kip
           IndependentOperator + get_microxs_and_flux.
   [Y4-B3] Bor aramasi: betigin gomulu dogrusal tablosu cekirdegin tam
           tarifiyle (tarama "bor_ppm") ayni yogunluklari verir (fark / toplam
           yogunluk < 1e-9; tarifin yuvarlamasi B10da ~5e-5 ppm mutlak);
           ppm > 0 dalinda (0 ppm'de tarif atomca H2O'dur, H 1.2e-5 farkli).
   [Y4-B4] Cubuk aramasi: betik derlenir; add_keff_search_control ve
           translation donusumu iceride.
"""

import ast
import copy
import os

from testler.ortak_test import ORNEK, kontrol


def _spec(ad="pwr_tukenme.json"):
    from cekirdek import sema
    s = sema.yukle(os.path.join(ORNEK, ad))
    s["tukenme"]["var"] = True
    s["tukenme"]["zincir"] = "casl_termal"
    return s


def _betik(spec):
    from cekirdek import kod_uret
    metin = kod_uret.uret(spec, "model.py")
    ast.parse(metin)
    return metin


def _degisken(metin, ad):
    for dugum in ast.parse(metin).body:
        if isinstance(dugum, ast.Assign) and getattr(dugum.targets[0], "id", None) == ad:
            return ast.literal_eval(dugum.value)
    raise KeyError(ad)


def test_entegratorler():
    print("\n[Y4-B1] betik: entegrator sinifi, SI n_steps, adim plani")
    from cekirdek import tukenme_ayar as ta
    for kod, e in ta.ENTEGRATORLER.items():
        s = _spec()
        s["tukenme"]["entegrator"] = kod
        metin = _betik(s)
        kontrol("%s -> openmc.deplete.%s" % (kod, e.sinif), "openmc.deplete.%s(" % e.sinif in metin)
        kontrol("  SI n_steps yalniz SI'de", ("n_steps=10" in metin) == e.si)
        adimlar, guc = ta.zaman_plani(s["tukenme"])
        kontrol("  adimlar ve guc cekirdekle ayni",
                [tuple(a) for a in _degisken(metin, "TUKENME_ADIMLARI")] == adimlar
                and _degisken(metin, "TUKENME_GUC_YOGUNLUGU") == guc)


def test_sogutma_ve_hizli_kip():
    print("\n[Y4-B2] betik: sogutma (guc 0) ve hizli kip")
    s = _spec()
    s["tukenme"]["sogutma"] = {"adimlar": [30.0, 365.0], "birim": "d"}
    metin = _betik(s)
    guc = _degisken(metin, "TUKENME_GUC_YOGUNLUGU")
    kontrol("son iki adim sifir guc", guc[-2:] == [0.0, 0.0] and guc[0] > 0, repr(guc))
    s["tukenme"]["hizli_kip"] = True
    metin = _betik(s)
    kontrol("hizli kip: IndependentOperator + MicroXS",
            "IndependentOperator(" in metin and "get_microxs_and_flux(" in metin
            and "CoupledOperator(" not in metin)


def test_bor_tablosu_dogrusal():
    print("\n[Y4-B3] betik bor tablosu = cekirdek tarifi (dogrusal)")
    from cekirdek import tukenme_arama
    s = _spec()
    s["tukenme"]["kritik_arama"] = {"var": True, "tur": "bor", "hedef": "su",
                                    "alt": 500.0, "ust": 1500.0, "sinir": [0.0, 3000.0]}
    metin = _betik(s)
    y0, egim = _degisken(metin, "_BOR_Y0"), _degisken(metin, "_BOR_EGIM")
    kontrol("add_keff_search_control betikte", "add_keff_search_control(" in metin)
    for ppm in (100.0, 700.0, 2500.0):
        tam = tukenme_arama.bor_yogunluklari(s, "su", ppm)
        betik = {n: y0[n] + ppm * egim[n] for n in y0}
        toplam = sum(tam.values())
        sapma = max(abs(betik.get(n, 0.0) - v) for n, v in tam.items()) / toplam
        kontrol("%g ppm: en buyuk fark / toplam yogunluk %.2e" % (ppm, sapma), sapma < 1e-9)


def test_cubuk_betigi():
    print("\n[Y4-B4] betik: cubuk aramasi derlenir")
    s = _spec("pwr_kontrol.json")
    s["tukenme"]["kritik_arama"] = {"var": True, "tur": "cubuk", "hedef": "kontrol_cubugu",
                                    "alt": 20.0, "ust": 80.0, "sinir": [0.0, 100.0]}
    metin = _betik(copy.deepcopy(s))
    kontrol("translation donusumu ve arama", "openmc.lib.cells[i].translation" in metin
            and "add_keff_search_control(" in metin)


HIZLI = [test_entegratorler, test_sogutma_ve_hizli_kip, test_bor_tablosu_dogrusal,
         test_cubuk_betigi]
VERI_GEREKEN = HIZLI
ZINCIR_GEREKEN = HIZLI
