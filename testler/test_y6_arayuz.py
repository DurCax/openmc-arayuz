# -*- coding: utf-8 -*-
"""
 test_y6_arayuz.py  --  v3 Y6: Analiz > Nokta kinetigi karti ve hesap ayari

   - Keepin hazir verisi tabloya gelir (beta_i pcm, lambda_i 1/s)
   - elle tek grup: periyot etiketi = Inhour kararli periyodu
   - pcm <-> $ birim degisimi degeri donusturur
   - rampa alanlari yalniz rampada gorunur
   - 1.2 $ -> ANI KRITIK uyarisi; gecersiz veri -> hata metni (cokmez)
   - son kosudan al: grup verisi varsa tablo + Lambda dolar; yoksa aciklama
   - geri besleme: sicaklik ekseni cizilir
   - Hesap ayarlari: grup sayisi kutusu spec'e yazar
"""

import math
import os

from testler.ortak_test import kontrol, KOK, ORNEK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

FIXTURE = os.path.join(KOK, "testler", "veri", "kosu_ornek")


def _uyg():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _panel():
    _uyg()
    from arayuz.analiz.kinetik import KinetikKarti
    return KinetikKarti()


def _hucre(p, satir, sutun):
    return float(p.tablo.item(satir, sutun).text())


def test_keepin_hazir_veri():
    print("\n[Y6A-1] Keepin hazir verisi tabloda; toplam beta 650 pcm")
    p = _panel()
    p.kaynak.setCurrentIndex(p.kaynak.findData("keepin"))
    kontrol("6 satir", p.tablo.rowCount() == 6)
    toplam = sum(_hucre(p, i, 1) for i in range(6))
    kontrol("beta_i toplami 650.2 pcm", abs(toplam - 650.2) < 0.05, "-> %.2f" % toplam)
    kontrol("lambda_1 = 0.0124 1/s", math.isclose(_hucre(p, 0, 2), 0.0124))
    from PySide6 import QtCore
    kontrol("hazir veride tablo duzenlenemez",
            not (p.tablo.item(0, 1).flags() & QtCore.Qt.ItemIsEditable))


def test_elle_tek_grup_periyot():
    print("\n[Y6A-2] elle tek grup: periyot etiketi Inhour ile ayni")
    from cekirdek import kinetik as kin
    p = _panel()
    p.kaynak.setCurrentIndex(p.kaynak.findData("elle"))
    p.grup_sayisi.setValue(1)
    p.tablo.item(0, 1).setText("650")
    p.tablo.item(0, 2).setText("0.08")
    p.nesil_suresi.setValue(100.0)            # us
    p.birim.setCurrentIndex(p.birim.findData("pcm"))
    p.reaktivite.setValue(100.0)
    p.sure.setValue(100.0)
    p.hesapla()
    v = kin.GrupVerisi(beta=(0.0065,), lam=(0.08,), nesil_suresi=1e-4)
    t = kin.kararli_periyot(v, 0.001)
    kontrol("cozum uretildi", p.son_cozum is not None and p.son_cozum.basarili)
    kontrol("periyot etiketi Inhour ile ayni", ("%.4g s" % t) in p.sonuc_etiketi.text(),
            "-> %s / %.4g" % (p.sonuc_etiketi.text(), t))
    kontrol("grafik bir egri cizdi", len(p.eksen.get_lines()) >= 1)


def test_birim_donusumu():
    print("\n[Y6A-3] pcm <-> $ birim degisimi")
    p = _panel()
    p.kaynak.setCurrentIndex(p.kaynak.findData("keepin"))
    p.birim.setCurrentIndex(p.birim.findData("dolar"))
    p.reaktivite.setValue(0.5)
    p.birim.setCurrentIndex(p.birim.findData("pcm"))
    kontrol("0.5 $ -> 325.1 pcm (beta = 650.2 pcm)", abs(p.reaktivite.value() - 325.1) < 0.01,
            "-> %.3f" % p.reaktivite.value())
    p.birim.setCurrentIndex(p.birim.findData("dolar"))
    kontrol("geri $'a: 0.5", abs(p.reaktivite.value() - 0.5) < 1e-4)


