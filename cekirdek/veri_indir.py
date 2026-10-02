# -*- coding: utf-8 -*-
"""
veri_indir.py -- OpenMC nukleer verisinin (tesir kesiti kutuphanesi + tukenme
zinciri) katalogdan guvenli indirilmesi (v3 K2). veri_indir.sh bu modulu cagirir.

KATALOG  cekirdek/veri_katalogu.json: openmc.org/data listesi (kaynak URL ve
         erisim tarihiyle), olculen bayt sayilari, bilinen sha256'lar, izinli
         alan adlari. Yuklenirken dogrulanir (katalog_yukle).

GUVENLIK
  - URL politikasi (UrlPolitikasi): uretimde YALNIZ https ve katalogdaki alan
    adlari; kullanici bilgisi (user:pw@) ve varsayilan disi port yok. Her
    yonlendirme adimi da ayni politikadan gecer. Testler gevsek politikayi
    YALNIZ nesne olarak verir (ortam degiskeni/ayar ile gevsetilemez).
  - TLS sertifikasi urllib'in varsayilan baglamiyla dogrulanir.
  - Indirme <hedef>.part dosyasina yapilir; bayt sayisi katalogdakiyle, sha256
    (biliniyorsa) dogrulanir, sonra os.replace ile ATOMIK yerine konur.
    Sunucunun bildirdigi boyut katalogdan farkliysa indirme baslamaz; katalogu
    asan bayt kabul edilmez.
  - Kesinti: .part kalir; sonraki cagri Range: bytes=N- ile surdurur (206 ve
    Content-Range baslangici N olmali; sunucu 200 donerse bastan yazilir).
  - Disk alani indirmeden ONCE denetlenir (kalan indirme + acilmis boyut + pay).
  - Arsiv acma: cekirdek/veri_arsiv.py (yol gecisi, baglanti, zip bombasi).

KOMUT SATIRI
  python -m cekirdek.veri_indir --liste
  python -m cekirdek.veri_indir [--hedef DIZIN] [--kutuphane KIMLIK]
                                [--zincir KIMLIK ...] [--yalniz-zincir] [--bashrc]
  Basarida secim uygulama ayarina yazilir (cekirdek/veri_yolu.py).
"""

import argparse
import hashlib
import http.client
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Optional, Tuple

from cekirdek import veri_arsiv, yollar
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from cekirdek.veri_arsiv import IptalEdildi, VeriHatasi  # noqa: F401 -- disa aktarim

_log = kaydedici(__name__)

KATALOG_DOSYASI = "veri_katalogu.json"
PARCA_UZANTISI = ".part"
INDIRME_DIZINI = ".indirilen"         # <hedef>/.indirilen/<kimlik>.tar.xz(.part)
ZINCIR_DIZINI = "chain"               # = veri_yolu.ZINCIR_DIZINI (cozumleyici burada arar)
MAKBUZ = "KAYNAK.json"                # kurulan kutuphane dizinindeki kaynak kaydi
# Okuma parcasi: bellek ve ilerleme bildirimi sikligi dengesi (tasarim secimi).
PARCA_BOYUTU = 256 * 1024
BAGLANTI_ZAMAN_ASIMI = 60.0           # s; okuma basina (urllib timeout)
EN_COK_YONLENDIRME = 5                # anl.box.com -> anl.app.box.com -> boxcloud: 3 adim
# Zip bombasi siniri: acilmis boyut tahmini x bu carpan (olculen ENDF/B-VIII.0
# oraninin ustune pay; tasarim secimi).
BOMBA_CARPANI = 3.0
VARSAYILAN_KUTUPHANE = "endfb-viii.0"
_SHA256_DESENI = re.compile(r"^[0-9a-f]{64}$")
_KUTUPHANE_ALANLARI = ("kimlik", "ad", "url", "bayt", "dizin_adi")
_ZINCIR_ALANLARI = ("kimlik", "ad", "url", "bayt", "dosya_adi")


class IndirmeHatasi(VeriHatasi):
    """Ag, politika, boyut ya da sha256 hatasi (mesaj kullaniciya gosterilir)."""


