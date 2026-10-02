# -*- coding: utf-8 -*-
"""
 test_y10_inceleme.py  --  Y10 inceleme bulgulari (security + python):
   surec yasam dongusu (okuma hatasi, boru tutan torun, tekil SIGKILL, atexit),
   olay sirasi (IsDurumu.seq), ekle/sinirlar tutarliligi, parametre/SLURM/k_farki
   sinir durumlari.
"""

import math
import os
import subprocess
import threading
import time

import pytest

from testler import y10_ortak as yo

_BEKLEME = 30.0


def _kuyruk(tmp_path, monkeypatch, **kw):
    from cekirdek import kuyruk
    monkeypatch.setenv("SAHTE_KAYIT", str(tmp_path / "kayit.txt"))
    kw.setdefault("openmc", yo.sahte_openmc(tmp_path))
    return kuyruk.Kuyruk(**kw)


def _is(tmp_path, ad, **kw):
    from cekirdek import kuyruk
    return kuyruk.KosuIsi(ad=ad, dizin=yo.hazir_dizin(tmp_path / ad),
                          sonuc_kancasi=kw.pop("sonuc_kancasi", yo.sahte_sonuc), **kw)


def _pid_dosyasi_bekle(yol):
    yo.bekle_kadar(lambda: os.path.isfile(yol) and open(yol).read().strip(), _BEKLEME)
    return [int(x) for x in open(yol).read().split()]


