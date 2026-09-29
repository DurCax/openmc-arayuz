# -*- coding: utf-8 -*-
"""
test_rapor.py -- cekirdek/rapor.py (HTML + PDF rapor), surum.derleme_bilgisi,
`openmc-arayuz-kosu rapor` alt komutu ve cekirdek/'in Qt'siz kalmasi.

Fixture: testler/veri/kosu_ornek/ (gercek, kucuk bir kosu; uret.py yeniden
uretir). Monte Carlo KOSULMAZ; statepoint okunur. Geometri kesitleri
`openmc -p` (cizim kipi, nukleer veri gerekmez) ile uretilir.
Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import ast
import html
import copy
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time

from testler.ortak_test import kontrol, KOK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

FIXTURE = os.path.join(KOK, "testler", "veri", "kosu_ornek")
FIXTURE_SPEC = os.path.join(FIXTURE, "spec.json")


def _modul_duzeyi_importlar(agac):
    """Modul duzeyinde (islev/sinif govdeleri HARIC; try/if icleri DAHIL)
    ice aktarilan modul adlari."""
    adlar, yigin = [], list(agac.body)
    while yigin:
        dugum = yigin.pop()
        if isinstance(dugum, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(dugum, ast.Import):
            adlar += [a.name for a in dugum.names]
        elif isinstance(dugum, ast.ImportFrom):
            adlar.append(dugum.module or "")
        else:
            yigin.extend(ast.iter_child_nodes(dugum))
    return adlar


def test_cekirdek_qt_siz():
    print("\n[R1] cekirdek/ altinda hicbir modul modul duzeyinde PySide6 ice aktarmaz")
    ihlal = []
    for kok, _dizinler, dosyalar in os.walk(os.path.join(KOK, "cekirdek")):
        for ad in dosyalar:
            if not ad.endswith(".py"):
                continue
            yol = os.path.join(kok, ad)
            with open(yol, encoding="utf-8") as f:
                agac = ast.parse(f.read())
            if any(a.split(".")[0] == "PySide6" for a in _modul_duzeyi_importlar(agac)):
                ihlal.append(os.path.relpath(yol, KOK))
    kontrol("PySide6 modul duzeyinde yok", not ihlal, "-> %s" % ihlal)
    ornek = ast.parse("try:\n    from PySide6 import QtGui\nexcept ImportError:\n    pass\n"
                      "def f():\n    import PySide6\n")
    kontrol("tarayici try icini yakalar, islev icini yakalamaz",
            _modul_duzeyi_importlar(ornek) == ["PySide6"])


def test_derleme_bilgisi():
    print("\n[R2] surum.derleme_bilgisi: uygulama, surum, git, python")
    from cekirdek import surum
    b = surum.derleme_bilgisi()
    kontrol("alanlar", {"uygulama", "surum", "git_commit", "git_degisiklik", "python",
                        "platform"} <= set(b), "-> %s" % sorted(b))
    kontrol("surum tek kaynaktan", b["surum"] == surum.surum()
            and b["uygulama"] == surum.UYGULAMA_ADI)
    git_var = shutil.which("git") and os.path.exists(os.path.join(KOK, ".git"))
    if git_var:
        kontrol("git commit 40 hane", isinstance(b["git_commit"], str)
                and len(b["git_commit"]) == 40, "-> %r" % b["git_commit"])
    eski = surum._GIT
    kayitlar = []
    isleyici = logging.Handler()
    isleyici.emit = kayitlar.append
    kaydedici = logging.getLogger("openmc_arayuz")
    kaydedici.addHandler(isleyici)
    try:
        surum._GIT = "olmayan-git-komutu-xyz"
        b2 = surum.derleme_bilgisi()
    finally:
        surum._GIT = eski
        kaydedici.removeHandler(isleyici)
    kontrol("git yoksa None + log", b2["git_commit"] is None and b2["git_degisiklik"] is None
            and any("git" in r.getMessage() for r in kayitlar), "-> %r" % b2["git_commit"])


def _fixture_spec():
    with open(FIXTURE_SPEC, encoding="utf-8") as f:
        return json.load(f)


def _statepoint_gercegi():
    """k, sigma, F_dH, F_q DOGRUDAN statepoint'ten (rapor kodundan bagimsiz):
    guc_dagilimi tally'si [distribcell x eksenel dilim] olarak yeniden sekillenir."""
    import openmc
    from cekirdek import kosucu
    sp = openmc.StatePoint(kosucu.son_statepoint(FIXTURE))
    tal = sp.get_tally(name="guc_dagilimi")
    n_dilim = _fixture_spec()["guc_dagilimi"]["eksenel_dilim"]
    dizi = tal.mean[:, 0, 0].reshape(-1, n_dilim)
    cubuk = dizi.sum(axis=1)
    return {"k": float(sp.keff.nominal_value), "sigma": float(sp.keff.std_dev),
            "F_dH": float(cubuk.max() / cubuk.mean()), "F_q": float(dizi.max() / dizi.mean()),
            "seed": int(sp.seed), "parcacik": int(sp.n_particles), "cevrim": int(sp.n_batches)}


