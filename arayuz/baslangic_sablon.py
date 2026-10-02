# -*- coding: utf-8 -*-
"""
baslangic_sablon.py -- "Bos basla" sablonlari: her kor turunun ASGARI ama TAM,
gecerli ve kosulabilir modeli (ornekler/ altindaki ilgili ornekten TURETILIR)

arayuz/baslangic.py'den YALNIZ TASINDI (v3 T2, dosya boyu): "bos sablonlar"
bolumu. Davranis aynidir; adlar baslangic'tan da erisilir (baslangic.bos_sablon,
baslangic.SABLON_MALZEMELERI ...). Qt gerektirmez.
"""

import copy
import os

from cekirdek import kaynak, sema, yollar
from cekirdek.ceviri import _

ORNEKLER = yollar.ornekler_dizini()


# ============================================================================
# bos sablonlar
# ============================================================================

def _yukle(dosya):
    return sema.yukle(os.path.join(ORNEKLER, dosya))


def _kullanilmayanlari_at(spec):
    """
    Korun gercekten kullanmadigi cubuk/plaka/kafes/malzemeleri ve haritada
    gecmeyen anahtar harflerini atar. Sablon "sade" olsun: ogrenci ilk
    bakista yalnizca modelde ISE YARAYAN parcalari gorur.
    """
    kor = spec["kor"]
    kok = set()
    ana = sema.ana_dolgu(kor)
    if ana:
        kok.add(ana)
    if kor.get("tur") in sema.HARITALI_KORLAR:
        kullanilan = {h for satir in kor.get("harita") or [] for h in satir}
        kor["anahtar"] = {h: a for h, a in (kor.get("anahtar") or {}).items()
                          if h in kullanilan}
        kok.update(kor["anahtar"].values())
    for _z0, _z1, b in (sema.eksenel_katmanlar(kor) or []):
        kok.update(sema.katman_adaylari(kor, b))

    gerekli, yigin = set(), list(kok)
    while yigin:
        ad = yigin.pop()
        if ad in gerekli:
            continue
        gerekli.add(ad)
        d = sema.demet_bul(spec, ad)
        if d is not None:
            kullanilan = {h for satir in d.get("harita") or [] for h in satir}
            d["anahtar"] = {h: a for h, a in (d.get("anahtar") or {}).items()
                            if h in kullanilan}
            yigin.extend(d["anahtar"].values())

    for liste in ("cubuklar", "plakalar", "demetler"):
        spec[liste] = [x for x in spec.get(liste, []) if x["ad"] in gerekli]
    malz = sema.kullanilan_malzemeler(spec) | {
        ad for ad in gerekli if sema.malzeme_bul(spec, ad) is not None}
    spec["malzemeler"] = [m for m in spec["malzemeler"] if m["ad"] in malz]
    return spec


# Bos sablonlarin malzemeleri KUTUPHANEDEN, parametreleriyle kurulur (Ajan 9
# bulgusu): ornekten kopyalanan elle malzemede "Duzenle" zenginlik/sicaklik
# sormuyordu ve pin ornegi soguk (293.6 K) ama su yogunlugu sicak (0.7) idi.
# Sicakliklar tipik calisma kosulu: PWR yakit 900 K, zarf 600 K, su 580 K.
_PWR = {"zirkaloy": ("zirkaloy4", {"sicaklik": 600.0}),
        "zirkaloy4": ("zirkaloy4", {"sicaklik": 600.0}),
        "helyum": ("helyum", {"sicaklik": 600.0})}
SABLON_MALZEMELERI = {
    "pin": dict(_PWR, uo2=("uo2", {"zenginlik": 3.0, "sicaklik": 900.0}),
                su=("su", {"sicaklik": 580.0, "bor_ppm": 0.0})),
    "demet_kare": dict(_PWR, uo2=("uo2", {"zenginlik": 3.2, "sicaklik": 900.0}),
                       su=("su", {"sicaklik": 580.0, "bor_ppm": 1300.0})),
    "demet_altigen": {"u10mo": ("u10mo", {"zenginlik": 19.75, "sicaklik": 900.0}),
                      "ss316": ("ss316", {"sicaklik": 750.0}),
                      "sodyum": ("sodyum", {"sicaklik": 673.0}),
                      "b4c": ("b4c", {"b10_zenginlik": 90.0, "sicaklik": 750.0})},
    "plaka": {"u3si2_al": ("u3si2_al", {"u_yukleme": 4.8, "zenginlik": 19.75,
                                        "sicaklik": 350.0}),
              "al6061": ("al6061", {"sicaklik": 350.0}),
              "su": ("su", {"sicaklik": 320.0, "bor_ppm": 0.0})},
    "tamburlu": {"u10mo": ("u10mo", {"zenginlik": 19.75, "sicaklik": 400.0}),
                 "berilyum": ("berilyum", {"sicaklik": 400.0}),
                 "b4c": ("b4c", {"sicaklik": 400.0})},
}
SABLON_MALZEMELERI["tam_kor"] = SABLON_MALZEMELERI["demet_kare"]
SABLON_MALZEMELERI["tam_kor_altigen"] = SABLON_MALZEMELERI["demet_altigen"]


def _parametrik_malzemeler(spec, eslem):
    """Sablon malzemelerini kutuphane uretimiyle degistirir (ad ve renk korunur)."""
    from cekirdek import malzeme_kutup as mk
    for i, m in enumerate(spec["malzemeler"]):
        if m["ad"] not in eslem:
            continue
        anahtar, param = eslem[m["ad"]]
        yeni = mk.parametrik_uret(anahtar, dict(param))
        yeni["ad"] = m["ad"]
        if m.get("renk"):
            yeni["renk"] = list(m["renk"])
        spec["malzemeler"][i] = yeni


