# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_arayuz.py  --  Tukenme sayfasinin widget'lari ve yerlesimi (karisim)
================================================================================
 sekme_tukenme.py'den ayrildi (dosya 800 satir sinirina dayaniyordu). Burada
 yalnizca widget KURULUR ve yerlestirilir; davranis (spec <-> arayuz, kosu,
 sonuc) sekme_tukenme.py ve tukenme_sonuc.py'dedir.

 YERLESIM (maket duzeni: sayfa basligi + kartlar)
   Tukenme                         baslik + aciklama + acma anahtari
   [Yanma ayarlari]    ayar_kutusu     guc, adimlar, yanan malzemeler, Gelismis
   [Izlenen nuklidler] izlenen_kutusu  NuklidSecici
   [Kosu]              kosu_kutusu     baslat / durdur / ilerleme, kapi, sure
   [Sonuc]             sonuc_kutusu    onceki sonuc, grafik, tablo, CSV
   Ayrintili cikti     ayrinti         (Gelismis bolum)
 Nitelik adlari (ayar_kutusu, kosu_kutusu, ...) onceki surumle AYNIDIR:
 testler ve _gorunum_guncelle onlari kullanir.
================================================================================
"""

from matplotlib.figure import Figure

from PySide6 import QtCore, QtWidgets

from cekirdek.ceviri import N_, _
from arayuz import bilesenler as bil
from arayuz.analiz.adlar import FORM_GENISLIGI, aciklama, form_duzeni
from arayuz.analiz.gorunum import kok_duzeni, kosu_satiri, sayfa_basligi
from arayuz.analiz.tuval import Tuval
from arayuz.nuklid_secici import NuklidSecici
from arayuz.ortak import BosDurum, GelismisBolum, sayi
from arayuz.tasarim import tokenlar

A = tokenlar.ARALIK
TUVAL_YUKSEKLIGI = 380      # k-eff + nuklid grafigi [px]
TABLO_EN_AZ = 160
GUNLUK_EN_AZ = 200
GUNLUK_SATIR_EN_COK = 4000

ZINCIR_SECENEK = [
    ("otomatik",    N_("Otomatik (spektrumdan)")),
    ("termal",      N_("ENDF/B-VIII.0 termal (3820 nüklid)")),
    ("hizli",       N_("ENDF/B-VIII.0 hızlı (3820 nüklid)")),
    ("casl_termal", N_("CASL basit termal (228 nüklid, ~3 kat hızlı)")),
    ("casl_hizli",  N_("CASL basit hızlı (228 nüklid, ~3 kat hızlı)")),
]


class TukenmeArayuzu:
    """TukenmeSekmesi'nin widget kurulumu (karisim; __init__ cagirir)."""

    def _arayuzu_kur(self):
        self.bos = BosDurum(_("Bu modelde tükenme hesabı yapılamaz"), "", None, "∅")
        self.var = QtWidgets.QCheckBox(_("Tükenme (yanma) hesabını etkinleştir"))
        self.aciklama = aciklama(_(
            "Yakıtın zamanla tükenmesini ve k-eff'in yanmayla değişimini hesaplar. "
            "Her adım en az bir OpenMC koşusudur; süre adım sayısıyla artar."))
        self._ayarlari_kur()
        self._gelismisi_kur()
        self._kosuyu_kur()
        self._izleneni_kur()
        self._sonucu_kur()
        self._gunlugu_kur()
        self._yerlesimi_kur()

    # ------------------------------------------------------------------
    def _ayarlari_kur(self):
        self.guc = sayi(40.0, 3, 0.001, 10000.0, 1.0, " W/gHM")
        self.guc.setToolTip(_(
            "Güç yoğunluğu, ağır metalin gramı başına. Mutlak güç kullanılmaz:\n"
            "2B bir modelde 'cm başına' olmak zorunda kalırdı.\n\n"
            "Tipik: PWR 38–40, BWR ~25, SFR 50–100 W/gHM."))
        self.birim = QtWidgets.QComboBox()
        self.birim.addItem(_("gün"), "d")
        self.birim.addItem(_("MWd/kg (yanma)"), "MWd/kg")
        self.adimlar = QtWidgets.QLineEdit()
        self.adimlar.setPlaceholderText(_("ör. 0.5, 1.5, 3, 5, 10, 30"))
        self.adimlar.setToolTip(_(
            "Adım uzunlukları, virgülle. İlk adımları kısa tutun (ör. 0.5, 1.5):\n"
            "Xe-135 ~2 günde dengeye gelir ve PWR'da birkaç bin pcm'lik hızlı\n"
            "bir düşüş yaratır; uzun bir ilk adım bunu görünmez kılar."))
        self.adim_ozet = QtWidgets.QLabel("—")
        self.adim_ozet.setObjectName("soluk")
        self.adim_ozet.setWordWrap(True)
        self.malzeme_bilgi = QtWidgets.QLabel("—")
        self.malzeme_bilgi.setWordWrap(True)
        self.malzeme_bilgi.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.malzeme_bilgi.setToolTip(_(
            "Fisil malzemeler ve yanabilir zehirler (Gd, Er) otomatik yanar. Hacimler "
            "analitik hesaplanır: yanlış bir hacim yanma hızını aynı oranda bozar ve "
            "k-eff'te iz bırakmaz. Testte OpenMC'nin stokastik hacim hesabıyla 1σ "
            "içinde uyuştuğu ölçüldü."))
        self.zincir_uyari = QtWidgets.QLabel("")
        self.zincir_uyari.setWordWrap(True)
        form = form_duzeni()
        form.addRow(_("Güç yoğunluğu:"), self.guc)
        form.addRow(_("Adım birimi:"), self.birim)
        form.addRow(_("Adımlar:"), self.adimlar)
        form.addRow("", self.adim_ozet)
        form.addRow(_("Yanan malzemeler:"), self.malzeme_bilgi)
        form.addRow("", self.zincir_uyari)
        self.ayar_formu = form

    def _gelismisi_kur(self):
        self.zincir = QtWidgets.QComboBox()
        for k, ad in ZINCIR_SECENEK:
            self.zincir.addItem(_(ad), k)
        self.zincir_bilgi = QtWidgets.QLabel("-")
        self.zincir_bilgi.setObjectName("soluk")
        self.zincir_bilgi.setWordWrap(True)
        self.entegrator = QtWidgets.QComboBox()
        self.entegrator.addItem(_("CECM (öngörücü-düzeltici, adım başına 2 transport)"), "cecm")
        self.entegrator.addItem(_("Predictor (adım başına 1 transport, kaba)"), "predictor")
        self.ayir = QtWidgets.QCheckBox(_("Çubuk çubuk yanma (her örnek ayrı malzeme — çok ağır)"))
        self.ayir.setToolTip(_("Yakıtın her örneği (ör. demetteki her çubuk) ayrı yanar; "
                               "bellek ve süre örnek sayısıyla artar."))
        self.gelismis = GelismisBolum("tukenme_gelismis")
        gf = form_duzeni()
        gf.setContentsMargins(0, 0, 0, 0)
        gf.addRow(_("Zincir:"), self.zincir)
        gf.addRow("", self.zincir_bilgi)
        gf.addRow(_("Entegratör:"), self.entegrator)
        gf.addRow("", self.ayir)
        self.gelismis_form = gf
        gk = QtWidgets.QWidget()
        gk.setLayout(gf)
        self.gelismis.ekle(gk)

    def _kosuyu_kur(self):
        self.d_baslat = QtWidgets.QPushButton(_("Tükenmeyi başlat"))
        self.d_baslat.setObjectName("birincil")
        self.d_durdur = QtWidgets.QPushButton(_("Durdur"))
        self.d_durdur.setEnabled(False)
        self.ilerleme = QtWidgets.QProgressBar()
        self.ilerleme.setTextVisible(True)
        self.ilerleme.setRange(0, 1)
        self.ilerleme.setValue(0)
        self.kapi_etiket = QtWidgets.QLabel("-")
        self.kapi_etiket.setWordWrap(True)
        self.sure_etiket = QtWidgets.QLabel("")
        self.sure_etiket.setObjectName("soluk")
        self.d_baslat.clicked.connect(self.baslat)
        self.d_durdur.clicked.connect(self.durdur)

    def _izleneni_kur(self):
        self.izlenen = NuklidSecici()
        self.izlenen.setToolTip(_("Grafikte, tabloda ve CSV'de izlenecek nüklidler. Seçim "
                                  "değişince önceki sonuç yeniden koşmadan güncellenir."))
        self.izlenen.secim_degisti.connect(self._izlenen_degisti)

    def _sonucu_kur(self):
        self.onceki_etiket = QtWidgets.QLabel("")
        self.onceki_etiket.setWordWrap(True)
        self.figur = Figure(figsize=(5, 4.2), tight_layout=True)
        self.tuval = Tuval(self.figur)
        self.tuval.setFixedHeight(TUVAL_YUKSEKLIGI)
        self.eksen_k = self.figur.add_subplot(211)
        self.eksen_n = self.figur.add_subplot(212)
        self._grafik_bos()
        self.bulunamayan_etiket = QtWidgets.QLabel("")
        self.bulunamayan_etiket.setWordWrap(True)
        self.bulunamayan_etiket.setVisible(False)
        self.csv_dugmesi = QtWidgets.QPushButton(_("CSV olarak dışa aktar"))
        self.csv_dugmesi.setToolTip(_("Zaman, yanma, k, σ ve seçili her nüklidin atom "
                                      "sayısı ile yoğunluğu (ondalık nokta)"))
        self.csv_dugmesi.setEnabled(False)
        self.csv_dugmesi.clicked.connect(self.csv_disa_aktar)
        self.tablo = QtWidgets.QTableWidget(0, 4)
        self.tablo.setHorizontalHeaderLabels([_("gün"), "MWd/kg", "k-eff", "ρ [pcm]"])
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tablo.setMinimumHeight(TABLO_EN_AZ)

    def _gunlugu_kur(self):
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setProperty("mono", True)          # QSS: tema mono yazisi
        self.log.setMaximumBlockCount(GUNLUK_SATIR_EN_COK)
        self.log.setMinimumHeight(GUNLUK_EN_AZ)
        self.ayrinti = GelismisBolum("tukenme_ayrinti", _("Ayrıntılı çıktı"))
        self.ayrinti.ekle(self.log)

    # ------------------------------------------------------------------
    def _yerlesimi_kur(self):
        self.ayar_kutusu = bil.Kart(_("Yanma ayarları"))
        self.ayar_kutusu.govde.addLayout(self.ayar_formu)
        self.ayar_kutusu.ekle(self.gelismis)
        self.izlenen_kutusu = bil.Kart(_("İzlenen nüklidler"))
        self.izlenen_kutusu.ekle(self.izlenen)
        self.kosu_kutusu = bil.Kart(_("Koşu"))
        self.kosu_kutusu.ekle(kosu_satiri(self.d_baslat, self.d_durdur, self.ilerleme))
        self.kosu_kutusu.ekle(self.kapi_etiket)
        self.kosu_kutusu.ekle(self.sure_etiket)
        for kart in (self.ayar_kutusu, self.izlenen_kutusu, self.kosu_kutusu):
            kart.setMaximumWidth(FORM_GENISLIGI)
        self.sonuc_kutusu = bil.Kart(_("Sonuç"), eylem=self.csv_dugmesi)
        for w in (self.onceki_etiket, self.bulunamayan_etiket, self.tuval, self.tablo):
            self.sonuc_kutusu.ekle(w)
        self.icerik = QtWidgets.QWidget()
        ic = QtWidgets.QVBoxLayout(self.icerik)
        ic.setContentsMargins(0, 0, 0, 0)
        ic.setSpacing(A["l"])
        ic.addWidget(self.var)
        for w in (self.ayar_kutusu, self.izlenen_kutusu, self.kosu_kutusu,
                  self.sonuc_kutusu, self.ayrinti):
            ic.addWidget(w)
        ic.addStretch(1)
        duzen = kok_duzeni(self)
        duzen.addWidget(sayfa_basligi(_("Tükenme"), self.aciklama))
        duzen.addWidget(self.bos, 1)
        duzen.addWidget(self.icerik, 1)
