# -*- coding: utf-8 -*-
"""
test_guc_coklu.py -- cok turlu guc dagilimi semasi (guc_dagilimi.cubuklar).

ISKELET (Dalga 2 on-commit 2). Sema karari cekirdek/sema.py'de
VARSAYILAN_GUC ustundeki "SEMA KARARI" notundadir. Uygulama Ajan 8b'nindir:
8b uygulayinca asagidaki islevleri HIZLI listesine alir (BEKLEYEN bosalir) ve
kendi cok tally / normalizasyon testlerini bu modüle ekler.
Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import copy
import glob
import json
import os

from testler.ortak_test import kontrol, ORNEK


def _eski_bicimli(cubuk="yakit_cubugu", bolge=0):
    from cekirdek import sema
    ham = sema.yeni_spec("guc")
    ham["guc_dagilimi"] = {"var": True, "cubuk": cubuk, "bolge": bolge,
                           "skor": "kappa-fission"}
    return ham


def test_varsayilan_cubuklar_bos():
    print("\n[GC1] VARSAYILAN_GUC: cubuklar = [] ve eski alanlar yok")
    from cekirdek import sema
    g = sema.yeni_spec("x")["guc_dagilimi"]
    kontrol("cubuklar bos liste", g.get("cubuklar") == [])
    kontrol("eski cubuk/bolge alani yok", "cubuk" not in g and "bolge" not in g)


def test_eski_bicim_tek_ogeli_listeye():
    print("\n[GC2] eski cubuk/bolge okunur -> tek ogeli cubuklar listesi")
    from cekirdek import sema
    g = sema.tamamla(_eski_bicimli("yakit_cubugu", 1))["guc_dagilimi"]
    kontrol("tek oge", g.get("cubuklar") == [{"cubuk": "yakit_cubugu", "bolge": 1}])
    kontrol("eski alanlar kaydedilmez", "cubuk" not in g and "bolge" not in g)
    bos = sema.tamamla(_eski_bicimli(None))["guc_dagilimi"]
    kontrol("eski cubuk None -> []", bos.get("cubuklar") == [])


def test_yeni_bicim_kazanir():
    print("\n[GC3] hem eski hem yeni alan varsa 'cubuklar' kazanir; tamamla girdiyi degistirmez")
    from cekirdek import sema
    ham = _eski_bicimli("eski")
    ham["guc_dagilimi"]["cubuklar"] = [{"cubuk": "a", "bolge": 0}, {"cubuk": "b", "bolge": 0}]
    once = copy.deepcopy(ham)
    g = sema.tamamla(ham)["guc_dagilimi"]
    kontrol("yeni liste aynen", g.get("cubuklar") == once["guc_dagilimi"]["cubuklar"])
    kontrol("girdi degismedi", ham == once)


def test_ornekler_yeni_bicimde_yuklenir():
    print("\n[GC4] guc_dagilimi olan her ornek yeni bicimle yuklenir")
    from cekirdek import sema
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        with open(yol, encoding="utf-8") as f:
            ham = json.load(f)
        if "guc_dagilimi" not in ham:
            continue
        g = sema.yukle(yol)["guc_dagilimi"]
        eski = ham["guc_dagilimi"].get("cubuk")
        beklenen = ham["guc_dagilimi"].get("cubuklar") or (
            [{"cubuk": eski, "bolge": ham["guc_dagilimi"].get("bolge") or 0}] if eski else [])
        kontrol("%s: cubuklar" % os.path.basename(yol), g.get("cubuklar") == beklenen,
                "-> %s" % g.get("cubuklar"))


BEKLEYEN = []
HIZLI = [test_varsayilan_cubuklar_bos, test_eski_bicim_tek_ogeli_listeye,
         test_yeni_bicim_kazanir, test_ornekler_yeni_bicimde_yuklenir]
YAVAS = []
