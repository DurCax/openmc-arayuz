# -*- coding: utf-8 -*-
"""
test_grup_formu.py -- Gelismis geometri editorunun grup formu: daldirma grubu
degeri YUZDEDIR (cekirdek: grup degeri kontrol cubugunun `daldirma` alanini,
%0 cekilmis .. %100 tam dalmis, ezer; tarama_agac._daldirma_siniri 0..100).
Donme grubu derecedir. Hata (Dalga 3, 13b bildirdi): daldirma grubunda kutu
"°" gosteriyor, aralik 0..1e5 ve aciklama "daldırma derinliği [cm]" diyordu.
"""

import os

from testler.ortak_test import kontrol

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _form():
    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.geometri.form_yerlesim import GrupFormu
    f = GrupFormu()
    f.spec = {"cubuklar": [{"ad": "kc", "tur": "kontrol"}]}
    f._yukleniyor = True          # FormTabani.yukle gibi: doldururken spec'e yazma
    return f


def test_daldirma_grubu_yuzde():
    print("\n[GF1] Grup formu: daldirma grubu yuzde, donme grubu derece")
    f = _form()
    f.doldur({"ad": "g1", "tur": "daldirma", "deger": 50.0, "uyeler": []})
    kutu = f.deger.kutu
    kontrol("daldirma: birim '%'", f.deger.birim_etiketi.text() == "%",
            "-> %r" % f.deger.birim_etiketi.text())
    kontrol("daldirma: aralik 0..100", (kutu.minimum(), kutu.maximum()) == (0.0, 100.0),
            "-> %s" % ((kutu.minimum(), kutu.maximum()),))
    kontrol("daldirma: deger 50, kaydirici 500", kutu.value() == 50.0
            and f.kaydirici.maximum() == 1000 and f.kaydirici.value() == 500)
    kontrol("daldirma: aciklama yuzde diyor (cm degil)",
            "%" in f.aciklama.text() and "[cm]" not in f.aciklama.text(),
            "-> %r" % f.aciklama.text())
    from arayuz.geometri import form_yerlesim
    eski = form_yerlesim.duzenle.yerlesim_adlari
    form_yerlesim.duzenle.yerlesim_adlari = lambda _agac: ["tambur_1"]
    try:
        f.doldur({"ad": "g2", "tur": "donme", "deger": 90.0, "uyeler": []})
    finally:
        form_yerlesim.duzenle.yerlesim_adlari = eski
    kontrol("donme: birim '°', aralik -360..360", f.deger.birim_etiketi.text() == "°"
            and (kutu.minimum(), kutu.maximum()) == (-360.0, 360.0))
    f.deleteLater()


HIZLI = [test_daldirma_grubu_yuzde]
YAVAS = []
