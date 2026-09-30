# -*- coding: utf-8 -*-
"""
 test_betik_tambur.py  --  tamburlu kor + eksenel katman: betik kurucuyla ayni

 Hata (G-0 tasarim incelemesi, 30.09.2026): kod_uret'in tamburlu dali kor
 silindirini TEK hucre yaziyordu; kurucu ise _eksenel_hucreler ile katmanlara
 boluyordu. Tamburlu + eksenel modelde betik ile arayuzun kurdugu model farkliydi.
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

import copy

from testler.ortak_test import kontrol
from testler.test_butunlesme import _yukle, anlamsal_fark


def _katmanli_tamburlu():
    spec = copy.deepcopy(_yukle("tamburlu_kor"))
    spec["kor"]["eksenel"] = {"var": True, "bolgeler": [
        {"ad": "alt berilyum", "yukseklik": 10.0, "dolgu": "berilyum"},
        {"ad": "aktif", "yukseklik": 45.0, "dolgu": None},
        {"ad": "ust berilyum", "yukseklik": 10.0, "dolgu": "berilyum"},
    ]}
    return spec


def test_tamburlu_eksenel_betik_esdegerligi():
    print("\n[BT1] BETIK: tamburlu kor + eksenel katmanlar kurucuyla ayni")
    fark = anlamsal_fark(_katmanli_tamburlu(), n=600)
    kontrol("tamburlu + eksenel: kurucu ile betik ayni", not fark, "-> %s" % fark)


def test_tamburlu_katmansiz_betik_esdegerligi():
    print("\n[BT2] BETIK: tamburlu kor (katmansiz) kurucuyla ayni")
    fark = anlamsal_fark(copy.deepcopy(_yukle("tamburlu_kor")), n=600)
    kontrol("tamburlu (katmansiz): kurucu ile betik ayni", not fark, "-> %s" % fark)


HIZLI = [test_tamburlu_eksenel_betik_esdegerligi, test_tamburlu_katmansiz_betik_esdegerligi]
YAVAS = []
