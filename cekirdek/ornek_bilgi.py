# -*- coding: utf-8 -*-
"""
ornek_bilgi.py -- ornek dosyalarinin galeri bilgisi (meta sozlesmesi).

Ornek JSON'larinin ust duzeyinde istege bagli meta alanlari bulunur
(sema.META_ALANLARI; sema.tamamla bunlari korur, fizige girmez):

    "baslik":      "PWR yakıt hücresi (pin)",          # gorunen ad (Turkce)
    "baslik_en":   "PWR fuel cell (pin)",              # Ingilizce karsiligi
    "aciklama_en": "Classic PWR pin cell ...",         # Ingilizce kisa aciklama
    "kategori":    "pwr",        # KATEGORILER'den biri
    "seviye":      "giris",      # SEVIYELER'den biri
    "referans": {                # yalniz OLCULMUS / yayimlanmis deger varsa
        "k": 1.0000, "sigma": 0.0010,
        "tur": "deney",          # "deney" (C/E) | "hesap" (hesap-hesap)
        "kaynak": "ICSBEP HEU-MET-FAST-001",
        "olcum": {               # bu aracin olcumu (istege bagli)
            "k": 0.99957, "sigma": 0.00054,
            "parcacik": 20000,   # nesil basina parcacik (istege bagli)
            "sure_s": 6.0,       # duvar saati (istege bagli)
            "is_parcacigi": 24,  # (istege bagli)
            "openmc": "0.16.0", "kutuphane": "ENDF/B-VIII.0",
        },
    }

Kullanim (Qt'siz; galeri ve rapor bunu kullanir):

    from cekirdek import ornek_bilgi
    for b in ornek_bilgi.ornek_listesi():
        print(b.dosya, b.baslik, b.kategori, b.seviye)
    sorunlar = ornek_bilgi.dogrula_meta(ham_json_sozlugu)   # [] = temiz

ornek_bilgisi() dosyayi sema.yukle() ile DEGIL ham JSON olarak okur: galeri
acilirken her ornegi tamamlamak gereksiz is olurdu.
"""

import glob
import json
import math
import os
from dataclasses import dataclass
from typing import Optional

from cekirdek import sema
from cekirdek.ceviri import N_
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

ORNEK_DIZINI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "ornekler")

KATEGORILER = ("pwr", "bwr", "vver", "sfr", "arastirma", "kriter", "zirh")
SEVIYELER = ("giris", "orta", "ileri")
REFERANS_TURLERI = ("deney", "hesap")
META_ALANLARI = sema.META_ALANLARI

# Gorunen adlar (yalniz isaret; gosterirken _(...) ile cevrilir)
KATEGORI_ADLARI = {"pwr": "PWR", "bwr": "BWR", "vver": "VVER", "sfr": "SFR",
                   "arastirma": N_("Araştırma"), "kriter": N_("Kriter"), "zirh": N_("Zırh")}
SEVIYE_ADLARI = {"giris": N_("Giriş"), "orta": N_("Orta"), "ileri": N_("İleri")}

_REFERANS_ZORUNLU = ("k", "sigma", "tur", "kaynak")
_REFERANS_ALANLARI = _REFERANS_ZORUNLU + ("olcum",)
_OLCUM_ZORUNLU = ("k", "sigma")
_OLCUM_SAYILAR = ("k", "sigma", "sure_s")
_OLCUM_TAMSAYILAR = ("parcacik", "is_parcacigi")
_OLCUM_METINLER = ("openmc", "kutuphane", "tarih")
_OLCUM_ALANLARI = _OLCUM_SAYILAR + _OLCUM_TAMSAYILAR + _OLCUM_METINLER
_METIN_ALANLARI = ("baslik", "baslik_en", "aciklama_en")


@dataclass(frozen=True)
class Olcum:
    """Bu aracin olcumu (bilinmeyen alan None)."""
    k: float
    sigma: float
    parcacik: Optional[int] = None
    sure_s: Optional[float] = None
    is_parcacigi: Optional[int] = None
    openmc: Optional[str] = None
    kutuphane: Optional[str] = None
    tarih: Optional[str] = None


@dataclass(frozen=True)
class Referans:
    """Yayimlanmis (deney) ya da hesap-hesap referans k degeri."""
    k: float
    sigma: float
    tur: str
    kaynak: str
    olcum: Optional[Olcum] = None


