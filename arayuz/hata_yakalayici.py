# -*- coding: utf-8 -*-
"""
hata_yakalayici.py -- yakalanmamis istisnalar icin genel kanca (GUI).

    from arayuz import hata_yakalayici
    hata_yakalayici.kur(app)      # QApplication kurulduktan hemen sonra

sys.excepthook ve threading.excepthook'u degistirir:
  1. hata izle birlikte log dosyasina yazilir (cekirdek.gunluk, CRITICAL),
  2. kullaniciya "Logu aç" dugmeli bir QMessageBox gosterilir. Is parcacigindan
     gelen hata Qt sinyaliyle ana is parcacigina tasinir (widget yalnizca ana
     is parcaciginda kurulur).
Basssiz (QT_QPA_PLATFORM=offscreen) ya da OPENMC_ARAYUZ_DIYALOGSUZ=1 iken
diyalog GOSTERILMEZ (testler engellenmesin); hata yine loglanir ve stderr'e
yazilir. KeyboardInterrupt eski kancaya birakilir.
"""

import os
import sys
import threading
import traceback

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import gunluk
from cekirdek.ceviri import _, _n

DIYALOGSUZ_DEGISKENI = "OPENMC_ARAYUZ_DIYALOGSUZ"
_log = gunluk.kaydedici("arayuz.hata")


def diyalog_engelli(ortam=None):
    """Diyalog gosterilemeyecek/gosterilmemesi gereken ortam mi?"""
    ortam = os.environ if ortam is None else ortam
    return (ortam.get(DIYALOGSUZ_DEGISKENI, "") not in ("", "0")
            or ortam.get("QT_QPA_PLATFORM", "") in ("offscreen", "minimal"))


def log_klasorunu_ac():
    """Log klasorunu sistemin dosya yoneticisinde acar."""
    klasor = os.path.dirname(gunluk.log_yolu())
    os.makedirs(klasor, exist_ok=True)
    if not QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(klasor)):
        _log.warning("log klasoru acilamadi: %s", klasor)


def mesaj_kutusu(ozet, ayrinti, sayi=1, ust=None):
    """Hata diyalogu (gosterilmeden kurulur; exec() cagirana kalir)."""
    kutu = QtWidgets.QMessageBox(ust)
    kutu.setIcon(QtWidgets.QMessageBox.Critical)
    kutu.setWindowTitle(_("Beklenmeyen hata"))
    kutu.setText(_("Beklenmeyen bir hata oluştu: {ozet}").format(ozet=ozet))
    if gunluk.dosyaya_yaziliyor():
        bilgi = _("Ayrıntılar log dosyasına yazıldı:\n{yol}").format(yol=gunluk.log_yolu())
    else:
        # Dizin yazilamiyorsa "log'a yazildi" demek teshis verisini kaybettirir.
        bilgi = _("Log dosyasına yazılamadı ({yol}); ayrıntıları aşağıdan "
                  "kopyalayın.").format(yol=gunluk.log_yolu())
    if sayi > 1:
        bilgi += "\n" + _n("Bu oturumda {n} hata kaydedildi.",
                           "Bu oturumda {n} hata kaydedildi.", sayi).format(n=sayi)
    kutu.setInformativeText(bilgi)
    kutu.setDetailedText(ayrinti)
    log_dugmesi = kutu.addButton(_("Logu aç"), QtWidgets.QMessageBox.ActionRole)
    log_dugmesi.clicked.disconnect()          # ActionRole dugmesi kutuyu kapatmasin
    log_dugmesi.clicked.connect(log_klasorunu_ac)
    log_dugmesi.setEnabled(gunluk.dosyaya_yaziliyor())
    kutu.addButton(QtWidgets.QMessageBox.Close)
    kutu.setProperty("log_dugmesi", log_dugmesi)
    return kutu


def _diyalog_goster(ozet, ayrinti, sayi):
    if diyalog_engelli():
        sys.stderr.write(ayrinti)
        return
    ust = QtWidgets.QApplication.activeWindow()
    mesaj_kutusu(ozet, ayrinti, sayi, ust).exec()


class HataYakalayici(QtCore.QObject):
    """Kurulu kancalari tutar; kaldir() ile eskilerini geri koyar."""

    _hata_geldi = QtCore.Signal(str, str)

    def __init__(self, goster=None, ust=None):
        super().__init__(ust)
        self._goster = goster
        self._sayi = 0
        self._eski_sys = sys.excepthook
        self._eski_thr = threading.excepthook
        self._hata_geldi.connect(self._kullaniciya_goster)
        sys.excepthook = self._sys_kancasi
        threading.excepthook = self._thr_kancasi

    def kaldir(self):
        sys.excepthook = self._eski_sys
        threading.excepthook = self._eski_thr

    def bekleyenleri_isle(self):
        """Is parcacigindan kuyruga giren hatalari simdi isler (testler icin)."""
        QtCore.QCoreApplication.sendPostedEvents(self)
        QtCore.QCoreApplication.processEvents()

    def _isle(self, tur, deger, iz, kaynak):
        ayrinti = "".join(traceback.format_exception(tur, deger, iz))
        _log.critical("yakalanmamis hata (%s)", kaynak, exc_info=(tur, deger, iz))
        gunluk.bosalt()
        ozet = "%s: %s" % (tur.__name__, deger) if str(deger) else tur.__name__
        self._hata_geldi.emit(ozet, ayrinti)   # baska is parcacigindan: kuyruklu

    def _sys_kancasi(self, tur, deger, iz):
        if issubclass(tur, KeyboardInterrupt):
            self._eski_sys(tur, deger, iz)
            return
        self._isle(tur, deger, iz, "ana is parcacigi")

    def _thr_kancasi(self, arg):
        if arg.exc_type is SystemExit:
            return
        ad = arg.thread.name if arg.thread is not None else "?"
        self._isle(arg.exc_type, arg.exc_value, arg.exc_traceback,
                   "is parcacigi %s" % ad)

    def _kullaniciya_goster(self, ozet, ayrinti):
        self._sayi += 1
        if self._goster is not None:
            self._goster(ozet, ayrinti)
        else:
            _diyalog_goster(ozet, ayrinti, self._sayi)


def kur(uygulama=None, goster=None):
    """Kancalari kurar; HataYakalayici nesnesini doner (uygulamaya baglidir).
    goster(ozet, ayrinti) verilirse diyalog yerine o cagrilir (testler)."""
    uygulama = uygulama or QtWidgets.QApplication.instance()
    return HataYakalayici(goster=goster, ust=uygulama)
