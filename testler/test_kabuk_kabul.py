# -*- coding: utf-8 -*-
"""
test_kabuk_kabul.py -- Dalga 2 Ajan 6 kabuk kabul olcutleri.

  - Ctrl+K komut paleti "Calistir"i bulur ve calistirir
  - birincil Calistir dugmesi kosu_durumu_degisti ile Durdur'a doner
  - Dosya > Rapor olustur...: rapor.olustur'a dogru argumanlar (monkeypatch)
  - galeri: butun ornekler, kategori/seviye sayilari JSON'la uyusur, suzgec
  - baslangic ekrani <= 300 ms kurulur (olculur)
  - en kucuk pencere <= 1280x800; 1280x800'de yatay kaydirma yok
  - onizleme paneli daraltilir ve QSettings'te hatirlanir
  - kenar cubugu durum ikonlari sekme isaretlerinden gelir

Yalnizca offscreen calisir; modal diyaloglar exec() EDILMEZ.
"""

import glob
import json
import os
import time
import warnings

from testler.ortak_test import kontrol, ORNEK   # noqa: F401

warnings.filterwarnings("ignore")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

BASLANGIC_SINIRI_MS = 300.0
EKRAN = (1280, 800)


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


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


# ============================================================================
# komut paleti ve birincil kosu dugmesi
# ============================================================================

def test_palet_calistiri_bulur():
    print("\n[KK1] Ctrl+K: 'Çalıştır' bulunur, Enter ile calisir")
    uyg = _qt()
    from PySide6 import QtCore, QtGui, QtWidgets
    from arayuz.bilesenler.komut_paleti import ROL_EYLEM
    p = _pencere(os.path.join(ORNEK, "pwr_pinhucre.json"))
    kosu = []
    p.s_calistir.calistir = lambda *a, **k: kosu.append(1)      # kosu baslatilmaz
    try:
        p.resize(*EKRAN)
        p.show()
        uyg.processEvents()
        kontrol("palet kisayolu Ctrl+K",
                p.palet.kisayol.key() == QtGui.QKeySequence("Ctrl+K"))
        p.ust.komut_alani.click()
        kontrol("ust cubuktaki arama alani paleti aciyor", p.palet.isVisible())
        p.palet.arama.setText("Çalıştır")
        ilk = p.palet.liste.item(0)
        kontrol("ilk sonuc F9 'ÇALIŞTIR' eylemi",
                ilk is not None and ilk.data(ROL_EYLEM) is p.e_calistir,
                "-> %s" % p.palet.sonuclar()[:3])
        olay = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Return,
                               QtCore.Qt.NoModifier)
        QtWidgets.QApplication.sendEvent(p.palet.arama, olay)
        kontrol("Enter paleti kapatip kosuyu baslatiyor",
                kosu == [1] and not p.palet.isVisible() and p.gecerli_sekme() == "calistir",
                "-> kosu %s, sayfa %s" % (kosu, p.gecerli_sekme()))
        p.sekmeye_git("malzemeler")
        eylemler = p.komut_eylemleri()
        sayfa = [e for e in eylemler if e in p.s_malzeme.komutlar()] \
            if hasattr(p.s_malzeme, "komutlar") else []
        kontrol("palet menu eylemlerini ve etkin sayfanin komutlarini listeliyor",
                p.e_kaydet in eylemler and p.e_rapor in eylemler
                and (not hasattr(p.s_malzeme, "komutlar") or sayfa))
    finally:
        _kapat(p)


