# -*- coding: utf-8 -*-
"""
 arayuz/tukenme_ek.py  --  "Ek yanan malzemeler" listesi (tukenme.ek_malzemeler)

 Fisil malzemeler ve yanabilir zehirler (Gd, Er, bor zehri) OTOMATIK yanar
 (cekirdek/tukenme.otomatik_yanan_adlar): listede isaretli ve kapali durur.
 Digerleri (or. yapisal malzemede aktivasyon) isaretlenerek eklenir. Spec'te
 olup modelde tanimsiz olan ad SILINMEZ: "(tanımsız)" notuyla isaretli
 gosterilir; kullanici kaldirabilir (dogrulama onu ayrica hata sayar).

   w = EkMalzemeListesi()
   w.doldur(spec)          # sinyal YAYMAZ
   w.secim() -> [ad]       # spec sirasiyla; otomatik olup listede olanlar korunur
   w.degisti               # kullanici bir kutuyu degistirdi
"""

from PySide6 import QtCore, QtWidgets

from cekirdek import tukenme as _tk
from cekirdek.ceviri import _

_ROL = QtCore.Qt.UserRole
_EN_COK_SATIR = 6


class EkMalzemeListesi(QtWidgets.QListWidget):
    degisti = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAccessibleName(_("Ek yanan malzemeler"))
        self.setToolTip(_(
            "Yakıt dışında tükenme hesabına katılacak malzemeler (ör. aktivasyonu "
            "izlenecek yapısal malzeme). Fisil malzemeler ve yanabilir zehirler "
            "kendiliğinden katılır. Her ek malzemenin kesin hacmi gerekir."))
        self._ilk = []
        self._yukleniyor = False
        self.itemChanged.connect(self._oge_degisti)

    def _oge(self, ad, metin, isaretli, etkin):
        oge = QtWidgets.QListWidgetItem(metin)
        oge.setData(_ROL, ad)
        bayrak = QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable
        oge.setFlags(bayrak | QtCore.Qt.ItemIsEnabled if etkin else bayrak)
        oge.setCheckState(QtCore.Qt.Checked if isaretli else QtCore.Qt.Unchecked)
        self.addItem(oge)

    def doldur(self, spec):
        t = (spec or {}).get("tukenme") or {}
        self._ilk = list(t.get("ek_malzemeler") or [])
        otomatik = set(_tk.otomatik_yanan_adlar(spec or {}))
        tanimli = [m["ad"] for m in (spec or {}).get("malzemeler") or []]
        self._yukleniyor = True
        self.blockSignals(True)
        try:
            self.clear()
            for ad in tanimli:
                if ad in otomatik:
                    self._oge(ad, _("{ad} — otomatik").format(ad=ad), True, False)
                else:
                    self._oge(ad, ad, ad in self._ilk, True)
            for ad in self._ilk:
                if ad not in tanimli:
                    self._oge(ad, _("{ad} (tanımsız)").format(ad=ad), True, True)
        finally:
            self.blockSignals(False)
            self._yukleniyor = False
        satir = max(self.sizeHintForRow(0), self.fontMetrics().height() + 4)
        self.setFixedHeight(min(max(self.count(), 1), _EN_COK_SATIR) * (satir + 2)
                            + 2 * self.frameWidth() + 2)

    def secim(self):
        """Isaretli adlar (liste sirasi); otomatik olup ilk listede olanlar korunur."""
        cikti = []
        for i in range(self.count()):
            oge = self.item(i)
            ad = oge.data(_ROL)
            etkin = bool(oge.flags() & QtCore.Qt.ItemIsEnabled)
            if (etkin and oge.checkState() == QtCore.Qt.Checked) or \
                    (not etkin and ad in self._ilk):
                cikti.append(ad)
        return cikti

    def _oge_degisti(self, _oge):
        if not self._yukleniyor:
            self.degisti.emit()
