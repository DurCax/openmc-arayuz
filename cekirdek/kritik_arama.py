# -*- coding: utf-8 -*-
"""
================================================================================
 kritik_arama.py  --  Hedef k-eff'i veren parametre degerini bul
================================================================================

 "Kritik bor konsantrasyonu nedir?", "Hangi yansitici kalinliginda k=1 olur?",
 "Kritik yukseklik ne kadar?" sorularinin cevabi. tarama.py ile ayni parametre
 tanimlarini kullanir.

 YONTEM -- BELIRSIZLIGE DUYARLI SEKANT
   Monte Carlo'da k-eff bir olcumdur, belirsizligi vardir. Klasik bir kok
   bulucu |k - hedef| < 1e-6 gibi bir olcut kullanirsa GURULTU KOVALAR:
   sonsuza kadar iterasyon yapar ve sonunda rastgele bir noktada durur.

   Bu yuzden durma olcutu istatistige baglanmistir:
       |k - hedef| < tolerans * sigma_k        (varsayilan tolerans = 2.0)

   Tolerans 2 sigma secildi cunku kosucu.keff_yorumu() de bir sonucu
   "|k-1| <= 2 sigma" oldugunda KRITIK sayiyor. Daha sıkı bir arama olcutu
   (orn. 1 sigma) aramanin, sonuc panelinin kritik dedigi bir konfigurasyonu
   REDDETMESINE yol aciyordu -- iki yer ayni tanimi kullanmali.
   Yani "k, hedeften istatistiksel olarak ayirt edilemiyor" olur olmaz durulur.
   Daha sıkı bir cevap isteniyorsa cozum daha cok iterasyon degil, nokta
   basina DAHA COK PARCACIK'tir; kod bunu acikca soyler.

   YONTEM: PARANTEZ KORUMALI YANLIS KONUM (regula falsi) + IKIYE BOLME
     Ilk iki nokta aralik uclarindan alinir ve kokun iclerinde oldugu dogrulanir.
     Her adimda kiris (sekant) tahmini yapilir; tahmin parantezin disina duserse
     ya da DAHA ONCE OLCULEN bir noktaya denk gelirse IKIYE BOLMEYE gecilir.
     (Ilk surumde saf sekant kullaniliyordu ve ayni noktayi -- aralik ucunu --
     ust uste kosuyordu: 12 iterasyonun 2'si bosa gidiyordu.)

   KOKUN BELIRSIZLIGI
     k bir olcumdur; kokun konumu da belirsizdir. Yerel egimden
         delta_x = sigma_k / |dk/dx|
     olarak tahmin edilir ve sonucla birlikte raporlanir. Parantez genisligi
     bu belirsizligin altina indiginde daha fazla iterasyon BILGI KATMAZ --
     arama durur ve bunu soyler. Daha dar bir cevap icin cozum iterasyon degil,
     nokta basina DAHA COK PARCACIK'tir.

 KOK SARTI
   f(alt) ve f(ust) zit isaretli olmali (hedef aralikta olmali). Degilse
   arama yapilmaz; kullaniciya araligi genisletmesi soylenir -- sessizce
   ekstrapolasyon yapilmaz.
================================================================================
"""

import os

from cekirdek import kosucu, sema, tarama


class AramaSonucu(object):
    """Arama ciktisini tasiyan basit kap."""

    def __init__(self):
        self.adimlar = []          # [{"deger","keff","sapma"}...]
        self.cozum = None          # bulunan parametre degeri
        self.cozum_keff = None
        self.cozum_sapma = None
        self.basarili = False
        self.mesaj = ""
        self.cozum_belirsizlik = None     # kokun konum belirsizligi
        self.egim = None                  # yerel dk/dx

    def ozet(self):
        if not self.basarili:
            return "Arama basarisiz: %s" % self.mesaj
        bel = ("" if self.cozum_belirsizlik is None
               else " +/- %.4g" % self.cozum_belirsizlik)
        return ("Cozum: %s = %.6g%s   (k = %.5f +/- %.5f, %d iterasyon)"
                % (self.parametre_adi, self.cozum, bel, self.cozum_keff,
                   self.cozum_sapma, len(self.adimlar)))


def _nokta_kos(spec, tur, hedef, deger, dizin, is_parcacigi, taban):
    """Tek bir parametre degeri icin kosar; (k, sapma) dondurur."""
    nokta_spec, _uyari = tarama.parametre_uygula(spec, tur, hedef, deger, taban=taban)
    kosu = kosucu.calistir(nokta_spec, dizin, is_parcacigi=is_parcacigi)
    if not kosu["basarili"]:
        raise RuntimeError("kosu basarisiz (cikis kodu %d), log: %s"
                           % (kosu["cikis_kodu"], kosu["log"]))
    okunan = kosucu.sonuc_oku(kosu["statepoint"])
    return okunan["keff"]


