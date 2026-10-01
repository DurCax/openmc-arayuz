# -*- coding: utf-8 -*-
"""
test_butunlesme.py -- Dalga 3 birlestirmesinde koordinatorun yaptigi
duzeltmeler: betik ureticinin anlamsal esdegerligi ve degisken adlari,
secilmemis malzemenin dogrulanmasi, yeni modellerde otomatik entropi agi,
uygunluk'a tasinan kurallar, okunur ipucu rengi.
"""

import copy
import importlib.util
import math
import os
import random
import re
import tempfile
import warnings

from testler.ortak_test import kontrol, ORNEK

warnings.filterwarnings("ignore")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_ORNEKLER = sorted(f[:-5] for f in os.listdir(ORNEK) if f.endswith(".json"))


def _yukle(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


# ---------------------------------------------------------------------------
# betik (kod_uret) ile kurucu ANLAMSAL olarak ayni modeli mi kuruyor?
# Hucre/yuzey kimlikleri olusturma sirasina gore degistigi icin XML metni
# karsilastirilamaz; geometri noktada ORNEKLENIR (Geometry.find, openmc.lib
# gerekmez), malzeme ve ayar XML'i dogrudan karsilastirilir.
# ---------------------------------------------------------------------------
def _betik_modeli(spec):
    from cekirdek import kod_uret
    d = tempfile.mkdtemp(prefix="butunlesme_")
    yol = os.path.join(d, "model.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kod_uret.uret(copy.deepcopy(spec), "model.py"))
    eski = os.getcwd()
    os.chdir(d)
    try:
        sm = importlib.util.spec_from_file_location("betik_%d" % random.randrange(1 << 30), yol)
        mod = importlib.util.module_from_spec(sm)
        sm.loader.exec_module(mod)
        return mod.model
    finally:
        os.chdir(eski)


def _malzeme_at(geom, p):
    import openmc
    try:
        yol = geom.find(p)
    except Exception:
        return "HATA"
    if not yol:
        return "DISARI"
    f = yol[-1].fill
    if f is None:
        return "void"
    if isinstance(f, openmc.Material):
        return (f.name, round(f.density, 10), f.temperature)
    return "?" + type(f).__name__


def _xml(nesne, dosya):
    d = tempfile.mkdtemp(prefix="butunlesme_xml_")
    nesne.export_to_xml(d)
    with open(os.path.join(d, dosya), encoding="utf-8") as f:
        # tukenme hacmi betikte malzemeye, arayuzde tukenme.hazirla'da yazilir
        return re.sub(r' volume="[^"]*"', "", f.read())


def anlamsal_fark(spec, n=400, tohum=1):
    """Kurucu ile betik arasindaki farklar (bos liste = ayni)."""
    import openmc
    from cekirdek import kurucu
    openmc.reset_auto_ids()
    a = kurucu.kur(copy.deepcopy(spec))[0]
    openmc.reset_auto_ids()
    try:
        b = _betik_modeli(spec)
    except Exception as e:
        return ["betik calismadi: %s: %s" % (type(e).__name__, e)]
    sorun = []
    if _xml(a.materials, "materials.xml") != _xml(b.materials, "materials.xml"):
        sorun.append("malzemeler")
    if _xml(a.settings, "settings.xml") != _xml(b.settings, "settings.xml"):
        sorun.append("ayarlar")
    ta = sorted(t.name for t in (a.tallies or []))
    tb = sorted(t.name for t in (b.tallies or []))
    if ta != tb:
        sorun.append("tally adlari %s / %s" % (ta, tb))
    ll, ur = a.geometry.bounding_box
    lo = [x if math.isfinite(x) else -1.0 for x in ll]
    hi = [x if math.isfinite(x) else 1.0 for x in ur]
    r = random.Random(tohum)
    farkli = 0
    for _ in range(n):
        p = tuple(r.uniform(lo[i], hi[i]) * 0.999 for i in range(3))
        if _malzeme_at(a.geometry, p) != _malzeme_at(b.geometry, p):
            farkli += 1
    if farkli:
        sorun.append("geometri: %d/%d noktada farkli malzeme" % (farkli, n))
    return sorun


def test_betik_anlamsal_esdegerlik():
    print("\n[B1] BETIK: 11 ornekte kurucu ile ayni malzeme, ayar, tally ve geometri")
    for ad in _ORNEKLER:
        sorun = anlamsal_fark(_yukle(ad))
        kontrol("betik = kurucu: %s" % ad, not sorun, "-> %s" % "; ".join(sorun))


def test_betik_ad_cakismalari():
    """Eskiden: 'a b'/'a_b' iki malzemeyi karistiriyordu (4/400 noktada
    farkli malzeme); 'class', 'None', 'openmc', 'malzemeler' betigi
    calistirmiyordu."""
    print("\n[B2] BETIK: spec adlari betik degiskenleriyle cakismiyor")
    from cekirdek import sema
    from arayuz.sekme_cubuk import parca_adini_degistir
    taban = _yukle("pwr_17x17")

    s = copy.deepcopy(taban)
    sema.malzeme_adini_degistir(s, "su", "a b")
    sema.malzeme_adini_degistir(s, "helyum", "a_b")
    sorun = anlamsal_fark(s)
    kontrol("'a b' ve 'a_b' malzemeleri ayri degisken", not sorun, "-> %s" % sorun)

    for ad in ("class", "None", "openmc", "malzemeler", "model", "geometri", "ayar"):
        s = copy.deepcopy(taban)
        sema.malzeme_adini_degistir(s, "su", ad)
        sorun = anlamsal_fark(s, n=150)
        kontrol("'%s' adli malzeme betigi bozmuyor" % ad, not sorun, "-> %s" % sorun)

    # eski dosya: cubuk malzemeyle ayni adli. parca_adini_degistir artik
    # cakisan adi reddeder (geometri.ad_degistir ValueError); dosya metinden kurulur.
    import json
    s = copy.deepcopy(taban)
    try:
        parca_adini_degistir(copy.deepcopy(s), s["cubuklar"][0]["ad"], "uo2")
        reddetti = False
    except ValueError:
        reddetti = True
    kontrol("malzemeyle cakisan cubuk adi reddedilir", reddetti)
    s = json.loads(json.dumps(s).replace('"%s"' % s["cubuklar"][0]["ad"], '"uo2"'))
    kontrol("cubuk ile malzeme ayni adli (eski dosya) -> betik ayni",
            not anlamsal_fark(s, n=150))

    s = copy.deepcopy(taban)
    d = s["demetler"][0]
    harf = sorted(d["anahtar"])[0]
    d["anahtar"][harf] = "su"          # malzeme dogrudan kafes dolgusu (u_ sarmalayici)
    kontrol("malzeme kafes dolgusu olunca malzeme degiskeni ezilmiyor",
            not anlamsal_fark(s, n=200))

    from cekirdek import kod_uret
    metin = kod_uret.uret(taban)
    kontrol("betik degiskenleri ture gore onekli (m_uo2, c_..., d_...)",
            "m_uo2 = openmc.Material" in metin and re.search(r"^c_\w+ = ", metin, re.M)
            and re.search(r"^d_\w+ = openmc\.RectLattice", metin, re.M))


def test_dogrula_secilmemis_malzeme():
    """Kurucu None malzemeyi SESSIZCE void kurar; dogrulama soylemeli."""
    print("\n[B3] DOGRULAMA: secilmemis bolge/plaka malzemesi, tur/birim")
    from cekirdek import dogrula

    def hatalar(s, seviye="hata"):
        return [b.mesaj for b in dogrula.tum_kontroller(s, veri_kontrolu=False) if b.seviye == seviye]

    for ad in _ORNEKLER:
        s = _yukle(ad)
        yeni = [m for m in hatalar(s) + hatalar(s, "uyari")
                if "seçilmemiş" in m or "geçersiz: " in m]
        kontrol("ornek '%s' yeni kontrollerden bulgu almiyor" % ad, not yeni, "-> %s" % yeni)

    s = _yukle("pwr_pinhucre")
    s["cubuklar"][0]["bolgeler"][1]["malzeme"] = None
    kontrol("None cubuk bolgesi -> hata",
            any("2. bölgenin malzemesi seçilmemiş" in m for m in hatalar(s)))

    s = _yukle("mtr_plaka")
    s["plakalar"][0]["zarf_malzeme"] = None
    kontrol("None plaka zarfi -> hata", any("zarf malzemesi seçilmemiş" in m for m in hatalar(s)))

    s = _yukle("pwr_kontrol")
    c = [c for c in s["cubuklar"] if c.get("tur") == "kontrol"][0]
    c["izleyici_malzeme"] = None
    kontrol("None izleyici -> uyari",
            any("izleyici malzeme seçilmemiş" in m for m in hatalar(s, "uyari")))

    s = _yukle("pwr_pinhucre")
    s["malzemeler"][0]["bilesim"][0]["tur"] = "nuclide"
    s["malzemeler"][0]["bilesim"][-1]["birim"] = "atom"
    h = hatalar(s)
    kontrol("bilesimde tur 'nuclide' -> hata", any("türü geçersiz" in m for m in h))
    kontrol("bilesimde birim 'atom' -> hata", any("birimi geçersiz" in m for m in h))


def test_entropi_otomatik():
    """Yeni modelde entropi agi modelden turetilir; eski dosya aynen."""
    print("\n[B4] ENTROPI AGI: yeni modelde otomatik, eski dosyada dosyadaki")
    from cekirdek import kaynak, kurucu, sema
    from arayuz import baslangic
    kontrol("yeni_spec otomatik", sema.yeni_spec()["ayarlar"]["entropi_mesh"].get("otomatik"))
    for k in ("pin", "demet_kare", "tamburlu"):
        s = baslangic.bos_sablon(k)
        kontrol("bos sablon '%s' otomatik" % k, s["ayarlar"]["entropi_mesh"].get("otomatik"))

    s = baslangic.bos_sablon("pin")
    kontrol("2B pin: [8,8,1]", kaynak.entropi_boyutu(s) == [8, 8, 1])
    s["kor"]["yukseklik"] = 100.0
    beklenen = [8, 8, 8]
    m = kurucu.kur(s)[0]
    kontrol("3B'ye gecince kurucu entropi agi %s" % beklenen,
            list(m.settings.entropy_mesh.dimension) == beklenen,
            "-> %s" % list(m.settings.entropy_mesh.dimension))
    kontrol("betik de ayni agi kuruyor", not anlamsal_fark(s, n=50))

    for ad in _ORNEKLER:
        s = _yukle(ad)
        e = s["ayarlar"].get("entropi_mesh") or {}
        if e.get("var"):
            kontrol("ornek '%s': dosyadaki boyut aynen" % ad,
                    "otomatik" not in e and kaynak.entropi_boyutu(s) == list(e["boyut"]))


def test_uygunluk_tasinan_kurallar():
    print("\n[B5] UYGUNLUK: demet tipleri, cubuk cubuk yanma, katman dolgusu")
    from cekirdek import uygunluk
    from arayuz.sekme_demet import demet_turleri
    s = _yukle("pwr_17x17")
    t = uygunluk.parca_turleri(s)
    kontrol("tek demet: kare ve altigen demet eklenebilir",
            t["demet_kare"] and t["demet_altigen"] and demet_turleri(s) == ("kare", "altigen"))
    from arayuz import baslangic
    s = baslangic.bos_sablon("tam_kor")
    t = uygunluk.parca_turleri(s)
    kontrol("tam kor: yalniz kare demet", t["demet_kare"] and not t["demet_altigen"]
            and demet_turleri(s) == ("kare",))
    s = _yukle("pwr_pinhucre")
    t = uygunluk.parca_turleri(s)
    kontrol("pin hucre: demet eklenmez", not t["demet_kare"] and not t["demet_altigen"])

    for ad, beklenen in (("pwr_pinhucre", False), ("godiva_kriter", False),
                         ("pwr_17x17", True), ("mtr_plaka", True)):
        kontrol("cubuk cubuk yanma anlamli: %s -> %s" % (ad, beklenen),
                uygunluk.tukenme_ayirma_anlamli(_yukle(ad)) is beklenen)

    kontrol("katman dolgusu: tam korda yalniz malzeme",
            uygunluk.katman_dolgu_turleri(baslangic.bos_sablon("tam_kor")) == ("malzeme",))
    kontrol("katman dolgusu: pin hucrede cubuk + malzeme",
            uygunluk.katman_dolgu_turleri(_yukle("pwr_pinhucre")) == ("cubuk", "malzeme"))


def test_ipucu_okunur():
    """ipucu() palette(mid) (bir KENAR rengi, ~1.3:1) kullaniyordu."""
    print("\n[B6] IPUCU METNI: temanin soluk metin rengi")
    try:
        from PySide6 import QtWidgets
    except Exception:
        return
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz import ortak
    e = ortak.ipucu("deneme")
    kontrol("ipucu objectName 'soluk', ozel stil yok",
            e.objectName() == "soluk" and "palette(mid)" not in e.styleSheet())


def test_u3si2_yogunlugu():
    """U3Si2-Al yogunlugu U yuklemesinden (eski sabit 5.4 g/cm3 4.8 gU/cm3
    yuklemeyle tutarsizdi: Al payi %4'e dusuyordu)."""
    print("\n[B7] U3Si2-Al: yogunluk yuklemeden hesaplaniyor")
    from cekirdek import malzeme_kutup as mk
    m = mk.u3si2_al()
    rho = m["yogunluk"]["deger"]
    b = {x["isim"]: x["miktar"] for x in m["bilesim"]}
    kontrol("4.8 gU/cm3, gozeneksiz -> ~6.73 g/cm3", abs(rho - 6.7316) < 1e-3, "-> %.4f" % rho)
    kontrol("geri hesaplanan U kutle yogunlugu = yukleme",
            abs(rho * b["U"] / 100.0 - 4.8) < 1e-9, "-> %.9f" % (rho * b["U"] / 100.0))
    kontrol("Al agirlikca payi makul (%20-%30)", 20.0 < b["Al"] < 30.0, "-> %.2f" % b["Al"])
    kontrol("%5 gozeneklilik yogunlugu 0.05*2.70 dusurur",
            abs(mk.u3si2_yogunlugu(4.8, 0.0) - mk.u3si2_yogunlugu(4.8, 0.05) - 0.135) < 1e-9)
    try:
        mk.u3si2_yogunlugu(9.0, 0.3)
        kontrol("Al'a yer kalmayan yukleme reddediliyor", False)
    except ValueError:
        kontrol("Al'a yer kalmayan yukleme reddediliyor", True)
    kontrol("elle verilen yogunluk aynen (eski kayitlar)",
            mk.u3si2_al(yogunluk=5.4)["yogunluk"]["deger"] == 5.4)
    adlar = [x["ad"] for x in mk.parametreler("u3si2_al")]
    kontrol("formda gozeneklilik var, yogunluk sorulmuyor",
            "gozeneklilik" in adlar and "yogunluk" not in adlar, "-> %s" % adlar)
    kontrol("varsayilanda tutarlilik uyarisi yok", mk.parametre_uyarilari("u3si2_al", {}) == [])


def test_ornek_aciklamalari_turkce():
    print("\n[B8] ORNEKLER: malzeme aciklamalari ve katman adlari Turkce, birim g/cm3")
    for ad in _ORNEKLER:
        s = _yukle(ad)
        metin = " ".join([m.get("gorunen_ad") or "" for m in s["malzemeler"]] +
                         [b.get("ad") or "" for b in ((s["kor"].get("eksenel") or {}).get("bolgeler") or [])])
        kotu = [k for k in ("g/cc", "dogal", "kilif", "yansitici", "yakit", "blanket") if k in metin]
        kontrol("ornek '%s' aciklamalari" % ad, not kotu, "-> %s" % kotu)


def test_sonsuz_ortam_etiketi():
    """Butun dis sinirlar yansiticiyken sonuc k∞'dur; "Kritik ustu — guc
    artar" demek yanlistir (Ajan 9 bulgusu, pin hucrede kirmizi yaziyordu)."""
    print("\n[B9] SONUC: yansitici sinirli modelde k∞, kritiklik hukmu yok")
    from cekirdek import uygunluk, kosucu
    beklenen = {"pwr_pinhucre": True, "pwr_17x17": True, "sfr_altigen": True,
                "mtr_plaka": True, "pwr_3b": False, "pwr_eksenel": False,
                "godiva_kriter": False, "tamburlu_kor": False}
    for ad, b in beklenen.items():
        kontrol("sonsuz_ortam(%s) = %s" % (ad, b), uygunluk.sonsuz_ortam(_yukle(ad)) is b)
    d, a = kosucu.keff_yorumu(1.35, 0.001, sonsuz=True)
    kontrol("k∞ yorumunda 'Kritik üstü' yok, 'k∞' var", "üstü" not in d and "k∞" in d, d)
    kontrol("sonlu modelde hukum aynen", "Kritik üstü" in kosucu.keff_yorumu(1.05, 0.001)[0])
    try:
        from PySide6 import QtWidgets
    except Exception:
        return
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.sekme_calistir import CalistirSekmesi
    for ad, baslik in (("pwr_pinhucre", "k∞"), ("pwr_3b", "k-eff")):
        w = CalistirSekmesi()
        w.spec_ayarla(_yukle(ad), None)
        w._sonuc_goster({"keff": (1.35, 0.001), "cevrim": 10, "pasif": 5, "parcacik": 100,
                         "entropi": None, "tallyler": {}}, None)
        kontrol("%s sonuc kartinda baslik '%s'" % (ad, baslik), w.keff_baslik.text() == baslik,
                "-> %s / %s" % (w.keff_baslik.text(), w.durum_etiket.text()[:40]))


def test_sablon_malzemeleri_parametrik():
    """Bos sablon malzemeleri kutuphaneden (Duzenle zenginlik/sicaklik sorar),
    sicakliklar tutarli; elle malzemede aciklama duzenlenebilir (Ajan 9 K1-K3)."""
    print("\n[B10] SABLONLAR: parametrik malzeme, tutarli sicaklik; elle aciklama")
    try:
        from PySide6 import QtWidgets
    except Exception:
        return
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz import baslangic
    from arayuz import sekme_malzeme as sm
    from cekirdek import malzeme_kutup as mk
    for k in ("pin", "demet_kare", "demet_altigen", "plaka", "tamburlu", "tam_kor"):
        s = baslangic.bos_sablon(k)
        kontrol("sablon '%s': butun malzemeler parametrik" % k,
                all(mk.parametrik_mi(m) for m in s["malzemeler"]))
        kontrol("sablon '%s': Normal hassasiyet" % k,
                (s["ayarlar"]["parcacik"], s["ayarlar"]["cevrim"], s["ayarlar"]["pasif"])
                == (10000, 150, 40))
    s = baslangic.bos_sablon("pin")
    t = {m["ad"]: m["sicaklik"] for m in s["malzemeler"]}
    kontrol("pin sablonu sicak kosul: yakit 900, zarf 600, su 580 K",
            t == {"uo2": 900.0, "zirkaloy": 600.0, "su": 580.0}, "-> %s" % t)
    uo2 = [m for m in s["malzemeler"] if m["ad"] == "uo2"][0]
    d = sm.MalzemeDiyalog(uo2, s)
    kontrol("sablon UO2'yi Duzenle -> parametre formu (zenginlik alani var)",
            d.parametrik_kip() and "zenginlik" in d.form.alanlar)
    elle = {"ad": "yakit", "gorunen_ad": "UO2 %3.0", "yogunluk": {"birim": "g/cm3", "deger": 10.4},
            "sicaklik": 900.0, "bilesim": [{"tur": "element", "isim": "U", "miktar": 1.0,
                                            "birim": "ao", "zenginlik": 3.0},
                                           {"tur": "element", "isim": "O", "miktar": 2.0,
                                            "birim": "ao"}], "sab": []}
    d = sm.MalzemeDiyalog(elle, s)
    kontrol("elle malzemede aciklama alani dolu", d.aciklama.text() == "UO2 %3.0")
    d.aciklama.setText("UO2 %4.0")
    kontrol("aciklama degisince sonuca yaziliyor", d.sonuc()["gorunen_ad"] == "UO2 %4.0")


def test_tukenme_dizin_yarim_adim():
    """Tukenme: sonuc dizini gosterilir (K12), yarim kosu 'bu modele ait'
    denmez (K11), gecersiz adim sessizce atilmaz; kaydedilmemis projenin
    kosulari ~/openmc_kosular altina yazilir (calisma dizinine degil)."""
    print("\n[B11] TUKENME: dizin, yarim kosu, adim dogrulamasi; kosu tabani")
    import json
    import tempfile
    import time
    from cekirdek import sema, tukenme
    kontrol("kaydedilmemis proje: kosu tabani ~/openmc_kosular",
            sema.kosu_tabani(None) == os.path.join(os.path.expanduser("~"), "openmc_kosular"))
    kontrol("kayitli proje: kosu tabani projenin dizini",
            sema.kosu_tabani("/a/b/model.json") == "/a/b")
    try:
        from PySide6 import QtWidgets
    except Exception:
        return
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.sekme_tukenme import TukenmeSekmesi
    d = tempfile.mkdtemp(prefix="butunlesme_tuk_")
    spec = _yukle("pwr_tukenme")
    spec["calistirma"]["dizin"] = os.path.join(d, "kosu")
    w = TukenmeSekmesi()
    w.proje_ayarla(None)
    w.spec_yukle(spec)
    kontrol("sonuc yokken yazilacagi dizin soyleniyor",
            os.path.join(d, "kosu_tukenme") in w.onceki_etiket.text(), "-> %s" % w.onceki_etiket.text())
    dizin = tukenme.kosu_dizini(spec, None)
    os.makedirs(dizin, exist_ok=True)
    tukenme.spec_kaydet(spec, dizin)
    n = len(spec["tukenme"]["adimlar"])
    w._onceki = {"h5": os.path.join(dizin, "depletion_results.h5"), "tarih": time.time(),
                 "sonuc": {"adim_sayisi": 1}}
    w._onceki_durum_guncelle()
    kontrol("yarim kosu: 'Yarım kalmış' ve 1 / %d adım" % n,
            "Yarım kalmış" in w.onceki_etiket.text() and ("1 / %d" % n) in w.onceki_etiket.text()
            and "bu modele ait" not in w.onceki_etiket.text(), "-> %s" % w.onceki_etiket.text())
    w._onceki["sonuc"]["adim_sayisi"] = n
    w._onceki_durum_guncelle()
    kontrol("tam kosu: 'bu modele ait'", "bu modele ait" in w.onceki_etiket.text())
    w.adimlar.setText("1, -5, abc")
    w._kaydet()
    kontrol("gecersiz adim: sayi olmayan parca soyleniyor, eksi toplam yazilmiyor",
            "abc" in w.adim_ozet.text() and "toplam" not in w.adim_ozet.text(),
            "-> %s" % w.adim_ozet.text())


HIZLI = [test_betik_anlamsal_esdegerlik, test_betik_ad_cakismalari,
         test_dogrula_secilmemis_malzeme, test_entropi_otomatik,
         test_uygunluk_tasinan_kurallar, test_ipucu_okunur,
         test_u3si2_yogunlugu, test_ornek_aciklamalari_turkce,
         test_sonsuz_ortam_etiketi, test_sablon_malzemeleri_parametrik,
         test_tukenme_dizin_yarim_adim]
YAVAS = []
