# -*- coding: utf-8 -*-
"""
================================================================================
 guc_katlama.py  --  Pin gucu tablosunun ceyrek katlamasi (yalniz dogrulanmis simetri)
================================================================================
 guc_tablo.py'den ayrildi (v3 K3 incelemesi). guc_tablo.ceyrek_katla /
 ceyrek_simetri adlariyla da erisilir.

 SIMETRI DENETIMI (hepsi gecmeli; biri bile tutmazsa katlanmaz, neden yazilir)
   * model: gelismis (agac) mod, tamburlu kor, kare olmayan duzey, kesik cubuk -> red
   * geometrideki her kare kafes x ve y'de ayna simetrik (evren kimlikleri) ve
     kendi elemaninda ortalanmis
   * kafes ya da evrenle dolu hicbir hucrede oteleme / donme yok
   * her duzeydeki BUTUN kafesler o duzeyin temsilci kafesiyle ayni sekilde
     (farkli boyutlu demetler ayni korda -> red) ve anahtar indeksleri aralikta
   * tablonun konum kumesi aynalamaya kapali (ayni cubuk turuyle)

 KATLI SATIR
   bagil = yorunge ortalamasi; σ = max(√Σσ²/m, s_uye/√m): tek kosu σ'si iyimser
   (guc.py basligi), uyelerin gercek sacilmasi ondan buyukse o kullanilir.
   asimetri = max|uye − ort| / ort; asimetri_sigma = max|uye − ort| / max σ_uye.
   asimetri_sigma > ASIMETRI_SIGMA olan yorunge varsa UYARI (red degil: σ
   iyimser oldugu icin gurultu de bu esigi asabilir; kullanici karar verir).
================================================================================
"""

import math

from cekirdek import guc as _guc
from cekirdek.ceviri import _
from cekirdek.guc_faktor import TEPE_YAKINLIK_SIGMA

_MERKEZ_TOLERANSI = 1e-6     # kafes ortalanmis mi [cm] (yuvarlama payi)
_OTELEME_TOLERANSI = 1e-9    # hucre otelemesi sifir mi [cm]
# Uyari esigi (gecti/kaldi degil): 3σ normal dagilimda ~%0.3 olasilik; tek kosu
# σ'si iyimser oldugundan gercek gurultu de bunu asabilir -> yalniz uyari.
ASIMETRI_SIGMA = 3.0
_DERINLIK_SINIRI = 16


def _kafes_simetrik(kafes):
    """(bool, neden): kare kafes x ve y'de ayna simetrik ve ortalanmis mi."""
    import numpy as np
    import openmc
    if not isinstance(kafes, openmc.RectLattice):
        return False, _("kare olmayan kafes (%s)") % type(kafes).__name__
    kimlik = np.vectorize(lambda u: u.id)(np.asarray(kafes.universes, dtype=object))
    if not (np.array_equal(kimlik, kimlik[..., ::-1]) and
            np.array_equal(kimlik, kimlik[..., ::-1, :])):
        return False, _("kafes %d ayna simetrik değil") % kafes.id
    adim = np.asarray(kafes.pitch, dtype=float)[:2]
    boyut = np.asarray(kafes.shape, dtype=float)[:2]
    if np.any(np.abs(np.asarray(kafes.lower_left, dtype=float)[:2] + adim * boyut / 2.0)
              > _MERKEZ_TOLERANSI):
        return False, _("kafes %d elemanında ortalanmamış") % kafes.id
    return True, ""


def _oteleme_var(hucre):
    import numpy as np
    t = getattr(hucre, "translation", None)
    if t is not None and np.any(np.abs(np.asarray(t, dtype=float)) > _OTELEME_TOLERANSI):
        return True
    return getattr(hucre, "rotation", None) is not None


def _dolu_hucre_denetimi(geometri):
    """Kafes/evrenle dolu hucrede oteleme ya da donme varsa neden; yoksa None."""
    for h in geometri.get_all_cells().values():
        if h.fill_type in ("lattice", "universe") and _oteleme_var(h):
            return _("hücre %d dolgusu ötelenmiş ya da döndürülmüş") % h.id
    return None


