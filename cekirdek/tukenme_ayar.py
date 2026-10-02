# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_ayar.py  --  Tukenme genisletme ayarlari (v3 Y4): okuyucu ve denetim
================================================================================

 Spec'in "tukenme" bolumune Y4 ile gelen anahtarlar. Hicbiri
 sema.VARSAYILAN_TUKENME'de DEGILDIR (onbellek kimligi ve eski dosyalar
 degismesin); okuyucu varsayilani burada verir:

   entegrator        predictor | cecm | celi | leqi | epc_rk4 | cf4 |
                     si_celi | si_leqi                 (varsayilan cecm)
   si_ic_adim        SI-* entegratorlerinin ic yineleme sayisi (OpenMC n_steps;
                     varsayilan 10 = OpenMC varsayilani)
   sogutma           {"adimlar": [..], "birim": "d"}: yanma adimlarindan SONRA
                     sifir gucte (yalniz bozunma) adimlar. OpenMC: guc 0 olan
                     adimda transport KOSULMAZ (CoupledOperator.__call__,
                     source_rate == 0 -> sifir reaksiyon hizi).
   surdur            true: dizindeki depletion_results.h5 kaldigi yerden
                     surdurulur (cekirdek/tukenme_surdur.py)
   hizli_kip         true: transport'suz tukenme -- tek transport'tan MicroXS,
                     sonra IndependentOperator (cekirdek/tukenme_hizli.py)
   kritik_arama      {"var", "tur": "bor"|"cubuk", "hedef", "alt", "ust",
                      "sinir": [min, max], "k_tol", "sigma"}
                     (cekirdek/tukenme_arama.py)

 Transport sayilari OpenMC 0.16 kaynagindan (openmc/deplete/integrators.py,
 abc.py): entegrator._num_stages adim basina; SI-* ilk adimda bir BOS
 transport'u (n_steps kat parcacikla) + adim basina (n_steps + 1).
