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

# Hesap hassasiyeti onayarlari: (anahtar, ad, parcacik, cevrim, pasif)
HASSASIYET = [
    ("hizli", "Hızlı deneme", 1000, 60, 20),
    ("normal", "Normal", 10000, 150, 40),
    ("hassas", "Hassas", 50000, 300, 80),
]
OZEL = "ozel"

# sigma_k [pcm] ~ SIGMA_KATSAYISI / sqrt(parcacik x aktif cevrim)
# (pwr_pinhucre olcumu; ayrinti modul basliginda)
SIGMA_KATSAYISI = 9.0e4

# Skorlar: (OpenMC adi, gorunen ad)
SKORLAR = [
    ("flux", "Akı (flux)"),
    ("fission", "Fisyon (fission)"),
    ("absorption", "Soğurma (absorption)"),
    ("nu-fission", "Fisyon nötronu üretimi (nu-fission)"),
    ("scatter", "Saçılma (scatter)"),
    ("total", "Toplam etkileşim (total)"),
    ("elastic", "Esnek saçılma (elastic)"),
    ("(n,gamma)", "Işınımsal yakalama (n,gamma)"),
    ("(n,2n)", "(n,2n) tepkimesi"),
    ("heating", "Isınma (heating)"),
    ("kappa-fission", "Fisyon enerjisi (kappa-fission)"),
    ("fission-q-prompt", "Anlık fisyon enerjisi (fission-q-prompt)"),
    ("damage-energy", "Hasar enerjisi (damage-energy)"),
]
_SKOR_ADI = dict(SKORLAR)

# Skor setleri: (anahtar, ad, skorlar)
SKOR_SETLERI = [
    ("aki", "Akı", ["flux"]),
    ("reaksiyon", "Reaksiyon hızları", ["fission", "absorption", "nu-fission"]),
    ("isi", "Isı / güç", ["kappa-fission", "heating"]),
]

SICAKLIK_YONTEMLERI = [
    ("interpolation", "Ara değer (interpolation)"),
    ("nearest", "En yakın sıcaklık (nearest)"),
]

GUC_SKORLARI = [
    ("kappa-fission", "Fisyon enerjisi (kappa-fission)"),
    ("fission-q-recoverable", "Geri kazanılabilir fisyon enerjisi (fission-q-recoverable)"),
    ("fission-q-prompt", "Anlık fisyon enerjisi (fission-q-prompt)"),
    ("heating-local", "Yerel ısınma (heating-local)"),
]

_FILTRE_ADI = {"malzeme": "malzeme", "hucre": "hücre", "enerji": "enerji",
               "mesh": "mesh"}


def hassasiyet_bul(parcacik, cevrim, pasif, ozdeger=True):
    """Degerlere uyan onayarin anahtari; uyan yoksa OZEL. Sabit kaynakta pasif
    cevrim kullanilmadigi icin karsilastirmaya girmez."""
    for anahtar, _ad, n, c, p in HASSASIYET:
        if n == parcacik and c == cevrim and (p == pasif or not ozdeger):
            return anahtar
    return OZEL


def belirsizlik_pcm(parcacik, cevrim, pasif):
    """Beklenen k-eff belirsizligi [pcm] (olcume dayali kaba tahmin); aktif
    cevrim yoksa None."""
    aktif = int(cevrim) - int(pasif)
    if parcacik <= 0 or aktif <= 0:
        return None
    return SIGMA_KATSAYISI / math.sqrt(float(parcacik) * aktif)


def _binlik(n):
    """10000 -> '10 000' (Turkce yazim: binlik ayraci bosluk)."""
    return "{:,}".format(int(n)).replace(",", " ")


def _pcm_yuvarla(s):
    if s >= 100:
        return int(round(s, -1))
    if s >= 20:
        return int(round(s / 5.0) * 5)
    return int(round(s))


