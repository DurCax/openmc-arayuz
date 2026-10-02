# -*- coding: utf-8 -*-
"""
================================================================================
 malzeme_sogutucu.py  --  Sogutucu/moderator yogunlugu: H2O, D2O, Na (T, p)
================================================================================

 Bagimlilik eklenmeden yazildi; GECERLILIK ARALIGI DISINDA ValueError verir
 (sessiz uc deger yok).

 H2O  IAPWS-IF97, yalniz BOLGE 1 (sikistirilmis sivi) ve BOLGE 4 doyma basinci.
      Kaynak: IAPWS R7-97(2012), "Revised Release on the IAPWS Industrial
      Formulation 1997 for the Thermodynamic Properties of Water and Steam",
      Denklem 7 (Bolge 1, Tablo 2 katsayilari) ve Denklem 30 (Bolge 4,
      Tablo 34 katsayilari). Dogrulama: Tablo 5 ve Tablo 35 (testler).
      Gecerlilik: 273.15 K <= T <= 623.15 K, p_s(T) <= p <= 100 MPa.
      IAPWS belgeleri serbestce kullanilabilir (www.iapws.org).

 D2O  Tablo + iki dogrusal interpolasyon (T'de izobar boyunca, sonra p'de).
      Degerler: NIST Chemistry WebBook, SRD 69 (Lemmon, McLinden, Friend),
      IAPWS R16-17 D2O formulasyonu (Herrig vd., J. Phys. Chem. Ref. Data 47
      (2018) 043102) ile hesaplanmis izobarlar; 02.10.2026'da alindi. Her
      izobarin son noktasi doymus sividir. Izobarda sivi olmayan sicaklik ya da
      tablo disi basinc ValueError'dur.

 Na   Fink & Leibowitz, "Thermodynamic and Transport Properties of Sodium
      Liquid and Vapor", ANL/RE-95/2 (1995), doymus sivi yogunlugu:
        rho = rho_c + f (1 - T/T_c) + g (1 - T/T_c)^h        [kg/m3]
      rho_c = 219, f = 275.32, g = 511.58, h = 0.5, T_c = 2503.7 K;
      371 K <= T <= 2503.7 K.
================================================================================
"""

import bisect
import math

from cekirdek.ceviri import _

# ----------------------------------------------------------------------------
# IAPWS-IF97 sabitleri
# ----------------------------------------------------------------------------
_R = 0.461526              # kJ/(kg K) -- IF97 ozgul gaz sabiti (Denklem 1)
_P_YILDIZ_1 = 16.53        # MPa       -- Bolge 1 indirgeme basinci
_T_YILDIZ_1 = 1386.0       # K         -- Bolge 1 indirgeme sicakligi
_T_EN_AZ = 273.15          # K
_T_BOLGE1_EN_COK = 623.15  # K
_P_EN_COK = 100.0          # MPa
_T_KRITIK = 647.096        # K (Bolge 4 ust siniri)

# Tablo 2: (I_i, J_i, n_i), i = 1..34
_BOLGE1 = (
    (0, -2, 0.14632971213167), (0, -1, -0.84548187169114), (0, 0, -0.37563603672040e1),
    (0, 1, 0.33855169168385e1), (0, 2, -0.95791963387872), (0, 3, 0.15772038513228),
    (0, 4, -0.16616417199501e-1), (0, 5, 0.81214629983568e-3), (1, -9, 0.28319080123804e-3),
    (1, -7, -0.60706301565874e-3), (1, -1, -0.18990068218419e-1), (1, 0, -0.32529748770505e-1),
    (1, 1, -0.21841717175414e-1), (1, 3, -0.52838357969930e-4), (2, -3, -0.47184321073267e-3),
    (2, 0, -0.30001780793026e-3), (2, 1, 0.47661393906987e-4), (2, 3, -0.44141845330846e-5),
    (2, 17, -0.72694996297594e-15), (3, -4, -0.31679644845054e-4), (3, 0, -0.28270797985312e-5),
    (3, 6, -0.85205128120103e-9), (4, -5, -0.22425281908000e-5), (4, -2, -0.65171222895601e-6),
    (4, 10, -0.14341729937924e-12), (5, -8, -0.40516996860117e-6), (8, -11, -0.12734301741641e-8),
    (8, -6, -0.17424871230634e-9), (21, -29, -0.68762131295531e-18),
    (23, -31, 0.14478307828521e-19), (29, -38, 0.26335781662795e-22),
    (30, -39, -0.11947622640071e-22), (31, -40, 0.18228094581404e-23),
    (32, -41, -0.93537087292458e-25),
)

