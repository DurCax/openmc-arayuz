# -*- coding: utf-8 -*-
"""
 test_h2_kapi.py  --  v3 H2: ana pencerede Calistir kapisi arka plan cizimiyle
                      ayni davranir (iyi model acik, kurulamayan model kapali,
                      panel daraltilmisken de denetlenir, kapanista isci biter)
"""

import copy
import os

from testler.ortak_test import kontrol, ORNEK
from testler.ortak_test import gereksinim  # v3 izlenebilirlik

_ZAMAN_ASIMI = 120.0


def _surec_durumu(pid):
    try:
        with open("/proc/%d/stat" % pid, encoding="ascii") as f:
            return f.read().rsplit(")", 1)[1].split()[0]
    except FileNotFoundError:
        return "yok"


@gereksinim("R-V3-12")
def test_calistir_kapisi_ayni():
    print("\n[H2K-1] Calistir kapisi: iyi model acik, kurulamayan kapali; daraltilmis panelde de")
    from PySide6 import QtWidgets
    from cekirdek import sema
    from arayuz.pencere.ana_pencere import AnaPencere
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yol = os.path.join(ORNEK, "pwr_17x17.json")
    p = AnaPencere()
    try:
        p._proje_kur(sema.yukle(yol), None, None)
        p.sekmeye_git("kor", sessiz=True)
        p.onizleme._ciz()
        p.onizleme.bekle(_ZAMAN_ASIMI)
        p._bulgular = []                      # yalniz onizleme kosulu sinansin
        izin, _neden = p._kosu_izni()
        kontrol("iyi model: kapi acik", izin and p.onizleme.cizildi_mi())

        bozuk = copy.deepcopy(p.spec)
        bozuk["malzemeler"] = []
        p.onizleme.spec_ayarla(bozuk)
        p.onizleme._ciz()
        p.onizleme.bekle(_ZAMAN_ASIMI)
        izin, neden = p._kosu_izni()
        kontrol("kurulamayan model: kapi kapali, gerekce onizleme",
                not izin and "önizlemesi henüz çizilmedi" in neden, "-> %s" % neden)

        p.onizleme_paneli.daralt(True)        # gizli: cizmez, yine denetler
        p.onizleme.spec_ayarla(p.spec)
        p.onizleme._ciz()
        p.onizleme.bekle(_ZAMAN_ASIMI)
        izin, neden = p._kosu_izni()
        kontrol("daraltilmis panel: onizleme gizli sayilir (yalniz kontrol istegi)",
                p.onizleme._gizli_mi() and not p.onizleme._son_eksenler)
        kontrol("daraltilmis panel: iyi model yine kapiyi acar", izin, "-> %s" % neden)
        p.onizleme.spec_ayarla(bozuk)
        p.onizleme._ciz()
        p.onizleme.bekle(_ZAMAN_ASIMI)
        kontrol("daraltilmis panel: kurulamayan model kapiyi kapatir", not p._kosu_izni()[0])
        p.onizleme_paneli.daralt(False)
        pid = p.onizleme._istemci.pid()
    finally:
        p._kirli = False
        p.close()
    kontrol("pencere kapaninca isci toplandi (zombi yok)",
            pid is not None and _surec_durumu(pid) == "yok", "-> %s" % pid)


HIZLI = [test_calistir_kapisi_ayni]
YAVAS = []
