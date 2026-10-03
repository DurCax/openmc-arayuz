# -*- coding: utf-8 -*-
"""
 test_h2_esdegerlik.py  --  v3 H2 kabul: eski Model.plot cizimi ile yeni
                            (cizim iscisi + kendi boyamamiz) esdeger.

 (1) test_malzeme_haritasi_esdeger (veri ister: eski yol '-c'): 200 px'te TUM
     goruntu Model.plot ile piksel piksel ayni (malzeme ve hucre kipi); kapsam
     (genislik + merkez) Model.plot'un kendi hesapladigi extent ile ayni.
 (2) test_id_haritasi_geometri_ile_ayni (veri GEREKMEZ, CI'da da kosar): iscinin
     ('-p') id haritasi, piksel merkezlerinde openmc.Geometry.find ile bagimsiz
     denetlenir; -1 (bosluk malzemesi) ve -2 (hucre yok) ayrimi ayrica sinanir.
"""

import os
import time

import numpy as np

from testler.ortak_test import kontrol, ORNEK
from testler.ortak_test import gereksinim  # v3 izlenebilirlik

# 2B kare, 3B (xz), kafes + tambur, altigen demet, plaka kor, tamburlu kor
ORNEKLER = ("pwr_17x17", "pwr_3b", "kafes_tamburlu_yansitici", "vver1000_demet", "mtr_kor",
            "tamburlu_kor")
# veri gerektirmeyen denetim: + bosluk (-1) ve hucre yok (-2) iceren SFR koru
ORNEKLER_VERISIZ = ORNEKLER + ("sfr_met1000_kor",)
_PIKSEL = 200
_FIND_SAYISI = 12              # kesit basina Geometry.find ile denetlenen ic nokta
_KOD_SAYISI = 5                # kesit basina denetlenen -1 / -2 pikseli
_TOHUM = 20261002