# Tablo 34: n_1 .. n_10
_BOLGE4 = (0.11670521452767e4, -0.72421316703206e6, -0.17073846940092e2,
           0.12020824702470e5, -0.32325550322333e7, 0.14915108613530e2,
           -0.48232657361591e4, 0.40511340542057e6, -0.23855557567849,
           0.65017534844798e3)

_KG_M3_G_CM3 = 1.0e-3
# Doyma sinirinda goreli basinc toleransi: IF97'nin IAPWS-95'ten sapmasi
# mertebesi (R7-97 Bolum 9; olculen en buyuk yogunluk sapmasi 2.7e-5).
_DOYMA_TOLERANSI = 1.0e-4


def doyma_basinci(sicaklik: float) -> float:
    """IF97 Bolge 4, Denklem 30: p_s(T) [MPa]; 273.15 K <= T <= 647.096 K."""
    if not _T_EN_AZ <= sicaklik <= _T_KRITIK:
        raise ValueError(_("doyma basıncı %.2f–%.3f K aralığında tanımlı: %.2f K")
                         % (_T_EN_AZ, _T_KRITIK, sicaklik))
    n = _BOLGE4
    v = sicaklik + n[8] / (sicaklik - n[9])          # T* = 1 K
    a = v * v + n[0] * v + n[1]
    b = n[2] * v * v + n[3] * v + n[4]
    c = n[5] * v * v + n[6] * v + n[7]
    return (2.0 * c / (-b + math.sqrt(b * b - 4.0 * a * c))) ** 4    # p* = 1 MPa


def _bolge1_gamma_pi(pi, tau):
    """dGamma/dpi (Tablo 4): -sum n_i I_i (7.1 - pi)^(I_i - 1) (tau - 1.222)^J_i."""
    return sum(-n * i * (7.1 - pi) ** (i - 1) * (tau - 1.222) ** j
               for i, j, n in _BOLGE1 if i)


def su_yogunlugu(sicaklik: float, basinc: float) -> float:
    """
    Sikistirilmis sivi su yogunlugu [g/cm3], IF97 Bolge 1:
      v = pi gamma_pi R T / p ;  pi = p/16.53 MPa, tau = 1386 K/T
    sicaklik [K], basinc [MPa]. Buhar bolgesi ya da aralik disi: ValueError.
    """
    if not _T_EN_AZ <= sicaklik <= _T_BOLGE1_EN_COK:
        raise ValueError(_("su yoğunluğu (IAPWS-IF97 Bölge 1) %.2f–%.2f K aralığında: %.2f K")
                         % (_T_EN_AZ, _T_BOLGE1_EN_COK, sicaklik))
    if not 0.0 < basinc <= _P_EN_COK:
        raise ValueError(_("basınç 0–%.0f MPa aralığında olmalı: %r MPa") % (_P_EN_COK, basinc))
    ps = doyma_basinci(sicaklik)
    if basinc < ps * (1.0 - _DOYMA_TOLERANSI):
        raise ValueError(_("%.2f K'de %.4g MPa buhar bölgesidir (doyma basıncı %.4g MPa); "
                           "sıvı için basıncı artırın") % (sicaklik, basinc, ps))
    pi = basinc / _P_YILDIZ_1
    tau = _T_YILDIZ_1 / sicaklik
    v = pi * _bolge1_gamma_pi(pi, tau) * _R * sicaklik / (basinc * 1.0e3)   # m3/kg
    return _KG_M3_G_CM3 / v


