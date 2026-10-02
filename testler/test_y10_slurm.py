# -*- coding: utf-8 -*-
"""
 test_y10_slurm.py  --  Y10 SLURM betigi uretimi (cekirdek/slurm.py):
                        bash -n sozdizimi, girdi dogrulama, kacis (enjeksiyon yok)
"""

import os
import subprocess

from testler.ortak_test import ORNEK
from testler import y10_ortak as yo


def _ayar(**kw):
    from cekirdek import slurm
    alanlar = dict(is_adi="pwr_17x17", sure="02:00:00", gorev=1, cpu_gorev=8)
    alanlar.update(kw)
    return slurm.SlurmAyari(**alanlar)


def test_betik_bash_sozdizimini_gecer():
    # Arrange
    from cekirdek import slurm
    ayarlar = [_ayar(), _ayar(gorev=4, dugum=2, bolum="hesap", hesap="nukleer_1",
                              bellek="16G", eposta="a.b@uni.edu.tr", moduller=("openmpi/4.1",),
                              conda_ortami="openmc-env", ek_ortam={"OPENMC_CROSS_SECTIONS":
                                                                   "/veri/x s/cross_sections.xml"},
                              mpi_baslatici="mpiexec", kosu_dizini="/scratch/u/kosu 1")]
    for a in ayarlar:
        # Act
        metin = slurm.betik_uret(a)
        tamam, mesaj = slurm.sozdizimi_denetle(metin)
        # Assert
        assert tamam, mesaj
        assert metin.startswith("#!/bin/bash\n")


def test_betik_sbatch_satirlari_ve_komut():
    from cekirdek import slurm
    metin = slurm.betik_uret(_ayar(gorev=4, dugum=2, bolum="hesap", bellek="16G"))
    satirlar = metin.splitlines()
    for beklenen in ("#SBATCH --job-name=pwr_17x17", "#SBATCH --nodes=2", "#SBATCH --ntasks=4",
                     "#SBATCH --cpus-per-task=8", "#SBATCH --time=02:00:00",
                     "#SBATCH --partition=hesap", "#SBATCH --mem=16G"):
        assert beklenen in satirlar, beklenen
    assert "set -euo pipefail" in satirlar
    assert any(s.startswith("srun ") and "-s" in s for s in satirlar)
    tek = slurm.betik_uret(_ayar())
    assert not any(s.startswith("srun ") for s in tek.splitlines()), "tek gorevde srun yok"
    # #SBATCH satirlari ilk komuttan once olmali (sbatch ilk komutta okumayi birakir)
    ilk_komut = next(i for i, s in enumerate(satirlar) if s and not s.startswith("#"))
    assert all(i < ilk_komut for i, s in enumerate(satirlar) if s.startswith("#SBATCH"))


def test_gecersiz_girdiler_reddedilir():
    hatali = [
        dict(is_adi="ad\n#SBATCH --x"), dict(is_adi="a b"), dict(is_adi=""),
        dict(sure="2 saat"), dict(sure="02:00:00\nrm"), dict(gorev=0), dict(cpu_gorev=-1),
        dict(dugum=0), dict(bolum="a b"), dict(hesap="x;y"), dict(bellek="16 GB"),
        dict(eposta="a@b; rm -rf ~"), dict(moduller=("openmpi; rm",)),
        dict(conda_ortami="env$(id)"), dict(ek_ortam={"1X": "a"}), dict(ek_ortam={"A B": "a"}),
        dict(mpi_baslatici="bash"), dict(openmc=""), dict(gorev=True),
        dict(kosu_dizini="a\nb"), dict(ek_ortam={"A": "x\ny"}),
        # Python'da `$` sondaki yeni satirdan ONCE de eslesir: fullmatch sart
        dict(is_adi="pwr\n"), dict(bolum="hesap\n"), dict(moduller=("openmpi\n",)),
        dict(conda_ortami="env\n"), dict(ek_ortam={"A\n": "x"}), dict(eposta="a@b.edu\n"),
    ]
    for kw in hatali:
        try:
            _ayar(**kw)
            raise AssertionError("gecersiz girdi kabul edildi: %r" % kw)
        except ValueError:
            pass


def test_kullanici_metni_kacislanir_enjeksiyon_calismaz(tmp_path):
    # Arrange: dizin ve ortam degerinde kabuk metakarakterleri
    from cekirdek import slurm
    kotu_ad = "kosu '; touch PWNED1; ' $(touch PWNED2) `touch PWNED3`"
    dizin = tmp_path / kotu_ad
    dizin.mkdir()
    kayit = tmp_path / "openmc_arg.txt"
    sahte_bin = tmp_path / "bin"
    yo.calistirilabilir(sahte_bin / "openmc",
                        '#!/bin/sh\nprintf "%%s|" "$PWD" "$@" "$DEGER" > "%s"\n' % kayit)
    metin = slurm.betik_uret(_ayar(kosu_dizini=str(dizin),
                                   ek_ortam={"DEGER": "$(touch PWNED4); echo x"}))
    betik = tmp_path / "is.sh"
    betik.write_text(metin)
    ortam = {"PATH": "%s:/usr/bin:/bin" % sahte_bin, "HOME": str(tmp_path)}
    # Act
    sonuc = subprocess.run(["/bin/bash", str(betik)], cwd=str(tmp_path), env=ortam,
                           capture_output=True, text=True, timeout=30)
    # Assert
    assert sonuc.returncode == 0, sonuc.stderr
    for n in range(1, 5):
        assert not list(tmp_path.rglob("PWNED%d" % n)), "enjeksiyon calisti: PWNED%d" % n
    alanlar = kayit.read_text().split("|")
    assert alanlar[0] == str(dizin)
    assert alanlar[1:3] == ["-s", "8"]
    assert alanlar[3] == "$(touch PWNED4); echo x"


def test_sozdizimi_denetimi_bozuk_betigi_yakalar():
    from cekirdek import slurm
    tamam, mesaj = slurm.sozdizimi_denetle("#!/bin/bash\nif true; then\n")
    assert not tamam and mesaj


def test_hazirla_model_ve_betigi_yazar(tmp_path):
    # Arrange
    from cekirdek import sema, slurm
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    dizin = str(tmp_path / "kume")
    # Act
    yol = slurm.hazirla(spec, dizin, _ayar(kosu_dizini=None))
    # Assert
    assert yol == os.path.join(dizin, slurm.BETIK_ADI)
    for ad in ("model.xml", "spec.json", slurm.BETIK_ADI):
        assert os.path.isfile(os.path.join(dizin, ad)), ad
    assert os.access(yol, os.X_OK)
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    assert 'cd -- "${SLURM_SUBMIT_DIR:-.}"' in metin
    assert slurm.sozdizimi_denetle(metin)[0]


HIZLI = [test_betik_bash_sozdizimini_gecer, test_betik_sbatch_satirlari_ve_komut,
         test_gecersiz_girdiler_reddedilir, test_kullanici_metni_kacislanir_enjeksiyon_calismaz,
         test_sozdizimi_denetimi_bozuk_betigi_yakalar, test_hazirla_model_ve_betigi_yazar]
YAVAS = []
