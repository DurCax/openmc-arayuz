# -*- coding: utf-8 -*-
"""
 test_betik.py  --  6-7. BETIK ESDEGERLIGI: kurucu.py ile uretilen betik ayni k-eff'i verir

 testler/test_regresyon.py'den tasindi (Dalga 0; test metinleri aynen).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

import importlib.util
import os

from cekirdek import sema, kurucu, kod_uret
from testler.ortak_test import kontrol, ISLEM_PARCACIGI
from testler.regresyon_ortak import ORNEK


def test_betik_esdegerligi(gecici):
    print("\n[6] BETIK ESDEGERLIGI -- kurucu.py ile uretilen betik ayni mi")
    import openmc
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    eski = os.getcwd()
    try:
        yol_a = os.path.join(gecici, "yol_a")
        os.makedirs(yol_a, exist_ok=True)
        os.chdir(yol_a)
        model_a, _ = kurucu.kur(spec)
        k_a = openmc.StatePoint(model_a.run(threads=ISLEM_PARCACIGI, output=False)).keff

        yol_b = os.path.join(gecici, "yol_b")
        os.makedirs(yol_b, exist_ok=True)
        os.chdir(yol_b)
        betik = os.path.join(yol_b, "model.py")
        with open(betik, "w", encoding="utf-8") as f:
            f.write(kod_uret.uret(spec, "model.py"))
        sm = importlib.util.spec_from_file_location("uretilen", betik)
        mod = importlib.util.module_from_spec(sm)
        sm.loader.exec_module(mod)
        k_b = openmc.StatePoint(mod.model.run(threads=ISLEM_PARCACIGI, output=False)).keff
    finally:
        os.chdir(eski)
    fark = abs(k_a.nominal_value - k_b.nominal_value)
    kontrol("kurucu %.8f  vs  betik %.8f" % (k_a.nominal_value, k_b.nominal_value),
            fark < 1e-10, "-> fark %.2e" % fark)


# ============================================================================
# ANA GIRIS
# ============================================================================

def test_altigen_betik_esdegerligi(gecici):
    print("\n[7] ALTIGEN BETIK ESDEGERLIGI")
    import openmc
    spec = sema.yukle(os.path.join(ORNEK, "sfr_altigen.json"))
    spec["ayarlar"].update(parcacik=2000, cevrim=30, pasif=10)
    eski = os.getcwd()
    try:
        ya = os.path.join(gecici, "hex_a"); os.makedirs(ya, exist_ok=True)
        os.chdir(ya)
        ma, _ = kurucu.kur(spec)
        ka = openmc.StatePoint(ma.run(threads=ISLEM_PARCACIGI, output=False)).keff
        yb = os.path.join(gecici, "hex_b"); os.makedirs(yb, exist_ok=True)
        os.chdir(yb)
        betik = os.path.join(yb, "model.py")
        with open(betik, "w", encoding="utf-8") as f:
            f.write(kod_uret.uret(spec, "model.py"))
        sm = importlib.util.spec_from_file_location("hexuret", betik)
        mo = importlib.util.module_from_spec(sm)
        sm.loader.exec_module(mo)
        kb = openmc.StatePoint(mo.model.run(threads=ISLEM_PARCACIGI, output=False)).keff
    finally:
        os.chdir(eski)
    fark = abs(ka.nominal_value - kb.nominal_value)
    kontrol("kurucu %.8f vs betik %.8f" % (ka.nominal_value, kb.nominal_value),
            fark < 1e-10, "-> fark %.2e" % fark)


HIZLI = []
YAVAS = [
    test_betik_esdegerligi, test_altigen_betik_esdegerligi,
]
