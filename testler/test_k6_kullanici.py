# -*- coding: utf-8 -*-
"""
 test_k6_kullanici.py  --  v3 K6: kullanici malzeme kutuphanesi
                           (cekirdek/malzeme_kullanici.py; yalniz yerel dosya)

  - yol: $XDG_DATA_HOME/openmc_arayuz/malzemeler.json (yollar.kullanici_veri_dizini)
  - atomik yazma: gecici dosya + os.replace; yazma yarida kesilirse eski dosya saglam
  - bozuk JSON / sema hatasi: acik hata, dosya SILINMEZ, istenince yedeklenir
  - surum alani: daha yeni surumlu dosya okunmaz ve UZERINE YAZILMAZ
  - degismezlik: ekle/guncelle/sil yeni demet dondurur
"""

import json
import os
import tempfile

import pytest

from testler.ortak_test import KOK  # noqa: F401


def _gecici_dizin():
    return tempfile.mkdtemp(prefix="k6_kutup_")


def _uo2(ad="benim_uo2"):
    from cekirdek import malzeme_kutup as mk
    m = mk.uo2(zenginlik=4.0)
    m["ad"] = ad
    return m


def test_yol_xdg_veri_dizininden():
    from cekirdek import malzeme_kullanici as mku
    yol = mku.varsayilan_yol(ortam={"XDG_DATA_HOME": "/abs/veri"})
    assert yol == "/abs/veri/openmc_arayuz/malzemeler.json"


def test_dosya_yoksa_bos_kutuphane():
    from cekirdek import malzeme_kullanici as mku
    assert mku.yukle(os.path.join(_gecici_dizin(), "yok", "malzemeler.json")) == ()


def test_kaydet_yukle_gidis_donus_ve_surum():
    from cekirdek import malzeme_kullanici as mku
    yol = os.path.join(_gecici_dizin(), "alt", "malzemeler.json")
    k = mku.ekle((), mku.kayit_olustur(_uo2(), aciklama="deneme", kaynak="asistan"))
    mku.kaydet(k, yol)
    with open(yol, encoding="utf-8") as f:
        ham = json.load(f)
    assert ham["surum"] == mku.SURUM and len(ham["malzemeler"]) == 1
    geri = mku.yukle(yol)
    assert geri == k
    assert geri[0]["malzeme"]["bilesim"] == _uo2()["bilesim"]


def test_degismez_islemler():
    from cekirdek import malzeme_kullanici as mku
    bos = ()
    bir = mku.ekle(bos, mku.kayit_olustur(_uo2("a")))
    iki = mku.ekle(bir, mku.kayit_olustur(_uo2("b")))
    assert bos == () and len(bir) == 1 and len(iki) == 2
    with pytest.raises(ValueError):
        mku.ekle(iki, mku.kayit_olustur(_uo2("a")))           # ayni ad
    yeni = mku.guncelle(iki, "a", mku.kayit_olustur(_uo2("a2"), aciklama="x"))
    assert [k["ad"] for k in yeni] == ["a2", "b"] and [k["ad"] for k in iki] == ["a", "b"]
    assert iki[0]["malzeme"]["ad"] == "a"                      # girdi degismedi
    assert [k["ad"] for k in mku.sil(yeni, "b")] == ["a2"]
    with pytest.raises(KeyError):
        mku.sil(yeni, "yok")


def test_atomik_yazma_yarida_kesilirse_eski_dosya_saglam():
    from unittest import mock
    from cekirdek import malzeme_kullanici as mku
    yol = os.path.join(_gecici_dizin(), "malzemeler.json")
    eski = mku.ekle((), mku.kayit_olustur(_uo2("eski")))
    mku.kaydet(eski, yol)

    with mock.patch.object(mku.os, "replace", side_effect=OSError("disk dolu")):
        with pytest.raises(mku.KutuphaneHatasi):
            mku.kaydet(mku.ekle(eski, mku.kayit_olustur(_uo2("yeni"))), yol)
    assert [k["ad"] for k in mku.yukle(yol)] == ["eski"]
    # gecici dosya ortada kalmaz
    assert [f for f in os.listdir(os.path.dirname(yol)) if f.endswith(".tmp")] == []


def test_onceki_surum_yedegi():
    from cekirdek import malzeme_kullanici as mku
    yol = os.path.join(_gecici_dizin(), "malzemeler.json")
    bir = mku.ekle((), mku.kayit_olustur(_uo2("a")))
    mku.kaydet(bir, yol)
    mku.kaydet(mku.ekle(bir, mku.kayit_olustur(_uo2("b"))), yol)
    assert [k["ad"] for k in mku.yukle(yol + mku.ONCEKI_EKI)] == ["a"]


