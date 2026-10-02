# -*- coding: utf-8 -*-
"""
test_vv_lct.py -- LEU oksit kafes V&V vakalari (v3 Y11; cekirdek/vv/lct.py).

  [VL1] TCA (LEU-COMP-THERM-006) durum tablosu JAERI 1254 Tablo 8-1 ve
        JAERI-Conf 2003-006 Tablo 1 eslemesiyle birebir: 18 durum, 4 adim,
        kafes boyutu ve 20 C kritik su seviyesi.
  [VL2] Birim hucre: su/yakit hacim orani ve H/U atom orani JAERI 1254
        Tablo 2 ile uyumlu (1.50/1.83/2.48/3.00; 4.33/5.28/7.16/8.65).
  [VL3] tca_spec: gelismis (agac) mod; eksenel yigin 30 cm alt su + islak
        H + kuru (144.15 - H); kafes N x N; yapisal denetim hatasiz.
  [VL4] tca_spec referansi: E = 1.0000 +- 0.0020 (ICSBEP; van der Marck 2006),
        seri, kaynak, basitlestirme listesi ve AOA girdisi (oksit, su, h_x).
  [VL5] tca_spec girdiyi degistirmez; bilinmeyen durum numarasi ValueError.
  [VL6] tca_spec OpenMC modeline kurulur (Monte Carlo kosulmaz): UO2 hucresi
        ve N x N kafes var.
"""

import math

from testler.ortak_test import kontrol

# (adim [cm], su/yakit hacim orani, H/U) -- JAERI 1254 Tablo 2
TABLO2 = ((1.849, 1.50, 4.33), (1.956, 1.83, 5.28), (2.150, 2.48, 7.16), (2.293, 3.00, 8.65))
ORAN_TOL = 0.01
H_U_TOL = 0.03


def test_tca_durum_tablosu():
    print("\n[VL1] TCA durum tablosu birincil kaynakla ayni")
    from cekirdek.vv import lct
    durumlar = lct.TCA_DURUMLARI
    kontrol("18 durum, 1..18", [d.no for d in durumlar] == list(range(1, 19)))
    adimlar = sorted({d.adim for d in durumlar})
    kontrol("dort adim", adimlar == [1.849, 1.956, 2.150, 2.293], "-> %s" % adimlar)
    beklenen = {1: (19, 99.45), 4: (17, 114.59), 9: (16, 78.67), 14: (15, 90.75),
                18: (19, 41.54)}
    for no, (n, h) in beklenen.items():
        d = lct.tca_durumu(no)
        kontrol("durum %d: %dx%d, %.2f cm" % (no, n, n, h), (d.n, d.su_seviyesi) == (n, h),
                "-> %s" % (d,))


def test_tca_birim_hucre():
    print("\n[VL2] Birim hucre oranlari JAERI 1254 Tablo 2 ile uyumlu")
    from cekirdek.vv import lct
    for adim, oran, h_u in TABLO2:
        hucre = lct.tca_birim_hucre(adim)
        kontrol("p = %.3f: Vsu/Vyakit %.2f" % (adim, oran),
                abs(hucre.su_yakit_hacim_orani - oran) < ORAN_TOL,
                "-> %.3f" % hucre.su_yakit_hacim_orani)
        kontrol("p = %.3f: H/U %.2f" % (adim, h_u), abs(hucre.h_u - h_u) < H_U_TOL,
                "-> %.3f" % hucre.h_u)
        kontrol("p = %.3f: H/U-235 > 100" % adim, hucre.h_x > 100.0, "-> %g" % hucre.h_x)


def test_tca_spec_eksenel_kafes():
    print("\n[VL3] tca_spec: eksenel yigin ve kafes")
    from cekirdek import geometri
    from cekirdek.vv import lct
    spec = lct.tca_spec(5)
    d = lct.tca_durumu(5)
    kontrol("gelismis mod", spec["kor"] == {"tur": "agac"})
    katmanlar = spec["geometri"]["kok"]["ic"]["katmanlar"]
    yuk = [k["yukseklik"] for k in katmanlar]
    kontrol("alt su + islak", yuk[:2] == [lct.TCA_ALT_YANSITICI, d.su_seviyesi], "-> %s" % yuk)
    kontrol("kuru = yakit boyu - H", math.isclose(yuk[2], lct.TCA_YAKIT_BOYU - d.su_seviyesi),
            "-> %s" % yuk)
    kafes = spec["geometri"]["kok"]["ic"]["icerik"]
    kontrol("N x N kafes", kafes["boyut"] == [d.n, d.n] and len(kafes["harita"]) == d.n)
    kontrol("adim", kafes["adim"] == d.adim)
    hatalar = [b.mesaj for b in geometri.yapisal_denetim(spec) if b.seviye == "hata"]
    kontrol("yapisal hata yok", not hatalar, "-> %s" % hatalar)


