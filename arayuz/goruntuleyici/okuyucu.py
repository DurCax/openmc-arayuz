# -*- coding: utf-8 -*-
"""
 okuyucu.py  --  Statepoint mesh tally okumasi ana is parcacigi DISINDA (QThread)

 mt.oku statepoint'i h5py ile acar ve her mesh tally'sini yeniden bicimler; buyuk
 statepoint'te yuzlerce ms surebilir (arayuz donmasin: plan Dalga H, 200 ms).
"""

from PySide6 import QtCore

from cekirdek import mesh_tally as mt
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)


class TallyOkuyucu(QtCore.QThread):
    """bitti(yol, sonuclar, atlanan, hata metni) -- hata yoksa bos metin."""

    bitti = QtCore.Signal(str, object, object, str)

    def __init__(self, yol: str, parent=None):
        super().__init__(parent)
        self.yol = yol

    def run(self):                                   # noqa: D401 (QThread API)
        try:
            sonuclar, atlanan = mt.oku(self.yol)
        except Exception as e:  # noqa: BLE001 -- is parcacigi siniri: hata sinyalle gider
            _log.warning("statepoint mesh tally'leri okunamadı: %s", self.yol, exc_info=True)
            self.bitti.emit(self.yol, [], [], str(e))
            return
        self.bitti.emit(self.yol, sonuclar, atlanan, "")
