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
import xml.etree.ElementTree as ET

_NUKLID_ONBELLEK = {}      # nuklid adi -> (en_dusuk, en_yuksek) K
_SAB_ONBELLEK = {}         # S(a,b) adi -> (en_dusuk, en_yuksek) K
_YOL_ONBELLEK = {}         # (tur, ad) -> h5 yolu


def _kutuphane_yolu():
    return os.environ.get("OPENMC_CROSS_SECTIONS")


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
    except ImportError:
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
                except ValueError:
                    pass
            # 0 K yalnizca bazi kutuphanelerde bulunur ve kullanilabilir
            # bir calisma sicakligi degildir; alt sinir olarak sayilmaz.
            gercek = [t for t in sicakliklar if t > 0]
            return (min(gercek), max(gercek)) if gercek else None
    except Exception:
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
        return None, None, "sicaklik araligi okunamadi"
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
    """Zincir dosyalarinin dizini: OPENMC_CHAIN_FILE'in dizini, yoksa ~/nucdata/chain."""
    yol = os.environ.get("OPENMC_CHAIN_FILE")
    if yol:
        return os.path.dirname(os.path.abspath(yol))
    return os.path.expanduser("~/nucdata/chain")


def zincir_kontrol(yol, tam=False):
    """
    Zincir dosyasi kullanilabilir mi?
    DONER (tamam: bool, mesaj: str, nuklid_sayisi: int|None)

    Hizli kontrol (varsayilan) dosyanin SONUNU okur: kesik bir indirme
    kapanis etiketini icermez. tam=True ise dosya ayristirilir (~1 s,
    sonuc yol+boyut+degisiklik zamanina gore onbelleklenir).
    """
    if not yol or not os.path.exists(yol):
        return False, "zincir dosyasi yok: %s" % yol, None
    boyut = os.path.getsize(yol)
    if boyut == 0:
        return False, "zincir dosyasi bos: %s" % yol, None
    try:
        with open(yol, "rb") as f:
            f.seek(max(0, boyut - 512))
            son = f.read()
    except OSError as e:
        return False, "zincir dosyasi okunamadi: %s" % e, None
    if b"</depletion_chain>" not in son:
        return False, ("zincir dosyasi YARIM: kapanis etiketi yok (%d bayt). "
                       "Indirme kesilmis olabilir; yeniden indirin." % boyut), None
    if not tam:
        return True, "zincir dosyasi tamam gorunuyor (%.1f MB)" % (boyut / 1e6), None

    anahtar = (os.path.abspath(yol), boyut, os.path.getmtime(yol))
    if anahtar in _ZINCIR_ONBELLEK:
        return _ZINCIR_ONBELLEK[anahtar]
    try:
        import openmc.deplete
        n = len(openmc.deplete.Chain.from_xml(yol).nuclides)
        sonuc = (True, "zincir ayristirildi: %d nuklid" % n, n)
    except Exception as e:
        sonuc = (False, "zincir ayristirilamadi: %s" % e, None)
    _ZINCIR_ONBELLEK[anahtar] = sonuc
    return sonuc
