# -*- coding: utf-8 -*-
"""
================================================================================
 malzeme_kullanici.py  --  Kullanicinin kendi malzeme kutuphanesi (YALNIZ YEREL)
================================================================================

 Dosya: $XDG_DATA_HOME/openmc_arayuz/malzemeler.json
        (varsayilan ~/.local/share/openmc_arayuz/malzemeler.json;
        cekirdek/yollar.kullanici_veri_dizini). Ag erisimi YOKTUR (kullanici
        karari 5, 02.10.2026).

 BICIM (surum 1)
   {"surum": 1,
    "malzemeler": [{"ad": str, "aciklama": str, "kaynak": str,
                    "olusturma": ISO-8601, "guncelleme": ISO-8601,
                    "malzeme": <sema.malzeme sozlugu>}, ...]}

 GUVENCELER
   * Atomik yazma: ayni dizinde gecici dosya -> fsync -> os.replace. Yazma
     yarida kesilirse eski dosya oldugu gibi kalir; gecici dosya silinir.
   * Bir onceki surum "<dosya>.onceki" olarak saklanir (tek kusak).
   * Bozuk JSON ya da sema hatasi: KutuphaneBozuk (yol + neden). Dosya ASLA
     sessizce silinmez ya da ezilmez; bozuk_dosyayi_yedekle() kopyasini alir.
   * Daha yeni surumlu dosya okunmaz ve uzerine yazilmaz (veri kaybi olmasin).
   * Degismezlik: ekle/guncelle/sil yeni demet dondurur, girdiye dokunmaz.
================================================================================
"""

import copy
import datetime
import json
import math
import os
import shutil
import tempfile

from cekirdek import yollar
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

SURUM = 1
DOSYA_ADI = "malzemeler.json"
ONCEKI_EKI = ".onceki"
_BOZUK_EKI = ".bozuk-"
_GECICI_ONEKI = ".malzemeler-"
_GECICI_SONEKI = ".tmp"

_TURLER = ("element", "nuklid")
_ORANLAR = ("ao", "wo")
_YOGUNLUK_BIRIMLERI = ("g/cm3", "g/cc", "kg/m3", "atom/b-cm", "atom/cm3", "sum", "macro")
_RENK_EN_COK = 255
_ZENGINLIK_EN_COK = 100.0


class KutuphaneHatasi(Exception):
    """Kullanici kutuphanesi okunamadi ya da yazilamadi."""

    def __init__(self, yol, neden):
        super().__init__(_("Malzeme kütüphanesi: %s\n%s") % (yol, neden))
        self.yol = yol
        self.neden = neden


class KutuphaneBozuk(KutuphaneHatasi):
    """Dosya var ama gecerli bir kutuphane degil (bozuk JSON, sema, surum)."""


def varsayilan_yol(ortam=None):
    return os.path.join(yollar.kullanici_veri_dizini(ortam), DOSYA_ADI)


# ============================================================================
# Sema dogrulama
# ============================================================================

