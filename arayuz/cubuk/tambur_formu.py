# -*- coding: utf-8 -*-
"""
 arayuz/cubuk/tambur_formu.py  --  TamburFormuMixin: Parcalar > Tamburlar

 Kontrol tamburu (control drum) KUTUPHANESI: spec["tamburlar"] tanimlari
 (docs/GEOMETRI_MODELI.md §3.1; alanlar cekirdek/tambur.py):
     ad, yaricap, govde_malzeme, emici_malzeme, emici_ic_yaricap, emici_aci
 Tanim geometri + malzemedir; yerlesim (sayi, merkez yaricapi, donme) gelismis
 geometri editorundeki yerlesim ve donme grubundadir. Bolum yalnizca gelismis
 modda (uygunluk.parca_turleri()["tambur"]) ya da spec'te tambur varken gorunur.

 AD DEGISIMI geometri.ad_degistir(spec, "tambur", eski, yeni) ile: agactaki
 bilesen basvurulari da guncellenir; cakisan ad (her kutuphane bolumu ve
 malzemeler) reddedilir. Kullanilan tambur silinmeden once onay sorulur.
 Duzenleme mevcut _kaydet kalibina uyar (self.spec yerinde yazilir).
"""

from PySide6 import QtCore, QtWidgets

from cekirdek import geometri, uygunluk
from cekirdek.ceviri import N_, _
from cekirdek.geometri.yol_metni import okunur
from arayuz import bilesenler as bl
from arayuz import sekme_duzen as sd
from arayuz.ortak import ipucu, sayi
from arayuz.cubuk.malzeme_kutusu import MalzemeKutusu
from arayuz.cubuk.parca_islemleri import ad_hatasi, benzersiz_ad, rol_listesi, rol_malzemesi

# Yeni tamburun varsayilan olculeri (cm, derece): emici yay 120°, ic yaricap
# yaricapin %75'i (docs/GEOMETRI_MODELI.md ornegi 6.0 / 4.5).
VARSAYILAN_TAMBUR = {"yaricap": 6.0, "emici_ic_yaricap": 4.5, "emici_aci": 120.0}
_IC_PAY = 1e-3                    # emici ic yaricapi < yaricap (cm)
_ROL = QtCore.Qt.UserRole


def tambur_bul(spec, ad):
    return next((t for t in spec.get("tamburlar") or [] if t.get("ad") == ad), None)


def tambur_kullanimlari(spec, ad):
    """Agacta 'ad' tamburuna basvuran yerlerin okunur metinleri."""
    from cekirdek.geometri.basvuru import basvurular
    return [okunur(b.yol) for b in basvurular(spec) if b.tur == "tambur" and b.ad == ad]


def tambur_sablonu(spec, ad):
    """YENI tambur tanimi: govde yapisal, emici emici rolunden (yoksa None)."""
    t = dict(VARSAYILAN_TAMBUR, ad=ad)
    t["govde_malzeme"] = rol_malzemesi(spec, "yapisal")
    t["emici_malzeme"] = rol_malzemesi(spec, "emici")
    return t


def tambur_bolumu_gerekli(spec):
    return bool(uygunluk.parca_turleri(spec).get("tambur") or spec.get("tamburlar"))


