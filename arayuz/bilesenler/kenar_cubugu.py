# -*- coding: utf-8 -*-
"""
kenar_cubugu.py -- KenarCubugu: sol dikey gezinme (ikon + metin + durum isareti).

    k = KenarCubugu()
    k.grup_ekle(_("Tasarım"))                       # istege bagli ara baslik
    k.ekle("malzemeler", _("Malzemeler"), "flask-conical")
    k.secildi.connect(lambda anahtar: ...)          # kullanici ya da sec() secince
    k.sec("demet");  k.secili() -> "demet"
    k.durum_ayarla("kor", "hata")                  # "tamam" ✓ | "hata" ! | "eksik" • | None
    k.gorunur_yap("tukenme", False)                # gizle/goster (dizin degismez)
    k.daralt(True)                                 # yalniz ikon; metin ipucuna gecer
    k.alt_ekle(widget)                             # alt bolume (tema dugmesi vb.)

Klavye: liste odaktayken yukari/asagi (gizli ve grup satirlarini atlar),
Home/End; secim hemen `secildi` yayar. Durum isareti rengi ve ikonu etkin
temadan boyama aninda okunur -- tema degisimi kendiliginden uyar.
"""

from PySide6 import QtCore, QtGui, QtWidgets

from arayuz.bilesenler.dugme import ikon_dugmesi
from arayuz.tasarim import tokenlar
from arayuz.tasarim.ikon import ikon
from cekirdek.ceviri import _

A = tokenlar.ARALIK
B = tokenlar.BOYUT
ROL_ANAHTAR = QtCore.Qt.UserRole + 1
ROL_IKON = QtCore.Qt.UserRole + 2
ROL_DURUM = QtCore.Qt.UserRole + 3
ROL_GRUP = QtCore.Qt.UserRole + 4
DURUM_IKONU = {"tamam": ("circle-check", "basari"), "hata": ("circle-alert", "hata"),
               "eksik": ("circle-dot", "metin_soluk"), "uyari": ("triangle-alert", "uyari")}
DURUM_METNI = {"tamam": "✓", "hata": "!", "eksik": "•", "uyari": "!"}