================================================================================
"""

from __future__ import annotations

from dataclasses import dataclass

from cekirdek.ceviri import N_, _

VARSAYILAN_ENTEGRATOR = "cecm"
SI_IC_ADIM = 10                 # OpenMC SIIntegrator n_steps varsayilani
SI_IC_ADIM_SINIR = (1, 100)
ZAMAN_BIRIMLERI = ("s", "min", "h", "d", "a")     # sogutma (guc 0): MWd/kg anlamsiz
YANMA_BIRIMLERI = ("d", "MWd/kg")
ARAMA_TURLERI = ("bor", "cubuk")
# kritik arama: OpenMC Model.keff_search varsayilani k_tol 1e-4, sigma_final
# 3e-4. Tukenme her adimda bir arama yapar; arayuz bu kadar dar bir hedefi
# kucuk modelde onlarca transport'la oder. Varsayilan 1e-3 / 1e-3: 100 pcm,
# tipik bir tukenme adimindaki istatistik belirsizligi duzeyinde.
ARAMA_K_TOL = 1.0e-3
ARAMA_SIGMA = 1.0e-3
CUBUK_SINIR = (0.0, 100.0)      # daldirma yuzdesi


@dataclass(frozen=True)
class Entegrator:
    """Bir openmc.deplete entegratoru: kod, sinif adi, adim basina transport."""
    kod: str
    sinif: str
    asama: int
    ad: str
    si: bool = False

    def gorunen_ad(self) -> str:
        return _(self.ad)


ENTEGRATORLER = {e.kod: e for e in (
    Entegrator("predictor", "PredictorIntegrator", 1,
               N_("Predictor — öngörücü, 1. mertebe (adım başına 1 transport)")),
    Entegrator("cecm", "CECMIntegrator", 2,
               N_("CE/CM — öngörücü-düzeltici, 2. mertebe (adım başına 2 transport)")),
    Entegrator("celi", "CELIIntegrator", 2,
               N_("CE/LI — sabit dışdeğerleme / doğrusal aradeğerleme (2 transport)")),
    Entegrator("leqi", "LEQIIntegrator", 2,
               N_("LE/QI — doğrusal dışdeğerleme / ikinci derece aradeğerleme (2 transport)")),
    Entegrator("epc_rk4", "EPCRK4Integrator", 4,
               N_("EPC-RK4 — genişletilmiş öngörücü-düzeltici, Runge-Kutta 4 (4 transport)")),
    Entegrator("cf4", "CF4Integrator", 4,
               N_("CF4 — 4. mertebe komütatörsüz Lie (4 transport)")),
    Entegrator("si_celi", "SICELIIntegrator", 2,
               N_("SI-CE/LI — stokastik örtük CE/LI (iç yinelemeli)"), si=True),
    Entegrator("si_leqi", "SILEQIIntegrator", 2,
               N_("SI-LE/QI — stokastik örtük LE/QI (iç yinelemeli)"), si=True),
)}


@dataclass(frozen=True)
class KritikArama:
    """Tukenme sirasinda kritiklik aramasi ayari (okunmus, varsayilanli)."""
    var: bool
    tur: str
    hedef: str
    alt: float
    ust: float
    sinir: tuple
    k_tol: float
    sigma: float


def entegrator(t: dict) -> Entegrator:
    """Secili entegrator; bilinmeyen kod ValueError (kosu baslamaz)."""
    kod = (t or {}).get("entegrator") or VARSAYILAN_ENTEGRATOR
    if kod not in ENTEGRATORLER:
        raise ValueError(_("bilinmeyen entegratör: %s") % kod)
    return ENTEGRATORLER[kod]


def si_ic_adim(t: dict) -> int:
    return int((t or {}).get("si_ic_adim") or SI_IC_ADIM)


def sogutma(t: dict) -> tuple:
    """(adimlar, birim): sifir guclu bozunma adimlari; yoksa ([], "d")."""
    s = (t or {}).get("sogutma") or {}
    return [float(a) for a in s.get("adimlar") or []], s.get("birim") or "d"


def surdur(t: dict) -> bool:
    return bool((t or {}).get("surdur"))


def hizli_kip(t: dict) -> bool:
    return bool((t or {}).get("hizli_kip"))


def kritik_arama(t: dict) -> KritikArama:
    k = (t or {}).get("kritik_arama") or {}
    tur = k.get("tur") or "bor"
    varsayilan_sinir = CUBUK_SINIR if tur == "cubuk" else (0.0, 3000.0)
    sinir = tuple(float(x) for x in (k.get("sinir") or varsayilan_sinir))
    return KritikArama(
        var=bool(k.get("var")), tur=tur, hedef=k.get("hedef") or "",
        alt=float(k.get("alt", sinir[0] if sinir else 0.0)),
        ust=float(k.get("ust", sinir[-1] if sinir else 0.0)),
        sinir=sinir, k_tol=float(k.get("k_tol") or ARAMA_K_TOL),
        sigma=float(k.get("sigma") or ARAMA_SIGMA))


def zaman_plani(t: dict) -> tuple:
    """
    (adimlar, guc_yogunluklari): openmc.deplete Integrator'a verilecek
    [(deger, birim)] ve [W/gHM]. Yanma adimlari adim_birimi ile, sogutma
    adimlari kendi birimiyle ve SIFIR gucle. OpenMC adim basina (deger,
    birim) ikililerini kabul eder (abc.Integrator, timesteps).
    """
    p = float(t["guc_yogunlugu"])
    birim = t.get("adim_birimi") or "d"
    yanma = [(float(a), birim) for a in t.get("adimlar") or []]
    s_adim, s_birim = sogutma(t)
    soguma = [(a, s_birim) for a in s_adim]
    return yanma + soguma, [p] * len(yanma) + [0.0] * len(soguma)


def transport_sayisi(t: dict) -> int:
    """
    Toplam transport cozumu (kritik arama haric: arama adim basina ek
    transport kosar, sayisi onceden bilinmez). Sogutma adimlarinda transport
    yoktur; son adim sogutmaysa son (EOL) transport da kosulmaz. Hizli kipte
    yalniz MicroXS icin bir transport.
    """
    t = t or {}
    if hizli_kip(t):
        return 1
    nb = len(t.get("adimlar") or [])
    ns = len(sogutma(t)[0])
    e = entegrator(t)
    if e.si:
        return 1 + nb * (si_ic_adim(t) + 1)
    return nb * e.asama + (0 if ns else 1)


# ============================================================================
# Denetim (tukenme.kapi cagirir; dogrula.kapi'nin bulgularina eklenir)
# ============================================================================

def ayar_bulgulari(spec: dict) -> list:
    """Y4 ayarlarinin bulgulari (hata/uyari/bilgi). Tukenme kapaliysa bos."""
    t = spec.get("tukenme") or {}
    if not t.get("var"):
        return []
    bulgular = _entegrator_bulgulari(t) + _sogutma_bulgulari(t)
    if hizli_kip(t):
        bulgular.append(_bulgu(
            "uyari", _("hızlı kip: tesir kesitleri tek transport'tan (MicroXS), adımlar boyunca sabit"),
            _("Yakıt tükendikçe spektrum değişir ama hızlı kip bunu görmez; yüksek yanmada "
              "Pu birikimi ve zehirlerin yanması sonucu saptırır. Ön inceleme içindir; tam "
              "(transport'lu) tükenmeyle doğrulayın. k-eff adım adım hesaplanmaz.")))
    if surdur(t):
        bulgular.append(_bulgu(
            "bilgi", _("sürdürme açık: önceki sonuç silinmez, kaldığı yerden devam edilir"),
            _("Önceki koşunun fiziği (malzeme, geometri, güç) aynı olmalı; adım listesi "
              "öncekinin devamı olmalı.")))
    return bulgular + _arama_bulgulari(spec, t)


def _bulgu(seviye: str, mesaj: str, oneri: str | None = None, yer: str = "tukenme"):
    from cekirdek.dogrula._ortak import Bulgu
    return Bulgu(seviye, yer, mesaj, oneri)


def _entegrator_bulgulari(t: dict) -> list:
    kod = t.get("entegrator") or VARSAYILAN_ENTEGRATOR
    if kod not in ENTEGRATORLER:
        return [_bulgu("hata", _("bilinmeyen entegratör: %s") % kod,
                       _("Seçenekler: %s") % ", ".join(ENTEGRATORLER))]
    if not ENTEGRATORLER[kod].si:
        return []
    try:
        n = int(t.get("si_ic_adim", SI_IC_ADIM))
    except (TypeError, ValueError):
        n = 0
    if SI_IC_ADIM_SINIR[0] <= n <= SI_IC_ADIM_SINIR[1]:
        return []
    return [_bulgu("hata", _("SI iç yineleme sayısı %d–%d arasında olmalı") % SI_IC_ADIM_SINIR)]


def _sogutma_bulgulari(t: dict) -> list:
    s = t.get("sogutma") or {}
    if s.get("birim", "d") not in ZAMAN_BIRIMLERI:
        return [_bulgu("hata", _("soğuma adımı birimi geçersiz: %s") % s.get("birim"),
                       _("Soğuma sıfır güçtedir; birim zaman olmalı (%s).")
                       % ", ".join(ZAMAN_BIRIMLERI))]
    try:
        adimlar = [float(a) for a in s.get("adimlar") or []]
    except (TypeError, ValueError):
        return [_bulgu("hata", _("soğuma adımları sayı olmalı"))]
    if any(a <= 0 for a in adimlar):
        return [_bulgu("hata", _("soğuma adımları sıfırdan büyük olmalı"))]
    return []


def _arama_bulgulari(spec: dict, t: dict) -> list:
    try:
        k = kritik_arama(t)
    except (TypeError, ValueError):
        return [_bulgu("hata", _("kritiklik araması ayarları sayı olmalı"))]
    if not k.var:
        return []
    if k.tur not in ARAMA_TURLERI:
        return [_bulgu("hata", _("bilinmeyen kritiklik araması türü: %s") % k.tur)]
    hatalar = _arama_uyum_hatalari(t, k) + _arama_hedef_hatalari(spec, k)
    if len(k.sinir) != 2 or not k.sinir[0] < k.sinir[1]:
        hatalar.append(_("arama sınırı [alt, üst] ve alt < üst olmalı"))
    elif not (k.sinir[0] <= min(k.alt, k.ust) and max(k.alt, k.ust) <= k.sinir[1]) \
            or k.alt == k.ust:
        hatalar.append(_("iki başlangıç tahmini sınırın içinde ve birbirinden farklı olmalı"))
    if k.k_tol <= 0 or k.sigma <= 0:
        hatalar.append(_("k toleransı ve σ sınırı sıfırdan büyük olmalı"))
    oneri = _("Kritiklik araması: OpenMC Integrator.add_keff_search_control "
              "(Model.keff_search, GRsecant).")
    return [_bulgu("hata", h, oneri) for h in hatalar]


def _arama_uyum_hatalari(t: dict, k: KritikArama) -> list:
    hatalar = []
    kod = t.get("entegrator") or VARSAYILAN_ENTEGRATOR
    if kod in ENTEGRATORLER and ENTEGRATORLER[kod].si:
        hatalar.append(_("SI-* entegratörleri kritiklik aramasını desteklemez (OpenMC 0.16)"))
    if hizli_kip(t):
        hatalar.append(_("hızlı kipte (MicroXS) kritiklik araması yapılamaz: transport yok"))
    if k.tur == "cubuk" and t.get("malzemeleri_ayir"):
        hatalar.append(_("kontrol çubuğu araması çubuk çubuk yanma ile birlikte desteklenmiyor"))
    return hatalar


def _arama_hedef_hatalari(spec: dict, k: KritikArama) -> list:
    from cekirdek import sema
    if k.tur == "bor":
        m = sema.malzeme_bul(spec, k.hedef)
        if m is None:
            return [_("bor araması: tanımsız malzeme '%s'") % k.hedef]
        from cekirdek import uygunluk
        if not uygunluk.tek_malzeme_rolleri(m) & {"sogutucu", "moderator"}:
            return [_("bor araması yalnız su (soğutucu/moderatör) malzemesine uygulanır: '%s'")
                    % k.hedef]
        return []
    c = sema.cubuk_bul(spec, k.hedef)
    if c is None or c.get("tur") != "kontrol":
        return [_("kontrol çubuğu araması: '%s' bir kontrol çubuğu değil") % k.hedef]
    if not (CUBUK_SINIR[0] <= k.sinir[0] and k.sinir[-1] <= CUBUK_SINIR[1]):
        return [_("kontrol çubuğu araması sınırı 0–100 daldırma yüzdesi içinde olmalı")]
    return []
