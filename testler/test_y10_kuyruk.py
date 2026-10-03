# -*- coding: utf-8 -*-
"""
 test_y10_kuyruk.py  --  Y10 kosu kuyrugu (cekirdek/kuyruk.py)

 Hizli testler SAHTE bir openmc ikilisiyle kosar (testler/y10_ortak.py):
 cevrim satirlari basar, statepoint.N.h5 birakir, baslangic/bitis anlarini
 ortak bir kayit dosyasina yazar. Boylece sira, paralellik, butce ve iptal
 gercek Monte Carlo olmadan olculur. Gercek kisa kosu YAVAS listesindedir.
"""

import json
import os
import time

from testler.ortak_test import ORNEK, ISLEM_PARCACIGI
from testler import y10_ortak as yo
from testler.ortak_test import gereksinim  # v3 izlenebilirlik

# Kuyruk testlerinde bir isin bitmesi icin cömert ust sinir (s); sahte
# ikili ~0.1 s'de biter. Asilirsa test kilitlenmez, basarisiz olur.
_BEKLEME = 30.0


def _kuyruk(tmp_path, monkeypatch, **kw):
    from cekirdek import kuyruk
    exe = yo.sahte_openmc(tmp_path)
    monkeypatch.setenv("SAHTE_KAYIT", str(tmp_path / "kayit.txt"))
    return kuyruk.Kuyruk(openmc=exe, **kw)


def _is(tmp_path, ad, **kw):
    from cekirdek import kuyruk
    dizin = yo.hazir_dizin(tmp_path / ad)
    return kuyruk.KosuIsi(ad=ad, dizin=dizin, is_parcacigi=kw.pop("is_parcacigi", 1),
                          sonuc_kancasi=kw.pop("sonuc_kancasi", yo.sahte_sonuc), **kw)


@gereksinim("R-V3-28")
def test_uc_kosu_sirayla_biter(tmp_path, monkeypatch):
    # Arrange
    from cekirdek import kuyruk
    k = _kuyruk(tmp_path, monkeypatch, en_fazla_paralel=1)
    kimlikler = [k.ekle(_is(tmp_path, "kosu_%d" % i)) for i in range(3)]
    # Act
    k.baslat()
    bitti = k.bekle(_BEKLEME)
    # Assert
    assert bitti
    durumlar = [k.durum(x) for x in kimlikler]
    assert [d.asama for d in durumlar] == [kuyruk.Asama.BITTI] * 3
    araliklar = yo.kayit_araliklari(tmp_path / "kayit.txt")
    sira = [os.path.basename(d) for d, _b, _s in araliklar]
    assert sira == ["kosu_0", "kosu_1", "kosu_2"]
    for (_d1, _b1, son1), (_d2, bas2, _s2) in zip(araliklar, araliklar[1:]):
        assert bas2 >= son1, "sirali kuyrukta kosular ust uste binmemeli"
    for d in durumlar:
        assert d.k == (1.01, 0.002)
        assert os.path.isfile(os.path.join(d.dizin, "kosu.log"))
        assert d.statepoint and os.path.isfile(d.statepoint)
        assert d.cevrim == yo.SAHTE_CEVRIM
        assert d.toplam_cevrim is None, "spec'siz iste toplam cevrim bilinmez"
    k.kapat()


@gereksinim("R-V3-28")
def test_her_kosu_ayri_dizinde_ve_ayni_dizin_reddedilir(tmp_path, monkeypatch):
    # Arrange
    from cekirdek import kuyruk
    k = _kuyruk(tmp_path, monkeypatch)
    k.ekle(_is(tmp_path, "a"))
    # Act / Assert
    try:
        k.ekle(_is(tmp_path, "a"))
        raise AssertionError("ayni dizin ikinci kez kabul edildi")
    except ValueError as e:
        assert "a" in str(e)
    yollar = {kuyruk.ayri_dizin(str(tmp_path), "UO2 3.1%/demet") for _ in range(1)}
    yol = yollar.pop()
    assert os.path.dirname(yol) == str(tmp_path)
    assert "/" not in os.path.basename(yol) and " " not in os.path.basename(yol)
    os.makedirs(yol)
    assert kuyruk.ayri_dizin(str(tmp_path), "UO2 3.1%/demet") != yol


