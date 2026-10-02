# -*- coding: utf-8 -*-
"""
 arayuz/ayar/yerel_k_karti.py  --  Hesap ayarlari: "Yerel k haritası" karti (K4)

 Modele cekirdek/yerel_k.py tally'lerini ekler/kaldirir (yerel_k.tally_ekle /
 tally_kaldir; isaret "uretici": "yerel_k"). Kart kendi icinde kapalidir: sekme
 yalniz doldur(spec) cagirir ve `degisti` sinyalini bildir()'e baglar.
 Desteklenmeyen modelde (altigen, bosluklu kor) spec degismez, hata kartta yazar.
"""

from typing import Any, Optional

from PySide6 import QtCore, QtWidgets

from arayuz import bilesenler as b
from arayuz.ortak import ipucu
from cekirdek import yerel_k
from cekirdek.ceviri import N_, _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)
_DUZEYLER = ((None, N_("Kapalı")), ("pin", N_("Pin")), ("demet", N_("Demet")))
_Z = (("model", N_("tüm model yüksekliği")), ("aktif", N_("yalnız aktif (fisil) bölge")))


class YerelKAyarKarti(b.Kart):
    """Yerel k (pin/demet) tally'sini acan kart."""

    degisti = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(_("Yerel k haritası (pin/demet)"),
                         _("νΣ_f φ / (Σ_a φ − X) — yerel üretim / yok olma oranı"),
                         parent=parent)
        self._spec: Optional[dict] = None
        self._yukleniyor = False
        self.duzey = QtWidgets.QComboBox()
        for veri, ad in _DUZEYLER:
            self.duzey.addItem(_(ad), veri)
        self.z = QtWidgets.QComboBox()
        for veri, ad in _Z:
            self.z.addItem(_(ad), veri)
        self.z.setToolTip(_("3B modelde 'tüm model' eksenel yansıtıcıyı da içerir (kapsam 1, "
                            "sonsuz kafes denetimi); 'aktif' yalnız fisil katmanı alır."))
        form = QtWidgets.QFormLayout()
        form.addRow(_("Düzey:"), self.duzey)
        form.addRow(_("Eksenel kapsam:"), self.z)
        self.govde.addLayout(form)
        self.ekle(ipucu(_("Koşuya hatveye hizalı bir mesh tally'si ve filtresiz bir toplam "
                          "tally'si ekler (adları yerel_k_ ile başlar); harita Çalıştır "
                          "sayfasında görünür. Yalnız kare kafes.")))
        self.uyari = ipucu("")
        self.uyari.setVisible(False)
        self.ekle(self.uyari)
        self.duzey.currentIndexChanged.connect(self._kaydet)
        self.z.currentIndexChanged.connect(self._kaydet)

    def doldur(self, spec: dict) -> None:
        """Spec'teki yerel k tally'sinden doldurur (sinyal yaymadan)."""
        self._spec = spec
        duzey = next((d for d in yerel_k.DUZEYLER if yerel_k.tally_duzeni(spec, d)), None) \
            if spec else None
        self._yukleniyor = True
        try:
            self.duzey.setCurrentIndex(max(self.duzey.findData(duzey), 0))
        finally:
            self._yukleniyor = False
        self.z.setEnabled(duzey is not None)
        self.uyari.setVisible(False)

    def _geri_al(self, hata: Exception) -> None:
        _log.warning("yerel k tally'si eklenemedi: %s", hata)
        self._yukleniyor = True
        try:
            self.duzey.setCurrentIndex(self.duzey.findData(None))
        finally:
            self._yukleniyor = False
        self.uyari.setText(_("Yerel k bu modelde kurulamaz: %s") % hata)
        self.uyari.setVisible(True)

    def _kaydet(self, *_a: Any) -> None:
        duzey = self.duzey.currentData()
        self.z.setEnabled(duzey is not None)
        if self._yukleniyor or self._spec is None:
            return
        try:
            yeni = yerel_k.tally_kaldir(self._spec)
            if duzey is not None:
                yeni = yerel_k.tally_ekle(yeni, duzey, self.z.currentData())
        except yerel_k.YerelKHatasi as e:
            self._geri_al(e)
            return
        # Sekmenin bellekteki modeli yerinde guncellenir (diger kartlarla ayni kalip).
        self._spec["tallyler"] = yeni["tallyler"]
        self.uyari.setVisible(False)
        self.degisti.emit()
