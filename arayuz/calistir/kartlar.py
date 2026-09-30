# -*- coding: utf-8 -*-
"""
kartlar.py -- Calistir sayfasinin kosu, sonuc ve ayrintili cikti kartlari.

    KosuKarti        : Calistir / Durdur / ilerleme + is parcacigi + kosu dizini
    SonucKarti       : kritiklik yorumu, ozet metni, (sabit kaynakta) tally'ler
    AyrintiCekmecesi : katlanir ham OpenMC gunlugu + tam sonuc metni
                       (maket: sonuclar_cekmece_*; baslik altinda satir sayisi)

Kartlar yalnizca widget kurar; kosu akisi arayuz/sekme_calistir.py'dedir. Renk,
aralik ve yazi boyutu tasarim tokenlarindan gelir.
"""

from PySide6 import QtCore, QtGui, QtWidgets

from arayuz import bilesenler as b
from arayuz.ortak import GelismisBolum, tamsayi
from arayuz.tasarim import tokenlar
from cekirdek.ceviri import _

A = tokenlar.ARALIK
_ES_ARALIKLI_PT = 8.5
_OZET_PT = 9.0
_TALLY_EN_AZ = 180
_GUNLUK_EN_AZ = 200
_SONUC_EN_AZ = 160
_GUNLUK_EN_COK_BLOK = 5000
_IS_PARCACIGI_EN_AZ_GENISLIK = 70


def es_aralikli(w, boyut=_ES_ARALIKLI_PT):
    """Widget'in yazi tipini es aralikli yapar (gunluk ve tablolar)."""
    f = w.font()
    f.setFamily("monospace")
    f.setStyleHint(QtGui.QFont.StyleHint.Monospace)
    f.setPointSizeF(boyut)
    w.setFont(f)


def _salt_okunur_metin(en_az_yukseklik):
    w = QtWidgets.QPlainTextEdit()
    w.setReadOnly(True)
    w.setMinimumHeight(en_az_yukseklik)
    w.setProperty("mono", True)
    es_aralikli(w)
    return w


class KisaltilanYol(QtWidgets.QLabel):
    """Uzun yolu ORTADAN kisaltarak cizen etiket (tam yol text() ve ipucunda).

    Mutlak kosu dizini 1280 genislikte sayfayi yatay kaydiriyordu; en az
    genisligi kucuk tutulur, sigmayan metin "…" ile kisaltilir (kirpilmaz).
    """

    def __init__(self, metin="", parent=None):
        super().__init__(metin, parent)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                           QtWidgets.QSizePolicy.Preferred)

    def minimumSizeHint(self):
        return QtCore.QSize(0, super().minimumSizeHint().height())

    def gorunen_metin(self):
        """Etiket genisligine sigan (gerekirse ortadan kisaltilmis) metin."""
        return self.fontMetrics().elidedText(self.text(), QtCore.Qt.ElideMiddle,
                                             max(self.contentsRect().width(), 0))

    def paintEvent(self, _olay):
        boyaci = QtGui.QPainter(self)
        boyaci.setPen(self.palette().color(self.foregroundRole()))
        boyaci.drawText(self.contentsRect(), int(self.alignment()), self.gorunen_metin())
        boyaci.end()


