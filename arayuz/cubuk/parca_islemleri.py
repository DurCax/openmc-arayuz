# -*- coding: utf-8 -*-
"""
 arayuz/cubuk/parca_islemleri.py  --  saf parca islemleri: roller, sablonlar, adlar, aciklamalar

 arayuz/sekme_cubuk.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import sekme_cubuk; sekme_cubuk.X` aynen calisir.
"""

import json
import re

from cekirdek import sema, uygunluk


BOS_ETIKETI = "Boş (madde yok)"
SECILMEDI_ETIKETI = "— Malzeme seçin —"
MALZEME_YOK_IPUCU = "Önce Malzemeler sekmesinden malzeme ekleyin."

ROL_ADI = {"yakit": "yakıt", "sogutucu": "soğutucu", "moderator": "moderatör",
           "emici": "emici", "yapisal": "yapısal", "gaz": "gaz"}

# (anahtar, menu metni, varsayilan ad) -- "+ Cubuk" menusu bu sirayla.
CUBUK_SABLONLARI = (
    ("yakit", "PWR yakıt çubuğu", "yakit_cubugu"),
    ("kilavuz", "Kılavuz boru", "kilavuz_boru"),
    ("kontrol", "Kontrol çubuğu", "kontrol_cubugu"),
)


# ============================================================================
# saf yardimcilar (Qt gerektirmez; testler/test_parca_demet.py sinar)
# ============================================================================

def _renk(ad, vars_):
    try:
        from arayuz import tema
        return tema.renk(ad)
    except Exception:
        return vars_


_ROL_ONBELLEK = {}


def roller(spec):
    """
    uygunluk.malzeme_rolleri'nin SONUCU, malzemeler bolumune gore onbellekli.
    Roller yalnizca malzeme tanimlarina baglidir; editor her yuklemede onlarca
    kez soruyordu (olculen: yeniden yukleme 4 ms -> 47 ms, cogu atom kutlesi
    aramasi). Kural uygunluk'ta kalir; burada yalnizca tekrar hesaplanmaz.
    """
    try:
        anahtar = json.dumps(spec.get("malzemeler", []), sort_keys=True, default=str)
    except Exception:
        return uygunluk.malzeme_rolleri(spec)
    sonuc = _ROL_ONBELLEK.get(anahtar)
    if sonuc is None:
        if len(_ROL_ONBELLEK) > 16:
            _ROL_ONBELLEK.clear()
        sonuc = _ROL_ONBELLEK[anahtar] = uygunluk.malzeme_rolleri(spec)
    return {ad: set(r) for ad, r in sonuc.items()}


def rol_listesi(spec, rol):
    """uygunluk.rol_malzemeleri ile ayni (spec sirasiyla), onbellekli roller."""
    r = roller(spec)
    return [m["ad"] for m in spec.get("malzemeler", []) if rol in r.get(m.get("ad"), ())]


def _elementler(m):
    """Malzemenin element sembolleri ("Zr90" -> "Zr")."""
    sonuc = set()
    for b in m.get("bilesim") or []:
        e = re.match(r"[A-Z][a-z]?", b.get("isim") or "")
        if e:
            sonuc.add(e.group(0))
    return sonuc


def rol_malzemesi(spec, rol, tercih=()):
    """
    Role uyan ilk malzeme (spec sirasiyla); tercih edilen elementi iceren
    varsa o (zarf: PWR'de zirkaloy, MTR'de aluminyum). Yoksa None.
    """
    adaylar = rol_listesi(spec, rol)
    for ad in adaylar:
        m = sema.malzeme_bul(spec, ad)
        if m is not None and _elementler(m) & set(tercih):
            return ad
    return adaylar[0] if adaylar else None


