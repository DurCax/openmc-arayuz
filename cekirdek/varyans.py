# -*- coding: utf-8 -*-
"""
================================================================================
 varyans.py  --  Y9: varyans azaltma (agirlik pencereleri, MAGIC) ve FOM
================================================================================
 Ayar: spec["ayarlar"]["varyans"] (sema.VARSAYILAN_AYARLAR'a EKLENMEZ -- alan yoksa
 kapali; onbellek kimligi ve eski dosyalar degismez):

   {"var": true,
    "mod": "uret" | "uret_uygula" | "uygula",
    "yontem": "magic",                       # fw_cadis: asagiya bakin
    "parcacik": "neutron" | "photon",
    "mesh_boyut": [nx, ny, nz],              # modelin sinir kutusunda duzenli ag
    "enerji_siniri": [E0, E1, ...] [eV],     # bos: tek enerji grubu (OpenMC varsayilani)
    "max_gerceklesme": 10, "guncelleme_araligi": 1,
    "dosya": "yol.h5 | yol.wwinp"}           # yalniz mod == "uygula"

 MODLAR (OpenMC 0.16, openmc/weight_windows.py ve docs/usersguide/variance_reduction)
   uret        : openmc.WeightWindowGenerator(method='magic', on_the_fly=False) --
                 kosu ANALOG transport eder, yalniz pencereleri uretir ve kosu sonunda
                 weight_windows.h5 yazar (onerilen ilk adim; ardindan 'uygula').
   uret_uygula : openmc.WeightWindowGenerator(method='magic', on_the_fly=True) --
                 pencereler KOSU SIRASINDA her `guncelleme_araligi` cevrimde, en cok
                 `max_gerceklesme` gerceklesmeye kadar guncellenir ve ayni kosuda
                 uygulanir (settings.weight_windows_on = True); kosu sonunda
                 weight_windows.h5 yazilir. Pencereler cevrimler arasinda degisir
                 ama her parcacigin agirligi pencereye gore ayarlanir ve ortalama
                 korunur: sonuc yanliliksizdir (testler/test_y9_varyans.py).
   uygula      : onceki bir kosunun weight_windows.h5 dosyasi (settings.
                 weight_windows_file) ya da bir MCNP wwinp dosyasi
                 (WeightWindowsList.from_wwinp) yuklenir; pencereler SABIT.
   OpenMC 0.16 wwinp DISA AKTARMA yapmaz (yalniz h5: WeightWindowsList.export_to_hdf5).

 MAGIC (Meshed Adjoint-like Generation by Iterative Computation; Davis ve Sawan, Fusion
 Sci. Tech. 2013): pencere alt siniri, ag hucresindeki skaler akinin en yuksek hucreye
 oranina gore olceklenir (akinin az oldugu yerde pencere dusuk: parcacik bolunur).
 FW-CADIS: OpenMC 0.16 WeightWindowGenerator(method='fw_cadis') kabul eder ama bu yontem
 random ray KOSUSUNUN adjoint cozumunu (settings.random_ray['adjoint'], cok gruplu
 kutuphane, ayri random ray modeli) ister. Arayuzde bu surumde ACILMADI (kapsam disi;
 CHANGELOG ve kilavuzda belgeli); yontem alani yalniz 'magic' kabul eder.

 FOM = 1 / (sigma_bagil^2 * T)  (Lewis ve Miller; bkz. fom()). T: kosu suresi [s].
 Ayni FOM'lu iki yontemin ayni sonucu ayni verimle verdigi anlamina gelir; FOM
 arttikca ayni belirsizlik daha kisa surede elde edilir.
================================================================================
"""

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from cekirdek.ceviri import _

_log = logging.getLogger(__name__)

YONTEMLER = ("magic",)
MODLAR = ("uret", "uret_uygula", "uygula")
PARCACIKLAR = ("neutron", "photon")
VARSAYILAN_BOYUT = (10, 10, 10)
VARSAYILAN_MAX_GERCEKLESME = 10      # OpenMC varsayilani 1; MAGIC icin birkac gerceklesme gerekir
VARSAYILAN_ARALIK = 1                # OpenMC varsayilani
EN_COK_HUCRE = 2_000_000             # ag hucresi ust siniri (bellek: hucre x enerji grubu)
H5_UZANTISI = ".h5"


@dataclass(frozen=True)
class VaryansAyari:
    """spec["ayarlar"]["varyans"] dogrulanmis hali."""
    var: bool
    mod: str = "uret"
    yontem: str = "magic"
    parcacik: str = "neutron"
    boyut: Tuple[int, int, int] = VARSAYILAN_BOYUT
    enerji_siniri: Tuple[float, ...] = ()
    max_gerceklesme: int = VARSAYILAN_MAX_GERCEKLESME
    aralik: int = VARSAYILAN_ARALIK
    dosya: Optional[str] = None


