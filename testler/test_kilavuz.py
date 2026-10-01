# -*- coding: utf-8 -*-
"""
test_kilavuz.py -- kullanim kilavuzu (docs/kilavuz/, Dalga 3 Ajan 13b) eskimesin.

  KL1 bolum kimlikleri: yardim.BOLUMLER Ajan 12'nin baglanti listesini kapsar;
      her kimligin TR ve EN kilavuzda bir basligi var.
  KL2 bolum 4 (sekme sekme basvuru): arayuzdeki her form etiketi ve onay kutusu
      (offscreen AnaPencere + malzeme diyaloglari + kutuphane parametreleri) TR
      bolum 4'te gecer; koddaki sema anahtarlari TR ve EN bolum 4'te ters tirnak
      icinde gecer. EN etiket (katalogda cevirisi varsa) yalniz UYARI.
  KL3 kilavuzdaki ornek yollari var; `openmc-arayuz-kosu` komutlari --help ile
      calisir ve yalniz gercek secenekleri kullanir.
  KL4 TR/EN esligi (dosya, kimlik sirasi, resim adlari), kirik baglanti yok,
      EN metinde Turkce karakter yok (ozel adlar istisna).
  KL5 uygulama ici gosterim: yardim.ac("geometri", pencere) basliksiz acilir,
      capaya gider, bildirim/hata yok; arama; EN eksikse TR + uyari.
  KL6 ekran goruntuleri: betigin girdi ozeti guncel degilse UYARI (kati degil);
      EN goruntusu yoksa TR'ye dusulur -> BILGI.
  KL7 sorun giderme (bolum 9): her uygunluk kurali / alt kimlik ve her bulgu
      yer oneki TR ve EN'de.
  KL8 derleme: HTML + PDF uretilir, capalar korunur; sozluk (bolum 10)
      docs/SOZLUK.md'nin her terimini icerir.
Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import contextlib
import glob
import io
import json
import os
import re
import shutil
import tempfile

from testler.ortak_test import kontrol, KOK, ORNEK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Ajan 12'nin arayuzde bagladigi bolumler (orkestrator sozlesmesi, 01.10.2026).
AJAN12_KIMLIKLERI = (
    "baslangic", "ilk-hesap", "kavramlar", "malzemeler", "parcalar", "demet",
    "geometri", "geometri-gelismis", "hesap-ayarlari", "calistir", "sonuclar",
    "analiz", "tukenme", "uygunluk-denetimi", "vv", "terminal", "sorun-giderme",
    "sozluk")

# Etiket taramasinda acilan ornekler: her sekme ve kor turu varyanti.
ETIKET_ORNEKLERI = ("pwr_17x17.json", "vver1000_kor.json", "godiva_kriter.json",
                    "pwr_3b.json", "zirh_kure.json", "mtr_plaka.json", "tamburlu_kor.json")
_NOT_UZUNLUGU = 60          # bundan uzun etiket alan degil not/ipucudur
TURKCE_HARFLER = "çğıİöşüÇĞÖŞÜ"
EN_ISTISNALARI = ("Türkçe",)    # EN metinde izin verilen ozel adlar
SOZLUK_DOSYASI = "10-sozluk.md"  # EN sozluk tablosunun "Turkish" sutunu istisnadir
YARDIM_LOGU = "openmc_arayuz.arayuz.yardim"
KOSU_ALT_KOMUTLARI = ("rapor", "uygunluk", "yeniden")
KOSU_SECENEKLERI = {
    None: {"--dizin", "-s", "--is-parcacigi", "--sadece-dogrula", "--betik", "--help", "-h"},
    "rapor": {"-o", "--cikti", "--spec", "--help", "-h"},
    "uygunluk": {"--profil", "--siki", "--help", "-h"},
    "yeniden": {"--hedef", "--kuru", "-s", "--is-parcacigi", "--help", "-h"},
}


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _ky():
    from arayuz.yardim import kaynak
    return kaynak


def _metin(dil, onek=""):
    """Bir dilin (istege bagli dosya onekiyle) kilavuz kaynaklari: {ad: metin}."""
    ky = _ky()
    return {ad: ky.dosya_oku(dil, ad) for ad in ky.dosya_adlari()
            if ad.startswith(onek) and os.path.exists(ky.dosya_yolu(dil, ad))}


def _norm(s):
    s = re.sub(r"<[^>]+>", "", s or "").replace("&", "")
    s = re.sub(r"\s+", " ", s).strip().rstrip(":").strip()
    return s.casefold()


def _duz(metin):
    """Markdown vurgulari ayiklanmis, bosluklari teklenmis, kucuk harf metin."""
    m = metin.replace("**", "").replace("`", "").replace("\\", "")
    return re.sub(r"\s+", " ", m).casefold()


# ----------------------------------------------------------------------------
# KL1 bolum kimlikleri
# ----------------------------------------------------------------------------
def test_bolum_kimlikleri():
    print("\n[KL1] BOLUMLER Ajan 12 listesini kapsar; her kimligin TR ve EN bolumu var")
    from arayuz import yardim
    eksik = [k for k in AJAN12_KIMLIKLERI if k not in yardim.BOLUMLER]
    kontrol("BOLUMLER Ajan 12'nin 18 kimligini kapsar", not eksik, "-> %s" % eksik)
    kontrol("bolum_var: bilinen True, bilinmeyen False",
            yardim.bolum_var("geometri") and not yardim.bolum_var("yok-boyle-bolum"))
    kontrol("BOLUMLER basliklari bos degil", all(v for v in yardim.BOLUMLER.values()))
    ky = _ky()
    for dil in ("tr", "en"):
        kimlikler = set()
        for ad, metin in _metin(dil).items():
            kimlikler |= set(ky.ayristir(metin).kimlikler)
        yok = [k for k in yardim.BOLUMLER if k not in kimlikler]
        kontrol("%s: BOLUMLER'in her kimligi kilavuzda" % dil.upper(), not yok, "-> %s" % yok)
    tr = ky.kilavuz("tr")
    kontrol("TR birlesik kilavuzda her baslik kimligi tekil",
            len(tr.kimlikler) == len(set(tr.kimlikler)),
            "-> %s" % sorted({k for k in tr.kimlikler if tr.kimlikler.count(k) > 1}))


# ----------------------------------------------------------------------------
# KL2 bolum 4: arayuz alanlari ve sema anahtarlari
# ----------------------------------------------------------------------------
def _form_etiketleri(kok):
    """Bir widget agacindaki QFormLayout satir etiketleri + onay kutusu metinleri."""
    from PySide6 import QtWidgets
    F = QtWidgets.QFormLayout
    etiketler = set()
    for f in kok.findChildren(QtWidgets.QFormLayout):
        for satir in range(f.rowCount()):
            for rol in (F.LabelRole, F.SpanningRole, F.FieldRole):
                oge = f.itemAt(satir, rol)
                w = oge.widget() if oge else None
                if isinstance(w, QtWidgets.QLabel) and rol == F.LabelRole:
                    etiketler.add(w.text())
                elif isinstance(w, QtWidgets.QCheckBox):
                    etiketler.add(w.text())
    for c in kok.findChildren(QtWidgets.QCheckBox):
        etiketler.add(c.text())
    return etiketler


def _alan_mi(etiket):
    n = _norm(etiket)
    return bool(n) and len(n) <= _NOT_UZUNLUGU and not n.endswith(".") and ". " not in n


def arayuz_etiketleri():
    """{sekme_anahtari: {etiket}} -- offscreen pencerede ornekler acilarak toplanir."""
    from arayuz.ana_pencere import AnaPencere
    from PySide6 import QtCore
    uyg = _qt()
    p = AnaPencere()
    p._kaydetme_sor = lambda: True
    sonuc = {}
    try:
        p.resize(1280, 800)
        p.show()
        for ornek in ETIKET_ORNEKLERI:
            p.proje_ac(os.path.join(ORNEK, ornek))
            uyg.processEvents()
            for k in p.sekme_anahtarlari():
                if p.sekmeye_git(k, sessiz=True):
                    uyg.processEvents()
                    sonuc.setdefault(k, set()).update(_form_etiketleri(p.sekme_sayfasi(k)))
        sonuc.setdefault("malzemeler", set()).update(_malzeme_etiketleri(p))
    finally:
        p.s_tukenme.bekle()
        p._kirli = False
        p.close()
        p.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    return {k: {e for e in v if _alan_mi(e)} for k, v in sonuc.items()}


def _malzeme_etiketleri(p):
    from cekirdek import malzeme_kutup as mk
    from arayuz.malzeme.kutuphane_diyalog import KutuphaneDiyalog
    from arayuz.malzeme.malzeme_diyalog import MalzemeDiyalog
    etiketler = set()
    for anahtar in mk.KUTUPHANE:
        etiketler |= {t["etiket"] for t in mk.parametreler(anahtar)}
    diyaloglar = [KutuphaneDiyalog(p.spec, p)]
    for m in p.spec.get("malzemeler") or []:
        diyaloglar.append(MalzemeDiyalog(m, p.spec, p))
    from cekirdek import sema_yapici
    diyaloglar.append(MalzemeDiyalog(sema_yapici.malzeme("yeni", [], 1.0), p.spec, p, yeni=True))
    for d in diyaloglar:
        etiketler |= _form_etiketleri(d)
        d.deleteLater()
    return etiketler


def _yapici_anahtarlari():
    """cekirdek.sema_yapici kuruculari kukla girdiyle cagrilir; donen anahtarlar."""
    import inspect
    from cekirdek import sema_yapici as y
    liste = ("gruplar", "adlar", "skorlar", "bilesim", "bolgeler", "harita")
    anahtarlar = set()
    for ad in ("malzeme", "bilesen", "cubuk", "bolge", "kontrol_cubugu", "plaka", "demet",
               "demet_altigen", "demet_kilifi", "eksenel_bolge", "kabuk", "tambur", "tally",
               "filtre_enerji", "filtre_mesh", "filtre_mesh_otomatik", "filtre_malzeme"):
        islev = getattr(y, ad)
        arg = []
        for p in inspect.signature(islev).parameters.values():
            if p.default is not inspect.Parameter.empty:
                continue
            arg.append([] if p.name in liste else {} if p.name == "anahtar"
                       else [1, 1] if p.name in ("boyut", "alt", "ust") else 1.0)
        anahtarlar |= set(islev(*arg))
    return anahtarlar


def sema_anahtarlari():
    """Bolum 4'te ters tirnak icinde gecmesi gereken, koddan cikan anahtar adlari."""
    from cekirdek import sema, tarama, uygunluk
    from cekirdek.geometri import kesit
    from cekirdek.geometri import sema as gsema
    spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    a = set(sema.VARSAYILAN_AYARLAR) | set(sema.VARSAYILAN_GUC)
    ayar = sema.VARSAYILAN_AYARLAR
    for alt in (ayar["kaynak"], ayar["kaynak"]["enerji"], ayar["kaynak"]["aci"],
                ayar["entropi_mesh"], ayar["kinetik"]):
        a |= set(alt)
    a |= set(sema.VARSAYILAN_TUKENME) | set(sema.VARSAYILAN_CALISTIRMA)
    kor = sema.VARSAYILAN_KOR
    a |= set(kor) | set(kor["tambur"]) | set(kor["yansitici"]) | set(kor["eksenel"])
    a |= set(kor["sinir"])
    for alanlar in sema.KOR_TUR_ALANLARI.values():
        a |= set(alanlar)
    a |= set(uygunluk.ayar_alanlari(spec)) | set(uygunluk.kor_ortak_alanlari(spec))
    a |= set(uygunluk.KOR_TURLERI) | {"kuresel", "agac"} | set(uygunluk.KRITIK_PARAMETRELER)
    a |= set(tarama.TURLER)
    a |= set(gsema.KULLANICI_TURLERI) | set(gsema.SINIR_TURLERI)
    a |= set(gsema.YERLESIM_MODLARI) | set(gsema.GRUP_TURLERI)
    a |= set(kesit.SEKILLER) | set(kesit.PIN_SEKILLERI)
    return a | _yapici_anahtarlari()


