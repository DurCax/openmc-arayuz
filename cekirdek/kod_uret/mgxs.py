# -*- coding: utf-8 -*-
"""
 kod_uret/mgxs.py  --  betigin Y8 bolumu: openmc.mgxs.Library tally'leri

 Parametreler kurucu ile AYNI kaynaktan (cekirdek.mgxs_uret.ayar / domainler
 ile ayni ifade); esdegerlik testler/test_y8_mgxs.py
 (test_kurucu_ve_betik_ayni_tallyler).
"""

from cekirdek import mgxs_uret

_DOMAIN_IFADESI = {
    "malzeme": "sorted(geometri.get_all_materials().values(), key=lambda _m: _m.id)",
    "hucre": "sorted(geometri.get_all_material_cells().values(), key=lambda _c: _c.id)",
    "demet": "[geometri.root_universe]",
}


def _mgxs_tallyleri(spec: dict, satirlar: list) -> None:
    """model kurulduktan SONRA cagrilir: MGXS tally'lerini model.tallies'e ekler."""
    if not mgxs_uret.etkin_mi(spec):
        return
    a = mgxs_uret.ayar(spec)
    satirlar += [
        "",
        "# --- çok gruplu tesir kesitleri (openmc.mgxs) ---",
        "# Akı ağırlıklı grup sabitleri; bölge: %s, grup yapısı: %s, düzeltme: %s."
        % (a.bolge, a.grup_yapisi, a.duzeltme),
        "# P0 = out-scatter taşıma düzeltmesi (Str = St - Ss1; matris köşegeni de Ss1 azalır).",
        "import openmc.mgxs",
        "",
        "",
        "def _y8_mgxs():",
        "    _lib = openmc.mgxs.Library(geometri)",
        "    _lib.energy_groups = openmc.mgxs.EnergyGroups(%r)" % a.grup_yapisi,
        "    _lib.mgxs_types = %r" % list(a.etkin_turler),
        "    _lib.domain_type = %r" % a.domain_turu,
        "    _lib.domains = %s" % _DOMAIN_IFADESI[a.bolge],
        "    _lib.correction = %r" % a.openmc_duzeltme,
        "    _lib.legendre_order = 0",
        "    _lib.build_library()",
        "    return _lib",
        "",
        "",
        "mgxs_kutuphanesi = _y8_mgxs()",
        "_y8_tallyler = openmc.Tallies()",
        "mgxs_kutuphanesi.add_to_tallies(_y8_tallyler, merge=True)",
        "model.tallies = openmc.Tallies(list(model.tallies) + list(_y8_tallyler))",
        "# Koşudan sonra:",
        "#   with openmc.StatePoint(sp) as _sp:",
        "#       mgxs_kutuphanesi.load_from_statepoint(_sp)",
        "#   mgxs_kutuphanesi.create_mg_library(xs_type='macro').export_to_hdf5('mgxs.h5')",
    ]
