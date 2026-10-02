# -*- coding: utf-8 -*-
"""
================================================================================
 kuyruk.py  --  Kosu kuyrugu (v3 Y10): sirali / sinirli paralel openmc kosulari
================================================================================

 Qt'den BAGIMSIZDIR (yalniz standart kutuphane + cekirdek). Arayuz tarafi
 arayuz/kuyruk/bagdastirici.py'deki ince QObject ile sarar; terminalden ve
 baska cekirdek modullerinden (K4 demet k-inf sihirbazi, parametrik tarama)
 dogrudan kullanilir. Kosu hazirligi kosucu.py'deki islevlerle AYNIDIR
 (dizin_hazirla, xml_yaz, cevrim_satiri, son_statepoint, sonuc_oku); burada
 yalniz zamanlama, iptal ve durum bildirimi eklenir.

 KULLANIM
   from cekirdek import kuyruk
   k = kuyruk.Kuyruk(en_fazla_paralel=2, is_parcacigi_butcesi=12)
   k.dinleyici_ekle(lambda d: print(d.ad, d.asama.value, d.cevrim, d.k))
   kimlik = k.ekle(kuyruk.KosuIsi(
       ad="UO2 3.1%", spec=spec, is_parcacigi=6,
       dizin=kuyruk.ayri_dizin("/tmp/kinf", "UO2 3.1%"),
       etiket={"demet": "UO2"},                     # cagirana ait; aynen tasinir
       sonuc_kancasi=None))                         # None: kosucu.sonuc_oku
   k.baslat()                    # bekleyenler sirayla / sinirli paralel baslar
   k.bekle(zaman_asimi=None)     # True: hepsi son asamada (BITTI/BASARISIZ/IPTAL)
   d = k.durum(kimlik)           # IsDurumu (degismez anlik goruntu)
   d.asama, d.k, d.sonuc, d.hata, d.dizin, d.statepoint
   k.kapat()                     # yeni is baslatmaz, kosanlari iptal eder

 API OZETI
   KosuIsi (frozen)   ad, dizin, spec (None: dizinde model.xml hazir),
                      is_parcacigi (OMP_NUM_THREADS ve `openmc -s`),
                      mpi_surec (>1 ise `mpiexec -n N openmc ...`), dogrulama,
                      veri_kontrolu, sonuc_kancasi, ortam (ek ortam degiskeni),
                      etiket (cagirana ait sozluk). maliyet = is_parcacigi x
                      max(1, mpi_surec) -- butceden duser.
   Asama              BEKLIYOR -> KOSUYOR -> BITTI | BASARISIZ | IPTAL
   IsDurumu (frozen)  kimlik, ad, dizin, asama, cevrim, toplam_cevrim, k
                      (kosu sirasinda canli ortalama; bitince sonuc_kancasi'nin
                      "keff"i), sonuc (kancanin dondurdugu), hata, cikis_kodu,
                      statepoint, baslangic / bitis (time.time), etiket.
   Kuyruk             ekle(is) -> kimlik; tasi(kimlik, sira); iptal(kimlik);
                      kaldir(kimlik) (yalniz son asamadaki ya da bekleyen);
                      baslat(); duraklat() (kosanlar surer, yenisi baslamaz);
                      bekle(zaman_asimi) -> bool; durum(kimlik); durumlar()
                      (kuyruk sirasiyla); tamamlandi_mi(); dinleyici_ekle(f) /
                      dinleyici_cikar(f); kapat().
   sonuc_kancasi      f(statepoint_yolu, KosuIsi) -> herhangi bir deger.
                      Mapping dondurur ve "keff" = (k, sigma) icerirse
                      IsDurumu.k bundan alinir. Istisna -> BASARISIZ (hata metni).
   Yardimcilar        ayri_dizin(kok, ad, alinmis=()), komut_olustur(...),
                      mpiexec_yolu(ortam, python), mpi_destegi(openmc_yolu),
                      varsayilan_sonuc_okuyucu(statepoint, is_).

 ZAMANLAMA
   Sira kesindir (FIFO; tasi ile degisir): siradaki is butceye ya da paralel
   sinirina sigmiyorsa ARKASINDAKI baslatilmaz (kucuk isler buyugu
   asmaz). en_fazla_paralel=1 tam sirali kuyruktur. is_parcacigi_butcesi
   varsayilani os.cpu_count(); tek basina butceyi asan is ekle()'de reddedilir.
   Her is AYRI dizinde kosar: bitmemis iki is ayni dizini paylasamaz.

 IPLIKLER VE BILDIRIM
   Her kosu kendi is parcaciginda (threading) alt surec olarak kosar; alt
   surec liste argumanla baslar (shell yok) ve kendi oturumunda (yeni surec
   grubu) calisir -- iptal SIGTERM'i mpiexec'in cocuklarina da ulastirir,
   IPTAL_SURESI sonra SIGKILL. Dinleyiciler kilit DISINDA ve cagri yapan
   iplikte (cogunlukla isci) cagrilir; Qt bagdastiricisi sinyalle ana iplige
   tasir. Dinleyici istisnasi loglanir, kuyrugu durdurmaz.

 MPI
   mpiexec_yolu(): $OPENMC_ARAYUZ_MPIEXEC (mutlak olmali) > python'un yanindaki
   bin/mpiexec > PATH'in MUTLAK ogeleri (bos/"."/goreli oge CWD'yi aratirdi)
   > $CONDA_PREFIX/bin -- yollar.openmc_ikilisi ile ayni guvenli kalip.
   mpi_destegi(): `openmc --version` ciktisindaki "MPI enabled: yes|no";
   desteksiz ikiliyle MPI isi acik hatayla BASARISIZ olur (sessizce tek
   surecte kosmaz).
================================================================================
"""

