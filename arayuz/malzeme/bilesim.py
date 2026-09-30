# -*- coding: utf-8 -*-
"""
 arayuz/malzeme/bilesim.py  --  bilesim tablosu modeli ve acilir liste delegesi

 arayuz/sekme_malzeme.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import sekme_malzeme; sekme_malzeme.X` aynen calisir.
"""

import copy

from PySide6 import QtCore, QtGui, QtWidgets
from arayuz.malzeme.yardimcilar import (
    BIRIM_SECENEKLERI, TUR_SECENEKLERI, _isim_duzelt, _tema_renk)


# ============================================================================
# Bilesim tablosu
# ============================================================================

class BilesimModeli(QtCore.QAbstractTableModel):
    """
    Malzeme bilesim satirlari. "Tur" ve "Birim" acilir listeden secilir
    (spec degerleri element/nuklid ve ao/wo AYNEN kalir). Zenginlik yalnizca
    tur=element ve isim=U satirinda duzenlenebilir: OpenMC baska bir elementte
    kosu sirasinda reddeder, nuklidde sessizce yok sayar.
    """

    BASLIKLAR = ["Tür", "İsim", "Miktar", "Birim", "Zenginlik %"]
    S_TUR, S_ISIM, S_MIKTAR, S_BIRIM, S_ZENG = range(5)

    def __init__(self, bilesim, salt_okunur=False, parent=None):
        super().__init__(parent)
        self.bilesim = copy.deepcopy(bilesim or [])
        self.salt_okunur = salt_okunur

    def yukle(self, bilesim):
        self.beginResetModel()
        self.bilesim = copy.deepcopy(bilesim or [])
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self.bilesim)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self.BASLIKLAR)

    def headerData(self, bolum, yon, rol=QtCore.Qt.DisplayRole):
        if rol == QtCore.Qt.DisplayRole and yon == QtCore.Qt.Horizontal:
            return self.BASLIKLAR[bolum]
        if rol == QtCore.Qt.DisplayRole and yon == QtCore.Qt.Vertical:
            return str(bolum + 1)
        return None

    def zenginlik_uygun(self, satir):
        b = self.bilesim[satir]
        return b.get("tur", "element") != "nuklid" and b.get("isim") == "U"

    def data(self, ix, rol=QtCore.Qt.DisplayRole):
        if not ix.isValid():
            return None
        b = self.bilesim[ix.row()]
        s = ix.column()
        if rol == QtCore.Qt.EditRole:
            return [b.get("tur", "element"), b.get("isim", ""), b.get("miktar", 0.0),
                    b.get("birim", "ao"), b.get("zenginlik")][s]
        if rol == QtCore.Qt.DisplayRole:
            if s == self.S_TUR:
                return dict(TUR_SECENEKLERI).get(b.get("tur", "element"), b.get("tur"))
            if s == self.S_ISIM:
                return b.get("isim", "")
            if s == self.S_MIKTAR:
                return "%.6g" % float(b.get("miktar") or 0.0)
            if s == self.S_BIRIM:
                return dict(BIRIM_SECENEKLERI).get(b.get("birim", "ao"), b.get("birim"))
            z = b.get("zenginlik")
            if z is None:
                return "doğal" if self.zenginlik_uygun(ix.row()) else ""
            return "%g" % z
        if rol == QtCore.Qt.ForegroundRole and s == self.S_ZENG:
            if b.get("zenginlik") is None or not self.zenginlik_uygun(ix.row()):
                return QtGui.QBrush(QtGui.QColor(_tema_renk("metin_soluk")))
        if rol == QtCore.Qt.ToolTipRole and s == self.S_ZENG:
            if not self.zenginlik_uygun(ix.row()):
                return "Zenginlik yalnızca doğal element U satırında girilir."
            return "U-235 ağırlıkça %; boş bırakılırsa doğal uranyum."
        return None

    def _zenginlik_temizle(self, satir):
        b = self.bilesim[satir]
        if not self.zenginlik_uygun(satir) and b.get("zenginlik") is not None:
            b.pop("zenginlik", None)

    def setData(self, ix, deger, rol=QtCore.Qt.EditRole):
        if rol != QtCore.Qt.EditRole or not ix.isValid() or self.salt_okunur:
            return False
        satir, s = ix.row(), ix.column()
        b = self.bilesim[satir]
        try:
            if s == self.S_TUR:
                if deger not in dict(TUR_SECENEKLERI):
                    return False
                b["tur"] = deger
                b["isim"] = _isim_duzelt(b.get("isim"), deger)
                self._zenginlik_temizle(satir)
            elif s == self.S_ISIM:
                b["isim"] = _isim_duzelt(str(deger), b.get("tur", "element"))
                self._zenginlik_temizle(satir)
            elif s == self.S_MIKTAR:
                b["miktar"] = float(str(deger).replace(",", "."))
            elif s == self.S_BIRIM:
                if deger not in dict(BIRIM_SECENEKLERI):
                    return False
                b["birim"] = deger
            elif s == self.S_ZENG:
                metin = "" if deger is None else str(deger).strip()
                if metin in ("", "doğal"):
                    b.pop("zenginlik", None)
                elif not self.zenginlik_uygun(satir):
                    return False            # yalnizca silinebilir
                else:
                    b["zenginlik"] = float(metin.replace(",", "."))
        except ValueError:      # sayi degil: Qt duzenlemeyi reddeder, eski deger kalir
            return False
        # satirin tamami: zenginlik hucresinin etkinligi degismis olabilir
        self.dataChanged.emit(self.index(satir, 0), self.index(satir, self.columnCount() - 1))
        return True

    def flags(self, ix):
        temel = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        if not ix.isValid() or self.salt_okunur:
            return temel
        if ix.column() == self.S_ZENG:
            if self.zenginlik_uygun(ix.row()):
                return temel | QtCore.Qt.ItemIsEditable
            if self.bilesim[ix.row()].get("zenginlik") is not None:
                # eski dosyadaki gecersiz deger: yalnizca silinebilsin
                return temel | QtCore.Qt.ItemIsEditable
            return QtCore.Qt.ItemIsSelectable          # gri, duzenlenemez
        return temel | QtCore.Qt.ItemIsEditable

    def satir_ekle(self):
        self.beginInsertRows(QtCore.QModelIndex(), len(self.bilesim), len(self.bilesim))
        self.bilesim.append({"tur": "element", "isim": "", "miktar": 1.0, "birim": "ao"})
        self.endInsertRows()

    def satir_sil(self, satir):
        if 0 <= satir < len(self.bilesim):
            self.beginRemoveRows(QtCore.QModelIndex(), satir, satir)
            self.bilesim.pop(satir)
            self.endRemoveRows()


