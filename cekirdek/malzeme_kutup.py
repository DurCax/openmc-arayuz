# -*- coding: utf-8 -*-
"""
================================================================================
 malzeme_kutup.py  --  Hazir malzeme kutuphanesi
================================================================================

 Reaktor modellemesinde sik kullanilan malzemelerin dogrulanmis bilesimleri.
 Her fonksiyon sema.py bicimimde bir malzeme sozlugu dondurur; dogrudan
 spec["malzemeler"] listesine eklenebilir.

 KULLANIM
   from cekirdek import malzeme_kutup as mk
   spec["malzemeler"].append(mk.uo2(zenginlik=3.2))
   spec["malzemeler"].append(mk.su(sicaklik=580.0))
   print(mk.listele())            # kutuphanedeki tum malzemeler

 BIRIM KURALLARI
   yogunluk  g/cm3
   sicaklik  K
   "ao" = atom orani, "wo" = agirlik orani

 !!! DIKKAT !!!
   Sicakliga bagli yogunluk veren fonksiyonlar (su, agir_su, lbe, sodyum)
   yaklasik korelasyonlar kullanir; gecerlilik araliklari docstring'lerinde
   yazilidir. Kritik hesaplarda yogunlugu elle dogrulayin -- her fonksiyon
   yogunluk= parametresiyle elle ezilebilir.

 TERMAL SACILMA S(a,b)
   Su, grafit ve berilyum icin S(a,b) otomatik eklenir. Termal spektrumda
   bunlarin unutulmasi k'yi yuzde mertebesinde kaydirir -- dogrula.py bunu
   ayrica kontrol eder.
================================================================================
"""

from cekirdek.sema import malzeme, bilesen

# ----------------------------------------------------------------------------
# Renk paleti -- Model.plot() icin. OpenMC SVG renk adi veya (R,G,B) ister;
# hex dize KABUL ETMEZ. Bu yuzden hepsi demet olarak tutuluyor.
# ----------------------------------------------------------------------------
RENK = {
    "yakit":     (222,  93,  40),     # turuncu
    "yakit2":    (180,  60,  30),
    "zarf":      (150, 150, 160),     # gri
    "sogutucu":  ( 90, 150, 220),     # mavi
    "yansitici": (120, 200, 140),     # yesil
    "emici":     ( 60,  60,  60),     # koyu gri
    "yapisal":   (190, 190, 200),
    "gaz":       (235, 235, 245),
}


# ============================================================================
# 1. YAKITLAR
# ============================================================================

def uo2(zenginlik=3.2, yogunluk=10.40, sicaklik=900.0, ad=None):
    """
    UO2 -- uranyum dioksit. Teorik yogunluk 10.97 g/cm3; yakit peletleri
    tipik olarak %95 TD -> 10.40 g/cm3.
    zenginlik : U235 agirlik yuzdesi
    """
    return malzeme(
        ad or "uo2",
        [bilesen("U", 1.0, zenginlik=zenginlik), bilesen("O", 2.0)],
        yogunluk, sicaklik=sicaklik, renk=RENK["yakit"],
        gorunen_ad="UO2 %%%.2f" % zenginlik,
    )


def un(zenginlik=19.75, yogunluk=13.5, sicaklik=900.0, ad=None):
    """UN -- uranyum nitrur. Teorik yogunluk 14.3 g/cm3."""
    return malzeme(
        ad or "un",
        [bilesen("U", 1.0, zenginlik=zenginlik), bilesen("N", 1.0)],
        yogunluk, sicaklik=sicaklik, renk=RENK["yakit"],
        gorunen_ad="UN %%%.2f" % zenginlik,
    )


def u10mo(zenginlik=19.75, yogunluk=17.0, sicaklik=900.0, ad=None):
    """
    U-10Mo -- agirlikca %10 molibden alasimli metalik uranyum.
    Hizli reaktor ve arastirma reaktoru yakiti.
    """
    return malzeme(
        ad or "u10mo",
        [bilesen("U", 90.0, birim="wo", zenginlik=zenginlik),
         bilesen("Mo", 10.0, birim="wo")],
        yogunluk, sicaklik=sicaklik, renk=RENK["yakit"],
        gorunen_ad="U-10Mo %%%.2f" % zenginlik,
    )


