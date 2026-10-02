# -*- coding: utf-8 -*-
"""
 arayuz/malzeme/tarif_formu.py  --  TarifFormu (asistan tarifinin alanlari) ve
 KarisimFormu (ozel karisim: malzemeler + oranlar + wo/ao/vo)

 Alan tanimlari cekirdekten gelir (cekirdek/malzeme_tarif.alanlar); burada
 yalnizca girdi kutulari kurulur. param() tarifin uret() argumanidir.
"""

from PySide6 import QtCore, QtWidgets

from cekirdek.ceviri import _
from arayuz.ortak import sayi
from arayuz.malzeme.girdiler import SicaklikGirdi
from arayuz.malzeme.yardimcilar import _etiket

# Yogunluk yolu secimine bagli gorunurluk: alan -> (secim alani, gorundugu deger)
_BAGLI = {"td_yuzde": ("yogunluk_yolu", "td"), "yogunluk": ("yogunluk_yolu", "dogrudan")}
_KARISIM_SATIRI = 4
_YUZDE = 100.0
_ORAN_ETIKETI = (("wo", "wo — ağırlıkça"), ("ao", "ao — atomca"), ("vo", "vo — hacimce"))


class _DogalYaDa(QtWidgets.QWidget):
    """'Dogal' onay kutusu + sayi kutusu; dogal secilince deger None."""

    degisti = QtCore.Signal()

    def __init__(self, a, parent=None):
        super().__init__(parent)
        self.dogal = QtWidgets.QCheckBox(_("doğal"))
        self.kutu = sayi(a["en_az"], a["ondalik"], a["en_az"], a["en_cok"], a["adim"], a["sonek"])
        d = QtWidgets.QHBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        d.addWidget(self.dogal)
        d.addWidget(self.kutu)
        d.addStretch(1)
        self.setValue(a["varsayilan"])
        self.dogal.toggled.connect(self._degisti)
        self.kutu.valueChanged.connect(self._degisti)

    def _degisti(self, *_a):
        self.kutu.setEnabled(not self.dogal.isChecked())
        self.degisti.emit()

    def value(self):
        return None if self.dogal.isChecked() else self.kutu.value()

    def setValue(self, v):
        self.dogal.setChecked(v is None)
        if v is not None:
            self.kutu.setValue(v)
        self.kutu.setEnabled(v is not None)


class TarifFormu(QtWidgets.QWidget):
    """Bir tarifin alanlari (QFormLayout); degisti sinyali her degisiklikte."""

    degisti = QtCore.Signal()

    def __init__(self, alanlar, parent=None):
        super().__init__(parent)
        self.tanimlar = alanlar
        self.alanlar, self.etiketler = {}, {}
        self._form = QtWidgets.QFormLayout(self)
        self._form.setContentsMargins(0, 0, 0, 0)
        self._form.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldsStayAtSizeHint)
        for a in alanlar:
            w = self._girdi(a)
            if a["ipucu"]:
                w.setToolTip(a["ipucu"])
            e = _etiket(a["etiket"] + ":")
            self._form.addRow(e, w)
            self.alanlar[a["ad"]], self.etiketler[a["ad"]] = w, e
        self._gorunurluk()

    def _girdi(self, a):
        if a["tur"] == "sicaklik":
            w = SicaklikGirdi(a["varsayilan"], a["en_az"], a["en_cok"], a["ondalik"], a["adim"])
            w.degisti.connect(self._degisti)
        elif a["tur"] == "secim":
            w = QtWidgets.QComboBox()
            for veri, metin in a["secenekler"]:
                w.addItem(metin, veri)
            w.setCurrentIndex(max(w.findData(a["varsayilan"]), 0))
            w.currentIndexChanged.connect(self._degisti)
        elif a["tur"] == "dogal_ya_da":
            w = _DogalYaDa(a)
            w.degisti.connect(self._degisti)
        else:
            w = sayi(a["varsayilan"], a["ondalik"], a["en_az"], a["en_cok"], a["adim"], a["sonek"])
            w.valueChanged.connect(self._degisti)
        return w

    def _gorunurluk(self):
        for ad, (secim, deger) in _BAGLI.items():
            if ad in self.alanlar and secim in self.alanlar:
                gorunur = self.alanlar[secim].currentData() == deger
                self._form.setRowVisible(self.alanlar[ad], gorunur)

    def _degisti(self, *_a):
        self._gorunurluk()
        self.degisti.emit()

    def param(self):
        cikti = {}
        for ad, w in self.alanlar.items():
            cikti[ad] = w.currentData() if isinstance(w, QtWidgets.QComboBox) else w.value()
        return cikti

    def deger_ayarla(self, degerler):
        """Alanlara deger yazar (tek degisti sinyaliyle)."""
        self.blockSignals(True)
        try:
            for ad, v in degerler.items():
                w = self.alanlar[ad]
                if isinstance(w, QtWidgets.QComboBox):
                    w.setCurrentIndex(w.findData(v))
                else:
                    w.setValue(v)
        finally:
            self.blockSignals(False)
        self._degisti()


