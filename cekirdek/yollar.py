# -*- coding: utf-8 -*-
"""
yollar.py -- uygulamanin TEK yol kaynagi (v3 T2).

Diger moduller `__file__`'dan yol hesaplamaz; buradaki islevleri kullanir.
Yalniz standart kutuphane: ceviri.py gibi en erken yuklenen moduller de
ice aktarabilsin (dongu ve agir import yok).

PAKET ICI (paketle birlikte gelir; package-data)
  paket_koku()            cekirdek/ ve arayuz/'u iceren dizin (kaynak agacinda
                          depo koku; kurulu pakette site-packages)
  ikon_dizini()           arayuz/kaynaklar/ikonlar
  font_dizini()           arayuz/kaynaklar/fontlar
  rapor_sablon_dizini()   cekirdek/rapor_sablon
  pyproject_yolu()        <paket koku>/pyproject.toml (yalniz kaynak agacinda var)

VERI (paketin disinda; kurulu pakette data-files -> <onek>/share/openmc-arayuz)
  veri_koku()             ornekler/, locale/, docs/kilavuz/'u iceren dizin
  ornekler_dizini()       <veri koku>/ornekler
  locale_dizini()         OPENMC_ARAYUZ_LOCALE ya da <veri koku>/locale
  kilavuz_dizini()        OPENMC_ARAYUZ_KILAVUZ ya da <veri koku>/docs/kilavuz

  veri_koku() sirasi: OPENMC_ARAYUZ_VERI (var olan dizinse) > paket koku
  (kaynak agaci ve conda paketi: build.sh agaci share/openmc-arayuz'a kopyalar)
  > kurulu dagitimin kaydindaki share/openmc-arayuz (venv, --user, --target)
  > sys.prefix/share/openmc-arayuz > paket koku (son care; yoksa cagiran
  "dosya bulunamadi" hatasini kendisi gosterir).

KULLANICI DIZINLERI (XDG Base Directory; $XDG_* mutlak degilse yok sayilir)
  ayar_dizini()           $XDG_CONFIG_HOME/openmc_arayuz  (~/.config/...)
  kullanici_veri_dizini() $XDG_DATA_HOME/openmc_arayuz    (~/.local/share/...)
  onbellek_dizini()       $XDG_CACHE_HOME/openmc_arayuz   (~/.cache/...)
  durum_dizini()          $XDG_STATE_HOME/openmc_arayuz   (~/.local/state/...)
  Hepsi `ortam=` alir (test / alt surec ortami); dizin OLUSTURULMAZ.

ARACLAR
  openmc_ikilisi(ayar=None) openmc calistirilabilir dosyasi ya da None.
                          Sira: ayar (cagiranin ayarindaki yol) >
                          $OPENMC_ARAYUZ_OPENMC > PATH > python'un yanindaki
                          bin/ (etkinlestirilmemis conda ortami) >
                          $CONDA_PREFIX/bin. Calistirilamayan aday atlanir.

Islevlerin hepsi her cagrida ortami yeniden okur (onbellek yalniz kurulu
dagitimin dosya listesindedir); modul sabitleri (ceviri.LOCALE_DIZINI vb.)
ice aktarma aninda bir kez hesaplanir, eski davranisla ayni.
"""

import functools
import logging
import os
import shutil
import sys

UYGULAMA_DIZINI = "openmc_arayuz"          # XDG alt dizini (gunluk.py ile ayni ad)
PAYLASIM_ADI = "openmc-arayuz"             # <onek>/share/<ad> (conda-recipe/build.sh)
DAGITIM_ADI = "openmc-arayuz"              # pyproject [project].name
VERI_ORTAM_DEGISKENI = "OPENMC_ARAYUZ_VERI"
LOCALE_ORTAM_DEGISKENI = "OPENMC_ARAYUZ_LOCALE"
KILAVUZ_ORTAM_DEGISKENI = "OPENMC_ARAYUZ_KILAVUZ"
OPENMC_ORTAM_DEGISKENI = "OPENMC_ARAYUZ_OPENMC"
OPENMC_ADI = "openmc"
_VERI_ISARETI = "ornekler"                 # veri kokunu taniyan alt dizin

# XDG Base Directory Specification 0.8: degisken -> ev dizinine gore varsayilan
_XDG_VARSAYILAN = {
    "XDG_CONFIG_HOME": (".config",),
    "XDG_DATA_HOME": (".local", "share"),
    "XDG_CACHE_HOME": (".cache",),
    "XDG_STATE_HOME": (".local", "state"),
}

_log = logging.getLogger("openmc_arayuz.yollar")   # gunluk.KOK_KAYDEDICI altinda

_PAKET_KOKU = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ortam(ortam):
    return os.environ if ortam is None else ortam


# ---------------------------------------------------------------------------
# paket ici
# ---------------------------------------------------------------------------

def paket_koku():
    """cekirdek/ ve arayuz/ paketlerini iceren dizin."""
    return _PAKET_KOKU


def ikon_dizini():
    return os.path.join(_PAKET_KOKU, "arayuz", "kaynaklar", "ikonlar")


def font_dizini():
    return os.path.join(_PAKET_KOKU, "arayuz", "kaynaklar", "fontlar")


def rapor_sablon_dizini():
    return os.path.join(_PAKET_KOKU, "cekirdek", "rapor_sablon")


def pyproject_yolu():
    """Kaynak agacindaki pyproject.toml (kurulu pakette yoktur; surum.py
    o zaman paket meta verisine duser)."""
    return os.path.join(_PAKET_KOKU, "pyproject.toml")


