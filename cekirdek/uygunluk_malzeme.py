# -*- coding: utf-8 -*-
"""
uygunluk_malzeme.py -- malzeme rolleri (yakit, sogutucu, moderator, emici,
yapisal, gaz) ve bilesim yardimcilari

cekirdek/uygunluk.py'den YALNIZ TASINDI (v3 T2, dosya boyu): "yardimcilar:
bilesim" ve "malzeme rolleri" bolumleri ile esik sabitleri. Davranis aynidir;
adlar uygunluk'tan da erisilir (uygunluk.malzeme_rolleri, uygunluk.ROLLER ...).
"""

import re

from cekirdek.gunluk import kaydedici, uyar_bir_kez

# Kaydedici adi tasimadan once neyse o: log satirlari ve uyar_bir_kez ayni kalir.
_log = kaydedici("cekirdek.uygunluk")


ROLLER = ("yakit", "sogutucu", "moderator", "emici", "yapisal", "gaz")

# Guclu notron sogurucu elementler (kontrol cubugu, tambur, yanabilir zehir).
_EMICI_ELEMENTLER = {"B", "Gd", "Ag", "In", "Cd", "Hf", "Er", "Eu", "Dy", "Sm"}
# Emici sayilmak icin, hafif baglayicilar (H, C, N, O) disindaki atomlarin en
# az bu kesri sogurucu olmali. B4C, Gd2O3, AgInCd, Hf, Dy2TiO5 (%67), borlu
# celik (%2 B -> ~%9) emici; eser Hf'li zirkaloy (1e-4) ve eser B'li celik
# yapisal kalir.
_EMICI_ESIGI = 0.05
# Bu atom kesrinin altindaki bilesenler "eser" (safsizlik) sayilir ve
# kimyasal aile kurallarina (su mu, grafit mi...) girmez: 1 ppm B'li grafit
# yine grafittir. Borlu sudaki bor (2000 ppm -> ~1e-3) da eserdir.
_ESER_ESIGI = 0.005
_GAZ_YOGUNLUK_ESIGI = 0.01      # g/cm3 altinda gaz sayilir
_AVOGADRO_BARN = 0.602214076    # N_A * 1e-24  (atom/b-cm <-> mol/cm3)


# ----------------------------------------------------------------------------
# yardimcilar: bilesim
# ----------------------------------------------------------------------------

def _eleman(b):
    """Bilesim satirindan element sembolu: "U235" -> "U", "Am242_m1" -> "Am"."""
    isim = b.get("isim") or ""
    if b.get("tur") != "nuklid":
        return isim
    m = re.match(r"[A-Z][a-z]?", isim)
    return m.group(0) if m else isim


def _z(sembol):
    import openmc.data
    return openmc.data.ATOMIC_NUMBER.get(sembol, 0)


def _kutle(b):
    """Bilesim satirinin atom kutlesi [u] (agirlik -> atom orani donusumu icin)."""
    import openmc.data
    isim = b.get("isim") or ""
    try:
        if b.get("tur") == "nuklid":
            try:
                return float(openmc.data.atomic_mass(isim))
            except Exception:
                return float(openmc.data.zam(isim)[1])
        return float(openmc.data.atomic_weight(isim))
    except Exception:
        # bilinmeyen ad: dogrula ayrica bulgu verir; burada kutle 0 sayilir
        uyar_bir_kez(_log, "atom kutlesi bilinmiyor: %r", isim)
        return 0.0


def _atom_kesirleri(m):
    """
    {element: atom kesri}. "wo" satirlari atom kutlesine bolunerek atom
    oranina cevrilir. Yaklasiktir (rol siniflamasi icin yeterli).
    """
    toplam = {}
    for b in m.get("bilesim") or []:
        if not b.get("isim"):
            continue
        try:
            miktar = float(b.get("miktar") or 0.0)
        except (TypeError, ValueError):   # sayi olmayan miktar: dogrula bulgu verir
            continue
        if miktar <= 0:
            continue
        if (b.get("birim") or "ao") == "wo":
            A = _kutle(b)
            if A > 0:
                miktar /= A
        e = _eleman(b)
        toplam[e] = toplam.get(e, 0.0) + miktar
    s = sum(toplam.values())
    return {e: v / s for e, v in toplam.items()} if s > 0 else {}


def _ortalama_kutle(m):
    """Atom kesirleriyle agirliklanmis ortalama atom kutlesi [u]; bilinmiyorsa 0."""
    import openmc.data
    kes = _atom_kesirleri(m)
    A = 0.0
    for e, f in kes.items():
        try:
            A += f * float(openmc.data.atomic_weight(e))
        except Exception:
            uyar_bir_kez(_log, "ortalama atom kutlesi: element %r bilinmiyor", e)
            return 0.0
    return A


def _yogunluk_gcm3(m):
    """Malzeme yogunlugu g/cm3 cinsinden; cevrilemiyorsa None."""
    y = m.get("yogunluk") or {}
    try:
        deger = float(y.get("deger") or 0.0)
    except (TypeError, ValueError):       # sayi olmayan yogunluk: dogrula bulgu verir
        return None
    birim = y.get("birim") or "g/cm3"
    if birim in ("g/cm3", "g/cc"):
        return deger
    if birim == "kg/m3":
        return deger / 1000.0
    if birim in ("atom/b-cm", "atom/cm3"):
        A = _ortalama_kutle(m)
        if A <= 0:
            return None
        n = deger if birim == "atom/b-cm" else deger * 1.0e-24
        return n * A / _AVOGADRO_BARN
    return None


