# -*- coding: utf-8 -*-
"""
 arayuz/malzeme/turetilmis_panel.py  --  TuretilmisPanel: malzemenin anlik
 turetilmis degerleri (cekirdek/malzeme_hesap.turetilmis)

   yogunluk g/cm3 ve atom/b-cm, ortalama molar kutle, gHM/cm3, H/X,
   nuklid tablosu (N_i, atomca %, agirlikca %).
 Hesap cekirdektedir; burada yalnizca gosterilir. Hesap hatasi (negatif
 miktar, karisik ao/wo ...) panelde metin olarak gorunur, sessiz kalmaz.
"""

from PySide6 import QtCore, QtWidgets

from cekirdek import malzeme_hesap as mh
from cekirdek.ceviri import _, N_
from arayuz.malzeme.yardimcilar import _hata_etiketi, _ozet_etiketi
from arayuz.tasarim import tokenlar

A = tokenlar.ARALIK
_YUZDE = 100.0


class TuretilmisPanel(QtWidgets.QWidget):
    """Ozet satirlari + nuklid tablosu; guncelle(m) ya da guncelle(None, hata)."""

    BASLIKLAR = (N_("Nüklid"), "N [atom/b-cm]", N_("Atomca %"), N_("Ağırlıkça %"))

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ozet = _ozet_etiketi()
        self.hata = _hata_etiketi()
        for e in (self.ozet, self.hata):          # metin dosyadan gelebilir (PNNL, kutuphane)
            e.setTextFormat(QtCore.Qt.PlainText)
        self.tablo = QtWidgets.QTableWidget(0, len(self.BASLIKLAR))
        self.tablo.setHorizontalHeaderLabels([_(b) for b in self.BASLIKLAR])
        self.tablo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.setAlternatingRowColors(True)
        self.tablo.setShowGrid(False)
        baslik = QtWidgets.QLabel(_("Türetilmiş değerler"))
        baslik.setObjectName("kartBaslik")
        d = QtWidgets.QVBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(A["s"])
        d.addWidget(baslik)
        d.addWidget(self.ozet)
        d.addWidget(self.hata)
        d.addWidget(self.tablo, 1)

    def metin(self):
        """Gorunen ozet + hata + tablo (testler ve ekran okuyucu icin)."""
        satirlar = [self.ozet.text(), self.hata.text() if self.hata.isVisibleTo(self) else ""]
        for i in range(self.tablo.rowCount()):
            satirlar.append(" ".join(self.tablo.item(i, j).text()
                                     for j in range(self.tablo.columnCount())))
        return "\n".join(s for s in satirlar if s)

    def guncelle(self, m, hata=None):
        if m is not None and hata is None:
            try:
                t = mh.turetilmis(m)
            except ValueError as e:          # kullaniciya gosterilir
                hata, t = str(e), None
        else:
            t = None
        self.hata.setText(hata or "")
        self.hata.setVisible(bool(hata))
        if t is None:
            self.ozet.setText("")
            self.tablo.setRowCount(0)
            return
        self.ozet.setText(self._ozet_metni(t))
        self._tablo_doldur(t)

    @staticmethod
    def _ozet_metni(t):
        satirlar = [
            _("Yoğunluk: {rho:.5g} g/cm³  =  {n:.4e} atom/b-cm").format(
                rho=t["yogunluk_gcm3"], n=t["N_toplam"]),
            _("Atom başına ortalama molar kütle: {m:.4f} g/mol").format(m=t["ortalama_kutle"]),
        ]
        if t["agir_metal_gcm3"] > 0.0:
            satirlar.append(_("Ağır metal: {hm:.4f} gHM/cm³").format(hm=t["agir_metal_gcm3"]))
        if t["H_X"] is not None:
            satirlar.append(_("H/X (hidrojen / fisil atom): {hx:.4g}").format(hx=t["H_X"]))
        return "\n".join(satirlar)

    def _tablo_doldur(self, t):
        n = t["nuklidler"]
        kesir = {k: v / t["N_toplam"] for k, v in n.items()}
        agirlik = mh.ao_to_wo(kesir)
        self.tablo.setRowCount(0)
        for nk in sorted(n, key=lambda k: (mh.atom_numarasi(k), k)):
            i = self.tablo.rowCount()
            self.tablo.insertRow(i)
            for j, metin in enumerate((nk, "%.4e" % n[nk], "%.4f" % (_YUZDE * kesir[nk]),
                                       "%.4f" % (_YUZDE * agirlik[nk]))):
                oge = QtWidgets.QTableWidgetItem(metin)
                if j:
                    oge.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                self.tablo.setItem(i, j, oge)
        self.tablo.resizeColumnsToContents()
