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


def _gunlugu_yalit():
    """Testler kullanicinin GERCEK log dosyasina (~/.local/state/...)
    yazmasin: cekirdek.gunluk yolu XDG_STATE_HOME'dan okur."""
    import atexit
    import shutil
    import tempfile
    dizin = tempfile.mkdtemp(prefix="openmc_arayuz_durum_")
    os.environ["XDG_STATE_HOME"] = dizin
    atexit.register(shutil.rmtree, dizin, True)
    return dizin


DURUM_DIZINI = _gunlugu_yalit()


# ---------------------------------------------------------------------------
# TEST_SURE=1: test islevi basina sure olcumu (calistiriciya dokunmadan)
# ---------------------------------------------------------------------------
# Eski calistirici test islevlerini dogrudan cagirir; sarmalamak icin her
# modulu degistirmek gerekirdi. Onun yerine yorumlayicinin izleme kancasi
# kullanilir: testler/ altinda tanimli ve adi "test_" ile baslayan her islevin
# baslangic/bitis anlari olculur. Ilgisiz kod yerlerinde olay kapatilir
# (sys.monitoring.DISABLE), boylece ek yuk ihmal edilebilir kalir.

SURELER = []            # [(sure_sn, "modul:islev", derinlik)]
_TESTLER_DIZINI = os.path.join(KOK, "testler") + os.sep
_SURE_ARACI = 4         # sys.monitoring arac kimligi (0-5 serbest)
_EN_YAVAS_SAYI = 20


def _test_kodu_mu(kod):
    return (kod.co_name.startswith("test_")
            and kod.co_filename.startswith(_TESTLER_DIZINI))


def _sure_etiketi(kod):
    modul = os.path.splitext(os.path.basename(kod.co_filename))[0]
    return "%s:%s" % (modul, kod.co_name)


class _SureOlcer:
    def __init__(self):
        import time
        self._saat = time.perf_counter
        self._yigin = []          # [(kod, baslangic)]

    def basla(self, kod):
        self._yigin.append((kod, self._saat()))

    def bitir(self, kod):
        if not self._yigin or self._yigin[-1][0] is not kod:
            return
        _, t0 = self._yigin.pop()
        sure = self._saat() - t0
        SURELER.append((sure, _sure_etiketi(kod), len(self._yigin)))
        print("  [SURE] %8.2f s  %s" % (sure, _sure_etiketi(kod)))


def _monitoring_kur(olcer):
    mon = sys.monitoring
    olaylar = mon.events

    def _basla(kod, _ofset):
        if not _test_kodu_mu(kod):
            return mon.DISABLE
        olcer.basla(kod)

    def _bitir(kod, _ofset, _deger):
        if not _test_kodu_mu(kod):
            return mon.DISABLE
        olcer.bitir(kod)

    def _cozul(kod, _ofset, _istisna):
        if _test_kodu_mu(kod):
            olcer.bitir(kod)

    mon.use_tool_id(_SURE_ARACI, "openmc_arayuz_test_sure")
    mon.register_callback(_SURE_ARACI, olaylar.PY_START, _basla)
    mon.register_callback(_SURE_ARACI, olaylar.PY_RETURN, _bitir)
    mon.register_callback(_SURE_ARACI, olaylar.PY_UNWIND, _cozul)
    mon.set_events(_SURE_ARACI,
                   olaylar.PY_START | olaylar.PY_RETURN | olaylar.PY_UNWIND)


def _profil_kur(olcer):
    """Python < 3.12 icin yedek (sys.monitoring yok): sys.setprofile."""
    def _kanca(cerceve, olay, _arg):
        kod = cerceve.f_code
        if not _test_kodu_mu(kod):
            return
        if olay == "call":
            olcer.basla(kod)
        elif olay == "return":
            olcer.bitir(kod)
    sys.setprofile(_kanca)


def sure_ozeti(sayi=_EN_YAVAS_SAYI):
    """En yavas `sayi` ust duzey test islevi, azalan sirada."""
    ust = [s for s in SURELER if s[2] == 0]
    return sorted(ust, reverse=True)[:sayi]


def _sure_ozetini_yaz():
    ozet = sure_ozeti()
    if not ozet:
        return
    toplam = sum(s[0] for s in SURELER if s[2] == 0)
    print("\n" + "=" * 74)
    print(" EN YAVAS %d TEST ISLEVI (toplam olculen %.1f s)" % (len(ozet), toplam))
    for sure, etiket, _ in ozet:
        print("   %8.2f s  %s" % (sure, etiket))
    print("=" * 74)


def sure_olcumunu_kur():
    """TEST_SURE=1 ise olcumu baslatir; cikista en yavas 20'yi yazar.
    Birden cok cagri zararsizdir. Olcum kurulduysa True doner."""
    if getattr(sure_olcumunu_kur, "_kuruldu", False):
        return True
    import atexit
    olcer = _SureOlcer()
    if hasattr(sys, "monitoring"):
        _monitoring_kur(olcer)
    else:
        _profil_kur(olcer)
    atexit.register(_sure_ozetini_yaz)
    sure_olcumunu_kur._kuruldu = True
    return True


if os.environ.get("TEST_SURE", "") not in ("", "0"):
    sure_olcumunu_kur()


def ek_moduller():
    """testler/ altindaki ek test modulleri (test_regresyon haric), sirali."""
    import glob
    import importlib
    adlar = sorted(os.path.splitext(os.path.basename(p))[0]
                   for p in glob.glob(os.path.join(KOK, "testler", "test_*.py")))
    return [importlib.import_module("testler." + a) for a in adlar
            if a != "test_regresyon"]
