# -*- coding: utf-8 -*-
"""
================================================================================
 ana_pencere.py  --  Ana uygulama penceresi (kabuk)
================================================================================
 YERLESIM
   Ust    : menu (Dosya / Duzen / Gorunum / Yardim) + arac cubugu
   Serit  : model basligi -- "Model: ad · 17×17 yakit demeti · 2B · Ozdeger"
            + "Turu degistir..." (kor turu; yalnizca uygunluk.kor_turleri)
   Sol    : editor sekmeleri. Numarasiz; yalnizca modele UYAN sekmeler gorunur
            (cekirdek/uygunluk.gecerli_sekmeler). Sekme basligindaki isaret
            durumu soyler:  !  hata   •  eksik adim   ✓  tamam.
   Sag    : geometri onizlemesi + dogrulama listesi. YALNIZCA tasarim
            sekmelerinde (Malzemeler/Parcalar/Demet/Kor; Hesap ayarlarinda
            yalnizca dogrulama). Calistir/Analiz/Tukenme tum genisligi kullanir.
   Alt    : durum cubugu -- sonraki adim ipucu + "2 hata · 1 uyari" rozeti
            (tiklayinca bulgu listesi acilir, satir ilgili sekmeye goturur).
   Yeni model / acilis: "Ne modelliyorsun?" baslangic ekrani (baslangic.py).

 DALGA 2'DE KALDIRILANLAR
   Rehber seridi (icerigi sekme isaretlerine, ipuclarina ve durum cubuguna
   tasindi), Model menusu (F5/F6/F9 pencere kisayolu olarak kaldi), F10
   "Pencereyi buyut" (main() zaten buyutuyor), "Neden geometri ice
   aktarilamiyor?" diyalogu (ozeti ice aktarma eyleminin ipucunda), "Ornek ac"
   alt menusu (baslangic ekraninda), ayri Kisayollar diyalogu (Yardim'da).

 SEKME DIZINLERI SABITTIR
   Sekiz sekme de QTabWidget'ta kalir; uygun olmayanlar setTabVisible ile
   GIZLENIR, silinmez. Dizinler uygunluk.SEKMELER sirasidir.

 PERFORMANS NOTLARI (olcume dayali)
   1. Model onbellegi  : ayni spec icin openmc.Model yeniden kurulmaz.
                         Olculen: 21.9 ms -> 0.07 ms (bkz. cekirdek/onbellek.py)
   2. Tembel sekme yenileme : bir degisiklikte yalnizca gorunur sekme
                         yenilenir, digerleri "kirli" isaretlenip acildiklarinda
                         guncellenir. Olculen kazanc: degisiklik basina ~34 ms.
   3. Onizleme 300 ms geciktirilir (debounce); hizli yazarken tek cizime duser.

 GERI AL / YINELE
   Spec anlik goruntuleri 700 ms bosta kalinca yigina itilir; ardarda tus
   basislari tek adima birlesir. En fazla 50 adim tutulur.
================================================================================
"""

import copy
import os
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import sema, dogrula, ice_aktar, kod_uret, onbellek, uygunluk
from arayuz.onizleme import OnizlemeWidget
from arayuz.sekme_analiz import AnalizSekmesi
from arayuz.sekme_tukenme import TukenmeSekmesi
from arayuz.sekme_ayar import AyarSekmesi
from arayuz.sekme_calistir import CalistirSekmesi
from arayuz.sekme_cubuk import CubukSekmesi
from arayuz.sekme_demet import DemetSekmesi
from arayuz.sekme_kor import KorSekmesi
from arayuz.sekme_malzeme import MalzemeSekmesi
from arayuz import baslangic, tema
from arayuz.ortak import DurumRozeti, cumle_basi, qt_turkce_cevirisi, tekerlek_korumasi_kur

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORNEKLER = os.path.join(KOK, "ornekler")
UYGULAMA_ADI = "OpenMC Reaktör Kuru Arayüzü"

_GECMIS_SINIR = 50


def _seviye_renk(seviye):
    """Dogrulama seviyesi rengi -- etkin temadan gelir."""
    return tema.renk({"hata": "hata", "uyari": "uyari", "bilgi": "bilgi"}.get(seviye, "bilgi"))


_SEVIYE_ADI = {"hata": "Hata", "uyari": "Uyarı", "bilgi": "Bilgi"}

# Bir konu degistiginde hangi sekmelerin tazelenmesi gerektigi.
# Amac: ayar degisikligi yuzunden kullanicinin kafes secimini sifirlamamak.
# "kor" -> cubuk/demet: kor turu parca ve kafes sekmelerinde neyin
# sunulacagini belirler (uygunluk.parca_turleri); sekmeler acildiklarinda
# yeni ture gore yeniden dolar.
_KONU_BAGIMLILIK = {
    # malzeme listeleri her yerde kullaniliyor; Hesap ayarlarindaki guc
    # dagilimi bolgesi ve Tukenme'nin ek malzemeleri de malzeme adi gosterir
    "malzeme": {"cubuk", "demet", "kor", "ayar", "tukenme"},
    "cubuk":   {"demet", "kor", "ayar"},    # kafes anahtarlari, kor secimi, guc cubugu
    "demet":   {"kor", "ayar"},             # kor hangi demeti kullanacagini secer
    # Hesap ayarlarinda gorunenler (kaynak kutusu, guc dagilimi, eksenel
    # dilim) kor turune ve yukseklige bagli
    "kor":     {"cubuk", "demet", "ayar"},
    "ayar":    set(),
    # Calistir'daki kosu dizini: Tukenme onceki sonucu <dizin>_tukenme'de arar
    "calistirma": {"tukenme"},
    "genel":   {"malzeme", "cubuk", "demet", "kor", "ayar", "tukenme"},
}

# Dogrulama bulgusunun "yer" onekinden o bulguyu duzelten EDITORE.
# (dogrula.py'nin urettigi yerler: malzeme:X, malzemeler, cubuk:X, plaka:X,
#  demet:X, kor, kor/katman N, ayarlar, veri kutuphanesi, kaynak, tally:X,
#  guc dagilimi, guc_dagilimi, tukenme, tukenme/X.)
# Sekme INDEKSI degil editor adi tutulur: indeks calisma aninda bulunur.
_YER_SEKME = [
    ("malzeme", "s_malzeme"), ("cubuk", "s_cubuk"), ("plaka", "s_cubuk"),
    ("demet", "s_demet"), ("kor", "s_kor"),
    ("ayarlar", "s_ayar"), ("veri kutuphanesi", "s_ayar"), ("kaynak", "s_ayar"),
    ("tally", "s_ayar"), ("guc dagilimi", "s_ayar"), ("guc_dagilimi", "s_ayar"),
    ("tukenme", "s_tukenme"),
]

# Editor niteligi -> uygunluk.SEKMELER anahtari (sekme sirasi bu anahtarlarla).
EDITOR_ANAHTARI = {
    "s_malzeme": "malzemeler", "s_cubuk": "parcalar", "s_demet": "demet",
    "s_kor": "kor", "s_ayar": "ayarlar", "s_calistir": "calistir",
    "s_analiz": "analiz", "s_tukenme": "tukenme",
}

# Sekme basliklari (numarasiz).
SEKME_ADLARI = {
    "malzemeler": "Malzemeler", "parcalar": "Parçalar", "demet": "Demet",
    "kor": "Kor", "ayarlar": "Hesap ayarları", "calistir": "Çalıştır",
    "analiz": "Analiz", "tukenme": "Tükenme",
}

# Onizleme + dogrulama paneli yalnizca TASARIM sekmelerinde; Hesap
# ayarlarinda yalnizca dogrulama.
TASARIM_SEKMELERI = ("malzemeler", "parcalar", "demet", "kor")
DOGRULAMA_SEKMELERI = TASARIM_SEKMELERI + ("ayarlar",)

# Kor turlerinin sade adlari ("Turu degistir..." menusu).
TUR_ADLARI = uygunluk.KOR_TURU_ADLARI

_ICE_AKTAR_NOTU = ("Yalnızca malzemeler aktarılır: OpenMC geometrisi ham CSG'dir "
                   "ve bu arayüzün malzeme → parça → demet → kor katmanlarına "
                   "güvenle çevrilemez; geometriyi arayüzde yeniden kurun.")


# ============================================================================
# saf yardimcilar (Qt'siz; testler/test_kabuk.py sinar)
# ============================================================================

def yer_sekme_anahtari(yer):
    """Bulgu 'yer' alanindan sekme anahtari (uygunluk.SEKMELER); yoksa None."""
    yer = (yer or "").lower()
    for onek, ad in _YER_SEKME:
        if yer.startswith(onek):
            return EDITOR_ANAHTARI[ad]
    return None


# Bulgu "yer" kodunun okunur adi: kural dogrula.yer_etiketi'nde (terminal
# ciktisi da ayni adi kullanir).
yer_etiketi = dogrula.yer_etiketi


def tur_ozeti(spec):
    """Kor turunun olculu, sade adi: "17×17 yakıt demeti", "3×3 tam kor"..."""
    kor = spec.get("kor") or {}
    tur = kor.get("tur")
    if tur == "tek_cubuk":
        return "yakıt çubuğu (pin hücre)"
    if tur == "tek_plaka":
        p = sema.plaka_bul(spec, kor.get("plaka") or "") if spec.get("plakalar") else None
        n = (p or {}).get("plaka_sayisi")
        return "plaka elemanı (%d plaka)" % n if n else "plaka elemanı"
    if tur == "tek_demet":
        d = sema.demet_bul(spec, kor.get("demet") or "") if spec.get("demetler") else None
        if d is None:
            return "yakıt demeti"
        if d.get("tur") == "altigen":
            return "%d halkalı altıgen demet" % int(d.get("halka_sayisi") or d.get("boyut", [0])[0])
        nx, ny = (d.get("boyut") or [0, 0])[:2]
        return "%d×%d yakıt demeti" % (nx, ny)
    if tur == "kare_kafes":
        nx, ny = (kor.get("boyut") or [0, 0])[:2]
        return "%d×%d tam kor" % (nx, ny)
    if tur == "tamburlu":
        n = int(((kor.get("tambur") or {}).get("sayi")) or 0)
        return "tamburlu kor (%d tambur)" % n if n else "tamburlu kor"
    if tur == "kuresel":
        n = len(kor.get("kabuklar") or [])
        return "küresel düzenek (%d kabuk)" % n if n else "küresel düzenek"
    return str(tur or "tanımsız kor")


def model_ozet_parcalari(spec):
    """{"ad", "tur", "boyut", "mod"} -- model basliginin parcalari (metin)."""
    oz = uygunluk.model_ozeti(spec)
    if oz["tur"] == "kuresel":
        boyut = "3B"                      # kure eksensizdir ama 3 boyutludur
    else:
        boyut = {"2B": "2B", "3B": "3B", "3B_katmanli": "3B katmanlı"}.get(oz["boyut"], oz["boyut"])
    mod = "Özdeğer (k-eff)" if oz["mod"] == "eigenvalue" else "Sabit kaynak"
    return {"ad": spec.get("ad") or "adsız model", "tur": tur_ozeti(spec),
            "boyut": boyut, "mod": mod}


def model_ozet_metni(spec):
    """"Model: ad · 17×17 yakıt demeti · 2B · Özdeğer (k-eff)" """
    p = model_ozet_parcalari(spec)
    return "Model: %s · %s · %s · %s" % (p["ad"], p["tur"], p["boyut"], p["mod"])


