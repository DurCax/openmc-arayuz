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

 Alanlar: her skor (cok nuklidli tally'de her nuklid) ve grup icin
 <skor>[_<nuklid>]_g<n> (+ _toplam), _sigma, _bagil_hata. Skorsuz hucrenin
 bagil hatasi SKORSUZ_BAGIL_HATA (-1; arayuzdeki × isaretinin karsiligi).
 Dosya once gecici adla yazilir, sonra os.replace (yarim dosya kalmaz).
"""

import os
import re
import tempfile

import numpy as np

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from cekirdek.mesh_tally import geometri as _geo
from cekirdek.mesh_tally import normalizasyon as _nrm
from cekirdek.mesh_tally import sonuc as _snc

_log = kaydedici(__name__)

SKORSUZ_BAGIL_HATA = -1.0
_BASLIK_SINIRI = 256          # legacy VTK: baslik satiri en cok 256 karakter


def _alan_adi(metin):
    """VTK alan adi: bosluk ve ozel karakter yok."""
    return re.sub(r"[^A-Za-z0-9_]+", "_", metin).strip("_")


def _nuklid_ekleri(sonuc, nuklid):
    if nuklid is not None:
        return [(nuklid, "")]
    if len(sonuc.nuklidler) <= 1:
        return [(0, "")]
    return [(i, "_" + n) for i, n in enumerate(sonuc.nuklidler)]


def alanlar(sonuc, yontem="hacim", kaynak_hizi=None, nuklid=None, eksenel_sonsuz=False):
    """{alan adi: 3B dizi} -- her skor, nuklid, grup ve gruplarin toplami (yeni sozluk).
    nuklid None: tek nuklidde o, cokta hepsi."""
    payda, olcu_turu = _nrm.olcu(sonuc, eksenel_sonsuz)
    # Tek grupta yalniz "toplam"; cok grupta her grup + toplam.
    gruplar = ([None] if sonuc.grup_sayisi == 1
               else list(range(sonuc.grup_sayisi)) + [None])
    cikti = {}
    for skor in sonuc.skorlar:
        for ni, nek in _nuklid_ekleri(sonuc, nuklid):
            for g in gruplar:
                o, s = _snc.secim(sonuc, skor, g, ni)
                o, s, _b = _nrm.normalize(o, s, payda, yontem, kaynak_hizi, skor,
                                          sonuc.ozdeger, olcu_turu)
                ad = _alan_adi("%s%s_%s" % (skor, nek, "toplam" if g is None
                                            else "g%d" % (g + 1)))
                cikti[ad] = o
                cikti[ad + "_sigma"] = s
                cikti[ad + "_bagil_hata"] = np.nan_to_num(
                    _nrm.bagil_hata(o, s), nan=SKORSUZ_BAGIL_HATA)
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


def _yerlesik_yaz(sonuc, f, veri):
    noktalar = _geo.koseler(sonuc.tur, sonuc.izgaralar, sonuc.merkez)
    n1, n2, n3 = sonuc.boyut
    baslik = ("openmc_arayuz mesh tally: %s" % _alan_adi(sonuc.ad))[:_BASLIK_SINIRI]
    f.write("# vtk DataFile Version 3.0\n%s\nASCII\nDATASET STRUCTURED_GRID\n" % baslik)
    f.write("DIMENSIONS %d %d %d\nPOINTS %d double\n" % (n1 + 1, n2 + 1, n3 + 1,
                                                         len(noktalar)))
    np.savetxt(f, noktalar, fmt="%.17g")
    f.write("CELL_DATA %d\n" % (n1 * n2 * n3))
    for ad, dizi in veri.items():
        f.write("SCALARS %s double 1\nLOOKUP_TABLE default\n" % ad)
        np.savetxt(f, np.asarray(dizi, dtype=float).T.ravel(), fmt="%.17g")


def vtk_yolunu_denetle(yol):
    """Yazmadan ONCE: .vtk uzantisi ve yazilabilir ust dizin (OSError/ValueError)."""
    if not str(yol).lower().endswith(".vtk"):
        raise ValueError(_("VTK dosya adı .vtk ile bitmeli: %s") % yol)
    dizin = os.path.dirname(os.path.abspath(str(yol)))
    if not os.path.isdir(dizin) or not os.access(dizin, os.W_OK):
        raise OSError(_("VTK dizini yok ya da yazılamıyor: %s") % dizin)
    return dizin


def vtk_yaz(sonuc, yol, yontem="hacim", kaynak_hizi=None, nuklid=None, yerlesik=None,
            eksenel_sonsuz=False):
    """
    Sonucu VTK dosyasina yazar; yazilan alan adlarini dondurur.
    yerlesik: True -> her zaman yerlesik yazici; None -> vtk paketi varsa OpenMC.
    Yol hesaptan once denetlenir; yazma atomiktir (gecici dosya + os.replace).
    """
    dizin = vtk_yolunu_denetle(yol)
    veri = alanlar(sonuc, yontem, kaynak_hizi, nuklid, eksenel_sonsuz)
    if yerlesik is None:
        yerlesik = not _vtk_var()
    fd, gecici = tempfile.mkstemp(prefix=".mesh_", suffix=".vtk", dir=dizin)
    try:
        if yerlesik:
            with os.fdopen(fd, "w", encoding="ascii") as f:
                _yerlesik_yaz(sonuc, f, veri)
        else:
            os.close(fd)
            mesh_nesnesi(sonuc).write_data_to_vtk(gecici, datasets=veri,
                                                  volume_normalization=False)
        os.replace(gecici, str(yol))
    except BaseException:
        if os.path.exists(gecici):
            os.remove(gecici)
        raise
    return list(veri)
