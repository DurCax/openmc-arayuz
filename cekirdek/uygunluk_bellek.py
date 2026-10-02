# -*- coding: utf-8 -*-
"""
================================================================================
 uygunluk_bellek.py  --  Icerige gore kucuk LRU bellek (v3 H1)
================================================================================

 NEDEN (olculdu, cProfile; SFR-MET1000 gelismis modda)
   uygunluk kurallari (gecerli_sekmeler, model_ozeti, ayar_alanlari ...) ve
   tukenme sekmesinin ornek sayimi her cagrida agac gezintisi yapiyordu
   (geometri/gezinti.py; SFR'de bir gezinti ~0.4 s CPU). Tek bir tus vurusunda
   7, gelismise geciste ~50 gezinti vardi: tus 2.9 s, gecis 33 s.
   Ayni icerik icin sonuc aynidir; burada bir kez hesaplanip saklanir.

 ANAHTAR
   icerik_anahtari(nesne): kanonik JSON'un SHA-256 ozeti (cekirdek/onbellek.ozet
   ile ayni kural). Anahtar HER cagrida icerikten yeniden uretilir: spec yerinde
   degistirilse bile yeni icerik yeni anahtardir, bayat sonuc donmez. Maliyeti
   SFR spec'inde ~1 ms (gezintinin ~1/400'u).

 DEGISMEZLIK
   Bellege yalniz degismez degerler konur (frozenset, tuple, str, sayi,
   MappingProxyType). Degistirilebilir bir sonuc isteyen cagiran kendi
   kopyasini uretir (bkz. uygunluk_geometri.geometri_icerigi).

 KULLANIM
   _BELLEK = Bellek("ad")
   deger = _BELLEK.al(anahtar, lambda: pahali_hesap())
   temizle()   # butun bellekler (testler; spec disi bir sey degistiyse)
================================================================================
"""

import collections
import hashlib
import json
import threading

# Ayni anda acik kalan farkli icerik sayisi: geri al/yinele ve iki-uc farkli
# editor durumu arasinda gidip gelmek icin yeterli; SFR'de bir kayit birkac
# yuz KB (ziyaret ozeti), sinir bellek kullanimini da sinirlar.
VARSAYILAN_SINIR = 8

_BELLEKLER = []


def icerik_anahtari(nesne):
    """JSON'a cevrilebilir nesnenin icerige dayali kimligi (SHA-256, 32 hane)."""
    ham = json.dumps(nesne, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), default=str)
    return hashlib.sha256(ham.encode("utf-8")).hexdigest()[:32]


class Bellek(object):
    """Anahtar -> degismez deger; en eski kullanilan atilir (LRU). Is parcacigi
    guvenli: hesap kilit DISINDA yapilir (iki is parcacigi ayni anahtari ayni
    anda hesaplarsa ikisi de ayni sonucu yazar)."""

    def __init__(self, ad, sinir=VARSAYILAN_SINIR):
        if sinir < 1:
            raise ValueError("bellek siniri en az 1 olmali: %r" % sinir)
        self.ad = ad
        self.sinir = sinir
        self._kayit = collections.OrderedDict()
        self._kilit = threading.Lock()
        _BELLEKLER.append(self)

    def al(self, anahtar, uret):
        with self._kilit:
            if anahtar in self._kayit:
                self._kayit.move_to_end(anahtar)
                return self._kayit[anahtar]
        deger = uret()
        with self._kilit:
            self._kayit[anahtar] = deger
            while len(self._kayit) > self.sinir:
                self._kayit.popitem(last=False)
        return deger

    def temizle(self):
        with self._kilit:
            self._kayit.clear()

    def __len__(self):
        return len(self._kayit)


def temizle():
    """Butun bellekleri bosaltir."""
    for b in _BELLEKLER:
        b.temizle()
