# -*- coding: utf-8 -*-
"""
 kod_uret/spektrum.py  --  betigin Y3 bolumu: spektrum ve dort faktor tally'leri

 Tanimlar kurucu ile AYNI kaynaktan gelir (cekirdek.spektrum.tally_tanimlari);
 filtre sirasi da ayni (malzeme, sonra enerji). Esdegerlik:
 testler/test_y3_spektrum.py (test_kurucu_ve_betik_ayni_tallyler).
"""

from cekirdek import spektrum
from cekirdek.kod_uret.ad import _ad


def _filtre_ifadeleri(t):
    ifadeler = []
    if t["malzemeler"]:
        ifadeler.append("openmc.MaterialFilter([%s])" % ", ".join(_ad(a) for a in t["malzemeler"]))
    if t["grup_yapisi"]:
        ifadeler.append("openmc.EnergyFilter.from_group_structure(%r)" % t["grup_yapisi"])
    elif t["enerji"]:
        ifadeler.append("openmc.EnergyFilter(%r)" % [float(e) for e in t["enerji"]])
    return ifadeler


def _spektrum_tallyleri(spec, satirlar):
    """model kurulduktan SONRA cagrilir: Y3 tally'lerini model.tallies'e ekler."""
    tanimlar = spektrum.tally_tanimlari(spec)
    if not tanimlar:
        return
    satirlar.append("")
    satirlar.append("# --- spektrum ve dört faktör (ε, p, f, η) tally'leri ---")
    satirlar.append("# Termal kesim %g eV (OpenMC tally-arithmetic örneği, CASMO-2 sınırı)."
                    % spektrum.TERMAL_KESIM_EV)
    satirlar.append("# ε = νF/νF_th, p = A_th/A, f = A_F,th/A_th, η = νF_th/A_F,th")
    satirlar.append("# (sızıntısız tanım; k = ε·p·f·η · A/(A−X) · P_NL, X = (n,xn) net üretim)")
    satirlar.append("def _y3_tallyleri():")
    satirlar.append("    _liste = []")
    for t in tanimlar:
        satirlar.append("    _t = openmc.Tally(name=%r)" % t["ad"])
        satirlar.append("    _t.scores = %r" % list(t["skorlar"]))
        if t["nuklidler"]:
            satirlar.append("    _t.nuclides = %r" % list(t["nuklidler"]))
        satirlar.append("    _t.filters = [%s]" % ", ".join(_filtre_ifadeleri(t)))
        satirlar.append("    _liste.append(_t)")
    satirlar.append("    return _liste")
    satirlar.append("")
    satirlar.append("")
    satirlar.append("model.tallies = openmc.Tallies(list(model.tallies) + _y3_tallyleri())")
