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
    print("\n[Y6T-1] gruplar varsayilani 6 (ENDF/B-VIII.0); sema varsayilanina YAZILMAZ")
    kontrol("VARSAYILAN_AYARLAR kinetik'te 'gruplar' yok (kinetik kapali modelin spec'i "
            "ve onbellek ozeti degismez)", "gruplar" not in sema.VARSAYILAN_AYARLAR["kinetik"])
    eski = sema.tamamla({"ayarlar": {"kinetik": {"var": True, "nesil": 10}}})
    kontrol("eski dosya: anahtar eklenmez, okuyucu 6 kabul eder",
            "gruplar" not in eski["ayarlar"]["kinetik"]
            and ko.grup_sayisi(eski["ayarlar"]["kinetik"]) == kin.VARSAYILAN_GRUP == 6)
    kontrol("grup_sayisi(None) = 6", ko.grup_sayisi(None) == 6)


def test_dogrula_grup_sayisi():
    print("\n[Y6T-1b] dogrula: gecersiz kinetik.gruplar -> HATA (kurucudan once)")
    from cekirdek import dogrula
    for g, beklenen in ((7, True), ("alti", True), (6, False), (0, False), (8, False)):
        s = _spec(g)
        bulgu = [b for b in dogrula.tum_kontroller(s, veri_kontrolu=False)
                 if b.seviye == "hata" and "grup sayısı" in b.mesaj]
        kontrol("gruplar=%r -> hata %s" % (g, beklenen), bool(bulgu) == beklenen,
                "-> %s" % [b.mesaj for b in bulgu])
    s = _spec(7)
    s["ayarlar"]["kinetik"]["var"] = False
    kontrol("kinetik kapaliyken grup sayisi denetlenmez",
            not [b for b in dogrula.tum_kontroller(s, veri_kontrolu=False)
                 if "grup sayısı" in b.mesaj])


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
    kontrol("toplam dnf tally'si (filtresiz): kapsam denetimi",
            oz.get(ko.TOPLAM_TALLY_ADI) == (("delayed-nu-fission",), []),
            "-> %r" % (oz.get(ko.TOPLAM_TALLY_ADI),))
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


