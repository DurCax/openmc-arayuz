# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme.py  --  Yanma (depletion) hesabi
================================================================================

 KULLANIM
   python3 -m cekirdek.tukenme ornekler/pwr_tukenme.json -s 8
   python3 -m cekirdek.tukenme ornekler/pwr_tukenme.json --hazirla   # kosmadan

 NE YAPAR
   Spec'teki "tukenme" bolumune gore yanabilir malzemeleri isaretler, hacimlerini
   ANALITIK olarak hesaplar, uygun zinciri secer ve openmc.deplete ile
   transport-bozunum dongusunu kosar. Sonuc: depletion_results.h5.

 TASARIM KARARLARI (hepsi olcume ya da bilinen bir tuzaga dayanir)

   1. GUC = GUC YOGUNLUGU [W/gHM].
      Mutlak guc [W] 2B bir modelde "cm basina" olmak zorunda kalirdi -- tam
      bu projede daha once birkac kez yakaladigimiz turden sessiz bir birim
      tuzagi. W/gHM geometriden bagimsizdir ve muhendislerin gercekten verdigi
      sayidir (PWR ~38-40).

   2. HACIMLER ANALITIK VE KESIN OLMALI.
      Tukenmede reaksiyon hizi / (N x V) atom basina hizi verir. Hacim f kat
      yanlissa yanma hizi da f kat yanlis olur -- k-eff'te hicbir iz birakmadan.
      Hacim = bolge alani x (katman yuksekligi x o katmandaki cubuk sayisi)
      toplami. Testte OpenMC'nin stokastik hacim hesabiyla karsilastirilir.

   3. ZINCIR SPEKTRUMA GORE, VE FISYON VERIMI DE.
      Termal/hizli zincir yalnizca YAKALAMA DALLANMA ORANLARINI degistirir
      (olculdu: 101 nuklid; or. Am241(n,g)->Am242m termalde %8.1, hizlida
      %13.2). Fisyon urunu verimleri ise ayri bir ayardir ve OpenMC'nin
      varsayilani SABIT 0.0253 eV'tur -- hizli zincir secilse bile. Hizli
      sistemde verim enerjisi ayrica 500 keV'e cekilir.

   4. ALT SURECTE KOSAR.
      openmc.lib icindeki bir C++ terminate() butun sureci oldurur (onizlemede
      yasandi). Arayuz bu kodu kendi surecinde asla calistirmaz.

 OLCULEN MALIYET (pin hucre, 2000 x 20 parcacik, 2 transport)
   CASL 228 nuklid: 37 s     ENDF/B-VIII.0 3820 nuklid: 125 s
   Zincirdeki nuklidler yakita eklenir; transport bu yuzden yavaslar.
