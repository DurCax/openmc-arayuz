# -*- coding: utf-8 -*-
"""
arayuz/geometri/renk.py -- sematik kesit ve kafes paletinin parca renkleri.

Dogal renk izgara._parca_rengi'dir (malzeme rengi, cubugun ic bolgesi, ...);
yoksa addan BELIRLEYICI bir kategorik palet rengi (her cizimde ayni renk).
"""

from arayuz.izgara import _PALET, _TANIMSIZ_RENGI, _parca_rengi


def parca_rengi(spec, ad):
    """(r, g, b); tambur tanimi govde malzemesinin rengini alir."""
    for t in spec.get("tamburlar") or []:
        if t.get("ad") == ad:
            return parca_rengi(spec, t.get("govde_malzeme"))
    rgb = _parca_rengi(spec, ad)
    if rgb is not None:
        return rgb
    if not ad:
        return _TANIMSIZ_RENGI
    return _PALET[sum(ord(ch) for ch in str(ad)) % len(_PALET)]
