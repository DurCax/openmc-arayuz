# -*- coding: utf-8 -*-
"""
 test_yol_metni.py  --  gelismis geometri yollari kullaniciya okunur gorunur

 Hata (Dalga 3 birlesmesi, 01.10.2026): dogrulama bulgularinin yer etiketi
 ("geometri:kok/ic/(1,2)>yansitici_blok") ve tukenme hacim ayrintisi
 ("[y]>yakit_cubugu/bolgeler/0: 1729 × 25.74 cm³; (0,0)>...") arayuzde ham
 kod olarak gorunuyordu; test_dil D1 bunu "ASCII'lestirilmis kelime"
 ('ic') ve "virgullu ondalik" ('(0,0)') olarak yakaladi.
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

from testler.ortak_test import kontrol


def test_geometri_yolu_okunur():
    print("\n[YM1] geometri yolu -> okunur metin (TR)")
    from cekirdek.geometri.yol_metni import okunur
    beklenen = {
        "kok/halkalar/0/icerik": "kök › 1. halka › içerik",
        "kok/ic": "kök › iç",
        "kok/ic/(1,2)>yansitici_blok": "kök › iç › (1, 2) konumu › yansitici_blok",
        "parcalar/0/dugum/yerlesimler/1/icerik": "1. parça › 2. yerleşim › içerik",
        "gruplar/0": "1. grup",
        "[y]>yakit_cubugu/bolgeler/0": "‘y’ harfi › yakit_cubugu › 1. bölge",
        "/geometri/kok/dis": "kök › dış",
        "yerlesimler/tamburlar#0/x/emici": "‘tamburlar’ yerleşimi, 1. öğe › x › emici",
        "yerlesimler/tamburlar#2>tambur_b4c/govde": "‘tamburlar’ yerleşimi, 3. öğe › tambur_b4c › gövde",
    }
    for yol, metin in beklenen.items():
        kontrol("%s -> %s" % (yol, metin), okunur(yol) == metin, "-> %r" % okunur(yol))


def test_yer_etiketi_geometri():
    print("\n[YM2] bulgu yer etiketi geometri yolunu okunur yazar")
    from cekirdek.dogrula._ortak import yer_etiketi
    e = yer_etiketi("geometri:kok/ic/(1,2)>yansitici_blok")
    kontrol("onek ve yol okunur", e == "Geometri: kök › iç › (1, 2) konumu › yansitici_blok",
            "-> %r" % e)
    kontrol("ham kod kalmadi", "/" not in e and "(1,2)" not in e)


def test_hacim_ayrintisi_okunur():
    print("\n[YM3] analitik hacim ayrintisi ham yol icermez")
    from cekirdek import sema, geometri
    from cekirdek.geometri import hacim
    s = sema.yukle("ornekler/altigen_tambur_halkasi.json")
    m = geometri.model(s)
    yakit = next(x["ad"] for x in s["malzemeler"] if x["ad"].lower().startswith("u"))
    a = hacim.analitik(m, yakit).ayrinti
    kontrol("ham yol yok ('/' ve '(i,j)')", "/" not in a and "(0,0)" not in a, "-> %s" % a[:200])


HIZLI = [test_geometri_yolu_okunur, test_yer_etiketi_geometri, test_hacim_ayrintisi_okunur]
YAVAS = []
