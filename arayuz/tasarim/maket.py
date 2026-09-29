# -*- coding: utf-8 -*-
"""
maket.py -- KAPI G1 icin statik maket ekranlari (gercek bilesenlerle; islev yok).

    python -m arayuz.tasarim.maket                          # kabugu pencerede acar
    python -m arayuz.tasarim.maket --ekran sonuclar         # tek ekran
    python -m arayuz.tasarim.maket --kaydet DIZIN           # her ekran x {acik,koyu}
                                                            #   x {1440x900, 1280x800}
    python -m arayuz.tasarim.maket --kaydet DIZIN --once ONCE_DIZINI
        # ayrica ONCE_DIZINI/<eski_ad>_<tema>_<WxH>.png ile yan yana karsilastirma
        # (DIZIN/karsilastirma/<ekran>_<tema>_<WxH>.png: once | sonra)
    python -m arayuz.tasarim.maket --kaydet DIZIN --varyant  # vurgu secenekleri
                                            # (DIZIN/varyant_<vurgu>/kabuk|sonuclar_*)

"Once" goruntuleri mevcut uygulamadan alinir (arayuz/tasarim/once_goruntu.py):
    git archive ana | tar -x -C /tmp/ana_kopya
    python arayuz/tasarim/once_goruntu.py --kok /tmp/ana_kopya --cikti DIZIN/once

Ekranlar: kabuk (Malzemeler sayfasiyla), kabuk_dar (kenar cubugu + onizleme
daraltilmis), kabuk_palet (Ctrl+K paleti + bildirim), baslangic, demet, hesap,
sonuclar (+ sonuclar_cekmece: "Ayrintili cikti" cekmecesi acik).
Kullanicinin QSettings'i degismez (gecici dizine yalitilir).
"""

import argparse
import os
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from arayuz.tasarim import tokenlar
from cekirdek.ceviri import _

COZUNURLUKLER = ((1440, 900), (1280, 800))
# maket ekrani -> mevcut uygulamadaki karsilik (once goruntusu dosya adi)
ONCE_ADI = {"kabuk": "malzemeler", "baslangic": "baslangic", "demet": "demet",
            "hesap": "ayarlar", "sonuclar": "calistir"}


def _kabuk():
    from arayuz.tasarim import maket_ekranlar as e
    from arayuz.tasarim.maket_kabuk import MaketKabuk
    return MaketKabuk(e.malzemeler(), "malzemeler", onizleme="acik")


def _baslangic():
    from arayuz.tasarim.maket_baslangic import MaketBaslangic
    return MaketBaslangic()


def _demet():
    from arayuz.tasarim import maket_ekranlar as e
    from arayuz.tasarim.maket_kabuk import MaketKabuk
    k = MaketKabuk(e.demet(), "demet", onizleme="dar", serit="uyari")
    k.kenar.durum_ayarla("parcalar", "uyari")
    return k


def _kabuk_dar():
    """Kenar cubugu ve onizleme daraltilmis (yalniz ikonlar)."""
    from arayuz.tasarim import maket_ekranlar as e
    from arayuz.tasarim.maket_kabuk import MaketKabuk
    return MaketKabuk(e.malzemeler(), "malzemeler", onizleme="dar", kenar_dar=True)


# (metin, ikon, kisayol) -- komut paletinde gorunen ornek eylemler
_PALET_EYLEMLERI = (
    ("Çalıştır", "play", "F5"), ("Kaydet", "save", "Ctrl+S"),
    ("Farklı kaydet…", "save", "Ctrl+Shift+S"), ("Doğrula", "circle-check", "Ctrl+D"),
    ("Kor türünü değiştir…", "hexagon", ""), ("Rapor oluştur…", "file-text", ""),
    ("Koyu tema", "moon", ""), ("Veri kütüphanesini denetle", "atom", ""))


