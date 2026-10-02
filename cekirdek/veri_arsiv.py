# -*- coding: utf-8 -*-
"""
veri_arsiv.py -- indirilen nukleer veri arsivinin GUVENLI acilmasi, disk alani
ve hedef klasor denetimi (v3 K2; cekirdek/veri_indir.py kullanir).

GUVENLIK (arsiv internetten gelir; guvenilmez girdi sayilir)
  - Yalniz duzenli dosya ve dizin uyesi kabul edilir: symlink, hardlink,
    aygit, fifo REDDEDILIR (veri kutuphanelerinde bulunmaz).
  - Uye adi mutlak olamaz, ".." bileseni iceremez; cozulen yol gecici acma
    dizininin icinde kalmali (commonpath).
  - Python >= 3.12'de ayrica tarfile filter="data" (PEP 706) uygulanir.
  - Zip bombasi: acilan toplam bayt `en_cok_bayt`i, uye sayisi `en_cok_uye`yi
    asamaz; her dosyadan once diskte uye + DISK_PAYI kadar yer olmali.
  - Acma gecici bir ".aciliyor-*" dizinine yapilir; basarida cross_sections.xml
    iceren dizin os.replace ile hedef ada TASINIR (atomik), hatada gecici dizin
    silinir. Var olan hedef dizin ezilmez.
"""

import bz2
import glob
import gzip
import lzma
import os
import shutil
import stat
import tarfile
import tempfile
from typing import Callable, Optional

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

# Indirme ve acmada diskte BIRAKILAN bos alan: tasarim payi (isletim sistemi ve
# baska yazmalar dolu diske dusmesin); kaynakli bir esik degildir.
DISK_PAYI = 512 * 1024 ** 2
# Uye sayisi ust siniri. ENDF/B-VIII.0 kutuphanesi 690 dosya (bu makine,
# cross_sections.xml kayit sayisi); sinir bunun ~150 kati -- tasarim payi.
EN_COK_UYE = 100_000
XS_DOSYASI = "cross_sections.xml"
_XML_ARAMA_DERINLIGI = 2          # arsivde cross_sections.xml en fazla 2 alt dizinde
# Kullanicinin hedef olarak secemeyecegi sistem dizinleri (Filesystem Hierarchy
# Standard 3.0 ust duzey dizinleri; /tmp, /home, /opt, /mnt, /media, /srv serbest).
SISTEM_DIZINLERI = ("/bin", "/boot", "/dev", "/etc", "/lib", "/lib32", "/lib64", "/libx32",
                    "/proc", "/root", "/run", "/sbin", "/sys", "/usr", "/var")
# Ev dizininde hedef olamayan alt dizinler (anahtar/kimlik deposu).
GIZLI_EV_DIZINLERI = (".ssh", ".gnupg")
GECICI_ONEK = ".aciliyor-"
# Acilan (sikistirilmamis) akis uzerinde baslik payi: uye basina tar basligi
# 512 bayt + PAX/GNU uzun ad bloklari icin pay (tasarim secimi).
_BASLIK_PAYI_UYE = 4096
_DIZIN_MODU = 0o755              # kurulan kutuphane: digerleri okuyabilir
_SIKISTIRMA = ((b"\xfd7zXZ\x00", lzma.open), (b"\x1f\x8b", gzip.open), (b"BZh", bz2.open))
GB = 1024 ** 3

Ilerleme = Optional[Callable[[int, int], None]]


class VeriHatasi(Exception):
    """Veri indirme/kurma hatalarinin tabani (mesaj kullaniciya gosterilir)."""


class ArsivHatasi(VeriHatasi):
    """Arsiv, disk alani ya da hedef klasor sorunu."""


class IptalEdildi(VeriHatasi):
    """Kullanici iptal etti; yarim indirme surdurulebilir."""


class BozukArsiv(ArsivHatasi):
    """Arsiv okunamadi (yarim/bozuk): yeniden indirilmeli (cagiran arsivi siler)."""


def guvenli_dizin(yol: str, mod: int) -> str:
    """yol dizinini olusturur (mod ile) ya da var olani denetler: symlink
    olamaz, sahibi bu kullanici olmali; izin `mod`a ayarlanir. Doner: yol."""
    try:
        os.makedirs(yol, mode=mod, exist_ok=True)
        bilgi = os.lstat(yol)
    except OSError as e:
        raise ArsivHatasi(_("klasör oluşturulamadı: %s (%s)") % (yol, e)) from e
    if stat.S_ISLNK(bilgi.st_mode) or not stat.S_ISDIR(bilgi.st_mode):
        raise ArsivHatasi(_("güvenlik: %s bir bağlantı ya da klasör değil") % yol)
    if bilgi.st_uid != os.getuid():
        raise ArsivHatasi(_("güvenlik: %s başka bir kullanıcıya ait") % yol)
    os.chmod(yol, mod)
    return yol


# ---------------------------------------------------------------------------
# hedef klasor ve disk
# ---------------------------------------------------------------------------

