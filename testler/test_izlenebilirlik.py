# -*- coding: utf-8 -*-
"""
test_izlenebilirlik.py -- Dalga S-4 (Y1): gereksinim isareti, GEREKSINIMLER.md
ve araclar/izlenebilirlik.py matrisi.
"""

import importlib.util
import os
import shutil
import tempfile

from testler.ortak_test import kontrol, KOK, gereksinim


def _arac():
    yol = os.path.join(KOK, "araclar", "izlenebilirlik.py")
    spec = importlib.util.spec_from_file_location("araclar_izlenebilirlik", yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _junit(yol, satirlar):
    govde = "".join(
        '<testcase classname="testler.%s" name="%s" time="0.1">%s</testcase>' % (m, a, ic)
        for m, a, ic in satirlar)
    with open(yol, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest" '
                'timestamp="2026-10-01T12:00:00" tests="%d">%s</testsuite></testsuites>'
                % (len(satirlar), govde))


@gereksinim("R-S-15")
def test_gereksinim_isareti():
    print("\n[IZ1] gereksinim(): ayni islev doner, nitelik + pytest isareti, gecersiz kimlik")
    import pytest

    def ornek():
        return 7
    donen = gereksinim("R-FZ-01")(ornek)
    kontrol("ayni islev nesnesi", donen is ornek)
    kontrol("gereksinimler niteligi", ornek.gereksinimler == ("R-FZ-01",))
    gereksinim("R-FZ-02", "R-FZ-01")(ornek)
    kontrol("ust uste isaret birlesir, tekrar yok",
            ornek.gereksinimler == ("R-FZ-01", "R-FZ-02"), "-> %r" % (ornek.gereksinimler,))
    isaretler = [m for m in getattr(ornek, "pytestmark", []) if m.name == "gereksinim"]
    kontrol("pytest isareti", len(isaretler) == 2 and isaretler[0].args == ("R-FZ-01",))
    kontrol("govde degismedi", ornek() == 7)
    for kotu in ("R-1", "X-FZ-01", "r-fz-01", 3):
        with pytest.raises(ValueError):
            gereksinim(kotu)
    with pytest.raises(ValueError):
        gereksinim()
    kontrol("gecersiz kimlikler reddedildi", True)


@gereksinim("R-S-15")
def test_gereksinim_belgesi():
    print("\n[IZ2] docs/GEREKSINIMLER.md: benzersiz kimlik, tek cumle, yontem T/I/A")
    arac = _arac()
    g = arac.gereksinimleri_oku()
    kontrol("en az 40 gereksinim", len(g) >= 40, "-> %d" % len(g))
    kotu_yontem = [k for k, v in g.items() if v.yontem not in ("T", "İ", "A")]
    kontrol("yontem T/İ/A", not kotu_yontem, "-> %s" % kotu_yontem)
    cok_cumle = [k for k, v in g.items()
                 if not v.metin.endswith(".") or ". " in v.metin.rstrip(".")]
    kontrol("her gereksinim tek cumle", not cok_cumle, "-> %s" % cok_cumle)
    kaynaksiz = [k for k, v in g.items() if not v.kaynak]
    kontrol("her gereksinimin kaynagi var", not kaynaksiz, "-> %s" % kaynaksiz)
    gruplar = {k.split("-")[1] for k in g}
    for grup in ("FZ", "A1", "A2", "A3", "A4", "M1", "M5", "M9", "M10", "TK", "G", "S"):
        kontrol("grup %s var" % grup, grup in gruplar)
    # cift kimlik reddedilir
    d = tempfile.mkdtemp()
    try:
        yol = os.path.join(d, "g.md")
        with open(yol, "w", encoding="utf-8") as f:
            f.write("| R-X-01 | a. | k | T |\n| R-X-01 | b. | k | T |\n")
        try:
            arac.gereksinimleri_oku(yol)
            kontrol("cift kimlik ValueError", False)
        except ValueError:
            kontrol("cift kimlik ValueError", True)
    finally:
        shutil.rmtree(d, True)


@gereksinim("R-S-15")
def test_testler_tanimli_kimlik_kullanir():
    print("\n[IZ3] butun @gereksinim kimlikleri belgede tanimli; kritik baglar yerinde")
    arac = _arac()
    g = arac.gereksinimleri_oku()
    kayitlar = arac.testleri_topla()
    tanimsiz = arac.tanimsiz_kimlikler(g, kayitlar)
    kontrol("tanimsiz kimlik yok", not tanimsiz,
            "-> %s" % ["%s:%s %s" % (k.modul, k.ad, i) for k, i in tanimsiz])
    bag = {(k.modul, k.ad): k.gereksinimler for k in kayitlar}
    beklenen = {
        ("test_capa", "test_regresyon_cipasi"): "R-FZ-01",
        ("test_capa", "test_godiva_kriteri"): "R-FZ-02",
        ("test_betik", "test_betik_esdegerligi"): "R-FZ-03",
        ("test_geometri_esdegerlik", "test_iz_kayit_1"): "R-G-01",
        ("test_uygunluk_denetimi", "test_k3_kayip_parcacik"): "R-S-04",
        ("test_rapor", "test_tekrarlanabilirlik"): "R-M10-02",
        ("test_tukenme_temel", "test_bateman_bozunum"): "R-TK-01",
        ("test_guc_kor", "test_kare_kor_2x2_mc"): "R-M1-01",
    }
    for anahtar, kimlik in beklenen.items():
        kontrol("%s:%s -> %s" % (anahtar + (kimlik,)), kimlik in bag.get(anahtar, ()),
                "-> %r" % (bag.get(anahtar),))
    bagli = sum(1 for k in kayitlar if k.gereksinimler)
    kontrol("en az 80 test gereksinime bagli", bagli >= 80, "-> %d" % bagli)


@gereksinim("R-S-15")
def test_matris_sentetik():
    print("\n[IZ4] matris: gecti / KALDI / kismen / calistirilmadi / TESTSIZ / inceleme")
    arac = _arac()
    G, T = arac.Gereksinim, arac.TestKaydi
    gereksinimler = {k: G(k, "m.", "kaynak", y) for k, y in
                     (("R-X-01", "T"), ("R-X-02", "T"), ("R-X-03", "T"), ("R-X-04", "T"),
                      ("R-X-05", "T"), ("R-X-06", "İ"))}
    kayitlar = [T("test_a", "test_1", "hizli", ("R-X-01",)),
                T("test_a", "test_2", "hizli", ("R-X-02", "R-X-03")),
                T("test_a", "test_3", "yavas", ("R-X-03",)),
                T("test_a", "test_4", "yavas", ("R-X-04",)),
                T("test_capa", "test_bagsiz", "yavas", ()),
                T("test_a", "test_5", "hizli", ("R-Y-99",))]
    d = tempfile.mkdtemp()
    try:
        x1, x2, bozuk = (os.path.join(d, a) for a in ("h.xml", "y.xml", "bozuk.xml"))
        _junit(x1, [("test_a", "test_1", ""), ("test_a", "test_2", "<failure message='x'/>")])
        _junit(x2, [("test_a", "test_3", ""), ("test_a", "test_2", "")])
        with open(bozuk, "w", encoding="utf-8") as f:
            f.write("<testsuites><testsuite")
        durumlar, kaynaklar = arac.sonuclari_oku([x1, x2, bozuk])
        kontrol("bozuk dosya atlandi, iki kaynak", len(kaynaklar) == 2, "-> %s" % kaynaklar)
        kontrol("en kotu sonuc kazanir", durumlar[("test_a", "test_2")] == arac.KALDI)
        satirlar = {g.kimlik: durum for g, _b, durum in arac.matris(gereksinimler, kayitlar,
                                                                    durumlar)}
        kontrol("R-X-01 gecti", satirlar["R-X-01"] == arac.GECTI, "-> %s" % satirlar)
        kontrol("R-X-02 KALDI", satirlar["R-X-02"] == arac.KALDI)
        kontrol("R-X-03 KALDI (test_2 kaldi)", satirlar["R-X-03"] == arac.KALDI)
        kontrol("R-X-04 calistirilmadi", satirlar["R-X-04"] == arac.CALISMADI)
        kontrol("R-X-05 TESTSIZ", satirlar["R-X-05"] == arac.TESTSIZ)
        kontrol("R-X-06 inceleme", satirlar["R-X-06"] == arac.INCELEME)
        md = arac.markdown(gereksinimler, kayitlar, durumlar, kaynaklar)
        for parca in ("## Testsiz gereksinimler", "- R-X-05", "`test_a:test_5` → R-Y-99",
                      "`test_capa:test_bagsiz` (yavas)", "| R-X-01 | T | geçti |"):
            kontrol("markdown: %s" % parca, parca in md)
        bos = arac.markdown(gereksinimler, kayitlar, {}, [])
        kontrol("sonuc yoksa calistirilmadi yazilir", "çalıştırılmadı" in bos
                and "sonuç uydurulmaz" in bos)
        # pytest-json-report bicimi + kismen
        import json
        js = os.path.join(d, "r.json")
        with open(js, "w", encoding="utf-8") as f:
            json.dump({"created": 1, "tests": [
                {"nodeid": "testler/test_a.py::test_3", "outcome": "passed"}]}, f)
        durumlar, _k = arac.sonuclari_oku([], [js])
        g3 = arac.gereksinim_durumu(gereksinimler["R-X-03"],
                                    [kayitlar[1], kayitlar[2]], durumlar)
        kontrol("json okunur; kismen", g3.startswith("kısmen"), "-> %s" % g3)
    finally:
        shutil.rmtree(d, True)


@gereksinim("R-S-15")
def test_uretilen_belge_guncel():
    print("\n[IZ5] docs/IZLENEBILIRLIK.md var ve butun kimlikleri listeler")
    arac = _arac()
    yol = os.path.join(KOK, "docs", "IZLENEBILIRLIK.md")
    kontrol("belge var", os.path.isfile(yol))
    if not os.path.isfile(yol):
        return
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    eksik = [k for k in arac.gereksinimleri_oku() if "| %s |" % k not in metin]
    kontrol("her gereksinim matriste", not eksik, "-> %s (araclar/izlenebilirlik.py kosun)"
            % eksik)


@gereksinim("R-S-15")
def test_komut_satiri():
    print("\n[IZ6] main(): gecici ciktiya yazar; --denetle cikis kodu")
    arac = _arac()
    d = tempfile.mkdtemp()
    try:
        cikti = os.path.join(d, "m.md")
        gm = os.path.join(d, "g.md")
        with open(gm, "w", encoding="utf-8") as f:
            f.write("| R-S-15 | Matris üretilir. | Y1 | T |\n| R-ZZ-01 | Testsiz. | k | T |\n")
        kod = arac.main(["--junit", os.path.join(d, "yok.xml"), "-o", cikti,
                         "--gereksinimler", gm, "--denetle"])
        kontrol("testsiz gereksinim -> cikis 1", kod == 1, "-> %r" % kod)
        kontrol("cikti yazildi", os.path.isfile(cikti))
        with open(gm, "w", encoding="utf-8") as f:
            f.write("| R-S-15 | Matris üretilir. | Y1 | T |\n")
        kod = arac.main(["--junit", os.path.join(d, "yok.xml"), "-o", cikti,
                         "--gereksinimler", gm])
        kontrol("--denetle yoksa cikis 0", kod == 0)
    finally:
        shutil.rmtree(d, True)


HIZLI = [test_gereksinim_isareti, test_gereksinim_belgesi, test_testler_tanimli_kimlik_kullanir,
         test_matris_sentetik, test_uretilen_belge_guncel, test_komut_satiri]
YAVAS = []
