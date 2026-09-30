# -*- coding: utf-8 -*-
"""
 test_geometri_tuketici3.py  --  G-2: uygunluk ve tarama agac modunda

 (1) Her ornek geometri.gelismise_gec ile agaca cevrilir: tuketicilerin
     cevaplari (icerik, boyut, sinir, sonsuz ortam, guc cubuklari, tukenme
     hacimleri ve ornek sayisi, malzeme hedefli taramalar) sablonla AYNI.
 (2) Agac duzeneklerinde uygunluk sorulari (grup hedefleri, yuz basina sinir)
     ve tarama parametreleri (grup_donme, grup_daldirma, takma adlar,
     kor_adim, yansitici_kalinlik); sunulan her (tarama, hedef) modeli degistirir.
 Sozlesme: testler/ortak_test.py.
"""

import copy
import glob
import os

from testler.ortak_test import kontrol, ORNEK
from testler import geometri_ortak as go

MALZEME_TARAMALARI = ("yakit_sicaklik", "sogutucu_sicaklik", "malzeme_yogunluk",
                      "void_orani", "bor_ppm", "zenginlik", "kafes_adim", "cubuk_yaricap")


def _ornekler():
    from cekirdek import sema
    return [(os.path.basename(y), sema.yukle(y))
            for y in sorted(glob.glob(os.path.join(ORNEK, "*.json")))]


def _hacim_ozeti(spec):
    from cekirdek import tukenme
    return {a: (round(v["hacim"], 6) if v["hacim"] else None)
            for a, v in tukenme.hacimler(spec).items()}


def _cevaplar(spec):
    from cekirdek import tukenme, uygunluk as u
    c = {"icerik": {k: sorted(v) for k, v in u.geometri_icerigi(spec).items()
                    if k in ("malzeme", "cubuk", "plaka", "demet", "kafesteki_cubuk")},
         "boyut": u.model_boyutu(spec), "sonsuz": u.sonsuz_ortam(spec),
         "alt_ust": (u.sinir_secenekleri(spec, "alt"), u.sinir_secenekleri(spec, "ust")),
         "guc": u.guc_cubuklari(spec), "tukenme": u.tukenme_uygun(spec)[0],
         "ayar": u.ayar_alanlari(spec), "kaynak": u.kaynak_secenekleri(spec),
         "hacim": _hacim_ozeti(spec), "ornek": tukenme.yakit_ornek_sayisi(spec)}
    for t in MALZEME_TARAMALARI:
        c["hedef_" + t] = u.gecerli_hedefler(spec, t)
    return c


def test_gelismise_gecen_ornekler_ayni():
    print("\n[GV1] 27 ornek agaca gecince uygunluk/tukenme cevaplari sablonla ayni")
    from cekirdek import geometri
    farklar, sayi = [], 0
    for ad, spec in _ornekler():
        agac = geometri.gelismise_gec(spec)
        eski, yeni = _cevaplar(spec), _cevaplar(agac)
        fark = [k for k in eski if eski[k] != yeni[k]]
        if fark:
            farklar.append((ad, {k: (eski[k], yeni[k]) for k in fark[:2]}))
        sayi += 1
    kontrol("%d ornekte cevaplar ayni" % sayi, not farklar and sayi >= 27,
            "-> %s" % farklar[:2])


def test_gelismise_gecen_dogrulama_temiz():
    print("\n[GV2] agaca gecen orneklerde dogrulama yeni HATA uretmez")
    from cekirdek import dogrula, geometri
    kotu = []
    for ad, spec in _ornekler():
        eski = {(b.yer, b.mesaj) for b in dogrula.tum_kontroller(spec, veri_kontrolu=False)
                if b.seviye == "hata"}
        yeni = [b for b in dogrula.tum_kontroller(geometri.gelismise_gec(spec), veri_kontrolu=False)
                if b.seviye == "hata"]
        if len(yeni) > len(eski):
            kotu.append((ad, [(b.yer, b.mesaj) for b in yeni][:3]))
    kontrol("gelismis modda yeni HATA yok", not kotu, "-> %s" % kotu[:3])


