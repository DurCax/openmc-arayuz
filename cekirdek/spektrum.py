# -*- coding: utf-8 -*-
"""
================================================================================
 spektrum.py  --  enerji spektrumu, dort faktor (eps, p, f, eta), spektral indeksler
================================================================================
 Ayar: spec["ayarlar"]["spektrum"] = {"var": bool, "grup_yapisi": "XMAS-172"}
 (alan yoksa kapali). Acikken kurucu.kur ve uretilen betik AYNI tally
 tanimlarini (tally_tanimlari) kurar: kurucu -> tally_ekle, betik ->
 kod_uret/spektrum.py. Sonuc statepoint'ten oku() ile okunur.

 TERMAL KESIM  E_c = 0.625 eV
   OpenMC'nin resmi "tally arithmetic" ornegi (openmc-notebooks,
   tally-arithmetic.ipynb) dort/alti faktoru EnergyFilter([0, 0.625]) ile
   hesaplar; CASMO-2 iki grup siniri ve CSEWG TRX kafes olcumlerinin kadmiyum
   kesimi de 0.625 eV'tur. Kesim degisirse faktorlerin hepsi degisir (tanim
   geregi): yalniz carpim kesimden bagimsizdir.

 DORT FAKTOR (OpenMC ornegi ile birebir; ders kitabi: Lamarsh & Baratta,
 Introduction to Nuclear Engineering, Bol. 6; Duderstadt & Hamilton, Nuclear
 Reactor Analysis, 1976 -- notron yasam dongusu / dort faktor formulu)
   eps = nuF / nuF_th                 hizli fisyon carpani
   p   = A_th / A                     rezonanstan kacma olasiligi
   f   = A_yakit,th / A_th            termal yararlanma (yakit = fisil malzemeler)
   eta = nuF_th / A_yakit,th          yakitta termal sogurma basina notron
   (nuF: nu-fission, A: absorption, _th: E < E_c, hacim ve tum malzemeler)
   Carpim cebirsel olarak  eps*p*f*eta = nuF / A  (ara tally'ler sadelesir).

 SIZINTISIZ VARSAYIM VE DUZELTMELER
   Ornekteki p tanimi termal sizintiyi de icerir: (A_th + L_th)/(A + L_th).
   Burada termal sizinti tally'si YOKTUR; p = A_th / A sizintisiz (k-sonsuz)
   tanimidir. Sizinti varsa (vakum siniri) toplam sizinti L statepoint'in
   global "leakage" tally'sinden alinir ve TEK carpan olarak verilir:
       P_NL = P_FNL * P_TNL = (A - X) / (A - X + L)
   P_FNL ve P_TNL'yi AYRI vermek enerjiye bagli sizinti (yuzey akimi) ister;
   kapsam disi, etiketlenir.
   OpenMC'de "absorption" (n,xn) ile dogan notronlari saymaz; net uretim
   X = (n,2n) + 2(n,3n) + 3(n,4n). Bu yuzden
       c_xn = A / (A - X)       ve   k = eps*p*f*eta * c_xn * P_NL = nuF/(A - X + L)
   Sizintisiz modelde k = k-sonsuz (test: testler/test_y3_spektrum.py).

 SPEKTRAL INDEKSLER (CSEWG benchmark tanimlari -- BNL-19302 / ENDF-202; TRX-1,2
 kafesleri; ENDF/B-VII.0 dogrulamasi: Chadwick vd., Nucl. Data Sheets 107, 2006)
   rho28   = U-238 yakalama, epitermal / termal
   delta25 = U-235 fisyon,  epitermal / termal
   delta28 = U-238 fisyon / U-235 fisyon
   C*      = U-238 yakalama / U-235 fisyon
   Deneyde merkez cubukta olculur; burada TUM yakit malzemelerinin
   ortalamasidir (etiketlenir).

 BELIRSIZLIK (birinci derece, KORELASYON YOK SAYILIR)
   r = a/b:  (s_r/r)^2 = (s_a/a)^2 + (s_b/b)^2;  a +- b:  s^2 = s_a^2 + s_b^2.
   Pay paydanin alt kumesi oldugunda (p, f ...) gercek korelasyon pozitiftir ve
   bu yaklasim belirsizligi BUYUK tahmin eder (ihtiyatli). OpenMC tally
   aritmetigi de ayni varsayimi kullanir.
================================================================================
"""

import math
from typing import NamedTuple

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from cekirdek.tukenme_spektrum import _fisil_mi

_log = kaydedici(__name__)

