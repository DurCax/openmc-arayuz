# -*- coding: utf-8 -*-
"""
================================================================================
 uygunluk.py  --  "Bu modelde ne gecerli?" sorusunun TEK cevabi
================================================================================

 NEDEN
   Kullanilabilirlik denetimi ayni kalibi her sekmede buldu: listeler her seyi
   sunuyor, uyumsuzluk ancak sonra (ya da hic) soyleniyor. Ornek: Analiz'de
   "bor" secilince UO2 hedef olarak sunuluyordu; kure modeline yukseklik
   girilebiliyordu; pin hucrede guc dagilimi acilabiliyordu.
   Bu modul arayuzun neyi GOSTERECEGINI ve dogrulamanin neyi HATA sayacagini
   ayni kurallardan turetir. Kural bir kez yazilir; arayuz gizler/suzer,
   dogrula.py ayni kurali ihlal eden elle yazilmis dosyalari yakalar.

 SOZLESME
   Asagidaki fonksiyonlarin IMZALARI sabittir; arayuz bunlara dayanir
   (testler/test_sozlesme.py). Ic mantik gelistirilebilir. Hepsi yalnizca
   spec'e bakar (openmc.Model kurmaz), hizlidir ve arayuzde her duzenlemede
   cagrilabilir.

   Sekme anahtarlari (SEKMELER) ana penceredeki sekme SIRASIDIR; sekmeler
   gizlenir ama silinmez, boylece dizinleri degismez.

 TEMEL ILKE -- "GEOMETRIDE GERCEKTEN VAR OLAN"
   Hedef listeleri spec'te TANIMLI olan her seyi degil, kurucu.kor_kur'un
   GEOMETRIYE KOYDUGU seyleri sunar (geometri_icerigi). Tanimli ama
   kullanilmayan bir malzemenin/cubugun/kafesin taramasi modeli degistirmez;
   sonuc "katsayi = 0 +/- gurultu" olur ve ogrenci bunu fizik sanar.
   Olculdu (testler/test_uygunluk.py): sunulan her (tarama, hedef) cifti
   kurulan modeli DEGISTIRIR; modeli degistirmeyen hicbir cift sunulmaz.

 KURALLAR (ozet -- ayrintisi ilgili fonksiyonda)
   malzeme rolleri   : bilesimden (malzeme_rolleri)
   analiz            : ozdeger modu + geometride fisil malzeme; her tarama
                       yalnizca en az bir gecerli hedefi varsa
   kritik arama      : KRITIK_PARAMETRELER ∩ gecerli taramalar
   sinirlar          : periodic yalnizca kare (x/y duzlem ciftli) yan
                       yuzeyde ve altigen tek demette; altigen tam korda
                       (kirik cizgi sinir) yok; alt/ust yalnizca 3B ve kure
                       disinda
   ayarlar           : mod ve fisil malzemeye gore (ayar_alanlari)
   guc dagilimi      : fisil bolgeli ve bir KAFESTE tekrarlanan cubuk
   tukenme           : ozdeger modu + geometride fisil malzeme
================================================================================
"""

import re

from cekirdek import sema
from cekirdek.uygunluk_geometri import (  # noqa: F401 -- disa verilen adlar
    _ALTIGEN_PERIODIC, _bul, geometri_icerigi, model_boyutu, sinir_secenekleri,
    sonsuz_ortam, yan_yuzey, yuz_sinir_secenekleri)
from cekirdek.ceviri import N_, _
from cekirdek.gunluk import kaydedici, uyar_bir_kez

_log = kaydedici(__name__)

# Ana penceredeki sekmelerin sabit anahtarlari, SIRAYLA.
SEKMELER = ("malzemeler", "parcalar", "demet", "kor", "ayarlar",
            "calistir", "analiz", "tukenme")

# Yeni modelde secilebilen kor turleri. "kuresel" yalnizca onu kullanan bir
# dosya acildiginda gorunur (kullanici karari).
KOR_TURLERI = ("tek_cubuk", "tek_plaka", "tek_demet", "kare_kafes", "altigen_kafes",
               "tamburlu")

# Kor turlerinin kullaniciya gorunen sade adlari (arayuz menusu, dogrulama
# mesajlari). Anahtarlar spec'te ASCII kalir.
KOR_TURU_ADLARI = {
    "tek_cubuk": N_("Yakıt çubuğu (pin hücre)"),
    "tek_plaka": N_("Plaka elemanı (MTR)"),
    "tek_demet": N_("Tek yakıt demeti"),
    "kare_kafes": N_("Tam kor (kare harita)"),
    "altigen_kafes": N_("Tam kor (altıgen harita)"),
    "tamburlu": N_("Tamburlu kompakt kor"),
    "kuresel": N_("Küresel düzenek (kabuklar)"),
}

ROLLER = ("yakit", "sogutucu", "moderator", "emici", "yapisal", "gaz")

