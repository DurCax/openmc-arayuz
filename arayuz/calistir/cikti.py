# -*- coding: utf-8 -*-
"""
cikti.py -- QProcess kosusunun ham ciktisi: kosu.log'a yazma ve kullaniciya
gosterilecek kayip parcacik / OpenMC uyari ozeti (M5).

    gunlugu_yaz(dizin, satirlar)  -> bool   (kosu.log; terminal kosucusuyla ayni ad)
    uyari_ozeti(dizin)            -> (satirlar, seviye)  seviye "hata" | "uyari" | ""

Terminal kosucusu (cekirdek/kosucu.py) ciktiyi kosu.log'a yazar; arayuz
eskiden yalnizca ekrana yaziyordu ve rapor (K4 izlenebilirlik), uygunluk
denetimi (K3 kayip parcacik) ve bu ozet kosu dizininde log bulamiyordu.
Metinler uygunluk_denetimi.ayristir.ozet_satirlari'ndandir (terminalle ayni).
"""

import os

from cekirdek.gunluk import kaydedici
from cekirdek.uygunluk_denetimi import ayristir

_log = kaydedici(__name__)


def gunlugu_yaz(dizin, satirlar):
    """Ham cikti satirlarini <dizin>/kosu.log'a yazar. DONER True: yazildi
    (yazilamazsa loglanir ve False doner; kosu sonucu yine gosterilir)."""
    if not dizin or not os.path.isdir(dizin):
        return False
    yol = os.path.join(dizin, ayristir.LOG_ADI)
    try:
        with open(yol, "w", encoding="utf-8") as f:
            f.write("\n".join(satirlar))
            f.write("\n")
        return True
    except OSError:
        _log.warning("koşu günlüğü yazılamadı: %s", yol, exc_info=True)
        return False


def uyari_ozeti(dizin):
    """Kosu dizininin kayip parcacik / OpenMC hata-uyari ozeti.
    DONER (satirlar, seviye); sorun yoksa ([], "")."""
    if not dizin:
        return [], ""
    ozet = ayristir.cikti_ozeti(dizin)
    satirlar = ayristir.ozet_satirlari(ozet)
    if not satirlar:
        return [], ""
    return satirlar, ("hata" if (ozet.kayip_parcacik or ozet.hatalar) else "uyari")
