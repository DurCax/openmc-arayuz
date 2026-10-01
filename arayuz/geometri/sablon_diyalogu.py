# -*- coding: utf-8 -*-
"""
================================================================================
 arayuz/geometri/sablon_diyalogu.py  --  Yeni sablonlarin parametre formu
================================================================================
 sablonlar.varsayilanlar(spec, anahtar) sozlugunun her alani icin bir denetim
 kurulur (turu alan adindan: demet / malzeme / tamsayi / uzunluk / aci /
 yukseklik). parametreler() formdaki degerleri, spec_uret() YENI spec'i verir
 (hata: sablonlar.SablonHatasi). Testler exec() cagirmadan kullanir.
================================================================================
"""

from PySide6 import QtWidgets

from cekirdek.ceviri import N_, _
from arayuz import bilesenler as b
from arayuz.geometri import sablonlar
from arayuz.geometri.form_ortak import aci, form_duzeni, kutu_doldur, uzunluk
from arayuz.ortak import ipucu

ETIKETLER = {
    "demet_a": N_("Çekirdek demeti A"), "demet_b": N_("Çekirdek demeti B (dama)"),
    "demet": N_("Demet"), "n": N_("Çekirdek boyutu (n×n)"), "adim": N_("Kafes adımı"),
    "blok_adim": N_("Blok adımı (düz–düz)"), "blok_halka": N_("Blok halka sayısı"),
    "blok_icerik": N_("Blok içeriği"), "blok_malzeme": N_("Blok malzemesi"),
    "kanal_yaricap": N_("Blok kanal yarıçapı"), "dolgu": N_("Aralık dolgusu"),
    "yansitici_kalinlik": N_("Dış yansıtıcı kalınlığı"),
    "yansitici_malzeme": N_("Yansıtıcı malzemesi"), "halka": N_("Kor halka sayısı"),
    "yonelim": N_("Kor yönelimi"), "dis_dolgu": N_("Kafes dış dolgusu"),
    "yansitici_apotem": N_("Yansıtıcı apotemi"), "yansitici_yaricap": N_("Yansıtıcı yarıçapı"),
    "tambur_sayi": N_("Tambur sayısı"), "tambur_merkez": N_("Tambur merkez yarıçapı"),
    "tambur_baslangic": N_("Başlangıç açısı"), "donme": N_("Dönme (grup)"),
    "tambur_adi": N_("Tambur tanımı adı"), "tambur_yaricap": N_("Tambur yarıçapı"),
    "tambur_govde": N_("Tambur gövdesi"), "tambur_emici": N_("Emici malzemesi"),
    "tambur_emici_ic": N_("Emici iç yarıçapı"), "tambur_emici_aci": N_("Emici yay açısı"),
    "yukseklik": N_("Yükseklik"),
}
_TAMSAYI = ("n", "blok_halka", "halka", "tambur_sayi")
_ACI = ("tambur_baslangic", "donme", "tambur_emici_aci")
_MALZEME = ("blok_malzeme", "dolgu", "yansitici_malzeme", "dis_dolgu", "tambur_govde",
            "tambur_emici")


