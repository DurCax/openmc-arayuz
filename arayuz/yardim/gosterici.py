# -*- coding: utf-8 -*-
"""
 arayuz/yardim/gosterici.py  --  uygulama ici kilavuz penceresi (cevrimdisi)

 Sol: icindekiler (bolum ve alt bolum basliklari). Sag: QTextBrowser (Qt'nin
 Markdown destegiyle kurulan belge, belge.py). Ust: arama kutusu (Enter/F3
 sonraki, Shift+F3 onceki; butun eslesmeler vurgulanir). Kilavuzun dili
 arayuz dilidir (cekirdek.ceviri.etkin_dil); EN bolumu eksikse TR'si
 gosterilir, ustte uyari seridi cikar ve durum loglanir.

 Pencere tektir (etkin_gosterici); ac() onu yeniden kullanir, dil degistiyse
 yeniden yukler. Baglantilar: "#kimlik" -> capa; http(s) ve yerel dosya ->
 sistemin varsayilan uygulamasi (QDesktopServices).
"""

import shiboken6
from PySide6 import QtCore, QtGui, QtWidgets

from arayuz.tasarim import tokenlar
from arayuz.yardim import belge as _belge
from arayuz.yardim import kaynak
from cekirdek import ceviri
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

A = tokenlar.ARALIK
_ICINDEKILER_SEVIYESI = 2           # H1 ve H2 basliklari icindekilerde
_BASLANGIC_BOYUTU = (1100, 760)
_durum = {"gosterici": None}


def etkin_gosterici():
    """Acik (silinmemis) kilavuz penceresi; yoksa None."""
    g = _durum["gosterici"]
    if g is not None and not shiboken6.isValid(g):     # C++ nesnesi silinmis
        g = _durum["gosterici"] = None
    return g


def gosterici_al(ust=None):
    """Tek kilavuz penceresi (gerekirse kurar)."""
    g = etkin_gosterici()
    if g is None:
        g = _durum["gosterici"] = KilavuzPenceresi(ust)
    return g


