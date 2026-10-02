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
import types

from cekirdek import sema, veri_bilgi
from cekirdek import tukenme_spektrum as _spektrum
from cekirdek.ceviri import N_, _, etkin_dil, pgettext
from cekirdek.uygunluk_bellek import Bellek, icerik_anahtari

# Spec icerigine gore bellek (v3 H1): Tukenme sekmesi her doldurmada yeniden
# sayiyor ve hacimleri yeniden hesapliyordu (SFR: 0.4 s + 1.5 s).
_ORNEK_SAYISI = Bellek("yakit_ornek_sayisi")
_HACIM_KAYDI = Bellek("tukenme_hacim_kaydi")

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

# Moderator sayilan S(a,b) kayitlari: cekirdek/tukenme_spektrum.py.


# ============================================================================
# Zincir secimi
# ============================================================================

def zincir_secimi(spec, kosu_dizini=None):
    """
    DONER {"tur", "yol", "spektrum", "verim_enerjisi", "gerekce", "yontem"}
    yontem: "ealf" | "komsuluk" | "genel" (otomatik secimin yolu) ya da
    "kullanici". kosu_dizini verilirse oradaki EALF tally'si kullanilir.
    """
    t = spec.get("tukenme") or {}
    istek = t.get("zincir") or "otomatik"
    spektrum, gerekce, yontem = _spektrum.tahmin(spec, kosu_dizini)
    if istek == "otomatik":
        tur = spektrum
        gerekce = _("otomatik: %s") % gerekce
    else:
        tur = istek
        gerekce = _("kullanıcı seçimi")
        yontem = "kullanici"
    temel = "hizli" if tur.endswith("hizli") else "termal"
    return {
        "tur": tur,
        "yol": os.path.join(veri_bilgi.zincir_dizini(), ZINCIRLER[tur]),
        "spektrum": spektrum,
        "temel": temel,
        "verim_enerjisi": VERIM_ENERJISI[temel],
        "gerekce": gerekce,
        "yontem": yontem,
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


def otomatik_yanan_adlar(spec):
    """Kendiliginden yanan malzemeler (ek listeden bagimsiz): fisil + yanabilir zehir."""
    return [m["ad"] for m in spec.get("malzemeler", []) if _fisil_mi(m) or _zehir_mi(m)]


def yanabilir_adlar(spec):
    """Yanacak malzemelerin adlari: fisil olanlar + yanabilir zehirler + ek liste."""
    adlar = otomatik_yanan_adlar(spec)
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


def _sayim(spec, dolgu, hedef, derinlik=0):
    """'dolgu' icinde 'hedef' cubuk/plaka kac kez geciyor (demetler icinden)."""
    return _bellekli_sayim(spec, dolgu, hedef, derinlik, {})


def _bellekli_sayim(spec, dolgu, hedef, derinlik, bellek):
    """_sayim; bellek {(dolgu, derinlik): sayi} AYNI cagri icinde ayni demetin
    yeniden sayilmamasi icin (v3 H1: SFR kor haritasinda 2.5 milyon ozyineleme,
    ~1.5 s). Derinlik anahtarda: sonuc bellekli ve belleksiz ayni. Hashlenemeyen
    dolgu (bozuk spec) bellege girmez; eskisi gibi sayilir (demet bulunmaz -> 0)."""
    if not dolgu or derinlik > 8:
        return 0
    if dolgu == hedef:
        return 1
    try:
        anahtar_b = (dolgu, derinlik)
        if anahtar_b in bellek:
            return bellek[anahtar_b]
    except TypeError:
        anahtar_b = None
    d = sema.demet_bul(spec, dolgu)
    toplam = 0
    if d is not None:
        anahtar = d.get("anahtar") or {}
        for satir in d.get("harita") or []:
            for harf in satir:
                if harf in anahtar:
                    toplam += _bellekli_sayim(spec, anahtar[harf], hedef, derinlik + 1, bellek)
    if anahtar_b is not None:
        bellek[anahtar_b] = toplam
    return toplam


def _kor_sayimi(spec, kor, dolgu, hedef, esleme=None):
    """Bir katmanin dolgusunda hedef kac kez var (kare/altigen kor haritasi dahil).
    Altigen harita halka listesidir; her harf bir konumdur, sayim aynidir."""
    bellek = {}
    if kor["tur"] in sema.HARITALI_KORLAR and dolgu is None:
        anahtar = dict(kor.get("anahtar") or {})
        if esleme:
            anahtar.update(esleme)
        toplam = 0
        for satir in kor.get("harita") or []:
            for harf in satir:
                if harf in anahtar:
                    toplam += _bellekli_sayim(spec, anahtar[harf], hedef, 0, bellek)
        return toplam
    return _bellekli_sayim(spec, dolgu or sema.ana_dolgu(kor), hedef, 0, bellek)


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
    hicbir sey degistirmez. uygunluk.tukenme_ayirma_anlamli bunu kullanir.
    Sayim tukenme_hacim.ornek_sayisi'ndadir (sablon ve agac modu).
    """
    return _ORNEK_SAYISI.al(icerik_anahtari(spec), lambda: _yakit_ornek_sayisi(spec))


def _yakit_ornek_sayisi(spec):
    from cekirdek import tukenme_hacim
    return max([tukenme_hacim.ornek_sayisi(spec, ad) for ad in yanabilir_adlar(spec)] or [0])


def _hacim_tablosu(spec):
    """Butun yanabilir malzemelerin kaydi + "zorunlu" (bkz. _zorunlu_mu).
    Sablon modunda tukenme_hacim.sablon_malzeme_hacmi, gelismis (agac)
    modunda geometri.hacim.analitik (agac gezintisi)."""
    dil = etkin_dil()
    anahtar = (icerik_anahtari(spec), dil)
    kayit = _HACIM_KAYDI.al(anahtar, lambda: _hacim_kaydi_hesapla(spec))
    if etkin_dil() != dil:
        # Hesap surerken dil degisti (baska is parcacigi): metinler karisik
        # olabilir; eski dil anahtariyla saklanmaz, yeni dilde yeniden hesaplanir.
        _HACIM_KAYDI.unut(anahtar)
        kayit = _hacim_kaydi_hesapla(spec)
    return {ad: dict(v, zorunlu=_zorunlu_mu(spec, ad)) for ad, v in kayit.items()}


def _hacim_kaydi_hesapla(spec):
    """Degismez kayit (ayrinti metni etkin dilde: anahtarda dil var)."""
    from cekirdek import tukenme_hacim
    kayit = tukenme_hacim.malzeme_hacimleri(spec, yanabilir_adlar(spec))
    return types.MappingProxyType({ad: types.MappingProxyType(dict(v))
                                   for ad, v in kayit.items()})


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
    (geometri.hacim.stokastik; sablon ve agac modunda ayni kutu)
    """
    from cekirdek.geometri import hacim
    return hacim.stokastik(spec, adlar, orneklem, dizin)


def _hazir_hacimler(spec):
    """
    hazirla() icin (hv, atlanan, stokastik_adlar). Gelismis (agac) modunda
    kesin olmayan hacim (kesik konum/cubuk) stokastik hacme duser ve
    BILDIRILIR; cubuk cubuk yanmada bu HATA'dir (ornek hacmi kesin degil).
    """
    from cekirdek import tukenme_hacim
    tablo = _hacim_tablosu(spec)
    kesin_degil = [a for a, v in tablo.items() if not v["hacim"]
                   and v["yontem"] == tukenme_hacim.KESIN_DEGIL]
    if kesin_degil and sema.agac_modu(spec) and (spec.get("tukenme") or {}).get(
            "malzemeleri_ayir"):
        raise ValueError(
            _("çubuk çubuk yanma kesin örnek hacmi gerektirir; hacmi kesin olmayan "
            "(kesik) yanabilir malzeme: %s") % ", ".join(kesin_degil))
    tablo, dusen = tukenme_hacim.stokastik_tamamla(spec, tablo)
    hv = {ad: v for ad, v in tablo.items() if v["hacim"] or v["zorunlu"]}
    atlanan = {ad: v["ayrinti"] for ad, v in tablo.items()
               if not v["hacim"] and not v["zorunlu"] and v["yontem"] != "yok"}
    return hv, atlanan, dusen


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
    tamam, mesaj, _zincir = veri_bilgi.zincir_kontrol(zs["yol"])
    if not tamam:
        raise ValueError(mesaj)

    hv, atlanan, stokastik = _hazir_hacimler(spec)
    eksik = [a for a, v in hv.items() if not v["hacim"]]
    if eksik:
        raise ValueError(
            _("hacmi analitik hesaplanamayan yanabilir malzeme: %s (%s). "
            "Tükenme kesin hacim gerektirir.")
            % (", ".join(eksik), "; ".join(hv[a]["ayrinti"] for a in eksik)))
    if not hv:
        raise ValueError(_("modelde yanabilir (fisil) malzeme yok"))
    if stokastik:
        kaydedici(__name__).warning("stokastik hacimle tükenen malzemeler (kesik "
                                    "konum): %s", ", ".join(sorted(stokastik)))
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
                   "yanabilir": list(hv), "atlanan": atlanan, "ornek_sayisi": ornek,
                   "stokastik": stokastik}


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


