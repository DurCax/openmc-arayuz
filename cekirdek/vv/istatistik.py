# -*- coding: utf-8 -*-
"""
vv/istatistik.py -- NUREG/CR-6698 (Ocak 2001) yanlilik, yanlilik belirsizligi ve USL.

Kaynak: J.C. Dean, R.W. Tayloe Jr., "Guide for Validation of Nuclear Criticality
Safety Calculational Methodology", NUREG/CR-6698, NRC (ML050250061). Esitlik
numaralari belgedekilerdir; yontem ozeti docs/STANDARTLAR.md §4. Belgenin §3
ornegi (Tablo 3.1, 25 vaka) testler/test_vv.py'de birebir yeniden uretilir.

Akis (degerlendir):
  1. k_norm = k_calc / k_exp, σ = √(σ_calc² + σ_exp²)        eş. (9), (3)
  2. agirlikli k̄, s², σ̄², S_p                               eş. (4)-(7)
  3. yanlilik = k̄ - 1; pozitifse 0 kullanilir                eş. (8)
  4. normallik: Shapiro-Wilk (n < 50 icin 6698 §2.4.3)       eş. (16)-(19)
  5. egilim: agirlikli dogrusal uydurma, egim t-testi        eş. (10)-(15)
     (t-testi 6698'de yok; SCALE/VADER uygulamasi)
  6. yontem: normal degil -> parametrik olmayan (31)-(34);
             normal + anlamli egilim -> tolerans bandi (23)-(30);
             normal + egilim yok -> tolerans siniri (20)-(22)
  7. USL = K_L - ΔSM - ΔAOA, ΔSM >= 0.02                      eş. (22), (35); §2.4.5
  8. kabul: k + 2σ < USL                                      eş. (36)

Excel islevlerinin bazi surumlerde hatali oldugu uyarisi (6698 §2.4) nedeniyle
dagilim nicelikleri SciPy (BSD lisansi) ile hesaplanir.
"""

import math
from dataclasses import dataclass, field
from typing import Mapping

from cekirdek.ceviri import _

GUVEN = 0.95                 # %95 guven (6698 ornegi)
KAPSAM = 0.95                # popülasyonun %95'i
DELTA_SM_ASGARI = 0.02       # 6698 §2.4.5 mutlak alt sinir
N_TABLO_UST = 50             # Tablo 2.1 n <= 50; n > 50 icin U(50) muhafazakar
N_ASGARI = 3                 # regresyon ve Shapiro-Wilk icin
N_USL_ASGARI = 10            # 6698 §2.2: < 10 deney teknik gerekce ister; arac gerekce
#                              olmadan USL VERMEZ (STANDARTLAR.md §5: sahte guven yok)
ALFA = 0.05                  # normallik ve egilim anlamlilik duzeyi
SINIRDA_UST = 0.10           # 0.05 < p < 0.10 "sinirda" (iki yontem de raporlanmali)
LOG_PARAMETRELER = ("ealf",)  # EALF egilimi log10 olceginde
# Tablo 2.2 (onerilen; gerekceyle degistirilebilir): (β alt siniri, NPM); β <= %40 -> veri yetersiz
NPM_TABLOSU = ((0.90, 0.00), (0.80, 0.01), (0.70, 0.02), (0.60, 0.03), (0.50, 0.04),
               (0.40, 0.05))


@dataclass(frozen=True)
class Vaka:
    ad: str
    k: float                 # k_calc
    sigma_calc: float
    k_exp: float = 1.0
    sigma_exp: float = 0.0
    parametreler: Mapping = field(default_factory=dict)
    seri: str = ""


def normallestir(vakalar):
    """eş. (9) k_norm = k_calc / k_exp; eş. (3) σ = √(σ_calc² + σ_exp²)."""
    k = [v.k / v.k_exp for v in vakalar]
    s = [math.hypot(v.sigma_calc, v.sigma_exp) for v in vakalar]
    return k, s