================================================================================
"""

import math
import os
import sys

from cekirdek import sema, veri_bilgi

ZINCIRLER = {
    "termal":      "chain_endfb80_thermal.xml",
    "hizli":       "chain_endfb80_fast.xml",
    "casl_termal": "chain_casl_thermal.xml",
    "casl_hizli":  "chain_casl_fast.xml",
}

# Zincirdeki fisyon verimi enerjileri 0.0253 eV, 500 keV ve 14 MeV'tir.
VERIM_ENERJISI = {"termal": 0.0253, "hizli": 5.0e5}

# Yanabilir zehirler: fisil olmasalar da yanmalari reaktiviteyi belirler.
YANABILIR_ZEHIR = {"Gd", "Er"}
# Bor (B10) YALNIZ kati emici/yapisal malzemede yanabilir sayilir: Pyrex,
# IFBA, WABA, B4C. Borlu su/sogutucu (rol sogutucu/moderator; eser B) yanmaz:
# cozunmus bor isletmede ayarlanir, yakitla birlikte tukenen bir envanter
# degildir.
BOR_ZEHIR_ROLLERI = {"emici", "yapisal"}
_BOR_ZEHIR_DISI_ROLLER = {"sogutucu", "moderator", "gaz"}

# Moderator sayilan S(a,b) kayitlari (on eklerine gore). Berilyum BILEREK
# yok: tamburlu korda Be yalnizca yansiticidir, kor spektrumu hizlidir.
_MODERATOR_SAB = ("c_H_", "c_D_", "c_Graphite", "c_ortho", "c_para")


# ============================================================================
# Zincir secimi
# ============================================================================

def spektrum_tahmini(spec):
    """
    ("termal"|"hizli", gerekce).

    Kural: modelde hidrojen ya da doteryum iceren, ya da grafit S(a,b)'si
    tanimli bir malzeme varsa TERMAL; yoksa HIZLI. Hidrojen baskin
    yavaslaticidir; su, ZrH, polietilen hepsini kapsar.
    """
    for m in spec.get("malzemeler", []):
        for s in m.get("sab") or []:
            if any(str(s).startswith(o) for o in _MODERATOR_SAB):
                return "termal", "'%s' malzemesinde %s var" % (m["ad"], s)
        for b in m.get("bilesim", []):
            isim = b.get("isim") or ""
            eleman = isim.rstrip("0123456789") if b.get("tur") == "nuklid" else isim
            if eleman in ("H", "D") and float(b.get("miktar") or 0) > 0:
                return "termal", "'%s' malzemesi hidrojen içeriyor" % m["ad"]
    return "hizli", "modelde hidrojen ya da grafit moderatör yok"


def zincir_secimi(spec):
    """
    DONER {"tur", "yol", "spektrum", "verim_enerjisi", "gerekce"}
    """
    t = spec.get("tukenme") or {}
    istek = t.get("zincir") or "otomatik"
    spektrum, gerekce = spektrum_tahmini(spec)
    if istek == "otomatik":
        tur = spektrum
        gerekce = "otomatik: " + gerekce
    else:
        tur = istek
        gerekce = "kullanıcı seçimi"
    temel = "hizli" if tur.endswith("hizli") else "termal"
    return {
        "tur": tur,
        "yol": os.path.join(veri_bilgi.zincir_dizini(), ZINCIRLER[tur]),
        "spektrum": spektrum,
        "temel": temel,
        "verim_enerjisi": VERIM_ENERJISI[temel],
        "gerekce": gerekce,
    }


# ============================================================================
# Yanabilir malzemeler ve analitik hacimler
# ============================================================================

def _z(nuklid_ya_da_element):
    import openmc.data
    try:
        return openmc.data.zam(nuklid_ya_da_element)[0]
    except Exception:
        return openmc.data.ATOMIC_NUMBER.get(nuklid_ya_da_element, 0)


def _eleman_adi(b):
    isim = b.get("isim") or ""
    return isim.rstrip("0123456789_m") if b.get("tur") == "nuklid" else isim


def _bor_zehri_mi(m):
    """Kati emici/yapisal malzemede bor (element B ya da B10) var mi?"""
    from cekirdek import uygunluk
    bor = any(_eleman_adi(b) == "B" and float(b.get("miktar") or 0) > 0
              for b in m.get("bilesim", []))
    if not bor:
        return False
    roller = uygunluk.tek_malzeme_rolleri(m)
    return bool(roller & BOR_ZEHIR_ROLLERI) and not roller & _BOR_ZEHIR_DISI_ROLLER


def _fisil_mi(m):
    return any(_z(b.get("isim") or "") >= 90 for b in m.get("bilesim", []))


def _zehir_mi(m):
    return (any(_eleman_adi(b) in YANABILIR_ZEHIR for b in m.get("bilesim", []))
            or _bor_zehri_mi(m))


def yanabilir_adlar(spec):
    """Yanacak malzemelerin adlari: fisil olanlar + yanabilir zehirler + ek liste."""
    adlar = [m["ad"] for m in spec.get("malzemeler", []) if _fisil_mi(m) or _zehir_mi(m)]
    for ad in (spec.get("tukenme") or {}).get("ek_malzemeler") or []:
        if ad not in adlar and sema.malzeme_bul(spec, ad) is not None:
            adlar.append(ad)
    return adlar


def _zorunlu_mu(spec, ad):
    """Hacmi olmadan tukenme KOSULAMAYAN malzeme: fisil ya da kullanicinin ek listesi.
    Yalniz zehir olan (fisil degil) malzemenin hacmi kesin degilse tukenmeye
    katilmaz ve dogrulama UYARIR (hacimsiz_zehirler)."""
    m = sema.malzeme_bul(spec, ad) or {}
    return _fisil_mi(m) or ad in ((spec.get("tukenme") or {}).get("ek_malzemeler") or [])


def _sayim(spec, dolgu, hedef, esleme=None, derinlik=0):
    """'dolgu' icinde 'hedef' cubuk/plaka kac kez geciyor (demetler icinden)."""
    if not dolgu or derinlik > 8:
        return 0
    if dolgu == hedef:
        return 1
    d = sema.demet_bul(spec, dolgu)
    if d is None:
        return 0
    anahtar = d.get("anahtar") or {}
    toplam = 0
    for satir in d.get("harita") or []:
        for harf in satir:
            if harf in anahtar:
                toplam += _sayim(spec, anahtar[harf], hedef, None, derinlik + 1)
    return toplam


def _kor_sayimi(spec, kor, dolgu, hedef, esleme=None):
    """Bir katmanin dolgusunda hedef kac kez var (kare/altigen kor haritasi dahil).
    Altigen harita halka listesidir; her harf bir konumdur, sayim aynidir."""
    if kor["tur"] in sema.HARITALI_KORLAR and dolgu is None:
        anahtar = dict(kor.get("anahtar") or {})
        if esleme:
            anahtar.update(esleme)
        toplam = 0
        for satir in kor.get("harita") or []:
            for harf in satir:
                if harf in anahtar:
                    toplam += _sayim(spec, anahtar[harf], hedef)
        return toplam
    return _sayim(spec, dolgu or sema.ana_dolgu(kor), hedef)


def _eksenel_dilimler(kor):
    """[(yukseklik, dolgu_adi|None, anahtar|None)]. 2B modelde tek dilim, 1 cm."""
    katmanlar = sema.eksenel_katmanlar(kor)
    if katmanlar:
        return [(z1 - z0, b.get("dolgu"), b.get("anahtar")) for z0, z1, b in katmanlar]
    h = sema.kor_yuksekligi(kor)
    return [(h if h else 1.0, None, None)]



def yakit_ornek_sayisi(spec):
    """
    Yanabilir malzemelerin geometrideki en buyuk ORNEK (hucre) sayisi.
    "Cubuk cubuk yanma" (diff_burnable_mats) her ornegi ayri malzeme yapar;
    tek ornekte (pin hucre, tek kabuklu kure, homojen tek katmanli kor)
    hicbir sey degistirmez. Sayim tukenme.hacimler()'in izledigi yolu izler
    (haritaya / demet anahtarina dogrudan konan malzeme dahil).
    uygunluk.tukenme_ayirma_anlamli bunu kullanir.
    """
    from cekirdek import tukenme_hacim
    kor = spec.get("kor") or {}
    adlar = yanabilir_adlar(spec)
    if kor.get("tur") == "kuresel":
        return max([sum(1 for k in kor.get("kabuklar") or [] if k.get("malzeme") == ad)
                    for ad in adlar] or [0])
    dilimler = _eksenel_dilimler(kor)

    def sayim(parca):
        return sum(_kor_sayimi(spec, kor, d, parca, e) for _h, d, e in dilimler)

    en_cok = 0
    for ad in adlar:
        n = 0
        for c in spec.get("cubuklar", []):
            bolge = sum(1 for b in c.get("bolgeler") or [] if b.get("malzeme") == ad)
            if bolge:
                n += bolge * sayim(c["ad"])
        for p in spec.get("plakalar", []):
            if p.get("et_malzeme") == ad:
                n += int(p.get("plaka_sayisi") or 1) * sayim(p["ad"])
        if kor.get("tur") == "tamburlu":
            n += sum(1 for _h, d, _e in dilimler if (d or kor.get("dolgu")) == ad)
        else:
            n += tukenme_hacim.dogrudan_yerlesim(spec, kor, ad, dilimler)["ornek"]
        en_cok = max(en_cok, n)
    return en_cok


def _kuresel_hacim(kor, ad):
    V, parcalar, r_ic = 0.0, [], 0.0
    for k in kor.get("kabuklar") or []:
        if k.get("malzeme") == ad:
            v = 4.0 / 3.0 * math.pi * (k["r"] ** 3 - r_ic ** 3)
            V += v
            parcalar.append("kabuk r = %g cm: %.4g cm³" % (k["r"], v))
        r_ic = k["r"]
    return {"hacim": V if V > 0 else None, "yontem": "analitik" if V > 0 else "yok",
            "ayrinti": "; ".join(parcalar)}


def _cubuk_hacmi(spec, kor, ad, dilimler, sorunlar):
    """Cubuk bolgelerindeki 'ad' hacmi (V, parcalar); kesin olmayanlar sorunlar'a."""
    V, parcalar = 0.0, []
    for c in spec.get("cubuklar", []):
        bolgeler = c.get("bolgeler") or []
        kontrol = c.get("tur") == "kontrol"
        if kontrol and c.get("izleyici_malzeme") == ad:
            sorunlar.append("'%s' kontrol çubuğunun izleyicisi (daldırmaya bağlı)" % c["ad"])
        for i, b in enumerate(bolgeler):
            if b.get("malzeme") != ad:
                continue
            if b.get("r") is None:
                sorunlar.append("'%s' çubuğunun dış bölgesi (alan kafes adımına bağlı)"
                                % c["ad"])
                continue
            if kontrol:
                sorunlar.append("'%s' kontrol çubuğu (daldırmaya bağlı)" % c["ad"])
                continue
            r_ic = bolgeler[i - 1]["r"] if i > 0 else 0.0
            alan = math.pi * (b["r"] ** 2 - r_ic ** 2)
            for h, dolgu, esleme in dilimler:
                n = _kor_sayimi(spec, kor, dolgu, c["ad"], esleme)
                if n:
                    V += alan * h * n
                    parcalar.append("%s, %d. bölge: %d adet × %g cm" % (c["ad"], i + 1, n, h))
    return V, parcalar


