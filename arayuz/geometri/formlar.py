# -*- coding: utf-8 -*-
"""
================================================================================
 arayuz/geometri/formlar.py  --  Dugum, kap ve halka formlari (§10 "Özellikler")
================================================================================
 IcerikFormu : bir yuvadaki dugum -- icerik turu (malzeme / bilesen / kafes /
               kap / eksenel) + malzeme ya da bilesen secimi + donusum.
 KapFormu    : ad, kesit (sekil + olculer), kokte yukseklik ve sinir (yuz
               basina), kok disinda donusum.
 HalkaFormu  : kalinlik ya da dis kesit.
 Tur degisimi (ornegin malzeme -> kafes) yeni varsayilan dugum koyar; eski
 alt agac Geri Al ile doner.
================================================================================
"""

from PySide6 import QtWidgets

from cekirdek.ceviri import N_, _
from cekirdek.gunluk import kaydedici
from arayuz import bilesenler as b
from arayuz.geometri import duzenle
from arayuz.geometri.form_ortak import (FormTabani, KesitEditoru, aci, form_duzeni,
                                        kutu_doldur, sayi_yaz, uzunluk)
from arayuz.geometri.sinir_formu import SinirFormu
from arayuz.ortak import ipucu

_log = kaydedici("arayuz.geometri.formlar")

TUR_ADLARI = {
    "malzeme": N_("Malzeme"),
    "bilesen": N_("Bileşen (kütüphaneden)"),
    "kafes": N_("Kafes"),
    "kap": N_("Kap (şekil + halkalar)"),
    "eksenel": N_("Eksenel yığın"),
}


class DonusumSatiri(QtWidgets.QWidget):
    """Donme [°] + oteleme (x, y) [cm]; degisti() -> donusum()."""

    def __init__(self, geri_cagir, parent=None):
        super().__init__(parent)
        self.donme = aci(0.0, _("dönme"))
        self.ox = uzunluk(0.0, -1e5, _("öteleme x"))
        self.oy = uzunluk(0.0, -1e5, _("öteleme y"))
        f = form_duzeni(self)
        f.addRow(_("Dönme"), self.donme)
        f.addRow(_("Öteleme x"), self.ox)
        f.addRow(_("Öteleme y"), self.oy)
        for w in (self.donme, self.ox, self.oy):
            w.degisti.connect(lambda _v: geri_cagir(self.donusum()))

    def ayarla(self, donusum):
        d = donusum or {}
        ot = d.get("oteleme") or (0.0, 0.0)
        sayi_yaz(self.donme, d.get("donme") or 0.0)
        sayi_yaz(self.ox, ot[0])
        sayi_yaz(self.oy, ot[1])

    def donusum(self):
        d = {}
        if self.donme.deger():
            d["donme"] = self.donme.deger()
        if self.ox.deger() or self.oy.deger():
            d["oteleme"] = [self.ox.deger(), self.oy.deger()]
        return d or None