from __future__ import annotations

import copy
import dataclasses
import enum
import os
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator, List, Mapping, Optional, Tuple

from cekirdek import kosucu
from cekirdek import yollar
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

MPIEXEC_ORTAM_DEGISKENI = "OPENMC_ARAYUZ_MPIEXEC"
MPIEXEC_ADI = "mpiexec"
LOG_ADI = "kosu.log"                 # kosucu.calistir ve arayuz ile ayni ad
IPTAL_SURESI = 5.0                   # s; SIGTERM'den sonra SIGKILL'e kadar
SURUM_SURESI = 15.0                  # s; `openmc --version` ust siniri
_KAPAT_SURESI = 10.0                 # s; kapat() iscileri bu kadar bekler
_AD_SINIRI = 60                      # ayri_dizin: dizin adinin en uzun hali
_MPI_DESEN = re.compile(r"MPI enabled:\s*(yes|no)", re.IGNORECASE)

Ortam = Optional[Mapping[str, str]]


class Asama(str, enum.Enum):
    """Isin yasam dongusu. Son asamalar: BITTI, BASARISIZ, IPTAL."""
    BEKLIYOR = "bekliyor"
    KOSUYOR = "kosuyor"
    BITTI = "bitti"
    BASARISIZ = "basarisiz"
    IPTAL = "iptal"


SON_ASAMALAR = frozenset({Asama.BITTI, Asama.BASARISIZ, Asama.IPTAL})


class KuyrukHatasi(RuntimeError):
    """Kosu hazirlanamadi / baslatilamadi (metin kullaniciya gosterilir)."""


class _Iptal(Exception):
    """Hazirlik sirasinda iptal istendi (ic denetim akisi)."""


SonucKancasi = Callable[[str, "KosuIsi"], Any]


@dataclass(frozen=True)
class KosuIsi:
    """Kuyruga eklenecek tek kosu (tanim; durumu IsDurumu tasir)."""
    ad: str
    dizin: str
    spec: Optional[Mapping[str, Any]] = None
    is_parcacigi: int = 1
    mpi_surec: int = 0
    dogrulama: bool = True
    veri_kontrolu: bool = True
    sonuc_kancasi: Optional[SonucKancasi] = None
    ortam: Mapping[str, str] = field(default_factory=dict)
    etiket: Mapping[str, Any] = field(default_factory=dict)

    @property
    def maliyet(self) -> int:
        """Butceden dusen is parcacigi sayisi."""
        return int(self.is_parcacigi) * max(1, int(self.mpi_surec))