TERMAL_KESIM_EV = 0.625       # gerekce: modul belgesi (OpenMC ornegi, CASMO-2, CSEWG)
# Indeks tally'sinin ust siniri: tum notron kutuphanelerinin azami enerjisinin
# (ENDF/B-VIII.0 en cok 150 MeV, TENDL 200 MeV) uzerinde; hicbir olay disarida kalmaz.
UST_SINIR_EV = 1.0e9
# Sunulan grup yapilari (openmc.mgxs.GROUP_STRUCTURES adlari) -> grup sayisi
GRUP_YAPILARI = {"CASMO-70": 70, "XMAS-172": 172, "SHEM-361": 361, "CCFE-709": 709}
VARSAYILAN_GRUP = "XMAS-172"
INDEKS_NUKLIDLERI = ("U235", "U238")

TALLY_ONEKI = "y3_"
T_TOPLAM = "y3_toplam"
T_TERMAL = "y3_termal"
T_YAKIT_TERMAL = "y3_yakit_termal"
T_INDEKS = "y3_indeks"
T_SPEKTRUM = "y3_spektrum"
T_SPEKTRUM_YAKIT = "y3_spektrum_yakit"
XN_SKORLARI = (("(n,2n)", 1), ("(n,3n)", 2), ("(n,4n)", 3))   # (skor, net ek notron)


class Deger(NamedTuple):
    """Ortalama ve 1 sigma standart sapma."""
    ort: float
    sapma: float


# ----------------------------------------------------------------------------
# ayar ve tally tanimlari
# ----------------------------------------------------------------------------

def ayar(spec: dict) -> dict:
    """spec["ayarlar"]["spektrum"] -> dogrulanmis YENI sozluk; bilinmeyen grup ValueError."""
    ham = ((spec or {}).get("ayarlar") or {}).get("spektrum") or {}
    grup = ham.get("grup_yapisi") or VARSAYILAN_GRUP
    if grup not in GRUP_YAPILARI:
        raise ValueError(_("bilinmeyen enerji grup yapısı: %s (geçerli: %s)")
                         % (grup, ", ".join(GRUP_YAPILARI)))
    return {"var": bool(ham.get("var")), "grup_yapisi": grup}


def etkin_mi(spec: dict) -> bool:
    return ayar(spec)["var"]


def yakit_malzemeleri(spec: dict) -> tuple:
    """Fisil nuklid iceren malzeme adlari (f ve eta'daki "yakit")."""
    return tuple(m["ad"] for m in spec.get("malzemeler", []) if _fisil_mi(m))


def _nuklid_var_mi(m: dict, nuklid: str) -> bool:
    for b in m.get("bilesim", []):
        if float(b.get("miktar") or 0) <= 0:
            continue
        isim = b.get("isim") or ""
        if isim == nuklid or (b.get("tur") != "nuklid" and isim == "U" and nuklid[0] == "U"):
            return True
    return False


def indeks_nuklidleri(spec: dict) -> tuple:
    """Spektral indeksler U-235 ve U-238'in IKISINI de ister; yoksa ()."""
    yakit = [m for m in spec.get("malzemeler", []) if m["ad"] in yakit_malzemeleri(spec)]
    if all(any(_nuklid_var_mi(m, n) for m in yakit) for n in INDEKS_NUKLIDLERI):
        return INDEKS_NUKLIDLERI
    return ()


def _tanim(ad, skorlar, enerji=None, malzemeler=None, nuklidler=(), grup_yapisi=None):
    return {"ad": ad, "skorlar": tuple(skorlar), "enerji": enerji,
            "malzemeler": malzemeler, "nuklidler": tuple(nuklidler),
            "grup_yapisi": grup_yapisi}


def tally_tanimlari(spec: dict) -> tuple:
    """Kurucu ve betigin ortak tally tanimlari (sira sabit); kapaliysa ()."""
    a = ayar(spec)
    if not a["var"]:
        return ()
    termal = (0.0, TERMAL_KESIM_EV)
    toplam_skor = ("nu-fission", "absorption") + tuple(s for s, _n in XN_SKORLARI)
    tanimlar = [_tanim(T_TOPLAM, toplam_skor),
                _tanim(T_TERMAL, ("nu-fission", "absorption"), enerji=termal),
                _tanim(T_SPEKTRUM, ("flux",), grup_yapisi=a["grup_yapisi"])]
    yakit = yakit_malzemeleri(spec)
    if yakit:
        tanimlar.append(_tanim(T_YAKIT_TERMAL, ("absorption",), enerji=termal, malzemeler=yakit))
        tanimlar.append(_tanim(T_SPEKTRUM_YAKIT, ("flux",), malzemeler=yakit,
                               grup_yapisi=a["grup_yapisi"]))
        nuk = indeks_nuklidleri(spec)
        if nuk:
            tanimlar.append(_tanim(T_INDEKS, ("fission", "(n,gamma)"), malzemeler=yakit,
                                   nuklidler=nuk,
                                   enerji=(0.0, TERMAL_KESIM_EV, UST_SINIR_EV)))
    return tuple(tanimlar)


