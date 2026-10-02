# -*- coding: utf-8 -*-
"""
panel.py -- Kosu gecmisi ve iki kosunun karsilastirilmasi (Y10).

Ust: gecmis tablosu (cekirdek.kosu_gecmisi.GecmisDeposu); iki satir secilip
"Karsilastir" ya da "Iki klasor sec…". Alt: k farki ozeti (Δk, σ, z,
anlamlilik, Δρ), pin gucu fark tablosu (|z|'ye gore sirali) ve kare kafeste
fark haritasi (Δ bagil guc; sifir merkezli iki yonlu renk olcegi). Hesap
cekirdek.kosu_gecmisi'ndedir; burada yalniz gosterim vardir.
"""

from __future__ import annotations

from typing import List, Optional

import matplotlib
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6 import QtCore, QtWidgets

from cekirdek import guc as _guc
from cekirdek import kosu_gecmisi as kg
from cekirdek.ceviri import N_, _
from cekirdek.gunluk import kaydedici
from arayuz import tema
from arayuz.tasarim import tokenlar

matplotlib.use("QtAgg")
_log = kaydedici(__name__)
A = tokenlar.ARALIK
_GECMIS_SUTUNLARI = (N_("Ad"), N_("Durum"), N_("k ± σ"), N_("Süre"), N_("Dizin"))
_FARK_SUTUNLARI = (N_("Konum"), N_("Bağıl güç 1"), N_("Bağıl güç 2"), N_("Δ"), N_("z"))
_GOSTERILEN_PIN = 400      # fark tablosunda en cok bu kadar satir (|z| sirali)
_RENK_HARITASI = "RdBu_r"  # iki yonlu: mavi = 2 dusuk, kirmizi = 2 yuksek


def k_ozeti(f: kg.KFarki) -> str:
    """k farkinin okunur ozeti (birden cok satir)."""
    hukum = (_("anlamlı (|z| > %g)") % kg.ANLAMLILIK_ESIGI if f.anlamli
             else _("anlamlı değil (|z| ≤ %g): fark istatistik gürültü içinde")
             % kg.ANLAMLILIK_ESIGI)
    return "\n".join([
        _("koşu 1: k = %.5f ± %.5f") % (f.k1, f.s1),
        _("koşu 2: k = %.5f ± %.5f") % (f.k2, f.s2),
        _("Δk = k2 − k1 = %+.5f ± %.5f  (%+.0f ± %.0f pcm)")
        % (f.fark, f.sigma, f.fark * kg.PCM, f.sigma * kg.PCM),
        _("Δρ = %+.0f ± %.0f pcm") % (f.rho_fark_pcm, f.rho_sigma_pcm),
        _("z = Δk / √(σ1² + σ2²) = %+.2f → %s") % (f.z, hukum),
        _("Varsayım: koşular bağımsız. Aynı tohumla koşulan modeller ilişkilidir; "
          "o zaman gerçek σ daha küçüktür ve bu z muhafazakârdır."),
    ])


def guc_ozeti(g: kg.GucFarki) -> str:
    n = len(g.farklar)
    satirlar = [_("%d ortak konum; RMS Δ = %.4f; en büyük fark: %s")
                % (n, g.rms_fark, _guc.konum_metni(g.en_buyuk) if g.en_buyuk is not None
                   else "—"),
                _("|z| > %g olan konum: %d (yalnız tesadüfle ~%.1f beklenir)")
                % (kg.ANLAMLILIK_ESIGI, g.anlamli_sayisi, g.beklenen_tesaduf)]
    if g.yalniz1 or g.yalniz2:
        satirlar.append(_("Yalnız bir koşuda olan konum: %d / %d") % (len(g.yalniz1),
                                                                      len(g.yalniz2)))
    return "\n".join(satirlar)


