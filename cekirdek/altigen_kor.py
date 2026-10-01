# -*- coding: utf-8 -*-
"""
================================================================================
 altigen_kor.py  --  Altigen tam kor (altigen_kafes) ve demet kilifi (duct)
================================================================================

 Kurucu (kurucu.py) ve betik uretici (kod_uret.py) AYNI islevleri kullanir:
 altigen_kor_hucreleri() ve kilifli_demet_universe() yalnizca math + openmc
 ile yazilmistir; betige KAYNAK KODLARI aynen kopyalanir (inspect). Boylece
 iki yol ayni geometriyi kurar -- ayni sayiyi iki yoldan hesaplayan iki kod
 er ya da gec ayrisir.

 YONELIM  (olculdu -- testler/test_altigen_kor.py, nokta-hucre testleri)
   Demet (pin kafesi yonelimi o_p) kendi altigen zarfiyla tek bir cisimdir:
   zarf = HexagonalPrism(orientation=o_p)  (kurucu._altigen_sinir notu).
   Kor kafesi 'y' ise komsu demetler yukarida/asagida -> kor HUCRESININ duz
   yuzleri YATAY, yani hucre = HexagonalPrism('x'). Genel olarak:
       kor hucresi prizmasi = ters(kor yonelimi)
   Demet hucreye ancak zarfi hucreyle ayni yonelimdeyse oturur:
       o_p == ters(o_k)   <=>   pin kafesi ile kor kafesi birbirine 90 derece
   (VVER / SFR tam korlari boyledir). Olcum: 19 pinli demet, adim = zarf,
   kor 'x' + pin 'y' -> 7 demet 1.3653 +/- 0.0006, tek demet 1.3649 +/- 0.0007;
   kor 'y' + pin 'y' (yanlis) -> 1.3813 (+1640 pcm: kose pinleri kirpilir).
   dogrula/kor.py ayni yonelimi HATA sayar.

 YAN SINIR -- KIRIK CIZGI (demetlerin dis yuzleri)
   Yansitici yoksa sinir kosulu en dis demetlerin DIS YUZLERINE konur; araya
   dolgu malzemesi girmez. Kare haritadaki RectangularPrism'in altigen
   karsiligi budur: 7 ayni demet + reflective = sonsuz demet kafesi (kesin).
   Once haritayi saran tek bir HexagonalPrism denendi: kose/vadi bosluklari
   dolgu (su) ile doldugu icin k +5300 pcm sapti (olculdu, 1.4179). Bu yuzden
   her demet konumu KENDI altigen prizmasiyla bir kok hucresidir; paylasilan
   yuzler ayni Plane nesnesidir, sinir yuzleri ayri (BC'li) nesnelerdir --
   BC'li bir duzlem baska bir hucrenin icinden gecseydi parcacik orada da
   yansirdi. periodic bu sinirda SUNULMAZ (eslesen duzlem cifti yok).

 YANSITICI HALKASI
   Kor hucrelerinin tam zarfi: apotem = (N-1) P sqrt(3)/2 + P/sqrt(3)
   (en dis hucrelerin sivri uclari), yonelim = kor yonelimi. Yansitici bu
   zarfin "kalinlik" kadar disina uzanir ve aradaki vadileri de doldurur.
================================================================================
"""

import inspect
import math

from cekirdek import altigen

SQ3 = math.sqrt(3.0)


# ============================================================================
# olculer (openmc gerektirmez)
# ============================================================================

def ters_yonelim(yonelim):
    """'x' <-> 'y'."""
    return "x" if yonelim == "y" else "y"


def halka_sayisi(d):
    """Demet ya da kor tanimindan halka sayisi."""
    return int(d.get("halka_sayisi") or (d.get("boyut") or [1])[0] or 1)


def kilif(d):
    """Demetin kilif tanimi (sozluk) ya da None. Kilif yalnizca altigen demette."""
    k = d.get("kilif") if d.get("tur") == "altigen" else None
    return k if isinstance(k, dict) and k else None


def pin_zarfi(d):
    """Kilifsiz demetin duz yuzden duz yuze olcusu: (halka-1) adim sqrt3 + adim."""
    adim = float(d.get("adim") or 0.0)
    return (halka_sayisi(d) - 1) * adim * SQ3 + adim


def demet_dis_olcu(d):
    """Demetin duz yuzden duz yuze dis olcusu (kilif dahil)."""
    k = kilif(d)
    if k:
        return float(k.get("ic_duz") or 0.0) + 2.0 * float(k.get("kalinlik") or 0.0)
    return pin_zarfi(d)


def kor_merkezleri(halka, adim, yonelim):
    """Demet merkezleri [(x, y)], harita sirasiyla (distan ice, her halka tepeden)."""
    kon = altigen.konumlar(halka, yonelim)
    return [(x * adim, y * adim) for _k, (x, y) in sorted(kon.items())]


