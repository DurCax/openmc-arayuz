# -*- coding: utf-8 -*-
"""
test_rapor_sozlesme.py -- cekirdek/rapor.py DONUK sozlesmesi ve
CalistirSekmesi.kosu_durumu_degisti / son_kosu_dizini (Dalga 2 on-commit 6).
Ajan 10 govdeyi uyguladi; NotImplementedError denetimi (RS3) silindi, yerini
testler/test_rapor.py aldi.
Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import ast
import dataclasses
import inspect
import os

from testler.ortak_test import kontrol, KOK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_rapor_imzasi():
    print("\n[RS1] rapor.olustur imzasi, RaporHatasi, RaporSonucu")
    from cekirdek import rapor
    kontrol("olustur(spec, kosu_dizini, yol, bicim)",
            list(inspect.signature(rapor.olustur).parameters)
            == ["spec", "kosu_dizini", "yol", "bicim"])
    kontrol("RaporHatasi ValueError alt sinifi", issubclass(rapor.RaporHatasi, ValueError))
    kontrol("BICIMLER", rapor.BICIMLER == ("html", "pdf"))
    s = rapor.RaporSonucu(yol="/x.html", uyarilar=("u",))
    try:
        s.yol = "y"
        dondu = False
    except dataclasses.FrozenInstanceError:
        dondu = True
    kontrol("RaporSonucu dondurulmus (yol, uyarilar)", dondu
            and [f.name for f in dataclasses.fields(rapor.RaporSonucu)] == ["yol", "uyarilar"])
    kontrol("uyarilar varsayilani bos tuple", rapor.RaporSonucu("/x").uyarilar == ())


def test_rapor_qt_siz():
    print("\n[RS2] cekirdek/rapor.py modul duzeyinde PySide6 ice aktarmaz")
    with open(os.path.join(KOK, "cekirdek", "rapor.py"), encoding="utf-8") as f:
        agac = ast.parse(f.read())
    adlar = []
    for dugum in agac.body:
        if isinstance(dugum, ast.Import):
            adlar += [a.name for a in dugum.names]
        elif isinstance(dugum, ast.ImportFrom):
            adlar.append(dugum.module or "")
    kontrol("PySide6 yok", not any(a.split(".")[0] == "PySide6" for a in adlar), "-> %s" % adlar)


def test_calistir_kosu_sinyali():
    print("\n[RS4] CalistirSekmesi.kosu_durumu_degisti(bool) ve son_kosu_dizini()")
    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.sekme_calistir import CalistirSekmesi
    c = CalistirSekmesi()
    kontrol("baslangicta son_kosu_dizini None", c.son_kosu_dizini() is None)
    c._dizin, c._son_basarili = "/tmp/kosu", True
    kontrol("basarili kosudan sonra dizin", c.son_kosu_dizini() == "/tmp/kosu")
    c.sifirla()
    kontrol("sifirla -> None", c.son_kosu_dizini() is None)
    gelen = []
    c.kosu_durumu_degisti.connect(gelen.append)
    c._bitti(1, None)            # surec yokken biten kosu da False yayar
    kontrol("bitis False yayar", gelen == [False], "-> %s" % gelen)
    c.deleteLater()


HIZLI = [test_rapor_imzasi, test_rapor_qt_siz, test_calistir_kosu_sinyali]
YAVAS = []
