# -*- coding: utf-8 -*-
"""
================================================================================
 arayuz/geometri/form_ortak.py  --  Ozellik formlarinin ortak tabani + kesit editoru
================================================================================
 Her form SECILI OGEYI gosterir ve her degisiklikte YENI agaci yayar
 (agac_degisti(yeni_agac)); agaci kendisi degistirmez (duzenle.py saf).
 Editor yeni agaci spec'e yazar; pencerenin gecmisi 700 ms bosta kalinca
 adimi yigar (form alanlari); yapisal agac islemleri tek adimdir (editor.py).

 Sayi kutulari birimlidir (bilesenler.SayiBirim: cm, derece).
================================================================================
"""

from PySide6 import QtCore, QtWidgets

from cekirdek.ceviri import N_, _
from arayuz import bilesenler as b
from arayuz.geometri import duzenle
from arayuz.tasarim import tokenlar

A = tokenlar.ARALIK
_BUYUK = 1.0e5

SEKIL_ADLARI = {
    "dikdortgen": N_("Dikdörtgen"),
    "silindir": N_("Silindir (daire)"),
    "altigen": N_("Altıgen"),
    "kure": N_("Küre"),
    "kafes_zarfi": N_("Kafes zarfı (altıgen kafesin kırık sınırı)"),
}
YONELIM_ADLARI = {"y": N_("y — düz yüzler sağda/solda"), "x": N_("x — düz yüzler üstte/altta")}


def uzunluk(deger=1.0, en_az=0.0, ad=None):
    return b.SayiBirim("cm", deger=deger, en_az=en_az, en_cok=_BUYUK, ondalik=4, adim=0.1,
                       erisilebilir_ad=ad)


def aci(deger=0.0, ad=None):
    return b.SayiBirim("°", deger=deger, en_az=-3600.0, en_cok=3600.0, ondalik=2, adim=5.0,
                       erisilebilir_ad=ad)


def form_duzeni(ebeveyn):
    f = QtWidgets.QFormLayout(ebeveyn)
    f.setContentsMargins(0, 0, 0, 0)
    f.setSpacing(A["s"])
    f.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
    return f


def kutu_doldur(kutu, ogeler, secili):
    """Secim kutusu: [(veri, etiket)]; listede olmayan deger ayri oge olur."""
    eski = kutu.blockSignals(True)
    try:
        kutu.clear()
        for veri, etiket in ogeler:
            kutu.addItem(etiket, veri)
        i = kutu.findData(secili)
        if i < 0 and secili is not None:
            kutu.addItem(_("{ad} (tanımsız)").format(ad=secili), secili)
            i = kutu.count() - 1
        kutu.setCurrentIndex(max(i, 0))
    finally:
        kutu.blockSignals(eski)


def sayi_yaz(kutu, deger):
    """SayiBirim'e sinyalsiz deger yazar."""
    eski = kutu.blockSignals(True)
    ic = kutu.kutu.blockSignals(True)
    try:
        kutu.deger_ayarla(float(deger or 0.0))
    finally:
        kutu.kutu.blockSignals(ic)
        kutu.blockSignals(eski)


class FormTabani(QtWidgets.QWidget):
    """Secili oge formu: yukle(spec, agac, yol); agac_degisti(yeni_agac)."""

    agac_degisti = QtCore.Signal(object)
    BASLIK = ""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec, self.agac, self.yol = None, None, None
        self._yukleniyor = False

    def yukle(self, spec, agac, yol):
        self.spec, self.agac, self.yol = spec, agac, tuple(yol)
        self._yukleniyor = True
        try:
            self.doldur(duzenle.al(agac, self.yol))
        finally:
            self._yukleniyor = False

    def agaci_tazele(self, agac):
        """Editor yeni agaci yazdi: form yeniden kurulmadan guncel agaci tutar."""
        self.agac = agac

    def doldur(self, oge):                            # pragma: no cover - soyut
        raise NotImplementedError

    def oge(self):
        return duzenle.al(self.agac, self.yol)

    def yaz(self, alan, deger, yol=None):
        """Alanin yeni degeriyle yeni agac yayar (yukleme sirasinda susar)."""
        if self._yukleniyor or self.agac is None:
            return
        yeni = duzenle.alan_yaz(self.agac, yol if yol is not None else self.yol, alan, deger)
        self.agac = yeni
        self.agac_degisti.emit(yeni)

    def agac_yay(self, yeni):
        if self._yukleniyor:
            return
        self.agac = yeni
        self.agac_degisti.emit(yeni)

    # ---------------- secenek listeleri ----------------
    def malzeme_secenekleri(self):
        from cekirdek import sema
        ogeler = [(duzenle.BOSLUK, _("Boşluk (void)"))]
        ogeler += [(m["ad"], sema.malzeme_etiketi(m)) for m in self.spec.get("malzemeler") or []]
        return ogeler

    def bilesen_secenekleri(self):
        ogeler = []
        for bolum, etiket in (("cubuklar", _("çubuk")), ("plakalar", _("plaka")),
                              ("demetler", _("demet")), ("tamburlar", _("tambur")),
                              ("trisolar", _("TRISO"))):
            ogeler += [(t["ad"], "%s: %s" % (etiket, t["ad"])) for t in self.spec.get(bolum) or []]
        ogeler += [(p["ad"], "%s: %s" % (_("parça"), p["ad"]))
                   for p in (self.agac or {}).get("parcalar") or []]
        return ogeler

    def kutuphane_adlari(self):
        adlar = set()
        for bolum in ("cubuklar", "plakalar", "demetler", "tamburlar", "trisolar",
                      "malzemeler"):
            adlar |= {t.get("ad") for t in self.spec.get(bolum) or []}
        return adlar


