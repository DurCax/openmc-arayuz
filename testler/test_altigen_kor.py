# -*- coding: utf-8 -*-
"""
 test_altigen_kor.py  --  Dalga 1 / Ajan 1: altigen tam kor (altigen_kafes)

 Kapsam
   * sema / uygunluk kurallari (kor turu, parca turleri, sinirlar, sekmeler)
   * dogrulama: kare demet, halka uzunlugu, adim < demet olcusu, yonelim,
     kilif (duct) olculeri
   * kurulan geometri: demet merkezleri, kilif, sinir yuzeyleri analitik
     degerlerle; yonelim NOKTA-HUCRE testleriyle olculur (Geometry.find,
     openmc.lib gerekmez)
   * tukenme sayimi, tur degisimi, baslangic karti, Kor sekmesi haritasi
   * YAVAS: 7 demet (reflective) = tek demet sonsuz kafes (2 sigma),
     betik esdegerligi, stokastik hacim, Model.plot

 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri).
"""

import copy
import importlib.util
import math
import os
import warnings

from testler.ortak_test import kontrol, ISLEM_PARCACIGI

warnings.filterwarnings("ignore")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Test demeti: 3 halkali (19 pin) altigen demet, VVER benzeri su/UO2.
PIN_ADIM = 1.275
PIN_HALKA = 3
R_YAKIT, R_ZARF = 0.3860, 0.4550
SQ3 = math.sqrt(3.0)
# Kilifsiz demetin kendi altigen zarfi (duz yuzden duz yuze):
# (halka-1) * adim * sqrt(3) + adim
ZARF = (PIN_HALKA - 1) * PIN_ADIM * SQ3 + PIN_ADIM
KILIF_IC, KILIF_KAL, KILIF_BOSLUK = ZARF + 0.10, 0.15, 0.20


# ============================================================================
# model kurucular
# ============================================================================

def _malzemeler(sema):
    return [
        sema.malzeme("uo2", [sema.bilesen("U", 1.0, zenginlik=4.0),
                             sema.bilesen("O", 2.0)], 10.4, renk=(200, 60, 60)),
        sema.malzeme("zr", [sema.bilesen("Zr", 1.0)], 6.55, renk=(150, 150, 150)),
        sema.malzeme("su", [sema.bilesen("H", 2.0), sema.bilesen("O", 1.0)], 0.72,
                     sab=["c_H_in_H2O"], renk=(90, 140, 230)),
        sema.malzeme("celik", [sema.bilesen("Fe", 1.0)], 7.9, renk=(90, 90, 90)),
    ]


def _demet(sema, ad="hex", kilif=False, yonelim="y"):
    from cekirdek import altigen
    d = sema.demet_altigen(ad, PIN_ADIM, PIN_HALKA, altigen.bos_harita(PIN_HALKA, "y"),
                           {"y": "yakit_cubugu"}, "su", yonelim=yonelim)
    if kilif:
        d["kilif"] = {"ic_duz": KILIF_IC, "kalinlik": KILIF_KAL, "malzeme": "celik"}
    return d


def _tek_demet_spec(kilif=False):
    from cekirdek import sema
    s = sema.yeni_spec("tek altigen demet")
    s["malzemeler"] = _malzemeler(sema)
    s["cubuklar"] = [sema.cubuk("yakit_cubugu", [sema.bolge(R_YAKIT, "uo2"),
                                                 sema.bolge(R_ZARF, "zr"),
                                                 sema.bolge(None, "su")])]
    s["demetler"] = [_demet(sema, kilif=kilif)]
    s["kor"].update(tur="tek_demet", demet="hex")
    s["kor"]["sinir"] = {"yan": "reflective", "alt": "reflective", "ust": "reflective"}
    return s


def _kor_spec(kilif=False, yansitici=False, halka=2, adim=None, yonelim="x"):
    """7 (halka=2) ayni demetli altigen tam kor; varsayilan adim demet zarfi."""
    from cekirdek import altigen, sema
    s = _tek_demet_spec(kilif)
    dis = (KILIF_IC + 2 * KILIF_KAL) if kilif else ZARF
    s["kor"].update(tur="altigen_kafes", demet=None,
                    adim=adim or (dis + (KILIF_BOSLUK if kilif else 0.0)),
                    halka_sayisi=halka, yonelim=yonelim,
                    harita=altigen.bos_harita(halka, "A"), anahtar={"A": "hex"})
    s["kor"]["yansitici"] = {"var": yansitici, "kalinlik": 5.0, "malzeme": "su"}
    s["kor"]["sinir"]["yan"] = "vacuum" if yansitici else "reflective"
    sema.kor_alanlarini_ayikla(s["kor"])
    return s


def _hatalar(spec):
    from cekirdek import dogrula
    return [b.mesaj for b in dogrula.tum_kontroller(spec, veri_kontrolu=False)
            if b.seviye == "hata"]


