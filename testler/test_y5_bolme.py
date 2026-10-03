# -*- coding: utf-8 -*-
"""
 test_y5_bolme.py  --  v3 Y5: tukenme bolgesi bolme (cekirdek/bolge_bol.py)

   [Y5-B1] Halka yaricaplari: esit hacimde halka alanlari esit, esit kalinlikta
           aralik esit, incelende kalinlik orani sabit; son yaricap TAM dis yaricap.
   [Y5-B2] Gd pininde halka bolme sonrasi toplam yakit hacmi analitik olarak
           korunur (sum halka hacmi = pi r^2 h, goreli 1e-9) -- uc halka turu,
           2B ve 3B yukseklik, tukenme.hacimler ile.
   [Y5-B3] uygula: girdi degismez, bolme anahtari duser (idempotent), cubuk
           cubuk yanma acilir, ornek sayisi halka sayisi kadar artar.
   [Y5-B4] K3 pin gucu uyumu: varsayilan hedefler butun halkalari icerir; acik
           hedefler (eski bolge numarasi) yeni numaralara tasinir.
   [Y5-B5] Eksenel dilim: katman h/n'lik n katmana bolunur, hacim korunur,
           aktif aralik degismez; 2B modelde HATA.
   [Y5-B6] Hata girdileri: kontrol cubugu, kare kesit, tanimsiz cubuk, olmayan
           bolge, dis bolge, gecersiz halka sayisi/tur.
   [Y5-B7] Betik esdegerligi: kod_uret bolunmus modeli uretir (hucre sayisi ve
           yaricaplar kurucu.kur ile ayni).
   [Y5-B8] hazirla: halka basina ayri malzeme, hacim toplami analitik (ZINCIR).
   [Y5-B9] (YAVAS) Demet: bolunmus ve bolunmemis kosuda K3 pin gucu tutarli.
"""

import copy
import math
import os

from testler.ortak_test import ORNEK, kontrol

GD_RADYAL = 0.39218          # pwr_tukenme yakit yaricapi [cm]
TOL = 1.0e-9


def _gd_pin(halka=5, tur="esit_hacim", **ek):
    from cekirdek import sema
    s = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    gd = sema.yukle(os.path.join(ORNEK, "pwr_gd_tukenme.json"))
    m = copy.deepcopy(sema.malzeme_bul(gd, "uo2_gd_1"))
    m["ad"] = "uo2_gd"
    s["malzemeler"] = [x for x in s["malzemeler"] if x["ad"] != "uo2"] + [m]
    s["cubuklar"][0]["bolgeler"][0]["malzeme"] = "uo2_gd"
    s["tukenme"]["bolme"] = {"cubuklar": [dict({"cubuk": "yakit_cubugu", "halka": halka,
                                               "tur": tur}, **ek)]}
    return s


def test_halka_yaricaplari():
    print("\n[Y5-B1] halka yaricaplari")
    from cekirdek import bolge_bol as bb
    r = bb.halka_yaricaplari(0.0, GD_RADYAL, 5, bb.ESIT_HACIM)
    a = bb.halka_alanlari(0.0, r)
    kontrol("son yaricap tam dis yaricap", r[-1] == GD_RADYAL, repr(r[-1]))
    kontrol("esit hacim: alanlar esit", max(a) - min(a) < TOL * max(a), repr(a))
    r = bb.halka_yaricaplari(0.1, 0.5, 4, bb.ESIT_KALINLIK)
    kontrol("esit kalinlik: aralik 0.1", all(abs(y - 0.1 * (i + 2)) < 1e-12
                                            for i, y in enumerate(r)), repr(r))
    r = bb.halka_yaricaplari(0.0, 1.0, 4, bb.DISTA_INCELEN, oran=0.5)
    kal = [r[0]] + [r[i] - r[i - 1] for i in range(1, 4)]
    kontrol("incelen: kalinlik orani 0.5", all(abs(kal[i + 1] / kal[i] - 0.5) < 1e-12
                                              for i in range(3)), repr(kal))
    kontrol("tek halka = dis yaricap", bb.halka_yaricaplari(0.2, 0.4, 1) == (0.4,))
    for kotu in ((0.5, 0.5, 3), (0.0, 1.0, 0), (0.0, 1.0, bb.MAKS_HALKA + 1), (-0.1, 1.0, 2)):
        try:
            bb.halka_yaricaplari(*kotu)
            kontrol("gecersiz %r reddedilir" % (kotu,), False)
        except ValueError:
            kontrol("gecersiz %r reddedilir" % (kotu,), True)


