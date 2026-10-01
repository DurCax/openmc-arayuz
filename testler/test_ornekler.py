# -*- coding: utf-8 -*-
"""
test_ornekler.py -- Dalga 2 ornek paketi: meta, dogrulama kapisi ve kaynaktan gelen
sayilar (demet/cubuk sayilari, olculer, hacim kesirleri).

HIZLI
  [OR1] Her ornek: dogrula_meta temiz, dogrula.kapi(veri_kontrolu=True) hatasiz;
        yeni orneklerde baslik_en / aciklama_en var.
  [OR2] VVER-1000 koru: 8 halka (169) - 6 kose yansitici = 163 demet; kor 'x', pin 'y'.
  [OR3] VVER-1000 demetleri: 331 konum = 312 yakit (12 Gd) + 18 kilavuz + 1 merkez;
        pin adimi 1.275, demet adimi 23.6 (kap), 11 halka, fiziksel kilif yok.
  [OR4] SFR MET-1000: tel sarimi homojenlestirmesinde kutle korunumu -- aktif bolge
        hacim kesirleri geometriden = Tablo 2.20 (yakit 39.00, HT-9 25.66, Na 35.34 %).
  [OR5] SFR MET-1000 koru: 78/102/114/66/15/4 (toplam 379), 271 pin.
  [OR6] LCT-008: 4961 cubuk, tank ic yaricapi 76.2 cm.
  [OR7] BEAVRS benzeri: 193 demet, 3 zenginlik (65/64/64), 21.50364 / 1.25984 cm,
        Pyrex (B-10) cubuklari.
  [OR8] Tam korlarin varsayilan hassasiyeti "Hizli deneme" (1000/60/20).
  [OR9] Ceyrek kor, tam korun sag-alt ceyregi; simetri yuzleri yansitici, dis yuzler vakum.
  [OR10] BEAVRS cok turlu guc (ON_KOSUL: Ajan 8b guc_dagilimi.cubuklar birlesmis).
YAVAS
  [OR11] Yeni ornekler kosucu.calistir(dogrulama=True) ile kisa kosar.
  [OR12] Ceyrek kor k = tam kor k (2 sigma): yuz basina sinir (simetri yuzleri
         yansitici, dis yuzler vakum).
  [OR13] Gd tukenmesi: dis halka ic halkadan hizli yanar (sogan kabugu), k yukselir.
Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import glob
import json
import math
import os

from testler.ortak_test import kontrol, ORNEK, ISLEM_PARCACIGI
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik

YENI = ("kriter_jezebel.json", "kriter_flattop25.json", "kriter_lct008.json",
        "kriter_vver1000_ugd.json", "vver1000_demet.json", "vver1000_kor.json",
        "sfr_met1000_demet.json", "sfr_met1000_kor.json", "pwr_beavrs_kor.json",
        "pwr_mox_demet.json", "pwr_gd_tukenme.json", "bwr_10x10.json", "mtr_kor.json",
        "zirh_katmanli.json", "pwr_smr_kor.json", "pwr_ceyrek_kor.json")
TAM_KORLAR = ("vver1000_kor.json", "sfr_met1000_kor.json", "pwr_beavrs_kor.json",
              "pwr_smr_kor.json", "pwr_ceyrek_kor.json")
HIZLI_DENEME = (1000, 60, 20)


def _ham(ad):
    with open(os.path.join(ORNEK, ad), encoding="utf-8") as f:
        return json.load(f)


def _spec(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad))


def _bul(liste, ad):
    return next(x for x in liste if x["ad"] == ad)


@gereksinim("R-A3-01")
def test_butun_ornekler_kapidan_gecer():
    print("\n[OR1] Butun ornekler: meta temiz, kapi(veri_kontrolu=True) hatasiz")
    from cekirdek import dogrula, ornek_bilgi
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        ad = os.path.basename(yol)
        ham = _ham(ad)
        kontrol("%s: meta temiz" % ad, ornek_bilgi.dogrula_meta(ham) == [],
                "-> %s" % ornek_bilgi.dogrula_meta(ham))
        try:
            dogrula.kapi(_spec(ad), veri_kontrolu=True)
            kontrol("%s: kapidan gecti" % ad, True)
        except dogrula.DogrulamaHatasi as e:
            kontrol("%s: kapidan gecti" % ad, False, "-> %s" % [b.mesaj for b in e.bulgular])
    for ad in YENI:
        ham = _ham(ad)
        kontrol("%s: baslik_en ve aciklama_en" % ad, bool(ham.get("baslik_en"))
                and bool(ham.get("aciklama_en")))


def test_vver_kor_163_demet():
    print("\n[OR2] VVER-1000 koru: 169 - 6 = 163 demet")
    from cekirdek import altigen
    kor = _spec("vver1000_kor.json")["kor"]
    harfler = "".join(kor["harita"])
    demetler = [h for h in harfler if kor["anahtar"][h].startswith("tvs_")]
    kontrol("8 halka, 169 konum", kor["halka_sayisi"] == 8 and len(harfler) == 169
            == altigen.toplam_hucre(8))
    kontrol("163 yakit demeti", len(demetler) == 163, "-> %d" % len(demetler))
    dis = kor["harita"][0]
    kose = [dis[i] for i in range(0, len(dis), 7)]
    kontrol("dis halkanin 6 kosesi yansitici",
            all(kor["anahtar"][h] == "yansitici_celik_su" for h in kose)
            and len(harfler) - len(demetler) == 6)
    s = _spec("vver1000_kor.json")
    kontrol("kor 'x', demet pinleri 'y'", kor["yonelim"] == "x"
            and all(d["yonelim"] == "y" for d in s["demetler"]))
    kontrol("demet adimi 23.6 cm", kor["adim"] == 23.6)


def test_vver_demetleri():
    print("\n[OR3] VVER-1000 demetleri: 331 = 312 yakit + 18 kilavuz + 1 merkez")
    for ad in ("vver1000_demet.json", "kriter_vver1000_ugd.json"):
        s = _spec(ad)
        d = s["demetler"][0]
        harfler = "".join(d["harita"])
        tur = {h: _bul(s["cubuklar"], c) for h, c in d["anahtar"].items()}

        def say(kosul):
            return sum(1 for h in harfler if kosul(tur[h]))
        yakit = say(lambda c: c["ad"].startswith(("yakit", "tveg")))
        gd = say(lambda c: "gd" in c["ad"] or "tveg" in c["ad"])
        kl = say(lambda c: c["ad"] == "kilavuz_boru")
        mb = say(lambda c: c["ad"] == "merkez_boru")
        kontrol("%s: 331 konum, 11 halka" % ad, len(harfler) == 331 and d["halka_sayisi"] == 11)
        kontrol("%s: 312 yakit (12 Gd), 18 kilavuz, 1 merkez" % ad,
                (yakit, gd, kl, mb) == (312, 12, 18, 1), "-> %s" % ((yakit, gd, kl, mb),))
        kontrol("%s: pin adimi 1.275" % ad, d["adim"] == 1.275)
        k = d.get("kilif") or {}
        dis = k.get("ic_duz", 0) + 2 * k.get("kalinlik", 0)
        kontrol("%s: 23.6 cm kap, kilif malzemesi = dis dolgu (fiziksel kilif yok)" % ad,
                abs(dis - 23.6) < 1e-9 and k.get("malzeme") == d["dolgu_disi"])
    c = _bul(_spec("vver1000_demet.json")["cubuklar"], "yakit_cubugu")
    r = [b["r"] for b in c["bolgeler"]]
    kontrol("pelet deligi 0.07, pelet 0.3785, kilif 0.386/0.455", r[:4] == [0.07, 0.3785, 0.386, 0.455])


def _sfr_kesirleri(s):
    d = s["demetler"][0]
    c = _bul(s["cubuklar"], d["anahtar"]["y"])
    k = d["kilif"]
    P = s["kor"]["adim"]
    n = sum(len(h) for h in d["harita"])
    hucre = math.sqrt(3) / 2 * P ** 2
    rf, rc = c["bolgeler"][0]["r"], c["bolgeler"][1]["r"]
    yakit = n * math.pi * rf ** 2
    dis = k["ic_duz"] + 2 * k["kalinlik"]
    ht9 = n * math.pi * (rc ** 2 - rf ** 2) + math.sqrt(3) / 2 * (dis ** 2 - k["ic_duz"] ** 2)
    return n, 100 * yakit / hucre, 100 * ht9 / hucre, 100 * (hucre - yakit - ht9) / hucre


def test_sfr_kutle_korunumu():
    print("\n[OR4] SFR MET-1000: tel sarimi kilifa homojen -- hacim kesirleri Tablo 2.20")
    for ad in ("sfr_met1000_demet.json", "sfr_met1000_kor.json"):
        n, yakit, ht9, na = _sfr_kesirleri(_spec(ad))
        kontrol("%s: 271 pin" % ad, n == 271)
        kontrol("%s: yakit %%%.2f (39.00)" % (ad, yakit), abs(yakit - 39.00) < 0.05)
        kontrol("%s: HT-9 %%%.2f (25.66)" % (ad, ht9), abs(ht9 - 25.66) < 0.05)
        kontrol("%s: Na %%%.2f (35.34)" % (ad, na), abs(na - 35.34) < 0.05)
    s = _spec("sfr_met1000_demet.json")
    kontrol("tek demet: halka=1 altigen_kafes", s["kor"]["tur"] == "altigen_kafes"
            and s["kor"]["halka_sayisi"] == 1)
    kontrol("hizli zincir", s["tukenme"]["zincir"] == "hizli")


def test_sfr_kor_sayilari():
    print("\n[OR5] SFR MET-1000 koru: Sekil 2.7 sayilari")
    kor = _spec("sfr_met1000_kor.json")["kor"]
    h = "".join(kor["harita"])
    say = {c: h.count(c) for c in "IORSPC"}
    kontrol("78/102/114/66/15/4", say == {"I": 78, "O": 102, "R": 114, "S": 66, "P": 15, "C": 4},
            "-> %s" % say)
    kontrol("toplam 379", sum(say.values()) == 379)
    toplam = sum(b["yukseklik"] for b in kor["eksenel"]["bolgeler"])
    kontrol("eksenel toplam 480.20 cm", abs(toplam - 480.20) < 1e-6, "-> %.4f" % toplam)


def test_lct008():
    print("\n[OR6] LCT-008: 4961 cubuk, 76.2 cm tank")
    s = _spec("kriter_lct008.json")
    d = s["demetler"][0]
    kontrol("4961 yakit cubugu", "".join(d["harita"]).count("y") == 4961)
    kor = s["kor"]
    kontrol("tank ic yaricapi 76.2", abs(kor["kor_yaricap"] + kor["yansitici"]["kalinlik"] - 76.2)
            < 1e-9)
    kontrol("tambur yok", kor["tambur"]["sayi"] == 0)


def test_beavrs():
    print("\n[OR7] BEAVRS benzeri kor: 193 demet, 3 zenginlik, olculer")
    s = _spec("pwr_beavrs_kor.json")
    kor = s["kor"]
    konum = [kor["anahtar"][h] for h in "".join(kor["harita"])]
    demetler = [a for a in konum if a != "su_borlu"]
    kontrol("193 demet", len(demetler) == 193, "-> %d" % len(demetler))
    zen = {z: sum(1 for a in demetler if a.startswith("d" + z)) for z in "abc"}
    kontrol("zenginlik 1.6/2.4/3.1: 65/64/64", zen == {"a": 65, "b": 64, "c": 64}, "-> %s" % zen)
    kontrol("demet adimi 21.50364", kor["adim"] == 21.50364)
    kontrol("pin adimi 1.25984", all(d["adim"] == 1.25984 for d in s["demetler"]))
    pyrex = sum(_bul(s["demetler"], a)["harita"][i].count("p") for a in demetler for i in range(17))
    kontrol("Pyrex cubuklari (BEAVRS modeli: 1268)", pyrex == 1268, "-> %d" % pyrex)
    b10 = _bul(s["malzemeler"], "pyrex")
    kontrol("Pyrex B-10 iceriyor", any(x["isim"] == "B10" for x in b10["bilesim"]))


def test_tam_kor_varsayilani():
    print("\n[OR8] Tam korlar 'Hizli deneme' ile acilir")
    for ad in TAM_KORLAR:
        a = _spec(ad)["ayarlar"]
        kontrol("%s: 1000/60/20" % ad, (a["parcacik"], a["cevrim"], a["pasif"]) == HIZLI_DENEME)


def test_ceyrek_kor():
    print("\n[OR9] Ceyrek kor = tam korun sag-alt ceyregi; AYNALAMA tam koru geri verir")
    tam = _spec("pwr_smr_kor.json")["kor"]
    cey = _spec("pwr_ceyrek_kor.json")["kor"]
    n = tam["boyut"][0] // 2
    kontrol("harita ceyrek", cey["harita"] == [r[n:] for r in tam["harita"][n:]])
    # Simetri duzlemi YANSITICI sinirdir: cozulen model, ceyregin iki eksende
    # AYNALANMASIYLA oluşan kordur. Dama deseninin 180 derece donme simetrisi
    # vardir ama ayna simetrisi yoktur; boyle bir desen sessizce BASKA bir kor
    # cozerdi (olculdu: +260 pcm). Bu denetim Monte Carlo'suz yakalar.
    aynali = [r[::-1] + r for r in cey["harita"]]
    aynali = [s[::1] for s in reversed(aynali)] + aynali
    kontrol("ceyregin aynasi tam korun kendisi", aynali == tam["harita"],
            "-> ilk fark: %s" % next((i for i, (a, b) in enumerate(zip(aynali, tam["harita"]))
                                      if a != b), None))
    kontrol("dis iki yuzde >= 2 sira su", all(r[-2:] == "ss" for r in cey["harita"])
            and cey["harita"][-1] == cey["harita"][-2] == "s" * n)
    # Yuz basina sinir (§15 karar 4): simetri yuzleri (-x sol, +y ust) yansitici,
    # dis yuzler (+x, -y) ve eksenel yuzler vakum -- tam korla AYNI fizik.
    kontrol("simetri yuzleri yansitici, dis yuzler ve eksenel vakum",
            cey["sinir"] == {"yan": "vacuum", "alt": "vacuum", "ust": "vacuum",
                             "yuzler": {"-x": "reflective", "+x": "vacuum",
                                        "-y": "vacuum", "+y": "reflective"}}, "-> %s" % cey["sinir"])
    kontrol("tam kor dort yuz vakum", tam["sinir"]["yan"] == "vacuum"
            and not tam["sinir"].get("yuzler"))
    kontrol("tam kor 52 demet, ceyrek 13", sum(c in "AB" for r in tam["harita"] for c in r) == 52
            and sum(c in "AB" for r in cey["harita"] for c in r) == 13)


def _on_kosul_atla(neden):
    """ON_KOSUL karsilanmadi: pytest altinda atla, eski calistiricida bilgi yaz."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        import pytest
        pytest.skip("ÖN_KOŞUL: " + neden)
    print("  [ATLANDI] ÖN_KOŞUL: %s" % neden)


