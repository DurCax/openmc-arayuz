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
   Kayit adi malzemenin "ad"iyla aynidir. Bilinmeyen anahtar reddedilir.

 GUVENCELER
   * Atomik yazma: ayni dizinde gecici dosya -> fsync -> os.replace -> dizin
     fsync. Yazma yarida kesilirse eski dosya oldugu gibi kalir.
   * "<dosya>.onceki" son SAGLAM surumdur: yalniz diskteki dosya gecerliyse
     guncellenir (bozuk dosya son saglam yedegi ezmez); sembolik baglantiysa
     yazma reddedilir.
   * degistir(): oku-degistir-yaz bir yan kilit dosyasiyla (fcntl.flock)
     yapilir; iki pencere ayni anda kaydederken kayit kaybolmaz.
   * Bozuk JSON, sema hatasi, asiri boyut/derinlik: KutuphaneBozuk (yol +
     neden). Dosya ASLA sessizce silinmez; bozuk_dosyayi_yedekle() kopyalar.
   * Daha yeni surumlu dosya okunmaz ve uzerine yazilmaz.
   * Degismezlik: ekle/guncelle/sil yeni demet dondurur; yukle() derin kopya
     dondurur (cagiran degistirse de onbellek/disk etkilenmez).
   * Dizin 0o700 ile olusturulur (kullaniciya ozel veri).
