# -*- coding: utf-8 -*-
"""
================================================================================
 arayuz/geometri/agac_paneli.py  --  Dugum agaci (gelismis editorun sol paneli)
================================================================================
 Agac spec["geometri"]den HER DEGISIKLIKTE yeniden kurulur; secim ve acik
 dallar yol metniyle korunur. Her ogenin verisi yol demetidir (ROL_YOL).

 SURUKLE-BIRAK yalniz uyumlu hedefe: dugum -> baska bir yuva; yerlesim -> bir
 kap ya da halka. Uyumsuz hedefte imlec "yasak" olur; birakma Qt'nin kendi
 tasimasini YAPMAZ -- tasima_istendi(kaynak, hedef) yayilir, editor
 duzenle.tasi ile yeni agaci kurar (tek geri al adimi).
 Sag tik: baglam_menusu_istendi(yol, genel konum) -- editor ayni eylemleri
 gosterir (arac cubuguyla ayni QAction'lar).
================================================================================
"""

from PySide6 import QtCore, QtWidgets

from cekirdek.ceviri import _
from arayuz.geometri import duzenle

ROL_YOL = QtCore.Qt.UserRole + 1
_ACIK_DERINLIK = 3


def kesit_ozeti(kes):
    s = (kes or {}).get("sekil")
    if s == "dikdortgen":
        return _("dikdörtgen %g×%g") % tuple(kes.get("boyut") or (0, 0))
    if s in ("silindir", "kure"):
        return _("{s} r={r:g}").format(s=_("küre") if s == "kure" else _("silindir"),
                                       r=float(kes.get("yaricap") or 0))
    if s == "altigen":
        return _("altıgen a={a:g} ({y})").format(a=float(kes.get("apotem") or 0),
                                                 y=kes.get("yonelim", "y"))
    if s == "kafes_zarfi":
        return _("kafes zarfı")
    return s or "?"


def dugum_ozeti(d):
    """Dugumun agacta gorunen kisa ozeti."""
    if isinstance(d, str) or d is None:
        return _("Kısaltma: {ad}").format(ad=d or duzenle.BOSLUK)
    tur = d.get("tur")
    ad = d.get("ad") or d.get("id") or ""
    if tur == "malzeme":
        return _("Boşluk") if d.get("ad") == duzenle.BOSLUK else _("Malzeme: {ad}").format(ad=ad)
    if tur == "bilesen":
        return _("Bileşen: {ad}").format(ad=d.get("ad"))
    if tur == "kafes":
        if d.get("sekil") == "altigen":
            olcu = _("altıgen, {n} halka").format(n=d.get("halka_sayisi"))
        else:
            olcu = _("kare {nx}×{ny}").format(nx=(d.get("boyut") or ("?", "?"))[0],
                                              ny=(d.get("boyut") or ("?", "?"))[1])
        return _("Kafes {ad} ({olcu})").format(ad=ad, olcu=olcu)
    if tur == "kap":
        return _("Kap {ad} ({kesit})").format(ad=ad, kesit=kesit_ozeti(d.get("kesit")))
    if tur == "eksenel":
        return _("Eksenel yığın ({n} katman)").format(n=len(d.get("katmanlar") or []))
    return str(tur)


class AgacGorunumu(QtWidgets.QTreeWidget):
    """QTreeWidget + yol verisi + uyumlu surukle-birak."""

    tasima_istendi = QtCore.Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.agac = {}
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setAccessibleName(_("Geometri ağacı"))
        self._surukle_yol = None

    def uyumlu_mu(self, kaynak, hedef):
        if kaynak is None or hedef is None or tuple(kaynak) == tuple(hedef):
            return False
        if duzenle.ata_mi(kaynak, hedef):
            return False
        if duzenle.oge_turu(self.agac, kaynak) == "yerlesim":
            d = duzenle.al(self.agac, hedef)
            return (duzenle.oge_turu(self.agac, hedef) == "halka"
                    or (isinstance(d, dict) and d.get("tur") == "kap"
                        and duzenle.yuva_mu(self.agac, hedef)))
        if not (duzenle.yuva_mu(self.agac, kaynak) and duzenle.yuva_mu(self.agac, hedef)):
            return False
        if tuple(kaynak) == duzenle.KOK:
            return False
        if tuple(hedef) == duzenle.KOK:
            return (duzenle.al(self.agac, kaynak) or {}).get("tur") == "kap"
        return True

    def _hedef_yolu(self, olay):
        oge = self.itemAt(olay.position().toPoint())
        return oge.data(0, ROL_YOL) if oge is not None else None

    def startDrag(self, eylemler):                    # noqa: N802 (Qt adi)
        oge = self.currentItem()
        self._surukle_yol = oge.data(0, ROL_YOL) if oge is not None else None
        super().startDrag(eylemler)

    def dragEnterEvent(self, olay):                   # noqa: N802
        if olay.source() is self:
            olay.acceptProposedAction()
        else:
            olay.ignore()

    def dragMoveEvent(self, olay):                    # noqa: N802
        hedef = self._hedef_yolu(olay)
        if self.uyumlu_mu(self._surukle_yol, hedef):
            oge = self.itemAt(olay.position().toPoint())
            self.setCurrentItem(oge, 0, QtCore.QItemSelectionModel.NoUpdate)
            olay.acceptProposedAction()
        else:
            olay.ignore()

    def dropEvent(self, olay):                        # noqa: N802
        hedef = self._hedef_yolu(olay)
        kaynak, self._surukle_yol = self._surukle_yol, None
        olay.setDropAction(QtCore.Qt.IgnoreAction)
        olay.accept()
        if self.uyumlu_mu(kaynak, hedef):
            self.tasima_istendi.emit(tuple(kaynak), tuple(hedef))


