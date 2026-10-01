# -*- coding: utf-8 -*-
"""
test_tukenme_spektrum.py -- otomatik zincir/spektrum secimi (profesor denetimi, Dalga 4).

  [TS1] Yakit komsulugu: hizli (H'siz) yakit cubuklu modele uzakta su zirhi
        eklenince zincir HIZLI kalir (eski kural: herhangi bir H -> termal).
  [TS2] Kosuda EALF tally'si varsa olculen EALF secimi belirler (komsuluktan once).
  [TS3] Secim raporda gorunur (rapor zincir satirinda "seçim: ... zincir").

Monte Carlo KOSULMAZ.
"""

import copy
import os

from testler.ortak_test import kontrol, ORNEK


def _sfr_su_zirhli():
    from cekirdek import sema
    spec = sema.yukle(os.path.join(ORNEK, "sfr_altigen.json"))
    s = copy.deepcopy(spec)
    s["malzemeler"].append({"ad": "su_zirh", "yogunluk": 1.0, "birim": "g/cm3",
                            "bilesim": [{"tur": "nuklid", "isim": "H1", "miktar": 2.0,
                                         "birim": "ao"},
                                        {"tur": "nuklid", "isim": "O16", "miktar": 1.0,
                                         "birim": "ao"}],
                            "sab": ["c_H_in_H2O"]})
    return spec, s


def test_komsuluk_uzak_su_hizli():
    print("\n[TS1] Yakit komsulugu: uzaktaki su zirhi spektrumu termal yapmaz")
    from cekirdek import tukenme
    asil, s = _sfr_su_zirhli()
    z = tukenme.zincir_secimi(s)
    kontrol("SFR + uzak su -> hizli", z["tur"] == "hizli", "-> %s (%s)" % (z["tur"], z["gerekce"]))
    kontrol("yontem komsuluk, gerekce su_zirh'i anar", z["yontem"] == "komsuluk"
            and "su_zirh" in z["gerekce"], "-> %s" % z["gerekce"])
    kontrol("girdi degismedi (asil spec'te su_zirh yok)",
            all(m["ad"] != "su_zirh" for m in asil["malzemeler"]))


def test_ealf_onceligi():
    print("\n[TS2] Kosudaki EALF secimi belirler")
    from cekirdek import tukenme
    from cekirdek.vv import aoa
    _a, s = _sfr_su_zirhli()
    eski = aoa.ealf_oku
    try:
        aoa.ealf_oku = lambda d: 0.05 if d == "termal_kosu" else 8.0e5
        zt = tukenme.zincir_secimi(s, "termal_kosu")
        zh = tukenme.zincir_secimi(s, "hizli_kosu")
    finally:
        aoa.ealf_oku = eski
    kontrol("EALF 0.05 eV -> termal (ealf)", zt["tur"] == "termal" and zt["yontem"] == "ealf",
            "-> %s" % zt)
    kontrol("EALF 800 keV -> hizli (ealf)", zh["tur"] == "hizli" and "EALF" in zh["gerekce"])


def test_secim_raporda():
    print("\n[TS3] Zincir secimi raporda")
    from cekirdek import rapor, sema
    spec = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    spec["tukenme"]["var"] = True
    eski = os.environ.get("OPENMC_CHAIN_FILE")
    os.environ["OPENMC_CHAIN_FILE"] = "/yok/chain_endfb80_thermal.xml"
    try:
        metin = rapor._zincir_metni(spec, {}, None)
    finally:
        if eski is None:
            os.environ.pop("OPENMC_CHAIN_FILE", None)
        else:
            os.environ["OPENMC_CHAIN_FILE"] = eski
    kontrol("rapor zincir satirinda secim ve gerekce", metin and "seçim:" in metin
            and "yakıta komşu" in metin, "-> %s" % metin)


HIZLI = [test_komsuluk_uzak_su_hizli, test_ealf_onceligi, test_secim_raporda]
YAVAS = []
