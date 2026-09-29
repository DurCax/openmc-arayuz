# -*- coding: utf-8 -*-
"""
dugme.py -- dugme yardimcilari (gorunum stil.py'deki QSS'ten gelir).

    birincil_dugme(metin, ikon=None, ipucu=None)   -> QPushButton (#birincil)
    ikincil_dugme(metin, ikon=None, ipucu=None)    -> QPushButton (varsayilan)
    tehlikeli_dugme(metin, ikon=None, ipucu=None)  -> QPushButton [tur=tehlikeli]
    duz_dugme(metin, ikon=None, ipucu=None)        -> QPushButton [tur=duz]
    baglanti_dugmesi(metin)                        -> QPushButton [tur=baglanti]
    ikon_dugmesi(ikon, ipucu, secilebilir=False, boyut=None) -> QToolButton [tur=ikon]

ikon: Lucide adi; renk temaya gore otomatik (tema degisince yenilenir).
"""

from PySide6 import QtCore, QtWidgets

from arayuz.tasarim import tokenlar
from arayuz.tasarim.ikon import ikon_bagla


# QPushButton QSS altinda ikon ile metin arasina bosluk koymaz; iki ince
# bosluk (U+2009) gorsel araligi verir. Erisilebilir ad bosluksuz metindir.
_IKON_ARALIGI = "\u2009\u2009"


def _kur(metin, ikon, ipucu, ikon_rengi, tur=None, ad=None):
    d = QtWidgets.QPushButton((_IKON_ARALIGI + metin) if ikon and metin else metin)
    if ad:
        d.setObjectName(ad)
    if tur:
        d.setProperty("tur", tur)
    if ikon:
        ikon_bagla(d, ikon, ikon_rengi, tokenlar.BOYUT["ikon"])
    if ipucu:
        d.setToolTip(ipucu)
    d.setAccessibleName(metin.replace("&", "") or (ipucu or ""))
    d.setCursor(QtCore.Qt.PointingHandCursor)
    return d


def birincil_dugme(metin, ikon=None, ipucu=None):
    return _kur(metin, ikon, ipucu, "vurgu_metin", ad="birincil")


def ikincil_dugme(metin, ikon=None, ipucu=None):
    return _kur(metin, ikon, ipucu, "metin")


def tehlikeli_dugme(metin, ikon=None, ipucu=None):
    return _kur(metin, ikon, ipucu, "hata", tur="tehlikeli")


def duz_dugme(metin, ikon=None, ipucu=None):
    return _kur(metin, ikon, ipucu, "metin_ikincil", tur="duz")


def baglanti_dugmesi(metin, ipucu=None):
    return _kur(metin, None, ipucu, None, tur="baglanti")


def ikon_dugmesi(ikon, ipucu, secilebilir=False, boyut=None, renk="metin_ikincil"):
    """Yalniz ikonlu arac dugmesi. ipucu ZORUNLU: ekran okuyucu adi da odur."""
    d = QtWidgets.QToolButton()
    d.setProperty("tur", "ikon")
    d.setAutoRaise(True)
    d.setCheckable(secilebilir)
    d.setToolTip(ipucu)
    d.setAccessibleName(ipucu)
    d.setFocusPolicy(QtCore.Qt.StrongFocus)
    d.setCursor(QtCore.Qt.PointingHandCursor)
    ikon_bagla(d, ikon, renk, boyut or tokenlar.BOYUT["ikon"])
    return d
