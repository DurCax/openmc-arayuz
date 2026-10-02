# -*- coding: utf-8 -*-
"""
 arayuz/sonuc/mesh_cizim.py  --  mesh haritasinin matplotlib cizimi (v3 Y1)

 Dilim (cekirdek.mesh_tally.Dilim) kose koordinatlariyla pcolormesh: duzenli
 agda dikdortgen, silindirik (r, φ) ve kuresel meridyen dilimde egri olmayan
 dortgenler (kenarlar duz; bolme sayisi arttikca daire yaklasir). Guvenilmez
 hucreler (bagil hata esik ustu ya da skorsuz) hucre ortasinda "×" ile
 isaretlenir. Renk haritasi ve isaret rengi tasarim tokenlarindan.
"""

import numpy as np

from arayuz.tasarim import tokenlar

ISARET_RENGI = tokenlar.OKABE_ITO["turuncu"]
_ISARET_BOYU = 28


def hucre_ortalari(dilim):
    """Dortgen hucrelerin kose ortalamasi (x, y), sekil (na, nb)."""
    x, y = dilim.x, dilim.y
    ox = 0.25 * (x[:-1, :-1] + x[1:, :-1] + x[:-1, 1:] + x[1:, 1:])
    oy = 0.25 * (y[:-1, :-1] + y[1:, :-1] + y[:-1, 1:] + y[1:, 1:])
    return ox, oy


def ciz(figur, dilim, isaretli, baslik_metni, renk_etiketi):
    """Figuru temizler ve dilimi cizer; eksen nesnesini dondurur."""
    figur.clear()
    eks = figur.add_subplot(111)
    deger = np.ma.masked_invalid(np.asarray(dilim.deger, dtype=float))
    ortu = eks.pcolormesh(dilim.x, dilim.y, deger, shading="flat",
                          cmap=tokenlar.GRAFIK_HARITASI)
    figur.colorbar(ortu, ax=eks, label=renk_etiketi)
    if isaretli is not None and np.any(isaretli):
        ox, oy = hucre_ortalari(dilim)
        # Aciklama kartin ust metninde (× = guvenilmez); lejant haritayi ortuyordu.
        eks.scatter(ox[isaretli], oy[isaretli], marker="x", s=_ISARET_BOYU,
                    color=ISARET_RENGI, linewidths=1.2)
    eks.set_xlabel(dilim.x_adi)
    eks.set_ylabel(dilim.y_adi)
    if dilim.esit_olcek:
        eks.set_aspect("equal")
    eks.set_title(baslik_metni, fontsize="medium")
    return eks


def bos_ciz(figur, metin):
    """Veri yokken ortada kisa metin."""
    figur.clear()
    eks = figur.add_subplot(111)
    eks.set_axis_off()
    eks.text(0.5, 0.5, metin, ha="center", va="center", transform=eks.transAxes)
    return eks
