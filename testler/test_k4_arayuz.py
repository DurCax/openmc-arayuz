# -*- coding: utf-8 -*-
"""
 test_k4_arayuz.py  --  K4 arayuzu: yerel k haritasi (arayuz/sonuc/yerel_k.py)
 ve demet k-sonsuz sihirbazi (arayuz/analiz/demet_kinf.py). Basiz (offscreen);
 sihirbaz kosulari SAHTE openmc ile (testler/y10_ortak.py).
"""

import math
import os
import time

import pytest

from testler.ortak_test import ORNEK
from testler import y10_ortak as yo

_BEKLEME = 60.0


def _uyg():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _ornek(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _sonuc(duzey="pin"):
    from cekirdek import yerel_k
    h = (yerel_k.YerelK((0, 0), 1.25, 0.01, 1.26, (2.5, 0.02), (2.0, 0.01), True),
         yerel_k.YerelK((1, 0), 0.0, 0.0, 0.0, (0.0, 0.0), (0.5, 0.01), False),
         yerel_k.YerelK((0, 1), 1.10, 0.01, 1.11, (2.2, 0.02), (2.0, 0.01), True),
         yerel_k.YerelK((1, 1), 1.30, 0.01, 1.31, (2.6, 0.02), (2.0, 0.01), True))
    return yerel_k.YerelKSonucu(duzey, (2, 2), (1.26, 1.26), h, (1.1765, 0.004), 1.0016,
                                (1.1765, 0.006), 1.0, (1.18, 0.003))


def _bekle(kosul, sure=_BEKLEME):
    uyg = _uyg()
    son = time.time() + sure
    while time.time() < son:
        uyg.processEvents()
        if kosul():
            return True
        time.sleep(0.02)
    return False


# ---------------------------------------------------------------------------
# yerel k haritasi
# ---------------------------------------------------------------------------

def test_harita_ozeti_etiket_ve_ortalama_gosterir():
    # Arrange
    _uyg()
    from arayuz.sonuc.yerel_k import YerelKHaritasi
    w = YerelKHaritasi()
    # Act
    w.sonuclari_ayarla([_sonuc()])
    # Assert
    metin = w.ozet.text()
    assert "k∞ değildir" in metin
    assert "1.1765" in metin and "1.18000" in metin
    izgara = w.izgara()
    assert math.isnan(izgara[0][1]), "yakitsiz bin bos (NaN) cizilir"
    assert izgara[1][1] == pytest.approx(1.30)


def test_harita_ipucu_bin_degerini_verir():
    _uyg()
    from arayuz.sonuc.yerel_k import YerelKHaritasi
    w = YerelKHaritasi()
    w.sonuclari_ayarla([_sonuc()])
    metin = w.ipucu_metni(0.63, 0.63)          # (1,1) bininin merkezi [cm]
    assert metin and "1.30000" in metin and "(2, 2)" in metin
    assert w.ipucu_metni(-50.0, -50.0) is None


def test_iki_duzey_varsa_secici_gorunur_ve_degistirir():
    _uyg()
    from arayuz.sonuc.yerel_k import YerelKHaritasi
    w = YerelKHaritasi()
    w.sonuclari_ayarla([_sonuc("pin"), _sonuc("demet")])
    assert not w.duzey.isHidden() and w.duzey.count() == 2
    w.duzey.setCurrentIndex(1)
    assert w.secili().duzey == "demet"


def test_harita_csv_kaydeder(tmp_path):
    _uyg()
    from arayuz.sonuc.yerel_k import YerelKHaritasi
    w = YerelKHaritasi()
    w.sonuclari_ayarla([_sonuc()])
    yol = tmp_path / "yk.csv"
    w.csv_kaydet(str(yol))
    assert len(yol.read_text(encoding="utf-8").strip().splitlines()) == 5


def test_tally_yoksa_ve_desteksiz_modelde_aciklama_gosterir():
    # Arrange
    _uyg()
    from arayuz.sonuc.yerel_k import YerelKHaritasi
    w = YerelKHaritasi()
    # Act / Assert
    w.kosu_sonucu_ayarla({"tallyler": {}}, _ornek("pwr_17x17"))
    assert "hesaplanmadı" in w.ozet.text()
    w.kosu_sonucu_ayarla({"tallyler": {"yerel_k_pin": "okunamadı: x"}}, _ornek("pwr_17x17"))
    assert "okunamadı" in w.ozet.text()


# ---------------------------------------------------------------------------
# demet k-sonsuz sihirbazi
# ---------------------------------------------------------------------------

def test_sihirbaz_demet_turlerini_listeler_hepsi_secili():
    _uyg()
    from arayuz.analiz.demet_kinf import DemetKinfPaneli
    p = DemetKinfPaneli(_ornek("pwr_ceyrek_kor"))
    assert p.demetler.rowCount() == 2
    assert p.secili_demetler() == ["demet_24", "demet_31"]
    assert p.demetler.item(1, 3).text() == "7"
    p.kapat()


def test_sihirbaz_ayar_okur_ve_denetler():
    _uyg()
    from arayuz.analiz.demet_kinf import DemetKinfPaneli
    p = DemetKinfPaneli(_ornek("pwr_ceyrek_kor"))
    p.parcacik.setValue(1500); p.cevrim.setValue(50); p.pasif.setValue(20)
    a = p.ayar()
    assert (a.parcacik, a.cevrim, a.pasif) == (1500, 50, 20)
    p.pasif.setValue(50)
    assert p.baslat() == [], "gecersiz ayarla kuyruga is eklenmez"
    assert "pasif" in p.durum_etiketi.text()
    p.kapat()


def test_sihirbaz_kuyrukla_kosar_tablo_ve_csv(tmp_path, monkeypatch):
    # Arrange: SAHTE openmc ile kuyruk; dogrulama/veri denetimi kapali
    _uyg()
    from cekirdek import kuyruk
    from arayuz.analiz import demet_kinf as ekran
    exe = yo.sahte_openmc(tmp_path)
    kq = kuyruk.Kuyruk(en_fazla_paralel=1, is_parcacigi_butcesi=2, openmc=exe)
    p = ekran.DemetKinfPaneli(_ornek("pwr_ceyrek_kor"), cekirdek_kuyrugu=kq,
                              kok_dizin=str(tmp_path / "kinf"))
    monkeypatch.setattr(p, "_is_ayari", lambda i: dict(sonuc_kancasi=yo.sahte_sonuc,
                                                       dogrulama=False, veri_kontrolu=False))
    p.is_parcacigi.setValue(1)
    # Act
    kimlikler = p.baslat()
    assert len(kimlikler) == 2
    assert _bekle(lambda: p.ilerleme.value() == 2)
    # Assert
    assert p.sonuclar.rowCount() == 2
    assert p.sonuclar.item(0, 0).text() == "demet_24"
    assert "1.01000" in p.sonuclar.item(0, 2).text()
    yol = tmp_path / "kinf.csv"
    p.csv_kaydet(str(yol))
    assert "demet_31" in yol.read_text(encoding="utf-8")
    p.kapat()


# ---------------------------------------------------------------------------
# duzeltme turu: ayril, kapanista iptal, kancalar, etiketler
# ---------------------------------------------------------------------------

def test_bagdastirici_ayril_dinleyiciyi_cikarir_kuyrugu_kapatmaz():
    # Arrange
    _uyg()
    from cekirdek import kuyruk
    from arayuz.kuyruk.bagdastirici import KuyrukBagdastirici
    k = kuyruk.Kuyruk()
    kq = KuyrukBagdastirici(k)
    # Act
    kq.ayril()
    kq.ayril()                                   # ikinci cagri zararsiz
    # Assert
    assert kq._olay not in k._dinleyiciler and k._dinleyiciler == []
    assert not k._kapali, "ayril kuyrugu kapatmamali"
    k.kapat()


def test_panel_kapaninca_kendi_bitmemis_islerini_iptal_eder(tmp_path, monkeypatch):
    # Arrange: paylasilan kuyruk + uzun suren SAHTE kosu
    _uyg()
    from cekirdek import kuyruk
    from arayuz.analiz import demet_kinf as ekran
    exe = yo.sahte_openmc(tmp_path)
    monkeypatch.setenv("SAHTE_SURE", "1.0")
    kq = kuyruk.Kuyruk(en_fazla_paralel=1, is_parcacigi_butcesi=1, openmc=exe)
    p = ekran.DemetKinfPaneli(_ornek("pwr_ceyrek_kor"), cekirdek_kuyrugu=kq,
                              kok_dizin=str(tmp_path / "kinf"))
    monkeypatch.setattr(p, "_is_ayari", lambda i: dict(sonuc_kancasi=yo.sahte_sonuc,
                                                       dogrulama=False, veri_kontrolu=False))
    p.is_parcacigi.setValue(1)
    kimlikler = p.baslat()
    # Act
    p.kapat()
    # Assert
    assert kq.bekle(_BEKLEME)
    assert all(kq.durum(k).asama == kuyruk.Asama.IPTAL for k in kimlikler)
    kq.kapat()


def test_panel_form_etiketi_parcacik_ve_bitmemiste_k_yok():
    _uyg()
    from cekirdek import kuyruk
    from arayuz.analiz.demet_kinf import DemetKinfPaneli
    p = DemetKinfPaneli(_ornek("pwr_ceyrek_kor"))
    etiketler = [w.text() for w in p.findChildren(QtWidgets_label())]
    assert "Parçacık:" in etiketler
    d = kuyruk.IsDurumu(kimlik="a", ad="x", dizin="/tmp/a", asama=kuyruk.Asama.KOSUYOR,
                        k=(1.0, 0.1), etiket={"k4_demet": "demet_24"})
    p._durum_geldi(d)
    assert p.sonuclar.item(0, 2).text() == "—", "ara k tabloda gosterilmez (CSV ile ayni)"
    p.kapat()


def QtWidgets_label():
    from PySide6 import QtWidgets
    return QtWidgets.QLabel


def test_harita_etiketi_uretim_yok_olma_orani_ve_sizinti_denetimi():
    # Arrange
    _uyg()
    import dataclasses
    from cekirdek import yerel_k
    from arayuz.sonuc.yerel_k import YerelKHaritasi
    s = dataclasses.replace(_sonuc(), model_uretim=(1.1765, 0.0), model_yok_olma=(0.95, 0.0),
                            denge=yerel_k.Denge((1.1765, 0.003), (0.05, 0.001)))
    w = YerelKHaritasi()
    # Act
    w.sonuclari_ayarla([s])
    # Assert
    metin = w.ozet.text()
    assert "üretim / yok olma" in metin and "k∞ değildir" in metin
    assert "çoğalma" not in metin
    assert "1.17650" in metin and "P/(D+L)" in metin


def test_ayar_karti_pin_secince_tally_ekler_kapali_kaldirir():
    # Arrange
    _uyg()
    from cekirdek import yerel_k
    from arayuz.ayar.yerel_k_karti import YerelKAyarKarti
    spec = _ornek("pwr_17x17")
    kart = YerelKAyarKarti()
    kart.doldur(spec)
    sayac = []
    kart.degisti.connect(lambda: sayac.append(1))
    # Act
    kart.duzey.setCurrentIndex(kart.duzey.findData("pin"))
    # Assert
    adlar = [t["ad"] for t in spec["tallyler"]]
    assert yerel_k.TALLY_ADLARI["pin"] in adlar and sayac
    kart.duzey.setCurrentIndex(kart.duzey.findData(None))
    assert not any(t.get("uretici") == yerel_k.URETICI for t in spec["tallyler"])


def test_ayar_karti_desteksiz_modelde_hata_gosterir_spec_degismez():
    _uyg()
    import copy
    from arayuz.ayar.yerel_k_karti import YerelKAyarKarti
    spec = _ornek("vver1000_demet")
    once = copy.deepcopy(spec)
    kart = YerelKAyarKarti()
    kart.doldur(spec)
    kart.duzey.setCurrentIndex(kart.duzey.findData("pin"))
    assert spec == once
    assert kart.duzey.currentData() is None
    assert not kart.uyari.isHidden() and "altıgen" in kart.uyari.text()


def test_ayar_sekmesi_yerel_k_kartini_doldurur():
    _uyg()
    from cekirdek import yerel_k
    from arayuz.sekme_ayar import AyarSekmesi
    a = AyarSekmesi()
    a.spec_yukle(yerel_k.tally_ekle(_ornek("pwr_17x17"), "demet"))
    assert a.yerel_k_karti.duzey.currentData() == "demet"


def test_calistir_sekmesi_yerel_k_kartini_yalniz_tally_varken_gosterir():
    # Arrange
    _uyg()
    from cekirdek import yerel_k
    from arayuz.sekme_calistir import CalistirSekmesi
    spec = yerel_k.tally_ekle(_ornek("pwr_17x17"), "demet")
    c = CalistirSekmesi()
    c.spec_ayarla(spec, None)
    temel = {"keff": (1.18, 0.001), "cevrim": 10, "pasif": 5, "parcacik": 100,
             "entropi": None}
    from testler.test_k4_yerel_k import _sentetik_df
    df = _sentetik_df({(0, 0): {"nu-fission": (1.18, 0.01), "absorption": (1.0, 0.01)}})
    # Act / Assert
    c._sonuc_goster(dict(temel, tallyler={}), None)
    assert c.yerel_k_karti.isHidden()
    c._sonuc_goster(dict(temel, tallyler={yerel_k.TALLY_ADLARI["demet"]: df}), None)
    assert not c.yerel_k_karti.isHidden()
    assert c.yerel_k.secili().duzey == "demet"


def test_araclar_menusu_demet_kinf_sihirbazini_acar(tmp_path, monkeypatch):
    # Arrange
    from arayuz.ana_pencere import AnaPencere
    from arayuz.analiz import demet_kinf as ekran
    _uyg()
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "veri"))
    p = AnaPencere()
    p._kaydetme_sor = lambda: True
    p.onizleme._ciz = lambda *a, **k: None
    try:
        # Act
        p.e_demet_kinf.trigger()
        acik = ekran._TEKIL.get("pencere")
        # Assert
        assert acik is not None and acik.isVisible()
        acik.close()
        assert ekran._TEKIL == {}
    finally:
        p.s_tukenme.bekle()
        p._kirli = False
        p.close()
        p.deleteLater()


