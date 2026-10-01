# -*- coding: utf-8 -*-
"""
izlenebilirlik.py -- gereksinim -> test -> son sonuc matrisi (Dalga S-4, Y1).

  python araclar/izlenebilirlik.py                       # docs/IZLENEBILIRLIK.md
  python araclar/izlenebilirlik.py --junit hizli.xml --junit yavas.xml
  python araclar/izlenebilirlik.py --json rapor.json     # pytest-json-report
  python araclar/izlenebilirlik.py --denetle             # cikis 1: testsiz T / tanimsiz kimlik

Girdiler
  docs/GEREKSINIMLER.md   `| R-XX-NN | metin | kaynak | T/İ/A |` satirlari
  testler/test_*.py       HIZLI / YAVAS listelerindeki islevler; @gereksinim(...)
                          isareti islevde `gereksinimler` niteligini birakir
  sonuc dosyalari         pytest --junitxml (ya da pytest-json-report) ciktisi;
                          verilmezse test_sonuclari/*.xml aranir; hic yoksa her
                          test "çalıştırılmadı" yazilir (sonuc UYDURULMAZ).

Test modulleri ICE AKTARILIR (AST degil): bazi listeler baska modulden
birlestiriliyor (ornek test_geometri_ui = yerel + geometri_ui_arayuz.HIZLI).
"""

import argparse
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import OrderedDict, namedtuple

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

from cekirdek.ceviri import _  # noqa: E402
from cekirdek.gunluk import kaydedici  # noqa: E402

_log = kaydedici(__name__)

GEREKSINIM_BELGESI = os.path.join(KOK, "docs", "GEREKSINIMLER.md")
CIKTI = os.path.join(KOK, "docs", "IZLENEBILIRLIK.md")
VARSAYILAN_SONUCLAR = os.path.join(KOK, "test_sonuclari", "*.xml")

# Fizik / esdegerlik / uygunluk / rapor / tukenme / guc / kalite kapilari:
# bu modullerde gereksinimsiz test "gereksinimsiz kritik test" olarak listelenir.
KRITIK_MODULLER = (
    "test_capa", "test_betik", "test_betik_kacis", "test_geometri_esdegerlik",
    "test_altigen_esdeger", "test_geometri_fizik", "test_dogrulama_kapisi", "test_goc",
    "test_uygunluk_denetimi", "test_uygunluk_arayuz", "test_rapor", "test_tukenme_temel",
    "test_tukenme_hacim", "test_guc", "test_guc_kor", "test_hata_yutma", "test_benchmark",
    "test_vv", "test_kapsul", "test_izlenebilirlik",
)

GECTI, KALDI, ATLANDI, CALISMADI = "geçti", "KALDI", "atlandı", "çalıştırılmadı"
TESTSIZ, INCELEME = "TESTSİZ", "inceleme"

_SATIR = re.compile(r"^\|\s*(R-[A-Z0-9]+-\d{2})\s*\|(.*)\|\s*$")

Gereksinim = namedtuple("Gereksinim", "kimlik metin kaynak yontem")
TestKaydi = namedtuple("TestKaydi", "modul ad tur gereksinimler")


# ============================================================================
# GIRDILER
# ============================================================================

def gereksinimleri_oku(yol=GEREKSINIM_BELGESI):
    """OrderedDict {kimlik: Gereksinim}; ayni kimlik iki kez yazilmissa ValueError."""
    sonuc = OrderedDict()
    with open(yol, encoding="utf-8") as f:
        for satir in f:
            m = _SATIR.match(satir.strip())
            if not m:
                continue
            hucreler = [h.strip() for h in m.group(2).split("|")]
            if len(hucreler) != 3:
                raise ValueError("%s: 4 sütun bekleniyordu: %s" % (m.group(1), satir.strip()))
            if m.group(1) in sonuc:
                raise ValueError("gereksinim kimliği iki kez tanımlı: %s" % m.group(1))
            sonuc[m.group(1)] = Gereksinim(m.group(1), *hucreler)
    return sonuc


