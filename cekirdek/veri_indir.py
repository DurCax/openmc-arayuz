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
_AD_DESENI = re.compile(r"^[A-Za-z0-9._-]+$")       # katalog dizin_adi / dosya_adi
# Katalogdaki "degerlendirme sayfasi" baglantilarinin izinli alanlari (yalniz
# gosterilir, indirilmez): NNDC, OECD-NEA, JAEA, IAEA.
DEGERLENDIRME_ALANLARI = frozenset({"www.nndc.bnl.gov", "www.oecd-nea.org",
                                    "wwwndc.jaea.go.jp", "www-nds.iaea.org"})
_PARCA_MODU = 0o600                                 # .part: yalniz sahibi
_INDIRME_MODU = 0o700                               # .indirilen/
_ZINCIR_MODU = 0o755                                # chain/ (digerleri okuyabilir)
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
    en: tuple = ()                        # ((alan, Ingilizce metin), ...) katalogdan

    def metin(self, alan: str) -> str:
        """icerik / notu / lisans_notu etkin dilde (katalogun "en" alanlari)."""
        from cekirdek.ceviri import etkin_dil
        if etkin_dil() == "en":
            ceviri = dict(self.en).get("not" if alan == "notu" else alan)
            if ceviri is not None:
                return ceviri
        return getattr(self, alan)

    def gorunen_ad(self) -> str:
        """Zincirde "<kutuphane> — termal/hizli" (CASL: "CASL (sadelestirilmis)"),
        etkin dilde; kutuphanede adin kendisi (ozel ad, cevrilmez)."""
        if self.tur != "zincir":
            return self.ad
        spektrum = {"termal": _("termal"), "hizli": _("hızlı")}.get(self.spektrum, "")
        kaynak = self.ad.rsplit(" ", 1)[0] if self.kutuphane else _("CASL (sadeleştirilmiş)")
        return "%s — %s" % (kaynak, spektrum)


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
    return (isinstance(ad, str) and bool(_AD_DESENI.match(ad))
            and veri_arsiv._guvenli_ad_mi(ad))


def _degerlendirme_denetle(kayit: dict) -> None:
    url = kayit.get("degerlendirme_sayfasi")
    if not url:
        return
    try:
        UrlPolitikasi(alanlar=DEGERLENDIRME_ALANLARI).denetle(url)
    except IndirmeHatasi as e:
        raise ValueError("degerlendirme sayfasi gecersiz (%s): %s" % (kayit["kimlik"], e)) from e


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
    _degerlendirme_denetle(kayit)
    return Oge(kimlik=kayit["kimlik"], ad=kayit["ad"], tur=tur, url=kayit["url"], bayt=bayt,
               sha256=sha, dizin_adi=kayit.get("dizin_adi"), dosya_adi=kayit.get("dosya_adi"),
               acik_bayt=kayit.get("acik_bayt"), grup=kayit.get("grup", ""),
               icerik=kayit.get("icerik", ""), sicakliklar=kayit.get("sicakliklar", ""),
               notu=kayit.get("not", ""), lisans_notu=kayit.get("lisans_notu", ""),
               degerlendirme_sayfasi=kayit.get("degerlendirme_sayfasi", ""),
               kutuphane=kayit.get("kutuphane"), spektrum=kayit.get("spektrum"),
               nuklid=kayit.get("nuklid"),
               uygulamada_kullanilir=bool(kayit.get("uygulamada_kullanilir")),
               en=tuple(sorted((kayit.get("en") or {}).items())))


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


def _dosya_sha256(yol: str, hasher=None, iptal=None):
    """Dosyanin sha256'si (surdurmede var olan parca icin); iptal dinlenir."""
    hasher = hasher or hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(PARCA_BOYUTU), b""):
            if iptal is not None and iptal.is_set():
                raise IptalEdildi(_("indirme iptal edildi; kaldığı yerden sürdürülebilir"))
            hasher.update(parca)
    return hasher