def _yol(model, nokta):
    """Geometry.find: kokten yapraga hucre/universe yolu (pure Python)."""
    return model.geometry.find((nokta[0], nokta[1], 0.0))


def _yaprak_malzeme(model, nokta):
    yol = _yol(model, nokta)
    if not yol:
        return None
    hucre = yol[-1]
    return getattr(hucre.fill, "name", None) if hucre.fill is not None else "void"


def _kok_hucresi(model, nokta):
    """Yolun ilk HUCRESI (yol kok universe ile baslar)."""
    import openmc
    return next((x for x in _yol(model, nokta) if isinstance(x, openmc.Cell)), None)


# ============================================================================
# 1. sema ve kurallar
# ============================================================================

def test_altigen_kor_sema_ve_kurallar():
    print("\n[AK1] ALTIGEN KOR: sema ve uygunluk kurallari")
    from cekirdek import sema, uygunluk
    kontrol("KOR_TUR_ALANLARI altigen_kafes",
            sema.KOR_TUR_ALANLARI.get("altigen_kafes")
            == ("adim", "halka_sayisi", "harita", "anahtar", "yonelim", "yansitici"))
    kontrol("yeni modelde secilebilir tur", "altigen_kafes" in uygunluk.KOR_TURLERI)
    kontrol("gorunen ad", uygunluk.KOR_TURU_ADLARI.get("altigen_kafes")
            == "Tam kor (altıgen harita)")
    kontrol("eksenel katmanlama destekli", "altigen_kafes" in sema.EKSENEL_DESTEKLI)
    s = _kor_spec()
    p = uygunluk.parca_turleri(s)
    kontrol("altigen korda yalniz altigen demet sunulur",
            p["demet_altigen"] and not p["demet_kare"], "-> %s" % p)
    kontrol("cubuk eklenebilir", p["cubuk"])
    kontrol("yan yuzey altigen", uygunluk.yan_yuzey(s) == "altigen")
    kontrol("yan sinir secenekleri: periodic YOK (kirik cizgi sinir)",
            uygunluk.sinir_secenekleri(s, "yan") == ["reflective", "vacuum", "white"],
            "-> %s" % uygunluk.sinir_secenekleri(s, "yan"))
    sek = uygunluk.gecerli_sekmeler(s)
    kontrol("sekmeler: parcalar, demet, kor, analiz, tukenme",
            all(k in sek for k in ("parcalar", "demet", "kor", "analiz", "tukenme")),
            "-> %s" % sek)
    kontrol("guc hedefi: kafesteki yakit cubugu",
            uygunluk.guc_cubuklari(s) == ["yakit_cubugu"])
    kontrol("tukenme uygun", uygunluk.tukenme_uygun(s)[0])
    kontrol("katman dolgusu yalniz malzeme",
            uygunluk.katman_dolgu_turleri(s) == ("malzeme",))
    kontrol("kor_adim taramasi sunulur", uygunluk.gecerli_hedefler(s, "kor_adim") == [None])
    kontrol("geometri icerigi: demet + cubuk", uygunluk.geometri_icerigi(s)["demet"] == {"hex"})
    ks = _kor_spec(kilif=True, yansitici=True)
    icerik = uygunluk.geometri_icerigi(ks)["malzeme"]
    kontrol("kilif ve yansitici malzemeleri geometride", {"celik", "su"} <= icerik,
            "-> %s" % sorted(icerik))
    kontrol("sema.kullanilan_malzemeler kilifi sayar",
            "celik" in sema.kullanilan_malzemeler(ks))
    # malzeme adi degisimi kilifi da gunceller
    yollar = sema.malzeme_adini_degistir(ks, "celik", "celik2")
    kontrol("kilif malzemesi yeniden adlandirildi",
            ks["demetler"][0]["kilif"]["malzeme"] == "celik2"
            and "demetler/hex/kilif" in yollar, "-> %s" % yollar)


# ============================================================================
# 2. dogrulama
# ============================================================================

