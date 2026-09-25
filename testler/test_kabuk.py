# -*- coding: utf-8 -*-
"""
test_kabuk.py -- Dalga 2 kabuk: baslangic ekrani, model basligi, sekme
gorunurlugu ve isaretleri, sag panel, kaldirilan ozellikler, ortak
bilesenler (GelismisBolum, BosDurum, DurumRozeti) ve parca paleti/izgaralar.

Yalnizca offscreen calisir; modal diyaloglar exec() EDILMEZ.
"""

import glob
import os
import re
import shutil
import tempfile
import warnings

from testler.ortak_test import kontrol, ORNEK, KOK   # noqa: F401

warnings.filterwarnings("ignore")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_AYAR = []


def _qt():
    try:
        from PySide6 import QtCore, QtWidgets
    except Exception as e:                         # pragma: no cover
        kontrol("PySide6 yok, kabuk testi atlandi", True, "-> %s" % e)
        return None
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    if not _AYAR:
        # Kullanicinin GERCEK ayarlari (son dosyalar, Gelismis durumlari)
        # kirletilmesin.
        import atexit
        _AYAR.append(tempfile.mkdtemp(prefix="kabuk_ayar_"))
        atexit.register(shutil.rmtree, _AYAR[0], True)
        for bicim in (QtCore.QSettings.NativeFormat, QtCore.QSettings.IniFormat):
            QtCore.QSettings.setPath(bicim, QtCore.QSettings.UserScope, _AYAR[0])
    return uyg


def _pencere(dosya=None):
    from arayuz.ana_pencere import AnaPencere
    p = AnaPencere(dosya)
    # Offscreen testte modal "kaydedilsin mi?" sorusu (QMessageBox.exec) testi
    # KILITLERDI: soru yerine "kaydetmeden devam" secilir.
    p._kaydetme_sor = lambda: True
    return p


def _kapat(p):
    """Pencereyi kapatir ve SILER: kapali ama canli pencereler her tema
    degisiminde yeniden cilalanir ve sonraki testleri yavaslatir."""
    try:
        from PySide6 import QtCore
        p.s_tukenme.bekle()
        p._kirli = False
        p.close()
        p.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    except Exception:
        pass


def _gorunur_anahtarlar(p):
    from cekirdek import uygunluk
    return [k for k in uygunluk.SEKMELER if p.sekmeler.isTabVisible(p._sekme_ix[k])]


def _duz(html):
    return re.sub(r"<[^>]+>", "", html).replace("&amp;", "&")


# ============================================================================
# 1. bos sablonlar
# ============================================================================

def test_bos_sablonlar():
    print("\n[K1] BASLANGIC: her 'Bos basla' sablonu gecerli, kurulur ve cizilir")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from arayuz import baslangic
    from cekirdek import dogrula, kurucu, uygunluk
    kontrol("7 kart, basliklar dogru sirada",
            [k["anahtar"] for k in baslangic.KARTLAR]
            == ["pin", "demet_kare", "demet_altigen", "tam_kor", "plaka", "tamburlu", "zirh"])
    beklenen_tur = {"pin": "tek_cubuk", "demet_kare": "tek_demet",
                    "demet_altigen": "tek_demet", "tam_kor": "kare_kafes",
                    "plaka": "tek_plaka", "tamburlu": "tamburlu"}
    for k in baslangic.KARTLAR:
        if not k["bos"]:
            continue
        a = k["anahtar"]
        spec = baslangic.bos_sablon(a)
        bulgular = dogrula.tum_kontroller(spec, veri_kontrolu=False)
        hatalar = [b.mesaj for b in bulgular if b.seviye == "hata"]
        kontrol("'%s' sablonu 0 hata" % a, not hatalar, "-> %s" % hatalar[:3])
        kontrol("'%s' kor turu %s" % (a, beklenen_tur[a]), spec["kor"]["tur"] == beklenen_tur[a],
                "-> %s" % spec["kor"]["tur"])
        kontrol("'%s' yeni modelde secilebilir tur (kuresel degil)" % a,
                spec["kor"]["tur"] in uygunluk.KOR_TURLERI)
        kontrol("'%s' sade: tally yok, aciklama bos" % a,
                spec["tallyler"] == [] and spec["aciklama"] == "")
        kontrol("'%s' malzeme + parca/kor hazir" % a,
                bool(spec["malzemeler"]) and (spec["cubuklar"] or spec["plakalar"]
                                              or spec["kor"].get("dolgu")))
        try:
            model, bilgi = kurucu.kur(spec)
            model.plot(basis="xy", width=bilgi["sinir_kutu"], pixels=(120, 120),
                       color_by="material", colors=bilgi["renkler"])
            plt.close("all")
            kontrol("'%s' kuruluyor ve ciziliyor" % a, True)
        except Exception as e:
            kontrol("'%s' kuruluyor ve ciziliyor" % a, False, "-> %s" % e)
        finally:
            # Model.plot hata verirse gecici dizinde (silinmis) kalabiliyor;
            # sonraki testler os.getcwd() hatasiyla dusmesin.
            os.chdir(KOK)
    # altigen sablon: kullanilmayan emici cubuk ve 'e' harfi atildi
    s = baslangic.bos_sablon("demet_altigen")
    kontrol("altigen sablon: kullanilmayan emici cubuk/harf yok",
            [c["ad"] for c in s["cubuklar"]] == ["yakit_cubugu"]
            and set(s["demetler"][0]["anahtar"]) == {"y"}
            and "b4c" not in [m["ad"] for m in s["malzemeler"]])
    t = baslangic.bos_sablon("tam_kor")
    kontrol("tam kor sablonu: 3x3 harita, adim = demet genisligi (21.42 cm)",
            t["kor"]["boyut"] == [3, 3] and len(t["kor"]["harita"]) == 3
            and abs(t["kor"]["adim"] - 21.42) < 1e-9)
    kontrol("zirh kartinda bos sablon yok (kuresel yeni modelde sunulmaz)",
            not baslangic.kart("zirh")["bos"] and baslangic.kart("zirh")["ornek"])
    try:
        baslangic.bos_sablon("zirh")
        kontrol("zirh icin bos_sablon KeyError", False)
    except KeyError:
        kontrol("zirh icin bos_sablon KeyError", True)
    kontrol("ilk_cumle sayidaki noktada bolmuyor",
            baslangic.ilk_cumle("k-inf = 1.3570 +/- 0.0020. Ikinci cumle.")
            == "k-inf = 1.3570 +/- 0.0020.")


