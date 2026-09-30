# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/eksenel.py  --  Eksenel yiginlar: yukseklik, dilimler, aktif aralik
================================================================================

 docs/GEOMETRI_MODELI.md §3.7, R7, R8.
   - Katmanlar alttan uste; yigin z = 0 etrafinda merkezlenir.
   - Yuksekligi <= 0 olan katman atlanir (sablonun eksenel_katmanlar davranisi).
   - Kokun ic'indeki yigin model yuksekligini belirler (tek gercek kaynak);
     kok disindaki bir yiginin toplami model yuksekligine esit olmalidir.
   - Aktif (fisil) aralik, hedef cubuk araligi ve lineer guc yuksekligi:
     sablon modunda eski kurucu islevleri (aynen tasindi; kurucu.py'de ince
     sarmalayicilar kalir), gelismis modda agactaki yiginlardan.
================================================================================
"""

from cekirdek import sema as _sema


def gecerli_katmanlar(eksenel):
    """Yuksekligi > 0 olan katmanlar (sirali)."""
    return [k for k in eksenel.get("katmanlar") or []
            if float(k.get("yukseklik") or 0.0) > 0.0]


def dilimler(eksenel):
    """[(z0, z1, katman)] -- yigin z = 0 etrafinda merkezli."""
    katmanlar = gecerli_katmanlar(eksenel)
    toplam = sum(float(k["yukseklik"]) for k in katmanlar)
    z = -toplam / 2.0
    cikti = []
    for k in katmanlar:
        h = float(k["yukseklik"])
        cikti.append((z, z + h, k))
        z += h
    return cikti


def yigin_yuksekligi(eksenel):
    """Gecerli katmanlarin toplam yuksekligi."""
    d = dilimler(eksenel)
    return (d[-1][1] - d[0][0]) if d else 0.0


def kok_yigini(kok):
    """Kokun ic'indeki eksenel yigin ya da None."""
    ic = kok.get("ic")
    return ic if isinstance(ic, dict) and ic.get("tur") == "eksenel" else None


def model_yuksekligi(m):
    """GeometriModeli -> toplam yukseklik [cm] ya da None (2B)."""
    kok = m.kok if hasattr(m, "kok") else m
    yigin = kok_yigini(kok)
    if yigin is not None and gecerli_katmanlar(yigin):
        return yigin_yuksekligi(yigin)
    h = kok.get("yukseklik")
    return float(h) if h else None


# ============================================================================
# SABLON MODU (kurucu.py'den tasindi; davranis ayni)
# ============================================================================

def _sablon_fisil_mi(spec, ad, derinlik=0):
    """
    Spec'teki bir ad (cubuk / plaka / demet / malzeme) fisil malzeme iceriyor mu?

    Geometri kurulmadan cevaplanmasi gerekiyor: kontrol cubugunun daldirma
    ekseni ve arayuzdeki aktif yukseklik gostergesi buna bagli.
    Olcut: Z >= 90 (aktinit) bir bilesen.
    """
    import openmc.data
    if derinlik > 8 or not ad:
        return False
    m = _sema.malzeme_bul(spec, ad)
    if m is not None:
        for b in m.get("bilesim", []):
            isim = b.get("isim") or ""
            try:
                if b.get("tur") == "element":
                    z = openmc.data.ATOMIC_NUMBER.get(isim, 0)
                else:
                    z = openmc.data.zam(isim)[0]
            except (KeyError, ValueError):   # bilinmeyen nuklid/element adi: fisil sayilmaz
                z = 0
            if z >= 90:
                return True
        return False
    c = _sema.cubuk_bul(spec, ad)
    if c is not None:
        return any(_sablon_fisil_mi(spec, b.get("malzeme"), derinlik + 1)
                   for b in c.get("bolgeler", []))
    p = _sema.plaka_bul(spec, ad)
    if p is not None:
        return any(_sablon_fisil_mi(spec, p.get(k), derinlik + 1)
                   for k in ("et_malzeme", "zarf_malzeme", "sogutucu",
                             "yan_levha_malzeme"))
    d = _sema.demet_bul(spec, ad)
    if d is not None:
        adaylar = list((d.get("anahtar") or {}).values()) + [d.get("dolgu_disi")]
        return any(_sablon_fisil_mi(spec, x, derinlik + 1) for x in adaylar if x)
    return False


