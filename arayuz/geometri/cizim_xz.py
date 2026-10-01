# -*- coding: utf-8 -*-
"""
================================================================================
 arayuz/geometri/cizim_xz.py  --  Sematik xz kesiti (y = 0 duzlemi)
================================================================================
 xy kesitiyle ayni oge bicimi (cizim.Oge), koordinatlar (x, z). Kok kabin
 bolgeleri y = 0 dogrusunu kestigi araliklarda dikey seritlerdir; eksenel
 yigin katmanlari yatay bantlardir (katman sinirlari 'cizgiler' ile kesikli
 cizilir, §10). Kafes: y = 0'i kesen hucreler sutun olur. Yerlesim ornekleri
 (tambur, kanal) y = 0'i kesiyorsa tam yukseklikte sutundur.
 2B modelde xz yoktur (xz_ogeleri bos doner).
================================================================================
"""

import math

from PySide6 import QtCore, QtGui

from cekirdek.geometri import yerlesim as _yer
from cekirdek.geometri.sema import bilesen_tanimi
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from arayuz.geometri import renk as _renk
from arayuz.geometri.cizim import (Oge, _hata_ekle, altigen_koseleri, bolge_kesitleri,
                                   kafes_konumlari,
                                   katman_araliklari, katman_icerigi, yol_metni, zarf)

_log = kaydedici("arayuz.geometri.cizim_xz")
SQ3 = math.sqrt(3.0)
_EN_DERIN = 6


def yarim_genislik(kes, dy, zarf=None):
    """Kesitin merkezinden dy uzaktaki yatay kirisin yarisi; kesmiyorsa None."""
    s = (kes or {}).get("sekil")
    if s == "dikdortgen":
        gx, gy = (float(v) for v in kes["boyut"])
        return gx / 2.0 if abs(dy) <= gy / 2.0 else None
    if s in ("silindir", "kure"):
        r = float(kes["yaricap"])
        return math.sqrt(r * r - dy * dy) if abs(dy) < r else None
    if s == "altigen":
        return _cokgen_kirisi(altigen_koseleri(float(kes["apotem"]), kes.get("yonelim", "y")), dy)
    if s == "kafes_zarfi" and zarf:
        return _cokgen_kirisi(altigen_koseleri(zarf[0], zarf[1]), dy)
    return None


def _cokgen_kirisi(koseler, dy):
    xs = []
    n = len(koseler)
    for i in range(n):
        (x1, y1), (x2, y2) = koseler[i], koseler[(i + 1) % n]
        if (y1 - dy) * (y2 - dy) <= 0 and y1 != y2:
            xs.append(x1 + (dy - y1) * (x2 - x1) / (y2 - y1))
    return max(abs(x) for x in xs) if xs else None