def yuz_normali_acilari(kor_yonelim):
    """Kor hucresinin 6 yuz normali (derece) = komsu demet yonleri."""
    taban = 0.0 if kor_yonelim == "x" else 30.0
    return [taban + 60.0 * k for k in range(6)]


def zarf_apotemi(halka, adim):
    """Kor hucrelerinin tam altigen zarfinin apotemi (yonelim = kor yonelimi)."""
    return (halka - 1) * adim * SQ3 / 2.0 + adim / SQ3


def prizma_kutusu(apotem, prizma_yonelimi):
    """HexagonalPrism'in (genislik, yukseklik). 'y': dusey duz yuzler."""
    uzun = 2.0 * apotem * 2.0 / SQ3
    return (2.0 * apotem, uzun) if prizma_yonelimi == "y" else (uzun, 2.0 * apotem)


def kor_hucre_kutusu(halka, adim, kor_yonelim):
    """Kor hucrelerinin (yansitici haric) tam sinir kutusu (genislik, yukseklik)."""
    r = adim / SQ3
    koseler = [math.radians(a + 30.0) for a in yuz_normali_acilari(kor_yonelim)]
    xs, ys = [], []
    for cx, cy in kor_merkezleri(halka, adim, kor_yonelim):
        xs += [cx + r * math.cos(a) for a in koseler]
        ys += [cy + r * math.sin(a) for a in koseler]
    return (max(xs) - min(xs), max(ys) - min(ys))


def yansitici_kalinligi(kor):
    """Kurulan yansitici halkasinin kalinligi; yoksa None."""
    y = kor.get("yansitici") or {}
    return float(y.get("kalinlik") or 0.0) if y.get("var") else None


def kor_sinir_kutusu(kor):
    """Modelin sinir kutusu (yansitici dahil)."""
    n, P, yon = halka_sayisi(kor), float(kor["adim"]), kor.get("yonelim") or "x"
    kal = yansitici_kalinligi(kor)
    if kal is None:
        return kor_hucre_kutusu(n, P, yon)
    return prizma_kutusu(zarf_apotemi(n, P) + kal, yon)


def kor_ic_olcusu(kor):
    """Yansitici HARIC olcu (kaynak kutusu): kor hucrelerinin zarfi."""
    return kor_hucre_kutusu(halka_sayisi(kor), float(kor["adim"]), kor.get("yonelim") or "x")


# ============================================================================
# openmc kurucular -- BETIGE AYNEN KOPYALANIR (yalniz math + openmc)
# ============================================================================

def kilifli_demet_universe(kafes, ic_duz, kalinlik, yonelim, kilif_malzeme, dis_malzeme):
    """
    Altigen demet + kilif (duct): kilifin ici pin kafesi, kilif, disi dolgu.
    Kilif prizmasi pin kafesiyle AYNI yonelimdedir (zarf gibi; olculdu).
    """
    import math
    import openmc
    ic = openmc.model.HexagonalPrism(edge_length=ic_duz / math.sqrt(3.0),
                                     orientation=yonelim)
    dis = openmc.model.HexagonalPrism(edge_length=(ic_duz + 2.0 * kalinlik) / math.sqrt(3.0),
                                      orientation=yonelim)
    return openmc.Universe(cells=[
        openmc.Cell(fill=kafes, region=-ic, name="kilif ici"),
        openmc.Cell(fill=kilif_malzeme, region=+ic & -dis, name="kilif"),
        openmc.Cell(fill=dis_malzeme, region=+dis, name="demetler arasi"),
    ])