def test_kosu_dugmesi_durdur():
    print("\n[KK2] birincil dugme: kapi, kosarken Durdur, bitince Calistir")
    _qt()
    p = _pencere(os.path.join(ORNEK, "pwr_pinhucre.json"))
    durduruldu = []
    p.s_calistir.durdur = lambda: durduruldu.append(1)
    try:
        p.onizleme.cizildi_mi = lambda: False
        p._kosu_dugmesi_guncelle()
        kontrol("cizilmemis geometri: dugme kapali, ipucu nedenini soyluyor",
                not p.ust.d_kosu.isEnabled() and "Önce çiz" in p.ust.d_kosu.toolTip())
        p.onizleme.cizildi_mi = lambda: True
        p._kosu_dugmesi_guncelle()
        kontrol("cizilmis ve hatasiz: dugme acik", p.ust.d_kosu.isEnabled())
        p.s_calistir.kosu_durumu_degisti.emit(True)
        kontrol("kosu basladi: dugme 'Durdur'",
                p.ust.d_kosu.text() == "Durdur" and p.ust.kosuyor_mu())
        p.ust.d_kosu.click()
        kontrol("Durdur tiklamasi s_calistir.durdur'u cagiriyor", durduruldu == [1])
        p.s_calistir.kosu_durumu_degisti.emit(False)
        kontrol("kosu bitti: dugme 'Çalıştır' ve acik",
                p.ust.d_kosu.text() == "Çalıştır" and p.ust.d_kosu.isEnabled())
        p.e_yeni.trigger()
        kontrol("baslangic ekraninda Calistir dugmesi kapali", not p.ust.d_kosu.isEnabled())
    finally:
        _kapat(p)


# ============================================================================
# rapor menusu
# ============================================================================

def _rapor_ortami(p, cagrilar, yol, suzgec="HTML (*.html)", hata=None):
    """rapor.olustur ve kayit diyalogunu taklit eder; geri yukleyiciyi dondurur."""
    from PySide6 import QtWidgets
    from cekirdek import rapor
    eski = (rapor.olustur, QtWidgets.QFileDialog.getSaveFileName,
            QtWidgets.QMessageBox.critical)

    def sahte_olustur(spec, kosu_dizini, hedef, bicim):
        cagrilar.append(("olustur", spec, kosu_dizini, hedef, bicim))
        if hata:
            raise rapor.RaporHatasi(hata)
        return rapor.RaporSonucu(yol=hedef, uyarilar=())
    rapor.olustur = sahte_olustur
    QtWidgets.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (yol, suzgec))
    QtWidgets.QMessageBox.critical = staticmethod(
        lambda *a, **k: cagrilar.append(("diyalog",) + a[1:3]))

    def geri():
        (rapor.olustur, QtWidgets.QFileDialog.getSaveFileName,
         QtWidgets.QMessageBox.critical) = eski
    return geri


def test_rapor_menusu():
    print("\n[KK3] Dosya > Rapor olustur...: dogru argumanlar, bildirim, hata diyalogu")
    _qt()
    p = _pencere(os.path.join(ORNEK, "pwr_pinhucre.json"))
    bildirimler = []
    gercek = p.bildir_mesaj

    def yakala(metin, *a, **k):
        bildirimler.append((metin, k.get("eylem_metni")))
        return gercek(metin, *a, **k)
    p.bildir_mesaj = yakala
    try:
        kontrol("Dosya menusunde 'Rapor oluştur…' var ve editorde acik",
                p.e_rapor.text() == "Rapor oluştur…" and p.e_rapor.isEnabled())
        cagrilar = []
        geri = _rapor_ortami(p, cagrilar, "/tmp/kk_rapor")
        p.s_calistir.son_kosu_dizini = lambda: None
        try:
            p.e_rapor.trigger()
        finally:
            geri()
        o = cagrilar[0] if cagrilar else None
        kontrol("kosu yok: yalniz model raporu (kosu_dizini None), .html eklendi",
                o is not None and o[1] is p.spec and o[2] is None
                and o[3] == "/tmp/kk_rapor.html" and o[4] == "html", "-> %s" % (o,))
        kontrol("basarida bildirim + 'Aç' eylemi",
                bool(bildirimler) and "kk_rapor.html" in bildirimler[-1][0]
                and bildirimler[-1][1] == "Aç", "-> %s" % bildirimler[-1:])

        cagrilar = []
        geri = _rapor_ortami(p, cagrilar, "/tmp/kk_rapor.pdf", "PDF (*.pdf)")
        p.s_calistir.son_kosu_dizini = lambda: "/tmp/kosu_dizini"
        try:
            p.rapor_olustur()
        finally:
            geri()
        o = cagrilar[0] if cagrilar else None
        kontrol("son kosu varsa dizini verilir; PDF bicimi",
                o is not None and o[2] == "/tmp/kosu_dizini" and o[4] == "pdf"
                and o[3] == "/tmp/kk_rapor.pdf", "-> %s" % (o,))

        cagrilar = []
        geri = _rapor_ortami(p, cagrilar, "/tmp/kk_rapor.html", hata="şablon bulunamadı")
        try:
            sonuc = p.rapor_olustur()
        finally:
            geri()
        kontrol("RaporHatasi: diyalog gosterilir, False doner",
                sonuc is False and any(c[0] == "diyalog" and "şablon bulunamadı" in c[2]
                                       for c in cagrilar), "-> %s" % cagrilar)
        cagrilar = []
        geri = _rapor_ortami(p, cagrilar, "")
        try:
            kontrol("diyalog iptal: rapor yazilmaz",
                    p.rapor_olustur() is False and not cagrilar)
        finally:
            geri()
    finally:
        _kapat(p)