def test_beavrs_cok_turlu_guc():
    print("\n[OR10] BEAVRS: guc dagilimi uc yakit turunu kapsar (ON_KOSUL: Ajan 8b)")
    from cekirdek import dogrula, sema
    if "cubuklar" not in sema.VARSAYILAN_GUC:
        _on_kosul_atla("guc_dagilimi.cubuklar (Ajan 8b) henuz birlesmedi")
        return
    s = _spec("pwr_beavrs_kor.json")
    kontrol("uc tur listede", [c["cubuk"] for c in s["guc_dagilimi"]["cubuklar"]]
            == ["yakit_a", "yakit_b", "yakit_c"])
    mesajlar = [b.mesaj for b in dogrula.guc_dagilimi_kontrol(s)]
    kontrol("'yalniz tek cubuk' uyarisi yok", not any("yalnız" in m for m in mesajlar),
            "-> %s" % mesajlar)


# ---------------------------------------------------------------------------
# YAVAS
# ---------------------------------------------------------------------------

def _kos(ad, gecici, n=500, c=30, p=10, spec=None):
    from cekirdek import kosucu
    s = spec or _spec(ad)
    a = s["ayarlar"]
    a["parcacik"], a["cevrim"], a["pasif"] = n, c, (p if a.get("mod") == "eigenvalue" else 0)
    s["tukenme"]["var"] = False
    r = kosucu.calistir(s, os.path.join(gecici, os.path.splitext(ad)[0]),
                        is_parcacigi=ISLEM_PARCACIGI)
    if not kontrol("%s: kosu basarili" % ad, r["basarili"], "-> %s" % r.get("log")):
        return None
    return kosucu.sonuc_oku(r["statepoint"])