def test_bozuk_json_acik_hata_silinmez_yedeklenir():
    from cekirdek import malzeme_kullanici as mku
    yol = os.path.join(_gecici_dizin(), "malzemeler.json")
    with open(yol, "w", encoding="utf-8") as f:
        f.write('{"surum": 1, "malzemeler": [')            # yarim JSON
    with pytest.raises(mku.KutuphaneBozuk) as hata:
        mku.yukle(yol)
    assert yol in str(hata.value)
    assert os.path.exists(yol)                              # sessiz silme yok
    yedek = mku.bozuk_dosyayi_yedekle(yol)
    assert os.path.exists(yol) and os.path.exists(yedek) and yedek != yol
    with open(yedek, encoding="utf-8") as f:
        assert f.read().startswith('{"surum": 1')


_HATALI_SEMALAR = (
    [],
    {"malzemeler": []},
    {"surum": "1", "malzemeler": []},
    {"surum": 1, "malzemeler": {}},
    {"surum": 1, "malzemeler": [{"ad": "x"}]},
)


def _malzemeli(m):
    return {"surum": 1, "malzemeler": [{"ad": m.get("ad", "x"), "aciklama": "", "kaynak": "",
                                        "olusturma": "", "guncelleme": "", "malzeme": m}]}


def test_sema_dogrulama_hatali_kayitlari_reddeder():
    from cekirdek import malzeme_kullanici as mku
    iyi = _uo2("x")
    bozuklar = list(_HATALI_SEMALAR) + [
        _malzemeli(dict(iyi, bilesim=[])),
        _malzemeli(dict(iyi, bilesim=[{"tur": "element", "isim": "U", "miktar": -1, "birim": "ao"}])),
        _malzemeli(dict(iyi, bilesim=[{"tur": "atom", "isim": "U", "miktar": 1, "birim": "ao"}])),
        _malzemeli(dict(iyi, bilesim=[{"tur": "element", "isim": "U", "miktar": 1, "birim": "%"}])),
        _malzemeli(dict(iyi, yogunluk={"birim": "g/cm3", "deger": -2})),
        _malzemeli(dict(iyi, yogunluk={"birim": "ton", "deger": 2})),
        _malzemeli(dict(iyi, yogunluk={"birim": "g/cm3", "deger": float("nan")})),
        _malzemeli(dict(iyi, ad="")),
        _malzemeli(dict(iyi, sab="c_H_in_H2O")),
        _malzemeli(dict(iyi, renk=[300, 0, 0])),
    ]
    for i, icerik in enumerate(bozuklar):
        yol = os.path.join(_gecici_dizin(), "malzemeler.json")
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(icerik, f)
        with pytest.raises(mku.KutuphaneBozuk):
            mku.yukle(yol)
        assert os.path.exists(yol), i
    # gecersiz kayit kaydedilmez de
    with pytest.raises(ValueError):
        mku.kaydet((mku.kayit_olustur(dict(iyi, bilesim=[])),),
                   os.path.join(_gecici_dizin(), "m.json"))


def test_yeni_surumlu_dosya_okunmaz_uzerine_yazilmaz():
    from cekirdek import malzeme_kullanici as mku
    yol = os.path.join(_gecici_dizin(), "malzemeler.json")
    ham = {"surum": mku.SURUM + 1, "malzemeler": []}
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(ham, f)
    with pytest.raises(mku.KutuphaneBozuk, match="sürüm"):
        mku.yukle(yol)
    with pytest.raises(mku.KutuphaneHatasi):
        mku.kaydet((), yol)
    with open(yol, encoding="utf-8") as f:
        assert json.load(f) == ham


def test_projeye_aktar_benzersiz_ad_ve_kopya():
    from cekirdek import malzeme_kullanici as mku
    from cekirdek import sema
    spec = sema.yeni_spec()
    kayit = mku.kayit_olustur(_uo2("uo2"))
    spec["malzemeler"].append(_uo2("uo2"))
    m = mku.projeye_aktar(kayit, spec)
    assert m["ad"] != "uo2" and m["ad"].startswith("uo2")
    assert m["bilesim"] == kayit["malzeme"]["bilesim"]
    m["bilesim"][0]["miktar"] = 99.0
    assert kayit["malzeme"]["bilesim"][0]["miktar"] == 1.0   # derin kopya
    assert sema.malzeme_adi_sorunu(spec, m["ad"]) is None


def test_benzersiz_kayit_adi():
    from cekirdek import malzeme_kullanici as mku
    k = mku.ekle(mku.ekle((), mku.kayit_olustur(_uo2("a"))), mku.kayit_olustur(_uo2("a_2")))
    assert mku.benzersiz_kayit_adi(k, "b") == "b"
    assert mku.benzersiz_kayit_adi(k, "a") == "a_3"


# ---------------------------------------------------------------------------
# Inceleme duzeltmeleri (guvenlik HIGH/MEDIUM)
# ---------------------------------------------------------------------------

