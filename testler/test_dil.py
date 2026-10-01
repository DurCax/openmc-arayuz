# -*- coding: utf-8 -*-
"""
test_dil.py -- Dalga 4 dil ve terim: kullaniciya GORUNEN metinler tek dilde
(gercek Turkce karakterli), ham deger ve virgullu ondalik icermez.

Taranan metinler (11 ornekle kurulan ana pencere, her sekme acilarak):
  QLabel / QAbstractButton / QGroupBox / QTabBar / QComboBox ogeleri /
  QTableWidget basliklari / QListWidget ogeleri / menu eylemleri /
  yer tutucular ve butun ipuclari; ayrica Yardim sayfasi, baslangic ekrani
  ve bozuk modellerden uretilen dogrulama bulgulari (mesaj + oneri).

Kontroller
  (a) ASCII'lestirilmis Turkce kelime yok (liste Dalga 4 envanterinden
      turetildi: "kosu", "yukseklik", "gecerli", "sicaklik", "cubuk"...).
  (b) Ham kaliplar yok: "None", " -- ", Python liste repr'i ("['"),
      0'dan numaralandirma ("0. bolge").
  (c) Gorunen sayilarda virgullu ondalik yok ("21,42").

Kullanici verisi (malzeme/parca adlari: "yakit_cubugu", "demet_17x17") ve
OpenMC'ye giden dizgiler ("kappa-fission") denetlenmez: kelimeler \\b ile
aranir, alt cizgili adlar tek kelime sayilir.
"""

import copy
import glob
import os
import re
import warnings

from testler.ortak_test import kontrol, KOK, ORNEK   # noqa: F401
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik

warnings.filterwarnings("ignore")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# ----------------------------------------------------------------------------
# (a) ASCII'lestirilmis Turkce kelimeler -- Dalga 4 envanterinde gercekten
# goruldu. Kelime sinirli ve buyuk/kucuk harf duyarsiz aranir.
# ----------------------------------------------------------------------------
ASCII_TURKCE = (
    # kosu / hesap
    "kosu", "kosusu", "kosun", "kosunun", "calistir", "calistirma", "calistirilamaz",
    "basarisiz", "basladi", "baslat", "baslatilamaz", "tamamlandi", "durduruldu",
    "ozdeger", "cevrim", "cevrimler", "parcacik", "sayisi", "yakinsama",
    "yakinsamamis", "yakinsamis", "degerlendirilemedi", "sonuc", "sonuclar",
    "sonuclari", "okunamadi", "kurulamadi", "hesaplanamadi", "bulunamadi",
    "tanimsiz", "tanimli", "gecerli", "gecersiz", "secilmemis", "secin", "secilmeli",
    "olmali", "degil", "icin", "uzerinden", "yalnizca", "hicbir", "dogrulama",
    "dogrulanamiyor", "ayni", "onceki", "boyle", "gore",
    # geometri
    "cubuk", "cubugu", "cubugun", "cubuklar", "bolge", "bolgenin", "bolgesi",
    "yaricap", "yaricapi", "yaricaplar", "yukseklik", "yuksekligi", "adim",
    "adimi", "adimlar", "kalinlik", "kalinligi", "genislik", "satir", "sutun",
    "haritasi", "yansitici", "kusak", "kusagi", "donme",
    "donmesi", "dis", "ic", "icinde", "disinda", "kure", "kuresel", "sinir",
    "sinirlar", "kosulu", "sizinti", "altigen", "hucre", "hucresi",
    # malzeme / fizik
    "sicaklik", "sicakligi", "yogunluk", "yogunlugu", "bilesim", "bilesen",
    "zenginligi", "nuklid", "nuklidler", "sogutucu", "sogurucu",
    "moderator", "yakit", "agir", "dogal", "bosluk", "kutuphane", "kutuphanesi",
    "sacilma", "tukenme", "tukenmeyi", "guc", "gucu", "yogunlugu", "bagil",
    "sicak", "katsayi", "katsayisi", "egim", "reaktor", "notron", "cozunmus",
    "tayfi", "acisal", "dagilim", "dagilimi", "siddet", "siddeti",
    "gun", "hazir",
)
# re.IGNORECASE KULLANILMAZ: Python'da "i" buyuk/kucuk harf duyarsiz aramada
# "ı" ve "İ" ile de eslesir ("olmalı" -> "olmali" diye yakalanirdi). Bunun
# yerine her kelimenin kucuk, Bas-harfi-buyuk ve BUYUK yazimlari aranir.
_ASCII_DESEN = re.compile(r"(?<!\w)(%s)(?!\w)" % "|".join(
    sorted({v for w in ASCII_TURKCE for v in (w, w.capitalize(), w.upper())},
           key=len, reverse=True)))

