# -*- coding: utf-8 -*-
"""
test_vv_altkume.py -- uygulamaya uygun V&V alt kumesi (NUREG/CR-6698 §2.5, Tablo 2.3).

  [VA1] aoa_filtresi: bolunebilir tur + fiziksel bicim + tayf (+ U-235 zenginlik
        sinifi, ICSBEP LEU/IEU/HEU); biri eksikse None (USL yok).
  [VA2] Regresyon: pwr_17x17 (LEU oksit kafes, termal) -> USL YALNIZ LEU oksit
        kafeslerden (v3 Y11: LCT-006 + LCT-008, n >= 10). Eski kod yalniz tayfla
        9 cozelti + 1 LCT secip USL 0.93877 veriyordu.
  [VA3] Hizli metal (Godiva benzeri) uygulama: >= 10 uygun vakalik kumede USL
        verilir; alt kume, n ve yontem K6 "gecti" metninde yazar.
  [VA4] Depodaki kume ile Godiva: U-235 HEU hizli metal vaka sayisi < 10 -> USL yok
        (durust sonuc; kume buyudukce degisir).

Monte Carlo KOSULMAZ: tayf (EALF) uygulama girdisi olarak verilir.
"""

import json
import os

from testler.ortak_test import kontrol, ORNEK


def _spec(ad):
    with open(os.path.join(ORNEK, ad), encoding="utf-8") as f:
        return json.load(f)


def _godiva_benzeri_kume(n=12):
    from cekirdek.vv.istatistik import Vaka
    vlar = []
    for i in range(n):
        vlar.append(Vaka("h%d" % i, 1.0 + 0.0004 * ((i * 5) % 7 - 3), 0.0002, 1.0, 0.002,
                         {"bolunebilir": "U-235", "fiziksel_bicim": "metal", "tayf": "hizli",
                          "yansitici": "yok", "zenginlik": 90.0 + 0.5 * i,
                          "ealf": 8e5 + 1e4 * i, "h_x": 0.0}, "SERI-%d" % i))
    # Uygunsuz vakalar (alt kumeye GIRMEMELI): termal cozelti ve Pu metal
    vlar.append(Vaka("t", 0.99, 0.0002, 1.0, 0.002, {"bolunebilir": "U-235",
                     "fiziksel_bicim": "cozelti", "tayf": "termal", "zenginlik": 93.0}, "T"))
    vlar.append(Vaka("p", 0.99, 0.0002, 1.0, 0.002, {"bolunebilir": "Pu",
                     "fiziksel_bicim": "metal", "tayf": "hizli", "zenginlik": 95.0}, "P"))
    return vlar


def test_aoa_filtresi_daraltir():
    print("\n[VA1] AOA filtresi: tur + bicim + tayf (+ zenginlik sinifi)")
    from cekirdek.vv import kume
    f = kume.aoa_filtresi({"bolunebilir": "U-235", "fiziksel_bicim": "oksit",
                           "tayf": "termal", "zenginlik": 3.2})
    kontrol("filtre tur, bicim, tayf iceriyor", f and f.get("bolunebilir") == "U-235"
            and f.get("fiziksel_bicim") == "oksit" and f.get("tayf") == "termal", "-> %r" % f)
    kontrol("U-235 %3.2 -> LEU zenginlik araligi", f and f.get("zenginlik", (None,))[0]
            == "aralik" and f["zenginlik"][1] <= 3.2 <= f["zenginlik"][2]
            and f["zenginlik"][2] <= 10.0, "-> %r" % ((f or {}).get("zenginlik"),))
    kontrol("bicim eksik -> None", kume.aoa_filtresi(
        {"bolunebilir": "U-235", "tayf": "termal", "zenginlik": 3.2}) is None)
    kontrol("tayf eksik -> None", kume.aoa_filtresi(
        {"bolunebilir": "U-235", "fiziksel_bicim": "oksit", "zenginlik": 3.2}) is None)
    fp = kume.aoa_filtresi({"bolunebilir": "Pu", "fiziksel_bicim": "metal", "tayf": "hizli",
                            "zenginlik": 94.0})
    kontrol("Pu: zenginlik sinifi yok", fp and "zenginlik" not in fp, "-> %r" % fp)