def test_bozuk_dosya_uzerine_kaydet_onceki_saglam_kalir(tmp_path):
    from cekirdek import malzeme_kullanici as mku
    yol = str(tmp_path / "malzemeler.json")
    saglam = mku.ekle((), mku.kayit_olustur(_uo2("saglam")))
    mku.kaydet(saglam, yol)
    mku.kaydet(mku.ekle(saglam, mku.kayit_olustur(_uo2("ikinci"))), yol)
    assert [k["ad"] for k in mku.yukle(yol + mku.ONCEKI_EKI)] == ["saglam"]
    with open(yol, "w", encoding="utf-8") as f:
        f.write("{bozuk")
    mku.kaydet((), yol)                                     # bozuk dosyanin ustune
    # son SAGLAM yedek bozuk icerikle ezilmedi (eski kod bozugu .onceki'ye kopyalardi)
    assert [k["ad"] for k in mku.yukle(yol + mku.ONCEKI_EKI)] == ["saglam"]


def test_onceki_sembolik_baglantiysa_yazma_reddedilir(tmp_path):
    from cekirdek import malzeme_kullanici as mku
    yol = str(tmp_path / "malzemeler.json")
    mku.kaydet(mku.ekle((), mku.kayit_olustur(_uo2("a"))), yol)
    hedef = tmp_path / "baska.txt"
    hedef.write_text("dokunma")
    os.symlink(str(hedef), yol + mku.ONCEKI_EKI)
    with pytest.raises(mku.KutuphaneHatasi):
        mku.kaydet((), yol)
    assert hedef.read_text() == "dokunma"
    assert [k["ad"] for k in mku.yukle(yol)] == ["a"]


def test_asiri_buyuk_ve_derin_json_kutuphane_bozuk(tmp_path, monkeypatch):
    from cekirdek import malzeme_kullanici as mku
    yol = str(tmp_path / "malzemeler.json")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("[" * 200000 + "]" * 200000)                 # RecursionError
    with pytest.raises(mku.KutuphaneBozuk):
        mku.yukle(yol)
    monkeypatch.setattr(mku, "AZAMI_BOYUT", 10)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump({"surum": 1, "malzemeler": []}, f)
    with pytest.raises(mku.KutuphaneBozuk, match="büyük"):
        mku.yukle(yol)


def test_sinirlar_ve_beyaz_liste(tmp_path):
    from cekirdek import malzeme_kullanici as mku
    m = _uo2("x")
    for bozuk in (dict(m, bilinmeyen=1),
                  dict(m, bilesim=[dict(m["bilesim"][0], fazla=1)]),
                  dict(m, bilesim=[{"tur": "element", "isim": "Xx", "miktar": 1, "birim": "ao"}]),
                  dict(m, bilesim=[{"tur": "nuklid", "isim": "U", "miktar": 1, "birim": "ao"}]),
                  dict(m, bilesim=[{"tur": "element", "isim": "U", "miktar": float("inf"),
                                    "birim": "ao"}]),
                  dict(m, ad="a\nb"), dict(m, ad="x" * 500)):
        assert mku.malzeme_sorunu(bozuk), bozuk
    k = mku.kayit_olustur(m)
    assert mku._kayit_sorunu(dict(k, ad="baska")) is not None   # kayit adi = malzeme adi
    with pytest.raises(ValueError):
        mku.ekle((), {"malzeme": m})                            # ad yok: acik hata
    with pytest.raises(ValueError):
        mku.guncelle((k,), "x", {"malzeme": m})


def test_degistir_kilit_altinda_oku_yaz(tmp_path):
    from cekirdek import malzeme_kullanici as mku
    yol = str(tmp_path / "alt" / "malzemeler.json")
    mku.degistir(lambda k: mku.ekle(k, mku.kayit_olustur(_uo2("a"))), yol)
    mku.degistir(lambda k: mku.ekle(k, mku.kayit_olustur(_uo2("b"))), yol)
    assert [k["ad"] for k in mku.yukle(yol)] == ["a", "b"]
    assert os.path.exists(yol + mku.KILIT_EKI)
    assert oct(os.stat(os.path.dirname(yol)).st_mode & 0o777) == oct(0o700)


HIZLI = [test_bozuk_dosya_uzerine_kaydet_onceki_saglam_kalir,
         test_onceki_sembolik_baglantiysa_yazma_reddedilir,
         test_asiri_buyuk_ve_derin_json_kutuphane_bozuk, test_sinirlar_ve_beyaz_liste,
         test_degistir_kilit_altinda_oku_yaz,
         test_benzersiz_kayit_adi, test_yol_xdg_veri_dizininden, test_dosya_yoksa_bos_kutuphane,
         test_kaydet_yukle_gidis_donus_ve_surum, test_degismez_islemler,
         test_onceki_surum_yedegi, test_bozuk_json_acik_hata_silinmez_yedeklenir,
         test_sema_dogrulama_hatali_kayitlari_reddeder,
         test_yeni_surumlu_dosya_okunmaz_uzerine_yazilmaz,
         test_projeye_aktar_benzersiz_ad_ve_kopya]
