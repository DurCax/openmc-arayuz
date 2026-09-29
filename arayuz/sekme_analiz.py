# -*- coding: utf-8 -*-
"""
sekme_analiz.py -- Analiz sekmesinin CEPHESI (parcalar: arayuz/analiz/).

Dosya 954 satirdi (Dalga 2 siniri 800); icerik bolundu:
    arayuz/analiz/adlar.py     gorunen adlar, aciklamalar, varsayilan araliklar
    arayuz/analiz/isciler.py   TaramaIsci / AramaIsci
    arayuz/analiz/tuval.py     kapanisa dayanikli matplotlib tuvali
    arayuz/analiz/sekme.py     AnalizSekmesi
Disaridaki kod (ana pencere, testler, sekme_tukenme) bu adlari kullanmayi
surdurur.
"""

from arayuz.analiz.adlar import (FORM_GENISLIGI, GELISMIS_PARAMETRELER, KATSAYI_ADLARI,
                                 PARAMETRE_ADLARI, SIRA, aciklama, birim, dar,
                                 form_duzeni, katsayi_birimi, parametre_adi,
                                 sirali_taramalar, varsayilan_aralik)
from arayuz.analiz.isciler import AramaIsci, TaramaIsci
from arayuz.analiz.sekme import AnalizSekmesi

__all__ = ["FORM_GENISLIGI", "GELISMIS_PARAMETRELER", "KATSAYI_ADLARI",
           "PARAMETRE_ADLARI", "SIRA", "aciklama", "birim", "dar", "form_duzeni",
           "katsayi_birimi", "parametre_adi", "sirali_taramalar", "varsayilan_aralik",
           "AramaIsci", "TaramaIsci", "AnalizSekmesi"]
