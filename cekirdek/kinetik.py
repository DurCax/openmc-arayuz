# -*- coding: utf-8 -*-
"""
================================================================================
 kinetik.py  --  Nokta kinetigi: gecikmis notron gruplari, Inhour, P(t)
================================================================================
 Qt'den BAGIMSIZDIR. Statepoint'ten grup verisi okuma: cekirdek/kinetik_oku.py.

 DENKLEMLER (Duderstadt & Hamilton, "Nuclear Reactor Analysis", 1976, bol. 6;
 Keepin, "Physics of Nuclear Kinetics", 1965)

     dn/dt   = [(rho(t) - beta) n + sum_i lambda_i c_i] / Lambda
     dc_i/dt = beta_i n - lambda_i c_i                         i = 1..N

   n      : bagil guc P(t)/P0 (n(0) = 1, baslangicta kritik denge)
   c_i    : Lambda ile olceklenmis oncul yogunlugu; denge c_i(0) = beta_i/lambda_i
            (olcekleme kati sistemi iyi kosullu tutar: c_i ~ 1e-2 duzeyinde)
   beta_i : grup i'nin ETKIN gecikmis notron kesri (IFP ile eslenik agirlikli)
   lambda_i [1/s]: grup i oncullerinin bozunma sabiti
   Lambda [s]    : (ani) notron uretim zamani (generation time)
   rho    : reaktivite, Delta k / k (birimsiz). 1 pcm = 1e-5; 1 $ = beta.

 Sistem KATIDIR (stiff): ani ozdeger ~ -(beta - rho)/Lambda ~ -1e3..-1e6 1/s,
 gecikmis olcek ~ 1e-2 1/s. Bu yuzden acik yontem degil, scipy.integrate.solve_ivp
 ile Radau (varsayilan) ya da BDF ve analitik Jacobian kullanilir.

 ISTEGE BAGLI ADIYABATIK SICAKLIK GERI BESLEMESI (isi atilmaz)
     d(DT)/dt = P0 n / C          rho = rho_dis(t) + alpha_T DT
   C [J/K] toplam isi kapasitesi, P0 [W] baslangic gucu, alpha_T [1/K]
   (arayuzde pcm/K girilir; 1 pcm/K = 1e-5 1/K).

 TERS SAAT (INHOUR) DENKLEMI -- basamak reaktivitesinde n(t) = sum_k A_k e^(w_k t)
     rho = w Lambda + sum_i beta_i w / (w + lambda_i)
   N grupta N+1 kok; en buyuk kok w_0, kararli periyot T = 1/w_0.
================================================================================
"""

import math
from dataclasses import dataclass, replace

import numpy as np

from cekirdek.ceviri import _, N_

PCM = 1e-5                      # 1 pcm = 1e-5 Delta k/k
AZAMI_GECIKMIS_GRUP = 8         # OpenMC DelayedGroupFilter: 1..8 (mgxs.MAX_DELAYED_GROUPS)
VARSAYILAN_GRUP = 6             # ENDF/B-VII.1 ve ENDF/B-VIII.0: 6 grup (JEFF-3.1+: 8)
# P/P0 bu degeri asinca cozum durur: nokta kinetigi + (cogunlukla) geri beslemesiz
# modelin fiziksel anlami coktan bitmistir; ustel buyume float tasmasina gitmesin.
AZAMI_GUC_ORANI = 1e10
VARSAYILAN_NOKTA = 401
_RTOL, _ATOL = 1e-9, 1e-12      # solve_ivp toleranslari (testlerde 1e-6 dogruluk)
_YONTEMLER = ("Radau", "BDF")
_KOK_UST_SINIR = 1e12           # Inhour koku aramasi [1/s]; Lambda >= 1e-10 s icin yeter
_PERIYOT_PENCERESI = 0.1        # periyot tahmini: zaman ekseninin son %10'u

