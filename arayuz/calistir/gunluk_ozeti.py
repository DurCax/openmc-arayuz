# -*- coding: utf-8 -*-
"""
gunluk_ozeti.py -- OpenMC gunlugunun (stdout) sonundaki ozet satirlarini okur.

Panodaki "Süre" ve "Hız" kartlari bu degerlerden dolar; ayni ayristirici hem
CANLI kosuda (arayuz ciktiyi zaten satir satir topluyor) hem de diskteki bir
kosu dizininde (kosu.log) calisir -- ikisi de ayni metindir.

    ozetle(metin) -> {"sure_s": float|None, "hiz": float|None,
                      "statepoint": str|None}

OpenMC 0.15-0.16 ciktisi (TIMING STATISTICS / RESULTS bolumleri):
     Total time elapsed                = 9.0529e+00 seconds
     Calculation Rate (active)         = 32043.8 particles/second
     Creating state point statepoint.40.h5...

Qt'ye ve openmc'ye bagli degildir: test ve rapor da kullanabilir.
"""

import re

_SURE = re.compile(r"^\s*Total time elapsed\s*=\s*([0-9.eE+-]+)\s*seconds", re.M)
_HIZ_AKTIF = re.compile(r"^\s*Calculation Rate \(active\)\s*=\s*([0-9.eE+-]+)", re.M)
_HIZ_PASIF = re.compile(r"^\s*Calculation Rate \(inactive\)\s*=\s*([0-9.eE+-]+)", re.M)
_STATEPOINT = re.compile(r"^\s*Creating state point (\S+?)\.\.\.", re.M)


def _son_sayi(desen, metin):
    """Desenin SON eslesmesindeki sayi (yeniden kosulmus gunlukte sonuncusu
    gecerlidir); eslesme yoksa ya da sayi bozuksa None."""
    eslesmeler = desen.findall(metin or "")
    if not eslesmeler:
        return None
    try:
        return float(eslesmeler[-1])
    except ValueError:  # bozuk sayi = deger yok (desen "1e" gibi yarim eslesebilir)
        return None


def ozetle(metin):
    """Gunluk metninden sure [s], hiz [parcacik/s] ve statepoint dosya adi."""
    sp = _STATEPOINT.findall(metin or "")
    return {
        "sure_s": _son_sayi(_SURE, metin),
        "hiz": _son_sayi(_HIZ_AKTIF, metin) or _son_sayi(_HIZ_PASIF, metin),
        "statepoint": sp[-1] if sp else None,
    }


def sure_metni(saniye):
    """Saniye -> "dk:sn" ("3:12"); bir saati asarsa "s:dd:ss". None -> "—"."""
    if saniye is None or saniye < 0:
        return "—"
    tam = int(round(saniye))
    saat, kalan = divmod(tam, 3600)
    dakika, sn = divmod(kalan, 60)
    if saat:
        return "%d:%02d:%02d" % (saat, dakika, sn)
    return "%d:%02d" % (dakika, sn)


def hiz_metni(parcacik_bolu_s):
    """Hiz -> binlik ayirici olarak ince bosluk ("52 400"). None -> "—"."""
    if parcacik_bolu_s is None or parcacik_bolu_s < 0:
        return "—"
    return "{:,.0f}".format(parcacik_bolu_s).replace(",", " ")