# ============================================================================
# 2. baslangic ekrani
# ============================================================================

def test_baslangic_ekrani():
    print("\n[K2] BASLANGIC: ekran, kartlar, ornek listesi, Yeni / geri don")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtCore, QtGui, QtWidgets
    from arayuz import baslangic
    p = _pencere()
    try:
        b = p.baslangic
        kontrol("dosyasiz acilista baslangic ekrani gorunur", p.baslangic_acik_mi())
        kontrol("baslik 'Ne modelliyorsun?'", b.baslik.text() == "Ne modelliyorsun?")
        kontrol("ilk acilista 'modele don' gizli", b.d_geri.isHidden())
        kontrol("baslangicta model eylemleri kapali (Kaydet, F9)",
                not p.e_kaydet.isEnabled() and not p.e_calistir.isEnabled())
        n_ornek = len(glob.glob(os.path.join(ORNEK, "*.json")))
        kontrol("ornek listesi butun ornekleri gosteriyor (%d)" % n_ornek,
                b.ornek_listesi.topLevelItemCount() == n_ornek,
                "-> %d" % b.ornek_listesi.topLevelItemCount())
        bos = [o for o in range(b.ornek_listesi.topLevelItemCount())
               if not b.ornek_listesi.topLevelItem(o).text(1)]
        kontrol("her ornegin aciklama satiri var", not bos)
        kontrol("zirh kartinda 'Bos basla' gizli, 'Ornekten basla' var",
                b.kart_dugmesi("zirh", "bos").isHidden()
                and not b.kart_dugmesi("zirh", "ornek").isHidden())
        kontrol("tam kor kartinda ornek yok -> 'Ornekten basla' gizli",
                b.kart_dugmesi("tam_kor", "ornek").isHidden())

        # klavye: kart dugmesi Enter ile basilir
        yakalanan = []
        b.bos_istendi.connect(yakalanan.append)
        dugme = b.kart_dugmesi("plaka", "bos")
        b.bos_istendi.disconnect(p._bos_basla)
        olay = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Return,
                               QtCore.Qt.NoModifier)
        QtWidgets.QApplication.sendEvent(dugme, olay)
        b.bos_istendi.connect(p._bos_basla)
        kontrol("Enter tusu kart dugmesini basiyor", yakalanan == ["plaka"],
                "-> %s" % yakalanan)

        b.kart_dugmesi("demet_kare", "bos").click()
        kontrol("'Bos basla' editoru aciyor", not p.baslangic_acik_mi())
        kontrol("'Bos basla' sablonu yuklendi (tek_demet)",
                p.spec["kor"]["tur"] == "tek_demet" and p.proje_yolu is None
                and p.ornek_kaynagi is None)
        kontrol("'Bos basla' karakteristik sekmeye goturuyor (Demet)",
                p._sekme_anahtari() == "demet")
        kontrol("editorde model eylemleri acik", p.e_kaydet.isEnabled())

        p.e_yeni.trigger()
        kontrol("Yeni -> baslangic ekrani", p.baslangic_acik_mi())
        kontrol("acik model varken 'modele don' gorunur", not b.d_geri.isHidden())
        kontrol("Yeni modeli silmiyor (kart secilene kadar)",
                p.spec["kor"]["tur"] == "tek_demet")
        esc = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Escape,
                              QtCore.Qt.NoModifier)
        QtWidgets.QApplication.sendEvent(b, esc)
        kontrol("Esc acik modele donuyor", not p.baslangic_acik_mi())

        p.e_yeni.trigger()
        b.kart_dugmesi("zirh", "ornek").click()
        kontrol("'Ornekten basla' ornegi KOPYA aciyor",
                p.proje_yolu is None and p.ornek_kaynagi
                and os.path.basename(p.ornek_kaynagi) == "zirh_kure.json")
        kontrol("ornekten gelen kuresel model aciliyor",
                p.spec["kor"]["tur"] == "kuresel")
        kontrol("kart ornek dosyalari mevcut",
                all(os.path.exists(os.path.join(baslangic.ORNEKLER, k["ornek"]))
                    for k in baslangic.KARTLAR if k["ornek"]))
    finally:
        _kapat(p)


# ============================================================================
# 3. sekmeler: gorunurluk, geri dusme, isaretler
# ============================================================================

