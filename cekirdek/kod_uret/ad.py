# -*- coding: utf-8 -*-
"""
 kod_uret/ad.py  --  betik degisken adlari (tur onekli, benzersiz), sayi yazimi

 Spec adlarindan uretilen degiskenler TURE GORE onek alir (m_ malzeme,
 c_ cubuk, p_ plaka, d_ demet, u_ malzeme sarmalayan evren ...) ve uret()
 boyunca bir kayitla BENZERSIZ tutulur. Eskiden ad aynen degisken oluyordu
 (olculdu, testler/test_butunlesme.py): 'a b' ve 'a_b' malzemeleri ayni
 degiskene dusup betik SESSIZCE farkli geometri kuruyordu; 'class', 'None',
 'openmc', 'malzemeler' adli malzemeler betigi calismaz yapiyordu. Betigin ic
 adlari (ayar, geometri, kok, _s1, _h1 ...) bu oneklerle baslamaz.
"""

import re


BANNER = "# " + "=" * 74
_TUREV_EKLERI = ("_yuzeyler", "_hucreler", "_disi", "_u", "_uc")
_KAYIT = None                          # uret() icinde: {"esle": {}, "kullanilan": set()}


def _cakisiyor(aday, kullanilan):
    if aday in kullanilan:
        return True
    for k in kullanilan:
        for ek in _TUREV_EKLERI:
            if aday == k + ek or k == aday + ek:
                return True
    return False


def _ad(metin, onek="m"):
    """Spec adini betikte (tur onekli, benzersiz) bir degisken adina cevirir."""
    temiz = re.sub(r"[^0-9a-zA-Z_]", "_", str(metin))
    taban = "%s_%s" % (onek, temiz)
    if _KAYIT is None:
        return taban
    anahtar = (onek, metin)
    if anahtar in _KAYIT["esle"]:
        return _KAYIT["esle"][anahtar]
    aday, i = taban, 2
    while _cakisiyor(aday, _KAYIT["kullanilan"]):
        aday = "%s_%d" % (taban, i)
        i += 1
    _KAYIT["esle"][anahtar] = aday
    _KAYIT["kullanilan"].add(aday)
    return aday


def _f(deger):
    """Float'i tam duyarlikla yazar (yuvarlama kaybi olmasin)."""
    if deger is None:
        return "None"
    if isinstance(deger, bool):
        return repr(deger)
    if isinstance(deger, float):
        return repr(deger)
    return repr(deger)


def _bolum(satirlar, no, baslik):
    satirlar.append("")
    satirlar.append(BANNER)
    satirlar.append("# %d. %s" % (no, baslik))
    satirlar.append(BANNER)


def _mat_ifade(ad):
    """Malzeme adini betikteki ifadeye cevirir; bosluk -> None (void)."""
    if ad is None or ad == "bosluk":
        return "None"
    return _ad(ad)


def dokuman_metni(metin):
    """Kullanici metnini uclu tirnakli docstring icine GUVENLE koyar (M3):
    ters bolu ve uclu tirnak kacar, satir sonu disindaki denetim karakterleri
    bosluk olur."""
    metin = str(metin).replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return "".join(c if (c == "\n" or c.isprintable()) else " " for c in metin)
