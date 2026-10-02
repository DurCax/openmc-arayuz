# -*- coding: utf-8 -*-
"""
 test_k3_arayuz.py  --  v3 K3: pin tablosu ve yanmaya gore pin gucu (arayuz)

   [PA1] Guc haritasi altinda pin tablosu: satir sayisi = konum sayisi; hucre
         degerleri haritanin bagil degerleri; sicak pin satiri isaretli.
   [PA2] Haritada pine tikla -> tabloda o satir secili, ayrinti etiketi o pinin
         degerleri; tablodan secim -> haritada secim isareti.
   [PA3] Sirala (bagil guc azalan -> ilk satir sicak pin), filtrele (metin).
   [PA4] Ceyrek katlama kutusu: simetrik 17x17'de etkin, 72 yorunge; dilim
         kaydiricisi tablonun dilim sutununu degistirir.
   [PA5] Disa aktarma: CSV dosyasi (Excel yalniz openpyxl varsa secenek).
   [PA6] Yanmaya gore: adim secici (3 adim), adim tablosu o adimin degerleri,
         secili pin icin guc-yanma serisi, adim basina F_ΔH/F_q tablosu,
         adim × pin CSV.
   [PA7] Tukenme sekmesi onceki sonucu okurken adim basina pin gucunu de okur
         ve sonuc kartinda gosterir (gercek fixture dizini).

 Monte Carlo KOSULMAZ (fixture'lar: testler/veri/kosu_ornek, tukenme_guc_ornek).
"""

import csv
import json
import os
import shutil

from testler.ortak_test import KOK, kontrol

KOSU = os.path.join(KOK, "testler", "veri", "kosu_ornek")
TUKENME = os.path.join(KOK, "testler", "veri", "tukenme_guc_ornek")


def _uyg():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _harita():
    _uyg()
    from arayuz.guc_harita import GucHaritaWidget
    from cekirdek import kosucu
    with open(os.path.join(KOSU, "spec.json"), encoding="utf-8") as f:
        spec = json.load(f)
    s = kosucu.sonuc_oku(os.path.join(KOSU, "statepoint.40.h5"))
    w = GucHaritaWidget()
    w.sonuc_ayarla(s, spec)
    return w, s


def _hucre(tablo_w, satir, sutun_adi):
    """Gorunen (proxy) satirdaki sutunun ham degeri (UserRole)."""
    from PySide6 import QtCore
    model = tablo_w.gorunum.model()
    sutun = tablo_w.sutun_no(sutun_adi)
    return model.data(model.index(satir, sutun), QtCore.Qt.UserRole)


def test_tablo_haritayla_ayni():
    print("\n[PA1] pin tablosu = harita")
    w, s = _harita()
    f = s["guc"]["faktorler"]
    t = w.pin_tablosu
    kontrol("264 satir", t.gorunum.model().rowCount() == 264,
            "-> %d" % t.gorunum.model().rowCount())
    farkli = 0
    for i in range(t.gorunum.model().rowCount()):
        a = t.satir_anahtari(i)
        if _hucre(t, i, "bagil") != f["bagil"][a][0]:
            farkli += 1
    kontrol("butun bagil hucreleri haritanin degeri", farkli == 0, "-> %d farkli" % farkli)
    kontrol("W ve q′ sutunlari var (toplam guc girili)",
            t.sutun_no("W") is not None and t.sutun_no("q") is not None)
    kontrol("sicak pin satiri isaretli", t.sicak_satir() is not None
            and t.satir_anahtari(t.sicak_satir()) == f["sicak_cubuk"])


