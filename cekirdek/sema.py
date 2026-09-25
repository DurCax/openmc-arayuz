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
    "kaynak": {
        "tur": "nokta",                # nokta | kutu
        "konum": [0.0, 0.0, 0.0],
        # Parcacik turu. "photon" secilirse foton tasinimi da acilir ve
        # kutuphanede foton verisi bulunmasi gerekir.
        "parcacik": "neutron",         # neutron | photon
        # Kaynak siddeti [parcacik/s]. Sabit kaynak modunda tally sonuclari
        # KAYNAK PARCACIGI BASINA verilir; mutlak birim icin bununla carpilir.
        # Ozdeger modunda hicbir etkisi yoktur.
        "kuvvet": 1.0,
        # --- enerji dagilimi ---
        #   watt      : fisyon tayfi  chi(E) ~ exp(-E/a) sinh(sqrt(bE))
        #   maxwell   : Maxwell tayfi ~ sqrt(E) exp(-E/theta)
        #   tek       : tek enerjili (monoenerjetik) kaynak
        #   ayrik     : ayrik cizgiler [[E, olasilik], ...]  (or. Co-60 gamalari)
        #   histogram : grup grup tayf (kenarlar N+1, degerler N)
        #   fuzyon    : D-T / D-D fuzyon tayfi (Muir; iyon sicakligi genislemesi)
        # ONEMLI: ozdeger (k-eff) modunda bu yalnizca BASLANGIC tahminidir;
        # pasif cevrimler icinde gercek fisyon tayfiyla degisir. Enerji tayfi
        # asil SABIT KAYNAK modunda belirleyicidir.
        "enerji": {
            "tur": "watt",
            "a": 988.0e3,              # watt  [eV]   -- U-235 termal fisyon
            "b": 2.249e-6,             # watt  [1/eV]
            "theta": 1.2932e6,         # maxwell [eV]
            "enerji": 14.1e6,          # tek [eV]
            "noktalar": [],            # ayrik: [[E_eV, olasilik], ...]
            "kenarlar": [],            # histogram: N+1 grup kenari [eV]
            "degerler": [],            # histogram: N grup degeri
            "e0": 14.08e6,             # fuzyon: ortalama enerji [eV] (D-T)
            "kutle_orani": 5.0,        # fuzyon: reaktif kutlelerin toplami (D+T=5)
            "iyon_sicaklik": 20.0e3,   # fuzyon: iyon sicakligi kT [eV]
        },
        # --- acisal dagilim ---
        #   izotropik : her yone esit
        #   tek_yon   : tek yonlu demet (kalem demet)
        #   koni      : "yon" ekseni etrafinda yari-acilimi "koni_aci" olan koni
        "aci": {"tur": "izotropik", "yon": [0.0, 0.0, 1.0], "koni_aci": 30.0},
    },
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

# Tukenme (yanma) hesabi. Ayrintilar: cekirdek/tukenme.py
VARSAYILAN_TUKENME = {
    "var": False,
    # otomatik: modelde hidrojen/doteryum ya da grafit S(a,b) varsa termal,
    # yoksa hizli. casl_*: 228 nuklidlik basitlestirilmis zincir, yaklasik
    # 3 kat hizli ama yalnizca on inceleme icindir.
    "zincir": "otomatik",       # otomatik | termal | hizli | casl_termal | casl_hizli
    # GUC YOGUNLUGU W/gHM. Mutlak guc [W] kullanilmaz: 2B bir modelde "cm
    # basina" olmak zorunda kalirdi ve bu sessiz bir birim tuzagidir.
    # Tipik: PWR ~38-40, BWR ~25, SFR ~ 50-100 W/gHM.
    "guc_yogunlugu": 40.0,
    "adimlar": [0.5, 1.5, 3.0, 5.0, 10.0, 10.0],
    "adim_birimi": "d",         # d | MWd/kg
    "entegrator": "cecm",       # cecm (adim basina 2 transport) | predictor (1)
    # false: ayni malzemeyi iceren butun hucreler TEK malzeme olarak yanar
    #        (demet ortalamasi, hizli). true: cubuk cubuk yanma (cok agir).
    "malzemeleri_ayir": False,
    # Yakit disinda yanmasi istenen malzemeler (or. Gd2O3 yanabilir zehir).
    # Fisil malzemeler otomatik eklenir.
    "ek_malzemeler": [],
    "izlenen": ["U235", "U238", "Pu239", "Pu240", "Pu241", "Xe135", "Sm149"],
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
    # ------------------------------------------------------------------
    # Eksenel heterojenlik: kor z yonunde KATMANLARA ayrilir.
    #   Gercek bir reaktorde aktif yakit tek bir eksenel bolge degildir:
    #   altta ve ustte yansitici, aktif bolgenin ucunda dogal uranyum
    #   blanket, gaz plenumu, farkli zenginlik kusaklari bulunur. Bunlar
    #   olmadan eksenel guc sekli ve reaktivite katsayilari gercekci cikmaz.
    #
    #   Her katman:
    #     ad       : gorunen ad (hucre adi olarak da yazilir)
    #     yukseklik: cm
    #     dolgu    : o katmani dolduran cubuk/plaka/demet/malzeme adi.
    #                None birakilirsa korun ANA dolgusu kullanilir.
    #     anahtar  : yalnizca kare_kafes icin -- ayni harita, katmana ozel
    #                harf -> demet eslemesi (eksenel zenginlik kusaklama).
    #
    #   "var" acikken modelin toplam yuksekligi katman yuksekliklerinin
    #   TOPLAMIDIR; "yukseklik" alani yok sayilir (tek gercek kaynak kurali).
    # ------------------------------------------------------------------
    "eksenel": {"var": False, "bolgeler": []},
    "sinir": {"yan": "reflective", "alt": "reflective", "ust": "reflective"},
}