def agirlikli_istatistik(k, s):
    """eş. (4)-(7): w = 1/σ², k̄, s², σ̄², S_p = √(s² + σ̄²)."""
    n = len(k)
    w = [1.0 / si ** 2 for si in s]
    W = sum(w)
    k_ort = sum(wi * ki for wi, ki in zip(w, k)) / W                            # (6)
    s2 = (sum(wi * (ki - k_ort) ** 2 for wi, ki in zip(w, k)) / (n - 1)) / (W / n)  # (4)
    sigma2_ort = n / W                                                           # (5)
    return {"W": W, "k_ort": k_ort, "s2": s2, "sigma2_ort": sigma2_ort,
            "S_p": math.sqrt(s2 + sigma2_ort)}                                   # (7)


def yanlilik(k_ort):
    """eş. (8): (ham yanlilik k̄ - 1, kullanilan yanlilik = min(ham, 0))."""
    ham = k_ort - 1.0
    return ham, min(ham, 0.0)


def egilim(x, k, s, alfa=ALFA):
    """eş. (10)-(15) agirlikli dogrusal uydurma k_fit = a + b·x; (26), (28)-(30) bant
    nicelikleri; egim anlamliligi t = |b| / se(b) > t_{1-α/2, n-2} (VADER)."""
    from scipy import stats
    n = len(k)
    w = [1.0 / si ** 2 for si in s]
    W = sum(w)
    x_ort = sum(wi * xi for wi, xi in zip(w, x)) / W
    k_ort = sum(wi * ki for wi, ki in zip(w, k)) / W
    sxx_w = sum(wi * (xi - x_ort) ** 2 for wi, xi in zip(w, x))
    skk_w = sum(wi * (ki - k_ort) ** 2 for wi, ki in zip(w, k))
    sxk_w = sum(wi * (xi - x_ort) * (ki - k_ort) for wi, xi, ki in zip(w, x, k))
    b = sxk_w / sxx_w                                                            # (11)
    a = k_ort - b * x_ort                                                        # (10)
    r = sxk_w / math.sqrt(sxx_w * skk_w) if skk_w > 0 else 0.0                   # (15)
    artik = sum(wi * (ki - (a + b * xi)) ** 2 for wi, xi, ki in zip(w, x, k))
    s_fit2 = (n / (n - 2)) * artik / W                                           # (30)
    S_xx = sxx_w / (W / n)                                                       # (26)
    se_b = math.sqrt((artik / (n - 2)) / sxx_w)
    t = abs(b) / se_b if se_b > 0 else float("inf")
    return {"a": a, "b": b, "r": r, "x_ort": x_ort, "S_xx": S_xx, "s_fit2": s_fit2,
            "S_p": math.sqrt(s_fit2 + n / W), "t": t,                            # (28)-(29)
            "anlamli": t > stats.t.ppf(1.0 - alfa / 2.0, n - 2), "n": n,
            "x_min": min(x), "x_max": max(x)}


def normallik(k, alfa=ALFA):
    """6698 §2.4.3: n < 50 icin Shapiro-Wilk W (eş. 16-19); SciPy uygulamasi.
    n > 50 icin belge yontem vermez -- yine Shapiro-Wilk kullanilir ve not edilir."""
    from scipy import stats
    W, p = stats.shapiro(k)
    return {"test": "Shapiro-Wilk", "W": float(W), "p": float(p), "normal": bool(p > alfa),
            "sinirda": bool(alfa < p < SINIRDA_UST), "n_ustu_50": len(k) > N_TABLO_UST}


def tolerans_carpani(n, kapsam=KAPSAM, guven=GUVEN):
    """Tablo 2.1 U(n): tek tarafli tolerans carpani, merkezi olmayan t dagilimindan.
    n > 50 icin U(50) kullanilir (6698: muhafazakar)."""
    from scipy import stats
    n = min(int(n), N_TABLO_UST)
    if n < 2:
        raise ValueError(_("tolerans çarpanı için en az 2 vaka gerekir"))
    delta = stats.norm.ppf(kapsam) * math.sqrt(n)
    return float(stats.nct.ppf(guven, n - 1, delta) / math.sqrt(n))


def tolerans_siniri(k_ort, S_p, n):
    """eş. (20)-(21): K_L = min(k̄, 1) - U·S_p (pozitif yanlilik kredilendirilmez)."""
    return min(k_ort, 1.0) - tolerans_carpani(n) * S_p