class _XzCizici:
    def __init__(self, spec, model, z0, z1):
        from arayuz import izgara
        self.spec, self.m, self.z0, self.z1 = spec, model, z0, z1
        self.ogeler, self.cizgiler = [], []
        self._izgara = izgara

    def renk(self, ad):
        return _renk.parca_rengi(self.spec, ad)

    def serit(self, yol, x0, x1, z0, z1, renk, etiket=None):
        if x1 - x0 <= 0 or z1 - z0 <= 0:
            return
        p = QtGui.QPainterPath()
        p.addRect(QtCore.QRectF(x0, z0, x1 - x0, z1 - z0))
        self.ogeler.append(Oge(tuple(yol), yol_metni(yol), p, renk, None, etiket))

    # ------------------------------------------------------------------
    def icerik(self, d, yol, araliklar, z0, z1, derinlik=0):
        """d dugumunu x araliklari [(x0, x1)] ve [z0, z1] bandinda cizer."""
        if derinlik > _EN_DERIN:
            return
        if isinstance(d, str) or d is None or d.get("tur") in ("malzeme", "bilesen"):
            ad = d if isinstance(d, str) or d is None else d.get("ad")
            renk = self._bilesen_rengi(ad)
            for x0, x1 in araliklar:
                self.serit(yol, x0, x1, z0, z1, renk, ad)
            return
        tur = d.get("tur")
        if tur == "eksenel":
            self._eksenel(d, yol, araliklar, z0, z1, derinlik)
        elif tur == "kafes":
            self._kafes(d, yol, araliklar, z0, z1, derinlik)
        elif tur == "kap":
            self.kap(d, yol, araliklar, z0, z1, derinlik)

    def _bilesen_rengi(self, ad):
        tur, tanim = bilesen_tanimi(self.m.tanimlar, ad)
        if tur == "demet":
            return self.renk(tanim.get("dolgu_disi") or ad)
        return self.renk(ad or "bosluk")

    def _eksenel(self, d, yol, araliklar, z0, z1, derinlik):
        yukseklik = z1 - z0
        toplam = sum(b - a for _i, a, b in katman_araliklari(d)) or yukseklik
        olcek = yukseklik / toplam
        orta = (z0 + z1) / 2.0
        for i, a, b in katman_araliklari(d):
            k = d["katmanlar"][i]
            za, zb = orta + a * olcek, orta + b * olcek
            if za > z0 + 1e-9:
                self.cizgiler.append(za)
            if k.get("icerik") is not None:
                self.icerik(k["icerik"], yol + ("katmanlar", i, "icerik"), araliklar, za, zb,
                            derinlik + 1)
            else:
                self.icerik(katman_icerigi(d, k), yol + ("icerik",), araliklar, za, zb,
                            derinlik + 1)

    def _kafes(self, d, yol, araliklar, z0, z1, derinlik):
        P = float(d.get("adim") or 0.0)
        self.icerik(d.get("dis"), yol + ("dis",), araliklar, z0, z1, derinlik + 1)
        if P <= 0:
            return
        sekil = d.get("sekil", "kare")
        yari_y = P / 2.0 if sekil == "kare" else P / SQ3
        anahtar = d.get("anahtar") or {}
        harita = d.get("harita") or []
        for (r, i), (x, y) in kafes_konumlari(sekil, P, harita, d.get("boyut"),
                                              d.get("halka_sayisi"), d.get("yonelim", "y")):
            if abs(y) >= yari_y * 0.999:
                continue
            try:
                harf = harita[r][i]
            except IndexError:
                continue
            if harf not in anahtar:
                continue
            kx = P / 2.0 if sekil == "kare" else self._hucre_kirisi(d, P, y)
            alt = _kes(araliklar, x - kx, x + kx)
            if alt:
                self.icerik(anahtar[harf], yol + ("anahtar", harf), alt, z0, z1, derinlik + 1)

    @staticmethod
    def _hucre_kirisi(d, P, y):
        from cekirdek.geometri.kesit import ters_yonelim
        g = _cokgen_kirisi(altigen_koseleri(P / 2.0, ters_yonelim(d.get("yonelim", "y"))), -y)
        return g or P / 2.0

    # ------------------------------------------------------------------
    def kap(self, d, yol, araliklar, z0, z1, derinlik=0, kok=False):
        kesitler = bolge_kesitleri(d)
        w = [yarim_genislik(k, 0.0, zarf(d)) or 0.0 for k in kesitler]
        if d.get("dis") is not None:
            dis_alt = _cikar(araliklar, -w[-1], w[-1])
            self.icerik(d.get("dis"), yol + ("dis",), dis_alt, z0, z1, derinlik + 1)
        bolgeler = [(("ic",), d.get("ic"), d.get("yerlesimler") or [], [(-w[0], w[0])])]
        for i, h in enumerate(d.get("halkalar") or []):
            bolgeler.append((("halkalar", i, "icerik"), h.get("icerik"),
                             h.get("yerlesimler") or [], [(-w[i + 1], -w[i]), (w[i], w[i + 1])]))
        for alt_yol, icerik, yerlesimler, bant in bolgeler:
            reg = _kesisim(araliklar, bant)
            delikler = self._delikler(d, alt_yol, yerlesimler)
            dolu = reg
            for _y, _ic, x0, x1 in delikler:
                dolu = _cikar(dolu, x0, x1)
            self.icerik(icerik, yol + alt_yol, dolu, z0, z1, derinlik + 1)
            for y_yol, y_ic, x0, x1 in delikler:
                alt = _kes(reg, x0, x1)
                if alt:
                    self.icerik(y_ic, yol + y_yol, alt, z0, z1, derinlik + 1)

    def _delikler(self, kap, bolge_yol, yerlesimler):
        cikti = []
        taban = bolge_yol[:-1] if bolge_yol[-1] == "icerik" else ()
        for j, y in enumerate(yerlesimler):
            try:
                ornekler = _yer.ornekler(y, kap, self.m.tanimlar, self.m.gruplar)
            except (ValueError, KeyError, TypeError) as e:
                _log.info("xz yerlesim ornekleri hesaplanamadi: %s", e)
                continue
            kes = y.get("kesit")
            if kes is None:
                _t, t = bilesen_tanimi(self.m.tanimlar, (y.get("icerik") or {}).get("ad"))
                kes = {"sekil": "silindir", "yaricap": float((t or {}).get("yaricap") or 0.0)}
            for x, yy, _psi in ornekler:
                g = yarim_genislik(kes, -yy)
                if g:
                    cikti.append((taban + ("yerlesimler", j, "icerik"), y.get("icerik"),
                                  x - g, x + g))
        return cikti


def _kes(araliklar, a, b):
    return [(max(x0, a), min(x1, b)) for x0, x1 in araliklar if min(x1, b) > max(x0, a)]


def _kesisim(araliklar, bant):
    cikti = []
    for a, b in bant:
        cikti += _kes(araliklar, a, b)
    return cikti


def _cikar(araliklar, a, b):
    cikti = []
    for x0, x1 in araliklar:
        if b <= x0 or a >= x1:
            cikti.append((x0, x1))
            continue
        if a > x0:
            cikti.append((x0, a))
        if b < x1:
            cikti.append((b, x1))
    return cikti


def xz_ogeleri(spec, hatalar=None):
    """(ogeler, kutu (x0, z0, x1, z1), katman cizgileri [z]); 2B'de ([], None, []).
    Birim cm (yalniz dikdortgenler; egri yok). Hata gunluge (warning) ve
    verilmisse 'hatalar' listesine."""
    from cekirdek import geometri
    try:
        m = geometri.model(spec)
        H = geometri.yukseklik(m)
    except Exception as e:
        _log.warning("sematik xz icin model kurulamadi", exc_info=True)
        _hata_ekle(hatalar, _("Kesit hesaplanamadı: %s") % e)
        return [], None, []
    if not H:
        return [], None, []
    c = _XzCizici(spec, m, -H / 2.0, H / 2.0)
    kok = m.kok
    w = yarim_genislik(bolge_kesitleri(kok)[-1], 0.0, zarf(kok)) or 1.0
    try:
        c.kap(kok, ("kok",), [(-w, w)], -H / 2.0, H / 2.0)
    except Exception as e:
        _log.warning("sematik xz cizilemedi", exc_info=True)
        _hata_ekle(hatalar, _("Kesit eksik çizildi (hesaplanamadı): %s") % e)
    return c.ogeler, (-w, -H / 2.0, w, H / 2.0), sorted(set(round(z, 9) for z in c.cizgiler))
