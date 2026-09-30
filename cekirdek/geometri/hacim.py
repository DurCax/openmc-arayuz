# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/hacim.py  --  Malzeme hacimleri: agac gezintisiyle analitik, yedek stokastik
================================================================================

 docs/GEOMETRI_MODELI.md §7 (tukenme satiri), §8 UYARI 1, §15 karar 2.

   analitik(m, ad)     -> HacimKaydi   agac gezintisi (geometri/gezinti.py):
                          her malzeme ziyaretinin alani x z uzunlugu x carpani
                          (kure kokunde kabuk hacmi). Bir ziyaretin alani
                          bilinmiyorsa (kesik konum, kesik cubuk, duzensiz
                          bolge, bilinmeyen sekil) kayit KESIN DEGILDIR:
                          hacim None, yontem KESIN_DEGIL, sorunlar nedenleri.
   ornek_sayisi(m, ad) -> int          hacmi sifir olmayan hucre ornekleri
   stokastik(spec, adlar, orneklem, dizin) -> {ad: (hacim, sapma)}
                          OpenMC VolumeCalculation (kurulan model)
   hesapla(spec, ad, stokastik_yedek=True) -> HacimKaydi
                          once analitik; kesin degilse (ve istenirse)
                          stokastik hacim, yontem "stokastik" -- BILDIRILIR.

 2B modelde hacim 1 cm yukseklik icindir (tukenme.hacimler ile ayni kural).
 Kontrol cubugu emicisi (§15 karar 5): her yerlesim ayri hucre/ornektir;
 emici uzunlugu daldirmaya gore (R8) z araligindan gelir, katmanli modelde
 de kesindir.