# (b) ham kaliplar
_HAM_DESENLER = [
    ("None", re.compile(r"\bNone\b")),
    ("' -- '", re.compile(r"(^|\s)--(\s|$)")),
    ("Python liste repr'i", re.compile(r"\[\s*('|⟨kimlik⟩)")),
    ("0'dan numara", re.compile(r"(?<![\d.,])0\.\s+(bölge|katman|halka|adım|tambur|satır)")),
    ("büyük harfle bağırma", re.compile(r"(?<!\w)(DIKKAT|DİKKAT|ONCE|ÖNCE|YANLIŞ|YANLI|UYARI:|NOT:|"
                                        r"BOZUK|BAŞARISIZ|KESİN|SESSİZCE|ANALİTİK|AIT|ESKI|DEGIL|SONUC|KOSU|BILGI|"
                                        r"OZDEGER|TUKENME)(?!\w)")),
]

# (c) virgullu ondalik: rakam,rakam (liste "0.5, 1.5" bosluklu oldugu icin tutmaz)
_VIRGUL_ONDALIK = re.compile(r"\d,\d")


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _html_duz(metin):
    """HTML etiketlerini ve varliklarini ayiklar (stil nitelikleri taranmaz)."""
    metin = re.sub(r"<style.*?</style>", " ", metin, flags=re.S)
    metin = re.sub(r"<[^>]+>", " ", metin)
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " ")):
        metin = metin.replace(a, b)
    return metin


def widget_metinleri(kok):
    """Bir widget agacindaki kullaniciya gorunen butun metinler: [(nereden, metin)]."""
    from PySide6 import QtWidgets
    out = []

    def ekle(nereden, metin):
        if metin and str(metin).strip():
            out.append((nereden, _html_duz(str(metin))))

    ogeler = [kok] + kok.findChildren(QtWidgets.QWidget)
    for w in ogeler:
        ad = type(w).__name__
        ekle(ad + ".toolTip", w.toolTip())
        if w.isWindow():
            ekle(ad + ".windowTitle", w.windowTitle())
        if isinstance(w, QtWidgets.QLabel):
            ekle("QLabel", w.text())
        elif isinstance(w, QtWidgets.QAbstractButton):
            ekle(ad, w.text())
        elif isinstance(w, QtWidgets.QGroupBox):
            ekle("QGroupBox", w.title())
        elif isinstance(w, QtWidgets.QComboBox):
            for i in range(w.count()):
                ekle("QComboBox", w.itemText(i))
                ekle("QComboBox.toolTip", w.itemData(i, 3))       # Qt.ToolTipRole
        elif isinstance(w, QtWidgets.QLineEdit):
            ekle("QLineEdit.placeholder", w.placeholderText())
        elif isinstance(w, QtWidgets.QTabBar):
            for i in range(w.count()):
                ekle("QTabBar", w.tabText(i))
                ekle("QTabBar.toolTip", w.tabToolTip(i))
        elif isinstance(w, QtWidgets.QTableWidget):
            for i in range(w.columnCount()):
                it = w.horizontalHeaderItem(i)
                ekle("QTableWidget.baslik", it.text() if it else "")
        elif isinstance(w, QtWidgets.QListWidget):
            for i in range(w.count()):
                ekle("QListWidget", w.item(i).text())
                ekle("QListWidget.toolTip", w.item(i).toolTip())
        elif isinstance(w, QtWidgets.QAbstractSpinBox):
            ekle(ad + ".specialValue", w.specialValueText())
        elif isinstance(w, QtWidgets.QProgressBar):
            ekle("QProgressBar", w.format())
    for eylem in kok.findChildren(__import__("PySide6").QtGui.QAction):
        ekle("QAction", eylem.text().replace("&", ""))
        ekle("QAction.toolTip", eylem.toolTip())
    return out


