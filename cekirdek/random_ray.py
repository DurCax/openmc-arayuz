# -*- coding: utf-8 -*-
"""
================================================================================
 random_ray.py  --  Random ray (rastgele isin) cozucu ayarlari (v3 Y8)
================================================================================

 OpenMC 0.16 random ray: MG kutuphanesiyle deterministik-benzeri bir
 karakteristik yontemi (MOC) -- isinlar rastgele baslar, kaynak bolgesi
 (FSR) basina duz ya da dogrusal kaynak varsayilir. Model MG olmalidir
 (cekirdek/mg_model.py). settings.random_ray anahtarlari (openmc/settings.py):
   distance_inactive  olu bolge: isinin acisal akisi yakinsayana kadar
                      tally'lenmeyen yol [cm]
   distance_active    tally'lenen yol [cm]
   ray_source         isin baslangici: uzayda ve acida DUZGUN (Box)
   source_shape       flat | linear | linear_xy
   source_region_meshes [(mesh, [domain])] -- kaynak bolgelerini mesh ile alt
                      bolme (0.16'da var; pin hucrede duz kaynak hatasini
                      azaltir)
 settings.particles = cevrim basina isin sayisi.

 VARSAYILANLAR openmc.Model.convert_to_random_ray ile ayni kural: en uzun
 kiris L = max(sinir kutusu kosegeni, 30 cm); olu = L, aktif = 5 L.
 Isin sayisi ve mesh bolmesi bizim olcumumuz (kilavuz 4.12, ders 5.19).
================================================================================
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, replace
from typing import Tuple

from cekirdek.ceviri import _

KAYNAK_SEKILLERI = ("flat", "linear", "linear_xy")
EN_KISA_KIRIS = 30.0          # cm; openmc convert_to_random_ray
AKTIF_KAT = 5.0               # aktif = 5 x olu (openmc convert_to_random_ray)
SONSUZ_YERINE = 1.0           # 2B (z sonsuz) sinir kutusunda +/-1 cm (openmc ile ayni)
# Olcum (Y8, pin hucre CASMO-70, testler/test_y8_kosu.py): hucre basina
# ~0.1 cm kare bolme duz kaynakta MG MC'ye ~100 pcm yaklasir.
HEDEF_BOLME_CM = 0.1
EN_COK_BOLME = 200            # eksen basina; buyuk demette FSR sayisini sinirlar
# Random ray her cevrimde TEK kaynak yinelemesi yapar; yakinsama orani grup ici
# sacilma orani c = Ss(g->g)/St ile belirlenir (sudaki termal grupta ~0.93:
# hata ~ c^n). 300 pasif cevrimde 0.93^300 ~ 1e-9. Olcum (Y8, pin hucre 2 grup,
# duzeltmesiz): 150 pasifte homojen ortam k'si ozdegerden 24 pcm sapti, P0'da
# (kosegen kucuk) sapmadi.
VARSAYILAN_ISIN = 200
VARSAYILAN_CEVRIM = 500
VARSAYILAN_PASIF = 300


@dataclass(frozen=True)
class RRAyar:
    olu_mesafe: float
    aktif_mesafe: float
    isin: int = VARSAYILAN_ISIN
    cevrim: int = VARSAYILAN_CEVRIM
    pasif: int = VARSAYILAN_PASIF
    kaynak_sekli: str = "flat"
    bolme: int = 0                       # eksen basina kare mesh; 0 = yok

    def __post_init__(self) -> None:
        if not (self.olu_mesafe >= 0.0 and self.aktif_mesafe > 0.0):
            raise ValueError(_("random ray: aktif mesafe > 0, ölü mesafe ≥ 0 olmalı"))
        if self.isin < 1 or self.cevrim <= self.pasif or self.pasif < 0:
            raise ValueError(_("random ray: ışın ≥ 1 ve çevrim > pasif ≥ 0 olmalı"))
        if self.kaynak_sekli not in KAYNAK_SEKILLERI:
            raise ValueError(_("random ray: bilinmeyen kaynak şekli %s") % self.kaynak_sekli)
        if not 0 <= self.bolme <= EN_COK_BOLME:
            raise ValueError(_("random ray: bölme 0–%d olmalı") % EN_COK_BOLME)


def _sonlu(v: float, isaret: float) -> float:
    return v if math.isfinite(v) else isaret * SONSUZ_YERINE


def sinir_kutusu(model: "openmc.Model") -> Tuple[Tuple[float, ...], Tuple[float, ...]]:
    bb = model.geometry.bounding_box
    alt = tuple(_sonlu(float(v), -1.0) for v in bb.lower_left)
    ust = tuple(_sonlu(float(v), 1.0) for v in bb.upper_right)
    return alt, ust


def varsayilan(model: "openmc.Model") -> RRAyar:
    """Modelin sinir kutusundan varsayilan ayar (openmc kurali + olcumlu bolme)."""
    alt, ust = sinir_kutusu(model)
    kosegen = math.dist(alt, ust)
    olu = max(kosegen, EN_KISA_KIRIS)
    genislik = max(ust[0] - alt[0], ust[1] - alt[1])
    bolme = min(EN_COK_BOLME, max(1, math.ceil(genislik / HEDEF_BOLME_CM)))
    return RRAyar(olu_mesafe=olu, aktif_mesafe=AKTIF_KAT * olu, bolme=bolme)


def ayar_degistir(a: RRAyar, **alanlar) -> RRAyar:
    return replace(a, **alanlar)


def rr_modeli(mg: "openmc.Model", a: RRAyar) -> "openmc.Model":
    """MG modelin random ray kopyasi (girdi degismez). Yalniz ozdeger."""
    import openmc
    if mg.settings.energy_mode != "multi-group":
        raise ValueError(_("random ray çok gruplu (MG) model ister"))
    if mg.settings.run_mode != "eigenvalue":
        raise ValueError(_("random ray burada yalnız özdeğer hesabı için kurulur"))
    model = copy.deepcopy(mg)
    alt, ust = sinir_kutusu(model)
    rr = {"distance_inactive": float(a.olu_mesafe), "distance_active": float(a.aktif_mesafe),
          "ray_source": openmc.IndependentSource(space=openmc.stats.Box(alt, ust)),
          "source_shape": a.kaynak_sekli}
    if a.bolme > 0:
        mesh = openmc.RegularMesh()
        mesh.lower_left, mesh.upper_right = alt[:2], ust[:2]
        mesh.dimension = (a.bolme, a.bolme)
        rr["source_region_meshes"] = [(mesh, [model.geometry.root_universe])]
    s = model.settings
    s.random_ray = rr
    s.particles, s.batches, s.inactive = int(a.isin), int(a.cevrim), int(a.pasif)
    s.source = []
    s._entropy_mesh = None     # noqa: SLF001 -- setter None kabul etmez; RR entropiyi FSR'lerden hesaplar; kullanici mesh'i reddedilir
    return model