class IcerikFormu(FormTabani):
    """Yuvadaki malzeme / bilesen dugumu (ve her dugumde tur degisimi)."""

    BASLIK = N_("İçerik")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tur = QtWidgets.QComboBox()
        self.tur.setAccessibleName(_("içerik türü"))
        self.malzeme = QtWidgets.QComboBox()
        self.malzeme.setAccessibleName(_("malzeme"))
        self.bilesen = QtWidgets.QComboBox()
        self.bilesen.setAccessibleName(_("bileşen"))
        self.donusum = DonusumSatiri(lambda d: self.yaz("donusum", d))
        self.not_etiketi = ipucu(_("Kütüphane bileşenleri (çubuk, demet, tambur) "
                                   "Parçalar/Demet sayfalarında tanımlanır."))
        f = form_duzeni(self)
        f.addRow(_("Tür"), self.tur)
        f.addRow(_("Malzeme"), self.malzeme)
        f.addRow(_("Bileşen"), self.bilesen)
        f.addRow(self.donusum)
        f.addRow(self.not_etiketi)
        self._form = f
        self.tur.currentIndexChanged.connect(self._tur_degisti)
        self.malzeme.currentIndexChanged.connect(
            lambda _i: self.yaz("ad", self.malzeme.currentData()))
        self.bilesen.currentIndexChanged.connect(
            lambda _i: self.yaz("ad", self.bilesen.currentData()))

    def doldur(self, d):
        if isinstance(d, str) or d is None:
            d = {"tur": "malzeme", "ad": d or duzenle.BOSLUK}
        tur = d.get("tur")
        turler = list(TUR_ADLARI) if self.yol != duzenle.KOK else ["kap"]
        kutu_doldur(self.tur, [(t, _(TUR_ADLARI[t])) for t in turler], tur)
        kutu_doldur(self.malzeme, self.malzeme_secenekleri(), d.get("ad") if tur == "malzeme" else None)
        kutu_doldur(self.bilesen, self.bilesen_secenekleri(),
                    d.get("ad") if tur == "bilesen" else None)
        self.donusum.ayarla(d.get("donusum"))
        self._form.setRowVisible(self.malzeme, tur == "malzeme")
        self._form.setRowVisible(self.bilesen, tur == "bilesen")
        self._form.setRowVisible(self.donusum, tur == "bilesen")
        self._form.setRowVisible(self.not_etiketi, tur == "bilesen")

    def _tur_degisti(self, *_a):
        if self._yukleniyor:
            return
        tur = self.tur.currentData()
        eski = self.oge() if isinstance(self.oge(), dict) else {}
        if tur == eski.get("tur"):
            return
        varsayilan = (self.malzeme_secenekleri()[1:2] or [(duzenle.BOSLUK, "")])[0][0]
        bilesenler = self.bilesen_secenekleri()
        yeni = duzenle.yeni_dugum(tur, self.agac, varsayilan,
                                  bilesenler[0][0] if bilesenler else None)
        self.agac_yay(duzenle.dugum_koy(self.agac, self.yol, yeni))


class KapFormu(FormTabani):
    """Kap: ad, kesit; kokte yukseklik + sinir; kok disinda dis dolgu + donusum."""

    BASLIK = N_("Kap")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ad = QtWidgets.QLineEdit()
        self.ad.setAccessibleName(_("görünen ad"))
        self.kimlik = QtWidgets.QLabel("-")
        self.kimlik.setObjectName("soluk")
        self.kesit = KesitEditoru()
        self.iki_boyut = QtWidgets.QCheckBox(_("2B (sonsuz yükseklik)"))
        self.yukseklik = uzunluk(100.0, 1e-6, _("yükseklik"))
        self.yukseklik_notu = ipucu(_("İç bölgede eksenel yığın var: model yüksekliği "
                                      "katmanların toplamıdır."))
        self.sinir = SinirFormu()
        self.donusum = DonusumSatiri(lambda d: self.yaz("donusum", d))
        f = form_duzeni(self)
        f.addRow(_("Ad"), self.ad)
        f.addRow(_("Kimlik"), self.kimlik)
        f.addRow(b.BolumBasligi(_("Kesit")))
        f.addRow(self.kesit)
        f.addRow(self.iki_boyut)
        f.addRow(_("Yükseklik"), self.yukseklik)
        f.addRow(self.yukseklik_notu)
        self.sinir_basligi = b.BolumBasligi(_("Sınır koşulu"))
        f.addRow(self.sinir_basligi)
        f.addRow(self.sinir)
        self.donusum_basligi = b.BolumBasligi(_("Dönüşüm"))
        f.addRow(self.donusum_basligi)
        f.addRow(self.donusum)
        self._form = f
        self.ad.editingFinished.connect(self._ad_degisti)
        self.kesit.degisti.connect(lambda k: self.yaz("kesit", k))
        self.iki_boyut.toggled.connect(self._yukseklik_degisti)
        self.yukseklik.degisti.connect(lambda _v: self._yukseklik_degisti())
        self.sinir.degisti.connect(lambda s: self.yaz("sinir", s))

    def _kok_mu(self):
        return self.yol == duzenle.KOK

    def doldur(self, d):
        kok = self._kok_mu()
        self.ad.setText(d.get("ad") or "")
        self.kimlik.setText(d.get("id") or "-")
        sekiller = ["dikdortgen", "silindir", "altigen"]
        if kok:
            sekiller.append("kure")
            if self._altigen_kafesli(d):
                sekiller.append("kafes_zarfi")
        self.kesit.ayarla(d.get("kesit"), sekiller)
        yigin = isinstance(d.get("ic"), dict) and d["ic"].get("tur") == "eksenel"
        h = d.get("yukseklik")
        self.iki_boyut.setChecked(h is None and not yigin)
        sayi_yaz(self.yukseklik, h or 100.0)
        for w, g in ((self.iki_boyut, kok and not yigin), (self.yukseklik, kok and not yigin
                                                            and h is not None),
                     (self.yukseklik_notu, kok and yigin), (self.sinir_basligi, kok),
                     (self.sinir, kok), (self.donusum_basligi, not kok),
                     (self.donusum, not kok)):
            self._form.setRowVisible(w, g)
        if kok:
            from arayuz.geometri.cizim import bolge_kesitleri
            dis = bolge_kesitleri(d)[-1]
            yon = self._kafes_yonelimi(d)
            self.sinir.ayarla(d.get("sinir"), dis, h is not None or yigin,
                              _yan_secenekleri(dis), yon)
        else:
            self.donusum.ayarla(d.get("donusum"))

    @staticmethod
    def _altigen_kafesli(d):
        ic = d.get("ic")
        if isinstance(ic, dict) and ic.get("tur") == "eksenel":
            ic = ic.get("icerik")
        return isinstance(ic, dict) and ic.get("tur") == "kafes" and ic.get("sekil") == "altigen"

    @staticmethod
    def _kafes_yonelimi(d):
        ic = d.get("ic")
        if isinstance(ic, dict) and ic.get("tur") == "eksenel":
            ic = ic.get("icerik")
        return (ic or {}).get("yonelim", "y") if isinstance(ic, dict) else "y"

    def _ad_degisti(self):
        ad = self.ad.text().strip()
        self.yaz("ad", ad or None)

    def _yukseklik_degisti(self, *_a):
        if self._yukleniyor:
            return
        iki = self.iki_boyut.isChecked()
        self._form.setRowVisible(self.yukseklik, not iki)
        self.yaz("yukseklik", None if iki else self.yukseklik.deger())
        if iki:
            # 2B'de alt/ust sinir yok: kayittan cikarilmaz (uc boyuta donunce korunur).
            _log.debug("kok 2B yapildi")
        self._yukleniyor = True
        try:
            self.doldur(self.oge())
        finally:
            self._yukleniyor = False