# Keepin, Wimett & Zeigler (1957), Phys. Rev. 107, 1044; Keepin (1965) Tablo 4-7:
# U-235 termal fisyon, 6 grup. Lamarsh & Baratta (2001) Tablo 7.4 ile ayni.
# beta = 0.0065. Lambda bu hazir veride TIPIK bir LWR degeridir (2e-5 s);
# kullanici kendi Lambda'sini girer ya da kosudan alir.
_KEEPIN_BETA = (0.000215, 0.001424, 0.001274, 0.002568, 0.000748, 0.000273)
_KEEPIN_LAMBDA = (0.0124, 0.0305, 0.111, 0.301, 1.14, 3.01)
_TIPIK_LWR_LAMBDA = 2e-5


# ============================================================================
# birimler
# ============================================================================

def pcm_den(pcm):
    """pcm -> rho (Delta k/k)."""
    return float(pcm) * PCM


def pcm_e(rho):
    """rho (Delta k/k) -> pcm."""
    return float(rho) / PCM


def dolar_dan(dolar, beta):
    """$ -> rho; 1 $ = beta_eff."""
    return float(dolar) * _pozitif(beta, "beta")


def dolar_a(rho, beta):
    """rho -> $."""
    return float(rho) / _pozitif(beta, "beta")


def k_den_rho(k):
    """k_eff -> rho = (k - 1)/k."""
    return (float(k) - 1.0) / _pozitif(k, "k")


def _pozitif(x, ad):
    x = float(x)
    if not (math.isfinite(x) and x > 0):
        raise ValueError(_("%s pozitif ve sonlu olmalı: %r") % (ad, x))
    return x


def _sonlu(x, ad):
    x = float(x)
    if not math.isfinite(x):
        raise ValueError(_("%s sonlu bir sayı olmalı: %r") % (ad, x))
    return x


# ============================================================================
# veri
# ============================================================================

@dataclass(frozen=True)
class GrupVerisi:
    """beta_i (Delta k/k), lambda_i (1/s), nesil_suresi = Lambda (s)."""
    beta: tuple
    lam: tuple
    nesil_suresi: float
    kaynak: str = ""

    def __post_init__(self):
        beta = tuple(float(b) for b in self.beta)
        lam = tuple(float(x) for x in self.lam)
        if not beta or len(beta) != len(lam):
            raise ValueError(_("β_i ve λ_i aynı sayıda (en az bir) grup içermeli."))
        if len(beta) > AZAMI_GECIKMIS_GRUP:
            raise ValueError(_("En çok %d gecikmeli nötron grubu desteklenir.")
                             % AZAMI_GECIKMIS_GRUP)
        if not all(math.isfinite(b) and b >= 0 for b in beta) or sum(beta) <= 0:
            raise ValueError(_("β_i negatif olamaz ve toplamı pozitif olmalı."))
        for x in lam:
            _pozitif(x, "λ_i")
        _pozitif(self.nesil_suresi, "Λ")
        object.__setattr__(self, "beta", beta)
        object.__setattr__(self, "lam", lam)
        object.__setattr__(self, "nesil_suresi", float(self.nesil_suresi))

    @property
    def beta_toplam(self):
        return math.fsum(self.beta)

    def nesil_suresi_ile(self, nesil_suresi):
        """Ayni gruplar, baska Lambda (YENI nesne)."""
        return replace(self, nesil_suresi=nesil_suresi)


KEEPIN_U235_TERMAL = GrupVerisi(
    beta=_KEEPIN_BETA, lam=_KEEPIN_LAMBDA, nesil_suresi=_TIPIK_LWR_LAMBDA,
    kaynak=N_("Keepin (1965), U-235 termal, 6 grup"))   # gosterimde _() ile cevrilir


@dataclass(frozen=True)
class Basamak:
    """t >= t0 icin sabit rho (Delta k/k)."""
    rho: float
    t0: float = 0.0

    def __post_init__(self):
        _sonlu(self.rho, "ρ")
        if not (math.isfinite(self.t0) and self.t0 >= 0):
            raise ValueError(_("Başlangıç zamanı negatif olamaz."))

    def deger(self, t):
        return self.rho if t >= self.t0 else 0.0

    def kirilmalar(self):
        return (self.t0,) if self.t0 > 0 else ()

    def en_buyuk(self):
        return max(self.rho, 0.0)


