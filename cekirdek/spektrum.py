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
   hesaplar; CASMO-2 iki grup siniri da 0.625 eV'tur. CSEWG/ENDF-202 TRX
   hesaplarinda 0.625 eV HESAP kesimidir; deneydeki etkin kadmiyum kesimi
   kadmiyum kalinligina baglidir (~0.4-0.5 eV). Kesim degisirse faktorlerin
   hepsi degisir (tanim geregi): yalniz carpim kesimden bagimsizdir.

 DORT FAKTOR (OpenMC ornegiyle SIZINTISIZ SINIRDA ayni; p farkli: ornegin p'si
 termal sizintiyi icerir. Ders kitabi: Lamarsh & Baratta, Introduction to
 Nuclear Engineering, Bol. 6; Duderstadt & Hamilton, Nuclear Reactor Analysis,
 1976). IKI GRUP TANIMI: ders kitabindaki eps yalniz hizli (U-238 esigi ustu)
 fisyonu sayar (tipik 1.02-1.08); burada "hizli" = E > 0.625 eV oldugundan eps
 epitermal/rezonans U-235 fisyonunu da icerir (LWR pin ~1.2) ve p buna karsilik
 kucuktur. Carpim ayni kalir.
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
   X = sum (x-1) R_x, XN_SKORLARI'ndaki kanallar: MT 11, 16, 17, 24, 25, 30,
   37, 41, 42. Daha yuksek kanallar (MT 152+; (n,5n) ...) SAYILMAZ: yalniz
   yuksek enerjili (TENDL turu) degerlendirmelerde vardir. Bu yuzden
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
from typing import NamedTuple, Optional

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from cekirdek.tukenme_spektrum import fisil_mi

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
# (skor, net ek notron x-1): OpenMC "absorption"inin disinda kalan, notron
# ureten kanallar (openmc.data.REACTION_NAME; MT 11, 16, 17, 24, 25, 30, 37, 41, 42)
XN_SKORLARI = (("(n,2nd)", 1), ("(n,2n)", 1), ("(n,3n)", 2), ("(n,2na)", 1),
               ("(n,3na)", 2), ("(n,2n2a)", 1), ("(n,4n)", 3), ("(n,2np)", 1),
               ("(n,3np)", 2))


class Deger(NamedTuple):
    """Ortalama ve 1 sigma standart sapma."""
    ort: float
    sapma: float


# ----------------------------------------------------------------------------
# ayar ve tally tanimlari
# ----------------------------------------------------------------------------

def ayar(spec: dict) -> dict:
    """
    spec["ayarlar"]["spektrum"] -> dogrulanmis YENI sozluk {"var", "grup_yapisi"}.
    Alan sozluk degilse kapali varsayilan. Acikken bilinmeyen grup ValueError;
    kapaliyken grup kullanilmaz ve varsayilana duser (kosu etkilenmez).
    """
    ham = ((spec or {}).get("ayarlar") or {}).get("spektrum")
    if not isinstance(ham, dict):
        return {"var": False, "grup_yapisi": VARSAYILAN_GRUP}
    var = bool(ham.get("var"))
    grup = ham.get("grup_yapisi") or VARSAYILAN_GRUP
    if grup not in GRUP_YAPILARI:
        if var:
            raise ValueError(_("bilinmeyen enerji grup yapısı: %s (geçerli: %s)")
                             % (grup, ", ".join(GRUP_YAPILARI)))
        grup = VARSAYILAN_GRUP
    return {"var": var, "grup_yapisi": grup}


def kapali_kopya(spec: dict) -> dict:
    """Y3 kapali YENI spec (sig kopya; yalniz "ayarlar" yeni sozluk). Tukenme
    bunu kullanir: cubuk cubuk yanma malzemeleri klonlar ve MaterialFilter
    eski malzemeye bagli kalirdi."""
    ayarlar = dict(spec.get("ayarlar") or {})
    ayarlar["spektrum"] = {"var": False, "grup_yapisi": ayar(spec)["grup_yapisi"]}
    return dict(spec, ayarlar=ayarlar)


def tukenme_icin(spec: dict) -> dict:
    """Tukenme modeli icin spec: Y3 aciksa kapali kopya (loglanir; kullaniciya
    dogrula/spektrum.py bilgi bulgusu gosterir), degilse ayni spec."""
    if not ayar(spec)["var"]:
        return spec
    _log.warning("tükenme koşusunda spektrum/dört faktör tally'leri kapatıldı "
                 "(çubuk çubuk yanma malzemeleri klonlar)")
    return kapali_kopya(spec)


def etkin_mi(spec: dict) -> bool:
    return ayar(spec)["var"]


