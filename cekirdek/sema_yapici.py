# -*- coding: utf-8 -*-
"""
================================================================================
 sema_yapici.py  --  Spec yapici yardimcilari (malzeme, cubuk, demet, tally ...)
================================================================================

 cekirdek/sema.py'den bolundu (Dalga G-1; sema.py 800 satir tavanini
 asiyordu, davranis degismedi). Arayuz, ornekler ve testler bunlari
 `sema.malzeme(...)`, `sema.cubuk(...)` olarak kullanir; sema yeniden disa verir.
================================================================================
"""

# ----------------------------------------------------------------------------
# Yapici yardimcilar -- arayuz ve ornek dosyalar bunlari kullanir
# ----------------------------------------------------------------------------

def malzeme(ad, bilesim, yogunluk, birim="g/cm3", sicaklik=293.6,
            sab=None, renk=None, gorunen_ad=None):
    """
    Malzeme tanimi uretir.

    bilesim : [{"tur":"element"|"nuklid", "isim":str, "miktar":float,
                "birim":"ao"|"wo", "zenginlik":float|None}, ...]
    """
    return {
        "ad": ad,
        "gorunen_ad": gorunen_ad or ad,
        "yogunluk": {"birim": birim, "deger": yogunluk},
        "sicaklik": sicaklik,
        "bilesim": bilesim,
        "sab": list(sab or []),
        "renk": list(renk) if renk else None,
    }


def bilesen(isim, miktar, tur="element", birim="ao", zenginlik=None):
    """Tek bir bilesim satiri uretir."""
    d = {"tur": tur, "isim": isim, "miktar": miktar, "birim": birim}
    if zenginlik is not None:
        d["zenginlik"] = zenginlik
    return d


def cubuk(ad, bolgeler):
    """
    Es merkezli silindirik cubuk.

    bolgeler : [{"r": float|None, "malzeme": str}, ...]
               artan yaricap sirasinda; SON elemanin "r" degeri None olmali.
    """
    return {"ad": ad, "tur": "silindirik", "bolgeler": bolgeler}


def bolge(r, malzeme_adi):
    """Cubuk icin tek bir radyal bolge."""
    return {"r": r, "malzeme": malzeme_adi}


def kontrol_cubugu(ad, bolgeler, izleyici_malzeme, daldirma=0.0, emici_bolge=0):
    """
    Eksenel hareket eden kontrol cubugu.

    bolgeler          : normal cubuk gibi radyal bolgeler. emici_bolge ile
                        belirtilen bolgenin malzemesi EMICIDIR.
    izleyici_malzeme  : emici bolgenin cubuk UCUNUN ALTINDA kalan kismini
                        dolduran malzeme (izleyici / follower; cogu zaman
                        sogutucu ya da celik).
    daldirma          : %0 = tamamen cekilmis (emici kor icinde yok)
                        %100 = tamamen dalmis (emici tum yuksekligi kaplar)
                        Cubuk YUKARIDAN daldirilir; uc konumu
                        z_uc = +H/2 - (daldirma/100)*H
    emici_bolge       : hangi radyal bolgenin eksenel olarak bolunecegi

    !!! 3B MODEL GEREKTIRIR !!!  Kor yuksekligi tanimli degilse eksenel bir
    konum tanimlanamaz; dogrula.py bunu hata olarak bildirir.
    """
    return {
        "ad": ad, "tur": "kontrol", "bolgeler": list(bolgeler),
        "emici_bolge": int(emici_bolge),
        "izleyici_malzeme": izleyici_malzeme,
        "daldirma": float(daldirma),
    }


def plaka(ad, plaka_sayisi, et_kalinlik, zarf_kalinlik, kanal_kalinlik,
          plaka_genislik, et_malzeme, zarf_malzeme, sogutucu,
          yan_levha_kalinlik=0.0, yan_levha_malzeme=None):
    """
    MTR tipi duz plaka yakit elemani.

    Kesit (x yonu), bir plaka icin:
        [zarf | et (yakit) | zarf]  ardindan  [kanal (sogutucu)]
    Bu desen plaka_sayisi kadar tekrarlanir; sonda bir kanal daha olur.
    plaka_genislik y yonundeki aktif genisliktir.
    """
    return {
        "ad": ad,
        "tur": "plaka",
        "plaka_sayisi": plaka_sayisi,
        "et_kalinlik": et_kalinlik,
        "zarf_kalinlik": zarf_kalinlik,
        "kanal_kalinlik": kanal_kalinlik,
        "plaka_genislik": plaka_genislik,
        "et_malzeme": et_malzeme,
        "zarf_malzeme": zarf_malzeme,
        "sogutucu": sogutucu,
        "yan_levha_kalinlik": yan_levha_kalinlik,
        "yan_levha_malzeme": yan_levha_malzeme,
    }


