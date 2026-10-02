# -*- coding: utf-8 -*-
"""
================================================================================
 malzeme_hesap.py  --  Malzeme hesaplayicilari (saf islevler)
================================================================================

 Malzeme asistaninin ve turetilmis degerler panelinin hesap cekirdegi. Hicbir
 islev girdisini degistirmez; hepsi yeni sozluk/sayi dondurur.

 VERI KAYNAKLARI (sabit yazilmaz, openmc.data'dan okunur)
   atom kutleleri        openmc.data.atomic_mass  -- AME2020 (Wang vd., Chinese
                         Phys. C 45 (2021) 030003)
   dogal bolluklar       openmc.data.NATURAL_ABUNDANCE -- IUPAC/CIAAW
                         "Isotopic compositions of the elements 2013"
                         (Meija vd., Pure Appl. Chem. 88 (2016) 293)
   yarilanma omurleri    openmc.data.half_life (ENDF/B-VIII.0 bozunma alt
                         kutuphanesi)
   Avogadro sabiti       openmc.data.AVOGADRO (CODATA 2018, tam deger)

 BIRIMLER
   yogunluk g/cm3; sayi yogunlugu atom/b-cm (1 b = 1e-24 cm2); kesirler 0-1
   (arayuz yuzde gosterir); zenginlik yuzde (OpenMC kurali).

 BILESIM GOSTERIMI
   "vektor" = {nuklid: kesir} (toplam 1). Spec bilesimi (sema.bilesen
   satirlari) nuklid_atom_kesirleri() ile atom kesirlerine acilir; acilis
   OpenMC'nin Element.expand mantigiyla aynidir (kesit kutuphanesi suzgeci
   haric: burada butun dogal izotoplar sayilir).
================================================================================
"""

import math
import re

from cekirdek.ceviri import _

# ----------------------------------------------------------------------------
# Adli sabitler (kaynakli)
# ----------------------------------------------------------------------------
# UO2 kuramsal yogunlugu [g/cm3], 300 K -- NUREG/CR-6150 (MATPRO), INEL-96/0422
# Rev.2, "FDEN": 10.97 g/cm3.
UO2_TD = 10.97
# Gd2O3 (kubik) kuramsal yogunlugu [g/cm3] -- CRC Handbook of Chemistry and
# Physics, 97. bs., "Physical Constants of Inorganic Compounds": 7.407.
GD2O3_TD = 7.407
# B4C kuramsal yogunlugu [g/cm3] -- CRC Handbook, 97. bs.: 2.52.
B4C_TD = 2.52

# ORNL/CSD/TM-244 (1988) bagintisi: U-234 ve U-236 agirlik yuzdeleri U-235
# agirlik yuzdesinin 0.0089 ve 0.0046 kati. OpenMC Element.expand ile ayni.
_U234_KATSAYI = 0.0089
_U236_KATSAYI = 0.0046

# Fisil nuklidler (H/X orani paydasi) -- termal fisil izotoplar.
FISIL = ("U233", "U235", "Pu239", "Pu241")
# Agir metal: Z >= 90 (aktinitler; gHM/cm3 tanimi, IAEA terminolojisi).
_AGIR_METAL_Z = 90

_PPM = 1.0e-6
_BARN_CM2 = 1.0e-24
# Bir yil [s] -- Julian yili (IAU), yarilanma omru donusumu icin.
_YIL_S = 365.25 * 86400.0

_NUKLID_KALIBI = re.compile(r"^([A-Z][a-z]?)(\d+)(_m\d+)?$")

ORAN_TURLERI = ("ao", "wo", "vo")


# ============================================================================
# 1. Veri erisimi (openmc.data tembel yuklenir: ice aktarim ~0.5 s)
# ============================================================================

def _veri():
    import openmc.data
    return openmc.data


def avogadro_barn():
    """N_A x 1e-24 = 0.602214076 (atom/b-cm) / (mol/cm3)."""
    return _veri().AVOGADRO * _BARN_CM2


def element_adi(nuklid):
    """'U235' -> 'U', 'Am242_m1' -> 'Am'. Gecersiz adda ValueError."""
    e = _NUKLID_KALIBI.match(nuklid or "")
    if not e:
        raise ValueError(_("geçersiz nüklid adı: %r") % (nuklid,))
    return e.group(1)


def atom_numarasi(nuklid_ya_da_element):
    """Z (element ya da nuklid adindan)."""
    ad = nuklid_ya_da_element
    if _NUKLID_KALIBI.match(ad or ""):
        ad = element_adi(ad)
    z = _veri().ATOMIC_NUMBER.get(ad)
    if z is None:
        raise ValueError(_("bilinmeyen element: %r") % (ad,))
    return z


