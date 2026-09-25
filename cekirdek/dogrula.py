# -*- coding: utf-8 -*-
"""
================================================================================
 dogrula.py  --  Model calistirilmadan once yapilan kontroller
================================================================================

 Monte Carlo kosusu pahalidir; hatalarin cogu saatler sonra ya da hic fark
 edilmez. Bu modul bilinen tuzaklari kosu ONCESINDE yakalar.

 KULLANIM
   from cekirdek import dogrula
   bulgular = dogrula.tum_kontroller(spec)
   for b in bulgular:
       print(b)
   if dogrula.hata_var(bulgular):
       ...  # calistirma engellenir

 SEVIYELER
   hata   : model calismaz ya da sonuc kesinlikle yanlis olur -- calistirma engellenir
   uyari  : model calisir ama sonuc supheli -- kullanici karar verir
   bilgi  : dikkat cekici ama sorun degil

 KONTROL LISTESI
   1. OPENMC_CROSS_SECTIONS ortam degiskeni ve dosyanin varligi
   2. Modelin istedigi her nuklidin veri kutuphanesinde bulunmasi
   3. S(a,b) unutulmus moderatorler (su/grafit/berilyum)
   4. Malzeme tanimlari: yogunluk, bos bilesim, negatif deger
   5. Cubuk bolgeleri: artan yaricap, son bolgenin acik olmasi
   6. Kafes haritalari: satir/sutun sayisi, tanimsiz harf
   7. Sinir kosullari ve sizinti riski
   8. Ayarlar: pasif cevrim sayisi, parcacik sayisi
   9. Tanimli ama kullanilmayan / kullanilmis ama tanimsiz malzemeler
================================================================================
"""

import os

from cekirdek.sema import kor_yuksekligi as sema_kor_yuksekligi
from cekirdek.sema import BOSLUK, malzeme_bul, cubuk_bul, plaka_bul, demet_bul
from cekirdek import altigen, kurucu, veri_bilgi, sema
from cekirdek import kaynak as _kaynak

# ----------------------------------------------------------------------------
# S(a,b) beklentisi -- SAFLIK KURALLARIYLA
#
# Naif kural ("bilesimde C varsa grafittir") SS316 (agirlikca %0.5 C), B4C ve
# SiC icin yanlis alarm uretir. Dogru olcut, malzemenin gercekten o baglayici
# fazda olup olmadigidir; bu yuzden her kural bilesimin TAMAMINA bakar.
#
# Her giris: (uygun_element_kumesi, onerilen_sab, insan_okunur_ad)
#   bilesimdeki tum elementler kumenin icindeyse kural tetiklenir.
# ----------------------------------------------------------------------------
# (izin verilen elementler, ZORUNLU elementler, onerilen S(a,b), tanim)
#   Eslesme sarti: zorunlu <= malzeme <= izin verilen.
#   ZORUNLU kume sonradan eklendi. Once yalnizca "malzeme <= izin verilen"
#   bakiliyordu; {Zr} kumesi {H, Zr}'nin alt kumesi oldugu icin SAF ZIRKONYUM
#   "zirkonyum hidrur" sayiliyor ve kullaniciya c_H_in_ZrH eklemesi
#   oneriliyordu -- hidrojensiz bir malzemeye hidrojen S(a,b)'si, yani yanlis
#   fizik. Ayni mantikla B2O3 "borlu su" cikardi.
_SAB_KURALLARI = [
    ({"H", "O"},      {"H"},       "c_H_in_H2O",  "su (H2O)"),
    ({"H", "O", "B"}, {"H"},       "c_H_in_H2O",  "borlu su"),
    ({"H", "Zr"},     {"H", "Zr"}, "c_H_in_ZrH",  "sirkonyum hidrur"),
    ({"H", "C"},      {"H", "C"},  "c_H_in_CH2",  "polietilen / plastik"),
    ({"C"},           {"C"},       "c_Graphite",  "grafit"),
    ({"Be"},          {"Be"},      "c_Be",        "berilyum"),
    ({"Be", "O"},     {"Be", "O"}, "c_Be_in_BeO", "berilyum oksit"),
    ({"D", "O"},      {"D"},       "c_D_in_D2O",  "agir su (D2O)"),
]

# ----------------------------------------------------------------------------
# Bilinen tally skorlari.
#
# !!! BU LISTE KURATORLUDUR !!!
#   OpenMC'nin Python tarafi gecerli skor listesi SUNMAZ; Tally.scores setter'i
#   hicbir dogrulama yapmaz (uydurma bir ad bile kabul edilir) ve hata ancak
#   kosu sirasinda C++ tarafinda cikar. Bu yuzden liste elle tutuluyor.
#   Yeni bir OpenMC surumu skor eklerse liste eskir -- bu nedenle bulunamayan
#   skor HATA degil UYARI uretir.
# ----------------------------------------------------------------------------
BILINEN_SKORLAR = {
    "flux", "total", "absorption", "elastic", "fission", "nu-fission",
    "prompt-nu-fission", "delayed-nu-fission", "kappa-fission",
    "fission-q-prompt", "fission-q-recoverable", "scatter", "nu-scatter",
    "heating", "heating-local", "damage-energy", "decay-rate",
    "inverse-velocity", "current", "events", "pulse-height",
    "(n,2n)", "(n,3n)", "(n,4n)", "(n,gamma)", "(n,p)", "(n,a)", "(n,d)",
    "(n,t)", "(n,elastic)", "(n,level)",
    "ifp-time-numerator", "ifp-beta-numerator", "ifp-denominator",
}

# Yogunlastirilmis faz esigi [g/cm3] -- bunun altinda gaz kabul edilir,
# termal sacilma baglama etkisi anlamsizdir.
_YOGUN_FAZ_ESIGI = 0.1


class Bulgu(object):
    """Tek bir dogrulama bulgusu."""

    def __init__(self, seviye, yer, mesaj, oneri=None):
        self.seviye = seviye        # "hata" | "uyari" | "bilgi"
        self.yer = yer              # "malzeme:uo2", "kor", "ayarlar" ...
        self.mesaj = mesaj
        self.oneri = oneri

    def __str__(self):
        im = {"hata": "HATA ", "uyari": "UYARI", "bilgi": "BILGI"}[self.seviye]
        s = "[%s] %-22s %s" % (im, self.yer, self.mesaj)
        if self.oneri:
            s += "\n                             -> %s" % self.oneri
        return s

    def __repr__(self):
        return "Bulgu(%s, %s)" % (self.seviye, self.mesaj)


def hata_var(bulgular):
    """Listede en az bir 'hata' seviyesinde bulgu varsa True."""
    return any(b.seviye == "hata" for b in bulgular)


# ============================================================================
# 1. VERI KUTUPHANESI
# ============================================================================

def veri_kutuphanesi_kontrol():
    """OPENMC_CROSS_SECTIONS ayarli mi, dosya var mi?"""
    bulgular = []
    yol = os.environ.get("OPENMC_CROSS_SECTIONS")
    if not yol:
        bulgular.append(Bulgu(
            "hata", "veri kutuphanesi",
            "OPENMC_CROSS_SECTIONS ortam degiskeni ayarli degil",
            "export OPENMC_CROSS_SECTIONS=$HOME/nucdata/.../cross_sections.xml"))
    elif not os.path.exists(yol):
        bulgular.append(Bulgu(
            "hata", "veri kutuphanesi",
            "cross_sections.xml bulunamadi: %s" % yol,
            "Yolu kontrol edin ya da veri kutuphanesini indirin"))
    return bulgular


