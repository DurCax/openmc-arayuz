# -*- coding: utf-8 -*-
"""
================================================================================
 nuklidler.py  --  Tukenme zincirindeki nuklid adlari, gruplar ve hazir setler
================================================================================
 "Izlenen nuklidler" eskiden serbest metindi; "Xe-135" yazan kullanici
 grafikte Xe'yi hic goremiyordu (sonuc okuma bilinmeyen adi sessizce
 atliyordu). Bu modul:

   zincir_nuklidleri(yol)  zincir XML'inden adlar (iterparse; yol + boyut +
                           degisiklik zamanina gore onbellekli). Olculdu
                           (28.09.2026): ENDF/B-VIII.0 3820 nuklid 0.12-0.13 s,
                           CASL 228 nuklid 0.01 s.
   normallestir(ad)        "Xe-135", "xe135", "XE135", "Xe 135", "135Xe" -> "Xe135";
                           "Am242m", "Am-242m" -> "Am242_m1" (OpenMC/GNDS adi).
   oneri(ad, adlar)        zincirdeki en yakin ad (once normallestirme, sonra difflib).
   gruplar / hazir_setler  YALNIZCA verilen zincirde bulunanlar.

 Butun nuklid listeleri (sabitler) bu dosyadadir; "Temel" seti
 sema.VARSAYILAN_TUKENME'deki varsayilandan gelir (tek kaynak).
================================================================================
"""

import difflib
import os
import re
import threading
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from cekirdek.ceviri import N_, _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

# ----------------------------------------------------------------------------
# Sabitler
# ----------------------------------------------------------------------------
# Z = 1..118 (openmc.data.ATOMIC_SYMBOL ile ayni sira; ice aktarmasi agir
# oldugu icin burada tutulur).
ELEMENTLER = (
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni "
    "Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe "
    "Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg "
    "Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg "
    "Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og").split()
_ELEMENT_KUCUK = {e.lower(): e for e in ELEMENTLER}

# Aktinit gruplari: (anahtar, baslik, element)
AKTINIT_GRUPLARI = (
    ("uranyum", N_("Uranyum"), "U"),
    ("neptunyum", N_("Neptünyum"), "Np"),
    ("plutonyum", N_("Plütonyum"), "Pu"),
    ("amerikyum", N_("Amerikyum"), "Am"),
    ("kuriyum", N_("Küriyum"), "Cm"),
)
# Buyuk yutma kesitli fisyon urunleri (reaktivite "zehirleri").
FISYON_ZEHIRLERI = ("Xe135", "Sm149", "Sm151", "Gd155", "Gd157", "Eu155", "Rh103",
                    "Nd143", "Cd113", "Sm150", "Eu153", "Pm147", "Xe131", "Cs133",
                    "Nd145")
# Yanabilir zehirler: Gd ve Er'in dogal izotoplari.
YANABILIR_ZEHIRLER = ("Gd152", "Gd154", "Gd155", "Gd156", "Gd157", "Gd158", "Gd160",
                      "Er162", "Er164", "Er166", "Er167", "Er168", "Er170")
# Uzun omurlu fisyon urunleri (atik yonetimi).
UZUN_OMURLU_FU = ("Tc99", "I129", "Cs135", "Cs137", "Sr90", "Zr93", "Pd107",
                  "Se79", "Sn126")
PU_VEKTORU = ("Pu238", "Pu239", "Pu240", "Pu241", "Pu242")
MINOR_AKTINITLER = ("Np237", "Am241", "Am242_m1", "Am243", "Cm242", "Cm244", "Cm245")
ZEHIR_SETI = ("Xe135", "Sm149", "Sm151", "Gd155", "Gd157", "Eu155", "Rh103", "Nd143")

_ONERI_ESIGI = 0.6          # difflib benzerlik alt siniri


@dataclass(frozen=True)
class Grup:
    """Bir nuklid grubu ya da hazir set; nuklidler zincirdeki sirayla."""
    anahtar: str
    baslik: str
    nuklidler: tuple


