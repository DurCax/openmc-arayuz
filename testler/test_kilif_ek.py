# -*- coding: utf-8 -*-
"""
test_kilif_ek.py -- bugune kadar yalniz JSON ile girilen iki alanin formu.

  [KE1] Demet sayfasi: altigen demette "Kılıf" karti (demetler[].kilif: ic_duz,
        kalinlik, malzeme); kare demette gizli. Ac/kapa kilifi ekler/kaldirir;
        varsayilan kilif dogrulamadan (kilif_kontrol) temiz gecer; pinler
        sigmazsa hata kartta gorunur.
  [KE2] Tukenme sayfasi: "Ek yanan malzemeler" listesi (tukenme.ek_malzemeler);
        fisil/zehir malzemeler otomatik (isaretli, kapali); tanimsiz ad korunur.
"""

import os

from testler.ortak_test import kontrol, ORNEK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _yukle(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _demet_sekmesi(spec):
    from arayuz.sekme_demet import DemetSekmesi
    w = DemetSekmesi()
    w.spec_yukle(spec)
    return w


def test_kilif_karti():
    print("\n[KE1] Demet > Kılıf: altigen demette duzenlenir")
    _qt()
    from cekirdek.dogrula.geometri import kilif_kontrol
    spec = _yukle("sfr_met1000_demet")
    w = _demet_sekmesi(spec)
    d = spec["demetler"][0]
    kontrol("altigen: kart gorunur", not w.kilif_karti.isHidden())
    kontrol("kilif acik ve degerler spec'ten",
            w.kilif_var.isChecked() and abs(w.kilif_ic.value() - 15.0191) < 1e-9
            and abs(w.kilif_kalinlik.value() - 0.3966) < 1e-9
            and w.kilif_malzeme.currentData() == "ht9")
    olaylar = []
    w.degisti.connect(olaylar.append)
    w.kilif_kalinlik.setValue(0.5)
    kontrol("kalinlik yazildi", d["kilif"]["kalinlik"] == 0.5 and bool(olaylar),
            "-> %s" % d.get("kilif"))
    w.kilif_ic.setValue(5.0)
    kontrol("pin sigmiyor -> hata kartta", not w.kilif_hata.isHidden()
            and "sığmıyor" in w.kilif_hata.text(), "-> %s" % w.kilif_hata.text())
    w.kilif_var.setChecked(False)
    kontrol("kapatinca kilif kaldirildi", "kilif" not in d, "-> %s" % d.get("kilif"))
    kontrol("kapaliyken alanlar kapali", not w.kilif_ic.isEnabled())
    w.kilif_var.setChecked(True)
    kontrol("acinca varsayilan kilif", isinstance(d.get("kilif"), dict)
            and d["kilif"].get("malzeme"), "-> %s" % d.get("kilif"))
    kontrol("varsayilan kilif dogrulamadan temiz", kilif_kontrol(spec, d) == [],
            "-> %s" % [b.mesaj for b in kilif_kontrol(spec, d)])
    kontrol("varsayilanda hata yok", w.kilif_hata.isHidden())
    w.spec_yukle(_yukle("pwr_17x17"))
    kontrol("kare demet: kart gizli", w.kilif_karti.isHidden())


def _tukenme_sekmesi(spec):
    from arayuz.sekme_tukenme import TukenmeSekmesi
    w = TukenmeSekmesi()
    w.spec_yukle(spec)
    return w


def _ogeler(liste):
    from PySide6 import QtCore
    return {liste.item(i).data(QtCore.Qt.UserRole): (
        liste.item(i).checkState() == QtCore.Qt.Checked,
        bool(liste.item(i).flags() & QtCore.Qt.ItemIsEnabled)) for i in range(liste.count())}


def test_tukenme_ek_malzemeler():
    print("\n[KE2] Tükenme > Ek yanan malzemeler")
    _qt()
    from PySide6 import QtCore
    spec = _yukle("pwr_tukenme")
    spec["tukenme"]["ek_malzemeler"] = ["eski_ad"]
    w = _tukenme_sekmesi(spec)
    og = _ogeler(w.ek_liste)
    kontrol("uo2 otomatik: isaretli ve kapali", og.get("uo2") == (True, False), "-> %s" % og)
    kontrol("zirkaloy secilebilir, isaretsiz", og.get("zirkaloy") == (False, True))
    kontrol("tanimsiz ad listede ve isaretli", og.get("eski_ad", (False,))[0])
    kontrol("yukleme spec'i degistirmedi", spec["tukenme"]["ek_malzemeler"] == ["eski_ad"])
    olaylar = []
    w.degisti.connect(olaylar.append)
    for i in range(w.ek_liste.count()):
        if w.ek_liste.item(i).data(QtCore.Qt.UserRole) == "zirkaloy":
            w.ek_liste.item(i).setCheckState(QtCore.Qt.Checked)
    kontrol("isaretlenen spec'e yazildi (tanimsiz korunur)",
            spec["tukenme"]["ek_malzemeler"] == ["zirkaloy", "eski_ad"],
            "-> %s" % spec["tukenme"]["ek_malzemeler"])
    kontrol("degisti yayildi", bool(olaylar))
    kontrol("yanan malzemelere eklendi", "zirkaloy" in w.malzeme_bilgi.text(),
            "-> %s" % w.malzeme_bilgi.text()[:200])
    for i in range(w.ek_liste.count()):
        if w.ek_liste.item(i).data(QtCore.Qt.UserRole) == "eski_ad":
            w.ek_liste.item(i).setCheckState(QtCore.Qt.Unchecked)
    kontrol("tanimsiz ad kaldirilabilir", spec["tukenme"]["ek_malzemeler"] == ["zirkaloy"])


HIZLI = [test_kilif_karti, test_tukenme_ek_malzemeler]
YAVAS = []
