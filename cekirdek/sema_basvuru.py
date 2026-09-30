# -*- coding: utf-8 -*-
"""
================================================================================
 sema_basvuru.py  --  Spec'teki malzeme basvurulari: kullanim, yeniden adlandirma
================================================================================

 cekirdek/sema.py'den bolundu (Dalga G-1; dosya 800 satir tavanini asiyordu,
 davranis degismedi). Disaridan `sema.kullanilan_malzemeler`,
 `sema.malzeme_adini_degistir` ... olarak kullanilir; sema bu adlari yeniden
 disa verir.

 Gelismis modda (kor.tur == "agac") agactaki malzeme dugumleri de gezilir
 (cekirdek/geometri: basvurular / ad_degistir).
================================================================================
"""

import copy

from cekirdek.sema import BOSLUK, malzeme_bul


def kullanilan_malzemeler(spec):
    """
    Modelde gercekten kullanilan malzeme adlarini dondurur ("bosluk" haric).
    Dogrulama ve renk atamasi icin kullanilir.
    """
    adlar = set()
    for c in spec["cubuklar"]:
        for b in c["bolgeler"]:
            if b.get("malzeme") and b["malzeme"] != BOSLUK:
                adlar.add(b["malzeme"])
        iz = c.get("izleyici_malzeme")
        if iz and iz != BOSLUK:
            adlar.add(iz)
    for p in spec["plakalar"]:
        for k in ("et_malzeme", "zarf_malzeme", "sogutucu", "yan_levha_malzeme"):
            if p.get(k) and p[k] != BOSLUK:
                adlar.add(p[k])
    for d in spec["demetler"]:
        if d.get("dolgu_disi") and d["dolgu_disi"] != BOSLUK:
            adlar.add(d["dolgu_disi"])
        k = d.get("kilif") if d.get("tur") == "altigen" else None
        if isinstance(k, dict) and k.get("malzeme") and k["malzeme"] != BOSLUK:
            adlar.add(k["malzeme"])
    t = spec["kor"].get("tambur") or {}
    if int(t.get("sayi") or 0) > 0:
        for anahtar in ("govde_malzeme", "emici_malzeme"):
            if t.get(anahtar) and t[anahtar] != BOSLUK:
                adlar.add(t[anahtar])
    d = spec["kor"].get("dolgu")
    if d and d != BOSLUK and malzeme_bul(spec, d) is not None:
        adlar.add(d)
    # Kabuklar yalnizca kuresel turde geometriye girer (bkz. KOR_KORUNAN).
    if spec["kor"].get("tur") == "kuresel":
        for k in (spec["kor"].get("kabuklar") or []):
            if k.get("malzeme") and k["malzeme"] != BOSLUK:
                adlar.add(k["malzeme"])
    yans = spec["kor"].get("yansitici") or {}
    # Tamburlu korda yansitici ZORUNLUDUR; kurucu onu "var" alanina bakmadan kurar.
    yans_var = yans.get("var") or spec["kor"].get("tur") == "tamburlu"
    if yans_var and yans.get("malzeme") and yans["malzeme"] != BOSLUK:
        adlar.add(yans["malzeme"])
    return adlar | _agac_malzemeleri(spec)


def _agac_malzemeleri(spec):
    """Gelismis modda agac ve tambur kutuphanesindeki malzeme adlari."""
    if not isinstance(spec.get("geometri"), dict):
        return set()
    from cekirdek.geometri.basvuru import basvurular
    adlar = {b.ad for b in basvurular(spec) if b.tur == "malzeme"}
    for t in spec.get("tamburlar") or []:
        adlar |= {t.get("govde_malzeme"), t.get("emici_malzeme")}
    return {a for a in adlar if a and a != BOSLUK}


# ----------------------------------------------------------------------------
# Malzeme adi degisimi
# ----------------------------------------------------------------------------
#
#  Bir malzeme adi spec'te IKI tur yerde gecer:
#   * yalnizca MALZEME kabul eden alanlar: cubuk bolgeleri ve izleyici,
#     plaka alanlari, demet dolgu_disi, yansitici, kuresel kabuklar, tambur
#     govde/emici, tally malzeme filtreleri, tukenme ek_malzemeler.
#   * GENEL ad alanlari (kurucu._universe_uret: cubuk -> plaka -> demet ->
#     malzeme sirasiyla cozulur): demet ve kor harita anahtarlari, tamburlu
#     kor dolgusu, eksenel katman dolgusu ve katman anahtarlari. Buradaki
#     ad ancak ayni adli cubuk/plaka/demet YOKSA malzemeyi gosterir; varsa
#     o oge kazanir ve bu alanlar DEGISTIRILMEZ.
#  Once arayuz yalnizca cubuk/plaka/demet/yansiticiyi guncelliyordu; kabuk,
#  tambur, kor dolgusu, katman dolgusu, kontrol cubugu izleyicisi ve tally
#  filtresi eski adda kaliyor, model "tanimsiz malzeme" ile kurulamiyordu.
#  Yeni bir alan eklenirse BURAYA da eklenmeli; testler/test_malzeme_sekmesi.py
#  11 ornekte her malzemeyi yeniden adlandirip modelin ayni kuruldugunu olcer.

