# -*- coding: utf-8 -*-
"""
================================================================================
 cekirdek/geometri  --  Esnek geometri modeli (Dalga G): dugum agaci
================================================================================

 Tasarim: docs/GEOMETRI_MODELI.md. G-1 genel API'si (G-2 ve G-3 yalniz
 bunu kullanir; G-1 birlesince DONDURULUR):

   model(spec)            -> GeometriModeli   sablon/agac -> normalize model
   genislet(spec)         -> dict             saf; sablon -> agac (§6)
   yapisal_denetim(spec)  -> [Bulgu]          tur/alan/basvuru/dongu/derinlik
   kur(spec, nesneler, universeler) -> (kok Universe, sinir kutusu, GeometriDizini)
   betik(spec, yazici)    -> (gx, gy, {ad: degisken})   ayni gezintiden betik
   yukseklik(m), eksenel_dilimler(m), aktif_aralik(spec), sinir_kutusu(m),
   ic_olcusu(m), gruplar(m), grup_degeri_yaz(spec, grup, deger),
   basvurular(spec), ad_degistir(spec, tur, eski, yeni), icerik(m)

 Sablon modunda (kor.tur 7 sablondan biri) agac her istendiginde
 genislet(spec) ile turetilir; gelismis modda (kor.tur == "agac") tek
 gercek kaynak spec["geometri"]dir.
================================================================================
"""

from dataclasses import dataclass, field

from cekirdek.geometri.sema import normalize, tanimlar as _tanimlar

AGAC = "agac"


@dataclass(frozen=True)
class GeometriModeli:
    """Normalize edilmis, dondurulmus geometri modeli (alanlar yeniden atanamaz)."""
    kok: dict
    parcalar: tuple
    gruplar: tuple
    tanimlar: dict
    sablon: str | None = None           # sablon turu; gelismis modda None
    kaynaklar: dict = field(default_factory=dict)
    agac: dict = field(default_factory=dict)   # normalize agac sozlugu (kopya)


def agac_modu(spec):
    """Spec gelismis (agac) modunda mi?"""
    return ((spec or {}).get("kor") or {}).get("tur") == AGAC


def ham_agac(spec):
    """Normalize edilmemis agac: gelismiste spec["geometri"], sablonda genislet."""
    if agac_modu(spec):
        return spec.get("geometri") or {}
    from cekirdek.geometri.genislet import genislet as _genislet
    return _genislet(spec)


def model(spec):
    """Spec -> GeometriModeli (normalize). Girdi DEGISMEZ."""
    agac = normalize(spec, ham_agac(spec))
    return GeometriModeli(
        kok=agac["kok"], parcalar=tuple(agac.get("parcalar") or ()),
        gruplar=tuple(agac.get("gruplar") or ()), tanimlar=_tanimlar(spec, agac),
        sablon=None if agac_modu(spec) else (spec.get("kor") or {}).get("tur"),
        kaynaklar=dict(agac.get("_kaynaklar") or {}), agac=agac)


def genislet(spec):
    """Sablonu agaca genisletir (saf; §6). Gelismis modda agacin kopyasi."""
    import copy
    if agac_modu(spec):
        return copy.deepcopy(spec.get("geometri") or {})
    from cekirdek.geometri.genislet import genislet as _genislet
    return _genislet(spec)


def yapisal_denetim(spec):
    """Agacin yapisal bulgulari (kurulumun on kosulu)."""
    from cekirdek.geometri.denetim import yapisal_denetim_agac
    return yapisal_denetim_agac(spec, ham_agac(spec))


def yukseklik(m):
    """Modelin toplam yuksekligi [cm]; 2B'de None (§3.6)."""
    from cekirdek.geometri.eksenel import model_yuksekligi
    return model_yuksekligi(m)