def sekme_isaretleri(spec, hata_sayilari=None, kosu_basarili=False,
                     analiz_sonucu=False, tukenme_sonucu=False):
    """
    Her sekme icin (isaret, tek cumlelik aciklama). isaret:
      "!"  bu sekmede yeri olan bir dogrulama HATASI var (oncelikli)
      "•"  gerekli icerik eksik (malzeme yok; kor turu cubuk istiyor ama
           yok; kafes gerekli ama yok; kor dolgusu secilmemis; hic kosulmadi)
      "✓"  tamam
      ""   istege bagli adim (Analiz, Tukenme) henuz kullanilmadi
    hata_sayilari: {sekme_anahtari: hata_sayisi} (yer_sekme_anahtari ile).
    """
    hata = hata_sayilari or {}
    kor = spec.get("kor") or {}
    tur = kor.get("tur")
    sonuc = {}

    def koy(anahtar, eksik=None, tamam="Tamam: bu adımda eksik ya da hata yok.",
            istege_bagli=None):
        n = hata.get(anahtar, 0)
        if n:
            sonuc[anahtar] = ("!", "Bu sekmede düzeltilmesi gereken %d hata var; "
                                   "ayrıntısı doğrulama listesinde." % n)
        elif eksik:
            sonuc[anahtar] = ("•", eksik)
        elif istege_bagli:
            sonuc[anahtar] = ("", istege_bagli)
        else:
            sonuc[anahtar] = ("✓", tamam)

    koy("malzemeler", None if spec.get("malzemeler") else
        "Eksik: henüz malzeme yok; yakıt, zarf ve soğutucu ekleyin.")

    eksik = None
    if tur in ("tek_cubuk", "tek_demet", "kare_kafes") and not spec.get("cubuklar"):
        eksik = "Eksik: bu kor türü için en az bir yakıt çubuğu tanımlanmalı."
    elif tur == "tek_plaka" and not spec.get("plakalar"):
        eksik = "Eksik: bu kor türü için bir plaka elemanı tanımlanmalı."
    koy("parcalar", eksik)

    koy("demet", "Eksik: bu kor türü için bir demet kurulmalı."
        if tur in ("tek_demet", "kare_kafes") and not spec.get("demetler") else None)

    eksik = None
    alan = {"tek_cubuk": "cubuk", "tek_plaka": "plaka", "tek_demet": "demet",
            "tamburlu": "dolgu"}.get(tur)
    if alan and not kor.get(alan):
        eksik = "Eksik: korun dolgusu henüz seçilmedi."
    elif tur == "kare_kafes" and not kor.get("harita"):
        eksik = "Eksik: kor haritası boş; demetleri haritaya yerleştirin."
    elif tur == "kuresel" and not kor.get("kabuklar"):
        eksik = "Eksik: küresel kabuk tanımlanmadı."
    koy("kor", eksik)

    koy("ayarlar")
    koy("calistir", None if kosu_basarili else
        "Model henüz çalıştırılmadı; hazır olduğunda ÇALIŞTIR (F9).",
        tamam="Tamam: model bu oturumda başarıyla çalıştırıldı.")
    koy("analiz", istege_bagli=None if analiz_sonucu else
        "İsteğe bağlı: reaktivite katsayıları ve kritik arama.",
        tamam="Tamam: bu oturumda bir analiz sonucu var.")
    koy("tukenme", istege_bagli=None if tukenme_sonucu else
        "İsteğe bağlı: yakıtın zamanla tükenmesi (yanma) hesabı.",
        tamam="Tamam: tükenme sonucu görüntüleniyor.")
    return sonuc


def sonraki_adim(isaretler, gorunur, cizildi=True):
    """
    Durum cubugundaki "simdi ne yapmali" ipucu (eski rehber seridinin ozu).
    gorunur: gorunur sekme anahtarlari (sirali).
    """
    for k in gorunur:
        if isaretler.get(k, ("", ""))[0] == "!":
            return "%s sekmesinde hata var — sekmeye gidip düzeltin." % SEKME_ADLARI[k]
    for k in gorunur:
        isaret, aciklama = isaretler.get(k, ("", ""))
        if isaret == "•" and k != "calistir":
            return "Sonraki adım: %s — %s" % (SEKME_ADLARI[k],
                                              aciklama.replace("Eksik: ", ""))
    if not cizildi:
        return "Geometri çiziliyor; önizleme hazır olunca ÇALIŞTIR etkinleşir."
    if isaretler.get("calistir", ("", ""))[0] != "✓":
        return "Model hazır — ÇALIŞTIR (F9) ile hesaplayın."
    if "analiz" in gorunur:
        return ("Koşu tamam — sonuçlar Çalıştır sekmesinde; Analiz sekmesinde "
                "reaktivite katsayılarını hesaplayabilirsiniz.")
    return "Koşu tamam — sonuçlar Çalıştır sekmesinde."


def _alan_varsayilan_mi(kor, alan):
    return kor.get(alan) == sema.VARSAYILAN_KOR.get(alan)


_AD_LISTELERI = ("malzemeler", "cubuklar", "plakalar", "demetler")


def model_adlari(spec):
    """{liste: set(ad)} -- malzeme ve parca adlari (tur hafizasi icin)."""
    return {l: {x.get("ad") for x in spec.get(l) or []} for l in _AD_LISTELERI}


def _adlari_cevir(deger, esle, kaybolan, anahtar=None):
    """
    Tur hafizasindaki bir alan degerinde adlari cevirir. (yeni_deger,
    kaybolan_ad_var_mi) dondurur. Yalnizca AD olabilecek dizgilere bakar:
    sozluk ANAHTARLARI (harita harfleri) ve "harita" satirlari atlanir --
    "A" adli bir demet 1x1 haritanin "A" satirini degistirmesin.
    """
    if anahtar == "harita":
        return deger, False
    if isinstance(deger, str):
        if deger in esle:
            return esle[deger], False
        return deger, deger in kaybolan
    if isinstance(deger, dict):
        yeni, kayip = {}, False
        for k, v in deger.items():
            yeni[k], kv = _adlari_cevir(v, esle, kaybolan, k)
            kayip = kayip or kv
        return yeni, kayip
    if isinstance(deger, list):
        yeni, kayip = [], False
        for v in deger:
            yv, kv = _adlari_cevir(v, esle, kaybolan)
            yeni.append(yv)
            kayip = kayip or kv
        return yeni, kayip
    return deger, False


def tur_hafizasini_esitle(hafiza, onceki, simdiki):
    """
    Kor turu hafizasini ad degisimlerine uydurur (onceki/simdiki:
    model_adlari). Bir listede TEK ad kaybolup TEK ad eklendiyse bu bir
    yeniden adlandirmadir: hafizadaki eski ad yenisine cevrilir. Baska
    kaybolan (silinen) adlari iceren alanlar hafizadan dusurulur; yoksa tur
    geri cevrilince var olmayan bir ada baglanirdi (Ajan 4/5 bulgusu).
    """
    esle, kaybolan = {}, set()
    for l in _AD_LISTELERI:
        giden = onceki.get(l, set()) - simdiki.get(l, set())
        gelen = simdiki.get(l, set()) - onceki.get(l, set())
        if len(giden) == 1 and len(gelen) == 1:
            esle[next(iter(giden))] = next(iter(gelen))
        else:
            kaybolan |= giden
    if not esle and not kaybolan:
        return False
    for tur, alanlar in hafiza.items():
        for alan in list(alanlar):
            yeni, kayip = _adlari_cevir(alanlar[alan], esle, kaybolan, alan)
            if kayip:
                del alanlar[alan]
            else:
                alanlar[alan] = yeni
    return True


def _eksik_parcayi_kur(spec, tur, eklenen=None):
    """
    Yeni kor turunun ihtiyac duydugu parca modelde yoksa sablondan kurar
    (Ajan 9 bulgusu K10): pin -> plaka gecisinde plaka elemani olmadigi icin
    kor "kurulamadı: 'tanımsız plaka elemanı: None'" diyordu ve "+ Plaka"
    dugmesi yalniz plaka modelinde gorundugu icin kullanici cikmaza giriyordu.
    Kurulan parcalarin adlari 'eklenen' listesine yazilir.
    """
    from arayuz import sekme_cubuk as sc
    eklenen = eklenen if eklenen is not None else []

    def cubuk_gerekli():
        if not spec.get("cubuklar"):
            ad = sc.benzersiz_ad(spec, "yakit_cubugu")
            spec.setdefault("cubuklar", []).append(sc.cubuk_sablonu(spec, "yakit", ad))
            eklenen.append(ad)

    def kare_demet_gerekli():
        if not any(d.get("tur", "kare") == "kare" for d in spec.get("demetler", [])):
            cubuk_gerekli()
            from arayuz.sekme_demet import yeni_demet
            ad = sc.benzersiz_ad(spec, "demet")
            spec.setdefault("demetler", []).append(yeni_demet(spec, "kare", ad))
            eklenen.append(ad)

    if tur == "tek_cubuk":
        cubuk_gerekli()
    elif tur == "tek_plaka" and not spec.get("plakalar"):
        ad = sc.benzersiz_ad(spec, "plaka_eleman")
        spec.setdefault("plakalar", []).append(sc.plaka_sablonu(spec, ad))
        eklenen.append(ad)
    elif tur == "tek_demet" and not spec.get("demetler"):
        kare_demet_gerekli()
    elif tur == "kare_kafes":
        kare_demet_gerekli()
    return eklenen


# Bos sablonun varsayilan model adi; tur degisince ad da yeni ture uyar
# (kullanici adi degistirmediyse). Ajan 9: "Yeni yakıt çubuğu" adli model
# plakaya donunce de ayni adla kaliyordu.
_SABLON_ADLARI = {"tek_cubuk": "Yeni yakıt çubuğu", "tek_demet": "Yeni kare yakıt demeti",
                  "tek_plaka": "Yeni plaka elemanı", "tamburlu": "Yeni tamburlu kor",
                  "kare_kafes": "Yeni tam kor"}


def kor_turu_degistir(spec, yeni_tur, hafiza=None, eklenen=None):
    """
    Kor turunu degistirir: tur yazilir, ture ozgu olmayan alanlar temizlenir
    (sema.kor_alanlarini_ayikla) ve yeni turun bos kalan zorunlu secimleri
    mevcut parcalardan doldurulur (ilk cubuk / plaka / kafes; tam korda 1×1
    harita). hafiza ({tur: {alan: deger}}) verilirse eski turun alanlari
    saklanir ve o ture geri donuldugunde -- alan o arada varsayilana dondu
    ise -- geri getirilir (Kor sekmesinin kutularda deger tutmasinin
    karsiligi). Degistiyse True.
    """
    kor = spec["kor"]
    eski = kor.get("tur")
    if yeni_tur == eski:
        return False
    eski_dolgu = sema.ana_dolgu(kor)
    if hafiza is not None and eski:
        hafiza[eski] = {a: copy.deepcopy(kor.get(a))
                        for a in sema.KOR_TUR_ALANLARI.get(eski, ())}
    kor["tur"] = yeni_tur
    sema.kor_alanlarini_ayikla(kor)
    for alan, deger in ((hafiza or {}).get(yeni_tur) or {}).items():
        if _alan_varsayilan_mi(kor, alan):
            kor[alan] = copy.deepcopy(deger)

    _eksik_parcayi_kur(spec, yeni_tur, eklenen)

    def ilk(liste):
        return spec.get(liste)[0]["ad"] if spec.get(liste) else None

    def uygun(ad, liste):
        return ad if ad and any(x["ad"] == ad for x in spec.get(liste, [])) else None

    if yeni_tur == "tek_cubuk" and not kor.get("cubuk"):
        kor["cubuk"] = uygun(eski_dolgu, "cubuklar") or ilk("cubuklar")
    elif yeni_tur == "tek_plaka" and not kor.get("plaka"):
        kor["plaka"] = uygun(eski_dolgu, "plakalar") or ilk("plakalar")
    elif yeni_tur == "tek_demet" and not kor.get("demet"):
        kor["demet"] = uygun(eski_dolgu, "demetler") or ilk("demetler")
    elif yeni_tur == "tamburlu" and not kor.get("dolgu"):
        # Tamburlu korun dolgusu kafes, cubuk ya da malzeme olabilir (plaka degil).
        yakitlar = uygunluk.rol_malzemeleri(spec, "yakit")
        kor["dolgu"] = (uygun(eski_dolgu, "demetler") or uygun(eski_dolgu, "cubuklar")
                        or uygun(eski_dolgu, "malzemeler") or ilk("demetler")
                        or (yakitlar[0] if yakitlar else None))
    elif yeni_tur == "kare_kafes" and not kor.get("harita"):
        # Kare kor haritasi KARE demetlerden kurulur; altigen demet kare
        # hucreye oturmaz (kullanici isterse elle secer, dogrulama uyarir).
        kare = [d["ad"] for d in spec.get("demetler", []) if d.get("tur", "kare") == "kare"]
        ad = eski_dolgu if eski_dolgu in kare else (kare[0] if kare else None)
        d = sema.demet_bul(spec, ad) if ad else None
        if d is not None:
            from arayuz.izgara import adlardan_harita
            kor["adim"] = round(d["adim"] * max(d.get("boyut") or [1]), 6)
            kor["boyut"] = [1, 1]
            kor["harita"], kor["anahtar"] = adlardan_harita([[ad]])
    return True