def test_pwr_17x17_usl_vermez():
    print("\n[VA2] Regresyon: pwr_17x17 LEU oksit kafes -> USL YALNIZ LEU oksit kafeslerden")
    from cekirdek.vv import kume
    vv, uyg = kume.uygulama_ozeti(_spec("pwr_17x17.json"), uygulama={"tayf": "termal"})
    alt = kume.vakalar(filtre=kume.aoa_filtresi(uyg))
    kontrol("uygulama spec'ten: oksit, U-235", uyg.get("fiziksel_bicim") == "oksit"
            and uyg.get("bolunebilir") == "U-235")
    kontrol("alt kumede cozelti yok (yalniz oksit)", alt and all(
        v.parametreler.get("fiziksel_bicim") == "oksit" for v in alt), "-> %d" % len(alt))
    kontrol("n = alt kume (v3 Y11: LCT-006 + LCT-008)", vv.n == len(alt) and vv.n >= 10,
            "-> n %d" % vv.n)
    kontrol("USL hesaplandi; eski hatali 0.93877 (9 cozelti + 1 LCT) degil",
            vv.usl is not None and abs(vv.usl - 0.93877) > 1e-4, "-> %r" % vv.usl)
    kontrol("alt kume metni oksit + LEU", "oksit" in vv.alt_kume and "LEU" in vv.alt_kume,
            "-> %s" % vv.alt_kume)
    # Kume normal degil (iki seri arasi ~130 pcm fark; docs/VV.md): parametrik olmayan yontem.
    kontrol("yontem durust: parametrik olmayan", vv.yontem == "parametrik_olmayan",
            "-> %s" % vv.yontem)


def _baglam(vv, uyg, k=0.90, s=0.0005):
    from cekirdek.uygunluk_denetimi.kurallar import Baglam
    from cekirdek.uygunluk_denetimi.ayristir import KosuVerisi
    kosu = KosuVerisi(statepoint="", mod="eigenvalue", keff=k, sigma=s, parcacik=1,
                      cevrim=1, pasif=0)
    return Baglam(spec={}, kosu=kosu, vv=vv, uygulama=uyg)


def test_hizli_metal_usl_verir():
    print("\n[VA3] Hizli metal (Godiva benzeri): uygun alt kume n >= 10 -> USL")
    from cekirdek.vv import kume
    from cekirdek.uygunluk_denetimi import kurallar_kritiklik as kk
    uyg = {"bolunebilir": "U-235", "fiziksel_bicim": "metal", "tayf": "hizli",
           "zenginlik": 93.7, "h_x": 0.0, "ealf": 8.3e5}
    vv, _u = kume.uygulama_ozeti(None, uygulama=uyg, vlar=_godiva_benzeri_kume())
    kontrol("alt kume n = 12 (termal ve Pu disarida)", vv.n == 12, "-> %d" % vv.n)
    kontrol("USL hesaplandi", vv.usl is not None and vv.usl < 1.0, "-> %r" % vv.usl)
    kontrol("alt kume metni tur/bicim/tayf/HEU", all(
        p in vv.alt_kume for p in ("U-235", "metal", "HEU")), "-> %s" % vv.alt_kume)
    kural = [k for k in kk.KURALLAR if k.kimlik == "K6"][0]
    b = kk.k6_usl(kural, _baglam(vv, uyg))
    kontrol("K6 gecti", b and b[0].durum == "karsilandi", "-> %s" % [x.durum for x in b])
    m = b[0].mesaj if b else ""
    kontrol("K6 metninde alt kume, n ve yontem", vv.alt_kume in m and "n = 12" in m
            and vv.yontem in m, "-> %s" % m)


def test_depo_godiva_usl_yok():
    print("\n[VA4] Depodaki kume: U-235 HEU hizli metal n < 10 -> USL yok")
    from cekirdek.vv import kume
    vv, uyg = kume.uygulama_ozeti(_spec("godiva_kriter.json"), uygulama={"tayf": "hizli"})
    n = len(kume.vakalar(filtre=kume.aoa_filtresi(uyg)))
    kontrol("depoda uygun vaka < 10", n < 10, "-> %d" % n)
    kontrol("USL None + durust neden", vv.usl is None and "USL yok" in vv.usl_neden,
            "-> %s" % vv.usl_neden)


def test_k12_hx_heterojen_uyarir():
    print("\n[VA5] K12: heterojen uygulamada H/X yok -> uyari (sessiz gecmez)")
    from cekirdek.vv import kume
    from cekirdek.uygunluk_denetimi import kurallar_kritiklik as kk
    uyg = kume.uygulama(_spec("pwr_17x17.json"))
    vv = kume.ozet(_godiva_benzeri_kume())  # kumede h_x araligi var
    kontrol("uygulamada h_x yok", "h_x" not in uyg)
    kural = [k for k in kk.KURALLAR if k.kimlik == "K12"][0]
    b = kk.k12_aralik(kural, _baglam(vv, uyg))
    kontrol("K12-h_x uyarisi", any(x.kural == "K12-h_x" and x.durum != "karsilandi"
                                   for x in b), "-> %s" % [(x.kural, x.durum) for x in b])


HIZLI = [test_aoa_filtresi_daraltir, test_pwr_17x17_usl_vermez, test_hizli_metal_usl_verir,
         test_depo_godiva_usl_yok, test_k12_hx_heterojen_uyarir]
YAVAS = []
