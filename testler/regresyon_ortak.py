# -*- coding: utf-8 -*-
"""
 regresyon_ortak.py  --  Tasinan regresyon testlerinin ortak yardimcilari (test modulu DEGIL)

 testler/test_regresyon.py'den ayrildi (Dalga 0). Adi test_ ile baslamaz;
 boylece ortak_test.ek_moduller() onu test modulu saymaz.
"""

import os

from testler.ortak_test import kontrol


KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


ORNEK = os.path.join(KOK, "ornekler")

# Regresyon cipasi -- arayuz gelistirilirken olculen referans
REFERANS_K = 1.3570
REFERANS_SAPMA = 0.0020


def _ornek_adlari():
    """
    ornekler/ altindaki butun spec dosyalari, sirali.

    ORNEK LISTELERI ELLE YAZILMAZ. Once sabit listeler vardi ve yeni eklenen
    ornekler (zirh_kure, pwr_eksenel) kapsam disinda kaliyordu; arayuzu
    cokerten bir cizim hatasi tam bu yuzden testlerden kacti.
    """
    import glob
    return sorted(os.path.splitext(os.path.basename(p))[0]
                  for p in glob.glob(os.path.join(ORNEK, "*.json")))


def _qt():
    """Ekransiz (offscreen) QApplication; PySide6 yoksa None."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6 import QtWidgets
    except Exception as e:
        kontrol("PySide6 yok, arayuz testi atlandi", True, "-> %s" % e)
        return None
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _ana_pencere(dosya=None):
    """
    AnaPencere kurar. Kullanicinin GERCEK ayarlari (son kullanilanlar)
    ortak_test.py'de, alt surecler dahil, yalitilir (AYAR_DIZINI). Buradaki
    eski yerel yonlendirme alt surecleri kapsamiyordu.
    """
    from arayuz.ana_pencere import AnaPencere
    return AnaPencere(dosya)


def _pencere_kapat(p):
    """Arka planda tukenme sonucu okunuyorsa bekler; pencereyi soru sormadan kapatir."""
    try:
        p.s_tukenme.bekle()
        p._kirli = False
        p.close()
    except Exception:
        pass


def _kor_turu(k, spec, tur, hafiza):
    """Dalga 3: kor turu Kor sekmesinde degil, model basligindan degisir
    (ana_pencere.kor_turu_degistir -> her editorde spec_yukle)."""
    from arayuz.ana_pencere import kor_turu_degistir
    kor_turu_degistir(spec, tur, hafiza)
    k.spec_yukle(spec)


def _tally_mesh(model_tallies, ad):
    import openmc
    for tal in model_tallies:
        if tal.name == ad:
            for f in tal.filters:
                if isinstance(f, openmc.MeshFilter):
                    m = f.mesh
                    return (list(m.dimension), [float(x) for x in m.lower_left],
                            [float(x) for x in m.upper_right])
    return None
