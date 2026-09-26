# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_cubuk.py  --  Parcalar sekmesi: cubuklar ve plaka elemanlari
================================================================================
 Solda parca listesi, sagda secili parcanin editoru.
   Silindirik cubuk : es merkezli radyal bolgeler (son bolge "dis bolge")
   Plaka eleman     : MTR tipi duz plaka istifi

 YALNIZCA MODELDE ANLAMLI OLAN SUNULUR (cekirdek/uygunluk.parca_turleri)
   "+ Cubuk"  cubuk kullanan kor turlerinde; bir SABLON menusu acar:
              PWR yakit cubugu / Kilavuz boru / Kontrol cubugu (sonuncusu
              yalnizca 3B ve kafesli modelde).
   "+ Plaka"  yalnizca plaka modelinde.
   Hic malzeme yokken ekleme dugmeleri kapalidir.
   Emici bolge listesinde dis bolge, izleyici listesinde yakit/emici,
   plaka listelerinde role uymayan malzeme yoktur (dosyadan gelen mevcut
   deger yine gosterilir -- veri sessizce degismez).

 SABLONLAR MALZEMEYI ROLUNDEN SECER (uygunluk.rol_malzemeleri)
   yakit -> yakit, zarf -> yapisal (cubukta Zr, plakada Al tercihli),
   dis -> sogutucu, yakit-zarf araligi -> gaz ya da Bos (madde yok).
   Rolu karsilayan malzeme yoksa bolgenin malzemesi None kalir ve arayuzde
   "Malzeme secin" olarak ACIKCA isaretlenir (kurucu None'i bosluk olarak
   kurar; sessizce bosluga donusmesin diye kirmizi gosterilir).

 BOLGE TABLOSU
   Yaricaplar artan sirada ZORUNLU: her kutunun alt/ust siniri komsularindan
   gelir. "Ice/Disa tasi" yalnizca MALZEMEYI tasir, yaricaplar yerinde kalir
   (eskiden yaricaplar da yer degistirip sira bozuluyordu).

 AD DEGISIMI butun referanslari gunceller (parca_adini_degistir): kafes
   anahtarlari, kor cubuk/plaka/demet/dolgu, kor haritasi anahtari, eksenel
   katman dolgusu ve anahtari, guc dagilimi cubugu. sekme_demet de kullanir.
================================================================================
"""

import copy
import json
import re

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import sema, uygunluk
from arayuz.ortak import BosDurum, SekmeTabani, baslik, ipucu, renk_simgesi, sayi, tamsayi

BOS_ETIKETI = "Boş (madde yok)"
SECILMEDI_ETIKETI = "— Malzeme seçin —"
MALZEME_YOK_IPUCU = "Önce Malzemeler sekmesinden malzeme ekleyin."

ROL_ADI = {"yakit": "yakıt", "sogutucu": "soğutucu", "moderator": "moderatör",
           "emici": "emici", "yapisal": "yapısal", "gaz": "gaz"}

# (anahtar, menu metni, varsayilan ad) -- "+ Cubuk" menusu bu sirayla.
CUBUK_SABLONLARI = (
    ("yakit", "PWR yakıt çubuğu", "yakit_cubugu"),
    ("kilavuz", "Kılavuz boru", "kilavuz_boru"),
    ("kontrol", "Kontrol çubuğu", "kontrol_cubugu"),
)


# ============================================================================
# saf yardimcilar (Qt gerektirmez; testler/test_parca_demet.py sinar)
# ============================================================================

def _renk(ad, vars_):
    try:
        from arayuz import tema
        return tema.renk(ad)
    except Exception:
        return vars_


_ROL_ONBELLEK = {}


def roller(spec):
    """
    uygunluk.malzeme_rolleri'nin SONUCU, malzemeler bolumune gore onbellekli.
    Roller yalnizca malzeme tanimlarina baglidir; editor her yuklemede onlarca
    kez soruyordu (olculen: yeniden yukleme 4 ms -> 47 ms, cogu atom kutlesi
    aramasi). Kural uygunluk'ta kalir; burada yalnizca tekrar hesaplanmaz.
    """
    try:
        anahtar = json.dumps(spec.get("malzemeler", []), sort_keys=True, default=str)
    except Exception:
        return uygunluk.malzeme_rolleri(spec)
    sonuc = _ROL_ONBELLEK.get(anahtar)
    if sonuc is None:
        if len(_ROL_ONBELLEK) > 16:
            _ROL_ONBELLEK.clear()
        sonuc = _ROL_ONBELLEK[anahtar] = uygunluk.malzeme_rolleri(spec)
    return {ad: set(r) for ad, r in sonuc.items()}


def rol_listesi(spec, rol):
    """uygunluk.rol_malzemeleri ile ayni (spec sirasiyla), onbellekli roller."""
    r = roller(spec)
    return [m["ad"] for m in spec.get("malzemeler", []) if rol in r.get(m.get("ad"), ())]


def _elementler(m):
    """Malzemenin element sembolleri ("Zr90" -> "Zr")."""
    sonuc = set()
    for b in m.get("bilesim") or []:
        e = re.match(r"[A-Z][a-z]?", b.get("isim") or "")
        if e:
            sonuc.add(e.group(0))
    return sonuc


def rol_malzemesi(spec, rol, tercih=()):
    """
    Role uyan ilk malzeme (spec sirasiyla); tercih edilen elementi iceren
    varsa o (zarf: PWR'de zirkaloy, MTR'de aluminyum). Yoksa None.
    """
    adaylar = rol_listesi(spec, rol)
    for ad in adaylar:
        m = sema.malzeme_bul(spec, ad)
        if m is not None and _elementler(m) & set(tercih):
            return ad
    return adaylar[0] if adaylar else None


def cubuk_sablonu(spec, anahtar, ad):
    """
    CUBUK_SABLONLARI'ndan bir cubuk tanimi; malzemeler rollerine gore.
    Olculer PWR 17x17 (Westinghouse): pelet 0.4096, zarf ic/dis 0.418/0.475;
    kilavuz boru 0.561/0.602; emici (Ag-In-Cd / B4C) 0.433 cm.
    Kontrol cubugu kilavuz borusunun icinde durur: cekildiginde emici
    bolgenin yerini sogutucu (izleyici) alir, boru ici tamamen suyla dolar.
    """
    yakit = rol_malzemesi(spec, "yakit")
    gaz = rol_malzemesi(spec, "gaz") or sema.BOSLUK
    zarf = rol_malzemesi(spec, "yapisal", ("Zr",))
    sog = rol_malzemesi(spec, "sogutucu")
    b = sema.bolge
    if anahtar == "yakit":
        return sema.cubuk(ad, [b(0.4096, yakit), b(0.418, gaz), b(0.475, zarf),
                               b(None, sog)])
    if anahtar == "kilavuz":
        return sema.cubuk(ad, [b(0.561, sog), b(0.602, zarf), b(None, sog)])
    if anahtar == "kontrol":
        emici = rol_malzemesi(spec, "emici")
        return sema.kontrol_cubugu(
            ad, [b(0.433, emici), b(0.561, sog), b(0.602, zarf), b(None, sog)],
            izleyici_malzeme=sog, daldirma=0.0, emici_bolge=0)
    raise KeyError("bilinmeyen çubuk şablonu: %s" % anahtar)


# Sablonlarin istedigi roller (eksik olanlar kullaniciya adiyla soylenir).
_SABLON_ROLLERI = {
    "yakit": (("yakit", "yakıt"), ("yapisal", "zarf (yapısal)"), ("sogutucu", "soğutucu")),
    "kilavuz": (("yapisal", "zarf (yapısal)"), ("sogutucu", "soğutucu")),
    "kontrol": (("emici", "emici"), ("yapisal", "zarf (yapısal)"), ("sogutucu", "soğutucu")),
    "plaka": (("yakit", "yakıt"), ("yapisal", "zarf (yapısal)"), ("sogutucu", "soğutucu")),
}


def sablon_eksik_roller(spec, anahtar):
    """Sablonun istedigi ama spec'te karsiligi olmayan roller (okunur adlarla)."""
    return [etiket for rol, etiket in _SABLON_ROLLERI[anahtar]
            if not rol_listesi(spec, rol)]


