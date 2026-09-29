# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_ayar.py  --  Hesap ayarlari: hesap turu, hassasiyet, kaynak, guc, tally
================================================================================
 OGRENCI BIRKAC TIKLA, UZMAN "GELISMIS"TE
   Ustte yalnizca iki karar vardir: hesap turu (ozdeger / sabit kaynak) ve
   "Hesap hassasiyeti" (Hizli deneme / Normal / Hassas / Ozel). Hassasiyet
   onayari parcacik, cevrim ve pasif cevrimi birlikte ayarlar ve beklenen
   k-eff belirsizligini (pcm) yazar. Rastgele tohum, sicaklik yontemi, entropi
   agi, IFP nesil sayisi ve (ozdegerde) baslangic kaynaginin tayfi/yonu
   ortak.GelismisBolum altindadir.

 NE GORUNUR -- uygunluk.ayar_alanlari(spec), uygunluk.kaynak_secenekleri(spec)
   Sabit kaynakta pasif cevrim, entropi ve kinetik gizlenir; ozdegerde foton
   kaynagi ve kaynak siddeti gizlenir. Guc dagilimi yalnizca
   uygunluk.guc_cubuklari(spec) bos degilse gorunur. GIZLENEN DEGER SPEC'TEN
   SILINMEZ ve _kaydet ona dokunmaz: kayit yalnizca gorunen alanlari yazar.

 CALISTIRMA AYARLARI BURADA DEGIL
   Is parcacigi ve kosu dizini (spec["calistirma"]) Calistir sekmesindedir;
   bu sekme onlari ne gosterir ne de yazar.

 HASSASIYET ONAYARLARI VE OLCULEN BELIRSIZLIK
   pwr_pinhucre (k-inf ~ 1.36), OpenMC 0.16, 4 is parcacigi, tohum 1-3:
     onayar        parcacik x cevrim (pasif)   sigma [pcm]           sure
     Hizli deneme     1 000 x  60 (20)          311 / 447 / 532      3.5 s
     Normal          10 000 x 150 (40)           82 /  86 /  88      36 s
     Hassas          50 000 x 300 (80)           28 / 28              337 s
   pwr_17x17 (2B demet):  Hizli 489 / 447 | Normal 75 / 89 | Hassas 28 pcm
   pwr_3b (3B demet):     Normal 82 pcm
   sigma * sqrt(parcacik x aktif cevrim) = C sabit kalir: C ~ 9.0e4 pcm
   (Normal ve Hassas'ta 7.9e4 - 9.3e4; Hizli'da 40 aktif cevrimle sigma'nin
   kendisi +/-%30 oynar). Belirsizlik bu C ile HER parcacik/cevrim secimi icin
   tahmin edilir (testler/test_kor_ayar.py SIGMA_OLCUMU ile sinanir). Cok
   buyuk ya da gevsek bagli korlarda (tam kor) daha buyuk olabilir; metin
   "yaklasik" der ve bunu belirtir.
