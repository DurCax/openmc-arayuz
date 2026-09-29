# -*- coding: utf-8 -*-
"""
sekme_duzen.py -- tasarim sekmelerinin (Malzemeler, Parcalar, Demet) ortak
sayfa duzeni: sayfa basligi, dugme satiri, kart sutunu.

Renk, aralik ve yazi boyutu YALNIZCA tasarim tokenlarindan gelir
(arayuz/tasarim/tokenlar.py); burada sabit piksel ya da #rrggbb yoktur.
Sekmeler QTabWidget'a bagli degildir: kabuk (Ajan 6) her sayfayi bir
QScrollArea icine koyar, bu yuzden kok duzen yatayda tasmaz ve dikeyde
buyuyebilir.
"""

from PySide6 import QtWidgets

from arayuz.tasarim import tokenlar

A = tokenlar.ARALIK


def sayfa_duzeni(widget, dolgu=True):
    """Sekmenin kok QVBoxLayout'u (token dolgusu ve araligi)."""
    d = QtWidgets.QVBoxLayout(widget)
    if dolgu:
        d.setContentsMargins(A["l"], A["m"], A["l"], A["l"])
    else:
        d.setContentsMargins(0, 0, 0, 0)
    d.setSpacing(A["l"])
    return d


def sayfa_basligi(metin, aciklama=None):
    """Sayfa ust basligi: buyuk baslik + tek cumle aciklama (maket duzeni)."""
    w = QtWidgets.QWidget()
    d = QtWidgets.QVBoxLayout(w)
    d.setContentsMargins(0, 0, 0, 0)
    d.setSpacing(2)
    b = QtWidgets.QLabel(metin)
    b.setObjectName("baslik")
    d.addWidget(b)
    if aciklama:
        a = QtWidgets.QLabel(aciklama)
        a.setObjectName("ikincil")
        a.setWordWrap(True)
        d.addWidget(a)
    w.setAccessibleName(metin)
    return w


def satir(*ogeler, esnek=True, bosluk=None):
    """Yatay dugme/oge satiri; esnek=True sona bosluk koyar."""
    w = QtWidgets.QWidget()
    d = QtWidgets.QHBoxLayout(w)
    d.setContentsMargins(0, 0, 0, 0)
    d.setSpacing(A["s"] if bosluk is None else bosluk)
    for o in ogeler:
        if isinstance(o, QtWidgets.QLayout):
            d.addLayout(o)
        else:
            d.addWidget(o)
    if esnek:
        d.addStretch(1)
    return w


def sutun(*widgetlar, genislik=None, en_az=None, esnek=True):
    """Kartlardan dikey sutun (sag panel); genislik/en_az piksel tokenlari."""
    w = QtWidgets.QWidget()
    d = QtWidgets.QVBoxLayout(w)
    d.setContentsMargins(0, 0, 0, 0)
    d.setSpacing(A["l"])
    for x in widgetlar:
        d.addWidget(x)
    if esnek:
        d.addStretch(1)
    if genislik:
        w.setFixedWidth(genislik)
    if en_az:
        w.setMinimumWidth(en_az)
    return w


def form(bosluk_yatay=None, bosluk_dikey=None):
    """Token aralikli QFormLayout (etiketler sola hizali, alanlar buyur)."""
    from PySide6 import QtCore
    f = QtWidgets.QFormLayout()
    f.setContentsMargins(0, 0, 0, 0)
    f.setHorizontalSpacing(A["m"] if bosluk_yatay is None else bosluk_yatay)
    f.setVerticalSpacing(A["s"] if bosluk_dikey is None else bosluk_dikey)
    f.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
    f.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
    return f
