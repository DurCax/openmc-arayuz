# -*- coding: utf-8 -*-
"""
================================================================================
 mgxs.py  --  Analiz > "Grup sabitleri ve random ray" karti (v3 Y8)
================================================================================
 1) Grup sabitlerini uret: modelin (ya da secili demetin yansitici alt
    modelinin) MGXS tally'li CE koşusu kuyrukta (Y10) kosar; bitince tablo,
    k ozeti, mgxs.csv ve mgxs.h5.
 2) MG ile yeniden kos: ayni geometri, makroskopik MG malzemeler.
 3) Random ray ile kos: ayni mgxs.h5, settings.random_ray.
 CE / MG / RR karsilastirma tablosu: k +- sigma, CE'ye ve MG'ye fark [pcm], sure.

 Hesap cekirdek/mgxs_uret.py, mgxs_is.py, mg_model.py, random_ray.py'dedir;
 gosterim yardimcilari arayuz/analiz/mgxs_tablo.py. Koşu dizinleri:
 <kosu tabani>/mgxs_{ce,mg,rr}.
================================================================================
"""

from __future__ import annotations

import dataclasses
import os
import shutil
from typing import Callable, Optional

from PySide6 import QtCore, QtWidgets

from cekirdek import kuyruk, mgxs_is, mgxs_uret, random_ray, sema
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from arayuz import bilesenler as bil
from arayuz import sekme_duzen as sd
from arayuz.analiz import mgxs_tablo as tb
from arayuz.analiz.adlar import FORM_GENISLIGI, aciklama, form_duzeni, renk
from arayuz.ortak import GelismisBolum, sayi, tamsayi

_log = kaydedici(__name__)
TABLO_YUKSEKLIGI = 260        # sabit tablosu [px]
KARSI_YUKSEKLIGI = 130        # 3 satir + baslik [px]
TUR_LISTESI_YUKSEKLIGI = 110  # 5 secmeli tur [px]
EN_COK_ISIN = 10 ** 6
EN_COK_CEVRIM = 100000
EN_COK_MESAFE = 1.0e5         # cm


_Y8 = "y8"                    # kuyruk isi etiketi: ce | mg | rr (cekirdek/mgxs_is.py)


def _tur_adi(tur: Optional[str]) -> str:
    ad = mgxs_is.TURLER.get(tur or "", tur or "")
    return _(ad)