def _sayi_mi(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _satir_sorunu(i, s):
    if not isinstance(s, dict):
        return _("bileşim satırı %d sözlük değil") % (i + 1)
    if s.get("tur") not in _TURLER:
        return _("bileşim satırı %d: tür element ya da nuklid olmalı") % (i + 1)
    if not isinstance(s.get("isim"), str) or not s["isim"]:
        return _("bileşim satırı %d: isim eksik") % (i + 1)
    if not _sayi_mi(s.get("miktar")) or s["miktar"] < 0:
        return _("bileşim satırı %d: miktar negatif olmayan bir sayı olmalı") % (i + 1)
    if s.get("birim", "ao") not in _ORANLAR:
        return _("bileşim satırı %d: birim ao ya da wo olmalı") % (i + 1)
    z = s.get("zenginlik")
    if z is not None and (not _sayi_mi(z) or not 0.0 <= z <= _ZENGINLIK_EN_COK):
        return _("bileşim satırı %d: zenginlik 0–100 olmalı") % (i + 1)
    return None


def _yogunluk_sorunu(y):
    if not isinstance(y, dict) or y.get("birim") not in _YOGUNLUK_BIRIMLERI:
        return _("yoğunluk birimi geçersiz")
    if not _sayi_mi(y.get("deger")):
        return _("yoğunluk sayı olmalı")
    if y["birim"] != "sum" and y["deger"] <= 0:
        return _("yoğunluk pozitif olmalı")
    return None


def _ek_alan_sorunu(m):
    if m.get("sicaklik") is not None and (not _sayi_mi(m["sicaklik"]) or m["sicaklik"] <= 0):
        return _("sıcaklık pozitif bir sayı olmalı")
    sab = m.get("sab", [])
    if not isinstance(sab, list) or not all(isinstance(s, str) for s in sab):
        return _("S(α,β) listesi metinlerden oluşmalı")
    renk = m.get("renk")
    if renk is not None and (not isinstance(renk, list) or len(renk) != 3 or not all(
            isinstance(c, int) and 0 <= c <= _RENK_EN_COK for c in renk)):
        return _("renk üç tamsayı (0–255) olmalı")
    return None


def malzeme_sorunu(m):
    """Malzeme sozlugu kutuphaneye yazilabilir mi? Sorun metni ya da None."""
    if not isinstance(m, dict):
        return _("malzeme sözlük değil")
    if not isinstance(m.get("ad"), str) or not m["ad"].strip():
        return _("malzeme adı boş")
    bilesim = m.get("bilesim")
    if not isinstance(bilesim, list) or not bilesim:
        return _("bileşim boş")
    for i, s in enumerate(bilesim):
        sorun = _satir_sorunu(i, s)
        if sorun:
            return sorun
    return _yogunluk_sorunu(m.get("yogunluk")) or _ek_alan_sorunu(m)


def _kayit_sorunu(k):
    if not isinstance(k, dict) or not isinstance(k.get("ad"), str) or not k["ad"].strip():
        return _("kayıt adı eksik")
    for alan in ("aciklama", "kaynak", "olusturma", "guncelleme"):
        if not isinstance(k.get(alan, ""), str):
            return _("'%s' alanı metin olmalı") % alan
    sorun = malzeme_sorunu(k.get("malzeme"))
    return (_("'%s': %s") % (k["ad"], sorun)) if sorun else None


def _belge_sorunu(belge):
    """Kok belge sorunu (ilk bulunan) ya da None."""
    if not isinstance(belge, dict):
        return _("kök öğe sözlük değil")
    surum = belge.get("surum")
    if not isinstance(surum, int) or isinstance(surum, bool):
        return _("'surum' alanı eksik ya da tamsayı değil")
    if surum > SURUM:
        return _("dosya daha yeni bir sürümle yazılmış (sürüm %d, bu program %d); "
                 "değiştirilmedi") % (surum, SURUM)
    kayitlar = belge.get("malzemeler")
    if not isinstance(kayitlar, list):
        return _("'malzemeler' alanı liste değil")
    adlar = set()
    for k in kayitlar:
        sorun = _kayit_sorunu(k)
        if sorun:
            return sorun
        if k["ad"] in adlar:
            return _("'%s' adı iki kez kayıtlı") % k["ad"]
        adlar.add(k["ad"])
    return None


# ============================================================================
# Okuma / yazma
# ============================================================================

def yukle(yol=None):
    """Kayitlar (demet). Dosya yoksa (). Bozuksa KutuphaneBozuk."""
    yol = yol or varsayilan_yol()
    try:
        with open(yol, encoding="utf-8") as f:
            belge = json.load(f)
    except FileNotFoundError:
        return ()
    except ValueError as e:                  # JSONDecodeError, UnicodeDecodeError
        raise KutuphaneBozuk(yol, _("JSON okunamadı: %s") % e) from e
    except OSError as e:
        raise KutuphaneHatasi(yol, _("dosya açılamadı: %s") % e) from e
    sorun = _belge_sorunu(belge)
    if sorun:
        raise KutuphaneBozuk(yol, sorun)
    return tuple(copy.deepcopy(belge["malzemeler"]))


def _yeni_surum_mu(yol):
    """Diskteki dosya bu programdan yeni surumlu mu? (uzerine yazmayi engeller)"""
    try:
        with open(yol, encoding="utf-8") as f:
            surum = json.load(f).get("surum")
    except (OSError, ValueError, AttributeError):
        return False                 # yok/bozuk: yazilabilir (bozuksa cagiran yedekledi)
    return isinstance(surum, int) and surum > SURUM


def _atomik_yaz(yol, metin):
    dizin = os.path.dirname(yol) or "."
    os.makedirs(dizin, exist_ok=True)
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=_GECICI_ONEKI, suffix=_GECICI_SONEKI)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(metin)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(yol):
            shutil.copy2(yol, yol + ONCEKI_EKI)
        os.replace(gecici, yol)
    except BaseException:
        if os.path.exists(gecici):
            os.unlink(gecici)        # yalnizca KENDI gecici dosyamiz
        raise


