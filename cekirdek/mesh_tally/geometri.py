# -*- coding: utf-8 -*-
"""
 cekirdek/mesh_tally/geometri.py  --  mesh hucre geometrisi (saf numpy; Qt'siz)

 Hacimler, kartezyen kose noktalari ve 2B dilim koordinatlari. Kurallar
 OpenMC 0.16.0 ile ayni (openmc/mesh.py, _convert_to_cartesian):
   silindirik (r, phi, z): x = r cos(phi) + ox, y = r sin(phi) + oy, z = z + oz
   kuresel (r, theta, phi): x = r sin(theta) cos(phi) + ox,
                            y = r sin(theta) sin(phi) + oy, z = r cos(theta) + oz
 Testler (test_y1_mesh_sonuc) hacmi mesh.volumes ile, kose sirasini
 mesh.vertices ile karsilastirir.
"""

from dataclasses import dataclass

import numpy as np

from cekirdek.ceviri import _
from cekirdek.mesh_tally.tanim import DUZENLI, SILINDIRIK, KURESEL


def mesh_tur_bul(mesh):
    """openmc mesh nesnesinin turu; desteklenmeyen sinif ValueError."""
    ad = type(mesh).__name__
    turler = {"RegularMesh": DUZENLI, "CylindricalMesh": SILINDIRIK,
              "SphericalMesh": KURESEL}
    if ad not in turler:
        raise ValueError(_("desteklenmeyen ağ sınıfı: %s") % ad)
    return turler[ad]


def mesh_izgaralari(mesh):
    """openmc mesh -> (eksen1, eksen2, eksen3) sinir izgaralari (yeni diziler)."""
    tur = mesh_tur_bul(mesh)
    if tur == DUZENLI:
        return tuple(np.linspace(a, u, int(n) + 1) for a, u, n in
                     zip(mesh.lower_left, mesh.upper_right, mesh.dimension))
    if tur == SILINDIRIK:
        return tuple(np.array(g, dtype=float) for g in
                     (mesh.r_grid, mesh.phi_grid, mesh.z_grid))
    return tuple(np.array(g, dtype=float) for g in
                 (mesh.r_grid, mesh.theta_grid, mesh.phi_grid))


def hacimler(tur, izgaralar):
    """Hucre hacimleri [cm3], sekil (n1, n2, n3)."""
    a, b, c = (np.asarray(g, dtype=float) for g in izgaralar)
    if tur == DUZENLI:
        da, db, dc = np.diff(a), np.diff(b), np.diff(c)
    elif tur == SILINDIRIK:
        da, db, dc = np.diff(a ** 2) / 2.0, np.diff(b), np.diff(c)
    elif tur == KURESEL:
        da, db, dc = np.diff(a ** 3) / 3.0, -np.diff(np.cos(b)), np.diff(c)
    else:
        raise ValueError(_("bilinmeyen ağ türü: %s") % tur)
    return da[:, None, None] * db[None, :, None] * dc[None, None, :]


def kartezyen(tur, a, b, c, merkez):
    """Ag koordinatlarini (ayni sekilli diziler) kartezyen (x, y, z)'ye cevirir."""
    ox, oy, oz = merkez
    if tur == DUZENLI:
        return a + 0.0, b + 0.0, c + 0.0
    if tur == SILINDIRIK:
        return a * np.cos(b) + ox, a * np.sin(b) + oy, c + oz
    rxy = a * np.sin(b)
    return rxy * np.cos(c) + ox, rxy * np.sin(c) + oy, a * np.cos(b) + oz


def koseler(tur, izgaralar, merkez):
    """Kose noktalari (N, 3): i en hizli, sonra j, sonra k (VTK STRUCTURED_GRID
    ve OpenMC'nin np.swapaxes(vertices, 0, 2).reshape(-1, 3) sirasi)."""
    a, b, c = np.meshgrid(*izgaralar, indexing="ij")
    x, y, z = kartezyen(tur, a, b, c, merkez)
    noktalar = np.stack([x, y, z], axis=-1)
    return np.swapaxes(noktalar, 0, 2).reshape(-1, 3)


@dataclass(frozen=True)
class Dilim:
    """2B dilim: kose koordinatlari x, y (na+1, nb+1), deger (na, nb), eksen adlari."""
    x: np.ndarray
    y: np.ndarray
    deger: np.ndarray
    x_adi: str
    y_adi: str
    esit_olcek: bool


_DERECE = 180.0 / np.pi


def _dilim_kafesi(tur, izgaralar, eksen, merkez):
    """(x, y, x_adi, y_adi, esit_olcek) -- serbest iki eksenin kose kafesi."""
    serbest = [e for e in range(3) if e != eksen]
    ga, gb = (np.asarray(izgaralar[e], dtype=float) for e in serbest)
    A, B = np.meshgrid(ga, gb, indexing="ij")
    if tur == DUZENLI:
        adlar = ("x [cm]", "y [cm]", "z [cm]")
        return A, B, adlar[serbest[0]], adlar[serbest[1]], True
    if tur == SILINDIRIK:
        if eksen == 2:      # (r, phi) -> kartezyen duzlem
            return (A * np.cos(B) + merkez[0], A * np.sin(B) + merkez[1],
                    "x [cm]", "y [cm]", True)
        if eksen == 1:      # (r, z)
            return A, B + merkez[2], "r [cm]", "z [cm]", True
        return A * _DERECE, B + merkez[2], "φ [°]", "z [cm]", False
    if eksen == 2:          # kuresel (r, theta): meridyen duzlemi (rho, z)
        return A * np.sin(B), A * np.cos(B) + merkez[2], "ρ [cm]", "z [cm]", True
    if eksen == 1:          # (r, phi): koni yuzeyi duzleme acilmis (r, phi) kutupsal
        return (A * np.cos(B) + merkez[0], A * np.sin(B) + merkez[1],
                "x [cm]", "y [cm]", True)
    return A * _DERECE, B * _DERECE, "θ [°]", "φ [°]", False


def dilim(sonuc, dizi, eksen, indeks):
    """3B dizinin (n1, n2, n3) `eksen` ekseninde `indeks` dilimi (Dilim)."""
    dizi = np.asarray(dizi)
    if eksen not in (0, 1, 2) or not 0 <= indeks < dizi.shape[eksen]:
        raise ValueError(_("geçersiz dilim: eksen %s, indeks %s") % (eksen, indeks))
    deger = np.take(dizi, indeks, axis=eksen).copy()
    x, y, xa, ya, esit = _dilim_kafesi(sonuc.tur, sonuc.izgaralar, eksen, sonuc.merkez)
    return Dilim(x=x, y=y, deger=deger, x_adi=xa, y_adi=ya, esit_olcek=esit)
