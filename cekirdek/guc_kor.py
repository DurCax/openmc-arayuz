# -*- coding: utf-8 -*-
"""
================================================================================
 guc_kor.py  --  Kafessiz kor duzeyi: altigen_kafes demet konumlari
================================================================================

 altigen_kafes korunda kor duzeyinde KAFES YOKTUR (cekirdek/altigen_kor.py):
 her demet konumu kendi altigen prizmasiyla bir kok hucresidir ve demet bu
 hucreye `translation = (x, y, 0)` ile yerlesir. Distribcell yolunda bu duzey
 ('level 1', 'cell', 'id') olarak gorunur, 'lat' olarak DEGIL. Yalniz kafes
 duzeylerinden anahtar kuran eski kod 7 demetin 133 cubugunu 19 anahtara
 katliyordu (D1-A bulgu 1; olculdu, testler/test_guc_altigen.py).

 ESLEME (kafessiz, oteleme merkezli)
   kok hucre -> cell.translation -> altigen_kor.kor_merkezleri(n, P, yon)
   sirasindaki konum -> anahtar (halka, sira) = sorted(altigen.konumlar(n, yon))
   Eksenel katman hucreleri AYNI otelemededir, ayni anahtara duser (katman
   ornekleri guc.dagilim_oku'da dilim dilim toplanir).

 n, P, yon statepoint'te yazili degildir; summary geometrisinden OLCULUR:
   Her konum hucresinin bolgesi 6 duzlemin kesisimidir (3 dogrultu x 2):
   dogrultu basina iki duzlemin ortasi merkezin izdusumu, arasi P'dir; yuz
   normallerinin acisi 0 (mod 60) ise kor yonelimi 'x', 30 ise 'y'
   (altigen_kor.yuz_normali_acilari). Halka sayisi, TUM konum hucrelerinin
   (malzemeyle dolu, translation'i None olanlar dahil) merkezlerini iceren en
   kucuk halka sayisidir -- boylece dis halka bos olsa bile "distan halka"
   numarasi kaymaz. Yansitici hucresi (tumleyen iceren bolge) sayilmaz.
================================================================================
"""

import math
from dataclasses import dataclass

from cekirdek.ceviri import _

KOK_HUCRE_SUTUNU = ("level 1", "cell", "id")
_GORELI_TOL = 1e-6
_MAKS_HALKA = 64


@dataclass(frozen=True)
class OtelemeDuzeyi:
    """
    Kor duzeyinin kafes yerine gecen tanimi. Cizimde kullanilan HexLattice
    alanlarini (pitch, orientation, num_rings, center) AYNI anlamda tasir;
    merkezler dogrudan kok hucre otelemeleridir: {(halka, sira): (x, y)}.
    """
    merkezler: dict
    pitch: tuple
    orientation: str
    num_rings: int
    center: tuple = (0.0, 0.0)
    id: object = None


def _yarim_uzaylar(bolge):
    """Kesisim agacini duz yarim uzay listesine acar; baska dugum varsa None."""
    import openmc
    if isinstance(bolge, openmc.Halfspace):
        return [bolge]
    if not isinstance(bolge, openmc.Intersection):
        return None
    sonuc = []
    for dugum in bolge:
        alt = _yarim_uzaylar(dugum)
        if alt is None:
            return None
        sonuc.extend(alt)
    return sonuc


def _dogrultu_gruplari(duzlemler):
    """{aci (derece, [0,180)): [u yonunde isaretli uzaklik, ...]}."""
    gruplar = {}
    for s in duzlemler:
        a, b, c, d = float(s.a), float(s.b), float(s.c), float(s.d)
        boy = math.hypot(a, b)
        if abs(c) > _GORELI_TOL or boy == 0.0:
            return None
        aci = math.degrees(math.atan2(b, a)) % 180.0
        aci = round(aci, 6) % 180.0
        ux, uy = math.cos(math.radians(aci)), math.sin(math.radians(aci))
        isaret = 1.0 if (a * ux + b * uy) > 0 else -1.0
        gruplar.setdefault(aci, []).append(isaret * d / boy)
    return gruplar


def altigen_hucre(hucre):
    """
    Kok hucresi bir altigen demet konumuysa (cx, cy, adim, yonelim); degilse
    None. Bolge yalniz yarim uzaylardan olusmali ve 3 dogrultuda ikiser
    duzlem (z duzlemleri haric) icermelidir.
    """
    import openmc
    uzaylar = _yarim_uzaylar(hucre.region) if hucre.region is not None else None
    if not uzaylar:
        return None
    # ZPlane de openmc.Plane alt sinifidir (tur 'z-plane'): yalniz genel duzlemler
    duzlemler = [h.surface for h in uzaylar
                 if isinstance(h.surface, openmc.Plane) and h.surface.type == "plane"]
    gruplar = _dogrultu_gruplari(duzlemler)
    if not gruplar or len(gruplar) != 3 or any(len(v) != 2 for v in gruplar.values()):
        return None
    acilar = sorted(gruplar)
    izd = {a: sum(gruplar[a]) / 2.0 for a in acilar}
    adimlar = [abs(gruplar[a][0] - gruplar[a][1]) for a in acilar]
    adim = adimlar[0]
    if adim <= 0 or any(abs(p - adim) > _GORELI_TOL * adim for p in adimlar):
        return None
    a1, a2 = math.radians(acilar[0]), math.radians(acilar[1])
    det = math.cos(a1) * math.sin(a2) - math.sin(a1) * math.cos(a2)
    p1, p2 = izd[acilar[0]], izd[acilar[1]]
    cx = (p1 * math.sin(a2) - p2 * math.sin(a1)) / det
    cy = (math.cos(a1) * p2 - math.cos(a2) * p1) / det
    kalan = acilar[0] % 60.0
    if min(kalan, 60.0 - kalan) < 1e-4:
        yonelim = "x"
    elif abs(kalan - 30.0) < 1e-4:
        yonelim = "y"
    else:
        return None
    return (cx, cy, adim, yonelim)


