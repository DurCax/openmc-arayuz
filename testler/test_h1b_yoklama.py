# -*- coding: utf-8 -*-
"""
 test_h1b_yoklama.py  --  v3 H1b: toplu (vektorel) nokta yoklamasi esdegerligi

 cekirdek/geometri/yoklama.nokta_yoklama noktalari tek tek openmc
 Region.__contains__ ile yokluyordu (SFR-MET1000, 600 nokta: ~11.5 s CPU).
 Yeni yol ayni noktalari evren basina TOPLU degerlendirir (yuzey denklemi
 numpy dizisinde bir kez). Bu test eski algoritmayi KAHIN olarak tasir ve
 her ornekte bosluk/ortusme listelerinin (nokta + hucre yolu) birebir ayni
 oldugunu dogrular; kasitli ortusen/bos modellerde de.
"""

import os
import random

from testler.ortak_test import kontrol, ORNEK

_HIZLI_N = 40              # hizli esdegerlik: ornek basina nokta (kahin tekil ve yavas)
_YAVAS_N = 600             # yavas esdegerlik: dogrulamanin kullandigi sayi (agac.YOKLAMA_N)


# ---------------------------------------------------------------------------
# kahin: H1b oncesi tekil algoritma (degistirmeden)
# ---------------------------------------------------------------------------

def _kahin_iceren(evren, p):
    nokta = tuple(float(v) for v in p)
    return [c for c in evren.cells.values() if c.region is None or nokta in c.region]


def _kahin_yerel(hucre, p):
    import numpy as np
    if hucre.translation is not None:
        p = p - np.asarray(hucre.translation, dtype=float)
    if hucre.rotation is not None:
        p = np.asarray(hucre.rotation_matrix, dtype=float) @ p
    return p


def _kahin_in(evren, p, kok, icinde, derinlik=0):
    yol = []
    while derinlik < 60:
        icerenler = _kahin_iceren(evren, p)
        if not icerenler:
            if kok and icinde is not None and not icinde(p[0], p[1]):
                return "dis", yol, p
            return ("dis" if kok and icinde is None else "bosluk"), yol, p
        if len(icerenler) > 1:
            return "ortusme", yol + icerenler, p
        hucre = icerenler[0]
        yol.append(hucre)
        kok = False
        if hucre.fill_type == "universe":
            p, evren = _kahin_yerel(hucre, p), hucre.fill
        elif hucre.fill_type == "lattice":
            p = _kahin_yerel(hucre, p)
            kafes = hucre.fill
            idx, p = kafes.find_element(p)
            if kafes.is_valid_index(idx):
                evren = kafes.get_universe(idx)
            elif kafes.outer is not None:
                evren = kafes.outer
            else:
                return "bosluk", yol, p
        else:
            return "tamam", yol, p
        derinlik += 1
    return "tamam", yol, p


def _kahin_yoklama(geo, n, tohum, kutu, icinde):
    import numpy as np
    (x0, y0, z0), (x1, y1, z1) = kutu
    rnd = random.Random(tohum)
    bosluk, ortusme, icerde, izler = [], [], 0, []
    for _i in range(int(n)):
        p = np.array([rnd.uniform(x0, x1), rnd.uniform(y0, y1),
                      rnd.uniform(z0, z1) if z1 > z0 else z0])
        durum, hucreler, _q = _kahin_in(geo.root_universe, p, True, icinde)
        izler.append((durum, [h.id for h in hucreler]))
        if durum == "dis":
            continue
        icerde += 1
        if durum == "bosluk":
            bosluk.append((tuple(p), hucreler))
        elif durum == "ortusme":
            ortusme.append((tuple(p), hucreler))
    return icerde, bosluk, ortusme, izler


# ---------------------------------------------------------------------------
# yardimcilar
# ---------------------------------------------------------------------------

def _girdi(spec):
    """yokla() ile ayni girdi: (geometri, kutu, dis sinir)."""
    from cekirdek import geometri, kurucu
    from cekirdek.geometri import yoklama
    model, _b = kurucu.kur(spec)
    m = geometri.model(spec)
    gx, gy = geometri.sinir_kutusu(m)
    h = geometri.yukseklik(m)
    z = h / 2.0 * (1.0 - 1.0e-9) if h else 0.0
    return model.geometry, ((-gx / 2.0, -gy / 2.0, -z), (gx / 2.0, gy / 2.0, z)), \
        yoklama._dis_sinir(m)


def _ozet(liste):
    return [(p, [h.id for h in hucreler]) for p, hucreler in liste]


def _noktalar(n, tohum, kutu):
    (x0, y0, z0), (x1, y1, z1) = kutu
    rnd = random.Random(tohum)
    for _i in range(int(n)):
        yield (rnd.uniform(x0, x1), rnd.uniform(y0, y1), rnd.uniform(z0, z1) if z1 > z0 else z0)


