# -*- coding: utf-8 -*-
"""
================================================================================
 arayuz/geometri/sinir_formu.py  --  Sinir kosulu formu (yuz basina; §15 karar 4)
================================================================================
 Yan / alt / ust sinir kosulu + "Yüz başına yan sınır": en dis kesit
 dikdortgense dort yuz (−x, +x, −y, +y), altigense (ya da kafes zarfi) alti
 yuz ayri kosul alir. Spec bicimi (G-1, cekirdek/geometri/kurulum.py):
     sinir.yuzler = {"-x": .., "+x": .., "-y": .., "+y": ..}      dikdortgen
     sinir.yuzler = [k0, k1, k2, k3, k4, k5]                       altigen
 altigen yuz sirasi yuz normali acisi artan: prizma 'y' 0°, 60°, ...;
 'x' 30°, 90°, ... Periyodik yalniz karsi yuz ciftinde (ikisi birden) anlamli;
 tek tarafli periyodik secilirse form bunu isaretler (dogrulama ayrica bildirir).
 Sablon (kor.sinir) ve gelismis (kok.sinir) ayni formu kullanir.
================================================================================
"""

from PySide6 import QtCore, QtWidgets

from cekirdek.ceviri import N_, _
from cekirdek.geometri.kesit import altigen_normal_acilari
from arayuz import bilesenler as b
from arayuz.geometri.form_ortak import form_duzeni
from arayuz.ortak import ipucu
from arayuz.tasarim import tokenlar

A = tokenlar.ARALIK

SINIR_ADLARI = {
    "reflective": N_("Yansıtıcı (reflective)"),
    "vacuum": N_("Vakum (vacuum)"),
    "white": N_("Beyaz (white)"),
    "periodic": N_("Periyodik (periodic)"),
}
DIKDORTGEN_YUZLERI = ("-x", "+x", "-y", "+y")
_DIKDORTGEN_ETIKETI = {"-x": N_("−x (sol)"), "+x": N_("+x (sağ)"),
                       "-y": N_("−y (alt)"), "+y": N_("+y (üst)")}
TEMEL = ("vacuum", "reflective", "white")


def yuz_duzeni(dis_kesit, kafes_yonelimi=None):
    """('dikdortgen', 4 ad) | ('altigen', 6 aci) | (None, ()) -- yuz basina uygun mu."""
    s = (dis_kesit or {}).get("sekil")
    if s == "dikdortgen":
        return "dikdortgen", DIKDORTGEN_YUZLERI
    if s == "altigen":
        return "altigen", tuple(altigen_normal_acilari(dis_kesit.get("yonelim", "y")))
    if s == "kafes_zarfi":
        return "altigen", tuple(altigen_normal_acilari(kafes_yonelimi or "y"))
    return None, ()


def tek_tarafli_periyodik(yuzler, duzen):
    """Karsi yuzu periyodik olmayan periyodik yuzler (uyari icin)."""
    if duzen == "dikdortgen" and isinstance(yuzler, dict):
        ciftler = (("-x", "+x"), ("-y", "+y"))
        return [a for p, q in ciftler for a in (p, q)
                if yuzler.get(a) == "periodic" and yuzler.get(q if a == p else p) != "periodic"]
    if duzen == "altigen" and isinstance(yuzler, list) and len(yuzler) == 6:
        return [i for i in range(6)
                if yuzler[i] == "periodic" and yuzler[(i + 3) % 6] != "periodic"]
    return []


