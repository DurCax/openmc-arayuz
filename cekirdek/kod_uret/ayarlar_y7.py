# -*- coding: utf-8 -*-
"""
 kod_uret/ayarlar_y7.py  --  betigin Y7 ayar satirlari: foton tasinimi, sicaklik

 Kurucu ile AYNI kaynaktan (cekirdek/foton.py, cekirdek/sicaklik.py
 betik_satirlari). Esdegerlik: testler/test_y7_ayar.py
 (test_kurucu_ve_betik_ayni_ayarlar).
"""

from typing import List

from cekirdek import foton, sicaklik


def _y7_ayar_satirlari(spec: dict, satirlar: List[str]) -> None:
    """bolumler._ayarlar kancasi: Settings'e foton ve sicaklik ayarlarini yazar."""
    ek = foton.betik_satirlari(spec) + sicaklik.betik_satirlari(spec)
    if ek:
        satirlar.append("")
        satirlar.extend(ek)