def _kodda_gecen(metin):
    """Ters tirnak icindeki kelimeler (nokta, koseli parantez, = ile bolunmus)."""
    kelimeler = set()
    for kod in re.findall(r"`([^`\n]+)`", metin):
        kelimeler |= set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", kod))
    return kelimeler


def _anahtar_eksikleri(metin, anahtarlar):
    kodda = _kodda_gecen(metin)
    noktali = {k for kod in re.findall(r"`([^`\n]+)`", metin) for k in [kod]}
    eksik = []
    for k in sorted(anahtarlar):
        if k in kodda:
            continue
        if "_" in k and any(k.replace("_", ".") in kod for kod in noktali):
            continue
        eksik.append(k)
    return eksik


def _en_etiket_uyarilari(etiketler, en_duz):
    """Katalogda cevirisi olan etiketlerin EN bolum 4'te gecmeyenleri (UYARI)."""
    from cekirdek import ceviri
    onceki = ceviri.etkin_dil()
    try:
        ceviri.dil_ayarla("en")
        eksik = []
        for e in sorted(etiketler):
            c = ceviri._(e)
            if c != e and _norm(c) not in en_duz:
                eksik.append(c)
        return eksik
    finally:
        ceviri.dil_ayarla(onceki)


def test_bolum4_alanlari():
    print("\n[KL2] bolum 4: arayuzdeki her alan TR'de; sema anahtarlari TR ve EN'de")
    tr = "\n".join(_metin("tr", "04").values())
    en = "\n".join(_metin("en", "04").values())
    kontrol("bolum 4 TR ve EN dosyalari var", bool(tr) and bool(en))
    etiketler = arayuz_etiketleri()
    tum = set().union(*etiketler.values()) if etiketler else set()
    kontrol("arayuzden etiket toplandi (>= 150)", len(tum) >= 150, "-> %d" % len(tum))
    tr_duz = _duz(tr)
    for sekme, kume in sorted(etiketler.items()):
        yok = sorted(e for e in kume if _norm(e) not in tr_duz)
        kontrol("TR bolum 4: '%s' sekmesinin %d alani kilavuzda" % (sekme, len(kume)), not yok,
                "-> eksik %d: %s" % (len(yok), yok[:12]))
    anahtarlar = sema_anahtarlari()
    for dil, metin in (("tr", tr), ("en", en)):
        eksik = _anahtar_eksikleri(metin, anahtarlar)
        kontrol("%s bolum 4: koddaki %d sema anahtari ters tirnakta" % (dil.upper(), len(anahtarlar)),
                not eksik, "-> eksik %d: %s" % (len(eksik), eksik[:15]))
    uyari = _en_etiket_uyarilari(tum, _duz(en))
    print("  [UYARI] EN bolum 4'te gecmeyen cevrilmis etiket: %d %s" % (len(uyari), uyari[:10])
          if uyari else "  [BILGI] EN etiketleri: katalogdaki her ceviri bolum 4'te ya da ceviri yok")