def altigen_kor_hucreleri(merkezler, adim, yonelim, dolgular, katmanlar, yan_bc,
                          yansitici=None):
    """
    Altigen tam korun kok hucreleri.

    merkezler : [(x, y)] demet merkezleri (tam altigen harita)
    yonelim   : kor kafesi yonelimi ('x' | 'y'; HexLattice anlaminda)
    dolgular  : konum basina, katman basina dolgu: dolgular[i][j]
    katmanlar : [(z_bolgesi | None, ad)] -- eksenel dilimler (alttan uste)
    yan_bc    : yan sinir kosulu
    yansitici : None | (malzeme, kalinlik, tam_z_bolgesi | None)
    Yansitici yoksa sinir kosulu en dis demetlerin DIS YUZLERINDEDIR.
    """
    import math
    import openmc
    sq3 = math.sqrt(3.0)
    taban = 0.0 if yonelim == "x" else 30.0
    nor = [(math.cos(math.radians(taban + 60.0 * k)),
            math.sin(math.radians(taban + 60.0 * k))) for k in range(6)]

    def anahtar(x, y):
        return (round(x / adim, 6) + 0.0, round(y / adim, 6) + 0.0)

    kume = {anahtar(x, y) for x, y in merkezler}
    duzlemler = {}

    def duzlem(kk, m, bc):
        a = (kk, m, bc)
        if a not in duzlemler:
            duzlemler[a] = openmc.Plane(a=nor[kk][0], b=nor[kk][1], c=0.0,
                                        d=m * adim / 2.0, boundary_type=bc)
        return duzlemler[a]

    bolgeler, dis_halka = [], []
    for x, y in merkezler:
        bolge, sinirda = None, False
        for k in range(6):
            nx, ny = nor[k]
            komsu = anahtar(x + adim * nx, y + adim * ny) in kume
            sinirda = sinirda or not komsu
            bc = "transmission" if (komsu or yansitici is not None) else yan_bc
            isaret = 1.0 if k < 3 else -1.0
            m = int(round(2.0 * isaret * (nx * x + ny * y + adim / 2.0) / adim))
            p = duzlem(k % 3, m, bc)
            yari = -p if isaret > 0 else +p
            bolge = yari if bolge is None else bolge & yari
        bolgeler.append(bolge)
        if sinirda:
            dis_halka.append(bolge)

    hucreler = []
    for i, (x, y) in enumerate(merkezler):
        for j, (z_bolge, ad) in enumerate(katmanlar):
            dolgu = dolgular[i][j]
            h = openmc.Cell(fill=dolgu, name=ad or "",
                            region=bolgeler[i] if z_bolge is None else bolgeler[i] & z_bolge)
            if isinstance(dolgu, (openmc.Universe, openmc.Lattice)):
                h.translation = (x, y, 0.0)
            hucreler.append(h)

    if yansitici is not None:
        malzeme, kalinlik, tam_z = yansitici
        halka = int(round(max(math.hypot(x, y) for x, y in merkezler) / adim)) + 1
        apotem = (halka - 1) * adim * sq3 / 2.0 + adim / sq3 + kalinlik
        dis = openmc.model.HexagonalPrism(edge_length=2.0 * apotem / sq3,
                                          orientation=yonelim, boundary_type=yan_bc)
        bolge = -dis
        if halka > 1:
            orta = openmc.model.HexagonalPrism(
                edge_length=2.0 * ((halka - 1) * adim * sq3 / 2.0) / sq3, orientation=yonelim)
            bolge = bolge & +orta
        for b in dis_halka:
            bolge = bolge & ~b
        if tam_z is not None:
            bolge = bolge & tam_z
        hucreler.append(openmc.Cell(fill=malzeme, region=bolge, name="yansıtıcı"))
    return hucreler


# ============================================================================
# spec -> kok hucreleri (kurucu.kor_kur'un altigen_kafes dali)
# ============================================================================

def z_dilimleri(kor):
    """
    Eksenel dilimler [(z_bolgesi | None, katman | None)] ve tam yukseklik
    bolgesi. Ic arayuzler transmission; BC yalnizca en alt ve en ust yuzeyde
    (kurucu._eksenel_hucreler ile ayni kural).
    """
    import openmc
    from cekirdek.sema import eksenel_katmanlar, kor_yuksekligi
    h = kor_yuksekligi(kor)
    if not h:
        return [(None, None)], None
    sinir = kor.get("sinir", {})
    katmanlar = eksenel_katmanlar(kor)
    sinirlar = ([-h / 2.0] + [z1 for _z0, z1, _b in katmanlar[:-1]] + [h / 2.0]
                if katmanlar else [-h / 2.0, h / 2.0])
    duz = [openmc.ZPlane(sinirlar[0], boundary_type=sinir.get("alt", "reflective"))]
    duz += [openmc.ZPlane(z) for z in sinirlar[1:-1]]
    duz.append(openmc.ZPlane(sinirlar[-1], boundary_type=sinir.get("ust", "reflective")))
    dilimler = [(+duz[i] & -duz[i + 1], (katmanlar[i][2] if katmanlar else None))
                for i in range(len(duz) - 1)]
    return dilimler, +duz[0] & -duz[-1]


def katman_adlari(dilimler):
    """z_dilimleri -> [(z_bolgesi, hucre adi)]."""
    return [(z, ((k or {}).get("ad") or "katman %d" % (i + 1)) if k else "")
            for i, (z, k) in enumerate(dilimler)]


def konum_dolgu_adlari(kor, dilimler):
    """
    Konum basina, dilim basina dolgu: ("ad", ad) ana/katmana ozel anahtarla
    cozulen harf; ("katman", katman) katmanin kendi dolgusu.
    """
    esleme = kor.get("anahtar") or {}
    sonuc = []
    for harf in (h for satir in kor.get("harita") or [] for h in satir):
        satir = []
        for _z, k in dilimler:
            if k and k.get("anahtar"):
                e = dict(esleme)
                e.update(k["anahtar"])
                satir.append(("ad", e.get(harf)))
            elif k and k.get("dolgu"):
                satir.append(("katman", k))
            else:
                satir.append(("ad", esleme.get(harf)))
        sonuc.append(satir)
    return sonuc


