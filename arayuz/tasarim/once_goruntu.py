# -*- coding: utf-8 -*-
"""
once_goruntu.py -- MEVCUT uygulamanin ekran goruntuleri (KAPI G1 "once" ve
"yeni QSS ile eski ekranlar" denetimi).

Baska bir kod agacina karsi da calisir (ornegin `git archive ana` ciktisi):
bu yuzden arayuz.tasarim'i IMPORT ETMEZ; yalnizca her surumde bulunan
arayuz.tema, arayuz.ana_pencere ve arayuz.ortak kullanilir.

    python arayuz/tasarim/once_goruntu.py --kok KOD_AGACI --cikti DIZIN
        -> DIZIN/<ekran>_<tema>_<GxY>.png
           ekran: baslangic + gorunur her sekme (malzemeler, parcalar, demet,
           kor, ayarlar, calistir, analiz, tukenme)

Kullanicinin gercek QSettings'i DEGISMEZ (gecici dizine yonlendirilir).
"""

import argparse
import os
import sys
import tempfile

COZUNURLUKLER = ((1440, 900), (1280, 800))
ORNEK = os.path.join("ornekler", "pwr_17x17.json")


_YALITIM = {"dizin": None}


def ayarlari_yalit():
    """QSettings'i gecici bir dizine yonlendirir (tema secimi kullaniciya yazilmasin).

    Tekrar cagrilabilir: surecte ilk cagrinin dizini kullanilir. Maket ve galeri
    araclarinin kaydet()/varyantlar() islevleri de bunu cagirir; main()
    atlanip dogrudan cagrilsalar bile kullanicinin gercek ayarina yazmazlar."""
    from PySide6 import QtCore
    if _YALITIM["dizin"] is None:
        _YALITIM["dizin"] = tempfile.mkdtemp(prefix="openmc_arayuz_ayar_")
    for bicim in (QtCore.QSettings.NativeFormat, QtCore.QSettings.IniFormat):
        QtCore.QSettings.setPath(bicim, QtCore.QSettings.UserScope, _YALITIM["dizin"])
    return _YALITIM["dizin"]


def _bekle(app, tur=6):
    for _i in range(tur):
        app.processEvents()


def _kaydet(resim, yol):
    if not resim.save(yol):
        raise OSError("PNG yazilamadi: %s" % yol)
    return yol


def _pencere_cek(app, boyut, tema_adi, cikti):
    from arayuz import ana_pencere
    yollar = []
    son = "%s_%dx%d.png" % (tema_adi, boyut[0], boyut[1])
    p = ana_pencere.AnaPencere()
    p._kaydetme_sor = lambda: True          # kapanista modal soru acilmasin
    p.resize(*boyut)
    p.show()
    _bekle(app)
    yollar.append(_kaydet(p.grab(), os.path.join(cikti, "baslangic_" + son)))
    p.ornek_ac(ORNEK)
    _bekle(app)
    for anahtar, indeks in p._sekme_ix.items():
        if not p.sekmeler.isTabVisible(indeks):
            continue
        p.sekmeler.setCurrentIndex(indeks)
        _bekle(app)
        yollar.append(_kaydet(p.grab(), os.path.join(cikti, "%s_%s" % (anahtar, son))))
    p.close()
    p.deleteLater()
    app.processEvents()
    return yollar


def cek(cikti, temalar=("acik", "koyu"), cozunurlukler=COZUNURLUKLER):
    from PySide6 import QtCore, QtWidgets
    QtCore.QLocale.setDefault(QtCore.QLocale.c())
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    from arayuz import ortak, tema
    ortak.tekerlek_korumasi_kur(app)
    os.makedirs(cikti, exist_ok=True)
    yollar = []
    for tema_adi in temalar:
        tema.uygula(app, tema_adi)
        for boyut in cozunurlukler:
            yollar += _pencere_cek(app, boyut, tema_adi, cikti)
    return yollar


def main(argv=None):
    ayr = argparse.ArgumentParser(description="Mevcut uygulamanin ekran goruntuleri")
    ayr.add_argument("--kok", default=None, help="kod agaci (varsayilan: bu depo)")
    ayr.add_argument("--cikti", required=True)
    a = ayr.parse_args(argv)
    cikti = os.path.abspath(a.cikti)
    kok = os.path.abspath(a.kok or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 os.pardir, os.pardir))
    sys.path.insert(0, kok)
    os.chdir(kok)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    ayarlari_yalit()
    for yol in cek(cikti):
        print(yol)
    return 0


if __name__ == "__main__":
    sys.exit(main())
