# -*- coding: utf-8 -*-
"""
bagdastirici.py -- cekirdek.kuyruk.Kuyruk icin ince Qt bagdastiricisi (Y10).

Kuyruk dinleyicileri isci is parcaciginda cagrilir; bu QObject olaylari bir
sinyalle yayar. Bagdastirici ana iplikte yaratildigi icin baska iplikten
yayilan sinyal Qt tarafindan KUYRUKLU iletilir: yuvalar (tablo, sihirbaz)
her zaman ana iplikte calisir. Bir isin daha eski (kucuk IsDurumu.seq) olayi
yayilmaz: cekirdek zaten sirali yayar, bu ikinci bir guvencedir.

    kq = KuyrukBagdastirici(kuyruk.Kuyruk(en_fazla_paralel=1))
    kq.durum_degisti.connect(lambda d: ...)      # d: kuyruk.IsDurumu
    kq.hepsi_bitti.connect(...)                  # bekleyen/kosan kalmadi
    kq.kuyruk.ekle(...); kq.kuyruk.baslat()
"""

from __future__ import annotations

import threading
from typing import Dict, Optional

from PySide6 import QtCore

from cekirdek import kuyruk as _kuyruk


class KuyrukBagdastirici(QtCore.QObject):
    """Kuyruk olaylarini Qt sinyallerine cevirir (ana iplige kuyruklu)."""

    durum_degisti = QtCore.Signal(object)       # kuyruk.IsDurumu
    hepsi_bitti = QtCore.Signal()

    def __init__(self, cekirdek_kuyrugu: Optional[_kuyruk.Kuyruk] = None,
                 parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.kuyruk = cekirdek_kuyrugu or _kuyruk.Kuyruk()
        self._son_seq: Dict[str, int] = {}
        self._kilit = threading.Lock()
        self._bitti_yayildi = False       # hepsi_bitti yeni bir is gelene kadar bir kez
        # TEK bagli yontem nesnesi: Kuyruk.dinleyici_cikar 'is' ile karsilastirir;
        # her self._olay erisimi yeni bir nesne uretir ve hic cikarilamazdi.
        self._dinleyici = self._olay
        self.kuyruk.dinleyici_ekle(self._dinleyici)

    def _olay(self, durum: _kuyruk.IsDurumu) -> None:
        # isci ipliginde: eski olayi at, yalniz sinyal yay (Qt kuyruklu iletir)
        with self._kilit:
            if self._son_seq.get(durum.kimlik, -1) >= durum.seq:
                return
            self._son_seq[durum.kimlik] = durum.seq
            bitti = durum.bitti_mi and self.kuyruk.tamamlandi_mi() and not self._bitti_yayildi
            self._bitti_yayildi = bitti or (self._bitti_yayildi and durum.bitti_mi)
        self.durum_degisti.emit(durum)
        if bitti:
            self.hepsi_bitti.emit()

    def ayril(self) -> None:
        """Yalniz dinleyiciyi cikarir; kuyruk (paylasilan) calismayi surdurur.
        Bagdastirici silinmeden once cagrilir: aksi halde isci ipligi silinmis
        QObject'in sinyalini yaymaya calisir. Tekrar cagrilabilir."""
        self.kuyruk.dinleyici_cikar(self._dinleyici)

    def kapat(self) -> None:
        """Dinleyiciyi cikarir ve kuyrugu kapatir (pencere kapanirken)."""
        self.ayril()
        self.kuyruk.kapat()
