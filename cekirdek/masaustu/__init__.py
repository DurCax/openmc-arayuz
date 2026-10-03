# -*- coding: utf-8 -*-
"""
masaustu -- Linux masaustu butunlesmesi (v3 P2): menu girdisi (.desktop), uygulama
simgesi (hicolor), ".json" proje dosyasi icin ozel MIME turu ve "ile ac" iliskisi.

  python -m cekirdek.masaustu kur [--exec YOL] [--bos-calistir] [--varsayilan-yapma]
  python -m cekirdek.masaustu kaldir
  python -m cekirdek.masaustu durum

Hem `pip install` hem constructor kurulumunda aynidir (yalniz standart kutuphane;
xdg araclari varsa kullanilir, yoksa dosyalar yine yazilir). Ayrintilar: kurulum.py.
"""

from cekirdek.masaustu.kurulum import (  # noqa: F401
    UYGULAMA_KIMLIGI, MIME_TURU, MasaustuHatasi, kur, kaldir, durum, simge_yolu)