def test_tikla_ve_sec():
    print("\n[PA2] haritada tikla -> tablo; tablodan sec -> harita")
    w, s = _harita()
    f = s["guc"]["faktorler"]
    sicak = f["sicak_cubuk"]
    w.haritada_tikla(sicak[0] + 1, sicak[1] + 1)       # kare tek demet: izgara koordinati
    kontrol("tikla: secili pin sicak pin", w.secili_pin == sicak, "-> %r" % (w.secili_pin,))
    kontrol("tabloda secili satir sicak pin", w.pin_tablosu.secili_anahtar() == sicak)
    kontrol("ayrinti etiketi pinin degerini yazar",
            ("%.4f" % f["bagil"][sicak][0]) in w.pin_tablosu.ayrinti.text(),
            w.pin_tablosu.ayrinti.text()[:120])
    w.haritada_tikla(-50.0, -50.0)
    kontrol("bos yere tiklama secimi degistirmez", w.secili_pin == sicak)
    baska = (0, 0)
    w.pin_tablosu.sec(baska)
    kontrol("tablodan secim haritaya gecer", w.secili_pin == baska)
    kontrol("haritada secim isareti cizildi", w.secim_isareti is not None)


def test_sirala_filtrele():
    print("\n[PA3] sirala ve filtrele")
    from PySide6 import QtCore
    w, s = _harita()
    t = w.pin_tablosu
    t.gorunum.sortByColumn(t.sutun_no("bagil"), QtCore.Qt.DescendingOrder)
    kontrol("azalan bagil: ilk satir sicak pin",
            t.satir_anahtari(0) == s["guc"]["faktorler"]["sicak_cubuk"])
    t.suzgec.setText("x = 17, y = 17")
    kontrol("metin suzgeci: tek satir", t.gorunum.model().rowCount() == 1,
            "-> %d" % t.gorunum.model().rowCount())
    t.suzgec.setText("")
    kontrol("suzgec temizlenince 264", t.gorunum.model().rowCount() == 264)


def test_katlama_ve_dilim():
    print("\n[PA4] ceyrek katlama ve dilim sutunu")
    w, s = _harita()
    t = w.pin_tablosu
    kontrol("katlama kutusu etkin (simetri dogrulandi)", t.katla.isEnabled(), t.katla.toolTip())
    t.katla.setChecked(True)
    kontrol("katli: 72 satir", t.gorunum.model().rowCount() == 72,
            "-> %d" % t.gorunum.model().rowCount())
    t.katla.setChecked(False)
    i = w.gorunum.findData("dilim")
    w.gorunum.setCurrentIndex(i)
    w.dilim.setValue(3)
    a = t.satir_anahtari(0)
    beklenen = s["guc"]["faktorler"]["bagil_eksenel"][a][2][0]
    kontrol("dilim 3 sutunu bagil_eksenel[2]", _hucre(t, 0, "dilim_bagil") == beklenen,
            "-> %r / %r" % (_hucre(t, 0, "dilim_bagil"), beklenen))


def test_disa_aktar(gecici):
    print("\n[PA5] CSV disa aktarma")
    from cekirdek import guc_tablo
    w, _s = _harita()
    yol = os.path.join(gecici, "pin.csv")
    w.pin_tablosu.kaydet_yola(yol)
    with open(yol, encoding="utf-8") as f:
        satirlar = list(csv.reader(f))
    kontrol("CSV: baslik + 264", len(satirlar) == 265, "-> %d" % len(satirlar))
    kontrol("dosya suzgecleri: Excel yalniz openpyxl varsa",
            ("xlsx" in w.pin_tablosu.dosya_suzgeci()) == guc_tablo.excel_var())


def _yanma_widget():
    _uyg()
    from arayuz.tukenme_pin_gucu import PinGucuYanma
    from cekirdek import tukenme_guc
    with open(os.path.join(TUKENME, "tukenme_spec.json"), encoding="utf-8") as f:
        spec = json.load(f)
    s = tukenme_guc.adim_gucleri(TUKENME, spec)
    w = PinGucuYanma()
    w.ayarla(s)
    return w, s


