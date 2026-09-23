# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_kor.py  --  Kor duzeni, yansitici, yukseklik ve sinir kosullari
================================================================================
 Kor turu secildiginde ilgili alanlar gosterilir:
   tek_cubuk   tek yakit cubugu + hucre adimi         (pin cell)
   tek_plaka   tek MTR plaka elemani
   tek_demet   tek kafes demeti
   kare_kafes  demetlerden olusan kare kor + harita
================================================================================
"""

from PySide6 import QtCore, QtWidgets

from cekirdek import sema
from arayuz.ortak import SekmeTabani, ayrac, baslik, ipucu, sayi, tamsayi

TURLER = [
    ("tek_cubuk", "Tek cubuk (pin hucre)"),
    ("tek_plaka", "Tek plaka elemani"),
    ("tek_demet", "Tek kafes demeti"),
    ("kare_kafes", "Kare kor kafesi (demetlerden)"),
]
SINIRLAR = ["reflective", "vacuum", "periodic", "white"]


class KorSekmesi(SekmeTabani):

    KONU = "kor"

    def __init__(self, parent=None):
        super().__init__(parent)

        self.tur = QtWidgets.QComboBox()
        for deger, etiket in TURLER:
            self.tur.addItem(etiket, deger)
        self.tur.currentIndexChanged.connect(self._tur_degisti)

        # --- tur'e gore degisen alanlar ---
        self.cubuk = QtWidgets.QComboBox()
        self.plaka = QtWidgets.QComboBox()
        self.demet = QtWidgets.QComboBox()
        self.adim = sayi(1.26, 5, 0.0001, 1000.0, 0.01, "cm")
        self.nx = tamsayi(3, 1, 100)
        self.ny = tamsayi(3, 1, 100)
        self.harita = QtWidgets.QPlainTextEdit()
        self.harita.setPlaceholderText("Her satir bir kor sirasi, her karakter bir demet")
        self.harita.setMaximumHeight(140)
        f = self.harita.font(); f.setFamily("monospace"); self.harita.setFont(f)
        self.anahtar_tablo = QtWidgets.QTableWidget(0, 2)
        self.anahtar_tablo.setHorizontalHeaderLabels(["Harf", "Hedef"])
        self.anahtar_tablo.horizontalHeader().setStretchLastSection(True)
        self.anahtar_tablo.verticalHeader().setVisible(False)
        self.anahtar_tablo.setMaximumHeight(130)
        self.d_harf_ekle = QtWidgets.QPushButton("Harf ekle")
        self.d_harf_sil = QtWidgets.QPushButton("Harf sil")
        self.d_harf_ekle.clicked.connect(self._harf_ekle)
        self.d_harf_sil.clicked.connect(self._harf_sil)

        # --- eksenel ve sinir ---
        self.yukseklik_var = QtWidgets.QCheckBox("Eksenel yukseklik tanimla (3B)")
        self.yukseklik = sayi(366.0, 3, 0.01, 10000.0, 1.0, "cm")
        self.yukseklik_var.toggled.connect(self._yukseklik_degisti)

        self.bc_yan = QtWidgets.QComboBox(); self.bc_yan.addItems(SINIRLAR)
        self.bc_alt = QtWidgets.QComboBox(); self.bc_alt.addItems(SINIRLAR)
        self.bc_ust = QtWidgets.QComboBox(); self.bc_ust.addItems(SINIRLAR)

        # --- yansitici ---
        self.yans_var = QtWidgets.QCheckBox("Yansitici kusak ekle")
        self.yans_kal = sayi(20.0, 3, 0.01, 1000.0, 1.0, "cm")
        self.yans_mal = QtWidgets.QComboBox()

        self.ozet = QtWidgets.QLabel("-")

        # --- yerlesim ---
        self.form = QtWidgets.QFormLayout()
        self.form.addRow("Kor turu:", self.tur)
        self.satir_cubuk = self._satir("Cubuk:", self.cubuk)
        self.satir_plaka = self._satir("Plaka elemani:", self.plaka)
        self.satir_demet = self._satir("Kafes demeti:", self.demet)
        self.satir_adim = self._satir("Hucre / demet adimi:", self.adim)
        boyut = QtWidgets.QHBoxLayout()
        boyut.addWidget(QtWidgets.QLabel("nx")); boyut.addWidget(self.nx)
        boyut.addWidget(QtWidgets.QLabel("ny")); boyut.addWidget(self.ny)
        boyut.addStretch(1)
        self.satir_boyut = self._satir("Kor boyutu:", boyut)

        harf_dugme = QtWidgets.QHBoxLayout()
        harf_dugme.addWidget(self.d_harf_ekle)
        harf_dugme.addWidget(self.d_harf_sil)
        harf_dugme.addStretch(1)

        self.kafes_kutu = QtWidgets.QGroupBox("Kor haritasi")
        kd = QtWidgets.QVBoxLayout(self.kafes_kutu)
        kd.addWidget(ipucu("Her satir bir kor sirasidir. Satir sayisi ny, satir "
                           "uzunlugu nx olmalidir; uyusmazsa dogrulama uyarir."))
        kd.addWidget(self.harita)
        kd.addWidget(self.anahtar_tablo)
        kd.addLayout(harf_dugme)

        eksen_kutu = QtWidgets.QGroupBox("Eksenel yon ve sinir kosullari")
        ed = QtWidgets.QFormLayout(eksen_kutu)
        ed.addRow(self.yukseklik_var)
        ed.addRow("Aktif yukseklik:", self.yukseklik)
        ed.addRow("Yan sinir:", self.bc_yan)
        ed.addRow("Alt sinir:", self.bc_alt)
        ed.addRow("Ust sinir:", self.bc_ust)

        yans_kutu = QtWidgets.QGroupBox("Yansitici")
        yd = QtWidgets.QFormLayout(yans_kutu)
        yd.addRow(self.yans_var)
        yd.addRow("Kalinlik:", self.yans_kal)
        yd.addRow("Malzeme:", self.yans_mal)
        yd.addRow(ipucu("Yansitici yalnizca 'tek demet' ve 'kare kor kafesi' "
                        "turlerinde uygulanir."))

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(baslik("Kor duzeni"))
        duzen.addLayout(self.form)
        duzen.addWidget(self.kafes_kutu)
        duzen.addWidget(ayrac())
        ikili = QtWidgets.QHBoxLayout()
        ikili.addWidget(eksen_kutu)
        ikili.addWidget(yans_kutu)
        duzen.addLayout(ikili)
        duzen.addWidget(self._ozet_satiri())
        duzen.addStretch(1)

        for w in (self.cubuk, self.plaka, self.demet, self.bc_yan, self.bc_alt,
                  self.bc_ust, self.yans_mal):
            w.currentIndexChanged.connect(self._kaydet)
        for w in (self.adim, self.yukseklik, self.yans_kal):
            w.valueChanged.connect(self._kaydet)
        for w in (self.nx, self.ny):
            w.valueChanged.connect(self._kaydet)
        self.yans_var.toggled.connect(self._kaydet)
        self.harita.textChanged.connect(self._kaydet)

    def _satir(self, etiket, w):
        if isinstance(w, QtWidgets.QLayout):
            sarmal = QtWidgets.QWidget()
            sarmal.setLayout(w)
            w = sarmal
        e = QtWidgets.QLabel(etiket)
        self.form.addRow(e, w)
        return (e, w)

    def _ozet_satiri(self):
        k = QtWidgets.QWidget()
        d = QtWidgets.QHBoxLayout(k)
        d.setContentsMargins(0, 6, 0, 0)
        d.addWidget(QtWidgets.QLabel("Toplam model olcusu:"))
        d.addWidget(self.ozet)
        d.addStretch(1)
        return k

    # ------------------------------------------------------------------
    def doldur(self):
        kor = self.spec["kor"]
        i = self.tur.findData(kor.get("tur", "tek_cubuk"))
        self.tur.setCurrentIndex(max(i, 0))

        self._kutu_doldur(self.cubuk, [(c["ad"], c["ad"]) for c in self.spec.get("cubuklar", [])],
                          kor.get("cubuk"))
        self._kutu_doldur(self.plaka, [(p["ad"], p["ad"]) for p in self.spec.get("plakalar", [])],
                          kor.get("plaka"))
        self._kutu_doldur(self.demet, [(d["ad"], d["ad"]) for d in self.spec.get("demetler", [])],
                          kor.get("demet"))
        malzemeler = [(sema.BOSLUK, "bosluk (void)")] + \
                     [(m["ad"], "%s -- %s" % (m["ad"], m.get("gorunen_ad") or ""))
                      for m in self.spec["malzemeler"]]
        self._kutu_doldur(self.yans_mal, malzemeler, (kor.get("yansitici") or {}).get("malzeme"))

        self.adim.setValue(kor.get("adim") or 1.26)
        self.nx.setValue(kor.get("boyut", [1, 1])[0])
        self.ny.setValue(kor.get("boyut", [1, 1])[1])
        self.harita.setPlainText("\n".join(kor.get("harita") or []))
        self._anahtar_doldur()

        h = kor.get("yukseklik")
        self.yukseklik_var.setChecked(bool(h))
        self.yukseklik.setValue(h or 366.0)
        self.yukseklik.setEnabled(bool(h))

        sinir = kor.get("sinir") or {}
        self.bc_yan.setCurrentText(sinir.get("yan", "reflective"))
        self.bc_alt.setCurrentText(sinir.get("alt", "reflective"))
        self.bc_ust.setCurrentText(sinir.get("ust", "reflective"))

        yans = kor.get("yansitici") or {}
        self.yans_var.setChecked(bool(yans.get("var")))
        self.yans_kal.setValue(yans.get("kalinlik") or 20.0)

        self._gorunurluk()
        self._ozet_guncelle()

    def _kutu_doldur(self, kutu, ogeler, secili):
        kutu.clear()
        for deger, etiket in ogeler:
            kutu.addItem(etiket, deger)
        i = kutu.findData(secili)
        if i >= 0:
            kutu.setCurrentIndex(i)

    def _anahtar_doldur(self):
        kor = self.spec["kor"]
        self.anahtar_tablo.setRowCount(0)
        hedefler = [(sema.BOSLUK, "bosluk (void)")]
        hedefler += [(d["ad"], "kafes: %s" % d["ad"]) for d in self.spec.get("demetler", [])]
        hedefler += [(c["ad"], "cubuk: %s" % c["ad"]) for c in self.spec.get("cubuklar", [])]
        hedefler += [(m["ad"], "malzeme: %s" % m["ad"]) for m in self.spec["malzemeler"]]
        for harf in sorted((kor.get("anahtar") or {}).keys()):
            satir = self.anahtar_tablo.rowCount()
            self.anahtar_tablo.insertRow(satir)
            h = QtWidgets.QTableWidgetItem(harf)
            h.setTextAlignment(QtCore.Qt.AlignCenter)
            h.setFlags(QtCore.Qt.ItemIsEnabled)
            self.anahtar_tablo.setItem(satir, 0, h)
            kutu = QtWidgets.QComboBox()
            for deger, etiket in hedefler:
                kutu.addItem(etiket, deger)
            i = kutu.findData(kor["anahtar"][harf])
            if i >= 0:
                kutu.setCurrentIndex(i)
            kutu.currentIndexChanged.connect(self._kaydet)
            self.anahtar_tablo.setCellWidget(satir, 1, kutu)
        self.anahtar_tablo.resizeColumnsToContents()

    # ------------------------------------------------------------------
    def _gorunurluk(self):
        tur = self.tur.currentData()
        for satir, gorunur in (
                (self.satir_cubuk, tur == "tek_cubuk"),
                (self.satir_plaka, tur == "tek_plaka"),
                (self.satir_demet, tur == "tek_demet"),
                (self.satir_adim, tur in ("tek_cubuk", "kare_kafes")),
                (self.satir_boyut, tur == "kare_kafes")):
            for w in satir:
                w.setVisible(gorunur)
        self.kafes_kutu.setVisible(tur == "kare_kafes")
        yans_uygun = tur in ("tek_demet", "kare_kafes")
        self.yans_var.setEnabled(yans_uygun)
        self.yans_kal.setEnabled(yans_uygun and self.yans_var.isChecked())
        self.yans_mal.setEnabled(yans_uygun and self.yans_var.isChecked())
        self.bc_alt.setEnabled(self.yukseklik_var.isChecked())
        self.bc_ust.setEnabled(self.yukseklik_var.isChecked())

    def _tur_degisti(self, *_):
        self._gorunurluk()
        self._kaydet()

    def _yukseklik_degisti(self, acik):
        self.yukseklik.setEnabled(acik)
        self.bc_alt.setEnabled(acik)
        self.bc_ust.setEnabled(acik)
        self._kaydet()

    def _ozet_guncelle(self):
        try:
            from cekirdek import onbellek
            _, bilgi = onbellek.kur_onbellekli(self.spec)
            gx, gy = bilgi["sinir_kutu"]
            h = self.spec["kor"].get("yukseklik")
            self.ozet.setText("%.4f x %.4f cm%s" % (gx, gy, (" x %.2f cm" % h) if h else "  (2B)"))
        except Exception as e:
            self.ozet.setText("kurulamadi: %s" % str(e)[:80])

    # ------------------------------------------------------------------
    def _kaydet(self, *_):
        if self._yukleniyor:
            return
        kor = self.spec["kor"]
        kor["tur"] = self.tur.currentData()
        kor["cubuk"] = self.cubuk.currentData()
        kor["plaka"] = self.plaka.currentData()
        kor["demet"] = self.demet.currentData()
        kor["adim"] = self.adim.value()
        kor["boyut"] = [self.nx.value(), self.ny.value()]
        kor["harita"] = [s for s in self.harita.toPlainText().split("\n") if s.strip()]
        anahtar = {}
        for i in range(self.anahtar_tablo.rowCount()):
            harf = self.anahtar_tablo.item(i, 0).text()
            kutu = self.anahtar_tablo.cellWidget(i, 1)
            anahtar[harf] = kutu.currentData()
        kor["anahtar"] = anahtar
        kor["yukseklik"] = self.yukseklik.value() if self.yukseklik_var.isChecked() else None
        kor["sinir"] = {"yan": self.bc_yan.currentText(),
                        "alt": self.bc_alt.currentText(),
                        "ust": self.bc_ust.currentText()}
        kor["yansitici"] = {"var": self.yans_var.isChecked(),
                            "kalinlik": self.yans_kal.value(),
                            "malzeme": self.yans_mal.currentData()}
        self._gorunurluk()
        self._ozet_guncelle()
        self.bildir()

    def _harf_ekle(self):
        import string
        kor = self.spec["kor"]
        kullanilan = set((kor.get("anahtar") or {}).keys())
        for harf in string.ascii_lowercase:
            if harf not in kullanilan:
                break
        else:
            return
        demetler = self.spec.get("demetler", [])
        kor.setdefault("anahtar", {})[harf] = demetler[0]["ad"] if demetler else sema.BOSLUK
        self._yukleniyor = True
        try:
            self._anahtar_doldur()
        finally:
            self._yukleniyor = False
        self.bildir()

    def _harf_sil(self):
        satir = self.anahtar_tablo.currentRow()
        if satir < 0:
            return
        harf = self.anahtar_tablo.item(satir, 0).text()
        self.spec["kor"].get("anahtar", {}).pop(harf, None)
        self._yukleniyor = True
        try:
            self._anahtar_doldur()
        finally:
            self._yukleniyor = False
        self.bildir()
