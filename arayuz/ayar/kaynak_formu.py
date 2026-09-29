# -*- coding: utf-8 -*-
"""
 arayuz/ayar/kaynak_formu.py  --  KaynakFormuMixin: kaynak enerji tayfi

 arayuz/sekme_ayar.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import sekme_ayar; sekme_ayar.X` aynen calisir.
"""

from PySide6 import QtWidgets
from cekirdek import kaynak as _kaynak
from arayuz import tema


class KaynakFormuMixin(object):
    """Baslangic / sabit kaynak: enerji tayfi alanlari."""

    def _tayfi_tasi(self, yer):
        """Tayf/aci kutusunu kaynak bolumu ile Gelismis arasinda tasir."""
        if self._tayf_yeri is yer:
            return
        if self._tayf_yeri is not None:
            self._tayf_yeri.removeWidget(self.tayf_kutu)
        yer.addWidget(self.tayf_kutu)
        self._tayf_yeri = yer

    # ------------------------------------------------------------------
    # kaynak tayfi
    # ------------------------------------------------------------------
    @staticmethod
    def _sayi_listesi(metin):
        cikti = []
        for parca in (metin or "").replace(";", ",").split(","):
            parca = parca.strip()
            if not parca:
                continue
            try:
                cikti.append(float(parca))
            except ValueError:
                pass
        return cikti

    def _tayf_oku(self):
        """Arayuzdeki SECILI tayfin alanlarini spec sozlugune yazar; diger
        tayflarin (gorunmeyen) alanlari dosyadaki gibi kalir."""
        e = dict((self.spec["ayarlar"].get("kaynak") or {}).get("enerji") or {})
        tur = self.tayf.currentData()
        e["tur"] = tur
        if tur == "watt":
            e["a"] = self.watt_a.deger()
            e["b"] = self.watt_b.value()
        elif tur == "maxwell":
            e["theta"] = self.maxwell_theta.deger()
        elif tur == "tek":
            e["enerji"] = self.tek_enerji.deger()
        elif tur == "ayrik":
            noktalar = []
            for parca in (self.ayrik_metin.text() or "").replace(";", ",").split(","):
                if ":" not in parca:
                    continue
                a_, b_ = parca.split(":", 1)
                try:
                    noktalar.append([float(a_), float(b_)])
                except ValueError:
                    pass
            e["noktalar"] = noktalar
        elif tur == "histogram":
            e["kenarlar"] = self._sayi_listesi(self.hist_kenar.text())
            e["degerler"] = self._sayi_listesi(self.hist_deger.text())
        elif tur == "fuzyon":
            e["e0"] = self.fuzyon_e0.deger()
            e["kutle_orani"] = self.fuzyon_kutle.value()
            e["iyon_sicaklik"] = self.fuzyon_kt.deger()
        return e

    def _tayf_gorunurluk(self):
        """Yalnizca secili tayfin alanlari gorunur; ozet satiri guncellenir."""
        self.tayf_yigin.setCurrentIndex(max(self.tayf.currentIndex(), 0))
        # Yigin en buyuk sayfanin yuksekligini ayirir (fuzyon: 3 satir); Watt
        # sayfasinin altinda bos alan kaliyordu. Yalnizca secili sayfa sayilir.
        for i in range(self.tayf_yigin.count()):
            sayfa = self.tayf_yigin.widget(i)
            pol = (QtWidgets.QSizePolicy.Preferred if i == self.tayf_yigin.currentIndex()
                   else QtWidgets.QSizePolicy.Ignored)
            sayfa.setSizePolicy(QtWidgets.QSizePolicy.Preferred, pol)
        self.tayf_yigin.updateGeometry()
        aci = self.aci_tur.currentData()
        self._tayf_form.setRowVisible(self.yon_satiri, aci != "izotropik")
        self._tayf_form.setRowVisible(self.koni_aci, aci == "koni")
        sabit = not self._ozdeger()
        e = self._tayf_oku()
        try:
            _kaynak.enerji_dagilimi(e)
            ort = _kaynak.ortalama_enerji(e)
            metin = ("Ortalama enerji: %s" % _kaynak.enerji_metni(ort)) if ort else ""
            if sabit:
                if self.kaynak_kuvvet.deger(1.0) == 1.0:
                    metin += "\nŞiddet 1 — sonuçlar kaynak parçacığı başına kalır."
                else:
                    metin += ("\nSonuçlar mutlak birimde olur (OpenMC şiddeti kendisi "
                              "uygular, ayrıca çarpmayın).")
            self.tayf_ozet.setText(metin.strip())
            self.tayf_ozet.setStyleSheet("")
        except Exception as hata:
            self.tayf_ozet.setText("Tayf kurulamadı: %s" % hata)
            self.tayf_ozet.setStyleSheet("color: %s;" % tema.renk("hata"))