def ara(spec, tur, hedef, alt, ust, kok_dizin, hedef_keff=1.0,
        tolerans_sigma=2.0, en_fazla=15, is_parcacigi=None,
        geri_cagir=None, dur_bayragi=None):
    """
    hedef_keff'i veren parametre degerini arar.

    tolerans_sigma : |k - hedef| bu kadar sigma icine girince durulur
    geri_cagir(i, sonuc_sozlugu) her iterasyonda cagrilir
    DONER AramaSonucu
    """
    sonuc = AramaSonucu()
    sonuc.parametre_adi = "%s(%s)" % (tur, hedef)
    adim_no = [0]

    def olc(deger):
        if dur_bayragi and dur_bayragi():
            raise KeyboardInterrupt("kullanici durdurdu")
        dizin = os.path.join(kok_dizin, "adim_%02d" % adim_no[0])
        k, s = _nokta_kos(spec, tur, hedef, deger, dizin, is_parcacigi, spec)
        kayit = {"deger": deger, "keff": k, "sapma": s,
                 "fark": k - hedef_keff, "sigma_orani": abs(k - hedef_keff) / s if s else None}
        sonuc.adimlar.append(kayit)
        if geri_cagir:
            geri_cagir(adim_no[0], kayit)
        adim_no[0] += 1
        return k, s

    try:
        k_alt, s_alt = olc(alt)
        k_ust, s_ust = olc(ust)
    except KeyboardInterrupt as e:
        sonuc.mesaj = str(e); return sonuc
    except Exception as e:
        sonuc.mesaj = str(e); return sonuc

    f_alt, f_ust = k_alt - hedef_keff, k_ust - hedef_keff

    # --- kok sarti: hedef aralikta mi? ---
    if f_alt * f_ust > 0:
        yon = "buyuk" if f_alt > 0 else "kucuk"
        sonuc.mesaj = (
            "Hedef k=%.5f verilen aralikta degil: her iki uc da hedeften %s "
            "(k(%g)=%.5f, k(%g)=%.5f). Araligi genisletin. "
            "Ekstrapolasyon yapilmadi -- sessizce yanlis cevap uretmemek icin."
            % (hedef_keff, yon, alt, k_alt, ust, k_ust))
        return sonuc

    # --- uclardan biri zaten yeterince yakinsa ---
    for deger, k, s in ((alt, k_alt, s_alt), (ust, k_ust, s_ust)):
        if abs(k - hedef_keff) <= tolerans_sigma * s:
            sonuc.cozum, sonuc.cozum_keff, sonuc.cozum_sapma = deger, k, s
            sonuc.basarili = True
            sonuc.mesaj = ("Aralik ucu zaten hedefte (|k-hedef| = %.1f sigma)."
                           % (abs(k - hedef_keff) / s if s else 0))
            return sonuc

    # --- parantez korumali iterasyon ---
    # Parantez: f(x_alt) ve f(x_ust) zit isaretli; kok daima aralarindadir.
    x_alt, f_a = (alt, f_alt) if f_alt < 0 else (ust, f_ust)
    x_ust, f_u = (ust, f_ust) if f_alt < 0 else (alt, f_alt)
    olculen = {alt: k_alt, ust: k_ust}

    def _yakin(x):
        """Bu deger daha once olculdu mu? (ayni noktayi tekrar kosma)"""
        genislik = abs(ust - alt)
        return any(abs(x - o) < 1e-6 * max(genislik, 1.0) for o in olculen)

    for _ in range(en_fazla):
        # kiris (yanlis konum) tahmini
        if abs(f_u - f_a) > 1e-12:
            x2 = x_alt + (x_ust - x_alt) * (-f_a) / (f_u - f_a)
        else:
            x2 = 0.5 * (x_alt + x_ust)
        # parantez disina dustuyse ya da tekrar ise ikiye bol
        ic = min(x_alt, x_ust) < x2 < max(x_alt, x_ust)
        if not ic or _yakin(x2):
            x2 = 0.5 * (x_alt + x_ust)
            if _yakin(x2):
                sonuc.mesaj = ("Parantez istatistiksel cozunurlugun altina indi; "
                               "daha fazla iterasyon bilgi katmaz.")
                break
        try:
            k2, s2 = olc(x2)
        except KeyboardInterrupt as e:
            sonuc.mesaj = str(e); return sonuc
        except Exception as e:
            sonuc.mesaj = str(e); return sonuc
        olculen[x2] = k2
        f2 = k2 - hedef_keff

        # yerel egim ve kokun belirsizligi
        yakin_uc = x_ust if abs(x_ust - x2) > 1e-12 else x_alt
        egim = ((k2 - olculen[yakin_uc]) / (x2 - yakin_uc)) if abs(x2 - yakin_uc) > 1e-12 else None
        if egim:
            sonuc.egim = egim
            sonuc.cozum_belirsizlik = abs(s2 / egim)

        if abs(f2) <= tolerans_sigma * s2:
            sonuc.cozum, sonuc.cozum_keff, sonuc.cozum_sapma = x2, k2, s2
            sonuc.basarili = True
            sonuc.mesaj = (
                "Yakinsadi: |k - hedef| = %.2f sigma (<= %.1f sigma olcutu)."
                % (abs(f2) / s2, tolerans_sigma))
            return sonuc

        # parantezi daralt
        if f2 < 0:
            x_alt, f_a = x2, f2
        else:
            x_ust, f_u = x2, f2

        # Parantez, kokun ISTATISTIKSEL belirsizliginden dar hale geldiyse dur:
        # bundan sonrasi gurultu kovalamaktir.
        if sonuc.cozum_belirsizlik and abs(x_ust - x_alt) <= sonuc.cozum_belirsizlik:
            sonuc.cozum = 0.5 * (x_alt + x_ust)
            sonuc.cozum_keff, sonuc.cozum_sapma = k2, s2
            sonuc.basarili = True
            sonuc.mesaj = (
                "Parantez genisligi (%.4g) kokun istatistiksel belirsizligine "
                "(%.4g) indi. Daha fazla iterasyon BILGI KATMAZ; daha dar bir "
                "cevap icin nokta basina parcacik sayisini artirin."
                % (abs(x_ust - x_alt), sonuc.cozum_belirsizlik))
            return sonuc

    if not sonuc.basarili and sonuc.adimlar:
        en_iyi = min(sonuc.adimlar, key=lambda a: abs(a["fark"]))
        sonuc.cozum = en_iyi["deger"]
        sonuc.cozum_keff = en_iyi["keff"]
        sonuc.cozum_sapma = en_iyi["sapma"]
        if not sonuc.mesaj:
            sonuc.mesaj = ("%d iterasyonda olcute ulasilamadi; en yakin nokta "
                           "raporlaniyor (|k-hedef| = %.2f sigma)."
                           % (en_fazla, abs(en_iyi["fark"]) / en_iyi["sapma"]))
    return sonuc


