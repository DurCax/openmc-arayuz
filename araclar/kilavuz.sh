#!/usr/bin/env bash
# =============================================================================
#  kilavuz.sh  --  Kullanim kilavuzunu (docs/kilavuz/) derleme zamaninda
#                  HTML + PDF'e cevirir; sozluk ve ekran goruntulerini yeniler
#
#  KULLANIM (depo kokunden ya da herhangi bir yerden; conda ortami etkin)
#    araclar/kilavuz.sh                    TR + EN -> build/kilavuz/<dil>/kilavuz.{html,pdf}
#    araclar/kilavuz.sh --dil tr           yalniz Turkce
#    araclar/kilavuz.sh --cikti /tmp/k     baska cikti dizini
#    araclar/kilavuz.sh --bicim html       yalniz HTML (ya da pdf)
#    araclar/kilavuz.sh --sozluk           10-sozluk.md tablolarini docs/SOZLUK.md'den yenile
#    araclar/kilavuz.sh --ekran tr         ekran goruntulerini yeniden cek (araclar/kilavuz_ekran.py)
#    araclar/kilavuz.sh --yardim
#
#  Cevirici Qt'nin kendisidir (QTextDocument Markdown -> HTML / QPdfWriter);
#  yeni bagimlilik yoktur (Qt LGPL). Basliksiz calisir (QT_QPA_PLATFORM=offscreen).
#  Uygulama ici gosterim derleme ISTEMEZ: arayuz/yardim Markdown'i dogrudan okur.
# =============================================================================
set -euo pipefail
KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
PY="${PYTHON:-python3}"

yardim() { sed -n '3,18p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,2\}//'; }
hata() { echo "HATA: $*" >&2; exit 2; }

DIL="tr,en"
CIKTI="$KOK/build/kilavuz"
BICIM="html,pdf"
while [ $# -gt 0 ]; do
    case "$1" in
        --dil)    [ $# -ge 2 ] || hata "--dil deger ister"; DIL="$2"; shift 2 ;;
        --cikti)  [ $# -ge 2 ] || hata "--cikti deger ister"; CIKTI="$2"; shift 2 ;;
        --bicim)  [ $# -ge 2 ] || hata "--bicim deger ister"; BICIM="$2"; shift 2 ;;
        --sozluk) cd "$KOK" && exec "$PY" -m arayuz.yardim.derle --sozluk ;;
        --ekran)  [ $# -ge 2 ] || hata "--ekran dil ister (tr|en)"
                  cd "$KOK" && exec "$PY" araclar/kilavuz_ekran.py --dil "$2" ;;
        -h|--yardim|--help) yardim; exit 0 ;;
        *) hata "bilinmeyen secenek: $1 (--yardim)" ;;
    esac
done

command -v "$PY" >/dev/null 2>&1 || hata "$PY yok: conda activate openmc-env"
cd "$KOK"
"$PY" -m arayuz.yardim.derle --dil "$DIL" --cikti "$CIKTI" --bicim "$BICIM"
echo "kilavuz -> $CIKTI"
