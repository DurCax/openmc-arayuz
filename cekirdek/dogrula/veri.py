# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/veri.py  --  1. veri kutuphanesi ve nuklid kontrolleri

 cekirdek/dogrula.py'den bolundu (davranis degismedi). Disaridan
 `from cekirdek import dogrula; dogrula.X` ile kullanilir.
"""

import os

from cekirdek.sema import malzeme_bul
from cekirdek import kurucu
from cekirdek.dogrula._ortak import Bulgu


# ============================================================================
# 1. VERI KUTUPHANESI
# ============================================================================

def veri_kutuphanesi_kontrol():
    """OPENMC_CROSS_SECTIONS ayarli mi, dosya var mi?"""
    bulgular = []
    yol = os.environ.get("OPENMC_CROSS_SECTIONS")
    if not yol:
        bulgular.append(Bulgu(
            "hata", "veri kutuphanesi",
            "OPENMC_CROSS_SECTIONS ortam değişkeni ayarlı değil",
            "export OPENMC_CROSS_SECTIONS=$HOME/nucdata/.../cross_sections.xml"))
    elif not os.path.exists(yol):
        bulgular.append(Bulgu(
            "hata", "veri kutuphanesi",
            "cross_sections.xml bulunamadı: %s" % yol,
            "Yolu denetleyin ya da nükleer veri kütüphanesini indirin."))
    return bulgular


def _kutuphane_icerigi():
    """
    cross_sections.xml icindeki notron ve termal kayitlarini okur.
    DONER (notron_adlari, termal_adlari) -- okunamazsa (None, None)
    """
    yol = os.environ.get("OPENMC_CROSS_SECTIONS")
    if not yol or not os.path.exists(yol):
        return None, None
    try:
        import xml.etree.ElementTree as ET
        kok = ET.parse(yol).getroot()
        notron, termal = set(), set()
        for lib in kok.findall("library"):
            tur = lib.get("type")
            mats = (lib.get("materials") or "").split()
            if tur == "neutron":
                notron.update(mats)
            elif tur == "thermal":
                termal.update(mats)
        return notron, termal
    except Exception:
        return None, None


def nuklid_kontrol(spec):
    """
    Modelin istedigi her nuklid veri kutuphanesinde var mi?
    Elementler dogal bollukla nuklidlere acilir; bunun icin malzemeler
    gercekten kurulur.
    """
    bulgular = []
    notron, termal = _kutuphane_icerigi()
    if notron is None:
        bulgular.append(Bulgu("uyari", "veri kutuphanesi",
                              "cross_sections.xml okunamadı; nüklid denetimi atlandı"))
        return bulgular

    try:
        nesneler, _, _ = kurucu.malzemeleri_kur(spec)
    except Exception as e:
        bulgular.append(Bulgu("hata", "malzemeler",
                              "malzemeler kurulamadı: %s" % e))
        return bulgular

    for ad, mat in nesneler.items():
        try:
            istenen = set(mat.get_nuclides())
        except Exception as e:
            bulgular.append(Bulgu("uyari", "malzeme:%s" % ad,
                                  "nüklid listesi çıkarılamadı: %s" % e))
            continue
        eksik = sorted(istenen - notron)
        if eksik:
            bulgular.append(Bulgu(
                "hata", "malzeme:%s" % ad,
                "veri kütüphanesinde olmayan nüklid: %s" % ", ".join(eksik),
                "Bileşimi değiştirin ya da bu nüklidleri içeren bir kütüphane kullanın."))
        for s in (malzeme_bul(spec, ad) or {}).get("sab", []):
            if s not in termal:
                bulgular.append(Bulgu(
                    "hata", "malzeme:%s" % ad,
                    "termal saçılma verisi (S(α,β)) kütüphanede yok: %s" % s,
                    "Kütüphanede %d S(α,β) kaydı var; listeden birini seçin." % len(termal)))
    return bulgular
