# -*- coding: utf-8 -*-
"""
================================================================================
 slurm.py  --  SLURM is betigi uretimi (Y10)
================================================================================

 Bir modeli hesaplama kumesinde (HPC) kosturmak icin `sbatch is.sh` ile
 gonderilecek bash betigini uretir. Betik bu makinede CALISTIRILMAZ;
 sozdizimi `bash -n` ile denetlenir.

   ayar = SlurmAyari(is_adi="pwr", sure="02:00:00", gorev=4, cpu_gorev=8,
                     bolum="hesap", moduller=("openmpi/4.1",), conda_ortami="openmc-env")
   metin = betik_uret(ayar)
   tamam, mesaj = sozdizimi_denetle(metin)
   yol = hazirla(spec, "/yol/kume_kosusu", ayar)  # model.xml + spec.json + is.sh

 GUVENLIK (kullanici girdisi -> kabuk)
   * #SBATCH satirlari bash degil sbatch tarafindan okunur ve TIRNAK KACISI
     YOKTUR: bu alanlar (is adi, sure, bolum, hesap, bellek, e-posta) kati
     desenlerle DOGRULANIR; uymayan deger ValueError ile reddedilir (yeni satir
     ile ek yonerge enjeksiyonu dahil).
   * Kabuk satirlarindaki serbest metin (kosu dizini, openmc yolu, ek ortam
     degiskeni degerleri, conda ortami) shlex.quote ile tek tirnakla yazilir:
     $(...), `...`, ; ve ' kabukta YORUMLANMAZ. Modul ve ortam degiskeni ADLARI
     desenle dogrulanir. Yeni satir hicbir alanda kabul edilmez.
   * Betik `set -euo pipefail` ile baslar: ilk hatada durur.

 KOMUT
   gorev (ntasks) = MPI surec sayisi; > 1 ise `srun` (ya da mpi_baslatici=
   "mpiexec" ile `mpiexec -n $SLURM_NTASKS`) ile baslatilir -- openmc MPI
   destekli derlenmis olmali (kuyruk.mpi_destegi). cpu_gorev = OpenMP is
   parcacigi: OMP_NUM_THREADS = $SLURM_CPUS_PER_TASK, `openmc -s` ayni sayi.
================================================================================
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Tuple

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

BETIK_ADI = "is.sh"
MPI_BASLATICILARI = ("srun", "mpiexec")
_SOZDIZIMI_SURESI = 10.0         # s; `bash -n` ust siniri
_BETIK_IZNI = 0o750

# sbatch(1) bicimleri; kaynak: https://slurm.schedmd.com/sbatch.html
_DESEN = {
    "is_adi": re.compile(r"^[A-Za-z0-9_.-]{1,64}$"),
    # --time: "dakika", "dk:sn", "sa:dk:sn", "gun-sa", "gun-sa:dk", "gun-sa:dk:sn"
    "sure": re.compile(r"^(\d+-)?\d{1,3}(:\d{2}){0,2}$"),
    "bolum": re.compile(r"^[A-Za-z0-9_.,-]{1,64}$"),
    "hesap": re.compile(r"^[A-Za-z0-9_.-]{1,64}$"),
    "bellek": re.compile(r"^\d+[KMGT]?$"),
    "eposta": re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"),
}
_MODUL_DESENI = re.compile(r"^[A-Za-z0-9_.+/-]{1,128}$")
_CONDA_DESENI = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_ORTAM_ADI_DESENI = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _tam_sayi(ad: str, deger: Any, en_az: int = 1) -> int:
    if isinstance(deger, bool) or not isinstance(deger, int) or deger < en_az:
        raise ValueError(_("%s en az %d olan bir tam sayı olmalı: %r") % (ad, en_az, deger))
    return deger


def _satirsiz(ad: str, deger: str) -> str:
    if "\n" in deger or "\r" in deger or "\0" in deger:
        raise ValueError(_("%s yeni satır içeremez") % ad)
    return deger


@dataclass(frozen=True)
class SlurmAyari:
    is_adi: str
    sure: str = "01:00:00"
    dugum: int = 1
    gorev: int = 1
    cpu_gorev: int = 1
    bolum: Optional[str] = None
    hesap: Optional[str] = None
    bellek: Optional[str] = None
    eposta: Optional[str] = None
    moduller: Tuple[str, ...] = ()
    conda_ortami: Optional[str] = None
    ek_ortam: Mapping[str, str] = field(default_factory=dict)
    openmc: str = "openmc"
    mpi_baslatici: str = "srun"
    kosu_dizini: Optional[str] = None

    def __post_init__(self) -> None:
        for ad, desen in _DESEN.items():
            deger = getattr(self, ad)
            if deger is None and ad not in ("is_adi", "sure"):
                continue
            if not isinstance(deger, str) or not desen.fullmatch(deger):
                raise ValueError(_("geçersiz SLURM alanı %s: %r") % (ad, deger))
        for ad in ("dugum", "gorev", "cpu_gorev"):
            _tam_sayi(ad, getattr(self, ad))
        self._serbest_alanlari_denetle()
        object.__setattr__(self, "moduller", tuple(self.moduller))
        object.__setattr__(self, "ek_ortam", dict(self.ek_ortam))

    def _serbest_alanlari_denetle(self) -> None:
        for m in self.moduller:
            if not _MODUL_DESENI.fullmatch(str(m)):
                raise ValueError(_("geçersiz modül adı: %r") % (m,))
        if self.conda_ortami is not None and not _CONDA_DESENI.fullmatch(self.conda_ortami):
            raise ValueError(_("geçersiz conda ortamı adı: %r") % (self.conda_ortami,))
        for ad, deger in dict(self.ek_ortam).items():
            if not _ORTAM_ADI_DESENI.fullmatch(str(ad)):
                raise ValueError(_("geçersiz ortam değişkeni adı: %r") % (ad,))
            _satirsiz(ad, str(deger))
        if not str(self.openmc or "").strip():
            raise ValueError(_("openmc yolu boş olamaz"))
        _satirsiz("openmc", self.openmc)
        if self.kosu_dizini is not None:
            _satirsiz(_("koşu dizini"), self.kosu_dizini)
        if self.mpi_baslatici not in MPI_BASLATICILARI:
            raise ValueError(_("MPI başlatıcı %s olmalı: %r")
                             % (" / ".join(MPI_BASLATICILARI), self.mpi_baslatici))


def _sbatch_satirlari(a: SlurmAyari) -> list:
    satirlar = ["#SBATCH --job-name=%s" % a.is_adi,
                "#SBATCH --nodes=%d" % a.dugum,
                "#SBATCH --ntasks=%d" % a.gorev,
                "#SBATCH --cpus-per-task=%d" % a.cpu_gorev,
                "#SBATCH --time=%s" % a.sure,
                "#SBATCH --output=%s-%%j.log" % a.is_adi]
    if a.bolum:
        satirlar.append("#SBATCH --partition=%s" % a.bolum)
    if a.hesap:
        satirlar.append("#SBATCH --account=%s" % a.hesap)
    if a.bellek:
        satirlar.append("#SBATCH --mem=%s" % a.bellek)
    if a.eposta:
        satirlar += ["#SBATCH --mail-user=%s" % a.eposta, "#SBATCH --mail-type=END,FAIL"]
    return satirlar


def _ortam_satirlari(a: SlurmAyari) -> list:
    satirlar = ["module load %s" % m for m in a.moduller]
    if a.conda_ortami:
        satirlar += ['eval "$(conda shell.bash hook)"',
                     "conda activate %s" % shlex.quote(a.conda_ortami)]
    satirlar.append('export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-%d}"' % a.cpu_gorev)
    satirlar += ["export %s=%s" % (ad, shlex.quote(str(d))) for ad, d in a.ek_ortam.items()]
    return satirlar


def _komut_satiri(a: SlurmAyari) -> str:
    openmc = '%s -s "${OMP_NUM_THREADS}"' % shlex.quote(a.openmc)
    if a.gorev <= 1:
        return openmc
    if a.mpi_baslatici == "mpiexec":
        return 'mpiexec -n "${SLURM_NTASKS:-%d}" %s' % (a.gorev, openmc)
    return "srun %s" % openmc


def betik_uret(ayar: SlurmAyari) -> str:
    """sbatch betiginin metni (deterministik; tarih/saat yazilmaz)."""
    dizin = (shlex.quote(ayar.kosu_dizini) if ayar.kosu_dizini
             else '"${SLURM_SUBMIT_DIR:-.}"')
    satirlar = ["#!/bin/bash"] + _sbatch_satirlari(ayar) + [
        "# openmc-arayuz (Y10) tarafından üretildi; göndermek için: sbatch %s" % BETIK_ADI,
        "",
        "set -euo pipefail",
    ] + _ortam_satirlari(ayar) + [
        "cd -- %s" % dizin,
        _komut_satiri(ayar),
        "",
    ]
    return "\n".join(satirlar)


def sozdizimi_denetle(metin: str) -> Tuple[bool, str]:
    """`bash -n` ile sozdizimi denetimi (betik CALISTIRILMAZ). DONER (tamam, mesaj)."""
    bash = shutil.which("bash", path="/usr/bin:/bin") or "/bin/bash"
    try:
        sonuc = subprocess.run([bash, "-n"], input=metin, capture_output=True, text=True,
                               timeout=_SOZDIZIMI_SURESI, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        _log.warning("bash -n calistirilamadi", exc_info=True)
        return False, str(e)
    return sonuc.returncode == 0, sonuc.stderr.strip()


def hazirla(spec: Mapping[str, Any], dizin: str, ayar: SlurmAyari) -> str:
    """Dizine model.xml + spec.json + kapsul ve is.sh yazar. DONER betik yolu."""
    from cekirdek import kosucu
    metin = betik_uret(ayar)
    tamam, mesaj = sozdizimi_denetle(metin)
    if not tamam:
        raise RuntimeError(_("üretilen SLURM betiği sözdizimi denetiminden geçmedi: %s") % mesaj)
    kosucu.dizin_hazirla(dizin, temizle=True)
    kosucu.xml_yaz(dict(spec), dizin, is_parcacigi=ayar.cpu_gorev)
    yol = os.path.join(dizin, BETIK_ADI)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    os.chmod(yol, _BETIK_IZNI)
    return yol
