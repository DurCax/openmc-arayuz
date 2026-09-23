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
from arayuz.ortak import SekmeTabani, ayrac, baslik, ipucu, sayi, tamsayi

SKORLAR = ["flux", "fission", "absorption", "nu-fission", "scatter", "total",
           "elastic", "(n,gamma)", "(n,2n)", "heating", "kappa-fission",
           "fission-q-prompt", "damage-energy"]


class AyarSekmesi(SekmeTabani):

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

        # --- kaynak ---
        self.kaynak_tur = QtWidgets.QComboBox()
        self.kaynak_tur.addItem("Nokta kaynak", "nokta")
        self.kaynak_tur.addItem("Kutu (yalnizca fisil bolgeler)", "kutu")
        self.kx = sayi(0.0, 4, -1e5, 1e5, 0.1, "cm")
        self.ky = sayi(0.0, 4, -1e5, 1e5, 0.1, "cm")
        self.kz = sayi(0.0, 4, -1e5, 1e5, 0.1, "cm")

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

        kaynak_form = QtWidgets.QFormLayout()
        kaynak_form.addRow("Kaynak tipi:", self.kaynak_tur)
        konum = QtWidgets.QHBoxLayout()
        for e, w in (("x", self.kx), ("y", self.ky), ("z", self.kz)):
            konum.addWidget(QtWidgets.QLabel(e))
            konum.addWidget(w)
        konum.addStretch(1)
        self.konum_etiket = QtWidgets.QLabel("Nokta konumu:")
        kaynak_form.addRow(self.konum_etiket, self._sar(konum))

        kosu_form = QtWidgets.QFormLayout()
        kosu_form.addRow("OpenMP is parcacigi:", self.is_parcacigi)
        kosu_form.addRow("Kosu dizini:", self.kosu_dizini)

        # --- tally'ler ---
        self.tally_liste = QtWidgets.QListWidget()
        self.tally_liste.currentRowChanged.connect(self._tally_secildi)
        self.t_ad = QtWidgets.QLineEdit()
        self.t_skor = QtWidgets.QListWidget()
        self.t_skor.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        for s in SKORLAR:
            self.t_skor.addItem(s)
        self.t_skor.setMaximumHeight(120)
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
        tally_bolucu.addLayout(tally_sol, 1)
        tally_bolucu.addLayout(t_form, 2)

        # --- yerlesim ---
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(baslik("Kosu ayarlari"))
        duzen.addLayout(form)
        duzen.addWidget(ipucu(
            "Pasif cevrimler kaynak dagilimi yakinsayana kadar atilir ve "
            "istatistige katilmaz. Tipik olarak 20-50 pasif cevrim kullanilir."))
        duzen.addWidget(ayrac())
        duzen.addWidget(baslik("Baslangic kaynagi"))
        duzen.addLayout(kaynak_form)
        duzen.addWidget(ayrac())
        duzen.addWidget(baslik("Calistirma"))
        duzen.addLayout(kosu_form)
        duzen.addWidget(ayrac())
        duzen.addWidget(baslik("Tally'ler"))
        duzen.addLayout(tally_bolucu, 1)

        for w in (self.parcacik, self.cevrim, self.pasif, self.tohum,
                  self.is_parcacigi, self.kx, self.ky, self.kz,
                  self.t_mesh_nx, self.t_mesh_ny, self.t_mesh_nz):
            w.valueChanged.connect(self._kaydet)
        for w in (self.mod, self.sicaklik_yontemi, self.kaynak_tur):
            w.currentIndexChanged.connect(self._kaydet)
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

    def _aktif_guncelle(self):
        aktif = self.cevrim.value() - self.pasif.value()
        self.aktif_etiket.setText("%d" % aktif if aktif > 0 else
                                  "%d  <-- pasif cevrim fazla!" % aktif)

    def _kaynak_gorunurluk(self):
        nokta = self.kaynak_tur.currentData() == "nokta"
        self.konum_etiket.setVisible(nokta)
        for w in (self.kx, self.ky, self.kz):
            w.parentWidget().setVisible(nokta)

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
        if self.kaynak_tur.currentData() == "nokta":
            a["kaynak"] = {"tur": "nokta",
                           "konum": [self.kx.value(), self.ky.value(), self.kz.value()]}
        else:
            a["kaynak"] = {"tur": "kutu", "alt": None, "ust": None}
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
                from cekirdek import kurucu
                _, bilgi = kurucu.kur(self.spec)
                gx, gy = bilgi["sinir_kutu"]
            except Exception:
                gx = gy = 10.0
            h = self.spec["kor"].get("yukseklik") or 2.0
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