def plaka_sablonu(spec, ad):
    """MTR plaka elemani (23 plaka); malzemeler rollerine gore, zarf Al tercihli."""
    return sema.plaka(ad, 23, 0.051, 0.038, 0.200, 6.30,
                      rol_malzemesi(spec, "yakit"),
                      rol_malzemesi(spec, "yapisal", ("Al",)),
                      rol_malzemesi(spec, "sogutucu"),
                      yan_levha_kalinlik=0.475)


def _tanimli(spec, ad):
    return ad == sema.BOSLUK or sema.malzeme_bul(spec, ad) is not None


def eksik_malzemeler(spec, parca):
    """
    Parcada malzemesi SECILMEMIS (None) ya da tanimsiz alanlarin okunur
    listesi. Bos liste = eksik yok. Bos (madde yok) bilincli bir secimdir,
    eksik sayilmaz.
    """
    eksik = []
    if parca is None:
        return eksik
    if parca.get("tur") == "plaka":
        for alan, etiket in (("et_malzeme", "yakıt tabakası"), ("zarf_malzeme", "zarf"),
                             ("sogutucu", "soğutucu")):
            ad = parca.get(alan)
            if ad is None or not _tanimli(spec, ad):
                eksik.append(etiket)
        yan = parca.get("yan_levha_malzeme")
        if yan is not None and not _tanimli(spec, yan) and \
                float(parca.get("yan_levha_kalinlik") or 0.0) > 0:
            eksik.append("yan levha")
        return eksik
    bolgeler = parca.get("bolgeler") or []
    for i, b in enumerate(bolgeler):
        ad = b.get("malzeme")
        if ad is None or not _tanimli(spec, ad):
            eksik.append("%d. bölge (%s)" % (i + 1, bolge_aciklamasi(spec, parca, i)
                                             if ad is not None else _konum_adi(parca, i)))
    if parca.get("tur") == "kontrol":
        iz = parca.get("izleyici_malzeme")
        if iz is None or not _tanimli(spec, iz):
            eksik.append("izleyici malzeme")
    return eksik


def _konum_adi(c, i):
    n = len(c.get("bolgeler") or [])
    return "dış bölge" if i == n - 1 else "iç bölge"


def bolge_aciklamasi(spec, c, i):
    """Bolgenin rolunu soyleyen kisa metin (tablonun 'Bölge' sutunu)."""
    bolgeler = c.get("bolgeler") or []
    n = len(bolgeler)
    ad = bolgeler[i].get("malzeme") if 0 <= i < n else None
    if i == n - 1:
        return "Dış bölge — hücrenin kalanını doldurur"
    if ad is None:
        return "Malzeme seçilmedi"
    rol_tablosu = roller(spec)

    def rol(j):
        if not (0 <= j < n):
            return set()
        a = bolgeler[j].get("malzeme")
        if a == sema.BOSLUK:
            return {"bos"}
        return rol_tablosu.get(a, set())

    r = rol(i)
    ek = ""
    if c.get("tur") == "kontrol" and c.get("emici_bolge") == i:
        ek = " (daldırılan)"
    if "yakit" in r:
        return "Yakıt" + ek
    if ("gaz" in r or "bos" in r) and "yakit" in rol(i - 1):
        return "Yakıt-zarf aralığı" + ek
    if "emici" in r:
        return "Emici" + ek
    if "yapisal" in r:
        return "Zarf / yapı" + ek
    if "sogutucu" in r or "moderator" in r:
        return "Soğutucu" + ek
    if "gaz" in r:
        return "Gaz" + ek
    if "bos" in r:
        return "Boş" + ek
    return "Bölge" + ek


def malzeme_etiketi(spec, ad, rol_goster=False, rol_tablosu=None):
    """Kullaniciya gosterilen malzeme adi: Malzemeler sekmesiyle ayni
    "ad — aciklama" bicimi (sema.malzeme_etiketi; ad benzersiz oldugu icin
    etiket de benzersizdir)."""
    if ad is None:
        return SECILMEDI_ETIKETI
    if ad == sema.BOSLUK:
        return BOS_ETIKETI
    m = sema.malzeme_bul(spec, ad)
    if m is None:
        return "%s (tanımsız)" % ad
    metin = sema.malzeme_etiketi(m)
    if rol_goster:
        r = (rol_tablosu if rol_tablosu is not None else roller(spec)).get(ad, set())
        adlar = [ROL_ADI[x] for x in uygunluk.ROLLER if x in r]
        if adlar:
            metin = "%s · %s" % (metin, ", ".join(adlar))
    return metin


def _betik_adi(ad):
    """kod_uret'in degisken adi (iki ad ayni degiskene dusmesin)."""
    try:
        from cekirdek.kod_uret import _ad
        return _ad(ad)
    except Exception:
        return ad


def ad_hatasi(spec, yeni, eski=None):
    """
    Yeni parca adi gecerli mi? Gecerliyse None, degilse okunur hata metni.
    Adlar cubuk/plaka/demet/malzeme arasinda TEKIL olmali: kurucu bir adi
    cubuk -> plaka -> demet -> malzeme sirasiyla cozer; ayni ad baska bir
    seyi gizlerdi. "bosluk" ayrilmistir.
    """
    yeni = (yeni or "").strip()
    if not yeni:
        return "Ad boş olamaz."
    if yeni == eski:
        return None
    if yeni == sema.BOSLUK:
        return "'%s' ayrılmış bir addır (Boş, madde yok)." % yeni
    diger = [x["ad"] for liste in ("cubuklar", "plakalar", "demetler", "malzemeler")
             for x in spec.get(liste, []) if x.get("ad") != eski]
    if yeni in diger:
        return "Bu ad zaten kullanılıyor: %s" % yeni
    betik = _betik_adi(yeni)
    for a in diger:
        if _betik_adi(a) == betik:
            return ("'%s' adı üretilen betikte '%s' ile aynı değişkene düşer; "
                    "başka bir ad seçin." % (yeni, a))
    return None


def benzersiz_ad(spec, taban):
    """taban, taban_2, taban_3 ... icinden ad_hatasi vermeyen ilk ad."""
    ad, i = taban, 2
    while ad_hatasi(spec, ad) is not None:
        ad = "%s_%d" % (taban, i)
        i += 1
    return ad


def _parca_bul(spec, ad):
    for liste in ("cubuklar", "plakalar", "demetler"):
        for x in spec.get(liste, []):
            if x.get("ad") == ad:
                return x
    return None


