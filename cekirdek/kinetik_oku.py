# -*- coding: utf-8 -*-
"""
================================================================================
 kinetik_oku.py  --  Kinetik tally ayari ve kosudan gecikmis notron gruplari
================================================================================
 Kurucu ve uretilen betik AYNI tally'leri kurar (testler/test_y6_tally.py).

 KAYNAKLAR (OpenMC 0.16 kaynagi ile dogrulandi)
   beta_i  Model.add_kinetics_parameters_tallies(num_groups=G): "IFP beta
           numerator" tally'sine DelayedGroupFilter(1..G) ekler. IFP (Iterated
           Fission Probability) ESLENIK AGIRLIKLI etkin kesirdir:
               beta_eff,i = <IFP beta payi>_i / <IFP payda>
   Lambda  StatePoint.get_kinetics_parameters ile ayni tanim:
               Lambda = <IFP zaman payi> / (<IFP payda> k_eff)
   lambda_i  IFP lambda VERMEZ. Ayri bir tally (GRUP_TALLY_ADI) ile
           DelayedGroupFilter(1..G) uzerinde "decay-rate" ve "delayed-nu-fission"
           skorlanir; openmc.mgxs.DecayRate ile ayni tanim:
               lambda_i = <lambda_i nu_d,i Sigma_f phi> / <nu_d,i Sigma_f phi>
           Bu, grup i'nin fisyon kaynakli (eslenik agirliksiz) karisim
           ortalamasidir; lambda_i nukleer veridir (ENDF/B-VIII.0: 6 grup ve
           nuklide gore farkli lambda; JEFF-3.1+: 8 grup, tum nuklidlerde ayni).
 Grup sayisi kutuphaneyle eslesmelidir: ENDF/B -> 6, JEFF -> 8. Kutuphanede
 olmayan gruplar sifir skorlar ve okunurken atilir (kutuphane_grup).
================================================================================
"""

import math

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from cekirdek.kinetik import GrupVerisi, VARSAYILAN_GRUP

_log = kaydedici(__name__)

# "IFP " oneki: kosucu._tallyleri_oku bu tally'yi kullanici tally'si gibi listelemez.
GRUP_TALLY_ADI = "IFP gruplar lambda"
GECERLI_GRUP_SAYILARI = (0, 6, 8)   # 0: yalniz toplam beta; 6: ENDF/B; 8: JEFF
_GRUP_SKORLARI = ("delayed-nu-fission", "decay-rate")


def grup_sayisi(kin_ayari):
    """spec['ayarlar']['kinetik'] -> gecerli grup sayisi (ValueError)."""
    g = (kin_ayari or {}).get("gruplar", VARSAYILAN_GRUP)
    if isinstance(g, bool) or not isinstance(g, int) or g not in GECERLI_GRUP_SAYILARI:
        raise ValueError(_("Gecikmiş nötron grup sayısı 0, 6 ya da 8 olmalı: %r") % (g,))
    return g


def tallyleri_ekle(model, kin_ayari):
    """IFP tally'leri (+ G > 0 ise grup ve lambda tally'si) modele EKLENIR."""
    import openmc
    g = grup_sayisi(kin_ayari)
    model.add_kinetics_parameters_tallies(num_groups=g or None)
    if g:
        t = openmc.Tally(name=GRUP_TALLY_ADI)
        t.filters = [openmc.DelayedGroupFilter(list(range(1, g + 1)))]
        t.scores = list(_GRUP_SKORLARI)
        model.tallies.append(t)
    model.settings.ifp_n_generation = int(kin_ayari.get("nesil") or 10)


def betik_satirlari(kin_ayari):
    """tallyleri_ekle'nin uretilen betikteki karsiligi (satir listesi)."""
    g = grup_sayisi(kin_ayari)
    satirlar = ["model.add_kinetics_parameters_tallies(num_groups=%s)" % (g or None)]
    if g:
        satirlar += [
            "# λ_i (öncül bozunma sabitleri): decay-rate / delayed-nu-fission, grup başına",
            "_kin_grup = openmc.Tally(name=%r)" % GRUP_TALLY_ADI,
            "_kin_grup.filters = [openmc.DelayedGroupFilter(list(range(1, %d)))]" % (g + 1),
            "_kin_grup.scores = %r" % list(_GRUP_SKORLARI),
            "model.tallies.append(_kin_grup)",
        ]
    satirlar.append("model.settings.ifp_n_generation = %d" % int(kin_ayari.get("nesil") or 10))
    return satirlar


# ============================================================================
# okuma
# ============================================================================