class KarisimFormu(QtWidgets.QWidget):
    """En cok dort bilesenli karisim: (malzeme, %) satirlari + oran turu + sicaklik."""

    degisti = QtCore.Signal()

    def __init__(self, malzemeler, parent=None):
        super().__init__(parent)
        self._malzemeler = list(malzemeler)          # [(gorunen etiket, malzeme sozlugu)]
        self.secimler, self.oranlar = [], []
        form = QtWidgets.QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        for i in range(_KARISIM_SATIRI):
            secim = QtWidgets.QComboBox()
            secim.addItem(_("— seçilmedi —"), None)
            for j, (etiket_, _m) in enumerate(self._malzemeler):
                secim.addItem(etiket_, j)
            oran = sayi(0.0, 3, 0.0, _YUZDE, 1.0, "%")
            satir = QtWidgets.QWidget()
            sd = QtWidgets.QHBoxLayout(satir)
            sd.setContentsMargins(0, 0, 0, 0)
            sd.addWidget(secim, 1)
            sd.addWidget(oran)
            form.addRow(_etiket(_("Bileşen %d:") % (i + 1)), satir)
            secim.currentIndexChanged.connect(self._degisti)
            oran.valueChanged.connect(self._degisti)
            self.secimler.append(secim)
            self.oranlar.append(oran)
        self.tur = QtWidgets.QComboBox()
        for veri, metin in _ORAN_ETIKETI:
            self.tur.addItem(_(metin), veri)
        self.tur.currentIndexChanged.connect(self._degisti)
        form.addRow(_etiket(_("Oranlar:")), self.tur)
        self.sicaklik = SicaklikGirdi(293.6, 250.0, 3000.0)
        self.sicaklik.degisti.connect(self._degisti)
        form.addRow(_etiket(_("Sıcaklık:")), self.sicaklik)

    def _degisti(self, *_a):
        self.degisti.emit()

    def _sira(self, ad):
        for j, (_e, m) in enumerate(self._malzemeler):
            if m.get("ad") == ad:
                return j
        raise KeyError(ad)

    def satir_ayarla(self, i, ad, yuzde):
        self.secimler[i].setCurrentIndex(self.secimler[i].findData(self._sira(ad)))
        self.oranlar[i].setValue(yuzde)

    def tur_ayarla(self, tur):
        self.tur.setCurrentIndex(self.tur.findData(tur))

    def param(self):
        """(malzemeler, oranlar 0-1, tur, sicaklik); secilmemis satirlar atlanir."""
        malz, oran = [], []
        for secim, kutu in zip(self.secimler, self.oranlar):
            j = secim.currentData()
            if j is not None:
                malz.append(self._malzemeler[j][1])
                oran.append(kutu.value() / _YUZDE)
        return malz, oran, self.tur.currentData(), self.sicaklik.value()
