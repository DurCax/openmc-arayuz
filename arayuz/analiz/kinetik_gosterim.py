# -*- coding: utf-8 -*-
"""
kinetik_gosterim.py -- Nokta kinetigi sonucunun GOSTERIMI (saf islevler):
P(t) grafigi (gerekirse logaritmik; geri beslemede ikinci eksende DT) ve
ozet metni (rho pcm/$, Inhour periyodu, cozumden olculen periyot).
Widget: arayuz/analiz/kinetik.py.
"""

import html
import math
import sys

from cekirdek import kinetik as kin
from cekirdek.ceviri import _
from arayuz.analiz.adlar import renk
from arayuz.analiz.sonuc import YAZI_EKSEN, YAZI_ISARET

LOG_ESIGI = 100.0        # P en buyuk / en kucuk bu orani asarsa y ekseni logaritmik
CIZGI = 1.4              # egri kalinligi [pt]


def periyot_metni(t):
    """Periyot [s]: sonsuzsa '∞'."""
    return "∞" if math.isinf(t) else "%.4g s" % t


def grafik_ciz(figur, cozum):
    """Figuru bastan cizer; DONER P(t) ekseni."""
    figur.clear()
    eksen = figur.add_subplot(111)
    eksen.grid(alpha=0.3)
    eksen.plot(cozum.t, cozum.guc, lw=CIZGI, color=renk("vurgu"), label="P/P₀")
    en_kucuk = max(min(cozum.guc), sys.float_info.min)
    if max(cozum.guc) / en_kucuk > LOG_ESIGI:
        eksen.set_yscale("log")
    eksen.set_xlabel(_("zaman [s]"), fontsize=YAZI_EKSEN)
    eksen.set_ylabel("P(t) / P₀", fontsize=YAZI_EKSEN)
    eksen.tick_params(labelsize=YAZI_ISARET)
    if cozum.sicaklik is not None:
        ikinci = eksen.twinx()
        ikinci.plot(cozum.t, cozum.sicaklik, lw=CIZGI, ls="--", color=renk("uyari"),
                    label="ΔT")
        ikinci.set_ylabel("ΔT [K]", fontsize=YAZI_EKSEN)
        ikinci.tick_params(labelsize=YAZI_ISARET)
    return eksen


def _reaktivite_satiri(rho, beta):
    return _("ρ = %.1f pcm = %.4f $ (β_eff = %.1f pcm)") % (
        kin.pcm_e(rho), kin.dolar_a(rho, beta), kin.pcm_e(beta))


def sonuc_metni(veri, rho_dis, cozum):
    """Zengin metin ozet (HTML kacisli)."""
    t_inhour = periyot_metni(kin.kararli_periyot(veri, rho_dis))
    if cozum.sicaklik is not None:
        inhour = _("Inhour kararlı periyot (geri beslemesiz, dış ρ ile): T = %s") % t_inhour
    else:
        inhour = _("Inhour kararlı periyot: T = %s") % t_inhour
    satirlar = [_reaktivite_satiri(rho_dis, veri.beta_toplam), inhour]
    try:
        satirlar.append(_("Çözümden ölçülen periyot (son %%10): %s")
                        % periyot_metni(kin.periyot_tahmini(cozum)))
    except ValueError as e:
        satirlar.append(_("Çözümden periyot ölçülemedi: %s") % e)
    satirlar.append(_("P(%.4g s) / P₀ = %.4g") % (cozum.t[-1], cozum.guc[-1]))
    if cozum.sicaklik is not None:
        satirlar.append(_("ΔT(%.4g s) = %.4g K; toplam ρ = %.1f pcm")
                        % (cozum.t[-1], cozum.sicaklik[-1], kin.pcm_e(cozum.rho[-1])))
    satirlar.append(_("Veri: %s; çözücü: %s (katı ODE). Nokta kinetiği uzaysal etkileri "
                      "içermez; eğitim amaçlıdır, sertifika değildir.")
                    % (_(veri.kaynak) if veri.kaynak else _("elle"), cozum.yontem))
    return "<br>".join(html.escape(s) for s in satirlar)
