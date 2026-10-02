# -*- coding: utf-8 -*-
"""
 test_y4_ayar.py  --  v3 Y4: tukenme ayar okuyucusu ve denetimi
                      (cekirdek/tukenme_ayar.py)

   [Y4-A1] Varsayilanlar: Y4 anahtarlari olmayan spec eski davranisi verir
           (cecm, sogutma yok, surdur/hizli/arama kapali); sema'ya anahtar
           EKLENMEZ.
   [Y4-A2] Zaman plani: yanma adimlari guc yogunluguyla, sogutma adimlari
           kendi birimiyle ve SIFIR gucle.
   [Y4-A3] Transport sayisi: entegrator asamasi (OpenMC _num_stages ile
           ayni), sogutmada transport yok, SI ve hizli kip.
   [Y4-A4] Denetim: bilinmeyen entegrator, gecersiz sogutma, arama
           uyumsuzluklari (SI, hizli kip, tanimsiz hedef, sinir) HATA.
"""

import copy
import os

from testler.ortak_test import ORNEK, kontrol


def _spec():
    from cekirdek import sema
    s = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    s["tukenme"]["var"] = True
    return s


def test_varsayilanlar():
    print("\n[Y4-A1] Y4 anahtarlari yoksa eski davranis; sema'da yok")
    from cekirdek import sema, tukenme_ayar as ta
    t = _spec()["tukenme"]
    kontrol("entegrator cecm", ta.entegrator(t).kod == "cecm")
    kontrol("sogutma yok", ta.sogutma(t) == ([], "d"))
    kontrol("surdur/hizli/arama kapali", not ta.surdur(t) and not ta.hizli_kip(t)
            and not ta.kritik_arama(t).var)
    yeni = set(sema.VARSAYILAN_TUKENME)
    kontrol("sema.VARSAYILAN_TUKENME'ye Y4 anahtari eklenmedi",
            not yeni & {"sogutma", "surdur", "hizli_kip", "kritik_arama", "si_ic_adim"})


def test_zaman_plani():
    print("\n[Y4-A2] zaman plani: yanma + sifir guclu sogutma")
    from cekirdek import tukenme_ayar as ta
    t = _spec()["tukenme"]
    t.update(adimlar=[1.0, 2.0], guc_yogunlugu=30.0, sogutma={"adimlar": [5.0, 1.0], "birim": "a"})
    adimlar, guc = ta.zaman_plani(t)
    kontrol("adimlar", adimlar == [(1.0, "d"), (2.0, "d"), (5.0, "a"), (1.0, "a")], repr(adimlar))
    kontrol("guc", guc == [30.0, 30.0, 0.0, 0.0], repr(guc))


def test_transport_sayisi():
    print("\n[Y4-A3] transport sayisi entegratore gore")
    import openmc.deplete as d
    from cekirdek import tukenme, tukenme_ayar as ta
    t = {"adimlar": [1, 2, 3]}
    for kod, e in ta.ENTEGRATORLER.items():
        kontrol("%s asama = OpenMC %s._num_stages" % (kod, e.sinif),
                e.asama == getattr(d, e.sinif)._num_stages)
    kontrol("cecm: 3x2+1", ta.transport_sayisi(dict(t, entegrator="cecm")) == 7)
    kontrol("cf4: 3x4+1", ta.transport_sayisi(dict(t, entegrator="cf4")) == 13)
    kontrol("sogutma: son transport yok",
            ta.transport_sayisi(dict(t, entegrator="cecm", sogutma={"adimlar": [10]})) == 6)
    kontrol("si_celi: 1 + 3x(10+1)", ta.transport_sayisi(dict(t, entegrator="si_celi")) == 34)
    kontrol("hizli kip: 1", ta.transport_sayisi(dict(t, hizli_kip=True)) == 1)
    kontrol("tukenme.transport_sayisi ayni kaynak",
            tukenme.transport_sayisi({"tukenme": dict(t, entegrator="predictor")}) == 4)


def _hatalar(spec):
    from cekirdek import tukenme_ayar as ta
    return [b.mesaj for b in ta.ayar_bulgulari(spec) if b.seviye == "hata"]


