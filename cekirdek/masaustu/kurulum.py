# -*- coding: utf-8 -*-
"""
kurulum.py -- masaustu butunlesmesinin kur / kaldir / durum islemleri (v3 P2).

KURULAN (kullanici duzeyi; kok gerekmez; $XDG_DATA_HOME ~/.local/share, $XDG_CONFIG_HOME ~/.config)
  applications/openmc-arayuz.desktop             menu girdisi (Desktop Entry Spec 1.1)
  icons/hicolor/{16,32,48,128,256}x../apps/openmc-arayuz.png  +  scalable/apps/openmc-arayuz.svg
  mime/packages/openmc-arayuz-mime.xml           application/x-openmc-arayuz+json
  config/mimeapps.list                           [Default Applications] satiri (yalniz bu tur)
  openmc_arayuz/masaustu_manifest.json           yazilan her seyin listesi

MIME YAKLASIMI: "*.json" glob'u ve application/json'a DOKUNULMAZ (baska JSON dosyalari
etkilenmez). Tur yalniz iceriktir: dosya `{"surum":` ile baslar (cekirdek/sema.kaydet
bicimi), magic oncelik 80; sub-class-of application/json. Bu tur icin varsayilan acici
uygulama olur; baska "ile ac" secimlerine dokunulmaz.

KALDIRMA yalniz manifestteki dosyalari siler: yollar mutlak ve XDG koklerinin altinda
olmali, duz dosya olmali (sembolik baglanti IZLENMEZ, silinmez, uyari verilir). Araclarin
(update-mime-database, update-desktop-database) urettigi dosyalar manifestte "uretilen"
olarak ayridir; araclar yeniden calistirildiktan SONRA silinir. mimeapps.list'te yalniz
kendi satirimiz geri alinir. Tekrar kur / tekrar kaldir zararsizdir.
"""

import json
import logging
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from importlib import resources
from typing import Dict, List, Optional, Sequence, Tuple

from cekirdek import yollar

_log = logging.getLogger("openmc_arayuz.masaustu")

UYGULAMA_KIMLIGI = "openmc-arayuz"                  # .desktop adi, simge adi, WM sinifi, Qt adi
MIME_TURU = "application/x-openmc-arayuz+json"
KOMUT_ADI = "openmc-arayuz"                         # pyproject console_scripts
SIMGE_BOYUTLARI = (16, 32, 48, 128, 256)            # hicolor (paket/masaustu/ikon_uret.py ile ayni)
MANIFEST_ADI = "masaustu_manifest.json"
MANIFEST_SURUMU = 1
ARAC_ZAMAN_ASIMI = 60.0                             # s; xdg/update-* araci
# Exec degerinde alintilama gerektiren karakterler (Desktop Entry Spec, "Exec key")
_EXEC_OZEL = set(" \t\n\"'\\><~|&;$*?#()`")
_RESMI_KAYNAK = "kaynaklar"


class MasaustuHatasi(Exception):
    """Kurulum/kaldirma sirasinda kullaniciya gosterilecek hata."""


@dataclass(frozen=True)
class Durum:
    kurulu: bool
    dosyalar: Tuple[str, ...] = ()
    manifest: str = ""


@dataclass(frozen=True)
class _Kokler:
    veri: str          # $XDG_DATA_HOME
    ayar: str          # $XDG_CONFIG_HOME

    @property
    def uygulamalar(self) -> str:
        return os.path.join(self.veri, "applications")

    @property
    def mime(self) -> str:
        return os.path.join(self.veri, "mime")

    @property
    def simgeler(self) -> str:
        return os.path.join(self.veri, "icons", "hicolor")

    @property
    def mimeapps(self) -> str:
        return os.path.join(self.ayar, "mimeapps.list")

    @property
    def manifest(self) -> str:
        return os.path.join(yollar.kullanici_veri_dizini(_ortam_sozlugu(self)), MANIFEST_ADI)


def _ortam_sozlugu(kok: "_Kokler") -> Dict[str, str]:
    return {"XDG_DATA_HOME": kok.veri, "XDG_CONFIG_HOME": kok.ayar}