class AgacPaneli(QtWidgets.QWidget):
    """Agac + secim sinyali. yukle(agac) yeniden kurar; sec(yol)."""

    secildi = QtCore.Signal(object)
    tasima_istendi = QtCore.Signal(object, object)
    baglam_menusu_istendi = QtCore.Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.agac = {}
        self.gorunum = AgacGorunumu()
        self._ogeler = {}
        d = QtWidgets.QVBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        d.addWidget(self.gorunum)
        self.gorunum.currentItemChanged.connect(self._secim_degisti)
        self.gorunum.tasima_istendi.connect(self.tasima_istendi)
        self.gorunum.customContextMenuRequested.connect(self._baglam)
        self._kuruluyor = False

    # ------------------------------------------------------------------
    def yukle(self, agac, secili=None):
        acik = self._acik_yollar()
        ilk = not self._ogeler
        secili = tuple(secili) if secili else self.secili_yol()
        self.agac = agac or {}
        self.gorunum.agac = self.agac
        self._kuruluyor = True
        try:
            self.gorunum.clear()
            self._ogeler = {}
            kok = self._oge(None, _("Kök — {ozet}").format(
                ozet=dugum_ozeti(self.agac.get("kok"))), duzenle.KOK)
            self._dugum_cocuklari(kok, self.agac.get("kok"), duzenle.KOK)
            self._parcalar()
            self._gruplar()
            for yol, oge in self._ogeler.items():
                if (ilk and len(yol) <= _ACIK_DERINLIK) or duzenle.yol_metni(yol) in acik:
                    oge.setExpanded(True)
        finally:
            self._kuruluyor = False
        self.sec(secili if secili in self._ogeler else duzenle.KOK, sinyal=False)

    def _acik_yollar(self):
        return {duzenle.yol_metni(y) for y, o in self._ogeler.items() if o.isExpanded()}

    def _oge(self, ebeveyn, metin, yol, ikon=None):
        oge = QtWidgets.QTreeWidgetItem([metin])
        oge.setData(0, ROL_YOL, tuple(yol))
        oge.setToolTip(0, duzenle.yol_metni(yol))
        bayrak = oge.flags() | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled
        oge.setFlags(bayrak)
        if ebeveyn is None:
            self.gorunum.addTopLevelItem(oge)
        else:
            ebeveyn.addChild(oge)
        self._ogeler[tuple(yol)] = oge
        return oge

    def _dugum_cocuklari(self, ebeveyn, d, yol):
        if not isinstance(d, dict):
            return
        tur = d.get("tur")
        if tur == "kap":
            self._kap(ebeveyn, d, yol)
        elif tur == "kafes":
            for h, v in sorted((d.get("anahtar") or {}).items()):
                self._yuva(ebeveyn, "%s → " % h, v, yol + ("anahtar", h))
            self._yuva(ebeveyn, _("Dış: "), d.get("dis"), yol + ("dis",))
        elif tur == "eksenel":
            self._yuva(ebeveyn, _("Varsayılan: "), d.get("icerik"), yol + ("icerik",))
            for i, k in enumerate(d.get("katmanlar") or []):
                ky = yol + ("katmanlar", i)
                ko = self._oge(ebeveyn, _("Katman: {ad} ({h:g} cm)").format(
                    ad=k.get("ad") or i + 1, h=float(k.get("yukseklik") or 0)), ky)
                if k.get("icerik") is not None:
                    self._yuva(ko, _("İçerik: "), k.get("icerik"), ky + ("icerik",))

    def _kap(self, ebeveyn, d, yol):
        self._yuva(ebeveyn, _("İç: "), d.get("ic"), yol + ("ic",))
        self._yerlesimler(ebeveyn, d.get("yerlesimler"), yol)
        for i, h in enumerate(d.get("halkalar") or []):
            hy = yol + ("halkalar", i)
            tanim = (_("{k:g} cm").format(k=float(h.get("kalinlik") or 0))
                     if h.get("dis") is None else kesit_ozeti(h.get("dis")))
            ho = self._oge(ebeveyn, _("Halka {n} ({t})").format(n=i + 1, t=tanim), hy)
            self._yuva(ho, _("İçerik: "), h.get("icerik"), hy + ("icerik",))
            self._yerlesimler(ho, h.get("yerlesimler"), hy)
        if "dis" in d and yol != duzenle.KOK:
            self._yuva(ebeveyn, _("Dış: "), d.get("dis"), yol + ("dis",))

    def _yerlesimler(self, ebeveyn, yerlesimler, yol):
        for j, y in enumerate(yerlesimler or []):
            yy = yol + ("yerlesimler", j)
            n = y.get("sayi") if y.get("mod") == "halka" else len(y.get("konumlar") or []) \
                if y.get("mod") == "liste" else y.get("harf")
            yo = self._oge(ebeveyn, _("Yerleşim: {ad} ({mod}, {n})").format(
                ad=y.get("ad"), mod=y.get("mod"), n=n), yy)
            self._yuva(yo, _("İçerik: "), y.get("icerik"), yy + ("icerik",))

    def _yuva(self, ebeveyn, onek, d, yol):
        oge = self._oge(ebeveyn, onek + dugum_ozeti(d), yol)
        self._dugum_cocuklari(oge, d, yol)
        return oge

    def _parcalar(self):
        parcalar = self.agac.get("parcalar") or []
        ust = self._oge(None, _("Parçalar ({n})").format(n=len(parcalar)), ("parcalar",))
        for i, p in enumerate(parcalar):
            po = self._oge(ust, _("Parça: {ad}").format(ad=p.get("ad")), ("parcalar", i))
            self._yuva(po, "", p.get("dugum"), ("parcalar", i, "dugum"))

    def _gruplar(self):
        gruplar = self.agac.get("gruplar") or []
        ust = self._oge(None, _("Gruplar ({n})").format(n=len(gruplar)), ("gruplar",))
        for i, g in enumerate(gruplar):
            tur = _("dönme") if g.get("tur") == "donme" else _("daldırma")
            self._oge(ust, _("Grup: {ad} ({tur} = {d:g})").format(
                ad=g.get("ad"), tur=tur, d=float(g.get("deger") or 0)), ("gruplar", i))

    # ------------------------------------------------------------------
    def secili_yol(self):
        oge = self.gorunum.currentItem()
        return tuple(oge.data(0, ROL_YOL)) if oge is not None else None

    def sec(self, yol, sinyal=True):
        """Yolu (ya da var olan en yakin atasini) secer."""
        yol = tuple(yol or duzenle.KOK)
        while yol and yol not in self._ogeler:
            yol = yol[:-1]
        oge = self._ogeler.get(yol)
        if oge is None:
            return None
        eski = self.gorunum.blockSignals(not sinyal)
        try:
            ata = oge.parent()
            while ata is not None:
                ata.setExpanded(True)
                ata = ata.parent()
            self.gorunum.setCurrentItem(oge)
            self.gorunum.scrollToItem(oge)
        finally:
            self.gorunum.blockSignals(eski)
        return yol

    def oge(self, yol):
        return self._ogeler.get(tuple(yol))

    def yollar(self):
        return list(self._ogeler)

    def _secim_degisti(self, simdiki, _onceki):
        if self._kuruluyor or simdiki is None:
            return
        self.secildi.emit(tuple(simdiki.data(0, ROL_YOL)))

    def _baglam(self, nokta):
        oge = self.gorunum.itemAt(nokta)
        if oge is None:
            return
        self.gorunum.setCurrentItem(oge)
        self.baglam_menusu_istendi.emit(tuple(oge.data(0, ROL_YOL)),
                                        self.gorunum.viewport().mapToGlobal(nokta))
