# -*- coding: utf-8 -*-
"""
 arayuz/demet/demet_islemleri.py  --  Demet sekmesinin saf islemleri

 arayuz/sekme_demet.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import sekme_demet; sekme_demet.X` aynen calisir.
 Qt gerektirmez; testler/test_parca_demet.py dogrudan sinar.
"""

from collections import Counter

from cekirdek import altigen, sema, uygunluk
from arayuz import izgara
from arayuz.cubuk.parca_islemleri import BOS_ETIKETI, rol_listesi


TUR_ADI = {"kare": "Kare demet", "altigen": "Altıgen demet"}


# ============================================================================
# saf yardimcilar (testler/test_parca_demet.py sinar)
# ============================================================================

def demet_turleri(spec):
    """Bu modelde eklenebilecek demet tipleri (uygunluk.parca_turleri)."""
    t = uygunluk.parca_turleri(spec)
    return tuple(tip for tip in ("kare", "altigen") if t.get("demet_" + tip))

def _harita_adlari(d):
    return izgara.harita_adlara(d.get("harita"), d.get("anahtar"))


def iceriyor(spec, kapsayan, aranan, derinlik=0):
    """'kapsayan' demeti (ic ice) 'aranan' adli parcayi iceriyor mu?"""
    if derinlik > 12 or not kapsayan:
        return False
    if kapsayan == aranan:
        return True
    d = sema.demet_bul(spec, kapsayan)
    if d is None:
        return False
    return any(iceriyor(spec, h, aranan, derinlik + 1)
               for h in set((d.get("anahtar") or {}).values()) if h)


def ic_demet_adaylari(spec, d):
    """
    (uygun, sigmayan): bu demete ic demet olarak konabilecek demetler.
    Aday: AYNI tipte (kare icine kare, altigen icine altigen), kendisi
    olmayan ve onu icermeyen (dongu yok). uygun = zarfi adima sigan;
    sigmayan = tip/dongu uygun ama adim kucuk (dogrula tasma hatasi verirdi).
    """
    from cekirdek import dogrula
    tur = d.get("tur", "kare")
    P = float(d.get("adim") or 0.0) * (1.0 + 1e-9)
    uygun, sigmayan = [], []
    for x in spec.get("demetler", []):
        if (x["ad"] == d["ad"] or x.get("tur", "kare") != tur
                or iceriyor(spec, x["ad"], d["ad"])):
            continue
        gx, gy, dar = dogrula._kafes_olculeri(x)
        (uygun if (dar if tur == "altigen" else max(gx, gy)) <= P else sigmayan).append(x["ad"])
    return uygun, sigmayan


def palet_izinli(spec, d, tum_malzemeler=False):
    """
    Bu demete yerlestirilebilecek adlar (kume). Haritada zaten gecenler
    CAGIRAN tarafindan eklenir (bkz. palet_listesi).
    """
    tur = d.get("tur", "kare")
    izin = {c["ad"] for c in spec.get("cubuklar", [])}
    if tur == "kare" and uygunluk.parca_turleri(spec)["plaka"]:
        izin |= {p["ad"] for p in spec.get("plakalar", [])}
    izin |= set(ic_demet_adaylari(spec, d)[0])
    if tum_malzemeler:
        izin |= {m["ad"] for m in spec.get("malzemeler", [])}
        izin.add(sema.BOSLUK)
    else:
        izin |= set(rol_listesi(spec, "sogutucu"))
        izin |= set(rol_listesi(spec, "moderator"))
    return izin


def palet_listesi(spec, d, tum_malzemeler=False):
    """
    Paletin girdileri [(ad, etiket, rgb, tur_etiketi)] -- izgara.palet_ogeleri
    turler/haric suzgeciyle: yalnizca bu demette uygun olanlar + haritada
    zaten gecenler (veri gizlenmez).
    """
    kullanilan = {a for satir in _harita_adlari(d) for a in satir if a}
    istenen = palet_izinli(spec, d, tum_malzemeler) | kullanilan
    bolum = {"cubuk": "cubuklar", "plaka": "plakalar", "demet": "demetler",
             "malzeme": "malzemeler"}
    turler, haric = [], []
    for tur in ("cubuk", "plaka", "demet", "malzeme"):
        adlar = [x["ad"] for x in spec.get(bolum[tur], [])]
        if any(a in istenen for a in adlar):
            turler.append(tur)
            haric += [a for a in adlar if a not in istenen]
    if sema.BOSLUK in istenen:
        turler.append("bosluk")
    ogeler = izgara.palet_ogeleri(spec, turler=tuple(turler), haric=tuple(haric))
    return [(ad, BOS_ETIKETI if ad == sema.BOSLUK else etiket, rgb, tur_e)
            for ad, etiket, rgb, tur_e in ogeler]


