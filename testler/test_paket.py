# -*- coding: utf-8 -*-
"""
test_paket.py -- dagitim denetimi (Dalga 4, Ajan 16). HEPSI HIZLI.

- LICENSE ("tum haklari saklidir") ve THIRD_PARTY_LICENSES.md var, beklenen
  bilesenleri anar.
- Surum tek kaynak: pyproject.toml -> cekirdek/surum.py; kod dosyalarinda
  (py/sh/Dockerfile/yaml) surum numarasinin ikinci bir kopyasi yok.
- pyproject giris noktalari ice aktarilir; `openmc-arayuz-kosu --help` 0 doner.
- Izlenen metin dosyalarinda kisisel/makineye ozgu deger yok: /home/<ad>
  yolu, e-posta adresi (ticarilesmeye hazirlik kurali).
- Docker ve conda betikleri sozdizimi denetiminden gecer (bash -n).
"""

import importlib
import os
import re
import shutil
import subprocess
import sys

from testler.ortak_test import kontrol, KOK
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik

_ZAMAN_ASIMI = 60.0          # s; alt surec (git, --help, bash -n)
_EV_YOLU = re.compile(r"/home/[A-Za-z0-9_]")
_EPOSTA = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
# izinli e-posta bicimleri: gettext sablon basligi, git ortak yazar satiri
_IZINLI_EPOSTA = {"LL@li.org", "noreply@anthropic.com"}
# surum numarasinin yazilabilecegi yerler (kaynak ve gunluk/not belgeleri);
# locale/*.po(t) basliklari pybabel uretir, kod degildir.
_SURUM_IZINLI = {"pyproject.toml", "CHANGELOG.md", os.path.join("docs", "SURUM_NOTLARI.md")}
_KOD_UZANTILARI = (".py", ".sh", ".yml", ".yaml", ".toml", ".cfg")


def _pyproject():
    import tomllib
    with open(os.path.join(KOK, "pyproject.toml"), "rb") as f:
        return tomllib.load(f)


