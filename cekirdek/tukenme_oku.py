# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_oku.py  --  Tukenme sonucunu (depletion_results.h5) okuma
================================================================================

 cekirdek/tukenme.py'den bolundu (v3 Y4; davranis degismedi). Genel adlar
 tukenme modulunden yeniden disa aktarilir: `tukenme.sonuc_oku(...)`.
 hacimler()/yanma() tukenme modulunden CAGRI ANINDA okunur (testler onlari
 tukenme uzerinden degistirir).
================================================================================
"""

import collections
import math
import os
import threading
import types

from cekirdek import spektrum as _y3          # Y3: tukenmede spektrum tally'leri kapali


def _tk():
    from cekirdek import tukenme
    return tukenme


# Sonuc okuma kaynagi onbellegi: {(h5, boyut, mtime, spec imzasi): (Results,
# {malzeme_id: ad}, hacimler)}. Olculdu: Results() 3820 nuklidli dosyada
# 1.8 s, kurucu.kur + hacimler ~0.5 s; secim degisince bunlar TEKRARLANMAZ.
_SONUC_KAYNAGI = collections.OrderedDict()   # kilitli LRU (v3 K3)
_SONUC_KILIDI = threading.Lock()
_SONUC_KAYNAGI_EN_COK = 2


def _klon_kaydi(model, spec, hv, nesneler):
    """
    Cubuk cubuk yanmanin (malzemeleri_ayir) klonlari: {malzeme_id: (ad, hacim)}.

    Klonlar kosudakiyle AYNI yolla (tukenme_hacim.ornekleri_ayir) kurulur;
    malzeme basina, Cell.paths (= distribcell ornek) sirasinda numaralanir:
    "uo2 #1", "uo2 #2", ... Boylece sonuc tablosu ve CSV klonlari kimlik
    numarasiyla ("1043") degil okunur adiyla gosterir ve her klonun kendi
    hacmi bilindigi icin yogunluk [atom/b-cm] hesaplanabilir.
    """
    from cekirdek import tukenme_hacim
    kayit = {}
    for ad, m in nesneler.items():
        once = {x.id for x in model.geometry.get_all_materials().values()}
        m.depletable = True
        m.volume = hv[ad]["hacim"]
        tukenme_hacim.ornekleri_ayir(model, spec, {ad: hv[ad]}, {ad: m})
        yeni = [x for x in model.geometry.get_all_materials().values()
                if x.id not in once]
        for i, klon in enumerate(sorted(yeni, key=lambda x: x.id), 1):
            kayit[str(klon.id)] = ("%s #%d" % (ad, i), klon.volume)
    return kayit


def _malzeme_haritasi(spec):
    """
    ({malzeme_id: gorunen ad}, {gorunen ad: hacim cm3}).
    Cubuk cubuk yanmada klonlar da (ad ve kendi hacmiyle) haritaya girer.
    """
    from cekirdek import kurucu
    model, kb = kurucu.kur(_y3.tukenme_icin(spec))      # Y3 tukenmede kapali
    hv = _tk().hacimler(spec)
    ad_by_id = {str(m.id): ad for ad, m in kb["malzemeler"].items()}
    hacim_by_ad = {ad: v.get("hacim") for ad, v in hv.items()}
    if not (spec.get("tukenme") or {}).get("malzemeleri_ayir"):
        return ad_by_id, hacim_by_ad
    nesneler = {a: kb["malzemeler"][a] for a in hv if a in kb["malzemeler"]}
    for mid, (ad, hacim) in _klon_kaydi(model, spec, hv, nesneler).items():
        ad_by_id[mid] = ad
        hacim_by_ad[ad] = hacim
    return ad_by_id, hacim_by_ad


def _sonuc_kaynagi(h5, spec):
    """(Results, {malzeme_id: ad}, {ad: hacim}) -- dosya/spec degismedikce onbellekten."""
    import json
    import openmc.deplete as d
    bilgi = os.stat(h5)
    anahtar = (os.path.abspath(h5), bilgi.st_size, bilgi.st_mtime,
               json.dumps(spec, sort_keys=True, default=str))
    with _SONUC_KILIDI:
        kaynak = _SONUC_KAYNAGI.get(anahtar)
        if kaynak is not None:
            _SONUC_KAYNAGI.move_to_end(anahtar)
            return kaynak
    # Okuma kilit DISINDA (saniyeler): arka plan iscileri birbirini beklemez.
    r = d.Results(h5)
    ad_by_id, hacim_by_ad = _malzeme_haritasi(spec)
    kaynak = (r, types.MappingProxyType(ad_by_id), types.MappingProxyType(hacim_by_ad))
    with _SONUC_KILIDI:
        _SONUC_KAYNAGI[anahtar] = kaynak
        _SONUC_KAYNAGI.move_to_end(anahtar)
        while len(_SONUC_KAYNAGI) > _SONUC_KAYNAGI_EN_COK:
            _SONUC_KAYNAGI.popitem(last=False)
    return kaynak


def _yanmalar(zaman_d, guclu, p):
    """Birikimli yanma [MWd/kgHM]: yalniz guclu araliklar (sogutmada artmaz).
    Kayit j'nin gucu [t_j, t_j+1] araligina aittir."""
    yanma, toplam = [0.0], 0.0
    for j in range(1, len(zaman_d)):
        if guclu[j - 1]:
            toplam += _tk().yanma(float(zaman_d[j]) - float(zaman_d[j - 1]), p)
        yanma.append(toplam)
    return yanma


