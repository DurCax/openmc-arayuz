# -*- coding: utf-8 -*-
"""
 test_y7_fizik.py  --  v3 Y7 Monte Carlo kabul testleri (YAVAS)

   1. Yuzey akimi korunumu, sabit kaynak (zirh_kure: 14 MeV fuzyon kaynagi,
      su + celik kure, vakum sinir):
        S + J_giren - J_cikan + U = A   (kutu dis yuzleri; U = nu-scatter - scatter)
      kaynagi iceren ve icermeyen iki kutu; aracin analog denge tally'siyle
      TAM (yalniz yuvarlama). Sinir akimi = global
      sizinti x siddet (ayni olaylar). Birim: kaynak parcacigi basina
      (siddet 1) -> siddet ile carpim birebir.
   2. Foton tasinimi acikken heating skorlari (pin hucre, yansitici):
      H_gama > 0, H = H_n + H_gama; temiz olcut H_gama / H (olculur, etiketli).
      heating-local ile esitlik SINANMAZ: OpenMC ozdegerde heating-local'i
      keff*kerma_fisyon-disi + kerma_fisyon ile agirliklandirir (Griesheimer
      vd., PHYSOR 2020), MT301 almaz; uyum garanti degildir. H / kappa-fission
      yalniz olculur (butce: ders 5.16).
   3. Sicaklik interpolasyonu: yakit 600 / 750 (ara) / 900 K;
      k(600) > k(750) > k(900) ve k(750) dogrusal ortadan 3 sigma icinde.
   4. Betik esdegerligi: foton + sicaklik + yuzey tally'leri acikken kurucu ve
      uretilen betik birebir ayni sonuc.
"""

import importlib.util
import math
import os

from cekirdek import sema
from testler.ortak_test import kontrol, ISLEM_PARCACIGI
from testler.regresyon_ortak import ORNEK
from testler.ortak_test import gereksinim  # v3 izlenebilirlik

_SIGMA = 3.0
_ANALOG_TOL = 1e-9          # analog denge her gecmiste tam: yalniz yuvarlama
_AYNI_TOL = 1e-9            # ayni olaylar, iki tahmin yolu
_KUTU_IC = ([-10.0, -10.0, -10.0], [10.0, 10.0, 10.0])      # kaynak icerde (su)
_KUTU_DIS = ([12.0, -6.0, -6.0], [24.0, 6.0, 6.0])         # kaynak disarida (su)
_SIDDET = 1.0e12


def _kos(model, dizin):
    os.makedirs(dizin, exist_ok=True)
    eski = os.getcwd()
    os.chdir(dizin)
    try:
        return model.run(threads=ISLEM_PARCACIGI, output=False)
    finally:
        os.chdir(eski)


def _kure(kuvvet=_SIDDET):
    from cekirdek import yuzey_akim as y
    spec = sema.yukle(os.path.join(ORNEK, "zirh_kure.json"))
    spec["ayarlar"].update(parcacik=4000, cevrim=5)
    spec["ayarlar"]["kaynak"]["kuvvet"] = kuvvet
    spec["tallyler"] = [
        dict(sema.tally("kacak", ["current"]),
             filtreler=[y.filtre_sinir(), sema.filtre_enerji([1e-5, 0.625, 1e5, 1e6, 2e7])]),
        dict(sema.tally("kutu_ic", ["current"]), filtreler=[y.filtre_kutu([2, 2, 2], *_KUTU_IC)]),
        dict(sema.tally("kutu_dis", ["current"]), filtreler=[y.filtre_kutu([1, 1, 1], *_KUTU_DIS)]),
    ]
    return spec


def _analog_ekle(model):
    """Tum model icin ANALOG notron dengesi tally'si (aracin kutu dengesiyle ayni skorlar)."""
    import openmc
    from cekirdek import yuzey_akim as y
    g = openmc.Tally(name="analog_model")
    g.scores = list(y.DENGE_SKORLARI)
    g.filters = [openmc.ParticleFilter(["neutron"])]
    g.estimator = "analog"
    model.tallies = openmc.Tallies(list(model.tallies) + [g])
    return model


def _analog_terimler(sp, ad):
    """(A, U): U = nu-scatter - scatter + nu-fission (sabit kaynak)."""
    df = sp.get_tally(name=ad).get_pandas_dataframe()

    def top(skor):
        return float(df[df["score"] == skor]["mean"].sum())
    return top("absorption"), top("nu-scatter") - top("scatter") + top("nu-fission")


