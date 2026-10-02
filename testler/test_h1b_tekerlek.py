# -*- coding: utf-8 -*-
"""
 test_h1b_tekerlek.py  --  v3 H1b: tekerlek suzgeci pencere kurulumunda askida

 arayuz/ortak.py'deki uygulama geneli olay suzgeci her olayda Python'a
 geciyordu; ana pencere kurulumunda ~170 bin olay = ~1.4 s CPU (olculdu).
 Kurulum artik ortak.tekerlek_suzgeci_askida() icinde: suzgec cikista geri
 kurulur, kurulumda polish edilen kutularin odak politikasi toplu duzeltilir.
 Davranis (odaksiz kutu tekerlekle degismez, odak politikasi StrongFocus,
 diyalog sonrasi etkin pencere) test_arayuz_hata_avi / test_qa14'te de durur.
"""

import time

from testler.ortak_test import kontrol



def _uygulama():
    from PySide6 import QtWidgets
    from arayuz.ortak import tekerlek_korumasi_kur
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    tekerlek_korumasi_kur(app)
    return app


def _tekerlek(w, delta=-120):
    from PySide6 import QtCore, QtGui, QtWidgets
    olay = QtGui.QWheelEvent(QtCore.QPointF(4, 4), QtCore.QPointF(4, 4), QtCore.QPoint(0, 0),
                             QtCore.QPoint(0, delta), QtCore.Qt.NoButton,
                             QtCore.Qt.NoModifier, QtCore.Qt.NoScrollPhase, False)
    QtWidgets.QApplication.sendEvent(w, olay)


def _kutulu_pencere():
    from PySide6 import QtWidgets
    w = QtWidgets.QWidget()
    duzen = QtWidgets.QVBoxLayout(w)
    kutu = QtWidgets.QComboBox()
    kutu.addItems(["a", "b", "c"])
    sayi = QtWidgets.QSpinBox()
    duzen.addWidget(kutu)
    duzen.addWidget(sayi)
    w.ensurePolished()
    kutu.ensurePolished()
    sayi.ensurePolished()
    return w, kutu, sayi


def test_askida_kurulan_kutular_korunur():
    print("\n[H1b-T1] askida kurulan kutu: odak StrongFocus, odaksiz tekerlek degistirmez")
    from PySide6 import QtCore
    from arayuz import ortak
    _uygulama()
    with ortak.tekerlek_suzgeci_askida():
        w, kutu, sayi = _kutulu_pencere()
    kontrol("odak politikasi StrongFocus (combo ve spin)",
            kutu.focusPolicy() == QtCore.Qt.StrongFocus
            and sayi.focusPolicy() == QtCore.Qt.StrongFocus,
            "-> %s / %s" % (kutu.focusPolicy(), sayi.focusPolicy()))
    once = kutu.currentIndex()
    _tekerlek(kutu)
    _tekerlek(sayi, 120)
    kontrol("odaksiz kutular tekerlekle degismedi", kutu.currentIndex() == once
            and sayi.value() == 0, "-> %d %d" % (kutu.currentIndex(), sayi.value()))
    w.deleteLater()


def test_askidan_sonra_suzgec_geri_kurulur():
    print("\n[H1b-T2] askidan cikinca suzgec yeniden etkin (sonra kurulan kutu da korunur)")
    from arayuz import ortak
    _uygulama()
    with ortak.tekerlek_suzgeci_askida():
        pass
    w, kutu, _sayi = _kutulu_pencere()
    _tekerlek(kutu)
    kontrol("sonradan kurulan odaksiz kutu degismedi", kutu.currentIndex() == 0)
    w.deleteLater()


def test_askida_hata_olsa_da_suzgec_geri_kurulur():
    print("\n[H1b-T3] kurulumda istisna: suzgec yine geri kurulur")
    from arayuz import ortak
    _uygulama()
    try:
        with ortak.tekerlek_suzgeci_askida():
            raise RuntimeError("deneme")
    except RuntimeError:
        pass
    w, kutu, _sayi = _kutulu_pencere()
    _tekerlek(kutu)
    kontrol("istisnadan sonra kutu korunuyor", kutu.currentIndex() == 0)
    w.deleteLater()


def _suzgec_etkin_mi():
    """Yoklama: odaksiz yeni kutuya tekerlek -- suzgec etkinse deger degismez."""
    from PySide6 import QtWidgets
    kutu = QtWidgets.QComboBox()
    kutu.addItems(["a", "b", "c"])
    _tekerlek(kutu)
    etkin = kutu.currentIndex() == 0
    kutu.deleteLater()
    return etkin