def kutle(nuklid):
    """Nuklid atom kutlesi [g/mol] (AME2020)."""
    try:
        return float(_veri().atomic_mass(nuklid))
    except (KeyError, ValueError) as e:
        raise ValueError(_("atom kütlesi bilinmiyor: %s") % nuklid) from e


def dogal_vektor(element):
    """Elementin dogal izotopik bileşimi {nuklid: atom kesri} (toplam 1)."""
    izo = _veri().isotopes(element)
    if not izo:
        raise ValueError(_("doğal izotopu olmayan element: %s (izotopları "
                           "tek tek verin)") % element)
    toplam = sum(a for _n, a in izo)
    return {n: a / toplam for n, a in izo}


# ============================================================================
# 2. Kesir donusumleri ve ortalama kutle
# ============================================================================

def _normalize(vektor):
    toplam = sum(vektor.values())
    if toplam <= 0.0:
        raise ValueError(_("kesirlerin toplamı sıfır"))
    return {k: v / toplam for k, v in vektor.items()}


def _negatif_yok(vektor):
    for k, v in vektor.items():
        if v < 0.0 or math.isnan(v):
            raise ValueError(_("negatif ya da geçersiz kesir: %s = %r") % (k, v))


def ao_to_wo(vektor_ao):
    """Atom kesirleri -> agirlik kesirleri: w_i = a_i M_i / sum(a_j M_j)."""
    _negatif_yok(vektor_ao)
    return _normalize({n: a * kutle(n) for n, a in vektor_ao.items()})


def wo_to_ao(vektor_wo):
    """Agirlik kesirleri -> atom kesirleri: a_i = (w_i/M_i) / sum(w_j/M_j)."""
    _negatif_yok(vektor_wo)
    return _normalize({n: w / kutle(n) for n, w in vektor_wo.items()})


def ortalama_kutle(vektor_ao):
    """Atom basina ortalama molar kutle [g/mol]: sum(a_i M_i), a normalize."""
    a = _normalize(vektor_ao)
    return sum(f * kutle(n) for n, f in a.items())


def gcm3_to_atom_bcm(yogunluk, ortalama_molar_kutle):
    """g/cm3 -> atom/b-cm: N = rho N_A 1e-24 / M."""
    if ortalama_molar_kutle <= 0.0:
        raise ValueError(_("ortalama molar kütle pozitif olmalı"))
    return yogunluk * avogadro_barn() / ortalama_molar_kutle


def atom_bcm_to_gcm3(sayi_yogunlugu, ortalama_molar_kutle):
    """atom/b-cm -> g/cm3: rho = N M / (N_A 1e-24)."""
    return sayi_yogunlugu * ortalama_molar_kutle / avogadro_barn()


# ============================================================================
# 3. Kuramsal yogunluk, gozeneklilik
# ============================================================================

def yogunluk_td(td_yogunluk, td_orani=None, gozeneklilik=None):
    """
    Kuramsal yogunluk (TD) kesrinden ya da gozeneklilikten yogunluk:
      rho = rho_TD * f_TD       veya   rho = rho_TD * (1 - p)
    Tam olarak biri verilir; f_TD (0, 1], p [0, 1).
    """
    if (td_orani is None) == (gozeneklilik is None):
        raise ValueError(_("%TD ya da gözeneklilikten yalnız biri verilmeli"))
    if td_yogunluk <= 0.0:
        raise ValueError(_("kuramsal yoğunluk pozitif olmalı"))
    if gozeneklilik is not None:
        if not 0.0 <= gozeneklilik < 1.0:
            raise ValueError(_("gözeneklilik 0 ile 1 arasında olmalı: %r") % gozeneklilik)
        return td_yogunluk * (1.0 - gozeneklilik)
    if not 0.0 < td_orani <= 1.0:
        raise ValueError(_("%%TD kesri 0 ile 1 arasında olmalı: %r") % td_orani)
    return td_yogunluk * td_orani


def td_orani(yogunluk, td_yogunluk):
    """Yogunlugun kuramsal yogunluga orani (f_TD)."""
    if td_yogunluk <= 0.0:
        raise ValueError(_("kuramsal yoğunluk pozitif olmalı"))
    return yogunluk / td_yogunluk


# ============================================================================
# 4. Zenginlik <-> izotopik vektor
# ============================================================================