def _gecici():
    return tempfile.mkdtemp(prefix="rapor_test_")


def test_rapor_html_fixture():
    print("\n[R3] fixture kosu dizininden HTML rapor; spec degismez")
    from cekirdek import rapor
    spec = _fixture_spec()
    kopya = copy.deepcopy(spec)
    dizin = _gecici()
    try:
        sonuc = rapor.olustur(spec, FIXTURE, os.path.join(dizin, "r.html"), "html")
        kontrol("RaporSonucu mutlak yol", isinstance(sonuc, rapor.RaporSonucu)
                and os.path.isabs(sonuc.yol) and os.path.exists(sonuc.yol))
        kontrol("uyarilar tuple", isinstance(sonuc.uyarilar, tuple))
        kontrol("spec degismedi", spec == kopya)
        with open(sonuc.yol, encoding="utf-8") as f:
            metin = f.read()
        for parca in ("<html", "Tekrarlanabilirlik", "Malzemeler", "Geometri", "Hesap ayarları",
                      "k-eff", "Güç dağılımı", "F_ΔH", "F_q", "Tally", "Doğrulama",
                      "Ek: model", "data:image/png;base64,", html.escape(spec["ad"])):
            kontrol("HTML icerir: %s" % parca, parca in metin)
        kontrol("gorsel sayisi >= 4 (xy, xz, yakinsama, guc haritasi)",
                metin.count("data:image/png;base64,") >= 4,
                "-> %d" % metin.count("data:image/png;base64,"))
    finally:
        shutil.rmtree(dizin, True)


def test_rapor_sayilar_birebir():
    print("\n[R4] k, sigma, F_dH, F_q statepoint ile BIREBIR (sayi ve metin)")
    from cekirdek import rapor
    g = _statepoint_gercegi()
    icerik = rapor.icerik_topla(_fixture_spec(), FIXTURE)
    k = icerik["kosu"]
    kontrol("k birebir", k["keff"] == g["k"], "-> %r / %r" % (k["keff"], g["k"]))
    kontrol("sigma birebir", k["sigma"] == g["sigma"])
    f = icerik["guc"]["faktorler"]
    kontrol("F_dH (bagimsiz hesapla 1e-12)", abs(f["F_dH"] - g["F_dH"]) < 1e-12,
            "-> %r / %r" % (f["F_dH"], g["F_dH"]))
    kontrol("F_q (bagimsiz hesapla 1e-12)", abs(f["F_q"] - g["F_q"]) < 1e-12,
            "-> %r / %r" % (f["F_q"], g["F_q"]))
    from cekirdek import rapor_sablon
    metin = rapor_sablon.html(icerik, gomulu=False)
    for m in ("%.5f ± %.5f" % (g["k"], g["sigma"]), "%.4f" % g["F_dH"], "%.4f" % g["F_q"]):
        kontrol("HTML metni: %s" % m, m in metin)