# Guclu notron sogurucu elementler (kontrol cubugu, tambur, yanabilir zehir).
_EMICI_ELEMENTLER = {"B", "Gd", "Ag", "In", "Cd", "Hf", "Er", "Eu", "Dy", "Sm"}
# Emici sayilmak icin, hafif baglayicilar (H, C, N, O) disindaki atomlarin en
# az bu kesri sogurucu olmali. B4C, Gd2O3, AgInCd, Hf, Dy2TiO5 (%67), borlu
# celik (%2 B -> ~%9) emici; eser Hf'li zirkaloy (1e-4) ve eser B'li celik
# yapisal kalir.
_EMICI_ESIGI = 0.05
# Bu atom kesrinin altindaki bilesenler "eser" (safsizlik) sayilir ve
# kimyasal aile kurallarina (su mu, grafit mi...) girmez: 1 ppm B'li grafit
# yine grafittir. Borlu sudaki bor (2000 ppm -> ~1e-3) da eserdir.
_ESER_ESIGI = 0.005
_GAZ_YOGUNLUK_ESIGI = 0.01      # g/cm3 altinda gaz sayilir
_AVOGADRO_BARN = 0.602214076    # N_A * 1e-24  (atom/b-cm <-> mol/cm3)

# Kritik aramada anlamli olan "denetim" parametreleri.
KRITIK_PARAMETRELER = ("bor_ppm", "cubuk_daldirma", "tambur_donme",
                       "zenginlik", "yansitici_kalinlik", "grup_donme", "grup_daldirma")



# ----------------------------------------------------------------------------
# yardimcilar: bilesim
# ----------------------------------------------------------------------------

def _eleman(b):
    """Bilesim satirindan element sembolu: "U235" -> "U", "Am242_m1" -> "Am"."""
    isim = b.get("isim") or ""
    if b.get("tur") != "nuklid":
        return isim
    m = re.match(r"[A-Z][a-z]?", isim)
    return m.group(0) if m else isim


def _z(sembol):
    import openmc.data
    return openmc.data.ATOMIC_NUMBER.get(sembol, 0)


def _kutle(b):
    """Bilesim satirinin atom kutlesi [u] (agirlik -> atom orani donusumu icin)."""
    import openmc.data
    isim = b.get("isim") or ""
    try:
        if b.get("tur") == "nuklid":
            try:
                return float(openmc.data.atomic_mass(isim))
            except Exception:
                return float(openmc.data.zam(isim)[1])
        return float(openmc.data.atomic_weight(isim))
    except Exception:
        # bilinmeyen ad: dogrula ayrica bulgu verir; burada kutle 0 sayilir
        uyar_bir_kez(_log, "atom kutlesi bilinmiyor: %r", isim)
        return 0.0


def _atom_kesirleri(m):
    """
    {element: atom kesri}. "wo" satirlari atom kutlesine bolunerek atom
    oranina cevrilir. Yaklasiktir (rol siniflamasi icin yeterli).
    """
    toplam = {}
    for b in m.get("bilesim") or []:
        if not b.get("isim"):
            continue
        try:
            miktar = float(b.get("miktar") or 0.0)
        except (TypeError, ValueError):   # sayi olmayan miktar: dogrula bulgu verir
            continue
        if miktar <= 0:
            continue
        if (b.get("birim") or "ao") == "wo":
            A = _kutle(b)
            if A > 0:
                miktar /= A
        e = _eleman(b)
        toplam[e] = toplam.get(e, 0.0) + miktar
    s = sum(toplam.values())
    return {e: v / s for e, v in toplam.items()} if s > 0 else {}


def _ortalama_kutle(m):
    """Atom kesirleriyle agirliklanmis ortalama atom kutlesi [u]; bilinmiyorsa 0."""
    import openmc.data
    kes = _atom_kesirleri(m)
    A = 0.0
    for e, f in kes.items():
        try:
            A += f * float(openmc.data.atomic_weight(e))
        except Exception:
            uyar_bir_kez(_log, "ortalama atom kutlesi: element %r bilinmiyor", e)
            return 0.0
    return A


def _yogunluk_gcm3(m):
    """Malzeme yogunlugu g/cm3 cinsinden; cevrilemiyorsa None."""
    y = m.get("yogunluk") or {}
    try:
        deger = float(y.get("deger") or 0.0)
    except (TypeError, ValueError):       # sayi olmayan yogunluk: dogrula bulgu verir
        return None
    birim = y.get("birim") or "g/cm3"
    if birim in ("g/cm3", "g/cc"):
        return deger
    if birim == "kg/m3":
        return deger / 1000.0
    if birim in ("atom/b-cm", "atom/cm3"):
        A = _ortalama_kutle(m)
        if A <= 0:
            return None
        n = deger if birim == "atom/b-cm" else deger * 1.0e-24
        return n * A / _AVOGADRO_BARN
    return None


