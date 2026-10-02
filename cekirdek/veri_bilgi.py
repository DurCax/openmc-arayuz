# -*- coding: utf-8 -*-
"""
================================================================================
 veri_bilgi.py  --  Nukleer veri kutuphanesinin sundugu sicaklik araliklari
================================================================================

 NEDEN GEREKLI
   OpenMC tesir kesitlerini yalnizca kutuphanede bulunan sicakliklarda tutar;
   ara degerler interpolasyonla uretilir ama ARALIK DISINA cikilamaz. Ornek
   (ENDF/B-VIII.0, bu makinedeki kurulum):

     notron verisi : 250, 294, 600, 900, 1200, 2500 K
     c_H_in_H2O    : 284 ... 800 K   <-- suyun S(a,b) araligi cok daha DAR
     c_Graphite    : 296 ... 2000 K
     c_Be          : 296 ... 1200 K

   Yani 900 K'de su tanimlarsaniz notron verisi bulunur ama S(a,b) bulunamaz
   ve kosu HATA ile durur. Sicaklik taramasi yaparken bu sinir asilirsa hata
   taramanin ortasinda, dakikalar harcandiktan sonra ortaya cikar.

   Bu modul sinirlari kosu ONCESINDE okur; dogrula.py bunu kullanir.

 MALIYET
   Sicaklik listesi HDF5 dosyasinin yalnizca grup adlarindan okunur (veri
   yuklenmez). Nuklid basina ~1 ms; sonuclar surec omru boyunca onbelleklenir.
================================================================================
"""

import os
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional, Tuple

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici, uyar_bir_kez

_log = kaydedici(__name__)

_NUKLID_ONBELLEK = {}      # nuklid adi -> (en_dusuk, en_yuksek) K
_SAB_ONBELLEK = {}         # S(a,b) adi -> (en_dusuk, en_yuksek) K
_YOL_ONBELLEK = {}         # (tur, ad) -> h5 yolu


def _kutuphane_yolu():
    """cross_sections.xml yolu: tek cozumleyiciden (veri_yolu; ortam > ayar > aday)."""
    from cekirdek import veri_yolu
    return veri_yolu.cross_sections().deger


def _yol_haritasi():
    """cross_sections.xml'den {(tur, ad): mutlak_yol} haritasi kurar."""
    if _YOL_ONBELLEK:
        return _YOL_ONBELLEK
    yol = _kutuphane_yolu()
    if not yol or not os.path.exists(yol):
        return _YOL_ONBELLEK
    taban = os.path.dirname(yol)
    try:
        kok = ET.parse(yol).getroot()
    except Exception:
        return _YOL_ONBELLEK
    for lib in kok.findall("library"):
        tur = lib.get("type")
        if tur not in ("neutron", "thermal"):
            continue
        dosya = os.path.join(taban, lib.get("path", ""))
        for ad in (lib.get("materials") or "").split():
            _YOL_ONBELLEK[(tur, ad)] = dosya
    return _YOL_ONBELLEK


def _h5_sicakliklari(dosya, ad, tur):
    """HDF5 dosyasindan sicaklik listesini okur (veri yuklemeden)."""
    try:
        import h5py
    except ImportError:          # h5py yoksa sicaklik araligi bilinmez (opsiyonel bilgi)
        return None
    if not dosya or not os.path.exists(dosya):
        return None
    try:
        with h5py.File(dosya, "r") as f:
            if ad not in f:
                return None
            g = f[ad]
            if tur == "neutron":
                if "energy" not in g:
                    return None
                anahtarlar = g["energy"].keys()
            else:
                anahtarlar = g["kTs"].keys() if "kTs" in g else \
                    [k for k in g.keys() if k.endswith("K")]
            sicakliklar = []
            for k in anahtarlar:
                try:
                    sicakliklar.append(int(str(k).replace("K", "")))
                except ValueError:   # sicaklik olmayan anahtar ("0K" disi grup) atlanir
                    pass
            # 0 K yalnizca bazi kutuphanelerde bulunur ve kullanilabilir
            # bir calisma sicakligi degildir; alt sinir olarak sayilmaz.
            gercek = [t for t in sicakliklar if t > 0]
            return (min(gercek), max(gercek)) if gercek else None
    except Exception:
        uyar_bir_kez(_log, "HDF5 sicakliklari okunamadi: %s (%s)", dosya, ad)
        return None