# ---------------------------------------------------------------------------
# katalog
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Oge:
    """Katalogdaki bir kutuphane (tur="kutuphane") ya da zincir (tur="zincir")."""
    kimlik: str
    ad: str
    tur: str
    url: str
    bayt: int
    sha256: Optional[str] = None
    dizin_adi: Optional[str] = None       # kutuphane: <hedef>/<dizin_adi>/
    dosya_adi: Optional[str] = None       # zincir: <hedef>/chain/<dosya_adi>
    acik_bayt: Optional[int] = None       # acilmis boyut (olculduyse)
    grup: str = ""
    icerik: str = ""
    sicakliklar: str = ""
    notu: str = ""
    lisans_notu: str = ""
    degerlendirme_sayfasi: str = ""
    kutuphane: Optional[str] = None       # zincir: ait oldugu kutuphane (CASL: None)
    spektrum: Optional[str] = None        # zincir: "termal" | "hizli"
    nuklid: Optional[int] = None
    uygulamada_kullanilir: bool = False   # zincir: tukenme.ZINCIRLER'deki adlardan mi


@dataclass(frozen=True)
class Katalog:
    kutuphaneler: Tuple[Oge, ...]
    zincirler: Tuple[Oge, ...]
    alanlar: frozenset
    oran: float
    oran_kaynagi: str
    kaynak: dict = field(default_factory=dict)

    def bul(self, kimlik: str) -> Optional[Oge]:
        return next((o for o in self.kutuphaneler + self.zincirler if o.kimlik == kimlik), None)


@dataclass(frozen=True)
class UrlPolitikasi:
    """Izin verilen URL'ler. port_serbest yalniz yerel test sunucusu icindir."""
    semalar: frozenset = frozenset({"https"})
    alanlar: frozenset = frozenset()
    port_serbest: bool = False

    def denetle(self, url: str) -> None:
        try:
            p = urllib.parse.urlsplit(url)
            port = p.port
        except ValueError as e:
            raise IndirmeHatasi(_("geçersiz adres: %s") % url) from e
        if p.scheme not in self.semalar:
            raise IndirmeHatasi(_("yalnız https adreslerine izin var: %s") % url)
        if (p.hostname or "").lower() not in self.alanlar:
            raise IndirmeHatasi(_("izin listesinde olmayan alan adı: %s") % (p.hostname or url))
        if p.username or p.password:
            raise IndirmeHatasi(_("adreste kullanıcı bilgisine izin yok: %s") % p.hostname)
        if port is not None and not self.port_serbest and port != 443:
            raise IndirmeHatasi(_("varsayılan dışı porta izin yok: %s") % url)


def katalog_yolu() -> str:
    return os.path.join(yollar.paket_koku(), "cekirdek", KATALOG_DOSYASI)


def _ad_guvenli(ad) -> bool:
    return isinstance(ad, str) and veri_arsiv._guvenli_ad_mi(ad)


def _oge_kur(kayit: dict, tur: str, politika: UrlPolitikasi) -> Oge:
    gerekli = _KUTUPHANE_ALANLARI if tur == "kutuphane" else _ZINCIR_ALANLARI
    eksik = [a for a in gerekli if a not in kayit]
    if eksik:
        raise ValueError("katalog kaydinda eksik alan %s: %r" % (eksik, kayit.get("kimlik")))
    try:
        politika.denetle(kayit["url"])
    except IndirmeHatasi as e:
        raise ValueError("katalog URL'si gecersiz (%s): %s" % (kayit["kimlik"], e)) from e
    bayt, sha = kayit["bayt"], kayit.get("sha256")
    if not isinstance(bayt, int) or isinstance(bayt, bool) or bayt <= 0:
        raise ValueError("katalog bayt sayisi gecersiz: %r" % kayit["kimlik"])
    if sha is not None and not _SHA256_DESENI.match(str(sha)):
        raise ValueError("katalog sha256 gecersiz: %r" % kayit["kimlik"])
    ad_alani = "dizin_adi" if tur == "kutuphane" else "dosya_adi"
    if not _ad_guvenli(kayit[ad_alani]):
        raise ValueError("katalog %s gecersiz: %r" % (ad_alani, kayit[ad_alani]))
    return Oge(kimlik=kayit["kimlik"], ad=kayit["ad"], tur=tur, url=kayit["url"], bayt=bayt,
               sha256=sha, dizin_adi=kayit.get("dizin_adi"), dosya_adi=kayit.get("dosya_adi"),
               acik_bayt=kayit.get("acik_bayt"), grup=kayit.get("grup", ""),
               icerik=kayit.get("icerik", ""), sicakliklar=kayit.get("sicakliklar", ""),
               notu=kayit.get("not", ""), lisans_notu=kayit.get("lisans_notu", ""),
               degerlendirme_sayfasi=kayit.get("degerlendirme_sayfasi", ""),
               kutuphane=kayit.get("kutuphane"), spektrum=kayit.get("spektrum"),
               nuklid=kayit.get("nuklid"),
               uygulamada_kullanilir=bool(kayit.get("uygulamada_kullanilir")))


