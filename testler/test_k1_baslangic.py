# -*- coding: utf-8 -*-
"""
test_k1_baslangic.py -- v3 K1: uc baslangic yolu (Sifirdan / Sablondan /
Ornekten), gercekten bos yeni_spec, adim rehberi, "eksik adim" sunumu,
Calistir kapisinin gerekcesi ve "acilista goster" ayari.

Uctan uca widget akisi (malzeme -> pin -> geometri -> kosu) ayrica:
testler/test_k1_akis.py.
"""

import os

from testler.ortak_test import kontrol, ORNEK
from testler.ortak_test import gereksinim  # v3 izlenebilirlik


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


# ============================================================================
# cekirdek: yeni_spec(kor_turu)
# ============================================================================

@gereksinim("R-V3-01")
def test_yeni_spec_gercekten_bos_yalniz_kor_turu():
    print("\n[K1-1] yeni_spec: gercekten bos, yalniz kor turu secilir")
    from cekirdek import sema
    # Arrange / Act
    varsayilan = sema.yeni_spec("x")
    demet = sema.yeni_spec("y", kor_turu="tek_demet")
    # Assert
    kontrol("varsayilan kor turu tek_cubuk", varsayilan["kor"]["tur"] == "tek_cubuk")
    kontrol("kor_turu verilince o tur kurulur", demet["kor"]["tur"] == "tek_demet")
    kontrol("malzeme / parca / demet / tally YOK",
            all(not demet[k] for k in ("malzemeler", "cubuklar", "plakalar",
                                        "demetler", "tallyler")))
    kontrol("kor dolgusu secilmemis (ornekten bir sey tasinmadi)",
            demet["kor"]["demet"] is None and demet["kor"]["cubuk"] is None
            and not demet["kor"]["harita"])
    try:
        sema.yeni_spec("z", kor_turu="yok_boyle")
        hata = None
    except ValueError as e:
        hata = str(e)
    kontrol("bilinmeyen kor turu ValueError verir", hata is not None and "yok_boyle" in hata,
            "-> %s" % hata)
    iki = sema.yeni_spec("x")
    iki["kor"]["harita"].append(["A"])
    kontrol("yeni_spec her cagride bagimsiz nesne (VARSAYILAN_KOR bozulmaz)",
            not sema.yeni_spec("x")["kor"]["harita"])


# ============================================================================
# saf adim rehberi
# ============================================================================

def test_adim_rehberi_tur_ve_ilerleme():
    print("\n[K1-2] adim rehberi: tura gore adimlar, tamamlananlar isaretli")
    from cekirdek import sema
    from arayuz import baslangic_adim as ba
    from arayuz.baslangic_sablon import bos_sablon
    # Arrange
    pin = sema.yeni_spec("p", kor_turu="tek_cubuk")
    demet = sema.yeni_spec("d", kor_turu="tek_demet")
    # Act
    pin_adim = ba.adimlar(pin)
    demet_adim = ba.adimlar(demet)
    # Assert
    kontrol("pin hucre: malzeme -> parca -> geometri (demet yok)",
            [a.anahtar for a in pin_adim] == ["malzeme", "parca", "geometri"],
            "-> %s" % [a.anahtar for a in pin_adim])
    kontrol("demet: malzeme -> parca -> demet -> geometri",
            [a.anahtar for a in demet_adim] == ["malzeme", "parca", "demet", "geometri"])
    kontrol("bos modelde hicbir adim tamam degil", not any(a.tamam for a in pin_adim))
    kontrol("her adim bir sayfaya gider",
            [a.sekme for a in demet_adim] == ["malzemeler", "parcalar", "demet", "kor"])
    kontrol("siradaki adim malzeme", ba.siradaki(pin).anahtar == "malzeme")

    pin["malzemeler"].append(sema.malzeme("uo2", [], 10.0))
    kontrol("malzeme eklenince ilk adim tamam, siradaki parca",
            ba.adimlar(pin)[0].tamam and ba.siradaki(pin).anahtar == "parca")
    plaka = sema.yeni_spec("pl", kor_turu="tek_plaka")
    kontrol("plaka turunde parca adimi plaka ister",
            "plaka" in ba.adimlar(plaka)[1].aciklama.lower())
    kontrol("sablon (calisan model) eksiksiz: rehber yok",
            not ba.eksik_adimlar(bos_sablon("pin")) and ba.siradaki(bos_sablon("pin")) is None)
    kure = sema.yeni_spec("k", kor_turu="kuresel")
    kontrol("rehbersiz tur (kuresel): adim yok", ba.adimlar(kure) == ())
    kontrol("SIFIRDAN_TURLERI rehberli turler",
            all(ba.adimlar(sema.yeni_spec("t", kor_turu=t)) for t in ba.SIFIRDAN_TURLERI))