_ENERJI_ONBELLEK = {}


def nuklid_enerji_tavani(nuklid):
    """
    Nuklidin degerlendirmesinin ust enerji siniri [eV]; okunamazsa None.

    Bu sayi kutuphaneye ve nuklide gore DEGISIR -- sabit bir 20 MeV varsaymak
    yanlis olurdu. ENDF/B-VIII.0'da olculen ornekler:
        H1  = 20 MeV,  U235 = 30 MeV,  Fe56 = 150 MeV
    Modelin gercek tavani, icindeki nuklidlerin tavanlarinin EN KUCUGUdur.
    """
    if nuklid in _ENERJI_ONBELLEK:
        return _ENERJI_ONBELLEK[nuklid]
    sonuc = None
    dosya = _yol_haritasi().get(("neutron", nuklid))
    if dosya and os.path.exists(dosya):
        try:
            import h5py
            with h5py.File(dosya, "r") as f:
                if nuklid in f and "energy" in f[nuklid]:
                    g = f[nuklid]["energy"]
                    anahtarlar = sorted(g.keys())
                    if anahtarlar:
                        sonuc = float(g[anahtarlar[0]][-1])
        except Exception:
            uyar_bir_kez(_log, "enerji tavani okunamadi: %s (%s)", nuklid, dosya)
            sonuc = None
    _ENERJI_ONBELLEK[nuklid] = sonuc
    return sonuc


def enerji_tavani(nuklidler):
    """
    Nuklid listesi icin (tavan_eV, tavani_belirleyen_nuklid); hicbiri
    okunamazsa (None, None).
    """
    en_dusuk, sahibi = None, None
    for n in nuklidler:
        t = nuklid_enerji_tavani(n)
        if t is None:
            continue
        if en_dusuk is None or t < en_dusuk:
            en_dusuk, sahibi = t, n
    return en_dusuk, sahibi


def nuklid_araligi(nuklid):
    """Nuklidin veri kutuphanesindeki (en_dusuk, en_yuksek) sicakligi [K]."""
    if nuklid in _NUKLID_ONBELLEK:
        return _NUKLID_ONBELLEK[nuklid]
    dosya = _yol_haritasi().get(("neutron", nuklid))
    sonuc = _h5_sicakliklari(dosya, nuklid, "neutron")
    _NUKLID_ONBELLEK[nuklid] = sonuc
    return sonuc


def sab_araligi(sab_adi):
    """S(a,b) kaydinin (en_dusuk, en_yuksek) sicakligi [K]."""
    if sab_adi in _SAB_ONBELLEK:
        return _SAB_ONBELLEK[sab_adi]
    dosya = _yol_haritasi().get(("thermal", sab_adi))
    sonuc = _h5_sicakliklari(dosya, sab_adi, "thermal")
    _SAB_ONBELLEK[sab_adi] = sonuc
    return sonuc


def malzeme_araligi(nuklidler, sab_listesi):
    """
    Bir malzemenin kullanilabilir sicaklik araligi: tum bilesenlerin
    araliklarinin KESISIMI. Herhangi biri okunamazsa None doner.

    DONER (alt, ust, kisitlayan_ad) ya da (None, None, aciklama)
    """
    alt, ust, kisitlayan = None, None, None
    for n in nuklidler:
        a = nuklid_araligi(n)
        if a is None:
            continue
        if alt is None or a[0] > alt:
            alt, kisitlayan = a[0], n
        if ust is None or a[1] < ust:
            ust = a[1]
    for s in sab_listesi or []:
        a = sab_araligi(s)
        if a is None:
            continue
        if alt is None or a[0] > alt:
            alt, kisitlayan = a[0], s
        if ust is None or a[1] < ust:
            ust, kisitlayan = a[1], s
    if alt is None or ust is None:
        return None, None, _("sıcaklık aralığı okunamadı")
    return alt, ust, kisitlayan


def ozet():
    """Kutuphanenin genel sicaklik ozeti (tanilama icin)."""
    satirlar = []
    for tur, ad in (("neutron", "U235"), ("neutron", "H1"),
                    ("thermal", "c_H_in_H2O"), ("thermal", "c_Graphite"),
                    ("thermal", "c_Be")):
        a = nuklid_araligi(ad) if tur == "neutron" else sab_araligi(ad)
        satirlar.append("%-14s %s" % (ad, ("%d - %d K" % a) if a else "okunamadi"))
    return satirlar


