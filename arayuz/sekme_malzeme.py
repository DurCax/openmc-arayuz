# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_malzeme.py  --  Malzeme tanimlari
================================================================================
 Iki yol:
   * Kutuphaneden ekle : hazir, dogrulanmis bilesimler. Uretim parametreleri
     (zenginlik, sicaklik, bor...) malzemeyle birlikte saklanir
     (m["kutup"], bkz. malzeme_kutup.parametrik_uret); "Duzenle" ayni formu
     acar ve malzeme o parametrelerden YENIDEN uretilir.
   * Elle tanimla      : bilesim tablosu (tur/birim acilir listeden,
     zenginlik yalnizca U elementi satirinda).
 Nadiren gereken alanlar (ham bilesim, yogunluk birimi, renk, serbest S(a,b))
 "Gelismis" bolumundedir.

 KURALLAR BURADA YAZILMAZ
   Kutuphane gruplari   : uygunluk.tek_malzeme_rolleri
   S(a,b) onerileri     : dogrula._SAB_KURALLARI (dogrulamanin uyardigi kural)
   Ad gecerliligi       : sema.malzeme_adi_sorunu
   Ad degisimi          : sema.malzeme_adini_degistir (butun referanslar)
================================================================================
"""

import copy

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import malzeme_kutup as mk
from cekirdek import sema
from arayuz.ortak import (BosDurum, GelismisBolum, RenkDugmesi, SekmeTabani,
                          baslik, ipucu, sayi)

# Bolunen parcalar (Dalga 0): eski ad alani aynen korunur.
from arayuz.malzeme.yardimcilar import (  # noqa: F401
    TUR_SECENEKLERI, BIRIM_SECENEKLERI, YOGUNLUK_BIRIMLERI, _YOGUNLUK_ETIKETI, GRUPLAR,
    ROL_ETIKETLERI, _ROL_SIRASI, _KELVIN, rol_grubu, _GRUP_ONBELLEK, kutuphane_gruplari,
    sab_onerileri, sicaklik_metni, yogunluk_metni, bilesim_ozeti, _PLAKA_ALANI,
    _YOL_KALIPLARI, yol_okunur, _isim_duzelt, _sayi_metni, _tema_renk, ETIKET_GENISLIGI,
    _etiket, _ozet_etiketi, _hata_etiketi, _benzersiz_ad)
from arayuz.malzeme.girdiler import (  # noqa: F401
    SicaklikGirdi, KesinSayiGirdi, ParametreFormu)
from arayuz.malzeme.bilesim import (  # noqa: F401
    BilesimModeli, SecenekDelegesi, _bilesim_tablosu)
from arayuz.malzeme.kutuphane_diyalog import (  # noqa: F401
    KutuphaneDiyalog)
from arayuz.malzeme.malzeme_diyalog import (  # noqa: F401
    MalzemeDiyalog)


# ============================================================================
# Sekme
# ============================================================================

class MalzemeSekmesi(SekmeTabani):
    """Malzeme listesi sekmesi."""

    KONU = "malzeme"

    BASLIKLAR = ["Renk", "Ad", "Açıklama", "Rol", "Yoğunluk", "Sıcaklık",
                 "S(α,β)", "Bileşim"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._secim_adi = None

        self.tablo = QtWidgets.QTableWidget(0, len(self.BASLIKLAR))
        self.tablo.setHorizontalHeaderLabels(self.BASLIKLAR)
        self.tablo.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tablo.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tablo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.doubleClicked.connect(self._duzenle)
        self.tablo.itemSelectionChanged.connect(self._dugmeleri_guncelle)

        self.d_kutup = QtWidgets.QPushButton("Kütüphaneden ekle…")
        self.d_kutup.setObjectName("birincil")
        self.d_yeni = QtWidgets.QPushButton("Elle tanımla…")
        self.d_yeni.setToolTip("Bileşimi element/izotop satırlarıyla kendiniz girin.")
        self.d_duzenle = QtWidgets.QPushButton("Düzenle…")
        self.d_kopya = QtWidgets.QPushButton("Kopyala")
        self.d_sil = QtWidgets.QPushButton("Sil")
        self.d_kutup.clicked.connect(self._kutuphaneden)
        self.d_yeni.clicked.connect(self._yeni)
        self.d_duzenle.clicked.connect(self._duzenle)
        self.d_kopya.clicked.connect(self._kopyala)
        self.d_sil.clicked.connect(self._sil)

        # Iki satir: editor paneli dar (onizlemenin yaninda ~250 px); tek
        # satirda Duzenle/Kopyala/Sil yatay kaydirmanin arkasina dusuyordu.
        dugmeler = QtWidgets.QVBoxLayout()
        ekle_satir = QtWidgets.QHBoxLayout()
        for d in (self.d_kutup, self.d_yeni):
            ekle_satir.addWidget(d)
        ekle_satir.addStretch(1)
        islem_satir = QtWidgets.QHBoxLayout()
        for d in (self.d_duzenle, self.d_kopya, self.d_sil):
            islem_satir.addWidget(d)
        islem_satir.addStretch(1)
        dugmeler.addLayout(ekle_satir)
        dugmeler.addLayout(islem_satir)

        liste_sayfa = QtWidgets.QWidget()
        ld = QtWidgets.QVBoxLayout(liste_sayfa)
        ld.setContentsMargins(0, 0, 0, 0)
        ld.addWidget(ipucu(
            "Düzenlemek için satıra çift tıklayın. Kütüphaneden eklenen "
            "malzemelerde zenginlik, sıcaklık, bor gibi değerler sonradan "
            "değiştirilebilir. 'bosluk' ayrılmış addır: geometride Boş (madde "
            "yok) anlamına gelir, burada tanımlanmaz."))
        ld.addWidget(self.tablo, 1)
        ld.addLayout(dugmeler)

        bos_sayfa = QtWidgets.QWidget()
        bd = QtWidgets.QVBoxLayout(bos_sayfa)
        bd.setContentsMargins(0, 0, 0, 0)
        self.bos = BosDurum(
            "Henüz malzeme yok",
            "Yakıt, zarf ve soğutucuyu hazır kütüphaneden ekleyin. Zenginlik, "
            "sıcaklık ve bor gibi değerleri sonradan değiştirebilirsiniz.",
            "Kütüphaneden ekle…")
        self.bos.eylem.connect(self._kutuphaneden)
        self.d_bos_elle = QtWidgets.QToolButton()
        self.d_bos_elle.setText("ya da bileşimi elle tanımlayın")
        self.d_bos_elle.setAutoRaise(True)
        self.d_bos_elle.setCursor(QtCore.Qt.PointingHandCursor)
        self.d_bos_elle.clicked.connect(self._yeni)
        bos_duzen = self.bos.layout()
        bos_duzen.insertWidget(bos_duzen.indexOf(self.bos.dugme) + 1,
                               self.d_bos_elle, 0, QtCore.Qt.AlignHCenter)
        bd.addWidget(self.bos, 1)

        self.yigin = QtWidgets.QStackedWidget()
        self.yigin.addWidget(bos_sayfa)
        self.yigin.addWidget(liste_sayfa)

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(baslik("Malzemeler"))
        duzen.addWidget(self.yigin, 1)
        self._dugmeleri_guncelle()

    # ------------------------------------------------------------------
    def doldur(self):
        from cekirdek import uygunluk
        malzemeler = self.spec["malzemeler"]
        self.yigin.setCurrentIndex(1 if malzemeler else 0)
        try:
            roller = uygunluk.malzeme_rolleri(self.spec)
        except Exception:
            roller = {}
        self.tablo.blockSignals(True)
        self.tablo.setRowCount(0)
        for m in malzemeler:
            satir = self.tablo.rowCount()
            self.tablo.insertRow(satir)
            renk = QtWidgets.QTableWidgetItem("")
            rgb = m.get("renk") or (170, 170, 170)
            renk.setBackground(QtGui.QColor(*[int(x) for x in rgb]))
            self.tablo.setItem(satir, 0, renk)
            rol = [ROL_ETIKETLERI[r] for r in _ROL_SIRASI if r in roller.get(m.get("ad"), ())]
            aciklama = m.get("gorunen_ad") or ""
            degerler = [
                m.get("ad", ""),
                "" if aciklama == m.get("ad") else aciklama,
                ", ".join(rol),
                yogunluk_metni(m),
                sicaklik_metni(m.get("sicaklik")),
                ", ".join(m.get("sab") or []) or "—",
                bilesim_ozeti(m),
            ]
            for i, d in enumerate(degerler, start=1):
                oge = QtWidgets.QTableWidgetItem(str(d))
                if i == 1:
                    oge.setToolTip("Kütüphaneden (%s) — Düzenle parametre formunu açar"
                                   % mk.okunur_ad(m["kutup"]["anahtar"])
                                   if mk.parametrik_mi(m) else "Elle tanımlı bileşim")
                self.tablo.setItem(satir, i, oge)
        self.tablo.resizeColumnsToContents()
        # Sutun genisligi baslik metnini ("Renk") de kapsamali.
        self.tablo.setColumnWidth(0, 52)
        self.tablo.verticalHeader().setDefaultSectionSize(26)
        # secim korunur (ad ile): duzenlemeden sonra ayni satir secili kalir
        adlar = [m.get("ad") for m in malzemeler]
        self.tablo.clearSelection()
        if self._secim_adi in adlar:
            self.tablo.selectRow(adlar.index(self._secim_adi))
        self.tablo.blockSignals(False)
        self._dugmeleri_guncelle()

    def _dugmeleri_guncelle(self):
        """Duzenle / Kopyala / Sil yalnizca bir satir seciliyken etkin."""
        satir = self._secili_satir()
        for d in (self.d_duzenle, self.d_kopya, self.d_sil):
            d.setEnabled(satir >= 0)
        if self.spec is not None:
            self._secim_adi = self.spec["malzemeler"][satir]["ad"] if satir >= 0 else None

    # ------------------------------------------------------------------
    def _adlar(self):
        return [m["ad"] for m in self.spec["malzemeler"]]

    def _benzersiz(self, taban):
        return _benzersiz_ad(self.spec, taban)

    def _diyalog_calistir(self, d):
        """Diyalogu kosar; kabul edildiyse True. (Testler bunu ezer.)"""
        return d.exec() == QtWidgets.QDialog.Accepted

    def _soru(self, baslik_, metin):
        c = QtWidgets.QMessageBox.question(self, baslik_, metin)
        return c == QtWidgets.QMessageBox.Yes

    def _ekle(self, m):
        self.spec["malzemeler"].append(m)
        self._secim_adi = m["ad"]
        self.spec_yukle(self.spec)
        self.bildir()

    def _kutuphaneden(self):
        d = KutuphaneDiyalog(self.spec, self)
        if self._diyalog_calistir(d):
            self._ekle(d.sonuc())

    def _yeni(self):
        m = sema.malzeme(self._benzersiz("malzeme"), [], 1.0, renk=(170, 170, 170))
        d = MalzemeDiyalog(m, self.spec, self, yeni=True)
        if self._diyalog_calistir(d):
            self._ekle(d.sonuc())

    def _secili_satir(self):
        if not self.spec:
            return -1
        satirlar = self.tablo.selectionModel().selectedRows()
        if not satirlar:
            return -1
        s = satirlar[0].row()
        return s if 0 <= s < len(self.spec["malzemeler"]) else -1

    def _duzenle(self, *_):
        satir = self._secili_satir()
        if satir < 0:
            return
        d = MalzemeDiyalog(self.spec["malzemeler"][satir], self.spec, self)
        if self._diyalog_calistir(d):
            self.duzenlemeyi_uygula(satir, d.sonuc())

    def duzenlemeyi_uygula(self, satir, yeni):
        """
        Diyalog sonucunu 'satir'daki malzemeye yazar. Ad degistiyse spec'teki
        BUTUN referanslar da degisir (sema.malzeme_adini_degistir).
        """
        eski = self.spec["malzemeler"][satir]
        if yeni["ad"] != eski["ad"]:
            ayni = sum(1 for m in self.spec["malzemeler"] if m.get("ad") == eski["ad"])
            if ayni == 1:
                sema.malzeme_adini_degistir(self.spec, eski["ad"], yeni["ad"])
        self.spec["malzemeler"][satir] = yeni
        self._secim_adi = yeni["ad"]
        self.spec_yukle(self.spec)
        self.bildir()

    def _ad_degistir(self, eski, yeni):
        """Geriye uyumluluk: tam ad degisimi sema'dadir."""
        return sema.malzeme_adini_degistir(self.spec, eski, yeni)

    def _kopyala(self):
        satir = self._secili_satir()
        if satir < 0:
            return
        m = copy.deepcopy(self.spec["malzemeler"][satir])
        m["ad"] = self._benzersiz(m["ad"])
        if m.get("gorunen_ad") == self.spec["malzemeler"][satir]["ad"]:
            m["gorunen_ad"] = m["ad"]
        self._ekle(m)

    def _sil(self):
        satir = self._secili_satir()
        if satir < 0:
            return
        ad = self.spec["malzemeler"][satir]["ad"]
        yerler = sema.malzeme_referanslari(self.spec, ad)
        if yerler:
            okunur = []
            for y in yerler:
                o = yol_okunur(y)
                if o not in okunur:
                    okunur.append(o)
            ornek = ", ".join(okunur[:3]) + (" …" if len(okunur) > 3 else "")
            if not self._soru(
                    "Malzeme kullanımda",
                    "'%s' modelde %d yerde kullanılıyor (%s).\n"
                    "Silerseniz bu yerler tanımsız kalır ve model kurulamaz. "
                    "Yine de silinsin mi?" % (ad, len(yerler), ornek)):
                return
        self.spec["malzemeler"].pop(satir)
        self._secim_adi = None
        self.spec_yukle(self.spec)
        self.bildir()