def _kutuphane_icerigi():
    """
    cross_sections.xml icindeki notron ve termal kayitlarini okur.
    DONER (notron_adlari, termal_adlari) -- okunamazsa (None, None)
    """
    yol = os.environ.get("OPENMC_CROSS_SECTIONS")
    if not yol or not os.path.exists(yol):
        return None, None
    try:
        import xml.etree.ElementTree as ET
        kok = ET.parse(yol).getroot()
        notron, termal = set(), set()
        for lib in kok.findall("library"):
            tur = lib.get("type")
            mats = (lib.get("materials") or "").split()
            if tur == "neutron":
                notron.update(mats)
            elif tur == "thermal":
                termal.update(mats)
        return notron, termal
    except Exception:
        return None, None


def nuklid_kontrol(spec):
    """
    Modelin istedigi her nuklid veri kutuphanesinde var mi?
    Elementler dogal bollukla nuklidlere acilir; bunun icin malzemeler
    gercekten kurulur.
    """
    bulgular = []
    notron, termal = _kutuphane_icerigi()
    if notron is None:
        bulgular.append(Bulgu("uyari", "veri kutuphanesi",
                              "cross_sections.xml okunamadi, nuklid kontrolu atlandi"))
        return bulgular

    try:
        nesneler, _, _ = kurucu.malzemeleri_kur(spec)
    except Exception as e:
        bulgular.append(Bulgu("hata", "malzemeler",
                              "malzemeler kurulamadi: %s" % e))
        return bulgular

    for ad, mat in nesneler.items():
        try:
            istenen = set(mat.get_nuclides())
        except Exception as e:
            bulgular.append(Bulgu("uyari", "malzeme:%s" % ad,
                                  "nuklid listesi cikarilamadi: %s" % e))
            continue
        eksik = sorted(istenen - notron)
        if eksik:
            bulgular.append(Bulgu(
                "hata", "malzeme:%s" % ad,
                "veri kutuphanesinde olmayan nuklid: %s" % ", ".join(eksik),
                "Bilesimi degistirin ya da bu nuklidleri iceren bir kutuphane kullanin"))
        for s in (malzeme_bul(spec, ad) or {}).get("sab", []):
            if s not in termal:
                bulgular.append(Bulgu(
                    "hata", "malzeme:%s" % ad,
                    "termal sacilma verisi kutuphanede yok: %s" % s,
                    "Mevcut S(a,b) kayitlari: %d adet" % len(termal)))
    return bulgular


# ============================================================================
# 2. MALZEMELER
# ============================================================================

def malzeme_kontrol(spec):
    """Yogunluk, bilesim ve S(a,b) tutarliligi."""
    bulgular = []
    adlar = [m["ad"] for m in spec["malzemeler"]]

    for ad in set(adlar):
        if adlar.count(ad) > 1:
            bulgular.append(Bulgu("hata", "malzeme:%s" % ad,
                                  "ayni ad %d kez tanimlanmis" % adlar.count(ad)))
    if BOSLUK in adlar:
        bulgular.append(Bulgu("hata", "malzemeler",
                              "'%s' ayrilmis bir addir (void), malzeme olarak tanimlanamaz" % BOSLUK))

    for m in spec["malzemeler"]:
        yer = "malzeme:%s" % m["ad"]
        if not m.get("bilesim"):
            bulgular.append(Bulgu("hata", yer, "bilesim bos"))
            continue
        yog = (m.get("yogunluk") or {}).get("deger")
        if yog is None:
            bulgular.append(Bulgu("hata", yer, "yogunluk verilmemis"))
        elif yog <= 0:
            bulgular.append(Bulgu("hata", yer, "yogunluk pozitif olmali: %s" % yog))

        for b in m["bilesim"]:
            if b.get("miktar", 0) <= 0:
                bulgular.append(Bulgu("hata", yer,
                                      "'%s' miktari pozitif olmali: %s"
                                      % (b.get("isim"), b.get("miktar"))))
            z = b.get("zenginlik")
            if z is not None and not (0.0 < z < 100.0):
                bulgular.append(Bulgu("hata", yer,
                                      "'%s' zenginligi 0-100 araliginda olmali: %s"
                                      % (b["isim"], z)))
            elif z is not None and b.get("isim") == "U" and z > 5.0:
                bulgular.append(Bulgu(
                    "uyari", yer,
                    "U zenginligi %%%.2f -- OpenMC zenginlik kisayolu U234/U235 "
                    "kutle oranini sabit 0.008 varsayar, bu sadece dusuk "
                    "zenginliklerde gecerlidir" % z,
                    "Bilesimi nuklid bazinda verin (U234/U235/U238) ya da sonucun "
                    "U234 duyarliligini kabul edin"))

        # --- S(a,b) unutulmus mu? termal spektrumun en klasik hatasi ---
        bulgular += _sab_kontrol(m, yer)
    return bulgular


def _element_kumesi(malzeme):
    """
    Bilesimdeki element sembollerini dondurur. Nuklidler element sembolune
    indirgenir (U235 -> U, H2 -> D cunku agir su ayri bir kuraldir).
    """
    kume = set()
    for b in malzeme.get("bilesim", []):
        isim = b.get("isim", "")
        if b.get("tur") == "nuklid":
            if isim in ("H2", "D"):
                kume.add("D")
                continue
            # "U235" -> "U",  "Pu239" -> "Pu"
            sembol = "".join(ch for ch in isim if ch.isalpha())
            kume.add(sembol)
        else:
            kume.add(isim)
    return kume


def _sab_kontrol(malzeme, yer):
    """
    Yogunlastirilmis fazdaki moderatorlerde S(a,b) eksikligini arar.

    Kural bilesimin TAMAMINA bakar: SS316 (%0.5 C), B4C ve SiC karbon icerir
    ama grafit degildir; bu yuzden "C var -> grafit" gibi bir kisayol
    kullanilmaz.
    """
    if malzeme.get("sab"):
        return []
    yog = (malzeme.get("yogunluk") or {}).get("deger") or 0.0
    if yog <= _YOGUN_FAZ_ESIGI:
        return []          # gaz -- baglama etkisi yok
    elemanlar = _element_kumesi(malzeme)
    if not elemanlar:
        return []
    # Birden fazla kural eslesebilir (saf karbon hem {"C"} hem {"H","C"}
    # kumesinin alt kumesidir). EN DAR kural kazanir -- yoksa grafit
    # "polietilen" diye raporlanir.
    eslesenler = [(len(uygun), onerilen, tanim)
                  for uygun, zorunlu, onerilen, tanim in _SAB_KURALLARI
                  if zorunlu <= elemanlar <= uygun]
    if eslesenler:
        _, onerilen, tanim = min(eslesenler)
        return [Bulgu(
            "uyari", yer,
            "%s gorunumunde ama S(a,b) termal sacilma verisi eklenmemis" % tanim,
            "Termal spektrumda k'yi yuzde mertebesinde kaydirir. "
            "Ekleyin: sab=['%s']" % onerilen)]
    # Kurala uymayan ama hidrojen iceren yogun malzeme -- yine de uyar
    if "H" in elemanlar:
        return [Bulgu(
            "uyari", yer,
            "yogunlastirilmis fazda hidrojen var ama S(a,b) eklenmemis",
            "Hidrojenin bagli oldugu faza uygun bir S(a,b) secin "
            "(orn. c_H_in_H2O, c_H_in_ZrH, c_H_in_CH2)")]
    return []


# ============================================================================
# 3. GEOMETRI
# ============================================================================