def test_sekme_gorunurlugu():
    print("\n[K3] SEKMELER: gorunurluk = uygunluk.gecerli_sekmeler, numarasiz basliklar")
    uyg = _qt()
    if uyg is None:
        return
    from cekirdek import uygunluk
    p = _pencere()
    try:
        kontrol("8 sekme de QTabWidget'ta (dizinler sabit)", p.sekmeler.count() == 8)
        kontrol("sekme sirasi uygunluk.SEKMELER",
                [p._sekme_ix[k] for k in uygunluk.SEKMELER] == list(range(8)))
        adlar = [re.sub(r"\s+[!•✓]$", "", p.sekmeler.tabText(i)) for i in range(8)]
        kontrol("basliklar numarasiz ve Turkce",
                adlar == ["Malzemeler", "Parçalar", "Demet", "Kor", "Hesap ayarları",
                          "Çalıştır", "Analiz", "Tükenme"], "-> %s" % adlar)
        for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
            p.proje_ac(yol)
            beklenen = uygunluk.gecerli_sekmeler(p.spec)
            kontrol("%s: gorunur sekmeler = gecerli_sekmeler" % os.path.basename(yol),
                    _gorunur_anahtarlar(p) == beklenen,
                    "-> %s / %s" % (_gorunur_anahtarlar(p), beklenen))
            kontrol("%s: etkin sekme gorunur" % os.path.basename(yol),
                    p.sekmeler.isTabVisible(p.sekmeler.currentIndex()))

        # etkin sekme gizlenince ILK gorunur sekmeye dusulur
        p.proje_ac(os.path.join(ORNEK, "pwr_17x17.json"))
        p._sekmeye_git("demet")
        kontrol("(on kosul) Demet sekmesi etkin", p._sekme_anahtari() == "demet")
        p.kor_turunu_degistir("tek_cubuk")
        kontrol("tur tek_cubuk: Demet gizli", not p.sekmeler.isTabVisible(p._sekme_ix["demet"]))
        kontrol("gizlenen etkin sekmeden ilk gorunur sekmeye (Malzemeler)",
                p._sekme_anahtari() == "malzemeler", "-> %s" % p._sekme_anahtari())
        p.geri_al()
        kontrol("geri al: Demet sekmesi yeniden gorunur",
                p.sekmeler.isTabVisible(p._sekme_ix["demet"]))

        p._sekmeye_git("tukenme")
        p.spec["ayarlar"]["mod"] = "fixed source"
        p._degisti("ayar")
        kontrol("sabit kaynak: Analiz/Tukenme gizlendi",
                not p.sekmeler.isTabVisible(p._sekme_ix["analiz"])
                and not p.sekmeler.isTabVisible(p._sekme_ix["tukenme"]))
        kontrol("Tukenme'den ilk gorunur sekmeye dusuldu",
                p._sekme_anahtari() == "malzemeler", "-> %s" % p._sekme_anahtari())
        kontrol("gizli sekmeye gidilmiyor",
                p._sekmeye_git("analiz") is False and p._sekme_anahtari() == "malzemeler")
    finally:
        _kapat(p)


def test_sekme_isaretleri():
    print("\n[K4] SEKMELER: isaret kurallari (saf fonksiyon) ve pencerede uygulanisi")
    from cekirdek import sema
    from arayuz.ana_pencere import sekme_isaretleri, sonraki_adim, yer_sekme_anahtari
    bos = sema.yeni_spec("x")
    i = sekme_isaretleri(bos)
    kontrol("bos model: Malzemeler '•'", i["malzemeler"][0] == "•")
    kontrol("bos model (tek_cubuk): Parcalar '•' (cubuk gerekli)", i["parcalar"][0] == "•")
    kontrol("bos model: Kor '•' (dolgu secilmedi)", i["kor"][0] == "•")
    kontrol("hic kosulmadi: Calistir '•'", i["calistir"][0] == "•")
    kontrol("Analiz/Tukenme istege bagli: isaretsiz",
            i["analiz"][0] == "" and i["tukenme"][0] == "")
    kontrol("her aciklama tek cumle ve dolu",
            all(a and a.count(". ") == 0 for _is, a in i.values()),
            "-> %s" % [a for _is, a in i.values() if not a or a.count(". ")])
    s = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    i = sekme_isaretleri(s, {"kor": 2}, kosu_basarili=True, analiz_sonucu=True)
    kontrol("hata onceliklidir: Kor '!' ve aciklamada sayi",
            i["kor"][0] == "!" and "2 hata" in i["kor"][1])
    kontrol("tam model: Malzemeler/Parcalar/Demet/Ayarlar '✓'",
            all(i[k][0] == "✓" for k in ("malzemeler", "parcalar", "demet", "ayarlar")))
    kontrol("kosu basarili: Calistir '✓'; analiz sonucu: Analiz '✓'",
            i["calistir"][0] == "✓" and i["analiz"][0] == "✓")
    s2 = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    s2["demetler"] = []
    kontrol("tek_demet ama kafes yok: Demet '•'", sekme_isaretleri(s2)["demet"][0] == "•")
    s3 = sema.yukle(os.path.join(ORNEK, "mtr_plaka.json"))
    s3["plakalar"] = []
    kontrol("tek_plaka ama plaka yok: Parcalar '•'", sekme_isaretleri(s3)["parcalar"][0] == "•")
    s4 = sema.yukle(os.path.join(ORNEK, "tamburlu_kor.json"))
    kontrol("tamburlu: cubuk/kafes zorunlu degil (✓)",
            sekme_isaretleri(s4)["parcalar"][0] == "✓" and sekme_isaretleri(s4)["demet"][0] == "✓")
    esleme = {"malzeme:uo2": "malzemeler", "malzemeler": "malzemeler",
              "cubuk:x": "parcalar", "plaka:x": "parcalar", "demet:x": "demet",
              "kor": "kor", "kor/katman 1": "kor", "ayarlar": "ayarlar",
              "kaynak": "ayarlar", "tally:aki": "ayarlar", "guc dagilimi": "ayarlar",
              "tukenme/uo2": "tukenme", "bilinmeyen": None}
    kontrol("yer -> sekme anahtari eslemesi",
            all(yer_sekme_anahtari(y) == k for y, k in esleme.items()),
            "-> %s" % {y: yer_sekme_anahtari(y) for y in esleme})
    gorunur = ["malzemeler", "parcalar", "kor", "ayarlar", "calistir"]
    kontrol("durum ipucu: once hata", "Kor sekmesinde hata" in sonraki_adim(
        sekme_isaretleri(s, {"kor": 1}), gorunur))
    kontrol("durum ipucu: sonra eksik adim",
            sonraki_adim(sekme_isaretleri(bos), gorunur).startswith("Sonraki adım: Malzemeler"))
    kontrol("durum ipucu: hazirsa CALISTIR",
            "ÇALIŞTIR (F9)" in sonraki_adim(sekme_isaretleri(s), gorunur))

    uyg = _qt()
    if uyg is None:
        return
    p = _pencere(os.path.join(ORNEK, "pwr_17x17.json"))
    try:
        ix = p._sekme_ix
        kontrol("pencere: Malzemeler basligi '✓' ile bitiyor",
                p.sekmeler.tabText(ix["malzemeler"]).endswith("✓"))
        kontrol("pencere: Calistir basligi '•' (hic kosulmadi)",
                p.sekmeler.tabText(ix["calistir"]).endswith("•"))
        kontrol("pencere: sekme ipucu isareti aciklar",
                "çalıştırılmadı" in p.sekmeler.tabToolTip(ix["calistir"]))
        p.spec["kor"]["demet"] = "yok_boyle_demet"
        p._dogrula(veri=False)
        kontrol("kor hatasi -> Kor basligi '!'", p.sekmeler.tabText(ix["kor"]).endswith("!"),
                "-> %r" % p.sekmeler.tabText(ix["kor"]))
        kontrol("durum cubugu ipucu hatali sekmeyi soyluyor",
                "Kor sekmesinde hata" in p.durum_ipucu.text(), "-> %r" % p.durum_ipucu.text())
    finally:
        _kapat(p)


