# -*- coding: utf-8 -*-
"""
veri_yolu.py -- nukleer verinin (tesir kesiti kutuphanesi + tukenme zinciri)
TEK cozumleyicisi (v3 K2).

Bugune kadar OPENMC_CROSS_SECTIONS / OPENMC_CHAIN_FILE dort ayri yerde
dogrudan os.environ'dan okunuyordu (dogrula, rapor, kapsul, veri_bilgi) ve
veri yoksa kosu openmc hatasiyla dusuyordu. Simdi hepsi buradan okur.

SIRA (ilk bulunan kazanir)
  cross_sections():
    1. ortam   OPENMC_CROSS_SECTIONS bos degilse O KULLANILIR -- dosya yoksa
               bile (gecerli=False): OpenMC'nin kendisi de bu degiskene bakar,
               kullanicinin bilincli secimi sessizce baska bir kutuphaneyle
               degistirilmez.
    2. ayar    <ayar_dizini()>/veri.json "cross_sections" (Veri sayfasinda
               secilen; mutlak yol). Dosya yoksa gecerli=False ve sira devam
               etmez (secim kullanicinindir; sayfa uyarir).
    3. aday    ADAY_KOKLERI altinda <kok>/cross_sections.xml ya da
               <kok>/*/cross_sections.xml (alfabetik ilk) -- veri_indir'in
               varsayilan hedefi ~/nucdata'dir.
  zincir():
    1. ortam   OPENMC_CHAIN_FILE   2. ayar "zincir"
    3. aday    kutuphanenin iki ust dizinindeki chain/<VARSAYILAN_ZINCIR>
               (veri_indir duzeni: <hedef>/<kutuphane>/cross_sections.xml +
               <hedef>/chain/), sonra <kok>/chain/<VARSAYILAN_ZINCIR>.

ALT SURECLER
  alt_surec_ortami(ortam) cozulen yollari yazan YENI bir ortam sozlugu doner
  (subprocess env=). surece_uygula() ayni degerleri bu surecin ortamina (ve
  openmc yukluyse openmc.config'e) yazar: QProcess.systemEnvironment() ve
  ortami miras alan subprocess'ler de ayni veriyi gorur. Arayuz acilista ve
  Veri sayfasinda secim degisince cagirir.

Yalniz standart kutuphane; Qt'ye bagli degil (terminal kosucusu da kullanir).
Islevlerin hepsi `ortam=` alir (None -> os.environ); test ve alt surec icin.
"""

import glob
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from typing import Dict, Mapping, MutableMapping, Optional, Tuple

from cekirdek import yollar
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

Ortam = Optional[Mapping[str, str]]

XS_DEGISKENI = "OPENMC_CROSS_SECTIONS"
ZINCIR_DEGISKENI = "OPENMC_CHAIN_FILE"
XS_DOSYASI = "cross_sections.xml"
# tukenme.ZINCIRLER["termal"] ile ayni ad (tukenme agir ice aktarim yapar;
# test_k2_veri_yolu esitligi denetler).
VARSAYILAN_ZINCIR = "chain_endfb80_thermal.xml"
ZINCIR_DIZINI = "chain"
AYAR_DOSYASI = "veri.json"
AYAR_SURUMU = 1
# Ayar dosyasinda kabul edilen anahtarlar: yol tasiyanlar MUTLAK olmali.
YOL_ANAHTARLARI = ("cross_sections", "zincir", "indirme_hedefi")
METIN_ANAHTARLARI = ("kutuphane",)
_EV_ADAY_DIZINI = "nucdata"            # veri_indir.sh'nin v2'den beri varsayilani


# Birden cok aday kutuphane varken tercih edilen dizin adi: uygulamanin
# dogrulandigi kutuphane (veri_katalogu.json "endfb-viii.0" dizin_adi).
VARSAYILAN_KUTUPHANE_DIZINI = "endfb-viii.0-hdf5"