def test_denetim():
    print("\n[Y4-A4] denetim bulgulari")
    s = _spec()
    kontrol("temiz spec: hata yok", _hatalar(s) == [], repr(_hatalar(s)))
    a = copy.deepcopy(s)
    a["tukenme"]["entegrator"] = "yok"
    kontrol("bilinmeyen entegrator", any("entegratör" in m for m in _hatalar(a)))
    a = copy.deepcopy(s)
    a["tukenme"]["sogutma"] = {"adimlar": [1.0], "birim": "MWd/kg"}
    kontrol("sogutma birimi MWd/kg olamaz", len(_hatalar(a)) == 1)
    a["tukenme"]["sogutma"] = {"adimlar": [-1.0]}
    kontrol("negatif sogutma", len(_hatalar(a)) == 1)
    a = copy.deepcopy(s)
    a["tukenme"]["kritik_arama"] = {"var": True, "tur": "bor", "hedef": "su",
                                    "alt": 0, "ust": 1000, "sinir": [0, 3000]}
    kontrol("gecerli bor aramasi", _hatalar(a) == [], repr(_hatalar(a)))
    b = copy.deepcopy(a)
    b["tukenme"]["entegrator"] = "si_celi"
    kontrol("SI + arama hata", any("SI" in m for m in _hatalar(b)))
    b = copy.deepcopy(a)
    b["tukenme"]["hizli_kip"] = True
    kontrol("hizli kip + arama hata", any("MicroXS" in m for m in _hatalar(b)))
    b = copy.deepcopy(a)
    b["tukenme"]["kritik_arama"]["hedef"] = "uo2"
    kontrol("yakita bor aramasi hata", len(_hatalar(b)) == 1, repr(_hatalar(b)))
    b = copy.deepcopy(a)
    b["tukenme"]["kritik_arama"]["ust"] = 5000
    kontrol("tahmin sinir disi hata", len(_hatalar(b)) == 1)
    b = copy.deepcopy(a)
    b["tukenme"]["kritik_arama"].update(tur="cubuk", hedef="yok", sinir=[0, 100], ust=50)
    kontrol("tanimsiz kontrol cubugu hata", any("kontrol" in m for m in _hatalar(b)))


def test_canli_dogrulama():
    print("\n[Y4-A5] canli dogrulama (dogrula.tum_kontroller) Y4 bulgularini icerir; kapi tekrarlamaz")
    from cekirdek import dogrula, tukenme
    s = _spec()
    s["tukenme"]["entegrator"] = "yok"
    mesajlar = [b.mesaj for b in dogrula.tum_kontroller(s, veri_kontrolu=False)]
    kontrol("bilinmeyen entegrator canli listede",
            sum("bilinmeyen entegratör" in m for m in mesajlar) == 1, repr(mesajlar))
    try:
        tukenme.kapi(s, veri_kontrolu=False)
        tum = []
    except dogrula.DogrulamaHatasi as e:
        tum = [b.mesaj for b in e.tum_bulgular]
    kontrol("kapida bir kez", sum("bilinmeyen entegratör" in m for m in tum) == 1, repr(tum))


def test_cubuk_emici_uyarisi():
    print("\n[Y4-A6] cubuk aramasi: yanan emici tukenmeden cikarilir -> gorunur UYARI")
    from cekirdek import sema, tukenme_ayar as ta
    s = sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json"))
    s["tukenme"].update(var=True, kritik_arama={
        "var": True, "tur": "cubuk", "hedef": "kontrol_cubugu", "alt": 20.0, "ust": 80.0,
        "sinir": [0.0, 100.0]})
    uyarilar = [b.mesaj for b in ta.ayar_bulgulari(s) if b.seviye == "uyari"]
    kontrol("b4c icin uyari", any("b4c" in m and "tükenme" in m for m in uyarilar), repr(uyarilar))


HIZLI = [test_varsayilanlar, test_zaman_plani, test_transport_sayisi, test_denetim,
         test_canli_dogrulama, test_cubuk_emici_uyarisi]
