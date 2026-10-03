# Olcumler (P1, 03.10.2026, Ubuntu 24.04 uzerinde uretildi/denendi)

- Paket: `dist/openmc-arayuz-2.0.0-Linux-x86_64.sh` = 409 MB (428 315 179 bayt); kurulu onek 1,7 GB.
- Uretim: ilk kez ~5,5 dk (paket indirme), onbellekli 25-30 sn (`uret.sh`).
- Kurulum (`bash paket.sh -b -p ONEK`, temiz HOME, `env -i`): 32 sn.
- Cozumlenen: python 3.13, openmc 0.16.0 `nodagmc_nompi_py313*`, pyside6 6.11, numpy, scipy, pandas, matplotlib-base, h5py, babel.
- glibc alt siniri: **2.28**. Kurulan 130 conda paketinden 129'u `__glibc >=2.17`,
  `libraqm` (matplotlib/Pillow metin yerlesimi) `__glibc >=2.28`. ELF sembol taramasi
  (1108 dosya): en yuksek `GLIBC_2.17`. Yani Ubuntu 20.04 (2.31), 22.04 (2.35), 24.04 (2.39),
  Fedora >= 29, Debian >= 10 yeterli. Uretim makinesinin glibc'i (2.39) paketi etkilemez.
- Ek sistem kitapligi: Qt xcb icin X11/xkb/EGL (Docker imajindaki liste: libegl1 libgl1
  libxkbcommon-x11-0 libxcb-cursor0 ...). Masaustu Ubuntu/Fedora'da bunlar kuruludur;
  yalniz-kabuk (minimal) imajlarda eksik olabilir. `offscreen` platformu bunlari istemez.
- conda-pack karsilastirmasi: 577 MB tar.gz.
- Kisa kosu (paketten, `godiva_kriter.json`, OMP 4 is parcacigi): 18 sn, nukleer veri disaridan.
- Docker/podman bu makinede YOK: temiz Ubuntu 22.04 kapsayicisi denenemedi; en yakin deneme
  temiz HOME + `env -i` + PATH=/usr/bin:/bin ile yapildi (testler/test_paket_kurulum.py).
  Gercek 22.04 denemesi P3'te (docker kurulunca).
