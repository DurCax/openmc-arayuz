# -*- coding: utf-8 -*-
"""
 test_t2_yollar.py  --  v3 T2: tek yol kaynagi (cekirdek/yollar.py), alt surec
                        dagiticisi (openmc-arayuz-kosu --alt tukenme), openmc
                        ikilisi cozumu, paket verisi ve dosya boyu siniri

 HIZLI testler kaynak agacinda calisir. YAVAS test (test_kurulu_paket) kabul
 olcutunu tekrarlar: gecici bir venv'e `pip install --no-deps .` kurar ve
 TEMIZ bir dizinden (kaynak agaci sys.path'te degil) yollari, veri dosyalarini,
 basssiz pencerenin acilip kapanmasini ve tukenme dagiticisini dener.
"""

import ast
import glob
import os
import shutil
import stat
import subprocess
import sys

from testler.ortak_test import kontrol, KOK

_KAYNAK_PAKETLER = ("cekirdek", "arayuz")
_AZAMI_SATIR = 800          # ORTAK_KURALLAR.md madde 9: dosya < 800 satir
_ALT_SUREC_SURESI = 120     # s; alt surec (import openmc dahil) en kotu durumda
_KOPYALANMAYAN = (".git", ".claude", ".env*", "__pycache__", "build", "dist", "*.egg-info",
                  "graphify-out", "htmlcov", ".ruff_cache")
# Kopyada OLMAMASI gereken (gizli bilgi / depo gecmisi tasiyabilen) adlar
_GIZLI_ADLAR = (".git", ".claude", ".env")


def _kaynak_dosyalari():
    for paket in _KAYNAK_PAKETLER:
        for yol in glob.glob(os.path.join(KOK, paket, "**", "*.py"), recursive=True):
            yield yol


def _sahte_calistirilabilir(dizin, ad="openmc"):
    yol = os.path.join(dizin, ad)
    with open(yol, "w") as f:
        f.write("#!/bin/sh\nexit 0\n")
    os.chmod(yol, os.stat(yol).st_mode | stat.S_IEXEC)
    return yol


# ---------------------------------------------------------------------------
# yollar: paket ve veri dizinleri
# ---------------------------------------------------------------------------

def _veri_dizini(kok):
    """Gecerli bir veri koku taklidi: yollar.VERI_ISARETI dosyasi var."""
    from cekirdek import yollar
    isaret = os.path.join(str(kok), yollar.VERI_ISARETI)
    os.makedirs(os.path.dirname(isaret), exist_ok=True)
    open(isaret, "w").close()
    return str(kok)


def test_paket_ve_veri_dizinleri():
    print("\n[T2-1] yollar: paket koku, ornekler, locale, kilavuz, ikon, font, sablon")
    from cekirdek import yollar
    kok = yollar.paket_koku()
    kontrol("paket koku cekirdek/ ve arayuz/ icerir",
            os.path.isdir(os.path.join(kok, "cekirdek")) and os.path.isdir(os.path.join(kok, "arayuz")),
            kok)
    kontrol("kaynak agacinda veri koku = paket koku",
            os.path.realpath(yollar.veri_koku(ortam={})) == os.path.realpath(KOK))
    kontrol("veri isareti dosyasi kaynak agacinda var",
            os.path.isfile(os.path.join(KOK, yollar.VERI_ISARETI)), yollar.VERI_ISARETI)
    kontrol("kaynak_agaci_mi", yollar.kaynak_agaci_mi())
    kontrol("ornekler *.json", bool(glob.glob(os.path.join(yollar.ornekler_dizini(), "*.json"))))
    kontrol("locale en katalog dizini",
            os.path.isdir(os.path.join(yollar.locale_dizini(ortam={}), "en", "LC_MESSAGES")))
    kontrol("kilavuz tr/00-giris.md",
            os.path.isfile(os.path.join(yollar.kilavuz_dizini(ortam={}), "tr", "00-giris.md")))
    kontrol("ikonlar *.svg", bool(glob.glob(os.path.join(yollar.ikon_dizini(), "*.svg"))))
    kontrol("font Inter-Regular.ttf",
            os.path.isfile(os.path.join(yollar.font_dizini(), "Inter-Regular.ttf")))
    kontrol("rapor sablonu rapor.html",
            os.path.isfile(os.path.join(yollar.rapor_sablon_dizini(), "rapor.html")))
    kontrol("pyproject yolu kaynak agacinda var", os.path.isfile(yollar.pyproject_yolu()))


