# -*- coding: utf-8 -*-
"""
 test_y10_gecmis.py  --  Y10 kosu gecmisi (SQLite) ve iki kosu karsilastirmasi
                         (cekirdek/kosu_gecmisi.py)
"""

import math
import os
import threading

from testler.ortak_test import ORNEK, ISLEM_PARCACIGI
from testler import y10_ortak as yo


def _kayit(kimlik, **kw):
    from cekirdek import kosu_gecmisi as kg
    alanlar = {"ad": "kosu " + kimlik, "dizin": "/tmp/" + kimlik, "durum": "bitti"}
    alanlar.update(kw)
    return kg.KosuKaydi(kimlik=kimlik, **alanlar)


def test_gecmis_gidis_donus_ve_siralama(tmp_path):
    # Arrange
    from cekirdek import kosu_gecmisi as kg
    depo = kg.GecmisDeposu(str(tmp_path / "g.sqlite3"))
    # Act
    depo.kaydet(_kayit("a", keff=1.1, sapma=0.001, kayit_ani=10.0,
                       etiket={"demet": "UO2", "nesne": object()}))
    depo.kaydet(_kayit("b", keff=None, durum="basarisiz", hata="x", kayit_ani=20.0))
    # Assert
    a = depo.getir("a")
    assert a.keff == 1.1 and a.sapma == 0.001
    assert a.etiket["demet"] == "UO2" and isinstance(a.etiket["nesne"], str)
    assert [k.kimlik for k in depo.listele()] == ["b", "a"]
    assert depo.getir("yok") is None
    assert depo.sil("a") and not depo.sil("a")
    assert [k.kimlik for k in kg.GecmisDeposu(depo.yol).listele()] == ["b"]


def test_gecmis_varsayilan_yolu_kullanici_veri_dizininde(tmp_path, monkeypatch):
    from cekirdek import kosu_gecmisi as kg
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "veri"))
    depo = kg.GecmisDeposu()
    assert depo.yol == str(tmp_path / "veri" / "openmc_arayuz" / kg.GECMIS_DOSYASI)
    assert os.path.isfile(depo.yol)


def test_gecmis_eszamanli_yazmalar_kaybolmaz(tmp_path):
    # Arrange: 8 iplik x 10 kayit ayni dosyaya
    from cekirdek import kosu_gecmisi as kg
    depo = kg.GecmisDeposu(str(tmp_path / "g.sqlite3"))

    def yaz(n):
        for i in range(10):
            depo.kaydet(_kayit("%d_%d" % (n, i)))
    iplikler = [threading.Thread(target=yaz, args=(n,)) for n in range(8)]
    # Act
    for t in iplikler:
        t.start()
    for t in iplikler:
        t.join()
    # Assert
    assert len(depo.listele(sinir=1000)) == 80


def test_gecmis_bos_kimlik_reddedilir_ve_yeni_sema_okunmaz(tmp_path):
    import sqlite3
    from cekirdek import kosu_gecmisi as kg
    depo = kg.GecmisDeposu(str(tmp_path / "g.sqlite3"))
    try:
        depo.kaydet(_kayit(""))
        raise AssertionError("bos kimlik kabul edildi")
    except ValueError:
        pass
    with sqlite3.connect(depo.yol) as bag:
        bag.execute("PRAGMA user_version = 99")
    try:
        kg.GecmisDeposu(depo.yol)
        raise AssertionError("yeni sema surumu sessizce acildi")
    except RuntimeError as e:
        assert "99" in str(e)


def test_gecmis_bozuk_etiket_bos_sayilir(tmp_path):
    import sqlite3
    from cekirdek import kosu_gecmisi as kg
    depo = kg.GecmisDeposu(str(tmp_path / "g.sqlite3"))
    depo.kaydet(_kayit("a"))
    with sqlite3.connect(depo.yol) as bag:
        bag.execute("UPDATE kosular SET etiket = '{bozuk' WHERE kimlik = 'a'")
    assert depo.getir("a").etiket == {}


def test_kuyruk_dinleyicisi_yalniz_biten_isleri_yazar(tmp_path, monkeypatch):
    # Arrange
    from cekirdek import kosu_gecmisi as kg, kuyruk
    depo = kg.GecmisDeposu(str(tmp_path / "g.sqlite3"))
    monkeypatch.setenv("SAHTE_KAYIT", str(tmp_path / "kayit.txt"))
    k = kuyruk.Kuyruk(openmc=yo.sahte_openmc(tmp_path))
    k.dinleyici_ekle(kg.gecmis_dinleyicisi(depo))
    x = k.ekle(kuyruk.KosuIsi(ad="x", dizin=yo.hazir_dizin(tmp_path / "x"),
                              sonuc_kancasi=yo.sahte_sonuc, etiket={"tur": "UO2"}))
    iptal = k.ekle(kuyruk.KosuIsi(ad="iptal", dizin=yo.hazir_dizin(tmp_path / "i")))
    k.iptal(iptal)
    # Act
    k.baslat()
    assert k.bekle(30.0)
    # Assert
    kayitlar = {r.kimlik: r for r in depo.listele()}
    assert set(kayitlar) == {x, iptal}
    assert kayitlar[x].durum == "bitti" and (kayitlar[x].keff, kayitlar[x].sapma) == yo.SAHTE_K
    assert kayitlar[x].etiket == {"tur": "UO2"} and kayitlar[x].sure >= 0
    assert kayitlar[iptal].durum == "iptal" and kayitlar[iptal].keff is None
    k.kapat()