@dataclass(frozen=True)
class IsDurumu:
    """Bir isin degismez anlik durumu (dinleyicilere bu gider)."""
    kimlik: str
    ad: str
    dizin: str
    asama: Asama = Asama.BEKLIYOR
    is_parcacigi: int = 1
    mpi_surec: int = 0
    cevrim: int = 0
    toplam_cevrim: Optional[int] = None
    k: Optional[Tuple[float, float]] = None
    sonuc: Any = None
    hata: Optional[str] = None
    cikis_kodu: Optional[int] = None
    statepoint: Optional[str] = None
    baslangic: Optional[float] = None
    bitis: Optional[float] = None
    etiket: Mapping[str, Any] = field(default_factory=dict)

    @property
    def bitti_mi(self) -> bool:
        return self.asama in SON_ASAMALAR


# ============================================================================
# YARDIMCILAR
# ============================================================================

def ayri_dizin(kok: str, ad: str, alinmis: Iterable[str] = ()) -> str:
    """kok altinda ad'dan turetilmis, VAR OLMAYAN ve alinmis'ta bulunmayan
    bir kosu dizini yolu (olusturmaz). Ad guvenli karakterlere indirgenir."""
    temiz = re.sub(r"[^\w.-]+", "_", str(ad), flags=re.UNICODE).strip("._")
    temiz = temiz[:_AD_SINIRI] or "kosu"
    kok = os.path.abspath(kok)
    alinan = {os.path.abspath(a) for a in alinmis}
    aday, n = os.path.join(kok, temiz), 1
    while os.path.exists(aday) or aday in alinan:
        n += 1
        aday = os.path.join(kok, "%s_%d" % (temiz, n))
    return aday


def komut_olustur(openmc: str, is_parcacigi: int, mpi_surec: int = 0,
                  mpiexec: Optional[str] = None) -> List[str]:
    """openmc komutu (liste; shell yok). mpi_surec > 1 ise mpiexec ile."""
    komut = [openmc, "-s", str(int(is_parcacigi))]
    if int(mpi_surec) <= 1:
        return komut
    if not mpiexec:
        raise KuyrukHatasi(_("MPI koşusu için mpiexec bulunamadı (OPENMC_ARAYUZ_MPIEXEC "
                             "ya da PATH)"))
    return [mpiexec, "-n", str(int(mpi_surec))] + komut


def _calistirilabilir_mi(yol: str) -> bool:
    return os.path.isfile(yol) and os.access(yol, os.X_OK)


def _mpiexec_adaylari(ortam: Mapping[str, str], python: str) -> Iterator[str]:
    deger = ortam.get(MPIEXEC_ORTAM_DEGISKENI)
    if deger:
        yol = os.path.expanduser(deger)
        if os.path.isabs(yol):
            yield yol
        else:
            _log.warning("%s=%s yok sayildi: mutlak yol olmali", MPIEXEC_ORTAM_DEGISKENI, deger)
    if os.path.isabs(python):
        yield os.path.join(os.path.dirname(python), MPIEXEC_ADI)
    for oge in ortam.get("PATH", "").split(os.pathsep):
        if oge and os.path.isabs(oge):            # bos / "." / goreli: CWD'yi aratirdi
            yield os.path.join(oge, MPIEXEC_ADI)
    onek = ortam.get("CONDA_PREFIX")
    if onek and os.path.isabs(onek):
        yield os.path.join(onek, "bin", MPIEXEC_ADI)


def mpiexec_yolu(ortam: Ortam = None, python: Optional[str] = None) -> Optional[str]:
    """mpiexec'in mutlak yolu ya da None (sira: modul belgesi, MPI)."""
    ortam = os.environ if ortam is None else ortam
    for aday in _mpiexec_adaylari(ortam, python or sys.executable):
        yol = os.path.normpath(aday)
        if _calistirilabilir_mi(yol):
            return yol
    return None


_MPI_ONBELLEK: dict = {}


