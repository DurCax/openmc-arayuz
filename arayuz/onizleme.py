# -*- coding: utf-8 -*-
"""
================================================================================
 onizleme.py  --  Canli geometri onizlemesi
================================================================================

 openmc.Model.plot() bir matplotlib Axes'e cizim yapabildigi icin kendi CSG
 cizicimizi yazmiyoruz.

 OLCUM (pwr_17x17, bu makinede)
   Tek seferlik cizim:   200 px -> 632 ms | 400 px -> 255 ms | 1200 px -> 387 ms
   Piksel sayisi neredeyse fark etmiyor. Sebep: Model.plot() her cagrida
   openmc kutuphanesini bastan baslatir ve tesir kesitlerini yeniden okur;
   maliyet BASLATMADA, isin izlemede degil.

   Kutuphane acik tutulursa:
   ilk baslatma 3.3 s, sonra   200 px -> 13 ms | 600 px -> 43 ms | 1200 px -> 162 ms

 BUNDAN CIKAN IKI KARAR
   1. Cozunurluk bedava sayilir -- varsayilan yuksek tutulur, dusurmenin
      anlami yok (taslak cizim denendi, kazanc yalnizca %10 oldu ve kaldirildi).
   2. "Hizli mod" istege bagli bir secenektir:
        KAPALI (varsayilan) : her cizim ~260 ms, spec degisiklikleri ucuz.
                              Model kurarken/duzenlerken dogru secim.
        ACIK                : ilk cizim ~3.3 s, sonraki cizimler ~40 ms.
                              Bitmis bir geometriyi incelerken (eksen degistirme,
                              yakinlastirma) dogru secim.
      Spec degisirse kutuphane yeniden baslatilmak zorundadir; bu yuzden
      duzenleme sirasinda hizli mod ACIK olursa her degisiklik 3.3 s surer.
      Secenegin ipucunda bu acikca yazar.
================================================================================
"""

import atexit
import os
import tempfile
import traceback

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from PySide6 import QtCore, QtWidgets

from cekirdek import onbellek

# Cozunurluk secenekleri -- maliyet baslatmada oldugu icin yuksek varsayilan ucuz
COZUNURLUK = [("Hizli (400)", 400), ("Normal (800)", 800), ("Yuksek (1400)", 1400)]


class _LibYoneticisi:
    """
    openmc.lib tek bir global orneklemedir; ayni anda yalnizca bir model
    yuklenebilir. Bu sinif hangi modelin yuklu oldugunu takip eder ve
    uygulama kapanirken duzgun kapatilmasini saglar.
    """

    def __init__(self):
        self.model = None
        self.anahtar = None
        self.dizin = None
        atexit.register(self.kapat)

    def hazirla(self, model, anahtar):
        """Verilen model icin kutuphaneyi baslatir (gerekiyorsa yeniden)."""
        if self.anahtar == anahtar and self.model is not None:
            return False                       # zaten hazir
        self.kapat()
        self.dizin = tempfile.mkdtemp(prefix="openmc_arayuz_lib_")
        eski = os.getcwd()
        try:
            os.chdir(self.dizin)
            model.init_lib(output=False)
        finally:
            os.chdir(eski)
        self.model = model
        self.anahtar = anahtar
        return True                            # yeni baslatildi

    def kapat(self):
        if self.model is not None:
            try:
                self.model.finalize_lib()
            except Exception:
                pass
        self.model = None
        self.anahtar = None
        if self.dizin:
            import shutil
            shutil.rmtree(self.dizin, ignore_errors=True)
            self.dizin = None


_LIB = _LibYoneticisi()


