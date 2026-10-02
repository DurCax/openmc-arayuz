# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_kayit.py  --  Onceki tukenme kosusu: spec kaydi, eskime, kosu dizini
================================================================================

 cekirdek/tukenme.py'den bolundu (v3 Y4; davranis degismedi). Genel adlar
 tukenme modulunden yeniden disa aktarilir.
================================================================================
"""

import os

from cekirdek import sema
from cekirdek.ceviri import N_, _, pgettext


# ============================================================================
# Onceki kosu
#   Arayuz acildiginda son koşunun sonucu gosterilir. Tuzak: sonuc SU ANKI
#   spec'e ait olmayabilir (kullanici kosudan sonra gucu ya da zenginligi
#   degistirmis olabilir). Eski bir sonucu guncelmis gibi gostermek, hic
#   gostermemekten kotudur. Bu yuzden kosu basinda spec'in kopyasi yazilir;
#   acilista karsilastirilir ve sonuc O KOPYAYA gore okunur (malzeme
#   kimlikleri ve hacimler kosudaki modelden gelsin).
# ============================================================================

from cekirdek.tukenme_temizlik import SPEC_KAYDI  # noqa: E402 (tek tanim)

# Fizigi etkilemeyen bolumler: bunlar degisti diye sonuc eskimez.
_FIZIK_DISI = ("ad", "aciklama", "calistirma") + sema.META_ALANLARI


def kosu_dizini(spec, proje_yolu=None):
    """Tukenme sonuclarinin dizini: <proje dizini>/<calistirma.dizin>_tukenme."""
    taban = sema.kosu_tabani(proje_yolu)
    dizin = (spec.get("calistirma") or {}).get("dizin", "kosu") + "_tukenme"
    return dizin if os.path.isabs(dizin) else os.path.join(taban, dizin)


def _fizik_kismi(spec):
    """
    Sonucu etkileyen kisim. ad/aciklama/calistirma, tukenme.var ve
    tukenme.izlenen cikarilir: tukenmeyi kapatip acmak ya da izlenen nuklid
    secimini degistirmek sonucu eskitmez (izlenen yalnizca h5'ten hangi
    nuklidlerin OKUNACAGINI belirler; kosu butun zinciri izler).

    Karsilastirma METIN (json/hash) ile degil Python esitligiyle yapilir:
    JSON'da 3 ile 3.0 farkli metindir ama ayni sayidir; hash kullanmak
    degismemis bir modeli "eski" gosterirdi.
    """
    import copy
    sade = {k: copy.deepcopy(v) for k, v in sema.tamamla(spec).items()
            if k not in _FIZIK_DISI}
    sade.get("tukenme", {}).pop("var", None)
    sade.get("tukenme", {}).pop("izlenen", None)
    sade.get("tukenme", {}).pop("adim_gucu", None)   # yalniz olcum (K3): fizik degil
    sade.pop("surum", None)
    return sade


def spec_kaydet(spec, dizin):
    import json
    with open(os.path.join(dizin, SPEC_KAYDI), "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)


def onceki_sonuc(spec, dizin):
    """
    Dizindeki son tukenme sonucu. Sonuc yoksa None.
    DONER {"h5", "tarih": float, "durum": "guncel"|"eski"|"bilinmiyor",
           "farklar": [bolum], "sonuc": sonuc_oku(...)}
    """
    h5 = os.path.join(dizin, "depletion_results.h5")
    if not os.path.exists(h5):
        return None
    durum, farklar = eskime(spec, dizin)
    kayit = _kayit_oku(dizin)
    return {"h5": h5, "tarih": os.path.getmtime(h5), "durum": durum,
            "farklar": farklar, "sonuc": _sonuc_oku(h5, kayit or spec)}


def _sonuc_oku(h5, spec):
    from cekirdek import tukenme
    return tukenme.sonuc_oku(h5, spec)


def _kayit_oku(dizin):
    yol = os.path.join(dizin, SPEC_KAYDI)
    return sema.yukle(yol) if os.path.exists(yol) else None


# Spec bolumlerinin kullaniciya gorunen adlari (eskime farklari icin).
BOLUM_ADLARI = {
    "malzemeler": N_("malzemeler"), "cubuklar": N_("çubuklar"),
    "plakalar": N_("plaka elemanları"), "demetler": N_("demetler"), "kor": N_("kor"),
    "ayarlar": N_("hesap ayarları"), "tallyler": N_("tally'ler"),
    "guc_dagilimi": N_("güç dağılımı"), "tukenme": N_("tükenme ayarları"),
}
# Turkce adlar (geriye uyum); gosterirken spektrum_adi() etkin dilde verir.
SPEKTRUM_ADLARI = {"termal": "termal", "hizli": "hızlı"}


def spektrum_adi(kod):
    """Spektrum turunun gorunen adi, etkin dilde (SPEKTRUM_ADLARI)."""
    return {"termal": pgettext("spektrum", "termal"),
            "hizli": pgettext("spektrum", "hızlı")}.get(kod, kod)


def fark_metni(farklar):
    """Eskime farklarinin okunur listesi: "malzemeler, hesap ayarları"."""
    return ", ".join(_(BOLUM_ADLARI[f]) if f in BOLUM_ADLARI else f for f in farklar)


def eskime(spec, dizin):
    """
    (durum, farklar): sonuc bu spec'e mi ait? Sonucu OKUMAZ -- arayuz her
    duzenlemede cagirir, ucuz olmali.
      "guncel"     : fizigi etkileyen her sey ayni
      "eski"       : farklar = degisen spec bolumleri
      "bilinmiyor" : kosunun spec kaydi yok
    """
    kayit = _kayit_oku(dizin)
    if kayit is None:
        return "bilinmiyor", []
    a, b = _fizik_kismi(spec), _fizik_kismi(kayit)
    farklar = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    return ("eski" if farklar else "guncel"), farklar
