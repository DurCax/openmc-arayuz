# -*- coding: utf-8 -*-
"""
test_vv.py -- Dalga S-3: NUREG/CR-6698 istatistigi, V&V kumesi, AOA, Profil B uctan uca.

NE SINANIR (hepsi HIZLI; Monte Carlo yok)
  [VV1] NUREG/CR-6698 Tablo 3.1'in 25 vakasiyla belgenin sayilari (STANDARTLAR.md §4.9):
        agirlikli k̄, s², σ̄², S_p, U(25), K_L, USL; egilim a, b, x̄, s_fit², bant K_L(x);
        parametrik olmayan β; Shapiro-Wilk W.
  [VV2] U(n) Tablo 2.1 ile 3 ondalikta ortusur; n > 50 icin n = 50 degeri kullanilir.
  [VV3] Kurallar: pozitif yanlilik kredilendirilmez (eş. 8); normallestirme k/k_exp (eş. 9);
        ΔSM < 0.02 reddedilir; parametrik olmayan β ≤ %40 -> USL yok; NPM tablosu.
  [VV4] Yontem secimi: normal + egilimsiz -> tolerans_siniri; normal + egilim ->
        tolerans_bandi; normal degil -> parametrik_olmayan; n < 3 -> USL hesaplanamadi.
  [VV5] AOA: EALF hesabi, tayf sinirlari, spec'ten bolunebilir tur / zenginlik / H/X / bicim.
  [VV6] Kume: kayitli kriter olcumlerinden VVOzeti (n, seriler, aralik, aoa_kategorik).
  [VV7] Profil B uctan uca: denetle(..., vv=kume.ozet(...)) ile LEU ornegi K6, K8-K14.
"""

import math

from testler.ortak_test import kontrol

# NUREG/CR-6698 Tablo 3.1 (satir 17'deki "-133.4" metin cikarim hatasidir: 133.4).
HX = [421.8] * 3 + [195.2] * 2 + [293.9] * 2 + [406.3, 495.9] + [613.6] * 2 + [971.7] * 2 \
    + [133.4] * 8 + [276.9] * 4
K = [0.9848, 0.9869, 0.9864, 0.9990, 0.9961, 1.0004, 0.9963, 0.9964, 0.9969, 0.9927, 0.9921,
     0.9881, 0.9856, 1.0039, 1.0114, 1.0108, 1.0071, 1.0064, 1.0113, 1.0128, 1.0067, 1.0054,
     1.0053, 1.0071, 1.0112]
SC = [0.0014, 0.0015, 0.0013, 0.0015, 0.0015, 0.0018, 0.0014, 0.0015, 0.0018, 0.0013, 0.0016,
      0.0013, 0.0015, 0.0016, 0.0018, 0.0017, 0.0018, 0.0022, 0.0018, 0.0021, 0.0018, 0.0018,
      0.0016, 0.0020, 0.0019]
SE = 0.0049


def _vakalar(k=K, sc=SC, ke=1.0, se=SE, hx=HX):
    from cekirdek.vv.istatistik import Vaka
    return [Vaka("v%d" % i, k[i], sc[i], ke, se, {"h_x": hx[i]}, "seri%d" % (i % 7))
            for i in range(len(k))]


def _yakin(a, b, tol):
    return a is not None and abs(a - b) <= tol


def test_nureg_ornegi_agirlikli():
    print("\n[VV1a] NUREG/CR-6698 §3 ornegi: agirlikli istatistik ve tolerans siniri")
    from cekirdek.vv import istatistik as ist
    k, s = ist.normallestir(_vakalar())
    a = ist.agirlikli_istatistik(k, s)
    kontrol("k̄ = 0.99983", _yakin(a["k_ort"], 0.999834, 5e-6), "-> %.6f" % a["k_ort"])
    kontrol("s² = 8.47993e-5", _yakin(a["s2"], 8.47993e-5, 1e-9), "-> %.5e" % a["s2"])
    kontrol("σ̄² = 2.67991e-5", _yakin(a["sigma2_ort"], 2.67991e-5, 1e-9))
    kontrol("S_p = 1.0564e-2", _yakin(a["S_p"], 1.0564e-2, 1e-6), "-> %.6f" % a["S_p"])
    u = ist.tolerans_carpani(25)
    kontrol("U(25) = 2.292", _yakin(u, 2.292, 1e-3), "-> %.4f" % u)
    kl = ist.tolerans_siniri(a["k_ort"], a["S_p"], 25)
    kontrol("K_L = 0.97562", _yakin(kl, 0.97562, 2e-5), "-> %.5f" % kl)
    kontrol("USL (ΔSM 0.02, ΔAOA 0.03) = 0.92562",
            _yakin(ist.usl(kl, 0.02, 0.03), 0.92562, 2e-5))