def _plaka_hacmi(spec, kor, ad, dilimler):
    V, parcalar = 0.0, []
    for p in spec.get("plakalar", []):
        if p.get("et_malzeme") != ad:
            continue
        alan = p["et_kalinlik"] * p["plaka_genislik"] * p["plaka_sayisi"]
        for h, dolgu, esleme in dilimler:
            n = _kor_sayimi(spec, kor, dolgu, p["ad"], esleme)
            if n:
                V += alan * h * n
                parcalar.append("%s: %d eleman × %g cm" % (p["ad"], n, h))
    return V, parcalar


def _malzeme_hacmi(spec, ad, dilimler):
    """Tek bir yanabilir malzemenin hacim kaydi (hacimler() icin)."""
    from cekirdek import tukenme_hacim
    kor = spec["kor"]
    if kor["tur"] == "kuresel":
        return _kuresel_hacim(kor, ad)
    sorunlar = []
    V, parcalar = _cubuk_hacmi(spec, kor, ad, dilimler, sorunlar)
    v, p = _plaka_hacmi(spec, kor, ad, dilimler)
    V, parcalar = V + v, parcalar + p
    if kor["tur"] == "tamburlu":
        # kor silindirini dogrudan dolduran homojen malzeme
        R = float(kor.get("kor_yaricap") or 0.0)
        for h, dolgu, _e in dilimler:
            if (dolgu or kor.get("dolgu")) == ad:
                V += math.pi * R * R * h
                parcalar.append("kor silindiri R = %g cm × %g cm" % (R, h))
    else:
        d = tukenme_hacim.dogrudan_yerlesim(spec, kor, ad, dilimler)
        V, parcalar, sorunlar = V + d["hacim"], parcalar + d["parcalar"], sorunlar + d["sorunlar"]
        altigen = kor["tur"] == "altigen_kafes"
        if kor.get("dolgu") == ad or any(dd == ad and not altigen for _h, dd, _e in dilimler):
            sorunlar.append("katmanı/koru doğrudan dolduruyor")
    if sorunlar:
        return {"hacim": None, "yontem": tukenme_hacim.KESIN_DEGIL,
                "ayrinti": "hacmi kesin değil: " + "; ".join(sorunlar)}
    if V > 0:
        return {"hacim": V, "yontem": "analitik", "ayrinti": "; ".join(parcalar)}
    from cekirdek import uygunluk
    if ad in (uygunluk.geometri_icerigi(spec).get("malzeme") or set()):
        # geometride var ama analitik yolu yok (or. kontrol tamburu emicisi)
        return {"hacim": None, "yontem": tukenme_hacim.KESIN_DEGIL,
                "ayrinti": "bu yerleşim için analitik hacim yok (ör. kontrol tamburu)"}
    return {"hacim": None, "yontem": "yok", "ayrinti": "malzeme geometride bulunamadı"}


