# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/mgxs.py  --  Y8 grup sabiti ayari kontrolleri

   - gecersiz bolge / grup yapisi / tur / duzeltme                -> hata
   - acikken tukenme: tukenme koşusunda MGXS tally'leri eklenmez  -> bilgi
   - acikken sabit kaynak: chi ve k anlamsiz olabilir            -> bilgi
   - tahmini tally bellegi BELLEK_SINIRI'ni asarsa                -> uyari
"""

from cekirdek import mgxs_uret
from cekirdek.ceviri import _
from cekirdek.dogrula._ortak import Bulgu

_YER = "mgxs"
# Uyari esigi: 2 GiB -- arayuzun hedefledigi masaustu (8-16 GB RAM) icin
# OpenMC'nin tally dizisi tek basina belligin onemli bir kismini alir.
BELLEK_SINIRI = 2 * 1024 ** 3


def _bolge_sayisi(spec: dict, bolge: str) -> int:
    if bolge == "demet":
        return 1
    if bolge == "malzeme":
        return max(1, len(spec.get("malzemeler") or []))
    # hucre: malzemeli hucre sayisi kurulmadan bilinmez; malzeme sayisinin
    # iki kati kaba bir alt tahmindir (her malzeme en az bir hucrede)
    return max(1, 2 * len(spec.get("malzemeler") or []))


def mgxs_kontrol(spec: dict) -> list:
    ham = (spec.get("ayarlar") or {}).get("mgxs")
    if not isinstance(ham, dict):
        return []
    try:
        a = mgxs_uret.ayar(spec)
    except ValueError as e:
        return [Bulgu("hata", _YER, str(e))]
    if not a.var:
        return []
    bulgular = []
    if (spec.get("tukenme") or {}).get("var"):
        bulgular.append(Bulgu(
            "bilgi", _YER, _("tükenme koşusunda grup sabiti (MGXS) tally'leri eklenmez"),
            _("Grup sabitlerini ayrı bir özdeğer koşusunda üretin.")))
    if (spec.get("ayarlar") or {}).get("mod", "eigenvalue") != "eigenvalue":
        bulgular.append(Bulgu(
            "bilgi", _YER, _("sabit kaynak hesabında χ ve k∞ kaynağın tayfına bağlıdır; "
                             "grup sabitleri o kaynağa özgüdür")))
    bayt = mgxs_uret.bellek_tahmini(a, _bolge_sayisi(spec, a.bolge))
    if bayt > BELLEK_SINIRI:
        bulgular.append(Bulgu(
            "uyari", _YER, _("MGXS tally'leri için tahmini bellek %.1f GiB") % (bayt / 1024 ** 3),
            _("Daha kaba grup yapısı ya da 'Malzeme' bölgesi seçin.")))
    return bulgular
