# -*- coding: utf-8 -*-
"""
 arayuz/malzeme/asistan.py  --  MalzemeAsistani: adim adim malzeme tasarimi

   1. "Ne tasarlıyorsun?"  yakit / kilif / moderator / emici / yapi / ozel
   2. Tarif ve degerler    alanlar (cekirdek/malzeme_tarif) + ANINDA turetilmis
                           degerler (TuretilmisPanel); gecersiz deger Ileri'yi kapatir
   3. Dogrulama ve kaydet  dogrula_malzeme bulgulari (hata varsa Bitir kapali),
                           ad, "Projeye ekle", "Kütüphaneme de kaydet"

 Hesap ve kurallar cekirdektedir; bu dosya yalnizca akisi kurar.
"""

from PySide6 import QtCore, QtWidgets

from cekirdek import malzeme_kullanici as mku
from cekirdek import malzeme_tarif as mt
from cekirdek import sema
from cekirdek.ceviri import _, pgettext
from cekirdek.gunluk import kaydedici
from arayuz import bilesenler as b
from arayuz.ortak import baslik, ipucu
from arayuz.malzeme.tarif_formu import KarisimFormu, TarifFormu
from arayuz.malzeme.turetilmis_panel import TuretilmisPanel
from arayuz.malzeme.yardimcilar import _benzersiz_ad, _etiket, _hata_etiketi
from arayuz.tasarim import tokenlar

_log = kaydedici(__name__)
A = tokenlar.ARALIK

_IKON = {"yakit": "atom", "kilif": "cylinder", "moderator": "flask-conical",
         "emici": "shield", "yapi": "box", "ozel": "layers"}
_SEVIYE_IMI = {"hata": "✖", "uyari": "⚠", "bilgi": "ℹ"}
_SAYFA_KATEGORI, _SAYFA_TARIF, _SAYFA_DOGRULA = 0, 1, 2
_KATEGORI_SUTUNU = 3
_KATEGORI_DUGME_KATI = 2      # kategori dugmesi = 2 x standart dugme yuksekligi


def _kutuphane_malzemeleri():
    """Karisim icin kullanici kutuphanesindeki malzemeler; okunamazsa bos (loglanir)."""
    try:
        return [(_("Kütüphanem: %s") % k["ad"], k["malzeme"]) for k in mku.yukle()]
    except mku.KutuphaneHatasi as e:
        _log.warning("karisim listesi: kullanici kutuphanesi okunamadi: %s", e)
        return []