def katalog_yukle(yol: Optional[str] = None) -> Katalog:
    """Katalogu okur ve dogrular; gecersiz katalog ValueError (OSError da olabilir)."""
    with open(yol or katalog_yolu(), encoding="utf-8") as f:
        veri = json.load(f)
    alanlar = frozenset(a.lower() for a in veri["izinli_alan_adlari"])
    politika = UrlPolitikasi(alanlar=alanlar)
    kutup = tuple(_oge_kur(k, "kutuphane", politika) for k in veri["kutuphaneler"])
    zincir = tuple(_oge_kur(k, "zincir", politika) for k in veri["zincirler"])
    kimlikler = [o.kimlik for o in kutup + zincir]
    if len(kimlikler) != len(set(kimlikler)):
        raise ValueError("katalogda tekrarlanan kimlik")
    oran = veri["acik_boyut_orani"]
    return Katalog(kutup, zincir, alanlar, float(oran["deger"]), oran["kaynak"],
                   dict(veri["kaynak"]))


def katalog_politikasi(katalog: Katalog) -> UrlPolitikasi:
    """Uretim politikasi: yalniz https + katalogdaki alan adlari."""
    return UrlPolitikasi(alanlar=katalog.alanlar)


# ---------------------------------------------------------------------------
# tek dosya indirme
# ---------------------------------------------------------------------------

class _Yonlendirme(urllib.request.HTTPRedirectHandler):
    max_redirections = EN_COK_YONLENDIRME

    def __init__(self, politika: UrlPolitikasi):
        super().__init__()
        self._politika = politika

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        self._politika.denetle(newurl)          # izinsiz adrese istek GITMEZ
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _acici(politika: UrlPolitikasi):
    return urllib.request.build_opener(_Yonlendirme(politika))


def _istek(url: str, bas: int) -> urllib.request.Request:
    from cekirdek.surum import surum
    basliklar = {"User-Agent": "openmc-arayuz/%s" % surum()}
    if bas:
        basliklar["Range"] = "bytes=%d-" % bas
    return urllib.request.Request(url, headers=basliklar)


def _dosya_sha256(yol: str, hasher=None):
    hasher = hasher or hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(PARCA_BOYUTU), b""):
            hasher.update(parca)
    return hasher


def _sil(yol: str) -> None:
    try:
        os.unlink(yol)
    except FileNotFoundError:
        return
    except OSError:
        _log.warning("dosya silinemedi: %s", yol, exc_info=True)


def _aralik_baslangici(yanit, beklenen: int) -> int:
    """206 yanitinin Content-Range baslangici; toplam katalogdan farkliysa hata."""
    m = re.match(r"bytes (\d+)-(\d+)/(\d+)", yanit.headers.get("Content-Range", ""))
    if not m or int(m.group(3)) != beklenen:
        raise IndirmeHatasi(_("sunucunun bildirdiği boyut katalogdan farklı (%s, beklenen %d)")
                            % (yanit.headers.get("Content-Range"), beklenen))
    return int(m.group(1))


