# -*- coding: utf-8 -*-
"""
test_p2_masaustu.py -- v3 P2: masaustu butunlesmesi (cekirdek/masaustu).

Hepsi gecici HOME'da calisir (gercek ~/.local'e dokunmaz). xdg araclari
(desktop-file-validate, xdg-mime) yoksa ilgili test pytest.skip ile ACIKCA atlanir.
Kabul: kur -> .desktop gecerli, MIME turu ve varsayilan acici, xdg-open'in
cagiracagi Exec satiri dosyayla calisir; kaldir -> iz kalmaz.
"""

import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time

import pytest

from cekirdek import masaustu
from cekirdek.masaustu import kurulum
from testler.ortak_test import KOK

_ZAMAN_ASIMI = 120          # s; alt surec (python + xdg araclari)
_ACILIS_BEKLEME_DENEME = 50     # x 0.1 s = 5 s; xdg-open'in baslattigi sureci bekle
_ACILIS_BEKLEME_ARALIGI = 0.1
_PROJE_ORNEGI = os.path.join(KOK, "ornekler", "pwr_pinhucre.json")
_SAHTE_BETIK = '#!/bin/sh\nprintf "%s\\n" "$@" > "$OPENMC_ARAYUZ_TEST_CIKTI"\n'


class _Ev:
    """Gecici HOME + sahte openmc-arayuz betigi + alt surec ortami."""

    def __init__(self, kok):
        self.kok = kok
        self.ev = os.path.join(kok, "ev")
        os.makedirs(os.path.join(self.ev))
        self.bin = os.path.join(kok, "bin", "openmc-arayuz")
        os.makedirs(os.path.dirname(self.bin))
        with open(self.bin, "w") as f:
            f.write(_SAHTE_BETIK)
        os.chmod(self.bin, 0o755)
        self.cikti = os.path.join(kok, "argv.txt")
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("XDG_", "KDE_", "GNOME_", "DESKTOP_"))
                    and k not in ("DISPLAY", "WAYLAND_DISPLAY", "BROWSER")}
        self.env.update(HOME=self.ev, PYTHONPATH=KOK, OPENMC_ARAYUZ_TEST_CIKTI=self.cikti)

    def kosu(self, *args):
        return subprocess.run([sys.executable, "-m", "cekirdek.masaustu", *args],
                              env=self.env, capture_output=True, text=True,
                              timeout=_ZAMAN_ASIMI, cwd=self.kok)

    def kur(self, *ek):
        sonuc = self.kosu("kur", "--exec", self.bin, *ek)
        assert sonuc.returncode == 0, sonuc.stderr
        return sonuc

    def agac(self):
        """Ev altindaki tum yollar (dizinler dahil) -- iz karsilastirmasi icin."""
        cikti = []
        for yol, dizinler, dosyalar in os.walk(self.ev):
            cikti.extend(os.path.join(yol, a) for a in dizinler + dosyalar)
        return sorted(cikti)

    def yol(self, *parca):
        return os.path.join(self.ev, ".local", "share", *parca)

    def calistir(self, arguman, *args):
        """Bir komutu bu ortamla calistirir (xdg-mime vb.)."""
        return subprocess.run([arguman, *args], env=self.env, capture_output=True,
                              text=True, timeout=_ZAMAN_ASIMI).stdout.strip()


def _gecici():
    return tempfile.TemporaryDirectory(prefix="p2-")


def _arac_iste(*adlar):
    eksik = [a for a in adlar if shutil.which(a) is None]
    if eksik:
        pytest.skip("xdg araci yok, atlandi: %s" % ", ".join(eksik))


# ---------------------------------------------------------------------------
# saf islevler
# ---------------------------------------------------------------------------

def test_exec_alintilama():
    assert kurulum.exec_alintila("/usr/bin/openmc-arayuz") == "/usr/bin/openmc-arayuz"
    assert kurulum.exec_alintila("/a b/x") == '"/a b/x"'
    assert kurulum.exec_alintila("/a/100%/x") == "/a/100%%/x"
    # $ tirnak icinde \$ ; .desktop'ta ters bolu ikilenir -> \\$
    assert kurulum.exec_alintila("/a$/x") == '"/a\\\\$/x"'


def test_desktop_metni_gerekli_anahtarlar():
    metin = kurulum.desktop_metni("/opt/x/openmc-arayuz")
    satirlar = dict(s.split("=", 1) for s in metin.splitlines() if "=" in s)
    assert satirlar["Exec"] == "/opt/x/openmc-arayuz %f"
    assert satirlar["TryExec"] == "/opt/x/openmc-arayuz"
    assert satirlar["Categories"] == "Science;Education;Physics;"
    assert satirlar["StartupWMClass"] == masaustu.UYGULAMA_KIMLIGI
    assert satirlar["MimeType"] == masaustu.MIME_TURU + ";"
    assert "Name[tr]" in satirlar and "Comment[tr]" in satirlar and "Keywords" in satirlar
    assert "@" not in satirlar["Exec"]


