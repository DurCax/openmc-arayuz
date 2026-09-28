# -*- coding: utf-8 -*-
"""
 arayuz/cubuk/malzeme_kutusu.py  --  MalzemeKutusu ve tablo satir takibi

 arayuz/sekme_cubuk.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import sekme_cubuk; sekme_cubuk.X` aynen calisir.
"""

from PySide6 import QtCore, QtWidgets
from cekirdek import sema
from arayuz.cubuk.parca_islemleri import (
    BOS_ETIKETI, SECILMEDI_ETIKETI, _renk, malzeme_etiketi, roller)


# ============================================================================
# Qt yardimcilari
# ============================================================================

class MalzemeKutusu(QtWidgets.QComboBox):
    """
    Malzeme secimi. adaylar: listelenecek adlar (None: hepsi). Mevcut deger
    listede yoksa yine eklenir ("role uymuyor" notuyla) -- dosyadaki veri
    gorunmeden degismesin. Deger None ise:
      yok_etiketi verilmisse o (gecerli bir secim, or. "zarf ile ayni"),
      verilmemisse "— Malzeme secin —" KIRMIZI gosterilir.
    """

    def __init__(self, spec, secili, adaylar=None, bos=True, yok_etiketi=None,
                 rol_goster=True, parent=None):
        super().__init__(parent)
        self.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(14)
        rol_tablosu = roller(spec)
        self._yok_gecerli = yok_etiketi is not None
        tum = [m["ad"] for m in spec.get("malzemeler", [])]
        liste = list(tum if adaylar is None else [a for a in tum if a in adaylar])
        if yok_etiketi is not None:
            self.addItem(yok_etiketi, None)
        elif secili is None:
            self.addItem(SECILMEDI_ETIKETI, None)
        if bos:
            self.addItem(BOS_ETIKETI, sema.BOSLUK)
        for ad in liste:
            self.addItem(malzeme_etiketi(spec, ad, rol_goster, rol_tablosu), ad)
            self.setItemData(self.count() - 1, ad, QtCore.Qt.ToolTipRole)
        if secili is not None and self.findData(secili) < 0:
            etiket = malzeme_etiketi(spec, secili, rol_goster, rol_tablosu)
            self.addItem("%s — role uymuyor" % etiket
                         if sema.malzeme_bul(spec, secili) is not None else etiket, secili)
        i = self.findData(secili)
        self.setCurrentIndex(max(i, 0))
        self.currentIndexChanged.connect(self._stil)
        self._stil()

    def eksik_mi(self):
        return self.currentData() is None and not self._yok_gecerli

    def _stil(self, *_):
        stil = ("QComboBox { color: %s; font-weight: 600; }" % _renk("hata", "#b3261e")
                if self.eksik_mi() else "")
        if self.styleSheet() != stil:
            self.setStyleSheet(stil)

    def adaylar(self):
        return [self.itemData(i) for i in range(self.count())]


class _SatirTakibi(QtCore.QObject):
    """Tablodaki hucre widget'ina tiklaninca / odaklaninca o satir secilsin
    (hucre widget'lari tablonun gecerli satirini kendiliginden degistirmez)."""

    def __init__(self, tablo):
        super().__init__(tablo)
        self.tablo = tablo

    def eventFilter(self, nesne, olay):
        if olay.type() in (QtCore.QEvent.FocusIn, QtCore.QEvent.MouseButtonPress):
            satir = nesne.property("satir")
            if satir is not None and int(satir) != self.tablo.currentRow():
                self.tablo.setCurrentCell(int(satir), 2)
        return False
