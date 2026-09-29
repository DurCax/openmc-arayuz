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


HIZLI = [test_atlama_nedeni_eksikleri_birlikte_soyler, test_kapsam_betigi_oturumu_yalitir]
YAVAS = []
