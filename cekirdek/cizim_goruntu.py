# -*- coding: utf-8 -*-
"""
================================================================================
 cizim_goruntu.py  --  Goruntuleyici (v3 Y2) icin cizim iscisi ekleri
================================================================================

 cekirdek/cizim_sureci.py iscisinin protokolunu GERI UYUMLU genisletir (yeni
 alanlar isteğe bagli; eski istemci ve onizleme degismeden calisir):

   kesit ogesi   {"eksen", "piksel"} + istege bagli
                 "merkez": [x, y, z]  (varsayilan KESIT_MERKEZI),
                 "genislik": [yatay, dikey] cm (varsayilan sinir kutusu),
                 "piksel_dikey": dikey piksel (varsayilan = piksel; kare piksel
                 icin arayuz genislik oranindan hesaplar).
                 Yanit "kesit" ogesine "merkez" eklenir.
   "ciz"/"kontrol" + "adlar": true  -> "model" yanitina "malzeme_adlari" ve
                 "hucre_adlari" ({kimlik: ad}) eklenir (fare altindaki bilgi).
   "isin"        3B golgeli goruntu: openmc.lib.SolidRayTracePlot (0.16.0'da var:
                 openmc/lib/plot.py, "versionadded 0.16.0"; '-p' kipinde calisir,
                 olculdu: PWR 3B demet 400 x 300 px 0.01 s).
                 {"tur": "isin", "no", "spec", "kamera": [3], "bakis": [3],
                  "yukari": [3], "gorus": derece, "piksel": [genislik, yukseklik],
                  "renk": "material" | "cell", "gizli": [kimlik], "isik": [3]?,
                  "dagilim": 0-1?}
                 -> {"tur": "goruntu", "no", "piksel", "sure"} + dizi "rgb"
                    (yukseklik, genislik, 3) uint8; satir 0 = goruntunun ustu.
   "kaynak"      kaynak noktalari:
                 {"tur": "kaynak", "no", "spec", "sayi", "tohum", "statepoint"?}
                 statepoint verilirse onun kaynak bankasi (h5py ile
                 "source_bank" veri kumesi; openmc/statepoint.py ile ayni ad),
                 yoksa settings.source ORNEKLENIR (asagiya bakin).
                 -> {"tur": "kaynak_noktalari", "no", "kaynak", "toplam",
                     "deneme", "sure"} + dizi "r" (n, 3) float64 [cm]

 NEDEN openmc.lib.sample_external_source DEGIL
   '-p' (cizim) kipinde nukleer veri yuklenmez; fisil kisitli kaynakta OpenMC
   "Exceeded maximum number of source rejections" deyip SURECI SONLANDIRIR
   (olculdu, 0.16.0, pwr_3b). Ornekleme burada numpy ile yapilir: kurucu yalniz
   Box ve Point uzay dagilimi kurar (cekirdek/kurucu.py); "fissionable" kisiti
   noktadaki malzemeye openmc.lib.find_material ile bakilarak uygulanir.
   Fisil malzeme: en az bir nuklidinin Z >= 90 (aktinit) olmasi -- OpenMC'nin
   tanimi "fisyon tesir kesiti olan nuklid" ise de veri yuklenmeden bilinemez;
   modeldeki fisyon yapan nuklidlerin hepsi aktinittir.
   Kabul orani KABUL_ORANI_EN_AZ'in altina duserse hata (OpenMC ile ayni esik:
   Settings.source_rejection_fraction varsayilani 0.05, openmc/settings.py).
================================================================================
"""

import math
import os
import time

import numpy as np

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

ISTEK_ISIN, ISTEK_KAYNAK = "isin", "kaynak"
YANIT_GORUNTU, YANIT_KAYNAK = "goruntu", "kaynak_noktalari"
RENK_MALZEME, RENK_HUCRE = "material", "cell"
KAYNAK_AYAR, KAYNAK_STATEPOINT = "ayar", "statepoint"

GORUS_EN_AZ, GORUS_EN_COK = 1.0, 170.0     # derece; 180'de perspektif tanimsiz
KAYNAK_EN_COK = 20_000                     # nokta; kesit bindirmesinde fazlasi okunmaz
KABUL_ORANI_EN_AZ = 0.05                   # OpenMC Settings.source_rejection_fraction
_EN_AZ_DENEME = 1000                       # oran bu kadar denemeden sonra yargilanir
_PARTI = 4096                              # tek seferde uretilen aday nokta
GIZLI_EN_COK = 10_000                      # gizlenen alan kimligi sayisi (sinir)
_AKTINIT_Z = 90                            # Th ve sonrasi (modul belgesi)
_SIFIR = 1.0e-12