def mpi_destegi(openmc: Optional[str]) -> Optional[bool]:
    """openmc MPI ile derlenmis mi: True / False; anlasilamazsa None."""
    if not openmc or not _calistirilabilir_mi(openmc):
        return None
    anahtar = (openmc, os.stat(openmc).st_mtime)
    if anahtar in _MPI_ONBELLEK:
        return _MPI_ONBELLEK[anahtar]
    try:
        cikti = subprocess.run([openmc, "--version"], capture_output=True, text=True,
                               timeout=SURUM_SURESI, check=False).stdout
    except (OSError, subprocess.TimeoutExpired):
        _log.warning("openmc --version calistirilamadi: %s", openmc, exc_info=True)
        return None
    m = _MPI_DESEN.search(cikti or "")
    destek = None if m is None else m.group(1).lower() == "yes"
    _MPI_ONBELLEK[anahtar] = destek
    return destek


def varsayilan_sonuc_okuyucu(statepoint: str, is_: KosuIsi) -> Any:
    """Varsayilan sonuc kancasi: kosucu.sonuc_oku (k-eff, tally, guc...)."""
    return kosucu.sonuc_oku(statepoint)


def _kancadan_k(sonuc: Any) -> Optional[Tuple[float, float]]:
    if isinstance(sonuc, Mapping) and sonuc.get("keff") is not None:
        k, s = sonuc["keff"]
        return float(k), float(s)
    return None


def _toplam_cevrim(spec: Optional[Mapping[str, Any]]) -> Optional[int]:
    if not spec:
        return None
    deger = (spec.get("ayarlar") or {}).get("cevrim")
    return int(deger) if deger else None


def _son_statepoint(dizin: str, baslangic: float) -> Optional[str]:
    """Bu kosunun statepoint'i: dizindeki en son cevrimli dosya, kosu
    baslangicindan ONCE yazilmissa (eski kosu artigi) None."""
    sp = kosucu.son_statepoint(dizin)
    if sp is None or os.path.getmtime(sp) < baslangic - 1.0:
        return None
    return sp


# ============================================================================
# KUYRUK
# ============================================================================