def test_tekrarlanabilirlik():
    print("\n[R5] tekrarlanabilirlik alanlari dolu; bilinmeyen -> 'bilinmiyor' + log + uyari")
    from cekirdek import rapor
    g = _statepoint_gercegi()
    alanlar, uyarilar = rapor.tekrarlanabilirlik(_fixture_spec(), FIXTURE)
    d = dict(alanlar)
    for ad in ("Uygulama sürümü", "OpenMC sürümü", "Tesir kesiti kütüphanesi", "Tohum",
               "Parçacık / çevrim", "Çevrim (pasif)", "İş parçacığı", "Zincir dosyası",
               "Git commit"):
        kontrol("alan: %s" % ad, ad in d and d[ad] and d[ad] != "bilinmiyor", "-> %r" % d.get(ad))
    kontrol("tohum statepoint'ten", d.get("Tohum") == str(g["seed"]))
    kontrol("parcacik statepoint'ten", d.get("Parçacık / çevrim") == str(g["parcacik"]))
    kontrol("is parcacigi logdan (8)", d.get("İş parçacığı") == "8")
    kontrol("zincir sha256", "sha256" in d.get("Zincir dosyası", ""))
    kontrol("fixture'da uyari yok", not uyarilar, "-> %s" % uyarilar)
    # log'suz kopya: is parcacigi bilinmiyor
    dizin = _gecici()
    kayitlar = []
    isleyici = logging.Handler()
    isleyici.emit = kayitlar.append
    logging.getLogger("openmc_arayuz").addHandler(isleyici)
    try:
        for ad in os.listdir(FIXTURE):
            if ad.endswith(".h5"):
                shutil.copy(os.path.join(FIXTURE, ad), dizin)
        alanlar, uyarilar = rapor.tekrarlanabilirlik(_fixture_spec(), dizin)
    finally:
        logging.getLogger("openmc_arayuz").removeHandler(isleyici)
        shutil.rmtree(dizin, True)
    d = dict(alanlar)
    kontrol("log yoksa is parcacigi bilinmiyor", d.get("İş parçacığı") == "bilinmiyor")
    kontrol("uyari listesinde", any("İş parçacığı" in u for u in uyarilar), "-> %s" % uyarilar)
    kontrol("loglandi", any("bilinmiyor" in r.getMessage() for r in kayitlar))


def test_rapor_yalniz_model():
    print("\n[R6] kosu_dizini None -> yalniz model raporu")
    from cekirdek import rapor
    from testler.ortak_test import ORNEK
    from cekirdek import sema
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    dizin = _gecici()
    try:
        sonuc = rapor.olustur(spec, None, os.path.join(dizin, "m.html"), "html")
        with open(sonuc.yol, encoding="utf-8") as f:
            metin = f.read()
        kontrol("model bolumleri var", "Malzemeler" in metin and "Hesap ayarları" in metin)
        kontrol("kosu bolumu yok", "Koşu sonucu" not in metin and "F_ΔH" not in metin)
        kontrol("'koşu yok' notu", "koşu dizini verilmedi" in metin)
    finally:
        shutil.rmtree(dizin, True)


def test_rapor_hatalar():
    print("\n[R7] hatali girdi -> RaporHatasi (kullaniciya gosterilecek metin)")
    from cekirdek import rapor
    spec = _fixture_spec()
    dizin = _gecici()

    def hata_mi(*arg):
        try:
            rapor.olustur(*arg)
        except rapor.RaporHatasi as e:
            return bool(str(e))
        return False
    try:
        kontrol("bilinmeyen bicim", hata_mi(spec, None, os.path.join(dizin, "x.doc"), "doc"))
        kontrol("olmayan kosu dizini", hata_mi(spec, os.path.join(dizin, "yok"),
                                              os.path.join(dizin, "x.html"), "html"))
        kontrol("statepoint'siz dizin", hata_mi(spec, dizin, os.path.join(dizin, "x.html"), "html"))
        kontrol("spec sozluk degil", hata_mi(None, None, os.path.join(dizin, "x.html"), "html"))
        kontrol("yazilamayan yol", hata_mi(spec, None, "/proc/yazilamaz/x.html", "html"))
        alt = os.path.join(dizin, "yeni", "alt", "x.html")
        rapor.olustur(spec, None, alt, "html")
        kontrol("eksik ust dizin olusturulur", os.path.exists(alt))
    finally:
        shutil.rmtree(dizin, True)


