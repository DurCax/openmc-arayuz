# -*- coding: utf-8 -*-
"""
test_kabuk_proje.py -- kabugun proje islemleri (arayuz/pencere/proje.py):
son kullanilanlar, kaydetme sorusu, ac / kaydet / farkli kaydet hatalari,
malzeme ice aktarma, betik / XML / PNG disa aktarma.

Diyaloglar taklit edilir (offscreen; modal exec() EDILMEZ).
"""

import os
import shutil
import tempfile
import warnings

from testler.ortak_test import kontrol, ORNEK   # noqa: F401

warnings.filterwarnings("ignore")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _pencere(dosya=None):
    from arayuz.ana_pencere import AnaPencere
    p = AnaPencere(dosya)
    p._kaydetme_sor = lambda: True
    return p


def _kapat(p):
    from PySide6 import QtCore
    p.s_tukenme.bekle()
    p._kirli = False
    p.close()
    p.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


class _Diyaloglar(object):
    """QFileDialog / QMessageBox statik islevlerini gecici olarak taklit eder."""

    ADLAR = (("QFileDialog", "getSaveFileName"), ("QFileDialog", "getOpenFileName"),
             ("QFileDialog", "getExistingDirectory"), ("QMessageBox", "critical"),
             ("QMessageBox", "information"))

    def __init__(self, kayit="", acma="", dizin=""):
        from PySide6 import QtWidgets
        self.qw = QtWidgets
        self.cagrilar = []
        self._eski = {(s, a): getattr(getattr(QtWidgets, s), a) for s, a in self.ADLAR}
        self.kayit, self.acma, self.dizin = kayit, acma, dizin

    def __enter__(self):
        qw = self.qw
        qw.QFileDialog.getSaveFileName = staticmethod(
            lambda *a, **k: (self.kayit, ""))
        qw.QFileDialog.getOpenFileName = staticmethod(
            lambda *a, **k: (self.acma, ""))
        qw.QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: self.dizin)
        qw.QMessageBox.critical = staticmethod(
            lambda _p, baslik, metin, *a: self.cagrilar.append(("hata", baslik, metin)))
        qw.QMessageBox.information = staticmethod(
            lambda _p, baslik, metin, *a: self.cagrilar.append(("bilgi", baslik, metin)))
        return self

    def __exit__(self, *_a):
        for (s, a), islev in self._eski.items():
            setattr(getattr(self.qw, s), a, islev)
        return False

    def turler(self):
        return [c[0] for c in self.cagrilar]


# ============================================================================
# son kullanilanlar ve kaydetme sorusu
# ============================================================================