def tolerans_bandi(e, x, n, guven=GUVEN):
    """eş. (23)-(24): K_L(x) = min(k_fit(x), 1) - S_p [√(2F(1/n + (x - x̄)²/S_xx))
    + z √((n-2)/χ²)]; F = F⁻¹(P; 2, n-2), z = Φ⁻¹(P), χ² alt (1-P)/2 noktasi."""
    from scipy import stats
    F = stats.f.ppf(guven, 2, n - 2)
    z = stats.norm.ppf(guven)
    chi2 = stats.chi2.ppf((1.0 - guven) / 2.0, n - 2)
    k_yildiz = min(e["a"] + e["b"] * x, 1.0)                                     # (24)
    genislik = (math.sqrt(2.0 * F * (1.0 / n + (x - e["x_ort"]) ** 2 / e["S_xx"]))
                + z * math.sqrt((n - 2) / chi2))
    return k_yildiz - e["S_p"] * genislik


def npm(beta):
    """Tablo 2.2: parametrik olmayan pay; β <= %40 -> None (ek veri gerekli)."""
    for alt, pay in NPM_TABLOSU:
        if beta > alt:
            return pay
    return None


def parametrik_olmayan(k, s, S_p, kapsam=KAPSAM):
    """eş. (31)-(34), m = 1 (en kucuk deger): β = 1 - qⁿ (32);
    K_L = k_(1) - σ_(1) - NPM (33); k_(1) > 1 ise K_L = 1 - S_p - NPM (34)."""
    n = len(k)
    beta = 1.0 - kapsam ** n                                                     # (32)
    pay = npm(beta)
    if pay is None:
        return {"guven": beta, "npm": None, "K_L": None}
    i = min(range(n), key=lambda j: k[j])
    if k[i] > 1.0:
        kl = 1.0 - S_p - pay                                                     # (34)
    else:
        kl = k[i] - s[i] - pay                                                   # (33)
    return {"guven": beta, "npm": pay, "K_L": kl}


def usl(K_L, delta_sm, delta_aoa=0.0):
    """eş. (22)/(35): USL = K_L - ΔSM - ΔAOA; ΔSM >= 0.02 (§2.4.5)."""
    if delta_sm < DELTA_SM_ASGARI:
        raise ValueError(_("ΔSM = %.3f, mutlak alt sınır %.2f'nin altında (NUREG/CR-6698 "
                           "§2.4.5)") % (delta_sm, DELTA_SM_ASGARI))
    if delta_aoa < 0:
        raise ValueError(_("ΔAOA negatif olamaz: %g") % delta_aoa)
    return K_L - delta_sm - delta_aoa


def kabul(k, sigma, usl_degeri, carpan=2.0):
    """eş. (36): k + 2σ < USL (kati esitsizlik)."""
    return k + carpan * sigma < usl_degeri


def _x(vaka, ad):
    deger = vaka.parametreler.get(ad)
    if deger is None:
        return None
    deger = float(deger)
    if ad in LOG_PARAMETRELER:
        return math.log10(deger) if deger > 0 else None
    return deger


def egilimler(vakalar, k, s, parametreler):
    """Her parametre icin egilim (butun vakalarda tanimli ve degiskense)."""
    sonuc = {}
    for ad in parametreler:
        x = [_x(v, ad) for v in vakalar]
        if any(xi is None for xi in x) or len(x) < N_ASGARI or max(x) - min(x) <= 0:
            continue
        sonuc[ad] = egilim(x, k, s)
    return sonuc


def _bant_usl(e, n, uygulama, ad):
    """Bant yonteminde K_L: uygulama degeri verilmisse orada, yoksa veri araligindaki
    en kucuk K_L (bant uclarda en genis; dogrusal k_fit uclarda uc degerde)."""
    if uygulama and uygulama.get(ad) is not None:
        x = float(uygulama[ad])
        x = math.log10(x) if ad in LOG_PARAMETRELER else x
        return tolerans_bandi(e, x, n), "%s = %g" % (ad, float(uygulama[ad]))
    adaylar = [e["x_min"], e["x_max"]]
    kl = min(tolerans_bandi(e, x, n) for x in adaylar)
    return kl, _("%s doğrulama aralığındaki en küçük değer") % ad


