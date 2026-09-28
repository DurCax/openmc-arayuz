# -*- coding: utf-8 -*-
"""
rozet.py -- Rozet: kucuk durum etiketi (basari / uyari / hata / bilgi / notr / vurgu).

    r = Rozet(_("Hata yok"), "basari");  r.tur_ayarla("hata")
Renkler QSS'ten (QLabel[rozet="..."]) gelir; tema degisimi kendiliginden uyar.
"""

from PySide6 import QtCore, QtWidgets

from arayuz.tasarim.stil import durum_ayarla

TURLER = ("basari", "uyari", "hata", "bilgi", "notr", "vurgu")


class Rozet(QtWidgets.QLabel):

    def __init__(self, metin="", tur="notr", parent=None):
        super().__init__(metin, parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.tur_ayarla(tur)

    def tur(self):
        return self.property("rozet")

    def tur_ayarla(self, tur):
        if tur not in TURLER:
            raise ValueError("bilinmeyen rozet turu: %r" % (tur,))
        durum_ayarla(self, "rozet", tur)

    def setText(self, metin):          # noqa: N802 (Qt adi)
        super().setText(metin)
        self.setAccessibleName(metin)
