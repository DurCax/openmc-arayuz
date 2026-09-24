# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_malzeme.py  --  Malzeme tanimlari
================================================================================
 Hazir kutuphaneden ekleme (malzeme_kutup.py) ve elle bilesim duzenleme.
 Arayuzun Python'a gore en cok deger kattigi yer burasidir: dogrulanmis
 bilesimler, sicakliga bagli yogunluk ve otomatik S(a,b) eklemesi.
================================================================================
"""

import copy

from PySide6 import QtCore, QtWidgets

from cekirdek import malzeme_kutup as mk
from cekirdek import sema
from arayuz.ortak import RenkDugmesi, SekmeTabani, baslik, ipucu, sayi, tamsayi

# Kutuphane fonksiyonlarinin kabul ettigi, arayuzden sorulacak parametreler
KUTUP_PARAM = {
    "uo2":      [("zenginlik", "U235 agirlik %", 3.2, 0.01, 100.0)],
    "un":       [("zenginlik", "U235 agirlik %", 19.75, 0.01, 100.0)],
    "u10mo":    [("zenginlik", "U235 agirlik %", 19.75, 0.01, 100.0)],
    "mox":      [("pu_orani", "Pu agirlik %", 7.0, 0.01, 100.0)],
    "u3si2_al": [("u_yukleme", "U yuklemesi [gU/cm3]", 4.8, 0.1, 10.0),
                 ("zenginlik", "U235 agirlik %", 19.75, 0.01, 100.0)],
    "su":       [("sicaklik", "Sicaklik [K]", 293.6, 273.0, 623.0),
                 ("bor_ppm", "Cozunmus bor [ppm]", 0.0, 0.0, 5000.0)],
    "lbe":      [("sicaklik", "Sicaklik [K]", 723.0, 400.0, 1300.0)],
    "sodyum":   [("sicaklik", "Sicaklik [K]", 673.0, 371.0, 1200.0)],
    "agir_su":  [("saflik", "D2O mol %", 99.75, 50.0, 100.0)],
    "b4c":      [("b10_zenginlik", "B10 atom % (0 = dogal)", 0.0, 0.0, 100.0)],
}


class BilesimModeli(QtCore.QAbstractTableModel):
    """Malzeme bilesim satirlari icin basit tablo modeli."""

    BASLIKLAR = ["Tur", "Isim", "Miktar", "Birim", "Zenginlik %"]

    def __init__(self, bilesim, parent=None):
        super().__init__(parent)
        self.bilesim = copy.deepcopy(bilesim or [])

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.bilesim)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self.BASLIKLAR)

    def headerData(self, bolum, yon, rol=QtCore.Qt.DisplayRole):
        if rol == QtCore.Qt.DisplayRole and yon == QtCore.Qt.Horizontal:
            return self.BASLIKLAR[bolum]
        return None

    def data(self, ix, rol=QtCore.Qt.DisplayRole):
        if not ix.isValid() or rol not in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            return None
        b = self.bilesim[ix.row()]
        s = ix.column()
        if s == 0:
            return b.get("tur", "element")
        if s == 1:
            return b.get("isim", "")
        if s == 2:
            return b.get("miktar", 0.0)
        if s == 3:
            return b.get("birim", "ao")
        if s == 4:
            z = b.get("zenginlik")
            return "" if z is None else z
        return None

    def setData(self, ix, deger, rol=QtCore.Qt.EditRole):
        if rol != QtCore.Qt.EditRole or not ix.isValid():
            return False
        b = self.bilesim[ix.row()]
        s = ix.column()
        try:
            if s == 0:
                b["tur"] = str(deger).strip() or "element"
            elif s == 1:
                b["isim"] = str(deger).strip()
            elif s == 2:
                b["miktar"] = float(deger)
            elif s == 3:
                b["birim"] = str(deger).strip() or "ao"
            elif s == 4:
                metin = str(deger).strip()
                if metin == "":
                    b.pop("zenginlik", None)
                else:
                    b["zenginlik"] = float(metin)
        except ValueError:
            return False
        self.dataChanged.emit(ix, ix)
        return True

    def flags(self, ix):
        return (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
                | QtCore.Qt.ItemIsEditable)

    def satir_ekle(self):
        self.beginInsertRows(QtCore.QModelIndex(), len(self.bilesim), len(self.bilesim))
        self.bilesim.append({"tur": "element", "isim": "", "miktar": 1.0, "birim": "ao"})
        self.endInsertRows()

    def satir_sil(self, satir):
        if 0 <= satir < len(self.bilesim):
            self.beginRemoveRows(QtCore.QModelIndex(), satir, satir)
            self.bilesim.pop(satir)
            self.endRemoveRows()


class MalzemeDiyalog(QtWidgets.QDialog):
    """Tek bir malzemeyi duzenleme penceresi."""

    def __init__(self, malzeme, mevcut_adlar, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Malzeme duzenle")
        self.resize(620, 520)
        self._mevcut = set(mevcut_adlar) - {malzeme["ad"]}

        self.ad = QtWidgets.QLineEdit(malzeme["ad"])
        self.gorunen = QtWidgets.QLineEdit(malzeme.get("gorunen_ad") or malzeme["ad"])
        self.yogunluk = sayi(malzeme["yogunluk"]["deger"] or 0.0, 6, 0.0, 1e4, 0.1)
        self.birim = QtWidgets.QComboBox()
        self.birim.addItems(["g/cm3", "atom/b-cm", "kg/m3"])
        self.birim.setCurrentText(malzeme["yogunluk"].get("birim", "g/cm3"))
        self.sicaklik = sayi(malzeme.get("sicaklik") or 293.6, 2, 0.0, 5000.0, 10.0, "K")
        self.sab = QtWidgets.QLineEdit(", ".join(malzeme.get("sab") or []))
        self.sab.setPlaceholderText("orn. c_H_in_H2O, c_Graphite  (bos birakilabilir)")
        self.renk = RenkDugmesi(malzeme.get("renk") or (170, 170, 170))

        form = QtWidgets.QFormLayout()
        form.addRow("Ad (benzersiz):", self.ad)
        form.addRow("Gorunen ad:", self.gorunen)
        yog = QtWidgets.QHBoxLayout()
        yog.addWidget(self.yogunluk)
        yog.addWidget(self.birim)
        yog.addStretch(1)
        form.addRow("Yogunluk:", yog)
        form.addRow("Sicaklik:", self.sicaklik)
        form.addRow("S(a,b):", self.sab)
        form.addRow("Renk:", self.renk)

        self.model = BilesimModeli(malzeme.get("bilesim"))
        self.tablo = QtWidgets.QTableView()
        self.tablo.setModel(self.model)
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        ekle = QtWidgets.QPushButton("Satir ekle")
        sil = QtWidgets.QPushButton("Satir sil")
        ekle.clicked.connect(self.model.satir_ekle)
        sil.clicked.connect(self._satir_sil)
        dugmeler = QtWidgets.QHBoxLayout()
        dugmeler.addWidget(ekle)
        dugmeler.addWidget(sil)
        dugmeler.addStretch(1)

        kutu = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        kutu.accepted.connect(self._onayla)
        kutu.rejected.connect(self.reject)

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addLayout(form)
        duzen.addWidget(baslik("Bilesim"))
        duzen.addWidget(ipucu(
            "Tur: 'element' (dogal bollukla acilir) ya da 'nuklid'. "
            "Birim: 'ao' atom orani, 'wo' agirlik orani. "
            "Zenginlik yalnizca element satirlarinda anlamlidir."))
        duzen.addWidget(self.tablo, 1)
        duzen.addLayout(dugmeler)
        duzen.addWidget(kutu)

    def _satir_sil(self):
        ix = self.tablo.currentIndex()
        if ix.isValid():
            self.model.satir_sil(ix.row())

    def _onayla(self):
        ad = self.ad.text().strip()
        if not ad:
            QtWidgets.QMessageBox.warning(self, "Eksik", "Malzeme adi bos olamaz.")
            return
        if ad in self._mevcut:
            QtWidgets.QMessageBox.warning(self, "Cakisma",
                                          "'%s' adinda baska bir malzeme var." % ad)
            return
        if ad == sema.BOSLUK:
            QtWidgets.QMessageBox.warning(
                self, "Ayrilmis ad",
                "'%s' ayrilmis bir addir (void anlamina gelir)." % sema.BOSLUK)
            return
        if not self.model.bilesim:
            QtWidgets.QMessageBox.warning(self, "Eksik", "Bilesim bos olamaz.")
            return
        self.accept()

    def sonuc(self):
        sab = [s.strip() for s in self.sab.text().split(",") if s.strip()]
        return {
            "ad": self.ad.text().strip(),
            "gorunen_ad": self.gorunen.text().strip() or self.ad.text().strip(),
            "yogunluk": {"birim": self.birim.currentText(), "deger": self.yogunluk.value()},
            "sicaklik": self.sicaklik.value(),
            "bilesim": copy.deepcopy(self.model.bilesim),
            "sab": sab,
            "renk": list(self.renk.rgb()),
        }


class KutuphaneDiyalog(QtWidgets.QDialog):
    """Hazir kutuphaneden malzeme secme ve parametre girme."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kutuphaneden malzeme ekle")
        self.resize(560, 460)

        self.liste = QtWidgets.QListWidget()
        for anahtar, aciklama in mk.listele():
            oge = QtWidgets.QListWidgetItem("%-12s  %s" % (anahtar, aciklama))
            oge.setData(QtCore.Qt.UserRole, anahtar)
            f = oge.font(); f.setFamily("monospace"); oge.setFont(f)
            self.liste.addItem(oge)
        self.liste.setCurrentRow(0)

        self.param_kutu = QtWidgets.QGroupBox("Parametreler")
        self.param_duzen = QtWidgets.QFormLayout(self.param_kutu)
        self._alanlar = {}

        kutu = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        kutu.accepted.connect(self.accept)
        kutu.rejected.connect(self.reject)

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(ipucu("Bilesimler dogrulanmis kaynaklardan alinmistir. "
                              "Sicakliga bagli yogunluk kullanan malzemelerde "
                              "gecerlilik araligi malzeme_kutup.py'de yazilidir."))
        duzen.addWidget(self.liste, 1)
        duzen.addWidget(self.param_kutu)
        duzen.addWidget(kutu)

        self.liste.currentRowChanged.connect(self._parametreleri_kur)
        self._parametreleri_kur(0)

    def _parametreleri_kur(self, _satir):
        while self.param_duzen.rowCount():
            self.param_duzen.removeRow(0)
        self._alanlar = {}
        anahtar = self.secilen()
        for ad, etiket, varsayilan, en_az, en_cok in KUTUP_PARAM.get(anahtar, []):
            w = sayi(varsayilan, 4, en_az, en_cok, 0.1)
            self.param_duzen.addRow(etiket + ":", w)
            self._alanlar[ad] = w
        self.param_kutu.setVisible(bool(self._alanlar))

    def secilen(self):
        oge = self.liste.currentItem()
        return oge.data(QtCore.Qt.UserRole) if oge else None

    def uret(self):
        anahtar = self.secilen()
        kwargs = {}
        for ad, w in self._alanlar.items():
            deger = w.value()
            if anahtar == "b4c" and ad == "b10_zenginlik" and deger <= 0:
                continue          # 0 -> dogal bor (None)
            kwargs[ad] = deger
        return mk.uret(anahtar, **kwargs)


