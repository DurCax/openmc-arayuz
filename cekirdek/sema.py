# -*- coding: utf-8 -*-
"""
================================================================================
 sema.py  --  Model tanimi (spec) semasi, varsayilanlar, oku/yaz
================================================================================

 Arayuz dogrudan OpenMC nesnelerini degil, bu modulde tanimlanan JSON "spec"
 yapisini duzenler. Spec tek gercek kaynaktir; ondan hem openmc.Model
 (kurucu.py) hem de tek basina calisan Python betigi (kod_uret.py) uretilir.

 KULLANIM
   from cekirdek import sema
   spec = sema.yeni_spec("PWR pin hucre")
   sema.kaydet(spec, "ornek.json")
   spec = sema.yukle("ornek.json")

 SPEC BOLUMLERI
   malzemeler   : malzeme tanimlari (bilesim, yogunluk, sicaklik, S(a,b), renk)
   cubuklar     : es merkezli silindirik yakit cubuklari
   plakalar     : MTR tipi plaka yakit elemanlari
   demetler     : kafes (lattice) tanimlari -- kare veya altigen
   kor          : kor duzeni, yansitici, yukseklik, sinir kosullari
   ayarlar      : cevrim/parcacik/kaynak/sicaklik
   tallyler     : tally tanimlari
   calistirma   : is parcacigi sayisi, kosu dizini

 NOTLAR
   "bosluk" ayrilmis bir malzeme adidir -- OpenMC'de None (void) demektir,
   malzemeler listesinde tanimlanmaz.
   Bolge listesinde son elemanin "r" degeri null olmalidir: "disarisi" anlamina
   gelir ve o bolge hucreyi doldurur.
================================================================================
"""

import json
import copy

# Spec sema surumu. Bolum eklendiginde artirilir; yukle() eski surumleri
# okuyup eksik alanlari varsayilanla tamamlar.
SEMA_SURUM = 1

# OpenMC'de void anlamina gelen ayrilmis malzeme adi
BOSLUK = "bosluk"

# ----------------------------------------------------------------------------
# Varsayilan bolumler
# ----------------------------------------------------------------------------

VARSAYILAN_AYARLAR = {
    "mod": "eigenvalue",          # eigenvalue | fixed source
    "parcacik": 5000,             # cevrim basina parcacik
    "cevrim": 100,                # toplam cevrim (batch)
    "pasif": 20,                  # pasif (inactive) cevrim
    "tohum": 1,                   # rastgele sayi tohumu
    "sicaklik_yontemi": "interpolation",   # nearest | interpolation
    "kaynak": {"tur": "nokta", "konum": [0.0, 0.0, 0.0]},
    # Shannon entropisi mesh'i: kaynak dagiliminin yakinsamasini olcer.
    # Ozdeger hesaplarinda acik olmasi onerilir -- yakinsamamis kaynak
    # k-eff'i yanli tahmin ettirir ve bu baska turlu fark edilmez.
    "entropi_mesh": {"var": True, "boyut": [8, 8, 1]},
    # Kinetik parametreler (IFP yontemi): beta_eff ve uretim zamani Lambda.
    # Kosuyu bir miktar yavaslatir, bu yuzden varsayilan olarak kapalidir.
    "kinetik": {"var": False, "nesil": 10},
}

# Cubuk bazli guc dagilimi (DistribcellFilter). Kafeste tekrarlanan bir
# cubugun her ornegi ayri sayilir; buradan F_dH ve (3B modelde) F_q cikar.
VARSAYILAN_GUC = {
    "var": False,
    "cubuk": None,          # hedef cubuk adi
    "bolge": 0,             # hangi radyal bolge (0 = en icteki, yakit eti)
    "skor": "kappa-fission",
    "eksenel_dilim": 20,    # 3B modelde eksenel bin sayisi; 2B'de yok sayilir
    "toplam_guc": None,     # W -- MODELIN KAPSADIGI bolgenin gucu
}

