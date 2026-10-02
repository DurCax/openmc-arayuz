# -*- coding: utf-8 -*-
"""
 cekirdek/mesh_tally/sonuc.py  --  mesh tally sonuclari (v3 Y1; Qt'siz)

 Statepoint'teki mesh tally'lerini okur (bir MeshFilter + istege bagli
 EnergyFilter), skor/grup secer, normalize eder, bagil hatayi hesaplar ve
 guvenilmez hucreleri isaretler.

 NORMALIZASYON (OpenMC tally'leri kaynak parcacigi basinadir):
   kaynak  ham deger (sabit kaynakta OpenMC kaynak siddetini zaten uygular)
   hacim   deger / hucre hacmi            (akı: 1/cm2 per kaynak)
   bagil   hacim basina deger / skorlu hucrelerin ortalamasi (1.00 = ortalama)
   mutlak  ozdeger hesabinda: S = P / (H * e)  [kaynak/s]; deger * S / V
           (isinma skorlarinda ayrica eV -> J: W/cm3; akı n/cm2/s).
           H = agin kapsadigi isinma skoru toplami (eV/kaynak) -> ag BUTUN
           fisil bolgeyi kapsamali (otomatik sinirlar kapsar).
 Normalizasyon carpaninin kendi belirsizligi (H'nin sigma'si, bagilda
 ortalamanin sigma'si) sigma'ya katilmaz -- belgede yazili.
 Gruplar toplanirken sigma'lar bagimsiz varsayilir (karelerin toplami).
"""

import math
from dataclasses import dataclass

import numpy as np

from cekirdek.ceviri import _, N_
from cekirdek.gunluk import kaydedici
from cekirdek.mesh_tally import geometri as _geo

_log = kaydedici(__name__)

# CODATA 2018 (SI tanimi, kesin): 1 eV = 1.602176634e-19 J
EV_JOULE = 1.602176634e-19

# Bagil hata esigi: R < 0.10 "genellikle guvenilir" (nokta dedektorleri haric).
BAGIL_HATA_ESIGI = 0.10
BAGIL_HATA_KAYNAGI = ("MCNP5 Manual Vol. I (LA-UR-03-1987), Bölüm 2, 'Guidelines for "
                      "interpreting the relative error R': R < 0.10 genellikle güvenilir.")

ISI_SKORLARI = ("kappa-fission", "fission-q-recoverable", "fission-q-prompt",
                "heating", "heating-local")

NORMALIZASYONLAR = ("kaynak", "hacim", "bagil", "mutlak")
NORMALIZASYON_ADLARI = {
    "kaynak": N_("Kaynak nötronu başına"),
    "hacim": N_("Hacim başına (/cm³)"),
    "bagil": N_("Ortalamaya bağıl (1 = ortalama)"),
    "mutlak": N_("Mutlak (toplam güçten)"),
}


@dataclass(frozen=True)
class MeshSonuc:
    """Bir mesh tally'sinin sonucu. ortalama/sapma sekli (n1, n2, n3, ne, nn, ns)."""
    ad: str
    tur: str
    izgaralar: tuple
    merkez: tuple
    skorlar: tuple
    nuklidler: tuple
    enerji: tuple          # grup sinirlari [eV] ya da None (tek grup)
    ortalama: np.ndarray
    sapma: np.ndarray
    ozdeger: bool

    @property
    def boyut(self):
        return tuple(len(g) - 1 for g in self.izgaralar)

    @property
    def grup_sayisi(self):
        return self.ortalama.shape[3]


# ---------------------------------------------------------------------------
# okuma
# ---------------------------------------------------------------------------

def _tally_filtreleri(tal):
    """(mesh filtresi, enerji filtresi | None, neden | None)."""
    import openmc
    mesh_f = [f for f in tal.filters if type(f) is openmc.MeshFilter]
    enerji_f = [f for f in tal.filters if type(f) is openmc.EnergyFilter]
    diger = [f for f in tal.filters if f not in mesh_f and f not in enerji_f]
    if len(mesh_f) != 1:
        return None, None, None if not mesh_f else _("birden çok ağ filtresi")
    if diger or len(enerji_f) > 1:
        return None, None, _("ağ ve enerji dışında filtre var: %s") % ", ".join(
            type(f).__name__ for f in diger + enerji_f[1:])
    return mesh_f[0], (enerji_f[0] if enerji_f else None), None


