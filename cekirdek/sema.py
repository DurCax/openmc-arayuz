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
   (meta)       : baslik, kategori, seviye, referans, baslik_en, aciklama_en --
                  ornek galerisi bilgisi (cekirdek/ornek_bilgi.py); fizige
                  girmez, tamamla() aynen korur

 NOTLAR
   "bosluk" ayrilmis bir malzeme adidir -- OpenMC'de None (void) demektir,
   malzemeler listesinde tanimlanmaz.
   Bolge listesinde son elemanin "r" degeri null olmalidir: "disarisi" anlamina
   gelir ve o bolge hucreyi doldurur.
================================================================================
"""

import json
import copy
import os

from cekirdek import goc as _goc
from cekirdek.ceviri import _

# Spec sema surumu. Bolum eklendiginde artirilir; yukle() eski surumleri
# once goc ettirir (cekirdek/goc.py zinciri), sonra eksik alanlari
# varsayilanla tamamlar. 3: esnek geometri (geometri, tamburlar).
SEMA_SURUM = _goc.GUNCEL_SURUM

# Gelismis (agac) geometri modunda kor.tur bu degeri alir; tek gercek kaynak
# spec["geometri"]dir (docs/GEOMETRI_MODELI.md).
AGAC = "agac"


class AgacModuHatasi(RuntimeError):
    """Gelismis (agac) modda kor alanlarindan okuma yapildi. Goc etmemis bir
    okuyucu sessizce yanlis deger yerine bu hatayi uretir (R-8)."""

# OpenMC'de void anlamina gelen ayrilmis malzeme adi
BOSLUK = "bosluk"

# Ornek meta alanlari (cekirdek/ornek_bilgi.py sozlesmesi). Istege baglidir;
# varsa tamamla() aynen korur. Fizige girmez: tukenme "sonuc eskidi mi"
# karsilastirmasi bunlari disarida birakir.
META_ALANLARI = ("baslik", "kategori", "seviye", "referans", "baslik_en", "aciklama_en")

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
    # Istege bagli "gruplar": gecikmeli notron grup sayisi (beta_i, lambda_i) --
    #   0 = yalniz toplam beta_eff; 6 = ENDF/B-VII.1/VIII.0; 8 = JEFF-3.1+.
    #   Varsayilana YAZILMAZ (kinetik kapali modellerin spec'i/onbellek ozeti
    #   degismesin); yoksa cekirdek/kinetik_oku.grup_sayisi 6 kabul eder.
    "kinetik": {"var": False, "nesil": 10},
}

# Cubuk bazli guc dagilimi (DistribcellFilter). Kafeste tekrarlanan bir
# cubugun her ornegi ayri sayilir; buradan F_dH ve (3B modelde) F_q cikar.
#
# SEMA KARARI (Dalga 2 on-commit; uygulama Ajan 8b, testler/test_guc_coklu.py):
#   Cok turlu guc dagilimi icin hedef cubuk TEK alan yerine LISTE olur:
#       "guc_dagilimi": {"var": true,
#                        "cubuklar": [{"cubuk": "yakit_a", "bolge": 0},
#                                     {"cubuk": "yakit_b", "bolge": 0}], ...}
#   - Okuma (tamamla): eski "cubuk"/"bolge" alanlari tek ogeli listeye cevrilir
#     ({"cubuk": ad, "bolge": bolge or 0}); "cubuk" None/eksikse cubuklar = [].
#     Hem eski hem yeni alan varsa "cubuklar" kazanir.
#   - Yazma: yalniz yeni bicim ("cubuk" ve "bolge" ust alanlari yazilmaz).
#   - Varsayilan: "cubuklar": [].
#   - Normalizasyon listedeki TUM yakit cubuklari uzerinden yapilir.
#   UYGULANDI (Dalga 2, Ajan 8b). Calisma aninda (bellekteki spec) eski
#   "cubuk" alani yazilmissa (eski kod, arayuzun tek secimli kutusu) o TAZE
#   niyettir ve guc_hedefleri() onu kullanir; kaydet() yeni bicime cevirir.
VARSAYILAN_GUC = {
    "var": False,
    # hedef cubuklar: [{"cubuk": ad, "bolge": radyal bolge (0 = en ic)}]
    "cubuklar": [],
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
                                  # altigen_kafes | tek_plaka | kuresel | tamburlu
    "cubuk": None,
    "demet": None,
    "plaka": None,
    "adim": 1.26,                 # cm -- tek_cubuk / tek_demet icin hucre adimi
    "boyut": [1, 1],              # kare_kafes icin [nx, ny]
    # kare_kafes: satir satir; altigen_kafes: DISTAN ICE halka listesi (demet
    # haritasiyla ayni bicim, bkz. cekirdek/altigen.py)
    "harita": [],
    # altigen_kafes: halka sayisi (merkez dahil; 2 -> 7 demet) ve kor kafesi
    # yonelimi (HexLattice anlaminda). Demet pin kafesi 'y' ise kor 'x'
    # olmalidir (birbirine 90 derece; bkz. cekirdek/altigen_kor.py).
    "halka_sayisi": 2,
    "yonelim": "x",
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
    #     anahtar  : yalnizca haritali korlarda (kare_kafes, altigen_kafes)
    #                -- ayni harita, katmana ozel
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
EKSENEL_DESTEKLI = ("tek_cubuk", "tek_plaka", "tek_demet", "kare_kafes", "altigen_kafes",
                    "tamburlu")

# Ana dolgusu tek bir ad degil KOR HARITASI olan turler (harf -> demet).
HARITALI_KORLAR = ("kare_kafes", "altigen_kafes")

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
    # adim: demet adimi (duz yuzden duz yuze); harita: halka listesi
    "altigen_kafes": ("adim", "halka_sayisi", "harita", "anahtar", "yonelim", "yansitici"),
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
    if kor.get("tur") in HARITALI_KORLAR:
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


# Kaydedilmemis projelerin (bos sablon, ornek kopyasi) kosu dizini tabani.
# Eskiden goreli "kosu" dizini os.getcwd()'ye dusuyordu: uygulamayi depodan
# baslatan ogrencinin kosulari depo icine yaziliyordu (Ajan 9 bulgusu).
KOSU_KOKU = os.path.join(os.path.expanduser("~"), "openmc_kosular")


def kosu_tabani(proje_yolu=None):
    """Goreli kosu dizinlerinin tabani: kayitli projede projenin dizini,
    kaydedilmemiste ~/openmc_kosular."""
    return os.path.dirname(os.path.abspath(proje_yolu)) if proje_yolu else KOSU_KOKU


def yeni_spec(ad: str = "adsız model", kor_turu: str = "tek_cubuk") -> dict:
    """
    GERCEKTEN bos bir spec dondurur (malzeme, parca, demet, tally yok); yalniz
    kor turu secilir (v3 K1 "Sifirdan"). kor_turu KOR_TUR_ALANLARI'ndan biri
    olmalidir, degilse ValueError. YENI modellerde entropi agi modelden
    turetilir (entropi_mesh.otomatik; kaynak.entropi_boyutu): 2B'den 3B'ye
    gecince nz kendiliginden 1 -> 8 olur. Eski dosyalarda (anahtar yok)
    dosyadaki "boyut" aynen kullanilir -- VARSAYILAN_AYARLAR'a eklenmedi,
    yoksa tamamla() kullanicinin sectigi boyutu ezerdi.
    """
    if kor_turu not in KOR_TUR_ALANLARI:
        raise ValueError(_("bilinmeyen kor türü: %r") % (kor_turu,))
    kor = copy.deepcopy(VARSAYILAN_KOR)
    kor["tur"] = kor_turu
    kor_alanlarini_ayikla(kor)
    spec = {
        "surum": SEMA_SURUM,
        "ad": ad,
        "aciklama": "",
        "malzemeler": [],
        "cubuklar": [],
        "plakalar": [],
        "demetler": [],
        "kor": kor,
        "ayarlar": copy.deepcopy(VARSAYILAN_AYARLAR),
        "tallyler": [],
        "guc_dagilimi": copy.deepcopy(VARSAYILAN_GUC),
        "tukenme": copy.deepcopy(VARSAYILAN_TUKENME),
        "calistirma": copy.deepcopy(VARSAYILAN_CALISTIRMA),
        # Esnek geometri (surum 3): sablon modunda None; gelismis modda
        # {"kok", "parcalar", "gruplar"} (docs/GEOMETRI_MODELI.md §3).
        "geometri": None,
        "tamburlar": [],
    }
    spec["ayarlar"]["entropi_mesh"]["otomatik"] = True
    return spec



def agac_modu(spec):
    """Spec gelismis (agac) geometri modunda mi?"""
    return ((spec or {}).get("kor") or {}).get("tur") == AGAC


def _agac_degil(kor, islev):
    if isinstance(kor, dict) and kor.get("tur") == AGAC:
        raise AgacModuHatasi(
            _("%s() gelişmiş (ağaç) geometri modunda kullanılamaz: kor alanları yok; "
            "cekirdek.geometri API'sini kullanın") % islev)


def model_yuksekligi(spec):
    """
    Modelin toplam eksenel yuksekligi [cm]; 2B modelde None. Sablon modunda
    kor_yuksekligi(kor) ile ayni; gelismis modda agactan (geometri.yukseklik).
    """
    if agac_modu(spec):
        from cekirdek import geometri
        return geometri.yukseklik(geometri.model(spec))
    return kor_yuksekligi(spec["kor"])


def eksenel_katmanlar(kor):
    """
    Gecerli eksenel katmanlari [(z_alt, z_ust, katman), ...] olarak dondurur.
    Katmanlama kapaliysa ya da hicbir gecerli katman yoksa None doner.
    Katmanlar ALTTAN USTE sirayla verilir; kor z=0 etrafinda ortalanir.
    Gelismis (agac) modda AgacModuHatasi: katmanlar agactadir
    (cekirdek.geometri.eksenel_dilimler).
    """
    _agac_degil(kor, "eksenel_katmanlar")
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
    Gelismis (agac) modda AgacModuHatasi; yerine model_yuksekligi(spec).
    """
    _agac_degil(kor, "kor_yuksekligi")
    katmanlar = eksenel_katmanlar(kor)
    if katmanlar:
        return katmanlar[-1][1] - katmanlar[0][0]
    h = kor.get("yukseklik")
    return float(h) if h else None


