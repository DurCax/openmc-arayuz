# -*- coding: utf-8 -*-
"""
test_ceviri_cekirdek.py -- Dalga 3 / Ajan 11: cekirdek/ metinleri Ingilizcede.

Katalog: locale/en/LC_MESSAGES/cekirdek.po (cekirdek parcasi). Birlesik
openmc_arayuz.mo orkestratorun birlestirmesinde uretilir; bu test ona
BAGLI KALMASIN diye cekirdek.po gecici bir dizinde .mo'ya derlenir ve
ceviri.LOCALE_DIZINI oraya yonlendirilir (ceviri.dil_ayarla("en")). Test
bitince eski dizin ve dil geri gelir.

  (a) butun ornekler + kasitli bozuk modeller: dogrula.tum_kontroller bulgu
      metinlerinde (mesaj, oneri, yer etiketi, ozet) Turkce karakter yok ve
      cevrilmemis msgid yok ("ceviri eksik" WARNING'i yakalanir);
  (b) uygunluk denetimi bulgulari (A-D profilleri) ve fixture kosu
      dizininden uretilen HTML rapor Ingilizce;
  (c) docs/SOZLUK.md terim tutarliligi: cekirdek.po'da sozlukteki Turkce
      terimi iceren msgid'in cevirisi sozlukteki Ingilizce karsiligi icerir
      (istisnalar SOZLUK_ISTISNA'da, gerekceli);
  (d) cekirdek.po butunlugu: her msgid cevrilmis, yer tutucular ayni.
TR modunda davranis degismez (kaynak dil; test_dil kurallari gecerli).
"""

import contextlib
import copy
import glob
import logging
import os
import re
import shutil
import tempfile

from testler.ortak_test import kontrol, KOK, ORNEK
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik

PO = os.path.join(KOK, "locale", "en", "LC_MESSAGES", "cekirdek.po")
FIXTURE = os.path.join(KOK, "testler", "veri", "kosu_ornek")
DEGISIM_SAYISI = 3000     # M6 okuma tutarliligi: dil degisimi sayisi
TURKCE_HARF = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
_EKSIK = re.compile(r"ceviri eksik \(en\): (.*)$", re.S)


