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

   Olculen (ornekler/tamburlu_kor.json: 8 tambur, 120 derece yay, Be yansitici;
   docs/ORNEKLER.md G-4 tablosu, ornegin kendi ayari):
     donme   0 -> k = 0.96346 ± 0.00092
     donme 180 -> k = 1.00719 ± 0.00110
     toplam tambur degeri Δk = 4372 pcm (Δk × 10⁵), Δρ = 4506 pcm
     (Δρ = (k₂ − k₁)/(k₁k₂) × 10⁵). Eski "~6200 pcm" daha once kullanilan bir
     modelin (k 0.8858 → 0.9371) Δρ'suydu (Δk = 5130 pcm); gecersizdir.

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

from cekirdek.ceviri import _


def _duzlem(aci_derece):
    """z ekseninden gecen, verilen aciya ait yari-duzlem siniri."""
    import openmc       # tembel: geometri_kontrol/ozet openmc'siz (H1b)
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
    import openmc
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
        hatalar.append(_("tambur sayısı en az 1 olmalı"))
    if R <= 0:
        hatalar.append(_("tambur yarıçapı sıfırdan büyük olmalı"))
    if not (0.0 < aci <= 360.0):
        hatalar.append(_("emici yay açısı 0–360° arasında olmalı"))
    if r_ic >= R:
        hatalar.append(_("emici iç yarıçapı (%.4f cm) tambur yarıçapından (%.4f cm) "
                       "küçük olmalı") % (r_ic, R))

    # radyal sigma: tambur tamamen yansitici kusaginin icinde kalmali
    dis_sinir = kor_yaricap + yansitici_kalinlik
    if R_m - R < kor_yaricap:
        hatalar.append(
            _("tamburlar kora giriyor: merkez yarıçapı %.4f − tambur yarıçapı "
            "%.4f = %.4f cm < kor yarıçapı %.4f cm")
            % (R_m, R, R_m - R, kor_yaricap))
    if R_m + R > dis_sinir:
        hatalar.append(
            _("tamburlar yansıtıcı kuşaktan taşıyor: %.4f + %.4f = %.4f cm > dış sınır %.4f cm")
            % (R_m, R, R_m + R, dis_sinir))

    # komsu tamburlar cakisiyor mu (kiris mesafesi)
    if n >= 2 and R_m > 0:
        kiris = 2.0 * R_m * math.sin(math.pi / n)
        if kiris <= 2.0 * R:
            hatalar.append(
                _("komşu tamburlar çakışıyor: merkezler arası %.4f cm, iki yarıçap "
                "toplamı %.4f cm. Tambur sayısını azaltın, yarıçapı küçültün ya "
                "da merkez yarıçapını büyütün.") % (kiris, 2.0 * R))
    return hatalar


def ozet(tambur):
    """Arayuz icin tek satirlik ozet."""
    n = int(tambur.get("sayi") or 0)
    return (_("%d tambur, yarıçap %.3f cm, merkez %.3f cm, yay %.0f°, "
            "dönme %.1f°")
            % (n, tambur.get("yaricap") or 0, tambur.get("merkez_yaricap") or 0,
               tambur.get("emici_aci") or 0, tambur.get("donme") or 0))
