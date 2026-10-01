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
from cekirdek.ceviri import _, N_

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


# U3Si2 icinde U agirlik orani: 3*238.03 / (3*238.03 + 2*28.09)
_U3SI2_U_ORANI = 0.9271
# U3Si2 kuramsal yogunlugu ve Al yogunlugu [g/cm3]
_U3SI2_YOGUNLUK = 12.2
_AL_YOGUNLUK = 2.70


def u3si2_yogunlugu(u_yukleme, gozeneklilik=0.0):
    """
    U3Si2-Al dispersiyon yakitinin (et) yogunlugu [g/cm3], U yuklemesinden:
      U3Si2 kutlesi   m = u_yukleme / 0.9271              [g/cm3 et]
      U3Si2 hacmi     v = m / 12.2                         [cm3/cm3 et]
      Al hacmi        1 - v - p     (p: gozeneklilik, 0-1)
      yogunluk        m + (1 - v - p) * 2.70
    4.8 gU/cm3, p = 0 -> 6.73 g/cm3. (Eski sabit varsayilan 5.4 g/cm3 bu
    yuklemeyle tutarsizdi: Al payi %4'e dusuyordu.)
    """
    m = u_yukleme / _U3SI2_U_ORANI
    v = m / _U3SI2_YOGUNLUK
    al_hacmi = 1.0 - v - gozeneklilik
    if al_hacmi < 0.0:
        raise ValueError(_("U yüklemesi %.2f gU/cm³ ve gözeneklilik %%%.1f ile alüminyuma yer "
                         "kalmıyor (U₃Si₂ hacim kesri %.2f).") % (u_yukleme, 100 * gozeneklilik, v))
    return m + al_hacmi * _AL_YOGUNLUK


def u3si2_al(u_yukleme=4.8, zenginlik=19.75, gozeneklilik=0.0, yogunluk=None,
             sicaklik=350.0, ad=None):
    """
    U3Si2-Al dispersiyon yakiti -- MTR tipi arastirma reaktoru plakalari.
    u_yukleme    : gU/cm3 (tipik 4.8; yuksek yuklemede 5.3)
    gozeneklilik : etteki bosluk hacim kesri (0-1); varsayilan 0
    yogunluk     : verilmezse yuklemeden hesaplanir (u3si2_yogunlugu);
                   verilirse aynen kullanilir (eski dosyalar ve elle deger).
    """
    if yogunluk is None:
        yogunluk = u3si2_yogunlugu(u_yukleme, gozeneklilik)
    u_kutle = u_yukleme                          # g U / cm3
    u3si2_kutle = u_kutle / _U3SI2_U_ORANI       # g U3Si2 / cm3
    al_kutle = max(yogunluk - u3si2_kutle, 0.0)
    top = u3si2_kutle + al_kutle
    return malzeme(
        ad or "u3si2_al",
        [bilesen("U", 100.0 * u_kutle / top, birim="wo", zenginlik=zenginlik),
         bilesen("Si", 100.0 * (u3si2_kutle - u_kutle) / top, birim="wo"),
         bilesen("Al", 100.0 * al_kutle / top, birim="wo")],
        yogunluk, sicaklik=sicaklik, renk=RENK["yakit"],
        gorunen_ad="U3Si2-Al %.1f gU/cm³" % u_yukleme,
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
    gad = "H2O %.3f g/cm³" % rho
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
        gorunen_ad="LBE %.0f K (%.2f g/cm³)" % (sicaklik, rho),
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
                   gorunen_ad="Na %.0f K (%.3f g/cm³)" % (sicaklik, rho))


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
        gad = "B4C (doğal)"
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
    "uo2": (uo2, N_("UO₂ — zenginlik parametreli uranyum dioksit")),
    "un": (un, N_("UN — uranyum nitrür")),
    "u10mo": (u10mo, N_("U-10Mo — metalik alaşım yakıt")),
    "mox": (mox, N_("MOX — karışık oksit")),
    "u3si2_al": (u3si2_al, N_("U₃Si₂-Al — MTR dispersiyon yakıtı")),
    # zarf / yapisal
    "zirkaloy4": (zirkaloy4, N_("Zircaloy-4 zarf")),
    "ss316": (ss316, N_("AISI 316 paslanmaz çelik")),
    "ma956": (ma956, N_("MA956 ODS FeCrAl")),
    "fecral": (fecral, N_("FeCrAl kazaya dayanıklı zarf")),
    "sic": (sic, N_("Silisyum karbür")),
    "al6061": (al6061, N_("Al-6061 plaka zarfı")),
    # sogutucu / moderator
    "su": (su, N_("Hafif su (S(α,β) dahil, sıcaklığa bağlı yoğunluk)")),
    "agir_su": (agir_su, N_("Ağır su (D₂O)")),
    "lbe": (lbe, N_("Kurşun-bizmut ötektiği")),
    "sodyum": (sodyum, N_("Sıvı sodyum")),
    "helyum": (helyum, N_("Helyum dolgu gazı")),
    "grafit": (grafit, N_("Grafit yansıtıcı/moderatör")),
    "berilyum": (berilyum, N_("Berilyum yansıtıcı")),
    # emiciler
    "b4c": (b4c, N_("Bor karbür")),
    "gd2o3": (gd2o3, N_("Gadolinyum oksit yanabilir zehir")),
    "agincd": (agincd, N_("Ag-In-Cd kontrol alaşımı")),
}