class MgxsKarti(bil.Kart):

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(_("Grup sabitleri ve random ray"), _(
            "Akı ağırlıklı çok gruplu tesir kesitleri (openmc.mgxs) üretir; aynı geometriyi "
            "çok gruplu Monte Carlo ve random ray ile yeniden koşup CE sonucuyla karşılaştırır."),
            parent=parent)
        self.spec: Optional[dict] = None
        self.proje_yolu: Optional[str] = None
        self._kapi: Callable[[], tuple] = lambda: (False, _("hazır değil"))
        self._kq = None                       # KuyrukBagdastirici (ilk kosuda)
        self._kusak = 0
        self._durumlar: dict = {}             # tur -> IsDurumu (son)
        self._ce_spec: Optional[dict] = None
        self.sonuc: Optional[mgxs_uret.MgxsSonuc] = None
        self._girdileri_kur()
        self._rr_girdileri_kur()
        self._dugmeleri_kur()
        self._sonuclari_kur()
        self._yerlesim_kur()
        self._gorunurluk()

    # ------------------------------------------------------------------
    def _girdileri_kur(self) -> None:
        self.kapsam = QtWidgets.QComboBox()
        self.bolge = QtWidgets.QComboBox()
        for anahtar, metin in mgxs_uret.BOLGE_ADLARI.items():
            self.bolge.addItem(_(metin), anahtar)
        self.bolge.setToolTip(_(
            "Malzeme: her malzeme bir bölge. Hücre: her malzemeli hücre bir bölge.\n"
            "Demet: modelin tamamı tek bölge (yansıtıcı sınırlı modelde sonsuz kafes sabitleri)."))
        self.grup = QtWidgets.QComboBox()
        from openmc.mgxs import GROUP_STRUCTURES
        for g in mgxs_uret.GRUP_YAPILARI:
            self.grup.addItem(_("%s (%d grup)") % (g, len(GROUP_STRUCTURES[g]) - 1), g)
        self.grup.setToolTip(_(
            "Homojenleştirme için 2–8 grup; MG ile yeniden koşu için ince yapı (CASMO-70, "
            "XMAS-172) grup yoğunlaştırma hatasını küçültür."))
        self.duzeltme = QtWidgets.QComboBox()
        self.duzeltme.addItem(_("Yok (izotropik saçılma, Σt)"), "yok")
        self.duzeltme.addItem(_("P0 taşıma düzeltmesi (out-scatter, Σtr)"), "P0")
        self.duzeltme.setToolTip(_(
            "P0: Σtr = Σt − Σs1 ve saçılma köşegeni Σs1 kadar azalır; sonsuz ortam k∞'u "
            "değişmez, sızıntı (D = 1/3Σtr) değişir.\nİnce grupta köşegen negatif olabilir: "
            "MG Monte Carlo bunu doğru işleyemez (random ray kararlılaştırır)."))
        self.turler = QtWidgets.QListWidget()
        for t in mgxs_uret.SECMELI_TURLER:
            o = QtWidgets.QListWidgetItem(_(mgxs_uret.TUR_ADLARI[t]))
            o.setData(QtCore.Qt.UserRole, t)
            o.setFlags(o.flags() | QtCore.Qt.ItemIsUserCheckable)
            o.setCheckState(QtCore.Qt.Unchecked)
            self.turler.addItem(o)
        self.turler.setMaximumHeight(TUR_LISTESI_YUKSEKLIGI)
        self.turler.setToolTip(_("Σt, Σa, νΣf, χ ve saçılma matrisleri her zaman üretilir "
                                 "(MG kütüphanesi için gerekli)."))

    def _rr_girdileri_kur(self) -> None:
        v = random_ray
        self.rr_isin = tamsayi(v.VARSAYILAN_ISIN, 1, EN_COK_ISIN, 50, _("ışın"))
        self.rr_cevrim = tamsayi(v.VARSAYILAN_CEVRIM, 2, EN_COK_CEVRIM, 50)
        self.rr_pasif = tamsayi(v.VARSAYILAN_PASIF, 0, EN_COK_CEVRIM, 50)
        self.rr_olu = sayi(30.0, 2, 0.0, EN_COK_MESAFE, 5.0, "cm")
        self.rr_aktif = sayi(150.0, 2, 0.01, EN_COK_MESAFE, 10.0, "cm")
        self.rr_sekil = QtWidgets.QComboBox()
        for s, metin in (("flat", _("Düz (flat)")), ("linear", _("Doğrusal (linear)")),
                         ("linear_xy", _("Doğrusal, yalnız x-y"))):
            self.rr_sekil.addItem(metin, s)
        self.rr_bolme = tamsayi(0, 0, v.EN_COK_BOLME, 1)
        self.rr_bolme.setToolTip(_("Kaynak bölgelerini eksen başına N×N kare mesh ile böler "
                                   "(0 = bölme yok). Varsayılan ≈ 0.1 cm hücre."))
        self.rr_gelismis = GelismisBolum("mgxs_rr", _("Random ray ayarları"))
        f = form_duzeni()
        f.addRow(_("Çevrim başına ışın:"), self.rr_isin)
        f.addRow(_("Çevrim / pasif:"), sd.satir(self.rr_cevrim, self.rr_pasif))
        f.addRow(_("Ölü / aktif mesafe:"), sd.satir(self.rr_olu, self.rr_aktif))
        f.addRow(_("Kaynak şekli:"), self.rr_sekil)
        f.addRow(_("Kaynak bölgesi bölmesi:"), self.rr_bolme)
        govde = QtWidgets.QWidget()
        govde.setLayout(f)
        self.rr_gelismis.ekle(govde)

    def _dugmeleri_kur(self) -> None:
        self.d_uret = QtWidgets.QPushButton(_("Grup sabitlerini üret"))
        self.d_uret.setObjectName("birincil")
        self.d_mg = QtWidgets.QPushButton(_("MG ile yeniden koş"))
        self.d_rr = QtWidgets.QPushButton(_("Random ray ile koş"))
        self.d_csv = QtWidgets.QPushButton(_("CSV kaydet…"))
        self.d_dur = QtWidgets.QPushButton(_("Durdur"))
        self.d_uret.clicked.connect(self.uret)
        self.d_mg.clicked.connect(self.mg_kos)
        self.d_rr.clicked.connect(self.rr_kos)
        self.d_csv.clicked.connect(self.csv_kaydet)
        self.d_dur.clicked.connect(self.durdur)
        self.ilerleme = QtWidgets.QProgressBar()
        self.ilerleme.setRange(0, 1)
        self.ilerleme.setValue(0)
        self.durum_etiketi = QtWidgets.QLabel("")
        self.durum_etiketi.setWordWrap(True)

    def _sonuclari_kur(self) -> None:
        self.ozet = QtWidgets.QLabel(_("Henüz grup sabiti üretilmedi."))
        self.ozet.setWordWrap(True)
        self.ozet.setTextFormat(QtCore.Qt.RichText)
        self.ozet.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.tur_suzgeci = QtWidgets.QComboBox()
        self.tur_suzgeci.currentIndexChanged.connect(self._tabloyu_doldur)
        self.tablo = self._tablo(tb.XS_SUTUNLARI, tb.xs_basliklari(), TABLO_YUKSEKLIGI)
        self.tablo_notu = aciklama("")
        self.karsi = self._tablo(tb.KARSI_SUTUNLARI, tb.karsi_basliklari(), KARSI_YUKSEKLIGI)

    @staticmethod
    def _tablo(sutun: int, basliklar: list, yukseklik: int) -> QtWidgets.QTableWidget:
        t = QtWidgets.QTableWidget(0, sutun)
        t.setHorizontalHeaderLabels(basliklar)
        t.horizontalHeader().setStretchLastSection(True)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        t.setMinimumHeight(yukseklik)
        return t

    def _yerlesim_kur(self) -> None:
        f = form_duzeni()
        f.addRow(_("Kapsam:"), self.kapsam)
        f.addRow(_("Bölge türü:"), self.bolge)
        f.addRow(_("Grup yapısı:"), self.grup)
        f.addRow(_("Taşıma düzeltmesi:"), self.duzeltme)
        f.addRow(_("Ek türler:"), self.turler)
        f.addRow("", self.rr_gelismis)
        govde = QtWidgets.QWidget()
        govde.setLayout(f)
        govde.setMaximumWidth(FORM_GENISLIGI)
        self.ekle(govde)
        self.ekle(sd.kosu_satiri(self.d_uret, self.d_dur, self.ilerleme))
        self.ekle(sd.satir(self.d_mg, self.d_rr, self.d_csv))
        for w in (self.durum_etiketi, self.ozet):
            self.ekle(w)
        self.ekle(sd.satir(QtWidgets.QLabel(_("Gösterilen tür:")), self.tur_suzgeci))
        for w in (self.tablo, self.tablo_notu, QtWidgets.QLabel(_("CE / MG / RR karşılaştırması")),
                  self.karsi):
            self.ekle(w)

    # ==================================================================
    # disaridan (AnalizSekmesi)
    # ==================================================================
    def kapi_ayarla(self, fonksiyon: Callable[[], tuple]) -> None:
        self._kapi = fonksiyon
        self._gorunurluk()

    def spec_ayarla(self, spec: Optional[dict], proje_yolu: Optional[str] = None) -> None:
        self.spec, self.proje_yolu = spec, proje_yolu
        secili = self.kapsam.currentData()
        self.kapsam.clear()
        for anahtar, metin in (mgxs_is.kapsam_secenekleri(spec) if spec else []):
            self.kapsam.addItem(metin, anahtar)
        i = self.kapsam.findData(secili)
        self.kapsam.setCurrentIndex(max(0, i))
        self._gorunurluk()

    def sifirla(self) -> None:
        """Proje degisti: sonuc silinir; eski kusagin olaylari yok sayilir."""
        self._kusak += 1
        self._durumlar = {}
        self.sonuc = self._ce_spec = None
        self.ozet.setText(_("Henüz grup sabiti üretilmedi."))
        self.tablo.setRowCount(0)
        self.karsi.setRowCount(0)
        self.tur_suzgeci.clear()
        self.tablo_notu.setText("")
        self.durum_etiketi.setText("")
        self._gorunurluk()

    def kapat(self) -> None:
        if self._kq is not None:
            self._kq.kapat()
            self._kq = None

    # ==================================================================
    # ayar
    # ==================================================================
    def ayar(self) -> mgxs_uret.MgxsAyar:
        turler = tuple(self.turler.item(i).data(QtCore.Qt.UserRole)
                       for i in range(self.turler.count())
                       if self.turler.item(i).checkState() == QtCore.Qt.Checked)
        return mgxs_uret.MgxsAyar(True, self.bolge.currentData(), self.grup.currentData(),
                                  turler, self.duzeltme.currentData())

    def rr_ayari(self) -> random_ray.RRAyar:
        return random_ray.RRAyar(
            olu_mesafe=self.rr_olu.value(), aktif_mesafe=self.rr_aktif.value(),
            isin=self.rr_isin.value(), cevrim=self.rr_cevrim.value(),
            pasif=self.rr_pasif.value(), kaynak_sekli=self.rr_sekil.currentData(),
            bolme=self.rr_bolme.value())

    def _rr_doldur(self, a: random_ray.RRAyar) -> None:
        self.rr_olu.setValue(a.olu_mesafe)
        self.rr_aktif.setValue(a.aktif_mesafe)
        self.rr_isin.setValue(a.isin)
        self.rr_cevrim.setValue(a.cevrim)
        self.rr_pasif.setValue(a.pasif)
        self.rr_sekil.setCurrentIndex(max(0, self.rr_sekil.findData(a.kaynak_sekli)))
        self.rr_bolme.setValue(a.bolme)

    # ==================================================================
    # kosular
    # ==================================================================
    def _calisiyor(self) -> bool:
        return any(not d.bitti_mi for d in self._durumlar.values())

    def _gorunurluk(self) -> None:
        izin, mesaj = self._kapi() if self.spec is not None else (False, _("Model yok"))
        bos = not self._calisiyor()
        self.d_uret.setEnabled(izin and bos)
        hazir = self.sonuc is not None and bos
        self.d_mg.setEnabled(hazir and self.sonuc.k_ce is not None)
        self.d_rr.setEnabled(hazir and self.sonuc.k_ce is not None)
        self.d_csv.setEnabled(self.sonuc is not None)
        self.d_dur.setEnabled(not bos)
        if not izin and bos:
            self._durum_yaz(mesaj, hata=True)

    def _durum_yaz(self, metin: str, hata: bool = False) -> None:
        self.durum_etiketi.setStyleSheet("color: %s;" % renk("hata" if hata else "metin_soluk"))
        self.durum_etiketi.setText(metin)

    def _dizin(self, tur: str) -> str:
        return os.path.join(sema.kosu_tabani(self.proje_yolu), "mgxs_%s" % tur)

    def _is_parcacigi(self) -> int:
        n = int(((self.spec or {}).get("calistirma") or {}).get("is_parcacigi", 1))
        return max(1, min(n, os.cpu_count() or 1))

    def _kuyruk(self):
        if self._kq is None:
            from arayuz.kuyruk.bagdastirici import KuyrukBagdastirici
            self._kq = KuyrukBagdastirici(kuyruk.Kuyruk(en_fazla_paralel=1), parent=self)
            self._kq.durum_degisti.connect(self._olay)
            uyg = QtWidgets.QApplication.instance()
            if uyg is not None:
                uyg.aboutToQuit.connect(self.kapat)   # kosan openmc sureci yetim kalmasin
        return self._kq.kuyruk

    def _ekle(self, is_: kuyruk.KosuIsi) -> None:
        is_ = dataclasses.replace(is_, etiket=dict(is_.etiket, kusak=self._kusak))
        q = self._kuyruk()
        q.ekle(is_)
        q.baslat()

    def _hata(self, baslik: str, e: Exception) -> None:
        _log.warning("%s: %s", baslik, e, exc_info=True)
        self._durum_yaz("%s: %s" % (baslik, e), hata=True)
        QtWidgets.QMessageBox.warning(self, baslik, str(e))

    def uret(self) -> None:
        izin, mesaj = self._kapi()
        if self.spec is None or not izin:
            QtWidgets.QMessageBox.warning(self, _("Çalıştırılamaz"), mesaj)
            return
        try:
            kapsamli = mgxs_is.kapsam_spec(self.spec, self.kapsam.currentData())
            a = self.ayar()
            self._ce_spec = mgxs_uret.ile(kapsamli, a)
            is_ = mgxs_is.ce_isi(kapsamli, a, self._dizin("ce"), self._is_parcacigi())
            self._durumlar = {}
            self.karsi.setRowCount(0)
            self._ekle(is_)
        except Exception as e:      # noqa: BLE001 -- dogrulama/alt model/dizin: kullaniciya
            self._hata(_("Grup sabiti koşusu başlatılamadı"), e)
        self._gorunurluk()

    def _ikincil(self, kurucu: Callable[[], kuyruk.KosuIsi], baslik: str) -> None:
        if self.sonuc is None or self._ce_spec is None:
            return
        try:
            self._ekle(kurucu())
        except Exception as e:      # noqa: BLE001 -- model kurulumu/dosya: kullaniciya
            self._hata(baslik, e)
        self._gorunurluk()

    def mg_kos(self) -> None:
        self._ikincil(lambda: mgxs_is.mg_isi(self._ce_spec, self.sonuc.dizin, self._dizin("mg"),
                                             self._is_parcacigi()),
                      _("MG koşusu başlatılamadı"))

    def rr_kos(self) -> None:
        def _kur() -> kuyruk.KosuIsi:
            return mgxs_is.rr_isi(self._ce_spec, self.sonuc.dizin, self._dizin("rr"),
                                  self._is_parcacigi(), self.rr_ayari())
        self._ikincil(_kur, _("Random ray koşusu başlatılamadı"))

    def durdur(self) -> None:
        if self._kq is None:
            return
        for d in self._durumlar.values():
            if not d.bitti_mi:
                self._kq.kuyruk.iptal(d.kimlik)

    # ==================================================================
    # olaylar (ana iplik; bagdastirici kuyruklu iletir)
    # ==================================================================
    def _olay(self, d: kuyruk.IsDurumu) -> None:
        tur = d.etiket.get(_Y8)
        if d.etiket.get("kusak") != self._kusak or tur not in mgxs_is.TURLER:
            return
        self._durumlar[tur] = d
        self._ilerleme(d)
        if d.asama == kuyruk.Asama.BITTI and tur == "ce":
            self._ce_bitti(d)
        elif d.asama == kuyruk.Asama.BASARISIZ:
            self._durum_yaz(_("%s başarısız: %s") % (_tur_adi(tur), d.hata), hata=True)
        if d.bitti_mi:
            tb.karsi_doldur(self.karsi, mgxs_is.karsilastirma(list(self._durumlar.values())))
        self._gorunurluk()

    def _ilerleme(self, d: kuyruk.IsDurumu) -> None:
        toplam = d.toplam_cevrim or 0
        self.ilerleme.setRange(0, max(1, toplam))
        self.ilerleme.setValue(min(d.cevrim, toplam) if toplam else int(d.bitti_mi))
        if not d.bitti_mi:
            k = "" if d.k is None else "  k = %.5f ± %.5f" % d.k
            self._durum_yaz(_("%s: çevrim %d%s") % (_tur_adi(d.etiket.get(_Y8)), d.cevrim, k))
        elif d.asama == kuyruk.Asama.BITTI:
            self._durum_yaz(_("%s bitti.") % _tur_adi(d.etiket.get(_Y8)))

    def _ce_bitti(self, d: kuyruk.IsDurumu) -> None:
        sonuc = (d.sonuc or {}).get("mgxs") if isinstance(d.sonuc, dict) else None
        if sonuc is None:
            self._durum_yaz(_("CE koşusu bitti ama grup sabitleri okunamadı"), hata=True)
            return
        self.sonuc_goster(sonuc)
        try:
            self._rr_doldur(mgxs_is.rr_varsayilan(self._ce_spec, sonuc.dizin))
        except (OSError, ValueError) as e:
            _log.warning("random ray varsayilani kurulamadi: %s", e)

    def sonuc_goster(self, sonuc: mgxs_uret.MgxsSonuc) -> None:
        self.sonuc = sonuc
        self.ozet.setText(tb.ozet_html(sonuc))
        secili = self.tur_suzgeci.currentData()
        self.tur_suzgeci.blockSignals(True)
        self.tur_suzgeci.clear()
        self.tur_suzgeci.addItem(_("Hepsi"), None)
        for t in sonuc.ayar.etkin_turler:
            self.tur_suzgeci.addItem(_(mgxs_uret.TUR_ADLARI.get(t, t)), t)
        self.tur_suzgeci.setCurrentIndex(max(0, self.tur_suzgeci.findData(secili)))
        self.tur_suzgeci.blockSignals(False)
        self._tabloyu_doldur()
        self._gorunurluk()

    def _tabloyu_doldur(self, *_args) -> None:
        if self.sonuc is None:
            return
        n = tb.xs_doldur(self.tablo, self.sonuc, self.tur_suzgeci.currentData())
        self.tablo_notu.setText(
            _("%d satırın ilk %d'i gösteriliyor; tamamı mgxs.csv'de.") % (n, tb.EN_COK_SATIR)
            if n > tb.EN_COK_SATIR else _("Grup 1 en yüksek enerji. σ: istatistik (1σ)."))

    def csv_kaydet(self, yol: Optional[str] = None) -> Optional[str]:
        if self.sonuc is None:
            return None
        if yol is None:
            yol, _suz = QtWidgets.QFileDialog.getSaveFileName(
                self, _("Grup sabitlerini kaydet"), "mgxs.csv", "CSV (*.csv)")
        if not yol:
            return None
        try:
            shutil.copyfile(self.sonuc.csv, yol)
        except OSError as e:
            self._hata(_("CSV kaydedilemedi"), e)
            return None
        self._durum_yaz(_("Kaydedildi: %s") % yol)
        return yol
