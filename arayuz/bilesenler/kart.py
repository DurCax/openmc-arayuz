# -*- coding: utf-8 -*-
"""
kart.py -- Kart (baslik + istege bagli aciklama + sag eylem + govde) ve
BolumBasligi (kucuk, soluk bolum etiketi + istege bagli eylem).

    k = Kart(_("Parçacık ve çevrim"), aciklama=_("..."), eylem=duz_dugme(_("Sıfırla")))
    k.ekle(widget)             # govdeye (QVBoxLayout) ekler
    k.govde.addLayout(form)    # dogrudan yerlesim de olur
    k.secili_ayarla(True)      # vurgu kenari

    BolumBasligi(_("Örnekler"), aciklama=None, eylem=None)
"""

from PySide6 import QtWidgets

from arayuz.tasarim import tokenlar
from arayuz.tasarim.stil import durum_ayarla

A = tokenlar.ARALIK


class Kart(QtWidgets.QFrame):

    def __init__(self, baslik=None, aciklama=None, eylem=None, parent=None, dolgu="l"):
        super().__init__(parent)
        self.setObjectName("yuzeyKart")
        dis = QtWidgets.QVBoxLayout(self)
        dis.setContentsMargins(A[dolgu], A[dolgu] - A["xs"], A[dolgu], A[dolgu])
        dis.setSpacing(A["m"])
        self.baslik_etiketi = QtWidgets.QLabel(baslik or "")
        self.baslik_etiketi.setObjectName("kartBaslik")
        self.aciklama_etiketi = QtWidgets.QLabel(aciklama or "")
        self.aciklama_etiketi.setObjectName("kartAlt")
        self.aciklama_etiketi.setWordWrap(True)
        self._ust = QtWidgets.QHBoxLayout()
        self._ust.setSpacing(A["s"])
        metinler = QtWidgets.QVBoxLayout()
        metinler.setSpacing(2)
        metinler.addWidget(self.baslik_etiketi)
        metinler.addWidget(self.aciklama_etiketi)
        self._ust.addLayout(metinler, 1)
        if eylem is not None:
            self._ust.addWidget(eylem)
        self.baslik_etiketi.setVisible(bool(baslik))
        self.aciklama_etiketi.setVisible(bool(aciklama))
        # Baslik satiri HER ZAMAN yerlesime girer (bossa yer kaplamaz): sahipsiz
        # kalan bir QLayout Python'a ait olur ve widget silinirken uygulama
        # geneli olay suzgeci varken (ortak.tekerlek_korumasi_kur) cokerdi.
        dis.addLayout(self._ust)
        if baslik:
            self.setAccessibleName(baslik)
        self.govde = QtWidgets.QVBoxLayout()
        self.govde.setSpacing(A["s"])
        dis.addLayout(self.govde, 1)
        # Govdede buyuyen oge yoksa bos alan altta kalsin (baslik ortada yuzmesin).
        dis.addStretch(0)

    def ekle(self, widget, esnek=0):
        self.govde.addWidget(widget, esnek)
        return widget

    def eylem_ekle(self, widget):
        self._ust.addWidget(widget)
        return widget

    def baslik_ayarla(self, metin):
        self.baslik_etiketi.setText(metin)
        self.baslik_etiketi.setVisible(bool(metin))
        self.setAccessibleName(metin)

    def secili_ayarla(self, secili):
        durum_ayarla(self, "secili", bool(secili))


class BolumBasligi(QtWidgets.QWidget):

    def __init__(self, metin, aciklama=None, eylem=None, parent=None):
        super().__init__(parent)
        d = QtWidgets.QHBoxLayout(self)
        d.setContentsMargins(0, A["s"], 0, A["xs"])
        d.setSpacing(A["s"])
        sol = QtWidgets.QVBoxLayout()
        sol.setSpacing(2)
        self.etiket = QtWidgets.QLabel(metin)
        self.etiket.setObjectName("bolumEtiketi")
        sol.addWidget(self.etiket)
        if aciklama:
            a = QtWidgets.QLabel(aciklama)
            a.setObjectName("bolumAciklama")
            a.setWordWrap(True)
            sol.addWidget(a)
        d.addLayout(sol, 1)
        if eylem is not None:
            d.addWidget(eylem)
        self.setAccessibleName(metin)