def tally_ekle(spec: dict, model, nesneler: dict) -> tuple:
    """kurucu.kur kancasi: tanimlari openmc.Tally'ye cevirip modele ekler.
    DONER eklenen tally adlari."""
    tanimlar = tally_tanimlari(spec)
    if not tanimlar:
        return ()
    import openmc
    yeni = []
    for t in tanimlar:
        tal = openmc.Tally(name=t["ad"])
        tal.scores = list(t["skorlar"])
        if t["nuklidler"]:
            tal.nuclides = list(t["nuklidler"])
        filtreler = []
        if t["malzemeler"]:
            filtreler.append(openmc.MaterialFilter([nesneler[a] for a in t["malzemeler"]]))
        if t["grup_yapisi"]:
            filtreler.append(openmc.EnergyFilter.from_group_structure(t["grup_yapisi"]))
        elif t["enerji"]:
            filtreler.append(openmc.EnergyFilter(list(t["enerji"])))
        tal.filters = filtreler
        yeni.append(tal)
    model.tallies = openmc.Tallies(list(model.tallies) + yeni)
    return tuple(t["ad"] for t in tanimlar)


# ----------------------------------------------------------------------------
# saf hesaplar (birinci derece, korelasyonsuz belirsizlik)
# ----------------------------------------------------------------------------

def oran(a, b):
    """a / b; payda sifir/None ya da pay None ise None."""
    if a is None or b is None or b.ort == 0:
        return None
    r = a.ort / b.ort
    if a.ort == 0:
        return Deger(0.0, abs(a.sapma / b.ort))
    return Deger(r, abs(r) * math.hypot(a.sapma / a.ort, b.sapma / b.ort))


def fark(a, b):
    return Deger(a.ort - b.ort, math.hypot(a.sapma, b.sapma))


def toplam(a, b):
    return Deger(a.ort + b.ort, math.hypot(a.sapma, b.sapma))


def faktorleri_hesapla(h: dict) -> dict:
    """
    h: {"nF", "A", "X", "nF_th", "A_th", "A_yakit_th" (None: yakit yok), "L"} (Deger)
    DONER {"eps", "p", "f", "eta", "carpim", "c_xn", "p_nl", "k"} -- tanimsiz olan None.
    carpim = nF / A (eps*p*f*eta ozdesligi); sapmasi bu orandan (ara tally'ler
    sadelesir, dort ayri sapmanin birlesimi buyuk tahmin olurdu).
    """
    net = fark(h["A"], h["X"])
    payda = toplam(net, h["L"])
    termal_var = h["nF_th"].ort > 0 and h["A_th"].ort > 0
    sizintisiz = h["L"].ort == 0.0 and h["L"].sapma == 0.0
    yakit = h.get("A_yakit_th") if termal_var else None
    return {
        "eps": oran(h["nF"], h["nF_th"]) if termal_var else None,
        "p": oran(h["A_th"], h["A"]) if termal_var else None,
        "f": oran(yakit, h["A_th"]) if yakit else None,
        "eta": oran(h["nF_th"], yakit) if yakit else None,
        "carpim": oran(h["nF"], h["A"]),
        "c_xn": oran(h["A"], net),
        # Sizinti tam sifirsa (yansitici sinir) P_NL = 1 KESIN: ayni sayinin
        # kendine orani; korelasyonsuz formul burada sahte bir sapma uretirdi.
        "p_nl": Deger(1.0, 0.0) if sizintisiz else oran(net, payda),
        "k": oran(h["nF"], payda),
    }


def indeksleri_hesapla(d: dict) -> dict:
    """d: {"F25_th","F25_epi","F28_th","F28_epi","C28_th","C28_epi"} -> CSEWG indeksleri."""
    f25 = toplam(d["F25_th"], d["F25_epi"])
    return {
        "rho28": oran(d["C28_epi"], d["C28_th"]),
        "delta25": oran(d["F25_epi"], d["F25_th"]),
        "delta28": oran(toplam(d["F28_th"], d["F28_epi"]), f25),
        "C*": oran(toplam(d["C28_th"], d["C28_epi"]), f25),
    }


def letarji_basina(kenarlar, aki, sapma):
    """
    Grup akisi phi_g -> letarji basina phi_g / ln(E_g,ust / E_g,alt).
    Alt kenari 0 olan grup (letarji sonsuz) atlanir.
    DONER (kenarlar, deger, sapma) -- numpy dizileri; len(kenarlar) = len(deger) + 1.
    """
    import numpy as np
    e = np.asarray(kenarlar, dtype=float)
    phi, s = np.asarray(aki, dtype=float), np.asarray(sapma, dtype=float)
    ilk = int(np.argmax(e > 0.0))
    if e[ilk] <= 0.0:
        raise ValueError(_("enerji kenarlarının hepsi sıfır ya da negatif"))
    du = np.log(e[ilk + 1:] / e[ilk:-1])
    return e[ilk:], phi[ilk:] / du, s[ilk:] / du


