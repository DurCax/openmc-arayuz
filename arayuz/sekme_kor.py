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
from arayuz import izgara
from arayuz.kor_altigen import AltigenKorHaritasi
from arayuz.ortak import SekmeTabani, baslik, ipucu, sayi, tamsayi

# Sinir kosullarinin gorunen adlari (OpenMC anahtar sozcugu parantezde).
SINIR_ADLARI = {
    "reflective": "Yansıtıcı (reflective)",
    "vacuum": "Vakum (vacuum)",
    "white": "Beyaz (white)",
    "periodic": "Periyodik (periodic)",
}

# Yukseklik secimi: (veri, gorunen ad)
YUKSEKLIK_MODLARI = [
    ("2B", "2B (sonsuz yükseklik)"),
    ("3B", "3B, tek bölge"),
    ("katmanli", "3B, katmanlı (yansıtıcı / örtü / plenum)"),
]

_BOS_ETIKET = "Boş (madde yok)"


def _tur_adi(tur):
    """Kor turunun model basligindaki "Turu degistir..." menusuyle AYNI adi."""
    try:
        from arayuz.ana_pencere import TUR_ADLARI
        return TUR_ADLARI.get(tur, tur or "tanımsız")
    except Exception:                                   # pragma: no cover
        return tur or "tanımsız"


def _tablo_yuksekligi(tablo, en_cok_satir):
    """Tablo yuksekligi satir sayisina uysun (en_cok_satir'a kadar kaydirmasiz)."""
    n = max(1, min(tablo.rowCount(), en_cok_satir))
    satir = tablo.verticalHeader().defaultSectionSize()
    if tablo.rowCount():
        satir = max(satir, max(tablo.rowHeight(i) for i in range(tablo.rowCount())))
    tablo.setFixedHeight(tablo.horizontalHeader().sizeHint().height()
                         + n * satir + 2 * tablo.frameWidth() + 2)