class KesitEditoru(QtWidgets.QWidget):
    """Kesit (sekil + olculer). ayarla(kesit, sekiller); degisti(kesit)."""

    degisti = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._yukleniyor = False
        self.sekil = QtWidgets.QComboBox()
        self.sekil.setAccessibleName(_("kesit şekli"))
        self.gx = uzunluk(10.0, 1e-6, _("genişlik x"))
        self.gy = uzunluk(10.0, 1e-6, _("genişlik y"))
        self.r = uzunluk(5.0, 1e-6, _("yarıçap"))
        self.apotem = uzunluk(5.0, 1e-6, _("apotem"))
        self.yonelim = QtWidgets.QComboBox()
        for k, v in YONELIM_ADLARI.items():
            self.yonelim.addItem(_(v), k)
        f = form_duzeni(self)
        f.addRow(_("Şekil"), self.sekil)
        f.addRow(_("Genişlik (x)"), self.gx)
        f.addRow(_("Yükseklik (y)"), self.gy)
        f.addRow(_("Yarıçap"), self.r)
        f.addRow(_("Apotem (merkez–yüz)"), self.apotem)
        f.addRow(_("Yönelim"), self.yonelim)
        self._form = f
        self.sekil.currentIndexChanged.connect(self._degisti)
        self.yonelim.currentIndexChanged.connect(self._degisti)
        for w in (self.gx, self.gy, self.r, self.apotem):
            w.degisti.connect(self._degisti)

    def ayarla(self, kesit, sekiller=("dikdortgen", "silindir", "altigen")):
        kesit = kesit or {"sekil": sekiller[0]}
        self._yukleniyor = True
        try:
            kutu_doldur(self.sekil, [(s, _(SEKIL_ADLARI[s])) for s in sekiller],
                        kesit.get("sekil"))
            boyut = kesit.get("boyut") or (10.0, 10.0)
            sayi_yaz(self.gx, boyut[0])
            sayi_yaz(self.gy, boyut[1])
            sayi_yaz(self.r, kesit.get("yaricap") or 5.0)
            sayi_yaz(self.apotem, kesit.get("apotem") or 5.0)
            kutu_doldur(self.yonelim, [(k, _(v)) for k, v in YONELIM_ADLARI.items()],
                        kesit.get("yonelim", "y"))
        finally:
            self._yukleniyor = False
        self._gorunurluk()

    def _gorunurluk(self):
        s = self.sekil.currentData()
        for w, gorunur in ((self.gx, s == "dikdortgen"), (self.gy, s == "dikdortgen"),
                           (self.r, s in ("silindir", "kure")), (self.apotem, s == "altigen"),
                           (self.yonelim, s == "altigen")):
            self._form.setRowVisible(w, gorunur)

    def kesit(self):
        s = self.sekil.currentData()
        if s == "dikdortgen":
            return {"sekil": s, "boyut": [self.gx.deger(), self.gy.deger()]}
        if s in ("silindir", "kure"):
            return {"sekil": s, "yaricap": self.r.deger()}
        if s == "altigen":
            return {"sekil": s, "apotem": self.apotem.deger(),
                    "yonelim": self.yonelim.currentData()}
        return {"sekil": s}

    def _degisti(self, *_a):
        self._gorunurluk()
        if not self._yukleniyor:
            self.degisti.emit(self.kesit())
