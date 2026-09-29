# -*- coding: utf-8 -*-
"""
 arayuz/cubuk/sayfalar.py  --  SayfalarMixin: cubuk ve plaka sayfalari

 arayuz/sekme_cubuk.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import sekme_cubuk; sekme_cubuk.X` aynen calisir.
"""

from PySide6 import QtCore, QtWidgets
from cekirdek.ceviri import _
from arayuz import bilesenler as bl
from arayuz import sekme_duzen as sd
from arayuz.ortak import baslik, ipucu, sayi, tamsayi
from arayuz.cubuk.parca_islemleri import _renk
from arayuz.cubuk.malzeme_kutusu import _SatirTakibi


class SayfalarMixin(object):
    """Cubuk ve plaka duzenleme sayfalarinin yerlesimi."""

    # ------------------------------------------------------------------
    # sayfalar
    # ------------------------------------------------------------------
    def _hata_etiketi(self):
        e = QtWidgets.QLabel("")
        e.setWordWrap(True)
        e.setVisible(False)
        return e

    def _hata_goster(self, etiket, metin):
        etiket.setText(metin or "")
        etiket.setStyleSheet("color: %s;" % _renk("hata"))
        etiket.setVisible(bool(metin))

    def _cubuk_sayfa(self):
        w = QtWidgets.QWidget()
        self.c_ad = QtWidgets.QLineEdit()
        self.c_ad.editingFinished.connect(lambda: self._ad_degisti("cubuk"))
        self.c_ad_hata = self._hata_etiketi()

        # --- kontrol cubugu alanlari ---
        self.c_tur = QtWidgets.QComboBox()
        self.c_emici = QtWidgets.QComboBox()
        self.c_izleyici = QtWidgets.QComboBox()
        self.c_daldirma = sayi(0.0, 2, 0.0, 100.0, 5.0, "%")
        self.c_daldirma_kaydirici = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.c_daldirma_kaydirici.setRange(0, 1000)
        self.c_uc_etiket = QtWidgets.QLabel("-")
        self.c_kontrol_etiketleri = {}

        self.c_tablo = QtWidgets.QTableWidget(0, 3)
        self.c_tablo.setHorizontalHeaderLabels(["Dış yarıçap", "Malzeme", "Bölge"])
        bas = self.c_tablo.horizontalHeader()
        bas.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        bas.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        bas.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.c_tablo.verticalHeader().setVisible(False)
        self.c_tablo.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.c_tablo.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.c_tablo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.c_tablo.currentCellChanged.connect(lambda *_: self._bolge_dugmeleri())
        self._satir_takibi = _SatirTakibi(self.c_tablo)

        self.d_bolge_ekle = bl.ikincil_dugme(_("Bölge ekle"), "plus")
        self.d_bolge_sil = bl.duz_dugme(_("Bölge sil"), "trash")
        self.d_ice = bl.duz_dugme(_("İçe taşı"), "chevron-left")
        self.d_disa = bl.duz_dugme(_("Dışa taşı"), "chevron-right")
        self.d_bolge_ekle.setToolTip("Dış bölgenin hemen içine yeni bir bölge ekler.")
        self.d_ice.setToolTip("Seçili bölgenin malzemesini bir içteki bölgeyle değiştirir; "
                              "yarıçaplar yerinde kalır.")
        self.d_disa.setToolTip("Seçili bölgenin malzemesini bir dıştaki bölgeyle değiştirir; "
                               "yarıçaplar yerinde kalır. Dış bölgeye taşınmaz.")
        self.d_bolge_ekle.clicked.connect(self._bolge_ekle)
        self.d_bolge_sil.clicked.connect(self._bolge_sil)
        self.d_ice.clicked.connect(lambda: self._bolge_tasi(-1))
        self.d_disa.clicked.connect(lambda: self._bolge_tasi(+1))
        dugme = sd.satir(self.d_bolge_ekle, self.d_bolge_sil, self.d_ice, self.d_disa)

        form = sd.form()
        form.addRow("Ad:", self.c_ad)
        form.addRow("", self.c_ad_hata)
        self.e_tur = QtWidgets.QLabel("Tür:")
        form.addRow(self.e_tur, self.c_tur)
        for etiket, alan, anahtar in (
                ("Emici bölge:", self.c_emici, "emici"),
                ("İzleyici malzeme:", self.c_izleyici, "izleyici")):
            e = QtWidgets.QLabel(etiket)
            self.c_kontrol_etiketleri[anahtar] = e
            form.addRow(e, alan)
        self.c_emici.setToolTip("Eksenel olarak daldırılan (emici) bölge. Dış bölge seçilemez.")
        self.c_izleyici.setToolTip(
            "Emici bölgenin çubuk ucunun altında kalan kısmını dolduran malzeme "
            "(follower). Yakıt ve emici malzemeler listelenmez.")
        dald = QtWidgets.QWidget()
        dd = QtWidgets.QHBoxLayout(dald)
        dd.setContentsMargins(0, 0, 0, 0)
        dd.addWidget(self.c_daldirma)
        dd.addWidget(self.c_daldirma_kaydirici, 1)
        e = QtWidgets.QLabel("Daldırma:")
        self.c_kontrol_etiketleri["daldirma"] = e
        form.addRow(e, dald)
        e = QtWidgets.QLabel("Uç konumu:")
        self.c_kontrol_etiketleri["uc"] = e
        form.addRow(e, self.c_uc_etiket)

        self.c_kontrol_not = ipucu(
            "Kontrol çubuğu yukarıdan daldırılır: %0 tamamen çekilmiş, %100 tamamen "
            "dalmış. Emici bölgenin uç altında kalan kısmı izleyici malzemeyle dolar. "
            "Kritik çubuk konumunu bulmak için Analiz sekmesinde 'Kritik arama' ile "
            "'Kontrol çubuğu daldırma' parametresini kullanın.")
        self.c_eksik = self._hata_etiketi()
        self.c_sira_uyari = self._hata_etiketi()

        self.c_karti = bl.Kart(_("Çubuk"))
        self.c_baslik = self.c_karti.baslik_etiketi
        self.c_karti.govde.addLayout(form)
        self.c_karti.ekle(self.c_kontrol_not)
        self.c_bolge_karti = bl.Kart(_("Radyal bölgeler"), aciklama=_(
            "Bölgeler içten dışa sıralanır; her satırın yarıçapı o bölgenin dış "
            "sınırıdır ve bir öncekinden büyük olmalıdır. Son satır dış bölgedir: "
            "çubuğun çevresini hücrenin kenarına kadar doldurur (çoğunlukla soğutucu)."))
        self.c_bolge_karti.ekle(self.c_tablo, 1)
        self.c_bolge_karti.ekle(self.c_sira_uyari)
        self.c_bolge_karti.ekle(self.c_eksik)
        self.c_bolge_karti.ekle(dugme)

        d = sd.sayfa_duzeni(w, dolgu=False)
        d.addWidget(self.c_karti)
        d.addWidget(self.c_bolge_karti, 1)

        self.c_tur.currentIndexChanged.connect(self._cubuk_tur_degisti)
        self.c_emici.currentIndexChanged.connect(self._cubuk_kaydet)
        self.c_izleyici.currentIndexChanged.connect(self._cubuk_kaydet)
        self.c_daldirma.valueChanged.connect(self._daldirma_degisti)
        self.c_daldirma_kaydirici.valueChanged.connect(self._kaydirici_degisti)
        return w

    def _plaka_sayfa(self):
        w = QtWidgets.QWidget()
        self.p_ad = QtWidgets.QLineEdit()
        self.p_ad.editingFinished.connect(lambda: self._ad_degisti("plaka"))
        self.p_ad_hata = self._hata_etiketi()
        self.p_sayi = tamsayi(23, 1, 500, 1, "plaka")
        self.p_et = sayi(0.051, 5, 0.0001, 10.0, 0.001, "cm")
        self.p_zarf = sayi(0.038, 5, 0.0001, 10.0, 0.001, "cm")
        self.p_kanal = sayi(0.200, 5, 0.0001, 10.0, 0.001, "cm")
        self.p_genislik = sayi(6.30, 4, 0.01, 100.0, 0.1, "cm")
        self.p_yan = sayi(0.475, 4, 0.0, 10.0, 0.01, "cm")
        self.p_ozet = QtWidgets.QLabel("-")
        self.p_eksik = self._hata_etiketi()
        # Malzeme kutulari her yuklemede yeniden kurulur (role gore suzulu).
        self.p_et_mal = self.p_zarf_mal = self.p_sog = self.p_yan_mal = None

        self.p_form = sd.form()
        f = self.p_form
        f.addRow("Ad:", self.p_ad)
        f.addRow("", self.p_ad_hata)
        f.addRow("Plaka sayısı:", self.p_sayi)
        f.addRow("Yakıt tabakası kalınlığı:", self.p_et)
        f.addRow("Zarf kalınlığı (her yüz):", self.p_zarf)
        f.addRow("Soğutucu kanal aralığı:", self.p_kanal)
        f.addRow("Aktif genişlik (y):", self.p_genislik)
        self._p_satir = {}
        for anahtar, etiket in (("et_malzeme", "Yakıt malzemesi:"),
                                ("zarf_malzeme", "Zarf malzemesi:"),
                                ("sogutucu", "Soğutucu:")):
            yer = QtWidgets.QWidget()
            yd = QtWidgets.QHBoxLayout(yer)
            yd.setContentsMargins(0, 0, 0, 0)
            self._p_satir[anahtar] = yd
            f.addRow(etiket, yer)
        f.addRow("Yan levha kalınlığı:", self.p_yan)
        yer = QtWidgets.QWidget()
        yd = QtWidgets.QHBoxLayout(yer)
        yd.setContentsMargins(0, 0, 0, 0)
        self._p_satir["yan_levha_malzeme"] = yd
        self.e_yan_mal = QtWidgets.QLabel("Yan levha malzemesi:")
        f.addRow(self.e_yan_mal, yer)
        f.addRow("Eleman dış ölçüsü (x × y):", self.p_ozet)

        for alan in (self.p_sayi, self.p_et, self.p_zarf, self.p_kanal,
                     self.p_genislik, self.p_yan):
            alan.valueChanged.connect(self._plaka_kaydet)

        self.p_karti = bl.Kart(_("MTR tipi plaka yakıt elemanı"), aciklama=_(
            "Kesit x yönünde sırayla kurulur: kanal [zarf | yakıt | zarf] kanal "
            "[zarf | yakıt | zarf] … ve sonda bir kanal daha. Yan levhalar y "
            "yönünde aktif bölgenin altında ve üstünde yer alır."))
        self.p_karti.govde.addLayout(f)
        self.p_karti.ekle(self.p_eksik)

        d = sd.sayfa_duzeni(w, dolgu=False)
        d.addWidget(self.p_karti)
        d.addStretch(1)
        return w
