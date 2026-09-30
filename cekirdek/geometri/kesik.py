# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/kesik.py  --  Kesik ve gizli kafes konumlari (R11, §8 UYARI 1 / BILGI)
================================================================================

 Bir kap bolgesinin (ic ya da halka) dogrudan icerigi olan kafesin her konumu
 icin eleman hucresinin siniri orneklenir (koseler, kenar ortalari, merkez):
   tam    : butun noktalar bolgede ve hicbir delikte degil
   gizli  : butun noktalar deliklerin icinde (konum tamamen oyulmus)
   kesik  : aradaki her durum (delik ya da bolge siniri konumu kirpiyor)
 Yalniz saf geometri (openmc gerektirmez). Kafes zarfli kokte (R3b) konumlar
 kendi prizmasidir, kirpilmaz. Uyari/bilgi mesajlari G-2'nin dogrula/agac'indadir;
 burada yalniz liste uretilir.
================================================================================
"""

import math

from cekirdek import altigen
from cekirdek.geometri import kesit as _k
from cekirdek.geometri import yerlesim as _yer

SQ3 = math.sqrt(3.0)


def _eleman_noktalari(sekil, P, yonelim, cx, cy, pay=1.0e-7):
    """Eleman hucresi sinirindan (biraz iceride) noktalar + merkez."""
    if sekil == "kare":
        h = P / 2.0 - pay
        return [(cx + sx * h, cy + sy * h) for sx in (-1, 0, 1) for sy in (-1, 0, 1)]
    eleman = _k.ters_yonelim(yonelim)
    kes = {"sekil": "altigen", "apotem": P / 2.0 - pay, "yonelim": eleman}
    return _k.sinir_noktalari(kes, (cx, cy)) + [(cx, cy)]


def _konumlar(kafes):
    """[(indeks, (x, y))] -- kafes cercevesinde merkezler (harita sirasi)."""
    P = float(kafes["adim"])
    harita = kafes.get("harita") or []
    if kafes.get("sekil") == "kare":
        nx, ny = kafes["boyut"]
        return [((r, i), (-P * nx / 2.0 + (i + 0.5) * P, P * ny / 2.0 - (r + 0.5) * P))
                for r, satir in enumerate(harita) for i in range(len(satir))]
    kon = altigen.konumlar(int(kafes["halka_sayisi"]), kafes.get("yonelim", "y"))
    return [((r, i), (x * P, y * P)) for (r, i), (x, y) in sorted(kon.items())]


def _delikler(kap, bolge, tanimlar, gruplar):
    """Bolgedeki yerlesim delikleri [(kesit, merkez)]."""
    liste = []
    yerlesimler = kap.get("yerlesimler") if bolge == "ic" else \
        kap["halkalar"][bolge].get("yerlesimler")
    for y in yerlesimler or []:
        kes = y.get("kesit")
        if kes is None:
            from cekirdek.geometri.sema import bilesen_tanimi
            _t, t = bilesen_tanimi(tanimlar, (y.get("icerik") or {}).get("ad"))
            kes = {"sekil": "silindir", "yaricap": float((t or {}).get("yaricap") or 0.0)}
        for x, yy, _psi in _yer.ornekler(y, kap, tanimlar, gruplar):
            liste.append((kes, (x, yy)))
    return liste


def bolge_kesitleri(kap):
    """(ic sinir, [halka i dis siniri]) kesitleri."""
    kesitler = [kap["kesit"]]
    for h in kap.get("halkalar") or []:
        kesitler.append(h["dis"] if h.get("dis") is not None
                        else _k.buyut(kesitler[-1], h["kalinlik"]))
    return kesitler


def kap_kesikleri(kap, tanimlar, gruplar, yol="kok"):
    """Kabin bolgelerindeki kafeslerin kesik/gizli konumlari."""
    if kap["kesit"].get("sekil") == "kafes_zarfi":
        return []
    kesitler = bolge_kesitleri(kap)
    sonuc = []
    bolgeler = [("ic", kap.get("ic"))] + [(i, h.get("icerik"))
                                         for i, h in enumerate(kap.get("halkalar") or [])]
    for bolge, icerik in bolgeler:
        if isinstance(icerik, dict) and icerik.get("tur") == "eksenel":
            icerik = icerik.get("icerik")
        if not (isinstance(icerik, dict) and icerik.get("tur") == "kafes"):
            continue
        dis = kesitler[0] if bolge == "ic" else kesitler[bolge + 1]
        ic = None if bolge == "ic" else kesitler[bolge]
        delikler = _delikler(kap, bolge, tanimlar, gruplar)
        for idx, (cx, cy) in _konumlar(icerik):
            harf = icerik["harita"][idx[0]][idx[1]]
            durum = _durum(_eleman_noktalari(icerik["sekil"], float(icerik["adim"]),
                                             icerik.get("yonelim", "y"), cx, cy),
                           dis, ic, delikler)
            if durum != "tam":
                sonuc.append({"kafes": icerik.get("id"), "yol": yol, "indeks": idx,
                              "harf": harf, "durum": durum})
    return sonuc


def _durum(noktalar, dis, ic, delikler):
    delikte = [any(_k.icinde(kes, x, y, merkez=m, pay=0.0) for kes, m in delikler)
               for x, y in noktalar]
    bolgede = [_k.icinde(dis, x, y, pay=0.0) and (ic is None or not _k.icinde(ic, x, y, pay=0.0))
               for x, y in noktalar]
    if all(delikte):
        return "gizli"
    if all(b and not d for b, d in zip(bolgede, delikte)):
        return "tam"
    if not any(b and not d for b, d in zip(bolgede, delikte)):
        return "gizli"
    return "kesik"


def kesik_konumlar(m):
    """Modelin kesik/gizli konumlari: kok ve parcalardaki butun kaplar."""
    from cekirdek.geometri.sema import cocuklar
    sonuc, ziyaret = [], set()

    def gez(d, yol):
        if not isinstance(d, dict) or id(d) in ziyaret:
            return
        ziyaret.add(id(d))
        if d.get("tur") == "kap":
            sonuc.extend(kap_kesikleri(d, m.tanimlar, m.gruplar, yol))
        for c in cocuklar(d):
            gez(c, yol + "/" + str(c.get("id") or c.get("tur")))
    gez(m.kok, "kok")
    for p in m.parcalar:
        gez(p.get("dugum"), "parcalar/%s" % p.get("ad"))
    return sonuc
