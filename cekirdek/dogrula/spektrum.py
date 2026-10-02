# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/spektrum.py  --  Y3 spektrum / dort faktor ayari kontrolleri

   - kullanici tally'si "y3_" onekini kullanamaz (Y3 okuyucusu bu adlari kendi
     tally'si sanar; sonuc karti yanlis veriyle dolar)            -> hata
   - acikken bilinmeyen grup yapisi                                 -> hata
   - acikken tukenme: tukenme koşusunda Y3 kapatilir                -> bilgi
   - acikken sabit kaynak: dort faktor/k yok, yalniz spektrum       -> bilgi
"""

from cekirdek import spektrum
from cekirdek.ceviri import _
from cekirdek.dogrula._ortak import Bulgu

_YER = "spektrum"


def spektrum_kontrol(spec):
    bulgular = []
    for t in spec.get("tallyler") or []:
        if str(t.get("ad") or "").startswith(spektrum.TALLY_ONEKI):
            bulgular.append(Bulgu(
                "hata", "tally:%s" % t.get("ad"),
                _("'%s' öneki spektrum/dört faktör tally'lerine ayrılmıştır")
                % spektrum.TALLY_ONEKI,
                _("Tally'yi yeniden adlandırın.")))
    ham = (spec.get("ayarlar") or {}).get("spektrum")
    if not (isinstance(ham, dict) and ham.get("var")):
        return bulgular
    try:
        spektrum.ayar(spec)
    except ValueError as e:
        bulgular.append(Bulgu("hata", _YER, str(e)))
        return bulgular
    if (spec.get("tukenme") or {}).get("var"):
        bulgular.append(Bulgu(
            "bilgi", _YER,
            _("tükenme koşusunda spektrum ve dört faktör tally'leri kapatılır"),
            _("Çubuk çubuk yanma malzemeleri klonlar; spektrumu ayrı bir özdeğer "
              "koşusunda hesaplayın.")))
    if spec["ayarlar"].get("mod", "eigenvalue") != "eigenvalue":
        bulgular.append(Bulgu(
            "bilgi", _YER,
            _("sabit kaynak hesabında dört faktör ve k tanımsızdır; yalnız spektrum verilir")))
    return bulgular
