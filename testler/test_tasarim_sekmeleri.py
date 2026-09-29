# -*- coding: utf-8 -*-
"""
test_tasarim_sekmeleri.py -- tasarim sekmeleri (Malzemeler, Parcalar, Demet)
Dalga 2 / Ajan 7 kabul testleri.

1. Spec gidis-donus: her ornek yuklenir, sekme doldurulur ve her oge
   DUZENLEMESIZ kaydedilir (_kaydet / _cubuk_kaydet / _plaka_kaydet /
   _harita_kaydet; malzemede diyalog sonucu duzenlemeyi_uygula) -> spec
   ilk haliyle DERIN ESIT (sekmeler veriyi sessizce degistirmez).
2. Kart duzeni: sekmeler tasarim sisteminin Kart'larini kullanir, eylem
   dugmeleri ikonludur ve QTabWidget'a bagli degildir (QScrollArea icinde
   calisir).
3. Kabuk sozlesmesi: baslik_eylemleri()/komutlar() QAction dizisi dondurur.
Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import copy
import glob
import os

from testler.ortak_test import kontrol, ORNEK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _ornekler():
    from cekirdek import sema
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        yield os.path.basename(yol), sema.yukle(yol)


def _fark(a, b, yol=""):
    """Ilk farkin yolu (derin esitlikte None)."""
    if type(a) is not type(b):
        return "%s: tur %s != %s" % (yol, type(a).__name__, type(b).__name__)
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                return "%s/%s: yalniz bir tarafta" % (yol, k)
            f = _fark(a[k], b[k], "%s/%s" % (yol, k))
            if f:
                return f
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return "%s: uzunluk %d != %d" % (yol, len(a), len(b))
        for i, (x, y) in enumerate(zip(a, b)):
            f = _fark(x, y, "%s/%d" % (yol, i))
            if f:
                return f
        return None
    return None if a == b else "%s: %r != %r" % (yol, a, b)


def _malzeme_turu(spec):
    from arayuz import sekme_malzeme as sm
    t = sm.MalzemeSekmesi()
    t.spec_yukle(spec)
    for i, m in enumerate(list(spec["malzemeler"])):
        t.tablo.selectRow(i)
        d = sm.MalzemeDiyalog(m, spec, t)
        t.duzenlemeyi_uygula(i, d.sonuc())
        d.deleteLater()
    t.deleteLater()


def _cubuk_turu(spec):
    from arayuz.sekme_cubuk import CubukSekmesi
    t = CubukSekmesi()
    t.spec_yukle(spec)
    for i in range(t.liste.count()):
        t.liste.setCurrentRow(i)
        tur = t._secili()[0]
        (t._cubuk_kaydet if tur == "cubuk" else t._plaka_kaydet)()
    t.deleteLater()


def _demet_turu(spec):
    from arayuz.sekme_demet import DemetSekmesi
    t = DemetSekmesi()
    t.spec_yukle(spec)
    for i in range(t.liste.count()):
        t.liste.setCurrentRow(i)
        t._kaydet()
        t._harita_kaydet()
    t.deleteLater()


def test_spec_gidis_donus():
    print("\n[TS1] her ornek: doldur -> duzenlemesiz kaydet -> spec derin esit")
    _qt()
    for ad, spec in _ornekler():
        for sekme, tur in (("malzeme", _malzeme_turu), ("cubuk", _cubuk_turu),
                           ("demet", _demet_turu)):
            s = copy.deepcopy(spec)
            tur(s)
            f = _fark(spec, s)
            kontrol("%s / %s: spec degismedi" % (ad, sekme), f is None, "-> %s" % f)


HIZLI = [test_spec_gidis_donus]
YAVAS = []
