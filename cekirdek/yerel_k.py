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

 BU BIR k-SONSUZ DEGILDIR: "sizintisiz yerel cogalma orani". Komsu binlerle
 notron alisverisi (net akim) yok sayilir; kor kenarindaki bir demetin yerel
 k'si yuksek gorunur ama sizinti onu kritiklige indirir.

 (n,xn) NEDEN PAYDADA (v3 Y3 bulgusu)
   OpenMC'de "absorption" (n,2n) gibi kanallari notron YOK OLMASI olarak
   saymaz (sacilma sayilir) ve onlarin dogurdugu ek notronlar nu-fission'a
   girmez. Sizintisiz denge: P + X = A  (k = 1)  ->  k = P / (A - X).
   Duzeltme carpani c_xn = A / (A - X) (Y3 dort faktor modulundeki tanimla
   ayni). Duzeltmesiz oran (P/A) de k_xn_siz olarak verilir.
   Kanallar: XN_SKORLARI (MT 11, 16, 17, 24, 25, 30, 37, 41, 42 -- Y3 ile
   ayni liste). Daha yuksek kanallar (MT 152+) yalniz TENDL turu
   degerlendirmelerde vardir; sayilmaz.

 ORTALAMA HANGI AGIRLIKLA k-SONSUZA ESITTIR (turetme)
   Sonsuz kafeste (yansitici sinirli tek pin/demet; sizinti 0) global denge
       k_inf = sum_i P_i / sum_i D_i .
   k_i = P_i / D_i yazilirsa
       k_inf = sum_i D_i k_i / sum_i D_i            (NET YOK OLMA agirlikli
                                                      aritmetik ortalama)
             = sum_i P_i / sum_i (P_i / k_i)         (URETIM agirlikli
                                                      HARMONIK ortalama)
   Hacim agirlikli ya da duz ortalama k_inf'a esit DEGILDIR (pinlerin
   akisi farkli). Yakitsiz binler (kilavuz boru, P=0) toplamaya GIRER:
   onlarin sogurmasi da kafesin notron dengesinin parcasidir.
   Haritanin kapsamadigi bolgeler (kanal kutusu/su araligi, yansitici) icin
   ayrica filtresiz bir "model toplami" tally'si okunur; kapsama orani
   = sum_harita D / D_model. Sonsuz kafeste kapsama 1 ise ortalama = k_inf.

 MESH
   Kare kafesin hatvesine hizali RegularMesh (spec kullanici tally'si olarak:
   kurucu.tallyleri_kur ve kod_uret ayni tanimi kurar -- betik esdegerligi
   kendiliginden). z: 3B'de model yuksekligi (+-h/2, kurucu ile ayni
   varsayim), 2B'de sinirsiz (+-SONSUZ_Z). Altigen kafes ve demetler arasi
   bosluklu kor (BEAVRS: demet adimi != pin sayisi x pin adimi) pin duzeyinde
   desteklenmez -- RegularMesh hizalanamaz; acik hatayla reddedilir.

 BELIRSIZLIK (birinci derece, KORELASYON YOK SAYILIR -- etiketlenir)
   (s_k/k)^2 = (s_P/P)^2 + (s_D/D)^2 ;  s_D^2 = s_A^2 + sum (x-1)^2 s_x^2.
   Ayni bindeki P ile A pozitif korelelidir (ikisi de ayni akiya bagli); bunu
   yok saymak oranin sigmasini BUYUK tahmin eder (ihtiyatli). Ote yandan bin
   sigmalari cevrimler arasi korelasyonu gormez (cekirdek/guc.py notu):
   tek kosunun sigmasi bir alt sinirdir. Gercek belirsizlik coklu tohumla.
