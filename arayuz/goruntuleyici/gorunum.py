# -*- coding: utf-8 -*-
"""
 gorunum.py  --  Goruntuleyici kesit gorunumu (saf; Qt'siz, test edilir)

 Gorunum degismez bir degerdir: eksen (xy/xz/yz), merkez (x, y, z), genislik
 (yatay, dikey) cm ve yatay piksel. Yakinlastirma/kaydirma YENI Gorunum dondurur.

 Piksel kurali OpenMC slice_data ile ayni (openmc.lib.slice_data; plot.cpp):
 satir 0 goruntunun USTU (dikey eksenin en buyuk degeri), piksel degeri piksel
 MERKEZINDEKI noktanindir:
     u_j = u0 + (j + 0.5) du        v_i = v1 - (i + 0.5) dv
 testler/test_y2_isci.py bunu bilinen cakismali modelde dogrular.
"""

from dataclasses import dataclass, replace

from cekirdek import cizim_goruntu as cg
from cekirdek import cizim_sureci as cs
from cekirdek.ceviri import _
from arayuz.onizleme_boyama import HUCRE_CAKISMA

# (yatay, dikey, normal) eksen sirasi
EKSENLER = {"xy": (0, 1, 2), "xz": (0, 2, 1), "yz": (1, 2, 0)}
EKSEN_ADLARI = ("x", "y", "z")
# Isci ile ayni sinirlar (cekirdek/cizim_goruntu.py): 1 um - 10 km
EN_KUCUK_GENISLIK = cg.GENISLIK_EN_AZ
EN_BUYUK_GENISLIK = cg.KOORDINAT_SINIRI

DURUM_NORMAL, DURUM_BOSLUK, DURUM_TANIMSIZ, DURUM_CAKISMA = (
    "normal", "bosluk", "tanimsiz", "cakisma")


@dataclass(frozen=True)
class Gorunum:
    """Bir kesit penceresi."""
    eksen: str
    merkez: tuple
    genislik: tuple
    piksel: int

    @property
    def piksel_dikey(self) -> int:
        """Kare piksel icin dikey piksel (isci sinirlarina kirpilir)."""
        oran = self.genislik[1] / self.genislik[0]
        return int(min(max(round(self.piksel * oran), cs.PIKSEL_EN_AZ), cs.PIKSEL_EN_COK))

    @property
    def konum(self) -> float:
        """Kesit duzleminin normal eksendeki konumu [cm]."""
        return self.merkez[EKSENLER[self.eksen][2]]

    @property
    def kapsam(self) -> tuple:
        """(u0, u1, v0, v1) -- imshow extent."""
        h, d, _n = EKSENLER[self.eksen]
        cu, cv = self.merkez[h], self.merkez[d]
        w, y = self.genislik
        return (cu - w / 2.0, cu + w / 2.0, cv - y / 2.0, cv + y / 2.0)

    def istek_ogesi(self) -> dict:
        """Isci 'ciz' isteginin kesit ogesi (cekirdek/cizim_goruntu.py)."""
        return {"eksen": self.eksen, "piksel": int(self.piksel),
                "piksel_dikey": self.piksel_dikey,
                "merkez": [float(v) for v in self.merkez],
                "genislik": [float(v) for v in self.genislik]}


def _sinirla(deger: float) -> float:
    return min(max(float(deger), EN_KUCUK_GENISLIK), EN_BUYUK_GENISLIK)


def varsayilan(sinir_kutu, yukseklik, eksen: str = "xy", piksel: int = 800) -> Gorunum:
    """Butun modeli gosteren gorunum (merkez orijin: cs.KESIT_MERKEZI)."""
    genislik = cs.kesit_genisligi(eksen, sinir_kutu, yukseklik)
    return Gorunum(eksen, tuple(cs.KESIT_MERKEZI), tuple(_sinirla(g) for g in genislik),
                   int(piksel))


def yakinlastir(g: Gorunum, kat: float, odak=None) -> Gorunum:
    """kat > 1 yakinlastirir; odak (u, v) noktasi ekranda yerinde kalir."""
    h, d, _n = EKSENLER[g.eksen]
    yeni_g = tuple(_sinirla(w / kat) for w in g.genislik)
    merkez = list(g.merkez)
    if odak is not None:
        for eksen, o, eski, yeni in ((h, odak[0], g.genislik[0], yeni_g[0]),
                                     (d, odak[1], g.genislik[1], yeni_g[1])):
            merkez[eksen] = o + (g.merkez[eksen] - o) * (yeni / eski)
    return replace(g, merkez=tuple(merkez), genislik=yeni_g)