def test_rampa_alanlari_ve_ani_kritik():
    print("\n[Y6A-4] rampa alani gorunurlugu; 1.2 $ ani kritik uyarisi")
    p = _panel()
    p.show()
    p.kaynak.setCurrentIndex(p.kaynak.findData("keepin"))
    p.tur.setCurrentIndex(p.tur.findData("basamak"))
    kontrol("basamakta rampa suresi gizli", not p.rampa_suresi.isVisible())
    p.tur.setCurrentIndex(p.tur.findData("rampa"))
    kontrol("rampada rampa suresi gorunur", p.rampa_suresi.isVisible())
    p.tur.setCurrentIndex(p.tur.findData("basamak"))
    p.birim.setCurrentIndex(p.birim.findData("dolar"))
    p.reaktivite.setValue(1.2)
    p.sure.setValue(1.0)
    p.hesapla()
    kontrol("ani kritik uyarisi gosterildi", "ANİ KRİTİK" in p.uyari_etiketi.text(),
            "-> %s" % p.uyari_etiketi.text())
    p.close()


def test_gecersiz_veri_hata_metni():
    print("\n[Y6A-5] gecersiz grup verisi: hata metni, cokme yok")
    p = _panel()
    p.kaynak.setCurrentIndex(p.kaynak.findData("elle"))
    p.grup_sayisi.setValue(1)
    p.tablo.item(0, 1).setText("650")
    p.tablo.item(0, 2).setText("0")
    p.hesapla()
    kontrol("cozum yok", p.son_cozum is None)
    kontrol("hata metni λ_i", "λ_i" in p.uyari_etiketi.text(), "-> %s" % p.uyari_etiketi.text())
    p.tablo.item(0, 2).setText("abc")
    p.hesapla()
    kontrol("sayi olmayan girdi: hata metni", bool(p.uyari_etiketi.text()))


def test_son_kosudan_al(monkeypatch):
    print("\n[Y6A-6] son kosudan al: grup verisi tabloya ve Lambda kutusuna")
    from cekirdek import kosucu
    p = _panel()
    p.kosu_kaynagi_ayarla(lambda: None)
    p.kosudan_al()
    kontrol("kosu yoksa aciklama", "koşu" in p.uyari_etiketi.text().lower(),
            "-> %s" % p.uyari_etiketi.text())
    p.kosu_kaynagi_ayarla(lambda: FIXTURE)
    p.kosudan_al()
    kontrol("grup verisi olmayan kosu: aciklama", "grup" in p.uyari_etiketi.text(),
            "-> %s" % p.uyari_etiketi.text())
    sahte = {"keff": (1.0, 1e-4), "kinetik": {
        "beta_eff": 0.0064, "beta_eff_sapma": 1e-5, "lambda": 5.5e-9, "lambda_sapma": 1e-10,
        "beta_i": [2e-4, 1e-3, 1e-3, 3e-3, 1e-3, 2e-4],
        "beta_i_sapma": [1e-5] * 6, "lambda_i": [0.0133, 0.0327, 0.121, 0.303, 0.851, 2.86],
        "lambda_i_sapma": [1e-4] * 6, "istenen_grup": 6, "kutuphane_grup": 6}}
    monkeypatch.setattr(kosucu, "sonuc_oku", lambda yol: sahte)
    p.kosudan_al()
    kontrol("kaynak 'kosu' secildi", p.kaynak.currentData() == "kosu")
    kontrol("6 satir, beta_4 = 300 pcm", p.tablo.rowCount() == 6
            and abs(_hucre(p, 3, 1) - 300.0) < 1e-6)
    kontrol("Lambda kutusu 0.0055 us", abs(p.nesil_suresi.value() - 0.0055) < 1e-9,
            "-> %r" % p.nesil_suresi.value())
    p.birim.setCurrentIndex(p.birim.findData("dolar"))
    p.reaktivite.setValue(0.5)
    p.sure.setValue(0.5)
    p.hesapla()
    kontrol("ns olcekli Lambda ile de cozum", p.son_cozum is not None and p.son_cozum.basarili)
    p.sifirla()
    kontrol("sifirla: kosu verisi silinir", p.kaynak.currentData() != "kosu"
            and p.son_cozum is None)


