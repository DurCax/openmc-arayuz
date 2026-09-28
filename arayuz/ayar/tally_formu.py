# -*- coding: utf-8 -*-
"""
 arayuz/ayar/tally_formu.py  --  TallyFormuMixin: tally listesi ve formu

 arayuz/sekme_ayar.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import sekme_ayar; sekme_ayar.X` aynen calisir.
"""

from PySide6 import QtCore, QtWidgets
from cekirdek import sema
from arayuz.ayar.sabitler import OZEL, SKORLAR, SKOR_SETLERI, _FILTRE_ADI, _SKOR_ADI


class TallyFormuMixin(object):
    """Tally listesi ve secili tally'nin formu."""

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
