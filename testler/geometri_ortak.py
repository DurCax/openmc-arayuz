# -*- coding: utf-8 -*-
"""
================================================================================
 testler/geometri_ortak.py  --  Dalga G test fikstürleri (G-1 sahibi; digerleri okur)
================================================================================

 Hedef duzenekler (docs/GEOMETRI_MODELI.md §4) ve G-1 yeni duzenekleri:
   (a) 5x5 kare cekirdek + altigen blok halkasi   duzenek_a(yakit_blok=False)
   (b) altigen kor + yansiticida 6 tambur          duzenek_b()
   (c) kare kafesli kor + silindirik yansiticida 4 tambur  duzenek_c()
   (d) altigen ve kare kesitli pinlerden birer demet       duzenek_d(sekil)
   (e) ceyrek kor: iki yuz reflective + iki yuz vacuum     duzenek_e_ceyrek(), duzenek_e_tam()
 Malzeme/cubuk/demet tanimlari ornekler/ dosyalarindan kopyalanir (ornekler
 degismez). Ayarlar kisa MC icindir (parcacik az).
================================================================================
"""

import copy
import json
import os

from testler.ortak_test import ORNEK


def ornek_ham(ad):
    """ornekler/<ad>.json ham sozlugu (goc/tamamla yok)."""
    with open(os.path.join(ORNEK, ad + ".json"), encoding="utf-8") as f:
        return json.load(f)


def malzeme(ornek, ad, yeni_ad=None):
    """Bir ornekten malzeme tanimi kopyasi (istege bagli yeni adla)."""
    m = copy.deepcopy(next(x for x in ornek_ham(ornek)["malzemeler"] if x["ad"] == ad))
    if yeni_ad:
        m["ad"] = yeni_ad
    return m


def _taban(ad, malzemeler, cubuklar=(), demetler=(), tamburlar=()):
    from cekirdek import sema
    spec = sema.yeni_spec(ad)
    spec["malzemeler"] = list(malzemeler)
    spec["cubuklar"] = copy.deepcopy(list(cubuklar))
    spec["demetler"] = copy.deepcopy(list(demetler))
    spec["tamburlar"] = copy.deepcopy(list(tamburlar))
    spec["kor"] = {"tur": "agac"}
    spec["ayarlar"].update(parcacik=2000, cevrim=40, pasif=15, tohum=1)
    spec["ayarlar"]["kaynak"] = {"tur": "kutu", "alt": None, "ust": None}
    spec["ayarlar"]["entropi_mesh"] = {"var": False, "boyut": [1, 1, 1]}
    return spec


def pwr_kutuphane():
    """pwr_ceyrek_kor: demet_24, demet_31 (17x17, adim 1.26) ve malzemeleri."""
    ham = ornek_ham("pwr_ceyrek_kor")
    return ham["malzemeler"], ham["cubuklar"], ham["demetler"]


def duzenek_a(yakit_blok=False):
    """(a) 5x5 kare cekirdek + altigen blok halkasi (§4.1). yakit_blok=True:
    halka bloklarinin icerigi yakit (demet_24 blogu) -- §15.3."""
    malz, cub, dem = pwr_kutuphane()
    malz = list(malz) + [malzeme("sfr_altigen", "ss316", "ss304")]
    blok_ic = ({"tur": "bilesen", "ad": "demet_24"} if yakit_blok
               else {"tur": "malzeme", "ad": "ss304"})
    blok = {"tur": "kap", "id": "blok",
            "kesit": {"sekil": "altigen", "yonelim": "y", "apotem": 14.8},
            "ic": blok_ic, "halkalar": [], "dis": {"tur": "malzeme", "ad": "su"},
            "yerlesimler": [] if yakit_blok else [
                {"ad": "blok_kanali", "mod": "liste", "konumlar": [[0.0, 0.0]],
                 "kesit": {"sekil": "silindir", "yaricap": 3.0},
                 "icerik": {"tur": "malzeme", "ad": "su"}}]}
    spec = _taban("G-1 (a) kare cekirdek + altigen blok halkasi", malz, cub, dem)
    spec["geometri"] = {
        "parcalar": [{"ad": "celik_blok", "dugum": blok}],
        "kok": {
            "tur": "kap", "id": "kok",
            "kesit": {"sekil": "altigen", "yonelim": "x", "apotem": 121.2436},
            "ic": {"tur": "kafes", "id": "blok_kafesi", "sekil": "altigen", "adim": 30.0,
                   "halka_sayisi": 5, "yonelim": "x",
                   "harita": ["B" * 24, "B" * 18, "B" * 12, "." * 6, "."],
                   "anahtar": {"B": {"tur": "bilesen", "ad": "celik_blok"}},
                   "dis": {"tur": "malzeme", "ad": "su"}},
            "yerlesimler": [
                {"ad": "kare_cekirdek", "mod": "liste", "konumlar": [[0.0, 0.0]],
                 "kesit": {"sekil": "dikdortgen", "boyut": [107.1, 107.1]},
                 "icerik": {"tur": "kafes", "id": "cekirdek_kafesi", "sekil": "kare",
                            "adim": 21.42, "boyut": [5, 5],
                            "harita": ["BABAB", "ABABA", "BABAB", "ABABA", "BABAB"],
                            "anahtar": {"A": {"tur": "bilesen", "ad": "demet_24"},
                                        "B": {"tur": "bilesen", "ad": "demet_31"}},
                            "dis": {"tur": "malzeme", "ad": "su"}}}],
            "halkalar": [{"kalinlik": 20.0, "icerik": {"tur": "malzeme", "ad": "su"}}],
            "yukseklik": None, "sinir": {"yan": "vacuum"}},
        "gruplar": []}
    return spec


