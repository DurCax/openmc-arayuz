# -*- coding: utf-8 -*-
"""
kabuk.py -- Dalga 2 kabugunun gorsel parcalari (ust cubuk, onizleme paneli,
dogrulama seridi). Yerlesim maketlerden gelir: maketler/kabuk_*.png.

  ┌ menu ────────────────────────────────────────────────────────────────┐
  │ UstCubuk: [yeni ac kaydet | geri yinele] ad [tur] ozet Turu degistir… │
  │                                   [⌕ Komut ara Ctrl K]  [▶ Çalıştır]  │
  ├ KenarCubugu ─┬ sayfa (QScrollArea) ──────────┬ OnizlemePaneli ────────┤
  ├──────────────┴───────────────────────────────┴───────────────────────┤
  │ DogrulamaSeridi: ✓ Doğrulama: hata yok · sonraki adım …  veri denetle │
  └──────────────────────────────────────────────────────────────────────┘

Renk ve aralik YALNIZCA tasarim tokenlarindan (arayuz/tasarim/tokenlar.py)
gelir; burada #rrggbb yazilmaz.
"""

from PySide6 import QtCore, QtGui, QtWidgets

from arayuz import bilesenler as b
from arayuz.tasarim import tokenlar
from arayuz.bilesenler.kenar_cubugu import ROL_ANAHTAR
from arayuz.tasarim.ikon import ikon_bagla
from cekirdek import surum
from cekirdek.ceviri import _

A = tokenlar.ARALIK
B = tokenlar.BOYUT

# Kenar cubugu: (anahtar, ikon, grup) -- anahtarlar uygunluk.SEKMELER sirasinda.
GEZINME_IKONLARI = {
    "malzemeler": "flask-conical", "parcalar": "cylinder", "demet": "grid-3x3",
    "kor": "hexagon", "ayarlar": "sliders-horizontal", "calistir": "play",
    "analiz": "activity", "tukenme": "hourglass",
}
GEZINME_GRUPLARI = (("malzemeler", "Model"), ("ayarlar", "Hesap"), ("analiz", "Sonuç"))

# sekme_isaretleri() isareti -> KenarCubugu durumu
ISARET_DURUMU = {"!": "hata", "•": "eksik", "✓": "tamam", "": None}
DURUM_ISARETI = {d: i for i, d in ISARET_DURUMU.items() if d}

ONIZLEME_GENISLIGI = 360
ONIZLEME_DAR = 44
ONIZLEME_AYARI = "kabuk/onizleme_acik"
BOLUCU_AYARI = "kabuk/bolucu"
KENAR_AYARI = "kabuk/kenar_dar"


def kenar_ipucu(kenar, anahtar, metin):
    """KenarCubugu ogesinin ipucunu (durum aciklamasi) gunceller."""
    for i in range(kenar.liste.count()):
        oge = kenar.liste.item(i)
        if oge.data(ROL_ANAHTAR) == anahtar:
            oge.setToolTip(metin)
            return True
    return False


def dikey_ayirici():
    f = QtWidgets.QFrame()
    f.setFrameShape(QtWidgets.QFrame.VLine)
    f.setFixedHeight(20)
    return f


def ikon_etiketi(ad, renk, boyut=None):
    """Tiklanmayan, yalnizca gosterim amacli ikon (tema ile yenilenir)."""
    d = QtWidgets.QToolButton()
    d.setFocusPolicy(QtCore.Qt.NoFocus)
    d.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
    d.setProperty("tur", "ikon")
    ikon_bagla(d, ad, renk, boyut or B["ikon"])
    return d


def eylem_dugmesi(eylem, ikon_adi):
    """QAction'i ikonlu bir arac dugmesine baglar (metin ipucunda kalir)."""
    ipucu = eylem.text().replace("&", "").rstrip("…")
    kisayol = eylem.shortcut().toString(QtGui.QKeySequence.NativeText)
    d = b.ikon_dugmesi(ikon_adi, "%s (%s)" % (ipucu, kisayol) if kisayol else ipucu)
    d.setDefaultAction(eylem)
    d.setToolButtonStyle(QtCore.Qt.ToolButtonIconOnly)
    d.setText("")
    ikon_bagla(d, ikon_adi, "metin_ikincil", B["ikon"])
    d.setToolTip("%s (%s)" % (ipucu, kisayol) if kisayol else ipucu)
    return d


