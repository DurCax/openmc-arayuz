# -*- coding: utf-8 -*-
"""
 test_y10_parametre.py  --  Y10 parametrik model (cekirdek/parametre.py) ve
                            mevcut tarama ile birlesme (cekirdek/tarama.py)
"""

import json
import os

from testler.ortak_test import ORNEK
from testler import y10_ortak as yo


def _taban():
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))


def _model(**kw):
    from cekirdek import parametre as p
    taban = _taban()
    yakit = next(m["ad"] for m in taban["malzemeler"]
                 if any(b.get("zenginlik") is not None for b in m.get("bilesim", [])))
    degiskenler = (
        p.Degisken(ad="zen", tur="zenginlik", hedef=yakit, birim="%"),
        p.Degisken(ad="n", tur=p.YOL_TURU, hedef="ayarlar.parcacik", deger=1000),
    )
    tarama = p.Tarama(degerler={"zen": (2.0, 3.0), "n": (500, 800)}, bicim=kw.pop("bicim", "kartezyen"))
    return p.ParametrikModel(ad="deneme", taban=taban, degiskenler=degiskenler, tarama=tarama), yakit


def test_parametrik_model_json_gidis_donus(tmp_path):
    # Arrange
    from cekirdek import parametre as p
    model, _yakit = _model()
    yol = str(tmp_path / "model.parametrik.json")
    # Act
    p.kaydet(model, yol)
    geri = p.yukle(yol)
    # Assert
    assert geri == model
    assert p.sozluge(geri) == p.sozluge(model)
    with open(yol, encoding="utf-8") as f:
        ham = json.load(f)
    assert ham["bicim"] == p.BICIM_ADI and ham["surum"] == p.BICIM_SURUMU
    assert not [a for a in os.listdir(tmp_path) if a != "model.parametrik.json"], \
        "atomik yazma gecici dosya birakmamali"


def test_kartezyen_ve_esli_noktalar():
    from cekirdek import parametre as p
    model, _ = _model()
    assert p.noktalar(model) == [{"zen": 2.0, "n": 500}, {"zen": 2.0, "n": 800},
                                 {"zen": 3.0, "n": 500}, {"zen": 3.0, "n": 800}]
    esli, _ = _model(bicim="esli")
    assert p.noktalar(esli) == [{"zen": 2.0, "n": 500}, {"zen": 3.0, "n": 800}]


def test_uygula_degiskenleri_spec_kopyasina_yazar():
    # Arrange
    from cekirdek import parametre as p, sema
    model, yakit = _model()
    taban_kopya = json.dumps(model.taban, sort_keys=True)
    # Act
    spec, notlar = p.uygula(model, {"zen": 4.2})
    # Assert
    m = sema.malzeme_bul(spec, yakit)
    assert [b["zenginlik"] for b in m["bilesim"] if b.get("zenginlik") is not None] == [4.2]
    assert spec["ayarlar"]["parcacik"] == 1000, "taramada olmayan degisken varsayilanini alir"
    assert isinstance(spec["ayarlar"]["parcacik"], int)
    assert json.dumps(model.taban, sort_keys=True) == taban_kopya, "taban degismemeli"
    assert notlar == []


def test_dogrulama_hatalari():
    from cekirdek import parametre as p
    taban = _taban()
    hatali = [
        lambda: p.Degisken(ad="1x", tur="zenginlik"),
        lambda: p.Degisken(ad="x", tur="bilinmeyen"),
        lambda: p.ParametrikModel(ad="m", taban=taban, degiskenler=(
            p.Degisken(ad="a", tur=p.YOL_TURU, hedef="ayarlar.parcacik"),
            p.Degisken(ad="a", tur=p.YOL_TURU, hedef="ayarlar.cevrim"))),
        lambda: p.ParametrikModel(ad="m", taban=taban, degiskenler=(), tarama=p.Tarama(
            degerler={"yok": (1,)})),
        lambda: p.Tarama(degerler={"a": (1, 2), "b": (1,)}, bicim="esli"),
        lambda: p.Tarama(degerler={"a": (1,)}, bicim="baska"),
        lambda: p.Tarama(degerler={"a": ()}),
    ]
    for i, f in enumerate(hatali):
        try:
            f()
            raise AssertionError("hatali tanim %d kabul edildi" % i)
        except ValueError:
            pass


