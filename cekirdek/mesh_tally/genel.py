# -*- coding: utf-8 -*-
"""
 cekirdek/mesh_tally/genel.py  --  mesh tally'sine eslik eden model geneli bilgiler

   genel isinma tally'si  Ozdeger hesabinda bir mesh tally'si varsa filtresiz
                          GENEL_ISI_TALLY eklenir (kurucu ve betik AYNI isimle ve
                          skorlarla). Mutlak normalizasyonun H'si (kaynak nötronu
                          basina isinma, eV) buradan okunur: ag fisil bolgeyi
                          kapsamasa da (kare demette silindirik ag ~%21.5 alani
                          kacirir) kaynak hizi dogru cikar.
   geometri z araligi     2B (spec'e gore eksenel sonsuz) modelde geometri yine de
                          z'de sinirliysa ag o araliga kirpilir; +/-Z_2B_YARI
                          yalniz gercekten sinirsiz modelde.
"""

import contextlib
import math

from cekirdek.mesh_tally.tanim import (GENEL_ISI_SKORLARI, GENEL_ISI_TALLY,
                                       eksenel_sonsuz)


def _mesh_filtreli(spec) -> bool:
    return any(f.get("tur") == "mesh" for t in spec.get("tallyler") or []
               for f in t.get("filtreler") or [])


def genel_isi_gerekli(spec) -> bool:
    """Ozdeger hesabi ve en az bir mesh filtreli tally varsa True."""
    mod = ((spec.get("ayarlar") or {}).get("mod") or "eigenvalue")
    return mod == "eigenvalue" and _mesh_filtreli(spec)


def genel_isi_tally_kur(spec):
    """kurucu kancasi: filtresiz genel isinma tally'si ya da None."""
    if not genel_isi_gerekli(spec):
        return None
    import openmc
    t = openmc.Tally(name=GENEL_ISI_TALLY)
    t.scores = list(GENEL_ISI_SKORLARI)
    return t


def genel_isi_betik(spec, degisken="mesh_genel_isi"):
    """kod_uret kancasi: (satirlar, degisken) ya da ([], None)."""
    if not genel_isi_gerekli(spec):
        return [], None
    return (["",
             "# Mutlak normalizasyon icin model geneli isinma (filtresiz; arayuzle ayni).",
             "%s = openmc.Tally(name=%r)" % (degisken, GENEL_ISI_TALLY),
             "%s.scores = %r" % (degisken, list(GENEL_ISI_SKORLARI))], degisken)


def geometri_z_araligi(evren):
    """openmc Universe/Geometry sinir kutusunun z araligi; sinirsizsa None."""
    kutu = evren.bounding_box
    z0, z1 = float(kutu[0][2]), float(kutu[1][2])
    return (z0, z1) if math.isfinite(z0) and math.isfinite(z1) else None


@contextlib.contextmanager
def _kimlikler_korunur():
    """OpenMC otomatik kimlik sayaclarini (kurucu.kur reset_auto_ids yapar) geri
    yukler: betik uretimi ayni surecte sonra kurulan nesnelerin kimligini kaydirmasin."""
    from openmc.mixin import IDManagerMixin
    siniflar = list(IDManagerMixin.__subclasses__())
    durum = [(c, c.next_id, set(c.used_ids)) for c in siniflar]
    try:
        yield
    finally:
        for c, sonraki, kullanilan in durum:
            c.next_id = sonraki
            c.used_ids.clear()
            c.used_ids.update(kullanilan)


def model_z_araligi(spec, evren=None):
    """2B modelde (eksenel_sonsuz) geometrinin sonlu z araligi; degilse None.
    evren verilmezse model kurulur (betik yolu; yalniz mesh tally varken; kimlik
    sayaclari korunur)."""
    if not (_mesh_filtreli(spec) and eksenel_sonsuz(spec)):
        return None
    if evren is None:
        from cekirdek import kurucu
        with _kimlikler_korunur():
            model, _bilgi = kurucu.kur(spec)
            return geometri_z_araligi(model.geometry)
    return geometri_z_araligi(evren)
