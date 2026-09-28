# -*- coding: utf-8 -*-
"""
 arayuz/cubuk/plaka_formu.py  --  PlakaFormuMixin: secili plakanin formu

 arayuz/sekme_cubuk.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import sekme_cubuk; sekme_cubuk.X` aynen calisir.
"""

from cekirdek import sema
from arayuz.cubuk.parca_islemleri import eksik_malzemeler, rol_listesi
from arayuz.cubuk.malzeme_kutusu import MalzemeKutusu


class PlakaFormuMixin(object):
    """Secili plaka elemaninin formu."""

    # ------------------------------------------------------------------
    # plaka
    # ------------------------------------------------------------------
    def _plaka_kutusu(self, anahtar, kutu):
        yer = self._p_satir[anahtar]
        while yer.count():
            w = yer.takeAt(0).widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        yer.addWidget(kutu, 1)
        kutu.currentIndexChanged.connect(self._plaka_kaydet)
        return kutu

    def _plaka_doldur(self, p):
        if p is None:
            return
        self.p_ad.setText(p["ad"])
        self._hata_goster(self.p_ad_hata, "")
        self.p_sayi.setValue(p["plaka_sayisi"])
        self.p_et.setValue(p["et_kalinlik"])
        self.p_zarf.setValue(p["zarf_kalinlik"])
        self.p_kanal.setValue(p["kanal_kalinlik"])
        self.p_genislik.setValue(p["plaka_genislik"])
        self.p_yan.setValue(p.get("yan_levha_kalinlik") or 0.0)
        s = self.spec
        yapisal = rol_listesi(s, "yapisal")
        self.p_et_mal = self._plaka_kutusu("et_malzeme", MalzemeKutusu(
            s, p.get("et_malzeme"), rol_listesi(s, "yakit"), bos=False))
        self.p_zarf_mal = self._plaka_kutusu("zarf_malzeme", MalzemeKutusu(
            s, p.get("zarf_malzeme"), yapisal, bos=False))
        self.p_sog = self._plaka_kutusu("sogutucu", MalzemeKutusu(
            s, p.get("sogutucu"), rol_listesi(s, "sogutucu"), bos=False))
        self.p_yan_mal = self._plaka_kutusu("yan_levha_malzeme", MalzemeKutusu(
            s, p.get("yan_levha_malzeme"), yapisal, bos=False,
            yok_etiketi="Zarf ile aynı"))
        self._plaka_ozet(p)

    def _plaka_ozet(self, p):
        tx = p["plaka_sayisi"] * (2 * p["zarf_kalinlik"] + p["et_kalinlik"]) \
            + (p["plaka_sayisi"] + 1) * p["kanal_kalinlik"]
        ty = p["plaka_genislik"] + 2 * (p.get("yan_levha_kalinlik") or 0.0)
        self.p_ozet.setText("%.4f × %.4f cm" % (tx, ty))
        yan_var = float(p.get("yan_levha_kalinlik") or 0.0) > 0
        if self.p_yan_mal is not None:
            self.p_yan_mal.setEnabled(yan_var)
            self.p_yan_mal.setToolTip("" if yan_var else
                                      "Yan levha kalınlığı 0: yan levha kurulmaz.")
        self.e_yan_mal.setEnabled(yan_var)
        eksik = eksik_malzemeler(self.spec, p)
        self._hata_goster(self.p_eksik, (
            "Malzemesi seçilmemiş: %s. Uygun malzeme yoksa önce Malzemeler "
            "sekmesinden ekleyin." % ", ".join(eksik)) if eksik else "")

    def _plaka_kaydet(self, *_):
        if self._yukleniyor:
            return
        tur, ad = self._secili()
        if tur != "plaka":
            return
        p = sema.plaka_bul(self.spec, ad)
        p["plaka_sayisi"] = self.p_sayi.value()
        p["et_kalinlik"] = self.p_et.value()
        p["zarf_kalinlik"] = self.p_zarf.value()
        p["kanal_kalinlik"] = self.p_kanal.value()
        p["plaka_genislik"] = self.p_genislik.value()
        p["yan_levha_kalinlik"] = self.p_yan.value()
        p["et_malzeme"] = self.p_et_mal.currentData()
        p["zarf_malzeme"] = self.p_zarf_mal.currentData()
        p["sogutucu"] = self.p_sog.currentData()
        p["yan_levha_malzeme"] = self.p_yan_mal.currentData()
        self._plaka_ozet(p)
        self._liste_ogesini_yenile(p)
        self.bildir()