# ----------------------------------------------------------------------------
# D2O tablosu: {basinc [MPa]: ((T [K], rho [g/cm3]), ...)} -- NIST SRD 69 / IAPWS R16-17
# ----------------------------------------------------------------------------
_D2O = {
    0.1: ((280, 1.10572), (290, 1.10569), (300, 1.10406), (310, 1.10114), (320, 1.09717),
          (330, 1.09231), (340, 1.08667), (350, 1.08034), (360, 1.07339), (370, 1.06585),
          (374.185, 1.06254)),
    1.0: ((280, 1.10623), (290, 1.10617), (300, 1.10452), (310, 1.10159), (320, 1.09762),
          (330, 1.09275), (340, 1.08712), (350, 1.08079), (360, 1.07385), (370, 1.06632),
          (380, 1.05825), (390, 1.04966), (400, 1.04055), (410, 1.03094), (420, 1.02082),
          (430, 1.01019), (440, 0.999017), (450, 0.987289), (453.494, 0.983054)),
    2.0: ((280, 1.10679), (290, 1.10670), (300, 1.10503), (310, 1.10209), (320, 1.09811),
          (330, 1.09324), (340, 1.08761), (350, 1.08129), (360, 1.07436), (370, 1.06684),
          (380, 1.05879), (390, 1.05021), (400, 1.04113), (410, 1.03154), (420, 1.02145),
          (430, 1.01084), (440, 0.999710), (450, 0.988025), (460, 0.975755), (470, 0.962862),
          (480, 0.949291), (485.622, 0.941340)),
    5.0: ((280, 1.10846), (290, 1.10828), (300, 1.10655), (310, 1.10358), (320, 1.09958),
          (330, 1.09471), (340, 1.08908), (350, 1.08278), (360, 1.07587), (370, 1.06839),
          (380, 1.06038), (390, 1.05186), (400, 1.04283), (410, 1.03332), (420, 1.02331),
          (430, 1.01279), (440, 1.00177), (450, 0.990207), (460, 0.978081), (470, 0.965353),
          (480, 0.951975), (490, 0.937888), (500, 0.923017), (510, 0.907265), (520, 0.890510),
          (530, 0.872589), (536.615, 0.859990)),
    10.0: ((280, 1.11123), (290, 1.11089), (300, 1.10906), (310, 1.10603), (320, 1.10200),
           (330, 1.09712), (340, 1.09151), (350, 1.08524), (360, 1.07837), (370, 1.07095),
           (380, 1.06300), (390, 1.05456), (400, 1.04564), (410, 1.03623), (420, 1.02635),
           (430, 1.01599), (440, 1.00514), (450, 0.993771), (460, 0.981870), (470, 0.969401),
           (480, 0.956325), (490, 0.942590), (500, 0.928133), (510, 0.912876), (520, 0.896717),
           (530, 0.879530), (540, 0.861144), (550, 0.841331), (560, 0.819767), (570, 0.795962),
           (580, 0.769116), (583.172, 0.759758)),
    12.0: ((280, 1.11233), (290, 1.11193), (300, 1.11006), (310, 1.10701), (320, 1.10296),
           (330, 1.09808), (340, 1.09247), (350, 1.08621), (360, 1.07936), (370, 1.07196),
           (380, 1.06404), (390, 1.05563), (400, 1.04674), (410, 1.03738), (420, 1.02756),
           (430, 1.01725), (440, 1.00646), (450, 0.995172), (460, 0.983357), (470, 0.970987),
           (480, 0.958024), (490, 0.944422), (500, 0.930120), (510, 0.915046), (520, 0.899107),
           (530, 0.882185), (540, 0.864128), (550, 0.844732), (560, 0.823713), (570, 0.800655),
           (580, 0.774901), (590, 0.745304), (596.702, 0.722241)),
    15.0: ((280, 1.11397), (290, 1.11348), (300, 1.11155), (310, 1.10846), (320, 1.10440),
           (330, 1.09952), (340, 1.09391), (350, 1.08766), (360, 1.08083), (370, 1.07347),
           (380, 1.06559), (390, 1.05723), (400, 1.04839), (410, 1.03910), (420, 1.02934),
           (430, 1.01912), (440, 1.00843), (450, 0.997248), (460, 0.985557), (470, 0.973330),
           (480, 0.960532), (490, 0.947120), (500, 0.933041), (510, 0.918228), (520, 0.902599),
           (530, 0.886052), (540, 0.868453), (550, 0.849630), (560, 0.829348), (570, 0.807273),
           (580, 0.782907), (590, 0.755437), (600, 0.723370), (610, 0.683388),
           (613.982, 0.663490)),
    20.0: ((280, 1.11668), (290, 1.11604), (300, 1.11402), (310, 1.11087), (320, 1.10678),
           (330, 1.10188), (340, 1.09628), (350, 1.09006), (360, 1.08327), (370, 1.07595),
           (380, 1.06814), (390, 1.05985), (400, 1.05111), (410, 1.04191), (420, 1.03228),
           (430, 1.02219), (440, 1.01165), (450, 1.00064), (460, 0.989149), (470, 0.977148),
           (480, 0.964609), (490, 0.951495), (500, 0.937760), (510, 0.923350), (520, 0.908197),
           (530, 0.892215), (540, 0.875300), (550, 0.857316), (560, 0.838089), (570, 0.817381),
           (580, 0.794856), (590, 0.770015), (600, 0.742054), (610, 0.709536), (620, 0.669441),
           (630, 0.613026), (637.284, 0.532196)),
}
_D2O_BASINCLARI = tuple(sorted(_D2O))


