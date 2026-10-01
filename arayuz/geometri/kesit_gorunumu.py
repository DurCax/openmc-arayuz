# -*- coding: utf-8 -*-
"""
================================================================================
 arayuz/geometri/kesit_gorunumu.py  --  Sematik kesit (xy | xz) widget'i
================================================================================
 Gelismis editorun orta paneli (§10):
   * xy | xz secimi, xy'de z kutusu; fare tekerlegiyle yakinlastirma, orta /
     sag tusla surukleyerek kaydirma, cift tik: sigdir;
   * tiklama -> yol_secildi(yol) (agacta secim); secili dugumun ogeleri renkli
     ve vurgu kenarli, digerleri soluk;
   * kesik konumlar taranir (uyari rengi), gizli konumlar noktali;
   * xz'de eksenel katman sinirlari kesikli cizgi.
 Renkler tema tokenlarindan (tema.renk) ve malzemenin kendi renginden gelir.
================================================================================
"""

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek.ceviri import _
from arayuz import bilesenler as b
from arayuz import tema
from arayuz.geometri import cizim, cizim_xz
from arayuz.geometri.duzenle import ata_mi
from arayuz.tasarim import tokenlar

A = tokenlar.ARALIK
_YAKINLIK = 1.15
_PAY = 0.04
_SOLUK = 70                 # secim varken digerlerinin opakligi (0-255)


