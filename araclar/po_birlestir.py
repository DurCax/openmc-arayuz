# -*- coding: utf-8 -*-
"""
po_birlestir.py -- parca .po kataloglarini tek katalogda birlestirir (Babel).

  python3 araclar/po_birlestir.py CIKTI.po PARCA1.po [PARCA2.po ...]

Dalga 3'te cekirdek ve arayuz metinleri ayri kataloglarda (cekirdek.po,
arayuz.po) cevrilir; uygulama tek alan (openmc_arayuz) yukler. Ayni msgid
(ve baglam) iki parcada FARKLI cevrilmisse birlestirme durur (cikis 1):
sessizce birini secmek ceviriyi kaybettirir. Ayni ceviri tekrarsa kaynak
satirlari birlestirilir.
"""

import sys

from babel.messages.catalog import Catalog
from babel.messages.pofile import read_po, write_po


def _oku(yol):
    with open(yol, "rb") as f:
        return read_po(f)


def birlestir(parca_yollari):
    """(katalog, cakismalar) -- cakismalar: ["msgid: parca1 'x' != parca2 'y'"]."""
    ilk = _oku(parca_yollari[0])
    hedef = Catalog(locale=ilk.locale, domain=ilk.domain, project=ilk.project,
                    version=ilk.version, fuzzy=False)
    kaynagi = {}
    cakismalar = []
    for yol in parca_yollari:
        for mesaj in _oku(yol):
            if not mesaj.id:
                continue
            anahtar = (mesaj.context, mesaj.id if isinstance(mesaj.id, str) else mesaj.id[0])
            var = hedef.get(mesaj.id, context=mesaj.context)
            if var is None:
                hedef.add(mesaj.id, mesaj.string, list(mesaj.locations),
                          flags=mesaj.flags, auto_comments=mesaj.auto_comments,
                          user_comments=mesaj.user_comments, context=mesaj.context)
                kaynagi[anahtar] = yol
            elif var.string != mesaj.string and mesaj.string and var.string:
                cakismalar.append("%r: %s %r != %s %r" % (
                    anahtar[1], kaynagi[anahtar], var.string, yol, mesaj.string))
            else:
                var.locations = list(var.locations) + [
                    l for l in mesaj.locations if l not in var.locations]
                if not var.string:
                    var.string = mesaj.string
    return hedef, cakismalar


def main(argv):
    if len(argv) < 2:
        sys.stderr.write(__doc__)
        return 2
    cikti, parcalar = argv[0], argv[1:]
    katalog, cakismalar = birlestir(parcalar)
    if cakismalar:
        sys.stderr.write("HATA: parca kataloglarda celisen ceviriler:\n  %s\n"
                         % "\n  ".join(cakismalar))
        return 1
    with open(cikti, "wb") as f:
        write_po(f, katalog, width=88, sort_output=True)
    print("%s: %d giris (%s)" % (cikti, len(katalog), ", ".join(parcalar)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