def cubuk_kontrol(spec):
    """Radyal bolgelerin sirasi ve kapanisi."""
    bulgular = []
    for c in spec.get("cubuklar", []):
        yer = "cubuk:%s" % c["ad"]
        bolgeler = c.get("bolgeler") or []
        if len(bolgeler) < 2:
            bulgular.append(Bulgu("hata", yer,
                                  "en az iki bolge gerekir (ic + disarisi)"))
            continue
        if bolgeler[-1].get("r") is not None:
            bulgular.append(Bulgu(
                "hata", yer, "son bolgenin 'r' degeri null olmali",
                "Son bolge 'disarisi'dir ve hucreyi doldurur"))
        yaricaplar = [b.get("r") for b in bolgeler[:-1]]
        for i, r in enumerate(yaricaplar):
            if r is None or r <= 0:
                bulgular.append(Bulgu("hata", yer,
                                      "%d. bolgenin yaricapi pozitif olmali: %s" % (i + 1, r)))
        temiz = [r for r in yaricaplar if isinstance(r, (int, float))]
        for i in range(len(temiz) - 1):
            if temiz[i] >= temiz[i + 1]:
                bulgular.append(Bulgu(
                    "hata", yer,
                    "yaricaplar artan sirada olmali: r%d=%.5f >= r%d=%.5f"
                    % (i + 1, temiz[i], i + 2, temiz[i + 1])))
        for b in bolgeler:
            ad = b.get("malzeme")
            if ad and ad != BOSLUK and malzeme_bul(spec, ad) is None:
                bulgular.append(Bulgu("hata", yer, "tanimsiz malzeme: %s" % ad))
    return bulgular


def kontrol_cubugu_kontrol(spec):
    """Kontrol cubuklarinin gereksinimleri."""
    bulgular = []
    h = sema_kor_yuksekligi(spec["kor"])
    for c in spec.get("cubuklar", []):
        if c.get("tur") != "kontrol":
            continue
        yer = "cubuk:%s" % c["ad"]
        if not h:
            bulgular.append(Bulgu(
                "hata", yer,
                "kontrol cubugu 3B model gerektirir (kor yuksekligi tanimsiz)",
                "Eksenel bir uc konumu olmadan daldirma tanimlanamaz. "
                "Kor sekmesinde aktif yukseklik tanimlayin."))
        d = c.get("daldirma")
        if d is None or not (0.0 <= float(d) <= 100.0):
            bulgular.append(Bulgu("hata", yer,
                                  "daldirma %%0-%%100 arasinda olmali: %s" % d))
        ix = c.get("emici_bolge")
        if not isinstance(ix, int) or not (0 <= ix < len(c.get("bolgeler", []))):
            bulgular.append(Bulgu("hata", yer,
                                  "gecersiz emici bolge: %s" % ix))
        else:
            mal = c["bolgeler"][ix].get("malzeme")
            m = malzeme_bul(spec, mal) if mal else None
            if m:
                elemanlar = {b.get("isim", "") for b in m.get("bilesim", [])}
                sogurucu = bool(elemanlar & {"B", "B10", "Gd", "Ag", "In", "Cd", "Hf", "Eu"})
                if not sogurucu:
                    bulgular.append(Bulgu(
                        "uyari", yer,
                        "emici bolgenin malzemesi ('%s') guclu bir notron "
                        "sogurucu icermiyor" % mal,
                        "Kontrol malzemeleri genellikle B4C, Ag-In-Cd, Gd2O3 ya "
                        "da Hf icerir."))
        iz = c.get("izleyici_malzeme")
        if iz and iz != BOSLUK and malzeme_bul(spec, iz) is None:
            bulgular.append(Bulgu("hata", yer, "tanimsiz izleyici malzeme: %s" % iz))
    return bulgular


def plaka_kontrol(spec):
    """Plaka eleman olculeri."""
    bulgular = []
    for p in spec.get("plakalar", []):
        yer = "plaka:%s" % p["ad"]
        for alan in ("plaka_sayisi", "et_kalinlik", "zarf_kalinlik",
                     "kanal_kalinlik", "plaka_genislik"):
            deger = p.get(alan)
            if deger is None or deger <= 0:
                bulgular.append(Bulgu("hata", yer,
                                      "%s pozitif olmali: %s" % (alan, deger)))
        for alan in ("et_malzeme", "zarf_malzeme", "sogutucu"):
            ad = p.get(alan)
            if ad and ad != BOSLUK and malzeme_bul(spec, ad) is None:
                bulgular.append(Bulgu("hata", yer,
                                      "%s icin tanimsiz malzeme: %s" % (alan, ad)))
    return bulgular


def demet_kontrol(spec):
    """Kafes haritasi boyutlari ve harf cozumlemesi."""
    bulgular = []
    for d in spec.get("demetler", []):
        yer = "demet:%s" % d["ad"]
        harita = d.get("harita") or []
        if not harita:
            bulgular.append(Bulgu("hata", yer, "harita bos"))
            continue
        if d.get("tur") == "kare":
            nx, ny = d["boyut"]
            if len(harita) != ny:
                bulgular.append(Bulgu(
                    "hata", yer,
                    "harita %d satir ama boyut %d satir bekliyor" % (len(harita), ny)))
            for i, satir in enumerate(harita):
                if len(satir) != nx:
                    bulgular.append(Bulgu(
                        "hata", yer,
                        "%d. satir %d karakter ama %d bekleniyor" % (i + 1, len(satir), nx)))
        if d.get("tur") == "altigen":
            halka = d.get("halka_sayisi") or d.get("boyut", [0])[0]
            if not halka or halka < 1:
                bulgular.append(Bulgu("hata", yer, "halka sayisi en az 1 olmali"))
            else:
                beklenen = altigen.halka_uzunluklari(halka)
                if len(harita) != len(beklenen):
                    bulgular.append(Bulgu(
                        "hata", yer,
                        "%d halka bekleniyor, haritada %d satir var"
                        % (len(beklenen), len(harita)),
                        "Halkalar DISTAN ICE siralanir; yaricapi k olan halkada "
                        "6k oge, merkezde 1 oge bulunur"))
                else:
                    for i, (satir, uzunluk) in enumerate(zip(harita, beklenen)):
                        if len(satir) != uzunluk:
                            bulgular.append(Bulgu(
                                "hata", yer,
                                "%d. halka (yaricap %d) %d oge bekliyor, %d var"
                                % (i + 1, halka - 1 - i, uzunluk, len(satir))))
            if d.get("yonelim", "y") not in ("x", "y"):
                bulgular.append(Bulgu("hata", yer,
                                      "yonelim 'x' ya da 'y' olmali: %s" % d.get("yonelim")))
        if d.get("adim", 0) <= 0:
            bulgular.append(Bulgu("hata", yer, "adim pozitif olmali"))

        kullanilan = {h for satir in harita for h in satir}
        tanimli = set((d.get("anahtar") or {}).keys())
        for h in sorted(kullanilan - tanimli):
            bulgular.append(Bulgu("hata", yer,
                                  "haritada tanimsiz harf: '%s'" % h,
                                  "anahtar sozlugune ekleyin"))
        for h in sorted(tanimli - kullanilan):
            bulgular.append(Bulgu("bilgi", yer,
                                  "anahtarda tanimli ama haritada kullanilmayan harf: '%s'" % h))
        for h, hedef in (d.get("anahtar") or {}).items():
            if (cubuk_bul(spec, hedef) is None and plaka_bul(spec, hedef) is None
                    and demet_bul(spec, hedef) is None
                    and hedef != BOSLUK and malzeme_bul(spec, hedef) is None):
                bulgular.append(Bulgu("hata", yer,
                                      "'%s' harfi cozumlenemeyen ada isaret ediyor: %s" % (h, hedef)))
    return bulgular


