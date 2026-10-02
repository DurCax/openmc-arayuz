# -*- coding: utf-8 -*-
"""
================================================================================
 guc_harita_secim.py  --  Guc haritasi: pin tablosu kurulumu, tikla -> pin, secim isareti
================================================================================
 GucHaritaWidget'in (arayuz/guc_harita.py) karisimi (v3 K3). Cizim islevleri
 her cizilen cubugu _tik_ogeleri'ne [(x, y, yaricap, anahtar)] yazar; burada
 tiklanan noktanin cubugu bulunur, tablo satiri secilir ve haritada kare
 isaret cizilir. Tablo haritanin AYNI degerlerinden kurulur (cekirdek/guc_tablo).
================================================================================
"""

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from arayuz import tema

_log = kaydedici(__name__)
_TIK_PAYI = 1.05     # tiklama: eleman yaricapinin bu kati icinde (ipucu_metni ile ayni)


class PinSecimi:
    """Karisim: GucHaritaWidget nitelikleri (pin_tablosu, tuval, arac, _tik_ogeleri,
    _ana_eksen, secili_pin, secim_isareti, dagilim, faktorler, mutlak) kullanilir."""

    def _tablo_kur(self, spec, yukseklik):
        """Pin tablosu haritanin AYNI degerlerinden (cekirdek/guc_tablo)."""
        from cekirdek import guc_tablo
        self.secili_pin = None
        try:
            self.tablo = guc_tablo.pin_tablosu(self.dagilim, self.faktorler, self.mutlak,
                                               yukseklik)
            notlar = (guc_tablo.yorum_notlari(self.dagilim, self.faktorler,
                                              getattr(self, "hedef_payi", None), spec)
                      if self.tablo else [])
        except Exception as e:
            _log.exception("pin gücü tablosu kurulamadı")
            self.tablo = []
            self.pin_tablosu.ayarla([])
            self.pin_tablosu.ayrinti.setText(_("Pin gücü tablosu kurulamadı: %s") % e)
            return
        self.pin_tablosu.ayarla(self.tablo, self.dagilim, spec, notlar=notlar)

    def _tiklandi(self, olay):
        if olay.inaxes is not self._ana_eksen or olay.xdata is None:
            return
        if getattr(self.arac, "mode", ""):
            return                      # yakinlastirma/kaydirma kipinde tiklama secim degil
        self.haritada_tikla(olay.xdata, olay.ydata)

    def haritada_tikla(self, x, y):
        """(x, y) haritanin veri koordinati. Bir cubuga dustuyse onu secer
        (tablo ve ayrinti satiri izler). DONER secilen anahtar ya da None."""
        import numpy as np
        if not self._tik_ogeleri:
            return None
        dizi = np.asarray([o[:3] for o in self._tik_ogeleri], dtype=float)
        uzak = np.hypot(dizi[:, 0] - x, dizi[:, 1] - y)
        i = int(np.argmin(uzak))
        if uzak[i] > dizi[i, 2] * _TIK_PAYI:
            return None
        anahtar = self._tik_ogeleri[i][3]
        if not self.pin_tablosu.sec(anahtar):
            self._pin_secildi(anahtar)      # tabloda yok (tur suzgeci): yine isaretle
        return anahtar

    def _pin_secildi(self, anahtar):
        self.secili_pin = anahtar
        self._secimi_ciz()
        self.tuval.draw_idle()

    def _secimi_ciz(self):
        """Secili pin kare isaretle (sicak pin halkasindan ayri renk)."""
        if self.secim_isareti is not None:
            try:
                self.secim_isareti.remove()
            except (ValueError, NotImplementedError):
                _log.debug("eski seçim işareti kaldırılamadı (eksen temizlenmiş)")
            self.secim_isareti = None
        if self.secili_pin is None or self._ana_eksen is None:
            return
        for x, y, r, a in self._tik_ogeleri:
            if a == self.secili_pin:
                self.secim_isareti = self._ana_eksen.plot(
                    x, y, marker="s", ms=12, mfc="none", mec=tema.renk("bilgi"), mew=2.0,
                    zorder=6)[0]
                return
