# -*- coding: utf-8 -*-
"""
================================================================================
 alt_model.py  --  Tek parca / tek demet / tek dugum ALT MODELI (saf)
================================================================================

 Tam modelin (spec) bir parcasini TEK EVRENLI, butun dis sinirlari YANSITICI
 yeni bir spec olarak verir. Kullananlar:
   - onizleme kapsami (v3 K5): Parcalar sayfasinda secili pin/plaka/tambur,
     Demet sayfasinda secili demet, gelismis Geometri'de secili dugum;
   - demet k-sonsuz sihirbazi (v3 K4): demet_alt_modeli(spec, ad, uc_boyutlu=False)
     -- sonsuz kafes (yansitici sinirli tek demet), 2B.

 Butun islevler SAF: girdi spec DEGISMEZ (derin kopya uzerinde calisilir),
 openmc gerektirmez. Kurulum her zaman kurucu.kur ile yapilir; alt model
 icin ayri bir kurucu yolu YOKTUR (ayni geometri kodu, ayni malzemeler).

 SABLON YOLU (cubuk, plaka, demet)
   kor.tur = tek_cubuk / tek_plaka / tek_demet (cekirdek/geometri/sablon.py
   olculeri), yansitici kusak yok, eksenel katmanlama yok. Kutuphane parcanin
   bagimlilik kapanisina (demet harita anahtarlari, ic ice demetler) ve
   malzeme listesi kullanilan malzemelere budanir: kapsam disi malzeme
   ne geometriye ne materials.xml'e girer.
   Cubuk adimi: cubugu kullanan ilk demetin adimi; yoksa tek_cubuk korunun
   adimi; yoksa dis yaricapin 2 x _PIN_PAYI kati (bkz. sabit).

 AGAC YOLU (tambur, gelismis geometride kafes/kap dugumu)
   kor.tur = "agac", kok = yansitici sinirli bir kap; icerik secili dugum.
   Kutuphane ve malzemeler aynen kalir (agacta kullanilmayan tanim kurulmaz);
   gruplar yalniz uyelerinin hepsi alt agacta kalanlardir.

 YUKSEKLIK
   uc_boyutlu=True (onizleme): 3B modelde alt model ayni yukseklikte, tek
   eksenel bolge (kontrol cubugu daldirmasi korunur). uc_boyutlu=False: 2B.

 KAYNAK
   Ayarlar korunur; kaynak kutusunun elle yazilmis koselerinin (alt/ust) ve
   nokta kaynagin konumunun alt model disinda kalmamasi icin koseler silinir
   (kutu alt modelin ic olcusunden turetilir), nokta orijine alinir.
   Tally, guc dagilimi, tukenme ve kinetik kapatilir.
================================================================================
"""

import copy

from cekirdek import sema
from cekirdek.ceviri import _, N_

# Demette kullanilmayan pinin hucre kenari = 2 x dis yaricap x pay. Pay yalniz
# GORSEL: dis (sogutucu) bolgesi kesitte gorunsun; bir tasarim adimi degildir
# (PWR 17x17: adim/cap = 1.26/0.95 = 1.33 -- pay bunun altinda kalir).
_PIN_PAYI = 1.25
_YANSITICI = {"yan": "reflective", "alt": "reflective", "ust": "reflective"}
_EN_COK_DERINLIK = 10            # dugum cozumunde ic ice parca siniri (geometri.sema)

PARCA_TURLERI = ("cubuk", "plaka", "demet", "tambur")
TUR_ADLARI = {"cubuk": N_("çubuk"), "plaka": N_("plaka"), "demet": N_("demet"),
              "tambur": N_("tambur")}
_SABLON = {"cubuk": ("tek_cubuk", "cubuklar"), "plaka": ("tek_plaka", "plakalar"),
           "demet": ("tek_demet", "demetler")}