# ============================================================================
# Tukenme zinciri
# ============================================================================
#   23.09.2026'daki ilk indirme %13'te SESSIZCE kesilmisti: 3 645 440 / 27 526 672
#   bayt, bir ozniteligin ortasinda bitiyor, kapanis etiketi yok. Dosya adi ve
#   yeri dogruydu; bakan biri bir sorun gormezdi. Bu kontrol onu anında yakalar.

_ZINCIR_ONBELLEK = {}


def zincir_dizini():
    """Zincir dosyalarinin dizini (veri_yolu.zincir_dizini: OPENMC_CHAIN_FILE >
    Veri sayfasi secimi > kutuphanenin yanindaki chain/ > ~/nucdata/chain)."""
    from cekirdek import veri_yolu
    return veri_yolu.zincir_dizini()


def zincir_kontrol(yol, tam=False):
    """
    Zincir dosyasi kullanilabilir mi?
    DONER (tamam: bool, mesaj: str, nuklid_sayisi: int|None)

    Hizli kontrol (varsayilan) dosyanin SONUNU okur: kesik bir indirme
    kapanis etiketini icermez. tam=True ise dosya ayristirilir (~1 s,
    sonuc yol+boyut+degisiklik zamanina gore onbelleklenir).
    """
    if not yol or not os.path.exists(yol):
        return False, _("zincir dosyası yok: %s") % yol, None
    boyut = os.path.getsize(yol)
    if boyut == 0:
        return False, _("zincir dosyası boş: %s") % yol, None
    try:
        with open(yol, "rb") as f:
            f.seek(max(0, boyut - 512))
            son = f.read()
    except OSError as e:
        _log.warning("zincir dosyasi okunamadi: %s", yol, exc_info=True)
        return False, _("zincir dosyası okunamadı: %s") % e, None
    if b"</depletion_chain>" not in son:
        return False, (_("zincir dosyası yarım: kapanış etiketi yok (%d bayt). "
                       "İndirme kesilmiş olabilir; yeniden indirin.") % boyut), None
    if not tam:
        return True, _("zincir dosyası tamam görünüyor (%.1f MB)") % (boyut / 1e6), None

    anahtar = (os.path.abspath(yol), boyut, os.path.getmtime(yol))
    if anahtar in _ZINCIR_ONBELLEK:
        return _ZINCIR_ONBELLEK[anahtar]
    try:
        import openmc.deplete
        n = len(openmc.deplete.Chain.from_xml(yol).nuclides)
        sonuc = (True, _("zincir ayrıştırıldı: %d nüklid") % n, n)
    except Exception as e:
        sonuc = (False, _("zincir ayrıştırılamadı: %s") % e, None)
    _ZINCIR_ONBELLEK[anahtar] = sonuc
    return sonuc


def onbellek_temizle():
    """Kutuphane secimi degisince (Veri sayfasi) yol/sicaklik/enerji onbellekleri."""
    for onbellek in (_YOL_ONBELLEK, _NUKLID_ONBELLEK, _SAB_ONBELLEK, _ENERJI_ONBELLEK):
        onbellek.clear()


# ============================================================================
# Klasor denetimi (Veri sayfasi: "Klasor sec")
# ============================================================================

_ORNEK_NUKLIDLER = ("U235", "H1")          # sicaklik araligi gosterilen ornekler
_ORNEK_SAB = ("c_H_in_H2O", "c_Graphite")
_EN_COK_EKSIK = 20                         # raporlanan eksik dosya sayisi siniri
_XS_DOSYASI = "cross_sections.xml"


@dataclass(frozen=True)
class KutuphaneDenetimi:
    """klasor_denetle sonucu (degismez)."""
    xml: Optional[str]          # bulunan cross_sections.xml ya da None
    tamam: bool
    notron: int = 0
    termal: int = 0
    foton: int = 0
    sab: Tuple[str, ...] = ()   # S(a,b) tablo adlari (sirali)
    sicakliklar: tuple = ()     # ((ad, (alt, ust)), ...) ornek nuklid / S(a,b)
    eksik: Tuple[str, ...] = ()  # dosyasi olmayan kayitlarin goreli yollari (ilk N)
    hatalar: Tuple[str, ...] = ()


