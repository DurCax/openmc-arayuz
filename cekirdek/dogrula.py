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

from cekirdek.sema import BOSLUK, malzeme_bul, cubuk_bul, plaka_bul, demet_bul
from cekirdek import altigen, kurucu

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
_SAB_KURALLARI = [
    ({"H", "O"},      "c_H_in_H2O",  "su (H2O)"),
    ({"H", "O", "B"}, "c_H_in_H2O",  "borlu su"),
    ({"H", "Zr"},     "c_H_in_ZrH",  "sirkonyum hidrur"),
    ({"H", "C"},      "c_H_in_CH2",  "polietilen / plastik"),
    ({"C"},           "c_Graphite",  "grafit"),
    ({"Be"},          "c_Be",        "berilyum"),
    ({"Be", "O"},     "c_Be_in_BeO", "berilyum oksit"),
    ({"D", "O"},      "c_D_in_D2O",  "agir su (D2O)"),
]

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
                  for uygun, onerilen, tanim in _SAB_KURALLARI
                  if elemanlar <= uygun]
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
    gecerli = ("tek_cubuk", "tek_demet", "kare_kafes", "tek_plaka", "kuresel")
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
    if not kor.get("yukseklik"):
        bulgular.append(Bulgu(
            "bilgi", "kor",
            "yukseklik verilmemis -- model eksenel yonde sonsuz (2B) kabul ediliyor"))
    return bulgular


# ============================================================================
# 4. AYARLAR
# ============================================================================

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
    bulgular += plaka_kontrol(spec)
    bulgular += demet_kontrol(spec)
    bulgular += kor_kontrol(spec)
    bulgular += ayar_kontrol(spec)
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
