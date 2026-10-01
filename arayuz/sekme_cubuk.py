# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_cubuk.py  --  Parcalar sekmesi: cubuklar ve plaka elemanlari
================================================================================
 Solda parca listesi, sagda secili parcanin editoru.
   Silindirik cubuk : es merkezli radyal bolgeler (son bolge "dis bolge")
   Plaka eleman     : MTR tipi duz plaka istifi

 YALNIZCA MODELDE ANLAMLI OLAN SUNULUR (cekirdek/uygunluk.parca_turleri)
   "+ Cubuk"  cubuk kullanan kor turlerinde; bir SABLON menusu acar:
              PWR yakit cubugu / Kilavuz boru / Kontrol cubugu (sonuncusu
              yalnizca 3B ve kafesli modelde).
   "+ Plaka"  yalnizca plaka modelinde.
   Hic malzeme yokken ekleme dugmeleri kapalidir.
   Emici bolge listesinde dis bolge, izleyici listesinde yakit/emici,
   plaka listelerinde role uymayan malzeme yoktur (dosyadan gelen mevcut
   deger yine gosterilir -- veri sessizce degismez).

 SABLONLAR MALZEMEYI ROLUNDEN SECER (uygunluk.rol_malzemeleri)
   yakit -> yakit, zarf -> yapisal (cubukta Zr, plakada Al tercihli),
   dis -> sogutucu, yakit-zarf araligi -> gaz ya da Bos (madde yok).
   Rolu karsilayan malzeme yoksa bolgenin malzemesi None kalir ve arayuzde
   "Malzeme secin" olarak ACIKCA isaretlenir (kurucu None'i bosluk olarak
   kurar; sessizce bosluga donusmesin diye kirmizi gosterilir).

 BOLGE TABLOSU
   Yaricaplar artan sirada ZORUNLU: her kutunun alt/ust siniri komsularindan
   gelir. "Ice/Disa tasi" yalnizca MALZEMEYI tasir, yaricaplar yerinde kalir
   (eskiden yaricaplar da yer degistirip sira bozuluyordu).

 AD DEGISIMI butun referanslari gunceller (parca_adini_degistir): kafes
   anahtarlari, kor cubuk/plaka/demet/dolgu, kor haritasi anahtari, eksenel
   katman dolgusu ve anahtari, guc dagilimi cubugu. sekme_demet de kullanir.
