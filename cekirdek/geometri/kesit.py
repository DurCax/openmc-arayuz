# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/kesit.py  --  Kesit (2B sekil) hesaplari: kutu, buyutme, kapsama, alan
================================================================================

 openmc gerektirmez; dogrulama, genislet ve kurucu ayni olculeri kullanir.

 KESIT TURLERI (docs/GEOMETRI_MODELI.md §3.6)
   dikdortgen  {"boyut": [gx, gy]}
   silindir    {"yaricap": r}
   altigen     {"apotem": a, "yonelim": "x"|"y"}   HexagonalPrism anlaminda:
               'y' -> duz yuzler sagda/solda (dusey), yuz normalleri 0, 60, ...
               'x' -> duz yuzler ustte/altta (yatay), yuz normalleri 30, 90, ...
   kure        {"yaricap": r}                      (yalniz kok)
   kafes_zarfi {}                                  (yalniz altigen kafesli kok)

 Kesitler her zaman kendi yerel cercevesinde (0, 0) merkezlidir; yerlesim
 delikleri merkez (x0, y0) ile verilir.
================================================================================
"""

import math
from typing import Callable

from cekirdek.ceviri import _

SQ3 = math.sqrt(3.0)
SEKILLER = ("dikdortgen", "silindir", "altigen", "kure", "kafes_zarfi")
YONELIMLER = ("x", "y")
# Ayni yuzey kabul payi (cm): kapsama ve oturma denetimleri
PAY = 1.0e-9


def ters_yonelim(yonelim):
    """'x' <-> 'y'."""
    return "x" if yonelim == "y" else "y"


def altigen_normal_acilari(prizma_yonelimi):
    """HexagonalPrism'in 6 yuz normali (derece, artan): 'y' 0,60..; 'x' 30,90.."""
    taban = 0.0 if prizma_yonelimi == "y" else 30.0
    return [taban + 60.0 * k for k in range(6)]


# ----------------------------------------------------------------------------
# on hesap tablolari (H1b): gezinti ayni sin/cos'u yuz binlerce kez istiyordu.
# Degerler eski ifadenin AYNISIYLA bir kez hesaplanir (bit duzeyinde ayni).
# ----------------------------------------------------------------------------

def _normal_tablosu(prizma_yonelimi):
    return tuple((math.cos(math.radians(aci)), math.sin(math.radians(aci)))
                 for aci in altigen_normal_acilari(prizma_yonelimi))


def _kose_tablosu(prizma_yonelimi):
    return tuple((math.cos(math.radians(aci + 30.0)), math.sin(math.radians(aci + 30.0)))
                 for aci in altigen_normal_acilari(prizma_yonelimi))


_NORMALLER = {True: _normal_tablosu("y"), False: _normal_tablosu("x")}
_KOSELER = {True: _kose_tablosu("y"), False: _kose_tablosu("x")}
_DAIRE_TABLOLARI = {}


def _birim_normaller(yonelim):
    """6 yuz normalinin (cos, sin) tablosu; 'y' disindaki her deger 'x' gibi."""
    return _NORMALLER[yonelim == "y"]


def _daire_tablosu(n_daire):
    tablo = _DAIRE_TABLOLARI.get(n_daire)
    if tablo is None:
        tablo = tuple((math.cos(2 * math.pi * i / n_daire), math.sin(2 * math.pi * i / n_daire))
                      for i in range(n_daire))
        _DAIRE_TABLOLARI[n_daire] = tablo
    return tablo


def kafes_zarfi_apotemi(halka_sayisi, adim):
    """Altigen kafes hucrelerinin tam zarfinin apotemi (yonelim = kafes yonelimi)."""
    return (halka_sayisi - 1) * adim * SQ3 / 2.0 + adim / SQ3


def kutu(kesit):
    """Kesitin eksene hizali sinir kutusu (genislik, yukseklik)."""
    s = kesit.get("sekil")
    if s == "dikdortgen":
        return (float(kesit["boyut"][0]), float(kesit["boyut"][1]))
    if s in ("silindir", "kure"):
        d = 2.0 * float(kesit["yaricap"])
        return (d, d)
    if s == "altigen":
        a = float(kesit["apotem"])
        uzun = 2.0 * a * 2.0 / SQ3
        return (2.0 * a, uzun) if kesit.get("yonelim", "y") == "y" else (uzun, 2.0 * a)
    raise ValueError(_("kutusu hesaplanamayan kesit: %s") % s)


