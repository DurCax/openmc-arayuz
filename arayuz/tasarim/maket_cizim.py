# -*- coding: utf-8 -*-
"""
maket_cizim.py -- maketlerdeki YER TUTUCU cizimler: kafes onizlemesi, boyama
izgarasi, ornek kucuk resimleri ve matplotlib grafikleri (sahte veri).

Gercek onizleme/izgara/grafik Dalga 2'de mevcut widget'larla (onizleme.py,
izgara.py, sekme_calistir) baglanir; burasi yalnizca gorunumu gosterir.
Renkler tokenlardan: malzemeler Okabe-Ito adlariyla, yuzeyler temadan.
"""

import math

from PySide6 import QtCore, QtGui, QtWidgets

from arayuz.tasarim import tokenlar
from arayuz.tasarim.maket_veri import ENSTRUMAN, KILAVUZ
from cekirdek.ceviri import _

O = tokenlar.OKABE_ITO
# parca -> Okabe-Ito rengi (maketlerde tutarli)
PARCA_RENGI = {"yakit_cubugu": O["kiremit"], "kilavuz_boru": O["gok"],
               "enstruman": O["mor"], "su": O["mavi"]}


def _r(ad):
    from arayuz import tema
    return QtGui.QColor(tema.renk(ad))


# (tema koyu mu) -> (diger parca, yakit) hucre dolgu opakligi: koyu zeminde
# ayni opaklik camurlu gorunur, daha yuksek olmali.
_IZGARA_OPAKLIK = {False: (90, 46), True: (150, 95)}


def _koyu_mu():
    from arayuz import tema
    return tema.etkin() == "koyu"


def _hucre_turu(i, j):
    if (i, j) in ENSTRUMAN:
        return "enstruman"
    if (i, j) in KILAVUZ:
        return "kilavuz_boru"
    return "yakit_cubugu"


class KafesCizimi(QtWidgets.QWidget):
    """17x17 kare demet: onizleme (daireler) ya da boyama izgarasi (hucreler)."""

    def __init__(self, izgara=False, n=17, parent=None):
        super().__init__(parent)
        self.izgara, self.n = izgara, n
        self.secili = {(0, 0), (0, 1), (1, 0)} if izgara else set()
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    def paintEvent(self, _olay):                             # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        kenar = min(self.width(), self.height()) - 2 * tokenlar.ARALIK["l"]
        adim = kenar / self.n
        x0 = (self.width() - kenar) / 2
        y0 = (self.height() - kenar) / 2
        if self.izgara:
            self._izgara_ciz(p, x0, y0, adim)
        else:
            self._onizleme_ciz(p, x0, y0, adim, kenar)
        p.end()

    def _onizleme_ciz(self, p, x0, y0, adim, kenar):
        su = QtGui.QColor(PARCA_RENGI["su"])
        su.setAlpha(70)
        p.fillRect(QtCore.QRectF(x0, y0, kenar, kenar), su)
        p.setPen(QtCore.Qt.NoPen)
        for i in range(self.n):
            for j in range(self.n):
                tur = _hucre_turu(i, j)
                c = QtCore.QPointF(x0 + (j + 0.5) * adim, y0 + (i + 0.5) * adim)
                p.setBrush(QtGui.QColor(PARCA_RENGI[tur]))
                r = adim * (0.39 if tur == "yakit_cubugu" else 0.45)
                p.drawEllipse(c, r, r)
                if tur != "yakit_cubugu":
                    p.setBrush(su)
                    p.drawEllipse(c, r * 0.78, r * 0.78)
        p.setPen(QtGui.QPen(_r("kenar_guclu"), 1))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRect(QtCore.QRectF(x0, y0, kenar, kenar))

    def _izgara_ciz(self, p, x0, y0, adim):
        f = QtGui.QFont(self.font())
        f.setPixelSize(max(8, int(adim * 0.3)))
        f.setWeight(QtGui.QFont.Medium)
        p.setFont(f)
        etiket = {"yakit_cubugu": "YÇ", "kilavuz_boru": "KB", "enstruman": "EN"}
        for i in range(self.n):
            for j in range(self.n):
                tur = _hucre_turu(i, j)
                h = QtCore.QRectF(x0 + j * adim + 1, y0 + i * adim + 1, adim - 2, adim - 2)
                zemin = QtGui.QColor(PARCA_RENGI[tur])
                zemin.setAlpha(_IZGARA_OPAKLIK[_koyu_mu()][tur == "yakit_cubugu"])
                p.setPen(QtCore.Qt.NoPen)
                p.setBrush(zemin)
                p.drawRoundedRect(h, 3, 3)
                p.setPen(_r("metin_ikincil"))
                p.drawText(h, QtCore.Qt.AlignCenter, etiket[tur])
                if (i, j) in self.secili:
                    p.setPen(QtGui.QPen(_r("vurgu"), 2))
                    p.setBrush(QtCore.Qt.NoBrush)
                    p.drawRoundedRect(h.adjusted(1, 1, -1, -1), 3, 3)


