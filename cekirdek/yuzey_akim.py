# -*- coding: utf-8 -*-
"""
================================================================================
 yuzey_akim.py  --  Y7: yuzey akimi tally'leri, kacak ve kacak spektrumu
================================================================================
 Kullanici tally'sinde (spec["tallyler"][i]["filtreler"]) iki yeni filtre turu:
   {"tur": "yuzey_sinir"}
       Modelin VAKUM sinir yuzeyleri (SurfaceFilter) + "current". Vakum
       yuzeyinden her gecis disariya dogrudur (parcacik oldurulur), OpenMC
       isareti yuzey normaline gore verir (src/tallies/tally_scoring.cpp
       score_surface_tally: wgt * sign(u.n)); bu yuzden yuzey basina |J|
       = o yuzeyden kacak. Toplam = global "leakage" (ayni olaylar).
   {"tur": "yuzey_kutu", "boyut": [nx, ny, nz], "otomatik": true | "alt", "ust"}
       Duzenli agin hucre yuzleri (MeshSurfaceFilter) + "current": her yuz
       icin AYRI giren/cikan kismi akim (OpenMC bin adlari "x-min out",
       "x-min in" ...). Otomatik sinirlar kurucu.tally_mesh_sinirlari ile ayni.
       Esli denge tally'si "y7_denge:<ad>" ayni ag uzerinde (MeshFilter,
       ANALOG tahminci, yalniz notron) absorption, nu-fission, scatter ve
       nu-scatter skorlarini toplar (notron kaynaginda).
 Her iki tur EnergyFilter ile birlesirse enerji gruplu akim: kacak spektrumu.
 Akim KAYNAK PARCACIGINA suzulur (ParticleFilter): foton tasinimi acikken
 fotonlar notron akimina karismaz (score_surface_tally parcacik ayirmaz).
 Baska filtre (malzeme, mesh) bir yuzey tally'sine konamaz (dogrula/yuzey.py).

 KORUNUM (notron dengesi, kutunun dis yuzleri; ic yuzler birbirini goturur)
     S + J_giren - J_cikan + U = A
   S: kutudaki kaynak -- sabit kaynakta kutu icindeki nokta kaynagin SIDDETI
      (OpenMC sabit kaynak tally'lerini kaynak siddetiyle carpar; olculdu),
      ozdegerde nu-fission_kutu / k-eff (kaynak = fisyon notronlari / k).
   U: sacilmada net notron uretimi  nu-scatter - scatter  ((n,xn) VE kesirli
      verimli MT5 (n,anything); ENDF/B-VIII.0 Fe56 MT5 verimi 14 MeV'de 0.46 --
      yalniz (n,xn) kanallarini saymak 14 MeV demir zirhta dengeyi %0.15
      bozuyordu, olculdu) + sabit kaynakta fisyon notronlari (nu-fission;
      ozdegerde fisyon S'nin icindedir).
   A: absorption (OpenMC "absorption" (n,xn)'i icermez).
   Analog tahminciyle denge HER GECMISTE tamdir (yalniz yuvarlama; test 1e-9).
   Birim: kaynak parcacigi basina (siddet 1) ya da siddetle [1/s].
================================================================================
"""

import math
from typing import Dict, List, Optional, Sequence, Tuple

from cekirdek import spektrum
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from cekirdek.spektrum import Deger

_log = kaydedici(__name__)

FILTRE_SINIR = "yuzey_sinir"
FILTRE_KUTU = "yuzey_kutu"
YUZEY_FILTRELERI = (FILTRE_SINIR, FILTRE_KUTU)
YUZEY_SKORU = "current"
TALLY_ONEKI = "y7_"
_DENGE_ONEKI = "y7_denge:"
DENGE_SKORLARI = ("absorption", "nu-fission", "scatter", "nu-scatter")
EKSENLER = ("x", "y", "z")
_SIFIR = Deger(0.0, 0.0)


