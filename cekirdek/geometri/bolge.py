# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/bolge.py  --  Gezinti bolgeleri: nokta icerme + analitik alan (G-2)
================================================================================

 Agac gezintisi (geometri/gez.py) her dugume, onu dolduran BOLGEYI verir:
 dugumun yerel cercevesinde bir nokta icerme sinamasi ve (biliniyorsa)
 analitik kesit alani. Hacim (geometri/hacim.py), kesik konum/cubuk tespiti
 ve dogrulama (dogrula/agac.py) ayni bolgeyi kullanir.

   Bolge(icinde, alan, kesit=None, hacim=None)
     icinde(x, y, pay) -> bool   yerel cercevede
     alan                        cm^2 ya da None (bilinmiyor: kirpilmis vb.)
     kesit                       bolge tek bir kesitse (0, 0) merkezli kesit
     hacim                       kure kokunde bolgenin 3B hacmi (alan yerine)

 Donusum (R6): cocuk yerel noktasi p, ust cercevede R(teta) p + t'dir
 (donme = +teta icerigi saat yonunun tersine dondurur). Bu yuzden cocugun
 bolgesi ustunkunun geri cekilmesidir: icinde_c(p) = icinde_u(R p + t).
 Yalniz saf geometri; openmc gerektirmez.
================================================================================
"""

import math

from cekirdek.geometri import kesit as _k

# Alan karsilastirma payi (goreli): sifir alanli bolge "yok" sayilir.
ALAN_PAYI = 1.0e-9
# Sinira oturan yuzeyler icin nokta payi (cm)
NOKTA_PAYI = 1.0e-9
# Eleman sinir noktalari biraz iceriden alinir (kesik.py ile ayni pay)
ICERI_PAY = 1.0e-7


class Bolge(object):
    """Nokta icerme + alan. Degismez (alanlar yeniden atanmaz)."""

    __slots__ = ("_icinde", "alan", "kesit", "hacim")

    def __init__(self, icinde, alan=None, kesit=None, hacim=None):
        self._icinde = icinde
        self.alan = alan
        self.kesit = kesit
        self.hacim = hacim

    def icinde(self, x, y, pay=NOKTA_PAYI):
        return self._icinde(x, y, pay)

    def hepsi_icinde(self, noktalar, pay=NOKTA_PAYI):
        return all(self._icinde(x, y, pay) for x, y in noktalar)


def kesit_bolgesi(kes, merkez=(0.0, 0.0)):
    """Tek kesit (merkez'de) -> Bolge."""
    cx, cy = merkez
    alan = _k.alan(kes) if kes.get("sekil") in ("dikdortgen", "silindir", "altigen") else None
    return Bolge(lambda x, y, pay: _k.icinde(kes, x, y, merkez=(cx, cy), pay=pay), alan,
                 kesit=kes if merkez == (0.0, 0.0) else None)


def kure_bolgesi(r_dis, r_ic=0.0):
    """Kure kokunun kabugu (2B kesitte daire halkasi; hacim 3B)."""
    hacim = 4.0 / 3.0 * math.pi * (r_dis ** 3 - r_ic ** 3)
    return Bolge(lambda x, y, pay: r_ic - pay <= math.hypot(x, y) <= r_dis + pay,
                 None, hacim=hacim)


def fark(dis, ic):
    """dis \\ ic (halka bolgesi). Alan: ikisi de biliniyorsa fark."""
    alan = None
    if dis.alan is not None and ic.alan is not None:
        alan = max(dis.alan - ic.alan, 0.0)
    return Bolge(lambda x, y, pay: dis.icinde(x, y, pay) and not ic.icinde(x, y, -pay), alan)


def delikli(bolge, delikler):
    """bolge \\ (delik1 U delik2 ...); delikler: [Bolge]. Alan: delik alanlari cikar."""
    if not delikler:
        return bolge
    alan = bolge.alan
    for d in delikler:
        alan = None if (alan is None or d.alan is None) else alan - d.alan
    if alan is not None:
        alan = max(alan, 0.0)
    return Bolge(lambda x, y, pay: bolge.icinde(x, y, pay)
                 and not any(d.icinde(x, y, -pay) for d in delikler), alan)


def kesisim(a, b):
    """a n b; alan bilinmez (kirpilmis konum)."""
    return Bolge(lambda x, y, pay: a.icinde(x, y, pay) and b.icinde(x, y, pay), None)


def otele(bolge, dx, dy):
    """Cercevesi (dx, dy) kaydirilmis bolge: yeni(p) = eski(p + d)."""
    return Bolge(lambda x, y, pay: bolge.icinde(x + dx, y + dy, pay), bolge.alan,
                 hacim=bolge.hacim)


def geri_cek(bolge, donme=0.0, oteleme=(0.0, 0.0)):
    """Donusumlu cocugun cercevesindeki bolge: yeni(p) = eski(R(donme) p + t)."""
    t = math.radians(float(donme or 0.0))
    c, s = math.cos(t), math.sin(t)
    tx, ty = (float(v) for v in (oteleme or (0.0, 0.0)))
    if not t and not tx and not ty:
        return bolge
    return Bolge(lambda x, y, pay: bolge.icinde(c * x - s * y + tx, s * x + c * y + ty, pay),
                 bolge.alan, hacim=bolge.hacim)


def sinir_noktalari_iceri(kes, merkez=(0.0, 0.0), pay=ICERI_PAY):
    """Kesit sinirindan biraz iceride noktalar + merkez (kirpma sinamasi)."""
    s = kes.get("sekil")
    if s == "dikdortgen":
        k = {"sekil": s, "boyut": [max(float(v) - 2 * pay, 0.0) for v in kes["boyut"]]}
    elif s in ("silindir", "kure"):
        k = {"sekil": s, "yaricap": max(float(kes["yaricap"]) - pay, 0.0)}
    else:
        k = dict(kes, apotem=max(float(kes["apotem"]) - pay, 0.0))
    return _k.sinir_noktalari(k, merkez) + [tuple(merkez)]


def durum(bolge, noktalar):
    """'tam' (hepsi icinde), 'gizli' (hicbiri), 'kesik' (arada) -- kesik.py ile ayni."""
    icerde = [bolge.icinde(x, y, 0.0) for x, y in noktalar]
    if all(icerde):
        return "tam"
    if not any(icerde):
        return "gizli"
    return "kesik"


def sigar(bolge, kes, merkez=(0.0, 0.0)):
    """Kesit (merkez'de) bolgenin icinde mi (sinir noktalari, NOKTA_PAYI)."""
    return bolge.hepsi_icinde(_k.sinir_noktalari(kes, merkez))


def sifir_mi(alan, olcek=1.0):
    """Alan fiilen sifir mi (goreli pay)."""
    return alan is not None and alan <= ALAN_PAYI * max(1.0, abs(olcek))