def uret(anahtar, **kwargs):
    """Kutuphaneden ada gore malzeme uretir."""
    if anahtar not in KUTUPHANE:
        raise KeyError(_("kütüphanede yok: %s  (mevcut: %s)")
                       % (anahtar, ", ".join(sorted(KUTUPHANE))))
    return KUTUPHANE[anahtar][0](**kwargs)


def listele():
    """Kutuphanedeki malzemeleri (anahtar, aciklama) olarak dondurur
    (aciklama etkin dilde)."""
    return [(k, _(v[1])) for k, v in sorted(KUTUPHANE.items())]


# ============================================================================
# 6. PARAMETRIK MALZEME -- "kutup" kaydi
# ============================================================================
#
#  Kutuphaneden arayuzle eklenen malzeme, URETIM PARAMETRELERINI de tasir:
#
#      m["kutup"] = {"anahtar": "su", "param": {"sicaklik": 580.0, "bor_ppm": 1300.0}}
#
#  Boylece "Duzenle" ayni parametre formunu yeniden acar ve malzeme bu
#  parametrelerden YENIDEN URETILIR (bilesim, yogunluk, sicaklik, S(a,b),
#  aciklama). Once parametreler tek seferlikti: 580 K su 600 K'e cekilince
#  yogunluk 0.6965'te (600 K: 0.6467), aciklama "H2O 0.696 g/cc"de kaliyordu.
#
#  kurucu.py ve kod_uret.py bu anahtari OKUMAZ (malzemenin alanlarina tek tek
#  erisirler); model yalnizca bilesim/yogunluk/sicaklik/sab'dan kurulur.
#
#  TUTARLILIK: ayni parametrelerle yeniden uretim BIT BIT ayni bilesimi verir
#  (fonksiyonlar deterministik; JSON float gidis-donusu kayipsiz). Malzeme
#  parametre formu disinda degistirilmisse (elle JSON, eski surum) yeniden
#  uretim onu EZMEMELI: parametrik_mi() bunu yakalar ve arayuz bileşim
#  tablosuna duser.
#
#  ROL/GRUP BURADA YAZILMAZ: kutuphane listesindeki gruplar
#  uygunluk.tek_malzeme_rolleri'nden turetilir (tek dogruluk kaynagi).
# ----------------------------------------------------------------------------

# Parametrik yeniden uretimde karsilastirilan (fizik tasiyan) alanlar.
FIZIK_ALANLARI = ("bilesim", "yogunluk", "sicaklik", "sab")

