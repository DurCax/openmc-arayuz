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
    c = triso.duzenli_merkezler(kap, r, oz.adim, oz.kayma)
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


# ---------------------------------------------------------------------------
# model kurulumu (openmc nesneleri; nukleer veri gerekmez)
# ---------------------------------------------------------------------------

def _model_spec(pf=0.30, yukseklik=0.5, yontem="rastgele"):
    import json
    import os
    from testler.ortak_test import ORNEK
    from cekirdek import sema
    with open(os.path.join(ORNEK, "htgr_kompakt.json"), encoding="utf-8") as f:
        ham = json.load(f)
    t = ham["trisolar"][0]
    t.update(paketleme=pf, yukseklik=yukseklik, yontem=yontem)
    ham["geometri"]["kok"]["yukseklik"] = yukseklik
    return sema.tamamla(ham)


def _kafes_merkezleri(model):
    """Kurulmus modeldeki TRISO merkezleri (global, tekil): kafes elemanlarinin parcalari."""
    import numpy as np
    import openmc
    kafes = next(c.fill for c in model.geometry.get_all_cells().values()
                 if isinstance(c.fill, openmc.RectLattice))
    ll, pitch = np.array(kafes.lower_left), np.array(kafes.pitch)
    merkezler = {}
    import itertools
    for idx in itertools.product(*(range(n) for n in kafes.shape)):
        evren = kafes.get_universe(idx)
        if evren is None:
            continue
        eleman = ll + (np.array(idx) + 0.5) * pitch
        for h in evren.cells.values():
            if h.translation is not None and h.fill_type == "universe":
                g = tuple(np.round(eleman + np.asarray(h.translation), 9))
                merkezler[g] = 1
    return np.array(sorted(merkezler))


def test_kurulan_modelde_paketleme_orani_hacim_sayimiyla_hedefe_yuzde_bir_icinde():
    print("\n[Y9-6] rastgele paketleme: kafesteki TRISO sayimi -> pf hedefe +-%1; cakisma yok")
    import warnings
    import numpy as np
    from cekirdek import kurucu, triso
    # Arrange
    spec = _model_spec(pf=0.30)
    t = spec["trisolar"][0]
    # Act
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model, _b = kurucu.kur(spec)
    c = _kafes_merkezleri(model)
    r = triso.parcacik_yaricap(t)
    pf = len(c) * triso.parcacik_hacmi(t) / triso.konteyner(t).hacim
    d = np.linalg.norm(c[:, None, :] - c[None, :, :], axis=2) + np.eye(len(c)) * 9
    # Assert
    kontrol("sayim = hedef sayi", len(c) == triso.hedef_sayi(t), "-> %d" % len(c))
    kontrol("pf hedefe %1 icinde", abs(pf / 0.30 - 1) < 0.01, "-> %.4f" % pf)
    kontrol("parcaciklar ust uste binmiyor", d.min() >= 2 * r - 1e-6, "-> %.6g" % d.min())
    kontrol("kap icinde", (np.hypot(c[:, 0], c[:, 1]) + r <= 0.6225 + 1e-9).all())


def test_betik_ve_kurucu_ayni_parcaciklari_kurar():
    print("\n[Y9-7] betik esdegerligi: uretilen betik ayni TRISO merkezlerini ve ayni hacimleri kurar")
    import importlib.util
    import os
    import tempfile
    import warnings
    import numpy as np
    from cekirdek import kod_uret, kurucu
    for yontem in ("rastgele", "duzenli"):
        # Arrange
        spec = _model_spec(pf=0.20, yontem=yontem)
        # Act
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model, _b = kurucu.kur(spec)
            with tempfile.TemporaryDirectory() as d:
                yol = os.path.join(d, "model.py")
                with open(yol, "w", encoding="utf-8") as f:
                    f.write(kod_uret.uret(spec, "model.py"))
                eski = os.getcwd()
                os.chdir(d)
                try:
                    sm = importlib.util.spec_from_file_location("y9_betik_" + yontem, yol)
                    mod = importlib.util.module_from_spec(sm)
                    sm.loader.exec_module(mod)
                finally:
                    os.chdir(eski)
        a, b = _kafes_merkezleri(model), _kafes_merkezleri(mod.model)
        # Assert
        kontrol("%s: ayni sayida parcacik" % yontem, len(a) == len(b) > 0, "-> %d / %d" % (len(a), len(b)))
        kontrol("%s: merkezler ayni" % yontem, np.allclose(a, b, atol=1e-9))


HIZLI += [test_kurulan_modelde_paketleme_orani_hacim_sayimiyla_hedefe_yuzde_bir_icinde,
          test_betik_ve_kurucu_ayni_parcaciklari_kurar]


def test_dogrula_triso_2b_model_hata_ve_tanimsiz_malzeme():
    print("\n[Y9-8] dogrula: 2B modelde kompakt hata; tanimsiz malzeme hata; yukseklik uyumsuzlugu uyari")
    from cekirdek import dogrula
    # Arrange
    spec = _model_spec(pf=0.2)
    # Act / Assert
    temiz = [b for b in dogrula.tum_kontroller(spec, veri_kontrolu=False)
             if b.yer.startswith("trisolar")]
    kontrol("temiz modelde TRISO bulgusu yok", temiz == [], "-> %r" % temiz)
    s2 = _model_spec(pf=0.2)
    s2["geometri"]["kok"]["yukseklik"] = None
    b2 = dogrula.tum_kontroller(s2, veri_kontrolu=False)
    kontrol("2B: hata", any(b.seviye == "hata" and "3B" in b.mesaj for b in b2))
    s3 = _model_spec(pf=0.2)
    s3["trisolar"][0]["matris_malzeme"] = "yok_boyle"
    b3 = dogrula.tum_kontroller(s3, veri_kontrolu=False)
    kontrol("tanimsiz malzeme hata", any(b.seviye == "hata" and "tanımsız malzeme" in b.mesaj
                                         for b in b3))
    s4 = _model_spec(pf=0.2)
    s4["trisolar"][0]["yukseklik"] = 0.4
    b4 = dogrula.tum_kontroller(s4, veri_kontrolu=False)
    kontrol("yukseklik farki uyari", any(b.seviye == "uyari" and "yüksekliğinden" in b.mesaj
                                         for b in b4))


def test_malzeme_adi_degisimi_triso_alanlarini_gunceller():
    print("\n[Y9-9] malzeme yeniden adlandirma: TRISO katman ve matris basvurulari da degisir")
    from cekirdek import sema
    # Arrange
    spec = _model_spec(pf=0.2)
    # Act
    sema.malzeme_adini_degistir(spec, "uco", "uco2")
    sema.malzeme_adini_degistir(spec, "matris", "matris2")
    t = spec["trisolar"][0]
    # Assert
    kontrol("kernel uco2", t["katmanlar"][0]["malzeme"] == "uco2")
    kontrol("matris2", t["matris_malzeme"] == "matris2")


HIZLI += [test_dogrula_triso_2b_model_hata_ve_tanimsiz_malzeme,
          test_malzeme_adi_degisimi_triso_alanlarini_gunceller]