def _pencere(dosya=None):
    from arayuz.ana_pencere import AnaPencere
    p = AnaPencere(dosya)
    p._kaydetme_sor = lambda: True
    return p


def _kapat(p):
    from PySide6 import QtCore
    try:
        p.s_tukenme.bekle()
        p._kirli = False
        p.close()
        p.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    except Exception:
        pass


def ornek_metinleri():
    """11 ornekle kurulan pencerelerin her sekmesindeki metinler: [(yer, metin)]."""
    from PySide6 import QtWidgets
    uyg = _qt()
    hepsi = []
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        ad = os.path.splitext(os.path.basename(yol))[0]
        p = _pencere(yol)
        p.s_tukenme.bekle()
        for anahtar in p.sekme_anahtarlari():
            if not p.sekme_gorunur_mu(anahtar):
                continue
            p.sekmeye_git(anahtar, sessiz=True)
            uyg.processEvents()
        p.s_tukenme.bekle()
        uyg.processEvents()
        hepsi += [("%s/%s" % (ad, n), m) for n, m in widget_metinleri(p)]
        _kapat(p)
    # baslangic ekrani ve Yardim
    p = _pencere()
    hepsi += [("baslangic/" + n, m) for n, m in widget_metinleri(p.baslangic)]
    y = p._yardim_diyalogu()
    hepsi += [("yardim/" + n, m) for n, m in widget_metinleri(y)]
    for w in y.findChildren(QtWidgets.QTextBrowser):
        hepsi.append(("yardim/QTextBrowser", w.toPlainText()))
    _kapat(p)
    return hepsi


def _bozuk_modeller():
    """Bircok dogrulama bulgusunu tetikleyen bozuk model kopyalari."""
    from cekirdek import sema

    def y(ad):
        return sema.yukle(os.path.join(ORNEK, ad + ".json"))

    cikti = []

    def ekle(ad, taban, degistir):
        s = copy.deepcopy(taban)
        degistir(s)
        cikti.append((ad, s))

    pin, p3b, kon = y("pwr_pinhucre"), y("pwr_3b"), y("pwr_kontrol")
    tam, zirh, tuk, eks = y("tamburlu_kor"), y("zirh_kure"), y("pwr_tukenme"), y("pwr_eksenel")
    ekle("sab yok", pin, lambda s: [m.update(sab=[]) for m in s["malzemeler"] if m["ad"] == "su"])
    ekle("yogunluk yok", pin, lambda s: s["malzemeler"][0]["yogunluk"].update(deger=None))
    ekle("yaricap sirasi", pin, lambda s: s["cubuklar"][0]["bolgeler"].__setitem__(
        0, sema.bolge(0.9, "uo2")))
    ekle("son bolge", pin, lambda s: s["cubuklar"][0]["bolgeler"].__setitem__(
        2, sema.bolge(0.8, "su")))
    ekle("adim kucuk", pin, lambda s: s["kor"].update(adim=0.5))
    ekle("sinir", pin, lambda s: s["kor"]["sinir"].update(yan="vacuum", alt="vacuum"))
    ekle("zenginlik", pin, lambda s: s["malzemeler"][0]["bilesim"][0].update(zenginlik=150.0))
    ekle("pasif", pin, lambda s: s["ayarlar"].update(pasif=2, cevrim=10, parcacik=100))
    ekle("entropi", pin, lambda s: s["ayarlar"]["entropi_mesh"].update(var=False))
    ekle("guc bolge", p3b, lambda s: s["guc_dagilimi"].update(var=True, bolge=2,
                                                            eksenel_dilim=3, skor="fission"))
    ekle("guc 2B", p3b, lambda s: (s["guc_dagilimi"].update(var=True, toplam_guc=1e6),
                                   s["kor"].update(yukseklik=None)))
    ekle("kontrol", kon, lambda s: sema.cubuk_bul(s, "kontrol_cubugu").update(
        daldirma=150.0, emici_bolge=9, izleyici_malzeme=None))
    ekle("tambur", tam, lambda s: s["kor"]["tambur"].update(sayi=40, donme=720.0))
    ekle("sabit kaynak", zirh, lambda s: (s.update(tallyler=[]),
                                          s["ayarlar"].update(pasif=10),
                                          s["ayarlar"]["kaynak"].update(tur="kutu")))
    ekle("ozdeger zirh", zirh, lambda s: s["ayarlar"].update(mod="eigenvalue"))
    ekle("periodic", p3b, lambda s: s["kor"]["sinir"].update(alt="periodic", ust="vacuum"))
    ekle("tukenme", tuk, lambda s: s["tukenme"].update(guc_yogunlugu=1000.0,
                                                      adimlar=[10.0], zincir="hizli"))
    ekle("eksenel", eks, lambda s: s["kor"]["eksenel"]["bolgeler"][0].update(
        dolgu="yok_boyle", yukseklik=0.0))
    ekle("kuresel yukseklik", zirh, lambda s: s["kor"].update(yukseklik=10.0))
    return cikti