def _doteryumlu(m):
    """
    Hidrojenin ANLAMLI kesri doteryum mu (H2 / D)? Agir su hafif su degildir.
    Dogal bolluktaki eser H2 (%0.016; BEAVRS gibi nuklid listeli hafif su) agir
    su SAYILMAZ: hidrojenin doteryum kesri _ESER_ESIGI'nin altindaysa False.
    """
    doteryum = hafif = 0.0
    for b in m.get("bilesim") or []:
        isim = b.get("isim") or ""
        miktar = abs(float(b.get("miktar") or 0.0))
        if isim in ("H2", "D"):
            doteryum += miktar
        elif isim in ("H", "H1"):
            hafif += miktar
    toplam = doteryum + hafif
    return toplam > 0.0 and doteryum / toplam >= _ESER_ESIGI


def _korelasyon(m):
    """
    tarama.py'nin sicakliga bagli yogunluk korelasyonu (fonksiyon ya da None).
    Kimya burada TEKRAR YAZILMAZ: sogutucu sicakligi taramasinin gercekte ne
    yapacagini tarama._yogunluk_korelasyonu belirler.
    """
    from cekirdek import tarama
    try:
        fonk, _aciklama = tarama._yogunluk_korelasyonu(m)
    except Exception:
        uyar_bir_kez(_log, "yogunluk korelasyonu secilemedi: %r", m.get("ad"))
        return None
    return fonk


def _hafif_su_korelasyonu_mu(m):
    from cekirdek import malzeme_kutup as mk
    return _korelasyon(m) is mk.su_yogunluk


# ----------------------------------------------------------------------------
# malzeme rolleri
# ----------------------------------------------------------------------------

def _roller(m):
    elemanlar = {_eleman(b) for b in m.get("bilesim") or [] if b.get("isim")}
    roller = set()
    # yakit: kurucu._spec_fisil_mi ile AYNI olcut (herhangi bir Z >= 90
    # bilesen). Aktif eksenel aralik, kaynak kutusu ve tukenme bu tanima baglidir.
    if any(_z(e) >= 90 for e in elemanlar):
        roller.add("yakit")
    yog = _yogunluk_gcm3(m)
    if yog is not None and 0.0 < yog < _GAZ_YOGUNLUK_ESIGI:
        roller.add("gaz")
    if roller:
        return roller

    kes = _atom_kesirleri(m)
    ana = {e for e, f in kes.items() if f >= _ESER_ESIGI} or elemanlar

    # --- sogutucu (sivi / yogun faz) ---
    su = "H" in ana and ana <= {"H", "O", "B"}
    if su:
        roller.update(("sogutucu", "moderator"))       # hafif, agir, borlu su
    elif (_korelasyon(m) is not None or ana <= {"Na", "K"} or ana <= {"Pb", "Bi"}
          or ana == {"C", "O"}):
        roller.add("sogutucu")                          # Na, NaK, Pb, LBE, CO2

    # --- moderator (kati) ---
    if (ana in ({"C"}, {"Be"}, {"Be", "O"})                    # grafit, Be, BeO
            or ("H" in ana and ana <= {"H", "C"} and "C" in ana)  # polietilen
            or ("H" in ana and ana - {"H"} and ana - {"H"} <= {"Zr", "Y"})):  # ZrH, YH
        roller.add("moderator")

    # --- emici: sogurucu eser degil VE hafif baglayicilar disindaki atomlarin
    # yeterli kesri (1 ppm B'li grafitte B, H/C/N/O disindaki TEK atomdur;
    # oran %100 cikar ama malzeme yine grafittir) ---
    if "sogutucu" not in roller:
        agir = sum(f for e, f in kes.items() if e not in ("H", "C", "N", "O"))
        emici = sum(f for e, f in kes.items() if e in _EMICI_ELEMENTLER)
        if emici >= _ESER_ESIGI and agir > 0 and emici / agir >= _EMICI_ESIGI:
            roller.add("emici")

    if not roller:
        roller.add("yapisal")
    return roller


def malzeme_rolleri(spec):
    """
    {malzeme_adi: set(rol)} ; roller ROLLER icinden.
      yakit     : Z >= 90 bilesen (kurucu._spec_fisil_mi ile ayni olcut)
      gaz       : yogunluk < 0.01 g/cm3 (atom/b-cm ve kg/m3 de cevrilir)
      sogutucu  : su (H+O[+B], agir su dahil), Na, NaK, Pb, Pb-Bi, CO2 ve
                  tarama.py'nin yogunluk korelasyonu olan her malzeme
      moderator : su, grafit, Be, BeO, polietilen, ZrH/YH
      emici     : H/C/N/O disindaki atomlarin >= %5'i B, Gd, Ag, In, Cd, Hf,
                  Er, Eu, Dy, Sm (B4C, Gd2O3, AgInCd, Hf, Dy2TiO5, borlu celik)
                  -- borlu su sogutucu+moderatordur, emici DEGIL (bor eser
                  bir katkidir; emici rolu kontrol malzemeleri icindir)
      yapisal   : hicbir role girmeyen kati (zarf, celik, Al, SiC)
    Aile kurallarinda %0.5 atom altindaki bilesenler eser sayilir: 1 ppm B'li
    grafit grafittir, eser Hf'li zirkaloy yapisaldir.
    Bir malzeme birden fazla role sahip olabilir (su: sogutucu + moderator).
    """
    return {m["ad"]: _roller(m) for m in spec.get("malzemeler", []) if "ad" in m}


