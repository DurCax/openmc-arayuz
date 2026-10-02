# -*- coding: utf-8 -*-
"""
test_ornek_bilgi.py -- ornek meta sozlesmesi (cekirdek/ornek_bilgi.py) ve
sema.tamamla'nin meta alanlarini korumasi (D2 on-commit 1).
Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import copy
import dataclasses
import glob
import json
import os
import tempfile

from testler.ortak_test import kontrol, ORNEK
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik


def _ham(ad):
    with open(os.path.join(ORNEK, ad), encoding="utf-8") as f:
        return json.load(f)


def test_tamamla_meta_korur():
    print("\n[OB1] sema.tamamla meta alanlarini korur, diger bilinmeyenleri siler")
    from cekirdek import sema
    ham = sema.yeni_spec("x")
    ham.update(baslik="B", kategori="pwr", seviye="giris", baslik_en="B en",
               aciklama_en="A en", referans={"k": 1.0, "sigma": 0.001, "tur": "deney",
                                             "kaynak": "K"},
               bilinmeyen_alan=3)
    spec = sema.tamamla(copy.deepcopy(ham))
    kontrol("meta alanlari aynen", all(spec.get(a) == ham[a] for a in sema.META_ALANLARI))
    kontrol("meta disi bilinmeyen alan eskisi gibi silinir", "bilinmeyen_alan" not in spec)
    kontrol("meta yoksa eklenmez", not any(a in sema.tamamla(sema.yeni_spec("y"))
                                           for a in sema.META_ALANLARI))


def test_ornek_meta_gidis_donus():
    print("\n[OB2] her ornek: yukle -> kaydet -> yukle meta ve spec aynen")
    from cekirdek import sema
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        ad = os.path.basename(yol)
        ham = _ham(ad)
        spec = sema.yukle(yol)
        with tempfile.TemporaryDirectory() as d:
            ikinci = sema.yukle(sema.kaydet(spec, os.path.join(d, ad)))
        kontrol("%s: meta korunur" % ad,
                all(spec.get(a) == ham.get(a) for a in sema.META_ALANLARI))
        kontrol("%s: gidis-donus esit" % ad, ikinci == spec)


@gereksinim("R-A3-02")
def test_ornekler_meta_temiz():
    print("\n[OB3] her ornegin meta'si dogrula_meta'dan temiz gecer")
    from cekirdek import ornek_bilgi
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        sorun = ornek_bilgi.dogrula_meta(_ham(os.path.basename(yol)))
        kontrol("%s temiz" % os.path.basename(yol), sorun == [], "-> %s" % sorun)


@gereksinim("R-A3-02")
def test_dogrula_meta_hatalari():
    print("\n[OB4] dogrula_meta hatali alanlari adlandirir")
    from cekirdek import ornek_bilgi as ob
    temiz = {"baslik": "B", "kategori": "pwr", "seviye": "orta"}
    kontrol("en kucuk gecerli meta temiz", ob.dogrula_meta(temiz) == [])
    kontrol("sozluk olmayan", ob.dogrula_meta([]) != [])
    durumlar = (
        ({"kategori": "pwr", "seviye": "orta"}, "baslik eksik"),
        (dict(temiz, kategori="lwr"), "kategori"),
        (dict(temiz, seviye="uzman"), "seviye"),
        (dict(temiz, baslik="  "), "baslik boş"),
        (dict(temiz, baslik_en=3), "baslik_en"),
        (dict(temiz, referans=[1]), "referans bir sözlük"),
        (dict(temiz, referans={"k": 1.0, "sigma": 0.1, "tur": "tahmin", "kaynak": "K"}),
         "referans.tur"),
        (dict(temiz, referans={"k": 1.0, "tur": "deney", "kaynak": "K"}), "referans.sigma eksik"),
        (dict(temiz, referans={"k": -1.0, "sigma": 0.1, "tur": "deney", "kaynak": "K"}),
         "referans.k"),
        (dict(temiz, referans={"k": 1.0, "sigma": 0.1, "tur": "deney", "kaynak": "",
                               "x": 1}), "referans.x bilinmeyen"),
        (dict(temiz, referans={"k": 1.0, "sigma": 0.1, "tur": "deney", "kaynak": "K",
                               "olcum": {"k": 1.0}}), "referans.olcum.sigma eksik"),
        (dict(temiz, referans={"k": 1.0, "sigma": 0.1, "tur": "deney", "kaynak": "K",
                               "olcum": {"k": 1.0, "sigma": 0.1, "parcacik": 1.5}}),
         "parcacik"),
        (dict(temiz, referans={"k": 1.0, "sigma": 0.1, "tur": "deney", "kaynak": "K",
                               "olcum": {"k": 1.0, "sigma": 0.1, "openmc": ""}}), "openmc"),
        (dict(temiz, referans={"k": 1.0, "sigma": 0.1, "tur": "deney", "kaynak": "K",
                               "olcum": "x"}), "olcum bir sözlük"),
    )
    for ham, beklenen in durumlar:
        sorun = ob.dogrula_meta(ham)
        kontrol("'%s' bulunur" % beklenen, any(beklenen in s for s in sorun), "-> %s" % sorun)


def test_ornek_bilgisi_okuma():
    print("\n[OB5] ornek_bilgisi: dondurulmus, ham JSON'dan, referans nesnesi")
    from cekirdek import ornek_bilgi as ob
    from testler.regresyon_ortak import REFERANS_K, REFERANS_SAPMA
    pin = ob.ornek_bilgisi(os.path.join(ORNEK, "pwr_pinhucre.json"))
    kontrol("pin: kategori/seviye", (pin.kategori, pin.seviye) == ("pwr", "giris"))
    kontrol("pin: referans regresyon cipasi",
            pin.referans is not None and pin.referans.k == REFERANS_K
            and pin.referans.sigma == REFERANS_SAPMA and pin.referans.tur == "hesap")
    god = ob.ornek_bilgisi(os.path.join(ORNEK, "godiva_kriter.json"))
    kontrol("godiva: deney referansi + olcum",
            god.referans.tur == "deney" and god.referans.k == 1.0
            and god.referans.sigma == 0.001
            and "HEU-MET-FAST-001" in god.referans.kaynak
            # 29.09.2026 olcumu (100k parcacik); eski 0.99957 / parcacik yok
            # kaydi commit 68797a0 ile yerini bu olcume birakti
            and god.referans.olcum.k == 1.00038 and god.referans.olcum.sigma == 0.00025
            and god.referans.olcum.parcacik == 100000)
    kontrol("kor/demet turu", (pin.kor_turu, pin.demet_turu) == ("tek_cubuk", None)
            and ob.ornek_bilgisi(os.path.join(ORNEK, "sfr_altigen.json")).demet_turu
            == "altigen")
    try:
        pin.baslik = "x"
        dondu = False
    except dataclasses.FrozenInstanceError:
        dondu = True
    kontrol("OrnekBilgisi dondurulmus", dondu)
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, "metasiz.json")
        with open(yol, "w", encoding="utf-8") as f:
            json.dump({"ad": "Metasız", "kategori": "yok", "referans": {"k": 1}}, f)
        b = ob.ornek_bilgisi(yol)
        kontrol("meta yoksa baslik 'ad'a duser, gecersizler None",
                (b.baslik, b.kategori, b.seviye, b.referans) == ("Metasız", None, None, None))
        with open(yol, "w", encoding="utf-8") as f:
            json.dump({}, f)
        kontrol("ad da yoksa dosya adi", ob.ornek_bilgisi(yol).baslik == "metasiz")
        with open(yol, "w", encoding="utf-8") as f:
            f.write("[1, 2]")
        try:
            ob.ornek_bilgisi(yol)
            hata = False
        except ValueError:
            hata = True
        kontrol("JSON nesnesi degilse ValueError", hata)


def test_ornek_listesi_ve_kategoriler():
    print("\n[OB6] ornek_listesi: butun ornekler, bozuk dosya atlanir")
    from cekirdek import ornek_bilgi as ob
    liste = ob.ornek_listesi()
    dosyalar = sorted(os.path.basename(p) for p in glob.glob(os.path.join(ORNEK, "*.json")))
    kontrol("her ornek listede", sorted(b.dosya for b in liste) == dosyalar)
    kontrol("hepsinin kategorisi ve seviyesi var",
            all(b.kategori in ob.KATEGORILER and b.seviye in ob.SEVIYELER for b in liste))
    sayilar = ob.kategori_sayilari(liste)
    kontrol("kategori sayilari toplami", sum(sayilar.values()) == len(liste), "-> %s" % sayilar)
    kontrol("siralama kategori sirasini izler",
            [ob.KATEGORILER.index(b.kategori) for b in liste]
            == sorted(ob.KATEGORILER.index(b.kategori) for b in liste))
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "a.json"), "w", encoding="utf-8") as f:
            f.write("{bozuk")
        with open(os.path.join(d, "b.json"), "w", encoding="utf-8") as f:
            json.dump({"ad": "B", "baslik": "B", "kategori": "zirh", "seviye": "ileri"}, f)
        kontrol("bozuk dosya atlanir", [b.dosya for b in ob.ornek_listesi(d)] == ["b.json"])
    kontrol("her kategorinin gorunen adi var", set(ob.KATEGORI_ADLARI) == set(ob.KATEGORILER)
            and set(ob.SEVIYE_ADLARI) == set(ob.SEVIYELER))


def test_meta_tukenmeyi_eskitmez():
    print("\n[OB7] meta alani degisince tukenme sonucu 'eski' sayilmaz")
    from cekirdek import sema, tukenme
    spec = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    degisik = copy.deepcopy(spec)
    degisik.update(baslik="baska", seviye="giris", referans={"k": 1.0})
    kontrol("_fizik_kismi meta'yi disarida birakir",
            tukenme._fizik_kismi(spec) == tukenme._fizik_kismi(degisik))


HIZLI = [test_tamamla_meta_korur, test_ornek_meta_gidis_donus, test_ornekler_meta_temiz,
         test_dogrula_meta_hatalari, test_ornek_bilgisi_okuma, test_ornek_listesi_ve_kategoriler,
         test_meta_tukenmeyi_eskitmez]
YAVAS = []
