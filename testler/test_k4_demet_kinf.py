# -*- coding: utf-8 -*-
"""
 test_k4_demet_kinf.py  --  K4 demet k-sonsuz sihirbazi (cekirdek/demet_kinf.py)

 Hizli: demet turleri listesi, tek demet alt modeli (yerel yedek ve -- dalda
 varsa -- K5'in cekirdek/alt_model.demet_alt_modeli'si ayni sozlesmeyle),
 sihirbaz ayarlari, kuyruk entegrasyonu (SAHTE openmc, testler/y10_ortak.py),
 tablo ve CSV. YAVAS: sihirbazin k-sonsuzu = elle kurulan tek demet modeli.
"""

import copy
import csv
import dataclasses
import io
import math
import os

import pytest

from testler.ortak_test import ORNEK, ISLEM_PARCACIGI
from testler import y10_ortak as yo

_BEKLEME = 60.0          # s; sahte ikiliyle is ~0.1 s'de biter


def _ornek(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _uygulamalar():
    """Sozlesmeyi saglamasi gereken tek demet alt modeli (K5 alt_model; sarmalayici)."""
    from cekirdek import alt_model, demet_kinf
    return [demet_kinf.tek_demet_spec, alt_model.demet_alt_modeli]


def _imza(spec):
    """Kurulan modelin kimlikten bagimsiz imzasi: geometride KULLANILAN
    malzemelerin bilesimi, yuzeyler (tur, katsayi, sinir), hucre ve kafes."""
    from cekirdek import kurucu
    model, _b = kurucu.kur(spec)
    geo = model.geometry
    malzemeler = {m.name: tuple(sorted((n, round(d, 12)) for n, d in
                                       m.get_nuclide_atom_densities().items()))
                  for m in geo.get_all_materials().values()}
    yuzeyler = sorted((s.type, tuple(round(float(v), 9) for v in s.coefficients.values()),
                       s.boundary_type) for s in geo.get_all_surfaces().values())
    kafesler = sorted((tuple(l.pitch), tuple(l.shape), tuple(l.lower_left))
                      for l in geo.get_all_lattices().values())
    return malzemeler, yuzeyler, len(geo.get_all_cells()), kafesler


def test_demet_turleri_kordaki_kullanim_sayisiyla_listelenir():
    # Arrange
    from cekirdek import demet_kinf
    spec = _ornek("pwr_ceyrek_kor")
    # Act
    turler = demet_kinf.demet_turleri(spec)
    # Assert
    sayilar = {t.ad: t.kullanim for t in turler}
    assert sayilar == {"demet_24": 6, "demet_31": 7}   # AAABss AABBss ABBsss BBssss
    assert all(t.tur == "kare" and t.boyut == (17, 17) for t in turler)


def test_tek_demet_modelinde_demet_bir_kez_kullanilir():
    from cekirdek import demet_kinf
    turler = demet_kinf.demet_turleri(_ornek("pwr_17x17"))
    assert [(t.ad, t.kullanim) for t in turler] == [("demet_17x17", 1)]


def test_tek_demet_alt_modeli_yansitici_ve_sade():
    # Arrange
    from cekirdek import kurucu
    spec = _ornek("pwr_ceyrek_kor")
    once = copy.deepcopy(spec)
    for uygula in _uygulamalar():
        # Act
        alt = uygula(spec, "demet_24")
        # Assert
        ad = getattr(uygula, "__name__", "?")
        assert spec == once, "%s girdiyi degistirdi" % ad
        assert alt["kor"]["tur"] == "tek_demet" and alt["kor"]["demet"] == "demet_24", ad
        assert set(alt["kor"]["sinir"].values()) == {"reflective"}, ad
        assert not alt["kor"].get("yukseklik"), "%s: k-sonsuz 2B olmali" % ad
        assert alt["tallyler"] == [], ad
        assert not alt["guc_dagilimi"].get("var") and not alt["tukenme"].get("var"), ad
        assert not (alt["ayarlar"].get("kinetik") or {}).get("var"), ad
        model, _b = kurucu.kur(alt)
        kutu = model.geometry.bounding_box
        assert kutu.upper_right[0] == pytest.approx(10.71), ad


def test_sihirbaz_modeli_elle_modelle_fiziksel_olarak_ozdes():
    # Arrange: deterministik kanit -- ayni malzeme bilesimi, yuzeyler, hucreler, kafes
    from cekirdek import demet_kinf
    spec = _ornek("pwr_ceyrek_kor")
    ayar = demet_kinf.KinfAyari(parcacik=100, cevrim=10, pasif=2)
    for ad in ("demet_24", "demet_31"):
        # Act
        sihirbaz = demet_kinf.sihirbaz_spec(spec, ad, ayar)
        elle = _elle_tek_demet(spec, ad, ayar)
        # Assert
        assert _imza(sihirbaz) == _imza(elle), ad


def test_budama_yalniz_kullanilmayan_malzemeleri_atar():
    # Arrange
    from cekirdek import demet_kinf, sema
    spec = _ornek("pwr_ceyrek_kor")
    for ad in ("demet_24", "demet_31"):
        # Act
        alt = demet_kinf.tek_demet_spec(spec, ad)
        # Assert
        tum = {m["ad"] for m in spec["malzemeler"]}
        kalan = {m["ad"] for m in alt["malzemeler"]}
        atilan = tum - kalan
        assert kalan <= tum
        assert not (atilan & set(_imza(alt)[0])), "atilan malzeme geometride kullanilmamali"
        assert sema.kullanilan_malzemeler(alt) <= kalan


def test_demet_kinf_csv_formul_oneki_etkisiz():
    from cekirdek import demet_kinf
    satir = demet_kinf.KinfSatiri("=CMD()", 1.0, 0.1, "basarisiz", "+hata")
    okunan = list(csv.reader(io.StringIO(demet_kinf.csv_metni([satir]))))[1]
    assert okunan[0] == "'=CMD()" and okunan[4] == "'+hata"


def test_tanimsiz_demet_acik_hata():
    from cekirdek import demet_kinf
    with pytest.raises(demet_kinf.DemetKinfHatasi):
        demet_kinf.tek_demet_spec(_ornek("pwr_ceyrek_kor"), "yok_boyle")


def test_sihirbaz_spec_ayarlari_uygular_kaynak_kutu():
    # Arrange
    from cekirdek import demet_kinf
    ayar = demet_kinf.KinfAyari(parcacik=1234, cevrim=33, pasif=11, tohum=7)
    # Act
    alt = demet_kinf.sihirbaz_spec(_ornek("pwr_ceyrek_kor"), "demet_31", ayar)
    # Assert
    a = alt["ayarlar"]
    assert (a["parcacik"], a["cevrim"], a["pasif"], a["tohum"]) == (1234, 33, 11, 7)
    assert a["mod"] == "eigenvalue"
    assert a["kaynak"]["tur"] == "kutu" and not a["kaynak"].get("alt")


def test_gecersiz_ayar_reddedilir():
    from cekirdek import demet_kinf
    for kotu in ({"parcacik": 0}, {"cevrim": 5, "pasif": 5}, {"is_parcacigi": 0}):
        with pytest.raises(demet_kinf.DemetKinfHatasi):
            demet_kinf.KinfAyari(**kotu).denetle()


def test_isler_ayri_dizinde_etiketli():
    # Arrange
    from cekirdek import demet_kinf
    ayar = demet_kinf.KinfAyari(is_parcacigi=2)
    # Act
    isler = demet_kinf.isleri_olustur(_ornek("pwr_ceyrek_kor"), ["demet_24", "demet_31"],
                                      ayar, "/tmp/k4_kok")
    # Assert
    assert [i.etiket[demet_kinf.ETIKET] for i in isler] == ["demet_24", "demet_31"]
    assert len({i.dizin for i in isler}) == 2
    assert all(i.is_parcacigi == 2 and i.spec["kor"]["tur"] == "tek_demet" for i in isler)


def test_kuyrukla_kosulup_tablo_dolar(tmp_path, monkeypatch):
    # Arrange: SAHTE openmc (k = 1.01 +- 0.002)
    from cekirdek import demet_kinf, kuyruk
    exe = yo.sahte_openmc(tmp_path)
    k = kuyruk.Kuyruk(en_fazla_paralel=2, is_parcacigi_butcesi=2, openmc=exe)
    ayar = demet_kinf.KinfAyari(is_parcacigi=1)
    isler = demet_kinf.isleri_olustur(_ornek("pwr_ceyrek_kor"), ["demet_24", "demet_31"],
                                      ayar, str(tmp_path / "kinf"))
    isler = [dataclasses.replace(i, sonuc_kancasi=yo.sahte_sonuc, dogrulama=False,
                                 veri_kontrolu=False) for i in isler]
    # Act
    kimlikler = demet_kinf.kuyruga_ekle(k, isler)
    k.baslat()
    assert k.bekle(_BEKLEME)
    satirlar = demet_kinf.tablo([k.durum(x) for x in kimlikler] + list(k.durumlar()))
    k.kapat()
    # Assert
    assert [s.demet for s in satirlar] == ["demet_24", "demet_31"], "tekrarsiz, sirali"
    assert all(s.asama == "bitti" and (s.k, s.sigma) == yo.SAHTE_K for s in satirlar)


def test_csv_demet_turu_k_sigma():
    # Arrange
    from cekirdek import demet_kinf
    satirlar = (demet_kinf.KinfSatiri("A", 1.2, 0.001, "bitti", None),
                demet_kinf.KinfSatiri("B", None, None, "basarisiz", "openmc hata"))
    # Act
    okunan = list(csv.reader(io.StringIO(demet_kinf.csv_metni(satirlar))))
    # Assert
    assert okunan[0][:3] == ["demet", "k_inf", "sigma"]
    assert okunan[1][:3] == ["A", "1.200000", "0.001000"]
    assert okunan[2][0] == "B" and okunan[2][1] == "" and "openmc" in okunan[2][4]


def test_yabanci_isler_tabloya_girmez():
    from cekirdek import demet_kinf, kuyruk
    d = kuyruk.IsDurumu(kimlik="x", ad="baska", dizin="/tmp/x", asama=kuyruk.Asama.BITTI,
                        etiket={})
    assert demet_kinf.tablo([d]) == ()


# ---------------------------------------------------------------------------
# YAVAS: sihirbaz k-sonsuz = elle kurulan model
# ---------------------------------------------------------------------------

def _elle_tek_demet(spec, ad, ayar):
    """Kullanicinin elle kuracagi model: ayni kutuphane, kor = tek demet, yansitici."""
    from cekirdek import sema
    el = copy.deepcopy(spec)
    kor = copy.deepcopy(sema.VARSAYILAN_KOR)
    kor.update({"tur": "tek_demet", "demet": ad,
                "sinir": {"yan": "reflective", "alt": "reflective", "ust": "reflective"}})
    el["kor"] = kor
    el["tallyler"] = []
    el["guc_dagilimi"] = dict(el.get("guc_dagilimi") or {}, var=False)
    el["tukenme"] = dict(el.get("tukenme") or {}, var=False)
    el["ayarlar"].update({"parcacik": ayar.parcacik, "cevrim": ayar.cevrim,
                          "pasif": ayar.pasif, "tohum": ayar.tohum})
    el["ayarlar"]["kaynak"] = {"tur": "kutu"}
    return el


def test_sihirbaz_k_sonsuzu_elle_modelle_ayni(gecici):
    # Arrange
    from cekirdek import demet_kinf, kosucu, kuyruk
    spec = _ornek("pwr_ceyrek_kor")
    ayar = demet_kinf.KinfAyari(parcacik=2000, cevrim=30, pasif=10, tohum=3,
                                is_parcacigi=min(ISLEM_PARCACIGI, 6))
    k = kuyruk.Kuyruk(en_fazla_paralel=1)
    kimlik = demet_kinf.kuyruga_ekle(k, demet_kinf.isleri_olustur(
        spec, ["demet_24"], ayar, os.path.join(str(gecici), "sihirbaz")))[0]
    # Act
    k.baslat()
    assert k.bekle(900.0)
    d = k.durum(kimlik)
    k.kapat()
    el = kosucu.calistir(_elle_tek_demet(spec, "demet_24", ayar),
                         os.path.join(str(gecici), "elle"), is_parcacigi=ayar.is_parcacigi)
    k_el = kosucu.sonuc_oku(el["statepoint"])["keff"]
    # Assert
    assert d.asama == kuyruk.Asama.BITTI, d.hata
    (k_s, s_s) = d.k
    # Fiziksel olarak ozdes model (imza testi); budama rastgele gerceklesmeyi
    # degistirir: istatistik sinirinda ayni, sigma_fark = hypot(s1, s2).
    assert abs(k_s - k_el[0]) <= 2.0 * math.hypot(s_s, k_el[1]), (d.k, k_el)
    assert k_s > 1.0, "yansitici 2.4% demet kritik ustu olmali"


HIZLI = [test_demet_turleri_kordaki_kullanim_sayisiyla_listelenir,
         test_tek_demet_modelinde_demet_bir_kez_kullanilir,
         test_tek_demet_alt_modeli_yansitici_ve_sade, test_tanimsiz_demet_acik_hata,
         test_sihirbaz_spec_ayarlari_uygular_kaynak_kutu, test_gecersiz_ayar_reddedilir,
         test_isler_ayri_dizinde_etiketli, test_kuyrukla_kosulup_tablo_dolar,
         test_csv_demet_turu_k_sigma, test_yabanci_isler_tabloya_girmez,
         test_sihirbaz_modeli_elle_modelle_fiziksel_olarak_ozdes,
         test_budama_yalniz_kullanilmayan_malzemeleri_atar,
         test_demet_kinf_csv_formul_oneki_etkisiz]
YAVAS = [test_sihirbaz_k_sonsuzu_elle_modelle_ayni]
