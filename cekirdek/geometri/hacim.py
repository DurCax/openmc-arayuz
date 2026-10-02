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

import math
import os
import types
from dataclasses import dataclass, field

from cekirdek.geometri.gezinti import gez
from cekirdek.geometri.sema import BOSLUK
from cekirdek.ceviri import N_, _
from cekirdek.uygunluk_bellek import Bellek, icerik_anahtari

# Model icerigine gore katki tablosu (v3 H1; bkz. cekirdek/uygunluk_bellek.py)
_KATKILAR = Bellek("hacim_katkilar")

KESIN_DEGIL = "stokastik hesap gerekli"
STOKASTIK = "stokastik"
ANALITIK = "analitik"
YOK = "yok"
AYRINTI_SINIRI = 6          # ayrintida gosterilen parca/sorun sayisi

_NEDEN = {
    "konum": N_("kesik kafes konumu"),
    "cubuk": N_("kesik çubuk (pin hücreye sığmıyor)"),
    "bilesen": N_("bileşen bölgesine sığmıyor"),
    "dis": N_("kafes dışı düzensiz bölge"),
    None: N_("alanı analitik hesaplanamayan bölge"),
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
    """Ayrinti metni icin yolun son uc parcasi, okunur bicimde (yol_metni)."""
    from cekirdek.geometri.yol_metni import okunur
    parcalar = yol.split("/")
    return okunur("/".join(parcalar[-3:]) if len(parcalar) > 3 else yol)


def _ozet(satirlar):
    goster = satirlar[:AYRINTI_SINIRI]
    ek = len(satirlar) - len(goster)
    return "; ".join(goster) + ((" (+%d)" % ek) if ek > 0 else "")


def katkilar(m, ad):
    """[(yol, hacim | None, carpan, neden)] -- 'ad' malzemesinin her ziyareti.

    Butun malzemelerin katkilari TEK gezintide cikarilir ve modelin icerigine
    gore bellekte tutulur (v3 H1: tukenme sekmesi her yanabilir malzeme icin
    ayri gezinti yapiyordu; SFR'de 12 x 0.4 s). Donen liste cagiranindir."""
    if ad == BOSLUK:
        return []
    return list(_katki_tablosu(m).get(ad, ()))


def _model_anahtari(m):
    """GeometriModeli'nin icerige dayali kimligi: BUTUN alanlar (agac dahil;
    gezinti bugun agac'i dogrudan okumasa da ileride okursa bayat sonuc olmasin)."""
    return icerik_anahtari([m.kok, m.parcalar, m.gruplar, m.tanimlar, m.sablon, m.kaynaklar,
                            m.agac])


def _katki_tablosu(m):
    """{ad: ((yol, hacim | None, carpan, neden), ...)} -- degismez, bellekli."""
    return _KATKILAR.al(_model_anahtari(m), lambda: _katki_tablosu_hesapla(m))


def _katki_tablosu_hesapla(m):
    tablo = {}
    for z in gez(m):
        d = z.dugum
        ad = d.get("ad")
        if d.get("tur") != "malzeme" or ad == BOSLUK:
            continue
        if z.bolge is not None and z.bolge.hacim is not None:
            v = z.bolge.hacim * z.carpan
        elif z.bolge is None or z.bolge.alan is None:
            v = None
        else:
            v = z.bolge.alan * _uzunluk(z.z_araligi) * z.carpan
        tablo.setdefault(ad, []).append((z.yol, v, z.carpan, z.neden))
    return types.MappingProxyType({a: tuple(k) for a, k in tablo.items()})


def analitik(m, ad):
    """GeometriModeli + malzeme adi -> HacimKaydi (analitik ya da kesin degil)."""
    V, ornek, parcalar, sorunlar = 0.0, 0, [], []
    for yol, v, n, neden in katkilar(m, ad):
        if v is None:
            sorunlar.append("%s (%s)" % (_kisa_yol(yol), _(_NEDEN.get(neden, _NEDEN[None]))))
            continue
        if v <= 0.0:
            parcalar.append("%s: 0 cm³" % _kisa_yol(yol))
            continue
        V += v
        ornek += n
        parcalar.append("%s: %d × %.4g cm³" % (_kisa_yol(yol), n, v / n))
    if sorunlar:
        return HacimKaydi(None, KESIN_DEGIL, _("hacmi kesin değil: ") + _ozet(sorunlar),
                          ornek, tuple(sorunlar))
    if V > 0:
        return HacimKaydi(V, ANALITIK, _ozet(parcalar), ornek)
    if parcalar:
        return HacimKaydi(None, YOK, _("hacmi sıfır: ") + _ozet(parcalar), 0)
    return HacimKaydi(None, YOK, _("malzeme geometride bulunamadı"), 0)


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
    # surec geneli os.chdir YOK (arayuz is parcaciklari ayni cwd'yi paylasir):
    # OpenMC 0.16 export_to_model_xml(yol) + calculate_volumes(cwd=dizin)
    model.export_to_model_xml(os.path.join(dizin, "model.xml"))
    openmc.calculate_volumes(output=False, cwd=dizin)
    sonuc = openmc.VolumeCalculation.from_hdf5(os.path.join(dizin, "volume_1.h5"))
    ters = {id(v): k for k, v in nesneler.items()}
    return {ters[id(mat)]: (float(sonuc.volumes[mat.id].nominal_value),
                            float(sonuc.volumes[mat.id].std_dev)) for mat in alanlar}


# Stokastik YEDEK hacmin (tukenmede kullanilan) bagil 1-sigma ust siniri.
# Gerekce (proje olcutu, standarttan gelmez): yanma hizi hacimle ayni oranda
# yanlis olur; %0.5, ornek modellerde 2e6 orneklemle olculen bagil sapmanin
# (kesik yakit bloklu duzenek: 18 / 8074 cm3 = %0.22) iki kati payla ulasilabilir
# bir siniri ve tukenme adimlarindaki tipik k sapmasindan kucuk bir hata payini
# verir. Asilirsa orneklem sigma ~ 1/sqrt(N) ile gereken N'e (en cok
# AZAMI_ORNEKLEM) cikarilir; yine asilirsa ValueError.
BAGIL_SIGMA_SINIRI = 0.005
AZAMI_ORNEKLEM = 64_000_000
_ORNEKLEM_PAYI = 1.2            # gereken N tahminine guvenlik payi


def _bagil(v, s):
    return (s or 0.0) / v if v else float("inf")


def _gereken_orneklem(orneklem, bagil):
    return min(AZAMI_ORNEKLEM, int(math.ceil(orneklem * _ORNEKLEM_PAYI
                                             * (bagil / BAGIL_SIGMA_SINIRI) ** 2)))


def denetimli_stokastik(spec, adlar, orneklem=2_000_000, dizin=None):
    """
    Bagil sigmasi denetlenen stokastik yedek hacim. DONER ({ad: (hacim, sapma)},
    {ad: neden}) -- ikinci sozluk olculemeyen malzemelerin nedeni (hacim 0 ya
    da malzeme kurulan modelde yok); sessiz KESIN_DEGIL birakilmaz.
    Sinir (BAGIL_SIGMA_SINIRI) orneklem artirildiktan sonra da asilirsa ValueError.
    """
    olculen = stokastik(spec, adlar, orneklem, dizin)
    genis = [a for a, (v, s) in olculen.items() if v and _bagil(v, s) > BAGIL_SIGMA_SINIRI]
    if genis:
        n = max(_gereken_orneklem(orneklem, _bagil(*olculen[a])) for a in genis)
        olculen = dict(olculen, **stokastik(spec, genis, max(n, orneklem + 1), dizin))
        kalan = [a for a in genis if _bagil(*olculen[a]) > BAGIL_SIGMA_SINIRI]
        if kalan:
            raise ValueError(
                _("stokastik hacmin bağıl σ'sı %%%.2f sınırını aşıyor (örneklem %d): %s")
                % (100 * BAGIL_SIGMA_SINIRI, n, ", ".join(
                    "%s %.6g ± %.2g cm³" % (a, olculen[a][0], olculen[a][1]) for a in kalan)))
    sonuc, nedenler = {}, {}
    for a in adlar:
        v, s = olculen.get(a, (None, None))
        if v:
            sonuc[a] = (v, s)
        elif a in olculen:
            nedenler[a] = _("stokastik hacim sıfır (malzeme örnekleme kutusunda bulunamadı)")
        else:
            nedenler[a] = _("stokastik hacim ölçülemedi (malzeme kurulan modelde yok)")
    return sonuc, nedenler


def hesapla(spec, ad, stokastik_yedek=True, orneklem=2_000_000, dizin=None):
    """Analitik hacim; kesin degilse stokastik yedek (yontem 'stokastik', bildirilir).
    Yedek de olcemezse kayit KESIN_DEGIL kalir ve nedeni ayrintiya eklenir."""
    from cekirdek import geometri
    kayit = analitik(geometri.model(spec), ad)
    if kayit.yontem != KESIN_DEGIL or not stokastik_yedek:
        return kayit
    sonuc, nedenler = denetimli_stokastik(spec, [ad], orneklem, dizin)
    if ad not in sonuc:
        return HacimKaydi(None, KESIN_DEGIL, "%s; %s" % (nedenler[ad], kayit.ayrinti),
                          kayit.ornek, kayit.sorunlar)
    v, s = sonuc[ad]
    return HacimKaydi(v, STOKASTIK, _("stokastik hacim %.6g ± %.2g cm³ (%s)")
                      % (v, s, kayit.ayrinti), kayit.ornek, kayit.sorunlar, s)
