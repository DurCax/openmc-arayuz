# -*- coding: utf-8 -*-
"""
================================================================================
 hex_izgara.py  --  Altigen kafes harita editoru
================================================================================
 Kare kafeslerde QTableWidget yeterli ama altigen kafeste hucre komsuluklari
 bir tabloya oturmaz. Bu widget hucreleri gercek geometrik konumlarinda cizer;
 konumlar cekirdek/altigen.py'den gelir, yani cizim ile kurulan model AYNI
 kaynagi kullanir -- editorde gordugun yerlesim modeldekiyle birebir aynidir.

 ETKILESIM
   Sol tik / suruklе : secili firca harfini hucreye yazar
   Sag tik           : o hucrenin harfini firca yapar (renk secici gibi)
   Tekerlek          : yakinlastir / uzaklastir
================================================================================
"""

import math

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import altigen

# Harf renkleri -- sekme_demet ile ayni palet
_PALET = [(222, 93, 40), (90, 150, 220), (150, 150, 160), (120, 200, 140),
          (200, 170, 90), (170, 120, 200), (90, 190, 190), (210, 130, 160),
          (130, 160, 110), (190, 190, 120)]


def harf_rengi(harfler, harf):
    """Harfe gore sabit bir renk; tanimsiz harf gri."""
    if harf not in harfler:
        return QtGui.QColor(225, 225, 225)
    return QtGui.QColor(*_PALET[harfler.index(harf) % len(_PALET)])


