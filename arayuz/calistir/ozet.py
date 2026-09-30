# -*- coding: utf-8 -*-
"""
ozet.py -- Sonuc ozetinin METIN satirlari (Qt'siz, saf islevler).

Calistir sayfasindaki "Sonuç" kartinin ve "Tam sonuç metni"nin govdesi burada
uretilir: sabit kaynak ozeti, ozdeger ozeti, guc dagilimi satirlari ve tally
tablolari. Hicbir islev aldigi sozlugu DEGISTIRMEZ; hepsi yeni liste dondurur.

Kaynak: kosucu.sonuc_oku() ciktisi (s) ve spec["ayarlar"]["kaynak"] (k_tanim).
"""

from cekirdek import guc as _guc
from cekirdek import kaynak as _kaynak
from cekirdek import kosucu
from cekirdek.ceviri import _


def sabit_ozeti(s, k_tanim):
    """Sabit kaynak kosusunun ozet satirlari (k-eff tanimsizdir)."""
    kuvvet = float((k_tanim or {}).get("kuvvet") or 1.0)
    satirlar = [
        "mod      = sabit kaynak (k-eff tanımsız)",
        "kaynak   = %s" % _kaynak.ozet(k_tanim or {}),
        "şiddet   = %.4g parçacık/s" % kuvvet,
        "çevrim   = %d, %d parçacık/çevrim" % (s["cevrim"], s["parcacik"]),
        "Sonuçlar akı ve tepkime hızlarıdır; doz hesaplanmaz. Akı hacim-"
        "integrallidir (n·cm/s): ortalama akı [n/cm²/s] için bölgenin "
        "hacmine bölün.",
    ]
    # OLCULDU (kosucu.py): OpenMC sabit kaynak tally'lerini kaynak siddetiyle
    # ZATEN carpar; "siddetle carpin" demek cift sayim olurdu.
    if kuvvet == 1.0:
        satirlar.append("NOT: tally değerleri kaynak parçacığı başınadır "
                        "(şiddet 1). Mutlak birim için şiddeti girin.")
    else:
        satirlar.append("Not: tally değerleri mutlak birimdedir — OpenMC "
                        "şiddeti zaten uygulamıştır, tekrar çarpmayın.")
    return satirlar


def kaynak_satiri(s):
    """(satir, yakinsadi) -- Shannon entropisiyle kaynak yakinsamasi."""
    if s.get("entropi"):
        yakinsadi, mesaj = kosucu.entropi_yakinsama(s["entropi"], s.get("pasif") or 0)
        isaret = {True: "[tamam]", False: "[uyarı]", None: "[  ?  ]"}[yakinsadi]
        return "kaynak   = %s %s" % (isaret, mesaj), yakinsadi
    if s.get("entropi_hata"):
        return ("kaynak   = [  ?  ] " + _("Shannon entropisi okunamadı: %s")
                % s["entropi_hata"]), None
    return ("kaynak   = [  ?  ] Shannon entropisi kapalı — "
            "kaynak yakınsaması doğrulanamıyor"), None


def ozdeger_ozeti(s):
    """(satirlar, yakinsadi) -- cevrim, kaynak yakinsamasi ve kinetik."""
    satirlar = ["çevrim   = %d (%d pasif), %d parçacık/çevrim"
                % (s["cevrim"], s["pasif"], s["parcacik"])]
    satir, yakinsadi = kaynak_satiri(s)
    satirlar.append(satir)
    kin = s.get("kinetik")
    if kin:
        satirlar.append("β_eff    = %.1f ± %.1f pcm   (reaktivite birimi: 1 $ = β_eff)"
                        % (kin["beta_eff"] * 1e5, kin["beta_eff_sapma"] * 1e5))
        satirlar.append("Λ        = %-22s (nötron üretim zamanı)"
                        % kosucu.lambda_metni(kin["lambda"], kin["lambda_sapma"]))
    return satirlar, yakinsadi


def guc_ozeti(s):
    """Tepe faktorleri, en sicak cubuk ve toplamin korunumu satirlari."""
    g = s.get("guc") or {}
    gf = g.get("faktorler")
    if not gf:
        return ["güç dağılımı okunamadı: %s" % s["guc_hata"]] if s.get("guc_hata") else []
    zayif = (gf.get("yanlilik_orani") or 0.0) > 0.3
    satirlar = ["F_ΔH     = %.4f   (en yüksek çubuk gücü / ortalama)%s"
                % (gf["F_dH"], "\n           ⚠ istatistik zayıf: bu değer yukarı "
                   "yanlı, güvenilir F_ΔH için Normal ya da Hassas hassasiyetle "
                   "koşun" if zayif else "")]
    if gf["F_q"]:
        satirlar.append("F_q      = %.4f   (en yüksek yerel güç yoğunluğu / ortalama)"
                        % gf["F_q"])
    else:
        satirlar.append("F_q      = tanımsız (model 2B)")
    satirlar.append("en sıcak çubuk: %s%s"
                    % (_guc.konum_metni(gf["sicak_cubuk"], gf.get("kafes_turu"),
                                        gf.get("kafes_turleri")),
                       (", dilim %d" % (gf["sicak_dilim"][1] + 1))
                       if gf["sicak_dilim"] else ""))
    return satirlar + list(kosucu.korunum_satirlari(g))


def tally_metinleri(s, sabit, kuvvet=1.0):
    """Her tally icin bicimlenmis tablo (aralarinda bos satir)."""
    satirlar = []
    for ad, df in s["tallyler"].items():
        satirlar.append(kosucu.tally_metni(ad, df, s.get("malzeme_adlari"), sabit,
                                           kuvvet))
        satirlar.append("")
    return satirlar
