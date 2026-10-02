# -*- coding: utf-8 -*-
"""
================================================================================
 demet_kinf.py  --  Demet k-sonsuz sihirbazi paneli (v3 K4)
================================================================================
 Demet turlerini listeler (kordaki sayisiyla), istatistik ayarini alir, her
 secili tur icin yansitici sinirli tek demet modelini koşu kuyruguna (Y10)
 ekler, ilerlemeyi ve "demet turu x k∞ ± σ" tablosunu gosterir, CSV yazar.
 Cekirdek: cekirdek/demet_kinf.py; Qt koprusu: arayuz/kuyruk/bagdastirici.py.

   p = DemetKinfPaneli(spec)                       # kendi kuyrugunu kurar
   p = DemetKinfPaneli(spec, cekirdek_kuyrugu=k)   # paylasilan kuyruk

 Yanmaya gore k∞ kapsam disi (Y4 sonrasi). Menu baglantisi orkestratorun
 isidir: ac(ebeveyn, spec, spec_yolu). Bagimsiz: python -m arayuz.analiz.demet_kinf model.json
================================================================================
"""

from __future__ import annotations

import dataclasses
import os
import sys
from typing import Any, Dict, List, Mapping, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import demet_kinf as _dk
from cekirdek import kuyruk
from cekirdek.ceviri import N_, _
from cekirdek.gunluk import kaydedici
from arayuz import tema
from arayuz.kuyruk.bagdastirici import KuyrukBagdastirici
from arayuz.kuyruk.panel import asama_adi, k_metni
from arayuz.ortak import baslik, tamsayi
from arayuz.tasarim import tokenlar

_log = kaydedici(__name__)
A = tokenlar.ARALIK
_DEMET_SUTUNLARI = (N_("Demet"), N_("Tür"), N_("Boyut"), N_("Kordaki sayı"))
_SONUC_SUTUNLARI = (N_("Demet"), N_("Durum"), N_("k∞ ± σ"), N_("Çevrim"))
_TUR_ADLARI = {"kare": N_("kare"), "altigen": N_("altıgen")}
_EN_COK_PARCACIK = 10 ** 8
_EN_COK_CEVRIM = 100000
_TEKIL: dict = {}


