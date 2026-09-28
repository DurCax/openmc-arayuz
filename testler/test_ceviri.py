# -*- coding: utf-8 -*-
"""
test_ceviri.py -- i18n iskeleti (cekirdek/ceviri.py).

Kaynak dil Turkce: msgid Turkce metnin kendisidir. "tr" etkinken metin aynen
doner; "en" etkinken locale/en/LC_MESSAGES/openmc_arayuz.mo'dan cevrilir.
Katalogda olmayan metin Turkce msgid'e duser ve DEBUG log yazilir.
"""

import logging
import os

from testler.ortak_test import kontrol, KOK


class _Toplayici(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.kayitlar = []

    def emit(self, kayit):
        self.kayitlar.append(kayit.getMessage())


def _dil_ile(ceviri, kod, fn):
    """Dili gecici degistirip fn()'i cagirir; onceki dile geri doner."""
    onceki = ceviri.etkin_dil()
    ceviri.dil_ayarla(kod)
    try:
        return fn()
    finally:
        ceviri.dil_ayarla(onceki)


def test_ceviri_temel():
    print("\n[C1] CEVIRI: tr'de msgid aynen, en'de katalogdan")
    from cekirdek import ceviri as c
    kontrol("desteklenen diller tr ve en", tuple(c.DESTEKLENEN_DILLER) == ("tr", "en"))
    kontrol("tr: msgid aynen doner",
            _dil_ile(c, "tr", lambda: c._("Logu aç")) == "Logu aç")
    kontrol("en: ornek giris cevrilir",
            _dil_ile(c, "en", lambda: c._("Logu aç")) == "Open log",
            "-> %r" % _dil_ile(c, "en", lambda: c._("Logu aç")))
    kontrol("en: dil adi cevrilir",
            _dil_ile(c, "en", lambda: c._("Türkçe")) == "Turkish")
    kontrol("etkin_dil ayarlanan dili verir",
            _dil_ile(c, "en", c.etkin_dil) == "en")
    kontrol("N_ metni degistirmez (yalnizca isaretler)", c.N_("Türkçe") == "Türkçe")


def test_ceviri_dil_secimi():
    print("\n[C2] CEVIRI: dil kodu normallestirme ve varsayilan dil")
    from cekirdek import ceviri as c
    kontrol("tr_TR.UTF-8 -> tr", c.dil_kodu("tr_TR.UTF-8") == "tr")
    kontrol("en_US -> en", c.dil_kodu("en_US") == "en")
    kontrol("bilinmeyen dil (de_DE) -> en", c.dil_kodu("de_DE") == "en")
    kontrol("bos/None -> en", c.dil_kodu(None) == "en" and c.dil_kodu("") == "en")
    kontrol("bilinmeyen dil ayarlaninca en etkin",
            _dil_ile(c, "fr", c.etkin_dil) == "en")
    kontrol("ayar degeri varsayilani belirler",
            c.varsayilan_dil(ayar="en", ortam={}) == "en"
            and c.varsayilan_dil(ayar="tr", ortam={}) == "tr")
    kontrol("OPENMC_ARAYUZ_DIL ortam degiskeni ayari gecer",
            c.varsayilan_dil(ayar="tr", ortam={"OPENMC_ARAYUZ_DIL": "en"}) == "en")
    kontrol("ayar yoksa sistem dili: LANG=tr_TR -> tr, LANG=de_DE -> en",
            c.varsayilan_dil(ortam={"LANG": "tr_TR.UTF-8"}) == "tr"
            and c.varsayilan_dil(ortam={"LANG": "de_DE.UTF-8"}) == "en")
    kontrol("LANGUAGE listesinin ilki onceliklidir",
            c.varsayilan_dil(ortam={"LANGUAGE": "tr:en", "LANG": "en_US"}) == "tr")


def test_ceviri_cogul_ve_baglam():
    print("\n[C3] CEVIRI: _n cogul ve pgettext baglam")
    from cekirdek import ceviri as c
    tekil, cogul = "Bu oturumda {n} hata kaydedildi.", "Bu oturumda {n} hata kaydedildi."
    kontrol("tr: _n tekil/cogul msgid",
            _dil_ile(c, "tr", lambda: c._n(tekil, cogul, 3)) == cogul)
    en1 = _dil_ile(c, "en", lambda: c._n(tekil, cogul, 1)).format(n=1)
    en3 = _dil_ile(c, "en", lambda: c._n(tekil, cogul, 3)).format(n=3)
    kontrol("en: _n(…, 1) tekil", en1 == "1 error was logged in this session.", "-> %r" % en1)
    kontrol("en: _n(…, 3) cogul", en3 == "3 errors were logged in this session.", "-> %r" % en3)
    kontrol("en: baglamli ceviri (pgettext)",
            _dil_ile(c, "en", lambda: c.pgettext("menü", "Dil")) == "Language")
    kontrol("tr: pgettext msgid aynen",
            _dil_ile(c, "tr", lambda: c.pgettext("menü", "Dil")) == "Dil")
    kontrol("dil menusu: baslik ve secenekler etkin dilde",
            _dil_ile(c, "en", lambda: (c.dil_menusu_basligi(), c.dil_secenekleri()))
            == ("Language", [("tr", "Turkish"), ("en", "English")]))


def test_ceviri_eksik_giris_loglanir():
    print("\n[C4] CEVIRI: eksik giris Turkce'ye duser ve DEBUG loglanir")
    from cekirdek import ceviri as c
    toplayici = _Toplayici()
    kaydedici = logging.getLogger(c.KAYDEDICI_ADI)
    eski_seviye = kaydedici.level
    kaydedici.addHandler(toplayici)
    kaydedici.setLevel(logging.DEBUG)
    try:
        metin = "Katalogda olmayan örnek metin 7f3a"
        sonuc = _dil_ile(c, "en", lambda: c._(metin))
    finally:
        kaydedici.removeHandler(toplayici)
        kaydedici.setLevel(eski_seviye)
    kontrol("eksik giris msgid'e duser", sonuc == metin)
    kontrol("eksik giris DEBUG log yazar",
            any(metin in k for k in toplayici.kayitlar), "-> %s" % toplayici.kayitlar)


def test_katalog_derlenmis():
    print("\n[C5] CEVIRI: .mo katalogu .po ile guncel")
    po = os.path.join(KOK, "locale", "en", "LC_MESSAGES", "openmc_arayuz.po")
    mo = po[:-3] + ".mo"
    kontrol("en .po ve .mo var", os.path.isfile(po) and os.path.isfile(mo))
    try:
        from babel.messages.pofile import read_po
    except ImportError:
        kontrol("babel yok; .po/.mo karsilastirmasi atlandi", True)
        return
    import gettext
    with open(po, "rb") as f:
        katalog = read_po(f)
    with open(mo, "rb") as f:
        derli = gettext.GNUTranslations(f)
    eksik = [m.id for m in katalog if m.id and m.string and not m.pluralizable
             and not m.context and derli.gettext(m.id) != m.string]
    kontrol(".po'daki her ceviri .mo'da ayni (araclar/ceviri.sh derle)", not eksik,
            "-> %s" % eksik[:5])


HIZLI = [test_ceviri_temel, test_ceviri_dil_secimi, test_ceviri_cogul_ve_baglam,
         test_ceviri_eksik_giris_loglanir, test_katalog_derlenmis]
YAVAS = []
