# -*- coding: utf-8 -*-
"""
 istek_sirasi.py  --  Tek cizim iscisine turlere gore sirali istek (Qt'siz)

 Istemci (arayuz/onizleme_istemci.py) yalniz EN SON istegin yanitlarini iletir:
 yeni istek eskisini iptal eder. Goruntuleyicide kesit, kaynak ve 3B istekleri
 ayni isciyi paylasir; bir kaynak istegi suren kesiti iptal etmemeli. Kural:
   - ayni turden yeni istek: hemen gider (suren ayni turdeki isi iptal eder),
   - farkli turden: suren is bitince gider; bekleyen her turden yalniz son istek
     tutulur (aradakiler atlanir), gelis sirasiyla.
"""

from typing import Any, Callable, Optional


class IstekSirasi:
    """Istemci sarmalayici; `iste` hemen doner."""

    def __init__(self, gonder: Callable[[dict], int]):
        self._gonder = gonder
        self._suren: Optional[tuple] = None          # (tur, no)
        self._bekleyen: dict = {}

    def iste(self, tur: str, istek: dict) -> None:
        if self._suren is None or self._suren[0] == tur:
            self._bekleyen.pop(tur, None)
            # Gonderim sirasinda istemci cokmeyi (coktu -> sifirla) ESZAMANLI yayabilir:
            # suren once jetonla yazilir; donuste hala o jeton degilse dokunulmaz.
            jeton = object()
            self._suren = (tur, jeton)
            no = self._gonder(istek)
            if self._suren is not None and self._suren[1] is jeton:
                self._suren = (tur, no)
            return
        self._bekleyen.pop(tur, None)
        self._bekleyen[tur] = istek                  # sona eklenir (gelis sirasi)

    def tur(self, no: Any) -> Optional[str]:
        """Yanitin istek turu; guncel istegin degilse None."""
        if self._suren is not None and self._suren[1] == no:
            return self._suren[0]
        return None

    def suren_tur(self) -> Optional[str]:
        """Iscide suren istegin turu (yoksa None)."""
        return self._suren[0] if self._suren is not None else None

    def bitti(self, no: Any) -> None:
        """Guncel istek bitti ('son'): siradakini gonderir."""
        if self._suren is not None and self._suren[1] == no:
            self.sifirla()

    def sifirla(self) -> None:
        """Suren istek yok sayilir (isci coktu) ve bekleyen gonderilir."""
        self._suren = None
        if self._bekleyen:
            tur = next(iter(self._bekleyen))
            self.iste(tur, self._bekleyen.pop(tur))

    def mesgul_mu(self) -> bool:
        return self._suren is not None or bool(self._bekleyen)
