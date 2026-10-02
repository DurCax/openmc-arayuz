# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_pin_gucu.py  --  Tukenme sonucu: yanmaya gore pin gucu
================================================================================
 cekirdek/tukenme_guc.adim_gucleri ciktisini gosterir (tukenmenin her adim
 basindaki guc dagilimi):
   adim secici          o adimin pin tablosu (arayuz/guc_harita_tablo.PinTablosu:
                        sirala, suz, ceyrek katla, CSV/Excel)
   grafik (sol)         SECILI pinlerin bagil gucu ve yanma; tablodan secilen
                        her pin listeye eklenir (en cok SECILI_EN_COK)
   grafik (sag)         adim basina F_ΔH ve F_q (3B)
   tepe faktoru tablosu adim, gun, MWd/kg, F_ΔH ± σ, F_q ± σ, en yuksek q′
   disa aktarma         adim × pin CSV / Excel; tepe faktorleri CSV
 Hesap yapmaz; degerler adim tablolarinin kendisidir. σ'lar tek kosu σ'sidir
 (iyimser; cekirdek/guc.py basligi).
================================================================================
"""

from matplotlib.figure import Figure

from PySide6 import QtWidgets

from cekirdek import guc as _guc
from cekirdek import guc_tablo
from cekirdek import tukenme_guc as _tg
from cekirdek.ceviri import _, pgettext
from cekirdek.gunluk import kaydedici
from arayuz import tema
from arayuz.analiz.tuval import Tuval
from arayuz.guc_harita_tablo import PinTablosu, dosya_sor

_log = kaydedici(__name__)

SECILI_EN_COK = 6           # grafikte ayni anda izlenen pin sayisi (okunurluk)
TUVAL_YUKSEKLIGI = 340      # px
FAKTOR_TABLOSU_EN_AZ = 120  # px


class PinGucuYanma(QtWidgets.QWidget):
    """Yanmaya gore pin gucu bolumu (tukenme sonuc karti icinde)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sonuc, self._spec, self._secili = None, None, []
        self.adim = QtWidgets.QComboBox()
        self.adim.setAccessibleName(_("Tükenme adımı"))
        self.adim.currentIndexChanged.connect(self._adim_degisti)
        self.d_temizle = QtWidgets.QPushButton(_("Seçimi temizle"))
        self.d_temizle.clicked.connect(self._secimi_temizle)
        self.d_kaydet = QtWidgets.QPushButton(_("Adım × pin kaydet…"))
        self.d_kaydet.setToolTip(_("Her adımın pin tablosu tek dosyada (CSV; openpyxl "
                                   "kuruluysa Excel)"))
        self.d_kaydet.clicked.connect(self._kaydet_sor)
        self.d_faktor = QtWidgets.QPushButton(_("Tepe faktörleri CSV…"))
        self.d_faktor.clicked.connect(self._faktor_kaydet_sor)
        self.notlar = QtWidgets.QLabel("")
        self.notlar.setObjectName("soluk")
        self.notlar.setWordWrap(True)
        self.eski_etiket = QtWidgets.QLabel(_(
            "Eski sonuç: model bu koşudan beri değişti; adım başına güç bu modele ait değil."))
        self.eski_etiket.setWordWrap(True)
        self.eski_etiket.setStyleSheet("color: %s; font-weight: bold;" % tema.renk("hata"))
        self.eski_etiket.setVisible(False)
        self.pin_tablosu = PinTablosu(dosya_adi="pin_gucu_adim")
        self.pin_tablosu.pin_secildi.connect(self._pin_secildi)
        self.figur = Figure(figsize=(6, 3.4), tight_layout=True)
        self.tuval = Tuval(self.figur)
        self.tuval.setFixedHeight(TUVAL_YUKSEKLIGI)
        self.eksen_pin = self.figur.add_subplot(121)
        self.eksen_f = self.figur.add_subplot(122)
        self.faktor_tablosu = QtWidgets.QTableWidget(0, 6)
        self.faktor_tablosu.setHorizontalHeaderLabels(
            [pgettext("tükenme", "adım"), _("gün"), "MWd/kg", "F_ΔH", "F_q", _("en yüksek q′ [W/cm]")])
        self.faktor_tablosu.verticalHeader().setVisible(False)
        self.faktor_tablosu.horizontalHeader().setStretchLastSection(True)
        self.faktor_tablosu.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.faktor_tablosu.setMinimumHeight(FAKTOR_TABLOSU_EN_AZ)
        self._yerlestir()
        self.ayarla(None)

    def _yerlestir(self):
        ust = QtWidgets.QHBoxLayout()
        ust.setContentsMargins(0, 0, 0, 0)
        ust.addWidget(QtWidgets.QLabel(_("Adım:")))
        ust.addWidget(self.adim, 1)
        ust.addWidget(self.d_temizle)
        ust.addWidget(self.d_faktor)
        ust.addWidget(self.d_kaydet)
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        aciklama = QtWidgets.QLabel(_(
            "Her tükenme adımının başındaki çubuk güç dağılımı. Tablodan seçilen çubuklar "
            "grafikte izlenir; bağıl güç o adımın yakıt çubuğu ortalamasına göredir."))
        aciklama.setObjectName("soluk")
        aciklama.setWordWrap(True)
        duzen.addWidget(aciklama)
        duzen.addLayout(ust)
        duzen.addWidget(self.eski_etiket)
        duzen.addWidget(self.notlar)
        duzen.addWidget(self.tuval)
        duzen.addWidget(self.faktor_tablosu)
        duzen.addWidget(self.pin_tablosu, 1)

    # ------------------------------------------------------------------
    def ayarla(self, sonuc, spec=None):
        """sonuc: tukenme_guc.adim_gucleri ciktisi ya da None (bolum gizlenir)."""
        self._sonuc, self._spec = sonuc, spec
        adimlar = _tg.gecerli_adimlar(sonuc)
        eski = self.adim.blockSignals(True)
        try:
            self.adim.clear()
            for a in adimlar:
                self.adim.addItem(_("adım %d — %.4g gün, %.4g MWd/kg")
                                  % (a["adim"], a["zaman_d"], a["yanma"]), a["adim"])
        finally:
            self.adim.blockSignals(eski)
        self.notlar.setText("<br>".join((sonuc or {}).get("notlar") or []))
        self.notlar.setVisible(bool((sonuc or {}).get("notlar")))
        for w in (self.d_kaydet, self.d_faktor, self.d_temizle):
            w.setEnabled(bool(adimlar))
        self._secili = []
        if adimlar:
            sicak = adimlar[0]["guc"]["faktorler"]["sicak_cubuk"]
            self._secili = [sicak]
        self._faktor_tablosu_doldur()
        self._adim_degisti()

    def eski_ayarla(self, eski):
        """Gosterilen tukenme sonucu su anki modele ait degilse uyari."""
        self.eski_etiket.setVisible(bool(eski))

    def gosterilecek_mi(self):
        """Gosterilecek adim ya da not var mi (gorunurlugu ev sahibi ayarlar)."""
        return bool(_tg.gecerli_adimlar(self._sonuc) or (self._sonuc or {}).get("notlar"))

    def _secili_adim(self):
        no = self.adim.currentData()
        for a in _tg.gecerli_adimlar(self._sonuc):
            if a["adim"] == no:
                return a
        return None

    def _adim_degisti(self, *_a):
        a = self._secili_adim()
        if a is None:
            self.pin_tablosu.ayarla([])
        else:
            g = a["guc"]
            self.pin_tablosu.ayarla(
                a["tablo"], g["dagilim"], self._spec,
                notlar=guc_tablo.yorum_notlari(g["dagilim"], g["faktorler"],
                                               g.get("hedef_payi"), self._spec),
                iki_boyut=bool((self._sonuc or {}).get("iki_boyut")))
        self._ciz()

    def _pin_secildi(self, anahtar):
        if anahtar in self._secili:
            self._secili.remove(anahtar)
        self._secili = (self._secili + [anahtar])[-SECILI_EN_COK:]
        self._ciz()

    def _secimi_temizle(self):
        self._secili = []
        self._ciz()

    def seri_noktalari(self, anahtar=None):
        """Son secilen (ya da verilen) pinin serisi: [(yanma, bagil)]."""
        if anahtar is None:
            anahtar = self._secili[-1] if self._secili else None
        return [(p["yanma"], p["bagil"]) for p in _tg.pin_serisi(self._sonuc, anahtar)]

    # ------------------------------------------------------------------
    def _faktor_tablosu_doldur(self):
        seri = _tg.faktor_serisi(self._sonuc)
        self.faktor_tablosu.setRowCount(len(seri))
        for i, x in enumerate(seri):
            fq = ("%.4f ± %.4f" % (x["F_q"], x["F_q_sapma"] or 0.0)) if x["F_q"] else "—"
            q = ("%.1f" % x["lineer_maks"]) if x["lineer_maks"] else "—"
            for j, metin in enumerate(("%d" % x["adim"], "%.4g" % x["zaman_d"],
                                       "%.4g" % x["yanma"],
                                       "%.4f ± %.4f" % (x["F_dH"], x["F_dH_sapma"]), fq, q)):
                self.faktor_tablosu.setItem(i, j, QtWidgets.QTableWidgetItem(metin))
        self.faktor_tablosu.resizeColumnsToContents()

    def _ciz(self):
        for e in (self.eksen_pin, self.eksen_f):
            e.clear()
            e.grid(alpha=0.3)
            e.tick_params(labelsize=7)
            e.set_xlabel(_("yanma [MWd/kg]"), fontsize=8)
        self.eksen_pin.set_ylabel(_("bağıl güç"), fontsize=8)
        self.eksen_f.set_ylabel(_("tepe faktörü"), fontsize=8)
        palet = tema.grafik_paleti()
        a0 = (_tg.gecerli_adimlar(self._sonuc) or [None])[0]
        turler = a0["guc"]["faktorler"].get("kafes_turleri") if a0 else None
        for i, anahtar in enumerate(self._secili):
            seri = _tg.pin_serisi(self._sonuc, anahtar)
            if not seri:
                continue
            self.eksen_pin.errorbar([p["yanma"] for p in seri], [p["bagil"] for p in seri],
                                    yerr=[p["sigma"] for p in seri], fmt="o-", ms=3, lw=1.2,
                                    capsize=2, color=palet[i % len(palet)],
                                    label=_guc.konum_metni(anahtar, None, turler))
        if self._secili:
            self.eksen_pin.legend(fontsize=6, loc="best", ncol=2)
        fs = _tg.faktor_serisi(self._sonuc)
        if fs:
            bu = [x["yanma"] for x in fs]
            self.eksen_f.errorbar(bu, [x["F_dH"] for x in fs], yerr=[x["F_dH_sapma"] for x in fs],
                                  fmt="o-", ms=3, lw=1.2, capsize=2, color=palet[0], label="F_ΔH")
            if all(x["F_q"] for x in fs):
                self.eksen_f.errorbar(bu, [x["F_q"] for x in fs],
                                      yerr=[x["F_q_sapma"] or 0.0 for x in fs], fmt="s-", ms=3,
                                      lw=1.2, capsize=2, color=palet[1], label="F_q")
            self.eksen_f.legend(fontsize=6, loc="best")
        self.tuval.draw_idle()

    # ------------------------------------------------------------------
    def kaydet_yola(self, yol):
        """Adim × pin tablosu (.csv / .xlsx)."""
        return guc_tablo.dosyaya_yaz(yol, _tg.satirlar(self._sonuc), "adim_x_pin")

    def _kaydet_sor(self):
        yol = dosya_sor(self, _("Adım × pin tablosunu kaydet"), "pin_gucu_adimlar",
                        self.pin_tablosu.dosya_suzgeci())
        self._yaz(yol, self.kaydet_yola)

    def _faktor_kaydet_sor(self):
        yol = dosya_sor(self, _("Tepe faktörlerini kaydet"), "tepe_faktorleri_adimlar",
                        _("CSV dosyası (*.csv)"))
        self._yaz(yol, lambda y: guc_tablo.dosyaya_yaz(y, _tg.faktor_satirlari(self._sonuc)))

    def _yaz(self, yol, yazici):
        if not yol:
            return
        try:
            yazici(yol)
        except (OSError, ImportError) as e:
            _log.exception("yanmaya göre pin gücü yazılamadı: %s", yol)
            QtWidgets.QMessageBox.warning(self, _("Tablo yazılamadı"), str(e))