def yakit_malzemeleri(spec: dict) -> tuple:
    """Fisil nuklid iceren malzeme adlari (f ve eta'daki "yakit")."""
    return tuple(m["ad"] for m in spec.get("malzemeler", []) if fisil_mi(m))


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
    if yakit:            # bos demet: yakitsiz modelde f, eta ve indeks tally'si yok
        tanimlar.append(_tanim(T_YAKIT_TERMAL, ("absorption",), enerji=termal, malzemeler=yakit))
        tanimlar.append(_tanim(T_SPEKTRUM_YAKIT, ("flux",), malzemeler=yakit,
                               grup_yapisi=a["grup_yapisi"]))
        nuk = indeks_nuklidleri(spec)
        if nuk:
            tanimlar.append(_tanim(T_INDEKS, ("fission", "(n,gamma)"), malzemeler=yakit,
                                   nuklidler=nuk,
                                   enerji=(0.0, TERMAL_KESIM_EV, UST_SINIR_EV)))
    return tuple(tanimlar)


def tally_ekle(spec: dict, model: "openmc.Model", nesneler: dict) -> tuple:
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

def oran(a: Optional[Deger], b: Optional[Deger]) -> Optional[Deger]:
    """a / b; payda sifir/None ya da pay None ise None."""
    if a is None or b is None or b.ort == 0:
        return None
    r = a.ort / b.ort
    if a.ort == 0:
        return Deger(0.0, abs(a.sapma / b.ort))
    return Deger(r, abs(r) * math.hypot(a.sapma / a.ort, b.sapma / b.ort))


def fark(a: Optional[Deger], b: Optional[Deger]) -> Optional[Deger]:
    if a is None or b is None:
        return None
    return Deger(a.ort - b.ort, math.hypot(a.sapma, b.sapma))


def toplam(a: Optional[Deger], b: Optional[Deger]) -> Optional[Deger]:
    if a is None or b is None:
        return None
    return Deger(a.ort + b.ort, math.hypot(a.sapma, b.sapma))


def _pozitif(d: Optional[Deger]) -> bool:
    return d is not None and d.ort > 0


