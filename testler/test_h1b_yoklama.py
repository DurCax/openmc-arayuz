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


def test_yokla_bellekli_ve_paylasilan_modeli_kullanir(monkeypatch):
    print("\n[H1b-Y6] yokla: ayni icerikte bellekten (kurmaz), model onbellekten (salt okuma)")
    from cekirdek import kurucu, onbellek, sema, uygunluk_bellek
    from cekirdek.geometri import yoklama
    spec = sema.yukle(os.path.join(ORNEK, "pwr_kare_altigen_halka.json"))
    uygunluk_bellek.temizle()
    onbellek.temizle()
    ilk = yoklama.yokla(spec, n=200)
    sayac = [0]
    asil = kurucu.kur

    def sayan(*a, **k):
        sayac[0] += 1
        return asil(*a, **k)
    monkeypatch.setattr(kurucu, "kur", sayan)
    ikinci = yoklama.yokla(spec, n=200)
    kontrol("ikinci cagri model kurmaz", sayac[0] == 0, "kur=%d" % sayac[0])
    kontrol("ayni sonuc ve metin", (_ozet(ilk[0].bosluklar), _ozet(ilk[0].ortusmeler), ilk[0].n,
                                    ilk[1]) == (_ozet(ikinci[0].bosluklar),
                                                _ozet(ikinci[0].ortusmeler), ikinci[0].n,
                                                ikinci[1]))
    uygunluk_bellek.temizle()
    yoklama.yokla(spec, n=200)
    kontrol("bellek bosken de model onbellekten (kur yok)", sayac[0] == 0, "kur=%d" % sayac[0])
    yoklama.yokla(spec, n=201)
    kontrol("farkli n: yeniden yoklar (model yine onbellekte)", sayac[0] == 0)


HIZLI.append(test_yokla_bellekli_ve_paylasilan_modeli_kullanir)


def test_iceren_hucreler_kahinle_ayni():
    print("\n[H1b-Y7] _iceren_hucreler (guc_faktor kullanir) tekil kahinle ayni")
    import numpy as np
    from cekirdek.geometri import yoklama
    from testler.test_geometri_dogrulama import ortusen_model
    geo, kutu, _i = _girdi(ortusen_model())
    rnd = random.Random(9)
    (x0, y0, _z0), (x1, y1, _z1) = kutu
    fark = 0
    for _k in range(300):
        p = np.array([rnd.uniform(x0, x1), rnd.uniform(y0, y1), 0.0])
        fark += [c.id for c in yoklama._iceren_hucreler(geo.root_universe, p)] != \
            [c.id for c in _kahin_iceren(geo.root_universe, p)]
    kontrol("300 noktada fark yok", fark == 0, "fark=%d" % fark)


HIZLI.append(test_iceren_hucreler_kahinle_ayni)


# ---------------------------------------------------------------------------
# inceleme (python-reviewer MEDIUM 1-3): her yuzey turu, sinir, NaN, yedek yol,
# parcali isleme, tek nokta hizi
# ---------------------------------------------------------------------------

def _yuzeyler():
    """(ad, yuzey, yuzey ustundeki tam noktalar): beyaz liste + yedek yol turleri."""
    import openmc
    return [
        ("Plane", openmc.Plane(a=1.0, b=2.0, c=0.5, d=0.25), [(0.25, 0.0, 0.0)]),
        ("XPlane", openmc.XPlane(0.5), [(0.5, 0.3, -1.0)]),
        ("YPlane", openmc.YPlane(-0.5), [(1.0, -0.5, 0.0)]),
        ("ZPlane", openmc.ZPlane(0.0), [(0.3, 0.2, 0.0)]),
        ("XCylinder", openmc.XCylinder(y0=0.5, z0=0.0, r=1.0), [(0.0, 1.5, 0.0), (1.0, -0.5, 0.0)]),
        ("YCylinder", openmc.YCylinder(x0=0.0, z0=0.0, r=1.0), [(1.0, 0.7, 0.0), (0.0, 0.1, -1.0)]),
        ("ZCylinder", openmc.ZCylinder(x0=0.5, y0=0.0, r=1.0), [(1.5, 0.0, 0.0), (-0.5, 0.0, 0.3)]),
        ("Sphere", openmc.Sphere(r=1.0), [(1.0, 0.0, 0.0), (0.0, -1.0, 0.0)]),
        ("XCone", openmc.XCone(r2=1.0), [(1.0, 1.0, 0.0)]),
        ("YCone", openmc.YCone(r2=1.0), [(1.0, 1.0, 0.0)]),
        ("ZCone", openmc.ZCone(r2=1.0), [(0.0, 1.0, 1.0)]),
        ("Quadric", openmc.Quadric(a=1.0, b=2.0, c=0.5, f=0.3, g=0.2, j=0.1, k=-1.0),
         [(0.0, 0.0, 0.0)]),
        ("XTorus", openmc.XTorus(a=1.0, b=0.4, c=0.4), [(0.0, 1.4, 0.0)]),
    ]


def _maske_ve_tekil(b, P):
    import numpy as np
    from cekirdek.geometri import yoklama
    maske = yoklama.bolge_maskesi(b, (P[:, 0], P[:, 1], P[:, 2]), P, {})
    tekil = np.array([tuple(float(v) for v in p) in b for p in P])
    return maske, tekil