def _pdf_sayfa_sayisi(yol):
    with open(yol, "rb") as f:
        veri = f.read()
    import re
    return len(re.findall(rb"/Type\s*/Page(?!s)", veri))


def _pdf_metni(yol):
    """pdftotext varsa PDF'in metni; yoksa None (metin denetimi atlanir)."""
    if not shutil.which("pdftotext"):
        return None
    return subprocess.run(["pdftotext", "-layout", yol, "-"], capture_output=True,
                          text=True, check=True).stdout


def test_rapor_pdf_ve_sure():
    print("\n[R8] fixture'dan PDF (sayfa > 0, metin icerir); HTML + PDF < 5 s (offscreen)")
    from cekirdek import rapor
    g = _statepoint_gercegi()
    spec = _fixture_spec()
    dizin = _gecici()
    try:
        t0 = time.perf_counter()
        rapor.olustur(spec, FIXTURE, os.path.join(dizin, "r.html"), "html")
        sonuc = rapor.olustur(spec, FIXTURE, os.path.join(dizin, "r.pdf"), "pdf")
        sure = time.perf_counter() - t0
        kontrol("HTML + PDF < 5 s", sure < 5.0, "-> %.2f s" % sure)
        with open(sonuc.yol, "rb") as f:
            kontrol("PDF imzasi", f.read(5) == b"%PDF-")
        n = _pdf_sayfa_sayisi(sonuc.yol)
        kontrol("PDF sayfa > 0", n > 0, "-> %d sayfa" % n)
        metin = _pdf_metni(sonuc.yol)
        if metin is None:
            print("  (pdftotext yok: PDF metin denetimi atlandi)")
        else:
            for parca in ("Tekrarlanabilirlik", "%.5f" % g["k"], "%.4f" % g["F_dH"],
                          "%.4f" % g["F_q"]):
                kontrol("PDF metni: %s" % parca, parca in metin)
    finally:
        shutil.rmtree(dizin, True)


