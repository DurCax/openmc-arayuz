#!/usr/bin/env bash
# =============================================================================
#  veri_indir.sh  --  OpenMC nükleer verisini indirir ve doğrular
#
#  v3'ten beri bu betik yalnız bir kabuktur: işi cekirdek/veri_indir.py yapar
#  (arayüzdeki "Veri ve kütüphaneler" sayfasıyla AYNI kod). Katalog:
#  cekirdek/veri_katalogu.json (kaynak: https://openmc.org/data, erişim tarihi
#  katalogda). Güvenlik: yalnız https + katalogdaki alan adları, kesintide
#  kaldığı yerden sürdürme (Range), bayt sayısı ve sha256 denetimi, geçici
#  dosyadan atomik taşıma, disk alanı denetimi, güvenli arşiv açma.
#
#  KULLANIM
#    ./veri_indir.sh --liste                 katalogu listeler
#    ./veri_indir.sh                         ENDF/B-VIII.0 + termal/hızlı/CASL
#                                            zincirleri ~/nucdata altına
#    ./veri_indir.sh --hedef DIZIN           başka bir dizine
#    ./veri_indir.sh --kutuphane jendl-5     başka bir kütüphane (--liste)
#    ./veri_indir.sh --zincir casl-termal    yalnız seçilen zincir(ler)
#    ./veri_indir.sh --yalniz-zincir         yalnız tükenme zincirleri
#    ./veri_indir.sh --bashrc                bitince ortam değişkenlerini
#                                            ~/.bashrc'ye ekler
#  Seçim uygulama ayarına da yazılır (~/.config/openmc_arayuz/veri.json);
#  arayüz ortam değişkeni olmadan da bulur.
#
#  PYTHON ortam değişkeni yorumlayıcıyı seçer (varsayılan python3; openmc'nin
#  kurulu olduğu conda ortamı etkin olmalı).
# =============================================================================
set -euo pipefail
KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-}" in
    -h|--yardim) sed -n '2,28p' "$0"; exit 0 ;;
esac
export PYTHONPATH="$KOK${PYTHONPATH:+:$PYTHONPATH}"
exec "${PYTHON:-python3}" -m cekirdek.veri_indir "$@"
