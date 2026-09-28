# -*- coding: utf-8 -*-
"""
 test_kosu_yardimcilari.py  --  3f/3i. entropi yakinsamasi, onbellek, reaktivite, tarama, kritik arama, k-eff yorumu

 testler/test_regresyon.py'den tasindi (Dalga 0; test metinleri aynen).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

import os

from cekirdek import sema, kurucu, dogrula
from testler.ortak_test import kontrol
from testler.regresyon_ortak import ORNEK


# ============================================================================
# 3f. KAYNAK YAKINSAMASI (Shannon entropisi)
# ============================================================================

def test_entropi_ayristirma():
    """Cevrim satiri ayristirici entropili ve entropisiz bicimi de tanimali."""
    print("\n[3f] Entropi cikti ayristirma (iki bicim)")
    from cekirdek.kosucu import cevrim_satiri
    durumlar = [
        ("entropisiz pasif", "        5/1    1.19846", (5, 1.19846, None, None)),
        ("entropisiz aktif", "       54/1    1.32041    1.36400 +/- 0.00368",
         (54, 1.32041, None, 1.364)),
        ("entropili pasif", "        5/1    1.22935    5.96734",
         (5, 1.22935, 5.96734, None)),
        ("entropili aktif", "       10/1    1.16569    5.94225    1.15720 +/- 0.00849",
         (10, 1.16569, 5.94225, 1.15720)),
    ]
    for ad, satir, beklenen in durumlar:
        r = cevrim_satiri(satir)
        ok = (r is not None and r["cevrim"] == beklenen[0]
              and abs(r["k"] - beklenen[1]) < 1e-9
              and ((r["entropi"] is None and beklenen[2] is None)
                   or (r["entropi"] is not None and abs(r["entropi"] - beklenen[2]) < 1e-9))
              and ((r["ortalama"] is None and beklenen[3] is None)
                   or (r["ortalama"] is not None and abs(r["ortalama"] - beklenen[3]) < 1e-9)))
        kontrol(ad, ok)
    for ad, satir in (("statepoint satiri", " Creating state point statepoint.60.h5..."),
                      ("zaman satiri", " Total time elapsed = 6.5384e+00 seconds")):
        kontrol("%s reddedilmeli" % ad, cevrim_satiri(satir) is None)


def test_entropi_yakinsama():
    """Yakinsama karari sentetik veride dogru olmali."""
    print("\n[3g] Kaynak yakinsamasi karari")
    import random
    from cekirdek.kosucu import entropi_yakinsama
    random.seed(7)

    def gurultu(n, taban, sigma):
        return [taban + random.gauss(0, sigma) for _ in range(n)]

    sabit = gurultu(30, 5.95, 0.01) + gurultu(70, 5.95, 0.01)
    kontrol("sabit entropi -> yakinsamis",
            entropi_yakinsama(sabit, 30)[0] is True)
    kayan = [5.50 + 0.015 * i + random.gauss(0, 0.01) for i in range(30)]
    kontrol("kayan entropi -> yakinsamamis",
            entropi_yakinsama(kayan + gurultu(70, 5.95, 0.01), 30)[0] is False)
    kontrol("pasif=2 -> karar verilemez",
            entropi_yakinsama(gurultu(40, 5.95, 0.01), 2)[0] is None)
    kontrol("entropi yok -> karar verilemez",
            entropi_yakinsama([None] * 40, 20)[0] is None)


def test_onbellek():
    """Model onbellegi ayni spec icin yeniden kurmamali, degisince kurmali."""
    print("\n[3h] Model onbellegi")
    from cekirdek import onbellek
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    m1, _ = onbellek.kur_onbellekli(spec)
    m2, _ = onbellek.kur_onbellekli(spec)
    kontrol("ayni spec -> ayni nesne", m1 is m2)
    import copy as _copy
    degisik = _copy.deepcopy(spec)
    degisik["kor"]["adim"] = 1.30
    m3, _ = onbellek.kur_onbellekli(degisik)
    kontrol("degisen spec -> yeni nesne", m3 is not m1)
    kontrol("kur_taze her zaman yeni", onbellek.kur_taze(spec)[0] is not m1)


# ============================================================================
# 3i. REAKTIVITE, TARAMA VE KRITIK ARAMA
# ============================================================================

def test_reaktivite():
    """rho = (k-1)/k ve belirsizlik yayilimi dogru olmali."""
    print("\n[3i] Reaktivite hesabi")
    from cekirdek.tarama import reaktivite
    for k, beklenen in ((1.0, 0.0), (1.05, 4761.9), (0.95, -5263.2)):
        r, _ = reaktivite(k, 0.001)
        kontrol("k=%.2f -> %.1f pcm" % (k, beklenen), abs(r - beklenen) < 0.1)
    # sigma_rho = sigma_k / k^2
    _, s = reaktivite(1.25, 0.001)
    kontrol("belirsizlik yayilimi", abs(s - 1e5 * 0.001 / 1.25 ** 2) < 1e-6)


def test_parametre_uygula():
    """Tarama parametreleri spec'i dogru degistirmeli, kaynagi bozmamali."""
    print("\n[3j] Parametre uygulama")
    from cekirdek import tarama
    from cekirdek import malzeme_kutup as mk
    spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    ilk_sicaklik = sema.malzeme_bul(spec, "su")["sicaklik"]

    y, _ = tarama.parametre_uygula(spec, "yakit_sicaklik", "uo2", 1100.0)
    kontrol("yakit sicakligi", sema.malzeme_bul(y, "uo2")["sicaklik"] == 1100.0)
    kontrol("kaynak spec bozulmadi",
            sema.malzeme_bul(spec, "su")["sicaklik"] == ilk_sicaklik)

    # sogutucu sicakligi: YOGUNLUK DA degismeli (en kritik davranis)
    y, _ = tarama.parametre_uygula(spec, "sogutucu_sicaklik", "su", 620.0)
    yeni_rho = sema.malzeme_bul(y, "su")["yogunluk"]["deger"]
    kontrol("sogutucu sicakligi yogunlugu da degistirdi",
            abs(yeni_rho - mk.su_yogunluk(620.0)) < 1e-9,
            "rho = %.4f" % yeni_rho)

    # void: rho0*(1-alfa)
    rho0 = sema.malzeme_bul(spec, "su")["yogunluk"]["deger"]
    y, _ = tarama.parametre_uygula(spec, "void_orani", "su", 40.0)
    kontrol("void %40 -> rho0*0.6",
            abs(sema.malzeme_bul(y, "su")["yogunluk"]["deger"] - rho0 * 0.6) < 1e-9)

    y, _ = tarama.parametre_uygula(spec, "zenginlik", "uo2", 4.5)
    z = [b.get("zenginlik") for b in sema.malzeme_bul(y, "uo2")["bilesim"]
         if b.get("zenginlik")]
    kontrol("zenginlik", z and abs(z[0] - 4.5) < 1e-9)

    y, _ = tarama.parametre_uygula(spec, "kafes_adim", "demet_17x17", 1.40)
    kontrol("kafes adimi", abs(sema.demet_bul(y, "demet_17x17")["adim"] - 1.40) < 1e-9)


