# -*- coding: utf-8 -*-
"""
 arayuz/ayar/yerlesim.py  --  YerlesimMixin: sekmenin yerlesimi

 arayuz/sekme_ayar.py'den bolundu (davranis degismedi). Dalga 2 (Ajan 8):
 bolumler kart (bilesenler.Kart); her kart kendi islevinde kurulur. Eski yol
 `from arayuz import sekme_ayar; sekme_ayar.X` aynen calisir.
"""

from PySide6 import QtCore, QtWidgets

from arayuz import bilesenler as b
from arayuz.ortak import baslik, ipucu, GelismisBolum
from cekirdek.ceviri import _, pgettext
from arayuz.tasarim import tokenlar
from arayuz.yardim_baglanti import yardim_dugmesi

A = tokenlar.ARALIK


class YerlesimMixin(object):
    """Hesap ayarlari sekmesinin yerlesimi (widget'lar __init__'te kurulur)."""

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
        """Iki sutun kart (maket: hesap_*): solda hesap, kaynak ve Gelismis;
        sagda guc dagilimi ve tally'ler."""
        sol = self._sutun((self._hesap_karti(), self._kaynak_karti(),
                           self._gelismis_karti()))
        sag = self._sutun((self._guc_karti(), self._spektrum_karti(), self._yerel_k_karti(),
                           self._tally_karti()))
        bolucu = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        bolucu.addWidget(sol)
        bolucu.addWidget(sag)
        bolucu.setStretchFactor(0, 4)
        bolucu.setStretchFactor(1, 5)
        bolucu.setSizes([430, 520])
        bolucu.setChildrenCollapsible(False)
        bolucu.setHandleWidth(A["l"])
        # Kartlar arasi bosluk: tutamac sayfa zemininde gorunmez kalir.
        bolucu.setStyleSheet("QSplitter::handle { background: transparent; }")
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(bolucu)
        self._tayfi_tasi(self._gelismis_tayf_yeri)

    @staticmethod
    def _sutun(kartlar):
        """Kartlari alt alta dizen sutun widget'i (bos alan altta)."""
        w = QtWidgets.QWidget()
        d = QtWidgets.QVBoxLayout(w)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(A["l"])
        for kart in kartlar:
            d.addWidget(kart)
        d.addStretch(1)
        return w

    def _hesap_karti(self):
        hesap = QtWidgets.QFormLayout()
        self._hesap_form = hesap
        hesap.addRow(_("Hesap türü:"), self.mod)
        hesap.addRow(_("Hesap hassasiyeti:"), self.hassasiyet)
        hesap.addRow("", self.hassasiyet_ozet)
        hesap.addRow(_("Parçacık / çevrim:"), self.parcacik)
        hesap.addRow(_("Toplam çevrim:"), self.cevrim)
        hesap.addRow(_("Pasif çevrim:"), self.pasif)
        hesap.addRow(self.kinetik_var)
        kart = b.Kart(_("Hesap"))
        kart.eylem_ekle(yardim_dugmesi("hesap-ayarlari", kart))
        kart.govde.addLayout(hesap)
        return kart

    def _kaynak_karti(self):
        kaynak = QtWidgets.QFormLayout()
        self._kaynak_form = kaynak
        kaynak.addRow(_("Kaynak tipi:"), self.kaynak_tur)
        self.konum_satiri = self._uclu((("x", self.kx), ("y", self.ky), ("z", self.kz)))
        kaynak.addRow(_("Nokta konumu:"), self.konum_satiri)
        kaynak.addRow(_("Parçacık:"), self.kaynak_parcacik)
        kaynak.addRow(_("Kaynak şiddeti [1/s]:"), self.kaynak_kuvvet)
        self._tayf_kutusu_kur()
        self._kaynak_tayf_yeri = QtWidgets.QVBoxLayout()
        self._kaynak_tayf_yeri.setContentsMargins(0, 0, 0, 0)
        kart = b.Kart(pgettext("kaynak", "Kaynak"))
        self.kaynak_baslik = kart.baslik_etiketi
        kart.govde.addLayout(kaynak)
        kart.govde.addLayout(self._kaynak_tayf_yeri)
        return kart

    def _tayf_kutusu_kur(self):
        """Enerji tayfi + acisal dagilim: ozdegerde Gelismis'e, sabit kaynakta
        kaynak kartina tasinan tek bir kutu."""
        self.tayf_kutu = QtWidgets.QWidget()
        tf = QtWidgets.QFormLayout(self.tayf_kutu)
        tf.setContentsMargins(0, 0, 0, 0)
        self._tayf_form = tf
        tf.addRow(_("Enerji tayfı:"), self.tayf)
        tf.addRow("", self.tayf_yigin)
        tf.addRow("", self.tayf_ozet)
        tf.addRow(_("Açısal dağılım:"), self.aci_tur)
        self.yon_satiri = self._uclu((("u", self.ax), ("v", self.ay), ("w", self.az)))
        tf.addRow(_("Yön:"), self.yon_satiri)
        tf.addRow(_("Koni yarı açısı:"), self.koni_aci)

    def _gelismis_karti(self):
        self.gelismis = GelismisBolum("ayar_gelismis")
        gf = QtWidgets.QFormLayout()
        self._gelismis_form = gf
        gf.addRow(_("Rastgele tohum:"), self.tohum)
        gf.addRow(_("Sıcaklık yöntemi:"), self.sicaklik_yontemi)
        gf.addRow(self.entropi_var)
        self.entropi_satiri = self._uclu((("nx", self.entropi_nx), ("ny", self.entropi_ny),
                                          ("nz", self.entropi_nz)))
        ent = QtWidgets.QHBoxLayout()
        ent.addWidget(self.entropi_oto)
        ent.addWidget(self.entropi_satiri, 1)
        self.entropi_agi = self._sar(ent)
        gf.addRow(_("Entropi ağı:"), self.entropi_agi)
        gf.addRow(_("IFP nesil sayısı:"), self.kinetik_nesil)
        gf.addRow(_("Gecikmeli nötron grupları:"), self.kinetik_gruplar)
        self.gelismis.ekle(self._sar(gf))
        self.gelismis_tayf_baslik = baslik(_("Başlangıç kaynağının enerjisi ve yönü"))
        self.gelismis.ekle(self.gelismis_tayf_baslik)
        self.gelismis_tayf_not = ipucu(_(
            "Özdeğer hesabında bunlar yalnızca başlangıç tahminidir; pasif çevrimlerde "
            "gerçek fisyon tayfına döner ve k-eff'i etkilemez."))
        self.gelismis.ekle(self.gelismis_tayf_not)
        self._gelismis_tayf_yeri = QtWidgets.QVBoxLayout()
        self.gelismis.ekle(self._sar(self._gelismis_tayf_yeri))
        kart = b.Kart()
        kart.ekle(self.gelismis)
        return kart

    def _guc_karti(self):
        """Guc dagilimi karti (gorunurluk: guc_formu, self.guc_kutu)."""
        self.guc_kutu = b.Kart(_("Güç dağılımı"))
        guc_form = QtWidgets.QFormLayout()
        guc_form.addRow(self.guc_var)
        self._guc_form = guc_form
        for etiket, w, ad in ((_("Hedef çubuk:"), self.guc_cubuk, "cubuk"),
                              (_("Eksenel dilim:"), self.guc_dilim, "dilim"),
                              (_("Toplam güç:"), self.guc_toplam, "toplam")):
            e = QtWidgets.QLabel(etiket)
            self.guc_etiketler[ad] = e
            guc_form.addRow(e, w)
        self.guc_kutu.govde.addLayout(guc_form)
        self.guc_not.setMinimumWidth(1)
        self.guc_kutu.ekle(self.guc_not)
        self.guc_kutu.ekle(self.guc_uyari)
        self.guc_gelismis = GelismisBolum("ayar_guc_gelismis")
        ggf = QtWidgets.QFormLayout()
        for etiket, w, ad in ((_("Hedef bölge:"), self.guc_bolge, "bolge"),
                              (_("Skor:"), self.guc_skor, "skor")):
            e = QtWidgets.QLabel(etiket)
            self.guc_etiketler[ad] = e
            ggf.addRow(e, w)
        self.guc_gelismis.ekle(self._sar(ggf))
        self.guc_kutu.ekle(self.guc_gelismis)
        return self.guc_kutu

    def _spektrum_karti(self):
        """Y3: spektrum ve dort faktor karti (arayuz/ayar/spektrum_karti.py)."""
        from arayuz.ayar.spektrum_karti import SpektrumAyarKarti
        self.spektrum_karti = SpektrumAyarKarti()
        self.spektrum_karti.degisti.connect(self.bildir)
        return self.spektrum_karti

    def _yerel_k_karti(self):
        """K4: yerel k haritasi karti (arayuz/ayar/yerel_k_karti.py). Tally
        listesi degisir: liste tazelenir, sonra ana pencereye bildirilir."""
        from arayuz.ayar.yerel_k_karti import YerelKAyarKarti
        self.yerel_k_karti = YerelKAyarKarti()
        self.yerel_k_karti.degisti.connect(lambda: (self._tallyleri_doldur(), self.bildir()))
        return self.yerel_k_karti

    def _tally_formu(self):
        t_form = QtWidgets.QFormLayout()
        self._t_form = t_form
        self._mesh_alanlari_kur()           # v3 Y1 (arayuz/ayar/mesh_formu.py)
        t_form.addRow(_("Ad:"), self.t_ad)
        t_form.addRow(_("Ne ölçülsün:"), self.t_set)
        t_form.addRow("", self.t_set_ozet)
        t_form.addRow(_("Skorlar:"), self.t_skor)
        t_form.addRow(self.t_enerji_var)
        self._enerji_satiri_ekle(t_form)
        t_form.addRow(_("Grup sınırları [eV]:"), self.t_enerji)
        t_form.addRow(self.t_mesh_var)
        self.mesh_satiri = self._uclu((("nx", self.t_mesh_nx), ("ny", self.t_mesh_ny),
                                       ("nz", self.t_mesh_nz)))
        t_form.addRow(_("Ağ bölmeleri:"), self.mesh_satiri)
        self._mesh_satirlari_ekle(t_form)
        t_form.addRow(self.t_diger)
        self.tally_duzenleyici = self._sar(t_form)

    def _tally_karti(self):
        d_t_ekle = b.ikincil_dugme(_("+ Tally"))
        self.d_t_sil = b.duz_dugme(_("Sil"), "trash")
        d_t_ekle.clicked.connect(self._tally_ekle)
        self.d_t_sil.clicked.connect(self._tally_sil)
        t_dugme = QtWidgets.QHBoxLayout()
        t_dugme.addWidget(d_t_ekle)
        t_dugme.addWidget(self.d_t_sil)
        t_dugme.addStretch(1)
        self._tally_formu()
        tally_sol = QtWidgets.QVBoxLayout()
        tally_sol.addWidget(self.tally_liste, 1)
        tally_sol.addLayout(t_dugme)
        tally_sag = QtWidgets.QVBoxLayout()
        tally_sag.addWidget(self.tally_bos)
        tally_sag.addWidget(self.tally_duzenleyici)
        tally_sag.addStretch(1)
        tally_bolucu = QtWidgets.QHBoxLayout()
        tally_bolucu.setSpacing(A["l"])
        tally_bolucu.addLayout(tally_sol, 0)
        tally_bolucu.addLayout(tally_sag, 1)
        kart = b.Kart(_("Tally'ler"), _("Ölçülecek büyüklükler"))
        kart.govde.addLayout(tally_bolucu)
        return kart
