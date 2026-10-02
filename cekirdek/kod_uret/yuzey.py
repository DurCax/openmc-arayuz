# -*- coding: utf-8 -*-
"""
 kod_uret/yuzey.py  --  betigin Y7 bolumu: yuzey akimi tally'leri

 Tanimlar kurucu ile AYNI kaynaktan (cekirdek/yuzey_akim.py): vakum sinir
 yuzeyleri betikte de geometriden secilir, kutu agi sinirlari ayni islevle
 (kurucu.tally_mesh_sinirlari) hesaplanir. Esdegerlik:
 testler/test_y7_yuzey.py (test_kurucu_ve_betik_ayni_yuzey_tallyleri).
"""

from typing import List

from cekirdek import yuzey_akim as _y


def _filtre_satirlari(spec: dict, t: dict, sinir_kutu, satirlar: List[str]) -> List[str]:
    ifadeler = []
    for f in t.get("filtreler") or []:
        if f["tur"] == _y.FILTRE_SINIR:
            satirlar.append("    _vakum = sorted((s for s in geometri.get_all_surfaces().values()")
            satirlar.append("                     if s.boundary_type == 'vacuum'), key=lambda s: s.id)")
            satirlar.append("    if not _vakum:")
            satirlar.append("        return []      # vakum sınırı yok: kaçak tanımca sıfır")
            ifadeler.append("openmc.SurfaceFilter(_vakum)")
        elif f["tur"] == _y.FILTRE_KUTU:
            alt, ust = _y.kutu_sinirlari(spec, f, sinir_kutu)
            satirlar.append("    _ag = openmc.RegularMesh()")
            satirlar.append("    _ag.dimension = %r" % list(f["boyut"]))
            satirlar.append("    _ag.lower_left, _ag.upper_right = %r, %r" % (list(alt), list(ust)))
            ifadeler.append("openmc.MeshSurfaceFilter(_ag)")
        elif f["tur"] == "enerji":
            ifadeler.append("openmc.EnergyFilter(%r)" % list(f["gruplar"]))
    return ifadeler


def _tally_satirlari(spec: dict, t: dict, islev: str, sinir_kutu, satirlar: List[str]) -> None:
    satirlar.append("")
    satirlar.append("def %s(geometri):" % islev)
    ifadeler = _filtre_satirlari(spec, t, sinir_kutu, satirlar)
    satirlar.append("    _t = openmc.Tally(name=%r)" % t["ad"])
    satirlar.append("    _t.scores = %r" % list(t["skorlar"]))
    satirlar.append("    _t.filters = [%s]" % ", ".join(ifadeler))
    if _y.yuzey_filtresi(t)["tur"] != _y.FILTRE_KUTU:
        satirlar.append("    return [_t]")
        return
    satirlar.append("    # Denge: S + giren − çıkan + X = A (aynı ağ; X = (n,xn) net üretim)")
    satirlar.append("    _d = openmc.Tally(name=%r)" % _y.denge_adi(t["ad"]))
    satirlar.append("    _d.scores = %r" % list(_y.DENGE_SKORLARI))
    satirlar.append("    _d.filters = [openmc.MeshFilter(_ag)]")
    satirlar.append("    return [_t, _d]")


def _yuzey_tallyleri(spec: dict, satirlar: List[str], sinir_kutu) -> None:
    """_tallyler kancasi ('tallyler' tanimlandiktan SONRA): yuzey tally'lerini
    kuran islevler ve tallyler'e ekleme."""
    tallyler = [t for t in spec.get("tallyler") or [] if _y.yuzey_tally_mi(t)]
    if not tallyler:
        return
    satirlar.append("")
    satirlar.append("# --- yüzey akımı tally'leri (Y7) ---")
    satirlar.append("# Vakum yüzeyinden her geçiş dışarıdır: yüzey başına |J| = kaçak.")
    satirlar.append("# Kutu ağı: her yüz için ayrı giren (in) / çıkan (out) kısmi akım.")
    adlar = ["_y7_yuzey_%d" % (i + 1) for i in range(len(tallyler))]
    for t, islev in zip(tallyler, adlar):
        _tally_satirlari(spec, t, islev, sinir_kutu, satirlar)
    satirlar.append("")
    satirlar.append("")
    for ad in adlar:
        satirlar.append("tallyler.extend(%s(geometri))" % ad)
