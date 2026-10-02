# -*- coding: utf-8 -*-
"""
 test_k6_sogutucu.py  --  v3 K6: su / D2O / Na yogunlugu (cekirdek/malzeme_sogutucu.py)

 Beklenen degerler RESMI DOGRULAMA TABLOLARIDIR:
   IAPWS R7-97(2012) "Revised Release on the IAPWS Industrial Formulation 1997
   for the Thermodynamic Properties of Water and Steam":
     Tablo 5  (Bolge 1): v(300 K, 3 MPa)  = 0.100215168e-2 m3/kg
                         v(300 K, 80 MPa) = 0.971180894e-3 m3/kg
                         v(500 K, 3 MPa)  = 0.120241800e-2 m3/kg
     Tablo 35 (Bolge 4): p_s(300 K) = 0.353658941e-2 MPa
                         p_s(500 K) = 0.263889776e1  MPa
                         p_s(600 K) = 0.123443146e2  MPa
   D2O: NIST Chemistry WebBook SRD 69 (IAPWS R16-17 D2O formulasyonu, Herrig vd.
   J. Phys. Chem. Ref. Data 47 (2018) 043102) izobar degerleri -- tablo dugumleri.
   Na : Fink & Leibowitz, ANL/RE-95/2 (1995), doymus sivi yogunlugu
        rho = 219 + 275.32 (1 - T/2503.7) + 511.58 (1 - T/2503.7)^0.5  [kg/m3]
        el hesabi: 371 K -> 925.68083 ; 673 K -> 857.76599 kg/m3
"""

import pytest

from testler.ortak_test import KOK  # noqa: F401


def test_if97_bolge1_resmi_dogrulama():
    from cekirdek import malzeme_sogutucu as ms
    for t, p, v in ((300.0, 3.0, 0.100215168e-2), (300.0, 80.0, 0.971180894e-3),
                    (500.0, 3.0, 0.120241800e-2)):
        # rho [g/cm3] = 1/v [m3/kg] / 1000
        assert ms.su_yogunlugu(t, p) == pytest.approx(1.0e-3 / v, rel=5e-9), (t, p)   # tablo 9 basamak


def test_if97_bolge4_doyma_basinci():
    from cekirdek import malzeme_sogutucu as ms
    for t, ps in ((300.0, 0.353658941e-2), (500.0, 0.263889776e1), (600.0, 0.123443146e2)):
        # tablo 9 anlamli basamak: goreli yuvarlama <= 5e-9
        assert ms.doyma_basinci(t) == pytest.approx(ps, rel=5e-9), t


def test_su_iapws95_ile_tutarli():
    """IF97, bilimsel IAPWS-95'ten (NIST WebBook) PWR kosulunda < 1e-4 sapar."""
    from cekirdek import malzeme_sogutucu as ms
    # NIST WebBook SRD 69 (IAPWS-95) izobarlari, g/ml. 275-620 K x 0.1-100 MPa
    # izgarasinin (130 nokta) tamami gelistirmede < 2.8e-5 sapti; burada ornekler.
    for t, p, rho in ((580.0, 15.5, 0.711869), (290.0, 0.1, 0.998803), (440.0, 50.0, 0.928199),
                      (275.0, 100.0, 1.04486), (305.0, 10.0, 0.999426),
                      (372.756, 0.1, 0.958632)):      # son nokta: doymus sivi (sinir)
        assert ms.su_yogunlugu(t, p) == pytest.approx(rho, rel=1e-4), (t, p)


def test_su_sinir_disinda_acik_hata():
    from cekirdek import malzeme_sogutucu as ms
    with pytest.raises(ValueError, match="buhar"):
        ms.su_yogunlugu(500.0, 1.0)            # p < p_s(500 K) = 2.64 MPa: buhar
    for t, p in ((650.0, 20.0), (270.0, 1.0), (300.0, 120.0), (300.0, 0.0)):
        with pytest.raises(ValueError):
            ms.su_yogunlugu(t, p)


def test_agir_su_tablo_dugum_ve_interpolasyon():
    from cekirdek import malzeme_sogutucu as ms
    # dugum: NIST 10 MPa, 560 K -> 0.819767 g/ml
    assert ms.agir_su_yogunlugu(560.0, 10.0) == pytest.approx(0.819767, rel=1e-12)
    # T'de dogrusal: 10 MPa, 565 K = (0.819767 + 0.795962)/2
    assert ms.agir_su_yogunlugu(565.0, 10.0) == pytest.approx((0.819767 + 0.795962) / 2, rel=1e-12)
    # p'de dogrusal: 11 MPa, 560 K = (0.819767 + 0.823713)/2
    assert ms.agir_su_yogunlugu(560.0, 11.0) == pytest.approx((0.819767 + 0.823713) / 2, rel=1e-12)
    # moderator kosulu: 0.1 MPa, 340 K dugumu = 1.08667
    assert ms.agir_su_yogunlugu(340.0, 0.1) == pytest.approx(1.08667, rel=1e-12)


