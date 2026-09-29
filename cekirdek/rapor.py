# -*- coding: utf-8 -*-
"""
rapor.py -- model ve kosu raporu (TASLAK; Dalga 2 on-commit 6, uygulama Ajan 10).

SOZLESME (DONUK; testler/test_rapor_sozlesme.py):

    from cekirdek import rapor
    try:
        sonuc = rapor.olustur(spec, kosu_dizini, "rapor.pdf", "pdf")
    except rapor.RaporHatasi as e:       # ValueError alt sinifi
        goster(str(e))                   # kullaniciya gosterilecek Turkce metin
    sonuc.yol       # yazilan dosyanin mutlak yolu
    sonuc.uyarilar  # tuple[str, ...] (ornek: "tekrarlanabilirlik: ... bilinmiyor")

- spec DEGISMEZ (okunur).
- kosu_dizini None -> yalniz model raporu (kosu sonucu bolumleri yok).
- bicim: "html" | "pdf" (BICIMLER). PDF cekirdek/rapor_pdf.py'de, Qt TEMBEL
  import edilir; bu modul modul duzeyinde PySide6 ice aktarmaz.
- Bilinmeyen tekrarlanabilirlik alani "bilinmiyor" yazilir ve loglanir.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

BICIMLER = ("html", "pdf")


class RaporHatasi(ValueError):
    """Rapor olusturulamadi; metni kullaniciya gosterilir."""


@dataclass(frozen=True)
class RaporSonucu:
    yol: str
    uyarilar: Tuple[str, ...] = ()


def olustur(spec: dict, kosu_dizini: Optional[str], yol: str, bicim: str) -> RaporSonucu:
    """spec (+ varsa kosu_dizini sonuclari) icin `yol`a `bicim` biciminde rapor yazar.
    TASLAK: Ajan 10 uygular."""
    raise NotImplementedError("rapor.olustur henüz uygulanmadı (Dalga 2, Ajan 10)")
