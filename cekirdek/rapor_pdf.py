# -*- coding: utf-8 -*-
"""
rapor_pdf.py -- rapor icerigini PDF'e yazar (QTextDocument + QPdfWriter).

Qt TEMBEL ice aktarilir (yalniz yaz() icinde): cekirdek/ modul duzeyinde
Qt'siz kalir (testler/test_rapor.py AST testi). Uygulama nesnesi yoksa bir
QApplication kurulur; ekran yoksa (terminal, CI) "offscreen" eklentisi
secilir. Gorseller <img src="<ad>"> adlariyla belge kaynagi olarak eklenir
(rapor_sablon.html(gomulu=False)).

Neden QTextDocument: PySide6 zaten bagimlilik; yeni PDF kutuphanesi
(reportlab, weasyprint...) gerekmez. Sinir: HTML/CSS'in alt kumesi.
"""

import os

from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

KENAR_MM = 15.0
COZUNURLUK = 300           # dpi (PDF vektor metin; gorseller bu cozunurlukte yerlesir)


class PdfHatasi(RuntimeError):
    """PDF yazilamadi; metni kullaniciya gosterilir."""


def _uygulama():
    """Var olan Qt uygulamasi ya da yeni QApplication (ekran yoksa offscreen).
    QGuiApplication DEGIL: ayni surecte sonra pencere (QWidget) kurulursa
    QGuiApplication ile surec cokerdi (olculdu: test_rapor_sozlesme RS4)."""
    ekran_var = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    if not ekran_var:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _belge(icerik):
    from PySide6 import QtCore, QtGui
    from cekirdek import rapor_sablon
    belge = QtGui.QTextDocument()
    for ad, veri in icerik["gorseller"].items():
        goruntu = QtGui.QImage.fromData(veri, "PNG")
        if goruntu.isNull():
            _log.warning("PDF: görsel çözülemedi: %s", ad)
            continue
        belge.addResource(QtGui.QTextDocument.ImageResource, QtCore.QUrl(ad), goruntu)
    belge.setHtml(rapor_sablon.html(icerik, gomulu=False))
    return belge


def _yazici(yol):
    from PySide6 import QtCore, QtGui
    from cekirdek import surum
    yazici = QtGui.QPdfWriter(yol)
    yazici.setResolution(COZUNURLUK)
    yazici.setPageSize(QtGui.QPageSize(QtGui.QPageSize.A4))
    yazici.setPageMargins(QtCore.QMarginsF(KENAR_MM, KENAR_MM, KENAR_MM, KENAR_MM),
                          QtGui.QPageLayout.Millimeter)
    yazici.setCreator("%s %s" % (surum.UYGULAMA_ADI, surum.surum()))
    return yazici


def yaz(icerik, yol):
    """icerik (rapor.icerik_topla) -> PDF dosyasi. Hata: PdfHatasi."""
    try:
        _uygulama()
        belge = _belge(icerik)
        yazici = _yazici(yol)
        yazici.setTitle(icerik["kapak"]["baslik"])
        belge.print_(yazici)
        del yazici                       # dosyayi kapatir (QPdfWriter yikicisi)
    except ImportError as e:
        _log.warning("PDF için PySide6 yüklenemedi", exc_info=True)
        raise PdfHatasi(_("PDF için PySide6 gerekli: %s") % e) from e
    if not os.path.exists(yol) or os.path.getsize(yol) == 0:
        _log.warning("PDF yazılamadı (dosya yok ya da boş): %s", yol)
        raise PdfHatasi(_("PDF yazılamadı: %s") % yol)
    return yol
