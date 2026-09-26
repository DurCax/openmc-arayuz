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
import string

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import altigen, sema

# Tanimsiz (anahtarda karsiligi olmayan) hucre icin harita karakteri.
BOS_HARF = "."

# Otomatik harf adaylari -- ASCII: harf haritasi dosyada okunur kalmali.
_HARF_ADAYLARI = string.ascii_lowercase + string.ascii_uppercase + string.digits

# Ayirt edilebilir kategorik palet (acik ve koyu zeminde okunur).
_PALET = [(222, 93, 40), (90, 150, 220), (120, 190, 110), (200, 170, 70),
          (160, 110, 200), (70, 180, 180), (215, 120, 160), (150, 150, 160),
          (130, 100, 70), (40, 110, 170), (190, 60, 60), (100, 140, 60)]
_BOSLUK_RENGI = (55, 58, 64)
_TANIMSIZ_RENGI = (200, 200, 205)


# ============================================================================
# saf yardimcilar
# ============================================================================

def harita_adlara(harita, anahtar):
    """
    Harf haritasini parca adlarina cevirir.

    harita : ["yyk", ...]  (kare: satirlar, altigen: DISTAN ICE halkalar)
    anahtar: {"y": "yakit_cubugu", ...}
    DONER  : [["yakit_cubugu", ...], ...]; anahtarda olmayan harf -> None
    """
    anahtar = anahtar or {}
    return [[anahtar.get(h) for h in satir] for satir in (harita or [])]


def _yeni_harf(ad, kullanilan):
    """
    Yeni bir parca icin harf: once adin ilk harfi (kucuk, sonra buyuk) --
    "yakit_cubugu" -> y, "kilavuz_boru" -> k -- dolu ise a-z, A-Z, 0-9 sirasi.
    Deterministiktir: ayni girdi her zaman ayni harfi verir.
    """
    adaylar = []
    ilk = next((ch for ch in str(ad) if ch.isascii() and ch.isalnum()), None)
    if ilk:
        adaylar += [ilk.lower(), ilk.upper()]
    adaylar += list(_HARF_ADAYLARI)
    for h in adaylar:
        if h not in kullanilan:
            return h
    raise ValueError("haritada en fazla %d farklı parça kullanılabilir"
                     % len(_HARF_ADAYLARI))


def adlardan_harita(adlar, eski_anahtar=None, eski_harita=None):
    """
    Parca adlari izgarasindan (harita, anahtar) uretir.

    adlar       : [[ad | None, ...], ...]  (harita_adlara'nin bicimi)
    eski_anahtar: dosyadaki mevcut anahtar. Butun girdileri AYNEN korunur
                  (kullanilmayanlar dahil: dosya gereksiz yere degismesin);
                  yeni parcalar sona eklenir.
    eski_harita : dosyadaki mevcut harita. Verilirse her hucre, eski harfi
                  hala AYNI parcayi gosteriyorsa o harfi korur. Bu olmadan
                  ayni parcaya iki harf veren dosyalar (pwr_17x17: kilavuz
                  borusu 'k', enstruman borusu 'e') birebir geri yazilamazdi.
    Hucre adi None ise (tanimsiz) BOS_HARF yazilir -- dogrulama bunu
    "tanimsiz harf" olarak yakalar; sessizce bir parcaya cevrilmez.

    Ayni parca icin birden fazla eski harf varsa (ve konum bilgisi yoksa)
    anahtardaki ILK harf kullanilir.
    """
    anahtar = dict(eski_anahtar or {})
    tercih = {}
    for h, ad in anahtar.items():
        tercih.setdefault(ad, h)
    kullanilan = set(anahtar) | {BOS_HARF}
    for satir in (eski_harita or []):
        kullanilan.update(satir)

    harita = []
    for r, satir in enumerate(adlar or []):
        eski_satir = (eski_harita[r] if eski_harita is not None
                      and r < len(eski_harita) else "")
        yeni = []
        for c, ad in enumerate(satir):
            eski_h = eski_satir[c] if c < len(eski_satir) else None
            if eski_h is not None and anahtar.get(eski_h) == ad:
                yeni.append(eski_h)
            elif ad is None:
                yeni.append(BOS_HARF)
            elif ad in tercih:
                yeni.append(tercih[ad])
            else:
                h = _yeni_harf(ad, kullanilan)
                anahtar[h] = ad
                tercih[ad] = h
                kullanilan.add(h)
                yeni.append(h)
        harita.append("".join(yeni))
    return harita, anahtar


def _mesafe(a, b):
    return math.sqrt(sum((int(x) - int(y)) ** 2 for x, y in zip(a, b)))


def _malzeme_rengi(spec, ad):
    for m in spec.get("malzemeler", []):
        if m["ad"] == ad and m.get("renk"):
            return tuple(int(x) for x in m["renk"][:3])
    return None


