# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/ice_aktar_kap.py  --  ice_aktar'in kap deseni: bolgeler, delikler, z
================================================================================

 geometri/ice_aktar.py'nin yardimcisi (dosya boyutu). Bir evrenin hucreleri
 -> kap dugumu:
   delik hucreleri  "g:<yerlesim>#<i>" adli hucreler (kurucu R10)
   bolge zinciri    ic (-S0 ~delikler), halkalar (+S(i-1) -S(i) ~delikler),
                    kok disinda dis (+S(n))
   z dilimleri      ayni 2B bolgenin farkli z araligindaki hucreleri ->
                    eksenel yigin (yalniz kokun ic'inde; R7)
   sinir            kokun en dis yuzeyinin ve z duzlemlerinin BC'si
================================================================================
"""

import math

from cekirdek.geometri.ice_aktar import (PAY, Desteklenmez, _DELIK_ADI, _atomlar, _ayni,
                                         _merkezde)


def _delik_mi(h):
    return bool(_DELIK_ADI.match(h.name or ""))


def _imza(atom, delik_sekilleri):
    """(ic sekli, [delik olmayan dis sekiller]) -- 2B bolge imzasi."""
    dislar = [d for d in atom["dislar"] if not any(_ayni(d, s) for s in delik_sekilleri)]
    return atom["ic"], dislar


def _gruplar(bolge_hucreleri, delik_sekilleri):
    """Ayni 2B bolgedeki hucreler (z dilimleri) birlikte: [(ic, dislar, [(z, hucre)])]."""
    gruplar = []
    for h, a in bolge_hucreleri:
        ic, dislar = _imza(a, delik_sekilleri)
        if len(dislar) > 1:
            raise Desteklenmez("hücre %d birden çok iç sınır dışlıyor (tanınmayan desen)" % h.id)
        for g in gruplar:
            if _ayni(g[0], ic) and len(g[1]) == len(dislar) and all(
                    _ayni(x, y) for x, y in zip(g[1], dislar)):
                g[2].append((a["z"], h))
                break
        else:
            gruplar.append((ic, dislar, [(a["z"], h)]))
    return gruplar


def _zincir(gruplar, kok):
    """Gruplari icten disa siralar: [ic, halka1, ...], dis grubu (kok degilse)."""
    ic = [g for g in gruplar if g[0] is not None and not g[1]]
    if len(ic) != 1:
        raise Desteklenmez("kabın iç bölgesi tek ve dışlamasız olmalı (%d aday)" % len(ic))
    zincir, kalan = [ic[0]], [g for g in gruplar if g is not ic[0]]
    while kalan:
        sonraki = [g for g in kalan if g[1] and _ayni(g[1][0], zincir[-1][0])]
        if len(sonraki) != 1:
            raise Desteklenmez("kap halkaları eş merkezli bir zincir oluşturmuyor")
        zincir.append(sonraki[0])
        kalan.remove(sonraki[0])
    dis = None
    if zincir[-1][0] is None:
        dis = zincir.pop()
    if kok and dis is not None:
        raise Desteklenmez("kökte dış (sınırsız) hücre var")
    if not kok and dis is None:
        raise Desteklenmez("kök olmayan kabın dış hücresi yok")
    for g in zincir:
        if not _merkezde(g[0]):
            raise Desteklenmez("kap bölgesi merkezli değil")
    return zincir, dis


def _yerlesimler(d, delikler, bolge_sekli, onceki):
    """Bolgeye ait delik hucreleri -> liste yerlesimleri."""
    from cekirdek.geometri import kesit as _k
    gruplu = {}
    for h, a in delikler:
        m, kes = a["ic"]
        icinde = _k.icinde(bolge_sekli[1], m[0], m[1]) and (
            onceki is None or not _k.icinde(onceki[1], m[0], m[1], pay=-PAY))
        if icinde:
            ad = _DELIK_ADI.match(h.name).group(1)
            gruplu.setdefault(ad, []).append((int(_DELIK_ADI.match(h.name).group(2)), h, m, kes))
    return [_yerlesim(d, ad, sorted(liste, key=lambda x: x[0]))
            for ad, liste in sorted(gruplu.items())]


def _yerlesim(d, ad, liste):
    icerikler = [d.dolgu(h.fill) for _i, h, _m, _k in liste]
    if any(x != icerikler[0] for x in icerikler):
        raise Desteklenmez("'%s' yerleşiminin örnekleri farklı içerikli" % ad)
    kes = dict(liste[0][3])
    y = {"ad": ad, "mod": "liste", "konumlar": [[m[0], m[1]] for _i, _h, m, _k in liste],
         "kesit": kes, "icerik": icerikler[0]}
    ofsetler = []
    for _i, h, m, _k in liste:
        t = [float(v) for v in (h.translation if h.translation is not None else (m[0], m[1], 0))]
        if abs(t[0] - m[0]) > PAY or abs(t[1] - m[1]) > PAY:
            raise Desteklenmez("'%s' deliğinin içeriği delik merkezinden ötelenmiş" % ad)
        r = h.rotation
        if r is not None and any(abs(float(v)) > PAY for v in r):
            if abs(float(r[0])) > PAY or abs(float(r[1])) > PAY:
                raise Desteklenmez("yalnız z ekseni etrafında dönme desteklenir")
            ofsetler.append(float(r[2]) - math.degrees(math.atan2(-m[1], -m[0])))
    if ofsetler:
        if len(ofsetler) != len(liste) or kes.get("sekil") != "silindir":
            raise Desteklenmez("'%s': döndürülen delik daire olmalı ve her örnek dönmeli" % ad)
        D = ofsetler[0]
        if any(abs(((o - D + 180.0) % 360.0) - 180.0) > 1e-6 for o in ofsetler):
            raise Desteklenmez("'%s' örneklerinin dönmesi 'kora bakan' desene uymuyor" % ad)
        y["bakis"] = {"tur": "merkez", "merkez": [0.0, 0.0]}
        if abs(((D + 180.0) % 360.0) - 180.0) > 1e-9:
            y["donme_ofset"] = D
    return y


def _icerik(d, dilimler, kok):
    """Grubun z dilimleri -> tek icerik ya da (kokte) eksenel yigin."""
    dilimler = sorted(dilimler, key=lambda zh: zh[0][0])
    if len(dilimler) == 1:
        return d._donusumlu(dilimler[0][1], d.dolgu(dilimler[0][1].fill))
    if not kok:
        raise Desteklenmez("kök dışında z dilimli bölge desteklenmiyor")
    katmanlar = []
    for i, ((z0, z1), h) in enumerate(dilimler):
        if i and abs(z0 - dilimler[i - 1][0][1]) > PAY:
            raise Desteklenmez("eksenel dilimler bitişik değil")
        katmanlar.append({"ad": h.name or "katman %d" % (i + 1), "yukseklik": z1 - z0,
                          "icerik": d._donusumlu(h, d.dolgu(h.fill))})
    return {"tur": "eksenel", "id": "eksenel", "icerik": katmanlar[0]["icerik"],
            "katmanlar": katmanlar}


def _z_araligi(gruplar):
    zler = {zh[0] for g in gruplar for zh in g[2]}
    alt = min(z[0] for z in zler)
    ust = max(z[1] for z in zler)
    return alt, ust


def _periyodik_es_dogrula(s):
    """Periyodik yuzeyin esi karsit yuz olmali (-x <-> +x, -y <-> +y). Donel
    periyodiklik (x <-> y) ya da baska es agacta temsil edilmez -> Desteklenmez."""
    import openmc
    if not isinstance(s, (openmc.XPlane, openmc.YPlane)):
        raise Desteklenmez("periyodik sınır yalnız eksene dik düzlemlerde içe aktarılır "
                           "(yüzey %d, %s)" % (s.id, s.type))
    es = getattr(s, "periodic_surface", None)
    if es is None:
        return
    eksen = "x0" if isinstance(s, openmc.XPlane) else "y0"
    konum = float(getattr(s, eksen))
    karsit = type(es) is type(s) and abs(konum) > PAY and \
        abs(float(getattr(es, eksen)) + konum) <= PAY * max(1.0, abs(konum))
    if not karsit:
        raise Desteklenmez("periyodik eş karşıt yüz değil (yüzey %d <-> %d); dönel "
                           "periyodiklik içe aktarılmaz" % (s.id, es.id))


def _sinir(hucreler):
    """Kokun BC'leri: dis yuzeyler (BC'li silindir/duzlem) ve z duzlemleri."""
    import openmc
    yan, yuz, alt, ust = set(), {}, None, None
    for h in hucreler:
        for s in (h.region.get_surfaces().values() if h.region is not None else ()):
            bc = getattr(s, "boundary_type", "transmission")
            if bc == "transmission":
                continue
            if isinstance(s, openmc.ZPlane):
                if s.z0 < 0:
                    alt = bc
                else:
                    ust = bc
                continue
            yan.add(bc)
            if bc == "periodic":
                _periyodik_es_dogrula(s)
            if isinstance(s, (openmc.XPlane, openmc.YPlane)):
                eksen, konum = ("x", s.x0) if isinstance(s, openmc.XPlane) else ("y", s.y0)
                yuz[("-" if konum < 0 else "+") + eksen] = bc
    if len(yan) > 1 and len(yuz) != 4:
        raise Desteklenmez("yan sınırda yüzeyler farklı sınır koşulu taşıyor; yüz başına "
                           "sınır yalnız dikdörtgen dış sınırda içe aktarılır")
    sinir = {"yan": sorted(yan)[0] if yan else "vacuum"}
    if len(yan) > 1:
        sinir["yuzler"] = yuz
    if alt:
        sinir["alt"] = alt
    if ust:
        sinir["ust"] = ust
    return sinir


def kap_dugumu(d, hucreler, kok):
    """Evrenin hucreleri -> kap dugumu (bkz. modul notu)."""
    if kok and sum(1 for h in hucreler if h.translation is not None and not _delik_mi(h)) > 1:
        raise Desteklenmez("kafes zarflı altıgen tam kor (konum hücreleri, R3b) içe "
                           "aktarılmıyor; şablon (altigen_kafes) olarak yeniden kurun")
    atomlu = [(h, _atomlar(h.region)) for h in hucreler]
    if not kok and sum(1 for _h, a in atomlu if a["ic"] is not None and not a["dislar"]) > 2:
        raise Desteklenmez("tanınmayan çok hücreli evren (%d ayrık bölge; ör. plaka "
                           "elemanı ya da kontrol çubuğu)" % len(hucreler))
    delikler = [(h, a) for h, a in atomlu if _delik_mi(h)]
    for h, a in delikler:
        if a["ic"] is None:
            raise Desteklenmez("delik hücresi %d kapalı bir kesit değil" % h.id)
    delik_sekilleri = [a["ic"] for _h, a in delikler]
    gruplar = _gruplar([(h, a) for h, a in atomlu if not _delik_mi(h)], delik_sekilleri)
    zincir, dis = _zincir(gruplar, kok)
    kap = {"tur": "kap", "id": "kok" if kok else "kap_%d" % hucreler[0].id,
           "kesit": dict(zincir[0][0][1]), "halkalar": [],
           "ic": _icerik(d, zincir[0][2], kok),
           "yerlesimler": _yerlesimler(d, delikler, zincir[0][0], None)}
    for i, g in enumerate(zincir[1:], start=1):
        tam = [zh for zh in g[2]]
        if len(tam) != 1:
            raise Desteklenmez("halka bölgesi z dilimli (yalnız kökün iç'i dilimlenebilir)")
        kap["halkalar"].append({"dis": dict(g[0][1]), "icerik": _icerik(d, tam, False),
                                "yerlesimler": _yerlesimler(d, delikler, g[0], zincir[i - 1][0])})
    if not kok:
        kap["dis"] = _icerik(d, dis[2], False)
        return kap
    alt, ust = _z_araligi(zincir)
    if math.isinf(alt) != math.isinf(ust) or (not math.isinf(alt) and abs(alt + ust) > PAY):
        raise Desteklenmez("model z = 0 etrafında merkezli değil (%g … %g)" % (alt, ust))
    yigin = kap["ic"].get("tur") == "eksenel"
    kap["yukseklik"] = None if (yigin or math.isinf(alt)) else ust - alt
    kap["sinir"] = _sinir(hucreler)
    if math.isinf(alt):
        kap["sinir"] = {"yan": kap["sinir"]["yan"]}
    return kap