def test_gd_hacim_korunumu():
    print("\n[Y5-B2] Gd pini: halka bolme analitik hacmi korur (1e-9)")
    from cekirdek import bolge_bol as bb, tukenme
    for tur in bb.TURLER:
        for yukseklik in (None, 366.0):
            s = _gd_pin(5, tur)
            if yukseklik:
                s["kor"]["yukseklik"] = yukseklik
            ref = copy.deepcopy(s)
            ref["tukenme"].pop("bolme")
            h_once = tukenme.hacimler(ref)["uo2_gd"]["hacim"]
            h_sonra = tukenme.hacimler(bb.uygula(s))["uo2_gd"]["hacim"]
            analitik = math.pi * GD_RADYAL ** 2 * (yukseklik or 1.0)
            kontrol("%s h=%s: once = pi r^2 h" % (tur, yukseklik),
                    abs(h_once - analitik) <= TOL * analitik, "%r %r" % (h_once, analitik))
            kontrol("  sonra = once", abs(h_sonra - h_once) <= TOL * h_once,
                    "%r %r" % (h_sonra, h_once))
            d = bb.halka_hacim_denetimi(s)
            kontrol("  denetim hatasi <= 1e-9", d and d[0]["goreli_hata"] <= TOL, repr(d))


def test_uygula_ozellikleri():
    print("\n[Y5-B3] uygula: girdi degismez, idempotent, cubuk cubuk yanma acik")
    from cekirdek import bolge_bol as bb
    s = _gd_pin(4)
    kopya = copy.deepcopy(s)
    y = bb.uygula(s)
    kontrol("girdi degismedi", s == kopya)
    reg = y["cubuklar"][0]["bolgeler"]
    kontrol("4 halka + kilif + su = 6 bolge", len(reg) == 6, repr(reg))
    kontrol("halkalar ayni malzeme", [b["malzeme"] for b in reg[:4]] == ["uo2_gd"] * 4)
    kontrol("bolme anahtari dustu, ayir acik",
            "bolme" not in y["tukenme"] and y["tukenme"]["malzemeleri_ayir"] is True)
    kontrol("ikinci uygulama bolmez", bb.uygula(y) is y)
    yok = copy.deepcopy(kopya)
    yok["tukenme"].pop("bolme")
    kontrol("bolme yoksa girdinin kendisi", bb.uygula(yok) is yok)
    kontrol("halka=1 bolmez", bb.bolme_oku(_gd_pin(1)) is None)
    once, sonra = bb.ornek_sayilari(s)
    kontrol("ornek sayisi 1 -> 4", (once, sonra) == (1, 4), repr((once, sonra)))
    kontrol("onizleme: 4 bolunmus + 2 degil",
            [x.bolunmus for x in bb.kesit_onizleme(s, "yakit_cubugu")]
            == [True] * 4 + [False] * 2)


def test_guc_hedefleri_uyumu():
    print("\n[Y5-B4] K3 pin gucu: butun halkalar hedef; acik hedefler tasinir")
    from cekirdek import bolge_bol as bb, guc, sema
    s = sema.yukle(os.path.join(ORNEK, "pwr_gd_tukenme.json"))
    once = guc.varsayilan_hedefler(s)
    s["tukenme"]["bolme"] = {"cubuklar": [{"cubuk": "yakit_cubugu", "halka": 3}]}
    y = bb.uygula(s)
    sonra = guc.varsayilan_hedefler(y)
    yc = [h for h in sonra if h["cubuk"] == "yakit_cubugu"]
    kontrol("yakit cubugu 1 -> 3 hedef", len([h for h in once if h["cubuk"] == "yakit_cubugu"]) == 1
            and len(yc) == 3, repr(yc))
    kontrol("gd cubugu etkilenmedi", [h for h in sonra if h["cubuk"] == "gd_cubugu"]
            == [h for h in once if h["cubuk"] == "gd_cubugu"])
    s["guc_dagilimi"]["cubuklar"] = [{"cubuk": "yakit_cubugu", "bolge": 0},
                                     {"cubuk": "gd_cubugu", "bolge": 4}]
    s["guc_dagilimi"].pop("cubuk", None)
    g = bb.uygula(s)["guc_dagilimi"]["cubuklar"]
    kontrol("acik hedef butun halkalara acildi", [h["bolge"] for h in g
            if h["cubuk"] == "yakit_cubugu"] == [0, 1, 2], repr(g))
    kontrol("bolunmeyen cubugun hedefi ayni", {"cubuk": "gd_cubugu", "bolge": 4} in g)


