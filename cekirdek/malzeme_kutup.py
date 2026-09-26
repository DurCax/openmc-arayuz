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
    "uo2": (uo2, "UO2 -- zenginlik parametreli uranyum dioksit"),
    "un": (un, "UN -- uranyum nitrür"),
    "u10mo": (u10mo, "U-10Mo -- metalik alaşım yakıt"),
    "mox": (mox, "MOX -- karışık oksit"),
    "u3si2_al": (u3si2_al, "U3Si2-Al -- MTR dispersiyon yakıtı"),
    # zarf / yapisal
    "zirkaloy4": (zirkaloy4, "Zircaloy-4 zarf"),
    "ss316": (ss316, "AISI 316 paslanmaz çelik"),
    "ma956": (ma956, "MA956 ODS FeCrAl"),
    "fecral": (fecral, "FeCrAl kazaya dayanıklı zarf"),
    "sic": (sic, "Silisyum karbür"),
    "al6061": (al6061, "Al-6061 plaka zarfı"),
    # sogutucu / moderator
    "su": (su, "Hafif su (S(α,β) dahil, sıcaklığa bağlı yoğunluk)"),
    "agir_su": (agir_su, "Ağır su D2O"),
    "lbe": (lbe, "Kurşun-bizmut ötektiği"),
    "sodyum": (sodyum, "Sıvı sodyum"),
    "helyum": (helyum, "Helyum dolgu gazı"),
    "grafit": (grafit, "Grafit yansıtıcı/moderatör"),
    "berilyum": (berilyum, "Berilyum yansıtıcı"),
    # emiciler
    "b4c": (b4c, "Bor karbür"),
    "gd2o3": (gd2o3, "Gadolinyum oksit yanabilir zehir"),
    "agincd": (agincd, "Ag-In-Cd kontrol alaşımı"),
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
    "zenginlik": {"etiket": "U-235 ağırlıkça %", "en_az": 0.01, "en_cok": 97.0,
                  "ondalik": 2, "adim": 0.1, "sonek": "%",
                  "ipucu": "U-235'in uranyum içindeki ağırlık yüzdesi. OpenMC'nin "
                           "zenginlik kısayolu %97'nin üstünde tanımsızdır."},
    "yogunluk": {"etiket": "Yoğunluk", "en_az": 0.01, "en_cok": 30.0,
                 "ondalik": 4, "adim": 0.01, "sonek": "g/cm³"},
    "sicaklik": {"etiket": "Sıcaklık", "tur": "sicaklik", "en_az": 250.0,
                 "en_cok": 3000.0, "ondalik": 2, "adim": 10.0, "sonek": "K",
                 "ipucu": "Tesir kesiti verisi bu sıcaklıkta kullanılır."},
    "bor_ppm": {"etiket": "Çözünmüş bor [ppm]", "en_az": 0.0, "en_cok": 5000.0,
                "ondalik": 0, "adim": 50.0, "sonek": "",
                "ipucu": "Suda çözünmüş doğal borun ağırlıkça ppm'i (PWR kimyasal kontrolü)."},
    "pu_orani": {"etiket": "Pu ağırlıkça %", "en_az": 0.01,
                 "en_cok": 100.0, "ondalik": 2, "adim": 0.5, "sonek": "%",
                 "ipucu": "Ağır metal (U + Pu) içindeki plütonyumun ağırlık yüzdesi."},
    "pu_fissil": {"etiket": "Fisil Pu %", "en_az": 0.0,
                  "en_cok": 100.0, "ondalik": 1, "adim": 1.0, "sonek": "%",
                  "ipucu": "Plütonyum içindeki Pu-239 + Pu-241 ağırlık yüzdesi; "
                           "kalanı Pu-240 ve Pu-242."},
    "u_zenginlik": {"etiket": "Taşıyıcı U'da U-235 %", "en_az": 0.01,
                    "en_cok": 97.0, "ondalik": 2, "adim": 0.05, "sonek": "%",
                    "ipucu": "MOX'taki uranyumun (çoğunlukla fakir U) U-235 ağırlık yüzdesi."},
    "u_yukleme": {"etiket": "Uranyum yüklemesi", "en_az": 0.1, "en_cok": 10.0,
                  "ondalik": 2, "adim": 0.1, "sonek": "gU/cm³"},
    "saflik": {"etiket": "D₂O saflığı (mol %)", "en_az": 50.0, "en_cok": 100.0,
               "ondalik": 2, "adim": 0.05, "sonek": "%"},
    "b10_zenginlik": {"etiket": "B-10 atomca %", "tur": "dogal_ya_da",
                      "en_az": 0.0, "en_cok": 100.0, "ondalik": 1, "adim": 1.0,
                      "sonek": "%", "dogal_metin": "doğal bor (%19.9)",
                      "ipucu": "En küçük değer doğal bor demektir."},
}

# Anahtar -> okunur ad, tek cumle aciklama, formda sorulan parametreler
# (SIRAYLA). Bir parametre (ad, {ezme}) olarak verilirse ortak tanim ezilir.
# Katalog sirasi listede grup ICI siradir.
_SICAK_SU = ("sicaklik", {"en_az": 273.15, "en_cok": 623.15,
                          "ipucu": "Yoğunluk bu sıcaklıktaki doymuş sıvı sudan "
                                   "hesaplanır (273-623 K)."})
