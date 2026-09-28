# -*- coding: utf-8 -*-
"""
 arayuz/ayar/guc_formu.py  --  GucFormuMixin: guc dagilimi alanlari

 arayuz/sekme_ayar.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import sekme_ayar; sekme_ayar.X` aynen calisir.
"""

from cekirdek import sema, uygunluk
from arayuz.ayar.sabitler import GUC_SKORLARI


class GucFormuMixin(object):
    """Cubuk bazli guc dagilimi alanlari."""

    def _guc_doldur(self):
        g = self.spec.get("guc_dagilimi") or {}
        self.guc_var.setChecked(bool(g.get("var")))
        cubuklar = uygunluk.guc_cubuklari(self.spec)
        self._kutu_doldur(self.guc_cubuk, [(c, c) for c in cubuklar], g.get("cubuk"),
                          " (fisil değil ya da demette değil)")
        self._guc_bolgeleri_doldur(g.get("bolge"))
        self._kutu_doldur(self.guc_skor, GUC_SKORLARI, g.get("skor") or "kappa-fission",
                          " (bilinmeyen)")
        self.guc_dilim.setValue(g.get("eksenel_dilim") or 20)
        self.guc_toplam.setValue(g.get("toplam_guc") or 0.0)

    def _guc_bolgeleri_doldur(self, secili=None):
        """Secili cubugun bolgeleri (1'den numarali, malzeme adiyla)."""
        eski = self.guc_bolge.blockSignals(True)
        try:
            self.guc_bolge.clear()
            ad = self.guc_cubuk.currentData()
            c = sema.cubuk_bul(self.spec, ad) if ad else None
            if c:
                for i, b in enumerate(c["bolgeler"]):
                    m_ad = b.get("malzeme")
                    etiket = "%d. bölge — %s" % (i + 1, m_ad if m_ad and m_ad != sema.BOSLUK
                                                   else "Boş (madde yok)")
                    if b.get("r"):
                        etiket += "  (r = %.4f cm)" % b["r"]
                    else:
                        etiket += "  (dış bölge)"
                    self.guc_bolge.addItem(etiket, i)
            if secili is not None:
                j = self.guc_bolge.findData(secili)
                if j >= 0:
                    self.guc_bolge.setCurrentIndex(j)
        finally:
            self.guc_bolge.blockSignals(eski)

    def _guc_gorunurluk(self):
        alan = self._alan()
        g = self.spec.get("guc_dagilimi") or {}
        # Uygun modelde gorunur; uygun olmayan modelde yalnizca dosyada acik
        # birakilmissa (kullanici kapatabilsin diye).
        gorunur = alan["guc_dagilimi"] or bool(g.get("var"))
        self.guc_kutu.setVisible(gorunur)
        acik = self.guc_var.isChecked()
        gf = self._guc_form
        for w in (self.guc_cubuk, self.guc_bolge, self.guc_skor, self.guc_dilim,
                  self.guc_toplam, self.guc_not):
            w.setEnabled(acik)
        for e in self.guc_etiketler.values():
            e.setEnabled(acik)
        gf.setRowVisible(self.guc_cubuk, acik)
        gf.setRowVisible(self.guc_dilim, acik and alan["eksenel_dilim"])
        gf.setRowVisible(self.guc_toplam, acik)
        self.guc_not.setVisible(acik)
        self.guc_gelismis.setVisible(acik)
        self.guc_dilim.setEnabled(acik and alan["eksenel_dilim"])
        self.guc_etiketler["dilim"].setEnabled(acik and alan["eksenel_dilim"])
        uyari = ""
        if acik and not alan["guc_dagilimi"]:
            uyari = ("Bu modelde güç dağılımı hesaplanamaz: demette tekrarlanan "
                     "fisil bir çubuk yok. Kutuyu kapatın.")
        self.guc_uyari.setText(uyari)
        self.guc_uyari.setVisible(bool(uyari))
        self.guc_var.setText("Çubuk bazlı güç dağılımı hesapla (F_ΔH%s)"
                             % (", F_q" if alan["eksenel_dilim"] else ""))

    def _guc_cubuk_degisti(self, *_):
        if self._yukleniyor:
            return
        self._guc_bolgeleri_doldur(0)
        self._kaydet()
