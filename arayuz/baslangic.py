# -*- coding: utf-8 -*-
"""
================================================================================
 baslangic.py  --  "Ne modelliyorsun?" baslangic ekrani ve bos sablonlar
================================================================================
 NEDEN
   Eski "Yeni model" diyalogu bes satirlik bir listeydi ve "Bos model" secen
   ogrenci bos bir pencereyle bas basa kaliyordu: once hangi sekmede ne
   yapacagini bilmesi gerekiyordu. Kullanici once NE modelledigini soyler;
   program ona CALISAN, sade bir model kurar ve yalnizca o modele uyan
   sekmeleri gosterir (bkz. cekirdek/uygunluk.py).

 KARTLAR
   Her kart: tek satir aciklama + iki eylem
     "Bos basla"      -> bos_sablon(anahtar): o turun ASGARI ama TAM, gecerli
                         ve kosulabilir modeli (malzeme + parca + kor hazir).
                         Sablonlar ornekler/ altindaki ilgili ornekten
                         TURETILIR (yalnizca gereken kisim tutulur): ornek
                         dosya duzeltilirse sablon da kendiliginden duzelir.
     "Ornekten basla" -> ornegi KOPYA olarak acar (ana pencere proje_ac;
                         ornek dosyasi asla ustune yazilmaz).
   Kuresel duzenek yeni modelde sunulmaz (kullanici karari): zirhlama karti
   yalnizca ornekten baslar.

 Kartlarin altinda butun ornekler (aciklamalarinin ilk cumlesiyle) ve son
 kullanilan dosyalar listelenir. Klavye: Tab ile dugmeler arasinda gezinilir,
 Enter secer; listelerde ok tuslari + Enter. Esc acik modele doner.
================================================================================
"""

import copy
import glob
import math
import os

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import kaynak
from cekirdek import sema

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORNEKLER = os.path.join(KOK, "ornekler")

# (anahtar, baslik, aciklama, ornek dosyasi | None, bos sablon var mi, ilk sekme)
KARTLAR = [
    {"anahtar": "pin", "baslik": "Yakıt çubuğu (pin hücre)",
     "aciklama": "Tek yakıt çubuğu ve çevresindeki soğutucu; en hızlı başlangıç.",
     "ornek": "pwr_pinhucre.json", "bos": True, "sekme": "parcalar", "simge": "pin"},
    {"anahtar": "demet_kare", "baslik": "Yakıt demeti — kare",
     "aciklama": "Kare ızgarada yakıt çubukları ve kılavuz borular (PWR tipi).",
     "ornek": "pwr_17x17.json", "bos": True, "sekme": "demet", "simge": "kare"},
    {"anahtar": "demet_altigen", "baslik": "Yakıt demeti — altıgen",
     "aciklama": "Altıgen ızgarada çubuk demeti (VVER, hızlı reaktör).",
     "ornek": "sfr_altigen.json", "bos": True, "sekme": "demet", "simge": "altigen"},
    {"anahtar": "tam_kor", "baslik": "Tam kor (kare harita)",
     "aciklama": "Demetlerden oluşan kor haritası, çevresinde su yansıtıcı.",
     "ornek": None, "bos": True, "sekme": "kor", "simge": "kor"},
    {"anahtar": "plaka", "baslik": "MTR plaka elemanı",
     "aciklama": "Araştırma reaktörünün düz plakalı yakıt elemanı.",
     "ornek": "mtr_plaka.json", "bos": True, "sekme": "parcalar", "simge": "plaka"},
    {"anahtar": "tamburlu", "baslik": "Tamburlu kompakt kor",
     "aciklama": "Silindirik kor, yansıtıcı kuşak ve dönen kontrol tamburları.",
     "ornek": "tamburlu_kor.json", "bos": True, "sekme": "kor", "simge": "tambur"},
    {"anahtar": "zirh", "baslik": "Zırhlama (sabit kaynak)",
     "aciklama": "Kaynaktan çıkan nötronların zırh katmanlarında zayıflaması.",
     "ornek": "zirh_kure.json", "bos": False, "sekme": "kor", "simge": "zirh"},
]

