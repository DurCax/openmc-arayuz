# -*- coding: utf-8 -*-
"""
================================================================================
 nuklid_secici.py  --  Izlenen nuklidler icin aranabilir, gruplu secici
================================================================================
 Eskiden virgullu serbest metindi; yazim hatasi ("Xe-135") sonuc okumada
 sessizce atlaniyordu. Simdi:

   arama kutusu     normallestirmeli ("xe-13", "am242m", "PU")
   agac             gruplu, isaretlenebilir (grup basliginda secili/toplam)
   hazir setler     Temel, Pu vektoru, Zehirler, Minor aktinitler, Atik
   cipler           secililer; x ile kaldirilir. Secili ama zincirde olmayan
                    ad KIRMIZI cip olur (silinmez; ipucunda en yakin ad).

 Sinyal: secim_degisti(list) -- kullanicinin her degisikliginde.
 Zincir: zincir_ayarla(yol) ya da adlar_ayarla(adlar, etiket).
================================================================================
"""

import os

from PySide6 import QtCore, QtWidgets

from cekirdek import nuklidler as nk
from cekirdek.ceviri import _
from arayuz.tasarim import tokenlar

A = tokenlar.ARALIK
R = tokenlar.YARICAP

_AD_ROLU = QtCore.Qt.UserRole
_AGAC_SATIR = 12            # agacin en az yuksekligi, satir cinsinden


def _renk(ad):
    from arayuz import tema
    return tema.renk(ad)


# ----------------------------------------------------------------------------
# Akis duzeni: cipler satira sigmayinca alt satira gecer
# ----------------------------------------------------------------------------
class _AkisDuzeni(QtWidgets.QLayout):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ogeler = []
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, oge):                       # noqa: N802 (Qt API)
        self._ogeler.append(oge)

    def count(self):
        return len(self._ogeler)

    def itemAt(self, i):                          # noqa: N802
        return self._ogeler[i] if 0 <= i < len(self._ogeler) else None

    def takeAt(self, i):                          # noqa: N802
        return self._ogeler.pop(i) if 0 <= i < len(self._ogeler) else None

    def expandingDirections(self):                # noqa: N802
        return QtCore.Qt.Orientations()

    def hasHeightForWidth(self):                  # noqa: N802
        return True

    def heightForWidth(self, genislik):           # noqa: N802
        return self._yerlestir(QtCore.QRect(0, 0, genislik, 0), deneme=True)

    def setGeometry(self, alan):                  # noqa: N802
        super().setGeometry(alan)
        self._yerlestir(alan, deneme=False)

    def sizeHint(self):                           # noqa: N802
        return self.minimumSize()

    def minimumSize(self):                        # noqa: N802
        boyut = QtCore.QSize()
        for oge in self._ogeler:
            boyut = boyut.expandedTo(oge.minimumSize())
        return boyut

    def _aralik(self):
        """Ogeler arasi yatay ve dikey aralik (tasarim tokeni)."""
        return A["xs"]

    def _yerlestir(self, alan, deneme):
        aralik = max(self._aralik(), 0)
        x, y, satir = alan.x(), alan.y(), 0
        for oge in self._ogeler:
            boyut = oge.sizeHint()
            if x + boyut.width() > alan.right() and satir > 0:
                x, y, satir = alan.x(), y + satir + aralik, 0
            if not deneme:
                oge.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), boyut))
            x += boyut.width() + aralik
            satir = max(satir, boyut.height())
        return y + satir - alan.y()


# ----------------------------------------------------------------------------
# Cip
# ----------------------------------------------------------------------------
class Cip(QtWidgets.QFrame):
    """Secili bir nuklid: ad + kaldir (x). eksik=True: secili zincirde yok."""

    def __init__(self, ad, eksik=False, ipucu="", parent=None):
        super().__init__(parent)
        self.ad = ad
        self.eksik = eksik
        self.setObjectName("cip")
        duzen = QtWidgets.QHBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.setSpacing(0)
        self.etiket = QtWidgets.QLabel(ad)
        self.kaldir = QtWidgets.QToolButton()
        self.kaldir.setText("×")
        self.kaldir.setAutoRaise(True)
        self.kaldir.setToolTip(_("%s nüklidini seçimden kaldır") % ad)
        duzen.addWidget(self.etiket)
        duzen.addWidget(self.kaldir)
        self.setToolTip(ipucu or ad)
        cerceve = _renk("hata") if eksik else _renk("kenar")
        zemin = _renk("yuzey") if eksik else _renk("vurgu_soluk")
        metin = _renk("hata") if eksik else _renk("metin")
        self.setStyleSheet(
            "QFrame#cip { background: %s; border: 1px solid %s; border-radius: %dpx;"
            " padding-left: %dpx; } QLabel { color: %s; }"
            % (zemin, cerceve, R["buyuk"], A["s"], metin))