# ----------------------------------------------------------------------------
# tanimlar
# ----------------------------------------------------------------------------

def filtre_sinir() -> dict:
    return {"tur": FILTRE_SINIR}


def filtre_kutu(boyut: Sequence[int], alt: Optional[Sequence[float]] = None,
                ust: Optional[Sequence[float]] = None) -> dict:
    """Kutu agi filtresi; alt/ust verilmezse sinirlar kurulurken turetilir."""
    f = {"tur": FILTRE_KUTU, "boyut": [int(n) for n in boyut]}
    if alt is not None and ust is not None:
        f["alt"] = [float(x) for x in alt]
        f["ust"] = [float(x) for x in ust]
    else:
        f["otomatik"] = True
    return f


def yuzey_filtresi(t: dict) -> Optional[dict]:
    """Tally'nin (ilk) yuzey filtresi; yoksa None."""
    return next((f for f in t.get("filtreler") or [] if f.get("tur") in YUZEY_FILTRELERI), None)


def yuzey_tally_mi(t: dict) -> bool:
    return yuzey_filtresi(t) is not None


def kosu_yuzey_tallysi_mi(tally) -> bool:
    """Statepoint tally'si (openmc.Tally) yuzey filtreli mi (Calistir karti okur)."""
    return any(type(f).__name__ in ("SurfaceFilter", "MeshSurfaceFilter")
               for f in tally.filters)


def denge_adi(ad: str) -> str:
    return _DENGE_ONEKI + ad


def kutu_sinirlari(spec: dict, f: dict, sinir_kutu) -> Tuple[List[float], List[float]]:
    from cekirdek import kurucu
    return kurucu.tally_mesh_sinirlari(spec, f, sinir_kutu)


# ----------------------------------------------------------------------------
# kurucu kancasi
# ----------------------------------------------------------------------------

def vakum_yuzeyleri(geometri: "openmc.Geometry") -> list:
    """Vakum sinir kosullu yuzeyler (id sirasinda)."""
    yuzeyler = geometri.get_all_surfaces().values()
    return sorted((s for s in yuzeyler if s.boundary_type == "vacuum"), key=lambda s: s.id)


def _kutu_agi(spec: dict, f: dict, sinir_kutu) -> "openmc.RegularMesh":
    import openmc
    mesh = openmc.RegularMesh()
    mesh.dimension = list(f["boyut"])
    mesh.lower_left, mesh.upper_right = kutu_sinirlari(spec, f, sinir_kutu)
    return mesh


def kaynak_parcacigi(spec: dict) -> str:
    k = ((spec or {}).get("ayarlar") or {}).get("kaynak") or {}
    return k.get("parcacik") or "neutron"


def _yuzey_filtreleri(spec: dict, t: dict, geometri, sinir_kutu):
    """(filtreler, kutu agi ya da None); sinirda vakum yoksa (None, None)."""
    import openmc
    filtreler, mesh = [], None
    for f in t.get("filtreler") or []:
        if f["tur"] == FILTRE_SINIR:
            yuzeyler = vakum_yuzeyleri(geometri)
            if not yuzeyler:
                _log.warning("'%s': modelde vakum sınırı yok, sınır tally'si kurulmadı", t["ad"])
                return None, None
            filtreler.append(openmc.SurfaceFilter(yuzeyler))
        elif f["tur"] == FILTRE_KUTU:
            mesh = _kutu_agi(spec, f, sinir_kutu)
            filtreler.append(openmc.MeshSurfaceFilter(mesh))
        elif f["tur"] == "enerji":
            filtreler.append(openmc.EnergyFilter(list(f["gruplar"])))
        else:
            raise ValueError(_("yüzey tally'sinde desteklenmeyen filtre: %s") % f["tur"])
    filtreler.append(openmc.ParticleFilter([kaynak_parcacigi(spec)]))
    return filtreler, mesh


