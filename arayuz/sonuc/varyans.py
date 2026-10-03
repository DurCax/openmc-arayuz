# -*- coding: utf-8 -*-
"""
 arayuz/sonuc/varyans.py  --  Calistir sayfasi: "Verimlilik (FOM)" karti (Y9)

 Statepoint'teki her kullanici tally'si icin (butun binlerin toplami) bagil hata ve
 FOM = 1 / (sigma_bagil^2 T) (cekirdek/varyans.py). Sabit kaynak kosusunda ya da
 varyans azaltma acikken gorunur. Agirlik penceresi kullanildiysa uretim kosusunun
 suresi bu T'ye girmez (kart bunu yazar); yanlilik denetimi icin analog kosuyla
 2 sigma icinde uyum beklenir.
"""

import html

from PySide6 import QtCore, QtWidgets

from arayuz import bilesenler as b
from arayuz import tema
from arayuz.ortak import ipucu
from cekirdek import varyans
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)


def tablo_html(satirlar) -> str:
    renk = tema.renk("metin_soluk")
    basliklar = (_("tally"), _("toplam"), _("σ"), _("σ bağıl"), _("T [s]"), _("FOM"))
    ust = "".join("<th align='%s' style='color:%s'>%s</th>"
                  % ("left" if i == 0 else "right", renk, html.escape(h))
                  for i, h in enumerate(basliklar))
    govde = "".join(
        "<tr><td>%s</td><td align='right'><tt>%.4e</tt></td><td align='right'><tt>%.2e</tt></td>"
        "<td align='right'><tt>%.2f %%</tt></td><td align='right'><tt>%.1f</tt></td>"
        "<td align='right'><tt>%.3g</tt></td></tr>"
        % (html.escape(s.ad), s.deger, s.sapma, 100.0 * s.bagil_hata, s.sure_s, s.fom)
        for s in satirlar)
    return "<table cellspacing='4'><tr>%s</tr>%s</table>" % (ust, govde)


class VaryansKarti(b.Kart):
    """FOM tablosu (tally basina)."""

    def __init__(self, parent=None):
        super().__init__(_("Verimlilik (FOM)"), _(
            "FOM = 1 / (σ_bağıl² · T): ne kadar büyükse aynı belirsizliğe o kadar kısa "
            "sürede inilir"), parent=parent)
        self.tablo = QtWidgets.QLabel()
        self.tablo.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.ekle(self.tablo)
        self.notlar = ipucu("")
        self.ekle(self.notlar)
        self.satirlar = None
        self.setVisible(False)

    def sonuc_ayarla(self, statepoint, spec):
        """Statepoint'ten okur; uygun degilse ya da tally yoksa gizlenir."""
        if statepoint is None or spec is None:
            self.goster(None)
            return
        a = spec.get("ayarlar") or {}
        try:
            acik = varyans.ayar(spec).var
        except ValueError:
            acik = False
        if not (acik or a.get("mod") == "fixed source"):
            self.goster(None)
            return
        try:
            satirlar = varyans.fom_tablosu(statepoint)
        except Exception as e:
            _log.exception("FOM okunamadı: %s", statepoint)      # kart sayfayi dusurmez
            self.goster(None)
            self.setVisible(True)
            self.tablo.setText(_("FOM okunamadı: %s") % html.escape(str(e)))
            return
        self.goster(satirlar, acik)

    def goster(self, satirlar, pencere=False):
        self.satirlar = satirlar
        self.setVisible(bool(satirlar))
        if not satirlar:
            self.tablo.clear()
            self.notlar.clear()
            return
        self.tablo.setText(tablo_html(satirlar))
        notlar = [_("σ bağıl: tally'nin tüm bölmeleri toplanarak (bağımsız kabul) hesaplanır; "
                    "bölme bazında FOM için tally'yi tek bölmeye indirin.")]
        if pencere:
            notlar.append(_("Ağırlık penceresi: T bu koşunun süresidir; pencereleri üreten "
                            "analog koşunun süresi eklenmemiştir. Yanlılıksızlık için aynı "
                            "tally'yi analog koşuyla 2σ içinde karşılaştırın."))
        self.notlar.setText("\n".join("• " + n for n in notlar))
