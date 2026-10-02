# -*- coding: utf-8 -*-
"""
================================================================================
 kinetik.py  --  Analiz > "Nokta kinetiği" karti
================================================================================
 beta_i / lambda_i tablosu (son kosudan IFP, Keepin hazir verisi ya da elle),
 uretim zamani Lambda, basamak/rampa reaktivitesi (pcm ya da $), istege bagli
 adiyabatik sicaklik geri beslemesi -> P(t) grafigi ve periyot.

 Hesap cekirdek/kinetik.py'dedir (kati ODE, Radau); bu dosya yalniz girdi
 toplar, dogrular ve sonucu gosterir. Cozum milisaniyeler-saniye surer:
 arka plan isci parcacigi gerekmez.
================================================================================
"""

from PySide6 import QtCore, QtWidgets
from matplotlib.figure import Figure

from cekirdek import kinetik as kin
from cekirdek import kinetik_oku, kosucu
from cekirdek.ceviri import _, N_
from cekirdek.gunluk import kaydedici
from arayuz import bilesenler as bil
from arayuz.analiz import kinetik_gosterim as gos
from arayuz.analiz.adlar import FORM_GENISLIGI, aciklama, form_duzeni, renk
from arayuz.analiz.tuval import Tuval
from arayuz.ortak import sayi, tamsayi

_log = kaydedici(__name__)
TUVAL_YUKSEKLIGI = 260          # P(t) grafigi [px]
TABLO_YUKSEKLIGI = 250          # 7 satir + baslik; 8 grupta kaydirma [px]
MIKRO = 1e-6                    # Lambda kutusu mikrosaniye
_SUTUN_BETA, _SUTUN_LAMBDA = 1, 2
_KAYNAKLAR = (("keepin", N_("Keepin U-235 termal (6 grup)")), ("kosu", N_("Son koşu (IFP)")),
              ("elle", N_("Elle")))