KATALOG = {
    "uo2": ("UO₂ — uranyum dioksit", "Hafif su reaktörlerinin seramik yakıtı.",
            ["zenginlik", "yogunluk", "sicaklik"]),
    "mox": ("MOX — karışık oksit (U, Pu)O₂", "Plütonyumlu seramik yakıt; basitleştirilmiş Pu vektörü.",
            ["pu_orani", "pu_fissil", "u_zenginlik", "yogunluk", "sicaklik"]),
    "un": ("UN — uranyum nitrür", "Yüksek yoğunluklu seramik yakıt.",
           ["zenginlik", "yogunluk", "sicaklik"]),
    "u10mo": ("U-10Mo — metalik uranyum alaşımı", "Ağırlıkça %10 molibdenli metalik yakıt.",
              ["zenginlik", "yogunluk", "sicaklik"]),
    "u3si2_al": ("U₃Si₂-Al — dispersiyon yakıtı", "MTR tipi araştırma reaktörü plakalarının yakıt tabakası.",
                 ["u_yukleme", "zenginlik", "yogunluk", "sicaklik"]),
    "zirkaloy4": ("Zircaloy-4", "Hafif su reaktörü yakıt zarfı.", ["yogunluk", "sicaklik"]),
    "ss316": ("SS-316 paslanmaz çelik", "Hızlı reaktör zarfı ve yapısal malzeme.",
              ["yogunluk", "sicaklik"]),
    "fecral": ("FeCrAl", "Kazaya dayanıklı yakıt zarfı.", ["yogunluk", "sicaklik"]),
    "ma956": ("MA956 — ODS FeCrAl", "Yüksek sıcaklık zarf alaşımı.", ["yogunluk", "sicaklik"]),
    "sic": ("SiC — silisyum karbür", "Seramik zarf / yapısal malzeme.", ["yogunluk", "sicaklik"]),
    "al6061": ("Al-6061 alüminyum", "Araştırma reaktörü plaka zarfı ve yapısı.",
               ["yogunluk", "sicaklik"]),
    "su": ("Hafif su (H₂O)", "Soğutucu ve moderatör; yoğunluk sıcaklıktan hesaplanır.",
           [_SICAK_SU, "bor_ppm"]),
    "agir_su": ("Ağır su (D₂O)", "Moderatör; kalanı hafif sudur.",
                ["saflik", ("yogunluk", {"en_az": 0.5, "en_cok": 1.2}),
                 ("sicaklik", {"en_az": 276.97, "en_cok": 640.0})]),
    "sodyum": ("Sıvı sodyum (Na)", "Hızlı reaktör soğutucusu; yoğunluk sıcaklıktan hesaplanır.",
               [("sicaklik", {"en_az": 371.0, "en_cok": 1200.0})]),
    "lbe": ("Kurşun-bizmut ötektiği (LBE)", "Hızlı reaktör soğutucusu; yoğunluk sıcaklıktan hesaplanır.",
            [("sicaklik", {"en_az": 400.0, "en_cok": 1300.0})]),
    "grafit": ("Grafit (C)", "Moderatör ve yansıtıcı.", ["yogunluk", "sicaklik"]),
    "berilyum": ("Berilyum (Be)", "Yansıtıcı ve moderatör.", ["yogunluk", "sicaklik"]),
    "b4c": ("B₄C — bor karbür", "Kontrol çubuğu ve tambur emicisi.",
            ["b10_zenginlik", "yogunluk", "sicaklik"]),
    "agincd": ("Ag-In-Cd", "PWR kontrol çubuğu alaşımı.", ["yogunluk", "sicaklik"]),
    "gd2o3": ("Gd₂O₃ — gadolinyum oksit", "Yanabilir zehir.", ["yogunluk", "sicaklik"]),
    "helyum": ("Helyum (He)", "Yakıt-zarf aralığı dolgu gazı.",
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
    return k[0] if k else anahtar


def katalog_aciklamasi(anahtar):
    k = KATALOG.get(anahtar)
    return k[1] if k else ""


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


# U3Si2 kuramsal yogunlugu ve Al yogunlugu [g/cm3] -- dispersiyon tutarlilik uyarisi
_U3SI2_YOGUNLUK = 12.2
_AL_YOGUNLUK = 2.70


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
            uyari.append("Zenginlik %%%.2f: OpenMC'nin zenginlik kısayolu U-234 "
                         "oranını sabit varsayar; yüksek zenginlikte izotopları "
                         "elle vermek daha doğrudur." % z)
            break
    if anahtar == "u3si2_al":
        u = float(p.get("u_yukleme") or 0.0)
        yog = float(p.get("yogunluk") or 0.0)
        kutle = u / 0.9271
        if yog <= kutle:
            uyari.append("Yoğunluk (%.2f g/cm³) U₃Si₂ kütlesinden (%.2f g/cm³) "
                         "küçük: alüminyum payı sıfıra iner." % (yog, kutle))
        else:
            beklenen = kutle + (1.0 - kutle / _U3SI2_YOGUNLUK) * _AL_YOGUNLUK
            if abs(yog / beklenen - 1.0) > 0.10:
                uyari.append("Bu yüklemede U₃Si₂ (%.1f g/cm³) ile Al (%.2f g/cm³) "
                             "karışımının yoğunluğu ≈ %.2f g/cm³; girilen %.2f g/cm³."
                             % (_U3SI2_YOGUNLUK, _AL_YOGUNLUK, beklenen, yog))
    return uyari