def _eski(model, bilgi, eksen, genislik, renk_kipi):
    """v2 onizlemesinin cagrisi (arayuz/onizleme.py, v2.0.0): (RGB 0-1, extent)."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure
    ax = Figure().add_subplot(111)
    model.plot(basis=eksen, width=genislik, pixels=(_PIKSEL, _PIKSEL), color_by=renk_kipi,
               colors=bilgi["renkler"] if renk_kipi == "material" else None, axes=ax)
    im = ax.images[0]
    return np.asarray(im.get_array(), dtype=float)[..., :3], tuple(im.get_extent())


def _yeni_harita(spec, eksen):
    from cekirdek import cizim_sureci as cs
    oturum = cs.Oturum()
    eski_dizin = os.getcwd()
    try:
        oturum.hazirla(spec)
        genislik, geom, _c = oturum.kesit(eksen, _PIKSEL)
        renkler = {int(k): v for k, v in oturum.ozellikler()["renkler"].items()}
    finally:
        oturum.kapat()
        os.chdir(eski_dizin)
    return genislik, geom, renkler


def _rgb(rgba_bayt):
    """Yeni RGBA (uint8) -> Model.plot'un RGB'si: saydam (hucre yok) beyazdi."""
    yeni = rgba_bayt.astype(float) / 255.0
    return np.where((yeni[..., 3] == 0)[..., None], 1.0, yeni[..., :3])


def _bir_kesit(ad, spec, model, bilgi, eksen):
    from arayuz import onizleme_boyama as ob
    from arayuz.onizleme import _kapsam
    from cekirdek import cizim_sureci as cs, sema
    genislik = cs.kesit_genisligi(eksen, bilgi["sinir_kutu"], sema.model_yuksekligi(spec))
    eski_m, kapsam_eski = _eski(model, bilgi, eksen, genislik, "material")
    eski_h, _k = _eski(model, bilgi, eksen, genislik, "cell")
    yeni_genislik, geom, renkler = _yeni_harita(spec, eksen)
    yeni_m = _rgb(ob.malzeme_goruntusu(geom, renkler, (1.0, 0.0, 0.0)))
    yeni_h = _rgb(ob.hucre_goruntusu(geom))
    kontrol("%s %s: kapsam (genislik + merkez) Model.plot extent'i ile ayni" % (ad, eksen),
            np.allclose(_kapsam(yeni_genislik), kapsam_eski), "-> %s / %s"
            % (_kapsam(yeni_genislik), kapsam_eski))
    cesit = len(np.unique(geom[..., 2]))
    kontrol("%s %s: goruntu anlamli (>= 2 farkli malzeme)" % (ad, eksen), cesit >= 2)
    fark_m = int((np.abs(eski_m - yeni_m) > 1.0 / 255).any(axis=-1).sum())
    fark_h = int((np.abs(eski_h - yeni_h) > 1.0 / 255).any(axis=-1).sum())
    kontrol("%s %s: malzeme kipi tum %d piksel ayni" % (ad, eksen, _PIKSEL ** 2), fark_m == 0,
            "-> %d farkli" % fark_m)
    kontrol("%s %s: hucre kipi tum %d piksel ayni" % (ad, eksen, _PIKSEL ** 2), fark_h == 0,
            "-> %d farkli" % fark_h)


@gereksinim("R-V3-12")
def test_malzeme_haritasi_esdeger():
    print("\n[H2E-1] eski Model.plot ile yeni cizim: tum goruntu esdeger (%d ornek)"
          % len(ORNEKLER))
    from cekirdek import cizim_sureci as cs, kurucu, sema
    eski_dizin = os.getcwd()
    try:
        for ad in ORNEKLER:
            spec = sema.yukle(os.path.join(ORNEK, ad + ".json"))
            model, bilgi = kurucu.kur(spec)
            model = cs.cizim_modeli(model)
            for eksen in (("xy", "xz") if sema.model_yuksekligi(spec) else ("xy",)):
                _bir_kesit(ad, spec, model, bilgi, eksen)
    finally:
        os.chdir(eski_dizin)


# ----------------------------------------------------------------------------
# veri gerektirmeyen denetim: isci + Geometry.find
# ----------------------------------------------------------------------------

def _find(model, nokta):
    """Noktadaki en derin hucrenin malzeme kimligi; bosluk -1, hucre yok -2."""
    import openmc
    hucreler = [n for n in model.geometry.find(nokta) if isinstance(n, openmc.Cell)]
    if not hucreler:
        return -2
    dolgu = hucreler[-1].fill
    return dolgu.id if isinstance(dolgu, openmc.Material) else -1


def _nokta(eksen, genislik, i, j):
    w, h = genislik
    a = -w / 2 + (j + 0.5) * w / _PIKSEL
    b = h / 2 - (i + 0.5) * h / _PIKSEL
    return {"xy": (a, b, 0.0), "xz": (a, 0.0, b), "yz": (0.0, a, b)}[eksen]


def _ic_pikseller(kanal, rng, n, secim=None):
    """Komsulari ayni malzeme olan (yuzeyden uzak) rastgele pikseller."""
    i, j = np.nonzero(secim if secim is not None else np.ones_like(kanal, dtype=bool))
    sira = rng.permutation(len(i))
    sonuc = []
    for k in sira:
        a, b = int(i[k]), int(j[k])
        parca = kanal[max(a - 1, 0):a + 2, max(b - 1, 0):b + 2]
        if (parca == kanal[a, b]).all():
            sonuc.append((a, b))
            if len(sonuc) >= n:
                break
    return sonuc


def _isci_kesitleri(istemci, spec, eksenler):
    from testler.test_h2_istemci import _bekle
    gelen = []
    istemci.cerceve_geldi.connect(gelen.append)
    try:
        istemci.iste({"tur": "ciz", "spec": spec,
                      "kesitler": [{"eksen": e, "piksel": _PIKSEL} for e in eksenler]})
        _bekle(lambda: any(c.baslik["tur"] == "son" for c in gelen), 120)
    finally:
        istemci.cerceve_geldi.disconnect(gelen.append)
    return [(c.baslik["eksen"], tuple(c.baslik["genislik"]), c.diziler["geom"])
            for c in gelen if c.baslik["tur"] == "kesit"]


def _kesiti_denetle(ad, model, eksen, genislik, geom, rng, gorulen):
    kanal = geom[..., 2]
    denet = _ic_pikseller(kanal, rng, _FIND_SAYISI)
    for kod in (-1, -2):
        if (kanal == kod).any():
            gorulen.add(kod)
            denet += _ic_pikseller(kanal, rng, _KOD_SAYISI, kanal == kod)
    farkli = [(i, j, int(kanal[i, j]), _find(model, _nokta(eksen, genislik, i, j)))
              for i, j in denet]
    farkli = [f for f in farkli if f[2] != f[3]]
    kontrol("%s %s: %d noktada malzeme / -1 / -2 Geometry.find ile ayni"
            % (ad, eksen, len(denet)), len(denet) >= 5 and not farkli, "-> %s" % farkli[:3])


def test_id_haritasi_geometri_ile_ayni():
    print("\n[H2E-2] isci id haritasi Geometry.find ile ayni; -1 / -2 ayrimi (veri gerekmez)")
    from PySide6 import QtWidgets
    from arayuz.onizleme_istemci import CizimIstemcisi
    from cekirdek import cizim_sureci as cs, kurucu, sema
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    rng = np.random.default_rng(_TOHUM)
    istemci = CizimIstemcisi()
    gorulen = set()
    t0 = time.perf_counter()
    try:
        for ad in ORNEKLER_VERISIZ:
            spec = sema.yukle(os.path.join(ORNEK, ad + ".json"))
            model, _bilgi = kurucu.kur(spec)
            model = cs.cizim_modeli(model)
            eksenler = ("xy", "xz") if sema.model_yuksekligi(spec) else ("xy",)
            for eksen, genislik, geom in _isci_kesitleri(istemci, spec, eksenler):
                _kesiti_denetle(ad, model, eksen, genislik, geom, rng, gorulen)
    finally:
        istemci.kapat()
    kontrol("hem bosluk (-1) hem hucre yok (-2) denetlendi", gorulen == {-1, -2},
            "-> %s (%.1f s)" % (sorted(gorulen), time.perf_counter() - t0))


HIZLI = [test_malzeme_haritasi_esdeger, test_id_haritasi_geometri_ile_ayni]
YAVAS = []
VERI_GEREKEN = [test_malzeme_haritasi_esdeger]     # eski yol (Model.plot, '-c') veri ister
