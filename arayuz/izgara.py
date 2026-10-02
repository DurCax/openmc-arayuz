# -*- coding: utf-8 -*-
"""
================================================================================
 izgara.py  --  Parca paleti ve boyanabilir kafes izgaralari (kare / altigen)
================================================================================
 KULLANICI HARF GORMEZ.
   Spec haritayi harflerle tutar ("yyk..." + anahtar {"y": "yakit_cubugu"}).
   Harf, kullanicinin ogrenmesi gereken ikinci bir dil demekti: once harfi
   tanimla, sonra harfi fircaya al, sonra boya. Bu modulun bilesenleri PARCA
   ADLARIYLA calisir: kullanici paletten bir parca secer (firca) ve izgarayi
   tiklayip SURUKLEYEREK boyar. Harfler kayit aninda otomatik atanir
   (adlardan_harita) ve mevcut harfler MUMKUN OLDUGUNCA KORUNUR -- kaydedilen
   dosyalar gereksiz yere degismez, eski dosyalar birebir geri yazilir.

 SAF YARDIMCILAR (Qt gerektirmez; testler/test_kabuk.py sinar)
   harita_adlara(harita, anahtar)
       -> [[ad | None, ...], ...]   (kare: satirlar; altigen: halkalar)
   adlardan_harita(adlar, eski_anahtar=None, eski_harita=None)
       -> (harita, anahtar)
   palet_ogeleri(spec, turler=..., haric=())
       -> [(ad, etiket, rgb, tur_etiketi), ...]  birbirinden ayirt edilen renkler

 BILESENLER
   ParcaPaleti   : renk karesi + ad listesi; tek secim = firca; secildi(ad)
   KareIzgara    : nx x ny hucre; tikla-surukle boyama; degisti
   AltigenIzgara : halka duzeni (cekirdek/altigen.py ile AYNI konumlar);
                   ayni etkilesim (eski arayuz/hex_izgara.py'nin parca-adli
                   genellemesi; o dosya Dalga 3'te kaldirildi).

 ETKILESIM (iki izgara icin ayni)
   Sol tik / surukle : secili parcayi hucrelere boyar. Bir darbe (bas-surukle-
                       birak) TEK degisiklik sayilir: degisti bir kez yayilir,
                       geri al da tek adimda geri alir.
   Sag tik           : o hucredeki parcayi firca yapar (firca_istendi).
================================================================================
"""

import math

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import altigen
from cekirdek.ceviri import _
from arayuz.izgara_yardimci import (  # noqa: F401 -- tasindi (T2), adlar burada da
    BOS_HARF, _BOSLUK_RENGI, _HARF_ADAYLARI, _PALET, _TANIMSIZ_RENGI, _TUR_ETIKETI,
    _malzeme_rengi, _mesafe, _parca_rengi, _qrenk, _renk_karesi, _yazi_rengi, _yeni_harf,
    adlardan_harita, harita_adlara, palet_ogeleri)


# ============================================================================
# ParcaPaleti
# ============================================================================

