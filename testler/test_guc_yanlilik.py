# -*- coding: utf-8 -*-
"""
test_guc_yanlilik.py -- guc tepe faktorleri: maksimum yanliligi, F_q paydasi,
kesik cubuk gucu, PWR esiklerinin kapsami (profesor denetimi, Dalga 4).

  [GY1] F_q ortalamasi yalniz yakitli (cubuk, dilim) ciftleri: kisa boy cubugun
        "cubuk yok" sifirlari paydaya girmez (eskiden F_q sisiyordu).
  [GY2] Maksimumun yanliligi tepeye yakin cubuklar uzerinden: simetrik 8 sicak
        cubuk -> yakin = 8, yanlilik > 0; tek belirgin tepe -> yanlilik 0.
        F_q icin dilim duzeyinde ayni alanlar.
  [GY3] Cok tohum: once harita ortalamasi, sonra maksimum (tohum maksimumlarinin
        ortalamasi yukari yanli).
  [GY4] mutlak_guc: kesik cubuklarin gucu kesik olmayanlara dagitilmaz.
  [GY5] Yorum: tipik PWR sinirlari yalniz PWR/VVER kategorisinde; ozet satirinda
        "tek kosu σ'si iyimser" notu; yanlilik uyarisi tepe sayisini yazar.

Monte Carlo KOSULMAZ (sentetik dagilim sozlukleri).
"""

from testler.ortak_test import kontrol


def _dagilim(konumlar, dilim=1, kesik=()):
    return {"konumlar": konumlar, "eksenel_dilim": dilim, "tam_kor": False,
            "kafes_turu": "kare", "kesik_cubuklar": list(kesik)}


def _konum(eksenel, sigma=0.001):
    toplam = sum(eksenel)
    return {"eksenel": [(d, sigma if d > 0 else 0.0) for d in eksenel],
            "toplam": (toplam, sigma * len(eksenel) ** 0.5)}


def test_fq_yalniz_yakitli_ciftler():
    print("\n[GY1] F_q paydasi: kisa boy cubugun sifirlari girmez")
    from cekirdek import guc
    tam = [1.0, 2.0, 2.0, 1.0]
    kisa = [1.0, 2.0, 0.0, 0.0]          # ust yarida cubuk yok
    d = _dagilim({(0, 0): _konum(tam), (1, 0): _konum(tam), (0, 1): _konum(tam),
                  (1, 1): _konum(kisa)}, dilim=4)
    f = guc.tepe_faktorleri(d)
    beklenen = 2.0 / (21.0 / 14.0)      # 14 yakitli cift; eski kod 16'ya bolerdi
    kontrol("F_q = 2 / (21/14) = 1.3333", abs(f["F_q"] - beklenen) < 1e-9,
            "-> %.4f (eski hata: %.4f)" % (f["F_q"], 2.0 / (21.0 / 16.0)))


def test_tepe_yakini_yanlilik():
    print("\n[GY2] Maksimumun yanliligi: tepeye yakin cubuklar")
    from cekirdek import guc
    from cekirdek.guc_faktor import beklenen_maks
    konumlar = {(i, 0): _konum([1.10], 0.01) for i in range(8)}
    konumlar.update({(i, 1): _konum([0.90], 0.01) for i in range(8)})
    f = guc.tepe_faktorleri(_dagilim(konumlar))
    kontrol("simetrik 8 sicak cubuk -> tepe_yakini = 8", f["F_dH_tepe_yakini"] == 8,
            "-> %r" % f.get("F_dH_tepe_yakini"))
    sigma_bagil = 0.01 / 1.0             # ortalama = 1.0
    kontrol("yanlilik = σ_tepe × beklenen_maks(8)",
            abs(f["F_dH_yanlilik"] - sigma_bagil * beklenen_maks(8)) < 1e-9,
            "-> %r" % f.get("F_dH_yanlilik"))
    kontrol("beklenen_maks: 1 -> 0, artan", beklenen_maks(1) == 0.0
            and 0 < beklenen_maks(2) < beklenen_maks(8) < beklenen_maks(50))
    tek = {(0, 0): _konum([1.5], 0.001)}
    tek.update({(i, 1): _konum([1.0], 0.001) for i in range(9)})
    f1 = guc.tepe_faktorleri(_dagilim(tek))
    kontrol("tek belirgin tepe -> yakin 1, yanlilik 0", f1["F_dH_tepe_yakini"] == 1
            and f1["F_dH_yanlilik"] == 0.0)
    d3 = {(i, 0): _konum([1.0, 1.2, 1.0], 0.01) for i in range(4)}
    f3 = guc.tepe_faktorleri(_dagilim(d3, dilim=3))
    kontrol("F_q dilim duzeyi: 4 esit tepe dilimi -> yakin 4, yanlilik > 0",
            f3["F_q_tepe_yakini"] == 4 and f3["F_q_yanlilik"] > 0,
            "-> %r / %r" % (f3.get("F_q_tepe_yakini"), f3.get("F_q_yanlilik")))