def _sistem_dizini_mi(gercek: str) -> bool:
    if gercek == os.sep:
        return True
    return any(gercek == d or gercek.startswith(d + os.sep) for d in SISTEM_DIZINLERI)


def hedef_dogrula(dizin: str) -> str:
    """Kullanicinin sectigi hedef klasor: mutlak, sistem dizini degil, dosya
    degil, yoksa olusturulur, yazilabilir. Doner: gercek (realpath) yol."""
    if not dizin or not os.path.isabs(dizin):
        raise ArsivHatasi(_("hedef klasör mutlak bir yol olmalı: %r") % (dizin,))
    gercek = os.path.realpath(dizin)
    if _sistem_dizini_mi(gercek):
        raise ArsivHatasi(_("sistem dizinine veri indirilemez: %s") % gercek)
    _ev_kurali(gercek)
    if os.path.exists(gercek) and not os.path.isdir(gercek):
        raise ArsivHatasi(_("hedef bir klasör değil: %s") % gercek)
    try:
        os.makedirs(gercek, exist_ok=True)
    except OSError as e:
        raise ArsivHatasi(_("hedef klasör oluşturulamadı: %s (%s)") % (gercek, e)) from e
    if not os.access(gercek, os.W_OK | os.X_OK):
        raise ArsivHatasi(_("hedef klasöre yazma izni yok: %s") % gercek)
    if os.stat(gercek).st_mode & stat.S_IWOTH:
        raise ArsivHatasi(_("hedef klasöre başka kullanıcılar da yazabiliyor (güvensiz): %s; "
                            "alt bir klasör seçin") % gercek)
    return gercek


def _ev_kurali(gercek: str) -> None:
    """Ev dizininin kendisi ve gizli anahtar dizinleri (~/.ssh, ~/.gnupg) hedef olamaz."""
    ev = os.path.realpath(os.path.expanduser("~"))
    if gercek == ev:
        raise ArsivHatasi(_("ev dizininin kendisine veri indirilemez; bir alt klasör seçin "
                            "(ör. ~/nucdata)"))
    for ad in GIZLI_EV_DIZINLERI:
        gizli = os.path.join(ev, ad)
        if gercek == gizli or gercek.startswith(gizli + os.sep):
            raise ArsivHatasi(_("bu klasöre veri indirilemez: %s") % gercek)


def _var_olan_ust(yol: str) -> str:
    yol = os.path.abspath(yol)
    while not os.path.exists(yol):
        ust = os.path.dirname(yol)
        if ust == yol:
            break
        yol = ust
    return yol


def bos_alan(dizin: str, kullanim=shutil.disk_usage) -> int:
    """dizinin (yoksa var olan en yakin ustunun) bulundugu diskteki bos bayt."""
    return int(kullanim(_var_olan_ust(dizin)).free)


def disk_denetle(dizin: str, gereken: int, kullanim=shutil.disk_usage) -> int:
    """gereken + DISK_PAYI bayt bos yer yoksa ArsivHatasi. Doner: bos bayt."""
    bos = bos_alan(dizin, kullanim)
    if bos < gereken + DISK_PAYI:
        raise ArsivHatasi(_("diskte yeterli yer yok: %.1f GB gerekli (%.1f GB pay dahil), "
                            "%.1f GB boş (%s)") % ((gereken + DISK_PAYI) / GB, DISK_PAYI / GB,
                                                  bos / GB, _var_olan_ust(dizin)))
    return bos


# ---------------------------------------------------------------------------
# arsiv
# ---------------------------------------------------------------------------

def _guvenli_ad_mi(ad: str) -> bool:
    return (bool(ad) and os.sep not in ad and ad not in (".", "..")
            and (os.altsep is None or os.altsep not in ad))


def _uye_denetle(uye: tarfile.TarInfo, kok: str) -> None:
    if not (uye.isfile() or uye.isdir()):
        raise ArsivHatasi(_("arşivde izin verilmeyen üye türü (bağlantı/aygıt): %s")
                          % uye.name)
    ad = uye.name
    if not ad or os.path.isabs(ad) or ".." in ad.replace("\\", "/").split("/"):
        raise ArsivHatasi(_("arşivde güvensiz yol: %s") % ad)
    hedef = os.path.realpath(os.path.join(kok, ad))
    if os.path.commonpath([kok, hedef]) != kok:
        raise ArsivHatasi(_("arşivde güvensiz yol: %s") % ad)


class _SinirliAkis:
    """Acilmis akistan okunan toplam bayti sinirlar (dev PAX basligi / bomba)."""

    def __init__(self, akis, sinir: int):
        self._akis, self._sinir, self._okunan = akis, sinir, 0

    def read(self, n=-1):
        veri = self._akis.read(n)
        self._okunan += len(veri)
        if self._okunan > self._sinir:
            raise ArsivHatasi(_("açılan akış boyut sınırını aştı (%.1f GB)") % (self._sinir / GB))
        return veri

    def close(self):
        self._akis.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
        return False