def harita_kontrol(kor):
    """Halka uzunluklari tutmuyorsa ValueError."""
    n = halka_sayisi(kor)
    beklenen = altigen.halka_uzunluklari(n)
    bulunan = [len(s) for s in kor.get("harita") or []]
    if bulunan != beklenen:
        raise ValueError("altıgen kor haritası %d halka bekliyor (öğe sayıları %s), "
                         "haritada %s" % (n, beklenen, bulunan))


def betik_kaynagi():
    """Betige kopyalanan islevlerin kaynak kodu."""
    return "\n\n".join(inspect.getsource(f) for f in
                       (kilifli_demet_universe, altigen_kor_hucreleri))


def kilif_kullaniliyor(spec):
    """Spec'te kilifli altigen demet var mi (betige yardimci islev gerekir)."""
    return any(kilif(d) for d in spec.get("demetler") or [])


def betik_satirlari(spec, satirlar, bagimlilik, mat_ifade, f):
    """
    altigen_kafes korunun betik satirlari (kurucu ile AYNI islevler).
    bagimlilik(ad) -> betikteki universe degiskeni; mat_ifade(ad) -> malzeme
    ifadesi; f(sayi) -> tam duyarlikli yazim. DONER (gx, gy).
    """
    from cekirdek.sema import eksenel_katmanlar, kor_yuksekligi
    kor = spec["kor"]
    harita_kontrol(kor)
    n, P = halka_sayisi(kor), float(kor["adim"])
    yon = kor.get("yonelim") or "x"
    sinir = kor.get("sinir") or {}
    h = kor_yuksekligi(kor)
    katmanlar = eksenel_katmanlar(kor)
    satirlar += ["", "# --- altıgen tam kor (%d halka, %d demet), demet adımı %s cm ---"
                 % (n, len(kor_merkezleri(n, P, yon)), f(P)),
                 "# Kor kafesi '%s', demet pin kafesi '%s' (birbirine 90°, ölçüldü)."
                 % (yon, ters_yonelim(yon)),
                 "# Yan sınır en dış demetlerin DIŞ YÜZLERİNDEDİR (kırık çizgi)."]
    if h:
        sinirlar = ([-h / 2.0] + [z1 for _a, z1, _b in katmanlar[:-1]] + [h / 2.0]
                    if katmanlar else [-h / 2.0, h / 2.0])
        satirlar.append("_z = [openmc.ZPlane(%s, boundary_type=%r)," % (
            f(sinirlar[0]), sinir.get("alt", "reflective")))
        for z in sinirlar[1:-1]:
            satirlar.append("      openmc.ZPlane(%s)," % f(z))
        satirlar.append("      openmc.ZPlane(%s, boundary_type=%r)]" % (
            f(sinirlar[-1]), sinir.get("ust", "reflective")))
        satirlar.append("_dilimler = [+_z[_i] & -_z[_i + 1] for _i in range(len(_z) - 1)]")
        satirlar.append("_tam_z = +_z[0] & -_z[-1]")
    else:
        satirlar += ["_dilimler = [None]", "_tam_z = None"]
    dilimler = [(None, b) for _a, _c, b in katmanlar] if katmanlar else [(None, None)]
    adlar = [a for _z, a in katman_adlari(dilimler)]
    satirlar.append("_katmanlar = list(zip(_dilimler, %r))" % (adlar,))
    satirlar.append("_merkezler = [")
    for x, y in kor_merkezleri(n, P, yon):
        satirlar.append("    (%s, %s)," % (f(x), f(y)))
    satirlar.append("]")
    # once bagimliliklar (universe'ler) uretilir, sonra liste yazilir
    dolgu_satirlari = [", ".join(bagimlilik(deger if tur == "ad" else deger.get("dolgu"))
                                 for tur, deger in satir)
                       for satir in konum_dolgu_adlari(kor, dilimler)]
    satirlar.append("_dolgular = [")
    satirlar.extend("    [%s]," % d for d in dolgu_satirlari)
    satirlar.append("]")
    kal = yansitici_kalinligi(kor)
    satirlar.append("_yansitici = %s" % ("None" if kal is None else "(%s, %s, _tam_z)" % (
        mat_ifade((kor.get("yansitici") or {}).get("malzeme")), f(kal))))
    satirlar.append("kok = openmc.Universe(cells=altigen_kor_hucreleri(")
    satirlar.append("    _merkezler, %s, %r, _dolgular, _katmanlar, %r, _yansitici))"
                    % (f(P), yon, sinir.get("yan", "reflective")))
    satirlar += ["", "geometri = openmc.Geometry(kok)"]
    return kor_sinir_kutusu(kor)