def test_mimeapps_ekle_ve_geri_al():
    mime, d = masaustu.MIME_TURU, "openmc-arayuz.desktop"
    bos, onceki = kurulum.varsayilan_ayarla("", mime, d)
    assert bos == "[Default Applications]\n%s=%s\n" % (mime, d) and onceki is None
    assert kurulum.varsayilan_geri_al(bos, mime, d, None) == ""
    # baskasinin satirlari ve baska bolumler korunur
    metin = "[Default Applications]\ntext/html=a.desktop\n\n[Added Associations]\nx/y=b.desktop;\n"
    yeni, _ = kurulum.varsayilan_ayarla(metin, mime, d)
    assert "text/html=a.desktop" in yeni and "x/y=b.desktop;" in yeni
    assert kurulum.varsayilan_geri_al(yeni, mime, d, None).strip() == metin.strip()
    # onceki deger geri gelir; baskasi degistirdiyse (satir bizim degil) dokunulmaz
    elle, onceki = kurulum.varsayilan_ayarla("[Default Applications]\n%s=eski.desktop\n" % mime, mime, d)
    assert onceki == "eski.desktop"
    assert "%s=eski.desktop" % mime in kurulum.varsayilan_geri_al(elle, mime, d, onceki)
    baskasi = "[Default Applications]\n%s=baska.desktop\n" % mime
    assert kurulum.varsayilan_geri_al(baskasi, mime, d, None) == baskasi


def test_paket_kaynaklari_var():
    assert os.path.isfile(masaustu.simge_yolu())
    for b in kurulum.SIMGE_BOYUTLARI:
        assert len(kurulum._kaynak("openmc-arayuz-%d.png" % b)) > 100
    assert b"application/x-openmc-arayuz+json" in kurulum._kaynak("openmc-arayuz-mime.xml")


def test_kosulsuz_json_glob_yok():
    """MIME XML *.json glob'u tanimlamaz (varsayilan JSON iliskisi ezilmez)."""
    xml = kurulum._kaynak("openmc-arayuz-mime.xml").decode("utf-8")
    assert "<glob" not in xml and "glob-deleteall" not in xml
    assert '<sub-class-of type="application/json"/>' in xml


def test_calistirilabilir_dogrulama():
    with _gecici() as kok:
        ev = _Ev(kok)
        assert kurulum.calistirilabilir_coz(ev.bin) == ev.bin
        for kotu in (os.path.join(kok, "yok"), kok):
            with pytest.raises(masaustu.MasaustuHatasi):
                kurulum.calistirilabilir_coz(kotu)


# ---------------------------------------------------------------------------
# kur / kaldir (gecici HOME)
# ---------------------------------------------------------------------------

def test_kur_dosyalari_yazar_ve_kaldir_iz_birakmaz():
    with _gecici() as kok:
        ev = _Ev(kok)
        once = ev.agac()
        ev.kur()
        assert os.path.isfile(ev.yol("applications", "openmc-arayuz.desktop"))
        for b in kurulum.SIMGE_BOYUTLARI:
            assert os.path.isfile(ev.yol("icons", "hicolor", "%dx%d" % (b, b), "apps", "openmc-arayuz.png"))
        assert os.path.isfile(ev.yol("icons", "hicolor", "scalable", "apps", "openmc-arayuz.svg"))
        assert ev.kosu("durum").returncode == 0
        sonuc = ev.kosu("kaldir")
        assert sonuc.returncode == 0, sonuc.stderr
        assert ev.agac() == once, "kaldir sonrasi iz kaldi"
        assert ev.kosu("durum").returncode == 1


def test_kur_ve_kaldir_tekrarlanabilir():
    with _gecici() as kok:
        ev = _Ev(kok)
        once = ev.agac()
        ev.kur()
        birinci = ev.agac()
        ev.kur()
        assert ev.agac() == birinci
        assert ev.kosu("kaldir").returncode == 0
        assert ev.kosu("kaldir").returncode == 0      # ikinci kez: zararsiz
        assert ev.agac() == once


def test_desktop_file_validate():
    _arac_iste("desktop-file-validate")
    with _gecici() as kok:
        ev = _Ev(kok)
        ev.kur()
        sonuc = subprocess.run(["desktop-file-validate", ev.yol("applications", "openmc-arayuz.desktop")],
                               capture_output=True, text=True, timeout=_ZAMAN_ASIMI)
        # "hint:" (birden cok ana kategori: Science+Education, gorev karti istedi) hata degil
        hatalar = [s for s in sonuc.stdout.splitlines() + sonuc.stderr.splitlines()
                   if s.strip() and "hint:" not in s]
        assert sonuc.returncode == 0 and not hatalar, hatalar


