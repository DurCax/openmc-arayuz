# -*- coding: utf-8 -*-
"""
uygunluk_denetimi/kurallar_rapor.py -- Profil D: raporlama.

  K4  veri izlenebilirligi: rapor.tekrarlanabilirlik alanlarinin hepsi
      biliniyor mu (OpenMC surumu, kutuphane, zincir sha256, tohum...) ve
      her malzemenin sicakligi tanimli mi (ANS-10.4; NUREG/CR-6698 §2.3)
  K5  belirsizlik ve birim bildirimi (JCGM 100 §7.2.2, §7.2.6; BIPM SI):
      a) "±" varsa 1σ / standart belirsizlik etiketi
      b) belirsizlik en cok 2 anlamli rakam
      c) deger belirsizlikle AYNI ondalik basamaga yuvarli
      d) pcm varsa tanimi (Δk × 10⁵ mi Δρ × 10⁵ mi) yazili
      e) SI disi birim yok (inch, ft, °F, psi, BTU, lbm)

 S-2 icin yardimcilar (rapor ve panel AYNI bicimi kullansin):
   belirsizlik_metni(k, s)  -> "1.1822 ± 0.0029 (1σ)"
   pcm_tanimi("dk" | "drho") -> tanim cumlesi
"""

import html as _html
import math
import os
import re

from cekirdek.ceviri import _, N_
from cekirdek.uygunluk_denetimi.kurallar import STANDART, Kural
from cekirdek.uygunluk_denetimi.profiller import GUM

_ORNEK = 3
_CIFT = re.compile(r"(?<![\w.+\-])([-+]?\d+(?:\.\d+)?)\s*(?:±|\+/-)\s*(\d+(?:\.\d+)?)"
                   r"(?![\d.]*[eE][-+]?\d)\s*(%)?")
_ETIKET = re.compile(r"1\s*σ|1\s*sigma|standart belirsizlik|standard uncertainty", re.I)
_PCM = re.compile(r"\bpcm\b")
_PCM_BUYUKLUK = re.compile(r"Δk|Δρ|delta[ _-]?(k|rho)", re.I)
_PCM_OLCEK = re.compile(r"10\s*(⁵|⁻⁵|\^\s*-?5)|1e-?5", re.I)
_SI_DISI = re.compile(r"(?<!\w)(inch|inç|feet|ft|psia?|BTU|lbm|°F)(?!\w)")


_UST_RAKAMLARI = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def _cift_metni(deger, sapma, rakam):
    """(deger, sapma) -> ("d", "s") ayni ondalik basamakta; sapma `rakam`
    anlamli rakamda. Sapmanin tam kismi `rakam`dan uzunsa None."""
    us = math.floor(math.log10(sapma))
    ondalik = max(rakam - 1 - us, 0)
    if round(sapma, ondalik) >= 10 ** (us + 1) and ondalik > 0:
        ondalik -= 1                      # 0.0096 -> 0.010 (3 rakam) olmasin
    if ondalik == 0 and _anlamli_rakam("%.0f" % sapma) > rakam:
        return None                       # 123 -> 3 rakam: olcekli yazilir
    return "%.*f" % (ondalik, deger), "%.*f" % (ondalik, sapma)


def belirsizlik_metni(deger, sapma, rakam=2, birim=""):
    """GUM §7.2.6 bicimi: sapma `rakam` anlamli basamaga, deger ayni ondalik
    basamaga yuvarlanir; "(1σ)" etiketi eklenir. sapma <= 0 ise deger %g.
    Sapma 10^rakam'dan buyukse ortak kuvvetle yazilir:
    (15432, 123) -> "(154.3 ± 1.2) × 10² (1σ)"; birim verilirse "... pcm (1σ)"."""
    ek = (" " + birim) if birim else ""
    if not sapma or sapma <= 0 or not math.isfinite(sapma):
        return "%g%s" % (deger, ek)
    cift = _cift_metni(deger, sapma, rakam)
    if cift is not None:
        return "%s ± %s%s (1σ)" % (cift[0], cift[1], ek)
    us = math.floor(math.log10(sapma))
    d, s = _cift_metni(deger / 10 ** us, sapma / 10 ** us, rakam)
    return "(%s ± %s) × 10%s%s (1σ)" % (d, s, str(us).translate(_UST_RAKAMLARI), ek)


def pcm_tanimi(tur="drho"):
    """Raporda pcm'nin hangi buyukluge uygulandigi (STANDARTLAR.md §3 K5-d)."""
    if tur == "dk":
        return _("pcm = Δk × 10⁵ (k farkı; reaktivite farkı değildir)")
    return _("pcm = Δρ × 10⁵, ρ = (k − 1)/k; iki durum arasında Δρ = (k₂ − k₁)/(k₁·k₂)")


def _anlamli_rakam(metin):
    return len(metin.replace(".", "").lstrip("0"))


def _ondalik(metin):
    return len(metin.split(".")[1]) if "." in metin else 0


def duz_metin(metin):
    """HTML etiketlerini ve varliklarini ayiklar."""
    return _html.unescape(re.sub(r"<[^>]+>", " ", metin or ""))


def _ciftleri_denetle(metin, rakam):
    """(cok_rakamli, ondalik_uyumsuz) ornek listeleri."""
    cok, uyumsuz = [], []
    for m in _CIFT.finditer(metin):
        deger, sapma, yuzde = m.group(1), m.group(2), m.group(3)
        if _anlamli_rakam(sapma) > rakam:
            cok.append(m.group(0).strip())
        elif not yuzde and _anlamli_rakam(sapma) and _ondalik(deger) != _ondalik(sapma):
            uyumsuz.append(m.group(0).strip())
    return cok, uyumsuz


