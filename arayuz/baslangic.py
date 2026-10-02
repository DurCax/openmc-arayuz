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

 GALERI (Dalga 2)
   Kartlarin altinda once SON KULLANILANLAR seridi, sonra filtrelenebilir
   ornek galerisi gelir: kategori ve seviye segment secicileri + arama kutusu.
   Basliklar, kategori ve seviye cekirdek/ornek_bilgi.py'den (ornek JSON'unun
   meta alanlari) okunur; burada ad listesi TUTULMAZ -- Ajan 9 yeni ornek
   ekleyince galeri kendiliginden buyur. Kucuk resim modelin TURUNDEN cizilir
   (Monte Carlo ya da openmc.plot YOK). Esc acik modele doner.
================================================================================
"""

import os
import time

from PySide6 import QtCore, QtWidgets

from arayuz import bilesenler as b
from arayuz.tasarim import tokenlar
from arayuz.tasarim.ikon import ikon_bagla
from arayuz.tasarim.maket_cizim import KucukResim

from cekirdek import ornek_bilgi, yollar
from cekirdek.ceviri import N_, _, _n
from cekirdek.gunluk import kaydedici
from arayuz.baslangic_sablon import (  # noqa: F401 -- tasindi (T2), adlar burada da
    SABLON_MALZEMELERI, _PWR, _altigen_tam_kor, _bos_sablon_ham, _kullanilmayanlari_at,
    _normal_hassasiyet, _parametrik_malzemeler, _sadelestir, _yukle, bos_sablon)

_log = kaydedici(__name__)
KOK = yollar.veri_koku()
ORNEKLER = yollar.ornekler_dizini()

# (anahtar, baslik, aciklama, ornek dosyasi | None, bos sablon var mi, ilk sekme)
# baslik/aciklama yalnizca ISARETLI (N_): ice aktarma aninda dil belli degil;
# gosterim yerleri (_TurKarti, ana pencere) _() ile cevirir.
KARTLAR = [
    {"anahtar": "pin", "baslik": N_("Yakıt çubuğu (pin hücre)"),
     "aciklama": N_("Tek yakıt çubuğu ve çevresindeki soğutucu; en hızlı başlangıç."),
     "ornek": "pwr_pinhucre.json", "bos": True, "sekme": "parcalar", "ikon": "circle-dot"},
    {"anahtar": "demet_kare", "baslik": N_("Yakıt demeti — kare"),
     "aciklama": N_("Kare ızgarada yakıt çubukları ve kılavuz borular (PWR tipi)."),
     "ornek": "pwr_17x17.json", "bos": True, "sekme": "demet", "ikon": "grid-3x3"},
    {"anahtar": "demet_altigen", "baslik": N_("Yakıt demeti — altıgen"),
     "aciklama": N_("Altıgen ızgarada çubuk demeti (VVER, hızlı reaktör)."),
     "ornek": "sfr_altigen.json", "bos": True, "sekme": "demet", "ikon": "hexagon"},
    {"anahtar": "tam_kor", "baslik": N_("Tam kor (kare harita)"),
     "aciklama": N_("Demetlerden oluşan kor haritası, çevresinde su yansıtıcı."),
     "ornek": None, "bos": True, "sekme": "kor", "ikon": "layers"},
    {"anahtar": "tam_kor_altigen", "baslik": N_("Tam kor — altıgen"),
     "aciklama": N_("Kılıflı altıgen demetlerden kor haritası (SFR / VVER tipi)."),
     "ornek": None, "bos": True, "sekme": "kor", "ikon": "hexagon"},
    {"anahtar": "plaka", "baslik": N_("MTR plaka elemanı"),
     "aciklama": N_("Araştırma reaktörünün düz plakalı yakıt elemanı."),
     "ornek": "mtr_plaka.json", "bos": True, "sekme": "parcalar", "ikon": "list"},
    {"anahtar": "tamburlu", "baslik": N_("Tamburlu kompakt kor"),
     "aciklama": N_("Silindirik kor, yansıtıcı kuşak ve dönen kontrol tamburları."),
     "ornek": "tamburlu_kor.json", "bos": True, "sekme": "kor", "ikon": "refresh-cw"},
    {"anahtar": "zirh", "baslik": N_("Zırhlama (sabit kaynak)"),
     "aciklama": N_("Kaynaktan çıkan nötronların zırh katmanlarında zayıflaması."),
     "ornek": "zirh_kure.json", "bos": False, "sekme": "kor", "ikon": "shield"},
]

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


# ============================================================================
# galeri yardimcilari
# ============================================================================

A = tokenlar.ARALIK
# Ornegin kor/demet turunden kucuk resim motifi (maket_cizim.KucukResim).
_MOTIFLER = {"kuresel": "kure", "tek_cubuk": "pin", "tek_plaka": "plaka",
             "kare_kafes": "kor", "altigen_kafes": "altigen", "tamburlu": "kor"}
_TUM = "hepsi"
_SUTUN_GENISLIGI = 260          # kart izgarasinda sutun basina en az genislik (px)
_EN_COK_SUTUN = 4
_SON_DOSYA_SAYISI = 3
_ARAMA_EN_AZ = 140             # galeri arama kutusu genislik araligi (px)
_ARAMA_EN_COK = 220


def ornek_motifi(bilgi):
    """OrnekBilgisi -> KucukResim motifi (tur bilinmiyorsa 'pin')."""
    if bilgi.kategori == "zirh":
        return "zirh"
    if bilgi.kor_turu == "tek_demet":
        return "altigen" if bilgi.demet_turu == "altigen" else "kare"
    return _MOTIFLER.get(bilgi.kor_turu, "pin")


def _kisa_dizin(yol):
    """Dizin yolu, ev dizini "~" ile kisaltilmis."""
    dizin = os.path.dirname(yol)
    ev = os.path.expanduser("~")
    return "~" + dizin[len(ev):] if dizin == ev or dizin.startswith(ev + os.sep) else dizin


def _dosya_zamani(yol):
    """Dosyanin son degisim zamani, okunur metin; okunamazsa bos."""
    try:
        return zaman_metni(os.path.getmtime(yol))
    except OSError:
        _log.warning("dosya zamani okunamadi: %s", yol, exc_info=True)
        return ""


def zaman_metni(saniye, simdi=None):
    """Dosya zaman damgasindan okunur metin ("2 saat önce")."""
    fark = max(0.0, (time.time() if simdi is None else simdi) - saniye)
    dakika = fark / 60.0
    if dakika < 1:
        return _("az önce")
    if dakika < 60:
        n = int(dakika)
        return _n("{n} dakika önce", "{n} dakika önce", n).format(n=n)
    if dakika < 60 * 24:
        n = int(dakika // 60)
        return _n("{n} saat önce", "{n} saat önce", n).format(n=n)
    gun = int(dakika // (60 * 24))
    return _("dün") if gun == 1 else _n("{n} gün önce", "{n} gün önce", gun).format(n=gun)


def ornek_eslesiyor(bilgi, metin="", kategori=_TUM, seviye=_TUM):
    """Galeri suzgeci: arama metni basligi/aciklamayi (Turkce ve Ingilizce alanlar,
    iki dilde arama), secimler meta alanlarini tutar."""
    if kategori != _TUM and bilgi.kategori != kategori:
        return False
    if seviye != _TUM and bilgi.seviye != seviye:
        return False
    ara = (metin or "").strip().lower()
    if not ara:
        return True
    havuz = " ".join(x for x in (bilgi.baslik, bilgi.aciklama, bilgi.baslik_en,
                                 bilgi.aciklama_en, bilgi.ad, bilgi.dosya) if x)
    return ara in havuz.lower()


class _TiklanirKart(b.Kart):
    """Tumu tiklanabilir kart (galeri ogesi); Enter/Space de secer."""

    secildi = QtCore.Signal()

    def __init__(self, parent=None, dolgu="m"):
        super().__init__(parent=parent, dolgu=dolgu)
        self.setProperty("tiklanir", True)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def mouseReleaseEvent(self, olay):                   # noqa: N802 (Qt adi)
        if olay.button() == QtCore.Qt.LeftButton and self.rect().contains(
                olay.position().toPoint()):
            self.secildi.emit()
        super().mouseReleaseEvent(olay)

    def keyPressEvent(self, olay):                       # noqa: N802 (Qt adi)
        if olay.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter, QtCore.Qt.Key_Space):
            self.secildi.emit()
            return
        super().keyPressEvent(olay)


class _TurKarti(b.Kart):
    """Model turu karti: ikon, baslik, tek cumle aciklama, iki eylem."""

    def __init__(self, bilgi, parent=None):
        super().__init__(parent=parent, dolgu="l")
        self.bilgi = bilgi
        self.setProperty("tiklanir", True)
        ust = QtWidgets.QHBoxLayout()
        ust.setSpacing(A["m"])
        simge = QtWidgets.QToolButton()
        simge.setFocusPolicy(QtCore.Qt.NoFocus)
        simge.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        simge.setProperty("tur", "ikon")
        ikon_bagla(simge, bilgi["ikon"], "vurgu", tokenlar.BOYUT["ikon_buyuk"])
        ust.addWidget(simge, 0, QtCore.Qt.AlignTop)
        metin = QtWidgets.QVBoxLayout()
        metin.setSpacing(2)
        # anahtar once degiskene: _() icinde dizgi sabiti sahte msgid uretir
        baslik, aciklama = bilgi["baslik"], bilgi["aciklama"]
        self.baslik = QtWidgets.QLabel(_(baslik))
        self.baslik.setObjectName("altBaslik")
        self.baslik.setWordWrap(True)
        metin.addWidget(self.baslik)
        self.aciklama = QtWidgets.QLabel(_(aciklama))
        self.aciklama.setObjectName("kucuk")
        self.aciklama.setWordWrap(True)
        metin.addWidget(self.aciklama)
        ust.addLayout(metin, 1)
        self.govde.addLayout(ust)
        self.govde.addStretch(1)
        self._eylemleri_kur()
        self.setAccessibleName(_(baslik))

    def _eylemleri_kur(self):
        bilgi = self.bilgi
        baslik = bilgi["baslik"]
        self.d_bos = b.ikincil_dugme(_("Boş başla"))
        self.d_ornek = b.duz_dugme(_("Örnekten"))
        # Diyalog disinda QPushButton Enter/Return'e tepki vermez; autoDefault
        # ile klavyeyle kart secilebilir (odak Tab ile dugmeler arasinda gezer).
        for d in (self.d_bos, self.d_ornek):
            d.setAutoDefault(True)
        if bilgi["bos"]:
            self.d_bos.setToolTip(
                _("Çalışır durumda, sade bir {ad} modeli kurar (malzemeler, "
                  "parçalar ve kor hazır).").format(
                      ad=_kucuk_bas(_(baslik).split(" (")[0])))
        else:
            self.d_bos.setVisible(False)
        if bilgi["ornek"]:
            self.d_ornek.setToolTip(
                _("Hazır örneğin bir kopyasını açar: {dosya} "
                  "(örnek dosyası değişmez).").format(dosya=bilgi["ornek"]))
        else:
            self.d_ornek.setVisible(False)
        eylem = QtWidgets.QHBoxLayout()
        eylem.setSpacing(A["s"])
        eylem.addWidget(self.d_bos)
        eylem.addWidget(self.d_ornek)
        eylem.addStretch(1)
        self.govde.addLayout(eylem)


class _OrnekKarti(_TiklanirKart):
    """Galeri ogesi: kucuk resim, baslik, kategori rozeti, seviye, aciklama."""

    def __init__(self, bilgi, parent=None):
        super().__init__(parent=parent, dolgu="m")
        self.bilgi = bilgi
        self.ekle(KucukResim(ornek_motifi(bilgi)))
        ust = QtWidgets.QHBoxLayout()
        ust.setSpacing(A["s"])
        baslik_metni = ornek_bilgi.yerel_baslik(bilgi)
        baslik = QtWidgets.QLabel(baslik_metni)
        baslik.setObjectName("govdeVurgulu")
        baslik.setWordWrap(True)
        ust.addWidget(baslik, 1)
        if bilgi.kategori:
            ust.addWidget(b.Rozet(_(ornek_bilgi.KATEGORI_ADLARI[bilgi.kategori]), "notr"))
        self.govde.addLayout(ust)
        alt = ilk_cumle(ornek_bilgi.yerel_aciklama(bilgi))
        if bilgi.seviye:
            alt = "%s · %s" % (_(ornek_bilgi.SEVIYE_ADLARI[bilgi.seviye]), alt) if alt \
                else _(ornek_bilgi.SEVIYE_ADLARI[bilgi.seviye])
        a = QtWidgets.QLabel(alt)
        a.setObjectName("kucuk")
        a.setWordWrap(True)
        self.ekle(a)
        self.setToolTip(_("{dosya} — kopya olarak açılır").format(dosya=bilgi.dosya))
        self.setAccessibleName(baslik_metni)


# ============================================================================
# baslangic ekrani
# ============================================================================

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

    def __init__(self, bilgiler=None, parent=None):
        super().__init__(parent)
        self._kartlar = []
        self._ornekler = []
        self._sutun = 0
        self.bilgiler = tuple(ornek_bilgi.ornek_listesi() if bilgiler is None else bilgiler)
        icerik = QtWidgets.QWidget()
        icerik.setObjectName("sayfa")
        icerik.setMaximumWidth(1320)
        d = QtWidgets.QVBoxLayout(icerik)
        d.setContentsMargins(A["xxl"], A["xl"], A["xxl"], A["xl"])
        d.setSpacing(A["m"])
        self._baslik_kur(d)
        self._turleri_kur(d)
        self._son_kullanilanlari_kur(d)
        self._galeriyi_kur(d)
        d.addStretch(1)
        self._kaydirmaya_koy(icerik)
        self._yerlestir(4)
        self.son_dosyalari_ayarla([])
        self.setFocusProxy(self._kartlar[0].d_bos)

    # ------------------------------------------------------------------ kurucular
    def _baslik_kur(self, d):
        ust = QtWidgets.QHBoxLayout()
        self.baslik = QtWidgets.QLabel(_("Ne modellemek istiyorsunuz?"))
        self.baslik.setObjectName("baslikBuyuk")
        ust.addWidget(self.baslik, 1)
        self.d_geri = b.duz_dugme(_("Açık modele dön"), "chevron-left")
        self.d_geri.setToolTip(_("Başlangıç ekranını kapatıp üzerinde çalıştığınız "
                                 "modele döner (Esc)."))
        self.d_geri.clicked.connect(self.geri_istendi)
        self.d_geri.setVisible(False)
        ust.addWidget(self.d_geri, 0, QtCore.Qt.AlignTop)
        d.addLayout(ust)
        alt = QtWidgets.QLabel(_("Bir model türüyle boş başlayın ya da hazır bir "
                                 "örneğin kopyasını açın."))
        alt.setObjectName("ikincil")
        alt.setWordWrap(True)
        d.addWidget(alt)

    def _turleri_kur(self, d):
        self._izgara = QtWidgets.QGridLayout()
        self._izgara.setSpacing(A["m"])
        for bilgi in KARTLAR:
            k = _TurKarti(bilgi)
            k.d_bos.clicked.connect(
                lambda _c=False, a=bilgi["anahtar"]: self.bos_istendi.emit(a))
            if bilgi["ornek"]:
                yol = os.path.join(ORNEKLER, bilgi["ornek"])
                k.d_ornek.clicked.connect(lambda _c=False, y=yol: self.ornek_istendi.emit(y))
            self._kartlar.append(k)
        self.dosya_karti = self._dosya_karti()
        self._kartlar.append(self.dosya_karti)
        d.addLayout(self._izgara)

    def _dosya_karti(self):
        k = _TurKarti({"anahtar": "dosya", "baslik": N_("Dosyadan aç"),
                       "aciklama": N_("Kaydedilmiş bir model (.json) ya da OpenMC XML klasörü."),
                       "ornek": None, "bos": True, "sekme": None, "ikon": "folder-open"})
        k.d_bos.setText(_("Aç…"))
        k.d_bos.setToolTip(_("Bilgisayarınızdaki bir model dosyasını (.json) açar (Ctrl+O)."))
        k.d_bos.clicked.connect(self.ac_istendi)
        return k

    def _son_kullanilanlari_kur(self, d):
        self._son_serit = QtWidgets.QHBoxLayout()
        self._son_serit.setSpacing(A["xl"])
        self._son_basligi = b.BolumBasligi(_("Son kullanılanlar"))
        self._son_serit.addWidget(self._son_basligi, 0, QtCore.Qt.AlignVCenter)
        self.son_bos = QtWidgets.QLabel(_("Henüz kaydedilmiş bir model yok."))
        self.son_bos.setObjectName("kucuk")
        self._son_serit.addWidget(self.son_bos, 0, QtCore.Qt.AlignVCenter)
        self._son_serit.addStretch(1)
        d.addLayout(self._son_serit)

    def _galeriyi_kur(self, d):
        filtre = QtWidgets.QHBoxLayout()
        filtre.setSpacing(A["s"])
        self._galeri_basligi = b.BolumBasligi(_("Örnekler"), "")
        filtre.addWidget(self._galeri_basligi, 1)
        self.arama = QtWidgets.QLineEdit()
        self.arama.setPlaceholderText(_("Örneklerde ara…"))
        self.arama.setClearButtonEnabled(True)
        # Arama kutusu daralabilir: suzgec satiri 1280 px'te tasmasin.
        self.arama.setMinimumWidth(_ARAMA_EN_AZ)
        self.arama.setMaximumWidth(_ARAMA_EN_COK)
        self.arama.textChanged.connect(lambda *_a: self.filtrele())
        filtre.addWidget(self.arama, 1, QtCore.Qt.AlignBottom)
        # Seviye acilir kutu: ikinci bir segment satiri 1280 px'e sigmiyordu.
        self.seviye = QtWidgets.QComboBox()
        self.seviye.setAccessibleName(_("Seviye"))
        self.seviye.setToolTip(_("Örnekleri zorluk seviyesine göre süzer."))
        self.seviye.addItem(_("Her seviye"), _TUM)
        for sev in ornek_bilgi.SEVIYELER:
            if any(o.seviye == sev for o in self.bilgiler):
                self.seviye.addItem(_(ornek_bilgi.SEVIYE_ADLARI[sev]), sev)
        self.seviye.currentIndexChanged.connect(lambda *_a: self.filtrele())
        filtre.addWidget(self.seviye, 0, QtCore.Qt.AlignBottom)
        self.kategori = b.SegmentSecici(
            [(_TUM, _("Tümü"))] + [(k, _(ornek_bilgi.KATEGORI_ADLARI[k]))
                                   for k in ornek_bilgi.KATEGORILER
                                   if any(o.kategori == k for o in self.bilgiler)], _TUM)
        self.kategori.secildi.connect(lambda *_a: self.filtrele())
        filtre.addWidget(self.kategori, 0, QtCore.Qt.AlignBottom)
        d.addLayout(filtre)
        self._galeri = QtWidgets.QGridLayout()
        self._galeri.setSpacing(A["m"])
        for bilgi in self.bilgiler:
            k = _OrnekKarti(bilgi)
            k.secildi.connect(lambda y=bilgi.yol: self.ornek_istendi.emit(y))
            self._ornekler.append(k)
        d.addLayout(self._galeri)
        self.galeri_bos = b.BosDurum("search", _("Eşleşen örnek yok"),
                                     _("Aramayı ya da kategori süzgecini değiştirin."))
        self.galeri_bos.setVisible(False)
        d.addWidget(self.galeri_bos)
        self.filtrele()

    def _kaydirmaya_koy(self, icerik):
        sarici = QtWidgets.QWidget()
        sarici.setObjectName("sayfa")
        sd = QtWidgets.QHBoxLayout(sarici)
        sd.setContentsMargins(0, 0, 0, 0)
        sd.addStretch(1)
        sd.addWidget(icerik, 100)
        sd.addStretch(1)
        self._icerik = icerik
        self.kaydirma = QtWidgets.QScrollArea()
        self.kaydirma.setObjectName("sayfa")
        self.kaydirma.setWidgetResizable(True)
        self.kaydirma.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.kaydirma.setWidget(sarici)
        ana = QtWidgets.QVBoxLayout(self)
        ana.setContentsMargins(0, 0, 0, 0)
        ana.addWidget(self.kaydirma)

    # ------------------------------------------------------------------ herkese acik
    def kart_dugmesi(self, anahtar, tur="bos"):
        """Kartin dugmesi (tur: "bos" | "ornek") -- testler ve klavye odagi icin."""
        for k in self._kartlar:
            if k.bilgi["anahtar"] == anahtar:
                return k.d_bos if tur == "bos" else k.d_ornek
        return None

    def ornek_kartlari(self):
        """Galerideki butun ornek kartlari (gizliler dahil)."""
        return tuple(self._ornekler)

    def gorunur_ornekler(self):
        """Suzgeci gecen orneklerin dosya adlari."""
        return tuple(k.bilgi.dosya for k in self._ornekler if not k.isHidden())

    def filtrele(self):
        """Arama + kategori + seviye secimini galeriye uygular."""
        metin = self.arama.text()
        kategori = self.kategori.secili() or _TUM
        seviye = self.seviye.currentData() or _TUM
        gorunur = []
        for k in self._ornekler:
            uygun = ornek_eslesiyor(k.bilgi, metin, kategori, seviye)
            k.setVisible(uygun)
            if uygun:
                gorunur.append(k)
        self._galeriyi_diz(gorunur)
        self.galeri_bos.setVisible(not gorunur)
        self._galeri_basligi.etiket.setText(_("Örnekler"))
        self._galeri_sayisi(len(gorunur))

    def _galeri_sayisi(self, n):
        toplam = len(self._ornekler)
        metin = (_n("{n} örnek · kategoriye göre süzün", "{n} örnek · kategoriye göre süzün",
                    toplam).format(n=toplam) if n == toplam
                 else _n("{n} / {toplam} örnek", "{n} / {toplam} örnek",
                         toplam).format(n=n, toplam=toplam))
        self._galeri_basligi.setToolTip(metin)
        self._galeri_basligi.etiket.setToolTip(metin)
        self._galeri_basligi.setAccessibleDescription(metin)

    def geri_gorunur(self, acik):
        self.d_geri.setVisible(bool(acik))

    def son_dosyalari_ayarla(self, yollar):
        """Son kullanilanlar seridi (en cok 3 dosya: ad, dizin, zaman)."""
        # Eski dosya ogeleri silinir; baslik, "henuz yok" etiketi ve sondaki
        # esneme yerinde kalir (eskiden etiket de seritten dusup sol kenarda
        # sahipsiz ciziliyordu).
        for i in reversed(range(self._son_serit.count())):
            w = self._son_serit.itemAt(i).widget()
            if w is not None and w not in (self._son_basligi, self.son_bos):
                self._son_serit.takeAt(i)
                w.deleteLater()
        for yol in list(yollar)[:_SON_DOSYA_SAYISI]:
            self._son_serit.insertWidget(self._son_serit.count() - 1,
                                         self._son_ogesi(yol), 0, QtCore.Qt.AlignVCenter)
        self.son_bos.setVisible(not yollar)

    def _son_ogesi(self, yol):
        w = QtWidgets.QWidget()
        d = QtWidgets.QHBoxLayout(w)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(A["s"])
        simge = QtWidgets.QToolButton()
        simge.setFocusPolicy(QtCore.Qt.NoFocus)
        simge.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        simge.setProperty("tur", "ikon")
        ikon_bagla(simge, "file-text", "metin_soluk")
        d.addWidget(simge)
        metin = QtWidgets.QVBoxLayout()
        metin.setSpacing(0)
        bag = b.baglanti_dugmesi(os.path.basename(yol))
        bag.setToolTip(yol)
        bag.clicked.connect(lambda _c=False, y=yol: self.dosya_istendi.emit(y))
        metin.addWidget(bag, 0, QtCore.Qt.AlignLeft)
        alt = QtWidgets.QLabel("%s · %s" % (_kisa_dizin(yol), _dosya_zamani(yol)))
        alt.setObjectName("kucuk")
        metin.addWidget(alt)
        d.addLayout(metin)
        return w

    # ------------------------------------------------------------------ yerlesim
    def _yerlestir(self, sutun):
        sutun = max(1, min(_EN_COK_SUTUN, sutun))
        if sutun == self._sutun:
            return
        self._sutun = sutun
        for i, k in enumerate(self._kartlar):
            self._izgara.addWidget(k, i // sutun, i % sutun)
        for c in range(_EN_COK_SUTUN):
            self._izgara.setColumnStretch(c, 1 if c < sutun else 0)
        onceki = None
        for k in self._kartlar:
            for w in (k.d_bos, k.d_ornek):
                if onceki is not None:
                    QtWidgets.QWidget.setTabOrder(onceki, w)
                onceki = w
        self._galeriyi_diz([k for k in self._ornekler if not k.isHidden()])

    def _galeriyi_diz(self, kartlar):
        sutun = max(1, self._sutun or _EN_COK_SUTUN)
        for i, k in enumerate(kartlar):
            self._galeri.addWidget(k, i // sutun, i % sutun)
        for c in range(_EN_COK_SUTUN):
            self._galeri.setColumnStretch(c, 1 if c < sutun else 0)

    def sutun_sayisi(self, genislik):
        """Pencere genisliginde tasmadan sigan kart sutunu (en az 1)."""
        kaydirma = self.style().pixelMetric(QtWidgets.QStyle.PM_ScrollBarExtent)
        icerik = min(genislik - kaydirma, self._icerik.maximumWidth()) - 2 * A["xxl"]
        kart = max([_SUTUN_GENISLIGI] + [k.minimumSizeHint().width()
                                         for k in self._kartlar + self._ornekler])
        return max(1, (icerik + A["m"]) // (kart + A["m"]))

    def resizeEvent(self, olay):                          # noqa: N802 (Qt adi)
        self._yerlestir(self.sutun_sayisi(self.width()))
        super().resizeEvent(olay)

    def keyPressEvent(self, olay):                        # noqa: N802 (Qt adi)
        if olay.key() == QtCore.Qt.Key_Escape and not self.d_geri.isHidden():
            self.geri_istendi.emit()
            return
        super().keyPressEvent(olay)