def _karsilastir(ad, spec, n, tohum=1):
    import numpy as np
    from cekirdek.geometri import yoklama
    geo, kutu, icinde = _girdi(spec)
    yeni = yoklama.nokta_yoklama(geo, n, tohum, kutu, icinde)
    icerde, bosluk, ortusme, izler = _kahin_yoklama(geo, n, tohum, kutu, icinde)
    P = np.array([p for p in _noktalar(n, tohum, kutu)])
    toplu = [(d, [h.id for h in y]) for d, y, _q in
             yoklama._in_toplu(geo.root_universe, P, True, icinde)]
    kontrol("%s: her noktada durum ve TAM hucre yolu ayni" % ad, toplu == izler)
    kontrol("%s: icerdeki nokta sayisi ayni" % ad, yeni.n == icerde,
            "yeni %d, kahin %d" % (yeni.n, icerde))
    kontrol("%s: bosluklar (nokta + hucre yolu) ayni" % ad,
            _ozet(yeni.bosluklar) == _ozet(bosluk), "%d / %d" % (len(yeni.bosluklar), len(bosluk)))
    kontrol("%s: ortusmeler (nokta + hucre yolu) ayni" % ad,
            _ozet(yeni.ortusmeler) == _ozet(ortusme),
            "%d / %d" % (len(yeni.ortusmeler), len(ortusme)))


def _ornek_specleri():
    from cekirdek import sema
    for ad in sorted(os.listdir(ORNEK)):
        if ad.endswith(".json"):
            yield ad[:-5], sema.yukle(os.path.join(ORNEK, ad))


# ---------------------------------------------------------------------------
# testler
# ---------------------------------------------------------------------------

def test_toplu_yoklama_tum_orneklerde_kahinle_ayni():
    print("\n[H1b-Y1] nokta_yoklama: tum orneklerde tekil kahinle birebir (n=%d)" % _HIZLI_N)
    for ad, spec in _ornek_specleri():
        _karsilastir(ad, spec, _HIZLI_N)


def test_toplu_yoklama_kasitli_ortusme_ve_boslukta_ayni():
    print("\n[H1b-Y2] kasitli ortusen / bos modelde toplu yoklama kahinle ayni")
    from testler.test_geometri_dogrulama import bos_model, ortusen_model
    _karsilastir("ortusen", ortusen_model(), 1500, tohum=3)
    _karsilastir("bos", bos_model(), 1500, tohum=2)


def test_tek_nokta_in_kahinle_ayni():
    print("\n[H1b-Y3] _in (tek nokta, ice_aktar testinin kullandigi) kahinle ayni")
    import numpy as np
    from cekirdek.geometri import yoklama
    from testler.test_geometri_dogrulama import ortusen_model
    geo, kutu, icinde = _girdi(ortusen_model())
    rnd = random.Random(5)
    (x0, y0, _z0), (x1, y1, _z1) = kutu
    for _i in range(200):
        p = np.array([rnd.uniform(x0, x1), rnd.uniform(y0, y1), 0.0])
        d1, y1_, _q1 = yoklama._in(geo.root_universe, p, True, icinde)
        d2, y2_, _q2 = _kahin_in(geo.root_universe, p, True, icinde)
        if (d1, [h.id for h in y1_]) != (d2, [h.id for h in y2_]):
            kontrol("tek nokta ayni", False, "%s: %s / %s" % (p, d1, d2))
            return
    kontrol("200 tek noktada durum ve yol ayni", True)


def test_bolge_maskesi_tekil_icermeyle_ayni():
    print("\n[H1b-Y4] bolge_maskesi: Halfspace/Intersection/Union/Complement tekil 'in' ile ayni")
    import numpy as np
    import openmc
    from cekirdek.geometri import yoklama
    s1, s2 = openmc.ZCylinder(r=1.0), openmc.Plane(a=1.0, b=2.0, c=0.5, d=0.3)
    s3, s4 = openmc.XPlane(0.2), openmc.Sphere(r=1.5)
    kon = openmc.ZCone(r2=0.5)                # vektorel listede yok: tekil yedek yol
    bolgeler = [-s1, +s2, -s1 & +s3, -s1 | +s2, ~(-s1 & +s3), (-s4 & ~(+s2 | -s3)) | +kon,
                openmc.Intersection([]), openmc.Union([])]
    rnd = np.random.default_rng(3)
    P = rnd.uniform(-2.0, 2.0, size=(500, 3))
    xyz = (P[:, 0], P[:, 1], P[:, 2])
    for i, b in enumerate(bolgeler):
        maske = yoklama.bolge_maskesi(b, xyz, P, {})
        tekil = np.array([tuple(float(v) for v in p) in b for p in P])
        kontrol("bolge %d: maske tekil sonucla ayni" % i, np.array_equal(maske, tekil))


def test_yavas_toplu_yoklama_tum_orneklerde_600_nokta():
    print("\n[H1b-Y5] nokta_yoklama: tum orneklerde n=%d kahinle birebir" % _YAVAS_N)
    for ad, spec in _ornek_specleri():
        _karsilastir(ad, spec, _YAVAS_N)


HIZLI = [test_toplu_yoklama_tum_orneklerde_kahinle_ayni,
         test_toplu_yoklama_kasitli_ortusme_ve_boslukta_ayni, test_tek_nokta_in_kahinle_ayni,
         test_bolge_maskesi_tekil_icermeyle_ayni]
YAVAS = [test_yavas_toplu_yoklama_tum_orneklerde_600_nokta]