def tek_malzeme_rolleri(malzeme):
    """Tek bir malzeme taniminin rolleri (malzeme_rolleri ile ayni kural)."""
    return _roller(malzeme)


def rol_malzemeleri(spec, rol):
    """Belirli bir role sahip malzeme adlari (spec sirasiyla; kullanilmasa da)."""
    r = malzeme_rolleri(spec)
    return [m["ad"] for m in spec.get("malzemeler", []) if rol in r.get(m.get("ad"), ())]


def kullanilan_malzemeler(spec):
    """Geometride gercekten yer alan malzeme adlari, spec sirasiyla."""
    adlar = geometri_icerigi(spec)["malzeme"]
    return [m["ad"] for m in spec.get("malzemeler", []) if m.get("ad") in adlar]


# ----------------------------------------------------------------------------
# baglam: bir cagrida bir kez hesaplanan bilgiler
# ----------------------------------------------------------------------------

class _Baglam(object):
    """Roller ve geometri bir kez hesaplanir; butun kurallar buradan okur."""

    def __init__(self, spec):
        self.spec = spec
        self.kor = spec.get("kor") or {}
        self.tur = self.kor.get("tur")
        self.mod = (spec.get("ayarlar") or {}).get("mod", "eigenvalue")
        self.ozdeger = self.mod == "eigenvalue"
        self.agac = self.tur == "agac"
        self.boyut = model_boyutu(spec)
        self.roller = malzeme_rolleri(spec)
        self.geo = geometri_icerigi(spec)
        # geometride kullanilan malzeme tanimlari, spec sirasiyla
        self.malzemeler = [m for m in spec.get("malzemeler", [])
                           if m.get("ad") in self.geo["malzeme"]]
        self.fisil = any("yakit" in self.roller.get(m["ad"], ())
                         for m in self.malzemeler)

    def rolu(self, ad, rol):
        return rol in self.roller.get(ad, ())

    @property
    def model(self):
        """GeometriModeli (yalniz gerektiginde kurulur; agac hedefleri)."""
        if getattr(self, "_model", None) is None:
            from cekirdek import geometri
            self._model = geometri.model(self.spec)
        return self._model

    def gruplar(self, tur):
        """Uyesi geometride olan 'tur' gruplarinin adlari (agac ya da sablon)."""
        from cekirdek import geometri
        return [g["ad"] for g in geometri.gruplar(self.model) if g.get("tur") == tur
                and g.get("uyeler")]


# ----------------------------------------------------------------------------
# model ozeti ve sekmeler
# ----------------------------------------------------------------------------

def model_ozeti(spec):
    """
    DONER {"tur", "boyut": "2B"|"3B"|"3B_katmanli", "mod",
           "kafes": bool, "kontrol_cubugu": bool, "tambur": bool, "fisil": bool}

      boyut          : EKSENEL boyut. Kuresel duzenekte z ekseni yoktur -> "2B".
      kafes          : geometride en az bir kafes (demet) KULLANILIYOR
      kontrol_cubugu : geometride bir kontrol cubugu KULLANILIYOR
      tambur         : tamburlu kor ve tambur sayisi > 0
      fisil          : geometride fisil (yakit rolunde) malzeme KULLANILIYOR
    """
    b = _Baglam(spec)
    return {
        "tur": b.tur,
        "boyut": b.boyut,
        "mod": b.mod,
        "kafes": bool(b.geo["demet"]) or (b.agac and _agacta_kafes_var(b)),
        "kontrol_cubugu": any((_bul(spec, "cubuklar", c) or {}).get("tur") == "kontrol"
                              for c in b.geo["cubuk"]),
        "tambur": bool(b.geo.get("tambur")) if b.agac else (
            b.tur == "tamburlu" and int(((b.kor.get("tambur") or {}).get("sayi")) or 0) > 0),
        "fisil": b.fisil,
    }


def _agacta_kafes_var(b):
    from cekirdek import geometri
    return any(z.dugum.get("tur") == "kafes" for z in geometri.gez(b.model))