def kaydir(g: Gorunum, du: float, dv: float) -> Gorunum:
    """Merkezi kesit duzleminde (du, dv) kadar kaydirir."""
    h, d, _n = EKSENLER[g.eksen]
    merkez = list(g.merkez)
    merkez[h] += du
    merkez[d] += dv
    return replace(g, merkez=tuple(merkez))


def konum_ayarla(g: Gorunum, deger: float) -> Gorunum:
    """Kesit duzleminin normal eksendeki konumu."""
    merkez = list(g.merkez)
    merkez[EKSENLER[g.eksen][2]] = float(deger)
    return replace(g, merkez=tuple(merkez))


def piksel_merkezi(g: Gorunum, i: int, j: int, sekil=None) -> tuple:
    """(satir i, sutun j) pikselinin merkezi (u, v)."""
    nv, nh = sekil[:2] if sekil is not None else (g.piksel_dikey, g.piksel)
    u0, u1, v0, v1 = g.kapsam
    return (u0 + (j + 0.5) * (u1 - u0) / nh, v1 - (i + 0.5) * (v1 - v0) / nv)


def piksel_indeksi(g: Gorunum, u: float, v: float, sekil=None):
    """(u, v) noktasini iceren piksel (i, j); pencere disinda None."""
    nv, nh = sekil[:2] if sekil is not None else (g.piksel_dikey, g.piksel)
    u0, u1, v0, v1 = g.kapsam
    if not (u0 <= u < u1 and v0 < v <= v1):
        return None
    j = min(int((u - u0) / (u1 - u0) * nh), nh - 1)
    i = min(int((v1 - v) / (v1 - v0) * nv), nv - 1)
    return i, j


def nokta(g: Gorunum, u: float, v: float) -> tuple:
    """Kesit duzlemindeki (u, v) -> (x, y, z)."""
    h, d, _n = EKSENLER[g.eksen]
    xyz = list(g.merkez)
    xyz[h], xyz[d] = float(u), float(v)
    return tuple(xyz)


@dataclass(frozen=True)
class NoktaBilgisi:
    """Fare altindaki noktanin bilgisi."""
    xyz: tuple
    hucre: int
    ornek: int
    malzeme: int
    hucre_adi: str
    malzeme_adi: str
    durum: str


def _durum(hucre: int, malzeme: int) -> str:
    if malzeme == cs.CAKISMA or hucre == HUCRE_CAKISMA:
        return DURUM_CAKISMA
    if hucre == cs.TANIMSIZ:
        return DURUM_TANIMSIZ
    if malzeme == cs.BOSLUK:
        return DURUM_BOSLUK
    return DURUM_NORMAL


def nokta_bilgisi(g: Gorunum, geom, u: float, v: float, adlar=None):
    """geom (v, h, 3) [hucre, ornek, malzeme] -> NoktaBilgisi; pencere disi None."""
    yer = piksel_indeksi(g, u, v, geom.shape)
    if yer is None:
        return None
    hucre, ornek, malzeme = (int(x) for x in geom[yer[0], yer[1], :3])
    adlar = adlar or {}
    return NoktaBilgisi(
        xyz=nokta(g, u, v), hucre=hucre, ornek=ornek, malzeme=malzeme,
        hucre_adi=(adlar.get("hucre_adlari") or {}).get(str(hucre), ""),
        malzeme_adi=(adlar.get("malzeme_adlari") or {}).get(str(malzeme), ""),
        durum=_durum(hucre, malzeme))


def bilgi_metni(b: NoktaBilgisi) -> str:
    """Durum cubugu metni: koordinat + hucre/malzeme ya da ozel durum."""
    konum = "  ".join("%s = %.4g cm" % (a, v) for a, v in zip(EKSEN_ADLARI, b.xyz))
    if b.durum == DURUM_CAKISMA:
        return konum + "   " + _("ÇAKIŞMA: nokta birden çok hücrede")
    if b.durum == DURUM_TANIMSIZ:
        return konum + "   " + _("hücre yok (geometri dışı ya da tanımsız bölge)")
    hucre = _("hücre %d") % b.hucre + (" (%s)" % b.hucre_adi if b.hucre_adi else "")
    if b.ornek:
        hucre += _(", örnek %d") % b.ornek
    malzeme = (_("boşluk (void)") if b.durum == DURUM_BOSLUK else
               _("malzeme %d") % b.malzeme + (" (%s)" % b.malzeme_adi if b.malzeme_adi
                                              else ""))
    return "%s   %s · %s" % (konum, hucre, malzeme)
