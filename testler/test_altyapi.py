# -*- coding: utf-8 -*-
"""
test_altyapi.py -- surum, gunluk (log) ve GUI hata yakalayicisi.

- cekirdek/surum.py: surum tek yerden (paket meta verisi / pyproject.toml),
  uygulama adi tek sabitte.
- cekirdek/gunluk.py: donen log dosyasi $XDG_STATE_HOME altinda; testlerde
  ortak_test bu dizini gecici dizine yonlendirir (gercek kullanici dizinine
  yazilmaz).
- arayuz/hata_yakalayici.py: yakalanmamis istisna loglanir ve kullaniciya
  "Logu ac" dugmeli bir diyalog gosterilir; basssiz testte diyalog ENGELLEMEZ.
"""

import logging
import os
import sys
import threading

from testler.ortak_test import kontrol, KOK, DURUM_DIZINI
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik


@gereksinim("R-M7-01")
def test_surum():
    print("\n[A1] SURUM: tek kaynak ve uygulama adi sabiti")
    import re
    from cekirdek import surum
    try:
        import tomllib
    except ImportError:          # Python 3.10
        tomllib = None
    kontrol("UYGULAMA_ADI bos olmayan metin",
            isinstance(surum.UYGULAMA_ADI, str) and bool(surum.UYGULAMA_ADI.strip()))
    kontrol("surum PEP 440 bicimli", bool(re.match(r"^\d+\.\d+\.\d+", surum.surum())),
            "-> %s" % surum.surum())
    kontrol("__version__ == surum()", surum.__version__ == surum.surum())
    if tomllib is not None:
        with open(os.path.join(KOK, "pyproject.toml"), "rb") as f:
            proje = tomllib.load(f)["project"]
        kontrol("surum pyproject.toml ile ayni", surum.surum() == proje["version"],
                "-> %s / %s" % (surum.surum(), proje["version"]))
        kontrol("pyproject paket adi PAKET_ADI", proje["name"] == surum.PAKET_ADI)
    kontrol("pyproject okunamazsa sabit geri donus",
            surum._pyproject_surumu(os.path.join(KOK, "yok.toml")) is None)


@gereksinim("R-M5-02")
def test_gunluk_yolu_ve_yazim():
    print("\n[A2] GUNLUK: log dosyasi XDG_STATE_HOME altinda ve donuyor")
    from cekirdek import gunluk
    yol = gunluk.log_yolu()
    kontrol("testte log yolu gecici dizinde (gercek kullanici dizini degil)",
            yol.startswith(DURUM_DIZINI), "-> %s" % yol)
    kontrol("log yolu .../openmc_arayuz/openmc_arayuz.log",
            yol.endswith(os.path.join("openmc_arayuz", "openmc_arayuz.log")))
    kontrol("XDG_STATE_HOME yoksa ~/.local/state",
            gunluk.durum_dizini(ortam={}) == os.path.join(
                os.path.expanduser("~"), ".local", "state", "openmc_arayuz"))
    k = gunluk.kaydedici("test.altyapi")
    kontrol("kaydedici uygulama ad alaninda",
            k.name == gunluk.KOK_KAYDEDICI + ".test.altyapi", "-> %s" % k.name)
    k.warning("altyapi testi isaret 91c2")
    gunluk.bosalt()
    with open(yol, encoding="utf-8") as f:
        icerik = f.read()
    kontrol("mesaj dosyaya yazildi", "altyapi testi isaret 91c2" in icerik)
    isleyici = gunluk.dosya_isleyicisi()
    kontrol("donen dosya ~1 MB x 5",
            isleyici is not None and isleyici.maxBytes == 1_000_000
            and isleyici.backupCount == 5)


def test_gunluk_yazilamazsa():
    print("\n[A3] GUNLUK: dizin yazilamazsa uygulama cokmez, stderr'e duser")
    import tempfile
    from cekirdek import gunluk
    with tempfile.TemporaryDirectory() as d:
        engel = os.path.join(d, "dosya")
        with open(engel, "w") as f:
            f.write("dizin degil")
        isleyici = gunluk._dosya_isleyicisi_kur(os.path.join(engel, "alt", "x.log"))
    kontrol("yazilamayan yol -> None (istisna yok)", isleyici is None)


def test_hata_diyalogu_log_yazilamazsa():
    print("\n[A3b] HATA DIYALOGU: log yazilamiyorsa 'yazildi' denmez, Logu ac pasif")
    _uygulama()
    from arayuz import hata_yakalayici as hy
    from cekirdek import gunluk
    eski = dict(gunluk._durum)
    try:
        gunluk._durum["isleyici"] = None
        kutu = hy.mesaj_kutusu("ValueError: x", "iz")
        metin = kutu.informativeText()
        kontrol("yazilamayan logda 'yazıldı' denmiyor", "yazıldı" not in metin, metin)
        kontrol("yazilamayan logda Logu ac pasif",
                not kutu.property("log_dugmesi").isEnabled())
    finally:
        gunluk._durum.update(eski)
    kutu = hy.mesaj_kutusu("ValueError: x", "iz")
    kontrol("yazilan logda Logu ac etkin", kutu.property("log_dugmesi").isEnabled()
            or not gunluk.dosyaya_yaziliyor())


