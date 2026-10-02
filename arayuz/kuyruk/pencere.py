# -*- coding: utf-8 -*-
"""
pencere.py -- "Is akisi" penceresi (Y10): Kuyruk | Gecmis ve karsilastirma | SLURM.

    from arayuz.kuyruk import pencere
    p = pencere.ac(ebeveyn, spec)        # tekil pencere; spec: gecerli model (dict)
    p.spec_ayarla(spec)                  # model degisince

Ana pencereye baglanti (menu eylemi) orkestratorun isidir (arayuz/pencere/
menuler.py Y10'un sahipliginde degil): `pencere.ac(self, self.spec)`.
Bagimsiz: `python -m arayuz.kuyruk [model.json]`.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from PySide6 import QtCore, QtWidgets

from cekirdek import kosu_gecmisi
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from arayuz.karsilastir.panel import KarsilastirmaPaneli
from arayuz.kuyruk.panel import KuyrukPaneli
from arayuz.kuyruk.slurm_paneli import SlurmPaneli

_log = kaydedici(__name__)
_BOYUT = (1100, 760)          # ilk acilis boyutu (piksel)
_TEKIL: dict = {}


class IsAkisiPenceresi(QtWidgets.QWidget):
    """Kuyruk, gecmis/karsilastirma ve SLURM sekmeleri."""

    def __init__(self, spec: Optional[Mapping[str, Any]] = None,
                 gecmis: Optional[kosu_gecmisi.GecmisDeposu] = None,
                 parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(_("İş akışı — kuyruk, geçmiş, SLURM"))
        self.resize(*_BOYUT)
        if gecmis is None:
            gecmis = self._gecmis_ac()
        self.kuyruk = KuyrukPaneli(self, gecmis=gecmis)
        self.karsilastir = KarsilastirmaPaneli(gecmis, self)
        self.slurm = SlurmPaneli(self)
        self.kuyruk.gecmis_degisti.connect(self.karsilastir.yenile)
        self.sekmeler = QtWidgets.QTabWidget(self)
        self.sekmeler.addTab(self.kuyruk, _("Koşu kuyruğu"))
        self.sekmeler.addTab(self.karsilastir, _("Geçmiş ve karşılaştırma"))
        self.sekmeler.addTab(self.slurm, _("SLURM betiği"))
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.addWidget(self.sekmeler)
        self.spec_ayarla(spec)

    @staticmethod
    def _gecmis_ac() -> Optional[kosu_gecmisi.GecmisDeposu]:
        try:
            return kosu_gecmisi.GecmisDeposu()
        except Exception:
            # gecmis yazilamazsa kuyruk yine calisir; durum loga
            _log.exception("kosu gecmisi acilamadi; gecmis kaydedilmeyecek")
            return None

    def spec_ayarla(self, spec: Optional[Mapping[str, Any]]) -> None:
        self.kuyruk.spec_ayarla(spec)
        self.slurm.spec_ayarla(spec)

    def closeEvent(self, olay: Any) -> None:
        kosan = [d for d in self.kuyruk.kq.kuyruk.durumlar() if not d.bitti_mi]
        if kosan and QtWidgets.QMessageBox.question(
                self, _("İş akışı"),
                _("Kuyrukta %d bitmemiş koşu var; kapatılırsa iptal edilir. Kapatılsın mı?")
                % len(kosan)) != QtWidgets.QMessageBox.Yes:
            olay.ignore()
            return
        self.kuyruk.kapat()
        _TEKIL.pop("pencere", None)
        super().closeEvent(olay)


def ac(ebeveyn: Optional[QtWidgets.QWidget] = None,
       spec: Optional[Mapping[str, Any]] = None) -> IsAkisiPenceresi:
    """Tekil is akisi penceresini acar (varsa one getirir ve modeli gunceller)."""
    p = _TEKIL.get("pencere")
    if p is None:
        p = IsAkisiPenceresi(spec, parent=ebeveyn)
        p.setWindowFlag(QtCore.Qt.Window, True)        # ebeveynli ama ayri pencere
        _TEKIL["pencere"] = p
    else:
        p.spec_ayarla(spec)
    p.show()
    p.raise_()
    p.activateWindow()
    return p