class TamburFormuMixin(object):
    """Tamburlar listesi (sol) ve secili tamburun formu (sag yigin)."""

    # ------------------------------------------------------------------
    # kurulum
    # ------------------------------------------------------------------
    def _tambur_karti(self):
        self.t_liste = QtWidgets.QListWidget()
        self.t_liste.setAccessibleName(_("Tamburlar"))
        self.t_liste.currentRowChanged.connect(self._tambur_secim_degisti)
        self.d_tambur = bl.ikincil_dugme(_("Tambur"), "plus")
        self.d_tambur.setToolTip(_("Kontrol tamburu tanımı ekler; gelişmiş geometri "
                                   "editöründeki yerleşimler bu kütüphaneden seçer."))
        self.d_tambur_sil = bl.tehlikeli_dugme(_("Sil"), "trash")
        self.d_tambur.clicked.connect(self.tambur_ekle)
        self.d_tambur_sil.clicked.connect(self._tambur_sil)
        self.tambur_karti = bl.Kart(_("Tamburlar"))
        self.tambur_karti.ekle(self.t_liste, 1)
        self.tambur_karti.ekle(sd.satir(self.d_tambur, self.d_tambur_sil))
        return self.tambur_karti

    def _tambur_sayfa(self):
        w = QtWidgets.QWidget()
        self.t_ad = QtWidgets.QLineEdit()
        self.t_ad.editingFinished.connect(self._tambur_ad_degisti)
        self.t_ad_hata = self._hata_etiketi()
        self.t_yaricap = sayi(6.0, 4, 0.01, 1e4, 0.1, "cm")
        self.t_ic = sayi(4.5, 4, 0.0, 1e4, 0.1, "cm")
        self.t_aci = sayi(120.0, 2, 1.0, 360.0, 5.0, "°")
        self.t_govde_yeri = QtWidgets.QHBoxLayout()
        self.t_emici_yeri = QtWidgets.QHBoxLayout()
        self.t_govde = self.t_emici = None
        self.t_eksik = self._hata_etiketi()
        for k in (self.t_yaricap, self.t_ic, self.t_aci):
            k.valueChanged.connect(self._tambur_kaydet)
        f = sd.form()
        f.addRow(_("Ad"), self.t_ad)
        f.addRow("", self.t_ad_hata)
        f.addRow(_("Yarıçap"), self.t_yaricap)
        f.addRow(_("Gövde malzemesi"), self.t_govde_yeri)
        f.addRow(_("Emici malzemesi"), self.t_emici_yeri)
        f.addRow(_("Emici iç yarıçapı"), self.t_ic)
        f.addRow(_("Emici yayı"), self.t_aci)
        kart = bl.Kart(_("Kontrol tamburu"), aciklama=_(
            "Dönen silindir; çevresinin bir yayı emicidir. Emici yay iç yarıçaptan "
            "dış yarıçapa uzanır (iç yarıçap 0: dolu dilim). Dönme 0° emici kora "
            "bakar (daldırılmış), 180° dışa bakar (çekilmiş)."))
        kart.govde.addLayout(f)
        kart.ekle(self.t_eksik)
        kart.ekle(ipucu(_("Tamburu yerleştirmek için Geometri sayfasında gelişmiş "
                          "editörü açın, bir yerleşim ekleyin ve içerik olarak bu "
                          "tamburu seçin. Dönme, yerleşimin grubundadır.")))
        d = sd.sayfa_duzeni(w, dolgu=False)
        d.addWidget(kart)
        d.addStretch(1)
        return w

    def _tambur_kutusu(self, yer, kutu):
        while yer.count():
            eski = yer.takeAt(0).widget()
            if eski is not None:
                eski.hide()
                eski.setParent(None)
                eski.deleteLater()
        yer.addWidget(kutu, 1)
        kutu.currentIndexChanged.connect(self._tambur_kaydet)
        return kutu

    # ------------------------------------------------------------------
    # doldurma / secim
    # ------------------------------------------------------------------
    def _tamburlari_doldur(self, onceki=None):
        """Listeyi doldurur; 'onceki' adli tambur varsa onu secer (True doner)."""
        self.tambur_karti.setVisible(tambur_bolumu_gerekli(self.spec))
        eski = self.t_liste.blockSignals(True)
        try:
            self.t_liste.clear()
            for t in self.spec.get("tamburlar") or []:
                oge = QtWidgets.QListWidgetItem(t.get("ad") or "")
                oge.setData(_ROL, t.get("ad"))
                self.t_liste.addItem(oge)
        finally:
            self.t_liste.blockSignals(eski)
        self.d_tambur.setEnabled(bool(self.spec.get("malzemeler")))
        self.d_tambur_sil.setEnabled(False)
        if onceki is not None and tambur_bul(self.spec, onceki) is not None:
            self._tambur_sec(onceki)
            return True
        return False

    def _tambur_secili(self):
        oge = self.t_liste.currentItem()
        return oge.data(_ROL) if oge is not None and oge.isSelected() else None

    def _tambur_sec(self, ad):
        for i in range(self.t_liste.count()):
            if self.t_liste.item(i).data(_ROL) == ad:
                self.t_liste.setCurrentRow(i)
                self.t_liste.item(i).setSelected(True)
                self._tambur_secim_degisti(i)
                return

    def _tambur_secim_degisti(self, satir):
        if satir < 0:
            return
        ad = self.t_liste.item(satir).data(_ROL)
        t = tambur_bul(self.spec, ad)
        if t is None:
            return
        eski = self.liste.blockSignals(True)
        self.liste.setCurrentRow(-1)
        self.liste.blockSignals(eski)
        self.d_kopya.setEnabled(False)
        self.d_sil.setEnabled(False)
        self.d_tambur_sil.setEnabled(True)
        onceki = self._yukleniyor
        self._yukleniyor = True
        try:
            self._tambur_formu_doldur(t)
        finally:
            self._yukleniyor = onceki
        self.yigin.setCurrentWidget(self.tambur_sayfa)

    def _tambur_secimini_birak(self):
        eski = self.t_liste.blockSignals(True)
        self.t_liste.setCurrentRow(-1)
        self.t_liste.clearSelection()
        self.t_liste.blockSignals(eski)
        self.d_tambur_sil.setEnabled(False)

    def _tambur_formu_doldur(self, t):
        s = self.spec
        self.t_ad.setText(t.get("ad") or "")
        self._hata_goster(self.t_ad_hata, "")
        self.t_yaricap.setValue(float(t.get("yaricap") or 0.0))
        self._ic_siniri()
        self.t_ic.setValue(float(t.get("emici_ic_yaricap") or 0.0))
        self.t_aci.setValue(float(t.get("emici_aci") or VARSAYILAN_TAMBUR["emici_aci"]))
        self.t_govde = self._tambur_kutusu(self.t_govde_yeri, MalzemeKutusu(
            s, t.get("govde_malzeme"), rol_listesi(s, "yapisal") + rol_listesi(s, "moderator"),
            bos=False))
        self.t_emici = self._tambur_kutusu(self.t_emici_yeri, MalzemeKutusu(
            s, t.get("emici_malzeme"), rol_listesi(s, "emici"), bos=False))
        self._tambur_eksik(t)

    def _ic_siniri(self):
        self.t_ic.setMaximum(max(self.t_yaricap.value() - _IC_PAY, 0.0))

    def _tambur_eksik(self, t):
        eksik = [_(a) for k, a in (("govde_malzeme", N_("gövde")),
                                           ("emici_malzeme", N_("emici")))
                 if not t.get(k)]
        self._hata_goster(self.t_eksik, _(
            "Malzemesi seçilmemiş: {eksik}. Uygun malzeme yoksa önce Malzemeler "
            "sekmesinden ekleyin.").format(eksik=", ".join(eksik)) if eksik else "")

    # ------------------------------------------------------------------
    # duzenleme
    # ------------------------------------------------------------------
    def _tambur_kaydet(self, *_a):
        if self._yukleniyor:
            return
        t = tambur_bul(self.spec, self._tambur_secili())
        if t is None:
            return
        self._ic_siniri()
        t["yaricap"] = self.t_yaricap.value()
        t["emici_ic_yaricap"] = self.t_ic.value()
        t["emici_aci"] = self.t_aci.value()
        if self.t_govde is not None:
            t["govde_malzeme"] = self.t_govde.currentData()
        if self.t_emici is not None:
            t["emici_malzeme"] = self.t_emici.currentData()
        self._tambur_eksik(t)
        self.bildir()

    def _tambur_ad_hatasi(self, yeni, eski):
        hata = ad_hatasi(self.spec, yeni, eski)
        if hata is None and yeni != eski:
            try:
                geometri.ad_degistir(self.spec, "tambur", eski, yeni)
            except (KeyError, ValueError) as e:
                hata = str(e)
        return hata

    def _tambur_ad_degisti(self):
        eski = self._tambur_secili()
        yeni = self.t_ad.text().strip()
        if eski is None or yeni == eski:
            self._hata_goster(self.t_ad_hata, "")
            return
        hata = self._tambur_ad_hatasi(yeni, eski)
        if hata:
            self.t_ad.setText(eski)
            self._hata_goster(self.t_ad_hata, _("{hata} Ad değiştirilmedi.").format(hata=hata))
            return
        yeni_spec = geometri.ad_degistir(self.spec, "tambur", eski, yeni)
        for k, v in yeni_spec.items():             # editor sozlesmesi: yerinde
            self.spec[k] = v
        self.spec_yukle(self.spec)
        self._tambur_sec(yeni)
        self.degisti.emit("genel")                 # geometri sayfasi da tazelensin

    def tambur_ekle(self):
        if not self.spec.get("malzemeler"):
            return None
        ad = benzersiz_ad(self.spec, "tambur")
        self.spec.setdefault("tamburlar", []).append(tambur_sablonu(self.spec, ad))
        self.spec_yukle(self.spec)
        self._tambur_sec(ad)
        self.bildir()
        return ad

    def _tambur_sil(self):
        ad = self._tambur_secili()
        if ad is None:
            return
        yerler = tambur_kullanimlari(self.spec, ad)
        if yerler and not self._onay_al(
                _("Tambur kullanılıyor"),
                _("'{ad}' şurada kullanılıyor: {yerler}.\n\nSilinirse bu yerler tanımsız bir "
                  "tambura işaret eder ve doğrulama hata verir. Silinsin mi?"
                  ).format(ad=ad, yerler="; ".join(yerler))):
            return
        self.spec["tamburlar"] = [t for t in self.spec.get("tamburlar") or []
                                  if t.get("ad") != ad]
        self._tambur_secimini_birak()
        self.spec_yukle(self.spec)
        self.bildir()
