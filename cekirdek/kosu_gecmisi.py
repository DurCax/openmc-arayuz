# -*- coding: utf-8 -*-
"""
================================================================================
 kosu_gecmisi.py  --  Kosu gecmisi (SQLite) ve iki kosunun karsilastirilmasi (Y10)
================================================================================

 GECMIS
   Varsayilan dosya: yollar.kullanici_veri_dizini()/kosu_gecmisi.sqlite3
   (~/.local/share/openmc_arayuz/...). Yalniz standart kutuphane (sqlite3).
   Her yazma tek bir islemdir (transaction): yarim kayit kalmaz; ayni anda
   yazan isci iplikleri her islemde kendi baglantisini acar (sqlite3
   baglantilari iplikler arasi paylasilmaz).

     depo = GecmisDeposu()                  # ya da GecmisDeposu("/yol/gecmis.sqlite3")
     kuyruk.dinleyici_ekle(gecmis_dinleyicisi(depo))   # son asamadaki isleri yazar
     depo.listele(sinir=50) -> [KosuKaydi]  # en yeni once
     depo.getir(kimlik) -> KosuKaydi | None ; depo.sil(kimlik)

 KARSILASTIRMA
   k_farki(k1, s1, k2, s2) -> KFarki
     Delta = k2 - k1,  sigma = sqrt(s1^2 + s2^2),  z = Delta / sigma
     |z| > ANLAMLILIK_ESIGI (2; ~%95, projenin 2 sigma yontemi) ise fark
     istatistiksel olarak anlamlidir. Varsayim: iki kosu BAGIMSIZ. Ayni tohumla
     kosulan iki model korelasyonludur; o zaman gercek sigma daha kucuktur ve
     bu z MUHAFAZAKARDIR (tarama.py'deki notla ayni).
     Reaktivite farki: Delta rho = (1/k1 - 1/k2) * 1e5 pcm, sigma_rho =
     1e5 * sqrt((s1/k1^2)^2 + (s2/k2^2)^2).
   guc_farki(bagil1, bagil2) -> GucFarki
     Girdi: guc.tepe_faktorleri(...)["bagil"] sozlukleri {konum: (deger, sigma)}
     (K3'un guc.pin_tablosu() ana dala girince ayni anahtarlarla beslenebilir).
     Her ortak konumda Delta, sigma, z; yalniz birinde olan konumlar ayrica
     listelenir. N pinde |z| > 2 olan konum sayisi tesadufen ~%4.6 N beklenir
     (normal dagilim); `beklenen_tesaduf` bunu verir -- tek bir "anlamli" pin
     bir fark kaniti degildir.
   kosulari_karsilastir(dizin1, dizin2) -> Karsilastirma
     Iki kosu dizininin son statepoint'ini kosucu.sonuc_oku ile okur.
================================================================================
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import time
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, Hashable, Iterator, List, Mapping, Optional, Tuple

from cekirdek import kosucu
from cekirdek import yollar
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

GECMIS_DOSYASI = "kosu_gecmisi.sqlite3"
SEMA_SURUMU = 1
ANLAMLILIK_ESIGI = 2.0                # sigma; ~%95 iki yanli (proje yontemi: 2 sigma)
# P(|Z| > 2) standart normalde: erfc(2 / sqrt 2) = 0.0455
TESADUF_ORANI = math.erfc(ANLAMLILIK_ESIGI / math.sqrt(2.0))
PCM = 1.0e5
_BAGLANTI_SURESI = 10.0               # s; kilitli veritabaninda bekleme
_VARSAYILAN_SINIR = 200

_SEMA = """
CREATE TABLE IF NOT EXISTS kosular (
    kimlik       TEXT PRIMARY KEY,
    ad           TEXT NOT NULL,
    dizin        TEXT NOT NULL,
    durum        TEXT NOT NULL,
    baslangic    REAL,
    bitis        REAL,
    keff         REAL,
    sapma        REAL,
    is_parcacigi INTEGER,
    mpi_surec    INTEGER,
    spec_sha     TEXT,
    statepoint   TEXT,
    hata         TEXT,
    etiket       TEXT,
    kayit_ani    REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS kosular_bitis ON kosular (kayit_ani);
"""
_SUTUNLAR = ("kimlik", "ad", "dizin", "durum", "baslangic", "bitis", "keff", "sapma",
             "is_parcacigi", "mpi_surec", "spec_sha", "statepoint", "hata", "etiket",
             "kayit_ani")


@dataclass(frozen=True)
class KosuKaydi:
    """Gecmisteki tek kosu."""
    kimlik: str
    ad: str
    dizin: str
    durum: str
    baslangic: Optional[float] = None
    bitis: Optional[float] = None
    keff: Optional[float] = None
    sapma: Optional[float] = None
    is_parcacigi: int = 1
    mpi_surec: int = 0
    spec_sha: Optional[str] = None
    statepoint: Optional[str] = None
    hata: Optional[str] = None
    etiket: Mapping[str, Any] = field(default_factory=dict)
    kayit_ani: float = 0.0

    @property
    def sure(self) -> Optional[float]:
        if self.baslangic is None or self.bitis is None:
            return None
        return self.bitis - self.baslangic


def varsayilan_yol(ortam: Optional[Mapping[str, str]] = None) -> str:
    return os.path.join(yollar.kullanici_veri_dizini(ortam), GECMIS_DOSYASI)


def _etiket_json(etiket: Mapping[str, Any]) -> str:
    # JSON'a cevrilemeyen deger (nesne) metne indirgenir: kayit yine yazilir
    return json.dumps(dict(etiket or {}), ensure_ascii=False, default=str, sort_keys=True)


class GecmisDeposu:
    """SQLite kosu gecmisi (API: modul belgesi)."""

    def __init__(self, yol: Optional[str] = None) -> None:
        self.yol = os.path.abspath(yol or varsayilan_yol())
        os.makedirs(os.path.dirname(self.yol), exist_ok=True)
        with self._islem() as bag:
            surum = bag.execute("PRAGMA user_version").fetchone()[0]
            if surum > SEMA_SURUMU:
                raise RuntimeError(_("kosu gecmisi daha yeni bir sürümle yazılmış (%d > %d): %s")
                                   % (surum, SEMA_SURUMU, self.yol))
            bag.executescript(_SEMA)
            bag.execute("PRAGMA user_version = %d" % SEMA_SURUMU)

    @contextmanager
    def _islem(self) -> Iterator[sqlite3.Connection]:
        """Tek islem: basarida commit, istisnada rollback; baglanti kapanir."""
        with closing(sqlite3.connect(self.yol, timeout=_BAGLANTI_SURESI)) as bag:
            with bag:
                yield bag

    def kaydet(self, kayit: KosuKaydi) -> KosuKaydi:
        """Kaydi yazar (ayni kimlik varsa yerine koyar). DONER yazilan kayit."""
        if not kayit.kimlik or not kayit.ad:
            raise ValueError(_("kayıt kimliği ve adı boş olamaz"))
        yazilan = kayit if kayit.kayit_ani else _yenile(kayit, kayit_ani=time.time())
        degerler = [getattr(yazilan, s) for s in _SUTUNLAR]
        degerler[_SUTUNLAR.index("etiket")] = _etiket_json(yazilan.etiket)
        with self._islem() as bag:
            bag.execute("INSERT OR REPLACE INTO kosular (%s) VALUES (%s)"
                        % (", ".join(_SUTUNLAR), ", ".join("?" * len(_SUTUNLAR))), degerler)
        return yazilan

    def getir(self, kimlik: str) -> Optional[KosuKaydi]:
        with self._islem() as bag:
            satir = bag.execute("SELECT %s FROM kosular WHERE kimlik = ?" % ", ".join(_SUTUNLAR),
                                (kimlik,)).fetchone()
        return _satirdan(satir) if satir else None

    def listele(self, sinir: int = _VARSAYILAN_SINIR) -> List[KosuKaydi]:
        """En yeni kayit once."""
        with self._islem() as bag:
            satirlar = bag.execute("SELECT %s FROM kosular ORDER BY kayit_ani DESC LIMIT ?"
                                   % ", ".join(_SUTUNLAR), (int(sinir),)).fetchall()
        return [_satirdan(s) for s in satirlar]

    def sil(self, kimlik: str) -> bool:
        """Kaydi siler (kosu dizinine DOKUNMAZ). DONER True: silindi."""
        with self._islem() as bag:
            return bag.execute("DELETE FROM kosular WHERE kimlik = ?", (kimlik,)).rowcount > 0


def _yenile(kayit: KosuKaydi, **alanlar: Any) -> KosuKaydi:
    return KosuKaydi(**{**asdict(kayit), **alanlar})


def _satirdan(satir: Tuple[Any, ...]) -> KosuKaydi:
    alanlar = dict(zip(_SUTUNLAR, satir))
    try:
        alanlar["etiket"] = json.loads(alanlar["etiket"] or "{}")
    except ValueError:
        _log.warning("kosu gecmisi etiketi bozuk (%s); bos sayildi", alanlar["kimlik"])
        alanlar["etiket"] = {}
    alanlar["is_parcacigi"] = int(alanlar["is_parcacigi"] or 1)
    alanlar["mpi_surec"] = int(alanlar["mpi_surec"] or 0)
    return KosuKaydi(**alanlar)


def _spec_sha(dizin: str) -> Optional[str]:
    """Kosu dizinindeki kapsul.json'dan spec karmasi; yoksa None."""
    from cekirdek import kapsul
    yol = os.path.join(dizin, kapsul.KAPSUL_ADI)
    if not os.path.isfile(yol):
        return None
    try:
        with open(yol, encoding="utf-8") as f:
            return (json.load(f).get("spec") or {}).get("sha256")
    except (OSError, ValueError):
        _log.warning("kapsul okunamadi: %s", yol, exc_info=True)
        return None


def durumdan_kayit(durum: Any) -> KosuKaydi:
    """kuyruk.IsDurumu -> KosuKaydi (k varsa keff/sapma)."""
    k = durum.k or (None, None)
    return KosuKaydi(
        kimlik=durum.kimlik, ad=durum.ad, dizin=durum.dizin, durum=durum.asama.value,
        baslangic=durum.baslangic, bitis=durum.bitis, keff=k[0], sapma=k[1],
        is_parcacigi=durum.is_parcacigi, mpi_surec=durum.mpi_surec,
        spec_sha=_spec_sha(durum.dizin), statepoint=durum.statepoint, hata=durum.hata,
        etiket=dict(durum.etiket or {}))


def gecmis_dinleyicisi(depo: GecmisDeposu) -> Callable[[Any], None]:
    """Kuyruk dinleyicisi: son asamaya gelen her isi gecmise yazar."""
    def dinle(durum: Any) -> None:
        if durum.bitti_mi:
            depo.kaydet(durumdan_kayit(durum))
    return dinle


# ============================================================================
# KARSILASTIRMA
# ============================================================================

@dataclass(frozen=True)
class KFarki:
    k1: float
    s1: float
    k2: float
    s2: float
    fark: float
    sigma: float
    z: float
    anlamli: bool
    rho_fark_pcm: float
    rho_sigma_pcm: float


def k_farki(k1: float, s1: float, k2: float, s2: float,
            esik: float = ANLAMLILIK_ESIGI) -> KFarki:
    """Iki k +- sigma'nin farki ve anlamliligi (formuller: modul belgesi)."""
    if k1 <= 0 or k2 <= 0 or s1 < 0 or s2 < 0:
        raise ValueError(_("k > 0 ve σ ≥ 0 olmalı"))
    fark = k2 - k1
    sigma = math.hypot(s1, s2)
    if sigma > 0:
        z = fark / sigma
    else:
        z = 0.0 if fark == 0 else math.copysign(math.inf, fark)
    rho = (1.0 / k1 - 1.0 / k2) * PCM
    rho_s = PCM * math.hypot(s1 / k1 ** 2, s2 / k2 ** 2)
    return KFarki(k1, s1, k2, s2, fark, sigma, z, abs(z) > esik, rho, rho_s)


@dataclass(frozen=True)
class KonumFarki:
    deger1: float
    deger2: float
    fark: float
    sigma: float
    z: float


@dataclass(frozen=True)
class GucFarki:
    farklar: Mapping[Hashable, KonumFarki]
    yalniz1: Tuple[Hashable, ...]
    yalniz2: Tuple[Hashable, ...]
    anlamli_sayisi: int
    beklenen_tesaduf: float
    en_buyuk: Optional[Hashable]
    rms_fark: float


def _z(fark: float, sigma: float) -> float:
    if sigma > 0:
        return fark / sigma
    return 0.0 if fark == 0 else math.copysign(math.inf, fark)


def guc_farki(bagil1: Mapping[Hashable, Tuple[float, float]],
              bagil2: Mapping[Hashable, Tuple[float, float]],
              esik: float = ANLAMLILIK_ESIGI) -> GucFarki:
    """Konum konum bagil guc farki (2 - 1); bkz. modul belgesi."""
    ortak = [a for a in bagil1 if a in bagil2]
    farklar: Dict[Hashable, KonumFarki] = {}
    for a in ortak:
        (d1, s1), (d2, s2) = bagil1[a], bagil2[a]
        fark, sigma = float(d2) - float(d1), math.hypot(float(s1), float(s2))
        farklar[a] = KonumFarki(float(d1), float(d2), fark, sigma, _z(fark, sigma))
    anlamli = sum(1 for f in farklar.values() if abs(f.z) > esik)
    en_buyuk = max(farklar, key=lambda a: abs(farklar[a].fark)) if farklar else None
    rms = math.sqrt(sum(f.fark ** 2 for f in farklar.values()) / len(farklar)) if farklar else 0.0
    return GucFarki(
        farklar=farklar,
        yalniz1=tuple(a for a in bagil1 if a not in bagil2),
        yalniz2=tuple(a for a in bagil2 if a not in bagil1),
        anlamli_sayisi=anlamli, beklenen_tesaduf=TESADUF_ORANI * len(farklar),
        en_buyuk=en_buyuk, rms_fark=rms)


@dataclass(frozen=True)
class Karsilastirma:
    dizin1: str
    dizin2: str
    k: Optional[KFarki]
    guc: Optional[GucFarki]
    notlar: Tuple[str, ...] = ()


def _bagil(sonuc: Mapping[str, Any]) -> Optional[Mapping[Hashable, Tuple[float, float]]]:
    faktorler = (sonuc.get("guc") or {}).get("faktorler") or {}
    return faktorler.get("bagil")


def _oku(dizin: str, okuyucu: Callable[[str], Mapping[str, Any]]) -> Mapping[str, Any]:
    sp = kosucu.son_statepoint(dizin)
    if sp is None:
        raise FileNotFoundError(_("statepoint bulunamadı: %s") % dizin)
    return okuyucu(sp)


def kosulari_karsilastir(dizin1: str, dizin2: str,
                         okuyucu: Callable[[str], Mapping[str, Any]] = kosucu.sonuc_oku
                         ) -> Karsilastirma:
    """Iki kosu dizinini karsilastirir (k ve varsa bagil pin gucu)."""
    s1, s2 = _oku(dizin1, okuyucu), _oku(dizin2, okuyucu)
    notlar: List[str] = []
    k = None
    if s1.get("keff") and s2.get("keff"):
        k = k_farki(*s1["keff"], *s2["keff"])
    else:
        notlar.append(_("En az bir koşu sabit kaynak: k-eff karşılaştırılmadı."))
    b1, b2 = _bagil(s1), _bagil(s2)
    guc = guc_farki(b1, b2) if b1 and b2 else None
    if guc is None:
        notlar.append(_("İki koşuda da güç dağılımı yok: pin gücü karşılaştırılmadı."))
    elif not guc.farklar:
        notlar.append(_("Güç haritalarında ortak konum yok (farklı geometri?)."))
    return Karsilastirma(os.path.abspath(dizin1), os.path.abspath(dizin2), k, guc,
                         tuple(notlar))
