# -*- coding: utf-8 -*-
"""
================================================================================
 tambur.py  --  Donen kontrol tamburu geometrisi
================================================================================

 Kontrol tamburu, yansiticinin icine gomulmus donen bir silindirdir. Cevresinin
 bir yayi emicidir (genellikle B4C); tambur dondukce emici kora yaklasir ya da
 uzaklasir. Kompakt/uzay reaktorlerinde (Kilopower, KRUSTY ve PETEK gibi
 tasarimlarda) kontrol cubugu yerine bu kullanilir.

 KONVANSIYON (olcumle dogrulandi)
   donme = 0   ->  emici KORE bakiyor  = DALDIRILMIS (en dusuk k)
   donme = 180 ->  emici DISA bakiyor  = CEKILMIS   (en yuksek k)

   Olculen (8 tambur, 120 derece yay, Be yansitici):
     donme   0 -> k = 0.8858
     donme  90 -> k = 0.9095
     donme 180 -> k = 0.9371          toplam deger ~6200 pcm

 DONME MATEMATIGI
   openmc.Cell.rotation = (0, 0, psi) emici yayi DOGRUDAN psi acisina koyar
   (nokta sorgusuyla olculdu: psi=45 -> yay merkezi 44.5 derece). Ters cevirme
   ya da kaydirma YOKTUR.
   Azimutu fi olan bir tamburda emicinin kora bakmasi icin yayin (fi+180)
   yonunde olmasi gerekir:
       psi = fi + 180 + donme
================================================================================
"""

import math

import openmc


def _duzlem(aci_derece):
    """z ekseninden gecen, verilen aciya ait yari-duzlem siniri."""
    a = math.radians(aci_derece)
    return openmc.Plane(a=-math.sin(a), b=math.cos(a), c=0.0, d=0.0)


def _kama(aci_genislik):
    """
    LOKAL +x yonunde ortalanmis, verilen genislikte aci kamasi.
    180 dereceden genis yaylarda kesisim yerine BIRLESIM gerekir.
    """
    yari = aci_genislik / 2.0
    p1, p2 = _duzlem(-yari), _duzlem(+yari)
    if aci_genislik <= 180.0:
        return +p1 & -p2
    return +p1 | -p2


def universe(tambur, nesneler, _mat):
    """
    Tambur universe'i: emici yay LOKAL +x yonunde ortalanmistir.
    Yerlestirme sirasinda cell.rotation ile dondurulur.
    """
    R = float(tambur["yaricap"])
    r_ic = float(tambur.get("emici_ic_yaricap") or 0.0)
    aci = float(tambur.get("emici_aci") or 120.0)

    dis = openmc.ZCylinder(r=R)
    govde = _mat(nesneler, tambur.get("govde_malzeme"))
    emici_mal = _mat(nesneler, tambur.get("emici_malzeme"))

    if r_ic > 0:
        ic = openmc.ZCylinder(r=r_ic)
        emici_bolge = +ic & -dis & _kama(aci)
    else:
        emici_bolge = -dis & _kama(aci)

    return openmc.Universe(cells=[
        openmc.Cell(fill=emici_mal, region=emici_bolge),
        openmc.Cell(fill=govde, region=(-dis) & ~emici_bolge),
        # tamburun disi: yerlestirildigi hucre zaten -delik ile sinirlidir,
        # ama universe'un her yeri tanimli olmalidir
        openmc.Cell(fill=govde, region=+dis),
    ])


def yerlesim(tambur):
    """
    Tamburlarin (x, y, psi) yerlesimini dondurur.

    psi = fi + 180 + donme   ->  donme=0'da emici kore bakar.
    """
    n = int(tambur.get("sayi") or 0)
    R_m = float(tambur.get("merkez_yaricap") or 0.0)
    donme = float(tambur.get("donme") or 0.0)
    baslangic = float(tambur.get("baslangic_acisi") or 0.0)
    liste = []
    for i in range(n):
        fi = baslangic + 360.0 * i / n
        liste.append((R_m * math.cos(math.radians(fi)),
                      R_m * math.sin(math.radians(fi)),
                      fi + 180.0 + donme))
    return liste


def geometri_kontrol(tambur, kor_yaricap, yansitici_kalinlik):
    """
    Tamburlarin yansiticiya SIGIP sigmadigini ve birbiriyle CAKISIP
    cakismadigini kontrol eder.

    DONER hata mesajlari listesi (bos ise sorun yok).
    """
    hatalar = []
    n = int(tambur.get("sayi") or 0)
    R = float(tambur.get("yaricap") or 0.0)
    R_m = float(tambur.get("merkez_yaricap") or 0.0)
    r_ic = float(tambur.get("emici_ic_yaricap") or 0.0)
    aci = float(tambur.get("emici_aci") or 0.0)

    if n < 1:
        hatalar.append("tambur sayisi en az 1 olmali")
    if R <= 0:
        hatalar.append("tambur yaricapi pozitif olmali")
    if not (0.0 < aci <= 360.0):
        hatalar.append("emici yay acisi 0-360 derece arasinda olmali")
    if r_ic >= R:
        hatalar.append("emici ic yaricapi (%.4f) tambur yaricapindan (%.4f) "
                       "kucuk olmali" % (r_ic, R))

    # radyal sigma: tambur tamamen yansitici kusaginin icinde kalmali
    dis_sinir = kor_yaricap + yansitici_kalinlik
    if R_m - R < kor_yaricap:
        hatalar.append(
            "tamburlar kora giriyor: merkez yaricapi %.4f - tambur yaricapi "
            "%.4f = %.4f < kor yaricapi %.4f"
            % (R_m, R, R_m - R, kor_yaricap))
    if R_m + R > dis_sinir:
        hatalar.append(
            "tamburlar yansiticidan tasiyor: %.4f + %.4f = %.4f > dis sinir %.4f"
            % (R_m, R, R_m + R, dis_sinir))

    # komsu tamburlar cakisiyor mu (kiris mesafesi)
    if n >= 2 and R_m > 0:
        kiris = 2.0 * R_m * math.sin(math.pi / n)
        if kiris <= 2.0 * R:
            hatalar.append(
                "komsu tamburlar cakisiyor: merkezler arasi %.4f cm, iki yaricap "
                "toplami %.4f cm. Tambur sayisini azaltin, yaricapi kucultun ya "
                "da merkez yaricapini buyutun." % (kiris, 2.0 * R))
    return hatalar


def ozet(tambur):
    """Arayuz icin tek satirlik ozet."""
    n = int(tambur.get("sayi") or 0)
    return ("%d tambur, yaricap %.3f cm, merkez %.3f cm, yay %.0f derece, "
            "donme %.1f derece"
            % (n, tambur.get("yaricap") or 0, tambur.get("merkez_yaricap") or 0,
               tambur.get("emici_aci") or 0, tambur.get("donme") or 0))