def _klon_kaydi(model, spec, hv, nesneler):
    """
    Cubuk cubuk yanmanin (malzemeleri_ayir) klonlari: {malzeme_id: (ad, hacim)}.

    Klonlar kosudakiyle AYNI yolla (tukenme_hacim.ornekleri_ayir) kurulur;
    malzeme basina, Cell.paths (= distribcell ornek) sirasinda numaralanir:
    "uo2 #1", "uo2 #2", ... Boylece sonuc tablosu ve CSV klonlari kimlik
    numarasiyla ("1043") degil okunur adiyla gosterir ve her klonun kendi
    hacmi bilindigi icin yogunluk [atom/b-cm] hesaplanabilir.
    """
    from cekirdek import tukenme_hacim
    kayit = {}
    for ad, m in nesneler.items():
        once = {x.id for x in model.geometry.get_all_materials().values()}
        m.depletable = True
        m.volume = hv[ad]["hacim"]
        tukenme_hacim.ornekleri_ayir(model, spec, {ad: hv[ad]}, {ad: m})
        yeni = [x for x in model.geometry.get_all_materials().values()
                if x.id not in once]
        for i, klon in enumerate(sorted(yeni, key=lambda x: x.id), 1):
            kayit[str(klon.id)] = ("%s #%d" % (ad, i), klon.volume)
    return kayit


