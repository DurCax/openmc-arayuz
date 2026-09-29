# -*- coding: utf-8 -*-
"""
sayi_birim.py -- SayiBirim: QDoubleSpinBox + birim etiketi ya da birim secici.

    SayiBirim(birim="cm", deger=1.26, ondalik=4)                   # sabit birim
    SayiBirim(birimler={"cm": 1.0, "mm": 0.1}, deger=1.0)          # secilebilir
        deger()          -> TABAN birimde (ilk birim) deger; secici yalniz gosterimi degistirir
        deger_ayarla(v)  -> taban birimde
        birim(), birim_ayarla("mm")
        degisti(float)   -> taban birimde yeni deger
        kutu             -> QDoubleSpinBox (hata ozelligi icin stil.durum_ayarla(kutu, "hata", True))

Ondalik ayirici NOKTA (QLocale.c(), binlik ayirici yok): mevcut kodla ayni;
bilimsel girdide "1,26" ile "1.26" karismasin.
"""

from PySide6 import QtCore, QtWidgets

from arayuz.tasarim import tokenlar

A = tokenlar.ARALIK
_EN_AZ_GENISLIK = 11 * A["s"]


class SayiBirim(QtWidgets.QWidget):
    degisti = QtCore.Signal(float)
    birim_degisti = QtCore.Signal(str)

    def __init__(self, birim=None, birimler=None, deger=0.0, en_az=0.0, en_cok=1e9,
                 ondalik=4, adim=None, parent=None, erisilebilir_ad=None):
        super().__init__(parent)
        if birimler is None:
            birimler = {birim or "": 1.0}
        if not birimler:
            raise ValueError("en az bir birim gerekli")
        self._carpan = dict(birimler)
        self._taban_min, self._taban_max = en_az, en_cok
        self._etkin = next(iter(self._carpan))
        d = QtWidgets.QHBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(A["s"])
        self.kutu = QtWidgets.QDoubleSpinBox()
        yerel = QtCore.QLocale.c()
        yerel.setNumberOptions(QtCore.QLocale.OmitGroupSeparator)
        self.kutu.setLocale(yerel)
        self.kutu.setDecimals(ondalik)
        self.kutu.setRange(en_az, en_cok)
        self.kutu.setSingleStep(adim if adim is not None else 10 ** -min(ondalik, 2))
        self.kutu.setKeyboardTracking(False)
        self.kutu.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # Genis aralik (1e9) sizeHint'i sisirir; formlar dar ekranda tassin diye
        # alt sinir acikca verilir.
        self.kutu.setMinimumWidth(_EN_AZ_GENISLIK)
        self.kutu.setValue(deger)
        self.kutu.valueChanged.connect(lambda _v: self.degisti.emit(self.deger()))
        d.addWidget(self.kutu, 1)
        self.birim_secici = None
        self.birim_etiketi = None
        if len(self._carpan) > 1:
            self.birim_secici = QtWidgets.QComboBox()
            self.birim_secici.addItems(list(self._carpan))
            self.birim_secici.setAccessibleName("birim")
            self.birim_secici.currentTextChanged.connect(self.birim_ayarla)
            d.addWidget(self.birim_secici)
        elif self._etkin:
            self.birim_etiketi = QtWidgets.QLabel(self._etkin)
            self.birim_etiketi.setObjectName("birim")
            self.birim_etiketi.setMinimumWidth(A["xl"])
            d.addWidget(self.birim_etiketi)
        ad = erisilebilir_ad or self._etkin
        self.kutu.setAccessibleName(ad)
        self.setFocusProxy(self.kutu)

    # ------------------------------------------------------------------
    def deger(self):
        return self.kutu.value() * self._carpan[self._etkin]

    def deger_ayarla(self, taban_deger):
        self.kutu.setValue(taban_deger / self._carpan[self._etkin])

    def birim(self):
        return self._etkin

    def birim_ayarla(self, birim):
        if birim not in self._carpan:
            raise ValueError("bilinmeyen birim: %r" % (birim,))
        if birim == self._etkin:
            return
        taban = self.deger()
        self._etkin = birim
        c = self._carpan[birim]
        engel = self.kutu.blockSignals(True)
        self.kutu.setRange(self._taban_min / c, self._taban_max / c)
        self.kutu.setValue(taban / c)
        self.kutu.blockSignals(engel)
        if self.birim_secici is not None and self.birim_secici.currentText() != birim:
            self.birim_secici.setCurrentText(birim)
        self.birim_degisti.emit(birim)
