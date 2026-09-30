# -*- coding: utf-8 -*-
"""
arayuz/kor/yerlesim.py -- KorYerlesimMixin: Kor sekmesinin widget'lari ve
yerlesimi (arayuz/sekme_kor.py'den bolundu; davranis degismedi).

Bolumler bilesenler.Kart'tir (Dalga 2, Ajan 8: yalnizca gorunum). Kartlarin
ozellik adlari (kafes_kutu, tambur_kutu, kabuk_kutu, eksen_kutu, yans_kutu,
katman_kutu) ve form referanslari (_eksen_form, _yans_form) sekme ve testler
tarafindan kullanilir. Bu dosyaya YENI ozellik eklenmez (Dalga G bu sekmeyi
esnek geometri sekmesine donusturecek).
"""

from PySide6 import QtCore, QtWidgets

from arayuz import bilesenler as b
from arayuz import izgara
from arayuz.kor_altigen import AltigenKorHaritasi
from arayuz.ortak import ipucu, sayi, tamsayi
from arayuz.tasarim import tokenlar

A = tokenlar.ARALIK

# Yukseklik secimi: (veri, gorunen ad)
YUKSEKLIK_MODLARI = [
    ("2B", "2B (sonsuz yükseklik)"),
    ("3B", "3B, tek bölge"),
    ("katmanli", "3B, katmanlı (yansıtıcı / örtü / plenum)"),
]

_PALET_EN_COK_GENISLIK = 230
_IZGARA_EN_AZ_YUKSEKLIK = 260
_KATMAN_TABLOSU_EN_AZ = 150
_DONME_ADIMI = 3600          # kaydirici: 0.1 derece adim


def _form():
    f = QtWidgets.QFormLayout()
    f.setContentsMargins(0, 0, 0, 0)
    f.setSpacing(A["s"])
    return f


def _tablo(sutunlar):
    t = QtWidgets.QTableWidget(0, len(sutunlar))
    t.setHorizontalHeaderLabels(sutunlar)
    t.horizontalHeader().setStretchLastSection(True)
    t.verticalHeader().setVisible(False)
    return t