def _doteryumlu(m):
    """
    Hidrojenin ANLAMLI kesri doteryum mu (H2 / D)? Agir su hafif su degildir.
    Dogal bolluktaki eser H2 (%0.016; BEAVRS gibi nuklid listeli hafif su) agir
    su SAYILMAZ: hidrojenin doteryum kesri _ESER_ESIGI'nin altindaysa False.
    """
    doteryum = hafif = 0.0
    for b in m.get("bilesim") or []:
        isim = b.get("isim") or ""
        miktar = abs(float(b.get("miktar") or 0.0))
        if isim in ("H2", "D"):
            doteryum += miktar
        elif isim in ("H", "H1"):
            hafif += miktar
    toplam = doteryum + hafif
    return toplam > 0.0 and doteryum / toplam >= _ESER_ESIGI


def _korelasyon(m):
    """
    tarama.py'nin sicakliga bagli yogunluk korelasyonu (fonksiyon ya da None).
    Kimya burada TEKRAR YAZILMAZ: sogutucu sicakligi taramasinin gercekte ne
    yapacagini tarama._yogunluk_korelasyonu belirler.
    """
    from cekirdek import tarama
    try:
        fonk, _aciklama = tarama._yogunluk_korelasyonu(m)
    except Exception:
        uyar_bir_kez(_log, "yogunluk korelasyonu secilemedi: %r", m.get("ad"))
        return None
    return fonk


def _hafif_su_korelasyonu_mu(m):
    from cekirdek import malzeme_kutup as mk
    return _korelasyon(m) is mk.su_yogunluk


# ----------------------------------------------------------------------------
# malzeme rolleri
# ----------------------------------------------------------------------------

def _roller(m):
    elemanlar = {_eleman(b) for b in m.get("bilesim") or [] if b.get("isim")}
    roller = set()
    # yakit: kurucu._spec_fisil_mi ile AYNI olcut (herhangi bir Z >= 90
    # bilesen). Aktif eksenel aralik, kaynak kutusu ve tukenme bu tanima baglidir.
    if any(_z(e) >= 90 for e in elemanlar):
        roller.add("yakit")
    yog = _yogunluk_gcm3(m)
    if yog is not None and 0.0 < yog < _GAZ_YOGUNLUK_ESIGI:
        roller.add("gaz")
    if roller:
        return roller

    kes = _atom_kesirleri(m)
    ana = {e for e, f in kes.items() if f >= _ESER_ESIGI} or elemanlar

    # --- sogutucu (sivi / yogun faz) ---
    su = "H" in ana and ana <= {"H", "O", "B"}
    if su:
        roller.update(("sogutucu", "moderator"))       # hafif, agir, borlu su
    elif (_korelasyon(m) is not None or ana <= {"Na", "K"} or ana <= {"Pb", "Bi"}
          or ana == {"C", "O"}):
        roller.add("sogutucu")                          # Na, NaK, Pb, LBE, CO2

    # --- moderator (kati) ---
    if (ana in ({"C"}, {"Be"}, {"Be", "O"})                    # grafit, Be, BeO
            or ("H" in ana and ana <= {"H", "C"} and "C" in ana)  # polietilen
            or ("H" in ana and ana - {"H"} and ana - {"H"} <= {"Zr", "Y"})):  # ZrH, YH
        roller.add("moderator")

    # --- emici: sogurucu eser degil VE hafif baglayicilar disindaki atomlarin
    # yeterli kesri (1 ppm B'li grafitte B, H/C/N/O disindaki TEK atomdur;
    # oran %100 cikar ama malzeme yine grafittir) ---
    if "sogutucu" not in roller:
        agir = sum(f for e, f in kes.items() if e not in ("H", "C", "N", "O"))
        emici = sum(f for e, f in kes.items() if e in _EMICI_ELEMENTLER)
        if emici >= _ESER_ESIGI and agir > 0 and emici / agir >= _EMICI_ESIGI:
            roller.add("emici")

    if not roller:
        roller.add("yapisal")
    return roller


def malzeme_rolleri(spec):
    """
    {malzeme_adi: set(rol)} ; roller ROLLER icinden.
      yakit     : Z >= 90 bilesen (kurucu._spec_fisil_mi ile ayni olcut)
      gaz       : yogunluk < 0.01 g/cm3 (atom/b-cm ve kg/m3 de cevrilir)
      sogutucu  : su (H+O[+B], agir su dahil), Na, NaK, Pb, Pb-Bi, CO2 ve
                  tarama.py'nin yogunluk korelasyonu olan her malzeme
      moderator : su, grafit, Be, BeO, polietilen, ZrH/YH
      emici     : H/C/N/O disindaki atomlarin >= %5'i B, Gd, Ag, In, Cd, Hf,
                  Er, Eu, Dy, Sm (B4C, Gd2O3, AgInCd, Hf, Dy2TiO5, borlu celik)
                  -- borlu su sogutucu+moderatordur, emici DEGIL (bor eser
                  bir katkidir; emici rolu kontrol malzemeleri icindir)
      yapisal   : hicbir role girmeyen kati (zarf, celik, Al, SiC)
    Aile kurallarinda %0.5 atom altindaki bilesenler eser sayilir: 1 ppm B'li
    grafit grafittir, eser Hf'li zirkaloy yapisaldir.
    Bir malzeme birden fazla role sahip olabilir (su: sogutucu + moderator).
    """
    return {m["ad"]: _roller(m) for m in spec.get("malzemeler", []) if "ad" in m}


def tek_malzeme_rolleri(malzeme):
    """Tek bir malzeme taniminin rolleri (malzeme_rolleri ile ayni kural)."""
    return _roller(malzeme)


def rol_malzemeleri(spec, rol):
    """Belirli bir role sahip malzeme adlari (spec sirasiyla; kullanilmasa da)."""
    r = malzeme_rolleri(spec)
    return [m["ad"] for m in spec.get("malzemeler", []) if rol in r.get(m.get("ad"), ())]