def test_uygunluk_agac_duzenekleri():
    print("\n[GV3] agac duzeneklerinde uygunluk: grup hedefleri, yuz basina sinir, boyut")
    from cekirdek import uygunluk as u
    b = go.duzenek_b()
    kontrol("(b) grup_donme -> ['tamburlar'], tambur_donme takma ad [None]",
            u.gecerli_hedefler(b, "grup_donme") == ["tamburlar"]
            and u.gecerli_hedefler(b, "tambur_donme") == [None])
    kontrol("(b) kor_adim -> agac kafesi 'kor_kafesi'",
            u.gecerli_hedefler(b, "kor_adim") == ["kor_kafesi"], "-> %s"
            % u.gecerli_hedefler(b, "kor_adim"))
    kontrol("(b) kritik aramada grup_donme var", "grup_donme" in u.gecerli_taramalar(b, "kritik"))
    kontrol("(b) 6 yuzlu yan sinir", len(u.yuz_sinir_secenekleri(b)) == 6)
    c = go.duzenek_c()
    kontrol("(c) silindirik dis sinir: periodic yok, yuz basina sinir yok",
            "periodic" not in u.sinir_secenekleri(c, "yan") and u.yuz_sinir_secenekleri(c) == {})
    e = go.duzenek_e_ceyrek()
    yuz = u.yuz_sinir_secenekleri(e)
    kontrol("(e) dort yuz, periodic sunulur", list(yuz) == ["-x", "+x", "-y", "+y"]
            and "periodic" in yuz["-x"] and u.sinir_secenekleri(e, "+y") == yuz["+y"])
    kontrol("(e) ceyrek kor sonsuz ortam degil (iki yuz vakum)", not u.sonsuz_ortam(e))
    d = go.duzenek_d("kare")
    kontrol("(d) her yuz yansitici, 2B: sonsuz ortam, alt/ust yok",
            u.sonsuz_ortam(d) and u.sinir_secenekleri(d, "alt") == []
            and u.model_boyutu(d) == "2B")
    a = go.duzenek_a()
    kontrol("(a) yansitici_kalinlik hedefi 'kok/halkalar/0'",
            u.gecerli_hedefler(a, "yansitici_kalinlik") == ["kok/halkalar/0"],
            "-> %s" % u.gecerli_hedefler(a, "yansitici_kalinlik"))
    oz = u.model_ozeti(c)
    kontrol("(c) model_ozeti: kafes, tambur, 3B", oz["kafes"] and oz["tambur"]
            and oz["boyut"] == "3B", "-> %s" % oz)
    kontrol("agac kor turu listede", "agac" in u.kor_turleri(c))