def mox(pu_orani=7.0, pu_fissil=65.0, u_zenginlik=0.25,
        yogunluk=10.40, sicaklik=900.0, ad=None):
    """
    MOX -- karisik oksit yakit.
    pu_orani   : agir metal icindeki Pu agirlik yuzdesi
    pu_fissil  : Pu icindeki Pu239+Pu241 agirlik yuzdesi (kalani Pu240/242)
    Basitlestirilmis Pu vektoru kullanilir; ayrintili vektor gerekiyorsa
    malzemeyi elle tanimlayin.
    """
    pu239 = pu_fissil * 0.90
    pu241 = pu_fissil * 0.10
    pu240 = (100.0 - pu_fissil) * 0.85
    pu242 = (100.0 - pu_fissil) * 0.15
    olcek = pu_orani / 100.0
    u_orani = 1.0 - olcek
    return malzeme(
        ad or "mox",
        [bilesen("U", u_orani, zenginlik=u_zenginlik),
         bilesen("Pu239", pu239 * olcek / 100.0, tur="nuklid"),
         bilesen("Pu240", pu240 * olcek / 100.0, tur="nuklid"),
         bilesen("Pu241", pu241 * olcek / 100.0, tur="nuklid"),
         bilesen("Pu242", pu242 * olcek / 100.0, tur="nuklid"),
         bilesen("O", 2.0)],
        yogunluk, sicaklik=sicaklik, renk=RENK["yakit2"],
        gorunen_ad="MOX %%%.1f Pu" % pu_orani,
    )


def u3si2_al(u_yukleme=4.8, zenginlik=19.75, yogunluk=5.4,
             sicaklik=350.0, ad=None):
    """
    U3Si2-Al dispersiyon yakiti -- MTR tipi arastirma reaktoru plakalari.
    u_yukleme : gU/cm3 (tipik 4.8; yuksek yuklemede 5.3)
    Yogunluk dispersiyon yogunlugudur, u_yukleme ile tutarli olmalidir.
    """
    # U3Si2 icinde U agirlik orani: 3*238.03 / (3*238.03 + 2*28.09) = 0.9271
    u_kutle = u_yukleme                       # g U / cm3
    u3si2_kutle = u_kutle / 0.9271            # g U3Si2 / cm3
    al_kutle = max(yogunluk - u3si2_kutle, 0.0)
    top = u3si2_kutle + al_kutle
    return malzeme(
        ad or "u3si2_al",
        [bilesen("U", 100.0 * u_kutle / top, birim="wo", zenginlik=zenginlik),
         bilesen("Si", 100.0 * (u3si2_kutle - u_kutle) / top, birim="wo"),
         bilesen("Al", 100.0 * al_kutle / top, birim="wo")],
        yogunluk, sicaklik=sicaklik, renk=RENK["yakit"],
        gorunen_ad="U3Si2-Al %.1f gU/cc" % u_yukleme,
    )


# ============================================================================
# 2. ZARF VE YAPISAL MALZEMELER
# ============================================================================

def zirkaloy4(yogunluk=6.55, sicaklik=600.0, ad=None):
    """Zircaloy-4 -- ASTM B811 nominal bilesim (agirlikca)."""
    return malzeme(
        ad or "zirkaloy4",
        [bilesen("Zr", 98.23, birim="wo"), bilesen("Sn", 1.45, birim="wo"),
         bilesen("Fe", 0.21, birim="wo"), bilesen("Cr", 0.11, birim="wo")],
        yogunluk, sicaklik=sicaklik, renk=RENK["zarf"], gorunen_ad="Zircaloy-4",
    )


def ss316(yogunluk=7.99, sicaklik=600.0, ad=None):
    """AISI 316 paslanmaz celik -- nominal bilesim (agirlikca)."""
    return malzeme(
        ad or "ss316",
        [bilesen("Fe", 65.0, birim="wo"), bilesen("Cr", 17.0, birim="wo"),
         bilesen("Ni", 12.0, birim="wo"), bilesen("Mo", 2.5, birim="wo"),
         bilesen("Mn", 2.0, birim="wo"),  bilesen("Si", 1.0, birim="wo"),
         bilesen("C", 0.5, birim="wo")],
        yogunluk, sicaklik=sicaklik, renk=RENK["yapisal"], gorunen_ad="SS-316",
    )


