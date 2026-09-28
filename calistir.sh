#!/usr/bin/env bash
# =============================================================================
#  calistir.sh  --  Ortami dogrulayip arayuzu acar
#
#  KULLANIM
#    ./calistir.sh                          bos modelle acilir
#    ./calistir.sh ornekler/pwr_17x17.json  verilen spec ile acilir
#
#  Paket kuruluysa (pip install -e . --no-deps) ayni is `openmc-arayuz`
#  komutuyla da yapilir. Uygulama logu: ~/.local/state/openmc_arayuz/
#  (XDG_STATE_HOME); arayuz hata verirse yolu asagida yazilir.
# =============================================================================
set -u
KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

hata() { echo "HATA: $*" >&2; exit 1; }

command -v openmc >/dev/null 2>&1 || hata "openmc PATH'te yok. 'conda activate openmc-env' calistirin."
python3 -c "import openmc" 2>/dev/null || hata "openmc Python paketi bulunamadi."
python3 -c "import PySide6" 2>/dev/null || hata "PySide6 bulunamadi. 'conda install -c conda-forge pyside6' gerekir."
[ -n "${OPENMC_CROSS_SECTIONS:-}" ] || echo "UYARI: OPENMC_CROSS_SECTIONS ayarli degil -- kosu basarisiz olur."
[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] || hata "Grafik oturum yok (DISPLAY/WAYLAND_DISPLAY bos)."
# Tukenme zinciri: yoksa ya da yarim inmisse UYARI (hata degil -- tukenme
# disindaki her sey calisir). Ilk indirme %13'te sessizce kesilmisti.
KOK="$KOK" python3 - <<'KONTROL' || true
import os, sys
sys.path.insert(0, os.environ.get("KOK", "."))
try:
    from cekirdek import veri_bilgi, tukenme
    d = veri_bilgi.zincir_dizini()
    kotu = [f for f in tukenme.ZINCIRLER.values()
            if not veri_bilgi.zincir_kontrol(os.path.join(d, f))[0]]
    if kotu:
        print("UYARI: tukenme zinciri eksik/bozuk: %s (dizin %s). Tukenme sekmesi calismaz."
              % (", ".join(kotu), d))
except Exception as e:
    print("UYARI: zincir kontrolu yapilamadi: %s" % e)
KONTROL

cd "$KOK" || hata "$KOK dizinine girilemedi."
python3 -m arayuz.ana_pencere "$@"
durum=$?
if [ "$durum" -ne 0 ]; then
    log=$(python3 -c "from cekirdek.gunluk import log_yolu; print(log_yolu())" 2>/dev/null)
    echo "Arayuz $durum koduyla kapandi. Ayrintilar: ${log:-~/.local/state/openmc_arayuz/openmc_arayuz.log}" >&2
fi
exit "$durum"
