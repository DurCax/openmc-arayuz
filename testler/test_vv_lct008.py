# -*- coding: utf-8 -*-
"""
test_vv_lct008.py -- LEU-COMP-THERM-008 ek durumlari (v3 Y11; cekirdek/vv/lct008.py).

  [VL8a] harita_uret: konum merkezindeki evren kimligi harfe cevrilir
         (1 su, 2 yakit, 3 pyrex, 5 Al2O3); ilk satir en ust (+y); bilinmeyen
         evren ValueError (sessiz su sayilmaz).
  [VL8b] spec_olustur: sablon (durum 1) degismez; su malzemesi durumun borlu
         suyuyla, harita yeni haritayla degisir; pertürbe cubuk ve malzemesi
         eklenir; referans E = 1.0007 +- 0.0012, seri, MIT lisansi, h_x.
  [VL8c] birim hucre h_x: H / U-235 (kafes birim hucresi) pozitif ve TCA ile
         ayni mertebede.
  [VL8d] kume.kriter_dosyalari: yeniden uretilmis durum 1 (vv/kriter_lct008_01.json)
         olcumluyse v2 dosyasi (kriter_lct008.json) V&V kumesinde iki kez sayilmaz.
"""

import copy
import json
import os

from testler.ortak_test import kontrol, ORNEK

ADIM = 1.63576


def _sablon():
    with open(os.path.join(ORNEK, "kriter_lct008.json"), encoding="utf-8") as f:
        return json.load(f)


def test_harita_uret():
    print("\n[VL8a] harita_uret: evren -> harf, ust satir +y")
    from cekirdek.vv import lct008

    def bulucu(x, y):
        if y > 0.5 * ADIM:
            return 1            # ust satir su
        return 3 if (abs(x) < 0.1 and abs(y) < 0.1) else 2

    harita = lct008.harita_uret(bulucu, 3, ADIM)
    kontrol("3 satir", len(harita) == 3)
    kontrol("ust satir su", harita[0] == "sss", "-> %s" % harita)
    kontrol("merkez pyrex", harita[1] == "ypy", "-> %s" % harita)
    disari = lct008.harita_uret(lambda x, y: lct008.DISARIDA, 2, ADIM)
    kontrol("tank disi su", disari == ["ss", "ss"], "-> %s" % disari)
    try:
        lct008.harita_uret(lambda x, y: 77, 2, ADIM)
        reddedildi = False
    except ValueError:
        reddedildi = True
    kontrol("bilinmeyen evren ValueError", reddedildi)


def _ornek_spec():
    from cekirdek.vv import lct008
    su = [("H1", 0.066737), ("O16", 0.033369), ("B10", 1.4e-05), ("B11", 5.6e-05)]
    pyrex = [("B10", 9.6e-04), ("B11", 3.9e-03), ("O16", 4.6e-02), ("Si28", 1.6e-02)]
    harita = ["s" * 93] * 46 + ["s" * 46 + "p" + "s" * 46] + ["s" * 93] * 46
    sablon = _sablon()
    once = copy.deepcopy(sablon)
    spec = lct008.spec_olustur(sablon, 5, su, {"pyrex": pyrex}, harita)
    return sablon, once, spec


def test_spec_olustur():
    print("\n[VL8b] spec_olustur: sablon degismez, su/harita/cubuk guncellenir")
    sablon, once, spec = _ornek_spec()
    kontrol("sablon degismedi", sablon == once)
    su = [m for m in spec["malzemeler"] if m["ad"] == "su_borlu"][0]
    b10 = [b["miktar"] for b in su["bilesim"] if b["isim"] == "B10"]
    kontrol("borlu su durumdan", b10 == [1.4e-05], "-> %s" % b10)
    kontrol("pyrex malzemesi", any(m["ad"] == "pyrex" for m in spec["malzemeler"]))
    demet = spec["demetler"][0]
    kontrol("harita yeni", demet["harita"][46][46] == "p")
    kontrol("anahtarda p", demet["anahtar"].get("p") == "pyrex_cubugu",
            "-> %s" % demet["anahtar"])
    kontrol("pyrex cubugu", any(c["ad"] == "pyrex_cubugu" for c in spec["cubuklar"]))
    ref = spec["referans"]
    kontrol("E ± σ", (ref["k"], ref["sigma"], ref["tur"]) == (1.0007, 0.0012, "deney"))
    kontrol("seri", ref["seri"] == "LEU-COMP-THERM-008")
    kontrol("durum adi", "durum 5" in ref["kaynak"], "-> %s" % ref["kaynak"])
    kontrol("MIT lisansi", "MIT" in ref["lisans"])
    kontrol("olcum yok (yeni)", "olcum" not in ref and "aoa" not in ref)
    kontrol("h_x girdisi", ref["aoa_girdi"]["h_x"] > 100.0)