def _malzeme_haritasi(spec):
    """
    ({malzeme_id: gorunen ad}, {gorunen ad: hacim cm3}).
    Cubuk cubuk yanmada klonlar da (ad ve kendi hacmiyle) haritaya girer.
    """
    from cekirdek import kurucu
    model, kb = kurucu.kur(spec)
    hv = hacimler(spec)
    ad_by_id = {str(m.id): ad for ad, m in kb["malzemeler"].items()}
    hacim_by_ad = {ad: v.get("hacim") for ad, v in hv.items()}
    if not (spec.get("tukenme") or {}).get("malzemeleri_ayir"):
        return ad_by_id, hacim_by_ad
    nesneler = {a: kb["malzemeler"][a] for a in hv if a in kb["malzemeler"]}
    for mid, (ad, hacim) in _klon_kaydi(model, spec, hv, nesneler).items():
        ad_by_id[mid] = ad
        hacim_by_ad[ad] = hacim
    return ad_by_id, hacim_by_ad


def _sonuc_kaynagi(h5, spec):
    """(Results, {malzeme_id: ad}, {ad: hacim}) -- dosya/spec degismedikce onbellekten."""
    import json
    import openmc.deplete as d
    bilgi = os.stat(h5)
    anahtar = (os.path.abspath(h5), bilgi.st_size, bilgi.st_mtime,
               json.dumps(spec, sort_keys=True, default=str))
    kaynak = _SONUC_KAYNAGI.get(anahtar)
    if kaynak is not None:
        return kaynak
    r = d.Results(h5)
    ad_by_id, hacim_by_ad = _malzeme_haritasi(spec)
    kaynak = (r, ad_by_id, hacim_by_ad)
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
    r, ad_by_id, hacim_by_ad = _sonuc_kaynagi(h5, spec)
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
        V = hacim_by_ad.get(ad)
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
_FIZIK_DISI = ("ad", "aciklama", "calistirma") + sema.META_ALANLARI


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
    "malzemeler": N_("malzemeler"), "cubuklar": N_("çubuklar"),
    "plakalar": N_("plaka elemanları"), "demetler": N_("demetler"), "kor": N_("kor"),
    "ayarlar": N_("hesap ayarları"), "tallyler": N_("tally'ler"),
    "guc_dagilimi": N_("güç dağılımı"), "tukenme": N_("tükenme ayarları"),
}
# Turkce adlar (geriye uyum); gosterirken spektrum_adi() etkin dilde verir.
SPEKTRUM_ADLARI = {"termal": "termal", "hizli": "hızlı"}