def test_coklu_tohum_harita_ortalamasi():
    print("\n[GY3] Cok tohum: once harita ortalamasi, sonra maksimum")
    from cekirdek import guc_yorum
    tohumlar = [{"a": 1.10, "b": 1.00, "c": 0.90}, {"a": 1.00, "b": 1.10, "c": 0.90},
                {"a": 1.05, "b": 1.05, "c": 0.90}]
    kayitlar = [{"F_dH": max(t.values()), "F_q": None,
                 "bagil": {k: (v, 0.001) for k, v in t.items()}} for t in tohumlar]
    h = guc_yorum.harita_faktorleri(kayitlar)
    maks_ort = sum(max(t.values()) for t in tohumlar) / 3
    kontrol("F_dH_harita = 1.05 (ortalama haritanin tepesi)",
            abs(h["F_dH_harita"] - 1.05) < 1e-12, "-> %r" % h)
    kontrol("tohum maksimumlarinin ortalamasi (%.4f) daha buyuk (yanli)" % maks_ort,
            h["F_dH_harita"] < maks_ort)
    kontrol("tepe σ'si tohum sacilmasi / √N", h["F_dH_harita_sapma"] > 0)
    kontrol("F_q haritasi yok (2B)", "F_q_harita" not in h)


def test_mutlak_guc_kesik():
    print("\n[GY4] mutlak_guc: kesik cubugun gucu dagitilmaz")
    from cekirdek import guc
    konumlar = {(i, 0): _konum([1.0]) for i in range(4)}
    f = guc.tepe_faktorleri(_dagilim(konumlar, kesik=[(3, 0)]))
    kontrol("3 cubuk (1 kesik)", f["cubuk_sayisi"] == 3)
    m = guc.mutlak_guc(f, 400.0, hedef_payi=1.0)
    kontrol("cubuk ortalamasi 100 W (eski: 133.3)", abs(m["cubuk_ortalama_W"] - 100.0) < 1e-9,
            "-> %.2f" % m["cubuk_ortalama_W"])
    y = " ".join(guc.yorumla(f, m))
    kontrol("yorumda kesik payi notu", "Kesik çubukların gücü" in y)


def test_yorum_kategori_ve_iyimser_not():
    print("\n[GY5] Yorum: PWR esikleri kategoriye bagli; ozette iyimser σ notu")
    from cekirdek import guc
    konumlar = {(i, 0): _konum([1.0 + 0.1 * i]) for i in range(5)}
    f = dict(guc.tepe_faktorleri(_dagilim(konumlar)), F_dH=1.8, F_q=2.9, F_q_sapma=0.01,
             eksenel_dilim=20)
    m = {"cubuk_ortalama_W": 100.0, "cubuk_maks_W": 180.0, "hedef_payi": None,
         "lineer_maks_W_cm": 600.0, "lineer_tepe_kaynagi": "F_q"}
    pwr = " ".join(guc.yorumla(f, m, kategori="pwr"))
    sfr = " ".join(guc.yorumla(f, m, kategori="sfr"))
    for parca in ("1.65", "2.3–2.6", "400–500"):
        kontrol("PWR: '%s' var" % parca, parca in pwr)
        kontrol("SFR: '%s' yok" % parca, parca not in sfr)
    kontrol("kategori yok -> PWR esigi yok", "1.65" not in " ".join(guc.yorumla(f, m)))
    kontrol("ozet: iyimser σ notu", "iyimser" in guc.ozet_metni(f))
    sim = {(i, 0): _konum([1.1], 0.01) for i in range(8)}
    sim.update({(i, 1): _konum([0.9], 0.01) for i in range(8)})
    y = " ".join(guc.yorumla(guc.tepe_faktorleri(_dagilim(sim))))
    kontrol("yanlilik uyarisi tepe sayisini yazar", "8 çubuk" in y and "yukarı" in y, y[:300])


HIZLI = [test_fq_yalniz_yakitli_ciftler, test_tepe_yakini_yanlilik,
         test_coklu_tohum_harita_ortalamasi, test_mutlak_guc_kesik,
         test_yorum_kategori_ve_iyimser_not]
YAVAS = []
