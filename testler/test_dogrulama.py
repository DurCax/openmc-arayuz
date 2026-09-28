# -*- coding: utf-8 -*-
"""
 test_dogrulama.py  --  1-2. dogrulama: temiz ornekler, negatif (bozuk) modeller, S(a,b), yeni kontroller

 testler/test_regresyon.py'den tasindi (Dalga 0; test metinleri aynen).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

import copy
import os

from cekirdek import sema, dogrula
from testler.ortak_test import kontrol
from testler.regresyon_ortak import ORNEK, _ornek_adlari


# ============================================================================
# 1-2. DOGRULAMA
# ============================================================================

def test_dogrulama_temiz():
    print("\n[1] Temiz modeller dogrulamadan hatasiz gecmeli")
    for ad in _ornek_adlari():
        spec = sema.yukle(os.path.join(ORNEK, ad + ".json"))
        b = dogrula.tum_kontroller(spec)
        kontrol(ad, not dogrula.hata_var(b), "(%s)" % dogrula.ozet(b))


def test_dogrulama_negatif():
    print("\n[2] Bozuk modeller yakalanmali")
    temiz = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))

    def dene(baslik, degistir, anahtar):
        s = copy.deepcopy(temiz)
        degistir(s)
        b = dogrula.tum_kontroller(s)
        bulundu = any(anahtar.lower() in x.mesaj.lower() for x in b)
        kontrol(baslik, bulundu)

    def sab_sil(s):
        for m in s["malzemeler"]:
            if m["ad"] == "su":
                m["sab"] = []

    dene("S(a,b)'siz su", sab_sil, "S(α,β)")
    dene("yogunluk yok", lambda s: s["malzemeler"][0]["yogunluk"].update({"deger": None}), "yoğunluk")
    dene("yaricap sirasi", lambda s: s["cubuklar"][0]["bolgeler"].__setitem__(0, sema.bolge(0.9, "uo2")), "artan sırada")
    dene("son bolge kapali", lambda s: s["cubuklar"][0]["bolgeler"].__setitem__(2, sema.bolge(0.8, "su")), "yarıçapı boş olmalı")
    dene("cubuk sigmiyor", lambda s: s["kor"].update({"adim": 0.5}), "adımından")
    dene("tanimsiz malzeme", lambda s: s["cubuklar"][0]["bolgeler"].__setitem__(0, sema.bolge(0.39, "yok")), "tanımsız malzeme")
    dene("olmayan nuklid", lambda s: s["malzemeler"][0].update({"bilesim": [sema.bilesen("Xx999", 1.0, tur="nuklid")]}), "nüklid")
    dene("olmayan S(a,b)", lambda s: s["malzemeler"][2].update({"sab": ["c_Yok"]}), "termal saçılma")
    dene("pasif >= cevrim", lambda s: s["ayarlar"].update({"pasif": 60, "cevrim": 60}), "pasif çevrim")
    dene("gecersiz sinir", lambda s: s["kor"]["sinir"].update({"yan": "xx"}), "geçersiz sınır")
    dene("vacuum sizinti", lambda s: s["kor"]["sinir"].update({"yan": "vacuum"}), "sızıntı")
    dene("zenginlik araligi", lambda s: s["malzemeler"][0]["bilesim"][0].update({"zenginlik": 150.0}), "zenginliği")
    dene("yuksek zenginlik", lambda s: s["malzemeler"][0]["bilesim"][0].update({"zenginlik": 19.75}), "U234")
    dene("kafeste tanimsiz harf",
         lambda s: s.update({"demetler": [sema.demet("d", 1.26, [2, 2], ["yy", "yz"], {"y": "yakit_cubugu"}, "su")]}),
         "tanımsız harf")
    dene("kafes satir uzunlugu",
         lambda s: s.update({"demetler": [sema.demet("d", 1.26, [3, 2], ["yy", "yy"], {"y": "yakit_cubugu"}, "su")]}),
         "karakter")


def test_sab_yanlis_alarm():
    """S(a,b) kontrolu karbon iceren alasimlarda yanlis alarm vermemeli."""
    print("\n[3e] S(a,b) yanlis alarm kontrolu")
    from cekirdek import malzeme_kutup as mk
    durumlar = [
        ("SS316 (%0.5 C)", mk.ss316(), False),
        ("B4C", mk.b4c(b10_zenginlik=90), False),
        ("SiC", mk.sic(), False),
        ("Helyum (gaz)", mk.helyum(), False),
        ("Su (S(a,b) yok)", dict(mk.su(), sab=[]), True),
        ("Grafit (S(a,b) yok)", dict(mk.grafit(), sab=[]), True),
        ("Su (S(a,b) var)", mk.su(), False),
        # Zorunlu element kurali: saf Zr {Zr} kumesi {H,Zr}'nin alt kumesiydi
        # ve "zirkonyum hidrur" sayilip c_H_in_ZrH oneriliyordu.
        ("Saf Zr (hidrojen yok)", sema.malzeme(
            "zr", [{"tur": "element", "isim": "Zr", "miktar": 1.0, "birim": "ao"}],
            6.55, "g/cm3", 600.0), False),
        ("Zircaloy-4", mk.zirkaloy4(), False),
        ("B2O3 (hidrojen yok)", sema.malzeme(
            "b2o3", [{"tur": "element", "isim": "B", "miktar": 2.0, "birim": "ao"},
                     {"tur": "element", "isim": "O", "miktar": 3.0, "birim": "ao"}],
            2.46, "g/cm3", 293.6), False),
        ("ZrH (S(a,b) yok)", sema.malzeme(
            "zrh", [{"tur": "element", "isim": "Zr", "miktar": 1.0, "birim": "ao"},
                    {"tur": "element", "isim": "H", "miktar": 1.6, "birim": "ao"}],
            5.6, "g/cm3", 600.0), True),
    ]
    for ad, m, beklenen in durumlar:
        uyardi = bool(dogrula._sab_kontrol(m, "t"))
        kontrol(ad, uyardi == beklenen, "uyari=%s beklenen=%s" % (uyardi, beklenen))
    # grafit dogru etiketlenmeli ("polietilen" degil)
    b = dogrula._sab_kontrol(dict(mk.grafit(), sab=[]), "t")
    kontrol("grafit dogru tanimlanmis", b and "grafit" in b[0].mesaj)


def test_dogrulama_yeni_kontroller():
    """[17] Dogrulayicinin sessiz kaldigi, OpenMC'nin kosuda reddettigi durumlar."""
    print("\n[18r] DOGRULAMA: yeni negatif kontroller")
    p17 = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))

    def bul(s, seviye, parca):
        return [b for b in dogrula.tum_kontroller(s, veri_kontrolu=False)
                if b.seviye == seviye and parca.lower() in b.mesaj.lower()]

    # a) U olmayan elementte zenginlik
    s = copy.deepcopy(p17)
    m = sema.malzeme_bul(s, "uo2")
    o = [b for b in m["bilesim"] if b["isim"] == "O"][0]
    o["zenginlik"] = 4.0
    b = bul(s, "hata", "zenginlik")
    kontrol("a) O elementinde zenginlik -> HATA", bool(b) and b[0].yer == "malzeme:uo2",
            "-> %s" % (b[0].mesaj if b else "yok"))
    kontrol("a) U elementinde zenginlik hata DEGIL", not bul(p17, "hata", "zenginlik"))

    # b) kafes adimi cubuk dis capindan kucuk
    s = copy.deepcopy(p17)
    sema.demet_bul(s, "demet_17x17")["adim"] = 0.9
    b = [x for x in bul(s, "hata", "dış çap") if x.yer == "demet:demet_17x17"]
    kontrol("b) adim 0.9 < cubuk capi 0.95 -> HATA", bool(b), "-> %s" % (b[0].mesaj if b else "yok"))
    sema.demet_bul(s, "demet_17x17")["adim"] = 1.21     # yakit 0.95 sigar, kilavuz 1.204 sigar
    kontrol("b) adim 1.21 hata degil", not [x for x in bul(s, "hata", "dış çap")
                                           if x.yer == "demet:demet_17x17"])

    # c) kafes konumunda ic ice kafes: zarfi adimdan buyuk
    s = copy.deepcopy(p17)
    s["demetler"].append(sema.demet("kor_kafesi", 20.0, [2, 2], ["aa", "aa"],
                                    {"a": "demet_17x17"}, "su"))
    b = [x for x in bul(s, "hata", "iç içe demet") if x.yer == "demet:kor_kafesi"]
    kontrol("c) ic kafes 21.42 cm > adim 20 -> HATA", bool(b),
            "-> %s" % (b[0].mesaj if b else "yok"))
    sema.demet_bul(s, "kor_kafesi")["adim"] = 21.42
    kontrol("c) adim 21.42 hata degil",
            not [x for x in bul(s, "hata", "iç içe demet") if x.yer == "demet:kor_kafesi"])

    # d) periodic: kure ve silindirde gecersiz (OpenMC esleyemez, olculdu).
    #    Altigen prizmada GECERLI -- denetimin aksi iddiasi olcumle curutuldu
    #    (sfr_altigen periodic ile reflective 0.14 sigma icinde ayni k).
    for ad in ("godiva_kriter", "tamburlu_kor"):
        s = sema.yukle(os.path.join(ORNEK, ad + ".json"))
        s["kor"]["sinir"]["yan"] = "periodic"
        kontrol("d) %s + periodic -> HATA" % ad, bool(bul(s, "hata", "periodic")))
    s = sema.yukle(os.path.join(ORNEK, "sfr_altigen.json"))
    s["kor"]["sinir"]["yan"] = "periodic"
    kontrol("d) altigen demet + periodic hata DEGIL", not bul(s, "hata", "periodic"))
    s = copy.deepcopy(p17)
    s["kor"]["sinir"]["yan"] = "periodic"
    kontrol("d) kare demet + periodic hata degil", not bul(s, "hata", "periodic"))

    # e) sabit kaynakta kinetik
    s = sema.yukle(os.path.join(ORNEK, "zirh_kure.json"))
    s["ayarlar"]["kinetik"]["var"] = True
    kontrol("e) sabit kaynak + kinetik -> BILGI", bool(bul(s, "bilgi", "kinetik")))


HIZLI = [
    test_dogrulama_temiz, test_dogrulama_negatif, test_sab_yanlis_alarm,
    test_dogrulama_yeni_kontroller,
]
YAVAS = []