def uranyum_vektoru(zenginlik):
    """
    U-235 agirlikca % zenginlikten uranyum izotopik vektoru (agirlik kesri),
    ORNL/CSD/TM-244: w234 = 0.0089 e, w236 = 0.0046 e, w238 = kalan.
    OpenMC add_element('U', ..., enrichment=e) ile ayni bagintidir.
    """
    if not 0.0 <= zenginlik <= 100.0 / (1.0 + _U234_KATSAYI + _U236_KATSAYI):
        raise ValueError(_("U-235 zenginliği 0 ile %%%.2f arasında olmalı: %r")
                         % (100.0 / (1.0 + _U234_KATSAYI + _U236_KATSAYI), zenginlik))
    e = zenginlik / 100.0
    return {"U234": _U234_KATSAYI * e, "U235": e, "U236": _U236_KATSAYI * e,
            "U238": 1.0 - (1.0 + _U234_KATSAYI + _U236_KATSAYI) * e}


def zenginlestir(element, hedef, oran, birim="ao"):
    """
    Dogal elementin 'hedef' izotopunu 'oran'a (0-1, ao ya da wo) cikarir; diger
    izotoplar DOGAL ORANLARINI koruyarak kalan paya bolunur:
      x_hedef = oran,   x_i = (1 - oran) x_i,dogal / (1 - x_hedef,dogal)
    (OpenMC Element.expand(enrichment_target=...) ile ayni yontem; burada iki
    izotoptan fazlasi da -- Gd -- desteklenir.)  DONER atom kesirleri.
    """
    if birim not in ("ao", "wo"):
        raise ValueError(_("zenginlik birimi ao ya da wo olmalı: %r") % birim)
    if not 0.0 <= oran <= 1.0:
        raise ValueError(_("zenginlik kesri 0 ile 1 arasında olmalı: %r") % oran)
    dogal = dogal_vektor(element)
    if hedef not in dogal:
        raise ValueError(_("%s, %s elementinin doğal izotopu değil") % (hedef, element))
    taban = ao_to_wo(dogal) if birim == "wo" else dogal
    kalan = 1.0 - taban[hedef]
    yeni = {n: (1.0 - oran) * f / kalan for n, f in taban.items() if n != hedef}
    yeni[hedef] = oran
    return wo_to_ao(yeni) if birim == "wo" else _normalize(yeni)


def zenginlik(vektor_ao, hedef, birim="ao"):
    """Ters islem: vektordeki 'hedef'in kesri (ao ya da wo)."""
    v = ao_to_wo(vektor_ao) if birim == "wo" else _normalize(vektor_ao)
    return v.get(hedef, 0.0)


# ============================================================================
# 5. Bilesim acilimi (spec satirlari -> nuklid atom kesirleri)
# ============================================================================

def element_vektoru(element, zenginlik_yuzde=None):
    """Element satirinin atom kesirleri (U'da zenginlik ORNL/CSD/TM-244)."""
    if zenginlik_yuzde is None:
        return dogal_vektor(element)
    if element != "U":
        raise ValueError(_("zenginlik kısayolu yalnız uranyum içindir (%s)") % element)
    return wo_to_ao(uranyum_vektoru(zenginlik_yuzde))


def _satir_mol(satir, birim):
    """Bir bilesim satirinin {nuklid: mol katkisi}; wo'da miktar/M_ort."""
    miktar = float(satir["miktar"])
    if miktar < 0.0 or math.isnan(miktar):
        raise ValueError(_("negatif miktar: %s = %r") % (satir.get("isim"), miktar))
    if satir.get("tur") == "nuklid":
        vek = {satir["isim"]: 1.0}
    else:
        vek = element_vektoru(satir["isim"], satir.get("zenginlik"))
    if birim == "ao":
        return {n: miktar * a for n, a in vek.items()}
    m_ort = sum(a * kutle(n) for n, a in vek.items())
    return {n: miktar * a / m_ort for n, a in vek.items()}


def bilesim_birimi(bilesim):
    """Bilesimin tek orani (ao ya da wo); karisiksa ValueError (OpenMC de reddeder)."""
    birimler = {b.get("birim", "ao") for b in bilesim}
    if len(birimler) != 1 or not birimler <= {"ao", "wo"}:
        raise ValueError(_("bileşimde atom ve ağırlık oranları karışık ya da geçersiz: %s")
                         % ", ".join(sorted(birimler)))
    return birimler.pop()


def nuklid_mol(bilesim):
    """Normalize EDILMEMIS {nuklid: mol} ('sum' biriminde atom/b-cm toplami)."""
    if not bilesim:
        raise ValueError(_("bileşim boş"))
    birim = bilesim_birimi(bilesim)
    toplam = {}
    for satir in bilesim:
        for n, m in _satir_mol(satir, birim).items():
            toplam[n] = toplam.get(n, 0.0) + m
    return toplam


def nuklid_atom_kesirleri(bilesim):
    """Spec bilesimi -> {nuklid: atom kesri} (toplam 1)."""
    return _normalize(nuklid_mol(bilesim))
