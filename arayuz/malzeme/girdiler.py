# -*- coding: utf-8 -*-
"""
 arayuz/malzeme/girdiler.py  --  SicaklikGirdi, KesinSayiGirdi, ParametreFormu

 arayuz/sekme_malzeme.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import sekme_malzeme; sekme_malzeme.X` aynen calisir.
"""

from PySide6 import QtCore, QtGui, QtWidgets
from cekirdek import malzeme_kutup as mk
from cekirdek.ceviri import _
from arayuz.ortak import sayi
from arayuz.malzeme.yardimcilar import _KELVIN, _etiket, _sayi_metni, _tema_renk


# ============================================================================
# Kucuk girdiler
# ============================================================================

class SicaklikGirdi(QtWidgets.QWidget):
    """Kelvin kutusu + yaninda canli Celsius karsiligi."""

    degisti = QtCore.Signal(float)

    def __init__(self, deger=293.6, en_az=0.0, en_cok=5000.0, ondalik=2,
                 adim=10.0, parent=None):
        super().__init__(parent)
        self.kutu = sayi(deger if deger is not None else 293.6, ondalik,
                         en_az, en_cok, adim, "K")
        self.celsius = QtWidgets.QLabel()
        self.celsius.setObjectName("soluk")
        self.celsius.setMinimumWidth(90)
        d = QtWidgets.QHBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        d.addWidget(self.kutu)
        d.addWidget(self.celsius)
        d.addStretch(1)
        self.kutu.valueChanged.connect(self._guncelle)
        self._guncelle(self.kutu.value())

    def _guncelle(self, k):
        self.celsius.setText("= %.1f °C" % (k - _KELVIN))
        self.degisti.emit(k)

    def value(self):
        return self.kutu.value()

    def setValue(self, k):
        self.kutu.setValue(k)


class KesinSayiGirdi(QtWidgets.QLineEdit):
    """
    Pozitif ondalik sayi girisi; degeri YUVARLAMAZ. Eski spinbox 6 ondalikla
    helyumun 0.0001785 g/cm3 yogunlugunu her duzenlemede 0.000179'a
    yuvarliyordu.
    """

    def __init__(self, deger=1.0, parent=None):
        super().__init__(parent)
        v = QtGui.QDoubleValidator(self)
        v.setNotation(QtGui.QDoubleValidator.ScientificNotation)
        v.setBottom(0.0)
        v.setLocale(QtCore.QLocale.c())
        self.setValidator(v)
        self._ilk = float(deger or 0.0)
        self.setText(_sayi_metni(self._ilk))
        self._ilk_metin = self.text()
        self.setMaximumWidth(160)

    def deger(self):
        """Metin degismediyse ILK deger (kayipsiz); gecersizse None."""
        if self.text() == self._ilk_metin:
            return self._ilk
        try:
            return float(self.text().replace(",", "."))
        except ValueError:      # yarim/bozuk yazim: None -> form "gecersiz" gosterir
            return None


# ============================================================================
# Parametre formu (kutuphane malzemesi)
# ============================================================================

class ParametreFormu(QtWidgets.QWidget):
    """
    Bir kutuphane malzemesinin parametre formu. Yalnizca O malzemede anlamli
    parametreler sorulur (UO2'de bor yok, suda zenginlik yok); sicaklik her
    malzemede sorulur. param() kutuphane fonksiyonunun argumanlaridir.
    """

    degisti = QtCore.Signal()

    def __init__(self, anahtar, param=None, parent=None):
        super().__init__(parent)
        self.anahtar = anahtar
        self.tanimlar = mk.parametreler(anahtar)
        degerler = mk.varsayilan_parametreler(anahtar)
        if param:
            degerler.update(param)
        # Yeni malzemede formdaki her deger spec'e yazilir (okunur JSON);
        # var olanda yalnizca kayitli ya da DEGISEN anahtarlar -- dokunulmayan
        # bir malzeme bit bit ayni kalir.
        self._yazilan = set(degerler) if param is None else set(param)
        self._ilk = dict(degerler)
        self._ilk_gosterim = {}
        self.alanlar = {}
        self.etiketler = {}

        form = QtWidgets.QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldsStayAtSizeHint)
        for p in self.tanimlar:
            ad = p["ad"]
            deger = degerler.get(ad)
            if p["tur"] == "sicaklik":
                w = SicaklikGirdi(deger, p["en_az"], p["en_cok"], p["ondalik"], p["adim"])
                w.degisti.connect(self._degisti)
            else:
                w = sayi(p["en_az"] if deger is None else deger, p["ondalik"],
                         p["en_az"], p["en_cok"], p["adim"], p["sonek"])
                if p["tur"] == "dogal_ya_da":
                    dogal_metin = p["dogal_metin"]
                    w.setSpecialValueText(_(dogal_metin))
                w.valueChanged.connect(self._degisti)
            # Parametre metinleri cekirdekten (malzeme_kutup._PARAM) gelir; burada cevrilir.
            ipucu = p.get("ipucu")
            if ipucu:
                w.setToolTip(_(ipucu))
            etiket_metni = p["etiket"]
            etiket = _etiket(_(etiket_metni) + ":")
            form.addRow(etiket, w)
            self.alanlar[ad] = w
            self.etiketler[ad] = etiket
            self._ilk_gosterim[ad] = w.value()

        self.hesaplanan = None
        if anahtar in mk.SICAKLIKTAN_YOGUNLUK:
            self.hesaplanan = QtWidgets.QLabel()
            self.hesaplanan.setToolTip(_("Sıcaklıktan hesaplanır; değiştirmek için "
                                         "sıcaklığı değiştirin."))
            form.addRow(_etiket(_("Yoğunluk:")), self.hesaplanan)
        self.uyari = QtWidgets.QLabel()
        self.uyari.setWordWrap(True)
        self.uyari.setStyleSheet("color: %s;" % _tema_renk("uyari"))
        form.addRow(self.uyari)
        self._degisti()

    def _degisti(self, *_):
        param = self.param()
        if self.hesaplanan is not None:
            try:
                m = mk.uret(self.anahtar, **param)
                self.hesaplanan.setText("%.4f g/cm³" % m["yogunluk"]["deger"])
            except Exception as e:           # pragma: no cover - savunma
                self.hesaplanan.setText(str(e))
        uyari = mk.parametre_uyarilari(self.anahtar, param)
        self.uyari.setText("\n".join("⚠ " + u for u in uyari))
        self.uyari.setVisible(bool(uyari))
        self.degisti.emit()

    def param(self):
        cikti = {}
        for p in self.tanimlar:
            ad = p["ad"]
            v = self.alanlar[ad].value()
            if v == self._ilk_gosterim[ad]:
                if ad in self._yazilan:
                    cikti[ad] = self._ilk.get(ad)
                continue
            if p["tur"] == "dogal_ya_da" and v <= p["en_az"]:
                v = None
            cikti[ad] = v
        return cikti

    def malzeme(self):
        return mk.parametrik_uret(self.anahtar, self.param())

    def uretim_sorunu(self):
        """Bu parametrelerle malzeme kurulamiyorsa nedeni (or. U3Si2-Al'da
        alüminyuma yer kalmamasi); kurulabiliyorsa None."""
        try:
            self.malzeme()
        except (ValueError, TypeError) as e:
            return str(e)
        return None