================================================================================
"""

import contextlib
import copy
import datetime
import json
import math
import os
import shutil
import tempfile
from typing import Callable, Iterable, Optional, Sequence, Tuple

from cekirdek import yollar
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

SURUM = 1
DOSYA_ADI = "malzemeler.json"
ONCEKI_EKI = ".onceki"
KILIT_EKI = ".lock"
_BOZUK_EKI = ".bozuk-"
_GECICI_ONEKI = ".malzemeler-"
_GECICI_SONEKI = ".tmp"
_DIZIN_KIPI = 0o700

# Sinirlar (kotu niyetli ya da bozuk dosyaya karsi; gercek kullanimin cok ustu):
# bir kayit ~1-5 kB JSON'dur; 20 MB ~ 4000+ kayit. Kayit sayisi 10 000, malzeme
# basina 1000 bilesim satiri (PNNL'deki en uzun malzeme < 40 satir), metin alani
# 2000 karakter, ad 200 karakter.
AZAMI_BOYUT = 20 * 1024 * 1024
AZAMI_KAYIT = 10000
AZAMI_SATIR = 1000
AZAMI_METIN = 2000
AZAMI_AD = 200

_TURLER = ("element", "nuklid")
_ORANLAR = ("ao", "wo")
_YOGUNLUK_BIRIMLERI = ("g/cm3", "g/cc", "kg/m3", "atom/b-cm", "atom/cm3", "sum", "macro")
_RENK_EN_COK = 255
_ZENGINLIK_EN_COK = 100.0
_KAYIT_ANAHTARLARI = frozenset(("ad", "aciklama", "kaynak", "olusturma", "guncelleme", "malzeme"))
_MALZEME_ANAHTARLARI = frozenset(("ad", "gorunen_ad", "yogunluk", "sicaklik", "bilesim", "sab",
                                  "renk", "kutup"))
_SATIR_ANAHTARLARI = frozenset(("tur", "isim", "miktar", "birim", "zenginlik"))
_YOGUNLUK_ANAHTARLARI = frozenset(("birim", "deger"))


class KutuphaneHatasi(Exception):
    """Kullanici kutuphanesi okunamadi ya da yazilamadi."""

    def __init__(self, yol, neden):
        super().__init__(_("Malzeme kütüphanesi: %s\n%s") % (yol, neden))
        self.yol = yol
        self.neden = neden


class KutuphaneBozuk(KutuphaneHatasi):
    """Dosya var ama gecerli bir kutuphane degil (bozuk JSON, sema, surum, boyut)."""


def varsayilan_yol(ortam=None) -> str:
    return os.path.join(yollar.kullanici_veri_dizini(ortam), DOSYA_ADI)


# ============================================================================
# Sema dogrulama
# ============================================================================

def _sayi_mi(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _ad_sorunu(ad, etiket):
    if not isinstance(ad, str) or not ad.strip():
        return _("%s boş") % etiket
    if len(ad) > AZAMI_AD:
        return _("%s en çok %d karakter olabilir") % (etiket, AZAMI_AD)
    if any(ord(c) < 32 or ord(c) == 127 for c in ad):
        return _("%s kontrol karakteri içeremez") % etiket
    return None


def _isim_sorunu(tur, isim):
    from cekirdek import malzeme_hesap as mh
    try:
        if tur == "nuklid":
            mh.atom_numarasi(mh.element_adi(isim))
        elif not (isim.isalpha() and len(isim) <= 2 and isim[:1].isupper()):
            raise ValueError(isim)
        else:
            mh.atom_numarasi(isim)
    except ValueError:
        return _("tanınmayan %s adı: %r") % (tur, isim)
    return None


def _satir_sorunu(i, s):
    if not isinstance(s, dict):
        return _("bileşim satırı %d sözlük değil") % (i + 1)
    if set(s) - _SATIR_ANAHTARLARI:
        return _("bileşim satırı %d: bilinmeyen alan %s") % (i + 1, sorted(set(s) - _SATIR_ANAHTARLARI))
    if s.get("tur") not in _TURLER:
        return _("bileşim satırı %d: tür element ya da nuklid olmalı") % (i + 1)
    if not isinstance(s.get("isim"), str) or not s["isim"] or len(s["isim"]) > AZAMI_AD:
        return _("bileşim satırı %d: isim eksik") % (i + 1)
    if not _sayi_mi(s.get("miktar")) or s["miktar"] < 0:
        return _("bileşim satırı %d: miktar negatif olmayan bir sayı olmalı") % (i + 1)
    if s.get("birim", "ao") not in _ORANLAR:
        return _("bileşim satırı %d: birim ao ya da wo olmalı") % (i + 1)
    z = s.get("zenginlik")
    if z is not None and (not _sayi_mi(z) or not 0.0 <= z <= _ZENGINLIK_EN_COK):
        return _("bileşim satırı %d: zenginlik 0–100 olmalı") % (i + 1)
    return _isim_sorunu(s["tur"], s["isim"])


def _yogunluk_sorunu(y):
    if not isinstance(y, dict) or y.get("birim") not in _YOGUNLUK_BIRIMLERI \
            or set(y) - _YOGUNLUK_ANAHTARLARI:
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
    if not isinstance(sab, list) or not all(isinstance(s, str) and len(s) <= AZAMI_AD for s in sab):
        return _("S(α,β) listesi metinlerden oluşmalı")
    renk = m.get("renk")
    if renk is not None and (not isinstance(renk, list) or len(renk) != 3 or not all(
            isinstance(c, int) and not isinstance(c, bool) and 0 <= c <= _RENK_EN_COK for c in renk)):
        return _("renk üç tamsayı (0–255) olmalı")
    gad = m.get("gorunen_ad")
    if gad is not None and (not isinstance(gad, str) or len(gad) > AZAMI_METIN):
        return _("'%s' alanı metin olmalı") % "gorunen_ad"
    if m.get("kutup") is not None and not isinstance(m["kutup"], dict):
        return _("'%s' alanı sözlük olmalı") % "kutup"
    return None


def malzeme_sorunu(m) -> Optional[str]:
    """Malzeme sozlugu kutuphaneye yazilabilir mi? Sorun metni ya da None."""
    if not isinstance(m, dict):
        return _("malzeme sözlük değil")
    if set(m) - _MALZEME_ANAHTARLARI:
        return _("malzemede bilinmeyen alan: %s") % ", ".join(sorted(set(m) - _MALZEME_ANAHTARLARI))
    sorun = _ad_sorunu(m.get("ad"), _("malzeme adı"))
    if sorun:
        return sorun
    bilesim = m.get("bilesim")
    if not isinstance(bilesim, list) or not bilesim:
        return _("bileşim boş")
    if len(bilesim) > AZAMI_SATIR:
        return _("bileşimde en çok %d satır olabilir") % AZAMI_SATIR
    for i, s in enumerate(bilesim):
        sorun = _satir_sorunu(i, s)
        if sorun:
            return sorun
    return _yogunluk_sorunu(m.get("yogunluk")) or _ek_alan_sorunu(m)


def _kayit_sorunu(k):
    if not isinstance(k, dict):
        return _("kayıt adı eksik")
    if set(k) - _KAYIT_ANAHTARLARI:
        return _("kayıtta bilinmeyen alan: %s") % ", ".join(sorted(set(k) - _KAYIT_ANAHTARLARI))
    sorun = _ad_sorunu(k.get("ad"), _("kayıt adı"))
    if sorun:
        return sorun
    for alan in ("aciklama", "kaynak", "olusturma", "guncelleme"):
        v = k.get(alan, "")
        if not isinstance(v, str) or len(v) > AZAMI_METIN:
            return _("'%s' alanı metin olmalı") % alan
    sorun = malzeme_sorunu(k.get("malzeme"))
    if sorun:
        return _("'%s': %s") % (k["ad"], sorun)
    if k["malzeme"]["ad"] != k["ad"]:
        return _("'%s': kayıt adı malzeme adıyla aynı olmalı") % k["ad"]
    return None


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
    if len(kayitlar) > AZAMI_KAYIT:
        return _("kütüphanede en çok %d kayıt olabilir") % AZAMI_KAYIT
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

def _ham_oku(yol):
    """JSON belgesi; boyut siniri ve derinlik/bellek hatalari KutuphaneBozuk."""
    boyut = os.stat(yol).st_size                  # yoksa FileNotFoundError
    if boyut > AZAMI_BOYUT:
        raise KutuphaneBozuk(yol, _("dosya çok büyük (%d bayt; sınır %d)") % (boyut, AZAMI_BOYUT))
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, RecursionError, MemoryError) as e:   # JSONDecodeError, Unicode, derinlik
        raise KutuphaneBozuk(yol, _("JSON okunamadı: %s") % e) from e


def yukle(yol: Optional[str] = None) -> Tuple[dict, ...]:
    """Kayitlar (yeni demet, derin kopya). Dosya yoksa (). Bozuksa KutuphaneBozuk."""
    yol = yol or varsayilan_yol()
    try:
        belge = _ham_oku(yol)
    except FileNotFoundError:
        return ()
    except OSError as e:
        raise KutuphaneHatasi(yol, _("dosya açılamadı: %s") % e) from e
    sorun = _belge_sorunu(belge)
    if sorun:
        raise KutuphaneBozuk(yol, sorun)
    return tuple(copy.deepcopy(belge["malzemeler"]))


def _diskteki_durum(yol):
    """'yok' | 'gecerli' | 'bozuk' | 'yeni' (bu programdan yeni surum)."""
    try:
        belge = _ham_oku(yol)
    except FileNotFoundError:
        return "yok"
    except (OSError, KutuphaneHatasi):
        return "bozuk"
    if isinstance(belge, dict) and isinstance(belge.get("surum"), int) and belge["surum"] > SURUM:
        return "yeni"
    return "bozuk" if _belge_sorunu(belge) else "gecerli"


def _dizin_fsync(dizin):
    fd = os.open(dizin, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _gecici_yaz(dizin, yaz):
    """Ayni dizinde gecici dosya; yaz(f) icerigi yazar. DONER gecici yol."""
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=_GECICI_ONEKI, suffix=_GECICI_SONEKI)
    try:
        with os.fdopen(fd, "wb") as f:
            yaz(f)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        os.unlink(gecici)
        raise
    return gecici


def _yer_degistir(gecici, hedef):
    try:
        os.replace(gecici, hedef)
    except BaseException:
        if os.path.exists(gecici):
            os.unlink(gecici)            # yalnizca KENDI gecici dosyamiz
        raise


def _onceki_guncelle(yol, dizin):
    """Diskteki GECERLI dosyayi .onceki'ye atomik kopyalar (bozuksa dokunmaz)."""
    onceki = yol + ONCEKI_EKI
    if os.path.islink(onceki):
        raise OSError(_("%s sembolik bağlantı; yedek yazılmadı") % onceki)
    with open(yol, "rb") as kaynak:
        gecici = _gecici_yaz(dizin, lambda f: shutil.copyfileobj(kaynak, f))
    _yer_degistir(gecici, onceki)