def _kayitlar(modul_adi, islevler, tur):
    return [TestKaydi(modul_adi, fn.__name__, tur, tuple(getattr(fn, "gereksinimler", ())))
            for fn in islevler]


def testleri_topla(moduller=None):
    """[TestKaydi] -- eski calistiricinin (ve conftest koprusunun) kostugu
    HIZLI/YAVAS listeleri. moduller verilmezse testler/test_*.py ice aktarilir."""
    if moduller is None:
        from testler import ortak_test
        moduller = ortak_test.ek_moduller()
    kayitlar = []
    for modul in moduller:
        ad = modul.__name__.rsplit(".", 1)[-1]
        kayitlar += _kayitlar(ad, getattr(modul, "HIZLI", []) or [], "hizli")
        kayitlar += _kayitlar(ad, getattr(modul, "YAVAS", []) or [], "yavas")
    return kayitlar


def _junit_oku(yol):
    """({(modul, ad): durum}, (yol, zaman, sayi))"""
    kok = ET.parse(yol).getroot()
    takimlar = [kok] if kok.tag == "testsuite" else kok.findall("testsuite")
    durumlar, zaman = {}, None
    for takim in takimlar:
        zaman = zaman or takim.get("timestamp")
        for tc in takim.iter("testcase"):
            modul = (tc.get("classname") or "").rsplit(".", 1)[-1]
            ad = re.sub(r"\[.*\]$", "", tc.get("name") or "")
            if tc.find("failure") is not None or tc.find("error") is not None:
                durum = KALDI
            elif tc.find("skipped") is not None:
                durum = ATLANDI
            else:
                durum = GECTI
            durumlar[(modul, ad)] = durum
    return durumlar, (yol, zaman, len(durumlar))


_JSON_DURUM = {"passed": GECTI, "failed": KALDI, "error": KALDI, "skipped": ATLANDI,
               "xfailed": ATLANDI, "xpassed": GECTI}


def _json_oku(yol):
    """pytest-json-report: {"created": ..., "tests": [{"nodeid", "outcome"}]}"""
    with open(yol, encoding="utf-8") as f:
        veri = json.load(f)
    durumlar = {}
    for t in veri.get("tests", []):
        dosya, _ayr, ad = t.get("nodeid", "").partition("::")
        modul = os.path.splitext(os.path.basename(dosya))[0]
        durumlar[(modul, re.sub(r"\[.*\]$", "", ad))] = _JSON_DURUM.get(t.get("outcome"), KALDI)
    return durumlar, (yol, str(veri.get("created", "")) or None, len(durumlar))


def _birlestir(eski, yeni):
    """Ayni test iki dosyada: KALDI > geçti > atlandı (en kotu sonuc kazanir)."""
    sira = {KALDI: 3, GECTI: 2, ATLANDI: 1}
    return eski if sira.get(eski, 0) >= sira.get(yeni, 0) else yeni


def sonuclari_oku(junit=(), jsonlar=()):
    """({(modul, ad): durum}, [(yol, zaman, sayi)]). Okunamayan dosya loglanir
    ve atlanir; kaynak listesinde yer almaz."""
    durumlar, kaynaklar = {}, []
    for yol, okuyucu in [(y, _junit_oku) for y in junit] + [(y, _json_oku) for y in jsonlar]:
        try:
            d, kaynak = okuyucu(yol)
        except (OSError, ET.ParseError, ValueError) as e:
            _log.warning("test sonuç dosyası okunamadı: %s (%s)", yol, e)
            print(_("uyarı: test sonuç dosyası okunamadı: %s (%s)") % (yol, e), file=sys.stderr)
            continue
        for anahtar, durum in d.items():
            durumlar[anahtar] = _birlestir(durumlar[anahtar], durum) if anahtar in durumlar \
                else durum
        kaynaklar.append(kaynak)
    return durumlar, kaynaklar


# ============================================================================
# MATRIS
# ============================================================================

