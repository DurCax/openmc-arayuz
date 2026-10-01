# -*- coding: utf-8 -*-
"""
================================================================================
 guc_harita_kor.py  --  Kor olcegi guc haritasinin eleman sekilleri (SAF)
================================================================================
 Tam kor anahtarinin her duzeyi ayni kafes turunde olmayabilir (Dalga G-2):
   kare / altigen kafes      eleman sekli kafesin adimi ve yonelimiyle
   "karisik" (KarisikDuzey)  parca (kafes adi, i, j): sekil o kafesten
   "yerlesim" (YerlesimDuzeyi) parca (ad, i): kafessiz; sekil uyelerin kutusu
 Merkezler cekirdek/guc.py'den (cubuk_merkezi, demet_merkezi) gelir; burada
 yalnizca "hangi kafes, hangi sekil" sorusu yanitlanir. Qt gerektirmez.
================================================================================
"""

import math

from matplotlib.patches import Rectangle, RegularPolygon

from cekirdek import altigen, guc_kor as _guc_kor

# kafessiz (yerlesim) demetin kutusu: uye cubuk merkezlerinin zarfina eklenen pay
_KUTU_PAYI = 0.5


def parca_kafesi(kafes, parca):
    """Duzey kafesi ve anahtar parcasi -> elemani tasiyan gercek kafes."""
    if isinstance(kafes, _guc_kor.KarisikDuzey):
        return kafes.kafesler.get(parca[0])
    return kafes


def eleman_bicimi(kafes):
    """(tur, adim, yonelim) -- kare / altigen; kafessiz duzeyde None."""
    import openmc
    if kafes is None or isinstance(kafes, (_guc_kor.YerlesimDuzeyi, _guc_kor.KarisikDuzey)):
        return None
    if isinstance(kafes, (openmc.HexLattice, _guc_kor.OtelemeDuzeyi)):
        return "altigen", float(kafes.pitch[0]), getattr(kafes, "orientation", "y")
    return "kare", float(kafes.pitch[0]), None


def _son_parca(anahtar_parcasi, tek):
    return anahtar_parcasi if tek else anahtar_parcasi[-1]


def demet_bicimi(dagilim, demet):
    """Demet elemaninin bicimi (en ic demet duzeyinin kafesinden)."""
    tek = dagilim.get("duzey_sayisi", 1) == 2
    return eleman_bicimi(parca_kafesi(dagilim["kafesler"][-2], _son_parca(demet, tek)))


def cubuk_bicimi(dagilim, anahtar):
    """Cubuk elemaninin bicimi (en ic duzeyin kafesinden)."""
    return eleman_bicimi(parca_kafesi(dagilim["kafesler"][-1], anahtar[-1]))


def yama(bicim, merkez, olcek=1.0, **stil):
    """Bicimin yamasi: kare (adim x adim) ya da altigen; olcek < 1 icten cizer."""
    tur, adim, yonelim = bicim
    adim = adim * olcek
    if tur == "altigen":
        kose = altigen.hucre_kose_acilari(yonelim)[0]
        return RegularPolygon(merkez, numVertices=6, radius=adim / math.sqrt(3.0),
                              orientation=math.radians(kose - 30.0), **stil)
    return Rectangle((merkez[0] - adim / 2.0, merkez[1] - adim / 2.0), adim, adim, **stil)


def kutu(noktalar, pay):
    """Noktalarin zarfi + pay: (x0, y0, genislik, yukseklik)."""
    xs = [p[0] for p in noktalar]
    ys = [p[1] for p in noktalar]
    return (min(xs) - pay, min(ys) - pay, max(xs) - min(xs) + 2 * pay,
            max(ys) - min(ys) + 2 * pay)


def kutu_yamasi(noktalar, pay, **stil):
    """Kafessiz demet: uye cubuklarin zarfi (dikdortgen)."""
    x0, y0, g, y = kutu(noktalar, pay * (1.0 + _KUTU_PAYI))
    return Rectangle((x0, y0), g, y, **stil)