@gereksinim("R-M3-01")
def test_yavas_yeni_ornekler_kosar(gecici):
    print("\n[OR11] Yeni ornekler kosucu.calistir(dogrulama=True) ile kisa kosar")
    for ad in YENI:
        if ad.startswith("kriter_"):
            continue                        # test_benchmark kosar
        sonuc = _kos(ad, gecici)
        if sonuc is None:
            continue
        if sonuc["mod"] == "eigenvalue":
            k = sonuc["keff"][0]
            kontrol("%s: k = %.4f makul (0.5-1.6)" % (ad, k), 0.5 < k < 1.6)
        else:
            kontrol("%s: sabit kaynak tally'leri okundu" % ad, bool(sonuc["tallyler"]))


@gereksinim("R-G-06")
def test_yavas_ceyrek_tam_esit(gecici):
    print("\n[OR12] Ceyrek kor k = tam kor k (dosyalardaki sinirlarla, 2 sigma)")
    # Yuz basina sinir (G-4): ceyregin simetri yuzleri yansitici, dis yuzleri
    # vakum; tam kor dort yuz vakum. Iki model ayni fizigi cozer (olculdu
    # 01.10.2026: tam 1.05881 +/- 0.00059, ceyrek 1.05922 +/- 0.00066, 0.5 sigma).
    t = _kos("pwr_smr_kor.json", gecici, 20000, 160, 60)
    c = _kos("pwr_ceyrek_kor.json", gecici, 20000, 160, 60)
    if t is None or c is None:
        return
    (kt, st), (kc, sc) = t["keff"], c["keff"]
    z = abs(kt - kc) / math.hypot(st, sc)
    print("   tam %.5f +/- %.5f, ceyrek %.5f +/- %.5f" % (kt, st, kc, sc))
    kontrol("ceyrek = tam (%.2f sigma)" % z, z <= 2.0)