def _kokler(ortam: Optional[Dict[str, str]] = None) -> _Kokler:
    """XDG kokleri (yollar.py ile ayni kural: mutlak degilse yok sayilir)."""
    veri = os.path.dirname(yollar.kullanici_veri_dizini(ortam))
    ayar = os.path.dirname(yollar.ayar_dizini(ortam))
    return _Kokler(veri=veri, ayar=ayar)


# ---------------------------------------------------------------------------
# .desktop uretimi
# ---------------------------------------------------------------------------

def exec_alintila(yol: str) -> str:
    """Exec= icin tek arguman: gerekirse cift tirnak; %% ve ters bolu kacislari."""
    guvenli = yol.replace("%", "%%")
    if not any(c in _EXEC_OZEL for c in guvenli):
        return guvenli
    ic = []
    for c in guvenli:
        ic.append("\\" + c if c in '"`$\\' else c)
    # anahtar-deger dizgesinde ters bolu de kacirilir (Desktop Entry "Value types")
    return '"' + "".join(ic).replace("\\", "\\\\") + '"'


def _anahtar_kacisi(yol: str) -> str:
    return yol.replace("\\", "\\\\")


def calistirilabilir_coz(verilen: Optional[str] = None) -> str:
    """Mutlak, calistirilabilir openmc-arayuz yolu (yoksa MasaustuHatasi)."""
    if verilen is not None:
        aday = os.path.abspath(os.path.expanduser(verilen))
    else:
        yani = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), KOMUT_ADI)
        aday = yani if os.access(yani, os.X_OK) else (shutil.which(KOMUT_ADI) or "")
    if not aday or not os.path.isfile(aday) or not os.access(aday, os.X_OK):
        raise MasaustuHatasi(
            "%s bulunamadi (pip install ile kurulu mu?); yolu --exec ile verin" % KOMUT_ADI)
    if any(ord(c) < 32 for c in aday):
        raise MasaustuHatasi("calistirilabilir yolunda denetim karakteri var")
    return aday


def simge_yolu() -> str:
    """Paketle gelen SVG simgenin dosya yolu (pencere simgesi icin; Qt'siz)."""
    return str(resources.files("cekirdek.masaustu").joinpath(_RESMI_KAYNAK, UYGULAMA_KIMLIGI + ".svg"))


def desktop_metni(calistirilabilir: str) -> str:
    sablon = _kaynak("openmc-arayuz.desktop.sablon").decode("utf-8")
    return (sablon.replace("@EXEC@", exec_alintila(calistirilabilir))
                  .replace("@TRYEXEC@", _anahtar_kacisi(calistirilabilir)))


def _kaynak(ad: str) -> bytes:
    return resources.files("cekirdek.masaustu").joinpath(_RESMI_KAYNAK, ad).read_bytes()


# ---------------------------------------------------------------------------
# mimeapps.list ([Default Applications] satiri)
# ---------------------------------------------------------------------------

_VARSAYILAN_BASLIK = "[Default Applications]"


def varsayilan_ayarla(metin: str, mime: str, desktop: str) -> Tuple[str, Optional[str]]:
    """(yeni metin, onceki deger). Satir varsa degistirir, yoksa bolume ekler."""
    satirlar = metin.splitlines()
    onek = mime + "="
    onceki: Optional[str] = None
    bolumde = False
    for i, s in enumerate(satirlar):
        if s.startswith("["):
            if bolumde:                       # bolum bitti, satir yok: buraya ekle
                satirlar.insert(i, onek + desktop)
                return "\n".join(satirlar) + "\n", onceki
            bolumde = s.strip() == _VARSAYILAN_BASLIK
        elif bolumde and s.startswith(onek):
            onceki = s[len(onek):]
            satirlar[i] = onek + desktop
            return "\n".join(satirlar) + "\n", onceki
    if bolumde:
        satirlar.append(onek + desktop)
    else:
        satirlar.extend(([""] if satirlar else []) + [_VARSAYILAN_BASLIK, onek + desktop])
    return "\n".join(satirlar) + "\n", onceki