def _tally_kur(spec: dict, t: dict, geometri, sinir_kutu) -> list:
    """Bir yuzey tally'si (+ notron kaynakli kutuda denge tally'si)."""
    import openmc
    filtreler, mesh = _yuzey_filtreleri(spec, t, geometri, sinir_kutu)
    if filtreler is None:
        return []
    tal = openmc.Tally(name=t["ad"])
    tal.scores = list(t["skorlar"])
    tal.filters = filtreler
    if mesh is None or kaynak_parcacigi(spec) != "neutron":
        return [tal]
    denge = openmc.Tally(name=denge_adi(t["ad"]))
    denge.scores = list(DENGE_SKORLARI)
    denge.filters = [openmc.MeshFilter(mesh), openmc.ParticleFilter(["neutron"])]
    denge.estimator = "analog"
    return [tal, denge]


def tally_ekle(spec: dict, model: "openmc.Model", sinir_kutu) -> Tuple[str, ...]:
    """kurucu.kur kancasi: yuzey tally'lerini modele ekler; eklenen adlar."""
    yeni = []
    for t in spec.get("tallyler") or []:
        if yuzey_tally_mi(t):
            yeni.extend(_tally_kur(spec, t, model.geometry, sinir_kutu))
    if yeni:
        import openmc
        model.tallies = openmc.Tallies(list(model.tallies) + yeni)
    return tuple(t.name for t in yeni)


# ----------------------------------------------------------------------------
# saf hesaplar
# ----------------------------------------------------------------------------

def toplam_degerleri(degerler: Sequence[Deger]) -> Deger:
    return Deger(sum(d.ort for d in degerler), math.sqrt(sum(d.sapma ** 2 for d in degerler)))


def sutun(df, ad: str):
    """Duz ya da cok duzeyli (MeshSurfaceFilter) sutun adlari icin seri."""
    if ad in df.columns:
        return df[ad]
    return df[(ad, "")]


def _enerji_var(df) -> bool:
    adlar = [c if isinstance(c, str) else c[0] for c in df.columns]
    return "energy low [eV]" in adlar


def _spektrum(df, degerler: Dict[int, Deger]) -> Optional[dict]:
    """degerler: satir sirasi -> Deger; enerji gruplari kenarlarla toplanir."""
    if not _enerji_var(df):
        return None
    alt, ust = sutun(df, "energy low [eV]"), sutun(df, "energy high [eV]")
    gruplar: Dict[Tuple[float, float], List[Deger]] = {}
    for sira, d in degerler.items():
        gruplar.setdefault((float(alt.iloc[sira]), float(ust.iloc[sira])), []).append(d)
    anahtarlar = sorted(gruplar)
    toplamlar = [toplam_degerleri(gruplar[a]) for a in anahtarlar]
    return {"kenarlar": [a[0] for a in anahtarlar] + [anahtarlar[-1][1]],
            "deger": [d.ort for d in toplamlar], "sapma": [d.sapma for d in toplamlar]}


def sinir_akimlari(df) -> dict:
    """SurfaceFilter tablosu -> yuzey basina kacak |J|, toplam ve spektrum."""
    yuzey, ort, sap = sutun(df, "surface"), sutun(df, "mean"), sutun(df, "std. dev.")
    satirlar = {i: Deger(abs(float(ort.iloc[i])), float(sap.iloc[i])) for i in range(len(df))}
    yuzeyler: Dict[int, List[Deger]] = {}
    for i, d in satirlar.items():
        yuzeyler.setdefault(int(yuzey.iloc[i]), []).append(d)
    yuzey_top = {k: toplam_degerleri(v) for k, v in sorted(yuzeyler.items())}
    return {"yuzeyler": yuzey_top, "toplam": toplam_degerleri(list(yuzey_top.values())),
            "spektrum": _spektrum(df, satirlar)}


def _mesh_sutunu(df, eksen: str):
    mesh = next(c[0] for c in df.columns if isinstance(c, tuple) and str(c[0]).startswith("mesh"))
    return df[(mesh, eksen)]