# ----------------------------------------------------------------------------
# KL3 ornek yollari ve komutlar
# ----------------------------------------------------------------------------
def _kod_bloklari(metin):
    return re.findall(r"^```[^\n]*\n(.*?)^```", metin, flags=re.S | re.M)


def kosu_komutlari(metinler):
    """Kod bloklarindaki `openmc-arayuz-kosu ...` satirlari: [(alt_komut, [secenek])]."""
    komutlar = []
    for metin in metinler:
        for blok in _kod_bloklari(metin):
            for satir in blok.splitlines():
                satir = satir.split("#", 1)[0].strip()
                if not satir.startswith("openmc-arayuz-kosu"):
                    continue
                parca = satir.split()[1:]
                alt = parca[0] if parca and parca[0] in KOSU_ALT_KOMUTLARI else None
                secenek = [x.split("=")[0] for x in re.sub(r"\[|\]", " ", " ".join(parca)).split()
                           if x.startswith("-")]
                komutlar.append((alt, secenek, satir))
    return komutlar


def _yardim_calisir(alt):
    from cekirdek import giris
    arg = ([alt] if alt else []) + ["--help"]
    cikti = io.StringIO()
    try:
        with contextlib.redirect_stdout(cikti), contextlib.redirect_stderr(cikti):
            kod = giris.kosu(arg)
    except SystemExit as cikis:
        kod = cikis.code
    return (kod or 0) == 0 and len(cikti.getvalue()) > 50