class HexIzgara(QtWidgets.QWidget):
    """Altigen kafes haritasini cizen ve duzenleyen tuval."""

    degisti = QtCore.Signal()
    firca_istendi = QtCore.Signal(str)      # sag tik ile harf secildi

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 320)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setMouseTracking(True)

        self.harita = []            # halka dizeleri, distan ice
        self.halka_sayisi = 0
        self.yonelim = "y"
        self.harfler = []           # sirali tanimli harfler (renk icin)
        self.firca = None
        self.etiket_goster = False

        self._konumlar = {}         # (r, i) -> (x, y) birim adimda
        self._olcek = 1.0
        self._merkez = QtCore.QPointF(0, 0)
        self._yakinlastirma = 1.0
        self._vurgulu = None
        self._basili = False

    # ------------------------------------------------------------------
    def yukle(self, harita, halka_sayisi, yonelim, harfler):
        self.harita = [list(s) for s in (harita or [])]
        self.halka_sayisi = halka_sayisi
        self.yonelim = yonelim or "y"
        self.harfler = list(harfler or [])
        self._konumlar = altigen.konumlar(halka_sayisi, self.yonelim) if halka_sayisi else {}
        self.update()

    def firca_ayarla(self, harf):
        self.firca = harf

    def harita_metni(self):
        return ["".join(s) for s in self.harita]

    def etiketleri_goster(self, acik):
        self.etiket_goster = acik
        self.update()

    # ------------------------------------------------------------------
    def _olcegi_hesapla(self):
        """Tuvale sigacak olcegi ve merkezi hesaplar."""
        if not self._konumlar:
            self._olcek = 1.0
            return
        xs = [x for x, _ in self._konumlar.values()]
        ys = [y for _, y in self._konumlar.values()]
        genislik = (max(xs) - min(xs)) + 2.0 / math.sqrt(3)
        yukseklik = (max(ys) - min(ys)) + 2.0 / math.sqrt(3)
        kenar_bosluk = 12
        ex = (self.width() - 2 * kenar_bosluk) / max(genislik, 1e-6)
        ey = (self.height() - 2 * kenar_bosluk) / max(yukseklik, 1e-6)
        self._olcek = min(ex, ey) * self._yakinlastirma
        self._merkez = QtCore.QPointF(self.width() / 2.0, self.height() / 2.0)

    def _ekran(self, x, y):
        """Birim adim koordinatlarini ekran koordinatina cevirir (y ters)."""
        return QtCore.QPointF(self._merkez.x() + x * self._olcek,
                              self._merkez.y() - y * self._olcek)

    def _hucre_bul(self, nokta):
        """Ekran noktasina en yakin hucreyi dondurur (yeterince yakinsa)."""
        if not self._konumlar:
            return None
        en_iyi, en_kucuk = None, None
        esik = (self._olcek / math.sqrt(3)) ** 2
        for anahtar, (x, y) in self._konumlar.items():
            p = self._ekran(x, y)
            d = (p.x() - nokta.x()) ** 2 + (p.y() - nokta.y()) ** 2
            if en_kucuk is None or d < en_kucuk:
                en_kucuk, en_iyi = d, anahtar
        return en_iyi if en_kucuk is not None and en_kucuk <= esik else None

    def _harf_al(self, anahtar):
        r, i = anahtar
        if 0 <= r < len(self.harita) and 0 <= i < len(self.harita[r]):
            return self.harita[r][i]
        return "."

    def _harf_yaz(self, anahtar, harf):
        r, i = anahtar
        if 0 <= r < len(self.harita) and 0 <= i < len(self.harita[r]):
            if self.harita[r][i] != harf:
                self.harita[r][i] = harf
                return True
        return False

    # ------------------------------------------------------------------
    def paintEvent(self, _olay):
        self._olcegi_hesapla()
        boya = QtGui.QPainter(self)
        boya.setRenderHint(QtGui.QPainter.Antialiasing)
        boya.fillRect(self.rect(), self.palette().base())

        if not self._konumlar:
            boya.setPen(QtGui.QColor(140, 140, 140))
            boya.drawText(self.rect(), QtCore.Qt.AlignCenter,
                          "Altigen kafes tanimli degil")
            return

        # Tek hucrenin kose acilari: kafes yonelimine bagli
        aci_derece = altigen.hucre_kose_acilari(self.yonelim)
        yaricap = self._olcek / math.sqrt(3)        # cevrel yaricap (ekran)
        kalem = QtGui.QPen(QtGui.QColor(70, 70, 70))
        kalem.setWidthF(max(0.6, self._olcek * 0.03))

        yazi = boya.font()
        yazi.setPointSizeF(max(5.0, self._olcek * 0.28))
        boya.setFont(yazi)

        for anahtar, (x, y) in sorted(self._konumlar.items()):
            merkez = self._ekran(x, y)
            cokgen = QtGui.QPolygonF([
                QtCore.QPointF(merkez.x() + yaricap * math.cos(math.radians(a)),
                               merkez.y() - yaricap * math.sin(math.radians(a)))
                for a in aci_derece])
            harf = self._harf_al(anahtar)
            renk = harf_rengi(self.harfler, harf)
            if anahtar == self._vurgulu:
                renk = renk.lighter(125)
            boya.setBrush(QtGui.QBrush(renk))
            boya.setPen(kalem)
            boya.drawPolygon(cokgen)

            if self._olcek > 14:
                boya.setPen(QtGui.QColor(30, 30, 30))
                metin = ("%d,%d" % anahtar) if self.etiket_goster else harf
                boya.drawText(QtCore.QRectF(merkez.x() - yaricap, merkez.y() - yaricap,
                                            2 * yaricap, 2 * yaricap),
                              QtCore.Qt.AlignCenter, metin)

        # bilgi serit
        boya.setPen(QtGui.QColor(120, 120, 120))
        boya.drawText(6, self.height() - 6,
                      "%d halka, %d hucre  |  sol tik: boya, sag tik: firca sec, "
                      "tekerlek: yakinlastir"
                      % (self.halka_sayisi, altigen.toplam_hucre(self.halka_sayisi)))

    # ------------------------------------------------------------------
    def mousePressEvent(self, olay):
        anahtar = self._hucre_bul(olay.position())
        if anahtar is None:
            return
        if olay.button() == QtCore.Qt.RightButton:
            self.firca_istendi.emit(self._harf_al(anahtar))
            return
        self._basili = True
        if self.firca and self._harf_yaz(anahtar, self.firca):
            self.update()
            self.degisti.emit()

    def mouseMoveEvent(self, olay):
        anahtar = self._hucre_bul(olay.position())
        if anahtar != self._vurgulu:
            self._vurgulu = anahtar
            self.update()
        if self._basili and anahtar and self.firca:
            if self._harf_yaz(anahtar, self.firca):
                self.update()
                self.degisti.emit()

    def mouseReleaseEvent(self, _olay):
        self._basili = False

    def leaveEvent(self, _olay):
        self._vurgulu = None
        self.update()

    def wheelEvent(self, olay):
        adim = 1.15 if olay.angleDelta().y() > 0 else 1 / 1.15
        self._yakinlastirma = max(0.4, min(6.0, self._yakinlastirma * adim))
        self.update()

    def yakinlastirmayi_sifirla(self):
        self._yakinlastirma = 1.0
        self.update()

    # ------------------------------------------------------------------
    def tumunu_doldur(self, harf):
        degisti = False
        for r in range(len(self.harita)):
            for i in range(len(self.harita[r])):
                if self.harita[r][i] != harf:
                    self.harita[r][i] = harf
                    degisti = True
        if degisti:
            self.update()
            self.degisti.emit()

    def halkayi_doldur(self, halka_indeksi, harf):
        if not (0 <= halka_indeksi < len(self.harita)):
            return
        degisti = False
        for i in range(len(self.harita[halka_indeksi])):
            if self.harita[halka_indeksi][i] != harf:
                self.harita[halka_indeksi][i] = harf
                degisti = True
        if degisti:
            self.update()
            self.degisti.emit()
