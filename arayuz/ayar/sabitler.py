# -*- coding: utf-8 -*-
"""
 arayuz/ayar/sabitler.py  --  hesap ayarlari sabitleri ve saf yardimcilar (hassasiyet, belirsizlik)

 arayuz/sekme_ayar.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import sekme_ayar; sekme_ayar.X` aynen calisir.
"""

import math


# Hesap hassasiyeti onayarlari: (anahtar, ad, parcacik, cevrim, pasif)
HASSASIYET = [
    ("hizli", "Hızlı deneme", 1000, 60, 20),
    ("normal", "Normal", 10000, 150, 40),
    ("hassas", "Hassas", 50000, 300, 80),
]
OZEL = "ozel"

# sigma_k [pcm] ~ SIGMA_KATSAYISI / sqrt(parcacik x aktif cevrim)
# (pwr_pinhucre olcumu; ayrinti modul basliginda)
SIGMA_KATSAYISI = 9.0e4

# Skorlar: (OpenMC adi, gorunen ad)
SKORLAR = [
    ("flux", "Akı (flux)"),
    ("fission", "Fisyon (fission)"),
    ("absorption", "Soğurma (absorption)"),
    ("nu-fission", "Fisyon nötronu üretimi (nu-fission)"),
    ("scatter", "Saçılma (scatter)"),
    ("total", "Toplam etkileşim (total)"),
    ("elastic", "Esnek saçılma (elastic)"),
    ("(n,gamma)", "Işınımsal yakalama (n,gamma)"),
    ("(n,2n)", "(n,2n) tepkimesi"),
    ("heating", "Isınma (heating)"),
    ("kappa-fission", "Fisyon enerjisi (kappa-fission)"),
    ("fission-q-prompt", "Anlık fisyon enerjisi (fission-q-prompt)"),
    ("damage-energy", "Hasar enerjisi (damage-energy)"),
]
_SKOR_ADI = dict(SKORLAR)

# Skor setleri: (anahtar, ad, skorlar)
SKOR_SETLERI = [
    ("aki", "Akı", ["flux"]),
    ("reaksiyon", "Reaksiyon hızları", ["fission", "absorption", "nu-fission"]),
    ("isi", "Isı / güç", ["kappa-fission", "heating"]),
]

SICAKLIK_YONTEMLERI = [
    ("interpolation", "Ara değer (interpolation)"),
    ("nearest", "En yakın sıcaklık (nearest)"),
]

GUC_SKORLARI = [
    ("kappa-fission", "Fisyon enerjisi (kappa-fission)"),
    ("fission-q-recoverable", "Geri kazanılabilir fisyon enerjisi (fission-q-recoverable)"),
    ("fission-q-prompt", "Anlık fisyon enerjisi (fission-q-prompt)"),
    ("heating-local", "Yerel ısınma (heating-local)"),
]

_FILTRE_ADI = {"malzeme": "malzeme", "hucre": "hücre", "enerji": "enerji",
               "mesh": "mesh"}


def hassasiyet_bul(parcacik, cevrim, pasif, ozdeger=True):
    """Degerlere uyan onayarin anahtari; uyan yoksa OZEL. Sabit kaynakta pasif
    cevrim kullanilmadigi icin karsilastirmaya girmez."""
    for anahtar, _ad, n, c, p in HASSASIYET:
        if n == parcacik and c == cevrim and (p == pasif or not ozdeger):
            return anahtar
    return OZEL


def belirsizlik_pcm(parcacik, cevrim, pasif):
    """Beklenen k-eff belirsizligi [pcm] (olcume dayali kaba tahmin); aktif
    cevrim yoksa None."""
    aktif = int(cevrim) - int(pasif)
    if parcacik <= 0 or aktif <= 0:
        return None
    return SIGMA_KATSAYISI / math.sqrt(float(parcacik) * aktif)


def _binlik(n):
    """10000 -> '10 000' (Turkce yazim: binlik ayraci bosluk)."""
    return "{:,}".format(int(n)).replace(",", " ")


def _pcm_yuvarla(s):
    if s >= 100:
        return int(round(s, -1))
    if s >= 20:
        return int(round(s / 5.0) * 5)
    return int(round(s))