def _kabuk_palet():
    """Ctrl+K komut paleti acik + bir bildirim (toast)."""
    from arayuz import bilesenler as b
    from arayuz.tasarim.ikon import ikon
    k = _kabuk()
    eylemler = []
    for metin, ikon_adi, kisayol in _PALET_EYLEMLERI:
        e = QtGui.QAction(ikon(ikon_adi), _(metin), k)
        if kisayol:
            e.setShortcut(QtGui.QKeySequence(kisayol))
        eylemler.append(e)
    k.palet = b.KomutPaleti(k, eylemler)

    def _ac():
        k.palet.ac()
        k.palet.arama.setText(_("kay"))
        b.bildir(k, _("Model kaydedildi: pwr_17x17.json"), "basari", 0)
    k.gosterim_sonrasi = _ac
    return k


def _hesap():
    from arayuz.tasarim import maket_ekranlar as e
    from arayuz.tasarim.maket_kabuk import MaketKabuk
    return MaketKabuk(e.hesap(), "hesap", onizleme="dar")


def _sonuclar(cekmece_acik=False):
    from arayuz.tasarim import maket_ekranlar as e
    from arayuz.tasarim.maket_kabuk import MaketKabuk
    k = MaketKabuk(e.sonuclar(cekmece_acik), "sonuclar", onizleme="yok")
    k.kenar.durum_ayarla("calistir", "tamam")
    k.kenar.durum_ayarla("sonuclar", "tamam")
    if cekmece_acik:
        k.gosterim_sonrasi = lambda: _sayfa_sonuna(k)
    return k


def _sayfa_sonuna(pencere):
    """Acik cekmece gorunsun: sayfayi en alta kaydir."""
    for alan in pencere.findChildren(QtWidgets.QScrollArea, "sayfa"):
        cubuk = alan.verticalScrollBar()
        cubuk.setValue(cubuk.maximum())


def ekranlar():
    """ad -> pencere kurucusu (her cagri YENI pencere)."""
    return {"kabuk": _kabuk, "kabuk_dar": _kabuk_dar, "kabuk_palet": _kabuk_palet,
            "baslangic": _baslangic, "demet": _demet, "hesap": _hesap,
            "sonuclar": _sonuclar, "sonuclar_cekmece": lambda: _sonuclar(True)}


def _uygulama():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)


def _cek(kur, boyut):
    app = _uygulama()
    w = kur()
    w.resize(*boyut)
    w.show()
    w.setFocus()         # ilk dugmenin odak halkasi maketi yaniltmasin
    for _i in range(3):
        app.processEvents()
    sonra = getattr(w, "gosterim_sonrasi", None)
    if sonra is not None:
        sonra()
        app.processEvents()
    resim = w.grab()
    w.close()
    w.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    return resim


def kaydet(dizin, vurgu=None, adlar=None, cozunurlukler=COZUNURLUKLER):
    from arayuz import tema
    from arayuz.tasarim.once_goruntu import ayarlari_yalit
    ayarlari_yalit()             # dogrudan cagrilsa da kullanici ayarina yazmasin
    app = _uygulama()
    os.makedirs(dizin, exist_ok=True)
    yollar = []
    for tema_adi in ("acik", "koyu"):
        tema.uygula(app, tema_adi, vurgu)
        for ad, kur in ekranlar().items():
            if adlar and ad not in adlar:
                continue
            for w, h in cozunurlukler:
                yol = os.path.join(dizin, "%s_%s_%dx%d.png" % (ad, tema_adi, w, h))
                if not _cek(kur, (w, h)).save(yol):
                    raise OSError("PNG yazilamadi: %s" % yol)
                yollar.append(yol)
    return yollar


def _etiketli(ressam, x, resim, etiket, ust):
    from arayuz import tema
    f = QtGui.QFont(ressam.font())
    f.setPixelSize(tokenlar.TIPOGRAFI["baslik"][0])
    f.setWeight(QtGui.QFont.DemiBold)
    ressam.setFont(f)
    ressam.setPen(QtGui.QColor(tema.renk("metin")))
    ressam.drawText(QtCore.QRect(x, 0, resim.width(), ust), QtCore.Qt.AlignCenter, etiket)
    ressam.drawImage(x, ust, resim)


