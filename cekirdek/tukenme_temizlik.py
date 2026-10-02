# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_temizlik.py  --  Tukenme dizininde onceki kosunun ciktilarini temizleme
================================================================================

 tukenme.calistir yeni kosudan ONCE cagirir (spec kaydi yazilmadan once):
   depletion_results.h5      her zaman silinir (eski davranis: yarim kalan kosu
                             eski sonucu "guncel" gostermesin)
   openmc_simulation_n<i>.h5 adim basina statepoint'ler (v3 K3). YALNIZ dizinde
                             bu arayuzun kosu kaydi (tukenme_spec.json) varsa
                             silinir: kullanici mutlak bir dizin vermis olabilir
                             (ev dizini, baska bir openmc.deplete ciktisi). Kayit
                             yoksa dosyalara dokunulmaz ve UYARI dondurulur.
 Yalniz duzenli dosyalar (sembolik bag DEGIL) ve adi desene TAM uyanlar silinir;
 alt dizinlere inilmez. Silinenler kaydedilir (INFO). Silme hatasi
 TemizlikHatasi'dir (OSError): mesaj dosyayi soyler; dizine yazma izni en
 basta denetlenir, boylece cogu hata hicbir sey silinmeden yakalanir.
================================================================================
"""

import os
import re

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

SPEC_KAYDI = "tukenme_spec.json"
SONUC_DOSYASI = "depletion_results.h5"
ADIM_DESENI = re.compile(r"openmc_simulation_n(\d+)\.h5")


class TemizlikHatasi(OSError):
    """Onceki tukenme ciktisi silinemedi (yeni kosu baslatilmaz)."""


def adim_dosyalari(dizin):
    """[(adim, yol)] sayisal sirayla: adi desene tam uyan duzenli dosyalar
    (sembolik bag ve dizin degil). Dizin yoksa bos liste."""
    try:
        ogeler = list(os.scandir(dizin))
    except (FileNotFoundError, NotADirectoryError):
        return []
    bulunan = []
    for oge in ogeler:
        m = ADIM_DESENI.fullmatch(oge.name)
        if m and oge.is_file(follow_symlinks=False):
            bulunan.append((int(m.group(1)), oge.path))
    return sorted(bulunan)


def _sil(yol):
    try:
        os.remove(yol)
    except OSError as e:
        raise TemizlikHatasi(_("Önceki tükenme çıktısı silinemedi: %s (%s)") % (yol, e)) from e
    _log.info("önceki tükenme çıktısı silindi: %s", yol)


def onceki_sonucu_temizle(dizin):
    """
    Yeni kosudan once dizini temizler. DONER {"silinen": [yol], "uyari": metin | None}.
    TemizlikHatasi: bir dosya silinemedi ya da dizine yazilamiyor.
    """
    if not os.path.isdir(dizin):
        return {"silinen": [], "uyari": None}
    if not os.access(dizin, os.W_OK | os.X_OK):
        raise TemizlikHatasi(_("Tükenme dizinine yazılamıyor: %s") % dizin)
    kayitli = os.path.isfile(os.path.join(dizin, SPEC_KAYDI))
    adimlar = [y for _i, y in adim_dosyalari(dizin)]
    uyari = None
    if adimlar and not kayitli:
        uyari = (_("%d adım dosyası (openmc_simulation_n*.h5) bu arayüzün koşu kaydı olmayan "
                   "dizinde bulundu; silinmedi: %s") % (len(adimlar), dizin))
        _log.warning("%s", uyari)
        adimlar = []
    silinen = []
    sonuc = os.path.join(dizin, SONUC_DOSYASI)
    for yol in adimlar + ([sonuc] if os.path.isfile(sonuc) else []):
        _sil(yol)
        silinen.append(yol)
    return {"silinen": silinen, "uyari": uyari}
