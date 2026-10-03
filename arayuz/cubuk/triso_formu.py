# -*- coding: utf-8 -*-
"""
 arayuz/cubuk/triso_formu.py  --  TrisoFormuMixin: Parcalar > TRISO kompakt / pebble (Y9)

 TRISO KUTUPHANESI: spec["trisolar"] tanimlari (alanlar cekirdek/triso.py): katmanlar
 (cekirdek, tampon, IPyC, SiC, OPyC: dis yaricap + malzeme), matris, kompakt (yaricap,
 yukseklik) ya da pebble (yakit yaricapi, dis yaricap, kabuk, gaz), paketleme orani,
 yerlesim (rastgele | duzenli) ve tohum. Bolum yalnizca gelismis modda
 (uygunluk.parca_turleri()["triso"]) ya da spec'te TRISO varken gorunur; tanim agacta
 "bilesen" olarak kullanilir. Alt satirda gercek parcacik sayisi ve paketleme orani
 (triso.yerlesim_ozeti) gosterilir. Duzenleme mevcut _kaydet kalibina uyar
 (self.spec yerinde yazilir). Ad degisimi geometri.ad_degistir ile.
"""

from PySide6 import QtCore, QtWidgets

from cekirdek import geometri, triso, uygunluk
from cekirdek.ceviri import N_, _
from cekirdek.geometri.yol_metni import okunur
from cekirdek.gunluk import kaydedici
from arayuz import bilesenler as bl
from arayuz import sekme_duzen as sd
from arayuz.ortak import ipucu, sayi, tamsayi
from arayuz.cubuk.malzeme_kutusu import MalzemeKutusu
from arayuz.cubuk.parca_islemleri import ad_hatasi, benzersiz_ad

_log = kaydedici(__name__)
_ROL = QtCore.Qt.UserRole
_PF_ADIMI = 0.01
_YARICAP_ONDALIK = 5                       # um duyarliginda (cm)
_KATMAN_ADLARI = {"kernel": N_("Çekirdek"), "buffer": N_("Tampon"), "ipyc": N_("İç PyC (IPyC)"),
                  "sic": N_("SiC"), "opyc": N_("Dış PyC (OPyC)")}
_SEKIL_ADLARI = {"kompakt": N_("Kompakt (silindir)"), "pebble": N_("Pebble (küre)")}
_YONTEM_ADLARI = {"rastgele": N_("Rastgele (RSP/CRP)"), "duzenli": N_("Düzenli (basit kübik)")}
_SABLON_ADLARI = {"agr1": N_("AGR-1 kompakt (UCO)"), "htr10": N_("HTR-10 pebble (UO2)")}
_MALZEME_ANAHTARLARI = ("matris_malzeme", "kabuk_malzeme", "dis_malzeme")


def triso_bul(spec, ad):
    return next((t for t in spec.get("trisolar") or [] if t.get("ad") == ad), None)


def triso_kullanimlari(spec, ad):
    """Agacta 'ad' TRISO tanimina basvuran yerlerin okunur metinleri."""
    from cekirdek.geometri.basvuru import basvurular
    return [okunur(b.yol) for b in basvurular(spec) if b.tur == "triso" and b.ad == ad]


def triso_bolumu_gerekli(spec):
    return bool(uygunluk.parca_turleri(spec).get("triso") or spec.get("trisolar"))


def triso_sablonu(spec, anahtar, ad):
    """YENI tanim; malzemeler ad sirasiyla modelin malzemelerinden doldurulur (yoksa None:
    arayuz 'Malzeme secin' diye isaretler)."""
    tum = [m["ad"] for m in spec.get("malzemeler") or []]
    slotlar = list(triso.KATMAN_ADLARI) + ["matris", "kabuk", "dis"]
    secim = {s: next((a for a in tum if a == s or a.startswith(s)), None) for s in slotlar}
    return triso.sablon(anahtar, ad, secim)


