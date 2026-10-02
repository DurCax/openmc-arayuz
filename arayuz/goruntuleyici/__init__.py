# -*- coding: utf-8 -*-
"""
 arayuz/goruntuleyici  --  Geometri goruntuleyicisi (v3 Y2)

   gorunum.py     kesit penceresi (eksen, merkez, genislik), piksel <-> koordinat
   renk_kipi.py   malzeme / hucre / cakisma ve tanimsiz bolge renk kipleri
   bindirme.py    Y1 mesh tally ve kaynak noktalarinin kesit uzerine bindirilmesi
   kamera.py      3B golgeli gorunum kamerasi
   pencere.py     Araclar -> Goruntuleyici... penceresi (Qt; agir is H2 iscisinde)

 Hafif tutulur: menu bu paketi acilista ice aktarir, pencere ilk acilista yuklenir.
"""

from cekirdek.ceviri import N_

# Araclar menusundeki eylemin ipucu (arayuz/pencere/menuler.py)
IPUCU = N_("Malzeme/hücre/çakışma kesiti, ağ tally bindirmesi, kaynak noktaları, 3B görünüm (Y2)")


def ac(ana_pencere=None):
    """Tekil goruntuleyici penceresini acar (gecerli model ve son kosuyla)."""
    from arayuz.goruntuleyici import pencere
    return pencere.ac(ana_pencere)