def _hata(metin):
    from cekirdek.cizim_sureci import ProtokolHatasi
    return ProtokolHatasi(metin)


def _tamsayi_mi(d):
    return isinstance(d, int) and not isinstance(d, bool)


def _sayi_mi(d):
    return isinstance(d, (int, float)) and not isinstance(d, bool) and math.isfinite(d)


def vektor(deger, ad: str, sifir_olabilir: bool = True) -> tuple:
    """JSON 3-vektor -> (x, y, z) float; gecersizse ProtokolHatasi."""
    if not isinstance(deger, list) or len(deger) != 3 or not all(map(_sayi_mi, deger)):
        raise _hata(_("%s üç sonlu sayı olmalı: %r") % (ad, deger))
    v = tuple(float(x) for x in deger)
    if not sifir_olabilir and math.hypot(*v) < _SIFIR:
        raise _hata(_("%s sıfır vektör olamaz") % ad)
    return v


def _piksel(deger, ad):
    from cekirdek.cizim_sureci import PIKSEL_EN_AZ, PIKSEL_EN_COK
    if not _tamsayi_mi(deger) or not PIKSEL_EN_AZ <= deger <= PIKSEL_EN_COK:
        raise _hata(_("%s %d-%d arası tamsayı olmalı: %r")
                    % (ad, PIKSEL_EN_AZ, PIKSEL_EN_COK, deger))
    return deger


def kesit_ekleri(k: dict) -> dict:
    """Kesit ogesinin istege bagli alanlari (dogrulanmis; yalniz verilenler)."""
    ek = {}
    if "merkez" in k:
        ek["merkez"] = vektor(k["merkez"], "merkez")
    if "genislik" in k:
        g = k["genislik"]
        if (not isinstance(g, list) or len(g) != 2 or not all(map(_sayi_mi, g))
                or min(g) <= 0):
            raise _hata(_("genişlik iki pozitif sayı olmalı: %r") % (g,))
        ek["genislik"] = (float(g[0]), float(g[1]))
    if "piksel_dikey" in k:
        ek["piksel_dikey"] = _piksel(k["piksel_dikey"], "piksel_dikey")
    return ek


def _gizli_dogrula(gizli):
    if not isinstance(gizli, list) or len(gizli) > GIZLI_EN_COK \
            or not all(_tamsayi_mi(k) for k in gizli):
        raise _hata(_("gizli kimlik listesi tamsayılardan oluşmalı"))


def isin_dogrula(b: dict) -> None:
    """'isin' isteginin alanlarini denetler (ProtokolHatasi)."""
    kamera = vektor(b.get("kamera"), "kamera")
    bakis = vektor(b.get("bakis"), "bakis")
    vektor(b.get("yukari"), "yukari", sifir_olabilir=False)
    if math.dist(kamera, bakis) < _SIFIR:
        raise _hata(_("kamera bakış noktasıyla aynı yerde olamaz"))
    if "isik" in b:
        vektor(b["isik"], "isik")
    gorus = b.get("gorus")
    if not _sayi_mi(gorus) or not GORUS_EN_AZ <= gorus <= GORUS_EN_COK:
        raise _hata(_("görüş açısı %g-%g derece olmalı: %r") % (GORUS_EN_AZ, GORUS_EN_COK, gorus))
    piksel = b.get("piksel")
    if not isinstance(piksel, list) or len(piksel) != 2:
        raise _hata(_("piksel [genişlik, yükseklik] olmalı: %r") % (piksel,))
    for p in piksel:
        _piksel(p, "piksel")
    if b.get("renk", RENK_MALZEME) not in (RENK_MALZEME, RENK_HUCRE):
        raise _hata(_("bilinmeyen renk kipi: %r") % (b.get("renk"),))
    _gizli_dogrula(b.get("gizli", []))
    if "dagilim" in b and (not _sayi_mi(b["dagilim"]) or not 0.0 <= b["dagilim"] <= 1.0):
        raise _hata(_("dağınık yansıma oranı 0-1 arası olmalı"))


