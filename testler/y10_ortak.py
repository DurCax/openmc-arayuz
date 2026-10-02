# -*- coding: utf-8 -*-
"""
y10_ortak.py -- Y10 testlerinin ortak yardimcilari (test modulu degil).

  sahte_openmc(dizin)    SAHTE openmc ikilisi: `-s N` alir, SAHTE_CEVRIM cevrim
                         satiri basar (OpenMC bicimi), statepoint.N.h5 birakir.
                         Ortam: SAHTE_SURE (cevrim basina s), SAHTE_KOD (cikis
                         kodu), SAHTE_KAYIT (bas/son anlari + OMP_NUM_THREADS),
                         SAHTE_MPI ("yes" ise --version MPI destekli der).
  hazir_dizin(yol)       model.xml'i hazir (spec'siz is) kosu dizini
  sahte_sonuc            kuyruk sonuc kancasi: sabit k (gercek statepoint okumaz)
  kayit_araliklari(...)  [(dizin, bas, son)] baslangic sirasiyla
"""

import copy
import os
import sys
import time

SAHTE_CEVRIM = 5
SAHTE_K = (1.01, 0.002)

_SAHTE = r'''#!{python}
import os, sys, time
arg = sys.argv[1:]
if "--version" in arg or "-v" in arg:
    print("OpenMC version 0.16.0 (sahte)")
    print("MPI enabled:           %s" % os.environ.get("SAHTE_MPI", "no"))
    sys.exit(0)
kayit = os.environ.get("SAHTE_KAYIT")
def yaz(olay):
    if kayit:
        with open(kayit, "a") as f:
            f.write("%s %s %.6f %s\n" % (olay, os.getcwd(), time.time(),
                                         os.environ.get("OMP_NUM_THREADS", "-")))
yaz("bas")
sure = float(os.environ.get("SAHTE_SURE", "0.01"))
n = {n}
print(" ===> K EIGENVALUE SIMULATION <===", flush=True)
for i in range(1, n + 1):
    time.sleep(sure)
    if i <= 2:
        print("  %4d/1    1.00500" % i, flush=True)
    else:
        print("  %4d/1    1.00500    1.01000 +/- 0.00200" % i, flush=True)
kod = int(os.environ.get("SAHTE_KOD", "0"))
if kod == 0:
    open("statepoint.%d.h5" % n, "w").close()
yaz("son")
sys.exit(kod)
'''


def calistirilabilir(yol, icerik):
    """icerik'i yol'a yazar ve calistirilabilir yapar. DONER str(yol)."""
    yol = str(yol)
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(icerik)
    os.chmod(yol, 0o755)
    return yol


def sahte_openmc(dizin):
    return calistirilabilir(os.path.join(str(dizin), "sahte_bin", "openmc"),
                            _SAHTE.replace("{python}", sys.executable)
                            .replace("{n}", str(SAHTE_CEVRIM)))


def hazir_dizin(yol):
    yol = str(yol)
    os.makedirs(yol, exist_ok=True)
    with open(os.path.join(yol, "model.xml"), "w", encoding="utf-8") as f:
        f.write("<model/>\n")
    return yol


def sahte_sonuc(statepoint, is_):
    return {"keff": SAHTE_K, "statepoint": statepoint, "ad": is_.ad}


def _kayitlar(yol):
    if not os.path.isfile(str(yol)):
        return []
    with open(str(yol), encoding="utf-8") as f:
        return [s.split() for s in f if s.strip()]


def kayit_araliklari(yol, yalniz_biten=True):
    bas, son = {}, {}
    for olay, dizin, an, _omp in _kayitlar(yol):
        (bas if olay == "bas" else son)[dizin] = float(an)
    dizinler = [d for d in bas if (d in son or not yalniz_biten)]
    return sorted(((d, bas[d], son.get(d, float("inf"))) for d in dizinler),
                  key=lambda x: x[1])


def kayit_omp(yol):
    return [omp for olay, _d, _a, omp in _kayitlar(yol) if olay == "bas"]


def en_cok_ortusme(araliklar):
    olaylar = sorted([(b, 1) for _d, b, _s in araliklar] + [(s, -1) for _d, _b, s in araliklar],
                     key=lambda x: (x[0], x[1]))
    simdi = en_cok = 0
    for _an, d in olaylar:
        simdi += d
        en_cok = max(en_cok, simdi)
    return en_cok


def bekle_kadar(kosul, sure):
    son = time.monotonic() + sure
    while time.monotonic() < son:
        if kosul():
            return True
        time.sleep(0.02)
    raise AssertionError("kosul %.0f s icinde saglanmadi" % sure)


def kisa_spec(taban, zenginlik=None, parcacik=300, cevrim=12, pasif=4):
    """Hizli gercek kosu icin kisaltilmis spec kopyasi (entropi kapali)."""
    spec = copy.deepcopy(taban)
    spec["ayarlar"].update({"parcacik": parcacik, "cevrim": cevrim, "pasif": pasif})
    spec["ayarlar"]["entropi_mesh"] = {"var": False}
    if zenginlik is not None:
        for m in spec["malzemeler"]:
            for b in m.get("bilesim", []):
                if b.get("zenginlik") is not None:
                    b["zenginlik"] = float(zenginlik)
    return spec
