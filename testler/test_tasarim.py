# -*- coding: utf-8 -*-
"""
test_tasarim.py -- Dalga 1 tasarim sistemi (Ajan 3): tokenlar ve kontrast,
ikonlar, QSS (iki tema, ayristirma uyarisi yok), tema.py geriye uyumu ve
arayuz/bilesenler davranislari (KenarCubugu, KomutPaleti, Bildirim, SayiBirim,
SegmentSecici, Rozet, Kart, BosDurum). Yalnizca offscreen; hepsi HIZLI.
"""

import os

from testler.ortak_test import kontrol, AYAR_DIZINI   # noqa: F401
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Dalga 0 tema.renk anahtarlari: mevcut kod ve Ajan 1/2/4 bunlara bagli.
ESKI_ANAHTARLAR = ("ad", "zemin", "yuzey", "yuzey2", "metin", "metin_soluk", "kenar",
                   "vurgu", "vurgu_metin", "vurgu_soluk", "basari", "uyari", "hata",
                   "bilgi", "grafik_zemin", "grafik_izgara")


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _sil(*widgetlar):
    from PySide6 import QtCore
    for w in widgetlar:
        w.close()
        w.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


# ============================================================================
# 1. tokenlar
# ============================================================================
@gereksinim("R-A4-01")
def test_kontrast_wcag():
    print("\n[T1] TOKEN: WCAG AA kontrast (iki tema x her vurgu)")
    from arayuz.tasarim import tokenlar
    kontrol("kontrast olcer: siyah/beyaz = 21", abs(tokenlar.kontrast("#000000", "#ffffff") - 21) < 1e-6)
    kontrol("kontrast olcer: ayni renk = 1", abs(tokenlar.kontrast("#777777", "#777777") - 1) < 1e-9)
    for tema_ in ("acik", "koyu"):
        for vurgu in tokenlar.VURGULAR:
            kalan = [(on, arka, round(oran, 2), esik)
                     for on, arka, oran, esik, gecti in tokenlar.kontrast_raporu(tema_, vurgu)
                     if not gecti]
            kontrol("kontrast %s/%s: tum kurallar" % (tema_, vurgu), not kalan, "-> %s" % kalan)


def test_token_olcekleri():
    print("\n[T2] TOKEN: aralik olcegi, tipografi, palet anahtarlari")
    from arayuz.tasarim import tokenlar
    kontrol("aralik olcegi 4/8/12/16/24/32",
            sorted(tokenlar.ARALIK.values()) == [4, 8, 12, 16, 24, 32])
    kontrol("tipografi rolleri", {"baslik", "altbaslik", "govde", "kucuk", "mono"}
            <= set(tokenlar.TIPOGRAFI))
    a, k = tokenlar.palet("acik"), tokenlar.palet("koyu")
    kontrol("iki temanin anahtarlari ayni", set(a) == set(k))
    gerekli = {"zemin", "yuzey1", "yuzey2", "yuzey3", "kenar", "metin", "metin_ikincil",
               "metin_soluk", "vurgu", "vurgu_hover", "vurgu_basili", "odak",
               "basari", "basari_soluk", "uyari", "uyari_soluk", "hata", "hata_soluk",
               "bilgi", "bilgi_soluk"}
    kontrol("gerekli renk tokenlari", gerekli <= set(a), "-> eksik %s" % (gerekli - set(a)))
    p = tokenlar.palet("acik", "teal")
    kontrol("palet yeni sozluk verir (kaynak degismez)",
            p is not tokenlar.palet("acik", "teal") and p["vurgu"] != a["vurgu"])
    kontrol("grafik paleti 7 renk, iki tema", all(len(tokenlar.GRAFIK_PALETI[t]) == 7
                                                 for t in ("acik", "koyu")))


# ============================================================================
# 2. tema.py geriye uyum + QSS
# ============================================================================
def test_tema_eski_anahtarlar():
    print("\n[T3] TEMA: eski tema.renk anahtarlari ve API")
    from arayuz import tema
    for ad in ("acik", "koyu"):
        eksik = [k for k in ESKI_ANAHTARLAR if k not in tema.TEMALAR[ad]]
        kontrol("TEMALAR[%s] eski anahtarlarin hepsi" % ad, not eksik, "-> %s" % eksik)
    kontrol("etkin/renk/uygula/_stil var",
            all(callable(getattr(tema, a, None)) for a in ("etkin", "renk", "uygula", "_stil")))
    kontrol("renk('vurgu') #rrggbb", tema.renk("vurgu").startswith("#") and len(tema.renk("vurgu")) == 7)


