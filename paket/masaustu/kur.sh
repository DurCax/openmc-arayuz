#!/usr/bin/env bash
# OpenMC arayuzu masaustu butunlesmesini kurar (kullanici duzeyi, kok gerekmez).
# Kullanim: kur.sh [--exec YOL] [--varsayilan-yapma] [--simulasyon]
# PYTHON ortam degiskeni yorumlayiciyi secer (varsayilan: python3). Python tarafi
# cekirdek/masaustu/ (pip ve constructor kurulumlarinda ayni modul). Cikis kodu 0 = tamam.
set -euo pipefail
python_bin="${PYTHON:-python3}"
exec "$python_bin" -m cekirdek.masaustu kur "$@"
