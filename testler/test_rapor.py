# -*- coding: utf-8 -*-
"""
test_rapor.py -- cekirdek/rapor.py (HTML + PDF rapor), surum.derleme_bilgisi,
`openmc-arayuz-kosu rapor` alt komutu ve cekirdek/'in Qt'siz kalmasi.

Fixture: testler/veri/kosu_ornek/ (gercek, kucuk bir kosu; uret.py yeniden
uretir). Monte Carlo KOSULMAZ; statepoint okunur. Geometri kesitleri
`openmc -p` (cizim kipi, nukleer veri gerekmez) ile uretilir.
Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import ast
import copy
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time

from testler.ortak_test import kontrol, KOK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

FIXTURE = os.path.join(KOK, "testler", "veri", "kosu_ornek")
FIXTURE_SPEC = os.path.join(FIXTURE, "spec.json")


def _modul_duzeyi_importlar(agac):
    """Modul duzeyinde (islev/sinif govdeleri HARIC; try/if icleri DAHIL)
    ice aktarilan modul adlari."""
    adlar, yigin = [], list(agac.body)
    while yigin:
        dugum = yigin.pop()
        if isinstance(dugum, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(dugum, ast.Import):
            adlar += [a.name for a in dugum.names]
        elif isinstance(dugum, ast.ImportFrom):
            adlar.append(dugum.module or "")
        else:
            yigin.extend(ast.iter_child_nodes(dugum))
    return adlar


def test_cekirdek_qt_siz():
    print("\n[R1] cekirdek/ altinda hicbir modul modul duzeyinde PySide6 ice aktarmaz")
    ihlal = []
    for kok, _dizinler, dosyalar in os.walk(os.path.join(KOK, "cekirdek")):
        for ad in dosyalar:
            if not ad.endswith(".py"):
                continue
            yol = os.path.join(kok, ad)
            with open(yol, encoding="utf-8") as f:
                agac = ast.parse(f.read())
            if any(a.split(".")[0] == "PySide6" for a in _modul_duzeyi_importlar(agac)):
                ihlal.append(os.path.relpath(yol, KOK))
    kontrol("PySide6 modul duzeyinde yok", not ihlal, "-> %s" % ihlal)
    ornek = ast.parse("try:\n    from PySide6 import QtGui\nexcept ImportError:\n    pass\n"
                      "def f():\n    import PySide6\n")
    kontrol("tarayici try icini yakalar, islev icini yakalamaz",
            _modul_duzeyi_importlar(ornek) == ["PySide6"])


def test_derleme_bilgisi():
    print("\n[R2] surum.derleme_bilgisi: uygulama, surum, git, python")
    from cekirdek import surum
    b = surum.derleme_bilgisi()
    kontrol("alanlar", {"uygulama", "surum", "git_commit", "git_degisiklik", "python",
                        "platform"} <= set(b), "-> %s" % sorted(b))
    kontrol("surum tek kaynaktan", b["surum"] == surum.surum()
            and b["uygulama"] == surum.UYGULAMA_ADI)
    git_var = shutil.which("git") and os.path.exists(os.path.join(KOK, ".git"))
    if git_var:
        kontrol("git commit 40 hane", isinstance(b["git_commit"], str)
                and len(b["git_commit"]) == 40, "-> %r" % b["git_commit"])
    eski = surum._GIT
    kayitlar = []
    isleyici = logging.Handler()
    isleyici.emit = kayitlar.append
    kaydedici = logging.getLogger("openmc_arayuz")
    kaydedici.addHandler(isleyici)
    try:
        surum._GIT = "olmayan-git-komutu-xyz"
        b2 = surum.derleme_bilgisi()
    finally:
        surum._GIT = eski
        kaydedici.removeHandler(isleyici)
    kontrol("git yoksa None + log", b2["git_commit"] is None and b2["git_degisiklik"] is None
            and any("git" in r.getMessage() for r in kayitlar), "-> %r" % b2["git_commit"])


HIZLI = [test_cekirdek_qt_siz, test_derleme_bilgisi]
YAVAS = []