def test_ornek_yollari_ve_komutlar():
    print("\n[KL3] kilavuzdaki ornek yollari var; openmc-arayuz-kosu komutlari calisir")
    metinler = list(_metin("tr").values()) + list(_metin("en").values())
    yollar = set()
    for m in metinler:
        yollar |= set(re.findall(r"ornekler/[A-Za-z0-9_./-]+\.json", m))
    yok = sorted(y for y in yollar if not os.path.exists(os.path.join(KOK, y)))
    kontrol("kilavuzda %d ornek yolu, hepsi var" % len(yollar), yollar and not yok, "-> %s" % yok)
    komutlar = kosu_komutlari(metinler)
    kontrol("kilavuzda openmc-arayuz-kosu komutu var", bool(komutlar))
    altlar = sorted({alt or "" for alt, _s, _t in komutlar})
    for alt in altlar:
        kontrol("openmc-arayuz-kosu %s--help calisir" % (alt + " " if alt else ""),
                _yardim_calisir(alt or None))
    kotu = [t for alt, sec, t in komutlar if not set(sec) <= KOSU_SECENEKLERI[alt]]
    kontrol("komutlarda yalniz gercek secenekler", not kotu, "-> %s" % kotu[:5])


# ----------------------------------------------------------------------------
# KL4 TR/EN esligi, kirik baglanti, EN'de Turkce yok
# ----------------------------------------------------------------------------
def _hedef_sorunu(ky, dil, ad, hedef, kimlikler):
    """Bir baglanti hedefinin sorunu (None = saglam)."""
    if re.match(r"^[a-z]+://", hedef) or hedef.startswith("mailto:"):
        return None
    dosya, _d, capa = hedef.partition("#")
    if not dosya:
        return None if capa in kimlikler.get(ad, ()) else "capa yok"
    if dosya in kimlikler:
        return None if not capa or capa in kimlikler[dosya] else "capa yok"
    yol = os.path.normpath(os.path.join(os.path.dirname(ky.dosya_yolu(dil, ad)), dosya))
    return None if os.path.exists(yol) else "dosya yok"