def _tum_denetimler():
    from PySide6 import QtCore, QtWidgets
    from arayuz import bilesenler as b
    w = QtWidgets.QMainWindow()
    govde = QtWidgets.QWidget()
    d = QtWidgets.QVBoxLayout(govde)
    ogeler = [QtWidgets.QPushButton("a"), b.birincil_dugme("b"), b.tehlikeli_dugme("c"),
              b.duz_dugme("d"), b.ikon_dugmesi("x", "Kapat"), QtWidgets.QLineEdit("e"),
              QtWidgets.QSpinBox(), QtWidgets.QDoubleSpinBox(), QtWidgets.QComboBox(),
              QtWidgets.QCheckBox("f"), QtWidgets.QRadioButton("g"), QtWidgets.QProgressBar(),
              QtWidgets.QTableWidget(2, 2), QtWidgets.QTreeWidget(), QtWidgets.QListWidget(),
              QtWidgets.QGroupBox("h"), QtWidgets.QTabBar(), QtWidgets.QSlider(QtCore.Qt.Horizontal),
              QtWidgets.QPlainTextEdit(), b.Rozet("i", "hata"), b.Kart("Kart"),
              b.SayiBirim(birim="cm"), b.SegmentSecici([("a", "A"), ("b", "B")]),
              b.BosDurum("atom", "Bos"), b.KenarCubugu(), QtWidgets.QSplitter()]
    for o in ogeler:
        d.addWidget(o)
    w.setCentralWidget(govde)
    w.addToolBar("t").addAction("u")
    w.menuBar().addMenu("m").addAction("n")
    return w


def test_qss_uyarisiz():
    print("\n[T4] QSS: iki temada ayristirma uyarisi yok")
    from PySide6 import QtCore
    from arayuz import tema
    app = _qt()
    mesajlar = []

    def isleyici(_tur, _bag, mesaj):
        mesajlar.append(mesaj)
    eski = QtCore.qInstallMessageHandler(isleyici)
    onceki = tema.etkin()
    try:
        for ad in ("acik", "koyu"):
            tema.uygula(app, ad)
            w = _tum_denetimler()
            w.resize(900, 1400)
            w.show()
            app.processEvents()
            w.grab()
            _sil(w)
    finally:
        QtCore.qInstallMessageHandler(eski)
        tema.uygula(app, onceki)
    hatali = [m for m in mesajlar if "stylesheet" in m.lower() or "parse" in m.lower()]
    kontrol("QSS ayristirma uyarisi yok", not hatali, "-> %s" % hatali[:3])
    qss = tema._stil(tema.TEMALAR["koyu"])
    kontrol("QSS birincil/tehlikeli/hata/rozet secicileri",
            all(s in qss for s in ("QPushButton#birincil", 'QPushButton[tur="tehlikeli"]',
                                   '[hata="true"]', 'QLabel[rozet="basari"]', "QScrollBar")))
    kontrol("QSS sabit renk yalniz tokenlardan (koyu vurgu var, acik vurgu yok)",
            tema.TEMALAR["koyu"]["vurgu"] in qss and tema.TEMALAR["acik"]["vurgu"] not in qss)


def test_eski_ekran_uyumu():
    print("\n[T4b] QSS: mevcut ekranlarin model renkleri korunur")
    from PySide6 import QtGui, QtWidgets
    from arayuz import tema
    app = _qt()
    onceki = tema.etkin()
    try:
        for ad in ("acik", "koyu"):
            tema.uygula(app, ad)
            t = QtWidgets.QTableWidget(1, 2)
            oge = QtWidgets.QTableWidgetItem("")
            oge.setBackground(QtGui.QColor("#ff0000"))
            t.setItem(0, 0, oge)
            t.resize(300, 120)
            t.show()
            app.processEvents()
            r = t.visualItemRect(oge)
            renk = t.viewport().grab().toImage().pixelColor(r.center()).name()
            kontrol("tablo hucresi BackgroundRole rengi (%s)" % ad, renk == "#ff0000", "-> %s" % renk)
            _sil(t)
    finally:
        tema.uygula(app, onceki)


