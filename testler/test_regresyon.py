# -*- coding: utf-8 -*-
"""
================================================================================
 test_regresyon.py  --  Test calistiricisi (butun testler/test_*.py modulleri)
================================================================================

 KULLANIM
   python3 testler/test_regresyon.py            # tum testler (Monte Carlo dahil)
   python3 testler/test_regresyon.py --hizli    # kosu gerektirmeyen testler
   python3 -m testler.test_regresyon [--hizli]

 Testlerin kendisi konu modullerindedir (Dalga 0'da bu dosyadan tasindi;
 sozlesme testler/ortak_test.py: HIZLI / YAVAS listeleri, kendiliginden
 bulunur). Eski numaralar ve yeni yerleri:
   1-2.     Dogrulama: temiz ornekler, bozuk modeller    -> test_dogrulama.py
   3-4.     Geometri olculeri, cizim, altigen kafes        -> test_geometri.py
   3f-3i.   Entropi, onbellek, tarama, kritik arama        -> test_kosu_yardimcilari.py
   3p.      Guc dagilimi                                   -> test_guc.py
   3u.      Kontrol cubugu                                 -> test_kontrol_cubugu.py
   3y.      Kontrol tamburu                                -> test_tambur.py
   5.       REGRESYON CIPASI: pin hucre k-inf = 1.3570 +/- 0.0020 (2 sigma)
            ve Godiva kritiklik olcutu                     -> test_capa.py
   6-7.     BETIK ESDEGERLIGI: kurucu.py ve uretilen betik
            ayni k-eff'i verir                             -> test_betik.py
   12-13.   KAYNAK TAYFI, ANALITIK ZAYIFLATMA              -> test_kaynak.py
   14-16.   EKSENEL HETEROJENLIK, onizleme                 -> test_eksenel.py
   17-18.   TUKENME: zincir, Bateman, kosu, Xe dengesi     -> test_tukenme_temel.py
   18a-18r. ARAYUZ HATA AVI                                -> test_arayuz_hata_avi.py,
                                                              test_arayuz_pencere.py
   Ortak yardimcilar (test modulu degil)                   -> regresyon_ortak.py

 5 ve 6 numarali testler bu katmanin dogru oldugunun tek gercek kanitidir.
 kurucu.py ya da kod_uret.py degistirilirse mutlaka tekrar kosulmalidir.
================================================================================
"""

import os
import shutil
import sys
import tempfile
import warnings

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
warnings.filterwarnings("ignore")

# Sayaclar ve kontrol() ortak modulde: ek test modulleri (testler/test_*.py)
# AYNI listelere yazsin ve ozet hepsini saysin. Bkz. testler/ortak_test.py.
from testler.ortak_test import _gecti, _kaldi, ek_moduller   # noqa: E402


def main(argv):
    hizli = "--hizli" in argv
    print("=" * 74)
    print(" openmc_arayuz cekirdek regresyon testleri%s" % (" (HIZLI MOD)" if hizli else ""))
    print("=" * 74)

    # --- test modulleri: hizli testler ---
    moduller = ek_moduller()
    for m in moduller:
        for fn in getattr(m, "HIZLI", []):
            fn()

    if not hizli:
        gecici = tempfile.mkdtemp(prefix="openmc_arayuz_test_")
        try:
            for m in moduller:
                for fn in getattr(m, "YAVAS", []):
                    fn(gecici)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)
    else:
        print("\n[5-11] Monte Carlo testleri atlandi (--hizli)")

    print("\n" + "=" * 74)
    print(" SONUC: %d gecti, %d kaldi" % (len(_gecti), len(_kaldi)))
    if _kaldi:
        print(" KALAN TESTLER:")
        for t in _kaldi:
            print("   - %s" % t)
    print("=" * 74)
    return 1 if _kaldi else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