def test_yavas_gd_sogan_kabugu(gecici):
    print("\n[OR13] Gd tukenmesi: uzaysal oz-perdeleme (sogan kabugu)")
    from cekirdek import tukenme
    s = _spec("pwr_gd_tukenme.json")
    a = s["ayarlar"]
    a["parcacik"], a["cevrim"], a["pasif"] = 1500, 40, 15
    s["tukenme"]["adimlar"] = [0.02, 0.08, 0.9, 2.0, 2.0]        # 5 MWd/kg
    d = os.path.join(gecici, "gd")
    tukenme.calistir(s, d)
    r = tukenme.sonuc_oku(os.path.join(d, "depletion_results.h5"), s)
    g = {m: v["Gd157"] for m, v in r["yogunluk"].items() if m.startswith("uo2_gd")}
    kalan = {m: v[-1] / v[0] for m, v in g.items()}
    print("   Gd157 kalan orani: %s" % {m: round(v, 3) for m, v in sorted(kalan.items())})
    # Gd-157 tesir kesiti oyle buyuktur ki pelet disindan ice dogru "sogan kabugu"
    # gibi yanar: kalan orani halka numarasiyla (icten disa) TEK YONLU azalir.
    sirali = [kalan["uo2_gd_%d" % i] for i in range(1, 6)]
    kontrol("kalan Gd157 ictan disa tek yonlu azalir",
            all(x > y for x, y in zip(sirali, sirali[1:])), "-> %s" % [round(x, 3) for x in sirali])
    kontrol("dis halka (5) neredeyse tukendi (< %5)", sirali[-1] < 0.05, "-> %.3f" % sirali[-1])
    kontrol("ic halka (1) yarisindan fazlasini korudu", sirali[0] > 0.5, "-> %.3f" % sirali[0])
    # 5 MWd/kg'da Gd hala ic halkalarda duruyor; 25 cubuktan yalnizca biri Gd'li
    # oldugu icin tutma etkisi zayiftir ve k tepesi GORULMEZ (docs/ORNEKLER.md).
    kontrol("k yakit tukenmesiyle duser", r["k"][-1] < r["k"][0], "-> %s" % [round(x, 4)
                                                                            for x in r["k"]])


HIZLI = [test_butun_ornekler_kapidan_gecer, test_vver_kor_163_demet, test_vver_demetleri,
         test_sfr_kutle_korunumu, test_sfr_kor_sayilari, test_lct008, test_beavrs,
         test_tam_kor_varsayilani, test_ceyrek_kor, test_beavrs_cok_turlu_guc]
YAVAS = [test_yavas_yeni_ornekler_kosar, test_yavas_ceyrek_tam_esit, test_yavas_gd_sogan_kabugu]
VERI_GEREKEN = [test_butun_ornekler_kapidan_gecer, test_beavrs_cok_turlu_guc]
ZINCIR_GEREKEN = [test_butun_ornekler_kapidan_gecer, test_yavas_gd_sogan_kabugu]
