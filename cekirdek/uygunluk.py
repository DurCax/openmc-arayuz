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
   Asagidaki fonksiyonlarin IMZALARI sabittir; arayuz bunlara dayanir.
   Ic mantik gelistirilebilir. Hepsi yalnizca spec'e bakar (openmc.Model
   kurmaz), hizlidir ve arayuzde her duzenlemede cagrilabilir.

   Sekme anahtarlari (SEKMELER) ana penceredeki sekme SIRASIDIR; sekmeler
   gizlenir ama silinmez, boylece dizinleri degismez.
================================================================================
"""

from cekirdek import sema

# Ana penceredeki sekmelerin sabit anahtarlari, SIRAYLA.
SEKMELER = ("malzemeler", "parcalar", "demet", "kor", "ayarlar",
            "calistir", "analiz", "tukenme")

# Yeni modelde secilebilen kor turleri. "kuresel" yalnizca onu kullanan bir
# dosya acildiginda gorunur (kullanici karari).
KOR_TURLERI = ("tek_cubuk", "tek_plaka", "tek_demet", "kare_kafes", "tamburlu")

ROLLER = ("yakit", "sogutucu", "moderator", "emici", "yapisal", "gaz")

_EMICI_ELEMENTLER = {"B", "Gd", "Ag", "In", "Cd", "Hf", "Er", "Eu", "Dy", "Sm"}
_GAZ_YOGUNLUK_ESIGI = 0.01      # g/cm3 altinda gaz sayilir


# ----------------------------------------------------------------------------
# yardimcilar
# ----------------------------------------------------------------------------

def _eleman(b):
    """Bilesim satirindan element sembolu: "U235" -> "U", "Am242_m1" -> "Am"."""
    import re
    isim = b.get("isim") or ""
    if b.get("tur") != "nuklid":
        return isim
    m = re.match(r"[A-Z][a-z]?", isim)
    return m.group(0) if m else isim


def _z(sembol):
    import openmc.data
    return openmc.data.ATOMIC_NUMBER.get(sembol, 0)


def _yogunluk_gcm3(m):
    y = m.get("yogunluk") or {}
    if (y.get("birim") or "g/cm3") in ("g/cm3", "g/cc"):
        return float(y.get("deger") or 0.0)
    return None


# ----------------------------------------------------------------------------
# malzeme rolleri
# ----------------------------------------------------------------------------

def malzeme_rolleri(spec):
    """
    {malzeme_adi: set(rol)} ; roller ROLLER icinden.
      yakit     : Z >= 90 bilesen
      sogutucu  : su (H+O[+B]), Na, NaK, Pb/Bi, He gazi degil
      moderator : H / D / C / Be icerir ve yakit degil
      emici     : B, Gd, Ag-In-Cd, Hf, Er ... icerir ve yakit degil
                  (borlu su hem sogutucu hem emici DEGIL -- bor kucuk bir
                  katkidir; emici rolu B4C, Gd2O3, AgInCd gibi govdeler icin)
      gaz       : yogunluk < 0.01 g/cm3
      yapisal   : baska hicbir role girmeyen kati (zarf, celik, Al)
    Bir malzeme birden fazla role sahip olabilir (su: sogutucu + moderator).
    """
    sonuc = {}
    for m in spec.get("malzemeler", []):
        elemanlar = {_eleman(b) for b in m.get("bilesim", []) if b.get("isim")}
        roller = set()
        if any(_z(e) >= 90 for e in elemanlar):
            roller.add("yakit")
        yog = _yogunluk_gcm3(m)
        if yog is not None and yog < _GAZ_YOGUNLUK_ESIGI:
            roller.add("gaz")
        if "yakit" not in roller and "gaz" not in roller:
            if elemanlar and elemanlar <= {"H", "O", "B"} and "H" in elemanlar:
                roller.update(("sogutucu", "moderator"))
            elif elemanlar and elemanlar <= {"D", "H", "O"} and "D" in elemanlar:
                roller.update(("sogutucu", "moderator"))
            elif elemanlar and elemanlar <= {"Na", "K"}:
                roller.add("sogutucu")
            elif elemanlar and elemanlar <= {"Pb", "Bi"}:
                roller.add("sogutucu")
            elif elemanlar & {"C", "Be"} and elemanlar <= {"C", "Be", "O"}:
                roller.add("moderator")
            elif elemanlar & {"H"} and "Zr" in elemanlar:
                roller.add("moderator")
            ana = elemanlar - {"C", "O", "N"}
            if ana and ana <= _EMICI_ELEMENTLER | {"C", "O"} and ana & _EMICI_ELEMENTLER:
                roller.add("emici")
        if not roller:
            roller.add("yapisal")
        sonuc[m["ad"]] = roller
    return sonuc


def rol_malzemeleri(spec, rol):
    """Belirli bir role sahip malzeme adlari (spec sirasiyla)."""
    r = malzeme_rolleri(spec)
    return [m["ad"] for m in spec.get("malzemeler", []) if rol in r.get(m["ad"], ())]


# ----------------------------------------------------------------------------
# model ozeti ve sekmeler
# ----------------------------------------------------------------------------

def model_ozeti(spec):
    """
    DONER {"tur", "boyut": "2B"|"3B"|"3B_katmanli", "mod",
           "kafes": bool, "kontrol_cubugu": bool, "tambur": bool, "fisil": bool}
    """
    kor = spec.get("kor") or {}
    if sema.eksenel_katmanlar(kor):
        boyut = "3B_katmanli"
    elif sema.kor_yuksekligi(kor):
        boyut = "3B"
    else:
        boyut = "2B"
    tur = kor.get("tur")
    return {
        "tur": tur,
        "boyut": boyut,
        "mod": (spec.get("ayarlar") or {}).get("mod", "eigenvalue"),
        "kafes": bool(spec.get("demetler")) and tur in ("tek_demet", "kare_kafes", "tamburlu"),
        "kontrol_cubugu": any(c.get("tur") == "kontrol" for c in spec.get("cubuklar", [])),
        "tambur": tur == "tamburlu" and int(((kor.get("tambur") or {}).get("sayi")) or 0) > 0,
        "fisil": bool(rol_malzemeleri(spec, "yakit")),
    }


def gecerli_sekmeler(spec):
    """Gorunmesi gereken sekme anahtarlari, SEKMELER sirasiyla."""
    oz = model_ozeti(spec)
    tur = oz["tur"]
    gorunur = {"malzemeler", "kor", "ayarlar", "calistir"}
    if tur != "kuresel":
        gorunur.add("parcalar")
    if tur in ("tek_demet", "kare_kafes", "tamburlu"):
        gorunur.add("demet")
    if oz["mod"] == "eigenvalue":
        gorunur.add("analiz")
        if oz["fisil"]:
            gorunur.add("tukenme")
    return [s for s in SEKMELER if s in gorunur]


def kor_turleri(spec):
    """Kor turu listesinde gosterilecek turler; kuresel yalnizca kullaniliyorsa."""
    turler = list(KOR_TURLERI)
    if (spec.get("kor") or {}).get("tur") == "kuresel":
        turler.append("kuresel")
    return turler


# ----------------------------------------------------------------------------
# parcalar, kor, sinirlar, ayarlar
# ----------------------------------------------------------------------------

def parca_turleri(spec):
    """{"cubuk": bool, "plaka": bool, "kontrol_cubugu": bool} -- 2. sekmede neler eklenebilir."""
    oz = model_ozeti(spec)
    tur = oz["tur"]
    return {
        "cubuk": tur in ("tek_cubuk", "tek_demet", "kare_kafes", "tamburlu"),
        "plaka": tur == "tek_plaka",
        "kontrol_cubugu": oz["boyut"] != "2B" and tur in ("tek_demet", "kare_kafes", "tamburlu"),
    }


def kor_alanlari(tur):
    """Bu kor turunde anlamli olan spec["kor"] alanlari (sema.KOR_TUR_ALANLARI)."""
    return tuple(sema.KOR_TUR_ALANLARI.get(tur, ()))


def sinir_secenekleri(spec, yuzey):
    """
    yuzey: "yan" | "alt" | "ust". Uygun sinir kosullari; bos liste = yuzey yok.
    periodic yalnizca duzlemsel yan yuzeylerde (kare kutu) gecerlidir.
    """
    oz = model_ozeti(spec)
    tur = oz["tur"]
    if yuzey in ("alt", "ust"):
        if tur == "kuresel" or oz["boyut"] == "2B":
            return []
        return ["vacuum", "reflective", "white"]
    if tur == "kuresel":
        return ["vacuum"]
    duzlemsel = tur in ("tek_cubuk", "tek_plaka", "kare_kafes") or (
        tur == "tek_demet" and not _altigen_kor(spec))
    secenek = ["reflective", "vacuum", "white"]
    if duzlemsel:
        secenek.append("periodic")
    return secenek


def _altigen_kor(spec):
    kor = spec.get("kor") or {}
    if kor.get("tur") != "tek_demet":
        return False
    d = sema.demet_bul(spec, kor.get("demet") or "")
    return bool(d) and d.get("tur") == "altigen"


def ayar_alanlari(spec):
    """
    5. sekme alanlarindan hangileri bu modelde ANLAMLI. {alan: bool}
    Anahtarlar: pasif, entropi, kinetik, kaynak_siddeti, foton,
                kaynak_tayfi_temel (tayf/aci temel gorunumde mi),
                kutu_kaynagi, guc_dagilimi, eksenel_dilim
    """
    oz = model_ozeti(spec)
    ozdeger = oz["mod"] == "eigenvalue"
    return {
        "pasif": ozdeger,
        "entropi": ozdeger,
        "kinetik": ozdeger and oz["fisil"],
        "kaynak_siddeti": not ozdeger,
        "foton": not ozdeger,
        "kaynak_tayfi_temel": not ozdeger,
        "kutu_kaynagi": oz["fisil"],
        "guc_dagilimi": ozdeger and bool(guc_cubuklari(spec)),
        "eksenel_dilim": oz["boyut"] != "2B",
    }


def kaynak_secenekleri(spec):
    """{"turler": [...], "parcaciklar": [...]} -- kaynak tipi ve parcacik listeleri."""
    alan = ayar_alanlari(spec)
    turler = ["nokta"] + (["kutu"] if alan["kutu_kaynagi"] else [])
    parcaciklar = ["neutron"] + (["photon"] if alan["foton"] else [])
    return {"turler": turler, "parcaciklar": parcaciklar}


def guc_cubuklari(spec):
    """
    Guc dagilimi hedefi olabilecek cubuklar: fisil bolgesi olan ve bir
    KAFESTE tekrarlanan cubuklar (distribcell). Pin hucrede ve kurede bos.
    """
    tur = (spec.get("kor") or {}).get("tur")
    if tur not in ("tek_demet", "kare_kafes", "tamburlu"):
        return []
    yakit = set(rol_malzemeleri(spec, "yakit"))
    kafeste = set()
    for d in spec.get("demetler", []):
        kafeste.update((d.get("anahtar") or {}).values())
    return [c["ad"] for c in spec.get("cubuklar", [])
            if c["ad"] in kafeste
            and any(b.get("malzeme") in yakit for b in c.get("bolgeler", []))]


def tukenme_uygun(spec):
    """(bool, sebep) -- tukenme sekmesi/hesabi bu modelde anlamli mi."""
    oz = model_ozeti(spec)
    if oz["mod"] != "eigenvalue":
        return False, "tükenme özdeğer (k-eff) hesabı gerektirir"
    if not oz["fisil"]:
        return False, "modelde fisil (yakıt) malzeme yok"
    return True, ""


# ----------------------------------------------------------------------------
# analiz: taramalar ve hedefler
# ----------------------------------------------------------------------------

# Kritik aramada anlamli olan "denetim" parametreleri.
KRITIK_PARAMETRELER = ("bor_ppm", "cubuk_daldirma", "tambur_donme",
                       "zenginlik", "yansitici_kalinlik")


def gecerli_hedefler(spec, tarama_turu):
    """
    Taramanin gecerli hedefleri -- sekme_analiz'deki hedef listesinin DATA
    degerleriyle ayni bicimde:
      malzeme       -> malzeme adi
      demet         -> demet adi
      kontrol_cubugu-> cubuk adi
      cubuk_bolge   -> (cubuk_adi, bolge_indeksi)
      kor           -> [None] (kor ayari; hedef secimi yok) ya da [] (gecersiz)
    """
    roller = malzeme_rolleri(spec)
    malz = [m["ad"] for m in spec.get("malzemeler", [])]
    oz = model_ozeti(spec)
    tur = oz["tur"]

    def rolu(ad, *istenen):
        return bool(roller.get(ad, set()) & set(istenen))

    if tarama_turu == "yakit_sicaklik":
        return [a for a in malz if rolu(a, "yakit")]
    if tarama_turu in ("sogutucu_sicaklik", "void_orani"):
        return [a for a in malz if rolu(a, "sogutucu")]
    if tarama_turu == "bor_ppm":
        return [m["ad"] for m in spec.get("malzemeler", [])
                if {_eleman(b) for b in m.get("bilesim", [])} <= {"H", "O", "B"}
                and "H" in {_eleman(b) for b in m.get("bilesim", [])}]
    if tarama_turu == "zenginlik":
        return [m["ad"] for m in spec.get("malzemeler", [])
                if any(b.get("zenginlik") is not None for b in m.get("bilesim", []))]
    if tarama_turu == "malzeme_yogunluk":
        return list(malz)
    if tarama_turu == "kafes_adim":
        return [d["ad"] for d in spec.get("demetler", [])]
    if tarama_turu == "cubuk_daldirma":
        if oz["boyut"] == "2B":
            return []
        return [c["ad"] for c in spec.get("cubuklar", []) if c.get("tur") == "kontrol"]
    if tarama_turu == "cubuk_yaricap":
        return [(c["ad"], i) for c in spec.get("cubuklar", [])
                for i, _b in enumerate(c.get("bolgeler", [])[:-1])]
    if tarama_turu == "kor_adim":
        return [None] if tur in ("tek_cubuk", "kare_kafes") else []
    if tarama_turu == "tambur_donme":
        return [None] if oz["tambur"] else []
    if tarama_turu == "yansitici_kalinlik":
        yans = ((spec.get("kor") or {}).get("yansitici") or {})
        if tur == "tamburlu" or (tur in ("tek_demet", "kare_kafes") and yans.get("var")):
            return [None]
        return []
    return []


def gecerli_taramalar(spec, amac="katsayi"):
    """
    Gosterilecek tarama turleri (tarama.TURLER anahtarlari), en az bir gecerli
    hedefi olanlar. amac: "katsayi" (reaktivite katsayisi) | "kritik" (kritik
    arama -- yalnizca KRITIK_PARAMETRELER). Sabit kaynak modunda bos.
    """
    from cekirdek import tarama
    if model_ozeti(spec)["mod"] != "eigenvalue":
        return []
    adaylar = list(tarama.TURLER)
    if amac == "kritik":
        adaylar = [t for t in adaylar if t in KRITIK_PARAMETRELER]
    return [t for t in adaylar if gecerli_hedefler(spec, t)]
