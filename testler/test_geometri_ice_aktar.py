# -*- coding: utf-8 -*-
"""
 test_geometri_ice_aktar.py  --  G-2: OpenMC XML geometrisinden agaca (gidis-donus)

 Model kurulur, model.xml'e yazilir, ice_aktar.geometri_oku ile agac modu
 spec'ine cevrilir ve yeniden kurulur: rastgele noktalarda malzeme izi AYNI.
 Taninmayan desen (plaka elemani, kontrol cubugu, R3b altigen tam kor)
 gerekceyle reddedilir. Hizli: 7 duzenek; yavas: butun ornekler.
 Sozlesme: testler/ortak_test.py.
"""

import copy
import glob
import os
import random

from testler.ortak_test import kontrol, ORNEK
from testler import geometri_ortak as go

IZ_NOKTASI = 1500


def _iz(model, bilgi, h, n=IZ_NOKTASI):
    import numpy as np
    from cekirdek.geometri.yoklama import _in
    # malzeme kimligi adla degil bilesimle karsilastirilir (ice aktarilan adlar
    # openmc malzeme adindan turetilir)
    ad = {id(m): tuple((n, round(v, 8)) for n, v in sorted(
        m.get_nuclide_atom_densities().items())) for m in bilgi["malzemeler"].values()}
    gx, gy = bilgi["sinir_kutu"]
    rnd = random.Random(7)
    iz = []
    for _i in range(n):
        p = np.array([rnd.uniform(-gx / 2, gx / 2), rnd.uniform(-gy / 2, gy / 2),
                      rnd.uniform(-h / 2 * 0.999, h / 2 * 0.999) if h else 0.0])
        durum, yol, _q = _in(model.geometry.root_universe, p, True, None)
        iz.append(ad.get(id(yol[-1].fill), "bosluk") if durum == "tamam" and yol else durum)
    return iz


def gidis_donus(spec, dizin):
    """(fark sayisi | None, notlar)."""
    from cekirdek import ice_aktar, kurucu, sema
    model, bilgi = kurucu.kur(copy.deepcopy(spec))
    os.makedirs(dizin, exist_ok=True)
    yol = os.path.join(dizin, "model.xml")
    model.export_to_model_xml(yol)
    parca, notlar = ice_aktar.geometri_oku(yol)
    if parca is None:
        return None, notlar
    yeni = copy.deepcopy(spec)
    yeni.update(parca)
    yeni["guc_dagilimi"] = dict(yeni.get("guc_dagilimi") or {}, var=False)
    yeni["tukenme"] = dict(yeni.get("tukenme") or {}, var=False)
    yeni = sema.tamamla(yeni) if hasattr(sema, "tamamla") else yeni
    model2, bilgi2 = kurucu.kur(copy.deepcopy(yeni))
    bilgi2["sinir_kutu"] = bilgi["sinir_kutu"]
    h = sema.model_yuksekligi(spec)
    a, b = _iz(model, bilgi, h), _iz(model2, bilgi2, h)
    return sum(1 for x, y in zip(a, b) if x != y), notlar


def _dene(ad, spec, gecici):
    try:
        return gidis_donus(spec, os.path.join(gecici, ad))
    except Exception as e:     # noqa: BLE001 -- test: her hata raporlanir
        return None, ["%s: %s" % (type(e).__name__, e)]


def test_gidis_donus_hizli():
    print("\n[GI1] disa aktar -> ice aktar (agac) -> ayni malzeme izi; taninmayan desen reddedilir")
    import tempfile
    from cekirdek import sema
    gecici = tempfile.mkdtemp(prefix="g2_ice_")
    duzenekler = [(a, sema.yukle(os.path.join(ORNEK, a + ".json")))
                  for a in ("pwr_pinhucre", "godiva_kriter", "pwr_17x17", "tamburlu_kor")]
    duzenekler += [("a", go.duzenek_a()), ("c", go.duzenek_c()), ("e", go.duzenek_e_ceyrek())]
    for ad, spec in duzenekler:
        fark, notlar = _dene(ad, spec, gecici)
        kontrol("(%s) gidis-donus: %d noktada malzeme ayni" % (ad, IZ_NOKTASI), fark == 0,
                "-> fark %s; %s" % (fark, notlar[-1:]))
    for ad, parca in (("vver1000_kor", "R3b"), ("mtr_plaka", "plaka")):
        fark, notlar = _dene(ad, sema.yukle(os.path.join(ORNEK, ad + ".json")), gecici)
        kontrol("(%s) gerekceyle reddedilir (%s)" % (ad, parca),
                fark is None and parca in notlar[-1], "-> %s" % notlar[-1:])


def test_yavas_gidis_donus_butun(gecici):
    print("\n[GI2] butun ornekler: donusturulebilenler ayni, digerleri gerekceli red")
    from cekirdek import sema
    ayni, red = [], []
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        ad = os.path.splitext(os.path.basename(yol))[0]
        fark, notlar = _dene(ad, sema.yukle(yol), gecici)
        if fark is None:
            red.append((ad, notlar[-1]))
            kontrol("(%s) red gerekceli" % ad, "içe aktarılamadı" in notlar[-1] or
                    "aktarılmıyor" in notlar[-1], "-> %s" % notlar[-1])
        else:
            ayni.append(ad)
            kontrol("(%s) gidis-donus ayni" % ad, fark == 0, "-> fark %d" % fark)
    print("  donusen %d, reddedilen %d: %s" % (len(ayni), len(red), [a for a, _n in red]))


HIZLI = [test_gidis_donus_hizli]
YAVAS = [test_yavas_gidis_donus_butun]