def _xml_bul(yol):
    """(xml | None, adaylar). Dosya verilmisse o; dizinse <dizin>/cross_sections.xml
    ya da alt dizinlerdekiler arasindan veri_yolu.aday_sec (VIII.0 once; tek
    aday o; birden cok ise None -- kullanici secer)."""
    from cekirdek import veri_yolu
    if os.path.isfile(yol):
        return os.path.abspath(yol), ()
    if not os.path.isdir(yol):
        return None, ()
    secilen, adaylar = veri_yolu.aday_sec(veri_yolu.kok_adaylari(os.path.abspath(yol)))
    return secilen, adaylar


def _kayitlar(xml):
    """[(tur, [adlar], goreli_yol)]; XML okunamazsa ValueError."""
    try:
        kok = ET.parse(xml).getroot()
    except (ET.ParseError, OSError) as e:
        raise ValueError(str(e)) from e
    return [(lib.get("type"), (lib.get("materials") or "").split(), lib.get("path", ""))
            for lib in kok.findall("library")]


def _sicaklik_ornekleri(taban, kayitlar):
    harita = {(tur, ad): os.path.join(taban, yol)
              for tur, adlar, yol in kayitlar for ad in adlar}
    sonuc = []
    for tur, adlar in (("neutron", _ORNEK_NUKLIDLER), ("thermal", _ORNEK_SAB)):
        for ad in adlar:
            aralik = _h5_sicakliklari(harita.get((tur, ad)), ad, tur)
            if aralik:
                sonuc.append((ad, aralik))
    return tuple(sonuc)


def klasor_denetle(yol):
    """Secilen klasor (ya da cross_sections.xml) kullanilabilir bir kutuphane
    mi: XML okunur mu, notron kaydi var mi, kayitlarin dosyalari var mi;
    nuklid/termal/foton sayilari, S(a,b) adlari, ornek sicaklik araliklari.
    Hata firlatmaz; sorunlar `hatalar`dadir."""
    xml, adaylar = _xml_bul(yol) if yol else (None, ())
    if xml is None and len(adaylar) > 1:
        adlar = ", ".join(os.path.basename(os.path.dirname(a)) for a in adaylar)
        return KutuphaneDenetimi(None, False, hatalar=(
            _("birden çok kütüphane bulundu (%s); birinin klasörünü seçin") % adlar,))
    if xml is None:
        return KutuphaneDenetimi(None, False, hatalar=(
            _("%s içinde cross_sections.xml bulunamadı") % (yol or "?"),))
    try:
        kayitlar = _kayitlar(xml)
    except ValueError as e:
        _log.warning("cross_sections.xml okunamadi: %s (%s)", xml, e)
        return KutuphaneDenetimi(xml, False, hatalar=(
            _("cross_sections.xml okunamadı: %s") % e,))
    taban = os.path.dirname(xml)
    sayi = {t: sum(len(a) for tur, a, _y in kayitlar if tur == t)
            for t in ("neutron", "thermal", "photon")}
    eksik = tuple(y for _t, _a, y in kayitlar if not os.path.isfile(os.path.join(taban, y)))
    hatalar = []
    if not sayi["neutron"]:
        hatalar.append(_("kütüphanede nötron kaydı yok"))
    if eksik:
        hatalar.append(_("%d kaydın dosyası yok (ilki: %s) — indirme ya da açma yarım "
                         "kalmış olabilir") % (len(eksik), eksik[0]))
    return KutuphaneDenetimi(
        xml, not hatalar, sayi["neutron"], sayi["thermal"], sayi["photon"],
        tuple(sorted(a for tur, adlar, _y in kayitlar if tur == "thermal" for a in adlar)),
        _sicaklik_ornekleri(taban, kayitlar), eksik[:_EN_COK_EKSIK], tuple(hatalar))


# ============================================================================
# Gereksinimler (Veri sayfasi: tek ekranda durum)
# ============================================================================

_SURUM_ZAMAN_ASIMI = 10.0       # s; `openmc --version` olculen ~0.02 s (bu makine)
_SURUM_DESENI = re.compile(r"OpenMC version\s+(\S+)")
_KURULUM_ONERISI = "conda install -c conda-forge openmc"


