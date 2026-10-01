# -*- coding: utf-8 -*-
"""
 arayuz/demet/yerlesim.py  --  YerlesimMixin: Demet sekmesinin kart duzeni

 arayuz/sekme_demet.py'den bolundu. Duzen maketle ayni (maketler/demet_*.png):
   sol  : "Izgara" karti -- harita + altinda olcu ozeti
   sag  : "Demetler" (liste + ekleme), "Demet" (ozellikler), "Parca paleti"
          (firca + doldurma eylemleri), "Gelismis" kutusu; sabit genislikte sutun.
 Renk/aralik yalnizca tasarim tokenlarindan; sekme QTabWidget'a bagli degil
 (kabuk her sayfayi QScrollArea icine koyar).
"""

from PySide6 import QtCore, QtWidgets

from cekirdek.ceviri import _
from arayuz import bilesenler as bl
from arayuz import izgara
from arayuz import sekme_duzen as sd
from arayuz.demet.demet_islemleri import tur_adi
from arayuz.ortak import BosDurum, GelismisBolum, ipucu, sayi, tamsayi
from arayuz.tasarim import tokenlar

A = tokenlar.ARALIK
SAG_SUTUN_GENISLIK = 330
EN_AZ_HARITA = 240
PALET_EN_COK = 8          # palet listesinin kaydirmadan gosterdigi satir (yaklasik)


