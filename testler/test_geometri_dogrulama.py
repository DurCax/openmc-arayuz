# -*- coding: utf-8 -*-
"""
 test_geometri_dogrulama.py  --  G-2: dogrula/agac ve nokta yoklamasi (M1)

 Kasitli ortusen ve kasitli bos modeller (§8): analitik denetim HATA verir,
 nokta yoklamasi kurulan modelde ortusmeyi/boslugu bulur (kirmizi -> yesil:
 dogrula/agac oncesinde bu modeller temiz geciyordu). (a) duzeneginde kesik
 blok UYARI, gizli konum BILGI; kesik cubuk; altigen demet yonelimi HATA;
 eksenel toplam; periyodik sinir; temiz duzeneklerde HATA yok.
 Yavas: kisa 'openmc --geometry-debug' kosusu ortusmeyi yakalar.
 Sozlesme: testler/ortak_test.py.
"""

import copy
import os

from testler.ortak_test import kontrol, ORNEK
from testler import geometri_ortak as go


def _bulgular(spec, seviye=None):
    from cekirdek import dogrula
    return [b for b in dogrula.kor_kontrol(spec) if seviye is None or b.seviye == seviye]


def _metin(bulgular):
    return [(b.seviye, b.yer, b.mesaj[:90]) for b in bulgular]


def ortusen_model():
    """(c) + ikinci bir liste yerlesimi ilk tamburun ustune: iki delik ortusur."""
    spec = go.duzenek_c()
    h = spec["geometri"]["kok"]["halkalar"][0]
    import math
    x = 60.0 * math.cos(math.radians(45.0))
    h["yerlesimler"].append({"ad": "kanal", "mod": "liste", "konumlar": [[x + 3.0, x]],
                             "kesit": {"sekil": "silindir", "yaricap": 4.0},
                             "icerik": {"tur": "malzeme", "ad": "su"}})
    return spec


def bos_model():
    """Plaka elemani kendi olcusunden buyuk bir kok kesitinde: arada tanimsiz bolge."""
    from cekirdek import sema
    s = sema.yukle(os.path.join(ORNEK, "mtr_plaka.json"))
    p = s["plakalar"][0]
    from cekirdek.geometri.sablon import plaka_olcusu
    gx, gy = plaka_olcusu(p)
    s["kor"] = {"tur": "agac"}
    s["geometri"] = {"parcalar": [], "gruplar": [], "kok": {
        "tur": "kap", "id": "kok", "kesit": {"sekil": "dikdortgen", "boyut": [gx + 2.0, gy + 2.0]},
        "ic": {"tur": "bilesen", "ad": p["ad"]}, "yerlesimler": [], "halkalar": [],
        "yukseklik": None, "sinir": {"yan": "reflective"}}}
    return s


def test_temiz_duzenekler():
    print("\n[GD1] (b)-(e) agac duzeneklerinde geometri HATA'si yok")
    for ad, uret in (("b", go.duzenek_b), ("c", go.duzenek_c),
                     ("d-kare", lambda: go.duzenek_d("kare")), ("e", go.duzenek_e_ceyrek),
                     ("a", go.duzenek_a)):
        h = _bulgular(uret(), "hata")
        kontrol("(%s) HATA yok" % ad, not h, "-> %s" % _metin(h))


def test_ortusme_yakalanir():
    print("\n[GD2] kasitli ortusen model: analitik HATA + nokta yoklamasi ortusme bulur")
    from cekirdek.geometri import yoklama
    spec = ortusen_model()
    h = [b for b in _bulgular(spec, "hata") if "örtüş" in b.mesaj]
    kontrol("delik ortusmesi HATA (yer: yerlesim bolgesi)",
            h and h[0].yer.startswith("geometri:kok/halkalar/0"), "-> %s" % _metin(h))
    sonuc, metin = yoklama.yokla(spec, n=4000, tohum=3)
    kontrol("nokta yoklamasi ortusmeyi bulur ve hucre yolunu yazar",
            len(sonuc.ortusmeler) > 0 and any("yerlesim" in t for t in metin),
            "-> %s | %s" % (yoklama.oran_metni(sonuc), metin[:2]))
    temiz, _m = yoklama.yokla(go.duzenek_c(), n=4000, tohum=3)
    kontrol("ortusmesiz asil model temiz", not temiz.ortusmeler and not temiz.bosluklar)


def test_bosluk_yakalanir():
    print("\n[GD3] kasitli bos model: plaka bolgeyi doldurmuyor -> HATA; yoklama bosluk bulur")
    from cekirdek.geometri import yoklama
    spec = bos_model()
    h = _bulgular(spec, "hata")
    kontrol("'bölgeyi doldurmuyor' HATA", any("doldurmuyor" in b.mesaj for b in h),
            "-> %s" % _metin(h))
    sonuc, metin = yoklama.yokla(spec, n=3000, tohum=2)
    kontrol("nokta yoklamasi bosluk bulur", len(sonuc.bosluklar) > 0,
            "-> %s | %s" % (yoklama.oran_metni(sonuc), metin[:1]))