class KarsilastirmaPaneli(QtWidgets.QWidget):
    """Gecmis + iki kosu karsilastirmasi."""

    def __init__(self, gecmis: Optional[kg.GecmisDeposu] = None,
                 parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.gecmis = gecmis
        self.sonuc: Optional[kg.Karsilastirma] = None
        self._kur()
        self.yenile()

    def _kur(self) -> None:
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(A["l"], A["l"], A["l"], A["l"])
        duzen.setSpacing(A["m"])
        self.gecmis_tablo = self._tablo(_GECMIS_SUTUNLARI)
        self.gecmis_tablo.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        duzen.addWidget(self.gecmis_tablo, 2)
        duzen.addLayout(self._dugmeler())
        self.ozet = QtWidgets.QLabel(_("İki koşu seçin (Ctrl ile) ve Karşılaştır'a basın."), self)
        self.ozet.setWordWrap(True)
        self.ozet.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        duzen.addWidget(self.ozet)
        alt = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        self.fark_tablo = self._tablo(_FARK_SUTUNLARI)
        alt.addWidget(self.fark_tablo)
        self.figur = Figure(figsize=(4, 4), facecolor=tema.renk("yuzey1"))
        self.tuval = FigureCanvasQTAgg(self.figur)
        alt.addWidget(self.tuval)
        duzen.addWidget(alt, 3)

    def _tablo(self, sutunlar) -> QtWidgets.QTableWidget:
        t = QtWidgets.QTableWidget(0, len(sutunlar), self)
        t.setHorizontalHeaderLabels([_(s) for s in sutunlar])
        t.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        t.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        t.horizontalHeader().setStretchLastSection(True)
        t.verticalHeader().setVisible(False)
        return t

    def _dugmeler(self) -> QtWidgets.QHBoxLayout:
        satir = QtWidgets.QHBoxLayout()
        for metin, yuva in ((_("Yenile"), self.yenile),
                            (_("Seçili iki koşuyu karşılaştır"), self._secilileri_karsilastir),
                            (_("İki klasör seç…"), self._klasor_sec)):
            d = QtWidgets.QPushButton(metin, self)
            d.clicked.connect(yuva)
            satir.addWidget(d)
        satir.addStretch(1)
        return satir

    # ------------------------------------------------------------------
    def yenile(self) -> None:
        kayitlar = self.gecmis.listele() if self.gecmis is not None else []
        self.gecmis_tablo.setRowCount(len(kayitlar))
        for i, r in enumerate(kayitlar):
            k = "%.5f ± %.5f" % (r.keff, r.sapma) if r.keff is not None else "—"
            sure = "%.1f s" % r.sure if r.sure is not None else "—"
            for j, metin in enumerate((r.ad, _(r.durum), k, sure, r.dizin)):
                oge = QtWidgets.QTableWidgetItem(metin)
                if j == 0:
                    oge.setData(QtCore.Qt.UserRole, r.dizin)
                self.gecmis_tablo.setItem(i, j, oge)

    def _secili_dizinler(self) -> List[str]:
        satirlar = sorted(i.row() for i in self.gecmis_tablo.selectionModel().selectedRows())
        return [self.gecmis_tablo.item(s, 0).data(QtCore.Qt.UserRole) for s in satirlar]

    def _secilileri_karsilastir(self) -> None:
        dizinler = self._secili_dizinler()
        if len(dizinler) != 2:
            self._ozet_yaz(_("Tam olarak iki koşu seçin."), "uyari")
            return
        # gecmis en yeni once listelenir: eski = 1, yeni = 2
        self.karsilastir(dizinler[1], dizinler[0])

    def _klasor_sec(self) -> None:
        d1 = QtWidgets.QFileDialog.getExistingDirectory(self, _("1. koşu klasörü"))
        if not d1:
            return
        d2 = QtWidgets.QFileDialog.getExistingDirectory(self, _("2. koşu klasörü"))
        if d2:
            self.karsilastir(d1, d2)

    def karsilastir(self, dizin1: str, dizin2: str) -> Optional[kg.Karsilastirma]:
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            self.sonuc = kg.kosulari_karsilastir(dizin1, dizin2)
        except Exception as e:
            # statepoint bozuk / eksik: kullaniciya goster, iz loga
            _log.exception("kosular karsilastirilamadi: %s, %s", dizin1, dizin2)
            self._ozet_yaz(_("Karşılaştırılamadı: %s") % e, "hata")
            self.sonuc = None
            return None
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        self._goster(self.sonuc)
        return self.sonuc

    def _ozet_yaz(self, metin: str, tur: str = "") -> None:
        self.ozet.setText(metin)
        self.ozet.setStyleSheet("color: %s;" % tema.renk(tur) if tur else "")

    def _goster(self, s: kg.Karsilastirma) -> None:
        parcalar = [k_ozeti(s.k)] if s.k else []
        if s.guc:
            parcalar.append(guc_ozeti(s.guc))
        parcalar += list(s.notlar)
        self._ozet_yaz("\n\n".join(parcalar))
        self._fark_tablosu(s.guc)
        self._harita(s.guc)

    def _fark_tablosu(self, g: Optional[kg.GucFarki]) -> None:
        if g is None:
            self.fark_tablo.setRowCount(0)
            return
        sirali = sorted(g.farklar.items(), key=lambda kv: -abs(kv[1].z))[:_GOSTERILEN_PIN]
        self.fark_tablo.setRowCount(len(sirali))
        for i, (a, f) in enumerate(sirali):
            for j, metin in enumerate((_guc.konum_metni(a), "%.4f" % f.deger1, "%.4f" % f.deger2,
                                       "%+.4f ± %.4f" % (f.fark, f.sigma), "%+.2f" % f.z)):
                self.fark_tablo.setItem(i, j, QtWidgets.QTableWidgetItem(metin))

    def _harita(self, g: Optional[kg.GucFarki]) -> None:
        import numpy as np
        self.figur.clear()
        eks = self.figur.add_subplot(111)
        iz = kg.fark_izgarasi(g) if g else None
        if iz is None:
            eks.text(0.5, 0.5, _("Fark haritası yalnız kare kafeste çizilir"),
                     ha="center", va="center", color=tema.renk("metin_soluk"), fontsize=9)
            eks.set_axis_off()
            self.tuval.draw_idle()
            return
        izgara = np.full((iz.ny, iz.nx), np.nan)
        for (x, y), f in iz.hucreler.items():
            izgara[y, x] = f.fark
        sinir = float(np.nanmax(np.abs(izgara))) or 1.0
        im = eks.imshow(izgara, origin="lower", cmap=_RENK_HARITASI, vmin=-sinir, vmax=sinir,
                        interpolation="nearest", extent=(0.5, iz.nx + 0.5, 0.5, iz.ny + 0.5))
        self.figur.colorbar(im, ax=eks, label=_("Δ bağıl güç (2 − 1)"))
        eks.set_title(_("Pin gücü farkı (kırmızı: 2. koşu yüksek)"), fontsize=9)
        eks.tick_params(labelsize=7)
        self.tuval.draw_idle()