class _Toplayici(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.eksikler = []

    def emit(self, kayit):
        m = _EKSIK.match(kayit.getMessage())
        if m:
            self.eksikler.append(m.group(1))


def _po_oku():
    from babel.messages.pofile import read_po
    with open(PO, "rb") as f:
        return read_po(f)


def _mo_derle(hedef_kok):
    """cekirdek.po -> <hedef_kok>/en/LC_MESSAGES/openmc_arayuz.mo"""
    from babel.messages.mofile import write_mo
    dizin = os.path.join(hedef_kok, "en", "LC_MESSAGES")
    os.makedirs(dizin)
    with open(os.path.join(dizin, "openmc_arayuz.mo"), "wb") as f:
        write_mo(f, _po_oku())


@contextlib.contextmanager
def ingilizce():
    """EN dili, cekirdek.po'dan derlenmis katalogla; eksik girisler toplanir."""
    from cekirdek import ceviri
    gecici = tempfile.mkdtemp(prefix="ceviri_cekirdek_")
    eski_dizin, eski_dil = ceviri.LOCALE_DIZINI, ceviri.etkin_dil()
    kaydedici = logging.getLogger(ceviri.KAYDEDICI_ADI)
    toplayici = _Toplayici()
    kaydedici.addHandler(toplayici)
    try:
        _mo_derle(gecici)
        ceviri.LOCALE_DIZINI = gecici
        ceviri.dil_ayarla("en")
        yield toplayici
    finally:
        ceviri.LOCALE_DIZINI = eski_dizin
        ceviri.dil_ayarla(eski_dil)
        kaydedici.removeHandler(toplayici)
        shutil.rmtree(gecici, True)


def _ornekler():
    from cekirdek import sema
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        yield os.path.splitext(os.path.basename(yol))[0], sema.yukle(yol)


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
    sfr, mtr = y("sfr_altigen"), y("mtr_plaka")
    ekle("sab yok", pin, lambda s: [m.update(sab=[]) for m in s["malzemeler"] if m["ad"] == "su"])
    ekle("yogunluk yok", pin, lambda s: s["malzemeler"][0]["yogunluk"].update(deger=None))
    ekle("bilesim", pin, lambda s: s["malzemeler"][0]["bilesim"][0].update(
        tur="xx", birim="yy", miktar=-1))
    ekle("yaricap sirasi", pin, lambda s: s["cubuklar"][0]["bolgeler"].__setitem__(
        0, sema.bolge(0.9, "uo2")))
    ekle("son bolge", pin, lambda s: s["cubuklar"][0]["bolgeler"].__setitem__(
        2, sema.bolge(0.8, "su")))
    ekle("tanimsiz malzeme", pin, lambda s: s["cubuklar"][0]["bolgeler"].__setitem__(
        0, sema.bolge(0.39, "yok")))
    ekle("adim kucuk", pin, lambda s: s["kor"].update(adim=0.5))
    ekle("sinir", pin, lambda s: s["kor"]["sinir"].update(yan="vacuum", alt="vacuum"))
    ekle("gecersiz sinir", pin, lambda s: s["kor"]["sinir"].update(yan="xx"))
    ekle("zenginlik", pin, lambda s: s["malzemeler"][0]["bilesim"][0].update(zenginlik=150.0))
    ekle("yuksek zenginlik", pin, lambda s: s["malzemeler"][0]["bilesim"][0].update(
        zenginlik=19.75))
    ekle("pasif", pin, lambda s: s["ayarlar"].update(pasif=2, cevrim=10, parcacik=100))
    ekle("pasif fazla", pin, lambda s: s["ayarlar"].update(pasif=60, cevrim=60))
    ekle("entropi", pin, lambda s: s["ayarlar"]["entropi_mesh"].update(var=False))
    ekle("kafes harf", pin, lambda s: s.update(demetler=[sema.demet(
        "d", 1.26, [3, 2], ["yy", "yz"], {"y": "yakit_cubugu", "q": "yok"}, "su")]))
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
    ekle("periodic altigen", sfr, lambda s: s["kor"]["sinir"].update(yan="periodic"))
    ekle("tukenme", tuk, lambda s: s["tukenme"].update(guc_yogunlugu=1000.0,
                                                      adimlar=[10.0], zincir="hizli"))
    ekle("tukenme bos", tuk, lambda s: s["tukenme"].update(guc_yogunlugu=0.0, adimlar=[]))
    ekle("eksenel", eks, lambda s: s["kor"]["eksenel"]["bolgeler"][0].update(
        dolgu="yok_boyle", yukseklik=0.0))
    ekle("kuresel yukseklik", zirh, lambda s: s["kor"].update(yukseklik=10.0))
    ekle("plaka", mtr, lambda s: [p.update(et_kalinlik=0.0, zarf_malzeme=None)
                                  for p in s.get("plakalar", [])])
    return cikti


def _bulgu_metinleri(modeller):
    """[(nereden, metin)]: mesaj, oneri, yer etiketi ve ozet."""
    from cekirdek import dogrula
    out = []
    for ad, s in modeller:
        try:
            bulgular = dogrula.tum_kontroller(s, veri_kontrolu=False)
        except Exception as e:      # kontrol cokerse test bunu gostersin
            out.append(("istisna:%s" % ad, "%s: %s" % (type(e).__name__, e)))
            continue
        for b in bulgular:
            out.append(("yer:%s" % ad, dogrula.yer_etiketi(b.yer)))
            out.append(("bulgu:%s" % ad, b.mesaj))
            if b.oneri:
                out.append(("oneri:%s" % ad, b.oneri))
            out.append(("str:%s" % ad, str(b)))
        out.append(("ozet:%s" % ad, dogrula.ozet(bulgular)))
    return out


def _kullanici_adlari(modeller):
    """Kullanici verisi (malzeme/parca/model adlari) icinden Turkce harf iceren
    adlar: metinden cikarilip denetlenir (kisa ASCII adlar -- "su" -- cikarilmaz,
    yoksa "result" gibi sozcukler bozulurdu)."""
    adlar = set()

    def topla(d):
        if isinstance(d, dict):
            for k, v in d.items():
                if k == "ad" and isinstance(v, str):
                    adlar.add(v)
                else:
                    topla(v)
        elif isinstance(d, list):
            for v in d:
                topla(v)

    for _ad, s in modeller:
        topla(s)
    return sorted((a for a in adlar if TURKCE_HARF.search(a)), key=len, reverse=True)


def _turkce_kalanlar(metinler, adlar=()):
    kalan = []
    for nereden, metin in metinler:
        temiz = metin
        for ad in adlar:
            temiz = temiz.replace(ad, "")
        if TURKCE_HARF.search(temiz):
            kalan.append("%s: %s" % (nereden, metin[:140]))
    return kalan


@gereksinim("R-M9-01")
def test_bulgular_ingilizce():
    print("\n[CC1] EN: ornekler + bozuk modeller -- dogrulama bulgulari Ingilizce")
    modeller = list(_ornekler()) + _bozuk_modeller()
    with ingilizce() as toplayici:
        metinler = _bulgu_metinleri(modeller)
    kontrol("bulgu metni uretildi (%d)" % len(metinler), len(metinler) > 150)
    istisna = [m for n, m in metinler if n.startswith("istisna:")]
    kontrol("dogrulama hicbir modelde cokmedi", not istisna, "-> %s" % istisna[:3])
    kalan = _turkce_kalanlar(metinler, _kullanici_adlari(modeller))
    kontrol("bulgu metinlerinde Turkce harf yok", not kalan,
            "-> %d: %s" % (len(kalan), kalan[:6]))
    kontrol("cevrilmemis msgid yok", not toplayici.eksikler,
            "-> %d: %s" % (len(toplayici.eksikler), toplayici.eksikler[:6]))


def _fixture_spec():
    import json
    with open(os.path.join(FIXTURE, "spec.json"), encoding="utf-8") as f:
        return json.load(f)


def _html_duz(metin):
    """HTML -> duz metin (etiket, stil, gomulu gorsel ve varliklar ayiklanir)."""
    import html as _html
    metin = re.sub(r"<style.*?</style>", " ", metin, flags=re.S)
    metin = re.sub(r"<pre.*?</pre>", " ", metin, flags=re.S)     # Ek: model JSON
    metin = re.sub(r"<[^>]+>", " ", metin)
    return _html.unescape(metin)


@gereksinim("R-M9-01")
def test_uygunluk_ve_rapor_ingilizce():
    print("\n[CC2] EN: uygunluk denetimi bulgulari ve fixture HTML raporu Ingilizce")
    from cekirdek import rapor
    from cekirdek.uygunluk_denetimi import denetle as D
    spec = _fixture_spec()
    adlar = _kullanici_adlari([("fixture", spec)])
    gecici = tempfile.mkdtemp(prefix="ceviri_rapor_")
    try:
        with ingilizce() as toplayici:
            bulgular = D.denetle(spec, FIXTURE, ("A", "B", "C", "D"))
            metinler = []
            for b in bulgular:
                metinler += [("mesaj:" + b.kural, b.mesaj), ("kaynak:" + b.kural, b.kaynak)]
                if b.oneri:
                    metinler.append(("oneri:" + b.kural, b.oneri))
            sonuc = rapor.olustur(spec, FIXTURE, os.path.join(gecici, "r.html"), "html")
            with open(sonuc.yol, encoding="utf-8") as f:
                html_metin = f.read()
            metinler += [("uyari", u) for u in sonuc.uyarilar]
    finally:
        shutil.rmtree(gecici, True)
    kontrol("denetim bulgusu uretildi (%d)" % len(bulgular), len(bulgular) > 15)
    kalan = _turkce_kalanlar(metinler, adlar)
    kontrol("uygunluk bulgularinda (mesaj, oneri, kaynak) Turkce harf yok", not kalan,
            "-> %d: %s" % (len(kalan), kalan[:5]))
    duz = _html_duz(html_metin)
    for ad in adlar:
        duz = duz.replace(ad, "")
    tr_satirlar = [s.strip() for s in re.split(r"\n|\s{2,}", duz) if TURKCE_HARF.search(s)]
    kontrol("HTML rapor metninde Turkce harf yok", not tr_satirlar,
            "-> %d: %s" % (len(tr_satirlar), tr_satirlar[:5]))
    kontrol("HTML rapor dili en (<html lang>)", 'lang="en"' in html_metin[:400],
            "-> %s" % html_metin[:120])
    for parca in ("Reproducibility", "Materials", "Geometry", "Run settings",
                  "Power distribution", "Model check findings"):
        kontrol("HTML Ingilizce bolum: %s" % parca, parca in html_metin)
    kontrol("cevrilmemis msgid yok", not toplayici.eksikler,
            "-> %d: %s" % (len(toplayici.eksikler), toplayici.eksikler[:6]))


def test_ayni_ceviri_eksik_sayilmaz():
    print("\n[CC3] M6: cevirisi msgid'le AYNI giris ('Statepoint') eksik sayilmaz")
    from cekirdek import ceviri
    with ingilizce() as toplayici:
        sonuc = ceviri._("Statepoint"), ceviri._("Git commit"), ceviri._("Kor")
    kontrol("ayni ceviriler aynen, digeri cevrilir",
            sonuc == ("Statepoint", "Git commit", "Core"), "-> %s" % (sonuc,))
    kontrol("ayni ceviri 'ceviri eksik' uyarisi vermez", not toplayici.eksikler,
            "-> %s" % toplayici.eksikler)


def test_ceviri_okuma_tutarli():
    print("\n[CC4] M6: dil degisirken okuyan is parcaciklari tutarli (dil, katalog) cifti gorur")
    import sys
    import threading
    from cekirdek import ceviri
    eski_aralik = sys.getswitchinterval()
    sonuclar, dur = [], threading.Event()

    def oku():
        while not dur.is_set():
            sonuclar.append(ceviri._("Kor"))

    with ingilizce() as toplayici:
        sys.setswitchinterval(1e-6)
        try:
            okuyucular = [threading.Thread(target=oku) for _i in range(4)]
            for t in okuyucular:
                t.start()
            for i in range(DEGISIM_SAYISI):
                ceviri.dil_ayarla("tr" if i % 2 else "en")
            dur.set()
            for t in okuyucular:
                t.join()
        finally:
            sys.setswitchinterval(eski_aralik)
    kontrol("okunan metin yalniz 'Kor' ya da 'Core' (%d okuma)" % len(sonuclar),
            set(sonuclar) <= {"Kor", "Core"}, "-> %s" % sorted(set(sonuclar)))
    kontrol("var olan giris icin yanlis 'ceviri eksik' uyarisi yok", not toplayici.eksikler,
            "-> %s" % toplayici.eksikler[:3])


def _tukenme_suzgeci(satir):
    """arayuz/sekme_tukenme._cikti_oku'nun satir suzgeci (ayni kosul): alt
    surec ciktisindan loga gecen satirlar."""
    bizim = satir.startswith("  ") and not satir.startswith("   ")
    return (satir.startswith("[openmc.deplete]") or bizim
            or "Combined k-effective" in satir or "TÜKENME" in satir
            or "Error" in satir or "HATA" in satir or "Traceback" in satir)


def test_tukenme_makine_isareti():
    print("\n[CC5] Tukenme terminal basligi makine isaretini (TÜKENME) EN'de de tasir")
    from cekirdek import tukenme, sema
    spec = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    tr = tukenme.kosu_basligi(spec)
    with ingilizce():
        en = tukenme.kosu_basligi(spec)
        isaretli = _tukenme_suzgeci(en)
    kontrol("baslik dilden bagimsiz ve isaretli", en == tr and tukenme.KOSU_ISARETI in en,
            "-> %r / %r" % (tr, en))
    kontrol("arayuz suzgeci EN basligini gecirir", isaretli)


def _po_girdileri():
    return [m for m in _po_oku() if m.id]


def test_cekirdek_po_butun():
    print("\n[CC6] cekirdek.po: her msgid cevrilmis, yer tutucular ve kenar bosluklari ayni")
    yer = re.compile(r"%(?:\(\w+\))?[-#0 +]*\d*(?:\.\d+)?[sdifgeExXrc]|\{[^{}]*\}")
    bos, uyumsuz, kenar = [], [], []
    for m in _po_girdileri():
        kimlik = m.id if isinstance(m.id, tuple) else (m.id,)
        ceviri = m.string if isinstance(m.string, tuple) else (m.string,)
        if not all(ceviri) or "fuzzy" in m.flags:
            bos.append(kimlik[0][:60])
            continue
        for a, b in zip(kimlik, ceviri):
            if yer.findall(a.replace("%%", "")) != yer.findall(b.replace("%%", "")):
                uyumsuz.append("%r -> %r" % (a[:50], b[:50]))
            if (a[:1].isspace(), a[-1:].isspace()) != (b[:1].isspace(), b[-1:].isspace()):
                kenar.append(a[:50])
    kontrol("cekirdek.po girdisi var (%d)" % len(_po_girdileri()), len(_po_girdileri()) > 1000)
    kontrol("cevrilmemis / fuzzy giris yok", not bos, "-> %d: %s" % (len(bos), bos[:5]))
    kontrol("yer tutucular (sira dahil) msgid ile ayni", not uyumsuz,
            "-> %d: %s" % (len(uyumsuz), uyumsuz[:3]))
    kontrol("bas/son bosluk msgid ile ayni", not kenar, "-> %s" % kenar[:3])
    kaynakli = [m for m in _po_girdileri() if any(
        not yol.startswith("cekirdek/") for yol, _s in m.locations)]
    kontrol("butun girisler cekirdek/ kaynakli (arayuz.po ile karismaz)", not kaynakli,
            "-> %s" % [m.id for m in kaynakli][:3])


def _parca_yaz(yol, girdiler):
    from babel.messages.catalog import Catalog
    from babel.messages.pofile import write_po
    k = Catalog(locale="en", domain="parca")
    for mid, ceviri in girdiler:
        k.add(mid, ceviri)
    with open(yol, "wb") as f:
        write_po(f, k)


def test_po_birlestir_cogul():
    print("\n[CC7] M6: po_birlestir -- cevrilmemis cogul giris (('', '')) celiski sayilmaz, "
          "doldurulur")
    import sys
    sys.path.insert(0, os.path.join(KOK, "araclar"))
    import po_birlestir
    cogul = ("%d hata", "%d hata")
    gecici = tempfile.mkdtemp(prefix="po_birlestir_")
    try:
        a, b = os.path.join(gecici, "a.po"), os.path.join(gecici, "b.po")
        _parca_yaz(a, [(cogul, ("", "")), ("Kor", "Core")])
        _parca_yaz(b, [(cogul, ("%d error", "%d errors")), ("Kor", "Core")])
        k1, c1 = po_birlestir.birlestir([a, b])
        k2, c2 = po_birlestir.birlestir([b, a])
        _parca_yaz(b, [(cogul, ("%d error", "%d errors (x)"))])
        _parca_yaz(a, [(cogul, ("%d error", "%d errors"))])
        _k3, c3 = po_birlestir.birlestir([a, b])
    finally:
        shutil.rmtree(gecici, True)
    kontrol("bos cogul + dolu cogul: celiski yok (iki sira)", not c1 and not c2,
            "-> %s / %s" % (c1, c2))
    for ad, k in (("bos once", k1), ("dolu once", k2)):
        m = k.get(cogul[0])
        kontrol("%s: birlesik cogul ceviri dolu" % ad,
                m is not None and tuple(m.string) == ("%d error", "%d errors"),
                "-> %r" % (m.string if m else None,))
    kontrol("gercekten farkli cogul ceviri celiski sayilir", len(c3) == 1, "-> %s" % c3)


def test_regresyon_listeleri_acik():
    print("\n[CC8] M6: test_regresyon HIZLI/YAVAS listelerini acikca tanimlar "
          "(conftest main() AST cozumlemesine dusmez)")
    import importlib
    m = importlib.import_module("testler.test_regresyon")
    kontrol("HIZLI ve YAVAS tanimli (bos liste)",
            getattr(m, "HIZLI", None) == [] and getattr(m, "YAVAS", None) == [],
            "-> HIZLI=%r YAVAS=%r" % (getattr(m, "HIZLI", None), getattr(m, "YAVAS", None)))
    try:
        import conftest
    except ImportError as e:            # pytest kurulu degil
        kontrol("pytest yok; kopru denetimi atlandi", True, "-> %s" % e)
        return
    kontrol("kopru listeyi kullanir: ([], [])", conftest.test_listeleri(m) == ([], []))


HIZLI = [test_bulgular_ingilizce, test_uygunluk_ve_rapor_ingilizce, test_po_birlestir_cogul,
         test_regresyon_listeleri_acik,
         test_ayni_ceviri_eksik_sayilmaz, test_ceviri_okuma_tutarli,
         test_tukenme_makine_isareti, test_cekirdek_po_butun]
YAVAS = []
