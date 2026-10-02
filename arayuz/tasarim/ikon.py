# -*- coding: utf-8 -*-
"""
ikon.py -- Lucide SVG ikonlarini tema rengine boyayip QIcon verir.

    from arayuz.tasarim.ikon import ikon, ikon_bagla
    d.setIcon(ikon("play"))                       # etkin temanin "metin" rengi
    d.setIcon(ikon("triangle-alert", renk="uyari"))   # token adi ya da "#rrggbb"
    ikon_bagla(d, "save")                          # tema degisince kendini yeniler

SVG'lerde stroke="currentColor" vardir; renk metin olarak yerine konur ve
QSvgRenderer ile 1x ve 2x (HiDPI) pikselle cizilir. Sonuc (ad, renk, boyut)
anahtariyla onbellekte tutulur; tema degisince renk degistigi icin anahtar da
degisir (eski girisler zararsizdir, onbellek sinirlidir).
"""

import functools
import os

from PySide6 import QtCore, QtGui
from PySide6.QtSvg import QSvgRenderer

from arayuz.tasarim import tokenlar
from cekirdek import yollar
from cekirdek.gunluk import kaydedici

_log = kaydedici("arayuz.tasarim.ikon")
IKON_DIZINI = yollar.ikon_dizini()
_ONBELLEK_BOYUTU = 512


def ikon_adlari():
    """Gomulu ikonlarin adlari (uzantisiz, sirali)."""
    return sorted(f[:-4] for f in os.listdir(IKON_DIZINI) if f.endswith(".svg"))


@functools.lru_cache(maxsize=None)
def _svg_metni(ad):
    yol = os.path.join(IKON_DIZINI, ad + ".svg")
    with open(yol, encoding="utf-8") as f:
        return f.read()


def _renk_coz(renk):
    if renk is None:
        renk = "metin"
    if renk.startswith("#"):
        return renk
    from arayuz import tema
    return tema.renk(renk)


def piksel(ad, renk_hex, boyut, olcek=1):
    """Tek bir boyali QPixmap (olcek: cihaz piksel orani)."""
    svg = _svg_metni(ad).replace("currentColor", renk_hex)
    cizici = QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8")))
    if not cizici.isValid():
        raise ValueError("gecersiz SVG ikon: %s" % ad)
    n = int(round(boyut * olcek))
    resim = QtGui.QImage(n, n, QtGui.QImage.Format_ARGB32_Premultiplied)
    resim.fill(QtCore.Qt.transparent)
    ressam = QtGui.QPainter(resim)
    ressam.setRenderHint(QtGui.QPainter.Antialiasing)
    cizici.render(ressam, QtCore.QRectF(0, 0, n, n))
    ressam.end()
    pm = QtGui.QPixmap.fromImage(resim)
    pm.setDevicePixelRatio(olcek)
    return pm


@functools.lru_cache(maxsize=_ONBELLEK_BOYUTU)
def _ikon_onbellekli(ad, renk_hex, boyut, pasif_hex):
    q = QtGui.QIcon()
    for olcek in (1, 2):
        q.addPixmap(piksel(ad, renk_hex, boyut, olcek), QtGui.QIcon.Normal)
        q.addPixmap(piksel(ad, pasif_hex, boyut, olcek), QtGui.QIcon.Disabled)
    return q


def ikon(ad, renk=None, boyut=None):
    """ad: Lucide adi ("play"); renk: token adi ya da "#rrggbb" (varsayilan
    "metin"); boyut: piksel (varsayilan tokenlar.BOYUT["ikon"]).
    Bilinmeyen ad -> bos QIcon + WARNING (arayuz cokmesin)."""
    boyut = int(boyut or tokenlar.BOYUT["ikon"])
    try:
        return _ikon_onbellekli(ad, _renk_coz(renk), boyut, _renk_coz("metin_pasif"))
    except (OSError, ValueError, KeyError):
        _log.warning("Ikon yuklenemedi: %s", ad, exc_info=True)
        return QtGui.QIcon()


def onbellegi_temizle():
    _ikon_onbellekli.cache_clear()


# ----------------------------------------------------------------------------
# Tema degisince ikonu yenilenen dugmeler
# ----------------------------------------------------------------------------
class _IkonYenileyici(QtCore.QObject):
    """Widget'in cocugu: widget silinince baglanti da kendiliginden kopar."""

    def __init__(self, widget, ad, renk, boyut):
        super().__init__(widget)
        self.setObjectName("_tasarimIkonYenileyici")
        self.bilgi = (ad, renk, boyut)
        from arayuz import tema
        tema.sinyal().degisti.connect(self.yenile)

    @QtCore.Slot(str)
    def yenile(self, *_):
        self.parent().setIcon(ikon(*self.bilgi))


def ikon_bagla(widget, ad, renk=None, boyut=None):
    """widget.setIcon(ikon(...)) yapar ve tema degisince tekrarlar.
    renk bir TOKEN adi olmali (sabit "#.." verilirse tema degisse de kalir)."""
    yenileyici = widget.findChild(_IkonYenileyici, "_tasarimIkonYenileyici",
                                  QtCore.Qt.FindDirectChildrenOnly)
    if yenileyici is None:
        yenileyici = _IkonYenileyici(widget, ad, renk, boyut)
    yenileyici.bilgi = (ad, renk, boyut)
    widget.setIcon(ikon(ad, renk, boyut))
    if boyut:
        widget.setIconSize(QtCore.QSize(int(boyut), int(boyut)))
    return widget
