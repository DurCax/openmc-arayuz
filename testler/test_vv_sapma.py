# -*- coding: utf-8 -*-
"""
test_vv_sapma.py -- PMF-008 / USI-001 sapma duyarlilik varyantlari (v3 Y11;
araclar/vv_sapma_duyarlilik.py). Monte Carlo KOSULMAZ.

  [VS1] sab_kaldir: yalniz adi verilen malzemenin S(a,b) listesi bosalir; girdi
        degismez; bilinmeyen malzeme ValueError.
  [VS2] sicaklik_ata: butun malzemeler verilen sicaklikta; girdi degismez.
  [VS3] Varyant listesi: ozgun (mit-crpg) ve spec varyantlari ayrik; USI-001
        varyantlari kriter dosyasindaki malzeme adlariyla kurulabilir.
"""

import copy
import importlib.util
import os

from testler.ortak_test import kontrol, KOK


def _arac():
    yol = os.path.join(KOK, "araclar", "vv_sapma_duyarlilik.py")
    spec = importlib.util.spec_from_file_location("vv_sapma_duyarlilik", yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _spec():
    return {"malzemeler": [{"ad": "a", "sab": ["c_H_in_H2O"], "sicaklik": 293.6},
                           {"ad": "b", "sab": ["c_Be"], "sicaklik": 293.6}]}


def test_sab_kaldir():
    print("\n[VS1] sab_kaldir")
    arac = _arac()
    girdi = _spec()
    once = copy.deepcopy(girdi)
    yeni = arac.sab_kaldir(girdi, "a")
    kontrol("a bos", yeni["malzemeler"][0]["sab"] == [])
    kontrol("b korunur", yeni["malzemeler"][1]["sab"] == ["c_Be"])
    kontrol("girdi degismez", girdi == once)
    try:
        arac.sab_kaldir(girdi, "yok")
        reddedildi = False
    except ValueError:
        reddedildi = True
    kontrol("bilinmeyen malzeme ValueError", reddedildi)


def test_sicaklik_ata():
    print("\n[VS2] sicaklik_ata")
    arac = _arac()
    girdi = _spec()
    yeni = arac.sicaklik_ata(girdi, 300.0)
    kontrol("hepsi 300 K", all(m["sicaklik"] == 300.0 for m in yeni["malzemeler"]))
    kontrol("girdi degismez", girdi["malzemeler"][0]["sicaklik"] == 293.6)


def test_varyantlar_kurulur():
    print("\n[VS3] varyant listesi ayrik; USI-001 varyantlari kurulur")
    arac = _arac()
    kontrol("ayrik", not set(arac.OZGUN) & set(arac.SPEC_VARYANTLARI))
    for ad, uret in arac.SPEC_VARYANTLARI.items():
        spec = uret()
        kontrol("%s kuruldu" % ad, bool(spec["malzemeler"]))
    h_yok = arac.SPEC_VARYANTLARI["usi001_sab_h_yok"]()
    cozelti = [m for m in h_yok["malzemeler"] if m["ad"] == "ieu_flouride_solution"][0]
    kontrol("cozeltide S(a,b) yok", cozelti["sab"] == [])


HIZLI = [test_sab_kaldir, test_sicaklik_ata, test_varyantlar_kurulur]
YAVAS = []