# Ornek listesinde gorunen adlar; listede olmayan yeni bir ornek dosyasi
# kendi "ad" alaniyla yine listelenir.
ORNEK_BASLIKLARI = {
    "pwr_pinhucre.json": "PWR yakıt hücresi (pin)",
    "pwr_17x17.json": "PWR 17×17 yakıt demeti",
    "pwr_3b.json": "PWR 17×17 demet — 3B",
    "pwr_eksenel.json": "PWR demeti — eksenel katmanlı",
    "pwr_kontrol.json": "PWR demeti — kontrol çubuklu",
    "pwr_tukenme.json": "PWR pin hücre — tükenme",
    "sfr_altigen.json": "SFR altıgen demet",
    "mtr_plaka.json": "MTR plaka yakıt elemanı",
    "tamburlu_kor.json": "Tamburlu kompakt kor",
    "godiva_kriter.json": "Godiva kritik küresi",
    "zirh_kure.json": "Zırh küresi (sabit kaynak)",
}


def _kucuk_bas(metin):
    """Cumle icinde kullanmak icin ilk harfi kucultur; kisaltmaya dokunmaz
    ("MTR plaka elemani" aynen kalir, "Yakit cubugu" -> "yakit cubugu")."""
    if len(metin) > 1 and metin[1].islower():
        return ("ı" if metin[0] == "I" else "i" if metin[0] == "İ" else metin[0].lower()) + metin[1:]
    return metin


def kart(anahtar):
    """KARTLAR girdisi; yoksa KeyError."""
    for k in KARTLAR:
        if k["anahtar"] == anahtar:
            return k
    raise KeyError(anahtar)


def ilk_cumle(metin):
    """Aciklamanin ilk cumlesi (satir sonlari birlestirilir)."""
    duz = " ".join((metin or "").split())
    for i, ch in enumerate(duz):
        if ch == "." and (i + 1 == len(duz) or duz[i + 1] == " "):
            # "k-inf = 1.3570" gibi sayilari bolme: noktadan sonra bosluk sart.
            return duz[:i + 1]
    return duz


def ornek_listesi():
    """[(yol, baslik, ilk_cumle)] -- ornekler/ altindaki butun spec dosyalari."""
    sonuc = []
    for yol in sorted(glob.glob(os.path.join(ORNEKLER, "*.json"))):
        ad = os.path.basename(yol)
        try:
            spec = sema.yukle(yol)
        except Exception:
            continue
        baslik = ORNEK_BASLIKLARI.get(ad) or spec.get("ad") or ad
        sonuc.append((yol, baslik, ilk_cumle(spec.get("aciklama", ""))))
    # Bilinen ornekler tanidik sirayla (kolaydan zora), digerleri sonda.
    sira = list(ORNEK_BASLIKLARI)
    sonuc.sort(key=lambda x: (sira.index(os.path.basename(x[0]))
                              if os.path.basename(x[0]) in sira else len(sira), x[0]))
    return sonuc


# ============================================================================
# bos sablonlar
# ============================================================================

def _yukle(dosya):
    return sema.yukle(os.path.join(ORNEKLER, dosya))


def _kullanilmayanlari_at(spec):
    """
    Korun gercekten kullanmadigi cubuk/plaka/kafes/malzemeleri ve haritada
    gecmeyen anahtar harflerini atar. Sablon "sade" olsun: ogrenci ilk
    bakista yalnizca modelde ISE YARAYAN parcalari gorur.
    """
    kor = spec["kor"]
    kok = set()
    ana = sema.ana_dolgu(kor)
    if ana:
        kok.add(ana)
    if kor.get("tur") == "kare_kafes":
        kullanilan = {h for satir in kor.get("harita") or [] for h in satir}
        kor["anahtar"] = {h: a for h, a in (kor.get("anahtar") or {}).items()
                          if h in kullanilan}
        kok.update(kor["anahtar"].values())
    for _z0, _z1, b in (sema.eksenel_katmanlar(kor) or []):
        kok.update(sema.katman_adaylari(kor, b))

    gerekli, yigin = set(), list(kok)
    while yigin:
        ad = yigin.pop()
        if ad in gerekli:
            continue
        gerekli.add(ad)
        d = sema.demet_bul(spec, ad)
        if d is not None:
            kullanilan = {h for satir in d.get("harita") or [] for h in satir}
            d["anahtar"] = {h: a for h, a in (d.get("anahtar") or {}).items()
                            if h in kullanilan}
            yigin.extend(d["anahtar"].values())

    for liste in ("cubuklar", "plakalar", "demetler"):
        spec[liste] = [x for x in spec.get(liste, []) if x["ad"] in gerekli]
    malz = sema.kullanilan_malzemeler(spec) | {
        ad for ad in gerekli if sema.malzeme_bul(spec, ad) is not None}
    spec["malzemeler"] = [m for m in spec["malzemeler"] if m["ad"] in malz]
    return spec