def _atomik_yaz(yol, metin, durum):
    dizin = os.path.dirname(yol) or "."
    os.makedirs(dizin, mode=_DIZIN_KIPI, exist_ok=True)
    if durum == "gecerli":
        _onceki_guncelle(yol, dizin)
    gecici = _gecici_yaz(dizin, lambda f: f.write(metin.encode("utf-8")))
    _yer_degistir(gecici, yol)
    _dizin_fsync(dizin)


def kaydet(kayitlar: Iterable[dict], yol: Optional[str] = None) -> str:
    """Kayitlari atomik olarak yazar. Gecersiz kayitta ValueError (dosyaya dokunmaz)."""
    yol = yol or varsayilan_yol()
    belge = {"surum": SURUM, "malzemeler": [copy.deepcopy(k) for k in kayitlar]}
    sorun = _belge_sorunu(belge)
    if sorun:
        raise ValueError(sorun)
    durum = _diskteki_durum(yol)
    if durum == "yeni":
        raise KutuphaneHatasi(yol, _("dosya daha yeni bir sürümle yazılmış; üzerine yazılmadı"))
    metin = json.dumps(belge, ensure_ascii=False, indent=1) + "\n"
    try:
        _atomik_yaz(yol, metin, durum)
    except OSError as e:
        _log.warning("kullanici kutuphanesi yazilamadi: %s (%s)", yol, e)
        raise KutuphaneHatasi(yol, _("yazılamadı: %s") % e) from e
    return yol