def test_altigen_kor_dogrulama():
    print("\n[AK2] ALTIGEN KOR: dogrulama")
    from cekirdek import sema
    kontrol("gecerli 7 demetli kor: 0 hata", not _hatalar(_kor_spec()), _hatalar(_kor_spec()))
    kontrol("kilifli + yansiticili kor: 0 hata",
            not _hatalar(_kor_spec(kilif=True, yansitici=True)),
            _hatalar(_kor_spec(kilif=True, yansitici=True)))

    def hata_var(degistir, parca):
        s = _kor_spec(kilif=True)
        degistir(s)
        h = _hatalar(s)
        return any(parca in m for m in h), h

    def kare_demet(s):
        s["demetler"].append(sema.demet("kare", 1.26, [2, 2], ["yy", "yy"],
                                        {"y": "yakit_cubugu"}, "su"))
        s["kor"]["anahtar"]["K"] = "kare"
        s["kor"]["harita"][0] = "K" + s["kor"]["harita"][0][1:]
    ok, h = hata_var(kare_demet, "altıgen")
    kontrol("kare demet haritada -> HATA", ok, "-> %s" % h)
    ok, h = hata_var(lambda s: s["kor"].update(adim=KILIF_IC + 2 * KILIF_KAL - 0.01),
                     "demet adımı")
    kontrol("adim < demet dis olcusu (kilif dahil) -> HATA", ok, "-> %s" % h)
    ok, h = hata_var(lambda s: s["kor"].update(harita=["AAAAA", "A"]), "halka")
    kontrol("halka uzunlugu yanlis -> HATA", ok, "-> %s" % h)
    ok, h = hata_var(lambda s: s["kor"].update(yonelim="y"), "yönelim")
    kontrol("kor yonelimi demetle ayni -> HATA", ok, "-> %s" % h)
    ok, h = hata_var(lambda s: s["demetler"][0]["kilif"].update(ic_duz=ZARF - 0.5), "kılıf")
    kontrol("pinler kilifa sigmiyor -> HATA", ok, "-> %s" % h)
    ok, h = hata_var(lambda s: s["demetler"][0]["kilif"].update(malzeme="yok"), "kılıf")
    kontrol("kilif malzemesi tanimsiz -> HATA", ok, "-> %s" % h)
    ok, h = hata_var(lambda s: s["kor"]["sinir"].update(yan="periodic"), "Periyodik")
    kontrol("periodic yan sinir -> HATA", ok, "-> %s" % h)
    ok, h = hata_var(lambda s: s["kor"].update(halka_sayisi=0), "halka")
    kontrol("halka sayisi 0 -> HATA", ok, "-> %s" % h)
    # eski dosyalar (kilifsiz) aynen gecer: tek demet sablonu
    kontrol("kilifsiz tek demet: 0 hata", not _hatalar(_tek_demet_spec()))
    kontrol("kilifli tek demet: 0 hata", not _hatalar(_tek_demet_spec(kilif=True)),
            _hatalar(_tek_demet_spec(kilif=True)))


# ============================================================================
# 3. geometri olculeri ve yonelim (nokta-hucre olcumu)
# ============================================================================

def _merkezler(model):
    """Kok hucrelerinden demet konumlari (translation), kurulum sirasiyla."""
    return [tuple(c.translation[:2]) for c in model.geometry.root_universe.cells.values()
            if c.translation is not None]


def test_altigen_kor_geometri():
    print("\n[AK3] ALTIGEN KOR: demet merkezleri, kilif, sinir olculeri")
    from cekirdek import altigen, kurucu
    s = _kor_spec(kilif=True)
    P = s["kor"]["adim"]
    model, bilgi = kurucu.kur(s)
    merk = _merkezler(model)
    beklenen = [(x * P, y * P) for (_r, _i), (x, y)
                in sorted(altigen.konumlar(2, "x").items())]
    kontrol("7 demet konumu (altigen.konumlar x adim)",
            len(merk) == 7 and all(math.hypot(a[0] - b[0], a[1] - b[1]) < 1e-9
                                   for a, b in zip(merk, beklenen)),
            "-> %s" % [tuple(round(v, 4) for v in m) for m in merk])
    # merkez komsu mesafesi = adim
    uzak = sorted(math.hypot(x, y) for x, y in merk)
    kontrol("komsu merkezler adim uzaklikta", abs(uzak[1] - P) < 1e-9 and abs(uzak[-1] - P) < 1e-9)
    # sinir kutusu: kilifsiz, yansiticisiz -> demet hucrelerinin tam zarfi
    # kor 'x': hucreler 'y' prizma (dusey duz yuz); x yonu 2P + P, y yonu
    # 2*(P*sqrt3/2) + 2*P/sqrt3
    gx, gy = bilgi["sinir_kutu"]
    kontrol("sinir kutusu analitik (3P x (sqrt3 P + 2P/sqrt3))",
            abs(gx - 3 * P) < 1e-9 and abs(gy - (SQ3 * P + 2 * P / SQ3)) < 1e-9,
            "-> %.5f x %.5f" % (gx, gy))
    kontrol("kor_ic_olcusu = sinir kutusu (yansitici yok)",
            tuple(kurucu.kor_ic_olcusu(s, bilgi["sinir_kutu"])) == (gx, gy))
    # yansiticili: dis prizma apotemi = (N-1)P sqrt3/2 + P/sqrt3 + kalinlik
    sy = _kor_spec(kilif=True, yansitici=True)
    _m, by = kurucu.kur(sy)
    a = P * SQ3 / 2 + P / SQ3 + 5.0
    kontrol("yansitici dis prizma kutusu (x: 4a/sqrt3, y: 2a)",
            abs(by["sinir_kutu"][0] - 4 * a / SQ3) < 1e-9
            and abs(by["sinir_kutu"][1] - 2 * a) < 1e-9, "-> %s" % (by["sinir_kutu"],))
    kontrol("kor_ic_olcusu yansitici HARIC = kor hucreleri zarfi",
            all(abs(u - v) < 1e-9 for u, v in zip(kurucu.kor_ic_olcusu(sy, by["sinir_kutu"]),
                                                  (gx, gy))))