@gereksinim("R-V3-28")
def test_paralel_kosu_is_parcacigi_butcesini_asmaz(tmp_path, monkeypatch):
    # Arrange: butce 4, her is 2 is parcacigi -> ayni anda en fazla 2 kosu
    monkeypatch.setenv("SAHTE_SURE", "0.05")
    k = _kuyruk(tmp_path, monkeypatch, en_fazla_paralel=3, is_parcacigi_butcesi=4)
    for i in range(4):
        k.ekle(_is(tmp_path, "p%d" % i, is_parcacigi=2))
    # Act
    k.baslat()
    assert k.bekle(_BEKLEME)
    # Assert
    araliklar = yo.kayit_araliklari(tmp_path / "kayit.txt")
    assert len(araliklar) == 4
    assert yo.en_cok_ortusme(araliklar) == 2
    omp = yo.kayit_omp(tmp_path / "kayit.txt")
    assert set(omp) == {"2"}, "OMP_NUM_THREADS ise ozgu is parcacigi sayisi olmali"
    k.kapat()


def test_butceyi_asan_is_reddedilir(tmp_path, monkeypatch):
    k = _kuyruk(tmp_path, monkeypatch, is_parcacigi_butcesi=4)
    try:
        k.ekle(_is(tmp_path, "buyuk", is_parcacigi=8))
        raise AssertionError("butceyi asan is kabul edildi")
    except ValueError:
        pass


def test_tasi_bekleyen_isin_sirasini_degistirir(tmp_path, monkeypatch):
    # Arrange
    k = _kuyruk(tmp_path, monkeypatch)
    a, b, c = (k.ekle(_is(tmp_path, ad)) for ad in ("a", "b", "c"))
    # Act
    k.tasi(c, 0)
    k.baslat()
    assert k.bekle(_BEKLEME)
    # Assert
    sira = [os.path.basename(d) for d, _b, _s in yo.kayit_araliklari(tmp_path / "kayit.txt")]
    assert sira == ["c", "a", "b"]
    assert [d.kimlik for d in k.durumlar()] == [c, a, b]
    k.kapat()


def test_iptal_kosani_sonlandirir_bekleyeni_baslatmaz(tmp_path, monkeypatch):
    # Arrange: ilk is uzun surer (cevrim basina 2 s)
    from cekirdek import kuyruk
    monkeypatch.setenv("SAHTE_SURE", "2")
    k = _kuyruk(tmp_path, monkeypatch)
    uzun = k.ekle(_is(tmp_path, "uzun"))
    bekleyen = k.ekle(_is(tmp_path, "bekleyen"))
    k.baslat()
    yo.bekle_kadar(lambda: k.durum(uzun).asama == kuyruk.Asama.KOSUYOR, _BEKLEME)
    # Act
    t0 = time.monotonic()
    k.iptal(bekleyen)
    k.iptal(uzun)
    assert k.bekle(_BEKLEME)
    # Assert
    assert k.durum(uzun).asama == kuyruk.Asama.IPTAL
    assert k.durum(bekleyen).asama == kuyruk.Asama.IPTAL
    assert time.monotonic() - t0 < 10.0, "iptal sureci hemen sonlandirmali"
    sira = [os.path.basename(d) for d, _b, _s in yo.kayit_araliklari(tmp_path / "kayit.txt",
                                                                       yalniz_biten=False)]
    assert "bekleyen" not in sira
    k.kapat()


def test_basarisiz_kosu_sonrakini_durdurmaz(tmp_path, monkeypatch):
    # Arrange
    from cekirdek import kuyruk
    k = _kuyruk(tmp_path, monkeypatch)
    kotu = k.ekle(_is(tmp_path, "kotu", ortam={"SAHTE_KOD": "3"}))
    iyi = k.ekle(_is(tmp_path, "iyi"))
    # Act
    k.baslat()
    assert k.bekle(_BEKLEME)
    # Assert
    d = k.durum(kotu)
    assert d.asama == kuyruk.Asama.BASARISIZ and d.cikis_kodu == 3
    assert d.hata
    assert k.durum(iyi).asama == kuyruk.Asama.BITTI
    k.kapat()