def gecerli_sekmeler(spec):
    """
    Gorunmesi gereken sekme anahtarlari, SEKMELER sirasiyla.
      parcalar : kuresel disinda (kurede yalnizca malzeme kabuklari var)
      demet    : tek_demet, kare_kafes, tamburlu (dolgu kafes olabilir) ya da
                 geometride bir kafes kullaniliyorsa
      analiz   : en az bir gecerli tarama varsa (ozdeger modu + fisil malzeme)
      tukenme  : tukenme_uygun
    """
    b = _Baglam(spec)
    gorunur = {"malzemeler", "kor", "ayarlar", "calistir"}
    if b.tur != "kuresel":
        gorunur.add("parcalar")
    if b.tur in ("tek_demet", "kare_kafes", "altigen_kafes", "tamburlu", "agac") \
            or b.geo["demet"]:
        gorunur.add("demet")
    if _gecerli_taramalar(b, "katsayi"):
        gorunur.add("analiz")
    if _tukenme_uygun(b)[0]:
        gorunur.add("tukenme")
    return [s for s in SEKMELER if s in gorunur]


def kor_turleri(spec):
    """Kor turu listesinde gosterilecek turler; kuresel ve gelismis (agac)
    yalnizca kullaniliyorsa (agaca gecis tek yonludur: geometri.gelismise_gec)."""
    turler = list(KOR_TURLERI)
    tur = (spec.get("kor") or {}).get("tur")
    if tur in ("kuresel", "agac"):
        turler.append(tur)
    return turler


# ----------------------------------------------------------------------------
# parcalar, kor, sinirlar, ayarlar
# ----------------------------------------------------------------------------

def parca_turleri(spec):
    """
    {"cubuk", "plaka", "kontrol_cubugu", "demet_kare", "demet_altigen": bool}
    -- Parcalar ve Demet sekmelerinde neler eklenebilir.
      kontrol cubugu 3B ve bir kafese (demet / kor haritasi / tambur dolgusu)
      yerlestirilebilen turlerde; tek_cubuk'ta cubugun kendisi kordur.
    """
    b = _Baglam(spec)
    tur = b.tur
    if b.agac:
        # gelismis modda her kutuphane parcasi herhangi bir yuvaya konabilir
        return {"cubuk": True, "plaka": True, "kontrol_cubugu": b.boyut != "2B",
                "demet_kare": True, "demet_altigen": True}
    kafesli = ("tek_demet", "kare_kafes", "altigen_kafes", "tamburlu")
    demet = tur in kafesli or bool(b.geo["demet"])
    return {
        "cubuk": tur in ("tek_cubuk",) + kafesli,
        "plaka": tur == "tek_plaka",
        "kontrol_cubugu": b.boyut != "2B" and tur in kafesli,
        # Demet sekmesinde eklenebilecek kafes tipleri. Kare haritanin
        # hucresi kare, altigen haritaninki altigendir; oteki tip oturmaz.
        "demet_kare": demet and tur != "altigen_kafes",
        "demet_altigen": demet and tur != "kare_kafes",
    }


def kor_alanlari(tur):
    """Bu kor turunde anlamli olan spec["kor"] alanlari (sema.KOR_TUR_ALANLARI)."""
    return tuple(sema.KOR_TUR_ALANLARI.get(tur, ()))


def kor_ortak_alanlari(spec):
    """
    Turlerin ORTAK kor alanlarindan hangileri bu modelde anlamli. {alan: bool}
      yukseklik, eksenel : kuresel disinda (kurede eksen yok)
      sinir_yan          : her zaman
      sinir_alt/sinir_ust: yalnizca 3B ve kuresel disinda (sinir_secenekleri)
    """
    tur = (spec.get("kor") or {}).get("tur")
    eksenli = tur in sema.EKSENEL_DESTEKLI or (
        tur == "agac" and yan_yuzey(spec) != "kure")
    return {
        "yukseklik": eksenli,
        "eksenel": eksenli,
        "sinir_yan": True,
        "sinir_alt": bool(sinir_secenekleri(spec, "alt")),
        "sinir_ust": bool(sinir_secenekleri(spec, "ust")),
    }


def _ayar_alanlari(b):
    ozdeger = b.ozdeger
    guc = bool(_guc_cubuklari(b))
    return {
        "pasif": ozdeger,
        "entropi": ozdeger,
        "kinetik": ozdeger and b.fisil,
        "kaynak_siddeti": not ozdeger,
        "foton": not ozdeger,
        "kaynak_tayfi_temel": not ozdeger,
        "kutu_kaynagi": b.fisil,
        "guc_dagilimi": guc,
        "eksenel_dilim": guc and b.boyut != "2B",
    }