================================================================================
"""

import os
from dataclasses import dataclass, field

from cekirdek.geometri.gezinti import gez
from cekirdek.geometri.sema import BOSLUK

KESIN_DEGIL = "stokastik hesap gerekli"
STOKASTIK = "stokastik"
ANALITIK = "analitik"
YOK = "yok"
AYRINTI_SINIRI = 6          # ayrintida gosterilen parca/sorun sayisi

_NEDEN = {
    "konum": "kesik kafes konumu",
    "cubuk": "kesik çubuk (pin hücreye sığmıyor)",
    "bilesen": "bileşen bölgesine sığmıyor",
    "dis": "kafes dışı düzensiz bölge",
    None: "alanı analitik hesaplanamayan bölge",
}


@dataclass(frozen=True)
class HacimKaydi:
    """Bir malzemenin hacim kaydi (tukenme.hacimler ogesiyle ayni anahtarlar)."""
    hacim: float | None
    yontem: str
    ayrinti: str
    ornek: int = 0
    sorunlar: tuple = field(default_factory=tuple)
    sapma: float | None = None

    def sozluk(self):
        """tukenme.hacimler() bicimi: {"hacim", "yontem", "ayrinti"}."""
        return {"hacim": self.hacim, "yontem": self.yontem, "ayrinti": self.ayrinti}


def _uzunluk(z):
    return 1.0 if z is None else max(float(z[1]) - float(z[0]), 0.0)


def _kisa_yol(yol):
    parcalar = yol.split("/")
    return "/".join(parcalar[-3:]) if len(parcalar) > 3 else yol


def _ozet(satirlar):
    goster = satirlar[:AYRINTI_SINIRI]
    ek = len(satirlar) - len(goster)
    return "; ".join(goster) + ((" (+%d)" % ek) if ek > 0 else "")


def katkilar(m, ad):
    """[(yol, hacim | None, carpan, neden)] -- 'ad' malzemesinin her ziyareti."""
    cikti = []
    for z in gez(m):
        d = z.dugum
        if d.get("tur") != "malzeme" or d.get("ad") != ad or ad == BOSLUK:
            continue
        if z.bolge is not None and z.bolge.hacim is not None:
            v = z.bolge.hacim * z.carpan
        elif z.bolge is None or z.bolge.alan is None:
            v = None
        else:
            v = z.bolge.alan * _uzunluk(z.z_araligi) * z.carpan
        cikti.append((z.yol, v, z.carpan, z.neden))
    return cikti


def analitik(m, ad):
    """GeometriModeli + malzeme adi -> HacimKaydi (analitik ya da kesin degil)."""
    V, ornek, parcalar, sorunlar = 0.0, 0, [], []
    for yol, v, n, neden in katkilar(m, ad):
        if v is None:
            sorunlar.append("%s (%s)" % (_kisa_yol(yol), _NEDEN.get(neden, _NEDEN[None])))
            continue
        if v <= 0.0:
            parcalar.append("%s: 0 cm³" % _kisa_yol(yol))
            continue
        V += v
        ornek += n
        parcalar.append("%s: %d × %.4g cm³" % (_kisa_yol(yol), n, v / n))
    if sorunlar:
        return HacimKaydi(None, KESIN_DEGIL, "hacmi kesin değil: " + _ozet(sorunlar),
                          ornek, tuple(sorunlar))
    if V > 0:
        return HacimKaydi(V, ANALITIK, _ozet(parcalar), ornek)
    if parcalar:
        return HacimKaydi(None, YOK, "hacmi sıfır: " + _ozet(parcalar), 0)
    return HacimKaydi(None, YOK, "malzeme geometride bulunamadı", 0)


def ornek_sayisi(m, ad):
    """'ad' malzemesinin hacmi sifir olmayan hucre ornegi sayisi (kesikler dahil)."""
    return sum(n for _y, v, n, _ne in katkilar(m, ad) if v is None or v > 0.0)


# ----------------------------------------------------------------------------
# stokastik (OpenMC VolumeCalculation)
# ----------------------------------------------------------------------------

def _kutu(spec):
    from cekirdek import geometri
    m = geometri.model(spec)
    gx, gy = geometri.sinir_kutusu(m)
    if m.kok.get("kesit", {}).get("sekil") == "kure":
        r = gx / 2.0
        return (-r, -r, -r), (r, r, r)
    h = geometri.yukseklik(m)
    z = h / 2.0 if h else 0.5
    return (-gx / 2.0, -gy / 2.0, -z), (gx / 2.0, gy / 2.0, z)


def stokastik(spec, adlar, orneklem=2_000_000, dizin=None):
    """
    OpenMC'nin stokastik hacim hesabi (kurulan modelde). {ad: (hacim, sapma)}.
    2B modelde kutu 1 cm yuksekliktir (analitik kuralla ayni).
    """
    import tempfile
    import openmc
    from cekirdek import kurucu
    model, bilgi = kurucu.kur(spec)
    model.tallies = openmc.Tallies()
    nesneler = bilgi["malzemeler"]
    alanlar = [nesneler[a] for a in adlar if a in nesneler]
    if not alanlar:
        return {}
    alt, ust = _kutu(spec)
    vc = openmc.VolumeCalculation(alanlar, orneklem, alt, ust)
    model.settings.volume_calculations = [vc]
    dizin = dizin or tempfile.mkdtemp(prefix="geometri_hacim_")
    eski = os.getcwd()
    try:
        os.chdir(dizin)
        model.export_to_model_xml()
        openmc.calculate_volumes(output=False)
        sonuc = openmc.VolumeCalculation.from_hdf5(os.path.join(dizin, "volume_1.h5"))
    finally:
        os.chdir(eski)
    ters = {id(v): k for k, v in nesneler.items()}
    return {ters[id(mat)]: (float(sonuc.volumes[mat.id].nominal_value),
                            float(sonuc.volumes[mat.id].std_dev)) for mat in alanlar}


def hesapla(spec, ad, stokastik_yedek=True, orneklem=2_000_000, dizin=None):
    """Analitik hacim; kesin degilse stokastik yedek (yontem 'stokastik', bildirilir)."""
    from cekirdek import geometri
    kayit = analitik(geometri.model(spec), ad)
    if kayit.yontem != KESIN_DEGIL or not stokastik_yedek:
        return kayit
    v, s = stokastik(spec, [ad], orneklem, dizin).get(ad, (None, None))
    if not v:
        return kayit
    return HacimKaydi(v, STOKASTIK, "stokastik hacim %.6g ± %.2g cm³ (%s)"
                      % (v, s, kayit.ayrinti), kayit.ornek, kayit.sorunlar, s)