# ============================================================================
# baslangic ekrani: galeri, sure
# ============================================================================

def _ham_meta():
    ham = {}
    for yol in glob.glob(os.path.join(ORNEK, "*.json")):
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
        ham[os.path.basename(yol)] = (veri.get("kategori"), veri.get("seviye"))
    return ham


def test_galeri_kategorileri():
    print("\n[KK4] GALERI: butun ornekler, kategori/seviye sayilari JSON'la uyusur")
    _qt()
    from arayuz.baslangic import BaslangicEkrani
    ham = _ham_meta()
    b = BaslangicEkrani()
    try:
        kontrol("galeride butun ornekler (%d)" % len(ham),
                sorted(k.bilgi.dosya for k in b.ornek_kartlari()) == sorted(ham))
        kategoriler = {}
        for kat, _sev in ham.values():
            kategoriler[kat] = kategoriler.get(kat, 0) + 1
        for kat, n in sorted(kategoriler.items(), key=lambda t: str(t[0])):
            if kat is None:
                continue
            b.kategori.sec(kat)
            gorunen = b.gorunur_ornekler()
            beklenen = sorted(d for d, (k, _s) in ham.items() if k == kat)
            kontrol("kategori '%s': %d ornek (JSON)" % (kat, n),
                    sorted(gorunen) == beklenen, "-> %d" % len(gorunen))
        b.kategori.sec("hepsi")
        for sev in ("giris", "orta", "ileri"):
            beklenen = sorted(d for d, (_k, s) in ham.items() if s == sev)
            if not beklenen:
                continue
            b.seviye.setCurrentIndex(b.seviye.findData(sev))
            kontrol("seviye '%s': %d ornek (JSON)" % (sev, len(beklenen)),
                    sorted(b.gorunur_ornekler()) == beklenen,
                    "-> %d" % len(b.gorunur_ornekler()))
        b.seviye.setCurrentIndex(0)
        b.arama.setText("godiva")
        bulunan = [k.bilgi for k in b.ornek_kartlari() if not k.isHidden()]
        kontrol("arama suzgeci: Godiva bulunur, her sonuc 'godiva' iceriyor",
                "godiva_kriter.json" in b.gorunur_ornekler()
                and all("godiva" in (o.baslik + o.aciklama + o.ad + o.dosya).lower()
                        for o in bulunan)
                and len(bulunan) < len(ham), "-> %s" % (b.gorunur_ornekler(),))
        b.arama.setText("boyle_bir_ornek_yok")
        kontrol("eslesme yoksa bos durum gorunur",
                not b.gorunur_ornekler() and not b.galeri_bos.isHidden())
        b.arama.clear()
        kontrol("suzgec temizlenince hepsi geri geliyor",
                len(b.gorunur_ornekler()) == len(ham) and b.galeri_bos.isHidden())
        acilan = []
        b.ornek_istendi.connect(acilan.append)
        b.ornek_kartlari()[0].secildi.emit()
        kontrol("galeri karti ornek yolunu yayar",
                acilan == [b.ornek_kartlari()[0].bilgi.yol], "-> %s" % acilan)
    finally:
        b.deleteLater()


