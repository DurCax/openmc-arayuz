# -*- coding: utf-8 -*-
"""
 arayuz/ayar/guc_formu.py  --  GucFormuMixin: guc dagilimi alanlari

 arayuz/sekme_ayar.py'den bolundu. Eski yol `from arayuz import sekme_ayar;
 sekme_ayar.X` aynen calisir.

 COK TURLU HEDEF (Dalga 2, guc_dagilimi.cubuklar)
   Hedef cubuk kutusunda uygun her cubuk ayri bir ogedir; modelde birden cok
   uygun cubuk varsa en uste "Tüm yakıt çubukları" (sema.GUC_TUM) eklenir.
   Dosyadaki liste bunlarin hicbirine uymuyorsa "Dosyadaki seçim"
   (sema.GUC_LISTE) ogesi listeyi aynen korur.
   Kaydetme AyarSekmesi._kaydet'tedir (eski tek alan "cubuk"/"bolge" yazar);
   _kaydet sonunda cagrilan _guc_gorunurluk -> _guc_listesini_esle bu secimi
   "cubuklar" listesine cevirir. Eski alanlar bellekte kalir (sema.guc_hedefleri
   onlari taze niyet sayar); sema.kaydet dosyaya yalniz yeni bicimi yazar.
"""

from cekirdek import guc, sema, uygunluk
from cekirdek.ceviri import _
from arayuz.ayar.sabitler import GUC_SKORLARI


class GucFormuMixin(object):
    """Cubuk bazli guc dagilimi alanlari."""

    def _guc_hedef_ogeleri(self):
        """(ogeler [(veri, etiket)], secili veri) -- hedef cubuk kutusu icin."""
        cubuklar = uygunluk.guc_cubuklari(self.spec)
        ogeler = [(c, c) for c in cubuklar]
        g = self.spec.get("guc_dagilimi") or {}
        hedefler = sema.guc_hedefleri(g)
        tum = guc.varsayilan_hedefler(self.spec)
        if len(cubuklar) > 1:
            ogeler.insert(0, (sema.GUC_TUM, _("Tüm yakıt çubukları (%d tür)") % len(cubuklar)))
        if len(hedefler) > 1:
            if hedefler == tum:
                return ogeler, sema.GUC_TUM
            adlar = ", ".join(h["cubuk"] or "?" for h in hedefler)
            ogeler.append((sema.GUC_LISTE, _("Dosyadaki seçim: %s") % adlar))
            return ogeler, sema.GUC_LISTE
        if hedefler:
            return ogeler, hedefler[0]["cubuk"]
        return ogeler, (sema.GUC_TUM if len(cubuklar) > 1 else None)

    def _guc_doldur(self):
        g = self.spec.get("guc_dagilimi") or {}
        self.guc_var.setChecked(bool(g.get("var")))
        ogeler, secili = self._guc_hedef_ogeleri()
        self._kutu_doldur(self.guc_cubuk, ogeler, secili,
                          " (fisil değil ya da demette değil)")
        hedefler = sema.guc_hedefleri(g)
        self._guc_bolgeleri_doldur(hedefler[0]["bolge"] if len(hedefler) == 1 else None)
        self._kutu_doldur(self.guc_skor, GUC_SKORLARI, g.get("skor") or "kappa-fission",
                          " (bilinmeyen)")
        self.guc_dilim.setValue(g.get("eksenel_dilim") or 20)
        self.guc_toplam.setValue(g.get("toplam_guc") or 0.0)

    def _guc_bolgeleri_doldur(self, secili=None):
        """Secili cubugun bolgeleri (1'den numarali, malzeme adiyla). Cok turlu
        secimde (Tüm / Dosyadaki) bolge tur basina fisil bolgedir: kutu bos."""
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

    def _guc_listesini_esle(self):
        """
        AyarSekmesi._kaydet'in yazdigi tek secimi (eski "cubuk"/"bolge")
        "cubuklar" listesine cevirir (_kaydet kalibi: self.spec yerinde).
          - ozel secim (Tüm / Dosyadaki): liste kurulur/korunur, eski alanlar
            silinir;
          - secim listeyle AYNI: eski alanlar silinir (degisikliksiz kayit
            spec'i degistirmez);
          - secim DEGISTI: liste guncellenir, eski alanlar bellekte kalir
            (henuz "cubuklar"a gecmemis okuyucular icin; sema.kaydet yazmaz).
        """
        g = (self.spec or {}).get("guc_dagilimi")
        if not isinstance(g, dict) or "cubuk" not in g:
            return
        ad = g["cubuk"]
        if ad in (sema.GUC_TUM, sema.GUC_LISTE):
            if ad == sema.GUC_TUM:
                g["cubuklar"] = guc.varsayilan_hedefler(self.spec)
            g.pop("cubuk")
            g.pop("bolge", None)
            return
        secim = sema.guc_hedefleri(g)
        if secim == sema.guc_hedefleri({"cubuklar": g.get("cubuklar")}):
            g.pop("cubuk")
            g.pop("bolge", None)
        else:
            g["cubuklar"] = secim

    def _guc_gorunurluk(self):
        self._guc_listesini_esle()
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
        self.guc_bolge.setEnabled(acik and self.guc_bolge.count() > 0)
        uyari = ""
        if acik and not alan["guc_dagilimi"]:
            uyari = ("Bu modelde güç dağılımı hesaplanamaz: demette tekrarlanan "
                     "fisil bir çubuk yok. Kutuyu kapatın.")
        self.guc_uyari.setText(uyari)
        self.guc_uyari.setVisible(bool(uyari))
        self.guc_var.setText("Çubuk bazlı güç dağılımı hesapla (F_ΔH%s)"
                             % (", F_q" if alan["eksenel_dilim"] else ""))

    def _guc_cubuk_degisti(self, *_a):
        if self._yukleniyor:
            return
        ad = self.guc_cubuk.currentData()
        c = sema.cubuk_bul(self.spec, ad) if ad else None
        self._guc_bolgeleri_doldur(guc._fisil_bolge(self.spec, c) if c else None)
        self._kaydet()
