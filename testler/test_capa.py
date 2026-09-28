# -*- coding: utf-8 -*-
"""
 test_capa.py  --  5. REGRESYON CIPASI (pin hucre k-inf) ve Godiva kritiklik olcutu (Monte Carlo)

 testler/test_regresyon.py'den tasindi (Dalga 0; test metinleri aynen).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

import os

from cekirdek import sema, kurucu
from testler.ortak_test import kontrol, ISLEM_PARCACIGI
from testler.regresyon_ortak import ORNEK, REFERANS_K, REFERANS_SAPMA


# ============================================================================
# 5-6. MONTE CARLO (yavas)
# ============================================================================

def test_regresyon_cipasi(gecici):
    print("\n[5] REGRESYON CIPASI -- pin hucre k-inf")
    import openmc
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    dizin = os.path.join(gecici, "cipa")
    os.makedirs(dizin, exist_ok=True)
    eski = os.getcwd()
    try:
        os.chdir(dizin)
        model, _ = kurucu.kur(spec)
        k = openmc.StatePoint(model.run(threads=ISLEM_PARCACIGI, output=False)).keff
    finally:
        os.chdir(eski)
    fark = abs(k.nominal_value - REFERANS_K)
    sigma = (k.std_dev ** 2 + REFERANS_SAPMA ** 2) ** 0.5
    kontrol("k-inf = %.5f +/- %.5f (referans %.4f)" % (k.nominal_value, k.std_dev, REFERANS_K),
            fark < 2 * sigma, "-> %.2f sigma" % (fark / sigma))


def test_godiva_kriteri(gecici):
    """
    ICSBEP HEU-MET-FAST-001 (Godiva) kriteri: yayimlanmis k_eff = 1.0000 +/- 0.0010.

    Bu test regresyon cipasindan FARKLIDIR: cipa "kod kendiyle tutarli" der,
    bu test "sonuc gercekten dogru" der. Malzeme bilesimi, geometri, tesir
    kesiti kutuphanesi ve tasima zincirinin tamami bagimsiz bir olcume
    karsi sinanir.
    """
    print("\n[8] GODIVA KRITERI (ICSBEP HEU-MET-FAST-001)")
    import math
    import openmc
    spec = sema.yukle(os.path.join(ORNEK, "godiva_kriter.json"))
    spec["ayarlar"].update(parcacik=15000, cevrim=140, pasif=40)
    dizin = os.path.join(gecici, "godiva")
    os.makedirs(dizin, exist_ok=True)
    eski = os.getcwd()
    try:
        os.chdir(dizin)
        model, _ = kurucu.kur(spec)
        k = openmc.StatePoint(model.run(threads=ISLEM_PARCACIGI, output=False)).keff
    finally:
        os.chdir(eski)
    KRITER, KRITER_S = 1.0000, 0.0010
    fark = abs(k.nominal_value - KRITER)
    top = math.sqrt(k.std_dev ** 2 + KRITER_S ** 2)
    kontrol("k = %.5f +/- %.5f  (kriter %.4f +/- %.4f)"
            % (k.nominal_value, k.std_dev, KRITER, KRITER_S),
            fark < 2 * top, "-> %.2f sigma" % (fark / top))


HIZLI = []
YAVAS = [
    test_regresyon_cipasi, test_godiva_kriteri,
]
