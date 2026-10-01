# -*- coding: utf-8 -*-
"""
 cekirdek/geometri/yol_metni.py  --  gelismis geometri yolu -> okunur metin

 Gezinti/basvuru yollari ("kok/ic/(1,2)>yansitici_blok",
 "[y]>yakit_cubugu/bolgeler/0") kod icindir; kullaniciya gosterilen her yer
 (dogrulama bulgusu yer etiketi, tukenme hacim ayrintisi, malzeme referans
 yollari) bu islevden gecer. Ad (malzeme, cubuk, parca) cevrilmez; yapisal
 parcalar etkin dilde yazilir. Bilinmeyen parca oldugu gibi kalir.
"""

import re

from cekirdek.ceviri import _, N_

_PARCA = {
    "kok": N_("kök"), "ic": N_("iç"), "dis": N_("dış"), "icerik": N_("içerik"),
    "anahtar": N_("harita"), "sinir": N_("sınır"), "eksenel": N_("eksenel yığın"),
    # tambur bileseninin ic bolgeleri (kurulum/bilesen.py)
    "emici": N_("emici"), "govde": N_("gövde"),
}
_SAYILI = {
    "halkalar": N_("{n}. halka"), "yerlesimler": N_("{n}. yerleşim"),
    "parcalar": N_("{n}. parça"), "katmanlar": N_("{n}. katman"),
    "hucreler": N_("{n}. hücre"), "gruplar": N_("{n}. grup"),
    "bolgeler": N_("{n}. bölge"),
}
# 'yerlesimler/<ad>#<sira>' (gezinti yolu) ya da 'yerlesimler/<ad>' bicimi
_ADLI = {"yerlesimler": (N_("‘{ad}’ yerleşimi"), N_("‘{ad}’ yerleşimi, {n}. öğe"))}
_ADLI_SIRA = re.compile(r"^(.+?)#(\d+)(?:>(.+))?$")
_ATLA = ("dugum", "geometri", "")
_KONUM = re.compile(r"^\(\s*(-?\d+(?:\s*,\s*-?\d+)*)\s*\)$")
_HARF = re.compile(r"^\[(.+)\]$")


def _secici(parca):
    """'(1,2)' -> '(1, 2) konumu'; '[y]' -> "'y' harfi"; degilse None."""
    e = _KONUM.match(parca)
    if e:
        sayilar = ", ".join(s.strip() for s in e.group(1).split(","))
        return _("({i}) konumu").format(i=sayilar)
    e = _HARF.match(parca)
    if e:
        return _("‘{h}’ harfi").format(h=e.group(1))
    return None


def _parca_metni(parca):
    """Tek bir yol parcasi ('>' ile secici + ad olabilir) -> metin listesi."""
    cikti = []
    for alt in parca.split(">"):
        s = _secici(alt)
        if s is not None:
            cikti.append(s)
        elif alt in _PARCA:
            cikti.append(_(_PARCA[alt]))
        elif alt not in _ATLA:
            cikti.append(alt)
    return cikti


def okunur(yol):
    """'kok/halkalar/0/icerik' -> 'kök › 1. halka › içerik' (etkin dilde)."""
    adimlar = (yol or "").split("/")
    metin, i = [], 0
    while i < len(adimlar):
        a = adimlar[i]
        if a in _SAYILI and i + 1 < len(adimlar) and adimlar[i + 1].isdigit():
            metin.append(_(_SAYILI[a]).format(n=int(adimlar[i + 1]) + 1))
            i += 2
            continue
        if a in _ADLI and i + 1 < len(adimlar) and adimlar[i + 1]:
            tekil, sirali = _ADLI[a]
            e = _ADLI_SIRA.match(adimlar[i + 1])
            if e:
                metin.append(_(sirali).format(ad=e.group(1), n=int(e.group(2)) + 1))
                if e.group(3):
                    metin.extend(_parca_metni(e.group(3)))
            else:
                metin.append(_(tekil).format(ad=adimlar[i + 1]))
            i += 2
            continue
        metin.extend(_parca_metni(a))
        i += 1
    return " › ".join(metin)
