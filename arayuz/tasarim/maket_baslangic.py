# -*- coding: utf-8 -*-
"""
maket_baslangic.py -- (b) Baslangic ekrani maketi: model turu kartlari (ikon,
kisa aciklama, iki eylem), filtrelenebilir ornek galerisi (kategori segmenti +
arama, kucuk resimli kartlar) ve son kullanilanlar. Kenar cubugu yok (model
henuz yok); ust cubukta Calistir pasif.
"""

from PySide6 import QtCore, QtWidgets

from arayuz import bilesenler as b
from arayuz.tasarim import tokenlar
from arayuz.tasarim.maket_cizim import KucukResim
from arayuz.tasarim.maket_kabuk import _menu_kur, ikon_etiketi, ust_cubuk
from arayuz.tasarim.maket_veri import KATEGORILER, MODEL_TURLERI, ORNEKLER, SON_KULLANILANLAR
from cekirdek.ceviri import _

A = tokenlar.ARALIK
_KATEGORI_ADI = dict(KATEGORILER)
_SUTUN_TUR = 4
_SUTUN_ORNEK = 4


def _tur_karti(ikon, baslik, aciklama):
    k = b.Kart(dolgu="l")
    k.setProperty("tiklanir", True)
    ust = QtWidgets.QHBoxLayout()
    ust.setSpacing(A["m"])
    ust.addWidget(ikon_etiketi(ikon, "vurgu", 24), 0, QtCore.Qt.AlignTop)
    metin = QtWidgets.QVBoxLayout()
    metin.setSpacing(2)
    bl = QtWidgets.QLabel(_(baslik))
    bl.setObjectName("altBaslik")
    metin.addWidget(bl)
    a = QtWidgets.QLabel(_(aciklama))
    a.setObjectName("kucuk")
    a.setWordWrap(True)
    metin.addWidget(a)
    ust.addLayout(metin, 1)
    k.govde.addLayout(ust)
    eylem = QtWidgets.QHBoxLayout()
    eylem.setSpacing(A["s"])
    eylem.addWidget(b.ikincil_dugme(_("Boş başla")))
    eylem.addWidget(b.duz_dugme(_("Örnekten")))
    eylem.addStretch(1)
    k.govde.addLayout(eylem)
    k.setAccessibleName(_(baslik))
    return k


def _ornek_karti(baslik, kategori, aciklama, motif):
    k = b.Kart(dolgu="m")
    k.setProperty("tiklanir", True)
    k.ekle(KucukResim(motif))
    ust = QtWidgets.QHBoxLayout()
    bl = QtWidgets.QLabel(_(baslik))
    bl.setObjectName("govdeVurgulu")
    ust.addWidget(bl, 1)
    ust.addWidget(b.Rozet(_(_KATEGORI_ADI[kategori]), "notr"))
    k.govde.addLayout(ust)
    a = QtWidgets.QLabel(_(aciklama))
    a.setObjectName("kucuk")
    a.setWordWrap(True)
    k.ekle(a)
    k.setAccessibleName(_(baslik))
    return k


def _son_kullanilanlar():
    k = b.Kart(_("Son kullanılanlar"), eylem=b.baglanti_dugmesi(_("Başka dosya aç…")))
    for ad, dizin, zaman in SON_KULLANILANLAR:
        satir = QtWidgets.QHBoxLayout()
        satir.setSpacing(A["s"])
        satir.addWidget(ikon_etiketi("file-text", "metin_soluk"))
        m = QtWidgets.QVBoxLayout()
        m.setSpacing(0)
        a = QtWidgets.QLabel(ad)
        a.setObjectName("govdeVurgulu")
        m.addWidget(a)
        y = QtWidgets.QLabel(dizin)
        y.setObjectName("kucuk")
        m.addWidget(y)
        satir.addLayout(m, 1)
        z = QtWidgets.QLabel(_(zaman))
        z.setObjectName("kucuk")
        satir.addWidget(z)
        k.govde.addLayout(satir)
    return k


def baslangic_icerigi(kategori="pwr"):
    ic = QtWidgets.QWidget()
    ic.setObjectName("sayfa")
    d = QtWidgets.QVBoxLayout(ic)
    d.setContentsMargins(A["xxl"] * 2, A["xl"], A["xxl"] * 2, A["xl"])
    d.setSpacing(A["m"])
    baslik = QtWidgets.QLabel(_("Ne modellemek istiyorsunuz?"))
    baslik.setObjectName("baslikBuyuk")
    d.addWidget(baslik)
    alt = QtWidgets.QLabel(_("Bir model türüyle boş başlayın ya da hazır bir örneğin kopyasını açın."))
    alt.setObjectName("ikincil")
    d.addWidget(alt)
    d.addSpacing(A["xs"])
    turler = QtWidgets.QGridLayout()
    turler.setSpacing(A["m"])
    for i, (ikon, bas, ac) in enumerate(MODEL_TURLERI):
        turler.addWidget(_tur_karti(ikon, bas, ac), i // _SUTUN_TUR, i % _SUTUN_TUR)
    turler.addWidget(_son_kullanilanlar(), 1, 3)
    d.addLayout(turler)
    d.addSpacing(A["m"])
    filtre = QtWidgets.QHBoxLayout()
    filtre.addWidget(b.BolumBasligi(_("Örnekler"), _("%d örnek · kategoriye göre süzün") % len(ORNEKLER)))
    filtre.addStretch(1)
    arama = QtWidgets.QLineEdit()
    arama.setPlaceholderText(_("Örneklerde ara…"))
    arama.setFixedWidth(220)
    filtre.addWidget(arama, 0, QtCore.Qt.AlignBottom)
    filtre.addWidget(b.SegmentSecici([(k_, _(m)) for k_, m in KATEGORILER], "hepsi"),
                     0, QtCore.Qt.AlignBottom)
    d.addLayout(filtre)
    ornekler = QtWidgets.QGridLayout()
    ornekler.setSpacing(A["m"])
    for i, o in enumerate(ORNEKLER[:8]):
        ornekler.addWidget(_ornek_karti(*o), i // _SUTUN_ORNEK, i % _SUTUN_ORNEK)
    for s in range(_SUTUN_ORNEK):
        ornekler.setColumnStretch(s, 1)
    d.addLayout(ornekler)
    d.addStretch(1)
    alan = QtWidgets.QScrollArea()
    alan.setObjectName("sayfa")
    alan.setWidgetResizable(True)
    alan.setFrameShape(QtWidgets.QFrame.NoFrame)
    alan.setWidget(ic)
    return alan


class MaketBaslangic(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(_("OpenMC arayüzü — başlangıç (maket)"))
        _menu_kur(self)
        m = QtWidgets.QWidget()
        d = QtWidgets.QVBoxLayout(m)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(0)
        d.addWidget(ust_cubuk(model=False))
        d.addWidget(baslangic_icerigi(), 1)
        self.setCentralWidget(m)