def _kontrollu_agac():
    """pwr_kontrol agaca cevrilir; kontrol cubugu bir daldirma grubuna konur."""
    from cekirdek import geometri, sema
    spec = geometri.gelismise_gec(sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json")))
    kc = next(c["ad"] for c in spec["cubuklar"] if c.get("tur") == "kontrol")
    spec["geometri"]["gruplar"] = [{"ad": "Banka A", "tur": "daldirma", "deger": 30.0,
                                    "uyeler": [kc]}]
    return spec, kc


def _model_imzasi(spec):
    import openmc
    from cekirdek import kurucu
    model, _b = kurucu.kur(copy.deepcopy(spec))
    geo = model.geometry
    yuzey = sorted(repr(sorted(s.coefficients.items()))
                   for s in geo.get_all_surfaces().values())
    hucre = sorted((c.name or "", repr(c.translation), repr(c.rotation))
                   for c in geo.get_all_cells().values())
    kafes = sorted(repr(getattr(k, "pitch", None)) for k in geo.get_all_lattices().values())
    del openmc
    return yuzey, hucre, kafes


def test_tarama_agac():
    print("\n[GV4] tarama agac modunda: grup_donme/daldirma, takma adlar, kor_adim, halka")
    from cekirdek import tarama
    b = go.duzenek_b()
    y, _n = tarama.parametre_uygula(b, "grup_donme", "tamburlar", 90.0)
    y2, _n = tarama.parametre_uygula(b, "tambur_donme", None, 90.0)
    kontrol("grup_donme = tambur_donme (tek grup) -> deger 90",
            y["geometri"]["gruplar"][0]["deger"] == 90.0 and y == y2
            and b["geometri"]["gruplar"][0]["deger"] == 180.0)
    iki = copy.deepcopy(b)
    iki["geometri"]["gruplar"].append({"ad": "ikinci", "tur": "donme", "deger": 0.0,
                                       "uyeler": ["tambur_halkasi"]})
    try:
        tarama.parametre_uygula(iki, "tambur_donme", None, 10.0)
        hata = ""
    except ValueError as e:
        hata = str(e)
    kontrol("iki donme grubu: tambur_donme 'grup seçin' HATA", "grup_donme" in hata, hata)
    spec, kc = _kontrollu_agac()
    y, _n = tarama.parametre_uygula(spec, "grup_daldirma", "Banka A", 70.0)
    kontrol("grup_daldirma grubu yazar", y["geometri"]["gruplar"][0]["deger"] == 70.0)
    try:
        tarama.parametre_uygula(spec, "cubuk_daldirma", kc, 50.0)
        hata = ""
    except ValueError as e:
        hata = str(e)
    kontrol("grup uyesi cubukta cubuk_daldirma HATA", "grup_daldirma" in hata, hata)
    for deger in (-1.0, 101.0):
        try:
            tarama.parametre_uygula(spec, "grup_daldirma", "Banka A", deger)
            sinir = False
        except ValueError:
            sinir = True
        kontrol("daldirma %g reddedilir" % deger, sinir)
    e = go.duzenek_e_ceyrek()
    y, _n = tarama.parametre_uygula(e, "kor_adim", "kor_kafesi", 22.0)
    kok = y["geometri"]["kok"]
    kontrol("kor_adim: kafes adimi 22, tam zarf kesiti 4 x 22 olceklendi",
            kok["ic"]["adim"] == 22.0 and kok["kesit"]["boyut"] == [88.0, 88.0], "-> %s"
            % kok["kesit"])
    a = go.duzenek_a()
    y, _n = tarama.parametre_uygula(a, "yansitici_kalinlik", "kok/halkalar/0", 25.0)
    kontrol("yansitici_kalinlik: halka kalinligi 25",
            y["geometri"]["kok"]["halkalar"][0]["kalinlik"] == 25.0)


def test_sunulan_hedefler_modeli_degistirir():
    print("\n[GV5] agac modunda sunulan her (tarama, hedef) kurulan modeli degistirir")
    from cekirdek import tarama, uygunluk as u
    spec, _kc = _kontrollu_agac()
    ornekler = (("b", go.duzenek_b(), "grup_donme", 90.0), ("b", go.duzenek_b(), "kor_adim", 10.5),
                ("a", go.duzenek_a(), "yansitici_kalinlik", 25.0),
                ("e", go.duzenek_e_ceyrek(), "kor_adim", 22.0),
                ("kontrol", spec, "grup_daldirma", 80.0))
    for ad, s, tur, deger in ornekler:
        hedefler = u.gecerli_hedefler(s, tur)
        kontrol("(%s) %s hedefi var" % (ad, tur), bool(hedefler), "-> %s" % hedefler)
        taban = _model_imzasi(s)
        for h in hedefler:
            yeni, _n = tarama.parametre_uygula(s, tur, h, deger)
            kontrol("(%s) %s(%s) modeli degistirir" % (ad, tur, h),
                    _model_imzasi(yeni) != taban)


HIZLI = [test_gelismise_gecen_ornekler_ayni, test_gelismise_gecen_dogrulama_temiz,
         test_uygunluk_agac_duzenekleri, test_tarama_agac, test_sunulan_hedefler_modeli_degistirir]
YAVAS = []
