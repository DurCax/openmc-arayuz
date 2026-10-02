# -*- coding: utf-8 -*-
"""
================================================================================
 mgxs_k.py  --  Grup sabitlerinden SONSUZ ORTAM k (v3 Y8; saf numpy)
================================================================================

 Homojen sonsuz ortamda (sizinti yok) cok gruplu denge denklemi:

     St_g phi_g - sum_g' S(g'->g) phi_g' = chi_g / k * sum_g' nuSf_g' phi_g'

 Matris bicimi  M phi = (1/k) chi nuSf^T phi,  M = diag(St) - S^T, S[g, g'] =
 g -> g' (nu-)sacilma matrisi (gelen satir, giden sutun; OpenMC
 ScatterMatrixXS.get_xs duzeni). k = M^-1 chi nuSf^T'nin en buyuk ozdegeri;
 F = chi nuSf^T birinci mertebeden oldugu icin k = nuSf^T M^-1 chi (tek sayi).

 GRUP SIRASI: g = 1 en YUKSEK enerji (OpenMC mgxs get_xs duzeni). Tally
 ortalamalari (EnergyFilter) artan enerji sirasindadir -- cevirmek
 cagiranin isidir (cekirdek/mgxs_uret.py).

 TUTARLILIK: St ve S ayni tanimdan gelmelidir. P0 tasima duzeltmesinde
 (out-scatter yaklasimi) St yerine nu-transport ve kosegeni Ss1 kadar azaltilmis
 nu-sacilma matrisi kullanilir: kaldirma St - S(g->g) DEGISMEZ, dolayisiyla
 sonsuz ortam k'si duzeltmeden bagimsizdir (duzeltme yalniz sizintiyi --
 D = 1/(3 Str) -- etkiler). nu-sacilma (n,xn) cogalmasini icerir; k_oran
 (= sum nuF / sum A) icermez, fark (n,xn) net uretimidir.

 BELIRSIZLIK: birinci derece, parametreler BAGIMSIZ varsayilir (ayni
 gecmislerden gelen tally'ler gercekte iliskilidir; bu bir ust sinir degil,
 yaklasik bir buyukluk gostergesidir). Etiket arayuzde ve kilavuzda yazar.
================================================================================
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import NamedTuple, Optional, Sequence, Tuple

import numpy as np

from cekirdek.ceviri import _

CHI_TOLERANSI = 1e-3        # chi toplami 1'den bu kadar sapabilir (tally normalizasyonu)
_TUREV_ADIMI = 1e-6         # bagil sonlu fark adimi (birinci derece yayilim)

Dizi = Tuple[float, ...]


class Deger(NamedTuple):
    """Ortalama ve 1 sigma standart sapma."""
    ort: float
    sapma: float


def _dizi(ad: str, deger: Sequence[float]) -> Dizi:
    try:
        d = tuple(float(x) for x in deger)
    except (TypeError, ValueError) as e:
        raise ValueError(_("%s sayı dizisi olmalı") % ad) from e
    if any(not math.isfinite(x) for x in d):
        raise ValueError(_("%s sonlu olmalı") % ad)
    return d


@dataclass(frozen=True)
class GrupSabitleri:
    """Tek bolgenin G grup sabitleri [1/cm]; g = 1 en yuksek enerji.

    toplam      : St (ya da P0 duzeltmesinde nu-transport Str)
    sacilma     : G x G, [gelen][giden] nu-sacilma (toplam ile ayni duzeltme)
    absorpsiyon : Sa (k_oran ve tablo icin; ozdeger kullanmaz)
    nu_fisyon   : nuSf
    chi         : fisyon notron tayfi (toplam 1; fisyonsuz bolgede 0)
    """
    toplam: Dizi
    absorpsiyon: Dizi
    nu_fisyon: Dizi
    chi: Dizi
    sacilma: Tuple[Dizi, ...]

    def __post_init__(self) -> None:
        g = len(_dizi("toplam", self.toplam))
        for ad in ("toplam", "absorpsiyon", "nu_fisyon", "chi"):
            d = _dizi(ad, getattr(self, ad))
            if len(d) != g:
                raise ValueError(_("%s %d grup olmalı (toplam ile aynı)") % (ad, g))
            object.__setattr__(self, ad, d)
        matris = tuple(_dizi("sacilma", satir) for satir in self.sacilma)
        if len(matris) != g or any(len(satir) != g for satir in matris):
            raise ValueError(_("saçılma matrisi %d x %d olmalı") % (g, g))
        object.__setattr__(self, "sacilma", matris)
        if any(x < 0.0 for x in self.toplam + self.nu_fisyon + self.absorpsiyon):
            raise ValueError(_("tesir kesitleri negatif olamaz"))
        if any(x > 0.0 for x in self.nu_fisyon) and abs(sum(self.chi) - 1.0) > CHI_TOLERANSI:
            raise ValueError(_("fisyonlu bölgede χ toplamı 1 olmalı (%.4f)") % sum(self.chi))

    @property
    def grup_sayisi(self) -> int:
        return len(self.toplam)


def _k(toplam: np.ndarray, sacilma: np.ndarray, nu_fisyon: np.ndarray,
       chi: np.ndarray) -> float:
    m = np.diag(toplam) - sacilma.T
    try:
        phi = np.linalg.solve(m, chi)          # M phi = chi (birim fisyon kaynagi)
    except np.linalg.LinAlgError as e:
        raise ValueError(_("kaldırma matrisi tekil (St - S)")) from e
    return float(nu_fisyon @ phi)


def k_ozdeger(s: GrupSabitleri) -> float:
    """Sonsuz homojen ortamin k'si (G x G ozdeger; yukari sacilma dahil)."""
    if not any(x > 0.0 for x in s.nu_fisyon):
        raise ValueError(_("bölgede fisyon yok: k∞ tanımsız"))
    return _k(np.array(s.toplam), np.array(s.sacilma), np.array(s.nu_fisyon),
              np.array(s.chi))