# ============================================================================
# yardim metni
# ============================================================================

YARDIM_HTML = """
<h2>Yardım ve terimler</h2>

<h3>Nasıl ilerlenir?</h3>
<p>Yalnızca modelinize uyan sekmeler görünür. Sekme başlığındaki işaret
durumu söyler: <b>!</b> düzeltilmesi gereken hata, <b>•</b> eksik adım,
<b>✓</b> tamam. İşaretin üzerine gelince ne yapmanız gerektiği yazar; alttaki
durum çubuğu da sıradaki adımı söyler. Kor türünü üstteki
<b>Türü değiştir…</b> düğmesiyle değiştirebilirsiniz.</p>
<p><b>Önce çiz, sonra çalıştır:</b> geometri önizlemesi başarıyla
çizilmeden ve doğrulama hataları giderilmeden koşu başlamaz; ÇALIŞTIR'a basarsanız
önce neyin eksik olduğu söylenir.</p>

<h3>Temel büyüklükler</h3>
<table cellpadding="5">
<tr><td><b>k-eff</b></td><td>Çoğalma çarpanı. Bir nötron neslinin bir sonraki
nesli ne kadar büyüttüğü. k&gt;1 güç artar, k=1 kritik, k&lt;1 söner.</td></tr>
<tr><td><b>k&infin; (k-inf)</b></td><td>Sonsuz ortam çoğalma çarpanı. Sınırlardan sızıntı
olmadığı varsayılır (yansıtıcı sınır koşulu). Gerçek bir reaktör için üst
sınırdır.</td></tr>
<tr><td><b>Reaktivite (&rho;)</b></td><td>(k-1)/k. Kritiklikten ne kadar uzak
olunduğunun ölçüsü. <b>pcm</b> = 10<sup>-5</sup> birim.</td></tr>
<tr><td><b>Dolar ($)</b></td><td>Reaktivite / &beta;<sub>eff</sub>. 1 $ üstü
geçici rejimde anlık kritiklik demektir.</td></tr>
<tr><td><b>&beta;<sub>eff</sub></b></td><td>Etkin gecikmiş nötron kesri.
Fisyon nötronlarının küçük bir kısmı (~%0.7) gecikmeli çıkar; reaktör denetimi
bu gecikmeye dayanır.</td></tr>
<tr><td><b>&Lambda;</b></td><td>Nötron üretim zamanı. Termal reaktörde ~20 &mu;s,
hızlı metal sistemde ~6 ns.</td></tr>
</table>

<h3>Reaktivite katsayıları (Analiz sekmesi)</h3>
<table cellpadding="5">
<tr><td><b>Doppler katsayısı</b></td><td>Yakıt sıcaklığı arttığında reaktivite
değişimi [pcm/K]. U-238 rezonansları genişler, yakalama artar &rarr;
<b>negatif</b> olmalı. Güvenliğin ilk savunma hattıdır: güç artarsa yakıt ısınır ve
reaktivite kendiliğinden düşer.</td></tr>
<tr><td><b>Moderatör sıcaklık katsayısı</b></td><td>Soğutucu sıcaklığı arttığında
reaktivite değişimi [pcm/K]. Sıcaklık artınca yoğunluk da düşer; ikisi birlikte
hesaplanmalıdır. Termal reaktörde <b>negatif</b> olmalı.</td></tr>
<tr><td><b>Boşluk (void) katsayısı</b></td><td>Soğutucuda boşluk oluşursa
reaktivite değişimi [pcm/%void]. Termal reaktörde negatif olmalı.</td></tr>
<tr><td><b>Bor değeri (worth)</b></td><td>Suda çözünmüş bor başına reaktivite
[pcm/ppm]. Bor nötron emicidir &rarr; negatif. Çok bor, moderatör sıcaklık
katsayısını pozitife doğru iter; bu yüzden sınırlanır.</td></tr>
</table>

<h3>Monte Carlo terimleri</h3>
<table cellpadding="5">
<tr><td><b>Çevrim (batch)</b></td><td>Bir grup nötronun izlendiği tur.</td></tr>
<tr><td><b>Pasif çevrim</b></td><td>Baştaki çevrimler. Kaynak dağılımı henüz
doğru değildir, bu yüzden istatistiğe <b>katılmaz</b>. Tipik 20–50.</td></tr>
<tr><td><b>Aktif çevrim</b></td><td>Pasif çevrimlerden sonraki çevrimler;
k-eff ve tally sonuçları yalnızca bunlardan hesaplanır.</td></tr>
<tr><td><b>Shannon entropisi</b></td><td>Kaynak dağılımının ne kadar yayıldığını
ölçer. Pasif çevrimler boyunca düzleşmelidir; hâlâ kayıyorsa pasif çevrim
sayısı yetersizdir ve k-eff <b>yanlı</b> çıkar.</td></tr>
<tr><td><b>Tally (ölçüm)</b></td><td>Sayaç. Modelin belirli bir yerinde/enerjisinde
hangi reaksiyonların kaç kez olduğunu toplar (akı, fisyon, soğurma…).</td></tr>
<tr><td><b>k-eff ve k&infin;</b></td><td>Çoğaltma katsayısı. Bütün dış sınırlar
yansıtıcı (sızıntısız) ise sonuç <b>k&infin;</b>'dur: sonsuz tekrarlanan ortamın
katsayısı. k&infin; &gt; 1 reaktörün süperkritik olduğunu değil, yakıtın reaktivite
fazlası taşıdığını söyler; sonlu bir korda sızıntı yüzünden k-eff daha küçüktür.</td></tr>
<tr><td><b>Sabit kaynak</b></td><td>Fisyon zinciri yerine dışarıdan verilen bir
kaynağın (ör. D-T füzyon, 14.1 MeV) nötronları izlenir; k-eff tanımsızdır. Kaynak
şiddeti [1/s] girilirse sonuçlar mutlak birimdedir (OpenMC şiddeti kendisi uygular).</td></tr>
<tr><td><b>Akı (flux)</b></td><td>OpenMC'nin akı tally'si hücre hacmi üzerinden
integrallidir: birimi n&middot;cm/s (ya da kaynak nötronu başına n&middot;cm).
Ortalama akı [n/cm²/s] için bölgenin hacmine bölün. Arayüz <b>doz</b> hesaplamaz;
doz için akı–doz dönüşüm katsayıları (ör. ICRP-116) gerekir.</td></tr>
<tr><td><b>F<sub>&Delta;H</sub> ve F<sub>q</sub></b></td><td>Güç tepe faktörleri:
en yüksek çubuk gücü / ortalama (radyal) ve en yüksek yerel güç yoğunluğu / ortalama
(3B). Az parçacıkla F<sub>&Delta;H</sub> istatistik gürültüsüyle <b>yukarı</b>
yanlıdır; güvenilir değer için Normal ya da Hassas hassasiyet kullanın.</td></tr>
<tr><td><b>S(&alpha;,&beta;)</b></td><td>Termal saçılma verisi. Düşük enerjide
nötron serbest bir çekirdekten değil, <b>bağlı</b> bir molekülden saçılır (sudaki
hidrojen gibi). Unutulursa termal reaktörde k yüzde mertebesinde kayar.</td></tr>
</table>

<h3>Geometri terimleri</h3>
<table cellpadding="5">
<tr><td><b>Çubuk (pin, rod)</b></td><td>Eş merkezli bölgelerden oluşan
yakıt, kontrol ya da boş kanal çubuğu: yakıt, yakıt-zarf aralığı, zarf ve
çevresindeki soğutucu.</td></tr>
<tr><td><b>Plaka elemanı</b></td><td>Araştırma reaktörlerindeki (MTR) düz
plakalı yakıt elemanı.</td></tr>
<tr><td><b>Demet (fuel assembly)</b></td><td>Çubukların kare ya da altıgen
ızgarada düzenli dizilimi (OpenMC'de kafes, <i>lattice</i>). Kare (PWR) ya da
altıgen (VVER, SFR).</td></tr>
<tr><td><b>Kor ve kor haritası</b></td><td>Demetlerin yerleşimi. Kor haritası
her konuma hangi demetin geldiğini gösterir.</td></tr>
<tr><td><b>Yansıtıcı kuşak (reflector)</b></td><td>Koru saran, kaçan
nötronları geri gönderen malzeme katmanı.</td></tr>
<tr><td><b>Kontrol tamburu</b></td><td>Yansıtıcı kuşağa gömülü, bir yüzü emici
kaplı dönen silindir. Emici kora döndükçe reaktivite düşer.</td></tr>
<tr><td><b>Eksenel katman</b></td><td>Koru yükseklik boyunca bölen katmanlar
(alt/üst yansıtıcı, örtü, farklı zenginlikte yakıt).</td></tr>
<tr><td><b>Adım (pitch)</b></td><td>Komşu iki hücre merkezi arası mesafe.</td></tr>
<tr><td><b>Universe</b></td><td>OpenMC'de tekrar kullanılabilir geometri
parçası. Her çubuk bir universe'tür; demet onu tekrarlar.</td></tr>
<tr><td><b>Sınır koşulu</b></td><td><b>Vakum (vacuum)</b>: nötron kaçar
(gerçek dış yüzey). <b>Yansıtıcı (reflective)</b>: aynadaki gibi geri yansır
(sonsuz tekrar varsayımı). <b>Beyaz (white)</b>: rastgele yönde geri döner.
<b>Periyodik (periodic)</b>: karşı yüzden geri girer.</td></tr>
</table>

<h3>Tükenme terimleri</h3>
<table cellpadding="5">
<tr><td><b>Tükenme (depletion)</b></td><td>Yakıttaki nüklidlerin zamanla
değişmesi: fisil çekirdekler azalır, fisyon ürünleri ve aktinitler birikir.</td></tr>
<tr><td><b>Yanma (burnup)</b></td><td>Birim ağır metal kütlesi başına üretilen
enerji [MWd/kg].</td></tr>
<tr><td><b>Zincir (chain)</b></td><td>Bozunma ve reaksiyon yollarını tanımlayan
veri dosyası; termal ve hızlı spektrum için ayrı zincirler vardır.</td></tr>
<tr><td><b>Güç yoğunluğu</b></td><td>Ağır metal gramı başına güç [W/gHM].</td></tr>
</table>
"""