def ayar_alanlari(spec):
    """
    5. sekme alanlarindan hangileri bu modelde ANLAMLI. {alan: bool}
      pasif, entropi     : ozdeger modu (kurucu sabit kaynakta kurmaz)
      kinetik            : ozdeger modu + fisil malzeme (IFP fisyon zinciri izler)
      kaynak_siddeti     : sabit kaynak (ozdegerde etkisiz)
      foton              : sabit kaynak (fotonlar fisyon zincirini tasimaz)
      kaynak_tayfi_temel : sabit kaynak (ozdegerde tayf yalnizca baslangic tahmini)
      kutu_kaynagi       : geometride fisil malzeme (kutu kaynagi HER modda
                           "fissionable" kisitiyla orneklenir; fisil yoksa
                           OpenMC ornekleme yapamaz)
      guc_dagilimi       : guc_cubuklari bos degil (moddan bagimsiz; kurucu
                           tally'yi her modda kurar)
      eksenel_dilim      : guc_dagilimi + 3B model
    """
    return _ayar_alanlari(_Baglam(spec))


def kaynak_secenekleri(spec):
    """{"turler": [...], "parcaciklar": [...]} -- kaynak tipi ve parcacik listeleri."""
    alan = ayar_alanlari(spec)
    turler = ["nokta"] + (["kutu"] if alan["kutu_kaynagi"] else [])
    parcaciklar = ["neutron"] + (["photon"] if alan["foton"] else [])
    return {"turler": turler, "parcaciklar": parcaciklar}


def _guc_cubuklari(b):
    yakit = {m["ad"] for m in b.malzemeler if b.rolu(m["ad"], "yakit")}
    sonuc = []
    for c in b.spec.get("cubuklar", []):
        if c.get("ad") not in b.geo["kafesteki_cubuk"]:
            continue
        if any(x.get("malzeme") in yakit for x in c.get("bolgeler") or []):
            sonuc.append(c["ad"])
    return sonuc


def guc_cubuklari(spec):
    """
    Guc dagilimi hedefi olabilecek cubuklar (spec sirasiyla): fisil bolgesi
    olan ve geometrideki bir KAFESTE (demet ya da kor haritasi) tekrarlanan
    cubuklar -- DistribcellFilter tekrarlanan orneklere ihtiyac duyar ve
    kurucu.guc_tally_ekle geometride olmayan cubukta durur. Pin hucrede,
    kurede, plakada ve dolgusu kafes olmayan tamburlu korda bos.
    """
    return _guc_cubuklari(_Baglam(spec))


def _tukenme_uygun(b):
    if not b.ozdeger:
        return False, _("tükenme özdeğer (k-eff) hesabı gerektirir")
    if not b.fisil:
        return False, _("geometride fisil (yakıt) malzeme yok")
    return True, ""


def tukenme_uygun(spec):
    """(bool, sebep) -- tukenme sekmesi/hesabi bu modelde anlamli mi."""
    return _tukenme_uygun(_Baglam(spec))


def tukenme_ayirma_anlamli(spec):
    """
    "Cubuk cubuk yanma" (her yakit ornegi ayri malzeme) secenegi anlamli mi?
    Yalnizca bir yanabilir malzeme geometride birden fazla kez geciyorsa
    (17x17: 264, MTR: 23); pin hucrede ve Godiva'da (1) hicbir sey degistirmez.
    Sayilamazsa True (secenek saklanmasin).
    """
    try:
        from cekirdek import tukenme
        return tukenme.yakit_ornek_sayisi(spec) > 1
    except Exception:
        uyar_bir_kez(_log, "yakit ornek sayisi sayilamadi; cubuk cubuk yanma secenegi "
                           "gosteriliyor")
        return True


# Bir eksenel katmani doldurabilecek parca turleri. Katman, korun ana
# dolgusuyla AYNI yanal kutuya yerlesir (kurucu._eksenel_hucreler); bu yuzden
# ana dolguyla ayni olcekte olmali: pin hucrede cubuk, demette (ayni tipte)
# demet; tam korda ana dolgu haritanin kendisidir, ayri katmana yalnizca
# malzeme (or. su yansitici) konur.
KATMAN_DOLGU_TURLERI = {
    "tek_cubuk":  ("cubuk", "malzeme"),
    "tek_plaka":  ("plaka", "malzeme"),
    "tek_demet":  ("demet", "malzeme"),
    "kare_kafes": ("malzeme",),
    "altigen_kafes": ("malzeme",),
    "tamburlu":   ("demet", "cubuk", "malzeme"),
}


def katman_dolgu_turleri(spec):
    """Bu kor turunde eksenel katmana konabilecek parca turleri."""
    tur = (spec.get("kor") or {}).get("tur")
    return KATMAN_DOLGU_TURLERI.get(tur, ("cubuk", "plaka", "demet", "malzeme"))


# ----------------------------------------------------------------------------
# analiz: taramalar ve hedefler
# ----------------------------------------------------------------------------

