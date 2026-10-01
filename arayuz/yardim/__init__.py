# -*- coding: utf-8 -*-
"""
 arayuz/yardim  --  uygulama ici kullanim kilavuzu (SOZLESME iskeleti)

 Dalga 3 sozlesmesi (orkestrator, 01.10.2026):
   ac(bolum_kimligi, pencere=None)  kilavuzu verilen bolumde acar.
   BOLUMLER                         {bolum_kimligi: gorunen baslik}
   bolum_var(bolum_kimligi)         kimlik kilavuzda tanimli mi.

 Ajan 12 arayuzdeki baglantilari (Yardim menusu, F1, alan "?" dugmeleri,
 bulgu -> bolum, uygunluk paneli KILAVUZ_BOLUMU) BU API ile kurar.
 Ajan 13b icerigi (docs/kilavuz/) ve gercek gosterimi (QTextBrowser,
 cevrimdisi) bu dosyanin YERINE yazar; imzalar degismez.

 Iskelet davranisi: kilavuz henuz yok -> kullaniciya bildirim + log
 (sessiz hata yok).
"""

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

BOLUMLER = {}


def bolum_var(bolum_kimligi):
    """Kimlik kilavuzda tanimli mi."""
    return bolum_kimligi in BOLUMLER


def ac(bolum_kimligi, pencere=None):
    """Kilavuzu bolum_kimligi bolumunde acar. Iskelet: kilavuz henuz yok."""
    _log.info("kilavuz istendi: %s (iskelet; kilavuz henuz yok)", bolum_kimligi)
    if pencere is not None:
        from arayuz.bilesenler.bildirim import bildir
        bildir(pencere, _("Kullanım kılavuzu henüz eklenmedi (bölüm: {b}).")
               .format(b=bolum_kimligi), tur="bilgi")
    return False
