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
# Buyuk yutma kesitli fisyon urunleri (reaktivite "zehirleri"). Termal
# kesitler ENDF/B-VIII.0, 0.0253 eV:
#   Xe135 2.6e6 b, Sm149 4.0e4 b, Gd155/157 6.1e4 / 2.5e5 b, Sm151 1.5e4 b,
#   Eu155 3.8e3 b, Rh103 145 b, Ag109 91 b (ve Ag110_m1 uretir),
#   Pm148_m1 ~1e4 b (Pm147 (n,g) kolu; Sm149 verimini belirler),
#   Sm152 206 b, Cd113 2.0e4 b, Nd143 325 b, Nd145 42 b, Cs133 29 b,
#   Mo95 13.4 b, Ru101 5.2 b, Xe131 85 b, Pm147 168 b, Sm150 100 b, Eu153 359 b.
# Mo95/Ru101 yalniz yuksek verimleri (her biri ~%6) yuzunden anlamlidir.
FISYON_ZEHIRLERI = ("Xe135", "Sm149", "Sm151", "Gd155", "Gd157", "Eu155", "Rh103",
                    "Ag109", "Pm148", "Pm148_m1", "Nd143", "Cd113", "Sm150", "Sm152",
                    "Eu153", "Pm147", "Xe131", "Cs133", "Nd145", "Mo95", "Ru101")
# Xe/Sm dinamigi: ONCULLERIYLE birlikte. I135 (6.6 sa) -> Xe135 (9.2 sa) ilk
# gunlerin birkac bin pcm'lik dususunu ve kapanistan sonraki "Xe cukurunu",
# Pm149 (53 sa) -> Sm149 (kararli) ise kalici zehirlenmeyi belirler.
XE_SM_ZINCIRI = ("I135", "Xe135", "Pm149", "Sm149")
# Yanma gostergeleri: yakit yanmasini OLCEN nuklidler.
#   Nd148  -- klasik yanma monitoru (ASTM E321): verimi ~%1.7, sabit ve
#             kesiti kucuk; atom sayisi fisyon sayisiyla dogru orantili.
#   Cs137  -- 30.1 y, gama ile olculur; yanma ile dogrusal.
#   Cs134  -- Cs133'un (n,g) urunu: yanmanin KARESIYLE artar; Cs134/Cs137
#             orani harcanmis yakit dogrulamasinda (NDA) kullanilir.
YANMA_GOSTERGELERI = ("Nd148", "Cs134", "Cs137")
# Yanabilir zehirler: Gd ve Er'in dogal izotoplari.
YANABILIR_ZEHIRLER = ("Gd152", "Gd154", "Gd155", "Gd156", "Gd157", "Gd158", "Gd160",
                      "Er162", "Er164", "Er166", "Er167", "Er168", "Er170")
# Klasik 7 uzun omurlu fisyon urunu (LLFP; yarilanma omru >= 2e5 y, atik
# yonetiminde ayirma/donusturme adaylari).
LLFP = ("Se79", "Zr93", "Tc99", "Pd107", "Sn126", "I129", "Cs135")
# Orta omurlu, ISI ve gama kaynagi ikili (~30 y): depolamanin ilk 300 yilini
# bunlar belirler.
ORTA_OMURLU_FU = ("Cs137", "Sr90")
# "Atik / isi" ust grubu: ikisinin birlesimi (eski ad UZUN_OMURLU_FU korunur).
UZUN_OMURLU_FU = LLFP + ORTA_OMURLU_FU
# Th/Pa yakit cevrimi: Th232 (n,g) -> Th233 -> Pa233 (27 g) -> U233.
# Pa233 ara urun olarak notron yutar (yanma sirasinda U233 uretimini
# geciktirir); U232 (ve onculleri Th230/Pa231) sert gama yayan kirliliktir.
TORYUM_ZINCIRI = ("Th230", "Th232", "Th233", "Pa231", "Pa233", "U232", "U233", "U234")
# Agacta gosterilen Th/Pa grubu: U izotoplari zaten "Uranyum" grubundadir;
# element suzgeci butun Th209-Th238'i getirecegi icin liste secilmistir.
TORYUM_ZINCIRI_GRUBU = ("Th228", "Th229", "Th230", "Th232", "Th233",
                        "Pa231", "Pa232", "Pa233")
