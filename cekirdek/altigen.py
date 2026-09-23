# -*- coding: utf-8 -*-
"""
================================================================================
 altigen.py  --  HexLattice halka duzeni ve konum hesabi
================================================================================

 OpenMC'nin HexLattice.universes yapisi:
   - Halkalar DISTAN ICE dogru siralanir (ilk alt liste en dis halka).
   - Her halka icindeki ogeler "tepe"den baslar ve SAAT YONUNDE ilerler.
   - Yaricapi k olan halkada 6k oge vardir; merkez halkada 1 oge.

 Bu modul (halka_indeksi, oge_indeksi) ciftlerini kartezyen konuma cevirir.
 Konumlar ADIM (pitch) biriminde doner; cizim ve dogrulama ayni kaynagi kullanir.

 DOGRULAMA
   Duzen openmc.HexLattice.show_indices() ciktisi ile karsilastirilarak
   dogrulanmistir (bkz. testler/test_regresyon.py -> test_altigen_duzen).

 YONELIM
   'y' (varsayilan) : hucrelerin ust ve alt yuzleri yatay; komsular yukarida
                      ve asagida. Halkanin ilk ogesi TEPEDE.
   'x'              : hucrelerin sag ve sol yuzleri dusey; komsular sagda ve
                      solda. Halkanin ilk ogesi SAGDA.
================================================================================
"""

import math

# Halka yaricapi k olan halkadaki oge sayisi
def halka_uzunlugu(yaricap):
    """Yaricapi k olan halkadaki oge sayisi (merkez icin 1)."""
    return 6 * yaricap if yaricap > 0 else 1


def halka_uzunluklari(halka_sayisi):
    """Distan ice dogru her halkanin oge sayisi."""
    return [halka_uzunlugu(halka_sayisi - 1 - r) for r in range(halka_sayisi)]


def toplam_hucre(halka_sayisi):
    """Toplam kafes hucresi sayisi."""
    return sum(halka_uzunluklari(halka_sayisi))


def konumlar(halka_sayisi, yonelim="y"):
    """
    {(halka_indeksi, oge_indeksi): (x, y)} dondurur. Birim = adim (pitch).

    Halka yaricapi k icin kose noktalari k yaricapinda bir cember uzerinde
    60 derece araliklarla durur; yuruyus tepeden (ya da 'x' yoneliminde sagdan)
    baslar ve saat yonunde her kenari k esit adimda kat eder.
    """
    sonuc = {}
    baslangic = math.pi / 2.0 if yonelim == "y" else 0.0
    for r in range(halka_sayisi):
        k = halka_sayisi - 1 - r            # bu halkanin yaricapi
        if k == 0:
            sonuc[(r, 0)] = (0.0, 0.0)
            continue
        koseler = [(k * math.cos(baslangic - i * math.pi / 3.0),
                    k * math.sin(baslangic - i * math.pi / 3.0))
                   for i in range(6)]
        i = 0
        for v in range(6):
            x0, y0 = koseler[v]
            x1, y1 = koseler[(v + 1) % 6]
            for adim in range(k):
                t = adim / float(k)
                sonuc[(r, i)] = (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)
                i += 1
    return sonuc


def hucre_kose_acilari(yonelim="y"):
    """
    Tek bir altigen hucrenin kose acilari (derece).
    'y' yoneliminde ust/alt yuzler yatay -> koseler 0, 60, ... derecede.
    'x' yoneliminde sag/sol yuzler dusey  -> koseler 30, 90, ... derecede.
    """
    baslangic = 0.0 if yonelim == "y" else 30.0
    return [baslangic + 60.0 * i for i in range(6)]


def cevre_yaricap(adim):
    """Adimi verilen altigen hucrenin cevrel cember yaricapi."""
    return adim / math.sqrt(3.0)


def kapsayan_olcu(halka_sayisi, adim, yonelim="y"):
    """
    Kafesin kapsadigi yaklasik (genislik, yukseklik).
    Onizleme penceresini olceklemek ve sinir kutusu kurmak icin kullanilir.
    """
    if halka_sayisi <= 0:
        return (adim, adim)
    kon = konumlar(halka_sayisi, yonelim)
    r = cevre_yaricap(adim)
    xs = [x * adim for x, _ in kon.values()]
    ys = [y * adim for _, y in kon.values()]
    return (max(xs) - min(xs) + 2 * r, max(ys) - min(ys) + 2 * r)


def bos_harita(halka_sayisi, harf="y"):
    """Tum hucreleri ayni harfle dolu bir harita uretir (distan ice)."""
    return ["".join(harf for _ in range(u)) for u in halka_uzunluklari(halka_sayisi)]


def harita_yeniden_boyutlandir(eski_harita, yeni_halka_sayisi, varsayilan="y"):
    """
    Halka sayisi degistiginde haritayi korumaya calisir.
    Halkalar ICTEN hizalanir -- merkez sabit kalir, disa halka eklenir/cikarilir.
    """
    eski = list(eski_harita or [])
    yeni_uzunluklar = halka_uzunluklari(yeni_halka_sayisi)
    n_yeni = len(yeni_uzunluklar)
    yeni = []
    for i in range(n_yeni):
        # icten hizalama: yeni listenin sondan i. halkasi, eskinin sondan i.'si
        ters = n_yeni - 1 - i
        eski_ters_ix = len(eski) - 1 - ters
        hedef = yeni_uzunluklar[i]
        if 0 <= eski_ters_ix < len(eski):
            kaynak = eski[eski_ters_ix]
            satir = (kaynak * (hedef // max(len(kaynak), 1) + 1))[:hedef] \
                if len(kaynak) != hedef else kaynak
        else:
            satir = varsayilan * hedef
        yeni.append(satir)
    return yeni