class DemetKinfPaneli(QtWidgets.QWidget):
    """Demet turu basina k∞ sihirbazi."""

    def __init__(self, spec: Optional[Mapping[str, Any]] = None,
                 cekirdek_kuyrugu: Optional[kuyruk.Kuyruk] = None,
                 kok_dizin: Optional[str] = None,
                 parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.spec = spec
        self.kok_dizin = kok_dizin or _dk.varsayilan_kok(None)
        self._kendi_kuyrugu = cekirdek_kuyrugu is None
        self.kq = KuyrukBagdastirici(cekirdek_kuyrugu or kuyruk.Kuyruk(), self)
        self._satirlar: Dict[str, int] = {}
        self._kur()
        self.kq.durum_degisti.connect(self._durum_geldi)
        self.spec_ayarla(spec)

    # ------------------------------------------------------------------
    def _kur(self) -> None:
        self.demetler = QtWidgets.QTableWidget(0, len(_DEMET_SUTUNLARI))
        self.demetler.setHorizontalHeaderLabels([_(s) for s in _DEMET_SUTUNLARI])
        self.demetler.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.demetler.horizontalHeader().setStretchLastSection(True)
        self.parcacik = tamsayi(_dk.VARSAYILAN_PARCACIK, 1, _EN_COK_PARCACIK, 1000)
        self.cevrim = tamsayi(_dk.VARSAYILAN_CEVRIM, 2, _EN_COK_CEVRIM, 10)
        self.pasif = tamsayi(_dk.VARSAYILAN_PASIF, 0, _EN_COK_CEVRIM, 5)
        self.tohum = tamsayi(1, 1, 2 ** 31 - 1)
        cekirdek = os.cpu_count() or 1
        self.is_parcacigi = tamsayi(min(6, cekirdek), 1, cekirdek)
        self.paralel = tamsayi(1, 1, cekirdek)
        self.d_baslat = QtWidgets.QPushButton(_("Kuyruğa ekle ve başlat"))
        self.d_iptal = QtWidgets.QPushButton(_("İptal"))
        self.d_csv = QtWidgets.QPushButton(_("CSV kaydet…"))
        self.ilerleme = QtWidgets.QProgressBar()
        self.ilerleme.setRange(0, 1)
        self.ilerleme.setValue(0)
        self.durum_etiketi = QtWidgets.QLabel("")
        self.durum_etiketi.setWordWrap(True)
        self.sonuclar = QtWidgets.QTableWidget(0, len(_SONUC_SUTUNLARI))
        self.sonuclar.setHorizontalHeaderLabels([_(s) for s in _SONUC_SUTUNLARI])
        self.sonuclar.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.sonuclar.horizontalHeader().setStretchLastSection(True)
        self.d_baslat.clicked.connect(self.baslat)
        self.d_iptal.clicked.connect(self._iptal)
        self.d_csv.clicked.connect(self._csv_sor)
        self._yerlesim()

    def _ayar_formu(self) -> QtWidgets.QWidget:
        kutu = QtWidgets.QGroupBox(_("Koşu ayarları (her demet için)"))
        form = QtWidgets.QFormLayout(kutu)
        form.addRow(_("Parçacık / çevrim:"), self.parcacik)
        form.addRow(_("Çevrim:"), self.cevrim)
        form.addRow(_("Pasif çevrim:"), self.pasif)
        form.addRow(_("Tohum:"), self.tohum)
        form.addRow(_("İş parçacığı (koşu başına):"), self.is_parcacigi)
        form.addRow(_("Aynı anda koşu:"), self.paralel)
        return kutu

    def _yerlesim(self) -> None:
        aciklama = QtWidgets.QLabel(_(
            "Her demet türü yansıtıcı sınırlı tek demet modeli olarak (sonsuz kafes, 2B) "
            "ayrı koşulur. Sonuç k∞'dur: sızıntı, su aralığı, yansıtıcı ve komşu "
            "demetlerin etkisi yoktur. Yanmaya göre k∞ bu sürümde yok."))
        aciklama.setObjectName("soluk")
        aciklama.setWordWrap(True)
        ust = QtWidgets.QHBoxLayout()
        ust.addWidget(self.demetler, 2)
        ust.addWidget(self._ayar_formu(), 1)
        dugmeler = QtWidgets.QHBoxLayout()
        dugmeler.addWidget(self.d_baslat)
        dugmeler.addWidget(self.d_iptal)
        dugmeler.addWidget(self.ilerleme, 1)
        dugmeler.addWidget(self.d_csv)
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(A["m"], A["m"], A["m"], A["m"])
        duzen.setSpacing(A["s"])
        duzen.addWidget(baslik(_("Demet k∞ sihirbazı")))
        duzen.addWidget(aciklama)
        duzen.addLayout(ust)
        duzen.addLayout(dugmeler)
        duzen.addWidget(self.durum_etiketi)
        duzen.addWidget(self.sonuclar, 1)

    # ------------------------------------------------------------------
    def spec_ayarla(self, spec: Optional[Mapping[str, Any]]) -> None:
        self.spec = spec
        turler = _dk.demet_turleri(spec) if spec else ()
        self.demetler.setRowCount(len(turler))
        for i, t in enumerate(turler):
            ad = QtWidgets.QTableWidgetItem(t.ad)
            ad.setFlags(ad.flags() | QtCore.Qt.ItemIsUserCheckable)
            ad.setCheckState(QtCore.Qt.Checked)
            self.demetler.setItem(i, 0, ad)
            hucreler = (_(_TUR_ADLARI.get(t.tur, t.tur)), "×".join(str(n) for n in t.boyut),
                        str(t.kullanim))
            for j, metin in enumerate(hucreler, start=1):
                self.demetler.setItem(i, j, QtWidgets.QTableWidgetItem(metin))
        self.demetler.resizeColumnsToContents()
        self.d_baslat.setEnabled(bool(turler))
        if not turler:
            self.durum_etiketi.setText(_("Modelde demet tanımı yok."))

    def secili_demetler(self) -> List[str]:
        return [self.demetler.item(i, 0).text() for i in range(self.demetler.rowCount())
                if self.demetler.item(i, 0).checkState() == QtCore.Qt.Checked]

    def ayar(self) -> _dk.KinfAyari:
        return _dk.KinfAyari(parcacik=self.parcacik.value(), cevrim=self.cevrim.value(),
                             pasif=self.pasif.value(), tohum=self.tohum.value(),
                             is_parcacigi=self.is_parcacigi.value())

    def _is_ayari(self, is_: kuyruk.KosuIsi) -> dict:
        """Ise eklenecek alanlar (testte sahte sonuc kancasi icin degistirilir)."""
        return {}

    def baslat(self) -> List[str]:
        """Secili demetleri kuyruga ekler ve baslatir. DONER kimlikler ([]: hata)."""
        adlar = self.secili_demetler()
        if not self.spec or not adlar:
            self.durum_etiketi.setText(_("En az bir demet seçin."))
            return []
        try:
            isler = _dk.isleri_olustur(self.spec, adlar, self.ayar().denetle(), self.kok_dizin)
            if self._kendi_kuyrugu:
                k = self.kq.kuyruk
                k.sinirlari_ayarla(self.paralel.value(),
                                   max(k.is_parcacigi_butcesi,
                                       self.paralel.value() * self.is_parcacigi.value()))
            isler = [dataclasses.replace(i, **self._is_ayari(i)) for i in isler]
            kimlikler = _dk.kuyruga_ekle(self.kq.kuyruk, isler)
        except (ValueError, kuyruk.KuyrukHatasi) as e:
            _log.warning("demet k∞ işleri eklenemedi: %s", e)
            self.durum_etiketi.setText(_("Başlatılamadı: %s") % e)
            return []
        for kimlik in kimlikler:
            self._durum_geldi(self.kq.kuyruk.durum(kimlik))
        self.kq.kuyruk.baslat()
        self.durum_etiketi.setText(_("%d demet kuyrukta.") % len(kimlikler))
        return kimlikler

    # ------------------------------------------------------------------
    def _durum_geldi(self, d: kuyruk.IsDurumu) -> None:
        ad = (d.etiket or {}).get(_dk.ETIKET)
        if ad is None:
            return                                  # paylasilan kuyrugun baska isi
        satir = self._satirlar.get(d.kimlik)
        if satir is None:
            satir = self.sonuclar.rowCount()
            self.sonuclar.insertRow(satir)
            self._satirlar[d.kimlik] = satir
        k = d.k if d.asama in (kuyruk.Asama.BITTI, kuyruk.Asama.KOSUYOR) else None
        cevrim = "%d / %s" % (d.cevrim, d.toplam_cevrim or "?")
        for j, metin in enumerate((ad, asama_adi(d.asama), k_metni(k), cevrim)):
            self.sonuclar.setItem(satir, j, QtWidgets.QTableWidgetItem(metin))
        if d.hata:
            self.sonuclar.item(satir, 1).setToolTip(d.hata)
            self.sonuclar.item(satir, 1).setForeground(QtGui.QColor(tema.renk("hata")))
        self.sonuclar.resizeColumnsToContents()
        self._ilerlemeyi_guncelle()

    def _durumlar(self) -> List[kuyruk.IsDurumu]:
        return [self.kq.kuyruk.durum(k) for k in self._satirlar]

    def _ilerlemeyi_guncelle(self) -> None:
        durumlar = self._durumlar()
        self.ilerleme.setRange(0, max(1, len(durumlar)))
        self.ilerleme.setValue(sum(1 for d in durumlar if d.bitti_mi))

    def satirlar(self) -> tuple:
        return _dk.tablo(self._durumlar())

    def csv_kaydet(self, yol: str) -> None:
        with open(yol, "w", encoding="utf-8", newline="") as f:
            f.write(_dk.csv_metni(self.satirlar()))

    def _csv_sor(self) -> None:
        yol, _s = QtWidgets.QFileDialog.getSaveFileName(
            self, _("Demet k∞ tablosunu kaydet"), "demet_kinf.csv", "CSV (*.csv)")
        if yol:
            try:
                self.csv_kaydet(yol)
            except OSError as e:
                _log.warning("demet k∞ CSV yazılamadı", exc_info=True)
                QtWidgets.QMessageBox.warning(self, _("Demet k∞"), _("Kaydedilemedi: %s") % e)

    def _iptal(self) -> None:
        for d in self._durumlar():
            if not d.bitti_mi:
                self.kq.kuyruk.iptal(d.kimlik)

    def kapat(self) -> None:
        """Kendi kuyruguysa kapatir (kosanlar iptal); paylasilansa yalniz ayrilir."""
        if self._kendi_kuyrugu:
            self.kq.kapat()
        else:
            # Paylasilan kuyruk: yalniz bu bagdastiricinin dinleyicisi cikar (kuyruk
            # surer). KuyrukBagdastirici'da "ayril" yok; Y10'a oneri olarak raporlandi.
            self.kq.kuyruk.dinleyici_cikar(self.kq._olay)

    def closeEvent(self, olay: Any) -> None:
        self.kapat()
        _TEKIL.pop("pencere", None)
        super().closeEvent(olay)


def ac(ebeveyn: Optional[QtWidgets.QWidget] = None, spec: Optional[Mapping[str, Any]] = None,
       spec_yolu: Optional[str] = None) -> DemetKinfPaneli:
    """Tekil sihirbaz penceresi (varsa one getirir ve modeli gunceller)."""
    p = _TEKIL.get("pencere")
    if p is None:
        p = DemetKinfPaneli(spec, kok_dizin=_dk.varsayilan_kok(spec_yolu), parent=ebeveyn)
        p.setWindowFlag(QtCore.Qt.Window, True)
        p.setWindowTitle(_("Demet k∞ sihirbazı"))
        p.resize(900, 640)
        _TEKIL["pencere"] = p
    else:
        p.spec_ayarla(spec)
    p.show()
    p.raise_()
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """python -m arayuz.analiz.demet_kinf model.json"""
    argv = list(sys.argv[1:] if argv is None else argv)
    from cekirdek import sema
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    tema.uygula(uyg)
    ac(None, sema.yukle(argv[0]) if argv else None, argv[0] if argv else None)
    return uyg.exec()


if __name__ == "__main__":
    sys.exit(main())