def _hedefler(b, tarama_turu):
    # Butun taramalar reaktiviteye dayanir: rho = (k-1)/k. Sabit kaynakta ve
    # fisil malzemesi olmayan modelde k-eff yoktur.
    if not (b.ozdeger and b.fisil):
        return []
    malz = b.malzemeler
    spec = b.spec

    if tarama_turu == "yakit_sicaklik":
        return [m["ad"] for m in malz if b.rolu(m["ad"], "yakit")]
    if tarama_turu == "sogutucu_sicaklik":
        # tarama yogunlugu korelasyonla gunceller. Agir su hafif su tablosuna
        # duser (tarama._yogunluk_korelasyonu H2'yi H sayar): 1.1056 g/cm3'luk
        # D2O ilk noktada ~0.998'e iner -- sahte %10 yogunluk kaybi. Sunulmaz.
        return [m["ad"] for m in malz if b.rolu(m["ad"], "sogutucu")
                and _korelasyon(m) is not None
                and not (_hafif_su_korelasyonu_mu(m) and _doteryumlu(m))]
    if tarama_turu == "void_orani":
        # rho0*(1-alfa): birimden bagimsiz; korelasyonu olan sivi sogutucular
        return [m["ad"] for m in malz if b.rolu(m["ad"], "sogutucu")
                and _korelasyon(m) is not None]
    if tarama_turu == "bor_ppm":
        # tarama bilesimi malzeme_kutup.su(..., bor_ppm) ile DEGISTIRIR: hafif
        # su + bor. Yalnizca hafif (borlu) suya uygulanabilir; agir su hafif
        # suya donerdi.
        return [m["ad"] for m in malz if b.rolu(m["ad"], "sogutucu")
                and _hafif_su_korelasyonu_mu(m) and not _doteryumlu(m)]
    if tarama_turu == "zenginlik":
        # tarama "zenginlik" alani olan satirlari degistirir; OpenMC zenginligi
        # yalnizca U ELEMENTINDE kabul eder (dogrula bunu hata sayar).
        return [m["ad"] for m in malz
                if any(x.get("zenginlik") is not None and x.get("isim") == "U"
                       and x.get("tur", "element") != "nuklid"
                       for x in m.get("bilesim") or [])]
    if tarama_turu == "malzeme_yogunluk":
        # tarama degeri g/cm3 kabul eder ama yalnizca "deger"i yazar: atom/b-cm
        # tanimli bir malzemede (Godiva HEU) 18.7 "atom/b-cm" olurdu.
        return [m["ad"] for m in malz
                if ((m.get("yogunluk") or {}).get("birim") or "g/cm3") in ("g/cm3", "g/cc")]
    if tarama_turu == "kafes_adim":
        # Eksenel katmanlamada her katmanin kafesi AYRIDIR; birinin adimi
        # degisince katmanlar farkli adimli olur (bkz. rapor).
        return [d["ad"] for d in spec.get("demetler", []) if d.get("ad") in b.geo["demet"]]
    if tarama_turu == "cubuk_daldirma":
        if b.boyut == "2B":
            return []
        return [c["ad"] for c in spec.get("cubuklar", [])
                if c.get("tur") == "kontrol" and c.get("ad") in b.geo["cubuk"]]
    if tarama_turu == "cubuk_yaricap":
        return [(c["ad"], i) for c in spec.get("cubuklar", []) if c.get("ad") in b.geo["cubuk"]
                for i, _x in enumerate((c.get("bolgeler") or [])[:-1])]
    if b.agac and tarama_turu in _AGAC_HEDEFLERI:
        return _AGAC_HEDEFLERI[tarama_turu](b)
    if tarama_turu in ("grup_donme", "grup_daldirma"):
        # sablonda gruplar yok (tamburlu korun tek donme grubu tambur_donme'dir)
        if not b.agac:
            return []
        if tarama_turu == "grup_donme":
            return b.gruplar("donme")
        return b.gruplar("daldirma") if b.boyut != "2B" else []
    if tarama_turu == "kor_adim":
        # kurucu kor["adim"]i yalnizca tek_cubuk (hucre) ve kare_kafes (kor
        # kafesi) icin okur; tek_demet olcusunu demetten alir.
        return [None] if "adim" in kor_alanlari(b.tur) else []
    if tarama_turu == "tambur_donme":
        t = b.kor.get("tambur") or {}
        return [None] if b.tur == "tamburlu" and int(t.get("sayi") or 0) > 0 else []
    if tarama_turu == "yansitici_kalinlik":
        # kurucu yansiticiyi tamburlu'da her zaman, tek_demet/kare_kafes'te
        # "var" iken kurar. Bosluk (void) yansiticinin kalinligi hicbir sey
        # degistirmez.
        yans = b.kor.get("yansitici") or {}
        kurulur = b.tur == "tamburlu" or (
            b.tur in ("tek_demet", "kare_kafes", "altigen_kafes") and yans.get("var"))
        malzeme_var = (yans.get("malzeme") or sema.BOSLUK) != sema.BOSLUK
        return [None] if kurulur and malzeme_var else []
    return []