class AyarSekmesi(SekmeTabani):

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
            "ölçer. Yakınsamamış kaynak k-eff'i YANLI tahmin ettirir ve bu başka\n"
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
        self.koni_aci.setToolTip("Koninin YARI açılımı. Katı açıda düzgün dağılım kullanılır.")

        # ================= guc dagilimi =================
        self.guc_var = QtWidgets.QCheckBox("Çubuk bazlı güç dağılımı hesapla (F_ΔH, 3B'de F_q)")
        self.guc_var.setToolTip(
            "Kafeste tekrarlanan yakıt çubuğunun HER örneği ayrı sayılır\n"
            "(DistribcellFilter). Buradan tepe faktörleri çıkar:\n"
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
            "Toplam güç, MODELİN KAPSADIĞI bölgenin gücüdür — tüm korun değil. "
            "Örnek: 3400 MWth / 193 demet = 17,6 MW; tek demetlik modelde 17.6e6 W "
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

    # ------------------------------------------------------------------
    # yerlesim
    # ------------------------------------------------------------------
    @staticmethod
    def _sar(duzen):
        w = QtWidgets.QWidget()
        duzen.setContentsMargins(0, 0, 0, 0)
        w.setLayout(duzen)
        return w

    def _uclu(self, alanlar):
        d = QtWidgets.QHBoxLayout()
        for e, w in alanlar:
            etiket = QtWidgets.QLabel(e)
            d.addWidget(etiket)
            d.addWidget(w)
            w._etiket = etiket
        d.addStretch(1)
        return self._sar(d)

    def _yerlesim_kur(self):
        # ---------- hesap ----------
        hesap = QtWidgets.QFormLayout()
        self._hesap_form = hesap
        hesap.addRow("Hesap türü:", self.mod)
        hesap.addRow("Hesap hassasiyeti:", self.hassasiyet)
        hesap.addRow("", self.hassasiyet_ozet)
        hesap.addRow("Parçacık / çevrim:", self.parcacik)
        hesap.addRow("Toplam çevrim:", self.cevrim)
        hesap.addRow("Pasif çevrim:", self.pasif)
        hesap.addRow(self.kinetik_var)

        # ---------- kaynak ----------
        kaynak = QtWidgets.QFormLayout()
        self._kaynak_form = kaynak
        kaynak.addRow("Kaynak tipi:", self.kaynak_tur)
        self.konum_satiri = self._uclu((("x", self.kx), ("y", self.ky), ("z", self.kz)))
        kaynak.addRow("Nokta konumu:", self.konum_satiri)
        kaynak.addRow("Parçacık:", self.kaynak_parcacik)
        kaynak.addRow("Kaynak şiddeti [1/s]:", self.kaynak_kuvvet)

        # enerji tayfi + acisal dagilim: ozdegerde Gelismis'e, sabit kaynakta
        # kaynak bolumune tasinan tek bir kutu
        self.tayf_kutu = QtWidgets.QWidget()
        tf = QtWidgets.QFormLayout(self.tayf_kutu)
        tf.setContentsMargins(0, 0, 0, 0)
        self._tayf_form = tf
        tf.addRow("Enerji tayfı:", self.tayf)
        tf.addRow("", self.tayf_yigin)
        tf.addRow("", self.tayf_ozet)
        tf.addRow("Açısal dağılım:", self.aci_tur)
        self.yon_satiri = self._uclu((("u", self.ax), ("v", self.ay), ("w", self.az)))
        tf.addRow("Yön:", self.yon_satiri)
        tf.addRow("Koni yarı açısı:", self.koni_aci)
        self._kaynak_tayf_yeri = QtWidgets.QVBoxLayout()
        self._kaynak_tayf_yeri.setContentsMargins(0, 0, 0, 0)

        # ---------- gelismis ----------
        self.gelismis = GelismisBolum("ayar_gelismis")
        gf = QtWidgets.QFormLayout()
        self._gelismis_form = gf
        gf.addRow("Rastgele tohum:", self.tohum)
        gf.addRow("Sıcaklık yöntemi:", self.sicaklik_yontemi)
        gf.addRow(self.entropi_var)
        self.entropi_satiri = self._uclu((("nx", self.entropi_nx), ("ny", self.entropi_ny),
                                          ("nz", self.entropi_nz)))
        ent = QtWidgets.QHBoxLayout()
        ent.addWidget(self.entropi_oto)
        ent.addWidget(self.entropi_satiri, 1)
        self.entropi_agi = self._sar(ent)
        gf.addRow("Entropi ağı:", self.entropi_agi)
        gf.addRow("IFP nesil sayısı:", self.kinetik_nesil)
        gw = QtWidgets.QWidget()
        gw.setLayout(gf)
        gf.setContentsMargins(0, 0, 0, 0)
        self.gelismis.ekle(gw)
        self.gelismis_tayf_baslik = baslik("Başlangıç kaynağının enerjisi ve yönü")
        self.gelismis.ekle(self.gelismis_tayf_baslik)
        self.gelismis_tayf_not = ipucu(
            "Özdeğer hesabında bunlar yalnızca başlangıç tahminidir; pasif çevrimlerde "
            "gerçek fisyon tayfına döner ve k-eff'i etkilemez.")
        self.gelismis.ekle(self.gelismis_tayf_not)
        self._gelismis_tayf_yeri = QtWidgets.QVBoxLayout()
        self._gelismis_tayf_yeri.setContentsMargins(0, 0, 0, 0)
        gt = QtWidgets.QWidget()
        gt.setLayout(self._gelismis_tayf_yeri)
        self.gelismis.ekle(gt)

        sol = QtWidgets.QVBoxLayout()
        sol.addWidget(baslik("Hesap"))
        sol.addLayout(hesap)
        sol.addWidget(ayrac())
        self.kaynak_baslik = baslik("Kaynak")
        sol.addWidget(self.kaynak_baslik)
        sol.addLayout(kaynak)
        sol.addLayout(self._kaynak_tayf_yeri)
        sol.addWidget(ayrac())
        sol.addWidget(self.gelismis)
        sol.addStretch(1)

        # ---------- guc dagilimi ----------
        self.guc_kutu = QtWidgets.QWidget()
        gk = QtWidgets.QVBoxLayout(self.guc_kutu)
        gk.setContentsMargins(0, 0, 0, 0)
        gk.addWidget(baslik("Güç dağılımı"))
        guc_form = QtWidgets.QFormLayout()
        guc_form.addRow(self.guc_var)
        self._guc_form = guc_form
        for etiket, w, ad in (("Hedef çubuk:", self.guc_cubuk, "cubuk"),
                              ("Eksenel dilim:", self.guc_dilim, "dilim"),
                              ("Toplam güç:", self.guc_toplam, "toplam")):
            e = QtWidgets.QLabel(etiket)
            self.guc_etiketler[ad] = e
            guc_form.addRow(e, w)
        gk.addLayout(guc_form)
        self.guc_not.setMinimumWidth(1)
        gk.addWidget(self.guc_not)
        gk.addWidget(self.guc_uyari)
        self.guc_gelismis = GelismisBolum("ayar_guc_gelismis")
        ggf = QtWidgets.QFormLayout()
        for etiket, w, ad in (("Hedef bölge:", self.guc_bolge, "bolge"),
                              ("Skor:", self.guc_skor, "skor")):
            e = QtWidgets.QLabel(etiket)
            self.guc_etiketler[ad] = e
            ggf.addRow(e, w)
        ggw = QtWidgets.QWidget()
        ggf.setContentsMargins(0, 0, 0, 0)
        ggw.setLayout(ggf)
        self.guc_gelismis.ekle(ggw)
        gk.addWidget(self.guc_gelismis)
        gk.addWidget(ayrac())

        # ---------- tally'ler ----------
        d_t_ekle = QtWidgets.QPushButton("+ Tally")
        d_t_sil = QtWidgets.QPushButton("Sil")
        self.d_t_sil = d_t_sil
        d_t_ekle.clicked.connect(self._tally_ekle)
        d_t_sil.clicked.connect(self._tally_sil)
        t_dugme = QtWidgets.QHBoxLayout()
        t_dugme.addWidget(d_t_ekle)
        t_dugme.addWidget(d_t_sil)
        t_dugme.addStretch(1)

        t_form = QtWidgets.QFormLayout()
        self._t_form = t_form
        t_form.addRow("Ad:", self.t_ad)
        t_form.addRow("Ne ölçülsün:", self.t_set)
        t_form.addRow("", self.t_set_ozet)
        t_form.addRow("Skorlar:", self.t_skor)
        t_form.addRow(self.t_enerji_var)
        t_form.addRow("Grup sınırları [eV]:", self.t_enerji)
        t_form.addRow(self.t_mesh_var)
        self.mesh_satiri = self._uclu((("nx", self.t_mesh_nx), ("ny", self.t_mesh_ny),
                                       ("nz", self.t_mesh_nz)))
        t_form.addRow("Ağ bölmeleri:", self.mesh_satiri)
        t_form.addRow(self.t_diger)
        self.tally_duzenleyici = QtWidgets.QWidget()
        self.tally_duzenleyici.setLayout(t_form)
        t_form.setContentsMargins(0, 0, 0, 0)

        tally_sol = QtWidgets.QVBoxLayout()
        tally_sol.addWidget(self.tally_liste, 1)
        tally_sol.addLayout(t_dugme)
        tally_bolucu = QtWidgets.QHBoxLayout()
        tally_bolucu.addLayout(tally_sol, 0)
        tally_sag = QtWidgets.QVBoxLayout()
        tally_sag.addWidget(self.tally_bos)
        tally_sag.addWidget(self.tally_duzenleyici)
        tally_sag.addStretch(1)
        tally_bolucu.addLayout(tally_sag, 1)

        sag = QtWidgets.QVBoxLayout()
        sag.addWidget(self.guc_kutu)
        sag.addWidget(baslik("Tally'ler (ölçülecek büyüklükler)"))
        sag.addLayout(tally_bolucu)
        sag.addStretch(1)

        sol_k = QtWidgets.QWidget()
        sol_k.setLayout(sol)
        sag_k = QtWidgets.QWidget()
        sag_k.setLayout(sag)
        bolucu = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        bolucu.addWidget(sol_k)
        bolucu.addWidget(sag_k)
        bolucu.setStretchFactor(0, 4)
        bolucu.setStretchFactor(1, 5)
        bolucu.setSizes([430, 520])
        bolucu.setChildrenCollapsible(False)
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(bolucu)
        self._tayfi_tasi(self._gelismis_tayf_yeri)

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

    def _tayfi_tasi(self, yer):
        """Tayf/aci kutusunu kaynak bolumu ile Gelismis arasinda tasir."""
        if self._tayf_yeri is yer:
            return
        if self._tayf_yeri is not None:
            self._tayf_yeri.removeWidget(self.tayf_kutu)
        yer.addWidget(self.tayf_kutu)
        self._tayf_yeri = yer

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

    def _guc_doldur(self):
        g = self.spec.get("guc_dagilimi") or {}
        self.guc_var.setChecked(bool(g.get("var")))
        cubuklar = uygunluk.guc_cubuklari(self.spec)
        self._kutu_doldur(self.guc_cubuk, [(c, c) for c in cubuklar], g.get("cubuk"),
                          " (fisil değil ya da kafeste değil)")
        self._guc_bolgeleri_doldur(g.get("bolge"))
        self._kutu_doldur(self.guc_skor, GUC_SKORLARI, g.get("skor") or "kappa-fission",
                          " (bilinmeyen)")
        self.guc_dilim.setValue(g.get("eksenel_dilim") or 20)
        self.guc_toplam.setValue(g.get("toplam_guc") or 0.0)

    def _guc_bolgeleri_doldur(self, secili=None):
        """Secili cubugun bolgeleri (1'den numarali, malzeme adiyla)."""
        eski = self.guc_bolge.blockSignals(True)
        try:
            self.guc_bolge.clear()
            ad = self.guc_cubuk.currentData()
            c = sema.cubuk_bul(self.spec, ad) if ad else None
            if c:
                for i, b in enumerate(c["bolgeler"]):
                    etiket = "%d. bölge — %s" % (i + 1, b.get("malzeme") or "boş")
                    if b.get("r"):
                        etiket += ("  (r = %.4f cm)" % b["r"]).replace(".", ",")
                    else:
                        etiket += "  (dış bölge)"
                    self.guc_bolge.addItem(etiket, i)
            if secili is not None:
                j = self.guc_bolge.findData(secili)
                if j >= 0:
                    self.guc_bolge.setCurrentIndex(j)
        finally:
            self.guc_bolge.blockSignals(eski)

    def _tallyleri_doldur(self):
        eski_satir = self.tally_liste.currentRow()
        eski = self.tally_liste.blockSignals(True)
        try:
            self.tally_liste.clear()
            for t in self.spec.get("tallyler", []):
                self.tally_liste.addItem(t["ad"])
        finally:
            self.tally_liste.blockSignals(eski)
        n = self.tally_liste.count()
        if n:
            self.tally_liste.setCurrentRow(min(max(eski_satir, 0), n - 1))
            self._tally_secildi(self.tally_liste.currentRow())
        self._tally_gorunurluk()

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

    def _guc_gorunurluk(self):
        alan = self._alan()
        g = self.spec.get("guc_dagilimi") or {}
        # Uygun modelde gorunur; uygun olmayan modelde yalnizca dosyada acik
        # birakilmissa (kullanici kapatabilsin diye).
        gorunur = alan["guc_dagilimi"] or bool(g.get("var"))
        self.guc_kutu.setVisible(gorunur)
        acik = self.guc_var.isChecked()
        gf = self._guc_form
        for w in (self.guc_cubuk, self.guc_bolge, self.guc_skor, self.guc_dilim,
                  self.guc_toplam, self.guc_not):
            w.setEnabled(acik)
        for e in self.guc_etiketler.values():
            e.setEnabled(acik)
        gf.setRowVisible(self.guc_cubuk, acik)
        gf.setRowVisible(self.guc_dilim, acik and alan["eksenel_dilim"])
        gf.setRowVisible(self.guc_toplam, acik)
        self.guc_not.setVisible(acik)
        self.guc_gelismis.setVisible(acik)
        self.guc_dilim.setEnabled(acik and alan["eksenel_dilim"])
        self.guc_etiketler["dilim"].setEnabled(acik and alan["eksenel_dilim"])
        uyari = ""
        if acik and not alan["guc_dagilimi"]:
            uyari = ("Bu modelde güç dağılımı hesaplanamaz: kafeste tekrarlanan "
                     "fisil bir çubuk yok. Kutuyu kapatın.")
        self.guc_uyari.setText(uyari)
        self.guc_uyari.setVisible(bool(uyari))
        self.guc_var.setText("Çubuk bazlı güç dağılımı hesapla (F_ΔH%s)"
                             % (", F_q" if alan["eksenel_dilim"] else ""))

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
    # kaynak tayfi
    # ------------------------------------------------------------------
    @staticmethod
    def _sayi_listesi(metin):
        cikti = []
        for parca in (metin or "").replace(";", ",").split(","):
            parca = parca.strip()
            if not parca:
                continue
            try:
                cikti.append(float(parca))
            except ValueError:
                pass
        return cikti

    def _tayf_oku(self):
        """Arayuzdeki SECILI tayfin alanlarini spec sozlugune yazar; diger
        tayflarin (gorunmeyen) alanlari dosyadaki gibi kalir."""
        e = dict((self.spec["ayarlar"].get("kaynak") or {}).get("enerji") or {})
        tur = self.tayf.currentData()
        e["tur"] = tur
        if tur == "watt":
            e["a"] = self.watt_a.deger()
            e["b"] = self.watt_b.value()
        elif tur == "maxwell":
            e["theta"] = self.maxwell_theta.deger()
        elif tur == "tek":
            e["enerji"] = self.tek_enerji.deger()
        elif tur == "ayrik":
            noktalar = []
            for parca in (self.ayrik_metin.text() or "").replace(";", ",").split(","):
                if ":" not in parca:
                    continue
                a_, b_ = parca.split(":", 1)
                try:
                    noktalar.append([float(a_), float(b_)])
                except ValueError:
                    pass
            e["noktalar"] = noktalar
        elif tur == "histogram":
            e["kenarlar"] = self._sayi_listesi(self.hist_kenar.text())
            e["degerler"] = self._sayi_listesi(self.hist_deger.text())
        elif tur == "fuzyon":
            e["e0"] = self.fuzyon_e0.deger()
            e["kutle_orani"] = self.fuzyon_kutle.value()
            e["iyon_sicaklik"] = self.fuzyon_kt.deger()
        return e

    def _tayf_gorunurluk(self):
        """Yalnizca secili tayfin alanlari gorunur; ozet satiri guncellenir."""
        self.tayf_yigin.setCurrentIndex(max(self.tayf.currentIndex(), 0))
        # Yigin en buyuk sayfanin yuksekligini ayirir (fuzyon: 3 satir); Watt
        # sayfasinin altinda bos alan kaliyordu. Yalnizca secili sayfa sayilir.
        for i in range(self.tayf_yigin.count()):
            sayfa = self.tayf_yigin.widget(i)
            pol = (QtWidgets.QSizePolicy.Preferred if i == self.tayf_yigin.currentIndex()
                   else QtWidgets.QSizePolicy.Ignored)
            sayfa.setSizePolicy(QtWidgets.QSizePolicy.Preferred, pol)
        self.tayf_yigin.updateGeometry()
        aci = self.aci_tur.currentData()
        self._tayf_form.setRowVisible(self.yon_satiri, aci != "izotropik")
        self._tayf_form.setRowVisible(self.koni_aci, aci == "koni")
        sabit = not self._ozdeger()
        e = self._tayf_oku()
        try:
            _kaynak.enerji_dagilimi(e)
            ort = _kaynak.ortalama_enerji(e)
            metin = ("Ortalama enerji: %s" % _kaynak.enerji_metni(ort)) if ort else ""
            if sabit:
                if self.kaynak_kuvvet.deger(1.0) == 1.0:
                    metin += "\nŞiddet 1 — sonuçlar kaynak parçacığı başına kalır."
                else:
                    metin += ("\nSonuçlar mutlak birimde olur (OpenMC şiddeti kendisi "
                              "uygular, ayrıca çarpmayın).")
            self.tayf_ozet.setText(metin.strip())
            self.tayf_ozet.setStyleSheet("")
        except Exception as hata:
            self.tayf_ozet.setText("Tayf kurulamadı: %s" % hata)
            self.tayf_ozet.setStyleSheet("color: #d04437;")

    # ------------------------------------------------------------------
    # kayit -- yalnizca GORUNEN alanlar yazilir
    # ------------------------------------------------------------------
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
                g["cubuk"] = self.guc_cubuk.currentData()
                g["bolge"] = self.guc_bolge.currentData() or 0
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

    def _guc_cubuk_degisti(self, *_):
        if self._yukleniyor:
            return
        self._guc_bolgeleri_doldur(0)
        self._kaydet()

    # ------------------------------------------------------------------
    # tally'ler
    # ------------------------------------------------------------------
    def _skor_listesi_kur(self, ekstra):
        """Skor listesi: bilinen skorlar + tally'deki bilinmeyenler (korunsun)."""
        eski = self.t_skor.blockSignals(True)
        try:
            self.t_skor.clear()
            for veri, ad in SKORLAR + [(s, s) for s in ekstra if s not in _SKOR_ADI]:
                oge = QtWidgets.QListWidgetItem(ad)
                oge.setData(QtCore.Qt.UserRole, veri)
                self.t_skor.addItem(oge)
        finally:
            self.t_skor.blockSignals(eski)

    def _secili_skorlar(self):
        return [self.t_skor.item(i).data(QtCore.Qt.UserRole)
                for i in range(self.t_skor.count()) if self.t_skor.item(i).isSelected()]

    def _skorlari_sec(self, skorlar):
        eski = self.t_skor.blockSignals(True)
        try:
            self.t_skor.clearSelection()
            for i in range(self.t_skor.count()):
                oge = self.t_skor.item(i)
                oge.setSelected(oge.data(QtCore.Qt.UserRole) in skorlar)
        finally:
            self.t_skor.blockSignals(eski)

    @staticmethod
    def _skor_seti_bul(skorlar):
        for anahtar, _ad, s in SKOR_SETLERI:
            if set(s) == set(skorlar):
                return anahtar
        return OZEL

    def _secili_tally(self):
        i = self.tally_liste.currentRow()
        tallyler = self.spec.get("tallyler", []) if self.spec else []
        return tallyler[i] if 0 <= i < len(tallyler) else None

    def _tally_secildi(self, _satir):
        t = self._secili_tally()
        if t is None:
            self._tally_gorunurluk()
            return
        eski = self._yukleniyor
        self._yukleniyor = True
        try:
            self.t_ad.setText(t["ad"])
            skorlar = list(t.get("skorlar", []))
            self._skor_listesi_kur(skorlar)
            self._skorlari_sec(skorlar)
            self.t_set.setCurrentIndex(self.t_set.findData(self._skor_seti_bul(skorlar)))
            enerji = next((f for f in t.get("filtreler", []) if f["tur"] == "enerji"), None)
            self.t_enerji_var.setChecked(bool(enerji))
            if enerji:
                self.t_enerji.setText(", ".join("%.12g" % g for g in enerji["gruplar"]))
                self.t_enerji.setCursorPosition(0)
            mesh = next((f for f in t.get("filtreler", []) if f["tur"] == "mesh"), None)
            self.t_mesh_var.setChecked(bool(mesh))
            if mesh:
                self.t_mesh_nx.setValue(mesh["boyut"][0])
                self.t_mesh_ny.setValue(mesh["boyut"][1])
                self.t_mesh_nz.setValue(mesh["boyut"][2])
        finally:
            self._yukleniyor = eski
        self._tally_gorunurluk()

    def _tally_gorunurluk(self):
        t = self._secili_tally()
        var = t is not None
        self.tally_bos.setVisible(not (self.spec or {}).get("tallyler"))
        self.tally_duzenleyici.setVisible(var)
        self.d_t_sil.setEnabled(var)
        if not var:
            return
        tf = self._t_form
        ozel = self.t_set.currentData() == OZEL
        tf.setRowVisible(self.t_skor, ozel)
        secili = self._secili_skorlar()
        self.t_set_ozet.setText("" if ozel else
                                "Skorlar: " + ", ".join(_SKOR_ADI.get(s, s) for s in secili))
        tf.setRowVisible(self.t_set_ozet, not ozel)
        tf.setRowVisible(self.t_enerji, self.t_enerji_var.isChecked())
        tf.setRowVisible(self.mesh_satiri, self.t_mesh_var.isChecked())
        uc_b = self._mesh_nz_anlamli()
        self.t_mesh_nz.setVisible(uc_b)
        self.t_mesh_nz._etiket.setVisible(uc_b)
        diger = [f.get("tur") for f in t.get("filtreler", [])
                 if f.get("tur") not in ("enerji", "mesh")]
        self.t_diger.setText("Ayrıca dosyadan gelen filtre: %s (korunur)."
                             % ", ".join(_FILTRE_ADI.get(d, d) for d in diger) if diger else "")
        tf.setRowVisible(self.t_diger, bool(diger))

    def _skor_seti_secildi(self, *_):
        if self._yukleniyor:
            return
        anahtar = self.t_set.currentData()
        for a_, _ad, s in SKOR_SETLERI:
            if a_ == anahtar:
                self._skorlari_sec(s)
                break
        self._tally_kaydet()

    def _tally_kaydet(self, *_):
        if self._yukleniyor:
            return
        t = self._secili_tally()
        if t is None:
            return
        t["ad"] = self.t_ad.text().strip() or t["ad"]
        secili = self._secili_skorlar() or ["flux"]
        # Skor kumesi degismediyse dosyadaki sira korunur.
        if set(secili) != set(t.get("skorlar") or []):
            anahtar = self.t_set.currentData()
            hazir = next((s for a_, _ad, s in SKOR_SETLERI if a_ == anahtar), None)
            t["skorlar"] = list(hazir) if hazir and set(hazir) == set(secili) else secili
        eski = list(t.get("filtreler", []))
        eski_enerji = next((f for f in eski if f.get("tur") == "enerji"), None)
        eski_mesh = next((f for f in eski if f.get("tur") == "mesh"), None)
        yeni = {"enerji": None, "mesh": None}
        if self.t_enerji_var.isChecked():
            gruplar = self._sayi_listesi(self.t_enerji.text())
            # Okunamayan metin mevcut filtreyi SILMEZ.
            yeni["enerji"] = (sema.filtre_enerji(sorted(gruplar)) if len(gruplar) >= 2
                              else eski_enerji)
            if yeni["enerji"] is None:
                yeni["enerji"] = sema.filtre_enerji([0.0, 0.625, 2.0e7])
            if eski_enerji is not None and yeni["enerji"]["gruplar"] == eski_enerji.get("gruplar"):
                yeni["enerji"] = eski_enerji
        if self.t_mesh_var.isChecked():
            eski_b = list((eski_mesh or {}).get("boyut") or [10, 10, 1])
            boyut = [self.t_mesh_nx.value(), self.t_mesh_ny.value(),
                     self.t_mesh_nz.value() if self._mesh_nz_anlamli() else eski_b[2]]
            if eski_mesh is not None:
                # Arayuzde gosterilmeyen alanlar (eski dosyalarin acik alt/ust
                # sinirlari, "otomatik") korunur; yalnizca bolme sayisi degisir.
                yeni["mesh"] = dict(eski_mesh, boyut=boyut)
            else:
                # Sinirlar model KURULURKEN turetilir (kurucu.tally_mesh_sinirlari).
                yeni["mesh"] = sema.filtre_mesh_otomatik(boyut)
        # Bu editorun YONETMEDIGI filtre turleri (or. malzeme) yerinde korunur.
        filtreler, konan = [], set()
        for f in eski:
            tur = f.get("tur")
            if tur in yeni:
                if yeni[tur] is not None and tur not in konan:
                    filtreler.append(yeni[tur])
                    konan.add(tur)
            else:
                filtreler.append(f)
        for tur in ("enerji", "mesh"):
            if yeni[tur] is not None and tur not in konan:
                filtreler.append(yeni[tur])
        t["filtreler"] = filtreler
        i = self.tally_liste.currentRow()
        if i >= 0:
            self.tally_liste.item(i).setText(t["ad"])
        self._tally_gorunurluk()
        self.bildir()

    def _tally_ekle(self):
        mevcut = {t["ad"] for t in self.spec.get("tallyler", [])}
        ad, i = "tally", 1
        while ad in mevcut:
            i += 1
            ad = "tally_%d" % i
        self.spec.setdefault("tallyler", []).append(sema.tally(ad, ["flux"]))
        self.spec_yukle(self.spec)
        self.tally_liste.setCurrentRow(self.tally_liste.count() - 1)
        self.bildir()

    def _tally_sil(self):
        i = self.tally_liste.currentRow()
        if i < 0:
            return
        self.spec["tallyler"].pop(i)
        self.spec_yukle(self.spec)
        self.bildir()