def ma956(yogunluk=7.20, sicaklik=900.0, ad=None):
    """
    MA956 -- ODS FeCrAl alasimi (Incoloy MA956). Yuksek sicaklik zarf malzemesi.
    Y2O3 dagilimi Y ve O olarak verilir.
    """
    return malzeme(
        ad or "ma956",
        [bilesen("Fe", 74.0, birim="wo"), bilesen("Cr", 20.0, birim="wo"),
         bilesen("Al", 4.5, birim="wo"),  bilesen("Ti", 0.5, birim="wo"),
         bilesen("Y", 0.4, birim="wo"),   bilesen("O", 0.6, birim="wo")],
        yogunluk, sicaklik=sicaklik, renk=RENK["zarf"], gorunen_ad="MA956 (ODS)",
    )


def fecral(yogunluk=7.10, sicaklik=900.0, ad=None):
    """FeCrAl -- kaza toleransli yakit zarfi (Fe-13Cr-5Al nominal)."""
    return malzeme(
        ad or "fecral",
        [bilesen("Fe", 82.0, birim="wo"), bilesen("Cr", 13.0, birim="wo"),
         bilesen("Al", 5.0, birim="wo")],
        yogunluk, sicaklik=sicaklik, renk=RENK["zarf"], gorunen_ad="FeCrAl",
    )


def sic(yogunluk=3.21, sicaklik=900.0, ad=None):
    """SiC -- silisyum karbur. Teorik yogunluk 3.21 g/cm3."""
    return malzeme(
        ad or "sic",
        [bilesen("Si", 1.0), bilesen("C", 1.0)],
        yogunluk, sicaklik=sicaklik, renk=RENK["zarf"], gorunen_ad="SiC",
    )


def al6061(yogunluk=2.70, sicaklik=350.0, ad=None):
    """Al-6061 -- arastirma reaktoru plaka zarfi (agirlikca nominal)."""
    return malzeme(
        ad or "al6061",
        [bilesen("Al", 97.2, birim="wo"), bilesen("Mg", 1.0, birim="wo"),
         bilesen("Si", 0.6, birim="wo"),  bilesen("Fe", 0.4, birim="wo"),
         bilesen("Cu", 0.28, birim="wo"), bilesen("Cr", 0.2, birim="wo"),
         bilesen("Mn", 0.15, birim="wo"), bilesen("Zn", 0.17, birim="wo")],
        yogunluk, sicaklik=sicaklik, renk=RENK["yapisal"], gorunen_ad="Al-6061",
    )


# ============================================================================
# 3. SOGUTUCULAR VE MODERATORLER
# ============================================================================

# Doymus sivi su yogunlugu (buhar tablosu), T[K] -> rho[g/cm3].
# Ara degerler dogrusal interpolasyonla bulunur.
_SU_TABLO = [
    (273.15, 0.9998), (293.15, 0.9982), (323.15, 0.9881), (373.15, 0.9584),
    (423.15, 0.9169), (473.15, 0.8647), (523.15, 0.7992), (553.15, 0.7504),
    (573.15, 0.7122), (593.15, 0.6663), (613.15, 0.6091), (623.15, 0.5743),
]


def su_yogunluk(sicaklik):
    """
    Doymus sivi su yogunlugu [g/cm3], T [K].
    GECERLILIK 273-623 K. Doymus egri degerleridir; basincli su (PWR, 15.5 MPa)
    icin yaklasik %1 dusuk kalir. Kritik hesaplarda elle dogrulayin.
    """
    if sicaklik <= _SU_TABLO[0][0]:
        return _SU_TABLO[0][1]
    if sicaklik >= _SU_TABLO[-1][0]:
        return _SU_TABLO[-1][1]
    for i in range(len(_SU_TABLO) - 1):
        t0, r0 = _SU_TABLO[i]
        t1, r1 = _SU_TABLO[i + 1]
        if t0 <= sicaklik <= t1:
            return r0 + (r1 - r0) * (sicaklik - t0) / (t1 - t0)
    return _SU_TABLO[-1][1]


