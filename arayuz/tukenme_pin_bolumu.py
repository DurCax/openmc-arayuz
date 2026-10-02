# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_pin_bolumu.py  --  Tukenme sonuc bolumunun "yanmaya gore pin gucu" kismi
================================================================================
 SonucBolumu'nun (arayuz/tukenme_sonuc.py) karisimi. Sonuc gosterilince
 (onceki ya da yeni kosu) ayni dizindeki adim statepoint'leri arka planda
 okunur (cekirdek/tukenme_guc.adim_gucleri) ve sonuc kartinin altinda
 arayuz/tukenme_pin_gucu.PinGucuYanma gosterilir; adim dosyasi yoksa gizli.

 IS PARCACIKLARI (kapanista hicbiri calisir halde yok edilmez)
   Her okuma bir _PinIsci'dir; calisanlar _pin_iscileri listesinde tutulur.
   isleri_durdur() (QApplication.aboutToQuit'e TukenmeSekmesi.__init__'te
   baglanir): hepsine requestInterruption(); adim_gucleri adimlar arasinda
   iptal denetler (tukenme_guc.Iptal) -- sonra wait(). Yeni okuma eskiyi de
   iptal eder; eski okumanin sonucu imza tutmadigi icin atilir.
 ANAHTAR: (proje kusagi, tukenme_guc.imza) -- adim dosyalari degisince yeniden okunur.
================================================================================
"""

import copy
import os

from PySide6 import QtCore

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)
BEKLEME_MS = 30000          # kapanista bir iscinin en cok beklenmesi [ms]


class _PinIsci(QtCore.QThread):
    """adim_gucleri'ni arka planda okur; iptal edilebilir. Basari ve hata ayri sinyal."""
    bitti = QtCore.Signal(object, object)      # (anahtar, sonuc | None)
    hata = QtCore.Signal(object, str)          # (anahtar, metin)

    def __init__(self, islev, anahtar, parent=None):
        super().__init__(parent)
        self._islev = islev
        self._anahtar = anahtar

    def run(self):
        from cekirdek import tukenme_guc
        try:
            sonuc = self._islev(self.isInterruptionRequested)
        except tukenme_guc.Iptal:
            _log.debug("adım başına pin gücü okuması iptal edildi")
            return
        except Exception as e:
            _log.exception("adım başına pin gücü okunamadı")
            self.hata.emit(self._anahtar, str(e))
            return
        self.bitti.emit(self._anahtar, sonuc)


class PinGucuBolumu:
    """Karisim: pin gucu bolumunun kurulumu, okunmasi ve kapanis."""

    def _pin_gucu_bolumu(self):
        """PinGucuYanma bolumu (ilk gerektiginde kurulur, sonuc kartina eklenir)."""
        w = getattr(self, "pin_gucu", None)
        if w is None:
            from arayuz.tukenme_pin_gucu import PinGucuYanma
            w = self.pin_gucu = PinGucuYanma()
            w.setVisible(False)
            self.sonuc_kutusu.ekle(w)
        return w

    def _pin_gucu_unut(self):
        w = getattr(self, "pin_gucu", None)
        self._pin_anahtari = None
        if w is not None:
            w.ayarla(None)
            w.setVisible(False)

    def _pin_iscileri_temizle(self):
        """Biten iscileri listeden cikarir (calisanlar kalir)."""
        self._pin_iscileri = [i for i in getattr(self, "_pin_iscileri", []) if i.isRunning()]
        return self._pin_iscileri

    def _pin_gucu_yukle(self, kaynak):
        """Sonucun dizinindeki adim basina gucu arka planda okur."""
        from cekirdek import tukenme_guc as _tg
        h5, spec = kaynak
        dizin = os.path.dirname(h5)
        if not _tg.adim_dosyalari(dizin) or not os.path.exists(h5):
            self._pin_gucu_unut()
            return
        try:
            anahtar = (self._kusak, _tg.imza(dizin, h5, spec))
        except OSError:
            _log.warning("adım dosyalarının imzası okunamadı: %s", dizin, exc_info=True)
            self._pin_gucu_unut()
            return
        if anahtar == getattr(self, "_pin_anahtari", None):
            return
        self._pin_anahtari = anahtar
        spec = copy.deepcopy(spec)
        for eski in self._pin_iscileri_temizle():
            eski.requestInterruption()
        isci = _PinIsci(lambda iptal: _tg.adim_gucleri(dizin, spec, h5, iptal=iptal),
                        (anahtar, spec), self)
        isci.bitti.connect(self._pin_gucu_geldi)
        isci.hata.connect(self._pin_gucu_hatasi)
        self._pin_iscileri.append(isci)
        isci.start()

    def _pin_guncel_mi(self, anahtar):
        if not self.canli_mi():
            _log.debug("tükenme sekmesi silindi; pin gücü yok sayıldı")
            return False
        kimlik = anahtar[0]
        return kimlik == getattr(self, "_pin_anahtari", None) and kimlik[0] == self._kusak

    def _pin_gucu_geldi(self, anahtar, sonuc):
        if not self._pin_guncel_mi(anahtar):
            return
        w = self._pin_gucu_bolumu()
        w.ayarla(sonuc, anahtar[1])
        w.setVisible(w.gosterilecek_mi())
        self._pin_eskime_yaz()

    def _pin_gucu_hatasi(self, anahtar, metin):
        if not self._pin_guncel_mi(anahtar):
            return
        w = self._pin_gucu_bolumu()
        w.ayarla({"adimlar": [], "notlar": [_("Adım başına güç okunamadı: %s") % metin]},
                 anahtar[1])
        w.setVisible(True)

    def _pin_eskime_yaz(self):
        """Gosterilen tukenme sonucu eskiyse pin gucu bolumu de "eski" etiketlenir."""
        w = getattr(self, "pin_gucu", None)
        if w is None or not getattr(self, "_onceki", None):
            return
        from cekirdek import tukenme as _tk
        durum, _farklar = _tk.eskime(self.spec, os.path.dirname(self._onceki["h5"]))
        w.eski_ayarla(durum == "eski")

    def pin_iscilerini_bekle(self, ms=BEKLEME_MS):
        for isci in list(getattr(self, "_pin_iscileri", [])):
            isci.wait(ms)
        self._pin_iscileri_temizle()

    def isleri_durdur(self):
        """Kapanis: pin okumalarini iptal eder, butun iscileri bekler."""
        for isci in getattr(self, "_pin_iscileri", []):
            isci.requestInterruption()
        self.pin_iscilerini_bekle()
        for isci in (getattr(self, "_isci", None), getattr(self, "_secim_isci", None)):
            if isci is not None:
                isci.wait(BEKLEME_MS)