def test_geri_besleme_sicaklik_ekseni():
    print("\n[Y6A-7] adiyabatik geri besleme: sicaklik ekseni")
    p = _panel()
    p.kaynak.setCurrentIndex(p.kaynak.findData("keepin"))
    p.birim.setCurrentIndex(p.birim.findData("pcm"))
    p.reaktivite.setValue(200.0)
    p.sure.setValue(50.0)
    p.gb_var.setChecked(True)
    p.alfa.setValue(-2.0)
    p.hesapla()
    kontrol("cozumde sicaklik var", p.son_cozum is not None
            and p.son_cozum.sicaklik is not None)
    kontrol("ikinci eksen (DT) cizildi", len(p.figur.axes) == 2)
    kontrol("sonuc metni DT icerir", "ΔT" in p.sonuc_etiketi.text())


def test_hesap_ayari_grup_sayisi():
    print("\n[Y6A-8] Hesap ayarlari: gecikmis notron grubu kutusu spec'e yazar")
    _uyg()
    from cekirdek import sema
    from arayuz.sekme_ayar import AyarSekmesi
    s = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    s["ayarlar"]["kinetik"] = {"var": True, "nesil": 10, "gruplar": 8}
    a = AyarSekmesi()
    a.spec_yukle(s)
    kontrol("kutu dosyadaki 8'i gosterir", a.kinetik_gruplar.currentData() == 8)
    a.kinetik_gruplar.setCurrentIndex(a.kinetik_gruplar.findData(0))
    kontrol("secim spec'e yazildi", s["ayarlar"]["kinetik"]["gruplar"] == 0,
            "-> %s" % s["ayarlar"]["kinetik"])
    kontrol("kutu Gelismis icinde", a.gelismis.isAncestorOf(a.kinetik_gruplar))


def test_analiz_sekmesinde_kart():
    print("\n[Y6A-9] Analiz sekmesi kinetik kartini icerir; sifirla kartı da sifirlar")
    _uyg()
    from arayuz.sekme_analiz import AnalizSekmesi
    s = AnalizSekmesi()
    kontrol("kinetik karti var", s.icerik.isAncestorOf(s.kinetik))
    s.kinetik.kaynak.setCurrentIndex(s.kinetik.kaynak.findData("keepin"))
    s.kinetik.hesapla()
    s.sifirla()
    kontrol("proje degisince kinetik sonucu silinir", s.kinetik.son_cozum is None)


def test_ana_pencere_kosu_kaynagi():
    print("\n[Y6A-10] ana pencere: kinetik kartinin kosu kaynagi Calistir'in son dizini")
    _uyg()
    from arayuz.ana_pencere import AnaPencere
    p = AnaPencere()
    p._kaydetme_sor = lambda: True
    try:
        kontrol("kaynak = s_calistir.son_kosu_dizini",
                p.s_analiz.kinetik._kosu_kaynagi == p.s_calistir.son_kosu_dizini)
    finally:
        p.close()


HIZLI = [test_ana_pencere_kosu_kaynagi, test_keepin_hazir_veri, test_elle_tek_grup_periyot, test_birim_donusumu,
         test_rampa_alanlari_ve_ani_kritik, test_gecersiz_veri_hata_metni, test_son_kosudan_al,
         test_geri_besleme_sicaklik_ekseni, test_hesap_ayari_grup_sayisi,
         test_analiz_sekmesinde_kart]
YAVAS = []