def test_tr_en_esligi():
    print("\n[KL4] TR/EN esligi, kirik baglanti yok, EN'de Turkce karakter yok")
    ky = _ky()
    tr, en = _metin("tr"), _metin("en")
    kontrol("TR ve EN ayni dosyalar", sorted(tr) == sorted(en),
            "-> yalniz TR %s, yalniz EN %s" % (sorted(set(tr) - set(en)), sorted(set(en) - set(tr))))
    kontrol("kilavuzda en az 11 bolum dosyasi (0-10)", len(tr) >= 11, "-> %d" % len(tr))
    ayr = {dil: {ad: ky.ayristir(m) for ad, m in d.items()} for dil, d in (("tr", tr), ("en", en))}
    for ad in sorted(set(tr) & set(en)):
        a, b = ayr["tr"][ad], ayr["en"][ad]
        kontrol("%s: kimlik sirasi TR = EN" % ad, a.kimlikler == b.kimlikler,
                "-> TR %s / EN %s" % (a.kimlikler, b.kimlikler))
        ra = [os.path.basename(x.hedef) for x in a.baglantilar if x.resim]
        rb = [os.path.basename(x.hedef) for x in b.baglantilar if x.resim]
        kontrol("%s: resimler TR = EN" % ad, ra == rb, "-> %s / %s" % (ra, rb))
    for dil in ("tr", "en"):
        sorunlar = [(ad, s) for ad, x in ayr[dil].items() for s in x.sorunlar]
        kontrol("%s: kimlik satirlari basligin hemen ustunde" % dil.upper(), not sorunlar,
                "-> %s" % sorunlar[:5])
        kimlikler = {ad: set(x.kimlikler) for ad, x in ayr[dil].items()}
        kirik = []
        for ad, x in ayr[dil].items():
            for b in x.baglantilar:
                if b.resim:
                    continue
                sorun = _hedef_sorunu(ky, dil, ad, b.hedef, kimlikler)
                if sorun:
                    kirik.append("%s:%d %s (%s)" % (ad, b.satir, b.hedef, sorun))
        kontrol("%s: kirik baglanti yok" % dil.upper(), not kirik, "-> %s" % kirik[:8])
    _resim_kontrolu(ky, ayr)
    turkce = []
    for ad, m in en.items():
        temiz = m
        for ozel in EN_ISTISNALARI:
            temiz = temiz.replace(ozel, "")
        for no, satir in enumerate(temiz.splitlines(), 1):
            if ad == SOZLUK_DOSYASI and satir.startswith("|"):
                continue            # sozluk tablosu bilerek iki dillidir (Turkish sutunu)
            if any(h in satir for h in TURKCE_HARFLER):
                turkce.append("%s:%d %s" % (ad, no, satir.strip()[:60]))
    kontrol("EN kilavuzda Turkce karakter yok (istisna: %s, sozluk tablosu)"
            % ", ".join(EN_ISTISNALARI),
            not turkce, "-> %d satir: %s" % (len(turkce), turkce[:6]))


def _resim_kontrolu(ky, ayr):
    eksik_tr, yedek_en = [], []
    for dil in ("tr", "en"):
        for ad, x in ayr[dil].items():
            for b in x.baglantilar:
                if not b.resim:
                    continue
                yol = os.path.normpath(os.path.join(os.path.dirname(ky.dosya_yolu(dil, ad)), b.hedef))
                if os.path.exists(yol):
                    continue
                tr_yol = yol.replace(os.sep + "en" + os.sep, os.sep + "tr" + os.sep)
                if dil == "en" and os.path.exists(tr_yol):
                    yedek_en.append(os.path.basename(yol))
                else:
                    eksik_tr.append("%s/%s: %s" % (dil, ad, b.hedef))
    kontrol("kilavuzdaki resimler var (EN icin TR karsiligi)", not eksik_tr, "-> %s" % eksik_tr[:6])
    if yedek_en:
        print("  [BILGI] EN ekran goruntusu yok, TR'ye dusuluyor: %d (%s); "
              "Ajan 12 birlesince: python araclar/kilavuz_ekran.py --dil en"
              % (len(set(yedek_en)), ", ".join(sorted(set(yedek_en))[:6])))


