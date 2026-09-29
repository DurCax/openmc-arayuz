# -*- coding: utf-8 -*-
"""
test_tasarim_kurallari.py -- tasarim kurallari (Dalga 2 on-commit 5).

1. Sabit renk tarayicisi: arayuz/ altinda (arayuz/tasarim/ HARIC) kodda
   `#rrggbb` yazilmaz; renkler tasarim tokenlarindan gelir. RENK_TABANI
   29.09.2026'daki sayilardir ve YALNIZ KUCULUR: bir dosyada sayi tabani
   asarsa ya da listede olmayan dosyada renk cikarsa test kalir. Sayiyi
   dusuren ajan kendi satirini dusurur/siler (dusmemis olmasi test
   kaldirmaz, yalniz bilgi yazar).
2. Sahipsiz QLayout: AnaPencere kurulup her ornekte gorunur her sekme
   acildiktan sonra hicbir QLayout'un parentWidget()'i None degildir
   (kurulup yerlestirilmemis ya da yanlis ebeveyne takilmis duzen).
   29.09.2026 olcumu: 0 sahipsiz (SAHIPSIZ_TABAN bos).
Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import gc
import glob
import os
import re

from testler.ortak_test import kontrol, KOK, ORNEK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

RENK_DESENI = re.compile(r"#[0-9a-fA-F]{6}\b")
TARANAN = "arayuz"
MUAF = ("arayuz/tasarim/",)

# dosya -> izin verilen en cok #rrggbb sayisi (YALNIZ KUCULUR)
RENK_TABANI = {
    "arayuz/baslangic.py": 2,
    "arayuz/cubuk/cubuk_formu.py": 1,
    "arayuz/cubuk/malzeme_kutusu.py": 1,
    "arayuz/cubuk/sayfalar.py": 1,
    "arayuz/malzeme/bilesim.py": 1,
    "arayuz/malzeme/girdiler.py": 1,
    "arayuz/malzeme/yardimcilar.py": 1,
    "arayuz/ortak.py": 3,
    "arayuz/sekme_analiz.py": 2,
    "arayuz/sekme_calistir.py": 2,
    "arayuz/sekme_cubuk.py": 1,
    "arayuz/sekme_demet.py": 1,
    "arayuz/sekme_tukenme.py": 6,
    "arayuz/tukenme_sonuc.py": 5,
}

# Sahipsiz QLayout taban listesi: "SinifAdi@ilk_ogenin_turu" (YALNIZ KUCULUR)
SAHIPSIZ_TABAN = ()


def renk_sayilari(kok=KOK):
    """{goreli_yol: #rrggbb sayisi} -- MUAF dizinler haric, yalniz >0 olanlar."""
    sayim = {}
    for yol in sorted(glob.glob(os.path.join(kok, TARANAN, "**", "*.py"), recursive=True)):
        goreli = os.path.relpath(yol, kok).replace(os.sep, "/")
        if goreli.startswith(MUAF):
            continue
        with open(yol, encoding="utf-8") as f:
            n = len(RENK_DESENI.findall(f.read()))
        if n:
            sayim[goreli] = n
    return sayim


def test_sabit_renk_tabani():
    print("\n[TK1] arayuz/ (tasarim/ haric) #rrggbb sayisi tabani asmiyor")
    sayim = renk_sayilari()
    for yol, n in sorted(sayim.items()):
        taban = RENK_TABANI.get(yol, 0)
        kontrol("%s: %d <= %d" % (yol, n, taban), n <= taban,
                "-> renkleri arayuz/tasarim tokenlarindan alin")
    dusen = {y: (sayim.get(y, 0), t) for y, t in RENK_TABANI.items() if sayim.get(y, 0) < t}
    if dusen:
        print("    bilgi: tabani dusurulebilir: %s" % dusen)
    kontrol("tarayici bir seyler buluyor (desen/yol dogru)", sum(sayim.values()) > 0
            or not RENK_TABANI)


def test_renk_tarayicisi_kendini_sinar():
    print("\n[TK2] renk deseni: #rrggbb yakalanir, #rgb / 7+ hane yakalanmaz")
    kontrol("yakalar", RENK_DESENI.findall('renk = "#1a2B3c"') == ["#1a2B3c"])
    kontrol("yakalamaz", RENK_DESENI.findall("#abc #1234567 #zzzzzz") == [])


def _katmanlar():
    from PySide6 import QtWidgets
    return [o for o in gc.get_objects() if isinstance(o, QtWidgets.QLayout)]


def _sahipsiz_katmanlar(once):
    import shiboken6
    sahipsiz = []
    for o in _katmanlar():
        if id(o) in once or not shiboken6.isValid(o) or o.parentWidget() is not None:
            continue
        ilk = o.itemAt(0).widget() if o.count() else None
        sahipsiz.append("%s@%s" % (type(o).__name__, type(ilk).__name__ if ilk else "-"))
    return sahipsiz


def test_sahipsiz_qlayout_yok():
    print("\n[TK3] AnaPencere + 8 sekme: sahipsiz QLayout yok")
    from PySide6 import QtWidgets
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.ana_pencere import AnaPencere
    once = {id(o) for o in _katmanlar()}
    p = AnaPencere()
    p._kaydetme_sor = lambda: True
    acilan = set()
    try:
        p.resize(1280, 800)
        p.show()
        for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
            p.proje_ac(yol)
            for k in p.sekme_anahtarlari():
                if p.sekmeye_git(k, sessiz=True):
                    acilan.add(k)
                    uyg.processEvents()
        kontrol("8 sekmenin hepsi en az bir kez acildi", acilan == set(p.sekme_anahtarlari()),
                "-> %s" % sorted(acilan))
        sahipsiz = _sahipsiz_katmanlar(once)
        yeni = [s for s in sahipsiz if s not in SAHIPSIZ_TABAN]
        kontrol("sahipsiz QLayout yok (taban disi)", not yeni, "-> %s" % yeni)
        pencere_ici = [type(k).__name__ for k in p.findChildren(QtWidgets.QLayout)
                       if k.parentWidget() is None]
        kontrol("pencere agacinda parentWidget None olan duzen yok", not pencere_ici,
                "-> %s" % pencere_ici)
    finally:
        from PySide6 import QtCore
        p.s_tukenme.bekle()
        p._kirli = False
        p.close()
        p.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


HIZLI = [test_sabit_renk_tabani, test_renk_tarayicisi_kendini_sinar, test_sahipsiz_qlayout_yok]
YAVAS = []
