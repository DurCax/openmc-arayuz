# -*- coding: utf-8 -*-
"""
 test_y4_arayuz.py  --  v3 Y4: Tukenme sekmesi genisletmeleri (arayuz)

   [Y4-U1] Entegrator kutusu tukenme_ayar.ENTEGRATORLER'in 8 secenegini tasir.
   [Y4-U2] Gidis-donus: Y4 anahtari olmayan spec kaydedilince Y4 anahtari
           EKLENMEZ; sogutma/surdur/hizli/arama girilince yazilir ve yeniden
           yuklenince ayni gorunur. SI satiri yalniz SI-* secilince gorunur.
   [Y4-U3] Cikti karti: K3 fixture'inda (3 adim) Hesapla -> tablo 3 satir,
           doz/atik metni, CSV etkin; kaynak yokken Hesapla kapali.
"""

import copy
import json
import os

from testler.ortak_test import KOK, ORNEK, kontrol

FIXTURE = os.path.join(KOK, "testler", "veri", "tukenme_guc_ornek")
Y4_ANAHTARLARI = {"sogutma", "surdur", "hizli_kip", "kritik_arama", "si_ic_adim"}


def _uyg():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _sekme(spec):
    from arayuz.sekme_tukenme import TukenmeSekmesi
    t = TukenmeSekmesi()
    t.spec_yukle(spec)
    return t


def _spec():
    from cekirdek import sema
    s = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    s["tukenme"]["var"] = True
    return s


def test_entegrator_secenekleri():
    print("\n[Y4-U1] entegrator kutusu: 8 secenek")
    _uyg()
    from cekirdek import tukenme_ayar as ta
    t = _sekme(_spec())
    kodlar = [t.entegrator.itemData(i) for i in range(t.entegrator.count())]
    kontrol("8 entegrator", kodlar == list(ta.ENTEGRATORLER), repr(kodlar))


def test_gidis_donus():
    print("\n[Y4-U2] Y4 ayarlari gidis-donus; varsayilan yazilmaz")
    _uyg()
    s = _spec()
    t = _sekme(s)
    t._kaydet()
    kontrol("varsayilanlar dosyaya yazilmadi", not Y4_ANAHTARLARI & set(s["tukenme"]),
            repr(sorted(set(s["tukenme"]) & Y4_ANAHTARLARI)))
    t.y4.sogutma.setText("1, 10")
    t.y4.sogutma.editingFinished.emit()
    t.y4.surdur.setChecked(True)
    t.y4.arama_var.setChecked(True)
    kontrol("sogutma yazildi", s["tukenme"].get("sogutma") == {"adimlar": [1.0, 10.0], "birim": "d"},
            repr(s["tukenme"].get("sogutma")))
    kontrol("surdur ve arama yazildi", s["tukenme"].get("surdur") is True
            and s["tukenme"]["kritik_arama"]["var"] is True
            and s["tukenme"]["kritik_arama"]["hedef"] == "su")
    kontrol("ozet: 8 adim x 2 + 0 (son adim sogutma) ve sogutma notu",
            "16 transport" in t.adim_ozet.text() and "2 soğuma adımı" in t.adim_ozet.text(),
            t.adim_ozet.text())
    t2 = _sekme(copy.deepcopy(s))
    kontrol("yeniden yukleme: ayni gorunur", t2.y4.sogutma.text() == "1, 10"
            and t2.y4.surdur.isChecked() and t2.y4.arama_var.isChecked())
    i = t.entegrator.findData("si_celi")
    t.entegrator.setCurrentIndex(i)
    kontrol("SI satiri SI'de gorunur", t.y4.form.isRowVisible(t.y4.si_adim))
    t.entegrator.setCurrentIndex(t.entegrator.findData("cecm"))
    kontrol("SI satiri CECM'de gizli", not t.y4.form.isRowVisible(t.y4.si_adim))


def test_cikti_karti():
    print("\n[Y4-U3] cikti karti: Hesapla -> tablo, doz/atik, CSV")
    _uyg()
    from arayuz.tukenme_cikti_panel import TukenmeCiktiPaneli
    p = TukenmeCiktiPaneli()
    kontrol("kaynak yokken Hesapla kapali", not p.hesapla.isEnabled())
    with open(os.path.join(FIXTURE, "tukenme_spec.json"), encoding="utf-8") as f:
        spec = json.load(f)
    p.kaynak_ayarla((os.path.join(FIXTURE, "depletion_results.h5"), spec))
    p.hesapla_tikla()
    kontrol("tablo 3 satir", p.tablo.rowCount() == 3, "-> %d; %s" % (p.tablo.rowCount(),
                                                                  p.durum.text()))
    kontrol("doz ve atik sinifi metni", "Gy(hava)/h" in p.doz.text(), p.doz.text())
    kontrol("CSV etkin", p.csv.isEnabled())
    kontrol("CASL zinciri notu gorunur", "CASL" in p.durum.text(), p.durum.text())
    p.seri.setCurrentIndex(p.seri.findData("foton"))
    kontrol("grafik ciziliyor", len(p.eksen.lines) >= 1)


HIZLI = [test_entegrator_secenekleri, test_gidis_donus, test_cikti_karti]
VERI_GEREKEN = [test_cikti_karti]
ZINCIR_GEREKEN = [test_cikti_karti]
