# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/bilesen_triso.py  --  Y9: TRISO kompakt / pebble bileseni evreni
================================================================================
 spec["trisolar"][] tanimi (cekirdek/triso.py) -> evren. Kurucu.bilesen_evreni
 'triso' turunde buraya gelir; nesne ve betik ayni cagrilari yapar (Yapici).

   parcacik evreni  : es merkezli kureler (kernel, buffer, IPyC, SiC, OPyC); en dis
                      katman parcacigin sinirinda biter (TRISO hucre bolgesi)
   kafes            : openmc.model.create_triso_lattice (pack_spheres / duzenli)
   kompakt evreni   : -zsilindir(R) icinde kafes; disinda matris (z'de kafesin
                      disi de matristir: kabi ust model keser, yukseklik 3B ister)
   pebble evreni    : -kure(yakit_yaricap) icinde kafes; kabuk; disi gaz
================================================================================
"""

from cekirdek import triso as _t
from cekirdek.ceviri import _


def _katman_hucreleri(y, yuzeyler, dolgular):
    """Es merkezli kure katmanlari (openmc.model.pin yalniz silindir kabul eder):
    icten disa ilk -s0, ara +s(i-1) & -s(i), son +s(son) (parcacik siniri TRISO bolgesinde)."""
    n = len(dolgular)
    hucreler = []
    for i, dolgu in enumerate(dolgular):
        if n == 1:
            bolge = None
        elif i == 0:
            bolge = -yuzeyler[0]
        elif i == n - 1:
            bolge = +yuzeyler[-1]
        else:
            bolge = +yuzeyler[i - 1] & -yuzeyler[i]
        hucreler.append(y.hucre(dolgu, bolge))
    return hucreler


def evren(k, t, ad):
    """Tanimdan evren (k: Kurucu)."""
    hatalar = [m for s, m in _t.sorunlar(t) if s == "hata"]
    if hatalar:
        raise ValueError(_("'%s' TRISO tanımı geçersiz: %s") % (ad, "; ".join(hatalar)))
    y = k.y
    kap = _t.konteyner(t)
    if kap.sekil == "kompakt" and not k.yukseklik:
        raise ValueError(_("'%s' TRISO kompaktı 3B model gerektirir: çekirdek yüksekliği "
                         "tanımlı değil. Kompakt sonlu yükseklikli bir silindirdir.") % ad)
    y.yorum("%s — TRISO %s, %d parçacık, %s yerleşim, paketleme %.4f"
            % (ad, kap.sekil, _t.yerlesim_ozeti(t).n, t.get("yontem") or "rastgele",
               _t.yerlesim_ozeti(t).gercek_pf))
    katmanlar = t["katmanlar"]
    yuzeyler = [y.kure(float(c["r"])) for c in katmanlar[:-1]]
    parcacik = y.evren(_katman_hucreleri(y, yuzeyler, [y.malzeme(c["malzeme"]) for c in katmanlar]),
                       degisken=k.degisken("tp", ad))
    matris = y.malzeme(t["matris_malzeme"])
    kafes = y.triso_kafesi(parcacik, t, matris)
    if kap.sekil == "pebble":
        s_yakit, s_dis = y.kure(kap.yaricap), y.kure(float(t["dis_yaricap"]))
        hucreler = [y.hucre(kafes, -s_yakit),
                    y.hucre(y.malzeme(t["kabuk_malzeme"]), +s_yakit & -s_dis),
                    y.hucre(y.malzeme(t["dis_malzeme"]), +s_dis)]
    else:
        s_kap = y.zsilindir(kap.yaricap)
        hucreler = [y.hucre(kafes, -s_kap), y.hucre(matris, +s_kap)]
    return y.evren(hucreler, name=ad, degisken=k.degisken("tk", ad))
