# -*- coding: utf-8 -*-
"""
isci.py -- Veri sayfasinin ARKA PLAN indirme iscisi (QThread).

Arayuz donmaz: ag ve arsiv acma bu is parcaciginda calisir; sonuc ve ilerleme
Qt sinyalleriyle (kuyruklu baglanti, ana is parcacigina) gelir. Iptal bir
threading.Event'tir: indirici her parcadan sonra bakar, yarim .part dosyasi
kalir ve ayni isin yeniden baslatilmasi kaldigi yerden SURDURUR.

Bayt sayilari 2^31'i asar (10 GB): sinyaller `object` tasir (Qt int 32 bit).
"""

import threading
from typing import Callable

from PySide6 import QtCore

from cekirdek import veri_indir
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)


class ArkaPlanIsi(QtCore.QThread):
    """Tek bir islevi arka planda calistirir (gereksinim denetimi, klasor
    denetimi: `openmc --version`, h5 okuma, binlerce isfile -- GUI donmasin).
    Sonuc `bitti(object)`, hata `basarisiz(str)` ile gelir."""

    bitti = QtCore.Signal(object)
    basarisiz = QtCore.Signal(str)

    def __init__(self, islev: Callable[[], object], parent=None):
        super().__init__(parent)
        self._islev = islev

    def run(self):                                       # noqa: D401 (QThread)
        try:
            sonuc = self._islev()
        except Exception as e:                           # noqa: BLE001 -- is parcacigi siniri
            _log.exception("arka plan veri denetimi basarisiz")
            self.basarisiz.emit(_("beklenmeyen hata: %s") % e)
            return
        self.bitti.emit(sonuc)


class IndirmeIscisi(QtCore.QThread):
    """isler: [(Oge, ...)] sirayla kurulur (once zincirler, sonra kutuphane)."""

    ilerleme = QtCore.Signal(str, str, object, object)   # asama, oge adi, alinan, toplam
    oge_bitti = QtCore.Signal(object)                    # (Oge, Kurulum)
    basarili = QtCore.Signal(object)                     # [(Oge, Kurulum)]
    basarisiz = QtCore.Signal(str)                       # kullaniciya gosterilecek metin
    iptal_edildi = QtCore.Signal()

    def __init__(self, isler, hedef, oran, politika=None, parent=None):
        super().__init__(parent)
        self._isler = tuple(isler)
        self._hedef = hedef
        self._oran = oran
        self._politika = politika           # None -> uretim (https + katalog)
        self._iptal = threading.Event()

    def iptal_et(self):
        self._iptal.set()

    def _kur(self, oge):
        ilerle = lambda asama, a, t: self.ilerleme.emit(asama, oge.gorunen_ad(), a, t)  # noqa: E731
        if oge.tur == "zincir":
            return veri_indir.zincir_kur(oge, self._hedef, politika=self._politika,
                                         ilerleme=ilerle, iptal=self._iptal)
        return veri_indir.kutuphane_kur(oge, self._hedef, self._oran, politika=self._politika,
                                        ilerleme=ilerle, iptal=self._iptal)

    def run(self):                                       # noqa: D401 (QThread)
        sonuclar = []
        try:
            for oge in self._isler:
                kurulum = self._kur(oge)
                sonuclar.append((oge, kurulum))
                self.oge_bitti.emit((oge, kurulum))
        except veri_indir.IptalEdildi:
            _log.info("veri indirme iptal edildi (%d/%d tamam)", len(sonuclar), len(self._isler))
            self.iptal_edildi.emit()
            return
        except veri_indir.VeriHatasi as e:
            _log.warning("veri indirme basarisiz: %s", e)
            self.basarisiz.emit(str(e))
            return
        except Exception as e:                           # noqa: BLE001 -- is parcacigi siniri
            _log.exception("veri indirmede beklenmeyen hata")
            self.basarisiz.emit(_("beklenmeyen hata: %s") % e)
            return
        self.basarili.emit(sonuclar)
