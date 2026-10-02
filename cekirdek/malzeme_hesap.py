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


# ============================================================================
# 6. Turetilmis degerler
# ============================================================================

def _sayi_ve_kutle_yogunlugu(m, kesirler, mol):
    """(N_toplam [atom/b-cm], rho [g/cm3]) -- yogunluk birimine gore."""
    y = m.get("yogunluk") or {}
    birim = y.get("birim") or "g/cm3"
    if birim == "macro":
        raise ValueError(_("'macro' yoğunluğu çok gruplu veri içindir; türetilmiş değer yok"))
    m_ort = ortalama_kutle(kesirler)
    if birim == "sum":
        if bilesim_birimi(m["bilesim"]) == "ao":       # satirlar atom/b-cm
            n = sum(mol.values())
            return n, atom_bcm_to_gcm3(n, m_ort)
        rho = sum(float(s["miktar"]) for s in m["bilesim"])   # satirlar g/cm3
        return gcm3_to_atom_bcm(rho, m_ort), rho
    deger = float(y.get("deger"))
    if not deger > 0.0:
        raise ValueError(_("yoğunluk pozitif olmalı: %r") % deger)
    if birim in ("g/cm3", "g/cc", "kg/m3"):
        rho = deger / 1000.0 if birim == "kg/m3" else deger
        return gcm3_to_atom_bcm(rho, m_ort), rho
    if birim in ("atom/b-cm", "atom/cm3"):
        n = deger * _BARN_CM2 if birim == "atom/cm3" else deger
        return n, atom_bcm_to_gcm3(n, m_ort)
    raise ValueError(_("bilinmeyen yoğunluk birimi: %r") % birim)


def turetilmis(m):
    """
    Spec malzemesinden turetilmis degerler (yeni sozluk):
      nuklidler        {nuklid: N_i [atom/b-cm]}
      N_toplam         sum N_i
      yogunluk_gcm3    rho
      ortalama_kutle   atom basina ortalama molar kutle [g/mol]
      agir_metal_gcm3  Z >= 90 nuklidlerin kutle yogunlugu (gHM/cm3)
      H_X              N_H / N_fisil (FISIL); H ya da fisil yoksa None
    """
    mol = nuklid_mol(m.get("bilesim") or [])
    kesirler = _normalize(mol)
    n_top, rho = _sayi_ve_kutle_yogunlugu(m, kesirler, mol)
    nuklidler = {n: a * n_top for n, a in kesirler.items()}
    na_b = avogadro_barn()
    hm = sum(v * kutle(n) / na_b for n, v in nuklidler.items()
             if atom_numarasi(n) >= _AGIR_METAL_Z)
    n_h = sum(v for n, v in nuklidler.items() if element_adi(n) == "H")
    n_x = sum(nuklidler.get(n, 0.0) for n in FISIL)
    return {"nuklidler": nuklidler, "N_toplam": n_top, "yogunluk_gcm3": rho,
            "ortalama_kutle": ortalama_kutle(kesirler), "agir_metal_gcm3": hm,
            "H_X": (n_h / n_x) if (n_h > 0.0 and n_x > 0.0) else None}


# ============================================================================
# 7. Cozunmus bor (ppm)
# ============================================================================

def _su_atom_kutlesi():
    """H2O'da atom basina ortalama kutle: (2 M_H + M_O) / 3."""
    return (2.0 * ortalama_kutle(dogal_vektor("H")) + ortalama_kutle(dogal_vektor("O"))) / 3.0


def _ppm_dogrula(ppm):
    if not 0.0 <= ppm < 1.0 / _PPM:
        raise ValueError(_("ppm 0 ile 1e6 arasında olmalı: %r") % ppm)


