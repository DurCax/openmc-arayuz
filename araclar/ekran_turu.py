# -*- coding: utf-8 -*-
"""
ekran_turu.py -- uygulamanin ekran turu (Dalga 2 ortak kabul: maketle yan yana
inceleme). Basliksiz (QT_QPA_PLATFORM=offscreen) calisir.

    python araclar/ekran_turu.py [--cikti DIZIN] [--alt d2_kabuk]
        [--ornek pwr_17x17.json] [--ornek sfr_altigen.json]
        [--sekme demet --sekme kor] [--tema acik,koyu] [--boyut 1280x800,1440x900]

Cikti dizini: --cikti > $OPENMC_V2_CIKTI (ikisi de yoksa hata). --alt verilirse
onun altina yazilir (ornek: $OPENMC_V2_CIKTI/d2_kabuk/).

Dosyalar:  baslangic_<tema>_<GxY>.png
           <ornek>_<sekme>_<tema>_<GxY>.png     (gorunur her sekme)
           tur_ozeti.txt   -- her ekran icin yatay kaydirma denetimi
                              ("YATAY KAYDIRMA" satiri = kabul disi)

Kullanicinin gercek QSettings'i DEGISMEZ (gecici dizine yonlendirilir).
Pencereye yalniz gezinme cephesiyle (arayuz/pencere/gezinme.py) erisilir.
"""

import argparse
import os
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORTAM_DEGISKENI = "OPENMC_V2_CIKTI"
TEMALAR = ("acik", "koyu")
BOYUTLAR = ((1280, 800), (1440, 900))
VARSAYILAN_ORNEK = "pwr_17x17.json"
_BEKLEME_TURU = 6


def cikti_dizini(arguman=None, alt=None, ortam=None):
    """--cikti > $OPENMC_V2_CIKTI; alt dizin eklenir. Ikisi de yoksa ValueError."""
    ortam = os.environ if ortam is None else ortam
    taban = arguman or ortam.get(ORTAM_DEGISKENI)
    if not taban:
        raise ValueError("cikti dizini yok: --cikti verin ya da %s tanimlayin"
                         % ORTAM_DEGISKENI)
    return os.path.abspath(os.path.join(taban, alt) if alt else taban)


def boyutlari_coz(metin):
    """'1280x800,1440x900' -> ((1280, 800), (1440, 900)); bozuksa ValueError."""
    boyutlar = []
    for parca in (p.strip() for p in metin.split(",") if p.strip()):
        gen, _x, yuk = parca.lower().partition("x")
        if not (gen.isdigit() and yuk.isdigit()):
            raise ValueError("boyut 'GENxYUK' olmali: %r" % parca)
        boyutlar.append((int(gen), int(yuk)))
    return tuple(boyutlar)


def dosya_adi(ekran, tema_adi, boyut):
    return "%s_%s_%dx%d.png" % (ekran, tema_adi, boyut[0], boyut[1])


def _ayarlari_yalit():
    from PySide6 import QtCore
    dizin = tempfile.mkdtemp(prefix="openmc_arayuz_ayar_")
    for bicim in (QtCore.QSettings.NativeFormat, QtCore.QSettings.IniFormat):
        QtCore.QSettings.setPath(bicim, QtCore.QSettings.UserScope, dizin)
    return dizin


def _bekle(app):
    for _i in range(_BEKLEME_TURU):
        app.processEvents()


def _kaydet(pencere, yol):
    if not pencere.grab().save(yol):
        raise OSError("ekran goruntusu yazilamadi: %s" % yol)
    return yol


def _yatay_kaydirma(pencere, anahtar):
    sayfa = pencere.sekme_sayfasi(anahtar)
    cubuk = sayfa.horizontalScrollBar() if hasattr(sayfa, "horizontalScrollBar") else None
    return cubuk.maximum() if cubuk is not None else 0


