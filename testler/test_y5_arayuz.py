# -*- coding: utf-8 -*-
"""
 test_y5_arayuz.py  --  v3 Y5: bolme sihirbazi (Tukenme) ve dal tablosu karti (Analiz)

   [Y5-U1] Bolme paneli: aday cubuklar, varsayilan dosyaya YAZILMAZ; secim gidis-donus.
   [Y5-U2] Onizleme: secili pinin halka sayisi; ozet "ornek 1 -> 4" ve hacim korunumu;
           gecersiz girdide (3B olmayan modelde eksenel dilim) panel kilitlenir.
   [Y5-U3] Dal karti: Analiz sekmesinde; sonuc yokken hesapla kapali ve neden yazili.
   [Y5-U4] Dal karti girdileri: DalAyar, koşu sayisi tahmini, gecersiz deger hata.
   [Y5-U5] Dal tablosu: sahte kuyruk olaylariyla tablo, dk, hata; eski kusak yok sayilir; CSV.
"""

import copy
import os

from testler.ortak_test import ORNEK, kontrol
from testler.test_y5_bolme import _gd_pin

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _uyg():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _sekme(spec):
    _uyg()
    from arayuz.sekme_tukenme import TukenmeSekmesi
    t = TukenmeSekmesi()
    t.spec_yukle(spec)
    return t


def test_panel_varsayilan_ve_gidis_donus():
    print("\n[Y5-U1] bolme paneli: varsayilan yazilmaz, secim gidis-donus")
    from PySide6 import QtCore
    s = _gd_pin(4)
    s["tukenme"].pop("bolme")
    s["tukenme"]["var"] = True
    t = _sekme(s)
    kontrol("aday cubuk: yakit_cubugu", t.bolme._adaylar == ["yakit_cubugu"])
    t._kaydet()
    kontrol("bolme yokken anahtar yazilmadi", "bolme" not in s["tukenme"])
    t.bolme.etkin.setChecked(True)
    t.bolme.tablo.item(0, 0).setCheckState(QtCore.Qt.Checked)
    t.bolme.tablo.cellWidget(0, 1).setValue(5)
    b = s["tukenme"].get("bolme")
    kontrol("secim spec'e yazildi", b == {"cubuklar": [{"cubuk": "yakit_cubugu", "halka": 5,
                                                      "tur": "esit_hacim"}]}, repr(b))
    t2 = _sekme(copy.deepcopy(s))
    kontrol("gidis-donus: etkin, 5 halka", t2.bolme.etkin.isChecked()
            and t2.bolme.tablo.cellWidget(0, 1).value() == 5
            and t2.bolme.tablo.item(0, 0).checkState() == QtCore.Qt.Checked)
    t.bolme.etkin.setChecked(False)
    kontrol("kapatinca anahtar kalkar", "bolme" not in s["tukenme"])


def test_onizleme_ve_ozet():
    print("\n[Y5-U2] onizleme: halka sayisi; ozet: ornek ve hacim korunumu; 2B'de dilim kilitli")
    from PySide6 import QtCore
    s = _gd_pin(3, "esit_kalinlik")
    s["tukenme"]["var"] = True
    t = _sekme(s)
    p = t.bolme
    kontrol("onizleme 3 halka + kilif + su = 5 bolge", len(p.onizleme.halkalar) == 5,
            repr(len(p.onizleme.halkalar)))
    kontrol("3 bolunmus halka", sum(h.bolunmus for h in p.onizleme.halkalar) == 3)
    kontrol("ozet: 1 -> 3", "1 → 3" in p.ozet.text(), p.ozet.text())
    kontrol("ozet: hacim korunumu", "analitik hacme eşit" in p.ozet.text())
    kontrol("2B modelde eksenel dilim kilitli", not p.dilim.isEnabled()
            and "3B" in p.dilim_not.text(), p.dilim_not.text())
    t.spec["kor"]["yukseklik"] = 100.0
    p.doldur(t.spec)
    kontrol("3B modelde eksenel dilim acik", p.dilim.isEnabled())
    p.dilim.setValue(2)
    kontrol("ozet: 1 -> 6 (3 halka x 2 dilim)", "1 → 6" in p.ozet.text(), p.ozet.text())
    kontrol("dilim spec'e yazildi", t.spec["tukenme"]["bolme"]["eksenel"] == {"dilim": 2})
    p.tablo.item(0, 0).setCheckState(QtCore.Qt.Unchecked)
    p.dilim.setValue(1)
    kontrol("secim yok: yonerge metni", "en az bir" in p.ozet.text(), p.ozet.text())


def _spec_pin():
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))


def test_dal_karti_sonuc_yok():
    print("\n[Y5-U3] dal karti Analiz'de; sonuc yokken kapali")
    _uyg()
    from arayuz.analiz.sekme import AnalizSekmesi
    a = AnalizSekmesi()
    a.kapi_ayarla(lambda: (True, "hazir"))
    a.spec_ayarla(_spec_pin(), "/tmp/y5_yok/proje.json")
    kontrol("kart var", type(a.dal).__name__ == "DalKarti")
    kontrol("hesapla kapali", not a.dal.d_hesapla.isEnabled())
    kontrol("neden yazili", "Tükenme sonucu yok" in a.dal.kaynak.text(), a.dal.kaynak.text())


