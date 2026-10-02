# -*- coding: utf-8 -*-
"""
 test_y6_tally.py  --  v3 Y6: kinetik tally ayari ve kosudan grup verisi

   - kurucu + uretilen betik: IFP beta payi DelayedGroupFilter(1..G) ile,
     lambda_i icin delayed-nu-fission + decay-rate tally'si (G = 0: eski tek
     toplam beta; grup tally'si yok)
   - kinetik_oku: beta_i = <IFP beta payi>_i / <payda>,
     lambda_i = <decay-rate>_i / <delayed-nu-fission>_i,
     Lambda = <zaman payi> / (<payda> k)  (OpenMC 0.16 get_kinetics_parameters)
   - kosucu.sonuc_oku Lambda'yi k'ya boler (eski kod bolmuyordu: l = Lambda k)
   - YAVAS: Godiva kucuk kosu; sum beta_i = beta_eff, lambda_i ENDF/B-VIII.0
     U-235 degerlerine yakin, Lambda ~ ns
"""

import copy
import importlib.util
import math
import os

import numpy as np

from testler.ortak_test import kontrol, KOK, ORNEK, ISLEM_PARCACIGI

from cekirdek import kinetik as kin
from cekirdek import kinetik_oku as ko
from cekirdek import sema

FIXTURE = os.path.join(KOK, "testler", "veri", "kosu_ornek")
# ENDF/B-VIII.0 U-235 gecikmis notron bozunma sabitleri [1/s] (HDF5 kutuphanesi,
# IncidentNeutron(U235).reactions[18].products[delayed].decay_rate ile okundu)
_U235_LAMBDA = (0.01334, 0.03274, 0.12078, 0.30278, 0.84949, 2.85300)


def _spec(gruplar):
    s = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    s = copy.deepcopy(s)
    s["ayarlar"]["kinetik"] = {"var": True, "nesil": 5, "gruplar": gruplar}
    return s


def _ozet(tallies):
    """{ad: (skorlar, [(filtre turu, kutular)])} -- kurucu/betik karsilastirmasi."""
    return {t.name: (tuple(t.scores), [(type(f).__name__, tuple(np.ravel(f.bins).tolist()))
                                       for f in t.filters])
            for t in tallies if t.name.startswith("IFP")}


def test_varsayilan_grup_sayisi():
    print("\n[Y6T-1] sema varsayilani: 6 grup (ENDF/B-VIII.0)")
    kontrol("VARSAYILAN_AYARLAR kinetik.gruplar = 6",
            sema.VARSAYILAN_AYARLAR["kinetik"].get("gruplar") == kin.VARSAYILAN_GRUP == 6)
    eski = sema.tamamla({"ayarlar": {"kinetik": {"var": True, "nesil": 10}}})
    kontrol("eski dosya tamamlaninca gruplar = 6", eski["ayarlar"]["kinetik"]["gruplar"] == 6)


def test_kurucu_grup_tallyleri():
    print("\n[Y6T-2] kurucu: IFP beta payi gruplu + lambda tally'si")
    from cekirdek import kurucu
    model, _bilgi = kurucu.kur(_spec(6))
    oz = _ozet(model.tallies)
    kontrol("IFP beta payi DelayedGroupFilter 1..6",
            oz.get("IFP beta numerator") == (("ifp-beta-numerator",),
                                             [("DelayedGroupFilter", (1, 2, 3, 4, 5, 6))]),
            "-> %r" % (oz.get("IFP beta numerator"),))
    kontrol("lambda tally'si: delayed-nu-fission + decay-rate, 6 grup",
            oz.get(ko.GRUP_TALLY_ADI) == (("delayed-nu-fission", "decay-rate"),
                                          [("DelayedGroupFilter", (1, 2, 3, 4, 5, 6))]),
            "-> %r" % (oz.get(ko.GRUP_TALLY_ADI),))
    kontrol("IFP nesil sayisi", model.settings.ifp_n_generation == 5)
    model0, _b = kurucu.kur(_spec(0))
    oz0 = _ozet(model0.tallies)
    kontrol("gruplar=0: toplam beta (filtresiz), lambda tally'si yok",
            oz0.get("IFP beta numerator") == (("ifp-beta-numerator",), [])
            and ko.GRUP_TALLY_ADI not in oz0, "-> %s" % oz0)
    for hatali in (-1, 9, "alti"):
        try:
            kurucu.kur(_spec(hatali))
            kontrol("gecersiz grup sayisi reddedildi: %r" % hatali, False)
        except ValueError:
            kontrol("gecersiz grup sayisi reddedildi: %r" % hatali, True)