class MalzemeSekmesi(SekmeTabani):
    """Malzeme listesi sekmesi."""

    KONU = "malzeme"

    BASLIKLAR = ["Renk", "Ad", "Gorunen ad", "Yogunluk", "Sicaklik [K]", "S(a,b)", "Bilesim"]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.tablo = QtWidgets.QTableWidget(0, len(self.BASLIKLAR))
        self.tablo.setHorizontalHeaderLabels(self.BASLIKLAR)
        self.tablo.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tablo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.doubleClicked.connect(self._duzenle)

        self.d_kutup = QtWidgets.QPushButton("Kutuphaneden ekle...")
        self.d_yeni = QtWidgets.QPushButton("Bos malzeme")
        self.d_duzenle = QtWidgets.QPushButton("Duzenle...")
        self.d_kopya = QtWidgets.QPushButton("Kopyala")
        self.d_sil = QtWidgets.QPushButton("Sil")
        self.d_kutup.clicked.connect(self._kutuphaneden)
        self.d_yeni.clicked.connect(self._yeni)
        self.d_duzenle.clicked.connect(self._duzenle)
        self.d_kopya.clicked.connect(self._kopyala)
        self.d_sil.clicked.connect(self._sil)

        dugmeler = QtWidgets.QHBoxLayout()
        for d in (self.d_kutup, self.d_yeni, self.d_duzenle, self.d_kopya, self.d_sil):
            dugmeler.addWidget(d)
        dugmeler.addStretch(1)

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(baslik("Malzemeler"))
        duzen.addWidget(ipucu(
            "Satira cift tiklayarak duzenleyin. 'bosluk' ayrilmis bir addir ve "
            "geometride void (madde yok) anlamina gelir; burada tanimlanmaz."))
        duzen.addWidget(self.tablo, 1)
        duzen.addLayout(dugmeler)

    # ------------------------------------------------------------------
    def doldur(self):
        self.tablo.setRowCount(0)
        for m in self.spec["malzemeler"]:
            satir = self.tablo.rowCount()
            self.tablo.insertRow(satir)
            renk = QtWidgets.QTableWidgetItem("")
            renk.setBackground(QtWidgets.QApplication.palette().base())
            rgb = m.get("renk") or (170, 170, 170)
            from PySide6 import QtGui
            renk.setBackground(QtGui.QColor(*[int(x) for x in rgb]))
            self.tablo.setItem(satir, 0, renk)
            ozet = ", ".join("%s%s" % (b.get("isim", "?"),
                                       (" %%%.2f" % b["zenginlik"]) if b.get("zenginlik") else "")
                             for b in m.get("bilesim", []))
            degerler = [
                m["ad"],
                m.get("gorunen_ad") or m["ad"],
                "%.5g %s" % (m["yogunluk"].get("deger") or 0.0, m["yogunluk"].get("birim", "")),
                "%.1f" % (m.get("sicaklik") or 0.0),
                ", ".join(m.get("sab") or []) or "-",
                ozet,
            ]
            for i, d in enumerate(degerler, start=1):
                self.tablo.setItem(satir, i, QtWidgets.QTableWidgetItem(str(d)))
        self.tablo.resizeColumnsToContents()
        # Sutun genisligi baslik metnini ("Renk") de kapsamali; 34 px'te
        # baslik kirpiliyordu.
        self.tablo.setColumnWidth(0, 52)
        self.tablo.verticalHeader().setDefaultSectionSize(26)

    # ------------------------------------------------------------------
    def _adlar(self):
        return [m["ad"] for m in self.spec["malzemeler"]]

    def _benzersiz(self, taban):
        ad, i = taban, 2
        mevcut = set(self._adlar())
        while ad in mevcut:
            ad = "%s_%d" % (taban, i)
            i += 1
        return ad

    def _kutuphaneden(self):
        d = KutuphaneDiyalog(self)
        if d.exec() != QtWidgets.QDialog.Accepted:
            return
        m = d.uret()
        m["ad"] = self._benzersiz(m["ad"])
        self.spec["malzemeler"].append(m)
        self.spec_yukle(self.spec)
        self.bildir()

    def _yeni(self):
        m = sema.malzeme(self._benzersiz("malzeme"),
                         [sema.bilesen("H", 1.0)], 1.0, renk=(170, 170, 170))
        d = MalzemeDiyalog(m, self._adlar(), self)
        if d.exec() == QtWidgets.QDialog.Accepted:
            self.spec["malzemeler"].append(d.sonuc())
            self.spec_yukle(self.spec)
            self.bildir()

    def _secili_satir(self):
        ix = self.tablo.currentIndex()
        return ix.row() if ix.isValid() else -1

    def _duzenle(self):
        satir = self._secili_satir()
        if satir < 0:
            return
        eski = self.spec["malzemeler"][satir]
        d = MalzemeDiyalog(copy.deepcopy(eski), self._adlar(), self)
        if d.exec() == QtWidgets.QDialog.Accepted:
            yeni = d.sonuc()
            # ad degistiyse referanslari guncelle
            if yeni["ad"] != eski["ad"]:
                self._ad_degistir(eski["ad"], yeni["ad"])
            self.spec["malzemeler"][satir] = yeni
            self.spec_yukle(self.spec)
            self.bildir()

    def _ad_degistir(self, eski, yeni):
        """Malzeme adi degistiginde tum referanslari gunceller."""
        for c in self.spec.get("cubuklar", []):
            for b in c["bolgeler"]:
                if b.get("malzeme") == eski:
                    b["malzeme"] = yeni
        for p in self.spec.get("plakalar", []):
            for k in ("et_malzeme", "zarf_malzeme", "sogutucu", "yan_levha_malzeme"):
                if p.get(k) == eski:
                    p[k] = yeni
        for d in self.spec.get("demetler", []):
            if d.get("dolgu_disi") == eski:
                d["dolgu_disi"] = yeni
            for h, hedef in (d.get("anahtar") or {}).items():
                if hedef == eski:
                    d["anahtar"][h] = yeni
        yans = self.spec["kor"].get("yansitici") or {}
        if yans.get("malzeme") == eski:
            yans["malzeme"] = yeni

    def _kopyala(self):
        satir = self._secili_satir()
        if satir < 0:
            return
        m = copy.deepcopy(self.spec["malzemeler"][satir])
        m["ad"] = self._benzersiz(m["ad"])
        self.spec["malzemeler"].append(m)
        self.spec_yukle(self.spec)
        self.bildir()

    def _sil(self):
        satir = self._secili_satir()
        if satir < 0:
            return
        ad = self.spec["malzemeler"][satir]["ad"]
        kullanan = sema.kullanilan_malzemeler(self.spec)
        if ad in kullanan:
            c = QtWidgets.QMessageBox.question(
                self, "Kullanimda",
                "'%s' modelde kullaniliyor. Yine de silinsin mi?\n"
                "Silerseniz geometri gecersiz olur." % ad)
            if c != QtWidgets.QMessageBox.Yes:
                return
        self.spec["malzemeler"].pop(satir)
        self.spec_yukle(self.spec)
        self.bildir()