def _baglanti_degil(yol: str) -> None:
    if os.path.islink(yol):
        raise IndirmeHatasi(_("güvenlik: %s bir sembolik bağlantı; silin ya da başka hedef "
                              "seçin") % yol)


def _parca_ac(parca: str, ekle: bool) -> int:
    """.part dosyasini symlink izlemeden, 0600 ile acar (os.open O_NOFOLLOW)."""
    bayrak = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | (os.O_APPEND if ekle else os.O_TRUNC)
    try:
        return os.open(parca, bayrak, _PARCA_MODU)
    except OSError as e:
        raise IndirmeHatasi(_("geçici dosya açılamadı: %s (%s)") % (parca, e)) from e


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
    if not m or int(m.group(3)) != beklenen or int(m.group(2)) != beklenen - 1:
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
    if yanit.headers.get("Content-Encoding", "identity").lower() != "identity":
        raise IndirmeHatasi(_("sunucu sıkıştırılmış aktarım gönderdi (Content-Encoding: %s); "
                              "bayt sayısı denetlenemez") % yanit.headers.get("Content-Encoding"))
    if yanit.status == 206:
        gercek = _aralik_baslangici(yanit, beklenen)
        if gercek != bas:
            raise IndirmeHatasi(_("sunucu istenmeyen aralık gönderdi (%d, istenen %d)")
                                % (gercek, bas))
        return bas
    if yanit.status != 200:
        raise IndirmeHatasi(_("beklenmeyen HTTP yanıtı: %d") % yanit.status)
    uzunluk = yanit.headers.get("Content-Length")
    if uzunluk is not None and (not uzunluk.strip().isdigit() or int(uzunluk) != beklenen):
        raise IndirmeHatasi(_("sunucunun bildirdiği boyut katalogdan farklı (%s, beklenen %d)")
                            % (uzunluk, beklenen))
    return 0                                    # aralik yok sayildi: bastan


def _akit(yanit, parca, bas, beklenen, hasher, ilerleme, iptal) -> int:
    alinan = bas
    with os.fdopen(_parca_ac(parca, ekle=bool(bas)), "ab" if bas else "wb") as f:
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


def _hazir_mi(hedef, beklenen, sha256, iptal=None) -> Optional[str]:
    """Hedef zaten tam mi: sha256 biliniyorsa karma, BILINMIYORSA YALNIZ BOYUT
    denetlenir (ayni boyutta bozuk dosya yakalanmaz; makbuzda/arayuzde
    "sha256 yok" etiketi bunu soyler). Symlink reddedilir."""
    _baglanti_degil(hedef)
    if not os.path.isfile(hedef) or os.path.getsize(hedef) != beklenen:
        return None
    ozet = _dosya_sha256(hedef, iptal=iptal).hexdigest()
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
    hazir = _hazir_mi(hedef, beklenen_bayt, sha256, iptal)
    if hazir:
        return hazir
    parca = hedef + PARCA_UZANTISI
    _baglanti_degil(parca)
    bas = os.path.getsize(parca) if os.path.isfile(parca) else 0
    hasher = _dosya_sha256(parca, iptal=iptal) if bas else None   # agdan once: iptal ucuz
    if bas > beklenen_bayt:
        _sil(parca)
        bas = 0
    yanit, bas = _ac(url, bas, politika, zaman_asimi)
    if yanit is None:                           # 416: sunucuya gore parca zaten tam
        if bas != beklenen_bayt:
            _sil(parca)
            raise IndirmeHatasi(_("sunucu aralığı reddetti; yarım dosya silindi, yeniden "
                                  "deneyin"))
        alinan = bas
    else:
        with yanit:
            bas = _yanit_baslangici(yanit, bas, beklenen_bayt)
            if not bas:
                hasher = hashlib.sha256()
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
    dogrulandi: bool = False     # katalogdaki sha256 ile dogrulandi (False: yalniz boyut)


