#!/usr/bin/env bash
# =============================================================================
#  veri_indir.sh  --  OpenMC nükleer verisini indirir ve doğrular
#
#  İndirilenler (kaynak: https://openmc.org/data):
#    1. ENDF/B-VIII.0 HDF5 tesir kesiti kütüphanesi (açılınca ~13 GB)
#    2. Tükenme zincirleri: ENDF/B-VIII.0 termal + hızlı (3820 nüklid, ~27 MB),
#       CASL termal + hızlı (228 nüklid, ~1 MB)
#
#  KULLANIM
#    ./veri_indir.sh                  hepsini ~/nucdata altına indirir
#    ./veri_indir.sh --hedef DIZIN    başka bir dizine
#    ./veri_indir.sh --yalniz-zincir  yalnız tükenme zincirleri (~57 MB)
#    ./veri_indir.sh --bashrc         bitince ortam değişkenlerini ~/.bashrc'ye ekler
#
#  Zincirlerin bayt sayısı ve sha256'sı aşağıdaki tabloyla karşılaştırılır:
#  yarım kalan indirme (bu projede bir kez %13'te sessizce kesilmişti) KABUL
#  EDİLMEZ. Dosya zaten varsa ve doğruysa yeniden indirilmez.
# =============================================================================
set -euo pipefail

HEDEF="$HOME/nucdata"
YALNIZ_ZINCIR=0
BASHRC=0
while [ $# -gt 0 ]; do
    case "$1" in
        --hedef) HEDEF="$2"; shift 2 ;;
        --yalniz-zincir) YALNIZ_ZINCIR=1; shift ;;
        --bashrc) BASHRC=1; shift ;;
        -h|--yardim) sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "Bilinmeyen seçenek: $1 (--yardim)" >&2; exit 2 ;;
    esac
done

XS_URL="https://anl.box.com/shared/static/uhbxlrx7hvxqw27psymfbhi7bx7s6u6a.xz"
# dosya | url | bayt | sha256
ZINCIRLER="
chain_endfb80_thermal.xml|https://anl.box.com/shared/static/nyezmyuofd4eqt6wzd626lqth7wvpprr.xml|27526672|98bf49c92c821280087ee180763ce11b849be5faf5c2ff8ef8a3cd90bd93e87e
chain_endfb80_fast.xml|https://anl.box.com/shared/static/x3kp739hr5upmeqpbwx9zk9ep04fnmtg.xml|27527401|5eeb727498d824d7c951ad89864bbc1c2d76ec5e8c9097a820505213ba6a2bf3
chain_casl_thermal.xml|https://anl.box.com/shared/static/3nvnasacm2b56716oh5hyndxdyauh5gs.xml|981527|9c71578f366b40ca0aa566b56ac99c22fc1c37d183ad8641eba253d5a6f370f7
chain_casl_fast.xml|https://anl.box.com/shared/static/9fqbq87j0tx4m6vfl06pl4ccc0hwamg9.xml|981581|eeb782a17a4501a267152313ce1e65abe15c35b15dd9b1e3d5a6e5e23f0bdebe
"

hata() { echo "HATA: $*" >&2; exit 1; }
command -v curl >/dev/null || hata "curl gerekli (conda install -c conda-forge curl ya da sistem paketi)."
command -v sha256sum >/dev/null || hata "sha256sum gerekli (coreutils)."

dogru_mu() {  # dosya bayt sha -> 0 ise doğru
    [ -f "$1" ] || return 1
    [ "$(stat -L -c %s "$1")" = "$2" ] || return 1
    [ "$(sha256sum "$1" | cut -d' ' -f1)" = "$3" ]
}

# ---------------------------------------------------------------- zincirler
ZD="$HEDEF/chain"
mkdir -p "$ZD"
echo "== Tükenme zincirleri -> $ZD"
echo "$ZINCIRLER" | while IFS='|' read -r ad url bayt sha; do
    [ -n "$ad" ] || continue
    if dogru_mu "$ZD/$ad" "$bayt" "$sha"; then
        echo "   $ad: zaten var ve doğru"
        continue
    fi
    echo "   $ad indiriliyor ($bayt bayt)..."
    curl -L --fail --retry 3 -C - -o "$ZD/$ad.indiriliyor" "$url"
    dogru_mu "$ZD/$ad.indiriliyor" "$bayt" "$sha" \
        || hata "$ad: boyut ya da sha256 tutmuyor (yarım indirme?). Betiği yeniden çalıştırın; kaldığı yerden sürer."
    mv "$ZD/$ad.indiriliyor" "$ZD/$ad"
    echo "   $ad: doğrulandı"
done

# ------------------------------------------------------ tesir kesiti kütüphanesi
XD="$HEDEF/endfb-viii.0-hdf5"
if [ "$YALNIZ_ZINCIR" = 0 ]; then
    echo "== ENDF/B-VIII.0 HDF5 kütüphanesi -> $XD"
    if [ -f "$XD/cross_sections.xml" ]; then
        echo "   zaten var: $XD/cross_sections.xml"
    else
        BOS=$(df -Pk "$HEDEF" | awk 'NR==2 {print int($4/1024/1024)}')
        [ "$BOS" -ge 20 ] || hata "$HEDEF üzerinde ~20 GB boş alan gerekli (şu an $BOS GB)."
        ARSIV="$HEDEF/endfb-viii.0-hdf5.tar.xz"
        echo "   arşiv indiriliyor (birkaç GB; kesilirse betiği yeniden çalıştırın, kaldığı yerden sürer)..."
        curl -L --fail --retry 3 -C - -o "$ARSIV" "$XS_URL"
        echo "   açılıyor..."
        mkdir -p "$XD.gecici"
        tar -xJf "$ARSIV" -C "$XD.gecici" || hata "arşiv açılamadı (yarım indirme?). $ARSIV'i silip yeniden deneyin."
        # Arşivin içindeki üst dizin adı sürüme göre değişebilir: cross_sections.xml'i bul.
        XML=$(find "$XD.gecici" -name cross_sections.xml -print -quit)
        [ -n "$XML" ] || hata "arşivde cross_sections.xml yok."
        mv "$(dirname "$XML")" "$XD"
        rm -rf "$XD.gecici" "$ARSIV"
        echo "   hazır: $XD/cross_sections.xml"
    fi
fi

# ------------------------------------------------------------- ortam değişkenleri
SATIRLAR="export OPENMC_CHAIN_FILE=\"$ZD/chain_endfb80_thermal.xml\""
[ "$YALNIZ_ZINCIR" = 1 ] || SATIRLAR="export OPENMC_CROSS_SECTIONS=\"$XD/cross_sections.xml\"
$SATIRLAR"
echo
if [ "$BASHRC" = 1 ]; then
    if grep -q "openmc_arayuz veri_indir" "$HOME/.bashrc" 2>/dev/null; then
        echo "~/.bashrc'de zaten bir openmc_arayuz bölümü var; değiştirilmedi. Gerekirse elle düzeltin:"
        echo "$SATIRLAR"
    else
        { echo ""; echo "# OpenMC verisi (openmc_arayuz veri_indir.sh)"; echo "$SATIRLAR"; } >> "$HOME/.bashrc"
        echo "~/.bashrc'ye eklendi. Yeni bir terminal açın ya da: source ~/.bashrc"
    fi
else
    echo "Bitti. Şu satırları ~/.bashrc dosyanıza ekleyin (ya da betiği --bashrc ile çalıştırın):"
    echo "$SATIRLAR"
fi
