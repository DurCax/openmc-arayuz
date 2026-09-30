# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/sinir.py  --  Dis sinir bilgisi ve grup degeri yazimi (§7)
================================================================================

   sinir_bilgisi(m) -> SinirBilgisi
     yuzey           "kare" | "altigen" | "silindir" | "kure" | "kirik"
                     (kirik: yansiticisiz kafes zarfli kok -- altigen tam
                     korun demet dis yuzlerinden gecen kirik cizgisi)
     yan, alt, ust   kokun sinir kosullari (alt/ust 2B'de ve kurede None)
     yuzler          yuz basina yan sinir (kok sinir.yuzler; yoksa None)
     yuz_adlari      dikdortgende ("-x", "+x", "-y", "+y"); altigende yuz
                     normali acilari ("0°", "60°", ...) -- kurulum sirasi
     periyodik_uygun en dis kesit dikdortgen/altigen ve en dis bolgede dis
                     sinira degen delik yok (OpenMC periodic esini bulur)
     dokunan_delikler dis sinira degen yerlesim adlari (periyodik engeli)
   grup_degeri_yaz(spec, grup, deger) -> YENI spec
     gelismis modda geometri.gruplar[ad].deger; sablonda tamburlu korun
     uretilen "tamburlar" grubu kor.tambur.donme'ye yazilir.
================================================================================
"""

import copy
from collections import namedtuple

from cekirdek.geometri import kesit as _k
from cekirdek.geometri import yerlesim as _yer
from cekirdek.geometri.eksenel import model_yuksekligi
from cekirdek.geometri.kap import en_dis_kesit

SinirBilgisi = namedtuple("SinirBilgisi", "yuzey yan alt ust yuzler yuz_adlari "
                                          "periyodik_uygun dokunan_delikler")
_YUZEY = {"dikdortgen": "kare", "altigen": "altigen", "silindir": "silindir",
          "kure": "kure", "kafes_zarfi": "kirik"}
DIKDORTGEN_YUZLERI = ("-x", "+x", "-y", "+y")
# dis sinira "degme" payi: bundan yakin delik periyodik eslemeyi bozar (cm)
DEGME_PAYI = 1.0e-6


def _yuz_adlari(kes):
    if kes.get("sekil") == "dikdortgen":
        return DIKDORTGEN_YUZLERI
    if kes.get("sekil") in ("altigen", "kafes_zarfi"):
        yon = kes.get("yonelim", "y")
        return tuple("%g°" % a for a in _k.altigen_normal_acilari(yon))
    return ()


def _dis_bolge_yerlesimleri(kok):
    halkalar = kok.get("halkalar") or []
    return (halkalar[-1].get("yerlesimler") if halkalar else kok.get("yerlesimler")) or []


def dokunan_delikler(m):
    """Kokun en dis bolgesinde dis sinira degen (ya da tasan) yerlesimler."""
    kok = m.kok
    dis = en_dis_kesit(kok)
    if dis.get("sekil") in ("kafes_zarfi", "kure"):
        return []
    adlar = []
    for y in _dis_bolge_yerlesimleri(kok):
        kes = y.get("kesit")
        if kes is None:
            from cekirdek.geometri.sema import bilesen_tanimi
            _t, t = bilesen_tanimi(m.tanimlar, (y.get("icerik") or {}).get("ad"))
            kes = {"sekil": "silindir", "yaricap": float((t or {}).get("yaricap") or 0.0)}
        for x, yy, _psi in _yer.ornekler(y, kok, m.tanimlar, m.gruplar):
            if not _k.kapsar(dis, kes, (x, yy), pay=-DEGME_PAYI):
                adlar.append(y.get("ad"))
                break
    return adlar


def sinir_bilgisi(m):
    """GeometriModeli -> SinirBilgisi."""
    kok = m.kok
    dis = en_dis_kesit(kok)
    yuzey = _YUZEY.get(dis.get("sekil"))
    if dis.get("sekil") == "kafes_zarfi":
        dis = dict(dis, yonelim=_zarf_yonelimi(kok))
    sinir = kok.get("sinir") or {}
    uc = yuzey != "kure" and bool(model_yuksekligi(m))
    dokunan = dokunan_delikler(m)
    return SinirBilgisi(
        yuzey=yuzey, yan=sinir.get("yan"),
        alt=sinir.get("alt") if uc else None, ust=sinir.get("ust") if uc else None,
        yuzler=copy.deepcopy(sinir.get("yuzler")), yuz_adlari=_yuz_adlari(dis),
        periyodik_uygun=yuzey in ("kare", "altigen") and not dokunan,
        dokunan_delikler=tuple(dokunan))


def _zarf_yonelimi(kok):
    ic = kok.get("ic") or {}
    kafes = ic.get("icerik") if ic.get("tur") == "eksenel" else ic
    return (kafes or {}).get("yonelim", "y") if isinstance(kafes, dict) else "y"


def grup_degeri_yaz(spec, grup, deger):
    """YENI spec: 'grup' adli grubun degeri 'deger'. Girdi DEGISMEZ.
    HATA KeyError: grup yok."""
    from cekirdek.geometri import agac_modu
    yeni = copy.deepcopy(spec)
    if agac_modu(spec):
        for g in (yeni.get("geometri") or {}).get("gruplar") or []:
            if g.get("ad") == grup:
                g["deger"] = float(deger)
                return yeni
        raise KeyError("tanımsız grup: %s" % grup)
    kor = yeni.get("kor") or {}
    t = kor.get("tambur") or {}
    if kor.get("tur") == "tamburlu" and int(t.get("sayi") or 0) > 0 and grup == "tamburlar":
        t["donme"] = float(deger)
        return yeni
    raise KeyError("tanımsız grup: %s" % grup)