def test_betik_ayni_tallyler(gecici=None):
    print("\n[Y6T-3] uretilen betik kurucu ile ayni kinetik tally'lerini kurar")
    import tempfile
    from cekirdek import kod_uret, kurucu
    for g in (6, 0):
        spec = _spec(g)
        model, _bilgi = kurucu.kur(spec)
        kod = kod_uret.uret(spec, "model.py")
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "model.py")
            with open(yol, "w", encoding="utf-8") as f:
                f.write(kod)
            sm = importlib.util.spec_from_file_location("y6_uretilen_%d" % g, yol)
            mod = importlib.util.module_from_spec(sm)
            eski = os.getcwd()
            os.chdir(d)
            try:
                sm.loader.exec_module(mod)
            finally:
                os.chdir(eski)
        kontrol("gruplar=%d: betik = kurucu" % g,
                _ozet(mod.model.tallies) == _ozet(model.tallies),
                "-> %s / %s" % (_ozet(mod.model.tallies), _ozet(model.tallies)))
        kontrol("gruplar=%d: betik nesil sayisi" % g,
                mod.model.settings.ifp_n_generation == model.settings.ifp_n_generation)


class _Tally:
    def __init__(self, degerler):
        self._d = {s: (np.asarray(m, float), np.asarray(e, float))
                   for s, (m, e) in degerler.items()}

    def get_values(self, scores, value="mean"):
        m, e = self._d[scores[0]]
        return (m if value == "mean" else e).reshape(-1, 1, 1)


class _Ufloat:
    def __init__(self, n, s):
        self.nominal_value, self.std_dev = n, s


class _SahteSP:
    def __init__(self, tallyler, k=1.25):
        self._t = tallyler
        self.keff = _Ufloat(k, 0.0)

    def get_tally(self, name):
        if name not in self._t:
            raise LookupError(name)
        return self._t[name]


def _sahte(beta_i, dnf, dr, k=1.25):
    return _SahteSP({
        "IFP beta numerator": _Tally({"ifp-beta-numerator": (beta_i, [1e-6] * len(beta_i))}),
        "IFP denominator": _Tally({"ifp-denominator": ([2.0], [0.0])}),
        "IFP time numerator": _Tally({"ifp-time-numerator": ([5e-5], [0.0])}),
        ko.GRUP_TALLY_ADI: _Tally({"delayed-nu-fission": (dnf, [0.0] * len(dnf)),
                                   "decay-rate": (dr, [0.0] * len(dr))}),
    }, k)


def test_statepoint_oku_sahte():
    print("\n[Y6T-4] kinetik_oku: beta_i, lambda_i, Lambda = zaman/(payda k)")
    lam = np.array(_U235_LAMBDA + (0.0, 0.0))
    dnf = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 0.0, 0.0])
    sp = _sahte([2e-4, 1e-3, 1e-3, 2e-3, 1e-3, 4e-4, 0.0, 0.0], dnf, lam * dnf)
    o = ko.statepoint_oku(sp)
    kontrol("bos kuyruk gruplari atildi (kutuphane 6 grup)", len(o["beta_i"]) == 6
            and o["kutuphane_grup"] == 6 and o["istenen_grup"] == 8)
    kontrol("beta_i = pay/payda", np.allclose(o["beta_i"], [1e-4, 5e-4, 5e-4, 1e-3, 5e-4, 2e-4]))
    kontrol("lambda_i = decay-rate / delayed-nu-fission", np.allclose(o["lambda_i"], _U235_LAMBDA))
    kontrol("Lambda = 5e-5 / (2 * 1.25)", math.isclose(o["nesil_suresi"], 2e-5))
    kontrol("beta_i sapmasi pozitif", all(s > 0 for s in o["beta_i_sapma"]))
    v = ko.grup_verisine(o)
    kontrol("GrupVerisi'ne cevrildi", isinstance(v, kin.GrupVerisi) and len(v.beta) == 6
            and math.isclose(v.beta_toplam, 2.8e-3) and v.nesil_suresi == o["nesil_suresi"])
    eksik = _SahteSP({"IFP denominator": _Tally({"ifp-denominator": ([2.0], [0.0])})})
    kontrol("grup tally'leri yoksa None", ko.statepoint_oku(eksik) is None)
    tek = _sahte([1e-3], [1.0], [0.08])
    kontrol("tek gruplu (filtresiz) beta payi: grup verisi yok", ko.statepoint_oku(tek) is None)