_MALZEME_BOLUMLERI = (("cubuklar", "çubuk"), ("plakalar", "plaka"),
                      ("demetler", "demet"))


def malzeme_etiketi(m):
    """
    Listelerde gosterilecek malzeme etiketi: "ad — aciklama"; aciklama
    (gorunen_ad) bos ya da adla ayniysa yalnizca ad. Once her liste
    "%s  --  %s" % (ad, gorunen_ad) yaziyordu: tek ad alanli yeni
    malzemelerde "yakit  --  yakit" cikardi.
    """
    ad = m.get("ad") or ""
    aciklama = m.get("gorunen_ad") or ""
    return ad if not aciklama or aciklama == ad else "%s — %s" % (ad, aciklama)


def malzeme_adi_sorunu(spec, ad, haric=None):
    """
    'ad' bir malzemeye verilebilir mi? Sorun varsa kisa Turkce aciklama,
    yoksa None. haric: duzenlenen malzemenin su anki adi (ad degismiyorsa
    her zaman gecerlidir -- eski dosyadaki bir ad cakismasi, ilgisiz bir
    duzenlemeyi kilitlemesin).
    """
    ad = ad if isinstance(ad, str) else ""
    if haric is not None and ad == haric:
        return None
    if not ad.strip():
        return "Malzeme adı boş olamaz."
    if ad != ad.strip():
        return "Ad boşlukla başlayamaz ya da bitemez."
    if ad == BOSLUK:
        return ("'%s' ayrılmış bir addır: geometride Boş (madde yok) anlamına "
                "gelir." % BOSLUK)
    if any(m.get("ad") == ad for m in spec.get("malzemeler") or []):
        return "'%s' adında başka bir malzeme var." % ad
    for bolum, etiket in _MALZEME_BOLUMLERI:
        if any(x.get("ad") == ad for x in spec.get(bolum) or []):
            return ("'%s' adı bir %s için kullanılıyor. Demet ve katman "
                    "seçimlerinde aynı ad iki şeyi gösterirdi." % (ad, etiket))
    return None