def cubuk_sablonu(spec, anahtar, ad):
    """
    CUBUK_SABLONLARI'ndan bir cubuk tanimi; malzemeler rollerine gore.
    Olculer PWR 17x17 (Westinghouse): pelet 0.4096, zarf ic/dis 0.418/0.475;
    kilavuz boru 0.561/0.602; emici (Ag-In-Cd / B4C) 0.433 cm.
    Kontrol cubugu kilavuz borusunun icinde durur: cekildiginde emici
    bolgenin yerini sogutucu (izleyici) alir, boru ici tamamen suyla dolar.
    """
    yakit = rol_malzemesi(spec, "yakit")
    gaz = rol_malzemesi(spec, "gaz") or sema.BOSLUK
    zarf = rol_malzemesi(spec, "yapisal", ("Zr",))
    sog = rol_malzemesi(spec, "sogutucu")
    b = sema.bolge
    if anahtar == "yakit":
        return sema.cubuk(ad, [b(0.4096, yakit), b(0.418, gaz), b(0.475, zarf),
                               b(None, sog)])
    if anahtar == "kilavuz":
        return sema.cubuk(ad, [b(0.561, sog), b(0.602, zarf), b(None, sog)])
    if anahtar == "kontrol":
        emici = rol_malzemesi(spec, "emici")
        return sema.kontrol_cubugu(
            ad, [b(0.433, emici), b(0.561, sog), b(0.602, zarf), b(None, sog)],
            izleyici_malzeme=sog, daldirma=0.0, emici_bolge=0)
    raise KeyError("bilinmeyen çubuk şablonu: %s" % anahtar)


# Sablonlarin istedigi roller (eksik olanlar kullaniciya adiyla soylenir).
_SABLON_ROLLERI = {
    "yakit": (("yakit", "yakıt"), ("yapisal", "zarf (yapısal)"), ("sogutucu", "soğutucu")),
    "kilavuz": (("yapisal", "zarf (yapısal)"), ("sogutucu", "soğutucu")),
    "kontrol": (("emici", "emici"), ("yapisal", "zarf (yapısal)"), ("sogutucu", "soğutucu")),
    "plaka": (("yakit", "yakıt"), ("yapisal", "zarf (yapısal)"), ("sogutucu", "soğutucu")),
}


def sablon_eksik_roller(spec, anahtar):
    """Sablonun istedigi ama spec'te karsiligi olmayan roller (okunur adlarla)."""
    return [etiket for rol, etiket in _SABLON_ROLLERI[anahtar]
            if not rol_listesi(spec, rol)]


def plaka_sablonu(spec, ad):
    """MTR plaka elemani (23 plaka); malzemeler rollerine gore, zarf Al tercihli."""
    return sema.plaka(ad, 23, 0.051, 0.038, 0.200, 6.30,
                      rol_malzemesi(spec, "yakit"),
                      rol_malzemesi(spec, "yapisal", ("Al",)),
                      rol_malzemesi(spec, "sogutucu"),
                      yan_levha_kalinlik=0.475)


def _tanimli(spec, ad):
    return ad == sema.BOSLUK or sema.malzeme_bul(spec, ad) is not None


def eksik_malzemeler(spec, parca):
    """
    Parcada malzemesi SECILMEMIS (None) ya da tanimsiz alanlarin okunur
    listesi. Bos liste = eksik yok. Bos (madde yok) bilincli bir secimdir,
    eksik sayilmaz.
    """
    eksik = []
    if parca is None:
        return eksik
    if parca.get("tur") == "plaka":
        for alan, etiket in (("et_malzeme", "yakıt tabakası"), ("zarf_malzeme", "zarf"),
                             ("sogutucu", "soğutucu")):
            ad = parca.get(alan)
            if ad is None or not _tanimli(spec, ad):
                eksik.append(etiket)
        yan = parca.get("yan_levha_malzeme")
        if yan is not None and not _tanimli(spec, yan) and \
                float(parca.get("yan_levha_kalinlik") or 0.0) > 0:
            eksik.append("yan levha")
        return eksik
    bolgeler = parca.get("bolgeler") or []
    for i, b in enumerate(bolgeler):
        ad = b.get("malzeme")
        if ad is None or not _tanimli(spec, ad):
            eksik.append("%d. bölge (%s)" % (i + 1, bolge_aciklamasi(spec, parca, i)
                                             if ad is not None else _konum_adi(parca, i)))
    if parca.get("tur") == "kontrol":
        iz = parca.get("izleyici_malzeme")
        if iz is None or not _tanimli(spec, iz):
            eksik.append("izleyici malzeme")
    return eksik