def _agac_kafes_hedefleri(b):
    """kor_adim (agac): adimi taranabilecek agac kafeslerinin kimlikleri."""
    from cekirdek import geometri
    kimlikler = []
    for z in geometri.gez(b.model):
        kid = z.dugum.get("id")
        if z.dugum.get("tur") == "kafes" and kid and not str(kid).startswith("demet:") \
                and kid not in kimlikler:
            kimlikler.append(kid)
    return kimlikler


def _agac_halka_hedefleri(b):
    """yansitici_kalinlik (agac): kalinlikla tanimli, malzemeli halkalar
    "<kap id>/halkalar/<i>" (kok ve parca kaplari)."""
    from cekirdek import geometri
    hedefler = []
    for z in geometri.gez(b.model):
        d = z.dugum
        if d.get("tur") != "kap" or not d.get("id"):
            continue
        for i, h in enumerate(d.get("halkalar") or []):
            icerik = h.get("icerik") or {}
            if h.get("kalinlik") is not None and icerik.get("tur") == "malzeme" \
                    and (icerik.get("ad") or sema.BOSLUK) != sema.BOSLUK:
                hedef = "%s/halkalar/%d" % (d["id"], i)
                if hedef not in hedefler:
                    hedefler.append(hedef)
    return hedefler


def _agac_daldirma_hedefleri(b):
    """cubuk_daldirma (agac): bir daldirma grubuna UYE OLMAYAN kontrol
    cubuklari (uyenin kendi daldirmasi yok sayilir; tarama modeli degistirmezdi)."""
    if b.boyut == "2B":
        return []
    from cekirdek import geometri
    uyeler = {u for g in geometri.gruplar(b.model) if g.get("tur") == "daldirma"
              for u in g.get("uyeler") or []}
    return [c["ad"] for c in b.spec.get("cubuklar", []) if c.get("tur") == "kontrol"
            and c.get("ad") in b.geo["cubuk"] and c["ad"] not in uyeler]


# Gelismis (agac) modda hedefi agactan gelen taramalar (§7 tarama satiri).
# tambur_donme takma addir: tek donme grubu varsa o grup, yoksa sunulmaz
# (arayuz grup_donme ile grup secer).
_AGAC_HEDEFLERI = {
    "kor_adim": _agac_kafes_hedefleri,
    "yansitici_kalinlik": _agac_halka_hedefleri,
    "cubuk_daldirma": _agac_daldirma_hedefleri,
    "tambur_donme": lambda b: [None] if len(b.gruplar("donme")) == 1 else [],
}


def gecerli_hedefler(spec, tarama_turu):
    """
    Taramanin gecerli hedefleri -- sekme_analiz'deki hedef listesinin DATA
    degerleriyle ayni bicimde:
      malzeme       -> malzeme adi
      demet         -> demet adi
      kontrol_cubugu-> cubuk adi
      cubuk_bolge   -> (cubuk_adi, bolge_indeksi)
      kor           -> [None] (kor ayari; hedef secimi yok) ya da [] (gecersiz)

    Yalnizca GEOMETRIDE YER ALAN hedefler sunulur. Kurallar:
      yakit_sicaklik     yakit rolundeki malzemeler
      sogutucu_sicaklik  tarama'nin yogunluk korelasyonu olan sogutucular
                         (su, Na, Pb/LBE); agir su haric
      void_orani         ayni sogutucular (agir su dahil)
      bor_ppm            hafif (borlu) su
      zenginlik          zenginlik alanli U elementi iceren malzemeler
      malzeme_yogunluk   yogunlugu g/cm3 olan malzemeler
      kafes_adim         geometrideki kafesler
      cubuk_daldirma     geometrideki kontrol cubuklari, yalnizca 3B
      cubuk_yaricap      geometrideki cubuklarin sinirli bolgeleri
      kor_adim           tek_cubuk, kare_kafes, altigen_kafes
      tambur_donme       tamburlu, sayi > 0
      yansitici_kalinlik tamburlu ya da yansiticisi acik tek_demet/kare_kafes;
                         yansitici malzemesi bosluk olmamali
    Ozdeger modu ve geometride fisil malzeme yoksa her tarama icin bos.
    """
    return _hedefler(_Baglam(spec), tarama_turu)


def _gecerli_taramalar(b, amac):
    from cekirdek import tarama
    if not (b.ozdeger and b.fisil):
        return []
    adaylar = list(tarama.TURLER)
    if amac == "kritik":
        adaylar = [t for t in adaylar if t in KRITIK_PARAMETRELER]
    return [t for t in adaylar if _hedefler(b, t)]


def gecerli_taramalar(spec, amac="katsayi"):
    """
    Gosterilecek tarama turleri (tarama.TURLER anahtarlari, o sirayla), en az
    bir gecerli hedefi olanlar. amac: "katsayi" (reaktivite katsayisi) |
    "kritik" (kritik arama -- yalnizca KRITIK_PARAMETRELER). Sabit kaynak
    modunda ve fisil malzemesi olmayan modelde bos.
    """
    return _gecerli_taramalar(_Baglam(spec), amac)
