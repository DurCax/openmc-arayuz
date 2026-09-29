# -*- coding: utf-8 -*-
"""
sekme_arayuzu.py -- kabuk <-> sekme sozlesmesi (Dalga 2 on-commit 4).

Kabuk (Ajan 6: ust baslik, komut paleti, "bulguya git") sekmelerden yalniz
su ISTEGE BAGLI uc yontemi bekler. Sekme yontemi tanimlamazsa asagidaki
modul islevleri varsayilani dondurur; boylece Ajan 7/8/8c sekmelerine
yontem eklemek birbirini beklemez.

    class BirSekme(SekmeTabani):
        def baslik_eylemleri(self):   # ust baslikta, sekme adinin yaninda
            return (self.e_ekle,)     # QtGui.QAction dizisi
        def komutlar(self):           # Ctrl+K komut paletinde
            return (self.e_ekle, self.e_sil)
        def odakla(self, yer):        # "bulguya git": bulgu.yer (dogrula)
            return self._satiri_sec(yer)   # bulunduysa True

Kabuk tarafi:

    from arayuz.pencere import sekme_arayuzu as sa
    sa.baslik_eylemleri(sekme)  -> tuple[QAction, ...]   (varsayilan ())
    sa.komutlar(sekme)          -> tuple[QAction, ...]   (varsayilan ())
    sa.odakla(sekme, yer)       -> bool                  (varsayilan False)

Eylemler QtGui.QAction'dir (menulerle ayni tur): metin, kisayol, ipucu,
etkinlik ve tetikleme tek yerde kalir. DONUK sekme uyeleri (spec_yukle,
kapi_ayarla, ...) testler/test_sekme_sozlesmesi.py'de listelenir.
"""

from typing import Protocol, Sequence, runtime_checkable

from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

UYELER = ("baslik_eylemleri", "komutlar", "odakla")


@runtime_checkable
class SekmeArayuzu(Protocol):
    """Kabugun sekmeden bekledigi istege bagli yuz (tamami ya da bir kismi)."""

    def baslik_eylemleri(self) -> Sequence:   # Sequence[QtGui.QAction]
        ...

    def komutlar(self) -> Sequence:           # Sequence[QtGui.QAction]
        ...

    def odakla(self, yer: str) -> bool:
        ...


def _eylem_dizisi(sekme, ad):
    yontem = getattr(sekme, ad, None)
    if yontem is None:
        return ()
    sonuc = yontem()
    if sonuc is None:
        return ()
    if isinstance(sonuc, (str, bytes)) or not hasattr(sonuc, "__iter__"):
        _log.warning("%s.%s() bir eylem dizisi dondurmedi: %r",
                     type(sekme).__name__, ad, sonuc)
        return ()
    return tuple(sonuc)


def baslik_eylemleri(sekme):
    """Sekmenin ust baslik eylemleri (tanimsizsa ())."""
    return _eylem_dizisi(sekme, "baslik_eylemleri")


def komutlar(sekme):
    """Sekmenin komut paleti eylemleri (tanimsizsa ())."""
    return _eylem_dizisi(sekme, "komutlar")


def odakla(sekme, yer):
    """Sekme 'yer'i (dogrulama bulgusunun yeri) kendi icinde odaklar; bulduysa
    True. Yontem tanimsizsa False (kabuk yalniz sekmeye gecer)."""
    yontem = getattr(sekme, "odakla", None)
    if yontem is None:
        return False
    return bool(yontem(yer))
