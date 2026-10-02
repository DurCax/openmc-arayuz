# -*- coding: utf-8 -*-
"""
 cekirdek/mesh_tally/sonuc.py  --  mesh tally sonuclarini okuma (v3 Y1; Qt'siz)

 Statepoint'teki mesh tally'lerini (bir MeshFilter + istege bagli EnergyFilter)
 ve filtresiz genel isinma tally'sini (tanim.GENEL_ISI_TALLY) okur, skor/grup
 secer. Normalizasyon ve istatistik: normalizasyon.py.

 OpenMC 0.16 tally'leri kaynak parcacigi basinadir; SABIT KAYNAKTA toplam kaynak
 siddetiyle carpilir (olculdu 02.10.2026: ayni problem strength=1 -> 30.48,
 strength=1000 -> 30478, oran 1000).
"""

from dataclasses import dataclass, replace

import numpy as np

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from cekirdek.mesh_tally import geometri as _geo
from cekirdek.mesh_tally.tanim import GENEL_ISI_TALLY

_log = kaydedici(__name__)

_EKSEN_SAYISI = 3
GRUP_TOPLAMI_NOTU = ("Grup toplamında σ, gruplar bağımsız varsayılarak (σ² toplamı) "
                     "hesaplanır; gruplar pozitif ilişkili olduğundan bu iyimser bir "
                     "tahmindir.")


@dataclass(frozen=True, eq=False)
class MeshSonuc:
    """Bir mesh tally'sinin sonucu. ortalama/sapma sekli (n1, n2, n3, ne, nn, ns)."""
    ad: str
    tur: str
    izgaralar: tuple          # tuple[np.ndarray, np.ndarray, np.ndarray]
    merkez: tuple             # (x, y, z) [cm]
    skorlar: tuple            # tuple[str, ...]
    nuklidler: tuple          # tuple[str, ...]
    enerji: tuple | None      # grup sinirlari [eV]; None = tek grup
    ortalama: np.ndarray
    sapma: np.ndarray
    ozdeger: bool

    @property
    def boyut(self) -> tuple:
        return tuple(len(g) - 1 for g in self.izgaralar)

    @property
    def grup_sayisi(self) -> int:
        return self.ortalama.shape[3]


def _dondur(dizi):
    d = np.array(dizi, dtype=float)
    d.setflags(write=False)
    return d


def salt_okunur(sonuc: MeshSonuc) -> MeshSonuc:
    """Dizileri salt okunur kopyalarla degistirilmis yeni MeshSonuc."""
    return replace(sonuc, ortalama=_dondur(sonuc.ortalama), sapma=_dondur(sonuc.sapma),
                   izgaralar=tuple(_dondur(g) for g in sonuc.izgaralar))


# ---------------------------------------------------------------------------
# okuma
# ---------------------------------------------------------------------------

def _tally_filtreleri(tal):
    """(mesh filtresi, enerji filtresi | None, neden | None)."""
    import openmc
    mesh_f = [f for f in tal.filters if type(f) is openmc.MeshFilter]
    enerji_f = [f for f in tal.filters if type(f) is openmc.EnergyFilter]
    diger = [f for f in tal.filters if f not in mesh_f and f not in enerji_f]
    if not mesh_f:
        return None, None, None
    if len(mesh_f) > 1:
        return None, None, _("birden çok ağ filtresi")
    if diger or len(enerji_f) > 1:
        return None, None, (_("ağ ve enerji dışında filtre var: %s") % ", ".join(
            type(f).__name__ for f in diger + enerji_f[1:]))
    if len(mesh_f[0].mesh.dimension) != _EKSEN_SAYISI:
        return None, None, (_("ağ %d boyutlu; yalnız 3 boyutlu ağ gösterilir")
                            % len(mesh_f[0].mesh.dimension))
    return mesh_f[0], (enerji_f[0] if enerji_f else None), None


