# -*- coding: utf-8 -*-
"""
 kamera.py  --  3B golgeli gorunumun kamerasi (saf; Qt'siz)

 Kamera modelin merkezine (cs.KESIT_MERKEZI) bakar ve onun cevresinde azimut
 (x ekseninden, z etrafinda) ve yukselti (xy duzleminden) acilariyla doner.
 Uzaklik, modelin sinir kuresi (yari kosegen R) gorus acisina sigacak bicimde
 d = kat * R / sin(gorus / 2) secilir; kat = 1 kureyi tam sigdirir. Yukari
 vektoru bakisa diktir (tepeden bakista da tanimli).
 2B modelde (yukseklik yok) z olcusu en buyuk yatay olcu alinir (kesit_genisligi
 ile ayni) -- model eksenel sonsuz prizmadir, goruntu bunu gosterir (kilavuz).
"""

import math
from dataclasses import dataclass

from cekirdek import cizim_sureci as cs

_YUKSELTI_SINIRI = 89.0       # derece: 90'da yukari vektoru bakisa paralel olur


@dataclass(frozen=True)
class Kamera:
    azimut: float = 45.0          # derece
    yukselti: float = 30.0        # derece
    uzaklik_kati: float = 1.1
    gorus: float = 40.0           # yatay gorus acisi, derece


def yari_kosegen(sinir_kutu, yukseklik) -> float:
    gx, gy = (float(v) for v in sinir_kutu)
    gz = float(yukseklik) if yukseklik else max(gx, gy)
    return 0.5 * math.sqrt(gx * gx + gy * gy + gz * gz)


def vektorler(k: Kamera, sinir_kutu, yukseklik) -> dict:
    """{"kamera", "bakis", "yukari", "gorus"} (isci 'isin' istegi alanlari)."""
    yukselti = max(-_YUKSELTI_SINIRI, min(_YUKSELTI_SINIRI, float(k.yukselti)))
    az, el = math.radians(k.azimut), math.radians(yukselti)
    d = k.uzaklik_kati * yari_kosegen(sinir_kutu, yukseklik) / math.sin(
        math.radians(k.gorus) / 2.0)
    yon = (math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))
    bakis = [float(v) for v in cs.KESIT_MERKEZI]
    kamera = [b + d * y for b, y in zip(bakis, yon)]
    # yukari = yonun yukseltiye gore turevi: bakisa her zaman dik (tepeden bakista da)
    yukari = [-math.sin(el) * math.cos(az), -math.sin(el) * math.sin(az), math.cos(el)]
    return {"kamera": kamera, "bakis": bakis, "yukari": yukari, "gorus": float(k.gorus)}


def istek(k: Kamera, sinir_kutu, yukseklik, piksel, renk: str, gizli) -> dict:
    """Isci 'isin' isteginin govdesi (tur/no/spec haric)."""
    return dict(vektorler(k, sinir_kutu, yukseklik), piksel=[int(piksel[0]), int(piksel[1])],
                renk=renk, gizli=[int(g) for g in gizli])