@gereksinim("R-V3-19")
def test_sabit_kaynak_yuzey_akimi_korunumu(gecici):
    print("\n[Y7-F1] sabit kaynak: S + giren - cikan + U = A (kutu dis yuzleri)")
    import openmc
    from cekirdek import kurucu, yuzey_oku
    # Arrange
    spec = _kure()
    model = _analog_ekle(kurucu.kur(spec)[0])
    # Act
    yol = _kos(model, os.path.join(gecici, "kure"))
    sonuc = {r["ad"]: r for r in yuzey_oku.oku(yol, spec)}
    sp = openmc.StatePoint(yol)
    # Assert -- sinir
    s = sonuc["kacak"]
    g = s["global_sizinti"]
    print("  kacak %.6e +- %.2e, global %.6e" % (s["toplam"].ort, s["toplam"].sapma, g.ort))
    kontrol("sinir akimi = global sizinti x siddet (ayni olaylar)",
            abs(s["toplam"].ort - g.ort) <= _AYNI_TOL * g.ort)
    kontrol("kacak spektrumu toplami = toplam",
            abs(sum(s["spektrum"]["deger"]) - s["toplam"].ort) <= _AYNI_TOL * s["toplam"].ort)
    ham = sp.get_tally(name="kacak").get_pandas_dataframe()["mean"]
    kontrol("isaret: OpenMC net akim dis normal (+) yonunde (kure)", (ham >= 0).all())
    # tum model: S - L + X = A (analog)
    a_m, u_m = _analog_terimler(sp, "analog_model")
    artik = _SIDDET - g.ort + u_m - a_m
    print("  model: S=%.4e L=%.4e U=%.4e A=%.4e artik/S=%.2e" % (_SIDDET, g.ort, u_m, a_m,
                                                                artik / _SIDDET))
    kontrol("tum model analog denge tam", abs(artik) <= _ANALOG_TOL * _SIDDET)
    for ad in ("kutu_ic", "kutu_dis"):
        _kutu_dengesi(sp, sonuc[ad], ad)


def _kutu_dengesi(sp, r, ad):
    t = r["terimler"]
    s, artik = r["kaynak"].ort, r["denge"]["artik"]
    olcek = max(r["cikan"].ort, t["A"].ort, 1.0)
    print("  %s: S=%.3e giren=%.4e cikan=%.4e U=%.3e (sacilma %.3e) A=%.4e artik=%.2e +- %.2e"
          % (ad, s, r["giren"].ort, r["cikan"].ort, t["U"].ort, t["X"].ort, t["A"].ort,
             artik.ort, artik.sapma))
    kontrol("%s: S + giren - cikan + U = A (analog, 1e-9)" % ad,
            abs(artik.ort) <= _ANALOG_TOL * olcek, "-> artik/olcek %.2e" % (artik.ort / olcek))
    if ad == "kutu_ic":
        kontrol("kaynak icerde: S = siddet, net cikan > 0", s == _SIDDET and r["net_cikan"].ort > 0)
    else:
        kontrol("kaynak disarida: S = 0, giren > cikan (net soğurma)",
                s == 0.0 and r["giren"].ort > r["cikan"].ort)


def test_birim_kaynak_parcacigi_basina(gecici):
    print("\n[Y7-F2] siddet 1: kaynak parcacigi basina; siddet ile carpim birebir")
    from cekirdek import kurucu, yuzey_oku
    # Arrange
    a, b = _kure(1.0), _kure(_SIDDET)
    for s in (a, b):
        s["ayarlar"].update(parcacik=1000, cevrim=3)
    # Act
    ra = {r["ad"]: r for r in yuzey_oku.oku(_kos(kurucu.kur(a)[0], os.path.join(gecici, "a")), a)}
    rb = {r["ad"]: r for r in yuzey_oku.oku(_kos(kurucu.kur(b)[0], os.path.join(gecici, "b")), b)}
    # Assert
    ka, kb = ra["kacak"]["toplam"].ort, rb["kacak"]["toplam"].ort
    print("  kacak / kaynak parcacigi = %.5f" % ka)
    kontrol("0 < kacak < 1 parcacik basina", 0.0 < ka < 1.0)
    kontrol("siddetle birebir olcek", abs(kb - _SIDDET * ka) <= _AYNI_TOL * kb)
    kontrol("kutu_ic: S = 1", ra["kutu_ic"]["kaynak"].ort == 1.0)


def _pin(foton_var):
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    spec["ayarlar"].update(parcacik=2000, cevrim=30, pasif=10)
    spec["ayarlar"]["foton"] = {"var": foton_var}
    spec["tallyler"] = [sema.tally("isi", ["heating", "heating-local", "kappa-fission",
                                           "damage-energy"])]
    return spec


