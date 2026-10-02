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
from cekirdek import spektrum as _y3          # Y3: tukenmede spektrum tally'leri kapali
from cekirdek.ceviri import _, etkin_dil
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
    model, kbilgi = kurucu.kur(_y3.tukenme_icin(spec))   # Y3 tukenmede kapali
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
                   "stokastik": stokastik, "nesneler": nesneler}


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
    from cekirdek import tukenme_ayar
    ek = tukenme_ayar.ayar_bulgulari(denetlenen)          # v3 Y4 ayarlari
    hatalar = [b for b in ek if b.seviye == "hata"]
    try:
        bulgular = dogrula.kapi(denetlenen, veri_kontrolu=veri_kontrolu)
    except dogrula.DogrulamaHatasi as e:
        raise dogrula.DogrulamaHatasi(e.bulgular + hatalar,
                                      tum_bulgular=e.tum_bulgular + ek) from None
    if hatalar:
        raise dogrula.DogrulamaHatasi(hatalar, tum_bulgular=bulgular + ek)
    return bulgular + ek


def calistir(spec, dizin, geri_cagir=None, veri_kontrolu=True):
    """
    Tukenme kosusu. dizin icinde depletion_results.h5 uretir.
    OMP_NUM_THREADS bu fonksiyondan ONCE ayarlanmis olmali (bkz. _terminal).

    Once dogrulama kapisi (kapi): hata varsa dogrula.DogrulamaHatasi ve
    dizindeki ONCEKI sonuc ile spec kaydi SILINMEZ. bilgi["dogrulama"]:
    kapidan gecen bulgular (uyari, bilgi). v3 Y4: entegrator, sogutma,
    surdurme, kritik arama ve hizli kip cekirdek/tukenme_kosu.py'dedir;
    bilgi["surdurulen"]: surdurmede onceki kosunun tamamlanmis adim sayisi.
    """
    bulgular = kapi(spec, veri_kontrolu=veri_kontrolu)
    from cekirdek import tukenme_ayar, tukenme_guc, tukenme_kosu, tukenme_surdur
    # v3 K3: guc tally'si kurulabilen modelde her adimda pin gucu sayilir
    # (spec kaydi kullanicinin spec'idir).
    model, bilgi = tukenme_guc.olcumlu_hazirla(hazirla, spec)
    bilgi["dogrulama"] = bulgular
    os.makedirs(dizin, exist_ok=True)
    onceki = (tukenme_surdur.onceki_durum(spec, dizin)
              if tukenme_ayar.surdur(spec["tukenme"]) else None)
    bilgi["surdurulen"] = onceki.tamam if onceki is not None else 0
    if onceki is None:
        # Eski sonuc SILINIR, sonra spec kaydi yazilir. Sira onemli: kosu yarida
        # kalirsa dizinde eski bir sonuc ile YENI bir spec kaydi yan yana kalir
        # ve eski sonuc "guncel" diye gosterilirdi.
        # (v3 K3) adim statepoint'leri yalniz bu arayuzun kayitli dizininde silinir.
        from cekirdek import tukenme_temizlik
        tukenme_temizlik.onceki_sonucu_temizle(dizin)
    spec_kaydet(spec, dizin)
    eski = os.getcwd()
    try:
        os.chdir(dizin)
        tukenme_kosu.kos(model, bilgi, spec, dizin, onceki)
    finally:
        os.chdir(eski)
    return os.path.join(dizin, "depletion_results.h5"), bilgi


# Sonuc okuma (v3 Y4: cekirdek/tukenme_oku.py), onceki kosu ve eskime
# (cekirdek/tukenme_kayit.py), terminal (cekirdek/tukenme_terminal.py) ayri
# modullerdedir; genel adlar burada yeniden disa aktarilir.
from cekirdek.tukenme_oku import (  # noqa: E402,F401
    _SONUC_KAYNAGI, _SONUC_KILIDI, _SONUC_KAYNAGI_EN_COK, _klon_kaydi,
    _malzeme_haritasi, _sonuc_kaynagi, sonuc_oku)
from cekirdek.tukenme_temizlik import SPEC_KAYDI  # noqa: E402,F401 (tek tanim)
from cekirdek.tukenme_kayit import (  # noqa: E402,F401
    _FIZIK_DISI, kosu_dizini, _fizik_kismi, spec_kaydet, onceki_sonuc, _kayit_oku,
    BOLUM_ADLARI, SPEKTRUM_ADLARI, spektrum_adi, fark_metni, eskime)
from cekirdek.tukenme_terminal import KOSU_ISARETI, kosu_basligi, _terminal  # noqa: E402,F401


def transport_sayisi(spec):
    """Toplam transport cozumu (entegrator, sogutma, hizli kip): tukenme_ayar."""
    from cekirdek import tukenme_ayar
    return tukenme_ayar.transport_sayisi(spec.get("tukenme") or {})


if __name__ == "__main__":
    from cekirdek.ceviri import terminal_dili
    terminal_dili()                   # OPENMC_ARAYUZ_DIL verilmisse o dil
    sys.exit(_terminal(sys.argv[1:]))
