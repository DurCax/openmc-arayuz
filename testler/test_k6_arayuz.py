# -*- coding: utf-8 -*-
"""
 test_k6_arayuz.py  --  v3 K6: malzeme asistani, turetilmis degerler paneli,
                        kutuphane tarayicisi (kullanici + PNNL) ve sekme baglantisi

 Yalnizca offscreen; modal diyaloglar exec() EDILMEZ. Kullanici kutuphanesi
 her testte gecici XDG_DATA_HOME'a yonlenir (gercek ~/.local/share'e yazilmaz).
"""

import json
import os
import tempfile
from unittest import mock

from testler.ortak_test import KOK, ORNEK  # noqa: F401

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _yerel_veri():
    """Gecici XDG_DATA_HOME + kesit yolu yok (nuklid denetimi atlanir)."""
    d = tempfile.mkdtemp(prefix="k6_xdg_")
    return mock.patch.dict(os.environ, {"XDG_DATA_HOME": d, "OPENMC_CROSS_SECTIONS": ""})


def _spec():
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))


def test_turetilmis_panel():
    _qt()
    from cekirdek import malzeme_kutup as mk
    from arayuz.malzeme.turetilmis_panel import TuretilmisPanel
    p = TuretilmisPanel()
    p.guncelle(mk.uo2(zenginlik=3.2, yogunluk=10.40))
    metin = p.metin()
    assert "6.9602e-02" in metin            # N_toplam atom/b-cm (el hesabi 0.0696019)
    assert "9.167" in metin                 # gHM/cm3
    assert p.tablo.rowCount() >= 4          # U234, U235, U236, U238, O...
    p.guncelle(None, "yoğunluk pozitif olmalı")
    assert "pozitif" in p.metin() and p.tablo.rowCount() == 0


def _asistan(spec=None):
    from arayuz.malzeme.asistan import MalzemeAsistani
    return MalzemeAsistani(spec if spec is not None else _spec())


def test_asistan_adimlari_uo2_katalogla_ayni():
    _qt()
    from cekirdek import malzeme_kutup as mk
    with _yerel_veri():
        a = _asistan()
        assert a.yigin.currentIndex() == 0
        assert sorted(a.kategori_dugmeleri) == sorted(
            ["yakit", "kilif", "moderator", "emici", "yapi", "ozel"])
        a.kategori_sec("yakit")
        assert a.yigin.currentIndex() == 1 and a.tarif_secici.currentData() == "uo2"
        a.form.deger_ayarla({"zenginlik": 3.2, "yogunluk_yolu": "dogrudan",
                             "yogunluk": 10.40, "sicaklik": 900.0})
        assert "0.0751" in a.panel.metin() or "7.516e-04" in a.panel.metin()   # N(U235)
        assert a.d_ileri.isEnabled()
        a.ileri()
        assert a.yigin.currentIndex() == 2
        assert any("atlandı" in m for _s, m in a.bulgular)
        assert a.ad.text() == "uo2_2"           # ornekte 'uo2' var
        m = a.sonuc()
        k = mk.uo2(zenginlik=3.2, yogunluk=10.40, sicaklik=900.0)
        for alan in ("bilesim", "yogunluk", "sicaklik", "sab"):
            assert m[alan] == k[alan], alan
        a.close()


def test_asistan_gecersiz_deger_ileriyi_kapatir():
    _qt()
    with _yerel_veri():
        a = _asistan()
        a.kategori_sec("moderator")
        a.tarif_sec("h2o")
        a.form.deger_ayarla({"sicaklik": 600.0, "basinc": 5.0})
        assert not a.d_ileri.isEnabled()
        assert "buhar" in a.hata.text()
        a.form.deger_ayarla({"basinc": 15.5})
        assert a.d_ileri.isEnabled() and not a.hata.isVisibleTo(a)
        a.close()


def test_asistan_kutuphaneme_kaydeder():
    _qt()
    from cekirdek import malzeme_kullanici as mku
    with _yerel_veri():
        a = _asistan()
        a.kategori_sec("emici")
        a.tarif_sec("b4c")
        a.ileri()
        a.ad.setText("benim_b4c")
        a.kutuphaneye.setChecked(True)
        a.aciklama.setText("deneme")
        assert a.bitir()
        kayitlar = mku.yukle()
        assert [k["ad"] for k in kayitlar] == ["benim_b4c"]
        assert kayitlar[0]["kaynak"] == "asistan" and kayitlar[0]["aciklama"] == "deneme"
        a.close()


def test_asistan_ozel_karisim():
    _qt()
    from cekirdek.sema import malzeme, bilesen
    spec = _spec()
    spec["malzemeler"] += [malzeme("a", [bilesen("H1", 1.0, tur="nuklid")], 1.0),
                           malzeme("b", [bilesen("O16", 1.0, tur="nuklid")], 3.0)]
    with _yerel_veri():
        a = _asistan(spec)
        a.kategori_sec("ozel")
        a.karisim.satir_ayarla(0, "a", 50.0)
        a.karisim.satir_ayarla(1, "b", 50.0)
        a.karisim.tur_ayarla("vo")
        assert a.d_ileri.isEnabled()
        assert abs(a.taslak()["yogunluk"]["deger"] - 2.0) < 1e-12
        a.karisim.satir_ayarla(1, "b", 40.0)            # toplam %90
        assert not a.d_ileri.isEnabled() and "100" in a.hata.text()
        a.close()


