# -*- coding: utf-8 -*-
"""
test_sozlesme.py -- cekirdek/uygunluk.py'nin IMZA sozlesmesi.

Arayuz (ana pencere, sekmeler) bu fonksiyonlara dayanir ve farkli gelistiriciler
paralel calisir. Bir imza degisirse diger taraf sessizce bozulur; bu test
imzalari ve donus bicimlerini sabitler. Ic mantigin dogrulugu
test_uygunluk.py'dedir.
"""

import inspect
import os

from testler.ortak_test import kontrol, ORNEK


def test_uygunluk_sozlesmesi():
    print("\n[S] UYGUNLUK SOZLESMESI: imzalar ve donus bicimleri")
    from cekirdek import sema, uygunluk as u
    beklenen = {
        "malzeme_rolleri": ["spec"], "rol_malzemeleri": ["spec", "rol"],
        "model_ozeti": ["spec"], "gecerli_sekmeler": ["spec"],
        "kor_turleri": ["spec"], "parca_turleri": ["spec"],
        "kor_alanlari": ["tur"], "sinir_secenekleri": ["spec", "yuzey"],
        "ayar_alanlari": ["spec"], "kaynak_secenekleri": ["spec"],
        "guc_cubuklari": ["spec"], "tukenme_uygun": ["spec"],
        "gecerli_hedefler": ["spec", "tarama_turu"],
        "gecerli_taramalar": ["spec", "amac"],
    }
    for ad, param in beklenen.items():
        fn = getattr(u, ad, None)
        kontrol("uygunluk.%s(%s) var" % (ad, ", ".join(param)),
                fn is not None and list(inspect.signature(fn).parameters) == param)
    kontrol("SEKMELER sirasi sabit",
            u.SEKMELER == ("malzemeler", "parcalar", "demet", "kor", "ayarlar",
                           "calistir", "analiz", "tukenme"))
    sp = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    oz = u.model_ozeti(sp)
    kontrol("model_ozeti anahtarlari",
            set(oz) == {"tur", "boyut", "mod", "kafes", "kontrol_cubugu", "tambur", "fisil"})
    kontrol("gecerli_sekmeler SEKMELER alt kumesi ve sirali",
            [s for s in u.SEKMELER if s in u.gecerli_sekmeler(sp)] == u.gecerli_sekmeler(sp))
    kontrol("tukenme_uygun (bool, str)",
            isinstance(u.tukenme_uygun(sp)[0], bool) and isinstance(u.tukenme_uygun(sp)[1], str))


HIZLI = [test_uygunluk_sozlesmesi]
YAVAS = []