def _ac(url, bas, politika, zaman_asimi):
    """(yanit, gercek baslangic) -- 416 + tam parca ise (None, bas)."""
    try:
        yanit = _acici(politika).open(_istek(url, bas), timeout=zaman_asimi)
    except urllib.error.HTTPError as e:
        if e.code == 416 and bas:
            return None, bas
        raise IndirmeHatasi(_("sunucu hata verdi: HTTP %d (%s)") % (e.code, url)) from e
    except (urllib.error.URLError, OSError) as e:
        raise IndirmeHatasi(_("bağlantı kurulamadı: %s") % getattr(e, "reason", e)) from e
    return yanit, bas


def _yanit_baslangici(yanit, bas: int, beklenen: int) -> int:
    if yanit.status == 206:
        gercek = _aralik_baslangici(yanit, beklenen)
        if gercek != bas:
            raise IndirmeHatasi(_("sunucu istenmeyen aralık gönderdi (%d, istenen %d)")
                                % (gercek, bas))
        return bas
    if yanit.status != 200:
        raise IndirmeHatasi(_("beklenmeyen HTTP yanıtı: %d") % yanit.status)
    uzunluk = yanit.headers.get("Content-Length")
    if uzunluk is not None and int(uzunluk) != beklenen:
        raise IndirmeHatasi(_("sunucunun bildirdiği boyut katalogdan farklı (%s, beklenen %d)")
                            % (uzunluk, beklenen))
    return 0                                    # aralik yok sayildi: bastan


def _akit(yanit, parca, bas, beklenen, hasher, ilerleme, iptal) -> int:
    alinan = bas
    with open(parca, "ab" if bas else "wb") as f:
        try:
            for blok in iter(lambda: yanit.read(PARCA_BOYUTU), b""):
                alinan += len(blok)
                if alinan > beklenen:
                    raise IndirmeHatasi(_("sunucu katalogdaki boyuttan fazla veri gönderdi"))
                f.write(blok)
                hasher.update(blok)
                if ilerleme:
                    ilerleme(alinan, beklenen)
                if iptal is not None and iptal.is_set():
                    raise IptalEdildi(_("indirme iptal edildi; kaldığı yerden sürdürülebilir"))
        except (OSError, ValueError, http.client.HTTPException) as e:   # IncompleteRead, zaman asimi
            _log.warning("indirme kesildi (%d/%d bayt)", alinan, beklenen, exc_info=True)
            raise IndirmeHatasi(_("indirme kesildi (%d / %d bayt); yeniden deneyin, kaldığı "
                                  "yerden sürer: %s") % (alinan, beklenen, e)) from e
        f.flush()
        os.fsync(f.fileno())
    return alinan


def _hazir_mi(hedef, beklenen, sha256) -> Optional[str]:
    if not os.path.isfile(hedef) or os.path.getsize(hedef) != beklenen:
        return None
    ozet = _dosya_sha256(hedef).hexdigest()
    return ozet if sha256 is None or ozet == sha256 else None


def dosya_indir(url: str, hedef: str, beklenen_bayt: int, sha256: Optional[str] = None,
                politika: Optional[UrlPolitikasi] = None,
                ilerleme: Optional[Callable[[int, int], None]] = None, iptal=None,
                zaman_asimi: float = BAGLANTI_ZAMAN_ASIMI) -> str:
    """url'yi hedef'e indirir (kurallar: modul belgesi). Doner: sha256 (hex).
    politika None -> uretim politikasi (katalog). Hata: IndirmeHatasi /
    IptalEdildi (yarim .part surdurme icin kalir; sha256 hatasinda silinir)."""
    politika = politika or katalog_politikasi(katalog_yukle())
    politika.denetle(url)
    hazir = _hazir_mi(hedef, beklenen_bayt, sha256)
    if hazir:
        return hazir
    parca = hedef + PARCA_UZANTISI
    bas = os.path.getsize(parca) if os.path.isfile(parca) else 0
    if bas > beklenen_bayt:
        _sil(parca)
        bas = 0
    yanit, bas = _ac(url, bas, politika, zaman_asimi)
    if yanit is None:                           # 416: sunucuya gore parca zaten tam
        if bas != beklenen_bayt:
            _sil(parca)
            raise IndirmeHatasi(_("sunucu aralığı reddetti; yarım parça silindi, yeniden "
                                  "deneyin"))
        alinan, hasher = bas, _dosya_sha256(parca)
    else:
        with yanit:
            bas = _yanit_baslangici(yanit, bas, beklenen_bayt)
            hasher = _dosya_sha256(parca) if bas else hashlib.sha256()
            alinan = _akit(yanit, parca, bas, beklenen_bayt, hasher, ilerleme, iptal)
    if alinan != beklenen_bayt:
        raise IndirmeHatasi(_("indirme yarım kaldı (%d / %d bayt); yeniden deneyin, kaldığı "
                              "yerden sürer") % (alinan, beklenen_bayt))
    ozet = hasher.hexdigest()
    if sha256 and ozet != sha256:
        _sil(parca)
        raise IndirmeHatasi(_("sha256 tutmuyor (beklenen %s…, gelen %s…); dosya silindi, "
                              "yeniden indirin") % (sha256[:12], ozet[:12]))
    os.replace(parca, hedef)
    return ozet