def _hacim_tablosu(spec):
    """Butun yanabilir malzemelerin kaydi + "zorunlu" (bkz. _zorunlu_mu)."""
    dilimler = _eksenel_dilimler(spec["kor"])
    return {ad: dict(_malzeme_hacmi(spec, ad, dilimler), zorunlu=_zorunlu_mu(spec, ad))
            for ad in yanabilir_adlar(spec)}


def hacimler(spec):
    """
    {malzeme_adi: {"hacim": cm3|None, "yontem": str, "ayrinti": str, "zorunlu": bool}}

    2B modelde hacim 1 cm yukseklik icindir; guc yogunlugu kullanildigi icin
    bu tutarlidir (kutle ve guc ayni oranda olceklenir).
    Analitik hesaplanamayan fisil (zorunlu) malzeme icin hacim None doner
    (yontem "stokastik hesap gerekli"); tukenme onu KOSMAZ. Hacmi kesin
    olmayan salt zehir burada YOKTUR: tukenmeye katilmaz, bkz.
    hacimsiz_zehirler() (dogrulama uyarir).
    """
    return {ad: v for ad, v in _hacim_tablosu(spec).items() if v["hacim"] or v["zorunlu"]}


def hacimsiz_zehirler(spec):
    """{ad: ayrinti}: geometride yer alan yanabilir zehir ama hacmi kesin degil ->
    tukenmeye katilmaz. Geometride hic olmayan (tanimli ama kullanilmayan)
    zehir burada yoktur: yakilacak bir sey yok."""
    return {ad: v["ayrinti"] for ad, v in _hacim_tablosu(spec).items()
            if not v["hacim"] and not v["zorunlu"] and v["yontem"] != "yok"}


