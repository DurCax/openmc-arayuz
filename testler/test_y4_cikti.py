# -*- coding: utf-8 -*-
"""
 test_y4_cikti.py  --  v3 Y4: tukenme ciktilari (cekirdek/tukenme_cikti.py)

   [Y4-C1] ANALITIK BOZUNMA ISISI: saf Co60 malzemesi yalniz sogutma
           adimlariyla (guc 0) bozunur. P(t) = lambda N0 exp(-lambda t) Q;
           Q ve T1/2 zincirin kendisinden (ENDF/B-VIII.0 bozunum alt
           kutuphanesi, chain_endfb80_thermal.xml: Co60 decay_energy,
           half_life). Birimler: W ve W/g. Tolerans: CRAM48 ~1e-8 -> 1e-6
           (W); W/g'de malzeme kutlesi Co60 -> Ni60 bozunmasiyla 5e-5
           oraninda degisir (59.9338 / 59.9308 u) -> 1e-4.
   [Y4-C2] Aktivite A = lambda N (Bq, Bq/g); foton kaynagi / aktivite = Co60
           bozunma basina foton sayisi ~2 (1173 keV %99.85 + 1332 keV
           %99.98, NNDC) -> %1 icinde.
   [Y4-C3] Doz hizi ve atik sinifi: OpenMC Material.get_photon_contact_dose_rate
           (FISPACT-II yontemi) pozitif ve Gy/h; waste_classification
           (10 CFR 61.55) metin doner. Foton spektrumu: Co60 cizgileri.
   [Y4-C4] CSV: baslik + zaman satirlari, ondalik nokta.

 Fixture: transport'suz bozunma (IndependentOperator, sifir MicroXS,
 source_rates = 0): Monte Carlo KOSULMAZ, saniyeler surer.
"""

import csv
import io
import math
import os

from testler.ortak_test import kontrol
from testler.ortak_test import gereksinim  # v3 izlenebilirlik

EV_J = 1.602176634e-19          # CODATA 2018
AVOGADRO = 6.02214076e23
N0_YOGUNLUK = 1.0e-4            # atom/b-cm
HACIM = 2.0                     # cm3
SOGUMA_A = [1.0, 4.0]           # yil


def _zincir():
    from cekirdek import veri_bilgi
    return os.path.join(veri_bilgi.zincir_dizini(), "chain_endfb80_thermal.xml")


def _bozunma_h5(dizin):
    """Saf Co60, yalniz bozunma: depletion_results.h5 yolu ve malzeme id'si."""
    import numpy as np
    import openmc
    import openmc.deplete as d
    zincir = d.Chain.from_xml(_zincir())
    m = openmc.Material(name="kaynak")
    m.add_nuclide("Co60", N0_YOGUNLUK)
    m.set_density("sum")
    m.depletable = True
    m.volume = HACIM
    nuklidler = [n.name for n in zincir.nuclides]
    tepkimeler = ["(n,gamma)"]
    micro = d.MicroXS(np.zeros((len(nuklidler), 1, 1)), nuklidler, tepkimeler)
    op = d.IndependentOperator(openmc.Materials([m]), [np.array([0.0])], [micro],
                               chain_file=zincir, normalization_mode="source-rate")
    op.output_dir = dizin
    integ = d.PredictorIntegrator(op, SOGUMA_A, source_rates=[0.0] * len(SOGUMA_A),
                                  timestep_units="a")
    integ.integrate()
    return os.path.join(dizin, "depletion_results.h5"), str(m.id)


def _seriler(gecici):
    import openmc.deplete as d
    from cekirdek import tukenme_cikti
    h5, mid = _bozunma_h5(gecici)
    r = d.Results(h5)
    return tukenme_cikti.seriler(r, {mid: "kaynak"}, _zincir()), r, mid


