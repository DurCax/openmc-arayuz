# -*- coding: utf-8 -*-
"""
 test_k5_pencere.py  --  v3 K5: ana pencerede sayfa + secim -> onizleme kapsami;
                         Gorunum > Onizlemeyi goster (F7), durum QSettings'te;
                         kapsamli cizimde Calistir kapisi tam modele bakar
"""

import os

from testler.ortak_test import kontrol, ORNEK

_ZAMAN_ASIMI = 120.0


def _pencere(ad):
    from PySide6 import QtWidgets
    from cekirdek import sema
    from arayuz.pencere.ana_pencere import AnaPencere
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    p = AnaPencere()
    p._proje_kur(sema.yukle(os.path.join(ORNEK, ad + ".json")), None, None)
    return p


def _git(p, sayfa):
    p.sekmeye_git(sayfa, sessiz=True)
    p.onizleme.bekle(_ZAMAN_ASIMI)


def _kapat(p):
    p._kirli = False
    p.close()


def _satir_sec(liste, ad):
    from PySide6 import QtCore
    for i in range(liste.count()):
        veri = liste.item(i).data(QtCore.Qt.UserRole)
        if veri == ad or (isinstance(veri, tuple) and veri[1] == ad):
            liste.setCurrentRow(i)
            return True
    return False


def test_sayfa_ve_secim_kapsami():
    print("\n[K5P-1] Parcalar -> secili pin, Demet -> secili demet, diger sayfalar -> tam model")
    p = _pencere("pwr_ceyrek_kor")
    try:
        _git(p, "parcalar")
        kontrol("pin satiri secildi", _satir_sec(p.s_cubuk.liste, "yakit_31"))
        p.onizleme.bekle(_ZAMAN_ASIMI)
        k = p.onizleme.etkin_kapsam
        kontrol("Parcalar: pin alt modeli", k.spec is not None and k.spec["kor"]["cubuk"] == "yakit_31",
                "-> %s" % (k,))
        kontrol("kapsam etiketi gorunur", "yakit_31" in p.onizleme.kapsam_bilgi.text())
        p._bulgular = []
        izin, neden = p._kosu_izni()
        kontrol("kapsamli cizimde kapi tam modele gore acik", izin, "-> %s" % neden)
        _git(p, "demet")
        _satir_sec(p.s_demet.liste, "demet_31")
        p.onizleme.bekle(_ZAMAN_ASIMI)
        k = p.onizleme.etkin_kapsam
        kontrol("Demet: demet alt modeli", k.spec is not None and k.spec["kor"]["demet"] == "demet_31")
        _git(p, "malzemeler")
        kontrol("Malzemeler: tam model", p.onizleme.etkin_kapsam.spec is None)
        _git(p, "kor")
        kontrol("Geometri (sablon): tam kor", p.onizleme.etkin_kapsam.spec is None)
        _git(p, "parcalar")
        from arayuz.onizleme_kapsam import KAPSAM_TAM
        p.onizleme.kapsam.setCurrentIndex(p.onizleme.kapsam.findData(KAPSAM_TAM))
        p.onizleme.bekle(_ZAMAN_ASIMI)
        kontrol("Tam model kipi Parcalar'da da tam model", p.onizleme.etkin_kapsam.spec is None)
    finally:
        _kapat(p)


def test_gelismis_dugum_ve_tambur_kapsami():
    print("\n[K5P-2] gelismis geometri: secili dugum ve Parcalar'da tambur")
    p = _pencere("kafes_tamburlu_yansitici")
    try:
        _git(p, "kor")
        p.s_kor.gelismis_editor.sec(("kok", "ic"))
        p.onizleme.bekle(_ZAMAN_ASIMI)
        k = p.onizleme.etkin_kapsam
        kontrol("Geometri: kafes dugumu alt modeli",
                k.spec is not None and k.spec["geometri"]["kok"]["ic"]["tur"] == "kafes", "-> %s" % (k,))
        p.s_kor.gelismis_editor.sec(("kok",))
        p.onizleme.bekle(_ZAMAN_ASIMI)
        kontrol("Geometri: kok secili -> tam kor", p.onizleme.etkin_kapsam.spec is None)
        _git(p, "parcalar")
        p.s_cubuk._tambur_sec("tambur_b4c")
        p.onizleme.bekle(_ZAMAN_ASIMI)
        k = p.onizleme.etkin_kapsam
        kontrol("Parcalar: tambur alt modeli",
                k.spec is not None and k.spec["geometri"]["kok"]["ic"]["ad"] == "tambur_b4c")
    finally:
        _kapat(p)


def test_onizlemeyi_gizle_goster_menusu():
    print("\n[K5P-3] Gorunum > Onizlemeyi goster (F7): panel gizlenir, durum hatirlanir, gizliyken cizim yok")
    from arayuz.pencere import kabuk
    p = _pencere("pwr_17x17")
    turler = []
    asil = p.onizleme._istemci.iste
    p.onizleme._istemci.iste = lambda istek: (turler.append(istek["tur"]), asil(istek))[1]
    try:
        e = p.e_onizleme_goster
        kontrol("eylem Gorunum menusunde",
                any(e in m.menu().actions() for m in p.menuBar().actions() if m.menu()))
        kontrol("kisayol F7, isaretli", e.shortcut().toString() == "F7" and e.isChecked())
        e.trigger()
        kontrol("gizlendi: panel daraltildi, ayar yazildi", p.onizleme_paneli.dar_mi()
                and str(p.ayarlar.value(kabuk.ONIZLEME_AYARI)).lower() in ("false", "0"))
        kontrol("eylem isareti kalkti", not e.isChecked())
        del turler[:]
        p.onizleme.iste()
        p.onizleme.bekle(_ZAMAN_ASIMI)
        kontrol("gizliyken yalniz kontrol (cizim yok)", turler == ["kontrol"], "-> %s" % turler)
        p.onizleme_paneli.daralt(False)          # panel dugmesiyle acilinca eylem de isaretlenir
        kontrol("panel acilinca eylem isaretli", e.isChecked())
        e.trigger()
        e.trigger()
        kontrol("yeniden gosterildi, ayar yazildi", not p.onizleme_paneli.dar_mi()
                and str(p.ayarlar.value(kabuk.ONIZLEME_AYARI)).lower() in ("true", "1"))
        kontrol("yardim kisayol tablosunda", "F7" in p._kisayol_html())
    finally:
        _kapat(p)


HIZLI = [test_sayfa_ve_secim_kapsami, test_gelismis_dugum_ve_tambur_kapsami,
         test_onizlemeyi_gizle_goster_menusu]
YAVAS = []
