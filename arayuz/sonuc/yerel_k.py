# -*- coding: utf-8 -*-
"""
================================================================================
 yerel_k.py  --  Yerel k haritasi (v3 K4)
================================================================================
 cekirdek/yerel_k.py sonucunu pin/demet izgarasi olarak cizer. Guc haritasiyla
 (arayuz/guc_harita.py) ayni kurallar: x soldan / y alttan 1 tabanli, beyaz =
 yakitsiz konum, renk olcegi eksenin yaninda, ozet kutusu, PNG kaydet; ek
 olarak CSV ve fare ipucu (konum, k ± σ).

   w = YerelKHaritasi()
   w.kosu_sonucu_ayarla(kosucu.sonuc_oku(sp), spec)   # ya da sonuclari_ayarla([...])

 Ana pencereye/sonuc sekmesine baglanti orkestratorun isidir (sekme dosyalari
 K4'un sahipliginde degil). Bagimsiz: python -m arayuz.sonuc.yerel_k sp.h5 model.json
================================================================================
"""

from __future__ import annotations

import html
import math
import sys
from typing import Any, List, Mapping, Optional, Sequence

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from PySide6 import QtCore, QtWidgets  # noqa: E402

from cekirdek import yerel_k as _yk  # noqa: E402
from cekirdek.ceviri import _  # noqa: E402
from cekirdek.gunluk import kaydedici  # noqa: E402
from arayuz import tema  # noqa: E402
from arayuz.ortak import GelismisBolum, baslik  # noqa: E402

_log = kaydedici(__name__)
_DEGER_YAZMA_SINIRI = 400          # bundan cok binde deger yazilmaz (guc haritasiyla ayni)
_DUZEY_ADLARI = {"pin": "Pin", "demet": "Demet"}