class KucukResim(QtWidgets.QWidget):
    """Ornek galerisi kucuk resmi: motif = pin|kare|kare3b|altigen|plaka|kor|kure|zirh."""

    def __init__(self, motif, parent=None):
        super().__init__(parent)
        self.motif = motif
        self.setFixedHeight(96)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

    def paintEvent(self, _olay):                             # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = QtCore.QRectF(self.rect())
        yol = QtGui.QPainterPath()
        yol.addRoundedRect(r, tokenlar.YARICAP["buyuk"], tokenlar.YARICAP["buyuk"])
        p.fillPath(yol, _r("yuzey2"))
        p.translate(r.center())
        s = min(r.width(), r.height()) * 0.36
        getattr(self, "_" + self.motif, self._pin)(p, s)
        p.end()

    @staticmethod
    def _daire(p, x, y, r, renk):
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(renk))
        p.drawEllipse(QtCore.QPointF(x, y), r, r)

    def _pin(self, p, s):
        self._daire(p, 0, 0, s, O["gok"])
        self._daire(p, 0, 0, s * 0.62, _r("yuzey2").name())
        self._daire(p, 0, 0, s * 0.55, O["kiremit"])

    def _kare(self, p, s, n=7):
        a = 2 * s / n
        for i in range(n):
            for j in range(n):
                renk = O["gok"] if (i, j) in {(1, 3), (3, 1), (3, 5), (5, 3), (3, 3)} else O["kiremit"]
                self._daire(p, -s + (j + 0.5) * a, -s + (i + 0.5) * a, a * 0.38, renk)

    def _kare3b(self, p, s):
        p.save()
        p.scale(1.0, 0.55)
        p.rotate(45)
        self._kare(p, s * 0.9)
        p.restore()

    def _altigen(self, p, s, halka=3):
        a = s / (halka + 0.3)
        for q in range(-halka, halka + 1):
            for r_ in range(max(-halka, -q - halka), min(halka, -q + halka) + 1):
                x = a * (q + r_ / 2.0)
                y = a * r_ * math.sqrt(3) / 2
                renk = O["gok"] if (q, r_) == (0, 0) else O["kiremit"]
                self._daire(p, x, y, a * 0.4, renk)

    def _plaka(self, p, s):
        p.setPen(QtCore.Qt.NoPen)
        for k in range(7):
            p.setBrush(QtGui.QColor(O["kiremit"] if k % 2 == 0 else O["gok"]))
            p.drawRoundedRect(QtCore.QRectF(-s * 1.3, -s + k * s * 0.3, s * 2.6, s * 0.16), 2, 2)

    def _kor(self, p, s):
        a = 2 * s / 7
        for i in range(7):
            for j in range(7):
                if math.hypot(i - 3, j - 3) <= 3.3:
                    renk = O["turuncu"] if (i + j) % 3 else O["kiremit"]
                    c = QtGui.QColor(renk)
                    p.fillRect(QtCore.QRectF(-s + j * a + 1, -s + i * a + 1, a - 2, a - 2), c)

    def _kure(self, p, s):
        g = QtGui.QRadialGradient(QtCore.QPointF(-s * 0.3, -s * 0.3), s * 1.2)
        g.setColorAt(0, QtGui.QColor(O["turuncu"]))
        g.setColorAt(1, QtGui.QColor(O["kiremit"]))
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(g)
        p.drawEllipse(QtCore.QPointF(0, 0), s, s)

    def _zirh(self, p, s):
        p.setPen(QtCore.Qt.NoPen)
        for k, renk in enumerate((O["mavi"], O["gok"], O["yesil"], O["gok"])):
            c = QtGui.QColor(renk)
            c.setAlpha(200 - k * 35)
            p.fillRect(QtCore.QRectF(-s * 0.6 + k * s * 0.45, -s, s * 0.4, 2 * s), c)
        self._daire(p, -s * 1.2, 0, s * 0.18, O["kiremit"])


# ----------------------------------------------------------------------------
# matplotlib grafikleri (sahte veri; tema rcParams'i tema.uygula verir)
# ----------------------------------------------------------------------------
def _tuval(gen=5.0, yuk=2.6):
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    from matplotlib.figure import Figure
    sekil = Figure(figsize=(gen, yuk), dpi=100, layout="constrained")
    t = FigureCanvasQTAgg(sekil)
    t.setMinimumHeight(180)
    # Tuvalin sizeHint'i mevcut boyutudur (buyudukce buyur): yerlesim onu dikkate
    # almasin, yoksa sayfa gereksiz kaydirma cubugu alir.
    t.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Ignored)
    return t, sekil