def _uygulama():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@gereksinim("R-M5-02")
def test_hata_yakalayici_loglar():
    print("\n[A4] HATA YAKALAYICI: excepthook loglar, diyalog engellemez")
    _uygulama()
    from arayuz import hata_yakalayici as hy
    from cekirdek import gunluk
    eski_sys, eski_thr = sys.excepthook, threading.excepthook
    gosterilen = []
    yakalayici = hy.kur(goster=lambda ozet, ayrinti: gosterilen.append((ozet, ayrinti)))
    try:
        kontrol("sys.excepthook kuruldu", sys.excepthook is not eski_sys)
        kontrol("threading.excepthook kuruldu", threading.excepthook is not eski_thr)
        try:
            raise ValueError("yakalanmamis hata 5d1e")
        except ValueError:
            sys.excepthook(*sys.exc_info())
        t = threading.Thread(target=lambda: 1 / 0)
        t.start()
        t.join()
        yakalayici.bekleyenleri_isle()
        gunluk.bosalt()
        with open(gunluk.log_yolu(), encoding="utf-8") as f:
            icerik = f.read()
        kontrol("ana is parcacigi hatasi loglandi (iz dahil)",
                "yakalanmamis hata 5d1e" in icerik and "Traceback" in icerik)
        kontrol("is parcacigi hatasi loglandi", "ZeroDivisionError" in icerik)
        kontrol("iki hata da kullaniciya iletildi", len(gosterilen) == 2,
                "-> %d" % len(gosterilen))
        kontrol("ayrinti metni izi tasiyor",
                bool(gosterilen) and "ValueError" in gosterilen[0][1])
    finally:
        yakalayici.kaldir()
    kontrol("kaldir() eski kancalari geri koyar",
            sys.excepthook is eski_sys and threading.excepthook is eski_thr)


@gereksinim("R-M5-02")
def test_hata_diyalogu():
    print("\n[A5] HATA YAKALAYICI: diyalog metni, 'Logu ac' dugmesi, basssiz engel yok")
    _uygulama()
    from PySide6 import QtGui
    from arayuz import hata_yakalayici as hy
    from cekirdek import gunluk
    kontrol("offscreen'de diyalog engellenmez", hy.diyalog_engelli())
    kutu = hy.mesaj_kutusu("özet", "ayrıntı izi", sayi=2)
    kontrol("ayrinti metni izi gosterir", kutu.detailedText() == "ayrıntı izi")
    dugme = kutu.property("log_dugmesi")
    kontrol("'Logu aç' dugmesi var", dugme is not None and dugme.text() == "Logu aç",
            "-> %r" % (dugme.text() if dugme else None))
    acilan = []
    eski = QtGui.QDesktopServices.openUrl
    QtGui.QDesktopServices.openUrl = staticmethod(lambda url: acilan.append(url) or True)
    try:
        hy.log_klasorunu_ac()
    finally:
        QtGui.QDesktopServices.openUrl = eski
    kontrol("'Logu aç' log klasorunu acar",
            len(acilan) == 1 and acilan[0].toLocalFile().rstrip("/")
            == os.path.dirname(gunluk.log_yolu()),
            "-> %s" % [u.toString() for u in acilan])
    kontrol("coklu hata sayisi metinde", "2" in kutu.informativeText())
    kutu.deleteLater()


def test_veri_listesi_gecerli():
    print("\n[A6] PYTEST KOPRUSU: VERI_GEREKTIREN listesi var olan testleri gosteriyor")
    import importlib
    try:
        import conftest
    except ImportError as e:            # pytest kurulu degil
        kontrol("pytest yok; kopru denetimi atlandi", True, "-> %s" % e)
        return
    hizli_adlar = set()
    for m in importlib.import_module("testler.ortak_test").ek_moduller() + [
            importlib.import_module("testler.test_regresyon")]:
        ad = m.__name__.rsplit(".", 1)[-1]
        hizli, _ = conftest.test_listeleri(m)
        hizli_adlar.update("%s:%s" % (ad, fn.__name__) for fn in hizli)
    bilinmeyen = sorted(conftest.VERI_GEREKTIREN - hizli_adlar)
    kontrol("VERI_GEREKTIREN'deki her ad bir HIZLI teste karsilik geliyor", not bilinmeyen,
            "-> tasinmis/silinmis: %s (conftest.py'de guncelleyin)" % bilinmeyen)


HIZLI = [test_surum, test_gunluk_yolu_ve_yazim, test_gunluk_yazilamazsa,
         test_hata_diyalogu_log_yazilamazsa,
         test_hata_yakalayici_loglar, test_hata_diyalogu, test_veri_listesi_gecerli]
YAVAS = []