================================================================================
"""

import math

from PySide6 import QtCore, QtWidgets

from cekirdek import sema, uygunluk
from cekirdek import kaynak as _kaynak
from arayuz.ortak import (SekmeTabani, ayrac, baslik, ipucu, sayi, tamsayi,
                          EnerjiGirdi, BilimselGirdi, GelismisBolum)

# Bolunen parcalar (Dalga 0): eski ad alani aynen korunur.
from arayuz.ayar.sabitler import (  # noqa: F401
    HASSASIYET, OZEL, SIGMA_KATSAYISI, SKORLAR, _SKOR_ADI, SKOR_SETLERI,
    SICAKLIK_YONTEMLERI, GUC_SKORLARI, _FILTRE_ADI, hassasiyet_bul, belirsizlik_pcm,
    _binlik, _pcm_yuvarla)
from arayuz.ayar.yerlesim import (  # noqa: F401
    YerlesimMixin)
from arayuz.ayar.kaynak_formu import (  # noqa: F401
    KaynakFormuMixin)
from arayuz.ayar.guc_formu import (  # noqa: F401
    GucFormuMixin)
from arayuz.ayar.tally_formu import (  # noqa: F401
    TallyFormuMixin)


class AyarSekmesi(YerlesimMixin, KaynakFormuMixin, GucFormuMixin, TallyFormuMixin, SekmeTabani):

    KONU = "ayar"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tayf_yeri = None

        # ================= hesap =================
        self.mod = QtWidgets.QComboBox()
        self.mod.addItem("Özdeğer (k-eff)", "eigenvalue")
        self.mod.addItem("Sabit kaynak", "fixed source")
        self.mod.setToolTip(
            "Özdeğer: kendi kendini sürdüren zincir tepkimesi; sonuç k-eff.\n"
            "Sabit kaynak: dışarıdan verilen bir kaynağın taşınımı (zırhlama,\n"
            "detektör); sonuç tally'lerdir, k-eff yoktur.")
        self.hassasiyet = QtWidgets.QComboBox()
        for anahtar, ad, *_ in HASSASIYET:
            self.hassasiyet.addItem(ad, anahtar)
        self.hassasiyet.addItem("Özel", OZEL)
        self.hassasiyet.setToolTip(
            "Hızlı deneme: modelin çalıştığını görmek için.\n"
            "Normal: ders ve ödev hesapları için.\n"
            "Hassas: küçük reaktivite farklarını ayırmak için (uzun sürer).\n"
            "Özel: parçacık ve çevrim sayılarını kendiniz girin.")
        self.hassasiyet_ozet = QtWidgets.QLabel("-")
        self.hassasiyet_ozet.setWordWrap(True)
        self.parcacik = tamsayi(10000, 100, 10 ** 9, 1000)
        self.cevrim = tamsayi(150, 1, 100000, 10)
        self.pasif = tamsayi(40, 0, 100000, 5)
        self.pasif.setToolTip(
            "Pasif çevrimler kaynak dağılımı yakınsayana kadar atılır ve\n"
            "istatistiğe katılmaz. Tipik olarak 20–50 pasif çevrim kullanılır.")
        self.kinetik_var = QtWidgets.QCheckBox(
            "Kinetik parametreleri hesapla (β_eff ve üretim zamanı Λ)")
        self.kinetik_var.setToolTip(
            "IFP (Iterated Fission Probability) yöntemiyle hesaplanır.\n"
            "β_eff : gecikmiş nötron kesri — reaktivite biriminin ($) tanımı\n"
            "Λ     : nötron üretim zamanı — kinetik davranışın hızı\n\n"
            "Koşuyu bir miktar yavaşlatır; gerekmedikçe kapalı bırakın.")

        # ================= gelismis =================
        self.tohum = tamsayi(1, 1, 2 ** 31 - 1, 1)
        self.tohum.setToolTip("Aynı tohum ve aynı model aynı sonucu verir.")
        self.sicaklik_yontemi = QtWidgets.QComboBox()
        self.entropi_var = QtWidgets.QCheckBox("Shannon entropisi ile kaynak yakınsamasını ölç")
        self.entropi_var.setToolTip(
            "Kaynak dağılımının pasif çevrimler içinde yakınsayıp yakınsamadığını\n"
            "ölçer. Yakınsamamış kaynak k-eff'i yanlı tahmin ettirir ve bu başka\n"
            "türlü fark edilmez. Özdeğer hesaplarında açık tutun.")
        self.entropi_oto = QtWidgets.QCheckBox("Ağ boyutu otomatik")
        self.entropi_oto.setToolTip(
            "8 × 8 radyal bölme; 3B modelde eksenel 8 bölme, 2B'de tek dilim.\n"
            "Model 2B ↔ 3B değişince ağ da değişir.")
        self.entropi_nx = tamsayi(8, 1, 200)
        self.entropi_ny = tamsayi(8, 1, 200)
        self.entropi_nz = tamsayi(1, 1, 200)
        self.kinetik_nesil = tamsayi(10, 1, 50, 1, "nesil")
        self.kinetik_nesil.setToolTip("IFP'nin geriye doğru izlediği nesil sayısı.")

        # ================= kaynak =================
        self.kaynak_tur = QtWidgets.QComboBox()
        self.kx = sayi(0.0, 4, -1e5, 1e5, 0.1, "cm")
        self.ky = sayi(0.0, 4, -1e5, 1e5, 0.1, "cm")
        self.kz = sayi(0.0, 4, -1e5, 1e5, 0.1, "cm")
        self.kaynak_parcacik = QtWidgets.QComboBox()
        self.kaynak_parcacik.setToolTip(
            "Foton seçilirse foton taşınımı da açılır ve kütüphanede foton\n"
            "verisi bulunmalıdır.")
        self.kaynak_kuvvet = BilimselGirdi(1.0)
        self.kaynak_kuvvet.setToolTip(
            "Kaynak şiddeti [parçacık/s]. Tally sonuçları bununla çarpılır ve\n"
            "mutlak birime geçer (1/s, 1/cm²/s). 1 bırakılırsa sonuçlar kaynak\n"
            "parçacığı başına kalır.")

        # --- enerji tayfi ---
        self.tayf = QtWidgets.QComboBox()
        for anahtar, ad in _kaynak.TAYFLAR:
            self.tayf.addItem(ad, anahtar)
        self.watt_a = EnerjiGirdi(988.0e3)
        self.watt_b = sayi(2.249e-6, 9, 1e-9, 1.0, 1e-7, " 1/eV")
        self.maxwell_theta = EnerjiGirdi(1.2932e6)
        self.tek_enerji = EnerjiGirdi(14.1e6)
        self.ayrik_metin = QtWidgets.QLineEdit("1.173e6:0.5, 1.333e6:0.5")
        self.ayrik_metin.setToolTip("enerji[eV]:olasılık çiftleri, virgülle ayrılmış\n"
                                    "Örnek (Co-60): 1.173e6:0.5, 1.333e6:0.5")
        self.hist_kenar = QtWidgets.QLineEdit("1e5, 1e6, 1e7")
        self.hist_deger = QtWidgets.QLineEdit("1.0, 1.0")
        self.hist_kenar.setToolTip("N+1 grup kenarı [eV], artan sırada")
        self.hist_deger.setToolTip("N grup değeri (bağıl); kenar sayısından bir eksik olmalı")
        self.fuzyon_e0 = EnerjiGirdi(14.08e6)
        self.fuzyon_kutle = sayi(5.0, 2, 1.0, 100.0, 1.0)
        self.fuzyon_kutle.setToolTip("Tepkimeye girenlerin kütleleri toplamı: D+T = 2+3 = 5, D+D = 4")
        self.fuzyon_kt = EnerjiGirdi(20.0e3)
        self.fuzyon_kt.setToolTip("İyon sıcaklığı kT. D-T için genişleme:\n"
                                  "FWHM = 177 × √kT[keV] keV")
        self.tayf_yigin = QtWidgets.QStackedWidget()
        for alanlar in (
                [("a (Watt):", self.watt_a), ("b:", self.watt_b)],
                [("θ:", self.maxwell_theta)],
                [("Enerji:", self.tek_enerji)],
                [("Çizgiler:", self.ayrik_metin)],
                [("Grup kenarları:", self.hist_kenar), ("Grup değerleri:", self.hist_deger)],
                [("Ortalama E₀:", self.fuzyon_e0), ("Kütle toplamı:", self.fuzyon_kutle),
                 ("İyon sıcaklığı:", self.fuzyon_kt)]):
            sayfa = QtWidgets.QWidget()
            f = QtWidgets.QFormLayout(sayfa)
            f.setContentsMargins(0, 0, 0, 0)
            for etiket, w in alanlar:
                f.addRow(etiket, w)
            self.tayf_yigin.addWidget(sayfa)
        self.tayf_ozet = QtWidgets.QLabel("-")
        self.tayf_ozet.setWordWrap(True)

        # --- acisal dagilim ---
        self.aci_tur = QtWidgets.QComboBox()
        for anahtar, ad in _kaynak.ACILAR:
            self.aci_tur.addItem(ad, anahtar)
        self.ax = sayi(0.0, 4, -1e3, 1e3, 0.1)
        self.ay = sayi(0.0, 4, -1e3, 1e3, 0.1)
        self.az = sayi(1.0, 4, -1e3, 1e3, 0.1)
        self.koni_aci = sayi(30.0, 2, 0.01, 180.0, 5.0, " derece")
        self.koni_aci.setToolTip("Koninin yarı açılımı (eksenden kenara açı). Katı açıda düzgün dağılım kullanılır.")

        # ================= guc dagilimi =================
        self.guc_var = QtWidgets.QCheckBox("Çubuk bazlı güç dağılımı hesapla (F_ΔH, 3B'de F_q)")
        self.guc_var.setToolTip(
            "Demette tekrarlanan yakıt çubuğunun her örneği ayrı sayılır\n"
            "(OpenMC: DistribcellFilter). Buradan tepe faktörleri çıkar:\n"
            "  F_ΔH = en yüksek çubuk gücü / ortalama        (radyal)\n"
            "  F_q  = en yüksek yerel güç yoğunluğu / ortalama (3B gerekir)")
        self.guc_cubuk = QtWidgets.QComboBox()
        self.guc_bolge = QtWidgets.QComboBox()
        self.guc_skor = QtWidgets.QComboBox()
        for veri, ad in GUC_SKORLARI:
            self.guc_skor.addItem(ad, veri)
        self.guc_dilim = tamsayi(20, 1, 200, 1, "dilim")
        self.guc_toplam = sayi(0.0, 1, 0.0, 1e12, 1e5, "W")
        self.guc_toplam.setSpecialValueText("(boş — yalnızca bağıl)")
        self.guc_etiketler = {}
        self.guc_not = ipucu(
            "Toplam güç, <b>modelin kapsadığı</b> bölgenin gücüdür — tüm korun değil. "
            "Örnek: 3400 MWth / 193 demet = 17.6 MW; tek demetlik modelde 17.6e6 W "
            "girilir. Boş bırakılırsa yalnızca bağıl dağılım verilir.")
        self.guc_uyari = ipucu("")

        # ================= tally'ler =================
        self.tally_liste = QtWidgets.QListWidget()
        self.tally_liste.setMinimumWidth(150)
        self.tally_liste.setMaximumWidth(210)
        self.tally_liste.setMinimumHeight(110)
        self.tally_liste.currentRowChanged.connect(self._tally_secildi)
        self.t_ad = QtWidgets.QLineEdit()
        self.t_set = QtWidgets.QComboBox()
        for anahtar, ad, _s in SKOR_SETLERI:
            self.t_set.addItem(ad, anahtar)
        self.t_set.addItem("Özel", OZEL)
        self.t_set_ozet = ipucu("")
        self.t_skor = QtWidgets.QListWidget()
        self.t_skor.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self._skor_listesi_kur([])
        self.t_skor.setMinimumHeight(150)
        self.t_enerji_var = QtWidgets.QCheckBox("Enerji grupları")
        self.t_enerji = QtWidgets.QLineEdit("0.0, 0.625, 2.0e7")
        self.t_enerji.setToolTip("Grup sınırları [eV], artan sırada, virgülle ayrılmış.\n"
                                 "Örnek (iki grup): 0.0, 0.625, 2.0e7")
        self.t_mesh_var = QtWidgets.QCheckBox("Akı haritası (düzenli ağ)")
        self.t_mesh_var.setToolTip("Sınırlar model kurulurken modelin dış ölçüsünden alınır.")
        self.t_mesh_nx = tamsayi(10, 1, 1000)
        self.t_mesh_ny = tamsayi(10, 1, 1000)
        self.t_mesh_nz = tamsayi(1, 1, 1000)
        self.t_diger = ipucu("")
        self.tally_bos = ipucu("Henüz tally yok. “+ Tally” ile ekleyin: ne ölçmek "
                               "istediğinizi (akı, reaksiyon hızı, ısı) seçersiniz.")

        # Uclu satirlardaki alanlar dar sutuna sigsin.
        for _w in (self.entropi_nx, self.entropi_ny, self.entropi_nz,
                   self.t_mesh_nx, self.t_mesh_ny, self.t_mesh_nz,
                   self.kx, self.ky, self.kz, self.ax, self.ay, self.az):
            _w.setMinimumWidth(56)

        self._yerlesim_kur()
        self._sinyalleri_bagla()

    def _sinyalleri_bagla(self):
        for w in (self.parcacik, self.cevrim, self.pasif):
            w.valueChanged.connect(self._sayi_elle_degisti)
        self.hassasiyet.currentIndexChanged.connect(self._hassasiyet_secildi)
        for w in (self.tohum, self.kx, self.ky, self.kz,
                  self.entropi_nx, self.entropi_ny, self.entropi_nz,
                  self.kinetik_nesil, self.guc_dilim, self.guc_toplam):
            w.valueChanged.connect(self._kaydet)
        for w in (self.entropi_var, self.entropi_oto, self.kinetik_var, self.guc_var):
            w.toggled.connect(self._kaydet)
        self.guc_cubuk.currentIndexChanged.connect(self._guc_cubuk_degisti)
        for w in (self.mod, self.sicaklik_yontemi, self.kaynak_tur, self.kaynak_parcacik,
                  self.tayf, self.aci_tur, self.guc_bolge, self.guc_skor):
            w.currentIndexChanged.connect(self._kaydet)
        for w in (self.watt_a, self.maxwell_theta, self.tek_enerji,
                  self.fuzyon_e0, self.fuzyon_kt):
            w.degisti.connect(self._kaydet)
        for w in (self.watt_b, self.fuzyon_kutle, self.koni_aci, self.ax, self.ay, self.az):
            w.valueChanged.connect(self._kaydet)
        for w in (self.ayrik_metin, self.hist_kenar, self.hist_deger, self.kaynak_kuvvet):
            w.editingFinished.connect(self._kaydet)
        self.t_ad.editingFinished.connect(self._tally_kaydet)
        self.t_set.currentIndexChanged.connect(self._skor_seti_secildi)
        self.t_skor.itemSelectionChanged.connect(self._tally_kaydet)
        self.t_enerji.editingFinished.connect(self._tally_kaydet)
        for w in (self.t_enerji_var, self.t_mesh_var):
            w.toggled.connect(self._tally_kaydet)
        for w in (self.t_mesh_nx, self.t_mesh_ny, self.t_mesh_nz):
            w.valueChanged.connect(self._tally_kaydet)

    # ------------------------------------------------------------------
    # yardimcilar
    # ------------------------------------------------------------------
    @staticmethod
    def _kutu_doldur(kutu, ogeler, secili, gecersiz_eki=" (bu modelde geçersiz)"):
        """Secim kutusunu (veri, etiket) ogeleriyle doldurur. Spec'teki deger
        listede yoksa AYRI bir oge olarak eklenir -- sessizce degismesin."""
        eski = kutu.blockSignals(True)
        try:
            kutu.clear()
            etiketler = dict(ogeler)
            for veri, etiket in ogeler:
                kutu.addItem(etiket, veri)
            i = kutu.findData(secili)
            if i < 0 and secili is not None:
                kutu.addItem("%s%s" % (etiketler.get(secili, secili), gecersiz_eki), secili)
                i = kutu.count() - 1
            kutu.setCurrentIndex(max(i, 0))
        finally:
            kutu.blockSignals(eski)

    @staticmethod
    def _deger_ayarla(w, deger):
        eski = w.blockSignals(True)
        w.setValue(deger)
        w.blockSignals(eski)

    def _alan(self):
        """uygunluk.ayar_alanlari -- hangi alan bu modelde anlamli."""
        return uygunluk.ayar_alanlari(self.spec)

    def _ozdeger(self):
        return (self.spec["ayarlar"].get("mod") or "eigenvalue") == "eigenvalue"

    def _uc_boyutlu(self):
        return bool(sema.kor_yuksekligi(self.spec.get("kor") or {}))

    def _mesh_nz_anlamli(self):
        """z yonu anlamli mi: 3B modelde ve kurede (tally aginda z = kure capi,
        nokta kaynakta z konumu). 2B modelde model z'de sonsuzdur ve tally agi
        tek dilimdir (kurucu.tally_mesh_sinirlari)."""
        return self._uc_boyutlu() or (self.spec.get("kor") or {}).get("tur") == "kuresel"

    def _kinetik_gorunur(self):
        """Kinetik kutusu: ozdeger + fisil; uygun olmayan ozdeger modelinde
        yalnizca dosyada acik birakilmissa (kapatilabilsin diye)."""
        return self._alan()["kinetik"] or (
            self._ozdeger() and bool((self.spec["ayarlar"].get("kinetik") or {}).get("var")))

    # ------------------------------------------------------------------
    # doldurma
    # ------------------------------------------------------------------
    def doldur(self):
        a = self.spec["ayarlar"]
        i = self.mod.findData(a.get("mod", "eigenvalue"))
        self.mod.setCurrentIndex(max(i, 0))
        self.parcacik.setValue(a.get("parcacik", 10000))
        self.cevrim.setValue(a.get("cevrim", 150))
        self.pasif.setValue(a.get("pasif", 40))
        self._hassasiyeti_goster()
        self.tohum.setValue(a.get("tohum") or 1)
        self._kutu_doldur(self.sicaklik_yontemi, SICAKLIK_YONTEMLERI,
                          a.get("sicaklik_yontemi", "interpolation"), " (bilinmeyen)")

        k = a.get("kaynak") or {}
        secenek = uygunluk.kaynak_secenekleri(self.spec)
        tur_adlari = {"nokta": "Nokta kaynak", "kutu": "Kutu (yalnızca fisil bölgeler)"}
        self._kutu_doldur(self.kaynak_tur, [(t, tur_adlari.get(t, t)) for t in secenek["turler"]],
                          k.get("tur", "nokta"))
        konum = k.get("konum") or [0.0, 0.0, 0.0]
        self.kx.setValue(konum[0])
        self.ky.setValue(konum[1])
        self.kz.setValue(konum[2])
        parcacik_adlari = {"neutron": "Nötron", "photon": "Foton (gama)"}
        self._kutu_doldur(self.kaynak_parcacik,
                          [(p, parcacik_adlari.get(p, p)) for p in secenek["parcaciklar"]],
                          k.get("parcacik") or "neutron")
        self.kaynak_kuvvet.ayarla(k.get("kuvvet") or 1.0)

        e = k.get("enerji") or {}
        i = self.tayf.findData(e.get("tur", "watt"))
        self.tayf.setCurrentIndex(max(i, 0))
        self.watt_a.ayarla(e.get("a", 988.0e3))
        self.watt_b.setValue(e.get("b", 2.249e-6))
        self.maxwell_theta.ayarla(e.get("theta", 1.2932e6))
        self.tek_enerji.ayarla(e.get("enerji", 14.1e6))
        if e.get("noktalar"):
            self.ayrik_metin.setText(", ".join("%g:%g" % (p[0], p[1]) for p in e["noktalar"]))
        if e.get("kenarlar"):
            self.hist_kenar.setText(", ".join("%g" % x for x in e["kenarlar"]))
        if e.get("degerler"):
            self.hist_deger.setText(", ".join("%g" % x for x in e["degerler"]))
        self.fuzyon_e0.ayarla(e.get("e0", 14.08e6))
        self.fuzyon_kutle.setValue(e.get("kutle_orani", 5.0))
        self.fuzyon_kt.ayarla(e.get("iyon_sicaklik", 20.0e3))

        ac = k.get("aci") or {}
        i = self.aci_tur.findData(ac.get("tur", "izotropik"))
        self.aci_tur.setCurrentIndex(max(i, 0))
        yon = ac.get("yon") or [0.0, 0.0, 1.0]
        self.ax.setValue(yon[0])
        self.ay.setValue(yon[1])
        self.az.setValue(yon[2])
        self.koni_aci.setValue(ac.get("koni_aci") or 30.0)

        ent = a.get("entropi_mesh") or {}
        self.entropi_var.setChecked(bool(ent.get("var", True)))
        boyut = list(ent.get("boyut") or [8, 8, 1])
        self.entropi_nx.setValue(boyut[0])
        self.entropi_ny.setValue(boyut[1])
        self.entropi_nz.setValue(boyut[2])
        # Otomatik: dosyada acikca isaretliyse ya da (isaret yokken) dosyadaki
        # boyut otomatik kuralin verdigiyle AYNIYSA. Spec'e yazilmaz.
        oto = ent.get("otomatik")
        if oto is None:
            oto = boyut == _kaynak.entropi_boyutu_otomatik(self.spec)
        self.entropi_oto.setChecked(bool(oto))

        kin = a.get("kinetik") or {}
        self.kinetik_var.setChecked(bool(kin.get("var")))
        self.kinetik_nesil.setValue(kin.get("nesil") or 10)

        self._guc_doldur()
        self._tallyleri_doldur()
        self._gorunurluk()

    def showEvent(self, olay):
        # Hangi alanin gorunecegi baska sekmelere de baglidir (kor turu ve
        # yuksekligi, fisil malzeme, kafesteki cubuklar). Sekme her
        # gosterildiginde spec'ten yeniden okunur; spec DEGISMEZ.
        if self.spec is not None and not self._yukleniyor:
            self.spec_yukle(self.spec)
        super().showEvent(olay)

    # ------------------------------------------------------------------
    # gorunurluk (uygunluk'tan)
    # ------------------------------------------------------------------
    def _gorunurluk(self):
        if self.spec is None:
            return
        alan = self._alan()
        ozdeger = self._ozdeger()
        uc_b = self._uc_boyutlu()
        hf = self._hesap_form
        hf.setRowVisible(self.pasif, alan["pasif"])
        hf.setRowVisible(self.kinetik_var, self._kinetik_gorunur())
        self._hassasiyet_ozet_guncelle()

        # kaynak
        self.kaynak_baslik.setText("Başlangıç kaynağı" if ozdeger else "Kaynak")
        kf = self._kaynak_form
        nokta = self.kaynak_tur.currentData() == "nokta"
        kf.setRowVisible(self.konum_satiri, nokta)
        self.kz.setVisible(self._mesh_nz_anlamli())
        self.kz._etiket.setVisible(self._mesh_nz_anlamli())
        # parcacik: tek secenek (notron) ve gecerli ise satir gizli
        kf.setRowVisible(self.kaynak_parcacik, self.kaynak_parcacik.count() > 1)
        kf.setRowVisible(self.kaynak_kuvvet, alan["kaynak_siddeti"])
        self._tayfi_tasi(self._kaynak_tayf_yeri if alan["kaynak_tayfi_temel"]
                         else self._gelismis_tayf_yeri)
        self.gelismis_tayf_baslik.setVisible(not alan["kaynak_tayfi_temel"])
        self.gelismis_tayf_not.setVisible(not alan["kaynak_tayfi_temel"])
        self._tayf_gorunurluk()

        # gelismis: entropi (ozdeger), IFP nesil (kinetik acik)
        gf = self._gelismis_form
        gf.setRowVisible(self.entropi_var, alan["entropi"])
        gf.setRowVisible(self.entropi_agi, alan["entropi"] and self.entropi_var.isChecked())
        oto = self.entropi_oto.isChecked()
        for w in (self.entropi_nx, self.entropi_ny, self.entropi_nz):
            w.setEnabled(not oto)
        if oto:
            b = _kaynak.entropi_boyutu_otomatik(self.spec)
            for w, v in zip((self.entropi_nx, self.entropi_ny, self.entropi_nz), b):
                self._deger_ayarla(w, v)
        self.entropi_nz.setVisible(uc_b)
        self.entropi_nz._etiket.setVisible(uc_b)
        gf.setRowVisible(self.kinetik_nesil,
                         self._kinetik_gorunur() and self.kinetik_var.isChecked())

        self._guc_gorunurluk()
        self._tally_gorunurluk()

    # ------------------------------------------------------------------
    # hassasiyet
    # ------------------------------------------------------------------
    def _hassasiyeti_goster(self):
        """Degerlere uyan onayari (ya da Ozel'i) SPEC'E DOKUNMADAN gosterir."""
        anahtar = hassasiyet_bul(self.parcacik.value(), self.cevrim.value(),
                                 self.pasif.value(), self._ozdeger())
        eski = self.hassasiyet.blockSignals(True)
        self.hassasiyet.setCurrentIndex(self.hassasiyet.findData(anahtar))
        self.hassasiyet.blockSignals(eski)
        self._hassasiyet_ozet_guncelle()

    def _hassasiyet_ozet_guncelle(self):
        n, c, p = self.parcacik.value(), self.cevrim.value(), self.pasif.value()
        if self._ozdeger():
            aktif = c - p
            metin = "%s parçacık × %d çevrim (%d pasif, %d aktif)" % (_binlik(n), c, p, aktif)
            s = belirsizlik_pcm(n, c, p)
            if s is None:
                metin += " — aktif çevrim yok: pasif çevrim sayısını azaltın."
                self.hassasiyet_ozet.setStyleSheet("color: #b3261e;")
            else:
                metin += (" — beklenen k-eff belirsizliği ≈ ±%d pcm (pin hücre ölçümü; "
                          "büyük korlarda daha fazla olabilir)" % _pcm_yuvarla(s))
                self.hassasiyet_ozet.setStyleSheet("")
        else:
            metin = ("%s parçacık × %d çevrim = %s kaynak parçacığı; tally belirsizliği "
                     "1/√N ile azalır." % (_binlik(n), c, _binlik(n * c)))
            self.hassasiyet_ozet.setStyleSheet("")
        self.hassasiyet_ozet.setText(metin)

    def _hassasiyet_secildi(self, *_):
        """Kullanici bir onayar SECTI: parcacik/cevrim/pasif spec'e yazilir."""
        if self._yukleniyor:
            return
        anahtar = self.hassasiyet.currentData()
        for a_, _ad, n, c, p in HASSASIYET:
            if a_ == anahtar:
                self._deger_ayarla(self.parcacik, n)
                self._deger_ayarla(self.cevrim, c)
                if self._ozdeger():
                    # sabit kaynakta pasif cevrim gizli: dokunulmaz
                    self._deger_ayarla(self.pasif, p)
                break
        self._kaydet()

    def _sayi_elle_degisti(self, *_):
        if self._yukleniyor:
            return
        self._hassasiyeti_goster()
        self._kaydet()

    # ------------------------------------------------------------------
    # kayit -- yalnizca GORUNEN alanlar yazilir
    # ------------------------------------------------------------------
    def _guc_hedeflerini_oku(self, g):
        """
        Hedef cubuk kutusunun secimi -> guc_dagilimi["cubuklar"] listesi
        ([{"cubuk", "bolge"}], YENI liste).
          sema.GUC_TUM   : uygun butun yakit cubuklari (guc.varsayilan_hedefler)
          sema.GUC_LISTE : dosyadaki liste aynen korunur
          bir cubuk adi  : tek ogeli liste (secili bolge ile)
        """
        from cekirdek import guc as _guc_cekirdek
        ad = self.guc_cubuk.currentData()
        if ad == sema.GUC_TUM:
            return _guc_cekirdek.varsayilan_hedefler(self.spec)
        if ad == sema.GUC_LISTE:
            return sema.guc_hedefleri({"cubuklar": g.get("cubuklar")})
        if ad is None:
            return []
        return [{"cubuk": ad, "bolge": int(self.guc_bolge.currentData() or 0)}]

    def _kaydet(self, *_):
        if self._yukleniyor or self.spec is None:
            return
        a = self.spec["ayarlar"]
        mod_degisti = a.get("mod", "eigenvalue") != self.mod.currentData()
        a["mod"] = self.mod.currentData()
        # Mod degisince neyin gorundugu de degisir: alanlar YENI moda gore.
        alan = self._alan()
        uc_b = self._uc_boyutlu()
        a["parcacik"] = self.parcacik.value()
        a["cevrim"] = self.cevrim.value()
        if alan["pasif"]:
            a["pasif"] = self.pasif.value()
        a["tohum"] = self.tohum.value()
        a["sicaklik_yontemi"] = self.sicaklik_yontemi.currentData()
        if alan["entropi"]:
            ent = dict(a.get("entropi_mesh") or {})
            ent["var"] = self.entropi_var.isChecked()
            if self.entropi_oto.isChecked():
                oto = _kaynak.entropi_boyutu_otomatik(self.spec)
                if ent.get("otomatik") is not None or ent.get("boyut") != oto:
                    ent["otomatik"] = True
                ent["boyut"] = oto
            else:
                eski = list(ent.get("boyut") or [8, 8, 1])
                ent["boyut"] = [self.entropi_nx.value(), self.entropi_ny.value(),
                                self.entropi_nz.value() if uc_b else eski[2]]
                if "otomatik" in ent:
                    ent["otomatik"] = False
            a["entropi_mesh"] = ent
        if self._kinetik_gorunur():
            kin = dict(a.get("kinetik") or {})
            kin["var"] = self.kinetik_var.isChecked()
            if self.kinetik_var.isChecked():
                kin["nesil"] = self.kinetik_nesil.value()
            a["kinetik"] = kin

        # Kaynak sozlugu BASTAN YAZILMAZ: gorunmeyen alanlar (or. ozdegerde
        # siddet, 2B'de z konumu) dosyadaki gibi kalir.
        kay = a.setdefault("kaynak", {})
        if self.kaynak_tur.currentData() == "nokta":
            kay["tur"] = "nokta"
            eski_z = (kay.get("konum") or [0.0, 0.0, 0.0])[2]
            kay["konum"] = [self.kx.value(), self.ky.value(),
                            self.kz.value() if self._mesh_nz_anlamli() else eski_z]
            kay.pop("alt", None)
            kay.pop("ust", None)
        else:
            kay["tur"] = self.kaynak_tur.currentData()
            kay.setdefault("alt", None)
            kay.setdefault("ust", None)
        if self.kaynak_parcacik.count() > 1 or kay.get("parcacik") is None:
            kay["parcacik"] = self.kaynak_parcacik.currentData()
        if alan["kaynak_siddeti"]:
            kay["kuvvet"] = self.kaynak_kuvvet.deger(1.0)
        kay["enerji"] = self._tayf_oku()
        aci = dict(kay.get("aci") or {})
        aci["tur"] = self.aci_tur.currentData()
        if aci["tur"] != "izotropik":
            aci["yon"] = [self.ax.value(), self.ay.value(), self.az.value()]
        if aci["tur"] == "koni":
            aci["koni_aci"] = self.koni_aci.value()
        kay["aci"] = aci

        if self.guc_kutu.isVisibleTo(self) or alan["guc_dagilimi"]:
            g = dict(self.spec.get("guc_dagilimi") or {})
            g["var"] = self.guc_var.isChecked()
            if self.guc_var.isChecked():
                # YALNIZ yeni bicim yazilir (guc_dagilimi.cubuklar); eski tek
                # alan (cubuk/bolge) bellekte de birakilmaz.
                g["cubuklar"] = self._guc_hedeflerini_oku(g)
                g.pop("cubuk", None)
                g.pop("bolge", None)
                g["skor"] = self.guc_skor.currentData()
                if alan["eksenel_dilim"]:
                    g["eksenel_dilim"] = self.guc_dilim.value()
                g["toplam_guc"] = self.guc_toplam.value() or None
            self.spec["guc_dagilimi"] = g

        # Mod degisimi kaynak seceneklerini (foton, kutu) ve hassasiyet
        # eslesmesini degistirir: kutular spec'ten tazelenir.
        self._yukleniyor = True
        try:
            secenek = uygunluk.kaynak_secenekleri(self.spec)
            tur_adlari = {"nokta": "Nokta kaynak", "kutu": "Kutu (yalnızca fisil bölgeler)"}
            self._kutu_doldur(self.kaynak_tur,
                              [(t, tur_adlari.get(t, t)) for t in secenek["turler"]],
                              kay.get("tur", "nokta"))
            parcacik_adlari = {"neutron": "Nötron", "photon": "Foton (gama)"}
            self._kutu_doldur(self.kaynak_parcacik,
                              [(p, parcacik_adlari.get(p, p)) for p in secenek["parcaciklar"]],
                              kay.get("parcacik") or "neutron")
            if mod_degisti:
                # sabit kaynakta pasif cevrim eslesmeye girmez
                self._hassasiyeti_goster()
        finally:
            self._yukleniyor = False
        self._gorunurluk()
        self.bildir()
