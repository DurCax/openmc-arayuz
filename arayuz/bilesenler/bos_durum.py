# -*- coding: utf-8 -*-
"""
bos_durum.py -- BosDurum: icerik yokken ortalanmis ikon + baslik + aciklama +
istege bagli eylem dugmesi.

    b = BosDurum("chart-line", _("Henüz sonuç yok"), _("Modeli çalıştırın."), _("Çalıştır"))
    b.eylem_istendi.connect(...)
(arayuz/ortak.py'deki eski BosDurum Dalga 2'de buna gecer.)
"""

from PySide6 import QtCore, QtWidgets

from arayuz.bilesenler.dugme import birincil_dugme
from arayuz.tasarim import tokenlar
from arayuz.tasarim.ikon import ikon_bagla

A = tokenlar.ARALIK
_IKON_BOYUTU = 40


class BosDurum(QtWidgets.QWidget):
    eylem_istendi = QtCore.Signal()

    def __init__(self, ikon, baslik, aciklama=None, eylem_metni=None, eylem_ikonu=None,
                 parent=None):
        super().__init__(parent)
        d = QtWidgets.QVBoxLayout(self)
        d.setContentsMargins(A["xl"], A["xl"], A["xl"], A["xl"])
        d.setSpacing(A["s"])
        d.addStretch(1)
        self.ikon = QtWidgets.QToolButton()
        self.ikon.setEnabled(True)
        self.ikon.setFocusPolicy(QtCore.Qt.NoFocus)
        self.ikon.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.ikon.setStyleSheet("border: none; background: transparent;")
        ikon_bagla(self.ikon, ikon, "metin_soluk", _IKON_BOYUTU)
        d.addWidget(self.ikon, 0, QtCore.Qt.AlignHCenter)
        self.baslik = QtWidgets.QLabel(baslik)
        self.baslik.setObjectName("bosBaslik")
        self.baslik.setAlignment(QtCore.Qt.AlignCenter)
        d.addWidget(self.baslik)
        self.aciklama = QtWidgets.QLabel(aciklama or "")
        self.aciklama.setObjectName("bosAciklama")
        self.aciklama.setAlignment(QtCore.Qt.AlignCenter)
        self.aciklama.setWordWrap(True)
        self.aciklama.setVisible(bool(aciklama))
        d.addWidget(self.aciklama)
        self.dugme = None
        if eylem_metni:
            self.dugme = birincil_dugme(eylem_metni, eylem_ikonu)
            self.dugme.clicked.connect(self.eylem_istendi)
            d.addSpacing(A["s"])
            d.addWidget(self.dugme, 0, QtCore.Qt.AlignHCenter)
        d.addStretch(1)
        self.setAccessibleName(baslik)
