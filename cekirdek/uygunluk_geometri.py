# -*- coding: utf-8 -*-
"""
================================================================================
 uygunluk_geometri.py  --  uygunluk'un geometri kurallari (icerik, boyut, sinir)
================================================================================

 uygunluk.py'den bolundu (Dalga G-2; dosya 800 satir tavanini asiyordu).
 Disaridan uygunluk.geometri_icerigi, uygunluk.sinir_secenekleri ... olarak
 kullanilir; uygunluk bu adlari yeniden disa verir (imzalar aynidir).

 SABLON / AGAC
   Sablon modunda (kor.tur 7 sablondan biri) kurallar eskisi gibi spec
   alanlarindan okunur (davranis degismedi). Gelismis (agac) modda:
     geometri_icerigi   -> geometri.icerik (agac gezintisi; ayni bicim)
     model_boyutu       -> agactaki eksenel yiginlar ve geometri.yukseklik
     yan_yuzey          -> geometri.sinir_bilgisi().yuzey
     sinir_secenekleri  -> periodic yalniz en dis kesit dikdortgen/altigense
                           ve dis sinira degen delik yoksa (sinir_bilgisi)
     sonsuz_ortam       -> yan (ya da yuz basina) + alt/ust sinirlar
   yuz_sinir_secenekleri(spec): yuz basina yan sinir (§15 karar 4) --
   dikdortgende 4, altigende 6 yuz; her yuze "yan" ile ayni secenekler.
================================================================================
"""

import types

from cekirdek import sema
from cekirdek.uygunluk_bellek import Bellek, icerik_anahtari

# Spec icerigine gore bellek (v3 H1; bkz. uygunluk_bellek.py)
_ICERIK = Bellek("geometri_icerigi")
_BOYUT = Bellek("model_boyutu")


def _agac(spec):
    return ((spec or {}).get("kor") or {}).get("tur") == "agac"


def _model(spec):
    from cekirdek import geometri
    return geometri.model(spec)


def geometri_icerigi(spec):
    """
    Kurulan modelde GERCEKTEN yer alan adlar.

    DONER {"malzeme", "cubuk", "plaka", "demet", "kafesteki_cubuk"} (kumeler;
    agac modunda ayrica "tambur", "parca")
      kafesteki_cubuk : bir kafes haritasinda (kor haritasi dahil) yer alan,
                        yani TEKRARLANAN cubuklar -- guc dagilimi icin.
    Agac modunda geometri.icerik (agac gezintisi), sablonda
    _sablon_geometri_icerigi (kurallar orada).
    """
    return {k: set(v) for k, v in dondurulmus_icerik(spec).items()}


def dondurulmus_icerik(spec, anahtar=None):
    """geometri_icerigi'nin DEGISMEZ bicimi (salt okunur esleme, frozenset);
    spec icerigine gore bellekli. anahtar: icerik_anahtari(spec) (verilmezse
    hesaplanir)."""
    return _ICERIK.al(anahtar or icerik_anahtari(spec), lambda: types.MappingProxyType(
        {k: frozenset(v) for k, v in _icerik_hesapla(spec).items()}))


def _icerik_hesapla(spec):
    if _agac(spec):
        from cekirdek import geometri
        return geometri.icerik(_model(spec))
    return _sablon_geometri_icerigi(spec)


def model_boyutu(spec, anahtar=None):
    """"2B" | "3B" | "3B_katmanli" -- eksenel boyut (kurede "2B"); bellekli.
    anahtar: icerik_anahtari(spec) (verilmezse hesaplanir)."""
    return _BOYUT.al(anahtar or icerik_anahtari(spec), lambda: _model_boyutu(spec))


def _model_boyutu(spec):
    if _agac(spec):
        from cekirdek import geometri
        from cekirdek.geometri.eksenel import yiginlar
        m = _model(spec)
        if not geometri.yukseklik(m):
            return "2B"
        return "3B_katmanli" if yiginlar(m) else "3B"
    kor = spec.get("kor") or {}
    if sema.eksenel_katmanlar(kor):
        return "3B_katmanli"
    if sema.kor_yuksekligi(kor):
        return "3B"
    return "2B"


# Altigen prizmada periodic yan sinir -- SUNULUR.
#   Kullanilabilirlik denetimi "OpenMC altigende periodic esleyemez" demisti;
#   YANLIS. OpenMC 0.16 HexagonalPrism karsi yuzleri periodic_surface ile
#   esler ve kosar. Iki bagimsiz olcum, sfr_altigen:
#     periodic 1.46737 +/- 0.00142  vs reflective 1.46804 +/- 0.00192
#     periodic 1.46672 +/- 0.00109  vs reflective 1.46699 +/- 0.00156 (0.14 sigma)
#   Silindir (tamburlu) ve kure icin periodic gecersiz kalir: OpenMC "Found
#   only one periodic surface without a specified partner" ile durur (olculdu).
_ALTIGEN_PERIODIC = True