def test_eksik_adim_yerleri():
    print("\n[K1-3] eksik adimin sonucu olan hata 'eksik adim' sayilir")
    from cekirdek import dogrula, sema
    from arayuz import baslangic_adim as ba
    from arayuz.baslangic_sablon import bos_sablon
    # Arrange
    spec = sema.yeni_spec("p")
    bulgular = dogrula.tum_kontroller(spec)
    # Act
    adim_bulgusu = [b for b in bulgular if ba.adim_bulgusu_mu(b)]
    # Assert
    kontrol("bos pin modelinde 'cubuk secilmemis' eksik adim sayilir",
            any("çubuk seçilmemiş" in b.mesaj for b in adim_bulgusu), "-> %s" % bulgular)
    tam = bos_sablon("pin")
    tam["kor"]["adim"] = -1.0
    kontrol("tamam modelde hata adim bulgusu sayilmaz",
            not any(ba.adim_bulgusu_mu(b) for b in dogrula.tum_kontroller(tam)))


# ============================================================================
# pencere: uc yol, sunum, kapı
# ============================================================================

def _sifirdan(p, tur="tek_cubuk"):
    b = p.baslangic
    b.sifirdan_turu.setCurrentIndex(b.sifirdan_turu.findData(tur))
    b.d_sifirdan.click()


def test_uc_yol_baslangic_ekraninda():
    print("\n[K1-4] baslangic ekrani: Sifirdan / Sablondan / Ornekten")
    _qt()
    from arayuz.baslangic import BaslangicEkrani
    b = BaslangicEkrani()
    try:
        kontrol("Sifirdan karti ilk sirada, dugmesi var",
                b._kartlar[0] is b.sifirdan_karti and b.d_sifirdan.text() == "Sıfırdan başla")
        kontrol("kor turu secici rehberli turleri listeler",
                b.sifirdan_turu.count() == 5)
        kontrol("tur kartlarinda 'Sablondan' + 'Ornekten'",
                b.kart_dugmesi("pin", "bos").text() == "Şablondan"
                and b.kart_dugmesi("pin", "ornek").text() == "Örnekten")
        yakalanan = []
        b.sifirdan_istendi.connect(yakalanan.append)
        b.sifirdan_turu.setCurrentIndex(b.sifirdan_turu.findData("kare_kafes"))
        b.d_sifirdan.click()
        kontrol("Sifirdan secili kor turunu yayar", yakalanan == ["kare_kafes"],
                "-> %s" % yakalanan)
        kontrol("'acilista goster' kutusu var ve varsayilan isaretli",
                b.acilista_goster.isChecked())
    finally:
        b.deleteLater()