def _sadelestir(spec, ad):
    """Ornekten sablon: ad/aciklama, tally, guc dagilimi, tukenme sifirlanir."""
    spec["ad"] = ad
    spec["aciklama"] = ""
    spec["tallyler"] = []
    spec["guc_dagilimi"] = copy.deepcopy(sema.VARSAYILAN_GUC)
    spec["tukenme"] = copy.deepcopy(sema.VARSAYILAN_TUKENME)
    spec["calistirma"] = copy.deepcopy(sema.VARSAYILAN_CALISTIRMA)
    # Yeni modelde entropi agi modelden turetilir (sema.yeni_spec ile ayni):
    # kullanici 2B'den 3B'ye gecince nz kendiliginden artar.
    ent = spec["ayarlar"].setdefault("entropi_mesh", {})
    ent["otomatik"] = True
    ent["boyut"] = kaynak.entropi_boyutu_otomatik(spec)   # dosyadaki deger de tutarli
    _kullanilmayanlari_at(spec)
    return spec


def bos_sablon(anahtar):
    """
    Kart anahtari icin ASGARI ama TAM ve gecerli spec (0 dogrulama hatasi,
    kurulur ve cizilir -- testler/test_kabuk.py sinar).
    """
    if anahtar == "pin":
        return _sadelestir(_yukle("pwr_pinhucre.json"), "Yeni yakıt çubuğu")
    if anahtar == "demet_kare":
        return _sadelestir(_yukle("pwr_17x17.json"), "Yeni kare yakıt demeti")
    if anahtar == "demet_altigen":
        return _sadelestir(_yukle("sfr_altigen.json"), "Yeni altıgen yakıt demeti")
    if anahtar == "plaka":
        return _sadelestir(_yukle("mtr_plaka.json"), "Yeni plaka elemanı")
    if anahtar == "tamburlu":
        return _sadelestir(_yukle("tamburlu_kor.json"), "Yeni tamburlu kor")
    if anahtar == "tam_kor":
        # ornekler/ altinda kare_kafes ornegi yok: 17x17 demetinden 3x3 kor
        # kurulur (su yansitici kusak, yanlarda vakum). Harf atamasi palet
        # editoruyle AYNI kuraldan gecer (izgara.adlardan_harita).
        from arayuz.izgara import adlardan_harita
        spec = _yukle("pwr_17x17.json")
        d = spec["demetler"][0]
        kor = spec["kor"]
        kor["tur"] = "kare_kafes"
        kor["adim"] = round(d["adim"] * d["boyut"][0], 6)
        kor["boyut"] = [3, 3]
        kor["harita"], kor["anahtar"] = adlardan_harita([[d["ad"]] * 3 for _ in range(3)])
        kor["yansitici"] = {"var": True, "kalinlik": 20.0, "malzeme": "su"}
        kor["sinir"] = {"yan": "vacuum", "alt": "reflective", "ust": "reflective"}
        sema.kor_alanlarini_ayikla(kor)
        return _sadelestir(spec, "Yeni tam kor")
    raise KeyError("boş şablonu olmayan kart: %s" % anahtar)


# ============================================================================
# kart simgeleri (QPainter; tema vurgu rengiyle)
# ============================================================================