@contextlib.contextmanager
def kilit(yol: Optional[str] = None):
    """Yan kilit dosyasi (<dosya>.lock) uzerinde ozel fcntl.flock."""
    import fcntl
    yol = yol or varsayilan_yol()
    dizin = os.path.dirname(yol) or "."
    try:
        os.makedirs(dizin, mode=_DIZIN_KIPI, exist_ok=True)
        fd = os.open(yol + KILIT_EKI, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    except OSError as e:
        raise KutuphaneHatasi(yol, _("kilit dosyası açılamadı: %s") % e) from e
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def degistir(islem: Callable[[Tuple[dict, ...]], Sequence[dict]],
             yol: Optional[str] = None) -> Tuple[dict, ...]:
    """Kilit altinda oku -> islem(kayitlar) -> yaz. Yeni kayitlari dondurur."""
    yol = yol or varsayilan_yol()
    with kilit(yol):
        yeni = tuple(islem(yukle(yol)))
        kaydet(yeni, yol)
    return yeni


def bozuk_dosyayi_yedekle(yol: Optional[str] = None) -> str:
    """Bozuk dosyanin zaman damgali KOPYASINI alir (asli yerinde kalir); yedek yolu."""
    yol = yol or varsayilan_yol()
    damga = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    yedek = yol + _BOZUK_EKI + damga
    try:
        shutil.copy2(yol, yedek, follow_symlinks=False)
    except OSError as e:
        raise KutuphaneHatasi(yol, _("yedeklenemedi: %s") % e) from e
    _log.warning("bozuk kullanici kutuphanesi yedeklendi: %s -> %s", yol, yedek)
    return yedek


# ============================================================================
# Degismez kayit islemleri
# ============================================================================

def _simdi():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def kayit_olustur(malzeme: dict, aciklama: str = "", kaynak: str = "") -> dict:
    """Yeni kayit (malzemenin derin kopyasi; ad malzemeden)."""
    zaman = _simdi()
    m = copy.deepcopy(malzeme)
    return {"ad": m.get("ad", ""), "aciklama": aciklama, "kaynak": kaynak,
            "olusturma": zaman, "guncelleme": zaman, "malzeme": m}


def _ad_gerekli(kayit):
    if not isinstance(kayit, dict) or not isinstance(kayit.get("ad"), str) or not kayit["ad"]:
        raise ValueError(_("kayıt adı eksik"))
    return kayit["ad"]


def _bul(kayitlar, ad):
    for i, k in enumerate(kayitlar):
        if k["ad"] == ad:
            return i
    raise KeyError(_("kütüphanede yok: %s") % ad)


def benzersiz_kayit_adi(kayitlar: Iterable[dict], taban: str) -> str:
    """Kutuphanede olmayan ad: taban, taban_2, taban_3 ..."""
    adlar = {k["ad"] for k in kayitlar}
    ad, i = taban, 2
    while ad in adlar:
        ad = "%s_%d" % (taban, i)
        i += 1
    return ad


def ekle(kayitlar: Sequence[dict], kayit: dict) -> Tuple[dict, ...]:
    ad = _ad_gerekli(kayit)
    if any(k["ad"] == ad for k in kayitlar):
        raise ValueError(_("'%s' adında bir kayıt zaten var") % ad)
    return tuple(kayitlar) + (copy.deepcopy(kayit),)


def guncelle(kayitlar: Sequence[dict], ad: str, yeni: dict) -> Tuple[dict, ...]:
    yeni_ad = _ad_gerekli(yeni)
    i = _bul(kayitlar, ad)
    if yeni_ad != ad and any(k["ad"] == yeni_ad for k in kayitlar):
        raise ValueError(_("'%s' adında bir kayıt zaten var") % yeni_ad)
    kayit = dict(copy.deepcopy(yeni), olusturma=kayitlar[i].get("olusturma") or _simdi(),
                 guncelleme=_simdi())
    return tuple(kayitlar[:i]) + (kayit,) + tuple(kayitlar[i + 1:])


def sil(kayitlar: Sequence[dict], ad: str) -> Tuple[dict, ...]:
    i = _bul(kayitlar, ad)
    return tuple(kayitlar[:i]) + tuple(kayitlar[i + 1:])


def projeye_aktar(kayit: dict, spec: dict) -> dict:
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
