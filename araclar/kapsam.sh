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
#
#  OTURUM YALITIMI (29.09.2026, D1-C): kapsam verisi her oturumda AYRI bir
#  gecici dizine yazilir (COVERAGE_FILE). Aksi halde ayni calisma dizininde
#  ust uste binen iki `pytest --cov` oturumu birbirinin .coverage.* isci
#  dosyalarini siler: pytest-cov ana sureci basta `coverage erase` (butun
#  .coverage.* dosyalari), sonda `coverage combine` (dizindeki butun
#  .coverage.* dosyalarini alip siler) yapar. Tam suitte erken biten isciler
#  dosyasini dakikalarca diskte bekletir; o arada baslayan/biten baska bir
#  oturum onu yutar ve o iscinin kostugu testlerin kapsami kaybolur
#  (Dalga 1: %71.8 olculdu, gercek deger %87). Kalici veri gerekirse:
#  KAPSAM_VERI=/yol/.coverage araclar/kapsam.sh tam
# =============================================================================
set -euo pipefail
KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$KOK"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
veri_dizini="$(mktemp -d "${TMPDIR:-/tmp}/openmc_kapsam.XXXXXX")"
trap 'rm -rf "$veri_dizini"' EXIT
export COVERAGE_FILE="${KAPSAM_VERI:-$veri_dizini/.coverage}"
secim="hizli"
[ "${1:-}" = "tam" ] && secim="hizli or yavas"
python -m pytest -m "$secim" -q -n "${KAPSAM_ISCI:-4}" -p no:cacheprovider \
    --cov --cov-report=term --cov-fail-under=80