def test_veri_koku_ortam_degiskeni(tmp_path, caplog):
    print("\n[T2-2] OPENMC_ARAYUZ_VERI: gecerli dizin kullanilir, gecersizi uyarip yok sayilir")
    from cekirdek import yollar
    d = _veri_dizini(tmp_path / "veri")
    ad = yollar.VERI_ORTAM_DEGISKENI
    kontrol("gecerli ortam dizini oncelikli", yollar.veri_koku(ortam={ad: d}) == d)
    kontrol("ornekler veri kokunun altinda",
            yollar.ornekler_dizini(ortam={ad: d}) == os.path.join(d, "ornekler"))
    yabanci = tmp_path / "yabanci"
    os.makedirs(yabanci / "ornekler")                 # isaretsiz yabanci ornekler/
    for deger, neden in ((str(tmp_path / "olmayan"), "olmayan"), (str(yabanci), "isaretsiz"),
                         ("goreli/dizin", "goreli")):
        caplog.clear()
        with caplog.at_level("WARNING", logger="openmc_arayuz.yollar"):
            sonuc = yollar.veri_koku(ortam={ad: deger})
        kontrol("%s dizin yok sayilir" % neden, sonuc != deger, sonuc)
        kontrol("%s dizin uyarisi" % neden, ad in caplog.text, caplog.text)


def test_veri_koku_aday_sirasi(tmp_path, monkeypatch):
    print("\n[T2-2a] veri koku: --target (paket koku/share) ve sys.prefix/share adaylari")
    from cekirdek import yollar
    sahte_kok = tmp_path / "site"                     # ornekler/ YOK (kurulu paket)
    os.makedirs(sahte_kok)
    monkeypatch.setattr(yollar, "_PAKET_KOKU", str(sahte_kok))
    monkeypatch.setattr(yollar, "_dagitim_paylasim_dizini", lambda: None)
    onek = tmp_path / "onek"
    monkeypatch.setattr(sys, "prefix", str(onek))
    kontrol("hicbiri yoksa paket koku", yollar.veri_koku(ortam={}) == str(sahte_kok))
    prefix_veri = _veri_dizini(onek / "share" / yollar.PAYLASIM_ADI)
    kontrol("sys.prefix/share/openmc-arayuz", yollar.veri_koku(ortam={}) == prefix_veri)
    hedef_veri = _veri_dizini(sahte_kok / "share" / yollar.PAYLASIM_ADI)
    kontrol("--target duzeni sys.prefix'ten once", yollar.veri_koku(ortam={}) == hedef_veri)
    kayit = _veri_dizini(tmp_path / "kayit")
    monkeypatch.setattr(yollar, "_dagitim_paylasim_dizini", lambda: kayit)
    kontrol("dagitim kaydi --target'tan once", yollar.veri_koku(ortam={}) == kayit)


class _SahteDagitim:
    """importlib.metadata.Distribution taklidi: files + locate_file."""

    def __init__(self, kok, dosyalar=None, hata=None):
        import pathlib
        self._kok = kok
        self._hata = hata
        self._dosyalar = [pathlib.PurePosixPath(d) for d in dosyalar or ()]

    @property
    def files(self):
        if self._hata:
            raise self._hata
        return self._dosyalar

    def locate_file(self, yol):
        return os.path.join(self._kok, str(yol))


