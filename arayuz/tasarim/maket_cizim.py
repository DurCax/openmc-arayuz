# -*- coding: utf-8 -*-
"""
maket_cizim.py -- baslangic galerisinin ornek kucuk resimleri (KucukResim).

Yer tutucu motif cizimi: renkler tokenlardan (Okabe-Ito), yuzey temadan.
"""

import math

from PySide6 import QtCore, QtGui, QtWidgets

from arayuz.tasarim import tokenlar

O = tokenlar.OKABE_ITO


def _r(ad):
    from arayuz import tema
    return QtGui.QColor(tema.renk(ad))


class KucukResim(QtWidgets.QWidget):
    """Ornek galerisi kucuk resmi: motif = pin|kare|kare3b|altigen|plaka|kor|kure|zirh."""

    def __init__(self, motif, parent=None):
        super().__init__(parent)
        self.motif = motif
        self.setFixedHeight(96)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

    def paintEvent(self, _olay):                             # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = QtCore.QRectF(self.rect())
        yol = QtGui.QPainterPath()
        yol.addRoundedRect(r, tokenlar.YARICAP["buyuk"], tokenlar.YARICAP["buyuk"])
        p.fillPath(yol, _r("yuzey2"))
        p.translate(r.center())
        s = min(r.width(), r.height()) * 0.36
        getattr(self, "_" + self.motif, self._pin)(p, s)
        p.end()

    @staticmethod
    def _daire(p, x, y, r, renk):
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(renk))
        p.drawEllipse(QtCore.QPointF(x, y), r, r)

    def _pin(self, p, s):
        self._daire(p, 0, 0, s, O["gok"])
        self._daire(p, 0, 0, s * 0.62, _r("yuzey2").name())
        self._daire(p, 0, 0, s * 0.55, O["kiremit"])

    def _kare(self, p, s, n=7):
        a = 2 * s / n
        for i in range(n):
            for j in range(n):
                renk = O["gok"] if (i, j) in {(1, 3), (3, 1), (3, 5), (5, 3), (3, 3)} else O["kiremit"]
                self._daire(p, -s + (j + 0.5) * a, -s + (i + 0.5) * a, a * 0.38, renk)

    def _kare3b(self, p, s):
        p.save()
        p.scale(1.0, 0.55)
        p.rotate(45)
        self._kare(p, s * 0.9)
        p.restore()

    def _altigen(self, p, s, halka=3):
        a = s / (halka + 0.3)
        for q in range(-halka, halka + 1):
            for r_ in range(max(-halka, -q - halka), min(halka, -q + halka) + 1):
                x = a * (q + r_ / 2.0)
                y = a * r_ * math.sqrt(3) / 2
                renk = O["gok"] if (q, r_) == (0, 0) else O["kiremit"]
                self._daire(p, x, y, a * 0.4, renk)

    def _plaka(self, p, s):
        p.setPen(QtCore.Qt.NoPen)
        for k in range(7):
            p.setBrush(QtGui.QColor(O["kiremit"] if k % 2 == 0 else O["gok"]))
            p.drawRoundedRect(QtCore.QRectF(-s * 1.3, -s + k * s * 0.3, s * 2.6, s * 0.16), 2, 2)

    def _kor(self, p, s):
        a = 2 * s / 7
        for i in range(7):
            for j in range(7):
                if math.hypot(i - 3, j - 3) <= 3.3:
                    renk = O["turuncu"] if (i + j) % 3 else O["kiremit"]
                    c = QtGui.QColor(renk)
                    p.fillRect(QtCore.QRectF(-s + j * a + 1, -s + i * a + 1, a - 2, a - 2), c)

    def _kure(self, p, s):
        g = QtGui.QRadialGradient(QtCore.QPointF(-s * 0.3, -s * 0.3), s * 1.2)
        g.setColorAt(0, QtGui.QColor(O["turuncu"]))
        g.setColorAt(1, QtGui.QColor(O["kiremit"]))
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(g)
        p.drawEllipse(QtCore.QPointF(0, 0), s, s)

    def _zirh(self, p, s):
        p.setPen(QtCore.Qt.NoPen)
        for k, renk in enumerate((O["mavi"], O["gok"], O["yesil"], O["gok"])):
            c = QtGui.QColor(renk)
            c.setAlpha(200 - k * 35)
            p.fillRect(QtCore.QRectF(-s * 0.6 + k * s * 0.45, -s, s * 0.4, 2 * s), c)
        self._daire(p, -s * 1.2, 0, s * 0.18, O["kiremit"])
