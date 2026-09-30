# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_kor.py  --  Kor: dolgu, harita, yukseklik, sinir kosullari, yansitici
================================================================================
 KOR TURU BURADA DEGISMEZ.
   Tur model basligindaki "Turu degistir..." ile degisir
   (ana_pencere.kor_turunu_degistir -> kor_turu_degistir -> spec_yukle).
   Bu sekme turu yalnizca GOSTERIR ve o turun alanlarini duzenler:
     uygunluk.kor_alanlari(tur)      -> ture ozgu alanlar (cubuk, harita, ...)
     uygunluk.kor_ortak_alanlari()   -> yukseklik / katman / alt-ust sinir
     uygunluk.sinir_secenekleri()    -> her yuzeyde gecerli sinir kosullari
   Gorunmeyen bir alanin degeri spec'e YAZILMAZ ve SILINMEZ.

 YUKSEKLIK TEK SECIMDIR
   "2B (sonsuz yukseklik)" | "3B, tek bolge [H]" | "3B, katmanli".
   Spec karsiliklari: yukseklik None | yukseklik = H | eksenel.var = True
   (katmanlida yukseklik None: gecerli yukseklik katman toplamidir --
   sema.kor_yuksekligi). Eskiden uc ayri denetim vardi (kutu + alan +
   "katmanlara ayir") ve biri digerini sessizce gecersiz kiliyordu.

 DOSYALAR (Dalga 2, Ajan 8: bolme + gorunum; yeni ozellik yok)
   arayuz/kor/yerlesim.py (widget + kart), kor/harita.py (kare harita
   boyama), kor/katmanlar.py (katman tablosu). Bu dosya: doldurma,
   gorunurluk, yukseklik secimi, kayit, tambur durumu.

 KATMAN TABLOSU FIZIKSEL SIRADA
   Spec katmanlari ALTTAN USTE tutar (sema.eksenel_katmanlar). Tablo ise EN
   UST katmani EN USTTE gosterir: satir r <-> spec indeksi n-1-r. Yukari ok
   katmani gercekten yukari (spec'te bir sonraki indekse) tasir.

 KOR HARITASI BOYANIR
   Kare kor haritasi izgara.ParcaPaleti + izgara.KareIzgara ile boyanir;
   harfler arka planda atanir (izgara.adlardan_harita), spec bicimi ayni
   kalir. Boyut (nx, ny) haritadan turetilir; hucre kaybettiren kucultme onay
   ister.
================================================================================
"""

import math

from PySide6 import QtCore, QtWidgets

from cekirdek import sema, uygunluk
from cekirdek.ceviri import _
from arayuz import tema
from arayuz.kor.harita import KorHaritasiMixin
from arayuz.kor.katmanlar import KorKatmanMixin, _BOS_ETIKET
from arayuz.kor.katmanlar import tablo_yuksekligi as _tablo_yuksekligi
from arayuz.kor.yerlesim import KorYerlesimMixin, YUKSEKLIK_MODLARI  # noqa: F401
from arayuz.ortak import SekmeTabani
from cekirdek.gunluk import kaydedici

_log = kaydedici("arayuz.sekme_kor")

# Sinir kosullarinin gorunen adlari (OpenMC anahtar sozcugu parantezde).
SINIR_ADLARI = {
    "reflective": "Yansıtıcı (reflective)",
    "vacuum": "Vakum (vacuum)",
    "white": "Beyaz (white)",
    "periodic": "Periyodik (periodic)",
}
_KABUK_EN_COK_SATIR = 6


def _tur_adi(tur):
    """Kor turunun model basligindaki "Turu degistir..." menusuyle AYNI adi."""
    try:
        from arayuz.ana_pencere import TUR_ADLARI
        return TUR_ADLARI.get(tur, tur or "tanımsız")
    except Exception:                                   # pragma: no cover
        return tur or "tanımsız"


class KorSekmesi(KorYerlesimMixin, KorHaritasiMixin, KorKatmanMixin, SekmeTabani):

    KONU = "kor"
    # "Türü değiştir…" baglantisi: ana pencere model basligindaki tur
    # menusunu acar (tur yalnizca oradan degisir -- tek yol, tek kural).
    tur_degistir_istendi = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tur = None
        self._alanlari_kur()           # arayuz/kor/yerlesim.py
        self._yerlesimi_kur()
        self._sinyalleri_bagla()

    # ------------------------------------------------------------------
    def _onay_al(self, baslik_, metin):
        """Veri silen islemler icin onay. Testler bunu degistirir (modal acilmaz)."""
        cevap = QtWidgets.QMessageBox.question(
            self, baslik_, metin,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)
        return cevap == QtWidgets.QMessageBox.Yes

    def gosterilen_tur(self):
        """Sekmenin gosterdigi kor turu (spec'ten okunur; burada degismez)."""
        return self._tur

    # ------------------------------------------------------------------
    # doldurma
    # ------------------------------------------------------------------
    def doldur(self):
        kor = self.spec["kor"]
        self._tur = kor.get("tur", "tek_cubuk")
        self.tur_etiket.setText(
            "Kor türü: <b>%s</b> — <a href=\"tur\">Türü değiştir…</a> "
            "(model başlığındaki menüyle aynı)" % _tur_adi(self._tur))

        self._kutu_doldur(self.cubuk, [(c["ad"], c["ad"]) for c in self.spec.get("cubuklar", [])],
                          kor.get("cubuk"))
        self._kutu_doldur(self.plaka, [(p["ad"], p["ad"]) for p in self.spec.get("plakalar", [])],
                          kor.get("plaka"))
        self._kutu_doldur(self.demet, [(d["ad"], d["ad"]) for d in self.spec.get("demetler", [])],
                          kor.get("demet"))
        malzemeler = [(sema.BOSLUK, _(_BOS_ETIKET))] + \
                     [(m["ad"], self._malzeme_etiketi(m)) for m in self.spec["malzemeler"]]
        self._malzeme_secenekleri = malzemeler
        self._kutu_doldur(self.yans_mal, malzemeler, (kor.get("yansitici") or {}).get("malzeme"))

        hedefler = [(sema.BOSLUK, _(_BOS_ETIKET))]
        hedefler += [(d["ad"], "demet: %s" % d["ad"]) for d in self.spec.get("demetler", [])]
        hedefler += [(c["ad"], "çubuk: %s" % c["ad"]) for c in self.spec.get("cubuklar", [])]
        hedefler += [(m["ad"], "malzeme: %s" % sema.malzeme_etiketi(m))
                     for m in self.spec["malzemeler"]]
        self._kutu_doldur(self.tb_dolgu, hedefler, kor.get("dolgu"))
        self.tb_kor_r.setValue(kor.get("kor_yaricap") or 16.0)
        t = kor.get("tambur") or {}
        self._baslangic_acisi = t.get("baslangic_acisi", 0.0)
        self.tb_sayi.setValue(int(t.get("sayi") or 0))
        self.tb_r.setValue(t.get("yaricap") or 4.0)
        self.tb_rm.setValue(t.get("merkez_yaricap") or 21.5)
        self.tb_emici_ric.setValue(t.get("emici_ic_yaricap") or 0.0)
        self.tb_aci.setValue(t.get("emici_aci") or 120.0)
        self.tb_donme.setValue(t.get("donme") or 0.0)
        self.tb_donme_kaydirici.setValue(int(round((t.get("donme") or 0.0) * 10)) % 3600)
        self._kutu_doldur(self.tb_govde, malzemeler, t.get("govde_malzeme"))
        self._kutu_doldur(self.tb_emici, malzemeler, t.get("emici_malzeme"))

        self.adim.setValue(kor.get("adim") or 1.26)
        if self._tur == "altigen_kafes":
            self.altigen_harita.yukle(self.spec)
        else:
            self._harita_doldur()
        self._kabuklari_doldur()

        # yukseklik: tek secim
        eks = kor.get("eksenel") or {}
        if eks.get("var"):
            mod = "katmanli"
        elif kor.get("yukseklik"):
            mod = "3B"
        else:
            mod = "2B"
        self.yukseklik_modu.setCurrentIndex(self.yukseklik_modu.findData(mod))
        # Katmanlida alan gecerli yuksekligi (katman toplami) gosterir: "3B, tek
        # bolge"ye donen kullanici ayni yukseklikle devam eder.
        self.yukseklik.setValue(sema.kor_yuksekligi(kor) or kor.get("yukseklik") or 366.0)
        self._katman_doldur()

        self._sinirlari_doldur()

        yans = kor.get("yansitici") or {}
        self.yans_var.setChecked(bool(yans.get("var")))
        self.yans_kal.setValue(yans.get("kalinlik") or 20.0)

        self._gorunurluk()
        self._tambur_durumu()      # ilk yuklemede de gosterilsin
        self._ozet_guncelle()

    @staticmethod
    def _malzeme_etiketi(m):
        return sema.malzeme_etiketi(m)

    def _kutu_doldur(self, kutu, ogeler, secili):
        """
        Secim kutusunu doldurur. Spec'teki deger listede yoksa (secilmemis ya da
        tanimsiz) AYRI bir oge olarak eklenir: ilk ogeye dusup bir sonraki
        kayitta dosyaya sessizce yazilmasin.
        """
        eski = kutu.blockSignals(True)
        try:
            kutu.clear()
            for deger, etiket in ogeler:
                kutu.addItem(etiket, deger)
            i = kutu.findData(secili)
            if i < 0:
                kutu.insertItem(0, "(seçilmedi)" if secili is None
                                else "%s (tanımsız)" % secili, secili)
                i = 0
            kutu.setCurrentIndex(i)
        finally:
            kutu.blockSignals(eski)

    def _sinirlari_doldur(self):
        """Sinir kutulari: yalnizca bu yuzeyde gecerli secenekler (uygunluk)."""
        sinir = self.spec["kor"].get("sinir") or {}
        for yuzey, kutu in (("yan", self.bc_yan), ("alt", self.bc_alt), ("ust", self.bc_ust)):
            secenek = list(uygunluk.sinir_secenekleri(self.spec, yuzey))
            deger = sinir.get(yuzey, "reflective")
            eski = kutu.blockSignals(True)
            try:
                kutu.clear()
                for s in secenek:
                    kutu.addItem(SINIR_ADLARI.get(s, s), s)
                i = kutu.findData(deger)
                if i < 0 and secenek:
                    # Dosyadaki deger bu yuzeyde gecersiz (elle yazilmis): silinmez,
                    # gecersizligi gorunur; dogrulama ayrica bildirir.
                    kutu.addItem("%s — bu yüzeyde geçersiz" % SINIR_ADLARI.get(deger, deger),
                                 deger)
                    i = kutu.count() - 1
                kutu.setCurrentIndex(i)
            finally:
                kutu.blockSignals(eski)

    def _kabuklari_doldur(self):
        kabuklar = self.spec["kor"].get("kabuklar") or []
        self.kabuk_tablo.setRowCount(len(kabuklar))
        for i, k in enumerate(kabuklar):
            r = QtWidgets.QTableWidgetItem("%g" % float(k.get("r") or 0.0))
            r.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.kabuk_tablo.setItem(i, 0, r)
            m = k.get("malzeme") or sema.BOSLUK
            self.kabuk_tablo.setItem(i, 1, QtWidgets.QTableWidgetItem(
                _(_BOS_ETIKET) if m == sema.BOSLUK else m))
        self.kabuk_tablo.resizeColumnsToContents()
        _tablo_yuksekligi(self.kabuk_tablo, _KABUK_EN_COK_SATIR)

    # ------------------------------------------------------------------
    # kor haritasi
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # eksenel katmanlar (tablo FIZIKSEL sirada: satir r <-> spec n-1-r)
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # yukseklik secimi
    # ------------------------------------------------------------------
    def _yukseklik_modu_degisti(self, *_):
        if self._yukleniyor:
            return
        kor = self.spec["kor"]
        mod = self.yukseklik_modu.currentData()
        eks = kor.setdefault("eksenel", {"var": False, "bolgeler": []})
        eski_h = sema.kor_yuksekligi(kor)
        if mod == "katmanli":
            eks["var"] = True
            if not (eks.get("bolgeler") or []):
                # Ilk acilista: mevcut yukseklik tek "aktif" katman olur.
                eks["bolgeler"] = [sema.eksenel_bolge(
                    "aktif", kor.get("yukseklik") or self.yukseklik.value(), None)]
            # Katmanlarin daha once kaydedilmis yuksekligi korunur (silinmez).
            kor["yukseklik"] = None
        else:
            eks["var"] = False
            if mod == "3B":
                if eski_h:
                    self.yukseklik.blockSignals(True)
                    self.yukseklik.setValue(eski_h)
                    self.yukseklik.blockSignals(False)
                kor["yukseklik"] = self.yukseklik.value()
            else:
                kor["yukseklik"] = None
        self._yukleniyor = True
        try:
            self._katman_doldur()
            self._sinirlari_doldur()        # alt/ust yalnizca 3B'de
        finally:
            self._yukleniyor = False
        self._gorunurluk()
        self._ozet_guncelle()
        self.bildir()

    # ------------------------------------------------------------------
    # gorunurluk
    # ------------------------------------------------------------------
    def _gorunurluk(self):
        if self.spec is None:
            return
        kor = self.spec["kor"]
        tur = kor.get("tur")
        alan = set(uygunluk.kor_alanlari(tur))
        ortak = uygunluk.kor_ortak_alanlari(self.spec)
        for satir, gorunur in (
                (self.satir_cubuk, "cubuk" in alan),
                (self.satir_plaka, "plaka" in alan),
                (self.satir_demet, "demet" in alan),
                (self.satir_tb_dolgu, "dolgu" in alan),
                (self.satir_tb_kor_r, "kor_yaricap" in alan),
                (self.satir_adim, "adim" in alan)):
            for w in satir:
                w.setVisible(gorunur)
        self.satir_adim[0].setText("Demet adımı:" if tur in sema.HARITALI_KORLAR
                                   else "Hücre adımı:")
        self.adim.setToolTip(_("Komşu demet merkezleri arası; altıgende düz yüzden düz "
                               "yüze. En az demetin dış ölçüsü (kılıf dahil) kadar.")
                             if tur == "altigen_kafes" else "")
        self.kafes_kutu.setVisible("harita" in alan)
        self.kare_harita.setVisible(tur != "altigen_kafes")
        self.altigen_harita.setVisible(tur == "altigen_kafes")
        self.tambur_kutu.setVisible("tambur" in alan)
        self.kabuk_kutu.setVisible("kabuklar" in alan)

        # yansitici: yalnizca "yansitici" alani olan turlerde; tamburluda zorunlu
        yans_uygun = "yansitici" in alan
        zorunlu = tur == "tamburlu"
        self.yans_kutu.setVisible(yans_uygun)
        self.yans_var.setVisible(yans_uygun and not zorunlu)
        self.yans_notu.setVisible(zorunlu)
        acik = yans_uygun and (zorunlu or self.yans_var.isChecked())
        self._yans_form.setRowVisible(self.yans_kal, acik)
        self._yans_form.setRowVisible(self.yans_mal, acik)

        # yukseklik ve sinirlar
        mod = self.yukseklik_modu.currentData()
        eksenli = ortak.get("yukseklik", False)
        form = self._eksen_form
        form.setRowVisible(self.yukseklik_modu, eksenli)
        form.setRowVisible(self.yukseklik, eksenli and mod == "3B")
        form.setRowVisible(self.bc_alt, ortak.get("sinir_alt", False))
        form.setRowVisible(self.bc_ust, ortak.get("sinir_ust", False))
        self.yan_etiket.setText("Dış yüzey sınırı:" if uygunluk.yan_yuzey(self.spec) == "kure"
                                else "Yan sınır:")
        self.eksen_kutu.baslik_ayarla("Yükseklik ve sınır koşulları" if eksenli
                                      else "Sınır koşulu")
        self.katman_kutu.setVisible(ortak.get("eksenel", False) and mod == "katmanli")
        self._sinir_notu_guncelle()

    def _sinir_notu_guncelle(self):
        kor = self.spec["kor"]
        yans = kor.get("yansitici") or {}
        yansitici_var = kor.get("tur") == "tamburlu" or (
            yans.get("var") and "yansitici" in uygunluk.kor_alanlari(kor.get("tur")))
        uyari = yansitici_var and (kor.get("sinir") or {}).get("yan") == "reflective"
        self.sinir_notu.setText(
            "Yansıtıcı kuşak + yansıtıcı (reflective) yan sınır sonsuz bir dizi "
            "modeller; tek, çevresi açık bir kor için Vakum seçin." if uyari else "")
        self._eksen_form.setRowVisible(self.sinir_notu, bool(uyari))

    def _ozet_guncelle(self):
        try:
            from cekirdek import onbellek
            _, bilgi = onbellek.kur_onbellekli(self.spec)
            gx, gy = bilgi["sinir_kutu"]
            # sema.kor_yuksekligi(): katmanliyken yukseklik katman toplamidir.
            h = sema.kor_yuksekligi(self.spec["kor"])
            ek = ("" if self.spec["kor"].get("tur") == "kuresel" else "  (2B)")
            metin = "%.4f × %.4f cm%s" % (gx, gy, (" × %.2f cm" % h) if h else ek)
            self.ozet.setText(metin)
        except Exception as e:
            from arayuz.ortak import hata_metni
            self.ozet.setText("Kurulamadı: %s" % hata_metni(e)[:120])

    # ------------------------------------------------------------------
    # kayit
    # ------------------------------------------------------------------
    def _kaydet(self, *_):
        if self._yukleniyor or self.spec is None:
            return
        kor = self.spec["kor"]
        tur = kor.get("tur")
        # Yalnizca BU TURUN alanlari yazilir (uygunluk.kor_alanlari). Harita,
        # anahtar ve boyut boyama/boyut islemlerinde yazilir; burada yazilmaz.
        alanlar = uygunluk.kor_alanlari(tur)
        ortak = uygunluk.kor_ortak_alanlari(self.spec)
        if "cubuk" in alanlar:
            kor["cubuk"] = self.cubuk.currentData()
        if "plaka" in alanlar:
            kor["plaka"] = self.plaka.currentData()
        if "demet" in alanlar:
            kor["demet"] = self.demet.currentData()
        if "adim" in alanlar:
            kor["adim"] = self.adim.value()
        if ortak.get("yukseklik") and self.yukseklik_modu.currentData() == "3B":
            kor["yukseklik"] = self.yukseklik.value()
        sinir = kor.setdefault("sinir", {})
        sinir["yan"] = self.bc_yan.currentData()
        if ortak.get("sinir_alt"):
            sinir["alt"] = self.bc_alt.currentData()
        if ortak.get("sinir_ust"):
            sinir["ust"] = self.bc_ust.currentData()
        if "dolgu" in alanlar:
            kor["dolgu"] = self.tb_dolgu.currentData()
        if "kor_yaricap" in alanlar:
            kor["kor_yaricap"] = self.tb_kor_r.value()
        if "tambur" in alanlar:
            kor["tambur"] = {
                "sayi": self.tb_sayi.value(),
                "yaricap": self.tb_r.value(),
                "merkez_yaricap": self.tb_rm.value(),
                "govde_malzeme": self.tb_govde.currentData(),
                "emici_malzeme": self.tb_emici.currentData(),
                "emici_ic_yaricap": self.tb_emici_ric.value(),
                "emici_aci": self.tb_aci.value(),
                "donme": self.tb_donme.value(),
                # arayuzde alani yok: yuklenen deger korunur
                "baslangic_acisi": self._baslangic_acisi,
            }
        if "yansitici" in alanlar:
            # Tamburlu'da "var" kutusu gizli ve anlamsiz (yansitici zorunlu):
            # dosyadaki deger oldugu gibi birakilir.
            eski_var = (kor.get("yansitici") or {}).get("var", False)
            kor["yansitici"] = {"var": (eski_var if tur == "tamburlu"
                                        else self.yans_var.isChecked()),
                                "kalinlik": self.yans_kal.value(),
                                "malzeme": self.yans_mal.currentData()}
        sema.kor_alanlarini_ayikla(kor)
        self._tambur_durumu()
        self._gorunurluk()
        self._ozet_guncelle()
        self.bildir()

    def _yans_degisti(self, acik):
        if self._yukleniyor:
            return
        if acik and self.yans_mal.currentData() in (None, sema.BOSLUK):
            # Kusak ilk kez eklenince malzemesi bos kalmasin: modeldeki ilk
            # moderator / sogutucu (genellikle su) onerilir; kutuda gorunur.
            aday = (uygunluk.rol_malzemeleri(self.spec, "moderator")
                    + uygunluk.rol_malzemeleri(self.spec, "sogutucu"))
            i = self.yans_mal.findData(aday[0]) if aday else -1
            if i >= 0:
                self.yans_mal.blockSignals(True)
                self.yans_mal.setCurrentIndex(i)
                self.yans_mal.blockSignals(False)
        self._kaydet()

    def _donme_degisti(self, *_):
        if self._yukleniyor:
            return
        self._yukleniyor = True
        try:
            self.tb_donme_kaydirici.setValue(int(round(self.tb_donme.value() * 10)) % 3600)
        finally:
            self._yukleniyor = False
        self._kaydet()

    def _donme_kaydirici(self, deger):
        if self._yukleniyor:
            return
        self._yukleniyor = True
        try:
            self.tb_donme.setValue(deger / 10.0)
        finally:
            self._yukleniyor = False
        self._kaydet()

    def _tambur_durumu(self):
        """Tambur yerlesiminin gecerliligini canli gosterir."""
        from cekirdek import tambur as _t
        kor = self.spec["kor"]
        t = kor.get("tambur") or {}
        if int(t.get("sayi") or 0) <= 0:
            self.tb_durum.setText("Tambur yok — düz yansıtıcı kuşak.")
            self.tb_durum.setObjectName("soluk")
            self.tb_durum.setStyleSheet("")
            return
        kal = (kor.get("yansitici") or {}).get("kalinlik") or 0.0
        hatalar = _t.geometri_kontrol(t, kor.get("kor_yaricap") or 0.0, kal)
        if hatalar:
            self.tb_durum.setText(hatalar[0])
            self.tb_durum.setStyleSheet("color: %s; font-weight: bold;" % tema.renk("hata"))
        else:
            n = int(t["sayi"])
            kiris = 2.0 * t["merkez_yaricap"] * math.sin(math.pi / n) if n > 1 else 0.0
            self.tb_durum.setText(
                "Geçerli — komşu tambur merkezleri arası %.3f cm (iki yarıçap %.3f cm)."
                % (kiris, 2 * t["yaricap"]))
            self.tb_durum.setStyleSheet("color: %s;" % tema.renk("basari"))