# Ortak parametre tanimlari (etiket gorunen metindir; anahtar fonksiyon
# argumanidir). "tur": "sayi" | "sicaklik" (K + canli °C) | "dogal_ya_da"
# (en kucuk deger = None = dogal bolluk).
_PARAM = {
    "zenginlik": {"etiket": N_("U-235 ağırlıkça %"), "en_az": 0.01, "en_cok": 97.0,
                  "ondalik": 2, "adim": 0.1, "sonek": "%",
                  "ipucu": N_("U-235'in uranyum içindeki ağırlık yüzdesi. OpenMC'nin "
                           "zenginlik kısayolu %97'nin üstünde tanımsızdır.")},
    "gozeneklilik": {"etiket": N_("Gözeneklilik"), "en_az": 0.0, "en_cok": 0.3,
                     "ondalik": 3, "adim": 0.01, "sonek": "",
                     "ipucu": N_("Yakıt tabakasındaki boşluk hacim kesri (0–0.3). Yoğunluk, "
                              "U yüklemesi ve bu değerden hesaplanır: U₃Si₂ (12.2 g/cm³) + "
                              "Al (2.70 g/cm³).")},
    "yogunluk": {"etiket": N_("Yoğunluk"), "en_az": 0.01, "en_cok": 30.0,
                 "ondalik": 4, "adim": 0.01, "sonek": "g/cm³"},
    "sicaklik": {"etiket": N_("Sıcaklık"), "tur": "sicaklik", "en_az": 250.0,
                 "en_cok": 3000.0, "ondalik": 2, "adim": 10.0, "sonek": "K",
                 "ipucu": N_("Tesir kesiti verisi bu sıcaklıkta kullanılır.")},
    "bor_ppm": {"etiket": N_("Çözünmüş bor [ppm]"), "en_az": 0.0, "en_cok": 5000.0,
                "ondalik": 0, "adim": 50.0, "sonek": "",
                "ipucu": N_("Suda çözünmüş doğal borun ağırlıkça ppm'i (PWR kimyasal kontrolü).")},
    "pu_orani": {"etiket": N_("Pu ağırlıkça %"), "en_az": 0.01,
                 "en_cok": 100.0, "ondalik": 2, "adim": 0.5, "sonek": "%",
                 "ipucu": N_("Ağır metal (U + Pu) içindeki plütonyumun ağırlık yüzdesi.")},
    "pu_fissil": {"etiket": N_("Fisil Pu %"), "en_az": 0.0,
                  "en_cok": 100.0, "ondalik": 1, "adim": 1.0, "sonek": "%",
                  "ipucu": N_("Plütonyum içindeki Pu-239 + Pu-241 ağırlık yüzdesi; "
                           "kalanı Pu-240 ve Pu-242.")},
    "u_zenginlik": {"etiket": N_("Taşıyıcı U'da U-235 %"), "en_az": 0.01,
                    "en_cok": 97.0, "ondalik": 2, "adim": 0.05, "sonek": "%",
                    "ipucu": N_("MOX'taki uranyumun (çoğunlukla fakir U) U-235 ağırlık yüzdesi.")},
    "u_yukleme": {"etiket": N_("Uranyum yüklemesi"), "en_az": 0.1, "en_cok": 10.0,
                  "ondalik": 2, "adim": 0.1, "sonek": "gU/cm³"},
    "saflik": {"etiket": N_("D₂O saflığı (mol %)"), "en_az": 50.0, "en_cok": 100.0,
               "ondalik": 2, "adim": 0.05, "sonek": "%"},
    "b10_zenginlik": {"etiket": N_("B-10 atomca %"), "tur": "dogal_ya_da",
                      "en_az": 0.0, "en_cok": 100.0, "ondalik": 1, "adim": 1.0,
                      "sonek": "%", "dogal_metin": N_("doğal bor (%19.9)"),
                      "ipucu": N_("En küçük değer doğal bor demektir.")},
}

# Anahtar -> okunur ad, tek cumle aciklama, formda sorulan parametreler
# (SIRAYLA). Bir parametre (ad, {ezme}) olarak verilirse ortak tanim ezilir.
# Katalog sirasi listede grup ICI siradir.
_SICAK_SU = ("sicaklik", {"en_az": 273.15, "en_cok": 623.15,
                          "ipucu": N_("Yoğunluk bu sıcaklıktaki doymuş sıvı sudan "
                                   "hesaplanır (273–623 K).")})