@dataclass(frozen=True)
class Rampa:
    """t0'dan baslayip `sure` boyunca `hiz` (Delta k/k / s) ile artan rho; sonra sabit."""
    hiz: float
    sure: float
    t0: float = 0.0

    def __post_init__(self):
        _sonlu(self.hiz, "ρ̇")
        _pozitif(self.sure, _("rampa süresi"))
        if not (math.isfinite(self.t0) and self.t0 >= 0):
            raise ValueError(_("Başlangıç zamanı negatif olamaz."))

    def deger(self, t):
        return self.hiz * min(max(t - self.t0, 0.0), self.sure)

    def kirilmalar(self):
        return tuple(x for x in (self.t0, self.t0 + self.sure) if x > 0)

    def en_buyuk(self):
        return max(self.hiz * self.sure, 0.0)


@dataclass(frozen=True)
class GeriBesleme:
    """Adiyabatik sicaklik geri beslemesi: alfa [1/K], isi_kapasitesi [J/K], guc0 [W]."""
    alfa: float
    isi_kapasitesi: float
    guc0: float

    def __post_init__(self):
        _sonlu(self.alfa, "α_T")
        _pozitif(self.isi_kapasitesi, _("ısı kapasitesi"))
        _pozitif(self.guc0, "P0")


@dataclass(frozen=True)
class Uyari:
    kod: str
    mesaj: str


@dataclass(frozen=True)
class Cozum:
    """t [s], guc = P/P0, rho [Delta k/k] (geri besleme dahil), sicaklik = DT [K] ya da None."""
    t: np.ndarray
    guc: np.ndarray
    rho: np.ndarray
    sicaklik: object
    uyarilar: tuple
    basarili: bool
    yontem: str


# ============================================================================
# ters saat (Inhour) denklemi
# ============================================================================

def inhour_rho(veri, omega):
    """rho(w) = w Lambda + sum beta_i w/(w + lambda_i)."""
    w = float(omega)
    return w * veri.nesil_suresi + math.fsum(b * w / (w + lam)
                                             for b, lam in zip(veri.beta, veri.lam))


def _birlesik_gruplar(veri):
    """Ayni lambda'li gruplari birlestirir (kok sayisi = farkli lambda + 1)."""
    birlesik = {}
    for b, lam in zip(veri.beta, veri.lam):
        birlesik[lam] = birlesik.get(lam, 0.0) + b
    lams = sorted(birlesik)
    return GrupVerisi(beta=tuple(birlesik[x] for x in lams), lam=tuple(lams),
                      nesil_suresi=veri.nesil_suresi, kaynak=veri.kaynak)


def _kok(f, a, b):
    from scipy.optimize import brentq
    fa, fb = f(a), f(b)
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    if fa * fb > 0:
        raise RuntimeError(_("Inhour kökü aralıkta bulunamadı: [%g, %g]") % (a, b))
    olcek = max(abs(a), abs(b), 1e-300)
    return brentq(f, a, b, xtol=1e-15 * olcek, rtol=4 * np.finfo(float).eps, maxiter=500)


def _genislet(f, bas, yon):
    """f'nin isareti yon'e (+1/-1) donene kadar adimi ikiye katlar."""
    adim = max(1.0, abs(bas))
    x = bas + yon * adim
    while yon * f(x) <= 0:
        adim *= 2.0
        if adim > _KOK_UST_SINIR:
            raise RuntimeError(_("Inhour kökü %g 1/s ötesinde.") % _KOK_UST_SINIR)
        x = bas + yon * adim
    return x