class ZincirOkunamadi(ValueError):
    """Zincir dosyasi yok, bos ya da ayristirilamiyor."""


# ----------------------------------------------------------------------------
# Zincir okuma (onbellekli)
# ----------------------------------------------------------------------------
_ONBELLEK = {}
_KILIT = threading.Lock()


def onbellegi_temizle():
    with _KILIT:
        _ONBELLEK.clear()


def zincir_nuklidleri(yol):
    """
    Zincir XML'indeki nuklid adlari (dosyadaki sirayla, tuple).
    Hata: ZincirOkunamadi. Onbellek anahtari (mutlak yol, boyut, mtime).
    """
    try:
        bilgi = os.stat(yol)
    except (OSError, TypeError) as e:
        raise ZincirOkunamadi(_("zincir dosyası okunamadı: %s") % yol) from e
    anahtar = (os.path.abspath(yol), bilgi.st_size, bilgi.st_mtime)
    with _KILIT:
        if anahtar in _ONBELLEK:
            return _ONBELLEK[anahtar]
    adlar = _ayristir(yol)
    with _KILIT:
        _ONBELLEK[anahtar] = adlar
    return adlar


def _ayristir(yol):
    adlar = []
    try:
        for olay, eleman in ET.iterparse(yol, events=("start", "end")):
            if eleman.tag != "nuclide":
                continue
            if olay == "start":
                ad = eleman.get("name")
                if ad:
                    adlar.append(ad)
            else:
                eleman.clear()          # bellek: alt elemanlar tutulmasin
    except (ET.ParseError, OSError) as e:
        raise ZincirOkunamadi(_("zincir dosyası ayrıştırılamadı: %s (%s)") % (yol, e)) from e
    if not adlar:
        raise ZincirOkunamadi(_("zincirde nüklid yok: %s") % yol)
    return tuple(adlar)


# ----------------------------------------------------------------------------
# Ad normallestirme ve oneri
# ----------------------------------------------------------------------------
_KALIP = re.compile(r"^([a-z]{1,2})[\s_-]*(\d{1,3})(?:[\s_-]*m(\d?))?$", re.IGNORECASE)
_TERS_KALIP = re.compile(r"^(\d{1,3})[\s_-]*([a-z]{1,2})(?:[\s_-]*m(\d?))?$", re.IGNORECASE)


def normallestir(ad):
    """OpenMC nuklid adi ("Xe135", "Am242_m1") ya da taninmazsa None."""
    if not isinstance(ad, str):
        return None
    metin = ad.strip()
    if metin.lower().endswith(("_m1", "_m2", "_m3")):
        metin = metin[:-3] + "m" + metin[-1]
    eslesme = _KALIP.match(metin)
    if eslesme:
        sembol, kutle, uyari = eslesme.groups()
    else:
        eslesme = _TERS_KALIP.match(metin)
        if not eslesme:
            return None
        kutle, sembol, uyari = eslesme.groups()
    element = _ELEMENT_KUCUK.get(sembol.lower())
    if element is None or int(kutle) == 0:
        return None
    temel = "%s%d" % (element, int(kutle))
    if uyari is None:
        return temel
    return "%s_m%s" % (temel, uyari or "1")


def _anahtar(ad):
    """Arama ve benzerlik icin: kucuk harf, yalnizca harf ve rakam."""
    return re.sub(r"[^a-z0-9]", "", ad.lower())


def oneri(ad, adlar):
    """Zincirdeki (adlar) en yakin ad; bulunamazsa None."""
    kume = set(adlar)
    normal = normallestir(ad)
    if normal in kume:
        return normal
    if not isinstance(ad, str) or not ad.strip():
        return None
    haritalar = {}
    for a in adlar:
        haritalar.setdefault(_anahtar(a), a)
    yakin = difflib.get_close_matches(_anahtar(normal or ad), list(haritalar), n=1,
                                      cutoff=_ONERI_ESIGI)
    return haritalar[yakin[0]] if yakin else None