@dataclass(frozen=True)
class Yol:
    """Bir cozum sonucu. kaynak: "ortam" | "ayar" | "aday" | "coklu" | "yok".
    "coklu": birden cok aday bulundu, hicbiri varsayilan degil -- otomatik
    secilmez (adaylar listesi Veri sayfasinda gosterilir)."""
    deger: Optional[str]
    kaynak: str
    gecerli: bool
    adaylar: Tuple[str, ...] = ()


_YOK = Yol(None, "yok", False)

# surece_uygula()'nin os.environ'a KENDI yazdigi degerler: bunlar "kullanici
# ortami" sayilmaz, yoksa Veri sayfasinda sonradan yapilan secim ortamdaki
# eski degerin arkasinda kalirdi.
_ENJEKTE: Dict[str, str] = {}


def _ortam(ortam: Ortam) -> Mapping[str, str]:
    return os.environ if ortam is None else ortam


def _ayni_yol(a: Optional[str], b: Optional[str]) -> bool:
    """Iki yol ayni dosyayi mi gosteriyor (symlink / openmc.config Path.resolve)."""
    return bool(a) and bool(b) and os.path.realpath(a) == os.path.realpath(b)


def _ortam_degeri(o: Mapping[str, str], degisken: str) -> Optional[str]:
    deger = o.get(degisken)
    if not deger or (o is os.environ and _ayni_yol(_ENJEKTE.get(degisken), deger)):
        return None
    return deger


def _ev(ortam: Mapping[str, str]) -> str:
    ev = ortam.get("HOME")
    return ev if ev and os.path.isabs(ev) else os.path.expanduser("~")


def aday_kokleri(ortam: Ortam = None) -> Tuple[str, ...]:
    """Kutuphane aranan kok dizinler: ~/nucdata, <kullanici_veri_dizini>/nucdata."""
    o = _ortam(ortam)
    return (os.path.join(_ev(o), _EV_ADAY_DIZINI),
            os.path.join(yollar.kullanici_veri_dizini(o), _EV_ADAY_DIZINI))


def varsayilan_indirme_hedefi(ortam: Ortam = None) -> str:
    """Veri sayfasi ve veri_indir icin onerilen hedef: ayardaki ya da ~/nucdata."""
    return ayar_oku(ortam).get("indirme_hedefi") or aday_kokleri(ortam)[0]


# ---------------------------------------------------------------------------
# ayar dosyasi
# ---------------------------------------------------------------------------

def ayar_yolu(ortam: Ortam = None) -> str:
    return os.path.join(yollar.ayar_dizini(_ortam(ortam)), AYAR_DOSYASI)


def ayar_oku(ortam: Ortam = None) -> Dict[str, str]:
    """Kayitli secimler (yeni sozluk). Dosya yoksa ya da bozuksa {} (bozuksa
    uyari loglanir; Veri sayfasi yeniden secim ister)."""
    yol = ayar_yolu(ortam)
    if not os.path.isfile(yol):
        return {}
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError) as e:
        _log.warning("veri ayari okunamadi, yok sayildi: %s (%s)", yol, e)
        return {}
    if not isinstance(veri, dict):
        _log.warning("veri ayari sozluk degil, yok sayildi: %s", yol)
        return {}
    izinli = YOL_ANAHTARLARI + METIN_ANAHTARLARI
    return {k: v for k, v in veri.items() if k in izinli and isinstance(v, str) and v}


def _dogrula_ayar(degerler: Mapping[str, Optional[str]]) -> None:
    for anahtar, deger in degerler.items():
        if anahtar not in YOL_ANAHTARLARI + METIN_ANAHTARLARI:
            raise ValueError("bilinmeyen veri ayari: %r" % (anahtar,))
        if deger is None:
            continue
        if not isinstance(deger, str):
            raise ValueError("veri ayari metin olmali: %s=%r" % (anahtar, deger))
        if anahtar in YOL_ANAHTARLARI and not os.path.isabs(deger):
            raise ValueError("veri ayari mutlak yol olmali: %s=%r" % (anahtar, deger))