def su(sicaklik=293.6, yogunluk=None, bor_ppm=0.0, ad=None):
    """
    Hafif su. yogunluk verilmezse su_yogunluk(sicaklik) kullanilir.
    bor_ppm : cozunmus dogal bor (agirlikca ppm) -- PWR kimyasal kontrolu.
    S(a,b) olarak c_H_in_H2O otomatik eklenir.
    """
    rho = yogunluk if yogunluk is not None else su_yogunluk(sicaklik)
    bil = [bilesen("H", 2.0), bilesen("O", 1.0)]
    gad = "H2O %.3f g/cc" % rho
    if bor_ppm > 0:
        # ppm agirlikca: 1e-6 * ppm kutle orani bor
        bil = [bilesen("H", 2.0 * 1.008 / 18.015 * 100.0 * (1 - bor_ppm * 1e-6), birim="wo"),
               bilesen("O", 16.0 / 18.015 * 100.0 * (1 - bor_ppm * 1e-6), birim="wo"),
               bilesen("B", bor_ppm * 1e-4, birim="wo")]
        gad += " + %.0f ppm B" % bor_ppm
    return malzeme(ad or "su", bil, rho, sicaklik=sicaklik,
                   sab=["c_H_in_H2O"], renk=RENK["sogutucu"], gorunen_ad=gad)


def agir_su(sicaklik=293.6, yogunluk=1.1056, saflik=99.75, ad=None):
    """
    Agir su (D2O). saflik : D2O mol yuzdesi, kalani H2O.
    S(a,b) olarak c_D_in_D2O eklenir.
    """
    d = 2.0 * saflik / 100.0
    h = 2.0 * (1.0 - saflik / 100.0)
    return malzeme(
        ad or "agir_su",
        [bilesen("H2", d, tur="nuklid"), bilesen("H1", h, tur="nuklid"),
         bilesen("O", 1.0)],
        yogunluk, sicaklik=sicaklik, sab=["c_D_in_D2O"],
        renk=RENK["sogutucu"], gorunen_ad="D2O %%%.2f" % saflik,
    )


def lbe(sicaklik=723.0, yogunluk=None, ad=None):
    """
    Kursun-bizmut otektigi (LBE), agirlikca %44.5 Pb - %55.5 Bi.
    Yogunluk korelasyonu (Sobolev / OECD-NEA 2007 el kitabi):
        rho [kg/m3] = 11096 - 1.3236 * T[K]
    GECERLILIK 400-1300 K.
    """
    rho = yogunluk if yogunluk is not None else (11096.0 - 1.3236 * sicaklik) / 1000.0
    return malzeme(
        ad or "lbe",
        [bilesen("Pb", 44.5, birim="wo"), bilesen("Bi", 55.5, birim="wo")],
        rho, sicaklik=sicaklik, renk=(140, 140, 170),
        gorunen_ad="LBE %.0f K (%.2f g/cc)" % (sicaklik, rho),
    )


def sodyum(sicaklik=673.0, yogunluk=None, ad=None):
    """
    Sivi sodyum. Yogunluk korelasyonu (Fink & Leibowitz, dogrusal yaklasim):
        rho [kg/m3] = 1014 - 0.235 * T[K]
    GECERLILIK 371-1200 K.
    """
    rho = yogunluk if yogunluk is not None else (1014.0 - 0.235 * sicaklik) / 1000.0
    return malzeme(ad or "sodyum", [bilesen("Na", 1.0)], rho,
                   sicaklik=sicaklik, renk=(200, 200, 120),
                   gorunen_ad="Na %.0f K (%.3f g/cc)" % (sicaklik, rho))


def helyum(yogunluk=0.0001785, sicaklik=600.0, ad=None):
    """Helyum bosluk gazi (yakit-zarf araligi). Normal sartlarda yogunluk."""
    return malzeme(ad or "helyum", [bilesen("He", 1.0)], yogunluk,
                   sicaklik=sicaklik, renk=RENK["gaz"], gorunen_ad="He")


def grafit(yogunluk=1.70, sicaklik=600.0, ad=None):
    """Nukleer safiyette grafit. S(a,b) olarak c_Graphite eklenir."""
    return malzeme(ad or "grafit", [bilesen("C", 1.0)], yogunluk,
                   sicaklik=sicaklik, sab=["c_Graphite"],
                   renk=RENK["yansitici"], gorunen_ad="Grafit")


def berilyum(yogunluk=1.85, sicaklik=350.0, ad=None):
    """Berilyum yansitici. S(a,b) olarak c_Be eklenir."""
    return malzeme(ad or "berilyum", [bilesen("Be", 1.0)], yogunluk,
                   sicaklik=sicaklik, sab=["c_Be"],
                   renk=RENK["yansitici"], gorunen_ad="Be")