================================================================================
"""

from __future__ import annotations

import copy
import csv
import io
import math
import sys
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Tuple

from cekirdek import sema
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

DUZEYLER = ("pin", "demet")
TALLY_ADLARI = {"pin": "yerel_k_pin", "demet": "yerel_k_demet"}
TOPLAM_TALLY = "yerel_k_toplam"
# 2B modelde eksenel sinir yok: mesh z'de "sonsuz" (entropi mesh'inin eski
# 2B degeriyle ayni buyukluk; tracklength icin tek bin).
SONSUZ_Z = 1.0e10
_ADIM_TOL = 1e-6                   # bagil; demet adimi = n x pin adimi denetimi

# (spec skoru, DataFrame'deki adi, net ek notron x-1). Adi dogrula.referans
# BILINEN_SKORLAR'da olmayan kanallar MT numarasiyla yazilir (OpenMC kabul
# eder, DataFrame'de tepki adiyla doner; test: openmc.data.REACTION_NAME).
XN_SKORLARI = (("(n,2n)", "(n,2n)", 1), ("(n,3n)", "(n,3n)", 2), ("(n,4n)", "(n,4n)", 3),
               ("11", "(n,2nd)", 1), ("24", "(n,2na)", 1), ("25", "(n,3na)", 2),
               ("30", "(n,2n2a)", 1), ("41", "(n,2np)", 1), ("42", "(n,3np)", 2))
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
class YerelKSonucu:
    duzey: str
    boyut: Tuple[int, int]
    adim: Tuple[float, float]
    hucreler: Tuple[YerelK, ...]
    ortalama: Deger                     # sum P / sum D (net yok olma agirlikli)
    c_xn: float                         # sum A / sum D (harita)
    model_toplami: Optional[Deger] = None
    kapsama: Optional[float] = None     # sum_harita D / D_model
    keff: Optional[Deger] = None        # kosunun k-eff'i (karsilastirma icin)


# ============================================================================
# 1. KAFES DUZENI (mesh hizalama)
# ============================================================================

def _ic_dugum(kok: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
    """Kok kabin icerigi; eksenel katmanlama aktif katmanin icerigine acilir."""
    dugum = kok.get("ic")
    while isinstance(dugum, dict) and dugum.get("tur") == "eksenel":
        dugum = dugum.get("icerik")
    return dugum if isinstance(dugum, dict) else None


def _kare_demet(spec: Mapping[str, Any], ad: str) -> dict:
    d = sema.demet_bul(spec, ad)
    if d is None:
        raise YerelKHatasi(_("'%s' bir demet değil; yerel k için kare demet gerekir") % ad)
    if d.get("tur") != "kare":
        raise YerelKHatasi(_("'%s' altıgen demet: yerel k haritası yalnız kare kafeste "
                             "kurulabilir (altıgen mesh OpenMC'de yok)") % ad)
    return d


def _z_siniri(spec: Mapping[str, Any]) -> Tuple[float, float]:
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
    """Kor kafesindeki demetlerin ortak (boyut, pin adimi); hizalanamazsa hata."""
    demetler = {v.get("ad") for v in (kafes.get("anahtar") or {}).values()
                if isinstance(v, dict) and v.get("tur") == "bilesen"}
    if not demetler:
        raise YerelKHatasi(_("kor kafesinde demet yok: pin düzeyi kurulamaz"))
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


def kafes_duzeni(spec: Mapping[str, Any], duzey: str) -> KafesDuzeni:
    """Spec'in kare kafesine hizali mesh duzeni. Desteklenmeyen durumda YerelKHatasi."""
    if duzey not in DUZEYLER:
        raise YerelKHatasi(_("bilinmeyen yerel k düzeyi: %s") % duzey)
    from cekirdek import geometri
    kok = geometri.model(spec).kok
    sekil = (kok.get("kesit") or {}).get("sekil")
    if sekil == "altigen":
        raise YerelKHatasi(_("altıgen kesitli model: yerel k haritası yalnız kare kafeste "
                             "kurulabilir (altıgen mesh OpenMC'de yok)"))
    if sekil not in ("dikdortgen", None):
        raise YerelKHatasi(_("yerel k haritası yalnız kare kafeste kurulabilir"))
    dugum = _ic_dugum(kok)
    z = _z_siniri(spec)
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


