# -*- coding: utf-8 -*-
"""
 test_goc.py  --  M2: sema surumu, goc zinciri (1 -> 2 -> 3), bozuk dosya korumasi

 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri).
"""

import copy
import glob
import json
import os
import shutil
import tempfile

from testler.ortak_test import kontrol, ORNEK
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik


def _yaz(dizin, ad, icerik):
    yol = os.path.join(dizin, ad)
    with open(yol, "w", encoding="utf-8") as f:
        if isinstance(icerik, str):
            f.write(icerik)
        else:
            json.dump(icerik, f, ensure_ascii=False)
    return yol


def _eski_v1():
    """Surum alani olmayan, guc dagilimi eski bicimli bir dosya icerigi."""
    with open(os.path.join(ORNEK, "pwr_pinhucre.json"), encoding="utf-8") as f:
        ham = json.load(f)
    ham.pop("surum", None)
    ham["guc_dagilimi"] = {"var": True, "cubuk": "yakit_cubugu", "bolge": 0}
    return ham


@gereksinim("R-G-02")
def test_goc_zinciri_saf():
    print("\n[GOC1] goc zinciri: 1 -> 3, girdi degismez, alanlar eklenir")
    from cekirdek import goc
    ham = _eski_v1()
    kopya = copy.deepcopy(ham)
    yeni, adimlar = goc.goc_ettir(ham)
    kontrol("girdi degismedi", ham == kopya)
    kontrol("adimlar 1->2, 2->3", adimlar == ["1->2", "2->3"], "-> %s" % adimlar)
    kontrol("surum 3", yeni["surum"] == 3)
    kontrol("geometri None, tamburlar []",
            yeni.get("geometri", "YOK") is None and yeni.get("tamburlar") == [])
    g = yeni["guc_dagilimi"]
    kontrol("guc eski bicim -> cubuklar",
            g.get("cubuklar") == [{"cubuk": "yakit_cubugu", "bolge": 0}]
            and "cubuk" not in g and "bolge" not in g, "-> %s" % g)
    kontrol("kor degismedi", yeni["kor"] == ham["kor"])
    uc, adim3 = goc.goc_ettir(yeni)
    kontrol("surum 3 dosya: adim yok, ayni icerik", adim3 == [] and uc == yeni)


@gereksinim("R-G-02")
def test_goc_hatalari():
    print("\n[GOC2] bozuk / yeni surum dosyalari acik hata verir")
    from cekirdek import goc, sema
    d = tempfile.mkdtemp(prefix="goc_")
    try:
        taban = _eski_v1()
        durumlar = [
            ("bozuk.json", '{"kor": {"tur": "tek_cubuk"', "JSON"),
            ("liste.json", [1, 2, 3], "nesne"),
            ("surum_metin.json", dict(taban, surum="iki"), "sayı değil"),
            ("surum_bool.json", dict(taban, surum=True), "sayı değil"),
            ("surum_kesir.json", dict(taban, surum=2.5), "tam sayı"),
            ("yeni.json", dict(taban, surum=4), "daha yeni"),
            ("korsuz.json", {k: v for k, v in taban.items() if k != "kor"}, "kor"),
            ("kor_liste.json", dict(taban, kor=[1]), "türü yanlış"),
            ("malzeme_nesne.json", dict(taban, malzemeler={"a": 1}), "türü yanlış"),
        ]
        for ad, icerik, parca in durumlar:
            yol = _yaz(d, ad, icerik)
            try:
                sema.yukle(yol)
                sonuc = "HATA YOK"
            except goc.GocHatasi as e:
                sonuc = str(e)
            kontrol("%s -> GocHatasi (%s)" % (ad, parca), parca in sonuc, "-> %s" % sonuc)
        kontrol("GocHatasi bir ValueError (eski yakalayicilar calisir)",
                issubclass(goc.GocHatasi, ValueError))
    finally:
        shutil.rmtree(d, ignore_errors=True)


