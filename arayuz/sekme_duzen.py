# -*- coding: utf-8 -*-
"""
sekme_duzen.py -- sayfalarin ortak duzeni: tasarim sekmeleri (Malzemeler,
Parcalar, Demet) ve hesap sayfalari (Analiz, Tukenme) icin sayfa basligi,
kok duzen, dugme satiri, kosu satiri, kart sutunu. (Dalga 2 kapanis:
eski arayuz/analiz/gorunum.py buraya katildi; davranis degismedi.)

Renk, aralik ve yazi boyutu YALNIZCA tasarim tokenlarindan gelir
(arayuz/tasarim/tokenlar.py); burada sabit piksel ya da #rrggbb yoktur.
Sekmeler QTabWidget'a bagli degildir: kabuk (Ajan 6) her sayfayi bir
QScrollArea icine koyar, bu yuzden kok duzen yatayda tasmaz ve dikeyde
buyuyebilir.
"""

from PySide6 import QtGui, QtWidgets

from arayuz.tasarim import tokenlar

A = tokenlar.ARALIK
B = tokenlar.BOYUT

# Baslik ile aciklama arasi (tasarim sekmelerinin mevcut gorunumu). Hesap
# sayfalari A["xs"] verir; ikisi de korunur ki ekran degismesin.
_BASLIK_ARALIGI = 2


def sayfa_duzeni(widget, dolgu=True):
    """Sekmenin kok QVBoxLayout'u (token dolgusu ve araligi)."""
    d = QtWidgets.QVBoxLayout(widget)
    if dolgu:
        d.setContentsMargins(A["l"], A["m"], A["l"], A["l"])
    else:
        d.setContentsMargins(0, 0, 0, 0)
    d.setSpacing(A["l"])
    return d


def sayfa_basligi(metin, aciklama=None, bosluk=None, bolum=None):
    """
    Sayfa ust basligi: buyuk baslik + tek cumle aciklama (maket duzeni).
    aciklama: metin ya da sekmenin KENDI QLabel'i (gorunurlugunu sekme
    yonetebilsin diye disaridan verilir); bosluk: baslik-aciklama araligi;
    bolum: kilavuz bolum kimligi -> basligin sagina "?" dugmesi
    (arayuz/yardim_baglanti.py).
    """
    w = QtWidgets.QWidget()
    d = QtWidgets.QVBoxLayout(w)
    d.setContentsMargins(0, 0, 0, 0)
    d.setSpacing(_BASLIK_ARALIGI if bosluk is None else bosluk)
    b = QtWidgets.QLabel(metin)
    b.setObjectName("baslik")
    if bolum:
        from arayuz.yardim_baglanti import yardim_dugmesi
        ust = QtWidgets.QHBoxLayout()
        ust.setContentsMargins(0, 0, 0, 0)
        ust.setSpacing(A["xs"])
        ust.addWidget(b)
        w.yardim_dugmesi = yardim_dugmesi(bolum, w)
        ust.addWidget(w.yardim_dugmesi)
        ust.addStretch(1)
        d.addLayout(ust)
    else:
        d.addWidget(b)
    a = aciklama
    if isinstance(aciklama, str):
        a = QtWidgets.QLabel(aciklama) if aciklama else None
    if a is not None:
        a.setObjectName("ikincil")
        a.setWordWrap(True)
        d.addWidget(a)
    w.setAccessibleName(metin)
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


# ----------------------------------------------------------------------
# Kabuk sozlesmesi (arayuz/pencere/sekme_arayuzu.py) yardimcilari
# ----------------------------------------------------------------------
def _dugme_eylemi(sahip, onek, dugme):
    e = QtGui.QAction(dugme.icon(), "%s: %s" % (onek, dugme.text().strip()), sahip)
    e.setToolTip(dugme.toolTip())
    e.triggered.connect(dugme.click)
    return e


def dugme_komutlari(sahip, onek, dugmeler):
    """
    Sekme dugmelerinin Ctrl+K paleti eylemleri (QAction). Eylem dugmeye
    tiklar: davranis tek yerde (dugmenin baglantisi) kalir. Eylemler ilk
    cagrida kurulur; etkinlik her cagrida dugmeden alinir.
    """
    dugmeler = tuple(dugmeler)
    eylemler = getattr(sahip, "_komut_eylemleri", None)
    if eylemler is None:
        eylemler = tuple(_dugme_eylemi(sahip, onek, d) for d in dugmeler)
        sahip._komut_eylemleri = eylemler
    for e, d in zip(eylemler, dugmeler):
        e.setEnabled(d.isEnabled() and not d.isHidden())
    return eylemler


def yer_adi(yer, *turler):
    """Bulgu yeri "tur:ad" -> (tur, ad); tur beklenmiyorsa ya da ad bossa None."""
    tur, ayirac, ad = (yer or "").partition(":")
    if not ayirac or tur not in turler or not ad.strip():
        return None
    return tur, ad.strip()
