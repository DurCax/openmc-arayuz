# -*- coding: utf-8 -*-
"""
test_qa14.py -- Ajan 14 (ogrenci QA) bulgulari (Dalga 4 duzeltme).

  [QA3a] Elle eklenen 'vv_ealf' tally'si (fisyon skoru yok): EALF okunamaz ama
         V&V ozeti DUSMEZ; USL nedeni tally sorununu acikca soyler (eskiden
         ValueError yutuluyor, K6-K14 "V&V kumesi yok" oluyordu).
  [QA3b] Panel: ayni adli gecersiz tally varken "EALF tally'sini duzelt" gorunur;
         onaylaninca gecersiz tally gecerli tanimla degisir.

Monte Carlo KOSULMAZ (openmc.Tally nesnesi bellekte kurulur; StatePoint taklit).
"""

import contextlib
import json
import os
import tempfile

from testler.ortak_test import kontrol, KOK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
FIXTURE = os.path.join(KOK, "testler", "veri", "kosu_ornek")


def _elle_tally():
    import openmc
    t = openmc.Tally(name="vv_ealf")
    t.filters = [openmc.EnergyFilter([1e-5, 0.625, 1e5, 2e7])]
    t.scores = ["flux"]
    return t


@contextlib.contextmanager
def _sahte_statepoint(tally):
    import openmc

    class _SP(object):
        def __init__(self, _yol):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get_tally(self, name=None):
            if name != tally.name:
                raise LookupError(name)
            return tally
    eski = openmc.StatePoint
    dizin = tempfile.mkdtemp(prefix="qa3_")
    open(os.path.join(dizin, "statepoint.10.h5"), "w").close()
    openmc.StatePoint = _SP
    try:
        yield dizin
    finally:
        openmc.StatePoint = eski


def _spec():
    with open(os.path.join(FIXTURE, "spec.json"), encoding="utf-8") as f:
        return json.load(f)


def test_elle_ealf_tally_vv_dusurmez():
    print("\n[QA3a] Elle eklenmis vv_ealf (flux): V&V ozeti kurulur, neden acik")
    from cekirdek.vv import aoa, kume
    with _sahte_statepoint(_elle_tally()) as dizin:
        ealf, neden = aoa.ealf_ayrintili(dizin)
        kontrol("EALF None, neden 'fission' skoru", ealf is None and neden
                and "fission" in neden, "-> %r %r" % (ealf, neden))
        vv, _u = kume.uygulama_ozeti(_spec(), dizin)
    kontrol("VVOzeti var (None degil)", vv is not None)
    kontrol("USL nedeni tally sorununu ve duzeltmeyi soyler", vv.usl is None
            and "fission" in vv.usl_neden and "vv_ealf" in vv.usl_neden, "-> %s" % vv.usl_neden)
    with _sahte_statepoint(_elle_tally()) as dizin:
        kontrol("tally yoksa (baska ad) neden None", aoa.ealf_ayrintili(
            os.path.join(dizin, "yok"))[1] is None)
    gecerli = aoa.ealf_tally_tanimi()
    kontrol("tanim gecerliligi: oneri gecerli, flux gecersiz", aoa.ealf_tanimi_gecerli(gecerli)
            and not aoa.ealf_tanimi_gecerli(dict(gecerli, skorlar=["flux"])))


def test_panel_gecersiz_tally_duzeltir():
    print("\n[QA3b] Panel: gecersiz vv_ealf -> 'duzelt'; onay -> degisir")
    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.sekme_calistir import CalistirSekmesi
    from cekirdek import sema
    from cekirdek.vv import aoa
    w = CalistirSekmesi()
    spec = sema.tamamla(_spec())
    elle = dict(aoa.ealf_tally_tanimi(), skorlar=["flux"])
    spec["tallyler"] = list(spec.get("tallyler") or []) + [elle]
    w.spec_ayarla(spec)
    p = w.uygunluk
    p.profilleri_ayarla(("A", "B"))
    p.denetle(w.spec, FIXTURE)
    kontrol("oneri gorunur ve 'düzelt' der", not p.d_ealf.isHidden()
            and "düzelt" in p.d_ealf.text(), "-> %r" % p.d_ealf.text())
    p._onay_al = lambda *_a: True
    p.d_ealf.click()
    adli = [t for t in w.spec["tallyler"] if t.get("ad") == aoa.EALF_TALLY]
    kontrol("tek vv_ealf ve gecerli", len(adli) == 1 and aoa.ealf_tanimi_gecerli(adli[0]),
            "-> %r" % adli)


def test_entropi_kisa_pasif_yakalanir():
    print("\n[QA4] K1: 4 pasif cevrim, entropi aktifte de dusuyor -> yakinsamadi")
    import math
    import random
    from cekirdek.kosucu import entropi_yakinsama
    random.seed(3)
    # 3B tam kor benzeri: entropi 8.0'dan 6.0'a ~15 cevrim zaman sabitiyle iner
    dusen = [6.0 + 2.0 * math.exp(-i / 15.0) + random.gauss(0, 0.01) for i in range(64)]
    karar, mesaj = entropi_yakinsama(dusen, 4)
    kontrol("4 pasif + aktifte kayma -> False", karar is False, "-> %r %s" % (karar, mesaj))
    random.seed(4)
    godiva = [6.0 * (1 - math.exp(-i / 2.0)) + random.gauss(0, 0.01) for i in range(80)]
    kontrol("hizla yukselip pasifte duzlesen -> True", entropi_yakinsama(godiva, 30)[0] is True,
            "-> %s" % (entropi_yakinsama(godiva, 30),))


def test_guc_yorumu_once_istatistik():
    print("\n[QA7] Guc yorumu: σ buyukse once istatistik yetersizligi, tasarim yorumu yok")
    from cekirdek import guc
    f = {"F_dH": 5.1, "F_dH_sapma": 2.4, "F_q": 45.0, "F_q_sapma": 30.0, "eksenel_dilim": 20,
         "cubuk_sayisi": 100, "F_dH_tepe_yakini": 1, "F_dH_yanlilik": 0.0}
    y = guc.yorumla(f, kategori="pwr")
    metin = " ".join(y)
    kontrol("istatistik yetersiz satiri (F_ΔH ve F_q)", metin.count("İstatistik yetersiz") == 2,
            "-> %s" % metin[:400])
    kontrol("'yakıt yüklemesi düzeltilmeli' ve F_q siniri yazilmaz",
            "düzeltilmeli" not in metin and "2.3–2.6" not in metin)
    iyi = guc.yorumla(dict(f, F_dH=1.8, F_dH_sapma=0.002, F_q=2.9, F_q_sapma=0.01),
                      kategori="pwr")
    kontrol("yeterli istatistikte PWR siniri yorumu yine var", "1.65" in " ".join(iyi))


HIZLI = [test_elle_ealf_tally_vv_dusurmez, test_panel_gecersiz_tally_duzeltir,
         test_entropi_kisa_pasif_yakalanir, test_guc_yorumu_once_istatistik]
YAVAS = []