def oneri_metni(ad, onerilen):
    """Kullaniciya gosterilen oneri: "Xe-135 → Xe135?"."""
    return "%s → %s?" % (ad, onerilen)


def eksikler(izlenen, adlar):
    """[(ad, oneri|None)]: izlenen icinde zincirde (adlar) olmayanlar, sirayla."""
    kume = set(adlar)
    return [(n, oneri(n, adlar)) for n in izlenen if n not in kume]


def ara(sorgu, adlar):
    """Normallestirmeli arama: "xe-13" -> Xe135, Xe136 ...; bos sorgu -> hepsi."""
    anahtar = _anahtar(sorgu or "")
    if not anahtar:
        return list(adlar)
    bas = [a for a in adlar if _anahtar(a).startswith(anahtar)]
    ic = [a for a in adlar if anahtar in _anahtar(a) and a not in bas]
    return bas + ic


# ----------------------------------------------------------------------------
# Gruplar ve hazir setler
# ----------------------------------------------------------------------------
_ELEMENT_KALIBI = re.compile(r"^([A-Z][a-z]?)\d")


def _element(ad):
    eslesme = _ELEMENT_KALIBI.match(ad)
    return eslesme.group(1) if eslesme else ""


def _zincirde(liste, adlar):
    kume = set(adlar)
    return tuple(n for n in liste if n in kume)


def gruplar(adlar):
    """
    Zincirdeki nuklidlerin gruplari (bos gruplar dahil degil). Son grup
    "diger": hicbir gruba girmeyen kalan nuklidler (arama hepsini bulsun).
    """
    sonuc = []
    for anahtar, baslik, element in AKTINIT_GRUPLARI:
        sonuc.append(Grup(anahtar, _(baslik),
                          tuple(a for a in adlar if _element(a) == element)))
    sonuc.append(Grup("zehirler", _("Fisyon ürünü zehirleri"),
                      _zincirde(FISYON_ZEHIRLERI, adlar)))
    sonuc.append(Grup("yanabilir", _("Yanabilir zehirler (Gd, Er)"),
                      _zincirde(YANABILIR_ZEHIRLER, adlar)))
    sonuc.append(Grup("uzun_omurlu", _("Uzun ömürlü fisyon ürünleri"),
                      _zincirde(UZUN_OMURLU_FU, adlar)))
    gruplu = {n for g in sonuc for n in g.nuklidler}
    sonuc.append(Grup("diger", _("Diğer nüklidler"),
                      tuple(a for a in adlar if a not in gruplu)))
    return [g for g in sonuc if g.nuklidler]


def temel_set():
    """Bugunku varsayilan izlenen liste (sema.VARSAYILAN_TUKENME)."""
    from cekirdek import sema
    return tuple(sema.VARSAYILAN_TUKENME["izlenen"])


def hazir_setler(adlar):
    """Hazir secim setleri; her biri yalnizca zincirde bulunanlari icerir."""
    return [
        Grup("temel", _("Temel"), _zincirde(temel_set(), adlar)),
        Grup("pu", _("Pu vektörü"), _zincirde(PU_VEKTORU, adlar)),
        Grup("zehirler", _("Zehirler"), _zincirde(ZEHIR_SETI, adlar)),
        Grup("minor", _("Minör aktinitler"), _zincirde(MINOR_AKTINITLER, adlar)),
        Grup("atik", _("Atık / uzun ömürlüler"), _zincirde(UZUN_OMURLU_FU, adlar)),
    ]


def zincir_nuklidleri_guvenli(yol):
    """zincir_nuklidleri; okunamazsa None (neden loglanir)."""
    try:
        return zincir_nuklidleri(yol)
    except ZincirOkunamadi as e:
        _log.warning("nüklid listesi okunamadı: %s", e)
        return None