# ----------------------------------------------------------------------------
# geometri icerigi -- kurucu.kor_kur'un izledigi yol
# ----------------------------------------------------------------------------

def _bul(spec, bolum, ad):
    for x in spec.get(bolum) or []:
        if x.get("ad") == ad:
            return x
    return None


def _harita_hedefleri(harita, anahtar):
    """Haritada GERCEKTEN gecen harflerin gosterdigi adlar (kurucu yalnizca onlari kurar)."""
    harfler = []
    for satir in harita or []:
        for h in satir:
            if h not in harfler:
                harfler.append(h)
    return [anahtar[h] for h in harfler if anahtar.get(h)]


def _sablon_geometri_icerigi(spec):
    """
    Kurulan modelde GERCEKTEN yer alan adlar.

    DONER {"malzeme", "cubuk", "plaka", "demet", "kafesteki_cubuk"} (kumeler)
      kafesteki_cubuk : bir kafes haritasinda (kor haritasi dahil) yer alan,
                        yani TEKRARLANAN cubuklar -- guc dagilimi icin.

    kurucu.kor_kur ile ayni yol izlenir:
      * ad cozumleme sirasi cubuk -> plaka -> demet -> malzeme
        (kurucu._universe_uret)
      * kafeste yalnizca haritada gecen harfler kurulur (anahtarda olup
        haritada olmayan harf modele girmez)
      * eksenel katmanlamada ana dolgu yalnizca kendi dolgusu olmayan bir
        katman varsa kullanilir; katmana ozel "anahtar" yalnizca kare_kafes'te
      * yansitici: tek_demet/kare_kafes'te "var" ise, tamburlu'da her zaman;
        tek_cubuk/tek_plaka/kuresel'de hic
      * tambur malzemeleri yalnizca tamburlu ve sayi > 0 iken
    """
    ic = {"malzeme": set(), "cubuk": set(), "plaka": set(), "demet": set(),
          "kafesteki_cubuk": set()}
    kor = spec.get("kor") or {}
    tur = kor.get("tur")

    def malzeme_ekle(ad):
        if ad and ad != sema.BOSLUK and _bul(spec, "malzemeler", ad) is not None:
            ic["malzeme"].add(ad)

    def gez(ad, kafeste=False, derinlik=0):
        if not ad or ad == sema.BOSLUK or derinlik > 8:
            return
        c = _bul(spec, "cubuklar", ad)
        if c is not None:
            ic["cubuk"].add(ad)
            if kafeste:
                ic["kafesteki_cubuk"].add(ad)
            for b in c.get("bolgeler") or []:
                malzeme_ekle(b.get("malzeme"))
            if c.get("tur") == "kontrol":
                malzeme_ekle(c.get("izleyici_malzeme"))
            return
        p = _bul(spec, "plakalar", ad)
        if p is not None:
            ic["plaka"].add(ad)
            for alan in ("et_malzeme", "zarf_malzeme", "sogutucu"):
                malzeme_ekle(p.get(alan))
            if float(p.get("yan_levha_kalinlik") or 0.0) > 0:
                malzeme_ekle(p.get("yan_levha_malzeme") or p.get("zarf_malzeme"))
            return
        d = _bul(spec, "demetler", ad)
        if d is not None:
            if ad in ic["demet"]:
                return
            ic["demet"].add(ad)
            malzeme_ekle(d.get("dolgu_disi"))
            k = d.get("kilif") if d.get("tur") == "altigen" else None
            if isinstance(k, dict):
                malzeme_ekle(k.get("malzeme"))
            for hedef in _harita_hedefleri(d.get("harita"), d.get("anahtar") or {}):
                gez(hedef, True, derinlik + 1)
            return
        malzeme_ekle(ad)

    def kor_haritasi(ek_anahtar=None):
        esleme = dict(kor.get("anahtar") or {})
        esleme.update(ek_anahtar or {})
        for hedef in _harita_hedefleri(kor.get("harita"), esleme):
            gez(hedef, True)

    if tur == "kuresel":
        for k in kor.get("kabuklar") or []:
            malzeme_ekle(k.get("malzeme"))
        return ic
    if tur not in sema.EKSENEL_DESTEKLI:
        return ic

    yans = kor.get("yansitici") or {}
    if tur == "tamburlu":
        malzeme_ekle(yans.get("malzeme"))
        t = kor.get("tambur") or {}
        if int(t.get("sayi") or 0) > 0:
            malzeme_ekle(t.get("govde_malzeme"))
            malzeme_ekle(t.get("emici_malzeme"))
    elif tur in ("tek_demet", "kare_kafes", "altigen_kafes") and yans.get("var"):
        malzeme_ekle(yans.get("malzeme"))

    katmanlar = sema.eksenel_katmanlar(kor)
    ana_kullanilir = katmanlar is None
    for _z0, _z1, b in katmanlar or []:
        if b.get("anahtar"):
            if tur in sema.HARITALI_KORLAR:
                kor_haritasi(b["anahtar"])
            # baska turde kurucu hata verir (dogrula.eksenel_kontrol bildirir)
        elif b.get("dolgu"):
            gez(b["dolgu"])
        else:
            ana_kullanilir = True
    if ana_kullanilir:
        if tur in sema.HARITALI_KORLAR:
            kor_haritasi()
        else:
            gez(sema.ana_dolgu(kor))
    return ic


