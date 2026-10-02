# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_demet.py  --  Demet (kafes / lattice) tanimlari ve harita editoru
================================================================================
 YERLESIM (arayuz/demet/yerlesim.py; maketler/demet_*.png)
   Sol  : "Izgara" karti -- harita kalan butun alani alir (17x17 kaydirmasiz)
   Sag  : "Demetler", "Parca paleti", "Demet" (ozellikler) kartlari + Gelismis

 KULLANICI HARF GORMEZ (arayuz/izgara.py)
   Paletten bir parca secilir (firca) ve izgarada tiklanir ya da basili
   tutup SURUKLENIR; sag tik o hucredeki parcayi firca yapar. Spec yine
   harf haritasi + anahtar tutar: harfler kayitta otomatik atanir
   (izgara.adlardan_harita) ve var olan harfler korunur -- dosya bicimi
   degismez, eski dosyalar birebir geri yazilir.

 YALNIZCA ANLAMLI OLAN SUNULUR (saf kurallar: arayuz/demet/demet_islemleri.py)
   Palet   : cubuklar; AYNI tipte ve dongu kurmayan ic demetler (kendisi,
             onu iceren demet, altigen icinde kare ya da tersi cikmaz);
             plaka yalnizca plaka modelinde ve kare demette; malzeme
             hucresi olarak yalnizca sogutucu/moderator (Gelismis: hepsi +
             Bos). Haritada ZATEN gecen her sey her zaman listelenir.
   Tip     : "Kare demet" / "Altigen demet" ile belirlenir; sonradan
             degismez (tip degisimi haritayi yok ediyordu). Tam kor (kare
             kor haritasi) modelinde altigen demet sunulmaz.
   Adim    : alt siniri haritadaki en buyuk cubuk dis capi / plaka ya da ic
             demet olcusu (dosyadaki daha kucuk deger sessizce buyutulmez).
   Dis dolgu: kare demet tek demet modelinin kendisiyse (sinir = demet
             zarfi) hic kullanilmaz -> gizli (degeri silinmez).
   Varsayilan firca haritada EN SIK gecen parca.