# ---------------------------------------------------------------------------
# veri koku
# ---------------------------------------------------------------------------

def _veri_koku_mu(dizin):
    return bool(dizin) and os.path.isdir(os.path.join(dizin, _VERI_ISARETI))


@functools.lru_cache(maxsize=1)
def _dagitim_paylasim_dizini():
    """Kurulu dagitimin RECORD kaydindan share/openmc-arayuz'un mutlak yolu;
    dagitim yoksa ya da veri dosyasi kaydedilmemisse None. Kurulum bicimi
    (venv, --user, --prefix) ne olursa olsun dogru oneki verir."""
    from importlib import metadata
    try:
        dagitim = metadata.distribution(DAGITIM_ADI)
    except metadata.PackageNotFoundError:
        return None
    parca = ("share", PAYLASIM_ADI, _VERI_ISARETI)
    for dosya in dagitim.files or ():
        p = dosya.parts
        for i in range(len(p) - len(parca) + 1):
            if p[i:i + len(parca)] == parca:
                return os.path.normpath(os.path.join(str(dagitim.locate_file("")),
                                                     *p[:i + len(parca) - 1]))
    return None


def _veri_adaylari(ortam):
    istenen = ortam.get(VERI_ORTAM_DEGISKENI)
    if istenen:
        if _veri_koku_mu(istenen):
            yield istenen
        else:
            _log.warning("%s=%s yok sayildi: icinde %s/ dizini yok",
                         VERI_ORTAM_DEGISKENI, istenen, _VERI_ISARETI)
    yield _PAKET_KOKU
    yield _dagitim_paylasim_dizini()
    yield os.path.join(sys.prefix, "share", PAYLASIM_ADI)


def veri_koku(ortam=None):
    """ornekler/, locale/, docs/kilavuz/'u iceren dizin (sira: modul belgesi)."""
    for aday in _veri_adaylari(_ortam(ortam)):
        if _veri_koku_mu(aday):
            return aday
    return _PAKET_KOKU


def ornekler_dizini(ortam=None):
    return os.path.join(veri_koku(ortam), "ornekler")


def locale_dizini(ortam=None):
    return _ortam(ortam).get(LOCALE_ORTAM_DEGISKENI) or os.path.join(veri_koku(ortam), "locale")


def kilavuz_dizini(ortam=None):
    return (_ortam(ortam).get(KILAVUZ_ORTAM_DEGISKENI)
            or os.path.join(veri_koku(ortam), "docs", "kilavuz"))


# ---------------------------------------------------------------------------
# XDG kullanici dizinleri
# ---------------------------------------------------------------------------

def _xdg(degisken, ortam):
    taban = _ortam(ortam).get(degisken)
    if not taban or not os.path.isabs(taban):
        # XDG: "If an implementation encounters a relative path in any of these
        # variables it should consider the path invalid and ignore it."
        taban = os.path.join(os.path.expanduser("~"), *_XDG_VARSAYILAN[degisken])
    return os.path.join(taban, UYGULAMA_DIZINI)


def ayar_dizini(ortam=None):
    return _xdg("XDG_CONFIG_HOME", ortam)


def kullanici_veri_dizini(ortam=None):
    return _xdg("XDG_DATA_HOME", ortam)


def onbellek_dizini(ortam=None):
    return _xdg("XDG_CACHE_HOME", ortam)


def durum_dizini(ortam=None):
    return _xdg("XDG_STATE_HOME", ortam)


# ---------------------------------------------------------------------------
# openmc ikilisi
# ---------------------------------------------------------------------------

def _calistirilabilir_mi(yol):
    return bool(yol) and os.path.isfile(yol) and os.access(yol, os.X_OK)


def _path_te_ara(ortam):
    # Surec ortaminda shutil.which'in kendi PATH okumasi kullanilir (ayni
    # sonuc; which'i degistiren eski testler de calisir).
    if ortam is os.environ:
        return shutil.which(OPENMC_ADI)
    return shutil.which(OPENMC_ADI, path=ortam.get("PATH", os.defpath))


def _openmc_adaylari(ayar, ortam, python):
    if ayar:
        yield "ayar", ayar
    yield OPENMC_ORTAM_DEGISKENI, ortam.get(OPENMC_ORTAM_DEGISKENI)
    yield "PATH", _path_te_ara(ortam)
    yield "python", os.path.join(os.path.dirname(python), OPENMC_ADI)
    onek = ortam.get("CONDA_PREFIX")
    yield "CONDA_PREFIX", os.path.join(onek, "bin", OPENMC_ADI) if onek else None


def openmc_ikilisi(ayar=None, ortam=None, python=None):
    """openmc calistirilabilir dosyasinin yolu; bulunamazsa None.

    ayar   : cagiranin ayarlarindan gelen yol (bos/None ise atlanir)
    ortam  : ortam degiskenleri (varsayilan os.environ)
    python : yanindaki bin/ dizinine bakilacak yorumlayici (varsayilan
             sys.executable; conda ortami etkinlestirilmeden calistirilinca)
    """
    ortam = _ortam(ortam)
    for kaynak, yol in _openmc_adaylari(ayar, ortam, python or sys.executable):
        if _calistirilabilir_mi(yol):
            return yol
        if yol and kaynak in ("ayar", OPENMC_ORTAM_DEGISKENI):
            _log.warning("openmc yolu (%s) calistirilabilir degil, atlandi: %s", kaynak, yol)
    return None
