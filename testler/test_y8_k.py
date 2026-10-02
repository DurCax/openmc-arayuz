# -*- coding: utf-8 -*-
"""
 test_y8_k.py  --  v3 Y8: grup sabitlerinden sonsuz ortam k (cekirdek/mgxs_k.py)

 HIZLI: saf numpy -- 1 grup k = nuSf/Sa, 2 grup yukari sacilmasiz el formulu,
        yukari sacilmali 2x2 ozdeger (determinant formulu), reaksiyon hizi
        orani k = sum(nuF)/sum(A), birinci derece belirsizlik, girdi
        dogrulama (negatif, boyut, chi toplami).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import math

from testler.ortak_test import kontrol

_TOL = 1e-12


def _yakin(a, b, tol=_TOL):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def _sabit(**ek):
    from cekirdek import mgxs_k as mk
    alanlar = dict(toplam=(0.52, 1.30), absorpsiyon=(0.010, 0.095),
                   nu_fisyon=(0.0070, 0.150), chi=(1.0, 0.0),
                   sacilma=((0.490, 0.020), (0.0, 1.205)))
    alanlar.update(ek)
    return mk.GrupSabitleri(**alanlar)


def test_tek_grup_k_nusf_bolu_sa():
    print("\n[Y8-K1] 1 grup: k = nuSf / (St - Ss) = nuSf / Sa")
    from cekirdek import mgxs_k as mk
    # Arrange
    s = mk.GrupSabitleri(toplam=(0.6,), absorpsiyon=(0.1,), nu_fisyon=(0.13,),
                         chi=(1.0,), sacilma=((0.5,),))
    # Act
    k = mk.k_ozdeger(s)
    # Assert
    kontrol("k = 1.3", _yakin(k, 1.3), "-> %r" % k)


def test_iki_grup_yukari_sacilmasiz_el_formulu():
    print("\n[Y8-K2] 2 grup, chi=(1,0), yukari sacilma yok: k = nuSf1/Sr1 + S12 nuSf2/(Sr1 Sa2)")
    from cekirdek import mgxs_k as mk
    # Arrange
    s = _sabit()
    sr1 = 0.52 - 0.490
    sa2 = 1.30 - 1.205
    beklenen = 0.0070 / sr1 + 0.020 * 0.150 / (sr1 * sa2)
    # Act
    k = mk.k_ozdeger(s)
    # Assert
    kontrol("el formulu", _yakin(k, beklenen, 1e-10), "-> %r / %r" % (k, beklenen))


def test_iki_grup_yukari_sacilmali_determinant():
    print("\n[Y8-K3] 2 grup yukari sacilmali: M phi = chi nuSf.phi / k, M = diag(St) - S^T")
    from cekirdek import mgxs_k as mk
    # Arrange
    s = _sabit(sacilma=((0.490, 0.020), (0.004, 1.201)))
    m11, m12 = 0.52 - 0.490, -0.004
    m21, m22 = -0.020, 1.30 - 1.201
    det = m11 * m22 - m12 * m21
    # chi=(1,0): phi = M^-1 e1 -> phi1 = m22/det, phi2 = -m21/det; k = nuSf.phi
    beklenen = 0.0070 * m22 / det + 0.150 * (-m21) / det
    # Act
    k = mk.k_ozdeger(s)
    # Assert
    kontrol("2x2 ozdeger", _yakin(k, beklenen, 1e-10), "-> %r / %r" % (k, beklenen))
    kontrol("yukari sacilma k'yi degistirir", not _yakin(k, mk.k_ozdeger(_sabit()), 1e-6))


def test_reaksiyon_hizi_orani_ve_belirsizlik():
    print("\n[Y8-K4] k_oran = sum(nuF)/sum(A); (s_k/k)^2 = (s_F/F)^2 + (s_A/A)^2")
    from cekirdek import mgxs_k as mk
    # Arrange
    nuf = [(2.0, 0.02), (1.0, 0.01)]
    a = [(1.0, 0.01), (1.0, 0.02)]
    # Act
    k = mk.k_oran(nuf, a)
    # Assert
    F, A = 3.0, 2.0
    sF, sA = math.hypot(0.02, 0.01), math.hypot(0.01, 0.02)
    beklenen = 1.5 * math.hypot(sF / F, sA / A)
    kontrol("oran 1.5", _yakin(k.ort, 1.5))
    kontrol("sapma el hesabi", _yakin(k.sapma, beklenen), "-> %r" % (k,))
    kontrol("payda sifirsa None", mk.k_oran([(1.0, 0.0)], [(0.0, 0.0)]) is None)


def test_ozdeger_belirsizligi_tek_grupta_analitik():
    print("\n[Y8-K5] 1 grup: s_k/k = hypot(s_nuSf/nuSf, s_Sa/Sa) (birinci derece)")
    from cekirdek import mgxs_k as mk
    # Arrange
    s = mk.GrupSabitleri(toplam=(0.6,), absorpsiyon=(0.1,), nu_fisyon=(0.13,),
                         chi=(1.0,), sacilma=((0.5,),))
    sapma = mk.GrupSapmalari(toplam=(0.0,), absorpsiyon=(0.0,), nu_fisyon=(0.0013,),
                             chi=(0.0,), sacilma=((0.0,),))
    # Act
    d = mk.k_ozdeger_belirsiz(s, sapma)
    # Assert
    kontrol("ortalama", _yakin(d.ort, 1.3))
    kontrol("yalniz nuSf %1 -> k %1", _yakin(d.sapma, 0.013, 1e-5), "-> %r" % (d,))


def test_girdi_dogrulama():
    print("\n[Y8-K6] boyut, negatif, chi toplami ve sacilma sekli denetlenir")
    from cekirdek import mgxs_k as mk
    hatalar = 0
    for ek in ({"toplam": (0.5,)}, {"nu_fisyon": (-0.1, 0.1)},
               {"sacilma": ((0.1, 0.1),)}, {"chi": (0.0, 0.0)}):
        try:
            _sabit(**ek)
        except ValueError:
            hatalar += 1
    kontrol("dort gecersiz girdi ValueError", hatalar == 4, "-> %d" % hatalar)
    try:
        mk.k_ozdeger(_sabit(nu_fisyon=(0.0, 0.0)))
        kontrol("fisyonsuz ortamda hata", False)
    except ValueError:
        kontrol("fisyonsuz ortamda hata", True)


HIZLI = [test_tek_grup_k_nusf_bolu_sa, test_iki_grup_yukari_sacilmasiz_el_formulu,
         test_iki_grup_yukari_sacilmali_determinant, test_reaksiyon_hizi_orani_ve_belirsizlik,
         test_ozdeger_belirsizligi_tek_grupta_analitik, test_girdi_dogrulama]
YAVAS = []