def buyut(kesit, kalinlik):
    """Ayni sekli 'kalinlik' kadar duzgun buyuten YENI kesit (§3.6 halka)."""
    s = kesit.get("sekil")
    k = float(kalinlik)
    if s == "dikdortgen":
        gx, gy = kesit["boyut"]
        return {"sekil": s, "boyut": [gx + 2 * k, gy + 2 * k]}
    if s in ("silindir", "kure"):
        return {"sekil": s, "yaricap": float(kesit["yaricap"]) + k}
    if s == "altigen":
        return {"sekil": s, "apotem": float(kesit["apotem"]) + k,
                "yonelim": kesit.get("yonelim", "y")}
    raise ValueError(_("kalınlıkla büyütülemeyen kesit: %s") % s)


def icinde(kesit, x, y, merkez=(0.0, 0.0), pay=PAY):
    """(x, y) noktasi kesitin icinde mi (sinirda pay kadar tolerans)."""
    px, py = x - merkez[0], y - merkez[1]
    s = kesit.get("sekil")
    if s == "dikdortgen":
        gx, gy = kesit["boyut"]
        return abs(px) <= gx / 2.0 + pay and abs(py) <= gy / 2.0 + pay
    if s in ("silindir", "kure"):
        return math.hypot(px, py) <= float(kesit["yaricap"]) + pay
    if s == "altigen":
        sinir = float(kesit["apotem"]) + pay
        for c, sn in _birim_normaller(kesit.get("yonelim", "y")):
            if px * c + py * sn > sinir:
                return False
        return True
    raise ValueError(_("içerme denetimi yapılamayan kesit: %s") % s)


def icinde_islevi(kesit: dict, merkez=(0.0, 0.0)) -> Callable[[float, float, float], bool]:
    """f(x, y, pay) == icinde(kesit, x, y, merkez, pay); olculer bir kez okunur.
    Kesit sonradan degistirilmemeli (gezinti kesitleri degismez kabul eder)."""
    cx, cy = merkez
    s = kesit.get("sekil")
    if s == "dikdortgen":
        hx, hy = kesit["boyut"][0] / 2.0, kesit["boyut"][1] / 2.0
        return lambda x, y, pay: abs(x - cx) <= hx + pay and abs(y - cy) <= hy + pay
    if s in ("silindir", "kure"):
        r = float(kesit["yaricap"])
        return lambda x, y, pay: math.hypot(x - cx, y - cy) <= r + pay
    if s == "altigen":
        return _altigen_islevi(float(kesit["apotem"]), _birim_normaller(kesit.get("yonelim", "y")),
                               cx, cy)
    return lambda x, y, pay: icinde(kesit, x, y, merkez=merkez, pay=pay)


def _altigen_islevi(a, normaller, cx, cy):
    (c0, s0), (c1, s1), (c2, s2), (c3, s3), (c4, s4), (c5, s5) = normaller

    def f(x, y, pay):
        # icinde() ile ayni: herhangi bir yuzde '>' ise disarida (NaN -> iceride)
        px, py = x - cx, y - cy
        sinir = a + pay
        return not (px * c0 + py * s0 > sinir or px * c1 + py * s1 > sinir
                    or px * c2 + py * s2 > sinir or px * c3 + py * s3 > sinir
                    or px * c4 + py * s4 > sinir or px * c5 + py * s5 > sinir)
    return f


