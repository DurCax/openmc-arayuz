# -*- coding: utf-8 -*-
"""
 test_h2_istemci.py  --  v3 H2 onizleme istemcisi (QProcess): cizim, eski
                         sonucun atilmasi, cokmede acik hata + yeniden
                         baslatma, kapanista zombisiz sonlanma
"""

import os
import signal
import time

from testler.ortak_test import kontrol, ORNEK

_ZAMAN_ASIMI = 60.0                  # s; yuklu makinede (xdist -n 4) bile yeter


def _uyg():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _bekle(kosul, sure=_ZAMAN_ASIMI):
    from PySide6 import QtCore
    uyg = _uyg()
    bas = time.monotonic()
    while not kosul() and time.monotonic() - bas < sure:
        uyg.processEvents(QtCore.QEventLoop.AllEvents, 50)
        time.sleep(0.005)
    return kosul()


def _spec(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _ciz(spec, kesitler=("xy",), piksel=64):
    return {"tur": "ciz", "spec": spec,
            "kesitler": [{"eksen": e, "piksel": piksel} for e in kesitler]}


def _surec_durumu(pid):
    """'yok' (toplandi), 'Z' (zombi) ya da calisan durum harfi."""
    try:
        with open("/proc/%d/stat" % pid, encoding="ascii") as f:
            return f.read().rsplit(")", 1)[1].split()[0]
    except FileNotFoundError:
        return "yok"


def test_istemci_cizer_ve_zombisiz_kapanir():
    print("\n[H2C-1] istemci: istek -> model/kesit/son; kapat -> surec toplanir (zombi yok)")
    _uyg()
    from arayuz.onizleme_istemci import CizimIstemcisi
    # Arrange
    ist = CizimIstemcisi()
    gelen = []
    ist.cerceve_geldi.connect(gelen.append)
    # Act
    no = ist.iste(_ciz(_spec("pwr_17x17")))
    bitti = _bekle(lambda: any(c.baslik["tur"] == "son" for c in gelen))
    pid = ist.pid()
    # Assert
    kontrol("son yaniti geldi", bitti)
    turler = [c.baslik["tur"] for c in gelen]
    kontrol("model, kesit, son (hepsi bu istegin)", turler == ["model", "kesit", "son"]
            and all(c.baslik["no"] == no for c in gelen), "-> %s" % turler)
    kontrol("kesit (64, 64, 3)", gelen[1].diziler["geom"].shape == (64, 64, 3))
    kontrol("istek bitince mesgul degil", not ist.mesgul_mu())
    kontrol("isci canli (oturum acik tutulur)", pid and _surec_durumu(pid) not in ("yok", "Z"))
    ist.kapat()
    kontrol("kapat: surec bitti", not ist.calisiyor_mu())
    kontrol("kapat: surec toplandi, zombi yok", _surec_durumu(pid) == "yok",
            "-> %s" % _surec_durumu(pid))
    ist.kapat()                       # ikinci kapat zararsiz


def test_istemci_eski_sonucu_atar():
    print("\n[H2C-2] istemci: yeni istek eskisini gecersiz kilar, eski yanitlar atilir")
    _uyg()
    from arayuz.onizleme_istemci import CizimIstemcisi
    ist = CizimIstemcisi()
    gelen = []
    ist.cerceve_geldi.connect(gelen.append)
    try:
        ist.iste(_ciz(_spec("vver1000_kor"), ("xy", "xz"), 800))      # yavas
        yeni = ist.iste(_ciz(_spec("pwr_17x17")))
        _bekle(lambda: any(c.baslik["tur"] == "son" for c in gelen))
        _bekle(lambda: not ist.mesgul_mu(), 5)
        kontrol("yalniz yeni istegin yanitlari iletildi",
                gelen and all(c.baslik["no"] == yeni for c in gelen),
                "-> %s" % [(c.baslik["tur"], c.baslik["no"]) for c in gelen])
        kontrol("yeni istek tamamlandi", gelen and gelen[-1].baslik.get("durum") == "tamam")
    finally:
        ist.kapat()


def test_istemci_cokmede_hata_ve_yeniden_baslar():
    print("\n[H2C-3] istemci: isci olurse acik hata, sonraki istek yeni surecte calisir")
    _uyg()
    from arayuz.onizleme_istemci import CizimIstemcisi
    ist = CizimIstemcisi()
    gelen, coktu = [], []
    ist.cerceve_geldi.connect(gelen.append)
    ist.coktu.connect(coktu.append)
    try:
        ist.baslat()
        kontrol("isci hazir", _bekle(ist.hazir_mi))
        eski = ist.pid()
        ist.iste(_ciz(_spec("vver1000_kor"), ("xy", "xz"), 800))
        os.kill(eski, signal.SIGKILL)
        kontrol("cokme bildirildi (acik mesaj)", _bekle(lambda: bool(coktu)), "-> %s" % coktu)
        kontrol("mesaj cikis durumunu soyler", coktu and "sonlandı" in coktu[0], "-> %s" % coktu)
        kontrol("cokme sonrasi mesgul degil", not ist.mesgul_mu())
        kontrol("olen surec toplandi", _bekle(lambda: _surec_durumu(eski) == "yok", 10))
        gelen.clear()
        no = ist.iste(_ciz(_spec("pwr_17x17")))
        _bekle(lambda: any(c.baslik["tur"] == "son" for c in gelen))
        kontrol("yeniden baslatilan iscide cizim tamam",
                gelen and gelen[-1].baslik["no"] == no and gelen[-1].baslik["durum"] == "tamam"
                and ist.pid() != eski)
    finally:
        ist.kapat()


def test_istemci_baslatilamazsa_hata():
    print("\n[H2C-4] istemci: isci baslatilamazsa acik hata, arayuz beklemez")
    _uyg()
    from arayuz.onizleme_istemci import CizimIstemcisi
    ist = CizimIstemcisi(komut=("/yok/boyle/bir/python", []))
    coktu = []
    ist.coktu.connect(coktu.append)
    t0 = time.perf_counter()
    ist.iste(_ciz({"ad": "x"}))
    sure = time.perf_counter() - t0
    kontrol("iste hemen doner (< 0.2 s)", sure < 0.2, "-> %.3f s" % sure)
    kontrol("baslatilamadi mesaji", _bekle(lambda: bool(coktu), 10) and "başlatılamadı" in coktu[0],
            "-> %s" % coktu)
    kontrol("mesgul degil", not ist.mesgul_mu())
    ist.kapat()


HIZLI = [test_istemci_cizer_ve_zombisiz_kapanir, test_istemci_eski_sonucu_atar,
         test_istemci_cokmede_hata_ve_yeniden_baslar, test_istemci_baslatilamazsa_hata]
YAVAS = []
# Nukleer veri GEREKMEZ: isci openmc.lib'i '-p' (cizim) kipinde baslatir.