class KilavuzPenceresi(QtWidgets.QWidget):
    """Kullanim kilavuzu penceresi. yukle(dil) -> bolume_git(kimlik) / ara(metin)."""

    def __init__(self, ust=None):
        super().__init__(ust, QtCore.Qt.Window)
        self.setObjectName("kilavuzPenceresi")
        self.setWindowTitle(_("Kullanım kılavuzu"))
        self.resize(*_BASLANGIC_BOYUTU)
        self.dil = None
        self.dizin = None
        self.klv = None
        self._konum = {}
        self._belge = None
        self._kur_arayuz()
        self._kisayollar()

    # ------------------------------------------------------------------
    def _kur_arayuz(self):
        kok = QtWidgets.QVBoxLayout(self)
        kok.setContentsMargins(A["m"], A["m"], A["m"], A["m"])
        kok.setSpacing(A["s"])
        kok.addWidget(self._arama_satiri())
        self.serit = QtWidgets.QLabel()
        self.serit.setObjectName("ikincil")
        self.serit.setWordWrap(True)
        self.serit.hide()
        kok.addWidget(self.serit)
        bolucu = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.icindekiler = QtWidgets.QTreeWidget()
        self.icindekiler.setHeaderHidden(True)
        self.icindekiler.setAccessibleName(_("İçindekiler"))
        self.icindekiler.itemActivated.connect(self._icindekiler_secildi)
        self.icindekiler.itemClicked.connect(self._icindekiler_secildi)
        self.tarayici = QtWidgets.QTextBrowser()
        self.tarayici.setOpenLinks(False)
        self.tarayici.setAccessibleName(_("Kılavuz metni"))
        self.tarayici.anchorClicked.connect(self._baglanti)
        bolucu.addWidget(self.icindekiler)
        bolucu.addWidget(self.tarayici)
        bolucu.setStretchFactor(1, 1)
        bolucu.setSizes([300, 800])
        kok.addWidget(bolucu, 1)

    def _arama_satiri(self):
        w = QtWidgets.QWidget()
        d = QtWidgets.QHBoxLayout(w)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(A["s"])
        self.arama = QtWidgets.QLineEdit()
        self.arama.setPlaceholderText(_("Kılavuzda ara…"))
        self.arama.setClearButtonEnabled(True)
        self.arama.setAccessibleName(_("Kılavuzda ara"))
        self.arama.returnPressed.connect(lambda: self.ara(self.arama.text()))
        self.onceki = QtWidgets.QPushButton(_("Önceki"))
        self.onceki.clicked.connect(lambda: self.ara(self.arama.text(), geri=True))
        self.sonraki = QtWidgets.QPushButton(_("Sonraki"))
        self.sonraki.clicked.connect(lambda: self.ara(self.arama.text()))
        self.sonuc = QtWidgets.QLabel()
        self.sonuc.setObjectName("ikincil")
        for x in (self.arama, self.onceki, self.sonraki, self.sonuc):
            d.addWidget(x, 1 if x is self.arama else 0)
        return w

    def _kisayollar(self):
        for dizi, islev in ((QtGui.QKeySequence.Find, self._aramaya_odaklan),
                            (QtGui.QKeySequence.FindNext, lambda: self.ara(self.arama.text())),
                            (QtGui.QKeySequence.FindPrevious,
                             lambda: self.ara(self.arama.text(), geri=True)),
                            (QtGui.QKeySequence.Close, self.close)):
            k = QtGui.QShortcut(dizi, self)
            k.activated.connect(islev)

    def _aramaya_odaklan(self):
        self.arama.setFocus()
        self.arama.selectAll()

    # ------------------------------------------------------------------
    def yukle(self, dil, dizin=None):
        """Kilavuzu dilde yukler. kaynak.KilavuzYok disariya gecer."""
        klv = kaynak.kilavuz(dil, dizin=dizin)
        belge, konum = _belge.belge_kur(klv, self)
        self.tarayici.setDocument(belge)
        if self._belge is not None:
            self._belge.deleteLater()
        self._belge, self._konum, self.klv = belge, konum, klv
        self.dil, self.dizin = klv.dil, dizin
        self._icindekileri_kur()
        self._serit_guncelle(klv)
        self.arama.clear()
        self.sonuc.clear()
        return klv

    def _serit_guncelle(self, klv):
        if klv.eksik:
            liste = ", ".join(klv.eksik)
            _log.warning("kilavuz: %s dilinde eksik bolumler TR'den gosteriliyor: %s",
                         klv.dil, liste)
            self.serit.setText(_("Bu bölümlerin bu dildeki çevirisi henüz yok; Türkçesi "
                                 "gösteriliyor: {liste}").format(liste=liste))
            self.serit.show()
        else:
            self.serit.hide()
        if klv.yedek_resimler:
            _log.info("kilavuz: %d ekran goruntusu TR'den: %s", len(klv.yedek_resimler),
                      ", ".join(klv.yedek_resimler))

    def _icindekileri_kur(self):
        self.icindekiler.clear()
        ust = None
        for blok in _belge.baslik_bloklari(self._belge):
            seviye = blok.blockFormat().headingLevel()
            if seviye > _ICINDEKILER_SEVIYESI:
                continue
            oge = QtWidgets.QTreeWidgetItem([blok.text()])
            oge.setData(0, QtCore.Qt.UserRole, blok.blockNumber())
            if seviye == 1 or ust is None:
                self.icindekiler.addTopLevelItem(oge)
                ust = oge
            else:
                ust.addChild(oge)
        self.icindekiler.expandToDepth(0)

    def _icindekiler_secildi(self, oge, _sutun=0):
        no = oge.data(0, QtCore.Qt.UserRole)
        if no is not None:
            self._bloka_git(self._belge.findBlockByNumber(no))

    def _bloka_git(self, blok):
        y = self._belge.documentLayout().blockBoundingRect(blok).top()
        self.tarayici.verticalScrollBar().setValue(int(y))
        imlec = QtGui.QTextCursor(blok)
        self.tarayici.setTextCursor(imlec)
        self.tarayici.verticalScrollBar().setValue(int(y))

    # ------------------------------------------------------------------
    def capa_blogu(self, kimlik):
        """Kimligin baslik blogu (yoksa None)."""
        no = self._konum.get(kimlik)
        return None if no is None else self._belge.findBlockByNumber(no)

    def bolume_git(self, kimlik):
        """Capaya kaydirir ve icindekilerde secer. Kimlik yoksa False."""
        blok = self.capa_blogu(kimlik)
        if blok is None:
            return False
        self._bloka_git(blok)
        self._icindekilerde_sec(blok.blockNumber())
        return True

    def _icindekilerde_sec(self, no):
        en_yakin = None
        it = QtWidgets.QTreeWidgetItemIterator(self.icindekiler)
        while it.value():
            oge = it.value()
            if oge.data(0, QtCore.Qt.UserRole) <= no:
                en_yakin = oge
            it += 1
        if en_yakin is not None:
            self.icindekiler.setCurrentItem(en_yakin)

    def ara(self, metin, geri=False):
        """Metni arar (dongusel); butun eslesmeleri vurgular. Eslesme sayisi."""
        metin = (metin or "").strip()
        self.tarayici.setExtraSelections([])
        if not metin or self._belge is None:
            self.sonuc.clear()
            return 0
        eslesmeler = self._eslesmeler(metin)
        self._vurgula(eslesmeler)
        if not eslesmeler:
            self.sonuc.setText(_("Bulunamadı"))
            return 0
        bayrak = QtGui.QTextDocument.FindBackward if geri else QtGui.QTextDocument.FindFlag(0)
        if not self.tarayici.find(metin, bayrak):
            imlec = self.tarayici.textCursor()
            imlec.movePosition(QtGui.QTextCursor.End if geri else QtGui.QTextCursor.Start)
            self.tarayici.setTextCursor(imlec)
            self.tarayici.find(metin, bayrak)
        self.sonuc.setText(_("{n} eşleşme").format(n=len(eslesmeler)))
        return len(eslesmeler)

    def _eslesmeler(self, metin):
        bulunan, imlec = [], QtGui.QTextCursor(self._belge)
        while True:
            imlec = self._belge.find(metin, imlec)
            if imlec.isNull():
                return bulunan
            bulunan.append(QtGui.QTextCursor(imlec))

    def _vurgula(self, imlecler):
        bicim = QtGui.QTextCharFormat()
        bicim.setBackground(self.palette().color(QtGui.QPalette.Highlight).lighter(160))
        secimler = []
        for imlec in imlecler:
            s = QtWidgets.QTextEdit.ExtraSelection()
            s.cursor, s.format = imlec, bicim
            secimler.append(s)
        self.tarayici.setExtraSelections(secimler)

    def _baglanti(self, adres):
        if not adres.scheme() and adres.hasFragment():
            if not self.bolume_git(adres.fragment()):
                _log.warning("kilavuz: kirik ic baglanti #%s", adres.fragment())
            return
        if not QtGui.QDesktopServices.openUrl(adres):
            _log.warning("kilavuz: baglanti acilamadi: %s", adres.toString())


def dil():
    """Kilavuzun gosterilecegi dil: arayuz dili."""
    return ceviri.etkin_dil()