# ============================================================================
# bulgu acilir listesi (durum cubugu rozeti)
# ============================================================================

class _BulguAcilir(QtWidgets.QFrame):
    """Rozete tiklayinca acilan bulgu listesi; satir ilgili sekmeye goturur."""

    def __init__(self, parent=None):
        super().__init__(parent, QtCore.Qt.Popup)
        self.setObjectName("bulguAcilir")
        self.liste = QtWidgets.QListWidget()
        self.liste.setAlternatingRowColors(True)
        self.liste.setWordWrap(True)
        self.liste.setResizeMode(QtWidgets.QListView.Adjust)
        self.baslik = QtWidgets.QLabel("Doğrulama bulguları")
        f = self.baslik.font()
        f.setBold(True)
        self.baslik.setFont(f)
        ipucu = QtWidgets.QLabel("Bir satıra tıklayınca ilgili sekmeye gider.")
        ipucu.setObjectName("soluk")
        d = QtWidgets.QVBoxLayout(self)
        d.setContentsMargins(10, 8, 10, 10)
        d.addWidget(self.baslik)
        d.addWidget(ipucu)
        d.addWidget(self.liste, 1)

    def goster(self, capa):
        """capa widget'inin ustunde, sag kenara hizali acar."""
        n = max(1, self.liste.count())
        self.resize(620, min(380, 90 + n * 30))
        sag_ust = capa.mapToGlobal(QtCore.QPoint(capa.width(), 0))
        self.move(sag_ust.x() - self.width(), sag_ust.y() - self.height() - 4)
        self.show()
        self.liste.setFocus()


# ============================================================================
# ana pencere
# ============================================================================