def test_yanmaya_gore(gecici):
    print("\n[PA6] adim secici, seri, F tablosu, CSV")
    w, s = _yanma_widget()
    kontrol("adim secici 3 adim", w.adim.count() == 3)
    w.adim.setCurrentIndex(2)
    a2 = s["adimlar"][2]
    t = w.pin_tablosu
    kontrol("adim 2 tablosu o adimin degerleri",
            all(_hucre(t, i, "bagil") == a2["guc"]["faktorler"]["bagil"][t.satir_anahtari(i)][0]
                for i in range(t.gorunum.model().rowCount())))
    sicak = a2["guc"]["faktorler"]["sicak_cubuk"]
    t.sec(sicak)
    kontrol("secili pin serisi 3 nokta", len(w.seri_noktalari()) == 3,
            "-> %r" % (w.seri_noktalari(),))
    kontrol("F tablosu 3 satir (F_ΔH, F_q)", w.faktor_tablosu.rowCount() == 3)
    yol = os.path.join(gecici, "adim.csv")
    w.kaydet_yola(yol)
    with open(yol, encoding="utf-8") as f:
        kontrol("adim × pin CSV: 73 satir", len(list(csv.reader(f))) == 73)
    w.ayarla(None)
    kontrol("sonuc yokken gizli/bos", w.adim.count() == 0)


def test_tukenme_sekmesinde(gecici):
    print("\n[PA7] tukenme sekmesi adim basina pin gucunu gosterir")
    _uyg()
    from arayuz.sekme_tukenme import TukenmeSekmesi
    with open(os.path.join(TUKENME, "tukenme_spec.json"), encoding="utf-8") as f:
        spec = json.load(f)
    spec["calistirma"]["dizin"] = os.path.join(gecici, "k")
    shutil.copytree(TUKENME, os.path.join(gecici, "k_tukenme"))
    t = TukenmeSekmesi()
    t.spec_yukle(spec)
    t.bekle()
    w = getattr(t, "pin_gucu", None)
    kontrol("pin gucu bolumu kuruldu ve gorunur", w is not None and not w.isHidden())
    kontrol("3 adim okundu", w is not None and w.adim.count() == 3)


def test_tam_kor_tiklama():
    print("\n[PA8] tam kor: cubuk ve demet gorunumunde tikla")
    _uyg()
    from cekirdek import guc
    from arayuz.guc_harita import GucHaritaWidget
    from testler.test_guc_kor import _kare_2x2_sentetik
    d = guc.dagilim_oku(_kare_2x2_sentetik())
    f = guc.tepe_faktorleri(d)
    w = GucHaritaWidget()
    w.sonuc_ayarla({"guc": {"dagilim": d, "faktorler": f, "korunum": 0.0}})
    t = w.pin_tablosu
    kontrol("tam kor tablosunda demet sutunu", t.sutun_no("demet") is not None)
    w.olcek.setCurrentIndex(w.olcek.findData("cubuk"))
    x, y = guc.cubuk_merkezi(d, f["sicak_cubuk"])
    kontrol("cubuk gorunumu: tiklanan sicak cubuk", w.haritada_tikla(x, y) == f["sicak_cubuk"])
    w.olcek.setCurrentIndex(w.olcek.findData("demet"))
    demet = f["demetler"][f["sicak_demet"]]
    x, y = guc.demet_merkezi(d, f["sicak_demet"])
    kontrol("demet gorunumu: demetin tepe cubugu secilir",
            w.haritada_tikla(x, y) == demet["tepe_cubuk"] and w.secili_pin == demet["tepe_cubuk"])
    kontrol("secim isareti yeniden cizimde korunur", w.secim_isareti is not None)


HIZLI = [test_tam_kor_tiklama, test_tablo_haritayla_ayni, test_tikla_ve_sec, test_sirala_filtrele,
         test_katlama_ve_dilim, test_disa_aktar, test_yanmaya_gore, test_tukenme_sekmesinde]
YAVAS = []
