# -*- coding: utf-8 -*-
"""
================================================================================
 arayuz/geometri/onizleme_secim.py  --  OpenMC onizlemesinde tiklama -> dugum yolu
================================================================================
 Sag paneldeki gercek OpenMC kesiti (arayuz/onizleme.py) tiklaninca noktayi
 iceren hucre openmc.Geometry.find ile bulunur (openmc.lib gerekmez); hucre
 kimligi GeometriDizini.hucre_yolu ile agactaki dugume cevrilir (§7 onizleme).

 Dizin yol bicimi kurucunun adlandirmasidir ("/kok/halkalar/0/icerik",
 ".../yerlesim/<ad>#<i>", R3b "/kok/ic/<konum>/<katman>"); agac_yolu() bunu
 editorun yol demetine cevirir (yerlesim adi -> yerlesimler indeksi).
================================================================================
"""

from cekirdek.gunluk import kaydedici
from arayuz.geometri import duzenle

_log = kaydedici("arayuz.geometri.onizleme_secim")


def agac_yolu(dizin_yolu, agac):
    """Kurucu dizin yolu -> editor yol demeti (var olan en yakin ata)."""
    parcalar = [p for p in str(dizin_yolu or "").split("/") if p]
    yol = ()
    i = 0
    while i < len(parcalar):
        p = parcalar[i]
        if p == "yerlesim" and i + 1 < len(parcalar):
            ad = parcalar[i + 1].split("#")[0]
            liste = duzenle.al(agac, yol + ("yerlesimler",)) or []
            j = next((k for k, y in enumerate(liste) if y.get("ad") == ad), None)
            if j is None:
                break
            yol = yol + ("yerlesimler", j, "icerik")
            i += 2
            continue
        aday = yol + ((int(p),) if p.isdigit() else (p,))
        if duzenle.al(agac, aday) is None:
            break
        yol = aday
        i += 1
    return yol or duzenle.KOK


def nokta_yolu(model, dizin, agac, nokta):
    """(x, y, z) noktasindaki en derin kayitli hucrenin agac yolu; yoksa None."""
    if model is None or dizin is None:
        return None
    try:
        yollar = model.geometry.find(tuple(float(v) for v in nokta))
    except Exception:
        _log.info("onizleme noktasi bulunamadi: %r", nokta, exc_info=True)
        return None
    hucre_yolu = getattr(dizin, "hucre_yolu", {}) or {}
    for nesne in reversed(yollar or []):
        kimlik = getattr(nesne, "id", None)
        if kimlik in hucre_yolu and hasattr(nesne, "fill"):
            return agac_yolu(hucre_yolu[kimlik], agac)
    return None


def vurgu_renkleri(model, dizin, agac, yol, vurgu, soluk):
    """Hucre renklendirmesinde secili dugumun hucreleri 'vurgu', digerleri 'soluk'."""
    if model is None or dizin is None or not yol:
        return None
    renkler = {}
    hucre_yolu = getattr(dizin, "hucre_yolu", {}) or {}
    for hucre in model.geometry.get_all_cells().values():
        dy = hucre_yolu.get(hucre.id)
        secili = dy is not None and duzenle.ata_mi(yol, agac_yolu(dy, agac))
        renkler[hucre] = vurgu if secili else soluk
    return renkler
