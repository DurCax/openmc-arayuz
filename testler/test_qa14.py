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


def test_simge_dugmesi_adi_ipucunda():
    print("\n[QA6] Gelismis geometri: simge dugmelerinin adi ipucunun basinda")
    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.geometri.editor import GelismisEditor
    e = GelismisEditor()
    for anahtar in ("yerlesim", "grup", "halka"):
        d = e.dugmeler[anahtar]
        kontrol("%s: ipucu adla baslar (%s)" % (anahtar, d.accessibleName()),
                d.toolTip().startswith(d.accessibleName()), "-> %r" % d.toolTip())


def _rapor_penceresi(son, aday, sor):
    from PySide6 import QtWidgets
    from arayuz.pencere.proje import ProjeMixin

    class _Calistir(object):
        def son_kosu_dizini(self):
            return son

        def _kosu_dizini(self):
            return aday

    class _P(ProjeMixin, QtWidgets.QWidget):
        def __init__(self):
            QtWidgets.QWidget.__init__(self)
            self.spec, self.proje_yolu, self.s_calistir = _spec(), None, _Calistir()
            self.bildirimler, self.sorular = [], []

        def bildir_mesaj(self, metin, tur, *a, **k):
            self.bildirimler.append((metin, tur))

        def _rapor_kosusu_sor(self, dizin):
            self.sorular.append(dizin)
            return sor
    return _P()


def test_kosusuz_rapor_sessiz_degil():
    print("\n[QA8] Rapor: kosu yuklu degilse kayitli kosu sorulur; yoksa acik uyari")
    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from cekirdek import rapor

    class _Sonuc(object):
        uyarilar = []

        def __init__(self, yol):
            self.yol = yol
    cagri = []
    eski_olustur, eski_dlg = rapor.olustur, QtWidgets.QFileDialog.getSaveFileName
    rapor.olustur = lambda spec, kosu, yol, bicim: (cagri.append(kosu), _Sonuc(yol))[1]
    QtWidgets.QFileDialog.getSaveFileName = staticmethod(
        lambda *a, **k: ("/tmp/qa8_rapor.html", "HTML (*.html)"))
    try:
        p = _rapor_penceresi(None, FIXTURE, True)
        p.rapor_olustur()
        kontrol("kayitli kosu soruldu ve eklendi", p.sorular == [FIXTURE] and cagri[-1] == FIXTURE)
        kontrol("bildirim: diskteki kosu notu (uyari)", p.bildirimler[-1][1] == "uyari"
                and "kayıtlı koşu" in p.bildirimler[-1][0], "-> %r" % p.bildirimler[-1:])
        p = _rapor_penceresi(None, tempfile.mkdtemp(prefix="qa8_"), True)
        p.rapor_olustur()
        kontrol("kosu yok: yalniz model + acik uyari", cagri[-1] is None
                and p.bildirimler[-1][1] == "uyari" and "yalnız modeli" in p.bildirimler[-1][0],
                "-> %r" % p.bildirimler[-1:])
        p = _rapor_penceresi("/tmp/oturum_kosusu", FIXTURE, True)
        p.rapor_olustur()
        kontrol("oturum kosusu varsa sorulmaz", not p.sorular and cagri[-1] == "/tmp/oturum_kosusu")
    finally:
        rapor.olustur, QtWidgets.QFileDialog.getSaveFileName = eski_olustur, eski_dlg


HIZLI = [test_elle_ealf_tally_vv_dusurmez, test_panel_gecersiz_tally_duzeltir,
         test_entropi_kisa_pasif_yakalanir, test_guc_yorumu_once_istatistik,
         test_simge_dugmesi_adi_ipucunda, test_kosusuz_rapor_sessiz_degil]
YAVAS = []
