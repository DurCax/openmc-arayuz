# -*- coding: utf-8 -*-
"""
================================================================================
 dal.py  --  Analiz > "Dal tablosu" karti (v3 Y5)
================================================================================
 Tukenme sonucunun secili yanma adimlarinda bilesim SABIT tutulup kosul
 degistirilir (T_yakit, C_bor, T_mod, rho_mod): yanma adimi x kosul tablosu,
 her hucre k +- sigma ve taban dala gore dk [pcm]. Koşular Y10 kuyrugunda
 (sirali) kosar; hesap cekirdek/dal.py'dedir.
 Tukenme sonucu yoksa kart bunu soyler (once Tukenme sekmesinde kosu).
================================================================================
"""

from __future__ import annotations

import datetime
import os
from typing import Callable, Dict, List, Optional

from PySide6 import QtCore, QtWidgets

from cekirdek import dal, kuyruk, sema, tukenme_kayit
from cekirdek.ceviri import N_, _
from cekirdek.gunluk import kaydedici
from arayuz import bilesenler as bil
from arayuz import sekme_duzen as sd
from arayuz.analiz.adlar import FORM_GENISLIGI, aciklama, form_duzeni, renk

_log = kaydedici(__name__)
TABLO_YUKSEKLIGI = 240          # px
ADIM_LISTESI_YUKSEKLIGI = 120   # px
UYARI_KOSU_SAYISI = 60          # bu kadar koşudan sonra "uzun sürer" uyarisi (kullanici bilgilendirmesi)
ONERILEN = {                    # baslangic degerleri (oneri; kullanici degistirir)
    "yakit_sicaklik": "600, 900, 1200",
    "bor_ppm": "0, 500, 1000",
    "sogutucu_sicaklik": "",
    "malzeme_yogunluk": "",
}
BICIM_ADLARI = (("tek", N_("Her değişken tek başına (taramayla aynı noktalar)")),
                ("kartezyen", N_("Tüm bileşimler (kartezyen çarpım)")))