def _dogrusal(x, x0, x1, y0, y1):
    return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def _izobar(basinc, sicaklik):
    noktalar = _D2O[basinc]
    ts = [t for t, _r in noktalar]
    if not ts[0] <= sicaklik <= ts[-1]:
        raise ValueError(_("D₂O tablosu %.4g MPa'da %.1f–%.1f K (sıvı) aralığında: %.2f K")
                         % (basinc, ts[0], ts[-1], sicaklik))
    i = min(max(bisect.bisect_right(ts, sicaklik) - 1, 0), len(ts) - 2)
    (t0, r0), (t1, r1) = noktalar[i], noktalar[i + 1]
    return _dogrusal(sicaklik, t0, t1, r0, r1)


def _komsu_izobarlar(basinc):
    """Tam dugum basincinda (p,) ; arada (alt, ust)."""
    ps = _D2O_BASINCLARI
    if not ps[0] <= basinc <= ps[-1]:
        raise ValueError(_("D₂O tablosu %.1f–%.0f MPa aralığında: %r MPa") % (ps[0], ps[-1], basinc))
    if basinc in _D2O:
        return (basinc,)
    j = bisect.bisect_right(ps, basinc) - 1
    return ps[j], ps[j + 1]


def ust_sicaklik_d2o(basinc: float) -> float:
    """Bu basincta tablonun ust sicakligi [K]: komsu izobarlarin doyma
    noktalarinin KUCUGU (arada tablo dogrusal interpolasyondur)."""
    return min(_D2O[p][-1][0] for p in _komsu_izobarlar(basinc))


def agir_su_yogunlugu(sicaklik: float, basinc: float) -> float:
    """Saf sivi D2O yogunlugu [g/cm3], tablo interpolasyonu (T [K], p [MPa]).
    Tam dugum basincinda yalniz o izobar; arada iki komsu izobar arasinda
    dogrusal. Ust sicaklik ust_sicaklik_d2o(p)'dir (ara basincta kucuk olan
    izobarin doyma sicakligi; gercek doyma sicakligi biraz daha yuksektir)."""
    izobarlar = _komsu_izobarlar(basinc)
    if len(izobarlar) == 1:
        return _izobar(basinc, sicaklik)
    alt, ust = izobarlar
    t_ust = ust_sicaklik_d2o(basinc)
    if sicaklik > t_ust:
        raise ValueError(_("D₂O tablosu %.4g MPa'da (komşu izobarlar %g ve %g MPa) en çok %.2f K'e "
                           "kadar sıvı verir: %.2f K") % (basinc, alt, ust, t_ust, sicaklik))
    return _dogrusal(basinc, alt, ust, _izobar(alt, sicaklik), _izobar(ust, sicaklik))