def test_yazi_tipi():
    print("\n[T5] YAZI: gomulu Inter yuklenir; mono secilir")
    _qt()
    from arayuz.tasarim import yazi
    kontrol("Inter yuklendi", yazi.aile() == "Inter", "-> %s" % yazi.aile())
    kontrol("mono aile bos degil", bool(yazi.mono_aile()), "-> %s" % yazi.mono_aile())
    kontrol("font('baslik') piksel boyutu", yazi.font("baslik").pixelSize() == 17)
    from arayuz import tema
    app = _qt()
    tema.uygula(app, tema.etkin())
    # Mevcut kod f.setPointSizeF(f.pointSizeF() * k) yapar: nokta boyutu olmali.
    nokta = app.font().pointSizeF()
    kontrol("uygulama yazisi nokta boyutlu (eski kodla uyumlu)", 8.0 <= nokta <= 12.0,
            "-> %s" % nokta)
    lisans = os.path.join(yazi.FONT_DIZINI, "LICENSE.txt")
    kontrol("OFL lisansi yaninda", os.path.isfile(lisans)
            and "Open Font License" in open(lisans, encoding="utf-8").read())


# ============================================================================
# 3. ikonlar
# ============================================================================
def _baskin_renk(pm):
    from collections import Counter
    img = pm.toImage()
    sayac = Counter()
    for x in range(img.width()):
        for y in range(img.height()):
            c = img.pixelColor(x, y)
            if c.alpha() > 200:
                sayac[c.name()] += 1
    return sayac.most_common(1)[0][0] if sayac else None


def test_ikonlar():
    print("\n[T6] IKON: her ikon yuklenir ve tema rengine boyanir")
    _qt()
    from arayuz.tasarim import ikon as ik
    adlar = ik.ikon_adlari()
    kontrol("en az 40 ikon", len(adlar) >= 40, "-> %d" % len(adlar))
    bos = [a for a in adlar if ik.ikon(a).isNull()]
    kontrol("hepsi QIcon olarak yuklenir", not bos, "-> %s" % bos)
    boyasiz = [a for a in adlar if _baskin_renk(ik.piksel(a, "#ff0000", 24, 2)) != "#ff0000"]
    kontrol("hepsi istenen renge boyanir", not boyasiz, "-> %s" % boyasiz)
    kontrol("bilinmeyen ikon -> bos QIcon (cokmez)", ik.ikon("yok-boyle-ikon").isNull())
    kontrol("ISC lisansi yaninda", "ISC License" in open(os.path.join(ik.IKON_DIZINI, "LICENSE"),
                                                         encoding="utf-8").read())
    for gerekli in ("play", "square", "save", "folder-open", "search", "atom", "hexagon",
                    "triangle-alert", "circle-check", "sun", "moon", "command", "panel-left"):
        if gerekli not in adlar:
            kontrol("gerekli ikon %s" % gerekli, False)


def test_tema_degisimi_ikon_ve_renk():
    print("\n[T7] TEMA DEGISIMI: renkler ve bagli ikonlar guncellenir")
    from PySide6 import QtWidgets
    from arayuz import tema
    from arayuz.tasarim.ikon import ikon_bagla
    app = _qt()
    onceki = tema.etkin()
    d = QtWidgets.QToolButton()
    try:
        tema.uygula(app, "acik")
        ikon_bagla(d, "save", "metin", 16)
        acik_renk = _baskin_renk(d.icon().pixmap(16, 16))
        sinyaller = []
        tema.sinyal().degisti.connect(sinyaller.append)
        tema.uygula(app, "koyu")
        tema.sinyal().degisti.disconnect(sinyaller.append)
        koyu_renk = _baskin_renk(d.icon().pixmap(16, 16))
        kontrol("tema.renk degisti", tema.renk("metin") == tema.TEMALAR["koyu"]["metin"])
        kontrol("degisti sinyali yayildi", sinyaller == ["koyu"])
        kontrol("bagli ikon koyu tema rengine boyandi",
                acik_renk == tema.TEMALAR["acik"]["metin"] and koyu_renk == tema.TEMALAR["koyu"]["metin"],
                "-> %s / %s" % (acik_renk, koyu_renk))
        tema.uygula(app, "koyu", vurgu="teal")
        kontrol("vurgu secenegi uygulanir", tema.renk("vurgu") == "#3cc7b6"
                and tema.etkin_vurgu() == "teal")
    finally:
        tema.uygula(app, onceki, vurgu="kobalt")
        _sil(d)