def _degerler(sp, ad, skor):
    """(ortalamalar, sapmalar) listeleri; tally yoksa None."""
    try:
        t = sp.get_tally(name=ad)
    except LookupError:
        _log.debug("'%s' tally'si statepoint'te yok", ad)
        return None
    o = [float(x) for x in t.get_values(scores=[skor]).ravel()]
    s = [float(x) for x in t.get_values(scores=[skor], value="std_dev").ravel()]
    return o, s


def _oran(pay, sp_pay, payda, sp_payda):
    """pay/payda ve bagimsiz kabul edilen bagil belirsizlik (ust sinir)."""
    if payda <= 0 or pay <= 0:
        return 0.0, 0.0
    r = pay / payda
    return r, r * math.hypot(sp_pay / pay, sp_payda / payda)


def statepoint_oku(sp):
    """
    Grup verisi: {"beta_i", "beta_i_sapma", "lambda_i", "lambda_i_sapma",
    "nesil_suresi", "nesil_suresi_sapma", "istenen_grup", "kutuphane_grup"};
    gruplu IFP ya da lambda tally'si yoksa None.
    """
    beta = _degerler(sp, "IFP beta numerator", "ifp-beta-numerator")
    payda = _degerler(sp, "IFP denominator", "ifp-denominator")
    zaman = _degerler(sp, "IFP time numerator", "ifp-time-numerator")
    dnf = _degerler(sp, GRUP_TALLY_ADI, _GRUP_SKORLARI[0])
    dr = _degerler(sp, GRUP_TALLY_ADI, _GRUP_SKORLARI[1])
    if None in (beta, payda, zaman, dnf, dr) or len(beta[0]) < 2:
        return None
    if len(dnf[0]) != len(beta[0]):
        _log.warning("IFP beta ve lambda tally'lerinin grup sayısı farklı: %d / %d",
                     len(beta[0]), len(dnf[0]))
        return None
    pd, spd = payda[0][0], payda[1][0]
    gruplar = [(_oran(b, sb, pd, spd), _oran(r, sr, n, sn))
               for b, sb, n, sn, r, sr in zip(beta[0], beta[1], dnf[0], dnf[1], dr[0], dr[1])]
    istenen = len(gruplar)
    while gruplar and gruplar[-1][1][0] == 0.0:
        gruplar.pop()          # kutuphanede olmayan grup: skor yok
    if not gruplar or any(lam == 0.0 for _b, (lam, _s) in gruplar):
        _log.warning("gecikmiş nötron grubu skorlanmadı (fisyon yok ya da veri eksik)")
        return None
    k = sp.keff
    lam_top, sp_lam = _oran(zaman[0][0], zaman[1][0], pd * k.nominal_value,
                            pd * k.nominal_value * math.hypot(spd / pd, k.std_dev / k.nominal_value))
    return {
        "beta_i": [b for (b, _s), _l in gruplar],
        "beta_i_sapma": [s for (_b, s), _l in gruplar],
        "lambda_i": [lam for _b, (lam, _s) in gruplar],
        "lambda_i_sapma": [s for _b, (_l, s) in gruplar],
        "nesil_suresi": lam_top, "nesil_suresi_sapma": sp_lam,
        "istenen_grup": istenen, "kutuphane_grup": len(gruplar),
    }


def kosu_kinetigi(temel, sp, keff):
    """
    kosucu._kinetik sonucu (temel) + grup verisi -> YENI sozluk.
    Lambda: temel["lambda"] IFP zaman payi/payda'dir (= l, ani omur); OpenMC
    tanimiyla uretim zamani Lambda = l / k olarak duzeltilir.
    """
    k, sk = keff if keff else (1.0, 0.0)
    yeni = dict(temel)
    yeni["lambda"] = temel["lambda"] / k
    yeni["lambda_sapma"] = yeni["lambda"] * math.hypot(
        temel["lambda_sapma"] / temel["lambda"], sk / k)
    try:
        gruplar = statepoint_oku(sp)
    except Exception as e:
        _log.exception("gecikmiş nötron grupları okunamadı")
        yeni["grup_hata"] = str(e)
        gruplar = None
    if gruplar:
        yeni.update({a: v for a, v in gruplar.items() if a != "nesil_suresi"
                     and a != "nesil_suresi_sapma"})
    return yeni


def grup_verisine(okunan, kaynak=None):
    """statepoint_oku / sonuc['kinetik'] sozlugu -> GrupVerisi."""
    lam = okunan.get("nesil_suresi", okunan.get("lambda"))
    return GrupVerisi(beta=tuple(okunan["beta_i"]), lam=tuple(okunan["lambda_i"]),
                      nesil_suresi=lam, kaynak=kaynak or _("OpenMC koşusu (IFP)"))
