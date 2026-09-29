# -*- coding: utf-8 -*-
"""
uret.py -- testler/veri/kosu_ornek/ fixture'ini YENIDEN URETIR.

Kucuk ama gercek bir kosu dizini: ornekler/pwr_3b.json (17x17 demet, 3B,
guc dagilimi acik) parcacik/cevrim/eksenel dilim sayisi dusurulerek kosulur.
Rapor testleri (testler/test_rapor.py) ve Calistir sonuc panosu (Ajan 8) bu
dizini kullanir: k, sigma, F_dH ve F_q statepoint'ten birebir okunur.

KULLANIM (kok dizinden, openmc-env etkin):
    OMP_NUM_THREADS=8 python testler/veri/kosu_ornek/uret.py

Dizinde kalanlar: spec.json, statepoint.<N>.h5, summary.h5, kosu.log.
(model.xml ve tallies.out silinir: spec.json'dan yeniden uretilebilir.)
Ayni OpenMC surumu + kutuphane + tohum ile sonuc bit duzeyinde ayni cikar.
"""

import copy
import json
import os
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(os.path.dirname(os.path.dirname(BURASI)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

# Kucultme ayarlari (olculdu: ~10 s / 8 is parcacigi; dizin ~0.4 MB)
PARCACIK = 5000
CEVRIM = 40
PASIF = 15
EKSENEL_DILIM = 10
TOHUM = 1
SILINECEKLER = ("model.xml", "tallies.out")


def fixture_spec():
    """ornekler/pwr_3b.json'un kucultulmus kopyasi."""
    from cekirdek import sema
    spec = copy.deepcopy(sema.yukle(os.path.join(KOK, "ornekler", "pwr_3b.json")))
    spec["ad"] = "Rapor fixture'ı — PWR 17×17 3B (küçük koşu)"
    ayar = spec["ayarlar"]
    ayar.update({"parcacik": PARCACIK, "cevrim": CEVRIM, "pasif": PASIF, "tohum": TOHUM})
    ayar["entropi_mesh"] = {"var": True, "boyut": [8, 8, 4]}
    spec["guc_dagilimi"]["eksenel_dilim"] = EKSENEL_DILIM
    spec["calistirma"]["is_parcacigi"] = int(os.environ.get("OMP_NUM_THREADS") or 8)
    return spec


def _logu_anonimlestir(yol):
    """kosu.log'daki ev dizini ve kosu dizini yollarini kisaltir (depoda kisisel
    yol kalmasin)."""
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    metin = metin.replace(BURASI, "testler/veri/kosu_ornek")
    metin = metin.replace(os.path.expanduser("~"), "~")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)


def main():
    from cekirdek import kosucu
    spec = fixture_spec()
    sonuc = kosucu.calistir(spec, BURASI, is_parcacigi=spec["calistirma"]["is_parcacigi"])
    if not sonuc["basarili"]:
        print("koşu başarısız: %s" % sonuc["log"])
        return 1
    for ad in SILINECEKLER:
        yol = os.path.join(BURASI, ad)
        if os.path.exists(yol):
            os.remove(yol)
    _logu_anonimlestir(sonuc["log"])
    with open(os.path.join(BURASI, "spec.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    print("tamam: %s (%.1f s)" % (sonuc["statepoint"], sonuc["sure"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
