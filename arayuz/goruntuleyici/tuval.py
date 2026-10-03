# -*- coding: utf-8 -*-
"""
 tuval.py  --  Goruntuleyici tuvalleri (matplotlib, Qt)

   KesitTuvali   geometri kesiti + mesh bindirmesi + kaynak noktalari; fare
                 tekerlegi yakinlastirir (imlec noktasi sabit), sol tusla
                 surukleme kaydirir, fare hareketi koordinati yayar. Yakinlastirma
                 ve kaydirma YENI kesit ister (cozunurluk yeni pencerede tam).
   GoruntuTuvali 3B golgeli goruntu (RGB) -- eksensiz.
 Cizim yalniz boyama + imshow'dur (onlarca ms); dilimleme iscidedir (H2).
"""

import numpy as np

from matplotlib.figure import Figure
from PySide6 import QtCore, QtWidgets

from cekirdek.ceviri import _
from arayuz import tema
from arayuz.analiz.tuval import Tuval
from arayuz.goruntuleyici import gorunum as gr
from arayuz.tasarim import tokenlar

TEKER_KATI = 1.25            # tekerlek adimi basina yakinlastirma
_GORUNUM_KATI = 2            # goruntu pikseli / ekran pikseli en cok (H2 onizleme ile ayni)
_NOKTA_BOYU = 4              # kaynak noktasi (pt^2)
_YAZI = 8


def _bos(figur, ax, metin, hata=False) -> None:
    ax.clear()
    ax.set_axis_off()
    ax.text(0.5, 0.5, metin, ha="center", va="center", wrap=True, fontsize=_YAZI + 1,
            color=tema.renk("hata" if hata else "metin_soluk"), transform=ax.transAxes)


