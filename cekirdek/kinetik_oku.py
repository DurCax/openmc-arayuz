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
           Bu, grup i icinde nuklidlerin lambda'larinin ONCUL URETIM HIZI
           (nu_d,i Sigma_f phi) agirlikli aritmetik ortalamasidir: ileri
           (eslenik agirliksiz) bir ortalama. beta_i ise eslenik agirliklidir;
           iki agirlik farklidir (tek baskin fisil nuklidde fark sifira gider).
           Envanteri koruyan harmonik ortalama (sum nu_d / sum nu_d/lambda)
           nuklid basina skor ister; burada yapilmaz. lambda_i nukleer veridir
           (ENDF/B-VIII.0: 6 grup, nuklide gore farkli lambda; JEFF-3.1+: 8 grup,
           tum nuklidlerde ayni).
 Grup sayisi kutuphaneyle eslesmelidir: ENDF/B -> 6, JEFF -> 8. Kutuphanede
 olmayan gruplar sifir skorlar ve okunurken atilir (kutuphane_grup). Ters
 durum (kutuphanede istenenden COK grup) filtresiz bir delayed-nu-fission
 tally'si (TOPLAM_TALLY_ADI) ile yakalanir: sum_i dnf_i / toplam < 1 ise
 beta_eff eksiktir ve "grup_uyari" yazilir.
 $ ve ani kritik esigi her yerde AYNI beta ile: sum_i beta_i (= gruplu IFP
 tally'sinin toplami = sonuc["kinetik"]["beta_eff"]).
================================================================================
"""

import math

from cekirdek.ceviri import _, N_
from cekirdek.gunluk import kaydedici
from cekirdek.kinetik import GrupVerisi, VARSAYILAN_GRUP

_log = kaydedici(__name__)

# "IFP " oneki: kosucu._tallyleri_oku bu tally'yi kullanici tally'si gibi listelemez.
GRUP_TALLY_ADI = "IFP gruplar lambda"
TOPLAM_TALLY_ADI = "IFP gruplar toplam"
_KAPSAM_TOLERANSI = 1e-6            # sum dnf_i / toplam bundan fazla 1'in altindaysa uyari
GECERLI_GRUP_SAYILARI = (0, 6, 8)   # 0: yalniz toplam beta; 6: ENDF/B; 8: JEFF
_GRUP_SKORLARI = ("delayed-nu-fission", "decay-rate")


def grup_sayisi(kin_ayari):
    """spec['ayarlar']['kinetik'] -> gecerli grup sayisi (ValueError)."""
    g = (kin_ayari or {}).get("gruplar", VARSAYILAN_GRUP)
    if isinstance(g, bool) or not isinstance(g, int) or g not in GECERLI_GRUP_SAYILARI:
        raise ValueError(_("Gecikmeli nötron grup sayısı 0, 6 ya da 8 olmalı: %r") % (g,))
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
        toplam = openmc.Tally(name=TOPLAM_TALLY_ADI)
        toplam.scores = [_GRUP_SKORLARI[0]]
        model.tallies.extend([t, toplam])
    model.settings.ifp_n_generation = _nesil(kin_ayari)


def _nesil(kin_ayari):
    return int((kin_ayari or {}).get("nesil") or 10)


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
            "# Grup kapsami denetimi: filtresiz delayed-nu-fission (kutuphanede daha cok grup?)",
            "_kin_toplam = openmc.Tally(name=%r)" % TOPLAM_TALLY_ADI,
            "_kin_toplam.scores = [%r]" % _GRUP_SKORLARI[0],
            "model.tallies.extend([_kin_grup, _kin_toplam])",
        ]
    satirlar.append("model.settings.ifp_n_generation = %d" % _nesil(kin_ayari))
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


def _tek_kutu(d, ad):
    """Payda/zaman/toplam tally'leri filtresizdir: TEK kutu beklenir."""
    if d is not None and len(d[0]) != 1:
        _log.warning("'%s' tally'si tek kutulu değil (%d); grup verisi okunmadı", ad, len(d[0]))
        return None
    return d


def _ham_degerler(sp):
    """Gerekli tally degerleri; biri eksik/uyumsuzsa None."""
    d = {"beta": _degerler(sp, "IFP beta numerator", "ifp-beta-numerator"),
         "payda": _tek_kutu(_degerler(sp, "IFP denominator", "ifp-denominator"), "payda"),
         "zaman": _tek_kutu(_degerler(sp, "IFP time numerator", "ifp-time-numerator"), "zaman"),
         "dnf": _degerler(sp, GRUP_TALLY_ADI, _GRUP_SKORLARI[0]),
         "dr": _degerler(sp, GRUP_TALLY_ADI, _GRUP_SKORLARI[1]),
         "toplam": _tek_kutu(_degerler(sp, TOPLAM_TALLY_ADI, _GRUP_SKORLARI[0]), "toplam")}
    if any(v is None for v in d.values()) or len(d["beta"][0]) < 2:
        return None
    if len(d["dnf"][0]) != len(d["beta"][0]):
        _log.warning("IFP beta ve lambda tally'lerinin grup sayısı farklı: %d / %d",
                     len(d["beta"][0]), len(d["dnf"][0]))
        return None
    if getattr(sp, "keff", None) is None:
        _log.warning("statepoint'te k_eff yok; Λ = ℓ/k hesaplanamaz, grup verisi okunmadı")
        return None
    return d


def _kapsam(dnf, toplam, istenen):
    """(sum dnf_i / toplam, uyari metni ya da None)."""
    if toplam <= 0:
        return 1.0, None
    oran = math.fsum(dnf) / toplam
    if oran >= 1.0 - _KAPSAM_TOLERANSI:
        return 1.0, None
    return oran, _(
        "İstenen %d grup gecikmeli nötron üretiminin yalnızca %%%.1f'ini kapsıyor: kütüphanede "
        "daha çok grup var (JEFF: 8). β_eff ve $ eksik çıkar; grup sayısını 8 yapıp yeniden "
        "koşun.") % (istenen, 100.0 * oran)


def statepoint_oku(sp):
    """
    Grup verisi: {"beta_i", "beta_i_sapma", "lambda_i", "lambda_i_sapma",
    "nesil_suresi", "nesil_suresi_sapma", "istenen_grup", "kutuphane_grup",
    "grup_kapsami" (+ "grup_uyari")}; gruplu IFP ya da lambda tally'si yoksa None.
    """
    d = _ham_degerler(sp)
    if d is None:
        return None
    (beta, sbeta), (dnf, sdnf), (dr, sdr) = d["beta"], d["dnf"], d["dr"]
    pd, spd = d["payda"][0][0], d["payda"][1][0]
    gruplar = [(_oran(b, sb, pd, spd), _oran(r, sr, n, sn))
               for b, sb, n, sn, r, sr in zip(beta, sbeta, dnf, sdnf, dr, sdr)]
    istenen = len(gruplar)
    while gruplar and gruplar[-1][1][0] == 0.0:
        gruplar.pop()          # kutuphanede olmayan grup: skor yok
    if not gruplar or any(lam == 0.0 for _b, (lam, _s) in gruplar):
        _log.warning("gecikmeli nötron grubu skorlanmadı (fisyon yok ya da veri eksik)")
        return None
    k = sp.keff
    lam_top, sp_lam = _oran(d["zaman"][0][0], d["zaman"][1][0], pd * k.nominal_value,
                            pd * k.nominal_value * math.hypot(spd / pd, k.std_dev / k.nominal_value))
    kapsam, uyari = _kapsam(dnf, d["toplam"][0][0], istenen)
    sonuc = {
        "beta_i": [b for (b, _s), _l in gruplar],
        "beta_i_sapma": [s for (_b, s), _l in gruplar],
        "lambda_i": [lam for _b, (lam, _s) in gruplar],
        "lambda_i_sapma": [s for _b, (_l, s) in gruplar],
        "nesil_suresi": lam_top, "nesil_suresi_sapma": sp_lam,
        "istenen_grup": istenen, "kutuphane_grup": len(gruplar), "grup_kapsami": kapsam,
    }
    if uyari:
        _log.warning("gecikmeli nötron grup kapsamı eksik: %.4f", kapsam)
        sonuc["grup_uyari"] = uyari
    return sonuc


# statepoint okuma hatalari (bozuk/eksik HDF5, beklenmeyen tally bicimi). Bunlarin
# disindaki istisnalar program hatasidir ve yukari cikar.
_OKUMA_HATALARI = (KeyError, ValueError, OSError, AttributeError, IndexError)


def kosu_kinetigi(temel, sp, keff):
    """
    kosucu._kinetik sonucu (temel: beta_eff, omur = l) + grup verisi -> YENI sozluk.
    Uretim zamani OpenMC tanimiyla Lambda = l / k ("lambda"); "omur" korunur.
    keff yoksa Lambda yerine l yazilir ve "lambda_uyari" eklenir.
    """
    yeni = dict(temel)
    omur, somur = temel["omur"], temel["omur_sapma"]
    if keff:
        k, sk = keff
        yeni["lambda"] = omur / k
        yeni["lambda_sapma"] = yeni["lambda"] * math.hypot(somur / omur, sk / k)
    else:
        _log.warning("k_eff yok: Λ = ℓ/k yerine ℓ yazıldı")
        yeni["lambda"], yeni["lambda_sapma"] = omur, somur
        yeni["lambda_uyari"] = _("k_eff yok: Λ yerine ani nötron ömrü ℓ yazıldı.")
    try:
        gruplar = statepoint_oku(sp)
    except _OKUMA_HATALARI as e:
        _log.exception("gecikmeli nötron grupları okunamadı")
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
                      nesil_suresi=lam, kaynak=kaynak or N_("OpenMC koşusu (IFP)"))
