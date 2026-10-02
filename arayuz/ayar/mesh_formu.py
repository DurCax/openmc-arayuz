# -*- coding: utf-8 -*-
"""
 arayuz/ayar/mesh_formu.py  --  MeshFormuMixin: tally formunun ag (mesh) ve
                                enerji grup yapisi alanlari (v3 Y1)

 TallyFormuMixin bundan turer; widget'lar yerlesim._tally_formu icinde
 (_mesh_alanlari_kur) kurulur, sekme_ayar.py'ye dokunulmaz. Spec bicimi ve
 sinir onerisi cekirdek/mesh_tally/tanim.py'dedir (tek kaynak).

   Ag turu          duzenli / silindirik / kuresel (altigen: OpenMC'de yok)
   Sinirlari modelden al   acik -> "otomatik" (kurulurken sinir kutusundan);
                    kapatinca o anki oneri acik sinir olarak yazilir
   Grup yapisi      Elle | CASMO-2/4/8/16/25/40/70 | XMAS-172 | SHEM-361
"""

from PySide6 import QtWidgets

from cekirdek import mesh_tally as mt
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from arayuz.ortak import ipucu, sayi

_log = kaydedici(__name__)

_SINIR_ARALIGI = 1.0e5        # cm; spin kutusu araligi (+/-1 km: her model sigar)
_ONDALIK = 4


