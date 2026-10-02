# -*- coding: utf-8 -*-
"""
kuyruk_surec.py -- kosu kuyrugunun alt surec yasam dongusu (Y10; kuyruk.py'den ayrildi).

  grup = SurecGrubu(komut, cwd, ortam)     # liste arguman, shell yok, YENI oturum
  for satir in grup.satirlar(): ...        # metin; bozuk bayt "?" olur (errors=replace)
  kod = grup.bekle()
  grup.sonlandir(iptal_suresi)             # SIGTERM gruba; iptal_suresi sonra SIGKILL
  grup.kapat(iptal_suresi)                 # finally'de: grupta yasayan kalmaz, lider toplanir

KURALLAR
  * Her kosu kendi surec grubundadir (start_new_session): sinyal mpiexec'in
    rank'larina ve openmc'nin cocuklarina da gider.
  * SIGKILL `poll()` kapisi OLMADAN gruba gonderilir: lider cikmis ama boruyu
    tutan torun (mpiexec rank'i) yasiyorsa okuma dongusu sonsuza kadar
    bloklanirdi. Grubun bir uyesi yasadikca pgid yeniden kullanilmaz;
    ProcessLookupError "grupta kimse kalmadi" demektir.
  * sonlandir() tekrarlanirsa ikinci SIGKILL zamanlayicisi kurulmaz.
  * Ust surec (arayuz) normal cikarken acik gruplar atexit ile SIGKILL alir:
    yetim openmc/mpiexec kalmaz. (SIGKILL ile oldurulen ust surecte hicbir
    kanca calisamaz; o durumda gruplar yetim kalir -- belgeli sinir.)
"""

from __future__ import annotations

import atexit
import os
import re
import signal
import subprocess
import sys
import threading
from typing import Dict, Iterator, List, Mapping, Optional, Set, Tuple

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

MPIEXEC_ORTAM_DEGISKENI = "OPENMC_ARAYUZ_MPIEXEC"
MPIEXEC_ADI = "mpiexec"
SURUM_SURESI = 15.0                  # s; `openmc --version` ust siniri
_MPI_DESEN = re.compile(r"MPI enabled:\s*(yes|no)", re.IGNORECASE)

Ortam = Optional[Mapping[str, str]]


class KuyrukHatasi(RuntimeError):
    """Kosu hazirlanamadi / baslatilamadi (metin kullaniciya gosterilir)."""


# ============================================================================
# KOMUT VE MPI
# ============================================================================

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


_MPI_ONBELLEK: Dict[Tuple[str, float], Optional[bool]] = {}
_MPI_KILIDI = threading.Lock()


def mpi_destegi(openmc: Optional[str]) -> Optional[bool]:
    """openmc MPI ile derlenmis mi: True / False; anlasilamazsa None."""
    if not openmc or not _calistirilabilir_mi(openmc):
        return None
    anahtar = (openmc, os.stat(openmc).st_mtime)
    with _MPI_KILIDI:
        if anahtar in _MPI_ONBELLEK:
            return _MPI_ONBELLEK[anahtar]
    try:
        cikti = subprocess.run([openmc, "--version"], capture_output=True, text=True,
                               encoding="utf-8", errors="replace",
                               timeout=SURUM_SURESI, check=False).stdout
    except (OSError, subprocess.TimeoutExpired):
        _log.warning("openmc --version calistirilamadi: %s", openmc, exc_info=True)
        return None
    m = _MPI_DESEN.search(cikti or "")
    destek = None if m is None else m.group(1).lower() == "yes"
    with _MPI_KILIDI:
        _MPI_ONBELLEK[anahtar] = destek
    return destek



def _calistirilabilir_mi(yol: str) -> bool:
    return os.path.isfile(yol) and os.access(yol, os.X_OK)


# ============================================================================
# SUREC GRUBU
# ============================================================================

_ACIK_GRUPLAR: Set[int] = set()
_ACIK_KILIDI = threading.Lock()


def _sinyal(pgid: int, sinyal: int) -> bool:
    """Gruba sinyal. DONER False: grupta yasayan surec yok."""
    try:
        os.killpg(pgid, sinyal)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        _log.warning("surec grubu %d sinyal %d alamadi (izin)", pgid, sinyal)
        return False


def grup_yasiyor_mu(pgid: int) -> bool:
    """Grupta yasayan (ya da toplanmamis) surec var mi (sinyal 0 yoklamasi)."""
    return _sinyal(pgid, 0)


@atexit.register
def _acik_gruplari_oldur() -> None:
    with _ACIK_KILIDI:
        gruplar = list(_ACIK_GRUPLAR)
        _ACIK_GRUPLAR.clear()
    for pgid in gruplar:
        _sinyal(pgid, signal.SIGKILL)


def acik_gruplar() -> List[int]:
    with _ACIK_KILIDI:
        return sorted(_ACIK_GRUPLAR)


class SurecGrubu:
    """Kendi oturumunda kosan bir alt surec ve grubu."""

    def __init__(self, komut: List[str], cwd: str, ortam: Mapping[str, str]) -> None:
        self.surec = subprocess.Popen(
            komut, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", bufsize=1, env=dict(ortam),
            start_new_session=True)
        self.pgid = self.surec.pid
        self._kilit = threading.Lock()
        self._zamanlayici: Optional[threading.Timer] = None
        with _ACIK_KILIDI:
            _ACIK_GRUPLAR.add(self.pgid)

    def satirlar(self) -> Iterator[str]:
        assert self.surec.stdout is not None
        yield from self.surec.stdout

    def bekle(self, zaman_asimi: Optional[float] = None) -> int:
        return self.surec.wait(zaman_asimi)

    def sonlandir(self, iptal_suresi: float) -> None:
        """SIGTERM gruba; iptal_suresi sonra SIGKILL (zamanlayici tekil)."""
        _sinyal(self.pgid, signal.SIGTERM)
        with self._kilit:
            if self._zamanlayici is not None:
                return
            self._zamanlayici = threading.Timer(iptal_suresi, _sinyal,
                                                args=(self.pgid, signal.SIGKILL))
            self._zamanlayici.daemon = True
            self._zamanlayici.start()

    def kapat(self, iptal_suresi: float) -> None:
        """Lider yasiyorsa SIGTERM -> bekle -> SIGKILL; lider toplanir; grupta kalan
        (boruyu tutan torun) SIGKILL alir; boru kapanir. Hata yukari tasinmaz."""
        try:
            if self.surec.poll() is None:
                _sinyal(self.pgid, signal.SIGTERM)
                try:
                    self.surec.wait(iptal_suresi)
                except subprocess.TimeoutExpired:
                    _sinyal(self.pgid, signal.SIGKILL)
                    self.surec.wait()
            if grup_yasiyor_mu(self.pgid):
                _sinyal(self.pgid, signal.SIGKILL)
        finally:
            with self._kilit:
                if self._zamanlayici is not None:
                    self._zamanlayici.cancel()
            if self.surec.stdout is not None:
                try:
                    self.surec.stdout.close()
                except OSError:
                    _log.debug("surec borusu kapatilamadi (%d)", self.pgid, exc_info=True)
            with _ACIK_KILIDI:
                _ACIK_GRUPLAR.discard(self.pgid)
