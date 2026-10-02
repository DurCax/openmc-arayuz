# -*- coding: utf-8 -*-
"""
bagdastirici.py -- cekirdek.kuyruk.Kuyruk icin ince Qt bagdastiricisi (Y10).

Kuyruk dinleyicileri isci is parcaciginda cagrilir; bu QObject olaylari bir
sinyalle yayar. Bagdastirici ana iplikte yaratildigi icin baska iplikten
yayilan sinyal Qt tarafindan KUYRUKLU iletilir: yuvalar (tablo, sihirbaz)
her zaman ana iplikte calisir.

    kq = KuyrukBagdastirici(kuyruk.Kuyruk(en_fazla_paralel=1))
    kq.durum_degisti.connect(lambda d: ...)      # d: kuyruk.IsDurumu
    kq.hepsi_bitti.connect(...)                  # bekleyen/kosan kalmadi
    kq.kuyruk.ekle(...); kq.kuyruk.baslat()
"""

from __future__ import annotations

from typing import Optional

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
        self.kuyruk.dinleyici_ekle(self._olay)

    def _olay(self, durum: _kuyruk.IsDurumu) -> None:
        # isci ipliginde: yalniz sinyal yay (Qt kuyruklu iletir)
        self.durum_degisti.emit(durum)
        if durum.bitti_mi and self.kuyruk.tamamlandi_mi():
            self.hepsi_bitti.emit()

    def kapat(self) -> None:
        """Dinleyiciyi cikarir ve kuyrugu kapatir (pencere kapanirken)."""
        self.kuyruk.dinleyici_cikar(self._olay)
        self.kuyruk.kapat()
