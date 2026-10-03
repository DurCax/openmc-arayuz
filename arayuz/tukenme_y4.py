# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_y4.py  --  Tukenme sayfasi: sogutma, surdurme, hizli kip, kritik arama
================================================================================
 v3 Y4. Ayar anahtarlari cekirdek/tukenme_ayar.py'dedir. Varsayilan degerler
 dosyaya YAZILMAZ (eski spec'ler gidis-donuste degismesin): bir anahtar ya
 kullanici degistirdiyse ya da zaten dosyadaysa yazilir.
================================================================================
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from cekirdek import tukenme_ayar as ta
from cekirdek.ceviri import N_, _
from arayuz.analiz.adlar import form_duzeni
from arayuz.ortak import sayi

SOGUMA_BIRIMLERI = [("d", N_("gün")), ("h", N_("saat")), ("a", N_("yıl")), ("s", N_("saniye"))]
ARAMA_TURU = [("bor", N_("Çözünmüş bor [ppm]")), ("cubuk", N_("Kontrol çubuğu daldırma [%]"))]
BOR_EN_COK = 1.0e4           # ppm (giris kutusu ust siniri)


def entegrator_doldur(kutu: QtWidgets.QComboBox) -> None:
    """Entegrator secimini tukenme_ayar.ENTEGRATORLER ile doldurur."""
    kutu.clear()
    for kod, e in ta.ENTEGRATORLER.items():
        kutu.addItem(e.gorunen_ad(), kod)
    kutu.setToolTip(_(
        "openmc.deplete entegratörü. Yüksek mertebe daha az adımla aynı doğruluğu verir "
        "ama adım başına daha çok transport koşar. SI-* (stokastik örtük) adım başına "
        "iç döngü koşar; kritik aramayla birlikte kullanılamaz."))


class TukenmeGenisletme(QtWidgets.QWidget):
    """Gelismis tukenme ayarlari (Y4). degisti: kullanici bir ayari degistirdi."""

    degisti = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._yukleniyor = False
        self._spec = None
        self._kur()

    # ------------------------------------------------------------------
    def _kur(self) -> None:
        self.sogutma = QtWidgets.QLineEdit()
        self.sogutma.setPlaceholderText(_("ör. 1, 10, 100 (boş: soğuma yok)"))
        self.sogutma.setToolTip(_(
            "Yanmadan SONRA sıfır güçte (yalnız bozunma) adımlar. Transport koşulmaz; "
            "bozunma ısısı, aktivite ve foton kaynağı soğuma adımlarında izlenir."))
        self.sogutma_birim = QtWidgets.QComboBox()
        for kod, ad in SOGUMA_BIRIMLERI:
            self.sogutma_birim.addItem(_(ad), kod)
        self.si_adim = QtWidgets.QSpinBox()
        self.si_adim.setRange(*ta.SI_IC_ADIM_SINIR)
        self.si_adim.setValue(ta.SI_IC_ADIM)
        self.si_adim.setToolTip(_("SI-* entegratörlerinin iç döngü sayısı (OpenMC n_steps)."))
        self.surdur = QtWidgets.QCheckBox(_("Kaldığı yerden sürdür"))
        self.surdur.setToolTip(_(
            "Dizindeki önceki sonuç silinmez; yarıda kalan koşu son kayıtlı adımdan devam "
            "eder, biten koşuya eklenen adımlar koşulur. Fizik aynı olmalı."))
        self.hizli = QtWidgets.QCheckBox(_("Hızlı kip (MicroXS, transport'suz)"))
        self.hizli.setToolTip(_(
            "Tek transport'tan tek gruplu tesir kesitleri; adımlar transport koşmadan "
            "çözülür. Spektrum değişimi görülmez ve k-eff adım adım hesaplanmaz."))
        self._arama_kur()
        form = form_duzeni()
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow(_("Soğuma adımları:"), self.sogutma)
        form.addRow(_("Soğuma birimi:"), self.sogutma_birim)
        form.addRow(_("SI iç döngü:"), self.si_adim)
        form.addRow("", self.surdur)
        form.addRow("", self.hizli)
        form.addRow(self.arama_var)
        form.addRow(_("Arama türü:"), self.arama_tur)
        form.addRow(_("Hedef:"), self.arama_hedef)
        form.addRow(_("Başlangıç tahminleri:"), self._ikili(self.arama_alt, self.arama_ust))
        form.addRow(_("Sınır [en az, en çok]:"), self._ikili(self.sinir_alt, self.sinir_ust))
        form.addRow(_("k toleransı:"), self.arama_tol)
        self.form = form
        self.setLayout(form)
        for w in (self.surdur, self.hizli, self.arama_var):
            w.toggled.connect(self._degisti)
        for w in (self.sogutma_birim, self.arama_tur, self.arama_hedef):
            w.currentIndexChanged.connect(self._degisti)
        for w in (self.si_adim, self.arama_alt, self.arama_ust, self.sinir_alt,
                  self.sinir_ust, self.arama_tol):
            w.valueChanged.connect(self._degisti)
        self.sogutma.editingFinished.connect(self._degisti)
        self.arama_tur.currentIndexChanged.connect(self._hedefleri_doldur)

    def _arama_kur(self) -> None:
        self.arama_var = QtWidgets.QCheckBox(_("Tükenme sırasında kritik arama (k = 1)"))
        self.arama_var.setToolTip(_(
            "Her güçlü adımın başında k = 1 veren bor derişimi ya da kontrol çubuğu daldırması "
            "aranır (OpenMC add_keff_search_control, GRsecant). Adım başına birkaç ek "
            "transport koşar."))
        self.arama_tur = QtWidgets.QComboBox()
        for kod, ad in ARAMA_TURU:
            self.arama_tur.addItem(_(ad), kod)
        self.arama_hedef = QtWidgets.QComboBox()
        self.arama_alt = sayi(500.0, 2, 0.0, BOR_EN_COK, 10.0)
        self.arama_ust = sayi(1500.0, 2, 0.0, BOR_EN_COK, 10.0)
        self.sinir_alt = sayi(0.0, 2, 0.0, BOR_EN_COK, 10.0)
        self.sinir_ust = sayi(3000.0, 2, 0.0, BOR_EN_COK, 10.0)
        self.arama_tol = sayi(ta.ARAMA_K_TOL, 5, 1e-5, 0.05, 1e-4)
        self.arama_tol.setToolTip(_(
            "Arama |k − 1| ≤ tolerans ve σ ≤ tolerans olunca durur. Varsayılan 1e-3 "
            "(100 pcm): tipik bir tükenme adımının istatistik belirsizliği düzeyi."))

    @staticmethod
    def _ikili(a, b):
        w = QtWidgets.QWidget()
        d = QtWidgets.QHBoxLayout(w)
        d.setContentsMargins(0, 0, 0, 0)
        d.addWidget(a)
        d.addWidget(b)
        return w

    def _hedefleri_doldur(self, *_a) -> None:
        if self._spec is None:
            return
        secili = self.arama_hedef.currentData()
        self.arama_hedef.blockSignals(True)
        self.arama_hedef.clear()
        if self.arama_tur.currentData() == "cubuk":
            adlar = [c["ad"] for c in self._spec.get("cubuklar") or [] if c.get("tur") == "kontrol"]
        else:
            from cekirdek import uygunluk
            adlar = [m["ad"] for m in self._spec.get("malzemeler") or []
                     if uygunluk.tek_malzeme_rolleri(m) & {"sogutucu", "moderator"}]
        for ad in adlar:
            self.arama_hedef.addItem(ad, ad)
        i = self.arama_hedef.findData(secili)
        self.arama_hedef.setCurrentIndex(max(i, 0))
        self.arama_hedef.blockSignals(False)

    # ------------------------------------------------------------------
    def doldur(self, spec: dict) -> None:
        self._yukleniyor = True
        try:
            self._spec = spec
            t = spec.get("tukenme") or {}
            adim, birim = ta.sogutma(t)
            self.sogutma.setText(", ".join("%g" % a for a in adim))
            self.sogutma_birim.setCurrentIndex(max(self.sogutma_birim.findData(birim), 0))
            self.si_adim.setValue(ta.si_ic_adim(t))
            self.surdur.setChecked(ta.surdur(t))
            self.hizli.setChecked(ta.hizli_kip(t))
            k = ta.kritik_arama(t)
            self.arama_var.setChecked(k.var)
            self.arama_tur.setCurrentIndex(max(self.arama_tur.findData(k.tur), 0))
            self._hedefleri_doldur()
            self.arama_hedef.setCurrentIndex(max(self.arama_hedef.findData(k.hedef), 0))
            for w, v in ((self.arama_alt, k.alt), (self.arama_ust, k.ust),
                         (self.sinir_alt, k.sinir[0]), (self.sinir_ust, k.sinir[-1]),
                         (self.arama_tol, k.k_tol)):
                w.setValue(float(v))
        finally:
            self._yukleniyor = False
        self.gorunum(t.get("entegrator") or ta.VARSAYILAN_ENTEGRATOR)

    def gorunum(self, entegrator_kodu: str) -> None:
        """Satirlarin gorunurlugu: SI satiri SI'de, arama ayrintisi acikken."""
        e = ta.ENTEGRATORLER.get(entegrator_kodu)
        self.form.setRowVisible(self.si_adim, bool(e and e.si))
        acik = self.arama_var.isChecked()
        for w in (self.arama_tur, self.arama_hedef, self.arama_alt.parentWidget(),
                  self.sinir_alt.parentWidget(), self.arama_tol):
            self.form.setRowVisible(w, acik)

    @staticmethod
    def _sayilar(metin: str) -> list:
        cikti = []
        for p in (metin or "").replace(";", ",").split(","):
            p = p.strip()
            if p:
                try:
                    cikti.append(float(p))
                except ValueError:       # gecersiz parca: denetim (tukenme_ayar) bildirir
                    cikti.append(p)
        return cikti

    def yaz(self, t: dict) -> None:
        """Arayuz -> spec['tukenme'] (yerinde; sekme _kaydet'i cagirir)."""
        adimlar = self._sayilar(self.sogutma.text())
        if adimlar or "sogutma" in t:
            t["sogutma"] = {"adimlar": adimlar, "birim": self.sogutma_birim.currentData()}
        _bayrak(t, "surdur", self.surdur.isChecked())
        _bayrak(t, "hizli_kip", self.hizli.isChecked())
        if self.si_adim.value() != ta.SI_IC_ADIM or "si_ic_adim" in t:
            t["si_ic_adim"] = self.si_adim.value()
        if self.arama_var.isChecked() or "kritik_arama" in t:
            t["kritik_arama"] = {
                "var": self.arama_var.isChecked(), "tur": self.arama_tur.currentData(),
                "hedef": self.arama_hedef.currentData() or "",
                "alt": self.arama_alt.value(), "ust": self.arama_ust.value(),
                "sinir": [self.sinir_alt.value(), self.sinir_ust.value()],
                "k_tol": self.arama_tol.value(), "sigma": self.arama_tol.value()}

    def _degisti(self, *_a) -> None:
        if self._yukleniyor:
            return
        self.gorunum(((self._spec or {}).get("tukenme") or {}).get("entegrator") or "")
        self.degisti.emit()


def _bayrak(t: dict, anahtar: str, deger: bool) -> None:
    """Varsayilan (False) dosyada yoksa yazilmaz."""
    if deger or anahtar in t:
        t[anahtar] = bool(deger)


