# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/sablon.py  --  Sablon (kor.tur) -> dugum agaci  (SAF; §6)
================================================================================

 genislet(spec) -> {"kok", "parcalar", "gruplar", ...}; girdi DEGISMEZ.
 Olculer ve sayilar eski kurucu.kor_kur ile BIT DUZEYINDE ayni sirayla
 hesaplanir (esdegerlik kapisi, §9): ornegin altigen demet siniri
   apotem = (n-1) P sqrt3/2 + P/2 + buyutme
 ayni islem sirasiyla yazilir.

 Turetilmis notlar ("_" ile baslar, diske yazilmaz):
   kok["_kutu"]    : eski kor_kur'un dondurdugu sinir kutusu (gx, gy)
   kok["_ic_kutu"] : eski kor_ic_olcusu (kaynak kutusu, yansitici haric)
   kok["_sablon"]  : kor.tur
   agac["_uretilen_tanimlar"]: sablonun urettigi tanimlar (tamburlu: tambur)
 Sablon denetimleri (eski kurucunun ValueError/KeyError mesajlari) burada
 AYNEN korunur; form mesajlari ve testler bunlara dayanir.
================================================================================
"""

import copy
import math

from cekirdek import altigen
from cekirdek import altigen_kor as _akor
from cekirdek import tambur as _tambur
from cekirdek.sema import (BOSLUK, cubuk_bul, plaka_bul, demet_bul, malzeme_bul,
                           eksenel_katmanlar, kor_yuksekligi)
from cekirdek.ceviri import _


def _ad_dugumu(spec, ad):
    """Eski _universe_uret sirasi: cubuk -> plaka -> demet -> malzeme/bosluk.
    Tanimsiz ad bilesen olur; kurucu KeyError('tanımsız ad') verir."""
    if ad is None:
        return {"tur": "bilesen", "ad": None}
    if cubuk_bul(spec, ad) is not None or plaka_bul(spec, ad) is not None \
            or demet_bul(spec, ad) is not None:
        return {"tur": "bilesen", "ad": ad}
    if ad == BOSLUK or malzeme_bul(spec, ad) is not None:
        return {"tur": "malzeme", "ad": ad}
    return {"tur": "bilesen", "ad": ad}


def _malzeme_dugumu(ad):
    return {"tur": "malzeme", "ad": ad if ad else BOSLUK}


def _sinir(kor, yalniz_yan=False):
    s = copy.deepcopy(kor.get("sinir") or {})
    if yalniz_yan:
        return {k: v for k, v in s.items() if k in ("yan", "yuzler")}
    return s


def _katman_hatasi(katman):
    return ValueError(
        _("'%s' eksenel katmanı: katmana özel harf eşlemesi yalnızca kare "
        "haritalı tam korda ya da altıgen haritalı tam korda kullanılabilir")
        % katman.get("ad"))


def _eksenel_sar(spec, kor, ic, haritali):
    """Katmanlama aciksa ic'i eksenel yigina sarar. DONER (ic, yukseklik)."""
    katmanlar = eksenel_katmanlar(kor)
    if katmanlar is None:
        h = kor_yuksekligi(kor)
        return ic, h
    yeni = []
    for _z0, _z1, b in katmanlar:
        k = {"ad": b.get("ad"), "yukseklik": float(b["yukseklik"]), "icerik": None}
        if b.get("anahtar"):
            if not haritali:
                raise _katman_hatasi(b)
            k["anahtar"] = {h: _ad_dugumu(spec, v) for h, v in sorted(b["anahtar"].items())}
        elif b.get("dolgu"):
            # _katman: eski kurucu katman dolgusunu AYRI ("__katman__<ad>") bir
            # evren olarak kuruyordu; distribcell ornek numaralari korunur.
            k["icerik"] = dict(_ad_dugumu(spec, b["dolgu"]), _katman=True)
        yeni.append(k)
    return {"tur": "eksenel", "id": "kor_eksen", "icerik": ic, "katmanlar": yeni}, None


def _kok(kesit, ic, halkalar, yukseklik, sinir, kutu, ic_kutu, sablon, yerlesimler=()):
    return {"tur": "kap", "id": "kok", "kesit": kesit, "ic": ic,
            "yerlesimler": list(yerlesimler), "halkalar": list(halkalar),
            "yukseklik": yukseklik, "sinir": sinir,
            "_kutu": [kutu[0], kutu[1]], "_ic_kutu": [ic_kutu[0], ic_kutu[1]],
            "_sablon": sablon}