# ----------------------------------------------------------------------------
# statepoint okuma
# ----------------------------------------------------------------------------

def _satir_degeri(df, **kosul):
    """Kosula uyan satirlarin toplami; sapmalar karesel toplanir (korelasyonsuz)."""
    sat = df
    for sutun, deger in kosul.items():
        sat = sat[sat[sutun] == deger]
    if sat.empty:
        return Deger(0.0, 0.0)
    return Deger(float(sat["mean"].sum()), math.sqrt(float((sat["std. dev."] ** 2).sum())))


def _tally_df(sp, ad):
    try:
        return sp.get_tally(name=ad).get_pandas_dataframe()
    except LookupError:
        _log.debug("'%s' tally'si statepoint'te yok", ad)
        return None


def _global_sizinti(sp):
    for satir in sp.global_tallies:
        if satir["name"] in (b"leakage", "leakage"):
            return Deger(float(satir["mean"]), float(satir["std_dev"]))
    _log.warning("statepoint'te global 'leakage' tally'si yok; sızıntı 0 sayıldı")
    return Deger(0.0, 0.0)


def _hizlar_oku(sp, toplam_df, termal_df):
    hiz = {"nF": _satir_degeri(toplam_df, score="nu-fission"),
           "A": _satir_degeri(toplam_df, score="absorption"),
           "nF_th": _satir_degeri(termal_df, score="nu-fission"),
           "A_th": _satir_degeri(termal_df, score="absorption"),
           "L": _global_sizinti(sp)}
    x = Deger(0.0, 0.0)
    for skor, carpan in XN_SKORLARI:
        d = _satir_degeri(toplam_df, score=skor)
        x = toplam(x, Deger(carpan * d.ort, carpan * d.sapma))
    hiz["X"] = x
    yakit = _tally_df(sp, T_YAKIT_TERMAL)
    hiz["A_yakit_th"] = _satir_degeri(yakit, score="absorption") if yakit is not None else None
    return hiz


def _indeksler_oku(sp):
    df = _tally_df(sp, T_INDEKS)
    if df is None:
        return None
    eb = "energy low [eV]"
    d = {}
    for kisa, nuk, skor in (("F25", "U235", "fission"), ("F28", "U238", "fission"),
                            ("C28", "U238", "(n,gamma)")):
        d[kisa + "_th"] = _satir_degeri(df, nuclide=nuk, score=skor, **{eb: 0.0})
        d[kisa + "_epi"] = _satir_degeri(df, nuclide=nuk, score=skor, **{eb: TERMAL_KESIM_EV})
    return indeksleri_hesapla(d)


def _spektrum_oku(sp):
    import openmc
    sonuc = {}
    for anahtar, ad in (("model", T_SPEKTRUM), ("yakit", T_SPEKTRUM_YAKIT)):
        try:
            tal = sp.get_tally(name=ad)
        except LookupError:
            continue
        kenar = tal.find_filter(openmc.EnergyFilter).values
        sonuc[anahtar] = (tal.mean.ravel().copy(), tal.std_dev.ravel().copy())
        sonuc["kenarlar"] = kenar.copy()
    return sonuc


def oku(statepoint) -> dict | None:
    """
    Statepoint yolundan (ya da openmc.StatePoint'ten) Y3 sonuclari; Y3 tally'si
    yoksa None. DONER {"faktorler" (ozdeger degilse None), "indeksler" | None,
    "spektrum": {"kenarlar", "model": (aki, sapma), "yakit": ...},
    "keff" | None, "sizinti", "termal_fisyon_payi", "termal_kesim"}.
    """
    import openmc
    sp = statepoint if hasattr(statepoint, "get_tally") else openmc.StatePoint(statepoint)
    toplam_df, termal_df = _tally_df(sp, T_TOPLAM), _tally_df(sp, T_TERMAL)
    if toplam_df is None or termal_df is None:
        return None
    hiz = _hizlar_oku(sp, toplam_df, termal_df)
    ozdeger = sp.run_mode == "eigenvalue"
    keff = Deger(float(sp.keff.nominal_value), float(sp.keff.std_dev)) if ozdeger else None
    pay = oran(hiz["nF_th"], hiz["nF"])
    return {"faktorler": faktorleri_hesapla(hiz) if ozdeger else None,
            "indeksler": _indeksler_oku(sp),
            "spektrum": _spektrum_oku(sp),
            "keff": keff,
            "sizinti": hiz["L"],
            "termal_fisyon_payi": pay.ort if pay else 0.0,
            "termal_kesim": TERMAL_KESIM_EV}