def parca_adini_degistir(spec, eski, yeni):
    """
    Cubuk/plaka/demet adini ve ONA ISARET EDEN BUTUN referanslari degistirir:
      demetler[].anahtar degerleri
      kor.cubuk / kor.plaka / kor.demet / kor.dolgu
      kor.anahtar (kor haritasi) degerleri
      kor.eksenel.bolgeler[].dolgu ve .anahtar degerleri
      guc_dagilimi.cubuk
    (tukenme ve tallyler yalnizca MALZEME adi tutar.) Yerinde degistirir;
    guncellenen referans sayisini dondurur. Parca yoksa KeyError.
    """
    parca = _parca_bul(spec, eski)
    if parca is None:
        raise KeyError("tanımsız parça: %s" % eski)
    parca["ad"] = yeni
    sayac = [0]

    def esle(sozluk):
        for h, hedef in list((sozluk or {}).items()):
            if hedef == eski:
                sozluk[h] = yeni
                sayac[0] += 1

    def alan(sozluk, anahtar):
        if sozluk is not None and sozluk.get(anahtar) == eski:
            sozluk[anahtar] = yeni
            sayac[0] += 1

    for d in spec.get("demetler", []):
        esle(d.get("anahtar"))
    kor = spec.get("kor") or {}
    for a in ("cubuk", "plaka", "demet", "dolgu"):
        alan(kor, a)
    esle(kor.get("anahtar"))
    for b in (kor.get("eksenel") or {}).get("bolgeler") or []:
        alan(b, "dolgu")
        esle(b.get("anahtar"))
    alan(spec.get("guc_dagilimi"), "cubuk")
    return sayac[0]


def parca_kullanimlari(spec, ad):
    """Parcanin kullanildigi yerler (okunur metinler) -- silmeden once sorulur."""
    yerler = []
    for d in spec.get("demetler", []):
        if d.get("ad") != ad and ad in (d.get("anahtar") or {}).values():
            yerler.append("'%s' demeti" % d["ad"])
    kor = spec.get("kor") or {}
    if sema.ana_dolgu(kor) == ad or ad in (kor.get("anahtar") or {}).values():
        yerler.append("kor")
    for b in (kor.get("eksenel") or {}).get("bolgeler") or []:
        if b.get("dolgu") == ad or ad in (b.get("anahtar") or {}).values():
            yerler.append("'%s' eksenel katmanı" % (b.get("ad") or "adsız"))
    if (spec.get("guc_dagilimi") or {}).get("cubuk") == ad:
        yerler.append("güç dağılımı")
    return yerler


def kor_dolgusu_bos_mu(spec, alan):
    """kor[alan] bos ya da tanimsiz bir parcaya mi isaret ediyor?"""
    ad = (spec.get("kor") or {}).get(alan)
    return not ad or _parca_bul(spec, ad) is None


def parca_rengi(spec, parca):
    """Listede simge rengi: cubukta en ic bolgenin, plakada yakit tabakasinin rengi."""
    adlar = ([b.get("malzeme") for b in parca.get("bolgeler") or []]
             if parca.get("tur") != "plaka" else [parca.get("et_malzeme")])
    for ad in adlar:
        m = sema.malzeme_bul(spec, ad) if ad else None
        if m is not None and m.get("renk"):
            return tuple(int(x) for x in m["renk"][:3])
    return (170, 170, 170)


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


# ============================================================================
# sekme
# ============================================================================

