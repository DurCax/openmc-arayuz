#!/usr/bin/env bash
# =============================================================================
#  docker/derle.sh -- imaji derler; etiket pyproject.toml surumunden
#
#  KULLANIM
#    docker/derle.sh            openmc-arayuz:<surum>   (X11 + komut satiri)
#    docker/derle.sh --novnc    openmc-arayuz:<surum>   + noVNC/Xvfb katmani
#  Ek docker build secenekleri sona eklenebilir (ornek: --no-cache).
# =============================================================================
set -euo pipefail

KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SURUM="$(sed -n 's/^version = "\(.*\)"/\1/p' "$KOK/pyproject.toml" | head -n 1)"
[ -n "$SURUM" ] || { echo "HATA: pyproject.toml'da surum okunamadi" >&2; exit 1; }
command -v docker >/dev/null || { echo "HATA: docker bulunamadi." >&2; exit 1; }

NOVNC=0
if [ "${1:-}" = "--novnc" ]; then
    NOVNC=1
    shift
fi
exec docker build --build-arg "NOVNC=$NOVNC" -t "openmc-arayuz:$SURUM" "$@" "$KOK"