def test_nureg_ornegi_egilim_bant():
    print("\n[VV1b] NUREG/CR-6698 §3 ornegi: egilim (H/X) ve tolerans bandi")
    from cekirdek.vv import istatistik as ist
    k, s = ist.normallestir(_vakalar())
    e = ist.egilim(HX, k, s)
    kontrol("a = 1.00967", _yakin(e["a"], 1.00967, 1e-5), "-> %.5f" % e["a"])
    kontrol("b = -2.863e-5", _yakin(e["b"], -2.8629e-5, 1e-8), "-> %.4e" % e["b"])
    kontrol("x̄ = 343.58", _yakin(e["x_ort"], 343.576, 1e-2))
    kontrol("s_fit² = 3.782e-5", _yakin(e["s_fit2"], 3.782e-5, 1e-8))
    kontrol("S_p (bant) = 0.0080386", _yakin(e["S_p"], 0.0080386, 1e-6))
    kontrol("egilim anlamli (t > t_0.975,23)", e["anlamli"], "-> t = %.2f" % e["t"])
    for x, kl_bek in ((421.8, 0.9746), (971.7, 0.9515), (133.4, 0.9758)):
        kl = ist.tolerans_bandi(e, x, 25)
        kontrol("K_L(%g) = %.4f" % (x, kl_bek), _yakin(kl, kl_bek, 1e-4), "-> %.5f" % kl)
        kontrol("USL(%g) = %.4f" % (x, kl_bek - 0.02),
                _yakin(ist.usl(kl, 0.02, 0.0), kl_bek - 0.02, 1e-4))


def test_nureg_ornegi_parametrik_olmayan_normallik():
    print("\n[VV1c] NUREG/CR-6698 §3 ornegi: parametrik olmayan β ve Shapiro-Wilk")
    from cekirdek.vv import istatistik as ist
    k, s = ist.normallestir(_vakalar())
    p = ist.parametrik_olmayan(k, s, 0.010564)
    kontrol("β(n=25) = %72.26", _yakin(p["guven"], 0.7226, 1e-4), "-> %.4f" % p["guven"])
    kontrol("NPM(β = %72) = 0.02", p["npm"] == 0.02, "-> %s" % p["npm"])
    kontrol("K_L = 0.9848 - 0.0051 - 0.02 = 0.9597", _yakin(p["K_L"], 0.9597, 1e-4),
            "-> %.5f" % p["K_L"])
    n = ist.normallik(k)
    kontrol("Shapiro-Wilk W = 0.9201 (scipy; belge 0.9182)", _yakin(n["W"], 0.9201, 1e-4),
            "-> %.4f" % n["W"])
    kontrol("sinirda normal (p > 0.05) ve 'sinirda' notu", n["normal"] and n["sinirda"],
            "-> %s" % n)


def test_tolerans_carpani_tablo():
    print("\n[VV2] U(n) Tablo 2.1 ile ortusur")
    from cekirdek.vv import istatistik as ist
    tablo = {10: 2.911, 15: 2.566, 20: 2.396, 25: 2.292, 30: 2.220, 40: 2.126, 50: 2.065}
    for n, u in sorted(tablo.items()):
        kontrol("U(%d) = %.3f" % (n, u), _yakin(ist.tolerans_carpani(n), u, 1.5e-3),
                "-> %.4f" % ist.tolerans_carpani(n))
    kontrol("n = 80 -> U(50) (muhafazakar)",
            ist.tolerans_carpani(80) == ist.tolerans_carpani(50))