def _yeniden_bicimle(tal, deger, mesh_f, enerji_f):
    """get_reshaped_data(expand_dims) -> (i, j, k, e, n, s) (yeni dizi)."""
    veri = tal.get_reshaped_data(value=deger, expand_dims=True)
    filtreler = list(tal.filters)
    mi = filtreler.index(mesh_f)
    eksenler = list(range(mi, mi + 3))
    if enerji_f is not None:
        ei = filtreler.index(enerji_f)
        eksenler.append(ei if ei < mi else ei + 2)
    veri = np.moveaxis(veri, eksenler, list(range(len(eksenler))))
    if enerji_f is None:
        veri = veri[:, :, :, None]
    return np.array(veri, dtype=float)


def tally_sonucu(tal, ozdeger):
    """Tek bir openmc.Tally -> (MeshSonuc | None, atlama nedeni | None)."""
    mesh_f, enerji_f, neden = _tally_filtreleri(tal)
    if mesh_f is None:
        return None, neden
    try:
        tur = _geo.mesh_tur_bul(mesh_f.mesh)
    except ValueError as e:
        return None, str(e)
    ad = tal.name or "tally_%d" % tal.id
    return MeshSonuc(
        ad=ad, tur=tur, izgaralar=_geo.mesh_izgaralari(mesh_f.mesh),
        merkez=tuple(float(x) for x in getattr(mesh_f.mesh, "origin", (0.0, 0.0, 0.0))),
        skorlar=tuple(tal.scores), nuklidler=tuple(tal.nuclides),
        enerji=tuple(float(x) for x in enerji_f.values) if enerji_f is not None else None,
        ortalama=_yeniden_bicimle(tal, "mean", mesh_f, enerji_f),
        sapma=_yeniden_bicimle(tal, "std_dev", mesh_f, enerji_f),
        ozdeger=bool(ozdeger)), None


def oku(statepoint_yolu):
    """
    Statepoint'teki mesh tally'leri.
    DONER ([MeshSonuc], [(tally adi, atlama nedeni)]) -- mesh filtresi olmayan
    tally'ler hic listelenmez; okunamayan/desteklenmeyen mesh tally'si nedeniyle.
    """
    import openmc
    sonuclar, atlanan = [], []
    with openmc.StatePoint(str(statepoint_yolu)) as sp:
        ozdeger = sp.run_mode == "eigenvalue"
        for tal in sp.tallies.values():
            try:
                s, neden = tally_sonucu(tal, ozdeger)
            except (ValueError, KeyError, IndexError) as e:
                _log.warning("'%s' mesh tally'si okunamadı", tal.name, exc_info=True)
                s, neden = None, _("okunamadı: %s") % e
            if s is not None:
                sonuclar.append(s)
            elif neden:
                atlanan.append((tal.name or "tally_%d" % tal.id, neden))
    return sonuclar, atlanan


# ---------------------------------------------------------------------------
# secim ve normalizasyon
# ---------------------------------------------------------------------------

def secim(sonuc, skor, grup=None, nuklid=0):
    """(ortalama, sapma) 3B diziler; grup None -> butun gruplarin toplami."""
    if skor not in sonuc.skorlar:
        raise ValueError(_("'%s' skoru bu tally'de yok (%s)")
                         % (skor, ", ".join(sonuc.skorlar)))
    si = sonuc.skorlar.index(skor)
    o = sonuc.ortalama[:, :, :, :, nuklid, si]
    s = sonuc.sapma[:, :, :, :, nuklid, si]
    if grup is None:
        return o.sum(axis=3), np.sqrt((s ** 2).sum(axis=3))
    if not 0 <= grup < o.shape[3]:
        raise ValueError(_("geçersiz enerji grubu: %s") % grup)
    return o[:, :, :, grup].copy(), s[:, :, :, grup].copy()


def isi_toplami(sonuc, nuklid=0):
    """Tally'deki ilk isinma skorunun ag ve gruplar uzerinden toplami (eV/kaynak); yoksa None."""
    skor = next((s for s in ISI_SKORLARI if s in sonuc.skorlar), None)
    if skor is None:
        return None
    return float(secim(sonuc, skor, None, nuklid)[0].sum())


