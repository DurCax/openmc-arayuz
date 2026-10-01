# -*- coding: utf-8 -*-
"""
dil_en_yardimci.py -- test_dil.py EN modunun yardimcilari (test modulu DEGIL).

  en_kipi()            Ingilizce katalog (locale/en/LC_MESSAGES/*.po -> gecici .mo),
                       ceviri.dil_ayarla("en") ve Qt cevirmeni; cikista "tr"ye doner.
                       Toplayici.eksik: cevirisi bulunamayan msgid'ler.
  arayuz_katalogu()    locale/en/LC_MESSAGES/arayuz.po (babel Catalog) ya da None.
  arayuz_msgidleri()   arayuz/ kaynaklarindan Babel'in cikardigi msgid kumesi.
  cekirdek_parcalari() cekirdek/ dizgi sabitlerinin Turkce karakterli parcalari
                       (gorunen metnin kaynagini ayirmak icin: cekirdek mi, arayuz mu).
  sozluk_terimleri()   docs/SOZLUK.md -> [(turkce, (ingilizce...), (kacin...))].
  terim_ihlalleri(), yer_tutucu_ihlalleri()   .po denetimleri.

Kaynak ayrimi (Ajan 11 birlesmeden once cekirdek metinleri EN'de Turkce kalabilir):
gorunen Turkce metin bir cekirdek dizgi parcasini iceriyorsa "cekirdek", yoksa
"arayuz" sayilir. Arayuz kaynakli bulgu 0 olmalidir; cekirdek kaynakli bilgi.
"""

import ast
import contextlib
import glob
import logging
import os
import re
import shutil
import tempfile

from testler.ortak_test import KOK

LOCALE = os.path.join(KOK, "locale")
EN_DIZINI = os.path.join(LOCALE, "en", "LC_MESSAGES")
ANAHTARLAR = {"_": None, "N_": None, "_n": (1, 2), "pgettext": ((1, "c"), 2)}
TR_HARF = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
# Yer tutucular: {ad}, {n:.3f}, %s, %d, %.4f, %(ad)s
_YER_TUTUCU = re.compile(r"\{[^{}]*\}|%\([a-z_]+\)[sdfrgx]|%[-+0#]*\d*(?:\.\d+)?[sdfrgeEx]")
_ETIKET = re.compile(r"</?([a-zA-Z0-9]+)")


# ----------------------------------------------------------------------------
# kataloglar
# ----------------------------------------------------------------------------

def po_oku(yol):
    from babel.messages.pofile import read_po
    with open(yol, "rb") as f:
        return read_po(f, locale="en")


def arayuz_katalogu():
    yol = os.path.join(EN_DIZINI, "arayuz.po")
    return po_oku(yol) if os.path.exists(yol) else None


def _dolu(m):
    if isinstance(m.string, (tuple, list)):
        return all(m.string)
    return bool(m.string)


def katalog_derle(hedef):
    """openmc_arayuz.po (taban) + cekirdek.po + arayuz.po -> hedef/en/LC_MESSAGES/*.mo.
    Parcalar tabanin uzerine yazar (Ajan 11/12 parcalari birlesik katalogdan yenidir)."""
    from babel.messages.catalog import Catalog
    from babel.messages.mofile import write_mo
    kat = Catalog(locale="en", domain="openmc_arayuz")
    for ad in ("openmc_arayuz.po", "cekirdek.po", "arayuz.po"):
        yol = os.path.join(EN_DIZINI, ad)
        if not os.path.exists(yol):
            continue
        for m in po_oku(yol):
            if m.id and _dolu(m) and not m.fuzzy:
                kat.add(m.id, m.string, context=m.context)
    dizin = os.path.join(hedef, "en", "LC_MESSAGES")
    os.makedirs(dizin, exist_ok=True)
    with open(os.path.join(dizin, "openmc_arayuz.mo"), "wb") as f:
        write_mo(f, kat)
    return hedef


class Toplayici(logging.Handler):
    """ceviri kaydedicisinin "ceviri eksik" uyarilarini toplar."""

    _DESEN = re.compile(r"ceviri eksik \(\w+\): (.*)$", re.S)

    def __init__(self):
        super().__init__(logging.WARNING)
        self.eksik = set()

    def emit(self, kayit):
        x = self._DESEN.search(kayit.getMessage())
        if x:
            try:
                self.eksik.add(ast.literal_eval(x.group(1)))
            except (ValueError, SyntaxError):
                self.eksik.add(x.group(1))