def dogrulama_etiketi(kurulum: "Kurulum") -> str:
    """sha256 dogrulanmadiysa kullaniciya gosterilen etiket, yoksa ""."""
    if kurulum.dogrulandi:
        return ""
    return _("sha256 yok: yalnız boyut denetlendi (openmc.org sha256 yayımlamıyor)")


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
             "sha256": sha, "sha256_dogrulandi": bool(oge.sha256),
             "indirme": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "katalog_kaynagi": katalog_yukle().kaynak.get("sayfa")}
    with open(os.path.join(dizin, MAKBUZ), "w", encoding="utf-8") as f:
        json.dump(kayit, f, ensure_ascii=False, indent=1)


def _makbuz(dizin: str) -> dict:
    try:
        with open(os.path.join(dizin, MAKBUZ), encoding="utf-8") as f:
            veri = json.load(f)
        return veri if isinstance(veri, dict) else {}
    except (OSError, ValueError):
        _log.info("makbuz okunamadi: %s", dizin)
        return {}


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
        makbuz = _makbuz(dizin)
        return Kurulum(xml, makbuz.get("sha256"), atlandi=True,
                       dogrulandi=bool(makbuz.get("sha256_dogrulandi")))
    if os.path.lexists(dizin):
        raise veri_arsiv.ArsivHatasi(_("%s var ama içinde cross_sections.xml yok; klasörü "
                                       "taşıyın ya da başka hedef seçin") % dizin)
    veri_arsiv.disk_denetle(hedef, gereken_alan(oge, oran, hedef), kullanim)
    indirme = veri_arsiv.guvenli_dizin(os.path.join(hedef, INDIRME_DIZINI), _INDIRME_MODU)
    arsiv = os.path.join(indirme, oge.kimlik + ".tar.xz")
    sha = dosya_indir(oge.url, arsiv, oge.bayt, oge.sha256, politika,
                      _asama(ilerleme, "indirme"), iptal)
    tahmin = acik_tahmini(oge, oran)
    try:
        xml = veri_arsiv.arsiv_ac(arsiv, hedef, oge.dizin_adi, int(tahmin * BOMBA_CARPANI),
                                  iptal=iptal, ilerleme=_asama(ilerleme, "acma"),
                                  tahmini=tahmin, kullanim=kullanim)
    except veri_arsiv.BozukArsiv as e:
        _sil(arsiv)                 # ayni bozuk dosya her denemede yeniden acilmasin
        raise veri_arsiv.ArsivHatasi(_("%s — arşiv silindi; yeniden indirin") % e) from e
    _makbuz_yaz(dizin, oge, sha)
    _sil(arsiv)
    return Kurulum(xml, sha, dogrulandi=bool(oge.sha256))


def zincir_kur(oge: Oge, hedef_dizin: str, politika: Optional[UrlPolitikasi] = None,
               ilerleme: Asamali = None, iptal=None, kullanim=shutil.disk_usage) -> Kurulum:
    """Zinciri <hedef>/chain/<dosya_adi> olarak indirir (sha256 biliniyorsa dogrulanir)."""
    hedef = veri_arsiv.hedef_dogrula(hedef_dizin)
    dizin = veri_arsiv.guvenli_dizin(os.path.join(hedef, ZINCIR_DIZINI), _ZINCIR_MODU)
    yol = os.path.join(dizin, oge.dosya_adi)
    veri_arsiv.disk_denetle(hedef, gereken_alan(oge, 1.0, hedef), kullanim)
    sha = dosya_indir(oge.url, yol, oge.bayt, oge.sha256, politika,
                      _asama(ilerleme, "indirme"), iptal)
    return Kurulum(yol, sha, dogrulandi=bool(oge.sha256))


# ---------------------------------------------------------------------------
# komut satiri: cekirdek/veri_indir_komut.py (dosya boyu)
# ---------------------------------------------------------------------------

def main(argv=None, katalog: Optional[Katalog] = None,
         politika: Optional[UrlPolitikasi] = None) -> int:
    """Komut satiri (veri_indir_komut.main); cikis 0/1/2."""
    from cekirdek import veri_indir_komut
    return veri_indir_komut.main(argv, katalog=katalog, politika=politika)


if __name__ == "__main__":
    sys.exit(main())