def stokastik_hacimler(spec, adlar, orneklem=2_000_000, dizin=None):
    """
    OpenMC'nin stokastik hacim hesabi. Analitik hacmin DOGRULANMASI ve
    analitik hesaplanamayan malzemeler icin. {ad: (hacim, sapma)}.
    """
    import tempfile
    import openmc
    from cekirdek import kurucu
    model, bilgi = kurucu.kur(spec)
    model.tallies = openmc.Tallies()
    nesneler = bilgi["malzemeler"]
    alanlar = [nesneler[a] for a in adlar if a in nesneler]
    gx, gy = bilgi["sinir_kutu"]
    h = sema.kor_yuksekligi(spec["kor"])
    z = (h / 2.0) if h else 0.5
    if spec["kor"]["tur"] == "kuresel":
        r = gx / 2.0
        alt, ust = (-r, -r, -r), (r, r, r)
    else:
        alt, ust = (-gx / 2, -gy / 2, -z), (gx / 2, gy / 2, z)
    vc = openmc.VolumeCalculation(alanlar, orneklem, alt, ust)
    model.settings.volume_calculations = [vc]
    dizin = dizin or tempfile.mkdtemp(prefix="tukenme_hacim_")
    eski = os.getcwd()
    try:
        os.chdir(dizin)
        model.export_to_model_xml()
        openmc.calculate_volumes(output=False)
        sonuc = openmc.VolumeCalculation.from_hdf5(os.path.join(dizin, "volume_1.h5"))
    finally:
        os.chdir(eski)
    cikti = {}
    ters = {id(v): k for k, v in nesneler.items()}
    for m in alanlar:
        v = sonuc.volumes[m.id]
        cikti[ters[id(m)]] = (float(v.nominal_value), float(v.std_dev))
    return cikti


# ============================================================================
# Model hazirlama ve kosu
# ============================================================================

def hazirla(spec):
    """
    Tukenmeye hazir model. DONER (model, bilgi).

    bilgi: {"zincir": zincir_secimi(), "hacimler": hacimler(),
            "agir_metal_g": float, "yanabilir": [ad], "atlanan": {ad: ayrinti}}
    Hacmi hesaplanamayan fisil malzeme varsa ValueError -- tahminle devam
    etmek yanma hizini sessizce bozardi. Hacmi kesin olmayan salt zehir
    tukenmeye katilmaz ("atlanan"; dogrulama bunu UYARI olarak gosterir).
    Cubuk cubuk yanmada (malzemeleri_ayir) ornekler burada, ornek basina
    kesin hacimle ayrilir (tukenme_hacim.ornekleri_ayir).
    Dogrulama kapisi burada YOK (--hazirla bilgi yolu); kosu calistir()'dadir.
    """
    from cekirdek import kurucu, tukenme_hacim
    from cekirdek.gunluk import kaydedici
    model, kbilgi = kurucu.kur(spec)
    zs = zincir_secimi(spec)
    tamam, mesaj, _ = veri_bilgi.zincir_kontrol(zs["yol"])
    if not tamam:
        raise ValueError(mesaj)

    hv = hacimler(spec)
    eksik = [a for a, v in hv.items() if not v["hacim"]]
    if eksik:
        raise ValueError(
            "hacmi analitik hesaplanamayan yanabilir malzeme: %s (%s). "
            "Tükenme kesin hacim gerektirir."
            % (", ".join(eksik), "; ".join(hv[a]["ayrinti"] for a in eksik)))
    if not hv:
        raise ValueError("modelde yanabilir (fisil) malzeme yok")
    atlanan = hacimsiz_zehirler(spec)
    if atlanan:
        kaydedici(__name__).warning("tükenmeye katılmayan yanabilir zehirler: %s",
                                    ", ".join(sorted(atlanan)))
    nesneler = kbilgi["malzemeler"]
    agir = 0.0
    for ad, v in hv.items():
        m = nesneler[ad]
        m.depletable = True
        m.volume = v["hacim"]
        agir += _agir_metal_kutlesi(m)
    ornek = 0
    if (spec.get("tukenme") or {}).get("malzemeleri_ayir"):
        ornek = tukenme_hacim.ornekleri_ayir(model, spec, hv, {a: nesneler[a] for a in hv})
    return model, {"zincir": zs, "hacimler": hv, "agir_metal_g": agir,
                   "yanabilir": list(hv), "atlanan": atlanan, "ornek_sayisi": ornek}


def _agir_metal_kutlesi(m):
    """Malzemedeki Z >= 90 nuklidlerin kutlesi [g] (m.volume ayarli olmali)."""
    import openmc.data
    toplam = 0.0
    for nuklid, yog in m.get_nuclide_atom_densities().items():   # atom/b-cm
        if _z(nuklid) >= 90:
            toplam += yog * 1e24 * m.volume * openmc.data.atomic_mass(nuklid) \
                / openmc.data.AVOGADRO
    return toplam


def yanma(zaman_gun, guc_yogunlugu):
    """Yanma [MWd/kgHM] = p [W/g] x t [gun] / 1000."""
    return guc_yogunlugu * zaman_gun / 1000.0


def kapi(spec, veri_kontrolu=True):
    """
    Tukenme kosusunun dogrulama kapisi: dogrula.kapi, tukenme kurallari
    ACIK olarak (spec'teki tukenme.var ne olursa olsun; spec DEGISMEZ).
    Hata varsa dogrula.DogrulamaHatasi; yoksa bulgular (uyari, bilgi).
    """
    import copy
    from cekirdek import dogrula
    denetlenen = copy.deepcopy(spec)
    denetlenen.setdefault("tukenme", {})["var"] = True
    return dogrula.kapi(denetlenen, veri_kontrolu=veri_kontrolu)