# Eksenel katmanlamayi destekleyen kor turleri. "kuresel"de eksen kavrami
# yoktur; orada katman istemek anlamsizdir.
EKSENEL_DESTEKLI = ("tek_cubuk", "tek_plaka", "tek_demet", "kare_kafes", "tamburlu")

# ----------------------------------------------------------------------------
# Kor turune OZGU alanlar -- hangi alan hangi turde anlamlidir (TEK tanim).
#   Ortak alanlar (tur, yukseklik, eksenel, sinir) burada yoktur.
#   Arayuz yalnizca secili turun alanlarini yazar; digerleri VARSAYILAN_KOR
#   degerine doner (kor_alanlarini_ayikla). Sebep: kurucu/dogrula/tukenme
#   "ana dolgu"yu  kor.cubuk or kor.demet or kor.plaka or kor.dolgu
#   zinciriyle okur; tek_demet bir modelde kalmis bir 'cubuk' degeri aktif
#   eksenel araligi, dogrulamayi ve tukenme hacimlerini SESSIZCE degistirir.
#   "yansitici" tek_demet ve kare_kafes'te istege bagli, tamburlu'da ZORUNLU
#   (tamburlar kusagin icine gomulur); kare_kafes'te malzemesi kafes disini
#   da doldurur.
# ----------------------------------------------------------------------------
KOR_TUR_ALANLARI = {
    "tek_cubuk":  ("cubuk", "adim"),
    "tek_plaka":  ("plaka",),
    "tek_demet":  ("demet", "yansitici"),
    "kare_kafes": ("adim", "boyut", "harita", "anahtar", "yansitici"),
    "kuresel":    ("kabuklar",),
    "tamburlu":   ("dolgu", "kor_yaricap", "tambur", "yansitici"),
}
KOR_TURE_OZGU = tuple(sorted({a for alanlar in KOR_TUR_ALANLARI.values() for a in alanlar}))

# Arayuzde editoru OLMAYAN alanlar tur degisince silinmez: kuresel kabuklar
# yalnizca JSON'dan girilebilir; tur kutusu bir kez yanlislikla degisince
# (or. fare tekerlegi) kullanici onlari arayuzden geri getiremezdi. Kurucu,
# dogrulayici ve tukenme kabuklari YALNIZCA kuresel turde okur -- kalmalari
# zararsizdir.
KOR_KORUNAN = ("kabuklar",)


def ana_dolgu(kor):
    """
    Korun ANA dolgusunun adi -- kor TURUNE gore.

    Once birkac yerde `cubuk or demet or plaka or dolgu` zinciri kullaniliyordu.
    Tur'e bakmadigi icin eski (baska bir turden kalma) bir alan varsa onu
    seciyordu; kare_kafes'te ise ana dolgu tek bir ad degil KOR HARITASININ
    kendisidir (bkz. katman_adaylari). kare_kafes ve kuresel icin None doner.
    """
    alan = {"tek_cubuk": "cubuk", "tek_plaka": "plaka",
            "tek_demet": "demet", "tamburlu": "dolgu"}.get(kor.get("tur"))
    return kor.get(alan) if alan else None


def katman_adaylari(kor, katman=None):
    """
    Bir eksenel katmani (ya da katmansiz koru) dolduran adlarin listesi.
    kare_kafes'te bu, kor haritasindaki harflerin gosterdigi demetlerdir
    (katmana ozel 'anahtar' uygulanmis olarak).
    """
    katman = katman or {}
    if katman.get("dolgu"):
        return [katman["dolgu"]]
    if kor.get("tur") == "kare_kafes":
        esleme = dict(kor.get("anahtar") or {})
        esleme.update(katman.get("anahtar") or {})
        return [v for v in esleme.values() if v]
    adaylar = [ana_dolgu(kor)]
    adaylar += list((katman.get("anahtar") or {}).values())
    return [a for a in adaylar if a]