def test_dagitim_kaydindan_paylasim_dizini(monkeypatch, caplog):
    print("\n[T2-2b] kurulu dagitimin RECORD'undan share/openmc-arayuz; bozuk kayit")
    from importlib import metadata
    from cekirdek import yollar
    bul = yollar._dagitim_paylasim_dizini.__wrapped__      # lru_cache'siz govde
    sp = "/onek/lib/python3.13/site-packages"
    monkeypatch.setattr(metadata, "distribution", lambda ad: _SahteDagitim(
        sp, ["cekirdek/yollar.py", "../../../share/openmc-arayuz/ornekler/a.json"]))
    kontrol("kayittaki onek", bul() == "/onek/share/openmc-arayuz", bul())
    monkeypatch.setattr(metadata, "distribution", lambda ad: _SahteDagitim(sp, ["cekirdek/a.py"]))
    kontrol("veri kaydi yoksa None", bul() is None)
    for hata in (OSError("RECORD okunamadi"), ValueError("bozuk satir")):
        monkeypatch.setattr(metadata, "distribution",
                            lambda ad, h=hata: _SahteDagitim(sp, hata=h))
        caplog.clear()
        with caplog.at_level("WARNING", logger="openmc_arayuz.yollar"):
            sonuc = bul()
        kontrol("bozuk RECORD (%s) -> None + uyari" % type(hata).__name__,
                sonuc is None and "RECORD" in caplog.text, caplog.text)

    def _yok(ad):
        raise metadata.PackageNotFoundError(ad)
    monkeypatch.setattr(metadata, "distribution", _yok)
    kontrol("dagitim kurulu degilse None", bul() is None)


def test_ozel_dizin_ortam_degiskenleri(tmp_path, monkeypatch, caplog):
    print("\n[T2-3] OPENMC_ARAYUZ_LOCALE / _KILAVUZ: ~ ve goreli yol, gecersiz uyarip atlanir")
    from cekirdek import yollar
    monkeypatch.setenv("HOME", str(tmp_path))
    os.makedirs(tmp_path / "loc")
    os.makedirs(tmp_path / "k")
    kontrol("locale ortam degiskeni (~ acilir)",
            yollar.locale_dizini(ortam={"OPENMC_ARAYUZ_LOCALE": "~/loc"}) == str(tmp_path / "loc"))
    kontrol("kilavuz ortam degiskeni",
            yollar.kilavuz_dizini(ortam={"OPENMC_ARAYUZ_KILAVUZ": str(tmp_path / "k")})
            == str(tmp_path / "k"))
    monkeypatch.chdir(tmp_path)
    kontrol("goreli yol mutlaga cevrilir",
            yollar.kilavuz_dizini(ortam={"OPENMC_ARAYUZ_KILAVUZ": "k"}) == str(tmp_path / "k"))
    varsayilan = os.path.join(yollar.veri_koku(ortam={}), "docs", "kilavuz")
    kontrol("bos degisken varsayilana duser",
            yollar.kilavuz_dizini(ortam={"OPENMC_ARAYUZ_KILAVUZ": ""}) == varsayilan)
    caplog.clear()
    with caplog.at_level("WARNING", logger="openmc_arayuz.yollar"):
        sonuc = yollar.kilavuz_dizini(ortam={"OPENMC_ARAYUZ_KILAVUZ": str(tmp_path / "yok")})
    kontrol("olmayan dizin uyarilip varsayilana duser",
            sonuc == varsayilan and "OPENMC_ARAYUZ_KILAVUZ" in caplog.text, caplog.text)


def test_xdg_dizinleri(tmp_path, monkeypatch):
    print("\n[T2-4] XDG kullanici dizinleri (config/data/cache/state)")
    from cekirdek import yollar
    monkeypatch.setenv("HOME", str(tmp_path))
    ev = str(tmp_path)
    beklenen = {"XDG_CONFIG_HOME": (yollar.ayar_dizini, ".config"),
                "XDG_DATA_HOME": (yollar.kullanici_veri_dizini, os.path.join(".local", "share")),
                "XDG_CACHE_HOME": (yollar.onbellek_dizini, ".cache"),
                "XDG_STATE_HOME": (yollar.durum_dizini, os.path.join(".local", "state"))}
    for degisken, (islev, varsayilan) in beklenen.items():
        kontrol("%s verilince" % degisken,
                islev(ortam={degisken: "/mutlak/yol"}) == "/mutlak/yol/openmc_arayuz")
        kontrol("%s yoksa ~/%s" % (degisken, varsayilan),
                islev(ortam={}) == os.path.join(ev, varsayilan, "openmc_arayuz"))
        kontrol("%s goreli ise yok sayilir (XDG kurali)" % degisken,
                islev(ortam={degisken: "goreli/yol"}) == os.path.join(ev, varsayilan, "openmc_arayuz"))