def bulgu_metinleri():
    from cekirdek import dogrula
    from arayuz.ana_pencere import yer_etiketi
    out = []
    for ad, s in _bozuk_modeller():
        for b in dogrula.tum_kontroller(s, veri_kontrolu=False):
            out.append(("bulgu:%s" % ad, "%s — %s" % (yer_etiketi(b.yer), b.mesaj)))
            if b.oneri:
                out.append(("oneri:%s" % ad, b.oneri))
    return out


def kullanici_verileri():
    """
    Orneklerdeki kullanici verisi DENETLENMEZ (GOREV: malzemelerin
    "gorunen_ad"i OpenMC malzeme adi olur ve tukenme sonucunun eskime
    karsilastirmasina girer; katman adlari hucre adina gider). Metinden
    maskelenirler. Tam metni bir veri olan ogeler (kosu dizini "kosu")
    yalnizca TAM eslesmede atlanir; dosya yollari da maskelenir.
    """
    import json
    parcali, tam = set(), set()
    for yol in glob.glob(os.path.join(ORNEK, "*.json")):
        with open(yol, encoding="utf-8") as f:
            sp = json.load(f)
        for m in sp.get("malzemeler") or []:
            if m.get("gorunen_ad"):
                parcali.add(m["gorunen_ad"])
        for b in ((sp.get("kor") or {}).get("eksenel") or {}).get("bolgeler") or []:
            if b.get("ad"):
                parcali.add(b["ad"])
        tam.add(((sp.get("calistirma") or {}).get("dizin")) or "kosu")
    return sorted(parcali, key=len, reverse=True), tam


def _denetle(metinler):
    """(ascii, ham, virgul) ihlal listeleri."""
    ascii_, ham, virgul = [], [], []
    parcali, tam = kullanici_verileri()
    temiz = []
    for yer, m in metinler:
        if m.strip() in tam:
            continue
        for v in parcali:
            m = m.replace(v, "⟨veri⟩")
        m = re.sub(r"(?<!\w)/\S*", "⟨yol⟩", m)
        m = re.sub(r"'[a-z0-9_]+'", "⟨kimlik⟩", m)      # 'bosluk' gibi ayrilmis adlar
        temiz.append((yer, m))
    for yer, m in temiz:
        for satir in m.split("\n"):
            x = _ASCII_DESEN.search(satir)
            if x:
                ascii_.append((yer, x.group(0), satir.strip()[:90]))
            for ad, d in _HAM_DESENLER:
                if d.search(satir):
                    ham.append((yer, ad, satir.strip()[:90]))
            if _VIRGUL_ONDALIK.search(satir):
                virgul.append((yer, satir.strip()[:90]))
    return ascii_, ham, virgul


