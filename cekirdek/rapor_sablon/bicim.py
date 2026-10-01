# -*- coding: utf-8 -*-
"""
bicim.py -- raporda sayi ± belirsizlik ve reaktivite gosterimi (K5 ile temiz).

Butun "deger ± sapma" metinleri uygunluk_denetimi.kurallar_rapor.belirsizlik_metni
uzerinden gecer (JCGM 100 §7.2.6: belirsizlik en cok 2 anlamli rakam, deger
ayni basamaga yuvarli, "(1σ)" etiketi). Boylece rapor kendi K5 denetiminden
uyari almaz (testler/test_uygunluk_arayuz.py S2-1).
"""

from cekirdek.ceviri import _
from cekirdek.uygunluk_denetimi.kurallar_rapor import belirsizlik_metni, pcm_tanimi

_AYIRAC = "  |  "                       # kosucu.keff_yorumu ayrinti ayiraci
PCM = 1.0e5
_ZAMAN_BIRIMLERI = ((1e-6, 1e6, "µs"), (1e-9, 1e9, "ns"))


def bm(deger, sapma, birim=""):
    """deger ± sapma (1σ) -- tek bicim."""
    return belirsizlik_metni(deger, sapma, birim=birim)


def gosterim_notu():
    """Raporun basinda bir kez: belirsizlik ve pcm tanimi."""
    return _("Belirsizlikler 1σ standart belirsizliktir (JCGM 100:2008, GUM); bir güven "
             "aralığı değildir. %s. Birimler SI'dır (uzunluk cm, sıcaklık K).") % pcm_tanimi("drho")


def reaktivite_metni(k, sapma, sonsuz=False):
    """ρ = (k − 1)/k; σ_ρ = σ_k / k². pcm (Δρ × 10⁵) olarak, GUM bicimiyle."""
    pcm = (k - 1.0) / k * PCM
    s_pcm = sapma / (k * k) * PCM
    metin = bm(pcm, s_pcm, "pcm")
    if sonsuz:
        return _("ρ∞ = %s (yakıtın taşıdığı reaktivite fazlası)") % metin
    return _("reaktivite ρ = %s") % metin


def kosu_ayrintisi(ayrinti, k, sapma, sonsuz=False):
    """kosucu.keff_yorumu ayrintisinin ilk parcasini (reaktivite) GUM bicimiyle
    degistirir; dolar ve ani kritiklik notlari aynen kalir."""
    parcalar = (ayrinti or "").split(_AYIRAC)
    parcalar[0] = reaktivite_metni(k, sapma, sonsuz)
    return _AYIRAC.join(parcalar)


def zaman_metni(deger, sapma):
    """Notron uretim zamani: okunur birimde (µs / ns / s) GUM bicimi."""
    for esik, carpan, birim in _ZAMAN_BIRIMLERI:
        if deger >= esik:
            return bm(deger * carpan, sapma * carpan, birim)
    return bm(deger, sapma, "s")
