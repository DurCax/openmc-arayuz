# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_ayar.py  --  Kosu ayarlari, kaynak tanimi ve tally'ler
================================================================================
 "Ne hesaplanacak" sorusunun tamami burada: cevrim/parcacik sayilari, baslangic
 kaynagi, sicaklik yontemi ve tally tanimlari.
================================================================================
"""

from PySide6 import QtCore, QtWidgets

from cekirdek import sema
from cekirdek import kaynak as _kaynak
from arayuz.ortak import (SekmeTabani, ayrac, baslik, ipucu, sayi, tamsayi,
                          EnerjiGirdi, BilimselGirdi)

SKORLAR = ["flux", "fission", "absorption", "nu-fission", "scatter", "total",
           "elastic", "(n,gamma)", "(n,2n)", "heating", "kappa-fission",
           "fission-q-prompt", "damage-energy"]


class AyarSekmesi(SekmeTabani):

    KONU = "ayar"

    def __init__(self, parent=None):
        super().__init__(parent)

        # --- kosu ayarlari ---
        self.mod = QtWidgets.QComboBox()
        self.mod.addItem("Ozdeger (k-eff)", "eigenvalue")
        self.mod.addItem("Sabit kaynak", "fixed source")
        self.parcacik = tamsayi(10000, 100, 10 ** 9, 1000)
        self.cevrim = tamsayi(150, 1, 100000, 10)
        self.pasif = tamsayi(40, 0, 100000, 5)
        self.tohum = tamsayi(1, 1, 2 ** 31 - 1, 1)
        self.sicaklik_yontemi = QtWidgets.QComboBox()
        self.sicaklik_yontemi.addItems(["interpolation", "nearest"])
        self.aktif_etiket = QtWidgets.QLabel("-")
        self.entropi_var = QtWidgets.QCheckBox("Shannon entropisi ile kaynak yakinsamasini olc")
        self.entropi_var.setToolTip(
            "Kaynak dagiliminin pasif cevrimler icinde yakinsayip yakinsamadigini\n"
            "olcer. Yakinsamamis kaynak k-eff'i YANLI tahmin ettirir ve bu baska\n"
            "turlu fark edilmez. Ozdeger hesaplarinda acik tutun.")
        self.entropi_nx = tamsayi(8, 1, 200)
        self.entropi_ny = tamsayi(8, 1, 200)
        self.entropi_nz = tamsayi(1, 1, 200)
        self.kinetik_var = QtWidgets.QCheckBox(
            "Kinetik parametreleri hesapla (beta_eff ve uretim zamani Lambda)")
        self.kinetik_var.setToolTip(
            "IFP (Iterated Fission Probability) yontemiyle hesaplanir.\n"
            "beta_eff : gecikmis notron kesri -- reaktivite biriminin ($) tanimi\n"
            "Lambda   : notron uretim zamani -- kinetik davranisin hizi\n\n"
            "Kosuyu bir miktar yavaslatir; ihtiyac duymadikca kapali birakin.")
        self.kinetik_nesil = tamsayi(10, 1, 50, 1, "nesil")

        # --- kaynak ---
        self.kaynak_tur = QtWidgets.QComboBox()
        self.kaynak_tur.addItem("Nokta kaynak", "nokta")
        self.kaynak_tur.addItem("Kutu (yalnizca fisil bolgeler)", "kutu")
        self.kx = sayi(0.0, 4, -1e5, 1e5, 0.1, "cm")
        self.ky = sayi(0.0, 4, -1e5, 1e5, 0.1, "cm")
        self.kz = sayi(0.0, 4, -1e5, 1e5, 0.1, "cm")

        # --- kaynak parcacigi ve siddeti ---
        self.kaynak_parcacik = QtWidgets.QComboBox()
        self.kaynak_parcacik.addItem("Notron", "neutron")
        self.kaynak_parcacik.addItem("Foton (gama)", "photon")
        self.kaynak_parcacik.setToolTip(
            "Foton secilirse foton tasinimi da acilir ve kutuphanede foton\n"
            "verisi bulunmalidir. Ozdeger (k-eff) modunda foton kaynagi\n"
            "anlamsizdir -- fotonlar fisyon zincirini tasimaz.")
        self.kaynak_kuvvet = BilimselGirdi(1.0)
        self.kaynak_kuvvet.setToolTip(
            "Kaynak siddeti [parcacik/s]. SABIT KAYNAK modunda tally sonuclari\n"
            "bununla carpilir ve mutlak birime gecer (1/s, 1/cm2/s).\n"
            "Ozdeger modunda hicbir etkisi yoktur.\n\n"
            "1 birakilirsa sonuclar kaynak parcacigi basina kalir.")

        # --- enerji tayfi ---
        self.tayf = QtWidgets.QComboBox()
        for anahtar, ad in _kaynak.TAYFLAR:
            self.tayf.addItem(ad, anahtar)
        self.tayf.setToolTip(
            "OZDEGER modunda bu yalnizca BASLANGIC tahminidir: pasif cevrimler\n"
            "icinde gercek fisyon tayfiyla degisir ve k-eff'i etkilemez.\n"
            "SABIT KAYNAK modunda ise sonucun kendisini belirler.")
        self.watt_a = EnerjiGirdi(988.0e3)
        self.watt_b = sayi(2.249e-6, 9, 1e-9, 1.0, 1e-7, " 1/eV")
        self.maxwell_theta = EnerjiGirdi(1.2932e6)
        self.tek_enerji = EnerjiGirdi(14.1e6)
        self.ayrik_metin = QtWidgets.QLineEdit("1.173e6:0.5, 1.333e6:0.5")
        self.ayrik_metin.setToolTip("enerji[eV]:olasilik ciftleri, virgulle ayrilmis\n"
                                    "Ornek (Co-60): 1.173e6:0.5, 1.333e6:0.5")
        self.hist_kenar = QtWidgets.QLineEdit("1e5, 1e6, 1e7")
        self.hist_deger = QtWidgets.QLineEdit("1.0, 1.0")
        self.hist_kenar.setToolTip("N+1 grup kenari [eV], artan sirada")
        self.hist_deger.setToolTip("N grup degeri (bagil); kenar sayisindan bir eksik olmali")
        self.fuzyon_e0 = EnerjiGirdi(14.08e6)
        self.fuzyon_kutle = sayi(5.0, 2, 1.0, 100.0, 1.0)
        self.fuzyon_kutle.setToolTip("Reaktif kutlelerinin toplami: D+T = 2+3 = 5, D+D = 4")
        self.fuzyon_kt = EnerjiGirdi(20.0e3)
        self.fuzyon_kt.setToolTip("Iyon sicakligi kT. D-T icin genisleme:\n"
                                  "FWHM = 177 * sqrt(kT[keV]) keV")

        self.tayf_yigin = QtWidgets.QStackedWidget()
        for alanlar in (
                [("a (%s):" % "Watt", self.watt_a), ("b:", self.watt_b)],
                [("theta:", self.maxwell_theta)],
                [("Enerji:", self.tek_enerji)],
                [("Cizgiler:", self.ayrik_metin)],
                [("Grup kenarlari:", self.hist_kenar), ("Grup degerleri:", self.hist_deger)],
                [("Ortalama E0:", self.fuzyon_e0), ("Kutle orani:", self.fuzyon_kutle),
                 ("Iyon sicakligi:", self.fuzyon_kt)]):
            sayfa = QtWidgets.QWidget()
            f = QtWidgets.QFormLayout(sayfa)
            f.setContentsMargins(0, 0, 0, 0)
            for etiket, w in alanlar:
                f.addRow(etiket, w)
            self.tayf_yigin.addWidget(sayfa)
        self.tayf_ozet = QtWidgets.QLabel("-")
        self.tayf_ozet.setWordWrap(True)

        # --- acisal dagilim ---
        self.aci_tur = QtWidgets.QComboBox()
        for anahtar, ad in _kaynak.ACILAR:
            self.aci_tur.addItem(ad, anahtar)
        self.ax = sayi(0.0, 4, -1e3, 1e3, 0.1)
        self.ay = sayi(0.0, 4, -1e3, 1e3, 0.1)
        self.az = sayi(1.0, 4, -1e3, 1e3, 0.1)
        self.koni_aci = sayi(30.0, 2, 0.01, 180.0, 5.0, " derece")
        self.koni_aci.setToolTip("Koninin YARI acilimi. Kati acida duzgun dagilim kullanilir.")

        # --- is parcacigi ---
        self.is_parcacigi = tamsayi(8, 1, 512, 1, "is parcacigi")
        self.kosu_dizini = QtWidgets.QLineEdit("kosu")

        form = QtWidgets.QFormLayout()
        form.addRow("Kosu modu:", self.mod)
        form.addRow("Cevrim basina parcacik:", self.parcacik)
        form.addRow("Toplam cevrim:", self.cevrim)
        form.addRow("Pasif cevrim:", self.pasif)
        form.addRow("Aktif cevrim:", self.aktif_etiket)
        form.addRow("Rastgele tohum:", self.tohum)
        form.addRow("Sicaklik yontemi:", self.sicaklik_yontemi)
        form.addRow(self.entropi_var)
        ent = QtWidgets.QHBoxLayout()
        for e, w in (("nx", self.entropi_nx), ("ny", self.entropi_ny), ("nz", self.entropi_nz)):
            ent.addWidget(QtWidgets.QLabel(e)); ent.addWidget(w)
        ent.addStretch(1)
        self.entropi_etiket = QtWidgets.QLabel("Entropi mesh bolmeleri:")
        form.addRow(self.entropi_etiket, self._sar(ent))
        form.addRow(self.kinetik_var)
        self.kinetik_etiket = QtWidgets.QLabel("IFP nesil sayisi:")
        form.addRow(self.kinetik_etiket, self.kinetik_nesil)

        kaynak_form = QtWidgets.QFormLayout()
        kaynak_form.addRow("Kaynak tipi:", self.kaynak_tur)
        konum = QtWidgets.QHBoxLayout()
        for e, w in (("x", self.kx), ("y", self.ky), ("z", self.kz)):
            konum.addWidget(QtWidgets.QLabel(e))
            konum.addWidget(w)
        konum.addStretch(1)
        self.konum_etiket = QtWidgets.QLabel("Nokta konumu:")
        kaynak_form.addRow(self.konum_etiket, self._sar(konum))
        kaynak_form.addRow("Parcacik:", self.kaynak_parcacik)
        self.kuvvet_etiket = QtWidgets.QLabel("Kaynak siddeti [1/s]:")
        kaynak_form.addRow(self.kuvvet_etiket, self.kaynak_kuvvet)
        kaynak_form.addRow("Enerji tayfi:", self.tayf)
        kaynak_form.addRow("", self.tayf_yigin)
        kaynak_form.addRow("", self.tayf_ozet)
        kaynak_form.addRow("Acisal dagilim:", self.aci_tur)
        yon = QtWidgets.QHBoxLayout()
        for e, w in (("u", self.ax), ("v", self.ay), ("w", self.az)):
            yon.addWidget(QtWidgets.QLabel(e))
            yon.addWidget(w)
        yon.addStretch(1)
        self.yon_etiket = QtWidgets.QLabel("Yon:")
        kaynak_form.addRow(self.yon_etiket, self._sar(yon))
        self.koni_etiket = QtWidgets.QLabel("Koni yari acisi:")
        kaynak_form.addRow(self.koni_etiket, self.koni_aci)

        kosu_form = QtWidgets.QFormLayout()
        kosu_form.addRow("OpenMP is parcacigi:", self.is_parcacigi)
        kosu_form.addRow("Kosu dizini:", self.kosu_dizini)

        # --- guc dagilimi ---
        self.guc_var = QtWidgets.QCheckBox(
            "Cubuk bazli guc dagilimi hesapla (F_dH ve F_q)")
        self.guc_var.setToolTip(
            "Kafeste tekrarlanan yakit hucresinin HER ORNEGI ayri sayilir\n"
            "(DistribcellFilter). Buradan tepe faktorleri cikar:\n"
            "  F_dH = maks cubuk gucu / ortalama          (radyal)\n"
            "  F_q  = maks yerel guc yogunlugu / ortalama (3B gerekir)")
        self.guc_cubuk = QtWidgets.QComboBox()
        self.guc_bolge = QtWidgets.QComboBox()
        self.guc_skor = QtWidgets.QComboBox()
        self.guc_skor.addItems(["kappa-fission", "fission-q-recoverable",
                                "fission-q-prompt", "heating-local"])
        self.guc_dilim = tamsayi(20, 1, 200, 1, "dilim")
        self.guc_toplam = sayi(0.0, 1, 0.0, 1e12, 1e5, "W")
        self.guc_toplam.setSpecialValueText("(bos -- yalnizca bagil)")
        self.guc_etiketler = {}

        guc_form = QtWidgets.QFormLayout()
        guc_form.addRow(self.guc_var)
        for etiket, w, ad in (("Hedef cubuk:", self.guc_cubuk, "cubuk"),
                              ("Hedef bolge:", self.guc_bolge, "bolge"),
                              ("Skor:", self.guc_skor, "skor"),
                              ("Eksenel dilim:", self.guc_dilim, "dilim"),
                              ("Toplam guc:", self.guc_toplam, "toplam")):
            e = QtWidgets.QLabel(etiket)
            self.guc_etiketler[ad] = e
            guc_form.addRow(e, w)
        self.guc_not = ipucu(
            "Toplam guc, MODELIN KAPSADIGI bolgenin gucudur -- tum korun degil. "
            "Ornek: 3400 MWth / 193 demet = 17.6 MW; tek demetlik bir modelde "
            "17.6e6 W girilir. Bos birakilirsa yalnizca bagil dagilim verilir.")


        # --- tally'ler ---
        self.tally_liste = QtWidgets.QListWidget()
        self.tally_liste.setMaximumHeight(120)
        self.tally_liste.setMaximumWidth(150)
        self.tally_liste.currentRowChanged.connect(self._tally_secildi)
        self.t_ad = QtWidgets.QLineEdit()
        self.t_skor = QtWidgets.QListWidget()
        self.t_skor.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        for s in SKORLAR:
            self.t_skor.addItem(s)
        self.t_skor.setMaximumHeight(96)
        self.t_skor.setMinimumWidth(130)
        self.t_enerji_var = QtWidgets.QCheckBox("Enerji grup filtresi")
        self.t_enerji = QtWidgets.QLineEdit("0.0, 0.625, 2.0e7")
        self.t_mesh_var = QtWidgets.QCheckBox("Mesh (akı haritasi) filtresi")
        self.t_mesh_nx = tamsayi(10, 1, 1000)
        self.t_mesh_ny = tamsayi(10, 1, 1000)
        self.t_mesh_nz = tamsayi(1, 1, 1000)

        d_t_ekle = QtWidgets.QPushButton("+ Tally")
        d_t_sil = QtWidgets.QPushButton("Sil")
        d_t_ekle.clicked.connect(self._tally_ekle)
        d_t_sil.clicked.connect(self._tally_sil)
        t_dugme = QtWidgets.QHBoxLayout()
        t_dugme.addWidget(d_t_ekle); t_dugme.addWidget(d_t_sil); t_dugme.addStretch(1)

        t_form = QtWidgets.QFormLayout()
        t_form.addRow("Ad:", self.t_ad)
        t_form.addRow("Skorlar:", self.t_skor)
        t_form.addRow(self.t_enerji_var)
        t_form.addRow("Grup sinirlari [eV]:", self.t_enerji)
        t_form.addRow(self.t_mesh_var)
        mesh = QtWidgets.QHBoxLayout()
        for e, w in (("nx", self.t_mesh_nx), ("ny", self.t_mesh_ny), ("nz", self.t_mesh_nz)):
            mesh.addWidget(QtWidgets.QLabel(e)); mesh.addWidget(w)
        mesh.addStretch(1)
        t_form.addRow("Mesh bolmeleri:", self._sar(mesh))

        tally_sol = QtWidgets.QVBoxLayout()
        tally_sol.addWidget(self.tally_liste, 1)
        tally_sol.addLayout(t_dugme)
        tally_bolucu = QtWidgets.QHBoxLayout()
        tally_bolucu.addLayout(tally_sol, 0)
        tally_bolucu.addLayout(t_form, 1)

        # Uclu satirlardaki (nx/ny/nz, x/y/z) alanlar dar sutuna sigsin.
        # Varsayilan 88 px ile ayarlar sekmesi tasip yatay kaydirma cubugu
        # cikariyordu.
        for _w in (self.entropi_nx, self.entropi_ny, self.entropi_nz,
                   self.t_mesh_nx, self.t_mesh_ny, self.t_mesh_nz,
                   self.kx, self.ky, self.kz,
                   self.ax, self.ay, self.az):
            _w.setMinimumWidth(56)

        # --- yerlesim: IKI SUTUN ---
        # Tek sutunda bu sekmenin minimum yuksekligi 1179 px'e cikiyordu ve
        # QTabWidget tum sayfalarin en buyugunu minimum kabul ettigi icin ANA
        # PENCERE 1317 px'in altina inemiyordu (ekranda 1048 px var).
        # Sonuc: pencere tam ekran yapilamiyor ve alt kismi goruntulenemiyordu.
        sol = QtWidgets.QVBoxLayout()
        sol.addWidget(baslik("Kosu ayarlari"))
        sol.addLayout(form)
        sol.addWidget(ipucu(
            "Pasif cevrimler kaynak dagilimi yakinsayana kadar atilir ve "
            "istatistige katilmaz. Tipik olarak 20-50 pasif cevrim kullanilir."))
        sol.addWidget(ayrac())
        sol.addWidget(baslik("Baslangic kaynagi"))
        sol.addLayout(kaynak_form)
        sol.addWidget(ayrac())
        sol.addWidget(baslik("Calistirma"))
        sol.addLayout(kosu_form)
        sol.addStretch(1)

        sag = QtWidgets.QVBoxLayout()
        sag.addWidget(baslik("Guc dagilimi"))
        sag.addLayout(guc_form)
        self.guc_not.setMinimumWidth(1)
        sag.addWidget(self.guc_not)
        sag.addWidget(ayrac())
        sag.addWidget(baslik("Tally'ler"))
        sag.addLayout(tally_bolucu, 1)

        sol_k = QtWidgets.QWidget(); sol_k.setLayout(sol)
        sag_k = QtWidgets.QWidget(); sag_k.setLayout(sag)
        bolucu = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        bolucu.addWidget(sol_k); bolucu.addWidget(sag_k)
        bolucu.setStretchFactor(0, 4); bolucu.setStretchFactor(1, 5)
        bolucu.setSizes([420, 520])
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(bolucu)

        for w in (self.parcacik, self.cevrim, self.pasif, self.tohum,
                  self.is_parcacigi, self.kx, self.ky, self.kz,
                  self.entropi_nx, self.entropi_ny, self.entropi_nz,
                  self.kinetik_nesil, self.guc_dilim, self.guc_toplam,
                  self.t_mesh_nx, self.t_mesh_ny, self.t_mesh_nz):
            w.valueChanged.connect(self._kaydet)
        self.entropi_var.toggled.connect(self._kaydet)
        self.kinetik_var.toggled.connect(self._kaydet)
        self.guc_var.toggled.connect(self._kaydet)
        self.guc_cubuk.currentIndexChanged.connect(self._guc_cubuk_degisti)
        self.guc_bolge.currentIndexChanged.connect(self._kaydet)
        self.guc_skor.currentIndexChanged.connect(self._kaydet)
        for w in (self.mod, self.sicaklik_yontemi, self.kaynak_tur,
                  self.kaynak_parcacik, self.tayf, self.aci_tur):
            w.currentIndexChanged.connect(self._kaydet)
        for w in (self.watt_a, self.maxwell_theta, self.tek_enerji,
                  self.fuzyon_e0, self.fuzyon_kt):
            w.degisti.connect(self._kaydet)
        for w in (self.watt_b, self.fuzyon_kutle, self.koni_aci,
                  self.ax, self.ay, self.az):
            w.valueChanged.connect(self._kaydet)
        for w in (self.ayrik_metin, self.hist_kenar, self.hist_deger,
                  self.kaynak_kuvvet):
            w.editingFinished.connect(self._kaydet)
        self.kosu_dizini.editingFinished.connect(self._kaydet)
        self.t_ad.editingFinished.connect(self._tally_kaydet)
        self.t_skor.itemSelectionChanged.connect(self._tally_kaydet)
        self.t_enerji.editingFinished.connect(self._tally_kaydet)
        for w in (self.t_enerji_var, self.t_mesh_var):
            w.toggled.connect(self._tally_kaydet)

    def _sar(self, duzen):
        w = QtWidgets.QWidget()
        w.setLayout(duzen)
        return w

    # ------------------------------------------------------------------
    def doldur(self):
        a = self.spec["ayarlar"]
        i = self.mod.findData(a.get("mod", "eigenvalue"))
        self.mod.setCurrentIndex(max(i, 0))
        self.parcacik.setValue(a.get("parcacik", 10000))
        self.cevrim.setValue(a.get("cevrim", 150))
        self.pasif.setValue(a.get("pasif", 40))
        self.tohum.setValue(a.get("tohum") or 1)
        self.sicaklik_yontemi.setCurrentText(a.get("sicaklik_yontemi", "interpolation"))

        k = a.get("kaynak") or {}
        i = self.kaynak_tur.findData(k.get("tur", "nokta"))
        self.kaynak_tur.setCurrentIndex(max(i, 0))
        konum = k.get("konum") or [0.0, 0.0, 0.0]
        self.kx.setValue(konum[0]); self.ky.setValue(konum[1]); self.kz.setValue(konum[2])
        i = self.kaynak_parcacik.findData(k.get("parcacik") or "neutron")
        self.kaynak_parcacik.setCurrentIndex(max(i, 0))
        self.kaynak_kuvvet.ayarla(k.get("kuvvet") or 1.0)

        e = k.get("enerji") or {}
        i = self.tayf.findData(e.get("tur", "watt"))
        self.tayf.setCurrentIndex(max(i, 0))
        self.watt_a.ayarla(e.get("a", 988.0e3))
        self.watt_b.setValue(e.get("b", 2.249e-6))
        self.maxwell_theta.ayarla(e.get("theta", 1.2932e6))
        self.tek_enerji.ayarla(e.get("enerji", 14.1e6))
        if e.get("noktalar"):
            self.ayrik_metin.setText(", ".join("%g:%g" % (p[0], p[1])
                                               for p in e["noktalar"]))
        if e.get("kenarlar"):
            self.hist_kenar.setText(", ".join("%g" % x for x in e["kenarlar"]))
        if e.get("degerler"):
            self.hist_deger.setText(", ".join("%g" % x for x in e["degerler"]))
        self.fuzyon_e0.ayarla(e.get("e0", 14.08e6))
        self.fuzyon_kutle.setValue(e.get("kutle_orani", 5.0))
        self.fuzyon_kt.ayarla(e.get("iyon_sicaklik", 20.0e3))

        ac = k.get("aci") or {}
        i = self.aci_tur.findData(ac.get("tur", "izotropik"))
        self.aci_tur.setCurrentIndex(max(i, 0))
        yon = ac.get("yon") or [0.0, 0.0, 1.0]
        self.ax.setValue(yon[0]); self.ay.setValue(yon[1]); self.az.setValue(yon[2])
        self.koni_aci.setValue(ac.get("koni_aci") or 30.0)

        ent = a.get("entropi_mesh") or {}
        self.entropi_var.setChecked(bool(ent.get("var", True)))
        boyut = ent.get("boyut") or [8, 8, 1]
        self.entropi_nx.setValue(boyut[0]); self.entropi_ny.setValue(boyut[1])
        self.entropi_nz.setValue(boyut[2])

        kin = a.get("kinetik") or {}
        self.kinetik_var.setChecked(bool(kin.get("var")))
        self.kinetik_nesil.setValue(kin.get("nesil") or 10)

        g = self.spec.get("guc_dagilimi") or {}
        self.guc_var.setChecked(bool(g.get("var")))
        self.guc_cubuk.clear()
        for cb in self.spec.get("cubuklar", []):
            self.guc_cubuk.addItem(cb["ad"], cb["ad"])
        i = self.guc_cubuk.findData(g.get("cubuk"))
        if i >= 0:
            self.guc_cubuk.setCurrentIndex(i)
        self._guc_bolgeleri_doldur(g.get("bolge"))
        self.guc_skor.setCurrentText(g.get("skor") or "kappa-fission")
        self.guc_dilim.setValue(g.get("eksenel_dilim") or 20)
        self.guc_toplam.setValue(g.get("toplam_guc") or 0.0)

        c = self.spec["calistirma"]
        self.is_parcacigi.setValue(c.get("is_parcacigi", 8))
        self.kosu_dizini.setText(c.get("dizin", "kosu"))

        self.tally_liste.clear()
        for t in self.spec.get("tallyler", []):
            self.tally_liste.addItem(t["ad"])
        if self.tally_liste.count():
            self.tally_liste.setCurrentRow(0)
        self._aktif_guncelle()
        self._kaynak_gorunurluk()
        for w in (self.entropi_etiket, self.entropi_nx, self.entropi_ny, self.entropi_nz):
            w.setEnabled(self.entropi_var.isChecked())
        for w in (self.kinetik_etiket, self.kinetik_nesil):
            w.setEnabled(self.kinetik_var.isChecked())

    def _guc_bolgeleri_doldur(self, secili=None):
        """Secili cubugun bolgelerini listeler (malzeme adiyla birlikte)."""
        self.guc_bolge.clear()
        ad = self.guc_cubuk.currentData()
        c = sema.cubuk_bul(self.spec, ad) if ad else None
        if c:
            for i, b in enumerate(c["bolgeler"]):
                etiket = "%d -- %s" % (i, b.get("malzeme") or "bosluk")
                if b.get("r"):
                    etiket += "  (r = %.4f cm)" % b["r"]
                else:
                    etiket += "  (disarisi)"
                self.guc_bolge.addItem(etiket, i)
        if secili is not None:
            j = self.guc_bolge.findData(secili)
            if j >= 0:
                self.guc_bolge.setCurrentIndex(j)

    def _guc_cubuk_degisti(self, *_):
        if self._yukleniyor:
            return
        self._yukleniyor = True
        try:
            self._guc_bolgeleri_doldur(0)
        finally:
            self._yukleniyor = False
        self._kaydet()

    def _guc_gorunurluk(self):
        acik = self.guc_var.isChecked()
        for w in list(self.guc_etiketler.values()) + [
                self.guc_cubuk, self.guc_bolge, self.guc_skor,
                self.guc_dilim, self.guc_toplam, self.guc_not]:
            w.setEnabled(acik)
        h = sema.kor_yuksekligi((self.spec or {}).get("kor") or {})
        for ad in ("dilim",):
            self.guc_etiketler[ad].setEnabled(acik and bool(h))
        self.guc_dilim.setEnabled(acik and bool(h))

    def _aktif_guncelle(self):
        aktif = self.cevrim.value() - self.pasif.value()
        self.aktif_etiket.setText("%d" % aktif if aktif > 0 else
                                  "%d  <-- pasif cevrim fazla!" % aktif)

    def _kaynak_gorunurluk(self):
        nokta = self.kaynak_tur.currentData() == "nokta"
        self.konum_etiket.setVisible(nokta)
        for w in (self.kx, self.ky, self.kz):
            w.parentWidget().setVisible(nokta)
        self._tayf_gorunurluk()

    @staticmethod
    def _sayi_listesi(metin):
        cikti = []
        for parca in (metin or "").replace(";", ",").split(","):
            parca = parca.strip()
            if not parca:
                continue
            try:
                cikti.append(float(parca))
            except ValueError:
                pass
        return cikti

    def _tayf_oku(self):
        """Arayuzdeki tayf alanlarini spec sozluguna cevirir."""
        e = dict((self.spec["ayarlar"].get("kaynak") or {}).get("enerji") or {})
        e.update({
            "tur": self.tayf.currentData(),
            "a": self.watt_a.deger(),
            "b": self.watt_b.value(),
            "theta": self.maxwell_theta.deger(),
            "enerji": self.tek_enerji.deger(),
            "e0": self.fuzyon_e0.deger(),
            "kutle_orani": self.fuzyon_kutle.value(),
            "iyon_sicaklik": self.fuzyon_kt.deger(),
        })
        noktalar = []
        for parca in (self.ayrik_metin.text() or "").replace(";", ",").split(","):
            if ":" not in parca:
                continue
            a_, b_ = parca.split(":", 1)
            try:
                noktalar.append([float(a_), float(b_)])
            except ValueError:
                pass
        e["noktalar"] = noktalar
        e["kenarlar"] = self._sayi_listesi(self.hist_kenar.text())
        e["degerler"] = self._sayi_listesi(self.hist_deger.text())
        return e

    def _tayf_gorunurluk(self):
        """Yalnizca secili tayfin alanlari gorunur; ozet satiri guncellenir."""
        i = max(self.tayf.currentIndex(), 0)
        self.tayf_yigin.setCurrentIndex(i)
        aci = self.aci_tur.currentData()
        self.yon_etiket.setVisible(aci != "izotropik")
        self.ax.parentWidget().setVisible(aci != "izotropik")
        self.koni_etiket.setVisible(aci == "koni")
        self.koni_aci.setVisible(aci == "koni")
        sabit = self.mod.currentData() != "eigenvalue"
        self.kuvvet_etiket.setEnabled(sabit)
        self.kaynak_kuvvet.setEnabled(sabit)

        e = self._tayf_oku()
        try:
            _kaynak.enerji_dagilimi(e)
            ort = _kaynak.ortalama_enerji(e)
            metin = ("Ortalama enerji: %s" % _kaynak.enerji_metni(ort)) if ort else ""
            if not sabit:
                metin += ("\nOzdeger modunda tayf yalnizca baslangic tahminidir; "
                          "pasif cevrimlerde gercek fisyon tayfiyla degisir.")
            elif self.kaynak_kuvvet.deger(1.0) == 1.0:
                metin += "\nSiddet 1 -- sonuclar kaynak parcacigi basina kalir."
            else:
                metin += ("\nSonuclar mutlak birimde olur (OpenMC siddeti kendisi "
                          "uygular, ayrica carpmayin).")
            self.tayf_ozet.setText(metin)
            self.tayf_ozet.setStyleSheet("")
        except Exception as hata:
            self.tayf_ozet.setText("Tayf kurulamadi: %s" % hata)
            self.tayf_ozet.setStyleSheet("color: #d04437;")

    def _kaydet(self, *_):
        if self._yukleniyor:
            return
        a = self.spec["ayarlar"]
        a["mod"] = self.mod.currentData()
        a["parcacik"] = self.parcacik.value()
        a["cevrim"] = self.cevrim.value()
        a["pasif"] = self.pasif.value()
        a["tohum"] = self.tohum.value()
        a["sicaklik_yontemi"] = self.sicaklik_yontemi.currentText()
        a["entropi_mesh"] = {
            "var": self.entropi_var.isChecked(),
            "boyut": [self.entropi_nx.value(), self.entropi_ny.value(),
                      self.entropi_nz.value()],
        }
        a["kinetik"] = {"var": self.kinetik_var.isChecked(),
                        "nesil": self.kinetik_nesil.value()}
        self.spec["guc_dagilimi"] = {
            "var": self.guc_var.isChecked(),
            "cubuk": self.guc_cubuk.currentData(),
            "bolge": self.guc_bolge.currentData() or 0,
            "skor": self.guc_skor.currentText(),
            "eksenel_dilim": self.guc_dilim.value(),
            "toplam_guc": (self.guc_toplam.value() or None),
        }
        self._guc_gorunurluk()
        for w in (self.kinetik_etiket, self.kinetik_nesil):
            w.setEnabled(self.kinetik_var.isChecked())
        for w in (self.entropi_etiket, self.entropi_nx, self.entropi_ny, self.entropi_nz):
            w.setEnabled(self.entropi_var.isChecked())
        # Kaynak sozlugu BASTAN YAZILMAZ: eskiden oyleydi ve her kayitta
        # enerji tayfi, acisal dagilim, parcacik turu ve siddet siliniyordu.
        kay = a.setdefault("kaynak", {})
        if self.kaynak_tur.currentData() == "nokta":
            kay["tur"] = "nokta"
            kay["konum"] = [self.kx.value(), self.ky.value(), self.kz.value()]
            kay.pop("alt", None)
            kay.pop("ust", None)
        else:
            kay["tur"] = "kutu"
            kay["alt"] = None
            kay["ust"] = None
        kay["parcacik"] = self.kaynak_parcacik.currentData()
        kay["kuvvet"] = self.kaynak_kuvvet.deger(1.0)
        kay["enerji"] = self._tayf_oku()
        kay["aci"] = {"tur": self.aci_tur.currentData(),
                      "yon": [self.ax.value(), self.ay.value(), self.az.value()],
                      "koni_aci": self.koni_aci.value()}
        self._tayf_gorunurluk()
        self.spec["calistirma"]["is_parcacigi"] = self.is_parcacigi.value()
        self.spec["calistirma"]["dizin"] = self.kosu_dizini.text().strip() or "kosu"
        self._aktif_guncelle()
        self._kaynak_gorunurluk()
        self.bildir()

    # ------------------------------------------------------------------
    def _secili_tally(self):
        i = self.tally_liste.currentRow()
        tallyler = self.spec.get("tallyler", [])
        return tallyler[i] if 0 <= i < len(tallyler) else None

    def _tally_secildi(self, _satir):
        t = self._secili_tally()
        if t is None:
            return
        eski = self._yukleniyor
        self._yukleniyor = True
        try:
            self.t_ad.setText(t["ad"])
            self.t_skor.clearSelection()
            for i in range(self.t_skor.count()):
                if self.t_skor.item(i).text() in t.get("skorlar", []):
                    self.t_skor.item(i).setSelected(True)
            enerji = next((f for f in t.get("filtreler", []) if f["tur"] == "enerji"), None)
            self.t_enerji_var.setChecked(bool(enerji))
            if enerji:
                self.t_enerji.setText(", ".join(str(g) for g in enerji["gruplar"]))
            mesh = next((f for f in t.get("filtreler", []) if f["tur"] == "mesh"), None)
            self.t_mesh_var.setChecked(bool(mesh))
            if mesh:
                self.t_mesh_nx.setValue(mesh["boyut"][0])
                self.t_mesh_ny.setValue(mesh["boyut"][1])
                self.t_mesh_nz.setValue(mesh["boyut"][2])
        finally:
            self._yukleniyor = eski

    def _tally_kaydet(self, *_):
        if self._yukleniyor:
            return
        t = self._secili_tally()
        if t is None:
            return
        t["ad"] = self.t_ad.text().strip() or t["ad"]
        t["skorlar"] = [o.text() for o in self.t_skor.selectedItems()] or ["flux"]
        filtreler = []
        if self.t_enerji_var.isChecked():
            try:
                gruplar = [float(x) for x in self.t_enerji.text().replace(";", ",").split(",")
                           if x.strip()]
                if len(gruplar) >= 2:
                    filtreler.append(sema.filtre_enerji(sorted(gruplar)))
            except ValueError:
                pass
        if self.t_mesh_var.isChecked():
            try:
                from cekirdek import onbellek
                _, bilgi = onbellek.kur_onbellekli(self.spec)
                gx, gy = bilgi["sinir_kutu"]
            except Exception:
                gx = gy = 10.0
            h = sema.kor_yuksekligi(self.spec["kor"]) or 2.0
            filtreler.append(sema.filtre_mesh(
                [self.t_mesh_nx.value(), self.t_mesh_ny.value(), self.t_mesh_nz.value()],
                [-gx / 2, -gy / 2, -h / 2], [gx / 2, gy / 2, h / 2]))
        t["filtreler"] = filtreler
        i = self.tally_liste.currentRow()
        if i >= 0:
            self.tally_liste.item(i).setText(t["ad"])
        self.bildir()

    def _tally_ekle(self):
        mevcut = {t["ad"] for t in self.spec.get("tallyler", [])}
        ad, i = "tally", 1
        while ad in mevcut:
            i += 1
            ad = "tally_%d" % i
        self.spec.setdefault("tallyler", []).append(
            sema.tally(ad, ["flux", "fission"]))
        self.spec_yukle(self.spec)
        self.tally_liste.setCurrentRow(self.tally_liste.count() - 1)
        self.bildir()

    def _tally_sil(self):
        i = self.tally_liste.currentRow()
        if i < 0:
            return
        self.spec["tallyler"].pop(i)
        self.spec_yukle(self.spec)
        self.bildir()
