# -*- coding: utf-8 -*-
"""
giris.py -- paket giris noktalari (pyproject.toml [project.scripts]).

  openmc-arayuz        -> gui()   = python -m arayuz.ana_pencere [spec.json]
  openmc-arayuz-kosu   -> kosu()  = python -m cekirdek.kosucu spec.json [...]

Ince sarmalayicilar: davranis mevcut modul girislerinin aynisidir. GUI tarafi
runpy ile `python -m arayuz.ana_pencere` gibi calistirilir; boylece pencere
modulu yeniden duzenlense de (arayuz/pencere/ paketi) giris yolu degismez.
"""

import runpy
import sys


def kosu(argv=None):
    """Terminal kosucusu: cekirdek.kosucu'nun komut satiri."""
    from cekirdek import kosucu
    return kosucu._terminal(list(sys.argv[1:] if argv is None else argv))


def gui(argv=None):
    """Arayuz: `python -m arayuz.ana_pencere` ile ayni."""
    if argv is not None:
        sys.argv = [sys.argv[0]] + list(argv)
    try:
        runpy.run_module("arayuz.ana_pencere", run_name="__main__", alter_sys=True)
    except SystemExit as cikis:
        return cikis.code
    return 0


if __name__ == "__main__":
    sys.exit(gui())
