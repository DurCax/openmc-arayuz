# -*- coding: utf-8 -*-
"""
 test_y4_kosu.py  --  v3 Y4: gercek tukenme kosulari (YAVAS; kucuk modeller,
                      CASL zinciri, dusuk istatistik)

   [Y4-K1] Sogutma: 1 guclu + 2 sogutma adimi. Sogutmada k NaN (transport
           yok), yanma artmaz, bozunma isisi azalir.
   [Y4-K2] Surdurme: 2 adimlik kosuya 3. adim eklenip surdurulur; ilk iki
           kayit degismez (ayni k), 4 zaman noktasi, surdurulen = 2.
   [Y4-K3] Entegrator karsilastirmasi (CE/CM - CE/LI): ayni tohum ve adimlar;
           k ve U-235 farki RAPORLANIR, esik konmaz (kart karari).
   [Y4-K4] Hizli kip (MicroXS): U-235 tam tukenmeyle (predictor) karsilastirilir;
           2 gunluk yanmada spektrum degisimi ihmal edilebilir -> bagil fark
           < 1e-3 (olculen 2.6e-6).
   [Y4-K5] Bor aramasi: her guclu adimda |k - 1| <= k_tol + 3 sigma (arama
           tolerans icinde durur, adimin transport'u bagimsiz olcum: %99.7);
           bulunan bor statik kritik bor bolgesinde (taze pin ~3300 ppm).
   [Y4-K6] Cubuk aramasi: 3B demet (60 cm), ayni olcut; daldirma 0-100 %.
"""

import copy
import math
import os

from cekirdek import sema
from testler.ortak_test import ORNEK, kontrol

K_TOL = 5.0e-3          # kucuk model: adim basina sigma ~5e-3 duzeyinde


def _pin(**tukenme):
    s = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    s["ayarlar"].update(parcacik=1000, cevrim=15, pasif=5)
    s["tukenme"].update(zincir="casl_termal", entegrator="predictor", adim_gucu=False)
    s["tukenme"].update(tukenme)
    return s


def test_sogutma_kosusu(gecici):
    print("\n[Y4-K1] sogutma adimlari: k NaN, yanma sabit, isi azalir")
    from cekirdek import tukenme, tukenme_cikti
    s = _pin(adimlar=[1.0], sogutma={"adimlar": [1.0, 10.0], "birim": "d"})
    h5, _b = tukenme.calistir(s, os.path.join(gecici, "k1"))
    r = tukenme.sonuc_oku(h5, s)
    kontrol("4 zaman noktasi", len(r["zaman_d"]) == 4, repr(r["zaman_d"]))
    kontrol("guclu adimda k var, sogutmada NaN", math.isfinite(r["k"][0])
            and all(math.isnan(k) for k in r["k"][1:]), repr(r["k"]))
    kontrol("yanma sogutmada artmaz", r["yanma"][1] == r["yanma"][2] == r["yanma"][3] > 0,
            repr(r["yanma"]))
    isi = tukenme_cikti.cikti_oku(h5, s)["toplam"]["isi"]
    kontrol("bozunma isisi sogutmada azalir: %s" % ["%.3g" % x for x in isi],
            isi[1] > isi[2] > isi[3] > 0)


def test_surdurme_kosusu(gecici):
    print("\n[Y4-K2] surdurme: eklenen adim kosulur, ilk kayitlar degismez")
    from cekirdek import tukenme
    d = os.path.join(gecici, "k2")
    s = _pin(adimlar=[1.0, 1.0])
    h5, _b = tukenme.calistir(s, d)
    once = tukenme.sonuc_oku(h5, s)
    s2 = copy.deepcopy(s)
    s2["tukenme"].update(adimlar=[1.0, 1.0, 2.0], surdur=True)
    h5, b = tukenme.calistir(s2, d)
    sonra = tukenme.sonuc_oku(h5, s2)
    kontrol("surdurulen = 2", b["surdurulen"] == 2, repr(b["surdurulen"]))
    kontrol("4 zaman noktasi: 0, 1, 2, 4 gun", sonra["zaman_d"] == [0.0, 1.0, 2.0, 4.0],
            repr(sonra["zaman_d"]))
    kontrol("ilk iki k degismedi", sonra["k"][:2] == once["k"][:2])
    kontrol("eski sonuc 'guncel'", tukenme.eskime(s2, d)[0] == "guncel")