def test_son_kullanilanlar():
    print("\n[KP1] son kullanilanlar: gecersiz/ornek girdiler suzulur, menu dolar")
    _qt()
    from cekirdek import sema
    d = tempfile.mkdtemp(prefix="kabuk_proje_")
    p = _pencere()
    try:
        yol = os.path.join(d, "a.json")
        sema.kaydet(sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json")), yol)
        p.ayarlar.setValue("son_dosyalar", yol)          # eski surum: tek metin
        kontrol("tek metin girdisi liste sayilir", p._son_listesi() == [yol])
        p.ayarlar.setValue("son_dosyalar", [os.path.join(d, "yok.json"),
                                            os.path.join(ORNEK, "pwr_17x17.json"), yol])
        kontrol("olmayan dosya ve ornek suzulur", p._son_listesi() == [yol],
                "-> %s" % p._son_listesi())
        p._son_menusu_yenile()
        eylemler = p.m_son.actions()
        kontrol("menude dosya adi, ipucunda tam yol",
                [e.text() for e in eylemler] == ["a.json"] and eylemler[0].toolTip() == yol)
        eylemler[0].trigger()
        kontrol("menu ogesi projeyi aciyor", p.proje_yolu == os.path.abspath(yol))
        p.ayarlar.setValue("son_dosyalar", [])
        p._son_menusu_yenile()
        bos = p.m_son.actions()
        kontrol("bos liste: tek, secilemez '(boş)' ogesi",
                len(bos) == 1 and bos[0].text() == "(boş)" and not bos[0].isEnabled())
    finally:
        _kapat(p)
        shutil.rmtree(d, True)


def test_kaydetme_sorusu():
    print("\n[KP2] kaydedilmemis degisiklik sorusu: Kaydet / Kaydetme / Vazgec")
    _qt()
    from PySide6 import QtWidgets
    from arayuz.pencere.proje import ProjeMixin
    p = _pencere(os.path.join(ORNEK, "pwr_pinhucre.json"))
    p._kaydetme_sor = lambda: ProjeMixin._kaydetme_sor(p)
    eski_exec = QtWidgets.QMessageBox.exec
    secim = {}
    metinler = []

    def sahte_exec(kutu):
        metinler.append([kutu.button(b).text() for b in
                         (QtWidgets.QMessageBox.Save, QtWidgets.QMessageBox.Discard,
                          QtWidgets.QMessageBox.Cancel)])
        kutu.button(secim["dugme"]).click()
        return 0
    QtWidgets.QMessageBox.exec = sahte_exec
    kayit = []
    p.proje_kaydet = lambda: kayit.append(1) or True
    try:
        p._kirli = False
        kontrol("temiz modelde soru sorulmaz", p._kaydetme_sor() is True and not metinler)
        p._kirli = True
        secim["dugme"] = QtWidgets.QMessageBox.Cancel
        kontrol("Vazgeç: False", p._kaydetme_sor() is False)
        kontrol("dugmeler Turkce ve acik",
                metinler[-1] == ["Kaydet", "Kaydetme", "Vazgeç"], "-> %s" % metinler[-1:])
        secim["dugme"] = QtWidgets.QMessageBox.Discard
        kontrol("Kaydetme: True, kayit yok", p._kaydetme_sor() is True and not kayit)
        secim["dugme"] = QtWidgets.QMessageBox.Save
        kontrol("Kaydet: proje_kaydet cagrilir", p._kaydetme_sor() is True and kayit == [1])
    finally:
        QtWidgets.QMessageBox.exec = eski_exec
        p._kirli = False
        _kapat(p)


# ============================================================================
# ac / kaydet hatalari
# ============================================================================

def test_ac_kaydet_hatalari():
    print("\n[KP3] ac / kaydet / farkli kaydet: hata diyalogu, iptal, uzanti")
    _qt()
    d = tempfile.mkdtemp(prefix="kabuk_proje_")
    p = _pencere()
    try:
        bozuk = os.path.join(d, "bozuk.json")
        with open(bozuk, "w", encoding="utf-8") as f:
            f.write("{ bozuk")
        with _Diyaloglar(acma=bozuk) as dg:
            p._ac_diyalog()
            kontrol("bozuk dosya: 'Açılamadı' diyalogu, model degismedi",
                    dg.turler() == ["hata"] and dg.cagrilar[0][1] == "Açılamadı"
                    and p.proje_yolu is None)
        with _Diyaloglar() as dg:
            kontrol("olmayan ornek kopyasi acilamaz",
                    p.ornek_ac(os.path.join(ORNEK, "yok_boyle.json")) is False
                    and dg.turler() == ["hata"])
        with _Diyaloglar(acma="") as dg:
            p._ac_diyalog()
            kontrol("Aç iptal: hicbir sey olmaz", not dg.cagrilar and p.proje_yolu is None)

        p.proje_ac(os.path.join(ORNEK, "pwr_pinhucre.json"))
        hedef = os.path.join(d, "kopya")
        with _Diyaloglar(kayit=hedef):
            kontrol("farkli kaydet: .json eklenir ve yazilir",
                    p.proje_farkli_kaydet() and p.proje_yolu == hedef + ".json"
                    and os.path.exists(hedef + ".json") and p.ornek_kaynagi is None)
        kontrol("kayit sonrasi baslikta '*' yok", not p.windowTitle().endswith("*"))
        with _Diyaloglar(kayit="") as dg:
            kontrol("farkli kaydet iptal: False", p.proje_farkli_kaydet() is False)
        p.proje_yolu = os.path.join(d, "yok_dizin", "x.json")
        with _Diyaloglar() as dg:
            kontrol("yazilamayan yer: 'Kaydedilemedi' diyalogu",
                    p.proje_kaydet() is False and dg.cagrilar[0][1] == "Kaydedilemedi")
    finally:
        _kapat(p)
        shutil.rmtree(d, True)


# ============================================================================
# ice / disa aktarma
# ============================================================================

def _materials_xml(dizin, ad="uo2"):
    import openmc
    m = openmc.Material(name=ad)
    m.add_nuclide("U235", 0.03)
    m.add_nuclide("O16", 2.0)
    m.set_density("g/cm3", 10.3)
    yol = os.path.join(dizin, "materials.xml")
    openmc.Materials([m]).export_to_xml(yol)
    return yol


def test_malzeme_ice_aktar():
    print("\n[KP4] malzeme ice aktarma: iptal, hata, bos, ad cakismasi, geri al")
    _qt()
    d = tempfile.mkdtemp(prefix="kabuk_proje_")
    p = _pencere(os.path.join(ORNEK, "pwr_pinhucre.json"))
    try:
        n0 = len(p.spec["malzemeler"])
        with _Diyaloglar(acma="") as dg:
            p.malzeme_ice_aktar()
            kontrol("iptal: malzeme eklenmez", len(p.spec["malzemeler"]) == n0 and not dg.cagrilar)
        with _Diyaloglar(acma=os.path.join(d, "yok.xml")) as dg:
            p.malzeme_ice_aktar()
            kontrol("okunamayan dosya: 'Okunamadı'", dg.cagrilar[:1]
                    and dg.cagrilar[0][1] == "Okunamadı")
        bos = os.path.join(d, "bos_materials.xml")
        with open(bos, "w", encoding="utf-8") as f:
            f.write("<?xml version='1.0'?>\n<materials/>\n")
        with _Diyaloglar(acma=bos) as dg:
            p.malzeme_ice_aktar()
            kontrol("malzemesiz dosya: 'Boş' bilgisi",
                    dg.cagrilar[:1] and dg.cagrilar[0][1] == "Boş", "-> %s" % dg.cagrilar)
        mevcut = p.spec["malzemeler"][0]["ad"]
        yol = _materials_xml(d, mevcut)
        with _Diyaloglar(acma=yol) as dg:
            p.malzeme_ice_aktar()
            adlar = [m["ad"] for m in p.spec["malzemeler"]]
            kontrol("ayni adli malzeme yeniden adlandirilarak eklendi",
                    len(adlar) == n0 + 1 and adlar[-1] != mevcut
                    and adlar[-1].startswith(mevcut), "-> %s" % adlar[-2:])
            kontrol("bilgi diyalogu geometri notunu tasiyor",
                    dg.cagrilar and dg.cagrilar[-1][0] == "bilgi"
                    and "geometri" in dg.cagrilar[-1][2].lower())
        p.geri_al()
        kontrol("ice aktarma tek geri al adimi", len(p.spec["malzemeler"]) == n0)
    finally:
        _kapat(p)
        shutil.rmtree(d, True)


def test_disa_aktarma():
    print("\n[KP5] disa aktarma: betik, XML, PNG, rapor dosyasini ac")
    _qt()
    from PySide6 import QtGui
    d = tempfile.mkdtemp(prefix="kabuk_proje_")
    p = _pencere(os.path.join(ORNEK, "pwr_pinhucre.json"))
    try:
        betik = os.path.join(d, "model.py")
        with _Diyaloglar(kayit=betik) as dg:
            p.betik_disa_aktar()
            kontrol("betik yazildi ve bilgi verildi",
                    os.path.exists(betik) and dg.turler() == ["bilgi"]
                    and "satır" in dg.cagrilar[0][2])
        with _Diyaloglar(kayit=os.path.join(d, "yok", "m.py")) as dg:
            p.betik_disa_aktar()
            kontrol("yazilamayan betik: 'Üretilemedi'", dg.turler() == ["hata"])
        with _Diyaloglar(kayit="") as dg:
            p.betik_disa_aktar()
            kontrol("betik iptal: sessiz", not dg.cagrilar)
        with _Diyaloglar(dizin=d) as dg:
            p.xml_disa_aktar()
            kontrol("model.xml yazildi", os.path.exists(os.path.join(d, "model.xml"))
                    and not dg.cagrilar, "-> %s" % dg.cagrilar)
        with _Diyaloglar(dizin=betik) as dg:              # dizin degil, dosya
            p.xml_disa_aktar()
            kontrol("yazilamayan XML dizini: 'Üretilemedi'", dg.turler() == ["hata"],
                    "-> %s" % dg.cagrilar)
        with _Diyaloglar(dizin="") as dg:
            p.xml_disa_aktar()
            kontrol("XML iptal: sessiz", not dg.cagrilar)
        kayitlar = []
        p.onizleme.kaydet = kayitlar.append
        with _Diyaloglar(kayit=os.path.join(d, "g.png")):
            p.png_kaydet()
        with _Diyaloglar(kayit=""):
            p.png_kaydet()
        kontrol("PNG: yalniz secilen yola kaydedilir", kayitlar == [os.path.join(d, "g.png")])
        acilan = []
        eski = QtGui.QDesktopServices.openUrl
        QtGui.QDesktopServices.openUrl = staticmethod(lambda url: acilan.append(url.toLocalFile()))
        try:
            p._dosyayi_ac(betik)
        finally:
            QtGui.QDesktopServices.openUrl = eski
        kontrol("'Aç' eylemi dosyayi sistemde aciyor", acilan == [betik])
    finally:
        _kapat(p)
        shutil.rmtree(d, True)


HIZLI = [test_son_kullanilanlar, test_kaydetme_sorusu, test_ac_kaydet_hatalari,
         test_malzeme_ice_aktar, test_disa_aktarma]
YAVAS = []


if __name__ == "__main__":
    from testler.ortak_test import _gecti, _kaldi
    for fn in HIZLI:
        fn()
    print("\n SONUC: %d gecti, %d kaldi" % (len(_gecti), len(_kaldi)))
    for t in _kaldi:
        print("   - %s" % t)
