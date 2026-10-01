# -*- coding: utf-8 -*-
"""
surum.py -- surum ve uygulama adi TEK YERDEN.

Surumun tek kaynagi pyproject.toml'daki [project].version'dir:
  1. kaynak agacindaki pyproject.toml (gelistirme, `pip install -e .`):
     duzenlenebilir kurulumun meta verisi surum degisince yeniden kurulana
     dek ESKI kalir; bu yuzden once dosyaya bakilir,
  2. dosya yoksa (wheel / conda paketi) importlib.metadata,
  3. ikisi de yoksa "bilinmiyor" isareti (_GERI_DONUS_SURUMU). Burada surum
     numarasi YAZILMAZ: ikinci bir kopya tek kaynak kuralini bozar.

Urun adi ve marka metni yalnizca UYGULAMA_ADI'ndadir; pencere basligi,
Hakkinda penceresi ve rapor bu sabiti kullanir (ad degisirse tek satir).
"""

import os

from cekirdek.ceviri import N_

# Urun adi kimlik olarak SABIT kalir (Qt applicationName -> ayar dosyasi yolu,
# kapsul.json); gosterirken _(UYGULAMA_ADI) ile etkin dile cevrilir.
UYGULAMA_ADI = N_("OpenMC Reaktör Kuru Arayüzü")
PAKET_ADI = "openmc-arayuz"
_GERI_DONUS_SURUMU = "0+bilinmiyor"
_PYPROJECT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "pyproject.toml")


def _pyproject_surumu(yol=_PYPROJECT):
    """pyproject.toml'daki surum; dosya yoksa ya da okunamazsa None."""
    try:
        import tomllib
    except ImportError:          # Python < 3.11
        return None
    try:
        with open(yol, "rb") as f:
            return tomllib.load(f)["project"]["version"]
    except (OSError, KeyError, ValueError):   # siradaki kaynaga dusulur (surum())
        return None


def _meta_surumu():
    from importlib import metadata
    try:
        return metadata.version(PAKET_ADI)
    except metadata.PackageNotFoundError:     # paket kurulu degil: geri donus isareti
        return None


def surum():
    """Uygulama surumu (PEP 440 metni, ornek "X.Y.ZrcN")."""
    return _pyproject_surumu() or _meta_surumu() or _GERI_DONUS_SURUMU


__version__ = surum()


# ----------------------------------------------------------------------------
# Derleme / kaynak bilgisi (rapor tekrarlanabilirlik blogu, Hakkinda)
# ----------------------------------------------------------------------------
_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GIT = "git"                 # testler var olmayan bir komutla degistirir
_GIT_SURESI = 5.0            # s; takilan bir git komutu raporu bekletmesin


def _git(*argumanlar):
    """Kaynak agacinda git komutu; cikti metni ya da (git yok / depo degil /
    zaman asimi) None. Neden loglanir (INFO): kurulu pakette git olmamasi
    olagandir, hata degildir."""
    import subprocess
    from cekirdek.gunluk import kaydedici
    try:
        cikti = subprocess.run([_GIT, "-C", _KOK] + list(argumanlar), capture_output=True,
                               text=True, timeout=_GIT_SURESI, check=True)
    except (OSError, subprocess.SubprocessError) as e:
        kaydedici(__name__).info("git bilgisi okunamadı (%s): %s", " ".join(argumanlar), e)
        return None
    return cikti.stdout.strip()


def derleme_bilgisi():
    """
    Uygulamanin kimligi (YENI sozluk):
      uygulama        UYGULAMA_ADI
      surum           surum()
      git_commit      40 haneli commit ya da None (git/depo yoksa; loglanir)
      git_degisiklik  calisma agacinda commit edilmemis degisiklik var mi; None
      python          Python surumu
      platform        isletim sistemi / mimari
    """
    import platform
    commit = _git("rev-parse", "HEAD")
    durum = _git("status", "--porcelain", "--untracked-files=no") if commit else None
    return {
        "uygulama": UYGULAMA_ADI,
        "surum": surum(),
        "git_commit": commit or None,
        "git_degisiklik": (bool(durum) if durum is not None else None),
        "python": platform.python_version(),
        "platform": platform.platform(terse=True),
    }
