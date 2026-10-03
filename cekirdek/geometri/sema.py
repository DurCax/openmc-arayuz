# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/sema.py  --  Dugum semasi: turler, tanimlar, yuva cozumu, normalize
================================================================================

 docs/GEOMETRI_MODELI.md §2-§3. Alti dugum turu: malzeme, bilesen, kafes,
 kap, eksenel, referans. Yuvaya (kap.ic, halka.icerik, kafes.anahtar[harf],
 kafes.dis, eksenel.icerik, katman.icerik, yerlesim.icerik) bir dugum ya da
 DIZE KISALTMASI yazilabilir; kisaltma kurucunun eski _universe_uret
 sirasiyla cozulur: cubuk -> plaka -> demet -> tambur -> parca -> malzeme.

 Butun islevler SAF: girdi degismez, yeni yapi doner.
================================================================================
"""

import copy

BOSLUK = "bosluk"
DUGUM_TURLERI = ("malzeme", "bilesen", "kafes", "kap", "eksenel", "referans")
KULLANICI_TURLERI = ("malzeme", "bilesen", "kafes", "kap", "eksenel")
SINIR_TURLERI = ("vacuum", "reflective", "white", "periodic")
YERLESIM_MODLARI = ("halka", "liste", "kafes_konumu")
GRUP_TURLERI = ("donme", "daldirma")
MAKS_DERINLIK = 10
UYARI_DERINLIK = 6
UYARI_DELIK_SAYISI = 50

# Kutuphane bolumleri, kisaltma cozum sirasi (kurucu._universe_uret ile ayni).
# (spec anahtari, tanim turu)
BOLUMLER = (("cubuklar", "cubuk"), ("plakalar", "plaka"), ("demetler", "demet"),
            ("tamburlar", "tambur"), ("parcalar", "parca"),
            ("trisolar", "triso"))


def yuva_adi(dugum):
    """Kisaltma dizesi ya da dugumun gorunen kisa adi (mesajlar icin)."""
    if isinstance(dugum, str):
        return dugum
    if isinstance(dugum, dict):
        return str(dugum.get("id") or dugum.get("ad") or dugum.get("tur") or "?")
    return repr(dugum)


def tanimlar(spec, agac=None):
    """
    Kutuphane tanimlari {tur: {ad: tanim}}; tur cubuk|plaka|demet|tambur|parca.
    agac: normalize edilmemis ya da edilmis geometri sozlugu (parcalar ve
    sablonun urettigi _uretilen_tanimlar buradan okunur).
    """
    agac = agac or {}
    sonuc = {tur: {} for _b, tur in BOLUMLER}
    for bolum, tur in BOLUMLER[:3]:
        for t in spec.get(bolum) or []:
            sonuc[tur].setdefault(t.get("ad"), t)
    uretilen = (agac.get("_uretilen_tanimlar") or {}).get("tamburlar") or []
    for t in list(spec.get("tamburlar") or []) + list(uretilen):
        sonuc["tambur"].setdefault(t.get("ad"), t)
    for t in spec.get("trisolar") or []:
        sonuc["triso"].setdefault(t.get("ad"), t)
    for p in agac.get("parcalar") or []:
        sonuc["parca"].setdefault(p.get("ad"), p)
    sonuc["malzeme"] = {m.get("ad"): m for m in spec.get("malzemeler") or []}
    return sonuc


def ad_bolumleri(tanim, ad):
    """'ad'in gectigi kutuphane turleri (sirali): belirsizlik denetimi icin."""
    return [tur for _b, tur in BOLUMLER if ad in tanim.get(tur, {})]


def kisaltma_coz(tanim, ad):
    """Dize kisaltmasini acik dugume cevirir (kopya). Tanimsiz ad bilesen olur
    (denetim 'tanimsiz basvuru' der)."""
    if ad == BOSLUK or ad is None:
        return {"tur": "malzeme", "ad": BOSLUK}
    for _b, tur in BOLUMLER:
        if ad in tanim.get(tur, {}):
            return {"tur": "bilesen", "ad": ad}
    if ad in tanim.get("malzeme", {}):
        return {"tur": "malzeme", "ad": ad}
    return {"tur": "bilesen", "ad": ad}


def bilesen_tanimi(tanim, ad):
    """(tur, tanim) -- kisaltma sirasiyla ilk eslesme; yoksa (None, None)."""
    for _b, tur in BOLUMLER:
        if ad in tanim.get(tur, {}):
            return tur, tanim[tur][ad]
    return None, None


# ----------------------------------------------------------------------------
# normalize: butun yuvalar acik dugum
# ----------------------------------------------------------------------------

def _yuva(deger, tanim):
    if isinstance(deger, str) or deger is None:
        return kisaltma_coz(tanim, deger)
    if isinstance(deger, dict):
        return _dugum(deger, tanim)
    return copy.deepcopy(deger)


def _yerlesim(y, tanim):
    yeni = copy.deepcopy(y)
    if "icerik" in yeni:
        yeni["icerik"] = _yuva(yeni.get("icerik"), tanim)
    return yeni


def _dugum(d, tanim):
    """Tek dugumun normalize kopyasi (ic yuvalar dahil)."""
    yeni = copy.deepcopy(d)
    tur = yeni.get("tur")
    if tur == "kafes":
        yeni["anahtar"] = {h: _yuva(v, tanim) for h, v in (d.get("anahtar") or {}).items()}
        if d.get("dis") is not None:
            yeni["dis"] = _yuva(d.get("dis"), tanim)
    elif tur == "kap":
        yeni["ic"] = _yuva(d.get("ic"), tanim)
        yeni["yerlesimler"] = [_yerlesim(y, tanim) for y in d.get("yerlesimler") or []]
        halkalar = []
        for h in d.get("halkalar") or []:
            hy = copy.deepcopy(h)
            hy["icerik"] = _yuva(h.get("icerik"), tanim)
            hy["yerlesimler"] = [_yerlesim(y, tanim) for y in h.get("yerlesimler") or []]
            halkalar.append(hy)
        yeni["halkalar"] = halkalar
        if d.get("dis") is not None:
            yeni["dis"] = _yuva(d.get("dis"), tanim)
    elif tur == "eksenel":
        yeni["icerik"] = _yuva(d.get("icerik"), tanim)
        katmanlar = []
        for k in d.get("katmanlar") or []:
            ky = copy.deepcopy(k)
            if k.get("icerik") is not None:
                ky["icerik"] = _yuva(k.get("icerik"), tanim)
            if k.get("anahtar"):
                ky["anahtar"] = {h: _yuva(v, tanim) for h, v in k["anahtar"].items()}
            katmanlar.append(ky)
        yeni["katmanlar"] = katmanlar
    return yeni


def _id_ile_bul(dugum, aranan):
    """Agacta id'si 'aranan' olan ilk dugum (referans cozumu icin)."""
    if not isinstance(dugum, dict):
        return None
    if dugum.get("id") == aranan and dugum.get("tur") != "referans":
        return dugum
    for alt in cocuklar(dugum):
        bulunan = _id_ile_bul(alt, aranan)
        if bulunan is not None:
            return bulunan
    return None