# ----------------------------------------------------------------------------
# KL5 uygulama ici gosterim
# ----------------------------------------------------------------------------
class _KayitTutucu(object):
    """WARNING ve ustu log kayitlari; onek verilirse yalniz o kaydediciler."""

    def __init__(self, onek="openmc_arayuz"):
        import logging
        self.kayitlar = []
        self.isleyici = logging.Handler(logging.WARNING)
        self.isleyici.emit = lambda r: (r.name.startswith(onek) and self.kayitlar.append(r))

    def __enter__(self):
        import logging
        logging.getLogger().addHandler(self.isleyici)
        return self

    def __exit__(self, *_):
        import logging
        logging.getLogger().removeHandler(self.isleyici)


def _bildirimler(w):
    from arayuz.bilesenler.bildirim import Bildirim
    return [b for b in w.findChildren(Bildirim) if not b.isHidden()]


def _capa_gorunur(gosterici, kimlik):
    """Capanin basligi tarayicinin gorunen alaninin ust kisminda mi."""
    tarayici = gosterici.tarayici
    blok = gosterici.capa_blogu(kimlik)
    if blok is None or not blok.isValid():
        return False
    y = tarayici.document().documentLayout().blockBoundingRect(blok).top()
    deger = tarayici.verticalScrollBar().value()
    return deger > 0 and abs(y - deger) <= tarayici.viewport().height() / 2


def test_uygulama_ici_gosterim():
    print("\n[KL5] yardim.ac('geometri', pencere): basliksiz acilir, capaya gider, bildirim yok")
    from PySide6 import QtWidgets
    from arayuz import yardim
    from arayuz.yardim import gosterici as g
    from cekirdek import ceviri
    uyg = _qt()
    onceki = ceviri.etkin_dil()
    ceviri.dil_ayarla("tr")
    pencere = QtWidgets.QMainWindow()
    pencere.resize(1000, 700)
    pencere.show()
    try:
        with _KayitTutucu() as kt:
            sonuc = yardim.ac("geometri", pencere)
            uyg.processEvents()
        gs = g.etkin_gosterici()
        kontrol("ac() True dondu", sonuc is True)
        kontrol("kilavuz penceresi gorunur", gs is not None and gs.isVisible())
        kontrol("geometri capasina gidildi", gs is not None and _capa_gorunur(gs, "geometri"))
        kontrol("pencerede bildirim yok", not _bildirimler(pencere), "-> %s" % _bildirimler(pencere))
        kontrol("uyari/hata logu yok", not kt.kayitlar,
                "-> %s" % [r.getMessage() for r in kt.kayitlar][:3])
        kontrol("TR icerik yuklu, uyari seridi gizli", gs.dil == "tr" and gs.serit.isHidden())
        kontrol("icindekiler dolu (>= 11 bolum)", gs.icindekiler.topLevelItemCount() >= 11)
        yardim.ac("tukenme", pencere)
        uyg.processEvents()
        kontrol("ikinci cagri ayni pencereyi kullanir ve capaya gider",
                g.etkin_gosterici() is gs and _capa_gorunur(gs, "tukenme"))
        n = gs.ara("Shannon")
        kontrol("arama eslesme bulur ve imleci tasir", n > 0 and gs.tarayici.textCursor().hasSelection(),
                "-> %d" % n)
        kontrol("bulunmayan arama 0", gs.ara("qqzzxxyy") == 0)
        _bilinmeyen_ve_en(uyg, pencere, yardim, g, ceviri)
    finally:
        ceviri.dil_ayarla(onceki)
        gs = g.etkin_gosterici()
        if gs is not None:
            gs.close()
        pencere.close()
        pencere.deleteLater()
        uyg.processEvents()


def _bilinmeyen_ve_en(uyg, pencere, yardim, g, ceviri):
    with _KayitTutucu(YARDIM_LOGU) as kt:
        sonuc = yardim.ac("yok-boyle-bolum", pencere)
        uyg.processEvents()
    kontrol("bilinmeyen bolum: False + bildirim + log (sessiz degil)",
            sonuc is False and _bildirimler(pencere) and kt.kayitlar)
    for b in _bildirimler(pencere):
        b.close()
    ceviri.dil_ayarla("en")
    sonuc = yardim.ac("geometri", pencere)
    uyg.processEvents()
    gs = g.etkin_gosterici()
    kontrol("dil degisince EN kilavuz yuklenir", sonuc and gs.dil == "en" and _capa_gorunur(gs, "geometri"))
    # EN dosyasi eksik bir kopya: TR'ye duser ve uyari seridi gorunur
    gecici = tempfile.mkdtemp(prefix="kilavuz_")
    try:
        ky = _ky()
        shutil.copytree(ky.KILAVUZ_DIZINI, os.path.join(gecici, "k"),
                        ignore=shutil.ignore_patterns("*.png"))
        en_dizin = os.path.join(gecici, "k", "en")
        silinen = "09-sorun-giderme.md"
        if os.path.exists(os.path.join(en_dizin, silinen)):
            os.remove(os.path.join(en_dizin, silinen))
        k = ky.kilavuz("en", dizin=os.path.join(gecici, "k"))
        kontrol("EN eksik dosya TR'den alinir ve listelenir", silinen in k.eksik
                and "sorun-giderme" in k.kimlikler, "-> %s" % (k.eksik,))
        with _KayitTutucu(YARDIM_LOGU) as kt:
            gs.yukle("en", dizin=os.path.join(gecici, "k"))
            uyg.processEvents()
        kontrol("EN eksikse uyari seridi gorunur ve loglanir",
                not gs.serit.isHidden() and silinen in gs.serit.text() and kt.kayitlar)
    finally:
        shutil.rmtree(gecici, True)
        ceviri.dil_ayarla("tr")
        gs.yukle("tr")