def test_xdg_mime_tur_varsayilan_ve_acilis():
    _arac_iste("xdg-mime", "update-mime-database")
    with _gecici() as kok:
        ev = _Ev(kok)
        ev.kur()
        proje = os.path.join(kok, "proje.json")
        shutil.copy(_PROJE_ORNEGI, proje)
        baska = os.path.join(kok, "baska.json")
        with open(baska, "w") as f:
            json.dump({"a": 1}, f)
        assert ev.calistir("xdg-mime", "query", "filetype", proje) == masaustu.MIME_TURU
        # baska JSON'a dokunulmadi: varsayilan JSON iliskisi ezilmez
        assert ev.calistir("xdg-mime", "query", "filetype", baska) == "application/json"
        assert ev.calistir("xdg-mime", "query", "default", masaustu.MIME_TURU) == "openmc-arayuz.desktop"
        # xdg-open'in yaptigi: .desktop Exec satirini %f -> dosya ile calistir
        exec_satiri = _desktop_exec(ev.yol("applications", "openmc-arayuz.desktop"))
        argv = [proje if p == "%f" else p for p in shlex.split(exec_satiri)]
        subprocess.run(argv, env=ev.env, check=True, timeout=_ZAMAN_ASIMI)
        with open(ev.cikti) as f:
            assert f.read().splitlines() == [proje]


def _desktop_exec(yol):
    with open(yol, encoding="utf-8") as f:
        for satir in f:
            if satir.startswith("Exec="):
                return satir[5:].rstrip("\n")
    raise AssertionError("Exec yok")


def test_xdg_open_proje_dosyasini_uygulamaya_verir():
    """Gercek xdg-open (generic DE, sahte DISPLAY): uygulama argv'de dosyayla acilir."""
    _arac_iste("xdg-open", "xdg-mime", "update-mime-database")
    with _gecici() as kok:
        ev = _Ev(kok)
        ev.kur()
        proje = os.path.join(kok, "proje.json")
        shutil.copy(_PROJE_ORNEGI, proje)
        env = dict(ev.env, DISPLAY=":99", XDG_DATA_DIRS=ev.yol() + ":/usr/local/share:/usr/share")
        sonuc = subprocess.run(["xdg-open", proje], env=env, capture_output=True, text=True,
                               timeout=_ZAMAN_ASIMI)
        assert sonuc.returncode == 0, sonuc.stderr
        for _ in range(_ACILIS_BEKLEME_DENEME):          # alt surec eszamansiz baslayabilir
            if os.path.isfile(ev.cikti):
                break
            time.sleep(_ACILIS_BEKLEME_ARALIGI)
        with open(ev.cikti) as f:
            assert f.read().splitlines() == [proje]


def test_varsayilan_yapma_mimeapps_yazmaz():
    with _gecici() as kok:
        ev = _Ev(kok)
        ev.kur("--varsayilan-yapma")
        assert not os.path.exists(os.path.join(ev.ev, ".config", "mimeapps.list"))
        assert ev.kosu("kaldir").returncode == 0


def test_kaldir_baskasinin_dosyalarini_korur():
    with _gecici() as kok:
        ev = _Ev(kok)
        ayar = os.path.join(ev.ev, ".config")
        os.makedirs(ayar)
        mimeapps = os.path.join(ayar, "mimeapps.list")
        with open(mimeapps, "w") as f:
            f.write("[Default Applications]\ntext/html=tarayici.desktop\n")
        baskasi = ev.yol("mime", "packages", "baska.xml")
        os.makedirs(os.path.dirname(baskasi))
        with open(baskasi, "w") as f:
            f.write('<mime-info xmlns="http://www.freedesktop.org/standards/shared-mime-info"/>\n')
        diger = ev.yol("applications", "baska.desktop")
        os.makedirs(os.path.dirname(diger))
        with open(diger, "w") as f:
            f.write("[Desktop Entry]\nType=Application\nName=B\nExec=b\n")
        ev.kur()
        assert ev.kosu("kaldir").returncode == 0
        assert os.path.isfile(baskasi) and os.path.isfile(diger)
        with open(mimeapps) as f:
            assert f.read() == "[Default Applications]\ntext/html=tarayici.desktop\n"


