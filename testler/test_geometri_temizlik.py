# -*- coding: utf-8 -*-
"""
 test_geometri_temizlik.py  --  Dalga G temizlik: kurucu sarmalayicilari gitti,
 tuketiciler geometri API'sinde; sinir formu / yeniden adlandirma G-2 API'sinde;
 guc haritasi yeni anahtar parcalari; onizleme vurgusu.

 Ucu de agac modu sablonlariyla (arayuz/geometri/sablonlar.uret) sinanir; MC yok.
 Sozlesme: testler/ortak_test.py.
"""

import os
import re

from testler.ortak_test import KOK, ORNEK, kontrol

SABLONLAR = (("pwr_ceyrek_kor", "kare_altigen"), ("sfr_altigen", "altigen_tambur"),
             ("pwr_ceyrek_kor", "kafes_tambur"))
SILINEN = ("kor_kur", "_tek_bilesen", "cubuk_universe", "plaka_universe", "_altigen_sinir",
           "aktif_eksenel_aralik", "cubuk_eksenel_aralik", "guc_eksenel_araligi",
           "guc_yuksekligi", "_spec_fisil_mi", "_iceriyor_mu", "_guc_hedef_adlari",
           "kor_ic_olcusu")


def agac_specleri():
    """[(sablon anahtari, agac modundaki spec)] -- uc yeni sablon."""
    from cekirdek import sema
    from arayuz.geometri import sablonlar
    return [(a, sablonlar.uret(sema.yukle(os.path.join(ORNEK, o + ".json")), a))
            for o, a in SABLONLAR]


def _kaynaklar():
    for kok_dizin in ("arayuz", "cekirdek", "testler"):
        for dizin, _alt, dosyalar in os.walk(os.path.join(KOK, kok_dizin)):
            for d in dosyalar:
                if d.endswith(".py"):
                    yol = os.path.join(dizin, d)
                    with open(yol, encoding="utf-8") as f:
                        yield os.path.relpath(yol, KOK), f.read()


def test_kurucu_sarmalayicilari_silindi():
    print("\n[GT1] kurucu sarmalayicilari silindi; cagiran kalmadi")
    from cekirdek import kurucu
    kalan = [a for a in SILINEN if hasattr(kurucu, a)]
    kontrol("kurucu'da sarmalayici yok", not kalan, "-> %s" % kalan)
    desen = re.compile(r"\b(?:kurucu|_kur|_k)\.(%s)\(" % "|".join(SILINEN))
    cagri = ["%s: %s" % (yol, e.group(0)) for yol, metin in _kaynaklar()
             if not yol.endswith("test_geometri_temizlik.py")
             for e in desen.finditer(metin)]
    kontrol("hicbir modul sarmalayici cagirmiyor", not cagri, "-> %s" % cagri[:5])


def test_agac_modu_tuketicileri():
    print("\n[GT2] guc_harita / katman ozeti / cubuk ucu agac modunda geometri API'siyle")
    from PySide6 import QtWidgets
    from cekirdek import geometri
    from arayuz import guc_harita
    from arayuz.sekme_cubuk import CubukSekmesi
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    for anahtar, spec in agac_specleri():
        kontrol("%s: guc paydasi = geometri.hedef_yuksekligi" % anahtar,
                guc_harita._aktif_yukseklik(spec) == geometri.hedef_yuksekligi(spec))
        w = CubukSekmesi()
        w.spec_yukle(spec)
        w._uc_guncelle()
        ar = geometri.aktif_aralik(spec)
        metin = w.c_uc_etiket.text()
        kontrol("%s: kontrol ucu etiketi aktif araliktan" % anahtar,
                ar is None or ("%+.1f" % ar[1]) in metin, "-> %s / %s" % (metin, ar))


HIZLI = [test_kurucu_sarmalayicilari_silindi, test_agac_modu_tuketicileri]
YAVAS = []
