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
    from cekirdek.geometri.sablon import genislet as _genislet
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
    from cekirdek.geometri.sablon import genislet as _genislet
    return _genislet(spec)


def yapisal_denetim(spec):
    """Agacin yapisal bulgulari (kurulumun on kosulu)."""
    from cekirdek.geometri.denetim import yapisal_denetim_agac
    return yapisal_denetim_agac(spec, ham_agac(spec))


def yukseklik(m):
    """Modelin toplam yuksekligi [cm]; 2B'de None (§3.6)."""
    from cekirdek.geometri.eksenel import model_yuksekligi
    return model_yuksekligi(m)


# ----------------------------------------------------------------------------
# kurulum ve betik (tek gezinti; geometri/kurulum.py)
# ----------------------------------------------------------------------------

def kur(spec, nesneler, universeler):
    """(kok openmc.Universe, (gx, gy), GeometriDizini) -- R1-R12."""
    from cekirdek.geometri.kurulum import kur as _kur
    return _kur(spec, nesneler, universeler)


def betik(spec, satirlar, malzeme_degiskeni, degisken_adi=None):
    """Ayni gezintiden betik satirlari; DONER (gx, gy, {ad: degisken})."""
    from cekirdek.geometri.kurulum import betik as _betik
    return _betik(spec, satirlar, malzeme_degiskeni, degisken_adi)


# ----------------------------------------------------------------------------
# olculer ve eksenel
# ----------------------------------------------------------------------------

def sinir_kutusu(m):
    """Modelin sinir kutusu (gx, gy)."""
    from cekirdek.geometri.kap import sinir_kutusu as _sk
    return _sk(m)


def ic_olcusu(m):
    """Kok kesitinin kutusu (halkalar haric) -> kaynak kutusu."""
    from cekirdek.geometri.kap import ic_olcusu as _io
    return _io(m)


def eksenel_dilimler(m):
    """[(z0, z1, katman adi, katmani dolduran dugum)]."""
    from cekirdek.geometri.eksenel import eksenel_dilimler as _ed
    return _ed(m)


def aktif_aralik(spec):
    """Aktif (fisil) eksenel aralik; 2B'de None (R8)."""
    from cekirdek.geometri.eksenel import aktif_aralik as _aa
    return _aa(spec)


def hedef_araligi(spec, adlar):
    """Hedef cubuklarin eksenel araliklarinin birlesimi (cubuk_eksenel_aralik)."""
    from cekirdek.geometri.eksenel import hedef_araligi as _ha
    return _ha(spec, adlar)


def hedef_yuksekligi(spec, adlar=None):
    """Lineer guc paydasi (guc_yuksekligi genellemesi)."""
    from cekirdek.geometri.eksenel import hedef_yuksekligi as _hy
    return _hy(spec, adlar)


def gruplar(m):
    """Gruplar (dondurulmus demet)."""
    return tuple(m.gruplar)


def gelismise_gec(spec):
    """
    "Gelismis moda gec" (§6, §15 karar 1): YENI spec -- kor {"tur": "agac"},
    geometri = genislet(spec) (turetilmis "_" notlari atilir), sablonun
    urettigi tamburlar kutuphaneye (spec["tamburlar"]) tasinir. Girdi
    DEGISMEZ; geri donus yalniz Geri Al ile (arayuz eski spec'i saklar).
    """
    import copy
    if agac_modu(spec):
        return copy.deepcopy(spec)
    agac = genislet(spec)
    uretilen = (agac.get("_uretilen_tanimlar") or {}).get("tamburlar") or []
    yeni = copy.deepcopy(spec)
    yeni["kor"] = {"tur": AGAC}
    yeni["tamburlar"] = list(yeni.get("tamburlar") or []) + copy.deepcopy(uretilen)
    yeni["geometri"] = _turetilmissiz(agac)
    return yeni


def _turetilmissiz(deger):
    if isinstance(deger, dict):
        return {k: _turetilmissiz(v) for k, v in deger.items()
                if not (isinstance(k, str) and k.startswith("_"))}
    if isinstance(deger, list):
        return [_turetilmissiz(v) for v in deger]
    return deger


def kesik_konumlar(m):
    """Kesik/gizli kafes konumlari [{"kafes", "yol", "indeks", "harf", "durum"}]."""
    from cekirdek.geometri.kesik import kesik_konumlar as _kk
    return _kk(m)


# ----------------------------------------------------------------------------
# G-2 eklemeleri (§7; §16 "henuz yok" listesi)
# ----------------------------------------------------------------------------

def gez(m):
    """Ziyaret ureteci: (yol, dugum, carpan, z_araligi, kesik, ust_yollar, ...)."""
    from cekirdek.geometri.gez import gez as _gez
    return _gez(m)


def icerik(m):
    """Modelde yer alan adlar -- uygunluk.geometri_icerigi ile ayni bicim."""
    from cekirdek.geometri.gez import icerik as _ic
    return _ic(m)


def sinir_bilgisi(m):
    """Dis sinir: yuzey, yan/alt/ust, yuzler, periyodik_uygun."""
    from cekirdek.geometri.sinir import sinir_bilgisi as _sb
    return _sb(m)


def grup_degeri_yaz(spec, grup, deger):
    """YENI spec; sablonda tamburlu korun 'tamburlar' grubu kor.tambur.donme."""
    from cekirdek.geometri.sinir import grup_degeri_yaz as _gdy
    return _gdy(spec, grup, deger)


def basvurular(spec):
    """[Basvuru(yol, tur, ad)] -- spec["geometri"]deki ad basvurulari."""
    from cekirdek.geometri.basvuru import basvurular as _b
    return _b(spec)


def ad_degistir(spec, tur, eski, yeni):
    """YENI spec: tanim + butun basvurular yeniden adlandirilir (saf)."""
    from cekirdek.geometri.basvuru import ad_degistir as _ad
    return _ad(spec, tur, eski, yeni)
