# -*- coding: utf-8 -*-
"""
onizleme_boyama.py -- id haritasi (openmc.lib.slice_data) -> RGBA goruntu.

Renkler bizden (spec'teki malzeme renkleri); gerisi openmc.plots._id_map_to_rgb
(0.16.0) ile ayni tutulur ki eski Model.plot cizimiyle esdeger olsun:
  - bosluk malzemesi (-1) beyaz (Model.plot'un beyaz zemini),
  - renk sozlugunde olmayan kimlikler, artan kimlik sirasiyla
    np.random.RandomState(1).randint(0, 256, 3) renkleri alir.
Farklar (bilerek): hucre bulunmayan bolge (-2: geometri disi ya da tanimsiz)
SAYDAMDIR (eksen zemini gorunur; Model.plot'ta bosluk gibi beyazdi), cakisma
(-3, yalniz cakisma denetiminde) verilen renkte boyanir.
Boyama uint8 arama tablosuyla (LUT) yapilir (np.unique siralamasindan kacinilir).
"""

import numpy as np

from cekirdek.ceviri import _
from cekirdek.cizim_sureci import BOSLUK, CAKISMA, TANIMSIZ

_BEYAZ = (1.0, 1.0, 1.0, 1.0)       # Model.plot zemini (openmc.plots._id_map_to_rgb)
_SAYDAM = (0.0, 0.0, 0.0, 0.0)
_KAYDIRMA = -CAKISMA                # en kucuk kod (-3) tablonun 0. satiri
_LUT_SINIRI = 1 << 22               # daha buyuk kimlikte np.unique yoluna dusulur
_RASTGELE_TOHUM = 1                 # openmc.plots._id_map_to_rgb ile ayni


def _rgb01(renk):
    return tuple(float(v) / 255.0 for v in renk[:3])


def _kimlik_renkleri(kimlikler, renkler, varsayilan):
    """Gorunen pozitif kimlik -> RGB (0-1). Sozlukte olmayana varsayilan; o da
    yoksa openmc'nin rastgele rengi (artan kimlik sirasiyla)."""
    sonuc = {}
    rng = np.random.RandomState(_RASTGELE_TOHUM)
    for k in kimlikler:
        if k <= 0:
            continue
        if k in renkler:
            sonuc[k] = _rgb01(renkler[k])
        elif varsayilan is not None:
            sonuc[k] = _rgb01(varsayilan)
        else:
            sonuc[k] = _rgb01(rng.randint(0, 256, (3,)))
    return sonuc


def _gorunen_kimlikler(kanal):
    pozitif = kanal[kanal > 0]
    if pozitif.size == 0:
        return []
    if int(pozitif.max()) < _LUT_SINIRI:
        return np.flatnonzero(np.bincount(pozitif)).tolist()
    return np.unique(pozitif).tolist()


def _bayt(rgba):
    return tuple(int(round(255 * v)) for v in rgba)


def _boya(kanal, renkler, varsayilan, cakisma_rengi):
    """Kimlik kanali -> RGBA uint8 (v, h, 4). uint8 tablo: float64'e gore 8 kat
    az bellek, imshow ayni (matplotlib uint8'i 0-255 okur)."""
    kanal = np.asarray(kanal)
    if (kanal < CAKISMA).any():
        kanal = np.where(kanal < CAKISMA, TANIMSIZ, kanal)
    eslesme = _kimlik_renkleri(_gorunen_kimlikler(kanal), renkler, varsayilan)
    ozel = {BOSLUK: _BEYAZ, TANIMSIZ: _SAYDAM, CAKISMA: tuple(cakisma_rengi[:3]) + (1.0,)}
    enb = int(kanal.max(initial=0))
    if enb < _LUT_SINIRI:
        tablo = np.empty((enb + 1 + _KAYDIRMA, 4), dtype=np.uint8)
        tablo[:] = _bayt(_BEYAZ)
        for kod, rgba in ozel.items():
            tablo[kod + _KAYDIRMA] = _bayt(rgba)
        for k, rgb in eslesme.items():
            tablo[k + _KAYDIRMA] = _bayt(rgb + (1.0,))
        return tablo[kanal.astype(np.intp) + _KAYDIRMA]
    tum = dict(ozel, **{k: rgb + (1.0,) for k, rgb in eslesme.items()})
    benzersiz, ters = np.unique(kanal, return_inverse=True)
    tablo = np.asarray([_bayt(tum.get(int(k), _BEYAZ)) for k in benzersiz], dtype=np.uint8)
    return tablo[ters].reshape(kanal.shape + (4,))


def malzeme_goruntusu(geom, renkler, cakisma_rengi):
    """geom (v, h, 3) [hucre, ornek, malzeme]; renkler {malzeme id: (R,G,B) 0-255}
    -> RGBA (v, h, 4) uint8."""
    return _boya(np.asarray(geom)[..., 2], renkler, None, cakisma_rengi)


def hucre_goruntusu(geom, renkler=None, varsayilan=None, cakisma_rengi=(1.0, 0.0, 0.0)):
    """Hucre renklendirmesi. renkler {hucre id: (R,G,B)} (vurgu); sozlukte
    olmayan hucre `varsayilan`, o da yoksa openmc'nin rastgele rengi."""
    return _boya(np.asarray(geom)[..., 0], renkler or {}, varsayilan, cakisma_rengi)


def gosterge_ogeleri(gosterge, cakisma_var, cakisma_rengi):
    """[(etiket, (r, g, b) 0-1)]: modeldeki malzemeler (+ cakisma varsa)."""
    ogeler = [(str(ad), _rgb01(renk)) for ad, renk in gosterge]
    if cakisma_var:
        ogeler.append((_("Çakışma"), tuple(cakisma_rengi[:3])))
    return ogeler
