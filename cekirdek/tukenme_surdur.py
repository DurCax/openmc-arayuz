# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_surdur.py  --  Tukenmeyi kaldigi yerden surdurme (v3 Y4)
================================================================================

 OpenMC 0.16: CoupledOperator(prev_results=Results) ile entegrator son kayitli
 adimin BASINDAN devam eder (abc.Integrator._get_start_data: zaman
 prev[-1].time[0], indis len(prev) - 1). Yani tamamlanmis adim sayisi
 len(prev) - 1'dir; yarida kalan adim bastan kosulur, biten kosuya yeni
 adimlar eklenebilir.

 DENETIM (sessizce yanlis devam etmesin)
   - dizinde bu arayuzun spec kaydi olmali ve fizik ayni olmali (adim
     listeleri ve surdur haric: tukenme_kayit._fizik_kismi);
   - h5'teki adimlar (saniye) yeni planin ONEKI olmali (bagil 1e-9), guc
     olan/olmayan adimlar ayni yerde;
   - plan zaten bitmisse kosu yok (hata metni).

 OPENMC TUZAGI: yeniden baslatmada ilk adim kayitli reaksiyon hizlarini
 kullanir (_get_bos_data_from_restart). h5 hizlari icermiyorsa
 (integrate(write_rates=False), OpenMC varsayilani) hizlar SIFIR okunur ve
 o adim sessizce yalniz bozunma olurdu. Bu durumda ilk adimin BOS
 transport'u yeniden kosulur (taze_bos). LE/QI onceki adimin hizlarini da
 ister: hizsiz dosyada LE/QI ile surdurme reddedilir.
================================================================================
"""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass

import numpy as np

from cekirdek.ceviri import _

_BAGIL_TOLERANS = 1e-9
_SANIYE = {"s": 1.0, "min": 60.0, "h": 3600.0, "d": 86400.0, "a": 365.25 * 86400.0}
_OYKU_ISTEYEN = {"leqi", "si_leqi"}       # onceki adimin hizlarini kullanir


@dataclass(frozen=True)
class Onceki:
    """Surdurulecek onceki sonuc: Results, tamamlanmis adim, hiz kaydi var mi."""
    sonuc: object
    tamam: int
    hizli: bool


def plan_saniye(adimlar: list, guc_yogunlugu: float) -> list:
    """[(deger, birim)] -> [saniye]; MWd/kg guc yogunluguyla zamana cevrilir."""
    sn = []
    for deger, birim in adimlar:
        if birim == "MWd/kg":
            sn.append(float(deger) * 1000.0 / float(guc_yogunlugu) * _SANIYE["d"])
        else:
            sn.append(float(deger) * _SANIYE[birim])
    return sn


def _fizik(spec: dict) -> dict:
    from cekirdek import tukenme_kayit
    f = copy.deepcopy(tukenme_kayit._fizik_kismi(spec))
    for k in ("adimlar", "sogutma"):
        f.get("tukenme", {}).pop(k, None)
    return f


def _hiz_kaydi_var(h5: str) -> bool:
    import h5py
    with h5py.File(h5, "r") as f:
        return "reaction rates" in f


def onceki_durum(spec: dict, dizin: str) -> Onceki | None:
    """Surdurulecek onceki sonuc; dizinde sonuc yoksa None. Uyumsuzsa ValueError."""
    import openmc.deplete as d
    from cekirdek import tukenme_ayar, tukenme_kayit
    from cekirdek.tukenme_temizlik import SONUC_DOSYASI
    h5 = os.path.join(dizin, SONUC_DOSYASI)
    if not os.path.isfile(h5):
        return None
    kayit = tukenme_kayit._kayit_oku(dizin)
    if kayit is None or _fizik(kayit) != _fizik(spec):
        raise ValueError(_("sürdürülemez: önceki koşunun fiziği farklı ya da kaydı yok "
                           "(malzeme, geometri, güç aynı olmalı). Sürdürmeyi kapatıp "
                           "baştan koşun."))
    r = d.Results(h5)
    t = spec["tukenme"]
    adimlar, guc = tukenme_ayar.zaman_plani(t)
    plan = plan_saniye(adimlar, t["guc_yogunlugu"])
    eski = np.diff(r.get_times(time_units="s"))
    tamam = len(r) - 1
    _onek_denetle(eski, plan, r.get_source_rates()[:tamam], guc)
    if tamam >= len(plan):
        raise ValueError(_("sürdürülecek adım yok: önceki koşu %d adımın hepsini bitirmiş. "
                           "Yeni adım ekleyin.") % tamam)
    hizli = _hiz_kaydi_var(h5)
    if not hizli and tukenme_ayar.entegrator(t).kod in _OYKU_ISTEYEN:
        raise ValueError(_("LE/QI ile sürdürme bu dosyada yapılamaz: önceki adımın "
                           "reaksiyon hızları kayıtlı değil. Başka entegratör seçin."))
    return Onceki(sonuc=r, tamam=tamam, hizli=hizli)


def _onek_denetle(eski, plan: list, eski_guc, guc: list) -> None:
    n = len(eski)
    if n > len(plan) or not np.allclose(eski, plan[:n], rtol=_BAGIL_TOLERANS, atol=0.0):
        raise ValueError(_("sürdürülemez: önceki koşunun %d adımı yeni adım listesinin "
                           "başıyla aynı değil") % n)
    if [g > 0 for g in eski_guc] != [g > 0 for g in guc[:n]]:
        raise ValueError(_("sürdürülemez: güçlü/soğuma adımlarının sırası önceki "
                           "koşuyla aynı değil"))


def taze_bos(integ) -> None:
    """Yeniden baslatmanin ilk adiminda kayitli (sifir) hiz yerine BOS transport
    kosulur: _get_bos_data_from_restart -> _get_bos_data_from_operator(0, ...).
    OpenMC 0.16 ic yontemleri (abc.Integrator); surum degisirse test_y4_surdur
    yakalar."""
    asil = integ._get_bos_data_from_operator

    def yeniden(source_rate, bos_conc):
        return asil(0, source_rate, bos_conc)
    integ._get_bos_data_from_restart = yeniden
