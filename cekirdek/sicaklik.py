# -*- coding: utf-8 -*-
"""
================================================================================
 sicaklik.py  --  Y7: sicaklik isleme (yontem, tolerans, multipole, aralik)
================================================================================
 Ayar: spec["ayarlar"]["sicaklik_yontemi"]  (mevcut alan: nearest | interpolation)
       spec["ayarlar"]["sicaklik"] = {"tolerans": K, "multipole": bool,
                                      "aralik": [T_min, T_max], "varsayilan": K}
 Alanlar yoksa OpenMC varsayilani gecerlidir ve Settings'e YAZILMAZ (eski
 dosyalar ayni modeli kurar; sema.VARSAYILAN_AYARLAR'a eklenmedi).

 OPENMC 0.16 KURALI (src/nuclide.cpp Nuclide::Nuclide, src/thermal.cpp)
   Kutuphane sicakliklari kT/k_B'nin TAMSAYIYA yuvarlanmisidir (293.6 -> 294).
   nearest        : en yakin T_k; |T_k - T| < tolerans (kati) degilse koşu
                    "does not contain cross sections ... at or near" ile durur.
   interpolation  : T_j <= T < T_j+1 olan cift yuklenir; carpismada iki
                    sicaklik arasinda kT'ye gore STOKASTIK secim (lineer
                    agirlik). Disarida: |T - uc| <= tolerans ise uca yapisir,
                    degilse durur. Tek sicaklikli veride nearest'e doner.
   S(a,b) tablolari ayni kurala uyar (thermal.cpp).
   Varsayilanlar (src/settings.cpp): yontem nearest, tolerans 10 K,
   varsayilan sicaklik 293.6 K, multipole kapali.
   range: araliktaki TUM kutuphane sicakliklari yuklenir (geri beslemeli
   hesaplarda); secim kurali degismez.
   multipole: cozulmus rezonans bolgesinde windowed multipole (WMP) ile
   herhangi bir sicaklikta Doppler genislemesi. Veri cross_sections.xml'de
   type="wmp" kaydidir; hic yoksa OpenMC yalniz UYARIR (cross_sections.cpp)
   ve noktasal veriye doner -- bu durumda yukaridaki kural yine gecerlidir.
================================================================================
"""

import math
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici, uyar_bir_kez

_log = kaydedici(__name__)

YONTEMLER = ("nearest", "interpolation")
VARSAYILAN_YONTEM = "nearest"        # OpenMC src/settings.cpp
VARSAYILAN_TOLERANS = 10.0           # K, src/settings.cpp temperature_tolerance
VARSAYILAN_SICAKLIK = 293.6          # K, src/settings.cpp temperature_default
K_BOLTZMANN_EV = 8.617333262e-5      # eV/K, CODATA 2018 (openmc.data.K_BOLTZMANN)
TAM_ESIK = 0.5                       # K: OpenMC tamsayiya yuvarlar; daha yakini "tam"


@dataclass(frozen=True)
class SicaklikAyari:
    yontem: str
    tolerans: float
    multipole: bool
    aralik: Optional[Tuple[float, float]]
    varsayilan: float


@dataclass(frozen=True)
class Karar:
    """durum: tam | yakin (nearest, baska sicaklik) | ara (interpolasyon) |
    kenar (uca yapisir) | yok (OpenMC durur). kullanilan: yuklenen T [K]."""
    durum: str
    kullanilan: Tuple[int, ...]


# ----------------------------------------------------------------------------
# ayar
# ----------------------------------------------------------------------------

def _ham(spec: dict) -> dict:
    ham = ((spec or {}).get("ayarlar") or {}).get("sicaklik")
    return ham if isinstance(ham, dict) else {}


def _sayi(deger, ad: str) -> float:
    try:
        x = float(deger)
    except (TypeError, ValueError):
        raise ValueError(_("%s sayı olmalı: %r") % (ad, deger)) from None
    if not math.isfinite(x):
        raise ValueError(_("%s sonlu olmalı: %r") % (ad, deger))
    return x


def _aralik(deger) -> Optional[Tuple[float, float]]:
    if deger is None:
        return None
    if not isinstance(deger, (list, tuple)) or len(deger) != 2:
        raise ValueError(_("sıcaklık aralığı iki sayı olmalı: %r") % (deger,))
    alt, ust = (_sayi(x, _("sıcaklık aralığı")) for x in deger)
    if not 0.0 <= alt < ust:
        raise ValueError(_("sıcaklık aralığı 0 ≤ alt < üst olmalı: %g – %g") % (alt, ust))
    return (alt, ust)


