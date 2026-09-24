# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_cubuk.py  --  Yakit cubuklari ve plaka elemanlari
================================================================================
 Sol tarafta oge listesi, sag tarafta secili ogenin editoru.
 Silindirik cubuk : es merkezli radyal bolgeler (son bolge "disarisi")
 Plaka eleman     : MTR tipi duz plaka istifi
================================================================================
"""

import copy

from PySide6 import QtCore, QtWidgets

from cekirdek import sema
from arayuz.ortak import SekmeTabani, baslik, ipucu, sayi, tamsayi


def _malzeme_kutusu(spec, secili=None, bosluk_dahil=True):
    """Malzeme secme acilir kutusu."""
    k = QtWidgets.QComboBox()
    if bosluk_dahil:
        k.addItem("bosluk (void)", sema.BOSLUK)
    for m in spec["malzemeler"]:
        k.addItem("%s  --  %s" % (m["ad"], m.get("gorunen_ad") or ""), m["ad"])
    if secili is not None:
        i = k.findData(secili)
        if i >= 0:
            k.setCurrentIndex(i)
    return k


class CubukSekmesi(SekmeTabani):
    """Cubuk ve plaka tanimlari."""

    KONU = "cubuk"

    def __init__(self, parent=None):
        super().__init__(parent)

        # --- sol: oge listesi ---
        self.liste = QtWidgets.QListWidget()
        self.liste.currentRowChanged.connect(self._secim_degisti)
        d_cubuk = QtWidgets.QPushButton("+ Cubuk")
        d_plaka = QtWidgets.QPushButton("+ Plaka")
        d_kopya = QtWidgets.QPushButton("Kopyala")
        d_sil = QtWidgets.QPushButton("Sil")
        d_cubuk.clicked.connect(self._cubuk_ekle)
        d_plaka.clicked.connect(self._plaka_ekle)
        d_kopya.clicked.connect(self._kopyala)
        d_sil.clicked.connect(self._sil)
        sol_dugme = QtWidgets.QGridLayout()
        sol_dugme.addWidget(d_cubuk, 0, 0); sol_dugme.addWidget(d_plaka, 0, 1)
        sol_dugme.addWidget(d_kopya, 1, 0); sol_dugme.addWidget(d_sil, 1, 1)
        sol = QtWidgets.QWidget()
        sol_d = QtWidgets.QVBoxLayout(sol)
        sol_d.setContentsMargins(0, 0, 0, 0)
        sol_d.addWidget(baslik("Ogeler"))
        sol_d.addWidget(self.liste, 1)
        sol_d.addLayout(sol_dugme)

        # --- sag: editor yigini ---
        self.yigin = QtWidgets.QStackedWidget()
        self.yigin.addWidget(self._bos_sayfa())
        self.cubuk_sayfa = self._cubuk_sayfa()
        self.plaka_sayfa = self._plaka_sayfa()
        self.yigin.addWidget(self.cubuk_sayfa)
        self.yigin.addWidget(self.plaka_sayfa)

        bolucu = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        bolucu.addWidget(sol)
        bolucu.addWidget(self.yigin)
        bolucu.setStretchFactor(0, 0)
        bolucu.setStretchFactor(1, 1)
        bolucu.setSizes([200, 500])

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(bolucu)

    # ------------------------------------------------------------------
    # sayfalar
    # ------------------------------------------------------------------
    def _bos_sayfa(self):
        w = QtWidgets.QWidget()
        d = QtWidgets.QVBoxLayout(w)
        d.addStretch(1)
        e = QtWidgets.QLabel("Soldan bir oge secin ya da yeni ekleyin")
        e.setAlignment(QtCore.Qt.AlignCenter)
        e.setStyleSheet("color: palette(mid);")
        d.addWidget(e)
        d.addStretch(1)
        return w

    def _cubuk_sayfa(self):
        w = QtWidgets.QWidget()
        self.c_ad = QtWidgets.QLineEdit()
        self.c_ad.editingFinished.connect(self._cubuk_ad_degisti)

        # --- kontrol cubugu alanlari ---
        self.c_tur = QtWidgets.QComboBox()
        self.c_tur.addItem("Silindirik (sabit)", "silindirik")
        self.c_tur.addItem("Kontrol cubugu (eksenel hareketli)", "kontrol")
        self.c_emici = QtWidgets.QComboBox()
        self.c_izleyici = QtWidgets.QComboBox()
        self.c_daldirma = sayi(0.0, 2, 0.0, 100.0, 5.0, "%")
        self.c_daldirma_kaydirici = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.c_daldirma_kaydirici.setRange(0, 1000)
        self.c_uc_etiket = QtWidgets.QLabel("-")
        self.c_kontrol_etiketleri = {}

        self.c_tablo = QtWidgets.QTableWidget(0, 3)
        self.c_tablo.setHorizontalHeaderLabels(["Yaricap r [cm]", "Malzeme", "Aciklama"])
        self.c_tablo.horizontalHeader().setStretchLastSection(True)
        self.c_tablo.verticalHeader().setVisible(False)

        d_ekle = QtWidgets.QPushButton("Bolge ekle")
        d_sil = QtWidgets.QPushButton("Bolge sil")
        d_yukari = QtWidgets.QPushButton("Yukari")
        d_asagi = QtWidgets.QPushButton("Asagi")
        d_ekle.clicked.connect(self._bolge_ekle)
        d_sil.clicked.connect(self._bolge_sil)
        d_yukari.clicked.connect(lambda: self._bolge_tasi(-1))
        d_asagi.clicked.connect(lambda: self._bolge_tasi(+1))
        dugme = QtWidgets.QHBoxLayout()
        for b in (d_ekle, d_sil, d_yukari, d_asagi):
            dugme.addWidget(b)
        dugme.addStretch(1)

        form = QtWidgets.QFormLayout()
        form.addRow("Ad:", self.c_ad)
        form.addRow("Tur:", self.c_tur)
        for etiket, alan, anahtar in (
                ("Emici bolge:", self.c_emici, "emici"),
                ("Izleyici malzeme:", self.c_izleyici, "izleyici")):
            e = QtWidgets.QLabel(etiket)
            self.c_kontrol_etiketleri[anahtar] = e
            form.addRow(e, alan)
        dald = QtWidgets.QWidget()
        dd = QtWidgets.QHBoxLayout(dald)
        dd.setContentsMargins(0, 0, 0, 0)
        dd.addWidget(self.c_daldirma)
        dd.addWidget(self.c_daldirma_kaydirici, 1)
        e = QtWidgets.QLabel("Daldirma:")
        self.c_kontrol_etiketleri["daldirma"] = e
        form.addRow(e, dald)
        e = QtWidgets.QLabel("Uc konumu:")
        self.c_kontrol_etiketleri["uc"] = e
        form.addRow(e, self.c_uc_etiket)

        self.c_kontrol_not = ipucu(
            "Kontrol cubugu YUKARIDAN daldirilir. %0 = tamamen cekilmis "
            "(emici kor icinde yok), %100 = tam dalmis. Emici bolge, cubuk "
            "ucunun ALTINDA izleyici malzemeyle doldurulur. 3B model gerektirir: "
            "kor yuksekligi tanimli olmali.\n"
            "Kritik cubuk konumunu bulmak icin 7. Analiz sekmesinde "
            "'Kritik arama' + 'Kontrol cubugu daldirma orani' kullanin.")

        d = QtWidgets.QVBoxLayout(w)
        d.addWidget(baslik("Yakit / kontrol cubugu"))
        d.addLayout(form)
        d.addWidget(self.c_kontrol_not)
        d.addWidget(ipucu(
            "Bolgeler ICTEN DISA dogru siralanir ve yaricaplar artan olmalidir. "
            "EN SON bolgenin yaricapi bos birakilir -- o bolge 'disarisi'dir ve "
            "hucrenin kalanini doldurur (genellikle sogutucu)."))
        d.addWidget(self.c_tablo, 1)
        d.addLayout(dugme)

        self.c_tur.currentIndexChanged.connect(self._cubuk_tur_degisti)
        self.c_emici.currentIndexChanged.connect(self._cubuk_kaydet)
        self.c_izleyici.currentIndexChanged.connect(self._cubuk_kaydet)
        self.c_daldirma.valueChanged.connect(self._daldirma_degisti)
        self.c_daldirma_kaydirici.valueChanged.connect(self._kaydirici_degisti)
        return w

    def _plaka_sayfa(self):
        w = QtWidgets.QWidget()
        self.p_ad = QtWidgets.QLineEdit()
        self.p_ad.editingFinished.connect(self._plaka_ad_degisti)
        self.p_sayi = tamsayi(23, 1, 500, 1, "plaka")
        self.p_et = sayi(0.051, 5, 0.0001, 10.0, 0.001, "cm")
        self.p_zarf = sayi(0.038, 5, 0.0001, 10.0, 0.001, "cm")
        self.p_kanal = sayi(0.200, 5, 0.0001, 10.0, 0.001, "cm")
        self.p_genislik = sayi(6.30, 4, 0.01, 100.0, 0.1, "cm")
        self.p_yan = sayi(0.475, 4, 0.0, 10.0, 0.01, "cm")
        self.p_et_mal = QtWidgets.QComboBox()
        self.p_zarf_mal = QtWidgets.QComboBox()
        self.p_sog = QtWidgets.QComboBox()
        self.p_yan_mal = QtWidgets.QComboBox()
        self.p_ozet = QtWidgets.QLabel("-")

        form = QtWidgets.QFormLayout()
        form.addRow("Ad:", self.p_ad)
        form.addRow("Plaka sayisi:", self.p_sayi)
        form.addRow("Yakit eti kalinligi:", self.p_et)
        form.addRow("Zarf kalinligi (her yuz):", self.p_zarf)
        form.addRow("Kanal kalinligi:", self.p_kanal)
        form.addRow("Aktif genislik (y):", self.p_genislik)
        form.addRow("Yan levha kalinligi:", self.p_yan)
        form.addRow("Yakit eti malzemesi:", self.p_et_mal)
        form.addRow("Zarf malzemesi:", self.p_zarf_mal)
        form.addRow("Sogutucu:", self.p_sog)
        form.addRow("Yan levha malzemesi:", self.p_yan_mal)
        form.addRow("Eleman kesiti:", self.p_ozet)

        for alan in (self.p_sayi, self.p_et, self.p_zarf, self.p_kanal,
                     self.p_genislik, self.p_yan):
            alan.valueChanged.connect(self._plaka_kaydet)
        for kutu in (self.p_et_mal, self.p_zarf_mal, self.p_sog, self.p_yan_mal):
            kutu.currentIndexChanged.connect(self._plaka_kaydet)

        d = QtWidgets.QVBoxLayout(w)
        d.addWidget(baslik("MTR tipi plaka yakit elemani"))
        d.addWidget(ipucu(
            "Kesit x yonunde su sirayla kurulur:  kanal [zarf | yakit eti | zarf] "
            "kanal [zarf | et | zarf] ...  ve sonda bir kanal daha. "
            "Yan levhalar y yonunde aktif bolgenin altinda ve ustunde yer alir."))
        d.addLayout(form)
        d.addStretch(1)
        return w

    # ------------------------------------------------------------------
    # doldurma
    # ------------------------------------------------------------------
    def doldur(self):
        self.liste.clear()
        for c in self.spec.get("cubuklar", []):
            simge = "[kontrol]" if c.get("tur") == "kontrol" else "[cubuk]  "
            oge = QtWidgets.QListWidgetItem("%s %s" % (simge, c["ad"]))
            oge.setData(QtCore.Qt.UserRole, ("cubuk", c["ad"]))
            self.liste.addItem(oge)
        for p in self.spec.get("plakalar", []):
            oge = QtWidgets.QListWidgetItem("[plaka]  %s" % p["ad"])
            oge.setData(QtCore.Qt.UserRole, ("plaka", p["ad"]))
            self.liste.addItem(oge)
        if self.liste.count():
            self.liste.setCurrentRow(0)
        else:
            self.yigin.setCurrentIndex(0)

    def _secili(self):
        oge = self.liste.currentItem()
        return oge.data(QtCore.Qt.UserRole) if oge else (None, None)

    def _secim_degisti(self, _satir):
        tur, ad = self._secili()
        eski = self._yukleniyor
        self._yukleniyor = True
        try:
            if tur == "cubuk":
                self._cubuk_doldur(sema.cubuk_bul(self.spec, ad))
                self.yigin.setCurrentWidget(self.cubuk_sayfa)
            elif tur == "plaka":
                self._plaka_doldur(sema.plaka_bul(self.spec, ad))
                self.yigin.setCurrentWidget(self.plaka_sayfa)
            else:
                self.yigin.setCurrentIndex(0)
        finally:
            self._yukleniyor = eski

    # ------------------------------------------------------------------
    # cubuk
    # ------------------------------------------------------------------
    def _cubuk_doldur(self, c):
        if c is None:
            return
        self.c_ad.setText(c["ad"])
        i = self.c_tur.findData(c.get("tur", "silindirik"))
        self.c_tur.setCurrentIndex(max(i, 0))
        self.c_emici.clear()
        for j, b in enumerate(c["bolgeler"]):
            self.c_emici.addItem("%d -- %s" % (j, b.get("malzeme") or "bosluk"), j)
        j = self.c_emici.findData(c.get("emici_bolge", 0))
        if j >= 0:
            self.c_emici.setCurrentIndex(j)
        self.c_izleyici.clear()
        self.c_izleyici.addItem("bosluk (void)", sema.BOSLUK)
        for m in self.spec["malzemeler"]:
            self.c_izleyici.addItem("%s  --  %s" % (m["ad"], m.get("gorunen_ad") or ""),
                                    m["ad"])
        j = self.c_izleyici.findData(c.get("izleyici_malzeme"))
        if j >= 0:
            self.c_izleyici.setCurrentIndex(j)
        dd = float(c.get("daldirma") or 0.0)
        self.c_daldirma.setValue(dd)
        self.c_daldirma_kaydirici.setValue(int(round(dd * 10)))
        self._kontrol_gorunurluk()
        self._uc_guncelle()
        self.c_tablo.setRowCount(0)
        for i, b in enumerate(c["bolgeler"]):
            self._bolge_satiri(i, b, son=(i == len(c["bolgeler"]) - 1))

    def _bolge_satiri(self, satir, bolge, son):
        self.c_tablo.insertRow(satir)
        if son:
            oge = QtWidgets.QTableWidgetItem("(disarisi)")
            oge.setFlags(QtCore.Qt.ItemIsEnabled)
            self.c_tablo.setItem(satir, 0, oge)
        else:
            w = sayi(bolge.get("r") or 0.0, 5, 0.00001, 1000.0, 0.01, "cm")
            w.valueChanged.connect(self._cubuk_kaydet)
            self.c_tablo.setCellWidget(satir, 0, w)
        k = _malzeme_kutusu(self.spec, bolge.get("malzeme"))
        k.currentIndexChanged.connect(self._cubuk_kaydet)
        self.c_tablo.setCellWidget(satir, 1, k)
        aciklama = "disarisi -- hucrenin kalanini doldurur" if son else ""
        self.c_tablo.setItem(satir, 2, QtWidgets.QTableWidgetItem(aciklama))
        self.c_tablo.resizeColumnsToContents()

    def _kontrol_gorunurluk(self):
        kontrol = self.c_tur.currentData() == "kontrol"
        for w in list(self.c_kontrol_etiketleri.values()) + [
                self.c_emici, self.c_izleyici, self.c_daldirma,
                self.c_daldirma_kaydirici, self.c_uc_etiket, self.c_kontrol_not]:
            w.setVisible(kontrol)

    def _uc_guncelle(self):
        """Daldirma oranindan uc konumunu hesaplayip gosterir."""
        h = (self.spec or {}).get("kor", {}).get("yukseklik")
        if not h:
            self.c_uc_etiket.setText("model 2B -- kor yuksekligi tanimli degil")
            self.c_uc_etiket.setStyleSheet("color: palette(mid);")
            return
        z = h / 2.0 - (self.c_daldirma.value() / 100.0) * h
        self.c_uc_etiket.setText("z = %+.2f cm   (kor: %+.1f .. %+.1f cm)"
                                 % (z, -h / 2.0, h / 2.0))
        self.c_uc_etiket.setStyleSheet("")

    def _cubuk_tur_degisti(self, *_):
        if self._yukleniyor:
            return
        tur, ad = self._secili()
        if tur != "cubuk":
            return
        c = sema.cubuk_bul(self.spec, ad)
        yeni_tur = self.c_tur.currentData()
        c["tur"] = yeni_tur
        if yeni_tur == "kontrol":
            c.setdefault("emici_bolge", 0)
            c.setdefault("daldirma", 0.0)
            if not c.get("izleyici_malzeme"):
                adlar = [m["ad"] for m in self.spec["malzemeler"]]
                c["izleyici_malzeme"] = "su" if "su" in adlar else (
                    adlar[0] if adlar else sema.BOSLUK)
        self.spec_yukle(self.spec)
        self._sec(("cubuk", ad))
        self.bildir()

    def _daldirma_degisti(self, *_):
        if self._yukleniyor:
            return
        self._yukleniyor = True
        try:
            self.c_daldirma_kaydirici.setValue(int(round(self.c_daldirma.value() * 10)))
        finally:
            self._yukleniyor = False
        self._uc_guncelle()
        self._cubuk_kaydet()

    def _kaydirici_degisti(self, deger):
        if self._yukleniyor:
            return
        self._yukleniyor = True
        try:
            self.c_daldirma.setValue(deger / 10.0)
        finally:
            self._yukleniyor = False
        self._uc_guncelle()
        self._cubuk_kaydet()

    def _cubuk_kaydet(self, *_):
        if self._yukleniyor:
            return
        tur, ad = self._secili()
        if tur != "cubuk":
            return
        c = sema.cubuk_bul(self.spec, ad)
        bolgeler = []
        n = self.c_tablo.rowCount()
        for i in range(n):
            w = self.c_tablo.cellWidget(i, 0)
            r = None if (i == n - 1 or w is None) else w.value()
            k = self.c_tablo.cellWidget(i, 1)
            bolgeler.append({"r": r, "malzeme": k.currentData() if k else None})
        c["bolgeler"] = bolgeler
        if c.get("tur") == "kontrol":
            c["emici_bolge"] = self.c_emici.currentData() or 0
            c["izleyici_malzeme"] = self.c_izleyici.currentData()
            c["daldirma"] = self.c_daldirma.value()
        self.bildir()

    def _cubuk_ad_degisti(self):
        tur, ad = self._secili()
        if tur != "cubuk":
            return
        yeni = self.c_ad.text().strip()
        if not yeni or yeni == ad:
            return
        sema.cubuk_bul(self.spec, ad)["ad"] = yeni
        self._referans_guncelle(ad, yeni)
        self.spec_yukle(self.spec)
        self.bildir()

    def _bolge_ekle(self):
        tur, ad = self._secili()
        if tur != "cubuk":
            return
        c = sema.cubuk_bul(self.spec, ad)
        yaricaplar = [b["r"] for b in c["bolgeler"] if b.get("r")]
        yeni_r = (max(yaricaplar) * 1.1) if yaricaplar else 0.4
        c["bolgeler"].insert(len(c["bolgeler"]) - 1,
                             {"r": round(yeni_r, 5), "malzeme": sema.BOSLUK})
        self._yukleniyor = True
        try:
            self._cubuk_doldur(c)
        finally:
            self._yukleniyor = False
        self.bildir()

    def _bolge_sil(self):
        tur, ad = self._secili()
        if tur != "cubuk":
            return
        c = sema.cubuk_bul(self.spec, ad)
        satir = self.c_tablo.currentRow()
        if satir < 0 or satir == len(c["bolgeler"]) - 1:
            QtWidgets.QMessageBox.information(
                self, "Silinemez", "Son bolge ('disarisi') silinemez.")
            return
        if len(c["bolgeler"]) <= 2:
            QtWidgets.QMessageBox.information(
                self, "Silinemez", "En az iki bolge gerekir.")
            return
        c["bolgeler"].pop(satir)
        self._yukleniyor = True
        try:
            self._cubuk_doldur(c)
        finally:
            self._yukleniyor = False
        self.bildir()

    def _bolge_tasi(self, yon):
        tur, ad = self._secili()
        if tur != "cubuk":
            return
        c = sema.cubuk_bul(self.spec, ad)
        i = self.c_tablo.currentRow()
        j = i + yon
        son = len(c["bolgeler"]) - 1
        if i < 0 or i == son or j < 0 or j >= son:
            return
        c["bolgeler"][i], c["bolgeler"][j] = c["bolgeler"][j], c["bolgeler"][i]
        self._yukleniyor = True
        try:
            self._cubuk_doldur(c)
        finally:
            self._yukleniyor = False
        self.c_tablo.setCurrentCell(j, 0)
        self.bildir()

    # ------------------------------------------------------------------
    # plaka
    # ------------------------------------------------------------------
    def _plaka_doldur(self, p):
        if p is None:
            return
        self.p_ad.setText(p["ad"])
        self.p_sayi.setValue(p["plaka_sayisi"])
        self.p_et.setValue(p["et_kalinlik"])
        self.p_zarf.setValue(p["zarf_kalinlik"])
        self.p_kanal.setValue(p["kanal_kalinlik"])
        self.p_genislik.setValue(p["plaka_genislik"])
        self.p_yan.setValue(p.get("yan_levha_kalinlik") or 0.0)
        for kutu, anahtar, bosluk in ((self.p_et_mal, "et_malzeme", False),
                                      (self.p_zarf_mal, "zarf_malzeme", False),
                                      (self.p_sog, "sogutucu", False),
                                      (self.p_yan_mal, "yan_levha_malzeme", True)):
            kutu.clear()
            if bosluk:
                kutu.addItem("(zarf ile ayni)", None)
            for m in self.spec["malzemeler"]:
                kutu.addItem("%s  --  %s" % (m["ad"], m.get("gorunen_ad") or ""), m["ad"])
            i = kutu.findData(p.get(anahtar))
            if i >= 0:
                kutu.setCurrentIndex(i)
        self._plaka_ozet(p)

    def _plaka_ozet(self, p):
        tx = p["plaka_sayisi"] * (2 * p["zarf_kalinlik"] + p["et_kalinlik"]) \
            + (p["plaka_sayisi"] + 1) * p["kanal_kalinlik"]
        ty = p["plaka_genislik"] + 2 * (p.get("yan_levha_kalinlik") or 0.0)
        self.p_ozet.setText("%.4f x %.4f cm" % (tx, ty))

    def _plaka_kaydet(self, *_):
        if self._yukleniyor:
            return
        tur, ad = self._secili()
        if tur != "plaka":
            return
        p = sema.plaka_bul(self.spec, ad)
        p["plaka_sayisi"] = self.p_sayi.value()
        p["et_kalinlik"] = self.p_et.value()
        p["zarf_kalinlik"] = self.p_zarf.value()
        p["kanal_kalinlik"] = self.p_kanal.value()
        p["plaka_genislik"] = self.p_genislik.value()
        p["yan_levha_kalinlik"] = self.p_yan.value()
        p["et_malzeme"] = self.p_et_mal.currentData()
        p["zarf_malzeme"] = self.p_zarf_mal.currentData()
        p["sogutucu"] = self.p_sog.currentData()
        p["yan_levha_malzeme"] = self.p_yan_mal.currentData()
        self._plaka_ozet(p)
        self.bildir()

    def _plaka_ad_degisti(self):
        tur, ad = self._secili()
        if tur != "plaka":
            return
        yeni = self.p_ad.text().strip()
        if not yeni or yeni == ad:
            return
        sema.plaka_bul(self.spec, ad)["ad"] = yeni
        self._referans_guncelle(ad, yeni)
        self.spec_yukle(self.spec)
        self.bildir()

    # ------------------------------------------------------------------
    # liste islemleri
    # ------------------------------------------------------------------
    def _benzersiz(self, taban):
        mevcut = {c["ad"] for c in self.spec.get("cubuklar", [])} | \
                 {p["ad"] for p in self.spec.get("plakalar", [])}
        ad, i = taban, 2
        while ad in mevcut:
            ad = "%s_%d" % (taban, i)
            i += 1
        return ad

    def _referans_guncelle(self, eski, yeni):
        """Cubuk/plaka adi degistiginde demet ve kor referanslarini gunceller."""
        for d in self.spec.get("demetler", []):
            for h, hedef in (d.get("anahtar") or {}).items():
                if hedef == eski:
                    d["anahtar"][h] = yeni
        kor = self.spec["kor"]
        for anahtar in ("cubuk", "plaka", "demet"):
            if kor.get(anahtar) == eski:
                kor[anahtar] = yeni
        for h, hedef in (kor.get("anahtar") or {}).items():
            if hedef == eski:
                kor["anahtar"][h] = yeni

    def _ilk_malzeme(self, tercih=None):
        adlar = [m["ad"] for m in self.spec["malzemeler"]]
        if tercih and tercih in adlar:
            return tercih
        return adlar[0] if adlar else sema.BOSLUK

    def _cubuk_ekle(self):
        ad = self._benzersiz("cubuk")
        m = self._ilk_malzeme()
        self.spec.setdefault("cubuklar", []).append(
            sema.cubuk(ad, [sema.bolge(0.40, m), sema.bolge(0.46, sema.BOSLUK),
                            sema.bolge(None, self._ilk_malzeme("su"))]))
        self.spec_yukle(self.spec)
        self._sec(("cubuk", ad))
        self.bildir()

    def _plaka_ekle(self):
        ad = self._benzersiz("plaka")
        m = self._ilk_malzeme()
        self.spec.setdefault("plakalar", []).append(
            sema.plaka(ad, 23, 0.051, 0.038, 0.200, 6.30,
                       m, self._ilk_malzeme("al6061"), self._ilk_malzeme("su"),
                       yan_levha_kalinlik=0.475))
        self.spec_yukle(self.spec)
        self._sec(("plaka", ad))
        self.bildir()

    def _sec(self, anahtar):
        for i in range(self.liste.count()):
            if self.liste.item(i).data(QtCore.Qt.UserRole) == anahtar:
                self.liste.setCurrentRow(i)
                return

    def _kopyala(self):
        tur, ad = self._secili()
        if tur == "cubuk":
            y = copy.deepcopy(sema.cubuk_bul(self.spec, ad))
            y["ad"] = self._benzersiz(ad)
            self.spec["cubuklar"].append(y)
        elif tur == "plaka":
            y = copy.deepcopy(sema.plaka_bul(self.spec, ad))
            y["ad"] = self._benzersiz(ad)
            self.spec["plakalar"].append(y)
        else:
            return
        self.spec_yukle(self.spec)
        self._sec((tur, y["ad"]))
        self.bildir()

    def _sil(self):
        tur, ad = self._secili()
        if tur is None:
            return
        liste = self.spec["cubuklar"] if tur == "cubuk" else self.spec["plakalar"]
        for i, o in enumerate(liste):
            if o["ad"] == ad:
                liste.pop(i)
                break
        self.spec_yukle(self.spec)
        self.bildir()
