# -*- coding: utf-8 -*-
"""
================================================================================
 geometri/yerlesim.py  --  Yerlesim ornekleri: merkezler ve "kora bakan" donme
================================================================================

 docs/GEOMETRI_MODELI.md §3.8. Yerlesim, sahibi olan bolgeden bir delik oyar
 ve delige icerik koyar. Yerlestirilen icerigin ON YUZU yerel +x yonudur
 (tamburda emici yay yerel +x'te ortalanmistir).

 ORNEK i ICIN DONME (psi_i, derece; pozitif = saat yonunun tersi)
   halka  : fi_i = baslangic + 360 i / n ; (R cos fi_i, R sin fi_i)
            bakis merkez (0, 0)   -> psi_i = fi_i + 180 + D   (tambur.yerlesim
                                     ile BIT DUZEYINDE ayni; atan2 KULLANILMAZ)
   liste / kafes_konumu, ya da halkada baska bir bakis merkezi:
            bakis merkez (mx, my) -> psi_i = atan2(my - y_i, mx - x_i) + D
   bakis sabit                    -> psi_i = aci + D
   bakis yok                      -> psi_i = icerik.donusum.donme (+ D)
   D = (yerlesimin uyesi oldugu donme grubunun degeri, yoksa 0) + donme_ofset
 donme = 0: emici kora bakiyor (daldirilmis); donme = 180: disa bakiyor.
 (olculdu: testler/test_geometri_yonelim.py -- her mod x ust donme x D)
================================================================================
"""

import math

from cekirdek import altigen
from cekirdek.ceviri import _

# Merkez ile ornek merkezi arasinda bundan kisa mesafe: yon tanimsiz (HATA)
MERKEZ_PAYI = 1.0e-9


def grup_degeri(gruplar, ad, tur="donme"):
    """Yerlesimin (ya da kontrol cubugunun) uyesi oldugu grubun degeri; yoksa None."""
    for g in gruplar or ():
        if g.get("tur") == tur and ad in (g.get("uyeler") or []):
            return float(g.get("deger") or 0.0)
    return None


def _d_acisi(gruplar, y):
    d = grup_degeri(gruplar, y.get("ad"))
    d = 0.0 if d is None else d
    ofset = y.get("donme_ofset")
    return d + float(ofset) if ofset else d


def varsayilan_bakis(tanimlar, icerik):
    """Icerik tambur ise merkeze (0, 0) bakis, degilse None."""
    from cekirdek.geometri.sema import bilesen_tanimi
    if isinstance(icerik, dict) and icerik.get("tur") == "bilesen":
        tur, _t = bilesen_tanimi(tanimlar, icerik.get("ad"))
        if tur == "tambur":
            return {"tur": "merkez", "merkez": [0.0, 0.0]}
    return None


def kafes_konum_merkezleri(kafes, harf):
    """Kafeste 'harf' konumlarinin merkezleri (kafes cercevesi, merkez 0)."""
    P = float(kafes["adim"])
    harita = kafes.get("harita") or []
    if kafes.get("sekil") == "kare":
        nx, ny = kafes["boyut"]
        cikti = []
        for r, satir in enumerate(harita):
            iy = ny - 1 - r
            for ix, h in enumerate(satir):
                if h == harf:
                    cikti.append((-P * nx / 2.0 + (ix + 0.5) * P, -P * ny / 2.0 + (iy + 0.5) * P))
        return cikti
    kon = altigen.konumlar(int(kafes["halka_sayisi"]), kafes.get("yonelim", "y"))
    return [(x * P, y * P) for (r, i), (x, y) in sorted(kon.items())
            if r < len(harita) and i < len(harita[r]) and harita[r][i] == harf]


def _kafes_bul(kap, kimlik):
    adaylar = [kap.get("ic")] + [h.get("icerik") for h in kap.get("halkalar") or []]
    for a in adaylar:
        if isinstance(a, dict) and a.get("tur") == "eksenel":
            a = a.get("icerik")
        if isinstance(a, dict) and a.get("tur") == "kafes" and a.get("id") == kimlik:
            return a
    raise ValueError(_("'kafes_konumu' yerleşimi: '%s' kimlikli kafes kabın içinde değil") % kimlik)


def merkezler(y, kap):
    """Yerlesimin ornek merkezleri [(x, y)] ve halka acilari [fi | None]."""
    mod = y.get("mod")
    if mod == "halka":
        n = int(y.get("sayi") or 0)
        R = float(y.get("merkez_yaricap") or 0.0)
        bas = float(y.get("baslangic_acisi") or 0.0)
        fiz = [bas + 360.0 * i / n for i in range(n)]
        return [(R * math.cos(math.radians(fi)), R * math.sin(math.radians(fi))) for fi in fiz], fiz
    if mod == "liste":
        kon = [(float(p[0]), float(p[1])) for p in y.get("konumlar") or []]
        return kon, [None] * len(kon)
    if mod == "kafes_konumu":
        kon = kafes_konum_merkezleri(_kafes_bul(kap, y.get("kafes")), y.get("harf"))
        return kon, [None] * len(kon)
    raise ValueError(_("bilinmeyen yerleşim modu: %s") % mod)


def ornekler(y, kap, tanimlar, gruplar):
    """
    [(x, y, psi | None)] -- psi None: donme yazilmaz (icerik yerel cercevesi
    kabin cercevesiyle ayni).
    """
    kon, fiz = merkezler(y, kap)
    bakis = y.get("bakis")
    if bakis is None:
        bakis = varsayilan_bakis(tanimlar, y.get("icerik"))
    D = _d_acisi(gruplar, y)
    icerik = y.get("icerik") if isinstance(y.get("icerik"), dict) else {}
    cikti = []
    for (x, yy), fi in zip(kon, fiz):
        cikti.append((x, yy, _psi(bakis, D, x, yy, fi, icerik)))
    return cikti


def _psi(bakis, D, x, y, fi, icerik):
    if bakis is None:
        don = float((icerik.get("donusum") or {}).get("donme") or 0.0) + D
        return don if don else None
    if bakis.get("tur") == "sabit":
        return float(bakis.get("aci") or 0.0) + D
    mx, my = (float(v) for v in bakis.get("merkez") or (0.0, 0.0))
    # cakisma denetimi halka kisayolundan ONCE: R = 0 halkasinda ornek merkezdedir
    if math.hypot(mx - x, my - y) < MERKEZ_PAYI:
        raise ValueError(_("yerleşim örneği bakış merkeziyle çakışıyor (%.6g, %.6g): 'kora "
                         "bakan' yön tanımsız; 'sabit' bakış seçin") % (x, y))
    if fi is not None and mx == 0.0 and my == 0.0:
        return fi + 180.0 + D                      # tambur.yerlesim ile bit duzeyinde ayni
    return math.degrees(math.atan2(my - y, mx - x)) + D