class SinirFormu(QtWidgets.QWidget):
    """ayarla(sinir, dis_kesit, uc_boyutlu, yan_secenekleri); degisti(yeni sinir)."""

    degisti = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._yukleniyor = False
        self._sinir = {}
        self._duzen, self._yuz_adlari = None, ()
        self.yan = QtWidgets.QComboBox()
        self.alt = QtWidgets.QComboBox()
        self.ust = QtWidgets.QComboBox()
        for k, ad in ((self.yan, _("yan sınır")), (self.alt, _("alt sınır")),
                      (self.ust, _("üst sınır"))):
            k.setAccessibleName(ad)
        self.yuz_basina = QtWidgets.QCheckBox(_("Yüz başına yan sınır"))
        self.yuz_basina.setToolTip(_(
            "Çeyrek kor gibi simetri modelleri için: her dış yüz ayrı koşul alır "
            "(ör. iki simetri yüzü yansıtıcı, iki dış yüz vakum)."))
        self.yuz_kutusu = QtWidgets.QWidget()
        self._yuz_form = form_duzeni(self.yuz_kutusu)
        self._yuz_kutulari = []
        self.not_etiketi = ipucu("")
        f = form_duzeni(self)
        f.addRow(_("Yan"), self.yan)
        f.addRow(_("Alt"), self.alt)
        f.addRow(_("Üst"), self.ust)
        f.addRow(self.yuz_basina)
        f.addRow(self.yuz_kutusu)
        f.addRow(self.not_etiketi)
        self._form = f
        for k in (self.yan, self.alt, self.ust):
            k.currentIndexChanged.connect(self._degisti)
        self.yuz_basina.toggled.connect(self._yuz_basina_degisti)

    # ------------------------------------------------------------------
    def ayarla(self, sinir, dis_kesit, uc_boyutlu, yan_secenekleri=None, kafes_yonelimi=None):
        self._sinir = dict(sinir or {})
        self._duzen, self._yuz_adlari = yuz_duzeni(dis_kesit, kafes_yonelimi)
        yan = list(yan_secenekleri or TEMEL)
        self._yukleniyor = True
        try:
            self._kutu(self.yan, yan, self._sinir.get("yan", "vacuum"))
            self._kutu(self.alt, TEMEL, self._sinir.get("alt", "vacuum"))
            self._kutu(self.ust, TEMEL, self._sinir.get("ust", "vacuum"))
            self._form.setRowVisible(self.alt, bool(uc_boyutlu))
            self._form.setRowVisible(self.ust, bool(uc_boyutlu))
            self._yuzleri_kur()
            self.yuz_basina.setChecked(bool(self._sinir.get("yuzler")) and bool(self._duzen))
        finally:
            self._yukleniyor = False
        self._form.setRowVisible(self.yuz_basina, bool(self._duzen))
        self._gorunurluk()

    @staticmethod
    def _kutu(kutu, secenekler, deger):
        eski = kutu.blockSignals(True)
        try:
            kutu.clear()
            for s in secenekler:
                kutu.addItem(_(SINIR_ADLARI.get(s, s)), s)
            i = kutu.findData(deger)
            if i < 0 and deger:
                kutu.addItem(_("{ad} — bu yüzeyde geçersiz").format(
                    ad=_(SINIR_ADLARI.get(deger, deger))), deger)
                i = kutu.count() - 1
            kutu.setCurrentIndex(max(i, 0))
        finally:
            kutu.blockSignals(eski)

    def _yuzleri_kur(self):
        while self._yuz_form.rowCount():
            self._yuz_form.removeRow(0)
        self._yuz_kutulari = []
        yuzler = self._sinir.get("yuzler")
        yan = self._sinir.get("yan", "vacuum")
        secenek = list(TEMEL) + ["periodic"]
        for i, ad in enumerate(self._yuz_adlari):
            k = QtWidgets.QComboBox()
            if self._duzen == "dikdortgen":
                etiket = _(_DIKDORTGEN_ETIKETI[ad])
                deger = (yuzler or {}).get(ad, yan) if isinstance(yuzler, dict) else yan
            else:
                etiket = _("Yüz {n} (normal {aci:g}°)").format(n=i + 1, aci=ad)
                deger = yuzler[i] if isinstance(yuzler, list) and i < len(yuzler) else yan
            k.setAccessibleName(etiket)
            self._kutu(k, secenek, deger)
            k.currentIndexChanged.connect(self._degisti)
            self._yuz_form.addRow(etiket, k)
            self._yuz_kutulari.append(k)

    def _gorunurluk(self):
        acik = self.yuz_basina.isChecked() and bool(self._duzen)
        self.yuz_kutusu.setVisible(acik)
        self._form.setRowVisible(self.yan, not acik)
        tek = tek_tarafli_periyodik(self._yuzler(), self._duzen) if acik else []
        self.not_etiketi.setText(
            _("Periyodik yüzün karşı yüzü de periyodik olmalı (tek taraflı periyodik "
              "OpenMC'yi durdurur).") if tek else "")
        self._form.setRowVisible(self.not_etiketi, bool(tek))

    def _yuzler(self):
        degerler = [k.currentData() for k in self._yuz_kutulari]
        if self._duzen == "dikdortgen":
            return dict(zip(self._yuz_adlari, degerler))
        return degerler

    def sinir(self):
        """Formun sinir sozlugu (YENI sozluk)."""
        s = {k: v for k, v in self._sinir.items() if k != "yuzler"}
        s["yan"] = self.yan.currentData()
        if self._form.isRowVisible(self.alt):
            s["alt"] = self.alt.currentData()
            s["ust"] = self.ust.currentData()
        if self.yuz_basina.isChecked() and self._duzen:
            s["yuzler"] = self._yuzler()
        return s

    def _yuz_basina_degisti(self, _acik):
        self._gorunurluk()
        self._degisti()

    def _degisti(self, *_a):
        if self._yukleniyor:
            return
        self._gorunurluk()
        self._sinir = self.sinir()
        self.degisti.emit(self.sinir())


def kart(baslik=None):
    """Sinir formu + Kart (sablon gorunumunde kullanilir)."""
    k = b.Kart(baslik or _("Sınır koşulları"))
    form = SinirFormu()
    k.ekle(form)
    return k, form
