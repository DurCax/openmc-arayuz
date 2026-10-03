#!/usr/bin/env bash
# Masaustu butunlesmesini kaldirir: yalniz kur'un manifestte kaydettigi dosyalar silinir.
set -euo pipefail
python_bin="${PYTHON:-python3}"
exec "$python_bin" -m cekirdek.masaustu kaldir "$@"