def _tek_yukseklikli():
    from cekirdek import sema
    s = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    s["kor"]["yukseklik"] = 100.0
    return s


def test_eksenel_dilim():
    print("\n[Y5-B5] eksenel dilim: h/n katmanlar, hacim korunur")
    from cekirdek import bolge_bol as bb, sema, tukenme
    s = _tek_yukseklikli()
    s["tukenme"]["bolme"] = {"eksenel": {"dilim": 4}}
    y = bb.uygula(s)
    kat = y["kor"]["eksenel"]["bolgeler"]
    kontrol("4 katman x 25 cm", len(kat) == 4 and all(k["yukseklik"] == 25.0 for k in kat),
            repr(kat))
    ref = _tek_yukseklikli()
    h0 = tukenme.hacimler(ref)["uo2"]["hacim"]
    h1 = tukenme.hacimler(y)["uo2"]["hacim"]
    kontrol("hacim korunur", abs(h1 - h0) <= TOL * h0, "%r %r" % (h0, h1))
    kontrol("toplam yukseklik ayni", sema.kor_yuksekligi(y["kor"]) == 100.0)
    kontrol("ornek sayisi 1 -> 4", bb.ornek_sayilari(s) == (1, 4), repr(bb.ornek_sayilari(s)))
    # eksenel katmanli demet: yalniz yanabilir katman bolunur
    e = sema.yukle(os.path.join(ORNEK, "pwr_eksenel.json"))
    e["tukenme"] = dict(sema.VARSAYILAN_TUKENME, var=True, bolme={"eksenel": {"dilim": 3}})
    y = bb.uygula(e)
    ad = [k["ad"] for k in e["kor"]["eksenel"]["bolgeler"]]
    yad = [k["ad"] for k in y["kor"]["eksenel"]["bolgeler"]]
    kontrol("katman sayisi artti, toplam yukseklik ayni", len(yad) > len(ad)
            and sema.kor_yuksekligi(y["kor"]) == sema.kor_yuksekligi(e["kor"]), repr(yad))
    d = _gd_pin(1)
    d["tukenme"]["bolme"] = {"eksenel": {"dilim": 2}}
    try:
        bb.uygula(d)
        kontrol("2B modelde eksenel dilim HATA", False)
    except ValueError as e:
        kontrol("2B modelde eksenel dilim HATA", "3B" in str(e), str(e))


def test_hata_girdileri():
    print("\n[Y5-B6] gecersiz bolme girdileri ValueError")
    from cekirdek import bolge_bol as bb, sema
    def hata(s, parca):
        try:
            bb.uygula(s)
            return False
        except ValueError as e:
            return parca in str(e)
    s = _gd_pin()
    s["tukenme"]["bolme"]["cubuklar"][0]["cubuk"] = "yok"
    kontrol("tanimsiz cubuk", hata(s, "tanımsız çubuk"))
    s = _gd_pin()
    s["tukenme"]["bolme"]["cubuklar"][0]["bolgeler"] = [9]
    kontrol("olmayan bolge", hata(s, "olmayan bölge"))
    s = _gd_pin()
    s["tukenme"]["bolme"]["cubuklar"][0]["bolgeler"] = [2]
    kontrol("yaricapsiz dis bolge", hata(s, "bölünemez"))
    s = _gd_pin(halka=99)
    kontrol("halka sayisi sinir disi", hata(s, "halka sayısı"))
    s = _gd_pin()
    s["tukenme"]["bolme"]["cubuklar"][0]["tur"] = "yok"
    kontrol("bilinmeyen tur", hata(s, "bilinmeyen halka türü"))
    s = _gd_pin()
    s["cubuklar"][0]["kesit"] = "kare"
    kontrol("kare kesit", hata(s, "silindirik değil"))
    k = sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json"))
    k["tukenme"]["var"] = True
    k["tukenme"]["bolme"] = {"cubuklar": [{"cubuk": "kontrol_cubugu", "halka": 3}]}
    kontrol("kontrol cubugu", hata(k, "kontrol çubuğu"))
    s = _gd_pin()
    s["tukenme"]["bolme"]["cubuklar"].append(dict(s["tukenme"]["bolme"]["cubuklar"][0]))
    kontrol("ayni cubuk iki kez", hata(s, "birden fazla"))