def test_pencere_kurulumunda_suzgec_askida(monkeypatch):
    print("\n[H1b-T4] AnaPencere sayfalari kurulurken suzgec askida, kurulumdan sonra etkin")
    from PySide6 import QtCore
    from arayuz.ana_pencere import AnaPencere
    from arayuz.pencere import ana_pencere as ap
    _uygulama()
    gozlem = []
    asil = ap.AnaPencere._sayfalari_kur

    def gozleyen(self):
        gozlem.append(_suzgec_etkin_mi())
        return asil(self)
    monkeypatch.setattr(ap.AnaPencere, "_sayfalari_kur", gozleyen)
    p = AnaPencere()
    try:
        kontrol("sayfa kurulumunda suzgec askida", gozlem == [False], "-> %r" % gozlem)
        kontrol("kurulumdan sonra suzgec etkin", _suzgec_etkin_mi())
        kontrol("pencere kutulari StrongFocus",
                p.s_kor.bc_yan.focusPolicy() == QtCore.Qt.StrongFocus
                and p.s_ayar.parcacik.focusPolicy() == QtCore.Qt.StrongFocus)
    finally:
        p._kirli = False
        p.close()
        p.deleteLater()


def test_yavas_pencere_kurulumu_suzgecsiz_kadar_hizli():
    print("\n[H1b-T5] AnaPencere kurulumu: suzgecli CPU <= 1.15 x suzgecsiz")
    from PySide6 import QtWidgets
    from arayuz import ortak
    from arayuz.ana_pencere import AnaPencere
    app = _uygulama()

    def olc():
        sureler = []
        for _i in range(2):
            t = time.process_time()
            p = AnaPencere()
            sureler.append(time.process_time() - t)
            p._kirli = False
            p.close()
            p.deleteLater()
            QtWidgets.QApplication.processEvents()
        return min(sureler)
    suzgecli = olc()
    suzgec = ortak._SUZGEC.pop(id(app))
    app.removeEventFilter(suzgec)
    try:
        suzgecsiz = olc()
    finally:
        app.installEventFilter(suzgec)
        ortak._SUZGEC[id(app)] = suzgec
    # gerekce: taban suzgecli/suzgecsiz = 4.4/3.0 s (x1.47); %15 olcum payi
    kontrol("suzgecli <= 1.15 x suzgecsiz", suzgecli <= 1.15 * suzgecsiz,
            "%.3f / %.3f s" % (suzgecli, suzgecsiz))


HIZLI = [test_askida_kurulan_kutular_korunur, test_askidan_sonra_suzgec_geri_kurulur,
         test_askida_hata_olsa_da_suzgec_geri_kurulur, test_pencere_kurulumunda_suzgec_askida]
YAVAS = [test_yavas_pencere_kurulumu_suzgecsiz_kadar_hizli]


def test_ic_ice_askida_yalniz_kaldiran_geri_kurar():
    print("\n[H1b-T6] ic ice askida: ic blok cikisinda suzgec hala askida, dis cikista geri")
    from arayuz import ortak
    _uygulama()
    with ortak.tekerlek_suzgeci_askida():
        with ortak.tekerlek_suzgeci_askida():
            pass
        ic_sonrasi = _suzgec_etkin_mi()
    kontrol("ic cikistan sonra suzgec askida", ic_sonrasi is False)
    kontrol("dis cikistan sonra suzgec etkin", _suzgec_etkin_mi())


def test_silinmis_kok_asil_hatayi_maskelemez():
    print("\n[H1b-T7] kok widget blok icinde silinirse: cikis hata vermez, asil hata korunur")
    import shiboken6
    from PySide6 import QtWidgets
    from arayuz import ortak
    _uygulama()
    kok = QtWidgets.QWidget()
    try:
        with ortak.tekerlek_suzgeci_askida(kok):
            shiboken6.delete(kok)
            raise KeyError("asil")
    except KeyError as e:
        kontrol("asil hata yukari cikar", str(e) == "'asil'", "-> %r" % e)
    except RuntimeError as e:
        kontrol("asil hata yukari cikar", False, "-> RuntimeError %s" % e)
    kontrol("suzgec yine etkin", _suzgec_etkin_mi())


HIZLI += [test_ic_ice_askida_yalniz_kaldiran_geri_kurar, test_silinmis_kok_asil_hatayi_maskelemez]
