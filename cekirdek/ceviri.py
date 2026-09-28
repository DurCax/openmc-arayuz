# -*- coding: utf-8 -*-
"""
ceviri.py -- arayuz ve cekirdek metinlerinin cevirisi (stdlib gettext).

KAYNAK DIL TURKCE: msgid, Turkce metnin kendisidir.

    from cekirdek.ceviri import _, _n, pgettext, N_
    etiket = _("Logu aç")
    ozet = _n("{n} hata", "{n} hata", sayi).format(n=sayi)
    menu = pgettext("menü", "Dil")
    TURLER = {"tr": N_("Türkçe")}      # yalnizca isaretler; gosterirken _(...)

Dil secimi (varsayilan_dil): OPENMC_ARAYUZ_DIL ortam degiskeni > kayitli ayar
(arayuz QSettings'ten okuyup `ayar=` ile verir; cekirdek Qt'ye bagli degil) >
sistem dili (LANGUAGE/LC_ALL/LC_MESSAGES/LANG). Sistem dili Turkce ise "tr",
degilse "en".

Katalog: locale/<dil>/LC_MESSAGES/openmc_arayuz.mo (araclar/ceviri.sh derler).
Katalog yoksa ya da giris eksikse metin Turkce msgid'e DUSER; bu sessiz
degildir: katalog eksigi WARNING, eksik giris (her msgid bir kez) WARNING loglanir (varsayilan INFO seviyesinde gorunsun).
"""

import gettext
import logging
import os
import threading

ALAN = "openmc_arayuz"
KAYNAK_DIL = "tr"
DESTEKLENEN_DILLER = ("tr", "en")
YEDEK_DIL = "en"
ORTAM_DEGISKENI = "OPENMC_ARAYUZ_DIL"
KAYDEDICI_ADI = "openmc_arayuz.ceviri"
LOCALE_DIZINI = os.environ.get(
    "OPENMC_ARAYUZ_LOCALE",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locale"))

# gettext.pgettext'in baglam ayiricisi (GNU gettext: EOT karakteri)
_BAGLAM_AYIRICI = "\x04"

_log = logging.getLogger(KAYDEDICI_ADI)
_kilit = threading.Lock()
_durum = {"dil": KAYNAK_DIL, "katalog": gettext.NullTranslations()}
_bildirilen_eksikler = set()
_dinleyiciler = []


def N_(metin):
    """Ceviri icin ISARETLER ama cevirmez (modul duzeyi sabitler icin).
    Gosterirken _(sabit) cagrilir."""
    return metin


# Dil adlari: "Görünüm > Dil" menusu bunlari _() ile gosterir.
DIL_ADLARI = {"tr": N_("Türkçe"), "en": N_("İngilizce")}


def dil_menusu_basligi():
    """"Görünüm > Dil" menusunun basligi (etkin dilde)."""
    return pgettext("menü", "Dil")


def dil_secenekleri():
    """Dil menusu icin [(kod, gorunen_ad)], etkin dilde."""
    return [(kod, _(DIL_ADLARI[kod])) for kod in DESTEKLENEN_DILLER]


def dil_kodu(deger):
    """"tr_TR.UTF-8", "tr-TR", "TR" -> "tr"; desteklenmeyen/bos -> "en"."""
    kod = (deger or "").strip().split(".")[0].replace("-", "_").split("_")[0].lower()
    return kod if kod in DESTEKLENEN_DILLER else YEDEK_DIL


def sistem_dili(ortam=None):
    """POSIX yerel ayar degiskenlerinden dil ("tr" ya da "en")."""
    ortam = os.environ if ortam is None else ortam
    for ad in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        deger = ortam.get(ad, "")
        if deger:
            ilk = deger.split(":")[0]
            if ilk not in ("C", "POSIX"):
                return dil_kodu(ilk)
    return YEDEK_DIL


def varsayilan_dil(ayar=None, ortam=None):
    """Ortam degiskeni > kayitli ayar > sistem dili."""
    ortam = os.environ if ortam is None else ortam
    if ortam.get(ORTAM_DEGISKENI):
        return dil_kodu(ortam[ORTAM_DEGISKENI])
    if ayar:
        return dil_kodu(ayar)
    return sistem_dili(ortam)


def _katalog_yukle(kod):
    if kod == KAYNAK_DIL:
        return gettext.NullTranslations()
    try:
        return gettext.translation(ALAN, LOCALE_DIZINI, languages=[kod])
    except OSError as e:
        _log.warning("'%s' ceviri katalogu yuklenemedi (%s); metinler Turkce "
                     "kalacak: %s", kod, LOCALE_DIZINI, e)
        return gettext.NullTranslations()


def dil_ayarla(kod):
    """Etkin dili degistirir (desteklenmeyen -> "en"); etkin kodu doner.
    Kayitli dinleyiciler (ornek Qt QTranslator yenileyici) yeni kodla cagrilir."""
    kod = dil_kodu(kod)
    katalog = _katalog_yukle(kod)
    with _kilit:
        _durum.update(dil=kod, katalog=katalog)
        _bildirilen_eksikler.clear()
        dinleyiciler = list(_dinleyiciler)
    for fn in dinleyiciler:
        fn(kod)
    return kod


def etkin_dil():
    return _durum["dil"]


def dinleyici_ekle(fn):
    """Dil degisince fn(kod) cagrilir (arayuz metinlerini yenilemek icin)."""
    with _kilit:
        if fn not in _dinleyiciler:
            _dinleyiciler.append(fn)


def dinleyici_cikar(fn):
    with _kilit:
        if fn in _dinleyiciler:
            _dinleyiciler.remove(fn)


def _eksik(anahtar):
    if anahtar in _bildirilen_eksikler:
        return
    _bildirilen_eksikler.add(anahtar)
    _log.warning("ceviri eksik (%s): %r", _durum["dil"], anahtar)


def _(metin):
    """Metni etkin dile cevirir; kaynak dilde (tr) aynen doner."""
    if _durum["dil"] == KAYNAK_DIL or not metin:
        return metin
    sonuc = _durum["katalog"].gettext(metin)
    if sonuc == metin:
        _eksik(metin)
    return sonuc


def _n(tekil, cogul, n):
    """Cogul bicim (ngettext): n'e gore tekil ya da cogul ceviri."""
    if _durum["dil"] == KAYNAK_DIL:
        return tekil if n == 1 else cogul
    sonuc = _durum["katalog"].ngettext(tekil, cogul, n)
    if sonuc in (tekil, cogul):
        _eksik(tekil)
    return sonuc


def pgettext(baglam, metin):
    """Baglamli ceviri: ayni Turkce metin farkli yerlerde farkli cevrilecekse."""
    if _durum["dil"] == KAYNAK_DIL:
        return metin
    sonuc = _durum["katalog"].pgettext(baglam, metin)
    if sonuc == metin:
        _eksik(baglam + _BAGLAM_AYIRICI + metin)
    return sonuc