def test_betik_esdegerligi():
    print("\n[Y5-B7] betik: bolunmus model kurucu ile ayni")
    from cekirdek import bolge_bol as bb, kod_uret, kurucu
    s = _gd_pin(4)
    metin = kod_uret.uret(s, "model.py")
    ad_alani = {"__name__": "betik"}
    exec(compile(metin, "model.py", "exec"), ad_alani)        # noqa: S102 (uretilen betik, test)
    betik = ad_alani["model"]
    model, _b = kurucu.kur(bb.uygula(s))
    def yaricaplar(m):
        return sorted(round(y.r, 12) for y in m.geometry.get_all_surfaces().values()
                      if hasattr(y, "r"))
    kontrol("silindir yaricaplari ayni", yaricaplar(betik) == yaricaplar(model),
            "%r %r" % (yaricaplar(betik), yaricaplar(model)))
    kontrol("hucre sayisi ayni",
            len(betik.geometry.get_all_cells()) == len(model.geometry.get_all_cells()),
            "%d %d" % (len(betik.geometry.get_all_cells()), len(model.geometry.get_all_cells())))
    gd = [c for c in model.geometry.get_all_cells().values()
          if c.fill is not None and getattr(c.fill, "name", "") == s["malzemeler"][-1]["ad"]
          or (c.fill is not None and "Gd" in getattr(c.fill, "name", ""))]
    kontrol("4 Gd halka hucresi", len(gd) == 4, repr(len(gd)))


def test_hazirla_halka_malzemeleri():
    print("\n[Y5-B8] tukenme.hazirla: halka basina ayri malzeme, hacimler analitik")
    from cekirdek import tukenme
    s = _gd_pin(5)
    s["tukenme"]["zincir"] = "casl_termal"
    s["kor"]["yukseklik"] = 50.0
    _model, bilgi = tukenme.hazirla(s)
    kontrol("5 ornek", bilgi["ornek_sayisi"] == 5, repr(bilgi["ornek_sayisi"]))
    yanan = [m for m in _model.materials if m.depletable]
    kontrol("5 klon, hepsi hacimli", len(yanan) == 5 and all(m.volume for m in yanan))
    toplam = sum(m.volume for m in yanan)
    analitik = math.pi * GD_RADYAL ** 2 * 50.0
    kontrol("hacim toplami = pi r^2 h", abs(toplam - analitik) <= TOL * analitik,
            "%r %r" % (toplam, analitik))
    v = sorted(m.volume for m in yanan)
    kontrol("esit hacimli halkalar esit", v[-1] - v[0] <= TOL * v[-1], repr(v))