================================================================================
"""

import copy
from collections import Counter

from PySide6 import QtCore, QtWidgets

from cekirdek import altigen, sema
from cekirdek.ceviri import _, _n
from arayuz import izgara
from arayuz import sekme_duzen as sd
from arayuz.ortak import SekmeTabani, renk_simgesi
from arayuz.sekme_cubuk import (ad_hatasi, benzersiz_ad, parca_adini_degistir,
                                parca_kullanimlari, _renk)
from arayuz.cubuk.malzeme_kutusu import MalzemeKutusu
from arayuz.cubuk.parca_islemleri import rol_listesi

# Bolunen parcalar (Dalga 2 / Ajan 7): eski ad alani aynen korunur.
from arayuz.demet.demet_islemleri import (  # noqa: F401
    TUR_ADI, tur_adi, demet_turleri, _harita_adlari, iceriyor, ic_demet_adaylari, palet_izinli,
    palet_listesi, en_sik_parca, _plaka_olcusu, gerekli_adim, dis_dolgu_anlamli,
    _yakit_cubugu, yeni_demet)
from arayuz.demet.yerlesim import YerlesimMixin  # noqa: F401
from arayuz.demet.kilif import KilifMixin


def _tip_ozeti(d):
    """Listede demet adinin yanindaki tip/boyut ozeti ("kare 17×17", "altıgen, 7 halka")."""
    if d.get("tur") == "altigen":
        halka = int(d.get("halka_sayisi") or 1)
        return _n("altıgen, {n} halka", "altıgen, {n} halka", halka).format(n=halka)
    nx, ny = (d.get("boyut") or [1, 1])[:2]
    return _("kare {nx}×{ny}").format(nx=int(nx), ny=int(ny))


# ============================================================================
# sekme
# ============================================================================

class DemetSekmesi(YerlesimMixin, KilifMixin, SekmeTabani):
    """Demet listesi + boyanabilir kare/altigen harita + parca paleti."""

    KONU = "demet"
    oge_secildi = QtCore.Signal()      # onizleme kapsami (v3 K5): secili demet degisti

    def __init__(self, parent=None):
        super().__init__(parent)
        self._firca_demeti = None      # firca hangi demet icin secildi
        self._yerlesim_kur()           # arayuz/demet/yerlesim.py
        self.adim.valueChanged.connect(self._kaydet)
        self.yonelim.currentIndexChanged.connect(self._yonelim_degisti)
        self.nx.valueChanged.connect(self._boyut_degisti)
        self.ny.valueChanged.connect(self._boyut_degisti)
        self.halka.valueChanged.connect(self._halka_degisti)

    # ==================================================================
    def doldur(self):
        secili = self._secili_ad()
        self.liste.blockSignals(True)
        try:
            self.liste.clear()
            renk = {o[0]: o[2] for o in izgara.palet_ogeleri(self.spec, turler=("demet",))}
            for d in self.spec.get("demetler", []):
                oge = QtWidgets.QListWidgetItem(renk_simgesi(renk.get(d["ad"])),
                                                "%s  · %s" % (d["ad"], _tip_ozeti(d)))
                oge.setData(QtCore.Qt.UserRole, d["ad"])
                self.liste.addItem(oge)
            hedef = 0
            for i in range(self.liste.count()):
                if self.liste.item(i).data(QtCore.Qt.UserRole) == secili:
                    hedef = i
            if self.liste.count():
                self.liste.setCurrentRow(hedef)
        finally:
            self.liste.blockSignals(False)
        satir = max(self.liste.sizeHintForRow(0), self.liste.fontMetrics().height() + 4)
        self.liste.setFixedHeight(min(max(self.liste.count(), 1), 5) * (satir + 2)
                                  + 2 * self.liste.frameWidth() + 2)
        self._eylemleri_guncelle()
        self._secim_degisti(self.liste.currentRow())

    def _eylemleri_guncelle(self):
        turler = demet_turleri(self.spec)
        cubuk_var = bool(self.spec.get("cubuklar"))
        self.d_kare.setVisible("kare" in turler)
        self.d_hex.setVisible("altigen" in turler)
        ekleme_ipucu = {
            "kare": _("Kare demet ekler; çubukları paletten seçip ızgaraya yerleştirirsiniz."),
            "altigen": _("Altıgen demet ekler; çubukları paletten seçip ızgaraya "
                         "yerleştirirsiniz.")}
        for d, tur in ((self.d_kare, "kare"), (self.d_hex, "altigen")):
            d.setEnabled(cubuk_var)
            d.setToolTip(ekleme_ipucu[tur] if cubuk_var else
                         _("Önce Parçalar sekmesinde en az bir çubuk tanımlayın."))
        secili = self._secili() is not None
        self.d_kopya.setEnabled(secili)
        self.d_sil.setEnabled(secili)
        # Demet kullanmayan modelde (pin hucre, plaka) sekme gizlidir ama yine
        # yuklenir: tip listesi bos olabilir.
        self._bos_tipi = turler[0] if turler else None
        if not turler:
            self.bos.ayarla(_("Bu modelde demet kullanılmıyor"),
                            _("Bu kor türü demet içermez. Demet gerekiyorsa kor türünü "
                              "model başlığındaki “Türü değiştir…” ile değiştirin."), "")
        elif not cubuk_var:
            self.bos.ayarla(_("Önce çubuk gerekli"),
                            _("Demet, Parçalar sekmesinde tanımlanan çubuklardan kurulur. "
                              "Önce bir yakıt çubuğu ekleyin."), "")
        else:
            self.bos.ayarla(_("Henüz demet yok"),
                            _("Bir demet ekleyin; çubukları sağdaki paletten seçip ızgaraya "
                              "tıklayarak ya da sürükleyerek yerleştirin."),
                            "+ " + tur_adi(self._bos_tipi))

    def _onay_al(self, baslik_, metin):
        """Veri silen islemler icin onay. Testler bunu degistirir (modal acilmaz)."""
        cevap = QtWidgets.QMessageBox.question(
            self, baslik_, metin,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)
        return cevap == QtWidgets.QMessageBox.Yes

    def _bilgi(self, baslik_, metin):
        """Bilgi mesaji (testler degistirir)."""
        QtWidgets.QMessageBox.information(self, baslik_, metin)

    def _geri_al_kutu(self, kutu, deger):
        """Reddedilen degisiklikte kutuyu sinyal islemeden eski degere dondurur."""
        eski = self._yukleniyor
        self._yukleniyor = True
        try:
            if isinstance(kutu, QtWidgets.QComboBox):
                kutu.setCurrentIndex(max(kutu.findData(deger), 0))
            else:
                kutu.setValue(deger)
        finally:
            self._yukleniyor = eski

    def _temizle(self):
        """Demet secili degil: harita yerine bos durum; ozellikler devre disi ve gizli."""
        self.harita_yigin.setCurrentWidget(self.bos)
        for w in (self.ozellik, self.palet_kutu, self.gelismis, self.kilif_karti):
            w.setEnabled(False)
            w.setVisible(False)
        self._bosluk.setVisible(True)
        self.ad.clear()
        self.kare_izgara.yukle([])
        self.hex_izgara.yukle([], 0)
        self.ozet.setText("-")

    def _secili_ad(self):
        oge = self.liste.currentItem()
        return oge.data(QtCore.Qt.UserRole) if oge else None

    def _secili(self):
        ad = self._secili_ad()
        return sema.demet_bul(self.spec, ad) if ad and self.spec else None

    def _izgara(self, d=None):
        d = d or self._secili()
        return self.hex_izgara if d is not None and d.get("tur") == "altigen" \
            else self.kare_izgara

    def secili_oge(self):
        """Onizleme kapsami (K5): secili demetin adi ya da None."""
        return self._secili_ad()

    def _secim_degisti(self, _satir):
        d = self._secili()
        self.oge_secildi.emit()
        self.d_kopya.setEnabled(d is not None)
        self.d_sil.setEnabled(d is not None)
        if d is None:
            self._temizle()
            return
        for w in (self.ozellik, self.palet_kutu, self.gelismis, self.kilif_karti):
            w.setEnabled(True)
            w.setVisible(True)
        self._bosluk.setVisible(False)
        eski = self._yukleniyor
        self._yukleniyor = True
        try:
            hex_mi = d.get("tur") == "altigen"
            self.oz_baslik.setText(tur_adi("altigen" if hex_mi else "kare"))
            self.ad.setText(d["ad"])
            self.ad_hata.setVisible(False)
            self._adim_siniri(d)
            self.adim.setValue(d["adim"])
            self.nx.setValue((d.get("boyut") or [1, 1])[0])
            self.ny.setValue((d.get("boyut") or [1, 1])[1])
            self.halka.setValue(d.get("halka_sayisi") or 7)
            self.yonelim.setCurrentIndex(max(self.yonelim.findData(d.get("yonelim", "y")), 0))
            for w in (self.e_kare_boyut, self.w_kare_boyut):
                w.setVisible(not hex_mi)
            for w in (self.e_halka, self.halka, self.halka_secim, self.d_halka_doldur,
                      self.e_yonelim, self.yonelim):
                w.setVisible(hex_mi)
            self._dis_doldur(d)
            self._kilif_doldur(d)
            self._halka_secenekleri(d)
            self._harita_doldur(d)
            self._ozet_guncelle(d)
        finally:
            self._yukleniyor = eski

    # ==================================================================
    def _dis_doldur(self, d):
        while self._dis_duzen.count():
            w = self._dis_duzen.takeAt(0).widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        yakit = set(rol_listesi(self.spec, "yakit"))
        adaylar = [m["ad"] for m in self.spec.get("malzemeler", []) if m["ad"] not in yakit]
        self.dis = MalzemeKutusu(self.spec, d.get("dolgu_disi"), adaylar, bos=True,
                                 rol_goster=False)
        self.dis.currentIndexChanged.connect(self._kaydet)
        self._dis_duzen.addWidget(self.dis, 1)
        anlamli = dis_dolgu_anlamli(self.spec, d)
        self.e_dis.setVisible(anlamli)
        self._dis_yer.setVisible(anlamli)

    def _halka_secenekleri(self, d):
        """Halkayi doldur: merkezden disa numaralanir (merkez, 1. halka ...)."""
        self.halka_secim.clear()
        if d.get("tur") != "altigen":
            return
        n = d.get("halka_sayisi") or 1
        for k in range(n):
            if k == 0:
                metin = _("Merkez hücre")
            else:
                metin = _n("{k}. halka · {n} hücre", "{k}. halka · {n} hücre",
                           6 * k).format(k=k, n=6 * k)
                if k == n - 1:
                    metin = _("{halka} (en dış)").format(halka=metin)
            # izgara.halkayi_doldur DISTAN ICE indeks kullanir.
            self.halka_secim.addItem(metin, n - 1 - k)
        self.halka_secim.setCurrentIndex(self.halka_secim.count() - 1)

    def _adim_siniri(self, d):
        """Adimin alt siniri: haritadaki en buyuk icerik (dosyadaki daha kucuk
        deger sessizce buyutulmez -- dogrulama onu hata olarak bildirir)."""
        gerekli, sebep = gerekli_adim(self.spec, d)
        alt = max(0.0001, min(gerekli, float(d.get("adim") or gerekli or 0.0001)))
        eski = self.adim.blockSignals(True)
        try:
            self.adim.setMinimum(alt)
        finally:
            self.adim.blockSignals(eski)
        self.adim.setToolTip(
            _("Komşu hücre merkezleri arası uzaklık (pitch).\nEn az {d:.5f} cm: {sebep}."
              ).format(d=gerekli, sebep=sebep) if gerekli else
            _("Komşu hücre merkezleri arası uzaklık (pitch)."))

    def _palet_yenile(self, d=None, firca=None):
        d = d or self._secili()
        if d is None:
            return
        ogeler = palet_listesi(self.spec, d, self.tum_malzemeler.isChecked())
        adlar = _harita_adlari(d)
        if firca is None:
            onceki = self.palet.secili() if self._firca_demeti == d["ad"] else None
            firca = onceki if onceki in [o[0] for o in ogeler] else en_sik_parca(adlar)
        self._firca_demeti = d["ad"]
        sigmayan = ic_demet_adaylari(self.spec, d)[1]
        self.palet_notu.setText(
            _("Adıma sığmayan iç demetler: {adlar}").format(adlar=", ".join(sigmayan))
            if sigmayan else "")
        self.palet_notu.setToolTip(
            _("Bir demeti iç demet olarak yerleştirmek için adım en az o demetin "
              "ölçüsü kadar olmalı.") if sigmayan else "")
        self.palet_notu.setVisible(bool(sigmayan))
        self.palet.parcalari_ayarla(ogeler, secili=firca)
        self._palet_boyu()
        renkler = self.palet.renkler()
        for iz in (self.kare_izgara, self.hex_izgara):
            iz.renkleri_ayarla(renkler)
            iz.firca_ayarla(self.palet.secili())

    def _harita_doldur(self, d):
        adlar = _harita_adlari(d)
        self._palet_yenile(d)
        renkler = self.palet.renkler()
        if d.get("tur") == "altigen":
            self.hex_izgara.yukle(adlar, d.get("halka_sayisi") or len(adlar),
                                  d.get("yonelim", "y"), renkler)
            self.harita_yigin.setCurrentWidget(self.hex_izgara)
        else:
            self.kare_izgara.yukle(adlar, renkler)
            self.harita_yigin.setCurrentWidget(self.kare_izgara)

    def _ozet_guncelle(self, d):
        if d.get("tur") == "altigen":
            halka = d.get("halka_sayisi") or 1
            gx, gy = altigen.kapsayan_olcu(halka, d["adim"], d.get("yonelim", "y"))
            self.ozet.setText(_n("{gx:.3f} × {gy:.3f} cm · {n} hücre, {h} halka",
                                 "{gx:.3f} × {gy:.3f} cm · {n} hücre, {h} halka", halka
                                 ).format(gx=gx, gy=gy, n=altigen.toplam_hucre(halka), h=halka))
        else:
            nx, ny = d["boyut"]
            self.ozet.setText(_n("{gx:.3f} × {gy:.3f} cm · {n} hücre",
                                 "{gx:.3f} × {gy:.3f} cm · {n} hücre", nx * ny
                                 ).format(gx=d["adim"] * nx, gy=d["adim"] * ny, n=nx * ny))

    # ==================================================================
    # firca ve boyama
    # ==================================================================
    def _firca_degisti(self, ad):
        for iz in (self.kare_izgara, self.hex_izgara):
            iz.firca_ayarla(ad)

    def _firca_istendi(self, ad):
        if not self.palet.sec(ad):
            # Palette olmayan (or. yeni gizlenen) parca: listeye alinsin.
            self._palet_yenile(firca=ad)

    def _harita_kaydet(self):
        """Bir boyama darbesi bitti: adlar -> harf haritasi (harfler korunur)."""
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None:
            return
        adlar = self._izgara(d).adlar()
        try:
            harita, anahtar = izgara.adlardan_harita(adlar, d.get("anahtar"), d.get("harita"))
        except ValueError as e:
            self._bilgi(_("Çok fazla parça"), str(e))
            self._harita_doldur(d)
            return
        d["harita"], d["anahtar"] = harita, anahtar
        self._adim_siniri(d)
        self.bildir()

    def _tumunu_doldur(self):
        ad = self.palet.secili()
        if self._secili() is None or ad is None:
            return
        self._izgara().tumunu_doldur(ad)          # degisti -> _harita_kaydet

    def _halka_doldur(self):
        d = self._secili()
        ad = self.palet.secili()
        ix = self.halka_secim.currentData()
        if d is None or d.get("tur") != "altigen" or ad is None or ix is None:
            return
        self.hex_izgara.halkayi_doldur(int(ix), ad)

    # ==================================================================
    # ozellik degisiklikleri
    # ==================================================================
    def _kaydet(self, *_):
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None:
            return
        adim_degisti = d.get("adim") != self.adim.value()
        d["adim"] = self.adim.value()
        if self.dis is not None:
            d["dolgu_disi"] = self.dis.currentData()
        self._ozet_guncelle(d)
        if adim_degisti:
            self._palet_yenile(d)          # sigan ic demetler degisebilir
        self.bildir()

    def _yonelim_degisti(self, *_):
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None:
            return
        d["yonelim"] = self.yonelim.currentData()
        self._yukleniyor = True
        try:
            self._harita_doldur(d)
            self._ozet_guncelle(d)
        finally:
            self._yukleniyor = False
        self.bildir()

    def _varsayilan_harf(self, d):
        """Buyutmede yeni hucreler haritada EN SIK gecen parcayla dolar."""
        sayac = Counter(h for satir in d.get("harita") or [] for h in satir)
        if sayac:
            return sayac.most_common(1)[0][0]
        harfler = sorted((d.get("anahtar") or {}).keys())
        return harfler[0] if harfler else izgara.BOS_HARF

    def _boyut_degisti(self, *_arg):          # '_' gettext'i golgelemesin
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None or d.get("tur") == "altigen":
            return
        nx, ny = self.nx.value(), self.ny.value()
        eski_nx, eski_ny = (d.get("boyut") or [nx, ny])[:2]
        if (nx, ny) == (eski_nx, eski_ny):
            return
        if nx < eski_nx or ny < eski_ny:
            # Kucultme haritanin sag/alt kismini KIRPAR; eskiden sessizdi.
            if not self._onay_al(
                    _("Harita küçülüyor"),
                    _("Demet {eski_nx}×{eski_ny}'den {nx}×{ny}'ye küçülüyor: haritanın "
                      "sağ/alt kısmındaki hücreler silinecek (büyütmek onları geri "
                      "getirmez).\n\nDevam edilsin mi?").format(
                          eski_nx=int(eski_nx), eski_ny=int(eski_ny), nx=nx, ny=ny)):
                self._geri_al_kutu(self.nx, eski_nx)
                self._geri_al_kutu(self.ny, eski_ny)
                return
        eski = d.get("harita") or []
        varsayilan = self._varsayilan_harf(d)
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
        self._liste_metni(d)
        self.bildir()

    def _halka_degisti(self, *_arg):
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None or d.get("tur") != "altigen":
            return
        halka = self.halka.value()
        eski_halka = d.get("halka_sayisi") or halka
        if halka == eski_halka:
            return
        if halka < eski_halka:
            # Halka azaltmak DIS halkalari siler; eskiden sessizdi.
            silinen = eski_halka - halka
            if not self._onay_al(
                    _("Halka sayısı azalıyor"),
                    _n("Halka sayısı {eski}'den {yeni}'ye iniyor: dıştaki {n} halka silinecek "
                       "(artırmak onları geri getirmez).\n\nDevam edilsin mi?",
                       "Halka sayısı {eski}'den {yeni}'ye iniyor: dıştaki {n} halka silinecek "
                       "(artırmak onları geri getirmez).\n\nDevam edilsin mi?",
                       silinen).format(eski=eski_halka, yeni=halka, n=silinen)):
                self._geri_al_kutu(self.halka, eski_halka)
                return
        d["halka_sayisi"] = halka
        d["boyut"] = [halka, halka]
        d["harita"] = altigen.harita_yeniden_boyutlandir(
            d.get("harita"), halka, self._varsayilan_harf(d))
        self._yukleniyor = True
        try:
            self._halka_secenekleri(d)
            self._harita_doldur(d)
            self._ozet_guncelle(d)
        finally:
            self._yukleniyor = False
        self._liste_metni(d)
        self.bildir()

    def _liste_metni(self, d):
        oge = self.liste.currentItem()
        if oge is None:
            return
        oge.setText("%s  · %s" % (d["ad"], _tip_ozeti(d)))

    # ==================================================================
    # liste islemleri
    # ==================================================================
    def _sec(self, ad):
        for i in range(self.liste.count()):
            if self.liste.item(i).data(QtCore.Qt.UserRole) == ad:
                self.liste.setCurrentRow(i)
                return

    def komutlar(self):
        return sd.dugme_komutlari(self, _("Demet"), (
            self.d_kare, self.d_hex, self.d_kopya, self.d_sil, self.d_hepsi,
            self.d_halka_doldur))

    def odakla(self, yer):
        """"demet:<ad>" bulgusunda o demeti secer."""
        hedef = sd.yer_adi(yer, "demet")
        if hedef is None:
            return False
        self._sec(hedef[1])
        return self._secili_ad() == hedef[1]

    def _yeni(self, tur):
        """'+ Kare demet' / '+ Altigen demet'. Kontrol ettigi sey mesajiyla ayni."""
        if tur not in demet_turleri(self.spec):
            return None
        if not self.spec.get("cubuklar"):
            self._bilgi(_("Önce çubuk gerekli"),
                        _("Demet kurmadan önce Parçalar sekmesinde en az bir çubuk "
                          "tanımlayın."))
            return None
        ad = benzersiz_ad(self.spec, "demet_altigen" if tur == "altigen" else "demet_kare")
        self.spec.setdefault("demetler", []).append(yeni_demet(self.spec, tur, ad))
        kor = self.spec.get("kor") or {}
        # Tek demet modelinde kor henuz bir demete isaret etmiyorsa bu demet
        # atanir: bos modelde ilk demet eklenince model hemen kurulur.
        if kor.get("tur") == "tek_demet" and (
                not kor.get("demet") or sema.demet_bul(self.spec, kor["demet"]) is None):
            kor["demet"] = ad
        self.spec_yukle(self.spec)
        self._sec(ad)
        self.bildir()
        return ad

    def _kopyala(self):
        d = self._secili()
        if d is None:
            return
        y = copy.deepcopy(d)
        y["ad"] = benzersiz_ad(self.spec, d["ad"])
        self.spec["demetler"].append(y)
        self.spec_yukle(self.spec)
        self._sec(y["ad"])
        self.bildir()

    def _sil(self):
        ad = self._secili_ad()
        if ad is None:
            return
        yerler = parca_kullanimlari(self.spec, ad)
        if yerler and not self._onay_al(
                _("Demet kullanılıyor"),
                _("'{ad}' şurada kullanılıyor: {yerler}.\n\nSilinirse bu yerler tanımsız bir "
                  "demete işaret eder ve doğrulama hata verir. Silinsin mi?"
                  ).format(ad=ad, yerler=", ".join(yerler))):
            return
        self.spec["demetler"] = [d for d in self.spec["demetler"] if d["ad"] != ad]
        self.spec_yukle(self.spec)
        self.bildir()

    def _ad_degisti(self):
        d = self._secili()
        if d is None:
            return
        yeni = self.ad.text().strip()
        eski = d["ad"]
        if yeni == eski:
            self.ad_hata.setVisible(False)
            return
        hata = ad_hatasi(self.spec, yeni, eski)
        if hata:
            self.ad.setText(eski)
            self.ad_hata.setText(_("{hata} Ad değiştirilmedi.").format(hata=hata))
            self.ad_hata.setStyleSheet("color: %s;" % _renk("hata"))
            self.ad_hata.setVisible(True)
            return
        parca_adini_degistir(self.spec, eski, yeni)
        self._firca_demeti = yeni if self._firca_demeti == eski else self._firca_demeti
        self.spec_yukle(self.spec)
        self._sec(yeni)
        self.bildir()
