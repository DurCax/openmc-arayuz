# -*- coding: utf-8 -*-
"""
 kod_uret/ayarlar_y9.py  --  betigin Y9 ayar satirlari: varyans azaltma (agirlik pencereleri)

 Kurucu ile AYNI kaynaktan (cekirdek/varyans.py betik_satirlari).
 Esdegerlik: testler/test_y9_varyans.py.
"""

from typing import List

from cekirdek import varyans


def _y9_ayar_satirlari(spec: dict, satirlar: List[str], sinir_kutu) -> None:
    """bolumler._ayarlar kancasi: Settings'e agirlik penceresi ayarlarini yazar."""
    ek = varyans.betik_satirlari(spec, sinir_kutu)
    if ek:
        satirlar.append("")
        satirlar.extend(ek)
