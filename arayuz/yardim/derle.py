# -*- coding: utf-8 -*-
"""
 arayuz/yardim/derle.py  --  kilavuzun derleme zamani ciktisi (HTML + PDF) ve
 sozluk bolumunun (10-sozluk.md) docs/SOZLUK.md'den uretilmesi

    python -m arayuz.yardim.derle [--dil tr,en] [--cikti DIZIN] [--bicim html,pdf]
    python -m arayuz.yardim.derle --sozluk      # 10-sozluk.md tablolarini yeniler

 Cevirici Qt'nin kendisidir (QTextDocument.setMarkdown -> toHtml / QPdfWriter):
 calisma zamanina da derlemeye de yeni bagimlilik eklenmez (Qt LGPL; izin
 verici lisans kosulu). Cikti: <cikti>/<dil>/kilavuz.html, kilavuz.pdf ve
 HTML'in kullandigi resimler (<cikti>/resimler/<dil>/...). araclar/kilavuz.sh
 bu modulu cagirir.
"""

import argparse
import os
import re
import shutil
import sys

from arayuz.yardim import kaynak
from cekirdek import yollar
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)


def varsayilan_cikti(kaynak_agaci=None):
    """Varsayilan cikti dizini: kaynak agacinda <kok>/build/kilavuz; kurulu
    pakette kurulum onekine (share/, site-packages) YAZILMAZ ->
    yollar.onbellek_dizini()/kilavuz. kaynak_agaci: None -> yollar.kaynak_agaci_mi()."""
    if kaynak_agaci is None:
        kaynak_agaci = yollar.kaynak_agaci_mi()
    if kaynak_agaci:
        return os.path.join(kaynak.KOK, "build", "kilavuz")
    return os.path.join(yollar.onbellek_dizini(), "kilavuz")


VARSAYILAN_CIKTI = varsayilan_cikti()
SOZLUK_KAYNAGI = os.path.join(kaynak.KOK, "docs", "SOZLUK.md")
SOZLUK_DOSYASI = "10-sozluk.md"
SOZLUK_BASI = "<!-- sozluk:baslangic (araclar/kilavuz.sh --sozluk uretir; elle duzenlemeyin) -->"
SOZLUK_SONU = "<!-- sozluk:son -->"
BASLIKLAR = {"tr": "Kullanım kılavuzu", "en": "User guide"}
PDF_KENAR_MM = 15
PDF_COZUNURLUK = 150
# SOZLUK.md kategori basliklarinin Ingilizcesi (bolum numarasina gore).
_KATEGORI_EN = {
    "1": "Model structure and geometry", "2": "Control",
    "3": "Run settings and Monte Carlo", "4": "Results and analysis",
    "5": "Depletion", "6": "Model check, conformity and report", "7": "User interface",
}


# ----------------------------------------------------------------------------
# HTML + PDF
# ----------------------------------------------------------------------------
def _uygulama():
    from PySide6 import QtGui
    return QtGui.QGuiApplication.instance() or QtGui.QGuiApplication(sys.argv[:1])


def _resimleri_kopyala(html, kaynak_taban, hedef):
    """HTML'deki goreli resimleri hedef dizine (ayni goreli yolla) kopyalar."""
    kopyalanan = []
    for src in sorted(set(re.findall(r'<img src="([^":]+)"', html))):
        kaynak_yol = os.path.normpath(os.path.join(kaynak_taban, src))
        hedef_yol = os.path.normpath(os.path.join(hedef, src))
        if not os.path.exists(kaynak_yol):
            _log.warning("kilavuz derleme: resim yok: %s", kaynak_yol)
            continue
        os.makedirs(os.path.dirname(hedef_yol), exist_ok=True)
        shutil.copyfile(kaynak_yol, hedef_yol)
        kopyalanan.append(hedef_yol)
    return kopyalanan


def html_yaz(klv, hedef):
    from PySide6 import QtGui
    from arayuz.yardim import belge
    _uygulama()
    b, _konum = belge.belge_kur(klv)
    b.setMetaInformation(QtGui.QTextDocument.DocumentTitle, BASLIKLAR.get(klv.dil, ""))
    html = b.toHtml()
    os.makedirs(hedef, exist_ok=True)
    yol = os.path.join(hedef, "kilavuz.html")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(html)
    return [yol] + _resimleri_kopyala(html, klv.taban, hedef)


def pdf_yaz(klv, hedef):
    from PySide6 import QtCore, QtGui
    from arayuz.yardim import belge
    _uygulama()
    os.makedirs(hedef, exist_ok=True)
    yol = os.path.join(hedef, "kilavuz.pdf")
    yazici = QtGui.QPdfWriter(yol)
    yazici.setPageSize(QtGui.QPageSize(QtGui.QPageSize.A4))
    yazici.setPageMargins(QtCore.QMarginsF(*(PDF_KENAR_MM,) * 4), QtGui.QPageLayout.Millimeter)
    yazici.setResolution(PDF_COZUNURLUK)
    yazici.setTitle(BASLIKLAR.get(klv.dil, ""))
    yazici.setCreator("openmc-arayuz")
    b, _konum = belge.belge_kur(klv)
    b.print_(yazici)
    del yazici                      # dosya kapanir
    return [yol]