def _sablon_aktif_aralik(spec):
    """
    Aktif (fisil) yakitin eksenel araligi (z_alt, z_ust); 2B modelde None.

    Eksenel katmanlama yokken tum yukseklik aktiftir. Katmanlama varken
    yalnizca fisil dolgusu olan katmanlar sayilir -- alt/ust yansitici ve
    plenum aktif bolgeye DAHIL DEGILDIR. Kontrol cubugu daldirmasi ve
    lineer guc [W/cm] bu araliga gore tanimlidir.
    """
    kor = spec["kor"]
    h = _sema.kor_yuksekligi(kor)
    if not h:
        return None
    katmanlar = _sema.eksenel_katmanlar(kor)
    if katmanlar is None:
        return (-h / 2.0, h / 2.0)
    alt, ust = None, None
    for z0, z1, katman in katmanlar:
        if not any(_sablon_fisil_mi(spec, x) for x in _sema.katman_adaylari(kor, katman)):
            continue
        alt = z0 if alt is None else min(alt, z0)
        ust = z1 if ust is None else max(ust, z1)
    if alt is None:
        return (-h / 2.0, h / 2.0)       # fisil katman bulunamadi: tumunu kullan
    return (alt, ust)


def _sablon_guc_yuksekligi(spec, cubuk_ad=None):
    """
    Lineer guc [W/cm] paydasi: guc hedef cubugunun GERCEKTEN bulundugu eksenel
    katmanlarin yukseklik TOPLAMI.

    Aktif (fisil) aralik yetmez: blanket fisildir ama hedef cubugu icermez; pay
    (toplam guc x kappa_hedef/kappa_model) blanketi disarida birakirken payda onu
    icerirse W/cm dusuk cikar (olculdu: pwr_eksenel 330 cm vs 300 cm, %9.1 --
    400-500 W/cm sinirina gore IYIMSER yon). Kesintili katmanlarda aradaki bosluk
    sayilmaz. 2B modelde None; hedef hicbir katmanda yoksa aktif aralik.
    Cok turlu hedefte (guc_dagilimi.cubuklar) hedeflerden EN AZ BIRINI
    iceren katmanlar sayilir. cubuk_ad: tek ad ya da ad listesi.
    """
    kor = spec["kor"]
    h = _sema.kor_yuksekligi(kor)
    if not h:
        return None
    adlar = _guc_hedef_adlari(spec, cubuk_ad)
    katmanlar = _sema.eksenel_katmanlar(kor)
    if katmanlar is None or not adlar:
        ar = _sablon_aktif_aralik(spec) if katmanlar is not None else None
        return (ar[1] - ar[0]) if ar else h
    toplam = sum(z1 - z0 for z0, z1, katman in katmanlar
                 if any(_sablon_iceriyor_mu(spec, x, a) for x in _sema.katman_adaylari(kor, katman)
                        for a in adlar))
    if toplam > 0:
        return toplam
    ar = _sablon_aktif_aralik(spec)
    return (ar[1] - ar[0]) if ar else h


def _sablon_iceriyor_mu(spec, kapsayan, aranan, derinlik=0):
    """'kapsayan' adli dolgu, 'aranan' cubugu/plakayi iceriyor mu?"""
    if derinlik > 8 or not kapsayan:
        return False
    if kapsayan == aranan:
        return True
    d = _sema.demet_bul(spec, kapsayan)
    if d is not None:
        adaylar = list((d.get("anahtar") or {}).values()) + [d.get("dolgu_disi")]
        return any(_sablon_iceriyor_mu(spec, x, aranan, derinlik + 1) for x in adaylar if x)
    return False


def _sablon_cubuk_araligi(spec, cubuk_ad):
    """
    Belirli bir cubugun eksenel olarak BULUNDUGU aralik (z_alt, z_ust).

    Guc dagilimi eksenel mesh'i bunu kullanir. "Fisil aralik" yetmez:
    dogal uranyum blanket fisildir ama iceriginde HEDEF cubuk yoktur; mesh
    oraya tasarsa bos bin'ler ortalamayi duserir ve F_q YAPAY OLARAK SISER.
    (Olculdu: pwr_eksenel'de F_q 1.815 -> 1.712, %6 fark.)
    """
    kor = spec["kor"]
    h = _sema.kor_yuksekligi(kor)
    if not h:
        return None
    katmanlar = _sema.eksenel_katmanlar(kor)
    if katmanlar is None:
        return (-h / 2.0, h / 2.0)
    alt, ust = None, None
    for z0, z1, katman in katmanlar:
        if not any(_sablon_iceriyor_mu(spec, x, cubuk_ad) for x in _sema.katman_adaylari(kor, katman)):
            continue
        alt = z0 if alt is None else min(alt, z0)
        ust = z1 if ust is None else max(ust, z1)
    if alt is None:
        return _sablon_aktif_aralik(spec)
    return (alt, ust)