# ============================================================================
# 2. TALLY TANIMI (spec kullanici tally'si)
# ============================================================================

def tally_tanimi(spec: Mapping[str, Any], duzey: str) -> dict:
    """Yerel k mesh tally'sinin spec tanimi (yeni sozluk)."""
    d = kafes_duzeni(spec, duzey)
    return {"ad": TALLY_ADLARI[duzey], "skorlar": list(SKORLAR), "nuklidler": [],
            "filtreler": [{"tur": "mesh", "boyut": [d.boyut[0], d.boyut[1], 1],
                           "otomatik": False, "alt": list(d.alt), "ust": list(d.ust)}]}


def _toplam_tanimi() -> dict:
    return {"ad": TOPLAM_TALLY, "skorlar": list(SKORLAR), "nuklidler": [], "filtreler": []}


def tally_ekle(spec: Mapping[str, Any], duzey: str) -> dict:
    """Yerel k tally'si (+ model toplami) eklenmis YENI spec; ayni adli eskisi
    degistirilir. Girdi degismez."""
    tanim = tally_tanimi(spec, duzey)
    yeni = copy.deepcopy(dict(spec))
    kalan = [t for t in yeni.get("tallyler") or []
             if t.get("ad") not in (tanim["ad"], TOPLAM_TALLY)]
    yeni["tallyler"] = kalan + [tanim, _toplam_tanimi()]
    return yeni


def tally_kaldir(spec: Mapping[str, Any]) -> dict:
    """Butun yerel k tally'leri cikarilmis YENI spec."""
    adlar = set(TALLY_ADLARI.values()) | {TOPLAM_TALLY}
    yeni = copy.deepcopy(dict(spec))
    yeni["tallyler"] = [t for t in yeni.get("tallyler") or [] if t.get("ad") not in adlar]
    return yeni


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
    if D[0] <= 0.0 or P[0] <= 0.0:
        return (0.0 if D[0] > 0.0 else math.nan, 0.0)
    k = P[0] / D[0]
    return k, k * math.hypot(P[1] / P[0], D[1] / D[0])


def _bin_skorlari(df: Any) -> dict:
    xs, ys = _mesh_sutunlari(df)
    skor, ort, sap = _sutun(df, "score"), _sutun(df, "mean"), _sutun(df, "std. dev.")
    binler: dict = {}
    for x, y, s, o, d in zip(xs, ys, skor, ort, sap):
        b = binler.setdefault((int(x) - 1, int(y) - 1), {})
        eski = b.get(s, (0.0, 0.0))                      # z dilimleri toplanir
        b[s] = (eski[0] + float(o), math.hypot(eski[1], float(d)))
    return binler


def _duz_skorlar(df: Any) -> dict:
    sk = {}
    for s, o, d in zip(_sutun(df, "score"), _sutun(df, "mean"), _sutun(df, "std. dev.")):
        eski = sk.get(s, (0.0, 0.0))
        sk[s] = (eski[0] + float(o), math.hypot(eski[1], float(d)))
    return sk


def _hucre(konum: Tuple[int, int], skorlar: Mapping[str, Deger]) -> YerelK:
    P, A, D = _toplamlar(skorlar)
    k, s = _oran(P, D)
    return YerelK(konum, k, s, P[0] / A[0] if A[0] > 0 else math.nan, P, D, P[0] > 0.0)


def _topla(degerler: Sequence[Deger]) -> Deger:
    return (sum(d[0] for d in degerler), math.sqrt(sum(d[1] ** 2 for d in degerler)))