def test_tca_spec_referans():
    print("\n[VL4] tca_spec referansi ve AOA girdisi")
    from cekirdek.vv import lct
    ref = lct.tca_spec(1)["referans"]
    kontrol("E ± σ = 1.0000 ± 0.0020 deney",
            (ref["k"], ref["sigma"], ref["tur"]) == (1.0, 0.0020, "deney"))
    kontrol("seri", ref["seri"] == "LEU-COMP-THERM-006")
    kontrol("birincil kaynak yazili", "JAERI 1254" in ref["kaynak_model"])
    kontrol("E kaynagi yazili", "van der Marck" in ref["kaynak"])
    aciklama = lct.tca_spec(1)["aciklama"]
    kontrol("basitlestirmeler aciklamada", len(lct.TCA_BASITLESTIRMELERI) >= 4
            and all(b in aciklama for b in lct.TCA_BASITLESTIRMELERI))
    from cekirdek import ornek_bilgi
    kontrol("meta sozlesmesi temiz", not ornek_bilgi.dogrula_meta(lct.tca_spec(1)),
            "-> %s" % ornek_bilgi.dogrula_meta(lct.tca_spec(1)))
    girdi = ref["aoa_girdi"]
    kontrol("AOA girdisi oksit/su", (girdi["fiziksel_bicim"], girdi["yansitici"])
            == ("oksit", "su"))
    kontrol("h_x birim hucreden", abs(girdi["h_x"] - lct.tca_birim_hucre(1.849).h_x) < 1e-6)


def test_tca_spec_saf():
    print("\n[VL5] tca_spec saf; gecersiz durum reddedilir")
    from cekirdek.vv import lct
    once = lct.tca_durumu(3)
    a, b = lct.tca_spec(3), lct.tca_spec(3)
    a["malzemeler"].clear()
    kontrol("her cagri yeni nesne", bool(b["malzemeler"]))
    kontrol("durum tablosu degismez", lct.tca_durumu(3) == once)
    try:
        lct.tca_spec(19)
        reddedildi = False
    except ValueError:
        reddedildi = True
    kontrol("durum 19 -> ValueError", reddedildi)


def test_tca_spec_kurulur():
    print("\n[VL6] tca_spec OpenMC modeline kurulur")
    from cekirdek import kurucu, sema
    from cekirdek.vv import lct
    model, bilgi = kurucu.kur(sema.tamamla(lct.tca_spec(14)))
    uo2 = bilgi["malzemeler"]["uo2_tca"]
    hucreler = model.geometry.get_all_cells().values()
    kontrol("UO2 hucresi", any(h.fill is uo2 for h in hucreler))
    kafesler = model.geometry.get_all_lattices().values()
    kontrol("15x15 kafes", any(tuple(k.shape) == (15, 15) for k in kafesler),
            "-> %s" % [tuple(k.shape) for k in kafesler])


def test_tca_varyantlari():
    print("\n[VL7] Duyarlilik varyantlari: alt_tapa (Al tapa katmani), u234 (U-234 eklenir)")
    from cekirdek.vv import lct
    temel, tapa, u234 = (lct.tca_spec(1, v) for v in (None, "alt_tapa", "u234"))
    katman = [k["ad"] for k in tapa["geometri"]["kok"]["ic"]["katmanlar"]]
    kontrol("alt_tapa katmani", "alt tapa" in katman, "-> %s" % katman)
    toplam = [sum(k["yukseklik"] for k in s["geometri"]["kok"]["ic"]["katmanlar"])
              for s in (temel, tapa)]
    kontrol("toplam yukseklik ayni", math.isclose(toplam[0], toplam[1]), "-> %s" % toplam)

    def yakit(s):
        m = [m for m in s["malzemeler"] if m["ad"] == "uo2_tca"][0]
        return {b["isim"]: b["miktar"] for b in m["bilesim"]}
    y0, y1 = yakit(temel), yakit(u234)
    kontrol("temelde U-234 yok", "U234" not in y0)
    kontrol("u234: U-234/U-235 orani", math.isclose(y1["U234"] / y1["U235"], lct.U234_U235_ORANI))
    kontrol("u234: toplam U korunur", math.isclose(y1["U234"] + y1["U238"], y0["U238"]))
    kontrol("varyant kaynakta yazar", "u234" in u234["referans"]["kaynak"])


HIZLI = [test_tca_varyantlari, test_tca_durum_tablosu, test_tca_birim_hucre, test_tca_spec_eksenel_kafes,
         test_tca_spec_referans, test_tca_spec_saf, test_tca_spec_kurulur]
YAVAS = []