class KinetikKarti(bil.Kart):

    def __init__(self, parent=None):
        super().__init__(_("Nokta kinetiği"), _(
            "Gecikmeli nötron grupları (β_i, λ_i) ve üretim zamanı Λ ile basamak ya da rampa "
            "reaktivitesine güç yanıtı P(t). β_i ve Λ kinetik açık bir koşudan (IFP) "
            "alınabilir."), parent=parent)
        self._kosu_kaynagi = lambda: None
        self._kosu_verisi = None
        self.son_cozum = None
        self._birim_onceki = "pcm"
        self._girdileri_kur()
        self._geri_beslemeyi_kur()
        self._yerlesim_kur()
        self.kaynak.setCurrentIndex(self.kaynak.findData("keepin"))
        self._kaynak_degisti()
        self._gorunurluk()

    # ------------------------------------------------------------------
    def _girdileri_kur(self):
        self.kaynak = QtWidgets.QComboBox()
        for anahtar, metin in _KAYNAKLAR:
            self.kaynak.addItem(_(metin), anahtar)
        self.kaynak.currentIndexChanged.connect(self._kaynak_degisti)
        self.d_kosudan = QtWidgets.QPushButton(_("Son koşudan al"))
        self.d_kosudan.clicked.connect(self.kosudan_al)
        self.grup_sayisi = tamsayi(6, 1, kin.AZAMI_GECIKMIS_GRUP, 1, _("grup"))
        self.grup_sayisi.valueChanged.connect(self._grup_sayisi_degisti)
        self.tablo = QtWidgets.QTableWidget(0, 3)
        self.tablo.setHorizontalHeaderLabels([_("Grup"), "β_i [pcm]", "λ_i [1/s]"])
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setMaximumHeight(TABLO_YUKSEKLIGI)
        self.nesil_suresi = sayi(20.0, 6, 1e-5, 1e5, 1.0, "μs")
        self.nesil_suresi.setToolTip(_(
            "Λ: ani nötron üretim zamanı. LWR ~ 10–30 μs, hızlı sistem ~ ns (Godiva ~ 5.6 ns)."))
        self.tur = QtWidgets.QComboBox()
        self.tur.addItem(_("Basamak"), "basamak")
        self.tur.addItem(_("Rampa"), "rampa")
        self.tur.currentIndexChanged.connect(self._gorunurluk)
        self.birim = QtWidgets.QComboBox()
        self.birim.addItem("pcm", "pcm")
        self.birim.addItem("$", "dolar")
        self.birim.currentIndexChanged.connect(self._birim_degisti)
        self.reaktivite = sayi(100.0, 4, -1e5, 1e5, 10.0)
        self.reaktivite.setToolTip(_(
            "Basamakta t = 0'da eklenen ρ; rampada rampa sonunda ulaşılan ρ.\n"
            "1 pcm = 10⁻⁵ Δk/k; 1 $ = β_eff. ρ ≥ 1 $ ANİ KRİTİK'tir."))
        self.rampa_suresi = sayi(10.0, 4, 1e-4, 1e6, 1.0, "s")
        self.sure = sayi(100.0, 4, 1e-6, 1e6, 10.0, "s")
        self.d_hesapla = QtWidgets.QPushButton(_("Hesapla"))
        self.d_hesapla.setObjectName("birincil")
        self.d_hesapla.clicked.connect(self.hesapla)

    def _geri_beslemeyi_kur(self):
        self.gb_var = QtWidgets.QCheckBox(_("Adiyabatik sıcaklık geri beslemesi"))
        self.gb_var.setToolTip(_(
            "Isı atılmaz: dΔT/dt = P₀·(P/P₀)/C, ρ = ρ_dış + α_T·ΔT.\n"
            "Doppler benzeri hızlı bir negatif geri beslemenin en basit modeli."))
        self.gb_var.toggled.connect(self._gorunurluk)
        self.alfa = sayi(-2.0, 4, -1e3, 1e3, 0.5, "pcm/K")
        self.isi_kapasitesi = sayi(1e6, 1, 1e-3, 1e15, 1e5, "J/K")
        self.guc0 = sayi(1e6, 1, 1e-6, 1e12, 1e5, "W")

    def _yerlesim_kur(self):
        f = form_duzeni()
        kaynak_satiri = QtWidgets.QWidget()
        ks = QtWidgets.QHBoxLayout(kaynak_satiri)
        ks.setContentsMargins(0, 0, 0, 0)
        kaynak_satiri.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        ks.addWidget(self.kaynak, 1)
        ks.addWidget(self.d_kosudan)
        f.addRow(_("Veri kaynağı:"), kaynak_satiri)
        f.addRow(_("Grup sayısı:"), self.grup_sayisi)
        f.addRow(self.tablo)
        f.addRow(_("Üretim zamanı Λ:"), self.nesil_suresi)
        f.addRow(_("Reaktivite türü:"), self.tur)
        f.addRow(_("Birim:"), self.birim)
        f.addRow(_("Reaktivite:"), self.reaktivite)
        f.addRow(_("Rampa süresi:"), self.rampa_suresi)
        f.addRow(_("Benzetim süresi:"), self.sure)
        f.addRow(self.gb_var)
        f.addRow("α_T:", self.alfa)
        f.addRow(_("Isı kapasitesi C:"), self.isi_kapasitesi)
        f.addRow(_("Başlangıç gücü P₀:"), self.guc0)
        f.addRow("", self.d_hesapla)
        self.form = f
        govde = QtWidgets.QWidget()
        govde.setLayout(f)
        govde.setMaximumWidth(FORM_GENISLIGI)
        self.ekle(govde)
        self.uyari_etiketi = QtWidgets.QLabel("")
        self.uyari_etiketi.setWordWrap(True)
        self.sonuc_etiketi = QtWidgets.QLabel(_("Henüz hesaplanmadı."))
        self.sonuc_etiketi.setWordWrap(True)
        self.sonuc_etiketi.setTextFormat(QtCore.Qt.RichText)
        self.sonuc_etiketi.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.figur = Figure(figsize=(5, 2.6), tight_layout=True)
        self.tuval = Tuval(self.figur)
        self.tuval.setFixedHeight(TUVAL_YUKSEKLIGI)
        self.eksen = self.figur.add_subplot(111)
        for w in (self.uyari_etiketi, self.sonuc_etiketi, self.tuval):
            self.ekle(w)

    # ==================================================================
    # disaridan
    # ==================================================================
    def kosu_kaynagi_ayarla(self, fonksiyon):
        """fonksiyon() -> son basarili kosunun dizini ya da None (ana pencere)."""
        self._kosu_kaynagi = fonksiyon

    def sifirla(self):
        """Proje degisti: kosu verisi ve sonuc silinir."""
        self._kosu_verisi = None
        self.son_cozum = None
        if self.kaynak.currentData() == "kosu":
            self.kaynak.setCurrentIndex(self.kaynak.findData("keepin"))
        self.sonuc_etiketi.setText(_("Henüz hesaplanmadı."))
        self._uyari("")
        self.figur.clear()
        self.eksen = self.figur.add_subplot(111)
        self.tuval.draw_idle()

    def kosudan_al(self):
        """Son basarili kosunun statepoint'inden beta_i, lambda_i ve Lambda."""
        dizin = self._kosu_kaynagi()
        sp = kosucu.son_statepoint(dizin) if dizin else None
        if not sp:
            self._uyari(_("Bu projede başarılı bir koşu yok: önce Çalıştır'da kinetik "
                          "parametreleri açık bir özdeğer koşusu yapın."), "uyari")
            return
        try:
            kin_sonuc = kosucu.sonuc_oku(sp).get("kinetik") or {}
            veri = kinetik_oku.grup_verisine(kin_sonuc) if "beta_i" in kin_sonuc else None
        except Exception as e:
            _log.exception("koşudan kinetik veri okunamadı: %s", sp)
            self._uyari(_("Koşudan kinetik veri okunamadı: %s") % e, "hata")
            return
        if veri is None:
            self._uyari(_("Son koşuda grup başına veri yok. Hesap ayarlarında kinetik "
                          "parametreleri ve gecikmeli nötron gruplarını (6 ya da 8) açıp "
                          "yeniden koşun."), "uyari")
            return
        self._kosu_verisi = veri
        self.kaynak.setCurrentIndex(self.kaynak.findData("kosu"))
        self._kaynak_degisti()
        self._uyari(_("Koşudan alındı: %d grup, β_eff = %.1f pcm, Λ = %.4g s.")
                    % (len(veri.beta), kin.pcm_e(veri.beta_toplam), veri.nesil_suresi))

    # ==================================================================
    # girdi -> veri
    # ==================================================================
    def veri(self):
        """Tablo + Lambda kutusu -> GrupVerisi (ValueError: kullaniciya gosterilir)."""
        beta, lam = [], []
        for i in range(self.tablo.rowCount()):
            try:
                beta.append(kin.pcm_den(float(self.tablo.item(i, _SUTUN_BETA).text())))
                lam.append(float(self.tablo.item(i, _SUTUN_LAMBDA).text()))
            except (AttributeError, ValueError):
                raise ValueError(_("Tablo satırı %d: β_i ve λ_i sayı olmalı.") % (i + 1)) from None
        kaynak = {"keepin": kin.KEEPIN_U235_TERMAL.kaynak,
                  "kosu": self._kosu_verisi.kaynak if self._kosu_verisi else ""}.get(
                      self.kaynak.currentData(), _("elle"))
        return kin.GrupVerisi(beta=tuple(beta), lam=tuple(lam),
                              nesil_suresi=self.nesil_suresi.value() * MIKRO, kaynak=kaynak)

    def _rho(self, beta):
        d = self.reaktivite.value()
        return kin.dolar_dan(d, beta) if self.birim.currentData() == "dolar" else kin.pcm_den(d)

    def _profil(self, rho):
        if self.tur.currentData() == "rampa":
            sure = self.rampa_suresi.value()
            return kin.Rampa(hiz=rho / sure, sure=sure)
        return kin.Basamak(rho)

    def _geri_besleme(self):
        if not self.gb_var.isChecked():
            return None
        return kin.GeriBesleme(alfa=kin.pcm_den(self.alfa.value()),
                               isi_kapasitesi=self.isi_kapasitesi.value(),
                               guc0=self.guc0.value())

    # ==================================================================
    def hesapla(self):
        """Girdileri dogrular, cozer, gosterir; hata kullaniciya yazilir."""
        self.son_cozum = None
        try:
            veri = self.veri()
            rho = self._rho(veri.beta_toplam)
            cozum = kin.coz(veri, self._profil(rho), self.sure.value(),
                            geri_besleme=self._geri_besleme())
            metin = gos.sonuc_metni(veri, rho, cozum)
        except (ValueError, RuntimeError) as e:
            _log.info("nokta kinetiği hesaplanamadı: %s", e)
            self._uyari(str(e), "hata")
            self.sonuc_etiketi.setText(_("Hesaplanamadı."))
            return
        self.son_cozum = cozum
        self._uyari(" ".join(u.mesaj for u in cozum.uyarilar), "uyari")
        self.sonuc_etiketi.setText(metin)
        self.eksen = gos.grafik_ciz(self.figur, cozum)
        self.tuval.draw_idle()

    def _uyari(self, metin, tur="metin_soluk"):
        self.uyari_etiketi.setStyleSheet("color: %s;" % renk(tur))
        self.uyari_etiketi.setText(metin)
        self.uyari_etiketi.setVisible(bool(metin))

    # ==================================================================
    # tablo ve gorunurluk
    # ==================================================================
    def _kaynak_degisti(self, *_a):
        k = self.kaynak.currentData()
        veri = {"keepin": kin.KEEPIN_U235_TERMAL, "kosu": self._kosu_verisi}.get(k)
        if k == "kosu" and veri is None:
            self._uyari(_("Önce \"Son koşudan al\" ile koşu verisini yükleyin."), "uyari")
        if veri is not None:
            self._tabloyu_doldur(veri.beta, veri.lam)
            self.nesil_suresi.setValue(veri.nesil_suresi / MIKRO)
        elif k == "kosu":
            self._tabloyu_doldur((), ())
        self._duzenlenebilir(k == "elle")

    def _grup_sayisi_degisti(self, n):
        if self.kaynak.currentData() != "elle" or n == self.tablo.rowCount():
            return
        eski = [(self.tablo.item(i, _SUTUN_BETA).text(), self.tablo.item(i, _SUTUN_LAMBDA).text())
                for i in range(min(n, self.tablo.rowCount()))]
        eski += [("0", "1")] * (n - len(eski))
        self._tablo_yaz(eski)
        self._duzenlenebilir(True)

    def _tabloyu_doldur(self, beta, lam):
        self._tablo_yaz([("%.6g" % kin.pcm_e(b), "%.6g" % x) for b, x in zip(beta, lam)])

    def _tablo_yaz(self, satirlar):
        self.tablo.setRowCount(len(satirlar))
        for i, (b, x) in enumerate(satirlar):
            for j, metin in enumerate((str(i + 1), b, x)):
                self.tablo.setItem(i, j, QtWidgets.QTableWidgetItem(metin))
        self.grup_sayisi.blockSignals(True)
        self.grup_sayisi.setValue(max(len(satirlar), 1))
        self.grup_sayisi.blockSignals(False)

    def _duzenlenebilir(self, elle):
        self.grup_sayisi.setEnabled(elle)
        self.nesil_suresi.setEnabled(True)
        for i in range(self.tablo.rowCount()):
            for j in range(3):
                oge = self.tablo.item(i, j)
                bayrak = oge.flags() | QtCore.Qt.ItemIsEditable
                if not elle or j == 0:
                    bayrak = oge.flags() & ~QtCore.Qt.ItemIsEditable
                oge.setFlags(bayrak)

    def _birim_degisti(self, *_a):
        yeni = self.birim.currentData()
        try:
            beta = self.veri().beta_toplam
        except ValueError:
            _log.debug("birim değişimi: tablo geçersiz, değer dönüştürülmedi")
            beta = None
        if beta and yeni != self._birim_onceki:
            d = self.reaktivite.value()
            self.reaktivite.setValue(kin.pcm_e(kin.dolar_dan(d, beta)) if yeni == "pcm"
                                     else kin.dolar_a(kin.pcm_den(d), beta))
        self._birim_onceki = yeni

    def _gorunurluk(self, *_a):
        self.form.setRowVisible(self.rampa_suresi, self.tur.currentData() == "rampa")
        for w in (self.alfa, self.isi_kapasitesi, self.guc0):
            self.form.setRowVisible(w, self.gb_var.isChecked())