def faktorleri_hesapla(h: dict) -> dict:
    """
    h: {"nF", "A", "X", "nF_th", "A_th", "A_yakit_th", "L"} (Deger; None = okunamadi:
    A_yakit_th yakit yoksa, L global sizinti tally'si yoksa -- o zaman P_NL ve k None)
    DONER {"eps", "p", "f", "eta", "carpim", "c_xn", "p_nl", "k"} -- tanimsiz olan None.
    carpim = nF / A (eps*p*f*eta ozdesligi); sapmasi bu orandan (ara tally'ler
    sadelesir, dort ayri sapmanin birlesimi buyuk tahmin olurdu).
    """
    net = fark(h["A"], h["X"])
    payda = toplam(net, h["L"])
    termal_var = _pozitif(h["nF_th"]) and _pozitif(h["A_th"])
    sizintisiz = h["L"] is not None and h["L"].ort == 0.0 and h["L"].sapma == 0.0
    yakit = h.get("A_yakit_th") if termal_var else None
    return {
        "eps": oran(h["nF"], h["nF_th"]) if termal_var else None,
        "p": oran(h["A_th"], h["A"]) if termal_var else None,
        "f": oran(yakit, h["A_th"]) if yakit is not None else None,
        "eta": oran(h["nF_th"], yakit) if _pozitif(yakit) else None,
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

ZORUNLU_TALLYLER = (T_TOPLAM, T_TERMAL)      # faktorler icin; ikisi her zaman kurulur


def _satir_degeri(df, **kosul) -> Optional[Deger]:
    """Kosula uyan satirlarin toplami (sapmalar karesel, korelasyonsuz).
    Satir yoksa None (eksik skor/nuklid sessizce 0 SAYILMAZ; loglanir)."""
    sat = df
    for sutun, deger in kosul.items():
        if sutun not in sat.columns:
            _log.warning("Y3 tally'sinde '%s' sütunu yok (koşul %s)", sutun, kosul)
            return None
        sat = sat[sat[sutun] == deger]
    if sat.empty:
        _log.warning("Y3 tally'sinde %s satırı yok", kosul)
        return None
    return Deger(float(sat["mean"].sum()), math.sqrt(float((sat["std. dev."] ** 2).sum())))


def _tally_df(sp, ad):
    try:
        return sp.get_tally(name=ad).get_pandas_dataframe()
    except LookupError:
        _log.debug("'%s' tally'si statepoint'te yok", ad)
        return None


def _global_sizinti(sp) -> Optional[Deger]:
    """Global 'leakage' (kaynak notronu basina); yoksa None -- 0 SAYILMAZ."""
    for satir in sp.global_tallies:
        if satir["name"] in (b"leakage", "leakage"):
            return Deger(float(satir["mean"]), float(satir["std_dev"]))
    _log.warning("statepoint'te global 'leakage' tally'si yok; sızıntı bilinmiyor")
    return None


def _xn_uretimi(toplam_df) -> Optional[Deger]:
    x = Deger(0.0, 0.0)
    for skor, carpan in XN_SKORLARI:
        d = _satir_degeri(toplam_df, score=skor)
        if d is None:
            return None
        x = toplam(x, Deger(carpan * d.ort, carpan * d.sapma))
    return x


def _hizlar_oku(sp, toplam_df, termal_df) -> dict:
    yakit = _tally_df(sp, T_YAKIT_TERMAL)
    return {"nF": _satir_degeri(toplam_df, score="nu-fission"),
            "A": _satir_degeri(toplam_df, score="absorption"),
            "X": _xn_uretimi(toplam_df),
            "nF_th": _satir_degeri(termal_df, score="nu-fission"),
            "A_th": _satir_degeri(termal_df, score="absorption"),
            "A_yakit_th": _satir_degeri(yakit, score="absorption") if yakit is not None else None,
            "L": _global_sizinti(sp)}


def _indeksler_oku(sp) -> Optional[dict]:
    df = _tally_df(sp, T_INDEKS)
    if df is None:
        return None
    eb = "energy low [eV]"
    d = {}
    for kisa, nuk, skor in (("F25", "U235", "fission"), ("F28", "U238", "fission"),
                            ("C28", "U238", "(n,gamma)")):
        d[kisa + "_th"] = _satir_degeri(df, nuclide=nuk, score=skor, **{eb: 0.0})
        d[kisa + "_epi"] = _satir_degeri(df, nuclide=nuk, score=skor, **{eb: TERMAL_KESIM_EV})
    if any(v is None for v in d.values()):
        return None
    return indeksleri_hesapla(d)


def spektrum_dizisi(ortalama, sapma, grup_sayisi: int):
    """
    Tally dizisi -> (aki, sapma), uzunluk grup_sayisi. Enerji filtresi SON
    filtredir (en hizli degisen indeks); onundeki bin'ler (or. birden cok yakit
    malzemesi) uzerinden toplanir, varyanslar toplanir (bin'ler ayri olaylar).
    """
    import numpy as np
    m = np.asarray(ortalama, dtype=float).reshape(-1, grup_sayisi)
    s = np.asarray(sapma, dtype=float).reshape(-1, grup_sayisi)
    return m.sum(axis=0), np.sqrt((s ** 2).sum(axis=0))


def _spektrum_oku(sp) -> dict:
    import openmc
    sonuc = {}
    for anahtar, ad in (("model", T_SPEKTRUM), ("yakit", T_SPEKTRUM_YAKIT)):
        try:
            tal = sp.get_tally(name=ad)
        except LookupError:
            continue
        kenar = tal.find_filter(openmc.EnergyFilter).values.copy()
        sonuc[anahtar] = spektrum_dizisi(tal.mean, tal.std_dev, len(kenar) - 1)
        sonuc["kenarlar"] = kenar
    return sonuc


def y3_tally_adlari(sp) -> set:
    return {t.name for t in sp.tallies.values() if (t.name or "").startswith(TALLY_ONEKI)}


def oku(statepoint) -> Optional[dict]:
    """
    Statepoint yolundan (ya da acik openmc.StatePoint'ten) Y3 sonuclari.
    Y3 tally'si hic yoksa None. Kismi ise (zorunlu tally eksik) uyari loglanir,
    "eksik" listesi dolar ve faktorler None olur.
    DONER {"faktorler" | None, "indeksler" | None, "spektrum", "keff" | None,
           "sizinti" | None (bilinmiyor), "termal_fisyon_payi", "termal_kesim", "eksik"}.
    """
    if hasattr(statepoint, "get_tally"):
        return _oku(statepoint)
    import openmc
    with openmc.StatePoint(statepoint) as sp:
        return _oku(sp)


def _oku(sp) -> Optional[dict]:
    adlar = y3_tally_adlari(sp)
    if not adlar:
        return None
    eksik = [a for a in ZORUNLU_TALLYLER if a not in adlar]
    ozdeger = sp.run_mode == "eigenvalue"
    hiz = None
    if eksik:
        _log.warning("Y3 tally'leri kısmi (eksik: %s); dört faktör hesaplanmadı",
                     ", ".join(eksik))
    else:
        hiz = _hizlar_oku(sp, _tally_df(sp, T_TOPLAM), _tally_df(sp, T_TERMAL))
    keff = Deger(float(sp.keff.nominal_value), float(sp.keff.std_dev)) if ozdeger else None
    pay = oran(hiz["nF_th"], hiz["nF"]) if hiz else None
    return {"faktorler": faktorleri_hesapla(hiz) if (ozdeger and hiz) else None,
            "indeksler": _indeksler_oku(sp),
            "spektrum": _spektrum_oku(sp),
            "keff": keff,
            "sizinti": hiz["L"] if hiz else _global_sizinti(sp),
            "termal_fisyon_payi": pay.ort if pay else None,
            "termal_kesim": TERMAL_KESIM_EV,
            "eksik": eksik}
