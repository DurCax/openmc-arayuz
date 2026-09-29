# -*- coding: utf-8 -*-
"""
test_kalite_altyapi.py -- kalite altyapisi (conftest atlama metni, kapsam
olcum ayarlari) icin hizli testler.
"""

import os
import re

from testler.ortak_test import kontrol, KOK


def test_atlama_nedeni_eksikleri_birlikte_soyler():
    print("\n[KA1] conftest: hem veri hem zincir eksikse atlama metni ikisini de soyler")
    import conftest
    iki = conftest.atlama_nedeni(False, False, True, True)
    kontrol("ikisi de eksik -> iki neden", iki is not None and "OPENMC_CROSS_SECTIONS" in iki
            and "OPENMC_CHAIN_FILE" in iki, "-> %r" % iki)
    kontrol("yalniz zincir eksik -> yalniz zincir",
            conftest.atlama_nedeni(True, False, True, True)
            == "tukenme zinciri yok (OPENMC_CHAIN_FILE)")
    kontrol("yalniz veri isteyen test zincir eksikliginden atlanmaz",
            conftest.atlama_nedeni(True, False, True, False) is None)
    kontrol("hicbir sey eksik degil -> atlanmaz",
            conftest.atlama_nedeni(True, True, True, True) is None)


def test_kapsam_betigi_oturumu_yalitir():
    print("\n[KA2] araclar/kapsam.sh: her oturum kendi COVERAGE_FILE dizinini kullanir")
    with open(os.path.join(KOK, "araclar", "kapsam.sh"), encoding="utf-8") as f:
        betik = f.read()
    kontrol("COVERAGE_FILE gecici dizine yonlendirilir",
            re.search(r"^\S*=\"\$\(mktemp -d", betik, re.M) is not None
            and re.search(r"^export COVERAGE_FILE=", betik, re.M) is not None)


def test_modul_basina_veri_listeleri():
    print("\n[KA3] conftest: modul basina VERI_GEREKEN / ZINCIR_GEREKEN")
    import importlib
    import types
    import conftest

    def test_a():
        pass
    sahte = types.SimpleNamespace(VERI_GEREKEN=[test_a, "test_b"])
    kontrol("islev ve ad metni kabul edilir",
            conftest.modul_gerekenleri(sahte, "VERI_GEREKEN") == {"test_a", "test_b"})
    kontrol("liste yoksa bos", conftest.modul_gerekenleri(sahte, "ZINCIR_GEREKEN") == set())
    ortak = importlib.import_module("testler.ortak_test")
    bayat = []
    for m in ortak.ek_moduller():
        hizli, yavas = conftest.test_listeleri(m)
        adlar = {fn.__name__ for fn in hizli + yavas}
        for liste in ("VERI_GEREKEN", "ZINCIR_GEREKEN"):
            bayat += ["%s:%s:%s" % (m.__name__, liste, a)
                      for a in sorted(conftest.modul_gerekenleri(m, liste) - adlar)]
    kontrol("modul listelerindeki her ad o modulun HIZLI/YAVAS testi", not bayat,
            "-> %s" % bayat)


HIZLI = [test_atlama_nedeni_eksikleri_birlikte_soyler, test_kapsam_betigi_oturumu_yalitir,
         test_modul_basina_veri_listeleri]
YAVAS = []