def test_kurallar():
    print("\n[VV3] Pozitif yanlilik, normallestirme, ΔSM, NPM")
    from cekirdek.vv import istatistik as ist
    b, bk = ist.yanlilik(1.004)
    kontrol("bias > 0 kredilendirilmez", _yakin(b, 0.004, 1e-12) and bk == 0.0)
    kontrol("bias < 0 aynen", _yakin(ist.yanlilik(0.995)[1], -0.005, 1e-12))
    v = _vakalar(k=[1.0014] * 3, sc=[0.0003] * 3, ke=1.0007, se=0.0012, hx=[0.0] * 3)
    k, s = ist.normallestir(v)
    kontrol("k_norm = k / k_exp", _yakin(k[0], 1.0014 / 1.0007, 1e-12))
    kontrol("σ = √(σc² + σe²)", _yakin(s[0], math.hypot(0.0003, 0.0012), 1e-12))
    try:
        ist.usl(0.97, 0.01, 0.0)
        kontrol("ΔSM = 0.01 reddedilir", False)
    except ValueError:
        kontrol("ΔSM = 0.01 reddedilir", True)
    for beta, npm in ((0.95, 0.0), (0.85, 0.01), (0.75, 0.02), (0.65, 0.03), (0.55, 0.04),
                      (0.45, 0.05), (0.40, None), (0.2, None)):
        kontrol("NPM(β = %.2f) = %s" % (beta, npm), ist.npm(beta) == npm)
    p = ist.parametrik_olmayan([0.99] * 9, [0.002] * 9, 0.003)
    kontrol("n = 9: β ≤ %40 -> K_L yok", p["K_L"] is None and p["guven"] <= 0.40,
            "-> %s" % p)
    p = ist.parametrik_olmayan([1.002, 1.004, 1.003], [0.002] * 3, 0.003)
    kontrol("k_(1) > 1 -> eş. 34 dali (1 - S_p - NPM) ama β düşük -> yok", p["K_L"] is None)
    p = ist.parametrik_olmayan([1.002] * 30, [0.002] * 30, 0.003)
    kontrol("k_(1) > 1, n = 30 (β = %78.5): K_L = 1 - S_p - 0.02", _yakin(p["K_L"], 1 - 0.003 - 0.02, 1e-12),
            "-> %s" % p)
    kontrol("kabul k + 2σ < USL (kati)", ist.kabul(0.90, 0.005, 0.91) is False
            and ist.kabul(0.899, 0.005, 0.91) is True)


def test_yontem_secimi():
    print("\n[VV4] Yontem secimi ve USL hesaplanamadi durumlari")
    from cekirdek.vv import istatistik as ist
    s = ist.degerlendir(_vakalar(), delta_sm=0.02, egilim_parametreleri=("h_x",))
    kontrol("NUREG verisi: anlamli H/X egilimi -> tolerans_bandi", s["yontem"] == "tolerans_bandi",
            "-> %s" % s["yontem"])
    kontrol("bant USL veri araligindaki en kucuk deger (x = 971.7 -> 0.9315)",
            _yakin(s["usl"], 0.9315, 1e-4), "-> %s" % s["usl"])
    s2 = ist.degerlendir(_vakalar(), delta_sm=0.02, egilim_parametreleri=("h_x",),
                         uygulama={"h_x": 421.8})
    kontrol("uygulama H/X = 421.8 -> USL 0.9546", _yakin(s2["usl"], 0.9546, 1e-4),
            "-> %s" % s2["usl"])
    duz = [1.0 + 0.001 * ((i * 7) % 11 - 5) / 5.0 for i in range(25)]
    s3 = ist.degerlendir(_vakalar(k=duz), delta_sm=0.05, egilim_parametreleri=("h_x",))
    kontrol("egilimsiz normal veri -> tolerans_siniri", s3["yontem"] == "tolerans_siniri",
            "-> %s %s" % (s3["yontem"], s3["normallik"]))
    kontrol("bias_kullanilan <= 0", s3["bias_kullanilan"] <= 0)
    carpik = [0.999] * 22 + [0.960, 0.955, 0.950]
    s4 = ist.degerlendir(_vakalar(k=carpik), delta_sm=0.05, egilim_parametreleri=())
    kontrol("normal olmayan veri -> parametrik_olmayan", s4["yontem"] == "parametrik_olmayan",
            "-> %s" % s4["normallik"])
    kontrol("parametrik olmayan: guven bildirildi", _yakin(s4["guven"], 1 - 0.95 ** 25, 1e-9))
    s5 = ist.degerlendir(_vakalar(k=K[:2], sc=SC[:2], hx=HX[:2]), delta_sm=0.05)
    kontrol("n = 2 -> USL hesaplanamadi", s5["usl"] is None and s5["usl_neden"], "-> %s" % s5)
    s6 = ist.degerlendir(_vakalar(k=carpik[:9], sc=SC[:9], hx=HX[:9]), delta_sm=0.05,
                         egilim_parametreleri=())
    if s6["yontem"] == "parametrik_olmayan":
        kontrol("n = 9 parametrik olmayan -> USL hesaplanamadi", s6["usl"] is None)