class MalzemeAsistani(QtWidgets.QDialog):

    def __init__(self, spec=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Malzeme asistanı"))
        self.resize(940, 640)
        self._spec = spec if spec is not None else sema.yeni_spec()
        self.kategori = self.form = None
        self.bulgular = []
        self._taslak, self._sorun = None, None
        self.yigin = QtWidgets.QStackedWidget()
        self.yigin.addWidget(self._kategori_sayfasi())
        self.yigin.addWidget(self._tarif_sayfasi())
        self.yigin.addWidget(self._dogrulama_sayfasi())
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(self.yigin, 1)
        duzen.addLayout(self._dugmeler())
        self._adim_guncelle()

    # ------------------------------------------------------------ sayfalar
    def _kategori_sayfasi(self):
        w = QtWidgets.QWidget()
        d = QtWidgets.QVBoxLayout(w)
        d.addWidget(baslik(_("Ne tasarlıyorsun?")))
        d.addWidget(ipucu(_("Malzemenin rolünü seçin; sonraki adımda yalnızca o role uygun "
                            "alanlar sorulur ve türetilmiş değerler anında hesaplanır.")))
        izgara = QtWidgets.QGridLayout()
        izgara.setSpacing(A["m"])
        self.kategori_dugmeleri = {}
        for i, (kat, etiket_) in enumerate(mt.KATEGORILER):
            dugme = b.ikincil_dugme(_(etiket_), _IKON[kat])
            dugme.setMinimumHeight(_KATEGORI_DUGME_KATI * tokenlar.BOYUT["dugme_yuksekligi"])
            dugme.clicked.connect(lambda _c=False, k=kat: self.kategori_sec(k))
            izgara.addWidget(dugme, i // _KATEGORI_SUTUNU, i % _KATEGORI_SUTUNU)
            self.kategori_dugmeleri[kat] = dugme
        d.addLayout(izgara)
        d.addStretch(1)
        return w

    def _tarif_sayfasi(self):
        w = QtWidgets.QWidget()
        self.tarif_baslik = baslik("")
        self.tarif_aciklama = ipucu("")
        self.tarif_secici = QtWidgets.QComboBox()
        self.tarif_secici.currentIndexChanged.connect(self._tarif_degisti)
        self.tarif_satiri = QtWidgets.QWidget()
        ts = QtWidgets.QFormLayout(self.tarif_satiri)
        ts.setContentsMargins(0, 0, 0, 0)
        ts.addRow(_etiket(_("Malzeme türü:")), self.tarif_secici)
        self.form_kutu = QtWidgets.QWidget()
        self._form_duzen = QtWidgets.QVBoxLayout(self.form_kutu)
        self._form_duzen.setContentsMargins(0, 0, 0, 0)
        self.karisim = KarisimFormu([(m.get("ad"), m) for m in self._spec.get("malzemeler", [])]
                                    + _kutuphane_malzemeleri())
        self.karisim.degisti.connect(self._yenile)
        self.hata = _hata_etiketi()
        self.hata.setTextFormat(QtCore.Qt.PlainText)
        sol = QtWidgets.QVBoxLayout()
        for oge in (self.tarif_baslik, self.tarif_aciklama, self.tarif_satiri, self.form_kutu,
                    self.karisim, self.hata):
            sol.addWidget(oge)
        sol.addStretch(1)
        self.panel = TuretilmisPanel()
        govde = QtWidgets.QHBoxLayout(w)
        govde.addLayout(sol, 1)
        govde.addWidget(self.panel, 1)
        return w

    def _dogrulama_sayfasi(self):
        w = QtWidgets.QWidget()
        self.bulgu_listesi = QtWidgets.QListWidget()
        self.ad = QtWidgets.QLineEdit()
        self.ad.textChanged.connect(self._ad_dogrula)
        self.ad_hata = _hata_etiketi()
        self.projeye = QtWidgets.QCheckBox(_("Projeye ekle"))
        self.projeye.setChecked(True)
        self.kutuphaneye = QtWidgets.QCheckBox(
            _("Kütüphaneme de kaydet (yalnız bu bilgisayarda: %s)") % mku.varsayilan_yol())
        self.aciklama = QtWidgets.QLineEdit()
        self.aciklama.setPlaceholderText(_("Kısa açıklama (isteğe bağlı)"))
        for kutu in (self.projeye, self.kutuphaneye):
            kutu.toggled.connect(self._ad_dogrula)
        form = QtWidgets.QFormLayout()
        form.addRow(_etiket(_("Ad:")), self.ad)
        form.addRow(self.ad_hata)
        form.addRow(self.projeye)
        form.addRow(self.kutuphaneye)
        form.addRow(_etiket(_("Açıklama:")), self.aciklama)
        d = QtWidgets.QVBoxLayout(w)
        d.addWidget(baslik(_("Doğrulama ve kaydetme")))
        d.addWidget(self.bulgu_listesi, 1)
        d.addLayout(form)
        return w

    def _dugmeler(self):
        self.d_geri = b.ikincil_dugme(_("Geri"), "chevron-left")
        self.d_ileri = b.birincil_dugme(pgettext("asistan adımı", "İleri"), "chevron-right")
        self.d_bitir = b.birincil_dugme(_("Bitir"), "check")
        self.d_vazgec = b.duz_dugme(_("Vazgeç"))
        self.d_geri.clicked.connect(self.geri)
        self.d_ileri.clicked.connect(self.ileri)
        self.d_bitir.clicked.connect(self.bitir)
        self.d_vazgec.clicked.connect(self.reject)
        satir = QtWidgets.QHBoxLayout()
        satir.addWidget(self.d_vazgec)
        satir.addStretch(1)
        for d in (self.d_geri, self.d_ileri, self.d_bitir):
            satir.addWidget(d)
        return satir

    # ------------------------------------------------------------ akis
    def kategori_sec(self, kategori):
        self.kategori = kategori
        ozel = kategori == "ozel"
        etiket_ = dict(mt.KATEGORILER)[kategori]
        self.tarif_baslik.setText(_(etiket_))
        self.tarif_satiri.setVisible(not ozel)
        self.form_kutu.setVisible(not ozel)
        self.karisim.setVisible(ozel)
        if ozel:
            self.tarif_aciklama.setText(_("Projedeki ya da kütüphanenizdeki malzemeleri "
                                          "ağırlık, atom ya da hacim oranıyla karıştırın "
                                          "(ideal karışım: hacimler toplanır)."))
        self.tarif_secici.blockSignals(True)
        self.tarif_secici.clear()
        for anahtar in ([] if ozel else mt.tarifler(kategori)):
            self.tarif_secici.addItem(mt.etiket(anahtar), anahtar)
        self.tarif_secici.blockSignals(False)
        if ozel:
            self._yenile()
        else:
            self._tarif_degisti()
        self.yigin.setCurrentIndex(_SAYFA_TARIF)
        self._adim_guncelle()

    def tarif_sec(self, anahtar):
        self.tarif_secici.setCurrentIndex(self.tarif_secici.findData(anahtar))

    def _tarif_degisti(self, *_a):
        anahtar = self.tarif_secici.currentData()
        if anahtar is None:
            return
        self.tarif_aciklama.setText(mt.aciklama(anahtar))
        if self.form is not None:
            self._form_duzen.removeWidget(self.form)
            self.form.hide()
            self.form.setParent(None)
            self.form.deleteLater()
        self.form = TarifFormu(mt.alanlar(anahtar))
        self.form.degisti.connect(self._yenile)
        self._form_duzen.addWidget(self.form)
        self._yenile()

    def taslak(self):
        """Gecerli degerlerin malzemesi (yeni sozluk); kurulamazsa ValueError."""
        if self.kategori == "ozel":
            malz, oran, tur, t = self.karisim.param()
            if len(malz) < 2:
                raise ValueError(_("En az iki bileşen seçin."))
            return mt.karisim_malzemesi(malz, oran, tur, sicaklik=t)
        return mt.uret(self.tarif_secici.currentData(), self.form.param())

    def _yenile(self, *_a):
        try:
            self._taslak, self._sorun = self.taslak(), None
        except ValueError as e:              # kullaniciya gosterilir; Ileri kapanir
            self._taslak, self._sorun = None, str(e)
        self.hata.setText(self._sorun or "")
        self.hata.setVisible(bool(self._sorun))
        self.panel.guncelle(self._taslak)          # neden self.hata etiketinde (tek yerde)
        self._adim_guncelle()

    def ileri(self):
        if self.yigin.currentIndex() != _SAYFA_TARIF or self._taslak is None:
            return
        self.bulgular = mt.dogrula_malzeme(self._taslak)
        self.bulgu_listesi.clear()
        for seviye, metin in self.bulgular or [("bilgi", _("Sorun bulunmadı."))]:
            self.bulgu_listesi.addItem("%s  %s" % (_SEVIYE_IMI.get(seviye, "•"), metin))
        self.ad.setText(_benzersiz_ad(self._spec, self._taslak["ad"]))
        self.yigin.setCurrentIndex(_SAYFA_DOGRULA)
        self._ad_dogrula()

    def geri(self):
        self.yigin.setCurrentIndex(max(self.yigin.currentIndex() - 1, _SAYFA_KATEGORI))
        self._adim_guncelle()

    def _ad_dogrula(self, *_a):
        sorun = None
        if self.projeye.isChecked():
            sorun = sema.malzeme_adi_sorunu(self._spec, self.ad.text())
        elif not self.ad.text().strip():
            sorun = _("Malzeme adı boş olamaz.")
        if not (self.projeye.isChecked() or self.kutuphaneye.isChecked()):
            sorun = _("Projeye ekleyin ya da kütüphanenize kaydedin.")
        if any(s == "hata" for s, _m in self.bulgular):
            sorun = _("Doğrulamada hata var; Geri dönüp değerleri düzeltin.")
        self.ad_hata.setText(sorun or "")
        self.ad_hata.setVisible(bool(sorun))
        self._adim_guncelle(sorun)
        return sorun is None

    def _adim_guncelle(self, ad_sorunu=None):
        sayfa = self.yigin.currentIndex()
        self.d_geri.setEnabled(sayfa > _SAYFA_KATEGORI)
        self.d_ileri.setVisible(sayfa != _SAYFA_DOGRULA)
        self.d_ileri.setEnabled(sayfa == _SAYFA_TARIF and self._taslak is not None)
        self.d_bitir.setVisible(sayfa == _SAYFA_DOGRULA)
        self.d_bitir.setEnabled(sayfa == _SAYFA_DOGRULA and ad_sorunu is None)

    # ------------------------------------------------------------ sonuc
    def sonuc(self):
        m = dict(self._taslak)
        m["ad"] = self.ad.text()
        return m

    def _hata_goster(self, metin):
        """Kutuphane yazma hatasi (testler ezer)."""
        kutu = QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning, _("Kütüphaneye kaydedilemedi"),
                                     metin, QtWidgets.QMessageBox.Ok, self)
        kutu.setTextFormat(QtCore.Qt.PlainText)
        kutu.exec()

    def kutuphaneye_kaydet(self, m):
        aciklama = self.aciklama.text()

        def islem(kayitlar):
            ad = mku.benzersiz_kayit_adi(kayitlar, m["ad"])
            return mku.ekle(kayitlar, mku.kayit_olustur(dict(m, ad=ad), aciklama=aciklama,
                                                        kaynak="asistan"))
        try:
            mku.degistir(islem)
        except (mku.KutuphaneHatasi, ValueError) as e:
            _log.warning("asistan: kutuphaneye kaydedilemedi: %s", e)
            self._hata_goster(str(e))
            return False
        return True

    def bitir(self):
        if self.yigin.currentIndex() != _SAYFA_DOGRULA or not self._ad_dogrula():
            return False
        if self.kutuphaneye.isChecked() and not self.kutuphaneye_kaydet(self.sonuc()):
            return False
        self.accept()
        return True

    def projeye_eklenecek_mi(self):
        return self.projeye.isChecked()