def _izlenen_dosyalar():
    """git ls-files (depo degilse None); calisma agacinda var olanlar."""
    try:
        cikti = subprocess.run(["git", "-C", KOK, "ls-files", "-z"], capture_output=True,
                               timeout=_ZAMAN_ASIMI, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    adlar = [a.decode("utf-8") for a in cikti.split(b"\0") if a]
    return [a for a in adlar if os.path.isfile(os.path.join(KOK, a))]


def _metin(yol):
    """Dosyanin metni; ikili dosya (NUL bayti) ya da UTF-8 olmayan dosya icin None."""
    with open(os.path.join(KOK, yol), "rb") as f:
        veri = f.read()
    if b"\0" in veri:
        return None
    try:
        return veri.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _oku(ad):
    yol = os.path.join(KOK, ad)
    if not os.path.isfile(yol):
        return None
    with open(yol, encoding="utf-8") as f:
        return f.read()


@gereksinim("R-M8-01")
def test_lisans_dosyalari():
    print("\n[P1] PAKET: LICENSE ve THIRD_PARTY_LICENSES.md")
    lisans = _oku("LICENSE")
    kontrol("LICENSE var", lisans is not None)
    lisans = lisans or ""
    kontrol("LICENSE: tum haklari saklidir (TR + EN)",
            "Tüm hakları saklıdır" in lisans and "All rights reserved" in lisans)
    kontrol("LICENSE: telif satiri", bool(re.search(r"Copyright \(c\) \d{4} \S", lisans)))
    kontrol("LICENSE: e-posta yok", not _EPOSTA.search(lisans))
    ucuncu = _oku("THIRD_PARTY_LICENSES.md")
    kontrol("THIRD_PARTY_LICENSES.md var", ucuncu is not None)
    ucuncu = ucuncu or ""
    for ad, lis in (("OpenMC", "MIT"), ("PySide6", "LGPL-3.0"), ("Inter", "Open Font License"),
                    ("Lucide", "ISC"), ("mit-crpg/benchmarks", "MIT"), ("ENDF/B-VIII.0", "")):
        kontrol("THIRD_PARTY: %s %s" % (ad, lis), ad in ucuncu and lis in ucuncu)
    kontrol("THIRD_PARTY: LGPL dinamik baglama notu", "dinamik" in ucuncu)
    proje = _pyproject()["project"]
    kontrol("pyproject license-files iki dosyayi tasir",
            set(proje.get("license-files", [])) >= {"LICENSE", "THIRD_PARTY_LICENSES.md"})
    kontrol("pyproject: PyPI'a yuklenmez sinifi",
            "Private :: Do Not Upload" in proje.get("classifiers", []))


@gereksinim("R-M7-01")
def test_surum_tek_kaynak():
    print("\n[P2] PAKET: surum tek kaynaktan (pyproject.toml -> cekirdek/surum.py)")
    from cekirdek import surum
    beklenen = _pyproject()["project"]["version"]
    kontrol("surum() == pyproject", surum.surum() == beklenen,
            "-> %s / %s" % (surum.surum(), beklenen))
    kontrol("kaynak agacinda pyproject meta veriden once okunur",
            surum._pyproject_surumu() == beklenen)
    kontrol("geri donus bir surum numarasi degil (ikinci kopya yok)",
            not re.match(r"^\d+\.\d+", surum._GERI_DONUS_SURUMU), surum._GERI_DONUS_SURUMU)
    tarif = _oku(os.path.join("conda-recipe", "meta.yaml")) or ""
    kontrol("conda tarifi surumu pyproject'ten okur",
            "load_file_data" in tarif and beklenen not in tarif)
    dosyalar = _izlenen_dosyalar()
    if dosyalar is None:
        kontrol("git ls-files okunamadi: kopya taramasi atlandi", True)
        return
    kopyalar = []
    for ad in dosyalar:
        if ad in _SURUM_IZINLI or not (ad.endswith(_KOD_UZANTILARI) or
                                       os.path.basename(ad) == "Dockerfile"):
            continue
        metin = _metin(ad)
        if metin and re.search(r"(?<![\w.])%s(?![\w.])" % re.escape(beklenen), metin):
            kopyalar.append(ad)
    kontrol("kod dosyalarinda surum numarasinin kopyasi yok", not kopyalar, "-> %s" % kopyalar)


@gereksinim("R-M7-01")
def test_giris_noktalari():
    print("\n[P3] PAKET: pyproject giris noktalari")
    betikler = _pyproject()["project"]["scripts"]
    kontrol("iki giris komutu tanimli",
            set(betikler) == {"openmc-arayuz", "openmc-arayuz-kosu"}, "-> %s" % sorted(betikler))
    for ad, hedef in sorted(betikler.items()):
        modul, islev = hedef.split(":")
        nesne = getattr(importlib.import_module(modul), islev, None)
        kontrol("%s -> %s cagrilabilir" % (ad, hedef), callable(nesne))
    ortam = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    kod = ("import sys; sys.argv = ['openmc-arayuz-kosu', '--help']; "
           "from cekirdek.giris import kosu; sys.exit(kosu())")
    sonuc = subprocess.run([sys.executable, "-c", kod], cwd=KOK, env=ortam, capture_output=True,
                           text=True, timeout=_ZAMAN_ASIMI)
    kontrol("openmc-arayuz-kosu --help (kaynak agaci) cikis 0", sonuc.returncode == 0,
            "-> %s %s" % (sonuc.returncode, sonuc.stderr[-300:]))
    kontrol("--help kullanim metni basar", "KULLANIM" in sonuc.stdout or "USAGE" in sonuc.stdout)
    komut = shutil.which("openmc-arayuz-kosu")
    if komut is None:
        kontrol("kurulu komut yok (pip install -e . yapilmamis): atlandi", True)
        return
    sonuc = subprocess.run([komut, "--help"], cwd=KOK, env=ortam, capture_output=True,
                           text=True, timeout=_ZAMAN_ASIMI)
    kontrol("kurulu openmc-arayuz-kosu --help cikis 0", sonuc.returncode == 0,
            "-> %s" % sonuc.returncode)


def test_kisisel_deger_yok():
    print("\n[P4] PAKET: izlenen dosyalarda /home/ yolu ve e-posta yok")
    dosyalar = _izlenen_dosyalar()
    if dosyalar is None:
        kontrol("git ls-files okunamadi: tarama atlandi", True)
        return
    ev, eposta = [], []
    for ad in dosyalar:
        metin = _metin(ad)
        if metin is None:
            continue
        for no, satir in enumerate(metin.splitlines(), 1):
            if _EV_YOLU.search(satir):
                ev.append("%s:%d" % (ad, no))
            bulunan = set(_EPOSTA.findall(satir)) - _IZINLI_EPOSTA
            if bulunan:
                eposta.append("%s:%d %s" % (ad, no, sorted(bulunan)))
    kontrol("metin dosyalarinda /home/<ad> yolu yok", not ev, "-> %s" % ev[:10])
    kontrol("metin dosyalarinda e-posta adresi yok", not eposta, "-> %s" % eposta[:10])


def test_dagitim_betikleri():
    print("\n[P5] PAKET: Docker ve conda dosyalari")
    for ad in ("Dockerfile", ".dockerignore", os.path.join("docker", "giris.sh"),
               os.path.join("docker", "calistir.sh"), os.path.join("docker", "derle.sh"),
               os.path.join("conda-recipe", "meta.yaml"), os.path.join("conda-recipe", "build.sh"),
               "CHANGELOG.md", os.path.join("docs", "SURUM_NOTLARI.md")):
        kontrol("%s var" % ad, os.path.isfile(os.path.join(KOK, ad)))
    docker = _oku("Dockerfile") or ""
    kod_satirlari = [s for s in docker.splitlines() if not s.lstrip().startswith("#")]
    kod = "\n".join(kod_satirlari)
    kontrol("Dockerfile: OpenMC surumu environment.yml'den (imajda ayri sabit yok)",
            "environment.yml" in kod and "openmc=" not in kod)
    kontrol("Dockerfile: nukleer veri imaja gomulmez (derlemede indirme yok, /veri hacmi)",
            not any("veri_indir.sh --" in s or "anl.box.com" in s for s in kod_satirlari)
            and any(s.startswith("VOLUME") and "/veri" in s for s in kod_satirlari))
    bash = shutil.which("bash")
    if bash is None:
        kontrol("bash yok: sozdizimi denetimi atlandi", True)
        return
    for ad in ("docker/giris.sh", "docker/calistir.sh", "docker/derle.sh",
               "conda-recipe/build.sh"):
        sonuc = subprocess.run([bash, "-n", os.path.join(KOK, ad)], capture_output=True,
                               text=True, timeout=_ZAMAN_ASIMI)
        kontrol("%s bash -n" % ad, sonuc.returncode == 0, sonuc.stderr[-200:])


HIZLI = [test_lisans_dosyalari, test_surum_tek_kaynak, test_giris_noktalari,
         test_kisisel_deger_yok, test_dagitim_betikleri]
YAVAS = []
