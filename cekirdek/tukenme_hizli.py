# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_hizli.py  --  Transport'suz hizli tukenme: MicroXS + IndependentOperator
================================================================================

 OpenMC 0.16 (openmc.deplete.microxs.get_microxs_and_flux): modelin TEK bir
 transport cozumunden yanabilir malzemelerin akisi ve tek gruplu mikroskobik
 tesir kesitleri ("direct" kip: reaksiyon hizlari dogrudan sayilir) alinir.
 IndependentOperator bu sabit tesir kesitleriyle Bateman denklemlerini cozer;
 akinin buyuklugu "fission-q" normalizasyonuyla guce olceklenir.

 SINIR: tesir kesitleri adimlar boyunca SABITTIR -- yakit tukendikce degisen
 spektrum (Pu birikimi, Xe, yanabilir zehirlerin yanmasi) gorulmez ve k-eff
 adim adim hesaplanmaz (sonuc tablosunda bos). Ilk transport'un k'si
 microxs_statepoint.h5'te kalir. On inceleme icindir.
================================================================================
"""

from __future__ import annotations

import os

STATEPOINT = "microxs_statepoint.h5"


def operator_kur(model, zincir: dict, dizin: str, onceki_sonuc=None):
    """IndependentOperator: yanabilir malzemeler, tek transport'tan MicroXS."""
    import openmc
    import openmc.deplete as d
    yanan = [m for m in model.materials if m.depletable]
    akilar, mikrolar = d.get_microxs_and_flux(
        model, yanan, chain_file=zincir["yol"],
        path_statepoint=os.path.join(dizin, STATEPOINT))
    return d.IndependentOperator(
        openmc.Materials(yanan), akilar, mikrolar, chain_file=zincir["yol"],
        normalization_mode="fission-q", prev_results=onceki_sonuc,
        fission_yield_opts={"energy": zincir["verim_enerjisi"]})