@dataclass(frozen=True)
class GrupSapmalari:
    """GrupSabitleri ile ayni alanlarin 1 sigma sapmalari (dogrulama yok)."""
    toplam: Dizi
    absorpsiyon: Dizi
    nu_fisyon: Dizi
    chi: Dizi
    sacilma: Tuple[Dizi, ...]
    sacilma_nusuz: Optional[Tuple[Dizi, ...]] = None


def kaldirma_k(sa: np.ndarray, nusf: np.ndarray, chi: np.ndarray, nus: np.ndarray,
                s: np.ndarray) -> float:
    """KALDIRMA bicimi: M_gg = Sa_g + sum_{g'!=g} S(g->g') - (nuS_gg - S_gg),
    M_gg' = -nuS(g'->g). Tutarli sabitlerde (St = Sa + sum_g' S) k_ozdeger ile
    ayni sayi; her terim dusuk gurultulu tally'den gelir (belirsizlik icin)."""
    disari = s.sum(axis=1) - np.diag(s)
    m = -nus.T.copy()
    np.fill_diagonal(m, sa + disari - (np.diag(nus) - np.diag(s)))
    return float(nusf @ np.linalg.solve(m, chi))


def k_ozdeger_belirsiz(s: GrupSabitleri, sapma: GrupSapmalari,
                       sacilma_nusuz: Optional[Sequence[Sequence[float]]] = None) -> Deger:
    """k_ozdeger + birinci derece belirsizlik.

    Deger St bicimindendir (random ray ile ayni denklem). Sapma KALDIRMA
    biciminden yayilir: St - S(g->g) iki buyuk ve iliskili sayinin farkidir;
    ogeleri bagimsiz saymak sapmayi kat kat sisirirdi. Yayilan: Sa, nuSf, chi
    ve kosegen DISI sacilma; kosegendeki (n,xn) cogalma farki (nuS_gg - S_gg)
    kucuk oldugu icin sapmasiz alinir. Bagimsizlik varsayimi -- yaklasik."""
    k0 = k_ozdeger(s)
    nus = np.array(s.sacilma, dtype=float)
    snusuz = nus if sacilma_nusuz is None else np.array(sacilma_nusuz, dtype=float)
    parametreler = {"sa": np.array(s.absorpsiyon), "nusf": np.array(s.nu_fisyon),
                    "chi": np.array(s.chi), "nus": nus, "s": snusuz}
    sapmalar = {"sa": np.array(sapma.absorpsiyon), "nusf": np.array(sapma.nu_fisyon),
                "chi": np.array(sapma.chi), "nus": np.array(sapma.sacilma),
                "s": np.array(sapma.sacilma if sapma.sacilma_nusuz is None
                              else sapma.sacilma_nusuz)}
    if sacilma_nusuz is None:
        sapmalar["s"] = np.zeros_like(snusuz)       # ayni matris iki kez sayilmasin
    taban = kaldirma_k(**parametreler)
    varyans = 0.0
    for ad, deger in parametreler.items():
        for ix in np.ndindex(deger.shape):
            if sapmalar[ad][ix] <= 0.0 or (deger.ndim == 2 and ix[0] == ix[1]):
                continue
            adim = _TUREV_ADIMI * max(abs(deger[ix]), 1e-12)
            kayik = {a: d.copy() for a, d in parametreler.items()}
            kayik[ad][ix] += adim
            varyans += ((kaldirma_k(**kayik) - taban) / adim * sapmalar[ad][ix]) ** 2
    return Deger(k0, math.sqrt(varyans))
def k_oran(nu_fisyon_hizlari: Sequence[Tuple[float, float]],
           absorpsiyon_hizlari: Sequence[Tuple[float, float]]) -> Optional[Deger]:
    """k = sum nuF / sum A (reaksiyon hizlari (ort, sapma)). (n,xn) icermez.
    Sapma birinci derece, pay ve payda bagimsiz varsayilir. Payda 0 -> None."""
    f = sum(o for o, _s in nu_fisyon_hizlari)
    a = sum(o for o, _s in absorpsiyon_hizlari)
    if a <= 0.0:
        return None
    sf = math.sqrt(sum(s_ ** 2 for _o, s_ in nu_fisyon_hizlari))
    sa = math.sqrt(sum(s_ ** 2 for _o, s_ in absorpsiyon_hizlari))
    k = f / a
    bagil = math.hypot(sf / f if f else 0.0, sa / a)
    return Deger(k, abs(k) * bagil)