def test_agir_su_tablo_disinda_acik_hata():
    from cekirdek import malzeme_sogutucu as ms
    for t, p in ((590.0, 10.0),     # 10 MPa izobari 583.172 K'de doyar
                 (275.0, 1.0), (500.0, 25.0), (400.0, 0.05)):
        with pytest.raises(ValueError):
            ms.agir_su_yogunlugu(t, p)


def test_sodyum_fink_leibowitz():
    from cekirdek import malzeme_sogutucu as ms
    assert ms.sodyum_yogunlugu(371.0) == pytest.approx(0.9256808317560121, rel=1e-12)
    assert ms.sodyum_yogunlugu(673.0) == pytest.approx(0.8577659873807998, rel=1e-12)
    for t in (300.0, 2600.0):
        with pytest.raises(ValueError):
            ms.sodyum_yogunlugu(t)


def test_agir_su_saflik_karisimi():
    """D2O/H2O ideal karisim (molar hacim toplanabilir): saflik 1 -> saf D2O."""
    from cekirdek import malzeme_sogutucu as ms
    saf = ms.agir_su_yogunlugu(340.0, 0.1)
    assert ms.agir_su_karisim_yogunlugu(340.0, 0.1, 1.0) == pytest.approx(saf, rel=1e-12)
    h2o = ms.su_yogunlugu(340.0, 0.1)
    # x = 0.5 mol: rho = (0.5 M_D + 0.5 M_H)/(0.5 M_D/rho_D + 0.5 M_H/rho_H)
    m_d, m_h = ms.molar_kutle_d2o(), ms.molar_kutle_h2o()
    beklenen = (0.5 * m_d + 0.5 * m_h) / (0.5 * m_d / saf + 0.5 * m_h / h2o)
    assert ms.agir_su_karisim_yogunlugu(340.0, 0.1, 0.5) == pytest.approx(beklenen, rel=1e-12)
    # M(D2O) el hesabi: 2 x 2.014101777844 + 15.999304509 = 20.027508065
    assert m_d == pytest.approx(20.027508064926562, rel=1e-12)


def test_agir_su_dugum_basincinda_tek_izobar():
    """20 MPa tam dugum: 614-637 K yalniz 20 MPa izobarinda var (15 MPa 614 K'de doyar)."""
    from cekirdek import malzeme_sogutucu as ms
    assert ms.agir_su_yogunlugu(630.0, 20.0) == pytest.approx(0.613026, rel=1e-12)
    assert ms.agir_su_yogunlugu(613.982, 15.0) == pytest.approx(0.663490, rel=1e-12)
    # ara basincta ust T siniri iki komsu izobarin kucuk olani; ileti ikisini de soyler
    with pytest.raises(ValueError, match="15") as hata:
        ms.agir_su_yogunlugu(620.0, 17.0)
    assert "17" in str(hata.value) and "613.98" in str(hata.value)
    assert ms.ust_sicaklik_d2o(17.0) == pytest.approx(613.982)
    assert ms.ust_sicaklik_d2o(20.0) == pytest.approx(637.284)


def test_agir_su_safligi_h2o_payi_buhar_degil():
    """x >= 0.99: H2O molar hacmi D2O'nunkiyle esit alinir (Kell 1977); IF97 cagrilmaz."""
    from cekirdek import malzeme_sogutucu as ms
    for t, p in ((373.5, 0.1), (453.3, 1.0), (630.0, 20.0)):    # H2O burada sivi degil/IF97 disi
        rho = ms.agir_su_karisim_yogunlugu(t, p, 0.9975)
        rho_d = ms.agir_su_yogunlugu(t, p)
        m_d, m_h = ms.molar_kutle_d2o(), ms.molar_kutle_h2o()
        # rho = (x M_D + (1-x) M_H) / V_D ,  V_D = M_D / rho_D
        assert rho == pytest.approx((0.9975 * m_d + 0.0025 * m_h) * rho_d / m_d, rel=1e-12)
    with pytest.raises(ValueError, match="H₂O"):
        ms.agir_su_karisim_yogunlugu(373.5, 0.1, 0.95)            # dusuk saflik: acik ileti


def test_sodyum_anl_tablosu():
    """ANL/RE-95/2 Tablo 1.3-1 (raporun kendi tablosu, tam sayiya yuvarli, kg/m3)."""
    from cekirdek import malzeme_sogutucu as ms
    tablo = {400: 919, 500: 897, 600: 874, 700: 852, 800: 828, 900: 805, 1000: 781,
             1100: 756, 1200: 732, 1300: 706, 1400: 680}
    for t, rho in tablo.items():
        assert ms.sodyum_yogunlugu(float(t)) * 1000.0 == pytest.approx(rho, abs=0.5), t


HIZLI = [test_sodyum_anl_tablosu, test_agir_su_dugum_basincinda_tek_izobar, test_agir_su_safligi_h2o_payi_buhar_degil,
         test_if97_bolge1_resmi_dogrulama, test_if97_bolge4_doyma_basinci,
         test_su_iapws95_ile_tutarli, test_su_sinir_disinda_acik_hata,
         test_agir_su_tablo_dugum_ve_interpolasyon, test_agir_su_tablo_disinda_acik_hata,
         test_sodyum_fink_leibowitz, test_agir_su_saflik_karisimi]