class TrisoFormuMixin(object):
    """TRISO listesi (sol) ve secili tanimin formu (sag yigin)."""

    # ------------------------------------------------------------------
    # kurulum
    # ------------------------------------------------------------------
    def _triso_karti(self):
        self.x_liste = QtWidgets.QListWidget()
        self.x_liste.setAccessibleName(_("TRISO tanımları"))
        self.x_liste.currentRowChanged.connect(self._triso_secim_degisti)
        self.d_triso = bl.ikincil_dugme(_("TRISO"), "plus")
        self.d_triso.setToolTip(_("TRISO kompakt ya da pebble tanımı ekler; gelişmiş geometri "
                                  "editöründe bileşen olarak seçilir."))
        self.triso_menusu = QtWidgets.QMenu(self.d_triso)
        for anahtar, ad in _SABLON_ADLARI.items():
            self.triso_menusu.addAction(_(ad), lambda _c=False, a=anahtar: self.triso_ekle(a))
        self.d_triso.setMenu(self.triso_menusu)
        self.d_triso_sil = bl.tehlikeli_dugme(_("Sil"), "trash")
        self.d_triso_sil.clicked.connect(self._triso_sil)
        self.triso_karti = bl.Kart(_("TRISO (kompakt, pebble)"))
        self.triso_karti.ekle(self.x_liste, 1)
        self.triso_karti.ekle(sd.satir(self.d_triso, self.d_triso_sil))
        return self.triso_karti

    def _triso_sayfa(self):
        w = QtWidgets.QWidget()
        self.x_ad = QtWidgets.QLineEdit()
        self.x_ad.editingFinished.connect(self._triso_ad_degisti)
        self.x_ad_hata = self._hata_etiketi()
        self.x_sekil = QtWidgets.QComboBox()
        for anahtar, ad in _SEKIL_ADLARI.items():
            self.x_sekil.addItem(_(ad), anahtar)
        self.x_yaricap = sayi(0.6225, 4, 0.01, 1e3, 0.01, "cm")
        self.x_yukseklik = sayi(2.5, 3, 0.01, 1e4, 0.1, "cm")
        self.x_yakit_yaricap = sayi(2.5, 3, 0.01, 1e3, 0.1, "cm")
        self.x_dis_yaricap = sayi(3.0, 3, 0.01, 1e3, 0.1, "cm")
        self.x_pf = sayi(0.35, 4, 0.0, triso.CRP_SINIRI, _PF_ADIMI, "")
        self.x_pf.setToolTip(_(
            "Hedef paketleme oranı = N·(4/3)πr³ / V_kap. Rastgele: en çok %.2f (CRP sınırı); "
            "düzenli (basit kübik): en çok π/6 = %.4f.") % (triso.CRP_SINIRI, triso.SC_SINIRI))
        self.x_yontem = QtWidgets.QComboBox()
        for anahtar, ad in _YONTEM_ADLARI.items():
            self.x_yontem.addItem(_(ad), anahtar)
        self.x_tohum = tamsayi(1, 0, 10 ** 9, 1)
        self.x_tohum.setToolTip(_("Rastgele paketlemenin tohumu: aynı tohum aynı yerleşimi verir."))
        self.x_katman_yeri = QtWidgets.QFormLayout()
        self.x_katman_kutular = []
        self.x_malzeme_yeri = {a: QtWidgets.QHBoxLayout() for a in _MALZEME_ANAHTARLARI}
        self.x_malzeme_kutu = {}
        self.x_ozet = QtWidgets.QLabel("-")
        self.x_ozet.setWordWrap(True)
        self.x_eksik = self._hata_etiketi()
        self._triso_sinyalleri()
        f = sd.form()
        f.addRow(_("Ad"), self.x_ad)
        f.addRow("", self.x_ad_hata)
        f.addRow(_("Şekil"), self.x_sekil)
        self._x_etiket = {}
        for anahtar, etiket, alan in (("yaricap", _("Kompakt yarıçapı"), self.x_yaricap),
                                      ("yukseklik", _("Kompakt yüksekliği"), self.x_yukseklik),
                                      ("yakit_yaricap", _("Yakıt bölgesi yarıçapı"), self.x_yakit_yaricap),
                                      ("dis_yaricap", _("Pebble dış yarıçapı"), self.x_dis_yaricap)):
            self._x_etiket[anahtar] = QtWidgets.QLabel(etiket)
            f.addRow(self._x_etiket[anahtar], alan)
        for anahtar, etiket in (("matris_malzeme", _("Matris malzemesi")),
                                ("kabuk_malzeme", _("Kabuk malzemesi (pebble)")),
                                ("dis_malzeme", _("Dış gaz (pebble)"))):
            self._x_etiket[anahtar] = QtWidgets.QLabel(etiket)
            f.addRow(self._x_etiket[anahtar], self.x_malzeme_yeri[anahtar])
        f.addRow(_("Paketleme oranı (hedef)"), self.x_pf)
        f.addRow(_("Yerleşim"), self.x_yontem)
        f.addRow(_("Tohum"), self.x_tohum)
        kart = bl.Kart(_("TRISO yakıt"), aciklama=_(
            "TRISO parçacığı es merkezli katmanlardan oluşur (içten dışa: çekirdek, tampon, "
            "IPyC, SiC, OPyC). Parçacıklar kompakt silindirinde ya da pebble'ın yakıt "
            "küresinde paketlenir; kalan hacim matris ile dolar. Kompakt 3B model ister."))
        kart.govde.addLayout(f)
        kart.ekle(self.x_ozet)
        kart.ekle(self.x_eksik)
        katman = bl.Kart(_("Katmanlar"), aciklama=_(
            "Her satır katmanın DIŞ yarıçapı ve malzemesidir; yarıçaplar artmalıdır. En dış "
            "katmanın yarıçapı parçacık yarıçapıdır."))
        katman.govde.addLayout(self.x_katman_yeri)
        d = sd.sayfa_duzeni(w, dolgu=False)
        d.addWidget(kart)
        d.addWidget(katman)
        d.addStretch(1)
        return w

    def _triso_sinyalleri(self):
        for k in (self.x_yaricap, self.x_yukseklik, self.x_yakit_yaricap, self.x_dis_yaricap,
                  self.x_pf, self.x_tohum):
            k.valueChanged.connect(self._triso_kaydet)
        self.x_yontem.currentIndexChanged.connect(self._triso_kaydet)
        self.x_sekil.currentIndexChanged.connect(self._triso_kaydet)

    # ------------------------------------------------------------------
    # doldurma / secim
    # ------------------------------------------------------------------
    def _trisolari_doldur(self, onceki=None):
        """Listeyi doldurur; 'onceki' adli tanim varsa onu secer (True doner)."""
        self.triso_karti.setVisible(triso_bolumu_gerekli(self.spec))
        eski = self.x_liste.blockSignals(True)
        try:
            self.x_liste.clear()
            for t in self.spec.get("trisolar") or []:
                oge = QtWidgets.QListWidgetItem(t.get("ad") or "")
                oge.setData(_ROL, t.get("ad"))
                self.x_liste.addItem(oge)
        finally:
            self.x_liste.blockSignals(eski)
        self.d_triso.setEnabled(bool(self.spec.get("malzemeler")))
        self.d_triso_sil.setEnabled(False)
        if onceki is not None and triso_bul(self.spec, onceki) is not None:
            self._triso_sec(onceki)
            return True
        return False

    def _triso_secili(self):
        oge = self.x_liste.currentItem()
        return oge.data(_ROL) if oge is not None and oge.isSelected() else None

    def _triso_sec(self, ad):
        for i in range(self.x_liste.count()):
            if self.x_liste.item(i).data(_ROL) == ad:
                self.x_liste.setCurrentRow(i)
                self.x_liste.item(i).setSelected(True)
                self._triso_secim_degisti(i)
                return

    def _triso_secim_degisti(self, satir):
        if satir < 0:
            return
        t = triso_bul(self.spec, self.x_liste.item(satir).data(_ROL))
        if t is None:
            return
        for liste in (self.liste, self.t_liste):
            eski = liste.blockSignals(True)
            liste.setCurrentRow(-1)
            liste.clearSelection()
            liste.blockSignals(eski)
        self.d_kopya.setEnabled(False)
        self.d_sil.setEnabled(False)
        self.d_tambur_sil.setEnabled(False)
        self.d_triso_sil.setEnabled(True)
        onceki = self._yukleniyor
        self._yukleniyor = True
        try:
            self._triso_formu_doldur(t)
        finally:
            self._yukleniyor = onceki
        self.yigin.setCurrentWidget(self.triso_sayfa)
        self.oge_secildi.emit()             # onizleme kapsami (K5)

    def _triso_secimini_birak(self):
        eski = self.x_liste.blockSignals(True)
        self.x_liste.setCurrentRow(-1)
        self.x_liste.clearSelection()
        self.x_liste.blockSignals(eski)
        self.d_triso_sil.setEnabled(False)

    def _triso_formu_doldur(self, t):
        self.x_ad.setText(t.get("ad") or "")
        self._hata_goster(self.x_ad_hata, "")
        sekil = t.get("sekil") or "kompakt"
        self.x_sekil.setCurrentIndex(max(self.x_sekil.findData(sekil), 0))
        for kutu, alan, vars_ in ((self.x_yaricap, "yaricap", 0.6225),
                                  (self.x_yukseklik, "yukseklik", 2.5),
                                  (self.x_yakit_yaricap, "yakit_yaricap", 2.5),
                                  (self.x_dis_yaricap, "dis_yaricap", 3.0)):
            kutu.setValue(float(t.get(alan) or vars_))
        self.x_pf.setValue(float(t.get("paketleme") or 0.0))
        self.x_yontem.setCurrentIndex(max(self.x_yontem.findData(t.get("yontem") or "rastgele"), 0))
        self.x_tohum.setValue(int(t.get("tohum") or triso.VARSAYILAN_TOHUM))
        self._triso_malzeme_kutulari(t)
        self._triso_katman_satirlari(t)
        self._triso_gorunurluk(sekil)
        self._triso_bilgi(t)

    def _triso_malzeme_kutulari(self, t):
        self.x_malzeme_kutu = {}
        for anahtar, yer in self.x_malzeme_yeri.items():
            self.x_malzeme_kutu[anahtar] = self._triso_kutusu(
                yer, MalzemeKutusu(self.spec, t.get(anahtar), None, bos=False, rol_goster=False))

    def _triso_kutusu(self, yer, kutu):
        """Malzeme kutusunu yerine koyar (tambur_formu._tambur_kutusu gibi; kaydi TRISO'nundur)."""
        while yer.count():
            eski = yer.takeAt(0).widget()
            if eski is not None:
                eski.hide()
                eski.setParent(None)
                eski.deleteLater()
        yer.addWidget(kutu, 1)
        kutu.currentIndexChanged.connect(self._triso_kaydet)
        return kutu

    def _triso_katman_satirlari(self, t):
        while self.x_katman_yeri.rowCount():
            self.x_katman_yeri.removeRow(0)
        self.x_katman_kutular = []
        for k in t.get("katmanlar") or []:
            r = sayi(float(k.get("r") or 0.0), _YARICAP_ONDALIK, 0.0, 1e3, 0.001, "cm")
            m = MalzemeKutusu(self.spec, k.get("malzeme"), None, bos=False, rol_goster=False)
            r.valueChanged.connect(self._triso_kaydet)
            m.currentIndexChanged.connect(self._triso_kaydet)
            satir = sd.satir(r, m)
            ad = k.get("ad") or ""
            self.x_katman_yeri.addRow(_(_KATMAN_ADLARI.get(ad, ad)), satir)
            self.x_katman_kutular.append((r, m))

    def _triso_gorunurluk(self, sekil):
        kompakt = sekil == "kompakt"
        for a in ("yaricap", "yukseklik"):
            self._x_etiket[a].setVisible(kompakt)
        for a in ("yaricap", "yukseklik"):
            (self.x_yaricap if a == "yaricap" else self.x_yukseklik).setVisible(kompakt)
        for a, w in (("yakit_yaricap", self.x_yakit_yaricap), ("dis_yaricap", self.x_dis_yaricap)):
            self._x_etiket[a].setVisible(not kompakt)
            w.setVisible(not kompakt)
        for a in ("kabuk_malzeme", "dis_malzeme"):
            self._x_etiket[a].setVisible(not kompakt)
            kutu = self.x_malzeme_kutu.get(a)
            if kutu is not None:
                kutu.setVisible(not kompakt)

    def _triso_bilgi(self, t):
        """Ozet satiri (parcacik sayisi, gercek pf) ve eksik malzeme uyarisi."""
        sorun = [m for s, m in triso.sorunlar(t) if s == "hata"]
        if sorun:
            self.x_ozet.setText("")
            self._hata_goster(self.x_eksik, "; ".join(sorun))
            return
        self._hata_goster(self.x_eksik, "")
        try:
            oz = triso.yerlesim_ozeti(t)
        except ValueError as e:
            _log.info("TRISO özeti hesaplanamadı", exc_info=True)
            self._hata_goster(self.x_eksik, str(e))
            return
        metin = _("%d parçacık · gerçek paketleme oranı %.4f (hedef %.4f)") % (
            oz.n, oz.gercek_pf, oz.hedef_pf)
        if oz.adim is not None:
            metin += _(" · kübik adım %.5f cm") % oz.adim
        self.x_ozet.setText(metin)

    # ------------------------------------------------------------------
    # duzenleme
    # ------------------------------------------------------------------
    def _triso_kaydet(self, *_a):
        if self._yukleniyor:
            return
        t = triso_bul(self.spec, self._triso_secili())
        if t is None:
            return
        sekil = self.x_sekil.currentData()
        t["sekil"] = sekil
        t["paketleme"] = self.x_pf.value()
        t["yontem"] = self.x_yontem.currentData()
        t["tohum"] = self.x_tohum.value()
        for alan, kutu in (("yaricap", self.x_yaricap), ("yukseklik", self.x_yukseklik),
                           ("yakit_yaricap", self.x_yakit_yaricap),
                           ("dis_yaricap", self.x_dis_yaricap)):
            t[alan] = kutu.value()
        for anahtar, kutu in self.x_malzeme_kutu.items():
            t[anahtar] = kutu.currentData()
        katmanlar = t.get("katmanlar") or []
        for k, (r, m) in zip(katmanlar, self.x_katman_kutular):
            k["r"], k["malzeme"] = r.value(), m.currentData()
        self._triso_gorunurluk(sekil)
        self._triso_bilgi(t)
        self.bildir()

    def _triso_ad_degisti(self):
        eski = self._triso_secili()
        yeni = self.x_ad.text().strip()
        if eski is None or yeni == eski:
            self._hata_goster(self.x_ad_hata, "")
            return
        hata = ad_hatasi(self.spec, yeni, eski)
        if hata is None:
            try:
                geometri.ad_degistir(self.spec, "triso", eski, yeni)
            except (KeyError, ValueError) as e:
                hata = str(e)
        if hata:
            self.x_ad.setText(eski)
            self._hata_goster(self.x_ad_hata, _("{hata} Ad değiştirilmedi.").format(hata=hata))
            return
        yeni_spec = geometri.ad_degistir(self.spec, "triso", eski, yeni)
        for k, v in yeni_spec.items():             # editor sozlesmesi: yerinde
            self.spec[k] = v
        self.spec_yukle(self.spec)
        self._triso_sec(yeni)
        self.degisti.emit("genel")

    def triso_ekle(self, anahtar="agr1"):
        if not self.spec.get("malzemeler"):
            return None
        ad = benzersiz_ad(self.spec, "agr1" if anahtar == "agr1" else "htr10")
        self.spec.setdefault("trisolar", []).append(triso_sablonu(self.spec, anahtar, ad))
        self.spec_yukle(self.spec)
        self._triso_sec(ad)
        self.bildir()
        return ad

    def _triso_sil(self):
        ad = self._triso_secili()
        if ad is None:
            return
        yerler = triso_kullanimlari(self.spec, ad)
        if yerler and not self._onay_al(
                _("TRISO tanımı kullanılıyor"),
                _("'{ad}' şurada kullanılıyor: {yerler}.\n\nSilinirse bu yerler tanımsız bir "
                  "bileşene işaret eder ve doğrulama hata verir. Silinsin mi?"
                  ).format(ad=ad, yerler="; ".join(yerler))):
            return
        self.spec["trisolar"] = [t for t in self.spec.get("trisolar") or []
                                 if t.get("ad") != ad]
        if not self.spec["trisolar"]:
            self.spec.pop("trisolar")           # bos alan dosyaya yazilmaz
        self._triso_secimini_birak()
        self.spec_yukle(self.spec)
        self.bildir()