class ParcaPaleti(QtWidgets.QWidget):
    """
    Dikey parca listesi: renk karesi + okunur ad. Tek secim = gecerli firca.
    secildi(ad) secim her degistiginde yayilir.
    """

    secildi = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.liste = QtWidgets.QListWidget()
        self.liste.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.liste.setIconSize(QtCore.QSize(18, 18))
        self.liste.setUniformItemSizes(True)
        self.liste.setSpacing(1)
        self.liste.setMinimumWidth(150)
        self.liste.currentItemChanged.connect(self._secim_degisti)
        self._rgb = {}
        self._etiket = {}
        d = QtWidgets.QVBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        d.addWidget(self.liste)

    def parcalari_ayarla(self, parcalar, secili=None):
        """
        parcalar: [(ad, etiket, rgb)] ya da [(ad, etiket, rgb, tur_etiketi)]
                  (palet_ogeleri'nin ciktisi dogrudan verilebilir).
        Onceki secim hala listede ise korunur; yoksa ilk parca secilir.
        """
        onceki = secili if secili is not None else self.secili()
        self.liste.blockSignals(True)
        try:
            self.liste.clear()
            self._rgb, self._etiket = {}, {}
            for oge in parcalar:
                ad, etiket, rgb = oge[0], oge[1], oge[2]
                tur = oge[3] if len(oge) > 3 else ""
                self._rgb[ad] = tuple(rgb) if rgb is not None else None
                self._etiket[ad] = etiket
                w = QtWidgets.QListWidgetItem(_renk_karesi(rgb), etiket)
                w.setData(QtCore.Qt.UserRole, ad)
                w.setToolTip(_("%s%s — seçip ızgarada tıklayın ya da sürükleyin")
                             % (etiket, (" (%s)" % _(tur)) if tur else ""))
                self.liste.addItem(w)
            hedef = self._satir(onceki)
            if hedef < 0 and self.liste.count():
                hedef = 0
            self.liste.setCurrentRow(hedef)
        finally:
            self.liste.blockSignals(False)
        ad = self.secili()
        if ad is not None:
            self.secildi.emit(ad)

    def _satir(self, ad):
        for i in range(self.liste.count()):
            if self.liste.item(i).data(QtCore.Qt.UserRole) == ad:
                return i
        return -1

    def _secim_degisti(self, simdiki, _onceki):
        if simdiki is not None:
            self.secildi.emit(simdiki.data(QtCore.Qt.UserRole))

    def sec(self, ad):
        """Parcayi programla secer; bulunamazsa False."""
        i = self._satir(ad)
        if i < 0:
            return False
        self.liste.setCurrentRow(i)
        return True

    def secili(self):
        oge = self.liste.currentItem()
        return oge.data(QtCore.Qt.UserRole) if oge is not None else None

    def adlar(self):
        return [self.liste.item(i).data(QtCore.Qt.UserRole)
                for i in range(self.liste.count())]

    def renkler(self):
        """{ad: QColor} -- izgaralara dogrudan verilir."""
        return {ad: _qrenk(rgb) for ad, rgb in self._rgb.items()}

    def etiket(self, ad):
        return self._etiket.get(ad, ad or _("tanımsız"))


# ============================================================================
# ortak boyama tuvali
# ============================================================================