# ---------------------------------------------------------------------------
# kurulum: kutuphane (arsiv) ve zincir (tek dosya)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Kurulum:
    yol: str                     # cross_sections.xml ya da zincir dosyasi
    sha256: Optional[str]
    atlandi: bool = False        # zaten kuruluydu; indirme yapilmadi


Asamali = Optional[Callable[[str, int, int], None]]   # (asama, alinan, toplam)


def _asama(ilerleme: Asamali, ad: str):
    if ilerleme is None:
        return None
    return lambda alinan, toplam: ilerleme(ad, alinan, toplam)


def acik_tahmini(oge: Oge, oran: float) -> int:
    """Acilmis boyut: olculduyse o, degilse arsiv x katalog orani (tahmin)."""
    return int(oge.acik_bayt or oge.bayt * oran)


def gereken_alan(oge: Oge, oran: float, hedef: str) -> int:
    """Kalan indirme + (kutuphanede) acilmis boyut, bayt (disk denetimi icin)."""
    if oge.tur == "zincir":
        parca = os.path.join(hedef, ZINCIR_DIZINI, oge.dosya_adi or "") + PARCA_UZANTISI
        return oge.bayt - (os.path.getsize(parca) if os.path.isfile(parca) else 0)
    parca = os.path.join(hedef, INDIRME_DIZINI, oge.kimlik + ".tar.xz" + PARCA_UZANTISI)
    mevcut = os.path.getsize(parca) if os.path.isfile(parca) else 0
    return oge.bayt - mevcut + acik_tahmini(oge, oran)


def _makbuz_yaz(dizin: str, oge: Oge, sha: str) -> None:
    from datetime import datetime, timezone
    kayit = {"kimlik": oge.kimlik, "ad": oge.ad, "url": oge.url, "bayt": oge.bayt,
             "sha256": sha, "indirme": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "katalog_kaynagi": katalog_yukle().kaynak.get("sayfa")}
    with open(os.path.join(dizin, MAKBUZ), "w", encoding="utf-8") as f:
        json.dump(kayit, f, ensure_ascii=False, indent=1)


def _makbuz_sha(dizin: str) -> Optional[str]:
    try:
        with open(os.path.join(dizin, MAKBUZ), encoding="utf-8") as f:
            return json.load(f).get("sha256")
    except (OSError, ValueError):
        return None