def test_kosucu_lambda_k_ile_bolunur():
    print("\n[Y6T-5] kosucu.sonuc_oku: Lambda = l / k (OpenMC tanimi)")
    from cekirdek import kosucu
    eski = kosucu._kinetik
    kosucu._kinetik = lambda ifp: {"beta_eff": 0.0065, "beta_eff_sapma": 1e-5,
                                   "lambda": 2e-5, "lambda_sapma": 1e-7}
    try:
        s = kosucu.sonuc_oku(kosucu.son_statepoint(FIXTURE))
    finally:
        kosucu._kinetik = eski
    k = s["keff"][0]
    kontrol("Lambda = 2e-5 / k", math.isclose(s["kinetik"]["lambda"], 2e-5 / k),
            "-> %.4e (k = %.5f)" % (s["kinetik"]["lambda"], k))
    kontrol("beta_eff degismedi", s["kinetik"]["beta_eff"] == 0.0065)
    kontrol("grup tally'si yoksa grup alani yok", "beta_i" not in s["kinetik"])


def test_godiva_ifp_gruplari(gecici):
    print("\n[Y6T-6] YAVAS: Godiva IFP 6 grup -- sum beta_i = beta_eff, lambda_i, Lambda")
    import openmc
    from cekirdek import kosucu, kurucu
    spec = sema.yukle(os.path.join(ORNEK, "godiva_kriter.json"))
    spec["ayarlar"].update(parcacik=4000, cevrim=60, pasif=20)
    spec["ayarlar"]["kinetik"] = {"var": True, "nesil": 10, "gruplar": 6}
    eski = os.getcwd()
    os.chdir(gecici)
    try:
        model, _bilgi = kurucu.kur(spec)
        yol = model.run(threads=ISLEM_PARCACIGI, output=False)
    finally:
        os.chdir(eski)
    s = kosucu.sonuc_oku(yol)
    k = s["kinetik"]
    resmi = openmc.StatePoint(yol).get_kinetics_parameters()
    kontrol("Lambda = OpenMC get_kinetics_parameters", math.isclose(
        k["lambda"], resmi.generation_time.nominal_value, rel_tol=1e-9),
        "-> %.4e / %.4e" % (k["lambda"], resmi.generation_time.nominal_value))
    kontrol("beta_i = OpenMC get_kinetics_parameters", np.allclose(
        k["beta_i"], [b.nominal_value for b in resmi.beta_effective], rtol=1e-9))
    kontrol("sum beta_i = beta_eff", math.isclose(sum(k["beta_i"]), k["beta_eff"], rel_tol=1e-9))
    kontrol("beta_eff 550-800 pcm (Godiva olcum ~ 645-660 pcm)",
            550e-5 < k["beta_eff"] < 800e-5, "-> %.0f pcm" % (k["beta_eff"] * 1e5))
    kontrol("Lambda 3-9 ns (Godiva ~ 5.7 ns)", 3e-9 < k["lambda"] < 9e-9,
            "-> %.2f ns" % (k["lambda"] * 1e9))
    sapma = max(abs(a / b - 1.0) for a, b in zip(k["lambda_i"], _U235_LAMBDA))
    kontrol("lambda_i ENDF/B-VIII.0 U-235 ile %5 icinde (Godiva ~%94 U-235)", sapma < 0.05,
            "-> %s" % ["%.4f" % x for x in k["lambda_i"]])
    v = ko.grup_verisine(k)
    coz = kin.coz(v, kin.Basamak(0.5 * v.beta_toplam), 1.0)
    kontrol("kosudan alinan veriyle cozum (Lambda ~ ns: kati)", coz.basarili and not coz.uyarilar)


HIZLI = [test_varsayilan_grup_sayisi, test_kurucu_grup_tallyleri, test_betik_ayni_tallyler,
         test_statepoint_oku_sahte, test_kosucu_lambda_k_ile_bolunur]
YAVAS = [test_godiva_ifp_gruplari]
VERI_GEREKEN = [test_godiva_ifp_gruplari]