KATALOG = {
    "uo2": (N_("UO₂ — uranyum dioksit"), N_("Hafif su reaktörlerinin seramik yakıtı."),
            ["zenginlik", "yogunluk", "sicaklik"]),
    "mox": (N_("MOX — karışık oksit (U, Pu)O₂"), N_("Plütonyumlu seramik yakıt; basitleştirilmiş Pu vektörü."),
            ["pu_orani", "pu_fissil", "u_zenginlik", "yogunluk", "sicaklik"]),
    "un": (N_("UN — uranyum nitrür"), N_("Yüksek yoğunluklu seramik yakıt."),
           ["zenginlik", "yogunluk", "sicaklik"]),
    "u10mo": (N_("U-10Mo — metalik uranyum alaşımı"), N_("Ağırlıkça %10 molibdenli metalik yakıt."),
              ["zenginlik", "yogunluk", "sicaklik"]),
    "u3si2_al": (N_("U₃Si₂-Al — dispersiyon yakıtı"), N_("MTR tipi araştırma reaktörü plakalarının yakıt tabakası."),
                 ["u_yukleme", "zenginlik", "gozeneklilik", "sicaklik"]),
    "zirkaloy4": (N_("Zircaloy-4"), N_("Hafif su reaktörü yakıt zarfı."), ["yogunluk", "sicaklik"]),
    "ss316": (N_("SS-316 paslanmaz çelik"), N_("Hızlı reaktör zarfı ve yapısal malzeme."),
              ["yogunluk", "sicaklik"]),
    "fecral": (N_("FeCrAl"), N_("Kazaya dayanıklı yakıt zarfı."), ["yogunluk", "sicaklik"]),
    "ma956": (N_("MA956 — ODS FeCrAl"), N_("Yüksek sıcaklık zarf alaşımı."), ["yogunluk", "sicaklik"]),
    "sic": (N_("SiC — silisyum karbür"), N_("Seramik zarf / yapısal malzeme."), ["yogunluk", "sicaklik"]),
    "al6061": (N_("Al-6061 alüminyum"), N_("Araştırma reaktörü plaka zarfı ve yapısı."),
               ["yogunluk", "sicaklik"]),
    "su": (N_("Hafif su (H₂O)"), N_("Soğutucu ve moderatör; yoğunluk sıcaklıktan hesaplanır."),
           [_SICAK_SU, "bor_ppm"]),
    "agir_su": (N_("Ağır su (D₂O)"), N_("Moderatör; kalanı hafif sudur."),
                ["saflik", ("yogunluk", {"en_az": 0.5, "en_cok": 1.2}),
                 ("sicaklik", {"en_az": 276.97, "en_cok": 640.0})]),
    "sodyum": (N_("Sıvı sodyum (Na)"), N_("Hızlı reaktör soğutucusu; yoğunluk sıcaklıktan hesaplanır."),
               [("sicaklik", {"en_az": 371.0, "en_cok": 1200.0})]),
    "lbe": (N_("Kurşun-bizmut ötektiği (LBE)"), N_("Hızlı reaktör soğutucusu; yoğunluk sıcaklıktan hesaplanır."),
            [("sicaklik", {"en_az": 400.0, "en_cok": 1300.0})]),
    "grafit": (N_("Grafit (C)"), N_("Moderatör ve yansıtıcı."), ["yogunluk", "sicaklik"]),
    "berilyum": (N_("Berilyum (Be)"), N_("Yansıtıcı ve moderatör."), ["yogunluk", "sicaklik"]),
    "b4c": (N_("B₄C — bor karbür"), N_("Kontrol çubuğu ve tambur emicisi."),
            ["b10_zenginlik", "yogunluk", "sicaklik"]),
    "agincd": (N_("Ag-In-Cd"), N_("PWR kontrol çubuğu alaşımı."), ["yogunluk", "sicaklik"]),
    "gd2o3": (N_("Gd₂O₃ — gadolinyum oksit"), N_("Yanabilir zehir."), ["yogunluk", "sicaklik"]),
    "helyum": (N_("Helyum (He)"), N_("Yakıt-zarf aralığı dolgu gazı."),
               [("yogunluk", {"en_az": 1.0e-7, "en_cok": 0.01, "ondalik": 7,
                              "adim": 1.0e-5}),
                ("sicaklik", {"en_cok": 2000.0})]),
}

# Yogunlugu SICAKLIKTAN hesaplayan malzemeler: yogunluk sorulmaz, formda
# hesaplanan deger gosterilir (fonksiyon yogunluk=None ile cagrilir).
SICAKLIKTAN_YOGUNLUK = ("su", "lbe", "sodyum")


def okunur_ad(anahtar):
    """Kutuphane anahtarinin gorunen adi ("uo2" -> "UO₂ — uranyum dioksit")."""
    k = KATALOG.get(anahtar)
    return _(k[0]) if k else anahtar


def katalog_aciklamasi(anahtar):
    """Kutuphane anahtarinin tek cumle aciklamasi, etkin dilde."""
    k = KATALOG.get(anahtar)
    return _(k[1]) if k else ""


def varsayilan_parametreler(anahtar):
    """Fonksiyon imzasindaki varsayilanlar (formdaki parametreler icin)."""
    import inspect
    imza = inspect.signature(KUTUPHANE[anahtar][0]).parameters
    return {p["ad"]: imza[p["ad"]].default for p in parametreler(anahtar)}


