# -*- coding: utf-8 -*-
"""
 arayuz/pencere/model_islemleri.py  --  saf model islemleri ve sekme/konu sabitleri (Qt'siz)

 arayuz/ana_pencere.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import ana_pencere; ana_pencere.X` aynen calisir.
"""

import copy
import math
import os

from cekirdek.ceviri import _
from cekirdek import sema, dogrula, surum, uygunluk


# Proje koku: arayuz/pencere/ -> arayuz/ -> kok (eski arayuz/ana_pencere.py'de
# iki dirname idi; dosya bir dizin derine indigi icin uc).
KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORNEKLER = os.path.join(KOK, "ornekler")
UYGULAMA_ADI = surum.UYGULAMA_ADI


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
    "kor": "Geometri", "ayarlar": "Hesap ayarları", "calistir": "Çalıştır",
    "analiz": "Analiz", "tukenme": "Tükenme",
}

# Onizleme + dogrulama paneli yalnizca TASARIM sekmelerinde; Hesap
# ayarlarinda yalnizca dogrulama.
TASARIM_SEKMELERI = ("malzemeler", "parcalar", "demet", "kor")
DOGRULAMA_SEKMELERI = TASARIM_SEKMELERI + ("ayarlar",)

# Kor turlerinin sade adlari ("Turu degistir..." menusu).
TUR_ADLARI = uygunluk.KOR_TURU_ADLARI


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
    if tur == "altigen_kafes":
        from cekirdek import altigen
        n = int(kor.get("halka_sayisi") or 0)
        return _("%d demetli altıgen tam kor") % altigen.toplam_hucre(n) if n else \
            _("altıgen tam kor")
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
    if tur in ("tek_cubuk", "tek_demet") + sema.HARITALI_KORLAR and not spec.get("cubuklar"):
        eksik = "Eksik: bu kor türü için en az bir yakıt çubuğu tanımlanmalı."
    elif tur == "tek_plaka" and not spec.get("plakalar"):
        eksik = "Eksik: bu kor türü için bir plaka elemanı tanımlanmalı."
    koy("parcalar", eksik)

    koy("demet", "Eksik: bu kor türü için bir demet kurulmalı."
        if tur in ("tek_demet",) + sema.HARITALI_KORLAR and not spec.get("demetler") else None)

    eksik = None
    alan = {"tek_cubuk": "cubuk", "tek_plaka": "plaka", "tek_demet": "demet",
            "tamburlu": "dolgu"}.get(tur)
    if alan and not kor.get(alan):
        eksik = "Eksik: korun dolgusu henüz seçilmedi."
    elif tur in sema.HARITALI_KORLAR and not kor.get("harita"):
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

    def altigen_demet_gerekli():
        # Altigen korun haritasina yalnizca altigen demet oturur.
        if not any(d.get("tur") == "altigen" for d in spec.get("demetler", [])):
            cubuk_gerekli()
            from arayuz.sekme_demet import yeni_demet
            ad = sc.benzersiz_ad(spec, "altigen_demet")
            spec.setdefault("demetler", []).append(yeni_demet(spec, "altigen", ad))
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
    elif tur == "altigen_kafes":
        altigen_demet_gerekli()
    return eklenen


# Bos sablonun varsayilan model adi; tur degisince ad da yeni ture uyar
# (kullanici adi degistirmediyse). Ajan 9: "Yeni yakıt çubuğu" adli model
# plakaya donunce de ayni adla kaliyordu.
_SABLON_ADLARI = {"tek_cubuk": "Yeni yakıt çubuğu", "tek_demet": "Yeni kare yakıt demeti",
                  "tek_plaka": "Yeni plaka elemanı", "tamburlu": "Yeni tamburlu kor",
                  "kare_kafes": "Yeni tam kor", "altigen_kafes": "Yeni altıgen tam kor"}


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
    if eski in sema.HARITALI_KORLAR and yeni_tur in sema.HARITALI_KORLAR:
        # Kare ve altigen harita ayni alanlari paylasir ama bicimleri farklidir
        # (satirlar / halkalar): birinin haritasi otekine tasinmaz.
        for alan in ("adim", "boyut", "harita", "anahtar"):
            kor[alan] = copy.deepcopy(sema.VARSAYILAN_KOR[alan])
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
    elif yeni_tur == "altigen_kafes" and not kor.get("harita"):
        altigen_kor_haritasi_kur(spec, eski_dolgu)
    return True


def altigen_kor_haritasi_kur(spec, tercih=None, halka=2):
    """
    Altigen tam korun varsayilan haritasi: 'halka' halkali (2 -> 7 demet),
    tum konumlarda ayni altigen demet. Kor yonelimi demetin tersidir
    (pin kafesi ile kor kafesi 90 derece; altigen_kor), adim demetin dis
    olcusudur (kilif dahil; demetler arasi bosluk yok).
    """
    from cekirdek import altigen, altigen_kor
    from arayuz.izgara import adlardan_harita
    kor = spec["kor"]
    hexler = [d["ad"] for d in spec.get("demetler", []) if d.get("tur") == "altigen"]
    ad = tercih if tercih in hexler else (hexler[0] if hexler else None)
    d = sema.demet_bul(spec, ad) if ad else None
    if d is None:
        return False
    kor["halka_sayisi"] = int(halka)
    kor["yonelim"] = altigen_kor.ters_yonelim(d.get("yonelim", "y"))
    # 6 haneye YUKARI yuvarlanir: asagi yuvarlanan adim demetten kucuk kalir
    # ve dogrulama bunu (hakli olarak) hata sayardi.
    kor["adim"] = math.ceil(altigen_kor.demet_dis_olcu(d) * 1e6 - 1e-6) / 1e6
    kor["harita"], kor["anahtar"] = adlardan_harita(
        [[ad] * u for u in altigen.halka_uzunluklari(int(halka))])
    return True
