# -*- coding: utf-8 -*-
"""
================================================================================
 yerel_k.py  --  Pin / demet bazli YEREL k (v3 K4)
================================================================================

 Tanim (her mesh bini i icin; bin = bir pin hucresi ya da bir demet):

     k_i = P_i / D_i ,   P_i = nu-Sigma_f phi  (nu-fission)
                         D_i = A_i - X_i       (net yok olma)
     A_i = Sigma_a phi   (OpenMC "absorption")
     X_i = sum_x (x-1) R_x,i   (n,xn) tepkimelerinin NET notron uretimi

 BU BIR k-SONSUZ DEGILDIR: "yerel uretim / yok olma orani" -- sizinti ve net
 akim terimi icermez. Binin akisi komsulardan gelen notronlari ICERIR (P ve D
 o akiyla hesaplanir); tanima girmeyen, binin sinirlarindaki NET akimdir.
 Yerel P/D'yi bindeki spektrum belirler: bir ic demetin k_i'si, kor ici
 spektrumdaki k-sonsuzuna yakindir. Kritiklik GLOBALDIR:
     k_eff = sum P / (sum D + L) = k_harita (1 - l),  l = L / (sum D + L)
 (L: sizinti; Duderstadt & Hamilton, Nuclear Reactor Analysis, 1976, bol. 5).

 (n,xn) NEDEN PAYDADA (v3 Y3 bulgusu)
   OpenMC'de "absorption" (n,2n) gibi kanallari notron YOK OLMASI olarak
   saymaz (sacilma sayilir) ve onlarin dogurdugu ek notronlar nu-fission'a
   girmez. Sizintisiz denge: P + X = A  (k = 1)  ->  k = P / (A - X).
   Duzeltme carpani c_xn = A / (A - X). Kanallar ve (x-1) carpanlari TEK
   kaynaktan: cekirdek/spektrum.XN_SKORLARI (Y3 dort faktor).

 ORTALAMA HANGI AGIRLIKLA k-SONSUZA ESITTIR (turetme)
   Sonsuz kafeste (yansitici sinirli tek pin/demet; L = 0) global denge
       k_inf = sum_i P_i / sum_i D_i .
   k_i = P_i / D_i yazilirsa
       k_inf = sum_i D_i k_i / sum_i D_i       (NET YOK OLMA agirlikli aritmetik)
   Uretim agirlikli HARMONIK ortalama ancak butun binler fisilse esdegerdir;
   P = 0 binlerin (kilavuz boru) D'si paydaya AYRICA eklenir:
       1 / k_inf = [ sum_{P>0} P_i / k_i + sum_{P=0} D_i ] / sum_i P_i .
   Duz ya da hacim agirlikli ortalama k_inf'a esit DEGILDIR.
   Filtresiz "model toplami" tally'si haritanin kapsamini olcer:
   kapsama = sum_harita D / D_model (kanal kutusu, su araligi, yansitici
   disarida kalirsa < 1).

 BEKLENEN ESITLIKLER (kabul testinin dayandigi, kaynak notronu basina)
   sum P_model  = global k-tracklength (AYNI tahminci; birebir)
   D_model + L  = 1 (beklenen deger; tracklength A tahminidir, istatistikle
                  sapar). Bu yuzden k_harita = k_tl / D_model, kosunun
                  birlesik k-eff'inden D_model'in sapmasi kadar ayrilir;
                  ikisi KORELASYONLU iki tahmindir (ayni gecmisler).

 MESH
   Kare kafesin hatvesine hizali RegularMesh (spec kullanici tally'si olarak:
   kurucu.tallyleri_kur ve kod_uret ayni tanimi kurar -- betik esdegerligi
   kendiliginden). z: "model" (3B'de +-h/2, eksenel yansitici DAHIL; 2B'de
   sinirsiz) ya da "aktif" (yalniz fisil eksenel aralik; kapsama < 1 olur).
   Altigen kafes, donusumlu kafes ve demetler arasi bosluklu kor (BEAVRS)
   pin duzeyinde desteklenmez -- acik hatayla reddedilir.

 BELIRSIZLIK (birinci derece, KORELASYON YOK SAYILIR -- etiketlenir)
   (s_k/k)^2 = (s_P/P)^2 + (s_D/D)^2 ;  s_D^2 = s_A^2 + sum (x-1)^2 s_x^2.
   Ayni bindeki P ile A pozitif korelelidir; bunu yok saymak oranin sigmasini
   BUYUK tahmin eder (ihtiyatli). Harita ortalamasinin sigmasi kapsama 1 iken
   filtresiz tally'den alinir (binler arasi korelasyonu da icerir); degilse
   bin sigmalarinin karesel toplamidir (binler arasi korelasyon da yok
   sayilir). Bin sigmalari cevrimler arasi korelasyonu gormez (iyimser).
================================================================================
"""

