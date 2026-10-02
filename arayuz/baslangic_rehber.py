# -*- coding: utf-8 -*-
"""
baslangic_rehber.py -- editorde "Sifirdan" modelin adim rehberi seridi (v3 K1)

  [1 ✓ Malzeme ekle] › [2 ● Parça ekle] › [3 ○ Geometriyi kur]   Sıradaki: …

Adimlar baslangic_adim.adimlar(spec)'ten gelir. Her adim bir duz dugmedir;
tiklaninca adim_secildi(sekme) yayar (ana pencere o sayfaya gider). Tamamlanan
adim basari ikonuyla, siradaki vurguyla isaretlenir. Bütün adimlar tamamsa ya
da rehbersiz bir turdeyse serit gizlenir (guncelle False doner).
Renk/aralik yalniz tokenlardan; serit bir Kart'tir (QSS stil.py'den).
"""

from PySide6 import QtCore, QtWidgets

from arayuz import bilesenler as b
from arayuz.baslangic_adim import adimlar, ilerleme
from arayuz.tasarim import tokenlar
from arayuz.tasarim.ikon import ikon_bagla
from cekirdek.ceviri import _

A = tokenlar.ARALIK
_IKON = {"tamam": ("circle-check", "basari"), "siradaki": ("circle-dot", "vurgu"),
         "bekliyor": ("circle-dot", "metin_soluk")}


class AdimRehberi(b.Kart):
    """Adim rehberi seridi. dugmeler: {adim anahtari: QPushButton}."""

    adim_secildi = QtCore.Signal(str)        # sayfa anahtari (uygunluk.SEKMELER)

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent=parent, dolgu="s")
        self.setObjectName("yuzeyKart")
        self.setAccessibleName(_("Aşama rehberi"))
        self.dugmeler = {}
        self._anahtarlar = ()
        self._satir = QtWidgets.QHBoxLayout()
        self._satir.setSpacing(A["xs"])
        self.govde.addLayout(self._satir)
        self.baslik = QtWidgets.QLabel()
        self.baslik.setObjectName("govdeVurgulu")
        self.siradaki = QtWidgets.QLabel()
        self.siradaki.setObjectName("kucuk")
        self.siradaki.setWordWrap(True)
        self.setVisible(False)

    # ------------------------------------------------------------------ kurulum
    def _bosalt(self) -> None:
        while self._satir.count():
            oge = self._satir.takeAt(0)
            w = oge.widget()
            if w is not None and w not in (self.baslik, self.siradaki):
                w.deleteLater()
        self.dugmeler = {}

    def _kur(self, liste: tuple) -> None:
        """Adim dugmelerini (tur degisince) yeniden kurar."""
        self._bosalt()
        self._satir.addWidget(self.baslik)
        for i, adim in enumerate(liste):
            if i:
                ok = QtWidgets.QLabel("›")
                ok.setObjectName("ikincil")
                self._satir.addWidget(ok)
            d = b.duz_dugme("%d. %s" % (i + 1, adim.baslik), "circle-dot")
            d.clicked.connect(lambda _c=False, s=adim.sekme: self.adim_secildi.emit(s))
            self.dugmeler[adim.anahtar] = d
            self._satir.addWidget(d)
        self._satir.addSpacing(A["m"])
        self._satir.addWidget(self.siradaki, 1)
        self._anahtarlar = tuple(a.anahtar for a in liste)

    # ------------------------------------------------------------------ herkese acik
    def guncelle(self, spec: dict, editorde: bool = True) -> bool:
        """Rehberi spec'e uydurur; gorunur kaldiysa True."""
        liste = adimlar(spec or {})
        eksik = [a for a in liste if not a.tamam]
        if not (editorde and eksik):
            self.setVisible(False)
            return False
        if tuple(a.anahtar for a in liste) != self._anahtarlar:
            self._kur(liste)
        tamam, toplam = ilerleme(spec)
        self.baslik.setText(_("Modeli kurun ({tamam}/{toplam}):").format(
            tamam=tamam, toplam=toplam))
        for adim in liste:
            durum = ("tamam" if adim.tamam else
                     "siradaki" if adim is eksik[0] else "bekliyor")
            d = self.dugmeler[adim.anahtar]
            ikon_bagla(d, *_IKON[durum], tokenlar.BOYUT["ikon"])
            d.setProperty("adim_durumu", durum)
            d.setToolTip(("%s — %s" % (_("Tamamlandı"), adim.aciklama)) if adim.tamam
                         else adim.aciklama)
            d.setAccessibleDescription(d.toolTip())
        self.siradaki.setText(_("Sıradaki: {aciklama}").format(aciklama=eksik[0].aciklama))
        self.setVisible(True)
        return True
