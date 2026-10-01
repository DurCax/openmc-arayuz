# -*- coding: utf-8 -*-
"""
 test_geometri_tuketici2.py  --  G-2: tukenme hacmi agac modunda (+ stokastik yedek)

 Agac modundaki duzeneklerde (docs §4 ve G-1 fiksturleri) tukenme hacimleri,
 ornek sayisi, dogrulama (kesik -> UYARI; cubuk cubuk yanmada HATA) ve
 yavas: analitik hacim OpenMC stokastik hacmiyle; kesik malzemede stokastik
 yedek. Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import math
import os

from testler.ortak_test import kontrol
from testler import geometri_ortak as go


def _tukenmeli(spec, ayir=False):
    spec["tukenme"] = dict(spec.get("tukenme") or {}, var=True, malzemeleri_ayir=ayir)
    return spec


def test_tukenme_hacimleri_agac():
    print("\n[GU1] agac modunda tukenme.hacimler ve ornek sayisi")
    from cekirdek import sema, tukenme
    spec = _tukenmeli(go.duzenek_c())
    hv = tukenme.hacimler(spec)
    c = sema.cubuk_bul(spec, "yakit_24")
    beklenen = 5 * 264 * math.pi * c["bolgeler"][0]["r"] ** 2 * 200.0
    v = (hv.get("uo2_24") or {}).get("hacim")
    kontrol("(c) uo2_24 = 5 demet x 264 pin x 200 cm: %.6g" % beklenen,
            v is not None and abs(v - beklenen) <= 1e-9 * beklenen, "-> %s" % hv.get("uo2_24"))
    kontrol("(c) b4c tambur emicisi yanabilir ve analitik",
            (hv.get("b4c") or {}).get("yontem") == "analitik", "-> %s" % hv.get("b4c"))
    n = tukenme.yakit_ornek_sayisi(spec)
    kontrol("(c) en cok ornek = 5 x 264 = 1320", n == 1320, "-> %d" % n)
    spec = _tukenmeli(go.duzenek_a(yakit_blok=True))
    hv = tukenme.hacimler(spec)
    kontrol("(a-yakit) kesik yakit bloklarinin yakiti 'stokastik hesap gerekli'",
            (hv.get("uo2_24") or {}).get("yontem") == "stokastik hesap gerekli",
            "-> %s" % hv.get("uo2_24"))


def test_tukenme_dogrulama_agac():
    print("\n[GU2] agac modunda tukenme dogrulamasi: kesik -> UYARI, cubuk cubuk yanmada HATA")
    from cekirdek import dogrula
    for ayir, seviye in ((False, "uyari"), (True, "hata")):
        spec = _tukenmeli(go.duzenek_a(yakit_blok=True), ayir)
        b = [x for x in dogrula.tukenme_kontrol(spec) if x.yer == "tukenme/uo2_24"]
        kontrol("malzemeleri_ayir=%s -> %s" % (ayir, seviye),
                b and all(x.seviye == seviye for x in b), "-> %s" % [(x.seviye, x.mesaj) for x in b])
    spec = _tukenmeli(go.duzenek_c())
    b = [x for x in dogrula.tukenme_kontrol(spec) if x.yer.startswith("tukenme/")]
    kontrol("(c) kesiksiz duzenekte hacim bulgusu yok", not b, "-> %s" % [x.mesaj for x in b])


def test_hazirla_ayirma_kesik_hata():
    print("\n[GU3] cubuk cubuk yanma + kesik yakit: hazirla stokastik hesaba girmeden durur")
    from cekirdek import tukenme
    spec = _tukenmeli(go.duzenek_a(yakit_blok=True), ayir=True)
    try:
        tukenme._hazir_hacimler(spec)
        hata = None
    except ValueError as e:
        hata = str(e)
    kontrol("ValueError 'kesin örnek hacmi'", hata is not None and "kesin" in hata, "-> %s" % hata)


def test_yavas_stokastik_capraz(gecici):
    print("\n[GU4] analitik hacim = OpenMC stokastik hacim (agac modu); kesik -> stokastik yedek")
    from cekirdek.geometri import hacim
    from cekirdek import geometri
    olcumler = []
    for ad, uret, mal in (("c", go.duzenek_c, "b4c"), ("c", go.duzenek_c, "uo2_31"),
                          ("d-kare", lambda: go.duzenek_d("kare"), "uo2_24"),
                          ("b", go.duzenek_b, "b4c")):
        spec = uret()
        an = hacim.analitik(geometri.model(spec), mal).hacim
        dizin = os.path.join(gecici, "%s_%s" % (ad, mal))
        os.makedirs(dizin, exist_ok=True)
        v, sd = hacim.stokastik(spec, [mal], orneklem=4_000_000, dizin=dizin)[mal]
        sapma = abs(v - an) / sd if sd else float("inf")
        olcumler.append(sapma)
        print("  (%s) %s: analitik %.5g, stokastik %.5g +- %.3g cm3 (%.2f sigma)"
              % (ad, mal, an, v, sd, sapma))
        kontrol("(%s) %s analitik = stokastik (3 sigma)" % (ad, mal), sapma <= 3.0)
    ic_bir = sum(1 for s in olcumler if s <= 1.0)
    print("  1 sigma icinde: %d / %d" % (ic_bir, len(olcumler)))
    kontrol("olcumlerin cogu 1 sigma icinde (beklenen ~%68)", ic_bir >= len(olcumler) // 2)
    spec = go.duzenek_a(yakit_blok=True)
    dizin = os.path.join(gecici, "a_yakit")
    os.makedirs(dizin, exist_ok=True)
    k = hacim.hesapla(spec, "uo2_24", orneklem=2_000_000, dizin=dizin)
    print("  (a-yakit) uo2_24: %s %s" % (k.yontem, k.hacim))
    kontrol("(a-yakit) kesik yakit stokastik yedege duser ve bildirir",
            k.yontem == hacim.STOKASTIK and k.hacim and k.sapma and "stokastik" in k.ayrinti)


HIZLI = [test_tukenme_hacimleri_agac, test_tukenme_dogrulama_agac, test_hazirla_ayirma_kesik_hata]
YAVAS = [test_yavas_stokastik_capraz]