# ============================================================================
# 4. model basligi ve tur degistirme
# ============================================================================

def test_model_basligi():
    print("\n[K5] MODEL BASLIGI: metin, baglantilar, 'Turu degistir...'")
    from cekirdek import sema, dogrula, uygunluk
    from arayuz.ana_pencere import model_ozet_metni
    beklenen = {
        "pwr_17x17.json": "· 17×17 yakıt demeti · 2B · Özdeğer (k-eff)",
        "pwr_3b.json": "· 17×17 yakıt demeti · 3B · Özdeğer (k-eff)",
        "pwr_eksenel.json": "· 17×17 yakıt demeti · 3B katmanlı · Özdeğer (k-eff)",
        "sfr_altigen.json": "· 7 halkalı altıgen demet · 2B · Özdeğer (k-eff)",
        "mtr_plaka.json": "· plaka elemanı (23 plaka) · 2B · Özdeğer (k-eff)",
        "tamburlu_kor.json": "· tamburlu kor (8 tambur) · 3B · Özdeğer (k-eff)",
        "zirh_kure.json": "· küresel düzenek (2 kabuk) · 3B · Sabit kaynak",
        "pwr_pinhucre.json": "· yakıt çubuğu (pin hücre) · 2B · Özdeğer (k-eff)",
    }
    for dosya, son in beklenen.items():
        s = sema.yukle(os.path.join(ORNEK, dosya))
        metin = model_ozet_metni(s)
        kontrol("%s: '%s'" % (dosya, metin),
                metin.startswith("Model: %s " % s["ad"]) and metin.endswith(son),
                "-> beklenen sonu %r" % son)

    uyg = _qt()
    if uyg is None:
        return
    p = _pencere(os.path.join(ORNEK, "pwr_eksenel.json"))
    try:
        kontrol("pencere basligi saf metinle ayni",
                _duz(p.model_basligi.text()) == model_ozet_metni(p.spec),
                "-> %r" % _duz(p.model_basligi.text()))
        p._sekmeye_git("malzemeler")
        p.model_basligi.linkActivated.emit("mod")
        kontrol("hesap turune tiklamak Hesap ayarlarina goturuyor",
                p._sekme_anahtari() == "ayarlar")
        p.model_basligi.linkActivated.emit("kor")
        kontrol("kor turune tiklamak Kor sekmesine goturuyor", p._sekme_anahtari() == "kor")

        p._tur_menusunu_doldur()
        turler = [e.data() for e in p._tur_menusu.actions()]
        kontrol("tur menusu = uygunluk.kor_turleri (kuresel yok)",
                turler == uygunluk.kor_turleri(p.spec) and "kuresel" not in turler,
                "-> %s" % turler)
        isaretli = [e.data() for e in p._tur_menusu.actions() if e.isChecked()]
        kontrol("gecerli tur isaretli", isaretli == ["tek_demet"])

        p.proje_ac(os.path.join(ORNEK, "pwr_17x17.json"))
        gecmis0 = p._gecmis_ix
        p.kor_turunu_degistir("kare_kafes")
        kor = p.spec["kor"]
        kontrol("kare_kafes: tur yazildi, 1x1 harita demet_17x17",
                kor["tur"] == "kare_kafes" and kor["boyut"] == [1, 1]
                and kor["anahtar"] == {"d": "demet_17x17"} and kor["harita"] == ["d"],
                "-> %s %s %s" % (kor["tur"], kor.get("harita"), kor.get("anahtar")))
        kontrol("kare_kafes: ture ozgu olmayan 'demet' alani temizlendi", kor.get("demet") is None)
        hatalar = [b.mesaj for b in dogrula.tum_kontroller(p.spec, veri_kontrolu=False)
                   if b.seviye == "hata"]
        kontrol("tur degisimi sonrasi model gecerli", not hatalar, "-> %s" % hatalar[:3])
        kontrol("baslik yeni turu gosteriyor", "1×1 tam kor" in _duz(p.model_basligi.text()))
        kontrol("Kor sekmesi turu spec'ten okuyor (tutarli)",
                p.s_kor.tur.currentData() == "kare_kafes")
        kontrol("tur degisimi tek geri al adimi", p._gecmis_ix == gecmis0 + 1)
        p.kor_turunu_degistir("tek_demet")
        kontrol("tek_demet'e donus: demet geri geldi",
                p.spec["kor"]["demet"] == "demet_17x17" and p.spec["kor"]["tur"] == "tek_demet")
        p.kor_turunu_degistir("kare_kafes")
        kontrol("kare_kafes'e tekrar: onceki harita hatirlandi",
                p.spec["kor"]["harita"] == ["d"])
        p.geri_al()
        p.geri_al()
        p.geri_al()
        kontrol("geri al x3: ilk hal (tek_demet, demet_17x17)",
                p.spec["kor"]["tur"] == "tek_demet"
                and p.spec["kor"]["demet"] == "demet_17x17", "-> %s" % p.spec["kor"]["tur"])
        kontrol("gecersiz tur reddediliyor (kuresel)", p.kor_turunu_degistir("kuresel") is False)

        p._kirli = False                 # "kaydedilsin mi?" modal sorusu acilmasin
        p.proje_ac(os.path.join(ORNEK, "godiva_kriter.json"))
        p._tur_menusunu_doldur()
        kontrol("kuresel dosya acilinca menude kuresel var",
                "kuresel" in [e.data() for e in p._tur_menusu.actions()])
    finally:
        _kapat(p)


