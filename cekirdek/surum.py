# -*- coding: utf-8 -*-
"""
surum.py -- surum ve uygulama adi TEK YERDEN.

Surumun tek kaynagi pyproject.toml'daki [project].version'dir:
  1. paket kuruluysa (pip install -e .) importlib.metadata,
  2. degilse kaynak agacindaki pyproject.toml,
  3. o da okunamazsa sabit geri donus (_GERI_DONUS_SURUMU).

Urun adi ve marka metni yalnizca UYGULAMA_ADI'ndadir; pencere basligi,
Hakkinda penceresi ve rapor bu sabiti kullanir (ad degisirse tek satir).
"""

import os

UYGULAMA_ADI = "OpenMC Arayüz"
PAKET_ADI = "openmc-arayuz"
_GERI_DONUS_SURUMU = "2.0.0.dev0"
_PYPROJECT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "pyproject.toml")


def _pyproject_surumu(yol=_PYPROJECT):
    """pyproject.toml'daki surum; dosya yoksa ya da okunamazsa None."""
    try:
        import tomllib
    except ImportError:          # Python < 3.11
        return None
    try:
        with open(yol, "rb") as f:
            return tomllib.load(f)["project"]["version"]
    except (OSError, KeyError, ValueError):
        return None


def _meta_surumu():
    from importlib import metadata
    try:
        return metadata.version(PAKET_ADI)
    except metadata.PackageNotFoundError:
        return None


def surum():
    """Uygulama surumu (PEP 440 metni, ornek "2.0.0.dev0")."""
    return _meta_surumu() or _pyproject_surumu() or _GERI_DONUS_SURUMU


__version__ = surum()