def _kutuphane_yaz(kayitlar):
    from cekirdek import malzeme_kullanici as mku
    mku.kaydet(kayitlar)


def test_tarayici_kullanici_kutuphanesi():
    _qt()
    from cekirdek import malzeme_kullanici as mku, malzeme_kutup as mk
    from arayuz.malzeme.kutuphane_tarayici import KutuphaneTarayici
    with _yerel_veri():
        m = mk.uo2(zenginlik=4.0)
        _kutuphane_yaz(mku.ekle((), mku.kayit_olustur(m, aciklama="dört yüzde")))
        t = KutuphaneTarayici(_spec())
        assert t.liste.count() == 1
        t.liste.setCurrentRow(0)
        assert t.d_ekle.isEnabled()
        eklenen = t.secileni_aktar()
        assert eklenen["ad"] == "uo2_2" and eklenen["bilesim"] == m["bilesim"]
        t._soru = lambda *_a: True                     # silme onayi
        t.sil()
        assert t.liste.count() == 0 and mku.yukle() == ()
        t.close()


def test_tarayici_bozuk_kutuphane_yedeklenir():
    _qt()
    from cekirdek import malzeme_kullanici as mku
    from arayuz.malzeme.kutuphane_tarayici import KutuphaneTarayici
    with _yerel_veri():
        yol = mku.varsayilan_yol()
        os.makedirs(os.path.dirname(yol))
        with open(yol, "w", encoding="utf-8") as f:
            f.write("{bozuk")
        t = KutuphaneTarayici(_spec())
        assert t.bozuk_kutu.isVisibleTo(t) and not t.liste.isEnabled()
        assert yol in t.bozuk_metin.text()
        yedek = t.bozugu_yedekle()
        assert os.path.exists(yedek) and open(yedek, encoding="utf-8").read() == "{bozuk"
        assert not t.bozuk_kutu.isVisibleTo(t) and t.liste.isEnabled()
        assert mku.yukle() == ()                         # yeni bos kutuphane yazildi
        t.close()


def test_tarayici_pnnl_ice_aktarim():
    _qt()
    from testler.test_k6_pnnl import _dosya
    from arayuz.malzeme.kutuphane_tarayici import KutuphaneTarayici
    with _yerel_veri():
        t = KutuphaneTarayici(_spec())
        assert t.pnnl_liste.count() == 0 and "indir" in t.pnnl_bilgi.text()
        t.pnnl_yukle(_dosya())
        assert t.pnnl_liste.count() == 2
        t.pnnl_ara.setText("u3o8")
        assert t.pnnl_liste.count() == 1
        t.pnnl_liste.setCurrentRow(0)
        m = t.pnnl_secileni_aktar()
        assert m["gorunen_ad"] == "Uranyum Oksit Denemesi"
        assert abs(m["yogunluk"]["deger"] - 8.3) < 1e-12
        t.pnnl_yukle("/yok/dosya.csv")                    # acik hata, liste korunur
        assert "açılamadı" in t.pnnl_bilgi.text()
        t.close()


def test_sekme_asistan_ve_kutuphane_dugmeleri():
    _qt()
    from cekirdek import malzeme_kullanici as mku
    from arayuz import sekme_malzeme as sm
    with _yerel_veri():
        s = sm.MalzemeSekmesi()
        s.spec_yukle(_spec())
        n = len(s.spec["malzemeler"])
        assert s.d_asistan.isEnabled() and s.d_kutuphanem.isEnabled()
        s._diyalog_calistir = lambda d: (d.kategori_sec("yakit"), d.ileri(), True)[-1] \
            if hasattr(d, "kategori_sec") else False
        s._asistan()
        assert len(s.spec["malzemeler"]) == n + 1
        s.tablo.selectRow(0)
        s._kutuphaneme_kaydet()
        assert [k["malzeme"]["ad"] for k in mku.yukle()] == [s.spec["malzemeler"][0]["ad"]]
        s._kutuphaneme_kaydet()                           # ayni ad: ikinci kayit _2
        assert len(mku.yukle()) == 2


HIZLI = [test_turetilmis_panel, test_asistan_adimlari_uo2_katalogla_ayni,
         test_asistan_gecersiz_deger_ileriyi_kapatir, test_asistan_kutuphaneme_kaydeder,
         test_asistan_ozel_karisim, test_tarayici_kullanici_kutuphanesi,
         test_tarayici_bozuk_kutuphane_yedeklenir, test_tarayici_pnnl_ice_aktarim,
         test_sekme_asistan_ve_kutuphane_dugmeleri]