def test_sonuc_kancasi_hatasi_basarisiz_sayilir(tmp_path, monkeypatch):
    # Arrange
    from cekirdek import kuyruk

    def bozuk(statepoint, is_):
        raise RuntimeError("okunamadi")
    k = _kuyruk(tmp_path, monkeypatch)
    x = k.ekle(_is(tmp_path, "x", sonuc_kancasi=bozuk))
    # Act
    k.baslat()
    assert k.bekle(_BEKLEME)
    # Assert
    d = k.durum(x)
    assert d.asama == kuyruk.Asama.BASARISIZ
    assert "okunamadi" in d.hata
    k.kapat()


def test_dinleyici_durum_olaylarini_alir(tmp_path, monkeypatch):
    # Arrange
    from cekirdek import kuyruk
    olaylar = []
    k = _kuyruk(tmp_path, monkeypatch)
    k.dinleyici_ekle(olaylar.append)
    x = k.ekle(_is(tmp_path, "x"))
    # Act
    k.baslat()
    assert k.bekle(_BEKLEME)
    # Assert
    asamalar = [o.asama for o in olaylar if o.kimlik == x]
    assert asamalar[0] == kuyruk.Asama.BEKLIYOR
    assert kuyruk.Asama.KOSUYOR in asamalar
    assert asamalar[-1] == kuyruk.Asama.BITTI
    cevrimler = [o.cevrim for o in olaylar if o.asama == kuyruk.Asama.KOSUYOR]
    assert max(cevrimler) == yo.SAHTE_CEVRIM
    assert all(isinstance(o, kuyruk.IsDurumu) for o in olaylar)
    k.kapat()


def test_dinleyici_hatasi_kuyrugu_durdurmaz(tmp_path, monkeypatch):
    from cekirdek import kuyruk

    def bozuk(_olay):
        raise RuntimeError("dinleyici")
    k = _kuyruk(tmp_path, monkeypatch)
    k.dinleyici_ekle(bozuk)
    x = k.ekle(_is(tmp_path, "x"))
    k.baslat()
    assert k.bekle(_BEKLEME)
    assert k.durum(x).asama == kuyruk.Asama.BITTI
    k.kapat()


def test_spec_ile_is_model_xml_yazar(tmp_path, monkeypatch):
    # Arrange: spec verilen is kendi dizinini hazirlar (model.xml, spec.json, kapsul)
    from cekirdek import kuyruk, sema
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    k = _kuyruk(tmp_path, monkeypatch)
    dizin = str(tmp_path / "spec_kosusu")
    x = k.ekle(kuyruk.KosuIsi(ad="pin", dizin=dizin, spec=spec, is_parcacigi=1,
                              dogrulama=False, sonuc_kancasi=yo.sahte_sonuc))
    spec["ad"] = "degisti"          # cagiranin sonraki degisikligi ise yansimaz
    # Act
    k.baslat()
    assert k.bekle(_BEKLEME)
    # Assert
    assert k.durum(x).asama == kuyruk.Asama.BITTI, k.durum(x).hata
    assert k.durum(x).toplam_cevrim == spec["ayarlar"]["cevrim"]
    for ad in ("model.xml", "spec.json", "kapsul.json", "kosu.log"):
        assert os.path.isfile(os.path.join(dizin, ad)), ad
    with open(os.path.join(dizin, "spec.json"), encoding="utf-8") as f:
        assert json.load(f)["ad"] != "degisti"
    k.kapat()


def test_openmc_yoksa_is_basarisiz(tmp_path):
    from cekirdek import kuyruk
    k = kuyruk.Kuyruk(openmc=str(tmp_path / "yok" / "openmc"))
    x = k.ekle(_is(tmp_path, "x"))
    k.baslat()
    assert k.bekle(_BEKLEME)
    d = k.durum(x)
    assert d.asama == kuyruk.Asama.BASARISIZ and "openmc" in d.hata
    k.kapat()


def test_bilinmeyen_kimlik_keyerror(tmp_path, monkeypatch):
    k = _kuyruk(tmp_path, monkeypatch)
    for islem in (lambda: k.durum("yok"), lambda: k.iptal("yok"), lambda: k.tasi("yok", 0)):
        try:
            islem()
            raise AssertionError("KeyError beklenirdi")
        except KeyError:
            pass


# ---------------------------------------------------------------------------
# MPI ve komut
# ---------------------------------------------------------------------------

