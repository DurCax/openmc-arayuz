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


# ----------------------------------------------------------------------------
# Fare tekerlegi korumasi
#   Her sekme bir QScrollArea icindedir. Sayfayi tekerlekle kaydiran kullanici
#   imlecin altindan gecen secim/sayi kutusunun degerini SESSIZCE degistiriyordu
#   (olculdu: kor turu tek_cubuk -> tek_plaka, yan sinir reflective -> vacuum,
#   hucre adimi 1.26 -> 1.25). Kutular pek cok dosyada, cogu ciplak
#   QComboBox() olarak kuruldugu icin cozum uygulama genelindedir:
#     * ODAKSIZ kutu tekerlek olayini yok sayar -> olay kaydirma alanina gecer;
#     * odak politikasi StrongFocus yapilir: varsayilan WheelFocus'ta tekerlek
#       kutuya ODAK VERIR ve korumayi bosa cikarirdi.
#   Kutuya tiklayan (odak veren) kullanici tekerlegi yine kullanabilir.
#   QScrollBar bilerek disarida: kaydirma cubugu tekerlegi almali.
# ----------------------------------------------------------------------------

_TEKERLEK_HEDEFLERI = (QtWidgets.QComboBox, QtWidgets.QAbstractSpinBox,
                       QtWidgets.QSlider)


class _TekerlekSuzgeci(QtCore.QObject):
    """Uygulama geneli olay suzgeci -- bkz. tekerlek_korumasi_kur()."""

    def eventFilter(self, nesne, olay):
        tur = olay.type()
        if tur == QtCore.QEvent.Wheel:
            if isinstance(nesne, _TEKERLEK_HEDEFLERI) and not nesne.hasFocus():
                olay.ignore()          # yok say: ust widget'a (kaydirma alanina) gecer
                return True            # kutunun kendisi degeri DEGISTIRMEZ
        elif tur == QtCore.QEvent.Polish:
            if (isinstance(nesne, _TEKERLEK_HEDEFLERI)
                    and nesne.focusPolicy() == QtCore.Qt.WheelFocus):
                nesne.setFocusPolicy(QtCore.Qt.StrongFocus)
        return False


_SUZGEC = {}


def tekerlek_korumasi_kur(uygulama=None):
    """Tekerlek korumasini uygulamaya bir kez kurar (tekrar cagrilabilir)."""
    uygulama = uygulama or QtWidgets.QApplication.instance()
    if uygulama is None or id(uygulama) in _SUZGEC:
        return
    suzgec = _TekerlekSuzgeci(uygulama)
    uygulama.installEventFilter(suzgec)
    _SUZGEC[id(uygulama)] = suzgec


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


# ----------------------------------------------------------------------------
# Enerji girdisi
#   Nukleer hesapta enerji araligi 0.0253 eV ile 14 MeV arasinda degisir --
#   tek bir kutuya "14100000" yazdirmak hata davetiyesidir. Deger + birim
#   ikilisi hem okunakli hem de belirsizlik birakmaz. Spec dosyasinda daima
#   eV tutulur; donusumu bu bilesen yapar.
# ----------------------------------------------------------------------------

_BIRIMLER = [("eV", 1.0), ("keV", 1.0e3), ("MeV", 1.0e6)]


class EnerjiGirdi(QtWidgets.QWidget):
    """Deger + birim (eV/keV/MeV). deger() ve ayarla() DAIMA eV kullanir."""

    degisti = QtCore.Signal()

    def __init__(self, ev=1.0e6, parent=None):
        super().__init__(parent)
        self.kutu = QtWidgets.QDoubleSpinBox()
        self.kutu.setDecimals(4)
        self.kutu.setRange(1.0e-6, 1.0e9)
        self.kutu.setSingleStep(0.1)
        self.kutu.setMinimumWidth(80)
        self.birim = QtWidgets.QComboBox()
        self.birim.addItems([b for b, _ in _BIRIMLER])
        d = QtWidgets.QHBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        d.addWidget(self.kutu, 1)
        d.addWidget(self.birim, 0)
        self.ayarla(ev)
        self.kutu.valueChanged.connect(self.degisti)
        self.birim.currentIndexChanged.connect(self._birim_degisti)

    def _birim_degisti(self):
        self.degisti.emit()

    def deger(self):
        """Girilen enerjiyi eV cinsinden dondurur."""
        return self.kutu.value() * _BIRIMLER[self.birim.currentIndex()][1]

    def ayarla(self, ev):
        """eV cinsinden bir enerjiyi, okunakli bir birim secerek gosterir."""
        ev = float(ev or 0.0)
        i = 0
        for j, (_, carpan) in enumerate(_BIRIMLER):
            if ev >= carpan:
                i = j
        eski = self.blockSignals(True)
        self.birim.setCurrentIndex(i)
        self.kutu.setValue(ev / _BIRIMLER[i][1])
        self.blockSignals(eski)


class BilimselGirdi(QtWidgets.QLineEdit):
    """1e12 gibi buyuk sayilar icin; QDoubleSpinBox bunlari okunakli gostermiyor."""

    def __init__(self, deger=1.0, parent=None):
        super().__init__(parent)
        dogrulayici = QtGui.QDoubleValidator(self)
        dogrulayici.setNotation(QtGui.QDoubleValidator.ScientificNotation)
        dogrulayici.setBottom(0.0)
        self.setValidator(dogrulayici)
        self.ayarla(deger)

    def deger(self, vars_=1.0):
        try:
            return float(self.text().replace(",", "."))
        except ValueError:
            return vars_

    def ayarla(self, v):
        self.setText("%g" % float(v or 1.0))
