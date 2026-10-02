# -*- coding: utf-8 -*-
"""
 test_h2_esdegerlik.py  --  v3 H2 kabul: eski Model.plot cizimi ile yeni
                            (cizim iscisi + kendi boyamamiz) malzeme haritasi
                            esdeger. Nokta orneklemesi: (1) piksel renkleri
                            Model.plot goruntusuyle ayni, (2) piksel merkezindeki
                            malzeme openmc.Geometry.find ile bagimsiz denetlenir.
"""

import os

import numpy as np

from testler.ortak_test import kontrol, ORNEK

# 2B kare, 3B (xz), kafes + tambur, altigen demet, plaka kor, tamburlu kor
ORNEKLER = ("pwr_17x17", "pwr_3b", "kafes_tamburlu_yansitici", "vver1000_demet", "mtr_kor",
            "tamburlu_kor")
_PIKSEL = 200
_ORNEK_SAYISI = 400            # kesit basina rastgele piksel
_FIND_SAYISI = 12              # kesit basina Geometry.find ile denetlenen nokta
_TOHUM = 20261002


def _eski_goruntu(model, bilgi, eksen, genislik):
    """v2 onizlemesinin cagrisi (arayuz/onizleme.py, v2.0.0): RGB (0-1)."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.figure import Figure
    ax = Figure().add_subplot(111)
    model.plot(basis=eksen, width=genislik, pixels=(_PIKSEL, _PIKSEL), color_by="material",
               colors=bilgi["renkler"], axes=ax)
    return np.asarray(ax.images[0].get_array(), dtype=float)[..., :3]


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


def _find_malzemesi(model, nokta):
    """Noktadaki en derin hucrenin malzeme kimligi; bosluk -1, hucre yok -2."""
    import openmc
    yol = model.geometry.find(nokta)
    hucreler = [n for n in yol if isinstance(n, openmc.Cell)]
    if not hucreler:
        return -2
    dolgu = hucreler[-1].fill
    return dolgu.id if isinstance(dolgu, openmc.Material) else -1


def _nokta(eksen, genislik, i, j):
    w, h = genislik
    a = -w / 2 + (j + 0.5) * w / _PIKSEL
    b = h / 2 - (i + 0.5) * h / _PIKSEL
    return {"xy": (a, b, 0.0), "xz": (a, 0.0, b), "yz": (0.0, a, b)}[eksen]


def _sinir_pikseli_mi(kanal, i, j):
    """Komsusu farkli malzeme olan piksel: merkez noktasi yuzeye cok yakin
    olabilir; Geometry.find ile openmc.lib ayni sinirda farkli yuvarlayabilir."""
    parca = kanal[max(i - 1, 0):i + 2, max(j - 1, 0):j + 2]
    return bool((parca != kanal[i, j]).any())


def _bir_kesit(ad, spec, model, bilgi, eksen, rng):
    from arayuz import onizleme_boyama as ob
    from cekirdek import cizim_sureci as cs, sema
    genislik = cs.kesit_genisligi(eksen, bilgi["sinir_kutu"], sema.model_yuksekligi(spec))
    eski = _eski_goruntu(model, bilgi, eksen, genislik)
    yeni_genislik, geom, renkler = _yeni_harita(spec, eksen)
    yeni = ob.malzeme_goruntusu(geom, renkler, (1.0, 0.0, 0.0)).astype(float) / 255.0
    saydam = yeni[..., 3] == 0                      # hucre yok: Model.plot'ta beyaz
    yeni_rgb = np.where(saydam[..., None], 1.0, yeni[..., :3])
    ii = rng.integers(0, _PIKSEL, _ORNEK_SAYISI)
    jj = rng.integers(0, _PIKSEL, _ORNEK_SAYISI)
    renk_ayni = np.allclose(eski[ii, jj], yeni_rgb[ii, jj], atol=1.0 / 255)
    kanal = geom[..., 2]
    adaylar = [(i, j) for i, j in zip(ii, jj) if not _sinir_pikseli_mi(kanal, i, j)]
    denetlenen = adaylar[:_FIND_SAYISI]
    farkli = [(i, j, int(kanal[i, j]), _find_malzemesi(model, _nokta(eksen, genislik, i, j)))
              for i, j in denetlenen]
    farkli = [f for f in farkli if f[2] != f[3]]
    kontrol("%s %s: genislik ayni" % (ad, eksen), np.allclose(yeni_genislik, genislik))
    cesit = len(set(kanal[ii, jj].tolist()))
    kontrol("%s %s: orneklem anlamli (>= 2 farkli malzeme)" % (ad, eksen), cesit >= 2,
            "-> %d" % cesit)
    kontrol("%s %s: %d ornek pikselde renk Model.plot ile ayni" % (ad, eksen, _ORNEK_SAYISI),
            renk_ayni)
    kontrol("%s %s: %d noktada malzeme Geometry.find ile ayni" % (ad, eksen, len(denetlenen)),
            len(denetlenen) >= 5 and not farkli, "-> %s" % farkli[:3])


def test_malzeme_haritasi_esdeger():
    print("\n[H2E-1] eski Model.plot ile yeni cizim: malzeme haritasi esdeger (%d ornek)"
          % len(ORNEKLER))
    from cekirdek import cizim_sureci as cs, kurucu, sema
    rng = np.random.default_rng(_TOHUM)
    eski_dizin = os.getcwd()
    try:
        for ad in ORNEKLER:
            spec = sema.yukle(os.path.join(ORNEK, ad + ".json"))
            model, bilgi = kurucu.kur(spec)
            model = cs.cizim_modeli(model)
            eksenler = ("xy", "xz") if sema.model_yuksekligi(spec) else ("xy",)
            for eksen in eksenler:
                _bir_kesit(ad, spec, model, bilgi, eksen, rng)
    finally:
        os.chdir(eski_dizin)


HIZLI = [test_malzeme_haritasi_esdeger]
YAVAS = []
VERI_GEREKEN = [test_malzeme_haritasi_esdeger]     # eski yol (Model.plot, '-c') veri ister