@contextlib.contextmanager
def en_kipi():
    """Ingilizce arayuz: katalog gecici dizine derlenir; cikista Turkceye doner."""
    from cekirdek import ceviri
    from PySide6 import QtWidgets
    from arayuz.ortak import qt_cevirisi_kur
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    gecici = tempfile.mkdtemp(prefix="openmc_arayuz_en_")
    eski_dizin, eski_dil = ceviri.LOCALE_DIZINI, ceviri.etkin_dil()
    top = Toplayici()
    kaydedici = logging.getLogger(ceviri.KAYDEDICI_ADI)
    kaydedici.addHandler(top)
    try:
        ceviri.LOCALE_DIZINI = katalog_derle(gecici)
        ceviri.dil_ayarla("en")
        qt_cevirisi_kur(uyg, "en")
        yield top
    finally:
        kaydedici.removeHandler(top)
        ceviri.LOCALE_DIZINI = eski_dizin
        ceviri.dil_ayarla(eski_dil)
        qt_cevirisi_kur(uyg, "en")          # testlerin varsayilani: Qt cevirmeni yok
        shutil.rmtree(gecici, True)


# ----------------------------------------------------------------------------
# kaynak msgid'leri ve parcalar
# ----------------------------------------------------------------------------

def _msgidler(dizin):
    from babel.messages.extract import extract_from_dir
    out = set()
    for _d, _s, metin, _y, baglam in extract_from_dir(
            dizin, method_map=[("**.py", "python")], keywords=ANAHTARLAR,
            comment_tags=(), strip_comment_tags=True):
        tekil = metin[0] if isinstance(metin, (tuple, list)) else metin
        if tekil:
            out.add((baglam, tekil))
    return out


def arayuz_msgidleri():
    """{(baglam, msgid)} -- arayuz/ altindan (Babel, ceviri.sh ile ayni anahtarlar)."""
    return _msgidler(os.path.join(KOK, "arayuz"))


def _sabitler(dizin):
    for yol in glob.glob(os.path.join(dizin, "**", "*.py"), recursive=True):
        with open(yol, encoding="utf-8") as f:
            agac = ast.parse(f.read())
        for n in ast.walk(agac):
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                yield n.value


def dizgi_parcalari(kok, en_az=6):
    """kok/ (cekirdek ya da arayuz) dizgi sabitlerinin yer tutucularla bolunmus,
    Turkce karakterli parcalari."""
    parcalar = set()
    for s in _sabitler(os.path.join(KOK, kok)):
        for p in _YER_TUTUCU.split(s):
            for satir in p.split("\n"):
                satir = satir.strip(" .,:;()—-")
                if len(satir) >= en_az and TR_HARF.search(satir):
                    parcalar.add(satir)
    return parcalar


def cekirdek_parcalari(en_az=6):
    """(cekirdek parcalari, arayuz parcalari) -- kaynak_sinifi icin."""
    return dizgi_parcalari("cekirdek", en_az), dizgi_parcalari("arayuz", en_az)


def kaynak_sinifi(metin, parcalar):
    """Gorunen Turkce satirin kaynagi: icerdigi EN UZUN cekirdek parcasi, en uzun arayuz
    parcasindan uzunsa "cekirdek", degilse "arayuz" (esitlikte arayuz: siki)."""
    cekirdek, arayuz = parcalar

    def en_uzun(kume):
        return max((len(p) for p in kume if p in metin), default=0)
    return "cekirdek" if en_uzun(cekirdek) > en_uzun(arayuz) else "arayuz"


