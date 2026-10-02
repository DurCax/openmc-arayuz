# -*- coding: utf-8 -*-
"""
 arayuz/sonuc/yuzey.py  --  Calistir sayfasi: "Yüzey akımı ve kaçak" karti (Y7)

 Statepoint'teki yuzey tally'lerinden (cekirdek/yuzey_oku.py): model sinirinda
 yuzey basina kacak ve global sizintiyla karsilastirma, kutu aginda dis
 yuzlerden giren/cikan kismi akimlar ve notron dengesi, enerji gruplari varsa
 kacak spektrumu (letarji basina, log x). Yuzey tally'si yoksa kart gizlidir.
 Isaret, birim ve varsayimlar kartta yazilir.
"""

import html
import math

from PySide6 import QtCore, QtWidgets

from arayuz import tema
from arayuz.calistir.yakinsama import GrafikKarti
from arayuz.ortak import ipucu
from cekirdek import yuzey_akim as _y
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)
_YUKSEKLIK = 220            # grafik [px]
_EN_COK_YUZEY = 12          # tabloda listelenen sinir yuzeyi (gerisi toplamda)
_ALT_ENERJI_EV = 1.0e-5     # log eksende sifir kenar yerine: OpenMC notron verisinin alt siniri


def _d(deger):
    """Deger -> 'ort ± sapma'; None -> 'bilinmiyor'."""
    if deger is None or not math.isfinite(deger.ort):
        return _("bilinmiyor")
    return "%.4e ± %.1e" % (deger.ort, deger.sapma)


def _sinir_satirlari(r):
    satirlar = [(_("kaçak (vakum sınırı, |J| toplamı)"), _d(r["toplam"]))]
    if len(r["yuzeyler"]) > 1:
        ogeler = list(r["yuzeyler"].items())
        satirlar += [(_("  yüzey %d") % k, _d(v)) for k, v in ogeler[:_EN_COK_YUZEY]]
        if len(ogeler) > _EN_COK_YUZEY:
            satirlar.append(("  …", _("%d yüzey daha") % (len(ogeler) - _EN_COK_YUZEY)))
    if not r.get("global_foton_karisik"):
        satirlar.append((_("global sızıntı (OpenMC)"), _d(r.get("global_sizinti"))))
    return satirlar


def _kutu_satirlari(r):
    satirlar = [(_("giren (dış yüzler)"), _d(r["giren"])), (_("çıkan (dış yüzler)"), _d(r["cikan"])),
                (_("net çıkan"), _d(r["net_cikan"]))]
    for yuz, g in r["yuzler"].items():
        if g["giren"].ort or g["cikan"].ort:
            satirlar.append(("  %s" % yuz, _("giren %s · çıkan %s") % (_d(g["giren"]),
                                                                    _d(g["cikan"]))))
    t = r.get("terimler")
    if t is not None:
        satirlar.append((_("kaynak S · üretim U · soğurma A"), "%s · %s · %s"
                         % (_d(r.get("kaynak")), _d(t["U"]), _d(t["A"]))))
        artik, bagil = r["denge"]["artik"], r["denge"]["bagil"]
        satirlar.append(("S + J_giren − J_çıkan + U − A",
                         _d(artik) + ("" if bagil is None else _("  (bağıl %.1e)") % bagil)))
    return satirlar


def tablo_html(sonuclar):
    renk = tema.renk("metin_soluk")
    parcalar = []
    for r in sonuclar:
        if r["tur"] == _y.FILTRE_SINIR:
            baslik, satirlar = _("model sınırı"), _sinir_satirlari(r)
        else:
            alt, ust = r["sinirlar"]
            baslik = _("kutu ağı %s, %s … %s cm") % (
                "×".join(str(n) for n in r["boyut"]), _uc(alt), _uc(ust))
            satirlar = _kutu_satirlari(r)
        govde = "".join("<tr><td style='color:%s'>%s</td><td align='right'><tt>%s</tt></td></tr>"
                        % (renk, html.escape(a), html.escape(d)) for a, d in satirlar)
        parcalar.append("<b>%s</b> — %s<table cellspacing='3'>%s</table>"
                        % (html.escape(r["ad"]), html.escape(baslik), govde))
    return "<br>".join(parcalar)


def _uc(v):
    return "(%s)" % ", ".join("%g" % x for x in v)