class _Temsilci(QtWidgets.QStyledItemDelegate):

    def __init__(self, kenar):
        super().__init__(kenar)
        self._kenar = kenar

    def sizeHint(self, secenek, dizin):                  # noqa: N802
        if dizin.data(ROL_GRUP):
            return QtCore.QSize(10, 0 if self._kenar.dar_mi() else B["kenar_cubugu_satir"] - 6)
        return QtCore.QSize(10, B["kenar_cubugu_satir"])

    def paint(self, ressam, secenek, dizin):
        from arayuz import tema
        opt = QtWidgets.QStyleOptionViewItem(secenek)
        self.initStyleOption(opt, dizin)
        stil = opt.widget.style() if opt.widget else QtWidgets.QApplication.style()
        r = opt.rect
        if dizin.data(ROL_GRUP):
            self._grup_ciz(ressam, r, dizin.data(QtCore.Qt.DisplayRole))
            return
        opt.text = ""
        opt.icon = QtGui.QIcon()
        stil.drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, opt, ressam, opt.widget)
        secili = bool(opt.state & QtWidgets.QStyle.State_Selected)
        renk = "vurgu" if secili else "metin_ikincil"
        n = B["ikon"]
        dar = self._kenar.dar_mi()
        x = r.left() + (r.width() - n) // 2 if dar else r.left() + A["m"]
        ikon(dizin.data(ROL_IKON), renk).paint(
            ressam, QtCore.QRect(x, r.center().y() - n // 2 + 1, n, n))
        if secili and opt.state & QtWidgets.QStyle.State_HasFocus and opt.widget.hasFocus():
            ressam.save()
            ressam.setPen(QtGui.QPen(QtGui.QColor(tema.renk("odak")), 2))
            ressam.drawRoundedRect(QtCore.QRectF(r).adjusted(1, 1, -1, -1), 5, 5)
            ressam.restore()
        durum = dizin.data(ROL_DURUM)
        if dar:
            if durum in ("hata", "uyari"):
                ressam.save()
                ressam.setRenderHint(QtGui.QPainter.Antialiasing)
                ressam.setBrush(QtGui.QColor(tema.renk(DURUM_IKONU[durum][1])))
                ressam.setPen(QtCore.Qt.NoPen)
                ressam.drawEllipse(QtCore.QPointF(x + n + 1, r.top() + 9), 3.5, 3.5)
                ressam.restore()
            return
        metin_x = x + n + A["s"] + 2
        sag = r.right() - A["s"]
        if durum in DURUM_IKONU:
            ad, drenk = DURUM_IKONU[durum]
            m = 14
            ikon(ad, drenk, m).paint(ressam, QtCore.QRect(sag - m, r.center().y() - m // 2 + 1, m, m))
            sag -= m + A["s"]
        f = QtGui.QFont(opt.font)
        f.setWeight(QtGui.QFont.DemiBold if secili else QtGui.QFont.Medium)
        ressam.save()
        ressam.setFont(f)
        ressam.setPen(QtGui.QColor(tema.renk("vurgu" if secili else "metin")))
        alan = QtCore.QRect(metin_x, r.top(), sag - metin_x, r.height())
        metin = QtGui.QFontMetrics(f).elidedText(dizin.data(QtCore.Qt.DisplayRole),
                                                 QtCore.Qt.ElideRight, alan.width())
        ressam.drawText(alan, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, metin)
        ressam.restore()

    def _grup_ciz(self, ressam, r, metin):
        from arayuz import tema
        if self._kenar.dar_mi():
            return
        ressam.save()
        f = QtGui.QFont(ressam.font())
        f.setPixelSize(tokenlar.TIPOGRAFI["etiket"][0])
        f.setWeight(QtGui.QFont.DemiBold)
        ressam.setFont(f)
        ressam.setPen(QtGui.QColor(tema.renk("metin_soluk")))
        ressam.drawText(r.adjusted(A["m"], 0, -A["s"], -2),
                        QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom, metin)
        ressam.restore()


class KenarCubugu(QtWidgets.QFrame):
    secildi = QtCore.Signal(str)
    daraltildi = QtCore.Signal(bool)

    def __init__(self, parent=None, baslik=None):
        super().__init__(parent)
        self.setObjectName("kenarCubugu")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self._dar = False
        self._son = None
        d = QtWidgets.QVBoxLayout(self)
        d.setContentsMargins(0, A["s"], 0, A["s"])
        d.setSpacing(A["xs"])
        self.liste = QtWidgets.QListWidget()
        self.liste.setObjectName("kenarListesi")
        self.liste.setAccessibleName(baslik or _("Gezinme"))
        self.liste.setItemDelegate(_Temsilci(self))
        self.liste.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.liste.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.liste.setUniformItemSizes(False)
        self.liste.setMouseTracking(True)
        self.liste.currentItemChanged.connect(self._degisti)
        d.addWidget(self.liste, 1)
        self._alt = QtWidgets.QVBoxLayout()
        self._alt.setContentsMargins(A["s"], 0, A["s"], 0)
        self._alt.setSpacing(2)
        d.addLayout(self._alt)
        self.daralt_dugmesi = ikon_dugmesi("panel-left", _("Kenar çubuğunu daralt"),
                                           secilebilir=True)
        self.daralt_dugmesi.toggled.connect(self.daralt)
        self._alt.addWidget(self.daralt_dugmesi, 0, QtCore.Qt.AlignLeft)
        self.setFocusProxy(self.liste)
        self._genislik_uygula()

    # ------------------------------------------------------------------ ogeler
    def ekle(self, anahtar, metin, ikon_adi):
        if self._oge(anahtar) is not None:
            raise ValueError("ayni anahtar iki kez: %r" % (anahtar,))
        o = QtWidgets.QListWidgetItem(metin)
        o.setData(ROL_ANAHTAR, anahtar)
        o.setData(ROL_IKON, ikon_adi)
        o.setToolTip(metin)
        self.liste.addItem(o)
        return o

    def grup_ekle(self, metin):
        o = QtWidgets.QListWidgetItem(metin)
        o.setData(ROL_GRUP, True)
        o.setFlags(QtCore.Qt.NoItemFlags)
        self.liste.addItem(o)
        return o

    def alt_ekle(self, widget):
        self._alt.insertWidget(self._alt.count() - 1, widget, 0, QtCore.Qt.AlignLeft)
        return widget

    def anahtarlar(self):
        return [self.liste.item(i).data(ROL_ANAHTAR) for i in range(self.liste.count())
                if not self.liste.item(i).data(ROL_GRUP)]

    def _oge(self, anahtar):
        for i in range(self.liste.count()):
            o = self.liste.item(i)
            if o.data(ROL_ANAHTAR) == anahtar:
                return o
        return None

    def _gerekli(self, anahtar):
        o = self._oge(anahtar)
        if o is None:
            raise KeyError("bilinmeyen kenar cubugu ogesi: %r" % (anahtar,))
        return o

    # ------------------------------------------------------------------ secim
    def sec(self, anahtar):
        """Ogeyi secer; gizli ya da bilinmeyen ogede False doner."""
        o = self._oge(anahtar)
        if o is None or o.isHidden():
            return False
        self.liste.setCurrentItem(o)
        return True

    def secili(self):
        o = self.liste.currentItem()
        return o.data(ROL_ANAHTAR) if o is not None else None

    def _degisti(self, simdiki, _onceki):
        anahtar = simdiki.data(ROL_ANAHTAR) if simdiki is not None else None
        if anahtar is None or anahtar == self._son:
            return
        self._son = anahtar
        self.secildi.emit(anahtar)

    # ------------------------------------------------------------------ durum
    def durum_ayarla(self, anahtar, durum):
        if durum is not None and durum not in DURUM_IKONU:
            raise ValueError("bilinmeyen durum: %r" % (durum,))
        o = self._gerekli(anahtar)
        o.setData(ROL_DURUM, durum)
        metin = o.text()
        o.setData(QtCore.Qt.AccessibleTextRole,
                  "%s %s" % (metin, DURUM_METNI[durum]) if durum else metin)

    def durum(self, anahtar):
        return self._gerekli(anahtar).data(ROL_DURUM)

    def gorunur_yap(self, anahtar, gorunur):
        self._gerekli(anahtar).setHidden(not gorunur)

    def gorunur_mu(self, anahtar):
        return not self._gerekli(anahtar).isHidden()

    # ------------------------------------------------------------------ daraltma
    def dar_mi(self):
        return self._dar

    def daralt(self, dar=True):
        dar = bool(dar)
        if dar == self._dar:
            return
        self._dar = dar
        engel = self.daralt_dugmesi.blockSignals(True)
        self.daralt_dugmesi.setChecked(dar)
        self.daralt_dugmesi.blockSignals(engel)
        self.daralt_dugmesi.setToolTip(_("Kenar çubuğunu genişlet") if dar
                                       else _("Kenar çubuğunu daralt"))
        self._genislik_uygula()
        self.liste.doItemsLayout()
        self.daraltildi.emit(dar)

    def _genislik_uygula(self):
        g = B["kenar_cubugu_dar"] if self._dar else B["kenar_cubugu_genis"]
        self.setFixedWidth(g)
        stil = QtCore.Qt.ToolButtonIconOnly if self._dar else QtCore.Qt.ToolButtonTextBesideIcon
        for i in range(self._alt.count()):
            w = self._alt.itemAt(i).widget()
            if isinstance(w, QtWidgets.QToolButton) and w is not self.daralt_dugmesi:
                w.setToolButtonStyle(stil)

    def sizeHint(self):                                    # noqa: N802
        g = B["kenar_cubugu_dar"] if self._dar else B["kenar_cubugu_genis"]
        return QtCore.QSize(g, super().sizeHint().height())