@gereksinim("R-V3-01")
def test_sifirdan_eksik_adim_sunumu_ve_kapi():
    print("\n[K1-5] Sifirdan: bos model, bilgi tonu 'eksik adim', Calistir kapali + neden")
    _qt()
    from PySide6 import QtGui
    from arayuz import tema
    p = _pencere()
    try:
        # Arrange / Act
        _sifirdan(p, "tek_cubuk")
        p._dogrula()
        # Assert
        kontrol("editor acildi, Malzemeler sayfasi", not p.baslangic_acik_mi()
                and p.gecerli_sekme() == "malzemeler")
        kontrol("model gercekten bos (ornek yok)",
                not p.spec["malzemeler"] and not p.spec["cubuklar"] and p.ornek_kaynagi is None)
        kontrol("serit bilgi tonunda (hata kirmizisi degil)",
                p.serit.rozet.property("rozet") == "bilgi", "-> %s" % p.serit.rozet.property("rozet"))
        kontrol("serit 'eksik adim' soyler", "aşama" in p.serit.ozet.text(),
                "-> %s" % p.serit.ozet.text())
        izin, neden = p._kosu_izni()
        kontrol("Calistir kapali", not izin)
        kontrol("ust cubuktaki Calistir dugmesi de kapali, ipucu nedeni soyler",
                not p.ust.d_kosu.isEnabled() and p.ust.d_kosu.toolTip() == neden,
                "-> %s / %s" % (p.ust.d_kosu.isEnabled(), p.ust.d_kosu.toolTip()))
        kontrol("seritte Calistir'in neden kapali oldugu yazar",
                "Çalıştır" in p.serit.ipucu.text(), "-> %s" % p.serit.ipucu.text())
        kontrol("neden acik: eksik adim + siradaki", "Malzeme" in neden and "aşama" in neden,
                "-> %s" % neden)
        renkler = {p.dogrulama.item(i).foreground().color().name()
                   for i in range(p.dogrulama.count())}
        kontrol("bulgu listesinde hata kirmizisi yok",
                QtGui.QColor(tema.renk("hata")).name() not in renkler, "-> %s" % renkler)
        kontrol("kenar cubugunda Geometri 'hata' degil",
                p._isaretler["kor"][0] != "!", "-> %s" % (p._isaretler["kor"],))
        r = p.adim_rehberi
        kontrol("adim rehberi gorunur, 3 adim", not r.isHidden() and len(r.dugmeler) == 3)
        r.dugmeler["parca"].click()
        kontrol("rehber adimi tiklaninca ilgili sayfaya gider", p.gecerli_sekme() == "parcalar")
        p.serit.d_bulgu.click()
        kontrol("seritteki 'Bulguya git' siradaki adima gider",
                p.gecerli_sekme() == "malzemeler")
        p.e_yeni.trigger()
        kontrol("baslangic ekraninda rehber gizli", p.adim_rehberi.isHidden())
        p.baslangic.kart_dugmesi("pin", "bos").click()
        kontrol("Sablondan calisan model: rehber gizli", p.adim_rehberi.isHidden()
                and p.spec["malzemeler"])
    finally:
        _kapat(p)


def test_acilista_goster_ayari():
    print("\n[K1-6] 'acilista goster' kapaliysa son proje acilir; listede kalir")
    import shutil
    import tempfile
    _qt()
    from arayuz import baslangic_akis
    gecici = tempfile.mkdtemp()
    yol = os.path.join(gecici, "benim.json")
    shutil.copy(os.path.join(ORNEK, "pwr_pinhucre.json"), yol)
    p = _pencere()
    try:
        p.ayarlar.setValue("son_dosyalar", [yol])
        p.baslangic.acilista_goster.setChecked(False)
        kontrol("kutu ayari yazar",
                not baslangic_akis.acilista_goster_mi(p.ayarlar))
    finally:
        _kapat(p)
    p = _pencere()
    try:
        kontrol("ayar kapali: son proje dogrudan acildi",
                not p.baslangic_acik_mi() and p.proje_yolu == os.path.abspath(yol))
        kontrol("son kullanilanlarda kalir", yol in p._son_listesi())
        p.e_yeni.trigger()
        kontrol("baslangic ekraninda kutu ayari yansitir",
                not p.baslangic.acilista_goster.isChecked())
        p.baslangic.acilista_goster.setChecked(True)
    finally:
        _kapat(p)
    p = _pencere()
    try:
        kontrol("ayar acik: baslangic ekrani", p.baslangic_acik_mi())
    finally:
        _kapat(p)
        p0 = _pencere()
        p0.ayarlar.remove("son_dosyalar")
        _kapat(p0)
        shutil.rmtree(gecici, ignore_errors=True)


HIZLI = [test_yeni_spec_gercekten_bos_yalniz_kor_turu, test_adim_rehberi_tur_ve_ilerleme,
         test_eksik_adim_yerleri, test_uc_yol_baslangic_ekraninda,
         test_sifirdan_eksik_adim_sunumu_ve_kapi, test_acilista_goster_ayari]
YAVAS = []