def _normal_hassasiyet(spec):
    """Ozdeger sablonlari "Normal" hassasiyet onayariyla baslar (Hesap
    ayarlarinda "Özel" degil, bilinen bir onayar gorunsun)."""
    from arayuz.sekme_ayar import HASSASIYET
    a = spec["ayarlar"]
    if a.get("mod", "eigenvalue") != "eigenvalue":
        return
    for anahtar, _ad, n, c, p in HASSASIYET:
        if anahtar == "normal":
            a["parcacik"], a["cevrim"], a["pasif"] = n, c, p


def _sadelestir(spec, ad):
    """Ornekten sablon: ad/aciklama, tally, guc dagilimi, tukenme sifirlanir."""
    spec["ad"] = ad
    spec["aciklama"] = ""
    spec["tallyler"] = []
    spec["guc_dagilimi"] = copy.deepcopy(sema.VARSAYILAN_GUC)
    spec["tukenme"] = copy.deepcopy(sema.VARSAYILAN_TUKENME)
    spec["calistirma"] = copy.deepcopy(sema.VARSAYILAN_CALISTIRMA)
    # Yeni modelde entropi agi modelden turetilir (sema.yeni_spec ile ayni):
    # kullanici 2B'den 3B'ye gecince nz kendiliginden artar.
    ent = spec["ayarlar"].setdefault("entropi_mesh", {})
    ent["otomatik"] = True
    ent["boyut"] = kaynak.entropi_boyutu_otomatik(spec)   # dosyadaki deger de tutarli
    _kullanilmayanlari_at(spec)
    _normal_hassasiyet(spec)
    return spec


def bos_sablon(anahtar):
    """
    Kart anahtari icin ASGARI ama TAM ve gecerli spec (0 dogrulama hatasi,
    kurulur ve cizilir -- testler/test_kabuk.py sinar). Malzemeler
    kutuphaneden parametrik kurulur (SABLON_MALZEMELERI).
    """
    spec = _bos_sablon_ham(anahtar)
    _parametrik_malzemeler(spec, SABLON_MALZEMELERI.get(anahtar, {}))
    return spec


def _bos_sablon_ham(anahtar):
    if anahtar == "pin":
        return _sadelestir(_yukle("pwr_pinhucre.json"), _("Yeni yakıt çubuğu"))
    if anahtar == "demet_kare":
        return _sadelestir(_yukle("pwr_17x17.json"), _("Yeni kare yakıt demeti"))
    if anahtar == "demet_altigen":
        return _sadelestir(_yukle("sfr_altigen.json"), _("Yeni altıgen yakıt demeti"))
    if anahtar == "plaka":
        return _sadelestir(_yukle("mtr_plaka.json"), _("Yeni plaka elemanı"))
    if anahtar == "tamburlu":
        return _sadelestir(_yukle("tamburlu_kor.json"), _("Yeni tamburlu kor"))
    if anahtar == "tam_kor":
        # ornekler/ altinda kare_kafes ornegi yok: 17x17 demetinden 3x3 kor
        # kurulur (su yansitici kusak, yanlarda vakum). Harf atamasi palet
        # editoruyle AYNI kuraldan gecer (izgara.adlardan_harita).
        from arayuz.izgara import adlardan_harita
        spec = _yukle("pwr_17x17.json")
        d = spec["demetler"][0]
        kor = spec["kor"]
        kor["tur"] = "kare_kafes"
        kor["adim"] = round(d["adim"] * d["boyut"][0], 6)
        kor["boyut"] = [3, 3]
        kor["harita"], kor["anahtar"] = adlardan_harita([[d["ad"]] * 3 for _s in range(3)])
        kor["yansitici"] = {"var": True, "kalinlik": 20.0, "malzeme": "su"}
        kor["sinir"] = {"yan": "vacuum", "alt": "reflective", "ust": "reflective"}
        sema.kor_alanlarini_ayikla(kor)
        return _sadelestir(spec, _("Yeni tam kor"))
    if anahtar == "tam_kor_altigen":
        return _sadelestir(_altigen_tam_kor(), _("Yeni altıgen tam kor"))
    # ana pencere bu hatayi kullaniciya gosterir (Şablon kurulamadı)
    raise KeyError(_("boş şablonu olmayan kart: %s") % anahtar)


def _altigen_tam_kor():
    """
    ornekler/ altinda altigen tam kor ornegi yok: SFR altigen demetine
    ss316 kilif eklenir ve 7 demetli (2 halkali) kor kurulur; cevresinde
    15 cm celik yansitici, yanlarda vakum. Kor yonelimi ve adimi tur
    degisimiyle AYNI kuraldan gelir (model_islemleri.altigen_kor_haritasi_kur).
    """
    from arayuz.pencere.model_islemleri import altigen_kor_haritasi_kur
    spec = _yukle("sfr_altigen.json")
    d = spec["demetler"][0]
    # en dis pinler (r = 0.395) + 0.08 cm pay; 0.3 cm kilif; 0.3 cm bosluk
    d["kilif"] = sema.demet_kilifi(10.30, 0.30, "ss316")
    kor = spec["kor"]
    kor["tur"] = "altigen_kafes"
    altigen_kor_haritasi_kur(spec, d["ad"], halka=2)
    kor["adim"] = round(kor["adim"] + 0.30, 6)
    kor["yansitici"] = {"var": True, "kalinlik": 15.0, "malzeme": "ss316"}
    kor["sinir"] = {"yan": "vacuum", "alt": "reflective", "ust": "reflective"}
    sema.kor_alanlarini_ayikla(kor)
    return spec