# ============================================================================
# 5. sag panel, rozet, CALISTIR kapisi
# ============================================================================

def test_sag_panel_ve_rozet():
    print("\n[K6] SAG PANEL yalnizca tasarim sekmelerinde; durum rozeti; kapi")
    uyg = _qt()
    if uyg is None:
        return
    p = _pencere(os.path.join(ORNEK, "pwr_17x17.json"))
    try:
        p.show()
        uyg.processEvents()
        for k in ("malzemeler", "parcalar", "demet", "kor"):
            p._sekmeye_git(k)
            kontrol("%s: onizleme + dogrulama gorunur" % k,
                    p.onizleme.isVisible() and p._dogrulama_kutu.isVisible())
        p._sekmeye_git("ayarlar")
        kontrol("Hesap ayarlari: yalnizca dogrulama",
                not p.onizleme.isVisible() and p._dogrulama_kutu.isVisible())
        for k in ("calistir", "analiz", "tukenme"):
            p._sekmeye_git(k)
            kontrol("%s: sag panel gizli (tam genislik)" % k, not p._sag.isVisible())

        # ONCE CIZ, SONRA CALISTIR
        p.onizleme.cizildi_mi = lambda: False
        izin, mesaj = p._kosu_izni()
        kontrol("cizilmemis geometri: CALISTIR kapali", not izin and "ÇİZ" in mesaj)
        p.onizleme.cizildi_mi = lambda: True
        kontrol("cizilmis ve hatasiz: CALISTIR acik", p._kosu_izni()[0])

        kontrol("rozet: 'Hata yok' (basari)",
                p.durum_rozeti.text() == "Hata yok" and p.durum_rozeti.seviye() == "basari")
        p.spec["kor"]["demet"] = "yok"
        p.spec["malzemeler"][0]["yogunluk"]["deger"] = -1.0
        p._dogrula(veri=False)
        n = sum(1 for b in p._bulgular if b.seviye == "hata")
        kontrol("rozet hata sayisini gosteriyor (%d hata)" % n,
                p.durum_rozeti.text().startswith("%d hata" % n)
                and p.durum_rozeti.seviye() == "hata", "-> %r" % p.durum_rozeti.text())
        kontrol("hata varken CALISTIR kapali", not p._kosu_izni()[0])
        p.durum_rozeti.tiklandi.emit()
        uyg.processEvents()
        kontrol("rozete tiklamak bulgu listesini aciyor",
                p.bulgu_acilir.isVisible() and p.bulgu_acilir.liste.count() == len(p._bulgular))
        satir = [i for i in range(p.bulgu_acilir.liste.count())
                 if p.bulgu_acilir.liste.item(i).data(0x0100) == "kor"]
        p.bulgu_acilir.liste.itemClicked.emit(p.bulgu_acilir.liste.item(satir[0]))
        kontrol("acilir listeden bulgu Kor sekmesine goturuyor ve liste kapaniyor",
                p._sekme_anahtari() == "kor" and not p.bulgu_acilir.isVisible())
    finally:
        _kapat(p)


# ============================================================================
# 6. kaldirilanlar, kisayollar, yardim, minimum yukseklik
# ============================================================================

def test_kaldirilanlar_ve_kisayollar():
    print("\n[K7] KALDIRILANLAR: rehber, Model menusu, F10, ornek/sablon; kisayollar")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtCore, QtGui
    from arayuz import ana_pencere
    p = _pencere(os.path.join(ORNEK, "pwr_pinhucre.json"))
    try:
        for ad in ("rehber", "rehber_git", "_rehber_kutu", "_sonraki_adim",
                   "_rehber_guncelle", "_rehbere_git", "_kisayollar", "_buyut",
                   "_geometri_aciklama", "_sozluk"):
            kontrol("'%s' yok" % ad, not hasattr(p, ad))
        kontrol("SablonDiyalog / SABLONLAR yok",
                not hasattr(ana_pencere, "SablonDiyalog") and not hasattr(ana_pencere, "SABLONLAR"))
        menuler = [a.text().replace("&", "") for a in p.menuBar().actions()]
        kontrol("menu cubugu sade ve Turkce", menuler == ["Dosya", "Düzen", "Görünüm", "Yardım"],
                "-> %s" % menuler)
        metinler = [e.text() for e in p.findChildren(QtGui.QAction)]
        for yasak in ("Pencereyi", "Neden geometri", "Örnek aç", "Ornek ac", "Kısayollar",
                      "Kisayollar"):
            kontrol("'%s' eylemi yok" % yasak, not any(yasak in t for t in metinler))
        kisayol = {}
        for e in p.actions():
            kisayol[e.shortcut().toString()] = e
        for tus in ("F5", "F6", "F9"):
            e = kisayol.get(tus)
            kontrol("%s pencere kisayolu var" % tus,
                    e is not None and e.shortcutContext() == QtCore.Qt.WindowShortcut)
        kontrol("F10 kisayolu yok",
                not any(e.shortcut().toString() == "F10" for e in p.findChildren(QtGui.QAction)))
        kontrol("F9 CALISTIR arac cubugunda", p.e_calistir in p._arac_cubugu.actions())
        d = p._yardim_diyalogu()
        html = d.metin.toPlainText()
        kontrol("yardimda terimler ve kisayollar birlikte",
                "k-eff" in html and "Klavye kısayolları" in html and "F9" in html
                and "F5" in html and "Ctrl+N" in html.replace("Ctrl+N", "Ctrl+N"))
        d.deleteLater()
        kontrol("ice aktarma ipucu geometri notunu tasiyor",
                "geometri" in p.e_ice_aktar.toolTip().lower())
        kontrol("pencere basliginda Turkce uygulama adi",
                p.windowTitle().startswith("OpenMC Reaktör Kuru Arayüzü"))
    finally:
        _kapat(p)


