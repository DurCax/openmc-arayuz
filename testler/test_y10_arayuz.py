# -*- coding: utf-8 -*-
"""
 test_y10_arayuz.py  --  Y10 is akisi penceresi: kuyruk paneli, gecmis ve
                         karsilastirma, SLURM formu (offscreen, sahte openmc)
"""

import os

from testler.ortak_test import ORNEK
from testler import y10_ortak as yo

_BEKLEME = 30.0


def _uyg():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _islet(uyg, kosul):
    yo.bekle_kadar(lambda: (uyg.processEvents(), kosul())[1], _BEKLEME)


def _panel(tmp_path, monkeypatch):
    from cekirdek import kosu_gecmisi, kuyruk
    from arayuz.kuyruk.panel import KuyrukPaneli
    monkeypatch.setenv("SAHTE_KAYIT", str(tmp_path / "kayit.txt"))
    depo = kosu_gecmisi.GecmisDeposu(str(tmp_path / "g.sqlite3"))
    k = kuyruk.Kuyruk(openmc=yo.sahte_openmc(tmp_path), sonuc_kancasi=yo.sahte_sonuc)
    return KuyrukPaneli(cekirdek_kuyrugu=k, gecmis=depo), depo


def test_kuyruk_paneli_uc_kosuyu_sirayla_gosterir(tmp_path, monkeypatch):
    # Arrange
    from cekirdek import kuyruk
    uyg = _uyg()
    panel, depo = _panel(tmp_path, monkeypatch)
    for ad in ("a", "b", "c"):
        panel.kq.kuyruk.ekle(kuyruk.KosuIsi(ad=ad, dizin=yo.hazir_dizin(tmp_path / ad)))
    # Act
    panel.d_baslat.click()
    _islet(uyg, lambda: panel.kq.kuyruk.tamamlandi_mi()
           and panel.tablo.item(2, 1).text() == "bitti")
    _islet(uyg, lambda: len(depo.listele()) == 3)
    # Assert
    assert panel.tablo.rowCount() == 3
    assert [panel.tablo.item(i, 0).text() for i in range(3)] == ["a", "b", "c"]
    assert all(panel.tablo.item(i, 3).text() == "1.01000 ± 0.00200" for i in range(3))
    assert panel.d_baslat.text() == "Duraklat"
    assert "tamamlandı" in panel.durum_etiket.text()
    panel.kapat()


def test_kuyruk_paneli_gecerli_modeli_ayri_dizine_ekler(tmp_path, monkeypatch):
    from cekirdek import sema
    _uyg()
    panel, _depo = _panel(tmp_path, monkeypatch)
    panel.kok.setText(str(tmp_path / "kosular"))
    assert not panel.d_ekle.isEnabled()
    panel.spec_ayarla(sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json")))
    assert panel.d_ekle.isEnabled()
    k1, k2 = panel.gecerli_modeli_ekle(), panel.gecerli_modeli_ekle()
    d1, d2 = panel.kq.kuyruk.durum(k1).dizin, panel.kq.kuyruk.durum(k2).dizin
    assert d1 != d2 and os.path.dirname(d1) == str(tmp_path / "kosular")
    assert panel.tablo.rowCount() == 2
    panel.tablo.selectRow(1)
    panel.d_yukari.click()
    assert [d.kimlik for d in panel.kq.kuyruk.durumlar()] == [k2, k1]
    panel.d_iptal.click()
    assert panel.kq.kuyruk.durum(k2).bitti_mi
    panel.kapat()


def _sahte_karsilastirma(tmp_path):
    from cekirdek import kosu_gecmisi as kg
    b1 = {(x, y): (1.0, 0.01) for x in range(3) for y in range(3)}
    b2 = {**b1, (1, 1): (1.1, 0.01)}
    return kg.Karsilastirma(str(tmp_path / "a"), str(tmp_path / "b"),
                            kg.k_farki(1.0, 0.0003, 1.002, 0.0003), kg.guc_farki(b1, b2), ())


def test_karsilastirma_paneli_ozet_tablo_ve_harita(tmp_path, monkeypatch):
    # Arrange
    from cekirdek import kosu_gecmisi as kg
    from arayuz.karsilastir.panel import KarsilastirmaPaneli
    _uyg()
    depo = kg.GecmisDeposu(str(tmp_path / "g.sqlite3"))
    for i, ad in enumerate(("a", "b")):
        depo.kaydet(kg.KosuKaydi(kimlik=ad, ad=ad, dizin=str(tmp_path / ad), durum="bitti",
                                 keff=1.0, sapma=0.001, kayit_ani=float(i + 1)))
    sahte = _sahte_karsilastirma(tmp_path)
    cagrilar = []
    monkeypatch.setattr(kg, "kosulari_karsilastir",
                        lambda d1, d2: (cagrilar.append((d1, d2)), sahte)[1])
    panel = KarsilastirmaPaneli(depo)
    # Act
    panel.gecmis_tablo.selectAll()
    panel._secilileri_karsilastir()
    # Assert
    assert cagrilar == [(str(tmp_path / "a"), str(tmp_path / "b"))], "eski = 1, yeni = 2"
    metin = panel.ozet.text()
    assert "z = Δk" in metin and "anlamlı" in metin
    assert panel.fark_tablo.rowCount() == 9
    assert panel.fark_tablo.item(0, 0).text()        # en buyuk |z| ustte
    assert panel.figur.axes, "fark haritasi cizilmeli"


def test_karsilastirma_paneli_hata_gosterir(tmp_path):
    from arayuz.karsilastir.panel import KarsilastirmaPaneli
    _uyg()
    panel = KarsilastirmaPaneli(None)
    assert panel.karsilastir(str(tmp_path), str(tmp_path)) is None
    assert "Karşılaştırılamadı" in panel.ozet.text()
    panel._secilileri_karsilastir()
    assert "iki" in panel.ozet.text()


def test_slurm_paneli_gecersiz_alani_reddeder_gecerliyi_onizler():
    from arayuz.kuyruk.slurm_paneli import SlurmPaneli
    _uyg()
    panel = SlurmPaneli()
    panel.gorev.setValue(4)
    assert "#SBATCH --ntasks=4" in panel.onizleme.toPlainText()
    assert "sözdizimi geçerli" in panel.durum.text()
    assert not panel.d_kaydet.isEnabled(), "model yokken klasor hazirlanamaz"
    panel.is_adi.setText("kotu ad; rm")
    assert "Geçersiz" in panel.durum.text() and not panel.d_kaydet.isEnabled()


def test_is_akisi_penceresi_uc_sekme(tmp_path, monkeypatch):
    from cekirdek import sema
    from arayuz.kuyruk import pencere
    _uyg()
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "veri"))
    p = pencere.ac(None, sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json")))
    assert p.sekmeler.count() == 3
    assert p.kuyruk.d_ekle.isEnabled() and p.slurm.d_kaydet.isEnabled()
    assert pencere.ac(None, None) is p
    assert not p.kuyruk.d_ekle.isEnabled()
    p.close()
    assert pencere._TEKIL == {}


HIZLI = [test_kuyruk_paneli_uc_kosuyu_sirayla_gosterir,
         test_kuyruk_paneli_gecerli_modeli_ayri_dizine_ekler,
         test_karsilastirma_paneli_ozet_tablo_ve_harita, test_karsilastirma_paneli_hata_gosterir,
         test_slurm_paneli_gecersiz_alani_reddeder_gecerliyi_onizler,
         test_is_akisi_penceresi_uc_sekme]
YAVAS = []
