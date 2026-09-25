# -*- coding: utf-8 -*-
"""
================================================================================
 ortak_test.py  --  Test modullerinin paylastigi sayaclar ve yollar
================================================================================
 Ek test modulleri (testler/test_*.py) bunu ice aktarir; boylece hepsi AYNI
 gecti/kaldi listelerine yazar ve test_regresyon.py'nin ozeti hepsini sayar.

 EK TEST MODULU SOZLESMESI
   testler/test_<ad>.py icinde:
       from testler.ortak_test import kontrol, KOK, ORNEK
       def test_bir_sey(): ...
       def test_yavas_bir_sey(gecici): ...     # Monte Carlo / uzun
       HIZLI = [test_bir_sey]                  # --hizli modda da kosar
       YAVAS = [test_yavas_bir_sey]            # yalnizca tam modda, gecici dizin alir
   test_regresyon.py bu modulleri kendiliginden bulur ve kosar; ayrica
   kaydetmek GEREKMEZ. Boylece paralel calisan gelistiriciler ayni dosyaya
   (ve ayni main() listesine) dokunmaz.
================================================================================
"""

import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)
ORNEK = os.path.join(KOK, "ornekler")


def _ayarlari_yalit():
    """Testler kullanicinin GERCEK uygulama ayarlarina (son kullanilanlar,
    tema, Gelismis bolum durumu) yazmasin. Onceden test gecici projeleri
    ~/.config/openmc_arayuz/arayuz.conf'taki "Son kullanilanlar" listesine
    dusuyordu. Qt ayar yolunu XDG_CONFIG_HOME'dan okur; ortam degiskeni alt
    sureclere de gecer. PySide6 yuklenmisse yol ayrica acikca yonlendirilir."""
    import atexit
    import shutil
    import tempfile
    dizin = tempfile.mkdtemp(prefix="openmc_arayuz_ayar_")
    os.environ["XDG_CONFIG_HOME"] = dizin
    atexit.register(shutil.rmtree, dizin, True)
    try:
        from PySide6 import QtCore
    except ImportError:
        return dizin
    for bicim in (QtCore.QSettings.NativeFormat, QtCore.QSettings.IniFormat):
        QtCore.QSettings.setPath(bicim, QtCore.QSettings.UserScope, dizin)
    return dizin


AYAR_DIZINI = _ayarlari_yalit()

_gecti = []
_kaldi = []


def kontrol(baslik, kosul, ayrinti=""):
    if kosul:
        _gecti.append(baslik)
        print("  [GECTI] %s %s" % (baslik, ayrinti))
    else:
        _kaldi.append(baslik)
        print("  [KALDI] %s %s" % (baslik, ayrinti))
    return kosul


def ek_moduller():
    """testler/ altindaki ek test modulleri (test_regresyon haric), sirali."""
    import glob
    import importlib
    adlar = sorted(os.path.splitext(os.path.basename(p))[0]
                   for p in glob.glob(os.path.join(KOK, "testler", "test_*.py")))
    return [importlib.import_module("testler." + a) for a in adlar
            if a != "test_regresyon"]