def test_cli_rapor():
    print("\n[R9] openmc-arayuz-kosu rapor <dizin> -o x.pdf (giris.kosu)")
    from cekirdek import giris, kosucu
    dizin = _gecici()
    try:
        pdf = os.path.join(dizin, "x.pdf")
        kontrol("rapor alt komutu 0", giris.kosu(["rapor", FIXTURE, "-o", pdf]) == 0)
        kontrol("PDF yazildi", os.path.exists(pdf) and _pdf_sayfa_sayisi(pdf) > 0)
        html_yol = os.path.join(dizin, "x.html")
        kontrol("--spec ile HTML", giris.kosu(["rapor", FIXTURE, "--spec", FIXTURE_SPEC,
                                               "-o", html_yol]) == 0
                and os.path.exists(html_yol))
        kontrol("yardim 0", giris.kosu(["rapor", "-h"]) == 0)
        kontrol("dizin yok -> 2", giris.kosu(["rapor"]) == 2)
        kontrol("-o degersiz -> 2", giris.kosu(["rapor", FIXTURE, "-o"]) == 2)
        kontrol("bilinmeyen secenek -> 2", giris.kosu(["rapor", FIXTURE, "--xyz"]) == 2)
        kontrol("gecersiz uzanti -> 2", giris.kosu(["rapor", FIXTURE, "-o",
                                                    os.path.join(dizin, "x.doc")]) == 2)
        kontrol("spec'siz dizin -> 2", giris.kosu(["rapor", dizin, "-o", pdf]) == 2)
        with open(os.path.join(dizin, "spec.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(_fixture_spec()))
        kontrol("statepoint'siz dizin -> 1", giris.kosu(["rapor", dizin, "-o", pdf]) == 1)
        cagri = []
        eski = kosucu._terminal
        kosucu._terminal = lambda argv: cagri.append(argv) or 0
        try:
            giris.kosu(["model.json", "--sadece-dogrula"])
        finally:
            kosucu._terminal = eski
        kontrol("diger argumanlar kosucu._terminal'e", cagri == [["model.json",
                                                                  "--sadece-dogrula"]])
    finally:
        shutil.rmtree(dizin, True)


def test_rapor_tukenme_bolumu():
    print("\n[R10] kosu dizininde depletion_results.h5 -> tukenme tablosu ve grafigi")
    from cekirdek import rapor, tukenme
    spec = _fixture_spec()
    dizin = _gecici()
    sahte = {"zaman_d": [0.0, 10.0, 20.0], "yanma": [0.0, 0.4, 0.8],
             "k": [1.30, 1.28, 1.27], "k_sapma": [0.002, 0.002, 0.002],
             "atomlar": {"uo2": {"U235": [1e22, 9e21, 8e21], "Xe135": [0.0, 1e17, 1e17]}},
             "yogunluk": {}, "adim_sayisi": 2, "bulunamayan": ["Xx999"]}
    eski = tukenme.onceki_sonuc
    tukenme.onceki_sonuc = lambda s, d: {"h5": d, "tarih": 0, "durum": "eski",
                                         "farklar": ["kor"], "sonuc": sahte}
    try:
        for ad in os.listdir(FIXTURE):
            shutil.copy(os.path.join(FIXTURE, ad), dizin)
        open(os.path.join(dizin, rapor.TUKENME_H5), "wb").close()
        icerik = rapor.icerik_topla(spec, dizin)
        t = icerik["tukenme"]
        kontrol("tablo 3 adim", t is not None and len(t["satirlar"]) == 3)
        kontrol("grafik", "tukenme" in icerik["gorseller"])
        kontrol("eski sonuc uyarisi", any("tükenme" in u for u in icerik["uyarilar"]))
        from cekirdek import rapor_sablon
        metin = rapor_sablon.html(icerik, gomulu=False)
        kontrol("HTML: Tükenme + bulunamayan", "Tükenme" in metin and "Xx999" in metin)
    finally:
        tukenme.onceki_sonuc = eski
        shutil.rmtree(dizin, True)


def test_rapor_dayaniklilik():
    print("\n[R11] openmc yok / grafik hatasi -> rapor yine yazilir, uyari listelenir")
    from cekirdek import rapor
    from cekirdek.rapor_sablon import grafik
    spec = _fixture_spec()
    dizin = _gecici()
    eski_which, eski_harita = grafik.shutil.which, grafik.guc_haritasi
    grafik.shutil.which = lambda ad: None

    def bozuk(_g):
        raise RuntimeError("deneme hatasi")
    grafik.guc_haritasi = bozuk
    try:
        sonuc = rapor.olustur(spec, FIXTURE, os.path.join(dizin, "r.html"), "html")
    finally:
        grafik.shutil.which, grafik.guc_haritasi = eski_which, eski_harita
    try:
        kontrol("geometri uyarisi", any("geometri" in u for u in sonuc.uyarilar),
                "-> %s" % (sonuc.uyarilar,))
        kontrol("grafik uyarisi", any("deneme hatasi" in u for u in sonuc.uyarilar))
        with open(sonuc.yol, encoding="utf-8") as f:
            kontrol("uyarilar raporda", "deneme hatasi" in f.read())
    finally:
        shutil.rmtree(dizin, True)


def test_ornek_cikti(hedef=None):
    """Ornek HTML ve PDF'i OPENMC_V2_CIKTI/d2_10/ altina yazar (ortam yoksa atlanir)."""
    from cekirdek import rapor
    kok = hedef or os.environ.get("OPENMC_V2_CIKTI")
    if not kok:
        print("  (OPENMC_V2_CIKTI yok: ornek cikti atlandi)")
        return
    for bicim in ("html", "pdf"):
        s = rapor.olustur(_fixture_spec(), FIXTURE,
                          os.path.join(kok, "d2_10", "rapor_ornek." + bicim), bicim)
        kontrol("ornek %s" % bicim, os.path.exists(s.yol), "-> %s" % s.yol)


HIZLI = [test_cekirdek_qt_siz, test_derleme_bilgisi, test_rapor_html_fixture,
         test_rapor_sayilar_birebir, test_tekrarlanabilirlik, test_rapor_yalniz_model,
         test_rapor_hatalar, test_rapor_pdf_ve_sure, test_cli_rapor,
         test_rapor_tukenme_bolumu, test_rapor_dayaniklilik]
YAVAS = []