def test_komut_mpi_ile_ve_mpisiz(tmp_path):
    from cekirdek import kuyruk
    assert kuyruk.komut_olustur("/x/openmc", 4) == ["/x/openmc", "-s", "4"]
    assert kuyruk.komut_olustur("/x/openmc", 2, mpi_surec=3, mpiexec="/m/mpiexec") == [
        "/m/mpiexec", "-n", "3", "/x/openmc", "-s", "2"]
    try:
        kuyruk.komut_olustur("/x/openmc", 2, mpi_surec=3, mpiexec=None)
        raise AssertionError("mpiexec yokken MPI komutu kuruldu")
    except RuntimeError:
        pass


def test_mpiexec_yolu_goreli_path_ogesini_yok_sayar(tmp_path, monkeypatch):
    # Arrange
    from cekirdek import kuyruk
    goreli = tmp_path / "goreli"
    mutlak = tmp_path / "mutlak"
    for d in (goreli, mutlak):
        yo.calistirilabilir(d / "mpiexec", "#!/bin/sh\nexit 0\n")
    monkeypatch.chdir(tmp_path)
    ortam = {"PATH": os.pathsep.join(["goreli", "", ".", str(mutlak)])}
    # Act
    yol = kuyruk.mpiexec_yolu(ortam=ortam, python="python")
    # Assert
    assert yol == str(mutlak / "mpiexec")
    assert kuyruk.mpiexec_yolu(ortam={"PATH": "goreli"}, python="python") is None
    ortam_d = {"OPENMC_ARAYUZ_MPIEXEC": str(goreli / "mpiexec"), "PATH": str(mutlak)}
    assert kuyruk.mpiexec_yolu(ortam=ortam_d, python="python") == str(goreli / "mpiexec")
    ortam_g = {"OPENMC_ARAYUZ_MPIEXEC": "goreli/mpiexec", "PATH": str(mutlak)}
    assert kuyruk.mpiexec_yolu(ortam=ortam_g, python="python") == str(mutlak / "mpiexec")


def test_mpi_destegi_openmc_surumunden_okunur(tmp_path):
    from cekirdek import kuyruk
    evet = yo.calistirilabilir(tmp_path / "evet", "#!/bin/sh\necho 'MPI enabled:           yes'\n")
    hayir = yo.calistirilabilir(tmp_path / "hayir", "#!/bin/sh\necho 'MPI enabled:           no'\n")
    bos = yo.calistirilabilir(tmp_path / "bos", "#!/bin/sh\necho 'OpenMC'\n")
    assert kuyruk.mpi_destegi(evet) is True
    assert kuyruk.mpi_destegi(hayir) is False
    assert kuyruk.mpi_destegi(bos) is None
    assert kuyruk.mpi_destegi(str(tmp_path / "yok")) is None


def test_mpi_isi_destek_yoksa_acik_hatayla_biter(tmp_path, monkeypatch):
    # Arrange: sahte openmc --version "MPI enabled: no" der
    from cekirdek import kuyruk
    k = _kuyruk(tmp_path, monkeypatch, is_parcacigi_butcesi=8)
    x = k.ekle(_is(tmp_path, "mpi", is_parcacigi=1, mpi_surec=2))
    # Act
    k.baslat()
    assert k.bekle(_BEKLEME)
    # Assert
    d = k.durum(x)
    assert d.asama == kuyruk.Asama.BASARISIZ
    assert "MPI" in d.hata
    k.kapat()


def test_mpi_isi_mpiexec_ile_baslar(tmp_path, monkeypatch):
    # Arrange: MPI destekli sahte openmc + sahte mpiexec (argumanlari kaydeder)
    from cekirdek import kuyruk
    monkeypatch.setenv("SAHTE_MPI", "yes")
    kayit = tmp_path / "mpi_arg.txt"
    mpiexec = yo.calistirilabilir(tmp_path / "bin" / "mpiexec",
                                  '#!/bin/sh\nprintf "%%s " "$@" > "%s"\nshift 2\nexec "$@"\n' % kayit)
    k = _kuyruk(tmp_path, monkeypatch, is_parcacigi_butcesi=8, mpiexec=mpiexec)
    x = k.ekle(_is(tmp_path, "mpi", is_parcacigi=2, mpi_surec=3))
    # Act
    k.baslat()
    assert k.bekle(_BEKLEME)
    # Assert
    assert k.durum(x).asama == kuyruk.Asama.BITTI, k.durum(x).hata
    assert kayit.read_text().split()[:2] == ["-n", "3"]
    k.kapat()