class SecenekDelegesi(QtWidgets.QStyledItemDelegate):
    """Hucreyi acilir listeyle duzenler; model ANAHTARI yazar, etiketi gosterir."""

    def __init__(self, secenekler, parent=None):
        super().__init__(parent)
        self.secenekler = tuple(secenekler)

    def createEditor(self, ebeveyn, secenek, ix):
        c = QtWidgets.QComboBox(ebeveyn)
        for anahtar, etiket in self.secenekler:
            c.addItem(etiket, anahtar)
        c.activated.connect(lambda _i, c=c: (self.commitData.emit(c),
                                             self.closeEditor.emit(c)))
        return c

    def setEditorData(self, editor, ix):
        i = editor.findData(ix.data(QtCore.Qt.EditRole))
        editor.setCurrentIndex(max(i, 0))

    def setModelData(self, editor, model, ix):
        model.setData(ix, editor.currentData(), QtCore.Qt.EditRole)


def _bilesim_tablosu(model):
    t = QtWidgets.QTableView()
    t.setModel(model)
    t.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    t.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    t.horizontalHeader().setStretchLastSection(True)
    t.verticalHeader().setDefaultSectionSize(26)
    t.setMinimumHeight(150)
    if not model.salt_okunur:
        t.setItemDelegateForColumn(model.S_TUR, SecenekDelegesi(TUR_SECENEKLERI, t))
        t.setItemDelegateForColumn(model.S_BIRIM, SecenekDelegesi(BIRIM_SECENEKLERI, t))
        t.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked
                          | QtWidgets.QAbstractItemView.SelectedClicked
                          | QtWidgets.QAbstractItemView.EditKeyPressed
                          | QtWidgets.QAbstractItemView.AnyKeyPressed)
    else:
        t.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    for s, g in ((0, 130), (1, 80), (2, 100), (3, 120)):
        t.setColumnWidth(s, g)
    return t
