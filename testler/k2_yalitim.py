# -*- coding: utf-8 -*-
"""
k2_yalitim.py -- K2 testleri icin nukleer veri yalitimi.

VeriYalitimi: gecici HOME / XDG_CONFIG_HOME / XDG_DATA_HOME, OPENMC_* yok;
cikista os.environ, openmc.config (cross_sections / chain_file) ve
veri_yolu / veri_bilgi onbellekleri ESKI haline doner. Gerekce: veri_yolu.
surece_uygula() openmc yukluyse openmc.config'i de yazar; geri alinmazsa ayni
pytest isci surecindeki sonraki testler gecici (silinmis) bir kutuphaneyi
okur (olculdu: 20 test OSError ile kaldi).
"""

import os
import sys
import tempfile

_DEGISKENLER = ("OPENMC_CROSS_SECTIONS", "OPENMC_CHAIN_FILE", "HOME", "XDG_CONFIG_HOME",
                "XDG_DATA_HOME")
_CONFIG = ("cross_sections", "chain_file")


def _config_al():
    if "openmc" not in sys.modules:
        return None
    import openmc
    return {k: openmc.config[k] for k in _CONFIG if k in openmc.config}


def _config_geri(eski):
    if eski is None or "openmc" not in sys.modules:
        return
    import openmc
    for k in _CONFIG:
        if k in eski:
            openmc.config[k] = eski[k]
        elif k in openmc.config:
            del openmc.config[k]


class VeriYalitimi:
    """with VeriYalitimi() as y: y.kok gecici ev dizini."""

    def __enter__(self):
        from cekirdek import veri_yolu
        self._dizin = tempfile.TemporaryDirectory()
        self.kok = self._dizin.name
        self._ortam = {k: os.environ.get(k) for k in _DEGISKENLER}
        self._config = _config_al()
        self._enjekte = dict(veri_yolu._ENJEKTE)
        for k in ("OPENMC_CROSS_SECTIONS", "OPENMC_CHAIN_FILE"):
            os.environ.pop(k, None)
        os.environ.update(HOME=self.kok, XDG_CONFIG_HOME=os.path.join(self.kok, "cfg"),
                          XDG_DATA_HOME=os.path.join(self.kok, "data"))
        veri_yolu._ENJEKTE.clear()
        return self

    def __exit__(self, *a):
        from cekirdek import veri_bilgi, veri_yolu
        _config_geri(self._config)            # os.environ'u da yazar; asagida duzelir
        for k, v in self._ortam.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        veri_yolu._ENJEKTE.clear()
        veri_yolu._ENJEKTE.update(self._enjekte)
        veri_bilgi.onbellek_temizle()
        self._dizin.cleanup()
        return False
