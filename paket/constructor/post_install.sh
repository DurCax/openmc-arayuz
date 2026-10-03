#!/usr/bin/env bash
# constructor post_install: uygulama wheel'ini kurar, isaret dosyasi yazar,
# P2 masaustu kancasini cagirir. Kullanici girdisi YOK; ag YOK.
# constructor ortami: PREFIX, INSTALLER_UNATTENDED.
set -euo pipefail

: "${PREFIX:?PREFIX tanimli degil}"
PAKET_DIZINI="$PREFIX/share/openmc-arayuz-paket"
ISARET="$PREFIX/.openmc-arayuz-kurulum"

shopt -s nullglob
wheeller=("$PAKET_DIZINI"/openmc_arayuz-*.whl)
[ "${#wheeller[@]}" -eq 1 ] || { echo "HATA: tam bir wheel beklenirdi, ${#wheeller[@]} bulundu" >&2; exit 1; }

# --no-index: ag kullanilmaz; --no-deps: bagimliliklar conda paketleri.
"$PREFIX/bin/python" -m pip install --no-index --no-deps --no-warn-script-location \
    --disable-pip-version-check -q "${wheeller[0]}"
rm -f -- "${wheeller[0]}"

# kaldir.sh yalniz bu isaretin bulundugu dizini siler.
printf '%s\n' "openmc-arayuz ${INSTALLER_VER:-}" > "$ISARET"
chmod +x "$PAKET_DIZINI/kaldir.sh"

# ---- KANCA (P2): masaustu bütünlesmesi --------------------------------------
# $PREFIX/share/openmc-arayuz-paket/masaustu/kur.sh varsa cagrilir:
#     kur.sh <PREFIX>      (kullanicinin $HOME/XDG dizinlerine .desktop/MIME/ikon yazar)
# Basarisizlik kurulumu bozmaz (uyari verilir).
KANCA="$PAKET_DIZINI/masaustu/kur.sh"
if [ -f "$KANCA" ]; then
    bash "$KANCA" "$PREFIX" || echo "UYARI: masaustu kaydi basarisiz (kanca $KANCA); uygulama yine calisir." >&2
fi

cat <<METIN

openmc-arayuz kuruldu: $PREFIX
  Baslat:   $PREFIX/bin/openmc-arayuz
  Terminal: $PREFIX/bin/openmc-arayuz-kosu --help
  Veri:     uygulamanin Veri sayfasindan indirin (pakette nukleer veri yok)
  Kaldir:   bash $PAKET_DIZINI/kaldir.sh
METIN