def _guc_hedef_adlari(spec, cubuk_ad=None):
    """Guc hedefi cubuk adlari (sirali, tekrarsiz). cubuk_ad verilirse o
    (tek ad ya da liste); yoksa spec'in guc_dagilimi hedefleri."""
    if cubuk_ad is None:
        adlar = [h["cubuk"] for h in _sema.guc_hedefleri(spec.get("guc_dagilimi"))]
    elif isinstance(cubuk_ad, str):
        adlar = [cubuk_ad]
    else:
        adlar = list(cubuk_ad)
    return list(dict.fromkeys(a for a in adlar if a))


def _sablon_guc_araligi(spec, adlar):
    """Guc mesh'inin eksenel araligi: hedef cubuklarin araliklarinin
    BIRLESIMI (tek turde cubuk_eksenel_aralik'in kendisi). 2B'de None."""
    h = _sema.kor_yuksekligi(spec["kor"])
    if not h:
        return None
    araliklar = [_sablon_cubuk_araligi(spec, a) or (-h / 2.0, h / 2.0) for a in adlar]
    if not araliklar:
        return (-h / 2.0, h / 2.0)
    return (min(a[0] for a in araliklar), max(a[1] for a in araliklar))


# ============================================================================
# AGAC MODU: eksenel araliklar agactaki yiginlardan (R8)
# ============================================================================

def _malzeme_fisil_mi(m):
    """Malzemede Z >= 90 bilesen var mi (sablon olcutuyle ayni)."""
    import openmc.data
    for b in (m or {}).get("bilesim", []):
        isim = b.get("isim") or ""
        try:
            if b.get("tur") == "element":
                z = openmc.data.ATOMIC_NUMBER.get(isim, 0)
            else:
                z = openmc.data.zam(isim)[0]
        except (KeyError, ValueError):   # bilinmeyen nuklid/element adi: fisil sayilmaz
            z = 0
        if z >= 90:
            return True
    return False


def _tanim_adlari(tanim, tur, t):
    """Kutuphane taniminin icerdigi adlar (malzeme ya da bilesen adlari)."""
    if tur == "cubuk":
        return [b.get("malzeme") for b in t.get("bolgeler", [])] + [t.get("izleyici_malzeme")]
    if tur == "plaka":
        return [t.get(k) for k in ("et_malzeme", "zarf_malzeme", "sogutucu", "yan_levha_malzeme")]
    if tur == "demet":
        return list((t.get("anahtar") or {}).values()) + [t.get("dolgu_disi")]
    if tur == "tambur":
        return [t.get("govde_malzeme"), t.get("emici_malzeme")]
    return []


def dugum_iceriyor(m, dugum, sinama, derinlik=0):
    """
    dugum (ya da ad) -- sinama(tur, ad, tanim) True donen bir oge iceriyor mu?
    tur: "malzeme" | "cubuk" | "plaka" | "demet" | "tambur" | "parca".
    """
    from cekirdek.geometri import sema as _gs
    if derinlik > 12 or dugum is None:
        return False
    if isinstance(dugum, str):
        dugum = _gs.kisaltma_coz(m.tanimlar, dugum)
    tur = dugum.get("tur")
    if tur == "malzeme":
        ad = dugum.get("ad")
        return bool(sinama("malzeme", ad, m.tanimlar["malzeme"].get(ad)))
    if tur == "bilesen":
        ad = dugum.get("ad")
        btur, t = _gs.bilesen_tanimi(m.tanimlar, ad)
        if btur is None:
            return False
        if sinama(btur, ad, t):
            return True
        if btur == "parca":
            return dugum_iceriyor(m, t.get("dugum"), sinama, derinlik + 1)
        return any(dugum_iceriyor(m, x, sinama, derinlik + 1)
                   for x in _tanim_adlari(m.tanimlar, btur, t) if x)
    return any(dugum_iceriyor(m, c, sinama, derinlik + 1) for c in _gs.cocuklar(dugum))


def _fisil_sinama(tur, _ad, t):
    return tur == "malzeme" and _malzeme_fisil_mi(t)


def _ad_sinama(adlar):
    kume = set(adlar)
    return lambda tur, ad, _t: tur != "malzeme" and ad in kume


def katman_icerigi(eks, katman):
    """Bir katmani dolduran dugum: katman icerigi, anahtarli kafes turevi ya
    da varsayilan icerik."""
    if katman.get("anahtar") and isinstance(eks.get("icerik"), dict):
        k = dict(eks["icerik"])
        k["anahtar"] = dict(k.get("anahtar") or {}, **katman["anahtar"])
        return k
    return katman.get("icerik") if katman.get("icerik") is not None else eks.get("icerik")