def _kart_simgesi(tur, renk, boyut=46):
    pix = QtGui.QPixmap(boyut, boyut)
    pix.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pix)
    p.setRenderHint(QtGui.QPainter.Antialiasing)
    r = QtGui.QColor(renk)
    acik = QtGui.QColor(r)
    acik.setAlpha(70)
    kalem = QtGui.QPen(r, 1.6)
    p.setPen(kalem)
    m = boyut / 2.0

    def daire(x, y, yc, dolu=True):
        p.setBrush(r if dolu else acik)
        p.drawEllipse(QtCore.QPointF(x, y), yc, yc)

    if tur == "pin":
        p.setBrush(acik)
        p.drawRect(QtCore.QRectF(4, 4, boyut - 8, boyut - 8))
        daire(m, m, boyut * 0.28, False)
        daire(m, m, boyut * 0.19)
    elif tur == "kare":
        s = (boyut - 8) / 4.0
        for i in range(4):
            for j in range(4):
                daire(4 + s * (i + 0.5), 4 + s * (j + 0.5), s * 0.36,
                      not ((i, j) in ((1, 1), (2, 2))))
    elif tur == "altigen":
        yc = boyut * 0.47
        p.setBrush(acik)
        p.drawPolygon(QtGui.QPolygonF([
            QtCore.QPointF(m + yc * math.cos(math.radians(60 * k)),
                           m + yc * math.sin(math.radians(60 * k))) for k in range(6)]))
        daire(m, m, boyut * 0.09)
        for k in range(6):
            a = math.radians(60 * k + 30)
            daire(m + boyut * 0.24 * math.cos(a), m + boyut * 0.24 * math.sin(a), boyut * 0.09)
    elif tur == "kor":
        s = (boyut - 6) / 3.0
        for i in range(3):
            for j in range(3):
                p.setBrush(r if (i, j) != (1, 1) else acik)
                p.drawRect(QtCore.QRectF(3 + s * i + 1.5, 3 + s * j + 1.5, s - 3, s - 3))
    elif tur == "plaka":
        p.setBrush(acik)
        p.drawRect(QtCore.QRectF(5, 4, boyut - 10, boyut - 8))
        p.setBrush(r)
        for k in range(5):
            y = 9 + k * (boyut - 18) / 4.0
            p.drawRect(QtCore.QRectF(9, y - 1.5, boyut - 18, 3))
    elif tur == "tambur":
        daire(m, m, boyut * 0.47, False)
        daire(m, m, boyut * 0.24)
        for k in range(6):
            a = math.radians(60 * k)
            daire(m + boyut * 0.36 * math.cos(a), m + boyut * 0.36 * math.sin(a), boyut * 0.08)
    else:   # zirh
        for k, yc in enumerate((0.47, 0.34, 0.21)):
            daire(m, m, boyut * yc, k == 1)
        p.setBrush(r)
        p.drawEllipse(QtCore.QPointF(m, m), boyut * 0.06, boyut * 0.06)
    p.end()
    return pix


# ============================================================================
# bilesenler
# ============================================================================

class _Dugme(QtWidgets.QPushButton):
    """Enter/Return ile de basilan dugme (diyalog disinda Qt bunu yapmaz)."""

    def keyPressEvent(self, olay):
        if olay.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.click()
            return
        super().keyPressEvent(olay)