def _ornek(liste):
    return ", ".join(liste[:_ORNEK]) + (" …" if len(liste) > _ORNEK else "")


def _k5_bulgulari(kural, metin, rakam):
    b = []
    ciftler = _CIFT.findall(metin)
    if ciftler and not _ETIKET.search(metin):
        b.append(kural.ihlal("uyari", _("'±' ile verilen değerlerin standart belirsizlik (1σ) "
                                        "olduğu yazılmamış; güven aralığı sanılabilir."),
                             _("Belirsizliğin 1σ standart belirsizlik olduğunu yazın."),
                             kimlik="K5-etiket", kaynak=GUM + " §7.2.2"))
    cok, uyumsuz = _ciftleri_denetle(metin, rakam)
    if cok:
        b.append(kural.ihlal("uyari", _("Belirsizlik %d anlamlı rakamdan fazla: %s")
                             % (rakam, _ornek(cok)), _("Örnek biçim: %s")
                             % belirsizlik_metni(1.18218, 0.00286), kimlik="K5-rakam",
                             kaynak=GUM + " §7.2.6"))
    if uyumsuz:
        b.append(kural.ihlal("uyari", _("Değer belirsizlikle aynı ondalık basamağa "
                                        "yuvarlanmamış: %s") % _ornek(uyumsuz),
                             kimlik="K5-yuvarlama", kaynak=GUM + " §7.2.6"))
    if _PCM.search(metin) and not (_PCM_BUYUKLUK.search(metin) and _PCM_OLCEK.search(metin)):
        b.append(kural.ihlal("uyari", _("'pcm' kullanılmış ama tanımı (Δk × 10⁵ mi Δρ × 10⁵ "
                                        "mi) yazılmamış."), pcm_tanimi(),
                             kimlik="K5-pcm", kaynak="BIPM SI Broşürü 9. baskı (tanımsal "
                                                     "terimler); STANDARTLAR.md §6 madde 15"))
    si = sorted(set(_SI_DISI.findall(metin)))
    if si:
        b.append(kural.ihlal("uyari", _("SI dışı birim: %s") % ", ".join(si),
                             _("SI birimlerini kullanın."), kimlik="K5-SI",
                             kaynak="BIPM SI Broşürü 9. baskı"))
    return b


def _rapor_metni(baglam):
    """(metin | None, kaynak adi). Once parametre, sonra kosu dizinindeki *.html."""
    if baglam.rapor_metni is not None:
        return baglam.rapor_metni, _("verilen rapor metni")
    d = baglam.kosu_dizini
    if not d or not os.path.isdir(d):
        return None, ""
    adaylar = sorted(a for a in os.listdir(d) if a.lower().endswith(".html"))
    if not adaylar:
        return None, ""
    yol = os.path.join(d, adaylar[0])
    with open(yol, encoding="utf-8", errors="replace") as f:
        return f.read(), adaylar[0]


def k5_belirsizlik(kural, baglam):
    try:
        metin, ad = _rapor_metni(baglam)
    except OSError as e:
        return [kural.ihlal("uyari", _("Rapor okunamadı: %s") % e)]
    if metin is None:
        return [kural.uygulanamadi(_("Denetlenecek rapor yok (koşu dizininde .html rapor "
                                     "bulunamadı)."),
                                   _("Raporu oluşturup denetimi yineleyin."))]
    rakam = baglam.esik("anlamli_rakam_azami", 2)
    bulgular = _k5_bulgulari(kural, duz_metin(metin), rakam)
    return bulgular or [kural.gecti(_("Belirsizlik ve birim bildirimi uygun (%s).") % ad)]


def _sicakliksiz(spec):
    return [m.get("ad", "?") for m in spec.get("malzemeler") or []
            if m.get("sicaklik") in (None, "")]


def k4_izlenebilirlik(kural, baglam):
    spec = baglam.spec
    if spec is None:
        return [kural.uygulanamadi(_("Model (spec) yok: veri izlenebilirliği "
                                     "denetlenemedi."))]
    from cekirdek import rapor
    alanlar, uyarilar = rapor.tekrarlanabilirlik(spec, baglam.kosu_dizini)
    bulgular = [kural.ihlal("uyari", u, _("Koşuyu bu uygulamayla yeniden çalıştırın; "
                                          "OpenMC sürümü ve kütüphane kosu.log'dan okunur."))
                for u in uyarilar]
    eksik = _sicakliksiz(spec)
    if eksik:
        bulgular.append(kural.ihlal("uyari", _("Sıcaklığı tanımsız malzeme: %s")
                                    % ", ".join(eksik), kimlik="K4-sicaklik"))
    if bulgular:
        return bulgular
    ozet = "; ".join("%s: %s" % (e, d) for e, d in alanlar[3:6])
    return [kural.gecti(_("İzlenebilirlik alanları tam (%s).") % ozet)]


KURALLAR = (
    Kural("K4", "D", N_("Veri izlenebilirliği"),
          "ANSI/ANS-10.4-2008 (R2021); NUREG/CR-6698 §2.3", STANDART, k4_izlenebilirlik),
    Kural("K5", "D", N_("Belirsizlik ve birim bildirimi"),
          GUM + " §7.2.2, §7.2.3, §7.2.6; BIPM SI Broşürü", STANDART, k5_belirsizlik),
)
