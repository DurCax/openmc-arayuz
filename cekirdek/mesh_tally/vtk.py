# -*- coding: utf-8 -*-
"""
 cekirdek/mesh_tally/vtk.py  --  ParaView icin VTK dosyasi (v3 Y1)

 Python `vtk` paketi kuruluysa OpenMC'nin kendi yazicisi kullanilir
 (Mesh.write_data_to_vtk, volume_normalization=False: normalizasyonu biz
 yapariz). Kurulu degilse (openmc-env'de yok; yeni calisma zamani bagimliligi
 EKLENMEZ) ayni bicimde yerlesik yazici: legacy ASCII "STRUCTURED_GRID",
 noktalar OpenMC'nin _create_vtk_structured_grid sirasinda (i en hizli),
 hucre verisi dataset.T.ravel() sirasinda. Egri yuzlu (curvilinear) hucre
 YAZILMAZ -- OpenMC'nin varsayilani da duz kenarli altiyuzlulerdir.

 Alanlar: her skor ve grup icin <skor>_g<n> (+ _toplam), _sigma, _bagil_hata.
"""

import re

import numpy as np

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from cekirdek.mesh_tally import geometri as _geo
from cekirdek.mesh_tally import sonuc as _snc

_log = kaydedici(__name__)


def _alan_adi(metin):
    """VTK alan adi: bosluk ve ozel karakter yok."""
    return re.sub(r"[^A-Za-z0-9_]+", "_", metin).strip("_")


def alanlar(sonuc, yontem="hacim", kaynak_hizi=None, nuklid=0):
    """{alan adi: 3B dizi} -- her skor, grup ve gruplarin toplami (yeni sozluk)."""
    hacim = _geo.hacimler(sonuc.tur, sonuc.izgaralar)
    # Tek grupta yalniz "toplam"; cok grupta her grup + toplam.
    gruplar = ([None] if sonuc.grup_sayisi == 1
               else list(range(sonuc.grup_sayisi)) + [None])
    cikti = {}
    for skor in sonuc.skorlar:
        for g in gruplar:
            o, s = _snc.secim(sonuc, skor, g, nuklid)
            o, s, _b = _snc.normalize(o, s, hacim, yontem, kaynak_hizi, skor, sonuc.ozdeger)
            ad = _alan_adi("%s_%s" % (skor, "toplam" if g is None else "g%d" % (g + 1)))
            cikti[ad] = o
            cikti[ad + "_sigma"] = s
            cikti[ad + "_bagil_hata"] = np.nan_to_num(_snc.bagil_hata(o, s), nan=0.0)
    return cikti


def _vtk_var():
    try:
        import vtk  # noqa: F401
    except ImportError:
        _log.info("Python 'vtk' paketi yok; yerleşik VTK yazıcısı kullanılıyor")
        return False
    return True


def mesh_nesnesi(sonuc):
    """MeshSonuc'tan openmc mesh nesnesi (OpenMC yazicisi icin)."""
    import openmc
    g = sonuc.izgaralar
    if sonuc.tur == "duzenli":
        m = openmc.RegularMesh()
        m.dimension = list(sonuc.boyut)
        m.lower_left = [float(x[0]) for x in g]
        m.upper_right = [float(x[-1]) for x in g]
        return m
    if sonuc.tur == "silindirik":
        return openmc.CylindricalMesh(r_grid=g[0], phi_grid=g[1], z_grid=g[2],
                                      origin=list(sonuc.merkez))
    return openmc.SphericalMesh(r_grid=g[0], theta_grid=g[1], phi_grid=g[2],
                                origin=list(sonuc.merkez))


def _yerlesik_yaz(sonuc, yol, veri):
    noktalar = _geo.koseler(sonuc.tur, sonuc.izgaralar, sonuc.merkez)
    n1, n2, n3 = sonuc.boyut
    satirlar = ["# vtk DataFile Version 3.0", "openmc_arayuz mesh tally: %s" % _alan_adi(
        sonuc.ad), "ASCII", "DATASET STRUCTURED_GRID",
        "DIMENSIONS %d %d %d" % (n1 + 1, n2 + 1, n3 + 1),
        "POINTS %d double" % len(noktalar)]
    satirlar += ["%.17g %.17g %.17g" % tuple(p) for p in noktalar]
    satirlar.append("CELL_DATA %d" % (n1 * n2 * n3))
    for ad, dizi in veri.items():
        satirlar += ["SCALARS %s double 1" % ad, "LOOKUP_TABLE default"]
        satirlar += ["%.17g" % x for x in np.asarray(dizi, dtype=float).T.ravel()]
    with open(yol, "w", encoding="ascii") as f:
        f.write("\n".join(satirlar) + "\n")


def vtk_yaz(sonuc, yol, yontem="hacim", kaynak_hizi=None, nuklid=0, yerlesik=None):
    """
    Sonucu VTK dosyasina yazar; yazilan alan adlarini dondurur.
    yerlesik: True -> her zaman yerlesik yazici; None -> vtk paketi varsa OpenMC.
    Yazma hatasi OSError olarak yukari cikar (arayuz gosterir).
    """
    veri = alanlar(sonuc, yontem, kaynak_hizi, nuklid)
    if not str(yol).lower().endswith(".vtk"):
        raise ValueError(_("VTK dosya adı .vtk ile bitmeli: %s") % yol)
    if yerlesik is None:
        yerlesik = not _vtk_var()
    if yerlesik:
        _yerlesik_yaz(sonuc, yol, veri)
    else:
        mesh_nesnesi(sonuc).write_data_to_vtk(str(yol), datasets=veri,
                                              volume_normalization=False)
    return list(veri)