def sfr_kutuphane():
    """sfr_altigen: demet_hex (7 halka, adim 0.9, pin 'y') ve malzemeleri."""
    ham = ornek_ham("sfr_altigen")
    return ham["malzemeler"], ham["cubuklar"], ham["demetler"]


def duzenek_b():
    """(b) altigen kor + yansitici halkada 6 tambur (§4.2)."""
    malz, cub, dem = sfr_kutuphane()
    malz = [m for m in malz if m["ad"] != "b4c"] + [
        malzeme("sfr_altigen", "ss316", "celik"), malzeme("tamburlu_kor", "b4c")]
    tambur = {"ad": "tambur_b4c", "yaricap": 6.0, "govde_malzeme": "celik",
              "emici_malzeme": "b4c", "emici_ic_yaricap": 4.5, "emici_aci": 120.0}
    spec = _taban("G-1 (b) altigen kor + 6 tambur", malz, cub, dem, [tambur])
    spec["geometri"] = {
        "parcalar": [],
        "kok": {
            "tur": "kap", "id": "kok", "kesit": {"sekil": "kafes_zarfi"},
            "ic": {"tur": "kafes", "id": "kor_kafesi", "sekil": "altigen", "adim": 10.26,
                   "halka_sayisi": 3, "yonelim": "x",
                   "harita": ["D" * 12, "D" * 6, "D"],
                   "anahtar": {"D": {"tur": "bilesen", "ad": "demet_hex"}}},
            "yerlesimler": [],
            "halkalar": [
                {"dis": {"sekil": "altigen", "yonelim": "x", "apotem": 48.69},
                 "icerik": {"tur": "malzeme", "ad": "celik"},
                 "yerlesimler": [
                     {"ad": "tambur_halkasi", "mod": "halka", "sayi": 6,
                      "merkez_yaricap": 36.0, "baslangic_acisi": 30.0,
                      "icerik": {"tur": "bilesen", "ad": "tambur_b4c"},
                      "bakis": {"tur": "merkez", "merkez": [0.0, 0.0]}}]}],
            "yukseklik": 80.0,
            "sinir": {"yan": "vacuum", "alt": "vacuum", "ust": "vacuum"}},
        "gruplar": [{"ad": "tamburlar", "tur": "donme", "deger": 180.0,
                     "uyeler": ["tambur_halkasi"]}]}
    return spec


def duzenek_c():
    """(c) kare kafesli kor + silindirik yansiticida 4 tambur (§4.3)."""
    malz, cub, dem = pwr_kutuphane()
    malz = list(malz) + [malzeme("tamburlu_kor", "berilyum"), malzeme("tamburlu_kor", "b4c")]
    tambur = {"ad": "tambur_b4c", "yaricap": 8.0, "govde_malzeme": "berilyum",
              "emici_malzeme": "b4c", "emici_ic_yaricap": 6.5, "emici_aci": 120.0}
    spec = _taban("G-1 (c) kare kafesli kor + 4 tambur", malz, cub, dem, [tambur])
    spec["geometri"] = {
        "parcalar": [],
        "kok": {
            "tur": "kap", "id": "kok", "kesit": {"sekil": "dikdortgen", "boyut": [64.26, 64.26]},
            "ic": {"tur": "kafes", "id": "kor_kafesi", "sekil": "kare", "adim": 21.42,
                   "boyut": [3, 3], "harita": ["ABA", "BAB", "ABA"],
                   "anahtar": {"A": {"tur": "bilesen", "ad": "demet_24"},
                               "B": {"tur": "bilesen", "ad": "demet_31"}},
                   "dis": {"tur": "malzeme", "ad": "berilyum"}},
            "yerlesimler": [],
            "halkalar": [
                {"dis": {"sekil": "silindir", "yaricap": 80.0},
                 "icerik": {"tur": "malzeme", "ad": "berilyum"},
                 "yerlesimler": [
                     {"ad": "tamburlar4", "mod": "halka", "sayi": 4, "merkez_yaricap": 60.0,
                      "baslangic_acisi": 45.0, "icerik": {"tur": "bilesen", "ad": "tambur_b4c"}}]}],
            "yukseklik": 200.0,
            "sinir": {"yan": "vacuum", "alt": "vacuum", "ust": "vacuum"}},
        "gruplar": [{"ad": "tamburlar", "tur": "donme", "deger": 180.0,
                     "uyeler": ["tamburlar4"]}]}
    return spec