class YerlesimMixin(object):
    """Demet sekmesinin widget'larini kurar (davranis DemetSekmesi'nde)."""

    def _yerlesim_kur(self):
        duzen = sd.sayfa_duzeni(self)
        duzen.addWidget(sd.sayfa_basligi(
            _("Demet"), _("Parçaları ızgaraya yerleştirin."), bolum="demet"))
        govde = QtWidgets.QHBoxLayout()
        govde.setSpacing(A["l"])
        govde.addWidget(self._izgara_karti(), 1)
        govde.addWidget(self._sag_sutun())
        duzen.addLayout(govde, 1)

    # ------------------------------------------------------------------
    def _izgara_karti(self):
        """Sol kart: bos durum / kare / altigen harita + doldurma satiri."""
        self.bos = BosDurum(_("Henüz demet yok"), "", _("+ Kare demet"))
        self.bos.eylem.connect(lambda: self._yeni(self._bos_tipi))
        self._bos_tipi = "kare"
        self.kare_izgara = izgara.KareIzgara()
        self.hex_izgara = izgara.AltigenIzgara()
        for iz in (self.kare_izgara, self.hex_izgara):
            iz.etiketleri_goster(True)
            iz.degisti.connect(self._harita_kaydet)
            iz.firca_istendi.connect(self._firca_istendi)
        self.harita_yigin = QtWidgets.QStackedWidget()
        self.harita_yigin.addWidget(self.bos)            # 0
        self.harita_yigin.addWidget(self.kare_izgara)    # 1
        self.harita_yigin.addWidget(self.hex_izgara)     # 2
        self.harita_yigin.setMinimumSize(EN_AZ_HARITA, EN_AZ_HARITA)

        # Olcu ozeti haritanin altinda tek basina: dar ekranda (1280) dugmeyle
        # ayni satirda kartin genisligini zorluyordu.
        self.ozet = QtWidgets.QLabel("-")
        self.ozet.setObjectName("monoSoluk")
        self.ozet.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        # Genis ekranda tek satir (haritadan yer calmaz), darda sarilir.
        self.ozet.setWordWrap(True)

        self.izgara_karti = bl.Kart(
            _("Izgara"), aciklama=_("Tıklayın ya da sürükleyin · sağ tık: parçayı seç"))
        self.izgara_karti.ekle(self.harita_yigin, 1)
        self.izgara_karti.ekle(self.ozet)
        return self.izgara_karti

    # ------------------------------------------------------------------
    def _sag_sutun(self):
        # _bosluk bos durumda sutunu yukari iter (kartlar gizliyken).
        self._bosluk = QtWidgets.QWidget()
        sag = sd.sutun(self._liste_karti(), self._ozellik_karti(), self._palet_karti(),
                       self._gelismis_kutusu(), self._bosluk,
                       genislik=SAG_SUTUN_GENISLIK, esnek=False)
        sag.layout().setStretchFactor(self._bosluk, 1)
        self._sag = sag
        return sag

    def _liste_karti(self):
        self.liste = QtWidgets.QListWidget()
        self.liste.setIconSize(QtCore.QSize(14, 14))
        self.liste.setAlternatingRowColors(True)
        self.liste.currentRowChanged.connect(self._secim_degisti)
        self.d_kare = bl.ikincil_dugme(_("Kare demet"), "grid-3x3")
        self.d_hex = bl.ikincil_dugme(_("Altıgen demet"), "hexagon")
        self.d_kopya = bl.duz_dugme(_("Kopyala"), "copy", _("Seçili demetin kopyasını ekler."))
        self.d_sil = bl.tehlikeli_dugme(_("Sil"), "trash", _(
            "Seçili demeti siler (kullanılıyorsa önce sorar)."))
        self.d_kare.clicked.connect(lambda: self._yeni("kare"))
        self.d_hex.clicked.connect(lambda: self._yeni("altigen"))
        self.d_kopya.clicked.connect(self._kopyala)
        self.d_sil.clicked.connect(self._sil)
        kart = bl.Kart(_("Demetler"))
        kart.ekle(self.liste)
        kart.ekle(sd.satir(self.d_kare, self.d_hex))
        kart.ekle(sd.satir(self.d_kopya, self.d_sil))
        return kart

    def _palet_karti(self):
        self.palet = izgara.ParcaPaleti()
        self.palet.secildi.connect(self._firca_degisti)
        self.palet.liste.setMinimumHeight(66)
        self.palet.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                 QtWidgets.QSizePolicy.Maximum)
        self.palet_notu = ipucu("")
        self.palet_notu.setVisible(False)
        # Halka doldurma altigen demete ozgudur: firca secimiyle ayni kartta.
        self.halka_secim = QtWidgets.QComboBox()
        self.halka_secim.setToolTip(_("Doldurulacak halka (merkezden dışa numaralı)"))
        self.halka_secim.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.halka_secim.setMinimumContentsLength(10)
        self.d_halka_doldur = bl.duz_dugme(_("Halkayı doldur"), "hexagon")
        self.d_halka_doldur.clicked.connect(self._halka_doldur)
        self.palet_kutu = bl.Kart(_("Parça paleti"))
        self.palet_kutu.ekle(self.palet)
        self.palet_kutu.ekle(self.palet_notu)
        # Doldurma eylemleri secili parcayla (firca) calisir: paletle ayni kartta.
        self.d_hepsi = bl.duz_dugme(_("Tümünü doldur"), "grid-3x3", _(
            "Bütün hücreleri seçili parçayla doldurur (Ctrl+Z geri alır)."))
        self.d_hepsi.clicked.connect(self._tumunu_doldur)
        # Altigende halka secimi dugmelerin ustunde; iki doldurma dugmesi tek
        # satirda (halka denetimleri kare demette gizlenir, bosluk kalmaz).
        self.palet_kutu.ekle(self.halka_secim)
        self.palet_kutu.ekle(sd.satir(self.d_hepsi, self.d_halka_doldur))
        return self.palet_kutu

    def _palet_boyu(self):
        """Palet listesi icerigi kadar uzar (bos alan birakmaz, sag sutun
        ekrana sigar); PALET_EN_COK satirdan fazlasi kaydirilir."""
        liste = self.palet.liste
        n = min(max(liste.count(), 1), PALET_EN_COK)
        satir = liste.sizeHintForRow(0) if liste.count() else liste.fontMetrics().height()
        boy = n * (satir + 2 * liste.spacing()) + 2 * liste.frameWidth()
        liste.setFixedHeight(max(boy, liste.minimumSizeHint().height()))

    # ------------------------------------------------------------------
    def _ozellik_karti(self):
        """Secili demetin ozellikleri: ad, adim (SayiBirim), boyut, dis dolgu."""
        self.ad = QtWidgets.QLineEdit()
        self.ad.editingFinished.connect(self._ad_degisti)
        self.ad_hata = QtWidgets.QLabel("")
        self.ad_hata.setWordWrap(True)
        self.ad_hata.setVisible(False)
        self.adim_birim = bl.SayiBirim(birim="cm", deger=1.26, en_az=0.0001, en_cok=1000.0,
                                       ondalik=5, adim=0.01, erisilebilir_ad=_("Adım"))
        self.adim = self.adim_birim.kutu
        self.adim.setKeyboardTracking(False)
        self.nx = tamsayi(17, 1, 200)
        self.ny = tamsayi(17, 1, 200)
        self.halka = tamsayi(7, 1, 40, 1, _("halka"))
        # Yazarken ara degerler islenmesin: "17" secip "15" yazmak once nx=1
        # yapip haritayi TEK SUTUNA kirpiyordu. Deger Enter/odak kaybinda ya da
        # ok tuslariyla islenir.
        for w in (self.nx, self.ny, self.halka):
            w.setKeyboardTracking(False)
        self.dis = None                                  # her yuklemede kurulur

        self.ozellik = bl.Kart(tur_adi("kare"))
        self.oz_baslik = self.ozellik.baslik_etiketi
        self.form = sd.form()
        self.form.addRow(_("Ad"), self.ad)
        self.form.addRow(self.ad_hata)
        self.adim.setToolTip(_("Komşu hücre merkezleri arası uzaklık (pitch)."))
        self.form.addRow(_("Adım"), self.adim_birim)
        self._boyut_satiri()
        self.e_halka = QtWidgets.QLabel(_("Halka sayısı"))
        self.halka.setToolTip(_("Merkez dahil halka sayısı; k. halkada 6k hücre vardır."))
        self.form.addRow(self.e_halka, self.halka)
        self._dis_satiri()
        self.ozellik.govde.addLayout(self.form)
        return self.ozellik

    def _boyut_satiri(self):
        self.nx.setMinimumWidth(11 * A["s"])
        self.ny.setMinimumWidth(11 * A["s"])
        self.nx.setToolTip(_("Sütun sayısı (x)"))
        self.ny.setToolTip(_("Satır sayısı (y)"))
        kare_boyut = sd.satir(self.nx, QtWidgets.QLabel("×"), self.ny,
                              QtWidgets.QLabel(_("hücre")))
        self.e_kare_boyut = QtWidgets.QLabel(_("Boyut"))
        self.w_kare_boyut = kare_boyut
        self.form.addRow(self.e_kare_boyut, self.w_kare_boyut)

    def _dis_satiri(self):
        self._dis_yer = QtWidgets.QWidget()
        dy = QtWidgets.QHBoxLayout(self._dis_yer)
        dy.setContentsMargins(0, 0, 0, 0)
        self._dis_duzen = dy
        self.e_dis = QtWidgets.QLabel(_("Demet dışı"))
        self.e_dis.setToolTip(_("Demet hücrelerinin dışında kalan alanı dolduran malzeme."))
        self.form.addRow(self.e_dis, self._dis_yer)

    def _gelismis_kutusu(self):
        self.gelismis = GelismisBolum("demet_gelismis")
        gf = sd.form()
        self.yonelim = QtWidgets.QComboBox()
        self.yonelim.addItem(_("Üst/alt yüzler yatay (tepede hücre)"), "y")
        self.yonelim.addItem(_("Sağ/sol yüzler düşey (sağda hücre)"), "x")
        self.e_yonelim = QtWidgets.QLabel(_("Yönelim"))
        gf.addRow(self.e_yonelim, self.yonelim)
        self.tum_malzemeler = QtWidgets.QCheckBox(_("Palette bütün malzemeler ve Boş hücre"))
        self.tum_malzemeler.setToolTip(_(
            "Varsayılan palet yalnızca çubukları, iç demetleri ve soğutucu/moderatör "
            "hücrelerini gösterir."))
        self.tum_malzemeler.toggled.connect(lambda _a: self._palet_yenile())
        gf.addRow(self.tum_malzemeler)
        gw = QtWidgets.QWidget()
        gw.setLayout(gf)
        self.gelismis.ekle(gw)
        return self.gelismis
