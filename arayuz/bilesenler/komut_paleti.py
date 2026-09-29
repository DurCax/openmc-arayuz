# -*- coding: utf-8 -*-
"""
komut_paleti.py -- KomutPaleti: Ctrl+K ile acilan, eylemlerde bulanik arama.

    pal = KomutPaleti(pencere, eylemler)     # eylemler: QAction listesi ya da
                                             # liste donduren islev (her aciliste okunur)
    pal.ac();  pal.kapat();  pal.sonuclar() -> gorunen metinler
    bulanik_puan("clstr", "Çalıştır") -> sayi | None

Arama Turkce harfleri katlar (ç→c, ı/İ→i, ş→s ...): "calistir" Çalıştır'i bulur.
Yalniz etkin, metni olan eylemler listelenir; menu anahtar isareti (&) ve
"…" gosterimde temizlenir. Ok tuslari arama kutusundayken listeyi gezer,
Enter calistirir, Esc kapatir. Palet pencerenin cocugudur (ust duzey degil).
"""

from PySide6 import QtCore, QtGui, QtWidgets

from arayuz.tasarim import tokenlar
from arayuz.tasarim.ikon import ikon_bagla
from cekirdek.ceviri import _

A = tokenlar.ARALIK
ROL_EYLEM = QtCore.Qt.UserRole + 1
ROL_KISAYOL = QtCore.Qt.UserRole + 2
_GENISLIK = 560
_EN_COK_SATIR = 9
_KATLAMA = str.maketrans("çğıöşüÇĞİÖŞÜâîû", "cgiosucgiosuaiu")


def _katla(metin):
    return metin.translate(_KATLAMA).lower()


def bulanik_puan(sorgu, metin):
    """Sorgu harfleri metinde SIRAYLA geciyorsa puan (buyuk = iyi), yoksa None.
    Bitisik eslesme, kelime basi ve onek odullendirilir."""
    s, m = _katla(sorgu.strip()), _katla(metin)
    if not s:
        return 0.0
    if m.startswith(s):
        return 1000.0 - len(m)
    konum = m.find(s)
    if konum >= 0:
        return 500.0 - konum - len(m) * 0.1
    puan, j, onceki = 0.0, 0, -2
    for harf in s:
        j = m.find(harf, j)
        if j < 0:
            return None
        puan += 5.0 if j == onceki + 1 else 1.0
        if j == 0 or not m[j - 1].isalnum():
            puan += 3.0
        onceki = j
        j += 1
    return puan - len(m) * 0.05


def eylem_metni(eylem):
    return eylem.text().replace("&&", "\x00").replace("&", "").replace("\x00", "&").strip()


class _Temsilci(QtWidgets.QStyledItemDelegate):
    """Satir: ikon + metin (varsayilan) ve sagda soluk kisayol."""

    def paint(self, ressam, secenek, dizin):
        super().paint(ressam, secenek, dizin)
        kisayol = dizin.data(ROL_KISAYOL)
        if not kisayol:
            return
        from arayuz import tema
        ressam.save()
        ressam.setPen(QtGui.QColor(tema.renk("metin_soluk")))
        ressam.drawText(secenek.rect.adjusted(0, 0, -A["m"], 0),
                        QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight, kisayol)
        ressam.restore()