def kullanici_verisi(spec):
    """Spec'teki kullanici verisi (ad, gorunen_ad, aciklama, baslik...): EN'de de Turkce
    kalabilir (model verisidir, arayuz metni degil)."""
    out = set()

    def gez(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("ad", "gorunen_ad", "aciklama", "baslik", "not", "dizin") \
                        and isinstance(v, str) and v.strip():
                    out.add(v.strip())
                else:
                    gez(v)
        elif isinstance(x, list):
            for v in x:
                gez(v)
    gez(spec)
    return out


# ----------------------------------------------------------------------------
# .po denetimleri
# ----------------------------------------------------------------------------

def _metinler(m):
    ids = m.id if isinstance(m.id, (tuple, list)) else (m.id,)
    strs = m.string if isinstance(m.string, (tuple, list)) else (m.string,)
    return ids, strs


def yer_tutucu_ihlalleri(katalog):
    """Yer tutucu kumesi ya da HTML etiket sayisi msgid ile msgstr arasinda farkli olanlar."""
    out = []
    for m in katalog:
        if not m.id or not _dolu(m):
            continue
        ids, strs = _metinler(m)
        beklenen = sorted(_YER_TUTUCU.findall(ids[0]))
        etiket = sorted(_ETIKET.findall(ids[0]))
        for s in strs:
            if sorted(_YER_TUTUCU.findall(s)) != beklenen:
                out.append((ids[0][:60], "yer tutucu", s[:60]))
            elif sorted(_ETIKET.findall(s)) != etiket:
                out.append((ids[0][:60], "HTML etiketi", s[:60]))
    return out


# Sozluk satirlarinin GENEL kullanim karsiliklari ve arayuz bilesik terimleri (en uzun
# eslesme kazanir: "kenar çubuğu" sidebar'dir, pin degil). Sozlukle CELISMEZ: ayni Turkce
# sozcugun sozlukte tanimlanmayan baska anlamini karsilar.
EK_TERIMLER = {
    "bölge": ("region",),                       # tally / kaynak bolgesi
    "örnek": ("e.g.", "for instance"),           # "örneğin"
    "başlangıç": ("initial", "starting"),        # başlangıç kaynağı / değeri
    "tarama": ("sweep",),
    "kenar çubuğu": ("sidebar",), "durum çubuğu": ("status bar",),
    "araç çubuğu": ("toolbar",), "ilerleme çubuğu": ("progress bar",),
    "doğrulama kümesi": ("validation set", "v&v set", "benchmark set"),
    "sonraki adım": ("next step",), "sıradaki adım": ("next step",),
    "eksik adım": ("missing step",), "adım adım": ("step by step",),
    "dönüşüm katsayı": ("conversion coefficient",),   # akı-doz dönüşüm katsayıları
    "örnek": ("e.g.", "for instance", "example", "instance"),   # Dalga G: yerleşim örneği
    "kaydet": ("record", "logged", "written"),  # "hata kaydedildi" (log)
    "kor sayfa": ("geometry page",), "kor sekme": ("geometry tab", "geometry page"),
    "bu adım": ("this step",),
    "çalıştır": ("ran",), "çalıştırılabilir": ("executable", "ready to run", "runnable"),
    "ön yüz": ("front",),
    "emici çubuk": ("absorber rod", "control rod"),
    "kılavuz": ("guide",),                      # kılavuz/ölçüm konumu = guide tube
    "doğrulama": ("check",),                    # "doğrulama yapılır" = the model is checked
}
# Tukenme sayfasinda "adım" tukenme adimidir (sozluk: tükenme adımı = depletion step):
# msgid'in kaynak dosyasi bu parcalardan birini iceriyorsa ek karsilik kabul edilir.
KONUM_KABUL = {"adım": (("tukenme",), ("step",))}
# Kontrol cubugu baglaminda "çubuk" = rod (sozluk: kontrol çubuğu = control rod).
BAGLAM_KABUL = {"çubuk": (("kontrol çubu", "emici çubu", "çubuk ucu", "çubuk değeri",
                            "kontrol grubu"), ("rod",))}
# "Kaçın" sutunu yalniz bu terimlerde ihlal sayilir: diger kacin sozcukleri metinde
# baska bir Turkce sozcugun dogru karsiligi olabilir ("reaktör" -> reactor).
KACIN_DENETLENEN = frozenset({"çubuk", "demet", "parça", "çevrim", "pasif çevrim", "kılıf",
                              "tükenme", "hesap hassasiyeti", "bulgu", "kılavuz"})
# Sozlukte grup/sayfa adi olarak gecen, metinde cok anlamli kisa sozcukler.
ATLANAN_TERIMLER = frozenset({"kap", "hesap", "sonuç", "grup", "seviye"})


def _temiz(hucre):
    return re.sub(r"[*`]", "", hucre).strip()


def _parantezsiz(metin):
    return re.sub(r"\s*\([^()]*(\([^()]*\)[^()]*)*\)", "", metin).strip()


def _parantez_ici(metin):
    x = re.search(r"\(([^()]*(\([^()]*\)[^()]*)*)\)", metin)
    return x.group(1).strip() if x else None


def sozluk_terimleri(yol=None):
    """docs/SOZLUK.md tablolari -> [(turkce, (kabul edilen ingilizce...), (kacin...))].
    "a / b" iki sutunda esit sayidaysa cift cift eslenir. Ayni Turkce kok birden cok
    satirda ise (kılıf: cladding | duct) karsiliklar birlesir."""
    yol = yol or os.path.join(KOK, "docs", "SOZLUK.md")
    terimler = {}
    with open(yol, encoding="utf-8") as f:
        for satir in f:
            if not satir.startswith("|") or satir.startswith("|---"):
                continue
            hucreler = [_temiz(h) for h in satir.strip().strip("|").split("|")]
            if len(hucreler) < 2 or hucreler[0] in ("Türkçe", ""):
                continue
            tr_, en_ = hucreler[0], hucreler[1]
            kacin = tuple(k.strip().lower() for k in re.split(
                r",|/", hucreler[2] if len(hucreler) > 2 else "") if k.strip())
            tr_lar = [t.strip() for t in tr_.split(" / ")]
            en_ler = [e.strip() for e in en_.split(" / ")]
            if len(tr_lar) != len(en_ler):
                en_ler = [en_] * len(tr_lar)
            for t, e in zip(tr_lar, en_ler):
                kok = _parantezsiz(t).lower()
                if len(kok) < 3:
                    continue
                kabul = {_parantezsiz(e).lower()}
                ic = _parantez_ici(e)
                if ic:
                    kabul.add(ic.lower())
                if kok in {k for k in kabul}:
                    continue                     # model = model: denetlenecek bir sey yok
                eski = terimler.get(kok, (set(), set()))
                terimler[kok] = (eski[0] | kabul, eski[1] | set(kacin))
    for kok, kabul in EK_TERIMLER.items():
        eski = terimler.get(kok, (set(), set()))
        terimler[kok] = (eski[0] | set(kabul), eski[1])
    return [(k, tuple(sorted(v[0])), tuple(sorted(v[1] - v[0])))
            for k, v in terimler.items() if k not in ATLANAN_TERIMLER]


def _kucuk(metin):
    return metin.replace("İ", "i").replace("I", "ı").lower()


# Kisa kokler (<= 4 harf) yalniz bu eklerle eslesir: "kor" "korunur"u tutmasin.
_KISA_EKLER = ("", "u", "ü", "ı", "i", "a", "e", "da", "de", "ta", "te", "dan", "den", "un",
               "ün", "ın", "in", "nun", "nün", "nın", "nin", "lar", "ler", "ları", "leri",
               "ların", "lerin", "larda", "lerde", "daki", "deki", "ya", "ye", "yı", "yi",
               "yu", "yü", "su", "sü", "sı", "si", "nu", "nü", "nı", "ni", "na", "ne",
               "sunda", "sündaki", "sundaki", "suna", "sunu", "sun", "nda", "ndaki")
_YUMUSAMA = {"k": "ğ", "p": "b", "t": "d", "ç": "c"}
# Ayni kokten baska sozcuk turetenler: "yüz" (face) "yüzde" (yuzde) ve "yüzden" degildir.
_OZEL_EKLER = {"yüz": ("", "ü", "ün", "üne", "ünü", "ünde", "ler", "leri", "lerin", "lerinde",
                       "lerde", "lere"),
               "dönme": ("", "si", "sı", "sini", "sine", "sinin", "ler", "leri", "yi", "ye",
                         "de", "den", "nin"),
               "bilgi": ("", "si", "sini", "ler", "leri", "lerin", "ye", "yi", "nin", "de",
                         "den", "dir")}


def _terim_deseni(kok):
    sozcukler = kok.split(" ")
    son = sozcukler[-1]
    govdeler = [re.escape(son)]
    if son[-1] in _YUMUSAMA:
        govdeler.append(re.escape(son[:-1] + _YUMUSAMA[son[-1]]))
    on = "".join(re.escape(s) + r"\w*\s+" for s in sozcukler[:-1])
    if kok in _OZEL_EKLER:
        ek = "(?:%s)" % "|".join(sorted(_OZEL_EKLER[kok], key=len, reverse=True))
    elif len(son) <= 4:
        ek = "(?:%s)" % "|".join(sorted(_KISA_EKLER, key=len, reverse=True))
    else:
        ek = r"[a-zçğıöşü]{0,8}"
    return re.compile(r"(?<!\w)%s(?:%s)%s(?!\w)" % (on, "|".join(govdeler), ek))


def _ingilizce_var(metin, kabul):
    m = metin.lower()
    for k in kabul:
        govde = k[:-3] if len(k) > 6 and k.endswith("ing") else (
            k[:-1] if len(k) > 4 and k[-1] in "yes" else k)
        sinir = "" if len(govde) >= 4 else r"(?<!\w)"
        if re.search(sinir + re.escape(govde), m):
            return True
    return False


def terim_ihlalleri(katalog, terimler=None, muaf=()):
    """Sozlukteki Turkce terimi iceren msgid'in cevirisinde sozluk karsiligi yoksa
    ya da "Kaçın" sutunundaki karsilik kullanilmissa ihlal. En uzun eslesme kazanir
    ("tükenme adımı" -> depletion step; "adım" ayrica pitch istemez)."""
    terimler = terimler if terimler is not None else sozluk_terimleri()
    desenler = [(_terim_deseni(k), k, kabul, kacin) for k, kabul, kacin in terimler]
    out = []
    for m in katalog:
        if not m.id or not _dolu(m):
            continue
        ids, strs = _metinler(m)
        if ids[0] in muaf:
            continue
        kaynak = _kucuk(_YER_TUTUCU.sub(" ", re.sub(r"<[^>]+>", " ", ids[0])))
        eslesen = []
        for desen, kok, kabul, kacin in desenler:
            for x in desen.finditer(kaynak):
                eslesen.append((x.start(), x.end(), kok, kabul, kacin))
        eslesen = [e for e in eslesen
                   if not any(o[0] <= e[0] and e[1] <= o[1] and o is not e and (
                       (o[1] - o[0]) > (e[1] - e[0]) or len(o[2]) > len(e[2]))
                       for o in eslesen)]
        tum_kabul = {k for e in eslesen for k in e[3]}
        for s in strs:
            for _b, _s, kok, kabul, kacin in eslesen:
                baglam, ek = BAGLAM_KABUL.get(kok, ((), ()))
                if any(b in kaynak for b in baglam):
                    kabul = kabul + ek
                konum, ek = KONUM_KABUL.get(kok, ((), ()))
                if any(k in yol for k in konum for yol, _n in getattr(m, "locations", ())):
                    kabul = kabul + ek
                if not _ingilizce_var(s, kabul):
                    out.append((ids[0][:70], kok, "/".join(kabul), s[:70]))
                    continue
                for k in (kacin if kok in KACIN_DENETLENEN else ()):
                    if k in kabul:
                        continue
                    if re.search(r"(?<!\w)%s(?!\w)" % re.escape(k), s.lower()) and \
                            not any(k in t for t in tum_kabul):
                        out.append((ids[0][:70], kok, "kaçın: " + k, s[:70]))
    return out


# ----------------------------------------------------------------------------
# kirpilma ve uzama
# ----------------------------------------------------------------------------

def kirpik_mi(w):
    """Gorunur, sarmasiz QLabel/QPushButton metni genisligine sigmiyor mu."""
    from PySide6 import QtWidgets
    if not w.isVisible() or w.width() <= 0:
        return False
    if isinstance(w, QtWidgets.QLabel):
        if w.wordWrap() or not w.text().strip() or w.pixmap() is not None and \
                not w.pixmap().isNull():
            return False
    elif isinstance(w, QtWidgets.QPushButton):
        if not w.text().strip():
            return False
    else:
        return False
    return w.sizeHint().width() > w.width() + 1


def uzama_orani(w, turkce):
    """Dugmenin Ingilizce metni Turkcesine gore kac kat genis (yazi olcusuyle)."""
    fm = w.fontMetrics()
    en = fm.horizontalAdvance(w.text().replace("&", ""))
    tr_ = fm.horizontalAdvance(turkce.replace("&", ""))
    return en / tr_ if tr_ else 1.0