def ayar(spec: dict) -> SicaklikAyari:
    """Dogrulanmis SicaklikAyari; gecersiz deger ValueError."""
    a = (spec or {}).get("ayarlar") or {}
    yontem = a.get("sicaklik_yontemi") or VARSAYILAN_YONTEM
    if yontem not in YONTEMLER:
        raise ValueError(_("bilinmeyen sıcaklık yöntemi: %s (geçerli: %s)")
                         % (yontem, ", ".join(YONTEMLER)))
    ham = _ham(spec)
    tolerans = _sayi(ham.get("tolerans", VARSAYILAN_TOLERANS), _("sıcaklık toleransı"))
    if tolerans < 0:
        raise ValueError(_("sıcaklık toleransı negatif olamaz: %g") % tolerans)
    varsayilan = _sayi(ham.get("varsayilan", VARSAYILAN_SICAKLIK), _("varsayılan sıcaklık"))
    if varsayilan <= 0:
        raise ValueError(_("varsayılan sıcaklık pozitif olmalı: %g K") % varsayilan)
    return SicaklikAyari(yontem, tolerans, bool(ham.get("multipole", False)),
                         _aralik(ham.get("aralik")), varsayilan)


def settings_sozlugu(spec: dict) -> Dict[str, object]:
    """openmc.Settings.temperature sozlugu: yalniz dosyada ACIKCA verilen
    alanlar (yontem eski kurucu gibi: alan varsa)."""
    a = ayar(spec)
    ham = _ham(spec)
    d: Dict[str, object] = {}
    if ((spec or {}).get("ayarlar") or {}).get("sicaklik_yontemi"):
        d["method"] = a.yontem
    if "tolerans" in ham:
        d["tolerance"] = a.tolerans
    if "multipole" in ham:
        d["multipole"] = a.multipole
    if a.aralik is not None:
        d["range"] = a.aralik
    if "varsayilan" in ham:
        d["default"] = a.varsayilan
    return d


def uygula(settings: "openmc.Settings", spec: dict) -> None:
    """kurucu.ayarlari_kur kancasi: sozluk bos degilse temperature atanir."""
    d = settings_sozlugu(spec)
    if d:
        settings.temperature = d


def betik_satirlari(spec: dict) -> List[str]:
    """uygula() ile ayni ayar; yalniz yontem disi alan varsa yazilir
    (yontem satirini bolumler._ayarlar zaten yazar)."""
    d = settings_sozlugu(spec)
    if set(d) <= {"method"}:
        return []
    return ["ayar.temperature = %r   # Y7: yöntem, tolerans [K], multipole, aralık, varsayılan"
            % (d,)]


# ----------------------------------------------------------------------------
# OpenMC secim kurali (saf)
# ----------------------------------------------------------------------------

def _tam_mi(t: float, mevcut: Sequence[float]) -> bool:
    return any(abs(t - m) < TAM_ESIK for m in mevcut)


def _en_yakin(t: float, mevcut: Sequence[float], tolerans: float, tam: bool) -> Karar:
    tamsayi = sorted({int(round(m)) for m in mevcut})
    gercek = min(tamsayi, key=lambda m: abs(m - t))
    if abs(gercek - t) < tolerans:
        return Karar("tam" if tam else "yakin", (gercek,))
    return Karar("yok", ())


def degerlendir(t: float, mevcut: Sequence[float], yontem: str, tolerans: float) -> Karar:
    """OpenMC 0.16'nin T sicakligi icin hangi kutuphane sicakliklarini
    yukleyecegi (modul belgesi). mevcut: gercek sicakliklar [K], bos olamaz."""
    if not mevcut:
        raise ValueError(_("kütüphane sıcaklık listesi boş"))
    tam = _tam_mi(t, mevcut)
    tamsayi = sorted({int(round(m)) for m in mevcut})
    if yontem == "nearest" or len(tamsayi) == 1:
        return _en_yakin(t, mevcut, tolerans, tam)
    for alt, ust in zip(tamsayi, tamsayi[1:]):
        if alt <= t < ust:
            return Karar("tam" if tam else "ara", (alt, ust))
    for uc in (tamsayi[0], tamsayi[-1]):
        if abs(t - uc) <= tolerans:
            return Karar("tam" if tam else "kenar", (uc,))
    return Karar("yok", ())