class AltModelHatasi(ValueError):
    """Alt model kurulamaz (tanimsiz parca, bilinmeyen tur); mesaj gosterilir."""


# ----------------------------------------------------------------------------
# ortak taban
# ----------------------------------------------------------------------------

def _yukseklik(spec: dict, uc_boyutlu: bool) -> float | None:
    if not uc_boyutlu:
        return None
    try:
        return sema.model_yuksekligi(spec)
    except (ValueError, KeyError, TypeError) as e:
        raise AltModelHatasi(_("model yüksekliği okunamadı: %s") % e) from e


def _taban(spec: dict, etiket: str) -> dict:
    """Spec'in derin kopyasi: tally/guc/tukenme/kinetik kapali, kaynak alt modele uyar."""
    alt = copy.deepcopy(spec)
    alt["ad"] = "%s — %s" % (spec.get("ad") or "", etiket)
    alt["tallyler"] = []
    alt["guc_dagilimi"] = copy.deepcopy(sema.VARSAYILAN_GUC)
    alt["tukenme"] = dict(copy.deepcopy(alt.get("tukenme") or sema.VARSAYILAN_TUKENME),
                          var=False, ek_malzemeler=[])
    ayar = alt.setdefault("ayarlar", copy.deepcopy(sema.VARSAYILAN_AYARLAR))
    ayar["kinetik"] = dict(ayar.get("kinetik") or {}, var=False)
    kaynak = ayar.setdefault("kaynak", {})
    kaynak.pop("alt", None)
    kaynak.pop("ust", None)
    kaynak["konum"] = [0.0, 0.0, 0.0]
    return alt


def _etiket(tur: str, ad: str) -> str:
    return "%s ‘%s’" % (_(TUR_ADLARI.get(tur, tur)), ad)


# ----------------------------------------------------------------------------
# sablon yolu: cubuk, plaka, demet
# ----------------------------------------------------------------------------

def _anahtar_adlari(demet: dict) -> list:
    """Demet harita anahtarlarindaki adlar (dize ya da {"ad": ...} dugumu)."""
    adlar = []
    for deger in (demet.get("anahtar") or {}).values():
        ad = deger.get("ad") if isinstance(deger, dict) else deger
        if isinstance(ad, str) and ad:
            adlar.append(ad)
    return adlar


def _kapanis(spec: dict, ad: str) -> set:
    """'ad' parcasinin bagimlilik kapanisi (kendisi + demet anahtarlarindaki adlar)."""
    gorulen, bekleyen = set(), [ad]
    while bekleyen:
        simdiki = bekleyen.pop()
        if simdiki in gorulen:
            continue
        gorulen.add(simdiki)
        demet = sema.demet_bul(spec, simdiki)
        if demet is not None:
            bekleyen.extend(_anahtar_adlari(demet))
    return gorulen


def _buda(alt: dict, adlar: set) -> dict:
    """Kutuphaneyi 'adlar'a, malzemeleri kullanilanlara budar (alt kopyadir)."""
    for bolum in ("cubuklar", "plakalar", "demetler"):
        alt[bolum] = [p for p in alt.get(bolum) or [] if p.get("ad") in adlar]
    kullanilan = sema.kullanilan_malzemeler(alt) | adlar
    alt["malzemeler"] = [m for m in alt.get("malzemeler") or [] if m.get("ad") in kullanilan]
    return alt


def _cubuk_adimi(spec: dict, ad: str) -> float:
    for d in spec.get("demetler") or []:
        if ad in _anahtar_adlari(d) and d.get("adim"):
            return float(d["adim"])
    kor = spec.get("kor") or {}
    if kor.get("tur") == "tek_cubuk" and kor.get("cubuk") == ad and kor.get("adim"):
        return float(kor["adim"])
    yaricaplar = [float(b["r"]) for b in (sema.cubuk_bul(spec, ad) or {}).get("bolgeler") or []
                  if b.get("r")]
    if yaricaplar:
        return 2.0 * max(yaricaplar) * _PIN_PAYI
    return float(sema.VARSAYILAN_KOR["adim"])