def test_gunluk_xdg_tek_kaynak():
    print("\n[T2-5] gunluk.durum_dizini = yollar.durum_dizini")
    from cekirdek import gunluk, yollar
    ortam = {"XDG_STATE_HOME": "/s"}
    kontrol("ayni yol", gunluk.durum_dizini(ortam) == yollar.durum_dizini(ortam))


def _file_kullanan_dosyalar():
    """cekirdek/ ve arayuz/ altinda `__file__` ADINI (AST) kullanan dosyalar."""
    kalan = []
    for yol in _kaynak_dosyalari():
        with open(yol, encoding="utf-8") as f:
            agac = ast.parse(f.read())
        if any(isinstance(d, ast.Name) and d.id == "__file__" for d in ast.walk(agac)):
            kalan.append(os.path.relpath(yol, KOK))
    return kalan


def test_moduller_yollari_kullanir():
    print("\n[T2-6] modul sabitleri yollar'dan; cekirdek/arayuz'da baska __file__ yok (AST)")
    from cekirdek import ceviri, ornek_bilgi, surum, yollar
    from cekirdek import rapor_sablon
    from cekirdek.vv import kume
    from arayuz import baslangic
    from arayuz.pencere import model_islemleri
    from arayuz.tasarim import ikon, yazi
    from arayuz.yardim import kaynak
    if not os.environ.get("OPENMC_ARAYUZ_LOCALE"):
        kontrol("ceviri.LOCALE_DIZINI", ceviri.LOCALE_DIZINI == yollar.locale_dizini())
    if not os.environ.get("OPENMC_ARAYUZ_KILAVUZ"):
        kontrol("kaynak.KILAVUZ_DIZINI", kaynak.KILAVUZ_DIZINI == yollar.kilavuz_dizini())
    esitler = (("ornek_bilgi.ORNEK_DIZINI", ornek_bilgi.ORNEK_DIZINI, yollar.ornekler_dizini()),
               ("kume.ORNEK", kume.ORNEK, yollar.ornekler_dizini()),
               ("baslangic.ORNEKLER", baslangic.ORNEKLER, yollar.ornekler_dizini()),
               ("model_islemleri.ORNEKLER", model_islemleri.ORNEKLER, yollar.ornekler_dizini()),
               ("ikon.IKON_DIZINI", ikon.IKON_DIZINI, yollar.ikon_dizini()),
               ("yazi.FONT_DIZINI", yazi.FONT_DIZINI, yollar.font_dizini()),
               ("rapor_sablon.SABLON_DIZINI", rapor_sablon.SABLON_DIZINI,
                yollar.rapor_sablon_dizini()),
               ("surum._PYPROJECT", surum._PYPROJECT, yollar.pyproject_yolu()))
    for ad, deger, beklenen in esitler:
        kontrol(ad, deger == beklenen, "%s != %s" % (deger, beklenen))
    kalan = [y for y in _file_kullanan_dosyalar() if y != os.path.join("cekirdek", "yollar.py")]
    kontrol("__file__ yalniz yollar.py'de", not kalan, "-> %s" % kalan)


# ---------------------------------------------------------------------------
# openmc ikilisi
# ---------------------------------------------------------------------------