def _ornek_turu(app, pencere, ornek, sekmeler, son, cikti, ozet):
    ad = os.path.splitext(os.path.basename(ornek))[0]
    if not pencere.proje_ac(ornek):       # ornekler/ altindakiler kopya acilir
        raise OSError("ornek acilamadi: %s" % ornek)
    _bekle(app)
    yollar = []
    for anahtar in pencere.sekme_anahtarlari():
        if sekmeler and anahtar not in sekmeler:
            continue
        if not pencere.sekmeye_git(anahtar, sessiz=True):
            continue
        _bekle(app)
        ekran = "%s_%s" % (ad, anahtar)
        yollar.append(_kaydet(pencere, os.path.join(cikti, ekran + son)))
        kaydirma = _yatay_kaydirma(pencere, anahtar)
        ozet.append("%s%s: %s" % (ekran, son[:-4], "YATAY KAYDIRMA %d px" % kaydirma
                                  if kaydirma else "tamam"))
    return yollar


def _tur(app, boyut, tema_adi, ornekler, sekmeler, cikti, ozet):
    from arayuz import ana_pencere
    son = "_" + dosya_adi("", tema_adi, boyut)[1:]
    pencere = ana_pencere.AnaPencere()
    pencere._kaydetme_sor = lambda: True          # kapanista modal soru acilmasin
    pencere.resize(*boyut)
    pencere.show()
    _bekle(app)
    yollar = [_kaydet(pencere, os.path.join(cikti, "baslangic" + son))]
    try:
        for ornek in ornekler:
            yollar += _ornek_turu(app, pencere, ornek, sekmeler, son, cikti, ozet)
    finally:
        pencere.close()
        pencere.deleteLater()
        app.processEvents()
    return yollar


def cek(cikti, ornekler=(VARSAYILAN_ORNEK,), sekmeler=(), temalar=TEMALAR, boyutlar=BOYUTLAR):
    """Ekran turunu ceker; yazilan PNG yollari (tur_ozeti.txt ayrica yazilir)."""
    from PySide6 import QtCore, QtWidgets
    QtCore.QLocale.setDefault(QtCore.QLocale.c())
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv[:1])
    from arayuz import ortak, tema
    ortak.tekerlek_korumasi_kur(app)
    os.makedirs(cikti, exist_ok=True)
    yollar, ozet = [], []
    for tema_adi in temalar:
        tema.uygula(app, tema_adi)
        for boyut in boyutlar:
            yollar += _tur(app, boyut, tema_adi, ornekler, sekmeler, cikti, ozet)
    with open(os.path.join(cikti, "tur_ozeti.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(ozet) + "\n")
    return yollar


def _ayristirici():
    a = argparse.ArgumentParser(description="Uygulamanin ekran turu (offscreen)")
    a.add_argument("--cikti", default=None, help="cikti dizini (varsayilan $%s)"
                   % ORTAM_DEGISKENI)
    a.add_argument("--alt", default=None, help="alt dizin (ornek d2_kabuk)")
    a.add_argument("--ornek", action="append", default=None,
                   help="ornekler/ altindaki dosya ya da mutlak yol (tekrarlanabilir)")
    a.add_argument("--sekme", action="append", default=None,
                   help="yalniz bu sekmeler (anahtar; tekrarlanabilir)")
    a.add_argument("--tema", default=",".join(TEMALAR))
    a.add_argument("--boyut", default=",".join("%dx%d" % b for b in BOYUTLAR))
    return a


def main(argv=None):
    a = _ayristirici().parse_args(argv)
    try:
        cikti = cikti_dizini(a.cikti, a.alt)
        boyutlar = boyutlari_coz(a.boyut)
    except ValueError as e:
        print("hata: %s" % e, file=sys.stderr)
        return 2
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if KOK not in sys.path:
        sys.path.insert(0, KOK)
    os.chdir(KOK)
    _ayarlari_yalit()
    ornekler = [o if os.path.isabs(o) else os.path.join(KOK, "ornekler", o)
                for o in (a.ornek or [VARSAYILAN_ORNEK])]
    temalar = tuple(t.strip() for t in a.tema.split(",") if t.strip())
    for yol in cek(cikti, ornekler, tuple(a.sekme or ()), temalar, boyutlar):
        print(yol)
    return 0


if __name__ == "__main__":
    sys.exit(main())