def ayar_yaz(degerler: Mapping[str, Optional[str]], ortam: Ortam = None) -> str:
    """Secimleri mevcut ayarla birlestirip ATOMIK yazar (gecici dosya +
    os.replace); None deger anahtari siler. Doner: ayar dosyasinin yolu.
    Gecersiz anahtar/yol ValueError; yazma hatasi OSError (cagiran gosterir)."""
    _dogrula_ayar(degerler)
    yeni = dict(ayar_oku(ortam))
    for anahtar, deger in degerler.items():
        if deger is None:
            yeni.pop(anahtar, None)
        else:
            yeni[anahtar] = deger
    yol = ayar_yolu(ortam)
    dizin = os.path.dirname(yol)
    os.makedirs(dizin, exist_ok=True)
    fd, gecici = tempfile.mkstemp(prefix=".veri.", suffix=".tmp", dir=dizin)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(dict(yeni, surum=AYAR_SURUMU), f, ensure_ascii=False, indent=1,
                      sort_keys=True)
        os.replace(gecici, yol)
    except BaseException:
        _sil(gecici)
        raise
    return yol


def _sil(yol: str) -> None:
    try:
        os.unlink(yol)
    except FileNotFoundError:
        pass
    except OSError:
        _log.warning("gecici dosya silinemedi: %s", yol, exc_info=True)


# ---------------------------------------------------------------------------
# cozum
# ---------------------------------------------------------------------------

def kok_adaylari(kok: str) -> Tuple[str, ...]:
    """kok/cross_sections.xml ya da kok/*/cross_sections.xml (alfabetik)."""
    dogrudan = os.path.join(kok, XS_DOSYASI)
    if os.path.isfile(dogrudan):
        return (dogrudan,)
    return tuple(y for y in sorted(glob.glob(os.path.join(glob.escape(kok), "*", XS_DOSYASI)))
                 if os.path.isfile(y))


def aday_sec(adaylar) -> Tuple[Optional[str], Tuple[str, ...]]:
    """(secilen | None, adaylar): varsayilan dizin (VIII.0) once; tek aday o;
    birden cok ve hicbiri varsayilan degilse None (kullanici secer)."""
    adaylar = tuple(adaylar)
    for yol in adaylar:
        if os.path.basename(os.path.dirname(yol)) == VARSAYILAN_KUTUPHANE_DIZINI:
            return yol, adaylar
    return (adaylar[0] if len(adaylar) == 1 else None), adaylar


def cross_sections(ortam: Ortam = None) -> Yol:
    """Tesir kesiti kutuphanesinin cross_sections.xml'i (sira: modul belgesi)."""
    o = _ortam(ortam)
    deger = _ortam_degeri(o, XS_DEGISKENI)
    if deger:
        return Yol(deger, "ortam", os.path.isfile(deger))
    ayarli = ayar_oku(o).get("cross_sections")
    if ayarli:
        return Yol(ayarli, "ayar", os.path.isfile(ayarli))
    adaylar = tuple(y for kok in aday_kokleri(o) for y in kok_adaylari(kok))
    if not adaylar:
        return _YOK
    secilen, adaylar = aday_sec(adaylar)
    if secilen is None:
        return Yol(None, "coklu", False, adaylar)
    return Yol(secilen, "aday", True, adaylar)


def _zincir_adaylari(o: Mapping[str, str]):
    xs = cross_sections(o)
    if xs.gecerli:
        ust = os.path.dirname(os.path.dirname(os.path.abspath(xs.deger)))
        yield os.path.join(ust, ZINCIR_DIZINI, VARSAYILAN_ZINCIR)
    for kok in aday_kokleri(o):
        yield os.path.join(kok, ZINCIR_DIZINI, VARSAYILAN_ZINCIR)