from __future__ import annotations

import csv
import io
import math
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from cekirdek import sema
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from cekirdek.spektrum import XN_SKORLARI as _XN

_log = kaydedici(__name__)

DUZEYLER = ("pin", "demet")
Z_KAPSAMLARI = ("model", "aktif")
TALLY_ADLARI = {"pin": "yerel_k_pin", "demet": "yerel_k_demet"}
TOPLAM_TALLY = "yerel_k_toplam"
URETICI = "yerel_k"               # tally sozlugundeki isaret: bu modul uretti
# 2B modelde eksenel sinir yok: mesh z'de "sonsuz" (tracklength icin tek bin).
SONSUZ_Z = 1.0e10
_ADIM_TOL = 1e-6                   # bagil; demet adimi = n x pin adimi denetimi
_KAPSAMA_TOL = 1e-9                # kapsama 1 sayilir (harita = model)
_CSV_FORMUL = ("=", "+", "-", "@", "\t", "\r")   # elektronik tablo formul oneki


def _spec_skoru(ad: str) -> str:
    """dogrula.referans'ta bilinmeyen tepki adi MT numarasiyla yazilir (OpenMC
    kabul eder, DataFrame'de tepki adiyla doner)."""
    from cekirdek.dogrula.referans import BILINEN_SKORLAR
    if ad in BILINEN_SKORLAR:
        return ad
    import openmc.data
    return str(openmc.data.REACTION_MT[ad])


# (spec skoru, DataFrame'deki adi, net ek notron x-1) -- spektrum ile ayni kanallar
XN_SKORLARI = tuple((_spec_skoru(ad), ad, fazla) for ad, fazla in _XN)
SKORLAR = ("nu-fission", "absorption") + tuple(s for s, _a, _x in XN_SKORLARI)

Deger = Tuple[float, float]        # (ortalama, 1 sigma)


class YerelKHatasi(ValueError):
    """Yerel k bu modelde kurulamaz/okunamaz; mesaj kullaniciya gosterilir."""


@dataclass(frozen=True)
class KafesDuzeni:
    """Hatveye hizali mesh: boyut (nx, ny), adim (px, py), alt/ust (x, y, z)."""
    duzey: str
    boyut: Tuple[int, int]
    adim: Tuple[float, float]
    alt: Tuple[float, float, float]
    ust: Tuple[float, float, float]


@dataclass(frozen=True)
class YerelK:
    """Bir binin yerel k'si. konum: (x, y) 0 tabanli, soldan/alttan."""
    konum: Tuple[int, int]
    k: float
    sigma: float
    k_xn_siz: float
    uretim: Deger
    yok_olma: Deger
    fisil: bool


@dataclass(frozen=True)
class Denge:
    """Statepoint'in global notron dengesi (kaynak notronu basina)."""
    k_izyolu: Deger                     # global k-tracklength
    sizinti: Deger                      # global leakage


