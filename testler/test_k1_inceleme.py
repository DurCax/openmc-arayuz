# -*- coding: utf-8 -*-
"""
test_k1_inceleme.py -- v3 K1 inceleme bulgulari (python-reviewer):

  HIGH-1  eksik asamanin sayfasindaki GERCEK hatalar bilgi tonuna dusmez:
          ayiklama yalniz bilinen bosluk bulgularinin KODUNA bakar
          (Bulgu.kod = "bos_adim:<asama>"), yer onekine ya da metne degil.
  HIGH-2  aşamayla ilgisiz sayfadaki gercek hata seritte normal hata olarak
          gorunur; "Bulguya git" once gercek hataya gider.
  MEDIUM  kapi mesaji gercek hatayi soyler; editore donuste kapi yeniden
          uygulanir; listede bosluk bulgusu tekrarlanmaz; acilis akisi
          (komut satiri dosyasi, bozuk son proje, son proje yok, ayar degeri).
"""

import os
import shutil
import tempfile

from testler.ortak_test import kontrol


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


def _sifirdan(p, tur="tek_cubuk"):
    b = p.baslangic
    b.sifirdan_turu.setCurrentIndex(b.sifirdan_turu.findData(tur))
    b.d_sifirdan.click()


def _maskelenen(spec):
    from cekirdek import dogrula
    from arayuz import baslangic_adim as ba
    return [b.mesaj for b in dogrula.tum_kontroller(spec) if ba.adim_bulgusu_mu(b)]


def _hatalar(spec):
    from cekirdek import dogrula
    return [b.mesaj for b in dogrula.tum_kontroller(spec) if b.seviye == "hata"]


# ============================================================================
# HIGH-1: gercek hata ayiklanmaz
# ============================================================================

def test_bosluk_bulgulari_kodlu():
    print("\n[K1I-1] bilinen bosluk bulgulari kodlu; Bulgu.kod geri uyumlu")
    from cekirdek import dogrula, sema
    from cekirdek.dogrula import Bulgu
    # Arrange / Act
    eski = Bulgu("hata", "kor", "x")
    kodlar = {}
    for tur in ("tek_cubuk", "tek_demet", "tek_plaka", "kare_kafes", "altigen_kafes"):
        kodlar[tur] = [b.kod for b in dogrula.tum_kontroller(sema.yeni_spec("t", tur))
                       if b.seviye == "hata"]
    # Assert
    kontrol("kodsuz Bulgu kurulabilir (kod None)", eski.kod is None)
    kontrol("bos modelin her hatasi bos_adim:geometri kodlu",
            all(k and all(x == dogrula.BOS_ADIM_GEOMETRI for x in k)
                for k in kodlar.values()), "-> %s" % kodlar)


def test_gercek_hata_ayiklanmaz_tek_cubuk():
    print("\n[K1I-2] tek_cubuk: kor.adim=-1 gercek hata, asama eksikken de hata")
    from cekirdek import sema
    # Arrange
    spec = sema.yeni_spec("p", "tek_cubuk")
    spec["kor"]["adim"] = -1.0
    # Act
    maske = _maskelenen(spec)
    # Assert
    kontrol("'çubuk seçilmemiş' ayiklanir", "çubuk seçilmemiş" in maske, "-> %s" % maske)
    kontrol("'hücre adımı sıfırdan büyük olmalı' ayiklanMAZ",
            "hücre adımı sıfırdan büyük olmalı" not in maske
            and "hücre adımı sıfırdan büyük olmalı" in _hatalar(spec))


def test_gercek_hata_ayiklanmaz_kafes():
    print("\n[K1I-3] kafes: gecersiz adim / sinir gercek hata kalir")
    from cekirdek import sema
    # Arrange
    alt = sema.yeni_spec("a", "altigen_kafes")
    alt["kor"]["adim"] = -1.0
    kare = sema.yeni_spec("k", "kare_kafes")
    kare["kor"]["sinir"]["yan"] = "bozuk"
    # Act / Assert
    kontrol("altigen: 'demet adımı' hatasi ayiklanmaz",
            not any("demet adımı" in m for m in _maskelenen(alt))
            and any("demet adımı" in m for m in _hatalar(alt)))
    kontrol("kare: sinir hatasi ayiklanmaz, 'kor haritası boş' ayiklanir",
            not any("sınır" in m for m in _maskelenen(kare))
            and "kor haritası boş" in _maskelenen(kare))


def test_gercek_hata_ayiklanmaz_plaka():
    print("\n[K1I-4] tek_plaka: parca asamasi eksikken cubuk hatasi gercek kalir")
    from cekirdek import sema
    # Arrange
    spec = sema.yeni_spec("pl", "tek_plaka")
    spec["malzemeler"].append(sema.malzeme("su", [], 1.0))
    spec["cubuklar"].append(sema.cubuk("c", [sema.bolge(-0.3, "su"), sema.bolge(None, "su")]))
    # Act
    maske = _maskelenen(spec)
    # Assert
    kontrol("cubuk bolge hatasi ayiklanmaz", not any("yarıçap" in m for m in maske)
            and any("yarıçap" in m for m in _hatalar(spec)), "-> %s" % maske)


# ============================================================================
# HIGH-2 + MEDIUM: serit, kapi, liste
# ============================================================================

