# -*- coding: utf-8 -*-
"""
 yuzey_oku.py  --  Y7: statepoint'ten yuzey akimi sonuclari (Calistir karti)

 Her yuzey tally'si icin (tanim: cekirdek/yuzey_akim.py):
   sinir : yuzey basina kacak |J|, toplam, kacak spektrumu (EnergyFilter
           varsa) ve karsilastirma icin global "leakage" (sabit kaynakta
           kaynak siddetiyle carpilir: OpenMC global tally'leri kaynak
           parcacigi basinadir, kullanici tally'leri siddetle carpilir --
           olculdu, testler/test_y7_fizik.py).
   kutu  : dis yuzlerden giren/cikan, yuz basina, cikan akim spektrumu ve
           notron dengesi S + giren - cikan + U - A (y7_denge:<ad> tally'si,
           analog; U = nu-scatter - scatter [+ nu-fission sabit kaynakta]).
"""

from typing import List, Optional

from cekirdek import foton, spektrum, yuzey_akim as _y
from cekirdek.gunluk import kaydedici
from cekirdek.spektrum import Deger

_log = kaydedici(__name__)


def _global_sizinti(sp) -> Optional[Deger]:
    try:
        for satir in sp.global_tallies:
            ad = satir["name"]
            ad = ad.decode() if isinstance(ad, bytes) else str(ad)
            if ad == "leakage":
                return Deger(float(satir["mean"]), float(satir["std_dev"]))
    except (KeyError, ValueError, TypeError):
        _log.warning("statepoint global sızıntısı okunamadı", exc_info=True)
    return None


def _keff(sp) -> Optional[Deger]:
    try:
        k = sp.keff
    except (KeyError, AttributeError, ValueError):
        return None
    return Deger(float(k.nominal_value), float(k.std_dev)) if k is not None else None


def _skor_toplami(df, skor: str) -> Deger:
    secim = _y.sutun(df, "score") == skor
    ort, sap = _y.sutun(df, "mean")[secim], _y.sutun(df, "std. dev.")[secim]
    return Deger(float(ort.sum()), float((sap ** 2).sum()) ** 0.5)


def _denge_terimleri(sp, ad: str, sabit: bool) -> Optional[dict]:
    """y7_denge:<ad> (analog) tally'sinden A, nuF ve net uretim
    U = (nu-scatter - scatter) [+ nuF sabit kaynakta]; yoksa None."""
    try:
        df = sp.get_tally(name=_y.denge_adi(ad)).get_pandas_dataframe()
    except LookupError:
        _log.info("'%s' denge tally'si yok", ad)
        return None
    eksik = set(_y.DENGE_SKORLARI) - set(_y.sutun(df, "score"))
    if eksik:
        _log.warning("'%s' denge tally'sinde skor eksik: %s; denge hesaplanmadı",
                     ad, ", ".join(sorted(eksik)))
        return None
    nuf = _skor_toplami(df, "nu-fission")
    sacilma = spektrum.fark(_skor_toplami(df, "nu-scatter"), _skor_toplami(df, "scatter"))
    uretim = _y.toplam_degerleri([sacilma, nuf]) if sabit else sacilma
    return {"A": _skor_toplami(df, "absorption"), "nuF": nuf, "X": sacilma, "U": uretim}


def _filtre(t, tur_adi: str):
    return next((f for f in t.filters if type(f).__name__ == tur_adi), None)


def _sinir_sonucu(t, sizinti: Optional[Deger], olcek: float, foton_var: bool) -> dict:
    """Foton tasinimi acikken global "leakage" fotonlari da sayar; sinir
    tally'si kaynak parcacigina suzuldugu icin karsilastirilmaz."""
    r = _y.sinir_akimlari(t.get_pandas_dataframe())
    global_ = (None if sizinti is None or foton_var
               else Deger(sizinti.ort * olcek, sizinti.sapma * olcek))
    return dict(r, ad=t.name, tur=_y.FILTRE_SINIR, global_sizinti=global_,
                global_foton_karisik=foton_var)


def _kutu_sonucu(sp, t, f, spec: dict, keff: Optional[Deger], sabit: bool) -> dict:
    boyut = tuple(int(n) for n in f.mesh.dimension)
    sinirlar = (list(f.mesh.lower_left), list(f.mesh.upper_right))
    r = _y.kutu_akimlari(t.get_pandas_dataframe(), boyut)
    terim = _denge_terimleri(sp, t.name, sabit)
    sonuc = dict(r, ad=t.name, tur=_y.FILTRE_KUTU, boyut=boyut, sinirlar=sinirlar,
                 terimler=terim, kaynak=None, denge={"artik": None, "bagil": None})
    if terim is not None:
        s = _y.kutu_kaynagi(spec, sinirlar, terim["nuF"], keff)
        sonuc["kaynak"] = s
        sonuc["denge"] = _y.denge(r["giren"], r["cikan"], s, terim["U"], terim["A"])
    return sonuc


def oku(statepoint: str, spec: dict) -> Optional[List[dict]]:
    """Statepoint'teki yuzey tally sonuclari (tally sirasi); yoksa None."""
    import openmc
    a = (spec or {}).get("ayarlar") or {}
    sabit = a.get("mod", "eigenvalue") != "eigenvalue"
    olcek = float((a.get("kaynak") or {}).get("kuvvet") or 1.0) if sabit else 1.0
    sonuclar = []
    with openmc.StatePoint(statepoint) as sp:
        sizinti, keff = _global_sizinti(sp), (None if sabit else _keff(sp))
        foton_var = foton.tasinim_var_mi(spec)
        for t in sp.tallies.values():
            if (t.name or "").startswith(_y.TALLY_ONEKI):
                continue
            if _filtre(t, "SurfaceFilter") is not None:
                sonuclar.append(_sinir_sonucu(t, sizinti, olcek, foton_var))
            else:
                f = _filtre(t, "MeshSurfaceFilter")
                if f is not None:
                    sonuclar.append(_kutu_sonucu(sp, t, f, spec, keff, sabit))
    return sonuclar or None
