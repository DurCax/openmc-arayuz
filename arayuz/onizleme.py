# -*- coding: utf-8 -*-
"""
================================================================================
 onizleme.py  --  Canli geometri onizlemesi
================================================================================

 openmc.Model.plot() bir matplotlib Axes'e cizim yapabildigi icin kendi CSG
 cizicimizi yazmiyoruz. Olculen hiz: 1000x1000 piksel kesit ~0.2 s, uc eksende
 de ayni -- her spec degisikliginden sonra yeniden cizmek icin fazlasiyla hizli.

 Cizim ana is parcaciginda yapilir; 0.2 s'lik tikanma fark edilmez. Degisiklikler
 300 ms geciktirilerek toplanir (debounce), boylece bir alanda hizli yazarken
 her tusa basista yeniden cizilmez.
================================================================================
"""

import traceback

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from PySide6 import QtCore, QtWidgets

from cekirdek import kurucu

# Kullanicinin secebilecegi cozunurlukler
COZUNURLUK = [("Hizli (300)", 300), ("Normal (600)", 600), ("Yuksek (1000)", 1000)]


class OnizlemeWidget(QtWidgets.QWidget):
    """Geometri kesiti gosteren matplotlib tuvali + denetimler."""

    # Cizim basarili/basarisiz oldugunda yayilir (mesaj, basarili_mi)
    durum = QtCore.Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec = None
        self._son_hata = None

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
        self.yenile_dugme = QtWidgets.QPushButton("Yenile")

        ust = QtWidgets.QHBoxLayout()
        ust.setContentsMargins(4, 4, 4, 0)
        for etiket, w in (("Eksen:", self.eksen), ("Renk:", self.renklendirme),
                          ("Cozunurluk:", self.cozunurluk)):
            ust.addWidget(QtWidgets.QLabel(etiket))
            ust.addWidget(w)
        ust.addWidget(self.gosterge)
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

        # --- gecikme sayaci (debounce) ---
        self._sayac = QtCore.QTimer(self)
        self._sayac.setSingleShot(True)
        self._sayac.setInterval(300)
        self._sayac.timeout.connect(self._ciz)

        for w in (self.eksen, self.renklendirme, self.cozunurluk):
            w.currentIndexChanged.connect(self.iste)
        self.gosterge.toggled.connect(self.iste)
        self.yenile_dugme.clicked.connect(self._ciz)

        self._bos_mesaj("Model bekleniyor")

    # ------------------------------------------------------------------
    def spec_ayarla(self, spec):
        self.spec = spec
        self.iste()

    def iste(self):
        """Cizimi gecikmeli olarak ister (ardarda cagrilar tek cizime dusulur)."""
        self._sayac.start()

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
            model, bilgi = kurucu.kur(self.spec)
            gx, gy = bilgi["sinir_kutu"]
            piksel = COZUNURLUK[self.cozunurluk.currentIndex()][1]
            eksen = self.eksen.currentText()

            # xz / yz kesitlerinde eksenel genislik: yukseklik varsa onu kullan
            h = self.spec["kor"].get("yukseklik")
            if eksen == "xy":
                genislik = (gx, gy)
            else:
                dikey = h if h else max(gx, gy)
                genislik = ((gx if eksen == "xz" else gy), dikey)

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
            self.durum.emit("Onizleme guncel (%s, %d piksel)" % (eksen, piksel), True)
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