def _sablon_alt_modeli(spec: dict, tur: str, ad: str, uc_boyutlu: bool) -> dict:
    kor_turu, bolum = _SABLON[tur]
    if not any(p.get("ad") == ad for p in spec.get(bolum) or []):
        raise AltModelHatasi(_("tanımsız %(tur)s: %(ad)s") % {"tur": _(TUR_ADLARI[tur]), "ad": ad})
    alt = _taban(spec, _etiket(tur, ad))
    kor = copy.deepcopy(sema.VARSAYILAN_KOR)
    kor.update({"tur": kor_turu, tur: ad, "yukseklik": _yukseklik(spec, uc_boyutlu),
                "sinir": dict(_YANSITICI)})
    if tur == "cubuk":
        kor["adim"] = _cubuk_adimi(spec, ad)
    alt["kor"] = kor
    alt["geometri"] = None
    alt["tamburlar"] = []
    return _buda(alt, _kapanis(spec, ad))


# ----------------------------------------------------------------------------
# agac yolu: tambur, kafes, kap
# ----------------------------------------------------------------------------

def _yerlesim_adlari(deger, adlar: set) -> set:
    if isinstance(deger, dict):
        for y in deger.get("yerlesimler") or []:
            if isinstance(y, dict) and y.get("ad"):
                adlar.add(y["ad"])
        for v in deger.values():
            _yerlesim_adlari(v, adlar)
    elif isinstance(deger, list):
        for v in deger:
            _yerlesim_adlari(v, adlar)
    return adlar


def _agac_alt_modeli(spec: dict, kok: dict, etiket: str, uc_boyutlu: bool) -> dict:
    """kok: yeni kok kap (kesit + ic); sinir yansitici, yukseklik modelden."""
    alt = _taban(spec, etiket)
    kok = dict(kok, id="kok", sinir=dict(_YANSITICI), yukseklik=_yukseklik(spec, uc_boyutlu))
    kok.setdefault("yerlesimler", [])
    kok.setdefault("halkalar", [])
    eski = spec.get("geometri") if sema.agac_modu(spec) else {}
    adlar = _yerlesim_adlari(kok, set())
    gruplar = [copy.deepcopy(g) for g in (eski or {}).get("gruplar") or []
               if set(g.get("uyeler") or []) <= adlar]
    alt["kor"] = {"tur": sema.AGAC}
    alt["geometri"] = {"kok": copy.deepcopy(kok),
                       "parcalar": copy.deepcopy((eski or {}).get("parcalar") or []),
                       "gruplar": gruplar}
    return alt


def _tambur_alt_modeli(spec: dict, ad: str, uc_boyutlu: bool) -> dict:
    t = next((t for t in spec.get("tamburlar") or [] if t.get("ad") == ad), None)
    if t is None:
        raise AltModelHatasi(_("tanımsız %(tur)s: %(ad)s") % {"tur": _(TUR_ADLARI["tambur"]),
                                                              "ad": ad})
    cap = 2.0 * float(t.get("yaricap") or 0.0)
    if cap <= 0.0:
        raise AltModelHatasi(_("tambur yarıçapı sıfırdan büyük olmalı: %s") % ad)
    kok = {"tur": "kap", "kesit": {"sekil": "dikdortgen", "boyut": [cap, cap]},
           "ic": {"tur": "bilesen", "ad": ad}}
    return _agac_alt_modeli(spec, kok, _etiket("tambur", ad), uc_boyutlu)


# ----------------------------------------------------------------------------
# genel giris
# ----------------------------------------------------------------------------