def test_openmc_ikilisi_sirasi(tmp_path):
    print("\n[T2-7] openmc ikilisi: ortam > python'un yani > PATH > CONDA_PREFIX")
    from cekirdek import yollar
    d = str(tmp_path)
    ortam_exe = _sahte_calistirilabilir(d, "openmc_ortam")
    yol_dizini = os.path.join(d, "path")
    os.makedirs(yol_dizini)
    path_exe = _sahte_calistirilabilir(yol_dizini)
    py_dizini = os.path.join(d, "env", "bin")
    os.makedirs(py_dizini)
    py_exe = _sahte_calistirilabilir(py_dizini)
    conda_bin = os.path.join(d, "conda", "bin")
    os.makedirs(conda_bin)
    conda_exe = _sahte_calistirilabilir(conda_bin)
    tam = {yollar.OPENMC_ORTAM_DEGISKENI: ortam_exe, "PATH": yol_dizini,
           "CONDA_PREFIX": os.path.join(d, "conda")}
    python = os.path.join(py_dizini, "python")
    yok_python = os.path.join(d, "py")
    kontrol("ortam degiskeni en once", yollar.openmc_ikilisi(ortam=tam, python=python) == ortam_exe)
    tam.pop(yollar.OPENMC_ORTAM_DEGISKENI)
    kontrol("python'un yanindaki PATH'ten once (ayni ortam)",
            yollar.openmc_ikilisi(ortam=tam, python=python) == py_exe)
    kontrol("PATH", yollar.openmc_ikilisi(ortam=tam, python=yok_python) == path_exe)
    tam["PATH"] = os.path.join(d, "bos")
    kontrol("CONDA_PREFIX/bin", yollar.openmc_ikilisi(ortam=tam, python=yok_python) == conda_exe)
    kontrol("hicbiri yoksa None",
            yollar.openmc_ikilisi(ortam={"PATH": ""}, python=yok_python) is None)


def test_openmc_ikilisi_guvenlik(tmp_path, monkeypatch, caplog):
    print("\n[T2-7b] openmc: PATH'in bos/goreli ogeleri, goreli/~ ortam yolu, bos degisken")
    from cekirdek import yollar
    d = str(tmp_path)
    yok_python = os.path.join(d, "py")
    _sahte_calistirilabilir(d)                         # CWD'de kotu niyetli 'openmc'
    monkeypatch.chdir(d)
    for path in ("", ".", "goreli", os.pathsep.join(["", ".", "goreli"])):
        kontrol("PATH=%r CWD'yi aramaz" % path,
                yollar.openmc_ikilisi(ortam={"PATH": path}, python=yok_python) is None)
    ad = yollar.OPENMC_ORTAM_DEGISKENI
    caplog.clear()
    with caplog.at_level("WARNING", logger="openmc_arayuz.yollar"):
        sonuc = yollar.openmc_ikilisi(ortam={ad: "openmc", "PATH": ""}, python=yok_python)
    kontrol("goreli ortam yolu reddedilir + uyari", sonuc is None and ad in caplog.text,
            caplog.text)
    monkeypatch.setenv("HOME", d)
    os.makedirs(os.path.join(d, "bin"))
    ev_exe = _sahte_calistirilabilir(os.path.join(d, "bin"))
    kontrol("~ acilir (HOME sabit)",
            yollar.openmc_ikilisi(ortam={ad: "~/bin/openmc", "PATH": ""}, python=yok_python)
            == ev_exe)
    kontrol("bos degisken atlanir (PATH'e duser)",
            yollar.openmc_ikilisi(ortam={ad: "", "PATH": os.path.join(d, "bin")},
                                  python=yok_python) == ev_exe)
    duz = os.path.join(d, "calistirilamaz")
    open(duz, "w").close()
    kontrol("calistirilamayan ortam yolu atlanir",
            yollar.openmc_ikilisi(ortam={ad: duz, "PATH": ""}, python=yok_python) is None)
    sonuc = yollar.openmc_ikilisi(ortam={"PATH": os.path.join(d, "bin")}, python=yok_python)
    kontrol("sonuc mutlak yol", sonuc is not None and os.path.isabs(sonuc), sonuc)


def test_kosucu_openmc_yolu_yollara_baglanir(tmp_path, monkeypatch):
    print("\n[T2-8] kosucu.openmc_yolu yollar.openmc_ikilisi'ni kullanir")
    from cekirdek import kosucu, yollar
    exe = _sahte_calistirilabilir(str(tmp_path), "openmc_ozel")
    monkeypatch.setenv(yollar.OPENMC_ORTAM_DEGISKENI, exe)
    kontrol("ortam degiskenindeki openmc", kosucu.openmc_yolu() == exe)