def zincir(ortam: Ortam = None) -> Yol:
    """Tukenme zinciri dosyasi (OPENMC_CHAIN_FILE anlami; sira: modul belgesi)."""
    o = _ortam(ortam)
    deger = _ortam_degeri(o, ZINCIR_DEGISKENI)
    if deger:
        return Yol(deger, "ortam", os.path.isfile(deger))
    ayarli = ayar_oku(o).get("zincir")
    if ayarli:
        return Yol(ayarli, "ayar", os.path.isfile(ayarli))
    for yol in _zincir_adaylari(o):
        if os.path.isfile(yol):
            return Yol(yol, "aday", True)
    return _YOK


def zincir_dizini(ortam: Ortam = None) -> str:
    """Zincir dosyalarinin dizini (tukenme termal/hizli/CASL adlarini burada
    arar): cozulen zincirin dizini, yoksa ~/nucdata/chain (v2 davranisi)."""
    o = _ortam(ortam)
    z = zincir(o)
    if z.deger:
        return os.path.dirname(os.path.abspath(z.deger))
    return os.path.join(aday_kokleri(o)[0], ZINCIR_DIZINI)


def veri_hazir_mi(ortam: Ortam = None) -> bool:
    """Kosu icin tesir kesiti kutuphanesi erisilebilir mi (zincir ayrica)."""
    return cross_sections(ortam).gecerli


# ---------------------------------------------------------------------------
# surec ortami
# ---------------------------------------------------------------------------

def _cozulen(o: Mapping[str, str]) -> Dict[str, str]:
    degerler = {}
    for degisken, yol in ((XS_DEGISKENI, cross_sections(o)), (ZINCIR_DEGISKENI, zincir(o))):
        if yol.gecerli and yol.kaynak != "ortam":
            degerler[degisken] = os.path.abspath(yol.deger)
    return degerler


def alt_surec_ortami(ortam: Ortam = None) -> Dict[str, str]:
    """Cozulen veri yollarini iceren YENI ortam sozlugu (subprocess env=).
    Ortamda zaten verilmis degisken degistirilmez; bulunamayan eklenmez."""
    o = _ortam(ortam)
    return dict(o, **_cozulen(o))


def surece_uygula(ortam: Ortam = None,
                  hedef: Optional[MutableMapping[str, str]] = None) -> Dict[str, str]:
    """Cozulen yollari `hedef`e (varsayilan os.environ) yazar; openmc bu
    surecte yukluyse openmc.config de guncellenir (onizleme, kapsul). Doner:
    yazilan {degisken: yol} (yeni sozluk). Bilincli yan etki: bkz. modul belgesi."""
    o = _ortam(ortam)
    hedef = os.environ if hedef is None else hedef
    cozulen = _cozulen(o)
    yazilan = {k: v for k, v in cozulen.items() if not _ayni_yol(hedef.get(k), v)}
    hedef.update(yazilan)
    if hedef is not os.environ:
        return yazilan
    # Onceden bizim yazdigimiz ama artik cozulmeyen deger (secim kaldirildi /
    # dosya silindi) ortamda birakilmaz.
    for degisken in [k for k in _ENJEKTE if k not in cozulen]:
        if _ayni_yol(os.environ.get(degisken), _ENJEKTE.pop(degisken)):
            del os.environ[degisken]
            _openmc_config_sil(degisken)
    _ENJEKTE.update(yazilan)
    if yazilan and "openmc" in sys.modules:
        _openmc_config(yazilan)
    return yazilan


_CONFIG_ANAHTARI = {XS_DEGISKENI: "cross_sections", ZINCIR_DEGISKENI: "chain_file"}


def _openmc_config(yazilan: Mapping[str, str]) -> None:
    import openmc
    for degisken, yol in yazilan.items():
        openmc.config[_CONFIG_ANAHTARI[degisken]] = yol


def _openmc_config_sil(degisken: str) -> None:
    """Kaldirilan degiskenin openmc.config karsiligi (openmc yukluyse)."""
    if "openmc" not in sys.modules:
        return
    import openmc
    anahtar = _CONFIG_ANAHTARI[degisken]
    if anahtar in openmc.config:
        del openmc.config[anahtar]