def _sinir_bul(model, merkez, yon, r0, r1, adim=60):
    """merkez + yon * r boyunca malzemenin degistigi ilk r (ikiye bolme)."""
    def mal(r):
        return _yaprak_malzeme(model, (merkez[0] + yon[0] * r, merkez[1] + yon[1] * r))
    m0 = mal(r0)
    for _ in range(adim):
        orta = 0.5 * (r0 + r1)
        if mal(orta) == m0:
            r0 = orta
        else:
            r1 = orta
    return 0.5 * (r0 + r1)


def test_altigen_kor_yonelim_olcumu():
    print("\n[AK4] ALTIGEN KOR: yonelim nokta-hucre olcumu (olculdu)")
    from cekirdek import kurucu
    # --- kilifsiz, adim = zarf: demet kose noktalari KENDI hucresinde ---
    s = _kor_spec()
    P = s["kor"]["adim"]
    model, _b = kurucu.kur(s)
    hucreler = [c for c in model.geometry.root_universe.cells.values()
                if c.translation is not None]
    kose_icerde = kose_pin = True
    for h in hucreler:
        cx, cy = h.translation[:2]
        for k in range(6):
            # pin kafesi 'y': kose pinleri 90, 30, -30 ... derecede
            aci = math.radians(90 - 60 * k)
            ux, uy = math.cos(aci), math.sin(aci)
            # demet zarfinin kosesi (pin kafesi 'y' -> zarf tepede sivri)
            rz = ZARF / SQ3 * 0.999
            if _kok_hucresi(model, (cx + ux * rz, cy + uy * rz)) is not h:
                kose_icerde = False
            # kose pininin zarfinin dis kenari (komsuya tasmamali)
            rp = (PIN_HALKA - 1) * PIN_ADIM + R_ZARF * 0.999
            nokta = (cx + ux * rp, cy + uy * rp)
            if _kok_hucresi(model, nokta) is not h or _yaprak_malzeme(model, nokta) != "zr":
                kose_pin = False
    kontrol("demet zarfinin 6 kosesi kendi kor hucresinde (7 demet)", kose_icerde)
    kontrol("kose pinlerinin dis zarfi kirpilmamis, komsuya tasmiyor", kose_pin)
    # --- kilifli: bosluk ve kilif her 6 yonde simetrik ---
    sk = _kor_spec(kilif=True)
    Pk = sk["kor"]["adim"]
    mk, _b = kurucu.kur(sk)
    dis = KILIF_IC + 2 * KILIF_KAL
    olculen = []
    for k in range(6):
        aci = math.radians(0 + 60 * k)      # kor 'x': hucre yuz normalleri 0, 60, ...
        yon = (math.cos(aci), math.sin(aci))
        ic = _sinir_bul(mk, (0.0, 0.0), yon, KILIF_IC / 2 - 0.05, KILIF_IC / 2 + 0.05)
        dk = _sinir_bul(mk, (0.0, 0.0), yon, dis / 2 - 0.05, dis / 2 + 0.05)
        olculen.append((ic, dk))
        m_bosluk = _yaprak_malzeme(mk, (yon[0] * (dis / 2 + KILIF_BOSLUK / 4),
                                        yon[1] * (dis / 2 + KILIF_BOSLUK / 4)))
        kontrol("yon %3d: kilif ic %.6f dis %.6f, bosluk malzemesi %s"
                % (60 * k, ic, dk, m_bosluk),
                abs(ic - KILIF_IC / 2) < 1e-6 and abs(dk - dis / 2) < 1e-6 and m_bosluk == "su")
    kontrol("kilif ve bosluk 6 yonde simetrik (fark < 1e-6 cm)",
            max(o[0] for o in olculen) - min(o[0] for o in olculen) < 1e-6
            and max(o[1] for o in olculen) - min(o[1] for o in olculen) < 1e-6)
    # komsu demetle aradaki bosluk: iki kilif arasi = adim - dis olcu
    yon = (1.0, 0.0)
    bas = _sinir_bul(mk, (0.0, 0.0), yon, dis / 2 - 0.05, dis / 2 + 0.05)
    son = _sinir_bul(mk, (0.0, 0.0), yon, Pk - dis / 2 - 0.05, Pk - dis / 2 + 0.05)
    kontrol("demetler arasi bosluk = adim - dis olcu = %.4f cm" % (Pk - dis),
            abs((son - bas) - (Pk - dis)) < 1e-6, "-> %.6f" % (son - bas))
    # kilif prizmasi yonelimi = pin kafesi yonelimi ('y'): kilif kosesi 90 derecede
    kose = _yaprak_malzeme(mk, (0.0, KILIF_IC / SQ3 + KILIF_KAL / 2))
    kontrol("kilif kosesi tepede (prizma 'y', pin kafesiyle ayni)", kose == "celik", "-> %s" % kose)