# ----------------------------------------------------------------------------
# Oku / yaz
# ----------------------------------------------------------------------------

# Arayuzun hedef cubuk kutusundaki ozel secimler (dosyaya yazilmaz):
#   GUC_LISTE : dosyadaki "cubuklar" listesi aynen kalir
#   GUC_TUM   : uygun butun yakit cubuklari (arayuz listeyi kendisi kurar)
GUC_LISTE = "__liste__"
GUC_TUM = "__tum__"


def guc_hedefleri(g):
    """
    Guc dagilimi hedefleri [{"cubuk": ad, "bolge": i}] (yeni liste, kopya).
    Eski "cubuk" alani varsa (tamamla'dan gecmemis eski sozluk ya da calisma
    aninda eski kodun yazdigi alan) tek ogeli liste; "cubuk" None ise bos
    liste. Arayuzun ozel secimleri (GUC_LISTE, GUC_TUM) "cubuklar"a bakar.
    """
    g = g or {}
    ad = g.get("cubuk")
    if "cubuk" in g and ad not in (GUC_LISTE, GUC_TUM):
        return [{"cubuk": ad, "bolge": int(g.get("bolge") or 0)}] if ad else []
    return [{"cubuk": h.get("cubuk"), "bolge": int(h.get("bolge") or 0)}
            for h in (g.get("cubuklar") or [])]


