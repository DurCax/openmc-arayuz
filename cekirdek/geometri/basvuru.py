# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/basvuru.py  --  Agactaki ad basvurulari ve yeniden adlandirma (§7)
================================================================================

   basvurular(spec)                  -> [Basvuru(yol, tur, ad)]
   agac_adini_degistir(spec, tur, eski, yeni) -> (yeni geometri, [yol])
   ad_degistir(spec, tur, eski, yeni) -> YENI spec (saf)

 Basvuru turleri: "malzeme" (malzeme dugumu ya da malzemeye cozulen
 kisaltma), kutuphane turleri "cubuk" | "plaka" | "demet" | "tambur" |
 "parca" (bilesen dugumu ya da kisaltma; cozum sirasi sema.kisaltma_coz),
 "tanimsiz" (hicbir tanima cozulmeyen ad), "yerlesim" (donme grubu uyesi),
 "kafes" (kafes_konumu yerlesiminin kafes kimligi). Yollar spec'e gore
 JSON isaretcisidir: "/geometri/kok/ic", "/geometri/parcalar/0/dugum/...".

 Yalniz spec["geometri"] (gelismis mod) gezilir; sablon modunda agac spec'te
 saklanmaz (kutuphane ve kor alanlari sema_basvuru'da).
================================================================================
"""

import copy
from collections import namedtuple

from cekirdek.geometri.sema import BOLUMLER, BOSLUK, ad_bolumleri, tanimlar

Basvuru = namedtuple("Basvuru", "yol tur ad")
KUTUPHANE_TURLERI = tuple(tur for _b, tur in BOLUMLER)
_BOLUM = {tur: bolum for bolum, tur in BOLUMLER}


def _coz_turu(tanim, ad, acik_malzeme=False):
    if acik_malzeme:
        return "malzeme"
    if ad == BOSLUK or ad is None:
        return "malzeme"
    turler = ad_bolumleri(tanim, ad)
    if turler:
        return turler[0]
    return "malzeme" if ad in tanim.get("malzeme", {}) else "tanimsiz"


def _yuvalar(d, yol):
    """[(yol, deger, ata, anahtar)] -- dugumun yuvalari (dize ya da dugum)."""
    tur = d.get("tur")
    cikti = []
    if tur == "kafes":
        for h in sorted(d.get("anahtar") or {}):
            cikti.append(("%s/anahtar/%s" % (yol, h), d["anahtar"][h], d["anahtar"], h))
        if "dis" in d:
            cikti.append((yol + "/dis", d["dis"], d, "dis"))
    elif tur == "kap":
        cikti.append((yol + "/ic", d.get("ic"), d, "ic"))
        cikti += _yerlesim_yuvalari(d.get("yerlesimler") or [], yol + "/yerlesimler")
        for i, h in enumerate(d.get("halkalar") or []):
            hy = "%s/halkalar/%d" % (yol, i)
            cikti.append((hy + "/icerik", h.get("icerik"), h, "icerik"))
            cikti += _yerlesim_yuvalari(h.get("yerlesimler") or [], hy + "/yerlesimler")
        if d.get("dis") is not None:
            cikti.append((yol + "/dis", d["dis"], d, "dis"))
    elif tur == "eksenel":
        cikti.append((yol + "/icerik", d.get("icerik"), d, "icerik"))
        for i, k in enumerate(d.get("katmanlar") or []):
            ky = "%s/katmanlar/%d" % (yol, i)
            if k.get("icerik") is not None:
                cikti.append((ky + "/icerik", k["icerik"], k, "icerik"))
            for h in sorted(k.get("anahtar") or {}):
                cikti.append(("%s/anahtar/%s" % (ky, h), k["anahtar"][h], k["anahtar"], h))
    return cikti


def _yerlesim_yuvalari(yerlesimler, yol):
    return [("%s/%d/icerik" % (yol, i), y.get("icerik"), y, "icerik")
            for i, y in enumerate(yerlesimler)]


def _gez(deger, yol, tanim, cikti, derinlik=0):
    """Ham agac degerini gezer; Basvuru'lari cikti'ya ekler."""
    if derinlik > 60 or deger is None:
        return
    if isinstance(deger, str):
        cikti.append(Basvuru(yol, _coz_turu(tanim, deger), deger))
        return
    if not isinstance(deger, dict):
        return
    tur = deger.get("tur")
    if tur == "malzeme":
        cikti.append(Basvuru(yol, "malzeme", deger.get("ad")))
        return
    if tur == "bilesen":
        ad = deger.get("ad")
        turler = ad_bolumleri(tanim, ad)
        cikti.append(Basvuru(yol, turler[0] if turler else "tanimsiz", ad))
        return
    if tur == "kap":
        for i, y in enumerate(_kap_yerlesimleri(deger)):
            if y.get("mod") == "kafes_konumu" and y.get("kafes"):
                cikti.append(Basvuru("%s/yerlesim/%s/kafes" % (yol, y.get("ad") or i), "kafes",
                                     y.get("kafes")))
    for ay, alt, _ata, _a in _yuvalar(deger, yol):
        _gez(alt, ay, tanim, cikti, derinlik + 1)


def _kap_yerlesimleri(kap):
    liste = list(kap.get("yerlesimler") or [])
    for h in kap.get("halkalar") or []:
        liste += list(h.get("yerlesimler") or [])
    return liste


def basvurular(spec):
    """spec["geometri"]deki butun ad basvurulari (yol sirasiyla)."""
    agac = (spec or {}).get("geometri") or {}
    tanim = tanimlar(spec, agac)
    cikti = []
    _gez(agac.get("kok"), "/geometri/kok", tanim, cikti)
    for i, p in enumerate(agac.get("parcalar") or []):
        _gez(p.get("dugum"), "/geometri/parcalar/%d/dugum" % i, tanim, cikti)
    for i, g in enumerate(agac.get("gruplar") or []):
        tur = "cubuk" if g.get("tur") == "daldirma" else "yerlesim"
        for j, u in enumerate(g.get("uyeler") or []):
            cikti.append(Basvuru("/geometri/gruplar/%d/uyeler/%d" % (i, j), tur, u))
    return cikti


# ----------------------------------------------------------------------------
# yeniden adlandirma
# ----------------------------------------------------------------------------

def _yeniden(deger, tanim, tur, eski, yeni, yol, yollar, derinlik=0):
    """Degerin kopyasi: 'tur' turune cozulen 'eski' basvurulari 'yeni'."""
    if derinlik > 60 or deger is None:
        return deger
    if isinstance(deger, str):
        if deger == eski and _coz_turu(tanim, deger) == tur:
            yollar.append(yol)
            return yeni
        return deger
    if not isinstance(deger, dict):
        return copy.deepcopy(deger)
    d = copy.deepcopy(deger)
    dt = d.get("tur")
    if dt in ("malzeme", "bilesen"):
        hedef = "malzeme" if dt == "malzeme" else _coz_turu(tanim, d.get("ad"))
        if d.get("ad") == eski and hedef == tur:
            d["ad"] = yeni
            yollar.append(yol)
        return d
    if dt == "kap" and tur == "kafes":
        for y in _kap_yerlesimleri(d):
            if y.get("mod") == "kafes_konumu" and y.get("kafes") == eski:
                y["kafes"] = yeni
                yollar.append("%s/yerlesim/%s/kafes" % (yol, y.get("ad")))
    for ay, alt, ata, anahtar in _yuvalar(d, yol):
        ata[anahtar] = _yeniden(alt, tanim, tur, eski, yeni, ay, yollar, derinlik + 1)
    if dt == "kafes" and tur == "kafes" and d.get("id") == eski:
        d["id"] = yeni
        yollar.append(yol + "/id")
    return d


def agac_adini_degistir(spec, tur, eski, yeni):
    """(yeni geometri sozlugu, [degisen yol]) -- spec DEGISMEZ."""
    agac = (spec or {}).get("geometri")
    if not isinstance(agac, dict):
        return agac, []
    tanim = tanimlar(spec, agac)
    yollar = []
    yeni_agac = copy.deepcopy(agac)
    yeni_agac["kok"] = _yeniden(agac.get("kok"), tanim, tur, eski, yeni, "/geometri/kok", yollar)
    parcalar = []
    for i, p in enumerate(agac.get("parcalar") or []):
        p2 = dict(p, dugum=_yeniden(p.get("dugum"), tanim, tur, eski, yeni,
                                    "/geometri/parcalar/%d/dugum" % i, yollar))
        if tur == "parca" and p.get("ad") == eski:
            p2["ad"] = yeni
        parcalar.append(p2)
    if "parcalar" in agac:
        yeni_agac["parcalar"] = parcalar
    uye_turu = {"cubuk": "daldirma", "yerlesim": "donme"}.get(tur)
    for i, g in enumerate(yeni_agac.get("gruplar") or []):
        if g.get("tur") == uye_turu:
            for j, u in enumerate(g.get("uyeler") or []):
                if u == eski:
                    g["uyeler"][j] = yeni
                    yollar.append("/geometri/gruplar/%d/uyeler/%d" % (i, j))
    return yeni_agac, yollar


def _yerlesim_adini_degistir(agac, eski, yeni):
    def gez(d):
        if not isinstance(d, dict):
            return
        if d.get("tur") == "kap":
            for y in _kap_yerlesimleri(d):
                if y.get("ad") == eski:
                    y["ad"] = yeni
        for _y, alt, _a, _k in _yuvalar(d, ""):
            gez(alt)
    gez(agac.get("kok"))
    for p in agac.get("parcalar") or []:
        gez(p.get("dugum"))


def ad_degistir(spec, tur, eski, yeni):
    """
    YENI spec: 'tur' turundeki 'eski' tanimi 'yeni' olur, butun basvurular
    (agac + kutuphane + sablon kor alanlari) guncellenir. tur: malzeme |
    cubuk | plaka | demet | tambur | parca | yerlesim | kafes. Girdi DEGISMEZ.
    HATA KeyError: tanim yok; ValueError: yeni ad cakisiyor.
    """
    kopya = copy.deepcopy(spec)
    if eski == yeni:
        return kopya
    if tur == "malzeme":
        from cekirdek.sema_basvuru import malzeme_adini_degistir
        malzeme_adini_degistir(kopya, eski, yeni)
        return kopya
    tanim = tanimlar(kopya, kopya.get("geometri") or {})
    if tur in KUTUPHANE_TURLERI:
        if eski not in tanim.get(tur, {}):
            raise KeyError("tanımsız %s: %s" % (tur, eski))
        if ad_bolumleri(tanim, yeni) or yeni in tanim.get("malzeme", {}):
            raise ValueError("'%s' adı zaten kullanılıyor" % yeni)
    agac, _yollar = agac_adini_degistir(kopya, tur, eski, yeni)
    if agac is not None:
        kopya["geometri"] = agac
    if tur == "yerlesim" and isinstance(kopya.get("geometri"), dict):
        _yerlesim_adini_degistir(kopya["geometri"], eski, yeni)
    if tur in ("cubuk", "plaka", "demet", "tambur"):
        _kutuphane_adini_degistir(kopya, tur, eski, yeni)
    return kopya


def _kutuphane_adini_degistir(spec, tur, eski, yeni):
    """Kutuphane tanimi + kutuphane ici ve sablon kor alanlarindaki basvurular."""
    for t in spec.get(_BOLUM[tur]) or []:
        if t.get("ad") == eski:
            t["ad"] = yeni
    if tur == "tambur":
        return
    for d in spec.get("demetler") or []:
        for h, v in list((d.get("anahtar") or {}).items()):
            if v == eski:
                d["anahtar"][h] = yeni
    kor = spec.get("kor") or {}
    for a in ("cubuk", "plaka", "demet", "dolgu"):
        if kor.get(a) == eski:
            kor[a] = yeni
    for h, v in list((kor.get("anahtar") or {}).items()):
        if v == eski:
            kor["anahtar"][h] = yeni
    for b in (kor.get("eksenel") or {}).get("bolgeler") or []:
        if b.get("dolgu") == eski:
            b["dolgu"] = yeni
        for h, v in list((b.get("anahtar") or {}).items()):
            if v == eski:
                b["anahtar"][h] = yeni
    g = spec.get("guc_dagilimi") or {}
    if tur == "cubuk":
        for h in [g] + [x for x in g.get("cubuklar") or [] if isinstance(x, dict)]:
            if h.get("cubuk") == eski:
                h["cubuk"] = yeni
