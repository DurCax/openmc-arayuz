# -*- coding: utf-8 -*-
"""
test_sekme_sozlesmesi.py -- kabuk <-> sekme sozlesmesi (Dalga 2 on-commit 3-4).

DONUK: asagidaki uyelerin adi ve imzasi Dalga 2 boyunca DEGISMEZ (Ajan 6/7/8/8c
gorunumu yenilerken bunlari korur). Bir imza degisecekse once bu liste ve
orkestrator. Ayrica: gezinme cephesi (arayuz/pencere/gezinme.py),
sekme_arayuzu varsayilanlari ve araclar/ekran_turu.py.
Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import importlib.util
import inspect
import os
import tempfile

from testler.ortak_test import kontrol, ORNEK, KOK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# sinif yolu -> {uye: imza}. Imza: yontemde inspect.signature metni,
# sinyalde Qt imzasi ("durum(QString,bool)"), sabitte "=deger".
DONUK_SEKME = {
    "arayuz.ortak:SekmeTabani": {
        "spec_yukle": "(self, spec)", "doldur": "(self)", "bildir": "(self)",
        "degisti": "degisti(QString)", "KONU": "=genel"},
    "arayuz.sekme_calistir:CalistirSekmesi": {
        "durum": "durum(QString,bool)", "sonuc_degisti": "sonuc_degisti()",
        "degisti": "degisti(QString)", "KONU": "=calistirma",
        "kapi_ayarla": "(self, fonksiyon)", "kapi_guncelle": "(self)",
        "sonuc_var": "(self)", "sifirla": "(self)",
        "spec_ayarla": "(self, spec, proje_yolu=None)", "calistir": "(self)",
        "durdur": "(self)",
        "kosu_durumu_degisti": "kosu_durumu_degisti(bool)", "son_kosu_dizini": "(self)"},
    "arayuz.sekme_analiz:AnalizSekmesi": {
        "durum": "durum(QString,bool)", "sonuc_degisti": "sonuc_degisti()",
        "kapi_ayarla": "(self, fonksiyon)", "kapi_guncelle": "(self)",
        "sonuc_var": "(self)", "sifirla": "(self)",
        "spec_ayarla": "(self, spec, proje_yolu=None)"},
    "arayuz.sekme_tukenme:TukenmeSekmesi": {
        "durum": "durum(QString,bool)", "sonuc_degisti": "sonuc_degisti()",
        "KONU": "=tukenme", "kapi_ayarla": "(self, fonksiyon)", "kapi_guncelle": "(self)",
        "sonuc_var": "(self)", "sifirla": "(self)", "durdur": "(self)"},
    "arayuz.sekme_kor:KorSekmesi": {
        "tur_degistir_istendi": "tur_degistir_istendi()", "KONU": "=kor"},
    "arayuz.sekme_malzeme:MalzemeSekmesi": {"KONU": "=malzeme"},
    "arayuz.sekme_cubuk:CubukSekmesi": {"KONU": "=cubuk"},
    "arayuz.sekme_demet:DemetSekmesi": {"KONU": "=demet"},
    "arayuz.sekme_ayar:AyarSekmesi": {"KONU": "=ayar"},
}

# arayuz/ortak.py herkese acik adlari (Ajan 6: yalniz EK; silme/imza degisimi yok)
DONUK_ORTAK = {
    "sayi": "(deger=0.0, ondalik=5, en_az=0.0, en_cok=1000000000.0, adim=0.01, sonek='')",
    "tamsayi": "(deger=0, en_az=0, en_cok=1000000000, adim=1, sonek='')",
    "baslik": "(metin)", "ipucu": "(metin)", "ayrac": "()", "hata_metni": "(e)",
    "cumle_basi": "(metin)",
    "RenkDugmesi": "(self, rgb=(170, 170, 170), parent=None)",
    "SekmeTabani": "(self, parent=None)",
    "EnerjiGirdi": "(self, ev=1000000.0, parent=None)",
    "BilimselGirdi": "(self, deger=1.0, parent=None)",
    "GelismisBolum": "(self, anahtar=None, baslik='Gelişmiş', parent=None)",
    "BosDurum": "(self, baslik='', metin='', dugme_metni=None, simge='＋', parent=None)",
    "DurumRozeti": "(self, metin='', seviye='notr', tiklanabilir=False, parent=None)",
    "tekerlek_korumasi_kur": "(uygulama=None)",
    "qt_cevirisi_kur": "(uygulama, dil)",
}

# AnaPencere gezinme cephesi
DONUK_CEPHE = {
    "sekme_anahtarlari": "(self)", "sekmeye_git": "(self, anahtar, sessiz=False)",
    "gecerli_sekme": "(self)", "sekme_gorunur_mu": "(self, anahtar)",
    "sekme_widget": "(self, anahtar)", "sekme_sayfasi": "(self, anahtar)",
    "sekme_basligi": "(self, anahtar)", "sekme_isareti": "(self, anahtar)",
}


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _sinif(yol):
    modul, ad = yol.split(":")
    return getattr(importlib.import_module(modul), ad)


def _sinyal_imzasi(cls, ad):
    from PySide6 import QtCore
    mo = cls.staticMetaObject
    for i in range(mo.methodCount()):
        m = mo.method(i)
        if (m.methodType() == QtCore.QMetaMethod.Signal
                and bytes(m.name()).decode() == ad):
            return bytes(m.methodSignature()).decode()
    return None


def _uye_imzasi(cls, ad, beklenen):
    if beklenen.startswith("="):
        return "=%s" % getattr(cls, ad, None)
    if "(" in beklenen and not beklenen.startswith("("):
        return _sinyal_imzasi(cls, ad)
    uye = getattr(cls, ad, None)
    return str(inspect.signature(uye)) if callable(uye) else None


def _pencere(dosya=None):
    from arayuz.ana_pencere import AnaPencere
    p = AnaPencere(dosya)
    p._kaydetme_sor = lambda: True
    return p


def _kapat(p):
    from PySide6 import QtCore
    p.s_tukenme.bekle()
    p._kirli = False
    p.close()
    p.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


def test_donuk_sekme_uyeleri():
    print("\n[SS1] DONUK sekme uyeleri: ad ve imza")
    _qt()
    for yol, uyeler in DONUK_SEKME.items():
        cls = _sinif(yol)
        for ad, beklenen in uyeler.items():
            bulunan = _uye_imzasi(cls, ad, beklenen)
            kontrol("%s.%s %s" % (yol.split(":")[1], ad, beklenen), bulunan == beklenen,
                    "-> %s" % bulunan)
    from arayuz.ortak import SekmeTabani
    editorler = [c for y, c in ((y, _sinif(y)) for y in DONUK_SEKME)
                 if y.split(":")[1] not in ("SekmeTabani", "CalistirSekmesi", "AnalizSekmesi")]
    kontrol("editor sekmeleri SekmeTabani alt sinifi",
            all(issubclass(c, SekmeTabani) for c in editorler))


def test_donuk_ortak_adlari():
    print("\n[SS2] arayuz/ortak.py herkese acik adlari ve imzalari")
    from arayuz import ortak
    for ad, beklenen in DONUK_ORTAK.items():
        nesne = getattr(ortak, ad, None)
        hedef = nesne.__init__ if inspect.isclass(nesne) else nesne
        bulunan = str(inspect.signature(hedef)) if nesne is not None else None
        kontrol("ortak.%s%s" % (ad, beklenen), bulunan == beklenen, "-> %s" % bulunan)


def test_sekme_arayuzu_varsayilanlari():
    print("\n[SS3] sekme_arayuzu: tanimsiz yontemde varsayilan, tanimlida sonuc")
    _qt()
    from PySide6 import QtGui, QtWidgets
    from arayuz.pencere import sekme_arayuzu as sa
    bos = QtWidgets.QWidget()
    kontrol("varsayilanlar: (), (), False",
            (sa.baslik_eylemleri(bos), sa.komutlar(bos), sa.odakla(bos, "kor")) == ((), (), False))
    kontrol("bos widget Protocol'u saglamaz", not isinstance(bos, sa.SekmeArayuzu))

    class Tam(QtWidgets.QWidget):
        def __init__(self):
            super().__init__()
            self.e = QtGui.QAction("Ekle", self)

        def baslik_eylemleri(self):
            return [self.e]

        def komutlar(self):
            return (self.e,)

        def odakla(self, yer):
            return yer == "kor"

    t = Tam()
    kontrol("tanimli: eylemler tuple", sa.baslik_eylemleri(t) == (t.e,)
            and sa.komutlar(t) == (t.e,))
    kontrol("tanimli: odakla sonucu", sa.odakla(t, "kor") and not sa.odakla(t, "x"))
    kontrol("Protocol saglanir", isinstance(t, sa.SekmeArayuzu))

    class Bozuk(QtWidgets.QWidget):
        def komutlar(self):
            return "metin"
    kontrol("dizi olmayan donus () (loglanir)", sa.komutlar(Bozuk()) == ())
    kontrol("UYELER", sa.UYELER == ("baslik_eylemleri", "komutlar", "odakla"))


def test_gezinme_cephesi():
    print("\n[SS4] gezinme cephesi: imzalar ve davranis")
    _qt()
    from cekirdek import uygunluk
    from arayuz.ana_pencere import AnaPencere
    from arayuz.pencere import sekme_arayuzu as sa
    for ad, beklenen in DONUK_CEPHE.items():
        uye = getattr(AnaPencere, ad, None)
        bulunan = str(inspect.signature(uye)) if uye else None
        kontrol("AnaPencere.%s%s" % (ad, beklenen), bulunan == beklenen, "-> %s" % bulunan)
    p = _pencere(os.path.join(ORNEK, "pwr_pinhucre.json"))
    try:
        kontrol("anahtarlar uygunluk.SEKMELER", p.sekme_anahtarlari() == tuple(uygunluk.SEKMELER))
        kontrol("sekme_widget editoru verir", p.sekme_widget("demet") is p.s_demet
                and p.sekme_widget("calistir") is p.s_calistir)
        kontrol("bilinmeyen anahtar", p.sekme_widget("yok") is None
                and p.sekme_sayfasi("yok") is None and p.sekmeye_git("yok") is False
                and not p.sekme_gorunur_mu("yok") and p.sekme_isareti("yok") == ("", ""))
        kontrol("tek_cubuk: Demet gizli, gidilmez",
                not p.sekme_gorunur_mu("demet") and p.sekmeye_git("demet", sessiz=True) is False)
        kontrol("gorunur sekmeye gidilir", p.sekmeye_git("kor") and p.gecerli_sekme() == "kor")
        kontrol("sayfa widget'i sarar", p.sekme_sayfasi("kor").widget() is p.s_kor)
        kontrol("baslik isaretsiz", p.sekme_basligi("kor") == "Geometri")
        isaret, ipucu = p.sekme_isareti("malzemeler")
        kontrol("isaret + ipucu", isaret in ("!", "•", "✓") and isinstance(ipucu, str),
                "-> %r" % ((isaret, ipucu),))
        kontrol("her sekmede sekme_arayuzu calisir",
                all(isinstance(sa.komutlar(p.sekme_widget(k)), tuple)
                    and isinstance(sa.baslik_eylemleri(p.sekme_widget(k)), tuple)
                    for k in p.sekme_anahtarlari()))
    finally:
        _kapat(p)


def _ekran_turu():
    spec = importlib.util.spec_from_file_location(
        "ekran_turu", os.path.join(KOK, "araclar", "ekran_turu.py"))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def test_ekran_turu():
    print("\n[SS5] araclar/ekran_turu.py: cikti dizini ve offscreen tur")
    et = _ekran_turu()
    kontrol("--cikti ortamdan once", et.cikti_dizini("/a", None, {et.ORTAM_DEGISKENI: "/b"})
            == "/a")
    kontrol("ortam + alt", et.cikti_dizini(None, "d2_x", {et.ORTAM_DEGISKENI: "/b"})
            == "/b/d2_x")
    try:
        et.cikti_dizini(None, None, {})
        hata = False
    except ValueError:
        hata = True
    kontrol("dizin yoksa ValueError", hata)
    kontrol("boyut ayristirma", et.boyutlari_coz("1280x800, 1440X900")
            == ((1280, 800), (1440, 900)))
    kontrol("cikti dizini yoksa main 2 dondurur",
            et.main(["--boyut", "1x1"]) == 2 if not os.environ.get(et.ORTAM_DEGISKENI) else True)
    _qt()
    with tempfile.TemporaryDirectory() as d:
        yollar = et.cek(d, (os.path.join(ORNEK, "pwr_17x17.json"),), ("demet",),
                        ("acik",), ((1280, 800),))
        adlar = sorted(os.path.basename(y) for y in yollar)
        kontrol("baslangic + demet PNG'leri",
                adlar == ["baslangic_acik_1280x800.png", "pwr_17x17_demet_acik_1280x800.png"]
                and all(os.path.getsize(y) > 0 for y in yollar), "-> %s" % adlar)
        with open(os.path.join(d, "tur_ozeti.txt"), encoding="utf-8") as f:
            ozet = f.read()
        kontrol("tur ozeti yazildi", "pwr_17x17_demet_acik_1280x800" in ozet, "-> %r" % ozet)


HIZLI = [test_donuk_sekme_uyeleri, test_donuk_ortak_adlari, test_sekme_arayuzu_varsayilanlari,
         test_gezinme_cephesi, test_ekran_turu]
YAVAS = []