def calistir(spec, dizin, geri_cagir=None, veri_kontrolu=True):
    """
    Tukenme kosusu. dizin icinde depletion_results.h5 uretir.
    OMP_NUM_THREADS bu fonksiyondan ONCE ayarlanmis olmali (bkz. _terminal).

    Once dogrulama kapisi (kapi): hata varsa dogrula.DogrulamaHatasi ve
    dizindeki ONCEKI sonuc ile spec kaydi SILINMEZ. bilgi["dogrulama"]:
    kapidan gecen bulgular (uyari, bilgi).
    """
    bulgular = kapi(spec, veri_kontrolu=veri_kontrolu)
    import openmc.deplete as d
    t = spec["tukenme"]
    model, bilgi = hazirla(spec)
    bilgi["dogrulama"] = bulgular
    zs = bilgi["zincir"]
    os.makedirs(dizin, exist_ok=True)
    # Eski sonuc SILINIR, sonra spec kaydi yazilir. Sira onemli: kosu yarida
    # kalirsa dizinde eski bir sonuc ile YENI bir spec kaydi yan yana kalir
    # ve eski sonuc "guncel" diye gosterilirdi.
    onceki = os.path.join(dizin, "depletion_results.h5")
    if os.path.exists(onceki):
        os.remove(onceki)
    spec_kaydet(spec, dizin)
    eski = os.getcwd()
    try:
        os.chdir(dizin)
        # Ornekler hazirla()'da kesin hacimle ayrildi; OpenMC'nin esit bolmesi
        # (diff_burnable_mats) bu yuzden KAPALI.
        op = d.CoupledOperator(
            model, zs["yol"],
            diff_burnable_mats=False,
            normalization_mode="fission-q",
            fission_yield_mode="constant",
            fission_yield_opts={"energy": zs["verim_enerjisi"]},
        )
        Sinif = {"cecm": d.CECMIntegrator,
                 "predictor": d.PredictorIntegrator}[t.get("entegrator") or "cecm"]
        integ = Sinif(op, list(t["adimlar"]),
                      power_density=float(t["guc_yogunlugu"]),
                      timestep_units=t.get("adim_birimi") or "d")
        integ.integrate()
    finally:
        os.chdir(eski)
    return os.path.join(dizin, "depletion_results.h5"), bilgi


# Sonuc okuma kaynagi onbellegi: {(h5, boyut, mtime, spec imzasi): (Results,
# {malzeme_id: ad}, hacimler)}. Olculdu: Results() 3820 nuklidli dosyada
# 1.8 s, kurucu.kur + hacimler ~0.5 s; secim degisince bunlar TEKRARLANMAZ.
_SONUC_KAYNAGI = {}
_SONUC_KAYNAGI_EN_COK = 2


def _sonuc_kaynagi(h5, spec):
    """(Results, {malzeme_id: ad}, hacimler) -- dosya ve spec degismedikce onbellekten."""
    import json
    import openmc.deplete as d
    from cekirdek import kurucu
    bilgi = os.stat(h5)
    anahtar = (os.path.abspath(h5), bilgi.st_size, bilgi.st_mtime,
               json.dumps(spec, sort_keys=True, default=str))
    kaynak = _SONUC_KAYNAGI.get(anahtar)
    if kaynak is not None:
        return kaynak
    r = d.Results(h5)
    _m, kb = kurucu.kur(spec)
    ad_by_id = {str(m.id): ad for ad, m in kb["malzemeler"].items()}
    kaynak = (r, ad_by_id, hacimler(spec))
    while len(_SONUC_KAYNAGI) >= _SONUC_KAYNAGI_EN_COK:
        _SONUC_KAYNAGI.pop(next(iter(_SONUC_KAYNAGI)))
    _SONUC_KAYNAGI[anahtar] = kaynak
    return kaynak


