#!/usr/bin/env bash
# =============================================================================
#  calistir.sh  --  Ortami dogrulayip arayuzu acar
#
#  KULLANIM
#    ./calistir.sh                          bos modelle acilir
#    ./calistir.sh ornekler/pwr_17x17.json  verilen spec ile acilir
# =============================================================================
set -u
KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

hata() { echo "HATA: $*" >&2; exit 1; }

command -v openmc >/dev/null 2>&1 || hata "openmc PATH'te yok. 'conda activate openmc-env' calistirin."
python3 -c "import openmc" 2>/dev/null || hata "openmc Python paketi bulunamadi."
python3 -c "import PySide6" 2>/dev/null || hata "PySide6 bulunamadi. 'conda install -c conda-forge pyside6' gerekir."
[ -n "${OPENMC_CROSS_SECTIONS:-}" ] || echo "UYARI: OPENMC_CROSS_SECTIONS ayarli degil -- kosu basarisiz olur."
[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] || hata "Grafik oturum yok (DISPLAY/WAYLAND_DISPLAY bos)."

cd "$KOK" && exec python3 -m arayuz.ana_pencere "$@"