PU_VEKTORU = ("Pu238", "Pu239", "Pu240", "Pu241", "Pu242")
MINOR_AKTINITLER = ("Np237", "Am241", "Am242_m1", "Am243", "Cm242", "Cm243",
                    "Cm244", "Cm245", "Cm246")
ZEHIR_SETI = ("I135", "Xe135", "Pm149", "Sm149", "Sm151", "Gd155", "Gd157", "Eu155",
              "Rh103", "Nd143")
# Hizli spektrum temel seti: termal zehirler (Xe135, Sm149) hizli spektrumda
# reaktiviteyi belirlemez; onem sirasi uretim/tuketim (U238 -> Pu239), minor
# aktinit birikimi (isi ve notron kaynagi: Cm244) ve yuksek verimli, hizli
# spektrumda da yutan fisyon urunleridir.
HIZLI_SETI = ("U234", "U235", "U238", "Np237", "Pu238", "Pu239", "Pu240", "Pu241",
              "Pu242", "Am241", "Am242_m1", "Am243", "Cm242", "Cm244", "Zr93",
              "Mo95", "Tc99", "Ru101", "Rh103", "Cs133", "Nd143")

_ONERI_ESIGI = 0.6          # difflib benzerlik alt siniri


@dataclass(frozen=True)
class Grup:
    """
    Bir nuklid grubu ya da hazir set; nuklidler zincirdeki sirayla.
    altgruplar: ayni grubun ayrilmis alt kumeleri (ornek "Atik / isi" ->
    klasik 7 LLFP ve orta omurlu Cs137/Sr90). Ust grubun nuklidleri
    altgruplarin hepsini icerir; bos altgrup listelenmez.
    """
    anahtar: str
    baslik: str
    nuklidler: tuple
    altgruplar: tuple = ()


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


def _atik_grubu(adlar):
    """"Atik / isi": klasik 7 LLFP ile orta omurlu Cs137/Sr90 AYRI alt gruplar."""
    alt = [Grup("llfp", _("Uzun ömürlü (7 LLFP)"), _zincirde(LLFP, adlar)),
           Grup("orta_omurlu", _("Orta ömürlü ısı kaynağı (Cs137, Sr90)"),
                _zincirde(ORTA_OMURLU_FU, adlar))]
    alt = tuple(g for g in alt if g.nuklidler)
    return Grup("uzun_omurlu", _("Atık / ısı"), _zincirde(UZUN_OMURLU_FU, adlar), alt)


def gruplar(adlar):
    """
    Zincirdeki nuklidlerin gruplari (bos gruplar dahil degil). Son grup
    "diger": hicbir gruba girmeyen kalan nuklidler (arama hepsini bulsun).
    Bir nuklid birden cok grupta olabilir (ornek Xe135: hem zehir hem
    Xe/Sm zinciri); secici ayni adin butun ogelerini birlikte isaretler.
    """
    sonuc = []
    for anahtar, baslik, element in AKTINIT_GRUPLARI:
        sonuc.append(Grup(anahtar, _(baslik),
                          tuple(a for a in adlar if _element(a) == element)))
    sonuc.append(Grup("toryum", _("Toryum çevrimi (Th, Pa)"),
                      _zincirde(TORYUM_ZINCIRI_GRUBU, adlar)))
    sonuc.append(Grup("xe_sm", _("Xe/Sm dinamiği (öncülleriyle)"),
                      _zincirde(XE_SM_ZINCIRI, adlar)))
    sonuc.append(Grup("zehirler", _("Fisyon ürünü zehirleri"),
                      _zincirde(FISYON_ZEHIRLERI, adlar)))
    sonuc.append(Grup("yanabilir", _("Yanabilir zehirler (Gd, Er)"),
                      _zincirde(YANABILIR_ZEHIRLER, adlar)))
    sonuc.append(Grup("yanma", _("Yanma göstergeleri"),
                      _zincirde(YANMA_GOSTERGELERI, adlar)))
    sonuc.append(_atik_grubu(adlar))
    gruplu = {n for g in sonuc for n in g.nuklidler}
    sonuc.append(Grup("diger", _("Diğer nüklidler"),
                      tuple(a for a in adlar if a not in gruplu)))
    return [g for g in sonuc if g.nuklidler]


