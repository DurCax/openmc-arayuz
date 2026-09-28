# -*- coding: utf-8 -*-
"""
segment.py -- SegmentSecici: bitisik dugmelerden tekli secim (ornek:
hassasiyet onayari Hizli / Dengeli / Hassas / Ozel).

    s = SegmentSecici([("hizli", _("Hızlı")), ("dengeli", _("Dengeli"))], "dengeli")
    s.secildi.connect(lambda anahtar: ...)
    s.secili() -> "dengeli";  s.sec("hizli");  s.dugme("hizli") -> QPushButton
"""

from PySide6 import QtCore, QtWidgets

from arayuz.tasarim.ikon import ikon_bagla


class SegmentSecici(QtWidgets.QWidget):
    secildi = QtCore.Signal(str)

    def __init__(self, secenekler, secili=None, parent=None, ikonlar=None):
        super().__init__(parent)
        self._dugmeler = {}
        self._grup = QtWidgets.QButtonGroup(self)
        self._grup.setExclusive(True)
        d = QtWidgets.QHBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(0)
        n = len(secenekler)
        for i, (anahtar, metin) in enumerate(secenekler):
            b = QtWidgets.QPushButton(metin)
            b.setCheckable(True)
            b.setProperty("segment", "tek" if n == 1 else "bas" if i == 0
                          else "son" if i == n - 1 else "orta")
            b.setAccessibleName(metin)
            if ikonlar and ikonlar.get(anahtar):
                ikon_bagla(b, ikonlar[anahtar], "metin_ikincil")
            b.clicked.connect(lambda _=False, a=anahtar: self._tiklandi(a))
            self._grup.addButton(b)
            self._dugmeler[anahtar] = b
            d.addWidget(b)
        self.setAccessibleName("segment")
        if secili is not None:
            self.sec(secili, sinyal=False)

    def dugme(self, anahtar):
        return self._dugmeler[anahtar]

    def secili(self):
        for anahtar, b in self._dugmeler.items():
            if b.isChecked():
                return anahtar
        return None

    def sec(self, anahtar, sinyal=True):
        if anahtar not in self._dugmeler or self.secili() == anahtar:
            return
        self._dugmeler[anahtar].setChecked(True)
        if sinyal:
            self.secildi.emit(anahtar)

    def _tiklandi(self, anahtar):
        self.secildi.emit(anahtar)