def kutuphane_kur(oge: Oge, hedef_dizin: str, oran: float,
                  politika: Optional[UrlPolitikasi] = None, ilerleme: Asamali = None,
                  iptal=None, kullanim=shutil.disk_usage) -> Kurulum:
    """Kutuphaneyi <hedef>/<dizin_adi>/ altina kurar: disk denetimi, surdurulebilir
    indirme, guvenli acma, makbuz (KAYNAK.json); arsiv basarida silinir.
    Zaten kuruluysa (cross_sections.xml var) indirmez."""
    hedef = veri_arsiv.hedef_dogrula(hedef_dizin)
    dizin = os.path.join(hedef, oge.dizin_adi)
    xml = os.path.join(dizin, veri_arsiv.XS_DOSYASI)
    if os.path.isfile(xml):
        return Kurulum(xml, _makbuz_sha(dizin), atlandi=True)
    if os.path.lexists(dizin):
        raise veri_arsiv.ArsivHatasi(_("%s var ama içinde cross_sections.xml yok; klasörü "
                                       "taşıyın ya da başka hedef seçin") % dizin)
    veri_arsiv.disk_denetle(hedef, gereken_alan(oge, oran, hedef), kullanim)
    indirme = os.path.join(hedef, INDIRME_DIZINI)
    os.makedirs(indirme, exist_ok=True)
    arsiv = os.path.join(indirme, oge.kimlik + ".tar.xz")
    sha = dosya_indir(oge.url, arsiv, oge.bayt, oge.sha256, politika,
                      _asama(ilerleme, "indirme"), iptal)
    tahmin = acik_tahmini(oge, oran)
    xml = veri_arsiv.arsiv_ac(arsiv, hedef, oge.dizin_adi, int(tahmin * BOMBA_CARPANI),
                              iptal=iptal, ilerleme=_asama(ilerleme, "acma"), tahmini=tahmin,
                              kullanim=kullanim)
    _makbuz_yaz(dizin, oge, sha)
    _sil(arsiv)
    return Kurulum(xml, sha)


def zincir_kur(oge: Oge, hedef_dizin: str, politika: Optional[UrlPolitikasi] = None,
               ilerleme: Asamali = None, iptal=None, kullanim=shutil.disk_usage) -> Kurulum:
    """Zinciri <hedef>/chain/<dosya_adi> olarak indirir (sha256 biliniyorsa dogrulanir)."""
    hedef = veri_arsiv.hedef_dogrula(hedef_dizin)
    dizin = os.path.join(hedef, ZINCIR_DIZINI)
    os.makedirs(dizin, exist_ok=True)
    yol = os.path.join(dizin, oge.dosya_adi)
    veri_arsiv.disk_denetle(hedef, gereken_alan(oge, 1.0, hedef), kullanim)
    sha = dosya_indir(oge.url, yol, oge.bayt, oge.sha256, politika,
                      _asama(ilerleme, "indirme"), iptal)
    return Kurulum(yol, sha)


# ---------------------------------------------------------------------------
# komut satiri
# ---------------------------------------------------------------------------

def _argumanlar():
    p = argparse.ArgumentParser(
        prog="veri_indir", description=_("OpenMC nükleer verisini openmc.org kataloğundan "
                                         "güvenli indirir (sürdürülebilir, sha256)."))
    p.add_argument("--liste", action="store_true", help=_("katalogu listele ve çık"))
    p.add_argument("--hedef", help=_("hedef klasör (varsayılan: ~/nucdata ya da son seçim)"))
    p.add_argument("--kutuphane", default=VARSAYILAN_KUTUPHANE,
                   help=_("kütüphane kimliği (--liste)"))
    p.add_argument("--zincir", action="append",
                   help=_("zincir kimliği; birden çok verilebilir (varsayılan: uygulamanın "
                          "kullandığı termal/hızlı/CASL zincirleri)"))
    p.add_argument("--yalniz-zincir", action="store_true", help=_("yalnız zincirleri indir"))
    p.add_argument("--bashrc", action="store_true",
                   help=_("bitince ortam değişkenlerini ~/.bashrc'ye ekle"))
    return p


def _liste(kat: Katalog) -> None:
    print(_("Kaynak: %s (erişim %s)") % (kat.kaynak.get("sayfa"), kat.kaynak.get("erisim_tarihi")))
    print(_("\nKütüphaneler:"))
    for o in kat.kutuphaneler:
        print("  %-18s %-26s %6.2f GB  %s" % (o.kimlik, o.ad, o.bayt / veri_arsiv.GB, o.grup))
    print(_("\nZincirler:"))
    for o in kat.zincirler:
        print("  %-20s %-32s %7.1f MB%s" % (o.kimlik, o.ad, o.bayt / 1e6,
                                             "  *" if o.uygulamada_kullanilir else ""))
    print(_("\n* uygulamanın tükenme hesabında kullandığı zincirler"))