def malzeme_adini_degistir(spec, eski, yeni):
    """
    'eski' adli malzemeyi 'yeni' olarak yeniden adlandirir ve spec'teki
    BUTUN referanslari gunceller (yerinde). Malzemenin gorunen_ad'i eski
    adla ayniysa o da degisir.

    DONER degisen referanslarin yol listesi (malzemenin kendi adi haric),
    ornek: ["cubuklar/yakit_cubugu/bolgeler/0", "kor/yansitici"].
    HATA  KeyError  : eski adli malzeme yok
          ValueError: yeni ad gecersiz ya da cakisiyor (malzeme_adi_sorunu),
                      ya da eski ad birden fazla malzemede (hangisi oldugu
                      belirsiz)
    """
    if eski == yeni:
        return []
    adli = [m for m in spec.get("malzemeler") or [] if m.get("ad") == eski]
    if not adli:
        raise KeyError("tanımsız malzeme: %s" % eski)
    if len(adli) > 1:
        raise ValueError("'%s' adında %d malzeme var; önce birini yeniden "
                         "adlandırın." % (eski, len(adli)))
    sorun = malzeme_adi_sorunu(spec, yeni)
    if sorun:
        raise ValueError(sorun)

    yollar = []

    def alan(kap, anahtar, yol):
        if isinstance(kap, dict) and kap.get(anahtar) == eski:
            kap[anahtar] = yeni
            yollar.append(yol)

    def liste(kap, anahtar, yol):
        dizi = kap.get(anahtar) if isinstance(kap, dict) else None
        for i, x in enumerate(dizi or []):
            if x == eski:
                dizi[i] = yeni
                yollar.append("%s/%d" % (yol, i))

    def harita_anahtari(kap, yol):
        esleme = kap.get("anahtar") if isinstance(kap, dict) else None
        for harf in sorted(esleme or {}):
            if esleme[harf] == eski:
                esleme[harf] = yeni
                yollar.append("%s/anahtar/%s" % (yol, harf))

    # malzemenin kendisi
    m = adli[0]
    m["ad"] = yeni
    if m.get("gorunen_ad") == eski:
        m["gorunen_ad"] = yeni

    # --- yalnizca malzeme kabul eden alanlar ---
    for c in spec.get("cubuklar") or []:
        yol = "cubuklar/%s" % c.get("ad")
        for i, b in enumerate(c.get("bolgeler") or []):
            alan(b, "malzeme", "%s/bolgeler/%d" % (yol, i))
        alan(c, "izleyici_malzeme", yol + "/izleyici_malzeme")
    for p in spec.get("plakalar") or []:
        for k in ("et_malzeme", "zarf_malzeme", "sogutucu", "yan_levha_malzeme"):
            alan(p, k, "plakalar/%s/%s" % (p.get("ad"), k))
    for d in spec.get("demetler") or []:
        alan(d, "dolgu_disi", "demetler/%s/dolgu_disi" % d.get("ad"))
        alan(d.get("kilif"), "malzeme", "demetler/%s/kilif" % d.get("ad"))
    kor = spec.get("kor") or {}
    alan(kor.get("yansitici"), "malzeme", "kor/yansitici")
    for i, k in enumerate(kor.get("kabuklar") or []):
        alan(k, "malzeme", "kor/kabuklar/%d" % i)
    for k in ("govde_malzeme", "emici_malzeme"):
        alan(kor.get("tambur"), k, "kor/tambur/" + k)
    for t in spec.get("tallyler") or []:
        for i, f in enumerate(t.get("filtreler") or []):
            if isinstance(f, dict) and f.get("tur") == "malzeme":
                liste(f, "adlar", "tallyler/%s/filtreler/%d/adlar" % (t.get("ad"), i))
    liste(spec.get("tukenme"), "ek_malzemeler", "tukenme/ek_malzemeler")

    # --- genel ad alanlari: ad baska bir ogeyi gostermiyorsa ---
    golgeli = any(x.get("ad") == eski for bolum, _e in _MALZEME_BOLUMLERI
                  for x in spec.get(bolum) or [])
    if not golgeli:
        for d in spec.get("demetler") or []:
            harita_anahtari(d, "demetler/%s" % d.get("ad"))
        harita_anahtari(kor, "kor")
        alan(kor, "dolgu", "kor/dolgu")
        for i, b in enumerate((kor.get("eksenel") or {}).get("bolgeler") or []):
            alan(b, "dolgu", "kor/eksenel/%d/dolgu" % i)
            harita_anahtari(b, "kor/eksenel/%d" % i)
    return yollar + _agac_adini_degistir(spec, eski, yeni)


def _agac_adini_degistir(spec, eski, yeni):
    """Gelismis mod: tambur kutuphanesi + agactaki malzeme basvurulari (yerinde).
    Malzemeye cozulen kisaltmalar geometri.basvuru ile ayni kuralla degisir."""
    yollar = []
    for t in spec.get("tamburlar") or []:
        for k in ("govde_malzeme", "emici_malzeme"):
            if t.get(k) == eski:
                t[k] = yeni
                yollar.append("tamburlar/%s/%s" % (t.get("ad"), k))
    if not isinstance(spec.get("geometri"), dict):
        return yollar
    from cekirdek.geometri.basvuru import agac_adini_degistir
    # ad cozumu malzeme listesine bakar: yeniden adlandirilmis listeyle eski
    # adi bulabilmek icin gecici olarak eski adi goster
    m = malzeme_bul(spec, yeni)
    m["ad"] = eski
    try:
        agac, agac_yollari = agac_adini_degistir(spec, "malzeme", eski, yeni)
    finally:
        m["ad"] = yeni
    spec["geometri"] = agac
    return yollar + [y.lstrip("/") for y in agac_yollari]


def malzeme_referanslari(spec, ad):
    """
    'ad' malzemesinin spec'te gectigi yerler (malzeme_adini_degistir'in
    guncelleyecegi yollar); spec DEGISMEZ. Silme onayinda kullanilir.
    """
    if malzeme_bul(spec, ad) is None:
        return []
    kopya = copy.deepcopy(spec)
    # yalnizca bu malzeme kalsin: ad cakismasi/cift ad yeniden adlandirmayi
    # engellemesin (referans yollari malzeme listesine bagli degildir)
    kopya["malzemeler"] = [m for m in kopya.get("malzemeler") or [] if m.get("ad") == ad][:1]
    gecici = "\x00silme_denetimi"
    while any(x.get("ad") == gecici for b, _e in _MALZEME_BOLUMLERI
              for x in kopya.get(b) or []):
        gecici += "_"
    return malzeme_adini_degistir(kopya, ad, gecici)