def kor_kontrol(spec):
    """Kor turu, referanslar ve sinir kosullari."""
    bulgular = []
    kor = spec["kor"]
    tur = kor.get("tur")
    gecerli = ("tek_cubuk", "tek_demet", "kare_kafes", "tek_plaka", "kuresel",
               "tamburlu")
    if tur not in gecerli:
        bulgular.append(Bulgu("hata", "kor",
                              "bilinmeyen kor turu: %s (gecerli: %s)"
                              % (tur, ", ".join(gecerli))))
        return bulgular

    if tur == "tek_cubuk":
        if not kor.get("cubuk"):
            bulgular.append(Bulgu("hata", "kor", "cubuk secilmemis"))
        elif cubuk_bul(spec, kor["cubuk"]) is None:
            bulgular.append(Bulgu("hata", "kor", "tanimsiz cubuk: %s" % kor["cubuk"]))
        if kor.get("adim", 0) <= 0:
            bulgular.append(Bulgu("hata", "kor", "adim pozitif olmali"))
        else:
            c = cubuk_bul(spec, kor.get("cubuk") or "")
            if c:
                dis_r = max([b["r"] for b in c["bolgeler"] if b.get("r")] or [0])
                if dis_r * 2 > kor["adim"]:
                    bulgular.append(Bulgu(
                        "hata", "kor",
                        "cubuk dis capi (%.5f) hucre adimindan (%.5f) buyuk"
                        % (dis_r * 2, kor["adim"])))
    elif tur == "tek_demet":
        if not kor.get("demet") or demet_bul(spec, kor.get("demet")) is None:
            bulgular.append(Bulgu("hata", "kor", "tanimsiz demet: %s" % kor.get("demet")))
    elif tur == "tek_plaka":
        if not kor.get("plaka") or plaka_bul(spec, kor.get("plaka")) is None:
            bulgular.append(Bulgu("hata", "kor", "tanimsiz plaka elemani: %s" % kor.get("plaka")))
    elif tur == "tamburlu":
        from cekirdek import tambur as _t
        R_kor = kor.get("kor_yaricap") or 0.0
        yans = kor.get("yansitici") or {}
        kal = yans.get("kalinlik") or 0.0
        if R_kor <= 0:
            bulgular.append(Bulgu("hata", "kor", "kor yaricapi pozitif olmali"))
        if kal <= 0:
            bulgular.append(Bulgu("hata", "kor",
                                  "tamburlu korda yansitici kalinligi pozitif olmali"))
        if not yans.get("malzeme") or yans["malzeme"] == BOSLUK:
            bulgular.append(Bulgu("uyari", "kor",
                                  "yansitici malzemesi secilmemis (void)"))
        dolgu = kor.get("dolgu")
        if not dolgu:
            bulgular.append(Bulgu("hata", "kor", "kor dolgusu secilmemis"))
        elif (dolgu != BOSLUK and cubuk_bul(spec, dolgu) is None
              and demet_bul(spec, dolgu) is None
              and malzeme_bul(spec, dolgu) is None):
            bulgular.append(Bulgu("hata", "kor",
                                  "kor dolgusu cozumlenemedi: %s" % dolgu))
        t = kor.get("tambur") or {}
        if int(t.get("sayi") or 0) <= 0:
            bulgular.append(Bulgu(
                "bilgi", "kor",
                "tambur sayisi 0 -- kontrol tamburu olmadan duz yansitici kusak"))
        else:
            for h in _t.geometri_kontrol(t, R_kor, kal):
                bulgular.append(Bulgu("hata", "kor", h))
            for anahtar, etiket in (("govde_malzeme", "tambur govdesi"),
                                    ("emici_malzeme", "tambur emicisi")):
                ad = t.get(anahtar)
                if not ad:
                    bulgular.append(Bulgu("hata", "kor",
                                          "%s malzemesi secilmemis" % etiket))
                elif ad != BOSLUK and malzeme_bul(spec, ad) is None:
                    bulgular.append(Bulgu("hata", "kor",
                                          "%s icin tanimsiz malzeme: %s" % (etiket, ad)))
            em = malzeme_bul(spec, t.get("emici_malzeme") or "")
            if em:
                elemanlar = {b.get("isim", "") for b in em.get("bilesim", [])}
                if not (elemanlar & {"B", "B10", "Gd", "Ag", "In", "Cd", "Hf", "Eu"}):
                    bulgular.append(Bulgu(
                        "uyari", "kor",
                        "tambur emicisi ('%s') guclu bir notron sogurucu icermiyor"
                        % t.get("emici_malzeme")))
            d = t.get("donme")
            if d is None or not (-360.0 <= float(d) <= 360.0):
                bulgular.append(Bulgu("hata", "kor",
                                      "tambur donmesi -360..360 derece olmali: %s" % d))
            if not sema_kor_yuksekligi(kor):
                bulgular.append(Bulgu(
                    "bilgi", "kor",
                    "tamburlu kor 2B -- eksenel sizinti yok, deger fazla cikar",
                    "Gercekci bir tambur degeri icin aktif yukseklik tanimlayin."))

    elif tur == "kuresel":
        kabuklar = kor.get("kabuklar") or []
        if not kabuklar:
            bulgular.append(Bulgu("hata", "kor", "kuresel korda en az bir kabuk gerekir"))
        for i, k in enumerate(kabuklar):
            if not k.get("r") or k["r"] <= 0:
                bulgular.append(Bulgu("hata", "kor",
                                      "%d. kabugun yaricapi pozitif olmali" % (i + 1)))
            ad = k.get("malzeme")
            if ad and ad != BOSLUK and malzeme_bul(spec, ad) is None:
                bulgular.append(Bulgu("hata", "kor",
                                      "%d. kabukta tanimsiz malzeme: %s" % (i + 1, ad)))
        r = [k.get("r") for k in kabuklar if k.get("r")]
        for i in range(len(r) - 1):
            if r[i] >= r[i + 1]:
                bulgular.append(Bulgu(
                    "hata", "kor",
                    "kabuk yaricaplari artan sirada olmali: r%d=%.5f >= r%d=%.5f"
                    % (i + 1, r[i], i + 2, r[i + 1])))
        if kor.get("sinir", {}).get("yan") == "reflective":
            bulgular.append(Bulgu(
                "uyari", "kor",
                "kuresel duzenekte dis sinir 'reflective' -- ciplak (bare) bir "
                "kriter modelliyorsaniz 'vacuum' olmali",
                "Yansitici sinir sonsuz bir ortam demektir; kritik kure "
                "kriterleri ciplaktir (vacuum)."))

    elif tur == "kare_kafes":
        harita = kor.get("harita") or []
        if not harita:
            bulgular.append(Bulgu("hata", "kor", "kor haritasi bos"))
        else:
            nx, ny = kor["boyut"]
            if len(harita) != ny:
                bulgular.append(Bulgu("hata", "kor",
                                      "harita %d satir, boyut %d bekliyor" % (len(harita), ny)))
            for i, satir in enumerate(harita):
                if len(satir) != nx:
                    bulgular.append(Bulgu("hata", "kor",
                                          "%d. satir %d karakter, %d bekleniyor"
                                          % (i + 1, len(satir), nx)))
            kullanilan = {h for satir in harita for h in satir}
            tanimli = set((kor.get("anahtar") or {}).keys())
            for h in sorted(kullanilan - tanimli):
                bulgular.append(Bulgu("hata", "kor", "haritada tanimsiz harf: '%s'" % h))

    # --- sinir kosullari ---
    sinir = kor.get("sinir") or {}
    gecerli_bc = ("reflective", "vacuum", "periodic", "white")
    for yon in ("yan", "alt", "ust"):
        bc = sinir.get(yon)
        if bc and bc not in gecerli_bc:
            bulgular.append(Bulgu("hata", "kor",
                                  "gecersiz sinir kosulu '%s': %s" % (yon, bc)))
    if sinir.get("yan") == "vacuum" and tur in ("tek_cubuk", "tek_demet"):
        bulgular.append(Bulgu(
            "uyari", "kor",
            "tek hucre/demet modelinde yan sinir 'vacuum' -- sizinti sonsuz "
            "kafes varsayimini bozar",
            "Sonsuz kafes (k-inf) istiyorsaniz 'reflective' kullanin"))
    # Kuresel duzenekte "yukseklik" diye bir kavram yoktur; kabuk yaricaplari
    # geometriyi tamamen belirler. Orada 2B uyarisi vermek yanlis olurdu.
    if not sema_kor_yuksekligi(kor) and kor.get("tur") != "kuresel":
        bulgular.append(Bulgu(
            "bilgi", "kor",
            "yukseklik verilmemis -- model eksenel yonde sonsuz (2B) kabul ediliyor"))
    return bulgular