def test_altigen_kor_kucuk_parcalar():
    """Kok hucreleri ortusmuyor ve bosluk birakmiyor (rastgele nokta)."""
    print("\n[AK5] ALTIGEN KOR: hucreler ortusmez, sinir icinde bosluk yok")
    import random
    from cekirdek import kurucu
    for ad, s in (("kilifsiz", _kor_spec(halka=3)),
                  ("kilifli+yansitici", _kor_spec(kilif=True, yansitici=True, halka=3))):
        model, bilgi = kurucu.kur(s)
        kok = list(model.geometry.root_universe.cells.values())
        gx, gy = bilgi["sinir_kutu"]
        rnd = random.Random(7)
        cift = eksik = 0
        for _ in range(3000):
            p = (rnd.uniform(-gx / 2, gx / 2), rnd.uniform(-gy / 2, gy / 2), 0.0)
            n = sum(1 for c in kok if p in c.region)
            cift += n > 1
            if n == 0 and s["kor"]["yansitici"]["var"]:
                # yansiticili korda dis prizmanin icinde her nokta bir hucrede
                a = bilgi["sinir_kutu"][1] / 2
                icerde = all(abs(p[0] * math.cos(math.radians(t)) + p[1] * math.sin(
                    math.radians(t))) < a - 1e-9 for t in (90, 30, 150))
                eksik += icerde
        kontrol("%s: ortusen nokta yok, eksik nokta yok" % ad, cift == 0 and eksik == 0,
                "-> ortusen %d, eksik %d" % (cift, eksik))


def test_altigen_tek_demet_kilif():
    print("\n[AK6] TEK DEMET + KILIF: sinir kilif dis yuzunde")
    from cekirdek import kurucu
    s = _tek_demet_spec(kilif=True)
    model, bilgi = kurucu.kur(s)
    dis = KILIF_IC + 2 * KILIF_KAL
    kontrol("kilif malzemesi: kilif ortasinda celik",
            _yaprak_malzeme(model, (dis / 2 - KILIF_KAL / 2, 0.0)) == "celik")
    kontrol("kilifin disi modelin disi (sinir kilif dis yuzunde)",
            not _yol(model, (dis / 2 + 0.01, 0.0)))
    kontrol("sinir kutusu: prizma 'y' (x = dis, y = 2 dis/sqrt3)",
            abs(bilgi["sinir_kutu"][0] - dis) < 1e-9
            and abs(bilgi["sinir_kutu"][1] - 2 * dis / SQ3) < 1e-9, "-> %s" % (bilgi["sinir_kutu"],))
    s0 = _tek_demet_spec()
    _m0, b0 = kurucu.kur(s0)
    from cekirdek import altigen
    kontrol("kilifsiz tek demet: eski olcu korunur (kapsayan_olcu)",
            tuple(b0["sinir_kutu"]) == altigen.kapsayan_olcu(PIN_HALKA, PIN_ADIM, "y"))


def test_altigen_kor_katman_anahtari():
    print("\n[AK7] ALTIGEN KOR: eksenel katmanlar ve katmana ozel anahtar")
    from cekirdek import kurucu, sema
    s = _kor_spec()
    s["demetler"].append(dict(copy.deepcopy(s["demetler"][0]), ad="hex2", dolgu_disi="su"))
    s["kor"]["eksenel"] = {"var": True, "bolgeler": [
        sema.eksenel_bolge("alt_yans", 10.0, "su"),
        sema.eksenel_bolge("aktif", 50.0, None),
        sema.eksenel_bolge("ust", 20.0, None, anahtar={"A": "hex2"})]}
    model, _b = kurucu.kur(s)
    hucreler = list(model.geometry.root_universe.cells.values())
    kontrol("7 konum x 3 katman = 21 kok hucresi", len(hucreler) == 21, "-> %d" % len(hucreler))
    ust = [c for c in hucreler if c.name.endswith("ust")]
    kontrol("ust katmanda harf A -> hex2",
            ust and all("hex2" in (c.fill.name or "") for c in ust),
            "-> %s" % [c.fill.name for c in ust[:2]])
    kontrol("aktif aralik yalniz aktif+ust (-30, 40)",
            kurucu.aktif_eksenel_aralik(s) == (-30.0, 40.0), "-> %s" % (kurucu.aktif_eksenel_aralik(s),))


# ============================================================================
# 4. betik, tukenme, tur degisimi, baslangic, arayuz
# ============================================================================