VARSAYILAN_CALISTIRMA = {
    "is_parcacigi": 8,            # OpenMP is parcacigi (openmc -s N)
    "dizin": "kosu",              # spec dosyasina gore goreli kosu dizini
}

VARSAYILAN_KOR = {
    "tur": "tek_cubuk",           # tek_cubuk | tek_demet | kare_kafes |
                                  # tek_plaka | kuresel | tamburlu
    "cubuk": None,
    "demet": None,
    "plaka": None,
    "adim": 1.26,                 # cm -- tek_cubuk / tek_demet icin hucre adimi
    "boyut": [1, 1],              # kare_kafes icin [nx, ny]
    "harita": [],                 # kare_kafes icin satir satir harf haritasi
    "anahtar": {},                # harf -> demet adi
    "yukseklik": None,            # cm; None => 2B sonsuz (eksenel sinir yok)
    "yansitici": {"var": False, "kalinlik": 20.0, "malzeme": None},
    # Kuresel duzenek: es merkezli kabuklar, ICTEN DISA. Her kabugun "r"
    # degeri DIS yaricapidir; en distaki ayni zamanda modelin sinir yuzeyidir.
    # Kritik kure kriterlerini (Godiva, Jezebel gibi) kurmak icin kullanilir.
    "kabuklar": [],
    # Tamburlu kor: silindirik kor + yansitici kusak + kusak icine gomulu
    # donen kontrol tamburlari (bkz. cekirdek/tambur.py).
    "dolgu": None,                # kor bolgesini dolduran kafes/cubuk/malzeme
    "kor_yaricap": 20.0,
    "tambur": {
        "sayi": 0, "yaricap": 4.0, "merkez_yaricap": 26.0,
        "govde_malzeme": None, "emici_malzeme": None,
        "emici_ic_yaricap": 2.5, "emici_aci": 120.0,
        "donme": 0.0, "baslangic_acisi": 0.0,
    },
    "sinir": {"yan": "reflective", "alt": "reflective", "ust": "reflective"},
}


def yeni_spec(ad="isimsiz model"):
    """Bos ama gecerli bir spec dondurur."""
    return {
        "surum": SEMA_SURUM,
        "ad": ad,
        "aciklama": "",
        "malzemeler": [],
        "cubuklar": [],
        "plakalar": [],
        "demetler": [],
        "kor": copy.deepcopy(VARSAYILAN_KOR),
        "ayarlar": copy.deepcopy(VARSAYILAN_AYARLAR),
        "tallyler": [],
        "guc_dagilimi": copy.deepcopy(VARSAYILAN_GUC),
        "calistirma": copy.deepcopy(VARSAYILAN_CALISTIRMA),
    }


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
                  yonelim="y"):
    """
    Altigen kafes (HexLattice) tanimi.

    halka_sayisi : merkez dahil halka sayisi (1 = tek hucre)
    harita       : halka basina bir dize, DISTAN ICE dogru.
                   Yaricapi k olan halkada 6k karakter, merkezde 1 karakter.
                   Her halkanin karakterleri TEPEDEN baslar, SAAT YONUNDE ilerler.
    yonelim      : "y" (ust/alt yuzler yatay) | "x" (sag/sol yuzler dusey)
    """
    return {
        "ad": ad, "tur": "altigen", "adim": adim,
        "halka_sayisi": halka_sayisi, "yonelim": yonelim,
        "boyut": [halka_sayisi, halka_sayisi],   # geriye uyumluluk icin
        "harita": list(harita), "anahtar": dict(anahtar),
        "dolgu_disi": dolgu_disi,
    }


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


def filtre_malzeme(adlar):
    """Malzeme filtresi."""
    return {"tur": "malzeme", "adlar": list(adlar)}


# ----------------------------------------------------------------------------
# Oku / yaz
# ----------------------------------------------------------------------------

