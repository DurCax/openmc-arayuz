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
from cekirdek.ceviri import N_, _, _n
from cekirdek.gunluk import kaydedici
from arayuz import bilesenler as b
from arayuz import sekme_duzen as sd
from arayuz.ortak import (BosDurum, GelismisBolum, RenkDugmesi, SekmeTabani,
                          baslik, ipucu, sayi)

# Bolunen parcalar (Dalga 0): eski ad alani aynen korunur.
from arayuz.malzeme.yardimcilar import (  # noqa: F401
    TUR_SECENEKLERI, BIRIM_SECENEKLERI, YOGUNLUK_BIRIMLERI, _YOGUNLUK_ETIKETI, GRUPLAR,
    ROL_ETIKETLERI, _ROL_SIRASI, _KELVIN, rol_grubu, _GRUP_ONBELLEK, kutuphane_gruplari,
    sab_onerileri, sicaklik_metni, yogunluk_metni, bilesim_ozeti, _PLAKA_ALANI,
    _YOL_KALIPLARI, yol_okunur, _isim_duzelt, _sayi_metni, _tema_renk, ETIKET_GENISLIGI,
    _etiket, _ozet_etiketi, _hata_etiketi, _benzersiz_ad, okunur_ad)
from arayuz.malzeme.girdiler import (  # noqa: F401
    SicaklikGirdi, KesinSayiGirdi, ParametreFormu)
from arayuz.malzeme.bilesim import (  # noqa: F401
    BilesimModeli, SecenekDelegesi, _bilesim_tablosu)
from arayuz.malzeme.kutuphane_diyalog import (  # noqa: F401
    KutuphaneDiyalog)
from arayuz.malzeme.malzeme_diyalog import (  # noqa: F401
    MalzemeDiyalog)

_log = kaydedici(__name__)


# ============================================================================
# Sekme
# ============================================================================

