# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_cikti_panel.py  --  Tukenme sonucu: aktivite, bozunma isisi, foton
                             kaynagi, temas doz hizi, atik sinifi (v3 Y4)
================================================================================
 Hesap cekirdek/tukenme_cikti.py'dedir (OpenMC Material API'si). Buyuk zincirde
 (3820 nuklid) adim basina saniyeler surebildigi icin sonuc gelince kendiligin-
 den DEGIL, "Hesapla" ile hesaplanir.
================================================================================
"""

from __future__ import annotations

import math
import os

from matplotlib.figure import Figure
from PySide6 import QtCore, QtWidgets

from cekirdek.ceviri import N_, _
from cekirdek.gunluk import kaydedici
from arayuz import bilesenler as bil
from arayuz.analiz.tuval import Tuval

_log = kaydedici(__name__)
TUVAL_YUKSEKLIGI = 300
TABLO_EN_AZ = 140
SERILER = [("isi", N_("Bozunma ısısı [W]")), ("isi_ozgul", N_("Bozunma ısısı [W/g]")),
           ("aktivite", N_("Aktivite [Bq]")), ("aktivite_ozgul", N_("Aktivite [Bq/g]")),
           ("foton", N_("Foton kaynağı [foton/s]"))]


class TukenmeCiktiPaneli(bil.Kart):
    """Aktivite / bozunma isisi / foton kaynagi karti."""

    def __init__(self, parent=None):
        self.hesapla = QtWidgets.QPushButton(_("Hesapla"))
        super().__init__(_("Aktivite, bozunma ısısı ve foton kaynağı"), eylem=self.hesapla,
                         parent=parent)
        self._kaynak = None
        self._seriler = None
        self.seri = QtWidgets.QComboBox()
        for kod, ad in SERILER:
            self.seri.addItem(_(ad), kod)
        self.durum = QtWidgets.QLabel(_("Sonuç yok."))
        self.durum.setWordWrap(True)
        self.durum.setObjectName("soluk")
        self.figur = Figure(figsize=(5, 3), tight_layout=True)
        self.tuval = Tuval(self.figur)
        self.tuval.setFixedHeight(TUVAL_YUKSEKLIGI)
        self.eksen = self.figur.add_subplot(111)
        self.tablo = QtWidgets.QTableWidget(0, 4)
        self.tablo.setHorizontalHeaderLabels([_("gün"), "Bq", "W", _("foton/s")])
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tablo.setMinimumHeight(TABLO_EN_AZ)
        self.doz = QtWidgets.QLabel("")
        self.doz.setWordWrap(True)
        self.doz.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.csv = QtWidgets.QPushButton(_("Çıktıları CSV olarak dışa aktar"))
        self.csv.setEnabled(False)
        from cekirdek import tukenme_cikti
        not_ = QtWidgets.QLabel(tukenme_cikti.birim_aciklamasi())
        not_.setWordWrap(True)
        not_.setObjectName("soluk")
        for w in (self.durum, self.seri, self.tuval, self.tablo, self.doz, self.csv, not_):
            self.ekle(w)
        self.hesapla.setEnabled(False)
        self.hesapla.clicked.connect(self.hesapla_tikla)
        self.seri.currentIndexChanged.connect(self._ciz)
        self.csv.clicked.connect(self.csv_kaydet)

    # ------------------------------------------------------------------
    def kaynak_ayarla(self, kaynak) -> None:
        """kaynak: (h5, okuma spec'i) ya da None (sonuc yok)."""
        self._kaynak = kaynak
        self._seriler = None
        self.hesapla.setEnabled(kaynak is not None)
        self.csv.setEnabled(False)
        self.tablo.setRowCount(0)
        self.doz.setText("")
        self.eksen.clear()
        self.tuval.draw_idle()
        self.durum.setText(_("Sonuç hazır — «Hesapla» ile çıktıları hesaplayın.")
                           if kaynak else _("Sonuç yok."))

    def hesapla_tikla(self) -> None:
        if self._kaynak is None:
            return
        from cekirdek import tukenme, tukenme_cikti
        h5, spec = self._kaynak
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            self._seriler = tukenme_cikti.cikti_oku(h5, spec)
            r, ad_by_id, _h = tukenme._sonuc_kaynagi(h5, spec)
            doz = tukenme_cikti.doz_ve_atik(r, ad_by_id, self._seriler["zincir"], adim=-1)
        except (OSError, ValueError, KeyError, RuntimeError) as e:
            _log.warning("tükenme çıktıları hesaplanamadı: %s", e, exc_info=True)
            self.durum.setText(_("Çıktılar hesaplanamadı: %s") % e)
            return
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        metin = (_("%d zaman noktası, %d malzeme.")
                 % (len(self._seriler["zaman_d"]), len(self._seriler["malzeme"])))
        if "casl" in os.path.basename(self._seriler.get("zincir") or "").lower():
            metin += " " + _("Basitleştirilmiş CASL zinciri: birçok aktivasyon ürünü (ör. Co-60) "
                             "yok; aktivite ve bozunma ısısı eksik çıkar (kısa ömürlü ürünlerde 10–20×). "
                             "Bu çıktılar için tam ENDF/B-VIII.0 zincirini seçin.")
        self.durum.setText(metin)
        self._tablo_doldur()
        self._doz_yaz(doz)
        self._ciz()
        self.csv.setEnabled(True)

    def _tablo_doldur(self) -> None:
        s = self._seriler
        self.tablo.setRowCount(0)
        for i, t in enumerate(s["zaman_d"]):
            r = self.tablo.rowCount()
            self.tablo.insertRow(r)
            degerler = ("%.4g" % t, "%.4e" % s["toplam"]["aktivite"][i],
                        "%.4e" % s["toplam"]["isi"][i], "%.4e" % s["toplam"]["foton"][i])
            for c, metin in enumerate(degerler):
                self.tablo.setItem(r, c, QtWidgets.QTableWidgetItem(metin))
        self.tablo.resizeColumnsToContents()

    def _doz_yaz(self, doz: dict) -> None:
        from cekirdek import tukenme_cikti
        satirlar = []
        for ad, v in doz.items():
            if v.get("hata"):
                satirlar.append(_("%s: hesaplanamadı (%s)") % (ad, v["hata"]))
            else:
                atik = (_("uygulanamaz (tabloda nüklid yok / yanma ≈ 0)")
                        if v["atik_sinifi"] == tukenme_cikti.ATIK_UYGULANAMAZ else v["atik_sinifi"])
                satirlar.append(_("%s: temas doz hızı %.4g Gy(hava)/h (yarı sonsuz levha, yalnız yakıt, "
                                  "havada soğurulan doz; hacimden bağımsız, kılıf yok: üst sınır "
                                  "göstergesi) · atık sınıfı: NRC 10 CFR 61.55 tablo karşılaştırması "
                                  "(yakın-yüzey; kullanılmış yakıt için geçerli değil) %s")
                                % (ad, v["doz_gy_h"], atik))
        self.doz.setText(_("Son adımda:\n") + "\n".join(satirlar))

    def _ciz(self, *_a) -> None:
        from arayuz import tema as _t
        self.eksen.clear()
        self.eksen.grid(alpha=0.3)
        self.eksen.tick_params(labelsize=7)
        if not self._seriler:
            self.tuval.draw_idle()
            return
        kod = self.seri.currentData()
        x = self._seriler["zaman_d"]
        for ad, m in self._seriler["malzeme"].items():
            noktalar = [(a, b) for a, b in zip(x, m[kod]) if b > 0 and math.isfinite(b)]
            if noktalar:
                self.eksen.plot(*zip(*noktalar), "o-", ms=3, lw=1.1, label=ad)
        self.eksen.set_yscale("log")
        self.eksen.set_xlabel(_("zaman [gün]"), fontsize=8)
        self.eksen.set_ylabel(self.seri.currentText(), fontsize=8, color=_t.renk("metin"))
        if self._seriler["malzeme"]:
            self.eksen.legend(fontsize=7, loc="best")
        self.tuval.draw_idle()

    def csv_kaydet(self) -> None:
        if not self._seriler:
            return
        from cekirdek import tukenme_cikti
        dizin = os.path.dirname(self._kaynak[0]) if self._kaynak else os.getcwd()
        yol, _f = QtWidgets.QFileDialog.getSaveFileName(
            self, _("Çıktıları kaydet"), os.path.join(dizin, "tukenme_cikti.csv"), "CSV (*.csv)")
        if not yol:
            return
        try:
            with open(yol, "w", encoding="utf-8", newline="") as f:
                f.write(tukenme_cikti.csv_metni(self._seriler))
        except OSError as e:
            QtWidgets.QMessageBox.warning(self, _("Kaydedilemedi"), str(e))
