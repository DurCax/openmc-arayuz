# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_kosu.py  --  Tukenme operatoru, entegrator ve integrate (v3 Y4)
================================================================================

 tukenme.calistir modeli hazirlar ve dizini temizler; bu modul openmc.deplete
 nesnelerini kurar ve kosar:
   operator    CoupledOperator (her adimda transport) ya da hizli kipte
               IndependentOperator (tukenme_hizli)
   entegrator  tukenme_ayar.ENTEGRATORLER; zaman plani yanma + sogutma
   surdurme    prev_results + kalan adimlar (tukenme_surdur)
   arama       add_keff_search_control (tukenme_arama)

 write_rates: reaksiyon hizlari h5'e yazilir (surdurmenin dogru baslamasi
 icin, bkz. tukenme_surdur). Cubuk cubuk yanmada malzeme sayisi buyuk
 oldugundan yazilmaz (dosya boyutu); o durumda surdurme ilk adimin BOS
 transport'unu yeniden kosar.
================================================================================
"""

from __future__ import annotations

from cekirdek import tukenme_ayar


def operator_kur(model, zincir: dict, spec: dict, dizin: str, onceki=None):
    """openmc.deplete operatoru (hizli kip ya da transport'lu)."""
    import openmc.deplete as d
    t = spec["tukenme"]
    prev = onceki.sonuc if onceki is not None else None
    if tukenme_ayar.hizli_kip(t):
        from cekirdek import tukenme_hizli
        return tukenme_hizli.operator_kur(model, zincir, dizin, prev)
    # Ornekler hazirla()'da kesin hacimle ayrildi; OpenMC'nin esit bolmesi
    # (diff_burnable_mats) bu yuzden KAPALI.
    return d.CoupledOperator(
        model, zincir["yol"],
        prev_results=prev,
        diff_burnable_mats=False,
        normalization_mode="fission-q",
        fission_yield_mode="constant",
        fission_yield_opts={"energy": zincir["verim_enerjisi"]},
    )


def entegrator_kur(op, t: dict, onceki=None):
    """Secili entegrator; surdurmede yalniz kalan adimlar."""
    import openmc.deplete as d
    e = tukenme_ayar.entegrator(t)
    adimlar, guc = tukenme_ayar.zaman_plani(t)
    if onceki is not None:
        adimlar, guc = adimlar[onceki.tamam:], guc[onceki.tamam:]
    kw = {"power_density": guc}
    if e.si:
        kw["n_steps"] = tukenme_ayar.si_ic_adim(t)
    integ = getattr(d, e.sinif)(op, adimlar, **kw)
    if onceki is not None and not onceki.hizli:
        from cekirdek import tukenme_surdur
        tukenme_surdur.taze_bos(integ)
    return integ


def kos(model, bilgi: dict, spec: dict, dizin: str, onceki=None) -> None:
    """Operator + entegrator (+ arama) kurar ve integrate eder (cwd = dizin)."""
    from cekirdek import tukenme_arama
    t = spec["tukenme"]
    islev = tukenme_arama.hazirla(model, bilgi.get("nesneler") or {}, spec)
    op = operator_kur(model, bilgi["zincir"], spec, dizin, onceki)
    integ = entegrator_kur(op, t, onceki)
    if islev is not None:
        tukenme_arama.ekle(integ, islev, spec)
    integ.integrate(write_rates=not t.get("malzemeleri_ayir"))