def _ortalama(element):
    from cekirdek import malzeme_hesap as mh
    return mh.ortalama_kutle(mh.dogal_vektor(element))


def molar_kutle_h2o() -> float:
    """Dogal H2O molar kutlesi [g/mol] (openmc.data AME2020 + IUPAC 2013)."""
    return 2.0 * _ortalama("H") + _ortalama("O")


def molar_kutle_d2o() -> float:
    """D2O molar kutlesi [g/mol]: 2 M(H2) + M_dogal(O)."""
    from cekirdek import malzeme_hesap as mh
    return 2.0 * mh.kutle("H2") + _ortalama("O")


# Bu saflik ve ustunde H2O payinin molar hacmi D2O'nunkiyle esit alinir:
# 25 °C'de V_m(D2O)/V_m(H2O) = 18.134/18.069 = 1.0036 (Kell, J. Phys. Chem. Ref.
# Data 6 (1977) 1109); %1 H2O payinda yogunluk hatasi < 4e-5. Boylece H2O'nun
# sivi olmadigi (D2O'nun daha yuksek kaynama noktasi) ya da IF97 Bolge 1 disi
# (T > 623.15 K) kosullarda da karisim tanimlidir.
D2O_YUKSEK_SAFLIK = 0.99


def agir_su_karisim_yogunlugu(sicaklik: float, basinc: float, d2o_mol_kesri: float) -> float:
    """
    D2O-H2O sivi karisimi [g/cm3], IDEAL KARISIM (molar hacimler toplanir):
      rho = (x M_D + (1-x) M_H) / (x V_D + (1-x) V_H)
    V_D = M_D/rho_D (tablo). x >= D2O_YUKSEK_SAFLIK: V_H = V_D (Kell 1977);
    daha dusuk saflikta V_H = M_H/rho_H (IF97) ve H2O bu kosulda sivi degilse
    acik hata.
    """
    if not 0.0 <= d2o_mol_kesri <= 1.0:
        raise ValueError(_("D₂O mol kesri 0 ile 1 arasında olmalı: %r") % d2o_mol_kesri)
    x = d2o_mol_kesri
    rho_d = agir_su_yogunlugu(sicaklik, basinc)
    m_d, m_h = molar_kutle_d2o(), molar_kutle_h2o()
    v_d = m_d / rho_d
    if x >= D2O_YUKSEK_SAFLIK:
        return (x * m_d + (1.0 - x) * m_h) / v_d
    try:
        v_h = m_h / su_yogunlugu(sicaklik, basinc)
    except ValueError as e:
        raise ValueError(_("Saflık %%%.2f < %%%.0f: H₂O payının yoğunluğu IAPWS-IF97 ile "
                           "hesaplanır ve bu koşulda bulunamadı (%s)")
                         % (100.0 * x, 100.0 * D2O_YUKSEK_SAFLIK, e)) from e
    return (x * m_d + (1.0 - x) * m_h) / (x * v_d + (1.0 - x) * v_h)


# ----------------------------------------------------------------------------
# Sivi sodyum -- Fink & Leibowitz, ANL/RE-95/2 (1995)
# ----------------------------------------------------------------------------
_NA_RHO_C, _NA_F, _NA_G, _NA_H = 219.0, 275.32, 511.58, 0.5      # kg/m3
_NA_T_KRITIK = 2503.7     # K
_NA_T_ERIME = 371.0       # K (370.98 K)


def sodyum_yogunlugu(sicaklik: float) -> float:
    """Doymus sivi sodyum yogunlugu [g/cm3], 371 K <= T <= 2503.7 K."""
    if not _NA_T_ERIME <= sicaklik <= _NA_T_KRITIK:
        raise ValueError(_("sodyum yoğunluğu %.0f–%.1f K aralığında tanımlı: %.2f K")
                         % (_NA_T_ERIME, _NA_T_KRITIK, sicaklik))
    th = 1.0 - sicaklik / _NA_T_KRITIK
    return (_NA_RHO_C + _NA_F * th + _NA_G * th ** _NA_H) * _KG_M3_G_CM3
