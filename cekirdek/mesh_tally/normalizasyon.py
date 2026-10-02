# -*- coding: utf-8 -*-
"""
 cekirdek/mesh_tally/normalizasyon.py  --  mesh tally normalizasyonu ve istatistigi

 OLCU (payda; olcu())
   3B / kure          hucre hacmi V [cm3]
   2B, butun z kolonu hucre ALANI A [cm2]: deger z uzerinden integraldir; hacim
                      basina deger agin keyfi yuksekligine bolunmus olurdu
   2B, elle dar dilim hacim (dilimdeki ortalama); mutlak kip REDDEDILIR (dilim
                      degeri kolonun bilinmeyen bir kesridir)

 KIPLER
   kaynak  ham deger (kaynak nötronu basina; sabit kaynakta kaynak siddetiyle)
   hacim   deger / olcu
   bagil   (deger / olcu) / hacim agirlikli ortalama  = deger/olcu * sum(V)/sum(o)
           (skorlu hucreler) -- 1.00 = ortalama
   mutlak  ozdegerde S = P / (H e); 3B'de P [W] modelin kapsadigi bolgenin gucu
           (guc.py ile ayni tanim), 2B'de P cizgisel guc [W/cm]; deger * S / olcu
           (isinma skorlarinda eV -> J: W/cm3; aki n/cm2 s). H filtresiz genel
           isinma tally'sinden (isi_payi) -- ag fisil bolgeyi kapsamasa da dogru.
 Normalizasyon carpaninin belirsizligi (H'nin sigma'si, bagil ortalamanin sigma'si)
 sigma'ya katilmaz.
"""

import math

import numpy as np

from cekirdek.ceviri import _, N_
from cekirdek.mesh_tally import geometri as _geo
from cekirdek.mesh_tally.tanim import KURESEL, Z_2B_YARI

# CODATA 2018 (SI tanimi, kesin): 1 eV = 1.602176634e-19 J
EV_JOULE = 1.602176634e-19

# Kaba yonerge (tek tally icin): R < 0.10 "genellikle guvenilir" (nokta
# dedektorleri haric). Pin gucu icin hedef <= %1-2 (kilavuz 4.10, ders 5.13).
BAGIL_HATA_ESIGI = 0.10
BAGIL_HATA_KAYNAGI = N_("kaba yönerge (MCNP, tek tally için): MCNP5 Manual Vol. I "
                      "(LA-UR-03-1987), Bölüm 2, 'relative error R' tablosu: R < 0.10 "
                      "genellikle güvenilir.")

# Birim donusumu (eV -> J) yapilan enerji skorlari
ISI_SKORLARI = ("kappa-fission", "fission-q-recoverable", "fission-q-prompt",
                "heating", "heating-local")
# H (normalizasyon paydasi) adaylari -- fission-q-prompt YOK (gecikmis enerji
# dahil degil, ~%7 dusuk). Aki/tepkime icin heating-local: yakalanma gamalari dahil.
H_SKORLARI = ("kappa-fission", "heating-local", "fission-q-recoverable", "heating")
_VARSAYILAN_H = ("heating-local", "kappa-fission")

NORMALIZASYONLAR = ("kaynak", "hacim", "bagil", "mutlak")
NORMALIZASYON_ADLARI = {
    "kaynak": N_("Kaynak nötronu başına"),
    "hacim": N_("Hacim başına (/cm³)"),
    "bagil": N_("Ortalamaya bağıl (1 = ortalama)"),
    "mutlak": N_("Mutlak (toplam güçten)"),
}
OLCU_TURLERI = ("hacim", "alan", "dilim2b")
_KOLON_PAYI = 1.0 - 1.0e-9          # z kapsami >= 2 Z_2B_YARI (yuvarlama payi)


def olcu(sonuc, eksenel_sonsuz: bool):
    """(payda dizisi (n1, n2, n3), tur) -- tur OLCU_TURLERI'nden (modul belgesi)."""
    hacim = _geo.hacimler(sonuc.tur, sonuc.izgaralar)
    if not eksenel_sonsuz or sonuc.tur == KURESEL:
        return hacim, "hacim"
    z = np.asarray(sonuc.izgaralar[2], dtype=float)
    if z[-1] - z[0] >= 2.0 * Z_2B_YARI * _KOLON_PAYI:
        return hacim / np.diff(z)[None, None, :], "alan"
    return hacim, "dilim2b"


def isi_payi(genel: dict, skor: str):
    """(H [eV/kaynak], H skoru): gosterilen skor bir H adayiysa kendisi, degilse
    heating-local, o da yoksa kappa-fission. Genel tally yoksa ValueError."""
    if skor in H_SKORLARI and skor in (genel or {}):
        return float(genel[skor]), skor
    for aday in _VARSAYILAN_H:
        if aday in (genel or {}):
            return float(genel[aday]), aday
    raise ValueError(_("model geneli ısınma tally'si yok (bu sürümden önceki koşu); "
                       "mutlak normalizasyon için koşuyu yineleyin"))


