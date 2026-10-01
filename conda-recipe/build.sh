#!/usr/bin/env bash
# conda-build derleme betigi: kaynak agacini $PREFIX/share/openmc-arayuz'a
# kopyalar; site-packages'a o dizini sys.path'e ekleyen bir .pth koyar.
# Giris komutlari (openmc-arayuz, openmc-arayuz-kosu) meta.yaml entry_points'ten.
set -euo pipefail

HEDEF="$PREFIX/share/openmc-arayuz"
mkdir -p "$HEDEF"

# Uygulamanin calisma aninda okudugu her sey (ikonlar ve yazi tipleri arayuz/
# altinda; ceviri katalogu locale/; surum pyproject.toml'dan okunur).
for oge in cekirdek arayuz locale ornekler docs pyproject.toml \
           LICENSE THIRD_PARTY_LICENSES.md README.md README.en.md \
           INSTALL.md KURULUM.md CHANGELOG.md veri_indir.sh; do
    [ -e "$oge" ] || { echo "HATA: kaynakta $oge yok" >&2; exit 1; }
    cp -R "$oge" "$HEDEF/"
done
chmod +x "$HEDEF/veri_indir.sh"
find "$HEDEF" -name "__pycache__" -type d -prune -exec rm -rf {} +

# .pth: "import" ile baslayan satir Python acilisinda calistirilir; yol
# sys.prefix'ten hesaplanir, boylece ortam tasinsa da (onek degisimi) dogru kalir.
mkdir -p "$SP_DIR"
echo "import os, sys; sys.path.append(os.path.join(sys.prefix, 'share', 'openmc-arayuz'))" \
    > "$SP_DIR/openmc_arayuz.pth"