def _parca_rengi(spec, ad, derinlik=0):
    """Parcanin dogal rengi: cubukta en ic bolgenin, plakada yakit etinin,
    kafeste en cok kullanilan parcanin, malzemede kendi rengi."""
    if ad == "bosluk":
        return _BOSLUK_RENGI
    for c in spec.get("cubuklar", []):
        if c["ad"] == ad:
            for b in c.get("bolgeler", []):
                r = _malzeme_rengi(spec, b.get("malzeme"))
                if r:
                    return r
            return None
    for p in spec.get("plakalar", []):
        if p["ad"] == ad:
            return _malzeme_rengi(spec, p.get("et_malzeme"))
    for d in spec.get("demetler", []):
        if d["ad"] == ad and derinlik < 4:
            sayac = {}
            for satir in d.get("harita") or []:
                for h in satir:
                    sayac[h] = sayac.get(h, 0) + 1
            for h, _n in sorted(sayac.items(), key=lambda x: -x[1]):
                hedef = (d.get("anahtar") or {}).get(h)
                if hedef and hedef != ad:
                    return _parca_rengi(spec, hedef, derinlik + 1)
            return None
    return _malzeme_rengi(spec, ad)


_TUR_ETIKETI = {"cubuk": "çubuk", "plaka": "plaka", "demet": "kafes",
                "malzeme": "malzeme", "bosluk": "boşluk"}


def palet_ogeleri(spec, turler=("cubuk", "plaka", "demet", "malzeme", "bosluk"),
                  haric=()):
    """
    Spec'teki parcalardan palet girdileri: [(ad, etiket, rgb, tur_etiketi)].

    Renkler birbirinden AYIRT EDILIR: iki parcanin dogal rengi yakinsa
    (or. ikisi de su ile dolu iki boru) sonraki kategorik palet rengi verilir.
    haric: listelenmeyecek adlar (or. kendi icine yerlestirilemeyen kafes).
    """
    ogeler = []
    for tur in turler:
        if tur == "bosluk":
            ogeler.append(("bosluk", "Boş (madde yok)", "bosluk"))
            continue
        liste = {"cubuk": "cubuklar", "plaka": "plakalar", "demet": "demetler",
                 "malzeme": "malzemeler"}[tur]
        for x in spec.get(liste, []):
            # Malzemeler her listede ayni bicimde: "ad — aciklama".
            etiket = (sema.malzeme_etiketi(x) if tur == "malzeme"
                      else x["ad"].replace("_", " "))
            ogeler.append((x["ad"], etiket, tur))
    sonuc, kullanilan = [], []
    yedek = iter(_PALET * 4)
    for ad, etiket, tur in ogeler:
        if ad in haric:
            continue
        rgb = _parca_rengi(spec, ad)
        if rgb is None or any(_mesafe(rgb, u) < 60 for u in kullanilan):
            rgb = None
            for aday in yedek:
                if all(_mesafe(aday, u) >= 60 for u in kullanilan):
                    rgb = aday
                    break
            if rgb is None:
                rgb = _PALET[len(sonuc) % len(_PALET)]
        kullanilan.append(rgb)
        sonuc.append((ad, etiket, rgb, _TUR_ETIKETI[tur]))
    return sonuc


def _qrenk(deger):
    if isinstance(deger, QtGui.QColor):
        return QtGui.QColor(deger)
    if deger is None:
        return QtGui.QColor(*_TANIMSIZ_RENGI)
    return QtGui.QColor(*[int(x) for x in deger[:3]])


def _yazi_rengi(zemin):
    """Zemine gore okunur yazi rengi (siyah/beyaz)."""
    parlaklik = 0.299 * zemin.red() + 0.587 * zemin.green() + 0.114 * zemin.blue()
    return QtGui.QColor(20, 20, 20) if parlaklik > 150 else QtGui.QColor(250, 250, 250)


def _renk_karesi(rgb, boyut=18):
    """Kenarli, yuvarlatilmis renk karesi simgesi."""
    pix = QtGui.QPixmap(boyut, boyut)
    pix.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pix)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    # Orta gri kenar: hem acik hem koyu zeminde koyu/acik renkli kare secilir.
    p.setPen(QtGui.QPen(QtGui.QColor(128, 128, 128, 200), 1))
    p.setBrush(_qrenk(rgb))
    p.drawRoundedRect(QtCore.QRectF(1.5, 1.5, boyut - 3, boyut - 3), 4, 4)
    p.end()
    simge = QtGui.QIcon()
    # Secili satirda stil simgeyi vurgu rengiyle BOYUYORDU (turuncu -> kahve):
    # renk karesi her durumda ayni gorunmeli.
    for kip in (QtGui.QIcon.Normal, QtGui.QIcon.Selected, QtGui.QIcon.Active):
        simge.addPixmap(pix, kip)
    return simge


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
                w.setToolTip("%s%s — seçip ızgarada tıklayın ya da sürükleyin"
                             % (etiket, (" (%s)" % tur) if tur else ""))
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
        return self._etiket.get(ad, ad or "tanımsız")


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
        return "Izgara boş"

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
        if self._vurgulu is not None:
            for anahtar, cokgen, _m in geo:
                if anahtar == self._vurgulu:
                    vurgu = QtGui.QPen(pal.color(QtGui.QPalette.Highlight))
                    vurgu.setWidthF(2.0)
                    boya.setPen(vurgu)
                    boya.setBrush(QtCore.Qt.NoBrush)
                    boya.drawPolygon(cokgen)
                    break

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
        return "Kafes tanımlı değil"

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
        return "satır %d, sütun %d: %s" % (r + 1, c + 1, ad if ad else "tanımsız")


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
        return "Altıgen kafes tanımlı değil"

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
        return "%d. halka (dıştan), %d. hücre: %s" % (r + 1, i + 1, ad if ad else "tanımsız")

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
