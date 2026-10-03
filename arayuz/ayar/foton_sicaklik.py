# -*- coding: utf-8 -*-
"""
 arayuz/ayar/foton_sicaklik.py  --  Hesap ayarlari > Gelismis: foton tasinimi ve
                                    sicaklik isleme formu (Y7)

 spec["ayarlar"]["foton"] (cekirdek/foton.py) ve spec["ayarlar"]["sicaklik"]
 (cekirdek/sicaklik.py) alanlarini yazar. Sicaklik YONTEMI mevcut kutudadir
 (sekme_ayar.sicaklik_yontemi). Doldurma spec'e dokunmaz; kayitta yalniz
 dosyada olan ya da varsayilandan farkli alan yazilir (degismeyen ayar spec'i
 degistirmez, onbellek kimligi korunur).
"""

from PySide6 import QtCore, QtWidgets

from arayuz.ortak import ipucu, sayi
from cekirdek import foton, sicaklik
from cekirdek.ceviri import _, N_
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

_ELEKTRON_ADLARI = {"ttb": N_("Kalın hedef frenleme (ttb)"), "led": N_("Yerel bırakım (led)")}
_EN_YUKSEK_K = 1.0e5             # sicaklik girisinin ust siniri [K] (kutuphaneler <= 3000 K)
_TOLERANS_UST_K = 1000.0
_ARALIK_VARSAYILAN = (250.0, 2500.0)   # ENDF/B-VIII.0 notron verisinin uc sicakliklari


