# -*- coding: utf-8 -*-
"""
 arayuz/ayar/yerlesim.py  --  YerlesimMixin: sekmenin yerlesimi

 arayuz/sekme_ayar.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import sekme_ayar; sekme_ayar.X` aynen calisir.
"""

from PySide6 import QtCore, QtWidgets
from arayuz.ortak import ayrac, baslik, ipucu, GelismisBolum


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
