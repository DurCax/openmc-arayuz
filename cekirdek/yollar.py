# -*- coding: utf-8 -*-
"""
yollar.py -- uygulamanin TEK yol kaynagi (v3 T2).

Diger moduller `__file__`'dan yol hesaplamaz; buradaki islevleri kullanir.
Yalniz standart kutuphane: ceviri.py gibi en erken yuklenen moduller de
ice aktarabilsin (dongu ve agir import yok).

PAKET ICI (paketle birlikte gelir; package-data)
  paket_koku()            cekirdek/ ve arayuz/'u iceren dizin (kaynak agacinda
                          depo koku; kurulu pakette site-packages)
  kaynak_agaci_mi()       paket koku bir kaynak agaci mi (pyproject.toml var)
  ikon_dizini()           arayuz/kaynaklar/ikonlar
  font_dizini()           arayuz/kaynaklar/fontlar
  rapor_sablon_dizini()   cekirdek/rapor_sablon
  pyproject_yolu()        <paket koku>/pyproject.toml (yalniz kaynak agacinda var)

VERI (paketin disinda; kurulu pakette data-files -> <onek>/share/openmc-arayuz)
  veri_koku()             ornekler/, locale/, docs/kilavuz/'u iceren dizin
  ornekler_dizini()       <veri koku>/ornekler
  locale_dizini()         OPENMC_ARAYUZ_LOCALE ya da <veri koku>/locale
  kilavuz_dizini()        OPENMC_ARAYUZ_KILAVUZ ya da <veri koku>/docs/kilavuz

  Bir dizin VERI_ISARETI dosyasini (ornekler/pwr_pinhucre.json) iceriyorsa
  veri kokudur: site-packages'ta baska bir paketin birakmis olabilecegi
  yabanci bir ornekler/ dizini secilmez.
  veri_koku() sirasi: OPENMC_ARAYUZ_VERI > paket koku (kaynak agaci ve conda
  paketi: build.sh agaci share/openmc-arayuz'a kopyalar) > kurulu dagitimin
  kaydindaki share/openmc-arayuz (venv, --user, --prefix) > <paket koku>/
  share/openmc-arayuz (pip install --target; RECORD'da yok) > sys.prefix/
  share/openmc-arayuz > paket koku (son care; cagiran "dosya bulunamadi"
  hatasini kendisi gosterir).

  Ortam degiskenleri (OPENMC_ARAYUZ_VERI/_LOCALE/_KILAVUZ): ~ acilir, goreli
  yol mutlaga cevrilir; dizin yoksa (VERI'de isaret yoksa) UYARI loglanir ve
  degisken yok sayilir.

KULLANICI DIZINLERI (XDG Base Directory; $XDG_* mutlak degilse yok sayilir)
  ayar_dizini()           $XDG_CONFIG_HOME/openmc_arayuz  (~/.config/...)
  kullanici_veri_dizini() $XDG_DATA_HOME/openmc_arayuz    (~/.local/share/...)
  onbellek_dizini()       $XDG_CACHE_HOME/openmc_arayuz   (~/.cache/...)
  durum_dizini()          $XDG_STATE_HOME/openmc_arayuz   (~/.local/state/...)
  Hepsi `ortam=` alir (test / alt surec ortami); dizin OLUSTURULMAZ.

ARACLAR
  openmc_ikilisi()        openmc calistirilabilir dosyasinin MUTLAK yolu ya da None.
                          Sira: $OPENMC_ARAYUZ_OPENMC (mutlak olmali; ~ acilir) >
                          python yorumlayicisinin yanindaki bin/openmc (ayni
                          ortam garantisi; etkinlestirilmemis conda ortami) >
                          PATH (yalniz MUTLAK ogeler: bos/"."/goreli oge CWD'yi
                          aratirdi -- kosucu cwd=model dizini ile calisir) >
                          $CONDA_PREFIX/bin. Calistirilamayan aday atlanir;
                          denetlenen yol, dondurulen (calistirilan) yoldur.

Islevlerin hepsi her cagrida ortami yeniden okur (onbellek yalniz kurulu
dagitimin dosya listesindedir); modul sabitleri (ceviri.LOCALE_DIZINI vb.)
ice aktarma aninda bir kez hesaplanir, eski davranisla ayni.
"""

import functools
import logging
import os
import sys
from typing import Iterator, Mapping, Optional

Ortam = Optional[Mapping[str, str]]        # None -> os.environ