# ============================================================================
# 4. AYARLAR
# ============================================================================

def eksenel_kontrol(spec):
    """
    Eksenel katmanlama tutarli mi?

    Katmanlamanin sessiz hatalari:
      * hicbir katmanda fisil malzeme yok -> ozdeger kosusu kaynak bulamaz
      * katman dolgusu tanimsiz bir ad -> kurulumda KeyError, kosudan once yakala
      * "yukseklik" ile katman toplami farkli -> hangisi gecerli belirsiz kalir
    """
    bulgular = []
    kor = spec["kor"]
    eks = kor.get("eksenel") or {}
    if not eks.get("var"):
        return bulgular

    tur = kor.get("tur")
    if tur not in sema.EKSENEL_DESTEKLI:
        bulgular.append(Bulgu(
            "hata", "kor",
            "eksenel katmanlama '%s' kor turunde desteklenmiyor" % tur,
            "Destekleyen turler: %s. Kuresel duzenekte eksen kavrami yoktur; "
            "orada katmani es merkezli kabuklarla kurun." % ", ".join(sema.EKSENEL_DESTEKLI)))
        return bulgular

    katmanlar = eks.get("bolgeler") or []
    if not katmanlar:
        bulgular.append(Bulgu("hata", "kor",
                              "eksenel katmanlama acik ama hic katman tanimli degil"))
        return bulgular

    adlar = set()
    for i, b in enumerate(katmanlar):
        yer = "kor/katman %d (%s)" % (i + 1, b.get("ad") or "adsiz")
        h = b.get("yukseklik")
        if not h or float(h) <= 0:
            bulgular.append(Bulgu("hata", yer, "katman yuksekligi pozitif olmali"))
        ad = b.get("ad") or ""
        if ad and ad in adlar:
            bulgular.append(Bulgu("uyari", yer,
                                  "ayni ad birden fazla katmanda kullanilmis: '%s'" % ad))
        adlar.add(ad)

        dolgu = b.get("dolgu")
        if dolgu and not _ad_var(spec, dolgu):
            bulgular.append(Bulgu(
                "hata", yer, "tanimsiz dolgu adi: '%s'" % dolgu,
                "Dolgu bir cubuk, plaka, demet ya da malzeme adi olmali."))

        anahtar = b.get("anahtar") or {}
        if anahtar and tur != "kare_kafes":
            bulgular.append(Bulgu(
                "hata", yer,
                "katmana ozel 'anahtar' yalnizca kare_kafes korunda kullanilabilir"))
        for harf, hedef in anahtar.items():
            if not any(harf in satir for satir in (kor.get("harita") or [])):
                bulgular.append(Bulgu(
                    "uyari", yer,
                    "'%s' harfi kor haritasinda hic gecmiyor" % harf))
            if not _ad_var(spec, hedef):
                bulgular.append(Bulgu("hata", yer,
                                      "tanimsiz demet/malzeme adi: '%s'" % hedef))

    if kor.get("yukseklik"):
        toplam = sema.kor_yuksekligi(kor)
        bulgular.append(Bulgu(
            "bilgi", "kor",
            "eksenel katmanlama acikken 'yukseklik' alani (%g cm) yok sayilir; "
            "gecerli yukseklik katman toplamidir (%g cm)"
            % (float(kor["yukseklik"]), toplam or 0.0)))

    # --- fisil katman var mi ---
    if spec["ayarlar"].get("mod", "eigenvalue") == "eigenvalue":
        try:
            aralik = kurucu.aktif_eksenel_aralik(spec)
            toplam = sema.kor_yuksekligi(kor)
            ana = (kor.get("cubuk") or kor.get("demet") or kor.get("plaka")
                   or kor.get("dolgu"))
            fisil_var = any(
                kurucu._spec_fisil_mi(spec, b.get("dolgu") or ana)
                or any(kurucu._spec_fisil_mi(spec, x)
                       for x in (b.get("anahtar") or {}).values())
                for b in katmanlar)
        except Exception:
            aralik, toplam, fisil_var = None, None, True
        if not fisil_var:
            bulgular.append(Bulgu(
                "hata", "kor",
                "hicbir eksenel katmanda fisil malzeme yok -- ozdeger kosusu "
                "baslangic kaynagi bulamaz"))
        elif aralik and toplam:
            aktif = aralik[1] - aralik[0]
            if aktif < toplam:
                bulgular.append(Bulgu(
                    "bilgi", "kor",
                    "aktif yakit yuksekligi %g cm / toplam %g cm "
                    "(z = %g .. %g)" % (aktif, toplam, aralik[0], aralik[1]),
                    "Baslangic kaynagi kutusu ve kontrol cubugu daldirmasi bu "
                    "FISIL araliga gore tanimlidir. Guc dagilimi eksenel mesh'i "
                    "ise hedef CUBUGUN bulundugu araliga gore -- ikisi ayni "
                    "olmak zorunda degil (dogal uranyum blanket fisildir ama "
                    "icinde yakit cubugu yoktur)."))

    # Mutlak guc normalizasyonu uyarisi: distribcell yalnizca HEDEF cubugu
    # kapsar, ama toplam_guc tum modelin gucudur. Katmanlamada fisil ama
    # hedef cubugu icermeyen katmanlar (blanket) varsa onlarin gucu de hedef
    # cubuklara paylastirilmis olur ve W/cm YUKSEK cikar.
    g = spec.get("guc_dagilimi") or {}
    if g.get("var") and g.get("toplam_guc") and g.get("cubuk"):
        try:
            ar = kurucu.aktif_eksenel_aralik(spec)
            cr = kurucu.cubuk_eksenel_aralik(spec, g["cubuk"])
        except Exception:
            ar = cr = None
        if ar and cr and (cr[1] - cr[0]) < (ar[1] - ar[0]) - 1e-9:
            bulgular.append(Bulgu(
                "uyari", "guc_dagilimi",
                "fisil aralik %g cm ama '%s' cubugu yalnizca %g cm boyunca var"
                % (ar[1] - ar[0], g["cubuk"], cr[1] - cr[0]),
                "Guc dagilimi yalnizca bu cubugu sayar; toplam_guc ise tum "
                "modelin gucudur. Aradaki fisil katmanlarin (blanket gibi) gucu "
                "de bu cubuklara paylastirilmis olur ve W/cm YUKSEK cikar. "
                "Mutlak sayilari kullanacaksaniz toplam_guc'u yalnizca bu "
                "cubuklarin uretimi olacak sekilde girin."))

    if any(c.get("tur") == "kontrol" for c in spec.get("cubuklar", [])):
        bulgular.append(Bulgu(
            "bilgi", "kor",
            "kontrol cubugu daldirmasi AKTIF yakit araliginda olculur",
            "%0 = uc aktif bolgenin tepesinde, %100 = dibinde. Modelin toplam "
            "yuksekligi degil."))
    return bulgular


