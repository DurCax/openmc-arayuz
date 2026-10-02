# -*- coding: utf-8 -*-
"""
================================================================================
 demet_kinf.py  --  Demet turu basina k-sonsuz sihirbazi (v3 K4; Qt'siz)
================================================================================

 Her demet turu icin YANSITICI sinirli tek demet modeli (sonsuz kafes) kurar,
 koşu kuyruguna (cekirdek/kuyruk.py, Y10) ekler ve sonuclari "demet turu x
 k-sonsuz +- sigma" tablosuna cevirir. Arayuz: arayuz/analiz/demet_kinf.py.

   turler = demet_turleri(spec)                       # (DemetTuru, ...)
   ayar = KinfAyari(parcacik=5000, cevrim=120, pasif=30, tohum=1, is_parcacigi=6)
   isler = isleri_olustur(spec, ["UO2_24", "UO2_31"], ayar, kok_dizin)
   kimlikler = kuyruga_ekle(k, isler); k.baslat(); k.bekle()
   satirlar = tablo(k.durumlar()); open("kinf.csv", "w").write(csv_metni(satirlar))

 TEK DEMET ALT MODELI
   tek_demet_spec(spec, ad, uc_boyutlu=False) K5'in cekirdek/alt_model.py
   demet_alt_modeli'si ile AYNI imza ve sozlesmededir; o modul varsa onu
   kullanir (tek gercek kaynak), yoksa _yedek_tek_demet_spec'e duser
   (K5 birlesince yedek kaldirilabilir). Sozlesme: kor = tek_demet, butun
   sinirlar yansitici, 2B, tally/guc dagilimi/tukenme/kinetik kapali, kaynak
   koseleri alt modelden turetilir. Testler iki uygulamayi da denetler.

 FIZIK
   Sonuc k-sonsuz'dur: sizintisiz, sonsuz ozdes demet kafesi (yansitici
   sinir). Kordaki komsu demetlerin etkisi (spektral etkilesim), su araligi
   ve yansitici YOKTUR. Yanmaya gore k-sonsuz (tukenme adimlari) kapsam
   disidir (v3 Y4 sonrasi).
================================================================================
"""

from __future__ import annotations

import copy
import csv
import io
import os
from dataclasses import dataclass
from typing import Any, Iterable, List, Mapping, Optional, Sequence, Tuple

from cekirdek import kuyruk, sema
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

ETIKET = "k4_demet"                   # KosuIsi.etiket anahtari (demet adi)
_YANSITICI = {"yan": "reflective", "alt": "reflective", "ust": "reflective"}
# Varsayilan istatistik: tek demet k-sonsuzu icin ~20 pcm duzeyi (pwr 17x17,
# 5000 x 90 aktif cevrim olculdu; kullanici degistirir).
VARSAYILAN_PARCACIK = 5000
VARSAYILAN_CEVRIM = 120
VARSAYILAN_PASIF = 30


class DemetKinfHatasi(ValueError):
    """Sihirbaz girdisi gecersiz ya da alt model kurulamaz; mesaj gosterilir."""


@dataclass(frozen=True)
class DemetTuru:
    ad: str
    tur: str                          # kare | altigen
    boyut: Tuple[int, ...]
    kullanim: int                     # geometride kac kez yer aliyor


@dataclass(frozen=True)
class KinfAyari:
    parcacik: int = VARSAYILAN_PARCACIK
    cevrim: int = VARSAYILAN_CEVRIM
    pasif: int = VARSAYILAN_PASIF
    tohum: int = 1
    is_parcacigi: int = 1

    def denetle(self) -> "KinfAyari":
        if self.parcacik < 1 or self.tohum < 1 or self.is_parcacigi < 1:
            raise DemetKinfHatasi(_("parçacık, tohum ve iş parçacığı sayısı pozitif olmalı"))
        if self.pasif < 0 or self.cevrim <= self.pasif:
            raise DemetKinfHatasi(_("çevrim sayısı pasif çevrim sayısından büyük olmalı"))
        return self