class UstCubuk(QtWidgets.QFrame):
    """Ust serit: hizli eylemler, model kimligi, komut arama, birincil kosu."""

    komut_istendi = QtCore.Signal()
    kosu_istendi = QtCore.Signal()
    durdur_istendi = QtCore.Signal()

    def __init__(self, eylemler, parent=None):
        """eylemler: {"yeni","ac","kaydet","geri","yinele"} -> QAction."""
        super().__init__(parent)
        self.setObjectName("ustCubuk")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setFixedHeight(B["ust_cubuk"])
        self._kosuyor = False
        d = QtWidgets.QHBoxLayout(self)
        d.setContentsMargins(A["m"], 0, A["m"], 0)
        d.setSpacing(A["xs"])
        for ad, ikon_adi in (("yeni", "file-plus"), ("ac", "folder-open"), ("kaydet", "save")):
            d.addWidget(eylem_dugmesi(eylemler[ad], ikon_adi))
        d.addWidget(dikey_ayirici())
        for ad, ikon_adi in (("geri", "undo-2"), ("yinele", "redo-2")):
            d.addWidget(eylem_dugmesi(eylemler[ad], ikon_adi))
        d.addWidget(dikey_ayirici())
        d.addSpacing(A["s"])
        self._kimlik_kur(d)
        d.addStretch(1)
        self._arama_kur(d)
        d.addSpacing(A["s"])
        self.d_kosu = b.birincil_dugme(_("Çalıştır"), "play")
        self.d_kosu.clicked.connect(self._kosu_tiklandi)
        d.addWidget(self.d_kosu)

    def _kimlik_kur(self, d):
        self.model_adi = QtWidgets.QLabel("")
        self.model_adi.setObjectName("altBaslik")
        d.addWidget(self.model_adi)
        d.addSpacing(A["xs"])
        self.tur_rozeti = b.Rozet("", "notr")
        d.addWidget(self.tur_rozeti)
        self.model_ozet = QtWidgets.QLabel("")
        self.model_ozet.setObjectName("kucuk")
        self.model_ozet.setTextFormat(QtCore.Qt.RichText)
        self.model_ozet.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse
                                                | QtCore.Qt.LinksAccessibleByKeyboard)
        d.addSpacing(A["xs"])
        d.addWidget(self.model_ozet)
        d.addSpacing(A["xs"])
        self.d_tur = b.duz_dugme(_("Türü değiştir…"))
        self.d_tur.setToolTip(_("Kor türünü değiştirir (yalnızca bu modelde "
                                "kullanılabilen türler listelenir). Geri almak için Ctrl+Z."))
        d.addWidget(self.d_tur)

    def _arama_kur(self, d):
        self.komut_alani = QtWidgets.QPushButton(_("Komut ara…"))
        self.komut_alani.setObjectName("komutAlani")
        self.komut_alani.setToolTip(_("Komut paletini açar (Ctrl+K)"))
        ikon_bagla(self.komut_alani, "search", "metin_soluk")
        self.komut_alani.setFixedWidth(240)
        self.komut_alani.clicked.connect(self.komut_istendi)
        kisayol = QtWidgets.QLabel("Ctrl K")
        kisayol.setObjectName("kucuk")
        ic = QtWidgets.QHBoxLayout(self.komut_alani)
        ic.setContentsMargins(0, 0, A["s"], 0)
        ic.addStretch(1)
        ic.addWidget(kisayol)
        d.addWidget(self.komut_alani)

    # ------------------------------------------------------------------
    def model_ayarla(self, ad, tur, ozet_html, ipucu=""):
        self.model_adi.setText(ad)
        self.tur_rozeti.setText(tur)
        self.tur_rozeti.setVisible(bool(tur))
        self.model_ozet.setText(ozet_html)
        self.model_ozet.setToolTip(ipucu)

    def model_gorunur(self, gorunur):
        """Baslangic ekraninda model kimligi ve kosu dugmesi anlamsizdir."""
        for w in (self.tur_rozeti, self.model_ozet, self.d_tur):
            w.setVisible(bool(gorunur) and (w is not self.tur_rozeti
                                            or bool(self.tur_rozeti.text())))
        self.d_kosu.setEnabled(bool(gorunur) and not self._kosuyor)

    def kosu_durumu(self, kosuyor):
        """Kosu basladiginda birincil dugme Durdur'a doner."""
        self._kosuyor = bool(kosuyor)
        self.d_kosu.setText(_("Durdur") if kosuyor else _("Çalıştır"))
        ikon_bagla(self.d_kosu, "square" if kosuyor else "play", "vurgu_metin", B["ikon"])
        self.d_kosu.setEnabled(True)

    def kosu_izni(self, izin, aciklama):
        if not self._kosuyor:
            self.d_kosu.setEnabled(bool(izin))
        self.d_kosu.setToolTip(aciklama)

    def kosuyor_mu(self):
        return self._kosuyor

    def _kosu_tiklandi(self):
        (self.durdur_istendi if self._kosuyor else self.kosu_istendi).emit()