def spektrum_adi(kod):
    """Spektrum turunun gorunen adi, etkin dilde (SPEKTRUM_ADLARI)."""
    return {"termal": pgettext("spektrum", "termal"),
            "hizli": pgettext("spektrum", "hızlı")}.get(kod, kod)


def fark_metni(farklar):
    """Eskime farklarinin okunur listesi: "malzemeler, hesap ayarları"."""
    return ", ".join(_(BOLUM_ADLARI[f]) if f in BOLUM_ADLARI else f for f in farklar)


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

# MAKINE ISARETI -- CEVRILMEZ. arayuz/sekme_tukenme._cikti_oku alt surecin
# ciktisini suzerken baslik satirini bu sabitle tanir ("TÜKENME" in satir);
# Ingilizce arayuzde de ayni kalmali (testler/test_ceviri_cekirdek CC5).
KOSU_ISARETI = "TÜKENME"


def kosu_basligi(spec):
    """Terminal ciktisinin baslik satiri: " TÜKENME: <model adi>" (isaret sabit)."""
    return " %s: %s" % (KOSU_ISARETI, spec.get("ad", ""))


def _terminal(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="python3 -m cekirdek.tukenme")
    ap.add_argument("spec")
    ap.add_argument("-s", "--is-parcacigi", type=int, default=None)
    ap.add_argument("--dizin", default=None)
    ap.add_argument("--hazirla", action="store_true",
                    help=_("koşmadan hacim, zincir ve ağır metal bilgisini yazdır"))
    ap.add_argument("--veri-kontrolu-yok", action="store_true",
                    help=_("doğrulamada nüklid/kütüphane denetimini atla"))
    a = ap.parse_args(argv)
    from cekirdek import veri_yolu
    veri_yolu.surece_uygula()   # K2: Veri sayfasi secimi (openmc.deplete ortami okur)

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
    print(kosu_basligi(spec))
    print("=" * 74)
    print(_("  zincir        : %s  (%s)") % (os.path.basename(zs["yol"]), zs["gerekce"]))
    print(_("  fisyon verimi : %s eV (%s spektrum)")
          % (zs["verim_enerjisi"], spektrum_adi(zs["temel"])))
    print(_("  güç yoğunluğu : %g W/gHM") % float(t["guc_yogunlugu"]))
    print(_("  adımlar       : %s %s  → %d transport")
          % (", ".join("%g" % float(x) for x in t["adimlar"]),
             {"d": _("gün")}.get(t.get("adim_birimi", "d"), t.get("adim_birimi", "d")),
             transport_sayisi(spec)))
    from cekirdek import tukenme_hacim
    for ad, v in hacimler(spec).items():
        print(_("  hacim %-10s: %s cm³ [%s] %s") % (ad, ("%.6g" % v["hacim"]) if v["hacim"] else "—",
                                                  tukenme_hacim.yontem_metni(v["yontem"]), v["ayrinti"]))
    if a.hazirla:
        _m, b = hazirla(spec)
        print(_("  ağır metal    : %.6g g") % b["agir_metal_g"])
        return 0

    dizin = a.dizin or os.path.join(os.path.dirname(os.path.abspath(a.spec)),
                                    (spec.get("calistirma") or {}).get("dizin", "kosu") + "_tukenme")
    from cekirdek import dogrula
    try:
        h5, bilgi = calistir(spec, dizin, veri_kontrolu=not a.veri_kontrolu_yok)
    except dogrula.DogrulamaHatasi as e:
        print(_("\n  DOĞRULAMA: koşu başlatılmadı (%d hata)") % len(e.bulgular))
        for b in e.tum_bulgular:          # hatalar + uyari/bilgi (tek denetim)
            print("  %s" % b)
        return 2
    for b in bilgi["dogrulama"]:
        print("  %s" % b)
    s = sonuc_oku(h5, spec)
    print(_("\n  ağır metal: %.6g g") % bilgi["agir_metal_g"])
    print("  %8s %10s %18s" % (_("gün"), "MWd/kg", "k-eff"))
    for z, b, k, sk in zip(s["zaman_d"], s["yanma"], s["k"], s["k_sapma"]):
        print("  %8.2f %10.3f %10.5f ± %.5f" % (z, b, k, sk))
    print(_("\n  sonuç: %s") % h5)
    return 0


if __name__ == "__main__":
    from cekirdek.ceviri import terminal_dili
    terminal_dili()                   # OPENMC_ARAYUZ_DIL verilmisse o dil
    sys.exit(_terminal(sys.argv[1:]))