def _kart():
    _uyg()
    from arayuz.analiz.dal import DalKarti
    k = DalKarti()
    k.kapi_ayarla(lambda: (True, "hazir"))
    s = _spec_pin()
    k.spec_ayarla(s, None)
    k._h5, k._taban = "/tmp/yok.h5", s          # sonuc varmis gibi (kosu yok)
    return k


def _adim_ekle(k, n):
    from PySide6 import QtCore, QtWidgets
    k.adimlar.clear()
    for i in range(n):
        o = QtWidgets.QListWidgetItem("adim %d" % i)
        o.setData(QtCore.Qt.UserRole, i)
        o.setFlags(o.flags() | QtCore.Qt.ItemIsUserCheckable)
        o.setCheckState(QtCore.Qt.Checked)
        k.adimlar.addItem(o)


def test_dal_girdileri():
    print("\n[Y5-U4] dal girdileri: DalAyar, tahmin, hata")
    from PySide6 import QtCore
    k = _kart()
    _adim_ekle(k, 3)
    k._tahmin()
    a = k.ayar()
    kontrol("adimlar 0,1,2", a.adimlar == (0, 1, 2))
    kontrol("degiskenler: T_yakit ve C_bor (oneriler)", [d.ad for d in a.degiskenler]
            == ["T_yakit", "C_bor"], repr([d.ad for d in a.degiskenler]))
    kontrol("tek bicim: 3 x (1 + 3 + 3) = 21 kosu", "21 koşu" in k.tahmin_etiketi.text(),
            k.tahmin_etiketi.text())
    k.bicim.setCurrentIndex(k.bicim.findData("kartezyen"))
    kontrol("kartezyen: 3 x (1 + 9) = 30", "30 koşu" in k.tahmin_etiketi.text(),
            k.tahmin_etiketi.text())
    k.degisken_degerleri["bor_ppm"].setText("0, abc")
    kontrol("gecersiz deger: hesapla kapali, hata gorunur", not k.d_hesapla.isEnabled()
            and "sayısal" in k.tahmin_etiketi.text(), k.tahmin_etiketi.text())
    k.degisken_degerleri["bor_ppm"].setText("0, 500")
    kontrol("duzelince acik", k.d_hesapla.isEnabled())
    for i in range(k.adimlar.count()):
        k.adimlar.item(i).setCheckState(QtCore.Qt.Unchecked)
    kontrol("adim secilmediyse kapali", not k.d_hesapla.isEnabled())


def _durum(kimlik, adim, nokta, degerler, k, kusak, asama="bitti", hata=None):
    from cekirdek import kuyruk
    return kuyruk.IsDurumu(kimlik=kimlik, ad=kimlik, dizin="/x", asama=kuyruk.Asama(asama),
                           k=k, hata=hata, seq=1,
                           etiket={"dal": {"adim": adim, "yanma": 10.0 * adim, "zaman_d": 25.0 * adim,
                                           "nokta": nokta, "degerler": degerler, "notlar": []},
                                   "kusak": kusak})


def test_dal_tablosu_ve_csv(gecici=None):
    print("\n[Y5-U5] dal tablosu: sahte olaylar, dk, hata, kusak, CSV")
    import tempfile
    k = _kart()
    liste = [_durum("a", 0, 0, {}, (1.2, 0.0003), 0), _durum("b", 0, 1, {"T_yakit": 900.0},
                                                          (1.19, 0.0004), 0),
             _durum("c", 0, 2, {"T_yakit": 1200.0}, None, 0, "basarisiz", "koşu başarısız")]
    k._durumlar = {d.kimlik: d for d in liste}
    for d in liste:
        k._olay(d)
    kontrol("3 satir", k.tablo.rowCount() == 3)
    basliklar = [k.tablo.horizontalHeaderItem(i).text() for i in range(k.tablo.columnCount())]
    kontrol("baslik: T_yakit sutunu", "T_yakit" in basliklar, repr(basliklar))
    kontrol("dk -1000 pcm", "-1000" in k.tablo.item(1, k.tablo.columnCount() - 1).text(),
            k.tablo.item(1, k.tablo.columnCount() - 1).text())
    kontrol("basarisiz satirda hata metni", "koşu başarısız" in k.tablo.item(2, 3).text()
            or "koşu başarısız" in k.tablo.item(2, 4).text())
    n = k.tablo.rowCount()
    k._olay(_durum("d", 1, 0, {}, (1.1, 0.0003), kusak=99))        # kimlik bilinmiyor
    kontrol("bilinmeyen kimlik yok sayildi", k.tablo.rowCount() == n)
    with tempfile.TemporaryDirectory() as d:
        yol = k.csv_kaydet(os.path.join(d, "dal.csv"))
        metin = open(yol, encoding="utf-8-sig").read()
        kontrol("CSV baslik ve 3 satir", metin.splitlines()[0].startswith("adim,zaman_gun")
                and len(metin.strip().splitlines()) == 4, metin)
    k.sifirla()
    kontrol("sifirla tabloyu temizler", k.tablo.rowCount() == 0 and not k._satirlar)


HIZLI = [test_panel_varsayilan_ve_gidis_donus, test_onizleme_ve_ozet, test_dal_karti_sonuc_yok,
         test_dal_girdileri, test_dal_tablosu_ve_csv]
YAVAS = []