# ---------------------------------------------------------------------------
# alt surec dagiticisi
# ---------------------------------------------------------------------------

def test_alt_surec_komutu():
    print("\n[T2-9] giris.alt_surec_komutu: sys.executable -m cekirdek.giris --alt tukenme")
    from cekirdek import giris
    program, arg = giris.alt_surec_komutu("tukenme", ["a.json", "-s", "4"])
    kontrol("program sys.executable", program == sys.executable)
    kontrol("argumanlar", arg == ["-m", "cekirdek.giris", "--alt", "tukenme", "a.json", "-s", "4"],
            "-> %r" % arg)
    kontrol("python verilirse o yorumlayici",
            giris.alt_surec_komutu("tukenme", [], python="/x/py")[0] == "/x/py")
    try:
        giris.alt_surec_komutu("yok", [])
        kontrol("bilinmeyen alt surec ValueError", False)
    except ValueError:
        kontrol("bilinmeyen alt surec ValueError", True)


def test_kosu_alt_dagiticisi():
    print("\n[T2-10] openmc-arayuz-kosu --alt tukenme -> tukenme._terminal")
    from cekirdek import giris, tukenme
    cagri = []
    eski = tukenme._terminal
    tukenme._terminal = lambda argv: cagri.append(argv) or 0
    try:
        kod = giris.kosu(["--alt", "tukenme", "m.json", "-s", "2"])
        kod_eksik = giris.kosu(["--alt"])
        kod_bilinmeyen = giris.kosu(["--alt", "yok"])
    finally:
        tukenme._terminal = eski
    kontrol("tukenme argumanlari iletildi", kod == 0 and cagri == [["m.json", "-s", "2"]],
            "-> %r %r" % (kod, cagri))
    kontrol("--alt degersiz -> 2", kod_eksik == 2)
    kontrol("bilinmeyen alt -> 2", kod_bilinmeyen == 2)


def test_alt_surec_gercek_komut_satiri(tmp_path):
    print("\n[T2-11] alt surec komutu kaynak agacindan, baska bir dizinden calisir")
    from cekirdek import giris
    program, arg = giris.alt_surec_komutu("tukenme", ["--help"])
    ortam = dict(os.environ)
    yol = giris.alt_surec_pythonpath(ortam.get("PYTHONPATH", ""))
    if yol:
        ortam["PYTHONPATH"] = yol
    r = subprocess.run([program] + arg, cwd=str(tmp_path), env=ortam, capture_output=True,
                       text=True, timeout=_ALT_SUREC_SURESI)
    kontrol("cikis 0", r.returncode == 0, r.stderr[-500:])
    kontrol("tukenme yardimi (--hazirla)", "--hazirla" in r.stdout, r.stdout[-300:])


def test_runpy_ve_modul_adi_yok():
    print("\n[T2-12] runpy ve string modul adiyla alt surec kalmadi")
    giris_kaynak = open(os.path.join(KOK, "cekirdek", "giris.py"), encoding="utf-8").read()
    agac = ast.parse(giris_kaynak)
    importlar = {a.name for d in ast.walk(agac) if isinstance(d, ast.Import) for a in d.names}
    kontrol("giris runpy kullanmaz", "runpy" not in importlar)
    sekme = open(os.path.join(KOK, "arayuz", "sekme_tukenme.py"), encoding="utf-8").read()
    kontrol("sekme_tukenme '-m cekirdek.tukenme' yazmaz", '"cekirdek.tukenme"' not in sekme)
    kontrol("sekme_tukenme alt_surec_komutu kullanir", "alt_surec_komutu" in sekme)


# ---------------------------------------------------------------------------
# paketleme
# ---------------------------------------------------------------------------

def _pyproject():
    import tomllib
    with open(os.path.join(KOK, "pyproject.toml"), "rb") as f:
        return tomllib.load(f)


def _kapsananlar(desenler):
    kume = set()
    for desen in desenler:
        kume.update(os.path.normpath(y) for y in glob.glob(os.path.join(KOK, desen)))
    return kume