def _betik_modeli(spec, dizin):
    from cekirdek import kod_uret
    betik = os.path.join(dizin, "model.py")
    with open(betik, "w", encoding="utf-8") as f:
        f.write(kod_uret.uret(spec, "model.py"))
    sm = importlib.util.spec_from_file_location("altigen_betik_%d" % id(spec), betik)
    mod = importlib.util.module_from_spec(sm)
    eski = os.getcwd()
    try:
        os.chdir(dizin)
        sm.loader.exec_module(mod)
    finally:
        os.chdir(eski)
    return mod.model


def test_altigen_kor_betik_geometrisi():
    print("\n[AK8] ALTIGEN KOR: uretilen betik ayni geometriyi kurar (nokta testi)")
    import random
    import tempfile
    from cekirdek import kurucu
    s = _kor_spec(kilif=True, yansitici=True)
    s["kor"]["yukseklik"] = 80.0
    ma, ba = kurucu.kur(s)
    mb = _betik_modeli(s, tempfile.mkdtemp(prefix="altigen_betik_"))
    kontrol("kok hucre sayisi ayni", len(ma.geometry.root_universe.cells)
            == len(mb.geometry.root_universe.cells))
    gx, gy = ba["sinir_kutu"]
    rnd = random.Random(3)
    farkli = 0
    for _ in range(1500):
        p = (rnd.uniform(-gx / 2, gx / 2), rnd.uniform(-gy / 2, gy / 2))
        farkli += _yaprak_malzeme(ma, p) != _yaprak_malzeme(mb, p)
    kontrol("1500 noktada malzeme ayni", farkli == 0, "-> %d farkli" % farkli)
    kontrol("kaynak kutusu ayni", str(ma.settings.source[0].space.lower_left)
            == str(mb.settings.source[0].space.lower_left)
            if hasattr(ma.settings.source[0].space, "lower_left") else True)


def test_altigen_kor_tukenme_sayimi():
    print("\n[AK9] ALTIGEN KOR: tukenme sayimi ve analitik hacim")
    from cekirdek import tukenme
    s = _kor_spec(kilif=True)
    s["kor"]["yukseklik"] = 100.0
    n_pin = 7 * 19
    kontrol("yakit ornek sayisi = 7 x 19", tukenme.yakit_ornek_sayisi(s) == n_pin,
            "-> %s" % tukenme.yakit_ornek_sayisi(s))
    V = tukenme.hacimler(s)["uo2"]["hacim"]
    Vb = n_pin * math.pi * R_YAKIT ** 2 * 100.0
    kontrol("uo2 hacmi = 133 pi r^2 H (%.6g cm3)" % Vb, V is not None and abs(V - Vb) / Vb < 1e-12,
            "-> %s" % V)


def test_altigen_kor_tur_degisimi():
    print("\n[AK10] TUR DEGISIMI: altigen_kafes'e gecis eksik parcayi kurar")
    from cekirdek import altigen, sema
    from arayuz.pencere.model_islemleri import kor_turu_degistir
    # (a) altigen tek demetten
    s = _tek_demet_spec()
    kor_turu_degistir(s, "altigen_kafes")
    k = s["kor"]
    kontrol("(a) 2 halkali 7 demetli harita",
            k["halka_sayisi"] == 2 and [len(x) for x in k["harita"]] == [6, 1]
            and set(k["anahtar"].values()) == {"hex"}, "-> %s" % k)
    kontrol("(a) kor yonelimi demetin tersi ('x')", k["yonelim"] == "x")
    kontrol("(a) adim = demet dis olcusu", abs(k["adim"] - ZARF) < 1e-6, "-> %s" % k["adim"])
    kontrol("(a) 0 hata", not _hatalar(s), _hatalar(s))
    # (b) yalniz kare demetli modelden: altigen demet kurulur
    from arayuz import baslangic
    t = baslangic.bos_sablon("demet_kare")
    eklenen = []
    kor_turu_degistir(t, "altigen_kafes", eklenen=eklenen)
    hex_ = [d for d in t["demetler"] if d.get("tur") == "altigen"]
    kontrol("(b) eksik altigen demet kuruldu", len(hex_) == 1 and hex_[0]["ad"] in eklenen,
            "-> %s" % eklenen)
    kontrol("(b) harita altigen demete isaret ediyor",
            set(t["kor"]["anahtar"].values()) == {hex_[0]["ad"]} if hex_ else False)
    kontrol("(b) 0 hata", not _hatalar(t), _hatalar(t))
    # (c) kare_kafes <-> altigen_kafes: harita karismaz
    hafiza = {}
    u = baslangic.bos_sablon("tam_kor")
    kor_turu_degistir(u, "altigen_kafes", hafiza)
    kontrol("(c) kare haritadan altigene: halka bicimli harita",
            [len(x) for x in u["kor"]["harita"]] == altigen.halka_uzunluklari(
                u["kor"]["halka_sayisi"]))
    kor_turu_degistir(u, "kare_kafes", hafiza)
    kontrol("(c) geri kare_kafes: eski 3x3 harita hatirlandi",
            u["kor"]["boyut"] == [3, 3] and len(u["kor"]["harita"]) == 3,
            "-> %s" % u["kor"]["harita"])
    kontrol("(c) 0 hata", not _hatalar(u), _hatalar(u))
    kontrol("sema: halka_sayisi/yonelim kare_kafes'te varsayilana doner",
            u["kor"]["halka_sayisi"] == sema.VARSAYILAN_KOR["halka_sayisi"])