def test_aoa_ealf_tayf():
    print("\n[VV5a] EALF ve tayf sinifi")
    from cekirdek.vv import aoa
    kenar = [1e-3, 1e-1, 10.0]
    kontrol("EALF tek grupta geometrik orta", _yakin(aoa.ealf_hesapla(kenar, [1.0, 0.0]),
                                                     1e-2, 1e-12))
    kontrol("EALF iki esit grup", _yakin(aoa.ealf_hesapla(kenar, [1.0, 1.0]), 0.1, 1e-12))
    kontrol("fisyon yoksa None", aoa.ealf_hesapla(kenar, [0.0, 0.0]) is None)
    kontrol("tayf sinirlari (1 eV, 100 keV)",
            [aoa.tayf_sinifi(e) for e in (0.5, 1.0, 5e4, 1e5, 1e6)]
            == ["termal", "ara", "ara", "hizli", "hizli"])


def test_aoa_spec_parametreleri():
    print("\n[VV5b] AOA parametreleri spec'ten (bolunebilir, zenginlik, H/X, bicim)")
    import os
    from cekirdek import sema
    from cekirdek.vv import aoa
    from testler.ortak_test import ORNEK
    beklenen = {
        "kriter_jezebel.json": ("Pu", "metal", 0.0),
        "godiva_kriter.json": ("U-235", "metal", 0.0),
        "kriter_lct008.json": ("U-235", "oksit", None),
        os.path.join("vv", "kriter_hst032.json"): ("U-235", "cozelti", "pozitif"),
        os.path.join("vv", "kriter_umf006.json"): ("U-233", "metal", 0.0),
        os.path.join("vv", "kriter_mmf001.json"): ("karisik", "metal", 0.0),
    }
    for ad, (tur, bicim, hx) in sorted(beklenen.items()):
        p = aoa.parametreler(sema.yukle(os.path.join(ORNEK, ad)))
        kontrol("%s: bolunebilir %s" % (ad, tur), p.get("bolunebilir") == tur, "-> %s" % p)
        kontrol("%s: bicim %s" % (ad, bicim), p.get("fiziksel_bicim") == bicim)
        if hx is None:
            kontrol("%s: heterojen -> H/X verilmez" % ad, "h_x" not in p)
        elif hx == "pozitif":
            kontrol("%s: H/X > 0" % ad, p.get("h_x", 0) > 0)
        else:
            kontrol("%s: H/X = 0" % ad, p.get("h_x") == 0.0)
    p = aoa.parametreler(sema.yukle(os.path.join(ORNEK, "kriter_lct008.json")))
    kontrol("LCT-008 zenginlik %2.46", _yakin(p.get("zenginlik"), 2.46, 0.02), "-> %s" % p)
    p = aoa.parametreler(sema.yukle(os.path.join(ORNEK, "vv", "kriter_umf006.json")))
    kontrol("Flattop-23: dogal U yansitici yakit sayilmaz (zenginlik > %95)",
            p.get("zenginlik", 0) > 95)


HIZLI = [test_nureg_ornegi_agirlikli, test_nureg_ornegi_egilim_bant,
         test_nureg_ornegi_parametrik_olmayan_normallik, test_tolerans_carpani_tablo,
         test_kurallar, test_yontem_secimi, test_aoa_ealf_tayf, test_aoa_spec_parametreleri]
YAVAS = []