def _kor_olcusu(konumlar):
    """Konum hucrelerinden (halka sayisi, adim, yonelim)."""
    from cekirdek import altigen_kor
    adim, yonelim = konumlar[0][2], konumlar[0][3]
    if any(abs(k[2] - adim) > _GORELI_TOL * adim or k[3] != yonelim for k in konumlar):
        raise RuntimeError(_("altıgen kor konum hücrelerinin adımı ya da yönelimi "
                             "birbirini tutmuyor; demet konumları belirlenemedi"))
    tol = _GORELI_TOL * adim * 10.0
    for n in range(1, _MAKS_HALKA + 1):
        merkezler = altigen_kor.kor_merkezleri(n, adim, yonelim)
        if all(any(math.hypot(k[0] - x, k[1] - y) < tol for x, y in merkezler)
               for k in konumlar):
            return n, adim, yonelim
    raise RuntimeError(_("altıgen kor konum hücreleri %d halkalı bir haritaya "
                         "sığmıyor; demet konumları belirlenemedi") % _MAKS_HALKA)


def _oteleme(hucre):
    t = getattr(hucre, "translation", None)
    return None if t is None else (float(t[0]), float(t[1]))


def oteleme_duzeni(df, geometri):
    """
    Distribcell yolunun kok duzeyi bir altigen_kafes demet konumuysa
    ({kok hucre kimligi: demet anahtari}, OtelemeDuzeyi); degilse None
    (kafesli kor, tek demet ya da tek konumlu altigen kor -- eski davranis).
    """
    kok = getattr(geometri, "root_universe", None)
    if kok is None or KOK_HUCRE_SUTUNU not in df.columns:
        return None
    hucreler = kok.cells
    kimlikler = sorted({int(i) for i in df[KOK_HUCRE_SUTUNU].tolist()})
    if any(i not in hucreler for i in kimlikler):
        return None
    otelemeler = {i: _oteleme(hucreler[i]) for i in kimlikler}
    if all(t is None for t in otelemeler.values()):
        return None
    konumlar = [k for k in (altigen_hucre(h) for h in hucreler.values()) if k]
    if len({(round(k[0], 6), round(k[1], 6)) for k in konumlar}) < 2:
        return None
    return _eslestir(_sifir_otelemeler(otelemeler, hucreler), konumlar)


def _sifir_otelemeler(otelemeler, hucreler):
    """
    OpenMC'de translation'siz hucre SIFIR otelemelidir; summary.h5 (0, 0, 0)
    otelemeyi YAZMAZ (olculdu: merkez demetin kok hucresi okununca None).
    Bu yuzden None -> (0, 0), ama yalnizca hucrenin kendi altigen merkezi de
    (0, 0) ise; degilse demet konumu belirlenemez -> acik hata.
    """
    sonuc = {}
    for kimlik, t in otelemeler.items():
        if t is None:
            merkez = altigen_hucre(hucreler[kimlik])
            if merkez is None or math.hypot(merkez[0], merkez[1]) > _GORELI_TOL * merkez[2] * 10:
                raise RuntimeError(_("kök hücre %d ötelemesiz ama diğer demet konumları "
                                     "ötelemeli; demet konumu belirlenemedi") % kimlik)
            t = (0.0, 0.0)
        sonuc[kimlik] = t
    return sonuc


def _eslestir(otelemeler, konumlar):
    from cekirdek import altigen, altigen_kor
    n, adim, yonelim = _kor_olcusu(konumlar)
    anahtarlar = sorted(altigen.konumlar(n, yonelim))
    merkezler = altigen_kor.kor_merkezleri(n, adim, yonelim)
    tol = _GORELI_TOL * adim * 10.0
    hucre_demet, demet_merkezi = {}, {}
    for kimlik, (tx, ty) in otelemeler.items():
        sira = next((i for i, (x, y) in enumerate(merkezler)
                     if math.hypot(tx - x, ty - y) < tol), None)
        if sira is None:
            raise RuntimeError(_("kök hücre %d ötelemesi (%.6g, %.6g) hiçbir demet "
                                 "konumuna denk gelmiyor") % (kimlik, tx, ty))
        hucre_demet[kimlik] = anahtarlar[sira]
        demet_merkezi[anahtarlar[sira]] = (tx, ty)
    return hucre_demet, OtelemeDuzeyi(merkezler=demet_merkezi, pitch=(adim,),
                                      orientation=yonelim, num_rings=n)