class OnizlemePaneli(QtWidgets.QFrame):
    """Onizleme + baslik satiri; daraltilinca yalniz ikon seridi kalir."""

    daraltildi = QtCore.Signal(bool)
    yenile_istendi = QtCore.Signal()

    def __init__(self, onizleme, parent=None):
        super().__init__(parent)
        self.setObjectName("onizlemePaneli")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self._dar = False
        self.onizleme = onizleme
        d = QtWidgets.QVBoxLayout(self)
        d.setContentsMargins(A["m"], A["s"], A["s"], A["s"])
        d.setSpacing(A["s"])
        ust = QtWidgets.QHBoxLayout()
        self.baslik = QtWidgets.QLabel(_("Önizleme"))
        self.baslik.setObjectName("altBaslik")
        ust.addWidget(self.baslik)
        ust.addStretch(1)
        self.d_yenile = b.ikon_dugmesi("refresh-cw", _("Önizlemeyi yenile (F6)"))
        self.d_yenile.clicked.connect(self.yenile_istendi)
        ust.addWidget(self.d_yenile)
        self.d_daralt = b.ikon_dugmesi("panel-right", _("Önizlemeyi daralt"))
        self.d_daralt.clicked.connect(lambda: self.daralt(not self._dar))
        ust.addWidget(self.d_daralt)
        self._ust = ust
        d.addLayout(ust)
        d.addWidget(onizleme, 1)
        self.olcu = QtWidgets.QLabel("")
        self.olcu.setObjectName("kucuk")
        d.addWidget(self.olcu)

    def dar_mi(self):
        return self._dar

    def daralt(self, dar=True):
        dar = bool(dar)
        self._dar = dar
        self.baslik.setVisible(not dar)
        self.d_yenile.setVisible(not dar)
        self.onizleme.setVisible(not dar)
        self.olcu.setVisible(not dar)
        self.d_daralt.setToolTip(_("Önizlemeyi aç") if dar else _("Önizlemeyi daralt"))
        ikon_bagla(self.d_daralt, "panel-left" if dar else "panel-right", "metin_ikincil")
        if dar:
            self.setFixedWidth(ONIZLEME_DAR)
        else:
            self.setMinimumWidth(260)
            self.setMaximumWidth(16777215)
        self.daraltildi.emit(dar)

    def olcu_ayarla(self, metin):
        self.olcu.setText(metin)


class DogrulamaSeridi(QtWidgets.QWidget):
    """Alt serit: dogrulama ozeti, ilk bulgu, sonraki adim, veri denetimi."""

    bulguya_git = QtCore.Signal()
    veri_denetle = QtCore.Signal()
    ozet_istendi = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        d = QtWidgets.QHBoxLayout(self)
        d.setContentsMargins(A["s"], 0, A["s"], 0)
        d.setSpacing(A["s"])
        self.durum_ikonu = ikon_etiketi("circle-check", "basari", 14)
        d.addWidget(self.durum_ikonu)
        self.ozet = QtWidgets.QLabel("")
        d.addWidget(self.ozet)
        self.rozet = b.Rozet("", "notr")
        self.rozet.setCursor(QtCore.Qt.PointingHandCursor)
        self.rozet.setToolTip(_("Doğrulama bulgularını göster"))
        d.addWidget(self.rozet)
        self.d_bulgu = b.baglanti_dugmesi(_("Bulguya git"))
        self.d_bulgu.clicked.connect(self.bulguya_git)
        self.d_bulgu.setVisible(False)
        d.addWidget(self.d_bulgu)
        self.ayirici = dikey_ayirici()
        d.addWidget(self.ayirici)
        self.ipucu = QtWidgets.QLabel("")
        self.ipucu.setObjectName("kucuk")
        d.addWidget(self.ipucu)
        d.addStretch(1)
        self.d_veri = b.baglanti_dugmesi(_("Veri kütüphanesini denetle"))
        self.d_veri.setToolTip(_("Modelin istediği her nüklidin cross_sections.xml "
                                 "içinde bulunup bulunmadığını denetler (yavaş, F5)."))
        self.d_veri.clicked.connect(self.veri_denetle)
        d.addWidget(self.d_veri)
        d.addWidget(dikey_ayirici())
        s = QtWidgets.QLabel("%s %s" % (surum.UYGULAMA_ADI, surum.surum()))
        s.setObjectName("kucuk")
        s.setToolTip(_("Uygulama sürümü (Yardım > Hakkında)"))
        d.addWidget(s)
        self.rozet.installEventFilter(self)

    def eventFilter(self, nesne, olay):                  # noqa: N802 (Qt adi)
        if nesne is self.rozet and olay.type() == QtCore.QEvent.MouseButtonPress:
            self.ozet_istendi.emit()
            return True
        return super().eventFilter(nesne, olay)

    def ayarla(self, seviye, ozet, rozet_metni, ilk_bulgu="", ipucu=""):
        """seviye: "basari" | "uyari" | "hata"."""
        ikon_adi = {"basari": "circle-check", "uyari": "triangle-alert",
                    "hata": "circle-x"}.get(seviye, "info")
        ikon_bagla(self.durum_ikonu, ikon_adi, seviye, 14)
        self.ozet.setText(ozet)
        self.rozet.setText(rozet_metni)
        self.rozet.tur_ayarla(seviye)
        self.d_bulgu.setVisible(bool(ilk_bulgu))
        self.d_bulgu.setToolTip(ilk_bulgu)
        self.ipucu.setText(ilk_bulgu or ipucu)
        self.ipucu.setVisible(bool(ilk_bulgu or ipucu))
        self.ayirici.setVisible(bool(ilk_bulgu or ipucu))