def _olu_mu(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    # zombi de "olu" sayilir (toplanmayi bekleyen)
    try:
        with open("/proc/%d/stat" % pid) as f:
            return f.read().split()[2] == "Z"
    except OSError:
        return True


# ---------------------------------------------------------------------------
# HIGH 1: okuma dongusunde istisna -> surec oldurulur ve toplanir
# ---------------------------------------------------------------------------

def test_okuma_hatasinda_surec_grubu_oldurulur(tmp_path, monkeypatch):
    # Arrange: satir islerken hata (disk dolu benzetimi); ikili uzun surer
    from cekirdek import kuyruk, kuyruk_surec
    monkeypatch.setenv("SAHTE_SURE", "2")
    k = _kuyruk(tmp_path, monkeypatch, iptal_suresi=0.2)

    def bozuk(self, kimlik, satir):
        raise OSError("disk dolu")
    monkeypatch.setattr(kuyruk.Kuyruk, "_satir_isle", bozuk)
    x = k.ekle(_is(tmp_path, "x"))
    # Act
    t0 = time.monotonic()
    k.baslat()
    assert k.bekle(_BEKLEME)
    # Assert
    d = k.durum(x)
    assert d.asama == kuyruk.Asama.BASARISIZ and "disk dolu" in d.hata
    assert time.monotonic() - t0 < 8.0, "surec beklenmeden oldurulmeli"
    assert kuyruk_surec.acik_gruplar() == []
    k.kapat()


def test_bozuk_bayt_okumayi_durdurmaz(tmp_path, monkeypatch):
    from cekirdek import kuyruk
    exe = yo.calistirilabilir(tmp_path / "bin" / "openmc",
                              "#!/bin/sh\nprintf '\\377\\376 bozuk\\n'\n"
                              "echo '   3/1    1.0    1.01 +/- 0.002'\n"
                              "touch statepoint.3.h5\n")
    k = _kuyruk(tmp_path, monkeypatch, openmc=exe)
    x = k.ekle(_is(tmp_path, "x"))
    k.baslat()
    assert k.bekle(_BEKLEME)
    assert k.durum(x).asama == kuyruk.Asama.BITTI, k.durum(x).hata
    k.kapat()


# ---------------------------------------------------------------------------
# HIGH 2: lider cikti, boruyu tutan torun TERM'i yok sayiyor -> iptal yine biter
# ---------------------------------------------------------------------------

def _torunlu_ikili(tmp_path, lider_bekler):
    pidler = tmp_path / "pidler.txt"
    torun = "sh -c 'trap \"\" TERM; echo $$ >> %s; while :; do sleep 0.1; done' &\n" % pidler
    lider = ("trap '' TERM\nwhile :; do sleep 0.1; done\n" if lider_bekler else "exit 0\n")
    return yo.calistirilabilir(tmp_path / "bin" / "openmc",
                               "#!/bin/sh\necho $$ > %s\n%s%s" % (pidler, torun, lider)), str(pidler)


def _iptal_torun(tmp_path, monkeypatch, lider_bekler):
    # Arrange
    from cekirdek import kuyruk, kuyruk_surec
    exe, pidler = _torunlu_ikili(tmp_path, lider_bekler)
    k = _kuyruk(tmp_path, monkeypatch, openmc=exe, iptal_suresi=0.2)
    x = k.ekle(_is(tmp_path, "x"))
    k.baslat()
    yo.bekle_kadar(lambda: len(open(pidler).read().split()) >= 2 if os.path.isfile(pidler)
                   else False, _BEKLEME)
    pid_listesi = [int(p) for p in open(pidler).read().split()]
    # Act
    k.iptal(x)
    k.iptal(x)                      # tekrar: ikinci SIGKILL zamanlayicisi kurulmaz
    # Assert
    assert k.bekle(10.0), "boruyu tutan torun okumayi kilitlememeli"
    assert k.durum(x).asama == kuyruk.Asama.IPTAL
    yo.bekle_kadar(lambda: all(_olu_mu(p) for p in pid_listesi), 5.0)
    # zombi torunu init toplayana kadar grup kimligi kisa sure gorunur kalabilir
    yo.bekle_kadar(lambda: not kuyruk_surec.grup_yasiyor_mu(pid_listesi[0]), 5.0)
    with pytest.raises(ProcessLookupError):
        os.killpg(pid_listesi[0], 0)
    assert kuyruk_surec.acik_gruplar() == []
    k.kapat()


def test_iptal_boru_tutan_toruni_da_oldurur(tmp_path, monkeypatch):
    _iptal_torun(tmp_path, monkeypatch, lider_bekler=True)


def test_lider_cikmisken_iptal_toruni_oldurur(tmp_path, monkeypatch):
    _iptal_torun(tmp_path, monkeypatch, lider_bekler=False)


def test_sonlandir_zamanlayicisi_tekil(tmp_path):
    from cekirdek import kuyruk_surec
    grup = kuyruk_surec.SurecGrubu(["sleep", "30"], str(tmp_path), os.environ)
    grup.sonlandir(5.0)
    ilk = grup._zamanlayici
    grup.sonlandir(5.0)
    assert grup._zamanlayici is ilk
    grup.kapat(0.2)
    assert grup.surec.returncode is not None
    assert not kuyruk_surec.grup_yasiyor_mu(grup.pgid)


def test_atexit_acik_gruplari_oldurur(tmp_path):
    # Ust surec cikinca alt surec grubu yetim kalmaz
    betik = tmp_path / "ust.py"
    pidf = tmp_path / "pid.txt"
    betik.write_text(
        "import sys, os\nsys.path.insert(0, %r)\n"
        "from cekirdek import kuyruk_surec\n"
        "g = kuyruk_surec.SurecGrubu(['sleep', '60'], %r, os.environ)\n"
        "open(%r, 'w').write(str(g.pgid))\n" % (os.getcwd(), str(tmp_path), str(pidf)))
    subprocess.run([os.sys.executable, str(betik)], check=True, timeout=30)
    pid = int(pidf.read_text())
    yo.bekle_kadar(lambda: _olu_mu(pid), 5.0)


# ---------------------------------------------------------------------------
# HIGH 3: olay sirasi -- seq artar, eski olay yayilmaz
# ---------------------------------------------------------------------------

def test_olay_sirasi_seq_ile_tekdize(tmp_path, monkeypatch):
    # Arrange: cok sayida hizli is, paralel
    monkeypatch.setenv("SAHTE_SURE", "0")
    k = _kuyruk(tmp_path, monkeypatch, en_fazla_paralel=4, is_parcacigi_butcesi=4)
    olaylar = []
    kilit = threading.Lock()

    def dinle(d):
        with kilit:
            olaylar.append(d)
    k.dinleyici_ekle(dinle)
    kimlikler = [k.ekle(_is(tmp_path, "h%d" % i)) for i in range(12)]
    # Act
    k.baslat()
    assert k.bekle(_BEKLEME)
    # Assert
    for x in kimlikler:
        seqler = [o.seq for o in olaylar if o.kimlik == x]
        assert seqler == sorted(seqler) and len(set(seqler)) == len(seqler), seqler
        son = [o for o in olaylar if o.kimlik == x][-1]
        assert son.bitti_mi
    tum = [o.seq for o in olaylar]
    assert len(set(tum)) == len(tum), "seq kuyruk genelinde tekil"
    k.kapat()


def test_bagdastirici_eski_olayi_atar(tmp_path, monkeypatch):
    import dataclasses
    from PySide6 import QtWidgets
    from cekirdek import kuyruk
    from arayuz.kuyruk.bagdastirici import KuyrukBagdastirici
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    kq = KuyrukBagdastirici(_kuyruk(tmp_path, monkeypatch))
    gelen = []
    kq.durum_degisti.connect(gelen.append)
    yeni = kuyruk.IsDurumu(kimlik="a", ad="a", dizin="/a", asama=kuyruk.Asama.BITTI, seq=5)
    kq._olay(yeni)
    kq._olay(dataclasses.replace(yeni, asama=kuyruk.Asama.KOSUYOR, seq=3))
    assert [d.seq for d in gelen] == [5]
    kq.kapat()


# ---------------------------------------------------------------------------
# MEDIUM / LOW: kuyruk tutarliligi
# ---------------------------------------------------------------------------

def test_ekle_hata_verirse_kismi_kayit_kalmaz(tmp_path, monkeypatch):
    from cekirdek import kuyruk
    k = _kuyruk(tmp_path, monkeypatch)
    kotu = kuyruk.KosuIsi(ad="x", dizin=str(tmp_path / "x"),
                          spec={"ayarlar": {"cevrim": "yirmi"}})
    with pytest.raises(ValueError):
        k.ekle(kotu)
    assert k.durumlar() == [] and k.tamamlandi_mi()


def test_sinirlar_bekleyen_isin_sigmayacagi_butceyi_reddeder(tmp_path, monkeypatch):
    k = _kuyruk(tmp_path, monkeypatch, is_parcacigi_butcesi=8)
    k.ekle(_is(tmp_path, "buyuk", is_parcacigi=6))
    with pytest.raises(ValueError):
        k.sinirlari_ayarla(1, 4)
    assert k.is_parcacigi_butcesi == 8
    k.sinirlari_ayarla(2, 6)
    assert k.is_parcacigi_butcesi == 6


def test_kapat_toplam_son_tarihe_uyar(tmp_path, monkeypatch):
    from cekirdek import kuyruk
    monkeypatch.setattr(kuyruk, "_KAPAT_SURESI", 1.0)
    monkeypatch.setenv("SAHTE_SURE", "3")
    k = _kuyruk(tmp_path, monkeypatch, en_fazla_paralel=3, is_parcacigi_butcesi=3,
                iptal_suresi=0.2)
    for i in range(3):
        k.ekle(_is(tmp_path, "u%d" % i))
    k.baslat()
    yo.bekle_kadar(lambda: all(d.asama == kuyruk.Asama.KOSUYOR for d in k.durumlar()), 10)
    t0 = time.monotonic()
    k.kapat()
    assert time.monotonic() - t0 < 3.0


def test_baglam_yoneticisi_kapatir(tmp_path, monkeypatch):
    from cekirdek import kuyruk
    with _kuyruk(tmp_path, monkeypatch) as k:
        k.ekle(_is(tmp_path, "x"))
    with pytest.raises(RuntimeError):
        k.ekle(_is(tmp_path, "y"))
    assert k.durumlar()[0].asama == kuyruk.Asama.IPTAL


def test_iplik_baslatilamazsa_is_basarisiz(tmp_path, monkeypatch):
    from cekirdek import kuyruk

    def bozuk_start(self):
        raise RuntimeError("can't start new thread")
    k = _kuyruk(tmp_path, monkeypatch)
    x = k.ekle(_is(tmp_path, "x"))
    monkeypatch.setattr(threading.Thread, "start", bozuk_start)
    k.baslat()
    monkeypatch.undo()
    assert k.bekle(5.0)
    assert k.durum(x).asama == kuyruk.Asama.BASARISIZ
    assert "thread" in k.durum(x).hata


def test_ayri_dizin_kok_disina_cikmaz_ve_bos_kok_reddedilir(tmp_path):
    from cekirdek import kuyruk
    yol = kuyruk.ayri_dizin(str(tmp_path), "../../etc")
    assert os.path.dirname(yol) == str(tmp_path)
    with pytest.raises(ValueError):
        kuyruk.ayri_dizin("", "x")
    a = kuyruk.ayri_dizin(str(tmp_path), "r", olustur=True)
    b = kuyruk.ayri_dizin(str(tmp_path), "r", olustur=True)
    assert a != b and os.path.isdir(a) and os.path.isdir(b)


def test_mpi_destegi_bozuk_cikti(tmp_path):
    from cekirdek import kuyruk
    exe = yo.calistirilabilir(tmp_path / "o", "#!/bin/sh\nprintf '\\377 MPI enabled: yes\\n'\n")
    assert kuyruk.mpi_destegi(exe) is True


# ---------------------------------------------------------------------------
# parametre
# ---------------------------------------------------------------------------

def _taban():
    import os as _os
    from cekirdek import sema
    from testler.ortak_test import ORNEK
    return sema.yukle(_os.path.join(ORNEK, "pwr_pinhucre.json"))


def test_parametre_sonlu_olmayan_ve_unicode_rakam_reddi():
    from cekirdek import parametre as p
    for deger in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            p.Tarama(degerler={"a": (1.0, deger)})
        with pytest.raises(ValueError):
            p.yol_uygula(_taban(), "ayarlar.cevrim", deger)
    with pytest.raises(KeyError):
        p.yol_uygula(_taban(), "ayarlar.entropi_mesh.boyut.١", 1)   # Arapca-Hint 1


def test_parametre_nokta_sinirini_asan_tarama_reddedilir():
    from cekirdek import parametre as p
    n = int(math.isqrt(p.MAKS_NOKTA)) + 2
    with pytest.raises(ValueError):
        p.ParametrikModel(ad="m", taban=_taban(), degiskenler=(
            p.Degisken(ad="a", tur=p.YOL_TURU, hedef="ayarlar.cevrim"),
            p.Degisken(ad="b", tur=p.YOL_TURU, hedef="ayarlar.pasif")),
            tarama=p.Tarama(degerler={"a": tuple(range(n)), "b": tuple(range(n))}))


def test_kuyruga_ekle_atomik_ve_var_olan_dizini_kullanmaz(tmp_path, monkeypatch):
    from cekirdek import kuyruk, parametre as p
    model = p.ParametrikModel(ad="m", taban=_taban(), degiskenler=(
        p.Degisken(ad="n", tur=p.YOL_TURU, hedef="ayarlar.parcacik"),),
        tarama=p.Tarama(degerler={"n": (100, 200, 300)}))
    os.makedirs(tmp_path / "t" / "nokta_000")
    k = _kuyruk(tmp_path, monkeypatch, is_parcacigi_butcesi=2)
    kimlikler = p.kuyruga_ekle(model, k, str(tmp_path / "t"), dogrulama=False)
    assert str(tmp_path / "t" / "nokta_000") not in [k.durum(x).dizin for x in kimlikler]
    # ikinci eklemede 3. nokta basarisiz -> eklenenler geri alinir
    k2 = _kuyruk(tmp_path, monkeypatch, is_parcacigi_butcesi=2)
    asil = k2.ekle
    sayac = {"n": 0}

    def bozuk_ekle(is_):
        sayac["n"] += 1
        if sayac["n"] == 3:
            raise ValueError("dolu")
        return asil(is_)
    monkeypatch.setattr(k2, "ekle", bozuk_ekle)
    with pytest.raises(ValueError):
        p.kuyruga_ekle(model, k2, str(tmp_path / "t2"), dogrulama=False)
    assert k2.durumlar() == []


def test_sozlukten_tur_hatasi_valueerror():
    from cekirdek import parametre as p
    with pytest.raises(ValueError):
        p.sozlukten({"bicim": p.BICIM_ADI, "surum": 1, "taban": {}, "degiskenler": [3]})
    with pytest.raises(ValueError):
        p.sozlukten({"bicim": p.BICIM_ADI, "surum": "x", "taban": {}})


# ---------------------------------------------------------------------------
# SLURM ve k_farki
# ---------------------------------------------------------------------------

def test_slurm_modul_ve_conda_set_u_altinda_calisir(tmp_path):
    # Arrange: `module` ve `conda` tanimsiz degisken okuyan kabuk islevleri (gercek
    # Lmod/conda betikleri boyle davranir); set -u altinda kirilirdi
    from cekirdek import slurm
    metin = slurm.betik_uret(slurm.SlurmAyari(
        is_adi="x", moduller=("openmpi/4.1",), conda_ortami="env", openmc="true"))
    on = ("module() { echo \"$TANIMSIZ_LMOD\" > /dev/null; }\n"
          "conda() { echo \"$TANIMSIZ_CONDA\" > /dev/null; }\nexport -f module conda\n")
    betik = tmp_path / "is.sh"
    betik.write_text(metin.replace("set -o pipefail\n", "set -o pipefail\n" + on, 1))
    sonuc = subprocess.run(["/bin/bash", str(betik)], cwd=str(tmp_path), capture_output=True,
                           text=True, timeout=30,
                           env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)})
    assert sonuc.returncode == 0, sonuc.stderr
    assert metin.index("set -o pipefail") < metin.index("module load")
    assert metin.index("set -euo pipefail") > metin.index("conda activate")


