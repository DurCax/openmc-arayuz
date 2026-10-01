# -*- coding: utf-8 -*-
"""
 arayuz/malzeme/malzeme_diyalog.py  --  MalzemeDiyalog: tek malzemeyi duzenleme

 arayuz/sekme_malzeme.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import sekme_malzeme; sekme_malzeme.X` aynen calisir.
"""

import copy

from PySide6 import QtCore, QtWidgets
from cekirdek import malzeme_kutup as mk
from cekirdek import sema
from cekirdek.ceviri import _
from arayuz import bilesenler as b
from arayuz import sekme_duzen as sd
from arayuz.ortak import GelismisBolum, RenkDugmesi, baslik, ipucu
from arayuz.tasarim import tokenlar
from arayuz.malzeme.yardimcilar import (
    ROL_ETIKETLERI, YOGUNLUK_BIRIMLERI, _ROL_SIRASI, _etiket, _hata_etiketi, _ozet_etiketi,
    _sayi_metni, katalog_aciklamasi, okunur_ad, sab_onerileri, uretim_ozeti)
from arayuz.malzeme.girdiler import KesinSayiGirdi, ParametreFormu, SicaklikGirdi
from arayuz.malzeme.bilesim import BilesimModeli, _bilesim_tablosu

A = tokenlar.ARALIK


# ============================================================================
# Duzenleme
# ============================================================================