def hesapla(df: Any, duzey: str, boyut: Sequence[int], adim: Sequence[float],
            toplam_df: Any = None, keff: Optional[Deger] = None) -> YerelKSonucu:
    """Mesh tally DataFrame'inden (OpenMC bicimi) yerel k sonucu."""
    binler = _bin_skorlari(df)
    hucreler = tuple(_hucre(k, binler[k]) for k in sorted(binler, key=lambda a: (a[1], a[0])))
    P = _topla([h.uretim for h in hucreler])
    D = _topla([h.yok_olma for h in hucreler])
    A = sum(_toplamlar(binler[h.konum])[1][0] for h in hucreler)
    model, kapsama = None, None
    if toplam_df is not None:
        Pm, _Am, Dm = _toplamlar(_duz_skorlar(toplam_df))
        model = _oran(Pm, Dm)
        kapsama = D[0] / Dm[0] if Dm[0] > 0 else None
    return YerelKSonucu(duzey, (int(boyut[0]), int(boyut[1])), (float(adim[0]), float(adim[1])),
                        hucreler, _oran(P, D), A / D[0] if D[0] > 0 else math.nan,
                        model, kapsama, tuple(keff) if keff else None)


def sonuctan(sonuc: Mapping[str, Any], spec: Mapping[str, Any]) -> list:
    """kosucu.sonuc_oku ciktisindaki yerel k tally'leri -> [YerelKSonucu]
    (duzey sirasiyla; yoksa bos liste). Okunamayan tally YerelKHatasi."""
    taller = (sonuc or {}).get("tallyler") or {}
    toplam = taller.get(TOPLAM_TALLY)
    if isinstance(toplam, str):
        toplam = None                    # okunamadi: kapsama verilmez (loga yazildi)
    cikti = []
    for duzey in DUZEYLER:
        df = taller.get(TALLY_ADLARI[duzey])
        if df is None:
            continue
        if isinstance(df, str):
            raise YerelKHatasi(df)
        d = kafes_duzeni(spec, duzey)
        cikti.append(hesapla(df, duzey, d.boyut, d.adim, toplam_df=toplam,
                             keff=(sonuc or {}).get("keff")))
    return cikti


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
#   python -m cekirdek.yerel_k ekle model.json pin|demet -o yeni.json
#   python -m cekirdek.yerel_k oku statepoint.h5 model.json [--csv yol]
# ============================================================================

def _ozet_satiri(s: YerelKSonucu) -> str:
    parca = ["%s: %s = %.5f +- %.5f" % (s.duzey, _("ortalama k"), *s.ortalama),
             "c_xn = %.5f" % s.c_xn]
    if s.keff:
        parca.append("k-eff = %.5f +- %.5f" % tuple(s.keff))
    if s.kapsama is not None:
        parca.append("%s = %.4f" % (_("kapsam"), s.kapsama))
    return " | ".join(parca)


def _oku(sp: str, model: str, csv_yolu: Optional[str]) -> None:
    from cekirdek import kosucu
    sonuclar = sonuctan(kosucu.sonuc_oku(sp), sema.yukle(model))
    if not sonuclar:
        raise YerelKHatasi(_("bu koşuda yerel k tally'si yok"))
    for s in sonuclar:
        sys.stdout.write(_ozet_satiri(s) + "\n")
    if csv_yolu:
        with open(csv_yolu, "w", encoding="utf-8", newline="") as f:
            f.write(csv_metni(sonuclar[0]))


def terminal(argv: Sequence[str]) -> int:
    """Komut satiri; DONER cikis kodu (0 tamam, 1 hata)."""
    import argparse
    ap = argparse.ArgumentParser(prog="python -m cekirdek.yerel_k")
    alt = ap.add_subparsers(dest="komut", required=True)
    e = alt.add_parser("ekle")
    e.add_argument("model")
    e.add_argument("duzey", choices=DUZEYLER)
    e.add_argument("-o", "--cikti", required=True)
    o = alt.add_parser("oku")
    o.add_argument("statepoint")
    o.add_argument("model")
    o.add_argument("--csv")
    a = ap.parse_args(list(argv))
    try:
        if a.komut == "ekle":
            sema.kaydet(tally_ekle(sema.yukle(a.model), a.duzey), a.cikti)
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
