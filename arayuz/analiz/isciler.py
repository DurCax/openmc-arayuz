# -*- coding: utf-8 -*-
"""
isciler.py -- Tarama ve kritik aramayi arka planda yuruten QThread'ler.
Sonuclar sinyallerle arayuze gelir; arayuz donmaz ve is durdurulabilir.
"""

from PySide6 import QtCore

from cekirdek import kritik_arama, tarama
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)


class TaramaIsci(QtCore.QThread):
    """Taramayi arka planda yurutur."""

    nokta = QtCore.Signal(int, int, dict)
    bitti = QtCore.Signal(list, list)
    hata = QtCore.Signal(str)

    def __init__(self, spec, tur, hedef, degerler, dizin, is_parcacigi, parent=None):
        super().__init__(parent)
        self.spec, self.tur, self.hedef = spec, tur, hedef
        self.degerler, self.dizin, self.is_parcacigi = degerler, dizin, is_parcacigi
        self._dur = False

    def durdur(self):
        self._dur = True

    def run(self):
        try:
            sonuclar, notlar = tarama.calistir(
                self.spec, self.tur, self.hedef, self.degerler, self.dizin,
                geri_cagir=lambda i, n, s: self.nokta.emit(i, n, s),
                is_parcacigi=self.is_parcacigi,
                dur_bayragi=lambda: self._dur)
            self.bitti.emit(sonuclar, notlar)
        except Exception as e:
            _log.exception("parametre taramasi basarisiz (%s)", self.tur)
            self.hata.emit(str(e))


class AramaIsci(QtCore.QThread):
    """Kritik aramayi arka planda yurutur."""

    adim = QtCore.Signal(int, dict)
    bitti = QtCore.Signal(object)
    hata = QtCore.Signal(str)

    def __init__(self, spec, tur, hedef, alt, ust, hedef_keff, dizin,
                 is_parcacigi, parent=None):
        super().__init__(parent)
        self.spec, self.tur, self.hedef = spec, tur, hedef
        self.alt, self.ust, self.hedef_keff = alt, ust, hedef_keff
        self.dizin, self.is_parcacigi = dizin, is_parcacigi
        self._dur = False

    def durdur(self):
        self._dur = True

    def run(self):
        try:
            s = kritik_arama.ara(
                self.spec, self.tur, self.hedef, self.alt, self.ust, self.dizin,
                hedef_keff=self.hedef_keff, is_parcacigi=self.is_parcacigi,
                geri_cagir=lambda i, k: self.adim.emit(i, k),
                dur_bayragi=lambda: self._dur)
            self.bitti.emit(s)
        except Exception as e:
            _log.exception("kritik arama basarisiz (%s)", self.tur)
            self.hata.emit(str(e))