@dataclass(frozen=True)
class Gereksinim:
    """Bir gereksinim satiri. durum: "tamam" | "uyari" | "eksik"."""
    anahtar: str
    ad: str
    durum: str
    deger: str
    oneri: str = ""


_SURUM_ONBELLEK = {}            # (exe, mtime) -> (surum | None, hata)


def _openmc_ikili_surumu(exe, calistir):
    """(surum ya da None, hata metni ya da ""); ikili degismedikce onbellekten."""
    try:
        anahtar = (exe, os.path.getmtime(exe))
    except OSError:
        anahtar = (exe, None)
    if anahtar not in _SURUM_ONBELLEK:
        _SURUM_ONBELLEK[anahtar] = _surum_calistir(exe, calistir)
    return _SURUM_ONBELLEK[anahtar]


def _surum_calistir(exe, calistir):
    try:
        r = calistir([exe, "--version"], capture_output=True, text=True,
                     timeout=_SURUM_ZAMAN_ASIMI, check=False)
    except (OSError, subprocess.SubprocessError) as e:
        _log.warning("openmc --version calismadi: %s (%s)", exe, e)
        return None, str(e)
    m = _SURUM_DESENI.search(r.stdout or "")
    if r.returncode != 0 or not m:
        return None, _("çıkış kodu %d") % r.returncode
    return m.group(1), ""


def _g_openmc(ortam, calistir, python):
    from cekirdek import yollar
    exe = yollar.openmc_ikilisi(ortam, python=python)
    ad = _("OpenMC ikilisi")
    if exe is None:
        return Gereksinim("openmc", ad, "eksik", _("bulunamadı"), _KURULUM_ONERISI), None
    surum, hata = _openmc_ikili_surumu(exe, calistir)
    if surum is None:
        return Gereksinim("openmc", ad, "uyari", _("%s (sürüm okunamadı: %s)") % (exe, hata),
                          _("İkilinin çalıştığını terminalde 'openmc --version' ile "
                            "deneyin.")), None
    return Gereksinim("openmc", ad, "tamam", "%s — %s" % (surum, exe)), surum


def _g_python_api(ikili_surum):
    ad = _("OpenMC Python API")
    try:
        import openmc
    except ImportError as e:
        _log.warning("openmc Python paketi yuklenemedi: %s", e)
        return Gereksinim("python_api", ad, "eksik", _("yüklenemedi"), _KURULUM_ONERISI)
    surum = getattr(openmc, "__version__", "?")
    if ikili_surum and ikili_surum != surum:
        return Gereksinim("python_api", ad, "uyari", surum,
                          _("İkili (%s) ile Python paketi (%s) farklı sürüm; aynı ortamdan "
                            "kurun.") % (ikili_surum, surum))
    return Gereksinim("python_api", ad, "tamam", surum)


def _g_hdf5():
    ad = _("HDF5 (h5py)")
    try:
        import h5py
    except ImportError:
        _log.info("h5py yok: sicaklik araliklari okunamaz")
        return Gereksinim("hdf5", ad, "uyari", _("h5py yok"),
                          _("Sıcaklık aralıkları gösterilemez: conda install h5py"))
    return Gereksinim("hdf5", ad, "tamam", "HDF5 %s · h5py %s" % (h5py.version.hdf5_version,
                                                                 h5py.__version__))


def _kaynak_adi(kaynak):
    return {"ortam": _("ortam değişkeni"), "ayar": _("Veri sayfası seçimi"),
            "aday": _("bulunan klasör")}.get(kaynak, kaynak)


def _g_kutuphane(ortam):
    from cekirdek import veri_yolu
    ad = _("Tesir kesiti kütüphanesi")
    xs = veri_yolu.cross_sections(ortam)
    if xs.gecerli:
        return Gereksinim("kutuphane", ad, "tamam", "%s (%s)" % (xs.deger, _kaynak_adi(xs.kaynak)))
    if xs.kaynak == "coklu":
        return Gereksinim("kutuphane", ad, "eksik", _("birden çok kütüphane bulundu: %s") % ", ".join(
            os.path.basename(os.path.dirname(a)) for a in xs.adaylar),
            _("Hangisinin kullanılacağını Klasör seç ile belirleyin."))
    deger = (_("%s yok (%s)") % (xs.deger, _kaynak_adi(xs.kaynak))) if xs.deger \
        else _("seçilmedi")
    return Gereksinim("kutuphane", ad, "eksik", deger,
                      _("Bir klasör seçin ya da kütüphane indirin."))