@dataclass(frozen=True)
class OrnekBilgisi:
    """Bir ornek dosyasinin galeri bilgisi. Meta eksikse baslik 'ad'a,
    o da yoksa dosya adina duser; kategori/seviye None kalir."""
    yol: str
    dosya: str                   # "pwr_pinhucre.json"
    ad: str                      # spec "ad"
    baslik: str
    aciklama: str
    kategori: Optional[str]
    seviye: Optional[str]
    kor_turu: Optional[str]      # spec kor.tur (kucuk resim motifi icin)
    demet_turu: Optional[str]    # ilk demetin turu ("kare"/"altigen") ya da None
    baslik_en: Optional[str] = None
    aciklama_en: Optional[str] = None
    referans: Optional[Referans] = None


# ----------------------------------------------------------------------------
# Dogrulama
# ----------------------------------------------------------------------------

def _sayi_mi(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _olcum_sorunlari(olcum):
    if not isinstance(olcum, dict):
        return ["referans.olcum bir sözlük olmalı"]
    sorunlar = ["referans.olcum.%s eksik" % a for a in _OLCUM_ZORUNLU if a not in olcum]
    sorunlar += ["referans.olcum.%s bilinmeyen alan" % a
                 for a in sorted(olcum) if a not in _OLCUM_ALANLARI]
    for a in _OLCUM_SAYILAR:
        if a in olcum and not (_sayi_mi(olcum[a]) and olcum[a] >= 0):
            sorunlar.append("referans.olcum.%s negatif olmayan bir sayı olmalı" % a)
    for a in _OLCUM_TAMSAYILAR:
        v = olcum.get(a)
        if a in olcum and not (isinstance(v, int) and not isinstance(v, bool) and v > 0):
            sorunlar.append("referans.olcum.%s pozitif tamsayı olmalı" % a)
    for a in _OLCUM_METINLER:
        if a in olcum and not (isinstance(olcum[a], str) and olcum[a].strip()):
            sorunlar.append("referans.olcum.%s boş olmayan metin olmalı" % a)
    return sorunlar


def _referans_sorunlari(ref):
    if not isinstance(ref, dict):
        return ["referans bir sözlük olmalı"]
    sorunlar = ["referans.%s eksik" % a for a in _REFERANS_ZORUNLU if a not in ref]
    sorunlar += ["referans.%s bilinmeyen alan" % a
                 for a in sorted(ref) if a not in _REFERANS_ALANLARI]
    if "k" in ref and not (_sayi_mi(ref["k"]) and ref["k"] >= 0):
        sorunlar.append("referans.k negatif olmayan bir sayı olmalı")
    if "sigma" in ref and not (_sayi_mi(ref["sigma"]) and ref["sigma"] >= 0):
        sorunlar.append("referans.sigma negatif olmayan bir sayı olmalı")
    if "tur" in ref and ref["tur"] not in REFERANS_TURLERI:
        sorunlar.append("referans.tur %r geçersiz (geçerli: %s)"
                        % (ref["tur"], ", ".join(REFERANS_TURLERI)))
    if "kaynak" in ref and not (isinstance(ref["kaynak"], str) and ref["kaynak"].strip()):
        sorunlar.append("referans.kaynak boş olmayan metin olmalı")
    if "olcum" in ref:
        sorunlar += _olcum_sorunlari(ref["olcum"])
    return sorunlar


def dogrula_meta(ham):
    """Ornek meta alanlarinin sorunlari (Turkce metin listesi; [] = temiz).
    baslik, kategori ve seviye ZORUNLUDUR; referans ve _en alanlari istege
    baglidir. `ham` ham JSON sozlugudur (sema.yukle ciktisi da olur)."""
    if not isinstance(ham, dict):
        return ["örnek bir JSON nesnesi olmalı"]
    sorunlar = []
    for a in ("baslik", "kategori", "seviye"):
        if a not in ham:
            sorunlar.append("%s eksik" % a)
    for a in _METIN_ALANLARI:
        if a in ham and not (isinstance(ham[a], str) and ham[a].strip()):
            sorunlar.append("%s boş olmayan metin olmalı" % a)
    if "kategori" in ham and ham["kategori"] not in KATEGORILER:
        sorunlar.append("kategori %r geçersiz (geçerli: %s)"
                        % (ham["kategori"], ", ".join(KATEGORILER)))
    if "seviye" in ham and ham["seviye"] not in SEVIYELER:
        sorunlar.append("seviye %r geçersiz (geçerli: %s)"
                        % (ham["seviye"], ", ".join(SEVIYELER)))
    if "referans" in ham:
        sorunlar += _referans_sorunlari(ham["referans"])
    return sorunlar


# ----------------------------------------------------------------------------
# Okuma
# ----------------------------------------------------------------------------

def _referans(ham_ref):
    if not isinstance(ham_ref, dict) or _referans_sorunlari(ham_ref):
        return None
    olcum = ham_ref.get("olcum")
    return Referans(k=float(ham_ref["k"]), sigma=float(ham_ref["sigma"]),
                    tur=ham_ref["tur"], kaynak=ham_ref["kaynak"],
                    olcum=Olcum(**olcum) if olcum is not None else None)


def _secenek(ham, alan, gecerli):
    deger = ham.get(alan)
    return deger if deger in gecerli else None


def bilgi_olustur(ham, yol):
    """Ham JSON sozlugunden OrnekBilgisi (dosya okumaz). Gecersiz meta alani
    None'a duser ve loglanir (dogrula_meta ayrintiyi verir)."""
    sorunlar = dogrula_meta(ham)
    if sorunlar:
        _log.warning("örnek meta sorunlu (%s): %s", yol, "; ".join(sorunlar))
    dosya = os.path.basename(yol)
    ad = ham.get("ad") if isinstance(ham.get("ad"), str) else ""
    baslik = ham.get("baslik") if isinstance(ham.get("baslik"), str) else ""
    kor = ham.get("kor") if isinstance(ham.get("kor"), dict) else {}
    demetler = ham.get("demetler") if isinstance(ham.get("demetler"), list) else []
    ilk_demet = demetler[0] if demetler and isinstance(demetler[0], dict) else {}
    return OrnekBilgisi(
        yol=yol, dosya=dosya, ad=ad,
        baslik=baslik.strip() or ad or os.path.splitext(dosya)[0],
        aciklama=ham.get("aciklama") if isinstance(ham.get("aciklama"), str) else "",
        kategori=_secenek(ham, "kategori", KATEGORILER),
        seviye=_secenek(ham, "seviye", SEVIYELER),
        kor_turu=kor.get("tur"), demet_turu=ilk_demet.get("tur"),
        baslik_en=ham.get("baslik_en") if isinstance(ham.get("baslik_en"), str) else None,
        aciklama_en=ham.get("aciklama_en") if isinstance(ham.get("aciklama_en"), str) else None,
        referans=_referans(ham.get("referans")))


def ornek_bilgisi(yol):
    """Ornek dosyasinin OrnekBilgisi'si (ham JSON hizli okuma; tamamla YOK).
    Dosya okunamazsa OSError, JSON bozuksa ValueError (json.JSONDecodeError)."""
    with open(yol, encoding="utf-8") as f:
        ham = json.load(f)
    if not isinstance(ham, dict):
        raise ValueError("%s: örnek bir JSON nesnesi değil" % yol)
    return bilgi_olustur(ham, yol)


def _sira(bilgi):
    kat = KATEGORILER.index(bilgi.kategori) if bilgi.kategori else len(KATEGORILER)
    sev = SEVIYELER.index(bilgi.seviye) if bilgi.seviye else len(SEVIYELER)
    return (kat, sev, bilgi.dosya)


def ornek_listesi(dizin=ORNEK_DIZINI):
    """Dizindeki butun *.json orneklerinin OrnekBilgisi'leri (kategori, seviye,
    dosya adi sirasiyla). Okunamayan dosya loglanip atlanir (galeriyi bozmaz)."""
    bilgiler = []
    for yol in sorted(glob.glob(os.path.join(dizin, "*.json"))):
        try:
            bilgiler.append(ornek_bilgisi(yol))
        except (OSError, ValueError):
            _log.exception("örnek okunamadı, galeride gösterilmiyor: %s", yol)
    return tuple(sorted(bilgiler, key=_sira))


def kategori_sayilari(bilgiler):
    """{kategori: adet} -- galeri filtresinin sayaclari (None = kategorisiz)."""
    sayilar = {}
    for b in bilgiler:
        sayilar[b.kategori] = sayilar.get(b.kategori, 0) + 1
    return sayilar