def _konum_adi(c, i):
    n = len(c.get("bolgeler") or [])
    return "dış bölge" if i == n - 1 else "iç bölge"


def bolge_aciklamasi(spec, c, i):
    """Bolgenin rolunu soyleyen kisa metin (tablonun 'Bölge' sutunu)."""
    bolgeler = c.get("bolgeler") or []
    n = len(bolgeler)
    ad = bolgeler[i].get("malzeme") if 0 <= i < n else None
    if i == n - 1:
        return "Dış bölge — hücrenin kalanını doldurur"
    if ad is None:
        return "Malzeme seçilmedi"
    rol_tablosu = roller(spec)

    def rol(j):
        if not (0 <= j < n):
            return set()
        a = bolgeler[j].get("malzeme")
        if a == sema.BOSLUK:
            return {"bos"}
        return rol_tablosu.get(a, set())

    r = rol(i)
    ek = ""
    if c.get("tur") == "kontrol" and c.get("emici_bolge") == i:
        ek = " (daldırılan)"
    if "yakit" in r:
        return "Yakıt" + ek
    if ("gaz" in r or "bos" in r) and "yakit" in rol(i - 1):
        return "Yakıt-zarf aralığı" + ek
    if "emici" in r:
        return "Emici" + ek
    if "yapisal" in r:
        return "Zarf / yapı" + ek
    if "sogutucu" in r or "moderator" in r:
        return "Soğutucu" + ek
    if "gaz" in r:
        return "Gaz" + ek
    if "bos" in r:
        return "Boş" + ek
    return "Bölge" + ek


def malzeme_etiketi(spec, ad, rol_goster=False, rol_tablosu=None):
    """Kullaniciya gosterilen malzeme adi: Malzemeler sekmesiyle ayni
    "ad — aciklama" bicimi (sema.malzeme_etiketi; ad benzersiz oldugu icin
    etiket de benzersizdir)."""
    if ad is None:
        return SECILMEDI_ETIKETI
    if ad == sema.BOSLUK:
        return BOS_ETIKETI
    m = sema.malzeme_bul(spec, ad)
    if m is None:
        return "%s (tanımsız)" % ad
    metin = sema.malzeme_etiketi(m)
    if rol_goster:
        r = (rol_tablosu if rol_tablosu is not None else roller(spec)).get(ad, set())
        adlar = [ROL_ADI[x] for x in uygunluk.ROLLER if x in r]
        if adlar:
            metin = "%s · %s" % (metin, ", ".join(adlar))
    return metin


def _betik_adi(ad):
    """kod_uret'in degisken adi (iki ad ayni degiskene dusmesin)."""
    try:
        from cekirdek.kod_uret import _ad
        return _ad(ad)
    except Exception:
        return ad


def ad_hatasi(spec, yeni, eski=None):
    """
    Yeni parca adi gecerli mi? Gecerliyse None, degilse okunur hata metni.
    Adlar cubuk/plaka/demet/malzeme arasinda TEKIL olmali: kurucu bir adi
    cubuk -> plaka -> demet -> malzeme sirasiyla cozer; ayni ad baska bir
    seyi gizlerdi. "bosluk" ayrilmistir.
    """
    yeni = (yeni or "").strip()
    if not yeni:
        return "Ad boş olamaz."
    if yeni == eski:
        return None
    if yeni == sema.BOSLUK:
        return "'%s' ayrılmış bir addır (Boş, madde yok)." % yeni
    diger = [x["ad"] for liste in ("cubuklar", "plakalar", "demetler", "malzemeler")
             for x in spec.get(liste, []) if x.get("ad") != eski]
    if yeni in diger:
        return "Bu ad zaten kullanılıyor: %s" % yeni
    betik = _betik_adi(yeni)
    for a in diger:
        if _betik_adi(a) == betik:
            return ("'%s' adı üretilen betikte '%s' ile aynı değişkene düşer; "
                    "başka bir ad seçin." % (yeni, a))
    return None