@dataclass(frozen=True)
class KinfSatiri:
    demet: str
    k: Optional[float]
    sigma: Optional[float]
    asama: str
    hata: Optional[str]


# ============================================================================
# 1. DEMET TURLERI
# ============================================================================

def _say(dugum: Any, sayac: dict) -> None:
    """Agacta demet kullanimlarini sayar (kafes haritasi harf basina)."""
    if isinstance(dugum, list):
        for d in dugum:
            _say(d, sayac)
        return
    if not isinstance(dugum, dict):
        return
    if dugum.get("tur") == "bilesen" and dugum.get("ad") in sayac:
        sayac[dugum["ad"]] += 1
    if dugum.get("tur") == "kafes":
        anahtar = dugum.get("anahtar") or {}
        for satir in dugum.get("harita") or []:
            for harf in str(satir):
                hedef = anahtar.get(harf)
                if isinstance(hedef, dict) and hedef.get("ad") in sayac:
                    sayac[hedef["ad"]] += 1
    for anahtar_adi, deger in dugum.items():
        if anahtar_adi not in ("anahtar", "harita"):
            _say(deger, sayac)


def demet_turleri(spec: Mapping[str, Any]) -> Tuple[DemetTuru, ...]:
    """Spec'teki butun demetler (kutuphane sirasiyla) ve geometrideki sayilari."""
    from cekirdek import geometri
    sayac = {d.get("ad"): 0 for d in spec.get("demetler") or []}
    try:
        _say(geometri.model(spec).kok, sayac)
    except (ValueError, KeyError, TypeError):
        _log.warning("demet kullanımları sayılamadı; 0 gösterilecek", exc_info=True)
    return tuple(DemetTuru(d.get("ad"), d.get("tur") or "kare", tuple(d.get("boyut") or ()),
                           sayac.get(d.get("ad"), 0))
                 for d in spec.get("demetler") or [])


# ============================================================================
# 2. TEK DEMET ALT MODELI
# ============================================================================

def _yedek_tek_demet_spec(spec: Mapping[str, Any], ad: str, uc_boyutlu: bool = False) -> dict:
    """K5 alt_model.demet_alt_modeli ile ayni sozlesme (K5 birlesmeden once)."""
    if sema.demet_bul(spec, ad) is None:
        raise DemetKinfHatasi(_("tanımsız demet: %s") % ad)
    alt = copy.deepcopy(dict(spec))
    alt["ad"] = "%s — %s" % (spec.get("ad") or "", ad)
    kor = copy.deepcopy(sema.VARSAYILAN_KOR)
    kor.update({"tur": "tek_demet", "demet": ad, "sinir": dict(_YANSITICI),
                "yukseklik": sema.model_yuksekligi(spec) if uc_boyutlu else None})
    alt.update(kor=kor, geometri=None, tamburlar=[], tallyler=[],
               guc_dagilimi=copy.deepcopy(sema.VARSAYILAN_GUC))
    alt["tukenme"] = dict(copy.deepcopy(alt.get("tukenme") or sema.VARSAYILAN_TUKENME),
                          var=False, ek_malzemeler=[])
    ayar = alt.setdefault("ayarlar", copy.deepcopy(sema.VARSAYILAN_AYARLAR))
    ayar["kinetik"] = dict(ayar.get("kinetik") or {}, var=False)
    kaynak = ayar.setdefault("kaynak", {})
    kaynak.pop("alt", None)
    kaynak.pop("ust", None)
    kaynak["konum"] = [0.0, 0.0, 0.0]
    return alt


def tek_demet_spec(spec: Mapping[str, Any], ad: str, uc_boyutlu: bool = False) -> dict:
    """Yansitici sinirli tek demet alt modeli (YENI spec; girdi degismez)."""
    try:
        from cekirdek.alt_model import demet_alt_modeli
    except ImportError:
        demet_alt_modeli = _yedek_tek_demet_spec
    try:
        return demet_alt_modeli(spec, ad, uc_boyutlu=uc_boyutlu)
    except DemetKinfHatasi:
        raise
    except ValueError as e:                  # K5 AltModelHatasi(ValueError)
        raise DemetKinfHatasi(str(e)) from e