def _yansitici(kor, tur):
    yans = kor.get("yansitici") or {}
    return yans if (yans.get("var") and tur in ("tek_demet", "kare_kafes")) else None


# ----------------------------------------------------------------------------
# sablonlar
# ----------------------------------------------------------------------------

def _tek_cubuk(spec, kor):
    if cubuk_bul(spec, kor.get("cubuk")) is None:
        raise KeyError(_("tanımsız çubuk: %s") % kor.get("cubuk"))
    ic, h = _eksenel_sar(spec, kor, {"tur": "bilesen", "ad": kor["cubuk"]}, False)
    a = kor["adim"]
    return _kok({"sekil": "dikdortgen", "boyut": [a, a]}, ic, [], h, _sinir(kor),
                (a, a), (a, a), "tek_cubuk")


def plaka_olcusu(p):
    """MTR elemaninin (top_x, top_y) olcusu -- kurucu.plaka_universe ile ayni."""
    n = p["plaka_sayisi"]
    plaka_kal = 2.0 * p["zarf_kalinlik"] + p["et_kalinlik"]
    top_x = n * plaka_kal + (n + 1) * p["kanal_kalinlik"]
    top_y = p["plaka_genislik"] + 2.0 * p.get("yan_levha_kalinlik", 0.0)
    return top_x, top_y


def _tek_plaka(spec, kor):
    p = plaka_bul(spec, kor.get("plaka"))
    if p is None:
        raise KeyError(_("tanımsız plaka elemanı: %s") % kor.get("plaka"))
    gx, gy = plaka_olcusu(p)
    ic, h = _eksenel_sar(spec, kor, {"tur": "bilesen", "ad": kor["plaka"]}, False)
    return _kok({"sekil": "dikdortgen", "boyut": [gx, gy]}, ic, [], h, _sinir(kor),
                (gx, gy), (gx, gy), "tek_plaka")


def _altigen_demet_apotem(d, buyutme=0.0):
    """kurucu._altigen_sinir ile ayni islem sirasi."""
    halka = d.get("halka_sayisi") or d["boyut"][0]
    adim = d["adim"]
    return (halka - 1) * adim * math.sqrt(3.0) / 2.0 + adim / 2.0 + buyutme


def _tek_demet(spec, kor):
    d = demet_bul(spec, kor.get("demet"))
    if d is None:
        raise KeyError(_("tanımsız demet: %s") % kor.get("demet"))
    ic, h = _eksenel_sar(spec, kor, {"tur": "bilesen", "ad": d["ad"]}, False)
    yans = _yansitici(kor, "tek_demet")
    if d.get("tur") != "altigen":
        gx, gy = d["adim"] * d["boyut"][0], d["adim"] * d["boyut"][1]
        return _dikdortgen_kor(kor, ic, h, gx, gy, yans, "tek_demet")
    yon = d.get("yonelim", "y")
    halka = d.get("halka_sayisi") or d["boyut"][0]
    buy = (_akor.demet_dis_olcu(d) - _akor.pin_zarfi(d)) / 2.0 if _akor.kilif(d) else 0.0
    if _akor.kilif(d):
        gx, gy = _akor.prizma_kutusu(_akor.demet_dis_olcu(d) / 2.0, yon)
    else:
        gx, gy = altigen.kapsayan_olcu(halka, d["adim"], yon)
    kesit = {"sekil": "altigen", "yonelim": yon, "apotem": _altigen_demet_apotem(d, buy)}
    if not yans:
        return _kok(kesit, ic, [], h, _sinir(kor), (gx, gy), (gx, gy), "tek_demet")
    kal = yans["kalinlik"]
    olcu = altigen.kapsayan_olcu(halka, d["adim"], yon) if not buy else (gx, gy)
    kutu = (olcu[0] + 2 * kal, olcu[1] + 2 * kal)
    halkalar = [{"dis": {"sekil": "altigen", "yonelim": yon,
                         "apotem": _altigen_demet_apotem(d, buyutme=kal + buy)},
                 "icerik": _malzeme_dugumu(yans.get("malzeme")), "yerlesimler": []}]
    return _kok(kesit, ic, halkalar, h, _sinir(kor), kutu, _ic_kutu(kutu, kal), "tek_demet")