# ----------------------------------------------------------------------------
# Secici
# ----------------------------------------------------------------------------
class NuklidSecici(QtWidgets.QWidget):

    secim_degisti = QtCore.Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._adlar = ()
        self._kume = frozenset()
        self._secim = []
        self._ogeler = {}             # nuklid -> [QTreeWidgetItem]
        self._gruplar = {}            # grup anahtari -> (QTreeWidgetItem, Grup)
        self._zincir_yolu = None
        self._kuruluyor = False
        self.cipler = {}

        self.arama = QtWidgets.QLineEdit()
        self.arama.setPlaceholderText(_("Ara: Xe-135, pu, am242m…"))
        self.arama.setClearButtonEnabled(True)
        self.arama.textChanged.connect(self._suz)

        setler = self._set_dugmelerini_kur()

        self.agac = QtWidgets.QTreeWidget()
        self.agac.setHeaderHidden(True)
        self.agac.setUniformRowHeights(True)
        self.agac.setMinimumHeight(self.fontMetrics().lineSpacing() * _AGAC_SATIR)
        self.agac.itemChanged.connect(self._oge_degisti)

        self.cip_alani = QtWidgets.QWidget()
        self._cip_duzeni = _AkisDuzeni(self.cip_alani)
        self.secili_etiket = QtWidgets.QLabel()
        self.bilgi = QtWidgets.QLabel()
        self.bilgi.setWordWrap(True)
        self.bilgi.setObjectName("soluk")

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.setSpacing(A["s"])
        duzen.addWidget(self.secili_etiket)
        duzen.addWidget(self.cip_alani)
        duzen.addWidget(self.arama)
        duzen.addWidget(setler)
        duzen.addWidget(self.agac, 1)
        duzen.addWidget(self.bilgi)
        self._cipleri_kur()

    def _set_dugmelerini_kur(self):
        """Hazir set dugmeleri (tum_setler) + Temizle; dar sayfada alt satira akar."""
        self.set_dugmeleri = {}
        alan = QtWidgets.QWidget()
        akis = _AkisDuzeni(alan)
        akis.addWidget(QtWidgets.QLabel(_("Hazır setler:")))
        for s in nk.tum_setler(()):
            d = QtWidgets.QPushButton(s.baslik)
            d.clicked.connect(lambda _c=False, k=s.anahtar: self._set_ekle(k))
            self.set_dugmeleri[s.anahtar] = d
            akis.addWidget(d)
        self.temizle = QtWidgets.QPushButton(_("Temizle"))
        self.temizle.setToolTip(_("Bütün seçimi kaldırır"))
        self.temizle.clicked.connect(lambda: self._secimi_degistir([]))
        akis.addWidget(self.temizle)
        return alan

    # ------------------------------------------------------------------
    # disari acik API
    # ------------------------------------------------------------------
    def zincir_ayarla(self, yol, etiket=None):
        """Zincir dosyasindan adlari okur (onbellekli). Ayni yol: bir sey yapmaz."""
        if yol == self._zincir_yolu and self._adlar:
            return
        self._zincir_yolu = yol
        adlar = nk.zincir_nuklidleri_guvenli(yol)
        if adlar is None:
            self.adlar_ayarla(None, _("Zincir okunamadı: %s") % yol)
        else:
            self.adlar_ayarla(adlar, etiket or os.path.basename(yol))

    def adlar_ayarla(self, adlar, etiket=""):
        """Listeyi yeniden kurar. adlar=None: zincir okunamadi (liste bos)."""
        self._adlar = tuple(adlar or ())
        self._kume = frozenset(self._adlar)
        if adlar is None:
            self.bilgi.setText(etiket)
            self.bilgi.setStyleSheet("color: %s;" % _renk("hata"))
        else:
            self.bilgi.setText(_("%s — %d nüklid") % (etiket, len(self._adlar)))
            self.bilgi.setStyleSheet("")
        for anahtar, s in ((s.anahtar, s) for s in nk.tum_setler(self._adlar)):
            d = self.set_dugmeleri[anahtar]
            d.setEnabled(bool(s.nuklidler))
            d.setToolTip(", ".join(s.nuklidler) or _("Bu zincirde yok"))
        self._agac_kur()
        self._cipleri_kur()

    def adlar(self):
        return self._adlar

    def secim(self):
        return list(self._secim)

    def secim_ayarla(self, liste, sinyal=True):
        yeni = []
        for ad in liste or []:
            if ad not in yeni:
                yeni.append(ad)
        self._secim = yeni
        self._isaretleri_esitle()
        self._cipleri_kur()
        if sinyal:
            self.secim_degisti.emit(self.secim())

    def ekle(self, ad):
        if ad not in self._secim:
            self._secimi_degistir(self._secim + [ad])

    def cikar(self, ad):
        if ad in self._secim:
            self._secimi_degistir([n for n in self._secim if n != ad])

    def ogeler(self, ad):
        return list(self._ogeler.get(ad, []))

    def grup_ogesi(self, anahtar):
        return self._gruplar[anahtar][0]

    @staticmethod
    def isaretli_mi(oge):
        return oge.checkState(0) == QtCore.Qt.Checked

    # ------------------------------------------------------------------
    # ic
    # ------------------------------------------------------------------
    def _secimi_degistir(self, liste):
        self.secim_ayarla(liste, sinyal=True)

    def _set_ekle(self, anahtar):
        s = next(s for s in nk.tum_setler(self._adlar) if s.anahtar == anahtar)
        self._secimi_degistir(self._secim + [n for n in s.nuklidler if n not in self._secim])

    def _agac_kur(self):
        self._kuruluyor = True
        self.agac.setUpdatesEnabled(False)
        try:
            self.agac.clear()
            self._ogeler, self._gruplar = {}, {}
            for g in nk.gruplar(self._adlar):
                baslik = QtWidgets.QTreeWidgetItem([g.baslik])
                baslik.setFlags(QtCore.Qt.ItemIsEnabled)
                self.agac.addTopLevelItem(baslik)
                self._gruplar[g.anahtar] = (baslik, g)
                cocuklar = []
                for ad in g.nuklidler:
                    oge = QtWidgets.QTreeWidgetItem([ad])
                    oge.setData(0, _AD_ROLU, ad)
                    oge.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
                    oge.setCheckState(0, QtCore.Qt.Checked if ad in self._secim
                                      else QtCore.Qt.Unchecked)
                    self._ogeler.setdefault(ad, []).append(oge)
                    cocuklar.append(oge)
                baslik.addChildren(cocuklar)
        finally:
            self._kuruluyor = False
            self.agac.setUpdatesEnabled(True)
        self._basliklari_yaz()
        self._suz(self.arama.text())

    def _isaretleri_esitle(self):
        self._kuruluyor = True
        try:
            secili = set(self._secim)
            for ad, ogeler in self._ogeler.items():
                durum = QtCore.Qt.Checked if ad in secili else QtCore.Qt.Unchecked
                for oge in ogeler:
                    if oge.checkState(0) != durum:
                        oge.setCheckState(0, durum)
        finally:
            self._kuruluyor = False
        self._basliklari_yaz()

    def _basliklari_yaz(self):
        secili = set(self._secim)
        for baslik, g in self._gruplar.values():
            n = sum(1 for ad in g.nuklidler if ad in secili)
            baslik.setText(0, "%s  (%d/%d)" % (g.baslik, n, len(g.nuklidler)))

    def _oge_degisti(self, oge, _sutun):
        if self._kuruluyor:
            return
        ad = oge.data(0, _AD_ROLU)
        if not ad:
            return
        if self.isaretli_mi(oge):
            self.ekle(ad)
        else:
            self.cikar(ad)

    def _suz(self, metin):
        eslesen = set(nk.ara(metin, self._adlar))
        arama_var = bool((metin or "").strip())
        for baslik, g in self._gruplar.values():
            gorunur = 0
            for i in range(baslik.childCount()):
                cocuk = baslik.child(i)
                gizle = cocuk.data(0, _AD_ROLU) not in eslesen
                cocuk.setHidden(gizle)
                gorunur += not gizle
            baslik.setHidden(gorunur == 0)
            baslik.setExpanded(arama_var and gorunur > 0)

    def _cipleri_kur(self):
        while self._cip_duzeni.count():
            oge = self._cip_duzeni.takeAt(0)
            if oge.widget() is not None:
                oge.widget().deleteLater()
        self.cipler = {}
        for ad in self._secim:
            eksik = bool(self._adlar) and ad not in self._kume
            ipucu = ""
            if eksik:
                onerilen = nk.oneri(ad, self._adlar)
                ipucu = _("Seçili zincirde yok: %s") % ad
                if onerilen:
                    ipucu += " — " + nk.oneri_metni(ad, onerilen)
            cip = Cip(ad, eksik, ipucu, self.cip_alani)
            cip.kaldir.clicked.connect(lambda _c=False, a=ad: self.cikar(a))
            self._cip_duzeni.addWidget(cip)
            self.cipler[ad] = cip
        eksik_sayi = sum(1 for c in self.cipler.values() if c.eksik)
        metin = _("Seçili: %d") % len(self._secim)
        if eksik_sayi:
            metin += "  ·  " + _("%d tanesi seçili zincirde yok (kırmızı)") % eksik_sayi
        elif not self._secim:
            metin += "  ·  " + _("aşağıdan işaretleyin ya da hazır set seçin")
        self.secili_etiket.setText(metin)
        self.cip_alani.updateGeometry()
