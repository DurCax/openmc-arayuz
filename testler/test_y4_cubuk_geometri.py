# -*- coding: utf-8 -*-
"""
 test_y4_cubuk_geometri.py  --  v3 Y4: cubuk aramasinin geometri butunlugu
                                (cekirdek/tukenme_arama.hareketli_yap; MC yok)

 Model: kontrol cubugu evreninde emici (r < R, uc < z < ust), izleyici
 (r < R, alt < z < uc), USTTE plenum (r < R, z > ust), ALTTA uc tipasi
 (r < R, z < alt) ve disarida su. Inceleme bulgusu (HIGH): dis hucre yalniz
 emicinin radyal kismini alirsa plenum/tipa ile cakisir; iç evren sinirsizdir.

   [Y4-G1] Donusumden hemen sonra (translation = ilk uc) her noktada AYNI
           malzeme (openmc.Geometry.find; translation'i dikkate alir).
   [Y4-G2] Daldirma %0 (uc = z_ust): aktif bolgede izleyici; %100 (uc = z_alt):
           aktif bolgede emici. Iki durumda da plenum, tipa ve su degismez.
   [Y4-G3] Betigin donusumu (kod_uret/tukenme_arama) ayni sonucu verir.
"""

from testler.ortak_test import kontrol

R, ALT, UC, UST = 0.4, -50.0, 10.0, 50.0
NOKTALAR = [(0.0, 0.0, z) for z in (-70.0, -49.0, -20.0, 5.0, 15.0, 49.0, 70.0)] + \
    [(0.6, 0.0, z) for z in (-60.0, 0.0, 60.0)]


def _model():
    import openmc
    m = {ad: openmc.Material(name=ad) for ad in ("emici", "izleyici", "plenum", "tipa", "su")}
    for x in m.values():
        x.add_nuclide("H1", 1.0)
    silindir = openmc.ZCylinder(r=R)
    alt, uc, ust = openmc.ZPlane(ALT), openmc.ZPlane(UC), openmc.ZPlane(UST)
    u = openmc.Universe(cells=[
        openmc.Cell(fill=m["emici"], region=-silindir & +uc & -ust),
        openmc.Cell(fill=m["izleyici"], region=-silindir & -uc & +alt),
        openmc.Cell(fill=m["plenum"], region=-silindir & +ust),
        openmc.Cell(fill=m["tipa"], region=-silindir & -alt),
        openmc.Cell(fill=m["su"], region=+silindir)])
    kutu = openmc.model.RectangularParallelepiped(-1, 1, -1, 1, -100, 100, boundary_type="vacuum")
    kok = openmc.Universe(cells=[openmc.Cell(fill=u, region=-kutu)])
    model = openmc.Model(geometry=openmc.Geometry(kok), materials=openmc.Materials(m.values()))
    return model, m


def _harita(model):
    sonuc = []
    for p in NOKTALAR:
        yol = model.geometry.find(p)
        sonuc.append(yol[-1].fill.name)
    return sonuc


def _cakisma_yok(model):
    """Cubuk evreninde her nokta EN COK bir hucrede (Geometry.find ilk eslesmeyi
    dondurdugu icin cakismayi gizler; burada acikca sayilir)."""
    import numpy as np
    for u in model.geometry.get_all_universes().values():
        if u is model.geometry.root_universe:
            continue
        for p in NOKTALAR:
            say = sum(1 for c in u.cells.values() if c.region is None or np.array(p) in c.region)
            if say > 1:
                return False
    return True


def _tasi(model, idler, z):
    hucreler = model.geometry.get_all_cells()
    for i in idler:
        hucreler[i].translation = (0.0, 0.0, z)


def test_donusum_ayni_geometri():
    print("\n[Y4-G1] donusumden sonra her noktada ayni malzeme")
    from cekirdek import tukenme_arama
    model, m = _model()
    once = _harita(model)
    idler = tukenme_arama.hareketli_yap(model, m["emici"], m["izleyici"])
    kontrol("bir hareketli hucre", len(idler) == 1, repr(idler))
    sonra = _harita(model)
    kontrol("ayni malzemeler: %s" % sonra, once == sonra, "once %s" % once)
    kontrol("cakisma yok (plenum/tipa ile)", _cakisma_yok(model))


def test_daldirma_uclari():
    print("\n[Y4-G2] daldirma %0 ve %100: emici/izleyici dogru sinirlar icinde")
    from cekirdek import tukenme_arama
    model, m = _model()
    idler = tukenme_arama.hareketli_yap(model, m["emici"], m["izleyici"])
    _tasi(model, idler, tukenme_arama.uc_konumu(0.0, ALT, UST))
    h0 = _harita(model)
    kontrol("%%0: aktif bolge izleyici, plenum/tipa/su ayni: %s" % h0,
            h0 == ["tipa", "izleyici", "izleyici", "izleyici", "izleyici", "izleyici", "plenum",
                   "su", "su", "su"])
    _tasi(model, idler, tukenme_arama.uc_konumu(100.0, ALT, UST))
    h1 = _harita(model)
    kontrol("%%100: aktif bolge emici, plenum/tipa/su ayni: %s" % h1,
            h1 == ["tipa", "emici", "emici", "emici", "emici", "emici", "plenum",
                   "su", "su", "su"])


def test_betik_donusumu():
    print("\n[Y4-G3] betik donusumu ayni")
    import openmc
    from cekirdek.kod_uret import tukenme_arama as kt
    model, m = _model()
    once = _harita(model)
    ortam = {"openmc": openmc, "m_emici": m["emici"], "m_izleyici": m["izleyici"]}
    metin = kt._CUBUK_ISLEVI.format(emici="m_emici", izleyici="m_izleyici", z_alt=ALT, z_ust=UST)
    exec(compile(metin, "<betik>", "exec"), ortam)  # nosec B102 - test: uretilen betik parcasi
    ortam["_arama_hazirla"](model)
    kontrol("betik: ayni malzemeler", _harita(model) == once)
    kontrol("betik: cakisma yok", _cakisma_yok(model))


HIZLI = [test_donusum_ayni_geometri, test_daldirma_uclari, test_betik_donusumu]