def _yuzey_noktalari(ustunde):
    import numpy as np
    rnd = np.random.default_rng(5)
    P = rnd.uniform(-2.0, 2.0, size=(300, 3))
    nan = np.array([[float("nan"), 0.0, 0.0], [0.0, float("nan"), float("nan")]])
    return np.vstack([P, np.array(ustunde, dtype=float), nan])


def test_her_yuzey_turunde_sinir_ve_nan_tekil_ile_ayni():
    print("\n[H1b-Y8] bolge_maskesi: her yuzey turu, yuzey ustu (deger 0) ve NaN noktalar")
    import numpy as np
    for ad, s, ustunde in _yuzeyler():
        P = _yuzey_noktalari(ustunde)
        sifir = [float(s.evaluate(tuple(p))) == 0.0 for p in np.array(ustunde, dtype=float)]
        for taraf, b in (("+", +s), ("-", -s), ("~-", ~(-s))):
            maske, tekil = _maske_ve_tekil(b, P)
            kontrol("%s %s: ayni" % (ad, taraf), np.array_equal(maske, tekil),
                    "fark=%d" % int((maske != tekil).sum()))
        if ad not in ("Quadric", "XTorus"):
            kontrol("%s: yuzey ustu noktalarda deger tam 0" % ad, all(sifir), "-> %s" % sifir)


def test_beyaz_liste_bosken_yedek_yol_calisir_ve_ayni(monkeypatch):
    print("\n[H1b-Y9] beyaz liste bos: butun yuzeyler tekil yedek yoldan, sonuc ayni")
    import numpy as np
    from cekirdek.geometri import yoklama
    tekil_cagri = [0]
    asil = yoklama._tekil_degerler

    def sayan(yuzey, P):
        tekil_cagri[0] += 1
        return asil(yuzey, P)
    monkeypatch.setattr(yoklama, "_tekil_degerler", sayan)
    monkeypatch.setattr(yoklama, "_VEKTOREL_YUZEY_ADLARI", ())
    for ad, s, ustunde in _yuzeyler():
        P = _yuzey_noktalari(ustunde)
        maske, tekil = _maske_ve_tekil(-s & +s | ~(+s), P)
        kontrol("%s: yedek yolla ayni" % ad, np.array_equal(maske, tekil))
    kontrol("yedek yol gercekten kullanildi", tekil_cagri[0] >= len(_yuzeyler()),
            "cagri=%d" % tekil_cagri[0])


def test_parcali_yoklama_ayni_ve_parca_siniri_asilmaz(monkeypatch):
    print("\n[H1b-Y10] nokta_yoklama parcalarla: sonuc ayni, toplu cagri parca boyunu asmaz")
    from cekirdek.geometri import yoklama
    from testler.test_geometri_dogrulama import ortusen_model
    geo, kutu, icinde = _girdi(ortusen_model())
    tam = yoklama.nokta_yoklama(geo, 500, 3, kutu, icinde)
    en_buyuk = [0]
    asil = yoklama._in_toplu

    def izleyen(evren, P, *a, **k):
        en_buyuk[0] = max(en_buyuk[0], len(P))
        return asil(evren, P, *a, **k)
    monkeypatch.setattr(yoklama, "_PARCA", 64)
    monkeypatch.setattr(yoklama, "_in_toplu", izleyen)
    parcali = yoklama.nokta_yoklama(geo, 500, 3, kutu, icinde)
    kontrol("ayni sonuc", (tam.n, _ozet(tam.bosluklar), _ozet(tam.ortusmeler))
            == (parcali.n, _ozet(parcali.bosluklar), _ozet(parcali.ortusmeler)))
    kontrol("toplu cagri <= 64 nokta", en_buyuk[0] <= 64, "-> %d" % en_buyuk[0])


def test_yavas_tek_nokta_sorgusu_tekil_kadar_hizli():
    print("\n[H1b-Y11] _iceren_hucreler (tek nokta, guc_faktor): CPU <= 1.5 x tekil kahin (SFR kok)")
    import time
    import numpy as np
    from cekirdek import kurucu, sema
    from cekirdek.geometri import yoklama
    model, bilgi = kurucu.kur(sema.yukle(os.path.join(ORNEK, "sfr_met1000_kor.json")))
    gx, gy = bilgi["sinir_kutu"]
    rnd = random.Random(1)
    P = [np.array([rnd.uniform(-gx / 2, gx / 2), rnd.uniform(-gy / 2, gy / 2), 0.0])
         for _i in range(40)]
    evren = model.geometry.root_universe
    sure = {}
    for ad, f in (("yeni", yoklama._iceren_hucreler), ("kahin", _kahin_iceren)):
        t = time.process_time()
        for p in P:
            f(evren, p)
        sure[ad] = time.process_time() - t
    # gerekce: H1b ilk surumu tek noktada 13x yavasti (numpy sabit maliyeti); %50 olcum payi
    kontrol("yeni <= 1.5 x kahin", sure["yeni"] <= 1.5 * sure["kahin"],
            "%.3f / %.3f s" % (sure["yeni"], sure["kahin"]))


HIZLI += [test_her_yuzey_turunde_sinir_ve_nan_tekil_ile_ayni,
          test_beyaz_liste_bosken_yedek_yol_calisir_ve_ayni,
          test_parcali_yoklama_ayni_ve_parca_siniri_asilmaz]
YAVAS.append(test_yavas_tek_nokta_sorgusu_tekil_kadar_hizli)