def test_minimum_yukseklik():
    print("\n[K8] PENCERE minimum yuksekligi kucuk ekranlara sigar (<= 320 px)")
    uyg = _qt()
    if uyg is None:
        return
    p = _pencere(os.path.join(ORNEK, "pwr_17x17.json"))
    try:
        p.show()
        uyg.processEvents()
        for k in ("malzemeler", "ayarlar", "calistir"):
            p._sekmeye_git(k)
            uyg.processEvents()
            h = p.minimumSizeHint().height()
            kontrol("%s sekmesinde minimumSizeHint %d px <= 320" % (k, h), h <= 320)
        p.e_yeni.trigger()
        uyg.processEvents()
        h = p.minimumSizeHint().height()
        kontrol("baslangic ekraninda minimumSizeHint %d px <= 320" % h, h <= 320)
    finally:
        _kapat(p)


def test_tema_gecisi():
    print("\n[K9] TEMA: acik <-> koyu gecisi kabugu bozmuyor")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz import tema
    p = _pencere(os.path.join(ORNEK, "pwr_17x17.json"))
    eski = tema.etkin()
    # Uygulama geneli stil sayfasi (tema.uygula) surecteki BUTUN widget'lari
    # yeniden cilalar: onceki testlerin kapali pencereleriyle ~20 s/gecis
    # suruyordu. Burada kabugun tema degisimine TEPKISI sinanir; tema
    # modulunun kendisi yalnizca etkin paleti degistirir. (Gorsel denetim:
    # offscreen ekran goruntuleri, iki tema.)
    gercek_uygula = tema.uygula

    def hafif_uygula(_app, ad=None):
        tema._ETKIN = ad if ad in tema.TEMALAR else "acik"
        return tema._ETKIN
    tema.uygula = hafif_uygula
    try:
        p._tema_degistir("koyu")
        kontrol("koyu tema: menude 'Koyu tema' isaretli",
                p._tema_eylemleri["koyu"].isChecked()
                and not p._tema_eylemleri["acik"].isChecked())
        kontrol("koyu tema: rozet koyu tema rengini kullaniyor",
                tema.renk("basari") in p.durum_rozeti.styleSheet())
        kontrol("koyu tema: baslik baglantisi vurgu rengi",
                tema.renk("vurgu") in p.model_basligi.text())
        p._tema_degistir("acik")
        kontrol("acik tema: rozet acik tema rengini kullaniyor",
                tema.renk("basari") in p.durum_rozeti.styleSheet())
        from arayuz.baslangic import BaslangicEkrani
        tema._ETKIN = "koyu"
        b = BaslangicEkrani()
        kontrol("koyu temada baslangic ekrani kuruluyor", b.kart_dugmesi("pin") is not None)
        b.deleteLater()
    finally:
        tema.uygula = gercek_uygula
        tema._ETKIN = eski
        _kapat(p)


# ============================================================================
# 7. ortak bilesenler
# ============================================================================

def test_ortak_bilesenler():
    print("\n[K10] ORTAK: GelismisBolum, BosDurum, DurumRozeti")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtCore, QtWidgets
    from arayuz.ortak import BosDurum, DurumRozeti, GelismisBolum
    anahtar = "test_%d" % os.getpid()
    g = GelismisBolum(anahtar)
    g.ekle(QtWidgets.QLabel("icerik"))
    kontrol("Gelismis varsayilan KAPALI", not g.acik_mi() and g.icerik.isHidden())
    kontrol("kapaliyken ok isareti '▸' ve baslik 'Gelişmiş'", g.dugme.text() == "▸  Gelişmiş")
    sinyal = []
    g.acildi.connect(sinyal.append)
    g.dugme.click()
    kontrol("tiklayinca aciliyor, ok '▾', sinyal",
            g.acik_mi() and not g.icerik.isHidden() and g.dugme.text().startswith("▾")
            and sinyal == [True])
    g2 = GelismisBolum(anahtar)
    kontrol("durum anahtar basina hatirlaniyor (yeni ornek ACIK)", g2.acik_mi())
    g3 = GelismisBolum(anahtar + "_baska")
    kontrol("baska anahtar bagimsiz (KAPALI)", not g3.acik_mi())
    g2.ac(False)
    kontrol("kapatma da hatirlaniyor", not GelismisBolum(anahtar).acik_mi())
    g4 = GelismisBolum(None)
    g4.ac(True)
    kontrol("anahtarsiz bolum hatirlanmiyor", not GelismisBolum(None).acik_mi())

    gercek = QtCore.QSettings

    class _Bozuk:
        def __init__(self, *a, **k):
            raise RuntimeError("ayar yok")
    QtCore.QSettings = _Bozuk
    try:
        try:
            gb = GelismisBolum("bozuk_ayar")
            gb.dugme.click()
            kontrol("QSettings kullanilamazsa da calisiyor (kapali baslar, acilir)",
                    gb.acik_mi())
        except Exception as e:
            kontrol("QSettings kullanilamazsa da calisiyor", False, "-> %s" % e)
    finally:
        QtCore.QSettings = gercek

    b = BosDurum("Henüz malzeme yok", "Yakıt, zarf ve soğutucu ekleyin.", "Kütüphaneden ekle…")
    tik = []
    b.eylem.connect(lambda: tik.append(1))
    b.dugme.click()
    kontrol("BosDurum: birincil dugme eylem yayiyor", tik == [1]
            and b.dugme.objectName() == "birincil")
    b.ayarla(dugme_metni="")
    kontrol("BosDurum: dugmesiz kullanim", b.dugme.isHidden())

    r = DurumRozeti("2 hata", "hata", tiklanabilir=True)
    t = []
    r.tiklandi.connect(lambda: t.append(1))
    from PySide6 import QtGui
    olay = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, QtCore.QPointF(3, 3),
                             QtCore.QPointF(3, 3), QtCore.Qt.LeftButton,
                             QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
    QtWidgets.QApplication.sendEvent(r, olay)
    kontrol("DurumRozeti tiklanabilir", t == [1])
    r.ayarla("Tamam", "basari")
    kontrol("DurumRozeti seviye/metin", r.text() == "Tamam" and r.seviye() == "basari")
    r.ayarla("x", "gecersiz")
    kontrol("DurumRozeti bilinmeyen seviye -> notr", r.seviye() == "notr")
    uyg  # noqa: B018


