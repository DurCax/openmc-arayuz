# -*- coding: utf-8 -*-
"""
================================================================================
 tuval.py  --  Kapanisa dayanikli matplotlib tuvali (Analiz ve Tukenme)
================================================================================
 SORUN (D1-A olcumu): `FigureCanvasQTAgg.draw_idle()` cizimi hemen yapmaz;
 `QTimer.singleShot(0, self._draw_idle)` ile olay kuyruguna koyar. Zamanlayici
 tuvalin BAGLI YONTEMINI tutar, yani tuvalin Python sarmalayicisi yasamaya
 devam eder -- ama sekme bu arada silinirse (sayfa degisti, proje kapandi,
 test islevi dondu) altindaki C++ nesnesi yok olur. Kuyruktaki cizim ve arka
 plandaki okumadan donen sonuc olu nesneye gider:
     RuntimeError: Internal C++ object (FigureCanvasQTAgg) already deleted.
 Olculdu: test_nuklid_secici.test_kisa_kosu_yeni_secim ve
 test_tukenme_temel.test_tukenme_kosu ayni surecte kosunca.

 COZUM
   Tuval.draw_idle()      C++ nesnesi silinmisse cizim ISTEMEZ (loglanir).
   Tuval.cizimi_iptal_et() bekleyen cizimi iptal eder; sekme close()'unda.
   canli_mi(widget)       gec gelen geri cagirmalarda "sekme hala var mi".
================================================================================
"""

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

import shiboken6

from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)


def canli_mi(widget):
    """Widget'in C++ nesnesi duruyor mu (silinmis sekmeye gelen gec cagri)."""
    return widget is not None and shiboken6.isValid(widget)


class Tuval(FigureCanvasQTAgg):
    """Silinmis tuvale cizim gondermeyen FigureCanvasQTAgg."""

    def draw_idle(self):                      # noqa: N802 (matplotlib API)
        if not canli_mi(self):
            _log.debug("silinmiş tuvale çizim istendi; yok sayıldı")
            return
        super().draw_idle()

    def cizimi_iptal_et(self):
        """Kuyruktaki cizimi iptal eder (kapanista; zamanlayici bos doner)."""
        self._draw_pending = False