def _altigen_kor(spec):
    kor = spec.get("kor") or {}
    if kor.get("tur") == "altigen_kafes":
        return True
    if kor.get("tur") != "tek_demet":
        return False
    d = _bul(spec, "demetler", kor.get("demet") or "")
    return bool(d) and d.get("tur") == "altigen"


def _sablon_yan_yuzey(spec):
    """
    kurucu.kor_kur'un kurdugu yan sinir yuzeyi:
      "kare"    : RectangularPrism (tek_cubuk, tek_plaka, kare demet, kare_kafes)
      "altigen" : HexagonalPrism (altigen tek_demet) ya da altigen tam korun
                  kirik cizgi siniri (altigen_kafes)
      "silindir": ZCylinder (tamburlu)
      "kure"    : Sphere (kuresel)
      None      : bilinmeyen tur
    """
    tur = (spec.get("kor") or {}).get("tur")
    if tur == "kuresel":
        return "kure"
    if tur == "tamburlu":
        return "silindir"
    if tur in ("tek_demet", "altigen_kafes"):
        return "altigen" if _altigen_kor(spec) else "kare"
    if tur in ("tek_cubuk", "tek_plaka", "kare_kafes"):
        return "kare"
    return None


def _sablon_sinir_secenekleri(spec, yuzey):
    """
    yuzey: "yan" | "alt" | "ust". Uygun sinir kosullari; bos liste = yuzey yok.

      yan : reflective, vacuum, white her yuzeyde (OpenMC 0.16 kure ve
            silindirde de kosar -- olculdu). periodic yalnizca KARE kesitte
            (x/y duzlem ciftleri): kure ve silindirde OpenMC "Found only one
            periodic surface without a specified partner" diyerek durur.
            Altigen prizma icin bkz. _ALTIGEN_PERIODIC.
      alt/ust : yalnizca 3B modelde ve kure disinda (2B'de z yuzeyi yok,
            kurede eksen yok). periodic SUNULMAZ: tek tarafli periodic
            OpenMC'yi durdurur (olculdu), iki tarafli olani ise korun
            tepesini dibine baglar -- sonlu bir korda fiziksel degildir.
    """
    tur = (spec.get("kor") or {}).get("tur")
    if yuzey in ("alt", "ust"):
        if tur == "kuresel" or model_boyutu(spec) == "2B":
            return []
        return ["vacuum", "reflective", "white"]
    if yuzey != "yan":
        return []
    yy = _sablon_yan_yuzey(spec)
    if yy == "kure":
        return ["vacuum", "reflective", "white"]
    secenek = ["reflective", "vacuum", "white"]
    # Altigen tam korun yan siniri demetlerin dis yuzlerinden gecen KIRIK bir
    # cizgidir (ya da yansitici halkasi); eslesen duzlem cifti yoktur.
    if tur == "altigen_kafes":
        return secenek
    if yy == "kare" or (yy == "altigen" and _ALTIGEN_PERIODIC):
        secenek.append("periodic")
    return secenek


# Nötron kaçırmayan sınır koşulları (dışarı sızıntı yok).
_SIZINTISIZ = ("reflective", "white", "periodic")