def sonuc_oku(h5, spec, izlenen=None):
    """
    DONER {"zaman_d", "yanma", "k", "k_sapma", "atomlar": {malz: {nuklid: [..]}},
           "yogunluk": {malz: {nuklid: [atom/b-cm]}}, "adim_sayisi",
           "bulunamayan": [sonuc dosyasinda olmayan izlenen adlar]}

    izlenen verilmezse spec'teki tukenme.izlenen okunur. Verilirse (arayuzde
    secim degisti) ayni h5'ten okunur; kosu tekrarlanmaz. Bulunamayan ad
    (or. "Xe-135") eskiden SESSIZCE atlaniyordu; simdi listelenir ve loglanir.
    """
    from cekirdek.gunluk import kaydedici
    r, ad_by_id, hv = _sonuc_kaynagi(h5, spec)
    zaman, k = r.get_keff(time_units="d")
    p = float(spec["tukenme"]["guc_yogunlugu"])
    if izlenen is None:
        izlenen = (spec.get("tukenme") or {}).get("izlenen") or []
    bilinen = r[0].index_nuc
    bulunamayan = [n for n in izlenen if n not in bilinen]
    atomlar, yogunluk = {}, {}
    for mid in r[0].index_mat.keys():
        ad = ad_by_id.get(str(mid), str(mid))
        atomlar[ad], yogunluk[ad] = {}, {}
        V = (hv.get(ad) or {}).get("hacim")
        for n in (n for n in izlenen if n in bilinen):
            _t, a = r.get_atoms(str(mid), n)
            atomlar[ad][n] = [float(x) for x in a]
            if V:
                yogunluk[ad][n] = [float(x) / V * 1e-24 for x in a]
    if bulunamayan:
        kaydedici(__name__).warning("tükenme sonucunda bulunamayan nüklidler (%s): %s",
                                    h5, ", ".join(bulunamayan))
    return {
        "zaman_d": [float(x) for x in zaman],
        "yanma": [yanma(float(x), p) for x in zaman],
        "k": [float(x) for x in k[:, 0]],
        "k_sapma": [float(x) for x in k[:, 1]],
        "atomlar": atomlar,
        "yogunluk": yogunluk,
        "adim_sayisi": len(zaman) - 1,
        "bulunamayan": bulunamayan,
    }


# ============================================================================
# Onceki kosu
#   Arayuz acildiginda son koşunun sonucu gosterilir. Tuzak: sonuc SU ANKI
#   spec'e ait olmayabilir (kullanici kosudan sonra gucu ya da zenginligi
#   degistirmis olabilir). Eski bir sonucu guncelmis gibi gostermek, hic
#   gostermemekten kotudur. Bu yuzden kosu basinda spec'in kopyasi yazilir;
#   acilista karsilastirilir ve sonuc O KOPYAYA gore okunur (malzeme
#   kimlikleri ve hacimler kosudaki modelden gelsin).
# ============================================================================

SPEC_KAYDI = "tukenme_spec.json"

# Fizigi etkilemeyen bolumler: bunlar degisti diye sonuc eskimez.
_FIZIK_DISI = ("ad", "aciklama", "calistirma")


def kosu_dizini(spec, proje_yolu=None):
    """Tukenme sonuclarinin dizini: <proje dizini>/<calistirma.dizin>_tukenme."""
    taban = sema.kosu_tabani(proje_yolu)
    dizin = (spec.get("calistirma") or {}).get("dizin", "kosu") + "_tukenme"
    return dizin if os.path.isabs(dizin) else os.path.join(taban, dizin)


def _fizik_kismi(spec):
    """
    Sonucu etkileyen kisim. ad/aciklama/calistirma, tukenme.var ve
    tukenme.izlenen cikarilir: tukenmeyi kapatip acmak ya da izlenen nuklid
    secimini degistirmek sonucu eskitmez (izlenen yalnizca h5'ten hangi
    nuklidlerin OKUNACAGINI belirler; kosu butun zinciri izler).

    Karsilastirma METIN (json/hash) ile degil Python esitligiyle yapilir:
    JSON'da 3 ile 3.0 farkli metindir ama ayni sayidir; hash kullanmak
    degismemis bir modeli "eski" gosterirdi.
    """
    import copy
    sade = {k: copy.deepcopy(v) for k, v in sema.tamamla(spec).items()
            if k not in _FIZIK_DISI}
    sade.get("tukenme", {}).pop("var", None)
    sade.get("tukenme", {}).pop("izlenen", None)
    sade.pop("surum", None)
    return sade


