# -*- coding: utf-8 -*-
"""
 test_h2_onizleme.py  --  v3 H2 onizleme widget'i: arka planda cizim, gizliyken
                          cizmeme (yalniz kapi denetimi), bozuk modelde kapi,
                          cokmede acik hata, ana is parcacigi bloklanmaz,
                          SFR-MET1000 suresi (olcum)
"""

import copy
import os
import signal
import time

from testler.ortak_test import kontrol, ORNEK

_DONMA_SINIRI = 0.200      # s; plan Dalga H: "hicbir islemde arayuz 200 ms'den uzun donmaz"
_SFR_SINIRI = 3.0          # s; plan H2 kabul: SFR onizlemesi <= 3 s (sicak isci)
_ZAMAN_ASIMI = 60.0


def _uyg():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _spec(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _bekle(kosul, sure=_ZAMAN_ASIMI):
    from PySide6 import QtCore
    uyg = _uyg()
    bas = time.monotonic()
    while not kosul() and time.monotonic() - bas < sure:
        uyg.processEvents(QtCore.QEventLoop.AllEvents, 20)
        time.sleep(0.002)
    return kosul()


class _DonmaOlcer:
    """Olay dongusu araliklarinin en buyugu (ana is parcacigi bloklanma suresi)."""

    _ARALIK_MS = 10

    def __init__(self):
        from PySide6 import QtCore
        self.en_buyuk = 0.0
        self._son = time.perf_counter()
        self._sayac = QtCore.QTimer()
        self._sayac.setInterval(self._ARALIK_MS)
        self._sayac.timeout.connect(self._tik)
        self._sayac.start()

    def _tik(self):
        simdi = time.perf_counter()
        self.en_buyuk = max(self.en_buyuk, simdi - self._son)
        self._son = simdi

    def durdur(self):
        self._sayac.stop()
        return self.en_buyuk


def _resimler(w):
    return [len(ax.images) for ax in w.figur.axes]


def test_widget_arka_planda_cizer():
    print("\n[H2W-1] onizleme: 3B model xy + xz arka planda cizilir, kapi acik")
    _uyg()
    from arayuz.onizleme import OnizlemeWidget
    # Arrange
    w = OnizlemeWidget()
    durumlar = []
    w.durum.connect(lambda m, b: durumlar.append(b))
    try:
        # Act
        w.spec_ayarla(_spec("pwr_3b"))
        w._ciz()
        bitti = w.bekle(_ZAMAN_ASIMI)
        # Assert
        kontrol("cizim bitti", bitti and not w.mesgul_mu())
        kontrol("iki kesit, ikisinde de goruntu", _resimler(w)[:2] == [1, 1], "-> %s" % _resimler(w))
        kontrol("cizildi_mi + basarili durum", w.cizildi_mi() and durumlar and durumlar[-1],
                "-> %s" % (w.son_hata() or "")[-300:])
        kontrol("olcu bilindi", w.son_olcu and abs(w.son_olcu[0] - 21.42) < 1e-6)
        kontrol("son_sure olculdu", w.son_sure is not None and w.son_sure > 0)
    finally:
        w.kapat()


def test_widget_gizliyken_cizmez():
    print("\n[H2W-2] onizleme: gizliyken cizmez (yalniz kapi denetimi), acilinca cizer")
    _uyg()
    from arayuz.onizleme import OnizlemeWidget
    from PySide6 import QtWidgets
    kap = QtWidgets.QWidget()
    lay = QtWidgets.QVBoxLayout(kap)
    w = OnizlemeWidget()
    lay.addWidget(w)
    turler = []
    asil = w._istemci.iste
    w._istemci.iste = lambda istek: (turler.append(istek["tur"]), asil(istek))[1]
    try:
        kap.show()
        w.setVisible(False)                       # panel daraltildi
        w.spec_ayarla(_spec("pwr_17x17"))
        w._ciz()
        w.bekle(_ZAMAN_ASIMI)
        kontrol("gizliyken istek turu 'kontrol'", turler == ["kontrol"], "-> %s" % turler)
        kontrol("gizliyken goruntu yok", not any(_resimler(w)))
        kontrol("kapi denetimi yapildi: cizildi_mi (hata yok)", w.cizildi_mi())
        w.setVisible(True)                        # panel acildi
        _bekle(lambda: "ciz" in turler, 5)
        w.bekle(_ZAMAN_ASIMI)
        kontrol("acilinca cizim istendi ve cizildi", "ciz" in turler and any(_resimler(w)),
                "-> %s" % turler)
    finally:
        w.kapat()
        kap.close()


def test_widget_bozuk_model_kapiyi_kapatir():
    print("\n[H2W-3] onizleme: kurulamayan model hata gosterir, Calistir kapisi kapanir")
    _uyg()
    from arayuz.onizleme import OnizlemeWidget
    w = OnizlemeWidget()
    durumlar = []
    w.durum.connect(lambda m, b: durumlar.append((m, b)))
    try:
        bozuk = copy.deepcopy(_spec("pwr_17x17"))
        bozuk["malzemeler"] = []
        w.spec_ayarla(bozuk)
        w._ciz()
        w.bekle(_ZAMAN_ASIMI)
        kontrol("kapi kapali (cizildi_mi False)", not w.cizildi_mi())
        kontrol("son_hata iz tasir", "Traceback" in (w.son_hata() or ""))
        kontrol("basarisiz durum yayildi", durumlar and not durumlar[-1][1]
                and "Önizleme başarısız" in durumlar[-1][0], "-> %s" % durumlar[-1:])
        metin = " ".join(t.get_text() for t in w.figur.axes[0].texts)
        kontrol("tuvalde 'Geometri kurulamadı'", "Geometri kurulamadı" in metin, "-> %s" % metin)
        w.spec_ayarla(_spec("pwr_17x17"))
        w._ciz()
        w.bekle(_ZAMAN_ASIMI)
        kontrol("duzelince kapi yeniden acik", w.cizildi_mi() and any(_resimler(w)))
    finally:
        w.kapat()


def test_widget_cokmede_acik_hata():
    print("\n[H2W-4] onizleme: isci olurse acik hata, kapi kapali, sonraki cizim calisir")
    _uyg()
    from arayuz.onizleme import OnizlemeWidget
    w = OnizlemeWidget()
    try:
        w._istemci.baslat()
        _bekle(w._istemci.hazir_mi)
        w.spec_ayarla(_spec("vver1000_kor"))
        w._ciz()
        os.kill(w._istemci.pid(), signal.SIGKILL)
        _bekle(lambda: w.son_hata() is not None, 10)
        kontrol("cokme hatasi gosterildi, kapi kapali",
                not w.cizildi_mi() and "sonlandı" in (w.son_hata() or ""), "-> %s" % w.son_hata())
        kontrol("arayuz beklemiyor (mesgul degil)", not w.mesgul_mu())
        w.spec_ayarla(_spec("pwr_17x17"))
        w._ciz()
        w.bekle(_ZAMAN_ASIMI)
        kontrol("yeniden baslayan iscide cizim tamam", w.cizildi_mi() and any(_resimler(w)))
    finally:
        w.kapat()


def test_widget_ana_is_parcacigi_bloklanmaz():
    print("\n[H2W-5] onizleme: VVER-1000 kor cizilirken olay dongusu %d ms'den uzun durmaz"
          % (_DONMA_SINIRI * 1000))
    _uyg()
    from arayuz.onizleme import OnizlemeWidget
    w = OnizlemeWidget()
    w.resize(700, 600)
    w.show()
    try:
        w._istemci.baslat()
        _bekle(w._istemci.hazir_mi)
        olcer = _DonmaOlcer()
        t0 = time.perf_counter()
        w.spec_ayarla(_spec("vver1000_kor"))
        w._ciz()
        cagri = time.perf_counter() - t0
        w.bekle(_ZAMAN_ASIMI)
        _bekle(lambda: False, 0.3)                # son cizim (draw_idle) da olculsun
        en_buyuk = olcer.durdur()
        kontrol("spec_ayarla + _ciz hemen doner (< 50 ms)", cagri < 0.05, "-> %.0f ms" % (cagri * 1e3))
        kontrol("en uzun olay dongusu araligi < %d ms" % (_DONMA_SINIRI * 1000),
                en_buyuk < _DONMA_SINIRI, "-> %.0f ms" % (en_buyuk * 1e3))
        kontrol("cizildi", w.cizildi_mi() and any(_resimler(w)))
    finally:
        w.kapat()


def test_widget_cakisma_secenegi():
    print("\n[H2W-6] onizleme: 'Çakışmaları göster' Gelismis altinda, istege gecer")
    _uyg()
    from arayuz.onizleme import OnizlemeWidget
    w = OnizlemeWidget()
    giden = []
    w._istemci.iste = lambda istek: giden.append(istek) or 1
    kontrol("secenek Gelismis altinda", w.gelismis.isAncestorOf(w.cakisma))
    kontrol("hizli mod kalkti (oturum her zaman acik)", not hasattr(w, "hizli_mod"))
    w.spec_ayarla(_spec("pwr_17x17"))
    w.cakisma.setChecked(True)
    w._ciz()
    kontrol("istekte cakisma = True", giden and giden[-1].get("cakisma") is True,
            "-> %s" % [g.get("cakisma") for g in giden])
    w._istemci.iste = lambda istek: 1
    w.kapat()


def test_sfr_onizleme_suresi(gecici=None):
    print("\n[H2W-7] OLCUM: SFR-MET1000 kor onizlemesi (xy + xz, 800 px) <= %.0f s, donmasiz"
          % _SFR_SINIRI)
    _uyg()
    from arayuz.onizleme import OnizlemeWidget
    w = OnizlemeWidget()
    w.resize(700, 600)
    w.show()
    try:
        w._istemci.baslat()
        _bekle(w._istemci.hazir_mi)
        olcer = _DonmaOlcer()
        t0 = time.perf_counter()
        w.spec_ayarla(_spec("sfr_met1000_kor"))
        w._ciz()
        w.bekle(_ZAMAN_ASIMI)
        ilk = time.perf_counter() - t0
        t0 = time.perf_counter()
        w.renklendirme.setCurrentIndex(w.renklendirme.findData("cell"))
        w.bekle(_ZAMAN_ASIMI)
        ikinci = time.perf_counter() - t0
        en_buyuk = olcer.durdur()
        print("  OLCUM sfr_met1000_kor: ilk %.2f s, renk degisimi %.2f s, en uzun donma %.0f ms"
              % (ilk, ikinci, en_buyuk * 1e3))
        kontrol("SFR ilk onizleme <= %.0f s" % _SFR_SINIRI, w.cizildi_mi() and ilk <= _SFR_SINIRI,
                "-> %.2f s" % ilk)
        kontrol("ayni modelde gorunum degisimi init'siz (< ilk)", ikinci < ilk,
                "-> %.2f s" % ikinci)
        kontrol("en uzun donma < %d ms" % (_DONMA_SINIRI * 1000), en_buyuk < _DONMA_SINIRI,
                "-> %.0f ms" % (en_buyuk * 1e3))
    finally:
        w.kapat()


HIZLI = [test_widget_arka_planda_cizer, test_widget_gizliyken_cizmez,
         test_widget_bozuk_model_kapiyi_kapatir, test_widget_cokmede_acik_hata,
         test_widget_ana_is_parcacigi_bloklanmaz, test_widget_cakisma_secenegi]
YAVAS = [test_sfr_onizleme_suresi]
VERI_GEREKEN = [test_widget_arka_planda_cizer, test_widget_gizliyken_cizmez,
                test_widget_bozuk_model_kapiyi_kapatir, test_widget_cokmede_acik_hata,
                test_widget_ana_is_parcacigi_bloklanmaz]