class KesitTuvali(QtWidgets.QWidget):
    """Ogeleri model cercevesinde cizer; isabet testi ve vurgu."""

    yol_secildi = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(8 * A["l"], 12 * A["l"])
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.ogeler, self.kutu, self.cizgiler = [], None, []
        self.hata = None                  # cizim hatasi metni (gorunur)
        self.olcek = 1.0                  # ic birim / cm (cizim.xy_ogeleri)
        self.secili = None
        self._yakin = 1.0
        self._kayma = QtCore.QPointF(0, 0)
        self._surukle = None
        self.setAccessibleName(_("Geometri kesiti"))

    # ---------------- veri ----------------
    def ayarla(self, ogeler, kutu, cizgiler=(), olcek=1.0, hata=None):
        self.ogeler, self.kutu, self.cizgiler = list(ogeler), kutu, list(cizgiler)
        self.olcek = float(olcek or 1.0)
        self.hata = hata
        self.update()

    def cm_noktasi(self, piksel):
        """Piksel -> model cm."""
        m = self.model_noktasi(piksel)
        return QtCore.QPointF(m.x() / self.olcek, m.y() / self.olcek)

    def pikseli_bul(self, x_cm, y_cm):
        """Model cm -> piksel (testler ve klavye erisimi icin)."""
        return self.donusum().map(QtCore.QPointF(x_cm * self.olcek, y_cm * self.olcek))

    def secimi_ayarla(self, yol):
        self.secili = tuple(yol) if yol else None
        self.update()

    def sigdir(self):
        self._yakin, self._kayma = 1.0, QtCore.QPointF(0, 0)
        self.update()

    # ---------------- donusum ----------------
    def donusum(self):
        """Model (x, y yukari) -> widget pikseli."""
        T = QtGui.QTransform()
        if not self.kutu:
            return T
        x0, y0, x1, y1 = self.kutu
        g, h = max(x1 - x0, 1e-9), max(y1 - y0, 1e-9)
        olcek = min(self.width() / g, self.height() / h) * (1.0 - 2 * _PAY) * self._yakin
        T.translate(self.width() / 2.0 + self._kayma.x(), self.height() / 2.0 + self._kayma.y())
        T.scale(olcek, -olcek)
        T.translate(-(x0 + x1) / 2.0, -(y0 + y1) / 2.0)
        return T

    def model_noktasi(self, piksel):
        ters, tamam = self.donusum().inverted()
        return ters.map(QtCore.QPointF(piksel)) if tamam else QtCore.QPointF(0, 0)

    # ---------------- cizim ----------------
    def paintEvent(self, _olay):                       # noqa: N802 (Qt adi)
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), QtGui.QColor(tema.renk("yuzey2")))
        if not self.ogeler:
            p.setPen(QtGui.QColor(tema.renk("uyari" if self.hata else "metin_soluk")))
            p.drawText(self.rect(), QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap,
                       self.hata or (_("Kesit yok (2B modelde xz çizilmez)")
                                     if self.kutu is None else _("Çizilecek öğe yok")))
            p.end()
            return
        p.setTransform(self.donusum())
        kalem = QtGui.QPen(QtGui.QColor(tema.renk("kenar")))
        kalem.setCosmetic(True)
        kalem.setWidthF(0.6)
        for oge in self.ogeler:
            self._oge_ciz(p, oge, kalem)
        self._vurgu_ciz(p)
        self._cizgileri_ciz(p)
        if self.hata:
            p.resetTransform()
            p.setPen(QtGui.QColor(tema.renk("uyari")))
            p.drawText(self.rect(), QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft, self.hata)
        p.end()

    def _oge_ciz(self, p, oge, kalem):
        if oge.kesik:
            renk = QtGui.QColor(tema.renk("uyari"))
            desen = QtCore.Qt.BDiagPattern if oge.kesik == "kesik" else QtCore.Qt.Dense6Pattern
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QBrush(renk, desen))
            p.drawPath(oge.yol_yolu)
            return
        renk = QtGui.QColor(*oge.renk) if oge.renk else QtGui.QColor(tema.renk("yuzey3"))
        if self.secili is not None and not ata_mi(self.secili, oge.yol):
            renk.setAlpha(_SOLUK)
        p.setPen(kalem)
        p.setBrush(renk)
        p.drawPath(oge.yol_yolu)

    def _vurgu_ciz(self, p):
        if self.secili is None:
            return
        kalem = QtGui.QPen(QtGui.QColor(tema.renk("vurgu")))
        kalem.setCosmetic(True)
        kalem.setWidthF(2.0)
        p.setPen(kalem)
        p.setBrush(QtCore.Qt.NoBrush)
        birlesik = QtGui.QPainterPath()
        n = 0
        for oge in self.ogeler:
            if oge.kesik is None and ata_mi(self.secili, oge.yol):
                birlesik.addPath(oge.yol_yolu)
                n += 1
                if n > 400:
                    break
        p.drawPath(birlesik.simplified() if n <= 60 else birlesik)

    def _cizgileri_ciz(self, p):
        if not self.cizgiler or not self.kutu:
            return
        kalem = QtGui.QPen(QtGui.QColor(tema.renk("metin_ikincil")))
        kalem.setCosmetic(True)
        kalem.setStyle(QtCore.Qt.DashLine)
        p.setPen(kalem)
        x0, _y0, x1, _y1 = self.kutu
        for z in self.cizgiler:
            p.drawLine(QtCore.QPointF(x0, z), QtCore.QPointF(x1, z))

    # ---------------- fare ----------------
    def wheelEvent(self, olay):                        # noqa: N802
        adim = olay.angleDelta().y()
        if not adim:
            return
        carpan = _YAKINLIK if adim > 0 else 1.0 / _YAKINLIK
        merkez = QtCore.QPointF(self.width() / 2.0, self.height() / 2.0) + self._kayma
        fark = olay.position() - merkez
        self._kayma -= fark * (carpan - 1.0)
        self._yakin = max(0.2, min(200.0, self._yakin * carpan))
        self.update()
        olay.accept()

    def mousePressEvent(self, olay):                   # noqa: N802
        if olay.button() in (QtCore.Qt.MiddleButton, QtCore.Qt.RightButton):
            self._surukle = olay.position()
            return
        if olay.button() == QtCore.Qt.LeftButton:
            m = self.model_noktasi(olay.position())
            yol = cizim.isabet(self.ogeler, m.x(), m.y())
            if yol is not None:
                self.yol_secildi.emit(yol)

    def mouseMoveEvent(self, olay):                    # noqa: N802
        if self._surukle is not None:
            self._kayma += olay.position() - self._surukle
            self._surukle = olay.position()
            self.update()
            return
        m = self.model_noktasi(olay.position())
        yol = cizim.isabet(self.ogeler, m.x(), m.y())
        oge = next((o for o in reversed(self.ogeler) if o.yol == yol and o.kesik is None), None)
        cm = self.cm_noktasi(olay.position())
        self.setToolTip("(%.3f, %.3f) cm%s" % (cm.x(), cm.y(),
                                              ("\n%s" % oge.etiket) if oge and oge.etiket else ""))

    def mouseReleaseEvent(self, _olay):                # noqa: N802
        self._surukle = None

    def mouseDoubleClickEvent(self, _olay):            # noqa: N802
        self.sigdir()