def _ad_var(spec, ad):
    """Ad bir cubuk / plaka / demet / malzeme (ya da bosluk) mu?"""
    return (ad == BOSLUK
            or malzeme_bul(spec, ad) is not None
            or cubuk_bul(spec, ad) is not None
            or plaka_bul(spec, ad) is not None
            or demet_bul(spec, ad) is not None)


def tukenme_kontrol(spec, veri_kontrolu=True):
    """
    Tukenme ayarlari tutarli mi?

    Tukenmenin sessiz hatalari: yarim indirilmis zincir, yanlis spektrumlu
    zincir, hacmi yanlis malzeme (yanma hizi o oranda yanlis olur ve k-eff'te
    iz birakmaz), Xe-135 dengesini kaciran uzun ilk adim.
    """
    from cekirdek import tukenme as _tk
    bulgular = []
    t = spec.get("tukenme") or {}
    if not t.get("var"):
        return bulgular
    yer = "tukenme"

    if spec["ayarlar"].get("mod", "eigenvalue") != "eigenvalue":
        bulgular.append(Bulgu("hata", yer,
                              "tukenme ozdeger (k-eff) modu gerektirir",
                              "Sabit kaynakli tukenme (aktivasyon) bu surumde yok."))

    # --- zincir ---
    zs = _tk.zincir_secimi(spec)
    # Hizli kontrol yalnizca dosyanin SONUNU okur (<1 ms); veri_kontrolu
    # kapaliyken bile yapilir ki arayuz yarim bir zinciri aninda gostersin.
    tamam, mesaj, _n = veri_bilgi.zincir_kontrol(zs["yol"])
    if not tamam:
        bulgular.append(Bulgu("hata", yer, mesaj,
                              "Kaynak ve sha256: ~/nucdata/chain/KAYNAK.txt"))
    if t.get("zincir", "otomatik") != "otomatik" and zs["temel"] != zs["spektrum"]:
        bulgular.append(Bulgu(
            "uyari", yer,
            "%s zincir secildi ama model %s spektrumlu gorunuyor"
            % (zs["temel"], zs["spektrum"]),
            "Termal/hizli zincir yakalama dallanma oranlarini ve fisyon "
            "verimlerini belirler (or. Am241(n,g)->Am242m termalde %8.1, "
            "hizlida %13.2)."))
    if zs["tur"].startswith("casl"):
        bulgular.append(Bulgu(
            "bilgi", yer,
            "basitlestirilmis CASL zinciri: 228 nuklid (tam zincir 3820)",
            "Yaklasik 3 kat hizli; on inceleme icindir. Sonuclari tam zincirle "
            "dogrulayin."))

    # --- guc ve adimlar ---
    p = t.get("guc_yogunlugu")
    if p is None or float(p) <= 0:
        bulgular.append(Bulgu("hata", yer, "guc yogunlugu pozitif olmali [W/gHM]"))
    elif not (1.0 <= float(p) <= 200.0):
        bulgular.append(Bulgu(
            "uyari", yer, "guc yogunlugu %g W/gHM olagan disi" % float(p),
            "Tipik: PWR 38-40, BWR ~25, SFR 50-100 W/gHM. Birim W/gHM'dir, "
            "mutlak guc degil."))
    adimlar = t.get("adimlar") or []
    if not adimlar:
        bulgular.append(Bulgu("hata", yer, "en az bir zaman adimi gerekli"))
    elif any(float(a) <= 0 for a in adimlar):
        bulgular.append(Bulgu("hata", yer, "zaman adimlari pozitif olmali"))
    else:
        birim = t.get("adim_birimi") or "d"
        ilk_gun = float(adimlar[0])
        if birim == "MWd/kg" and p:
            ilk_gun = float(adimlar[0]) * 1000.0 / float(p)
        if ilk_gun > 2.0:
            bulgular.append(Bulgu(
                "uyari", yer,
                "ilk adim %.3g gun -- Xe-135 dengesi (~2 gun) tek adima eziliyor"
                % ilk_gun,
                "Ilk adimlari kisa tutun (or. 0.5 ve 1.5 gun). Xe-135 PWR'da "
                "birkac bin pcm'lik hizli bir dusus yaratir; uzun bir ilk adim "
                "bunu gorunmez kilar."))

    # --- yanabilir malzemeler ve hacimler ---
    try:
        hv = _tk.hacimler(spec)
    except Exception as e:
        hv = None
        bulgular.append(Bulgu("hata", yer, "hacimler hesaplanamadi: %s" % e))
    if hv is not None:
        if not hv:
            bulgular.append(Bulgu("hata", yer,
                                  "modelde yanabilir (fisil) malzeme yok"))
        for ad, v in hv.items():
            if not v["hacim"]:
                bulgular.append(Bulgu(
                    "hata", "tukenme/%s" % ad,
                    "hacim hesaplanamiyor: %s" % v["ayrinti"],
                    "Tukenme KESIN hacim gerektirir: yanlis hacim yanma hizini "
                    "ayni oranda bozar ve k-eff'te iz birakmaz."))
    for ad in t.get("ek_malzemeler") or []:
        if malzeme_bul(spec, ad) is None:
            bulgular.append(Bulgu("hata", yer, "tanimsiz ek malzeme: '%s'" % ad))

    # --- istatistik ---
    a = spec["ayarlar"]
    aktif = int(a.get("cevrim", 0)) - int(a.get("pasif", 0))
    if int(a.get("parcacik", 0)) * max(aktif, 0) < 100000:
        bulgular.append(Bulgu(
            "uyari", yer,
            "aktif istatistik az (%d parcacik x %d cevrim)"
            % (int(a.get("parcacik", 0)), aktif),
            "Tukenme her adimda reaksiyon hizlarini transporttan alir; gurultu "
            "adimdan adima BIRIKIR. Aktif parcacik x cevrim >= 1e5 onerilir."))
    if t.get("malzemeleri_ayir"):
        bulgular.append(Bulgu(
            "bilgi", yer, "cubuk cubuk yanma acik (malzemeleri_ayir)",
            "Her hucre ayri malzeme olur; bellek ve sure hucre sayisiyla artar."))
    return bulgular


def ayar_kontrol(spec):
    """Cevrim/parcacik sayilari ve kaynak tanimi."""
    bulgular = []
    a = spec["ayarlar"]
    cevrim = a.get("cevrim", 0)
    pasif = a.get("pasif", 0)
    parcacik = a.get("parcacik", 0)

    if parcacik <= 0:
        bulgular.append(Bulgu("hata", "ayarlar", "parcacik sayisi pozitif olmali"))
    if cevrim <= 0:
        bulgular.append(Bulgu("hata", "ayarlar", "cevrim sayisi pozitif olmali"))
    if a.get("mod") == "eigenvalue":
        if pasif >= cevrim:
            bulgular.append(Bulgu(
                "hata", "ayarlar",
                "pasif cevrim (%d) toplam cevrimden (%d) az olmali" % (pasif, cevrim)))
        elif pasif < 5:
            bulgular.append(Bulgu(
                "uyari", "ayarlar",
                "pasif cevrim cok az (%d) -- kaynak dagilimi yakinsamamis olabilir" % pasif,
                "Tipik olarak en az 20-50 pasif cevrim kullanilir"))
        elif cevrim - pasif < 20:
            bulgular.append(Bulgu(
                "uyari", "ayarlar",
                "aktif cevrim sayisi az (%d) -- istatistik zayif kalir" % (cevrim - pasif)))
        ent = a.get("entropi_mesh") or {}
        if not ent.get("var"):
            bulgular.append(Bulgu(
                "uyari", "ayarlar",
                "Shannon entropisi kapali -- kaynak dagiliminin yakinsayip "
                "yakinsamadigi olculemez",
                "Yakinsamamis kaynak k-eff'i yanli tahmin ettirir ve bu baska "
                "turlu fark edilmez. Ozdeger hesaplarinda acik tutun."))
        elif any(n <= 0 for n in (ent.get("boyut") or [0])):
            bulgular.append(Bulgu("hata", "ayarlar",
                                  "entropi mesh boyutlari pozitif olmali"))
        if parcacik < 1000:
            bulgular.append(Bulgu(
                "uyari", "ayarlar",
                "cevrim basina parcacik az (%d) -- kaynak yakinsamasi bozulabilir" % parcacik))
    return bulgular