def test_slurm_ascii_ve_tire_ile_baslayan_modul_reddi():
    from cekirdek import slurm
    for kw in (dict(is_adi="adı"), dict(bolum="hésap"), dict(moduller=("-f",)),
               dict(sure="١:00:00")):
        with pytest.raises(ValueError):
            slurm.SlurmAyari(**dict(dict(is_adi="x"), **kw))


def test_k_farki_sonlu_olmayan_reddi_ve_esik():
    from cekirdek import kosu_gecmisi as kg
    for arg in ((math.nan, 0.1, 1.0, 0.1), (1.0, math.inf, 1.0, 0.1), (1.0, 0.1, 1.0, math.nan)):
        with pytest.raises(ValueError):
            kg.k_farki(*arg)
    f = kg.k_farki(1.0, 0.0003, 1.0 + 0.0005 * 2.0000001, 0.0004)
    assert f.anlamli and math.isclose(f.z, 2.0, rel_tol=1e-6)


def test_gecmis_negatif_sinir_ve_dosya_izni(tmp_path):
    from cekirdek import kosu_gecmisi as kg
    depo = kg.GecmisDeposu(str(tmp_path / "g.sqlite3"))
    with pytest.raises(ValueError):
        depo.listele(sinir=-1)
    assert os.stat(depo.yol).st_mode & 0o077 == 0


