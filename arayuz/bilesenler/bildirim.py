# -*- coding: utf-8 -*-
"""
bildirim.py -- Bildirim (toast): pencerenin sag altinda, yigilan, kendiliginden
kapanan kisa mesaj.

    from arayuz.bilesenler import bildir
    bildir(pencere, _("Model kaydedildi"), "basari")            # 4 sn sonra kapanir
    bildir(pencere, _("2 uyarı var"), "uyari", sure=0,          # sure=0: elle kapanir
           eylem_metni=_("Bulguya git"), eylem=lambda: ...)

Bildirimler pencerenin COCUGU (ust duzey pencere degil): odak calmaz,
offscreen ekran goruntusune girer, pencere tasininca birlikte gider. Konum
pencerenin cocuklari taranarak hesaplanir (ayri durum tutulmaz); pencere
boyutu degisince _Konumlayici yeniden dizer. Altta kalici bir serit varsa
pencere.setProperty(ALT_PAYI_OZELLIGI, yukseklik) ile bildirimler onun ustune alinir.
"""

import itertools

from PySide6 import QtCore, QtGui, QtWidgets

from arayuz.bilesenler.dugme import baglanti_dugmesi, ikon_dugmesi
from arayuz.tasarim import tokenlar
from arayuz.tasarim.ikon import ikon_bagla
from arayuz.tasarim.stil import durum_ayarla
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici("arayuz.bilesenler.bildirim")

A = tokenlar.ARALIK
TUR_IKONU = {"basari": "circle-check", "uyari": "triangle-alert", "hata": "circle-x",
             "bilgi": "info"}
VARSAYILAN_SURE = 4000
_EN_COK = 4          # ayni anda gorunen bildirim; fazlasinda en eskisi kapanir
# Pencerenin altinda kalici bir serit varsa (dogrulama seridi) bildirimler
# onun USTUNDE dursun: pencere.setProperty(ALT_PAYI_OZELLIGI, serit_yuksekligi)
ALT_PAYI_OZELLIGI = "bildirimAltPayi"
_SIRA = itertools.count()   # olusma sirasi: raise_() cocuk sirasini degistirir


class Bildirim(QtWidgets.QFrame):
    kapandi = QtCore.Signal()

    def __init__(self, pencere, metin, tur="bilgi", sure=VARSAYILAN_SURE, baslik=None,
                 eylem_metni=None, eylem=None):
        super().__init__(pencere)
        if tur not in TUR_IKONU:
            raise ValueError("bilinmeyen bildirim turu: %r" % (tur,))
        self.setObjectName("bildirim")
        self.sira = next(_SIRA)
        durum_ayarla(self, "tur", tur)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setFixedWidth(tokenlar.BOYUT["bildirim_genislik"])
        self._kur_icerik(metin, tur, baslik, eylem_metni, eylem)
        golge = QtWidgets.QGraphicsDropShadowEffect(self)
        bulanik, dy, opak = tokenlar.YUKSELTI[2]
        golge.setBlurRadius(bulanik)
        golge.setOffset(0, dy)
        from arayuz import tema
        renk = QtGui.QColor(tema.renk("golge"))
        renk.setAlpha(opak)
        golge.setColor(renk)
        self.setGraphicsEffect(golge)
        self.setAccessibleName(" ".join(m for m in (baslik, metin) if m))
        self.setAccessibleDescription(tur)
        self._sayac = QtCore.QTimer(self)
        self._sayac.setSingleShot(True)
        self._sayac.timeout.connect(self.kapat)
        if sure and sure > 0:
            self._sayac.start(int(sure))

    def _kur_icerik(self, metin, tur, baslik, eylem_metni, eylem):
        d = QtWidgets.QHBoxLayout(self)
        d.setContentsMargins(A["m"], A["m"], A["s"], A["m"])
        d.setSpacing(A["m"])
        ik = QtWidgets.QToolButton()
        ik.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        ik.setFocusPolicy(QtCore.Qt.NoFocus)
        ik.setStyleSheet("border: none; background: transparent; padding: 0;")
        ikon_bagla(ik, TUR_IKONU[tur], tur, tokenlar.BOYUT["ikon_buyuk"])
        d.addWidget(ik, 0, QtCore.Qt.AlignTop)
        metinler = QtWidgets.QVBoxLayout()
        metinler.setSpacing(2)
        if baslik:
            b = QtWidgets.QLabel(baslik)
            b.setObjectName("altBaslik")
            metinler.addWidget(b)
        self.etiket = QtWidgets.QLabel(metin)
        self.etiket.setWordWrap(True)
        metinler.addWidget(self.etiket)
        if eylem_metni and eylem:
            e = baglanti_dugmesi(eylem_metni)
            e.clicked.connect(eylem)
            e.clicked.connect(self.kapat)
            metinler.addWidget(e, 0, QtCore.Qt.AlignLeft)
        d.addLayout(metinler, 1)
        x = ikon_dugmesi("x", _("Kapat"), boyut=14, renk="metin_soluk")
        x.clicked.connect(self.kapat)
        d.addWidget(x, 0, QtCore.Qt.AlignTop)

    def kapat(self):
        if self.property("_kapandi"):
            return
        self.setProperty("_kapandi", True)
        self._sayac.stop()
        self.hide()
        self.kapandi.emit()
        pencere = self.parentWidget()
        self.deleteLater()
        if pencere is not None:
            QtCore.QTimer.singleShot(0, lambda: yeniden_diz(pencere))