def _acilmis_akis(arsiv: str):
    """Sikistirmayi bas baytlardan tanir; acilmis akis (xz/gz/bz2 ya da duz tar)."""
    with open(arsiv, "rb") as f:
        bas = f.read(6)
    for imza, acici in _SIKISTIRMA:
        if bas.startswith(imza):
            return acici(arsiv, "rb")
    return open(arsiv, "rb")


def _uye_ac(tf, uye, kok):
    if hasattr(tarfile, "data_filter"):
        tf.extract(uye, kok, filter="data")
    else:                       # Python < 3.11.4: oznitelik (mod/uid) arsivden alinmaz
        tf.extract(uye, kok, set_attrs=False)


def _ac(arsiv, kok, en_cok_bayt, en_cok_uye, iptal, ilerleme, tahmini, kullanim):
    toplam = sayi = 0
    akis = _SinirliAkis(_acilmis_akis(arsiv), en_cok_bayt + en_cok_uye * _BASLIK_PAYI_UYE)
    with akis, tarfile.open(fileobj=akis, mode="r|") as tf:
        for uye in tf:
            sayi += 1
            if sayi > en_cok_uye:
                raise ArsivHatasi(_("arşivde çok fazla üye (> %d)") % en_cok_uye)
            _uye_denetle(uye, kok)
            toplam += uye.size
            if toplam > en_cok_bayt:
                raise ArsivHatasi(_("açılan boyut sınırı aşıldı (%.1f GB): arşiv beklenenden "
                                    "büyük ya da bozuk") % (en_cok_bayt / GB))
            if uye.isfile():
                disk_denetle(kok, uye.size, kullanim)
            if iptal is not None and iptal.is_set():
                raise IptalEdildi(_("açma iptal edildi"))
            _uye_ac(tf, uye, kok)
            if ilerleme:
                ilerleme(toplam, max(tahmini, toplam))


def _xml_bul(kok: str) -> Optional[str]:
    """kok altinda en fazla _XML_ARAMA_DERINLIGI duzey derinde cross_sections.xml."""
    for dizin, altlar, dosyalar in os.walk(kok):
        derinlik = os.path.relpath(dizin, kok).count(os.sep) + (dizin != kok)
        if XS_DOSYASI in dosyalar:
            return os.path.join(dizin, XS_DOSYASI)
        if derinlik >= _XML_ARAMA_DERINLIGI:
            altlar[:] = []
        altlar.sort()
    return None


def _artiklari_sil(hedef_dizin: str) -> None:
    """Onceki yarim acmadan kalan, BU kullaniciya ait .aciliyor-* dizinleri."""
    for yol in glob.glob(os.path.join(glob.escape(hedef_dizin), GECICI_ONEK + "*")):
        bilgi = os.lstat(yol)
        if stat.S_ISDIR(bilgi.st_mode) and bilgi.st_uid == os.getuid():
            _log.info("yarim acma artigi siliniyor: %s", yol)
            _gecici_sil(yol)


def _gecici_sil(yol: str) -> None:
    """Yalniz BIZIM olusturdugumuz gecici acma dizini silinir."""
    if not os.path.isdir(yol):
        return
    try:
        shutil.rmtree(yol)
    except OSError as e:
        _log.warning("gecici acma dizini silinemedi: %s (%s)", yol, e)


def arsiv_ac(arsiv: str, hedef_dizin: str, dizin_adi: str, en_cok_bayt: int,
             en_cok_uye: int = EN_COK_UYE, iptal=None, ilerleme: Ilerleme = None,
             tahmini: int = 0, kullanim=shutil.disk_usage) -> str:
    """tar arsivini (xz/gz/bz2) guvenli acar; cross_sections.xml'i iceren dizin
    <hedef_dizin>/<dizin_adi> olur. Doner: o dizindeki cross_sections.xml.
    Kurallar: modul belgesi (GUVENLIK)."""
    if not _guvenli_ad_mi(dizin_adi):
        raise ArsivHatasi(_("geçersiz kütüphane dizin adı: %r") % (dizin_adi,))
    son = os.path.join(hedef_dizin, dizin_adi)
    if os.path.lexists(son):
        raise ArsivHatasi(_("hedefte aynı adlı klasör zaten var: %s") % son)
    _artiklari_sil(hedef_dizin)
    kok = os.path.realpath(tempfile.mkdtemp(prefix=GECICI_ONEK, dir=hedef_dizin))
    try:
        _ac(arsiv, kok, en_cok_bayt, en_cok_uye, iptal, ilerleme, tahmini, kullanim)
        xml = _xml_bul(kok)
        if xml is None:
            raise ArsivHatasi(_("arşivde cross_sections.xml yok"))
        os.replace(os.path.dirname(xml), son)
        os.chmod(son, _DIZIN_MODU)
    except (tarfile.TarError, EOFError, lzma.LZMAError, OSError) as e:
        _log.warning("arsiv acilamadi: %s", arsiv, exc_info=True)
        raise BozukArsiv(_("arşiv açılamadı (yarım ya da bozuk indirme?): %s") % e) from e
    finally:
        _gecici_sil(kok)
    return os.path.join(son, XS_DOSYASI)
