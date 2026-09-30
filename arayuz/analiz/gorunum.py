# -*- coding: utf-8 -*-
"""
gorunum.py -- Analiz ve Tukenme sayfalarinin ortak yerlesim parcalari
(maket duzeni: sayfa basligi + kartlar; arayuz/tasarim/maket_ekranlar.py).

    sayfa_basligi(baslik, aciklama_etiketi)  buyuk baslik + tek cumle aciklama
    kosu_satiri(birincil, durdur, ilerleme)  baslat / durdur / ilerleme cubugu
    kok_duzeni(widget)                        sayfanin token dolgulu kok duzeni

Renk, aralik ve yazi boyutu YALNIZCA tasarim tokenlarindan gelir; burada
sabit piksel ya da #rrggbb yoktur. Kabuk her sayfayi bir QScrollArea'ya
koyar: kok duzen yatayda tasmaz, dikeyde buyur.
"""

from PySide6 import QtWidgets

from arayuz.tasarim import tokenlar

A = tokenlar.ARALIK
B = tokenlar.BOYUT


def kok_duzeni(widget):
    """Sayfanin kok QVBoxLayout'u (token dolgusu ve araligi)."""
    d = QtWidgets.QVBoxLayout(widget)
    d.setContentsMargins(A["l"], A["m"], A["l"], A["l"])
    d.setSpacing(A["l"])
    return d


def sayfa_basligi(baslik, aciklama_etiketi=None):
    """
    Sayfa ust basligi. aciklama_etiketi: sekmenin KENDI QLabel'i (gorunurlugu
    sekme tarafindan yonetilebilsin diye disaridan verilir).
    """
    w = QtWidgets.QWidget()
    d = QtWidgets.QVBoxLayout(w)
    d.setContentsMargins(0, 0, 0, 0)
    d.setSpacing(A["xs"])
    e = QtWidgets.QLabel(baslik)
    e.setObjectName("baslik")
    d.addWidget(e)
    if aciklama_etiketi is not None:
        aciklama_etiketi.setObjectName("ikincil")
        aciklama_etiketi.setWordWrap(True)
        d.addWidget(aciklama_etiketi)
    w.setAccessibleName(baslik)
    return w


def kosu_satiri(birincil, durdur, ilerleme):
    """Birincil dugme + Durdur + esnek ilerleme cubugu (tek satir widget)."""
    for dugme in (birincil, durdur):
        dugme.setMinimumHeight(B["dugme_yuksekligi"])
    w = QtWidgets.QWidget()
    d = QtWidgets.QHBoxLayout(w)
    d.setContentsMargins(0, 0, 0, 0)
    d.setSpacing(A["s"])
    d.addWidget(birincil)
    d.addWidget(durdur)
    d.addWidget(ilerleme, 1)
    return w