def sihirbaz_spec(spec: Mapping[str, Any], ad: str, ayar: KinfAyari) -> dict:
    """Alt model + sihirbaz istatistik ayarlari; kaynak fisil bolgede kutu."""
    ayar.denetle()
    alt = tek_demet_spec(spec, ad)
    a = alt["ayarlar"]
    a.update({"mod": "eigenvalue", "parcacik": int(ayar.parcacik), "cevrim": int(ayar.cevrim),
              "pasif": int(ayar.pasif), "tohum": int(ayar.tohum)})
    kaynak = {k: v for k, v in (a.get("kaynak") or {}).items() if k not in ("alt", "ust")}
    kaynak["tur"] = "kutu"            # kutu: ic olcuden turetilir, fisil kisitli
    a["kaynak"] = kaynak
    alt["calistirma"] = dict(alt.get("calistirma") or {}, is_parcacigi=int(ayar.is_parcacigi))
    return alt


# ============================================================================
# 3. KUYRUK
# ============================================================================

def isleri_olustur(spec: Mapping[str, Any], adlar: Sequence[str], ayar: KinfAyari,
                   kok_dizin: str) -> List[kuyruk.KosuIsi]:
    """Her demet icin ayri dizinde bir KosuIsi (etiket {ETIKET: ad})."""
    isler, alinan = [], []
    for ad in adlar:
        dizin = kuyruk.ayri_dizin(kok_dizin, "kinf_%s" % ad, alinmis=alinan)
        alinan.append(dizin)
        isler.append(kuyruk.KosuIsi(ad=_("k∞ — %s") % ad, dizin=dizin,
                                    spec=sihirbaz_spec(spec, ad, ayar),
                                    is_parcacigi=int(ayar.is_parcacigi), etiket={ETIKET: ad}))
    return isler


def kuyruga_ekle(k: kuyruk.Kuyruk, isler: Iterable[kuyruk.KosuIsi]) -> List[str]:
    """Isleri sirayla ekler; DONER kimlikler."""
    return [k.ekle(i) for i in isler]


def tablo(durumlar: Iterable[kuyruk.IsDurumu]) -> Tuple[KinfSatiri, ...]:
    """Sihirbaz islerinin satirlari (ilk gorulme sirasi; ayni kimlik bir kez).
    Etiketsiz (baska) isler atlanir."""
    gorulen, satirlar = set(), []
    for d in durumlar:
        ad = (d.etiket or {}).get(ETIKET)
        if ad is None or d.kimlik in gorulen:
            continue
        gorulen.add(d.kimlik)
        k, s = d.k if (d.k and d.asama == kuyruk.Asama.BITTI) else (None, None)
        satirlar.append(KinfSatiri(ad, k, s, d.asama.value, d.hata))
    return tuple(satirlar)


def csv_metni(satirlar: Iterable[KinfSatiri]) -> str:
    """demet, k_inf, sigma, durum, hata (bos hucre: sonuc yok)."""
    tampon = io.StringIO()
    yazici = csv.writer(tampon, lineterminator="\n")
    yazici.writerow(["demet", "k_inf", "sigma", "durum", "hata"])
    for s in satirlar:
        yazici.writerow([s.demet, "" if s.k is None else "%.6f" % s.k,
                         "" if s.sigma is None else "%.6f" % s.sigma, s.asama, s.hata or ""])
    return tampon.getvalue()


def varsayilan_kok(spec_yolu: Optional[str] = None) -> str:
    """Sihirbaz kosularinin kok dizini: model dosyasinin yaninda kinf/."""
    taban = sema.kosu_tabani(spec_yolu) if spec_yolu else os.getcwd()
    return os.path.join(taban, "kinf")