class MeshFormuMixin(object):
    """Tally formunun ag turu, sinir ve grup yapisi alanlari."""

    # ------------------------------------------------------------------
    # kurulum
    # ------------------------------------------------------------------
    def _mesh_alanlari_kur(self):
        """Widget'lari kurar ve sinyalleri baglar (yerlesim._tally_formu cagirir)."""
        self.t_mesh_var.setText(_("Ağ (mesh) tally'si"))
        self.t_mesh_var.setToolTip(_("Değerleri bir ağın hücrelerine böler: 2B harita "
                                     "ve ParaView için VTK."))
        self.t_mesh_tur = QtWidgets.QComboBox()
        for tur in mt.MESH_TURLERI:
            self.t_mesh_tur.addItem(_(mt.MESH_TUR_ADLARI[tur]), tur)
        self.t_mesh_tur.setToolTip(_(mt.HEKSAGONAL_NOTU))
        self.t_mesh_oto = QtWidgets.QCheckBox(_("Sınırları modelden al"))
        self.t_mesh_oto.setChecked(True)
        self.t_mesh_oto.setToolTip(_("Sınırlar model kurulurken modelin dış ölçüsünden "
                                     "türetilir; yansıtıcı eklenirse ağ da büyür."))
        self.t_mesh_alt = [self._sinir_kutusu() for _i in range(3)]
        self.t_mesh_ust = [self._sinir_kutusu() for _i in range(3)]
        self.t_mesh_r = sayi(1.0, _ONDALIK, 1.0e-4, _SINIR_ARALIGI, 0.1, "cm")
        self.t_mesh_z_alt = self._sinir_kutusu()
        self.t_mesh_z_ust = self._sinir_kutusu()
        self.t_mesh_oneri = ipucu("")
        self.t_enerji_yapi = QtWidgets.QComboBox()
        self.t_enerji_yapi.addItem(_("Elle"), None)
        for ad in mt.GRUP_YAPILARI:
            self.t_enerji_yapi.addItem(ad, ad)
        self.t_enerji_yapi.setToolTip(_("Hazır grup yapıları OpenMC'den "
                                        "(openmc.mgxs.GROUP_STRUCTURES) alınır."))
        self.t_mesh_tur.currentIndexChanged.connect(self._mesh_turu_degisti)
        self.t_mesh_oto.toggled.connect(self._mesh_oto_degisti)
        for w in self.t_mesh_alt + self.t_mesh_ust + [self.t_mesh_r, self.t_mesh_z_alt,
                                                       self.t_mesh_z_ust]:
            w.valueChanged.connect(self._tally_kaydet)
        self.t_enerji_yapi.currentIndexChanged.connect(self._enerji_yapisi_secildi)

    @staticmethod
    def _sinir_kutusu():
        return sayi(0.0, _ONDALIK, -_SINIR_ARALIGI, _SINIR_ARALIGI, 0.1, "cm")

    def _mesh_satirlari_ekle(self, t_form):
        """Ag satirlari (Ag bolmeleri satirindan sonra)."""
        t_form.addRow(_("Ağ türü:"), self.t_mesh_tur)
        t_form.addRow(self.t_mesh_oto)
        self.t_mesh_alt_satiri = self._uclu(tuple(zip(("x", "y", "z"), self.t_mesh_alt)))
        self.t_mesh_ust_satiri = self._uclu(tuple(zip(("x", "y", "z"), self.t_mesh_ust)))
        self.t_mesh_z_satiri = self._uclu(((_("alt"), self.t_mesh_z_alt),
                                           (_("üst"), self.t_mesh_z_ust)))
        t_form.addRow(_("Alt sınır:"), self.t_mesh_alt_satiri)
        t_form.addRow(_("Üst sınır:"), self.t_mesh_ust_satiri)
        t_form.addRow(_("Dış yarıçap:"), self.t_mesh_r)
        t_form.addRow(_("z aralığı:"), self.t_mesh_z_satiri)
        t_form.addRow("", self.t_mesh_oneri)

    def _enerji_satiri_ekle(self, t_form):
        t_form.addRow(_("Grup yapısı:"), self.t_enerji_yapi)

    # ------------------------------------------------------------------
    # yardimcilar
    # ------------------------------------------------------------------
    def _mesh_sinir_kutusu(self):
        """Modelin sinir kutusu; kurulamazsa None (loglanir, oneri gosterilmez)."""
        try:
            return mt.model_sinir_kutusu(self.spec)
        except (ValueError, KeyError, TypeError) as e:
            _log.info("ağ önerisi için sınır kutusu alınamadı: %s", e)
            return None

    def _mesh_onerisi(self, tur):
        kutu = self._mesh_sinir_kutusu()
        return None if kutu is None else mt.sinir_onerisi(self.spec, kutu, tur)

    @staticmethod
    def _deger_yaz(w, deger):
        eski = w.blockSignals(True)
        try:
            w.setValue(float(deger))
        finally:
            w.blockSignals(eski)

    def _sinirlari_goster(self, tur, sinir):
        """Acik sinir sozlugunu ({alt, ust} | {r_ust, z_alt, z_ust}) alanlara yazar."""
        if not sinir:
            return
        if tur == mt.DUZENLI and sinir.get("alt") and sinir.get("ust"):
            for w, d in zip(self.t_mesh_alt + self.t_mesh_ust,
                            list(sinir["alt"]) + list(sinir["ust"])):
                self._deger_yaz(w, d)
            return
        for w, k in ((self.t_mesh_r, "r_ust"), (self.t_mesh_z_alt, "z_alt"),
                     (self.t_mesh_z_ust, "z_ust")):
            if sinir.get(k) is not None:
                self._deger_yaz(w, sinir[k])

    def _oneri_metni(self, tur, oneri):
        if oneri is None:
            return _("Öneri yok: modelin dış ölçüsü okunamadı.")
        if tur == mt.DUZENLI:
            return _("Öneri (modelin sınır kutusu): x, y, z alt {a} · üst {u} cm").format(
                a=", ".join("%.4g" % x for x in oneri["alt"]),
                u=", ".join("%.4g" % x for x in oneri["ust"]))
        metin = _("Öneri: r = {r:.4g} cm (modelin dış ölçüsünün yarısı)").format(
            r=oneri["r_ust"])
        if tur == mt.SILINDIRIK:
            metin += _(", z = {a:.4g} … {u:.4g} cm").format(a=oneri["z_alt"], u=oneri["z_ust"])
        return metin

    # ------------------------------------------------------------------
    # tally formuyla baglanti
    # ------------------------------------------------------------------
    def _mesh_formu_yukle(self, mesh):
        """Secili tally'nin ag filtresini alanlara yukler (sinyaller susturulur)."""
        if mesh is None:
            return
        try:
            tur = mt.mesh_turu(mesh)
        except ValueError:
            _log.warning("tanınmayan ağ türü: %r", mesh.get("mesh_turu"))
            tur = mt.DUZENLI
        self.t_mesh_tur.blockSignals(True)
        self.t_mesh_oto.blockSignals(True)
        try:
            self.t_mesh_tur.setCurrentIndex(max(self.t_mesh_tur.findData(tur), 0))
            acik = (mesh.get("alt") and mesh.get("ust")) or mesh.get("r_ust") is not None
            self.t_mesh_oto.setChecked(bool(mesh.get("otomatik")) or not acik)
        finally:
            self.t_mesh_tur.blockSignals(False)
            self.t_mesh_oto.blockSignals(False)
        self._sinirlari_goster(tur, mesh if not self.t_mesh_oto.isChecked()
                               else self._mesh_onerisi(tur))

    def _enerji_yapisi_goster(self, enerji):
        ad = mt.yapi_bul(enerji["gruplar"]) if enerji else None
        eski = self.t_enerji_yapi.blockSignals(True)
        try:
            self.t_enerji_yapi.setCurrentIndex(max(self.t_enerji_yapi.findData(ad), 0))
        finally:
            self.t_enerji_yapi.blockSignals(eski)

    def _mesh_eksen_anlamli(self, tur):
        """Ucuncu bolme anlamli mi: kurede (r, θ, φ) her zaman; digerinde z ekseni
        (2B modelde ag tek dilimdir; bkz. kurucu.tally_mesh_sinirlari)."""
        return tur == mt.KURESEL or self._mesh_nz_anlamli()

    def _mesh_formu_gorunurluk(self):
        """Ag satirlarinin gorunurlugu (_tally_gorunurluk cagirir)."""
        tf = self._t_form
        var = self.t_mesh_var.isChecked()
        tur = self.t_mesh_tur.currentData()
        acik = var and not self.t_mesh_oto.isChecked()
        for w, ad in zip((self.t_mesh_nx, self.t_mesh_ny, self.t_mesh_nz),
                         mt.EKSEN_ADLARI[tur]):
            w._etiket.setText(ad)
        uc = self._mesh_eksen_anlamli(tur)
        self.t_mesh_nz.setVisible(uc)
        self.t_mesh_nz._etiket.setVisible(uc)
        tf.setRowVisible(self.t_mesh_tur, var)
        tf.setRowVisible(self.t_mesh_oto, var)
        tf.setRowVisible(self.t_mesh_alt_satiri, acik and tur == mt.DUZENLI)
        tf.setRowVisible(self.t_mesh_ust_satiri, acik and tur == mt.DUZENLI)
        tf.setRowVisible(self.t_mesh_r, acik and tur != mt.DUZENLI)
        tf.setRowVisible(self.t_mesh_z_satiri, acik and tur == mt.SILINDIRIK)
        tf.setRowVisible(self.t_mesh_oneri, var)
        tf.setRowVisible(self.t_enerji_yapi, self.t_enerji_var.isChecked())
        t = self._secili_tally() or {}
        self._enerji_yapisi_goster(next((f for f in t.get("filtreler", [])
                                         if f.get("tur") == "enerji"), None))
        if var:
            self.t_mesh_oneri.setText(self._oneri_metni(tur, self._mesh_onerisi(tur)))

    def _mesh_formu_filtresi(self, eski_mesh):
        """Formdan yeni ag filtresi (yeni sozluk). Formun yonetmedigi alanlar
        (merkez vb.) korunur; tur degisirse eski turun sinirlari atilir."""
        tur = self.t_mesh_tur.currentData()
        eski = dict(eski_mesh or {})
        eski_b = list(eski.get("boyut") or [10, 10, 1])
        boyut = [self.t_mesh_nx.value(), self.t_mesh_ny.value(),
                 self.t_mesh_nz.value() if self._mesh_eksen_anlamli(tur) else eski_b[2]]
        korunan = {k: v for k, v in eski.items()
                   if k not in ("tur", "mesh_turu", "boyut", "otomatik", "alt", "ust",
                                "r_ust", "z_alt", "z_ust")}
        if self.t_mesh_oto.isChecked():
            yeni = mt.filtre_duzenli(boyut) if tur == mt.DUZENLI else (
                mt.filtre_silindirik(boyut) if tur == mt.SILINDIRIK else mt.filtre_kuresel(boyut))
        elif tur == mt.DUZENLI:
            yeni = mt.filtre_duzenli(boyut, [w.value() for w in self.t_mesh_alt],
                                     [w.value() for w in self.t_mesh_ust])
        elif tur == mt.SILINDIRIK:
            yeni = mt.filtre_silindirik(boyut, self.t_mesh_r.value(),
                                        self.t_mesh_z_alt.value(), self.t_mesh_z_ust.value())
        else:
            yeni = mt.filtre_kuresel(boyut, self.t_mesh_r.value())
        return dict(korunan, **yeni)

    # ------------------------------------------------------------------
    # sinyaller
    # ------------------------------------------------------------------
    def _mesh_turu_degisti(self, *_):
        if self._yukleniyor:
            return
        tur = self.t_mesh_tur.currentData()
        if not self.t_mesh_oto.isChecked():
            self._sinirlari_goster(tur, self._mesh_onerisi(tur))
        self._tally_kaydet()

    def _mesh_oto_degisti(self, acik):
        """Otomatik kapaninca o anki oneri acik sinir olarak baslar."""
        if self._yukleniyor:
            return
        if not acik:
            tur = self.t_mesh_tur.currentData()
            self._sinirlari_goster(tur, self._mesh_onerisi(tur))
        self._tally_kaydet()

    def _enerji_yapisi_secildi(self, *_):
        if self._yukleniyor:
            return
        ad = self.t_enerji_yapi.currentData()
        if ad is None:
            return
        self.t_enerji.setText(", ".join("%.12g" % g for g in mt.grup_sinirlari(ad)))
        self.t_enerji.setCursorPosition(0)
        self._tally_kaydet()