def _referanslari_parcaya(kok, parcalar):
    """referans dugumlerini parcaya cevirir (§3.11). DONER (kok, parcalar)."""
    yeni_parcalar = list(parcalar)
    adlar = {p.get("ad") for p in yeni_parcalar}

    def cevir(d):
        if not isinstance(d, dict):
            return d
        if d.get("tur") == "referans":
            hedef = _id_ile_bul(kok, d.get("id"))
            if hedef is None:
                return d          # denetim 'tanimsiz referans' der
            if d.get("id") not in adlar:
                yeni_parcalar.append({"ad": d.get("id"), "dugum": copy.deepcopy(hedef)})
                adlar.add(d.get("id"))
            return {"tur": "bilesen", "ad": d.get("id")}
        return _cocuklari_degistir(d, cevir)

    return cevir(kok), yeni_parcalar


def normalize(spec, agac):
    """
    Agacin normalize kopyasi: butun yuvalar acik dugum, eksik listeler bos
    liste, referanslar parca. Girdi DEGISMEZ. agac: {"kok", "parcalar",
    "gruplar", ...}.
    """
    tanim = tanimlar(spec, agac)
    kok = _yuva(agac.get("kok"), tanim)
    parcalar = [{"ad": p.get("ad"), "dugum": _yuva(p.get("dugum"), tanim)}
                for p in agac.get("parcalar") or []]
    kok, parcalar = _referanslari_parcaya(kok, parcalar)
    yeni = {k: copy.deepcopy(v) for k, v in agac.items()
            if k not in ("kok", "parcalar")}
    yeni["kok"] = kok
    yeni["parcalar"] = parcalar
    yeni["gruplar"] = copy.deepcopy(agac.get("gruplar") or [])
    return yeni