def ppm_wo_to_ao(ppm_wo, cozunen_vektor=None, cozucu_atom_kutlesi=None):
    """
    Kutlece ppm -> atomca ppm (cozeltinin BUTUN atomlarina gore):
      x = (w/M_B) / (w/M_B + (1-w)/M_c) ;  M_c = cozucu atom basina kutle
    Varsayilan: dogal bor, cozucu H2O.
    """
    _ppm_dogrula(ppm_wo)
    m_b = ortalama_kutle(cozunen_vektor or dogal_vektor("B"))
    m_c = cozucu_atom_kutlesi or _su_atom_kutlesi()
    w = ppm_wo * _PPM
    return (w / m_b) / (w / m_b + (1.0 - w) / m_c) / _PPM


def ppm_ao_to_wo(ppm_ao, cozunen_vektor=None, cozucu_atom_kutlesi=None):
    """Atomca ppm -> kutlece ppm: w = x M_B / (x M_B + (1-x) M_c)."""
    _ppm_dogrula(ppm_ao)
    m_b = ortalama_kutle(cozunen_vektor or dogal_vektor("B"))
    m_c = cozucu_atom_kutlesi or _su_atom_kutlesi()
    x = ppm_ao * _PPM
    return x * m_b / (x * m_b + (1.0 - x) * m_c) / _PPM


def bor_sayi_yogunlugu(ppm_wo, yogunluk, b10_ao=None):
    """Cozeltideki bor sayi yogunlugu: N_B = rho w N_A 1e-24 / M_B [atom/b-cm]."""
    _ppm_dogrula(ppm_wo)
    vek = zenginlestir("B", "B10", b10_ao) if b10_ao is not None else dogal_vektor("B")
    return gcm3_to_atom_bcm(yogunluk * ppm_wo * _PPM, ortalama_kutle(vek))


def _satir(isim, yuzde, tur="element", zenginlik_=None):
    d = {"tur": tur, "isim": isim, "miktar": yuzde, "birim": "wo"}
    if zenginlik_ is not None:
        d["zenginlik"] = zenginlik_
    return d


def borlu_su_bilesimi(ppm_wo, b10_ao=None):
    """
    Borlu hafif su, agirlikca YUZDE satirlar (sema.bilesen bicimi):
      B = w ; H = (1-w) 2M_H/M_H2O ; O = (1-w) M_O/M_H2O.
    b10_ao verilirse bor B10/B11 nuklid satirlari olur (zenginlestirilmis bor).
    """
    _ppm_dogrula(ppm_wo)
    w = ppm_wo * _PPM
    m_h = ortalama_kutle(dogal_vektor("H"))
    m_o = ortalama_kutle(dogal_vektor("O"))
    m_su = 2.0 * m_h + m_o
    satirlar = [_satir("H", 100.0 * (1.0 - w) * 2.0 * m_h / m_su),
                _satir("O", 100.0 * (1.0 - w) * m_o / m_su)]
    if w == 0.0:
        return satirlar
    if b10_ao is None:
        return satirlar + [_satir("B", 100.0 * w)]
    bw = ao_to_wo(zenginlestir("B", "B10", b10_ao))
    return satirlar + [_satir(n, 100.0 * w * f, tur="nuklid") for n, f in sorted(bw.items())]


# ============================================================================
# 8. Karisim (wo / ao / vo) -- openmc.Material.mix_materials ile ayni model
# ============================================================================

_TOPLAM_TOLERANSI = 1.0e-6


def _oranlari_dogrula(oranlar, n):
    if len(oranlar) != n or n == 0:
        raise ValueError(_("bileşen ve oran sayısı eşit olmalı"))
    if any(f < 0.0 for f in oranlar):
        raise ValueError(_("oranlar negatif olamaz"))
    if abs(sum(oranlar) - 1.0) > _TOPLAM_TOLERANSI:
        raise ValueError(_("oranların toplamı %%100 olmalı (şu an %%%.4f)") % (100.0 * sum(oranlar)))