def test_paket_verisi_tam():
    print("\n[T2-13] pyproject: data-files ornek/kilavuz/.mo'yu, package-data ikon/font/sablonu kapsar")
    st = _pyproject()["tool"]["setuptools"]
    veri = st.get("data-files", {})
    desenler = [d for liste in veri.values() for d in liste]
    kapsanan = _kapsananlar(desenler)
    gerekli = [y for kalip in ("ornekler/**/*", "docs/kilavuz/**/*", "locale/**/*.mo")
               for y in glob.glob(os.path.join(KOK, kalip), recursive=True) if os.path.isfile(y)]
    eksik = sorted(os.path.relpath(y, KOK) for y in gerekli if os.path.normpath(y) not in kapsanan)
    kontrol("tum veri dosyalari data-files'ta", gerekli and not eksik, "-> eksik %s" % eksik[:5])
    for hedef, liste in veri.items():
        kaynak_dizinleri = {os.path.dirname(d) for d in liste}
        kontrol("hedef share/openmc-arayuz/<kaynak>: %s" % hedef,
                all(hedef == "share/openmc-arayuz/" + k for k in kaynak_dizinleri), hedef)
    paket = st.get("package-data", {})
    paket_dosyalari = []
    for ad, liste in paket.items():
        dizin = ad.replace(".", os.sep)
        paket_dosyalari += [os.path.join(dizin, d) for d in liste]
    kapsanan = _kapsananlar(paket_dosyalari)
    gerekli = [y for kalip in ("arayuz/kaynaklar/**/*", "cekirdek/rapor_sablon/*.html",
                               "cekirdek/rapor_sablon/*.css")
               for y in glob.glob(os.path.join(KOK, kalip), recursive=True) if os.path.isfile(y)]
    eksik = sorted(os.path.relpath(y, KOK) for y in gerekli if os.path.normpath(y) not in kapsanan)
    kontrol("ikon/font/sablon package-data'da", gerekli and not eksik, "-> eksik %s" % eksik[:5])


def test_kaynak_dosyalari_800_satir_alti():
    print("\n[T2-14] cekirdek/ ve arayuz/ altinda her .py < 800 satir")
    uzun = []
    for yol in _kaynak_dosyalari():
        with open(yol, encoding="utf-8") as f:
            n = sum(1 for _ in f)
        if n >= _AZAMI_SATIR:
            uzun.append("%s (%d)" % (os.path.relpath(yol, KOK), n))
    kontrol("800 satiri asan yok", not uzun, "-> %s" % uzun)


# ---------------------------------------------------------------------------
# YAVAS: kurulu paket (kabul olcutu)
# ---------------------------------------------------------------------------

_KURULU_DENETIM = r"""
import os, sys, glob, subprocess
from cekirdek import yollar, giris
kok = os.environ["KAYNAK_KOK"]
paket = os.path.realpath(yollar.paket_koku())
assert not paket.startswith(os.path.realpath(kok)), "kaynak agaci kullanildi: " + paket
assert glob.glob(os.path.join(yollar.ornekler_dizini(), "*.json")), "ornek yok"
assert glob.glob(os.path.join(yollar.ornekler_dizini(), "vv", "*.json")), "vv ornegi yok"
assert os.path.isfile(os.path.join(yollar.locale_dizini(), "en", "LC_MESSAGES",
                                   "openmc_arayuz.mo")), "ceviri yok"
assert os.path.isfile(os.path.join(yollar.kilavuz_dizini(), "en", "00-giris.md")), "kilavuz yok"
assert glob.glob(os.path.join(yollar.kilavuz_dizini(), "resimler", "tr", "*.png")), "resim yok"
assert os.path.isfile(os.path.join(yollar.ikon_dizini(), "play.svg")), "ikon yok"
assert os.path.isfile(os.path.join(yollar.font_dizini(), "Inter-Regular.ttf")), "font yok"
assert os.path.isfile(os.path.join(yollar.rapor_sablon_dizini(), "rapor.html")), "sablon yok"
from cekirdek import ceviri
ceviri.dil_ayarla("en")
assert ceviri._("Malzemeler") != "Malzemeler", "ingilizce katalog yuklenmedi"
from cekirdek import ornek_bilgi
assert ornek_bilgi.ornek_listesi(), "ornek listesi bos"
program, arg = giris.alt_surec_komutu("tukenme", ["--help"])
r = subprocess.run([program] + arg, capture_output=True, text=True)
assert r.returncode == 0 and "--hazirla" in r.stdout, r.stderr
from PySide6 import QtCore, QtWidgets
_exec = QtWidgets.QApplication.exec
def _kisa_exec(app):
    pencere = [w for w in app.topLevelWidgets() if w.isVisible()]
    assert pencere, "gorunur pencere yok"
    QtCore.QTimer.singleShot(1500, app.quit)
    return _exec()
QtWidgets.QApplication.exec = _kisa_exec
sys.exit(giris.gui([]))
"""


