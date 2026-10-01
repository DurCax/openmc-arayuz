# -*- coding: utf-8 -*-
"""
test_benchmark.py -- kriter (benchmark) paketi: C/E ve hesap-hesap karsilastirmasi.

NE SINANIR
  HIZLI (Monte Carlo yok):
    [BM1] Her kriter orneginde referans (E +/- sigma_e, tur, kaynak) ve bu aracin
          olcumu (C +/- sigma_c, parcacik, sure, is parcacigi, OpenMC, kutuphane)
          var; sigma_c <= 30 pcm.
    [BM2] Kabul: |C - E| <= 3 sqrt(sigma_c^2 + sigma_e^2). Asan bir kriter ancak
          KUTUPHANE_YANLILIGI listesinde ve docs/VV.md'de aciklanmissa kabul edilir.
    [BM3] Deney (tur="deney", C/E) ve hesap-hesap (tur="hesap") referanslari ayri
          etiketli: VVER demet kriteri "hesap", ICSBEP kriterleri "deney"; VV.md'de
          iki ayri tablo.
    [BM4] docs/VV.md tablosu JSON'daki olcumlerle ayni (C degerleri birebir).
  YAVAS (Monte Carlo; her biri <= ~2 dk, 8 is parcacigi):
    [BM5..] Her kriter azaltilmis istatistikle yeniden kosulur: hem referansla
          (3 sigma) hem kayitli olcumle (4 sigma) tutarli olmali.

V&V kumesi (Dalga S-3): ornekler/vv/kriter_*.json dosyalari da (deney) bu
denetimlerden gecer; VV.md deney tablosunda "vv/<dosya>" adiyla yer alir.

Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import glob
import json
import math
import os

from testler.ortak_test import kontrol, gereksinim, KOK, ORNEK, ISLEM_PARCACIGI

VV = os.path.join(KOK, "docs", "VV.md")
SIGMA_C_SINIRI = 30e-5                  # sigma_c <= 30 pcm
KABUL_SIGMA = 3.0

# Kriter ornekleri ve beklenen referans turu.
KRITERLER = {
    "godiva_kriter.json": "deney",
    "kriter_jezebel.json": "deney",
    "kriter_flattop25.json": "deney",
    "kriter_lct008.json": "deney",
    "kriter_vver1000_ugd.json": "hesap",
}
# V&V kumesi (S-3; araclar/vv_kriter_uret.py): hepsi ICSBEP deney kriteri.
KRITERLER.update({"vv/" + os.path.basename(y): "deney"
                  for y in sorted(glob.glob(os.path.join(ORNEK, "vv", "kriter_*.json")))})

# 3 sigma disinda kalan ve sapmasi docs/VV.md'de kutuphane yanliligi olarak
# aciklanan kriterler (dosya -> VV.md'de gecmesi gereken aciklama basligi).
KUTUPHANE_YANLILIGI = {}

# YAVAS kosu istatistigi: (parcacik, cevrim, pasif)
YAVAS_AYAR = {
    "godiva_kriter.json": (20000, 100, 30),
    "kriter_jezebel.json": (20000, 100, 30),
    "kriter_flattop25.json": (20000, 100, 30),
    "kriter_lct008.json": (20000, 90, 30),
    "kriter_vver1000_ugd.json": (20000, 90, 30),
    "vv/kriter_umf001.json": (20000, 100, 30),
    "vv/kriter_lst002a.json": (20000, 90, 30),
}


def _ham(ad):
    with open(os.path.join(ORNEK, ad), encoding="utf-8") as f:
        return json.load(f)


def _fark_sigma(c, sc, e, se):
    return abs(c - e) / math.sqrt(sc ** 2 + se ** 2)


def _vv_metni():
    with open(VV, encoding="utf-8") as f:
        return f.read()


@gereksinim("R-M2-01")
def test_kriter_olcumleri_tam():
    print("\n[BM1] Kriter referanslari ve olcumleri tam, sigma_c <= 30 pcm")
    for ad in sorted(KRITERLER):
        ref = _ham(ad).get("referans") or {}
        olc = ref.get("olcum") or {}
        kontrol("%s: referans k/sigma/tur/kaynak" % ad,
                all(a in ref for a in ("k", "sigma", "tur", "kaynak")), "-> %s" % ref)
        eksik = [a for a in ("k", "sigma", "parcacik", "sure_s", "is_parcacigi",
                             "openmc", "kutuphane") if a not in olc]
        kontrol("%s: olcum alanlari tam" % ad, not eksik, "-> eksik %s" % eksik)
        kontrol("%s: sigma_c <= 30 pcm" % ad, olc.get("sigma", 1.0) <= SIGMA_C_SINIRI,
                "-> %.0f pcm" % (1e5 * olc.get("sigma", 1.0)))


@gereksinim("R-M2-01")
def test_kriter_kabul():
    print("\n[BM2] Kabul: |C-E| <= 3 sqrt(sc^2+se^2) ya da aciklanmis kutuphane yanliligi")
    metin = _vv_metni()
    for ad in sorted(KRITERLER):
        ref = _ham(ad)["referans"]
        olc = ref["olcum"]
        z = _fark_sigma(olc["k"], olc["sigma"], ref["k"], ref["sigma"])
        if z <= KABUL_SIGMA:
            kontrol("%s: C-E = %+.0f pcm (%.2f sigma)" % (ad, 1e5 * (olc["k"] - ref["k"]), z), True)
            continue
        baslik = KUTUPHANE_YANLILIGI.get(ad)
        kontrol("%s: %.2f sigma -- VV.md'de kutuphane yanliligi aciklamasi" % (ad, z),
                bool(baslik) and baslik in metin, "-> aciklama yok")


@gereksinim("R-M2-01")
def test_deney_hesap_ayri():
    print("\n[BM3] Deney (C/E) ve hesap-hesap referanslari ayri etiketli")
    for ad, tur in sorted(KRITERLER.items()):
        kontrol("%s: tur = %s" % (ad, tur), _ham(ad)["referans"]["tur"] == tur)
    metin = _vv_metni()
    kontrol("VV.md: deney tablosu basligi", "## Deney kriterleri (C/E)" in metin)
    kontrol("VV.md: hesap-hesap tablosu basligi", "## Hesap-hesap kriterleri" in metin)
    deney = metin.split("## Deney kriterleri (C/E)")[1].split("## Hesap-hesap kriterleri")[0]
    hesap = metin.split("## Hesap-hesap kriterleri")[1].split("\n## ")[0]
    for ad, tur in sorted(KRITERLER.items()):
        bolum, oteki = (deney, hesap) if tur == "deney" else (hesap, deney)
        kontrol("VV.md: %s yalniz kendi tablosunda" % ad, ad in bolum and ad not in oteki)


@gereksinim("R-M2-01")
def test_vv_tablosu_json_ile_ayni():
    print("\n[BM4] docs/VV.md tablosu JSON olcumleriyle ayni")
    metin = _vv_metni()
    for ad in sorted(KRITERLER):
        olc = _ham(ad)["referans"]["olcum"]
        satir = next((s for s in metin.splitlines() if s.startswith("|") and ad in s), "")
        kontrol("%s: VV.md satiri C = %.5f" % (ad, olc["k"]), ("%.5f" % olc["k"]) in satir,
                "-> %s" % (satir or "satir yok"))
        kontrol("%s: VV.md satiri parcacik %d" % (ad, olc["parcacik"]),
                str(olc["parcacik"]) in satir)


def _yeniden_kos(ad, gecici):
    from cekirdek import kosucu, sema
    spec = sema.yukle(os.path.join(ORNEK, ad))
    a = spec["ayarlar"]
    a["parcacik"], a["cevrim"], a["pasif"] = YAVAS_AYAR[ad]
    r = kosucu.calistir(spec, os.path.join(gecici, "kriter_" + os.path.splitext(
                            os.path.basename(ad))[0]),
                        is_parcacigi=ISLEM_PARCACIGI)
    if not kontrol("%s: kosu basarili" % ad, r["basarili"], "-> %s" % r.get("log")):
        return None
    return kosucu.sonuc_oku(r["statepoint"])["keff"]


def _yavas_kriter(ad):
    def test(gecici):
        print("\n[BM5] %s yeniden kosulur (azaltilmis istatistik)" % ad)
        k = _yeniden_kos(ad, gecici)
        if k is None:
            return
        ref = _ham(ad)["referans"]
        olc = ref["olcum"]
        z_ref = _fark_sigma(k[0], k[1], ref["k"], ref["sigma"])
        z_olc = _fark_sigma(k[0], k[1], olc["k"], olc["sigma"])
        print("   C = %.5f +/- %.5f  (E = %.4f +/- %.4f, kayitli %.5f)"
              % (k[0], k[1], ref["k"], ref["sigma"], olc["k"]))
        kontrol("%s: referansla tutarli (%.2f sigma)" % (ad, z_ref),
                z_ref <= KABUL_SIGMA or ad in KUTUPHANE_YANLILIGI)
        kontrol("%s: kayitli olcumle tutarli (%.2f sigma)" % (ad, z_olc), z_olc <= 4.0)
    test.__name__ = "test_yavas_" + os.path.splitext(os.path.basename(ad))[0]
    return test


test_yavas_godiva_kriter = _yavas_kriter("godiva_kriter.json")
test_yavas_kriter_jezebel = _yavas_kriter("kriter_jezebel.json")
test_yavas_kriter_flattop25 = _yavas_kriter("kriter_flattop25.json")
test_yavas_kriter_lct008 = _yavas_kriter("kriter_lct008.json")
test_yavas_kriter_vver1000_ugd = _yavas_kriter("kriter_vver1000_ugd.json")
test_yavas_vv_umf001 = _yavas_kriter("vv/kriter_umf001.json")
test_yavas_vv_lst002a = _yavas_kriter("vv/kriter_lst002a.json")


HIZLI = [test_kriter_olcumleri_tam, test_kriter_kabul, test_deney_hesap_ayri,
         test_vv_tablosu_json_ile_ayni]
YAVAS = [test_yavas_godiva_kriter, test_yavas_kriter_jezebel, test_yavas_kriter_flattop25,
         test_yavas_kriter_lct008, test_yavas_kriter_vver1000_ugd, test_yavas_vv_umf001,
         test_yavas_vv_lst002a]