def yiginlar(m):
    """Agactaki eksenel yiginlar (kok ic'indeki once), parcalar dahil."""
    from cekirdek.geometri import sema as _gs
    bulunan, ziyaret = [], set()

    def gez(d):
        if not isinstance(d, dict) or id(d) in ziyaret:
            return
        ziyaret.add(id(d))
        if d.get("tur") == "eksenel":
            bulunan.append(d)
        for c in _gs.cocuklar(d):
            gez(c)
    gez(m.kok)
    for p in m.parcalar:
        gez(p.get("dugum"))
    return bulunan


def eksenel_dilimler(m):
    """[(z0, z1, katman adi, katmani dolduran dugum)] -- butun yiginlar."""
    cikti = []
    for eks in yiginlar(m):
        for i, (z0, z1, k) in enumerate(dilimler(eks)):
            cikti.append((z0, z1, k.get("ad") or "katman %d" % (i + 1), katman_icerigi(eks, k)))
    return cikti


def _agac_araligi(m, sinama):
    h = model_yuksekligi(m)
    if not h:
        return None
    alt = ust = None
    for z0, z1, _ad, icerik in eksenel_dilimler(m):
        if dugum_iceriyor(m, icerik, sinama):
            alt = z0 if alt is None else min(alt, z0)
            ust = z1 if ust is None else max(ust, z1)
    return None if alt is None else (alt, ust)


def _agac_aktif_aralik(m):
    h = model_yuksekligi(m)
    if not h:
        return None
    return _agac_araligi(m, _fisil_sinama) or (-h / 2.0, h / 2.0)


def _agac_hedef_araligi(m, adlar):
    h = model_yuksekligi(m)
    if not h:
        return None
    if not yiginlar(m):
        return (-h / 2.0, h / 2.0)
    araliklar = [_agac_araligi(m, _ad_sinama([a])) or _agac_aktif_aralik(m) for a in adlar]
    if not araliklar:
        return (-h / 2.0, h / 2.0)
    return (min(a[0] for a in araliklar), max(a[1] for a in araliklar))


def _agac_hedef_yuksekligi(m, adlar):
    h = model_yuksekligi(m)
    if not h:
        return None
    dil = eksenel_dilimler(m)
    if not dil or not adlar:
        ar = _agac_aktif_aralik(m) if dil else None
        return (ar[1] - ar[0]) if ar else h
    sinama = _ad_sinama(adlar)
    toplam = sum(z1 - z0 for z0, z1, _a, ic in dil if dugum_iceriyor(m, ic, sinama))
    if toplam > 0:
        return toplam
    ar = _agac_aktif_aralik(m)
    return (ar[1] - ar[0]) if ar else h


# ============================================================================
# GENEL API (kurucu sarmalayicilari bunlari cagirir)
# ============================================================================

def _agac_mi(spec):
    return ((spec or {}).get("kor") or {}).get("tur") == "agac"


def _model(spec):
    from cekirdek import geometri
    return geometri.model(spec)


def aktif_aralik(spec):
    """Aktif (fisil) eksenel aralik (z_alt, z_ust); 2B'de None (R8)."""
    if _agac_mi(spec):
        return _agac_aktif_aralik(_model(spec))
    return _sablon_aktif_aralik(spec)


def hedef_araligi(spec, adlar):
    """Hedef cubuklarin bulundugu eksenel araliklarin birlesimi; 2B'de None."""
    adlar = [adlar] if isinstance(adlar, str) else list(adlar)
    if _agac_mi(spec):
        return _agac_hedef_araligi(_model(spec), adlar)
    return _sablon_guc_araligi(spec, adlar)


def cubuk_araligi(spec, cubuk_ad):
    """Tek cubugun bulundugu eksenel aralik (sablon: cubuk_eksenel_aralik)."""
    if _agac_mi(spec):
        return _agac_hedef_araligi(_model(spec), [cubuk_ad])
    return _sablon_cubuk_araligi(spec, cubuk_ad)


def hedef_yuksekligi(spec, adlar=None):
    """Lineer guc paydasi: hedeflerin bulundugu katmanlarin toplam yuksekligi."""
    if _agac_mi(spec):
        return _agac_hedef_yuksekligi(_model(spec), _guc_hedef_adlari(spec, adlar))
    return _sablon_guc_yuksekligi(spec, adlar)


def fisil_mi(spec, ad):
    """Ad (cubuk/plaka/demet/malzeme; agacta tambur/parca da) fisil mi?"""
    if _agac_mi(spec):
        m = _model(spec)
        return dugum_iceriyor(m, ad, _fisil_sinama)
    return _sablon_fisil_mi(spec, ad)


def iceriyor_mu(spec, kapsayan, aranan):
    """'kapsayan' dolgusu 'aranan' cubugunu iceriyor mu?"""
    if _agac_mi(spec):
        return dugum_iceriyor(_model(spec), kapsayan, _ad_sinama([aranan]))
    return _sablon_iceriyor_mu(spec, kapsayan, aranan)