class MalzemeSekmesi(SekmeTabani):
    """Malzeme listesi sekmesi."""

    KONU = "malzeme"

    SAB_BASLIGI = "S(α,β)"             # sembol: cevrilmez
    BASLIKLAR = [N_("Renk"), N_("Ad"), N_("Açıklama"), N_("Rol"), N_("Yoğunluk"),
                 N_("Sıcaklık"), SAB_BASLIGI, N_("Bileşim")]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._secim_adi = None

        self.tablo = self._tablo_kur()
        self._dugmeleri_kur()

        # Kart: baslik + aciklama + sag ust birincil eylem (maket duzeni).
        self.kart = b.Kart(
            _("Malzemeler"),
            aciklama=_("Düzenlemek için satıra çift tıklayın. 'bosluk' ayrılmış "
                       "addır: geometride Boş (madde yok) anlamına gelir, burada "
                       "tanımlanmaz."),
            eylem=self.d_kutup)
        self.kart.ekle(self.tablo, 1)
        # Asistan ve Kutuphanem baslik satirinda (birincil eylemin yaninda): alt satir
        # 1280 px pencerede yatay kaydirma yaratmasin (test_kabuk_kabul).
        self.kart.eylem_ekle(self.d_asistan)
        self.kart.eylem_ekle(self.d_kutuphanem)
        self.kart.ekle(sd.satir(self.d_yeni, self.d_duzenle, self.d_kopya, self.d_kaydet_kutup,
                                self.d_sil))
        liste_sayfa = self.kart

        bos_sayfa = QtWidgets.QWidget()
        bd = QtWidgets.QVBoxLayout(bos_sayfa)
        bd.setContentsMargins(0, 0, 0, 0)
        self.bos = BosDurum(
            _("Henüz malzeme yok"),
            _("Yakıt, zarf ve soğutucuyu hazır kütüphaneden ekleyin. Zenginlik, "
              "sıcaklık ve bor gibi değerleri sonradan değiştirebilirsiniz."),
            _("Kütüphaneden ekle…"))
        self.bos.eylem.connect(self._kutuphaneden)
        self.d_bos_elle = QtWidgets.QToolButton()
        self.d_bos_elle.setText(_("ya da bileşimi elle tanımlayın"))
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

        duzen = sd.sayfa_duzeni(self)
        duzen.addWidget(sd.sayfa_basligi(
            _("Malzemeler"), _("Modeldeki malzemeler, yoğunluk ve bileşim."),
            bolum="malzemeler"))
        duzen.addWidget(self.yigin, 1)
        self._dugmeleri_guncelle()

    # ------------------------------------------------------------------
    def _tablo_kur(self):
        t = QtWidgets.QTableWidget(0, len(self.BASLIKLAR))
        t.setHorizontalHeaderLabels([b_ if b_ == self.SAB_BASLIGI else _(b_)
                                     for b_ in self.BASLIKLAR])
        t.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        t.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        t.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        t.horizontalHeader().setStretchLastSection(True)
        t.horizontalHeader().setHighlightSections(False)
        t.verticalHeader().setVisible(False)
        t.setAlternatingRowColors(True)
        t.setShowGrid(False)
        t.doubleClicked.connect(self._duzenle)
        t.itemSelectionChanged.connect(self._dugmeleri_guncelle)
        return t

    def _dugmeleri_kur(self):
        """Kart eylemleri: birincil "Kütüphaneden ekle", ikonlu islem dugmeleri."""
        self.d_kutup = b.birincil_dugme(
            _("Kütüphaneden ekle…"), "download",
            _("Hazır, doğrulanmış bileşimler. Zenginlik, sıcaklık ve bor gibi "
              "değerler sonradan değiştirilebilir."))
        self.d_yeni = b.ikincil_dugme(
            _("Elle tanımla…"), "plus",
            _("Bileşimi element/izotop satırlarıyla kendiniz girin."))
        self.d_duzenle = b.ikincil_dugme(_("Düzenle…"), "sliders-horizontal")
        self.d_kopya = b.duz_dugme(_("Kopyala"), "copy")
        self.d_sil = b.tehlikeli_dugme(_("Sil"), "trash")
        self.d_asistan = b.ikincil_dugme(
            _("Asistan…"), "zap",
            _("Adım adım malzeme tasarımı: zenginlik, %TD, bor, sıcaklık ve basınçtan "
              "bileşim ve yoğunluk; türetilmiş değerler anında hesaplanır."))
        self.d_kutuphanem = b.ikincil_dugme(
            _("Kütüphanem…"), "folder-open",
            _("Bu bilgisayarda sakladığınız malzemeler ve PNNL-15870 içe aktarımı."))
        self.d_kaydet_kutup = b.duz_dugme(
            _("Kütüphaneme kaydet"), "save",
            _("Seçili malzemeyi yalnız bu bilgisayardaki kütüphanenize kaydeder."))
        for d, islem in ((self.d_kutup, self._kutuphaneden), (self.d_yeni, self._yeni),
                         (self.d_duzenle, self._duzenle), (self.d_kopya, self._kopyala),
                         (self.d_sil, self._sil), (self.d_asistan, self._asistan),
                         (self.d_kutuphanem, self._kutuphanem),
                         (self.d_kaydet_kutup, self._kutuphaneme_kaydet)):
            d.clicked.connect(islem)

    # ------------------------------------------------------------------
    def doldur(self):
        from cekirdek import uygunluk
        malzemeler = self.spec["malzemeler"]
        self.yigin.setCurrentIndex(1 if malzemeler else 0)
        try:
            roller = uygunluk.malzeme_rolleri(self.spec)
        except Exception as e:              # bozuk malzeme: tablo yine dolar, rol sutunu bos
            _log.warning("malzeme rolleri okunamadi: %s", e)
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
            rol = [_(ROL_ETIKETLERI[r]) for r in _ROL_SIRASI
                   if r in roller.get(m.get("ad"), ())]
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
                    oge.setToolTip(self._kaynak_ipucu(m))
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

    @staticmethod
    def _kaynak_ipucu(m):
        """Ad hucresinin ipucu: kutuphane malzemesi mi, elle tanimli mi."""
        if not mk.parametrik_mi(m):
            return _("Elle tanımlı bileşim")
        anahtar = m["kutup"]["anahtar"]
        return _("Kütüphaneden ({ad}) — Düzenle parametre formunu açar").format(
            ad=okunur_ad(anahtar))

    def _dugmeleri_guncelle(self):
        """Duzenle / Kopyala / Sil yalnizca bir satir seciliyken etkin."""
        satir = self._secili_satir()
        for d in (self.d_duzenle, self.d_kopya, self.d_sil, self.d_kaydet_kutup):
            d.setEnabled(satir >= 0)
        if self.spec is not None:
            self._secim_adi = self.spec["malzemeler"][satir]["ad"] if satir >= 0 else None

    # ------------------------------------------------------------------
    # kabuk sozlesmesi (Ctrl+K paleti, "bulguya git")
    # ------------------------------------------------------------------
    def komutlar(self):
        return sd.dugme_komutlari(self, _("Malzeme"), (
            self.d_kutup, self.d_asistan, self.d_kutuphanem, self.d_yeni, self.d_duzenle,
            self.d_kopya, self.d_kaydet_kutup, self.d_sil))

    def odakla(self, yer):
        """"malzeme:<ad>" bulgusunda o malzemenin satirini secer."""
        hedef = sd.yer_adi(yer, "malzeme")
        if hedef is None or self.spec is None:
            return False
        for i, m in enumerate(self.spec["malzemeler"]):
            if m.get("ad") == hedef[1]:
                self.tablo.selectRow(i)
                self.tablo.setFocus()
                return True
        return False

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

    def _asistan(self):
        from arayuz.malzeme.asistan import MalzemeAsistani
        d = MalzemeAsistani(self.spec, self)
        if self._diyalog_calistir(d) and d.projeye_eklenecek_mi():
            self._ekle(d.sonuc())

    def _kutuphanem(self):
        from arayuz.malzeme.kutuphane_tarayici import KutuphaneTarayici
        t = KutuphaneTarayici(self.spec, self)
        t.projeye_ekle.connect(self._ekle)
        self._diyalog_calistir(t)

    def _kutuphaneme_kaydet(self):
        """Secili malzemeyi kullanici kutuphanesine ekler (ad cakisirsa _2, _3 ...)."""
        from cekirdek import malzeme_kullanici as mku
        satir = self._secili_satir()
        if satir < 0:
            return False
        m = self.spec["malzemeler"][satir]
        ad = m["ad"]

        def islem(kayitlar):
            nonlocal ad
            ad = mku.benzersiz_kayit_adi(kayitlar, m["ad"])
            return mku.ekle(kayitlar, mku.kayit_olustur(
                dict(m, ad=ad), aciklama=m.get("gorunen_ad") or "", kaynak="proje"))
        try:
            mku.degistir(islem)
        except (mku.KutuphaneHatasi, ValueError) as e:
            _log.warning("kutuphaneye kaydedilemedi: %s", e)
            b.bildir(self.window(), str(e), "hata", baslik=_("Kütüphaneye kaydedilemedi"))
            return False
        b.bildir(self.window(), _("'%s' kütüphanenize kaydedildi.") % ad, "basari")
        return True

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
                    _("Malzeme kullanımda"),
                    _n("'{ad}' modelde {n} yerde kullanılıyor ({ornek}).\n"
                       "Silerseniz bu yerler tanımsız kalır ve model kurulamaz. "
                       "Yine de silinsin mi?",
                       "'{ad}' modelde {n} yerde kullanılıyor ({ornek}).\n"
                       "Silerseniz bu yerler tanımsız kalır ve model kurulamaz. "
                       "Yine de silinsin mi?", len(yerler)).format(
                           ad=ad, n=len(yerler), ornek=ornek)):
                return
        self.spec["malzemeler"].pop(satir)
        self._secim_adi = None
        self.spec_yukle(self.spec)
        self.bildir()
