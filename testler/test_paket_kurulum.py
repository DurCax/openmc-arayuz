# -*- coding: utf-8 -*-
"""
 test_paket_kurulum.py  --  v3 P1: constructor ile tek dosya .sh kurulum paketi

 HIZLI  : betik soz dizimi, kaldirma betiginin guvenlik korumalari (isaretsiz
          dizini silmez), uretim betigi/tarif tutarliligi.
 YAVAS  : paketi uretir (ya da OPENMC_ARAYUZ_PAKET_SH ile verileni kullanir),
          TEMIZ bir HOME ve bos ortamla (env -i) kurar, basssiz pencereyi
          acip kapatir, openmc-arayuz-kosu ile kosu dener, kaldirir.
          constructor yoksa (conda ortami openmc-paketleme) test ATLANIR;
          neden pytest ciktisinda yazar. Nukleer veri yoksa kosu adimi yalniz
          --sadece-dogrula ile sinirlanir (veri pakete girmez).
"""

import glob
import os
import shutil
import subprocess
import tempfile

import pytest

from testler.ortak_test import kontrol, KOK

_PAKET = os.path.join(KOK, "paket", "constructor")
_URETIM_SURESI = 1800        # s; ilk uretim paketleri indirir (sonraki: ~30 s)
_KURULUM_SURESI = 900        # s
_KOSU_SURESI = 600           # s
_PENCERE_DENETIMI = """
import sys
from cekirdek import giris, yollar
from PySide6 import QtCore, QtWidgets
assert yollar.openmc_ikilisi(), "openmc bulunamadi"
_exec = QtWidgets.QApplication.exec
def _kisa(app):
    assert [w for w in app.topLevelWidgets() if w.isVisible()], "gorunur pencere yok"
    QtCore.QTimer.singleShot(1000, app.quit)
    return _exec()
QtWidgets.QApplication.exec = _kisa
sys.exit(giris.gui([]))
"""


def _calistir(komut, **kw):
    return subprocess.run(komut, capture_output=True, text=True, **kw)


def test_betikler_soz_dizimi():
    print("\n[P1-1] bash -n: uret.sh, post_install.sh, kaldir.sh")
    for ad in ("uret.sh", "post_install.sh", "kaldir.sh"):
        r = _calistir(["bash", "-n", os.path.join(_PAKET, ad)])
        kontrol("%s soz dizimi" % ad, r.returncode == 0, r.stderr)
        with open(os.path.join(_PAKET, ad), encoding="utf-8") as f:
            kontrol("%s set -euo pipefail" % ad, "set -euo pipefail" in f.read())


def test_kaldir_isaretsiz_dizini_silmez(tmp_path):
    print("\n[P1-2] kaldir.sh: openmc-arayuz isareti olmayan dizine dokunmaz")
    sahte = tmp_path / "baska"
    paket = sahte / "share" / "openmc-arayuz-paket"
    paket.mkdir(parents=True)
    shutil.copy(os.path.join(_PAKET, "kaldir.sh"), paket / "kaldir.sh")
    (sahte / "onemli.txt").write_text("silinmemeli")
    r = _calistir(["bash", str(paket / "kaldir.sh"), "--evet"], env={"HOME": str(tmp_path)})
    kontrol("isaretsiz dizin: hata kodu", r.returncode != 0, r.stderr)
    kontrol("isaretsiz dizin: dosya durur", (sahte / "onemli.txt").exists())
    (sahte / ".openmc-arayuz-kurulum").write_text("x")      # isaret var ama conda yok
    r = _calistir(["bash", str(paket / "kaldir.sh"), "--evet"], env={"HOME": str(tmp_path)})
    kontrol("conda yapisi yoksa silmez", r.returncode != 0 and (sahte / "onemli.txt").exists(),
            r.stderr)


def test_tarif_ve_uretim_tutarli():
    print("\n[P1-3] construct.yaml: nukleer veri yok, conda-forge, kok yetkisi yok")
    with open(os.path.join(_PAKET, "construct.yaml"), encoding="utf-8") as f:
        yml = f.read()
    kontrol("installer_type sh", "installer_type: sh" in yml)
    kontrol("openmc nodagmc_nompi sabit", "openmc 0.16.0 nodagmc_nompi" in yml)
    kontrol("yalniz conda-forge", "- conda-forge" in yml and "defaults" not in yml)
    kontrol("nukleer veri paketi yok", "endf" not in yml.lower() and "nndc" not in yml.lower())
    kontrol(".bashrc'ye yazmaz", "initialize_by_default: false" in yml)
    with open(os.path.join(_PAKET, "post_install.sh"), encoding="utf-8") as f:
        pi = f.read()
    kontrol("post_install ag kullanmaz (--no-index)", "--no-index" in pi and "curl" not in pi
            and "wget" not in pi)
    kontrol("masaustu kancasi adli", "masaustu/kur.sh" in pi)