def test_arayuz_metinleri(gecici=None):
    print("\n[D1] DIL: 11 ornekle kurulan pencerenin gorunen metinleri")
    metinler = ornek_metinleri()
    ascii_, ham, virgul = _denetle(metinler)
    kontrol("taranan metin sayisi anlamli (%d)" % len(metinler), len(metinler) > 3000)
    kontrol("(a) ASCII'lestirilmis Turkce kelime yok", not ascii_, "-> %s" % ascii_[:5])
    kontrol("(b) ham kalip yok (None, --, liste repr, 0. numara, BAGIRMA)", not ham,
            "-> %s" % ham[:5])
    kontrol("(c) virgullu ondalik yok", not virgul, "-> %s" % virgul[:5])


@gereksinim("R-M9-02")
def test_bulgu_metinleri():
    print("\n[D2] DIL: dogrulama bulgulari (bozuk modeller)")
    metinler = bulgu_metinleri()
    ascii_, ham, virgul = _denetle(metinler)
    kontrol("bozuk modeller bircok bulgu uretiyor (%d)" % len(metinler), len(metinler) > 60)
    kontrol("(a) bulgularda ASCII'lestirilmis Turkce yok", not ascii_, "-> %s" % ascii_[:5])
    kontrol("(b) bulgularda ham kalip yok", not ham, "-> %s" % ham[:5])
    kontrol("(c) bulgularda virgullu ondalik yok", not virgul, "-> %s" % virgul[:5])
    from cekirdek import dogrula
    kontrol("bulgu yer kodu okunur ada cevriliyor",
            __import__("arayuz.ana_pencere", fromlist=["x"]).yer_etiketi("malzeme:uo2")
            == "Malzeme uo2"
            and __import__("arayuz.ana_pencere", fromlist=["x"]).yer_etiketi(
                "kor/katman 2 (su)") == "Kor, katman 2 (su)")
    kontrol("ozet Turkce", dogrula.ozet([]) == "0 hata, 0 uyarı, 0 bilgi")


def test_cekirdek_yorumlari():
    print("\n[D3] DIL: cekirdek yorum metinleri (keff, entropi, tarama, guc)")
    from cekirdek import kosucu, tarama, guc, tukenme, kaynak
    metinler = []
    for k, s, b in ((1.05, 0.001, 0.0065), (0.95, 0.001, None), (1.0001, 0.001, 0.0065),
                    (1.2, 0.001, 0.0065)):
        metinler += list(kosucu.keff_yorumu(k, s, b))
    metinler.append(kosucu.entropi_yakinsama([1.0] * 5 + [2.0] * 5 + [3.0] * 20, 10)[1])
    metinler.append(kosucu.entropi_yakinsama([1.0, 1.1] * 20, 2)[1])
    metinler.append(kosucu.lambda_metni(2e-5, 1e-7))
    for tur in tarama.TURLER:
        metinler.append(tarama.TURLER[tur][0])
        metinler.append(tarama.yorumla(tur, {"egim": -3.0, "egim_sapma": 0.1}))
    metinler.append(tarama.yorumla("bor_ppm", {"egim": -0.1, "egim_sapma": 1.0}))
    f = {"F_dH": 1.7, "F_q": 2.7, "eksenel_dilim": 5, "yanlilik_orani": 0.5,
         "istatistik_sapma": 0.04, "sacilma": 0.06, "sicak_cubuk": (3, 4),
         "kafes_turu": "kare", "F_dH_sapma": 0.01, "F_q_sapma": 0.02, "cubuk_sayisi": 264}
    metinler += guc.yorumla(f, {"cubuk_ortalama_W": 1.0, "cubuk_maks_W": 2.0,
                                "lineer_maks_W_cm": 600.0, "lineer_tepe_kaynagi": "F_q"})
    metinler.append(guc.ozet_metni(f))
    metinler.append(guc.konum_metni((0, 0), "altigen"))
    metinler.append(tukenme.fark_metni(["malzemeler", "ayarlar", "guc_dagilimi"]))
    metinler.append(kaynak.ozet({"parcacik": "neutron"}))
    ascii_, ham, virgul = _denetle([("cekirdek", m) for m in metinler])
    kontrol("(a) cekirdek yorumlarinda ASCII'lestirilmis Turkce yok", not ascii_,
            "-> %s" % ascii_[:5])
    kontrol("(b) cekirdek yorumlarinda ham kalip yok", not ham, "-> %s" % ham[:5])
    kontrol("(c) cekirdek yorumlarinda virgullu ondalik yok", not virgul, "-> %s" % virgul[:5])
    kontrol("sicak cubuk konumu 1'den numarali", guc.konum_metni((0, 0), "kare") == "x = 1, y = 1")
    kontrol("tukenme farklari okunur", tukenme.fark_metni(["ayarlar"]) == "hesap ayarları")


