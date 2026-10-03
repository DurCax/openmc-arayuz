# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/triso.py  --  Y9 TRISO kompakt / pebble kontrolleri

   - tanimin kendi tutarliligi (katman yaricaplari, malzeme, paketleme siniri)  -> cekirdek/triso.py
   - tanimsiz malzeme adi                                                      -> hata
   - TRISO kompakti 2B (yuksekligi olmayan) modelde                             -> hata (sonlu silindir)
   - kompakt yuksekligi modelin yuksekligiyle ayni degil                        -> uyari
   - kullanilmayan TRISO tanimi                                                 -> bilgi
 Kural kaynagi: cekirdek/triso.py modul belgesi (paketleme sinirlari OpenMC 0.16 pack_spheres).
"""

from typing import List

from cekirdek import sema, triso
from cekirdek.ceviri import _
from cekirdek.dogrula._ortak import Bulgu
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

_YER = "trisolar"
_YUKSEKLIK_TOLERANSI = 1.0e-9    # cm; ayni yukseklik sayilir


def _kullanimlar(spec: dict) -> set:
    from cekirdek.geometri.basvuru import basvurular
    if not sema.agac_modu(spec):
        return set()
    try:
        return {b.ad for b in basvurular(spec) if b.tur == "triso"}
    except (KeyError, ValueError, TypeError):   # agac bozuksa agac denetimi zaten bildirir
        _log.info("TRISO kullanımı okunamadı (ağaç geçersiz)", exc_info=True)
        return set()


def _model_yuksekligi(spec: dict):
    try:
        return sema.model_yuksekligi(spec)
    except (KeyError, ValueError, TypeError):
        _log.info("model yüksekliği okunamadı", exc_info=True)
        return None


def triso_kontrol(spec: dict) -> List[Bulgu]:
    """spec["trisolar"] icin bulgular (alan yoksa bos)."""
    tanimlar = spec.get("trisolar") or []
    if not tanimlar:
        return []
    tanimli = {m.get("ad") for m in spec.get("malzemeler") or []}
    yukseklik = _model_yuksekligi(spec)
    bulgular: List[Bulgu] = []
    for t in tanimlar:
        yer = "%s:%s" % (_YER, t.get("ad"))
        for seviye, mesaj in triso.sorunlar(t):
            bulgular.append(Bulgu(seviye, yer, mesaj))
        eksik = [m for m in triso.malzemeler(t) if m not in tanimli]
        if eksik:
            bulgular.append(Bulgu("hata", yer, _("tanımsız malzeme: %s") % ", ".join(eksik)))
        if (t.get("sekil") or "kompakt") == "kompakt":
            bulgular += _yukseklik_kontrol(t, yer, yukseklik)
    kullanilan = _kullanimlar(spec)
    for t in tanimlar:
        if sema.agac_modu(spec) and t.get("ad") not in kullanilan:
            bulgular.append(Bulgu("bilgi", "%s:%s" % (_YER, t.get("ad")),
                                  _("TRISO tanımı geometride kullanılmıyor")))
    return bulgular


def _yukseklik_kontrol(t: dict, yer: str, yukseklik) -> List[Bulgu]:
    if not yukseklik:
        return [Bulgu("hata", yer, _("TRISO kompaktı 3B model gerektirir"),
                      _("Kompakt sonlu yükseklikli bir silindirdir; modelin yüksekliği "
                        "tanımlanmalı (geometri kökünde yükseklik)."))]
    try:
        h = float(t.get("yukseklik"))
    except (TypeError, ValueError):
        return []
    if abs(h - float(yukseklik)) > _YUKSEKLIK_TOLERANSI:
        return [Bulgu("uyari", yer,
                      _("kompakt yüksekliği (%g cm) modelin yüksekliğinden (%g cm) farklı")
                      % (h, yukseklik),
                      _("Parçacıklar yalnızca kompakt yüksekliğinde paketlenir; fazlası matris "
                        "ile dolar, eksiği parçacıkları keser."))]
    return []