class OnizlemeWidget(QtWidgets.QWidget):
    """Geometri kesiti gosteren matplotlib tuvali + denetimler."""

    durum = QtCore.Signal(str, bool)
    olcu_bulundu = QtCore.Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec = None
        self._son_hata = None
        self.son_olcu = None

        # --- denetim satiri ---
        self.eksen = QtWidgets.QComboBox()
        self.eksen.addItems(["xy", "xz", "yz"])
        self.renklendirme = QtWidgets.QComboBox()
        self.renklendirme.addItems(["material", "cell"])
        self.cozunurluk = QtWidgets.QComboBox()
        for etiket, _ in COZUNURLUK:
            self.cozunurluk.addItem(etiket)
        self.cozunurluk.setCurrentIndex(1)
        self.gosterge = QtWidgets.QCheckBox("Gosterge")
        self.gosterge.setChecked(True)
        self.hizli_mod = QtWidgets.QCheckBox("Hizli mod")
        self.hizli_mod.setToolTip(
            "KAPALI  : her cizim ~260 ms, model duzenlerken dogru secim.\n"
            "ACIK    : ilk cizim ~3 s (tesir kesitleri bellege yuklenir),\n"
            "          sonraki cizimler ~40 ms.\n\n"
            "Bitmis bir geometriyi incelerken (eksen degistirme, yakinlastirma)\n"
            "acin. DUZENLERKEN ACMAYIN: her spec degisikligi kutuphaneyi\n"
            "yeniden baslatmayi gerektirir ve degisiklik basina ~3 s surer.")
        self.yenile_dugme = QtWidgets.QPushButton("Yenile")

        ust = QtWidgets.QHBoxLayout()
        ust.setContentsMargins(4, 4, 4, 0)
        for etiket, w in (("Eksen:", self.eksen), ("Renk:", self.renklendirme),
                          ("Cozunurluk:", self.cozunurluk)):
            ust.addWidget(QtWidgets.QLabel(etiket))
            ust.addWidget(w)
        ust.addWidget(self.gosterge)
        ust.addWidget(self.hizli_mod)
        ust.addStretch(1)
        ust.addWidget(self.yenile_dugme)

        # --- tuval ---
        self.figur = Figure(figsize=(5, 5), tight_layout=True)
        self.tuval = FigureCanvasQTAgg(self.figur)
        self.eksenler = self.figur.add_subplot(111)
        self.arac_cubugu = NavigationToolbar2QT(self.tuval, self)

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.addLayout(ust)
        duzen.addWidget(self.tuval, 1)
        duzen.addWidget(self.arac_cubugu)

        # --- gecikme sayaci ---
        self._sayac = QtCore.QTimer(self)
        self._sayac.setSingleShot(True)
        self._sayac.setInterval(300)
        self._sayac.timeout.connect(self._ciz)

        for w in (self.eksen, self.renklendirme, self.cozunurluk):
            w.currentIndexChanged.connect(lambda *_: self._ciz())
        self.gosterge.toggled.connect(lambda *_: self._ciz())
        self.hizli_mod.toggled.connect(self._hizli_mod_degisti)
        self.yenile_dugme.clicked.connect(lambda *_: self._ciz())

        self._bos_mesaj("Model bekleniyor")

    # ------------------------------------------------------------------
    def spec_ayarla(self, spec):
        self.spec = spec
        self.iste()

    def iste(self):
        """Cizimi gecikmeli ister; ardarda cagrilar tek cizime duser."""
        self._sayac.start()

    def _hizli_mod_degisti(self, acik):
        if not acik:
            _LIB.kapat()
            self.durum.emit("Hizli mod kapatildi", True)
        self._ciz()

    # ------------------------------------------------------------------
    def _bos_mesaj(self, metin, hata=False):
        self.eksenler.clear()
        self.eksenler.set_axis_off()
        self.eksenler.text(0.5, 0.5, metin, ha="center", va="center",
                           wrap=True, fontsize=9,
                           color="#c0392b" if hata else "#7f8c8d")
        self.tuval.draw_idle()

    def _ciz(self):
        if self.spec is None:
            self._bos_mesaj("Model bekleniyor")
            return
        try:
            model, bilgi = onbellek.kur_onbellekli(self.spec)
            gx, gy = bilgi["sinir_kutu"]
            piksel = COZUNURLUK[self.cozunurluk.currentIndex()][1]
            eksen = self.eksen.currentText()

            h = self.spec["kor"].get("yukseklik")
            if eksen == "xy":
                genislik = (gx, gy)
            else:
                dikey = h if h else max(gx, gy)
                genislik = ((gx if eksen == "xz" else gy), dikey)

            yeniden_baslatildi = False
            if self.hizli_mod.isChecked():
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                try:
                    yeniden_baslatildi = _LIB.hazirla(model, onbellek.ozet(self.spec))
                finally:
                    QtWidgets.QApplication.restoreOverrideCursor()

            self.eksenler.clear()
            self.eksenler.set_axis_on()
            renk_ver = self.renklendirme.currentText() == "material"
            model.plot(basis=eksen, width=genislik, pixels=(piksel, piksel),
                       color_by=self.renklendirme.currentText(),
                       colors=bilgi["renkler"] if renk_ver else None,
                       legend=self.gosterge.isChecked() and renk_ver,
                       axes=self.eksenler)
            self.eksenler.set_title("%s   %.3f x %.3f cm"
                                    % (self.spec.get("ad", ""), genislik[0], genislik[1]),
                                    fontsize=9)
            self.tuval.draw_idle()
            self._son_hata = None
            self.son_olcu = (gx, gy)
            self.olcu_bulundu.emit(gx, gy)
            ek = "  [hizli mod yeniden baslatildi]" if yeniden_baslatildi else ""
            self.durum.emit("Onizleme guncel (%s, %d piksel)%s" % (eksen, piksel, ek), True)
        except Exception as e:
            self._son_hata = traceback.format_exc()
            self._bos_mesaj("Geometri kurulamadi:\n\n%s" % e, hata=True)
            self.durum.emit("Onizleme basarisiz: %s" % e, False)

    # ------------------------------------------------------------------
    def cizildi_mi(self):
        """Gecerli bir cizim yapildi mi? (CALISTIR kapisi bunu kullanir)"""
        return self.spec is not None and self._son_hata is None

    def son_hata(self):
        return self._son_hata

    def kaydet(self, yol):
        self.figur.savefig(yol, dpi=150, bbox_inches="tight")
        return yol

    def kapat(self):
        """Uygulama kapanirken openmc kutuphanesini serbest birakir."""
        _LIB.kapat()