def temel_set():
    """Bugunku varsayilan izlenen liste (sema.VARSAYILAN_TUKENME)."""
    from cekirdek import sema
    return tuple(sema.VARSAYILAN_TUKENME["izlenen"])


def hazir_setler(adlar):
    """
    Hazir secim setleri (DONUK: bu bes anahtar ve sirasi degismez; secici
    dugmeleri ve eski testler buna baglidir). Her biri yalnizca zincirde
    bulunanlari icerir. Yeni setler icin bkz. tum_setler().
    """
    return [
        Grup("temel", _("Temel"), _zincirde(temel_set(), adlar)),
        Grup("pu", _("Pu vektörü"), _zincirde(PU_VEKTORU, adlar)),
        Grup("zehirler", _("Zehirler"), _zincirde(ZEHIR_SETI, adlar)),
        Grup("minor", _("Minör aktinitler"), _zincirde(MINOR_AKTINITLER, adlar)),
        Grup("atik", _("Atık / ısı"), _zincirde(UZUN_OMURLU_FU, adlar)),
    ]


def tum_setler(adlar):
    """hazir_setler + Dalga 2 setleri (yanma göstergesi, Th çevrimi, hızlı)."""
    return hazir_setler(adlar) + [
        Grup("yanma", _("Yanma göstergesi"), _zincirde(YANMA_GOSTERGELERI, adlar)),
        Grup("toryum", _("Th çevrimi"), _zincirde(TORYUM_ZINCIRI, adlar)),
        Grup("hizli", _("Hızlı spektrum"), _zincirde(HIZLI_SETI, adlar)),
    ]


# {anahtar: nuklid listesi} -- cozulme denetimi ve arayuz ipuclari icin.
SABIT_LISTELER = {
    "zehirler": FISYON_ZEHIRLERI, "xe_sm": XE_SM_ZINCIRI,
    "yanma": YANMA_GOSTERGELERI, "yanabilir": YANABILIR_ZEHIRLER,
    "llfp": LLFP, "orta_omurlu": ORTA_OMURLU_FU, "toryum_grubu": TORYUM_ZINCIRI_GRUBU,
    "toryum": TORYUM_ZINCIRI, "pu": PU_VEKTORU, "minor": MINOR_AKTINITLER,
    "zehir_seti": ZEHIR_SETI, "hizli": HIZLI_SETI,
}


def tum_sabit_adlar():
    """Butun sabit listelerdeki nuklid adlari (tekrarsiz, sirali)."""
    return tuple(sorted({n for liste in SABIT_LISTELER.values() for n in liste}))


def cozulmeyenler(adlar):
    """
    {liste anahtari: verilen zincirde BULUNMAYAN adlar}. Bos listeler yoktur;
    hepsi cozuluyorsa {} doner. Kabul olcutu: pwr_tukenme zincirinde {}.
    """
    kume = set(adlar)
    eksik = {}
    for anahtar, liste in SABIT_LISTELER.items():
        yok = tuple(n for n in liste if n not in kume)
        if yok:
            eksik[anahtar] = yok
    return eksik


def zincir_nuklidleri_guvenli(yol):
    """zincir_nuklidleri; okunamazsa None (neden loglanir)."""
    try:
        return zincir_nuklidleri(yol)
    except ZincirOkunamadi as e:
        _log.warning("nüklid listesi okunamadı: %s", e)
        return None
