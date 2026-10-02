# -*- coding: utf-8 -*-
"""
yazi.py -- gomulu Inter yazi tipini yukler; mono aileyi sistemden secer.

    from arayuz.tasarim import yazi
    yazi.yukle()                 # QGuiApplication kurulduktan sonra, bir kez
    yazi.aile()                  # "Inter" ya da (yuklenemezse) sistem sans
    yazi.mono_aile()             # "JetBrains Mono" / "DejaVu Sans Mono" / ...
    yazi.font("baslik")          # tokenlar.TIPOGRAFI'den QFont

Inter bulunamazsa ya da yuklenemezse sistem sans yazisina DUSULUR ve bu
bir kez WARNING olarak loglanir (sessiz degil).
"""

import os

from PySide6 import QtGui

from arayuz.tasarim import tokenlar
from cekirdek import yollar
from cekirdek.gunluk import kaydedici

_log = kaydedici("arayuz.tasarim.yazi")
FONT_DIZINI = yollar.font_dizini()
FONT_DOSYALARI = ("Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-SemiBold.ttf")

_durum = {"yuklendi": False, "aile": None, "mono": None}

_AGIRLIK = {400: QtGui.QFont.Normal, 500: QtGui.QFont.Medium, 600: QtGui.QFont.DemiBold}


def yukle():
    """Gomulu Inter'i QFontDatabase'e ekler (tekrarlanan cagri ucuzdur).
    Dondurur: kullanilacak sans aile adi."""
    if _durum["yuklendi"]:
        return _durum["aile"]
    aileler = set()
    for ad in FONT_DOSYALARI:
        yol = os.path.join(FONT_DIZINI, ad)
        if not os.path.isfile(yol):
            _log.warning("Yazi tipi dosyasi yok: %s", yol)
            continue
        kimlik = QtGui.QFontDatabase.addApplicationFont(yol)
        if kimlik < 0:
            _log.warning("Yazi tipi yuklenemedi: %s", yol)
            continue
        aileler.update(QtGui.QFontDatabase.applicationFontFamilies(kimlik))
    if tokenlar.YAZI_AILESI in aileler:
        _durum["aile"] = tokenlar.YAZI_AILESI
    else:
        sistem = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.GeneralFont).family()
        _log.warning("Inter yuklenemedi; sistem yazisina dusuldu: %s", sistem)
        _durum["aile"] = sistem
    _durum["mono"] = _mono_sec()
    _durum["yuklendi"] = True
    return _durum["aile"]


def _mono_sec():
    mevcut = set(QtGui.QFontDatabase.families())
    for aday in tokenlar.MONO_ADAYLARI:
        if aday in mevcut:
            return aday
    return QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont).family()


def aile():
    return yukle()


def mono_aile():
    yukle()
    return _durum["mono"]


def font(rol="govde"):
    """tokenlar.TIPOGRAFI rolunden QFont (piksel boyutlu)."""
    boyut, agirlik, _satir = tokenlar.TIPOGRAFI[rol]
    mono = rol in ("mono", "sayi_buyuk")
    f = QtGui.QFont(mono_aile() if mono else aile())
    f.setPixelSize(boyut)
    f.setWeight(_AGIRLIK.get(agirlik, QtGui.QFont.Normal))
    if mono:
        f.setStyleHint(QtGui.QFont.Monospace)
    return f
