# -*- coding: utf-8 -*-
"""
 arayuz/ayar/spektrum_karti.py  --  Hesap ayarlari: "Spektrum ve dört faktör" karti (Y3)

 spec["ayarlar"]["spektrum"] = {"var": bool, "grup_yapisi": ad} alanini yazar
 (cekirdek/spektrum.py). Kart kendi icinde kapalidir: sekme yalniz doldur(spec)
 cagirir ve `degisti` sinyalini bildir()'e baglar.
"""

from PySide6 import QtCore, QtWidgets

from arayuz import bilesenler as b
from arayuz.ortak import ipucu
from cekirdek import spektrum
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)


class SpektrumAyarKarti(b.Kart):
    """Spektrum/dort faktor tally'lerini acan kart."""

    degisti = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(_("Spektrum ve dört faktör"),
                         _("ε, p, f, η, spektral indeksler ve akı spektrumu"), parent=parent)
        self._spec = None
        self._yukleniyor = False
        self.var = QtWidgets.QCheckBox(_("Spektrum ve dört faktörü hesapla"))
        self.var.setToolTip(_(
            "Koşuya altı tally ekler (adları y3_ ile başlar). Sonuçlar Çalıştır\n"
            "sayfasındaki “Spektrum ve dört faktör” kartında görünür."))
        self.grup = QtWidgets.QComboBox()
        for ad, sayi in spektrum.GRUP_YAPILARI.items():
            self.grup.addItem(_("%s (%d grup)") % (ad, sayi), ad)
        self.grup.setToolTip(_(
            "Akı spektrumunun enerji grupları (OpenMC hazır yapıları).\n"
            "Çok grup = ince ayrıntı ama grup başına daha çok gürültü."))
        form = QtWidgets.QFormLayout()
        form.addRow(self.var)
        form.addRow(_("Enerji grup yapısı:"), self.grup)
        self.govde.addLayout(form)
        self.ekle(ipucu(_(
            "Termal kesim %g eV. Dört faktör yalnızca özdeğer hesabında anlamlıdır; "
            "k∞ için sızıntısız (yansıtıcı sınırlı) model gerekir, sızıntı varsa "
            "ayrı bir P_NL çarpanı verilir.") % spektrum.TERMAL_KESIM_EV))
        self.uyari = ipucu("")
        self.uyari.setVisible(False)
        self.ekle(self.uyari)
        self.var.toggled.connect(self._kaydet)
        self.grup.currentIndexChanged.connect(self._kaydet)

    def doldur(self, spec):
        """Spec'ten doldurur (sinyal yaymadan). Dosyadaki grup yapisi gecersizse
        onay kutusu dosyadaki gibi kalir (arayuz ile spec celismesin), kutu
        varsayilani gosterir ve uyari yazilir; dogrulama ayrica hata verir."""
        self._spec = spec
        ham = (spec.get("ayarlar") or {}).get("spektrum")
        ham = ham if isinstance(ham, dict) else {}
        var = bool(ham.get("var"))
        grup = ham.get("grup_yapisi") or spektrum.VARSAYILAN_GRUP
        gecersiz = grup not in spektrum.GRUP_YAPILARI
        self._yukleniyor = True
        try:
            self.var.setChecked(var)
            self.grup.setCurrentIndex(
                max(self.grup.findData(spektrum.VARSAYILAN_GRUP if gecersiz else grup), 0))
        finally:
            self._yukleniyor = False
        self.grup.setEnabled(var)
        self.uyari.setText(_("Dosyadaki grup yapısı '%s' geçersiz; düzeltmek için listeden "
                             "seçin (koşu bu haliyle başlamaz).") % grup
                           if (gecersiz and var) else "")
        self.uyari.setVisible(gecersiz and var)
        if gecersiz:
            _log.warning("spektrum grup yapısı geçersiz: %r", grup)

    def _kaydet(self, *_a):
        self.grup.setEnabled(self.var.isChecked())
        if self._yukleniyor or self._spec is None:
            return
        self._spec["ayarlar"]["spektrum"] = {"var": self.var.isChecked(),
                                             "grup_yapisi": self.grup.currentData()}
        self.uyari.setVisible(False)
        self.degisti.emit()