def _alt_kafesler(evren, derinlik=0):
    """Evrenin icindeki (kafes olmayan ara evrenlerden gecerek) ilk kafesler."""
    import openmc
    bulunan = []
    if derinlik > _DERINLIK_SINIRI:
        return bulunan
    for h in evren.cells.values():
        if isinstance(h.fill, openmc.Lattice):
            bulunan.append(h.fill)
        elif isinstance(h.fill, openmc.UniverseBase):
            bulunan += _alt_kafesler(h.fill, derinlik + 1)
    return bulunan


def _duzey_sekilleri(geometri):
    """{derinlik: {sekil}} -- kok evrenden baslayarak kafes ic ice derinligi."""
    import numpy as np
    sekiller, gorulen = {}, set()
    sira = [(k, 0) for k in _alt_kafesler(geometri.root_universe)]
    while sira:
        kafes, d = sira.pop()
        if (kafes.id, d) in gorulen or d > _DERINLIK_SINIRI:
            continue
        gorulen.add((kafes.id, d))
        sekiller.setdefault(d, set()).add(tuple(kafes.shape[:2]))
        evrenler = {u.id: u for u in np.asarray(kafes.universes, dtype=object).ravel()}
        for u in evrenler.values():
            sira += [(alt, d + 1) for alt in _alt_kafesler(u)]
    return sekiller


def _sekil_denetimi(dagilim, boyutlar):
    geo = dagilim.get("geometri")
    if geo is None:
        return None
    hata = _dolu_hucre_denetimi(geo)
    if hata:
        return hata
    sekiller = _duzey_sekilleri(geo)
    for d, kume in sekiller.items():
        if d < len(boyutlar) and kume != {boyutlar[d]}:
            return _("%d. düzeyde farklı boyutlu kafesler var: %s") % (
                d + 1, ", ".join("%d×%d" % s for s in sorted(kume)))
    return None


def _model_reddi(dagilim, spec):
    """Katlamayi geometriye bakmadan reddeden durumlar; yoksa None."""
    from cekirdek import sema
    if spec is not None and sema.agac_modu(spec):
        return _("gelişmiş (ağaç) modelde simetri doğrulanamıyor")
    if spec is not None and int(((spec.get("kor") or {}).get("tambur") or {}).get("sayi") or 0):
        return _("kontrol tamburlu kor simetrik sayılmaz")
    turler = dagilim.get("kafes_turleri") or [dagilim.get("kafes_turu")]
    if any(t != "kare" for t in turler):
        return _("çeyrek katlama yalnız kare kafeste")
    if dagilim.get("kesik_cubuklar"):
        return _("kesik çubuklu modelde katlanmaz")
    return None


def _parcalar(anahtar):
    return [anahtar] if not isinstance(anahtar[0], tuple) else list(anahtar)


def _ayna(anahtar, boyutlar, eksen):
    """Anahtarin x (eksen 0) ya da y (eksen 1) aynasi; duzey basina boyutla."""
    tek = not isinstance(anahtar[0], tuple)
    yeni = []
    for p, (nx, ny) in zip(_parcalar(anahtar), boyutlar):
        p = list(p)
        p[eksen] = (nx if eksen == 0 else ny) - 1 - p[eksen]
        yeni.append(tuple(p))
    return yeni[0] if tek else tuple(yeni)


def _aralikta(anahtar, boyutlar):
    return all(0 <= p[0] < nx and 0 <= p[1] < ny
               for p, (nx, ny) in zip(_parcalar(anahtar), boyutlar))


def _konum_denetimi(tablo, dagilim, boyutlar):
    turler = {r["anahtar"]: r["tur"] for r in tablo}
    for a, tur in turler.items():
        metin = _guc.konum_metni(a, None, dagilim.get("kafes_turleri"))
        if not _aralikta(a, boyutlar):
            return _("%s konumu düzey kafesinin dışında (farklı boyutlu demet)") % metin
        for eksen in (0, 1):
            if turler.get(_ayna(a, boyutlar, eksen)) != tur:
                return _("%s konumunun aynası tabloda yok ya da farklı türde") % metin
    return None


