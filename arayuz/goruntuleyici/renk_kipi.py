# -*- coding: utf-8 -*-
"""
 renk_kipi.py  --  Goruntuleyici renk kipleri (saf; Qt'siz)

   Malzeme   spec malzeme renkleri (arayuz/onizleme_boyama.malzeme_goruntusu)
   Hucre     hucre kimligi renkleri (openmc'nin tohumlu rastgele renkleri)
   Cakisma   model soluk gri; cakisma (-3) ve tanimsiz bolge (-2) opak vurgu

 Cakisma kodu (olculdu, OpenMC 0.16.0, testler/test_y2_isci.py): cakisma
 denetiminde MALZEME kanali -3, HUCRE kanali -4 olur. onizleme_boyama hucre
 kanalinda -3'ten kucugu tanimsiz sayar; burada hucre kipinde cakisma ayrica
 -3'e cevrilir ki cakisma her kipte gorunsun.
 -2 "hucre yok" demektir: geometri disi YA DA tanimsiz bolge (OpenMC ayirmaz);
 silindirik/altigen modelin sinir kutusu koselerinde olagandir.
"""

import numpy as np

from cekirdek import cizim_sureci as cs
from cekirdek.ceviri import N_
from arayuz import onizleme_boyama as boyama

MALZEME, HUCRE, CAKISMA_KIPI = "material", "cell", "cakisma"
KIPLER = ((MALZEME, N_("Malzeme")), (HUCRE, N_("Hücre")),
          (CAKISMA_KIPI, N_("Çakışma ve tanımsız bölge")))
_SOLUK_GRI = 0.80             # cakisma kipinde modelin gri tonu (0-1)
_SOLUK_SAYDAMLIK = 0.45       # ve opakligi: vurgu one ciksin, model okunur kalsin
_BAYT = 255


def cakisma_maskesi(geom) -> np.ndarray:
    """Cakisma pikselleri (bool, (v, h))."""
    geom = np.asarray(geom)
    return (geom[..., 2] == cs.CAKISMA) | (geom[..., 0] < cs.TANIMSIZ)


def tanimsiz_maskesi(geom) -> np.ndarray:
    """Hucre bulunmayan (-2) ve cakisma olmayan pikseller."""
    geom = np.asarray(geom)
    return (geom[..., 0] == cs.TANIMSIZ) & ~cakisma_maskesi(geom)


def sayim(geom) -> dict:
    """{"cakisma": piksel, "tanimsiz": piksel}."""
    return {"cakisma": int(cakisma_maskesi(geom).sum()),
            "tanimsiz": int(tanimsiz_maskesi(geom).sum())}


def _rgba(renk01) -> tuple:
    return tuple(int(round(_BAYT * v)) for v in renk01[:3]) + (_BAYT,)


def goruntu(geom, kip: str, renkler: dict, cakisma_rengi, tanimsiz_rengi) -> np.ndarray:
    """geom (v, h, 3) -> RGBA (v, h, 4) uint8 (yeni dizi; girdi degismez).
    renkler {malzeme id: (R, G, B) 0-255}; cakisma/tanimsiz rengi (r, g, b) 0-1."""
    geom = np.asarray(geom)
    cak = cakisma_maskesi(geom)
    if kip == MALZEME:
        return boyama.malzeme_goruntusu(geom, renkler, cakisma_rengi)
    if kip == HUCRE:
        duzeltilmis = geom.copy()
        duzeltilmis[..., 0][cak] = cs.CAKISMA
        return boyama.hucre_goruntusu(duzeltilmis, None, None, cakisma_rengi)
    if kip != CAKISMA_KIPI:
        raise ValueError("bilinmeyen renk kipi: %r" % (kip,))
    img = np.zeros(geom.shape[:2] + (4,), dtype=np.uint8)
    img[...] = (int(_BAYT * _SOLUK_GRI),) * 3 + (int(_BAYT * _SOLUK_SAYDAMLIK),)
    img[tanimsiz_maskesi(geom)] = _rgba(tanimsiz_rengi)
    img[cak] = _rgba(cakisma_rengi)
    return img
