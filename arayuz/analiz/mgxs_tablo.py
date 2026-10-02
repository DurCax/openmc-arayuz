# -*- coding: utf-8 -*-
"""
 mgxs_tablo.py  --  Analiz > Grup sabitleri karti: tablo doldurma ve metinler

 Saf gosterim: MgxsSonuc / Karsilastirma -> QTableWidget satirlari ve ozet
 HTML'i. Hesap cekirdek/mgxs_uret.py, mgxs_is.py ve mgxs_k.py'dedir.
"""

from __future__ import annotations

import html
import math
from typing import Optional, Sequence

from PySide6 import QtCore, QtWidgets

from cekirdek import mgxs_is, mgxs_uret
from cekirdek.ceviri import _

PCM = mgxs_is.PCM
XS_SUTUNLARI = 6           # bolge, tur, g, g', deger, bagil sapma
KARSI_SUTUNLARI = 7        # yontem, k, sigma, fark CE, sigma fark, fark MG, sure
# Tabloda en cok bu kadar satir gosterilir (70 grup x 70 grup x bolge
# saniyelerce cizim demekti); tam veri her zaman mgxs.csv'dedir.
EN_COK_SATIR = 5000


def _oge(metin: str, sayi: Optional[float] = None) -> QtWidgets.QTableWidgetItem:
    o = QtWidgets.QTableWidgetItem(metin)
    o.setFlags(o.flags() & ~QtCore.Qt.ItemIsEditable)
    if sayi is not None:
        o.setData(QtCore.Qt.UserRole, float(sayi))
        o.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
    return o


def _sayi(x: Optional[float], bicim: str = "%.6g") -> str:
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "–"
    return bicim % x


def xs_basliklari() -> list:
    return [_("Bölge"), _("Tür"), "g", "g′", _("Değer"), "σ [%]"]


def xs_doldur(tablo: QtWidgets.QTableWidget, sonuc: mgxs_uret.MgxsSonuc,
              tur_suzgeci: Optional[str] = None) -> int:
    """Tabloyu sonucun satirlariyla doldurur. DONER toplam (suzulmus) satir sayisi."""
    satirlar = [s for s in sonuc.satirlar if tur_suzgeci in (None, s.tur)]
    gosterilen = satirlar[:EN_COK_SATIR]
    tablo.setSortingEnabled(False)
    tablo.setRowCount(len(gosterilen))
    for i, s in enumerate(gosterilen):
        tur = _(mgxs_uret.TUR_ADLARI.get(s.tur, s.tur))
        degerler = (_oge(s.bolge), _oge(tur), _oge(str(s.grup), s.grup),
                    _oge("" if s.giden is None else str(s.giden), s.giden or 0),
                    _oge(_sayi(s.deger), s.deger), _oge(_sayi(100.0 * s.bagil, "%.2f"),
                                                       s.bagil))
        for j, o in enumerate(degerler):
            tablo.setItem(i, j, o)
    return len(satirlar)


def karsi_basliklari() -> list:
    return [_("Yöntem"), "k", "± σ", _("Δk CE'ye [pcm]"), "± [pcm]", _("Δk MG'ye [pcm]"),
            _("Süre [s]")]


def karsi_doldur(tablo: QtWidgets.QTableWidget,
                 satirlar: Sequence[mgxs_is.Karsilastirma]) -> None:
    tablo.setRowCount(len(satirlar))
    for i, s in enumerate(satirlar):
        degerler = (_oge(_(mgxs_is.TURLER[s.tur])), _oge("%.5f" % s.k, s.k),
                    _oge("%.5f" % s.sapma, s.sapma),
                    _oge(_sayi(s.fark_pcm, "%+.0f"), s.fark_pcm or 0.0),
                    _oge(_sayi(s.fark_sapma_pcm, "%.0f"), s.fark_sapma_pcm or 0.0),
                    _oge(_sayi(s.mg_fark_pcm, "%+.0f"), s.mg_fark_pcm or 0.0),
                    _oge(_sayi(s.sure_s, "%.1f"), s.sure_s or 0.0))
        for j, o in enumerate(degerler):
            tablo.setItem(i, j, o)


def _k_metni(d) -> str:
    return "–" if d is None else "%.5f ± %.5f" % (d.ort, d.sapma)


def ozet_html(sonuc: mgxs_uret.MgxsSonuc) -> str:
    """CE k, sabitlerden k (oran ve ozdeger) ve notlar."""
    a = sonuc.ayar
    satirlar = [
        "<b>%s</b>" % html.escape(_("Grup sabitleri hazır: %d bölge, %s (%d grup), düzeltme: %s")
                                  % (len(sonuc.adlar), a.grup_yapisi,
                                     len(sonuc.grup_kenarlari) - 1, a.duzeltme)),
        html.escape(_("CE k: %s") % _k_metni(sonuc.k_ce)),
        html.escape(_("Sabitlerden k = Σ νΣf·φ / Σ Σa·φ ((n,xn) hariç): %s")
                    % _k_metni(sonuc.k_oran)),
    ]
    if sonuc.k_ozdeger is not None:
        satirlar.append(html.escape(
            _("Sonsuz ortam k∞ (G×G özdeğer, yukarı saçılma ve (n,xn) dahil): %s")
            % _k_metni(sonuc.k_ozdeger)))
        if sonuc.k_ce is not None:
            satirlar.append(html.escape(_("Özdeğer − CE: %+.0f pcm")
                                        % ((sonuc.k_ozdeger.ort - sonuc.k_ce.ort) * PCM)))
    satirlar.append("<i>%s</i>" % html.escape(_(
        "σ'lar birinci derece ve bağımsızlık varsayımlıdır (aynı geçmişlerden gelen "
        "tally'ler ilişkilidir); k∞ yalnız yansıtıcı sınırlı (sonsuz kafes) modelde "
        "CE k ile karşılaştırılabilir.")))
    for n in sonuc.notlar:
        satirlar.append("⚠ %s" % html.escape(n))
    satirlar.append(html.escape(_("Kütüphane: %s") % sonuc.h5))
    return "<br>".join(satirlar)