def test_durumdan_kayit_kapsul_karmasini_okur(tmp_path):
    import json
    from cekirdek import kosu_gecmisi as kg, kuyruk
    (tmp_path / "kapsul.json").write_text(json.dumps({"spec": {"sha256": "abc"}}))
    d = kuyruk.IsDurumu(kimlik="q", ad="q", dizin=str(tmp_path), asama=kuyruk.Asama.BITTI)
    assert kg.durumdan_kayit(d).spec_sha == "abc"
    (tmp_path / "kapsul.json").write_text("{bozuk")
    assert kg.durumdan_kayit(d).spec_sha is None


# ---------------------------------------------------------------------------
# karsilastirma
# ---------------------------------------------------------------------------

def test_k_farki_z_ve_anlamlilik():
    # Arrange / Act
    from cekirdek import kosu_gecmisi as kg
    f = kg.k_farki(1.00000, 0.00030, 1.00100, 0.00040)
    # Assert: Delta = 100 pcm k, sigma = 50 pcm -> z = 2.0 (esikte: anlamli DEGIL)
    assert math.isclose(f.fark, 0.001)
    assert math.isclose(f.sigma, 0.0005)
    assert math.isclose(f.z, 2.0)
    assert not f.anlamli
    g = kg.k_farki(1.0, 0.0003, 1.0011, 0.0004)
    assert g.anlamli and g.z > 2
    assert math.isclose(f.rho_fark_pcm, (1 / 1.0 - 1 / 1.001) * 1e5)
    assert math.isclose(f.rho_sigma_pcm, 1e5 * math.hypot(0.0003, 0.0004 / 1.001 ** 2))
    assert kg.k_farki(1.0, 0.0, 1.0, 0.0).z == 0.0
    assert kg.k_farki(1.0, 0.0, 1.1, 0.0).z == math.inf
    try:
        kg.k_farki(0.0, 0.1, 1.0, 0.1)
        raise AssertionError("k = 0 kabul edildi")
    except ValueError:
        pass


def test_guc_farki_konum_konum():
    # Arrange
    from cekirdek import kosu_gecmisi as kg
    b1 = {(0, 0): (1.10, 0.01), (0, 1): (0.90, 0.01), (1, 1): (1.00, 0.01)}
    b2 = {(0, 0): (1.00, 0.01), (0, 1): (0.905, 0.01), (2, 2): (1.0, 0.01)}
    # Act
    g = kg.guc_farki(b1, b2)
    # Assert
    assert set(g.farklar) == {(0, 0), (0, 1)}
    assert math.isclose(g.farklar[(0, 0)].fark, -0.10)
    assert math.isclose(g.farklar[(0, 0)].z, -0.10 / math.hypot(0.01, 0.01))
    assert g.anlamli_sayisi == 1
    assert g.en_buyuk == (0, 0)
    assert g.yalniz1 == ((1, 1),) and g.yalniz2 == ((2, 2),)
    assert math.isclose(g.beklenen_tesaduf, 2 * 0.0455, rel_tol=1e-2)
    assert math.isclose(g.rms_fark, math.sqrt((0.1 ** 2 + 0.005 ** 2) / 2))
    bos = kg.guc_farki({}, {})
    assert bos.en_buyuk is None and bos.rms_fark == 0.0


def test_fark_izgarasi_tek_demet_tam_kor_ve_altigen():
    from cekirdek import kosu_gecmisi as kg
    tek = kg.guc_farki({(0, 0): (1, 0.1), (2, 1): (1, 0.1)}, {(0, 0): (2, 0.1), (2, 1): (1, 0.1)})
    iz = kg.fark_izgarasi(tek)
    assert (iz.nx, iz.ny) == (3, 2) and iz.hucreler[(0, 0)].fark == 1
    kor = {((1, 0), (0, 1)): (1.0, 0.1), ((0, 0), (1, 1)): (1.0, 0.1)}
    iz2 = kg.fark_izgarasi(kg.guc_farki(kor, kor))
    assert (iz2.nx, iz2.ny) == (4, 2)
    assert set(iz2.hucreler) == {(2, 1), (1, 1)}
    altigen = {("halka", 1): (1.0, 0.1)}
    assert kg.fark_izgarasi(kg.guc_farki(altigen, altigen)) is None
    assert kg.fark_izgarasi(kg.guc_farki({}, {})) is None