# ============================================================================
# 4. EMICILER VE KONTROL MALZEMELERI
# ============================================================================

def b4c(yogunluk=2.52, b10_zenginlik=None, sicaklik=600.0, ad=None):
    """
    B4C -- bor karbur kontrol/emici malzemesi.
    b10_zenginlik : B10 atom yuzdesi; None ise dogal bor (%19.9 B10).
    """
    if b10_zenginlik is None:
        bil = [bilesen("B", 4.0), bilesen("C", 1.0)]
        gad = "B4C (dogal)"
    else:
        f = b10_zenginlik / 100.0
        bil = [bilesen("B10", 4.0 * f, tur="nuklid"),
               bilesen("B11", 4.0 * (1 - f), tur="nuklid"),
               bilesen("C", 1.0)]
        gad = "B4C %%%.1f B10" % b10_zenginlik
    return malzeme(ad or "b4c", bil, yogunluk, sicaklik=sicaklik,
                   renk=RENK["emici"], gorunen_ad=gad)


def gd2o3(yogunluk=7.41, sicaklik=900.0, ad=None):
    """Gd2O3 -- yanabilir zehir (genellikle UO2 icinde karisim olarak)."""
    return malzeme(ad or "gd2o3",
                   [bilesen("Gd", 2.0), bilesen("O", 3.0)],
                   yogunluk, sicaklik=sicaklik, renk=(100, 60, 120),
                   gorunen_ad="Gd2O3")


def agincd(yogunluk=10.16, sicaklik=600.0, ad=None):
    """Ag-In-Cd kontrol cubugu alasimi (agirlikca 80/15/5)."""
    return malzeme(ad or "agincd",
                   [bilesen("Ag", 80.0, birim="wo"),
                    bilesen("In", 15.0, birim="wo"),
                    bilesen("Cd", 5.0, birim="wo")],
                   yogunluk, sicaklik=sicaklik, renk=RENK["emici"],
                   gorunen_ad="Ag-In-Cd")


# ============================================================================
# 5. KUTUPHANE KAYDI
# ============================================================================

KUTUPHANE = {
    # yakitlar
    "uo2": (uo2, "UO2 -- zenginlik parametreli uranyum dioksit"),
    "un": (un, "UN -- uranyum nitrur"),
    "u10mo": (u10mo, "U-10Mo -- metalik alasim yakit"),
    "mox": (mox, "MOX -- karisik oksit"),
    "u3si2_al": (u3si2_al, "U3Si2-Al -- MTR dispersiyon yakiti"),
    # zarf / yapisal
    "zirkaloy4": (zirkaloy4, "Zircaloy-4 zarf"),
    "ss316": (ss316, "AISI 316 paslanmaz celik"),
    "ma956": (ma956, "MA956 ODS FeCrAl"),
    "fecral": (fecral, "FeCrAl kaza toleransli zarf"),
    "sic": (sic, "Silisyum karbur"),
    "al6061": (al6061, "Al-6061 plaka zarfi"),
    # sogutucu / moderator
    "su": (su, "Hafif su (S(a,b) dahil, sicakliga bagli yogunluk)"),
    "agir_su": (agir_su, "Agir su D2O"),
    "lbe": (lbe, "Kursun-bizmut otektigi"),
    "sodyum": (sodyum, "Sivi sodyum"),
    "helyum": (helyum, "Helyum bosluk gazi"),
    "grafit": (grafit, "Grafit yansitici/moderator"),
    "berilyum": (berilyum, "Berilyum yansitici"),
    # emiciler
    "b4c": (b4c, "Bor karbur"),
    "gd2o3": (gd2o3, "Gadolinyum oksit yanabilir zehir"),
    "agincd": (agincd, "Ag-In-Cd kontrol alasimi"),
}


def uret(anahtar, **kwargs):
    """Kutuphaneden ada gore malzeme uretir."""
    if anahtar not in KUTUPHANE:
        raise KeyError("kutuphanede yok: %s  (mevcut: %s)"
                       % (anahtar, ", ".join(sorted(KUTUPHANE))))
    return KUTUPHANE[anahtar][0](**kwargs)


def listele():
    """Kutuphanedeki malzemeleri (anahtar, aciklama) olarak dondurur."""
    return [(k, v[1]) for k, v in sorted(KUTUPHANE.items())]