def benzersiz_ad(spec, taban):
    """taban, taban_2, taban_3 ... icinden ad_hatasi vermeyen ilk ad."""
    ad, i = taban, 2
    while ad_hatasi(spec, ad) is not None:
        ad = "%s_%d" % (taban, i)
        i += 1
    return ad


def _parca_bul(spec, ad):
    for liste in ("cubuklar", "plakalar", "demetler"):
        for x in spec.get(liste, []):
            if x.get("ad") == ad:
                return x
    return None


def parca_adini_degistir(spec, eski, yeni):
    """
    Cubuk/plaka/demet adini ve ONA ISARET EDEN BUTUN referanslari degistirir:
      demetler[].anahtar degerleri
      kor.cubuk / kor.plaka / kor.demet / kor.dolgu
      kor.anahtar (kor haritasi) degerleri
      kor.eksenel.bolgeler[].dolgu ve .anahtar degerleri
      guc_dagilimi.cubuk
    (tukenme ve tallyler yalnizca MALZEME adi tutar.) Yerinde degistirir;
    guncellenen referans sayisini dondurur. Parca yoksa KeyError.
    """
    parca = _parca_bul(spec, eski)
    if parca is None:
        raise KeyError("tanımsız parça: %s" % eski)
    parca["ad"] = yeni
    sayac = [0]

    def esle(sozluk):
        for h, hedef in list((sozluk or {}).items()):
            if hedef == eski:
                sozluk[h] = yeni
                sayac[0] += 1

    def alan(sozluk, anahtar):
        if sozluk is not None and sozluk.get(anahtar) == eski:
            sozluk[anahtar] = yeni
            sayac[0] += 1

    for d in spec.get("demetler", []):
        esle(d.get("anahtar"))
    kor = spec.get("kor") or {}
    for a in ("cubuk", "plaka", "demet", "dolgu"):
        alan(kor, a)
    esle(kor.get("anahtar"))
    for b in (kor.get("eksenel") or {}).get("bolgeler") or []:
        alan(b, "dolgu")
        esle(b.get("anahtar"))
    alan(spec.get("guc_dagilimi"), "cubuk")
    return sayac[0]


def parca_kullanimlari(spec, ad):
    """Parcanin kullanildigi yerler (okunur metinler) -- silmeden once sorulur."""
    yerler = []
    for d in spec.get("demetler", []):
        if d.get("ad") != ad and ad in (d.get("anahtar") or {}).values():
            yerler.append("'%s' demeti" % d["ad"])
    kor = spec.get("kor") or {}
    if sema.ana_dolgu(kor) == ad or ad in (kor.get("anahtar") or {}).values():
        yerler.append("kor")
    for b in (kor.get("eksenel") or {}).get("bolgeler") or []:
        if b.get("dolgu") == ad or ad in (b.get("anahtar") or {}).values():
            yerler.append("'%s' eksenel katmanı" % (b.get("ad") or "adsız"))
    if (spec.get("guc_dagilimi") or {}).get("cubuk") == ad:
        yerler.append("güç dağılımı")
    return yerler


def kor_dolgusu_bos_mu(spec, alan):
    """kor[alan] bos ya da tanimsiz bir parcaya mi isaret ediyor?"""
    ad = (spec.get("kor") or {}).get(alan)
    return not ad or _parca_bul(spec, ad) is None


def parca_rengi(spec, parca):
    """Listede simge rengi: cubukta en ic bolgenin, plakada yakit tabakasinin rengi."""
    adlar = ([b.get("malzeme") for b in parca.get("bolgeler") or []]
             if parca.get("tur") != "plaka" else [parca.get("et_malzeme")])
    for ad in adlar:
        m = sema.malzeme_bul(spec, ad) if ad else None
        if m is not None and m.get("renk"):
            return tuple(int(x) for x in m["renk"][:3])
    return (170, 170, 170)
