# -*- coding: utf-8 -*-
"""
 test_h1b_stil.py  --  v3 H1b: uygulama QSS'i ana pencere kurulduktan SONRA

 QSS etkinken her addWidget/setWidget yeni alt agaci QStyleSheetStyle ile
 yeniden cilaliyordu (pencere kurulumu ~4.4 s CPU, H1 profili). AnaPencere
 artik kurulumu arayuz/tasarim/stil.sonradan_uygula() icinde yapar: QSS cikista
 bir kez uygulanir. Renk/token ayni; birkac bolucu 11 px kayabilir (orkestrator
 karari: kabul; once/sonra ekranlari v3 cikti dizininde h1b/ekran/).
"""

import contextlib
import time

from testler.ortak_test import kontrol

_ORNEK_QSS = "QPushButton { min-height: 41px; }"   # olcusu tokenlardan ayirt edilir
_HIZ_ORANI = 0.5               # >= 2x hizlanma payi (olculen 4.4 -> 1.2 s, x3.7)


def _uygulama():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _sil(*widgetlar):
    from PySide6 import QtCore
    for w in widgetlar:
        w._kirli = False
        w.close()
        w.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


@contextlib.contextmanager
def _qss(app, qss):
    eski = app.styleSheet()
    app.setStyleSheet(qss)
    try:
        yield
    finally:
        app.setStyleSheet(eski)


def test_sonradan_uygula_askiya_alir_ve_geri_koyar():
    print("\n[H1b-S1] stil.sonradan_uygula: icerde QSS bos, cikista aynisi geri")
    from arayuz.tasarim import stil
    app = _uygulama()
    with _qss(app, _ORNEK_QSS):
        with stil.sonradan_uygula():
            icerde = app.styleSheet()
        kontrol("icerde QSS bos", icerde == "", "-> %r" % icerde)
        kontrol("cikista ayni QSS", app.styleSheet() == _ORNEK_QSS)


def test_sonradan_uygula_istisnada_da_geri_koyar():
    print("\n[H1b-S2] stil.sonradan_uygula: kurulum hatasinda QSS yine geri")
    from arayuz.tasarim import stil
    app = _uygulama()
    with _qss(app, _ORNEK_QSS):
        try:
            with stil.sonradan_uygula():
                raise RuntimeError("deneme")
        except RuntimeError:
            pass
        kontrol("istisnadan sonra ayni QSS", app.styleSheet() == _ORNEK_QSS)


def test_qss_yoksa_dokunmaz():
    print("\n[H1b-S3] stil.sonradan_uygula: QSS yoksa hicbir sey yapmaz")
    from arayuz.tasarim import stil
    app = _uygulama()
    with _qss(app, ""):
        with stil.sonradan_uygula():
            pass
        kontrol("QSS bos kalir", app.styleSheet() == "")


def test_pencere_kurulumdan_sonra_stilli():
    print("\n[H1b-S4] AnaPencere: kurulum QSS'siz, sonra QSS etkin (dugme olcusu QSS'den)")
    from PySide6 import QtWidgets
    from arayuz.ana_pencere import AnaPencere
    from arayuz.pencere import ana_pencere as ap
    app = _uygulama()
    gozlem = []
    asil = ap.AnaPencere._sayfalari_kur

    def gozleyen(self):
        gozlem.append(app.styleSheet())
        return asil(self)
    with _qss(app, _ORNEK_QSS):
        ap.AnaPencere._sayfalari_kur = gozleyen
        try:
            p = AnaPencere()
        finally:
            ap.AnaPencere._sayfalari_kur = asil
        try:
            kontrol("sayfa kurulumunda QSS askida", gozlem == [""], "-> %r" % gozlem)
            kontrol("kurulumdan sonra uygulama QSS'i ayni", app.styleSheet() == _ORNEK_QSS)
            dugme = p.findChildren(QtWidgets.QPushButton)[0]
            kontrol("dugmeye QSS uygulanmis (min-height 41 px)",
                    dugme.minimumSizeHint().height() >= 41,
                    "-> %d" % dugme.minimumSizeHint().height())
        finally:
            _sil(p)


def test_yavas_qss_sonradan_pencere_kurulumu_hizli():
    print("\n[H1b-S5] AnaPencere kurulumu (gercek tema): QSS sonradan <= %.1f x QSS kurulumda"
          % _HIZ_ORANI)
    from arayuz import tema
    from arayuz.ana_pencere import AnaPencere
    from arayuz.pencere import ana_pencere as ap
    app = _uygulama()
    once = (tema.etkin(), tema.etkin_vurgu())

    def olc():
        sureler = []
        for _i in range(2):
            t = time.process_time()
            p = AnaPencere()
            sureler.append(time.process_time() - t)
            _sil(p)
        return min(sureler)
    eski_qss = app.styleSheet()
    tema.uygula(app, "acik")
    try:
        sonradan = olc()
        asil = ap._stil.sonradan_uygula
        ap._stil.sonradan_uygula = contextlib.nullcontext
        try:
            kurulumda = olc()
        finally:
            ap._stil.sonradan_uygula = asil
    finally:
        tema.uygula(app, *once)
        app.setStyleSheet(eski_qss)
    kontrol("QSS sonradan <= %.1f x kurulumda" % _HIZ_ORANI, sonradan <= _HIZ_ORANI * kurulumda,
            "%.3f / %.3f s" % (sonradan, kurulumda))


HIZLI = [test_sonradan_uygula_askiya_alir_ve_geri_koyar,
         test_sonradan_uygula_istisnada_da_geri_koyar, test_qss_yoksa_dokunmaz,
         test_pencere_kurulumdan_sonra_stilli]
YAVAS = [test_yavas_qss_sonradan_pencere_kurulumu_hizli]
