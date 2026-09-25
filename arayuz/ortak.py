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


# ----------------------------------------------------------------------------
# Sadelestirme bilesenleri (dalga 2)
#   GelismisBolum : nadiren gereken alanlari "Gelismis" basliginin altina
#                   katlar. Varsayilan KAPALI -- ilk bakista yalnizca gerekli
#                   alanlar gorunur. Durum anahtar basina hatirlanir.
#   BosDurum      : bos bir liste/sekme yerine "ne yapmaliyim" sorusunu
#                   cevaplayan panel: baslik, tek cumle, tek birincil eylem.
#   DurumRozeti   : kucuk renkli rozet ("2 hata", "Tamam"...). Renkler temadan
#                   okunur ve tema degisince kendiliginden yenilenir.
# ----------------------------------------------------------------------------

def _tema_renk(ad, vars_):
    """Tema rengi; tema modulu yuklenemezse (or. yalniz test) yedek renk."""
    try:
        from arayuz import tema
        return tema.renk(ad)
    except Exception:
        return vars_


class GelismisBolum(QtWidgets.QWidget):
    """
    Katlanabilir "Gelismis" bolumu (ok isaretli baslik + icerik).

    Kullanim:
        g = GelismisBolum("kor_gelismis")          # anahtar: QSettings'te durum
        g.ekle(widget)  ya da  g.duzen().addRow(...) icin kendi duzeninizi
        g.icerik'e kurun.
    Varsayilan KAPALI. anahtar None ise durum hatirlanmaz. QSettings
    kullanilamazsa (bozuk dosya, izin yok) sessizce varsayilanla calisir.
    """

    acildi = QtCore.Signal(bool)
    AYAR_ONEKI = "gelismis/"

    def __init__(self, anahtar=None, baslik="Gelişmiş", parent=None):
        super().__init__(parent)
        self._anahtar = anahtar
        self._baslik = baslik
        self.dugme = QtWidgets.QToolButton()
        self.dugme.setObjectName("gelismisDugme")
        self.dugme.setCheckable(True)
        self.dugme.setAutoRaise(True)
        self.dugme.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.dugme.setCursor(QtCore.Qt.PointingHandCursor)
        self.dugme.toggled.connect(self._degisti)
        self.icerik = QtWidgets.QWidget()
        self._icerik_duzeni = QtWidgets.QVBoxLayout(self.icerik)
        self._icerik_duzeni.setContentsMargins(18, 2, 0, 4)
        d = QtWidgets.QVBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(2)
        d.addWidget(self.dugme, 0, QtCore.Qt.AlignLeft)
        d.addWidget(self.icerik)
        acik = self._oku()
        self.dugme.blockSignals(True)
        self.dugme.setChecked(acik)
        self.dugme.blockSignals(False)
        self._uygula(acik)

    # -- durum kaliciligi --
    def _oku(self):
        if not self._anahtar:
            return False
        try:
            deger = QtCore.QSettings("openmc_arayuz", "arayuz").value(
                self.AYAR_ONEKI + self._anahtar, False)
        except Exception:
            return False
        if isinstance(deger, str):
            return deger.strip().lower() in ("true", "1", "yes")
        return bool(deger)

    def _yaz(self, acik):
        if not self._anahtar:
            return
        try:
            QtCore.QSettings("openmc_arayuz", "arayuz").setValue(
                self.AYAR_ONEKI + self._anahtar, bool(acik))
        except Exception:
            pass

    # -- gorunum --
    def _uygula(self, acik):
        self.dugme.setText(("▾  " if acik else "▸  ") + self._baslik)
        self.dugme.setToolTip("Gizle" if acik else "Nadiren gereken ayarları göster")
        self.icerik.setVisible(acik)

    def _degisti(self, acik):
        self._uygula(acik)
        self._yaz(acik)
        self.acildi.emit(acik)

    # -- API --
    def ekle(self, widget):
        self._icerik_duzeni.addWidget(widget)
        return widget

    def duzen(self):
        """Icerigin QVBoxLayout'u (form satirlari icin bir QFormLayout eklenebilir)."""
        return self._icerik_duzeni

    def acik_mi(self):
        return self.dugme.isChecked()

    def ac(self, acik=True):
        self.dugme.setChecked(bool(acik))