def parca_alt_modeli(spec: dict, tur: str, ad: str, uc_boyutlu: bool = True) -> dict:
    """Tek parcanin (cubuk | plaka | demet | tambur) yansitici sinirli alt modeli."""
    if tur == "tambur":
        return _tambur_alt_modeli(spec, ad, uc_boyutlu)
    if tur not in _SABLON:
        raise AltModelHatasi(_("bilinmeyen parça türü: %s") % tur)
    return _sablon_alt_modeli(spec, tur, ad, uc_boyutlu)


def demet_alt_modeli(spec: dict, ad: str, uc_boyutlu: bool = False) -> dict:
    """K4 demet k-sonsuz: yansitici sinirli tek demet (varsayilan 2B)."""
    return parca_alt_modeli(spec, "demet", ad, uc_boyutlu=uc_boyutlu)


def _al(agac, yol):
    d = agac
    for p in yol:
        if isinstance(d, dict) and not isinstance(p, int) and p in d:
            d = d[p]
        elif isinstance(d, list) and isinstance(p, int) and 0 <= p < len(d):
            d = d[p]
        else:
            return None
    return d


def _kafes_kesiti(kafes: dict) -> dict | None:
    if kafes.get("sekil") == "altigen":
        return {"sekil": "kafes_zarfi"}
    adim, boyut = kafes.get("adim"), kafes.get("boyut") or []
    if not adim or len(boyut) < 2:
        return None
    return {"sekil": "dikdortgen", "boyut": [float(adim) * boyut[0], float(adim) * boyut[1]]}


def _bilesen(spec, tanim, deger, uc_boyutlu, derinlik):
    from cekirdek.geometri.sema import bilesen_tanimi
    tur, t = bilesen_tanimi(tanim, deger.get("ad"))
    if tur in PARCA_TURLERI:
        return parca_alt_modeli(spec, tur, deger["ad"], uc_boyutlu)
    if tur == "parca":
        return _deger_alt_modeli(spec, tanim, t.get("dugum"), uc_boyutlu, derinlik + 1)
    return None


def _deger_alt_modeli(spec, tanim, deger, uc_boyutlu, derinlik=0):
    """Agactaki bir deger (dugum, kisaltma, halka/yerlesim/katman) -> alt model | None."""
    from cekirdek.geometri.sema import kisaltma_coz
    if derinlik > _EN_COK_DERINLIK:
        return None
    if isinstance(deger, str):
        deger = kisaltma_coz(tanim, deger)
    if not isinstance(deger, dict):
        return None
    tur = deger.get("tur")
    if tur is None and "icerik" in deger:          # halka, yerlesim, katman
        return _deger_alt_modeli(spec, tanim, deger.get("icerik"), uc_boyutlu, derinlik + 1)
    if tur == "bilesen":
        return _bilesen(spec, tanim, deger, uc_boyutlu, derinlik)
    etiket = "%s ‘%s’" % (_("düğüm"), deger.get("id") or tur)
    if tur == "kafes":
        kesit = _kafes_kesiti(deger)
        if kesit is None:
            return None
        return _agac_alt_modeli(spec, {"tur": "kap", "kesit": kesit, "ic": deger}, etiket,
                                uc_boyutlu)
    if tur == "kap":
        return _agac_alt_modeli(spec, {k: v for k, v in deger.items() if k != "dis"}, etiket,
                                uc_boyutlu)
    return None                                    # malzeme, eksenel, referans: tam model


def dugum_alt_modeli(spec: dict, yol, uc_boyutlu: bool = True) -> dict | None:
    """Gelismis geometride secili dugumun alt modeli; tam kor gereken yerde None
    (sablon modu, kok, malzeme/eksenel dugumu, cozulemeyen yol)."""
    yol = tuple(yol or ())
    if not sema.agac_modu(spec) or yol in ((), ("kok",)):
        return None
    from cekirdek.geometri.sema import tanimlar
    agac = spec.get("geometri") or {}
    return _deger_alt_modeli(spec, tanimlar(spec, agac), _al(agac, yol), uc_boyutlu)