# ============================================================================
# 5. REFERANS TUTARLILIGI
# ============================================================================

def kaynak_kontrol(spec, veri_kontrolu=True):
    """
    Kaynak tanimi: enerji tayfi, acisal dagilim, parcacik turu, siddet.

    Sabit kaynak modunun kendine ozgu tuzaklari var ve hicbiri kosuyu
    durdurmuyor -- sessizce anlamsiz sonuc uretiyorlar:
      * foton kaynagi acik ama foton tasinimi kapali -> hicbir etkilesim yok
      * hicbir tally yok -> kosu hicbir sey uretmez, k-eff de yoktur
      * kaynak enerjisi kutuphane tavaninin ustunde -> kosuda hata
      * nokta kaynak geometrinin disinda -> butun parcaciklar aninda kayip
    """
    bulgular = []
    a = spec["ayarlar"]
    k = a.get("kaynak") or {}
    e = k.get("enerji") or {}
    mod = a.get("mod", "eigenvalue")
    sabit = (mod != "eigenvalue")

    # --- dagilimlar gercekten kurulabiliyor mu ---
    for ad, fn, arg in (("enerji tayfi", _kaynak.enerji_dagilimi, e),
                        ("acisal dagilim", _kaynak.aci_dagilimi, k.get("aci"))):
        try:
            fn(arg)
        except Exception as hata:
            bulgular.append(Bulgu("hata", "kaynak", "%s kurulamadi: %s" % (ad, hata)))

    # --- siddet ---
    kuvvet = k.get("kuvvet")
    if kuvvet is not None and float(kuvvet) <= 0:
        bulgular.append(Bulgu("hata", "kaynak",
                              "kaynak siddeti pozitif olmali (%s)" % kuvvet))

    # --- parcacik turu ---
    parca = k.get("parcacik") or "neutron"
    if parca not in ("neutron", "photon"):
        bulgular.append(Bulgu("hata", "kaynak",
                              "bilinmeyen parcacik turu: %s" % parca))
    elif parca == "photon":
        if mod == "eigenvalue":
            bulgular.append(Bulgu(
                "hata", "kaynak",
                "foton kaynagi ozdeger (k-eff) modunda anlamsiz",
                "Fotonlar fisyon zincirini tasimaz. Foton kaynagi icin modu "
                "'Sabit kaynak' yapin."))
        if veri_kontrolu:
            _, _, foton = _kutuphane_icerigi_foton()
            if foton is not None and not foton:
                bulgular.append(Bulgu(
                    "hata", "kaynak",
                    "foton kaynagi secildi ama kutuphanede foton verisi yok",
                    "cross_sections.xml icinde type='photon' kaydi bulunamadi."))

    # --- enerji tavani ---
    tepe = _kaynak.en_yuksek_enerji(e)
    if tepe is not None and veri_kontrolu and parca == "neutron":
        try:
            nesneler, _, _ = kurucu.malzemeleri_kur(spec)
            nuklidler = set()
            for mat in nesneler.values():
                nuklidler |= set(mat.get_nuclides())
            tavan, sahibi = veri_bilgi.enerji_tavani(sorted(nuklidler))
        except Exception:
            tavan, sahibi = None, None
        if tavan is not None and tepe > tavan:
            bulgular.append(Bulgu(
                "hata", "kaynak",
                "kaynak enerjisi %s, veri tavani %s (%s)"
                % (_kaynak.enerji_metni(tepe), _kaynak.enerji_metni(tavan), sahibi),
                "Tavani belirleyen nuklid modelin icindeki en dusuk ust sinira "
                "sahip olandir. OpenMC kosu sirasinda hata verir."))

    # --- nokta kaynak geometrinin icinde mi ---
    if k.get("tur", "nokta") == "nokta":
        konum = list(k.get("konum") or (0.0, 0.0, 0.0))
        h = sema_kor_yuksekligi(spec["kor"])
        if h and abs(float(konum[2])) >= float(h) / 2.0:
            bulgular.append(Bulgu(
                "hata", "kaynak",
                "nokta kaynak z=%g modelin disinda (yukseklik %g, sinir +/-%g)"
                % (konum[2], h, h / 2.0),
                "Geometri disinda baslayan parcaciklar aninda kaybolur."))

    # --- sabit kaynak moduna ozgu ---
    if sabit:
        if not spec.get("tallyler") and not (spec.get("guc_dagilimi") or {}).get("var"):
            bulgular.append(Bulgu(
                "hata", "ayarlar",
                "sabit kaynak modunda hicbir tally tanimli degil -- kosu hicbir "
                "sonuc uretmez",
                "Sabit kaynak hesabinda k-eff yoktur; ne olculecsekse bir "
                "tally olarak tanimlanmalidir (akı, doz, reaksiyon hizi)."))
        if (a.get("entropi_mesh") or {}).get("var"):
            bulgular.append(Bulgu(
                "bilgi", "ayarlar",
                "Shannon entropisi sabit kaynak modunda kullanilmaz",
                "Entropi fisyon kaynagi dagiliminin yakinsamasini olcer; sabit "
                "kaynakta kaynak zaten sabittir. OpenMC bunu yok sayar."))
        if k.get("tur") == "kutu":
            bulgular.append(Bulgu(
                "uyari", "kaynak",
                "sabit kaynak modunda kutu kaynagi 'yalnizca fisil bolgeler' "
                "kisitiyla orneklenir",
                "Zirhlama probleminde fisil bolge olmayabilir; o durumda OpenMC "
                "ornekleme yapamaz. Nokta kaynak kullanmayi dusunun."))
    else:
        tur = e.get("tur", "watt")
        if tur != "watt":
            bulgular.append(Bulgu(
                "bilgi", "kaynak",
                "ozdeger modunda enerji tayfi ('%s') yalnizca BASLANGIC tahminidir"
                % tur,
                "Pasif cevrimler icinde gercek fisyon tayfiyla degisir; k-eff'i "
                "etkilemez. Tayf asil sabit kaynak modunda belirleyicidir."))
        if (k.get("aci") or {}).get("tur", "izotropik") != "izotropik":
            bulgular.append(Bulgu(
                "bilgi", "kaynak",
                "ozdeger modunda acisal dagilim da yalnizca baslangic tahminidir"))

    return bulgular


def _kutuphane_icerigi_foton():
    """(notron, termal, foton) ad kumeleri; okunamazsa (None, None, None)."""
    notron, termal = _kutuphane_icerigi()
    yol = os.environ.get("OPENMC_CROSS_SECTIONS")
    if not yol or not os.path.exists(yol):
        return notron, termal, None
    try:
        import xml.etree.ElementTree as ET
        kok = ET.parse(yol).getroot()
        foton = {d.get("materials") for d in kok.findall("library")
                 if d.get("type") == "photon"}
        return notron, termal, foton
    except Exception:
        return notron, termal, None