def kaynak_hizi(toplam_guc: float, isi_ev: float) -> float:
    """S = P / (H * e): 3B'de [kaynak/s], 2B'de (P W/cm) [kaynak/(s cm)]."""
    if not (toplam_guc and toplam_guc > 0):
        raise ValueError(_("mutlak normalizasyon için toplam güç sıfırdan büyük olmalı"))
    if not (isi_ev and isi_ev > 0):
        raise ValueError(_("mutlak normalizasyon için ağda ısınma skoru (kappa-fission, "
                           "heating …) sıfırdan büyük olmalı"))
    return float(toplam_guc) / (float(isi_ev) * EV_JOULE)


def birim(skor, yontem, ozdeger=True, olcu_turu="hacim") -> str:
    """Gorunen birim metni."""
    isi, aki = skor in ISI_SKORLARI, skor == "flux"
    if yontem == "bagil":
        return _("bağıl (1 = ortalama)")
    if yontem == "mutlak":
        return "W/cm³" if isi else ("n/cm²·s" if aki else _("tepkime/cm³·s"))
    pay = "eV" if isi else ("n·cm" if aki else _("tepkime"))
    if yontem == "hacim" and olcu_turu == "alan":
        pay = (_("eV/cm² (z integrali)") if isi else
               (_("n/cm (z integrali)") if aki else _("tepkime/cm² (z integrali)")))
    elif yontem == "hacim":
        pay = "eV/cm³" if isi else ("n/cm²" if aki else _("tepkime/cm³"))
    return pay + (_(" / kaynak nötronu") if ozdeger else _(" (kaynak şiddetiyle)"))


def isi_toplami(sonuc, nuklid: int = 0):
    """Tally'deki ilk H adayi skorunun AG ICINDEKI toplami (eV/kaynak); yoksa None.
    Mutlak normalizasyonda KULLANILMAZ (ag fisil bolgeyi kapsamayabilir; isi_payi
    genel tally'yi kullanir) -- kapsama denetimi ve testler icin."""
    from cekirdek.mesh_tally.sonuc import secim
    skor = next((s for s in H_SKORLARI if s in sonuc.skorlar), None)
    if skor is None:
        return None
    return float(secim(sonuc, skor, None, nuklid)[0].sum())


def normalize(ortalama, sapma, payda, yontem, kaynak_hizi=None, skor=None, ozdeger=True,
              olcu_turu="hacim"):
    """(ortalama, sapma, birim) -- yeni diziler (bkz. modul belgesi). payda ve
    olcu_turu olcu()'den."""
    if yontem not in NORMALIZASYONLAR:
        raise ValueError(_("bilinmeyen normalizasyon: %s") % yontem)
    o, s = np.array(ortalama, dtype=float), np.array(sapma, dtype=float)
    b = birim(skor, yontem, ozdeger, olcu_turu)
    if yontem == "kaynak":
        return o, s, b
    payda = np.asarray(payda, dtype=float)
    if yontem == "bagil":
        skorlu = o > 0
        if not skorlu.any():
            raise ValueError(_("bağıl normalizasyon: ağda skorlu hücre yok"))
        # (o/payda) / hacim-agirlikli ortalama: payda'nin bir hucre olcusu
        # (V ya da A) olmasi orani degistirmez -> V esdegeri sum(o)/sum(payda).
        ort = float(o[skorlu].sum()) / float(payda[skorlu].sum())
        return o / payda / ort, s / payda / ort, b
    if yontem == "hacim":
        return o / payda, s / payda, b
    if not ozdeger:
        raise ValueError(_("mutlak normalizasyon yalnız özdeğer hesabında; sabit "
                           "kaynakta değerler kaynak şiddetiyle zaten ölçeklidir"))
    if olcu_turu == "dilim2b":
        raise ValueError(_("2B modelde ağ z kolonunun yalnız bir dilimini kapsıyor; mutlak "
                           "değer tanımsız (otomatik sınırları kullanın)"))
    if not kaynak_hizi:
        raise ValueError(_("mutlak normalizasyon için kaynak hızı gerekli"))
    c = float(kaynak_hizi) * (EV_JOULE if skor in ISI_SKORLARI else 1.0)
    return o * c / payda, s * c / payda, b


# ---------------------------------------------------------------------------
# istatistik
# ---------------------------------------------------------------------------

def bagil_hata(ortalama, sapma):
    """sigma / |deger|; skorsuz (0) hucrede NaN (yeni dizi)."""
    o = np.abs(np.asarray(ortalama, dtype=float))
    s = np.asarray(sapma, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(o > 0, s / np.where(o > 0, o, 1.0), np.nan)


def yuksek_hata_maskesi(ortalama, sapma, esik=BAGIL_HATA_ESIGI):
    """Guvenilmez hucreler: bagil hata > esik ya da hic skor yok."""
    b = bagil_hata(ortalama, sapma)
    return np.isnan(b) | (np.nan_to_num(b, nan=0.0) > esik)


def ozet(ortalama, sapma, esik=BAGIL_HATA_ESIGI) -> dict:
    """{"hucre", "skorsuz", "yuksek", "en_buyuk_bagil"} (skorlu hucrelerde)."""
    b = bagil_hata(ortalama, sapma)
    skorsuz = int(np.isnan(b).sum())
    skorlu = b[~np.isnan(b)]
    return {"hucre": int(b.size), "skorsuz": skorsuz,
            "yuksek": int((skorlu > esik).sum()),
            "en_buyuk_bagil": float(skorlu.max()) if skorlu.size else math.nan}