def kaynak_hizi(toplam_guc, isi_ev):
    """S [kaynak/s] = P [W] / (H [eV/kaynak] * e). Pozitif olmayan girdi ValueError."""
    if not (toplam_guc and toplam_guc > 0):
        raise ValueError(_("mutlak normalizasyon için toplam güç sıfırdan büyük olmalı"))
    if not (isi_ev and isi_ev > 0):
        raise ValueError(_("mutlak normalizasyon için ağda ısınma skoru (kappa-fission, "
                           "heating …) sıfırdan büyük olmalı"))
    return float(toplam_guc) / (float(isi_ev) * EV_JOULE)


def birim(skor, yontem, ozdeger=True):
    """Gorunen birim metni."""
    isi = skor in ISI_SKORLARI
    aki = skor == "flux"
    if yontem == "bagil":
        return _("bağıl (1 = ortalama)")
    if yontem == "mutlak":
        return "W/cm³" if isi else ("n/cm²·s" if aki else _("1/cm³·s"))
    pay = "eV" if isi else ("n·cm" if aki else _("tepkime"))
    if yontem == "hacim":
        pay = "eV/cm³" if isi else ("n/cm²" if aki else _("tepkime/cm³"))
    return pay + (_(" / kaynak nötronu") if ozdeger else _(" (kaynak şiddetiyle)"))


def normalize(ortalama, sapma, hacim, yontem, kaynak_hizi=None, skor=None, ozdeger=True):
    """(ortalama, sapma, birim) -- yeni diziler (bkz. modul belgesi)."""
    if yontem not in NORMALIZASYONLAR:
        raise ValueError(_("bilinmeyen normalizasyon: %s") % yontem)
    o, s = np.array(ortalama, dtype=float), np.array(sapma, dtype=float)
    if yontem == "kaynak":
        return o, s, birim(skor, yontem, ozdeger)
    o, s = o / hacim, s / hacim
    if yontem == "bagil":
        skorlu = o > 0
        ort = float(o[skorlu].mean()) if skorlu.any() else 0.0
        if ort <= 0.0:
            raise ValueError(_("bağıl normalizasyon: ağda skorlu hücre yok"))
        return o / ort, s / ort, birim(skor, yontem, ozdeger)
    if yontem == "mutlak":
        if not ozdeger:
            raise ValueError(_("mutlak normalizasyon yalnız özdeğer hesabında; sabit "
                               "kaynakta değerler kaynak şiddetiyle zaten ölçeklidir"))
        if not kaynak_hizi:
            raise ValueError(_("mutlak normalizasyon için kaynak hızı gerekli"))
        c = float(kaynak_hizi) * (EV_JOULE if skor in ISI_SKORLARI else 1.0)
        return o * c, s * c, birim(skor, yontem, ozdeger)
    return o, s, birim(skor, yontem, ozdeger)


# ---------------------------------------------------------------------------
# istatistik
# ---------------------------------------------------------------------------

def bagil_hata(ortalama, sapma):
    """sigma / |deger|; skorsuz (0) hucrede NaN (yeni dizi)."""
    o = np.abs(np.asarray(ortalama, dtype=float))
    s = np.asarray(sapma, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(o > 0, s / np.where(o > 0, o, 1.0), np.nan)


def yuksek_hata_maskesi(ortalama, sapma, esik=BAGIL_HATA_ESIGI):
    """Guvenilmez hucreler: bagil hata > esik ya da hic skor yok."""
    b = bagil_hata(ortalama, sapma)
    return np.isnan(b) | (np.nan_to_num(b, nan=0.0) > esik)


def ozet(ortalama, sapma, esik=BAGIL_HATA_ESIGI):
    """{"hucre", "skorsuz", "yuksek", "en_buyuk_bagil"} (skorlu hucrelerde)."""
    b = bagil_hata(ortalama, sapma)
    skorsuz = int(np.isnan(b).sum())
    skorlu = b[~np.isnan(b)]
    return {"hucre": int(b.size), "skorsuz": skorsuz,
            "yuksek": int((skorlu > esik).sum()),
            "en_buyuk_bagil": float(skorlu.max()) if skorlu.size else math.nan}