class FotonSicaklikFormu(QtWidgets.QWidget):
    """Foton tasinimi (elektron islemi) ve sicaklik isleme ayrintilari."""

    degisti = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._spec = None
        self._yukleniyor = False
        self._alanlari_kur()
        form = QtWidgets.QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        self._form = form
        form.addRow(self.foton)
        form.addRow(_("Elektron işlemi:"), self.elektron)
        form.addRow(self.kaynak_notu)
        form.addRow(_("Sıcaklık toleransı:"), self.tolerans)
        form.addRow(_("Varsayılan sıcaklık:"), self.varsayilan)
        form.addRow(self.multipole)
        aralik = QtWidgets.QWidget()
        d = QtWidgets.QHBoxLayout(aralik)
        d.setContentsMargins(0, 0, 0, 0)
        d.addWidget(self.aralik_var)
        d.addWidget(self.aralik_alt)
        d.addWidget(QtWidgets.QLabel("–"))
        d.addWidget(self.aralik_ust)
        d.addStretch(1)
        form.addRow(_("Yüklenecek aralık:"), aralik)
        form.addRow(ipucu(_(
            "Yalnız kütüphanede bulunan sıcaklıklarda veri vardır (ENDF/B-VIII.0: 250, 294, 600, "
            "900, 1200, 2500 K). En yakın yöntemi tolerans içindeki kütüphane sıcaklığını "
            "kullanır; ara değer yöntemi iki komşu sıcaklık arasında stokastik interpolasyon "
            "yapar. Doğrulama her malzeme için hangisinin kullanılacağını yazar.")))
        self._sinyalleri_bagla()

    def _alanlari_kur(self):
        self.foton = QtWidgets.QCheckBox(_("Foton taşınımı (gama ısınması)"))
        self.foton.setToolTip(_(
            "Nötronlardan doğan gamalar da taşınır; 'heating' skoru nötron + gama\n"
            "ısınmasını verir. Kütüphanede her element için foton verisi gerekir.\n"
            "Koşu belirgin biçimde uzar."))
        self.elektron = QtWidgets.QComboBox()
        for anahtar in foton.ELEKTRON_YONTEMLERI:
            self.elektron.addItem(_(_ELEKTRON_ADLARI[anahtar]), anahtar)
        self.elektron.setToolTip(_(
            "ttb: elektron/pozitron enerjisi doğduğu yerde bırakılır, frenleme\n"
            "fotonları taşınır (OpenMC varsayılanı). led: frenleme fotonu da üretilmez."))
        self.kaynak_notu = ipucu(_("Foton kaynağı seçili: foton taşınımı zaten açık."))
        self.tolerans = sayi(sicaklik.VARSAYILAN_TOLERANS, 1, 0.0, _TOLERANS_UST_K, 5.0, "K")
        self.tolerans.setToolTip(_(
            "En yakın: kütüphane sıcaklığı bu kadar yakınsa kullanılır.\n"
            "Ara değer: kütüphane aralığının bu kadar dışına uç değerle izin verilir."))
        self.varsayilan = sayi(sicaklik.VARSAYILAN_SICAKLIK, 1, 1.0, _EN_YUKSEK_K, 10.0, "K")
        self.varsayilan.setToolTip(_("Sıcaklığı verilmemiş malzemelerin sıcaklığı."))
        self.multipole = QtWidgets.QCheckBox(_("Windowed multipole (rezonans bölgesinde her sıcaklık)"))
        self.multipole.setToolTip(_(
            "Çözülmüş rezonans bölgesinde Doppler genişlemesi her sıcaklıkta analitik\n"
            "hesaplanır. Kütüphanede wmp verisi gerekir; yoksa OpenMC yalnız uyarır."))
        self.aralik_var = QtWidgets.QCheckBox()
        self.aralik_var.setToolTip(_("Aralıktaki TÜM kütüphane sıcaklıklarını yükle "
                                     "(geri beslemeli hesaplar için)."))
        self.aralik_alt = sayi(_ARALIK_VARSAYILAN[0], 1, 0.0, _EN_YUKSEK_K, 50.0, "K")
        self.aralik_ust = sayi(_ARALIK_VARSAYILAN[1], 1, 0.0, _EN_YUKSEK_K, 50.0, "K")

    def _sinyalleri_bagla(self):
        self.foton.toggled.connect(self._foton_kaydet)
        self.elektron.currentIndexChanged.connect(self._foton_kaydet)
        for w in (self.tolerans, self.varsayilan, self.aralik_alt, self.aralik_ust):
            w.valueChanged.connect(self._sicaklik_kaydet)
        for w in (self.multipole, self.aralik_var):
            w.toggled.connect(self._sicaklik_kaydet)

    # ------------------------------------------------------------------
    def doldur(self, spec):
        """Spec'ten doldurur (sinyalsiz, spec'e yazmaz). Gecersiz deger
        varsayilanla gosterilir; dogrulama ayrica hata verir."""
        self._spec = spec
        a = (spec.get("ayarlar") or {})
        fh = a.get("foton") if isinstance(a.get("foton"), dict) else {}
        sh = a.get("sicaklik") if isinstance(a.get("sicaklik"), dict) else {}
        self._yukleniyor = True
        try:
            self.foton.setChecked(bool(fh.get("var")))
            self.elektron.setCurrentIndex(max(self.elektron.findData(
                fh.get("elektron") or foton.VARSAYILAN_ELEKTRON), 0))
            self.tolerans.setValue(self._sayi(sh.get("tolerans"), sicaklik.VARSAYILAN_TOLERANS))
            self.varsayilan.setValue(self._sayi(sh.get("varsayilan"),
                                                sicaklik.VARSAYILAN_SICAKLIK))
            self.multipole.setChecked(bool(sh.get("multipole")))
            aralik = sh.get("aralik")
            gecerli = isinstance(aralik, (list, tuple)) and len(aralik) == 2
            self.aralik_var.setChecked(gecerli)
            alt, ust = (aralik if gecerli else _ARALIK_VARSAYILAN)
            self.aralik_alt.setValue(self._sayi(alt, _ARALIK_VARSAYILAN[0]))
            self.aralik_ust.setValue(self._sayi(ust, _ARALIK_VARSAYILAN[1]))
        finally:
            self._yukleniyor = False
        self._etkinlik()

    @staticmethod
    def _sayi(deger, varsayilan):
        try:
            return float(deger) if deger is not None else varsayilan
        except (TypeError, ValueError):
            _log.warning("Y7 ayar alanı sayı değil: %r", deger)
            return varsayilan

    def _etkinlik(self):
        kaynak_foton = self._spec is not None and foton.kaynak_foton_mu(self._spec)
        self.elektron.setEnabled(self.foton.isChecked() or kaynak_foton)
        self.kaynak_notu.setVisible(kaynak_foton)
        for w in (self.aralik_alt, self.aralik_ust):
            w.setEnabled(self.aralik_var.isChecked())

    @staticmethod
    def _yaz(ham, anahtar, deger, varsayilan):
        """Dosyada varsa ya da varsayilandan farkliysa yazar (YENI sozluk)."""
        if anahtar in ham or deger != varsayilan:
            return dict(ham, **{anahtar: deger})
        return ham

    def _foton_kaydet(self, *_a):
        self._etkinlik()
        if self._yukleniyor or self._spec is None:
            return
        a = self._spec["ayarlar"]
        ham = dict(a.get("foton") or {}, var=self.foton.isChecked())
        a["foton"] = self._yaz(ham, "elektron", self.elektron.currentData(),
                               foton.VARSAYILAN_ELEKTRON)
        self.degisti.emit()

    def _sicaklik_kaydet(self, *_a):
        self._etkinlik()
        if self._yukleniyor or self._spec is None:
            return
        a = self._spec["ayarlar"]
        ham = dict(a.get("sicaklik") or {})
        ham = self._yaz(ham, "tolerans", self.tolerans.value(), sicaklik.VARSAYILAN_TOLERANS)
        ham = self._yaz(ham, "varsayilan", self.varsayilan.value(), sicaklik.VARSAYILAN_SICAKLIK)
        ham = self._yaz(ham, "multipole", self.multipole.isChecked(), False)
        if self.aralik_var.isChecked():
            ham["aralik"] = [self.aralik_alt.value(), self.aralik_ust.value()]
        else:
            ham.pop("aralik", None)
        if ham or "sicaklik" in a:
            a["sicaklik"] = ham
        self.degisti.emit()