class KesitTuvali(QtWidgets.QWidget):
    """Kesit tuvali (bkz. modul belgesi)."""

    fare_hareketi = QtCore.Signal(float, float)
    yakinlastir = QtCore.Signal(float, float, float)     # kat, u, v
    kaydir = QtCore.Signal(float, float)                 # du, dv (merkez kaymasi)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.figur = Figure(figsize=(6, 6))
        self.tuval = Tuval(self.figur)
        self.ax = self.figur.add_subplot(111)
        self._renk_cubugu = None
        self._taban = None           # geometri AxesImage (yeniden kullanilir)
        self._ekler = []             # bindirme resmi, kaynak noktalari (her cizimde yenilenir)
        self._surukle = None
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.addWidget(self.tuval)
        for olay, islev in (("scroll_event", self._teker), ("button_press_event", self._bas),
                            ("button_release_event", self._birak),
                            ("motion_notify_event", self._hareket)):
            self.tuval.mpl_connect(olay, islev)
        self.mesaj(_("Model bekleniyor"))

    # ------------------------------------------------------------------
    def mesaj(self, metin, hata=False) -> None:
        self._renk_cubugu_kaldir()
        self._taban, self._ekler = None, []
        _bos(self.figur, self.ax, metin, hata)
        self.tuval.draw_idle()

    def _renk_cubugu_kaldir(self) -> None:
        if self._renk_cubugu is not None:
            self._renk_cubugu.remove()
            self._renk_cubugu = None

    def ciz(self, img, g: gr.Gorunum, baslik_metni, bindirme=None, noktalar=None) -> None:
        """img RGBA; bindirme (Raster, saydamlik, birim) | None; noktalar (u, v) | None."""
        self._renk_cubugu_kaldir()
        ax = self.ax
        for ek in self._ekler:
            ek.remove()
        self._ekler = []
        self._taban_koy(ax, self._seyrelt(img), g.kapsam)
        if bindirme is not None:
            self._bindir(ax, *bindirme)
        if noktalar is not None and len(noktalar[0]):
            self._ekler.append(ax.scatter(
                noktalar[0], noktalar[1], s=_NOKTA_BOYU, marker=".", linewidths=0,
                color=tokenlar.OKABE_ITO["gok"], label=_("kaynak noktaları")))
        h, d, _n = gr.EKSENLER[g.eksen]
        ax.set_xlim(g.kapsam[0], g.kapsam[1])
        ax.set_ylim(g.kapsam[2], g.kapsam[3])
        ax.set_xlabel("%s [cm]" % gr.EKSEN_ADLARI[h], fontsize=_YAZI)
        ax.set_ylabel("%s [cm]" % gr.EKSEN_ADLARI[d], fontsize=_YAZI)
        ax.set_title(baslik_metni, fontsize=_YAZI)
        ax.tick_params(labelsize=_YAZI - 1)
        self.tuval.draw_idle()

    def _seyrelt(self, img):
        """Ekran pikselinin _GORUNUM_KATI katindan buyuk goruntu seyreltilir: tam
        cozunurluk yakinlastirinca yeni dilimle gelir; ana is parcacigi cizimi kisalir."""
        hedef = max(1, _GORUNUM_KATI * self.tuval.width())
        adim = max(1, img.shape[1] // hedef)
        return img[::adim, ::adim] if adim > 1 else img

    def _taban_koy(self, ax, img, kapsam) -> None:
        """Geometri resmi: eksen bir kez kurulur, sonra yalniz veri degisir (ax.clear +
        imshow her cizimde tik nesnelerini yeniden kuruyordu: ~70 ms, olculdu)."""
        if self._taban is None:
            ax.clear()
            ax.set_axis_on()
            self._taban = ax.imshow(img, extent=kapsam, interpolation="nearest")
            return
        self._taban.set_data(img)
        self._taban.set_extent(kapsam)

    def _bindir(self, ax, raster, saydamlik, birim) -> None:
        if not np.isfinite(raster.aralik[0]):
            return
        im = ax.imshow(np.ma.masked_invalid(raster.deger), extent=raster.kapsam,
                       interpolation="nearest", cmap=tokenlar.GRAFIK_HARITASI,
                       alpha=saydamlik, vmin=raster.aralik[0], vmax=raster.aralik[1])
        self._ekler.append(im)
        self._renk_cubugu = self.figur.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        self._renk_cubugu.set_label(birim, fontsize=_YAZI)
        self._renk_cubugu.ax.tick_params(labelsize=_YAZI - 1)

    # ------------------------------------------------------------------
    def _teker(self, olay) -> None:
        if olay.inaxes is not self.ax or olay.xdata is None:
            return
        kat = TEKER_KATI if olay.button == "up" else 1.0 / TEKER_KATI
        self.yakinlastir.emit(kat, float(olay.xdata), float(olay.ydata))

    def _bas(self, olay) -> None:
        if olay.inaxes is self.ax and olay.button == 1 and olay.xdata is not None:
            self._surukle = (float(olay.xdata), float(olay.ydata))

    def _birak(self, olay) -> None:
        bas, self._surukle = self._surukle, None
        if bas is None or olay.xdata is None or olay.inaxes is not self.ax:
            return
        du, dv = bas[0] - float(olay.xdata), bas[1] - float(olay.ydata)
        if du or dv:
            self.kaydir.emit(du, dv)

    def _hareket(self, olay) -> None:
        if olay.inaxes is self.ax and olay.xdata is not None:
            self.fare_hareketi.emit(float(olay.xdata), float(olay.ydata))


class GoruntuTuvali(QtWidgets.QWidget):
    """3B golgeli goruntu tuvali."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.figur = Figure(figsize=(6, 5))
        self.tuval = Tuval(self.figur)
        self.ax = self.figur.add_axes((0.0, 0.0, 1.0, 1.0))
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.addWidget(self.tuval)
        self.mesaj(_("3B görünüm için “Çiz”e basın"))

    def piksel(self) -> tuple:
        """Tuvalin ekran pikseli (genislik, yukseklik)."""
        return max(self.tuval.width(), 1), max(self.tuval.height(), 1)

    def mesaj(self, metin, hata=False) -> None:
        _bos(self.figur, self.ax, metin, hata)
        self.tuval.draw_idle()

    def ciz(self, rgb) -> None:
        self.ax.clear()
        self.ax.set_axis_off()
        self.ax.imshow(rgb, interpolation="nearest")
        self.tuval.draw_idle()
