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
        a = float(kesit["apotem"])
        for aci in altigen_normal_acilari(kesit.get("yonelim", "y")):
            t = math.radians(aci)
            if px * math.cos(t) + py * math.sin(t) > a + pay:
                return False
        return True
    raise ValueError(_("içerme denetimi yapılamayan kesit: %s") % s)


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
        return [(cx + r * math.cos(2 * math.pi * i / n_daire),
                 cy + r * math.sin(2 * math.pi * i / n_daire)) for i in range(n_daire)]
    if s == "altigen":
        a = float(kesit["apotem"])
        r = 2.0 * a / SQ3
        noktalar = []
        for aci in altigen_normal_acilari(kesit.get("yonelim", "y")):
            t = math.radians(aci)
            noktalar.append((cx + a * math.cos(t), cy + a * math.sin(t)))
            k = math.radians(aci + 30.0)
            noktalar.append((cx + r * math.cos(k), cy + r * math.sin(k)))
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
    for aci in altigen_normal_acilari(dis.get("yonelim", "y")):
        t = math.radians(aci)
        if cx * math.cos(t) + cy * math.sin(t) + r > a + pay:
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