def karsilastir(once_yolu, sonra_yolu, hedef):
    """once | sonra yan yana PNG."""
    from arayuz import tema
    once, sonra = QtGui.QImage(once_yolu), QtGui.QImage(sonra_yolu)
    if once.isNull() or sonra.isNull():
        raise OSError("karsilastirma icin resim okunamadi: %s / %s" % (once_yolu, sonra_yolu))
    ust, ara = 44, tokenlar.ARALIK["xl"]
    tuval = QtGui.QImage(once.width() + sonra.width() + ara,
                         max(once.height(), sonra.height()) + ust, QtGui.QImage.Format_RGB32)
    tuval.fill(QtGui.QColor(tema.renk("yuzey3")))
    r = QtGui.QPainter(tuval)
    r.setRenderHint(QtGui.QPainter.Antialiasing)
    _etiketli(r, 0, once, _("Önce"), ust)
    _etiketli(r, once.width() + ara, sonra, _("Sonra (maket)"), ust)
    r.end()
    if not tuval.save(hedef):
        raise OSError("PNG yazilamadi: %s" % hedef)
    return hedef


def karsilastirmalar(dizin, once_dizini):
    hedef_dizin = os.path.join(dizin, "karsilastirma")
    os.makedirs(hedef_dizin, exist_ok=True)
    yollar = []
    for ad, eski in ONCE_ADI.items():
        for tema_adi in ("acik", "koyu"):
            for w, h in COZUNURLUKLER:
                son = "%s_%dx%d.png" % (tema_adi, w, h)
                once = os.path.join(once_dizini, "%s_%s" % (eski, son))
                sonra = os.path.join(dizin, "%s_%s" % (ad, son))
                if os.path.exists(once) and os.path.exists(sonra):
                    yollar.append(karsilastir(once, sonra,
                                              os.path.join(hedef_dizin, "%s_%s" % (ad, son))))
    return yollar


def varyantlar(dizin):
    """Her vurgu secenegi icin kabuk + sonuclar, iki tema, 1440x900."""
    from arayuz.tasarim.once_goruntu import ayarlari_yalit
    ayarlari_yalit()
    yollar = []
    for vurgu in tokenlar.VURGULAR:
        alt = os.path.join(dizin, "varyant_%s" % vurgu)
        yollar += kaydet(alt, vurgu, ("kabuk", "sonuclar"), COZUNURLUKLER[:1])
    return yollar


def main(argv=None):
    ayr = argparse.ArgumentParser(description=_("Tasarım maketleri (KAPI G1)"))
    ayr.add_argument("--kaydet", metavar="DIZIN")
    ayr.add_argument("--once", metavar="DIZIN", help=_("önce görüntülerinin dizini"))
    ayr.add_argument("--varyant", action="store_true", help=_("vurgu seçeneklerini de yaz"))
    ayr.add_argument("--ekran", choices=sorted(ekranlar()), default="kabuk")
    ayr.add_argument("--tema", choices=("acik", "koyu"), default=None)
    ayr.add_argument("--vurgu", choices=sorted(tokenlar.VURGULAR), default=None)
    a = ayr.parse_args(argv)
    from arayuz.tasarim.once_goruntu import ayarlari_yalit
    ayarlari_yalit()             # tema/vurgu secimi kullanicinin ayarlarina yazilmasin
    vurgu = a.vurgu or tokenlar.VARSAYILAN_VURGU
    app = _uygulama()
    from arayuz import ortak, tema
    ortak.tekerlek_korumasi_kur(app)     # gercek uygulamadaki olay suzgeci
    if a.kaydet:
        yollar = kaydet(a.kaydet, vurgu)
        if a.once:
            tema.uygula(app, "acik", vurgu)
            yollar += karsilastirmalar(a.kaydet, a.once)
        if a.varyant:
            yollar += varyantlar(a.kaydet)
        print("\n".join(yollar))
        return 0
    tema.uygula(app, a.tema or "acik", vurgu)
    w = ekranlar()[a.ekran]()
    w.resize(*COZUNURLUKLER[0])
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