class MalzemeDiyalog(QtWidgets.QDialog):
    """
    Tek bir malzemeyi duzenler.
      * kutuphane malzemesi (mk.parametrik_mi): AYNI parametre formu; sonuc
        parametrelerden yeniden uretilir. Ham bilesim Gelismis'te salt okunur;
        "Bilesimi elle duzenle" malzemeyi kutuphaneden ayirir.
      * diger (eski/elle) malzemeler: bilesim tablosu.
    Tek ad alani vardir (spec "ad"i). "gorunen_ad" kutuphane malzemesinde
    parametrelerden uretilen aciklamadir; elle malzemede eski deger korunur
    (adla ayniysa adla birlikte degisir).
    """

    GELISMIS_ANAHTAR = "malzeme_diyalog"

    def __init__(self, malzeme, spec=None, parent=None, yeni=False):
        super().__init__(parent)
        # Eski imza MalzemeDiyalog(malzeme, mevcut_adlar) de kabul edilir.
        if spec is None or isinstance(spec, (list, tuple, set)):
            adlar = list(spec or [])
            spec = sema.yeni_spec()
            spec["malzemeler"] = [{"ad": a} for a in adlar]
        self._spec = spec
        self._orijinal = copy.deepcopy(malzeme)
        self._eski_ad = malzeme.get("ad", "")
        self._parametrik = mk.parametrik_mi(malzeme)
        self._kopmus = "kutup" in malzeme and not self._parametrik
        self.setWindowTitle(_("Yeni malzeme") if yeni else _("Malzemeyi düzenle"))
        self.resize(660, 600)

        self._ad_alani()
        self._param_sayfasi(malzeme)
        self._elle_sayfasi(malzeme)
        self.ozet = _ozet_etiketi()
        self._gelismis_kutusu(malzeme)
        self._dugme_kutusu()
        self._duzeni_kur()

        # S(a,b) durumu: tek kaynak self._sab
        self._sab = list(malzeme.get("sab") or [])
        self._oneri_vardi = bool(sab_onerileri(malzeme))
        self._kip_uygula()
        self._dogrula()
        if yeni and not self.model.bilesim and not self.parametrik_kip():
            self._satir_ekle()

    # --------------------------------------------------------------- kurulum
    def _ad_alani(self):
        self.ad = QtWidgets.QLineEdit(self._eski_ad)
        self.ad.textChanged.connect(self._dogrula)
        self.ad_hata = _hata_etiketi()
        self._ust_form = sd.form()
        self._ust_form.addRow(_etiket(_("Ad:")), self.ad)
        self._ust_form.addRow(self.ad_hata)

    def _param_sayfasi(self, malzeme):
        """Kutuphane malzemesi: parametre formu (elle bilesim tablosu yerine)."""
        self.param_sayfa = QtWidgets.QWidget()
        pd = QtWidgets.QVBoxLayout(self.param_sayfa)
        pd.setContentsMargins(0, 0, 0, 0)
        pd.setSpacing(A["s"])
        self.form = None
        if not self._parametrik:
            return
        k = malzeme["kutup"]
        anahtar = k["anahtar"]
        self.tur_etiket = baslik("%s (%s)" % (okunur_ad(anahtar), _("kütüphane")))
        pd.addWidget(self.tur_etiket)
        pd.addWidget(ipucu(katalog_aciklamasi(anahtar)))
        self.form = ParametreFormu(anahtar, k.get("param") or {})
        self.form.degisti.connect(self._param_degisti)
        pd.addWidget(self.form)

    def _elle_sayfasi(self, malzeme):
        """Elle tanimli malzeme: yogunluk/sicaklik/S(a,b) formu + bilesim tablosu."""
        self.elle_sayfa = QtWidgets.QWidget()
        ed = QtWidgets.QVBoxLayout(self.elle_sayfa)
        ed.setContentsMargins(0, 0, 0, 0)
        ed.setSpacing(A["s"])
        self.kopuk_not = ipucu(_(
            "Bu malzeme kütüphaneden eklendikten sonra parametre formu dışında "
            "değiştirilmiş; bileşim tablosuyla düzenleniyor."))
        self.kopuk_not.setVisible(self._kopmus)
        ed.addWidget(self.kopuk_not)
        ed.addLayout(self._elle_formu(malzeme))
        ed.addWidget(baslik(_("Bileşim")))
        self.model = BilesimModeli(malzeme.get("bilesim"))
        self.tablo = _bilesim_tablosu(self.model)
        ed.addWidget(self.tablo, 1)
        self.d_satir_ekle = b.ikincil_dugme(_("Satır ekle"), "plus")
        self.d_satir_sil = b.duz_dugme(_("Satırı sil"), "trash")
        self.d_satir_ekle.clicked.connect(self._satir_ekle)
        self.d_satir_sil.clicked.connect(self._satir_sil)
        ed.addWidget(sd.satir(self.d_satir_ekle, self.d_satir_sil))
        self.tablo.selectionModel().selectionChanged.connect(self._satir_dugmeleri)
        for sinyal in (self.model.dataChanged, self.model.rowsInserted,
                       self.model.rowsRemoved, self.model.modelReset):
            sinyal.connect(self._elle_degisti)

    def _elle_formu(self, malzeme):
        self.elle_form = sd.form()
        # Elle malzemede aciklama kendiliginden yenilenmez (bilesimden okunamaz):
        # zenginligi degistiren kullanici onu burada gunceller. Eskiden alan
        # yoktu ve "UO2 %3.0" aciklamasi %4 zenginlikte de listelerde kaliyordu.
        g0 = malzeme.get("gorunen_ad") or ""
        self.aciklama = QtWidgets.QLineEdit("" if g0 == self._eski_ad else g0)
        self.aciklama.setPlaceholderText(
            _("ör. UO₂ %4.0 — listelerde adın yanında görünür"))
        self.elle_form.addRow(_etiket(_("Açıklama:")), self.aciklama)
        self.yogunluk = KesinSayiGirdi((malzeme.get("yogunluk") or {}).get("deger") or 1.0)
        self.yogunluk.textChanged.connect(self._elle_degisti)
        self.yogunluk_birim_etiket = QtWidgets.QLabel()
        self.yogunluk_birim_etiket.setObjectName("birim")
        self.elle_form.addRow(_etiket(_("Yoğunluk:")),
                              sd.satir(self.yogunluk, self.yogunluk_birim_etiket))
        self._ilk_sicaklik = malzeme.get("sicaklik")
        self.sicaklik = SicaklikGirdi(self._ilk_sicaklik or 293.6, 0.0, 5000.0, 2, 10.0)
        self._ilk_sicaklik_gosterim = self.sicaklik.value()
        self.elle_form.addRow(_etiket(_("Sıcaklık:")), self.sicaklik)
        self.sab_kutu = QtWidgets.QComboBox()
        self.sab_kutu.setToolTip(_(
            "Bileşime uyan termal saçılma tabloları. Termal spektrumda eksik "
            "bırakmak k'yi yüzde mertebesinde kaydırır."))
        self.sab_kutu.activated.connect(self._sab_secildi)
        self.elle_form.addRow(_etiket(_("Termal saçılma S(α,β):")), self.sab_kutu)
        return self.elle_form

    def _gelismis_kutusu(self, malzeme):
        """Nadiren gereken alanlar: renk, yogunluk birimi, serbest S(a,b), ham bilesim."""
        self.gelismis = GelismisBolum(self.GELISMIS_ANAHTAR)
        g_form = sd.form()
        self.renk = RenkDugmesi(malzeme.get("renk") or (170, 170, 170))
        g_form.addRow(_etiket(_("Renk:")), self.renk)
        self.birim = QtWidgets.QComboBox()
        for anahtar, etiket in YOGUNLUK_BIRIMLERI:
            self.birim.addItem(etiket, anahtar)
        ilk_birim = (malzeme.get("yogunluk") or {}).get("birim") or "g/cm3"
        if self.birim.findData(ilk_birim) < 0:
            self.birim.addItem(ilk_birim, ilk_birim)
        self.birim.setCurrentIndex(self.birim.findData(ilk_birim))
        self.birim.currentIndexChanged.connect(self._elle_degisti)
        self.birim_etiket = _etiket(_("Yoğunluk birimi:"))
        g_form.addRow(self.birim_etiket, self.birim)
        self.sab_elle = QtWidgets.QLineEdit()
        self.sab_elle.setPlaceholderText(_("ör. c_H_in_H2O, c_Graphite"))
        self.sab_elle.setToolTip(_("Virgülle ayrılmış S(α,β) tablo adları. Önerilen "
                                   "listede olmayan bir tablo gerekiyorsa buraya yazın."))
        self.sab_elle.editingFinished.connect(self._sab_elle_bitti)
        self.sab_elle_etiket = _etiket(_("S(α,β) (elle):"))
        g_form.addRow(self.sab_elle_etiket, self.sab_elle)
        self.gelismis.duzen().addLayout(g_form)
        self.gelismis.ekle(self._ham_kutu())

    def _ham_kutu(self):
        """Parametrik malzemede uretilen bilesim (salt okunur) + kutuphaneden ayirma."""
        self.ham_kutu = QtWidgets.QWidget()
        hd = QtWidgets.QVBoxLayout(self.ham_kutu)
        hd.setContentsMargins(0, 0, 0, 0)
        hd.setSpacing(A["s"])
        hd.addWidget(QtWidgets.QLabel(_("Üretilen bileşim:")))
        self.ham_model = BilesimModeli([], salt_okunur=True)
        self.ham_tablo = _bilesim_tablosu(self.ham_model)
        hd.addWidget(self.ham_tablo)
        self.d_elle_gec = b.ikincil_dugme(_("Bileşimi elle düzenle"), "sliders-horizontal",
                                          _("Malzeme kütüphane parametrelerinden ayrılır; "
                                            "zenginlik, sıcaklık gibi değerler bir daha "
                                            "otomatik hesaplanmaz."))
        self.d_elle_gec.clicked.connect(self.elle_duzenlemeye_gec)
        hd.addWidget(self.d_elle_gec, 0, QtCore.Qt.AlignLeft)
        hd.addWidget(ipucu(_("Elle düzenlemeye geçince malzeme kütüphane "
                             "parametrelerinden ayrılır.")))
        return self.ham_kutu

    def _dugme_kutusu(self):
        self.kutu = QtWidgets.QDialogButtonBox()
        self.d_tamam = self.kutu.addButton(_("Tamam"), QtWidgets.QDialogButtonBox.AcceptRole)
        self.d_tamam.setObjectName("birincil")
        self.kutu.addButton(_("Vazgeç"), QtWidgets.QDialogButtonBox.RejectRole)
        self.kutu.accepted.connect(self._onayla)
        self.kutu.rejected.connect(self.reject)
        self.hata = _hata_etiketi()

    def _duzeni_kur(self):
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(A["l"], A["l"], A["l"], A["l"])
        duzen.setSpacing(A["m"])
        duzen.addLayout(self._ust_form)
        duzen.addWidget(self.param_sayfa)
        duzen.addWidget(self.elle_sayfa, 1)
        duzen.addWidget(self.ozet)
        duzen.addWidget(self.gelismis)
        duzen.addStretch(0)
        duzen.addWidget(self.hata)
        duzen.addWidget(self.kutu)

    # ------------------------------------------------------------------ kip
    def parametrik_kip(self):
        return self.form is not None

    def _kip_uygula(self):
        p = self.parametrik_kip()
        self.param_sayfa.setVisible(p)
        self.elle_sayfa.setVisible(not p)
        self.ham_kutu.setVisible(p)
        for w in (self.birim_etiket, self.birim, self.sab_elle_etiket, self.sab_elle):
            w.setVisible(not p)
        if p:
            self._param_degisti()
        else:
            self._sab_kutusunu_kur()
            self._elle_degisti()
        self._satir_dugmeleri()
        # parametrik formda bilesim tablosu yok: pencere icerik kadar olsun
        self.resize(660, self.sizeHint().height() if p else 600)

    def elle_duzenlemeye_gec(self):
        """Parametrik malzemeyi kutuphaneden ayirip bilesim tablosuna gecer."""
        if self.form is None:
            return
        m = self.form.malzeme()
        m.pop("kutup", None)
        m["ad"] = self._eski_ad
        m["renk"] = list(self.renk.rgb())
        for k, v in self._orijinal.items():
            if k not in m and k != "kutup":
                m[k] = copy.deepcopy(v)
        self._orijinal = m
        self.aciklama.setText(m.get("gorunen_ad") or "")
        self.form.hide()
        self.form.setParent(None)
        self.form.deleteLater()
        self.form = None
        self.yogunluk._ilk = float(m["yogunluk"]["deger"])
        self.yogunluk.setText(_sayi_metni(self.yogunluk._ilk))
        self.yogunluk._ilk_metin = self.yogunluk.text()
        self.birim.setCurrentIndex(max(self.birim.findData(m["yogunluk"]["birim"]), 0))
        self._ilk_sicaklik = m.get("sicaklik")
        self.sicaklik.setValue(self._ilk_sicaklik or 293.6)
        self._ilk_sicaklik_gosterim = self.sicaklik.value()
        self._sab = list(m.get("sab") or [])
        self._oneri_vardi = bool(sab_onerileri(m))
        self.model.yukle(m.get("bilesim"))
        self._kip_uygula()

    # ------------------------------------------------------------ parametrik
    def _param_degisti(self):
        if self.form is None:
            return
        uretim = self.form.uretim_sorunu()
        m = None
        if not uretim:
            m = self.form.malzeme()
            self.ham_model.yukle(m.get("bilesim"))
        self.ozet.setText(uretim_ozeti(m, uretim))
        self._dogrula()

    # ----------------------------------------------------------------- elle
    def _gecici_malzeme(self):
        return {"bilesim": self.model.bilesim,
                "yogunluk": {"birim": self.birim.currentData(),
                             "deger": self.yogunluk.deger() or 0.0}}

    def _elle_degisti(self, *_arg):           # '_' gettext'i golgelemesin
        if self.parametrik_kip():
            return
        self.yogunluk_birim_etiket.setText(
            dict(YOGUNLUK_BIRIMLERI).get(self.birim.currentData(), self.birim.currentData()))
        oneriler = sab_onerileri(self._gecici_malzeme())
        # Bilesim su/grafit gorunumune YENI geldiyse (bu pencerede) onerilen
        # S(a,b) kendiliginden secilir; acilista var olan secim DEGISMEZ.
        if oneriler and not self._oneri_vardi and not self._sab:
            self._sab = [oneriler[0][0]]
            self.sab_elle.setText(", ".join(self._sab))
        self._oneri_vardi = bool(oneriler)
        self._sab_kutusunu_kur(oneriler)
        try:
            from cekirdek import uygunluk
            roller = uygunluk.tek_malzeme_rolleri(self._gecici_malzeme())
        except Exception:
            roller = set()
        rol = ", ".join(_(ROL_ETIKETLERI[r]) for r in _ROL_SIRASI if r in roller)
        self.ozet.setText(_("Bu bileşim modelde şöyle tanınıyor: {rol}").format(rol=rol or "—"))

    def _sab_kutusunu_kur(self, oneriler=None):
        if oneriler is None:
            oneriler = sab_onerileri(self._gecici_malzeme())
        self.sab_kutu.blockSignals(True)
        self.sab_kutu.clear()
        for ad, tanim in oneriler:
            # tanim cekirdekten (dogrula._SAB_KURALLARI); burada cevrilir
            self.sab_kutu.addItem("%s — %s" % (ad, _(tanim)), [ad])
        if self._sab and self._sab not in [[a] for a, _t in oneriler]:
            self.sab_kutu.insertItem(0, _("Elle girilen: {sab}").format(sab=", ".join(self._sab)),
                                     list(self._sab))
        self.sab_kutu.addItem(_("Yok (termal saçılma verisi ekleme)"), [])
        for i in range(self.sab_kutu.count()):
            if self.sab_kutu.itemData(i) == self._sab:
                self.sab_kutu.setCurrentIndex(i)
                break
        self.sab_kutu.blockSignals(False)
        goster = bool(oneriler) or bool(self._sab)
        self.elle_form.setRowVisible(self.sab_kutu, goster)
        if self.sab_elle.text() != ", ".join(self._sab) and not self.sab_elle.hasFocus():
            self.sab_elle.setText(", ".join(self._sab))

    def _sab_secildi(self, i):
        self._sab = list(self.sab_kutu.itemData(i) or [])
        self.sab_elle.setText(", ".join(self._sab))
        self._elle_degisti()

    def _sab_elle_bitti(self):
        yeni = [s.strip() for s in self.sab_elle.text().replace(";", ",").split(",") if s.strip()]
        if yeni != self._sab:
            self._sab = yeni
            self._elle_degisti()

    def _satir_ekle(self):
        self.model.satir_ekle()
        ix = self.model.index(self.model.rowCount() - 1, BilesimModeli.S_ISIM)
        self.tablo.setCurrentIndex(ix)
        self.tablo.edit(ix)

    def _satir_sil(self):
        satirlar = self.tablo.selectionModel().selectedRows()
        if satirlar:
            self.model.satir_sil(satirlar[0].row())

    def _satir_dugmeleri(self, *_):
        self.d_satir_sil.setEnabled(bool(self.tablo.selectionModel().selectedRows()))

    # ---------------------------------------------------------------- onay
    def _dogrula(self, *_):
        sorun = sema.malzeme_adi_sorunu(self._spec, self.ad.text(), haric=self._eski_ad)
        self.ad_hata.setText(sorun or "")
        self.ad_hata.setVisible(bool(sorun))
        uretim = self.form.uretim_sorunu() if self.parametrik_kip() else None
        self.d_tamam.setEnabled(sorun is None and uretim is None)
        return sorun is None and uretim is None

    def icerik_sorunu(self):
        """Elle kipte kaydi engelleyen eksik; yoksa None."""
        if self.parametrik_kip():
            return None
        yog = self.yogunluk.deger()
        if yog is None or yog <= 0:
            return _("Yoğunluk pozitif bir sayı olmalı.")
        if not self.model.bilesim:
            return _("Bileşime en az bir satır ekleyin.")
        for i, b in enumerate(self.model.bilesim, start=1):
            if not (b.get("isim") or "").strip():
                return _("Bileşimin {n}. satırında isim boş.").format(n=i)
            if float(b.get("miktar") or 0.0) <= 0:
                return _("Bileşimin {n}. satırında miktar pozitif olmalı.").format(n=i)
        return None

    def _onayla(self):
        if not self._dogrula():
            return
        sorun = self.icerik_sorunu()
        self.hata.setText(sorun or "")
        self.hata.setVisible(bool(sorun))
        if sorun is None:
            self.accept()

    def sonuc(self):
        ad = self.ad.text()
        if self.parametrik_kip():
            m = self.form.malzeme()
            m["ad"] = ad
            m["renk"] = list(self.renk.rgb())
            for k, v in self._orijinal.items():     # bilinmeyen alanlar korunur
                if k not in m:
                    m[k] = copy.deepcopy(v)
            return m
        m = copy.deepcopy(self._orijinal)
        m.pop("kutup", None)
        m["ad"] = ad
        m["gorunen_ad"] = self.aciklama.text().strip() or ad
        m["yogunluk"] = {"birim": self.birim.currentData(), "deger": self.yogunluk.deger()}
        v = self.sicaklik.value()
        m["sicaklik"] = self._ilk_sicaklik if v == self._ilk_sicaklik_gosterim else v
        m["bilesim"] = copy.deepcopy(self.model.bilesim)
        m["sab"] = list(self._sab)
        m["renk"] = list(self.renk.rgb())
        return m
