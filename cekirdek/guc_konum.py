# -*- coding: utf-8 -*-
"""
guc_konum.py -- guc dagilimi: kafes turu ve konum -> fiziksel merkez

cekirdek/guc.py'den YALNIZ TASINDI (v3 T2, dosya boyu): "2b. KONUM ->
FIZIKSEL MERKEZ" bolumu ve _kafes_turu. Davranis aynidir; adlar guc'tan da
erisilir (guc.eleman_merkezi, guc.cubuk_merkezi, guc._kafes_turu ...).
Cizim ve nokta-hucre olcumu ayni kaynagi kullanir.
"""

import functools

from cekirdek import guc_kor as _guc_kor


def _kafes_turu(kafes):
    import openmc
    if isinstance(kafes, (openmc.HexLattice, _guc_kor.OtelemeDuzeyi)):
        return "altigen"
    if isinstance(kafes, _guc_kor.YerlesimDuzeyi):
        return "yerlesim"
    if isinstance(kafes, _guc_kor.KarisikDuzey):
        return "karisik"
    return "kare"


# ============================================================================
# 2b. KONUM -> FIZIKSEL MERKEZ (cizim ve nokta-hucre olcumu ayni kaynagi kullanir)
# ============================================================================

@functools.lru_cache(maxsize=32)
def _altigen_konumlar(halka, yonelim):
    from cekirdek import altigen
    return altigen.konumlar(halka, yonelim)


def eleman_merkezi(kafes, konum):
    """
    Kafes elemaninin merkezi, kafesin kendi koordinatinda [cm].
    Kare: lower_left + (i + 1/2) * adim. Altigen: center + adim * konum
    (konum cekirdek/altigen.konumlar'dan; OpenMC ile nokta-hucre olcumuyle
    dogrulandi, testler/test_guc_kor.py).
    """
    if isinstance(kafes, (_guc_kor.OtelemeDuzeyi, _guc_kor.YerlesimDuzeyi)):
        return kafes.merkezler[tuple(konum)]      # kafessiz: hucre otelemesi
    if isinstance(kafes, _guc_kor.KarisikDuzey):     # (kafes adi, i, j)
        return eleman_merkezi(kafes.kafesler[konum[0]], tuple(konum[1:]))
    if _kafes_turu(kafes) == "altigen":
        kx, ky = _altigen_konumlar(int(kafes.num_rings), kafes.orientation)[tuple(konum)]
        cx, cy = tuple(kafes.center)[:2]
        adim = kafes.pitch[0]
        return (cx + adim * kx, cy + adim * ky)
    llx, lly = tuple(kafes.lower_left)[:2]
    px, py = tuple(kafes.pitch)[:2]
    return (llx + (konum[0] + 0.5) * px, lly + (konum[1] + 0.5) * py)


def _duzeyler(dagilim, anahtar):
    """Anahtari duzey konumlari listesine acar (tek demette [anahtar])."""
    return list(anahtar) if dagilim.get("tam_kor") else [anahtar]


def cubuk_merkezi(dagilim, anahtar):
    """
    Cubugun modeldeki (x, y) merkezi [cm]: duzey merkezlerinin toplami.
    OpenMC kafes elemanina girerken koordinati eleman merkezine tasir; ara
    hucrelerde oteleme/donme olmadigi varsayilir (kurucu bunu kullanmaz).
    """
    x = y = 0.0
    for kafes, konum in zip(dagilim["kafesler"], _duzeyler(dagilim, anahtar)):
        ex, ey = eleman_merkezi(kafes, konum)
        x, y = x + ex, y + ey
    return (x, y)


def demet_anahtari(anahtar):
    """Tam kor anahtarindan demet anahtari (en ic duzey haric konum)."""
    return anahtar[0] if len(anahtar) == 2 else tuple(anahtar[:-1])


def demet_merkezi(dagilim, demet):
    """Demetin modeldeki (x, y) merkezi [cm] (tam kor)."""
    duzeyler = [demet] if dagilim.get("duzey_sayisi", 1) == 2 else list(demet)
    x = y = 0.0
    for kafes, konum in zip(dagilim["kafesler"][:-1], duzeyler):
        ex, ey = eleman_merkezi(kafes, konum)
        x, y = x + ex, y + ey
    return (x, y)