def test_durumu(kayit, durumlar):
    return durumlar.get((kayit.modul, kayit.ad), CALISMADI)


def gereksinim_durumu(gereksinim, bagli, durumlar):
    """Bir gereksinimin ozet durumu (bagli: o gereksinime bagli TestKaydi'lar)."""
    if not bagli:
        return TESTSIZ if gereksinim.yontem == "T" else INCELEME
    sonuclar = [test_durumu(k, durumlar) for k in bagli]
    if KALDI in sonuclar:
        return KALDI
    gecen = sonuclar.count(GECTI)
    if gecen == len(sonuclar):
        return GECTI
    if gecen == 0:
        return ATLANDI if ATLANDI in sonuclar else CALISMADI
    return "kısmen (%d/%d geçti)" % (gecen, len(sonuclar))


def matris(gereksinimler, kayitlar, durumlar):
    """[(Gereksinim, [TestKaydi], durum)] belge sirasiyla."""
    bagli = {k: [] for k in gereksinimler}
    for kayit in kayitlar:
        for kimlik in kayit.gereksinimler:
            if kimlik in bagli:
                bagli[kimlik].append(kayit)
    return [(g, bagli[k], gereksinim_durumu(g, bagli[k], durumlar))
            for k, g in gereksinimler.items()]


def tanimsiz_kimlikler(gereksinimler, kayitlar):
    """[(TestKaydi, kimlik)] -- belgede olmayan kimlige bagli testler."""
    return [(k, kimlik) for k in kayitlar for kimlik in k.gereksinimler
            if kimlik not in gereksinimler]


def gereksinimsiz_kritik(kayitlar, kritik=KRITIK_MODULLER):
    return [k for k in kayitlar if k.modul in kritik and not k.gereksinimler]


def testsiz(satirlar):
    return [g for g, _b, durum in satirlar if durum == TESTSIZ]


# ============================================================================
# CIKTI
# ============================================================================

def _test_metni(kayit, durumlar):
    return "`%s:%s` (%s) — %s" % (kayit.modul, kayit.ad, kayit.tur, test_durumu(kayit, durumlar))


def _kaynak_satirlari(kaynaklar):
    if not kaynaklar:
        return ["Sonuç dosyası verilmedi: bütün testler **%s** sayılır (sonuç uydurulmaz)."
                % CALISMADI]
    return ["- `%s` — %s, %d test" % (_gosterim_yolu(yol), zaman or "zaman yok", sayi)
            for yol, zaman, sayi in kaynaklar]


def _gosterim_yolu(yol):
    """Depo icindeyse goreli yol, disindaysa yalniz dosya adi (yerel yol sizmasin)."""
    tam = os.path.abspath(yol)
    if tam.startswith(KOK + os.sep):
        return os.path.relpath(tam, KOK)
    return os.path.basename(tam)


def _ozet_satirlari(satirlar, kayitlar):
    sayac = OrderedDict()
    for _g, _b, durum in satirlar:
        anahtar = "kısmen" if durum.startswith("kısmen") else durum
        sayac[anahtar] = sayac.get(anahtar, 0) + 1
    bagli = sum(1 for k in kayitlar if k.gereksinimler)
    return (["- Gereksinim: %d (%s)" % (len(satirlar), ", ".join(
                "%s %d" % (d, n) for d, n in sayac.items())),
             "- Toplanan test: %d; gereksinime bağlı: %d; bağsız: %d"
             % (len(kayitlar), bagli, len(kayitlar) - bagli)])


def _matris_satirlari(satirlar, durumlar):
    cikti = ["| Kimlik | Yöntem | Durum | Testler |", "|---|---|---|---|"]
    for g, bagli, durum in satirlar:
        testler = "<br>".join(_test_metni(k, durumlar) for k in bagli) or "—"
        cikti.append("| %s | %s | %s | %s |" % (g.kimlik, g.yontem, durum, testler))
    return cikti