@gereksinim("R-G-02")
def test_goc_yukle_ve_yedek():
    print("\n[GOC3] yukle surum 3 dondurur; eski dosyanin ustune yazmadan .bak")
    from cekirdek import sema
    d = tempfile.mkdtemp(prefix="goc_")
    try:
        yol = _yaz(d, "eski.json", _eski_v1())
        with open(yol, encoding="utf-8") as f:
            ozgun = f.read()
        spec = sema.yukle(yol)
        kontrol("yuklenen surum = SEMA_SURUM = 3", spec["surum"] == sema.SEMA_SURUM == 3)
        kontrol("yuklenen: geometri None, tamburlar []",
                spec.get("geometri", "YOK") is None and spec.get("tamburlar") == [])
        kontrol("yukleme diske dokunmadi (bak yok)", not os.path.exists(yol + ".bak"))
        sema.kaydet(spec, yol)
        kontrol("eski surumun ustune yazarken .bak yazildi", os.path.exists(yol + ".bak"))
        with open(yol + ".bak", encoding="utf-8") as f:
            kontrol(".bak ozgun icerik", f.read() == ozgun)
        sema.kaydet(spec, yol)
        with open(yol + ".bak", encoding="utf-8") as f:
            kontrol("ikinci kayit yedegi ezmez", f.read() == ozgun)
        yeni = os.path.join(d, "yeni.json")
        sema.kaydet(spec, yeni)
        kontrol("yeni dosyada yedek yok", not os.path.exists(yeni + ".bak"))
        bozuk = _yaz(d, "bozuk.json", "{bozuk")
        sema.kaydet(spec, bozuk)
        kontrol("bozuk dosyanin ustune yazarken de .bak",
                os.path.exists(bozuk + ".bak"))
        kontrol("kaydedilen dosya tekrar yuklenir", sema.yukle(yol)["surum"] == 3)
    finally:
        shutil.rmtree(d, ignore_errors=True)


@gereksinim("R-G-02")
def test_goc_ornekler():
    print("\n[GOC4] 30 ornek (27 sablon + 3 G-4 agac) goc ettirilip yuklenir; kor aynen kalir")
    from cekirdek import sema, goc
    dosyalar = sorted(glob.glob(os.path.join(ORNEK, "*.json")))
    kontrol("30 ornek", len(dosyalar) == 30, "-> %d" % len(dosyalar))
    for yol in dosyalar:
        with open(yol, encoding="utf-8") as f:
            ham = json.load(f)
        spec = sema.yukle(yol)
        yeni, _a = goc.goc_ettir(ham)
        kontrol("%s: surum 3, kor diskteki gibi" % os.path.basename(yol),
                spec["surum"] == 3 and yeni["kor"] == ham["kor"])


def test_agac_modu_yukseklik():
    print("\n[GOC5] gelismis modda sema.kor_yuksekligi yuksek sesle hata verir")
    from cekirdek import sema
    spec = sema.yukle(os.path.join(ORNEK, "tamburlu_kor.json"))
    kontrol("sablon: model_yuksekligi = kor_yuksekligi",
            sema.model_yuksekligi(spec) == sema.kor_yuksekligi(spec["kor"]) == 45.0)
    agac = copy.deepcopy(spec)
    agac["kor"] = {"tur": "agac"}
    agac["geometri"] = {"kok": {"tur": "kap", "kesit": {"sekil": "silindir", "yaricap": 5.0},
                                "ic": {"tur": "malzeme", "ad": "u10mo"},
                                "yukseklik": 12.0, "halkalar": [], "yerlesimler": []},
                        "parcalar": [], "gruplar": []}
    try:
        sema.kor_yuksekligi(agac["kor"])
        sonuc = "hata yok"
    except sema.AgacModuHatasi as e:
        sonuc = "AgacModuHatasi: %s" % e
    kontrol("kor_yuksekligi(agac kor) -> AgacModuHatasi", sonuc.startswith("AgacModuHatasi"),
            "-> %s" % sonuc)
    kontrol("model_yuksekligi agactan", sema.model_yuksekligi(agac) == 12.0,
            "-> %s" % sema.model_yuksekligi(agac))


HIZLI = [test_goc_zinciri_saf, test_goc_hatalari, test_goc_yukle_ve_yedek,
         test_goc_ornekler, test_agac_modu_yukseklik]
YAVAS = []