def kaydet(kayitlar, yol=None):
    """Kayitlari atomik olarak yazar. Gecersiz kayitta ValueError (dosyaya dokunmaz)."""
    yol = yol or varsayilan_yol()
    belge = {"surum": SURUM, "malzemeler": [copy.deepcopy(k) for k in kayitlar]}
    sorun = _belge_sorunu(belge)
    if sorun:
        raise ValueError(sorun)
    if _yeni_surum_mu(yol):
        raise KutuphaneHatasi(yol, _("dosya daha yeni bir sürümle yazılmış; üzerine yazılmadı"))
    metin = json.dumps(belge, ensure_ascii=False, indent=1) + "\n"
    try:
        _atomik_yaz(yol, metin)
    except OSError as e:
        _log.warning("kullanici kutuphanesi yazilamadi: %s (%s)", yol, e)
        raise KutuphaneHatasi(yol, _("yazılamadı: %s") % e) from e
    return yol


def bozuk_dosyayi_yedekle(yol=None):
    """Bozuk dosyanin zaman damgali KOPYASINI alir (asli yerinde kalir); yedek yolu."""
    yol = yol or varsayilan_yol()
    damga = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    yedek = yol + _BOZUK_EKI + damga
    try:
        shutil.copy2(yol, yedek)
    except OSError as e:
        raise KutuphaneHatasi(yol, _("yedeklenemedi: %s") % e) from e
    _log.warning("bozuk kullanici kutuphanesi yedeklendi: %s -> %s", yol, yedek)
    return yedek


# ============================================================================
# Degismez kayit islemleri
# ============================================================================

def _simdi():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def kayit_olustur(malzeme, aciklama="", kaynak=""):
    """Yeni kayit (malzemenin derin kopyasi; ad malzemeden)."""
    zaman = _simdi()
    m = copy.deepcopy(malzeme)
    return {"ad": m.get("ad", ""), "aciklama": aciklama, "kaynak": kaynak,
            "olusturma": zaman, "guncelleme": zaman, "malzeme": m}


def _bul(kayitlar, ad):
    for i, k in enumerate(kayitlar):
        if k["ad"] == ad:
            return i
    raise KeyError(_("kütüphanede yok: %s") % ad)


def benzersiz_kayit_adi(kayitlar, taban):
    """Kutuphanede olmayan ad: taban, taban_2, taban_3 ..."""
    adlar = {k["ad"] for k in kayitlar}
    ad, i = taban, 2
    while ad in adlar:
        ad = "%s_%d" % (taban, i)
        i += 1
    return ad


def ekle(kayitlar, kayit):
    if any(k["ad"] == kayit["ad"] for k in kayitlar):
        raise ValueError(_("'%s' adında bir kayıt zaten var") % kayit["ad"])
    return tuple(kayitlar) + (copy.deepcopy(kayit),)


def guncelle(kayitlar, ad, yeni):
    i = _bul(kayitlar, ad)
    if yeni["ad"] != ad and any(k["ad"] == yeni["ad"] for k in kayitlar):
        raise ValueError(_("'%s' adında bir kayıt zaten var") % yeni["ad"])
    kayit = dict(copy.deepcopy(yeni), olusturma=kayitlar[i].get("olusturma") or _simdi(),
                 guncelleme=_simdi())
    return tuple(kayitlar[:i]) + (kayit,) + tuple(kayitlar[i + 1:])


def sil(kayitlar, ad):
    i = _bul(kayitlar, ad)
    return tuple(kayitlar[:i]) + tuple(kayitlar[i + 1:])


def projeye_aktar(kayit, spec):
    """Kaydin malzemesinin projeye eklenecek DERIN kopyasi (benzersiz ad)."""
    from cekirdek import sema
    m = copy.deepcopy(kayit["malzeme"])
    taban = m.get("ad") or kayit["ad"]
    ad, i = taban, 2
    while sema.malzeme_adi_sorunu(spec, ad) is not None:
        ad = "%s_%d" % (taban, i)
        i += 1
    if m.get("gorunen_ad") in (None, "", taban):
        m["gorunen_ad"] = ad
    m["ad"] = ad
    return m