def ayar(spec: dict) -> VaryansAyari:
    """Ayari okur. Alan sozluk degilse ya da var False ise kapali; aciksa gecersiz
    deger ValueError (kosu oncesi dogrulama bunu hata olarak gosterir)."""
    ham = ((spec or {}).get("ayarlar") or {}).get("varyans")
    if not isinstance(ham, dict) or not ham.get("var"):
        return VaryansAyari(False)
    mod = ham.get("mod") or "uret"
    if mod not in MODLAR:
        raise ValueError(_("bilinmeyen varyans azaltma modu: %r (geçerli: %s)")
                         % (mod, ", ".join(MODLAR)))
    yontem = ham.get("yontem") or "magic"
    if yontem not in YONTEMLER:
        raise ValueError(_("varyans azaltma yöntemi desteklenmiyor: %r (geçerli: %s; FW-CADIS "
                           "random ray adjoint çözümü ister, bu sürümde yok)")
                         % (yontem, ", ".join(YONTEMLER)))
    parcacik = ham.get("parcacik") or "neutron"
    if parcacik not in PARCACIKLAR:
        raise ValueError(_("bilinmeyen parçacık türü: %r") % (parcacik,))
    boyut = _boyut(ham.get("mesh_boyut"))
    enerji = _enerji(ham.get("enerji_siniri"))
    max_g = _tam(ham.get("max_gerceklesme", VARSAYILAN_MAX_GERCEKLESME), "max_gerceklesme")
    aralik = _tam(ham.get("guncelleme_araligi", VARSAYILAN_ARALIK), "guncelleme_araligi")
    dosya = ham.get("dosya") or None
    if mod == "uygula" and not dosya:
        raise ValueError(_("'uygula' modu için pencere dosyası (.h5 ya da wwinp) gerekli"))
    return VaryansAyari(True, mod, yontem, parcacik, boyut, enerji, max_g, aralik, dosya)


def _tam(deger, ad: str) -> int:
    try:
        v = int(deger)
    except (TypeError, ValueError):
        raise ValueError(_("'%s' tamsayı olmalı") % ad) from None
    if v < 1:
        raise ValueError(_("'%s' en az 1 olmalı (%d)") % (ad, v))
    return v


def _boyut(ham) -> Tuple[int, int, int]:
    if ham is None:
        return VARSAYILAN_BOYUT
    if not isinstance(ham, (list, tuple)) or len(ham) != 3:
        raise ValueError(_("ağ boyutu [nx, ny, nz] olmalı"))
    boyut = tuple(_tam(v, "mesh_boyut") for v in ham)
    if boyut[0] * boyut[1] * boyut[2] > EN_COK_HUCRE:
        raise ValueError(_("ağ çok büyük: %d hücre (üst sınır %d)")
                         % (boyut[0] * boyut[1] * boyut[2], EN_COK_HUCRE))
    return boyut


def _enerji(ham) -> Tuple[float, ...]:
    if not ham:
        return ()
    try:
        e = tuple(float(v) for v in ham)
    except (TypeError, ValueError):
        raise ValueError(_("enerji sınırları sayı listesi olmalı")) from None
    if len(e) < 2 or any(b <= a for a, b in zip(e, e[1:])) or e[0] < 0:
        raise ValueError(_("enerji sınırları artan ve en az iki değerli olmalı (eV)"))
    return e


def kosu_dosyasi(dizin: str) -> str:
    """Bir koşu dizininde OpenMC'nin yazdigi pencere dosyasi (uret_uygula sonrasi)."""
    return os.path.join(dizin, "weight_windows.h5")


def mesh_sinirlari(spec: dict, sinir_kutu) -> Tuple[List[float], List[float]]:
    """(alt, ust) [cm]: modelin sinir kutusu x z yuksekligi (kurede kure capi).
    2B (z'de sinirsiz) modelde ValueError: agirlik penceresi sonlu bir ag ister."""
    from cekirdek import kurucu
    from cekirdek.sema import model_yuksekligi
    if not (model_yuksekligi(spec) or kurucu._kure_mu(spec)):
        raise ValueError(_("ağırlık penceresi 3B model gerektirir (yükseklik tanımlı değil)"))
    return kurucu.tally_mesh_sinirlari(spec, {"otomatik": True}, sinir_kutu)


def pencere_dosyasi_h5_mi(dosya: str) -> bool:
    return str(dosya).lower().endswith(H5_UZANTISI)


def uygula(settings, spec: dict, sinir_kutu) -> None:
    """kurucu.ayarlari_kur kancasi: ayar aciksa settings'e jenerator ya da pencere dosyasi."""
    a = ayar(spec)
    if not a.var:
        return
    import openmc
    if a.mod == "uygula":
        if pencere_dosyasi_h5_mi(a.dosya):
            settings.weight_windows_file = a.dosya
        else:
            settings.weight_windows = openmc.WeightWindowsList.from_wwinp(a.dosya)
        settings.weight_windows_on = True
        return
    alt, ust = mesh_sinirlari(spec, sinir_kutu)
    mesh = openmc.RegularMesh()
    mesh.dimension = list(a.boyut)
    mesh.lower_left = alt
    mesh.upper_right = ust
    kw = {"energy_bounds": list(a.enerji_siniri)} if a.enerji_siniri else {}
    uygulaniyor = a.mod == "uret_uygula"
    settings.weight_window_generators = openmc.WeightWindowGenerator(
        mesh, particle_type=a.parcacik, method=a.yontem, max_realizations=a.max_gerceklesme,
        update_interval=a.aralik, on_the_fly=uygulaniyor, **kw)
    settings.weight_windows_on = uygulaniyor