def markdown(gereksinimler, kayitlar, durumlar, kaynaklar):
    satirlar = matris(gereksinimler, kayitlar, durumlar)
    tanimsiz = tanimsiz_kimlikler(gereksinimler, kayitlar)
    kritik = gereksinimsiz_kritik(kayitlar)
    parca = [
        "# İzlenebilirlik matrisi (üretilir — elle düzenlemeyin)", "",
        "Üreten: `python araclar/izlenebilirlik.py`. Gereksinimler: `docs/GEREKSINIMLER.md`; "
        "test işareti: `@gereksinim(\"R-…\")` (`testler/ortak_test.py`). Bu matris bir "
        "uygunluk sertifikası değildir; hangi gereksinimin hangi testle ve hangi son sonuçla "
        "kanıtlandığını ve **nerede kanıt olmadığını** gösterir.", "",
        "## Sonuç kaynakları", ""] + _kaynak_satirlari(kaynaklar) + [
        "", "## Özet", ""] + _ozet_satirlari(satirlar, kayitlar) + [
        "", "## Gereksinim → test → son sonuç", ""] + _matris_satirlari(satirlar, durumlar) + [
        "", "## Testsiz gereksinimler (yöntem T, bağlı test yok)", ""]
    parca += ["- %s — %s" % (g.kimlik, g.metin) for g in testsiz(satirlar)] or ["Yok."]
    parca += ["", "## Test dışı doğrulanan gereksinimler (İ / A)", ""]
    parca += ["- %s (%s) — %s" % (g.kimlik, g.yontem, g.metin)
              for g, _b, durum in satirlar if durum == INCELEME] or ["Yok."]
    parca += ["", "## Tanımsız kimliğe bağlı testler", ""]
    parca += ["- `%s:%s` → %s" % (k.modul, k.ad, kimlik) for k, kimlik in tanimsiz] or ["Yok."]
    parca += ["", "## Gereksinimsiz kritik testler", "",
              "Kritik modüller: %s." % ", ".join("`%s`" % m for m in KRITIK_MODULLER), ""]
    parca += ["- `%s:%s` (%s)" % (k.modul, k.ad, k.tur) for k in kritik] or ["Yok."]
    return "\n".join(parca) + "\n"


# ============================================================================
# KOMUT SATIRI
# ============================================================================

def _argumanlar(argv):
    p = argparse.ArgumentParser(description=_("Gereksinim → test → sonuç matrisi üretir."))
    p.add_argument("--junit", action="append", default=None,
                   help=_("pytest --junitxml çıktısı (birden çok verilebilir)"))
    p.add_argument("--json", action="append", default=[],
                   help=_("pytest-json-report çıktısı (birden çok verilebilir)"))
    p.add_argument("-o", "--cikti", default=CIKTI, help=_("yazılacak Markdown dosyası"))
    p.add_argument("--gereksinimler", default=GEREKSINIM_BELGESI)
    p.add_argument("--denetle", action="store_true",
                   help=_("testsiz T gereksinimi ya da tanımsız kimlik varsa çıkış 1"))
    return p.parse_args(argv)


def main(argv=None):
    a = _argumanlar(sys.argv[1:] if argv is None else argv)
    junit = a.junit if a.junit is not None else sorted(glob.glob(VARSAYILAN_SONUCLAR))
    gereksinimler = gereksinimleri_oku(a.gereksinimler)
    kayitlar = testleri_topla()
    durumlar, kaynaklar = sonuclari_oku(junit, a.json)
    with open(a.cikti, "w", encoding="utf-8") as f:
        f.write(markdown(gereksinimler, kayitlar, durumlar, kaynaklar))
    satirlar = matris(gereksinimler, kayitlar, durumlar)
    eksik, tanimsiz = testsiz(satirlar), tanimsiz_kimlikler(gereksinimler, kayitlar)
    print(_("yazıldı: %s — %d gereksinim, %d testsiz, %d tanımsız kimlik")
          % (a.cikti, len(satirlar), len(eksik), len(tanimsiz)))
    return 1 if a.denetle and (eksik or tanimsiz) else 0


if __name__ == "__main__":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    sys.exit(main())