def _sahte(beta_i, dnf, dr, k=1.25, dnf_toplam=None):
    toplam = float(np.sum(dnf)) if dnf_toplam is None else dnf_toplam
    return _SahteSP({
        ko.TOPLAM_TALLY_ADI: _Tally({"delayed-nu-fission": ([toplam], [0.0])}),
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
    kontrol("kapsam tam: uyari yok", o["grup_kapsami"] == 1.0 and "grup_uyari" not in o)


def test_grup_kapsami_uyarisi():
    print("\n[Y6T-4b] kutuphanede istenenden cok grup: sum dnf_i < toplam -> uyari")
    dnf = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    sp = _sahte([2e-4, 1e-3, 1e-3, 2e-3, 1e-3, 4e-4], dnf, np.array(_U235_LAMBDA) * dnf,
                dnf_toplam=21.0 / 0.9)
    o = ko.statepoint_oku(sp)
    kontrol("kapsam %90", math.isclose(o["grup_kapsami"], 0.9), "-> %r" % o.get("grup_kapsami"))
    kontrol("uyari metni grup sayisini soyler", "6" in o.get("grup_uyari", "")
            and "8" in o.get("grup_uyari", ""), "-> %r" % o.get("grup_uyari"))
    temel = {"beta_eff": 0.0056, "beta_eff_sapma": 1e-5, "omur": 5e-5, "omur_sapma": 0.0}
    kin_s = ko.kosu_kinetigi(temel, sp, (1.25, 0.0))
    kontrol("uyari sonuc sozlugune tasinir", kin_s.get("grup_uyari") == o["grup_uyari"])


def test_kosu_kinetigi_hata_yollari():
    print("\n[Y6T-4c] kosu_kinetigi: dar istisna, keff yok, tek kutu denetimi")
    temel = {"beta_eff": 0.0065, "beta_eff_sapma": 1e-5, "omur": 2e-5, "omur_sapma": 1e-7}

    class _Bozuk(_SahteSP):
        def __init__(self, istisna):
            super().__init__({})
            self._i = istisna

        def get_tally(self, name):
            raise self._i

    k = ko.kosu_kinetigi(temel, _Bozuk(OSError("bozuk h5")), (1.0, 0.0))
    kontrol("okuma hatasi -> grup_hata, lambda yine var",
            "bozuk h5" in k.get("grup_hata", "") and k["lambda"] == 2e-5)
    try:
        ko.kosu_kinetigi(temel, _Bozuk(ZeroDivisionError("program hatasi")), (1.0, 0.0))
        kontrol("beklenmeyen istisna yutulmaz", False)
    except ZeroDivisionError:
        kontrol("beklenmeyen istisna yutulmaz", True)
    yok = ko.kosu_kinetigi(temel, _SahteSP({}), None)
    kontrol("keff yok: Lambda = omur (ozgun), uyari", yok["lambda"] == 2e-5
            and bool(yok.get("lambda_uyari")) and yok["omur"] == 2e-5)
    kontrol("girdi sozlugu degismedi", temel == {"beta_eff": 0.0065, "beta_eff_sapma": 1e-5,
                                                 "omur": 2e-5, "omur_sapma": 1e-7})
    cift = _sahte([1e-3, 2e-3], [1.0, 2.0], [0.0133, 0.0654])
    cift._t["IFP denominator"] = _Tally({"ifp-denominator": ([2.0, 3.0], [0.0, 0.0])})
    kontrol("payda tek kutulu degilse grup verisi yok", ko.statepoint_oku(cift) is None)
    sifirk = _sahte([1e-3, 2e-3], [1.0, 2.0], [0.0133, 0.0654])
    sifirk.keff = None
    kontrol("sp.keff None: grup verisi yok (cokmez)", ko.statepoint_oku(sifirk) is None)


def test_kosucu_lambda_k_ile_bolunur():
    print("\n[Y6T-5] kosucu.sonuc_oku: Lambda = l / k (OpenMC tanimi)")
    from cekirdek import kosucu
    eski = kosucu._kinetik
    kosucu._kinetik = lambda ifp: {"beta_eff": 0.0065, "beta_eff_sapma": 1e-5,
                                   "omur": 2e-5, "omur_sapma": 1e-7}
    try:
        s = kosucu.sonuc_oku(kosucu.son_statepoint(FIXTURE))
    finally:
        kosucu._kinetik = eski
    k = s["keff"][0]
    kontrol("Lambda = 2e-5 / k", math.isclose(s["kinetik"]["lambda"], 2e-5 / k),
            "-> %.4e (k = %.5f)" % (s["kinetik"]["lambda"], k))
    kontrol("beta_eff degismedi, omur (l) korunur", s["kinetik"]["beta_eff"] == 0.0065
            and s["kinetik"]["omur"] == 2e-5)
    gercek = kosucu._kinetik({"IFP beta numerator": (0.0065, 0.0),
                              "IFP time numerator": (2e-5, 0.0), "IFP denominator": (1.0, 0.0)})
    kontrol("kosucu._kinetik ara degeri 'omur' (l) anahtariyla doner",
            gercek["omur"] == 2e-5 and "lambda" not in gercek)
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


HIZLI = [test_varsayilan_grup_sayisi, test_dogrula_grup_sayisi, test_kurucu_grup_tallyleri, test_betik_ayni_tallyler,
         test_statepoint_oku_sahte, test_grup_kapsami_uyarisi, test_kosu_kinetigi_hata_yollari,
         test_kosucu_lambda_k_ile_bolunur]
YAVAS = [test_godiva_ifp_gruplari]
VERI_GEREKEN = [test_godiva_ifp_gruplari]