def varsayilan_geri_al(metin: str, mime: str, desktop: str,
                       onceki: Optional[str]) -> str:
    """Yalniz `mime=desktop` satirini geri alir (baskasinin secimine dokunmaz)."""
    satirlar = metin.splitlines()
    hedef = mime + "=" + desktop
    yeni: List[str] = []
    for s in satirlar:
        if s == hedef:
            if onceki is not None:
                yeni.append(mime + "=" + onceki)
            continue
        yeni.append(s)
    # bos kalan [Default Applications] bolumu (bizim actigimiz) sil
    temiz: List[str] = []
    for i, s in enumerate(yeni):
        sonraki = yeni[i + 1] if i + 1 < len(yeni) else "["
        if s.strip() == _VARSAYILAN_BASLIK and (sonraki.startswith("[") or sonraki == ""):
            continue
        temiz.append(s)
    while temiz and temiz[-1] == "":
        temiz.pop()
    return "\n".join(temiz) + "\n" if temiz else ""


# ---------------------------------------------------------------------------
# dosya islemleri
# ---------------------------------------------------------------------------

def _altinda(yol: str, kok: str) -> bool:
    yol, kok = os.path.normpath(yol), os.path.normpath(kok)
    return yol == kok or yol.startswith(kok + os.sep)


def _eksik_dizinler(ust: str) -> List[str]:
    """`ust` ve henuz var olmayan ust dizinleri (en ustten alta)."""
    eksik = []
    d = ust
    while not os.path.lexists(d):
        eksik.append(d)
        d = os.path.dirname(d)
    return list(reversed(eksik))