def test_ornek_basliklari():
    print("\n[D4] DIL: orneklerin ad/aciklama alanlari Turkce, kimlikler ASCII")
    import json
    kotu, kimlik = [], []
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        with open(yol, encoding="utf-8") as f:
            s = json.load(f)
        for alan in ("ad", "aciklama"):
            ascii_, ham, virgul = _denetle([(os.path.basename(yol), s.get(alan) or "")])
            kotu += ascii_ + ham + virgul
        # (tally adlari zaten Turkce karakterli olabilir: "akı_gruplu")
        for bolum in ("malzemeler", "cubuklar", "plakalar", "demetler"):
            for x in s.get(bolum) or []:
                if not re.fullmatch(r"[A-Za-z0-9_\-]+", str(x.get("ad", ""))):
                    kimlik.append((os.path.basename(yol), x.get("ad")))
    kontrol("ornek ad/aciklama Turkce ve temiz", not kotu, "-> %s" % kotu[:5])
    kontrol("malzeme/parca/demet/tally kimlikleri ASCII kaldi", not kimlik, "-> %s" % kimlik[:5])


def test_qt_standart_metinleri():
    print("\n[D5] DIL: Qt'nin standart dugme metinleri Turkce")
    from PySide6 import QtCore, QtWidgets
    from arayuz.ortak import qt_turkce_cevirisi
    uyg = _qt()
    ceviri = qt_turkce_cevirisi(uyg)
    try:
        kontrol("qtbase_tr cevirisi yuklendi", ceviri is not None)
        kutu = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close
                                          | QtWidgets.QDialogButtonBox.Yes
                                          | QtWidgets.QDialogButtonBox.No
                                          | QtWidgets.QDialogButtonBox.Cancel)
        metinler = sorted(b.text().replace("&", "") for b in kutu.buttons())
        kontrol("standart dugmeler Turkce (Kapat/Evet/Hayir/Iptal)",
                metinler == sorted(["Kapat", "Evet", "Hayır", "İptal"]), "-> %s" % metinler)
    finally:
        if ceviri is not None:
            uyg.removeTranslator(ceviri)
    # Yardim diyalogunun dugmesi ceviriden bagimsiz Turkce
    p = _pencere()
    d = p._yardim_diyalogu()
    dugmeler = [b.text() for b in d.findChildren(QtWidgets.QPushButton)]
    kontrol("Yardim diyalogunda 'Kapat' (Close degil)", dugmeler == ["Kapat"], "-> %s" % dugmeler)
    _kapat(p)
    kontrol("sayi kutulari icin C yerel ayari main()'de kuruluyor",
            "QLocale.setDefault(QtCore.QLocale.c())" in open(
                os.path.join(KOK, "arayuz", "ana_pencere.py"), encoding="utf-8").read())


HIZLI = [test_qt_standart_metinleri, test_bulgu_metinleri, test_cekirdek_yorumlari,
         test_ornek_basliklari]
YAVAS = [test_arayuz_metinleri]


if __name__ == "__main__":
    from testler import ortak_test
    for fn in HIZLI:
        fn()
    print("\n%d gecti, %d kaldi" % (len(ortak_test._gecti), len(ortak_test._kaldi)))
    for k in ortak_test._kaldi:
        print("  KALDI:", k)