def _ic_kutu(kutu, kal):
    """kurucu.kor_ic_olcusu: sinir kutusu - 2 x kalinlik (ayni islem)."""
    kal = float(kal or 0.0)
    return (kutu[0] - 2.0 * kal, kutu[1] - 2.0 * kal)


def _dikdortgen_kor(kor, ic, h, gx, gy, yans, sablon):
    kesit = {"sekil": "dikdortgen", "boyut": [gx, gy]}
    if not yans:
        return _kok(kesit, ic, [], h, _sinir(kor), (gx, gy), (gx, gy), sablon)
    kal = yans["kalinlik"]
    kutu = (gx + 2 * kal, gy + 2 * kal)
    halkalar = [{"kalinlik": kal, "icerik": _malzeme_dugumu(yans.get("malzeme")),
                 "yerlesimler": []}]
    return _kok(kesit, ic, halkalar, h, _sinir(kor), kutu, _ic_kutu(kutu, kal), sablon)


def _kare_kafes(spec, kor):
    nx, ny = kor["boyut"]
    harita = kor["harita"]
    if len(harita) != ny:
        raise ValueError(_("kor haritası %d satır, boyut %d bekliyor") % (len(harita), ny))
    kafes = {"tur": "kafes", "id": "kor_kafesi", "sekil": "kare", "adim": kor["adim"],
             "boyut": [nx, ny], "harita": list(harita),
             "anahtar": {h: _ad_dugumu(spec, v) for h, v in sorted((kor.get("anahtar") or {}).items())},
             "dis": _malzeme_dugumu((kor.get("yansitici") or {}).get("malzeme")),
             "_sablon_harita": True}
    ic, h = _eksenel_sar(spec, kor, kafes, True)
    return _dikdortgen_kor(kor, ic, h, kor["adim"] * nx, kor["adim"] * ny,
                           _yansitici(kor, "kare_kafes"), "kare_kafes")


def _altigen_kafes(spec, kor):
    _akor.harita_kontrol(kor)
    n, P = _akor.halka_sayisi(kor), float(kor["adim"])
    yon = kor.get("yonelim") or "x"
    kafes = {"tur": "kafes", "id": "kor_kafesi", "sekil": "altigen", "adim": P,
             "halka_sayisi": n, "yonelim": yon, "harita": list(kor.get("harita") or []),
             "anahtar": {h: _ad_dugumu(spec, v) for h, v in sorted((kor.get("anahtar") or {}).items())},
             "_sablon_harita": True}
    ic, h = _eksenel_sar(spec, kor, kafes, True)
    kal = _akor.yansitici_kalinligi(kor)
    halkalar = [] if kal is None else [
        {"dis": {"sekil": "altigen", "yonelim": yon, "apotem": _akor.zarf_apotemi(n, P) + kal},
         "icerik": _malzeme_dugumu((kor.get("yansitici") or {}).get("malzeme")),
         "yerlesimler": []}]
    return _kok({"sekil": "kafes_zarfi"}, ic, halkalar, h, _sinir(kor),
                _akor.kor_sinir_kutusu(kor), _akor.kor_ic_olcusu(kor), "altigen_kafes")


def _kuresel(spec, kor):
    kabuklar = kor.get("kabuklar") or []
    if not kabuklar:
        raise ValueError(_("küresel düzenekte en az bir kabuk gerekir"))
    yaricaplar = [k["r"] for k in kabuklar]
    for i in range(len(yaricaplar) - 1):
        if yaricaplar[i] >= yaricaplar[i + 1]:
            raise ValueError(_("kabuk yarıçapları artan sırada olmalı: "
                             "r%d = %.5f ≥ r%d = %.5f")
                             % (i + 1, yaricaplar[i], i + 2, yaricaplar[i + 1]))
    halkalar = [{"dis": {"sekil": "kure", "yaricap": k["r"]},
                 "icerik": _malzeme_dugumu(k.get("malzeme")), "yerlesimler": []}
                for k in kabuklar[1:]]
    capi = 2.0 * yaricaplar[-1]
    return _kok({"sekil": "kure", "yaricap": kabuklar[0]["r"]},
                _malzeme_dugumu(kabuklar[0].get("malzeme")), halkalar, None,
                _sinir(kor, yalniz_yan=True), (capi, capi), (capi, capi), "kuresel")


