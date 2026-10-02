# -*- coding: utf-8 -*-
"""
slurm_paneli.py -- SLURM is betigi formu (Y10).

Form alanlari cekirdek.slurm.SlurmAyari'ya donusur; gecersiz alan (yeni satir,
bosluk, kabuk karakteri) cekirdekte reddedilir ve hata burada gosterilir.
Onizleme `bash -n` ile denetlenir. "Kosu klasorunu hazirla…" gecerli modelin
model.xml / spec.json'unu ve is.sh'yi secilen klasore yazar; betik bu
makinede calistirilmaz (kumede `sbatch is.sh`).
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Mapping, Optional

from PySide6 import QtCore, QtWidgets

from cekirdek import slurm
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from arayuz import tema
from arayuz.tasarim import tokenlar, yazi

_log = kaydedici(__name__)
A = tokenlar.ARALIK
_EN_COK_GOREV = 100000         # spin kutusu ust siniri (kume boyu)
_EN_COK_CPU = 512
_EN_COK_DUGUM = 10000
ONIZLEME_GECIKMESI = 300     # ms; yazarken onizleme gecikmesi (debounce)


class SlurmPaneli(QtWidgets.QWidget):
    """SLURM betigi formu + onizleme + kaydetme."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.spec: Optional[Dict[str, Any]] = None
        # her tusta `bash -n` alt sureci ana iplikte kosmasin: son degisiklikten
        # ONIZLEME_GECIKMESI ms sonra bir kez
        self._zamanlayici = QtCore.QTimer(self)
        self._zamanlayici.setSingleShot(True)
        self._zamanlayici.setInterval(ONIZLEME_GECIKMESI)
        self._zamanlayici.timeout.connect(self.onizle)
        self._kur()
        self.onizle()

    def _kur(self) -> None:
        duzen = QtWidgets.QHBoxLayout(self)
        duzen.setContentsMargins(A["l"], A["l"], A["l"], A["l"])
        duzen.setSpacing(A["l"])
        duzen.addWidget(self._form_kur(), 1)
        duzen.addLayout(self._onizleme_kur(), 2)

    def _alanlari_kur(self, kutu: QtWidgets.QWidget) -> tuple:
        self.is_adi = QtWidgets.QLineEdit("openmc", kutu)
        self.sure = QtWidgets.QLineEdit("01:00:00", kutu)
        self.dugum = self._spin(1, _EN_COK_DUGUM, 1)
        self.gorev = self._spin(1, _EN_COK_GOREV, 1)
        self.cpu = self._spin(1, _EN_COK_CPU, 8)
        self.bolum, self.hesap, self.bellek, self.eposta = (
            QtWidgets.QLineEdit(kutu) for _i in range(4))
        self.moduller = QtWidgets.QLineEdit(kutu)
        self.moduller.setPlaceholderText(_("birden çok modül: openmpi/4.1 hdf5"))
        self.conda = QtWidgets.QLineEdit(kutu)
        self.openmc = QtWidgets.QLineEdit("openmc", kutu)
        self.veri = QtWidgets.QLineEdit(kutu)
        self.veri.setPlaceholderText(_("kümedeki cross_sections.xml yolu (isteğe bağlı)"))
        self.baslatici = QtWidgets.QComboBox(kutu)
        for b in slurm.MPI_BASLATICILARI:
            self.baslatici.addItem(b, b)
        return ((_("İş adı"), self.is_adi), (_("Süre (ss:dd:sn)"), self.sure),
                (_("Düğüm"), self.dugum), (_("MPI görev (ntasks)"), self.gorev),
                (_("Görev başına CPU (OMP)"), self.cpu), (_("Bölüm (partition)"), self.bolum),
                (_("Hesap (account)"), self.hesap), (_("Bellek (ör. 16G)"), self.bellek),
                (_("E-posta"), self.eposta), (_("Modüller"), self.moduller),
                (_("Conda ortamı"), self.conda), (_("openmc yolu"), self.openmc),
                (_("OPENMC_CROSS_SECTIONS"), self.veri), (_("MPI başlatıcı"), self.baslatici))

    def _form_kur(self) -> QtWidgets.QWidget:
        kutu = QtWidgets.QWidget(self)
        form = QtWidgets.QFormLayout(kutu)
        for etiket, alan in self._alanlari_kur(kutu):
            form.addRow(etiket, alan)
            sinyal = getattr(alan, "textChanged", None) or getattr(alan, "valueChanged", None) \
                or alan.currentIndexChanged
            sinyal.connect(self._zamanlayici.start)
        self.d_kaydet = QtWidgets.QPushButton(_("Koşu klasörünü hazırla…"), kutu)
        self.d_kaydet.clicked.connect(self._kaydet)
        form.addRow("", self.d_kaydet)
        return kutu

    def _onizleme_kur(self) -> QtWidgets.QVBoxLayout:
        sag = QtWidgets.QVBoxLayout()
        self.durum = QtWidgets.QLabel("", self)
        self.durum.setWordWrap(True)
        sag.addWidget(self.durum)
        self.onizleme = QtWidgets.QPlainTextEdit(self)
        self.onizleme.setReadOnly(True)
        self.onizleme.setFont(yazi.font("mono"))
        sag.addWidget(self.onizleme, 1)
        return sag

    def _spin(self, alt: int, ust: int, deger: int) -> QtWidgets.QSpinBox:
        s = QtWidgets.QSpinBox(self)
        s.setRange(alt, ust)
        s.setValue(deger)
        return s

    def spec_ayarla(self, spec: Optional[Mapping[str, Any]]) -> None:
        self.spec = dict(spec) if spec else None
        if spec and spec.get("ad"):
            self.is_adi.setText(re.sub(r"[^A-Za-z0-9_.-]+", "_", str(spec["ad"]))[:64] or "openmc")
        self.onizle()

    def _bos_none(self, alan: QtWidgets.QLineEdit) -> Optional[str]:
        metin = alan.text().strip()
        return metin or None

    def ayar(self) -> slurm.SlurmAyari:
        """Formdan SlurmAyari (gecersizse ValueError)."""
        ek = {"OPENMC_CROSS_SECTIONS": self.veri.text().strip()} if self.veri.text().strip() else {}
        return slurm.SlurmAyari(
            is_adi=self.is_adi.text().strip(), sure=self.sure.text().strip(),
            dugum=self.dugum.value(), gorev=self.gorev.value(), cpu_gorev=self.cpu.value(),
            bolum=self._bos_none(self.bolum), hesap=self._bos_none(self.hesap),
            bellek=self._bos_none(self.bellek), eposta=self._bos_none(self.eposta),
            moduller=tuple(self.moduller.text().split()), conda_ortami=self._bos_none(self.conda),
            ek_ortam=ek, openmc=self.openmc.text().strip(),
            mpi_baslatici=self.baslatici.currentData())

    def _durum_yaz(self, metin: str, tur: str) -> None:
        self.durum.setText(metin)
        self.durum.setStyleSheet("color: %s;" % tema.renk(tur))

    def onizle(self, *_a: Any) -> Optional[str]:
        try:
            metin = slurm.betik_uret(self.ayar())
        except ValueError as e:
            self._durum_yaz(_("Geçersiz alan: %s") % e, "hata")
            self.d_kaydet.setEnabled(False)
            return None
        tamam, mesaj = slurm.sozdizimi_denetle(metin)
        self.onizleme.setPlainText(metin)
        if tamam:
            self._durum_yaz(_("bash -n: sözdizimi geçerli. Kümede: sbatch %s") % slurm.BETIK_ADI,
                            "basari")
        else:
            self._durum_yaz(_("bash -n hatası: %s") % mesaj, "hata")
        self.d_kaydet.setEnabled(tamam and bool(self.spec))
        return metin

    def _kaydet(self) -> None:
        if not self.spec:
            return
        dizin = QtWidgets.QFileDialog.getExistingDirectory(self, _("Küme koşu klasörü"))
        if not dizin:
            return
        self._zamanlayici.stop()
        try:
            yol = slurm.hazirla(self.spec, dizin, self.ayar())
        except Exception as e:
            # model kurulamadi / dizine yazilamadi: kullaniciya goster, iz loga
            _log.exception("SLURM kosu klasoru hazirlanamadi: %s", dizin)
            self._durum_yaz(_("Hazırlanamadı: %s") % e, "hata")
            return
        self._durum_yaz(_("Yazıldı: %s — kümeye kopyalayıp 'sbatch %s' ile gönderin.")
                        % (yol, os.path.basename(yol)), "basari")