class _BoyaTuvali(QtWidgets.QWidget):
    """KareIzgara ve AltigenIzgara'nin ortak cizim/fare mantigi."""

    degisti = QtCore.Signal()               # bir firca darbesi haritayi degistirdi
    firca_istendi = QtCore.Signal(str)      # sag tik: hucrenin parcasi

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(120, 120)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._adlar = []
        self._renkler = {}
        self._kisaltma = {}
        self._firca = None
        self._etiket_goster = False
        self._geo = None                    # [(anahtar, QPolygonF, merkez)]
        self._geo_boyut = None
        self._olcek = 1.0
        self._basili = False
        self._darbe_degisti = False
        self._son_nokta = None
        self._vurgulu = None
        self._salt_okunur = False
        self._isaretler, self._isaret_rengi = {}, None     # kesik konumlar (Dalga G)

    # ---------------- API ----------------
    def adlar(self):
        """Parca adlari izgarasinin KOPYASI (satirlar / halkalar)."""
        return [list(s) for s in self._adlar]

    def firca_ayarla(self, ad):
        self._firca = ad

    def firca(self):
        return self._firca

    def renkleri_ayarla(self, renkler):
        """renkler: {ad: QColor | (r, g, b)}"""
        self._renkler = {ad: _qrenk(r) for ad, r in (renkler or {}).items()}
        self.update()

    def kisaltmalari_ayarla(self, kisaltmalar):
        """Hucre etiketi olarak gosterilecek kisa metinler {ad: "YK"}."""
        self._kisaltma = dict(kisaltmalar or {})
        self.update()

    def etiketleri_goster(self, acik):
        self._etiket_goster = bool(acik)
        self.update()

    def isaretleri_ayarla(self, isaretler, renk=None):
        """Kesik / gizli konumlari tarar: {anahtar: "kesik"|"gizli"}; renk: QColor."""
        self._isaretler = dict(isaretler or {})
        self._isaret_rengi = QtGui.QColor(renk) if renk is not None else None
        self.update()

    def salt_okunur(self, acik=True):
        self._salt_okunur = bool(acik)

    def hucre_adi(self, anahtar):
        return self._ad_al(anahtar)

    def hucreyi_boya(self, anahtar, ad):
        """Programla boyar; degistiyse True (degisti YAYILMAZ)."""
        if self._ad_yaz(anahtar, ad):
            self.update()
            return True
        return False

    def tumunu_doldur(self, ad):
        degisti = False
        for anahtar, _p, _m in self._geometri():
            degisti = self._ad_yaz(anahtar, ad) or degisti
        if degisti:
            self.update()
            self.degisti.emit()
        return degisti

    def hucre_merkezi(self, anahtar):
        """Hucrenin ekran merkezi (QPointF) -- testler sentetik fare olayi icin kullanir."""
        for a, _p, m in self._geometri():
            if a == anahtar:
                return QtCore.QPointF(m)
        return None

    # ---------------- alt sinif ----------------
    def _geometri_kur(self):
        raise NotImplementedError

    def _ad_al(self, anahtar):
        raise NotImplementedError

    def _ad_yaz(self, anahtar, ad):
        raise NotImplementedError

    def _hucre_bul(self, nokta):
        raise NotImplementedError

    def _bos_metin(self):
        return _("Izgara boş")

    def _ipucu(self, anahtar):
        return ""

    # ---------------- geometri onbellegi ----------------
    def _geometri(self):
        # Onbellek boyuta baglidir: gizli bir widget resize() edildiginde
        # resizeEvent gosterilene kadar GELMEZ; eski olcekle hucre bulunurdu.
        boyut = (self.width(), self.height())
        if self._geo is None or self._geo_boyut != boyut:
            self._geo = self._geometri_kur()
            self._geo_boyut = boyut
        return self._geo

    def _gecersiz(self):
        self._geo = None
        self.update()

    def resizeEvent(self, olay):
        self._geo = None
        super().resizeEvent(olay)

    # ---------------- cizim ----------------
    def _hucre_rengi(self, ad):
        if ad is None:
            return QtGui.QColor(*_TANIMSIZ_RENGI)
        if ad in self._renkler:
            return QtGui.QColor(self._renkler[ad])
        # Renk verilmemis parca: ada bagli SABIT renk (hash() surecten surece
        # degisir; kullanici her acilista baska renk gormesin).
        return _qrenk(_PALET[sum(map(ord, str(ad))) % len(_PALET)])

    def _etiket_metni(self, anahtar, ad):
        if ad is None:
            return "?"
        if ad in self._kisaltma:
            return self._kisaltma[ad]
        parca = [p for p in str(ad).replace("-", "_").split("_") if p]
        return "".join(p[0] for p in parca[:2]).upper() or str(ad)[:2]

    def paintEvent(self, _olay):
        boya = QtGui.QPainter(self)
        boya.setRenderHint(QtGui.QPainter.Antialiasing)
        pal = self.palette()
        boya.fillRect(self.rect(), pal.base())
        geo = self._geometri()
        if not geo:
            boya.setPen(pal.color(QtGui.QPalette.PlaceholderText))
            boya.drawText(self.rect(), QtCore.Qt.AlignCenter, self._bos_metin())
            return
        kenar = QtGui.QColor(pal.color(QtGui.QPalette.Mid)).darker(135)
        kalem = QtGui.QPen(kenar)
        kalem.setWidthF(max(0.6, min(1.4, self._olcek * 0.04)))
        yazi = boya.font()
        yazi.setPointSizeF(max(6.0, min(11.0, self._olcek * 0.30)))
        boya.setFont(yazi)
        etiket_sigar = self._etiket_goster and self._olcek >= 16
        for anahtar, cokgen, merkez in geo:
            ad = self._ad_al(anahtar)
            renk = self._hucre_rengi(ad)
            if anahtar == self._vurgulu:
                renk = renk.lighter(130)
            boya.setPen(kalem)
            if ad is None:
                boya.setBrush(QtGui.QBrush(renk, QtCore.Qt.Dense5Pattern))
            else:
                boya.setBrush(renk)
            boya.drawPolygon(cokgen)
            if etiket_sigar:
                boya.setPen(_yazi_rengi(renk))
                r = self._olcek * 0.5
                boya.drawText(QtCore.QRectF(merkez.x() - r, merkez.y() - r, 2 * r, 2 * r),
                              QtCore.Qt.AlignCenter, self._etiket_metni(anahtar, ad))
        self._isaretleri_ciz(boya, geo, pal)
        if self._vurgulu is not None:
            for anahtar, cokgen, _m in geo:
                if anahtar == self._vurgulu:
                    vurgu = QtGui.QPen(pal.color(QtGui.QPalette.Highlight))
                    vurgu.setWidthF(2.0)
                    boya.setPen(vurgu)
                    boya.setBrush(QtCore.Qt.NoBrush)
                    boya.drawPolygon(cokgen)
                    break

    def _isaretleri_ciz(self, boya, geo, pal):
        if not self._isaretler:
            return
        renk = self._isaret_rengi or pal.color(QtGui.QPalette.Highlight)
        boya.setPen(QtCore.Qt.NoPen)
        for anahtar, cokgen, _m in geo:
            durum = self._isaretler.get(anahtar)
            if durum:
                desen = QtCore.Qt.BDiagPattern if durum == "kesik" else QtCore.Qt.Dense6Pattern
                boya.setBrush(QtGui.QBrush(renk, desen))
                boya.drawPolygon(cokgen)

    # ---------------- fare ----------------
    def _boya(self, nokta):
        anahtar = self._hucre_bul(nokta)
        if anahtar is None or self._firca is None:
            return False
        return self._ad_yaz(anahtar, self._firca)

    def _yol_boyunca_boya(self, a, b):
        """Hizli surukleme hucre atlamasin: a->b dogrusu hucre boyunun 1/3'u
        adimlarla orneklenir."""
        uzunluk = math.hypot(b.x() - a.x(), b.y() - a.y())
        adim = max(2.0, self._olcek / 3.0)
        n = max(1, int(uzunluk / adim))
        degisti = False
        for k in range(1, n + 1):
            t = k / float(n)
            p = QtCore.QPointF(a.x() + (b.x() - a.x()) * t, a.y() + (b.y() - a.y()) * t)
            degisti = self._boya(p) or degisti
        return degisti

    def mousePressEvent(self, olay):
        nokta = olay.position()
        self._geometri()                    # olcek guncel olsun
        if olay.button() == QtCore.Qt.RightButton:
            anahtar = self._hucre_bul(nokta)
            ad = self._ad_al(anahtar) if anahtar is not None else None
            if ad is not None:
                self.firca_istendi.emit(ad)
            return
        if olay.button() != QtCore.Qt.LeftButton or self._salt_okunur:
            return
        self._basili = True
        self._darbe_degisti = self._boya(nokta)
        self._son_nokta = nokta
        if self._darbe_degisti:
            self.update()

    def mouseMoveEvent(self, olay):
        nokta = olay.position()
        anahtar = self._hucre_bul(nokta)
        if anahtar != self._vurgulu:
            self._vurgulu = anahtar
            self.setToolTip(self._ipucu(anahtar) if anahtar is not None else "")
            self.update()
        if self._basili and (olay.buttons() & QtCore.Qt.LeftButton):
            if self._yol_boyunca_boya(self._son_nokta or nokta, nokta):
                self._darbe_degisti = True
                self.update()
            self._son_nokta = nokta

    def mouseReleaseEvent(self, olay):
        if olay.button() != QtCore.Qt.LeftButton:
            return
        if self._basili and self._darbe_degisti:
            self.degisti.emit()
        self._basili = False
        self._darbe_degisti = False
        self._son_nokta = None

    def leaveEvent(self, _olay):
        if self._vurgulu is not None:
            self._vurgulu = None
            self.update()


