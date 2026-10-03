# -*- coding: utf-8 -*-
"""
================================================================================
 kod_uret  --  spec -> tek basina calisan Python betigi
================================================================================

 Arayuzde kurulan modeli, elle duzenlenebilir bir OpenMC betigine cevirir.
 Uretilen betik openmc_arayuz'a bagimli DEGILDIR; sadece openmc gerektirir.

 KULLANIM
   from cekirdek import kod_uret, sema
   spec = sema.yukle("ornekler/pwr_pinhucre.json")
   kod = kod_uret.uret(spec)
   open("model.py", "w", encoding="utf-8").write(kod)

 !!! ONEMLI !!!
   Uretilen betik kurucu.py ile AYNI modeli vermek zorundadir. Bunun tek
   gercek kaniti testler/test_regresyon.py icindeki "betik esdegerligi"
   testidir: ayni tohumla iki yol da birebir ayni k-eff vermelidir.
   kurucu.py degistirilirse bu modul de guncellenmeli ve test tekrar kosulmalidir.

 TEK YONLU
   Uretilen betik spec'e geri cevrilemez (keyfi Python cozumlenemez).
   Betik uzerinde calismaya devam edilecekse arayuz tarafi birakilmalidir.
================================================================================
"""


import datetime

from cekirdek.kod_uret import ad as _admod
from cekirdek.kod_uret.ad import _ad, _f, dokuman_metni  # noqa: F401  (arayuz _ad kullanir)
from cekirdek.kod_uret.bolumler import _malzemeler, _geometri, _ayarlar, _kapanis
from cekirdek.kod_uret.tally import _guc_dagilimi, _tallyler


def uret(spec, kaynak_dosya=None, renkli=True):
    """Spec'ten tek basina calisan Python betigi metni uretir."""
    from cekirdek import bolge_bol
    spec = bolge_bol.uygula(spec)        # v3 Y5: tukenme.bolme -> bolunmus model
    _admod._KAYIT = {"esle": {}, "kullanilan": set()}
    try:
        return _uret(spec, kaynak_dosya, renkli)
    finally:
        _admod._KAYIT = None


def _uret(spec, kaynak_dosya, renkli):
    tarih = datetime.date.today().isoformat()
    satirlar = [
        "# -*- coding: utf-8 -*-",
        '"""',
        "=" * 78,
        " %s" % dokuman_metni(spec.get("ad", "adsız model")),
        "=" * 78,
    ]
    if spec.get("aciklama"):
        for satir in spec["aciklama"].split("\n"):
            satirlar.append(" %s" % dokuman_metni(satir))
        satirlar.append("")
    satirlar += [
        " Bu betik openmc_arayuz tarafından üretilmiştir (%s)." % tarih,
    ]
    if kaynak_dosya:
        satirlar.append(" Kaynak model dosyası: %s" % dokuman_metni(kaynak_dosya))
    satirlar += [
        "",
        " Betik tek başına çalışır; openmc_arayuz'a bağımlı değildir.",
        " Elle düzenlenebilir, ancak arayüze geri yüklenemez.",
        "",
        " Kullanım",
        "   python3 %s" % dokuman_metni(kaynak_dosya or "model.py"),
        "=" * 78,
        '"""',
        "",
        "import openmc",
    ]

    _malzemeler(spec, satirlar)
    gx, gy, uretilen = _geometri(spec, satirlar)
    _ayarlar(spec, satirlar, gx, gy)
    guc_satirlari = []
    ek = _guc_dagilimi(spec, guc_satirlari, uretilen, gx, gy)
    _tallyler(spec, satirlar, ek_tallyler=ek, on_satirlar=guc_satirlari,
              sinir_kutu=(gx, gy))
    _kapanis(spec, satirlar, renkli)
    satirlar.append("")
    return "\n".join(satirlar)
