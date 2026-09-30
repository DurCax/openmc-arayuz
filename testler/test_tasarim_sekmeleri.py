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
3. Kabuk sozlesmesi: komutlar() QAction dizisi dondurur (Ctrl+K paleti),
   odakla("malzeme:<ad>" / "cubuk:<ad>" / "demet:<ad>") o ogeyi secer.
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


def _sekmeler(spec):
    from arayuz.sekme_malzeme import MalzemeSekmesi
    from arayuz.sekme_cubuk import CubukSekmesi
    from arayuz.sekme_demet import DemetSekmesi
    sekmeler = []
    for sinif in (MalzemeSekmesi, CubukSekmesi, DemetSekmesi):
        t = sinif()
        t.spec_yukle(spec)
        sekmeler.append(t)
    return sekmeler


def _ornek(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad))


def test_kart_duzeni():
    print("\n[TS2] kart duzeni: Kart, ikonlu eylemler, QTabWidget'siz")
    _qt()
    from PySide6 import QtWidgets
    from arayuz import bilesenler as bl
    for t in _sekmeler(_ornek("sfr_altigen.json")):
        ad = type(t).__name__
        kartlar = t.findChildren(bl.Kart)
        kontrol("%s: en az bir Kart" % ad, len(kartlar) >= 1, "-> %d" % len(kartlar))
        kontrol("%s: QTabWidget yok" % ad, not t.findChildren(QtWidgets.QTabWidget))
        ikonsuz = [e.text() for e in t.komutlar() if e.icon().isNull()]
        kontrol("%s: komut eylemleri ikonlu" % ad, not ikonsuz, "-> %s" % ikonsuz)
        t.deleteLater()


def test_kabuk_sozlesmesi():
    print("\n[TS3] kabuk sozlesmesi: komutlar() ve odakla()")
    _qt()
    from PySide6 import QtGui
    from arayuz.pencere import sekme_arayuzu as sa
    spec = _ornek("pwr_mox_demet.json")
    malzeme, cubuk, demet = _sekmeler(spec)
    for t in (malzeme, cubuk, demet):
        k = sa.komutlar(t)
        kontrol("%s: komutlar QAction dizisi" % type(t).__name__,
                k and all(isinstance(e, QtGui.QAction) for e in k), "-> %r" % (k,))
        kontrol("%s: eylemler kalici (ayni nesneler)" % type(t).__name__,
                sa.komutlar(t) == k)
        kontrol("%s: yabanci yer odaklanmaz" % type(t).__name__,
                not sa.odakla(t, "ayarlar") and not sa.odakla(t, "kor"))
    kontrol("malzeme:waba odaklandi", sa.odakla(malzeme, "malzeme:waba")
            and malzeme._secili_satir() == [m["ad"] for m in spec["malzemeler"]].index("waba"))
    kontrol("malzeme:yok odaklanmaz", not sa.odakla(malzeme, "malzeme:yok"))
    kontrol("cubuk:kilavuz_boru odaklandi", sa.odakla(cubuk, "cubuk:kilavuz_boru")
            and tuple(cubuk._secili()) == ("cubuk", "kilavuz_boru"))
    kontrol("demet:mox_demeti odaklandi", sa.odakla(demet, "demet:mox_demeti")
            and demet._secili_ad() == "mox_demeti")
    # Eylem dugmeye tiklar: "Sil" etkinligi secimi izler, Kopyala yeni oge ekler.
    once = len(spec["cubuklar"])
    kopya = [e for e in sa.komutlar(cubuk) if e.text().endswith(cubuk.d_kopya.text().strip())][0]
    kopya.trigger()
    kontrol("Parca: Kopyala eylemi cubuk ekledi", len(spec["cubuklar"]) == once + 1,
            "-> %d" % len(spec["cubuklar"]))
    malzeme.tablo.clearSelection()
    sil = [e for e in sa.komutlar(malzeme) if e.text().endswith(malzeme.d_sil.text().strip())][0]
    kontrol("Malzeme: secim yokken Sil eylemi etkisiz", not sil.isEnabled())
    for t in (malzeme, cubuk, demet):
        t.deleteLater()


HIZLI = [test_spec_gidis_donus, test_kart_duzeni, test_kabuk_sozlesmesi]
YAVAS = []