class _Konumlayici(QtCore.QObject):
    """Pencere boyutu degisince bildirimleri yeniden dizer."""

    def eventFilter(self, nesne, olay):              # noqa: N802 (Qt adi)
        if olay.type() == QtCore.QEvent.Resize:
            yeniden_diz(nesne)
        return False


def _acik_bildirimler(pencere):
    acik = [b for b in pencere.findChildren(Bildirim, options=QtCore.Qt.FindDirectChildrenOnly)
            if not b.property("_kapandi")]
    return sorted(acik, key=lambda b: b.sira)


def yeniden_diz(pencere):
    """Bildirimleri sag alttan yukari dogru yigar (en yenisi altta)."""
    try:
        acik = _acik_bildirimler(pencere)
    except RuntimeError:          # pencere silinmis: dizilecek bir sey yok
        _log.debug("yeniden_diz: pencere silinmis olabilir", exc_info=True)
        return
    alt = pencere.height() - A["l"] - int(pencere.property(ALT_PAYI_OZELLIGI) or 0)
    # statusBar() CAGRILMAZ: durum cubugu yoksa onu yaratirdi.
    durum = pencere.findChild(QtWidgets.QStatusBar, options=QtCore.Qt.FindDirectChildrenOnly)
    if durum is not None and durum.isVisible():
        alt -= durum.height()
    for b in reversed(acik):
        b.adjustSize()
        y = alt - b.height()
        b.move(pencere.width() - b.width() - A["l"], y)
        b.raise_()
        alt = y - A["s"]


def bildir(pencere, metin, tur="bilgi", sure=VARSAYILAN_SURE, baslik=None,
           eylem_metni=None, eylem=None):
    """Pencereye bildirim ekler ve dondurur. sure ms (0: elle kapanir)."""
    if not isinstance(pencere, QtWidgets.QWidget):
        raise ValueError("bildir(): pencere bir QWidget olmali, %r verildi" % (pencere,))
    if pencere.findChild(_Konumlayici, "_bildirimKonumlayici") is None:
        k = _Konumlayici(pencere)
        k.setObjectName("_bildirimKonumlayici")
        pencere.installEventFilter(k)
    acik = _acik_bildirimler(pencere)
    for eski in acik[:max(0, len(acik) - _EN_COK + 1)]:
        eski.kapat()
    b = Bildirim(pencere, metin, tur, sure, baslik, eylem_metni, eylem)
    b.show()
    yeniden_diz(pencere)
    return b