================================================================================
"""

import copy
import json
import re

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import sema, uygunluk
from cekirdek.ceviri import _
from arayuz import bilesenler as bl
from arayuz import sekme_duzen as sd
from arayuz.tasarim import tokenlar
from arayuz.ortak import BosDurum, SekmeTabani, baslik, ipucu, renk_simgesi, sayi, tamsayi

# Bolunen parcalar (Dalga 0): eski ad alani aynen korunur.
from arayuz.cubuk.parca_islemleri import (  # noqa: F401
    BOS_ETIKETI, SECILMEDI_ETIKETI, MALZEME_YOK_IPUCU, ROL_ADI, CUBUK_SABLONLARI, _renk,
    _ROL_ONBELLEK, roller, rol_listesi, _elementler, rol_malzemesi, cubuk_sablonu,
    _SABLON_ROLLERI, sablon_eksik_roller, plaka_sablonu, _tanimli, eksik_malzemeler,
    _konum_adi, bolge_aciklamasi, malzeme_etiketi, _betik_adi, ad_hatasi, benzersiz_ad,
    _parca_bul, parca_adini_degistir, parca_kullanimlari, kor_dolgusu_bos_mu, parca_rengi)
from arayuz.cubuk.malzeme_kutusu import (  # noqa: F401
    MalzemeKutusu, _SatirTakibi)
from arayuz.cubuk.sayfalar import (  # noqa: F401
    SayfalarMixin)
from arayuz.cubuk.cubuk_formu import (  # noqa: F401
    CubukFormuMixin)
from arayuz.cubuk.plaka_formu import (  # noqa: F401
    PlakaFormuMixin)


# ============================================================================
# sekme
# ============================================================================

class CubukSekmesi(SayfalarMixin, CubukFormuMixin, PlakaFormuMixin, SekmeTabani):
    """Cubuk ve plaka tanimlari."""

    KONU = "cubuk"

    def __init__(self, parent=None):
        super().__init__(parent)

        sol = self._liste_karti()

        # --- sag: editor yigini ---
        self.bos = BosDurum(_("Henüz parça yok"), "", _("Yakıt çubuğu ekle"))
        self.bos.eylem.connect(self._bos_eylem)
        self.yigin = QtWidgets.QStackedWidget()
        self.yigin.addWidget(self.bos)
        self.cubuk_sayfa = self._cubuk_sayfa()
        self.plaka_sayfa = self._plaka_sayfa()
        self.yigin.addWidget(self.cubuk_sayfa)
        self.yigin.addWidget(self.plaka_sayfa)

        bolucu = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        bolucu.addWidget(sol)
        bolucu.addWidget(self.yigin)
        bolucu.setStretchFactor(0, 0)
        bolucu.setStretchFactor(1, 1)
        bolucu.setSizes([210, 520])
        bolucu.setChildrenCollapsible(False)
        bolucu.setHandleWidth(tokenlar.ARALIK["m"])

        duzen = sd.sayfa_duzeni(self)
        duzen.addWidget(sd.sayfa_basligi(
            _("Parçalar"), _("Çubuklar ve plaka elemanları: radyal bölgeler ve malzemeler."),
            bolum="parcalar"))
        duzen.addWidget(bolucu, 1)

    # ------------------------------------------------------------------
    def _liste_karti(self):
        """Sol kart: parca listesi + sablon menusu ve islem dugmeleri."""
        self.liste = QtWidgets.QListWidget()
        self.liste.setIconSize(QtCore.QSize(14, 14))
        self.liste.setAlternatingRowColors(True)
        self.liste.currentRowChanged.connect(self._secim_degisti)
        self.d_cubuk = bl.ikincil_dugme(_("Çubuk"), "cylinder")
        self.cubuk_menusu = QtWidgets.QMenu(self.d_cubuk)
        self.sablon_eylemleri = {}
        for anahtar, metin, _ad in CUBUK_SABLONLARI:
            e = self.cubuk_menusu.addAction(_(metin))
            e.triggered.connect(lambda _c=False, a=anahtar: self.cubuk_ekle(a))
            self.sablon_eylemleri[anahtar] = e
        self.sablon_eylemleri["yakit"].setToolTip(_(
            "Yakıt, yakıt-zarf aralığı, zarf ve soğutucu; malzemeler rollerine göre seçilir."))
        self.sablon_eylemleri["kilavuz"].setToolTip(_(
            "Suyla dolu kılavuz boru (zarf + soğutucu)."))
        self.sablon_eylemleri["kontrol"].setToolTip(_(
            "Kılavuz borusunda eksenel hareket eden emici çubuk (3B model)."))
        self.cubuk_menusu.setToolTipsVisible(True)
        self.d_cubuk.setMenu(self.cubuk_menusu)
        self.d_plaka = bl.ikincil_dugme(_("Plaka"), "layers")
        self.d_kopya = bl.duz_dugme(_("Kopyala"), "copy")
        self.d_sil = bl.tehlikeli_dugme(_("Sil"), "trash")
        self.d_plaka.clicked.connect(self.plaka_ekle)
        self.d_kopya.clicked.connect(self._kopyala)
        self.d_sil.clicked.connect(self._sil)
        self.liste_karti = bl.Kart(_("Parçalar"))
        self.liste_karti.ekle(self.liste, 1)
        self.liste_karti.ekle(sd.satir(self.d_cubuk, self.d_plaka))
        self.liste_karti.ekle(sd.satir(self.d_kopya, self.d_sil))
        return self.liste_karti

    # ------------------------------------------------------------------
    # doldurma
    # ------------------------------------------------------------------
    def doldur(self):
        onceki = self._secili()
        self.liste.blockSignals(True)
        self.liste.clear()
        for c in self.spec.get("cubuklar", []):
            ek = _("  · kontrol") if c.get("tur") == "kontrol" else ""
            oge = QtWidgets.QListWidgetItem(renk_simgesi(parca_rengi(self.spec, c)),
                                            c["ad"] + ek)
            oge.setData(QtCore.Qt.UserRole, ("cubuk", c["ad"]))
            self._liste_isareti(oge, c)
            self.liste.addItem(oge)
        for p in self.spec.get("plakalar", []):
            oge = QtWidgets.QListWidgetItem(renk_simgesi(parca_rengi(self.spec, p)),
                                            p["ad"] + _("  · plaka"))
            oge.setData(QtCore.Qt.UserRole, ("plaka", p["ad"]))
            self._liste_isareti(oge, p)
            self.liste.addItem(oge)
        hedef = 0
        for i in range(self.liste.count()):
            if self.liste.item(i).data(QtCore.Qt.UserRole) == onceki:
                hedef = i
        if self.liste.count():
            self.liste.setCurrentRow(hedef)
        self.liste.blockSignals(False)
        self._secim_degisti(self.liste.currentRow())
        self._eylemleri_guncelle()

    def _liste_isareti(self, oge, parca):
        eksik = eksik_malzemeler(self.spec, parca)
        if eksik:
            oge.setText(oge.text() + "  ⚠")
            oge.setForeground(QtGui.QColor(_renk("hata")))
            oge.setToolTip(_("Malzemesi seçilmemiş: {eksik}").format(eksik=", ".join(eksik)))

    def _eylemleri_guncelle(self):
        """Ekleme dugmeleri yalnizca bu modelde anlamli parcalar icin."""
        spec = self.spec or sema.yeni_spec()
        turler = uygunluk.parca_turleri(spec)
        malzeme_var = bool(spec.get("malzemeler"))
        self.d_cubuk.setVisible(turler["cubuk"])
        self.d_plaka.setVisible(turler["plaka"])
        self.sablon_eylemleri["kontrol"].setVisible(turler["kontrol_cubugu"])
        for d, metin in ((self.d_cubuk, _("Şablondan çubuk ekler; malzemeler rollerine "
                                         "göre otomatik seçilir.")),
                         (self.d_plaka, _("MTR plaka elemanı ekler; malzemeler rollerine "
                                          "göre otomatik seçilir."))):
            d.setEnabled(malzeme_var)
            d.setToolTip(metin if malzeme_var else _(MALZEME_YOK_IPUCU))
        secili = self._secili()[0] is not None
        self.d_kopya.setEnabled(secili)
        self.d_sil.setEnabled(secili)
        self._bos_durum_guncelle(turler, malzeme_var)

    def _bos_durum_guncelle(self, turler, malzeme_var):
        if not malzeme_var:
            self.bos.ayarla(_("Önce malzeme gerekli"),
                            _("Parçalar malzemelerden kurulur. Malzemeler sekmesinden "
                              "yakıt, zarf ve soğutucu malzemelerini ekleyin."), "")
        elif self.liste.count():
            self.bos.ayarla(_("Bir parça seçin"),
                            _("Düzenlemek için soldaki listeden bir parça seçin."), "")
        elif turler["plaka"]:
            self.bos.ayarla(_("Henüz parça yok"),
                            _("Plaka elemanı ekleyin; malzemeler rollerine göre "
                              "otomatik seçilir."), _("Plaka elemanı ekle"))
        elif turler["cubuk"]:
            self.bos.ayarla(_("Henüz parça yok"),
                            _("Soldaki '+ Çubuk' menüsünden bir şablon seçin; malzemeler "
                              "rollerine göre (yakıt, zarf, soğutucu) otomatik seçilir."),
                            _("Yakıt çubuğu ekle"))
        else:
            self.bos.ayarla(_("Bu model parça kullanmıyor"),
                            _("Bu kor türünde çubuk ya da plaka tanımlanmaz."), "")

    def _bos_eylem(self):
        if uygunluk.parca_turleri(self.spec)["plaka"]:
            self.plaka_ekle()
        else:
            self.cubuk_ekle("yakit")

    def _secili(self):
        oge = self.liste.currentItem()
        return oge.data(QtCore.Qt.UserRole) if oge else (None, None)

    def _secim_degisti(self, _satir):
        tur, ad = self._secili()
        eski = self._yukleniyor
        self._yukleniyor = True
        try:
            if tur == "cubuk" and sema.cubuk_bul(self.spec, ad) is not None:
                self._cubuk_doldur(sema.cubuk_bul(self.spec, ad))
                self.yigin.setCurrentWidget(self.cubuk_sayfa)
            elif tur == "plaka" and sema.plaka_bul(self.spec, ad) is not None:
                self._plaka_doldur(sema.plaka_bul(self.spec, ad))
                self.yigin.setCurrentWidget(self.plaka_sayfa)
            else:
                self.yigin.setCurrentWidget(self.bos)
        finally:
            self._yukleniyor = eski
        secili = tur is not None
        self.d_kopya.setEnabled(secili)
        self.d_sil.setEnabled(secili)

    # ------------------------------------------------------------------
    # ad degisimi
    # ------------------------------------------------------------------
    def _ad_degisti(self, tur_):
        tur, ad = self._secili()
        if tur != tur_:
            return
        alan, hata_etiketi = ((self.c_ad, self.c_ad_hata) if tur == "cubuk"
                              else (self.p_ad, self.p_ad_hata))
        yeni = alan.text().strip()
        if yeni == ad:
            self._hata_goster(hata_etiketi, "")
            return
        hata = ad_hatasi(self.spec, yeni, ad)
        if hata:
            alan.setText(ad)
            self._hata_goster(hata_etiketi, _("{hata} Ad değiştirilmedi.").format(hata=hata))
            return
        parca_adini_degistir(self.spec, ad, yeni)
        self.spec_yukle(self.spec)
        self._sec((tur, yeni))
        # Ad; kafes, kor ve HESAP AYARLARI (guc dagilimi cubugu) sekmelerinde
        # de gecer: hepsi yeniden yuklensin ("cubuk" konusu ayarlari tazelemez).
        if not self._yukleniyor:
            self.degisti.emit("genel")

    # ------------------------------------------------------------------
    # liste islemleri
    # ------------------------------------------------------------------
    def _onay_al(self, baslik_, metin):
        """Veri silen islemler icin onay. Testler bunu degistirir (modal acilmaz)."""
        cevap = QtWidgets.QMessageBox.question(
            self, baslik_, metin,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)
        return cevap == QtWidgets.QMessageBox.Yes

    def _kora_ata(self, alan, ad):
        """Kor bu tur parcayi istiyor ve henuz secilmemisse yeni parcayi ata
        (bos modelde ilk cubuk eklenince pin hucre hemen kurulur)."""
        kor = self.spec.get("kor") or {}
        istenen = {"tek_cubuk": "cubuk", "tek_plaka": "plaka"}.get(kor.get("tur"))
        if istenen == alan and kor_dolgusu_bos_mu(self.spec, alan):
            kor[alan] = ad

    def cubuk_ekle(self, sablon="yakit"):
        """Sablondan cubuk ekler; malzemeler rollerine gore secilir."""
        if not self.spec.get("malzemeler"):
            return None
        taban = dict((a, v) for a, _m, v in CUBUK_SABLONLARI)[sablon]
        ad = benzersiz_ad(self.spec, taban)
        self.spec.setdefault("cubuklar", []).append(cubuk_sablonu(self.spec, sablon, ad))
        self._kora_ata("cubuk", ad)
        self.spec_yukle(self.spec)
        self._sec(("cubuk", ad))
        self._sablon_eksigi(self.c_eksik, sablon)
        self.bildir()
        return ad

    def _sablon_eksigi(self, etiket, sablon):
        """Sablonun rolunu karsilayan malzeme yoksa bunu ADIYLA soyle."""
        eksik = sablon_eksik_roller(self.spec, sablon)
        if eksik:
            self._hata_goster(etiket, _(
                "Bu modelde {roller} rolünde malzeme yok; ilgili bölgeler kırmızı "
                "işaretli. Önce Malzemeler sekmesinden ekleyin, sonra burada seçin."
            ).format(roller=" / ".join(eksik)))

    def plaka_ekle(self):
        if not self.spec.get("malzemeler"):
            return None
        ad = benzersiz_ad(self.spec, "plaka_eleman")
        self.spec.setdefault("plakalar", []).append(plaka_sablonu(self.spec, ad))
        self._kora_ata("plaka", ad)
        self.spec_yukle(self.spec)
        self._sec(("plaka", ad))
        self._sablon_eksigi(self.p_eksik, "plaka")
        self.bildir()
        return ad

    def _sec(self, anahtar):
        for i in range(self.liste.count()):
            if self.liste.item(i).data(QtCore.Qt.UserRole) == anahtar:
                self.liste.setCurrentRow(i)
                return

    def komutlar(self):
        return sd.dugme_komutlari(self, _("Parça"), (
            self.d_cubuk, self.d_plaka, self.d_kopya, self.d_sil))

    def odakla(self, yer):
        """"cubuk:<ad>" / "plaka:<ad>" bulgusunda o parcayi secer."""
        hedef = sd.yer_adi(yer, "cubuk", "plaka")
        if hedef is None:
            return False
        self._sec(hedef)
        return tuple(self._secili()) == hedef

    def _kopyala(self):
        tur, ad = self._secili()
        if tur == "cubuk":
            y = copy.deepcopy(sema.cubuk_bul(self.spec, ad))
            y["ad"] = benzersiz_ad(self.spec, ad)
            self.spec["cubuklar"].append(y)
        elif tur == "plaka":
            y = copy.deepcopy(sema.plaka_bul(self.spec, ad))
            y["ad"] = benzersiz_ad(self.spec, ad)
            self.spec["plakalar"].append(y)
        else:
            return
        self.spec_yukle(self.spec)
        self._sec((tur, y["ad"]))
        self.bildir()

    def _sil(self):
        tur, ad = self._secili()
        if tur is None:
            return
        yerler = parca_kullanimlari(self.spec, ad)
        if yerler and not self._onay_al(
                _("Parça kullanılıyor"),
                _("'{ad}' şurada kullanılıyor: {yerler}.\n\nSilinirse bu yerler tanımsız bir "
                  "parçaya işaret eder ve doğrulama hata verir. Silinsin mi?"
                  ).format(ad=ad, yerler=", ".join(yerler))):
            return
        liste = self.spec["cubuklar"] if tur == "cubuk" else self.spec["plakalar"]
        for i, o in enumerate(liste):
            if o["ad"] == ad:
                liste.pop(i)
                break
        self.spec_yukle(self.spec)
        self.bildir()