# ============================================================================
# 4. bilesenler
# ============================================================================
def _kenar():
    from arayuz.bilesenler import KenarCubugu
    k = KenarCubugu()
    for anahtar, metin, ik in (("malzemeler", "Malzemeler", "flask-conical"),
                               ("parcalar", "Parçalar", "cylinder"),
                               ("demet", "Demet", "grid-3x3"),
                               ("kor", "Kor", "hexagon")):
        k.ekle(anahtar, metin, ik)
    return k


def test_kenar_cubugu():
    print("\n[T8] KENAR CUBUGU: sinyal, gizleme, durum, klavye, daraltma")
    from PySide6 import QtCore
    from PySide6.QtTest import QTest
    _qt()
    k = _kenar()
    k.resize(220, 400)
    k.show()
    gelen = []
    k.secildi.connect(gelen.append)
    k.sec("demet")
    kontrol("sec -> secildi('demet')", gelen == ["demet"] and k.secili() == "demet")
    k.sec("demet")
    kontrol("ayni oge tekrar secilince sinyal yinelenmez", gelen == ["demet"])
    k.durum_ayarla("kor", "hata")
    kontrol("durum okunur", k.durum("kor") == "hata" and k.durum("demet") is None)
    k.gorunur_yap("parcalar", False)
    kontrol("gizlenen oge gorunmez", not k.gorunur_mu("parcalar") and k.gorunur_mu("kor"))
    k.sec("malzemeler")
    k.liste.setFocus()
    QTest.keyClick(k.liste, QtCore.Qt.Key_Down)
    kontrol("asagi ok gizli ogeyi atlar", k.secili() == "demet", "-> %s" % k.secili())
    QTest.keyClick(k.liste, QtCore.Qt.Key_Down)
    kontrol("asagi ok -> kor", k.secili() == "kor")
    kontrol("gizli ogeye sec() yapilmaz", not k.sec("parcalar") and k.secili() == "kor")
    genis = k.sizeHint().width()
    k.daralt(True)
    kontrol("daraltinca dar", k.dar_mi() and k.sizeHint().width() < genis)
    kontrol("dar modda ipucu metni", k.liste.item(0).toolTip() == "Malzemeler")
    kontrol("erisilebilir ad", bool(k.liste.accessibleName()))
    k.daralt(False)
    kontrol("anahtarlar sirali", k.anahtarlar() == ["malzemeler", "parcalar", "demet", "kor"])
    _sil(k)


def test_komut_paleti():
    print("\n[T9] KOMUT PALETI: bulanik arama, oklar, Enter, Esc")
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtTest import QTest
    from arayuz.bilesenler import KomutPaleti, bulanik_puan
    _qt()
    kontrol("bulanik: 'clstr' Çalıştır'a uyar", bulanik_puan("clstr", "Çalıştır") is not None)
    kontrol("bulanik: sira bozuksa uymaz", bulanik_puan("rtsil", "Çalıştır") is None)
    kontrol("bulanik: bitisik/onek daha yuksek",
            bulanik_puan("kay", "Kaydet") > bulanik_puan("kay", "Farklı kaydet… (k-a-y)"))
    p = QtWidgets.QMainWindow()
    p.resize(900, 600)
    calisan = []
    eylemler = []
    for metin in ("Kaydet", "Farklı kaydet…", "Çalıştır", "Koyu tema"):
        e = QtGui.QAction(metin, p)
        e.triggered.connect(lambda _=False, m=metin: calisan.append(m))
        eylemler.append(e)
    pal = KomutPaleti(p, eylemler)
    p.show()
    p.activateWindow()
    QTest.qWaitForWindowActive(p, 1000)
    QTest.keyClick(p, QtCore.Qt.Key_K, QtCore.Qt.ControlModifier)
    kontrol("Ctrl+K paleti acar", pal.isVisible())
    QTest.keyClicks(pal.arama, "calis")
    kontrol("arama: tek sonuc Çalıştır", pal.sonuclar() == ["Çalıştır"], "-> %s" % pal.sonuclar())
    QTest.keyClick(pal.arama, QtCore.Qt.Key_Return)
    kontrol("Enter eylemi calistirir ve kapanir", calisan == ["Çalıştır"] and not pal.isVisible())
    pal.ac()
    kontrol("yeniden acinca arama bos, hepsi listede", pal.arama.text() == "" and len(pal.sonuclar()) == 4)
    QTest.keyClicks(pal.arama, "kay")
    QTest.keyClick(pal.arama, QtCore.Qt.Key_Down)
    QTest.keyClick(pal.arama, QtCore.Qt.Key_Enter)
    kontrol("asagi ok ikinci sonucu secer", calisan[-1] == "Farklı kaydet…", "-> %s" % calisan)
    pal.ac()
    QTest.keyClick(pal.arama, QtCore.Qt.Key_Escape)
    kontrol("Esc kapatir, eylem calismaz", not pal.isVisible() and len(calisan) == 2)
    _sil(p)