def betik_satirlari(spec: dict, sinir_kutu) -> List[str]:
    """uygula() ile ayni ayarin betik satirlari (kapaliysa bos)."""
    a = ayar(spec)
    if not a.var:
        return []
    if a.mod == "uygula":
        if pencere_dosyasi_h5_mi(a.dosya):
            satir = "ayar.weight_windows_file = %r" % a.dosya
        else:
            satir = "ayar.weight_windows = openmc.WeightWindowsList.from_wwinp(%r)" % a.dosya
        return ["# varyans azaltma: hazır ağırlık pencereleri", satir,
                "ayar.weight_windows_on = True"]
    alt, ust = mesh_sinirlari(spec, sinir_kutu)
    enerji = ", energy_bounds=%r" % list(a.enerji_siniri) if a.enerji_siniri else ""
    uygulaniyor = a.mod == "uret_uygula"
    baslik = ("koşu sırasında üretilir ve uygulanır" if uygulaniyor
              else "yalnız üretilir (analog taşıma); weight_windows.h5 yazılır")
    return ["# varyans azaltma: MAGIC ağırlık penceresi üreteci (%s)" % baslik,
            "_ww_ag = openmc.RegularMesh()",
            "_ww_ag.dimension = %r" % list(a.boyut),
            "_ww_ag.lower_left = %r" % (tuple(alt),),
            "_ww_ag.upper_right = %r" % (tuple(ust),),
            "ayar.weight_window_generators = openmc.WeightWindowGenerator(_ww_ag, "
            "particle_type=%r, method=%r, max_realizations=%d, update_interval=%d, "
            "on_the_fly=%s%s)" % (a.parcacik, a.yontem, a.max_gerceklesme, a.aralik,
                                     uygulaniyor, enerji),
            "ayar.weight_windows_on = %s" % uygulaniyor]


# ----------------------------------------------------------------------------
# FOM
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class FomSatiri:
    """Bir tally (toplami) icin verimlilik olcusu."""
    ad: str
    deger: float
    sapma: float
    bagil_hata: float
    sure_s: float
    fom: float


def fom(deger: float, sapma: float, sure_s: float) -> Optional[float]:
    """FOM = 1 / (sigma_bagil^2 T); sigma_bagil = sapma / |deger|. Deger sifir, sapma
    sifir ya da sure <= 0 ise None (tanimsiz: sifir sayimda FOM anlamsiz)."""
    if not deger or sapma <= 0.0 or sure_s <= 0.0:
        return None
    bagil = sapma / abs(deger)
    return 1.0 / (bagil * bagil * sure_s)


def fom_satiri(ad: str, deger: float, sapma: float, sure_s: float) -> Optional[FomSatiri]:
    f = fom(deger, sapma, sure_s)
    if f is None:
        return None
    return FomSatiri(ad, deger, sapma, sapma / abs(deger), sure_s, f)


def kosu_suresi(runtime: dict) -> Optional[float]:
    """statepoint 'runtime' sozlugunden simulasyon suresi [s] ('simulation' = baslatma
    ve tally yazma haric tum cevrimler; weight window uretimi dahildir)."""
    for anahtar in ("simulation", "total simulation"):
        if anahtar in runtime:
            return float(runtime[anahtar])
    return None


def fom_tablosu(statepoint_yolu: str) -> List[FomSatiri]:
    """Statepoint'teki her tally icin (butun binlerin toplami; binler bagimsiz kabul)
    FOM satiri. Genel tally'ler (guc, spektrum, yuzey vb.) dahil degildir."""
    import math
    import openmc
    satirlar: List[FomSatiri] = []
    with openmc.StatePoint(statepoint_yolu) as sp:
        sure = kosu_suresi(sp.runtime)
        if sure is None:
            _log.warning("statepoint süresi okunamadı; FOM hesaplanmadı")
            return []
        for t in sp.tallies.values():
            ad = t.name or "tally_%d" % t.id
            if ad.startswith(_ONEK_DISLA):
                continue
            ort, sap = float(t.mean.sum()), math.sqrt(float((t.std_dev ** 2).sum()))
            s = fom_satiri(ad, ort, sap, sure)
            if s is not None:
                satirlar.append(s)
    return satirlar


# Guc (guc_*), spektrum (y3_), yuzey (y7_), IFP ve ag genel isi tally'leri kullanici
# olcutu degildir (kendi okuyuculari var)
_ONEK_DISLA = ("guc_", "y3_", "y7_", "IFP", "mesh_genel_isi")