def _guclu_listesi(r, n):
    """Kayit basina guc > 0 mi. source_rate tasimayan (eski/taklit) sonucta
    hepsi guclu sayilir (Y4 oncesi davranis)."""
    try:
        return [bool(float(r[i].source_rate) > 0) for i in range(n)]
    except AttributeError:
        return [True] * n


def _kok(adim):
    """Kritik aramanin bu adimda buldugu deger (ppm ya da %); yoksa None."""
    v = getattr(adim, "keff_search_root", None)
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def sonuc_oku(h5, spec, izlenen=None):
    """
    DONER {"zaman_d", "yanma", "k", "k_sapma", "atomlar": {malz: {nuklid: [..]}},
           "yogunluk": {malz: {nuklid: [atom/b-cm]}}, "adim_sayisi",
           "bulunamayan": [sonuc dosyasinda olmayan izlenen adlar]}

    izlenen verilmezse spec'teki tukenme.izlenen okunur. Verilirse (arayuzde
    secim degisti) ayni h5'ten okunur; kosu tekrarlanmaz. Bulunamayan ad
    (or. "Xe-135") eskiden SESSIZCE atlaniyordu; simdi listelenir ve loglanir.
    """
    from cekirdek.gunluk import kaydedici
    r, ad_by_id, hacim_by_ad = _sonuc_kaynagi(h5, spec)
    zaman, k = r.get_keff(time_units="d")
    # v3 Y4: sogutma (guc 0) adiminda OpenMC transport kosmaz ve k = 0 +- 0
    # yazar; hizli kipte k hic yoktur. Bunlar NaN gosterilir (sifir degil).
    guclu = _guclu_listesi(r, len(zaman))
    kli = [g and float(x) > 0 and math.isfinite(float(x)) for g, x in zip(guclu, k[:, 0])]
    p = float(spec["tukenme"]["guc_yogunlugu"])
    if izlenen is None:
        izlenen = (spec.get("tukenme") or {}).get("izlenen") or []
    bilinen = r[0].index_nuc
    bulunamayan = [n for n in izlenen if n not in bilinen]
    atomlar, yogunluk = {}, {}
    for mid in r[0].index_mat.keys():
        ad = ad_by_id.get(str(mid), str(mid))
        atomlar[ad], yogunluk[ad] = {}, {}
        V = hacim_by_ad.get(ad)
        for n in (n for n in izlenen if n in bilinen):
            _t, a = r.get_atoms(str(mid), n)
            atomlar[ad][n] = [float(x) for x in a]
            if V:
                yogunluk[ad][n] = [float(x) / V * 1e-24 for x in a]
    if bulunamayan:
        kaydedici(__name__).warning("tükenme sonucunda bulunamayan nüklidler (%s): %s",
                                    h5, ", ".join(bulunamayan))
    return {
        "zaman_d": [float(x) for x in zaman],
        "yanma": _yanmalar(zaman, guclu, p),
        "k": [float(x) if g else math.nan for x, g in zip(k[:, 0], kli)],
        "k_sapma": [float(x) if g else math.nan for x, g in zip(k[:, 1], kli)],
        "guclu": guclu,
        "arama_degeri": [_kok(r[i]) for i in range(len(zaman))],
        "atomlar": atomlar,
        "yogunluk": yogunluk,
        "adim_sayisi": len(zaman) - 1,
        "bulunamayan": bulunamayan,
    }