UYGULAMA_DIZINI = "openmc_arayuz"          # XDG alt dizini (gunluk.UYGULAMA_DIZINI de bu)
PAYLASIM_ADI = "openmc-arayuz"             # <onek>/share/<ad> (conda-recipe/build.sh)
DAGITIM_ADI = "openmc-arayuz"              # pyproject [project].name
VERI_ORTAM_DEGISKENI = "OPENMC_ARAYUZ_VERI"
LOCALE_ORTAM_DEGISKENI = "OPENMC_ARAYUZ_LOCALE"
KILAVUZ_ORTAM_DEGISKENI = "OPENMC_ARAYUZ_KILAVUZ"
OPENMC_ORTAM_DEGISKENI = "OPENMC_ARAYUZ_OPENMC"
OPENMC_ADI = "openmc"
_ORNEK_DIZINI = "ornekler"
# Veri kokunu taniyan uygulamaya ozgu dosya (README'nin ilk ornegi; test_t2_yollar
# kaynak agacinda var oldugunu denetler -- adi degisirse burasi da degisir).
VERI_ISARETI = os.path.join(_ORNEK_DIZINI, "pwr_pinhucre.json")

# XDG Base Directory Specification 0.8: degisken -> ev dizinine gore varsayilan
_XDG_VARSAYILAN = {
    "XDG_CONFIG_HOME": (".config",),
    "XDG_DATA_HOME": (".local", "share"),
    "XDG_CACHE_HOME": (".cache",),
    "XDG_STATE_HOME": (".local", "state"),
}

_log = logging.getLogger("openmc_arayuz.yollar")   # gunluk.KOK_KAYDEDICI altinda

_PAKET_KOKU = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ortam(ortam: Ortam) -> Mapping[str, str]:
    return os.environ if ortam is None else ortam


# ---------------------------------------------------------------------------
# paket ici
# ---------------------------------------------------------------------------

def paket_koku() -> str:
    """cekirdek/ ve arayuz/ paketlerini iceren dizin."""
    return _PAKET_KOKU


def pyproject_yolu() -> str:
    """Kaynak agacindaki pyproject.toml (kurulu pakette yoktur; surum.py
    o zaman paket meta verisine duser)."""
    return os.path.join(_PAKET_KOKU, "pyproject.toml")


def kaynak_agaci_mi() -> bool:
    """Paket kaynak agacindan mi calisiyor (kurulu paket degil)."""
    return os.path.isfile(pyproject_yolu())


def ikon_dizini() -> str:
    return os.path.join(_PAKET_KOKU, "arayuz", "kaynaklar", "ikonlar")


def font_dizini() -> str:
    return os.path.join(_PAKET_KOKU, "arayuz", "kaynaklar", "fontlar")


def rapor_sablon_dizini() -> str:
    return os.path.join(_PAKET_KOKU, "cekirdek", "rapor_sablon")


# ---------------------------------------------------------------------------
# ortam degiskeninden dizin
# ---------------------------------------------------------------------------

def _mutlak(yol: str) -> str:
    return os.path.abspath(os.path.expanduser(yol))


def _ortam_dizini(ortam: Mapping[str, str], degisken: str, isaret: str = "") -> Optional[str]:
    """Degiskendeki dizin (~ acilmis, mutlak); bos ise None. Dizin yoksa (ya
    da `isaret` dosyasi yoksa) uyarir ve None doner."""
    deger = ortam.get(degisken)
    if not deger:
        return None
    yol = _mutlak(deger)
    if os.path.isdir(yol) and (not isaret or os.path.isfile(os.path.join(yol, isaret))):
        return yol
    _log.warning("%s=%s yok sayildi: dizin yok%s", degisken, deger,
                 " ya da icinde %s yok" % isaret if isaret else "")
    return None


# ---------------------------------------------------------------------------
# veri koku
# ---------------------------------------------------------------------------

def _veri_koku_mu(dizin: Optional[str]) -> bool:
    return bool(dizin) and os.path.isfile(os.path.join(dizin, VERI_ISARETI))


def _paylasim_kaydi(dagitim) -> Optional[str]:
    parca = ("share", PAYLASIM_ADI, _ORNEK_DIZINI)
    for dosya in dagitim.files or ():
        p = dosya.parts
        for i in range(len(p) - len(parca) + 1):
            if p[i:i + len(parca)] == parca:
                return os.path.normpath(os.path.join(str(dagitim.locate_file("")),
                                                     *p[:i + len(parca) - 1]))
    return None


@functools.lru_cache(maxsize=1)
def _dagitim_paylasim_dizini() -> Optional[str]:
    """Kurulu dagitimin RECORD kaydindan share/openmc-arayuz'un mutlak yolu;
    dagitim yoksa, veri dosyasi kaydedilmemisse ya da kayit okunamazsa
    (uyari loglanir) None. Kurulum bicimi (venv, --user, --prefix) ne olursa
    olsun dogru oneki verir."""
    from importlib import metadata
    try:
        dagitim = metadata.distribution(DAGITIM_ADI)
    except metadata.PackageNotFoundError:
        return None
    try:
        return _paylasim_kaydi(dagitim)
    except (OSError, ValueError) as e:
        _log.warning("%s dagitiminin RECORD kaydi okunamadi: %s", DAGITIM_ADI, e)
        return None