def spec_kaydet(spec, dizin):
    import json
    with open(os.path.join(dizin, SPEC_KAYDI), "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)


def onceki_sonuc(spec, dizin):
    """
    Dizindeki son tukenme sonucu. Sonuc yoksa None.
    DONER {"h5", "tarih": float, "durum": "guncel"|"eski"|"bilinmiyor",
           "farklar": [bolum], "sonuc": sonuc_oku(...)}
    """
    h5 = os.path.join(dizin, "depletion_results.h5")
    if not os.path.exists(h5):
        return None
    durum, farklar = eskime(spec, dizin)
    kayit = _kayit_oku(dizin)
    return {"h5": h5, "tarih": os.path.getmtime(h5), "durum": durum,
            "farklar": farklar, "sonuc": sonuc_oku(h5, kayit or spec)}


def _kayit_oku(dizin):
    yol = os.path.join(dizin, SPEC_KAYDI)
    return sema.yukle(yol) if os.path.exists(yol) else None


# Spec bolumlerinin kullaniciya gorunen adlari (eskime farklari icin).
BOLUM_ADLARI = {
    "malzemeler": "malzemeler", "cubuklar": "çubuklar", "plakalar": "plaka elemanları",
    "demetler": "demetler", "kor": "kor", "ayarlar": "hesap ayarları",
    "tallyler": "tally'ler", "guc_dagilimi": "güç dağılımı", "tukenme": "tükenme ayarları",
}
SPEKTRUM_ADLARI = {"termal": "termal", "hizli": "hızlı"}


def fark_metni(farklar):
    """Eskime farklarinin okunur listesi: "malzemeler, hesap ayarları"."""
    return ", ".join(BOLUM_ADLARI.get(f, f) for f in farklar)


def eskime(spec, dizin):
    """
    (durum, farklar): sonuc bu spec'e mi ait? Sonucu OKUMAZ -- arayuz her
    duzenlemede cagirir, ucuz olmali.
      "guncel"     : fizigi etkileyen her sey ayni
      "eski"       : farklar = degisen spec bolumleri
      "bilinmiyor" : kosunun spec kaydi yok
    """
    kayit = _kayit_oku(dizin)
    if kayit is None:
        return "bilinmiyor", []
    a, b = _fizik_kismi(spec), _fizik_kismi(kayit)
    farklar = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    return ("eski" if farklar else "guncel"), farklar


def transport_sayisi(spec):
    """Toplam transport cozumu: (adim + 1) x entegrator basina transport."""
    t = spec.get("tukenme") or {}
    n = len(t.get("adimlar") or [])
    basina = 2 if (t.get("entegrator") or "cecm") == "cecm" else 1
    return n * basina + 1


# ============================================================================
# Terminal
# ============================================================================

def _terminal(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="python3 -m cekirdek.tukenme")
    ap.add_argument("spec")
    ap.add_argument("-s", "--is-parcacigi", type=int, default=None)
    ap.add_argument("--dizin", default=None)
    ap.add_argument("--hazirla", action="store_true",
                    help="koşmadan hacim, zincir ve ağır metal bilgisini yazdır")
    ap.add_argument("--veri-kontrolu-yok", action="store_true",
                    help="doğrulamada nüklid/kütüphane denetimini atla")
    a = ap.parse_args(argv)

    # libgomp OMP_NUM_THREADS'i KUTUPHANE YUKLENIRKEN okur; openmc.deplete'in
    # ice aktarilmasi kutuphaneyi yukler. Bu yuzden once ortam, sonra import.
    if a.is_parcacigi:
        os.environ["OMP_NUM_THREADS"] = str(a.is_parcacigi)

    import warnings
    warnings.filterwarnings("ignore")
    spec = sema.yukle(a.spec)
    spec.setdefault("tukenme", {})["var"] = True
    zs = zincir_secimi(spec)
    t = spec["tukenme"]
    print("=" * 74)
    print(" TÜKENME: %s" % spec.get("ad", ""))
    print("=" * 74)
    print("  zincir        : %s  (%s)" % (os.path.basename(zs["yol"]), zs["gerekce"]))
    print("  fisyon verimi : %s eV (%s spektrum)"
          % (zs["verim_enerjisi"], SPEKTRUM_ADLARI.get(zs["temel"], zs["temel"])))
    print("  güç yoğunluğu : %g W/gHM" % float(t["guc_yogunlugu"]))
    print("  adımlar       : %s %s  → %d transport"
          % (", ".join("%g" % float(x) for x in t["adimlar"]),
             {"d": "gün"}.get(t.get("adim_birimi", "d"), t.get("adim_birimi", "d")),
             transport_sayisi(spec)))
    for ad, v in hacimler(spec).items():
        print("  hacim %-10s: %s cm³ [%s] %s" % (ad, ("%.6g" % v["hacim"]) if v["hacim"] else "—",
                                                  v["yontem"], v["ayrinti"]))
    if a.hazirla:
        _m, b = hazirla(spec)
        print("  ağır metal    : %.6g g" % b["agir_metal_g"])
        return 0

    dizin = a.dizin or os.path.join(os.path.dirname(os.path.abspath(a.spec)),
                                    (spec.get("calistirma") or {}).get("dizin", "kosu") + "_tukenme")
    from cekirdek import dogrula
    try:
        h5, bilgi = calistir(spec, dizin, veri_kontrolu=not a.veri_kontrolu_yok)
    except dogrula.DogrulamaHatasi as e:
        print("\n  DOĞRULAMA: koşu başlatılmadı (%d hata)" % len(e.bulgular))
        for b in e.bulgular:
            print("  %s" % b)
        return 2
    for b in bilgi["dogrulama"]:
        print("  %s" % b)
    s = sonuc_oku(h5, spec)
    print("\n  ağır metal: %.6g g" % bilgi["agir_metal_g"])
    print("  %8s %10s %18s" % ("gün", "MWd/kg", "k-eff"))
    for z, b, k, sk in zip(s["zaman_d"], s["yanma"], s["k"], s["k_sapma"]):
        print("  %8.2f %10.3f %10.5f ± %.5f" % (z, b, k, sk))
    print("\n  sonuç: %s" % h5)
    return 0


if __name__ == "__main__":
    sys.exit(_terminal(sys.argv[1:]))