def test_katsayi_uyumu():
    """Agirlikli dogrusal uyum bilinen bir egimi geri vermeli."""
    print("\n[3k] Katsayi uyumu (sentetik)")
    from cekirdek import tarama
    # rho(p) = -3.0 * p + 5000 pcm olacak sekilde k uret
    sonuclar = []
    for p in (0, 100, 200, 300, 400):
        rho = (5000.0 - 3.0 * p) / 1e5
        k = 1.0 / (1.0 - rho)
        sonuclar.append({"deger": float(p), "keff": k, "sapma": 1e-5})
    kats = tarama.katsayi(sonuclar)
    kontrol("egim -3.0 pcm/birim geri geldi",
            abs(kats["egim"] + 3.0) < 0.02, "olculen %.4f" % kats["egim"])
    kontrol("R2 ~ 1", kats["r2"] > 0.999)
    kontrol("tek nokta -> None", tarama.katsayi(sonuclar[:1]) is None)


def test_kritik_arama_kok_sarti():
    """Hedef aralik disindaysa arama EKSTRAPOLASYON YAPMAMALI."""
    print("\n[3l] Kritik arama kok sarti")
    from cekirdek import kritik_arama
    import tempfile as _t

    class SahteKosucu:
        """k(p) = 1.3 - 0.0001*p  -- gercek kosu yapmadan mantigi sinar."""
        @staticmethod
        def sahte(spec, tur, hedef, deger, dizin, is_parcacigi, taban):
            return 1.3 - 0.0001 * deger, 0.0005

    orj = kritik_arama._nokta_kos
    kritik_arama._nokta_kos = SahteKosucu.sahte
    try:
        spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
        # k(0)=1.3, k(1000)=1.2 -> hedef 1.0 aralikta DEGIL
        s = kritik_arama.ara(spec, "bor_ppm", "su", 0, 1000, _t.mkdtemp())
        kontrol("aralik disi -> reddetti", not s.basarili and "aralıkta değil" in s.mesaj)
        # k(0)=1.3, k(5000)=0.8 -> hedef 1.0 aralikta
        s = kritik_arama.ara(spec, "bor_ppm", "su", 0, 5000, _t.mkdtemp())
        kontrol("aralik icinde -> buldu", s.basarili, "cozum=%.1f" % (s.cozum or -1))
        kontrol("cozum dogru (beklenen 3000)", s.basarili and abs(s.cozum - 3000) < 60,
                "cozum=%.1f" % (s.cozum or -1))
    finally:
        kritik_arama._nokta_kos = orj


