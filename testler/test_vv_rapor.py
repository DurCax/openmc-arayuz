# -*- coding: utf-8 -*-
"""
test_vv_rapor.py -- araclar/vv_rapor.py (v3 Y11): VV.md tablolari JSON'dan.

  [VR1] deney_satiri: C %.5f, parcacik, tipografik eksi, kabul sonucu (3 σ).
  [VR2] tabloya_yerlestir: bolumdeki tabloda ayni dosyanin satiri degisir, yenisi
        sirali yere eklenir; baska satirlar ve tablo disi metin degismez.
"""

import importlib.util
import os

from testler.ortak_test import kontrol, KOK


def _arac():
    yol = os.path.join(KOK, "araclar", "vv_rapor.py")
    spec = importlib.util.spec_from_file_location("vv_rapor", yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _ham(k, s=0.0003):
    return {"referans": {"k": 1.0, "sigma": 0.002, "kaynak": "ICSBEP LEU-COMP-THERM-006, durum 3 (TCA)",
                         "olcum": {"k": k, "sigma": s, "parcacik": 100000, "cevrim": 200,
                                   "pasif": 50, "sure_s": 600.0}}}


def test_deney_satiri():
    print("\n[VR1] deney_satiri")
    arac = _arac()
    satir = arac.deney_satiri("vv/kriter_lct006_03.json", _ham(0.99870), "tr")
    kontrol("C %.5f", "0.99870 ± 0.00030" in satir, "-> %s" % satir)
    kontrol("parcacik", "| 100000 |" in satir)
    kontrol("tipografik eksi", "| −130 |" in satir, "-> %s" % satir)
    kontrol("kabul gecti", satir.endswith("| geçti |"))
    kontrol("seri adi", "| LEU-COMP-THERM-006, durum 3 |" in satir, "-> %s" % satir)
    kontrol("EN", arac.deney_satiri("vv/x.json", _ham(1.0), "en").endswith("| passed |"))
    kontrol("3 σ disi kaldi", arac.deney_satiri("vv/x.json", _ham(1.01), "tr").endswith("| kaldı |"))


METIN = """# Baslik

## Deney kriterleri (C/E)

| Örnek | Kriter |
|---|---|
| vv/kriter_hst009a.json | eski |
| vv/kriter_lct006_01.json | ESKI |
| vv/kriter_pmf008.json | p |

Notlar: metin.

## Hesap-hesap kriterleri

| Örnek | x |
|---|---|
| a.json | y |
"""


def test_tabloya_yerlestir():
    print("\n[VR2] tabloya_yerlestir")
    arac = _arac()
    yeni = arac.tabloya_yerlestir(METIN, "## Deney kriterleri (C/E)",
                                  ["| vv/kriter_lct006_01.json | YENI |",
                                   "| vv/kriter_lct006_02.json | YENI2 |"])
    satirlar = yeni.splitlines()
    kontrol("eski satir degisti", "| vv/kriter_lct006_01.json | YENI |" in satirlar
            and "| vv/kriter_lct006_01.json | ESKI |" not in satirlar)
    i = satirlar.index("| vv/kriter_lct006_02.json | YENI2 |")
    kontrol("sirali yer", satirlar[i - 1].startswith("| vv/kriter_lct006_01")
            and satirlar[i + 1].startswith("| vv/kriter_pmf008"), "-> %s" % satirlar[i - 1:i + 2])
    kontrol("tablo disi metin ayni", "Notlar: metin." in yeni and "| a.json | y |" in yeni)
    kontrol("idempotent", arac.tabloya_yerlestir(yeni, "## Deney kriterleri (C/E)",
                                                 ["| vv/kriter_lct006_02.json | YENI2 |"]) == yeni)


HIZLI = [test_deney_satiri, test_tabloya_yerlestir]
YAVAS = []