def demet(ad, adim, boyut, harita, anahtar, dolgu_disi, tur="kare"):
    """
    Kafes (lattice) tanimi.

    tur     : "kare" (RectLattice) | "altigen" (HexLattice)
    boyut   : [nx, ny] -- kare icin
    harita  : satir listesi; her satir harflerden olusan bir dize
    anahtar : {"y": "yakit_cubugu", "k": "kilavuz_boru", ...}
    """
    return {
        "ad": ad, "tur": tur, "adim": adim, "boyut": list(boyut),
        "harita": list(harita), "anahtar": dict(anahtar),
        "dolgu_disi": dolgu_disi,
    }


def demet_altigen(ad, adim, halka_sayisi, harita, anahtar, dolgu_disi,
                  yonelim="y", kilif=None):
    """
    Altigen kafes (HexLattice) tanimi.

    halka_sayisi : merkez dahil halka sayisi (1 = tek hucre)
    harita       : halka basina bir dize, DISTAN ICE dogru.
                   Yaricapi k olan halkada 6k karakter, merkezde 1 karakter.
                   Her halkanin karakterleri TEPEDEN baslar, SAAT YONUNDE ilerler.
    yonelim      : "y" (ust/alt yuzler yatay) | "x" (sag/sol yuzler dusey)
    kilif        : istege bagli kilif (duct), bkz. demet_kilifi(). Yoksa alan
                   yazilmaz (eski dosyalar aynen kalir).
    """
    d = {
        "ad": ad, "tur": "altigen", "adim": adim,
        "halka_sayisi": halka_sayisi, "yonelim": yonelim,
        "boyut": [halka_sayisi, halka_sayisi],   # geriye uyumluluk icin
        "harita": list(harita), "anahtar": dict(anahtar),
        "dolgu_disi": dolgu_disi,
    }
    if kilif:
        d["kilif"] = dict(kilif)
    return d


def demet_kilifi(ic_duz, kalinlik, malzeme):
    """
    Altigen demet kilifi (duct; SFR, VVER-440). ic_duz: kilifin IC duz yuzden
    duz yuze olcusu [cm]; kalinlik: duvar kalinligi. Kilifin disi ile demet
    hucresinin siniri arasi demetin dolgu_disi malzemesiyle dolar (demetler
    arasi bosluk). Kilif yoksa pin kafesi kor hucresinde kirpilir.
    """
    return {"ic_duz": float(ic_duz), "kalinlik": float(kalinlik), "malzeme": malzeme}


def eksenel_bolge(ad, yukseklik, dolgu=None, anahtar=None):
    """Eksenel katman tanimi uretir (alttan uste sirayla verilir)."""
    b = {"ad": ad, "yukseklik": float(yukseklik), "dolgu": dolgu}
    if anahtar:
        b["anahtar"] = dict(anahtar)
    return b


def kabuk(r, malzeme_adi):
    """Kuresel duzenek icin tek bir kuresel kabuk (r = dis yaricap)."""
    return {"r": r, "malzeme": malzeme_adi}


def tambur(sayi, yaricap, merkez_yaricap, govde_malzeme, emici_malzeme,
           emici_ic_yaricap=0.0, emici_aci=120.0, donme=0.0, baslangic_acisi=0.0):
    """
    Donen kontrol tamburu takimi.

    donme = 0   -> emici KORE bakiyor (daldirilmis, en dusuk k)
    donme = 180 -> emici DISA bakiyor (cekilmis, en yuksek k)
    """
    return {
        "sayi": int(sayi), "yaricap": yaricap, "merkez_yaricap": merkez_yaricap,
        "govde_malzeme": govde_malzeme, "emici_malzeme": emici_malzeme,
        "emici_ic_yaricap": emici_ic_yaricap, "emici_aci": emici_aci,
        "donme": donme, "baslangic_acisi": baslangic_acisi,
    }


def tally(ad, skorlar, filtreler=None, nuklidler=None):
    """Tally tanimi."""
    return {
        "ad": ad,
        "skorlar": list(skorlar),
        "filtreler": list(filtreler or []),
        "nuklidler": list(nuklidler or []),
    }


def filtre_enerji(gruplar):
    """Enerji grup siniri filtresi (eV, artan)."""
    return {"tur": "enerji", "gruplar": list(gruplar)}


def filtre_mesh(boyut, alt, ust):
    """Duzenli mesh filtresi. boyut=[nx,ny,nz], alt/ust=[x,y,z] (cm)."""
    return {"tur": "mesh", "boyut": list(boyut), "alt": list(alt), "ust": list(ust)}


def filtre_mesh_otomatik(boyut):
    """
    Sinirlari model KURULURKEN turetilen mesh filtresi (bkz.
    kurucu.tally_mesh_sinirlari). Sinirlari olusturma aninda dondurmak,
    sonradan yansitici eklenen bir modelde mesh'i eski olcude birakiyordu
    (olculdu: model 61.42 cm, mesh +/-10.71 cm).
    """
    return {"tur": "mesh", "boyut": list(boyut), "otomatik": True}


def filtre_malzeme(adlar):
    """Malzeme filtresi."""
    return {"tur": "malzeme", "adlar": list(adlar)}