def _bos_sonuc(n, delta_sm, delta_aoa, neden):
    return {"n": n, "yontem": "tolerans_siniri", "usl": None, "usl_neden": neden,
            "bias": 0.0, "bias_kullanilan": 0.0, "delta_sm": delta_sm, "delta_aoa": delta_aoa,
            "guven": None, "normallik": None, "egilim": {}, "K_L": None,
            "normallestirildi": True}


def degerlendir(vakalar, delta_sm=0.05, delta_aoa=0.0,
                egilim_parametreleri=("zenginlik", "h_x", "ealf"), uygulama=None,
                n_usl_asgari=N_USL_ASGARI):
    """NUREG/CR-6698 akisi (modul basligi). DONER sozluk (vv_arayuz.VVOzeti alanlari +
    K_L, S_p, k_ort, usl_noktasi). USL hesaplanamazsa usl None ve usl_neden dolu.
    n < n_usl_asgari ise istatistikler raporlanir ama USL verilmez (kullanici teknik
    gerekceyle n_usl_asgari'yi dusurebilir; K10 yine uyarir)."""
    usl(1.0, delta_sm, delta_aoa)            # ΔSM / ΔAOA girdisini en basta denetle
    n = len(vakalar)
    if n < N_ASGARI:
        return _bos_sonuc(n, delta_sm, delta_aoa,
                          _("doğrulama kümesinde %d vaka var; en az %d gerekir")
                          % (n, N_ASGARI))
    k, s = normallestir(vakalar)
    ag = agirlikli_istatistik(k, s)
    ham, kullanilan = yanlilik(ag["k_ort"])
    norm = normallik(k)
    eg = egilimler(vakalar, k, s, egilim_parametreleri)
    sonuc = {"n": n, "bias": ham, "bias_kullanilan": kullanilan, "delta_sm": delta_sm,
             "delta_aoa": delta_aoa, "guven": None, "normallik": norm, "K_L": None,
             "egilim": {p: {"egim": e["b"], "anlamli": bool(e["anlamli"]), "t": e["t"],
                            "r": e["r"], "log10": p in LOG_PARAMETRELER}
                        for p, e in eg.items()},
             "S_p": ag["S_p"], "k_ort": ag["k_ort"], "usl_neden": "", "usl_noktasi": "",
             "normallestirildi": True}
    anlamli = sorted((p for p, e in eg.items() if e["anlamli"]), key=lambda p: -eg[p]["t"])
    if not norm["normal"]:
        po = parametrik_olmayan(k, s, ag["S_p"])
        sonuc.update(yontem="parametrik_olmayan", guven=po["guven"], K_L=po["K_L"])
        if po["K_L"] is None:
            sonuc["usl"] = None
            sonuc["usl_neden"] = (_("veri normal değil ve parametrik olmayan güven β = %%%.1f "
                                    "≤ %%40: ek kriter verisi gerekli (NUREG/CR-6698 "
                                    "Tablo 2.2)") % (100 * po["guven"]))
            return sonuc
    elif anlamli:
        e = eg[anlamli[0]]
        kl, nokta = _bant_usl(e, n, uygulama, anlamli[0])
        sonuc.update(yontem="tolerans_bandi", K_L=kl, usl_noktasi=nokta, S_p=e["S_p"])
    else:
        sonuc.update(yontem="tolerans_siniri", K_L=tolerans_siniri(ag["k_ort"], ag["S_p"], n))
    if n < n_usl_asgari:
        sonuc["usl"] = None
        sonuc["usl_neden"] = (_("kümede %d vaka var (< %d): bağımsız vaka yetersiz, teknik "
                                "gerekçe olmadan USL verilmez (NUREG/CR-6698 §2.2); hesaplanan "
                                "K_L = %.4f yalnız bilgi") % (n, n_usl_asgari, sonuc["K_L"]))
        return sonuc
    sonuc["usl"] = usl(sonuc["K_L"], delta_sm, delta_aoa)
    return sonuc