# ============================================================================
# 8. izgara: saf yardimcilar ve boyama
# ============================================================================

def _ornek_haritalari():
    """(etiket, harita, anahtar) -- orneklerdeki butun kafes/kor haritalari."""
    from cekirdek import sema
    sonuc = []
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        s = sema.yukle(yol)
        ad = os.path.basename(yol)
        for d in s.get("demetler", []):
            sonuc.append(("%s/%s (%s)" % (ad, d["ad"], d.get("tur", "kare")),
                          d["harita"], d["anahtar"]))
        if s["kor"].get("tur") == "kare_kafes":
            sonuc.append(("%s/kor" % ad, s["kor"]["harita"], s["kor"]["anahtar"]))
    return sonuc


def test_izgara_yardimcilari():
    print("\n[K11] IZGARA: harita_adlara / adlardan_harita gidis-donus")
    from arayuz import baslangic
    from arayuz.izgara import (BOS_HARF, adlardan_harita, harita_adlara, palet_ogeleri)
    from cekirdek import sema
    haritalar = _ornek_haritalari()
    t = baslangic.bos_sablon("tam_kor")
    haritalar.append(("sablon tam_kor/kor", t["kor"]["harita"], t["kor"]["anahtar"]))
    # sentetik kare_kafes kor haritasi: iki demet + su kosesi (ornek yok)
    haritalar.append(("sentetik kare_kafes/kor", ["sAAs", "ABBA", "ABBA", "sAAs"],
                      {"A": "demet_17x17", "B": "demet_blanket", "s": "su"}))
    kontrol("ornek haritalari bulundu (kare + altigen)",
            any("altigen" in e for e, _h, _a in haritalar) and len(haritalar) >= 8,
            "-> %d" % len(haritalar))
    for etiket, harita, anahtar in haritalar:
        adlar = harita_adlara(harita, anahtar)
        h2, a2 = adlardan_harita(adlar, anahtar, harita)
        kontrol("birebir gidis-donus: %s" % etiket, h2 == harita and a2 == anahtar,
                "-> %s" % ([x for x in zip(h2, harita) if x[0] != x[1]][:2],))
        h3, a3 = adlardan_harita(adlar, anahtar)
        kontrol("konumsuz: adlar korunuyor, harfler anahtardan: %s" % etiket,
                harita_adlara(h3, a3) == adlar and a3 == anahtar)
        h4, a4 = adlardan_harita(adlar)
        kontrol("sifirdan: adlar korunuyor: %s" % etiket, harita_adlara(h4, a4) == adlar)
    s = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    d = s["demetler"][0]
    adlar = harita_adlara(d["harita"], d["anahtar"])
    h, a = adlardan_harita(adlar)
    kontrol("sifirdan harfler anlamli ve deterministik (y=yakit, k=kilavuz)",
            a == {"y": "yakit_cubugu", "k": "kilavuz_boru"}
            and adlardan_harita(adlar) == (h, a))
    adlar[0][0] = "kontrol_cubugu"
    h5, a5 = adlardan_harita(adlar, d["anahtar"], d["harita"])
    kontrol("yeni parca yeni harf alir, eski harfler KORUNUR",
            a5 == dict(d["anahtar"], **{"K": "kontrol_cubugu"})
            and h5[0][0] == "K" and h5[1:] == d["harita"][1:] and h5[0][1:] == d["harita"][0][1:],
            "-> %s %r" % (a5, h5[0][:3]))
    h6, a6 = adlardan_harita([["y_a", None], ["y_b", "y_a"]])
    kontrol("tanimsiz hucre BOS_HARF, cakisan ilk harf -> buyuk harf",
            h6 == ["y%s" % BOS_HARF, "Yy"] and a6 == {"y": "y_a", "Y": "y_b"}, "-> %s %s" % (h6, a6))
    try:
        adlardan_harita([["p%d" % i for i in range(70)]])
        kontrol("62'den fazla parca ValueError", False)
    except ValueError:
        kontrol("62'den fazla parca ValueError", True)

    ogeler = palet_ogeleri(s)
    adlar_p = [o[0] for o in ogeler]
    kontrol("palet: cubuk, kafes, malzeme ve bosluk girdileri",
            "yakit_cubugu" in adlar_p and "demet_17x17" in adlar_p and "su" in adlar_p
            and "bosluk" in adlar_p)
    from arayuz.izgara import _mesafe
    ayrik = all(_mesafe(x[2], y[2]) >= 60 for i, x in enumerate(ogeler) for y in ogeler[i + 1:])
    kontrol("palet renkleri birbirinden ayirt edilebilir", ayrik)
    kontrol("yakit cubugu yakit (uo2) renginde", dict((o[0], o[2]) for o in ogeler)
            ["yakit_cubugu"] == (222, 93, 40))
    kontrol("haric tutulan listelenmiyor",
            "demet_17x17" not in [o[0] for o in palet_ogeleri(s, haric=("demet_17x17",))])


def _fare(w, tur, nokta, dugme, dugmeler):
    from PySide6 import QtCore, QtGui, QtWidgets
    olay = QtGui.QMouseEvent(tur, QtCore.QPointF(nokta), w.mapToGlobal(QtCore.QPointF(nokta)),
                             dugme, dugmeler, QtCore.Qt.NoModifier)
    QtWidgets.QApplication.sendEvent(w, olay)