HIZLI = [test_harita_ozeti_etiket_ve_ortalama_gosterir, test_harita_ipucu_bin_degerini_verir,
         test_iki_duzey_varsa_secici_gorunur_ve_degistirir, test_harita_csv_kaydeder,
         test_tally_yoksa_ve_desteksiz_modelde_aciklama_gosterir,
         test_sihirbaz_demet_turlerini_listeler_hepsi_secili,
         test_sihirbaz_ayar_okur_ve_denetler, test_sihirbaz_kuyrukla_kosar_tablo_ve_csv,
         test_bagdastirici_ayril_dinleyiciyi_cikarir_kuyrugu_kapatmaz,
         test_panel_kapaninca_kendi_bitmemis_islerini_iptal_eder,
         test_panel_form_etiketi_parcacik_ve_bitmemiste_k_yok,
         test_harita_etiketi_uretim_yok_olma_orani_ve_sizinti_denetimi,
         test_ayar_karti_pin_secince_tally_ekler_kapali_kaldirir,
         test_ayar_karti_desteksiz_modelde_hata_gosterir_spec_degismez,
         test_ayar_sekmesi_yerel_k_kartini_doldurur,
         test_calistir_sekmesi_yerel_k_kartini_yalniz_tally_varken_gosterir,
         test_araclar_menusu_demet_kinf_sihirbazini_acar]
YAVAS = []