class KorYerlesimMixin(object):
    """Widget'lar (_alanlari_kur), kartlar (_yerlesimi_kur) ve sinyaller."""

    # ------------------------------------------------------------------
    # widget'lar
    # ------------------------------------------------------------------
    def _alanlari_kur(self):
        self._tur_alanlari_kur()
        self._harita_alanlari_kur()
        self._yukseklik_alanlari_kur()
        self._katman_alanlari_kur()
        self._sinir_ve_yansitici_kur()
        self._tambur_alanlari_kur()
        self.ozet = QtWidgets.QLabel("-")

    def _tur_alanlari_kur(self):
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
        # --- kuresel kabuklar (salt okunur) ---
        self.kabuk_tablo = _tablo(["Dış yarıçap [cm]", "Malzeme"])
        self.kabuk_tablo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

    def _harita_alanlari_kur(self):
        # --- kor haritasi (kare_kafes) ---
        self.palet = izgara.ParcaPaleti()
        self.palet.setMaximumWidth(_PALET_EN_COK_GENISLIK)
        self.izgara = izgara.KareIzgara()
        self.izgara.setMinimumHeight(_IZGARA_EN_AZ_YUKSEKLIK)
        self.izgara.etiketleri_goster(True)
        self.nx = tamsayi(3, 1, 100, 1, "sütun")
        self.ny = tamsayi(3, 1, 100, 1, "satır")
        self.nx.setToolTip("Haritanın sütun sayısı. Büyütünce yeni hücreler "
                           "paletteki seçili parçayla dolar.")
        self.ny.setToolTip("Haritanın satır sayısı. Büyütünce yeni hücreler "
                           "paletteki seçili parçayla dolar.")
        self.d_doldur = b.ikincil_dugme("Tümünü seçili parçayla doldur", "paintbrush")
        # --- kor haritasi (altigen_kafes; arayuz/kor_altigen.py) ---
        # onay testlerde degistirilen self._onay_al'dan CAGRI ANINDA okunur
        self.altigen_harita = AltigenKorHaritasi(lambda b_, m: self._onay_al(b_, m))

    def _yukseklik_alanlari_kur(self):
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

    def _katman_alanlari_kur(self):
        self.katman_tablo = _tablo(["Ad", "Yükseklik", "Dolgu"])
        self.katman_tablo.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.katman_tablo.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.katman_tablo.setMinimumHeight(_KATMAN_TABLOSU_EN_AZ)
        self.d_kat_ekle = b.ikincil_dugme("+ Katman", None, "En üste yeni bir katman ekler.")
        self.d_kat_sil = b.duz_dugme("Sil", "trash", "Seçili katmanı siler.")
        self.d_kat_yukari = b.duz_dugme("Yukarı taşı", "chevron-up",
                                        "Seçili katmanı bir üste taşır")
        self.d_kat_asagi = b.duz_dugme("Aşağı taşı", "chevron-down",
                                       "Seçili katmanı bir alta taşır")
        self.katman_ozet = QtWidgets.QLabel("-")
        self.katman_ozet.setWordWrap(True)

    def _sinir_ve_yansitici_kur(self):
        self.bc_yan = QtWidgets.QComboBox()
        self.bc_alt = QtWidgets.QComboBox()
        self.bc_ust = QtWidgets.QComboBox()
        self.sinir_notu = ipucu("")
        self.sinir_notu.setVisible(False)
        self.yans_var = QtWidgets.QCheckBox("Yansıtıcı kuşak ekle")
        self.yans_kal = sayi(20.0, 3, 0.01, 1000.0, 1.0, "cm")
        self.yans_mal = QtWidgets.QComboBox()

    def _tambur_alanlari_kur(self):
        self.tb_sayi = tamsayi(8, 0, 64, 1, "tambur")
        self.tb_r = sayi(4.0, 4, 0.01, 1000.0, 0.1, "cm")
        self.tb_rm = sayi(21.5, 4, 0.01, 10000.0, 0.5, "cm")
        self.tb_emici_ric = sayi(2.6, 4, 0.0, 1000.0, 0.1, "cm")
        self.tb_aci = sayi(120.0, 2, 1.0, 360.0, 5.0, "derece")
        self.tb_donme = sayi(0.0, 2, -360.0, 360.0, 5.0, "derece")
        self.tb_donme_kaydirici = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.tb_donme_kaydirici.setRange(0, _DONME_ADIMI)
        self.tb_govde = QtWidgets.QComboBox()
        self.tb_emici = QtWidgets.QComboBox()
        self.tb_durum = QtWidgets.QLabel("-")
        self.tb_durum.setWordWrap(True)
        self._baslangic_acisi = 0.0     # arayuzde alani yok; dosyadan korunur

    # ------------------------------------------------------------------
    # kartlar
    # ------------------------------------------------------------------
    def _yerlesimi_kur(self):
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setSpacing(A["l"])
        duzen.addWidget(self._tur_karti())
        duzen.addWidget(self._harita_karti(), 1)
        duzen.addWidget(self._tambur_karti())
        duzen.addWidget(self._kabuk_karti())
        ikili = QtWidgets.QHBoxLayout()
        ikili.setSpacing(A["l"])
        ikili.addWidget(self._eksen_karti(), 1)
        ikili.addWidget(self._yans_karti(), 1)
        duzen.addLayout(ikili)
        duzen.addWidget(self._katman_karti())
        duzen.addWidget(self._ozet_satiri())
        duzen.addStretch(1)

    def _satir(self, etiket, w):
        e = QtWidgets.QLabel(etiket)
        self.form.addRow(e, w)
        return (e, w)

    def _tur_karti(self):
        """Kor turu (degistirme baglantisi) ve ture ozgu tekil alanlar."""
        self.form = _form()
        self.satir_cubuk = self._satir("Çubuk:", self.cubuk)
        self.satir_plaka = self._satir("Plaka elemanı:", self.plaka)
        self.satir_demet = self._satir("Demet:", self.demet)
        self.satir_tb_dolgu = self._satir("Kor dolgusu:", self.tb_dolgu)
        self.satir_tb_kor_r = self._satir("Kor yarıçapı:", self.tb_kor_r)
        self.satir_adim = self._satir("Hücre adımı:", self.adim)
        kart = b.Kart("Kor")
        kart.ekle(self.tur_etiket)
        kart.govde.addLayout(self.form)
        return kart

    def _harita_karti(self):
        """Kare ve altigen harita ayni kartta; ture gore biri gorunur."""
        self.kafes_kutu = b.Kart("Kor haritası")
        self.kare_harita = QtWidgets.QWidget()
        kd = QtWidgets.QVBoxLayout(self.kare_harita)
        kd.setContentsMargins(0, 0, 0, 0)
        kd.setSpacing(A["s"])
        self.kafes_kutu.ekle(self.kare_harita, 1)
        self.kafes_kutu.ekle(self.altigen_harita, 1)
        boyut = QtWidgets.QHBoxLayout()
        boyut.setSpacing(A["s"])
        boyut.addWidget(QtWidgets.QLabel("Boyut:"))
        boyut.addWidget(self.nx)
        boyut.addWidget(QtWidgets.QLabel("×"))
        boyut.addWidget(self.ny)
        boyut.addStretch(1)
        boyut.addWidget(self.d_doldur)
        kd.addLayout(boyut)
        boya = QtWidgets.QHBoxLayout()
        boya.setSpacing(A["m"])
        boya.addWidget(self.palet, 0)
        boya.addWidget(self.izgara, 1)
        kd.addLayout(boya, 1)
        kd.addWidget(ipucu(
            "Paletten bir parça seçip ızgarada tıklayın ya da sürükleyin; sağ tık "
            "o hücredeki parçayı seçer. İlk satır haritanın en üstüdür (+y)."))
        return self.kafes_kutu

    def _tambur_karti(self):
        self.tambur_kutu = b.Kart("Kontrol tamburları")
        tf = _form()
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
        self.tambur_kutu.govde.addLayout(tf)
        return self.tambur_kutu

    def _kabuk_karti(self):
        self.kabuk_kutu = b.Kart("Küresel kabuklar (içten dışa)")
        self.kabuk_kutu.ekle(self.kabuk_tablo)
        self.kabuk_kutu.ekle(ipucu("Kabuk düzenleyici henüz yok; kabukları model "
                                   "dosyasında düzenleyin. En dıştaki kabuk modelin "
                                   "sınır yüzeyidir."))
        return self.kabuk_kutu

    def _eksen_karti(self):
        self.eksen_kutu = b.Kart("Yükseklik ve sınır koşulları")
        ed = _form()
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
        self.eksen_kutu.govde.addLayout(ed)
        return self.eksen_kutu

    def _yans_karti(self):
        self.yans_kutu = b.Kart("Yansıtıcı kuşak")
        yd = _form()
        self._yans_form = yd
        yd.addRow(self.yans_var)
        self.yans_kal_etiket = QtWidgets.QLabel("Kalınlık:")
        yd.addRow(self.yans_kal_etiket, self.yans_kal)
        self.yans_mal_etiket = QtWidgets.QLabel("Malzeme:")
        yd.addRow(self.yans_mal_etiket, self.yans_mal)
        self.yans_notu = ipucu("Tamburlu korda yansıtıcı kuşak zorunludur; "
                               "tamburlar bu kuşağın içine gömülür.")
        yd.addRow(self.yans_notu)
        self.yans_kutu.govde.addLayout(yd)
        return self.yans_kutu

    def _katman_karti(self):
        self.katman_kutu = b.Kart("Eksenel katmanlar",
                                  "En üstteki katman tabloda en üsttedir.")
        self.katman_kutu.ekle(self.katman_tablo)
        kat_dugme = QtWidgets.QHBoxLayout()
        kat_dugme.setSpacing(A["s"])
        for d in (self.d_kat_ekle, self.d_kat_sil, self.d_kat_yukari, self.d_kat_asagi):
            kat_dugme.addWidget(d)
        kat_dugme.addStretch(1)
        self.katman_kutu.govde.addLayout(kat_dugme)
        self.katman_kutu.ekle(self.katman_ozet)
        self.katman_kutu.ekle(ipucu(
            "Dolgusu “ana dolgu” olan katman korun kendi dolgusunu kullanır. "
            "Katmanlar arası yüzeyler geçirgendir; sınır koşulu yalnızca en alt ve "
            "en üst yüzeye uygulanır. Kontrol çubuğu daldırması ve doğrusal güç "
            "aktif yakıt aralığına göre ölçülür."))
        return self.katman_kutu

    def _ozet_satiri(self):
        k = QtWidgets.QWidget()
        d = QtWidgets.QHBoxLayout(k)
        d.setContentsMargins(0, A["s"], 0, 0)
        d.setSpacing(A["s"])
        e = QtWidgets.QLabel("Toplam model ölçüsü:")
        e.setObjectName("ikincil")
        d.addWidget(e)
        d.addWidget(self.ozet)
        d.addStretch(1)
        return k

    # ------------------------------------------------------------------
    # sinyaller
    # ------------------------------------------------------------------
    def _sinyalleri_bagla(self):
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