class YerelKHaritasi(QtWidgets.QWidget):
    """Yerel k (sizintisiz yerel cogalma orani) haritasi ve ozeti."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.sonuclar: List[_yk.YerelKSonucu] = []
        self.duzey = QtWidgets.QComboBox()
        self.duzey_etiket = QtWidgets.QLabel(_("Düzey:"))
        self.degerler = QtWidgets.QCheckBox(_("Değerleri haritaya yaz"))
        self.d_csv = QtWidgets.QPushButton(_("CSV kaydet…"))
        self.d_png = QtWidgets.QPushButton(_("PNG kaydet…"))
        self.ozet = QtWidgets.QLabel()
        self.ozet.setWordWrap(True)
        self.ozet.setTextFormat(QtCore.Qt.RichText)
        self.ozet.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.figur = Figure(figsize=(6, 4), tight_layout=True)
        self.tuval = FigureCanvasQTAgg(self.figur)
        self.tuval.setMinimumHeight(380)
        self.tuval.mpl_connect("motion_notify_event", self._fare_hareketi)
        self.gelismis = GelismisBolum("yerel_k_gelismis")
        self.gelismis.ekle(self.degerler)
        self.gelismis.ekle(NavigationToolbar2QT(self.tuval, self))
        self._yerlesim()
        self.duzey.currentIndexChanged.connect(self._yenile)
        self.degerler.toggled.connect(self._ciz)
        self.d_csv.clicked.connect(self._csv_sor)
        self.d_png.clicked.connect(self._png_sor)
        self._bos(_("Yerel k hesaplanmadı. Modele yerel k tally'si ekleyip yeniden "
                    "çalıştırın."))

    def _yerlesim(self) -> None:
        ust = QtWidgets.QHBoxLayout()
        for w in (self.duzey_etiket, self.duzey):
            ust.addWidget(w)
        ust.addStretch(1)
        ust.addWidget(self.d_csv)
        ust.addWidget(self.d_png)
        aciklama = QtWidgets.QLabel(_(
            "k_yerel = νΣ_f φ / (Σ_a φ − X) her pin/demet hücresinde: yerel üretim / yok olma "
            "oranı (sızıntı ve net akım terimi içermez), k∞ değildir. Akı komşulardan gelen "
            "nötronları içerir; oranı hücredeki spektrum belirler. X: (n,xn) tepkimelerinin "
            "net nötron üretimi (OpenMC 'absorption'ı bunları saymaz)."))
        aciklama.setObjectName("soluk")
        aciklama.setWordWrap(True)
        belirsizlik = QtWidgets.QLabel(_(
            "Belirsizlik: σ, pay ile payda arasındaki korelasyon yok sayılarak yayılır "
            "(ihtiyatlı); bin σ'ları çevrimler arası korelasyonu görmez (iyimser). Gerçek "
            "belirsizlik için modeli birkaç tohumla koşun."))
        belirsizlik.setObjectName("soluk")
        belirsizlik.setWordWrap(True)
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.addWidget(baslik(_("Yerel k haritası")))
        duzen.addWidget(aciklama)
        duzen.addLayout(ust)
        duzen.addWidget(self.ozet)
        duzen.addWidget(self.tuval, 1)
        duzen.addWidget(belirsizlik)
        duzen.addWidget(self.gelismis)

    # ------------------------------------------------------------------
    def kosu_sonucu_ayarla(self, sonuc: Mapping[str, Any], spec: Mapping[str, Any],
                           statepoint: Optional[str] = None) -> None:
        """kosucu.sonuc_oku ciktisi + spec (+ statepoint: global denge, sizinti
        denetimi). Hata gosterilir, yutulmaz."""
        denge = None
        if statepoint:
            try:
                denge = _yk.denge_oku(statepoint)
            except (_yk.YerelKHatasi, OSError, KeyError) as e:
                _log.warning("global denge okunamadı (%s); sızıntı denetimi yok", e)
        try:
            sonuclar = _yk.sonuctan(sonuc, spec, denge=denge)
        except _yk.YerelKHatasi as e:
            _log.warning("yerel k okunamadı: %s", e)
            self.sonuclari_ayarla([], _("Yerel k okunamadı: %s") % e)
            return
        self.sonuclari_ayarla(sonuclar)

    def sonuclari_ayarla(self, sonuclar: Sequence[_yk.YerelKSonucu],
                         bos_metni: Optional[str] = None) -> None:
        self.sonuclar = list(sonuclar)
        eski = self.duzey.blockSignals(True)
        try:
            self.duzey.clear()
            for s in self.sonuclar:
                self.duzey.addItem(_(_DUZEY_ADLARI.get(s.duzey, s.duzey)), s.duzey)
        finally:
            self.duzey.blockSignals(eski)
        for w in (self.duzey, self.duzey_etiket):
            w.setVisible(len(self.sonuclar) > 1)
        for w in (self.d_csv, self.d_png):
            w.setEnabled(bool(self.sonuclar))
        if not self.sonuclar:
            metin = bos_metni or _("Yerel k hesaplanmadı: bu koşuda yerel k tally'si yok.")
            self.ozet.setText(html.escape(metin))
            self._bos(metin)
            return
        self._yenile()

    def secili(self) -> Optional[_yk.YerelKSonucu]:
        i = max(self.duzey.currentIndex(), 0)
        return self.sonuclar[i] if self.sonuclar else None

    def _yenile(self) -> None:
        self._ozet_yaz()
        self._ciz()

    def _ozet_yaz(self) -> None:
        s = self.secili()
        k, sk = s.ortalama
        p = [_("<b>ortalama k = %.5f ± %.5f</b> (net yok olma ağırlıklı = Σ νΣ_f φ / "
               "Σ (Σ_a φ − X))") % (k, sk)]
        if s.keff:
            p.append(_("koşunun k-eff'i %.5f ± %.5f") % tuple(s.keff))
        p.append(_("c_xn = %.5f") % s.c_xn)
        if s.kapsama is not None:
            p.append(_("harita kapsamı (net yok olma payı): %.4f") % s.kapsama)
        if s.sizintili_k is not None:
            p.append(_("P/(D+L) = %.5f (sızıntı L = %.5f; k-eff ile karşılaştırın)")
                     % (s.sizintili_k, s.denge.sizinti[0]))
        fisil = [h.k for h in s.hucreler if h.fisil and math.isfinite(h.k)]
        if fisil:
            p.append(_("en düşük / en yüksek: %.4f / %.4f") % (min(fisil), max(fisil)))
        metin = " &nbsp;|&nbsp; ".join(p)
        metin += "<br>" + _("Yerel üretim / yok olma oranı (sızıntı ve net akım terimi "
                            "içermez), k∞ değildir. Ortalama yalnız sonsuz kafeste (yansıtıcı "
                            "sınır, kapsam %100) k∞'a eşittir; kritiklik globaldir: "
                            "k_eff = ΣP / (ΣD + L).")
        self.ozet.setText(metin)

    # ------------------------------------------------------------------
    def izgara(self) -> List[List[float]]:
        """[y][x] k degerleri; yakitsiz bin NaN."""
        s = self.secili()
        nx, ny = s.boyut
        iz = [[math.nan] * nx for _y in range(ny)]
        for h in s.hucreler:
            if h.fisil:
                iz[h.konum[1]][h.konum[0]] = h.k
        return iz

    def _bos(self, metin: str) -> None:
        self.figur.clear()
        eks = self.figur.add_subplot(111)
        eks.set_axis_off()
        eks.text(0.5, 0.5, metin, ha="center", va="center", fontsize=10, wrap=True,
                 color=tema.renk("metin_soluk"))
        self.tuval.draw_idle()

    def _ciz(self) -> None:
        s = self.secili()
        if s is None:
            return
        import numpy as np
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        self.figur.clear()
        eks = self.figur.add_subplot(111)
        nx, ny = s.boyut
        iz = np.array(self.izgara(), dtype=float)
        im = eks.imshow(iz, origin="lower", cmap="viridis", interpolation="nearest",
                        extent=(0.5, nx + 0.5, 0.5, ny + 0.5))
        cax = make_axes_locatable(eks).append_axes("right", size="4%", pad=0.08)
        self.figur.colorbar(im, cax=cax, label=_("k_yerel"))
        eks.set_xlabel(_("x (soldan)"), fontsize=8)
        eks.set_ylabel(_("y (alttan)"), fontsize=8)
        eks.tick_params(labelsize=7)
        eks.set_title(_("Yerel k — %s düzeyi\nbeyaz: yakıtsız konum (k = 0)")
                      % _(_DUZEY_ADLARI.get(s.duzey, s.duzey)).lower(), fontsize=8)
        if self.degerler.isChecked() and nx * ny <= _DEGER_YAZMA_SINIRI:
            for h in s.hucreler:
                if h.fisil:
                    eks.text(h.konum[0] + 1, h.konum[1] + 1, "%.3f" % h.k, ha="center",
                             va="center", fontsize=5, color="white")
        self.tuval.draw_idle()

    # ------------------------------------------------------------------
    def ipucu_metni(self, x_cm: float, y_cm: float) -> Optional[str]:
        """Model koordinatindaki (cm; kafes merkezli) binin ipucu; disarida None."""
        s = self.secili()
        if s is None:
            return None
        (nx, ny), (px, py) = s.boyut, s.adim
        ix = math.floor((x_cm + px * nx / 2.0) / px)
        iy = math.floor((y_cm + py * ny / 2.0) / py)
        h = next((h for h in s.hucreler if h.konum == (ix, iy)), None)
        if h is None:
            return None
        if not h.fisil:
            return _("(%d, %d): yakıtsız") % (ix + 1, iy + 1)
        return _("(%d, %d): k_yerel = %.5f ± %.5f (xn düzeltmesiz %.5f)") % (
            ix + 1, iy + 1, h.k, h.sigma, h.k_xn_siz)

    def _fare_hareketi(self, olay: Any) -> None:
        s = self.secili()
        if s is None or olay.inaxes is None or olay.xdata is None:
            return
        # eksen 1 tabanli bin numarasi -> model koordinati
        x = (olay.xdata - 0.5) * s.adim[0] - s.adim[0] * s.boyut[0] / 2.0
        y = (olay.ydata - 0.5) * s.adim[1] - s.adim[1] * s.boyut[1] / 2.0
        metin = self.ipucu_metni(x, y)
        if metin:
            from PySide6 import QtGui
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), metin, self.tuval)
        else:
            QtWidgets.QToolTip.hideText()

    def csv_kaydet(self, yol: str) -> None:
        with open(yol, "w", encoding="utf-8", newline="") as f:
            f.write(_yk.csv_metni(self.secili()))

    def _csv_sor(self) -> None:
        yol, _s = QtWidgets.QFileDialog.getSaveFileName(
            self, _("Yerel k tablosunu kaydet"), "yerel_k.csv", "CSV (*.csv)")
        if yol:
            try:
                self.csv_kaydet(yol)
            except OSError as e:
                _log.warning("yerel k CSV yazılamadı", exc_info=True)
                QtWidgets.QMessageBox.warning(self, _("Yerel k"), _("Kaydedilemedi: %s") % e)

    def _png_sor(self) -> None:
        yol, _s = QtWidgets.QFileDialog.getSaveFileName(
            self, _("Yerel k haritasını kaydet"), "yerel_k.png", "PNG (*.png)")
        if yol:
            self.figur.savefig(yol, dpi=150, bbox_inches="tight")


def main(argv: Optional[List[str]] = None) -> int:
    """python -m arayuz.sonuc.yerel_k statepoint.h5 model.json"""
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2:
        sys.stderr.write("kullanım: python -m arayuz.sonuc.yerel_k statepoint.h5 model.json\n")
        return 2
    from cekirdek import kosucu, sema
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    tema.uygula(uyg)
    w = YerelKHaritasi()
    w.kosu_sonucu_ayarla(kosucu.sonuc_oku(argv[0]), sema.yukle(argv[1]))
    w.resize(900, 700)
    w.show()
    return uyg.exec()


if __name__ == "__main__":
    sys.exit(main())