def _isinma(yol):
    import openmc
    with openmc.StatePoint(yol) as sp:
        df = sp.get_tally(name="isi").get_pandas_dataframe()
        p = sp.get_tally(name="isi_parcacik").get_pandas_dataframe()
    d = {r["score"]: (float(r["mean"]), float(r["std. dev."])) for _i, r in df.iterrows()}
    d.update({"H_" + r["particle"]: (float(r["mean"]), float(r["std. dev."]))
              for _i, r in p.iterrows()})
    return d


def _parcacik_tallysi(model):
    import openmc
    t = openmc.Tally(name="isi_parcacik")
    t.filters = [openmc.ParticleFilter(["neutron", "photon"])]
    t.scores = ["heating"]
    model.tallies = openmc.Tallies(list(model.tallies) + [t])
    return model


@gereksinim("R-V3-20")
def test_foton_acik_isinma_skorlari(gecici):
    print("\n[Y7-F3] foton acik: heating = H_n + H_gama; sonsuz kafeste ~ heating-local")
    from cekirdek import kurucu
    # Arrange / Act
    sonuc = {}
    for var in (False, True):
        model = _parcacik_tallysi(kurucu.kur(_pin(var))[0])
        sonuc[var] = _isinma(_kos(model, os.path.join(gecici, "foton_%s" % var)))
    kapali, acik = sonuc[False], sonuc[True]
    # Assert
    h, hl, kf = acik["heating"], acik["heating-local"], acik["kappa-fission"]
    hn, hg = acik["H_neutron"], acik["H_photon"]
    print("  foton acik : H=%.4e H_n=%.4e H_g=%.4e (pay %.3f) H_local=%.4e kF=%.4e H/kF=%.4f"
          % (h[0], hn[0], hg[0], hg[0] / h[0], hl[0], kf[0], h[0] / kf[0]))
    for etiket, d in (("acik", acik), ("kapali", kapali)):
        print("  sigma %s: " % etiket + ", ".join("%s %.4e+-%.1e" % (a, v[0], v[1])
                                                  for a, v in sorted(d.items())))
    print("  foton kapali: H=%.4e H_local=%.4e kF=%.4e H/H_local=%.4f"
          % (kapali["heating"][0], kapali["heating-local"][0], kapali["kappa-fission"][0],
             kapali["heating"][0] / kapali["heating-local"][0]))
    kontrol("foton acik: H_gama > 0", hg[0] > 0)
    kontrol("foton kapali: H_gama = 0", kapali["H_photon"][0] == 0.0)
    sinir = _SIGMA * math.sqrt(h[1] ** 2 + hn[1] ** 2 + hg[1] ** 2)
    kontrol("H = H_n + H_gama (3 sigma; carpisma/iz tahmincileri)",
            abs(h[0] - hn[0] - hg[0]) <= sinir, "-> fark %.3e sinir %.3e" % (h[0] - hn[0] - hg[0],
                                                                            sinir))
    pay = hg[0] / h[0]
    pay_s = pay * math.hypot(hg[1] / hg[0], h[1] / h[0])
    print("  temiz olcut H_gama / H = %.4f +- %.4f (heating-local / kF yalniz olculur)"
          % (pay, pay_s))
    kontrol("0 < H_gama / H < 1", 0.0 < pay < 1.0)
    kontrol("damage-energy foton kipinden bagimsiz (3 sigma)",
            abs(acik["damage-energy"][0] - kapali["damage-energy"][0])
            <= _SIGMA * math.hypot(acik["damage-energy"][1], kapali["damage-energy"][1]))


def _yakit_sicakligi(t):
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    spec["ayarlar"].update(parcacik=30000, cevrim=100, pasif=20, sicaklik_yontemi="interpolation")
    next(m for m in spec["malzemeler"] if m["ad"] == "uo2")["sicaklik"] = t
    return spec