def test_spec_sha_beklenmeyen_json(tmp_path):
    import json
    from cekirdek import kosu_gecmisi as kg
    (tmp_path / "kapsul.json").write_text(json.dumps([1, 2]))
    assert kg._spec_sha(str(tmp_path)) is None
    (tmp_path / "kapsul.json").write_text(json.dumps({"spec": "metin"}))
    assert kg._spec_sha(str(tmp_path)) is None


HIZLI = [test_okuma_hatasinda_surec_grubu_oldurulur, test_bozuk_bayt_okumayi_durdurmaz,
         test_iptal_boru_tutan_toruni_da_oldurur, test_lider_cikmisken_iptal_toruni_oldurur,
         test_sonlandir_zamanlayicisi_tekil,
         test_atexit_acik_gruplari_oldurur, test_olay_sirasi_seq_ile_tekdize,
         test_bagdastirici_eski_olayi_atar, test_ekle_hata_verirse_kismi_kayit_kalmaz,
         test_sinirlar_bekleyen_isin_sigmayacagi_butceyi_reddeder,
         test_kapat_toplam_son_tarihe_uyar, test_baglam_yoneticisi_kapatir,
         test_iplik_baslatilamazsa_is_basarisiz,
         test_ayri_dizin_kok_disina_cikmaz_ve_bos_kok_reddedilir, test_mpi_destegi_bozuk_cikti,
         test_parametre_sonlu_olmayan_ve_unicode_rakam_reddi,
         test_parametre_nokta_sinirini_asan_tarama_reddedilir,
         test_kuyruga_ekle_atomik_ve_var_olan_dizini_kullanmaz,
         test_sozlukten_tur_hatasi_valueerror, test_slurm_modul_ve_conda_set_u_altinda_calisir,
         test_slurm_ascii_ve_tire_ile_baslayan_modul_reddi, test_k_farki_sonlu_olmayan_reddi_ve_esik,
         test_gecmis_negatif_sinir_ve_dosya_izni, test_spec_sha_beklenmeyen_json]
YAVAS = []