class DalKarti(bil.Kart):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(_("Dal tablosu (yanma × koşul)"), _(
            "Tükenme sonucunun seçili yanma adımlarında bileşim sabit tutulup yakıt sıcaklığı, "
            "bor, soğutucu sıcaklığı/yoğunluğu değiştirilir; her hücre bir transport koşusudur."),
            parent=parent)
        self.spec: Optional[dict] = None
        self.proje_yolu: Optional[str] = None
        self._kapi: Callable[[], tuple] = lambda: (False, _("hazır değil"))
        self._kq = None
        self._kusak = 0
        self._durumlar: Dict[str, kuyruk.IsDurumu] = {}
        self._h5: Optional[str] = None
        self._taban: Optional[dict] = None
        self._satirlar: List[dal.DalSatiri] = []
        self._kur()

    # ------------------------------------------------------------------
    def _kur(self) -> None:
        self.kaynak = QtWidgets.QLabel("")
        self.kaynak.setWordWrap(True)
        self.adimlar = QtWidgets.QListWidget()
        self.adimlar.setMinimumHeight(ADIM_LISTESI_YUKSEKLIGI // 2)
        self.adimlar.setMaximumHeight(ADIM_LISTESI_YUKSEKLIGI)
        self.adimlar.setToolTip(_("Dalın hesaplanacağı yanma noktaları (sonuç dosyasındaki "
                                  "zaman noktaları). Taze yakıt (adım 0) tarama ile karşılaştırılabilir."))
        self.adimlar.itemChanged.connect(self._tahmin)
        self.d_yenile = QtWidgets.QPushButton(_("Adımları yenile"))
        self.d_yenile.clicked.connect(self.adimlari_yukle)
        self.degisken_kutulari: Dict[str, QtWidgets.QCheckBox] = {}
        self.degisken_degerleri: Dict[str, QtWidgets.QLineEdit] = {}
        for tur in dal.TURLER:
            k = QtWidgets.QCheckBox(_(dal.TUR_ADLARI[tur]))
            e = QtWidgets.QLineEdit(ONERILEN[tur])
            e.setPlaceholderText(_("virgülle ayrılmış değerler"))
            k.setChecked(bool(ONERILEN[tur]))
            k.toggled.connect(self._tahmin)
            e.textChanged.connect(self._tahmin)
            self.degisken_kutulari[tur], self.degisken_degerleri[tur] = k, e
        self.bicim = QtWidgets.QComboBox()
        for kod, metin in BICIM_ADLARI:
            self.bicim.addItem(_(metin), kod)
        self.bicim.currentIndexChanged.connect(self._tahmin)
        self.tahmin_etiketi = QtWidgets.QLabel("")
        self.tahmin_etiketi.setWordWrap(True)
        self.d_hesapla = QtWidgets.QPushButton(_("Dal tablosunu hesapla"))
        self.d_hesapla.setObjectName("birincil")
        self.d_dur = QtWidgets.QPushButton(_("Durdur"))
        self.d_csv = QtWidgets.QPushButton(_("CSV kaydet…"))
        self.d_hesapla.clicked.connect(self.hesapla)
        self.d_dur.clicked.connect(self.durdur)
        self.d_csv.clicked.connect(self.csv_kaydet)
        self.ilerleme = QtWidgets.QProgressBar()
        self.ilerleme.setRange(0, 1)
        self.ilerleme.setValue(0)
        self.durum = QtWidgets.QLabel("")
        self.durum.setWordWrap(True)
        self.tablo = QtWidgets.QTableWidget(0, 0)
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tablo.setMinimumHeight(TABLO_YUKSEKLIGI)
        self.not_etiketi = aciklama(_(
            "Δk taban dala (koşulu değişmemiş, aynı bileşim) göre pcm; σ iki koşunun "
            "istatistik belirsizliğinin bileşkesidir (koşular bağımsız sayılır: muhafazakâr). "
            "Bileşim yanmayla ilerlemez: bu anlık koşul etkisidir, yeni bir tükenme değil."))
        f = form_duzeni()
        f.addRow(_("Tükenme sonucu:"), self.kaynak)
        f.addRow(_("Yanma adımları:"), self.adimlar)
        f.addRow("", self.d_yenile)
        for tur in dal.TURLER:
            f.addRow(self.degisken_kutulari[tur], self.degisken_degerleri[tur])
        f.addRow(_("Birleşim:"), self.bicim)
        f.addRow("", self.tahmin_etiketi)
        govde = QtWidgets.QWidget()
        govde.setLayout(f)
        govde.setMaximumWidth(FORM_GENISLIGI)
        self.ekle(govde)
        self.ekle(sd.kosu_satiri(self.d_hesapla, self.d_dur, self.ilerleme))
        self.ekle(sd.satir(self.d_csv))
        for w in (self.durum, self.tablo, self.not_etiketi):
            self.ekle(w)
        self._gorunurluk()

    # ------------------------------------------------------------------
    # disaridan (AnalizSekmesi)
    # ------------------------------------------------------------------
    def kapi_ayarla(self, fonksiyon: Callable[[], tuple]) -> None:
        self._kapi = fonksiyon
        self._gorunurluk()

    def spec_ayarla(self, spec: Optional[dict], proje_yolu: Optional[str] = None) -> None:
        self.spec, self.proje_yolu = spec, proje_yolu
        self._kaynagi_bul()
        self._gorunurluk()

    def sifirla(self) -> None:
        """Proje degisti: sonuc silinir; eski kusagin olaylari yok sayilir."""
        self._kusak += 1
        self._durumlar = {}
        self._satirlar = []
        self.adimlar.clear()
        self.tablo.setRowCount(0)
        self.tablo.setColumnCount(0)
        self.durum.setText("")
        self._h5 = self._taban = None
        self.kaynak.setText("")
        self._gorunurluk()

    def kapat(self) -> None:
        if self._kq is not None:
            self._kq.kapat()
            self._kq = None

    # ------------------------------------------------------------------
    def _kaynagi_bul(self) -> None:
        """Tukenme sonuc dosyasi ve kosuda kullanilan spec (kayit)."""
        self._h5 = self._taban = None
        if self.spec is None:
            self.kaynak.setText(_("Model yok."))
            return
        dizin = tukenme_kayit.kosu_dizini(self.spec, self.proje_yolu)
        h5 = os.path.join(dizin, "depletion_results.h5")
        if not os.path.isfile(h5):
            self.kaynak.setText(_("Tükenme sonucu yok: önce Tükenme sekmesinde bir koşu yapın."))
            self.adimlar.clear()
            return
        self._h5 = h5
        self._taban = tukenme_kayit._kayit_oku(dizin) or self.spec
        durum, farklar = tukenme_kayit.eskime(self.spec, dizin)
        metin = h5
        if durum == "eski":
            metin += "\n" + _("Sonuç şimdiki modele ait değil (değişen: %s); dal hesabı sonuç "
                              "kaydındaki modelle yapılır.") % tukenme_kayit.fark_metni(farklar)
        self.kaynak.setText(metin)
        if self.adimlar.count() == 0:
            self.adimlari_yukle()

    def adimlari_yukle(self) -> None:
        """Sonuc dosyasinin zaman noktalarini listeler (Results okumak saniyeler surebilir)."""
        self.adimlar.blockSignals(True)
        self.adimlar.clear()
        if self._h5 is not None and self._taban is not None:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            try:
                for a in dal.adim_listesi(self._h5, self._taban):
                    o = QtWidgets.QListWidgetItem(_("adım %d — %.4g gün — %.4g MWd/kg")
                                                  % (a["adim"], a["zaman_d"], a["yanma"]))
                    o.setData(QtCore.Qt.UserRole, a["adim"])
                    o.setFlags(o.flags() | QtCore.Qt.ItemIsUserCheckable)
                    o.setCheckState(QtCore.Qt.Unchecked)
                    self.adimlar.addItem(o)
            except Exception as e:     # noqa: BLE001 -- sonuc dosyasi okunamadi: kullaniciya
                _log.warning("dal: adimlar okunamadi", exc_info=True)
                self._durum_yaz(_("Adımlar okunamadı: %s") % e, hata=True)
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()
        self.adimlar.blockSignals(False)
        self._tahmin()

    def secili_adimlar(self) -> List[int]:
        return [self.adimlar.item(i).data(QtCore.Qt.UserRole) for i in range(self.adimlar.count())
                if self.adimlar.item(i).checkState() == QtCore.Qt.Checked]

    def ayar(self) -> dal.DalAyar:
        """Arayuzdeki secimden DalAyar (ValueError: gecersiz deger/secim)."""
        degiskenler = []
        for tur, kutu in self.degisken_kutulari.items():
            if not kutu.isChecked():
                continue
            metin = self.degisken_degerleri[tur].text()
            try:
                degerler = [float(p) for p in metin.replace(";", ",").split(",") if p.strip()]
            except ValueError:
                raise ValueError(_("'%s' için sayısal değerler girin (virgülle): %s")
                                 % (dal.TURLER[tur][0], metin)) from None
            degiskenler.append(dal.degisken(self._taban, tur, degerler))
        return dal.DalAyar(tuple(self.secili_adimlar()), tuple(degiskenler),
                           bicim=self.bicim.currentData())

    def _tahmin(self, *_a) -> None:
        if self._taban is None:
            self.tahmin_etiketi.setText("")
            self._gorunurluk()
            return
        try:
            a = self.ayar()
            n = len(a.adimlar) * len(dal.noktalar(a))
            metin = _("%d koşu (%d adım × %d koşul).") % (n, len(a.adimlar), len(dal.noktalar(a)))
            if n > UYARI_KOSU_SAYISI:
                metin += " " + _("Uzun sürer: her koşu tam bir transport hesabıdır.")
            self.tahmin_etiketi.setText(metin)
            self.tahmin_etiketi.setStyleSheet("")
        except ValueError as e:
            self.tahmin_etiketi.setText(str(e))
            self.tahmin_etiketi.setStyleSheet("color: %s;" % renk("hata"))
        self._gorunurluk()

    def _gecerli_mi(self) -> bool:
        try:
            self.ayar()
            return True
        except ValueError:
            return False

    def _calisiyor(self) -> bool:
        return any(not d.bitti_mi for d in self._durumlar.values())

    def _gorunurluk(self) -> None:
        izin, mesaj = self._kapi() if self.spec is not None else (False, _("Model yok"))
        bos = not self._calisiyor()
        hazir = self._h5 is not None and self._taban is not None
        self.d_hesapla.setEnabled(izin and bos and hazir and self._gecerli_mi())
        self.d_dur.setEnabled(not bos)
        self.d_csv.setEnabled(bool(self._satirlar))
        self.d_yenile.setEnabled(hazir and bos)

    def _durum_yaz(self, metin: str, hata: bool = False) -> None:
        self.durum.setStyleSheet("color: %s;" % renk("hata" if hata else "metin_soluk"))
        self.durum.setText(metin)

    def _is_parcacigi(self) -> int:
        n = int(((self.spec or {}).get("calistirma") or {}).get("is_parcacigi", 1))
        return max(1, min(n, os.cpu_count() or 1))

    def _kuyruk(self) -> kuyruk.Kuyruk:
        if self._kq is None:
            from arayuz.kuyruk.bagdastirici import KuyrukBagdastirici
            self._kq = KuyrukBagdastirici(kuyruk.Kuyruk(en_fazla_paralel=1), parent=self)
            self._kq.durum_degisti.connect(self._olay)
            uyg = QtWidgets.QApplication.instance()
            if uyg is not None:
                uyg.aboutToQuit.connect(self.kapat)
        return self._kq.kuyruk

    # ------------------------------------------------------------------
    def hesapla(self) -> None:
        izin, mesaj = self._kapi()
        if self._taban is None or self._h5 is None or not izin:
            QtWidgets.QMessageBox.warning(self, _("Çalıştırılamaz"), mesaj)
            return
        try:
            a = self.ayar()
            kok = os.path.join(sema.kosu_tabani(self.proje_yolu), "dal_kosulari",
                               datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
            self._durumlar, self._satirlar = {}, []
            self.tablo.setRowCount(0)
            self._durum_yaz(_("Dal modelleri hazırlanıyor…"))
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            try:
                q = self._kuyruk()
                kimlikler = dal.kuyruga_ekle(self._taban, self._h5, a, q, kok, self._is_parcacigi())
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()
            for kimlik in kimlikler:
                self._durumlar[kimlik] = q.durum(kimlik)
            self.ilerleme.setRange(0, len(kimlikler))
            self.ilerleme.setValue(0)
            self._durum_yaz(_("%d koşu sırada.") % len(kimlikler))
            q.baslat()
        except Exception as e:          # noqa: BLE001 -- model/sonuc uyusmazligi, dizin: kullaniciya
            _log.warning("dal baslatilamadi: %s", e, exc_info=True)
            self._durum_yaz(_("Dal hesabı başlatılamadı: %s") % e, hata=True)
            QtWidgets.QMessageBox.warning(self, _("Dal hesabı başlatılamadı"), str(e))
        self._gorunurluk()

    def durdur(self) -> None:
        if self._kq is None:
            return
        for d in self._durumlar.values():
            if not d.bitti_mi:
                self._kq.kuyruk.iptal(d.kimlik)

    # ------------------------------------------------------------------
    def _olay(self, d: kuyruk.IsDurumu) -> None:
        if dal.ETIKET not in (d.etiket or {}) or d.kimlik not in self._durumlar:
            return
        self._durumlar[d.kimlik] = d
        bitti = sum(1 for x in self._durumlar.values() if x.bitti_mi)
        self.ilerleme.setValue(bitti)
        if d.asama == kuyruk.Asama.BASARISIZ:
            self._durum_yaz(_("Bir koşu başarısız: %s") % d.hata, hata=True)
        elif bitti == len(self._durumlar):
            self._durum_yaz(_("Dal tablosu tamamlandı (%d koşu).") % bitti)
        else:
            self._durum_yaz(_("%d / %d koşu bitti.") % (bitti, len(self._durumlar)))
        self._satirlar = dal.dal_tablosu(list(self._durumlar.values()))
        self._tabloyu_doldur()
        self._gorunurluk()

    def _tabloyu_doldur(self) -> None:
        adlar = dal.degisken_adlari(self._satirlar)
        basliklar = [_("Adım"), _("Yanma [MWd/kg]")] + adlar + [_("k ± σ"), _("Δk [pcm]")]
        self.tablo.setColumnCount(len(basliklar))
        self.tablo.setHorizontalHeaderLabels(basliklar)
        self.tablo.setRowCount(len(self._satirlar))
        for i, s in enumerate(self._satirlar):
            hucreler = ["%d" % s.adim, "%.4g" % s.yanma]
            hucreler += ["%g" % s.degerler[a] if a in s.degerler else "—" for a in adlar]
            if s.k is None:
                hucreler += [s.hata or "—", "—"]
            else:
                hucreler += ["%.5f ± %.5f" % (s.k, s.sapma),
                             "—" if s.dk_pcm is None else "%+.0f ± %.0f" % (s.dk_pcm, s.dk_sapma_pcm)]
            for j, metin in enumerate(hucreler):
                self.tablo.setItem(i, j, QtWidgets.QTableWidgetItem(metin))
        self.tablo.resizeColumnsToContents()

    def csv_kaydet(self, yol: Optional[str] = None) -> Optional[str]:
        if not self._satirlar:
            return None
        if yol is None:
            yol, _suz = QtWidgets.QFileDialog.getSaveFileName(
                self, _("Dal tablosunu kaydet"), "dal_tablosu.csv", "CSV (*.csv)")
        if not yol:
            return None
        try:
            with open(yol, "w", encoding="utf-8-sig", newline="") as f:
                f.write(dal.csv_metni(self._satirlar))
        except OSError as e:
            _log.warning("dal CSV yazilamadi", exc_info=True)
            self._durum_yaz(_("CSV kaydedilemedi: %s") % e, hata=True)
            return None
        self._durum_yaz(_("Kaydedildi: %s") % yol)
        return yol