def tally_kontrol(spec):
    """Tally skorlarinin taninip taninmadigini kontrol eder."""
    bulgular = []
    for t in spec.get("tallyler", []):
        yer = "tally:%s" % t.get("ad", "?")
        if not t.get("skorlar"):
            bulgular.append(Bulgu("hata", yer, "en az bir skor secilmeli"))
        for s in t.get("skorlar", []):
            if s not in BILINEN_SKORLAR and not str(s).isdigit():
                bulgular.append(Bulgu(
                    "uyari", yer,
                    "'%s' bilinen skorlar arasinda degil" % s,
                    "OpenMC bu skoru tanimayabilir ve hata KOSU SIRASINDA cikar. "
                    "Liste kuratorludur (OpenMC gecerli skor listesi sunmuyor), "
                    "yeni bir skor kullaniyorsaniz bu uyari yanlis alarm olabilir."))
    return bulgular


def guc_dagilimi_kontrol(spec):
    """Cubuk bazli guc dagilimi ayarlarini kontrol eder."""
    bulgular = []
    g = spec.get("guc_dagilimi") or {}
    if not g.get("var"):
        return bulgular
    yer = "guc dagilimi"

    cubuk_ad = g.get("cubuk")
    c = cubuk_bul(spec, cubuk_ad) if cubuk_ad else None
    if c is None:
        bulgular.append(Bulgu("hata", yer, "hedef cubuk secilmemis ya da tanimsiz: %r"
                              % cubuk_ad))
        return bulgular

    bolge = g.get("bolge")
    if not isinstance(bolge, int) or not (0 <= bolge < len(c["bolgeler"])):
        bulgular.append(Bulgu("hata", yer,
                              "gecersiz bolge numarasi %r (cubukta %d bolge var)"
                              % (bolge, len(c["bolgeler"]))))
    else:
        mal = c["bolgeler"][bolge].get("malzeme")
        m = malzeme_bul(spec, mal) if mal else None
        fisil = False
        if m:
            for b in m.get("bilesim", []):
                isim = str(b.get("isim", ""))
                if isim.startswith(("U", "Pu", "Th")) or b.get("zenginlik"):
                    fisil = True
        if not fisil:
            bulgular.append(Bulgu(
                "uyari", yer,
                "secilen bolgenin malzemesi ('%s') fisil gorunmuyor" % mal,
                "Guc dagilimi genellikle YAKIT bolgesinde olculur (bolge 0). "
                "Zarf ya da sogutucu secildiyse sonuc anlamsiz olur."))

    # --- cubuk bir kafeste tekrarlaniyor mu? ---
    kafeste = False
    for d in spec.get("demetler", []):
        if cubuk_ad in (d.get("anahtar") or {}).values():
            kafeste = True
    if spec["kor"].get("cubuk") == cubuk_ad and not kafeste:
        bulgular.append(Bulgu(
            "hata", yer,
            "'%s' bir kafeste tekrarlanmiyor (kor turu 'tek_cubuk')" % cubuk_ad,
            "Guc dagilimi tekrarlanan hucre ornekleri uzerinden hesaplanir; "
            "tek bir cubukta dagilim yoktur. Bir kafes kurun."))
    elif not kafeste:
        bulgular.append(Bulgu(
            "uyari", yer,
            "'%s' hicbir kafes haritasinda kullanilmiyor" % cubuk_ad,
            "Tekrarlanan ornek yoksa dagilim tek bir degerden ibaret kalir."))

    skor = g.get("skor") or "kappa-fission"
    if skor not in BILINEN_SKORLAR:
        bulgular.append(Bulgu("uyari", yer, "'%s' bilinen skorlar arasinda degil" % skor))
    elif skor not in ("kappa-fission", "fission-q-prompt", "fission-q-recoverable",
                      "heating", "heating-local"):
        bulgular.append(Bulgu(
            "uyari", yer,
            "'%s' bir ENERJI skoru degil" % skor,
            "Guc dagilimi icin enerji birakan bir skor gerekir; standart secim "
            "'kappa-fission'dir. 'fission' yalnizca fisyon SAYISINI verir."))

    # --- eksenel ---
    h = sema_kor_yuksekligi(spec["kor"])
    dilim = int(g.get("eksenel_dilim") or 1)
    if not h:
        bulgular.append(Bulgu(
            "bilgi", yer,
            "model 2B -- F_q hesaplanamaz, yalnizca F_dH verilir",
            "Yerel guc yogunlugu tepesi eksenel sekle baglidir. Kor sekmesinde "
            "aktif yukseklik tanimlayin."))
    elif dilim < 10:
        bulgular.append(Bulgu(
            "uyari", yer,
            "yalnizca %d eksenel dilim -- F_q KUCUK cikar" % dilim,
            "Kaba dilimler eksenel tepeyi ortalar. En az 10-20 dilim kullanin."))

    tg = g.get("toplam_guc")
    if tg is not None:
        if tg <= 0:
            bulgular.append(Bulgu("hata", yer, "toplam guc pozitif olmali"))
        elif not h:
            bulgular.append(Bulgu(
                "uyari", yer,
                "toplam guc verilmis ama model 2B -- lineer guc [W/cm] hesaplanamaz",
                "W/cm icin aktif yukseklik gerekir."))
    return bulgular


def referans_kontrol(spec):
    """Tanimli ama kullanilmayan / kullanilan ama tanimsiz ogeler."""
    from cekirdek.sema import kullanilan_malzemeler
    bulgular = []
    tanimli = {m["ad"] for m in spec["malzemeler"]}
    kullanilan = kullanilan_malzemeler(spec)

    for ad in sorted(kullanilan - tanimli):
        bulgular.append(Bulgu("hata", "malzemeler", "kullanilan ama tanimsiz malzeme: %s" % ad))
    for ad in sorted(tanimli - kullanilan):
        bulgular.append(Bulgu("bilgi", "malzemeler",
                              "tanimli ama modelde kullanilmayan malzeme: %s" % ad))
    return bulgular


# ============================================================================
# 6. TOPLU CALISTIRMA
# ============================================================================

def tum_kontroller(spec, veri_kontrolu=True):
    """
    Tum kontrolleri sirayla calistirir.
    veri_kontrolu=False ise nuklid/kutuphane kontrolu atlanir (hizli mod).
    DONER Bulgu listesi -- once hatalar, sonra uyarilar, sonra bilgiler.
    """
    bulgular = []
    if veri_kontrolu:
        bulgular += veri_kutuphanesi_kontrol()
    bulgular += malzeme_kontrol(spec)
    bulgular += cubuk_kontrol(spec)
    bulgular += kontrol_cubugu_kontrol(spec)
    bulgular += plaka_kontrol(spec)
    bulgular += demet_kontrol(spec)
    bulgular += kor_kontrol(spec)
    bulgular += eksenel_kontrol(spec)
    bulgular += ayar_kontrol(spec)
    bulgular += kaynak_kontrol(spec, veri_kontrolu)
    bulgular += tukenme_kontrol(spec, veri_kontrolu)
    bulgular += tally_kontrol(spec)
    bulgular += guc_dagilimi_kontrol(spec)
    bulgular += referans_kontrol(spec)
    # nuklid kontrolu malzemeleri kurmayi gerektirir; once temel hatalar temiz olmali
    if veri_kontrolu and not hata_var(bulgular):
        bulgular += nuklid_kontrol(spec)

    sira = {"hata": 0, "uyari": 1, "bilgi": 2}
    return sorted(bulgular, key=lambda b: sira[b.seviye])


def ozet(bulgular):
    """Bulgulari '2 hata, 1 uyari, 3 bilgi' seklinde ozetler."""
    say = {"hata": 0, "uyari": 0, "bilgi": 0}
    for b in bulgular:
        say[b.seviye] += 1
    return "%d hata, %d uyari, %d bilgi" % (say["hata"], say["uyari"], say["bilgi"])
