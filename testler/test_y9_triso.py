# -*- coding: utf-8 -*-
"""
 test_y9_triso.py  --  v3 Y9: TRISO tanimi, paketleme orani, duzenli/rastgele yerlesim

 HIZLI: saf hesaplar (hacim, hedef sayi, duzenli adim, dogrulama), paketleme orani
        hedefe +-%1 (hacim sayimiyla), betik/kurucu esdegerligi.
"""

import math

from testler.ortak_test import kontrol


def _kompakt(pf=0.35, yukseklik=0.5, yontem="rastgele"):
    from cekirdek import triso
    t = triso.sablon("agr1", "k", {k: "m_" + k for k in triso.KATMAN_ADLARI} | {"matris": "mat"})
    return dict(t, paketleme=pf, yukseklik=yukseklik, yontem=yontem)


def test_agr1_sablonu_standart_olculer():
    print("\n[Y9-1] AGR-1 sablonu: cekirdek capi 350 um, kaplamalar 100/40/35/40 um")
    from cekirdek import triso
    # Arrange / Act
    t = _kompakt()
    r = [k["r"] for k in t["katmanlar"]]
    # Assert
    kontrol("cekirdek capi 350 um", abs(2 * r[0] - 0.0350) < 1e-9)
    kontrol("kalinliklar 100/40/35/40 um",
            all(abs(a - b) < 1e-9 for a, b in zip((b - a for a, b in zip(r, r[1:])),
                                                  (0.0100, 0.0040, 0.0035, 0.0040))))
    kontrol("dis yaricap 390 um", abs(triso.parcacik_yaricap(t) - 0.0390) < 1e-12)
    kontrol("hata yok (pf 0.35 CRP uyarisi olabilir)", not any(s == "hata" for s, _m in triso.sorunlar(t)))


def test_hedef_sayi_ve_paketleme_orani():
    print("\n[Y9-2] hedef sayi N = int(pf V / Vp); N Vp / V hedefe +-%1")
    from cekirdek import triso
    # Arrange
    t = _kompakt(pf=0.30)
    V = math.pi * 0.6225 ** 2 * 0.5
    Vp = 4 / 3 * math.pi * 0.039 ** 3
    # Act
    n = triso.hedef_sayi(t)
    # Assert
    kontrol("N = int(pf V/Vp)", n == int(0.30 * V // Vp), "-> %d" % n)
    kontrol("pf hedefe %1 icinde", abs(triso.paketleme_orani(t, n) / 0.30 - 1) < 0.01)


def test_duzenli_yerlesim_pf_hedefe_yakin_ve_kap_icinde():
    print("\n[Y9-3] duzenli: adim taramasi pf'yi hedefe +-%1 tutar; parcaciklar kap icinde")
    import numpy as np
    from cekirdek import triso
    # Arrange
    t = _kompakt(pf=0.30, yontem="duzenli")
    # Act
    oz = triso.yerlesim_ozeti(t)
    kap, r = triso.konteyner(t), triso.parcacik_yaricap(t)
    c = triso.duzenli_merkezler(kap, r, oz.adim)
    # Assert
    kontrol("pf +-%1", abs(oz.gercek_pf / 0.30 - 1) < 0.01, "-> %.4f" % oz.gercek_pf)
    kontrol("kap icinde", (np.hypot(c[:, 0], c[:, 1]) + r <= kap.yaricap + 1e-12).all()
            and (np.abs(c[:, 2]) + r <= kap.yukseklik / 2 + 1e-12).all())
    d = np.linalg.norm(c[:, None, :] - c[None, :, :], axis=2) + np.eye(len(c)) * 9
    kontrol("ust uste binme yok (min uzaklik >= 2 r)", d.min() >= 2 * r - 1e-12)


def test_duzenli_pf_siniri_ve_dogrulama():
    print("\n[Y9-4] dogrulama: duzenli pf <= pi/6, rastgele <= 0.64, bozuk katman, eksik malzeme")
    from cekirdek import triso
    # Arrange / Act / Assert
    kontrol("duzenli 0.6 hata", any(s == "hata" for s, _m in
                                    triso.sorunlar(_kompakt(0.6, yontem="duzenli"))))
    kontrol("rastgele 0.7 hata", any(s == "hata" for s, _m in triso.sorunlar(_kompakt(0.7))))
    kontrol("rastgele 0.45 uyari (CRP)", any(s == "uyari" for s, _m in triso.sorunlar(_kompakt(0.45))))
    t = _kompakt()
    t["katmanlar"][2]["r"] = 0.01
    kontrol("azalan yaricap hata", any("büyük olmalı" in m for _s, m in triso.sorunlar(t)))
    t = _kompakt()
    t["katmanlar"][0]["malzeme"] = None
    t["matris_malzeme"] = None
    kontrol("eksik malzeme hata", len([1 for s, _m in triso.sorunlar(t) if s == "hata"]) == 2)


def test_pebble_hacimleri():
    print("\n[Y9-5] HTR-10 sablonu: 8335 parcacik yakit bolgesinde pf ~ %5.0")
    from cekirdek import triso
    # Arrange
    t = triso.sablon("htr10", "p", {k: "m" for k in triso.KATMAN_ADLARI}
                     | {"matris": "m", "kabuk": "m", "dis": "m"})
    # Act
    n = triso.hedef_sayi(t)
    # Assert
    kontrol("N ~ 8335 (HTR-10 benchmark)", abs(n - 8335) <= 10, "-> %d" % n)
    kontrol("sorun yok", triso.sorunlar(t) == [], "-> %r" % triso.sorunlar(t))
    kontrol("kap hacmi 4/3 pi r^3", abs(triso.konteyner(t).hacim - 4 / 3 * math.pi * 2.5 ** 3) < 1e-9)


HIZLI = [test_agr1_sablonu_standart_olculer, test_hedef_sayi_ve_paketleme_orani,
         test_duzenli_yerlesim_pf_hedefe_yakin_ve_kap_icinde,
         test_duzenli_pf_siniri_ve_dogrulama, test_pebble_hacimleri]
YAVAS = []