def derle(diller=kaynak.DILLER, cikti=None, bicimler=("html", "pdf"), dizin=None):
    """Kilavuzu derler; yazilan dosyalarin listesi."""
    cikti = cikti or VARSAYILAN_CIKTI
    yazilan = []
    for dil in diller:
        klv = kaynak.kilavuz(dil, dizin=dizin)
        if klv.eksik:
            _log.warning("kilavuz derleme: %s dilinde TR'den alinan bolumler: %s",
                         dil, ", ".join(klv.eksik))
        hedef = os.path.join(cikti, dil)
        if "html" in bicimler:
            yazilan += html_yaz(klv, hedef)
        if "pdf" in bicimler:
            yazilan += pdf_yaz(klv, hedef)
    return yazilan


# ----------------------------------------------------------------------------
# Sozluk (docs/SOZLUK.md -> 10-sozluk.md)
# ----------------------------------------------------------------------------
def _hucreler(satir):
    return [h.strip() for h in satir.strip().strip("|").split("|")]


def sozluk_terimleri(yol=None):
    """SOZLUK.md tablolari: [(turkce, english, kacin, not, kategori_no, kategori)].
    SOZLUK.md yalniz kaynak agacinda vardir (kurulu pakete girmez): yoksa
    acik FileNotFoundError."""
    yol = yol or SOZLUK_KAYNAGI
    if not os.path.isfile(yol):
        raise FileNotFoundError("%s yok: sozluk yalniz kaynak agacindan (docs/SOZLUK.md) "
                                "uretilir" % yol)
    terimler, kategori, no = [], "", ""
    with open(yol, encoding="utf-8") as f:
        for satir in f:
            b = re.match(r"^##\s+(\d+)\.\s+(.+?)\s*$", satir)
            if b:
                no, kategori = b.group(1), b.group(2)
                continue
            if not satir.startswith("|") or not no:
                continue
            h = _hucreler(satir)
            if len(h) < 2 or h[0] in ("Türkçe", "") or set(h[0]) <= {"-", ":"}:
                continue
            h += [""] * (4 - len(h))
            terimler.append((h[0], h[1], h[2], h[3], no, kategori))
    return terimler


def sozluk_tablolari(dil, terimler=None):
    """10-sozluk.md'nin uretilen kismi (Markdown)."""
    terimler = sozluk_terimleri() if terimler is None else terimler
    satirlar, kategori = [], None
    for tr, en, kacin, notu, no, ad in terimler:
        if no != kategori:
            kategori = no
            baslik = ad if dil == "tr" else _KATEGORI_EN.get(no, "Section %s" % no)
            satirlar += ["", "### 10.%s %s" % (no, baslik), ""]
            satirlar += (["| Türkçe | English | Kaçın | Not |", "|---|---|---|---|"] if dil == "tr"
                         else ["| English | Turkish | Avoid |", "|---|---|---|"])
        satirlar.append("| %s | %s | %s | %s |" % (tr, en, kacin, notu) if dil == "tr"
                        else "| %s | %s | %s |" % (en, tr, kacin))
    return "\n".join(satirlar).strip() + "\n"


def sozluk_yenile(dizin=None):
    """Her dilin 10-sozluk.md'sinde iki isaret arasini yeniden uretir."""
    yazilan = []
    terimler = sozluk_terimleri()
    for dil in kaynak.DILLER:
        yol = kaynak.dosya_yolu(dil, SOZLUK_DOSYASI, dizin)
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
        bas, son = metin.find(SOZLUK_BASI), metin.find(SOZLUK_SONU)
        if bas < 0 or son < bas:
            raise ValueError("%s: sozluk isaretleri yok" % yol)
        yeni = (metin[:bas + len(SOZLUK_BASI)] + "\n\n" + sozluk_tablolari(dil, terimler)
                + "\n" + metin[son:])
        with open(yol, "w", encoding="utf-8") as f:
            f.write(yeni)
        yazilan.append(yol)
    return yazilan


# ----------------------------------------------------------------------------
def _ayristirici():
    a = argparse.ArgumentParser(description="Kullanım kılavuzunu HTML + PDF olarak derler")
    a.add_argument("--dil", default=",".join(kaynak.DILLER), help="tr,en")
    a.add_argument("--cikti", default=VARSAYILAN_CIKTI, help="çıktı dizini")
    a.add_argument("--bicim", default="html,pdf", help="html,pdf")
    a.add_argument("--sozluk", action="store_true",
                   help="yalnız 10-sozluk.md tablolarını docs/SOZLUK.md'den yenile")
    return a


def main(argv=None):
    arg = _ayristirici().parse_args(argv)
    if arg.sozluk:
        try:
            yazilan = sozluk_yenile()
        except FileNotFoundError as e:
            print(e, file=sys.stderr)
            return 2
        for yol in yazilan:
            print(yol)
        return 0
    diller = tuple(d for d in arg.dil.split(",") if d)
    bilinmeyen = [d for d in diller if d not in kaynak.DILLER]
    if bilinmeyen:
        print("bilinmeyen dil: %s" % ", ".join(bilinmeyen), file=sys.stderr)
        return 2
    for yol in derle(diller, arg.cikti, tuple(arg.bicim.split(","))):
        print(yol)
    return 0


if __name__ == "__main__":
    sys.exit(main())