def _yeniden_bicimle(tal, deger, mesh_f, enerji_f):
    """get_reshaped_data(expand_dims) -> (i, j, k, e, n, s) (yeni dizi)."""
    veri = tal.get_reshaped_data(value=deger, expand_dims=True)
    filtreler = list(tal.filters)
    mi = filtreler.index(mesh_f)
    eksenler = list(range(mi, mi + _EKSEN_SAYISI))
    if enerji_f is not None:
        ei = filtreler.index(enerji_f)
        eksenler.append(ei if ei < mi else ei + _EKSEN_SAYISI - 1)
    veri = np.moveaxis(veri, eksenler, list(range(len(eksenler))))
    if enerji_f is None:
        veri = veri[:, :, :, None]
    return _dondur(veri)


def tally_sonucu(tal, ozdeger: bool):
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
        ad=ad, tur=tur, izgaralar=tuple(_dondur(g) for g in _geo.mesh_izgaralari(mesh_f.mesh)),
        merkez=tuple(float(x) for x in getattr(mesh_f.mesh, "origin", (0.0, 0.0, 0.0))),
        skorlar=tuple(tal.scores), nuklidler=tuple(tal.nuclides),
        enerji=tuple(float(x) for x in enerji_f.values) if enerji_f is not None else None,
        ortalama=_yeniden_bicimle(tal, "mean", mesh_f, enerji_f),
        sapma=_yeniden_bicimle(tal, "std_dev", mesh_f, enerji_f),
        ozdeger=bool(ozdeger)), None


def _tally_oku(tal, ozdeger):
    """Tek tally; beklenmeyen hata butun okumayi dusurmez (gunluk + neden)."""
    try:
        return tally_sonucu(tal, ozdeger)
    except Exception as e:  # noqa: BLE001 -- tally basina yalitim; nedeniyle bildirilir
        _log.warning("'%s' mesh tally'si okunamadı", tal.name, exc_info=True)
        return None, _("okunamadı: %s") % e


def oku(statepoint_yolu):
    """
    Statepoint'teki mesh tally'leri.
    DONER ([MeshSonuc], [(tally adi, atlama nedeni)]) -- mesh filtresi olmayan
    tally'ler listelenmez; okunamayan/desteklenmeyen mesh tally'si nedeniyle.
    Statepoint'in kendisi acilamazsa (OSError, KeyError ...) hata yukari cikar.
    """
    import openmc
    sonuclar, atlanan = [], []
    with openmc.StatePoint(str(statepoint_yolu)) as sp:
        ozdeger = sp.run_mode == "eigenvalue"
        for tal in sp.tallies.values():
            s, neden = _tally_oku(tal, ozdeger)
            if s is not None:
                sonuclar.append(s)
            elif neden:
                atlanan.append((tal.name or "tally_%d" % tal.id, neden))
    return sonuclar, atlanan


def genel_isi_oku(statepoint_yolu) -> dict:
    """{skor: kaynak nötronu basina ortalama [eV]} -- genel isinma tally'si;
    eski kosuda (tally yok) bos sozluk (DEBUG gunlugu)."""
    import openmc
    with openmc.StatePoint(str(statepoint_yolu)) as sp:
        try:
            tal = sp.get_tally(name=GENEL_ISI_TALLY)
        except LookupError:
            _log.debug("'%s' tally'si statepoint'te yok (eski koşu)", GENEL_ISI_TALLY)
            return {}
        degerler = np.asarray(tal.mean, dtype=float).reshape(-1, len(tal.scores)).sum(axis=0)
        return {skor: float(d) for skor, d in zip(tal.scores, degerler)}


def secim(sonuc: MeshSonuc, skor: str, grup=None, nuklid: int = 0):
    """(ortalama, sapma) 3B diziler (yeni); grup None -> butun gruplarin toplami
    (sigma: GRUP_TOPLAMI_NOTU)."""
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
    return np.array(o[:, :, :, grup]), np.array(s[:, :, :, grup])