def duzenek_d(sekil):
    """(d) kesiti 'kare' ya da 'altigen' pinlerden bir demet (tek demet, sonsuz
    kafes). Kare pin kare kafeste (17x17), altigen pin altigen kafeste (pin
    kesiti yonelimi = ters(kafes yonelimi): eleman hucresiyle ayni yonde)."""
    if sekil == "kare":
        malz, cub, dem = pwr_kutuphane()
        pin = copy.deepcopy(next(c for c in cub if c["ad"] == "yakit_24"))
        pin.update(ad="yakit_kare", kesit="kare")
        kil = copy.deepcopy(next(c for c in cub if c["ad"] == "kilavuz_boru"))
        kil.update(ad="kilavuz_kare", kesit="kare")
        d = copy.deepcopy(next(x for x in dem if x["ad"] == "demet_24"))
        d.update(ad="demet_kare_pin", anahtar={"y": "yakit_kare", "k": "kilavuz_kare",
                                              "e": "kilavuz_kare"})
        spec = _taban("G-1 (d) kare kesitli pin demeti", malz, [pin, kil], [d])
        kesit = {"sekil": "dikdortgen", "boyut": [21.42, 21.42]}
    else:
        malz, cub, dem = sfr_kutuphane()
        pin = copy.deepcopy(next(c for c in cub if c["ad"] == "yakit_cubugu"))
        pin.update(ad="yakit_altigen", kesit="altigen", kesit_yonelim="x")
        emi = copy.deepcopy(next(c for c in cub if c["ad"] == "emici_cubuk"))
        emi.update(ad="emici_altigen", kesit="altigen", kesit_yonelim="x")
        d = copy.deepcopy(dem[0])
        d.update(ad="demet_altigen_pin", anahtar={"y": "yakit_altigen", "e": "emici_altigen"})
        spec = _taban("G-1 (d) altigen kesitli pin demeti", malz, [pin, emi], [d])
        apotem = 6 * 0.9 * 3 ** 0.5 / 2 + 0.45
        kesit = {"sekil": "altigen", "yonelim": "y", "apotem": apotem}
    spec["geometri"] = {
        "parcalar": [], "gruplar": [],
        "kok": {"tur": "kap", "id": "kok", "kesit": kesit,
                "ic": {"tur": "bilesen", "ad": d["ad"]}, "yerlesimler": [], "halkalar": [],
                "yukseklik": None,
                "sinir": {"yan": "reflective", "alt": "reflective", "ust": "reflective"}}}
    return spec


def _kucuk_kor(harita, boyut, yuzler=None, yan="vacuum"):
    malz, cub, dem = pwr_kutuphane()
    spec = _taban("G-1 (e) kucuk kor", malz, cub, dem)
    nx, ny = boyut
    sinir = {"yan": yan, "alt": "reflective", "ust": "reflective"}
    if yuzler:
        sinir["yuzler"] = yuzler
    spec["geometri"] = {
        "parcalar": [], "gruplar": [],
        "kok": {"tur": "kap", "id": "kok",
                "kesit": {"sekil": "dikdortgen", "boyut": [21.42 * nx, 21.42 * ny]},
                "ic": {"tur": "kafes", "id": "kor_kafesi", "sekil": "kare", "adim": 21.42,
                       "boyut": [nx, ny], "harita": harita,
                       "anahtar": {"A": "demet_24", "B": "demet_31", "s": "su"},
                       "dis": {"tur": "malzeme", "ad": "su"}},
                "yerlesimler": [], "halkalar": [], "yukseklik": None, "sinir": sinir}}
    return spec


def duzenek_e_ceyrek():
    """(e) ceyrek kor: -x, -y simetri yuzleri reflective; +x, +y vacuum.
    Tam kor duzenek_e_tam()'in sag-ust ceyregidir (merkez demet ceyrekte)."""
    # satirlar ustten alta; sol-alt kose tam korun merkezine bitisik
    return _kucuk_kor(["Bsss", "ABss", "AABs", "AAAB"], (4, 4),
                      yuzler={"-x": "reflective", "-y": "reflective",
                              "+x": "vacuum", "+y": "vacuum"})


def duzenek_e_tam():
    """(e) tam kor (8x8, dort yuz vacuum): ceyregin aynasal kopyasi."""
    ceyrek = duzenek_e_ceyrek()["geometri"]["kok"]["ic"]["harita"]
    ust = [satir[::-1] + satir for satir in ceyrek]      # ilk satir en ust
    tam = ust + ust[::-1]
    return _kucuk_kor(tam, (8, 8), yan="vacuum")