def test_qt_bagdastirici_olaylari_ana_iplikte_yayar(tmp_path, monkeypatch):
    # Arrange
    import threading
    from PySide6 import QtCore, QtWidgets
    from arayuz.kuyruk.bagdastirici import KuyrukBagdastirici
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    kq = KuyrukBagdastirici(_kuyruk(tmp_path, monkeypatch))
    iplikler, bitti = set(), []
    kq.durum_degisti.connect(lambda d: iplikler.add(threading.get_ident()))
    kq.hepsi_bitti.connect(lambda: bitti.append(True))
    kq.kuyruk.ekle(_is(tmp_path, "q1"))
    kq.kuyruk.ekle(_is(tmp_path, "q2"))
    # Act
    kq.kuyruk.baslat()
    assert kq.kuyruk.bekle(_BEKLEME)
    yo.bekle_kadar(lambda: (uyg.processEvents(), bool(bitti))[1], _BEKLEME)
    # Assert
    assert iplikler == {threading.get_ident()}, "yuvalar ana iplikte calismali"
    assert bitti
    kq.kapat()
    assert QtCore.QThread.currentThread() is uyg.thread()


# ---------------------------------------------------------------------------
# YAVAS: gercek kisa kosu
# ---------------------------------------------------------------------------

def test_gercek_uc_kosu_sirayla(gecici):
    # Arrange: pin hucresi, cok kisa (10 cevrim x 300 parcacik)
    from cekirdek import kuyruk, sema
    taban = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    k = kuyruk.Kuyruk(en_fazla_paralel=1)
    kimlikler = []
    for i, zen in enumerate((2.0, 3.1, 4.5)):
        spec = yo.kisa_spec(taban, zenginlik=zen)
        kimlikler.append(k.ekle(kuyruk.KosuIsi(
            ad="zen_%g" % zen, spec=spec, is_parcacigi=min(ISLEM_PARCACIGI, 6),
            dizin=kuyruk.ayri_dizin(gecici, "zen_%g" % zen))))
    # Act
    k.baslat()
    assert k.bekle(600.0)
    # Assert
    durumlar = [k.durum(x) for x in kimlikler]
    assert all(d.asama == kuyruk.Asama.BITTI for d in durumlar), [d.hata for d in durumlar]
    kler = [d.k[0] for d in durumlar]
    assert kler[0] < kler[1] < kler[2], "zenginlik arttikca k artmali: %s" % kler
    assert all(d.bitis >= d.baslangic for d in durumlar)
    for a, b in zip(durumlar, durumlar[1:]):
        assert b.baslangic >= a.bitis
    k.kapat()


HIZLI = [test_uc_kosu_sirayla_biter, test_her_kosu_ayri_dizinde_ve_ayni_dizin_reddedilir,
         test_paralel_kosu_is_parcacigi_butcesini_asmaz, test_butceyi_asan_is_reddedilir,
         test_tasi_bekleyen_isin_sirasini_degistirir,
         test_iptal_kosani_sonlandirir_bekleyeni_baslatmaz,
         test_basarisiz_kosu_sonrakini_durdurmaz, test_sonuc_kancasi_hatasi_basarisiz_sayilir,
         test_dinleyici_durum_olaylarini_alir, test_dinleyici_hatasi_kuyrugu_durdurmaz,
         test_spec_ile_is_model_xml_yazar, test_openmc_yoksa_is_basarisiz,
         test_bilinmeyen_kimlik_keyerror, test_komut_mpi_ile_ve_mpisiz,
         test_mpiexec_yolu_goreli_path_ogesini_yok_sayar,
         test_mpi_destegi_openmc_surumunden_okunur,
         test_mpi_isi_destek_yoksa_acik_hatayla_biter, test_mpi_isi_mpiexec_ile_baslar,
         test_qt_bagdastirici_olaylari_ana_iplikte_yayar]
YAVAS = [test_gercek_uc_kosu_sirayla]