def kaydet(spec, dosya):
    """Spec'i JSON olarak yazar (UTF-8, okunabilir girinti)."""
    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return dosya


def yukle(dosya):
    """JSON spec okur ve eksik alanlari varsayilanlarla tamamlar."""
    with open(dosya, encoding="utf-8") as f:
        ham = json.load(f)
    return tamamla(ham)


def tamamla(ham):
    """
    Eksik bolumleri varsayilanla doldurur. Eski surumden okunan dosyalarin
    yeni alanlar yuzunden patlamamasi icin gerekli.
    """
    spec = yeni_spec(ham.get("ad", "isimsiz model"))
    for anahtar in ("surum", "ad", "aciklama", "malzemeler", "cubuklar",
                    "plakalar", "demetler", "tallyler"):
        if anahtar in ham:
            spec[anahtar] = ham[anahtar]
    # ic ice sozlukler: varsayilanin uzerine yaz
    for anahtar, vars_ in (("kor", VARSAYILAN_KOR),
                           ("ayarlar", VARSAYILAN_AYARLAR),
                           ("guc_dagilimi", VARSAYILAN_GUC),
                           ("calistirma", VARSAYILAN_CALISTIRMA)):
        birlesik = copy.deepcopy(vars_)
        birlesik.update(ham.get(anahtar, {}))
        spec[anahtar] = birlesik
    spec["surum"] = SEMA_SURUM
    return spec


# ----------------------------------------------------------------------------
# Arama yardimcilari
# ----------------------------------------------------------------------------

def malzeme_bul(spec, ad):
    """Ada gore malzeme tanimini dondurur, yoksa None."""
    for m in spec["malzemeler"]:
        if m["ad"] == ad:
            return m
    return None


def cubuk_bul(spec, ad):
    for c in spec["cubuklar"]:
        if c["ad"] == ad:
            return c
    return None


def plaka_bul(spec, ad):
    for p in spec["plakalar"]:
        if p["ad"] == ad:
            return p
    return None


def demet_bul(spec, ad):
    for d in spec["demetler"]:
        if d["ad"] == ad:
            return d
    return None


def kullanilan_malzemeler(spec):
    """
    Modelde gercekten kullanilan malzeme adlarini dondurur ("bosluk" haric).
    Dogrulama ve renk atamasi icin kullanilir.
    """
    adlar = set()
    for c in spec["cubuklar"]:
        for b in c["bolgeler"]:
            if b.get("malzeme") and b["malzeme"] != BOSLUK:
                adlar.add(b["malzeme"])
        iz = c.get("izleyici_malzeme")
        if iz and iz != BOSLUK:
            adlar.add(iz)
    for p in spec["plakalar"]:
        for k in ("et_malzeme", "zarf_malzeme", "sogutucu", "yan_levha_malzeme"):
            if p.get(k) and p[k] != BOSLUK:
                adlar.add(p[k])
    for d in spec["demetler"]:
        if d.get("dolgu_disi") and d["dolgu_disi"] != BOSLUK:
            adlar.add(d["dolgu_disi"])
    t = spec["kor"].get("tambur") or {}
    if int(t.get("sayi") or 0) > 0:
        for anahtar in ("govde_malzeme", "emici_malzeme"):
            if t.get(anahtar) and t[anahtar] != BOSLUK:
                adlar.add(t[anahtar])
    d = spec["kor"].get("dolgu")
    if d and d != BOSLUK and malzeme_bul(spec, d) is not None:
        adlar.add(d)
    for k in (spec["kor"].get("kabuklar") or []):
        if k.get("malzeme") and k["malzeme"] != BOSLUK:
            adlar.add(k["malzeme"])
    yans = spec["kor"].get("yansitici") or {}
    if yans.get("var") and yans.get("malzeme") and yans["malzeme"] != BOSLUK:
        adlar.add(yans["malzeme"])
    return adlar
