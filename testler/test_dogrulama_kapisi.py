# -*- coding: utf-8 -*-
"""
test_dogrulama_kapisi.py -- dogrula.kapi(): "hata" bulgusu olan spec kosulmaz.

NEDEN
  Dogrulama yalnizca arayuzun Calistir dugmesinde ve kosucu terminal girisinde
  uygulaniyordu. kosucu.calistir / tukenme.calistir programatik (tarama,
  kritik arama, coklu tohum, betikler) cagrilinca gecersiz bir geometri (or.
  pinleri kesen kilif) sessizce kurulup "basarili" kosuyordu. kapi() tek
  ortak yardimcidir; cagiranlar dosya silmeden ONCE cagirir.
"""

import copy
import os

from testler.ortak_test import kontrol, ORNEK
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik


def _gecerli_spec():
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))


def _hatali_spec():
    s = _gecerli_spec()
    s["ayarlar"]["parcacik"] = 0          # dogrula: parcacik sayisi hatasi
    return s


def test_kapi_hatali_spec():
    print("\n[DK1] DOGRULAMA KAPISI: hata bulgusu -> DogrulamaHatasi")
    from cekirdek import dogrula
    try:
        dogrula.kapi(_hatali_spec(), veri_kontrolu=False)
        kontrol("hatali spec kapidan gecmedi", False, "-> istisna yok")
    except dogrula.DogrulamaHatasi as e:
        kontrol("hatali spec kapidan gecmedi", True)
        kontrol("istisna bulgulari tasiyor",
                bool(e.bulgular) and all(b.seviye == "hata" for b in e.bulgular),
                "-> %s" % [b.seviye for b in e.bulgular])
        kontrol("ValueError alt sinifi (eski yakalayicilar calisir)",
                isinstance(e, ValueError))
        kontrol("mesaj ilk hatanin metnini icerir",
                e.bulgular[0].mesaj in str(e), "-> %s" % e)


def test_kapi_gecerli_spec():
    print("\n[DK2] DOGRULAMA KAPISI: temiz spec gecer, bulgular doner")
    from cekirdek import dogrula
    bulgular = dogrula.kapi(_gecerli_spec(), veri_kontrolu=False)
    kontrol("gecerli spec kapidan gecti, liste dondu", isinstance(bulgular, list))
    kontrol("donen listede hata yok", not dogrula.hata_var(bulgular))


def test_kapi_spec_degistirmez():
    print("\n[DK3] DOGRULAMA KAPISI: spec'i yerinde degistirmez")
    from cekirdek import dogrula
    s = _gecerli_spec()
    once = copy.deepcopy(s)
    dogrula.kapi(s, veri_kontrolu=False)
    kontrol("kapi sonrasi spec ayni", s == once)


@gereksinim("R-A3-01")
def test_ornekler_kapidan_gecer():
    print("\n[DK4] Butun ornekler kapidan gecer (kapi eklenince kosu kirilmaz)")
    import glob
    from cekirdek import dogrula, sema
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        ad = os.path.basename(yol)
        try:
            dogrula.kapi(sema.yukle(yol), veri_kontrolu=False)
            kontrol("%s kapidan gecti" % ad, True)
        except dogrula.DogrulamaHatasi as e:
            kontrol("%s kapidan gecti" % ad, False,
                    "-> %s" % [b.mesaj for b in e.bulgular])


HIZLI = [test_kapi_hatali_spec, test_kapi_gecerli_spec, test_kapi_spec_degistirmez,
         test_ornekler_kapidan_gecer]
YAVAS = []