def kaynak_dogrula(b: dict) -> None:
    """'kaynak' isteginin alanlarini denetler (ProtokolHatasi)."""
    sayi = b.get("sayi")
    if not _tamsayi_mi(sayi) or not 1 <= sayi <= KAYNAK_EN_COK:
        raise _hata(_("nokta sayısı 1-%d arası tamsayı olmalı: %r") % (KAYNAK_EN_COK, sayi))
    if not _tamsayi_mi(b.get("tohum", 1)) or b.get("tohum", 1) < 0:
        raise _hata(_("tohum negatif olmayan tamsayı olmalı"))
    yol = b.get("statepoint")
    if yol is not None and (not isinstance(yol, str) or not yol):
        raise _hata(_("statepoint yolu metin olmalı"))


# ----------------------------------------------------------------------------
# model bilgisi
# ----------------------------------------------------------------------------

def _aktinit_mi(nuklid: str) -> bool:
    import openmc.data
    try:
        return openmc.data.zam(nuklid)[0] >= _AKTINIT_Z
    except ValueError:                      # element adi (or. "C") ya da tanimsiz
        _log.debug("nuklid adi cozulemedi: %s", nuklid)
        return False


def fisil_malzemeler(malzemeler) -> frozenset:
    """Fisil (aktinit iceren) malzeme kimlikleri (modul belgesi)."""
    return frozenset(m.id for m in malzemeler
                     if any(_aktinit_mi(n) for n in m.get_nuclides()))


def adlar(model) -> dict:
    """{"malzeme_adlari": {str(id): ad}, "hucre_adlari": {str(id): ad}} (bos ad atlanir)."""
    malzeme = {str(m.id): m.name for m in model.materials if m.name}
    hucre = {str(c.id): c.name for c in model.geometry.get_all_cells().values() if c.name}
    return {"malzeme_adlari": malzeme, "hucre_adlari": hucre}


# ----------------------------------------------------------------------------
# 3B golgeli goruntu
# ----------------------------------------------------------------------------

def isin_goruntusu(cizim, renkler: dict, istek: dict) -> np.ndarray:
    """SolidRayTracePlot ile (yukseklik, genislik, 3) uint8 goruntu.
    cizim: oturumun openmc.lib.SolidRayTracePlot nesnesi (yeniden kullanilir:
    her nesne kutuphanenin cizim dizisine eklenir, finalize'a dek silinmez).
    renkler: {malzeme id: (R, G, B)} (malzeme kipinde spec renkleri)."""
    w, h = istek["piksel"]
    cizim.pixels = (int(w), int(h))
    malzeme = istek.get("renk", RENK_MALZEME) == RENK_MALZEME
    cizim.color_by = cizim.COLOR_BY_MATERIAL if malzeme else cizim.COLOR_BY_CELL
    cizim.set_default_colors()
    cizim.set_all_opaque()
    if malzeme:
        for kimlik, rgb in renkler.items():
            cizim.set_color(int(kimlik), tuple(int(v) for v in rgb[:3]))
    for kimlik in istek.get("gizli") or []:
        cizim.set_visibility(int(kimlik), False)
    kamera = tuple(istek["kamera"])
    cizim.camera_position = kamera
    cizim.look_at = tuple(istek["bakis"])
    cizim.up = tuple(istek["yukari"])
    cizim.light_position = tuple(istek.get("isik") or kamera)
    cizim.fov = float(istek["gorus"])
    if "dagilim" in istek:
        cizim.diffuse_fraction = float(istek["dagilim"])
    cizim.update_view()
    return cizim.create_image()


# ----------------------------------------------------------------------------
# kaynak noktalari
# ----------------------------------------------------------------------------

def _uzay_ornekle(uzay, n, rng):
    """Uzay dagilimindan n aday nokta (n, 3)."""
    ad = type(uzay).__name__
    if ad == "Box":
        alt = np.asarray(uzay.lower_left, dtype=float)
        ust = np.asarray(uzay.upper_right, dtype=float)
        return alt + (ust - alt) * rng.random((n, 3))
    if ad == "Point":
        return np.tile(np.asarray(uzay.xyz, dtype=float), (n, 1))
    raise ValueError(_("kaynak noktaları gösterilemiyor: desteklenmeyen uzay dağılımı %s")
                     % ad)


def _kisit_fisil_mi(kaynak) -> bool:
    kisit = dict(getattr(kaynak, "constraints", None) or {})
    if kisit.get("domains") or kisit.get("domain_ids"):   # 0.16: domain_ids
        raise ValueError(_("kaynak noktaları gösterilemiyor: domain kısıtı "
                           "desteklenmiyor"))
    return bool(kisit.get("fissionable"))


