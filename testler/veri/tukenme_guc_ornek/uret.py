# -*- coding: utf-8 -*-
"""
uret.py -- testler/veri/tukenme_guc_ornek/ fixture'ini YENIDEN URETIR (v3 K3).

Kucuk ama gercek bir TUKENME kosu dizini: 5x5 PWR demeti (ortada kilavuz
boru), 3B (40 cm, alt/ust vakum, yan yansitici), guc dagilimi acik (4
eksenel dilim). OpenMC depletion her adimin BASINDAKI transportun sonunda
openmc_simulation_n<i>.h5 statepoint'ini yazar (CoupledOperator.write_bos_data);
kurucu.kur'un ekledigi "guc_dagilimi" tally'leri bu dosyalarda bulunur.
testler/test_k3_*.py adim basina pin gucunu bu dizinden okur.

KULLANIM (kok dizinden, openmc-env etkin):
    OMP_NUM_THREADS=6 python testler/veri/tukenme_guc_ornek/uret.py

Dizinde kalanlar: tukenme_spec.json (kosunun spec kaydi), depletion_results.h5,
openmc_simulation_n<i>.h5, summary.h5. Model XML'leri ve son statepoint
silinir (spec'ten yeniden uretilebilir).
"""

import copy
import glob
import os
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(os.path.dirname(os.path.dirname(BURASI)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

# Kucultme ayarlari: hiz icin (fixture fizik dogrulugu iddia etmez)
PARCACIK = 1000
CEVRIM = 25
PASIF = 8
TOHUM = 1
YUKSEKLIK = 40.0           # cm
EKSENEL_DILIM = 4
ADIMLAR = [2.0, 8.0]       # gun
GUC_YOGUNLUGU = 40.0       # W/gHM (PWR tipik)
HARITA = ["yyyyy", "yyyyy", "yykyy", "yyyyy", "yyyyy"]
SILINECEKLER = ("materials.xml", "geometry.xml", "settings.xml", "tallies.xml",
                "model.xml", "tallies.out")


def fixture_spec():
    """ornekler/pwr_3b.json'dan 5x5, 40 cm, kisa tukenme."""
    from cekirdek import sema
    spec = copy.deepcopy(sema.yukle(os.path.join(KOK, "ornekler", "pwr_3b.json")))
    spec["ad"] = "K3 fixture'ı — 5×5 PWR 3B tükenme (küçük koşu)"
    spec["aciklama"] = "testler/veri/tukenme_guc_ornek/uret.py ile üretildi."
    d = spec["demetler"][0]
    d["boyut"] = [5, 5]
    d["harita"] = list(HARITA)
    d["anahtar"] = {"y": "yakit_cubugu", "k": "kilavuz_boru"}
    spec["kor"]["yukseklik"] = YUKSEKLIK
    ayar = spec["ayarlar"]
    ayar.update({"parcacik": PARCACIK, "cevrim": CEVRIM, "pasif": PASIF, "tohum": TOHUM})
    ayar["entropi_mesh"] = {"var": False, "boyut": [4, 4, 2]}
    spec["guc_dagilimi"]["eksenel_dilim"] = EKSENEL_DILIM
    spec["guc_dagilimi"]["toplam_guc"] = None
    spec["tukenme"] = {
        "var": True, "zincir": "casl_termal", "guc_yogunlugu": GUC_YOGUNLUGU,
        "adimlar": list(ADIMLAR), "adim_birimi": "d", "entegrator": "predictor",
        "malzemeleri_ayir": False, "ek_malzemeler": [],
        "izlenen": ["U235", "Pu239", "Xe135"]}
    spec["calistirma"] = {"is_parcacigi": int(os.environ.get("OMP_NUM_THREADS") or 6),
                          "dizin": "kosu_k3"}
    return spec


def _temizle():
    for ad in SILINECEKLER:
        yol = os.path.join(BURASI, ad)
        if os.path.exists(yol):
            os.remove(yol)
    for yol in glob.glob(os.path.join(BURASI, "statepoint.*.h5")):
        os.remove(yol)


def main():
    from cekirdek import tukenme
    spec = fixture_spec()
    h5, _bilgi = tukenme.calistir(spec, BURASI)
    _temizle()
    sys.stdout.write("tamam: %s\n" % h5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