class KesitGorunumu(QtWidgets.QWidget):
    """Tuval + xy|xz secimi + z kutusu + gosterge. spec_ayarla ile tazelenir."""

    yol_secildi = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec = None
        self.eksen = b.SegmentSecici([("xy", "xy"), ("xz", "xz")], "xy")
        self.z = b.SayiBirim("cm", deger=0.0, en_az=-1e5, en_cok=1e5, ondalik=2, adim=1.0,
                             erisilebilir_ad=_("kesit yüksekliği z"))
        self.z_etiket = QtWidgets.QLabel("z =")
        self.d_sigdir = b.ikon_dugmesi("refresh-cw", _("Sığdır (çift tık)"))
        self.tuval = KesitTuvali()
        self.z.kutu.setMinimumWidth(5 * A["l"])
        self.gosterge = QtWidgets.QLabel(
            _("Tıklama ağaçta seçer · tekerlek: yakınlaştır · sağ tuş: kaydır · "
              "taralı = kesik konum (uyarı)"))
        self.gosterge.setObjectName("soluk")
        self.gosterge.setWordWrap(True)
        self._kur()
        self.eksen.secildi.connect(lambda _a: self.tazele())
        self.z.degisti.connect(lambda _v: self.tazele())
        self.d_sigdir.clicked.connect(self.tuval.sigdir)
        self.tuval.yol_secildi.connect(self.yol_secildi)

    def _kur(self):
        d = QtWidgets.QVBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(A["s"])
        ust = QtWidgets.QWidget()
        u = QtWidgets.QHBoxLayout(ust)
        u.setContentsMargins(0, 0, 0, 0)
        u.setSpacing(A["s"])
        u.addWidget(self.eksen)
        u.addStretch(1)
        u.addWidget(self.d_sigdir)
        d.addWidget(ust)
        # z ayri satirda: 1280 genislikte uc panel yan yana sigsin (yatay kaydirma yok).
        z_satiri = QtWidgets.QWidget()
        zs = QtWidgets.QHBoxLayout(z_satiri)
        zs.setContentsMargins(0, 0, 0, 0)
        zs.setSpacing(A["s"])
        zs.addWidget(self.z_etiket)
        zs.addWidget(self.z, 1)
        self.z_satiri = z_satiri
        d.addWidget(z_satiri)
        d.addWidget(self.tuval, 1)
        d.addWidget(self.gosterge)

    def eksen_adi(self):
        return self.eksen.secili() or "xy"

    def spec_ayarla(self, spec):
        self.spec = spec
        self.tazele()

    def tazele(self):
        if self.spec is None:
            return
        xy = self.eksen_adi() == "xy"
        self.z_satiri.setVisible(xy)
        hatalar = []
        if xy:
            ogeler, kutu, olcek = cizim.xy_ogeleri(self.spec, self.z.deger(), hatalar=hatalar)
            self.tuval.ayarla(ogeler, kutu, (), olcek, hata="; ".join(hatalar) or None)
        else:
            ogeler, kutu, cizgiler = cizim_xz.xz_ogeleri(self.spec, hatalar=hatalar)
            self.tuval.ayarla(ogeler, kutu, cizgiler, hata="; ".join(hatalar) or None)

    def secimi_ayarla(self, yol):
        self.tuval.secimi_ayarla(yol)