def test_baslangic_suresi():
    print("\n[KK5] BASLANGIC ekrani <= %d ms kurulur ve cizilir" % BASLANGIC_SINIRI_MS)
    uyg = _qt()
    from arayuz.baslangic import BaslangicEkrani
    isinma = BaslangicEkrani()             # ikon/yazi tipi onbellekleri isinsin
    isinma.deleteLater()
    olculen = []
    for _i in range(3):
        t0 = time.perf_counter()
        b = BaslangicEkrani()
        b.resize(*EKRAN)
        b.show()
        uyg.processEvents()
        b.grab()
        olculen.append((time.perf_counter() - t0) * 1000.0)
        b.close()
        b.deleteLater()
    en_iyi = min(olculen)
    print("    olculen: %s ms" % ", ".join("%.0f" % x for x in olculen))
    kontrol("baslangic ekrani %.0f ms <= %.0f ms" % (en_iyi, BASLANGIC_SINIRI_MS),
            en_iyi <= BASLANGIC_SINIRI_MS)


# ============================================================================
# pencere boyutu, yatay kaydirma, onizleme paneli, kenar cubugu
# ============================================================================

def test_boyut_ve_yatay_kaydirma():
    print("\n[KK6] en kucuk pencere <= 1280x800; 1280x800'de yatay kaydirma yok")
    uyg = _qt()
    from PySide6 import QtWidgets
    p = _pencere(os.path.join(ORNEK, "pwr_17x17.json"))
    try:
        kontrol("en kucuk pencere <= 1280x800",
                p.minimumWidth() <= EKRAN[0] and p.minimumHeight() <= EKRAN[1]
                and p.minimumSizeHint().width() <= EKRAN[0]
                and p.minimumSizeHint().height() <= EKRAN[1],
                "-> %dx%d / ipucu %s" % (p.minimumWidth(), p.minimumHeight(),
                                         p.minimumSizeHint()))
        p.resize(*EKRAN)
        p.show()
        uyg.processEvents()
        tasan = []
        for k in p.sekme_anahtarlari():
            if not p.sekmeye_git(k, sessiz=True):
                continue
            uyg.processEvents()
            alan = p.sekme_sayfasi(k)
            if isinstance(alan, QtWidgets.QScrollArea) and alan.horizontalScrollBar().maximum() > 0:
                tasan.append("%s(+%d px)" % (k, alan.horizontalScrollBar().maximum()))
        kontrol("1280x800: hicbir sayfada yatay kaydirma yok", not tasan, "-> %s" % tasan)
        kontrol("pencere 1280x800'e sigdi (en kucuk boyut zorlamadi)",
                p.width() == EKRAN[0] and p.height() == EKRAN[1], "-> %dx%d" % (p.width(), p.height()))
        # Baska pencere boyutundan kalan bolucu orani (onizleme genis) da tasirmamali.
        p.sekmeye_git("kor", sessiz=True)
        p._bolucu.setSizes([300, 900])
        p.resize(EKRAN[0] - 1, EKRAN[1])
        p.resize(*EKRAN)
        for _i in range(3):
            uyg.processEvents()
        alan = p.sekme_sayfasi("kor")
        kontrol("genis onizleme orani: sayfaya yer acildi, yatay kaydirma yok",
                alan.horizontalScrollBar().maximum() == 0
                and p._bolucu.sizes()[1] >= p.onizleme_paneli.minimumWidth(),
                "-> +%d px, %s" % (alan.horizontalScrollBar().maximum(), p._bolucu.sizes()))
        p.e_yeni.trigger()
        uyg.processEvents()
        kontrol("baslangic ekraninda yatay kaydirma yok",
                p.baslangic.kaydirma.horizontalScrollBar().maximum() == 0,
                "-> +%d px" % p.baslangic.kaydirma.horizontalScrollBar().maximum())
        kontrol("1280 px'te baslangic kartlari 4 sutun (maket)", p.baslangic._sutun == 4,
                "-> %d" % p.baslangic._sutun)
    finally:
        _kapat(p)