def _g_zincir(ortam):
    from cekirdek import veri_yolu
    ad = _("Tükenme zinciri")
    z = veri_yolu.zincir(ortam)
    oneri = _("Yalnız tükenme hesabı için gerekir; zincir indirin.")
    if not z.gecerli:
        return Gereksinim("zincir", ad, "uyari",
                          (_("%s yok") % z.deger) if z.deger else _("seçilmedi"), oneri)
    tamam, mesaj, _sayi = zincir_kontrol(z.deger)
    deger = "%s — %s" % (z.deger, mesaj)
    if not tamam:
        return Gereksinim("zincir", ad, "uyari", deger, oneri)
    uyum = zincir_uyumu(z.deger, veri_yolu.cross_sections(ortam).deger)
    return Gereksinim("zincir", ad, "uyari" if uyum else "tamam", deger, uyum)


# Zincir dosya adi oneki -> uyumlu kutuphane kimlikleri (veri_katalogu.json).
_ZINCIR_KUTUPHANESI = {"chain_endfb80_": ("endfb-viii.0", "lanl-endfb-viii.0")}
_DIZIN_SONEKI = "-hdf5"


def kutuphane_kimligi(xs_yolu):
    """Kutuphanenin katalog kimligi: makbuz (KAYNAK.json) > Veri sayfasi secimi >
    dizin adi ("-hdf5" soneki atilir); bilinmiyorsa None."""
    if not xs_yolu:
        return None
    import json
    from cekirdek import veri_yolu
    dizin = os.path.dirname(os.path.abspath(xs_yolu))
    try:
        with open(os.path.join(dizin, "KAYNAK.json"), encoding="utf-8") as f:
            kimlik = json.load(f).get("kimlik")
        if kimlik:
            return kimlik
    except (OSError, ValueError, AttributeError):
        _log.debug("makbuz yok/okunamadi: %s", dizin)
    ayar = veri_yolu.ayar_oku()
    if ayar.get("kutuphane") and veri_yolu._ayni_yol(ayar.get("cross_sections"), xs_yolu):
        return ayar["kutuphane"]
    ad = os.path.basename(dizin)
    return ad[:-len(_DIZIN_SONEKI)] if ad.endswith(_DIZIN_SONEKI) else ad


def _katalog_kimlikleri():
    """Katalogdaki kutuphane kimlikleri (bilinmeyen kimlikle uyari verilmez)."""
    from cekirdek import veri_indir
    try:
        return {o.kimlik for o in veri_indir.katalog_yukle().kutuphaneler}
    except (OSError, ValueError, KeyError) as e:
        _log.warning("veri katalogu okunamadi: %s", e)
        return set()


def zincir_uyumu(zincir_yolu, xs_yolu):
    """Zincir secilen kutuphaneyle ayni degerlendirmeden degilse uyari metni, yoksa ""."""
    ad = os.path.basename(zincir_yolu or "")
    kimlik = kutuphane_kimligi(xs_yolu)
    for onek, uyumlu in _ZINCIR_KUTUPHANESI.items():
        if ad.startswith(onek) and kimlik in _katalog_kimlikleri() and kimlik not in uyumlu:
            return _("Bu zincir ENDF/B-VIII.0 verisinden üretildi; seçili kütüphane %s. "
                     "Tükenme sonuçları iki farklı değerlendirmeyi karıştırır.") % kimlik
    return ""


def gereksinimler(ortam=None, calistir=None, python=None, tazele=False):
    """Veri sayfasinin durum tablosu: openmc ikilisi + surumu, Python API,
    HDF5, kutuphane, zincir. calistir: subprocess.run yerine (test);
    python: openmc aranirken yanina bakilan yorumlayici; tazele: surum
    onbellegini bosalt (Yenile dugmesi). Hata firlatmaz."""
    if tazele:
        _SURUM_ONBELLEK.clear()
    calistir = calistir or subprocess.run
    openmc_satiri, ikili_surum = _g_openmc(ortam, calistir, python)
    return (openmc_satiri, _g_python_api(ikili_surum), _g_hdf5(), _g_kutuphane(ortam),
            _g_zincir(ortam))