def test_altigen_kor_baslangic_karti():
    print("\n[AK11] BASLANGIC: 'Tam kor — altıgen' karti ve bos sablonu")
    from arayuz import baslangic
    from cekirdek import kurucu
    kart = [k for k in baslangic.KARTLAR if k["anahtar"] == "tam_kor_altigen"]
    kontrol("kart var", len(kart) == 1 and kart[0]["baslik"] == "Tam kor — altıgen")
    s = baslangic.bos_sablon("tam_kor_altigen")
    kontrol("sablon turu altigen_kafes, 7 demet",
            s["kor"]["tur"] == "altigen_kafes" and s["kor"]["halka_sayisi"] == 2)
    kontrol("sablon 0 hata", not _hatalar(s), _hatalar(s))
    try:
        kurucu.kur(s)
        kontrol("sablon kuruluyor", True)
    except Exception as e:
        kontrol("sablon kuruluyor", False, "-> %s" % e)


def _qt():
    try:
        from PySide6 import QtWidgets
    except ImportError as e:                         # pragma: no cover
        kontrol("PySide6 yok, arayuz testi atlandi", True, "-> %s" % e)
        return None
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_altigen_kor_sekmesi():
    print("\n[AK12] KOR SEKMESI: altigen harita boyanir, halka kucultme onay ister")
    if _qt() is None:
        return
    from arayuz.sekme_kor import KorSekmesi
    s = _kor_spec(halka=3)
    s["demetler"].append(dict(copy.deepcopy(s["demetler"][0]), ad="hex2"))
    k = KorSekmesi()
    k.resize(900, 900)
    k.spec_yukle(s)
    k.show()
    hk = k.altigen_harita
    kontrol("altigen harita gorunur, kare harita gizli (ayni 'Kor haritası' kutusu)",
            hk.isVisibleTo(k) and k.kafes_kutu.isVisibleTo(k)
            and not k.kare_harita.isVisibleTo(k))
    kontrol("izgara 3 halka, yonelim 'x'",
            hk.izgara.halka_sayisi == 3 and hk.izgara.yonelim == "x")
    kontrol("palette altigen demetler var, kare yok",
            {"hex", "hex2"} <= set(hk.palet.adlar()))
    # merkez hucreyi hex2 ile boya
    hk.palet.sec("hex2")
    hk.izgara.hucreyi_boya((2, 0), "hex2")
    hk.izgara.degisti.emit()
    kor = s["kor"]
    kontrol("boyama spec'e yazildi (merkez -> hex2)",
            kor["anahtar"].get(kor["harita"][2]) == "hex2", "-> %s %s" % (kor["harita"], kor["anahtar"]))
    sorular = []
    k._onay_al = lambda b, m: (sorular.append(b), False)[1]
    hk.halka.setValue(2)
    kontrol("halka kucultme onay istedi, reddedilince degismedi",
            sorular and kor["halka_sayisi"] == 3 and hk.halka.value() == 3)
    k._onay_al = lambda b, m: (sorular.append(b), True)[1]
    hk.halka.setValue(2)
    kontrol("onaylaninca 2 halka, merkez korundu",
            kor["halka_sayisi"] == 2 and [len(x) for x in kor["harita"]] == [6, 1]
            and kor["anahtar"].get(kor["harita"][1]) == "hex2", "-> %s" % kor["harita"])
    hk.halka.setValue(3)
    kontrol("buyutme onay istemez, 3 halka",
            kor["halka_sayisi"] == 3 and len(sorular) == 2)
    i = hk.yonelim.findData("y")
    hk.yonelim.setCurrentIndex(i)
    kontrol("yonelim secimi spec'e yazildi", kor["yonelim"] == "y")
    kontrol("adim etiketi 'Demet adımı:'", k.satir_adim[0].text() == "Demet adımı:")
    k.close()


# ============================================================================
# 5. YAVAS: Monte Carlo
# ============================================================================

def _kos(model, dizin, parcacik, cevrim=130, pasif=30):
    import openmc
    model.settings.particles = parcacik
    model.settings.batches = cevrim
    model.settings.inactive = pasif
    model.settings.seed = 11
    os.makedirs(dizin, exist_ok=True)
    return openmc.StatePoint(model.run(cwd=dizin, threads=ISLEM_PARCACIGI,
                                       output=False)).keff


