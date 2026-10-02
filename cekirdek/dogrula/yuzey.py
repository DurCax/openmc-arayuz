# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/yuzey.py  --  Y7 yuzey akimi tally kontrolleri

   - kullanici tally'si "y7_" onekini kullanamaz (denge tally'leri)   -> hata
   - bir tally'de birden cok yuzey filtresi                           -> hata
   - yuzey tally'sinde enerji disi filtre (malzeme, mesh)              -> hata
   - 'current' disi skor (OpenMC MeshSurfaceFilter'da durur;
     SurfaceFilter'da yalniz current/flux kabul eder)                  -> hata
   - kutu: boyut 3 pozitif tamsayi degil, elle sinirda alt >= ust     -> hata
   - sinir: modelde vakum siniri yok (kacak tanimca sifir; tally
     kurulmaz)                                                         -> uyari
 Kural kaynagi: cekirdek/yuzey_akim.py modul belgesi; OpenMC 0.16
 src/tallies/tally.cpp (Tally::set_scores).
"""

from typing import List, Optional

from cekirdek import yuzey_akim as _y
from cekirdek.ceviri import _
from cekirdek.dogrula._ortak import Bulgu
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)
_EKSEN_SAYISI = 3


def _uc_sayi(deger) -> Optional[List[float]]:
    if not isinstance(deger, (list, tuple)) or len(deger) != _EKSEN_SAYISI:
        return None
    try:
        return [float(x) for x in deger]
    except (TypeError, ValueError):
        return None


def _kutu_kontrol(f: dict, yer: str) -> List[Bulgu]:
    bulgular = []
    boyut = f.get("boyut")
    if not (isinstance(boyut, (list, tuple)) and len(boyut) == _EKSEN_SAYISI
            and all(isinstance(n, int) and n >= 1 for n in boyut)):
        bulgular.append(Bulgu("hata", yer, _("kutu ağı bölmeleri üç pozitif tamsayı olmalı: %r")
                              % (boyut,)))
    if f.get("otomatik") or ("alt" not in f and "ust" not in f):
        return bulgular
    alt, ust = _uc_sayi(f.get("alt")), _uc_sayi(f.get("ust"))
    if alt is None or ust is None or any(a >= u for a, u in zip(alt, ust)):
        bulgular.append(Bulgu("hata", yer, _("kutu sınırları geçersiz: alt %r, üst %r (her "
                                             "eksende alt < üst)") % (f.get("alt"), f.get("ust"))))
    return bulgular


def _vakum_var_mi(spec: dict) -> Optional[bool]:
    """Kok sinirinda vakum kosulu var mi; geometri okunamazsa None."""
    from cekirdek import geometri
    from cekirdek.geometri.sinir import sinir_bilgisi
    try:
        b = sinir_bilgisi(geometri.model(spec))
    except (ValueError, KeyError, TypeError, AttributeError):
        _log.info("Y7 sınır denetimi: geometri okunamadı", exc_info=True)
        return None
    yuzler = b.yuzler.values() if isinstance(b.yuzler, dict) else (b.yuzler or [])
    return "vacuum" in (b.yan, b.alt, b.ust, *yuzler)


def _tally_kontrol(spec: dict, t: dict) -> List[Bulgu]:
    yer = "tally:%s" % t.get("ad", "?")
    filtreler = t.get("filtreler") or []
    yuzeyler = [f for f in filtreler if f.get("tur") in _y.YUZEY_FILTRELERI]
    bulgular = []
    if len(yuzeyler) > 1:
        bulgular.append(Bulgu("hata", yer, _("bir tally'de yalnız bir yüzey filtresi olabilir")))
    diger = sorted({f.get("tur") for f in filtreler
                    if f.get("tur") not in _y.IZINLI_FILTRELER})
    if diger:
        bulgular.append(Bulgu("hata", yer, _("yüzey tally'sine yalnız enerji filtresi eklenebilir "
                                             "(bulunan: %s)") % ", ".join(map(str, diger))))
    if list(t.get("skorlar") or []) != [_y.YUZEY_SKORU]:
        bulgular.append(Bulgu("hata", yer, _("yüzey tally'sinde yalnız 'current' skoru olabilir"),
                              _("OpenMC yüzey ağı filtresinde başka skorla koşuyu durdurur.")))
    for f in yuzeyler:
        if f["tur"] == _y.FILTRE_KUTU:
            bulgular.extend(_kutu_kontrol(f, yer))
        elif _vakum_var_mi(spec) is False:
            bulgular.append(Bulgu("uyari", yer, _("modelde vakum sınırı yok: kaçak tanımca sıfır, "
                                                  "sınır tally'si kurulmaz"),
                                  _("Yansıtıcı/periyodik sınırdan parçacık kaçmaz. Bir bölgeden "
                                    "geçen akım için kutu ağı türünü kullanın.")))
    return bulgular


def _ad_tekilligi(spec: dict) -> List[Bulgu]:
    """Yuzey tally'sinin adi tekil olmali: denge tally'si y7_denge:<ad> ve
    sonuc karti adla eslesir."""
    adlar = [t.get("ad") for t in spec.get("tallyler") or []]
    return [Bulgu("hata", "tally:%s" % t.get("ad"),
                  _("'%s' adı birden çok tally'de var; yüzey tally'sinin adı tekil olmalı")
                  % t.get("ad"))
            for t in spec.get("tallyler") or []
            if _y.yuzey_tally_mi(t) and adlar.count(t.get("ad")) > 1]


def yuzey_kontrol(spec: dict) -> List[Bulgu]:
    bulgular = _ad_tekilligi(spec)
    for t in spec.get("tallyler") or []:
        if str(t.get("ad") or "").startswith(_y.TALLY_ONEKI):
            bulgular.append(Bulgu("hata", "tally:%s" % t.get("ad"),
                                  _("'%s' öneki yüzey akımı denge tally'lerine ayrılmıştır")
                                  % _y.TALLY_ONEKI, _("Tally'yi yeniden adlandırın.")))
        if _y.yuzey_tally_mi(t):
            bulgular.extend(_tally_kontrol(spec, t))
    return bulgular
