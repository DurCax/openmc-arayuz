# -*- coding: utf-8 -*-
"""
================================================================================
 tema.py  --  Gorunum temalari (tasarim tokenlarina bagli)
================================================================================
 HERKESE ACIK API (degismez; mevcut kod ve testler buna baglidir):
   TEMALAR            {"acik": {...}, "koyu": {...}} -- duz renk sozlukleri
   etkin()            etkin tema adi
   renk(ad)           etkin temadan renk ("zemin", "yuzey", "vurgu", "hata", ...)
   uygula(app, ad)    temayi uygular (ad None ise QSettings'ten)

 EK (Dalga 1, tasarim sistemi):
   uygula(app, ad, vurgu=None)   vurgu: tokenlar.VURGULAR anahtari
   etkin_vurgu()                 etkin vurgu adi
   sinyal().degisti(str)         tema/vurgu degisince yayilir (ikonlar yenilenir)
   grafik_paleti()               renk koruge uygun kategorik palet (Okabe-Ito)

 Renkler arayuz/tasarim/tokenlar.py'den, stil sayfasi arayuz/tasarim/stil.py'den
 gelir. Eski anahtarlar (yuzey, yuzey2, grafik_zemin, ...) tokenlara eslenir;
 yeni anahtarlar (yuzey1..3, metin_ikincil, vurgu_hover, *_soluk, odak ...) de
 ayni sozlukte bulunur.

 Tema yalnizca GORUNUMU degistirir; hicbir sayisal davranisi etkilemez.
 Secim QSettings'te saklanir ve bir sonraki aciliste hatirlanir.
================================================================================
"""

from PySide6 import QtCore, QtGui

from arayuz.tasarim import stil as _stil_modulu
from arayuz.tasarim import tokenlar
from cekirdek.gunluk import kaydedici

_log = kaydedici("arayuz.tema")

# Dalga 0 anahtarlari -> token (geriye uyum)
_ESKI_ANAHTARLAR = {
    "yuzey": "yuzey1",
    "grafik_zemin": "yuzey1",
}


def _tema_sozlugu(ad, vurgu):
    p = tokenlar.palet(ad, vurgu)
    eski = {k: p[v] for k, v in _ESKI_ANAHTARLAR.items()}
    return {"ad": tokenlar.TEMA_ADLARI[ad], **p, **eski}


def _temalari_kur(vurgu):
    return {ad: _tema_sozlugu(ad, vurgu) for ad in tokenlar.TEMA_ADLARI}


_ETKIN = "acik"
_VURGU = tokenlar.VARSAYILAN_VURGU
TEMALAR = _temalari_kur(_VURGU)


class _TemaYayici(QtCore.QObject):
    degisti = QtCore.Signal(str)


_yayici = None


def sinyal():
    """Tema degisim sinyalinin sahibi (tekil)."""
    global _yayici
    if _yayici is None:
        _yayici = _TemaYayici()
    return _yayici


def etkin():
    return _ETKIN


def etkin_vurgu():
    return _VURGU


def renk(ad):
    """Etkin temadan bir rengi dondurur (arayuzun her yeri buradan okur)."""
    return TEMALAR[_ETKIN][ad]


def grafik_paleti(ad=None):
    return tokenlar.GRAFIK_PALETI[ad or _ETKIN]


# ----------------------------------------------------------------------------
def _palet(t):
    p = QtGui.QPalette()
    R = QtGui.QColor
    roller = (
        (QtGui.QPalette.Window, "zemin"), (QtGui.QPalette.WindowText, "metin"),
        (QtGui.QPalette.Base, "yuzey1"), (QtGui.QPalette.AlternateBase, "yuzey2"),
        (QtGui.QPalette.Text, "metin"), (QtGui.QPalette.Button, "yuzey2"),
        (QtGui.QPalette.ButtonText, "metin"), (QtGui.QPalette.Highlight, "vurgu"),
        (QtGui.QPalette.HighlightedText, "vurgu_metin"), (QtGui.QPalette.ToolTipBase, "yuzey3"),
        (QtGui.QPalette.ToolTipText, "metin"), (QtGui.QPalette.Mid, "kenar"),
        (QtGui.QPalette.Dark, "metin_soluk"), (QtGui.QPalette.PlaceholderText, "metin_soluk"),
        (QtGui.QPalette.Link, "vurgu"), (QtGui.QPalette.Light, "yuzey1"),
        (QtGui.QPalette.Midlight, "yuzey3"), (QtGui.QPalette.Shadow, "golge"),
    )
    for rol, anahtar in roller:
        p.setColor(rol, R(t[anahtar]))
    for rol in (QtGui.QPalette.Text, QtGui.QPalette.ButtonText, QtGui.QPalette.WindowText):
        p.setColor(QtGui.QPalette.Disabled, rol, R(t["metin_pasif"]))
    return p