def karistir(bilesenler, oranlar, tur):
    """
    bilesenler: [(vektor_ao, yogunluk_gcm3), ...]; oranlar toplami 1.
    Hacim toplanabilirligi (ideal karisim): bilesenin hacim kesri
      vo: v_i = f_i ; wo: v_i ~ f_i/rho_i ; ao: v_i ~ f_i M_i/rho_i
    N_n = sum v_i N_i,n ; rho = sum v_i rho_i.  DONER (vektor_ao, rho).
    """
    if tur not in ORAN_TURLERI:
        raise ValueError(_("karışım oranı ao, wo ya da vo olmalı: %r") % tur)
    _oranlari_dogrula(oranlar, len(bilesenler))
    kutleler = [ortalama_kutle(v) for v, _r in bilesenler]
    if tur == "vo":
        hacim = list(oranlar)
    else:
        ham = [f * (kutleler[i] if tur == "ao" else 1.0) / bilesenler[i][1]
               for i, f in enumerate(oranlar)]
        hacim = [h / sum(ham) for h in ham]
    sayi = {}
    for (vek, rho), m_i, v_i in zip(bilesenler, kutleler, hacim):
        n_i = gcm3_to_atom_bcm(rho, m_i)
        for nk, a in _normalize(vek).items():
            sayi[nk] = sayi.get(nk, 0.0) + v_i * n_i * a
    return _normalize(sayi), sum(v * r for v, (_vek, r) in zip(hacim, bilesenler))


def karisim_td(kesirler_wo, td_yogunluklari):
    """Ideal karisim kuramsal yogunlugu: 1/rho = sum(w_i/rho_i)."""
    _oranlari_dogrula(kesirler_wo, len(td_yogunluklari))
    return 1.0 / sum(w / r for w, r in zip(kesirler_wo, td_yogunluklari))


# ============================================================================
# 9. Yakit bilesimleri: UO2-Gd2O3, MOX, Am-241 yaslanmasi
# ============================================================================

def _uranyum_kutlesi(zenginlik_yuzde):
    return 1.0 / sum(w / kutle(n) for n, w in uranyum_vektoru(zenginlik_yuzde).items())


def uo2_gd2o3_bilesimi(zenginlik_yuzde, gd2o3_wo, gd_vektor_ao=None):
    """
    (U,Gd)O2 yakiti, agirlikca YUZDE satirlar. Kutle dengesi (1 g yakit):
      U  = (1-g) M_U / (M_U + 2 M_O)
      Gd = g 2M_Gd / (2M_Gd + 3M_O)
      O  = kalan
    g: Gd2O3 kutle kesri (0-1). gd_vektor_ao verilirse Gd nuklid satirlari.
    """
    if not 0.0 <= gd2o3_wo < 1.0:
        raise ValueError(_("Gd₂O₃ kütle kesri 0 ile 1 arasında olmalı: %r") % gd2o3_wo)
    m_u = _uranyum_kutlesi(zenginlik_yuzde)
    m_o = ortalama_kutle(dogal_vektor("O"))
    gd_vek = gd_vektor_ao or dogal_vektor("Gd")
    m_gd = ortalama_kutle(gd_vek)
    w_u = (1.0 - gd2o3_wo) * m_u / (m_u + 2.0 * m_o)
    w_gd = gd2o3_wo * 2.0 * m_gd / (2.0 * m_gd + 3.0 * m_o)
    satirlar = [_satir("U", 100.0 * w_u, zenginlik_=zenginlik_yuzde)]
    if gd_vektor_ao is None:
        satirlar.append(_satir("Gd", 100.0 * w_gd))
    else:
        satirlar += [_satir(n, 100.0 * w_gd * f, tur="nuklid")
                     for n, f in sorted(ao_to_wo(gd_vek).items())]
    return satirlar + [_satir("O", 100.0 * (1.0 - w_u - w_gd))]


PU_VEKTOR_NUKLIDLERI = ("Pu238", "Pu239", "Pu240", "Pu241", "Pu242", "Am241")