class BosDurum(QtWidgets.QWidget):
    """
    Bos durum paneli: simge, baslik, tek cumle aciklama, tek birincil dugme.
    eylem() dugmeye basilinca yayilir. dugme_metni None ise dugme gizlenir.
    """

    eylem = QtCore.Signal()

    def __init__(self, baslik="", metin="", dugme_metni=None, simge="＋", parent=None):
        super().__init__(parent)
        self.simge = QtWidgets.QLabel(simge)
        self.simge.setAlignment(QtCore.Qt.AlignCenter)
        f = self.simge.font()
        f.setPointSizeF(f.pointSizeF() * 2.6)
        self.simge.setFont(f)
        self.baslik = QtWidgets.QLabel(baslik)
        self.baslik.setAlignment(QtCore.Qt.AlignCenter)
        self.baslik.setWordWrap(True)
        f = self.baslik.font()
        f.setPointSizeF(f.pointSizeF() * 1.25)
        f.setBold(True)
        self.baslik.setFont(f)
        self.metin = QtWidgets.QLabel(metin)
        self.metin.setAlignment(QtCore.Qt.AlignCenter)
        self.metin.setWordWrap(True)
        self.dugme = QtWidgets.QPushButton(dugme_metni or "")
        self.dugme.setObjectName("birincil")
        self.dugme.setCursor(QtCore.Qt.PointingHandCursor)
        self.dugme.clicked.connect(self.eylem)
        self.dugme.setVisible(bool(dugme_metni))
        d = QtWidgets.QVBoxLayout(self)
        d.setContentsMargins(24, 24, 24, 24)
        d.addStretch(1)
        d.addWidget(self.simge)
        d.addWidget(self.baslik)
        d.addWidget(self.metin)
        d.addSpacing(8)
        d.addWidget(self.dugme, 0, QtCore.Qt.AlignHCenter)
        d.addStretch(2)
        self._renkleri_uygula()

    def ayarla(self, baslik=None, metin=None, dugme_metni=None):
        if baslik is not None:
            self.baslik.setText(baslik)
        if metin is not None:
            self.metin.setText(metin)
        if dugme_metni is not None:
            self.dugme.setText(dugme_metni)
            self.dugme.setVisible(bool(dugme_metni))

    def _renkleri_uygula(self):
        soluk = _tema_renk("metin_soluk", "#6b7785")
        stil_s = "color: %s;" % _tema_renk("vurgu", "#0f766e")
        stil_m = "color: %s;" % soluk
        if self.simge.styleSheet() != stil_s:
            self.simge.setStyleSheet(stil_s)
        if self.metin.styleSheet() != stil_m:
            self.metin.setStyleSheet(stil_m)

    def changeEvent(self, olay):
        if olay.type() == QtCore.QEvent.PaletteChange:
            self._renkleri_uygula()
        super().changeEvent(olay)


class DurumRozeti(QtWidgets.QLabel):
    """
    Kucuk renkli rozet. seviye: "hata" | "uyari" | "basari" | "bilgi" | "notr".
    tiklanabilir=True ise imlec el olur ve tiklandi() yayilir.
    """

    tiklandi = QtCore.Signal()
    SEVIYELER = ("hata", "uyari", "basari", "bilgi", "notr")

    def __init__(self, metin="", seviye="notr", tiklanabilir=False, parent=None):
        super().__init__(metin, parent)
        self._seviye = seviye if seviye in self.SEVIYELER else "notr"
        self._tiklanabilir = tiklanabilir
        self.setAlignment(QtCore.Qt.AlignCenter)
        if tiklanabilir:
            self.setCursor(QtCore.Qt.PointingHandCursor)
        self._stil_uygula()

    def ayarla(self, metin, seviye=None):
        self.setText(metin)
        if seviye is not None:
            self._seviye = seviye if seviye in self.SEVIYELER else "notr"
        self._stil_uygula()

    def seviye(self):
        return self._seviye

    def _stil_uygula(self):
        ad = {"hata": "hata", "uyari": "uyari", "basari": "basari",
              "bilgi": "bilgi", "notr": "metin_soluk"}[self._seviye]
        renk = QtGui.QColor(_tema_renk(ad, "#5b6673"))
        zemin = QtGui.QColor(renk)
        zemin.setAlpha(38)
        kenar = QtGui.QColor(renk)
        kenar.setAlpha(110)
        stil = ("QLabel { color: %s; background: rgba(%d,%d,%d,%d); "
                "border: 1px solid rgba(%d,%d,%d,%d); border-radius: 9px; "
                "padding: 1px 9px; font-weight: 600; }"
                % (renk.name(), zemin.red(), zemin.green(), zemin.blue(), zemin.alpha(),
                   kenar.red(), kenar.green(), kenar.blue(), kenar.alpha()))
        # Ayni stili yeniden kurmamak PaletteChange dongusunu de onler.
        if self.styleSheet() != stil:
            self.setStyleSheet(stil)

    def changeEvent(self, olay):
        if olay.type() == QtCore.QEvent.PaletteChange:
            self._stil_uygula()
        super().changeEvent(olay)

    def mousePressEvent(self, olay):
        if self._tiklanabilir and olay.button() == QtCore.Qt.LeftButton:
            self.tiklandi.emit()
            olay.accept()
            return
        super().mousePressEvent(olay)