def test_entegrator_karsilastirmasi(gecici):
    print("\n[Y4-K3] CE/CM ile CE/LI farki (rapor; esik yok)")
    from cekirdek import tukenme
    sonuc = {}
    for kod in ("cecm", "celi"):
        s = _pin(adimlar=[1.0, 5.0], entegrator=kod)
        h5, _b = tukenme.calistir(s, os.path.join(gecici, kod))
        sonuc[kod] = tukenme.sonuc_oku(h5, s)
    a, b = sonuc["cecm"], sonuc["celi"]
    for i in range(len(a["k"])):
        print("  adim %d: k CECM %.5f +/- %.5f  CELI %.5f +/- %.5f  fark %+.0f pcm"
              % (i, a["k"][i], a["k_sapma"][i], b["k"][i], b["k_sapma"][i],
                 (a["k"][i] - b["k"][i]) * 1e5))
    ua, ub = a["yogunluk"]["uo2"]["U235"][-1], b["yogunluk"]["uo2"]["U235"][-1]
    print("  U-235 (6 gun): CECM %.6e  CELI %.6e  bagil fark %.2e" % (ua, ub, ua / ub - 1))
    kontrol("iki entegrator de sonuc verdi", all(math.isfinite(x) for x in a["k"] + b["k"]))


def test_hizli_kip(gecici):
    print("\n[Y4-K4] hizli kip (MicroXS) ile tam tukenme")
    from cekirdek import tukenme
    sonuc = {}
    for hizli in (False, True):
        s = _pin(adimlar=[1.0, 1.0], hizli_kip=hizli)
        h5, _b = tukenme.calistir(s, os.path.join(gecici, "h%d" % hizli))
        sonuc[hizli] = tukenme.sonuc_oku(h5, s)
    ut, uh = (sonuc[x]["yogunluk"]["uo2"]["U235"][-1] for x in (False, True))
    print("  U-235 (2 gun): tam %.8e  hizli %.8e  bagil fark %.2e" % (ut, uh, uh / ut - 1))
    kontrol("bagil fark < 1e-3", abs(uh / ut - 1) < 1e-3)
    kontrol("hizli kipte k yok (NaN)", all(math.isnan(k) for k in sonuc[True]["k"]))


def _arama_olcutu(r):
    for i, (k, s, g, x) in enumerate(zip(r["k"], r["k_sapma"], r["guclu"], r["arama_degeri"])):
        if not g:
            continue
        kontrol("adim %d: k = %.5f +/- %.5f, deger %.4g; |k-1| <= %.0e + 3 sigma"
                % (i, k, s, x if x is not None else float("nan"), K_TOL),
                x is not None and abs(k - 1.0) <= K_TOL + 3.0 * s)


def test_bor_aramasi(gecici):
    print("\n[Y4-K5] tukenme sirasinda kritik bor aramasi")
    from cekirdek import tukenme
    s = _pin(adimlar=[1.0, 2.0], kritik_arama={
        "var": True, "tur": "bor", "hedef": "su", "alt": 500.0, "ust": 1500.0,
        "sinir": [0.0, 5000.0], "k_tol": K_TOL, "sigma": K_TOL})
    s["ayarlar"].update(parcacik=1500, cevrim=20, pasif=5)
    h5, _b = tukenme.calistir(s, os.path.join(gecici, "bor"))
    r = tukenme.sonuc_oku(h5, s)
    _arama_olcutu(r)
    kontrol("bor taze pinde 2000-5000 ppm (statik: 3000 ppm'de k = 1.019)",
            all(2000.0 < x < 5000.0 for x in r["arama_degeri"][:2]), repr(r["arama_degeri"]))


def test_cubuk_aramasi(gecici):
    print("\n[Y4-K6] tukenme sirasinda kontrol cubugu aramasi (3B demet)")
    from cekirdek import tukenme
    s = sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json"))
    s["kor"]["yukseklik"] = 60.0
    s["ayarlar"].update(parcacik=2000, cevrim=20, pasif=5)
    s["ayarlar"]["entropi_mesh"]["var"] = False
    s["tukenme"].update(var=True, zincir="casl_termal", entegrator="predictor", adimlar=[1.0],
                        adim_gucu=False, kritik_arama={
                            "var": True, "tur": "cubuk", "hedef": "kontrol_cubugu",
                            "alt": 20.0, "ust": 80.0, "sinir": [0.0, 100.0],
                            "k_tol": K_TOL, "sigma": K_TOL})
    h5, _b = tukenme.calistir(s, os.path.join(gecici, "cubuk"), veri_kontrolu=False)
    r = tukenme.sonuc_oku(h5, s)
    _arama_olcutu(r)
    kontrol("daldirma 0-100 %", all(0.0 <= x <= 100.0 for x in r["arama_degeri"][:1]))


YAVAS = [test_sogutma_kosusu, test_surdurme_kosusu, test_entegrator_karsilastirmasi,
         test_hizli_kip, test_bor_aramasi, test_cubuk_aramasi]
ZINCIR_GEREKEN = YAVAS
