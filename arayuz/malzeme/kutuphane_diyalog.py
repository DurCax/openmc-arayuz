# -*- coding: utf-8 -*-
"""
 arayuz/malzeme/kutuphane_diyalog.py  --  KutuphaneDiyalog: kutuphaneden malzeme

 arayuz/sekme_malzeme.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import sekme_malzeme; sekme_malzeme.X` aynen calisir.
"""

from PySide6 import QtCore, QtWidgets
from cekirdek import sema
from cekirdek.ceviri import _
from arayuz.ortak import baslik, ipucu
from arayuz.malzeme.yardimcilar import (
    _benzersiz_ad, _etiket, _hata_etiketi, _ozet_etiketi, katalog_aciklamasi,
    kutuphane_gruplari, okunur_ad, uretim_ozeti)
from arayuz.malzeme.girdiler import ParametreFormu


# ============================================================================
# Kutuphaneden ekleme
# ============================================================================

class KutuphaneDiyalog(QtWidgets.QDialog):
    """Rol gruplu kutuphane listesi + secilen malzemenin parametre formu."""

    GELISMIS_ANAHTAR = "malzeme_kutuphane"

    def __init__(self, spec=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Kütüphaneden malzeme ekle"))
        self.resize(860, 620)
        self._spec = spec if spec is not None else sema.yeni_spec()
        self._ad_elle = False
        self.form = None

        self.liste = QtWidgets.QTreeWidget()
        self.liste.setHeaderHidden(True)
        self.liste.setRootIsDecorated(False)
        self.liste.setIndentation(12)
        self.liste.setMinimumWidth(270)
        self._ogeler = {}
        for grup, etiket, anahtarlar in kutuphane_gruplari():
            g = QtWidgets.QTreeWidgetItem([etiket])
            g.setFlags(QtCore.Qt.ItemIsEnabled)            # secilemez baslik
            g.setData(0, QtCore.Qt.UserRole + 1, grup)
            f = g.font(0)
            f.setBold(True)
            g.setFont(0, f)
            self.liste.addTopLevelItem(g)
            for k in anahtarlar:
                oge = QtWidgets.QTreeWidgetItem([okunur_ad(k)])
                oge.setData(0, QtCore.Qt.UserRole, k)
                oge.setToolTip(0, katalog_aciklamasi(k))
                g.addChild(oge)
                self._ogeler[k] = oge
        self.liste.expandAll()

        self.baslik_etiket = baslik("")
        self.aciklama = ipucu("")
        self.ad = QtWidgets.QLineEdit()
        self.ad.textEdited.connect(self._ad_duzenlendi)
        self.ad.textChanged.connect(self._dogrula)
        self.ad_hata = _hata_etiketi()
        ust = QtWidgets.QFormLayout()
        ust.addRow(_etiket(_("Ad:")), self.ad)
        ust.addRow(self.ad_hata)
        self.form_kutu = QtWidgets.QWidget()
        self._form_duzen = QtWidgets.QVBoxLayout(self.form_kutu)
        self._form_duzen.setContentsMargins(0, 0, 0, 0)
        self.ozet = _ozet_etiketi()

        self.kutu = QtWidgets.QDialogButtonBox()
        self.d_tamam = self.kutu.addButton(_("Ekle"), QtWidgets.QDialogButtonBox.AcceptRole)
        self.kutu.addButton(_("Vazgeç"), QtWidgets.QDialogButtonBox.RejectRole)
        self.kutu.accepted.connect(self._onayla)
        self.kutu.rejected.connect(self.reject)

        sag = QtWidgets.QVBoxLayout()
        sag.addWidget(self.baslik_etiket)
        sag.addWidget(self.aciklama)
        sag.addLayout(ust)
        sag.addWidget(self.form_kutu)
        sag.addWidget(self.ozet)
        sag.addStretch(1)
        govde = QtWidgets.QHBoxLayout()
        govde.addWidget(self.liste, 0)
        govde.addLayout(sag, 1)
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addLayout(govde, 1)
        duzen.addWidget(self.kutu)

        self.liste.currentItemChanged.connect(self._secim_degisti)
        self.sec("uo2" if "uo2" in self._ogeler else next(iter(self._ogeler)))

    # -------------------------------------------------------------- secim
    def sec(self, anahtar):
        self.liste.setCurrentItem(self._ogeler[anahtar])

    def secilen(self):
        oge = self.liste.currentItem()
        return oge.data(0, QtCore.Qt.UserRole) if oge else None

    def _secim_degisti(self, oge, _onceki=None):
        anahtar = oge.data(0, QtCore.Qt.UserRole) if oge else None
        if not anahtar:
            # grup basligi (klavyeyle) secildi: grubun ilk malzemesine gec
            if oge is not None and oge.childCount():
                self.liste.setCurrentItem(oge.child(0))
            return
        self.baslik_etiket.setText(okunur_ad(anahtar))
        self.aciklama.setText(katalog_aciklamasi(anahtar))
        if self.form is not None:
            # hemen gizle ve ayir: deleteLater olay dongusune kadar bekler,
            # o arada eski formun etiketleri yenisinin ustune ciziliyordu
            self._form_duzen.removeWidget(self.form)
            self.form.hide()
            self.form.setParent(None)
            self.form.deleteLater()
        self.form = ParametreFormu(anahtar)
        self.form.degisti.connect(self._ozet_guncelle)
        self._form_duzen.addWidget(self.form)
        if not self._ad_elle:
            self.ad.setText(_benzersiz_ad(self._spec, anahtar))
        self._ozet_guncelle()
        self._dogrula()

    def _ad_duzenlendi(self, _metin):
        self._ad_elle = True

    # -------------------------------------------------------------- sonuc
    def _ozet_guncelle(self):
        if self.form is None:
            return
        uretim = self.form.uretim_sorunu()
        self.ozet.setText(uretim_ozeti(None if uretim else self.form.malzeme(), uretim))
        self._dogrula()

    def _dogrula(self, *_):
        sorun = sema.malzeme_adi_sorunu(self._spec, self.ad.text())
        self.ad_hata.setText(sorun or "")
        self.ad_hata.setVisible(bool(sorun))
        uretim = self.form.uretim_sorunu() if self.form is not None else None
        self.d_tamam.setEnabled(sorun is None and uretim is None and self.secilen() is not None)
        return sorun is None and uretim is None

    def _onayla(self):
        if self._dogrula():
            self.accept()

    def sonuc(self):
        m = self.form.malzeme()
        m["ad"] = self.ad.text()
        return m

    # geriye uyumluluk (eski ad)
    uret = sonuc
