# -*- coding: utf-8 -*-
"""
================================================================================
 triso.py  --  Y9: TRISO yakit parcacigi, kompakt ve pebble bilesenleri (saf hesap)
================================================================================
 Tanim (spec["trisolar"][]), geometri agacinda "bilesen" dugumu olarak kullanilir
 (cekirdek/geometri/bilesen_triso.py kurar, gezinti.py hacim verir):

   {"ad": "agr1_kompakt",
    "sekil": "kompakt" | "pebble",
    "katmanlar": [{"ad": "kernel", "r": 0.0175, "malzeme": "uco"}, ...],  # icten disa
    "matris_malzeme": "grafit_matris",
    "yaricap": 0.6225, "yukseklik": 2.5,         # kompakt: silindir [cm]
    "yakit_yaricap": 2.5, "dis_yaricap": 3.0,    # pebble: yakit bolgesi / kabuk [cm]
    "kabuk_malzeme": "grafit", "dis_malzeme": "helyum",   # pebble
    "paketleme": 0.35,                            # hedef paketleme orani (hacim)
    "yontem": "rastgele" | "duzenli",
    "tohum": 1}

 PAKETLEME ORANI = N * (4/3) pi r_p^3 / V_kap  (r_p: en dis katman yaricapi,
 V_kap: kompaktta pi R^2 h, pebblede (4/3) pi r_yakit^3). Hedef sayi
 N = int(pf V / V_p) -- openmc.model.pack_spheres ile ayni kural.

 YONTEMLER (OpenMC 0.16 pack_spheres belgesi; Jodrey ve Tory 1985)
   rastgele : rastgele ardisik paketleme (RSP) pf <= ~0.30'a, uzerinde yakin
              rastgele paketleme (CRP, Jodrey-Tory) ~0.64'e kadar. Kabin sinirlari
              kompakt (silindir) ve pebble (kure). Tohum belirleyicidir.
   duzenli  : basit kubik kafes (SC) -- parcacik merkezleri a adimli kubik izgarada;
              pf <= pi/6 = 0.5236 (SC siniri). Adim, hedef sayiya en yakin sayiyi
              verecek sekilde taranir; gercek pf raporlanir.
 Her ikisi de OpenMC'ye openmc.model.create_triso_lattice ile verilir (parcacik basina
 hucre aramasi yerine kafes hucresi basina yerel liste: hiz icin sart).

 KATMAN KAYNAKLARI (varsayilanlar, sablon() ile)
   AGR-1 taban parcacigi (INL AGR-1 yakiti, UCO cekirdek): cekirdek capi ~350 um,
     tampon 100, IPyC 40, SiC 35, OPyC 40 um; yogunluklar 10.9 / 1.05 / 1.90 / 3.20 /
     1.91 g/cm3 (INL AGR-1 yakit tasarimi; Petti vd.).
   HTR-10 (IAEA-TECDOC-1382, INL/EXT-06-01): UO2 cekirdek capi 500 um, tampon 90,
     IPyC 40, SiC 35, OPyC 40 um; 10.4 / 1.1 / 1.9 / 3.18 / 1.9 g/cm3; kure: yakit
     bolgesi yaricapi 2.5 cm, kabuk dis yaricapi 3.0 cm.
 Bunlar baslangic degerleridir; sertifika degil, kullanici kendi tasarimini girer.
================================================================================
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from cekirdek.ceviri import _

SEKILLER = ("kompakt", "pebble")
YONTEMLER = ("rastgele", "duzenli")
VARSAYILAN_TOHUM = 1

# openmc.model.pack_spheres sinirlari (OpenMC 0.16: MAX_PF_RSP=0.38, MAX_PF_CRP=0.64).
RSP_ESIGI = 0.30          # initial_pf varsayilani: bunun uzerinde CRP calisir (yavaslar)
RSP_SINIRI = 0.38
CRP_SINIRI = 0.64
SC_SINIRI = math.pi / 6.0   # basit kubik kafesin en yuksek paketleme orani
# Kafes hucresi boyutu: parcacik capinin kaci kati (hiz / bellek dengesi; olculdu:
# 3 cap ~18 parcacik/hucre, tracking maliyeti ile hucre sayisi dengesi)
HUCRE_CAP_KATI = 3.0
# Bu parcacik sayisinin ustunde Python'da kurulum belirgin uzar (olculdu: 857 -> 2.5 s)
UYARI_PARCACIK_SAYISI = 50000
KATMAN_ADLARI = ("kernel", "buffer", "ipyc", "sic", "opyc")


@dataclass(frozen=True)
class Konteyner:
    """Parcaciklarin paketlendigi kap: kompakt (silindir) ya da pebble yakit bolgesi."""
    sekil: str
    yaricap: float
    yukseklik: float          # pebblede 2 * yaricap (kutu yuksekligi)

    @property
    def hacim(self) -> float:
        if self.sekil == "pebble":
            return 4.0 / 3.0 * math.pi * self.yaricap ** 3
        return math.pi * self.yaricap ** 2 * self.yukseklik

    @property
    def kutu(self) -> Tuple[float, float, float]:
        """Kabin eksene hizali sinir kutusunun kenarlari (x, y, z) [cm]."""
        return (2.0 * self.yaricap, 2.0 * self.yaricap, self.yukseklik)


def konteyner(t: dict) -> Konteyner:
    """Tanimdan parcacik kabi. Eksik/gecersiz alan ValueError."""
    sekil = t.get("sekil") or "kompakt"
    if sekil == "pebble":
        r = _pozitif(t, "yakit_yaricap")
        return Konteyner("pebble", r, 2.0 * r)
    if sekil != "kompakt":
        raise ValueError(_("bilinmeyen TRISO şekli: %r (geçerli: %s)") % (sekil, ", ".join(SEKILLER)))
    return Konteyner("kompakt", _pozitif(t, "yaricap"), _pozitif(t, "yukseklik"))


def _pozitif(t: dict, anahtar: str) -> float:
    try:
        v = float(t.get(anahtar))
    except (TypeError, ValueError):
        raise ValueError(_("'%s' sayı olmalı") % anahtar) from None
    if not v > 0.0:
        raise ValueError(_("'%s' pozitif olmalı (%s)") % (anahtar, v))
    return v


def parcacik_yaricap(t: dict) -> float:
    """En dis katmanin yaricapi [cm] = TRISO parcacik yaricapi."""
    katmanlar = t.get("katmanlar") or []
    if not katmanlar:
        raise ValueError(_("TRISO parçacığında katman yok"))
    return float(katmanlar[-1]["r"])


def parcacik_hacmi(t: dict) -> float:
    return 4.0 / 3.0 * math.pi * parcacik_yaricap(t) ** 3


def katman_hacimleri(t: dict) -> List[Tuple[dict, float]]:
    """[(katman, tek parcacikta hacim cm3)] icten disa."""
    sonuc, onceki = [], 0.0
    for k in t.get("katmanlar") or []:
        r = float(k["r"])
        sonuc.append((k, 4.0 / 3.0 * math.pi * (r ** 3 - onceki ** 3)))
        onceki = r
    return sonuc


def hedef_sayi(t: dict) -> int:
    """Hedef parcacik sayisi N = int(pf V / V_p) (pack_spheres ile ayni kural)."""
    pf = float(t.get("paketleme") or 0.0)
    return int(pf * konteyner(t).hacim // parcacik_hacmi(t))


def paketleme_orani(t: dict, n: int) -> float:
    """N parcacigin kapta kapladigi hacim orani."""
    return n * parcacik_hacmi(t) / konteyner(t).hacim


def kafes_bolmesi(t: dict) -> Tuple[int, int, int]:
    """create_triso_lattice kafesinin (nx, ny, nz) eleman sayisi: hucre ~ HUCRE_CAP_KATI cap."""
    hucre = HUCRE_CAP_KATI * 2.0 * parcacik_yaricap(t)
    return tuple(max(1, math.ceil(e / hucre)) for e in konteyner(t).kutu)


def kafes_alt_sol(t: dict) -> Tuple[float, float, float]:
    gx, gy, gz = konteyner(t).kutu
    return (-gx / 2.0, -gy / 2.0, -gz / 2.0)


def kafes_adimi(t: dict) -> Tuple[float, float, float]:
    n = kafes_bolmesi(t)
    return tuple(e / k for e, k in zip(konteyner(t).kutu, n))


# ----------------------------------------------------------------------------
# duzenli (basit kubik) yerlesim
# ----------------------------------------------------------------------------

def duzenli_merkezler(kap: Konteyner, r_p: float, adim: float) -> np.ndarray:
    """Basit kubik izgarada kabin icine tam sigan parcacik merkezleri (N x 3).
    Izgara kabin merkezine gore simetriktir; kosul: kompaktta rho <= R - r_p ve
    |z| <= h/2 - r_p, pebblede |c| <= R - r_p."""
    nx = int(kap.kutu[0] / adim) + 1
    nz = int(kap.kutu[2] / adim) + 1
    ix = adim * (np.arange(nx) - (nx - 1) / 2.0)
    iz = adim * (np.arange(nz) - (nz - 1) / 2.0)
    x, y, z = np.meshgrid(ix, ix, iz, indexing="ij")
    if kap.sekil == "pebble":
        ic = np.sqrt(x ** 2 + y ** 2 + z ** 2) <= kap.yaricap - r_p
    else:
        ic = (np.hypot(x, y) <= kap.yaricap - r_p) & (np.abs(z) <= kap.yukseklik / 2.0 - r_p)
    return np.column_stack([x[ic], y[ic], z[ic]])


def duzenli_adim_bul(kap: Konteyner, r_p: float, n_hedef: int) -> float:
    """Merkez sayisi n_hedef'e en yakin olan kubik adim (tarama; esitlikte buyuk adim).
    Alt sinir 2 r_p (parcaciklar ust uste binmez)."""
    pf = n_hedef * 4.0 / 3.0 * math.pi * r_p ** 3 / kap.hacim
    a0 = 2.0 * r_p * (SC_SINIRI / max(pf, 1e-12)) ** (1.0 / 3.0)
    en_iyi, en_iyi_fark = a0, None
    for c in np.linspace(0.85, 1.25, 161):
        a = max(a0 * float(c), 2.0 * r_p)
        fark = abs(len(duzenli_merkezler(kap, r_p, a)) - n_hedef)
        if en_iyi_fark is None or fark < en_iyi_fark or (fark == en_iyi_fark and a > en_iyi):
            en_iyi, en_iyi_fark = a, fark
    return en_iyi


@dataclass(frozen=True)
class Yerlesim:
    """Hesaplanmis yerlesim ozeti (arayuz / dogrulama / rapor)."""
    yontem: str
    n: int
    hedef_pf: float
    gercek_pf: float
    adim: Optional[float]          # duzenli: kubik adim [cm]; rastgele: None


def yerlesim_ozeti(t: dict) -> Yerlesim:
    """Kurulum yapmadan beklenen parcacik sayisi ve gercek paketleme orani."""
    kap, r_p = konteyner(t), parcacik_yaricap(t)
    hedef = float(t.get("paketleme") or 0.0)
    n = hedef_sayi(t)
    if (t.get("yontem") or "rastgele") == "duzenli":
        a = duzenli_adim_bul(kap, r_p, n)
        n = len(duzenli_merkezler(kap, r_p, a))
        return Yerlesim("duzenli", n, hedef, paketleme_orani(t, n), a)
    return Yerlesim("rastgele", n, hedef, paketleme_orani(t, n), None)


# ----------------------------------------------------------------------------
# dogrulama (saf: openmc gerektirmez)
# ----------------------------------------------------------------------------

def sorunlar(t: dict) -> List[Tuple[str, str]]:
    """[(seviye, mesaj)] -- seviye 'hata' | 'uyari'. Tanimin kendi tutarliligi."""
    cikti: List[Tuple[str, str]] = []
    try:
        kap = konteyner(t)
    except ValueError as e:
        return [("hata", str(e))]
    katmanlar = t.get("katmanlar") or []
    if not katmanlar:
        return [("hata", _("TRISO parçacığında katman yok"))]
    onceki = 0.0
    for i, k in enumerate(katmanlar):
        try:
            r = float(k.get("r"))
        except (TypeError, ValueError):
            cikti.append(("hata", _("katman %d: yarıçap sayı olmalı") % (i + 1)))
            return cikti
        if not r > onceki:
            cikti.append(("hata", _("katman %d: yarıçap (%g cm) bir içtekinden (%g) büyük "
                                   "olmalı") % (i + 1, r, onceki)))
        if not k.get("malzeme"):
            cikti.append(("hata", _("katman %d: malzeme seçilmemiş") % (i + 1)))
        onceki = r
    cikti += _paketleme_sorunlari(t, kap, onceki)
    cikti += _pebble_sorunlari(t)
    return cikti


def _paketleme_sorunlari(t: dict, kap: Konteyner, r_p: float) -> List[Tuple[str, str]]:
    cikti: List[Tuple[str, str]] = []
    if not t.get("matris_malzeme"):
        cikti.append(("hata", _("matris malzemesi seçilmemiş")))
    yontem = t.get("yontem") or "rastgele"
    if yontem not in YONTEMLER:
        return cikti + [("hata", _("bilinmeyen yerleşim yöntemi: %r") % (yontem,))]
    try:
        pf = float(t.get("paketleme"))
    except (TypeError, ValueError):
        return cikti + [("hata", _("paketleme oranı sayı olmalı"))]
    sinir = SC_SINIRI if yontem == "duzenli" else CRP_SINIRI
    if not 0.0 < pf <= sinir:
        return cikti + [("hata", _("paketleme oranı 0 ile %.4g arasında olmalı (%s yöntemi için "
                                  "üst sınır; girilen %g)") % (sinir, yontem, pf))]
    if 2.0 * r_p >= min(kap.kutu[0], kap.kutu[2]):
        cikti.append(("hata", _("TRISO parçacığı (çap %g cm) kaba sığmıyor") % (2.0 * r_p)))
        return cikti
    if yontem == "rastgele" and pf > RSP_ESIGI:
        cikti.append(("uyari", _("paketleme %.3g > %.2g: yakın rastgele paketleme (CRP) "
                                "kullanılır, kurulum yavaşlar") % (pf, RSP_ESIGI)))
    n = hedef_sayi(t)
    if n < 1:
        cikti.append(("hata", _("bu paketleme oranıyla kaba hiç parçacık sığmıyor")))
    elif n > UYARI_PARCACIK_SAYISI:
        cikti.append(("uyari", _("%d parçacık: model kurulumu ve koşu uzun sürer") % n))
    return cikti


def _pebble_sorunlari(t: dict) -> List[Tuple[str, str]]:
    if (t.get("sekil") or "kompakt") != "pebble":
        return []
    cikti: List[Tuple[str, str]] = []
    try:
        r_dis = float(t.get("dis_yaricap"))
    except (TypeError, ValueError):
        return [("hata", _("'dis_yaricap' sayı olmalı"))]
    if not r_dis > float(t.get("yakit_yaricap") or 0.0):
        cikti.append(("hata", _("pebble dış yarıçapı yakıt bölgesi yarıçapından büyük olmalı")))
    for anahtar, ad in (("kabuk_malzeme", _("kabuk")), ("dis_malzeme", _("dış (gaz)"))):
        if not t.get(anahtar):
            cikti.append(("hata", _("pebble %s malzemesi seçilmemiş") % ad))
    return cikti


def malzemeler(t: dict) -> List[str]:
    """Tanimin basvurdugu malzeme adlari (sirali, tekil)."""
    adlar = [k.get("malzeme") for k in t.get("katmanlar") or []]
    adlar += [t.get("matris_malzeme")]
    if (t.get("sekil") or "kompakt") == "pebble":
        adlar += [t.get("kabuk_malzeme"), t.get("dis_malzeme")]
    gorulen, sonuc = set(), []
    for a in adlar:
        if a and a not in gorulen:
            gorulen.add(a)
            sonuc.append(a)
    return sonuc


# ----------------------------------------------------------------------------
# sablonlar (baslangic degerleri)
# ----------------------------------------------------------------------------

SABLONLAR = {
    # AGR-1 taban parcacigi, UCO cekirdek; kompakt capi 12.45 mm, boyu 25 mm
    "agr1": {
        "sekil": "kompakt",
        "katmanlar": [("kernel", 0.0175), ("buffer", 0.0275), ("ipyc", 0.0315),
                      ("sic", 0.0350), ("opyc", 0.0390)],
        "yaricap": 0.6225, "yukseklik": 2.5, "paketleme": 0.35,
    },
    # HTR-10 pebble'i: UO2 cekirdek, 2.5 cm yakit bolgesi, 3.0 cm dis yaricap
    "htr10": {
        "sekil": "pebble",
        "katmanlar": [("kernel", 0.0250), ("buffer", 0.0340), ("ipyc", 0.0380),
                      ("sic", 0.0415), ("opyc", 0.0455)],
        "yakit_yaricap": 2.5, "dis_yaricap": 3.0, "paketleme": 0.0502,
    },
}
SABLON_ADLARI = {"agr1": "AGR-1 (UCO, kompakt)", "htr10": "HTR-10 (UO2, pebble)"}


def sablon(anahtar: str, ad: str, malzemeler_: dict) -> dict:
    """YENI tanim. malzemeler_: {katman adi | 'matris' | 'kabuk' | 'dis': malzeme adi}."""
    s = SABLONLAR[anahtar]
    t = {"ad": ad, "sekil": s["sekil"], "paketleme": s["paketleme"], "yontem": "rastgele",
         "tohum": VARSAYILAN_TOHUM,
         "katmanlar": [{"ad": k, "r": r, "malzeme": malzemeler_.get(k)}
                       for k, r in s["katmanlar"]],
         "matris_malzeme": malzemeler_.get("matris")}
    for alan in ("yaricap", "yukseklik", "yakit_yaricap", "dis_yaricap"):
        if alan in s:
            t[alan] = s[alan]
    if s["sekil"] == "pebble":
        t["kabuk_malzeme"] = malzemeler_.get("kabuk")
        t["dis_malzeme"] = malzemeler_.get("dis")
    return t