def sinir_noktalari(kesit, merkez=(0.0, 0.0), n_daire=72):
    """Kesit sinirindan noktalar (kose ve yuz ortalari; dairede n_daire nokta)."""
    cx, cy = merkez
    s = kesit.get("sekil")
    if s == "dikdortgen":
        gx, gy = (v / 2.0 for v in kesit["boyut"])
        return [(cx + sx * gx, cy + sy * gy) for sx in (-1, 0, 1) for sy in (-1, 0, 1)
                if (sx, sy) != (0, 0)]
    if s in ("silindir", "kure"):
        r = float(kesit["yaricap"])
        return [(cx + r * c, cy + r * sn) for c, sn in _daire_tablosu(n_daire)]
    if s == "altigen":
        a = float(kesit["apotem"])
        r = 2.0 * a / SQ3
        yon = kesit.get("yonelim", "y") == "y"
        noktalar = []
        for (c, sn), (kc, ks) in zip(_NORMALLER[yon], _KOSELER[yon]):
            noktalar.append((cx + a * c, cy + a * sn))
            noktalar.append((cx + r * kc, cy + r * ks))
        return noktalar
    raise ValueError(_("sınır noktası üretilemeyen kesit: %s") % s)


def kapsar(dis, ic, ic_merkez=(0.0, 0.0), pay=PAY):
    """'ic' kesiti (ic_merkez'de) 'dis' kesitinin (0, 0) icinde mi?"""
    if not all(icinde(dis, x, y, pay=pay) for x, y in sinir_noktalari(ic, ic_merkez)):
        return False
    if ic.get("sekil") in ("silindir", "kure") and dis.get("sekil") in ("dikdortgen", "altigen"):
        # daire: merkezin cokgen kenarlarina uzakligi >= r
        return _daire_cokgende(dis, ic_merkez, float(ic["yaricap"]), pay)
    return True


def _daire_cokgende(dis, merkez, r, pay):
    cx, cy = merkez
    if dis["sekil"] == "dikdortgen":
        gx, gy = (v / 2.0 for v in dis["boyut"])
        return abs(cx) + r <= gx + pay and abs(cy) + r <= gy + pay
    a = float(dis["apotem"])
    for c, sn in _birim_normaller(dis.get("yonelim", "y")):
        if cx * c + cy * sn + r > a + pay:
            return False
    return True


def alan(kesit):
    """Kesit alani [cm^2]: dikdortgen gx*gy, daire pi r^2, altigen 2 sqrt3 a^2."""
    s = kesit.get("sekil")
    if s == "dikdortgen":
        return float(kesit["boyut"][0]) * float(kesit["boyut"][1])
    if s in ("silindir", "kure"):
        return math.pi * float(kesit["yaricap"]) ** 2
    if s == "altigen":
        return 2.0 * SQ3 * float(kesit["apotem"]) ** 2
    raise ValueError(_("alanı hesaplanamayan kesit: %s") % s)


# ----------------------------------------------------------------------------
# yakit pini kesiti (§15.3): bolge "r" = yari olcu
# ----------------------------------------------------------------------------

PIN_SEKILLERI = ("silindir", "kare", "altigen")


def pin_bolge_kesiti(sekil, r, yonelim="y"):
    """Pin bolgesinin dis kesiti: silindir r; kare kenar 2r; altigen apotem r."""
    if sekil == "kare":
        return {"sekil": "dikdortgen", "boyut": [2.0 * r, 2.0 * r]}
    if sekil == "altigen":
        return {"sekil": "altigen", "apotem": float(r), "yonelim": yonelim}
    return {"sekil": "silindir", "yaricap": float(r)}


def pin_bolge_alani(sekil, r):
    """Pin bolgesi dis sinirinin alani: pi r^2, (2r)^2, (sqrt3/2) (2r)^2."""
    if sekil == "kare":
        return (2.0 * r) ** 2
    if sekil == "altigen":
        return SQ3 / 2.0 * (2.0 * r) ** 2
    return math.pi * r * r


# ----------------------------------------------------------------------------
# karisik kafes oturma kosullari (§5 R9)
# ----------------------------------------------------------------------------

def kare_altigene_sigar(kenar, altigen_adim):
    """Eksene hizali kare, adimi P olan altigen elemana sigar mi (iki yonelim)."""
    return kenar <= (SQ3 - 1.0) * altigen_adim + PAY


def altigen_kareye_sigar(duz_olcu, prizma_yonelimi, kare_kenar):
    """Duz-yuzden-duz-yuze olcusu d olan altigen, kenari a olan kareye sigar mi."""
    genislik, yukseklik = kutu({"sekil": "altigen", "apotem": duz_olcu / 2.0,
                                "yonelim": prizma_yonelimi})
    return genislik <= kare_kenar + PAY and yukseklik <= kare_kenar + PAY
