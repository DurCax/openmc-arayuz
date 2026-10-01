# -*- coding: utf-8 -*-
"""
 test_geometri_pencere.py  --  gercek ana pencere agac modundaki modeli acar

 Hata (G-2 + G-3 birlesmesi, 01.10.2026): G-3'un testleri agac modundaki
 spec'i yalniz kucuk bir ev sahibi pencerede sinadi; gercek AnaPencere
 _proje_kur ile agac modundaki modeli yuklerken arayuz cagiranlari
 (cubuk_formu, sekme_ayar, guc_harita ...) sema.kor_yuksekligi'ni cagirip
 AgacModuHatasi ile cokuyordu.
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

from testler.ortak_test import kontrol

SABLONLAR = (("pwr_ceyrek_kor", "kare_altigen"), ("sfr_altigen", "altigen_tambur"),
             ("pwr_ceyrek_kor", "kafes_tambur"))


def test_ana_pencere_agac_modunu_acar():
    print("\n[GP1] gercek ana pencere uc agac modu sablonunu acar ve sayfalari gezer")
    from PySide6 import QtWidgets
    from cekirdek import sema
    from arayuz.geometri import sablonlar
    from arayuz.pencere.ana_pencere import AnaPencere
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    for ornek, anahtar in SABLONLAR:
        spec = sablonlar.uret(sema.yukle("ornekler/%s.json" % ornek), anahtar)
        p = AnaPencere()
        try:
            hata = None
            try:
                p._proje_kur(spec, None, None)
                uyg.processEvents()
                for anahtar_s in list(p._sayfalar):   # gizli sayfalar dahil hepsi
                    p.sekmeye_git(anahtar_s, sessiz=True)
                    uyg.processEvents()
                p._kaydet_hepsi() if hasattr(p, "_kaydet_hepsi") else None
            except Exception as e:      # testin amaci cokmeyi raporlamak
                hata = "%s: %s" % (type(e).__name__, e)
            kontrol("%s: pencere agac modundaki modeli acti, butun sayfalari gezdi" % anahtar, hata is None,
                    "-> %s" % hata)
        finally:
            p.close()


HIZLI = [test_ana_pencere_agac_modunu_acar]
YAVAS = []