@gereksinim("R-V3-20")
def test_sicaklik_interpolasyonu_ara_sicaklik(gecici):
    print("\n[Y7-F4] interpolation: k(600) > k(750) > k(900), k(750) ~ dogrusal orta (3 sigma)")
    import openmc
    from cekirdek import kurucu
    from cekirdek.dogrula import y7
    # Arrange
    sicakliklar = (600.0, 750.0, 900.0)
    # Act
    k = {}
    for t in sicakliklar:
        spec = _yakit_sicakligi(t)
        if t == 750.0:
            b = y7.y7_kontrol(spec)
            kontrol("750 K: dogrulama 600-900 K interpolasyon bilgisi",
                    any(x.seviye == "bilgi" and "600–900" in x.mesaj for x in b))
        with openmc.StatePoint(_kos(kurucu.kur(spec)[0], os.path.join(gecici, "T%d" % t))) as sp:
            k[t] = (sp.keff.nominal_value, sp.keff.std_dev)
    # Assert
    for t in sicakliklar:
        print("  T_yakit = %4.0f K  k = %.5f +- %.5f" % (t, k[t][0], k[t][1]))
    d1, d2 = k[600.0][0] - k[750.0][0], k[750.0][0] - k[900.0][0]
    s1 = math.hypot(k[600.0][1], k[750.0][1])
    s2 = math.hypot(k[750.0][1], k[900.0][1])
    kontrol("monoton: k(600) > k(750) (3 sigma)", d1 > _SIGMA * s1, "-> %.5f / %.5f" % (d1, s1))
    kontrol("monoton: k(750) > k(900) (3 sigma)", d2 > _SIGMA * s2, "-> %.5f / %.5f" % (d2, s2))
    orta = 0.5 * (k[600.0][0] + k[900.0][0])
    so = math.sqrt(0.25 * (k[600.0][1] ** 2 + k[900.0][1] ** 2) + k[750.0][1] ** 2)
    # Bu sinama interpolasyonun UYGULANDIGINI gosterir, fizik dogrulugunu degil:
    # sqrt(T) egrilik farki ~-25 pcm cozunurluk altinda; stokastik karisim gercek
    # Doppler genislemesi degildir (profesor D7).
    kontrol("k(750) dogrusal ortadan 3 sigma icinde (interpolasyon uygulandi)",
            abs(k[750.0][0] - orta) <= _SIGMA * so,
            "-> fark %.5f sinir %.5f" % (k[750.0][0] - orta, _SIGMA * so))
    print("  adimlar: %.1f sigma, %.1f sigma (sigma_fark = sqrt(s1^2 + s2^2))" % (d1 / s1, d2 / s2))
    k6, k9 = k[600.0][0], k[900.0][0]
    alfa = 1e5 * (k9 - k6) / (k9 * k6) / 300.0
    alfa_s = 1e5 * math.hypot(k[900.0][1] / k9 ** 2, k[600.0][1] / k6 ** 2) / 300.0
    print("  Doppler katsayisi (600-900 K): %.2f +- %.2f pcm/K" % (alfa, alfa_s))


def _betik_modeli(spec, dizin):
    from cekirdek import kod_uret
    yol = os.path.join(dizin, "model.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kod_uret.uret(spec, "model.py"))
    eski = os.getcwd()
    os.chdir(dizin)
    try:
        sm = importlib.util.spec_from_file_location("y7_fizik_betik", yol)
        mod = importlib.util.module_from_spec(sm)
        sm.loader.exec_module(mod)
    finally:
        os.chdir(eski)
    return mod.model


def test_betik_esdegerligi_y7(gecici):
    print("\n[Y7-F5] foton + sicaklik + yuzey tally'leri: kurucu = betik (birebir)")
    from cekirdek import kurucu, yuzey_oku
    # Arrange
    spec = _kure(1.0)
    spec["ayarlar"].update(parcacik=500, cevrim=3)
    spec["ayarlar"]["foton"] = {"var": True, "elektron": "led"}
    spec["ayarlar"]["sicaklik"] = {"tolerans": 20.0}
    # Act
    ya = _kos(kurucu.kur(spec)[0], os.path.join(gecici, "a"))
    dizin_b = os.path.join(gecici, "b")
    os.makedirs(dizin_b, exist_ok=True)
    yb = _kos(_betik_modeli(spec, dizin_b), dizin_b)
    ra = {r["ad"]: r for r in yuzey_oku.oku(ya, spec)}
    rb = {r["ad"]: r for r in yuzey_oku.oku(yb, spec)}
    # Assert
    for ad in ("kacak", "kutu_ic", "kutu_dis"):
        a_ = ra[ad]["toplam"].ort if ad == "kacak" else ra[ad]["cikan"].ort
        b_ = rb[ad]["toplam"].ort if ad == "kacak" else rb[ad]["cikan"].ort
        kontrol("%s birebir" % ad, abs(a_ - b_) <= 1e-12 * max(abs(a_), 1.0), "-> %r / %r"
                % (a_, b_))


HIZLI = []
YAVAS = [test_sabit_kaynak_yuzey_akimi_korunumu, test_birim_kaynak_parcacigi_basina,
         test_foton_acik_isinma_skorlari, test_sicaklik_interpolasyonu_ara_sicaklik,
         test_betik_esdegerligi_y7]
