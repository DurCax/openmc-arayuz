# -*- coding: utf-8 -*-
"""
================================================================================
 onbellek.py  --  Model onbellegi
================================================================================

 SORUN
   kurucu.kur() bir spec icin openmc.Model kurar; olculen maliyet 11-24 ms
   (buyuk kismi malzemelerin element -> nuklid acilimi). Arayuzde ayni spec
   icin birden fazla yerden cagriliyordu:
     - onizleme cizimi
     - Kor sekmesinin "toplam olcu" ozeti
     - tally mesh sinirlarinin hesabi
     - XML disa aktarma
   Tek bir kullanici degisikliginde iki kez kurulup atiliyordu.

 COZUM
   Spec'in kanonik JSON temsilinin SHA-256 ozetine gore kucuk bir LRU onbellek.
   Spec degismediyse ayni Model nesnesi geri verilir.

 !!! DIKKAT !!!
   Donen Model nesnesi PAYLASILIR. Uzerinde degisiklik yapilmamalidir.
   Kosu icin (XML yazma, run) her zaman taze bir model kurun: kur_taze().
   Sebep: openmc nesneleri global id sayaclari tutar ve model.run() calisma
   dizinine baglidir; paylasilan nesneyi kosuya sokmak sasirtici yan etkiler
   uretir. Onbellek yalnizca OKUMA amaclidir (cizim, olcu, dogrulama).
================================================================================
"""

import collections
import hashlib
import json

_ONBELLEK = collections.OrderedDict()
_SINIR = 8

# Istatistik -- ayar/profil icin
isabet = 0
kacirma = 0


def ozet(spec):
    """Spec'in icerige dayali kimligi (SHA-256, kisaltilmis)."""
    ham = json.dumps(spec, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), default=str)
    return hashlib.sha256(ham.encode("utf-8")).hexdigest()[:32]


def kur_onbellekli(spec):
    """
    (model, bilgi) dondurur -- ayni spec icin yeniden kurmaz.
    SADECE OKUMA amacli kullanin (cizim, olcu, dogrulama).
    """
    global isabet, kacirma
    from cekirdek import kurucu

    anahtar = ozet(spec)
    if anahtar in _ONBELLEK:
        isabet += 1
        _ONBELLEK.move_to_end(anahtar)
        return _ONBELLEK[anahtar]

    kacirma += 1
    sonuc = kurucu.kur(spec)
    _ONBELLEK[anahtar] = sonuc
    while len(_ONBELLEK) > _SINIR:
        _ONBELLEK.popitem(last=False)
    return sonuc


def kur_taze(spec):
    """
    Onbellegi atlayarak yeni bir Model kurar.
    Kosu, XML yazma ve modeli degistirecek her islem bunu kullanmalidir.
    """
    from cekirdek import kurucu
    return kurucu.kur(spec)


def temizle():
    """Onbellegi bosaltir (spec disi bir sey degistiyse, orn. veri kutuphanesi)."""
    _ONBELLEK.clear()


def istatistik():
    """(isabet, kacirma, oran) dondurur."""
    toplam = isabet + kacirma
    return isabet, kacirma, (isabet / toplam if toplam else 0.0)
