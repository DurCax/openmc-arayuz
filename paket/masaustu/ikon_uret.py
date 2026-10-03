# -*- coding: utf-8 -*-
"""Uygulama simgesi PNG'lerini SVG'den uretir (hicolor boyutlari). Gelistirici araci:
   QT_QPA_PLATFORM=offscreen python paket/masaustu/ikon_uret.py"""
import os
import sys

from PySide6 import QtGui, QtSvg, QtWidgets

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KAYNAK = os.path.join(KOK, "cekirdek", "masaustu", "kaynaklar")
BOYUTLAR = (16, 32, 48, 128, 256)     # hicolor tema boyutlari (gorev karti)


def uret() -> int:
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    isleyici = QtSvg.QSvgRenderer(os.path.join(KAYNAK, "openmc-arayuz.svg"))
    if not isleyici.isValid():
        print("SVG gecersiz", file=sys.stderr)
        return 1
    for boyut in BOYUTLAR:
        resim = QtGui.QImage(boyut, boyut, QtGui.QImage.Format_ARGB32)
        resim.fill(0)
        boyayici = QtGui.QPainter(resim)
        isleyici.render(boyayici)
        boyayici.end()
        if not resim.save(os.path.join(KAYNAK, "openmc-arayuz-%d.png" % boyut)):
            print("yazilamadi: %d" % boyut, file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(uret())