class SablonDiyalogu(QtWidgets.QDialog):
    def __init__(self, spec, anahtar, parent=None):
        super().__init__(parent)
        self.spec, self.anahtar = spec, anahtar
        self.setWindowTitle(_(sablonlar.YENI_SABLONLAR[anahtar]))
        self._alanlar = {}
        self.hata = ipucu("")
        d = QtWidgets.QVBoxLayout(self)
        d.addWidget(ipucu(_("Şablon ölçülerden bir geometri ağacı kurar ve model gelişmiş "
                            "geometriye geçer. Geri Al şablondan önceki duruma döner.")))
        govde = QtWidgets.QWidget()
        f = form_duzeni(govde)
        for alan, deger in sablonlar.varsayilanlar(spec, anahtar).items():
            w = self._denetim(alan, deger)
            self._alanlar[alan] = w
            f.addRow(_(ETIKETLER.get(alan, alan)), w)
        alan_ = QtWidgets.QScrollArea()
        alan_.setWidgetResizable(True)
        alan_.setWidget(govde)
        d.addWidget(alan_, 1)
        d.addWidget(self.hata)
        dugmeler = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok
                                              | QtWidgets.QDialogButtonBox.Cancel)
        dugmeler.accepted.connect(self._kabul)
        dugmeler.rejected.connect(self.reject)
        d.addWidget(dugmeler)
        self.yeni_spec = None

    # ------------------------------------------------------------------
    def _denetim(self, alan, deger):
        if alan.startswith("demet"):
            k = QtWidgets.QComboBox()
            tur = "altigen" if self.anahtar == "altigen_tambur" else "kare"
            kutu_doldur(k, [(x["ad"], x["ad"]) for x in self.spec.get("demetler") or []
                            if x.get("tur", "kare") == tur], deger)
            return k
        if alan == "blok_icerik":
            k = QtWidgets.QComboBox()
            ogeler = [(sablonlar.YANSITICI_BLOK, _("Yansıtıcı blok (malzeme + kanal)"))]
            ogeler += [(x["ad"], _("Yakıt: {ad}").format(ad=x["ad"]))
                       for x in self.spec.get("demetler") or [] if x.get("tur") == "altigen"]
            kutu_doldur(k, ogeler, deger)
            return k
        if alan in _MALZEME:
            k = QtWidgets.QComboBox()
            kutu_doldur(k, [("bosluk", _("Boşluk (void)"))]
                        + [(m["ad"], m["ad"]) for m in self.spec.get("malzemeler") or []], deger)
            return k
        if alan == "yonelim":
            k = QtWidgets.QComboBox()
            kutu_doldur(k, [("x", "x"), ("y", "y")], deger)
            return k
        if alan == "tambur_adi":
            return QtWidgets.QLineEdit(str(deger or ""))
        if alan in _TAMSAYI:
            k = QtWidgets.QSpinBox()
            k.setRange(0 if alan == "tambur_sayi" else 1, 64)
            k.setValue(int(deger or 0))
            return k
        if alan == "yukseklik":
            return _YukseklikSecici(deger)
        if alan in _ACI:
            return aci(float(deger or 0.0), _(ETIKETLER[alan]))
        return uzunluk(float(deger or 0.0), 0.0, _(ETIKETLER.get(alan, alan)))

    def parametreler(self):
        p = {}
        for alan, w in self._alanlar.items():
            if isinstance(w, QtWidgets.QComboBox):
                p[alan] = w.currentData()
            elif isinstance(w, QtWidgets.QLineEdit):
                p[alan] = w.text().strip()
            elif isinstance(w, QtWidgets.QSpinBox):
                p[alan] = w.value()
            elif isinstance(w, _YukseklikSecici):
                p[alan] = w.deger()
            else:
                p[alan] = w.deger()
        return p

    def spec_uret(self):
        return sablonlar.uret(self.spec, self.anahtar, self.parametreler())

    def _kabul(self):
        try:
            self.yeni_spec = self.spec_uret()
        except sablonlar.SablonHatasi as e:
            self.hata.setText(str(e))
            return
        self.accept()


class _YukseklikSecici(QtWidgets.QWidget):
    def __init__(self, deger, parent=None):
        super().__init__(parent)
        self.iki = QtWidgets.QCheckBox(_("2B"))
        self.h = uzunluk(float(deger or 100.0), 1e-6, _("yükseklik"))
        d = QtWidgets.QHBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        d.addWidget(self.iki)
        d.addWidget(self.h, 1)
        self.iki.setChecked(deger is None)
        self.h.setEnabled(deger is not None)
        self.iki.toggled.connect(lambda a: self.h.setEnabled(not a))

    def deger(self):
        return None if self.iki.isChecked() else self.h.deger()


def calistir(spec, anahtar, ebeveyn=None):
    """Diyalogu acar; kabul edilirse YENI spec, yoksa None."""
    d = SablonDiyalogu(spec, anahtar, ebeveyn)
    d.resize(b.SayiBirim().sizeHint().width() * 5, d.sizeHint().height())
    return d.yeni_spec if d.exec() == QtWidgets.QDialog.Accepted else None