def _sablon_sonsuz_ortam(spec):
    """
    Modelin DIS sinirlarinin hepsi sizintisiz mi (yansitici / beyaz /
    periyodik)? O zaman hesaplanan carpim katsayisi k-eff degil k∞'dur:
    sonsuz tekrarlanan ortamin katsayisi. Bu durumda "kritik ustu" hukmu
    YANLIS olur -- k∞ > 1 yalnizca yakitin reaktivite fazlasi tasidigini
    soyler, reaktorun ne yaptigini degil (Ajan 9 bulgusu: pin hucrede
    kirmiziyla "Kritik ustu — guc artar" yaziyordu).
    2B modelde (yukseklik yok) eksen yonu zaten sonsuzdur; yalniz yan sinir
    bakilir. Kurede tek sinir vardir.
    """
    kor = spec.get("kor") or {}
    sinir = kor.get("sinir") or {}
    yuzeyler = ["yan"]
    if kor.get("tur") != "kuresel" and sema.kor_yuksekligi(kor):
        yuzeyler += ["alt", "ust"]
    if isinstance(sinir.get("yuzler"), (dict, list)):
        return _yuzler_sizintisiz(sinir["yuzler"]) and all(
            sinir.get(y, "reflective") in _SIZINTISIZ for y in yuzeyler[1:])
    return all(sinir.get(y, "reflective") in _SIZINTISIZ for y in yuzeyler)


def yan_yuzey(spec):
    """
    Kurulan modelin yan (dis) sinir yuzeyi: "kare" | "altigen" | "silindir"
    | "kure" | None; agac modunda ayrica "kirik" (yansiticisiz altigen tam
    kor: demet dis yuzlerinden gecen kirik cizgi). Sablon: _sablon_yan_yuzey.
    """
    if _agac(spec):
        from cekirdek import geometri
        return geometri.sinir_bilgisi(_model(spec)).yuzey
    return _sablon_yan_yuzey(spec)


def sinir_secenekleri(spec, yuzey):
    """
    yuzey: "yan" | "alt" | "ust" ya da bir yuz adi (yuz_sinir_secenekleri;
    "yan" ile ayni secenekler). Uygun sinir kosullari; bos liste = yuzey yok.
    Sablon kurallari _sablon_sinir_secenekleri'nde; agac modunda periodic
    yalniz sinir_bilgisi().periyodik_uygun iken sunulur.
    """
    if yuzey not in ("yan", "alt", "ust"):
        return list(sinir_secenekleri(spec, "yan")) if yuzey in _yuz_adlari(spec) else []
    if not _agac(spec):
        return _sablon_sinir_secenekleri(spec, yuzey)
    from cekirdek import geometri
    sb = geometri.sinir_bilgisi(_model(spec))
    if yuzey in ("alt", "ust"):
        return [] if (sb.yuzey == "kure" or model_boyutu(spec) == "2B") else \
            ["vacuum", "reflective", "white"]
    if sb.yuzey == "kure":
        return ["vacuum", "reflective", "white"]
    secenek = ["reflective", "vacuum", "white"]
    if sb.periyodik_uygun and (sb.yuzey == "kare" or _ALTIGEN_PERIODIC):
        secenek.append("periodic")
    return secenek


def _yuz_adlari(spec):
    from cekirdek import geometri
    try:
        return geometri.sinir_bilgisi(_model(spec)).yuz_adlari
    except (KeyError, ValueError, TypeError) as e:
        # kurulamayan (yarim duzenlenmis) spec: yuz yok; dogrulama bildirir
        from cekirdek.gunluk import kaydedici
        kaydedici(__name__).debug("yüz adları okunamadı: %s", e)
        return ()


def yuz_sinir_secenekleri(spec):
    """
    Yuz basina yan sinir (§15 karar 4): {yuz adi: [secenekler]}; sirali
    (kurulum sirasi: dikdortgende -x, +x, -y, +y; altigende yuz normali
    acisi artan). Yan yuzeyi duz yuzlu olmayan modelde (silindir, kure,
    kirik) bos sozluk. Periyodik karsi yuzler ciftler halinde secilmelidir
    (dogrulama denetler).
    """
    yy = yan_yuzey(spec)
    if yy not in ("kare", "altigen"):
        return {}
    yan = sinir_secenekleri(spec, "yan")
    return {ad: list(yan) for ad in _yuz_adlari(spec)}


def _yuzler_sizintisiz(yuzler):
    degerler = list(yuzler.values()) if isinstance(yuzler, dict) else list(yuzler)
    return all((v or "reflective") in _SIZINTISIZ for v in degerler)


def sonsuz_ortam(spec):
    """Dis sinirlarin hepsi sizintisiz mi (k-eff degil k-sonsuz)? Sablon
    kurallari _sablon_sonsuz_ortam'da; agac modunda sinir_bilgisi."""
    if not _agac(spec):
        return _sablon_sonsuz_ortam(spec)
    from cekirdek import geometri
    sb = geometri.sinir_bilgisi(_model(spec))
    if sb.yuzler:
        yan = _yuzler_sizintisiz(sb.yuzler)
    else:
        yan = (sb.yan or "reflective") in _SIZINTISIZ
    uclar = [x for x in (sb.alt, sb.ust) if x is not None] if sb.yuzey != "kure" else []
    return yan and all(x in _SIZINTISIZ for x in uclar)