def _yaz(yol: str, icerik: bytes, olusturulan: List[str]) -> None:
    """Atomik yazim; hedef sembolik baglantiysa reddeder; olusan dizinleri kaydeder."""
    if os.path.islink(yol):
        raise MasaustuHatasi("hedef sembolik baglanti, yazilmadi: %s" % yol)
    ust = os.path.dirname(yol)
    olusturulan.extend(_eksik_dizinler(ust))
    os.makedirs(ust, exist_ok=True)
    fd, gecici = tempfile.mkstemp(dir=ust, prefix=".openmc-arayuz-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(icerik)
        os.chmod(gecici, 0o644)
        os.replace(gecici, yol)
    except BaseException:
        if os.path.lexists(gecici):
            os.unlink(gecici)
        raise


def _arac(arguman: Sequence[str]) -> bool:
    """Yardimci araci (varsa) calistirir; hata/eksik uyari olarak kaydedilir."""
    if shutil.which(arguman[0]) is None:
        _log.warning("%s yok; atlandi (dosyalar yine de yazildi)", arguman[0])
        return False
    try:
        sonuc = subprocess.run(list(arguman), capture_output=True, text=True,
                               timeout=ARAC_ZAMAN_ASIMI, check=False)
    except (OSError, subprocess.SubprocessError) as hata:
        _log.warning("%s calistirilamadi: %s", arguman[0], hata)
        return False
    if sonuc.returncode != 0:
        _log.warning("%s cikis %d: %s", arguman[0], sonuc.returncode, sonuc.stderr.strip())
        return False
    return True


def _veritabanlarini_tazele(kok: _Kokler) -> None:
    if os.path.isdir(kok.mime):
        _arac(["update-mime-database", kok.mime])
    if os.path.isdir(kok.uygulamalar):
        _arac(["update-desktop-database", "-q", kok.uygulamalar])
    if os.path.isfile(os.path.join(kok.simgeler, "index.theme")):
        _arac(["gtk-update-icon-cache", "-q", "-t", "-f", kok.simgeler])


def _okunur_mimeapps(yol: str) -> str:
    if not os.path.lexists(yol):
        return ""
    if os.path.islink(yol):
        raise MasaustuHatasi("mimeapps.list sembolik baglanti; dokunulmadi: %s" % yol)
    with open(yol, encoding="utf-8") as f:
        return f.read()


def _dosya_listesi(kok: _Kokler, calistirilabilir: str) -> List[Tuple[str, bytes]]:
    dosyalar = [(os.path.join(kok.uygulamalar, UYGULAMA_KIMLIGI + ".desktop"),
                 desktop_metni(calistirilabilir).encode("utf-8")),
                (os.path.join(kok.mime, "packages", UYGULAMA_KIMLIGI + "-mime.xml"),
                 _kaynak("openmc-arayuz-mime.xml")),
                (os.path.join(kok.simgeler, "scalable", "apps", UYGULAMA_KIMLIGI + ".svg"),
                 _kaynak("openmc-arayuz.svg"))]
    for b in SIMGE_BOYUTLARI:
        dosyalar.append((os.path.join(kok.simgeler, "%dx%d" % (b, b), "apps",
                                      UYGULAMA_KIMLIGI + ".png"),
                         _kaynak("openmc-arayuz-%d.png" % b)))
    return dosyalar


# ---------------------------------------------------------------------------
# kur / kaldir / durum
# ---------------------------------------------------------------------------

def kur(calistirilabilir: Optional[str] = None, varsayilan_yap: bool = True,
        simulasyon: bool = False, ortam: Optional[Dict[str, str]] = None) -> Durum:
    """Masaustu dosyalarini yazar ve veritabanlarini tazeler (tekrar calistirilabilir)."""
    kok = _kokler(ortam)
    yurutulecek = calistirilabilir_coz(calistirilabilir)
    dosyalar = _dosya_listesi(kok, yurutulecek)
    if simulasyon:
        for yol, _ in dosyalar:
            _log.info("yazilacak: %s", yol)
        return Durum(kurulu=False, dosyalar=tuple(y for y, _ in dosyalar))
    eski = _manifest_oku(kok.manifest)
    olusturulan: List[str] = list(eski.get("dizinler", [])) if eski else []
    mime_vardi = os.path.lexists(kok.mime)
    onbellek = os.path.join(kok.uygulamalar, "mimeinfo.cache")
    onbellek_vardi = os.path.lexists(onbellek)
    for yol, icerik in dosyalar:
        _yaz(yol, icerik, olusturulan)
    _veritabanlarini_tazele(kok)
    uretilen = [] if onbellek_vardi or not os.path.lexists(onbellek) else [onbellek]
    mimeapps = _varsayilan_yaz(kok, yurutulecek, varsayilan_yap, eski)
    manifest = {
        "surum": MANIFEST_SURUMU,
        "dosyalar": [y for y, _ in dosyalar],
        "uretilen": sorted(set(uretilen) | set(eski.get("uretilen", []) if eski else [])),
        "dizinler": sorted(set(olusturulan)),
        "mime_koku_olusturuldu": bool(eski and eski.get("mime_koku_olusturuldu")) or not mime_vardi,
        "mimeapps": mimeapps,
        "calistirilabilir": yurutulecek,
    }
    olusturulan.extend(_eksik_dizinler(os.path.dirname(kok.manifest)))
    manifest["dizinler"] = sorted(set(olusturulan))
    _yaz(kok.manifest, (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"), [])
    _log.info("masaustu butunlesmesi kuruldu (%d dosya)", len(dosyalar))
    return Durum(kurulu=True, dosyalar=tuple(manifest["dosyalar"]), manifest=kok.manifest)


def _varsayilan_yaz(kok: _Kokler, calistirilabilir: str, yap: bool,
                    eski: Optional[dict]) -> Optional[dict]:
    if not yap:
        return eski.get("mimeapps") if eski else None
    desktop = UYGULAMA_KIMLIGI + ".desktop"
    metin = _okunur_mimeapps(kok.mimeapps)
    yeni, onceki = varsayilan_ayarla(metin, MIME_TURU, desktop)
    if onceki == desktop and eski and eski.get("mimeapps"):
        return eski["mimeapps"]            # zaten bizim; ilk kurulumdaki onceki degeri koru
    olusturulan: List[str] = []
    _yaz(kok.mimeapps, yeni.encode("utf-8"), olusturulan)
    return {"yol": kok.mimeapps, "onceki": onceki,
            "dosya_olusturuldu": not metin, "dizinler": olusturulan}


def _manifest_oku(yol: str) -> Optional[dict]:
    if not os.path.lexists(yol):
        return None
    if os.path.islink(yol):
        raise MasaustuHatasi("manifest sembolik baglanti: %s" % yol)
    try:
        with open(yol, encoding="utf-8") as f:
            veri = json.load(f)
    except (OSError, ValueError) as hata:
        raise MasaustuHatasi("manifest okunamadi (%s): %s" % (yol, hata)) from hata
    if not isinstance(veri, dict) or veri.get("surum") != MANIFEST_SURUMU:
        raise MasaustuHatasi("manifest bicimi taninmiyor: %s" % yol)
    return veri


def durum(ortam: Optional[Dict[str, str]] = None) -> Durum:
    kok = _kokler(ortam)
    m = _manifest_oku(kok.manifest)
    if m is None:
        return Durum(kurulu=False)
    return Durum(kurulu=all(os.path.isfile(y) for y in m["dosyalar"]),
                 dosyalar=tuple(m["dosyalar"]), manifest=kok.manifest)


def _guvenli_sil(yol: str, kok: _Kokler) -> bool:
    """Manifest girdisini siler: mutlak + XDG koku altinda + duz dosya (symlink degil)."""
    if not isinstance(yol, str) or not os.path.isabs(yol) or not (
            _altinda(yol, kok.veri) or _altinda(yol, kok.ayar)):
        _log.warning("manifestte kok disi yol, silinmedi: %r", yol)
        return False
    try:
        mod = os.lstat(yol).st_mode
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(mod):
        _log.warning("duz dosya degil (sembolik baglanti vb.), silinmedi: %s", yol)
        return False
    os.unlink(yol)
    return True


def _bos_dizinleri_sil(dizinler: Sequence[str]) -> None:
    """Kurulumun actigi dizinleri (manifestte kayitli), BOSSA ve sembolik baglanti
    degilse sondan basa siler; ev dizini ve kok asla silinmez; dolu dizine dokunulmaz."""
    ev = os.path.expanduser("~")
    for d in sorted(set(dizinler), key=len, reverse=True):
        if not isinstance(d, str) or not os.path.isabs(d) or os.path.normpath(d) in (ev, os.sep):
            continue
        if os.path.isdir(d) and not os.path.islink(d) and not os.listdir(d):
            os.rmdir(d)


def _mimeapps_geri_al(bilgi: Optional[dict], kok: _Kokler) -> None:
    if not bilgi or bilgi.get("yol") != kok.mimeapps:
        return
    metin = _okunur_mimeapps(kok.mimeapps)
    yeni = varsayilan_geri_al(metin, MIME_TURU, UYGULAMA_KIMLIGI + ".desktop", bilgi.get("onceki"))
    if yeni == metin:
        return
    if not yeni.strip() and bilgi.get("dosya_olusturuldu"):
        _guvenli_sil(kok.mimeapps, kok)
    else:
        _yaz(kok.mimeapps, yeni.encode("utf-8"), [])
    _bos_dizinleri_sil(bilgi.get("dizinler", []))


def kaldir(ortam: Optional[Dict[str, str]] = None) -> int:
    """Manifestteki dosyalari siler; silinen dosya sayisini dondurur. Kurulu degilse 0."""
    kok = _kokler(ortam)
    m = _manifest_oku(kok.manifest)
    if m is None:
        _log.info("kurulu masaustu butunlesmesi yok (manifest yok)")
        return 0
    silinen = sum(_guvenli_sil(y, kok) for y in m["dosyalar"])
    _mimeapps_geri_al(m.get("mimeapps"), kok)
    _veritabanlarini_tazele(kok)
    silinen += sum(_guvenli_sil(y, kok) for y in m.get("uretilen", []))
    _mime_kokunu_sil(m, kok)
    _guvenli_sil(kok.manifest, kok)
    _bos_dizinleri_sil(m.get("dizinler", []))
    _log.info("masaustu butunlesmesi kaldirildi (%d dosya)", silinen)
    return silinen


def _mime_kokunu_sil(m: dict, kok: _Kokler) -> None:
    """mime/ dizinini biz actiysak ve packages/ bos kaldiysa, aracin urettigi
    veritabani dosyalariyla birlikte kaldirir (baska paket yoksa)."""
    if not m.get("mime_koku_olusturuldu"):
        return
    paketler = os.path.join(kok.mime, "packages")
    if os.path.islink(kok.mime) or not os.path.isdir(kok.mime):
        return
    if os.path.isdir(paketler) and os.listdir(paketler):
        return                                  # baska uygulamanin turleri var
    shutil.rmtree(kok.mime)