# ----------------------------------------------------------------------------
# KL6 ekran goruntuleri
# ----------------------------------------------------------------------------
def test_ekran_goruntuleri():
    print("\n[KL6] ekran goruntuleri betikle uretilmis; girdi ozeti guncel mi (UYARI)")
    import importlib.util
    yol = os.path.join(KOK, "araclar", "kilavuz_ekran.py")
    kontrol("araclar/kilavuz_ekran.py var", os.path.exists(yol))
    belirtim = importlib.util.spec_from_file_location("kilavuz_ekran", yol)
    modul = importlib.util.module_from_spec(belirtim)
    belirtim.loader.exec_module(modul)
    ky = _ky()
    tr_manifest = os.path.join(ky.KILAVUZ_DIZINI, "resimler", "tr", modul.MANIFEST)
    kontrol("TR ekran manifesti var", os.path.exists(tr_manifest))
    with open(tr_manifest, encoding="utf-8") as f:
        kayit = json.load(f)
    adlar = {e["ad"] for e in modul.EKRANLAR}
    kontrol("manifest betigin ekran listesini kapsar", set(kayit.get("ekranlar", {})) == adlar,
            "-> %s" % sorted(adlar ^ set(kayit.get("ekranlar", {}))))
    yok = [a for a in adlar if not os.path.exists(os.path.join(os.path.dirname(tr_manifest), a + ".png"))]
    kontrol("her TR ekran dosyasi var", not yok, "-> %s" % yok)
    boyut = sum(os.path.getsize(p) for p in glob.glob(os.path.join(os.path.dirname(tr_manifest), "*.png")))
    kontrol("TR ekranlari kucuk (toplam < 4 MB)", boyut < 4 * 1024 * 1024, "-> %.1f MB" % (boyut / 2 ** 20))
    guncel = modul.girdi_ozeti("tr")
    if kayit.get("girdi_ozeti") != guncel:
        print("  [UYARI] TR ekran goruntuleri eski olabilir (arayuz ya da ornekler degisti): "
              "python araclar/kilavuz_ekran.py --dil tr")
    else:
        print("  [BILGI] TR ekran goruntuleri guncel")
    en_manifest = os.path.join(ky.KILAVUZ_DIZINI, "resimler", "en", modul.MANIFEST)
    if not os.path.exists(en_manifest):
        print("  [BILGI] EN ekran goruntuleri henuz yok (Ajan 12 birlesince): "
              "python araclar/kilavuz_ekran.py --dil en; EN kilavuz TR goruntulerine duser")
    kontrol("girdi_ozeti dile gore degisir (betik dil parametreli)",
            modul.girdi_ozeti("tr") != modul.girdi_ozeti("en"))


# ----------------------------------------------------------------------------
# KL7 sorun giderme kapsami
# ----------------------------------------------------------------------------
def kural_kimlikleri():
    from cekirdek.uygunluk_denetimi import kurallar
    ana = {k.kimlik for k in kurallar.tum_kurallar()}
    alt = set()
    for yol in glob.glob(os.path.join(KOK, "cekirdek", "uygunluk_denetimi", "*.py")):
        with open(yol, encoding="utf-8") as f:
            alt |= set(re.findall(r"\"(K[0-9]+-[A-Za-z_]+)\"", f.read()))
    return ana, alt


def bulgu_onekleri():
    from cekirdek.dogrula import _ortak
    return {onek for onek, _ad in _ortak._YER_ETIKETI} | {"geometri:", "uygunluk:"}