def test_altigen_analitik_esdegerlik(gecici):
    """7 ayni kilifsiz demet (adim = zarf, yan sinir reflective) = tek demet sonsuz kafes."""
    print("\n[AK13] ANALITIK ESDEGERLIK: 7 demet = tek demet sonsuz kafes")
    from cekirdek import kurucu
    tek, _b = kurucu.kur(_tek_demet_spec())
    kor, _b = kurucu.kur(_kor_spec())
    k1 = _kos(tek, os.path.join(gecici, "tek"), 20000)
    k2 = _kos(kor, os.path.join(gecici, "kor"), 20000)
    fark = abs(k1.nominal_value - k2.nominal_value)
    sigma = math.hypot(k1.std_dev, k2.std_dev)
    kontrol("tek %.5f +/- %.5f  vs  7 demet %.5f +/- %.5f  (fark %.2f sigma)"
            % (k1.nominal_value, k1.std_dev, k2.nominal_value, k2.std_dev, fark / sigma),
            fark <= 2 * sigma and 2 * sigma <= 0.0015, "-> 2 sigma = %.0f pcm" % (2e5 * sigma))


def test_altigen_betik_esdegerligi(gecici):
    print("\n[AK14] BETIK ESDEGERLIGI: altigen kor (kilif + yansitici + katman)")
    from cekirdek import kurucu, sema
    s = _kor_spec(kilif=True, yansitici=True)
    s["kor"]["eksenel"] = {"var": True, "bolgeler": [
        sema.eksenel_bolge("alt", 10.0, "su"), sema.eksenel_bolge("aktif", 40.0, None)]}
    s["kor"]["sinir"].update(alt="vacuum", ust="vacuum")
    s["ayarlar"]["kaynak"]["tur"] = "kutu"
    ma, _b = kurucu.kur(s)
    ka = _kos(ma, os.path.join(gecici, "a"), 2000, 30, 10)
    bdir = os.path.join(gecici, "betik")
    os.makedirs(bdir, exist_ok=True)
    mb = _betik_modeli(s, bdir)
    kb = _kos(mb, os.path.join(gecici, "b"), 2000, 30, 10)
    fark = abs(ka.nominal_value - kb.nominal_value)
    kontrol("kurucu %.10f vs betik %.10f" % (ka.nominal_value, kb.nominal_value),
            fark < 1e-10, "-> fark %.2e" % fark)


def test_altigen_tukenme_hacmi_stokastik(gecici):
    print("\n[AK15] TUKENME HACMI: analitik vs OpenMC stokastik hacim")
    from cekirdek import tukenme
    s = _kor_spec(kilif=True, yansitici=True)
    s["kor"]["yukseklik"] = 50.0
    s["ayarlar"]["tohum"] = 5
    a = tukenme.hacimler(s)["uo2"]["hacim"]
    v, sd = tukenme.stokastik_hacimler(s, ["uo2"], orneklem=4_000_000,
                                       dizin=gecici)["uo2"]
    kontrol("analitik %.3f cm3 vs stokastik %.3f +/- %.3f (%.2f sigma)"
            % (a, v, sd, abs(a - v) / sd), abs(a - v) <= 2 * sd)


def test_altigen_cizim(gecici=None):
    print("\n[AK16] Model.plot: altigen kor (kilif + yansitici) ciziliyor")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from cekirdek import kurucu
    eski = os.getcwd()
    try:
        for ad, s in (("kilifsiz", _kor_spec()),
                      ("kilifli+yansitici", _kor_spec(kilif=True, yansitici=True, halka=3))):
            model, bilgi = kurucu.kur(s)
            model.plot(basis="xy", width=bilgi["sinir_kutu"], pixels=(200, 200),
                       color_by="material", colors=bilgi["renkler"])
            plt.close("all")
            kontrol("%s ciziliyor" % ad, True)
    except Exception as e:
        kontrol("altigen kor ciziliyor", False, "-> %s" % e)
    finally:
        os.chdir(eski)


HIZLI = [
    test_altigen_kor_sema_ve_kurallar, test_altigen_kor_dogrulama,
    test_altigen_kor_geometri, test_altigen_kor_yonelim_olcumu,
    test_altigen_kor_kucuk_parcalar, test_altigen_tek_demet_kilif,
    test_altigen_kor_katman_anahtari, test_altigen_kor_betik_geometrisi,
    test_altigen_kor_tukenme_sayimi, test_altigen_kor_tur_degisimi,
    test_altigen_kor_baslangic_karti, test_altigen_kor_sekmesi,
]
YAVAS = [
    test_altigen_analitik_esdegerlik, test_altigen_betik_esdegerligi,
    test_altigen_tukenme_hacmi_stokastik, test_altigen_cizim,
]