def notlar(sonuclar, sabit, kuvvet):
    if sabit and kuvvet != 1.0:
        birim = _("Birim 1/s: kaynak şiddeti %g ile çarpılmış (kaynak parçacığı başına değer "
                  "için şiddete bölün).") % kuvvet
    elif sabit:
        birim = _("Birim: kaynak parçacığı başına.")
    else:
        birim = _("Birim: kaynak nötronu başına (özdeğer; mutlak değer için güç normalizasyonu "
                  "gerekir).")
    liste = [birim,
             _("Sınır: OpenMC net akımı yüzey normaline göre işaretler (+ normal yönü); vakum "
               "yüzeyinden her geçiş dışarı olduğundan yüzey başına |J| kaçaktır. Toplam global "
               "sızıntıyla aynı olaylardır.")]
    if any(r.get("global_foton_karisik") for r in sonuclar):
        liste.append(_("Foton taşınımı açık: OpenMC global sızıntısı fotonları da sayar; sınır "
                       "tally'si kaynak parçacığına süzüldüğü için karşılaştırılmadı."))
    if any(r["tur"] == _y.FILTRE_KUTU for r in sonuclar):
        liste.append(_("Kutu: OpenMC 'out' hücreden çıkan, 'in' giren kısmi akımdır; iç yüzler "
                       "birbirini götürür. Denge S + J_giren − J_çıkan + U = A; U = nu-scatter − "
                       "scatter ((n,xn) ve MT5), sabit kaynakta + nu-fission."))
        liste.append(_denge_notu(sabit))
        liste.append(_("± birinci derece, terimler arası korelasyon yok sayıldı: yaklaşık."))
    if any(r.get("spektrum") for r in sonuclar):
        liste.append(_("Kaçak spektrumu: grup akımı / Δu (letarji genişliği), kutuda yalnız dış "
                       "yüzlerden çıkan akım."))
    return liste


def _denge_notu(sabit):
    if sabit:
        return _("Sabit kaynak, analog tahminci: denge her geçmişte tamdır (survival biasing, "
                 "ağırlık penceresi ve enerji/zaman kesmesi kapalıyken); artık yalnız "
                 "yuvarlamadır.")
    return _("Özdeğer: S = nu-fission/k yalnız beklenen değerdir; artık istatistiksel, "
             "yakınsamış kaynakta ~σ mertebesindedir (tam değildir).")


class YuzeyKarti(GrafikKarti):
    """Yuzey akimi tablosu + kacak spektrumu."""

    def __init__(self, parent=None):
        super().__init__(_("Yüzey akımı ve kaçak"),
                         _("Sınırdan kaçak, kutu yüzlerinden giren/çıkan, nötron dengesi"),
                         yukseklik=_YUKSEKLIK, parent=parent)
        self.tablo = QtWidgets.QLabel()
        self.tablo.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.ekle(self.tablo)
        self.notlar = ipucu("")
        self.ekle(self.notlar)
        self.sonuclar = None
        self.setVisible(False)

    def dosya_sor(self, varsayilan):
        return super().dosya_sor("kacak_spektrumu.png")

    def sonuc_ayarla(self, statepoint, spec):
        """Statepoint'ten okur; None ya da yuzey tally'si yoksa gizlenir."""
        if statepoint is None or spec is None:
            self.goster(None)
            return
        from cekirdek import yuzey_oku
        a = spec.get("ayarlar") or {}
        try:
            sonuclar = yuzey_oku.oku(statepoint, spec)
        except Exception as e:
            # Kart hatasi Calistir sayfasinin geri kalanini dusurmez.
            _log.exception("yüzey akımı sonucu gösterilemedi: %s", statepoint)
            self.goster(None)
            self.setVisible(True)
            self.tablo.setText(_("Yüzey akımı sonucu okunamadı: %s") % html.escape(str(e)))
            return
        self.goster(sonuclar, sabit=a.get("mod", "eigenvalue") != "eigenvalue",
                    kuvvet=float((a.get("kaynak") or {}).get("kuvvet") or 1.0))

    def goster(self, sonuclar, sabit=True, kuvvet=1.0):
        self.sonuclar = sonuclar
        self.setVisible(bool(sonuclar))
        if not sonuclar:
            self.tablo.clear()
            self.notlar.clear()
            self.eksen.clear()
            self.tuval.draw_idle()
            return
        self.tablo.setText(tablo_html(sonuclar))
        self.notlar.setText("\n".join("• " + n for n in notlar(sonuclar, sabit, kuvvet)))
        self.ciz(sonuclar)

    def ciz(self, sonuclar):
        spektrumlu = [r for r in sonuclar if r.get("spektrum")]
        if not spektrumlu:
            self.bos_yaz(_("Kaçak spektrumu için yüzey tally'sine enerji grupları ekleyin"))
            return
        self.eksen.set_axis_on()
        self.eksen.clear()
        palet = tema.grafik_paleti()
        for sira, r in enumerate(spektrumlu):
            e, y = _letarji_basina(r["spektrum"])
            self.eksen.stairs(y, e, color=palet[sira % len(palet)], lw=1.2, label=r["ad"])
        self.eksen.set_xscale("log")
        self.eksen.set_xlabel(_("enerji [eV]"), fontsize=8)
        self.eksen.set_ylabel(_("J / Δu"), fontsize=8)
        self.eksen.tick_params(labelsize=7)
        self.eksen.grid(True, which="major", alpha=0.3, lw=0.6)
        self.eksen.legend(fontsize=7, loc="best")
        self.tuval.draw_idle()


def _letarji_basina(spk):
    """(kenarlar, deger/Δu); sifir alt kenar log eksende 1e-5 eV'a cekilir
    (OpenMC notron verisinin alt siniri)."""
    e = [max(x, _ALT_ENERJI_EV) for x in spk["kenarlar"]]
    y = [d / math.log(b / a) if b > a else 0.0 for d, a, b in zip(spk["deger"], e, e[1:])]
    return e, y
