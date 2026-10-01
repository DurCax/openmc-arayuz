# syntax=docker/dockerfile:1
# =============================================================================
#  openmc-arayuz -- Docker imaji (OpenMC 0.16 + uygulama)
#
#  NUKLEER VERI IMAJA GOMULMEZ (ENDF/B-VIII.0 ~13 GB; ayrica verinin kendi
#  kullanim kosullari vardir -- THIRD_PARTY_LICENSES.md §3). Veri calisma
#  aninda /veri hacmine baglanir ya da kapsayicinin icinde bir kez indirilir:
#      docker/calistir.sh veri-indir            # /veri hacmine indirir (~20 GB bos alan)
#
#  DERLEME
#      docker/derle.sh                          # etiket pyproject.toml surumunden
#      docker/derle.sh --novnc                  # + tarayicidan erisim (noVNC)
#  (elle: docker build [--build-arg NOVNC=1] -t openmc-arayuz:<surum> .)
#
#  CALISTIRMA (ayrintilar: docker/calistir.sh --yardim)
#      docker/calistir.sh x11                   # Linux masaustu (X11 / XWayland)
#      docker/calistir.sh web                   # noVNC: http://localhost:6080/vnc.html
#      docker/calistir.sh kosu /opt/openmc-arayuz/ornekler/godiva_kriter.json --dizin kosu_godiva
#      docker/calistir.sh test                  # hizli test suiti (veri gerekmez)
#
#  WINDOWS (WSL2): Docker Desktop + WSL2 arka ucunda `x11` kipi WSLg ile
#  calisir (WSL2 dagitimindaki bir kabuktan docker/calistir.sh x11); WSLg yoksa
#  `web` kipi (noVNC) kullanilir. Veri hacmini WSL2 dosya sisteminde tutun
#  (/mnt/c altinda ~13 GB HDF5 okumasi cok yavastir).
#
#  LISANS: uygulama "tum haklari saklidir" (LICENSE); imaj yalniz izin verilen
#  kisilere dagitilir. Imajdaki ucuncu taraf bilesenler: THIRD_PARTY_LICENSES.md
#  (PySide6/Qt LGPL-3.0 dinamik baglanir, degistirilmedi).
# =============================================================================

# Tekrarlanabilir derleme icin etiketi sabitleyin (ornek: --build-arg MINIFORGE_ETIKETI=<surum>)
ARG MINIFORGE_ETIKETI=latest
FROM condaforge/miniforge3:${MINIFORGE_ETIKETI}

# 1 = noVNC/Xvfb/x11vnc katmani (tarayicidan erisim); 0 = yalniz X11 / komut satiri
ARG NOVNC=0
ARG KULLANICI_UID=1000

LABEL org.opencontainers.image.title="openmc-arayuz" \
      org.opencontainers.image.description="OpenMC reaktor modeli arayuzu (OpenMC 0.16)" \
      org.opencontainers.image.licenses="LicenseRef-Proprietary"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1

# Qt (xcb/EGL) calisma ani sistem kitapliklari -- CI ile ayni liste
# (.github/workflows/test.yml) + xcb eklentisinin X11 bagimliliklari.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        libegl1 libgl1 libopengl0 libxkbcommon0 libxkbcommon-x11-0 \
        libfontconfig1 libdbus-1-3 fonts-dejavu-core \
        libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
        libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxcb-xinerama0 \
        libxcb-xkb1 libx11-xcb1 libxrender1 libxi6 \
        curl ca-certificates xz-utils \
 && if [ "$NOVNC" = "1" ]; then \
        apt-get install -y --no-install-recommends \
            xvfb x11vnc novnc websockify fluxbox ; \
    fi \
 && rm -rf /var/lib/apt/lists/*

# conda ortami: environment.yml (openmc=0.16.0 sabit). Ayri katman: uygulama
# kodu degisince ortam yeniden kurulmaz.
COPY environment.yml /tmp/environment.yml
RUN mamba env create -y -f /tmp/environment.yml \
 && mamba clean -afy \
 && rm /tmp/environment.yml

ENV PATH=/opt/conda/envs/openmc-env/bin:$PATH \
    CONDA_DEFAULT_ENV=openmc-env \
    OPENMC_CROSS_SECTIONS=/veri/endfb-viii.0-hdf5/cross_sections.xml \
    OPENMC_CHAIN_FILE=/veri/chain/chain_endfb80_thermal.xml \
    QT_QPA_PLATFORM=xcb

# Uygulama: kaynak agaci /opt/openmc-arayuz (ikonlar, yazi tipleri, ornekler,
# locale kaynak agacindan okunur; bu yuzden duzenlenebilir kurulum).
WORKDIR /opt/openmc-arayuz
COPY . /opt/openmc-arayuz
# (derleme yalitimi setuptools>=77'yi PyPI'dan gecici olarak alir)
RUN pip install --no-deps -e . \
 && chmod +x docker/giris.sh veri_indir.sh \
 && useradd -m -u "$KULLANICI_UID" -s /bin/bash kullanici \
 && mkdir -p /veri /calisma \
 && chown kullanici:kullanici /veri /calisma

USER kullanici
WORKDIR /calisma
VOLUME ["/veri", "/calisma"]
EXPOSE 6080

ENTRYPOINT ["/opt/openmc-arayuz/docker/giris.sh"]
CMD ["yardim"]