def test_onizleme_paneli_hatirlanir():
    print("\n[KK7] onizleme paneli daraltilir, QSettings'te hatirlanir")
    uyg = _qt()
    from arayuz.pencere import kabuk
    p = _pencere(os.path.join(ORNEK, "pwr_17x17.json"))
    try:
        p.resize(*EKRAN)
        p.show()
        uyg.processEvents()
        p.onizleme_paneli.daralt(False)
        p.onizleme_paneli.d_daralt.click()
        kontrol("daralt dugmesi paneli daraltiyor, onizleme gizli",
                p.onizleme_paneli.dar_mi() and p.onizleme.isHidden()
                and p.onizleme_paneli.width() == kabuk.ONIZLEME_DAR)
        kontrol("daraltma QSettings'e yazildi",
                str(p.ayarlar.value(kabuk.ONIZLEME_AYARI)).lower() in ("false", "0"))
    finally:
        _kapat(p)
    p2 = _pencere(os.path.join(ORNEK, "pwr_17x17.json"))
    try:
        kontrol("yeni pencere daraltilmis acilir", p2.onizleme_paneli.dar_mi())
        p2.onizleme_paneli.d_daralt.click()
        kontrol("yeniden acilinca onizleme gorunur ve ayar guncellenir",
                not p2.onizleme_paneli.dar_mi() and not p2.onizleme.isHidden()
                and str(p2.ayarlar.value(kabuk.ONIZLEME_AYARI)).lower() in ("true", "1"))
    finally:
        _kapat(p2)


def test_kenar_durumlari():
    print("\n[KK8] kenar cubugu: durum ikonlari ve ipuclari sekme isaretlerinden")
    _qt()
    from arayuz.bilesenler.kenar_cubugu import ROL_ANAHTAR
    from arayuz.pencere import kabuk
    p = _pencere(os.path.join(ORNEK, "pwr_17x17.json"))
    try:
        uyusmayan = []
        for k in p.sekme_anahtarlari():
            isaret, aciklama = p.sekme_isareti(k)
            oge = [p.kenar.liste.item(i) for i in range(p.kenar.liste.count())
                   if p.kenar.liste.item(i).data(ROL_ANAHTAR) == k]
            beklenen = kabuk.ISARET_DURUMU.get(isaret)
            if not oge or p.kenar.durum(k) != beklenen \
                    or (aciklama and oge[0].toolTip() != aciklama):
                uyusmayan.append((k, isaret, p.kenar.durum(k) if oge else "?"))
        kontrol("her ogenin durumu ve ipucu isaretle uyusuyor", not uyusmayan,
                "-> %s" % uyusmayan)
        kontrol("kenar_ipucu bilinmeyen anahtarda False",
                kabuk.kenar_ipucu(p.kenar, "yok_boyle", "x") is False)
    finally:
        _kapat(p)


