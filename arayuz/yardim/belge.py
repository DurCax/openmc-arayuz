# -*- coding: utf-8 -*-
"""
 arayuz/yardim/belge.py  --  Kilavuz -> QTextDocument (gosterici, HTML, PDF)

 Qt'nin kendi Markdown okuyucusu (QTextDocument.setMarkdown, GitHub lehcesi)
 kullanilir; calisma zamanina YENI BAGIMLILIK yoktur. Okuyucu basliklara capa
 koymaz: kaynak.ayristir'in buldugu kimlikler baslik bloklarina sirayla
 eslenir ve karakter bicimine capa adi olarak yazilir. Boylece
 QTextBrowser.scrollToAnchor ve toHtml() (<a name="...">) ikisi de calisir.

 Yalniz QtGui kullanir (QWidget gerekmez); QGuiApplication yeterlidir.
"""

import os

from PySide6 import QtCore, QtGui

from arayuz.yardim import kaynak
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

RESIM_EN_GENIS = 760        # px; daha genis ekran goruntusu orantili kuculur


def baslik_bloklari(belge):
    """Belgedeki baslik bloklari, sirayla: [QTextBlock]."""
    bloklar = []
    b = belge.begin()
    while b.isValid():
        if b.blockFormat().headingLevel() > 0:
            bloklar.append(b)
        b = b.next()
    return bloklar


def _capa_koy(blok, kimlik):
    imlec = QtGui.QTextCursor(blok)
    imlec.movePosition(QtGui.QTextCursor.EndOfBlock, QtGui.QTextCursor.KeepAnchor)
    bicim = QtGui.QTextCharFormat()
    bicim.setAnchor(True)
    bicim.setAnchorNames([kimlik])
    imlec.mergeCharFormat(bicim)


def capalari_koy(belge, basliklar):
    """kaynak.Baslik listesindeki kimlikleri baslik bloklarina yazar.
    Eslesme metinle yapilir (sira korunur); eslesmeyen kimlik loglanir.
    Donus: {kimlik: blok numarasi}."""
    bloklar = baslik_bloklari(belge)
    konum, i = {}, 0
    for b in basliklar:
        j = i
        while j < len(bloklar) and kaynak.duz_baslik(bloklar[j].text()) != b.metin:
            j += 1
        if j == len(bloklar):
            if b.kimlik:
                _log.warning("kilavuz: baslik bulunamadi, capa konmadi: %s (%s)", b.kimlik, b.metin)
            continue
        if b.kimlik:
            _capa_koy(bloklar[j], b.kimlik)
            konum[b.kimlik] = bloklar[j].blockNumber()
        i = j + 1
    return konum


def _resim_boyutu(taban, ad):
    yol = os.path.normpath(os.path.join(taban, ad))
    boyut = QtGui.QImageReader(yol).size()
    return boyut if boyut.isValid() else None


def resimleri_olcekle(belge, taban, en_genis=RESIM_EN_GENIS):
    """Genis resimleri en_genis'e orantili indirir (kaynak dosya degismez)."""
    b = belge.begin()
    while b.isValid():
        it = b.begin()
        while not it.atEnd():
            parca = it.fragment()
            bicim = parca.charFormat()
            if bicim.isImageFormat():
                resim = bicim.toImageFormat()
                boyut = _resim_boyutu(taban, resim.name())
                if boyut is not None and boyut.width() > en_genis:
                    resim.setWidth(en_genis)
                    resim.setHeight(boyut.height() * en_genis / boyut.width())
                    imlec = QtGui.QTextCursor(belge)
                    imlec.setPosition(parca.position())
                    imlec.setPosition(parca.position() + parca.length(), QtGui.QTextCursor.KeepAnchor)
                    imlec.setCharFormat(resim)
            it += 1
        b = b.next()


def belge_kur(klv, ust=None, en_genis=RESIM_EN_GENIS):
    """Kilavuz -> (QTextDocument, {kimlik: blok numarasi})."""
    belge = QtGui.QTextDocument(ust)
    belge.setBaseUrl(QtCore.QUrl.fromLocalFile(klv.taban + os.sep))
    belge.setMarkdown(klv.markdown, QtGui.QTextDocument.MarkdownDialectGitHub)
    konum = capalari_koy(belge, klv.basliklar)
    resimleri_olcekle(belge, klv.taban, en_genis)
    return belge, konum
