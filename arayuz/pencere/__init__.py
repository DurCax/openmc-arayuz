# -*- coding: utf-8 -*-
"""
================================================================================
 arayuz/pencere/  --  Ana uygulama penceresi, parcalara bolunmus
================================================================================
 model_islemleri.py : saf (Qt'siz) model islemleri + sekme/konu sabitleri
                      (kor_turu_degistir, tur hafizasi, sekme isaretleri, ...)
 menuler.py         : MenulerMixin -- menu, arac cubugu, durum cubugu, yardim
 proje.py           : ProjeMixin   -- ac/kaydet, son kullanilanlar, ice/disa aktarma
 gecmis.py          : GecmisMixin  -- geri al / yinele
 ana_pencere.py     : AnaPencere   -- pencere iskeleti (yukaridakileri karistirir)

 Giris noktasi ve eski ice aktarma yolu arayuz/ana_pencere.py'de kalir:
   python -m arayuz.ana_pencere [dosya.json]
   from arayuz import ana_pencere; ana_pencere.AnaPencere / kor_turu_degistir ...
================================================================================
"""
