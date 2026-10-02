# -*- coding: utf-8 -*-
"""
 bindirme.py  --  Mesh tally (Y1) ve kaynak noktalarinin kesit uzerine bindirilmesi
                  (saf numpy; Qt'siz)

 AYNI KOORDINAT CERCEVESI
   Bindirme geometri kesitinin piksel izgarasinda orneklenir: her pikselin
   merkezi (gorunum.piksel_merkezi kurali) 3B noktaya cevrilir, noktanin ag
   koordinati (duzenli: x, y, z; silindirik: r, phi, z; kuresel: r, theta, phi
   -- donusum cekirdek/mesh_tally/geometri.py ile ayni, OpenMC 0.16.0) ag
   izgarasinda aranir. Boylece imshow ayni extent ile cizildiginde ag hucresi
   geometrinin tam ustune duser (testler/test_y2_gorunum.py: bilinen hucre <->
   koordinat). Ag disindaki piksel NaN (saydam).
 SIGMA MASKESI
   maske3b (mt.yuksek_hata_maskesi: bagil hata > esik ya da skorsuz) dogruysa
   piksel gizlenir (NaN) ve `guvenilmez` dizisinde isaretlenir.
 COZUNURLUK
   Ornekleme en cok BINDIRME_PIKSEL x orantili dikey pikseldir (ag hucreleri
   piksellerden buyuktur); 400 x 400 ~ 30 ms (ana is parcacigi esigi 200 ms).
"""

from dataclasses import dataclass

import numpy as np

from cekirdek import cizim_sureci as cs
from cekirdek.mesh_tally.tanim import DUZENLI, KURESEL, SILINDIRIK
from arayuz.goruntuleyici import gorunum as gr

BINDIRME_PIKSEL = 400
_IKI_PI = 2.0 * np.pi


@dataclass(frozen=True)
class Raster:
    """Kesit izgarasinda orneklenmis ag degeri."""
    deger: np.ndarray            # (v, h) float, NaN = ag disi ya da maskeli
    guvenilmez: np.ndarray       # (v, h) bool
    kapsam: tuple                # imshow extent (gorunum.kapsam)
    aralik: tuple                # (en kucuk, en buyuk) sonlu deger; yoksa (nan, nan)


def _piksel_noktalari(g: gr.Gorunum, nh: int, nv: int):
    """Piksel merkezlerinin (x, y, z) dizileri, sekil (nv, nh)."""
    u0, u1, v0, v1 = g.kapsam
    u = u0 + (np.arange(nh) + 0.5) * (u1 - u0) / nh
    v = v1 - (np.arange(nv) + 0.5) * (v1 - v0) / nv
    U, V = np.meshgrid(u, v)
    h, d, n = gr.EKSENLER[g.eksen]
    xyz = [None, None, None]
    xyz[h], xyz[d] = U, V
    xyz[n] = np.full_like(U, g.merkez[n])
    return xyz


def ag_koordinati(tur: str, x, y, z, merkez) -> tuple:
    """Kartezyen -> ag koordinati (geometri.kartezyen'in tersi)."""
    if tur == DUZENLI:
        return x, y, z
    ox, oy, oz = merkez
    dx, dy, dz = x - ox, y - oy, z - oz
    if tur == SILINDIRIK:
        return np.hypot(dx, dy), np.mod(np.arctan2(dy, dx), _IKI_PI), dz
    if tur == KURESEL:
        r = np.sqrt(dx * dx + dy * dy + dz * dz)
        with np.errstate(invalid="ignore", divide="ignore"):
            teta = np.arccos(np.clip(np.where(r > 0, dz / np.where(r > 0, r, 1.0), 1.0),
                                     -1.0, 1.0))
        return r, teta, np.mod(np.arctan2(dy, dx), _IKI_PI)
    raise ValueError("bilinmeyen ağ türü: %s" % tur)


def _indeks(izgara, deger):
    """Izgara hucre indeksi; disarida -1 (son sinir dahil)."""
    izgara = np.asarray(izgara, dtype=float)
    i = np.searchsorted(izgara, deger, side="right") - 1
    i = np.where(deger == izgara[-1], len(izgara) - 2, i)
    disari = (deger < izgara[0]) | (deger > izgara[-1]) | ~np.isfinite(deger)
    return np.where(disari, -1, i)


