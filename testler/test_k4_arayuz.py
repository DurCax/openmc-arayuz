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


HIZLI = [test_harita_ozeti_etiket_ve_ortalama_gosterir, test_harita_ipucu_bin_degerini_verir,
         test_iki_duzey_varsa_secici_gorunur_ve_degistirir, test_harita_csv_kaydeder,
         test_tally_yoksa_ve_desteksiz_modelde_aciklama_gosterir,
         test_sihirbaz_demet_turlerini_listeler_hepsi_secili,
         test_sihirbaz_ayar_okur_ve_denetler, test_sihirbaz_kuyrukla_kosar_tablo_ve_csv]
YAVAS = []