def inhour_kokleri(veri, rho):
    """Ters saat denkleminin tum kokleri, buyukten kucuge (1/s)."""
    rho = _sonlu(rho, "ρ")
    v = _birlesik_gruplar(veri)
    f = lambda w: inhour_rho(v, w) - rho          # noqa: E731
    kutup = [-x for x in v.lam]                   # azalan: -l1 > -l2 > ...
    pay = lambda p: abs(p) * 1e-13                # noqa: E731
    kokler = [_kok(f, kutup[0] + pay(kutup[0]), _genislet(f, kutup[0], +1))]
    for ust, alt in zip(kutup, kutup[1:]):
        kokler.append(_kok(f, alt + pay(alt), ust - pay(ust)))
    kokler.append(_kok(f, _genislet(f, kutup[-1], -1), kutup[-1] - pay(kutup[-1])))
    return tuple(sorted(kokler, reverse=True))


def kararli_periyot(veri, rho):
    """Basamak rho icin kararli (asimptotik) periyot T = 1/w_0 [s]; rho = 0 -> inf."""
    if float(rho) == 0.0:
        return math.inf
    return 1.0 / inhour_kokleri(veri, rho)[0]


# ============================================================================
# cozum
# ============================================================================

def _sistem_matrisi(veri, rho):
    """y' = A y; y = [n, c_1..c_N] (dogrusal, sabit rho)."""
    n = len(veri.beta)
    lam, beta, L = np.array(veri.lam), np.array(veri.beta), veri.nesil_suresi
    a = np.zeros((n + 1, n + 1))
    a[0, 0] = (rho - veri.beta_toplam) / L
    a[0, 1:] = lam / L
    a[1:, 0] = beta
    a[1:, 1:] = -np.diag(lam)
    return a


def _denge(veri):
    return np.concatenate(([1.0], np.array(veri.beta) / np.array(veri.lam)))


def analitik_basamak(veri, rho, t):
    """Basamak rho icin TAM cozum n(t) = [exp(A t) y0]_0 (matris ustel; dogrulama)."""
    from scipy.linalg import expm
    a, y0 = _sistem_matrisi(veri, _sonlu(rho, "ρ")), _denge(veri)
    return np.array([(expm(a * float(x)) @ y0)[0] for x in np.atleast_1d(t)])


def _turevler(veri, profil, gb):
    """solve_ivp icin (f, jac). Durum: [n, c_1..c_N] (+ DT geri beslemede)."""
    lam, beta = np.array(veri.lam), np.array(veri.beta)
    L, btop, n_g = veri.nesil_suresi, veri.beta_toplam, len(veri.beta)
    alfa = gb.alfa if gb else 0.0
    isinma = gb.guc0 / gb.isi_kapasitesi if gb else 0.0

    def rho_t(t, y):
        return profil.deger(t) + (alfa * y[-1] if gb else 0.0)

    def f(t, y):
        n, c = y[0], y[1:1 + n_g]
        dn = ((rho_t(t, y) - btop) * n + lam @ c) / L
        dy = [dn, *(beta * n - lam * c)]
        if gb:
            dy.append(isinma * n)
        return np.array(dy)

    def jac(t, y):
        m = np.zeros((len(y), len(y)))
        m[:n_g + 1, :n_g + 1] = _sistem_matrisi(veri, rho_t(t, y))
        if gb:
            m[0, -1] = alfa * y[0] / L
            m[-1, 0] = isinma
        return m

    return f, jac, rho_t


def _baslangic_uyarilari(veri, profil, gb):
    uy = []
    en_buyuk = profil.en_buyuk()
    if en_buyuk >= veri.beta_toplam:
        uy.append(Uyari("ani_kritik", _(
            "ρ = %.3f $ ≥ 1 $: ANİ KRİTİK. Güç gecikmeli nötronları beklemeden Λ "
            "ölçeğinde artar; bu bölgede nokta kinetiği yalnız nitel bir tablo verir.")
            % (en_buyuk / veri.beta_toplam)))
    if gb and gb.alfa > 0:
        uy.append(Uyari("pozitif_alfa", _(
            "α_T > 0: pozitif sıcaklık katsayısı gücü kendiliğinden artırır "
            "(kararsız geri besleme).")))
    return uy


def _parcalar(profil, t_son):
    sinirlar = [0.0, *(x for x in profil.kirilmalar() if 0.0 < x < t_son), t_son]
    return list(zip(sinirlar, sinirlar[1:]))