# ============================================================================
# TERMINAL GIRISI
# ============================================================================

def _terminal(argv):
    import sys
    if not argv or argv[0] in ("-h", "--yardim", "--help"):
        print(__doc__)
        print("\nKULLANIM")
        print("  python3 -m cekirdek.kritik_arama <spec.json> --tur <tur> "
              "--hedef <ad> --alt <a> --ust <b> [--keff 1.0] [-s N]")
        print("\nTARAMA TURLERI (tarama.py ile ayni)")
        for ad, (aciklama, _h, birim, _k) in sorted(tarama.TURLER.items()):
            print("  %-20s %-56s [%s]" % (ad, aciklama, birim))
        return 0

    spec_yolu = argv[0]
    p = {"tur": None, "hedef": None, "alt": None, "ust": None,
         "keff": "1.0", "s": None, "dizin": None, "sigma": "2.0"}
    i = 1
    while i < len(argv):
        a = argv[i].lstrip("-")
        if a in p:
            i += 1; p[a] = argv[i]
        else:
            print("bilinmeyen secenek: %s" % argv[i]); return 2
        i += 1
    if not all([p["tur"], p["alt"], p["ust"]]):
        print("--tur, --alt ve --ust zorunlu"); return 2

    spec = sema.yukle(spec_yolu)
    hedef = p["hedef"]
    if p["tur"] == "cubuk_yaricap" and hedef:
        ad, no = hedef.split(":"); hedef = (ad, int(no))
    dizin = p["dizin"] or os.path.join(
        os.path.dirname(os.path.abspath(spec_yolu)), "arama_%s" % p["tur"])
    birim = tarama.TURLER[p["tur"]][2]

    print("=" * 74)
    print(" KRITIK ARAMA: %s" % tarama.TURLER[p["tur"]][0])
    print(" hedef k = %s   |   aralik: %s - %s %s" % (p["keff"], p["alt"], p["ust"], birim))
    print("=" * 74)

    def ilerleme(i, kayit):
        print("  [%2d] %-12.6g %s  k = %.5f +/- %.5f   fark = %+8.5f (%.1f sigma)"
              % (i + 1, kayit["deger"], birim, kayit["keff"], kayit["sapma"],
                 kayit["fark"], kayit["sigma_orani"] or 0))

    s = ara(spec, p["tur"], hedef, float(p["alt"]), float(p["ust"]), dizin,
            hedef_keff=float(p["keff"]), tolerans_sigma=float(p["sigma"]),
            is_parcacigi=int(p["s"]) if p["s"] else None, geri_cagir=ilerleme)

    print("\n" + "=" * 74)
    if s.basarili:
        bel = ("" if s.cozum_belirsizlik is None
               else " +/- %.4g" % s.cozum_belirsizlik)
        print("  COZUM: %s = %.6g%s %s" % (p["tur"], s.cozum, bel, birim))
        print("         k = %.5f +/- %.5f" % (s.cozum_keff, s.cozum_sapma))
        if s.egim:
            print("         yerel egim dk/dx = %.4g / %s" % (s.egim, birim))
    else:
        print("  BULUNAMADI")
    print("  %s" % s.mesaj)
    print("=" * 74)
    return 0 if s.basarili else 1


if __name__ == "__main__":
    import sys
    sys.exit(_terminal(sys.argv[1:]))