def _fisil_noktalar(noktalar, fisil):
    """Noktadaki malzeme fisil mi (bool dizi); geometri disi nokta reddedilir."""
    import openmc.lib
    from openmc.exceptions import GeometryError
    kabul = np.zeros(len(noktalar), dtype=bool)
    for i, xyz in enumerate(noktalar):
        try:
            m = openmc.lib.find_material(xyz)
        except GeometryError:
            continue                        # geometri disi: OpenMC de reddeder
        kabul[i] = m is not None and m.id in fisil
    return kabul


def _kaynak_secimi(kaynaklar, rng, n):
    """Her aday icin kaynak sirasi (siddetle agirlikli)."""
    guc = np.array([max(float(getattr(k, "strength", 1.0)), 0.0) for k in kaynaklar])
    if guc.sum() <= 0:
        raise ValueError(_("kaynak şiddetlerinin toplamı sıfır"))
    return rng.choice(len(kaynaklar), size=n, p=guc / guc.sum())


def ayar_kaynagi(kaynaklar, fisil, sayi: int, tohum: int):
    """settings.source'tan sayi nokta: ((n, 3) dizi, deneme sayisi)."""
    if not kaynaklar:
        raise ValueError(_("modelde kaynak tanımı yok"))
    rng = np.random.default_rng(tohum)
    fisil_kisit = [_kisit_fisil_mi(k) for k in kaynaklar]
    kabul_edilen, deneme = [], 0
    toplam = 0
    while toplam < sayi:
        secim = _kaynak_secimi(kaynaklar, rng, _PARTI)
        aday = np.empty((_PARTI, 3))
        for i, k in enumerate(kaynaklar):
            yer = secim == i
            aday[yer] = _uzay_ornekle(k.space, int(yer.sum()), rng)
        kisitli = np.array([fisil_kisit[i] for i in secim])
        kabul = ~kisitli
        if kisitli.any():
            kabul[kisitli] = _fisil_noktalar(aday[kisitli], fisil)
        deneme += _PARTI
        kabul_edilen.append(aday[kabul])
        toplam += int(kabul.sum())
        if deneme >= _EN_AZ_DENEME and toplam < KABUL_ORANI_EN_AZ * deneme:
            raise ValueError(_("kaynak örneklemesinde kabul oranı %%%.1f (< %%%g): kaynak kutusu "
                               "fisil malzemeyi kapsamıyor olabilir")
                             % (100.0 * toplam / deneme, 100.0 * KABUL_ORANI_EN_AZ))
    return np.concatenate(kabul_edilen)[:sayi], deneme


def statepoint_kaynagi(yol: str, sayi: int, tohum: int):
    """Statepoint kaynak bankasindan en cok sayi nokta (rastgele alt kume):
    ((n, 3) dizi, bankadaki toplam)."""
    import h5py
    if not os.path.isfile(yol):
        raise ValueError(_("statepoint dosyası bulunamadı: %s") % yol)
    with h5py.File(yol, "r") as f:
        if "source_bank" not in f or not f.attrs.get("source_present", 1):
            raise ValueError(_("statepoint dosyasında kaynak bankası yok (koşu "
                               "sourcepoint yazmamış)"))
        banka = f["source_bank"]
        toplam = int(banka.shape[0])
        if toplam == 0:
            raise ValueError(_("statepoint kaynak bankası boş"))
        secim = np.arange(toplam)
        if toplam > sayi:
            secim = np.sort(np.random.default_rng(tohum).choice(toplam, sayi, replace=False))
        r = banka.fields("r")[secim] if hasattr(banka, "fields") else banka[secim]["r"]
    r = np.asarray(r)
    noktalar = np.stack([r["x"], r["y"], r["z"]], axis=-1) if r.dtype.names else r
    return np.ascontiguousarray(noktalar, dtype=np.float64).reshape(-1, 3), toplam


def kaynak_noktalari(oturum, istek: dict):
    """(yanit basligi, {"r": dizi}) -- 'kaynak' istegi (modul belgesi)."""
    t0 = time.perf_counter()
    sayi, tohum = istek["sayi"], istek.get("tohum", 1)
    if istek.get("statepoint"):
        r, toplam = statepoint_kaynagi(istek["statepoint"], sayi, tohum)
        tur, deneme = KAYNAK_STATEPOINT, toplam
    else:
        r, deneme = ayar_kaynagi(oturum.kaynaklar, oturum.fisil, sayi, tohum)
        tur, toplam = KAYNAK_AYAR, len(r)
    return ({"tur": YANIT_KAYNAK, "no": istek["no"], "kaynak": tur, "toplam": toplam,
             "deneme": deneme, "sure": time.perf_counter() - t0}, {"r": r})