def ceyrek_simetri(tablo, dagilim, spec=None):
    """(bool, neden) -- ceyrek katlama yapilabilir mi (bkz. modul basligi)."""
    red = _model_reddi(dagilim, spec)
    if red:
        return False, red
    tum = dagilim.get("tum_kafesler") or {}
    if not tum:
        return False, _("geometri kafesleri okunamadı")
    for kafes in tum.values():
        tamam, neden = _kafes_simetrik(kafes)
        if not tamam:
            return False, neden
    boyutlar = [tuple(k.shape[:2]) for k in dagilim["kafesler"]]
    neden = _sekil_denetimi(dagilim, boyutlar) or _konum_denetimi(tablo, dagilim, boyutlar)
    return (False, neden) if neden else (True, "")


def _yorunge(a, boyutlar):
    ax = _ayna(a, boyutlar, 0)
    return sorted({a, ax, _ayna(a, boyutlar, 1), _ayna(ax, boyutlar, 1)}, key=repr)


def _katli_satir(uyeler):
    """Yorunge satiri (YENI sozluk; temsilcinin ic listeleri paylasilmaz)."""
    m = len(uyeler)
    b = [u["bagil"] for u in uyeler]
    ort = sum(b) / m
    s_uye = math.sqrt(sum((x - ort) ** 2 for x in b) / (m - 1)) if m > 1 else 0.0
    sigma = max(math.sqrt(sum(u["sigma"] ** 2 for u in uyeler)) / m, s_uye / math.sqrt(m))
    sapma = max(abs(x - ort) for x in b)
    s_en = max(u["sigma"] for u in uyeler)
    W = [u["W"] for u in uyeler]
    q = [u["q"] for u in uyeler]
    temsilci = max(uyeler, key=lambda u: (u["x"], u["y"]))      # sag ust ceyrek
    satir = {k: v for k, v in temsilci.items() if not isinstance(v, (list, tuple, dict))}
    satir.update(anahtar=temsilci["anahtar"], uyeler=tuple(u["anahtar"] for u in uyeler),
                 bagil=ort, sigma=sigma,
                 W=(sum(W) / m) if None not in W else None,
                 W_sigma=None, q=(sum(q) / m) if None not in q else None,
                 sicak=any(u["sicak"] for u in uyeler),
                 asimetri=(sapma / ort) if ort else 0.0,
                 asimetri_sigma=(sapma / s_en) if s_en > 0 else 0.0,
                 dilimler=(), tepe_q=None, tepe_yakini=False)
    return satir


def _tepe_isaretle(satirlar):
    """D4: tepeden birlesik TEPE_YAKINLIK_SIGMA·σ icindeki satirlar (yeni sozlukler)."""
    adaylar = [r for r in satirlar if not r.get("kesik")]
    if not adaylar:
        return list(satirlar)
    tepe = max(adaylar, key=lambda r: r["bagil"])
    return [dict(r, tepe_yakini=(not r.get("kesik")) and tepe["bagil"] - r["bagil"]
                 <= TEPE_YAKINLIK_SIGMA * math.hypot(r["sigma"], tepe["sigma"]))
            for r in satirlar]


def ceyrek_katla(tablo, dagilim, spec=None):
    """
    (katli tablo | None, not). Simetri yoksa (None, neden). Katlandiysa not:
    katli F_ΔH ve (varsa) asimetri uyarisi. Dilim ayrintisi katlanmaz.
    """
    tamam, neden = ceyrek_simetri(tablo, dagilim, spec)
    if not tamam:
        return None, neden
    boyutlar = [tuple(k.shape[:2]) for k in dagilim["kafesler"]]
    satirlar = {r["anahtar"]: r for r in tablo}
    goruldu, katli = set(), []
    for r in tablo:
        if r["anahtar"] in goruldu:
            continue
        yorunge = _yorunge(r["anahtar"], boyutlar)
        goruldu.update(yorunge)
        katli.append(_katli_satir([satirlar[a] for a in yorunge]))
    katli = _tepe_isaretle(katli)
    notlar = [_("Katlı F_ΔH = %.4f (yörünge ortalamalarının en büyüğü).")
              % max(r["bagil"] for r in katli)]
    asimetrik = [r for r in katli if r["asimetri_sigma"] > ASIMETRI_SIGMA]
    if asimetrik:
        notlar.append(_("Uyarı — asimetri: %d yörüngede üyeler arası fark %gσ'yı aşıyor. Ya "
                        "σ iyimser (tek koşu) ya da model gerçekten asimetrik; katlı değerleri "
                        "dikkatle kullanın.") % (len(asimetrik), ASIMETRI_SIGMA))
    return katli, " ".join(notlar)