def _constructor_var_mi():
    if shutil.which("constructor"):
        return True
    ortam = os.environ.get("OPENMC_ARAYUZ_PAKETLEME_ORTAMI", "openmc-paketleme")
    taban = os.path.dirname(os.path.dirname(shutil.which("conda") or "/yok/yok"))
    return os.path.isfile(os.path.join(taban, "envs", ortam, "bin", "constructor"))


def _paketi_hazirla():
    var = os.environ.get("OPENMC_ARAYUZ_PAKET_SH")
    if var:
        return var
    r = _calistir(["bash", os.path.join(_PAKET, "uret.sh")], timeout=_URETIM_SURESI)
    kontrol("uret.sh basarili", r.returncode == 0, (r.stdout + r.stderr)[-1500:])
    adaylar = sorted(glob.glob(os.path.join(KOK, "dist", "openmc-arayuz-*-Linux-x86_64.sh")))
    return adaylar[-1] if adaylar else None


def test_temiz_dizine_kurulum_acilis_kosu(gecici):
    print("\n[P1-Y1] paketi uret, temiz HOME'a kur, basssiz ac, kos, kaldir")
    if not _constructor_var_mi() and not os.environ.get("OPENMC_ARAYUZ_PAKET_SH"):
        pytest.skip("constructor yok (conda create -n openmc-paketleme -c conda-forge constructor "
                    "'setuptools>=77' wheel pip)")
    paket = _paketi_hazirla()
    kontrol("tek dosya .sh uretildi", bool(paket) and os.path.isfile(paket), str(paket))
    if not paket:
        return
    ev = os.path.join(gecici, "home")
    onek = os.path.join(ev, "openmc-arayuz")
    os.makedirs(ev)
    temiz = {"HOME": ev, "PATH": "/usr/bin:/bin", "QT_QPA_PLATFORM": "offscreen",
             "OMP_NUM_THREADS": "2", "LANG": "C.UTF-8"}
    r = _calistir(["bash", paket, "-b", "-p", onek], env=temiz, timeout=_KURULUM_SURESI)
    kontrol("kurulum (-b, kok yetkisiz, ag yok)", r.returncode == 0, (r.stdout + r.stderr)[-1500:])
    kontrol("openmc-arayuz komutu kuruldu", os.access(os.path.join(onek, "bin", "openmc-arayuz"),
                                                      os.X_OK))
    kontrol("openmc ikilisi kuruldu", os.access(os.path.join(onek, "bin", "openmc"), os.X_OK))
    kontrol("kurulum isareti", os.path.isfile(os.path.join(onek, ".openmc-arayuz-kurulum")))
    kontrol("nukleer veri pakette yok", not glob.glob(os.path.join(onek, "**", "cross_sections.xml"),
                                                      recursive=True))
    kontrol(".bashrc'ye dokunulmadi", not os.path.exists(os.path.join(ev, ".bashrc")))
    py = os.path.join(onek, "bin", "python")
    r = _calistir([py, "-c", _PENCERE_DENETIMI], env=temiz, cwd=gecici, timeout=_KOSU_SURESI)
    kontrol("basssiz pencere acilir/kapanir", r.returncode == 0, r.stderr[-800:])
    ornek = os.path.join(onek, "share", "openmc-arayuz", "ornekler", "godiva_kriter.json")
    komut = [os.path.join(onek, "bin", "openmc-arayuz-kosu"), ornek]
    veri = os.environ.get("OPENMC_CROSS_SECTIONS")
    if veri and os.path.isfile(veri):
        temiz["OPENMC_CROSS_SECTIONS"] = veri
        komut += ["--dizin", os.path.join(gecici, "kosu")]
    else:
        komut += ["--sadece-dogrula"]
    r = _calistir(komut, env=temiz, cwd=gecici, timeout=_KOSU_SURESI)
    kontrol("openmc-arayuz-kosu (%s)" % ("kosu" if "--dizin" in komut else "dogrulama"),
            r.returncode == 0, (r.stdout + r.stderr)[-800:])
    komsu = os.path.join(ev, "komsu.txt")
    with open(komsu, "w") as f:
        f.write("kurulum disi dosya")
    r = _calistir(["bash", os.path.join(onek, "share", "openmc-arayuz-paket", "kaldir.sh"), "--evet"],
                  env=temiz, timeout=_KURULUM_SURESI)
    kontrol("kaldirma", r.returncode == 0 and not os.path.exists(onek), r.stderr)
    kontrol("kaldirma yalniz kendi dizinini siler", os.path.isfile(komsu))


HIZLI = [test_betikler_soz_dizimi, test_kaldir_isaretsiz_dizini_silmez, test_tarif_ve_uretim_tutarli]
YAVAS = [test_temiz_dizine_kurulum_acilis_kosu]
