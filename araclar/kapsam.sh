#!/usr/bin/env bash
# =============================================================================
#  kapsam.sh  --  Test kapsamini olcer (kalite kapisi: toplam >= %80)
#
#  KULLANIM
#    araclar/kapsam.sh            hizli suit (dakikanin altinda)
#    araclar/kapsam.sh tam        hizli + yavas (Monte Carlo dahil, uzun)
#
#  Her dalga sonunda TAM olcum yapilir; sonuc plan dosyasina ve dalga
#  raporuna yazilir. Toplam %80'in altina duserse cikis kodu 1'dir.
# =============================================================================
set -euo pipefail
KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$KOK"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
secim="hizli"
[ "${1:-}" = "tam" ] && secim="hizli or yavas"
python -m pytest -m "$secim" -q -n "${KAPSAM_ISCI:-4}" -p no:cacheprovider \
    --cov --cov-report=term --cov-fail-under=80
