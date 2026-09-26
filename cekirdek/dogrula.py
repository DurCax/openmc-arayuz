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
  10. Bu modelde GECERLI OLMAYAN secimler -- kurallar uygunluk.py'de (arayuz
      ayni kurallarla secenekleri gizler; burada elle yazilmis dosyalar
      yakalanir): sinir kosullari, bu kor turunde kurulmayan alanlar,
      guc dagilimi cubugu, fisil malzeme gerektiren secimler (ozdeger modu,
      kutu kaynagi, tukenme), malzeme rolleri (emici / yakit)
================================================================================
"""

import math
import os

from cekirdek.sema import kor_yuksekligi as sema_kor_yuksekligi
from cekirdek.sema import BOSLUK, malzeme_bul, cubuk_bul, plaka_bul, demet_bul
from cekirdek import altigen, kurucu, veri_bilgi, sema
from cekirdek import kaynak as _kaynak
# "Bu modelde ne gecerli?" kurallarinin TEK kaynagi. Arayuz ayni kurallarla
# secenekleri gizler/suzer; burada ayni kurali ihlal eden (elle yazilmis)
# dosyalar yakalanir. Kural burada TEKRAR YAZILMAZ.
from cekirdek import uygunluk

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
    ({"H", "O"},      {"H"},       "c_H_in_H2O",  "su (H₂O)"),
    ({"H", "O", "B"}, {"H"},       "c_H_in_H2O",  "borlu su"),
    ({"H", "Zr"},     {"H", "Zr"}, "c_H_in_ZrH",  "zirkonyum hidrür"),
    ({"H", "C"},      {"H", "C"},  "c_H_in_CH2",  "polietilen / plastik"),
    ({"C"},           {"C"},       "c_Graphite",  "grafit"),
    ({"Be"},          {"Be"},      "c_Be",        "berilyum"),
    ({"Be", "O"},     {"Be", "O"}, "c_Be_in_BeO", "berilyum oksit"),
    ({"D", "O"},      {"D"},       "c_D_in_D2O",  "ağır su (D₂O)"),
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


# Kullaniciya gorunen adlar (anahtarlar spec'te ASCII kalir).
_PLAKA_ALAN_ADI = {
    "plaka_sayisi": "plaka sayısı", "et_kalinlik": "yakıt (et) kalınlığı",
    "zarf_kalinlik": "zarf kalınlığı", "kanal_kalinlik": "soğutucu kanalı kalınlığı",
    "plaka_genislik": "plaka genişliği",
}
_YON_ADI = {"yan": "yan", "alt": "alt", "ust": "üst"}
_SINIR_ADI = {"reflective": "Yansıtıcı", "vacuum": "Vakum", "white": "Beyaz",
              "periodic": "Periyodik"}
_SPEKTRUM_ADI = {"termal": "termal", "hizli": "hızlı"}


def _kor_turu_adi(tur):
    """Kor turunun sade adi (uygunluk.KOR_TURU_ADLARI); bilinmiyorsa kendisi."""
    return uygunluk.KOR_TURU_ADLARI.get(tur, str(tur))


# Bulgu "yer" kodunun kullaniciya gorunen adi. Kod degismez (sekme eslemesi
# ona bakar); yalnizca listede okunur bir ad gosterilir.
_YER_ETIKETI = [
    ("malzemeler", "Malzemeler"), ("malzeme:", "Malzeme "), ("cubuk:", "Çubuk "),
    ("plaka:", "Plaka elemanı "), ("demet:", "Demet "), ("kor/katman ", "Kor, katman "),
    ("kor", "Kor"), ("ayarlar", "Hesap ayarları"), ("veri kutuphanesi", "Veri kütüphanesi"),
    ("kaynak", "Kaynak"), ("tally:", "Tally "), ("guc dagilimi", "Güç dağılımı"),
    ("guc_dagilimi", "Güç dağılımı"), ("tukenme/", "Tükenme, "), ("tukenme", "Tükenme"),
    ("dogrulama", "Doğrulama"),
]


def yer_etiketi(yer):
    """Bulgu yerinin okunur adi: "malzeme:uo2" -> "Malzeme uo2". Kod degismez."""
    yer = yer or ""
    for onek, ad in _YER_ETIKETI:
        if yer == onek or (onek.endswith((":", "/", " ")) and yer.startswith(onek)):
            return ad + yer[len(onek):]
    return yer


class Bulgu(object):
    """Tek bir dogrulama bulgusu."""

    def __init__(self, seviye, yer, mesaj, oneri=None):
        self.seviye = seviye        # "hata" | "uyari" | "bilgi"
        self.yer = yer              # "malzeme:uo2", "kor", "ayarlar" ...
        self.mesaj = mesaj
        self.oneri = oneri

    def __str__(self):
        im = {"hata": "HATA ", "uyari": "UYARI", "bilgi": "BİLGİ"}[self.seviye]
        s = "[%s] %-22s %s" % (im, yer_etiketi(self.yer), self.mesaj)
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
            "OPENMC_CROSS_SECTIONS ortam değişkeni ayarlı değil",
            "export OPENMC_CROSS_SECTIONS=$HOME/nucdata/.../cross_sections.xml"))
    elif not os.path.exists(yol):
        bulgular.append(Bulgu(
            "hata", "veri kutuphanesi",
            "cross_sections.xml bulunamadı: %s" % yol,
            "Yolu denetleyin ya da nükleer veri kütüphanesini indirin."))
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
                              "cross_sections.xml okunamadı; nüklid denetimi atlandı"))
        return bulgular

    try:
        nesneler, _, _ = kurucu.malzemeleri_kur(spec)
    except Exception as e:
        bulgular.append(Bulgu("hata", "malzemeler",
                              "malzemeler kurulamadı: %s" % e))
        return bulgular

    for ad, mat in nesneler.items():
        try:
            istenen = set(mat.get_nuclides())
        except Exception as e:
            bulgular.append(Bulgu("uyari", "malzeme:%s" % ad,
                                  "nüklid listesi çıkarılamadı: %s" % e))
            continue
        eksik = sorted(istenen - notron)
        if eksik:
            bulgular.append(Bulgu(
                "hata", "malzeme:%s" % ad,
                "veri kütüphanesinde olmayan nüklid: %s" % ", ".join(eksik),
                "Bileşimi değiştirin ya da bu nüklidleri içeren bir kütüphane kullanın."))
        for s in (malzeme_bul(spec, ad) or {}).get("sab", []):
            if s not in termal:
                bulgular.append(Bulgu(
                    "hata", "malzeme:%s" % ad,
                    "termal saçılma verisi (S(α,β)) kütüphanede yok: %s" % s,
                    "Kütüphanede %d S(α,β) kaydı var; listeden birini seçin." % len(termal)))
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
                                  "aynı ad %d kez tanımlanmış" % adlar.count(ad)))
    if BOSLUK in adlar:
        bulgular.append(Bulgu("hata", "malzemeler",
                              "'%s' ayrılmış bir addır (Boş, madde yok); malzeme adı olarak kullanılamaz" % BOSLUK))

    for m in spec["malzemeler"]:
        yer = "malzeme:%s" % m["ad"]
        if not m.get("bilesim"):
            bulgular.append(Bulgu("hata", yer, "bileşim boş"))
            continue
        yog = (m.get("yogunluk") or {}).get("deger")
        if yog is None:
            bulgular.append(Bulgu("hata", yer, "yoğunluk verilmemiş"))
        elif yog <= 0:
            bulgular.append(Bulgu("hata", yer, "yoğunluk sıfırdan büyük olmalı: %s" % yog))

        for b in m["bilesim"]:
            # Kurucu "nuklid" disindaki her turu element sayar ve birimi
            # OpenMC'ye aynen verir: "nuclide"/"atom" gibi bir yazim ancak
            # kosuda patlar ya da nuklidi element diye ekler.
            if b.get("tur", "element") not in ("element", "nuklid"):
                bulgular.append(Bulgu(
                    "hata", yer,
                    "'%s' satırının türü geçersiz: %s" % (b.get("isim"), b.get("tur")),
                    "Tür 'element' (doğal element) ya da 'nuklid' (izotop) olmalı."))
            if b.get("birim", "ao") not in ("ao", "wo"):
                bulgular.append(Bulgu(
                    "hata", yer,
                    "'%s' satırının birimi geçersiz: %s" % (b.get("isim"), b.get("birim")),
                    "Birim 'ao' (atom oranı) ya da 'wo' (ağırlık oranı) olmalı."))
            if b.get("miktar", 0) <= 0:
                bulgular.append(Bulgu("hata", yer,
                                      "'%s' miktarı sıfırdan büyük olmalı: %s"
                                      % (b.get("isim"), b.get("miktar"))))
            z = b.get("zenginlik")
            # OpenMC zenginligi yalnizca U ELEMENTINE uygular: baska bir
            # elementte kosu sirasinda reddeder ("Unable to use enrichment for
            # element O which is not uranium"); nuklid satirinda kurucu onu
            # sessizce yok sayar. Ikisi de kosudan ONCE yakalanmali.
            if z is not None and b.get("tur", "element") == "nuklid":
                bulgular.append(Bulgu(
                    "hata", yer,
                    "'%s' nüklid satırında zenginlik tanımlı — nüklidde zenginlik "
                    "yok sayılır" % b.get("isim"),
                    "Zenginlik yalnızca U elementi satırında kullanılabilir. "
                    "İzotopları nüklid olarak giriyorsanız miktarları doğrudan verin."))
            elif z is not None and b.get("isim") != "U":
                bulgular.append(Bulgu(
                    "hata", yer,
                    "'%s' elementinde zenginlik tanımlı — zenginlik yalnızca U "
                    "elementinde kullanılabilir" % b.get("isim"),
                    "OpenMC koşu sırasında reddeder (\"Unable to use enrichment for "
                    "element %s which is not uranium\"). Zenginliği U satırına "
                    "taşıyın ya da bu satırdan silin." % b.get("isim")))
            if z is not None and not (0.0 < z < 100.0):
                bulgular.append(Bulgu("hata", yer,
                                      "'%s' zenginliği %%0–100 aralığında olmalı: %s"
                                      % (b["isim"], z)))
            elif z is not None and b.get("isim") == "U" and z > 5.0:
                bulgular.append(Bulgu(
                    "uyari", yer,
                    "U zenginliği %%%.2f — OpenMC'nin zenginlik kısayolu U234/U235 "
                    "kütle oranını sabit 0.008 varsayar; bu yalnızca düşük "
                    "zenginliklerde geçerlidir" % z,
                    "Bileşimi nüklid bazında verin (U234/U235/U238) ya da sonucun "
                    "U234'e duyarlılığını kabul edin."))

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
            "%s görünümünde ama termal saçılma verisi (S(α,β)) eklenmemiş" % tanim,
            "Termal spektrumda k'yi yüzde mertebesinde kaydırır. Malzemeler "
            "sekmesinde S(α,β) olarak %s ekleyin." % onerilen)]
    # Kurala uymayan ama hidrojen iceren yogun malzeme -- yine de uyar
    if "H" in elemanlar:
        return [Bulgu(
            "uyari", yer,
            "yoğun fazda hidrojen var ama termal saçılma verisi (S(α,β)) eklenmemiş",
            "Hidrojenin bağlı olduğu faza uygun bir S(α,β) seçin "
            "(ör. c_H_in_H2O, c_H_in_ZrH, c_H_in_CH2).")]
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
                                  "en az iki bölge gerekir (iç bölge + dış dolgu)"))
            continue
        if bolgeler[-1].get("r") is not None:
            bulgular.append(Bulgu(
                "hata", yer, "son bölgenin yarıçapı boş olmalı",
                "Son bölge çubuğun dışıdır ve hücrenin geri kalanını doldurur."))
        yaricaplar = [b.get("r") for b in bolgeler[:-1]]
        for i, r in enumerate(yaricaplar):
            if r is None or r <= 0:
                bulgular.append(Bulgu("hata", yer,
                                      "%d. bölgenin yarıçapı sıfırdan büyük olmalı: %s" % (i + 1, r)))
        temiz = [r for r in yaricaplar if isinstance(r, (int, float))]
        for i in range(len(temiz) - 1):
            if temiz[i] >= temiz[i + 1]:
                bulgular.append(Bulgu(
                    "hata", yer,
                    "yarıçaplar artan sırada olmalı: r%d = %.5f ≥ r%d = %.5f"
                    % (i + 1, temiz[i], i + 2, temiz[i + 1])))
        for i, b in enumerate(bolgeler):
            ad = b.get("malzeme")
            if ad is None:
                # Kurucu None'u sessizce bosluk (void) kurar; bilincli bosluk
                # "bosluk" ile secilir.
                bulgular.append(Bulgu(
                    "hata", yer, "%d. bölgenin malzemesi seçilmemiş" % (i + 1),
                    "Bir malzeme seçin; bölge bilerek boş bırakılacaksa "
                    "'Boş (madde yok)' seçin."))
            elif ad != BOSLUK and malzeme_bul(spec, ad) is None:
                bulgular.append(Bulgu("hata", yer, "tanımsız malzeme: %s" % ad))
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
                "kontrol çubuğu 3B model gerektirir (kor yüksekliği tanımsız)",
                "Eksenel bir uç konumu olmadan daldırma tanımlanamaz. "
                "Kor sekmesinde aktif yükseklik tanımlayın."))
        d = c.get("daldirma")
        if d is None or not (0.0 <= float(d) <= 100.0):
            bulgular.append(Bulgu("hata", yer,
                                  "daldırma %%0–%%100 arasında olmalı: %s" % d))
        ix = c.get("emici_bolge")
        if not isinstance(ix, int) or not (0 <= ix < len(c.get("bolgeler", []))):
            bulgular.append(Bulgu("hata", yer,
                                  "geçersiz emici bölge: %s"
                                  % (ix + 1 if isinstance(ix, int) else "seçilmemiş")))
        else:
            mal = c["bolgeler"][ix].get("malzeme")
            m = malzeme_bul(spec, mal) if mal else None
            if m:
                # "emici" rolu uygunluk'tan: eskiden burada ayri bir element
                # listesi vardi; "Gd157" nuklidi ya da Dy2TiO5 yanlis alarm
                # veriyordu, borlu su ise (2000 ppm) emici sayiliyordu.
                sogurucu = "emici" in uygunluk.tek_malzeme_rolleri(m)
                if not sogurucu:
                    bulgular.append(Bulgu(
                        "uyari", yer,
                        "emici bölgenin malzemesi ('%s') güçlü bir nötron "
                        "emici içermiyor" % mal,
                        "Kontrol malzemeleri genellikle B4C, Ag-In-Cd, Gd2O3 ya "
                        "da Hf içerir."))
        iz = c.get("izleyici_malzeme")
        if iz is None:
            bulgular.append(Bulgu(
                "uyari", yer,
                "izleyici malzeme seçilmemiş — çubuk çekildiğinde yeri boş (madde yok) kalır",
                "Çekilen çubuğun yerini genellikle soğutucu doldurur; bilerek boş "
                "bırakılacaksa 'Boş (madde yok)' seçin."))
        elif iz != BOSLUK and malzeme_bul(spec, iz) is None:
            bulgular.append(Bulgu("hata", yer, "tanımsız izleyici malzeme: %s" % iz))
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
                                      "%s sıfırdan büyük olmalı: %s"
                                      % (_PLAKA_ALAN_ADI[alan], deger)))
        for alan in ("et_malzeme", "zarf_malzeme", "sogutucu"):
            ad = p.get(alan)
            if ad is None:
                bulgular.append(Bulgu(
                    "hata", yer,
                    "%s seçilmemiş" % {"et_malzeme": "yakıt (et) malzemesi",
                                        "zarf_malzeme": "zarf malzemesi",
                                        "sogutucu": "soğutucu"}[alan],
                    "Seçilmeyen malzeme boş (madde yok) kurulurdu."))
            elif ad != BOSLUK and malzeme_bul(spec, ad) is None:
                bulgular.append(Bulgu("hata", yer,
                                      "%s için tanımsız malzeme: %s"
                                      % (_PLAKA_ALAN_ADI[alan], ad)))
    return bulgular


def demet_kontrol(spec):
    """Kafes haritasi boyutlari ve harf cozumlemesi."""
    bulgular = []
    for d in spec.get("demetler", []):
        yer = "demet:%s" % d["ad"]
        harita = d.get("harita") or []
        if not harita:
            bulgular.append(Bulgu("hata", yer, "harita boş"))
            continue
        if d.get("tur") == "kare":
            nx, ny = d["boyut"]
            if len(harita) != ny:
                bulgular.append(Bulgu(
                    "hata", yer,
                    "harita %d satır ama boyut %d satır bekliyor" % (len(harita), ny)))
            for i, satir in enumerate(harita):
                if len(satir) != nx:
                    bulgular.append(Bulgu(
                        "hata", yer,
                        "%d. satır %d karakter ama %d bekleniyor" % (i + 1, len(satir), nx)))
        if d.get("tur") == "altigen":
            halka = d.get("halka_sayisi") or d.get("boyut", [0])[0]
            if not halka or halka < 1:
                bulgular.append(Bulgu("hata", yer, "halka sayısı en az 1 olmalı"))
            else:
                beklenen = altigen.halka_uzunluklari(halka)
                if len(harita) != len(beklenen):
                    bulgular.append(Bulgu(
                        "hata", yer,
                        "%d halka bekleniyor, haritada %d satır var"
                        % (len(beklenen), len(harita)),
                        "Halkalar dıştan içe sıralanır; yarıçapı k olan halkada "
                        "6k öğe, merkezde 1 öğe bulunur."))
                else:
                    for i, (satir, uzunluk) in enumerate(zip(harita, beklenen)):
                        if len(satir) != uzunluk:
                            bulgular.append(Bulgu(
                                "hata", yer,
                                "%d. halka (yarıçap %d) %d öğe bekliyor, %d var"
                                % (i + 1, halka - 1 - i, uzunluk, len(satir))))
            if d.get("yonelim", "y") not in ("x", "y"):
                bulgular.append(Bulgu("hata", yer,
                                      "yönelim 'x' ya da 'y' olmalı: %s" % d.get("yonelim")))
        if d.get("adim", 0) <= 0:
            bulgular.append(Bulgu("hata", yer, "adım sıfırdan büyük olmalı"))

        kullanilan = {h for satir in harita for h in satir}
        tanimli = set((d.get("anahtar") or {}).keys())
        for h in sorted(kullanilan - tanimli):
            bulgular.append(Bulgu("hata", yer,
                                  "haritada tanımsız harf: '%s'" % h,
                                  "Harfi demetin anahtar listesine ekleyin."))
        for h in sorted(tanimli - kullanilan):
            bulgular.append(Bulgu("bilgi", yer,
                                  "anahtarda tanımlı ama haritada kullanılmayan harf: '%s'" % h))
        for h, hedef in (d.get("anahtar") or {}).items():
            if (cubuk_bul(spec, hedef) is None and plaka_bul(spec, hedef) is None
                    and demet_bul(spec, hedef) is None
                    and hedef != BOSLUK and malzeme_bul(spec, hedef) is None):
                bulgular.append(Bulgu("hata", yer,
                                      "'%s' harfi tanımsız bir ada işaret ediyor: %s" % (h, hedef)))
        bulgular += _kafes_icerik_kontrol(
            spec, yer, d.get("adim"), d.get("tur", "kare"),
            [(d.get("anahtar") or {}).get(h) for h in sorted(kullanilan)])
    return bulgular


def _cubuk_dis_capi(c):
    """Cubugun dis capi: 2 x en buyuk SONLU bolge yaricapi (son bolge 'disarisi')."""
    r = [b.get("r") for b in (c.get("bolgeler") or [])
         if isinstance(b.get("r"), (int, float)) and b.get("r") > 0]
    return 2.0 * max(r) if r else None


def _kafes_olculeri(d):
    """
    Ic ice yerlestirilen kafesin olculeri: (zarf_x, zarf_y, en_dar_genislik).

    Zarf kurucu.py'nin kullandigi olcudur (kare: adim x n; altigen:
    altigen.kapsayan_olcu). En dar genislik altigende kurucu._altigen_sinir'in
    duz yuzden duz yuze olcusudur: (halka-1) * adim * sqrt(3) + adim.
    """
    adim = float(d.get("adim") or 0.0)
    if d.get("tur") == "altigen":
        halka = d.get("halka_sayisi") or (d.get("boyut") or [1])[0] or 1
        gx, gy = altigen.kapsayan_olcu(halka, adim, d.get("yonelim", "y"))
        return gx, gy, (halka - 1) * adim * math.sqrt(3.0) + adim
    nx, ny = (d.get("boyut") or [1, 1])[:2]
    return adim * nx, adim * ny, adim * min(nx, ny)


def _kafes_icerik_kontrol(spec, yer, adim, kafes_turu, hedefler):
    """
    Kafes adimi, konumlara yerlestirilen iceriklerden kucuk mu?

    Cubuk: dis cap > adim ise cubuk komsu hucreye TASAR. OpenMC bunu hata
    saymaz -- kafes hucresi cubugu sessizce keser. Ic ice kafes: zarfi hucreye
    sigmiyorsa dis halkadaki cubuklar kesilir.
      kare hucre (adim x adim)  : zarfin iki boyutu da adima sigmali
      altigen hucre (duz yuz = adim): en dar genislik adimdan buyukse hicbir
                                    yonelimde sigmaz
    Yalnizca KESIN tasmalar raporlanir (yanlis alarm yerine sessiz kalir).
    """
    bulgular = []
    try:
        P = float(adim or 0.0)
    except (TypeError, ValueError):
        return bulgular
    if P <= 0:
        return bulgular
    pay = P * (1.0 + 1e-9)
    gorulen = set()
    for hedef in hedefler:
        if not hedef or hedef in gorulen:
            continue
        gorulen.add(hedef)
        c = cubuk_bul(spec, hedef)
        if c is not None:
            cap = _cubuk_dis_capi(c)
            if cap and cap > pay:
                bulgular.append(Bulgu(
                    "hata", yer,
                    "'%s' çubuğunun dış çapı (%.5f cm) kafes adımından (%.5f cm) "
                    "büyük — çubuk komşu hücreye taşar" % (hedef, cap, P),
                    "OpenMC bunu hata saymaz: kafes hücresi çubuğu sessizce keser. "
                    "Adımı büyütün ya da çubuk yarıçaplarını küçültün."))
            continue
        ic = demet_bul(spec, hedef)
        if ic is not None:
            gx, gy, dar = _kafes_olculeri(ic)
            gerekli = max(gx, gy) if kafes_turu != "altigen" else dar
            if gerekli > pay:
                bulgular.append(Bulgu(
                    "hata", yer,
                    "iç içe demet '%s' (%.4f × %.4f cm) demet adımına (%.5f cm) "
                    "sığmıyor" % (hedef, gx, gy, P),
                    "Kafes hücresi içteki demeti keser; dış halkadaki çubuklar "
                    "sessizce kaybolur. Dış demetin adımı en az %.5f cm olmalı."
                    % gerekli))
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
                              "bilinmeyen kor türü: %s (geçerli: %s)"
                              % (tur, ", ".join(gecerli))))
        return bulgular

    if tur == "tek_cubuk":
        if not kor.get("cubuk"):
            bulgular.append(Bulgu("hata", "kor", "çubuk seçilmemiş"))
        elif cubuk_bul(spec, kor["cubuk"]) is None:
            bulgular.append(Bulgu("hata", "kor", "tanımsız çubuk: %s" % kor["cubuk"]))
        if kor.get("adim", 0) <= 0:
            bulgular.append(Bulgu("hata", "kor", "hücre adımı sıfırdan büyük olmalı"))
        else:
            c = cubuk_bul(spec, kor.get("cubuk") or "")
            if c:
                dis_r = max([b["r"] for b in c["bolgeler"] if b.get("r")] or [0])
                if dis_r * 2 > kor["adim"]:
                    bulgular.append(Bulgu(
                        "hata", "kor",
                        "çubuğun dış çapı (%.5f cm) hücre adımından (%.5f cm) büyük"
                        % (dis_r * 2, kor["adim"])))
    elif tur == "tek_demet":
        if not kor.get("demet") or demet_bul(spec, kor.get("demet")) is None:
            bulgular.append(Bulgu("hata", "kor", "tanımsız demet: %s" % kor.get("demet")
                                  if kor.get("demet") else "demet seçilmemiş"))
    elif tur == "tek_plaka":
        if not kor.get("plaka") or plaka_bul(spec, kor.get("plaka")) is None:
            bulgular.append(Bulgu("hata", "kor", "tanımsız plaka elemanı: %s" % kor.get("plaka")
                                  if kor.get("plaka") else "plaka elemanı seçilmemiş"))
    elif tur == "tamburlu":
        from cekirdek import tambur as _t
        R_kor = kor.get("kor_yaricap") or 0.0
        yans = kor.get("yansitici") or {}
        kal = yans.get("kalinlik") or 0.0
        if R_kor <= 0:
            bulgular.append(Bulgu("hata", "kor", "kor yarıçapı sıfırdan büyük olmalı"))
        if kal <= 0:
            bulgular.append(Bulgu("hata", "kor",
                                  "tamburlu korda yansıtıcı kuşak kalınlığı sıfırdan büyük olmalı"))
        if not yans.get("malzeme") or yans["malzeme"] == BOSLUK:
            bulgular.append(Bulgu("uyari", "kor",
                                  "yansıtıcı kuşağın malzemesi seçilmemiş (boş, madde yok)"))
        dolgu = kor.get("dolgu")
        if not dolgu:
            bulgular.append(Bulgu("hata", "kor", "kor dolgusu seçilmemiş"))
        elif (dolgu != BOSLUK and cubuk_bul(spec, dolgu) is None
              and demet_bul(spec, dolgu) is None
              and malzeme_bul(spec, dolgu) is None):
            bulgular.append(Bulgu("hata", "kor",
                                  "kor dolgusu tanımsız: %s" % dolgu))
        t = kor.get("tambur") or {}
        if int(t.get("sayi") or 0) <= 0:
            bulgular.append(Bulgu(
                "bilgi", "kor",
                "tambur sayısı 0 — kontrol tamburu olmadan düz yansıtıcı kuşak"))
        else:
            for h in _t.geometri_kontrol(t, R_kor, kal):
                bulgular.append(Bulgu("hata", "kor", h))
            for anahtar, etiket in (("govde_malzeme", "tambur gövdesi"),
                                    ("emici_malzeme", "tambur emicisi")):
                ad = t.get(anahtar)
                if not ad:
                    bulgular.append(Bulgu("hata", "kor",
                                          "%s malzemesi seçilmemiş" % etiket))
                elif ad != BOSLUK and malzeme_bul(spec, ad) is None:
                    bulgular.append(Bulgu("hata", "kor",
                                          "%s için tanımsız malzeme: %s" % (etiket, ad)))
            em = malzeme_bul(spec, t.get("emici_malzeme") or "")
            if em:
                if "emici" not in uygunluk.tek_malzeme_rolleri(em):
                    bulgular.append(Bulgu(
                        "uyari", "kor",
                        "tambur emicisi ('%s') güçlü bir nötron emici içermiyor"
                        % t.get("emici_malzeme")))
            d = t.get("donme")
            if d is None or not (-360.0 <= float(d) <= 360.0):
                bulgular.append(Bulgu("hata", "kor",
                                      "tambur dönme açısı −360…360° aralığında olmalı: %s" % d))
            if not sema_kor_yuksekligi(kor):
                bulgular.append(Bulgu(
                    "bilgi", "kor",
                    "tamburlu kor 2B — eksenel sızıntı yok, k-eff olduğundan yüksek çıkar",
                    "Gerçekçi bir tambur değeri için Kor sekmesinde aktif yükseklik tanımlayın."))

    elif tur == "kuresel":
        kabuklar = kor.get("kabuklar") or []
        if not kabuklar:
            bulgular.append(Bulgu("hata", "kor", "küresel düzenekte en az bir kabuk gerekir"))
        for i, k in enumerate(kabuklar):
            if not k.get("r") or k["r"] <= 0:
                bulgular.append(Bulgu("hata", "kor",
                                      "%d. kabuğun yarıçapı sıfırdan büyük olmalı" % (i + 1)))
            ad = k.get("malzeme")
            if ad and ad != BOSLUK and malzeme_bul(spec, ad) is None:
                bulgular.append(Bulgu("hata", "kor",
                                      "%d. kabukta tanımsız malzeme: %s" % (i + 1, ad)))
        r = [k.get("r") for k in kabuklar if k.get("r")]
        for i in range(len(r) - 1):
            if r[i] >= r[i + 1]:
                bulgular.append(Bulgu(
                    "hata", "kor",
                    "kabuk yarıçapları artan sırada olmalı: r%d = %.5f ≥ r%d = %.5f"
                    % (i + 1, r[i], i + 2, r[i + 1])))
        if kor.get("yukseklik"):
            bulgular.append(Bulgu(
                "hata", "kor",
                "küresel düzenekte yükseklik tanımlanamaz (%g cm)" % float(kor["yukseklik"]),
                "Küre geometrisi kabuk yarıçaplarıyla tamamen belirlenir; yükseklik "
                "kaynak kutusuna, entropi ağına ve tally ağlarına girer. Kor "
                "sekmesinde küresel tür seçiliyken alan temizlenir."))
        if kor.get("sinir", {}).get("yan") == "reflective":
            bulgular.append(Bulgu(
                "uyari", "kor",
                "küresel düzenekte dış sınır Yansıtıcı (reflective) — çıplak (bare) bir "
                "kritiklik düzeneği modelliyorsanız Vakum (vacuum) olmalı",
                "Yansıtıcı sınır sonsuz bir ortam demektir; kritik küre "
                "düzenekleri çıplaktır (Vakum)."))

    elif tur == "kare_kafes":
        harita = kor.get("harita") or []
        if not harita:
            bulgular.append(Bulgu("hata", "kor", "kor haritası boş"))
        else:
            nx, ny = kor["boyut"]
            if len(harita) != ny:
                bulgular.append(Bulgu("hata", "kor",
                                      "harita %d satır, boyut %d bekliyor" % (len(harita), ny)))
            for i, satir in enumerate(harita):
                if len(satir) != nx:
                    bulgular.append(Bulgu("hata", "kor",
                                          "%d. satır %d karakter, %d bekleniyor"
                                          % (i + 1, len(satir), nx)))
            kullanilan = {h for satir in harita for h in satir}
            tanimli = set((kor.get("anahtar") or {}).keys())
            for h in sorted(kullanilan - tanimli):
                bulgular.append(Bulgu("hata", "kor", "haritada tanımsız harf: '%s'" % h))
            bulgular += _kafes_icerik_kontrol(
                spec, "kor", kor.get("adim"), "kare",
                [(kor.get("anahtar") or {}).get(h) for h in sorted(kullanilan)])

    # --- sinir kosullari ---
    sinir = kor.get("sinir") or {}
    gecerli_bc = ("reflective", "vacuum", "periodic", "white")
    for yon in ("yan", "alt", "ust"):
        bc = sinir.get(yon)
        if bc and bc not in gecerli_bc:
            bulgular.append(Bulgu("hata", "kor",
                                  "geçersiz sınır koşulu (%s): %s" % (_YON_ADI.get(yon, yon), bc)))
    # Hangi yuzeyde hangi sinirin gecerli oldugu uygunluk.sinir_secenekleri'nde
    # (arayuz de listeyi oradan alir). Burada yalnizca ihlal raporlanir.
    yan = sinir.get("yan")
    if yan in gecerli_bc and yan not in uygunluk.sinir_secenekleri(spec, "yan"):
        yy = uygunluk.yan_yuzey(spec)
        if yy == "altigen":
            yuzey = "altıgen bir prizma"
            oneri = ("Bu sürüm periyodik sınırı yalnızca kare kesitte (x/y düzlem "
                     "çiftleri) sunuyor. Simetrik bir demette sonsuz kafes için "
                     "Yansıtıcı (reflective) sınır aynı k'yı verir.")
        else:
            yuzey = {"kure": "bir küre", "silindir": "bir silindir"}.get(yy, "düzlemsel değil")
            oneri = ("OpenMC periyodik yüzeyin eşini bulamaz (\"Found only one "
                     "periodic surface without a specified partner\") ve koşu "
                     "başlamadan durur. Yansıtıcı ya da Vakum seçin.")
        bulgular.append(Bulgu(
            "hata", "kor",
            "Periyodik (periodic) sınır yalnızca düzlemsel sınırlarda (x/y düzlem "
            "çiftleri) kullanılabilir — bu kor türünün yan yüzeyi %s" % yuzey, oneri))
    for yon in ("alt", "ust"):
        bc = sinir.get(yon)
        if bc not in gecerli_bc:
            continue
        secenek = uygunluk.sinir_secenekleri(spec, yon)
        if not secenek:
            # 2B modelde z yuzeyi kurulmaz; kurede eksen yoktur (orada hic
            # soylenmez -- kabuk yuzeyi tek sinirdir).
            if tur != "kuresel" and bc != "reflective":
                bulgular.append(Bulgu(
                    "bilgi", "kor",
                    "model 2B — %s sınır koşulu (%s) yok sayılır" % (_YON_ADI.get(yon, yon), _SINIR_ADI.get(bc, bc)),
                    "2B model eksenel yönde sonsuzdur (yansıtıcı alt/üst ile "
                    "eşdeğer). Eksenel sızıntı için Kor sekmesinde yükseklik "
                    "tanımlayın."))
            continue
        if bc in secenek:
            continue
        # buraya yalnizca periodic duser
        karsi = "ust" if yon == "alt" else "alt"
        if sinir.get(karsi) != "periodic":
            bulgular.append(Bulgu(
                "hata", "kor",
                "%s sınır Periyodik (periodic) ama %s sınır değil — periyodik yüzeyin "
                "eşi yok" % (_YON_ADI.get(yon, yon).capitalize(), _YON_ADI.get(karsi, karsi)),
                "OpenMC koşu başlamadan durur (\"Found only one periodic surface "
                "without a specified partner\"). Alt/üst için Yansıtıcı ya da "
                "Vakum seçin."))
        elif yon == "alt":
            bulgular.append(Bulgu(
                "uyari", "kor",
                "alt ve üst sınır Periyodik (periodic) — korun tepesi dibine bağlanır",
                "Sonlu yükseklikteki bir korda eksenel periyodiklik fiziksel "
                "değildir (üst yansıtıcıdan çıkan nötron alt yansıtıcıya girer). "
                "Eksenel simetri için Yansıtıcı sınır kullanın; arayüz bu seçeneği "
                "sunmaz."))

    # --- bu kor turunde KURULMAYAN alanlar (elle yazilmis dosyalar) ---
    alanlar = uygunluk.kor_alanlari(tur)
    yans = kor.get("yansitici") or {}
    if yans.get("var") and "yansitici" not in alanlar:
        bulgular.append(Bulgu(
            "uyari", "kor",
            "'%s' kor türünde yansıtıcı kuşak kurulmaz — dosyada açık ama "
            "yok sayılır" % _kor_turu_adi(tur),
            "Yansıtıcı kuşak yalnızca tek yakıt demeti ve kare haritalı tam korda "
            "(isteğe bağlı) ve tamburlu korda (zorunlu) kurulur. Model "
            "yansıtıcısız çalışır."))
    artik = [alan for alan in sema.KOR_TURE_OZGU
             if alan not in alanlar and alan not in sema.KOR_KORUNAN
             and alan != "yansitici"
             and kor.get(alan, sema.VARSAYILAN_KOR[alan]) != sema.VARSAYILAN_KOR[alan]]
    if artik:
        bulgular.append(Bulgu(
            "bilgi", "kor",
            "'%s' kor türünde kullanılmayan alanlar dolu: %s — yok sayılır"
            % (_kor_turu_adi(tur), ", ".join(artik)),
            "Başka bir kor türünden kalmış olabilir; kurucu bu alanlara bakmaz."))
    if sinir.get("yan") == "vacuum" and tur in ("tek_cubuk", "tek_demet"):
        bulgular.append(Bulgu(
            "uyari", "kor",
            "tek hücre/demet modelinde yan sınır Vakum (vacuum) — sızıntı sonsuz "
            "kafes varsayımını bozar",
            "Sonsuz kafes (k∞) istiyorsanız Yansıtıcı (reflective) sınır kullanın."))
    # Kuresel duzenekte "yukseklik" diye bir kavram yoktur; kabuk yaricaplari
    # geometriyi tamamen belirler. Orada 2B uyarisi vermek yanlis olurdu.
    if not sema_kor_yuksekligi(kor) and kor.get("tur") != "kuresel":
        bulgular.append(Bulgu(
            "bilgi", "kor",
            "yükseklik verilmemiş — model eksenel yönde sonsuz (2B) kabul ediliyor"))
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
            "eksenel katmanlar '%s' kor türünde desteklenmiyor" % _kor_turu_adi(tur),
            "Destekleyen türler: %s. Küresel düzenekte eksen kavramı yoktur; "
            "orada katmanı eş merkezli kabuklarla kurun."
            % ", ".join(_kor_turu_adi(x) for x in sema.EKSENEL_DESTEKLI)))
        return bulgular

    katmanlar = eks.get("bolgeler") or []
    if not katmanlar:
        bulgular.append(Bulgu("hata", "kor",
                              "eksenel katmanlar açık ama hiç katman tanımlı değil"))
        return bulgular

    adlar = set()
    for i, b in enumerate(katmanlar):
        yer = "kor/katman %d (%s)" % (i + 1, b.get("ad") or "adsız")
        h = b.get("yukseklik")
        if not h or float(h) <= 0:
            bulgular.append(Bulgu("hata", yer, "katman yüksekliği sıfırdan büyük olmalı"))
        ad = b.get("ad") or ""
        if ad and ad in adlar:
            bulgular.append(Bulgu("uyari", yer,
                                  "aynı ad birden fazla katmanda kullanılmış: '%s'" % ad))
        adlar.add(ad)

        dolgu = b.get("dolgu")
        if dolgu and not _ad_var(spec, dolgu):
            bulgular.append(Bulgu(
                "hata", yer, "tanımsız dolgu adı: '%s'" % dolgu,
                "Dolgu bir çubuk, plaka elemanı, demet ya da malzeme adı olmalı."))

        anahtar = b.get("anahtar") or {}
        if anahtar and tur != "kare_kafes":
            bulgular.append(Bulgu(
                "hata", yer,
                "katmana özel harf eşlemesi yalnızca kare haritalı tam korda kullanılabilir"))
        for harf, hedef in anahtar.items():
            if not any(harf in satir for satir in (kor.get("harita") or [])):
                bulgular.append(Bulgu(
                    "uyari", yer,
                    "'%s' harfi kor haritasında hiç geçmiyor" % harf))
            if not _ad_var(spec, hedef):
                bulgular.append(Bulgu("hata", yer,
                                      "tanımsız demet/malzeme adı: '%s'" % hedef))

    if kor.get("yukseklik"):
        toplam = sema.kor_yuksekligi(kor)
        bulgular.append(Bulgu(
            "bilgi", "kor",
            "eksenel katmanlar açıkken yükseklik alanı (%g cm) yok sayılır; "
            "geçerli yükseklik katmanların toplamıdır (%g cm)"
            % (float(kor["yukseklik"]), toplam or 0.0)))

    # --- fisil katman var mi ---
    if spec["ayarlar"].get("mod", "eigenvalue") == "eigenvalue":
        try:
            aralik = kurucu.aktif_eksenel_aralik(spec)
            toplam = sema.kor_yuksekligi(kor)
            fisil_var = any(
                kurucu._spec_fisil_mi(spec, x)
                for b in katmanlar for x in sema.katman_adaylari(kor, b))
        except Exception:
            aralik, toplam, fisil_var = None, None, True
        if not fisil_var:
            bulgular.append(Bulgu(
                "hata", "kor",
                "hiçbir eksenel katmanda fisil malzeme yok — özdeğer koşusu "
                "başlangıç kaynağı bulamaz"))
        elif aralik and toplam:
            aktif = aralik[1] - aralik[0]
            if aktif < toplam:
                bulgular.append(Bulgu(
                    "bilgi", "kor",
                    "aktif yakıt yüksekliği %g cm / toplam %g cm "
                    "(z = %g … %g)" % (aktif, toplam, aralik[0], aralik[1]),
                    "Başlangıç kaynağı kutusu ve kontrol çubuğu daldırması bu "
                    "fisil aralığa göre tanımlıdır. Güç dağılımının eksenel ağı "
                    "ise hedef çubuğun bulunduğu aralığa göre — ikisi aynı "
                    "olmak zorunda değil (doğal uranyum örtü fisildir ama "
                    "içinde yakıt çubuğu yoktur)."))

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
                "fisil aralık %g cm ama '%s' çubuğu yalnızca %g cm boyunca var"
                % (ar[1] - ar[0], g["cubuk"], cr[1] - cr[0]),
                "Güç dağılımı yalnızca bu çubuğu sayar; toplam güç ise tüm "
                "modelin gücüdür. Aradaki fisil katmanların (örtü gibi) gücü "
                "de bu çubuklara paylaştırılmış olur ve W/cm olduğundan yüksek "
                "çıkar. Mutlak sayıları kullanacaksanız toplam gücü yalnızca bu "
                "çubukların ürettiği güç olarak girin."))

    if any(c.get("tur") == "kontrol" for c in spec.get("cubuklar", [])):
        bulgular.append(Bulgu(
            "bilgi", "kor",
            "kontrol çubuğu daldırması aktif yakıt aralığında ölçülür",
            "%0 = uç aktif bölgenin tepesinde, %100 = dibinde; modelin toplam "
            "yüksekliği değil."))
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

    # Tukenmenin bu modelde yapilabilir olup olmadigi: uygunluk.tukenme_uygun
    # (arayuz tukenme sekmesini ayni kuralla gizler).
    uygun, sebep = uygunluk.tukenme_uygun(spec)
    if not uygun:
        if spec["ayarlar"].get("mod", "eigenvalue") != "eigenvalue":
            bulgular.append(Bulgu("hata", yer,
                                  "tükenme Özdeğer (k-eff) hesabı gerektirir",
                                  "Sabit kaynaklı tükenme (aktivasyon) bu sürümde yok."))
        else:
            bulgular.append(Bulgu("hata", yer, "tükenme yapılamaz: %s" % sebep,
                                  "Yanacak yakıt geometride yer almalı."))

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
            "%s zincir seçildi ama model %s spektrumlu görünüyor"
            % (_SPEKTRUM_ADI.get(zs["temel"], zs["temel"]),
               _SPEKTRUM_ADI.get(zs["spektrum"], zs["spektrum"])),
            "Termal/hızlı zincir yakalama dallanma oranlarını ve fisyon "
            "verimlerini belirler (ör. Am241(n,γ)→Am242m termalde %8.1, "
            "hızlıda %13.2)."))
    if zs["tur"].startswith("casl"):
        bulgular.append(Bulgu(
            "bilgi", yer,
            "basitleştirilmiş CASL zinciri: 228 nüklid (tam zincir 3820)",
            "Yaklaşık 3 kat hızlı; ön inceleme içindir. Sonuçları tam zincirle "
            "doğrulayın."))

    # --- guc ve adimlar ---
    p = t.get("guc_yogunlugu")
    if p is None or float(p) <= 0:
        bulgular.append(Bulgu("hata", yer, "güç yoğunluğu sıfırdan büyük olmalı [W/gHM]"))
    elif not (1.0 <= float(p) <= 200.0):
        bulgular.append(Bulgu(
            "uyari", yer, "güç yoğunluğu %g W/gHM olağan dışı" % float(p),
            "Tipik: PWR 38–40, BWR ~25, SFR 50–100 W/gHM. Birim W/gHM'dir, "
            "mutlak güç değil."))
    adimlar = t.get("adimlar") or []
    if not adimlar:
        bulgular.append(Bulgu("hata", yer, "en az bir zaman adımı gerekli"))
    elif any(float(a) <= 0 for a in adimlar):
        bulgular.append(Bulgu("hata", yer, "zaman adımları sıfırdan büyük olmalı"))
    else:
        birim = t.get("adim_birimi") or "d"
        ilk_gun = float(adimlar[0])
        if birim == "MWd/kg" and p:
            ilk_gun = float(adimlar[0]) * 1000.0 / float(p)
        if ilk_gun > 2.0:
            bulgular.append(Bulgu(
                "uyari", yer,
                "ilk adım %.3g gün — Xe-135 dengesi (~2 gün) tek adıma eziliyor"
                % ilk_gun,
                "İlk adımları kısa tutun (ör. 0.5 ve 1.5 gün). Xe-135 PWR'da "
                "birkaç bin pcm'lik hızlı bir düşüş yaratır; uzun bir ilk adım "
                "bunu görünmez kılar."))

    # --- yanabilir malzemeler ve hacimler ---
    try:
        hv = _tk.hacimler(spec)
    except Exception as e:
        hv = None
        bulgular.append(Bulgu("hata", yer, "hacimler hesaplanamadı: %s" % e))
    if hv is not None:
        if not hv and uygun:
            bulgular.append(Bulgu("hata", yer,
                                  "modelde yanabilir (fisil) malzeme yok"))
        for ad, v in hv.items():
            if not v["hacim"]:
                bulgular.append(Bulgu(
                    "hata", "tukenme/%s" % ad,
                    "hacim hesaplanamıyor: %s" % v["ayrinti"],
                    "Tükenme kesin hacim gerektirir: yanlış hacim yanma hızını "
                    "aynı oranda bozar ve k-eff'te iz bırakmaz."))
    for ad in t.get("ek_malzemeler") or []:
        if malzeme_bul(spec, ad) is None:
            bulgular.append(Bulgu("hata", yer, "tanımsız ek malzeme: '%s'" % ad))

    # --- istatistik ---
    a = spec["ayarlar"]
    aktif = int(a.get("cevrim", 0)) - int(a.get("pasif", 0))
    if int(a.get("parcacik", 0)) * max(aktif, 0) < 100000:
        bulgular.append(Bulgu(
            "uyari", yer,
            "aktif istatistik az (%d parçacık × %d çevrim)"
            % (int(a.get("parcacik", 0)), aktif),
            "Tükenme her adımda reaksiyon hızlarını transport hesabından alır; "
            "gürültü adımdan adıma birikir. Parçacık × aktif çevrim ≥ 100 000 "
            "önerilir."))
    if t.get("malzemeleri_ayir"):
        bulgular.append(Bulgu(
            "bilgi", yer, "çubuk çubuk yanma açık",
            "Her hücre ayrı malzeme olur; bellek ve süre hücre sayısıyla artar."))
    return bulgular


def ayar_kontrol(spec):
    """Cevrim/parcacik sayilari ve kaynak tanimi."""
    bulgular = []
    a = spec["ayarlar"]
    cevrim = a.get("cevrim", 0)
    pasif = a.get("pasif", 0)
    parcacik = a.get("parcacik", 0)

    if parcacik <= 0:
        bulgular.append(Bulgu("hata", "ayarlar", "parçacık sayısı sıfırdan büyük olmalı"))
    if cevrim <= 0:
        bulgular.append(Bulgu("hata", "ayarlar", "çevrim sayısı sıfırdan büyük olmalı"))
    if a.get("mod") == "eigenvalue":
        if pasif >= cevrim:
            bulgular.append(Bulgu(
                "hata", "ayarlar",
                "pasif çevrim (%d) toplam çevrimden (%d) az olmalı" % (pasif, cevrim)))
        elif pasif < 5:
            bulgular.append(Bulgu(
                "uyari", "ayarlar",
                "pasif çevrim çok az (%d) — kaynak dağılımı yakınsamamış olabilir" % pasif,
                "Tipik olarak en az 20–50 pasif çevrim kullanılır."))
        elif cevrim - pasif < 20:
            bulgular.append(Bulgu(
                "uyari", "ayarlar",
                "aktif çevrim sayısı az (%d) — istatistik zayıf kalır" % (cevrim - pasif)))
        ent = a.get("entropi_mesh") or {}
        if not ent.get("var"):
            bulgular.append(Bulgu(
                "uyari", "ayarlar",
                "Shannon entropisi kapalı — kaynak dağılımının yakınsayıp "
                "yakınsamadığı ölçülemez",
                "Yakınsamamış kaynak k-eff'i yanlı tahmin ettirir ve bu başka "
                "türlü fark edilmez. Özdeğer hesaplarında açık tutun."))
        elif any(n <= 0 for n in (ent.get("boyut") or [0])):
            bulgular.append(Bulgu("hata", "ayarlar",
                                  "entropi ağı boyutları sıfırdan büyük olmalı"))
        if parcacik < 1000:
            bulgular.append(Bulgu(
                "uyari", "ayarlar",
                "çevrim başına parçacık az (%d) — kaynak yakınsaması bozulabilir" % parcacik))
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
    # hangi alan/secenek bu modelde gecerli: uygunluk (arayuzle ayni kural)
    alan = uygunluk.ayar_alanlari(spec)
    secenek = uygunluk.kaynak_secenekleri(spec)

    # --- dagilimlar gercekten kurulabiliyor mu ---
    for ad, fn, arg in (("enerji tayfı", _kaynak.enerji_dagilimi, e),
                        ("açısal dağılım", _kaynak.aci_dagilimi, k.get("aci"))):
        try:
            fn(arg)
        except Exception as hata:
            bulgular.append(Bulgu("hata", "kaynak", "%s kurulamadı: %s" % (ad, hata)))

    # --- siddet ---
    kuvvet = k.get("kuvvet")
    if kuvvet is not None and float(kuvvet) <= 0:
        bulgular.append(Bulgu("hata", "kaynak",
                              "kaynak şiddeti sıfırdan büyük olmalı (%s)" % kuvvet))
    elif (kuvvet is not None and not alan["kaynak_siddeti"]
          and float(kuvvet) != float(sema.VARSAYILAN_AYARLAR["kaynak"]["kuvvet"])):
        bulgular.append(Bulgu(
            "bilgi", "kaynak",
            "özdeğer hesabında kaynak şiddeti (%g) yok sayılır" % float(kuvvet),
            "Özdeğer hesabında sonuçlar fisyon kaynağına normalize edilir; "
            "mutlak ölçek için güç dağılımındaki toplam gücü kullanın."))

    # (kutu kaynagi + fisil malzeme yok: fisil_gereksinim_kontrol)

    # --- parcacik turu ---
    parca = k.get("parcacik") or "neutron"
    if parca not in ("neutron", "photon"):
        bulgular.append(Bulgu("hata", "kaynak",
                              "bilinmeyen parçacık türü: %s" % parca))
    elif parca == "photon":
        if parca not in secenek["parcaciklar"]:
            bulgular.append(Bulgu(
                "hata", "kaynak",
                "foton kaynağı Özdeğer (k-eff) hesabında anlamsız",
                "Fotonlar fisyon zincirini taşımaz. Foton kaynağı için hesap "
                "türünü Sabit kaynak yapın."))
        if veri_kontrolu:
            _, _, foton = _kutuphane_icerigi_foton()
            if foton is not None and not foton:
                bulgular.append(Bulgu(
                    "hata", "kaynak",
                    "foton kaynağı seçildi ama kütüphanede foton verisi yok",
                    "cross_sections.xml içinde type='photon' kaydı bulunamadı."))

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
                "kaynak enerjisi %s, veri tavanı %s (%s)"
                % (_kaynak.enerji_metni(tepe), _kaynak.enerji_metni(tavan), sahibi),
                "Tavanı, modeldeki nüklidler içinde en düşük üst sınıra sahip "
                "olan belirler. OpenMC koşu sırasında hata verir."))

    # --- nokta kaynak geometrinin icinde mi ---
    if k.get("tur", "nokta") == "nokta":
        konum = list(k.get("konum") or (0.0, 0.0, 0.0))
        h = sema_kor_yuksekligi(spec["kor"])
        if h and abs(float(konum[2])) >= float(h) / 2.0:
            bulgular.append(Bulgu(
                "hata", "kaynak",
                "nokta kaynak z = %g modelin dışında (yükseklik %g, sınır ±%g)"
                % (konum[2], h, h / 2.0),
                "Geometri dışında başlayan parçacıklar anında kaybolur."))

    # --- sabit kaynak moduna ozgu ---
    if sabit:
        if not spec.get("tallyler") and not (spec.get("guc_dagilimi") or {}).get("var"):
            bulgular.append(Bulgu(
                "hata", "ayarlar",
                "sabit kaynak hesabında hiçbir tally tanımlı değil — koşu hiçbir "
                "sonuç üretmez",
                "Sabit kaynak hesabında k-eff yoktur; ne ölçülecekse bir "
                "tally olarak tanımlanmalıdır (akı, doz, reaksiyon hızı)."))
        if (a.get("kinetik") or {}).get("var") and not alan["kinetik"]:
            bulgular.append(Bulgu(
                "bilgi", "ayarlar",
                "kinetik parametreler (β_eff, Λ) yalnızca özdeğer hesabında "
                "bulunur — sabit kaynak hesabında yok sayılır",
                "IFP yöntemi fisyon zincirini nesiller boyunca izler; sabit "
                "kaynak hesabında k-eff ve nesil kavramı yoktur."))
        if (a.get("entropi_mesh") or {}).get("var") and not alan["entropi"]:
            bulgular.append(Bulgu(
                "bilgi", "ayarlar",
                "Shannon entropisi sabit kaynak hesabında kullanılmaz",
                "Entropi fisyon kaynağı dağılımının yakınsamasını ölçer; sabit "
                "kaynakta kaynak zaten sabittir. OpenMC bunu yok sayar."))
        if int(a.get("pasif") or 0) > 0 and not alan["pasif"]:
            bulgular.append(Bulgu(
                "bilgi", "ayarlar",
                "sabit kaynak hesabında pasif çevrim (%d) yok sayılır"
                % int(a.get("pasif") or 0),
                "Pasif çevrim fisyon kaynağının yakınsaması içindir; sabit "
                "kaynak hesabında hiç yazılmaz. Bütün çevrimler sayılır."))
        if k.get("tur") == "kutu" and "kutu" in secenek["turler"]:
            # fisil malzeme yoksa fisil_gereksinim_kontrol HATA verir
            bulgular.append(Bulgu(
                "uyari", "kaynak",
                "sabit kaynak hesabında kutu kaynağı 'yalnızca fisil bölgeler' "
                "kısıtıyla örneklenir",
                "Kaynak parçacıkları yalnızca fisil malzemede başlar; kutunun "
                "geri kalanı boş kalır. Dış bir kaynak modelliyorsanız nokta "
                "kaynak kullanın."))
    else:
        tur = e.get("tur", "watt")
        if tur != "watt":
            bulgular.append(Bulgu(
                "bilgi", "kaynak",
                "özdeğer hesabında enerji tayfı (%s) yalnızca başlangıç tahminidir"
                % dict(_kaynak.TAYFLAR).get(tur, tur),
                "Pasif çevrimler içinde gerçek fisyon tayfıyla değişir; k-eff'i "
                "etkilemez. Tayf asıl sabit kaynak hesabında belirleyicidir."))
        if (k.get("aci") or {}).get("tur", "izotropik") != "izotropik":
            bulgular.append(Bulgu(
                "bilgi", "kaynak",
                "özdeğer hesabında açısal dağılım da yalnızca başlangıç tahminidir"))

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
            bulgular.append(Bulgu("hata", yer, "en az bir skor seçilmeli"))
        for s in t.get("skorlar", []):
            if s not in BILINEN_SKORLAR and not str(s).isdigit():
                bulgular.append(Bulgu(
                    "uyari", yer,
                    "'%s' bilinen skorlar arasında değil" % s,
                    "OpenMC bu skoru tanımayabilir; hata ancak koşu sırasında çıkar. "
                    "Liste elle tutulur (OpenMC geçerli skor listesi sunmuyor); "
                    "yeni bir skor kullanıyorsanız bu uyarı yanlış alarm olabilir."))
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
        bulgular.append(Bulgu("hata", yer, "hedef çubuk tanımsız: %s" % cubuk_ad
                              if cubuk_ad else "hedef çubuk seçilmemiş"))
        return bulgular

    bolge = g.get("bolge")
    if not isinstance(bolge, int) or not (0 <= bolge < len(c["bolgeler"])):
        bulgular.append(Bulgu("hata", yer,
                              "geçersiz bölge numarası %s (çubukta %d bölge var)"
                              % (bolge + 1 if isinstance(bolge, int) else "(seçilmemiş)",
                                 len(c["bolgeler"]))))
    else:
        mal = c["bolgeler"][bolge].get("malzeme")
        m = malzeme_bul(spec, mal) if mal else None
        # "yakit" rolu uygunluk'tan (Z >= 90, kurucu ile ayni olcut). Eski
        # kural ad oneki ("U"/"Pu"/"Th") ve zenginlik alanina bakiyordu.
        fisil = bool(m) and "yakit" in uygunluk.tek_malzeme_rolleri(m)
        if not fisil:
            bulgular.append(Bulgu(
                "uyari", yer,
                "seçilen bölgenin malzemesi ('%s') fisil görünmüyor" % mal,
                "Güç dağılımı genellikle yakıt bölgesinde (1. bölge) ölçülür. "
                "Zarf ya da soğutucu seçildiyse sonuç anlamsız olur."))

    # --- cubuk geometride mi, bir kafeste tekrarlaniyor mu? ---
    # Uygun cubuk kurali uygunluk.guc_cubuklari'nda (arayuz listeyi oradan
    # alir). Eskiden "herhangi bir demetin anahtarinda geciyor mu" bakiliyordu:
    # KULLANILMAYAN bir demette gecen cubuk gecerli sayiliyor, kurucu ise
    # "cubugu modelde kullanilmiyor" diyerek duruyordu.
    uygun = uygunluk.guc_cubuklari(spec)
    if cubuk_ad not in uygun:
        geo = uygunluk.geometri_icerigi(spec)
        liste = ("Uygun çubuklar: %s" % ", ".join(uygun) if uygun else
                 "Bu modelde uygun çubuk yok: fisil bölgeli bir çubuğun bir "
                 "demette tekrarlanması gerekir.")
        if cubuk_ad not in geo["cubuk"]:
            bulgular.append(Bulgu(
                "hata", yer,
                "'%s' çubuğu modelde kullanılmıyor — güç dağılımı yalnızca "
                "geometride yer alan bir çubuk için hesaplanabilir" % cubuk_ad,
                "Model kurulurken durur. " + liste))
        elif cubuk_ad not in geo["kafesteki_cubuk"]:
            if (spec["kor"].get("tur") == "tek_cubuk"
                    and spec["kor"].get("cubuk") == cubuk_ad):
                bulgular.append(Bulgu(
                    "hata", yer,
                    "'%s' bir demette tekrarlanmıyor (kor türü: '%s')"
                    % (cubuk_ad, _kor_turu_adi("tek_cubuk")),
                    "Güç dağılımı tekrarlanan hücre örnekleri üzerinden "
                    "hesaplanır; tek bir çubukta dağılım yoktur. Bir demet kurun."))
            else:
                bulgular.append(Bulgu(
                    "uyari", yer,
                    "'%s' hiçbir demet haritasında kullanılmıyor" % cubuk_ad,
                    "Tekrarlanan örnek yoksa dağılım tek bir değerden ibaret "
                    "kalır. " + liste))
        # cubuk kafeste ama fisil bolgesi yok: yukaridaki "fisil gorunmuyor"
        # uyarisi bunu zaten soyler.

    skor = g.get("skor") or "kappa-fission"
    if skor not in BILINEN_SKORLAR:
        bulgular.append(Bulgu("uyari", yer, "'%s' bilinen skorlar arasında değil" % skor))
    elif skor not in ("kappa-fission", "fission-q-prompt", "fission-q-recoverable",
                      "heating", "heating-local"):
        bulgular.append(Bulgu(
            "uyari", yer,
            "'%s' bir enerji skoru değil" % skor,
            "Güç dağılımı için enerji bırakan bir skor gerekir; standart seçim "
            "'kappa-fission'dır. 'fission' yalnızca fisyon sayısını verir."))

    # --- eksenel ---
    h = sema_kor_yuksekligi(spec["kor"])
    dilim = int(g.get("eksenel_dilim") or 1)
    if not h:
        bulgular.append(Bulgu(
            "bilgi", yer,
            "model 2B — F_q hesaplanamaz, yalnızca F_ΔH verilir",
            "Yerel güç yoğunluğu tepesi eksenel şekle bağlıdır. Kor sekmesinde "
            "aktif yükseklik tanımlayın."))
    elif dilim < 10:
        bulgular.append(Bulgu(
            "uyari", yer,
            "yalnızca %d eksenel dilim — F_q olduğundan küçük çıkar" % dilim,
            "Kaba dilimler eksenel tepeyi ortalar. En az 10–20 dilim kullanın."))

    tg = g.get("toplam_guc")
    if tg is not None:
        if tg <= 0:
            bulgular.append(Bulgu("hata", yer, "toplam güç sıfırdan büyük olmalı"))
        elif not h:
            bulgular.append(Bulgu(
                "uyari", yer,
                "toplam güç verilmiş ama model 2B — çizgisel güç [W/cm] hesaplanamaz",
                "W/cm için Kor sekmesinde aktif yükseklik tanımlayın."))
    return bulgular


def fisil_gereksinim_kontrol(spec):
    """
    Fisil malzeme gerektiren secimler: ozdeger modu ve kutu kaynagi.

    "Fisil" uygunluk'tan gelir: GEOMETRIDE KULLANILAN yakit (Z >= 90). Arayuz
    ayni kuralla analiz/tukenme sekmelerini ve kutu kaynagini gizler.
    Iki durumda da model KURULUR ama OpenMC kosuda durur (olculdu:
    ozdegerde "No fission sites banked"). Bu yuzden tum_kontroller bunu
    nuklid kontrolunden SONRA cagirir: bozuk bir yakit bilesimi (or. veri
    kutuphanesinde olmayan bir nuklid) once KOK NEDEN olarak raporlanmali,
    bu bulgu onu gizlememeli.
    """
    bulgular = []
    a = spec["ayarlar"]
    oz = uygunluk.model_ozeti(spec)
    if oz["fisil"]:
        return bulgular
    # Geometri hic cozulmuyorsa kor hatalari zaten soyler; katmanli korda
    # eksenel_kontrol ayni seyi katman diliyle soyler.
    geometri_var = bool(uygunluk.geometri_icerigi(spec)["malzeme"])
    if (a.get("mod", "eigenvalue") == "eigenvalue" and geometri_var
            and sema.eksenel_katmanlar(spec["kor"]) is None):
        bulgular.append(Bulgu(
            "hata", "ayarlar",
            "Özdeğer (k-eff) hesabı fisil malzeme gerektirir — geometride "
            "fisil malzeme yok",
            "OpenMC ilk çevrimde durur (\"No fission sites banked\"). "
            "Zırhlama/aktivasyon hesabı için hesap türünü Sabit kaynak yapın."))
    if (a.get("kaynak") or {}).get("tur") == "kutu":
        bulgular.append(Bulgu(
            "hata", "kaynak",
            "kutu kaynağı fisil malzeme gerektirir — geometride fisil malzeme yok",
            "Kutu kaynağı yalnızca fisil bölgelerde örneklenir; OpenMC hiç "
            "örnek bulamaz ve durur. Nokta kaynak kullanın."))
    return bulgular


def referans_kontrol(spec):
    """Tanimli ama kullanilmayan / kullanilan ama tanimsiz ogeler."""
    from cekirdek.sema import kullanilan_malzemeler
    bulgular = []
    tanimli = {m["ad"] for m in spec["malzemeler"]}
    kullanilan = kullanilan_malzemeler(spec)

    for ad in sorted(kullanilan - tanimli):
        bulgular.append(Bulgu("hata", "malzemeler", "kullanılan ama tanımsız malzeme: %s" % ad))
    for ad in sorted(tanimli - kullanilan):
        bulgular.append(Bulgu("bilgi", "malzemeler",
                              "tanımlı ama modelde kullanılmayan malzeme: %s" % ad))
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
    # fisil gereksinimi nuklid kontrolunden SONRA (bkz. fonksiyon notu)
    bulgular += fisil_gereksinim_kontrol(spec)

    sira = {"hata": 0, "uyari": 1, "bilgi": 2}
    return sorted(bulgular, key=lambda b: sira[b.seviye])


def ozet(bulgular):
    """Bulgulari '2 hata, 1 uyari, 3 bilgi' seklinde ozetler."""
    say = {"hata": 0, "uyari": 0, "bilgi": 0}
    for b in bulgular:
        say[b.seviye] += 1
    return "%d hata, %d uyarı, %d bilgi" % (say["hata"], say["uyari"], say["bilgi"])
