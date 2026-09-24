# -*- coding: utf-8 -*-
"""
================================================================================
 ortak.py  --  Arayuz genelinde paylasilan kucuk bilesenler
================================================================================
 Qt sinif gerektirdigi icin arayuz/ altinda sinif kullanilir; cekirdek/ altinda
 duz fonksiyonlar korunur.
================================================================================
"""

from PySide6 import QtCore, QtGui, QtWidgets


def sayi(deger=0.0, ondalik=5, en_az=0.0, en_cok=1e9, adim=0.01, sonek=""):
    """Ondalikli sayi girisi."""
    w = QtWidgets.QDoubleSpinBox()
    w.setDecimals(ondalik)
    w.setRange(en_az, en_cok)
    w.setSingleStep(adim)
    w.setValue(deger if deger is not None else 0.0)
    if sonek:
        w.setSuffix(" " + sonek)
    w.setMinimumWidth(88)
    return w


def tamsayi(deger=0, en_az=0, en_cok=10 ** 9, adim=1, sonek=""):
    """Tam sayi girisi."""
    w = QtWidgets.QSpinBox()
    w.setRange(en_az, en_cok)
    w.setSingleStep(adim)
    w.setValue(int(deger or 0))
    if sonek:
        w.setSuffix(" " + sonek)
    w.setMinimumWidth(88)
    return w


def baslik(metin):
    """Bolum basligi."""
    e = QtWidgets.QLabel(metin)
    f = e.font()
    f.setBold(True)
    e.setFont(f)
    e.setContentsMargins(0, 8, 0, 2)
    return e


def ipucu(metin):
    """Kucuk, soluk aciklama metni."""
    e = QtWidgets.QLabel(metin)
    e.setWordWrap(True)
    e.setStyleSheet("color: palette(mid);")
    f = e.font()
    f.setPointSizeF(max(f.pointSizeF() - 1.0, 7.0))
    e.setFont(f)
    return e


def ayrac():
    c = QtWidgets.QFrame()
    c.setFrameShape(QtWidgets.QFrame.HLine)
    c.setFrameShadow(QtWidgets.QFrame.Sunken)
    return c


def renk_simgesi(rgb, boyut=14):
    """RGB demetinden kucuk bir renk karesi simgesi uretir."""
    if not rgb:
        rgb = (170, 170, 170)
    pix = QtGui.QPixmap(boyut, boyut)
    pix.fill(QtGui.QColor(*[int(x) for x in rgb]))
    return QtGui.QIcon(pix)


class RenkDugmesi(QtWidgets.QPushButton):
    """Tiklayinca renk secici acan dugme. Deger (R,G,B) demetidir."""

    degisti = QtCore.Signal(tuple)

    def __init__(self, rgb=(170, 170, 170), parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 24)
        self._rgb = tuple(rgb or (170, 170, 170))
        self._yenile()
        self.clicked.connect(self._sec)

    def _yenile(self):
        self.setStyleSheet(
            "background-color: rgb(%d,%d,%d); border: 1px solid palette(mid);"
            % self._rgb)

    def rgb(self):
        return self._rgb

    def ayarla(self, rgb):
        self._rgb = tuple(int(x) for x in (rgb or (170, 170, 170)))
        self._yenile()

    def _sec(self):
        renk = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(*self._rgb), self, "Malzeme rengi")
        if renk.isValid():
            self.ayarla((renk.red(), renk.green(), renk.blue()))
            self.degisti.emit(self._rgb)


class SekmeTabani(QtWidgets.QWidget):
    """
    Tum editor sekmelerinin ortak tabani.

    Sozlesme:
      spec_yukle(spec)  -- spec'ten arayuzu doldurur (sinyal yaymadan)
      degisti(konu)     -- kullanici bir sey degistirdiginde yayilir
      KONU              -- bu sekmenin degistirdigi spec bolumu

    "konu" ana pencerenin hangi sekmelerin tazelenmesi gerektigini bilmesini
    saglar. Boylece bir ayar degisikligi, kullanicinin kafes sekmesindeki
    secimini bosu bosuna sifirlamaz.

    Alt siniflar _yukleniyor bayragini kontrol ederek yukleme sirasinda
    sinyal yaymaktan kacinir.
    """

    degisti = QtCore.Signal(str)
    KONU = "genel"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec = None
        self._yukleniyor = False

    def spec_yukle(self, spec):
        self.spec = spec
        self._yukleniyor = True
        try:
            self.doldur()
        finally:
            self._yukleniyor = False

    def doldur(self):
        """Alt sinif doldurur."""
        raise NotImplementedError

    def bildir(self):
        """Degisikligi ana pencereye bildirir (yukleme sirasinda susar)."""
        if not self._yukleniyor:
            self.degisti.emit(self.KONU)
