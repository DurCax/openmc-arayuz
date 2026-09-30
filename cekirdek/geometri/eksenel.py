# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/eksenel.py  --  Eksenel yiginlar: yukseklik, dilimler, aktif aralik
================================================================================

 docs/GEOMETRI_MODELI.md §3.7, R7, R8.
   - Katmanlar alttan uste; yigin z = 0 etrafinda merkezlenir.
   - Yuksekligi <= 0 olan katman atlanir (sablonun eksenel_katmanlar davranisi).
   - Kokun ic'indeki yigin model yuksekligini belirler (tek gercek kaynak);
     kok disindaki bir yiginin toplami model yuksekligine esit olmalidir.
================================================================================
"""


def gecerli_katmanlar(eksenel):
    """Yuksekligi > 0 olan katmanlar (sirali)."""
    return [k for k in eksenel.get("katmanlar") or []
            if float(k.get("yukseklik") or 0.0) > 0.0]


def dilimler(eksenel):
    """[(z0, z1, katman)] -- yigin z = 0 etrafinda merkezli."""
    katmanlar = gecerli_katmanlar(eksenel)
    toplam = sum(float(k["yukseklik"]) for k in katmanlar)
    z = -toplam / 2.0
    cikti = []
    for k in katmanlar:
        h = float(k["yukseklik"])
        cikti.append((z, z + h, k))
        z += h
    return cikti


def yigin_yuksekligi(eksenel):
    """Gecerli katmanlarin toplam yuksekligi."""
    d = dilimler(eksenel)
    return (d[-1][1] - d[0][0]) if d else 0.0


def kok_yigini(kok):
    """Kokun ic'indeki eksenel yigin ya da None."""
    ic = kok.get("ic")
    return ic if isinstance(ic, dict) and ic.get("tur") == "eksenel" else None


def model_yuksekligi(m):
    """GeometriModeli -> toplam yukseklik [cm] ya da None (2B)."""
    kok = m.kok if hasattr(m, "kok") else m
    yigin = kok_yigini(kok)
    if yigin is not None and gecerli_katmanlar(yigin):
        return yigin_yuksekligi(yigin)
    h = kok.get("yukseklik")
    return float(h) if h else None