def test_kosulari_karsilastir_dizinlerden_okur(tmp_path):
    # Arrange: sahte okuyucu (statepoint dosyasi bos, icerigi okumaz)
    from cekirdek import kosu_gecmisi as kg
    sonuclar = {}
    for ad, k, bagil in (("a", (1.0, 0.001), {(0, 0): (1.0, 0.01)}),
                         ("b", (1.01, 0.001), {(0, 0): (1.2, 0.01)})):
        d = tmp_path / ad
        d.mkdir()
        (d / "statepoint.10.h5").write_text("")
        sonuclar[str(d / "statepoint.10.h5")] = {"keff": k, "guc": {"faktorler": {"bagil": bagil}}}
    # Act
    sonuc = kg.kosulari_karsilastir(str(tmp_path / "a"), str(tmp_path / "b"),
                                    okuyucu=sonuclar.__getitem__)
    # Assert
    assert sonuc.k.anlamli and sonuc.guc.anlamli_sayisi == 1 and not sonuc.notlar
    (tmp_path / "c").mkdir()
    try:
        kg.kosulari_karsilastir(str(tmp_path / "a"), str(tmp_path / "c"),
                                okuyucu=sonuclar.__getitem__)
        raise AssertionError("statepoint'siz dizin kabul edildi")
    except FileNotFoundError:
        pass


def test_karsilastirma_sabit_kaynak_ve_gucsuz_notlar(tmp_path):
    from cekirdek import kosu_gecmisi as kg
    for ad in ("a", "b"):
        (tmp_path / ad).mkdir()
        (tmp_path / ad / "statepoint.5.h5").write_text("")
    sonuc = kg.kosulari_karsilastir(str(tmp_path / "a"), str(tmp_path / "b"),
                                    okuyucu=lambda sp: {"keff": None})
    assert sonuc.k is None and sonuc.guc is None and len(sonuc.notlar) == 2


# ---------------------------------------------------------------------------
# YAVAS: ayni model, farkli tohum -> fark anlamsiz olmali
# ---------------------------------------------------------------------------

def test_gercek_iki_kosu_karsilastirma(gecici):
    # Arrange: 17x17 demet, guc dagilimi acik, kisa; tohum 1 ve 2
    from cekirdek import kosu_gecmisi as kg, kuyruk, sema
    taban = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    k = kuyruk.Kuyruk()
    dizinler = []
    for tohum in (1, 2):
        spec = yo.kisa_spec(taban, parcacik=2000, cevrim=25, pasif=10)
        spec["ayarlar"]["tohum"] = tohum
        spec["guc_dagilimi"] = {"var": True, "cubuk": "yakit_cubugu", "bolge": 0,
                                "skor": "kappa-fission", "eksenel_dilim": 1}
        dizinler.append(os.path.join(gecici, "tohum_%d" % tohum))
        k.ekle(kuyruk.KosuIsi(ad="t%d" % tohum, spec=spec, dizin=dizinler[-1],
                              is_parcacigi=min(ISLEM_PARCACIGI, 6)))
    k.baslat()
    assert k.bekle(900.0)
    assert all(d.asama == kuyruk.Asama.BITTI for d in k.durumlar()), [
        d.hata for d in k.durumlar()]
    # Act
    sonuc = kg.kosulari_karsilastir(*dizinler)
    # Assert
    assert abs(sonuc.k.z) < 4.0, sonuc.k
    assert sonuc.guc is not None and len(sonuc.guc.farklar) > 200
    assert sonuc.guc.anlamli_sayisi < 0.2 * len(sonuc.guc.farklar), sonuc.guc.anlamli_sayisi
    k.kapat()


HIZLI = [test_gecmis_gidis_donus_ve_siralama, test_gecmis_varsayilan_yolu_kullanici_veri_dizininde,
         test_gecmis_eszamanli_yazmalar_kaybolmaz,
         test_gecmis_bos_kimlik_reddedilir_ve_yeni_sema_okunmaz,
         test_gecmis_bozuk_etiket_bos_sayilir, test_kuyruk_dinleyicisi_yalniz_biten_isleri_yazar,
         test_durumdan_kayit_kapsul_karmasini_okur, test_k_farki_z_ve_anlamlilik,
         test_guc_farki_konum_konum, test_fark_izgarasi_tek_demet_tam_kor_ve_altigen,
         test_kosulari_karsilastir_dizinlerden_okur,
         test_karsilastirma_sabit_kaynak_ve_gucsuz_notlar]
YAVAS = [test_gercek_iki_kosu_karsilastirma]
