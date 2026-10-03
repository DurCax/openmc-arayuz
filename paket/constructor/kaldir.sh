#!/usr/bin/env bash
# openmc-arayuz kaldirma: YALNIZ bu betigin bulundugu kurulumu siler.
# Kullanim: bash <PREFIX>/share/openmc-arayuz-paket/kaldir.sh [--evet]
# Kullanicinin projelerine, ~/nucdata'ya ve ayarlara (~/.config/openmc_arayuz) DOKUNMAZ.
set -euo pipefail

BETIK_DIZINI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PREFIX="$(cd "$BETIK_DIZINI/../.." && pwd -P)"

[ -f "$PREFIX/.openmc-arayuz-kurulum" ] || { echo "HATA: $PREFIX bir openmc-arayuz kurulumu degil (isaret yok); silinmedi." >&2; exit 1; }
[ -x "$PREFIX/bin/python" ] && [ -d "$PREFIX/conda-meta" ] || { echo "HATA: $PREFIX conda kurulumuna benzemiyor; silinmedi." >&2; exit 1; }
case "$PREFIX" in
    /|"$HOME"|/usr|/usr/*|/opt|/home|/etc|/var|/bin|/lib) echo "HATA: tehlikeli hedef: $PREFIX" >&2; exit 1 ;;
esac

if [ "${1:-}" != "--evet" ]; then
    printf '%s silinecek. Devam? [e/H] ' "$PREFIX"
    read -r cevap
    [ "$cevap" = "e" ] || { echo "Iptal."; exit 0; }
fi

# P2 kancasi: masaustu kayitlarini (menu, MIME) geri alir
if [ -f "$BETIK_DIZINI/masaustu/kaldir.sh" ]; then
    PYTHON="$PREFIX/bin/python" bash "$BETIK_DIZINI/masaustu/kaldir.sh" || echo "UYARI: masaustu kaydi kaldirilamadi." >&2
fi

# Betik kendi dizinini silecek: once bellege okunmasi icin /tmp'ye tasinmaz;
# bash betigi satir satir okur, bu yuzden son komut olarak exec ile bitirilir.
exec rm -rf --one-file-system -- "$PREFIX"