def test_kesik_ve_gizli():
    print("\n[GD4] (a): kesik blok UYARI, gizli konum BILGI; (a-yakit): kesik cubuk UYARI")
    b = _bulgular(go.duzenek_a())
    uyari = [x for x in b if x.seviye == "uyari" and "kesik konum/bileşen" in x.mesaj]
    kontrol("(a) kesik blok UYARI (sayi + ilk 5 konum)", uyari and "celik_blok" in uyari[0].mesaj,
            "-> %s" % _metin(b))
    bilgi = [x for x in b if x.seviye == "bilgi" and "gizli" in x.mesaj]
    kontrol("(a) gizli konum yoksa BILGI yok ('.' yazilmis)", not bilgi, "-> %s" % _metin(bilgi))
    spec = go.duzenek_a()
    kafes = spec["geometri"]["kok"]["ic"]
    kafes["harita"][3] = "BBBBBB"
    kafes["harita"][4] = "B"
    bilgi = [x for x in _bulgular(spec) if x.seviye == "bilgi" and "gizli" in x.mesaj]
    kontrol("(a) '.' yerine blok: 7 gizli konum BILGI", bilgi and "7" in bilgi[0].mesaj,
            "-> %s" % _metin(bilgi))
    b = _bulgular(go.duzenek_a(yakit_blok=True))
    kontrol("(a-yakit) kesik cubuk UYARI", any(x.seviye == "uyari" and "kesik çubuk" in x.mesaj
                                               for x in b), "-> %s" % _metin(b))


def test_yonelim_eksenel_sinir():
    print("\n[GD5] altigen demet ayni yonelim HATA; eksenel toplam HATA; periyodik sinir HATA")
    spec = go.duzenek_b()
    d = next(x for x in spec["demetler"] if x["ad"] == "demet_hex")
    d["yonelim"] = spec["geometri"]["kok"]["ic"]["yonelim"]
    h = _bulgular(spec, "hata")
    kontrol("(b) demet yonelimi = kafes yonelimi -> HATA", any("yönelim" in x.mesaj for x in h),
            "-> %s" % _metin(h))
    spec = go.duzenek_c()
    kok = spec["geometri"]["kok"]
    kok["ic"]["anahtar"]["A"] = {"tur": "eksenel", "id": "yigin", "icerik": "demet_24",
                                 "katmanlar": [{"ad": "alt", "yukseklik": 50.0, "icerik": "su"},
                                               {"ad": "aktif", "yukseklik": 100.0}]}
    h = _bulgular(spec, "hata")
    kontrol("(c) kok disi yigin 150 != 200 cm -> HATA",
            any("eşit değil" in x.mesaj for x in h), "-> %s" % _metin(h))
    spec = go.duzenek_c()
    spec["geometri"]["kok"]["sinir"]["yan"] = "periodic"
    h = _bulgular(spec, "hata")
    kontrol("(c) silindirik dis sinirda periodic -> HATA",
            any("periodic" in x.mesaj for x in h), "-> %s" % _metin(h))
    spec = copy.deepcopy(ortusen_model())
    spec["geometri"]["kok"]["halkalar"][0]["yerlesimler"][1]["konumlar"] = [[79.0, 0.0]]
    h = _bulgular(spec, "hata")
    kontrol("disa tasan delik -> HATA", any("taşıyor" in x.mesaj for x in h), "-> %s" % _metin(h))


def test_yapisal_once():
    print("\n[GD6] yapisal HATA varsa geometrik denetim atlanir (tanimsiz basvuru, dongu)")
    spec = go.duzenek_c()
    spec["geometri"]["kok"]["ic"]["anahtar"]["A"] = "yok_boyle"
    h = _bulgular(spec, "hata")
    kontrol("tanimsiz basvuru HATA", any("yok_boyle" in x.mesaj for x in h), "-> %s" % _metin(h))
    spec = go.duzenek_a()
    spec["geometri"]["parcalar"][0]["dugum"]["ic"] = {"tur": "bilesen", "ad": "celik_blok"}
    h = _bulgular(spec, "hata")
    kontrol("dongu (parca kendini iceriyor) HATA", any("öngü" in x.mesaj or "kendini" in x.mesaj
                                                        for x in h), "-> %s" % _metin(h))


def test_yavas_geometri_hata_ayikla(gecici):
    print("\n[GD7] kisa 'openmc --geometry-debug' kosusu ortusmeyi yakalar, temiz modeli gecirir")
    from cekirdek.geometri import yoklama
    tamam, metin = yoklama.derin_dogrulama(go.duzenek_c(), os.path.join(gecici, "temiz"),
                                           parcacik=300, cevrim=2)
    kontrol("(c) temiz", tamam, "-> %s" % metin)
    tamam, metin = yoklama.derin_dogrulama(ortusen_model(), os.path.join(gecici, "ortusen"),
                                           parcacik=2000, cevrim=3)
    kontrol("ortusen model yakalandi", not tamam and "verlap" in metin, "-> %s" % metin)


HIZLI = [test_temiz_duzenekler, test_ortusme_yakalanir, test_bosluk_yakalanir,
         test_kesik_ve_gizli, test_yonelim_eksenel_sinir, test_yapisal_once]
YAVAS = [test_yavas_geometri_hata_ayikla]
