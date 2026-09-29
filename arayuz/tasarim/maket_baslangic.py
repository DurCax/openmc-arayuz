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
from cekirdek.ceviri import N_, _

A = tokenlar.ARALIK
_KATEGORI_ADI = dict(KATEGORILER)
_SUTUN_TUR = 4
_SUTUN_ORNEK = 4


def _tur_karti(ikon, baslik, aciklama, eylemler=(N_("Boş başla"), N_("Örnekten"))):
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
    k.govde.addStretch(1)
    eylem = QtWidgets.QHBoxLayout()
    eylem.setSpacing(A["s"])
    eylem.addWidget(b.ikincil_dugme(_(eylemler[0])))
    eylem.addWidget(b.duz_dugme(_(eylemler[1])))
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


def _dosya_karti():
    """Izgaranin 8. hucresi: kendi dosyasini acmak isteyen icin."""
    k = _tur_karti("folder-open", N_("Dosyadan aç"),
                   N_("Kaydedilmiş bir model (.json) ya da OpenMC XML klasörü."),
                   (N_("Aç…"), N_("XML içe aktar…")))
    return k


def _son_kullanilanlar():
    """Tek satirlik yatay serit: baslik + son dosyalar (dosya adi, dizin, zaman)."""
    serit = QtWidgets.QHBoxLayout()
    serit.setSpacing(A["xl"])
    serit.addWidget(b.BolumBasligi(_("Son kullanılanlar")), 0, QtCore.Qt.AlignVCenter)
    for ad, dizin, zaman in SON_KULLANILANLAR:
        oge = QtWidgets.QHBoxLayout()
        oge.setSpacing(A["s"])
        oge.addWidget(ikon_etiketi("file-text", "metin_soluk"))
        m = QtWidgets.QVBoxLayout()
        m.setSpacing(0)
        a = b.baglanti_dugmesi(ad)
        a.setToolTip("%s/%s" % (dizin, ad))
        m.addWidget(a, 0, QtCore.Qt.AlignLeft)
        y = QtWidgets.QLabel("%s · %s" % (dizin, _(zaman)))
        y.setObjectName("kucuk")
        m.addWidget(y)
        oge.addLayout(m)
        serit.addLayout(oge)
    serit.addStretch(1)
    return serit


def baslangic_icerigi():
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
    turler.addWidget(_dosya_karti(), 1, 3)
    for s_ in range(_SUTUN_TUR):
        turler.setColumnStretch(s_, 1)
    d.addLayout(turler)
    d.addSpacing(A["xs"])
    d.addLayout(_son_kullanilanlar())
    d.addSpacing(A["xs"])
    filtre = QtWidgets.QHBoxLayout()
    filtre.addWidget(b.BolumBasligi(_("Örnekler"), _("%d örnek · kategoriye göre süzün") % len(ORNEKLER)), 1)
    arama = QtWidgets.QLineEdit()
    arama.setPlaceholderText(_("Örneklerde ara…"))
    arama.setFixedWidth(220)
    filtre.addWidget(arama, 0, QtCore.Qt.AlignBottom)
    filtre.addWidget(b.SegmentSecici([(k_, _(m)) for k_, m in KATEGORILER], "hepsi"),
                     0, QtCore.Qt.AlignBottom)
    d.addLayout(filtre)
    ornekler = QtWidgets.QGridLayout()
    ornekler.setSpacing(A["m"])
    for i, o in enumerate(ORNEKLER):
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