def test_kurulu_paket(gecici):
    print("\n[T2-Y1] pip install (venv) + temiz dizinden yollar, veri, pencere, tukenme dagiticisi")
    venv = os.path.join(gecici, "venv")
    r = subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", venv],
                       capture_output=True, text=True)
    kontrol("venv olustu", r.returncode == 0, r.stderr[-500:])
    py = os.path.join(venv, "bin", "python")
    # Kopyadan kurulur: pip agacin icinde derler (build/, *.egg-info) -- depo kirlenmesin
    kaynak = os.path.join(gecici, "kaynak")
    shutil.copytree(KOK, kaynak, ignore=shutil.ignore_patterns(*_KOPYALANMAYAN))
    sizan = [os.path.relpath(os.path.join(k, a), kaynak) for k, dizinler, dosyalar in os.walk(kaynak)
             for a in dizinler + dosyalar if a.startswith(_GIZLI_ADLAR)]
    kontrol("kopyada .git/.claude/.env* yok", not sizan, "-> %s" % sizan[:5])
    r = subprocess.run([py, "-m", "pip", "install", "-q", "--no-deps", kaynak],
                       capture_output=True, text=True, cwd=gecici)
    kontrol("pip install --no-deps .", r.returncode == 0, r.stderr[-1500:])
    temiz = os.path.join(gecici, "temiz")
    os.makedirs(temiz)
    ortam = {k: v for k, v in os.environ.items()
             if k not in ("PYTHONPATH", "OPENMC_ARAYUZ_LOCALE", "OPENMC_ARAYUZ_KILAVUZ",
                          "OPENMC_ARAYUZ_VERI")}
    ortam.update(KAYNAK_KOK=KOK, QT_QPA_PLATFORM="offscreen")
    r = subprocess.run([py, "-c", _KURULU_DENETIM], capture_output=True, text=True, cwd=temiz,
                       env=ortam, timeout=_ALT_SUREC_SURESI * 3)
    kontrol("kurulu paket denetimi (yollar, veri, ceviri, pencere, tukenme)", r.returncode == 0,
            (r.stdout + r.stderr)[-2000:])
    kosu = os.path.join(venv, "bin", "openmc-arayuz-kosu")
    r = subprocess.run([kosu, "--alt", "tukenme", "--help"], capture_output=True, text=True,
                       cwd=temiz, env=ortam, timeout=_ALT_SUREC_SURESI)
    kontrol("openmc-arayuz-kosu --alt tukenme --help", r.returncode == 0 and "--hazirla" in r.stdout,
            r.stderr[-500:])


HIZLI = [test_paket_ve_veri_dizinleri, test_veri_koku_ortam_degiskeni, test_veri_koku_aday_sirasi,
         test_dagitim_kaydindan_paylasim_dizini,
         test_ozel_dizin_ortam_degiskenleri, test_xdg_dizinleri, test_gunluk_xdg_tek_kaynak,
         test_moduller_yollari_kullanir, test_openmc_ikilisi_sirasi, test_openmc_ikilisi_guvenlik,
         test_kosucu_openmc_yolu_yollara_baglanir, test_alt_surec_komutu,
         test_kosu_alt_dagiticisi, test_alt_surec_gercek_komut_satiri,
         test_runpy_ve_modul_adi_yok, test_paket_verisi_tam, test_kaynak_dosyalari_800_satir_alti]
YAVAS = [test_kurulu_paket]