def _veri_adaylari(ortam: Mapping[str, str]) -> Iterator[Optional[str]]:
    yield _ortam_dizini(ortam, VERI_ORTAM_DEGISKENI, VERI_ISARETI)
    yield _PAKET_KOKU
    yield _dagitim_paylasim_dizini()
    yield os.path.join(_PAKET_KOKU, "share", PAYLASIM_ADI)     # pip install --target
    yield os.path.join(sys.prefix, "share", PAYLASIM_ADI)


def veri_koku(ortam: Ortam = None) -> str:
    """ornekler/, locale/, docs/kilavuz/'u iceren dizin (sira: modul belgesi)."""
    for aday in _veri_adaylari(_ortam(ortam)):
        if _veri_koku_mu(aday):
            return aday
    return _PAKET_KOKU


def ornekler_dizini(ortam: Ortam = None) -> str:
    return os.path.join(veri_koku(ortam), _ORNEK_DIZINI)


def locale_dizini(ortam: Ortam = None) -> str:
    ortam = _ortam(ortam)
    return (_ortam_dizini(ortam, LOCALE_ORTAM_DEGISKENI)
            or os.path.join(veri_koku(ortam), "locale"))


def kilavuz_dizini(ortam: Ortam = None) -> str:
    ortam = _ortam(ortam)
    return (_ortam_dizini(ortam, KILAVUZ_ORTAM_DEGISKENI)
            or os.path.join(veri_koku(ortam), "docs", "kilavuz"))


# ---------------------------------------------------------------------------
# XDG kullanici dizinleri
# ---------------------------------------------------------------------------

def _xdg(degisken: str, ortam: Ortam) -> str:
    taban = _ortam(ortam).get(degisken)
    if not taban or not os.path.isabs(taban):
        # XDG: "If an implementation encounters a relative path in any of these
        # variables it should consider the path invalid and ignore it."
        taban = os.path.join(os.path.expanduser("~"), *_XDG_VARSAYILAN[degisken])
    return os.path.join(taban, UYGULAMA_DIZINI)


def ayar_dizini(ortam: Ortam = None) -> str:
    return _xdg("XDG_CONFIG_HOME", ortam)


def kullanici_veri_dizini(ortam: Ortam = None) -> str:
    return _xdg("XDG_DATA_HOME", ortam)


def onbellek_dizini(ortam: Ortam = None) -> str:
    return _xdg("XDG_CACHE_HOME", ortam)


def durum_dizini(ortam: Ortam = None) -> str:
    return _xdg("XDG_STATE_HOME", ortam)


# ---------------------------------------------------------------------------
# openmc ikilisi
# ---------------------------------------------------------------------------

def _calistirilabilir_mi(yol: str) -> bool:
    return os.path.isfile(yol) and os.access(yol, os.X_OK)


def _ortam_openmc(ortam: Mapping[str, str]) -> Iterator[str]:
    deger = ortam.get(OPENMC_ORTAM_DEGISKENI)
    if not deger:
        return
    yol = os.path.expanduser(deger)
    if not os.path.isabs(yol):
        _log.warning("%s=%s yok sayildi: mutlak yol olmali", OPENMC_ORTAM_DEGISKENI, deger)
        return
    if not _calistirilabilir_mi(yol):
        _log.warning("%s=%s yok sayildi: calistirilabilir dosya degil",
                     OPENMC_ORTAM_DEGISKENI, deger)
        return
    yield yol


def _path_adaylari(ortam: Mapping[str, str]) -> Iterator[str]:
    # Bos, "." ve goreli ogeler CWD'ye gore cozulurdu: yok sayilir.
    for oge in ortam.get("PATH", "").split(os.pathsep):
        if oge and os.path.isabs(oge):
            yield os.path.join(oge, OPENMC_ADI)


def _openmc_adaylari(ortam: Mapping[str, str], python: str) -> Iterator[str]:
    yield from _ortam_openmc(ortam)
    if os.path.isabs(python):
        yield os.path.join(os.path.dirname(python), OPENMC_ADI)
    yield from _path_adaylari(ortam)
    onek = ortam.get("CONDA_PREFIX")
    if onek and os.path.isabs(onek):
        yield os.path.join(onek, "bin", OPENMC_ADI)


def openmc_ikilisi(ortam: Ortam = None, python: Optional[str] = None) -> Optional[str]:
    """openmc calistirilabilir dosyasinin mutlak yolu; bulunamazsa None.

    ortam  : ortam degiskenleri (varsayilan os.environ)
    python : yanindaki bin/ dizinine bakilacak yorumlayici (varsayilan
             sys.executable)
    Sira ve guvenlik kurallari: modul belgesi (ARACLAR).
    """
    ortam = _ortam(ortam)
    for aday in _openmc_adaylari(ortam, python or sys.executable):
        yol = os.path.normpath(aday)          # denetlenen = dondurulen (calistirilan)
        if _calistirilabilir_mi(yol):
            return yol
    return None