def test_kaldir_sembolik_baglanti_ve_kok_disi_yolu_silmez():
    with _gecici() as kok:
        ev = _Ev(kok)
        ev.kur()
        manifest = ev.yol("openmc_arayuz", "masaustu_manifest.json")
        with open(manifest, encoding="utf-8") as f:
            veri = json.load(f)
        hedef = os.path.join(kok, "kullanici_dosyasi.txt")
        with open(hedef, "w") as f:
            f.write("dokunma")
        svg = ev.yol("icons", "hicolor", "scalable", "apps", "openmc-arayuz.svg")
        os.unlink(svg)
        os.symlink(hedef, svg)                              # manifestte listeli yol sembolik baglanti
        veri["dosyalar"].append(hedef)                      # kok disi yol (kurcalanmis manifest)
        with open(manifest, "w", encoding="utf-8") as f:
            json.dump(veri, f)
        sonuc = ev.kosu("kaldir")
        assert sonuc.returncode == 0, sonuc.stderr
        assert os.path.isfile(hedef), "kok disi dosya silindi"
        assert os.path.islink(svg), "sembolik baglanti silindi/izlendi"


def test_kur_sembolik_baglanti_uzerine_yazmaz():
    with _gecici() as kok:
        ev = _Ev(kok)
        hedef = os.path.join(kok, "baska.txt")
        with open(hedef, "w") as f:
            f.write("dokunma")
        d = ev.yol("applications")
        os.makedirs(d)
        os.symlink(hedef, os.path.join(d, "openmc-arayuz.desktop"))
        sonuc = ev.kosu("kur", "--exec", ev.bin)
        assert sonuc.returncode == 1
        with open(hedef) as f:
            assert f.read() == "dokunma"


def test_exec_bulunamazsa_hata_kodu_1():
    with _gecici() as kok:
        ev = _Ev(kok)
        sonuc = ev.kosu("kur", "--exec", os.path.join(kok, "yok"))
        assert sonuc.returncode == 1 and "bulunamadi" in sonuc.stderr
        assert ev.agac() == []


def test_betikler_sozdizimi_ve_guvenli_mod():
    for ad in ("kur.sh", "kaldir.sh"):
        yol = os.path.join(KOK, "paket", "masaustu", ad)
        assert os.stat(yol).st_mode & stat.S_IXUSR
        with open(yol, encoding="utf-8") as f:
            assert "set -euo pipefail" in f.read()
        subprocess.run(["bash", "-n", yol], check=True, timeout=_ZAMAN_ASIMI)


def test_betik_kur_sonra_kaldir():
    with _gecici() as kok:
        ev = _Ev(kok)
        once = ev.agac()
        env = dict(ev.env, PYTHON=sys.executable)
        kur = os.path.join(KOK, "paket", "masaustu", "kur.sh")
        kaldir = os.path.join(KOK, "paket", "masaustu", "kaldir.sh")
        subprocess.run(["bash", kur, "--exec", ev.bin], env=env, check=True, cwd=kok, timeout=_ZAMAN_ASIMI)
        assert ev.agac() != once
        subprocess.run(["bash", kaldir], env=env, check=True, cwd=kok, timeout=_ZAMAN_ASIMI)
        assert ev.agac() == once


def test_qt_uygulama_kimligi():
    """ana_pencere.main Qt adini/masaustu dosya adini .desktop ile eslestirir."""
    with open(os.path.join(KOK, "arayuz", "ana_pencere.py"), encoding="utf-8") as f:
        kaynak = f.read()
    assert "setApplicationName(masaustu.UYGULAMA_KIMLIGI)" in kaynak
    assert "setDesktopFileName(masaustu.UYGULAMA_KIMLIGI)" in kaynak
    assert masaustu.UYGULAMA_KIMLIGI == "openmc-arayuz"


HIZLI = [test_exec_alintilama, test_desktop_metni_gerekli_anahtarlar, test_mimeapps_ekle_ve_geri_al,
         test_paket_kaynaklari_var, test_kosulsuz_json_glob_yok, test_calistirilabilir_dogrulama,
         test_kur_dosyalari_yazar_ve_kaldir_iz_birakmaz, test_kur_ve_kaldir_tekrarlanabilir,
         test_desktop_file_validate, test_xdg_mime_tur_varsayilan_ve_acilis,
         test_xdg_open_proje_dosyasini_uygulamaya_verir, test_varsayilan_yapma_mimeapps_yazmaz,
         test_kaldir_baskasinin_dosyalarini_korur,
         test_kaldir_sembolik_baglanti_ve_kok_disi_yolu_silmez,
         test_kur_sembolik_baglanti_uzerine_yazmaz, test_exec_bulunamazsa_hata_kodu_1,
         test_betikler_sozdizimi_ve_guvenli_mod, test_betik_kur_sonra_kaldir,
         test_qt_uygulama_kimligi]