def test_ilgisiz_gercek_hata_seritte():
    print("\n[K1I-5] eksik asama + ilgisiz gercek hata: serit hata, kapi hatayi soyler")
    _qt()
    p = _pencere()
    try:
        # Arrange
        _sifirdan(p)
        p.spec["ayarlar"]["parcacik"] = 0
        # Act
        p._dogrula()
        izin, neden = p._kosu_izni()
        # Assert
        kontrol("serit hata tonunda", p.serit.rozet.property("rozet") == "hata",
                "-> %s" % p.serit.rozet.property("rozet"))
        kontrol("asama bilgisi ipucunda kalir", "Malzeme" in p.serit.ipucu.text(),
                "-> %s" % p.serit.ipucu.text())
        kontrol("kapi kapali ve gercek hatayi soyler", not izin and "hata" in neden,
                "-> %s" % neden)
        p.serit.d_bulgu.click()
        kontrol("'Bulguya git' once gercek hataya gider", p.gecerli_sekme() == "ayarlar",
                "-> %s" % p.gecerli_sekme())
    finally:
        _kapat(p)


def test_liste_tekrarsiz_ve_kapi_geri_donuste():
    print("\n[K1I-6] liste: bosluk bulgusu yok, asama satiri var; editore donuste kapi")
    _qt()
    p = _pencere()
    try:
        # Arrange / Act
        _sifirdan(p)
        p._dogrula()
        metinler = [p.dogrulama.item(i).text() for i in range(p.dogrulama.count())]
        # Assert
        kontrol("'çubuk seçilmemiş' listede tekrarlanmaz",
                not any("çubuk seçilmemiş" in m for m in metinler), "-> %s" % metinler)
        kontrol("asama satirlari listede (3)", len(metinler) >= 3, "-> %s" % metinler)
        p.e_yeni.trigger()
        p.baslangic.geri_istendi.emit()
        kontrol("editore donuste ust cubuk Calistir kapali",
                not p.baslangic_acik_mi() and not p.ust.d_kosu.isEnabled())
    finally:
        _kapat(p)


# ============================================================================
# MEDIUM-6: acilis akisi
# ============================================================================

def _ayarla(son, goster):
    from PySide6 import QtCore
    a = QtCore.QSettings("openmc_arayuz", "arayuz")
    a.setValue("son_dosyalar", son)
    a.setValue("baslangic/acilista_goster", goster)
    a.sync()


def _ayar_temizle():
    from PySide6 import QtCore
    a = QtCore.QSettings("openmc_arayuz", "arayuz")
    a.remove("son_dosyalar")
    a.remove("baslangic/acilista_goster")
    a.sync()


def test_acilis_akisi_kenar_durumlari():
    print("\n[K1I-7] acilis: komut satiri dosyasi, bozuk son proje, son proje yok")
    _qt()
    from PySide6 import QtWidgets
    from arayuz import baslangic_akis
    gecici = tempfile.mkdtemp()
    bozuk = os.path.join(gecici, "bozuk.json")
    with open(bozuk, "w", encoding="utf-8") as f:
        f.write("{bozuk")
    eski = QtWidgets.QMessageBox.critical
    QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **k: None)
    try:
        _ayarla([bozuk], False)
        p = _pencere()
        kontrol("bozuk son proje: baslangic ekrani", p.baslangic_acik_mi())
        _kapat(p)
        _ayarla([], False)
        p = _pencere()
        kontrol("ayar kapali + son proje yok: baslangic ekrani", p.baslangic_acik_mi())
        _kapat(p)
        iyi = os.path.join(gecici, "iyi.json")
        shutil.copy(os.path.join(os.path.dirname(__file__), "..", "ornekler",
                                 "pwr_pinhucre.json"), iyi)
        _ayarla([iyi], False)
        p = _pencere(os.path.join(gecici, "yok.json"))
        kontrol("komut satiri dosyasi verildi (acilamadi): son proje denenmez",
                p.baslangic_acik_mi() and p.proje_yolu is None, "-> %s" % p.proje_yolu)
        kontrol("on kanca listesi var (K2 icin)", isinstance(p._acilis_on_kancalari, list))
        _kapat(p)
        from PySide6 import QtCore
        a = QtCore.QSettings("openmc_arayuz", "arayuz")
        a.setValue("baslangic/acilista_goster", "")
        kontrol("bos deger varsayilan (goster)", baslangic_akis.acilista_goster_mi(a))
        a.setValue("baslangic/acilista_goster", "false")
        kontrol("'false' kapali", not baslangic_akis.acilista_goster_mi(a))
    finally:
        QtWidgets.QMessageBox.critical = eski
        _ayar_temizle()
        shutil.rmtree(gecici, ignore_errors=True)


def test_on_kanca_once_calisir():
    print("\n[K1I-8] acilis on kancalari baslangic seciminden ONCE cagrilir")
    _qt()
    from arayuz.pencere.ana_pencere import AnaPencere
    sira = []
    eski_goster = AnaPencere.baslangici_goster

    def goster(self):
        sira.append("baslangic")
        return eski_goster(self)
    AnaPencere.baslangici_goster = goster
    try:
        p = AnaPencere.__new__(AnaPencere)
        AnaPencere.__init__(p)
        sira.clear()
        p._acilis_on_kancalari.append(lambda: sira.append("veri"))
        p.acilis_akisi()
        kontrol("sira: veri -> baslangic", sira == ["veri", "baslangic"], "-> %s" % sira)
    finally:
        AnaPencere.baslangici_goster = eski_goster
        _kapat(p)


HIZLI = [test_bosluk_bulgulari_kodlu, test_gercek_hata_ayiklanmaz_tek_cubuk,
         test_gercek_hata_ayiklanmaz_kafes, test_gercek_hata_ayiklanmaz_plaka,
         test_ilgisiz_gercek_hata_seritte, test_liste_tekrarsiz_ve_kapi_geri_donuste,
         test_acilis_akisi_kenar_durumlari, test_on_kanca_once_calisir]
YAVAS = []