class AnaPencere(QtWidgets.QMainWindow):

    def __init__(self, acilis_dosyasi=None):
        super().__init__()
        # Fare tekerlegi odaksiz kutulari degistirmesin (bkz. ortak.py).
        tekerlek_korumasi_kur()
        self.setWindowTitle(UYGULAMA_ADI)
        # Boyut EKRANA gore belirlenir; sabit bir deger kucuk ekranlarda
        # pencerenin bir kismini ekran disinda birakiyordu.
        ekran = QtWidgets.QApplication.primaryScreen()
        alan = ekran.availableGeometry() if ekran else QtCore.QRect(0, 0, 1280, 800)
        self.resize(min(1600, int(alan.width() * 0.92)),
                    min(1000, int(alan.height() * 0.92)))
        self.setMinimumSize(900, 560)

        self.ayarlar = QtCore.QSettings("openmc_arayuz", "arayuz")
        self.spec = sema.yeni_spec("yeni model")
        self.proje_yolu = None
        # Kopyasi acilmis ornek dosyasi. YALNIZCA OKUMA icin (tukenme
        # sekmesinin onceki sonuclari); kayit asla buraya yapilmaz.
        self.ornek_kaynagi = None
        self._kirli = False
        self._bulgular = []
        self._kirli_sekmeler = set()
        self._gecmis = []
        self._gecmis_ix = -1
        self._gecmis_yaziyor = False
        self._model_var = False          # baslangic ekraninda "modele don" gorunsun mu
        self._tur_hafizasi = {}          # kor turu degisiminde eski turun alanlari
        self._adlar = {}                 # model_adlari: hafizayi ad degisimine uydurmak icin
        self._isaretler = {}

        # ---------------- editor sekmeleri ----------------
        self.sekmeler = QtWidgets.QTabWidget()
        self.sekmeler.setDocumentMode(True)
        self.sekmeler.setUsesScrollButtons(True)
        self.s_malzeme = MalzemeSekmesi()
        self.s_cubuk = CubukSekmesi()
        self.s_demet = DemetSekmesi()
        self.s_kor = KorSekmesi()
        self.s_ayar = AyarSekmesi()
        self.s_calistir = CalistirSekmesi()
        self.s_analiz = AnalizSekmesi()
        self.s_tukenme = TukenmeSekmesi()

        # Tukenme sekmesi hem EDITOR (spec'in "tukenme" bolumunu yazar) hem de
        # kosu baslatir; bu yuzden editorler listesinde ve kapi/proje yolu alir.
        self.editorler = [self.s_malzeme, self.s_cubuk, self.s_demet,
                          self.s_kor, self.s_ayar, self.s_tukenme]
        # Her sekme bir kaydirma alanina sarilir.
        #
        # SEBEP: QTabWidget'in minimum yuksekligi TUM sayfalarin en buyugudur.
        # Ayarlar sekmesi buyudukce pencerenin minimumu 1317 px'e cikmisti;
        # ekranda 1048 px oldugu icin pencere tam ekran yapilamiyor ve ALT
        # KISMI HIC GORUNMUYORDU. Kaydirma alani bu bagi koparir.
        self._sayfa_editor = {}
        self._sekme_ix = {}
        editor_sirasi = {EDITOR_ANAHTARI[ad]: getattr(self, ad) for ad in EDITOR_ANAHTARI}
        for anahtar in uygunluk.SEKMELER:
            w = editor_sirasi[anahtar]
            kaydirma = QtWidgets.QScrollArea()
            kaydirma.setWidgetResizable(True)
            kaydirma.setFrameShape(QtWidgets.QFrame.NoFrame)
            kaydirma.setWidget(w)
            self._sayfa_editor[kaydirma] = w
            self._sekme_ix[anahtar] = self.sekmeler.addTab(kaydirma, SEKME_ADLARI[anahtar])
        for e in self.editorler:
            e.degisti.connect(self._degisti)
        self.sekmeler.currentChanged.connect(self._sekme_degisti)
        self._konu_sekme = {e.KONU: e for e in self.editorler}

        # ---------------- onizleme ----------------
        self.onizleme = OnizlemeWidget()
        self.onizleme.durum.connect(self._onizleme_durum)
        self.onizleme.olcu_bulundu.connect(lambda *_: self._ozet_guncelle())
        # matplotlib gezinme cubugu 24 px simgelerle ~51 px yer kapliyordu;
        # kucuk ekranda pencere minimumunu buyuten en buyuk kalem buydu.
        self.onizleme.arac_cubugu.setIconSize(QtCore.QSize(18, 18))

        # ---------------- dogrulama paneli ----------------
        self.dogrulama = QtWidgets.QListWidget()
        self.dogrulama.setAlternatingRowColors(True)
        self.dogrulama.setToolTip("Bir satıra tıklayınca ilgili sekmeye gider.")
        # Kucuk ekranda pencerenin minimum yuksekligini sismesin (bkz. test_kabuk).
        self.dogrulama.setMinimumHeight(40)
        # Uzun bulgu metni yatay kaydirma yerine satir kaydirsin.
        self.dogrulama.setWordWrap(True)
        self.dogrulama.setResizeMode(QtWidgets.QListView.Adjust)
        self.dogrulama.itemActivated.connect(self._bulguya_git)
        self.dogrulama.itemClicked.connect(self._bulguya_git)
        self.dogrulama_ozet = DurumRozeti("-", "notr")
        dg = QtWidgets.QWidget()
        dgd = QtWidgets.QVBoxLayout(dg)
        dgd.setContentsMargins(6, 4, 6, 4)
        dgd.setSpacing(4)
        ust = QtWidgets.QHBoxLayout()
        e = QtWidgets.QLabel("Doğrulama")
        f = e.font()
        f.setBold(True)
        e.setFont(f)
        ust.addWidget(e)
        ust.addWidget(self.dogrulama_ozet)
        ust.addStretch(1)
        d_yenile = QtWidgets.QToolButton()
        d_yenile.setText("Veri kütüphanesini de denetle")
        d_yenile.setAutoRaise(True)
        d_yenile.setToolTip("Modelin istediği her nüklidin cross_sections.xml "
                            "içinde bulunup bulunmadığını denetler (yavaş, F5).")
        d_yenile.clicked.connect(lambda: self._dogrula(veri=True))
        ust.addWidget(d_yenile)
        dgd.addLayout(ust)
        dgd.addWidget(self.dogrulama)
        self._dogrulama_kutu = dg

        # ---------------- yerlesim ----------------
        sag = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        sag.addWidget(self.onizleme)
        sag.addWidget(dg)
        sag.setStretchFactor(0, 3)
        sag.setStretchFactor(1, 1)
        sag.setChildrenCollapsible(False)
        self._sag = sag

        bolucu = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        bolucu.addWidget(self.sekmeler)
        bolucu.addWidget(sag)
        # Sekme tarafi daha genis: ayarlar sekmesi iki sutunlu ve dar kalinca
        # yatay kaydirma cubugu cikiyordu.
        bolucu.setStretchFactor(0, 5)
        bolucu.setStretchFactor(1, 3)
        bolucu.setSizes([1150, 700])
        bolucu.setChildrenCollapsible(False)
        self._bolucu = bolucu

        # Model basligi seridi (arac cubugunun altinda)
        self.model_seridi = QtWidgets.QWidget()
        self.model_seridi.setObjectName("modelSeridi")
        self.model_seridi.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.model_basligi = QtWidgets.QLabel("")
        self.model_basligi.setTextFormat(QtCore.Qt.RichText)
        self.model_basligi.setTextInteractionFlags(
            QtCore.Qt.LinksAccessibleByMouse | QtCore.Qt.LinksAccessibleByKeyboard)
        self.model_basligi.linkActivated.connect(self._baslik_baglantisi)
        self.model_olcu = QtWidgets.QLabel("")
        self.model_olcu.setObjectName("soluk")
        self.d_tur = QtWidgets.QToolButton()
        self.d_tur.setText("Türü değiştir…")
        self.d_tur.setToolTip("Kor türünü değiştirir (yalnızca bu modelde "
                              "kullanılabilen türler listelenir). Geri almak için Ctrl+Z.")
        self._tur_menusu = QtWidgets.QMenu(self)
        self._tur_menusu.aboutToShow.connect(self._tur_menusunu_doldur)
        self.d_tur.setMenu(self._tur_menusu)
        self.d_tur.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        sd = QtWidgets.QHBoxLayout(self.model_seridi)
        sd.setContentsMargins(12, 2, 6, 2)
        sd.setSpacing(12)
        sd.addWidget(self.model_basligi, 1)
        sd.addWidget(self.model_olcu)
        sd.addWidget(self.d_tur)

        editor = QtWidgets.QWidget()
        md = QtWidgets.QVBoxLayout(editor)
        md.setContentsMargins(0, 0, 0, 0)
        md.setSpacing(0)
        md.addWidget(self.model_seridi)
        md.addWidget(bolucu, 1)
        self._editor = editor

        # Baslangic ekrani + editor: ayni pencerede, modal degil.
        self.baslangic = baslangic.BaslangicEkrani()
        self.baslangic.bos_istendi.connect(self._bos_basla)
        self.baslangic.ornek_istendi.connect(self.proje_ac)
        self.baslangic.dosya_istendi.connect(self.proje_ac)
        self.baslangic.ac_istendi.connect(self._ac_diyalog)
        self.baslangic.geri_istendi.connect(self._editoru_goster)
        self.yigin = QtWidgets.QStackedWidget()
        self.yigin.addWidget(self.baslangic)
        self.yigin.addWidget(editor)
        self.setCentralWidget(self.yigin)

        self._menu_kur()
        self._arac_cubugu_kur()
        self._durum_cubugu_kur()

        self.s_calistir.kapi_ayarla(self._kosu_izni)
        self.s_analiz.kapi_ayarla(self._kosu_izni)
        self.s_tukenme.kapi_ayarla(self._kosu_izni)
        for s in (self.s_calistir, self.s_analiz, self.s_tukenme):
            s.durum.connect(self._sekme_durum_mesaji)
            s.sonuc_degisti.connect(self._isaretleri_guncelle)
        # Is parcacigi ve kosu dizini Calistir'da duzenlenir (konu "calistirma"):
        # proje kirlenir, geri alinabilir.
        self.s_calistir.degisti.connect(self._degisti)
        self.s_kor.tur_degistir_istendi.connect(self._tur_menusunu_ac)

        self._dog_sayac = QtCore.QTimer(self); self._dog_sayac.setSingleShot(True)
        self._dog_sayac.setInterval(250)
        self._dog_sayac.timeout.connect(lambda: self._dogrula(veri=False))

        self._gecmis_sayac = QtCore.QTimer(self); self._gecmis_sayac.setSingleShot(True)
        self._gecmis_sayac.setInterval(700)
        self._gecmis_sayac.timeout.connect(self._gecmise_it)

        self._spec_uygula()
        self._gecmise_it(ilk=True)
        if acilis_dosyasi:
            self.proje_ac(acilis_dosyasi)
        if not self._model_var:
            self.baslangici_goster()

    # ==================================================================
    # menu / arac cubugu / durum cubugu
    # ==================================================================
    def _menu_kur(self):
        m_dosya = self.menuBar().addMenu("&Dosya")
        m_dosya.setToolTipsVisible(True)
        self.e_yeni = self._eylem(m_dosya, "Yeni…", self.proje_yeni,
                                  QtGui.QKeySequence.New,
                                  "Başlangıç ekranı: ne modelleyeceğini seç")
        self.e_ac = self._eylem(m_dosya, "Aç…", self._ac_diyalog, QtGui.QKeySequence.Open,
                                "Bir model dosyası (.json) aç")
        self.m_son = m_dosya.addMenu("Son kullanılanlar")
        m_dosya.addSeparator()
        self.e_kaydet = self._eylem(m_dosya, "Kaydet", self.proje_kaydet,
                                    QtGui.QKeySequence.Save)
        self.e_farkli = self._eylem(m_dosya, "Farklı kaydet…", self.proje_farkli_kaydet,
                                    QtGui.QKeySequence.SaveAs)
        m_dosya.addSeparator()
        self.e_ice_aktar = self._eylem(m_dosya, "Malzemeleri içe aktar (OpenMC XML)…",
                                       self.malzeme_ice_aktar, None, _ICE_AKTAR_NOTU)
        self.e_betik = self._eylem(m_dosya, "Python betiği olarak dışa aktar…",
                                   self.betik_disa_aktar, "Ctrl+E",
                                   "Tek başına çalışan bir Python betiği üretir")
        self.e_xml = self._eylem(m_dosya, "OpenMC XML olarak dışa aktar…", self.xml_disa_aktar)
        self.e_png = self._eylem(m_dosya, "Önizlemeyi PNG olarak kaydet…", self.png_kaydet)
        m_dosya.addSeparator()
        self._eylem(m_dosya, "Çıkış", self.close, QtGui.QKeySequence.Quit)

        m_duzen = self.menuBar().addMenu("D&üzen")
        self.e_geri = self._eylem(m_duzen, "Geri al", self.geri_al, QtGui.QKeySequence.Undo)
        self.e_yinele = self._eylem(m_duzen, "Yinele", self.yinele, QtGui.QKeySequence.Redo)

        m_gorunum = self.menuBar().addMenu("&Görünüm")
        self._tema_eylemleri = {}
        grup = QtGui.QActionGroup(self)
        grup.setExclusive(True)
        for anahtar, bilgi in tema.TEMALAR.items():
            e = QtGui.QAction("%s tema" % bilgi["ad"], self)
            e.setCheckable(True)
            e.setChecked(anahtar == tema.etkin())
            e.triggered.connect(lambda _c=False, a=anahtar: self._tema_degistir(a))
            grup.addAction(e)
            m_gorunum.addAction(e)
            self._tema_eylemleri[anahtar] = e
        m_gorunum.addSeparator()
        self._eylem(m_gorunum, "Tam ekran", self._tam_ekran, "F11")

        m_yardim = self.menuBar().addMenu("&Yardım")
        self._eylem(m_yardim, "Yardım ve terimler", self._yardim, "F1")
        self._eylem(m_yardim, "Hakkında", self._hakkinda)

        # Menude olmayan pencere kisayollari (eski Model menusu).
        self.e_dogrula = self._pencere_eylemi(
            "Doğrulamayı yenile (veri kütüphanesi dahil)",
            lambda: self._dogrula(veri=True), "F5")
        self.e_onizle = self._pencere_eylemi(
            "Önizlemeyi yenile", self.onizleme._ciz, "F6")
        self.e_calistir = self._pencere_eylemi(
            "ÇALIŞTIR", self._calistir_menuden, "F9")
        self.e_calistir.setToolTip("Modeli çalıştır (F9) — önce geometri çizilmiş ve "
                                   "doğrulama hatasız olmalı")
        # Baslangic ekraninda anlamsiz eylemler (acik model yok ya da gizli).
        self._model_eylemleri = [self.e_kaydet, self.e_farkli, self.e_ice_aktar,
                                 self.e_betik, self.e_xml, self.e_png,
                                 self.e_dogrula, self.e_onizle, self.e_calistir]
        self._son_menusu_yenile()

    def _pencere_eylemi(self, ad, islev, kisayol):
        e = QtGui.QAction(ad, self)
        e.setShortcut(kisayol)
        e.setShortcutContext(QtCore.Qt.WindowShortcut)
        e.triggered.connect(lambda _c=False: islev())
        self.addAction(e)
        return e

    def _arac_cubugu_kur(self):
        cubuk = QtWidgets.QToolBar("Ana")
        cubuk.setObjectName("anaAracCubugu")
        # Simge yok: TextBesideIcon 24 px simge yuksekligi ayiriyor, pencere
        # minimumunu bosuna buyutuyordu.
        cubuk.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        cubuk.setMovable(False)
        for e in (self.e_yeni, self.e_ac, self.e_kaydet):
            cubuk.addAction(e)
        cubuk.addSeparator()
        for e in (self.e_geri, self.e_yinele):
            cubuk.addAction(e)
        cubuk.addSeparator()
        cubuk.addAction(self.e_calistir)
        calistir = cubuk.widgetForAction(self.e_calistir)
        if calistir is not None:
            calistir.setObjectName("calistirDugmesi")
        self.addToolBar(cubuk)
        self._arac_cubugu = cubuk

    def _durum_cubugu_kur(self):
        # Sonraki adim ipucu: "normal" durum cubugu bileseni -- gecici
        # mesajlar (onizleme, kayit...) onu kisa sure ortup geri birakir.
        self.durum_ipucu = QtWidgets.QLabel("")
        self.durum_ipucu.setObjectName("soluk")
        self.statusBar().addWidget(self.durum_ipucu, 1)
        self.durum_rozeti = DurumRozeti("", "notr", tiklanabilir=True)
        self.durum_rozeti.setToolTip("Doğrulama bulgularını göster")
        self.durum_rozeti.tiklandi.connect(self._bulgu_listesini_ac)
        self.statusBar().addPermanentWidget(self.durum_rozeti)
        self.bulgu_acilir = _BulguAcilir(self)
        self.bulgu_acilir.liste.itemClicked.connect(self._acilirdan_git)
        self.bulgu_acilir.liste.itemActivated.connect(self._acilirdan_git)

    def _eylem(self, menu, ad, islev, kisayol=None, ipucu=None):
        e = QtGui.QAction(ad, self)
        e.triggered.connect(lambda _c=False: islev())
        if kisayol:
            e.setShortcut(kisayol)
        if ipucu:
            e.setToolTip(ipucu)
            e.setStatusTip(ipucu)
        menu.addAction(e)
        return e

    def _tema_degistir(self, ad):
        """Temayi degistirir ve renge bagli panelleri tazeler."""
        tema.uygula(QtWidgets.QApplication.instance(), ad)
        for anahtar, e in self._tema_eylemleri.items():
            e.setChecked(anahtar == ad)
        self._dogrula(veri=False)          # seviye renkleri, rozetler
        self._ozet_guncelle()              # baslik baglanti rengi
        self.onizleme._ciz()               # grafik paleti
        self.statusBar().showMessage("Tema: %s" % tema.TEMALAR[ad]["ad"], 4000)

    def _tam_ekran(self):
        """F11 -- tam ekran ac/kapa."""
        if self.isFullScreen():
            self.setWindowState(self.windowState() & ~QtCore.Qt.WindowFullScreen)
        else:
            self.setWindowState(self.windowState() | QtCore.Qt.WindowFullScreen)

    def _kisayol_html(self):
        """Kisayol tablosu -- eylemlerin GERCEK kisayollarindan uretilir."""
        satirlar = [
            (self.e_yeni, "Yeni model (başlangıç ekranı)"), (self.e_ac, "Aç"),
            (self.e_kaydet, "Kaydet"), (self.e_farkli, "Farklı kaydet"),
            (self.e_geri, "Geri al"), (self.e_yinele, "Yinele"),
            (self.e_betik, "Python betiği olarak dışa aktar"),
            (self.e_dogrula, "Doğrulamayı yenile (veri kütüphanesi dahil)"),
            (self.e_onizle, "Önizlemeyi yenile"), (self.e_calistir, "ÇALIŞTIR"),
        ]
        html = ["<h3>Klavye kısayolları</h3><table cellpadding='4'>"]
        for e, aciklama in satirlar:
            tus = e.shortcut().toString(QtGui.QKeySequence.NativeText)
            if tus:
                html.append("<tr><td><b>%s</b></td><td>%s</td></tr>" % (tus, aciklama))
        html.append("<tr><td><b>F1</b></td><td>Bu yardım</td></tr>"
                    "<tr><td><b>F11</b></td><td>Tam ekran</td></tr>"
                    "<tr><td><b>Esc</b></td><td>Başlangıç ekranında: açık modele dön</td></tr>"
                    "</table><p>Demet ve kor haritasında sol tık boyar, sağ tık o hücrenin "
                    "parçasını fırça yapar; altıgen haritada tekerlek yakınlaştırır.</p>")
        return "".join(html)

    def _yardim_diyalogu(self):
        """Yardim diyalogunu KURAR (gostermez) -- testler exec() cagirmadan inceler."""
        d = QtWidgets.QDialog(self)
        d.setWindowTitle("Yardım ve terimler")
        d.resize(760, 640)
        metin = QtWidgets.QTextBrowser()
        metin.setOpenExternalLinks(False)
        metin.setHtml(YARDIM_HTML + self._kisayol_html())
        kutu = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        kutu.button(QtWidgets.QDialogButtonBox.Close).setText("Kapat")
        kutu.rejected.connect(d.reject)
        duzen = QtWidgets.QVBoxLayout(d)
        duzen.addWidget(metin)
        duzen.addWidget(kutu)
        d.metin = metin
        return d

    def _yardim(self):
        """Ogrenciye yonelik yardim: terim sozlugu + kisayollar (F1)."""
        self._yardim_diyalogu().exec()

    def _hakkinda(self):
        QtWidgets.QMessageBox.information(
            self, "Hakkında",
            "%s\n\n"
            "Model tanımı JSON 'spec' olarak tutulur; ondan hem openmc.Model\n"
            "hem de tek başına çalışan Python betiği üretilir.\n\n"
            "Arayüz bir çıkmaz sokak değildir: Dosya > Python betiği olarak\n"
            "dışa aktar (Ctrl+E) ile modeli alıp elle düzenlemeye devam\n"
            "edebilirsiniz." % UYGULAMA_ADI)

    # ==================================================================
    # baslangic ekrani
    # ==================================================================
    def baslangic_acik_mi(self):
        return self.yigin.currentWidget() is self.baslangic

    def baslangici_goster(self):
        """"Ne modelliyorsun?" ekranini gosterir (Dosya > Yeni, acilis)."""
        self.baslangic.son_dosyalari_ayarla(self._son_listesi())
        self.baslangic.geri_gorunur(self._model_var)
        self.yigin.setCurrentWidget(self.baslangic)
        # Baslangic ekraninda dogrulama rozeti anlamsiz (bos model "hata" sayardi).
        self.durum_rozeti.setVisible(False)
        self._model_eylemleri_guncelle()
        self.baslangic.setFocus()
        self.durum_ipucu.setText("Başlamak için bir model türü seçin.")

    def _editoru_goster(self):
        self.yigin.setCurrentWidget(self._editor)
        self.durum_rozeti.setVisible(True)
        self._model_eylemleri_guncelle()
        self._durum_ipucu_guncelle()

    def _model_eylemleri_guncelle(self):
        editorde = not self.baslangic_acik_mi()
        for e in self._model_eylemleri:
            e.setEnabled(editorde)
        self._baslik_guncelle()

    def _bos_basla(self, anahtar):
        """Kart: 'Bos basla' -- o turun sade, calisan sablonu."""
        if not self._kaydetme_sor():
            return False
        try:
            spec = baslangic.bos_sablon(anahtar)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Şablon kurulamadı", str(e))
            return False
        self._proje_kur(spec, proje_yolu=None, ornek_kaynagi=None)
        kart = baslangic.kart(anahtar)
        self._sekmeye_git(kart.get("sekme") or "malzemeler", sessiz=True)
        self.statusBar().showMessage(
            "Çalışan sade bir model kuruldu (%s). Kaydetmek için 'Farklı kaydet' "
            "kullanın." % kart["baslik"], 8000)
        return True

    # ==================================================================
    # spec yasam dongusu
    # ==================================================================
    def _proje_degisti(self):
        """
        PROJE degisti (yeni / ac / ornek / sablon): onceki projenin SONUCLARI
        silinir. Sekme degisiminde ve geri al/yinele'de CAGRILMAZ -- orada ayni
        projedeyiz. Eskiden Calistir/Analiz yeni projede eski k-eff'i ve
        katsayiyi gosteriyordu.
        """
        self.s_calistir.sifirla()
        self.s_analiz.sifirla()
        self.s_tukenme.sifirla()

    def _proje_kur(self, spec, proje_yolu, ornek_kaynagi):
        """Yeni bir projeyi pencereye yukler (ac / ornek / bos sablon)."""
        self._proje_degisti()
        self.spec = spec
        self.proje_yolu = proje_yolu
        self.ornek_kaynagi = ornek_kaynagi
        self._kirli = False
        self._tur_hafizasi = {}
        self._gecmis, self._gecmis_ix = [], -1
        self._spec_uygula()
        self._gecmise_it(ilk=True)
        self._model_var = True
        self._editoru_goster()

    def _spec_uygula(self):
        """Spec bastan yuklendi -- tum sekmeleri tazele."""
        self._hafizayi_esitle()
        self.s_tukenme.proje_ayarla(self.proje_yolu, self.ornek_kaynagi)
        for e in self.editorler:
            e.spec_yukle(self.spec)
        self._kirli_sekmeler.clear()
        self.onizleme.spec_ayarla(self.spec)
        self.s_calistir.spec_ayarla(self.spec, self.proje_yolu)
        self.s_analiz.spec_ayarla(self.spec, self.proje_yolu)
        self._sekme_gorunurlugu()
        self._dogrula(veri=False)
        self._baslik_guncelle()
        self._ozet_guncelle()

    def _degisti(self, konu="genel"):
        """
        Bir editor sekmesi spec'i degistirdi.

        Yalnizca konuya BAGIMLI sekmeler kirli isaretlenir, onlar da ancak
        acildiklarinda yenilenir (olculen: tum sekmeleri kurmak 34 ms idi ve
        gorunmeyen sekmelerin secimi sifirlaniyordu).
        """
        self._kirli = True
        self._hafizayi_esitle()
        bagimli_konular = _KONU_BAGIMLILIK.get(konu, set())
        gorunur = self._gorunur_editor()
        for k in bagimli_konular:
            e = self._konu_sekme.get(k)
            if e is None:
                continue
            if e is gorunur:
                e.spec_yukle(self.spec)
                self._kirli_sekmeler.discard(e)
            else:
                self._kirli_sekmeler.add(e)

        if konu != "calistirma":
            # Is parcacigi / kosu dizini geometriyi degistirmez; onizleme
            # onbellek anahtari tum spec'i kapsadigi icin bosuna yeniden cizerdi.
            self.onizleme.iste()
        self._dog_sayac.start()
        self._gecmis_sayac.start()
        self._sekme_gorunurlugu()
        self._baslik_guncelle()
        self._ozet_guncelle()
        self._isaretleri_guncelle()

    def _hafizayi_esitle(self):
        """Malzeme/parca adi degistiyse ya da silindiyse tur hafizasini uydur."""
        simdiki = model_adlari(self.spec)
        if self._adlar:
            tur_hafizasini_esitle(self._tur_hafizasi, self._adlar, simdiki)
        self._adlar = simdiki

    def _gorunur_editor(self):
        """Etkin sekmenin ICINDEKI editoru dondurur (kaydirma alanini asar)."""
        return self._sayfa_editor.get(self.sekmeler.currentWidget())

    def _sekme_degisti(self, indeks):
        self._sag_panel_guncelle()
        self._sekme_renkleri()
        w = self._sayfa_editor.get(self.sekmeler.widget(indeks))
        if w is None:
            return
        if w in self._kirli_sekmeler:
            w.spec_yukle(self.spec)
            self._kirli_sekmeler.discard(w)
        if w is self.s_calistir:
            self.s_calistir.spec_ayarla(self.spec, self.proje_yolu)
        elif w is self.s_analiz:
            self.s_analiz.spec_ayarla(self.spec, self.proje_yolu)

    # ==================================================================
    # sekmeler: gorunurluk, isaretler, sag panel
    # ==================================================================
    def _gecerli_sekmeler(self):
        try:
            return list(uygunluk.gecerli_sekmeler(self.spec))
        except Exception:
            return list(uygunluk.SEKMELER)     # bozuk spec: hicbir seyi gizleme

    def _sekme_anahtari(self, indeks=None):
        indeks = self.sekmeler.currentIndex() if indeks is None else indeks
        for anahtar, i in self._sekme_ix.items():
            if i == indeks:
                return anahtar
        return None

    def _sekme_gorunurlugu(self):
        """Yalnizca modele uyan sekmeler gorunur; etkin sekme gizlenirse ilk
        gorunur sekmeye gecilir (Qt kendiliginden komsuya atliyordu)."""
        gorunur = self._gecerli_sekmeler()
        simdiki = self._sekme_anahtari()
        if gorunur and simdiki not in gorunur:
            self.sekmeler.setCurrentIndex(self._sekme_ix[gorunur[0]])
        for anahtar, i in self._sekme_ix.items():
            acik = anahtar in gorunur
            if self.sekmeler.isTabVisible(i) != acik:
                self.sekmeler.setTabVisible(i, acik)
        self._sag_panel_guncelle()

    def _sekmeye_git(self, anahtar, sessiz=False):
        """Sekmeye gecer; sekme bu modelde gizliyse gecmez (False)."""
        i = self._sekme_ix.get(anahtar)
        if i is None:
            return False
        if not self.sekmeler.isTabVisible(i):
            if not sessiz:
                self.statusBar().showMessage(
                    "%s sekmesi bu model türünde kullanılmıyor." % SEKME_ADLARI[anahtar], 6000)
            return False
        self.sekmeler.setCurrentIndex(i)
        return True

    def _isaretleri_guncelle(self):
        """Sekme basliklarindaki ! • ✓ isaretleri ve ipuclari."""
        hata = {}
        for b in self._bulgular:
            if b.seviye == "hata":
                k = yer_sekme_anahtari(b.yer)
                if k:
                    hata[k] = hata.get(k, 0) + 1
        self._isaretler = sekme_isaretleri(
            self.spec, hata,
            kosu_basarili=self.s_calistir.sonuc_var(),
            analiz_sonucu=self.s_analiz.sonuc_var(),
            tukenme_sonucu=self.s_tukenme.sonuc_var())
        for anahtar, i in self._sekme_ix.items():
            isaret, aciklama = self._isaretler.get(anahtar, ("", ""))
            ad = SEKME_ADLARI[anahtar]
            metin = "%s  %s" % (ad, isaret) if isaret else ad
            if self.sekmeler.tabText(i) != metin:
                self.sekmeler.setTabText(i, metin)
            self.sekmeler.setTabToolTip(i, aciklama)
        self._sekme_renkleri()
        self._durum_ipucu_guncelle()

    def _sekme_renkleri(self):
        """Hatali sekmenin basligi kirmizi; digerleri secili: vurgu, degil: soluk.
        (Isaretin kendisi baslik metnindedir; renk yalnizca HATAYI one cikarir.)"""
        cubuk = self.sekmeler.tabBar()
        simdiki = self.sekmeler.currentIndex()
        for anahtar, i in self._sekme_ix.items():
            if self._isaretler.get(anahtar, ("", ""))[0] == "!":
                renk = tema.renk("hata")
            elif i == simdiki:
                renk = tema.renk("vurgu")
            else:
                renk = tema.renk("metin_soluk")
            cubuk.setTabTextColor(i, QtGui.QColor(renk))

    def _durum_ipucu_guncelle(self):
        if self.baslangic_acik_mi():
            return
        self.durum_ipucu.setText(sonraki_adim(
            self._isaretler, self._gecerli_sekmeler(), self.onizleme.cizildi_mi()))

    def _sag_panel_guncelle(self):
        """Onizleme + dogrulama yalnizca tasarim sekmelerinde; kosu/sonuc
        sekmeleri tum genisligi kullanir."""
        anahtar = self._sekme_anahtari()
        tasarim = anahtar in TASARIM_SEKMELERI
        dogrulama = anahtar in DOGRULAMA_SEKMELERI
        kip = "tasarim" if tasarim else ("dogrulama" if dogrulama else "yok")
        onceki = getattr(self, "_sag_kip", None)
        if onceki == "tasarim" and kip != "tasarim":
            self._tasarim_boyutlari = self._bolucu.sizes()
        self.onizleme.setVisible(tasarim)
        self._dogrulama_kutu.setVisible(dogrulama)
        self._sag.setVisible(tasarim or dogrulama)
        # Yalnizca dogrulama gosterilirken (Hesap ayarlari) sag panel daralir:
        # ayar formu genislik ister; liste icin ~%28 yeter. Tasarim sekmesine
        # donunce kullanicinin ayarladigi genislik geri gelir.
        toplam = sum(self._bolucu.sizes()) or self._bolucu.width()
        if kip == "dogrulama" and onceki != "dogrulama" and toplam > 0:
            sag = max(300, int(toplam * 0.28))
            self._bolucu.setSizes([toplam - sag, sag])
        elif kip == "tasarim" and onceki not in (None, "tasarim"):
            boyut = getattr(self, "_tasarim_boyutlari", None)
            if boyut:
                self._bolucu.setSizes(boyut)
        self._sag_kip = kip

    # ==================================================================
    # model basligi ve kor turu
    # ==================================================================
    def _baslik_guncelle(self):
        if self.proje_yolu:
            ad = os.path.basename(self.proje_yolu)
        elif self.ornek_kaynagi:
            ad = "adsız — örnek: %s" % os.path.splitext(
                os.path.basename(self.ornek_kaynagi))[0]
        else:
            ad = "kaydedilmemiş"
        self.setWindowTitle("%s — %s%s" % (UYGULAMA_ADI, ad, " *" if self._kirli else ""))
        editorde = not self.baslangic_acik_mi()
        self.e_geri.setEnabled(editorde and self._gecmis_ix > 0)
        self.e_yinele.setEnabled(editorde and 0 <= self._gecmis_ix < len(self._gecmis) - 1)

    def _ozet_guncelle(self):
        """
        Model basligi. BURADA MODEL KURULMAZ -- olcu bilgisi onizlemeden gelir
        (olcu_bulundu sinyali); her degisiklikte model kurmak ~22 ms ekliyordu.
        """
        try:
            p = model_ozet_parcalari(self.spec)
        except Exception:
            p = {"ad": self.spec.get("ad", ""), "tur": "?", "boyut": "?", "mod": "?"}
        vurgu = tema.renk("vurgu")
        soluk = tema.renk("metin_soluk")
        bag = ("<a href='%%s' style='color:%s; text-decoration:none;'>%%s</a>" % vurgu)
        esc = lambda s: (str(s).replace("&", "&amp;").replace("<", "&lt;")
                         .replace(">", "&gt;"))
        ayrac = " <span style='color:%s'>·</span> " % soluk
        self.model_basligi.setText(
            "<span style='color:%s'>Model:</span> <b>%s</b>" % (soluk, esc(p["ad"]))
            + ayrac + bag % ("kor", esc(p["tur"]))
            + ayrac + bag % ("kor", esc(p["boyut"]))
            + ayrac + bag % ("mod", esc(p["mod"])))
        self.model_basligi.setToolTip(
            "Kor türüne ya da boyuta tıklayınca Kor sekmesine, hesap türüne "
            "tıklayınca Hesap ayarlarına gider.")
        olcu = self.onizleme.son_olcu
        self.model_olcu.setText("%.2f × %.2f cm" % olcu if olcu else "")

    def _baslik_baglantisi(self, hedef):
        self._sekmeye_git({"mod": "ayarlar", "kor": "kor"}.get(hedef, "kor"))

    def _tur_menusunu_ac(self):
        """Kor sekmesindeki 'Türü değiştir…' baglantisi: basliktaki menu."""
        if self.d_tur.isVisible():
            self.d_tur.showMenu()
        else:
            self._tur_menusunu_doldur()
            self._tur_menusu.exec(QtGui.QCursor.pos())

    def _tur_menusunu_doldur(self):
        self._tur_menusu.clear()
        simdiki = (self.spec.get("kor") or {}).get("tur")
        for tur in uygunluk.kor_turleri(self.spec):
            e = self._tur_menusu.addAction(TUR_ADLARI.get(tur, tur))
            e.setCheckable(True)
            e.setChecked(tur == simdiki)
            e.setData(tur)
            e.triggered.connect(lambda _c=False, t=tur: self.kor_turunu_degistir(t))

    def kor_turunu_degistir(self, tur):
        """Model basligindaki 'Turu degistir...' -- geri alinabilir tek adim."""
        if tur not in uygunluk.kor_turleri(self.spec):
            return False
        # Bekleyen duzenleme once kendi adimi olsun: geri al tur degisimini
        # onceki duzenlemeyle birlikte silmesin.
        self._gecmis_sayac.stop()
        self._gecmise_it()
        eklenen = []
        if not kor_turu_degistir(self.spec, tur, self._tur_hafizasi, eklenen):
            return False
        if self.spec.get("ad") in _SABLON_ADLARI.values() and tur in _SABLON_ADLARI:
            self.spec["ad"] = _SABLON_ADLARI[tur]
        self._kirli = True
        self._spec_uygula()
        self._gecmise_it()
        ek = (" Model bu türün gerektirdiği parçayı içermiyordu; şablondan eklendi: %s "
              "(Parçalar/Demet sekmesinde düzenleyin)." % ", ".join(eklenen)) if eklenen else ""
        self.statusBar().showMessage(
            "Kor türü: %s — geri almak için Ctrl+Z.%s" % (TUR_ADLARI.get(tur, tur), ek), 10000)
        return True

    # ==================================================================
    # geri al / yinele
    # ==================================================================
    def _gecmise_it(self, ilk=False):
        if self._gecmis_yaziyor:
            return
        anlik = copy.deepcopy(self.spec)
        if self._gecmis and self._gecmis_ix >= 0:
            if onbellek.ozet(self._gecmis[self._gecmis_ix]) == onbellek.ozet(anlik):
                return          # degisiklik yok
        del self._gecmis[self._gecmis_ix + 1:]
        self._gecmis.append(anlik)
        if len(self._gecmis) > _GECMIS_SINIR:
            self._gecmis.pop(0)
        self._gecmis_ix = len(self._gecmis) - 1
        self._baslik_guncelle()

    def _gecmisten_yukle(self, ix):
        self._gecmis_yaziyor = True
        try:
            self.spec = copy.deepcopy(self._gecmis[ix])
            self._gecmis_ix = ix
            self._spec_uygula()
            self._kirli = True
        finally:
            self._gecmis_yaziyor = False
        self._baslik_guncelle()

    def geri_al(self):
        self._gecmis_sayac.stop()
        self._gecmise_it()
        if self._gecmis_ix > 0:
            self._gecmisten_yukle(self._gecmis_ix - 1)
            self.statusBar().showMessage("Geri alındı (%d/%d)"
                                         % (self._gecmis_ix + 1, len(self._gecmis)), 3000)

    def yinele(self):
        if self._gecmis_ix < len(self._gecmis) - 1:
            self._gecmisten_yukle(self._gecmis_ix + 1)
            self.statusBar().showMessage("Yinelendi (%d/%d)"
                                         % (self._gecmis_ix + 1, len(self._gecmis)), 3000)

    # ==================================================================
    # dogrulama
    # ==================================================================
    def _bulgu_ogeleri(self, liste):
        """Bulgulari bir QListWidget'a yazar (panel ve acilir liste ayni bicim)."""
        liste.clear()
        for b in self._bulgular:
            oge = QtWidgets.QListWidgetItem(
                "%s · %s: %s" % (_SEVIYE_ADI.get(b.seviye, b.seviye), yer_etiketi(b.yer),
                                  cumle_basi(b.mesaj)))
            oge.setForeground(QtGui.QColor(_seviye_renk(b.seviye)))
            oge.setData(QtCore.Qt.UserRole, b.yer)
            # Eskiden: (ipucu + "\n\n") if ipucu else "" + "Tiklayinca..." --
            # oncelik yuzunden oneri varken tiklama bilgisi DUSUYORDU.
            tiklama = "Tıklayınca ilgili sekmeye gider."
            oge.setToolTip((b.oneri + "\n\n" + tiklama) if b.oneri else tiklama)
            liste.addItem(oge)
        if not self._bulgular:
            # Bos kutu "calismiyor mu?" sorusunu dogurur; sonucu soyle.
            oge = QtWidgets.QListWidgetItem("✓ Bulgu yok — model tutarlı görünüyor.")
            oge.setForeground(QtGui.QColor(tema.renk("basari")))
            oge.setFlags(QtCore.Qt.ItemIsEnabled)
            liste.addItem(oge)

    def _dogrula(self, veri=False):
        try:
            self._bulgular = dogrula.tum_kontroller(self.spec, veri_kontrolu=veri)
        except Exception as e:
            self._bulgular = [dogrula.Bulgu("hata", "dogrulama",
                                            "doğrulama sırasında hata: %s" % e)]
        self._bulgu_ogeleri(self.dogrulama)
        if self.bulgu_acilir.isVisible():
            self._bulgu_ogeleri(self.bulgu_acilir.liste)
        n_hata = sum(1 for b in self._bulgular if b.seviye == "hata")
        n_uyari = sum(1 for b in self._bulgular if b.seviye == "uyari")
        n_bilgi = sum(1 for b in self._bulgular if b.seviye == "bilgi")
        if n_hata or n_uyari:
            parca = (["%d hata" % n_hata] if n_hata else []) + \
                    (["%d uyarı" % n_uyari] if n_uyari else [])
            metin, seviye = " · ".join(parca), ("hata" if n_hata else "uyari")
        else:
            metin, seviye = "Hata yok", "basari"
        self.dogrulama_ozet.ayarla(metin, seviye)
        self.dogrulama_ozet.setToolTip("%d hata, %d uyarı, %d bilgi" % (n_hata, n_uyari, n_bilgi))
        self.durum_rozeti.ayarla(metin, seviye)
        self.durum_rozeti.setToolTip("%d hata, %d uyarı, %d bilgi — listeyi açmak için tıklayın"
                                     % (n_hata, n_uyari, n_bilgi))
        self.s_calistir.kapi_guncelle()
        self.s_analiz.kapi_guncelle()
        self.s_tukenme.kapi_guncelle()
        self._isaretleri_guncelle()

    def _bulgu_listesini_ac(self):
        self._bulgu_ogeleri(self.bulgu_acilir.liste)
        self.bulgu_acilir.goster(self.durum_rozeti)

    def _acilirdan_git(self, oge):
        self.bulgu_acilir.hide()
        self._bulguya_git(oge)

    def _bulguya_git(self, oge):
        """Dogrulama satirina tiklayinca ilgili sekmeyi ac."""
        anahtar = yer_sekme_anahtari(oge.data(QtCore.Qt.UserRole))
        if anahtar is not None:
            if self.baslangic_acik_mi():
                self._editoru_goster()
            self._sekmeye_git(anahtar)

    def _sekme_indeksi(self, editor):
        """Editorun (kaydirma alanina sarili) sekme indeksi; yoksa -1."""
        for kaydirma, w in self._sayfa_editor.items():
            if w is editor:
                return self.sekmeler.indexOf(kaydirma)
        return -1

    def _yer_sekmesi(self, yer):
        """Bulgunun 'yer' alanindan sekme indeksi; eslesme yoksa None."""
        anahtar = yer_sekme_anahtari(yer)
        return self._sekme_ix.get(anahtar) if anahtar else None

    def _onizleme_durum(self, mesaj, basarili):
        # Yalnizca SORUN bildirilir: her duzenlemeden sonra gelen "onizleme
        # guncel" mesaji durum cubugundaki sonraki-adim ipucunu surekli
        # ortuyordu. Baslangic ekraninda arkadaki bos modelin cizim hatasi da
        # gosterilmez.
        if not basarili and not self.baslangic_acik_mi():
            self.statusBar().showMessage(mesaj, 8000)
        self.s_calistir.kapi_guncelle()
        self.s_tukenme.kapi_guncelle()
        self._durum_ipucu_guncelle()

    def _sekme_durum_mesaji(self, mesaj, _basarili):
        """Calistir/Analiz/Tukenme bildirimi: durum cubugu + sekme isaretleri."""
        self.statusBar().showMessage(mesaj, 8000)
        self._isaretleri_guncelle()

    def _kosu_izni(self):
        """CALISTIR kapisi: once geometri cizilmeli, sonra hata olmamali."""
        if dogrula.hata_var(self._bulgular):
            n = sum(1 for b in self._bulgular if b.seviye == "hata")
            return False, ("Doğrulamada %d hata var — önce bunları giderin. Sağ "
                           "alttaki rozete tıklayıp bir bulguyu seçince ilgili "
                           "sekmeye gidersiniz." % n)
        if not self.onizleme.cizildi_mi():
            return False, ("Geometri önizlemesi henüz çizilmedi. Önce çiz, "
                           "sonra çalıştır: yanlış geometriyle saatlerce koşmamak "
                           "için önizlemenin çizilmesi bekleniyor.")
        uyari = sum(1 for b in self._bulgular if b.seviye == "uyari")
        if uyari:
            return True, ("Çalıştırılabilir. %d uyarı var — sonucu etkileyebilir, "
                          "doğrulama listesini gözden geçirin." % uyari)
        return True, "Model çalıştırılmaya hazır."

    def _calistir_menuden(self):
        if self.baslangic_acik_mi():
            return
        self._sekmeye_git("calistir")
        self.s_calistir.spec_ayarla(self.spec, self.proje_yolu)
        self.s_calistir.calistir()

    # ==================================================================
    # son kullanilanlar
    # ==================================================================
    def _son_listesi(self):
        try:
            ham = self.ayarlar.value("son_dosyalar", []) or []
        except Exception:
            ham = []
        if isinstance(ham, str):
            ham = [ham]
        # Ornekler baslangic ekraninda ayrica listelenir ve kopya olarak
        # acilir; eski surumlerden kalan ornek girdileri burada gosterilmez.
        return [y for y in ham if isinstance(y, str) and os.path.exists(y)
                and not self._ornek_mi(y)]

    def _sona_ekle(self, yol):
        liste = [os.path.abspath(yol)] + [y for y in self._son_listesi()
                                          if os.path.abspath(y) != os.path.abspath(yol)]
        self.ayarlar.setValue("son_dosyalar", liste[:10])
        self._son_menusu_yenile()

    def _son_menusu_yenile(self):
        self.m_son.clear()
        liste = self._son_listesi()
        if not liste:
            e = self.m_son.addAction("(boş)")
            e.setEnabled(False)
            return
        for yol in liste:
            e = QtGui.QAction(os.path.basename(yol), self)
            e.setToolTip(yol)
            e.triggered.connect(lambda _c=False, y=yol: self.proje_ac(y))
            self.m_son.addAction(e)

    # ==================================================================
    # dosya islemleri
    # ==================================================================
    def _kaydetme_sor(self):
        if not self._kirli:
            return True
        soru = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Question, "Kaydedilmemiş değişiklikler",
            "Değişiklikler kaydedilmedi. Kaydedilsin mi?",
            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard
            | QtWidgets.QMessageBox.Cancel, self)
        # Qt'nin Turkce cevirisinde "Discard" -> "At"; burada acik adlar.
        for dugme, ad in ((QtWidgets.QMessageBox.Save, "Kaydet"),
                          (QtWidgets.QMessageBox.Discard, "Kaydetme"),
                          (QtWidgets.QMessageBox.Cancel, "Vazgeç")):
            soru.button(dugme).setText(ad)
        soru.exec()
        c = soru.standardButton(soru.clickedButton())
        if c == QtWidgets.QMessageBox.Save:
            return self.proje_kaydet()
        return c == QtWidgets.QMessageBox.Discard

    def proje_yeni(self):
        """Dosya > Yeni: baslangic ekrani. Kaydetme sorusu bir kart
        SECILINCE sorulur -- vazgecen kullanici modeline geri doner."""
        self.baslangici_goster()

    def _ac_diyalog(self):
        yol, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Model aç", ORNEKLER, "JSON model (*.json);;Tüm dosyalar (*)")
        if yol:
            self.proje_ac(yol)

    @staticmethod
    def _ornek_mi(yol):
        """Dosya ornekler/ dizininde mi? (ornekler ayni zamanda test referansidir)"""
        return (os.path.dirname(os.path.realpath(yol))
                == os.path.realpath(ORNEKLER))

    def proje_ac(self, yol):
        # Ornek dosyalar (baslangic ekrani, Ac..., komut satiri, son
        # kullanilanlar -- hepsi buradan gecer) KAYDEDILMEMIS BIR KOPYA olarak
        # acilir. Eskiden gercek dosya aciliyordu ve Ctrl+S ornekler/*.json'u
        # (testlerin referanslarini) ustune yaziyordu.
        if self._ornek_mi(yol):
            return self.ornek_ac(yol)
        if not self._kaydetme_sor():
            return False
        try:
            yeni = sema.yukle(yol)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Açılamadı", str(e))
            return False
        self._proje_kur(yeni, proje_yolu=os.path.abspath(yol), ornek_kaynagi=None)
        self._sona_ekle(yol)
        self.statusBar().showMessage("Açıldı: %s" % yol, 6000)
        return True

    def ornek_ac(self, yol):
        """Bir ornegi kaydedilmemis KOPYA olarak acar (proje_yolu = None)."""
        if not self._kaydetme_sor():
            return False
        try:
            yeni = sema.yukle(yol)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Açılamadı", str(e))
            return False
        self._proje_kur(yeni, proje_yolu=None, ornek_kaynagi=os.path.abspath(yol))
        self.statusBar().showMessage(
            "Örnek kopya olarak açıldı: %s — kaydetmek için 'Farklı kaydet' "
            "kullanın (örnek dosyası değişmez)" % os.path.basename(yol), 8000)
        return True

    def proje_kaydet(self):
        if self.proje_yolu is None:
            return self.proje_farkli_kaydet()
        try:
            sema.kaydet(self.spec, self.proje_yolu)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Kaydedilemedi", str(e))
            return False
        self._kirli = False
        self._baslik_guncelle()
        self._sona_ekle(self.proje_yolu)
        self.statusBar().showMessage("Kaydedildi: %s" % self.proje_yolu, 5000)
        return True

    def proje_farkli_kaydet(self):
        if self.proje_yolu:
            varsayilan = self.proje_yolu
        elif self.ornek_kaynagi:
            # Ornegin kopyasi: varsayilan yer ornekler/ OLMAMALI.
            varsayilan = os.path.join(os.path.expanduser("~"),
                                      os.path.basename(self.ornek_kaynagi))
        else:
            varsayilan = os.path.join(os.path.expanduser("~"), "model.json")
        yol, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Modeli kaydet", varsayilan, "JSON model (*.json)")
        if not yol:
            return False
        if not yol.endswith(".json"):
            yol += ".json"
        self.proje_yolu = yol
        self.ornek_kaynagi = None
        self.s_calistir.spec_ayarla(self.spec, self.proje_yolu)
        self.s_tukenme.proje_ayarla(self.proje_yolu)
        return self.proje_kaydet()

    def malzeme_ice_aktar(self):
        yol, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Malzeme içeren OpenMC XML dosyası",
            os.path.dirname(self.proje_yolu) if self.proje_yolu else os.path.expanduser("~"),
            "OpenMC XML (materials.xml model.xml *.xml);;Tüm dosyalar (*)")
        if not yol:
            return
        try:
            yeni_malzemeler, notlar = ice_aktar.malzemeleri_oku(yol)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Okunamadı", str(e))
            return
        if not yeni_malzemeler:
            QtWidgets.QMessageBox.information(self, "Boş", "Dosyada malzeme bulunamadı.")
            return
        # Geri alinabilir tek adim: bekleyen duzenleme once kendi adimi olsun.
        self._gecmis_sayac.stop()
        self._gecmise_it()
        mevcut = {m["ad"] for m in self.spec["malzemeler"]}
        for m in yeni_malzemeler:
            ad, i = m["ad"], 2
            while ad in mevcut:
                ad = "%s_%d" % (m["ad"], i)
                i += 1
            m["ad"] = ad
            mevcut.add(ad)
            self.spec["malzemeler"].append(m)
        self._kirli = True
        self._spec_uygula()
        self._gecmise_it()
        mesaj = "%d malzeme eklendi.\n\n" % len(yeni_malzemeler)
        if notlar:
            mesaj += "Notlar:\n" + "\n".join("  - " + n for n in notlar) + "\n\n"
        mesaj += _ICE_AKTAR_NOTU
        self.statusBar().showMessage("%d malzeme içe aktarıldı — geometri aktarılmaz, "
                                     "arayüzde kurulur." % len(yeni_malzemeler), 8000)
        QtWidgets.QMessageBox.information(self, "İçe aktarıldı", mesaj)

    def betik_disa_aktar(self):
        varsayilan = os.path.splitext(self.proje_yolu or "model.json")[0] + ".py"
        yol, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Python betiği olarak dışa aktar", varsayilan, "Python (*.py)")
        if not yol:
            return
        try:
            kod = kod_uret.uret(self.spec, os.path.basename(yol))
            with open(yol, "w", encoding="utf-8") as f:
                f.write(kod)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Üretilemedi", str(e))
            return
        QtWidgets.QMessageBox.information(
            self, "Dışa aktarıldı",
            "Betik yazıldı:\n%s\n\n%d satır. Tek başına çalışır; arayüze geri "
            "yüklenemez." % (yol, len(kod.splitlines())))

    def xml_disa_aktar(self):
        dizin = QtWidgets.QFileDialog.getExistingDirectory(
            self, "XML'lerin yazılacağı dizin",
            os.path.dirname(self.proje_yolu) if self.proje_yolu else os.path.expanduser("~"))
        if not dizin:
            return
        try:
            model, _ = onbellek.kur_taze(self.spec)
            model.export_to_model_xml(os.path.join(dizin, "model.xml"))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Üretilemedi", str(e))
            return
        self.statusBar().showMessage("XML yazıldı: %s/model.xml" % dizin, 6000)

    def png_kaydet(self):
        yol, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Önizlemeyi kaydet", "geometri.png", "PNG (*.png)")
        if yol:
            self.onizleme.kaydet(yol)
            self.statusBar().showMessage("Kaydedildi: %s" % yol, 5000)

    def closeEvent(self, olay):
        if self._kaydetme_sor():
            self.onizleme.kapat()      # openmc kutuphanesini serbest birak
            # Onceki tukenme sonucu arka planda okunuyor olabilir (~3 s).
            # Calisan bir QThread yok edilirse Qt sureci DUSURUR ("QThread:
            # Destroyed while thread is still running") -- ornegi acip hemen
            # kapatan kullanici uygulamayi cokertirdi.
            self.s_tukenme.bekle()
            olay.accept()
        else:
            olay.ignore()


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    # Ondalik ayirici her yerde nokta: sayi kutulari sistem diline (tr_TR'de
    # virgul) degil C yerel ayarina gore yazar/okur; etiketler de nokta kullanir.
    QtCore.QLocale.setDefault(QtCore.QLocale.c())
    app = QtWidgets.QApplication(sys.argv[:1])
    qt_turkce_cevirisi(app)
    app.setApplicationName("OpenMC Arayüz")
    tema.uygula(app)
    tekerlek_korumasi_kur(app)
    pencere = AnaPencere(argv[0] if argv else None)
    pencere.show()

    # Pencereyi buyutme:
    #   showMaximized() bu makinedeki pencere yoneticisinde yok sayiliyor,
    #   show()'dan hemen sonra setWindowState() de tutmuyor -- pencerenin
    #   once HARITALANMASI gerekiyor. Bu yuzden olay dongusu basladiktan
    #   kisa bir sure sonra uygulaniyor.
    def _buyut_gecikmeli():
        pencere.setWindowState(pencere.windowState() | QtCore.Qt.WindowMaximized)
    QtCore.QTimer.singleShot(120, _buyut_gecikmeli)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