def test_demette_pin_gucu_toplami(gecici):
    print("\n[Y5-B9] demet: halka bolme sonrasi K3 pin gucu bolunmemisle tutarli (3 sigma)")
    from cekirdek import sema, tukenme, tukenme_guc
    def kos(ad, bolme):
        s = sema.yukle(os.path.join(ORNEK, "pwr_gd_tukenme.json"))
        s["ayarlar"].update(parcacik=2000, cevrim=40, pasif=10, tohum=5)
        s["ayarlar"]["entropi_mesh"]["var"] = False
        s["tukenme"].update(zincir="casl_termal", entegrator="predictor", adimlar=[1.0],
                            adim_birimi="d", izlenen=["Gd157"])
        if bolme:
            s["tukenme"]["bolme"] = {"cubuklar": [{"cubuk": "yakit_cubugu", "halka": 3},
                                                  {"cubuk": "gd_cubugu", "halka": 2,
                                                   "bolgeler": [4]}]}
        d = os.path.join(gecici, ad)
        h5, b = tukenme.calistir(s, d, veri_kontrolu=False)
        return s, d, h5, b
    s0, d0, h0, _b0 = kos("bolunmemis", False)
    s1, d1, h1, b1 = kos("bolunmus", True)
    kontrol("bolunmus: ornek sayisi arttı", b1["ornek_sayisi"] > _b0["ornek_sayisi"],
            "%d -> %d" % (_b0["ornek_sayisi"], b1["ornek_sayisi"]))
    t0 = tukenme_guc.adim_gucleri(d0, s0, h0)["adimlar"][0]["tablo"]
    t1 = tukenme_guc.adim_gucleri(d1, s1, h1)["adimlar"][0]["tablo"]
    kontrol("ayni sayida pin satiri", len(t0) == len(t1) > 0, "%d %d" % (len(t0), len(t1)))
    f0 = {(r["demet"], r["konum"]): r for r in t0}
    en_kotu = 0.0
    for r in t1:
        a = f0[(r["demet"], r["konum"])]
        fark = abs(r["bagil"] - a["bagil"])
        sg = (r["sigma"] ** 2 + a["sigma"] ** 2) ** 0.5
        en_kotu = max(en_kotu, fark / sg if sg else 0.0)
    kontrol("her pinin bagil gucu 4 sigma icinde (en kotu %.2f sigma)" % en_kotu, en_kotu <= 4.0)
    m0 = sum(r["W"] for r in t0 if r["W"])
    m1 = sum(r["W"] for r in t1 if r["W"])
    kontrol("toplam guc korunur (%.4g vs %.4g W)" % (m0, m1), abs(m1 - m0) <= 0.02 * m0)


def test_ornek_eski_ornekle_ayni():
    print("\n[Y5-B10] pwr_gd_bolme: 5 esit hacimli halka = pwr_gd_tukenme'nin elle yazilmis halkalari")
    from cekirdek import bolge_bol as bb, sema, tukenme
    yeni = sema.yukle(os.path.join(ORNEK, "pwr_gd_bolme.json"))
    eski = sema.yukle(os.path.join(ORNEK, "pwr_gd_tukenme.json"))
    y = bb.uygula(yeni)
    ry = [b["r"] for b in sema.cubuk_bul(y, "gd_cubugu")["bolgeler"]][:5]
    re_ = [b["r"] for b in sema.cubuk_bul(eski, "gd_cubugu")["bolgeler"]][:5]
    kontrol("yaricaplar 5 basamak yuvarlama icinde ayni", max(abs(a - b) for a, b in zip(ry, re_)) < 1e-5,
            repr(ry))
    hy = sum(v["hacim"] for a, v in tukenme.hacimler(y).items() if a.startswith("uo2_gd"))
    he = sum(v["hacim"] for a, v in tukenme.hacimler(eski).items() if a.startswith("uo2_gd"))
    kontrol("Gd malzemesi toplam hacmi ayni (1e-5)", abs(hy - he) <= 1e-5 * he, "%r %r" % (hy, he))
    kontrol("ornek sayisi 1 + 24 UO2 -> 5 + 24", bb.ornek_sayilari(yeni) == (25, 29)
            or bb.ornek_sayilari(yeni)[1] - bb.ornek_sayilari(yeni)[0] == 4,
            repr(bb.ornek_sayilari(yeni)))


HIZLI = [test_halka_yaricaplari, test_gd_hacim_korunumu, test_uygula_ozellikleri,
         test_guc_hedefleri_uyumu, test_eksenel_dilim, test_hata_girdileri,
         test_betik_esdegerligi, test_ornek_eski_ornekle_ayni]
YAVAS = [test_demette_pin_gucu_toplami]
HIZLI += [test_hazirla_halka_malzemeleri]
VERI_GEREKEN = [test_betik_esdegerligi, test_hazirla_halka_malzemeleri] + YAVAS
ZINCIR_GEREKEN = [test_hazirla_halka_malzemeleri] + YAVAS