def test_birim_hucre_hx():
    print("\n[VL8c] LCT-008 birim hucre h_x")
    from cekirdek.vv import lct008
    hx = lct008.birim_hucre_h_x(_sablon())
    kontrol("h_x 100-1000", 100.0 < hx < 1000.0, "-> %g" % hx)


def test_vv_yerine():
    print("\n[VL8d] kume: vv/kriter_lct008_01.json olcumluyse kriter_lct008.json kumeden cikar")
    import tempfile
    from cekirdek.vv import kume
    with tempfile.TemporaryDirectory() as kok:
        os.makedirs(os.path.join(kok, "vv"))

        def yaz(goreli, olcumlu):
            ref = {"k": 1.0, "sigma": 0.001, "tur": "deney", "kaynak": "x"}
            if olcumlu:
                ref["olcum"] = {"k": 1.0, "sigma": 0.0002}
            with open(os.path.join(kok, goreli), "w", encoding="utf-8") as f:
                json.dump({"referans": ref}, f)

        yaz("kriter_lct008.json", True)
        yaz("vv/kriter_lct008_01.json", False)
        adlar = [os.path.relpath(y, kok) for y in kume.kriter_dosyalari(kok)]
        kontrol("yerine gecen olcumsuz: ikisi de aday", "kriter_lct008.json" in adlar, "-> %s" % adlar)
        yaz("vv/kriter_lct008_01.json", True)
        adlar = [os.path.relpath(y, kok) for y in kume.kriter_dosyalari(kok)]
        kontrol("olcumlu: eski cikar", "kriter_lct008.json" not in adlar
                and os.path.join("vv", "kriter_lct008_01.json") in adlar, "-> %s" % adlar)


# mit-crpg/benchmarks klonu (MIT): VV_MITCRPG ortam degiskeni ya da Y11 calisma kopyasi.
MITCRPG = os.environ.get("VV_MITCRPG",
                         os.path.expanduser("~/openmc_v3_ciktilar/y11/kaynak/benchmarks"))


def test_depodan_spec():
    print("\n[VL8e] mit-crpg girdisinden durum 1 ve 11 (klon yoksa atlanir)")
    from cekirdek.vv import lct008
    if not os.path.isdir(os.path.join(MITCRPG, "icsbep", "leu-comp-therm-008")):
        print("  [ATLANDI] mit-crpg klonu yok: %s" % MITCRPG)
        return
    s1 = lct008.spec(MITCRPG, 1)
    kontrol("durum 1 haritasi v2 sablonuyla ayni",
            s1["demetler"][0]["harita"] == _sablon()["demetler"][0]["harita"])
    s11 = lct008.spec(MITCRPG, 11)
    j = "".join(s11["demetler"][0]["harita"])
    kontrol("durum 11: 4808 yakit + 144 Al2O3", (j.count("y"), j.count("a")) == (4808, 144),
            "-> %d, %d" % (j.count("y"), j.count("a")))
    adlar = [m["ad"] for m in s11["malzemeler"]]
    kontrol("Al2O3 ve kilifi eklendi", "al2o3" in adlar and "al2o3_kilif" in adlar, "-> %s" % adlar)
    try:
        lct008.spec(MITCRPG, 3)
        reddedildi = False
    except ValueError:
        reddedildi = True
    kontrol("acik modeli olmayan durum 3 reddedilir", reddedildi)


HIZLI = [test_harita_uret, test_spec_olustur, test_birim_hucre_hx, test_vv_yerine,
         test_depodan_spec]
YAVAS = []