def _guc_yeni_bicim(g):
    """Guc sozlugunun yeni bicimli kopyasi (eski cubuk/bolge alanlari yok)."""
    yeni = {k: copy.deepcopy(v) for k, v in g.items() if k not in ("cubuk", "bolge")}
    yeni["cubuklar"] = guc_hedefleri(g)
    return yeni


def _eski_guc_tasi(ham_guc, birlesik):
    """tamamla icin: eski cubuk/bolge -> cubuklar; "cubuklar" varsa o kazanir.
    'birlesik' tamamla'nin kendi kopyasidir (girdi degismez)."""
    ham_guc = ham_guc or {}
    if "cubuklar" in ham_guc:
        birlesik["cubuklar"] = guc_hedefleri({"cubuklar": ham_guc["cubuklar"]})
    else:
        birlesik["cubuklar"] = guc_hedefleri({"cubuk": ham_guc.get("cubuk"),
                                              "bolge": ham_guc.get("bolge")})
    birlesik.pop("cubuk", None)
    birlesik.pop("bolge", None)
    return birlesik


def kaydet(spec, dosya):
    """Spec'i JSON olarak yazar (UTF-8, okunabilir girinti). Guc dagilimi
    yeni bicimde yazilir (eski cubuk/bolge alanlari yok); spec degismez."""
    if isinstance(spec.get("guc_dagilimi"), dict):
        spec = dict(spec, guc_dagilimi=_guc_yeni_bicim(spec["guc_dagilimi"]))
    if isinstance(spec.get("geometri"), dict):
        # "_" ile baslayan alanlar calisma anindaki turetilmis notlardir
        # (genislet'in _kaynak/_kutu notlari); diske yazilmaz.
        spec = dict(spec, geometri=_turetilmisleri_ayikla(spec["geometri"]))
    # Eski surumlu ya da bozuk bir dosyanin ustune yazmadan once yedek (M2).
    _goc.yedekle(dosya)
    with open(dosya, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return dosya


def _turetilmisleri_ayikla(deger):
    """Ic ice yapidan "_" ile baslayan sozluk anahtarlarini atar (kopya)."""
    if isinstance(deger, dict):
        return {k: _turetilmisleri_ayikla(v) for k, v in deger.items()
                if not (isinstance(k, str) and k.startswith("_"))}
    if isinstance(deger, list):
        return [_turetilmisleri_ayikla(v) for v in deger]
    return deger


def yukle(dosya):
    """
    JSON spec okur, sema surumunu goc ettirir (cekirdek/goc.py) ve eksik
    alanlari varsayilanlarla tamamlar. Bozuk dosya, sayi olmayan surum,
    daha yeni surum ya da eksik zorunlu bolum goc.GocHatasi (ValueError).
    """
    ham, _adimlar = _goc.dosya_oku(dosya)
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
    spec = yeni_spec(ham.get("ad", "adsız model"))
    for anahtar in ("surum", "ad", "aciklama", "malzemeler", "cubuklar",
                    "plakalar", "demetler", "tallyler") + META_ALANLARI:
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
    _eski_guc_tasi(ham.get("guc_dagilimi"), spec["guc_dagilimi"])
    # Esnek geometri (surum 3). Gelismis modda kor yalniz {"tur": "agac"}dir:
    # varsayilan kor alanlari BIRLESTIRILMEZ -- goc etmemis bir okuyucu
    # sessizce varsayilan deger okumasin (R-8).
    if (ham.get("kor") or {}).get("tur") == AGAC:
        spec["kor"] = {"tur": AGAC}
    spec["geometri"] = copy.deepcopy(ham.get("geometri"))
    spec["tamburlar"] = copy.deepcopy(ham.get("tamburlar") or [])
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


# Bolunen alt moduller (Dalga G-1): adlar burada yeniden disa verilir.
from cekirdek.sema_yapici import (  # noqa: E402,F401
    malzeme, bilesen, cubuk, bolge, kontrol_cubugu, plaka, demet, demet_altigen,
    demet_kilifi, eksenel_bolge, kabuk, tambur, tally, filtre_enerji, filtre_mesh,
    filtre_mesh_otomatik, filtre_malzeme)
from cekirdek.sema_basvuru import (  # noqa: E402,F401
    kullanilan_malzemeler, malzeme_etiketi, malzeme_adi_sorunu, malzeme_adini_degistir,
    malzeme_referanslari, _MALZEME_BOLUMLERI)
