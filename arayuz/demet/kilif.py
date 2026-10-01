# -*- coding: utf-8 -*-
"""
 arayuz/demet/kilif.py  --  KilifMixin: altigen demet kilifi (duct) karti

 demetler[].kilif = {"ic_duz": cm, "kalinlik": cm, "malzeme": ad}
 (cekirdek/sema_yapici.demet_kilifi; kurulum cekirdek/altigen_kor.py). Kilif
 YALNIZ altigen demette kurulur; kare demette kart gizlidir. Kilif kapatilinca
 alan spec'ten kaldirilir (kilifsiz demet: pin kafesi kor hucresinde kirpilir).
 Olculer ve pinlerin kilifa sigmasi dogrulamanin kendi kuraliyla
 (dogrula.geometri.kilif_kontrol) anlik gosterilir. Duzenleme sekmenin
 _kaydet kalibina uyar (secili demet sozlugu yerinde yazilir).
"""

from PySide6 import QtWidgets

from cekirdek import altigen_kor
from cekirdek.ceviri import _
from cekirdek.dogrula.geometri import kilif_kontrol
from arayuz import bilesenler as bl
from arayuz import sekme_duzen as sd
from arayuz.ortak import sayi
from arayuz.cubuk.malzeme_kutusu import MalzemeKutusu
from arayuz.cubuk.parca_islemleri import _renk, rol_listesi, rol_malzemesi

VARSAYILAN_KALINLIK = 0.3        # cm; tipik SFR kilif duvari 0.3-0.4 cm


def varsayilan_kilif(spec, d):
    """YENI kilif: ic olcu pin zarfi (dis halka pinleri kilifa sigar), yapisal malzeme."""
    malzeme = rol_malzemesi(spec, "yapisal") or next(
        (m["ad"] for m in spec.get("malzemeler") or []), None)
    return {"ic_duz": round(altigen_kor.pin_zarfi(d), 5), "kalinlik": VARSAYILAN_KALINLIK,
            "malzeme": malzeme}


class KilifMixin(object):
    """Secili altigen demetin kilif karti."""

    def _kilif_karti(self):
        self.kilif_var = QtWidgets.QCheckBox(_("Kılıf (duct) var"))
        self.kilif_var.setToolTip(_(
            "Altıgen demeti saran duvar (SFR, VVER-440). Kılıfın dışı ile demet "
            "hücresinin sınırı arası 'Demet dışı' malzemesiyle dolar."))
        self.kilif_ic = sayi(10.0, 5, 0.0001, 1000.0, 0.01, "cm")
        self.kilif_ic.setToolTip(_("Kılıfın iç düz yüzden düz yüze ölçüsü."))
        self.kilif_kalinlik = sayi(VARSAYILAN_KALINLIK, 5, 0.0001, 100.0, 0.01, "cm")
        self.kilif_kalinlik.setToolTip(_("Kılıf duvarının kalınlığı."))
        self._kilif_mal_yeri = QtWidgets.QHBoxLayout()
        self.kilif_malzeme = None
        self.kilif_dis = QtWidgets.QLabel("")
        self.kilif_dis.setObjectName("soluk")
        self.kilif_hata = QtWidgets.QLabel("")
        self.kilif_hata.setWordWrap(True)
        self.kilif_hata.setVisible(False)
        f = sd.form()
        f.addRow(self.kilif_var)
        f.addRow(_("İç ölçü"), self.kilif_ic)
        f.addRow(_("Kalınlık"), self.kilif_kalinlik)
        f.addRow(_("Malzeme"), self._kilif_mal_yeri)
        f.addRow(_("Dış ölçü"), self.kilif_dis)
        # Kilif kapaliyken yalniz onay kutusu gorunur: kilifsiz altigen demette
        # sag sutun uzayip sayfa dikey kaydirmasin (test_demet_yerlesim P7,
        # 1600x950 altigen 7 halka; olculdu 02.10.2026).
        self._kilif_form = f
        self.kilif_karti = bl.Kart(_("Kılıf"))
        self.kilif_karti.govde.addLayout(f)
        self.kilif_karti.ekle(self.kilif_hata)
        self.kilif_var.toggled.connect(self._kilif_ac_kapa)
        self.kilif_ic.valueChanged.connect(self._kilif_kaydet)
        self.kilif_kalinlik.valueChanged.connect(self._kilif_kaydet)
        return self.kilif_karti

    def _kilif_malzeme_kur(self, secili):
        while self._kilif_mal_yeri.count():
            w = self._kilif_mal_yeri.takeAt(0).widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self.kilif_malzeme = MalzemeKutusu(self.spec, secili, rol_listesi(self.spec, "yapisal"),
                                           bos=False)
        self.kilif_malzeme.currentIndexChanged.connect(self._kilif_kaydet)
        self._kilif_mal_yeri.addWidget(self.kilif_malzeme, 1)

    def _kilif_doldur(self, d):
        """Secili demet (yukleme sirasinda cagrilir; sinyal spec'e yazmaz)."""
        altigen = d is not None and d.get("tur") == "altigen"
        self.kilif_karti.setVisible(altigen)
        if not altigen:
            return
        k = altigen_kor.kilif(d)
        sablon = k or varsayilan_kilif(self.spec, d)
        self.kilif_var.setChecked(k is not None)
        self.kilif_ic.setValue(float(sablon.get("ic_duz") or 0.0))
        self.kilif_kalinlik.setValue(float(sablon.get("kalinlik") or 0.0))
        self._kilif_malzeme_kur(sablon.get("malzeme"))
        self._kilif_durum(d)

    def _kilif_durum(self, d):
        acik = self.kilif_var.isChecked()
        for satir in range(1, self._kilif_form.rowCount()):
            self._kilif_form.setRowVisible(satir, acik)
        for w in (self.kilif_ic, self.kilif_kalinlik, self.kilif_malzeme):
            if w is not None:
                w.setEnabled(acik)
        self.kilif_dis.setText("%.5f cm" % altigen_kor.demet_dis_olcu(d) if acik else "—")
        hatalar = [b.mesaj for b in kilif_kontrol(self.spec, d)] if acik else []
        self.kilif_hata.setText("\n".join(hatalar))
        self.kilif_hata.setStyleSheet("color: %s;" % _renk("hata"))
        self.kilif_hata.setVisible(bool(hatalar))

    def _kilif_ac_kapa(self, acik):
        if self._yukleniyor:
            return
        d = self._secili()
        if d is None:
            return
        if acik:
            d["kilif"] = varsayilan_kilif(self.spec, d)
            eski, self._yukleniyor = self._yukleniyor, True
            try:
                self._kilif_doldur(d)
            finally:
                self._yukleniyor = eski
        else:
            d.pop("kilif", None)
            self._kilif_durum(d)
        self._ozet_guncelle(d)
        self.bildir()

    def _kilif_kaydet(self, *_a):
        if self._yukleniyor or not self.kilif_var.isChecked():
            return
        d = self._secili()
        if d is None or d.get("tur") != "altigen":
            return
        d["kilif"] = dict(d.get("kilif") or {}, ic_duz=self.kilif_ic.value(),
                          kalinlik=self.kilif_kalinlik.value(),
                          malzeme=self.kilif_malzeme.currentData() if self.kilif_malzeme
                          else None)
        self._kilif_durum(d)
        self.bildir()
