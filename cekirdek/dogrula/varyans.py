# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/varyans.py  --  Y9 varyans azaltma (agirlik penceresi) kontrolleri

   - gecersiz ayar (mod, yontem, ag, enerji, sayilar)                        -> hata
   - 'uygula': pencere dosyasi yok                                            -> hata
   - 2B model (z'de sinirsiz): ag kurulamaz                                   -> hata
   - 'uret_uygula': pencereler kosu sirasinda ogrenilir; ilk cevrimlerde
     kotu pencere asiri bolunmeye yol acabilir                                -> bilgi
   - kuresel ag, kuresel olmayan modelde                                      -> uyari
 Kural kaynagi: cekirdek/varyans.py modul belgesi.
"""

import os
from typing import List

from cekirdek import kurucu, varyans
from cekirdek.ceviri import _
from cekirdek.dogrula._ortak import Bulgu

_YER = "ayarlar"


def varyans_kontrol(spec: dict) -> List[Bulgu]:
    try:
        a = varyans.ayar(spec)
    except ValueError as e:
        return [Bulgu("hata", _YER, str(e))]
    if not a.var:
        return []
    bulgular: List[Bulgu] = []
    if a.mod == "uygula":
        if not os.path.isfile(a.dosya):
            bulgular.append(Bulgu("hata", _YER, _("ağırlık penceresi dosyası yok: %s") % a.dosya))
        return bulgular
    try:
        varyans.mesh_sinirlari(spec, (1.0, 1.0))
    except ValueError as e:
        return [Bulgu("hata", _YER, str(e))]
    if a.mesh_turu == "kuresel" and not kurucu._kure_mu(spec):
        bulgular.append(Bulgu("uyari", _YER, _("küresel ağırlık penceresi ağı küresel olmayan "
                                               "modelde yalnız kürenin içindeki bölgeyi kapsar")))
    if a.mod == "uret_uygula":
        bulgular.append(Bulgu("bilgi", _YER, _(
            "pencereler koşu sırasında öğrenilir; ilk çevrimlerde pencere eksik olduğundan "
            "analog taşıma yapılır. Önerilen düzen: önce 'üret', sonra 'uygula'.")))
    return bulgular