@gereksinim("R-V3-21")
def test_bozunma_isisi_analitik(gecici):
    print("\n[Y4-C1] sogutmada bozunma isisi = lambda N0 e^-lambda t Q (W, W/g)")
    import openmc.deplete as d
    s, _r, _m = _seriler(gecici)
    co = d.Chain.from_xml(_zincir())["Co60"]
    lam = math.log(2.0) / co.half_life
    n0 = N0_YOGUNLUK * 1.0e24 * HACIM
    kutle0 = n0 * 59.9338 / AVOGADRO            # g (Co60 atom kutlesi, AME2020)
    zaman_s = [x * 86400.0 for x in s["zaman_d"]]
    isi = s["malzeme"]["kaynak"]["isi"]
    ozgul = s["malzeme"]["kaynak"]["isi_ozgul"]
    kontrol("zaman: 0, 1, 5 yil", [round(t / 86400.0 / 365.25, 6) for t in zaman_s] == [0, 1, 5],
            "-> %r" % s["zaman_d"])
    for t, p, pg in zip(zaman_s, isi, ozgul):
        beklenen = lam * n0 * math.exp(-lam * t) * co.decay_energy * EV_J
        kontrol("t = %.4g a: P = %.6e W (analitik %.6e)" % (t / 3.15576e7, p, beklenen),
                abs(p / beklenen - 1.0) < 1e-6)
        kontrol("  W/g = %.6e (analitik %.6e)" % (pg, beklenen / kutle0),
                abs(pg / (beklenen / kutle0) - 1.0) < 1e-4)
    kontrol("Q kaynagi zincirde: Co60 %.4g MeV (ENDF/B-VIII.0 ~2.60 MeV)" % (co.decay_energy / 1e6),
            abs(co.decay_energy / 1e6 - 2.60) < 0.01)


def test_aktivite_ve_foton(gecici):
    print("\n[Y4-C2] aktivite = lambda N; Co60 foton/bozunma ~ 2")
    import openmc.deplete as d
    s, _r, _m = _seriler(gecici)
    lam = math.log(2.0) / d.Chain.from_xml(_zincir())["Co60"].half_life
    n0 = N0_YOGUNLUK * 1.0e24 * HACIM
    k = s["malzeme"]["kaynak"]
    a0 = lam * n0
    kontrol("A(0) = %.6e Bq (analitik %.6e)" % (k["aktivite"][0], a0),
            abs(k["aktivite"][0] / a0 - 1.0) < 1e-6)
    kontrol("Bq/g = Bq / kutle", abs(k["aktivite_ozgul"][0] * (n0 * 59.9338 / AVOGADRO)
                                     / k["aktivite"][0] - 1.0) < 1e-4)
    oran = [f / a for f, a in zip(k["foton"], k["aktivite"])]
    kontrol("foton / aktivite = %s (NNDC: 1.9985)" % ["%.4f" % x for x in oran],
            all(abs(x - 1.9985) < 0.02 for x in oran))
    kontrol("toplam = malzemelerin toplami (tek malzeme)",
            s["toplam"]["isi"] == k["isi"] and s["toplam"]["aktivite"] == k["aktivite"])


def test_doz_atik_spektrum(gecici):
    print("\n[Y4-C3] temas doz hizi, atik sinifi, foton spektrumu (OpenMC Material)")
    from cekirdek import tukenme_cikti
    _s, r, mid = _seriler(gecici)
    tablo = tukenme_cikti.doz_ve_atik(r, {mid: "kaynak"}, _zincir(), adim=-1)
    satir = tablo["kaynak"]
    kontrol("doz hizi > 0 Gy/h", satir["doz_gy_h"] > 0, "-> %r" % satir)
    kontrol("atik sinifi metni", satir["atik_sinifi"] in ("Class A", "Class B", "Class C", "GTCC"),
            "-> %r" % satir["atik_sinifi"])
    e, y = tukenme_cikti.foton_spektrumu(r, mid, _zincir(), adim=0)
    cizgiler = sorted(x for x, w in zip(e, y) if w > 0.5 * max(y))
    kontrol("Co60 cizgileri 1.173 ve 1.332 MeV", len(cizgiler) == 2
            and abs(cizgiler[0] - 1.1732e6) < 1e3 and abs(cizgiler[1] - 1.3325e6) < 1e3,
            "-> %r" % cizgiler)


def test_csv(gecici):
    print("\n[Y4-C4] cikti CSV: baslik + zaman satirlari")
    from cekirdek import tukenme_cikti
    s, _r, _m = _seriler(gecici)
    metin = tukenme_cikti.csv_metni(s)
    satirlar = list(csv.reader(io.StringIO(metin)))
    kontrol("baslik + 3 satir", len(satirlar) == 4, "-> %d" % len(satirlar))
    kontrol("sutunlar: zaman ve malzeme basina isi", satirlar[0][0] == "gun"
            and any("kaynak" in b and "W" in b for b in satirlar[0]), "-> %r" % satirlar[0])
    kontrol("ondalik nokta", "," not in "".join(satirlar[1][0]))
    float(satirlar[2][1])


HIZLI = [test_bozunma_isisi_analitik, test_aktivite_ve_foton, test_doz_atik_spektrum, test_csv]
VERI_GEREKEN = HIZLI
ZINCIR_GEREKEN = HIZLI