def _bekle(kosul, en_cok_ms):
    """kosul() dogru olana ya da sure dolana dek olay dongusunu dondurur."""
    from PySide6.QtTest import QTest
    for _i in range(en_cok_ms // 20):
        if kosul():
            return True
        QTest.qWait(20)
    return kosul()


def test_bildirim():
    print("\n[T10] BILDIRIM: sag altta, yigilir, kendiliginden kapanir")
    from PySide6 import QtWidgets
    from arayuz.bilesenler import Bildirim, bildir
    _qt()
    p = QtWidgets.QMainWindow()
    p.resize(800, 600)
    p.show()
    # Zamanlama yuk altinda (xdist) kayar: sure uzun tutulur, bekleme _bekle ile.
    b1 = bildir(p, "Kaydedildi", "basari", 600)
    b2 = bildir(p, "Doğrulama: 2 uyarı", "uyari", 0)
    kontrol("iki bildirim gorunur", b1.isVisible() and b2.isVisible())
    kontrol("sag altta", b1.geometry().right() > 700 and b1.geometry().bottom() > 500)
    kontrol("yigilir (ust uste binmez)", not b1.geometry().intersects(b2.geometry()))
    kontrol("erisilebilir ad = metin", "Kaydedildi" in b1.accessibleName())
    kontrol("durum cubugu olmayan pencereye durum cubugu eklenmez",
            p.findChild(QtWidgets.QStatusBar) is None)
    from arayuz.bilesenler.bildirim import ALT_PAYI_OZELLIGI, yeniden_diz
    alt_once = b2.geometry().bottom()
    p.setProperty(ALT_PAYI_OZELLIGI, 30)
    yeniden_diz(p)
    kontrol("alt payi kadar yukari alinir", b2.geometry().bottom() == alt_once - 30,
            "-> %d / %d" % (b2.geometry().bottom(), alt_once))

    def _acik():
        return [b for b in p.findChildren(Bildirim) if b.isVisible()]
    _bekle(lambda: len(_acik()) == 1, 5000)
    kalan = _acik()
    kontrol("sure dolunca kapanir; sure=0 kalir", kalan == [b2], "-> %d" % len(kalan))
    b2.kapat()
    _bekle(lambda: not _acik(), 2000)
    kontrol("kapat() ile kapanir", not _acik())
    _sil(p)


def test_form_bilesenleri():
    print("\n[T11] SAYI+BIRIM, SEGMENT, ROZET, KART, BOS DURUM, DUGMELER")
    from PySide6 import QtCore
    from arayuz import bilesenler as b
    from arayuz.tasarim import stil
    _qt()
    s = b.SayiBirim(birim="cm", deger=1.26, ondalik=4)
    kontrol("SayiBirim: ondalik NOKTA", "1.2600" in s.kutu.text(), "-> %s" % s.kutu.text())
    kontrol("SayiBirim: birim etiketi", s.birim() == "cm")
    s2 = b.SayiBirim(birimler={"cm": 1.0, "mm": 0.1}, deger=1.0, ondalik=3)
    gelen = []
    s2.degisti.connect(gelen.append)
    s2.birim_ayarla("mm")
    kontrol("SayiBirim: birim degisince gosterilen deger donusur, taban deger ayni",
            abs(s2.kutu.value() - 10.0) < 1e-9 and abs(s2.deger() - 1.0) < 1e-9)
    s2.kutu.setValue(25.0)
    kontrol("SayiBirim: deger() taban birimde", abs(s2.deger() - 2.5) < 1e-9 and gelen[-1] == 2.5)
    stil.durum_ayarla(s2.kutu, "hata", True)
    kontrol("hata ozelligi", s2.kutu.property("hata") is True)
    seg = b.SegmentSecici([("hizli", "Hızlı"), ("dengeli", "Dengeli"), ("hassas", "Hassas")], "dengeli")
    secim = []
    seg.secildi.connect(secim.append)
    seg.dugme("hassas").click()
    kontrol("SegmentSecici tek secim + sinyal", seg.secili() == "hassas" and secim == ["hassas"])
    kontrol("segment ozellikleri bas/orta/son",
            [seg.dugme(a).property("segment") for a in ("hizli", "dengeli", "hassas")]
            == ["bas", "orta", "son"])
    r = b.Rozet("Hata yok", "basari")
    r.tur_ayarla("hata")
    kontrol("Rozet tur degisir", r.property("rozet") == "hata")
    k = b.Kart("Parçacık", aciklama="Çevrim başına", eylem=b.duz_dugme("Sıfırla"))
    k.ekle(s)
    kontrol("Kart baslik + govde", k.baslik_etiketi.text() == "Parçacık" and k.govde.count() == 1)
    bos = b.BosDurum("chart-line", "Henüz sonuç yok", "Çalıştırın.", "Çalıştır")
    istek = []
    bos.eylem_istendi.connect(lambda: istek.append(1))
    bos.dugme.click()
    kontrol("BosDurum eylemi", istek == [1])
    d = b.ikon_dugmesi("save", "Kaydet")
    kontrol("ikon dugmesi erisilebilir ad + ipucu",
            d.accessibleName() == "Kaydet" and d.toolTip() == "Kaydet" and not d.icon().isNull())
    kontrol("birincil dugme objectName", b.birincil_dugme("Çalıştır", "play").objectName() == "birincil")
    kontrol("tehlikeli dugme ozelligi", b.tehlikeli_dugme("Sil").property("tur") == "tehlikeli")
    kontrol("odak politikasi (klavye)", d.focusPolicy() & QtCore.Qt.TabFocus)
    _sil(s, s2, seg, r, k, bos, d)


# ----------------------------------------------------------------------------
# Inceleme bulgulari (Dalga 1): sessiz dusmeler loglanir, API geri bildirim verir
# ----------------------------------------------------------------------------
class _Toplayici(__import__("logging").Handler):
    def __init__(self):
        import logging
        super().__init__(logging.DEBUG)
        self.kayitlar = []

    def emit(self, kayit):
        self.kayitlar.append(kayit.getMessage())


def _loglarken(ad, fn):
    import logging
    kay = logging.getLogger(ad)
    top = _Toplayici()
    eski = kay.level
    kay.addHandler(top)
    kay.setLevel(logging.DEBUG)
    try:
        sonuc = fn()
    finally:
        kay.removeHandler(top)
        kay.setLevel(eski)
    return sonuc, top.kayitlar


def test_bilinmeyen_tema_loglanir():
    print("\n[T14] TEMA: bilinmeyen tema/vurgu adi varsayilana duser ve LOGLANIR")
    from arayuz import tema
    app = _qt()
    once = (tema.etkin(), tema.etkin_vurgu())
    try:
        _s, kayit = _loglarken("openmc_arayuz.arayuz.tema",
                               lambda: tema.uygula(app, "boyle_tema_yok", "boyle_vurgu_yok"))
        kontrol("bilinmeyen tema -> acik", tema.etkin() == "acik")
        kontrol("bilinmeyen tema loglandi", any("boyle_tema_yok" in k for k in kayit),
                "-> %s" % kayit)
        kontrol("bilinmeyen vurgu loglandi", any("boyle_vurgu_yok" in k for k in kayit),
                "-> %s" % kayit)
    finally:
        tema.uygula(app, *once)


def test_segment_bilinmeyen_anahtar():
    print("\n[T15] SEGMENT: bilinmeyen anahtar False doner ve loglanir")
    from arayuz.bilesenler import SegmentSecici
    _qt()
    s = SegmentSecici([("a", "A"), ("b", "B")], secili="a")
    try:
        sonuc, kayit = _loglarken("openmc_arayuz.arayuz.bilesenler.segment",
                                  lambda: s.sec("yok"))
        kontrol("bilinmeyen anahtar -> False, secim degismedi",
                sonuc is False and s.secili() == "a", "-> %r %r" % (sonuc, s.secili()))
        kontrol("bilinmeyen anahtar loglandi", any("yok" in k for k in kayit), "-> %s" % kayit)
        kontrol("bilinen anahtar -> True", s.sec("b") is True and s.secili() == "b")
        kontrol("zaten secili -> True (hata degil)", s.sec("b") is True)
    finally:
        _sil(s)


def test_bildir_pencere_yok():
    print("\n[T16] BILDIRIM: pencere None -> acik ValueError")
    from arayuz.bilesenler import bildir
    _qt()
    try:
        bildir(None, "x")
        kontrol("pencere None reddedildi", False, "-> istisna yok")
    except ValueError as e:
        kontrol("pencere None reddedildi", "pencere" in str(e), "-> %s" % e)


def test_stil_resmi_uretilemezse():
    print("\n[T17] STIL: ikon resmi uretilemezse QSS yine uretilir ve LOGLANIR")
    from arayuz.tasarim import ikon, stil, tokenlar
    _qt()
    asil = ikon.piksel

    def bozuk(*_a, **_k):
        raise ValueError("bozuk svg (test)")
    ikon.piksel = bozuk
    try:
        import tempfile
        eski_dizin = stil._resim_dizini
        gecici = tempfile.mkdtemp(prefix="stil_test_")
        stil._resim_dizini = lambda: gecici     # onbellekteki eski PNG kullanilmasin
        try:
            qss, kayit = _loglarken("openmc_arayuz.arayuz.tasarim.stil",
                                    lambda: stil.uret(tokenlar.palet("acik")))
        finally:
            stil._resim_dizini = eski_dizin
        kontrol("QSS yine uretildi", isinstance(qss, str) and "QPushButton" in qss)
        kontrol("resim hatasi loglandi", any("bozuk svg" in k or "chevron" in k for k in kayit),
                "-> %s" % kayit)
    finally:
        ikon.piksel = asil


def test_bildirim_uzun_metin_kirpilmaz():
    print("\n[T10b] BILDIRIM: uzun (sarilan) metin kirpilmaz -- acilis bildirimi")
    from PySide6 import QtWidgets
    from arayuz import tema
    from arayuz.bilesenler import bildir
    uyg = _qt()
    tema.uygula(uyg)          # tema yazi tipi/dolgusu olmadan hata gorunmuyordu
    p = QtWidgets.QMainWindow()
    p.resize(1280, 800)
    p.show()
    metinler = ("Örnek kopya olarak açıldı: sfr_met1000_kor.json — kaydetmek için "
                "'Farklı kaydet' kullanın (örnek dosyası değişmez)",
                "Kısa", "Açıldı: " + "/cok/uzun/bir/yol" * 6 + " dosya.json " * 4)
    kirpik = []
    for m in metinler:
        b = bildir(p, m, "bilgi", 0)
        e = b.etiket
        gerek = e.heightForWidth(e.width())
        if e.height() < gerek or not b.rect().contains(e.geometry()):
            kirpik.append((m[:30], e.height(), gerek))
        b.kapat()
    kontrol("etiket yuksekligi sarilan metne yetiyor (heightForWidth)", not kirpik,
            "-> %s" % kirpik)
    _sil(p)


HIZLI = [test_kontrast_wcag, test_token_olcekleri, test_tema_eski_anahtarlar, test_qss_uyarisiz,
         test_eski_ekran_uyumu,
         test_yazi_tipi, test_ikonlar, test_tema_degisimi_ikon_ve_renk, test_kenar_cubugu,
         test_komut_paleti, test_bildirim, test_bildirim_uzun_metin_kirpilmaz,
         test_form_bilesenleri,
         test_bilinmeyen_tema_loglanir, test_segment_bilinmeyen_anahtar,
         test_bildir_pencere_yok, test_stil_resmi_uretilemezse]
YAVAS = []


if __name__ == "__main__":
    from testler.ortak_test import _gecti, _kaldi
    for fn in HIZLI:
        fn()
    print("\nGECTI %d  KALDI %d" % (len(_gecti), len(_kaldi)))
