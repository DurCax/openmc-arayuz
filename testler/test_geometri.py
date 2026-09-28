# -*- coding: utf-8 -*-
"""
 test_geometri.py  --  3-4. geometri olculeri, cizim, altigen kafes, malzeme ice aktarma

 testler/test_regresyon.py'den tasindi (Dalga 0; test metinleri aynen).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

import os
import tempfile

from cekirdek import sema, kurucu, dogrula
from testler.ortak_test import kontrol
from testler.regresyon_ortak import ORNEK, _ornek_adlari


# ============================================================================
# 3-4. GEOMETRI VE CIZIM
# ============================================================================

def test_geometri_olculeri():
    print("\n[3] Geometri olculeri analitik degerlerle uyusmali")
    beklenen = {
        "pwr_pinhucre": (1.26, 1.26),
        "pwr_17x17": (17 * 1.26, 17 * 1.26),
        # 23 plaka * (2*0.038 + 0.051) + 24 kanal * 0.200  x  6.30 + 2*0.475
        "mtr_plaka": (23 * (2 * 0.038 + 0.051) + 24 * 0.200, 6.30 + 2 * 0.475),
    }
    for ad, (bx, by) in beklenen.items():
        spec = sema.yukle(os.path.join(ORNEK, ad + ".json"))
        _, bilgi = kurucu.kur(spec)
        gx, gy = bilgi["sinir_kutu"]
        uyum = abs(gx - bx) < 1e-9 and abs(gy - by) < 1e-9
        kontrol(ad, uyum, "olculen %.4f x %.4f, beklenen %.4f x %.4f" % (gx, gy, bx, by))


def test_cizim():
    print("\n[4] Model.plot() calismali")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for ad in _ornek_adlari():
        spec = sema.yukle(os.path.join(ORNEK, ad + ".json"))
        model, bilgi = kurucu.kur(spec)
        try:
            model.plot(basis="xy", width=bilgi["sinir_kutu"], pixels=(200, 200),
                       color_by="material", colors=bilgi["renkler"])
            plt.close("all")
            kontrol(ad, True)
        except Exception as e:
            kontrol(ad, False, "-> %s" % e)


# ============================================================================
# 3b. ALTIGEN KAFES
# ============================================================================

def test_altigen_duzen():
    """altigen.py halka duzeni OpenMC'nin show_indices ciktisiyla uyusmali."""
    print("\n[3b] Altigen halka duzeni OpenMC ile uyusmali")
    import openmc
    import re as _re
    from cekirdek import altigen
    for yonelim in ("y", "x"):
        for n in (2, 3, 5):
            metin = openmc.HexLattice.show_indices(n, orientation=yonelim)
            omc = set()
            for satir in metin.split("\n"):
                for m in _re.finditer(r"\((\s*\d+),\s*(\d+)\)", satir):
                    omc.add((int(m.group(1)), int(m.group(2))))
            bizim = set(altigen.konumlar(n, yonelim))
            kontrol("yonelim=%s n=%d (%d hucre)" % (yonelim, n, altigen.toplam_hucre(n)),
                    omc == bizim)


def test_altigen_sinir():
    """HexagonalPrism duvarlari tum pinlere tam yarim adim mesafede olmali."""
    print("\n[3c] Altigen duct olcusu -- yarim adim aciklik")
    import math
    import openmc
    from cekirdek import altigen, kurucu

    def mesafeler(prizma, nokta):
        x, y = nokta
        cikti = []
        for ad in ("plane_max", "plane_min", "upper_right", "lower_left",
                   "upper_left", "lower_right"):
            yuzey = getattr(prizma, ad)
            if isinstance(yuzey, openmc.XPlane):
                a, b, d = 1.0, 0.0, yuzey.x0
            elif isinstance(yuzey, openmc.YPlane):
                a, b, d = 0.0, 1.0, yuzey.y0
            else:
                a, b, d = yuzey.a, yuzey.b, yuzey.d
            cikti.append(abs(d - (a * x + b * y)) / math.hypot(a, b))
        return cikti

    for yonelim in ("y", "x"):
        for n, p in ((2, 0.9), (7, 0.9), (10, 1.3)):
            prizma = kurucu._altigen_sinir(n, p, yonelim, "reflective")
            kon = altigen.konumlar(n, yonelim)
            en_yakin = min(min(mesafeler(prizma, (x * p, y * p)))
                           for x, y in kon.values())
            kontrol("yonelim=%s n=%d adim=%.1f" % (yonelim, n, p),
                    abs(en_yakin - p / 2.0) < 1e-9,
                    "en yakin duvar %.6f, beklenen %.6f" % (en_yakin, p / 2.0))


def test_ice_aktarma():
    """XML'e yazilip geri okunan malzemeler dogrulamadan gecmeli."""
    print("\n[3d] Malzeme ice aktarma (XML -> spec)")
    import tempfile
    from cekirdek import ice_aktar
    for ad in ("pwr_17x17", "sfr_altigen"):
        spec = sema.yukle(os.path.join(ORNEK, ad + ".json"))
        model, _ = kurucu.kur(spec)
        with tempfile.TemporaryDirectory() as gecici:
            yol = os.path.join(gecici, "materials.xml")
            model.materials.export_to_xml(yol)
            aktarilan, _notlar = ice_aktar.malzemeleri_oku(yol)
            yeni = sema.yeni_spec("t")
            yeni["malzemeler"] = aktarilan
            b = dogrula.malzeme_kontrol(yeni) + dogrula.nuklid_kontrol(yeni)
            kontrol("%s (%d malzeme)" % (ad, len(aktarilan)),
                    len(aktarilan) == len(spec["malzemeler"]) and not dogrula.hata_var(b),
                    "(%s)" % dogrula.ozet(b))


HIZLI = [
    test_geometri_olculeri, test_altigen_duzen, test_altigen_sinir, test_ice_aktarma,
    test_cizim,
]
YAVAS = []
