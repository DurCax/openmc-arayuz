# -*- coding: utf-8 -*-
"""
 test_y8_arayuz.py  --  v3 Y8: Analiz > "Grup sabitleri ve random ray" karti

   - kart Analiz sekmesinde; kapsam listesi modelden (kor: demet basina)
   - girdiler -> MgxsAyar / RRAyar (ek turler isaretli kutulardan)
   - sonuc yokken MG/RR/CSV kapali; sonuc gelince tablo, ozet, dugmeler
   - tur suzgeci tabloyu suzer; karsilastirma tablosu (CE/MG/RR)
   - eski kusagin (proje degisti) olayi yok sayilir; sifirla temizler
   - CSV kaydet dosyayi kopyalar
 Kosu yok (sahte IsDurumu ve MgxsSonuc).
"""

import os

from testler.ortak_test import kontrol, ORNEK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _uyg():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _spec(ad="pwr_pinhucre.json"):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad))


def _kart(ad="pwr_pinhucre.json"):
    _uyg()
    from arayuz.analiz.mgxs import MgxsKarti
    k = MgxsKarti()
    k.kapi_ayarla(lambda: (True, "hazir"))
    k.spec_ayarla(_spec(ad), None)
    return k


def _sonuc(dizin):
    from cekirdek import mgxs_k, mgxs_uret as mu
    a = mu.MgxsAyar(True, "demet", "CASMO-2")
    satirlar = (mu.Satir("Universe 1", "u1", "total", 1, None, 0.53, 0.001),
                mu.Satir("Universe 1", "u1", "total", 2, None, 1.37, 0.002),
                mu.Satir("Universe 1", "u1", mu.SACILMA_TURU, 1, 2, 0.02, 0.0001))
    csv = os.path.join(dizin, mu.CSV_ADI)
    mu.csv_yaz(satirlar, csv, a)
    return mu.MgxsSonuc(a, (0.0, 0.625, 2e7), {1: "u1"}, satirlar,
                        mgxs_k.Deger(1.358, 0.0015), mgxs_k.Deger(1.356, 0.004),
                        mgxs_k.Deger(1.3589, 0.007), dizin, ("deneme notu",))


def _durum(tur, kusak, k=(1.3, 0.001), sonuc=None):
    from cekirdek import kuyruk
    return kuyruk.IsDurumu(kimlik=tur, ad=tur, dizin="/x", asama=kuyruk.Asama.BITTI, k=k,
                           sonuc=sonuc, baslangic=0.0, bitis=5.0,
                           etiket={"y8": tur, "kusak": kusak}, seq=1)


def test_kart_analiz_sekmesinde():
    print("\n[Y8A-1] Analiz sekmesi MgxsKarti icerir; spec_ayarla karta iletilir")
    _uyg()
    from arayuz.analiz.sekme import AnalizSekmesi
    s = AnalizSekmesi()
    s.spec_ayarla(_spec("pwr_smr_kor.json"))
    kontrol("kart var", type(s.mgxs).__name__ == "MgxsKarti")
    kontrol("kor: 3 kapsam (tum + 2 demet)", s.mgxs.kapsam.count() == 3,
            "-> %d" % s.mgxs.kapsam.count())


def test_girdiler_ayara():
    print("\n[Y8A-2] girdiler -> MgxsAyar (ek tur isaretli), RRAyar")
    from PySide6 import QtCore
    k = _kart()
    k.bolge.setCurrentIndex(k.bolge.findData("hucre"))
    k.grup.setCurrentIndex(k.grup.findData("CASMO-8"))
    k.duzeltme.setCurrentIndex(k.duzeltme.findData("P0"))
    k.turler.item(1).setCheckState(QtCore.Qt.Checked)
    a = k.ayar()
    kontrol("bolge/grup/duzeltme", (a.bolge, a.grup_yapisi, a.duzeltme) == ("hucre", "CASMO-8", "P0"),
            "-> %r" % (a,))
    kontrol("ek tur kappa-fission", a.turler == ("kappa-fission",), "-> %r" % (a.turler,))
    k.rr_sekil.setCurrentIndex(k.rr_sekil.findData("linear"))
    kontrol("RR kaynak sekli", k.rr_ayari().kaynak_sekli == "linear")


def test_sonuc_gosterimi_ve_dugmeler():
    print("\n[Y8A-3] sonuc yokken MG/RR kapali; sonuc -> tablo, ozet, suzgec, dugmeler acik")
    import tempfile
    k = _kart()
    kontrol("baslangicta MG kapali", not k.d_mg.isEnabled())
    kontrol("uret acik", k.d_uret.isEnabled())
    with tempfile.TemporaryDirectory() as d:
        k.sonuc_goster(_sonuc(d))
        kontrol("tablo 3 satir", k.tablo.rowCount() == 3)
        kontrol("MG ve RR acik", k.d_mg.isEnabled() and k.d_rr.isEnabled())
        kontrol("ozette k_inf ve not", "1.35890" in k.ozet.text() and "deneme notu" in k.ozet.text())
        k.tur_suzgeci.setCurrentIndex(k.tur_suzgeci.findData("total"))
        kontrol("suzgec: total 2 satir", k.tablo.rowCount() == 2)
        hedef = os.path.join(d, "kopya.csv")
        kontrol("CSV kaydet", k.csv_kaydet(hedef) == hedef and os.path.isfile(hedef))


def test_karsilastirma_ve_kusak():
    print("\n[Y8A-4] olaylar: karsilastirma tablosu; eski kusak yok sayilir; sifirla temizler")
    k = _kart()
    k._olay(_durum("ce", k._kusak, (1.30, 0.001)))
    k._olay(_durum("mg", k._kusak, (1.299, 0.001)))
    kontrol("2 karsilastirma satiri", k.karsi.rowCount() == 2)
    kontrol("MG farki -100", k.karsi.item(1, 3).text() == "-100", "-> %s" % k.karsi.item(1, 3).text())
    k.sifirla()
    k._olay(_durum("rr", k._kusak - 1))
    kontrol("eski kusak yok sayildi", k.karsi.rowCount() == 0 and not k._durumlar)
    kontrol("sifirla sonucu sildi", k.sonuc is None and not k.d_csv.isEnabled())


def test_kapi_kapaliyken_uret_kapali():
    print("\n[Y8A-5] kapi kapali: uret dugmesi kapali, neden gosterilir")
    k = _kart()
    k.kapi_ayarla(lambda: (False, "veri yok"))
    kontrol("uret kapali", not k.d_uret.isEnabled())
    kontrol("neden yazili", "veri yok" in k.durum_etiketi.text())


HIZLI = [test_kart_analiz_sekmesinde, test_girdiler_ayara, test_sonuc_gosterimi_ve_dugmeler,
         test_karsilastirma_ve_kusak, test_kapi_kapaliyken_uret_kapali]
YAVAS = []
