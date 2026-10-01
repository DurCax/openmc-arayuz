#!/usr/bin/env bash
# =============================================================================
#  docker/calistir.sh -- imaji ana makineden calistirir (docker run sarmalayicisi)
#
#  KULLANIM
#    docker/calistir.sh x11 [spec.json]     Linux X11/XWayland ya da WSL2 + WSLg
#    docker/calistir.sh web [spec.json]     noVNC: http://localhost:6080/vnc.html
#    docker/calistir.sh kosu <arguman...>   komut satiri kosusu (openmc-arayuz-kosu)
#    docker/calistir.sh veri-indir [--yalniz-zincir]
#    docker/calistir.sh veri-durum | test | kabuk
#
#  ORTAM DEGISKENLERI (hepsi istege bagli)
#    IMAJ         imaj adi                      (varsayilan openmc-arayuz:2.0.0rc1)
#    VERI         nukleer veri: ana makine dizini ya da adli hacim
#                 (varsayilan: adli hacim openmc-veri). Var olan bir veri
#                 dizini icin ornek: VERI=$HOME/nucdata (endfb-viii.0-hdf5/ ve
#                 chain/ alt dizinleri olmali; veri_indir.sh duzeni)
#    CALISMA      model ve kosu dizini          (varsayilan: bulunulan dizin)
#    NOVNC_PORTU  web kipinde ana makine portu  (varsayilan 6080; yalniz 127.0.0.1)
#    VNC_PAROLASI web kipinde VNC parolasi      (verilmezse parolasiz, yalniz yerel)
#    IS_PARCACIGI OMP_NUM_THREADS               (varsayilan: ayarlanmaz, OpenMC secer)
# =============================================================================
set -euo pipefail

IMAJ="${IMAJ:-openmc-arayuz:2.0.0rc1}"
VERI="${VERI:-openmc-veri}"
CALISMA="${CALISMA:-$PWD}"
NOVNC_PORTU="${NOVNC_PORTU:-6080}"

hata() { echo "HATA: $*" >&2; exit 1; }
command -v docker >/dev/null || hata "docker bulunamadi."

kip="${1:-yardim}"
[ $# -gt 0 ] && shift
if [ "$kip" = "yardim" ] || [ "$kip" = "-h" ] || [ "$kip" = "--yardim" ]; then
    awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0"
    exit 0
fi

secenekler=(--rm -it
    -v "$VERI:/veri"
    -v "$CALISMA:/calisma"
    --user "$(id -u):$(id -g)"
    -e HOME=/tmp)
[ -n "${IS_PARCACIGI:-}" ] && secenekler+=(-e "OMP_NUM_THREADS=$IS_PARCACIGI")

case "$kip" in
    x11)
        [ -n "${DISPLAY:-}" ] || hata "DISPLAY bos (grafik oturum yok). 'web' kipini deneyin."
        secenekler+=(-e "DISPLAY=$DISPLAY" -v /tmp/.X11-unix:/tmp/.X11-unix:ro)
        # WSLg (Windows 11 WSL2): Wayland/PulseAudio soketleri /mnt/wslg altinda
        [ -d /mnt/wslg ] && secenekler+=(-v /mnt/wslg:/mnt/wslg
            -e "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-}" -e "XDG_RUNTIME_DIR=/mnt/wslg/runtime-dir")
        # Xauthority: ana makinede xhost acmak yerine cerez dosyasini paylas
        if [ -n "${XAUTHORITY:-}" ] && [ -f "$XAUTHORITY" ]; then
            secenekler+=(-e XAUTHORITY=/tmp/.Xauthority -v "$XAUTHORITY:/tmp/.Xauthority:ro")
        fi
        exec docker run "${secenekler[@]}" "$IMAJ" gui "$@" ;;
    web)
        secenekler+=(-p "127.0.0.1:${NOVNC_PORTU}:6080")
        [ -n "${VNC_PAROLASI:-}" ] && secenekler+=(-e "VNC_PAROLASI=$VNC_PAROLASI")
        exec docker run "${secenekler[@]}" "$IMAJ" web "$@" ;;
    kosu|veri-indir|veri-durum|test|kabuk)
        exec docker run "${secenekler[@]}" "$IMAJ" "$kip" "$@" ;;
    *)
        hata "bilinmeyen kip: $kip (docker/calistir.sh yardim)" ;;
esac