class KosuKarti(b.Kart):
    """Kosu dugmeleri, ilerleme, kosu ayarlari ve kapi mesaji."""

    def __init__(self, parent=None):
        self.d_klasor = b.duz_dugme(_("Klasörü aç"), "folder-open")
        self.d_klasor.setEnabled(False)
        super().__init__(_("Koşu"), eylem=self.d_klasor, parent=parent)
        self.d_calistir = b.birincil_dugme(_("Çalıştır"), "play",
                                           _("Modeli OpenMC ile çalıştırır (F9)."))
        self.d_durdur = b.ikincil_dugme(_("Durdur"), "square")
        self.d_durdur.setEnabled(False)
        self.ilerleme = QtWidgets.QProgressBar()
        self.ilerleme.setProperty("metinli", True)
        self.ilerleme.setTextVisible(True)
        self.ilerleme.setRange(0, 1)
        self.ilerleme.setValue(0)
        self.kapi_etiket = QtWidgets.QLabel("-")
        self.kapi_etiket.setWordWrap(True)
        self.kapi_etiket.setObjectName("kucuk")
        ust = QtWidgets.QHBoxLayout()
        ust.setSpacing(A["s"])
        ust.addWidget(self.d_calistir)
        ust.addWidget(self.d_durdur)
        ust.addWidget(self.ilerleme, 1)
        self.govde.addLayout(ust)
        self.govde.addLayout(self._ayar_satiri())
        self.ekle(self.kapi_etiket)

    def _ayar_satiri(self):
        """Is parcacigi ve kosu dizini satiri (spec["calistirma"])."""
        self.is_parcacigi = tamsayi(8, 1, 512, 1)
        self.is_parcacigi.setMinimumWidth(_IS_PARCACIGI_EN_AZ_GENISLIK)
        n_cekirdek = QtCore.QThread.idealThreadCount()
        self.is_parcacigi.setToolTip(
            _("OpenMP iş parçacığı sayısı (openmc -s N). Bu bilgisayarda %d mantıksal "
              "çekirdek var; tüm çekirdekleri kullanmak arayüzü yavaşlatabilir.")
            % max(n_cekirdek, 1))
        self.kosu_dizini = QtWidgets.QLineEdit()
        self.kosu_dizini.setPlaceholderText("kosu")
        self.kosu_dizini.setToolTip(
            _("Koşu dosyalarının yazılacağı dizin. Göreli yol proje dosyasının "
              "yanına yazılır; her koşuda içi temizlenir."))
        self.dizin_yolu = KisaltilanYol()
        self.dizin_yolu.setObjectName("kucuk")
        satir = QtWidgets.QHBoxLayout()
        satir.setSpacing(A["s"])
        for etiket, w, esnek in ((_("İş parçacığı:"), self.is_parcacigi, 0),
                                 (_("Koşu dizini:"), self.kosu_dizini, 1)):
            e = QtWidgets.QLabel(etiket)
            e.setObjectName("ikincil")
            satir.addWidget(e)
            satir.addWidget(w, esnek)
        satir.addWidget(self.dizin_yolu, 2)
        return satir


class SonucKarti(b.Kart):
    """Kritiklik yorumu, ozet metni ve (sabit kaynakta) tally tablolari."""

    def __init__(self, parent=None):
        super().__init__(_("Sonuç"), parent=parent)
        self.durum_etiket = QtWidgets.QLabel("")
        self.durum_etiket.setWordWrap(True)
        self.durum_etiket.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.ozet_etiket = QtWidgets.QLabel("")
        self.ozet_etiket.setWordWrap(True)
        self.ozet_etiket.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        es_aralikli(self.ozet_etiket, _OZET_PT)
        self.tally_baslik = QtWidgets.QLabel(_("Tally sonuçları"))
        self.tally_baslik.setObjectName("altBaslik")
        self.tally_metin = _salt_okunur_metin(_TALLY_EN_AZ)
        for w in (self.durum_etiket, self.ozet_etiket, self.tally_baslik,
                  self.tally_metin):
            self.ekle(w)


class AyrintiCekmecesi(b.Kart):
    """Katlanir ayrintili cikti: ham OpenMC gunlugu ve tam sonuc metni."""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.log = _salt_okunur_metin(_GUNLUK_EN_AZ)
        self.log.setMaximumBlockCount(_GUNLUK_EN_COK_BLOK)
        self.sonuc_metin = _salt_okunur_metin(_SONUC_EN_AZ)
        self.d_kopyala = b.duz_dugme(_("Kopyala"), "copy")
        self.ayrinti = GelismisBolum("calistir_ayrinti", _("Ayrıntılı çıktı"))
        self.satir_etiketi = QtWidgets.QLabel("")
        self.satir_etiketi.setObjectName("kucuk")
        self.ekle(self.ayrinti)
        self.ekle(self.satir_etiketi)
        self.ayrinti.ekle(QtWidgets.QLabel(_("OpenMC çıktısı")))
        self.ayrinti.ekle(self.log)
        self.ayrinti.ekle(self.d_kopyala)
        self.ayrinti.ekle(QtWidgets.QLabel(
            _("Tam sonuç metni (statepoint ve tüm tally tabloları)")))
        self.ayrinti.ekle(self.sonuc_metin)
        self.log.blockCountChanged.connect(self._satir_sayisi_yaz)
        self._satir_sayisi_yaz()

    def _satir_sayisi_yaz(self, *_a):
        """Baslik altindaki "OpenMC gunlugu · N satir" ozeti."""
        n = self.log.blockCount() if self.log.toPlainText() else 0
        self.satir_etiketi.setText(_("OpenMC günlüğü · %d satır") % n)