def _yan_secenekleri(dis_kesit):
    """Gelismis modda yan sinir secenekleri: periyodik yalniz duzlem ciftli kesitte."""
    s = (dis_kesit or {}).get("sekil")
    temel = ["vacuum", "reflective", "white"]
    return temel + ["periodic"] if s in ("dikdortgen", "altigen") else temel


class HalkaFormu(FormTabani):
    """Halka: kalinlik (ayni sekli buyutur) ya da dis kesit."""

    BASLIK = N_("Halka")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mod = b.SegmentSecici([("kalinlik", _("Kalınlık")), ("dis", _("Dış kesit"))],
                                   "kalinlik")
        self.kalinlik = uzunluk(10.0, 1e-6, _("halka kalınlığı"))
        self.dis = KesitEditoru()
        self.aciklama = ipucu(_("Kalınlık iç sınırın şeklini düzgün büyütür; dış kesit "
                                "farklı bir şekil verir (ör. kare korun çevresinde "
                                "silindirik yansıtıcı)."))
        f = form_duzeni(self)
        f.addRow(_("Tanım"), self.mod)
        f.addRow(_("Kalınlık"), self.kalinlik)
        f.addRow(self.dis)
        f.addRow(self.aciklama)
        self._form = f
        self.mod.secildi.connect(self._mod_degisti)
        self.kalinlik.degisti.connect(self._kaydet)
        self.dis.degisti.connect(self._kaydet)

    def doldur(self, h):
        mod = "dis" if h.get("dis") is not None else "kalinlik"
        self.mod.sec(mod, sinyal=False)
        sayi_yaz(self.kalinlik, h.get("kalinlik") or 10.0)
        self.dis.ayarla(h.get("dis") or {"sekil": "silindir", "yaricap": 50.0})
        self._gorunurluk(mod)

    def _gorunurluk(self, mod):
        self._form.setRowVisible(self.kalinlik, mod == "kalinlik")
        self._form.setRowVisible(self.dis, mod == "dis")

    def _mod_degisti(self, mod):
        self._gorunurluk(mod)
        self._kaydet()

    def _kaydet(self, *_a):
        if self._yukleniyor:
            return
        h = dict(self.oge() or {})
        if self.mod.secili() == "dis":
            h.pop("kalinlik", None)
            h["dis"] = self.dis.kesit()
        else:
            h.pop("dis", None)
            h["kalinlik"] = self.kalinlik.deger()
        self.agac_yay(duzenle.yaz(self.agac, self.yol, h))