# ============================================================================
# KareIzgara
# ============================================================================

class KareIzgara(_BoyaTuvali):
    """nx x ny parca izgarasi. adlar satir satir, ilk satir EN USTTE cizilir
    (spec haritasindaki satir sirasiyla ayni -- kurucu da boyle okur)."""

    def yukle(self, adlar, renkler=None):
        self._adlar = [list(s) for s in (adlar or [])]
        if renkler is not None:
            self._renkler = {ad: _qrenk(r) for ad, r in renkler.items()}
        self._vurgulu = None
        self._gecersiz()

    def boyut(self):
        """(nx, ny)"""
        ny = len(self._adlar)
        nx = max((len(s) for s in self._adlar), default=0)
        return nx, ny

    def _bos_metin(self):
        return _("Demet tanımlı değil")

    def _yerlesim(self):
        nx, ny = self.boyut()
        pay = 6
        if not nx or not ny:
            return 0.0, 0.0, 0.0
        s = max(2.0, min((self.width() - 2 * pay) / nx, (self.height() - 2 * pay) / ny))
        x0 = (self.width() - s * nx) / 2.0
        y0 = (self.height() - s * ny) / 2.0
        return s, x0, y0

    def _geometri_kur(self):
        s, x0, y0 = self._yerlesim()
        self._olcek = s
        geo = []
        for r, satir in enumerate(self._adlar):
            for c in range(len(satir)):
                dik = QtCore.QRectF(x0 + c * s, y0 + r * s, s, s)
                geo.append(((r, c), QtGui.QPolygonF(dik), dik.center()))
        return geo

    def _hucre_bul(self, nokta):
        s, x0, y0 = self._yerlesim()
        if s <= 0:
            return None
        c = int(math.floor((nokta.x() - x0) / s))
        r = int(math.floor((nokta.y() - y0) / s))
        if 0 <= r < len(self._adlar) and 0 <= c < len(self._adlar[r]):
            return (r, c)
        return None

    def _ad_al(self, anahtar):
        r, c = anahtar
        if 0 <= r < len(self._adlar) and 0 <= c < len(self._adlar[r]):
            return self._adlar[r][c]
        return None

    def _ad_yaz(self, anahtar, ad):
        r, c = anahtar
        if 0 <= r < len(self._adlar) and 0 <= c < len(self._adlar[r]):
            if self._adlar[r][c] != ad:
                self._adlar[r][c] = ad
                return True
        return False

    def _ipucu(self, anahtar):
        r, c = anahtar
        ad = self._ad_al(anahtar)
        return _("satır %d, sütun %d: %s") % (r + 1, c + 1, ad or _("tanımsız"))


