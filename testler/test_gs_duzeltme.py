# -*- coding: utf-8 -*-
"""
 test_gs_duzeltme.py  --  Dalga G+S inceleme duzeltmeleri (v2-gs-duzeltme).

 Her test bir inceleme bulgusunu kilitler (madde numarasi test basliginda).
 Sozlesme: testler/ortak_test.py.
"""

import copy

from testler import geometri_ortak as go
from testler.ortak_test import kontrol


def _sinir_hatalari(spec):
    from cekirdek import geometri
    return [b for b in geometri.yapisal_denetim(spec)
            if b.seviye == "hata" and "sinir" in b.yer]


def test_periyodik_es_etkin_bc():
    print("\n[GS1] dikdortgen sinir: eksik yuz 'yan'i miras alir; periyodik es etkin BC ile")
    s = go.duzenek_e_ceyrek()
    s["geometri"]["kok"]["sinir"] = {"yan": "periodic", "alt": "reflective",
                                     "ust": "reflective", "yuzler": {"-x": "reflective"}}
    kontrol("yan=periodic, -x reflective -> +x essiz periyodik HATA", _sinir_hatalari(s),
            "-> bulgu yok")
    t = copy.deepcopy(s)
    t["geometri"]["kok"]["sinir"]["yuzler"] = {"-x": "reflective", "+x": "vacuum"}
    kontrol("yan=periodic, x yuzleri acik, y yuzleri miras periyodik cift -> hata yok",
            not _sinir_hatalari(t), "-> %s" % _sinir_hatalari(t))
    u = copy.deepcopy(s)
    u["geometri"]["kok"]["sinir"] = {"yan": "reflective", "yuzler": {"+y": "periodic"}}
    kontrol("yan=reflective, yalniz +y periodic -> HATA", _sinir_hatalari(u))


HIZLI = [test_periyodik_es_etkin_bc]
YAVAS = []