class _TikListe(QtWidgets.QTreeWidget):
    """
    Tek tik ya da Enter ile acilan liste. itemActivated kullanilmaz: bazi
    platformlarda cift tik hem tiklama hem etkinlestirme uretir ve ayni dosya
    iki kez acilirdi.
    """

    secildi = QtCore.Signal(object)

    def __init__(self, sutun=2, parent=None):
        super().__init__(parent)
        self.setObjectName("tikListe")
        self.setColumnCount(sutun)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(False)
        self.setUniformRowHeights(True)
        self.setMouseTracking(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setTextElideMode(QtCore.Qt.ElideRight)
        self.viewport().setCursor(QtCore.Qt.PointingHandCursor)

    def mouseReleaseEvent(self, olay):
        super().mouseReleaseEvent(olay)
        if olay.button() == QtCore.Qt.LeftButton:
            oge = self.itemAt(olay.position().toPoint())
            if oge is not None:
                self.secildi.emit(oge)

    def keyPressEvent(self, olay):
        if olay.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            if self.currentItem() is not None:
                self.secildi.emit(self.currentItem())
            return
        super().keyPressEvent(olay)

    def yuksekligi_sabitle(self):
        """Ic kaydirma olmasin: sayfa zaten kayar, tum satirlar gorunsun."""
        n = max(self.topLevelItemCount(), 1)
        satir = self.sizeHintForRow(0) if self.topLevelItemCount() else 26
        self.setFixedHeight(n * max(satir, 16) + 2 * self.frameWidth() + 4)


class _Kart(QtWidgets.QFrame):
    def __init__(self, bilgi, parent=None):
        super().__init__(parent)
        self.bilgi = bilgi
        self.setObjectName("kart")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.simge = QtWidgets.QLabel()
        self.simge.setFixedSize(46, 46)
        self.baslik = QtWidgets.QLabel(bilgi["baslik"])
        f = self.baslik.font()
        f.setPointSizeF(f.pointSizeF() + 1.5)
        f.setBold(True)
        self.baslik.setFont(f)
        self.baslik.setWordWrap(True)
        self.aciklama = QtWidgets.QLabel(bilgi["aciklama"])
        self.aciklama.setObjectName("kartAciklama")
        self.aciklama.setWordWrap(True)
        self.aciklama.setMinimumHeight(self.aciklama.fontMetrics().lineSpacing() * 2)
        self.aciklama.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        self.d_bos = _Dugme("Boş başla")
        self.d_bos.setObjectName("birincil")
        self.d_ornek = _Dugme("Örnekten başla")
        for d in (self.d_bos, self.d_ornek):
            d.setCursor(QtCore.Qt.PointingHandCursor)
        if bilgi["bos"]:
            self.d_bos.setToolTip("Çalışır durumda, sade bir %s modeli kurar "
                                  "(malzemeler, parçalar ve kor hazır)."
                                  % _kucuk_bas(bilgi["baslik"].split(" (")[0]))
        else:
            self.d_bos.setVisible(False)
        if bilgi["ornek"]:
            self.d_ornek.setToolTip("Hazır örneğin bir kopyasını açar: %s "
                                    "(örnek dosyası değişmez)." % bilgi["ornek"])
        else:
            self.d_ornek.setVisible(False)
        if not bilgi["bos"]:
            # Tek eylem kaldiysa o birincil olur.
            self.d_ornek.setObjectName("birincil")

        ust = QtWidgets.QHBoxLayout()
        ust.setSpacing(12)
        ust.addWidget(self.simge, 0, QtCore.Qt.AlignTop)
        metin = QtWidgets.QVBoxLayout()
        metin.setSpacing(3)
        metin.addWidget(self.baslik)
        metin.addWidget(self.aciklama)
        ust.addLayout(metin, 1)
        alt = QtWidgets.QHBoxLayout()
        alt.addWidget(self.d_bos)
        alt.addWidget(self.d_ornek)
        alt.addStretch(1)
        d = QtWidgets.QVBoxLayout(self)
        d.setContentsMargins(14, 12, 14, 12)
        d.setSpacing(10)
        d.addLayout(ust)
        d.addLayout(alt)

    def simgeyi_ciz(self, renk):
        self.simge.setPixmap(_kart_simgesi(self.bilgi["simge"], renk))


class BaslangicEkrani(QtWidgets.QWidget):
    """
    Baslangic ekrani. Ana pencere sinyalleri baglar; ekran kendisi model
    yuklemez (test edilebilir, modal degil).
    """

    bos_istendi = QtCore.Signal(str)        # kart anahtari
    ornek_istendi = QtCore.Signal(str)      # ornek dosya yolu (kopya acilir)
    dosya_istendi = QtCore.Signal(str)      # son kullanilan dosya yolu
    ac_istendi = QtCore.Signal()            # "Baska bir dosya ac..."
    geri_istendi = QtCore.Signal()          # acik modele don

    def __init__(self, parent=None):
        super().__init__(parent)
        self._kartlar = []
        self._sutun = 0

        self.baslik = QtWidgets.QLabel("Ne modellemek istiyorsunuz?")
        self.baslik.setObjectName("ekranBaslik")
        self.alt_baslik = QtWidgets.QLabel(
            "Bir model türü seçin. <b>Boş başla</b> çalışır durumda sade bir model "
            "kurar; <b>Örnekten başla</b> hazır bir örneğin kopyasını açar.")
        self.alt_baslik.setObjectName("soluk")
        self.alt_baslik.setWordWrap(True)
        self.d_geri = _Dugme("←  Açık modele dön")
        self.d_geri.setToolTip("Başlangıç ekranını kapatıp üzerinde çalıştığınız "
                               "modele döner (Esc).")
        self.d_geri.clicked.connect(self.geri_istendi)
        self.d_geri.setVisible(False)

        ust = QtWidgets.QHBoxLayout()
        ust.addWidget(self.baslik, 1)
        ust.addWidget(self.d_geri, 0, QtCore.Qt.AlignTop)

        self._izgara = QtWidgets.QGridLayout()
        self._izgara.setSpacing(12)
        for bilgi in KARTLAR:
            k = _Kart(bilgi)
            k.d_bos.clicked.connect(lambda _c=False, a=bilgi["anahtar"]: self.bos_istendi.emit(a))
            if bilgi["ornek"]:
                yol = os.path.join(ORNEKLER, bilgi["ornek"])
                k.d_ornek.clicked.connect(lambda _c=False, y=yol: self.ornek_istendi.emit(y))
            self._kartlar.append(k)

        # ---------------- ornekler + son kullanilanlar ----------------
        self.ornek_listesi = _TikListe(2)
        for yol, baslik, cumle in ornek_listesi():
            oge = QtWidgets.QTreeWidgetItem([baslik, cumle])
            oge.setData(0, QtCore.Qt.UserRole, yol)
            oge.setToolTip(0, "%s — kopya olarak açılır" % os.path.basename(yol))
            oge.setToolTip(1, cumle)
            f = oge.font(0)
            f.setBold(True)
            oge.setFont(0, f)
            self.ornek_listesi.addTopLevelItem(oge)
        self.ornek_listesi.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.ornek_listesi.header().setStretchLastSection(True)
        self.ornek_listesi.secildi.connect(
            lambda oge: self.ornek_istendi.emit(oge.data(0, QtCore.Qt.UserRole)))
        self.ornek_listesi.yuksekligi_sabitle()

        self.son_listesi = _TikListe(2)
        self.son_listesi.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.son_listesi.header().setStretchLastSection(True)
        self.son_listesi.secildi.connect(
            lambda oge: self.dosya_istendi.emit(oge.data(0, QtCore.Qt.UserRole)))
        self.son_bos = QtWidgets.QLabel("Henüz kaydedilmiş bir model yok.")
        self.son_bos.setObjectName("soluk")
        self.d_ac = _Dugme("Başka bir dosya aç…")
        self.d_ac.setToolTip("Bilgisayarınızdaki bir model dosyasını (.json) açar (Ctrl+O).")
        self.d_ac.clicked.connect(self.ac_istendi)

        # Ic duzenler araligi ACIKCA verir: verilmezse ust duzenin 24 px'lik
        # yatay araligini miras alip baslikla liste arasinda bosluk birakiyordu.
        sol = QtWidgets.QVBoxLayout()
        sol.setSpacing(6)
        e = QtWidgets.QLabel("Örnekler")
        e.setObjectName("bolumBaslik")
        sol.addWidget(e)
        sol.addWidget(self.ornek_listesi)
        sol.addStretch(1)
        sag = QtWidgets.QVBoxLayout()
        sag.setSpacing(6)
        e = QtWidgets.QLabel("Son kullanılanlar")
        e.setObjectName("bolumBaslik")
        sag.addWidget(e)
        sag.addWidget(self.son_listesi)
        sag.addWidget(self.son_bos)
        sag.addWidget(self.d_ac, 0, QtCore.Qt.AlignLeft)
        sag.addStretch(1)
        alt = QtWidgets.QHBoxLayout()
        alt.setSpacing(24)
        alt.addLayout(sol, 3)
        alt.addLayout(sag, 2)

        # ---------------- ortalanmis icerik + kaydirma ----------------
        icerik = QtWidgets.QWidget()
        icerik.setMaximumWidth(1240)
        d = QtWidgets.QVBoxLayout(icerik)
        d.setContentsMargins(28, 22, 28, 22)
        d.setSpacing(10)
        d.addLayout(ust)
        d.addWidget(self.alt_baslik)
        d.addSpacing(8)
        d.addLayout(self._izgara)
        d.addSpacing(18)
        d.addLayout(alt)
        d.addStretch(1)

        sarici = QtWidgets.QWidget()
        sd = QtWidgets.QHBoxLayout(sarici)
        sd.setContentsMargins(0, 0, 0, 0)
        sd.addStretch(1)
        sd.addWidget(icerik, 100)
        sd.addStretch(1)
        self._icerik = icerik

        self.kaydirma = QtWidgets.QScrollArea()
        self.kaydirma.setWidgetResizable(True)
        self.kaydirma.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.kaydirma.setWidget(sarici)
        ana = QtWidgets.QVBoxLayout(self)
        ana.setContentsMargins(0, 0, 0, 0)
        ana.addWidget(self.kaydirma)

        self._yerlestir(3)
        self._renkleri_uygula()
        self.son_dosyalari_ayarla([])
        self.setFocusProxy(self._kartlar[0].d_bos)

    # ------------------------------------------------------------------
    def kart_dugmesi(self, anahtar, tur="bos"):
        """Kartin dugmesi (tur: "bos" | "ornek") -- testler ve klavye odagi icin."""
        for k in self._kartlar:
            if k.bilgi["anahtar"] == anahtar:
                return k.d_bos if tur == "bos" else k.d_ornek
        return None

    def geri_gorunur(self, acik):
        self.d_geri.setVisible(bool(acik))

    def son_dosyalari_ayarla(self, yollar):
        self.son_listesi.clear()
        for yol in yollar:
            oge = QtWidgets.QTreeWidgetItem([os.path.basename(yol), os.path.dirname(yol)])
            oge.setData(0, QtCore.Qt.UserRole, yol)
            oge.setToolTip(0, yol)
            oge.setToolTip(1, yol)
            f = oge.font(0)
            f.setBold(True)
            oge.setFont(0, f)
            self.son_listesi.addTopLevelItem(oge)
        self.son_listesi.setVisible(bool(yollar))
        self.son_bos.setVisible(not yollar)
        self.son_listesi.yuksekligi_sabitle()
        self._renkleri_uygula()

    # ------------------------------------------------------------------
    def _yerlestir(self, sutun):
        sutun = max(1, min(4, sutun))
        if sutun == self._sutun:
            return
        self._sutun = sutun
        for k in self._kartlar:
            self._izgara.removeWidget(k)
        for i, k in enumerate(self._kartlar):
            self._izgara.addWidget(k, i // sutun, i % sutun)
        for c in range(4):
            self._izgara.setColumnStretch(c, 1 if c < sutun else 0)
        # Tab sirasi okuma sirasiyla ayni olsun (satir satir, soldan saga).
        onceki = None
        for k in self._kartlar:
            for w in (k.d_bos, k.d_ornek):
                if onceki is not None:
                    QtWidgets.QWidget.setTabOrder(onceki, w)
                onceki = w

    def resizeEvent(self, olay):
        genislik = min(self.width(), 1240) - 56
        self._yerlestir(genislik // 300)
        super().resizeEvent(olay)

    def keyPressEvent(self, olay):
        if olay.key() == QtCore.Qt.Key_Escape and not self.d_geri.isHidden():
            self.geri_istendi.emit()
            return
        super().keyPressEvent(olay)

    def _renkleri_uygula(self):
        try:
            from arayuz import tema
            vurgu, soluk = tema.renk("vurgu"), tema.renk("metin_soluk")
        except Exception:
            vurgu, soluk = "#0f766e", "#6b7785"
        for k in self._kartlar:
            k.simgeyi_ciz(vurgu)
        for liste in (self.ornek_listesi, self.son_listesi):
            for i in range(liste.topLevelItemCount()):
                liste.topLevelItem(i).setForeground(1, QtGui.QColor(soluk))

    def changeEvent(self, olay):
        if olay.type() == QtCore.QEvent.PaletteChange:
            self._renkleri_uygula()
        super().changeEvent(olay)