def ag_indeksleri(sonuc, x, y, z) -> tuple:
    """Her nokta icin (i, j, k) ag indeksi (disarida -1)."""
    a, b, c = ag_koordinati(sonuc.tur, x, y, z, sonuc.merkez)
    return tuple(_indeks(g, v) for g, v in zip(sonuc.izgaralar, (a, b, c)))


def raster_boyutu(g: gr.Gorunum, sekil=None) -> tuple:
    """(nv, nh) ornekleme boyutu: geometri dizisinin sekli (v, h) verilirse ondan,
    yoksa gorunum oranindan; her eksen [1, PIKSEL_EN_COK] icinde (ince-uzun modelde
    400:1 oran 160 000 satir demekti)."""
    if sekil is not None:
        v, h = int(sekil[0]), int(sekil[1])
    else:
        h = int(g.piksel)
        v = int(round(h * g.genislik[1] / g.genislik[0]))
    nh = max(1, min(h, BINDIRME_PIKSEL))
    nv = int(round(nh * v / max(h, 1)))
    return max(1, min(nv, cs.PIKSEL_EN_COK)), nh


def raster(sonuc, deger3b, maske3b, g: gr.Gorunum, sigma_maskesi: bool = True,
           sekil=None) -> Raster:
    """Ag degerini (n1, n2, n3) kesit gorunumunun piksel izgarasinda orneklenir."""
    nv, nh = raster_boyutu(g, sekil)
    x, y, z = _piksel_noktalari(g, nh, nv)
    i, j, k = ag_indeksleri(sonuc, x, y, z)
    icerde = (i >= 0) & (j >= 0) & (k >= 0)
    deger = np.full((nv, nh), np.nan)
    guvenilmez = np.zeros((nv, nh), dtype=bool)
    d3, m3 = np.asarray(deger3b, dtype=float), np.asarray(maske3b, dtype=bool)
    deger[icerde] = d3[i[icerde], j[icerde], k[icerde]]
    guvenilmez[icerde] = m3[i[icerde], j[icerde], k[icerde]]
    if sigma_maskesi:
        deger = np.where(guvenilmez, np.nan, deger)
    sonlu = deger[np.isfinite(deger)]
    aralik = (float(sonlu.min()), float(sonlu.max())) if sonlu.size else (np.nan, np.nan)
    return Raster(deger=deger, guvenilmez=guvenilmez, kapsam=g.kapsam, aralik=aralik)


def izdusum(noktalar, g: gr.Gorunum, kalinlik=None) -> tuple:
    """Kaynak noktalarinin kesit duzlemine izdusumu (u, v) -- yalniz penceredekiler
    ve (kalinlik verilirse) |normal - konum| <= kalinlik / 2 olanlar."""
    r = np.asarray(noktalar, dtype=float).reshape(-1, 3)
    h, d, n = gr.EKSENLER[g.eksen]
    u0, u1, v0, v1 = g.kapsam
    sec = (r[:, h] >= u0) & (r[:, h] <= u1) & (r[:, d] >= v0) & (r[:, d] <= v1)
    if kalinlik is not None:
        sec &= np.abs(r[:, n] - g.konum) <= kalinlik / 2.0
    return r[sec, h], r[sec, d]


def tally_dizileri(sonuc, skor: str, grup, yontem: str, esik: float, eksenel_sonsuz: bool):
    """(deger3b, guvenilmez3b, birim): secilen skor/grup, normalizasyon (Y1 ile ayni:
    cekirdek/mesh_tally) ve sigma maskesi. Skorsuz hucre NaN (renk olcegini 0'a
    cekmesin; Calistir > Ag haritasi ile ayni kural)."""
    from cekirdek import mesh_tally as mt
    o, sg = mt.secim(sonuc, skor, grup)
    maske = mt.yuksek_hata_maskesi(o, sg, esik)
    payda, olcu_turu = mt.olcu(sonuc, eksenel_sonsuz)
    deger, _sapma, birim = mt.normalize(o, sg, payda, yontem, None, skor, sonuc.ozdeger,
                                        olcu_turu)
    return np.where(o == 0, np.nan, deger), maske, birim