@dataclass(frozen=True)
class YerelKSonucu:
    duzey: str
    boyut: Tuple[int, int]
    adim: Tuple[float, float]
    hucreler: Tuple[YerelK, ...]
    ortalama: Deger                     # sum P / sum D (net yok olma agirlikli)
    c_xn: float                         # sum A / sum D (harita)
    model_toplami: Optional[Deger] = None     # P_model / D_model
    kapsama: Optional[float] = None           # sum_harita D / D_model
    keff: Optional[Deger] = None              # kosunun birlesik k-eff'i
    model_uretim: Optional[Deger] = None      # P_model
    model_yok_olma: Optional[Deger] = None    # D_model
    denge: Optional[Denge] = None

    @property
    def sizintili_k(self) -> Optional[float]:
        """P_model / (D_model + L) -- kritiklik denetimi (k-eff ile karsilastirilir)."""
        if not (self.denge and self.model_uretim and self.model_yok_olma):
            return None
        payda = self.model_yok_olma[0] + self.denge.sizinti[0]
        return self.model_uretim[0] / payda if payda > 0 else None


# ============================================================================
# 1. KAFES DUZENI (mesh hizalama)
# ============================================================================

def _ic_dugum(kok: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    """Kok kabin icerigi; eksenel katmanlama aktif katmanin icerigine acilir.
    Donusumlu (otelenmis/dondurulmus) icerik hizalanamaz: hata."""
    dugum = kok.get("ic")
    while isinstance(dugum, dict) and dugum.get("tur") == "eksenel":
        if dugum.get("donusum"):
            break
        dugum = dugum.get("icerik")
    if isinstance(dugum, dict) and dugum.get("donusum"):
        raise YerelKHatasi(_("kafes ötelenmiş ya da döndürülmüş: yerel k mesh'i "
                             "hizalanamaz"))
    return dugum if isinstance(dugum, dict) else None


def _kare_demet(spec: Mapping[str, Any], ad: str) -> dict:
    d = sema.demet_bul(spec, ad)
    if d is None:
        raise YerelKHatasi(_("'%s' bir demet değil; yerel k için kare demet gerekir") % ad)
    if d.get("tur") != "kare":
        raise YerelKHatasi(_("'%s' altıgen demet: yerel k haritası yalnız kare kafeste "
                             "kurulabilir (altıgen mesh OpenMC'de yok)") % ad)
    return d


def _z_siniri(spec: Mapping[str, Any], z_kapsam: str) -> Tuple[float, float]:
    if z_kapsam not in Z_KAPSAMLARI:
        raise YerelKHatasi(_("bilinmeyen eksenel kapsam: %s") % z_kapsam)
    if z_kapsam == "aktif":
        from cekirdek import geometri
        aralik = geometri.aktif_aralik(spec)
        if aralik:
            return float(aralik[0]), float(aralik[1])
    h = sema.model_yuksekligi(spec)
    return (-h / 2.0, h / 2.0) if h else (-SONSUZ_Z, SONSUZ_Z)


def _duzen(duzey: str, n: Sequence[int], p: Sequence[float], z: Tuple[float, float]
           ) -> KafesDuzeni:
    nx, ny = int(n[0]), int(n[1])
    px, py = float(p[0]), float(p[1])
    return KafesDuzeni(duzey, (nx, ny), (px, py), (-px * nx / 2.0, -py * ny / 2.0, z[0]),
                       (px * nx / 2.0, py * ny / 2.0, z[1]))


def _bilesen_duzeni(spec: Mapping[str, Any], dugum: Mapping[str, Any], kok: Mapping[str, Any],
                    duzey: str, z: Tuple[float, float]) -> KafesDuzeni:
    ad = dugum.get("ad")
    if sema.cubuk_bul(spec, ad) is not None:
        kesit = kok.get("kesit") or {}
        if kesit.get("sekil") != "dikdortgen":
            raise YerelKHatasi(_("tek pin modelinde kare hücre gerekir"))
        return _duzen(duzey, (1, 1), kesit["boyut"], z)
    d = _kare_demet(spec, ad)
    n, p = d["boyut"], float(d["adim"])
    if duzey == "pin":
        return _duzen(duzey, n, (p, p), z)
    return _duzen(duzey, (1, 1), (p * n[0], p * n[1]), z)


def _kor_pin_adimi(spec: Mapping[str, Any], kafes: Mapping[str, Any]
                   ) -> Tuple[Sequence[int], float]:
    """Kor kafesindeki demetlerin ortak (boyut, pin adimi); hizalanamazsa hata.
    Demet disi hucreler (su, yansitici) mesh'te ayni hatveyle kalir."""
    bilesenler = {v.get("ad") for v in (kafes.get("anahtar") or {}).values()
                  if isinstance(v, dict) and v.get("tur") == "bilesen"}
    demetler = {ad for ad in bilesenler if sema.demet_bul(spec, ad) is not None}
    if not demetler:
        raise YerelKHatasi(_("kor kafesinde demet yok (%s): pin düzeyi kurulamaz; demet "
                             "düzeyini kullanın") % (", ".join(sorted(bilesenler)) or "—"))
    if bilesenler - demetler:
        raise YerelKHatasi(_("kor kafesinde demet olmayan parça var (%s): pin düzeyi tek "
                             "mesh'e hizalanamaz; demet düzeyini kullanın")
                           % ", ".join(sorted(bilesenler - demetler)))
    olculer = set()
    for ad in sorted(demetler):
        d = _kare_demet(spec, ad)
        olculer.add((tuple(d["boyut"]), float(d["adim"])))
    if len(olculer) != 1:
        raise YerelKHatasi(_("kordaki demetlerin pin adımı/boyutu farklı: pin düzeyi tek "
                             "mesh'e hizalanamaz; demet düzeyini kullanın"))
    (n, p), = olculer
    P = float(kafes["adim"])
    if abs(n[0] * p - P) > _ADIM_TOL * P or abs(n[1] * p - P) > _ADIM_TOL * P:
        raise YerelKHatasi(
            _("demet adımı (%.5g cm) pin sayısı × pin adımına (%d × %.5g cm) eşit değil "
              "(demetler arası boşluk): pin düzeyi mesh'e hizalanamaz; demet düzeyini "
              "kullanın") % (P, n[0], p))
    return n, p


def _kafes_duzeni(spec: Mapping[str, Any], duzey: str, z_kapsam: str) -> KafesDuzeni:
    from cekirdek import geometri
    kok = geometri.model(spec).kok
    sekil = (kok.get("kesit") or {}).get("sekil")
    if sekil == "altigen":
        raise YerelKHatasi(_("altıgen kesitli model: yerel k haritası yalnız kare kafeste "
                             "kurulabilir (altıgen mesh OpenMC'de yok)"))
    if sekil not in ("dikdortgen", None):
        raise YerelKHatasi(_("yerel k haritası yalnız kare kafeste kurulabilir"))
    dugum = _ic_dugum(kok)
    z = _z_siniri(spec, z_kapsam)
    tur = (dugum or {}).get("tur")
    if tur == "bilesen":
        return _bilesen_duzeni(spec, dugum, kok, duzey, z)
    if tur == "kafes" and dugum.get("sekil") == "kare":
        if duzey == "demet":
            P = float(dugum["adim"])
            return _duzen(duzey, dugum["boyut"], (P, P), z)
        n, p = _kor_pin_adimi(spec, dugum)
        N = dugum["boyut"]
        return _duzen(duzey, (N[0] * n[0], N[1] * n[1]), (p, p), z)
    raise YerelKHatasi(_("bu geometride (%s) pin/demet kafesi bulunamadı; yerel k "
                         "haritası kare kafesli modellerde kurulur") % (tur or "?"))


def kafes_duzeni(spec: Mapping[str, Any], duzey: str, z_kapsam: str = "model") -> KafesDuzeni:
    """Spec'in kare kafesine hizali mesh duzeni. Desteklenmeyen durumda YerelKHatasi."""
    if duzey not in DUZEYLER:
        raise YerelKHatasi(_("bilinmeyen yerel k düzeyi: %s") % duzey)
    try:
        return _kafes_duzeni(spec, duzey, z_kapsam)
    except YerelKHatasi:
        raise
    except (KeyError, TypeError, IndexError, ValueError) as e:
        _log.warning("yerel k kafes düzeni kurulamadı", exc_info=True)
        raise YerelKHatasi(_("modelin kafes tanımı okunamadı: %s") % e) from e


# ============================================================================
# 2. TALLY TANIMI (spec kullanici tally'si)
# ============================================================================

def tally_tanimi(spec: Mapping[str, Any], duzey: str, z_kapsam: str = "model") -> dict:
    """Yerel k mesh tally'sinin spec tanimi (yeni sozluk)."""
    d = kafes_duzeni(spec, duzey, z_kapsam)
    return {"ad": TALLY_ADLARI[duzey], "skorlar": list(SKORLAR), "nuklidler": [],
            "uretici": URETICI,
            "filtreler": [{"tur": "mesh", "boyut": [d.boyut[0], d.boyut[1], 1],
                           "otomatik": False, "alt": list(d.alt), "ust": list(d.ust)}]}


def _toplam_tanimi() -> dict:
    return {"ad": TOPLAM_TALLY, "skorlar": list(SKORLAR), "nuklidler": [], "filtreler": [],
            "uretici": URETICI}


def tally_ekle(spec: Mapping[str, Any], duzey: str, z_kapsam: str = "model") -> dict:
    """Yerel k tally'si (+ model toplami) eklenmis YENI spec (yalniz 'tallyler'
    yeni liste; girdi degismez). Bu modulun urettigi ayni adli tally yerinde
    degistirilir; ayni adli KULLANICI tally'si varsa YerelKHatasi."""
    tanimlar = [tally_tanimi(spec, duzey, z_kapsam), _toplam_tanimi()]
    eski = list(spec.get("tallyler") or [])
    yeni_liste = []
    for t in eski:
        es = next((y for y in tanimlar if y["ad"] == t.get("ad")), None)
        if es is None:
            yeni_liste.append(t)
            continue
        if t.get("uretici") != URETICI:
            raise YerelKHatasi(_("'%s' adlı bir kullanıcı tally'si zaten var; yeniden "
                                 "adlandırın ya da silin") % t.get("ad"))
        yeni_liste.append(es)
        tanimlar.remove(es)
    return dict(spec, tallyler=yeni_liste + tanimlar)


def tally_kaldir(spec: Mapping[str, Any]) -> dict:
    """Bu modulun ekledigi tally'ler cikarilmis YENI spec."""
    return dict(spec, tallyler=[t for t in spec.get("tallyler") or []
                                if t.get("uretici") != URETICI])


def tally_duzeni(spec: Mapping[str, Any], duzey: str) -> Optional[KafesDuzeni]:
    """Spec'te KAYITLI yerel k tally'sinin mesh duzeni (kosudaki mesh); yoksa None."""
    t = next((t for t in spec.get("tallyler") or [] if t.get("ad") == TALLY_ADLARI[duzey]),
             None)
    if t is None:
        return None
    try:
        f = next(f for f in t.get("filtreler") or [] if f.get("tur") == "mesh")
        nx, ny = int(f["boyut"][0]), int(f["boyut"][1])
        alt, ust = [float(v) for v in f["alt"]], [float(v) for v in f["ust"]]
    except (StopIteration, KeyError, TypeError, IndexError, ValueError) as e:
        raise YerelKHatasi(_("'%s' tally'sinin mesh tanımı okunamadı") % t.get("ad")) from e
    adim = ((ust[0] - alt[0]) / nx, (ust[1] - alt[1]) / ny)
    return KafesDuzeni(duzey, (nx, ny), adim, tuple(alt), tuple(ust))


# ============================================================================
# 3. HESAP
# ============================================================================

def _sutun(df: Any, ad: str) -> Any:
    """Duz ya da MultiIndex (('score', '')) sutun."""
    if ad in df.columns:
        return df[ad]
    return df[(ad, "")]


def _mesh_sutunlari(df: Any) -> Tuple[Any, Any]:
    ad = next((c[0] for c in df.columns if isinstance(c, tuple)
               and str(c[0]).startswith("mesh")), None)
    if ad is None:
        raise YerelKHatasi(_("yerel k tally'sinde mesh filtresi yok"))
    return df[(ad, "x")], df[(ad, "y")]


def _toplamlar(skorlar: Mapping[str, Deger]) -> Tuple[Deger, Deger, Deger]:
    """(P, A, D) -- D = A - X; sigmalar karesel toplam (korelasyonsuz)."""
    for gerekli in ("nu-fission", "absorption"):
        if gerekli not in skorlar:
            raise YerelKHatasi(_("yerel k tally'sinde '%s' skoru yok") % gerekli)
    P, A = skorlar["nu-fission"], skorlar["absorption"]
    x_ort, x_var = 0.0, 0.0
    for _s, df_adi, fazla in XN_SKORLARI:
        o, s = skorlar.get(df_adi, (0.0, 0.0))
        x_ort += fazla * o
        x_var += (fazla * s) ** 2
    D = (A[0] - x_ort, math.sqrt(A[1] ** 2 + x_var))
    return P, A, D


def _oran(P: Deger, D: Deger) -> Deger:
    """k = P/D ve korelasyonsuz sigma. D <= 0: tanimsiz (NaN). P <= 0: k = 0,
    sigma = s_P / D (payin belirsizligi)."""
    if D[0] <= 0.0:
        return math.nan, math.nan
    if P[0] <= 0.0:
        return 0.0, P[1] / D[0]
    k = P[0] / D[0]
    return k, k * math.hypot(P[1] / P[0], D[1] / D[0])


def _bin_skorlari(df: Any) -> Dict[Tuple[int, int], Dict[str, Deger]]:
    xs, ys = _mesh_sutunlari(df)
    skor, ort, sap = _sutun(df, "score"), _sutun(df, "mean"), _sutun(df, "std. dev.")
    binler: Dict[Tuple[int, int], Dict[str, Deger]] = {}
    for x, y, s, o, d in zip(xs, ys, skor, ort, sap):
        b = binler.setdefault((int(x) - 1, int(y) - 1), {})
        eski = b.get(s, (0.0, 0.0))                      # z dilimleri toplanir
        b[s] = (eski[0] + float(o), math.hypot(eski[1], float(d)))
    return binler


def _duz_skorlar(df: Any) -> Dict[str, Deger]:
    sk: Dict[str, Deger] = {}
    for s, o, d in zip(_sutun(df, "score"), _sutun(df, "mean"), _sutun(df, "std. dev.")):
        eski = sk.get(s, (0.0, 0.0))
        sk[s] = (eski[0] + float(o), math.hypot(eski[1], float(d)))
    return sk


def _hucre(konum: Tuple[int, int], P: Deger, A: Deger, D: Deger) -> YerelK:
    k, s = _oran(P, D)
    fisil = P[0] > 0.0 and D[0] > 0.0 and math.isfinite(k)
    return YerelK(konum, k, s, P[0] / A[0] if A[0] > 0 else math.nan, P, D, fisil)


def _topla(degerler: Sequence[Deger]) -> Deger:
    return (sum(d[0] for d in degerler), math.sqrt(sum(d[1] ** 2 for d in degerler)))


def _binleri_denetle(binler: Mapping[Tuple[int, int], Any], boyut: Sequence[int]) -> None:
    nx, ny = int(boyut[0]), int(boyut[1])
    if len(binler) != nx * ny or any(not (0 <= x < nx and 0 <= y < ny) for x, y in binler):
        raise YerelKHatasi(_("yerel k tally'si %d×%d mesh'le uyuşmuyor (%d bin); model "
                             "koşudan sonra değişmiş olabilir — yeniden koşun")
                           % (nx, ny, len(binler)))


def hesapla(df: Any, duzey: str, boyut: Sequence[int], adim: Sequence[float],
            toplam_df: Any = None, keff: Optional[Deger] = None,
            denge: Optional[Denge] = None) -> YerelKSonucu:
    """Mesh tally DataFrame'inden (OpenMC bicimi) yerel k sonucu."""
    binler = _bin_skorlari(df)
    _binleri_denetle(binler, boyut)
    sirali = sorted(binler, key=lambda a: (a[1], a[0]))
    uclu = {k: _toplamlar(binler[k]) for k in sirali}
    hucreler = tuple(_hucre(k, *uclu[k]) for k in sirali)
    P = _topla([uclu[k][0] for k in sirali])
    D = _topla([uclu[k][2] for k in sirali])
    A = sum(uclu[k][1][0] for k in sirali)
    ortalama = _oran(P, D)
    model, kapsama, Pm, Dm = None, None, None, None
    if toplam_df is not None:
        Pm, _Am, Dm = _toplamlar(_duz_skorlar(toplam_df))
        model = _oran(Pm, Dm)
        kapsama = D[0] / Dm[0] if Dm[0] > 0 else None
        if kapsama is not None and abs(kapsama - 1.0) < _KAPSAMA_TOL:
            ortalama = (ortalama[0], model[1])      # binler arasi korelasyon dahil
    return YerelKSonucu(duzey, (int(boyut[0]), int(boyut[1])), (float(adim[0]), float(adim[1])),
                        hucreler, ortalama, A / D[0] if D[0] > 0 else math.nan,
                        model, kapsama, tuple(keff) if keff else None, Pm, Dm, denge)


def denge_oku(statepoint_yolu: str) -> Denge:
    """Global k-tracklength ve sizinti (statepoint'in global tally'leri)."""
    import openmc
    with openmc.StatePoint(statepoint_yolu) as sp:
        g = {(r["name"].decode() if isinstance(r["name"], bytes) else str(r["name"])):
             (float(r["mean"]), float(r["std_dev"])) for r in sp.global_tallies}
    if "k-tracklength" not in g or "leakage" not in g:
        raise YerelKHatasi(_("statepoint'te global k-tracklength/leakage yok"))
    return Denge(g["k-tracklength"], g["leakage"])


def sonuctan(sonuc: Mapping[str, Any], spec: Mapping[str, Any],
             denge: Optional[Denge] = None) -> List[YerelKSonucu]:
    """kosucu.sonuc_oku ciktisindaki yerel k tally'leri -> [YerelKSonucu]
    (duzey sirasiyla; yoksa bos liste). Mesh olcusu spec'te KAYITLI tally
    tanimindan okunur (kosudaki mesh). Okunamayan tally YerelKHatasi."""
    taller = (sonuc or {}).get("tallyler") or {}
    toplam = taller.get(TOPLAM_TALLY)
    if isinstance(toplam, str):
        _log.warning("yerel k model toplamı okunamadı: %s", toplam)
        toplam = None
    cikti = []
    for duzey in DUZEYLER:
        df = taller.get(TALLY_ADLARI[duzey])
        if df is None:
            continue
        if isinstance(df, str):
            raise YerelKHatasi(df)
        d = tally_duzeni(spec, duzey)
        if d is None:
            raise YerelKHatasi(_("modelde '%s' tally tanımı yok; koşunun modeliyle açın")
                               % TALLY_ADLARI[duzey])
        cikti.append(hesapla(df, duzey, d.boyut, d.adim, toplam_df=toplam,
                             keff=(sonuc or {}).get("keff"), denge=denge))
    return cikti


def _hucre_metni(deger: Any) -> str:
    """CSV hucresi: formul onekiyle baslayan metin tirnakla etkisizlestirilir."""
    metin = str(deger)
    return "'" + metin if metin.startswith(_CSV_FORMUL) else metin


def csv_metni(s: YerelKSonucu) -> str:
    """Bin basina bir satir: x, y (1 tabanli), k, sigma, k (xn duzeltmesiz), P, D."""
    tampon = io.StringIO()
    yazici = csv.writer(tampon, lineterminator="\n")
    yazici.writerow(["x", "y", "k_yerel", "sigma", "k_yerel_xn_duzeltmesiz",
                     "nu_fission", "net_yok_olma", "fisil"])
    for h in s.hucreler:
        yazici.writerow([h.konum[0] + 1, h.konum[1] + 1, "%.6f" % h.k, "%.6f" % h.sigma,
                         "%.6f" % h.k_xn_siz, "%.6e" % h.uretim[0], "%.6e" % h.yok_olma[0],
                         int(h.fisil)])
    return tampon.getvalue()


# ============================================================================
# 4. TERMINAL
#   python -m cekirdek.yerel_k ekle model.json pin|demet -o yeni.json [--z aktif]
#   python -m cekirdek.yerel_k oku statepoint.h5 model.json [--csv yol]
# ============================================================================

def ozet_satiri(s: YerelKSonucu) -> str:
    """Tek satir ozet (terminal ve gunluk)."""
    parca = ["%s: %s = %.5f +- %.5f" % (s.duzey, _("ortalama k"), *s.ortalama),
             "c_xn = %.5f" % s.c_xn]
    if s.keff:
        parca.append("k-eff = %.5f +- %.5f" % tuple(s.keff))
    if s.kapsama is not None:
        parca.append("%s = %.4f" % (_("kapsam"), s.kapsama))
    if s.denge:
        parca.append("k-tracklength = %.5f, L = %.5f" % (s.denge.k_izyolu[0],
                                                       s.denge.sizinti[0]))
    if s.sizintili_k is not None:
        parca.append("P/(D+L) = %.5f" % s.sizintili_k)
    return " | ".join(parca)


def _csv_yolu(taban: str, duzey: str, cok: bool) -> str:
    if not cok:
        return taban
    kok, uzanti = os.path.splitext(taban)
    return "%s_%s%s" % (kok, duzey, uzanti or ".csv")


def _oku(sp: str, model: str, csv_yolu: Optional[str]) -> None:
    from cekirdek import kosucu
    sonuclar = sonuctan(kosucu.sonuc_oku(sp), sema.yukle(model), denge=denge_oku(sp))
    if not sonuclar:
        raise YerelKHatasi(_("bu koşuda yerel k tally'si yok"))
    for s in sonuclar:
        sys.stdout.write(ozet_satiri(s) + "\n")
        if csv_yolu:
            with open(_csv_yolu(csv_yolu, s.duzey, len(sonuclar) > 1), "w",
                      encoding="utf-8", newline="") as f:
                f.write(csv_metni(s))


def _ekle(model: str, duzey: str, cikti: str, z_kapsam: str) -> None:
    if os.path.abspath(model) == os.path.abspath(cikti):
        raise YerelKHatasi(_("çıktı dosyası girdiyle aynı olamaz: %s") % cikti)
    sema.kaydet(tally_ekle(sema.yukle(model), duzey, z_kapsam), cikti)


def terminal(argv: Sequence[str]) -> int:
    """Komut satiri; DONER cikis kodu (0 tamam, 1 hata)."""
    import argparse
    ap = argparse.ArgumentParser(prog="python -m cekirdek.yerel_k")
    alt = ap.add_subparsers(dest="komut", required=True)
    e = alt.add_parser("ekle")
    e.add_argument("model")
    e.add_argument("duzey", choices=DUZEYLER)
    e.add_argument("-o", "--cikti", required=True)
    e.add_argument("--z", choices=Z_KAPSAMLARI, default="model")
    o = alt.add_parser("oku")
    o.add_argument("statepoint")
    o.add_argument("model")
    o.add_argument("--csv")
    a = ap.parse_args(list(argv))
    try:
        if a.komut == "ekle":
            _ekle(a.model, a.duzey, a.cikti, a.z)
        else:
            _oku(a.statepoint, a.model, a.csv)
    except (ValueError, OSError) as h:          # YerelKHatasi, GocHatasi dahil
        _log.warning("yerel k terminal: %s", h)
        sys.stderr.write("%s\n" % h)
        return 1
    return 0


if __name__ == "__main__":
    from cekirdek.ceviri import terminal_dili
    terminal_dili()
    sys.exit(terminal(sys.argv[1:]))