def parametreler(anahtar):
    """
    Formda sorulan parametreler, SIRAYLA: [{"ad", "etiket", "tur", "en_az",
    "en_cok", "ondalik", "adim", "sonek", "ipucu", "varsayilan"}, ...].
    Varsayilanlar FONKSIYON IMZASINDAN okunur (tek kaynak).
    """
    import inspect
    imza = inspect.signature(KUTUPHANE[anahtar][0]).parameters
    cikti = []
    for oge in KATALOG[anahtar][2]:
        ad, ezme = (oge, {}) if isinstance(oge, str) else oge
        p = {"tur": "sayi", "ipucu": "", "dogal_metin": ""}
        p.update(_PARAM[ad])
        p.update(ezme)
        p["ad"] = ad
        p["varsayilan"] = imza[ad].default
        for alan in ("etiket", "ipucu", "dogal_metin"):     # gorunen metin: etkin dilde
            if p.get(alan):
                p[alan] = _(p[alan])
        cikti.append(p)
    return cikti


def parametrik_uret(anahtar, param=None):
    """
    Kutuphaneden malzeme uretir ve uretim parametrelerini m["kutup"]'a yazar.
    param: {arguman: deger}; verilmeyenler fonksiyon varsayilanidir.
    """
    param = dict(param or {})
    m = uret(anahtar, **param)
    m["kutup"] = {"anahtar": anahtar, "param": param}
    return m


def yeniden_uret(m):
    """
    m["kutup"] kaydindan malzemeyi yeniden uretir (yeni sozluk; "ad" ve
    "renk" m'den korunur). Kayit yoksa ya da gecersizse None.
    """
    k = m.get("kutup") if isinstance(m, dict) else None
    if not isinstance(k, dict) or k.get("anahtar") not in KUTUPHANE:
        return None
    param = k.get("param") or {}
    if not isinstance(param, dict):
        return None
    try:
        yeni = parametrik_uret(k["anahtar"], param)
    except (TypeError, ValueError):
        return None
    yeni["ad"] = m.get("ad", yeni["ad"])
    if m.get("renk"):
        yeni["renk"] = list(m["renk"])
    return yeni


def parametrik_mi(m):
    """
    Malzeme kutuphane parametrelerinden uretilmis VE o zamandan beri elle
    degistirilmemis mi? (yeniden uretim FIZIK_ALANLARI'nda birebir ayni)
    """
    yeni = yeniden_uret(m)
    if yeni is None:
        return False
    return all(yeni.get(a) == m.get(a) for a in FIZIK_ALANLARI)




def parametre_uyarilari(anahtar, param):
    """
    Parametreler gecerli ama fiziksel olarak supheli ise kisa uyari metinleri
    (arayuz formun altinda gosterir; malzemeyi DEGISTIRMEZ).
    """
    uyari = []
    p = dict(varsayilan_parametreler(anahtar)) if anahtar in KATALOG else {}
    p.update(param or {})
    for ad in ("zenginlik", "u_zenginlik"):
        z = p.get(ad)
        # dogrula %5 ustunu zaten uyarir; formda yalnizca HEU (> %20) icin
        # soylenir -- HALEU (%19.75) yakitlarda her seferinde uyari gurultu olur.
        if z is not None and z > 20.0:
            uyari.append(_("Zenginlik %%%.2f: OpenMC'nin zenginlik kısayolu U-234 "
                           "oranını sabit varsayar; yüksek zenginlikte izotopları "
                           "elle vermek daha doğrudur.") % z)
            break
    if anahtar == "u3si2_al":
        u = float(p.get("u_yukleme") or 0.0)
        gz = float(p.get("gozeneklilik") or 0.0)
        try:
            beklenen = u3si2_yogunlugu(u, gz)
        except ValueError as e:
            uyari.append(str(e))
            beklenen = None
        yog = p.get("yogunluk")
        if beklenen is not None and yog is not None and abs(float(yog) / beklenen - 1.0) > 0.10:
            uyari.append(_("Bu yüklemede U₃Si₂ (%.1f g/cm³) ile Al (%.2f g/cm³) "
                           "karışımının yoğunluğu ≈ %.2f g/cm³; girilen %.2f g/cm³.")
                         % (_U3SI2_YOGUNLUK, _AL_YOGUNLUK, beklenen, float(yog)))
    return uyari
