#!/usr/bin/env bash
# =============================================================================
#  paket/constructor/uret.sh -- tek dosya .sh kurulum paketi uretir -> dist/
#
#  KULLANIM   paket/constructor/uret.sh [--kuru]
#     --kuru  yalniz cozumleme (constructor --dry-run); dosya uretmez
#  GEREK      constructor, pip, setuptools>=77, wheel (conda-forge). Yoksa
#             OPENMC_ARAYUZ_PAKETLEME_ORTAMI (varsayilan: openmc-paketleme)
#             adli conda ortami kullanilir:
#               conda create -n openmc-paketleme -c conda-forge constructor "setuptools>=77" wheel pip
#  CIKTI      dist/openmc-arayuz-<surum>-Linux-x86_64.sh  (+ .sha256)
# =============================================================================
set -euo pipefail

KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SURUM="$(sed -n 's/^version = "\(.*\)"/\1/p' "$KOK/pyproject.toml" | head -n 1)"
[ -n "$SURUM" ] || { echo "HATA: pyproject.toml'da surum okunamadi" >&2; exit 1; }
ORTAM="${OPENMC_ARAYUZ_PAKETLEME_ORTAMI:-openmc-paketleme}"
KURU=0
[ "${1:-}" = "--kuru" ] && KURU=1

if ! command -v constructor >/dev/null; then
    CONDA_TABAN="$(conda info --base)"
    PATH="$CONDA_TABAN/envs/$ORTAM/bin:$PATH"
    command -v constructor >/dev/null || { echo "HATA: constructor yok (ortam: $ORTAM)" >&2; exit 1; }
fi

SAHNE="$(mktemp -d)"
trap 'rm -rf -- "$SAHNE"' EXIT
KAYNAK="$SAHNE/kaynak"
mkdir -p "$KAYNAK" "$SAHNE/masaustu" "$SAHNE/yapi"

# Kopyadan derle: pip kaynak agacini (build/, *.egg-info) kirletmesin
tar -C "$KOK" --exclude=.git --exclude=.claude --exclude='.env*' --exclude=dist \
    --exclude=build --exclude='*.egg-info' --exclude=__pycache__ --exclude=graphify-out \
    -cf - . | tar -C "$KAYNAK" -xf -
python -m pip wheel --no-deps --no-build-isolation -q -w "$SAHNE/yapi" "$KAYNAK"

cp "$KOK/paket/constructor/construct.yaml" "$KOK/paket/constructor/post_install.sh" \
   "$KOK/paket/constructor/kaldir.sh" "$SAHNE/yapi/"
# constructor lisans metnini yalniz ASCII kabul eder: Turkce harfler sadelestirilir
python - "$KOK/LICENSE" "$SAHNE/yapi/LICENSE.txt" <<'PY'
import sys, unicodedata
tablo = str.maketrans({"\u0131": "i", "\u0130": "I", "\u2019": "'", "\u2018": "'",
                       "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-"})
metin = open(sys.argv[1], encoding="utf-8").read().translate(tablo)
metin = unicodedata.normalize("NFKD", metin).encode("ascii", "ignore").decode("ascii")
open(sys.argv[2], "w", encoding="ascii").write(metin)
PY
# P2 dosyalari (varsa) kurulum agacina girer; yoksa bos dizin
if [ -d "$KOK/paket/masaustu" ]; then
    cp -R "$KOK/paket/masaustu/." "$SAHNE/masaustu/"
fi
touch "$SAHNE/masaustu/.yer-tutucu"
tar -C "$SAHNE/masaustu" -cf "$SAHNE/yapi/masaustu.tar" .

WHEEL="$(cd "$SAHNE/yapi" && ls openmc_arayuz-*.whl)"
export OPENMC_ARAYUZ_SURUM="$SURUM" OPENMC_ARAYUZ_WHEEL="$WHEEL"
mkdir -p "$KOK/dist"
if [ "$KURU" = 1 ]; then
    constructor --dry-run "$SAHNE/yapi"
    exit 0
fi
BASLA="$(date +%s)"
constructor --output-dir "$KOK/dist" "$SAHNE/yapi"
( cd "$KOK/dist" && sha256sum "openmc-arayuz-$SURUM-Linux-x86_64.sh" > "openmc-arayuz-$SURUM-Linux-x86_64.sh.sha256" )
echo "Uretildi: $KOK/dist/openmc-arayuz-$SURUM-Linux-x86_64.sh ($(( $(date +%s) - BASLA )) sn, $(du -h "$KOK/dist/openmc-arayuz-$SURUM-Linux-x86_64.sh" | cut -f1))"
