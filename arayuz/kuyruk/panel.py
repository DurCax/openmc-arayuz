# -*- coding: utf-8 -*-
"""
panel.py -- Kosu kuyrugu paneli (Y10).

Tablo: ad, durum, cevrim, k ± σ, sure, dizin. Denetimler: paralel kosu sayisi,
OpenMP is parcacigi butcesi, kosu basina is parcacigi, MPI surec sayisi,
"Gecerli modeli ekle", "Parametrik model ekle…", Baslat/Duraklat, yukari/
asagi, iptal, kaldir. Biten her kosu kosu gecmisine yazilir
(cekirdek.kosu_gecmisi). Cekirdek: cekirdek.kuyruk; Qt koprusu:
arayuz.kuyruk.bagdastirici (yuvalar ana iplikte).
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, Mapping, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import kosu_gecmisi, kuyruk, parametre, yollar
from cekirdek.ceviri import N_, _
from cekirdek.gunluk import kaydedici
from arayuz import tema
from arayuz.kuyruk.bagdastirici import KuyrukBagdastirici
from arayuz.tasarim import tokenlar

_log = kaydedici(__name__)
A = tokenlar.ARALIK
_SUTUNLAR = (N_("Ad"), N_("Durum"), N_("Çevrim"), N_("k ± σ"), N_("Süre"), N_("Dizin"))
_MPI_EN_COK = 256          # arayuz siniri (spin kutusu); kume kosulari SLURM ile
_ASAMA_ADLARI = {
    kuyruk.Asama.BEKLIYOR: N_("bekliyor"), kuyruk.Asama.KOSUYOR: N_("koşuyor"),
    kuyruk.Asama.BITTI: N_("bitti"), kuyruk.Asama.BASARISIZ: N_("başarısız"),
    kuyruk.Asama.IPTAL: N_("iptal"),
}
_ASAMA_RENGI = {kuyruk.Asama.BITTI: "basari", kuyruk.Asama.BASARISIZ: "hata",
                kuyruk.Asama.IPTAL: "metin_soluk", kuyruk.Asama.KOSUYOR: "vurgu"}


def asama_adi(asama: kuyruk.Asama) -> str:
    return _(_ASAMA_ADLARI.get(asama, asama.value))


def k_metni(k: Optional[tuple]) -> str:
    return "%.5f ± %.5f" % k if k else "—"


def sure_metni(d: kuyruk.IsDurumu) -> str:
    if d.baslangic is None:
        return "—"
    son = d.bitis if d.bitis is not None else time.time()
    return "%.1f s" % max(0.0, son - d.baslangic)


class KuyrukPaneli(QtWidgets.QWidget):
    """Kosu kuyrugunu yoneten panel."""

    gecmis_degisti = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None,
                 cekirdek_kuyrugu: Optional[kuyruk.Kuyruk] = None,
                 gecmis: Optional[kosu_gecmisi.GecmisDeposu] = None) -> None:
        super().__init__(parent)
        self.spec: Optional[Dict[str, Any]] = None
        self.kq = KuyrukBagdastirici(cekirdek_kuyrugu or kuyruk.Kuyruk(), self)
        self.gecmis = gecmis
        if gecmis is not None:
            self.kq.kuyruk.dinleyici_ekle(kosu_gecmisi.gecmis_dinleyicisi(gecmis))
        self._satirlar: Dict[str, int] = {}
        self._kur()
        self.kq.durum_degisti.connect(self._durum_geldi)
        self.kq.hepsi_bitti.connect(self._hepsi_bitti)
        self._sayac = QtCore.QTimer(self)
        self._sayac.setInterval(1000)                 # sure sutunu 1 s'de bir
        self._sayac.timeout.connect(self._sureleri_yenile)
        self._sayac.start()
        self._dugmeleri_guncelle()

    # ------------------------------------------------------------------
    # kurulum
    # ------------------------------------------------------------------
    def _kur(self) -> None:
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(A["l"], A["l"], A["l"], A["l"])
        duzen.setSpacing(A["m"])
        duzen.addWidget(self._sinir_kutusu())
        duzen.addLayout(self._dugme_satiri())
        self.tablo = QtWidgets.QTableWidget(0, len(_SUTUNLAR), self)
        self.tablo.setHorizontalHeaderLabels([_(s) for s in _SUTUNLAR])
        self.tablo.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tablo.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tablo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeToContents)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.itemSelectionChanged.connect(self._dugmeleri_guncelle)
        duzen.addWidget(self.tablo, 1)
        self.durum_etiket = QtWidgets.QLabel("", self)
        self.durum_etiket.setWordWrap(True)
        duzen.addWidget(self.durum_etiket)

    def _sinir_kutusu(self) -> QtWidgets.QWidget:
        kutu = QtWidgets.QGroupBox(_("Paralellik ve kaynaklar"), self)
        form = QtWidgets.QFormLayout(kutu)
        cpu = os.cpu_count() or 1
        k = self.kq.kuyruk
        self.paralel = self._spin(1, cpu, k.en_fazla_paralel)
        self.butce = self._spin(1, cpu, min(k.is_parcacigi_butcesi, cpu))
        self.is_parcacigi = self._spin(1, cpu, min(6, cpu))
        self.mpi = self._spin(0, _MPI_EN_COK, 0)
        for s in (self.paralel, self.butce):
            s.valueChanged.connect(self._sinirlar_degisti)
        form.addRow(_("En fazla paralel koşu"), self.paralel)
        form.addRow(_("Toplam iş parçacığı bütçesi"), self.butce)
        form.addRow(_("Koşu başına iş parçacığı (OMP)"), self.is_parcacigi)
        form.addRow(_("MPI süreç sayısı (0 = MPI yok)"), self.mpi)
        self.mpi_bilgi = QtWidgets.QLabel(self._mpi_metni(), kutu)
        self.mpi_bilgi.setWordWrap(True)
        form.addRow("", self.mpi_bilgi)
        self.kok = QtWidgets.QLineEdit(os.path.join(yollar.kullanici_veri_dizini(), "kosular"),
                                       kutu)
        sec = QtWidgets.QPushButton(_("Seç…"), kutu)
        sec.clicked.connect(self._kok_sec)
        satir = QtWidgets.QWidget(kutu)
        sd = QtWidgets.QHBoxLayout(satir)
        sd.setContentsMargins(0, 0, 0, 0)
        sd.addWidget(self.kok, 1)
        sd.addWidget(sec)
        form.addRow(_("Koşu klasörü (her koşu ayrı alt dizinde)"), satir)
        return kutu

    def _spin(self, alt: int, ust: int, deger: int) -> QtWidgets.QSpinBox:
        s = QtWidgets.QSpinBox(self)
        s.setRange(alt, ust)
        s.setValue(deger)
        return s

    def _dugme_satiri(self) -> QtWidgets.QHBoxLayout:
        satir = QtWidgets.QHBoxLayout()
        satir.setSpacing(A["s"])
        tanimlar = (
            ("d_ekle", _("Geçerli modeli ekle"), self.gecerli_modeli_ekle),
            ("d_param", _("Parametrik model ekle…"), self._parametrik_sec),
            ("d_baslat", _("Başlat"), self._baslat_duraklat),
            ("d_yukari", _("Yukarı"), lambda: self._tasi(-1)),
            ("d_asagi", _("Aşağı"), lambda: self._tasi(+1)),
            ("d_iptal", _("İptal"), self._iptal),
            ("d_kaldir", _("Kaldır"), self._kaldir),
        )
        for ad, metin, yuva in tanimlar:
            d = QtWidgets.QPushButton(metin, self)
            d.clicked.connect(yuva)
            setattr(self, ad, d)
            satir.addWidget(d)
        satir.addStretch(1)
        return satir

    def _mpi_metni(self) -> str:
        exe = yollar.openmc_ikilisi()
        destek = kuyruk.mpi_destegi(exe)
        mpiexec = kuyruk.mpiexec_yolu()
        if destek is True and mpiexec:
            return _("MPI kullanılabilir (mpiexec: %s).") % mpiexec
        if destek is False:
            return _("Bu openmc MPI desteksiz derlenmiş; MPI süreç sayısı 0 kalmalı. "
                     "Kümede MPI için SLURM sekmesini kullanın.")
        return _("MPI desteği belirlenemedi (openmc ya da mpiexec bulunamadı).")

    # ------------------------------------------------------------------
    # dis API
    # ------------------------------------------------------------------
    def spec_ayarla(self, spec: Optional[Mapping[str, Any]]) -> None:
        self.spec = dict(spec) if spec else None
        self._dugmeleri_guncelle()

    def kapat(self) -> None:
        self._sayac.stop()
        self.kq.kapat()

    def gecerli_modeli_ekle(self) -> Optional[str]:
        if not self.spec:
            return None
        ad = str(self.spec.get("ad") or _("model"))
        return self._ekle(lambda: self.kq.kuyruk.ekle(self._is(ad, self.spec)))

    def parametrik_ekle(self, model: parametre.ParametrikModel) -> list:
        kok = kuyruk.ayri_dizin(self.kok.text(), model.ad or "parametrik")
        return self._ekle(lambda: parametre.kuyruga_ekle(
            model, self.kq.kuyruk, kok, is_parcacigi=self.is_parcacigi.value(),
            mpi_surec=self.mpi.value())) or []

    # ------------------------------------------------------------------
    def _is(self, ad: str, spec: Mapping[str, Any]) -> kuyruk.KosuIsi:
        alinmis = [d.dizin for d in self.kq.kuyruk.durumlar()]
        return kuyruk.KosuIsi(ad=ad, spec=spec, is_parcacigi=self.is_parcacigi.value(),
                              mpi_surec=self.mpi.value(),
                              dizin=kuyruk.ayri_dizin(self.kok.text(), ad, alinmis))

    def _ekle(self, islem: Callable[[], Any]) -> Any:
        try:
            return islem()
        except (ValueError, KeyError, RuntimeError, OSError) as e:
            # DogrulamaHatasi bir ValueError'dur; OSError: koşu klasörü yazılamaz
            _log.warning("kuyruga eklenemedi: %s", e)
            self._durum_yaz(_("Kuyruğa eklenemedi: %s") % e, "hata")
            return None

    def _parametrik_sec(self) -> None:
        yol, _f = QtWidgets.QFileDialog.getOpenFileName(
            self, _("Parametrik model"), "", _("Parametrik model (*.json)"))
        if not yol:
            return
        try:
            model = parametre.yukle(yol)
        except (OSError, ValueError, KeyError) as e:
            self._durum_yaz(_("Parametrik model okunamadı: %s") % e, "hata")
            return
        n = len(self.parametrik_ekle(model))
        if n:
            self._durum_yaz(_("%d nokta kuyruğa eklendi.") % n, "basari")

    def _kok_sec(self) -> None:
        d = QtWidgets.QFileDialog.getExistingDirectory(self, _("Koşu klasörü"), self.kok.text())
        if d:
            self.kok.setText(d)

    def _sinirlar_degisti(self) -> None:
        try:
            self.kq.kuyruk.sinirlari_ayarla(self.paralel.value(), self.butce.value())
        except ValueError as e:
            self._durum_yaz(str(e), "hata")

    def _secili(self) -> Optional[str]:
        satirlar = self.tablo.selectionModel().selectedRows()
        if not satirlar:
            return None
        oge = self.tablo.item(satirlar[0].row(), 0)
        return oge.data(QtCore.Qt.UserRole) if oge else None

    def _baslat_duraklat(self) -> None:
        if self.kq.kuyruk.etkin:
            self.kq.kuyruk.duraklat()
        else:
            self.kq.kuyruk.baslat()
        self._dugmeleri_guncelle()

    def _tasi(self, yon: int) -> None:
        kimlik = self._secili()
        if kimlik is None:
            return
        sira = [d.kimlik for d in self.kq.kuyruk.durumlar()].index(kimlik)
        self.kq.kuyruk.tasi(kimlik, sira + yon)
        self._tabloyu_yeniden_kur(secili=kimlik)

    def _iptal(self) -> None:
        kimlik = self._secili()
        if kimlik is not None:
            self.kq.kuyruk.iptal(kimlik)

    def _kaldir(self) -> None:
        kimlik = self._secili()
        if kimlik is None:
            return
        try:
            self.kq.kuyruk.kaldir(kimlik)
        except RuntimeError as e:
            self._durum_yaz(str(e), "uyari")
            return
        self._tabloyu_yeniden_kur()

    # ------------------------------------------------------------------
    # tablo
    # ------------------------------------------------------------------
    def _durum_geldi(self, d: kuyruk.IsDurumu) -> None:
        if d.kimlik not in self._satirlar or self._sira_degisti():
            self._tabloyu_yeniden_kur(secili=self._secili())
        else:
            self._satir_yaz(self._satirlar[d.kimlik], d)
        if d.bitti_mi:
            self.gecmis_degisti.emit()
            if d.asama == kuyruk.Asama.BASARISIZ:
                self._durum_yaz(_("'%s' başarısız: %s") % (d.ad, d.hata or ""), "hata")
        self._dugmeleri_guncelle()

    def _sira_degisti(self) -> bool:
        sira = [d.kimlik for d in self.kq.kuyruk.durumlar()]
        return sira != sorted(self._satirlar, key=self._satirlar.get)

    def _tabloyu_yeniden_kur(self, secili: Optional[str] = None) -> None:
        durumlar = self.kq.kuyruk.durumlar()
        self.tablo.setRowCount(len(durumlar))
        self._satirlar = {}
        for i, d in enumerate(durumlar):
            self._satirlar[d.kimlik] = i
            self._satir_yaz(i, d)
            if d.kimlik == secili:
                self.tablo.selectRow(i)
        self._dugmeleri_guncelle()

    def _satir_yaz(self, i: int, d: kuyruk.IsDurumu) -> None:
        cevrim = ("%d / %d" % (d.cevrim, d.toplam_cevrim) if d.toplam_cevrim
                  else str(d.cevrim or "—"))
        degerler = (d.ad, asama_adi(d.asama), cevrim, k_metni(d.k), sure_metni(d), d.dizin)
        for j, metin in enumerate(degerler):
            oge = QtWidgets.QTableWidgetItem(metin)
            if j == 0:
                oge.setData(QtCore.Qt.UserRole, d.kimlik)
            if j == 1 and d.asama in _ASAMA_RENGI:
                oge.setForeground(QtGui.QColor(tema.renk(_ASAMA_RENGI[d.asama])))
            if j == 1 and d.hata:
                oge.setToolTip(d.hata)
            self.tablo.setItem(i, j, oge)

    def _sureleri_yenile(self) -> None:
        for d in self.kq.kuyruk.durumlar():
            if d.asama == kuyruk.Asama.KOSUYOR and d.kimlik in self._satirlar:
                oge = self.tablo.item(self._satirlar[d.kimlik], 4)
                if oge is not None:
                    oge.setText(sure_metni(d))

    def _hepsi_bitti(self) -> None:
        durumlar = self.kq.kuyruk.durumlar()
        biten = sum(1 for d in durumlar if d.asama == kuyruk.Asama.BITTI)
        self._durum_yaz(_("Kuyruk tamamlandı: %d / %d koşu başarılı.") % (biten, len(durumlar)),
                        "basari" if biten == len(durumlar) else "uyari")

    def _durum_yaz(self, metin: str, tur: str = "") -> None:
        self.durum_etiket.setText(metin)
        self.durum_etiket.setStyleSheet("color: %s;" % tema.renk(tur) if tur else "")

    def _dugmeleri_guncelle(self) -> None:
        secili = self._secili()
        durum = None
        if secili is not None:
            try:
                durum = self.kq.kuyruk.durum(secili)
            except KeyError:
                durum = None
        self.d_ekle.setEnabled(bool(self.spec))
        self.d_baslat.setText(_("Duraklat") if self.kq.kuyruk.etkin else _("Başlat"))
        self.d_yukari.setEnabled(durum is not None)
        self.d_asagi.setEnabled(durum is not None)
        self.d_iptal.setEnabled(durum is not None and not durum.bitti_mi)
        self.d_kaldir.setEnabled(durum is not None and durum.asama != kuyruk.Asama.KOSUYOR)