class KomutPaleti(QtWidgets.QFrame):
    calistirildi = QtCore.Signal(object)

    def __init__(self, pencere, eylemler=(), kisayol="Ctrl+K"):
        super().__init__(pencere)
        self.setObjectName("komutPaleti")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self._eylemler = eylemler
        self.setFixedWidth(_GENISLIK)
        d = QtWidgets.QVBoxLayout(self)
        d.setContentsMargins(0, 0, 0, A["xs"])
        d.setSpacing(0)
        ust = QtWidgets.QHBoxLayout()
        ust.setContentsMargins(A["m"], 0, 0, 0)
        ust.setSpacing(0)
        buyutec = QtWidgets.QToolButton()
        buyutec.setFocusPolicy(QtCore.Qt.NoFocus)
        buyutec.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        buyutec.setStyleSheet("border: none; background: transparent;")
        ikon_bagla(buyutec, "search", "metin_soluk", tokenlar.BOYUT["ikon_buyuk"])
        ust.addWidget(buyutec)
        self.arama = QtWidgets.QLineEdit()
        self.arama.setPlaceholderText(_("Komut ara…"))
        self.arama.setAccessibleName(_("Komut ara"))
        self.arama.textChanged.connect(self._doldur)
        self.arama.installEventFilter(self)
        ust.addWidget(self.arama, 1)
        d.addLayout(ust)
        self.liste = QtWidgets.QListWidget()
        self.liste.setAccessibleName(_("Komutlar"))
        self.liste.setItemDelegate(_Temsilci(self.liste))
        self.liste.setFocusPolicy(QtCore.Qt.NoFocus)
        self.liste.itemActivated.connect(self._calistir)
        self.liste.itemClicked.connect(self._calistir)
        d.addWidget(self.liste)
        self.bos = QtWidgets.QLabel(_("Eşleşen komut yok"))
        self.bos.setObjectName("kucuk")
        self.bos.setAlignment(QtCore.Qt.AlignCenter)
        self.bos.setContentsMargins(0, A["m"], 0, A["m"])
        d.addWidget(self.bos)
        golge = QtWidgets.QGraphicsDropShadowEffect(self)
        bulanik, dy, opak = tokenlar.YUKSELTI[3]
        golge.setBlurRadius(bulanik)
        golge.setOffset(0, dy)
        from arayuz import tema
        renk = QtGui.QColor(tema.renk("golge"))
        renk.setAlpha(opak)
        golge.setColor(renk)
        self.setGraphicsEffect(golge)
        self.hide()
        if kisayol:
            # Ebeveyn PENCERE olmali: gizli paletin kendi kisayolu tetiklenmez
            # (olculdu). Palet silinince kisayol da silinir -- silinmis palete
            # sinyal gitmesin (palet yenilenirse eski kisayol kalmasin).
            self.kisayol = QtGui.QShortcut(QtGui.QKeySequence(kisayol), pencere)
            self.kisayol.setContext(QtCore.Qt.WindowShortcut)
            self.kisayol.activated.connect(self.ac)
            self.destroyed.connect(self.kisayol.deleteLater)

    # ------------------------------------------------------------------
    def eylemler_ayarla(self, eylemler):
        self._eylemler = eylemler

    def _tum_eylemler(self):
        kaynak = self._eylemler() if callable(self._eylemler) else self._eylemler
        return [e for e in kaynak if e.isEnabled() and eylem_metni(e) and not e.isSeparator()]

    def ac(self):
        self.arama.clear()
        self._doldur("")
        p = self.parentWidget()
        self.adjustSize()
        self.move(max(0, (p.width() - self.width()) // 2), int(p.height() * 0.12))
        self.show()
        self.raise_()
        self.arama.setFocus()

    def kapat(self):
        self.hide()
        p = self.parentWidget()
        if p is not None:
            p.setFocus()

    def sonuclar(self):
        return [self.liste.item(i).text() for i in range(self.liste.count())]

    def _doldur(self, sorgu):
        puanli = []
        for sira, e in enumerate(self._tum_eylemler()):
            puan = bulanik_puan(sorgu, eylem_metni(e))
            if puan is not None:
                puanli.append((-puan, sira, e))
        puanli.sort(key=lambda t: (t[0], t[1]))
        self.liste.clear()
        for _p, _s, e in puanli:
            o = QtWidgets.QListWidgetItem(e.icon(), eylem_metni(e))
            o.setData(ROL_EYLEM, e)
            o.setData(ROL_KISAYOL, e.shortcut().toString(QtGui.QKeySequence.NativeText))
            self.liste.addItem(o)
        if self.liste.count():
            self.liste.setCurrentRow(0)
        satir = self.liste.sizeHintForRow(0) if self.liste.count() else 0
        self.liste.setFixedHeight(min(self.liste.count(), _EN_COK_SATIR) * satir + A["s"])
        self.liste.setVisible(self.liste.count() > 0)
        self.bos.setVisible(self.liste.count() == 0)
        if self.isVisible():
            self.adjustSize()

    def _calistir(self, oge):
        if oge is None:
            return
        e = oge.data(ROL_EYLEM)
        self.kapat()
        e.trigger()
        self.calistirildi.emit(e)

    def eventFilter(self, nesne, olay):                  # noqa: N802
        if nesne is self.arama and olay.type() == QtCore.QEvent.KeyPress:
            tus = olay.key()
            if tus in (QtCore.Qt.Key_Down, QtCore.Qt.Key_Up):
                n = self.liste.count()
                if n:
                    adim = 1 if tus == QtCore.Qt.Key_Down else -1
                    self.liste.setCurrentRow((self.liste.currentRow() + adim) % n)
                return True
            if tus in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                self._calistir(self.liste.currentItem())
                return True
            if tus == QtCore.Qt.Key_Escape:
                self.kapat()
                return True
        return super().eventFilter(nesne, olay)
