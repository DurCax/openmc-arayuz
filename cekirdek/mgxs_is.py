# -*- coding: utf-8 -*-
"""
================================================================================
 mgxs_is.py  --  Grup sabiti is akisi: CE -> mgxs.h5 -> MG MC -> random ray (Y8)
================================================================================

 Qt'den bagimsiz; isler cekirdek/kuyruk.py (Y10) ile kosar. Uc koşu turu:

   ce_isi  : spec'in MGXS acik KOPYASI (girdi degismez) -- kuyruk modeli
             kurucu.kur ile yazar; sonuc kancasi mgxs_uret.isle (mgxs.h5,
             mgxs.csv, mgxs_ozet.json CE dizinine).
   mg_isi  : ayni geometri, makroskopik MG malzemeler (mg_model) -- model.xml
             burada (cagiran iplikte) yazilir, is spec'siz kuyruga girer.
   rr_isi  : MG model + settings.random_ray (random_ray).

 karsilastirma(): CE / MG / RR icin k +- sigma, CE'ye fark [pcm] ve sure.
   dk [pcm] = (k - k_CE) x 1e5; sigma_dk = hypot(sigma, sigma_CE) x 1e5
   (koşular bagimsiz). RR satiri ayrica MG'ye fark (yontem farki; ayni
   mgxs.h5) verir.
================================================================================
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from cekirdek import kosucu, kuyruk, mg_model, mgxs_uret, random_ray
from cekirdek.ceviri import _, N_

PCM = 1.0e5
TURLER = {"ce": N_("Sürekli enerji (CE) MC"), "mg": N_("Çok gruplu (MG) MC"),
          "rr": N_("Random ray (MG)")}


def ce_isi(spec: Mapping, a: mgxs_uret.MgxsAyar, dizin: str, is_parcacigi: int,
           ad: Optional[str] = None) -> kuyruk.KosuIsi:
    """CE + MGXS tally koşusu. Bitince sonuc: {"keff", "mgxs": MgxsSonuc}."""
    if not a.var:
        a = mgxs_uret.MgxsAyar(True, a.bolge, a.grup_yapisi, a.turler, a.duzeltme)
    kopya = mgxs_uret.ile(spec, a)

    def _kanca(sp: str, is_: kuyruk.KosuIsi) -> dict:
        s = mgxs_uret.isle(sp, is_.spec, is_.dizin)
        return {"keff": None if s.k_ce is None else (s.k_ce.ort, s.k_ce.sapma), "mgxs": s}

    return kuyruk.KosuIsi(ad=ad or _("MGXS üretimi (CE)"), dizin=dizin, spec=kopya,
                          is_parcacigi=int(is_parcacigi), sonuc_kancasi=_kanca,
                          etiket={"y8": "ce"})


def _k_kancasi(sp: str, _is: kuyruk.KosuIsi) -> dict:
    import openmc
    with openmc.StatePoint(sp, autolink=False) as f:
        k = f.keff
    return {"keff": None if k is None else (float(k.n), float(k.s))}


def _hazir_dizin(dizin: str) -> str:
    return kosucu.dizin_hazirla(dizin, temizle=True)


def _mg_kur(ce_spec: Mapping, ce_dizin: str) -> "openmc.Model":
    ozet = mgxs_uret.ozet_oku(ce_dizin)
    return mg_model.mg_modeli(ce_spec, ozet, os.path.join(ce_dizin, mgxs_uret.H5_ADI))


def mg_isi(ce_spec: Mapping, ce_dizin: str, dizin: str, is_parcacigi: int) -> kuyruk.KosuIsi:
    """Ayni geometrinin MG MC koşusu (model.xml simdi yazilir)."""
    with kuyruk._HAZIRLIK_KILIDI:          # noqa: SLF001 (openmc API is parcacigi guvenli degil)
        model = _mg_kur(ce_spec, ce_dizin)
        model.export_to_model_xml(os.path.join(_hazir_dizin(dizin), "model.xml"))
    return kuyruk.KosuIsi(ad=_("MG MC"), dizin=dizin, spec=None,
                          is_parcacigi=int(is_parcacigi), sonuc_kancasi=_k_kancasi,
                          etiket={"y8": "mg"})


def rr_varsayilan(ce_spec: Mapping, ce_dizin: str) -> random_ray.RRAyar:
    with kuyruk._HAZIRLIK_KILIDI:          # noqa: SLF001
        return random_ray.varsayilan(_mg_kur(ce_spec, ce_dizin))


def rr_isi(ce_spec: Mapping, ce_dizin: str, dizin: str, is_parcacigi: int,
           a: Optional[random_ray.RRAyar] = None) -> kuyruk.KosuIsi:
    """Random ray koşusu (ayni mgxs.h5). a None ise varsayilan ayar."""
    with kuyruk._HAZIRLIK_KILIDI:          # noqa: SLF001
        mg = _mg_kur(ce_spec, ce_dizin)
        model = random_ray.rr_modeli(mg, a or random_ray.varsayilan(mg))
        model.export_to_model_xml(os.path.join(_hazir_dizin(dizin), "model.xml"))
    return kuyruk.KosuIsi(ad=_("Random ray"), dizin=dizin, spec=None,
                          is_parcacigi=int(is_parcacigi), sonuc_kancasi=_k_kancasi,
                          etiket={"y8": "rr"})


# ----------------------------------------------------------------------------
# karsilastirma
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class Karsilastirma:
    tur: str                      # ce | mg | rr
    k: float
    sapma: float
    fark_pcm: Optional[float]     # CE'ye
    fark_sapma_pcm: Optional[float]
    mg_fark_pcm: Optional[float]  # yalniz rr: MG'ye
    sure_s: Optional[float]


def _sure(d: Any) -> Optional[float]:
    if getattr(d, "baslangic", None) is None or getattr(d, "bitis", None) is None:
        return None
    return float(d.bitis - d.baslangic)


def karsilastirma(durumlar: Sequence[Any]) -> list:
    """IsDurumu listesi (etiket y8: ce|mg|rr; son tamamlanan kazanir) ->
    Karsilastirma satirlari (ce, mg, rr sirasiyla, olanlar)."""
    son = {}
    for d in durumlar:
        tur = (getattr(d, "etiket", None) or {}).get("y8")
        if tur in TURLER and getattr(d, "k", None) is not None \
                and getattr(d, "asama", None) == kuyruk.Asama.BITTI:
            son[tur] = d
    ce = son.get("ce")
    satirlar = []
    for tur in ("ce", "mg", "rr"):
        d = son.get(tur)
        if d is None:
            continue
        k, s = d.k
        fark = fark_s = mg_fark = None
        if ce is not None and tur != "ce":
            fark = (k - ce.k[0]) * PCM
            fark_s = math.hypot(s, ce.k[1]) * PCM
        if tur == "rr" and "mg" in son:
            mg_fark = (k - son["mg"].k[0]) * PCM
        satirlar.append(Karsilastirma(tur, k, s, fark, fark_s, mg_fark, _sure(d)))
    return satirlar