def _stil(t):
    """Stil sayfasi (geriye uyum: test_kabuk tema._stil(TEMALAR[..]) cagirir)."""
    from arayuz.tasarim import yazi
    aile = mono = None
    if QtGui.QGuiApplication.instance() is not None:
        aile, mono = yazi.aile(), yazi.mono_aile()
    return _stil_modulu.uret(t, aile=aile, mono=mono)


def _matplotlib_uydur(t, palet_):
    """Grafikleri arayuz paletine uydurur (renk koruge uygun renk dongusu)."""
    import matplotlib
    from cycler import cycler
    from arayuz.tasarim import yazi
    ayar = {
        "figure.facecolor": t["grafik_zemin"],
        "axes.facecolor": t["grafik_zemin"],
        "savefig.facecolor": t["grafik_zemin"],
        "axes.edgecolor": t["kenar_guclu"],
        "axes.labelcolor": t["metin_ikincil"],
        "axes.titlecolor": t["metin"],
        "axes.prop_cycle": cycler(color=list(palet_)),
        "axes.spines.top": False,
        "axes.spines.right": False,
        "text.color": t["metin"],
        "xtick.color": t["metin_soluk"],
        "ytick.color": t["metin_soluk"],
        "grid.color": t["grafik_izgara"],
        "legend.facecolor": t["yuzey1"],
        "legend.edgecolor": t["kenar"],
        "legend.frameon": False,
        "image.cmap": tokenlar.GRAFIK_HARITASI,
        "font.size": 9,
    }
    if QtGui.QGuiApplication.instance() is not None:
        from matplotlib import font_manager
        aile = yazi.aile()
        try:
            font_manager.fontManager.addfont(_inter_yolu())
            ayar["font.family"] = [aile, "DejaVu Sans"]
        except (OSError, RuntimeError, ValueError):
            _log.warning("matplotlib Inter'i yukleyemedi; varsayilan yazi", exc_info=True)
    matplotlib.rcParams.update(ayar)


def _inter_yolu():
    import os
    from arayuz.tasarim import yazi
    return os.path.join(yazi.FONT_DIZINI, "Inter-Regular.ttf")


def uygula(app, ad=None, vurgu=None):
    """Temayi uygular. ad/vurgu verilmezse QSettings'ten okunur."""
    global _ETKIN, _VURGU, TEMALAR
    from arayuz.tasarim import ikon, yazi
    ayar = QtCore.QSettings("openmc_arayuz", "arayuz")
    if ad is None:
        ad = ayar.value("tema", "acik")
    if ad not in tokenlar.TEMA_ADLARI:
        ad = "acik"
    if vurgu is None:
        vurgu = ayar.value("tema_vurgu", tokenlar.VARSAYILAN_VURGU)
    if vurgu not in tokenlar.VURGULAR:
        vurgu = tokenlar.VARSAYILAN_VURGU
    if vurgu != _VURGU:
        TEMALAR = _temalari_kur(vurgu)
        ikon.onbellegi_temizle()
    _ETKIN, _VURGU = ad, vurgu
    t = TEMALAR[ad]
    aile = yazi.yukle()
    app.setStyle("Fusion")
    f = QtGui.QFont(aile)
    f.setPixelSize(tokenlar.TIPOGRAFI["govde"][0])
    app.setFont(f)
    app.setPalette(_palet(t))
    app.setStyleSheet(_stil(t))
    _matplotlib_uydur(t, grafik_paleti(ad))
    ayar.setValue("tema", ad)
    ayar.setValue("tema_vurgu", vurgu)
    sinyal().degisti.emit(ad)
    return ad