# ----------------------------------------------------------------------------
# kutuphane
# ----------------------------------------------------------------------------

def _kutuphane_yolu(yol: Optional[str]) -> Optional[str]:
    yol = yol if yol is not None else os.environ.get("OPENMC_CROSS_SECTIONS")
    return yol if yol and os.path.exists(yol) else None


def _kayitlar(yol: Optional[str]) -> Optional[Dict[Tuple[str, str], str]]:
    """{(tur, ad): mutlak h5 yolu}; okunamazsa None (loglanir)."""
    yol = _kutuphane_yolu(yol)
    if yol is None:
        return None
    try:
        kok = ET.parse(yol).getroot()
    except (ET.ParseError, OSError):
        uyar_bir_kez(_log, "cross_sections.xml okunamadi: %s", yol)
        return None
    taban = os.path.dirname(yol)
    harita = {}
    for lib in kok.findall("library"):
        for ad in (lib.get("materials") or "").split():
            harita[(lib.get("type"), ad)] = os.path.join(taban, lib.get("path", ""))
    return harita


def wmp_nuklidleri(yol: Optional[str] = None) -> Optional[FrozenSet[str]]:
    """type="wmp" kaydi olan nuklidler; kutuphane okunamazsa None."""
    harita = _kayitlar(yol)
    if harita is None:
        return None
    return frozenset(ad for tur, ad in harita if tur == "wmp")


_SICAKLIK_ONBELLEK: Dict[Tuple[str, str], Optional[Tuple[float, ...]]] = {}


def _h5_sicakliklari(dosya: str, ad: str) -> Optional[Tuple[float, ...]]:
    try:
        import h5py
    except ImportError:
        _log.warning("h5py yok: kütüphane sıcaklıkları okunamaz")
        return None
    if not os.path.exists(dosya):
        return None
    try:
        with h5py.File(dosya, "r") as f:
            if ad not in f or "kTs" not in f[ad]:
                return None
            kt = [float(d[()]) for d in f[ad]["kTs"].values()]
    except (OSError, KeyError, ValueError):
        uyar_bir_kez(_log, "HDF5 sicakliklari okunamadi: %s (%s)", dosya, ad)
        return None
    return tuple(sorted(k / K_BOLTZMANN_EV for k in kt if k > 0)) or None


def kutuphane_sicakliklari(tur: str, ad: str,
                           yol: Optional[str] = None) -> Optional[Tuple[float, ...]]:
    """Notron ("neutron") ya da S(a,b) ("thermal") verisinin sicakliklari
    [K, kT/k_B, artan]; bulunamazsa None. Surec omru boyunca onbellekli."""
    anahtar = (tur, ad)
    if yol is None and anahtar in _SICAKLIK_ONBELLEK:
        return _SICAKLIK_ONBELLEK[anahtar]
    harita = _kayitlar(yol) or {}
    dosya = harita.get(anahtar)
    sonuc = _h5_sicakliklari(dosya, ad) if dosya else None
    if yol is None:
        _SICAKLIK_ONBELLEK[anahtar] = sonuc
    return sonuc


@dataclass(frozen=True)
class MalzemeSicakligi:
    malzeme: str
    tur: str          # neutron | thermal
    ad: str
    sicaklik: float
    karar: Karar
    mevcut: Tuple[float, ...]


def model_degerlendirmesi(spec: dict, yol: Optional[str] = None) -> List[MalzemeSicakligi]:
    """Her malzemenin her nuklidi ve S(a,b) tablosu icin OpenMC karari.
    Verisi okunamayan bilesen atlanir (nuklid denetimi ayrica raporlar)."""
    from cekirdek import kurucu
    a = ayar(spec)
    nesneler, _m, _r = kurucu.malzemeleri_kur(spec)
    sonuc = []
    for m in spec.get("malzemeler") or []:
        t = float(m.get("sicaklik") or a.varsayilan)
        bilesenler = [("neutron", n) for n in nesneler[m["ad"]].get_nuclides()]
        bilesenler += [("thermal", s) for s in m.get("sab") or []]
        for tur, ad in bilesenler:
            mevcut = kutuphane_sicakliklari(tur, ad, yol)
            if not mevcut:
                continue
            sonuc.append(MalzemeSicakligi(m["ad"], tur, ad, t,
                                          degerlendir(t, mevcut, a.yontem, a.tolerans),
                                          mevcut))
    return sonuc