def _sahte_keff(n=250, pasif=50, tohum=7):
    import numpy as np
    ug = np.random.default_rng(tohum)
    k = 1.18342 + 0.0062 * ug.standard_normal(n)
    k[:pasif] += np.linspace(0.02, 0.0, pasif)
    ort, sig = [], []
    for i in range(pasif + 1, n + 1):
        parca = k[pasif:i]
        ort.append(parca.mean())
        sig.append(parca.std(ddof=1) / math.sqrt(len(parca)) if len(parca) > 1 else 0.004)
    return k, np.array(ort), np.array(sig)


def yakinsama_grafigi():
    import numpy as np
    from arayuz import tema
    t, sekil = _tuval()
    ax = sekil.add_subplot()
    k, ort, sig = _sahte_keff()
    x = np.arange(1, len(k) + 1)
    ax.plot(x, k, lw=0.8, alpha=0.45, label=_("k (çevrim)"))
    xa = np.arange(51, len(k) + 1)
    ax.plot(xa, ort, lw=1.6, label=_("k ort."))
    ax.fill_between(xa, ort - sig, ort + sig, alpha=0.18, lw=0, color=tema.grafik_paleti()[1])
    ax.axvline(50.5, lw=1, ls="--", color=tema.renk("metin_soluk"))
    ax.text(52, ax.get_ylim()[1], _(" etkin çevrimler"), va="top", fontsize=8,
            color=tema.renk("metin_soluk"))
    ax.set_xlabel(_("çevrim"))
    ax.set_ylabel("k-eff")
    ax.grid(True, lw=0.6)
    ax.legend(loc="lower right", fontsize=8)
    return t


def entropi_grafigi():
    import numpy as np
    t, sekil = _tuval(3.2, 2.6)
    ax = sekil.add_subplot()
    x = np.arange(1, 251)
    ug = np.random.default_rng(3)
    h = 7.92 - 1.4 * np.exp(-x / 9.0) + 0.006 * ug.standard_normal(len(x))
    ax.plot(x, h, lw=1.2)
    ax.axvline(50.5, lw=1, ls="--", alpha=0.6)
    ax.set_xlabel(_("çevrim"))
    ax.set_ylabel("H (bit)")
    ax.grid(True, lw=0.6)
    return t


def guc_verisi():
    """Sahte 17x17 pin guc haritasi (ortalama 1): kosinus zarfi + kilavuz boru
    komsularinda yerel tepe (suyla yavaslama). -> (harita, F_dH, (satir, sutun))."""
    import numpy as np
    n = 17
    i, j = np.mgrid[0:n, 0:n]
    g = 1.0 + 0.06 * np.cos((i - 8) / 8.5 * 1.2) * np.cos((j - 8) / 8.5 * 1.2)
    bos = KILAVUZ | ENSTRUMAN
    for a, b_ in bos:
        for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if 0 <= a + da < n and 0 <= b_ + db < n and (a + da, b_ + db) not in bos:
                g[a + da, b_ + db] += 0.025
    for a, b_ in bos:
        g[a, b_] = np.nan
    g = g / np.nanmean(g)
    tepe = tuple(int(v) for v in np.unravel_index(np.nanargmax(g), g.shape))
    return g, float(np.nanmax(g)), tepe


def guc_haritasi_grafigi():
    import numpy as np
    from arayuz import tema
    t, sekil = _tuval(3.2, 3.0)
    ax = sekil.add_subplot()
    g, fdh, tepe = guc_verisi()
    ax.set_facecolor(tema.renk("yuzey2"))       # kilavuz borular (NaN) notr gorunur
    alt = math.floor(np.nanmin(g) * 50) / 50.0
    ust = math.ceil(fdh * 50) / 50.0
    im = ax.imshow(g, cmap=tokenlar.GRAFIK_HARITASI, vmin=alt, vmax=ust)
    ax.plot(tepe[1], tepe[0], marker="s", mfc="none", mec=tema.renk("hata"), ms=8, mew=1.6)
    ax.set_xticks([])
    ax.set_yticks([])
    for kenar in ax.spines.values():
        kenar.set_visible(False)
    # Renk cubugu goruntuyle ayni yukseklikte: eksen koordinatinda ic eksen.
    cax = ax.inset_axes([1.04, 0.0, 0.05, 1.0])
    sekil.colorbar(im, cax=cax, label=_("göreli güç (ort. = 1)"))
    return t