def test_yol_uygula_sayisal_alani_degistirir_digerlerini_reddeder():
    from cekirdek import parametre as p
    spec = _taban()
    yeni = p.yol_uygula(spec, "ayarlar.entropi_mesh.boyut.0", 4)
    assert yeni["ayarlar"]["entropi_mesh"]["boyut"][0] == 4
    assert spec["ayarlar"]["entropi_mesh"]["boyut"][0] == 8
    for yol in ("ayarlar.yok", "ayarlar.mod", "ayarlar.entropi_mesh.var",
                "ayarlar.entropi_mesh.boyut.9", "", "malzemeler.x"):
        try:
            p.yol_uygula(spec, yol, 1.0)
            raise AssertionError("gecersiz yol kabul edildi: %r" % yol)
        except (KeyError, ValueError):
            pass


def test_tarama_parametre_uygula_yol_turunu_tanir():
    # Arrange: mevcut tarama mekanizmasi ayni yol turunu kullanir (birlesme)
    from cekirdek import parametre as p, tarama
    spec = _taban()
    # Act
    yeni, notu = tarama.parametre_uygula(spec, p.YOL_TURU, "ayarlar.cevrim", 77)
    # Assert
    assert yeni["ayarlar"]["cevrim"] == 77 and notu is None


def test_tarama_tanimindan_parametrik_model():
    # Arrange
    from cekirdek import parametre as p, tarama
    spec = _taban()
    yakit = next(m["ad"] for m in spec["malzemeler"]
                 if any(b.get("zenginlik") is not None for b in m.get("bilesim", [])))
    # Act
    model = tarama.parametrik_model(spec, "zenginlik", yakit, [2.0, 3.0, 4.0])
    # Assert
    assert [n["zenginlik"] for n in p.noktalar(model)] == [2.0, 3.0, 4.0]
    assert model.degiskenler[0].tur == "zenginlik" and model.degiskenler[0].hedef == yakit
    geri = p.sozlukten(json.loads(json.dumps(p.sozluge(model))))
    assert geri == model
    cy = tarama.parametrik_model(spec, "cubuk_yaricap", ("yakit_cubugu", 0), [0.4])
    assert p.sozlukten(json.loads(json.dumps(p.sozluge(cy)))).degiskenler[0].hedef == (
        "yakit_cubugu", 0)


def test_kuyruga_ekle_her_noktaya_ayri_dizin_ve_etiket(tmp_path, monkeypatch):
    # Arrange
    from cekirdek import kuyruk, parametre as p
    model, _ = _model()
    monkeypatch.setenv("SAHTE_KAYIT", str(tmp_path / "kayit.txt"))
    k = kuyruk.Kuyruk(openmc=yo.sahte_openmc(tmp_path), en_fazla_paralel=2,
                      is_parcacigi_butcesi=2)
    # Act
    kimlikler = p.kuyruga_ekle(model, k, str(tmp_path / "tarama"), is_parcacigi=1,
                               dogrulama=False, sonuc_kancasi=yo.sahte_sonuc)
    k.baslat()
    assert k.bekle(60.0)
    # Assert
    durumlar = [k.durum(x) for x in kimlikler]
    assert len(durumlar) == 4 and all(d.asama == kuyruk.Asama.BITTI for d in durumlar)
    assert len({d.dizin for d in durumlar}) == 4
    assert [d.etiket["degerler"] for d in durumlar] == p.noktalar(model)
    with open(os.path.join(durumlar[1].dizin, "spec.json"), encoding="utf-8") as f:
        assert json.load(f)["ayarlar"]["parcacik"] == 800
    k.kapat()


HIZLI = [test_parametrik_model_json_gidis_donus, test_kartezyen_ve_esli_noktalar,
         test_uygula_degiskenleri_spec_kopyasina_yazar, test_dogrulama_hatalari,
         test_yol_uygula_sayisal_alani_degistirir_digerlerini_reddeder,
         test_tarama_parametre_uygula_yol_turunu_tanir, test_tarama_tanimindan_parametrik_model,
         test_kuyruga_ekle_her_noktaya_ayri_dizin_ve_etiket]
YAVAS = []