class CubukSekmesi(SekmeTabani):
    """Cubuk ve plaka tanimlari."""

    KONU = "cubuk"

    def __init__(self, parent=None):
        super().__init__(parent)

        # --- sol: parca listesi ---
        self.liste = QtWidgets.QListWidget()
        self.liste.setIconSize(QtCore.QSize(14, 14))
        self.liste.currentRowChanged.connect(self._secim_degisti)
        self.d_cubuk = QtWidgets.QPushButton("+ Çubuk")
        self.cubuk_menusu = QtWidgets.QMenu(self.d_cubuk)
        self.sablon_eylemleri = {}
        for anahtar, metin, _ad in CUBUK_SABLONLARI:
            e = self.cubuk_menusu.addAction(metin)
            e.triggered.connect(lambda _c=False, a=anahtar: self.cubuk_ekle(a))
            self.sablon_eylemleri[anahtar] = e
        self.sablon_eylemleri["yakit"].setToolTip(
            "Yakıt, yakıt-zarf aralığı, zarf ve soğutucu; malzemeler rollerine göre seçilir.")
        self.sablon_eylemleri["kilavuz"].setToolTip(
            "Suyla dolu kılavuz boru (zarf + soğutucu).")
        self.sablon_eylemleri["kontrol"].setToolTip(
            "Kılavuz borusunda eksenel hareket eden emici çubuk (3B model).")
        self.cubuk_menusu.setToolTipsVisible(True)
        self.d_cubuk.setMenu(self.cubuk_menusu)
        self.d_plaka = QtWidgets.QPushButton("+ Plaka")
        self.d_kopya = QtWidgets.QPushButton("Kopyala")
        self.d_sil = QtWidgets.QPushButton("Sil")
        self.d_plaka.clicked.connect(self.plaka_ekle)
        self.d_kopya.clicked.connect(self._kopyala)
        self.d_sil.clicked.connect(self._sil)
        ekle = QtWidgets.QHBoxLayout()
        ekle.addWidget(self.d_cubuk)
        ekle.addWidget(self.d_plaka)
        islem = QtWidgets.QHBoxLayout()
        islem.addWidget(self.d_kopya)
        islem.addWidget(self.d_sil)
        sol = QtWidgets.QWidget()
        sol_d = QtWidgets.QVBoxLayout(sol)
        sol_d.setContentsMargins(0, 0, 0, 0)
        sol_d.addWidget(baslik("Parçalar"))
        sol_d.addWidget(self.liste, 1)
        sol_d.addLayout(ekle)
        sol_d.addLayout(islem)

        # --- sag: editor yigini ---
        self.bos = BosDurum("Henüz parça yok", "", "Yakıt çubuğu ekle")
        self.bos.eylem.connect(self._bos_eylem)
        self.yigin = QtWidgets.QStackedWidget()
        self.yigin.addWidget(self.bos)
        self.cubuk_sayfa = self._cubuk_sayfa()
        self.plaka_sayfa = self._plaka_sayfa()
        self.yigin.addWidget(self.cubuk_sayfa)
        self.yigin.addWidget(self.plaka_sayfa)

        bolucu = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        bolucu.addWidget(sol)
        bolucu.addWidget(self.yigin)
        bolucu.setStretchFactor(0, 0)
        bolucu.setStretchFactor(1, 1)
        bolucu.setSizes([210, 520])
        bolucu.setChildrenCollapsible(False)

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(bolucu)

    # ------------------------------------------------------------------
    # sayfalar
    # ------------------------------------------------------------------
    def _hata_etiketi(self):
        e = QtWidgets.QLabel("")
        e.setWordWrap(True)
        e.setVisible(False)
        return e

    def _hata_goster(self, etiket, metin):
        etiket.setText(metin or "")
        etiket.setStyleSheet("color: %s;" % _renk("hata", "#b3261e"))
        etiket.setVisible(bool(metin))

    def _cubuk_sayfa(self):
        w = QtWidgets.QWidget()
        self.c_ad = QtWidgets.QLineEdit()
        self.c_ad.editingFinished.connect(lambda: self._ad_degisti("cubuk"))
        self.c_ad_hata = self._hata_etiketi()

        # --- kontrol cubugu alanlari ---
        self.c_tur = QtWidgets.QComboBox()
        self.c_emici = QtWidgets.QComboBox()
        self.c_izleyici = QtWidgets.QComboBox()
        self.c_daldirma = sayi(0.0, 2, 0.0, 100.0, 5.0, "%")
        self.c_daldirma_kaydirici = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.c_daldirma_kaydirici.setRange(0, 1000)
        self.c_uc_etiket = QtWidgets.QLabel("-")
        self.c_kontrol_etiketleri = {}

        self.c_tablo = QtWidgets.QTableWidget(0, 3)
        self.c_tablo.setHorizontalHeaderLabels(["Dış yarıçap", "Malzeme", "Bölge"])
        bas = self.c_tablo.horizontalHeader()
        bas.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        bas.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        bas.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.c_tablo.verticalHeader().setVisible(False)
        self.c_tablo.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.c_tablo.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.c_tablo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.c_tablo.currentCellChanged.connect(lambda *_: self._bolge_dugmeleri())
        self._satir_takibi = _SatirTakibi(self.c_tablo)

        self.d_bolge_ekle = QtWidgets.QPushButton("Bölge ekle")
        self.d_bolge_sil = QtWidgets.QPushButton("Bölge sil")
        self.d_ice = QtWidgets.QPushButton("İçe taşı")
        self.d_disa = QtWidgets.QPushButton("Dışa taşı")
        self.d_bolge_ekle.setToolTip("Dış bölgenin hemen içine yeni bir bölge ekler.")
        self.d_ice.setToolTip("Seçili bölgenin malzemesini bir içteki bölgeyle değiştirir; "
                              "yarıçaplar yerinde kalır.")
        self.d_disa.setToolTip("Seçili bölgenin malzemesini bir dıştaki bölgeyle değiştirir; "
                               "yarıçaplar yerinde kalır. Dış bölgeye taşınmaz.")
        self.d_bolge_ekle.clicked.connect(self._bolge_ekle)
        self.d_bolge_sil.clicked.connect(self._bolge_sil)
        self.d_ice.clicked.connect(lambda: self._bolge_tasi(-1))
        self.d_disa.clicked.connect(lambda: self._bolge_tasi(+1))
        dugme = QtWidgets.QHBoxLayout()
        for b in (self.d_bolge_ekle, self.d_bolge_sil, self.d_ice, self.d_disa):
            dugme.addWidget(b)
        dugme.addStretch(1)

        form = QtWidgets.QFormLayout()
        form.addRow("Ad:", self.c_ad)
        form.addRow("", self.c_ad_hata)
        self.e_tur = QtWidgets.QLabel("Tür:")
        form.addRow(self.e_tur, self.c_tur)
        for etiket, alan, anahtar in (
                ("Emici bölge:", self.c_emici, "emici"),
                ("İzleyici malzeme:", self.c_izleyici, "izleyici")):
            e = QtWidgets.QLabel(etiket)
            self.c_kontrol_etiketleri[anahtar] = e
            form.addRow(e, alan)
        self.c_emici.setToolTip("Eksenel olarak daldırılan (emici) bölge. Dış bölge seçilemez.")
        self.c_izleyici.setToolTip(
            "Emici bölgenin çubuk ucunun altında kalan kısmını dolduran malzeme "
            "(follower). Yakıt ve emici malzemeler listelenmez.")
        dald = QtWidgets.QWidget()
        dd = QtWidgets.QHBoxLayout(dald)
        dd.setContentsMargins(0, 0, 0, 0)
        dd.addWidget(self.c_daldirma)
        dd.addWidget(self.c_daldirma_kaydirici, 1)
        e = QtWidgets.QLabel("Daldırma:")
        self.c_kontrol_etiketleri["daldirma"] = e
        form.addRow(e, dald)
        e = QtWidgets.QLabel("Uç konumu:")
        self.c_kontrol_etiketleri["uc"] = e
        form.addRow(e, self.c_uc_etiket)

        self.c_kontrol_not = ipucu(
            "Kontrol çubuğu yukarıdan daldırılır: %0 tamamen çekilmiş, %100 tamamen "
            "dalmış. Emici bölgenin uç altında kalan kısmı izleyici malzemeyle dolar. "
            "Kritik çubuk konumunu bulmak için Analiz sekmesinde 'Kritik arama' ile "
            "'Kontrol çubuğu daldırma' parametresini kullanın.")
        self.c_eksik = self._hata_etiketi()
        self.c_sira_uyari = self._hata_etiketi()

        d = QtWidgets.QVBoxLayout(w)
        self.c_baslik = baslik("Çubuk")
        d.addWidget(self.c_baslik)
        d.addLayout(form)
        d.addWidget(self.c_kontrol_not)
        d.addWidget(baslik("Radyal bölgeler"))
        d.addWidget(ipucu(
            "Bölgeler içten dışa sıralanır; her satırın yarıçapı o bölgenin dış "
            "sınırıdır ve bir öncekinden büyük olmalıdır. Son satır dış bölgedir: "
            "çubuğun çevresini hücrenin kenarına kadar doldurur (çoğunlukla soğutucu)."))
        d.addWidget(self.c_tablo, 1)
        d.addWidget(self.c_sira_uyari)
        d.addWidget(self.c_eksik)
        d.addLayout(dugme)

        self.c_tur.currentIndexChanged.connect(self._cubuk_tur_degisti)
        self.c_emici.currentIndexChanged.connect(self._cubuk_kaydet)
        self.c_izleyici.currentIndexChanged.connect(self._cubuk_kaydet)
        self.c_daldirma.valueChanged.connect(self._daldirma_degisti)
        self.c_daldirma_kaydirici.valueChanged.connect(self._kaydirici_degisti)
        return w

    def _plaka_sayfa(self):
        w = QtWidgets.QWidget()
        self.p_ad = QtWidgets.QLineEdit()
        self.p_ad.editingFinished.connect(lambda: self._ad_degisti("plaka"))
        self.p_ad_hata = self._hata_etiketi()
        self.p_sayi = tamsayi(23, 1, 500, 1, "plaka")
        self.p_et = sayi(0.051, 5, 0.0001, 10.0, 0.001, "cm")
        self.p_zarf = sayi(0.038, 5, 0.0001, 10.0, 0.001, "cm")
        self.p_kanal = sayi(0.200, 5, 0.0001, 10.0, 0.001, "cm")
        self.p_genislik = sayi(6.30, 4, 0.01, 100.0, 0.1, "cm")
        self.p_yan = sayi(0.475, 4, 0.0, 10.0, 0.01, "cm")
        self.p_ozet = QtWidgets.QLabel("-")
        self.p_eksik = self._hata_etiketi()
        # Malzeme kutulari her yuklemede yeniden kurulur (role gore suzulu).
        self.p_et_mal = self.p_zarf_mal = self.p_sog = self.p_yan_mal = None

        self.p_form = QtWidgets.QFormLayout()
        f = self.p_form
        f.addRow("Ad:", self.p_ad)
        f.addRow("", self.p_ad_hata)
        f.addRow("Plaka sayısı:", self.p_sayi)
        f.addRow("Yakıt tabakası kalınlığı:", self.p_et)
        f.addRow("Zarf kalınlığı (her yüz):", self.p_zarf)
        f.addRow("Soğutucu kanal aralığı:", self.p_kanal)
        f.addRow("Aktif genişlik (y):", self.p_genislik)
        self._p_satir = {}
        for anahtar, etiket in (("et_malzeme", "Yakıt malzemesi:"),
                                ("zarf_malzeme", "Zarf malzemesi:"),
                                ("sogutucu", "Soğutucu:")):
            yer = QtWidgets.QWidget()
            yd = QtWidgets.QHBoxLayout(yer)
            yd.setContentsMargins(0, 0, 0, 0)
            self._p_satir[anahtar] = yd
            f.addRow(etiket, yer)
        f.addRow("Yan levha kalınlığı:", self.p_yan)
        yer = QtWidgets.QWidget()
        yd = QtWidgets.QHBoxLayout(yer)
        yd.setContentsMargins(0, 0, 0, 0)
        self._p_satir["yan_levha_malzeme"] = yd
        self.e_yan_mal = QtWidgets.QLabel("Yan levha malzemesi:")
        f.addRow(self.e_yan_mal, yer)
        f.addRow("Eleman dış ölçüsü (x × y):", self.p_ozet)

        for alan in (self.p_sayi, self.p_et, self.p_zarf, self.p_kanal,
                     self.p_genislik, self.p_yan):
            alan.valueChanged.connect(self._plaka_kaydet)

        d = QtWidgets.QVBoxLayout(w)
        d.addWidget(baslik("MTR tipi plaka yakıt elemanı"))
        d.addWidget(ipucu(
            "Kesit x yönünde sırayla kurulur: kanal [zarf | yakıt | zarf] kanal "
            "[zarf | yakıt | zarf] … ve sonda bir kanal daha. Yan levhalar y "
            "yönünde aktif bölgenin altında ve üstünde yer alır."))
        d.addLayout(f)
        d.addWidget(self.p_eksik)
        d.addStretch(1)
        return w

    # ------------------------------------------------------------------
    # doldurma
    # ------------------------------------------------------------------
    def doldur(self):
        onceki = self._secili()
        self.liste.blockSignals(True)
        self.liste.clear()
        for c in self.spec.get("cubuklar", []):
            ek = "  · kontrol" if c.get("tur") == "kontrol" else ""
            oge = QtWidgets.QListWidgetItem(renk_simgesi(parca_rengi(self.spec, c)),
                                            c["ad"] + ek)
            oge.setData(QtCore.Qt.UserRole, ("cubuk", c["ad"]))
            self._liste_isareti(oge, c)
            self.liste.addItem(oge)
        for p in self.spec.get("plakalar", []):
            oge = QtWidgets.QListWidgetItem(renk_simgesi(parca_rengi(self.spec, p)),
                                            p["ad"] + "  · plaka")
            oge.setData(QtCore.Qt.UserRole, ("plaka", p["ad"]))
            self._liste_isareti(oge, p)
            self.liste.addItem(oge)
        hedef = 0
        for i in range(self.liste.count()):
            if self.liste.item(i).data(QtCore.Qt.UserRole) == onceki:
                hedef = i
        if self.liste.count():
            self.liste.setCurrentRow(hedef)
        self.liste.blockSignals(False)
        self._secim_degisti(self.liste.currentRow())
        self._eylemleri_guncelle()

    def _liste_isareti(self, oge, parca):
        eksik = eksik_malzemeler(self.spec, parca)
        if eksik:
            oge.setText(oge.text() + "  ⚠")
            oge.setForeground(QtGui.QColor(_renk("hata", "#b3261e")))
            oge.setToolTip("Malzemesi seçilmemiş: %s" % ", ".join(eksik))

    def _eylemleri_guncelle(self):
        """Ekleme dugmeleri yalnizca bu modelde anlamli parcalar icin."""
        spec = self.spec or sema.yeni_spec()
        turler = uygunluk.parca_turleri(spec)
        malzeme_var = bool(spec.get("malzemeler"))
        self.d_cubuk.setVisible(turler["cubuk"])
        self.d_plaka.setVisible(turler["plaka"])
        self.sablon_eylemleri["kontrol"].setVisible(turler["kontrol_cubugu"])
        for d, metin in ((self.d_cubuk, "Şablondan çubuk ekler; malzemeler rollerine "
                                       "göre otomatik seçilir."),
                         (self.d_plaka, "MTR plaka elemanı ekler; malzemeler rollerine "
                                        "göre otomatik seçilir.")):
            d.setEnabled(malzeme_var)
            d.setToolTip(metin if malzeme_var else MALZEME_YOK_IPUCU)
        secili = self._secili()[0] is not None
        self.d_kopya.setEnabled(secili)
        self.d_sil.setEnabled(secili)
        self._bos_durum_guncelle(turler, malzeme_var)

    def _bos_durum_guncelle(self, turler, malzeme_var):
        if not malzeme_var:
            self.bos.ayarla("Önce malzeme gerekli",
                            "Parçalar malzemelerden kurulur. Malzemeler sekmesinden "
                            "yakıt, zarf ve soğutucu malzemelerini ekleyin.", "")
        elif self.liste.count():
            self.bos.ayarla("Bir parça seçin",
                            "Düzenlemek için soldaki listeden bir parça seçin.", "")
        elif turler["plaka"]:
            self.bos.ayarla("Henüz parça yok",
                            "Plaka elemanı ekleyin; malzemeler rollerine göre "
                            "otomatik seçilir.", "Plaka elemanı ekle")
        elif turler["cubuk"]:
            self.bos.ayarla("Henüz parça yok",
                            "Soldaki '+ Çubuk' menüsünden bir şablon seçin; malzemeler "
                            "rollerine göre (yakıt, zarf, soğutucu) otomatik seçilir.",
                            "Yakıt çubuğu ekle")
        else:
            self.bos.ayarla("Bu model parça kullanmıyor",
                            "Bu kor türünde çubuk ya da plaka tanımlanmaz.", "")

    def _bos_eylem(self):
        if uygunluk.parca_turleri(self.spec)["plaka"]:
            self.plaka_ekle()
        else:
            self.cubuk_ekle("yakit")

    def _secili(self):
        oge = self.liste.currentItem()
        return oge.data(QtCore.Qt.UserRole) if oge else (None, None)

    def _secim_degisti(self, _satir):
        tur, ad = self._secili()
        eski = self._yukleniyor
        self._yukleniyor = True
        try:
            if tur == "cubuk" and sema.cubuk_bul(self.spec, ad) is not None:
                self._cubuk_doldur(sema.cubuk_bul(self.spec, ad))
                self.yigin.setCurrentWidget(self.cubuk_sayfa)
            elif tur == "plaka" and sema.plaka_bul(self.spec, ad) is not None:
                self._plaka_doldur(sema.plaka_bul(self.spec, ad))
                self.yigin.setCurrentWidget(self.plaka_sayfa)
            else:
                self.yigin.setCurrentWidget(self.bos)
        finally:
            self._yukleniyor = eski
        secili = tur is not None
        self.d_kopya.setEnabled(secili)
        self.d_sil.setEnabled(secili)

    # ------------------------------------------------------------------
    # cubuk
    # ------------------------------------------------------------------
    def _cubuk_doldur(self, c):
        if c is None:
            return
        self.c_ad.setText(c["ad"])
        self._hata_goster(self.c_ad_hata, "")
        kontrol = c.get("tur") == "kontrol"
        self.c_baslik.setText("Kontrol çubuğu" if kontrol else "Çubuk")
        # Tur: kontrol cubugu yalnizca modelde anlamliysa (3B + kafes) ya da
        # zaten kontrol cubuguysa (dosyadaki veri gizlenmez).
        izin = uygunluk.parca_turleri(self.spec)["kontrol_cubugu"]
        self.c_tur.clear()
        self.c_tur.addItem("Sabit çubuk", "silindirik")
        if izin or kontrol:
            self.c_tur.addItem("Kontrol çubuğu (eksenel hareketli)", "kontrol")
        self.c_tur.setCurrentIndex(max(self.c_tur.findData(c.get("tur", "silindirik")), 0))
        tek = self.c_tur.count() < 2
        self.e_tur.setVisible(not tek)
        self.c_tur.setVisible(not tek)

        self._emici_doldur(c)
        self._izleyici_doldur(c)
        dd = float(c.get("daldirma") or 0.0)
        self.c_daldirma.setValue(dd)
        self.c_daldirma_kaydirici.setValue(int(round(dd * 10)))
        self._kontrol_gorunurluk()
        self._uc_guncelle()
        self._tablo_doldur(c)

    def _emici_doldur(self, c):
        """Emici bolge: dis bolge haric; numaralandirma 1'den."""
        self.c_emici.clear()
        bolgeler = c.get("bolgeler") or []
        for j in range(max(len(bolgeler) - 1, 0)):
            self.c_emici.addItem("%d. bölge — %s" % (
                j + 1, malzeme_etiketi(self.spec, bolgeler[j].get("malzeme"))), j)
        ix = c.get("emici_bolge", 0)
        if c.get("tur") == "kontrol" and self.c_emici.findData(ix) < 0:
            self.c_emici.addItem("%s. bölge — geçersiz (dış bölge daldırılamaz)"
                                 % (ix + 1 if isinstance(ix, int) else ix), ix)
        self.c_emici.setCurrentIndex(max(self.c_emici.findData(ix), 0))

    def _izleyici_doldur(self, c):
        rol_tablosu = roller(self.spec)
        adaylar = [ad for ad, r in rol_tablosu.items() if not r & {"yakit", "emici"}]
        secili = c.get("izleyici_malzeme")
        self.c_izleyici.clear()
        if secili is None:
            self.c_izleyici.addItem(SECILMEDI_ETIKETI, None)
        self.c_izleyici.addItem(BOS_ETIKETI, sema.BOSLUK)
        for m in self.spec.get("malzemeler", []):
            if m["ad"] in adaylar:
                self.c_izleyici.addItem(malzeme_etiketi(self.spec, m["ad"], True, rol_tablosu),
                                        m["ad"])
        if secili is not None and self.c_izleyici.findData(secili) < 0:
            self.c_izleyici.addItem("%s — izleyici olamaz"
                                    % malzeme_etiketi(self.spec, secili), secili)
        self.c_izleyici.setCurrentIndex(max(self.c_izleyici.findData(secili), 0))

    def _tablo_doldur(self, c):
        self.c_tablo.setRowCount(0)
        bolgeler = c.get("bolgeler") or []
        n = len(bolgeler)
        for i, b in enumerate(bolgeler):
            son = i == n - 1
            self.c_tablo.insertRow(i)
            if son:
                oge = QtWidgets.QTableWidgetItem("dış bölge")
                oge.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                oge.setToolTip("Son bölgenin yarıçapı yoktur: hücrenin kalanını doldurur.")
                self.c_tablo.setItem(i, 0, oge)
            else:
                w = sayi(b.get("r") or 0.0, 5, 0.00001, 1000.0, 0.01, "cm")
                w.setKeyboardTracking(False)
                w.valueChanged.connect(self._yaricap_degisti)
                self._takip_et(w, i)
                self.c_tablo.setCellWidget(i, 0, w)
            k = MalzemeKutusu(self.spec, b.get("malzeme"))
            k.currentIndexChanged.connect(self._cubuk_kaydet)
            self._takip_et(k, i)
            self.c_tablo.setCellWidget(i, 1, k)
            aciklama = QtWidgets.QTableWidgetItem("")
            aciklama.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            self.c_tablo.setItem(i, 2, aciklama)
        self._aciklamalari_guncelle(c)
        self._yaricap_sinirlari()
        self._bolge_dugmeleri()

    def _takip_et(self, w, satir):
        w.setProperty("satir", satir)
        w.installEventFilter(self._satir_takibi)
        if isinstance(w, QtWidgets.QAbstractSpinBox) and w.lineEdit() is not None:
            w.lineEdit().setProperty("satir", satir)
            w.lineEdit().installEventFilter(self._satir_takibi)

    def _aciklamalari_guncelle(self, c):
        for i in range(self.c_tablo.rowCount()):
            oge = self.c_tablo.item(i, 2)
            if oge is not None:
                oge.setText(bolge_aciklamasi(self.spec, c, i))
        eksik = eksik_malzemeler(self.spec, c)
        self._hata_goster(self.c_eksik, (
            "Malzemesi seçilmemiş: %s. Uygun malzeme yoksa önce Malzemeler "
            "sekmesinden ekleyin." % ", ".join(eksik)) if eksik else "")

    def _yaricap_kutulari(self):
        n = self.c_tablo.rowCount()
        return [self.c_tablo.cellWidget(i, 0) for i in range(max(n - 1, 0))]

    def _yaricap_sinirlari(self):
        """Her yaricap kutusunun alt/ust siniri komsularindan: sira bozulamaz."""
        kutular = [k for k in self._yaricap_kutulari() if k is not None]
        r = [k.value() for k in kutular]
        artan = all(r[i] < r[i + 1] for i in range(len(r) - 1))
        eps = 1e-5
        for i, k in enumerate(kutular):
            k.blockSignals(True)
            try:
                if artan:
                    k.setRange(r[i - 1] + eps if i > 0 else eps,
                               r[i + 1] - eps if i + 1 < len(r) else 1000.0)
                else:
                    k.setRange(eps, 1000.0)
            finally:
                k.blockSignals(False)
        self._hata_goster(self.c_sira_uyari, "" if artan else (
            "Yarıçaplar içten dışa artmalı: %s. Değerleri düzeltin."
            % " → ".join("%.5g" % x for x in r)))

    def _bolge_dugmeleri(self):
        n = self.c_tablo.rowCount()
        satir = self.c_tablo.currentRow()
        ic = 0 <= satir < n - 1
        self.d_bolge_sil.setEnabled(ic and n > 2)
        self.d_ice.setEnabled(ic and satir > 0)
        self.d_disa.setEnabled(ic and satir + 1 < n - 1)

    def _kontrol_gorunurluk(self):
        kontrol = self.c_tur.currentData() == "kontrol"
        for w in list(self.c_kontrol_etiketleri.values()) + [
                self.c_emici, self.c_izleyici, self.c_daldirma,
                self.c_daldirma_kaydirici, self.c_uc_etiket, self.c_kontrol_not]:
            w.setVisible(kontrol)

    def _uc_guncelle(self):
        """
        Daldirma oranindan uc konumunu hesaplayip gosterir.

        Kurucu ile AYNI formul (kurucu.cubuk_universe): daldirma AKTIF yakit
        araliginda olculur, modelin toplam yuksekliginde degil:
            z_uc = z_ust - daldirma/100 * (z_ust - z_alt)
        """
        h = sema.kor_yuksekligi((self.spec or {}).get("kor") or {})
        if not h:
            self.c_uc_etiket.setText("Model 2B: Kor sekmesinde yükseklik tanımlayın")
            self.c_uc_etiket.setStyleSheet("color: %s;" % _renk("hata", "#b3261e"))
            return
        try:
            from cekirdek import kurucu
            z_alt, z_ust = kurucu.aktif_eksenel_aralik(self.spec) or (-h / 2.0, h / 2.0)
        except Exception:
            z_alt, z_ust = -h / 2.0, h / 2.0
        z = z_ust - (self.c_daldirma.value() / 100.0) * (z_ust - z_alt)
        self.c_uc_etiket.setText("z = %+.2f cm   (aktif yakıt: %+.1f … %+.1f cm)"
                                 % (z, z_alt, z_ust))
        self.c_uc_etiket.setStyleSheet("")

    def _cubuk_tur_degisti(self, *_):
        if self._yukleniyor:
            return
        tur, ad = self._secili()
        if tur != "cubuk":
            return
        c = sema.cubuk_bul(self.spec, ad)
        yeni_tur = self.c_tur.currentData()
        c["tur"] = yeni_tur
        if yeni_tur == "kontrol":
            if "emici_bolge" not in c:
                rol_tablosu = roller(self.spec)
                emici = [i for i, b in enumerate(c["bolgeler"][:-1])
                         if "emici" in rol_tablosu.get(b.get("malzeme"), ())]
                c["emici_bolge"] = emici[0] if emici else 0
            c.setdefault("daldirma", 0.0)
            if not c.get("izleyici_malzeme"):
                c["izleyici_malzeme"] = rol_malzemesi(self.spec, "sogutucu") or sema.BOSLUK
        self.spec_yukle(self.spec)
        self._sec(("cubuk", ad))
        self.bildir()

    def _daldirma_degisti(self, *_):
        if self._yukleniyor:
            return
        self._yukleniyor = True
        try:
            self.c_daldirma_kaydirici.setValue(int(round(self.c_daldirma.value() * 10)))
        finally:
            self._yukleniyor = False
        self._uc_guncelle()
        self._cubuk_kaydet()

    def _kaydirici_degisti(self, deger):
        if self._yukleniyor:
            return
        self._yukleniyor = True
        try:
            self.c_daldirma.setValue(deger / 10.0)
        finally:
            self._yukleniyor = False
        self._uc_guncelle()
        self._cubuk_kaydet()

    def _yaricap_degisti(self, *_):
        if self._yukleniyor:
            return
        self._cubuk_kaydet()
        self._yaricap_sinirlari()

    def _cubuk_kaydet(self, *_):
        if self._yukleniyor:
            return
        tur, ad = self._secili()
        if tur != "cubuk":
            return
        c = sema.cubuk_bul(self.spec, ad)
        bolgeler = []
        n = self.c_tablo.rowCount()
        for i in range(n):
            w = self.c_tablo.cellWidget(i, 0)
            r = None if (i == n - 1 or w is None) else w.value()
            k = self.c_tablo.cellWidget(i, 1)
            bolgeler.append({"r": r, "malzeme": k.currentData() if k else None})
        c["bolgeler"] = bolgeler
        if c.get("tur") == "kontrol":
            ix = self.c_emici.currentData()
            c["emici_bolge"] = ix if isinstance(ix, int) else 0
            c["izleyici_malzeme"] = self.c_izleyici.currentData()
            c["daldirma"] = self.c_daldirma.value()
        # Aciklama, eksik uyarisi ve emici listesi malzemeye bagli.
        self._yukleniyor = True
        try:
            self._aciklamalari_guncelle(c)
            if c.get("tur") == "kontrol":
                self._emici_doldur(c)
        finally:
            self._yukleniyor = False
        self._liste_ogesini_yenile(c)
        self.bildir()

    def _liste_ogesini_yenile(self, parca):
        oge = self.liste.currentItem()
        if oge is None:
            return
        tur = oge.data(QtCore.Qt.UserRole)[0]
        ek = ("  · plaka" if tur == "plaka"
              else "  · kontrol" if parca.get("tur") == "kontrol" else "")
        oge.setText(parca["ad"] + ek)
        oge.setIcon(renk_simgesi(parca_rengi(self.spec, parca)))
        oge.setData(QtCore.Qt.ForegroundRole, None)
        oge.setToolTip("")
        self._liste_isareti(oge, parca)

    def _secili_cubuk_yenile(self, c, satir=None):
        self._yukleniyor = True
        try:
            self._cubuk_doldur(c)
            if satir is not None:
                self.c_tablo.setCurrentCell(satir, 2)
        finally:
            self._yukleniyor = False
        self._bolge_dugmeleri()
        self._liste_ogesini_yenile(c)

    def _bolge_ekle(self):
        tur, ad = self._secili()
        if tur != "cubuk":
            return
        c = sema.cubuk_bul(self.spec, ad)
        yaricaplar = [b["r"] for b in c["bolgeler"] if b.get("r")]
        yeni_r = (max(yaricaplar) * 1.1) if yaricaplar else 0.4
        n = len(c["bolgeler"])
        # Malzemesi SECILMEMIS olarak eklenir: sessizce bosluk/su olmasin,
        # kullanici secene kadar kirmizi isaretli kalir.
        c["bolgeler"].insert(n - 1, {"r": round(yeni_r, 5), "malzeme": None})
        self._secili_cubuk_yenile(c, n - 1)
        self.bildir()

    def _bolge_sil(self):
        tur, ad = self._secili()
        if tur != "cubuk":
            return
        c = sema.cubuk_bul(self.spec, ad)
        satir = self.c_tablo.currentRow()
        if satir < 0 or satir >= len(c["bolgeler"]) - 1 or len(c["bolgeler"]) <= 2:
            return                     # dugme zaten kapali
        c["bolgeler"].pop(satir)
        if c.get("tur") == "kontrol":
            ix = c.get("emici_bolge", 0)
            if isinstance(ix, int) and satir < ix:
                c["emici_bolge"] = ix - 1
            elif ix == satir:
                c["emici_bolge"] = 0
        self._secili_cubuk_yenile(c, min(satir, len(c["bolgeler"]) - 2))
        self.bildir()

    def _bolge_tasi(self, yon):
        """Secili bolgenin MALZEMESINI komsusuyla degistirir; yaricaplar yerinde."""
        tur, ad = self._secili()
        if tur != "cubuk":
            return
        c = sema.cubuk_bul(self.spec, ad)
        i = self.c_tablo.currentRow()
        j = i + yon
        son = len(c["bolgeler"]) - 1
        if i < 0 or i >= son or j < 0 or j >= son:
            return
        b = c["bolgeler"]
        b[i]["malzeme"], b[j]["malzeme"] = b[j].get("malzeme"), b[i].get("malzeme")
        if c.get("tur") == "kontrol":
            ix = c.get("emici_bolge", 0)
            if ix == i:
                c["emici_bolge"] = j
            elif ix == j:
                c["emici_bolge"] = i
        self._secili_cubuk_yenile(c, j)
        self.bildir()

    # ------------------------------------------------------------------
    # plaka
    # ------------------------------------------------------------------
    def _plaka_kutusu(self, anahtar, kutu):
        yer = self._p_satir[anahtar]
        while yer.count():
            w = yer.takeAt(0).widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        yer.addWidget(kutu, 1)
        kutu.currentIndexChanged.connect(self._plaka_kaydet)
        return kutu

    def _plaka_doldur(self, p):
        if p is None:
            return
        self.p_ad.setText(p["ad"])
        self._hata_goster(self.p_ad_hata, "")
        self.p_sayi.setValue(p["plaka_sayisi"])
        self.p_et.setValue(p["et_kalinlik"])
        self.p_zarf.setValue(p["zarf_kalinlik"])
        self.p_kanal.setValue(p["kanal_kalinlik"])
        self.p_genislik.setValue(p["plaka_genislik"])
        self.p_yan.setValue(p.get("yan_levha_kalinlik") or 0.0)
        s = self.spec
        yapisal = rol_listesi(s, "yapisal")
        self.p_et_mal = self._plaka_kutusu("et_malzeme", MalzemeKutusu(
            s, p.get("et_malzeme"), rol_listesi(s, "yakit"), bos=False))
        self.p_zarf_mal = self._plaka_kutusu("zarf_malzeme", MalzemeKutusu(
            s, p.get("zarf_malzeme"), yapisal, bos=False))
        self.p_sog = self._plaka_kutusu("sogutucu", MalzemeKutusu(
            s, p.get("sogutucu"), rol_listesi(s, "sogutucu"), bos=False))
        self.p_yan_mal = self._plaka_kutusu("yan_levha_malzeme", MalzemeKutusu(
            s, p.get("yan_levha_malzeme"), yapisal, bos=False,
            yok_etiketi="Zarf ile aynı"))
        self._plaka_ozet(p)

    def _plaka_ozet(self, p):
        tx = p["plaka_sayisi"] * (2 * p["zarf_kalinlik"] + p["et_kalinlik"]) \
            + (p["plaka_sayisi"] + 1) * p["kanal_kalinlik"]
        ty = p["plaka_genislik"] + 2 * (p.get("yan_levha_kalinlik") or 0.0)
        self.p_ozet.setText("%.4f × %.4f cm" % (tx, ty))
        yan_var = float(p.get("yan_levha_kalinlik") or 0.0) > 0
        if self.p_yan_mal is not None:
            self.p_yan_mal.setEnabled(yan_var)
            self.p_yan_mal.setToolTip("" if yan_var else
                                      "Yan levha kalınlığı 0: yan levha kurulmaz.")
        self.e_yan_mal.setEnabled(yan_var)
        eksik = eksik_malzemeler(self.spec, p)
        self._hata_goster(self.p_eksik, (
            "Malzemesi seçilmemiş: %s. Uygun malzeme yoksa önce Malzemeler "
            "sekmesinden ekleyin." % ", ".join(eksik)) if eksik else "")

    def _plaka_kaydet(self, *_):
        if self._yukleniyor:
            return
        tur, ad = self._secili()
        if tur != "plaka":
            return
        p = sema.plaka_bul(self.spec, ad)
        p["plaka_sayisi"] = self.p_sayi.value()
        p["et_kalinlik"] = self.p_et.value()
        p["zarf_kalinlik"] = self.p_zarf.value()
        p["kanal_kalinlik"] = self.p_kanal.value()
        p["plaka_genislik"] = self.p_genislik.value()
        p["yan_levha_kalinlik"] = self.p_yan.value()
        p["et_malzeme"] = self.p_et_mal.currentData()
        p["zarf_malzeme"] = self.p_zarf_mal.currentData()
        p["sogutucu"] = self.p_sog.currentData()
        p["yan_levha_malzeme"] = self.p_yan_mal.currentData()
        self._plaka_ozet(p)
        self._liste_ogesini_yenile(p)
        self.bildir()

    # ------------------------------------------------------------------
    # ad degisimi
    # ------------------------------------------------------------------
    def _ad_degisti(self, tur_):
        tur, ad = self._secili()
        if tur != tur_:
            return
        alan, hata_etiketi = ((self.c_ad, self.c_ad_hata) if tur == "cubuk"
                              else (self.p_ad, self.p_ad_hata))
        yeni = alan.text().strip()
        if yeni == ad:
            self._hata_goster(hata_etiketi, "")
            return
        hata = ad_hatasi(self.spec, yeni, ad)
        if hata:
            alan.setText(ad)
            self._hata_goster(hata_etiketi, hata + " Ad değiştirilmedi.")
            return
        parca_adini_degistir(self.spec, ad, yeni)
        self.spec_yukle(self.spec)
        self._sec((tur, yeni))
        # Ad; kafes, kor ve HESAP AYARLARI (guc dagilimi cubugu) sekmelerinde
        # de gecer: hepsi yeniden yuklensin ("cubuk" konusu ayarlari tazelemez).
        if not self._yukleniyor:
            self.degisti.emit("genel")

    # ------------------------------------------------------------------
    # liste islemleri
    # ------------------------------------------------------------------
    def _onay_al(self, baslik_, metin):
        """Veri silen islemler icin onay. Testler bunu degistirir (modal acilmaz)."""
        cevap = QtWidgets.QMessageBox.question(
            self, baslik_, metin,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)
        return cevap == QtWidgets.QMessageBox.Yes

    def _kora_ata(self, alan, ad):
        """Kor bu tur parcayi istiyor ve henuz secilmemisse yeni parcayi ata
        (bos modelde ilk cubuk eklenince pin hucre hemen kurulur)."""
        kor = self.spec.get("kor") or {}
        istenen = {"tek_cubuk": "cubuk", "tek_plaka": "plaka"}.get(kor.get("tur"))
        if istenen == alan and kor_dolgusu_bos_mu(self.spec, alan):
            kor[alan] = ad

    def cubuk_ekle(self, sablon="yakit"):
        """Sablondan cubuk ekler; malzemeler rollerine gore secilir."""
        if not self.spec.get("malzemeler"):
            return None
        taban = dict((a, v) for a, _m, v in CUBUK_SABLONLARI)[sablon]
        ad = benzersiz_ad(self.spec, taban)
        self.spec.setdefault("cubuklar", []).append(cubuk_sablonu(self.spec, sablon, ad))
        self._kora_ata("cubuk", ad)
        self.spec_yukle(self.spec)
        self._sec(("cubuk", ad))
        self._sablon_eksigi(self.c_eksik, sablon)
        self.bildir()
        return ad

    def _sablon_eksigi(self, etiket, sablon):
        """Sablonun rolunu karsilayan malzeme yoksa bunu ADIYLA soyle."""
        eksik = sablon_eksik_roller(self.spec, sablon)
        if eksik:
            self._hata_goster(etiket, (
                "Bu modelde %s rolünde malzeme yok; ilgili bölgeler kırmızı "
                "işaretli. Önce Malzemeler sekmesinden ekleyin, sonra burada seçin."
                % " / ".join(eksik)))

    def plaka_ekle(self):
        if not self.spec.get("malzemeler"):
            return None
        ad = benzersiz_ad(self.spec, "plaka_eleman")
        self.spec.setdefault("plakalar", []).append(plaka_sablonu(self.spec, ad))
        self._kora_ata("plaka", ad)
        self.spec_yukle(self.spec)
        self._sec(("plaka", ad))
        self._sablon_eksigi(self.p_eksik, "plaka")
        self.bildir()
        return ad

    def _sec(self, anahtar):
        for i in range(self.liste.count()):
            if self.liste.item(i).data(QtCore.Qt.UserRole) == anahtar:
                self.liste.setCurrentRow(i)
                return

    def _kopyala(self):
        tur, ad = self._secili()
        if tur == "cubuk":
            y = copy.deepcopy(sema.cubuk_bul(self.spec, ad))
            y["ad"] = benzersiz_ad(self.spec, ad)
            self.spec["cubuklar"].append(y)
        elif tur == "plaka":
            y = copy.deepcopy(sema.plaka_bul(self.spec, ad))
            y["ad"] = benzersiz_ad(self.spec, ad)
            self.spec["plakalar"].append(y)
        else:
            return
        self.spec_yukle(self.spec)
        self._sec((tur, y["ad"]))
        self.bildir()

    def _sil(self):
        tur, ad = self._secili()
        if tur is None:
            return
        yerler = parca_kullanimlari(self.spec, ad)
        if yerler and not self._onay_al(
                "Parça kullanılıyor",
                "'%s' şurada kullanılıyor: %s.\n\nSilinirse bu yerler tanımsız bir "
                "parçaya işaret eder ve doğrulama hata verir. Silinsin mi?"
                % (ad, ", ".join(yerler))):
            return
        liste = self.spec["cubuklar"] if tur == "cubuk" else self.spec["plakalar"]
        for i, o in enumerate(liste):
            if o["ad"] == ad:
                liste.pop(i)
                break
        self.spec_yukle(self.spec)
        self.bildir()