# ----------------------------------------------------------------------------
# gezinti yardimcilari
# ----------------------------------------------------------------------------

def cocuklar(dugum):
    """Dugumun dogrudan alt dugumleri (yuvalar), sirali."""
    tur = dugum.get("tur")
    alt = []
    if tur == "kafes":
        alt += [v for _h, v in sorted((dugum.get("anahtar") or {}).items())]
        alt.append(dugum.get("dis"))
    elif tur == "kap":
        alt.append(dugum.get("ic"))
        alt += [y.get("icerik") for y in dugum.get("yerlesimler") or []]
        for h in dugum.get("halkalar") or []:
            alt.append(h.get("icerik"))
            alt += [y.get("icerik") for y in h.get("yerlesimler") or []]
        alt.append(dugum.get("dis"))
    elif tur == "eksenel":
        alt.append(dugum.get("icerik"))
        for k in dugum.get("katmanlar") or []:
            alt.append(k.get("icerik"))
            alt += [v for _h, v in sorted((k.get("anahtar") or {}).items())]
    return [a for a in alt if isinstance(a, dict)]


def _cocuklari_degistir(d, islev):
    """Dugumun kopyasi; her yuvaya islev(yuva) uygulanir."""
    yeni = dict(d)
    tur = d.get("tur")
    if tur == "kafes":
        yeni["anahtar"] = {h: islev(v) for h, v in (d.get("anahtar") or {}).items()}
        if "dis" in d:
            yeni["dis"] = islev(d["dis"])
    elif tur == "kap":
        yeni["ic"] = islev(d.get("ic"))
        yeni["yerlesimler"] = [dict(y, icerik=islev(y.get("icerik")))
                               for y in d.get("yerlesimler") or []]
        yeni["halkalar"] = [dict(h, icerik=islev(h.get("icerik")),
                                 yerlesimler=[dict(y, icerik=islev(y.get("icerik")))
                                              for y in h.get("yerlesimler") or []])
                            for h in d.get("halkalar") or []]
        if "dis" in d:
            yeni["dis"] = islev(d["dis"])
    elif tur == "eksenel":
        yeni["icerik"] = islev(d.get("icerik"))
        yeni["katmanlar"] = [dict(k, icerik=islev(k.get("icerik")),
                                  **({"anahtar": {h: islev(v) for h, v in k["anahtar"].items()}}
                                     if k.get("anahtar") else {}))
                             for k in d.get("katmanlar") or []]
    return yeni


def dugum_degistir(dugum, islev):
    """Agacin kopyasi: her dugume (alttan uste) islev(dugum) -> yeni dugum."""
    if not isinstance(dugum, dict):
        return dugum
    return islev(_cocuklari_degistir(dugum, lambda d: dugum_degistir(d, islev)))