def kor_alanlarini_ayikla(kor, korunan=KOR_KORUNAN):
    """
    Secili kor turune ait OLMAYAN ture ozgu alanlari varsayilana dondurur
    (yerinde degistirir ve kor'u dondurur). Kuresel duzenekte eksen kavrami
    olmadigi icin yukseklik de temizlenir.
    """
    tur = kor.get("tur")
    izinli = set(KOR_TUR_ALANLARI.get(tur, ()))
    for alan in KOR_TURE_OZGU:
        if alan not in izinli and alan not in korunan:
            kor[alan] = copy.deepcopy(VARSAYILAN_KOR[alan])
    if tur == "kuresel":
        kor["yukseklik"] = None
    return kor


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
        "tukenme": copy.deepcopy(VARSAYILAN_TUKENME),
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


def eksenel_bolge(ad, yukseklik, dolgu=None, anahtar=None):
    """Eksenel katman tanimi uretir (alttan uste sirayla verilir)."""
    b = {"ad": ad, "yukseklik": float(yukseklik), "dolgu": dolgu}
    if anahtar:
        b["anahtar"] = dict(anahtar)
    return b


def eksenel_katmanlar(kor):
    """
    Gecerli eksenel katmanlari [(z_alt, z_ust, katman), ...] olarak dondurur.
    Katmanlama kapaliysa ya da hicbir gecerli katman yoksa None doner.
    Katmanlar ALTTAN USTE sirayla verilir; kor z=0 etrafinda ortalanir.
    """
    eks = kor.get("eksenel") or {}
    if not eks.get("var"):
        return None
    katmanlar = [b for b in (eks.get("bolgeler") or [])
                 if float(b.get("yukseklik") or 0.0) > 0.0]
    if not katmanlar:
        return None
    toplam = sum(float(b["yukseklik"]) for b in katmanlar)
    z = -toplam / 2.0
    cikti = []
    for b in katmanlar:
        h = float(b["yukseklik"])
        cikti.append((z, z + h, b))
        z += h
    return cikti


def kor_yuksekligi(kor):
    """
    Modelin toplam eksenel yuksekligi [cm]; 2B modelde None.

    Eksenel katmanlama acikken bu TOPLAM KATMAN YUKSEKLIGIDIR ve "yukseklik"
    alani yok sayilir. Iki yerden yukseklik okumak (biri katmanlardan, biri
    alandan) er ya da gec birbirini tutmaz; tek gercek kaynak burasidir.
    """
    katmanlar = eksenel_katmanlar(kor)
    if katmanlar:
        return katmanlar[-1][1] - katmanlar[0][0]
    h = kor.get("yukseklik")
    return float(h) if h else None


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


def _derin_birlestir(taban, ustu):
    """
    "ustu" sozlugunu "taban" uzerine ic ice yazar ve tabani dondurur.
    Listeler BUTUN olarak degistirilir (harita, bolgeler, kabuklar gibi
    kullanici verisinde kismi birlestirme anlamsiz olurdu).
    """
    for k, v in (ustu or {}).items():
        if isinstance(v, dict) and isinstance(taban.get(k), dict):
            _derin_birlestir(taban[k], v)
        else:
            taban[k] = v
    return taban


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
    # Ic ice sozlukler: varsayilanin uzerine DERIN birlestirme.
    #   Sig update() yeterli DEGILDI: "kaynak" gibi ic ice bir sozluge yeni
    #   alan eklendiginde, o sozlugu iceren eski bir dosya tum yeni alanlari
    #   kaybediyordu (ornegin kaynak.enerji hic olusmuyordu) ve hata ancak
    #   kurucu.py'de KeyError olarak cikiyordu.
    for anahtar, vars_ in (("kor", VARSAYILAN_KOR),
                           ("ayarlar", VARSAYILAN_AYARLAR),
                           ("guc_dagilimi", VARSAYILAN_GUC),
                           ("tukenme", VARSAYILAN_TUKENME),
                           ("calistirma", VARSAYILAN_CALISTIRMA)):
        spec[anahtar] = _derin_birlestir(copy.deepcopy(vars_),
                                         ham.get(anahtar, {}))
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
    # Kabuklar yalnizca kuresel turde geometriye girer (bkz. KOR_KORUNAN).
    if spec["kor"].get("tur") == "kuresel":
        for k in (spec["kor"].get("kabuklar") or []):
            if k.get("malzeme") and k["malzeme"] != BOSLUK:
                adlar.add(k["malzeme"])
    yans = spec["kor"].get("yansitici") or {}
    # Tamburlu korda yansitici ZORUNLUDUR; kurucu onu "var" alanina bakmadan kurar.
    yans_var = yans.get("var") or spec["kor"].get("tur") == "tamburlu"
    if yans_var and yans.get("malzeme") and yans["malzeme"] != BOSLUK:
        adlar.add(yans["malzeme"])
    return adlar