def test_izgara_boyama():
    print("\n[K12] IZGARA: tikla-surukle boyama (sentetik fare olaylari), palet")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtCore
    from arayuz.izgara import AltigenIzgara, KareIzgara, ParcaPaleti
    from cekirdek import altigen
    L, N = QtCore.Qt.LeftButton, QtCore.Qt.NoButton
    E = QtCore.QEvent

    # --- palet ---
    pal = ParcaPaleti()
    secilen = []
    pal.secildi.connect(secilen.append)
    pal.parcalari_ayarla([("yakit", "yakıt çubuğu", (222, 93, 40), "çubuk"),
                          ("kilavuz", "kılavuz boru", (90, 150, 220)),
                          ("su", "su", (60, 120, 200))])
    kontrol("palet ilk parcayi secer ve bildirir", pal.secili() == "yakit" and secilen == ["yakit"])
    pal.sec("kilavuz")
    kontrol("secim degisince secildi(ad)", secilen[-1] == "kilavuz")
    pal.parcalari_ayarla([("su", "su", (60, 120, 200)), ("kilavuz", "k", (90, 150, 220))])
    kontrol("yeniden doldurmada secim korunur", pal.secili() == "kilavuz")
    kontrol("renkler QColor olarak", pal.renkler()["su"].blue() == 200)

    # --- kare ---
    k = KareIzgara()
    k.resize(300, 300)
    k.yukle([["y"] * 5 for _ in range(5)], {"y": (222, 93, 40), "k": (90, 150, 220)})
    pal.secildi.connect(k.firca_ayarla)
    k.firca_ayarla("k")
    sayac = []
    k.degisti.connect(lambda: sayac.append(1))
    p0, p4 = k.hucre_merkezi((0, 0)), k.hucre_merkezi((0, 4))
    _fare(k, E.MouseButtonPress, p0, L, L)
    _fare(k, E.MouseMove, p4, N, L)          # tek hizli hareket: araya giren hucreler de
    _fare(k, E.MouseButtonRelease, p4, L, N)
    kontrol("surukleme ilk satiri boyadi (atlama yok)", k.adlar()[0] == ["k"] * 5,
            "-> %s" % k.adlar()[0])
    kontrol("diger satirlar degismedi", all(r == ["y"] * 5 for r in k.adlar()[1:]))
    kontrol("bir darbe = bir degisti", sayac == [1], "-> %s" % sayac)
    _fare(k, E.MouseMove, k.hucre_merkezi((2, 2)), N, N)     # basmadan gezinme
    kontrol("basmadan gezinme boyamiyor", k.adlar()[2][2] == "y" and sayac == [1])
    _fare(k, E.MouseButtonPress, p0, L, L)
    _fare(k, E.MouseButtonRelease, p0, L, N)
    kontrol("ayni parcayla boyamak degisti yaymiyor", sayac == [1])
    iste = []
    k.firca_istendi.connect(iste.append)
    _fare(k, E.MouseButtonPress, k.hucre_merkezi((3, 3)), QtCore.Qt.RightButton,
          QtCore.Qt.RightButton)
    kontrol("sag tik hucrenin parcasini firca olarak istiyor", iste == ["y"])
    _fare(k, E.MouseButtonPress, QtCore.QPointF(1, 1), L, L)
    _fare(k, E.MouseButtonRelease, QtCore.QPointF(1, 1), L, N)
    kontrol("izgara disina tiklamak bir sey yapmiyor", sayac == [1])
    k.resize(600, 200)
    kontrol("boyuta olcekleniyor (kare hucre, ortalanmis)",
            abs(k.hucre_merkezi((0, 0)).x() - (300 - 2 * k._olcek)) < 1.0
            and k._olcek <= 200 / 5.0)
    k.etiketleri_goster(True)
    k.grab()                                     # etiketli cizim hata vermemeli
    kontrol("etiketli cizim calisiyor", True)

    # --- altigen ---
    a = AltigenIzgara()
    a.resize(320, 320)
    halka = 3
    adlar = [["y"] * u for u in altigen.halka_uzunluklari(halka)]
    a.yukle(adlar, halka, "y", {"y": (222, 93, 40), "e": (40, 40, 40)})
    kontrol("altigen hucre sayisi = altigen.toplam_hucre",
            len(a._geometri()) == altigen.toplam_hucre(halka))
    konum = altigen.konumlar(halka, "y")
    m00 = a.hucre_merkezi((0, 0))
    kontrol("altigen ilk hucre TEPEDE (OpenMC duzeni)",
            abs(konum[(0, 0)][0]) < 1e-9 and abs(m00.x() - a.width() / 2.0) < 0.5
            and m00.y() < a.height() / 2.0, "-> %s %s" % (konum[(0, 0)], m00))
    a.firca_ayarla("e")
    say = []
    a.degisti.connect(lambda: say.append(1))
    _fare(a, E.MouseButtonPress, a.hucre_merkezi((0, 0)), L, L)
    _fare(a, E.MouseMove, a.hucre_merkezi((0, 1)), N, L)
    _fare(a, E.MouseMove, a.hucre_merkezi((0, 2)), N, L)
    _fare(a, E.MouseButtonRelease, a.hucre_merkezi((0, 2)), L, N)
    kontrol("altigen surukleme dis halkada 3 hucre boyadi",
            a.adlar()[0][:3] == ["e", "e", "e"] and a.adlar()[0][3:] == ["y"] * 9,
            "-> %s" % a.adlar()[0])
    kontrol("altigen: bir darbe = bir degisti", say == [1])
    a.halkayi_doldur(2, "e")
    kontrol("merkez halkayi doldurma", a.adlar()[2] == ["e"] and say == [1, 1])
    a.yukle(adlar, halka, "x")
    kontrol("x yoneliminde ilk hucre SAGDA",
            a.hucre_merkezi((0, 0)).x() > a.width() / 2.0 + 10)
    a.yukle([], 0)
    a.grab()
    kontrol("bos altigen izgara cizimi calisiyor", a._geometri() == [])


HIZLI = [test_bos_sablonlar, test_baslangic_ekrani, test_sekme_gorunurlugu,
         test_sekme_isaretleri, test_model_basligi, test_sag_panel_ve_rozet,
         test_kaldirilanlar_ve_kisayollar, test_minimum_yukseklik, test_tema_gecisi,
         test_ortak_bilesenler, test_izgara_yardimcilari, test_izgara_boyama]
YAVAS = []


if __name__ == "__main__":
    from testler.ortak_test import _gecti, _kaldi
    for fn in HIZLI:
        fn()
    print("\n SONUC: %d gecti, %d kaldi" % (len(_gecti), len(_kaldi)))
    for t in _kaldi:
        print("   - %s" % t)