def _dis_yuz_mu(yuz: str, indeks: Sequence[int], boyut: Sequence[int]) -> bool:
    """'x-min' yuzu yalniz ix = 1 hucresinde, 'x-max' yalniz ix = nx'te dis yuzdur."""
    eksen, uc = yuz.split("-")
    i = EKSENLER.index(eksen)
    return indeks[i] == (1 if uc == "min" else int(boyut[i]))


def kutu_akimlari(df, boyut: Sequence[int]) -> dict:
    """MeshSurfaceFilter tablosu -> dis yuzlerden giren/cikan (yuz basina ve
    toplam) ve cikan akimin enerji spektrumu (varsa)."""
    yuzey = _mesh_sutunu(df, "surf")
    indeksler = [_mesh_sutunu(df, e) for e in EKSENLER]
    ort, sap = sutun(df, "mean"), sutun(df, "std. dev.")
    yuzler = {"%s-%s" % (e, u): {"giren": [], "cikan": []} for e in EKSENLER for u in ("min", "max")}
    cikan_satirlar: Dict[int, Deger] = {}
    for i in range(len(df)):
        yuz, yon = str(yuzey.iloc[i]).split()
        if not _dis_yuz_mu(yuz, [int(s.iloc[i]) for s in indeksler], boyut):
            continue
        d = Deger(float(ort.iloc[i]), float(sap.iloc[i]))
        yuzler[yuz]["cikan" if yon == "out" else "giren"].append(d)
        if yon == "out":
            cikan_satirlar[i] = d
    ozet = {y: {k: toplam_degerleri(v) for k, v in g.items()} for y, g in yuzler.items()}
    giren = toplam_degerleri([g["giren"] for g in ozet.values()])
    cikan = toplam_degerleri([g["cikan"] for g in ozet.values()])
    return {"yuzler": ozet, "giren": giren, "cikan": cikan,
            "net_cikan": spektrum.fark(cikan, giren), "spektrum": _spektrum(df, cikan_satirlar)}


def denge(giren: Deger, cikan: Deger, kaynak: Optional[Deger], uretim: Deger,
          sogurma: Deger) -> dict:
    """artik = S + giren - cikan + U - A (korelasyonsuz birlesik sapma);
    kaynak bilinmiyorsa artik None."""
    if kaynak is None:
        return {"artik": None, "bagil": None}
    uretim = toplam_degerleri([kaynak, giren, uretim])
    kayip = toplam_degerleri([cikan, sogurma])
    artik = spektrum.fark(uretim, kayip)
    bagil = artik.ort / kayip.ort if kayip.ort else None
    return {"artik": artik, "bagil": bagil}


def _icinde(nokta: Sequence[float], alt: Sequence[float], ust: Sequence[float]) -> Optional[bool]:
    """True/False; tam bir yuzun uzerindeyse None (pay belirsiz)."""
    if any(p == a or p == u for p, a, u in zip(nokta, alt, ust)):
        return None
    return all(a < p < u for p, a, u in zip(nokta, alt, ust))


def kutu_kaynagi(spec: dict, sinirlar, nu_fisyon: Optional[Deger] = None,
                 keff: Optional[Deger] = None) -> Optional[Deger]:
    """Kutudaki kaynak S (modul belgesi); bilinmiyorsa None."""
    a = spec.get("ayarlar") or {}
    if a.get("mod", "eigenvalue") == "eigenvalue":
        return spektrum.oran(nu_fisyon, keff)
    k = a.get("kaynak") or {}
    if k.get("tur", "nokta") != "nokta":
        return None
    ic = _icinde(list(k.get("konum") or (0.0, 0.0, 0.0)), sinirlar[0], sinirlar[1])
    if ic is None:
        return None
    return Deger(float(k.get("kuvvet") or 1.0), 0.0) if ic else _SIFIR
