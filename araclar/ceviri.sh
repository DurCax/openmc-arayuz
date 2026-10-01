#!/usr/bin/env bash
# =============================================================================
#  ceviri.sh  --  Ceviri kataloglarini cikarir, gunceller, birlestirir, derler
#
#  KULLANIM (depo kokunden, conda ortami etkin; Babel gerekir)
#    araclar/ceviri.sh               hepsi: cikar + guncelle + birlestir + derle
#    araclar/ceviri.sh cikar         locale/<parca>.pot sablonlarini uretir
#    araclar/ceviri.sh guncelle      locale/<dil>/LC_MESSAGES/<parca>.po gunceller
#                                    (yoksa olusturur)
#    araclar/ceviri.sh birlestir     parca .po'lari openmc_arayuz.po'da birlestirir
#    araclar/ceviri.sh derle         openmc_arayuz.po -> openmc_arayuz.mo
#
#  PARCALAR: cekirdek (cekirdek/) ve arayuz (arayuz/). Dalga 3'te iki ajan ayri
#  parcayi cevirir; birlestirme celisen ceviride durur. Parca .po yoksa
#  (baslangic) openmc_arayuz.po elle tutulur ve birlestirme atlanir.
#
#  ANAHTAR SOZCUKLER: _  _n:1,2  N_  pgettext:1c,2  (cekirdek/ceviri.py)
#  Kaynak dil Turkce (msgid); hedef diller DILLER'de.
# =============================================================================
set -euo pipefail
KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ALAN="openmc_arayuz"
LOCALE="$KOK/locale"
PARCALAR=(cekirdek arayuz)
DILLER=(en)

hata() { echo "HATA: $*" >&2; exit 1; }
command -v pybabel >/dev/null 2>&1 || hata "pybabel yok: 'conda install -c conda-forge babel'"

surum() {
    python3 -c "import sys; sys.path.insert(0, '$KOK'); from cekirdek.surum import surum; print(surum())"
}

cikar() {
    local s; s="$(surum)"
    for parca in "${PARCALAR[@]}"; do
        # Depo kokunden GORELI yol: .pot/.po kaynak yorumlarina makineye ozgu
        # mutlak yol (/home/...) yazilmasin (ticari hazirlik kurali).
        (cd "$KOK" && pybabel extract --no-default-keywords \
            -k _ -k _n:1,2 -k N_ -k pgettext:1c,2 \
            --project=openmc-arayuz --version="$s" \
            --sort-by-file --width=88 \
            -o "locale/$parca.pot" "$parca")
    done
}

guncelle() {
    for dil in "${DILLER[@]}"; do
        for parca in "${PARCALAR[@]}"; do
            local pot="$LOCALE/$parca.pot"
            local po="$LOCALE/$dil/LC_MESSAGES/$parca.po"
            [ -f "$pot" ] || hata "$pot yok; once: $0 cikar"
            local birlesik="$LOCALE/$dil/LC_MESSAGES/$ALAN.po"
            mkdir -p "$(dirname "$po")"
            if [ ! -f "$po" ] && [ -f "$birlesik" ]; then
                # Ilk parca: mevcut cevirileri kaybetmemek icin birlesik
                # katalogdan tohumla; update bu parcaya ait olmayanlari eler.
                cp "$birlesik" "$po"
            fi
            if [ -f "$po" ]; then
                pybabel update -i "$pot" -o "$po" -l "$dil" -D "$parca" --width=88
            else
                pybabel init -i "$pot" -o "$po" -l "$dil" -D "$parca" --width=88
            fi
        done
    done
}

birlestir() {
    for dil in "${DILLER[@]}"; do
        local dizin="$LOCALE/$dil/LC_MESSAGES"
        local parcalar=()
        for parca in "${PARCALAR[@]}"; do
            [ -f "$dizin/$parca.po" ] && parcalar+=("$dizin/$parca.po")
        done
        if [ ${#parcalar[@]} -eq 0 ]; then
            echo "$dil: parca katalog yok; $ALAN.po oldugu gibi kaliyor"
            continue
        fi
        python3 "$KOK/araclar/po_birlestir.py" "$dizin/$ALAN.po" "${parcalar[@]}"
    done
}

derle() {
    pybabel compile -d "$LOCALE" -D "$ALAN" --statistics
}

komut="${1:-hepsi}"
case "$komut" in
    cikar|guncelle|birlestir|derle) "$komut" ;;
    hepsi) cikar; guncelle; birlestir; derle ;;
    *) hata "bilinmeyen komut: $komut (cikar|guncelle|birlestir|derle|hepsi)" ;;
esac