def test_sorun_giderme_kapsami():
    print("\n[KL7] bolum 9: her uygunluk kurali ve bulgu yer oneki TR ve EN'de")
    ana, alt = kural_kimlikleri()
    kontrol("kural kaydi bos degil", len(ana) >= 16, "-> %d" % len(ana))
    onekler = bulgu_onekleri()
    for dil in ("tr", "en"):
        metin = "\n".join(_metin(dil, "09").values())
        kontrol("%s bolum 9 var" % dil.upper(), bool(metin))
        for ad, kume in (("kural", ana), ("alt kural", alt)):
            yok = sorted(k for k in kume if not re.search(r"(?<![A-Za-z0-9-])%s(?![A-Za-z0-9_-])"
                                                          % re.escape(k), metin))
            kontrol("%s bolum 9: her %s kimligi (%d)" % (dil.upper(), ad, len(kume)), not yok,
                    "-> %s" % yok)
        kodlar = set(re.findall(r"`([^`\n]+)`", metin))
        yok = sorted(o for o in onekler if not any(k.startswith(o.rstrip()) for k in kodlar))
        kontrol("%s bolum 9: her bulgu yer oneki ters tirnakta (%d)" % (dil.upper(), len(onekler)),
                not yok, "-> %s" % yok)


# ----------------------------------------------------------------------------
# KL8 derleme ve sozluk
# ----------------------------------------------------------------------------
def test_derleme_ve_sozluk():
    print("\n[KL8] HTML + PDF uretilir; sozluk SOZLUK.md'nin her terimini icerir")
    _qt()
    from arayuz.yardim import derle
    gecici = tempfile.mkdtemp(prefix="kilavuz_derle_")
    try:
        yollar = derle.derle(("tr",), gecici, bicimler=("html", "pdf"))
        html = os.path.join(gecici, "tr", "kilavuz.html")
        pdf = os.path.join(gecici, "tr", "kilavuz.pdf")
        kontrol("HTML ve PDF yazildi", os.path.exists(html) and os.path.exists(pdf), "-> %s" % yollar)
        with open(html, encoding="utf-8") as f:
            icerik = f.read()
        kontrol("HTML'de bolum capalari ve ic baglantilar korunur",
                'name="geometri"' in icerik and 'href="#' in icerik)
        resimler = re.findall(r'<img src="([^"]+)"', icerik)
        yok = [r for r in resimler if not os.path.exists(os.path.join(gecici, "tr", r))]
        kontrol("HTML'deki resimler cikti dizininde", resimler and not yok, "-> %s" % yok[:3])
        kontrol("PDF bos degil (> 50 kB)", os.path.getsize(pdf) > 50 * 1024)
        kontrol("derle CLI: bilinmeyen dil -> 2", derle.main(["--dil", "xx"]) == 2)
        kontrol("derle CLI: EN yalniz HTML -> 0",
                derle.main(["--dil", "en", "--cikti", gecici, "--bicim", "html"]) == 0
                and os.path.exists(os.path.join(gecici, "en", "kilavuz.html")))
        ky = _ky()
        kopya = os.path.join(gecici, "kaynak")
        shutil.copytree(ky.KILAVUZ_DIZINI, kopya, ignore=shutil.ignore_patterns("*.png"))
        derle.sozluk_yenile(dizin=kopya)
        ayni = all(ky.dosya_oku(d, derle.SOZLUK_DOSYASI, kopya) == ky.dosya_oku(d, derle.SOZLUK_DOSYASI)
                   for d in ky.DILLER)
        kontrol("10-sozluk.md tablolari SOZLUK.md ile guncel (araclar/kilavuz.sh --sozluk)", ayni)
    finally:
        shutil.rmtree(gecici, True)
    terimler = derle.sozluk_terimleri()
    kontrol("SOZLUK.md'den terim okundu (>= 150)", len(terimler) >= 150, "-> %d" % len(terimler))
    for dil, sutun in (("tr", 0), ("en", 1)):
        metin = _duz("\n".join(_metin(dil, "10").values()))
        yok = [t[sutun] for t in terimler if _duz(t[sutun]) not in metin]
        kontrol("%s sozluk: SOZLUK.md'nin her terimi" % dil.upper(), not yok,
                "-> %s; yeniden uretin: araclar/kilavuz.sh --sozluk" % yok[:6])
    kontrol("araclar/kilavuz.sh var ve calistirilabilir",
            os.access(os.path.join(KOK, "araclar", "kilavuz.sh"), os.X_OK))


HIZLI = [test_bolum_kimlikleri, test_bolum4_alanlari, test_ornek_yollari_ve_komutlar,
         test_tr_en_esligi, test_uygulama_ici_gosterim, test_ekran_goruntuleri,
         test_sorun_giderme_kapsami, test_derleme_ve_sozluk]
YAVAS = []
