# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_demet.py  --  Kafes (lattice) tanimlari ve harita editoru
================================================================================
 Harita harflerden olusur; her harf bir cubuga, plakaya, baska bir demete ya da
 dogrudan bir malzemeye isaret eder.

 KARE kafes    : nx x ny izgara, QTableWidget ile duzenlenir
 ALTIGEN kafes : halkalar DISTAN ICE; gercek altigen yerlesimde cizilir
                 (arayuz/hex_izgara.py). Yaricapi k olan halkada 6k hucre,
                 merkezde 1 hucre bulunur.

 Kafes tipi degistirildiginde harita otomatik olarak yeni duzene cevrilir.
================================================================================
"""

import copy
import string

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import altigen, sema
from arayuz.hex_izgara import HexIzgara, harf_rengi
from arayuz.ortak import SekmeTabani, baslik, ipucu, sayi, tamsayi


class DemetSekmesi(SekmeTabani):
    """Kafes listesi + kare/altigen harita editoru."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._firca = None

        # ---------------- sol: kafes listesi ----------------
        self.liste = QtWidgets.QListWidget()
        self.liste.currentRowChanged.connect(self._secim_degisti)
        d_kare = QtWidgets.QPushButton("+ Kare kafes")
        d_hex = QtWidgets.QPushButton("+ Altigen kafes")
        d_kopya = QtWidgets.QPushButton("Kopyala")
        d_sil = QtWidgets.QPushButton("Sil")
        d_kare.clicked.connect(lambda: self._yeni("kare"))
        d_hex.clicked.connect(lambda: self._yeni("altigen"))
        d_kopya.clicked.connect(self._kopyala)
        d_sil.clicked.connect(self._sil)
        sol = QtWidgets.QWidget()
        sol_d = QtWidgets.QVBoxLayout(sol)
        sol_d.setContentsMargins(0, 0, 0, 0)
        sol_d.addWidget(baslik("Kafesler"))
        sol_d.addWidget(self.liste, 1)
        for d in (d_kare, d_hex, d_kopya, d_sil):
            sol_d.addWidget(d)

        # ---------------- sag ust: ozellikler ----------------
        self.ad = QtWidgets.QLineEdit()
        self.ad.editingFinished.connect(self._ad_degisti)
        self.tur = QtWidgets.QComboBox()
        self.tur.addItem("Kare (RectLattice)", "kare")
        self.tur.addItem("Altigen (HexLattice)", "altigen")
        self.adim = sayi(1.26, 5, 0.0001, 1000.0, 0.01, "cm")
        self.nx = tamsayi(17, 1, 200)
        self.ny = tamsayi(17, 1, 200)
        self.halka = tamsayi(7, 1, 40, 1, "halka")
        self.yonelim = QtWidgets.QComboBox()
        self.yonelim.addItem("y -- ust/alt yuzler yatay (tepede hucre)", "y")
        self.yonelim.addItem("x -- sag/sol yuzler dusey (sagda hucre)", "x")
        self.dis = QtWidgets.QComboBox()
        self.ozet = QtWidgets.QLabel("-")

        self.form = QtWidgets.QFormLayout()
        self.form.addRow("Ad:", self.ad)
        self.form.addRow("Kafes tipi:", self.tur)
        self.form.addRow("Adim (pitch):", self.adim)
        kare_boyut = QtWidgets.QWidget()
        kb = QtWidgets.QHBoxLayout(kare_boyut)
        kb.setContentsMargins(0, 0, 0, 0)
        kb.addWidget(QtWidgets.QLabel("nx")); kb.addWidget(self.nx)
        kb.addWidget(QtWidgets.QLabel("ny")); kb.addWidget(self.ny)
        kb.addStretch(1)
        self.e_kare_boyut = QtWidgets.QLabel("Boyut:")
        self.w_kare_boyut = kare_boyut
        self.form.addRow(self.e_kare_boyut, self.w_kare_boyut)
        self.e_halka = QtWidgets.QLabel("Halka sayisi:")
        self.form.addRow(self.e_halka, self.halka)
        self.e_yonelim = QtWidgets.QLabel("Yonelim:")
        self.form.addRow(self.e_yonelim, self.yonelim)
        self.form.addRow("Kafes disi dolgu:", self.dis)
        self.form.addRow("Toplam olcu:", self.ozet)

        # ---------------- harf anahtari ----------------
        self.anahtar_tablo = QtWidgets.QTableWidget(0, 3)
        self.anahtar_tablo.setHorizontalHeaderLabels(["Harf", "Hedef", "Firca"])
        self.anahtar_tablo.horizontalHeader().setStretchLastSection(True)
        self.anahtar_tablo.verticalHeader().setVisible(False)
        self.anahtar_tablo.setMaximumHeight(150)
        d_harf_ekle = QtWidgets.QPushButton("Harf ekle")
        d_harf_sil = QtWidgets.QPushButton("Harf sil")
        d_harf_ekle.clicked.connect(self._harf_ekle)
        d_harf_sil.clicked.connect(self._harf_sil)
        harf_dugme = QtWidgets.QHBoxLayout()
        harf_dugme.addWidget(d_harf_ekle)
        harf_dugme.addWidget(d_harf_sil)
        harf_dugme.addStretch(1)
        self.firca_etiket = QtWidgets.QLabel("Firca: (yok)")

        # ---------------- harita alani ----------------
        self.izgara = QtWidgets.QTableWidget(0, 0)
        self.izgara.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.izgara.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.izgara.cellClicked.connect(self._kare_hucre_boya)

        self.hex_izgara = HexIzgara()
        self.hex_izgara.degisti.connect(self._hex_harita_kaydet)
        self.hex_izgara.firca_istendi.connect(self._firca_sec)

        self.harita_yigin = QtWidgets.QStackedWidget()
        self.harita_yigin.addWidget(self.izgara)        # 0 = kare
        self.harita_yigin.addWidget(self.hex_izgara)    # 1 = altigen

        d_doldur = QtWidgets.QPushButton("Secimi doldur")
        d_hepsi = QtWidgets.QPushButton("Tumunu doldur")
        self.d_halka_doldur = QtWidgets.QPushButton("Halkayi doldur...")
        self.etiket_kutusu = QtWidgets.QCheckBox("Halka,indeks etiketleri")
        d_doldur.clicked.connect(self._secimi_doldur)
        d_hepsi.clicked.connect(self._tumunu_doldur)
        self.d_halka_doldur.clicked.connect(self._halka_doldur)
        self.etiket_kutusu.toggled.connect(self.hex_izgara.etiketleri_goster)
        self.d_secimi_doldur = d_doldur
        harita_dugme = QtWidgets.QHBoxLayout()
        harita_dugme.addWidget(self.firca_etiket)
        harita_dugme.addStretch(1)
        harita_dugme.addWidget(self.etiket_kutusu)
        harita_dugme.addWidget(self.d_halka_doldur)
        harita_dugme.addWidget(d_doldur)
        harita_dugme.addWidget(d_hepsi)

        sag = QtWidgets.QWidget()
        sag_d = QtWidgets.QVBoxLayout(sag)
        sag_d.setContentsMargins(0, 0, 0, 0)
        sag_d.addWidget(baslik("Kafes ozellikleri"))
        sag_d.addLayout(self.form)
        sag_d.addWidget(baslik("Harf anahtari"))
        sag_d.addWidget(ipucu(
            "Her harf bir cubuga, plakaya, baska bir kafese ya da dogrudan bir "
            "malzemeye isaret edebilir. 'Firca' sutunundan harf secip haritaya "
            "tiklayarak boyayin. Altigen haritada sag tik, o hucrenin harfini "
            "firca yapar."))
        sag_d.addWidget(self.anahtar_tablo)
        sag_d.addLayout(harf_dugme)
        sag_d.addWidget(baslik("Harita"))
        sag_d.addLayout(harita_dugme)
        sag_d.addWidget(self.harita_yigin, 1)

        bolucu = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        bolucu.addWidget(sol)
        bolucu.addWidget(sag)
        bolucu.setStretchFactor(0, 0)
        bolucu.setStretchFactor(1, 1)
        bolucu.setSizes([190, 640])
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(bolucu)

        self.adim.valueChanged.connect(self._kaydet)
        self.dis.currentIndexChanged.connect(self._kaydet)
        self.yonelim.currentIndexChanged.connect(self._yonelim_degisti)
        self.tur.currentIndexChanged.connect(self._tur_degisti)
        self.nx.valueChanged.connect(self._boyut_degisti)
        self.ny.valueChanged.connect(self._boyut_degisti)
        self.halka.valueChanged.connect(self._halka_degisti)

    # ==================================================================
    def doldur(self):
        secili = self._secili_ad()
        self.liste.clear()
        for d in self.spec.get("demetler", []):
            simge = "[kare]  " if d.get("tur") != "altigen" else "[hex ]  "
            oge = QtWidgets.QListWidgetItem(simge + d["ad"])
            oge.setData(QtCore.Qt.UserRole, d["ad"])
            self.liste.addItem(oge)
        if self.liste.count():
            hedef = 0
            for i in range(self.liste.count()):
                if self.liste.item(i).data(QtCore.Qt.UserRole) == secili:
                    hedef = i
                    break
            self.liste.setCurrentRow(hedef)
            self._secim_degisti(hedef)
        else:
            self._temizle()

    def _temizle(self):
        self.ad.clear()
        self.izgara.setRowCount(0)
        self.izgara.setColumnCount(0)
        self.hex_izgara.yukle([], 0, "y", [])
        self.anahtar_tablo.setRowCount(0)
        self.ozet.setText("-")

    def _secili_ad(self):
        oge = self.liste.currentItem()
        return oge.data(QtCore.Qt.UserRole) if oge else None

    def _secili(self):
        ad = self._secili_ad()
        return sema.demet_bul(self.spec, ad) if ad else None

    def _secim_degisti(self, _satir):
        d = self._secili()
        if d is None:
            self._temizle()
            return
        eski = self._yukleniyor
        self._yukleniyor = True
        try:
            self.ad.setText(d["ad"])
            self.tur.setCurrentIndex(max(self.tur.findData(d.get("tur", "kare")), 0))
            self.adim.setValue(d["adim"])
            self.nx.setValue(d.get("boyut", [1, 1])[0])
            self.ny.setValue(d.get("boyut", [1, 1])[1])
            self.halka.setValue(d.get("halka_sayisi") or 7)
            self.yonelim.setCurrentIndex(max(self.yonelim.findData(d.get("yonelim", "y")), 0))
            self._dis_doldur(d)
            self._anahtar_doldur(d)
            self._harita_doldur(d)
            self._gorunurluk()
            self._ozet_guncelle(d)
        finally:
            self._yukleniyor = eski

    # ==================================================================
    def _gorunurluk(self):
        hex_mi = self.tur.currentData() == "altigen"
        for w in (self.e_kare_boyut, self.w_kare_boyut):
            w.setVisible(not hex_mi)
        for w in (self.e_halka, self.halka, self.e_yonelim, self.yonelim):
            w.setVisible(hex_mi)
        self.harita_yigin.setCurrentIndex(1 if hex_mi else 0)
        self.d_halka_doldur.setVisible(hex_mi)
        self.etiket_kutusu.setVisible(hex_mi)
        self.d_secimi_doldur.setVisible(not hex_mi)

    def _dis_doldur(self, d):
        self.dis.clear()
        self.dis.addItem("bosluk (void)", sema.BOSLUK)
        for m in self.spec["malzemeler"]:
            self.dis.addItem("%s  --  %s" % (m["ad"], m.get("gorunen_ad") or ""), m["ad"])
        i = self.dis.findData(d.get("dolgu_disi"))
        if i >= 0:
            self.dis.setCurrentIndex(i)

    def _hedefler(self):
        secili = self._secili_ad()
        ogeler = [(sema.BOSLUK, "bosluk (void)")]
        for c in self.spec.get("cubuklar", []):
            ogeler.append((c["ad"], "cubuk: %s" % c["ad"]))
        for p in self.spec.get("plakalar", []):
            ogeler.append((p["ad"], "plaka: %s" % p["ad"]))
        for d in self.spec.get("demetler", []):
            if d["ad"] != secili:
                ogeler.append((d["ad"], "kafes: %s" % d["ad"]))
        for m in self.spec["malzemeler"]:
            ogeler.append((m["ad"], "malzeme: %s" % m["ad"]))
        return ogeler

    def _anahtar_doldur(self, d):
        harfler = sorted((d.get("anahtar") or {}).keys())
        self.anahtar_tablo.setRowCount(0)
        for harf in harfler:
            satir = self.anahtar_tablo.rowCount()
            self.anahtar_tablo.insertRow(satir)
            h_oge = QtWidgets.QTableWidgetItem(harf)
            h_oge.setTextAlignment(QtCore.Qt.AlignCenter)
            h_oge.setBackground(harf_rengi(harfler, harf))
            h_oge.setFlags(QtCore.Qt.ItemIsEnabled)
            self.anahtar_tablo.setItem(satir, 0, h_oge)
            kutu = QtWidgets.QComboBox()
            for deger, etiket in self._hedefler():
                kutu.addItem(etiket, deger)
            i = kutu.findData(d["anahtar"][harf])
            if i >= 0:
                kutu.setCurrentIndex(i)
            kutu.currentIndexChanged.connect(self._anahtar_kaydet)
            self.anahtar_tablo.setCellWidget(satir, 1, kutu)
            dugme = QtWidgets.QPushButton("Sec")
            dugme.setCheckable(True)
            dugme.clicked.connect(lambda _c, h=harf: self._firca_sec(h))
            self.anahtar_tablo.setCellWidget(satir, 2, dugme)
        self.anahtar_tablo.resizeColumnsToContents()
        if harfler and self._firca not in harfler:
            self._firca_sec(harfler[0])
        else:
            self._firca_sec(self._firca)

    def _firca_sec(self, harf):
        if harf is None:
            return
        self._firca = harf
        self.firca_etiket.setText("Firca: '%s'" % harf)
        self.hex_izgara.firca_ayarla(harf)
        for i in range(self.anahtar_tablo.rowCount()):
            d = self.anahtar_tablo.cellWidget(i, 2)
            oge = self.anahtar_tablo.item(i, 0)
            if d and oge:
                d.setChecked(oge.text() == harf)

    # ==================================================================
    def _harita_doldur(self, d):
        harfler = sorted((d.get("anahtar") or {}).keys())
        if d.get("tur") == "altigen":
            halka = d.get("halka_sayisi") or 1
            self.hex_izgara.yukle(d.get("harita") or [], halka,
                                  d.get("yonelim", "y"), harfler)
        else:
            self._kare_izgara_doldur(d, harfler)

    def _kare_izgara_doldur(self, d, harfler):
        harita = d.get("harita") or []
        nx, ny = d["boyut"]
        self.izgara.setRowCount(ny)
        self.izgara.setColumnCount(nx)
        self.izgara.setHorizontalHeaderLabels([str(i) for i in range(nx)])
        self.izgara.setVerticalHeaderLabels([str(i) for i in range(ny)])
        varsayilan = harfler[0] if harfler else "."
        for r in range(ny):
            satir = harita[r] if r < len(harita) else ""
            for c in range(nx):
                harf = satir[c] if c < len(satir) else varsayilan
                oge = QtWidgets.QTableWidgetItem(harf)
                oge.setTextAlignment(QtCore.Qt.AlignCenter)
                oge.setBackground(harf_rengi(harfler, harf))
                self.izgara.setItem(r, c, oge)
        for c in range(nx):
            self.izgara.setColumnWidth(c, 26)
        for r in range(ny):
            self.izgara.setRowHeight(r, 24)

    def _ozet_guncelle(self, d):
        if d.get("tur") == "altigen":
            halka = d.get("halka_sayisi") or 1
            gx, gy = altigen.kapsayan_olcu(halka, d["adim"], d.get("yonelim", "y"))
            self.ozet.setText("%.4f x %.4f cm  (%d hucre, %d halka)"
                              % (gx, gy, altigen.toplam_hucre(halka), halka))
        else:
            nx, ny = d["boyut"]
            self.ozet.setText("%.4f x %.4f cm  (%d hucre)"
                              % (d["adim"] * nx, d["adim"] * ny, nx * ny))

    # ==================================================================
    # kare harita
    # ==================================================================
    def _kare_hucre_boya(self, satir, sutun):
        d = self._secili()
        if d is None or self._firca is None:
            return
        harfler = sorted((d.get("anahtar") or {}).keys())
        oge = self.izgara.item(satir, sutun)
        oge.setText(self._firca)
        oge.setBackground(harf_rengi(harfler, self._firca))
        self._kare_harita_kaydet()

    def _secimi_doldur(self):
        d = self._secili()
        if d is None or self._firca is None:
            return
        harfler = sorted((d.get("anahtar") or {}).keys())
        for ix in self.izgara.selectedIndexes():
            oge = self.izgara.item(ix.row(), ix.column())
            oge.setText(self._firca)
            oge.setBackground(harf_rengi(harfler, self._firca))
        self._kare_harita_kaydet()

    def _tumunu_doldur(self):
        d = self._secili()
        if d is None or self._firca is None:
            return
        if d.get("tur") == "altigen":
            self.hex_izgara.tumunu_doldur(self._firca)
            return
        harfler = sorted((d.get("anahtar") or {}).keys())
        for r in range(self.izgara.rowCount()):
            for c in range(self.izgara.columnCount()):
                oge = self.izgara.item(r, c)
                oge.setText(self._firca)
                oge.setBackground(harf_rengi(harfler, self._firca))
        self._kare_harita_kaydet()

    def _halka_doldur(self):
        d = self._secili()
        if d is None or d.get("tur") != "altigen" or self._firca is None:
            return
        halka = d.get("halka_sayisi") or 1
        secenekler = ["%d. halka (yaricap %d, %d hucre)"
                      % (i + 1, halka - 1 - i, u)
                      for i, u in enumerate(altigen.halka_uzunluklari(halka))]
        secim, tamam = QtWidgets.QInputDialog.getItem(
            self, "Halkayi doldur",
            "'%s' fircasiyla doldurulacak halka (distan ice):" % self._firca,
            secenekler, 0, False)
        if tamam and secim:
            self.hex_izgara.halkayi_doldur(secenekler.index(secim), self._firca)

    def _kare_harita_kaydet(self):
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None:
            return
        harita = []
        for r in range(self.izgara.rowCount()):
            satir = ""
            for c in range(self.izgara.columnCount()):
                oge = self.izgara.item(r, c)
                satir += (oge.text() or ".")[0] if oge else "."
            harita.append(satir)
        d["harita"] = harita
        self.bildir()

    def _hex_harita_kaydet(self):
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None:
            return
        d["harita"] = self.hex_izgara.harita_metni()
        self.bildir()

    # ==================================================================
    # ozellik degisiklikleri
    # ==================================================================
    def _kaydet(self, *_):
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None:
            return
        d["adim"] = self.adim.value()
        d["dolgu_disi"] = self.dis.currentData()
        self._ozet_guncelle(d)
        self.bildir()

    def _anahtar_kaydet(self, *_):
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None:
            return
        yeni = {}
        for i in range(self.anahtar_tablo.rowCount()):
            harf = self.anahtar_tablo.item(i, 0).text()
            kutu = self.anahtar_tablo.cellWidget(i, 1)
            yeni[harf] = kutu.currentData()
        d["anahtar"] = yeni
        self.bildir()

    def _tur_degisti(self, *_):
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None:
            return
        yeni_tur = self.tur.currentData()
        if yeni_tur == d.get("tur"):
            return
        harfler = sorted((d.get("anahtar") or {}).keys())
        varsayilan = harfler[0] if harfler else "y"
        d["tur"] = yeni_tur
        if yeni_tur == "altigen":
            halka = d.get("halka_sayisi") or max(2, min(self.nx.value(), 20))
            d["halka_sayisi"] = halka
            d.setdefault("yonelim", "y")
            d["harita"] = altigen.bos_harita(halka, varsayilan)
        else:
            n = max(d.get("boyut", [3, 3])[0], 3)
            d["boyut"] = [n, n]
            d["harita"] = [varsayilan * n for _ in range(n)]
        self.spec_yukle(self.spec)
        self.bildir()

    def _yonelim_degisti(self, *_):
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None:
            return
        d["yonelim"] = self.yonelim.currentData()
        self._harita_doldur(d)
        self._ozet_guncelle(d)
        self.bildir()

    def _boyut_degisti(self, *_):
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None or d.get("tur") == "altigen":
            return
        nx, ny = self.nx.value(), self.ny.value()
        eski = d.get("harita") or []
        harfler = sorted((d.get("anahtar") or {}).keys())
        varsayilan = harfler[0] if harfler else "."
        yeni = []
        for r in range(ny):
            eski_satir = eski[r] if r < len(eski) else ""
            yeni.append("".join(eski_satir[c] if c < len(eski_satir) else varsayilan
                                for c in range(nx)))
        d["boyut"] = [nx, ny]
        d["harita"] = yeni
        self._yukleniyor = True
        try:
            self._harita_doldur(d)
            self._ozet_guncelle(d)
        finally:
            self._yukleniyor = False
        self.bildir()

    def _halka_degisti(self, *_):
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None or d.get("tur") != "altigen":
            return
        harfler = sorted((d.get("anahtar") or {}).keys())
        halka = self.halka.value()
        d["halka_sayisi"] = halka
        d["boyut"] = [halka, halka]
        d["harita"] = altigen.harita_yeniden_boyutlandir(
            d.get("harita"), halka, harfler[0] if harfler else "y")
        self._yukleniyor = True
        try:
            self._harita_doldur(d)
            self._ozet_guncelle(d)
        finally:
            self._yukleniyor = False
        self.bildir()

    # ==================================================================
    def _harf_ekle(self):
        d = self._secili()
        if d is None:
            return
        kullanilan = set((d.get("anahtar") or {}).keys())
        for harf in string.ascii_lowercase:
            if harf not in kullanilan:
                break
        else:
            return
        hedefler = self._hedefler()
        d.setdefault("anahtar", {})[harf] = hedefler[1][0] if len(hedefler) > 1 else sema.BOSLUK
        self._yukleniyor = True
        try:
            self._anahtar_doldur(d)
            self._harita_doldur(d)
        finally:
            self._yukleniyor = False
        self.bildir()

    def _harf_sil(self):
        d = self._secili()
        satir = self.anahtar_tablo.currentRow()
        if d is None or satir < 0:
            return
        harf = self.anahtar_tablo.item(satir, 0).text()
        if len(d.get("anahtar") or {}) <= 1:
            QtWidgets.QMessageBox.information(self, "Silinemez",
                                              "En az bir harf tanimli kalmali.")
            return
        if any(harf in s for s in (d.get("harita") or [])):
            c = QtWidgets.QMessageBox.question(
                self, "Kullanimda",
                "'%s' harfi haritada kullaniliyor. Silinirse o hucreler "
                "gecersiz kalir. Devam edilsin mi?" % harf)
            if c != QtWidgets.QMessageBox.Yes:
                return
        d["anahtar"].pop(harf, None)
        self._yukleniyor = True
        try:
            self._anahtar_doldur(d)
            self._harita_doldur(d)
        finally:
            self._yukleniyor = False
        self.bildir()

    # ==================================================================
    def _benzersiz(self, taban):
        mevcut = {d["ad"] for d in self.spec.get("demetler", [])}
        ad, i = taban, 2
        while ad in mevcut:
            ad = "%s_%d" % (taban, i)
            i += 1
        return ad

    def _yeni(self, tur):
        cubuklar = self.spec.get("cubuklar", [])
        if not cubuklar:
            QtWidgets.QMessageBox.information(
                self, "Once cubuk gerekli",
                "Kafes kurmadan once en az bir cubuk ya da plaka tanimlayin.")
            return
        ad = self._benzersiz("kafes_hex" if tur == "altigen" else "kafes")
        sog = next((m["ad"] for m in self.spec["malzemeler"] if m["ad"] == "su"),
                   self.spec["malzemeler"][0]["ad"] if self.spec["malzemeler"] else sema.BOSLUK)
        if tur == "altigen":
            halka = 5
            yeni = sema.demet_altigen(ad, 1.0, halka, altigen.bos_harita(halka, "y"),
                                      {"y": cubuklar[0]["ad"]}, sog)
        else:
            n = 5
            yeni = sema.demet(ad, 1.26, [n, n], ["y" * n] * n,
                              {"y": cubuklar[0]["ad"]}, sog)
        self.spec.setdefault("demetler", []).append(yeni)
        self.spec_yukle(self.spec)
        for i in range(self.liste.count()):
            if self.liste.item(i).data(QtCore.Qt.UserRole) == ad:
                self.liste.setCurrentRow(i)
        self.bildir()

    def _kopyala(self):
        d = self._secili()
        if d is None:
            return
        y = copy.deepcopy(d)
        y["ad"] = self._benzersiz(d["ad"])
        self.spec["demetler"].append(y)
        self.spec_yukle(self.spec)
        self.bildir()

    def _sil(self):
        ad = self._secili_ad()
        if ad is None:
            return
        self.spec["demetler"] = [d for d in self.spec["demetler"] if d["ad"] != ad]
        self.spec_yukle(self.spec)
        self.bildir()

    def _ad_degisti(self):
        d = self._secili()
        if d is None:
            return
        yeni = self.ad.text().strip()
        if not yeni or yeni == d["ad"]:
            return
        eski = d["ad"]
        d["ad"] = yeni
        for b in self.spec.get("demetler", []):
            for h, hedef in (b.get("anahtar") or {}).items():
                if hedef == eski:
                    b["anahtar"][h] = yeni
        kor = self.spec["kor"]
        if kor.get("demet") == eski:
            kor["demet"] = yeni
        for h, hedef in (kor.get("anahtar") or {}).items():
            if hedef == eski:
                kor["anahtar"][h] = yeni
        self.spec_yukle(self.spec)
        self.bildir()