def test_kuresel_kor():
    """Kuresel kor kurulmali ve olculeri dogru olmali."""
    print("\n[3m] Kuresel kor turu")
    spec = sema.yukle(os.path.join(ORNEK, "godiva_kriter.json"))
    b = dogrula.tum_kontroller(spec)
    kontrol("godiva dogrulamadan geciyor", not dogrula.hata_var(b),
            "(%s)" % dogrula.ozet(b))
    _, bilgi = kurucu.kur(spec)
    gx, gy = bilgi["sinir_kutu"]
    kontrol("sinir kutusu = 2 x yaricap", abs(gx - 2 * 8.7407) < 1e-9,
            "%.4f cm" % gx)
    # ters siralı kabuk -> hata
    import copy as _c
    bozuk = _c.deepcopy(spec)
    bozuk["kor"]["kabuklar"] = [sema.kabuk(9.0, "heu"), sema.kabuk(5.0, "heu")]
    b = dogrula.tum_kontroller(bozuk)
    kontrol("ters kabuk sirasi yakalandi",
            any("artan sırada" in x.mesaj for x in b))


def test_veri_sicaklik_araligi():
    """Veri kutuphanesi sicaklik araliklari okunabilmeli."""
    print("\n[3n] Veri kutuphanesi sicaklik araliklari")
    from cekirdek import veri_bilgi
    a = veri_bilgi.nuklid_araligi("U235")
    kontrol("U235 araligi okundu", a is not None and a[0] > 0 and a[1] > a[0],
            str(a))
    s = veri_bilgi.sab_araligi("c_H_in_H2O")
    kontrol("c_H_in_H2O araligi okundu", s is not None, str(s))
    kontrol("su S(a,b) araligi notrondan DAR",
            s is not None and a is not None and s[1] < a[1],
            "S(a,b) ust sinir %s < notron %s" % (s[1] if s else "?", a[1] if a else "?"))


def test_keff_yorumu():
    """k-eff yorumu dogru kritiklik durumunu vermeli."""
    print("\n[3o] k-eff yorumu")
    from cekirdek.kosucu import keff_yorumu
    d, _ = keff_yorumu(1.05, 0.001)
    kontrol("k=1.05 -> kritik ustu", "Kritik üstü" in d)
    d, _ = keff_yorumu(0.95, 0.001)
    kontrol("k=0.95 -> kritik alti", "Kritik altı" in d)
    d, _ = keff_yorumu(1.0001, 0.001)
    kontrol("k=1.0001 -> kritik", d.startswith("Kritik ("))
    _, a = keff_yorumu(1.01, 0.0005, 0.0065)
    kontrol("dolar cinsinden verildi", "$" in a, a[:60])


HIZLI = [
    test_entropi_ayristirma, test_entropi_yakinsama, test_onbellek, test_reaktivite,
    test_parametre_uygula, test_katsayi_uyumu, test_kritik_arama_kok_sarti,
    test_kuresel_kor, test_veri_sicaklik_araligi, test_keff_yorumu,
]
YAVAS = []