def _tambur_tanimi(t, ad):
    return {"ad": ad, "yaricap": t.get("yaricap"), "govde_malzeme": t.get("govde_malzeme"),
            "emici_malzeme": t.get("emici_malzeme"),
            "emici_ic_yaricap": t.get("emici_ic_yaricap"), "emici_aci": t.get("emici_aci")}


def _uretilen_tambur_adi(spec):
    adlar = {x.get("ad") for b in ("cubuklar", "plakalar", "demetler", "tamburlar",
                                   "malzemeler") for x in spec.get(b) or []}
    ad, i = "tambur", 2
    while ad in adlar:
        ad, i = "tambur_%d" % i, i + 1
    return ad


def _tamburlu(spec, kor):
    R_kor = float(kor.get("kor_yaricap") or 0.0)
    yans = kor.get("yansitici") or {}
    kal = float(yans.get("kalinlik") or 0.0)
    if R_kor <= 0 or kal <= 0:
        raise ValueError(_("tamburlu korda kor yarıçapı ve yansıtıcı kuşak "
                         "kalınlığı sıfırdan büyük olmalı"))
    t = kor.get("tambur") or {}
    n = int(t.get("sayi") or 0)
    hatalar = _tambur.geometri_kontrol(t, R_kor, kal) if n else []
    if hatalar:
        raise ValueError(_("tambur yerleşimi geçersiz: ") + hatalar[0])
    if not kor.get("dolgu"):
        raise ValueError(_("tamburlu korda kor dolgusu seçilmeli "
                         "(demet, çubuk ya da malzeme)"))
    ic, h = _eksenel_sar(spec, kor, _ad_dugumu(spec, kor["dolgu"]), False)
    ad = _uretilen_tambur_adi(spec)
    yerlesimler, gruplar = [], []
    if n > 0:
        yerlesimler = [{"ad": "tamburlar", "mod": "halka", "sayi": n,
                        "merkez_yaricap": float(t.get("merkez_yaricap") or 0.0),
                        "baslangic_acisi": float(t.get("baslangic_acisi") or 0.0),
                        "icerik": {"tur": "bilesen", "ad": ad}, "kesit": None,
                        "bakis": {"tur": "merkez", "merkez": [0.0, 0.0]}}]
        gruplar = [{"ad": "tamburlar", "tur": "donme", "deger": float(t.get("donme") or 0.0),
                    "uyeler": ["tamburlar"]}]
    R_dis = R_kor + kal
    kutu = (2 * R_dis, 2 * R_dis)
    kok = _kok({"sekil": "silindir", "yaricap": R_kor}, ic,
               [{"kalinlik": kal, "icerik": _malzeme_dugumu(yans.get("malzeme")),
                 "yerlesimler": yerlesimler}], h, _sinir(kor), kutu, _ic_kutu(kutu, kal),
               "tamburlu")
    return kok, gruplar, ([_tambur_tanimi(t, ad)] if n > 0 else [])


_SABLONLAR = {"tek_cubuk": _tek_cubuk, "tek_plaka": _tek_plaka, "tek_demet": _tek_demet,
              "kare_kafes": _kare_kafes, "altigen_kafes": _altigen_kafes,
              "kuresel": _kuresel}


def genislet(spec):
    """
    Sablon spec -> agac sozlugu {"kok", "parcalar", "gruplar"
    [, "_uretilen_tanimlar"]}. Girdi DEGISMEZ (sonuc derin kopyadir).
    """
    kor = spec["kor"]
    tur = kor.get("tur")
    if tur == "tamburlu":
        kok, gruplar, tamburlar = _tamburlu(spec, kor)
        agac = {"kok": kok, "parcalar": [], "gruplar": gruplar}
        if tamburlar:
            agac["_uretilen_tanimlar"] = {"tamburlar": tamburlar}
        return copy.deepcopy(agac)
    if tur not in _SABLONLAR:
        raise ValueError(_("bilinmeyen kor türü: %s") % tur)
    return copy.deepcopy({"kok": _SABLONLAR[tur](spec, kor), "parcalar": [], "gruplar": []})
