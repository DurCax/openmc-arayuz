#!/usr/bin/env bash
# =============================================================================
#  docker/giris.sh -- kapsayicinin giris noktasi (ENTRYPOINT)
#
#  KIPLER
#    gui [spec.json]        arayuzu acar; DISPLAY (X11/XWayland/WSLg) gerekir
#    web [spec.json]        Xvfb + x11vnc + noVNC; tarayicidan
#                           http://localhost:6080/vnc.html (imaj NOVNC=1 ile
#                           derlenmis olmali). VNC_PAROLASI verilirse sorulur.
#    kosu <argumanlar>      openmc-arayuz-kosu; goreli yollar /calisma'ya gore.
#                           Ornekler imajda: /opt/openmc-arayuz/ornekler/
#    veri-indir [secenek]   veri_indir.sh --hedef /veri (ornek: --yalniz-zincir)
#    veri-durum             /veri altindaki kutuphane ve zincirleri denetler
#    test                   hizli test suiti (nukleer veri gerekmez)
#    kabuk                  bash
#    yardim                 bu metin
#
#  Ortam: OPENMC_CROSS_SECTIONS ve OPENMC_CHAIN_FILE imajda /veri altina
#  ayarlidir; baska bir yerdeyse `docker run -e ...` ile degistirin.
# =============================================================================
set -euo pipefail

UYGULAMA=/opt/openmc-arayuz
NOVNC_PORTU="${NOVNC_PORTU:-6080}"
EKRAN_BOYUTU="${EKRAN_BOYUTU:-1600x1000x24}"

# bas yorum blogu (ilk yorum olmayan satira kadar)
yardim() { awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"; }
hata() { echo "HATA: $*" >&2; exit 1; }

veri_uyarisi() {
    if [ ! -f "${OPENMC_CROSS_SECTIONS:-}" ]; then
        echo "UYARI: tesir kesiti kutuphanesi yok (${OPENMC_CROSS_SECTIONS:-ayarsiz})." >&2
        echo "       Model kurulur ve dogrulanir ama Monte Carlo kosusu calismaz." >&2
        echo "       Veriyi /veri'ye baglayin ya da: docker/calistir.sh veri-indir" >&2
    fi
}

arayuz_ac() {
    cd /calisma
    exec openmc-arayuz "$@"
}

web_kipi() {
    command -v Xvfb >/dev/null && command -v x11vnc >/dev/null && command -v websockify >/dev/null \
        || hata "Bu imajda noVNC yok. 'docker build --build-arg NOVNC=1 ...' ile derleyin."
    local novnc_dizini=/usr/share/novnc
    [ -d "$novnc_dizini" ] || hata "$novnc_dizini yok (novnc paketi)."
    export DISPLAY=:99
    Xvfb "$DISPLAY" -screen 0 "$EKRAN_BOYUTU" -nolisten tcp &
    sleep 1
    fluxbox >/dev/null 2>&1 &
    local vnc_secenek=(-nopw)
    if [ -n "${VNC_PAROLASI:-}" ]; then
        mkdir -p "$HOME/.vnc"
        x11vnc -storepasswd "$VNC_PAROLASI" "$HOME/.vnc/parola" >/dev/null
        vnc_secenek=(-rfbauth "$HOME/.vnc/parola")
    else
        echo "UYARI: VNC_PAROLASI verilmedi; port yalniz bu makineye acilmalidir (-p 127.0.0.1:...)." >&2
    fi
    x11vnc -display "$DISPLAY" -forever -shared -localhost -rfbport 5900 \
        "${vnc_secenek[@]}" -quiet &
    websockify --web "$novnc_dizini" "$NOVNC_PORTU" localhost:5900 >/dev/null 2>&1 &
    echo "Tarayicida acin: http://localhost:${NOVNC_PORTU}/vnc.html"
    arayuz_ac "$@"
}

kip="${1:-yardim}"
[ $# -gt 0 ] && shift
case "$kip" in
    gui)
        [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] \
            || hata "DISPLAY bos. X11 soketini baglayin (docker/calistir.sh x11) ya da 'web' kipini kullanin."
        veri_uyarisi
        arayuz_ac "$@" ;;
    web)
        veri_uyarisi
        web_kipi "$@" ;;
    kosu)
        veri_uyarisi
        exec openmc-arayuz-kosu "$@" ;;
    veri-indir)
        exec "$UYGULAMA/veri_indir.sh" --hedef /veri "$@" ;;
    veri-durum)
        cd "$UYGULAMA"
        exec python - <<'DURUM'
import os
from cekirdek import tukenme, veri_bilgi
xs = os.environ.get("OPENMC_CROSS_SECTIONS", "")
print("kutuphane :", xs, "->", "var" if os.path.isfile(xs) else "YOK")
d = veri_bilgi.zincir_dizini()
for ad in sorted(set(tukenme.ZINCIRLER.values())):
    tamam, mesaj, _n = veri_bilgi.zincir_kontrol(os.path.join(d, ad))
    print("zincir    :", ad, "->", "tamam" if tamam else mesaj)
DURUM
        ;;
    test)
        cd "$UYGULAMA"
        export QT_QPA_PLATFORM=offscreen OPENMC_ARAYUZ_DIYALOGSUZ=1
        exec python -m pytest -m "hizli and not veri" -q -p no:cacheprovider "$@" ;;
    kabuk)
        exec bash "$@" ;;
    yardim|-h|--help|--yardim)
        yardim ;;
    *)
        hata "bilinmeyen kip: $kip (yardim)" ;;
esac
