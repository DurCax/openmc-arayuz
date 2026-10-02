# -*- coding: utf-8 -*-
"""
 test_k4_yerel_k.py  --  K4 yerel k (cekirdek/yerel_k.py)

 Hizli testler: kafes duzeni (mesh hizalama), tally tanimi (spec'e ekleme,
 girdi degismez), oran ve sigma hesabi sentetik OpenMC DataFrame'iyle,
 agirlikli ortalama ozdesligi. YAVAS: sonsuz kafeste (yansitici 17x17 demet)
 net yok olma agirlikli yerel k ortalamasi = k-sonsuz (2 sigma).
"""

import copy
import math
import os

import pandas as pd
import pytest

from testler.ortak_test import ORNEK, ISLEM_PARCACIGI


def _ornek(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _sentetik_df(degerler):
    """degerler: {(x, y): {skor: (ort, sapma)}} -> OpenMC bicimli mesh DataFrame
    (1 tabanli x/y/z, MultiIndex sutunlar; olculdu: OpenMC 0.16)."""
    satirlar = []
    for (x, y), skorlar in sorted(degerler.items()):
        for skor, (ort, sap) in skorlar.items():
            satirlar.append((x + 1, y + 1, 1, "total", skor, ort, sap))
    sutunlar = pd.MultiIndex.from_tuples(
        [("mesh 1", "x"), ("mesh 1", "y"), ("mesh 1", "z"), ("nuclide", ""),
         ("score", ""), ("mean", ""), ("std. dev.", "")])
    return pd.DataFrame(satirlar, columns=sutunlar)


# ---------------------------------------------------------------------------
# kafes duzeni
# ---------------------------------------------------------------------------

def test_pin_hucresinde_tek_bin_adim_kadar():
    # Arrange
    from cekirdek import yerel_k
    spec = _ornek("pwr_pinhucre")
    # Act
    d = yerel_k.kafes_duzeni(spec, "pin")
    # Assert
    assert d.boyut == (1, 1)
    assert d.adim == pytest.approx((1.26, 1.26))
    assert d.alt[:2] == pytest.approx((-0.63, -0.63))
    assert d.ust[:2] == pytest.approx((0.63, 0.63))


def test_tek_demette_pin_duzeyi_17x17_demet_duzeyi_tek_bin():
    # Arrange
    from cekirdek import yerel_k
    spec = _ornek("pwr_17x17")
    # Act
    pin = yerel_k.kafes_duzeni(spec, "pin")
    demet = yerel_k.kafes_duzeni(spec, "demet")
    # Assert
    assert pin.boyut == (17, 17) and pin.adim == pytest.approx((1.26, 1.26))
    assert pin.alt[:2] == pytest.approx((-10.71, -10.71))
    assert demet.boyut == (1, 1) and demet.adim == pytest.approx((21.42, 21.42))
    assert pin.alt[2] < -1e9 and pin.ust[2] > 1e9, "2B modelde z sinirsiz olmali"


def test_kor_kafesinde_demet_ve_pin_duzeyi_hizali():
    # Arrange
    from cekirdek import yerel_k
    spec = _ornek("pwr_ceyrek_kor")
    # Act
    demet = yerel_k.kafes_duzeni(spec, "demet")
    pin = yerel_k.kafes_duzeni(spec, "pin")
    # Assert
    assert demet.boyut == (6, 6) and demet.adim == pytest.approx((21.42, 21.42))
    assert pin.boyut == (102, 102) and pin.adim == pytest.approx((1.26, 1.26))
    assert pin.alt[:2] == pytest.approx(demet.alt[:2])
    assert demet.alt[2] == pytest.approx(-120.0) and demet.ust[2] == pytest.approx(120.0)


def test_demet_arasi_bosluklu_korda_pin_duzeyi_acik_hata():
    # Arrange: BEAVRS demet adimi 21.50364 != 17 x 1.25984
    from cekirdek import yerel_k
    spec = _ornek("pwr_beavrs_kor")
    # Act / Assert
    assert yerel_k.kafes_duzeni(spec, "demet").boyut == (15, 15)
    with pytest.raises(yerel_k.YerelKHatasi) as e:
        yerel_k.kafes_duzeni(spec, "pin")
    assert "demet" in str(e.value)


def test_altigen_kafes_acik_hatayla_reddedilir():
    # Arrange
    from cekirdek import yerel_k
    spec = _ornek("vver1000_demet")
    # Act / Assert
    with pytest.raises(yerel_k.YerelKHatasi):
        yerel_k.kafes_duzeni(spec, "pin")


def test_bilinmeyen_duzey_reddedilir():
    from cekirdek import yerel_k
    with pytest.raises(yerel_k.YerelKHatasi):
        yerel_k.kafes_duzeni(_ornek("pwr_17x17"), "plaka")


# ---------------------------------------------------------------------------
# tally tanimi
# ---------------------------------------------------------------------------

def test_tally_ekle_yeni_spec_dondurur_girdiyi_degistirmez():
    # Arrange
    from cekirdek import yerel_k
    spec = _ornek("pwr_17x17")
    once = copy.deepcopy(spec)
    # Act
    yeni = yerel_k.tally_ekle(spec, "pin")
    # Assert
    assert spec == once, "girdi spec degismemeli"
    adlar = [t["ad"] for t in yeni["tallyler"]]
    assert yerel_k.TALLY_ADLARI["pin"] in adlar and yerel_k.TOPLAM_TALLY in adlar
    t = next(t for t in yeni["tallyler"] if t["ad"] == yerel_k.TALLY_ADLARI["pin"])
    f = t["filtreler"][0]
    assert f["tur"] == "mesh" and f["boyut"] == [17, 17, 1] and f["otomatik"] is False
    assert f["alt"][:2] == pytest.approx([-10.71, -10.71])
    assert {"nu-fission", "absorption", "(n,2n)"} <= set(t["skorlar"])


def test_tally_ekle_iki_kez_cagrilinca_tek_kopya_kalir():
    from cekirdek import yerel_k
    spec = yerel_k.tally_ekle(yerel_k.tally_ekle(_ornek("pwr_17x17"), "pin"), "pin")
    adlar = [t["ad"] for t in spec["tallyler"]]
    assert adlar.count(yerel_k.TALLY_ADLARI["pin"]) == 1
    assert adlar.count(yerel_k.TOPLAM_TALLY) == 1


def test_tally_skorlari_dogrulamadan_uyarisiz_gecer():
    # Arrange
    from cekirdek import yerel_k
    from cekirdek.dogrula.referans import tally_kontrol
    # Act
    bulgular = tally_kontrol(yerel_k.tally_ekle(_ornek("pwr_17x17"), "demet"))
    # Assert
    assert bulgular == [], bulgular


def test_xn_skor_adlari_openmc_tepki_adlariyla_ayni():
    import openmc.data
    from cekirdek import yerel_k
    for skor, df_adi, _x in yerel_k.XN_SKORLARI:
        mt = int(skor) if skor.isdigit() else None
        if mt is not None:
            assert openmc.data.REACTION_NAME[mt] == df_adi
        else:
            assert skor == df_adi


def test_tally_kurucudan_ve_betikten_gecer():
    # Arrange: kurucu (model) ve betik ayni tally'yi uretmeli
    from cekirdek import kurucu, yerel_k
    from cekirdek import kod_uret
    spec = yerel_k.tally_ekle(_ornek("pwr_17x17"), "pin")
    # Act
    model, _b = kurucu.kur(spec)
    betik = kod_uret.uret(spec)
    # Assert
    adlar = [t.name for t in model.tallies]
    assert yerel_k.TALLY_ADLARI["pin"] in adlar
    assert yerel_k.TALLY_ADLARI["pin"] in betik


# ---------------------------------------------------------------------------
# hesap
# ---------------------------------------------------------------------------

def test_yerel_k_orani_ve_xn_duzeltmesi():
    # Arrange: P=1.2, A=1.0, (n,2n)=0.01 -> k = 1.2 / (1.0 - 0.01)
    from cekirdek import yerel_k
    df = _sentetik_df({(0, 0): {"nu-fission": (1.2, 0.012), "absorption": (1.0, 0.01),
                                "(n,2n)": (0.01, 0.001)}})
    # Act
    s = yerel_k.hesapla(df, "pin", (1, 1), (1.26, 1.26))
    # Assert
    h = s.hucreler[0]
    assert h.k == pytest.approx(1.2 / 0.99)
    beklenen = h.k * math.sqrt(0.01 ** 2 + (math.sqrt(0.01 ** 2 + 0.001 ** 2) / 0.99) ** 2)
    assert h.sigma == pytest.approx(beklenen)
    assert h.k_xn_siz == pytest.approx(1.2)
    assert s.c_xn == pytest.approx(1.0 / 0.99)


def test_coklu_kanal_net_uretimi_x_eksi_bir_ile_agirliklanir():
    from cekirdek import yerel_k
    df = _sentetik_df({(0, 0): {"nu-fission": (1.0, 0.0), "absorption": (1.0, 0.0),
                                "(n,2n)": (0.01, 0.0), "(n,3n)": (0.01, 0.0),
                                "(n,2nd)": (0.01, 0.0)}})
    s = yerel_k.hesapla(df, "pin", (1, 1), (1.0, 1.0))
    assert s.hucreler[0].yok_olma[0] == pytest.approx(1.0 - 0.01 - 0.02 - 0.01)


def test_yakitsiz_bin_fisil_degil_ama_ortalamaya_payda_olarak_girer():
    # Arrange: yakit (P=2, A=1) + kilavuz boru (P=0, A=0.5)
    from cekirdek import yerel_k
    df = _sentetik_df({(0, 0): {"nu-fission": (2.0, 0.02), "absorption": (1.0, 0.01)},
                       (1, 0): {"nu-fission": (0.0, 0.0), "absorption": (0.5, 0.01)}})
    # Act
    s = yerel_k.hesapla(df, "pin", (2, 1), (1.0, 1.0))
    # Assert
    yakit, boru = s.hucreler
    assert yakit.fisil and not boru.fisil
    assert boru.k == 0.0
    assert s.ortalama[0] == pytest.approx(2.0 / 1.5)


def test_net_yok_olma_agirlikli_ortalama_uretim_toplami_oranina_esit():
    # Arrange: rastgele binler; ozdeslik: sum(D_i k_i)/sum(D_i) = sum P / sum D
    import random
    from cekirdek import yerel_k
    r = random.Random(7)
    deg = {(i, j): {"nu-fission": (r.uniform(0.5, 2.0), 0.01),
                    "absorption": (r.uniform(0.5, 1.5), 0.01),
                    "(n,2n)": (r.uniform(0.0, 0.01), 0.0)}
           for i in range(3) for j in range(3)}
    # Act
    s = yerel_k.hesapla(_sentetik_df(deg), "pin", (3, 3), (1.0, 1.0))
    # Assert
    agirlikli = (sum(h.yok_olma[0] * h.k for h in s.hucreler)
                 / sum(h.yok_olma[0] for h in s.hucreler))
    harmonik = (sum(h.uretim[0] for h in s.hucreler)
                / sum(h.uretim[0] / h.k for h in s.hucreler if h.k > 0))
    assert s.ortalama[0] == pytest.approx(agirlikli)
    assert s.ortalama[0] == pytest.approx(harmonik), "uretim agirlikli harmonik ortalama"


def test_model_toplami_ve_kapsama_orani():
    # Arrange: harita D toplami 1.5, model toplami (yansitici dahil) 2.0
    from cekirdek import yerel_k
    df = _sentetik_df({(0, 0): {"nu-fission": (2.0, 0.0), "absorption": (1.5, 0.0)}})
    toplam = pd.DataFrame({"nuclide": ["total", "total"],
                           "score": ["nu-fission", "absorption"],
                           "mean": [2.0, 2.0], "std. dev.": [0.0, 0.0]})
    # Act
    s = yerel_k.hesapla(df, "pin", (1, 1), (1.0, 1.0), toplam_df=toplam)
    # Assert
    assert s.model_toplami[0] == pytest.approx(1.0)
    assert s.kapsama == pytest.approx(0.75)


def test_eksik_skor_acik_hata():
    from cekirdek import yerel_k
    df = _sentetik_df({(0, 0): {"nu-fission": (1.0, 0.0)}})
    with pytest.raises(yerel_k.YerelKHatasi):
        yerel_k.hesapla(df, "pin", (1, 1), (1.0, 1.0))


def test_sonuctan_tally_yoksa_none_varsa_sonuc():
    # Arrange
    from cekirdek import yerel_k
    spec = yerel_k.tally_ekle(_ornek("pwr_17x17"), "demet")
    df = _sentetik_df({(0, 0): {"nu-fission": (1.2, 0.0), "absorption": (1.0, 0.0)}})
    # Act
    yok = yerel_k.sonuctan({"tallyler": {}}, spec)
    var = yerel_k.sonuctan({"tallyler": {yerel_k.TALLY_ADLARI["demet"]: df},
                            "keff": (1.2, 0.001)}, spec)
    # Assert
    assert yok == []
    assert len(var) == 1 and var[0].duzey == "demet"
    assert var[0].keff == (1.2, 0.001)
    assert var[0].ortalama[0] == pytest.approx(1.2)


def test_csv_satirlari_her_bin_icin_bir_satir():
    from cekirdek import yerel_k
    df = _sentetik_df({(0, 0): {"nu-fission": (2.0, 0.02), "absorption": (1.0, 0.01)},
                       (1, 0): {"nu-fission": (0.0, 0.0), "absorption": (0.5, 0.01)}})
    s = yerel_k.hesapla(df, "pin", (2, 1), (1.0, 1.0))
    metin = yerel_k.csv_metni(s)
    satirlar = metin.strip().splitlines()
    assert len(satirlar) == 3 and satirlar[0].startswith("x,y")


def test_terminal_ekle_yeni_model_dosyasi_yazar(tmp_path):
    # Arrange
    from cekirdek import sema, yerel_k
    cikti = tmp_path / "yk.json"
    # Act
    kod = yerel_k.terminal(["ekle", os.path.join(ORNEK, "pwr_17x17.json"), "pin",
                            "-o", str(cikti)])
    # Assert
    assert kod == 0
    adlar = [t["ad"] for t in sema.yukle(str(cikti))["tallyler"]]
    assert yerel_k.TALLY_ADLARI["pin"] in adlar


def test_terminal_desteksiz_modelde_hata_kodu(tmp_path, capsys):
    from cekirdek import yerel_k
    kod = yerel_k.terminal(["ekle", os.path.join(ORNEK, "vver1000_demet.json"), "pin",
                            "-o", str(tmp_path / "x.json")])
    assert kod == 1 and "altıgen" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# YAVAS: sonsuz kafeste ortalama = k-sonsuz

# ---------------------------------------------------------------------------
# duzeltme turu (profesor + python-reviewer)
# ---------------------------------------------------------------------------

def test_harmonik_esdegerlik_yakitsiz_binin_d_si_ayrica_eklenir():
    # Arrange: iki yakit bini + bir kilavuz boru (P = 0)
    from cekirdek import yerel_k
    df = _sentetik_df({(0, 0): {"nu-fission": (2.0, 0.0), "absorption": (1.0, 0.0)},
                       (1, 0): {"nu-fission": (1.5, 0.0), "absorption": (1.2, 0.0)},
                       (2, 0): {"nu-fission": (0.0, 0.0), "absorption": (0.4, 0.0)}})
    # Act
    s = yerel_k.hesapla(df, "pin", (3, 1), (1.0, 1.0))
    # Assert
    fisil = [h for h in s.hucreler if h.fisil]
    yalniz_fisil = sum(h.uretim[0] for h in fisil) / sum(h.uretim[0] / h.k for h in fisil)
    duzeltilmis = sum(h.uretim[0] for h in s.hucreler) / (
        sum(h.uretim[0] / h.k for h in fisil)
        + sum(h.yok_olma[0] for h in s.hucreler if not h.fisil))
    assert s.ortalama[0] == pytest.approx(duzeltilmis)
    assert s.ortalama[0] != pytest.approx(yalniz_fisil), "P=0 binin D'si eklenmeli"


def test_uretimsiz_binin_sigmasi_payin_belirsizliginden():
    from cekirdek import yerel_k
    df = _sentetik_df({(0, 0): {"nu-fission": (0.0, 0.02), "absorption": (0.5, 0.01)}})
    h = yerel_k.hesapla(df, "pin", (1, 1), (1.0, 1.0)).hucreler[0]
    assert h.k == 0.0 and h.sigma == pytest.approx(0.04) and not h.fisil


def test_sifir_yok_olmali_bin_fisil_sayilmaz_nan():
    from cekirdek import yerel_k
    df = _sentetik_df({(0, 0): {"nu-fission": (1.0, 0.0), "absorption": (0.0, 0.0)}})
    h = yerel_k.hesapla(df, "pin", (1, 1), (1.0, 1.0)).hucreler[0]
    assert math.isnan(h.k) and not h.fisil


def test_mesh_olcusu_kayitli_tallyden_okunur_uyusmazlik_hata():
    # Arrange: kosu 2x1 mesh'le yapildi; spec'teki tanim 17x17 (model degismis)
    from cekirdek import yerel_k
    spec = yerel_k.tally_ekle(_ornek("pwr_17x17"), "pin")
    df = _sentetik_df({(0, 0): {"nu-fission": (1.0, 0.0), "absorption": (1.0, 0.0)},
                       (1, 0): {"nu-fission": (1.0, 0.0), "absorption": (1.0, 0.0)}})
    # Act / Assert
    with pytest.raises(yerel_k.YerelKHatasi):
        yerel_k.sonuctan({"tallyler": {yerel_k.TALLY_ADLARI["pin"]: df}}, spec)
    yok = _ornek("pwr_17x17")
    with pytest.raises(yerel_k.YerelKHatasi):
        yerel_k.sonuctan({"tallyler": {yerel_k.TALLY_ADLARI["pin"]: df}}, yok)


def test_tally_duzeni_kayitli_tanimdan_adim_ve_boyut():
    from cekirdek import yerel_k
    spec = yerel_k.tally_ekle(_ornek("pwr_ceyrek_kor"), "demet")
    d = yerel_k.tally_duzeni(spec, "demet")
    assert d.boyut == (6, 6) and d.adim == pytest.approx((21.42, 21.42))
    assert yerel_k.tally_duzeni(spec, "pin") is None


def test_ayni_adli_kullanici_tallysi_silinmez_hata():
    # Arrange
    from cekirdek import yerel_k
    spec = _ornek("pwr_17x17")
    spec["tallyler"].append({"ad": "yerel_k_pin", "skorlar": ["flux"], "filtreler": [],
                             "nuklidler": []})
    # Act / Assert
    with pytest.raises(yerel_k.YerelKHatasi):
        yerel_k.tally_ekle(spec, "pin")


def test_tally_ekle_yalniz_tally_listesini_yeniler_ve_kayitta_isaret_kalir(tmp_path):
    # Arrange
    from cekirdek import sema, yerel_k
    spec = _ornek("pwr_17x17")
    # Act
    yeni = yerel_k.tally_ekle(spec, "pin")
    yol = str(tmp_path / "m.json")
    sema.kaydet(yeni, yol)
    geri = sema.yukle(yol)
    # Assert
    assert yeni["tallyler"] is not spec["tallyler"] and yeni["malzemeler"] is spec["malzemeler"]
    isaretli = [t["ad"] for t in geri["tallyler"] if t.get("uretici") == yerel_k.URETICI]
    assert sorted(isaretli) == sorted([yerel_k.TALLY_ADLARI["pin"], yerel_k.TOPLAM_TALLY])
    assert yerel_k.tally_kaldir(geri)["tallyler"] == spec["tallyler"]


def test_donusumlu_kafes_reddedilir():
    from cekirdek import yerel_k
    spec = _ornek("pwr_ceyrek_kor")
    spec["kor"] = dict(spec["kor"])
    import cekirdek.geometri as geo
    agac = geo.genislet(spec)
    agac["kok"]["ic"]["icerik"]["donusum"] = {"donme": 30.0}
    spec2 = dict(spec, kor={"tur": "agac"}, geometri=agac)
    with pytest.raises(yerel_k.YerelKHatasi):
        yerel_k.kafes_duzeni(spec2, "demet")


def test_aktif_eksenel_kapsam_yalniz_fisil_aralik():
    from cekirdek import geometri, yerel_k
    spec = _ornek("pwr_ceyrek_kor")
    model = yerel_k.kafes_duzeni(spec, "demet")
    aktif = yerel_k.kafes_duzeni(spec, "demet", z_kapsam="aktif")
    z0, z1 = geometri.aktif_aralik(spec)
    assert (aktif.alt[2], aktif.ust[2]) == pytest.approx((z0, z1))
    assert aktif.ust[2] - aktif.alt[2] < model.ust[2] - model.alt[2]


def test_sizintili_k_denge_ile():
    from cekirdek import yerel_k
    s = yerel_k.YerelKSonucu("pin", (1, 1), (1.0, 1.0), (), (1.1, 0.0), 1.0,
                             model_uretim=(1.1, 0.0), model_yok_olma=(0.9, 0.0),
                             denge=yerel_k.Denge((1.1, 0.0), (0.1, 0.0)))
    assert s.sizintili_k == pytest.approx(1.1)


def test_terminal_cikti_girdiyle_ayniysa_reddeder(tmp_path):
    import shutil
    from cekirdek import yerel_k
    yol = str(tmp_path / "m.json")
    shutil.copy(os.path.join(ORNEK, "pwr_17x17.json"), yol)
    assert yerel_k.terminal(["ekle", yol, "pin", "-o", yol]) == 1

# ---------------------------------------------------------------------------

def test_sonsuz_kafeste_yerel_k_ortalamasi_k_sonsuza_esit(gecici):
    # Arrange: yansitici 17x17 demet (sonsuz kafes), pin duzeyi
    from cekirdek import kosucu, yerel_k
    spec = yerel_k.tally_ekle(_ornek("pwr_17x17"), "pin")
    spec["ayarlar"] = dict(spec["ayarlar"], parcacik=3000, cevrim=40, pasif=15,
                           entropi_mesh={"var": False})
    # Act
    r = kosucu.calistir(spec, os.path.join(str(gecici), "yk"),
                        is_parcacigi=min(ISLEM_PARCACIGI, 6))
    assert r["basarili"], r
    sonuc = kosucu.sonuc_oku(r["statepoint"])
    s = yerel_k.sonuctan(sonuc, spec, denge=yerel_k.denge_oku(r["statepoint"]))[0]
    # Assert 1 (birebir): harita uretim toplami = global k-tracklength (ayni tahminci)
    P = sum(h.uretim[0] for h in s.hucreler)
    assert P == pytest.approx(s.denge.k_izyolu[0], rel=1e-9)
    assert s.model_uretim[0] == pytest.approx(P, rel=1e-9)
    # Assert 2 (birebir): harita = model (kapsama 1), sizinti 0
    assert s.kapsama == pytest.approx(1.0, abs=1e-9) and s.denge.sizinti[0] == 0.0
    assert s.ortalama[0] == pytest.approx(s.model_toplami[0], rel=1e-9)
    # Assert 3 (istatistik): kaynak notronu basina net yok olma = 1 (L = 0); 3 sigma
    D, sD = s.model_yok_olma
    assert abs(D - 1.0) <= 3.0 * sD, (D, sD)
    # Assert 4: k_harita = k_tl / D_model -- k-sonsuz tahmini
    assert s.ortalama[0] == pytest.approx(s.denge.k_izyolu[0] / D, rel=1e-9)
    assert s.c_xn > 1.0, "UO2'de (n,2n) net uretimi pozitif"
    fisil = [h for h in s.hucreler if h.fisil]
    assert len(fisil) == 264 and len(s.hucreler) == 289


HIZLI = [test_pin_hucresinde_tek_bin_adim_kadar,
         test_tek_demette_pin_duzeyi_17x17_demet_duzeyi_tek_bin,
         test_kor_kafesinde_demet_ve_pin_duzeyi_hizali,
         test_demet_arasi_bosluklu_korda_pin_duzeyi_acik_hata,
         test_altigen_kafes_acik_hatayla_reddedilir, test_bilinmeyen_duzey_reddedilir,
         test_tally_ekle_yeni_spec_dondurur_girdiyi_degistirmez,
         test_tally_ekle_iki_kez_cagrilinca_tek_kopya_kalir,
         test_tally_skorlari_dogrulamadan_uyarisiz_gecer,
         test_xn_skor_adlari_openmc_tepki_adlariyla_ayni,
         test_tally_kurucudan_ve_betikten_gecer,
         test_yerel_k_orani_ve_xn_duzeltmesi,
         test_coklu_kanal_net_uretimi_x_eksi_bir_ile_agirliklanir,
         test_yakitsiz_bin_fisil_degil_ama_ortalamaya_payda_olarak_girer,
         test_net_yok_olma_agirlikli_ortalama_uretim_toplami_oranina_esit,
         test_model_toplami_ve_kapsama_orani, test_eksik_skor_acik_hata,
         test_sonuctan_tally_yoksa_none_varsa_sonuc,
         test_csv_satirlari_her_bin_icin_bir_satir,
         test_terminal_ekle_yeni_model_dosyasi_yazar, test_terminal_desteksiz_modelde_hata_kodu,
         test_harmonik_esdegerlik_yakitsiz_binin_d_si_ayrica_eklenir,
         test_uretimsiz_binin_sigmasi_payin_belirsizliginden,
         test_sifir_yok_olmali_bin_fisil_sayilmaz_nan,
         test_mesh_olcusu_kayitli_tallyden_okunur_uyusmazlik_hata,
         test_tally_duzeni_kayitli_tanimdan_adim_ve_boyut,
         test_ayni_adli_kullanici_tallysi_silinmez_hata,
         test_tally_ekle_yalniz_tally_listesini_yeniler_ve_kayitta_isaret_kalir,
         test_donusumlu_kafes_reddedilir, test_aktif_eksenel_kapsam_yalniz_fisil_aralik,
         test_sizintili_k_denge_ile, test_terminal_cikti_girdiyle_ayniysa_reddeder]
YAVAS = [test_sonsuz_kafeste_yerel_k_ortalamasi_k_sonsuza_esit]