def en_sik_parca(adlar):
    """Haritada en sik gecen parca adi (esitlikte ilk gorulen); bossa None."""
    sayac = Counter(a for satir in adlar for a in satir if a)
    if not sayac:
        return None
    en_cok = max(sayac.values())
    for satir in adlar:
        for a in satir:
            if a and sayac[a] == en_cok:
                return a
    return None


def _plaka_olcusu(p):
    tx = p["plaka_sayisi"] * (2 * p["zarf_kalinlik"] + p["et_kalinlik"]) \
        + (p["plaka_sayisi"] + 1) * p["kanal_kalinlik"]
    ty = p["plaka_genislik"] + 2 * (p.get("yan_levha_kalinlik") or 0.0)
    return tx, ty


def gerekli_adim(spec, d):
    """
    (en_kucuk_adim, sebep) -- haritadaki en buyuk icerigin hucreye sigmasi
    icin gereken adim. dogrula._kafes_icerik_kontrol ile AYNI olcu:
      cubuk     : dis cap (2 x en buyuk sonlu yaricap)
      plaka     : eleman dis olcusunun buyuk kenari
      ic demet  : kare -> zarfin buyuk kenari; altigen -> duz yuzden duz yuze
    """
    from cekirdek import dogrula
    en, sebep = 0.0, ""
    tur = d.get("tur", "kare")
    for ad in {a for satir in _harita_adlari(d) for a in satir if a}:
        olcu, metin = 0.0, ""
        c = sema.cubuk_bul(spec, ad)
        if c is not None:
            olcu = dogrula._cubuk_dis_capi(c) or 0.0
            metin = "'%s' çubuğunun dış çapı" % ad
        elif sema.plaka_bul(spec, ad) is not None:
            olcu = max(_plaka_olcusu(sema.plaka_bul(spec, ad)))
            metin = "'%s' plaka elemanının ölçüsü" % ad
        elif sema.demet_bul(spec, ad) is not None:
            gx, gy, dar = dogrula._kafes_olculeri(sema.demet_bul(spec, ad))
            olcu = dar if tur == "altigen" else max(gx, gy)
            metin = "iç demet '%s' ölçüsü" % ad
        if olcu > en:
            en, sebep = olcu, metin
    return en, sebep


def dis_dolgu_anlamli(spec, d):
    """
    'Kafes disi dolgu' kullaniliyor mu? Kare demet tek_demet modelinin kok
    dolgusuysa (ana dolgu ya da eksenel katman dolgusu) model siniri demet
    zarfidir -- dis bolgeye hic ulasilmaz. Altigen demette kose bosluklari,
    ic ice / tam kor / tamburlu kullaniminda hucre ya da silindir kalanini
    doldurur.
    """
    if d.get("tur", "kare") == "altigen":
        return True
    kor = spec.get("kor") or {}
    if kor.get("tur") != "tek_demet":
        return True
    kok = {kor.get("demet")} | {b.get("dolgu") for b in
                                (kor.get("eksenel") or {}).get("bolgeler") or []}
    if d["ad"] not in kok:
        return True
    ic_ice = any(d["ad"] in (x.get("anahtar") or {}).values()
                 for x in spec.get("demetler", []) if x["ad"] != d["ad"])
    return ic_ice


def _yakit_cubugu(spec):
    """Yeni demetin dolgusu: yakit bolgeli ilk cubuk, yoksa ilk cubuk."""
    yakit = set(rol_listesi(spec, "yakit"))
    cubuklar = spec.get("cubuklar", [])
    for c in cubuklar:
        if any(b.get("malzeme") in yakit for b in c.get("bolgeler") or []):
            return c
    return cubuklar[0] if cubuklar else None


def yeni_demet(spec, tur, ad):
    """Yakit cubuguyla dolu yeni demet; adim cubuga sigacak kadar."""
    from cekirdek import dogrula
    c = _yakit_cubugu(spec)
    cap = (dogrula._cubuk_dis_capi(c) or 0.0) if c else 0.0
    sog = (rol_listesi(spec, "sogutucu")
           or [m["ad"] for m in spec.get("malzemeler", [])
               if m["ad"] not in rol_listesi(spec, "yakit")]
           or [sema.BOSLUK])[0]
    if tur == "altigen":
        halka = 5
        adim = max(1.0, round(cap * 1.33, 4))
        adlar = [[c["ad"]] * u for u in altigen.halka_uzunluklari(halka)]
        harita, anahtar = izgara.adlardan_harita(adlar)
        return sema.demet_altigen(ad, adim, halka, harita, anahtar, sog)
    n = 5
    adim = max(1.26, round(cap * 1.33, 4))
    harita, anahtar = izgara.adlardan_harita([[c["ad"]] * n for _ in range(n)])
    return sema.demet(ad, adim, [n, n], harita, anahtar, sog)