def _pu_vektoru_dogrula(vektor_wo):
    bilinmeyen = set(vektor_wo) - set(PU_VEKTOR_NUKLIDLERI)
    if bilinmeyen:
        raise ValueError(_("Pu vektöründe beklenmeyen nüklid: %s") % ", ".join(sorted(bilinmeyen)))
    _negatif_yok(vektor_wo)
    if abs(sum(vektor_wo.values()) - 1.0) > _TOPLAM_TOLERANSI:
        raise ValueError(_("Pu vektörünün toplamı %%100 olmalı (şu an %%%.4f)")
                         % (100.0 * sum(vektor_wo.values())))


def mox_bilesimi(pu_hm_wo, pu_vektor_wo, u_zenginlik_yuzde, om=2.0):
    """
    (U,Pu)O_x yakiti, agirlikca YUZDE satirlar. 1 g agir metal (HM) icin:
      U = 1 - p ;  Pu_i = p w_i ;  O = x M_O [ (1-p)/M_U + sum p w_i / M_i ]
    p = Pu/HM kutle kesri, w = Pu(+Am) vektoru (kutle, toplam 1), x = O/M.
    """
    if not 0.0 < pu_hm_wo <= 1.0:
        raise ValueError(_("Pu/HM kütle kesri 0 ile 1 arasında olmalı: %r") % pu_hm_wo)
    if om <= 0.0:
        raise ValueError(_("O/M oranı pozitif olmalı"))
    _pu_vektoru_dogrula(pu_vektor_wo)
    mol_hm = ((1.0 - pu_hm_wo) / _uranyum_kutlesi(u_zenginlik_yuzde)
              + sum(pu_hm_wo * w / kutle(n) for n, w in pu_vektor_wo.items()))
    m_o = om * ortalama_kutle(dogal_vektor("O")) * mol_hm
    toplam = 1.0 + m_o
    satirlar = []
    if pu_hm_wo < 1.0:
        satirlar.append(_satir("U", 100.0 * (1.0 - pu_hm_wo) / toplam,
                               zenginlik_=u_zenginlik_yuzde))
    satirlar += [_satir(n, 100.0 * pu_hm_wo * pu_vektor_wo[n] / toplam, tur="nuklid")
                 for n in PU_VEKTOR_NUKLIDLERI if pu_vektor_wo.get(n)]
    return satirlar + [_satir("O", 100.0 * m_o / toplam)]


def _bozunma_sabiti_yil(nuklid):
    t12 = _veri().half_life(nuklid)
    if not t12:
        raise ValueError(_("yarılanma ömrü bilinmiyor: %s") % nuklid)
    return math.log(2.0) / (t12 / _YIL_S)


def pu_yaslandir(vektor_wo, yil):
    """
    Pu(+Am) vektorunu 'yil' boyunca bozundurur (Bateman):
      N_i(t) = N_i(0) e^(-l_i t)                         (her nuklid)
      Am(t) += N_241(0) l_p/(l_a - l_p) (e^(-l_p t) - e^(-l_a t))   (Pu-241 -> Am-241)
    Diger urunler (Pu-238 -> U-234, Am-241 -> Np-237) vektorden cikar;
    sonuc kutle kesirleri yeniden normalize edilir. Yarilanma omurleri
    openmc.data.half_life (ENDF/B-VIII.0).
    """
    if yil < 0.0:
        raise ValueError(_("yaşlanma süresi negatif olamaz"))
    _pu_vektoru_dogrula(vektor_wo)
    atom = {n: w / kutle(n) for n, w in vektor_wo.items()}
    sonra = {n: a * math.exp(-_bozunma_sabiti_yil(n) * yil) for n, a in atom.items()}
    lp, la = _bozunma_sabiti_yil("Pu241"), _bozunma_sabiti_yil("Am241")
    olusan = atom.get("Pu241", 0.0) * lp / (la - lp) * (math.exp(-lp * yil) - math.exp(-la * yil))
    sonra["Am241"] = sonra.get("Am241", 0.0) + olusan
    return _normalize({n: a * kutle(n) for n, a in sonra.items()})