class KorSekmesi(SekmeTabani):

    KONU = "kor"
    # "Türü değiştir…" baglantisi: ana pencere model basligindaki tur
    # menusunu acar (tur yalnizca oradan degisir -- tek yol, tek kural).
    tur_degistir_istendi = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tur = None

        # --- tur bilgisi (degistirilemez; model basligindan degisir) ---
        self.tur_etiket = QtWidgets.QLabel("-")
        self.tur_etiket.setTextFormat(QtCore.Qt.RichText)
        self.tur_etiket.setWordWrap(True)
        self.tur_etiket.setTextInteractionFlags(
            QtCore.Qt.LinksAccessibleByMouse | QtCore.Qt.LinksAccessibleByKeyboard)
        self.tur_etiket.linkActivated.connect(lambda _b: self.tur_degistir_istendi.emit())

        # --- ture ozgu alanlar ---
        self.cubuk = QtWidgets.QComboBox()
        self.plaka = QtWidgets.QComboBox()
        self.demet = QtWidgets.QComboBox()
        self.adim = sayi(1.26, 5, 0.0001, 1000.0, 0.01, "cm")
        self.tb_dolgu = QtWidgets.QComboBox()
        self.tb_kor_r = sayi(16.0, 4, 0.01, 10000.0, 0.5, "cm")

        # --- kor haritasi (kare_kafes) ---
        self.palet = izgara.ParcaPaleti()
        self.palet.setMaximumWidth(230)
        self.izgara = izgara.KareIzgara()
        self.izgara.setMinimumHeight(260)
        self.izgara.etiketleri_goster(True)
        self.nx = tamsayi(3, 1, 100, 1, "sütun")
        self.ny = tamsayi(3, 1, 100, 1, "satır")
        self.nx.setToolTip("Haritanın sütun sayısı. Büyütünce yeni hücreler "
                           "paletteki seçili parçayla dolar.")
        self.ny.setToolTip("Haritanın satır sayısı. Büyütünce yeni hücreler "
                           "paletteki seçili parçayla dolar.")
        self.d_doldur = QtWidgets.QPushButton("Tümünü seçili parçayla doldur")
        # --- kor haritasi (altigen_kafes; arayuz/kor_altigen.py) ---
        # onay testlerde degistirilen self._onay_al'dan CAGRI ANINDA okunur
        self.altigen_harita = AltigenKorHaritasi(lambda b, m: self._onay_al(b, m))

        # --- kuresel kabuklar (salt okunur) ---
        self.kabuk_tablo = QtWidgets.QTableWidget(0, 2)
        self.kabuk_tablo.setHorizontalHeaderLabels(["Dış yarıçap [cm]", "Malzeme"])
        self.kabuk_tablo.horizontalHeader().setStretchLastSection(True)
        self.kabuk_tablo.verticalHeader().setVisible(False)
        self.kabuk_tablo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        # --- yukseklik (tek secim) ---
        self.yukseklik_modu = QtWidgets.QComboBox()
        for veri, ad in YUKSEKLIK_MODLARI:
            self.yukseklik_modu.addItem(ad, veri)
        self.yukseklik_modu.setToolTip(
            "2B: model eksenel yönde sonsuzdur (k∞ / kesit hesabı).\n"
            "3B, tek bölge: aktif yükseklik H boyunca tek eksenel bölge.\n"
            "3B, katmanlı: kor alttan üste katmanlara ayrılır; yükseklik\n"
            "katmanların toplamıdır.")
        self.yukseklik = sayi(366.0, 3, 0.01, 10000.0, 1.0, "cm")
        self.yukseklik.setToolTip("Modelin eksenel yüksekliği (z = −H/2 … +H/2).")

        # --- eksenel katmanlar ---
        self.katman_tablo = QtWidgets.QTableWidget(0, 3)
        self.katman_tablo.setHorizontalHeaderLabels(["Ad", "Yükseklik", "Dolgu"])
        self.katman_tablo.horizontalHeader().setStretchLastSection(True)
        self.katman_tablo.verticalHeader().setVisible(False)
        self.katman_tablo.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.katman_tablo.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.katman_tablo.setMinimumHeight(150)
        self.d_kat_ekle = QtWidgets.QPushButton("+ Katman")
        self.d_kat_ekle.setToolTip("En üste yeni bir katman ekler.")
        self.d_kat_sil = QtWidgets.QPushButton("Sil")
        self.d_kat_sil.setToolTip("Seçili katmanı siler.")
        self.d_kat_yukari = QtWidgets.QPushButton("Yukarı taşı")
        self.d_kat_asagi = QtWidgets.QPushButton("Aşağı taşı")
        self.d_kat_yukari.setToolTip("Seçili katmanı bir üste taşır")
        self.d_kat_asagi.setToolTip("Seçili katmanı bir alta taşır")
        self.katman_ozet = QtWidgets.QLabel("-")
        self.katman_ozet.setWordWrap(True)

        # --- sinirlar ---
        self.bc_yan = QtWidgets.QComboBox()
        self.bc_alt = QtWidgets.QComboBox()
        self.bc_ust = QtWidgets.QComboBox()
        self.sinir_notu = ipucu("")
        self.sinir_notu.setVisible(False)

        # --- yansitici ---
        self.yans_var = QtWidgets.QCheckBox("Yansıtıcı kuşak ekle")
        self.yans_kal = sayi(20.0, 3, 0.01, 1000.0, 1.0, "cm")
        self.yans_mal = QtWidgets.QComboBox()

        # --- tamburlu kor ---
        self.tb_sayi = tamsayi(8, 0, 64, 1, "tambur")
        self.tb_r = sayi(4.0, 4, 0.01, 1000.0, 0.1, "cm")
        self.tb_rm = sayi(21.5, 4, 0.01, 10000.0, 0.5, "cm")
        self.tb_emici_ric = sayi(2.6, 4, 0.0, 1000.0, 0.1, "cm")
        self.tb_aci = sayi(120.0, 2, 1.0, 360.0, 5.0, "derece")
        self.tb_donme = sayi(0.0, 2, -360.0, 360.0, 5.0, "derece")
        self.tb_donme_kaydirici = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.tb_donme_kaydirici.setRange(0, 3600)
        self.tb_govde = QtWidgets.QComboBox()
        self.tb_emici = QtWidgets.QComboBox()
        self.tb_durum = QtWidgets.QLabel("-")
        self.tb_durum.setWordWrap(True)
        self._baslangic_acisi = 0.0     # arayuzde alani yok; dosyadan korunur

        self.ozet = QtWidgets.QLabel("-")

        # ================= yerlesim =================
        self.form = QtWidgets.QFormLayout()
        self.satir_cubuk = self._satir("Çubuk:", self.cubuk)
        self.satir_plaka = self._satir("Plaka elemanı:", self.plaka)
        self.satir_demet = self._satir("Demet:", self.demet)
        self.satir_tb_dolgu = self._satir("Kor dolgusu:", self.tb_dolgu)
        self.satir_tb_kor_r = self._satir("Kor yarıçapı:", self.tb_kor_r)
        self.satir_adim = self._satir("Hücre adımı:", self.adim)

        # kor haritasi
        # Kare ve altigen harita ayni kutuda; ture gore biri gorunur.
        self.kafes_kutu = QtWidgets.QGroupBox("Kor haritası")
        dis_kd = QtWidgets.QVBoxLayout(self.kafes_kutu)
        self.kare_harita = QtWidgets.QWidget()
        kd = QtWidgets.QVBoxLayout(self.kare_harita)
        kd.setContentsMargins(0, 0, 0, 0)
        dis_kd.addWidget(self.kare_harita, 1)
        dis_kd.addWidget(self.altigen_harita, 1)
        boyut = QtWidgets.QHBoxLayout()
        boyut.addWidget(QtWidgets.QLabel("Boyut:"))
        boyut.addWidget(self.nx)
        boyut.addWidget(QtWidgets.QLabel("×"))
        boyut.addWidget(self.ny)
        boyut.addStretch(1)
        boyut.addWidget(self.d_doldur)
        kd.addLayout(boyut)
        boya = QtWidgets.QHBoxLayout()
        boya.addWidget(self.palet, 0)
        boya.addWidget(self.izgara, 1)
        kd.addLayout(boya, 1)
        kd.addWidget(ipucu(
            "Paletten bir parça seçip ızgarada tıklayın ya da sürükleyin; sağ tık "
            "o hücredeki parçayı seçer. İlk satır haritanın en üstüdür (+y)."))

        # kontrol tamburlari
        self.tambur_kutu = QtWidgets.QGroupBox("Kontrol tamburları")
        tf = QtWidgets.QFormLayout(self.tambur_kutu)
        tf.addRow("Tambur sayısı:", self.tb_sayi)
        tf.addRow("Tambur yarıçapı:", self.tb_r)
        tf.addRow("Merkez yarıçapı:", self.tb_rm)
        tf.addRow("Gövde malzemesi:", self.tb_govde)
        tf.addRow("Emici malzemesi:", self.tb_emici)
        tf.addRow("Emici iç yarıçapı:", self.tb_emici_ric)
        tf.addRow("Emici yay açısı:", self.tb_aci)
        dn = QtWidgets.QWidget()
        dnl = QtWidgets.QHBoxLayout(dn)
        dnl.setContentsMargins(0, 0, 0, 0)
        dnl.addWidget(self.tb_donme)
        dnl.addWidget(self.tb_donme_kaydirici, 1)
        tf.addRow("Dönme:", dn)
        tf.addRow(ipucu(
            "Dönme 0° = emici kora bakar (daldırılmış, en düşük k); 180° = emici "
            "dışa bakar (çekilmiş, en yüksek k). Kritik tambur konumu için: "
            "Analiz sekmesi › Kritik arama › Kontrol tamburu dönmesi."))
        tf.addRow("Yerleşim:", self.tb_durum)

        # kuresel kabuklar
        self.kabuk_kutu = QtWidgets.QGroupBox("Küresel kabuklar (içten dışa)")
        kk = QtWidgets.QVBoxLayout(self.kabuk_kutu)
        kk.addWidget(self.kabuk_tablo)
        kk.addWidget(ipucu("Kabuk düzenleyici henüz yok; kabukları model dosyasında "
                           "düzenleyin. En dıştaki kabuk modelin sınır yüzeyidir."))

        # yukseklik ve sinirlar
        self.eksen_kutu = QtWidgets.QGroupBox("Yükseklik ve sınır koşulları")
        ed = QtWidgets.QFormLayout(self.eksen_kutu)
        self._eksen_form = ed
        self.yukseklik_etiket = QtWidgets.QLabel("Model:")
        ed.addRow(self.yukseklik_etiket, self.yukseklik_modu)
        self.h_etiket = QtWidgets.QLabel("Yükseklik:")
        ed.addRow(self.h_etiket, self.yukseklik)
        self.yan_etiket = QtWidgets.QLabel("Yan sınır:")
        ed.addRow(self.yan_etiket, self.bc_yan)
        self.alt_etiket = QtWidgets.QLabel("Alt sınır:")
        ed.addRow(self.alt_etiket, self.bc_alt)
        self.ust_etiket = QtWidgets.QLabel("Üst sınır:")
        ed.addRow(self.ust_etiket, self.bc_ust)
        ed.addRow(self.sinir_notu)

        # yansitici
        self.yans_kutu = QtWidgets.QGroupBox("Yansıtıcı kuşak")
        yd = QtWidgets.QFormLayout(self.yans_kutu)
        yd.addRow(self.yans_var)
        self.yans_kal_etiket = QtWidgets.QLabel("Kalınlık:")
        yd.addRow(self.yans_kal_etiket, self.yans_kal)
        self.yans_mal_etiket = QtWidgets.QLabel("Malzeme:")
        yd.addRow(self.yans_mal_etiket, self.yans_mal)
        self.yans_notu = ipucu("Tamburlu korda yansıtıcı kuşak zorunludur; "
                               "tamburlar bu kuşağın içine gömülür.")
        yd.addRow(self.yans_notu)

        # eksenel katmanlar
        self.katman_kutu = QtWidgets.QGroupBox("Eksenel katmanlar (en üstteki katman en üstte)")
        kl = QtWidgets.QVBoxLayout(self.katman_kutu)
        kl.addWidget(self.katman_tablo)
        kat_dugme = QtWidgets.QHBoxLayout()
        for d in (self.d_kat_ekle, self.d_kat_sil, self.d_kat_yukari, self.d_kat_asagi):
            kat_dugme.addWidget(d)
        kat_dugme.addStretch(1)
        kl.addLayout(kat_dugme)
        kl.addWidget(self.katman_ozet)
        kl.addWidget(ipucu(
            "Dolgusu “ana dolgu” olan katman korun kendi dolgusunu kullanır. "
            "Katmanlar arası yüzeyler geçirgendir; sınır koşulu yalnızca en alt ve "
            "en üst yüzeye uygulanır. Kontrol çubuğu daldırması ve doğrusal güç "
            "aktif yakıt aralığına göre ölçülür."))

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(baslik("Kor"))
        duzen.addWidget(self.tur_etiket)
        duzen.addLayout(self.form)
        duzen.addWidget(self.kafes_kutu, 1)
        duzen.addWidget(self.tambur_kutu)
        duzen.addWidget(self.kabuk_kutu)
        ikili = QtWidgets.QHBoxLayout()
        ikili.addWidget(self.eksen_kutu, 1)
        ikili.addWidget(self.yans_kutu, 1)
        duzen.addLayout(ikili)
        duzen.addWidget(self.katman_kutu)
        duzen.addWidget(self._ozet_satiri())
        duzen.addStretch(1)

        # ================= sinyaller =================
        for w in (self.cubuk, self.plaka, self.demet, self.bc_yan, self.bc_alt,
                  self.bc_ust, self.yans_mal, self.tb_dolgu, self.tb_govde,
                  self.tb_emici):
            w.currentIndexChanged.connect(self._kaydet)
        for w in (self.adim, self.yukseklik, self.yans_kal, self.tb_kor_r,
                  self.tb_r, self.tb_rm, self.tb_emici_ric, self.tb_aci):
            w.valueChanged.connect(self._kaydet)
        self.tb_sayi.valueChanged.connect(self._kaydet)
        self.yans_var.toggled.connect(self._yans_degisti)
        self.tb_donme.valueChanged.connect(self._donme_degisti)
        self.tb_donme_kaydirici.valueChanged.connect(self._donme_kaydirici)
        self.yukseklik_modu.currentIndexChanged.connect(self._yukseklik_modu_degisti)
        self.d_kat_ekle.clicked.connect(self._katman_ekle)
        self.d_kat_sil.clicked.connect(self._katman_sil)
        self.d_kat_yukari.clicked.connect(lambda: self._katman_tasi(-1))
        self.d_kat_asagi.clicked.connect(lambda: self._katman_tasi(+1))
        self.palet.secildi.connect(self.izgara.firca_ayarla)
        self.izgara.firca_istendi.connect(self.palet.sec)
        self.izgara.degisti.connect(self._harita_boyandi)
        self.nx.valueChanged.connect(self._boyut_degisti)
        self.ny.valueChanged.connect(self._boyut_degisti)
        self.d_doldur.clicked.connect(self._tumunu_doldur)
        self.altigen_harita.degisti.connect(self._altigen_boyandi)

    # ------------------------------------------------------------------
    def _satir(self, etiket, w):
        e = QtWidgets.QLabel(etiket)
        self.form.addRow(e, w)
        return (e, w)

    def _ozet_satiri(self):
        k = QtWidgets.QWidget()
        d = QtWidgets.QHBoxLayout(k)
        d.setContentsMargins(0, 6, 0, 0)
        d.addWidget(QtWidgets.QLabel("Toplam model ölçüsü:"))
        d.addWidget(self.ozet)
        d.addStretch(1)
        return k

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
        malzemeler = [(sema.BOSLUK, _BOS_ETIKET)] + \
                     [(m["ad"], self._malzeme_etiketi(m)) for m in self.spec["malzemeler"]]
        self._malzeme_secenekleri = malzemeler
        self._kutu_doldur(self.yans_mal, malzemeler, (kor.get("yansitici") or {}).get("malzeme"))

        hedefler = [(sema.BOSLUK, _BOS_ETIKET)]
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
                _BOS_ETIKET if m == sema.BOSLUK else m))
        self.kabuk_tablo.resizeColumnsToContents()
        _tablo_yuksekligi(self.kabuk_tablo, 6)

    # ------------------------------------------------------------------
    # kor haritasi
    # ------------------------------------------------------------------
    def _palet_ogeleri(self):
        """Kor haritasina konabilecek parcalar: kare kafesler, malzemeler, bosluk;
        ayrica haritada zaten gecen (or. dosyadan gelen bir cubuk) her ad."""
        kor = self.spec["kor"]
        kullanilan = {ad for satir in izgara.harita_adlara(kor.get("harita"), kor.get("anahtar"))
                      for ad in satir if ad}
        altigen = {d["ad"] for d in self.spec.get("demetler", []) if d.get("tur") == "altigen"}
        ogeler = []
        for oge in izgara.palet_ogeleri(self.spec, turler=("demet", "cubuk", "plaka",
                                                           "malzeme", "bosluk")):
            ad, tur = oge[0], oge[3]
            if ad in kullanilan or (tur == "kafes" and ad not in altigen) \
                    or tur in ("malzeme", "boşluk"):
                ogeler.append(oge)
        return ogeler

    def _harita_doldur(self):
        kor = self.spec["kor"]
        harita = kor.get("harita") or []
        if harita:
            adlar = izgara.harita_adlara(harita, kor.get("anahtar"))
        else:
            nx, ny = (list(kor.get("boyut") or [1, 1]) + [1, 1])[:2]
            adlar = [[None] * max(int(nx), 1) for _ in range(max(int(ny), 1))]
        onceki = self.palet.secili()
        self.palet.blockSignals(True)
        try:
            self.palet.parcalari_ayarla(self._palet_ogeleri(), secili=onceki)
        finally:
            self.palet.blockSignals(False)
        if onceki is None or self.palet.secili() != onceki:
            # Ilk yukleme: firca haritada en cok gecen kafes olsun.
            sayac = {}
            for satir in adlar:
                for ad in satir:
                    if ad:
                        sayac[ad] = sayac.get(ad, 0) + 1
            if sayac:
                self.palet.sec(max(sayac, key=sayac.get))
        self.izgara.firca_ayarla(self.palet.secili())
        self.izgara.yukle(adlar, self.palet.renkler())
        nx = max((len(s) for s in adlar), default=0)
        for kutu, deger in ((self.nx, nx), (self.ny, len(adlar))):
            eski = kutu.blockSignals(True)
            kutu.setValue(max(deger, 1))
            kutu.blockSignals(eski)

    def _harita_yaz(self, adlar):
        """Parca adlari izgarasini spec'e yazar (harfler otomatik, eskiler korunur)."""
        kor = self.spec["kor"]
        try:
            harita, anahtar = izgara.adlardan_harita(adlar, kor.get("anahtar"),
                                                     kor.get("harita"))
        except ValueError as hata:
            QtWidgets.QMessageBox.warning(self, "Harita yazılamadı", str(hata))
            return False
        kor["harita"] = harita
        kor["anahtar"] = anahtar
        kor["boyut"] = [max((len(s) for s in adlar), default=0), len(adlar)]
        return True

    def _harita_boyandi(self):
        if self._yukleniyor or self.spec is None:
            return
        if self._harita_yaz(self.izgara.adlar()):
            self._ozet_guncelle()
            self.bildir()

    def _altigen_boyandi(self):
        if self._yukleniyor or self.spec is None:
            return
        self._ozet_guncelle()
        self.bildir()

    def _boyut_degisti(self, *_):
        if self._yukleniyor or self.spec is None:
            return
        adlar = self.izgara.adlar()
        nx, ny = self.nx.value(), self.ny.value()
        eski_nx = max((len(s) for s in adlar), default=0)
        eski_ny = len(adlar)
        kaybolan = sum(1 for r, satir in enumerate(adlar) for c, ad in enumerate(satir)
                       if (r >= ny or c >= nx) and ad is not None)
        if kaybolan:
            if not self._onay_al(
                    "Kor haritası küçülüyor",
                    "Harita %d×%d'den %d×%d'ye küçülüyor: sağdaki/alttaki %d dolu hücre "
                    "silinecek (büyütmek onları geri getirmez).\n\nDevam edilsin mi?"
                    % (eski_nx, eski_ny, nx, ny, kaybolan)):
                for kutu, deger in ((self.nx, eski_nx), (self.ny, eski_ny)):
                    eski = kutu.blockSignals(True)
                    kutu.setValue(deger)
                    kutu.blockSignals(eski)
                return
        firca = self.palet.secili()
        yeni = [[(adlar[r][c] if r < len(adlar) and c < len(adlar[r]) else firca)
                 for c in range(nx)] for r in range(ny)]
        self.izgara.yukle(yeni, self.palet.renkler())
        self._harita_boyandi()

    def _tumunu_doldur(self):
        if self.palet.secili() is None:
            return
        self.izgara.firca_ayarla(self.palet.secili())
        self.izgara.tumunu_doldur(self.palet.secili())   # degisti -> _harita_boyandi

    # ------------------------------------------------------------------
    # eksenel katmanlar (tablo FIZIKSEL sirada: satir r <-> spec n-1-r)
    # ------------------------------------------------------------------
    def _katmanlar(self):
        return ((self.spec["kor"].get("eksenel") or {}).get("bolgeler") or [])

    def _spec_indeksi(self, satir):
        n = len(self._katmanlar())
        return n - 1 - satir if 0 <= satir < n else -1

    def _satir_indeksi(self, i):
        n = len(self._katmanlar())
        return n - 1 - i if 0 <= i < n else -1

    def _dolgu_secenekleri(self):
        """
        Bir katmani doldurabilecek adlar. Ilk oge None = korun ana dolgusu;
        etiketi sema.katman_adaylari'nin o katman icin donecegi adlardir.
        """
        kor = self.spec["kor"]
        tur = kor.get("tur")
        ana = sema.katman_adaylari(kor, {})
        if tur == "kare_kafes":
            ana_etiket = "Ana dolgu (kor haritası)"
        elif ana:
            ana_etiket = "Ana dolgu (%s)" % ", ".join(ana)
        else:
            ana_etiket = "Ana dolgu (seçilmedi)"
        izinli = uygunluk.katman_dolgu_turleri(self.spec)
        ogeler = [(None, ana_etiket), (sema.BOSLUK, _BOS_ETIKET)]
        ana_demet = sema.demet_bul(self.spec, kor.get("demet")) if kor.get("demet") else None
        if "demet" in izinli:
            for d in self.spec.get("demetler", []):
                # tek demette katman, ana demetle AYNI kafes tipinde olmali
                if tur == "tek_demet" and ana_demet is not None \
                        and d.get("tur", "kare") != ana_demet.get("tur", "kare"):
                    continue
                ogeler.append((d["ad"], "demet: %s" % d["ad"]))
        if "cubuk" in izinli:
            ogeler += [(c["ad"], "çubuk: %s" % c["ad"]) for c in self.spec.get("cubuklar", [])]
        if "plaka" in izinli:
            ogeler += [(p["ad"], "plaka: %s" % p["ad"]) for p in self.spec.get("plakalar", [])]
        if "malzeme" in izinli:
            ogeler += [(m["ad"], "malzeme: %s" % sema.malzeme_etiketi(m))
                       for m in self.spec["malzemeler"]]
        return ogeler

    def _katman_doldur(self):
        """spec -> tablo (en ust katman ilk satirda)."""
        katmanlar = self._katmanlar()
        secenekler = self._dolgu_secenekleri()
        n = len(katmanlar)
        self.katman_tablo.setRowCount(0)
        self.katman_tablo.setRowCount(n)
        z = sema.eksenel_katmanlar(dict(self.spec["kor"], eksenel={"var": True,
                                                                   "bolgeler": katmanlar}))
        z_adi = {id(b): (z0, z1) for z0, z1, b in (z or [])}
        for i, b in enumerate(katmanlar):
            satir = n - 1 - i
            ad = QtWidgets.QLineEdit(b.get("ad") or "")
            ad.editingFinished.connect(self._katman_kaydet)
            if id(b) in z_adi:
                ad.setToolTip("z = %g … %g cm" % z_adi[id(b)])
            self.katman_tablo.setCellWidget(satir, 0, ad)
            h = sayi(float(b.get("yukseklik") or 1.0), 3, 0.001, 10000.0, 1.0, "cm")
            h.valueChanged.connect(self._katman_kaydet)
            self.katman_tablo.setCellWidget(satir, 1, h)
            kutu = QtWidgets.QComboBox()
            for deger, etiket in secenekler:
                kutu.addItem(etiket, deger)
            if b.get("anahtar"):
                # Katmana ozel harf eslemesi arayuzde duzenlenmiyor; secim
                # kutusu bunu SESSIZCE SILMESIN diye ayri bir oge gosterilir.
                kutu.insertItem(0, "(katmana özel harita — dosyadan)", "__anahtar__")
                kutu.setCurrentIndex(0)
                kutu.setEnabled(False)
            else:
                j = kutu.findData(b.get("dolgu"))
                if j < 0:
                    # listede olmayan (ture uymayan / tanimsiz) dolgu korunur
                    kutu.addItem("%s (bu kor türünde uygun değil)" % b.get("dolgu"),
                                 b.get("dolgu"))
                    j = kutu.count() - 1
                kutu.setCurrentIndex(j)
            kutu.currentIndexChanged.connect(self._katman_kaydet)
            self.katman_tablo.setCellWidget(satir, 2, kutu)
        self.katman_tablo.resizeColumnsToContents()
        _tablo_yuksekligi(self.katman_tablo, 10)
        self._katman_ozet_guncelle()

    def _katman_kaydet(self, *_):
        """Tablo -> spec. Duzenlenmeyen alanlar (anahtar) KORUNUR."""
        if self._yukleniyor:
            return
        eski = self._katmanlar()
        n = self.katman_tablo.rowCount()
        yeni = []
        for i in range(n):                       # spec sirasi: alttan uste
            satir = n - 1 - i
            b = dict(eski[i]) if i < len(eski) else {}
            ad_w = self.katman_tablo.cellWidget(satir, 0)
            h_w = self.katman_tablo.cellWidget(satir, 1)
            d_w = self.katman_tablo.cellWidget(satir, 2)
            b["ad"] = ad_w.text().strip() or ("katman %d" % (i + 1))
            b["yukseklik"] = h_w.value()
            if not b.get("anahtar"):
                b["dolgu"] = d_w.currentData()
            yeni.append(b)
        eks = self.spec["kor"].setdefault("eksenel", {})
        eks["bolgeler"] = yeni
        self._katman_ozet_guncelle()
        self._ozet_guncelle()
        self.bildir()

    def _katman_ozet_guncelle(self):
        """Toplam / aktif / cubuk araliklarini canli gosterir."""
        kor = self.spec["kor"]
        if not (kor.get("eksenel") or {}).get("var"):
            self.katman_ozet.setText("")
            return
        toplam = sema.kor_yuksekligi(kor)
        if not toplam:
            self.katman_ozet.setText("Geçerli katman yok (her katmanın yüksekliği pozitif olmalı).")
            return
        satir = "Toplam yükseklik = %g cm" % toplam
        try:
            from cekirdek import kurucu
            ar = kurucu.aktif_eksenel_aralik(self.spec)
            if ar:
                satir += ("   ·   aktif yakıt = %g cm  (z = %g … %g)"
                          % (ar[1] - ar[0], ar[0], ar[1]))
            g = self.spec.get("guc_dagilimi") or {}
            if g.get("var") and g.get("cubuk"):
                cr = kurucu.cubuk_eksenel_aralik(self.spec, g["cubuk"])
                if cr and (cr[1] - cr[0]) != (ar[1] - ar[0] if ar else None):
                    satir += ("\n“%s” çubuğu = %g cm (z = %g … %g) — güç ağı bunu kullanır"
                              % (g["cubuk"], cr[1] - cr[0], cr[0], cr[1]))
        except Exception as hata:
            satir += "   ·   aralık hesaplanamadı: %s" % hata
        self.katman_ozet.setText(satir)

    def _katmanlari_yenile(self, secili_spec=None):
        self._yukleniyor = True
        try:
            self._katman_doldur()
        finally:
            self._yukleniyor = False
        if secili_spec is not None:
            satir = self._satir_indeksi(secili_spec)
            if satir >= 0:
                self.katman_tablo.setCurrentCell(satir, 0)
        self._gorunurluk()
        self._ozet_guncelle()

    def _katman_ekle(self):
        eks = self.spec["kor"].setdefault("eksenel", {})
        bolgeler = eks.setdefault("bolgeler", [])
        bolgeler.append(sema.eksenel_bolge("katman %d" % (len(bolgeler) + 1), 20.0, None))
        self._katmanlari_yenile(len(bolgeler) - 1)          # en ust = ilk satir
        self.bildir()

    def _katman_sil(self):
        i = self._spec_indeksi(self.katman_tablo.currentRow())
        katmanlar = self._katmanlar()
        if i < 0:
            return
        katmanlar.pop(i)
        self._katmanlari_yenile(min(i, len(katmanlar) - 1) if katmanlar else None)
        self.bildir()

    def _katman_tasi(self, yon):
        """yon: -1 = tabloda yukari (fiziksel olarak YUKARI), +1 = asagi."""
        i = self._spec_indeksi(self.katman_tablo.currentRow())
        katmanlar = self._katmanlar()
        hedef = i - yon                  # spec alttan uste: yukari = indeks + 1
        if i < 0 or hedef < 0 or hedef >= len(katmanlar):
            return
        katmanlar[i], katmanlar[hedef] = katmanlar[hedef], katmanlar[i]
        self._katmanlari_yenile(hedef)
        self.bildir()

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
        self.yans_kutu.layout().setRowVisible(self.yans_kal, acik)
        self.yans_kutu.layout().setRowVisible(self.yans_mal, acik)

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
        self.eksen_kutu.setTitle("Yükseklik ve sınır koşulları" if eksenli
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
            self.tb_durum.setStyleSheet("color: #b3261e; font-weight: bold;")
        else:
            n = int(t["sayi"])
            kiris = 2.0 * t["merkez_yaricap"] * math.sin(math.pi / n) if n > 1 else 0.0
            self.tb_durum.setText(
                "Geçerli — komşu tambur merkezleri arası %.3f cm (iki yarıçap %.3f cm)."
                % (kiris, 2 * t["yaricap"]))
            self.tb_durum.setStyleSheet("color: #1e7a44;")