def _ilerleme_yazici():
    son = {}

    def yaz(asama, alinan, toplam):
        yuzde = int(100 * alinan / toplam) if toplam else 0
        if son.get(asama) != yuzde // 5:
            son[asama] = yuzde // 5
            print("   %s %3d%%" % (asama, yuzde), flush=True)
    return yaz


def _secimler(a, kat: Katalog):
    """(kutuphane | None, [zincirler]) ya da hata metni."""
    kutup = None if a.yalniz_zincir else kat.bul(a.kutuphane)
    if not a.yalniz_zincir and (kutup is None or kutup.tur != "kutuphane"):
        return _("bilinmeyen kütüphane: %s (--liste)") % a.kutuphane
    kimlikler = a.zincir or [o.kimlik for o in kat.zincirler if o.uygulamada_kullanilir]
    zincirler = [kat.bul(k) for k in kimlikler]
    if any(z is None or z.tur != "zincir" for z in zincirler):
        return _("bilinmeyen zincir: %s (--liste)") % ", ".join(kimlikler)
    return kutup, zincirler


def _bashrc(satirlar) -> None:
    yol = os.path.expanduser("~/.bashrc")
    isaret = "# OpenMC verisi (openmc_arayuz veri_indir)"
    mevcut = open(yol, encoding="utf-8").read() if os.path.isfile(yol) else ""
    if isaret in mevcut:
        print(_("~/.bashrc'de zaten bir openmc_arayuz bölümü var; değiştirilmedi."))
        return
    with open(yol, "a", encoding="utf-8") as f:
        f.write("\n%s\n%s\n" % (isaret, "\n".join(satirlar)))
    print(_("~/.bashrc'ye eklendi. Yeni bir terminal açın ya da: source ~/.bashrc"))


def _kur_hepsi(kutup, zincirler, hedef, kat):
    """(cross_sections.xml | None, ayara yazilacak zincir | None)."""
    from cekirdek import veri_yolu
    yaz = _ilerleme_yazici()
    zincir_yollari = []
    for z in zincirler:
        print(_("== zincir: %s") % z.ad)
        zincir_yollari.append(zincir_kur(z, hedef, ilerleme=yaz).yol)
    xml = None
    if kutup is not None:
        print(_("== kütüphane: %s (%.2f GB)") % (kutup.ad, kutup.bayt / veri_arsiv.GB))
        xml = kutuphane_kur(kutup, hedef, kat.oran, ilerleme=yaz).yol
    varsayilan = [y for y in zincir_yollari
                  if os.path.basename(y) == veri_yolu.VARSAYILAN_ZINCIR]
    return xml, (varsayilan or zincir_yollari or [None])[0]


def main(argv=None) -> int:
    """Cikis: 0 tamam, 1 indirme/kurma hatasi, 2 kullanim hatasi."""
    from cekirdek import veri_yolu
    a = _argumanlar().parse_args(argv)
    kat = katalog_yukle()
    if a.liste:
        _liste(kat)
        return 0
    secim = _secimler(a, kat)
    if isinstance(secim, str):
        print(secim, file=sys.stderr)
        return 2
    try:
        hedef = veri_arsiv.hedef_dogrula(a.hedef or veri_yolu.varsayilan_indirme_hedefi())
        xml, zincir_yolu = _kur_hepsi(secim[0], secim[1], hedef, kat)
    except VeriHatasi as e:
        print(_("HATA: %s") % e, file=sys.stderr)
        return 1
    ayar = {"indirme_hedefi": hedef, "zincir": zincir_yolu}
    if xml:
        ayar.update(cross_sections=xml, kutuphane=secim[0].kimlik)
    veri_yolu.ayar_yaz({k: v for k, v in ayar.items() if v})
    satirlar = (['export OPENMC_CROSS_SECTIONS="%s"' % xml] if xml else []) + (
        ['export OPENMC_CHAIN_FILE="%s"' % zincir_yolu] if zincir_yolu else [])
    print(_("\nBitti. Seçim uygulama ayarına yazıldı (%s).") % veri_yolu.ayar_yolu())
    if a.bashrc:
        _bashrc(satirlar)
    else:
        print(_("Terminalden openmc kullanacaksanız:\n%s") % "\n".join(satirlar))
    return 0


if __name__ == "__main__":
    sys.exit(main())