class Kuyruk:
    """Sirali / sinirli paralel kosu kuyrugu (API: modul belgesi)."""

    def __init__(self, en_fazla_paralel: int = 1, is_parcacigi_butcesi: Optional[int] = None,
                 openmc: Optional[str] = None, mpiexec: Optional[str] = None,
                 sonuc_kancasi: Optional[SonucKancasi] = None,
                 iptal_suresi: float = IPTAL_SURESI) -> None:
        if int(en_fazla_paralel) < 1:
            raise ValueError(_("en fazla paralel koşu sayısı en az 1 olmalı"))
        butce = int(is_parcacigi_butcesi or os.cpu_count() or 1)
        if butce < 1:
            raise ValueError(_("iş parçacığı bütçesi en az 1 olmalı"))
        self._paralel = int(en_fazla_paralel)
        self._butce = butce
        self._openmc = openmc
        self._mpiexec = mpiexec
        self._kanca = sonuc_kancasi
        self._iptal_suresi = float(iptal_suresi)
        self._kosul = threading.Condition()
        self._sira: List[str] = []
        self._isler: dict = {}
        self._durumlar: dict = {}
        self._surecler: dict = {}
        self._iptal_istenen: set = set()
        self._calisan: set = set()
        self._iplikler: dict = {}
        self._dinleyiciler: List[Callable[[IsDurumu], None]] = []
        self._etkin = False
        self._kapali = False
        self._bildirim = 0          # dinleyicilere henuz iletilmemis son asama olayi

    # ------------------------------------------------------------------
    # ozellikler
    # ------------------------------------------------------------------
    @property
    def en_fazla_paralel(self) -> int:
        return self._paralel

    @property
    def is_parcacigi_butcesi(self) -> int:
        return self._butce

    @property
    def etkin(self) -> bool:
        return self._etkin

    def sinirlari_ayarla(self, en_fazla_paralel: int, is_parcacigi_butcesi: int) -> None:
        """Paralellik ve butceyi degistirir (kosanlari etkilemez)."""
        if int(en_fazla_paralel) < 1 or int(is_parcacigi_butcesi) < 1:
            raise ValueError(_("paralel koşu sayısı ve bütçe en az 1 olmalı"))
        with self._kosul:
            self._paralel = int(en_fazla_paralel)
            self._butce = int(is_parcacigi_butcesi)
            olaylar = self._dagit()
        self._yay(olaylar)

    # ------------------------------------------------------------------
    # dinleyiciler
    # ------------------------------------------------------------------
    def dinleyici_ekle(self, dinleyici: Callable[[IsDurumu], None]) -> None:
        with self._kosul:
            self._dinleyiciler = self._dinleyiciler + [dinleyici]

    def dinleyici_cikar(self, dinleyici: Callable[[IsDurumu], None]) -> None:
        with self._kosul:
            self._dinleyiciler = [d for d in self._dinleyiciler if d is not dinleyici]

    def _yay(self, olaylar: Iterable[IsDurumu]) -> None:
        """Olaylari dinleyicilere iletir (kilit DISINDA cagrilmali)."""
        dinleyiciler = self._dinleyiciler
        for olay in olaylar:
            for d in dinleyiciler:
                try:
                    d(olay)
                except Exception:
                    _log.exception("kuyruk dinleyicisi hata verdi (%s)", olay.ad)

    # ------------------------------------------------------------------
    # is ekleme / sira
    # ------------------------------------------------------------------
    def _dogrula(self, is_: KosuIsi) -> KosuIsi:
        if not str(is_.ad or "").strip():
            raise ValueError(_("koşunun adı boş olamaz"))
        if not str(is_.dizin or "").strip():
            raise ValueError(_("koşu dizini boş olamaz"))
        if int(is_.is_parcacigi) < 1 or int(is_.mpi_surec) < 0:
            raise ValueError(_("iş parçacığı en az 1, MPI süreç sayısı negatif olamaz"))
        if is_.maliyet > self._butce:
            raise ValueError(_("'%s' %d iş parçacığı istiyor; bütçe %d")
                             % (is_.ad, is_.maliyet, self._butce))
        dizin = os.path.abspath(os.path.expanduser(is_.dizin))
        for d in self._durumlar.values():
            if d.dizin == dizin and not d.bitti_mi:
                raise ValueError(_("'%s' dizini zaten kuyruktaki bir koşunun (%s)")
                                 % (dizin, d.ad))
        return dataclasses.replace(
            is_, dizin=dizin, spec=copy.deepcopy(is_.spec) if is_.spec is not None else None,
            ortam=dict(is_.ortam), etiket=dict(is_.etiket))

    def ekle(self, is_: KosuIsi) -> str:
        """Isi kuyrugun sonuna ekler; DONER kimlik. Kuyruk etkinse baslayabilir."""
        with self._kosul:
            if self._kapali:
                raise RuntimeError(_("kuyruk kapatıldı"))
            is_ = self._dogrula(is_)
            kimlik = uuid.uuid4().hex[:12]
            self._isler[kimlik] = is_
            self._sira.append(kimlik)
            durum = IsDurumu(kimlik=kimlik, ad=is_.ad, dizin=is_.dizin,
                             is_parcacigi=int(is_.is_parcacigi), mpi_surec=int(is_.mpi_surec),
                             toplam_cevrim=_toplam_cevrim(is_.spec), etiket=is_.etiket)
            self._durumlar[kimlik] = durum
            olaylar = [durum] + self._dagit()
        self._yay(olaylar)
        return kimlik

    def _bul(self, kimlik: str) -> IsDurumu:
        if kimlik not in self._durumlar:
            raise KeyError(kimlik)
        return self._durumlar[kimlik]

    def tasi(self, kimlik: str, sira: int) -> None:
        """Isi kuyrukta `sira` konumuna tasir (0 = en on; sinirlara kirpilir)."""
        with self._kosul:
            durum = self._bul(kimlik)
            self._sira.remove(kimlik)
            sira = max(0, min(int(sira), len(self._sira)))
            self._sira.insert(sira, kimlik)
            olaylar = [durum] + self._dagit()
        self._yay(olaylar)

    def kaldir(self, kimlik: str) -> None:
        """Bekleyen ya da son asamadaki isi listeden cikarir (kosani iptal edin)."""
        with self._kosul:
            durum = self._bul(kimlik)
            if durum.asama == Asama.KOSUYOR:
                raise RuntimeError(_("koşan iş kaldırılamaz; önce iptal edin"))
            self._sira.remove(kimlik)
            del self._durumlar[kimlik]
            del self._isler[kimlik]
            self._kosul.notify_all()

    # ------------------------------------------------------------------
    # durum
    # ------------------------------------------------------------------
    def durum(self, kimlik: str) -> IsDurumu:
        with self._kosul:
            return self._bul(kimlik)

    def durumlar(self) -> List[IsDurumu]:
        """Butun islerin durumu, kuyruk sirasiyla."""
        with self._kosul:
            return [self._durumlar[k] for k in self._sira]

    def is_tanimi(self, kimlik: str) -> KosuIsi:
        with self._kosul:
            self._bul(kimlik)
            return self._isler[kimlik]

    def tamamlandi_mi(self) -> bool:
        """Butun isler son asamada mi (dinleyici icinden de dogru cevap verir)."""
        with self._kosul:
            return self._hepsi_son()

    def _hepsi_son(self) -> bool:
        return all(d.bitti_mi for d in self._durumlar.values()) and not self._calisan

    def _tamam(self) -> bool:
        # bekle() dinleyiciler son olayi ALDIKTAN sonra doner (gecmis kaydi vb.)
        return self._hepsi_son() and self._bildirim == 0

    def bekle(self, zaman_asimi: Optional[float] = None) -> bool:
        """Butun isler son asamaya gelene kadar bekler. DONER True: tamam."""
        with self._kosul:
            return self._kosul.wait_for(self._tamam, timeout=zaman_asimi)

    # ------------------------------------------------------------------
    # baslat / duraklat / iptal / kapat
    # ------------------------------------------------------------------
    def baslat(self) -> None:
        with self._kosul:
            if self._kapali:
                raise RuntimeError(_("kuyruk kapatıldı"))
            self._etkin = True
            olaylar = self._dagit()
        self._yay(olaylar)

    def duraklat(self) -> None:
        """Yeni is baslatilmaz; kosanlar surer."""
        with self._kosul:
            self._etkin = False

    def iptal(self, kimlik: str) -> None:
        """Bekleyen isi IPTAL eder; kosan isin surecini sonlandirir."""
        olaylar: List[IsDurumu] = []
        with self._kosul:
            durum = self._bul(kimlik)
            if durum.bitti_mi:
                return
            if durum.asama == Asama.BEKLIYOR:
                yeni = dataclasses.replace(durum, asama=Asama.IPTAL, bitis=time.time())
                self._durumlar[kimlik] = yeni
                olaylar = [yeni]
                self._bildirim += 1
            else:
                self._iptal_istenen.add(kimlik)
                surec = self._surecler.get(kimlik)
                if surec is not None:
                    self._sonlandir(surec)
        if olaylar:
            self._son_yay(olaylar)

    def kapat(self) -> None:
        """Yeni is alinmaz; bekleyenler ve kosanlar iptal edilir, isciler beklenir."""
        with self._kosul:
            self._kapali = True
            self._etkin = False
            kimlikler = list(self._sira)
            iplikler = list(self._iplikler.values())
        for kimlik in kimlikler:
            self.iptal(kimlik)
        for iplik in iplikler:
            iplik.join(_KAPAT_SURESI)

    def _sonlandir(self, surec: subprocess.Popen) -> None:
        """Surec grubuna SIGTERM; iptal_suresi sonra hala yasiyorsa SIGKILL."""
        def gonder(sinyal: int) -> None:
            if surec.poll() is not None:
                return
            try:
                os.killpg(surec.pid, sinyal)
            except (ProcessLookupError, PermissionError):
                _log.debug("surec grubu %d sinyal %d alamadi", surec.pid, sinyal)
        gonder(signal.SIGTERM)
        zamanlayici = threading.Timer(self._iptal_suresi, gonder, args=(signal.SIGKILL,))
        zamanlayici.daemon = True
        zamanlayici.start()

    # ------------------------------------------------------------------
    # zamanlama (kilit ICINDE cagrilir)
    # ------------------------------------------------------------------
    def _kullanilan(self) -> int:
        return sum(self._isler[k].maliyet for k in self._calisan)

    def _dagit(self) -> List[IsDurumu]:
        """Sigan bekleyen isleri sirayla baslatir. DONER yayilacak olaylar."""
        olaylar: List[IsDurumu] = []
        if not self._etkin or self._kapali:
            return olaylar
        for kimlik in self._sira:
            durum = self._durumlar[kimlik]
            if durum.asama != Asama.BEKLIYOR:
                continue
            is_ = self._isler[kimlik]
            if (len(self._calisan) >= self._paralel
                    or self._kullanilan() + is_.maliyet > self._butce):
                break                                   # FIFO: arkadaki one gecmez
            yeni = dataclasses.replace(durum, asama=Asama.KOSUYOR, baslangic=time.time())
            self._durumlar[kimlik] = yeni
            self._calisan.add(kimlik)
            olaylar.append(yeni)
            iplik = threading.Thread(target=self._isci, args=(kimlik,),
                                     name="kuyruk-%s" % kimlik, daemon=True)
            self._iplikler[kimlik] = iplik
            iplik.start()
        return olaylar

    def _guncelle(self, kimlik: str, **alanlar: Any) -> IsDurumu:
        with self._kosul:
            yeni = dataclasses.replace(self._durumlar[kimlik], **alanlar)
            self._durumlar[kimlik] = yeni
            return yeni

    # ------------------------------------------------------------------
    # isci (kendi is parcaciginda)
    # ------------------------------------------------------------------
    def _isci(self, kimlik: str) -> None:
        is_ = self._isler[kimlik]
        try:
            son = self._yurut(kimlik, is_)
        except _Iptal:
            son = {"asama": Asama.IPTAL}
        except Exception as e:
            _log.exception("kuyruk isi '%s' basarisiz", is_.ad)
            son = {"asama": Asama.BASARISIZ, "hata": str(e) or type(e).__name__}
        with self._kosul:
            yeni = dataclasses.replace(self._durumlar[kimlik], bitis=time.time(), **son)
            self._durumlar[kimlik] = yeni
            self._calisan.discard(kimlik)
            self._surecler.pop(kimlik, None)
            self._iptal_istenen.discard(kimlik)
            self._iplikler.pop(kimlik, None)
            olaylar = [yeni] + self._dagit()
            self._bildirim += 1
        self._son_yay(olaylar)

    def _son_yay(self, olaylar: List[IsDurumu]) -> None:
        """Son asama olayini yayar, SONRA bekleyenleri uyandirir."""
        try:
            self._yay(olaylar)
        finally:
            with self._kosul:
                self._bildirim -= 1
                self._kosul.notify_all()

    def _iptal_mi(self, kimlik: str) -> bool:
        with self._kosul:
            return kimlik in self._iptal_istenen

    def _yurut(self, kimlik: str, is_: KosuIsi) -> dict:
        """Hazirla, kos, sonucu oku. DONER son durum alanlari."""
        self._hazirla(is_)
        if self._iptal_mi(kimlik):
            raise _Iptal()
        komut = self._komut(is_)
        baslangic = time.time()
        kod = self._surec_kos(kimlik, is_, komut)
        if self._iptal_mi(kimlik):
            return {"asama": Asama.IPTAL, "cikis_kodu": kod}
        if kod != 0:
            return {"asama": Asama.BASARISIZ, "cikis_kodu": kod,
                    "hata": _("openmc çıkış kodu %d (günlük: %s)")
                    % (kod, os.path.join(is_.dizin, LOG_ADI))}
        sp = _son_statepoint(is_.dizin, baslangic)
        if sp is None:
            return {"asama": Asama.BASARISIZ, "cikis_kodu": kod,
                    "hata": _("koşu bitti ama statepoint dosyası bulunamadı")}
        kanca = is_.sonuc_kancasi or self._kanca or varsayilan_sonuc_okuyucu
        sonuc = kanca(sp, is_)
        alanlar = {"asama": Asama.BITTI, "cikis_kodu": kod, "statepoint": sp, "sonuc": sonuc}
        k = _kancadan_k(sonuc)
        if k is not None:
            alanlar["k"] = k
        return alanlar

    def _hazirla(self, is_: KosuIsi) -> None:
        """Spec'li is: dogrula + temiz dizin + model.xml/spec.json/kapsul.
        Spec'siz is: dizinde model.xml (ya da settings.xml) olmali."""
        if is_.spec is None:
            if not any(os.path.isfile(os.path.join(is_.dizin, ad))
                       for ad in ("model.xml", "settings.xml")):
                raise KuyrukHatasi(_("'%s' dizininde model.xml yok") % is_.dizin)
            return
        if is_.dogrulama:
            from cekirdek import dogrula
            dogrula.kapi(is_.spec, veri_kontrolu=is_.veri_kontrolu)
        kosucu.dizin_hazirla(is_.dizin, temizle=True)
        kosucu.xml_yaz(is_.spec, is_.dizin, is_parcacigi=int(is_.is_parcacigi))

    def _komut(self, is_: KosuIsi) -> List[str]:
        exe = self._openmc or yollar.openmc_ikilisi()
        if not exe or not _calistirilabilir_mi(exe):
            raise KuyrukHatasi(_("openmc çalıştırılabilir dosyası bulunamadı (%s)")
                               % (exe or "PATH"))
        if int(is_.mpi_surec) <= 1:
            return komut_olustur(exe, is_.is_parcacigi)
        if mpi_destegi(exe) is False:
            raise KuyrukHatasi(_("Bu openmc MPI desteksiz derlenmiş (MPI enabled: no); "
                                 "MPI süreç sayısını 0 yapın"))
        mpiexec = self._mpiexec or mpiexec_yolu()
        return komut_olustur(exe, is_.is_parcacigi, is_.mpi_surec, mpiexec)

    def _surec_ortami(self, is_: KosuIsi) -> dict:
        ortam = dict(os.environ)
        ortam.update({str(a): str(d) for a, d in is_.ortam.items()})
        ortam["OMP_NUM_THREADS"] = str(int(is_.is_parcacigi))
        return ortam

    def _surec_kos(self, kimlik: str, is_: KosuIsi, komut: List[str]) -> int:
        """Alt sureci kosar, ciktiyi kosu.log'a yazar, ilerlemeyi bildirir."""
        os.makedirs(is_.dizin, exist_ok=True)
        with open(os.path.join(is_.dizin, LOG_ADI), "w", encoding="utf-8") as log:
            log.write("# komut: %s\n# dizin: %s\n\n" % (" ".join(komut), is_.dizin))
            surec = subprocess.Popen(komut, cwd=is_.dizin, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, bufsize=1,
                                     env=self._surec_ortami(is_), start_new_session=True)
            with self._kosul:
                self._surecler[kimlik] = surec
                if kimlik in self._iptal_istenen:
                    self._sonlandir(surec)
            with surec.stdout:
                for satir in surec.stdout:
                    log.write(satir)
                    self._satir_isle(kimlik, satir.rstrip("\n"))
            return surec.wait()

    def _satir_isle(self, kimlik: str, satir: str) -> None:
        bilgi = kosucu.cevrim_satiri(satir)
        if bilgi is not None:
            alanlar = {"cevrim": bilgi["cevrim"]}
            if bilgi["ortalama"] is not None:
                alanlar["k"] = (bilgi["ortalama"], bilgi["sapma"])
        else:
            n = kosucu.sabit_kaynak_cevrimi(satir)
            if n is None:
                return
            alanlar = {"cevrim": n}
        self._yay([self._guncelle(kimlik, **alanlar)])