def test_giris_noktasi():
    print("\n[KK9] python -m arayuz.ana_pencere: main() pencereyi kurar ve dosyayi acar")
    uyg = _qt()
    import types
    from PySide6 import QtCore, QtWidgets
    from arayuz import ana_pencere as ap
    cagrilar = []
    eski = {"QtWidgets": ap.QtWidgets, "gunluk": ap.gunluk.kur,
            "hata": ap.hata_yakalayici.kur, "tema": ap.tema.uygula,
            "dinleyici": ap.ceviri.dinleyici_ekle, "exec": QtWidgets.QApplication.exec,
            "yerel": QtCore.QLocale()}
    ap.QtWidgets = types.SimpleNamespace(QApplication=lambda argv: uyg)
    ap.gunluk.kur = lambda *a, **k: cagrilar.append("gunluk")
    ap.hata_yakalayici.kur = lambda app: cagrilar.append("hata_yakalayici")
    ap.tema.uygula = lambda app, *a, **k: cagrilar.append("tema")
    ap.ceviri.dinleyici_ekle = lambda f: cagrilar.append("dinleyici")
    QtWidgets.QApplication.exec = lambda *a: 0
    once = set(QtWidgets.QApplication.topLevelWidgets())
    try:
        sonuc = ap.main([os.path.join(ORNEK, "pwr_pinhucre.json")])
        yeni = [w for w in QtWidgets.QApplication.topLevelWidgets()
                if w not in once and isinstance(w, ap.AnaPencere)]
        kontrol("main 0 doner, bir AnaPencere acar",
                sonuc == 0 and len(yeni) == 1, "-> %s %d" % (sonuc, len(yeni)))
        kontrol("komut satiri dosyasi kopya olarak acildi (ornek)",
                bool(yeni) and yeni[0].ornek_kaynagi
                and yeni[0].ornek_kaynagi.endswith("pwr_pinhucre.json"))
        kontrol("gunluk, hata yakalayici, tema ve dil dinleyicisi kuruldu",
                {"gunluk", "hata_yakalayici", "tema", "dinleyici"} <= set(cagrilar),
                "-> %s" % cagrilar)
        kontrol("ondalik ayirici nokta (C yerel ayari)",
                QtCore.QLocale().decimalPoint() == ".")
        for w in yeni:
            _kapat(w)
    finally:
        ap.QtWidgets = eski["QtWidgets"]
        ap.gunluk.kur, ap.hata_yakalayici.kur = eski["gunluk"], eski["hata"]
        ap.tema.uygula, ap.ceviri.dinleyici_ekle = eski["tema"], eski["dinleyici"]
        QtWidgets.QApplication.exec = eski["exec"]
        QtCore.QLocale.setDefault(eski["yerel"])


def test_ust_cubuk_ikonlari_ve_son_seridi():
    print("\n[KK10] ust cubuk ikonlari etkinlik degisince kalir; son kullanilanlar seridi")
    _qt()
    from PySide6 import QtWidgets
    from arayuz.baslangic import BaslangicEkrani
    p = _pencere(os.path.join(ORNEK, "pwr_pinhucre.json"))
    try:
        dugmeler = [d for d in p.ust.findChildren(QtWidgets.QToolButton)
                    if d.defaultAction() in (p.e_yeni, p.e_ac, p.e_kaydet, p.e_geri, p.e_yinele)]
        p.e_geri.setEnabled(False)
        p.e_geri.setEnabled(True)
        p.e_kaydet.setEnabled(False)
        kontrol("5 hizli eylem dugmesi, hepsi ikonlu (etkinlik degisiminden sonra da)",
                len(dugmeler) == 5 and all(not d.icon().isNull() for d in dugmeler),
                "-> %s" % [(d.defaultAction().text(), d.icon().isNull()) for d in dugmeler])
    finally:
        _kapat(p)
    b = BaslangicEkrani()
    try:
        serit = b._son_serit
        b.son_dosyalari_ayarla([])
        b.son_dosyalari_ayarla([os.path.join(ORNEK, "pwr_17x17.json")])
        b.son_dosyalari_ayarla([])
        kontrol("'henuz yok' etiketi seritte kalir (sahipsiz cizilmez)",
                serit.indexOf(b.son_bos) == 1 and not b.son_bos.isHidden()
                and serit.count() == 3, "-> index %d, %d oge" % (serit.indexOf(b.son_bos),
                                                               serit.count()))
    finally:
        b.deleteLater()


HIZLI = [test_palet_calistiri_bulur, test_kosu_dugmesi_durdur, test_rapor_menusu,
         test_galeri_kategorileri, test_baslangic_suresi, test_boyut_ve_yatay_kaydirma,
         test_onizleme_paneli_hatirlanir, test_kenar_durumlari, test_giris_noktasi,
         test_ust_cubuk_ikonlari_ve_son_seridi]
YAVAS = []


if __name__ == "__main__":
    from testler.ortak_test import _gecti, _kaldi
    for fn in HIZLI:
        fn()
    print("\n SONUC: %d gecti, %d kaldi" % (len(_gecti), len(_kaldi)))
    for t in _kaldi:
        print("   - %s" % t)