def coz(veri, reaktivite, t_son, geri_besleme=None, nokta=VARSAYILAN_NOKTA, yontem="Radau"):
    """
    Nokta kinetigi denklemlerini [0, t_son] s'de cozer (kati ODE; Radau/BDF).
    reaktivite: Basamak ya da Rampa (dis reaktivite, Delta k/k).
    DONER Cozum; P/P0 AZAMI_GUC_ORANI'ni asarsa cozum durur ("tasma" uyarisi).
    """
    from scipy.integrate import solve_ivp
    t_son = _pozitif(t_son, _("süre"))
    if yontem not in _YONTEMLER:
        raise ValueError(_("Yöntem Radau ya da BDF olmalı: %r") % yontem)
    if int(nokta) < 2:
        raise ValueError(_("En az iki zaman noktası gerekir."))
    f, jac, rho_t = _turevler(veri, reaktivite, geri_besleme)
    tasma = lambda t, y: y[0] - AZAMI_GUC_ORANI   # noqa: E731
    tasma.terminal, tasma.direction = True, 1
    izgara = np.linspace(0.0, t_son, int(nokta))
    y = np.concatenate((_denge(veri), [0.0] if geri_besleme else []))
    ts, ys = [0.0], [y]
    uyarilar = _baslangic_uyarilari(veri, reaktivite, geri_besleme)
    basarili = True
    for a, b in _parcalar(reaktivite, t_son):
        ara = np.unique(np.concatenate((izgara[(izgara > a) & (izgara < b)], [b])))
        s = solve_ivp(f, (a, b), y, method=yontem, t_eval=ara, jac=jac, events=tasma,
                      rtol=_RTOL, atol=_ATOL)
        if s.status == -1:
            basarili = False
            uyarilar.append(Uyari("cozucu", _("Çözücü başarısız: %s") % s.message))
            break
        ts.extend(s.t)
        ys.extend(s.y.T)
        if s.status == 1:
            ts.append(float(s.t_events[0][0]))
            ys.append(s.y_events[0][0])
            uyarilar.append(Uyari("tasma", _(
                "P/P0 %.0e'yi aştı (t = %.4g s); çözüm burada durduruldu.")
                % (AZAMI_GUC_ORANI, ts[-1])))
            break
        y = s.y[:, -1]
    return _cozum_kur(ts, ys, rho_t, izgara, uyarilar, basarili, yontem,
                      geri_besleme is not None)


def _cozum_kur(ts, ys, rho_t, izgara, uyarilar, basarili, yontem, gb_var):
    """Ara kirilma noktalarini atar (yalniz izgara + son nokta), salt-okunur diziler."""
    t, y = np.array(ts), np.array(ys)
    tut = np.isin(t, izgara) | (np.arange(len(t)) == len(t) - 1)
    t, y = t[tut], y[tut]
    rho = np.array([rho_t(x, yy) for x, yy in zip(t, y)])
    diziler = [t, y[:, 0].copy(), rho] + ([y[:, -1].copy()] if gb_var else [])
    for d in diziler:
        d.setflags(write=False)
    return Cozum(t=diziler[0], guc=diziler[1], rho=diziler[2],
                 sicaklik=diziler[3] if gb_var else None, uyarilar=tuple(uyarilar),
                 basarili=basarili, yontem=yontem)


def periyot_tahmini(cozum):
    """Cozumun son %10'unda ln(P) egiminden periyot [s]; egim ~0 ise inf."""
    t, n = np.asarray(cozum.t), np.asarray(cozum.guc)
    if len(t) < 3:
        raise ValueError(_("Periyot için en az üç nokta gerekir."))
    pencere = t >= t[-1] - _PERIYOT_PENCERESI * (t[-1] - t[0])
    if pencere.sum() < 2 or np.any(n[pencere] <= 0):
        raise ValueError(_("Periyot tahmini için pozitif güç noktaları gerekir."))
    egim = np.polyfit(t[pencere], np.log(n[pencere]), 1)[0]
    return math.inf if abs(egim) < 1e-14 else 1.0 / egim