# ============================================================================
# AltigenIzgara
# ============================================================================

class AltigenIzgara(_BoyaTuvali):
    """
    Altigen kafes: adlar DISTAN ICE halkalar, her halka tepeden (x yoneliminde
    sagdan) saat yonunde -- OpenMC HexLattice.universes duzeni. Konumlar
    cekirdek/altigen.py'den gelir; cizim ile kurulan model AYNI kaynagi
    kullanir.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.halka_sayisi = 0
        self.yonelim = "y"
        self._konumlar = {}

    def yukle(self, adlar, halka_sayisi=None, yonelim="y", renkler=None):
        self._adlar = [list(s) for s in (adlar or [])]
        self.halka_sayisi = int(halka_sayisi if halka_sayisi is not None
                                else len(self._adlar))
        self.yonelim = yonelim or "y"
        self._konumlar = (altigen.konumlar(self.halka_sayisi, self.yonelim)
                          if self.halka_sayisi > 0 else {})
        if renkler is not None:
            self._renkler = {ad: _qrenk(r) for ad, r in renkler.items()}
        self._vurgulu = None
        self._gecersiz()

    def _bos_metin(self):
        return _("Altıgen demet tanımlı değil")

    def _yerlesim(self):
        if not self._konumlar:
            return 0.0, QtCore.QPointF(0, 0)
        xs = [x for x, _ in self._konumlar.values()]
        ys = [y for _, y in self._konumlar.values()]
        g = (max(xs) - min(xs)) + 2.0 / math.sqrt(3)
        h = (max(ys) - min(ys)) + 2.0 / math.sqrt(3)
        pay = 8
        olcek = max(2.0, min((self.width() - 2 * pay) / max(g, 1e-6),
                             (self.height() - 2 * pay) / max(h, 1e-6)))
        return olcek, QtCore.QPointF(self.width() / 2.0, self.height() / 2.0)

    def _geometri_kur(self):
        olcek, merkez0 = self._yerlesim()
        self._olcek = olcek
        if not self._konumlar:
            return []
        acilar = altigen.hucre_kose_acilari(self.yonelim)
        # Komsu hucreler arasinda ince bir bosluk kalsin (okunurluk).
        yaricap = olcek / math.sqrt(3) * 0.97
        geo = []
        for anahtar, (x, y) in sorted(self._konumlar.items()):
            m = QtCore.QPointF(merkez0.x() + x * olcek, merkez0.y() - y * olcek)
            cokgen = QtGui.QPolygonF([
                QtCore.QPointF(m.x() + yaricap * math.cos(math.radians(a)),
                               m.y() - yaricap * math.sin(math.radians(a)))
                for a in acilar])
            geo.append((anahtar, cokgen, m))
        return geo

    def _hucre_bul(self, nokta):
        geo = self._geometri()
        if not geo:
            return None
        esik = (self._olcek / math.sqrt(3)) ** 2
        en_iyi, en_kucuk = None, None
        for anahtar, _p, m in geo:
            d = (m.x() - nokta.x()) ** 2 + (m.y() - nokta.y()) ** 2
            if en_kucuk is None or d < en_kucuk:
                en_kucuk, en_iyi = d, anahtar
        return en_iyi if en_kucuk is not None and en_kucuk <= esik else None

    def _ad_al(self, anahtar):
        r, i = anahtar
        if 0 <= r < len(self._adlar) and 0 <= i < len(self._adlar[r]):
            return self._adlar[r][i]
        return None

    def _ad_yaz(self, anahtar, ad):
        r, i = anahtar
        if 0 <= r < len(self._adlar) and 0 <= i < len(self._adlar[r]):
            if self._adlar[r][i] != ad:
                self._adlar[r][i] = ad
                return True
        return False

    def _ipucu(self, anahtar):
        r, i = anahtar
        ad = self._ad_al(anahtar)
        return _("%d. halka (dıştan), %d. hücre: %s") % (r + 1, i + 1, ad or _("tanımsız"))

    def halkayi_doldur(self, halka_indeksi, ad):
        """Bir halkanin tamamini boyar (DISTAN ICE indeks); degisti yayilir."""
        if not (0 <= halka_indeksi < len(self._adlar)):
            return False
        degisti = False
        for i in range(len(self._adlar[halka_indeksi])):
            degisti = self._ad_yaz((halka_indeksi, i), ad) or degisti
        if degisti:
            self.update()
            self.degisti.emit()
        return degisti
