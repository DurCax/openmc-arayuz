# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/eksenel.py  --  eksenel katman kontrolleri

 cekirdek/dogrula.py'den bolundu (davranis degismedi). Disaridan
 `from cekirdek import dogrula; dogrula.X` ile kullanilir.
"""

from cekirdek.sema import BOSLUK, malzeme_bul, cubuk_bul, plaka_bul, demet_bul
from cekirdek import kurucu, sema
from cekirdek.dogrula._ortak import Bulgu, _kor_turu_adi


# ============================================================================
# 4. AYARLAR
# ============================================================================

def eksenel_kontrol(spec):
    """
    Eksenel katmanlama tutarli mi?

    Katmanlamanin sessiz hatalari:
      * hicbir katmanda fisil malzeme yok -> ozdeger kosusu kaynak bulamaz
      * katman dolgusu tanimsiz bir ad -> kurulumda KeyError, kosudan once yakala
      * "yukseklik" ile katman toplami farkli -> hangisi gecerli belirsiz kalir
    """
    bulgular = []
    kor = spec["kor"]
    eks = kor.get("eksenel") or {}
    if not eks.get("var"):
        return bulgular

    tur = kor.get("tur")
    if tur not in sema.EKSENEL_DESTEKLI:
        bulgular.append(Bulgu(
            "hata", "kor",
            "eksenel katmanlar '%s' kor türünde desteklenmiyor" % _kor_turu_adi(tur),
            "Destekleyen türler: %s. Küresel düzenekte eksen kavramı yoktur; "
            "orada katmanı eş merkezli kabuklarla kurun."
            % ", ".join(_kor_turu_adi(x) for x in sema.EKSENEL_DESTEKLI)))
        return bulgular

    katmanlar = eks.get("bolgeler") or []
    if not katmanlar:
        bulgular.append(Bulgu("hata", "kor",
                              "eksenel katmanlar açık ama hiç katman tanımlı değil"))
        return bulgular

    adlar = set()
    for i, b in enumerate(katmanlar):
        yer = "kor/katman %d (%s)" % (i + 1, b.get("ad") or "adsız")
        h = b.get("yukseklik")
        if not h or float(h) <= 0:
            bulgular.append(Bulgu("hata", yer, "katman yüksekliği sıfırdan büyük olmalı"))
        ad = b.get("ad") or ""
        if ad and ad in adlar:
            bulgular.append(Bulgu("uyari", yer,
                                  "aynı ad birden fazla katmanda kullanılmış: '%s'" % ad))
        adlar.add(ad)

        dolgu = b.get("dolgu")
        if dolgu and not _ad_var(spec, dolgu):
            bulgular.append(Bulgu(
                "hata", yer, "tanımsız dolgu adı: '%s'" % dolgu,
                "Dolgu bir çubuk, plaka elemanı, demet ya da malzeme adı olmalı."))

        anahtar = b.get("anahtar") or {}
        if anahtar and tur != "kare_kafes":
            bulgular.append(Bulgu(
                "hata", yer,
                "katmana özel harf eşlemesi yalnızca kare haritalı tam korda kullanılabilir"))
        for harf, hedef in anahtar.items():
            if not any(harf in satir for satir in (kor.get("harita") or [])):
                bulgular.append(Bulgu(
                    "uyari", yer,
                    "'%s' harfi kor haritasında hiç geçmiyor" % harf))
            if not _ad_var(spec, hedef):
                bulgular.append(Bulgu("hata", yer,
                                      "tanımsız demet/malzeme adı: '%s'" % hedef))

    if kor.get("yukseklik"):
        toplam = sema.kor_yuksekligi(kor)
        bulgular.append(Bulgu(
            "bilgi", "kor",
            "eksenel katmanlar açıkken yükseklik alanı (%g cm) yok sayılır; "
            "geçerli yükseklik katmanların toplamıdır (%g cm)"
            % (float(kor["yukseklik"]), toplam or 0.0)))

    # --- fisil katman var mi ---
    if spec["ayarlar"].get("mod", "eigenvalue") == "eigenvalue":
        try:
            aralik = kurucu.aktif_eksenel_aralik(spec)
            toplam = sema.kor_yuksekligi(kor)
            fisil_var = any(
                kurucu._spec_fisil_mi(spec, x)
                for b in katmanlar for x in sema.katman_adaylari(kor, b))
        except Exception:
            aralik, toplam, fisil_var = None, None, True
        if not fisil_var:
            bulgular.append(Bulgu(
                "hata", "kor",
                "hiçbir eksenel katmanda fisil malzeme yok — özdeğer koşusu "
                "başlangıç kaynağı bulamaz"))
        elif aralik and toplam:
            aktif = aralik[1] - aralik[0]
            if aktif < toplam:
                bulgular.append(Bulgu(
                    "bilgi", "kor",
                    "aktif yakıt yüksekliği %g cm / toplam %g cm "
                    "(z = %g … %g)" % (aktif, toplam, aralik[0], aralik[1]),
                    "Başlangıç kaynağı kutusu ve kontrol çubuğu daldırması bu "
                    "fisil aralığa göre tanımlıdır. Güç dağılımının eksenel ağı "
                    "ise hedef çubuğun bulunduğu aralığa göre — ikisi aynı "
                    "olmak zorunda değil (doğal uranyum örtü fisildir ama "
                    "içinde yakıt çubuğu yoktur)."))

    # Mutlak guc normalizasyonu uyarisi: distribcell yalnizca HEDEF cubugu
    # kapsar, ama toplam_guc tum modelin gucudur. Katmanlamada fisil ama
    # hedef cubugu icermeyen katmanlar (blanket) varsa onlarin gucu de hedef
    # cubuklara paylastirilmis olur ve W/cm YUKSEK cikar.
    g = spec.get("guc_dagilimi") or {}
    if g.get("var") and g.get("toplam_guc") and g.get("cubuk"):
        try:
            ar = kurucu.aktif_eksenel_aralik(spec)
            cr = kurucu.cubuk_eksenel_aralik(spec, g["cubuk"])
        except Exception:
            ar = cr = None
        if ar and cr and (cr[1] - cr[0]) < (ar[1] - ar[0]) - 1e-9:
            bulgular.append(Bulgu(
                "uyari", "guc_dagilimi",
                "fisil aralık %g cm ama '%s' çubuğu yalnızca %g cm boyunca var"
                % (ar[1] - ar[0], g["cubuk"], cr[1] - cr[0]),
                "Güç dağılımı yalnızca bu çubuğu sayar; toplam güç ise tüm "
                "modelin gücüdür. Aradaki fisil katmanların (örtü gibi) gücü "
                "de bu çubuklara paylaştırılmış olur ve W/cm olduğundan yüksek "
                "çıkar. Mutlak sayıları kullanacaksanız toplam gücü yalnızca bu "
                "çubukların ürettiği güç olarak girin."))

    if any(c.get("tur") == "kontrol" for c in spec.get("cubuklar", [])):
        bulgular.append(Bulgu(
            "bilgi", "kor",
            "kontrol çubuğu daldırması aktif yakıt aralığında ölçülür",
            "%0 = uç aktif bölgenin tepesinde, %100 = dibinde; modelin toplam "
            "yüksekliği değil."))
    return bulgular


def _ad_var(spec, ad):
    """Ad bir cubuk / plaka / demet / malzeme (ya da bosluk) mu?"""
    return (ad == BOSLUK
            or malzeme_bul(spec, ad) is not None
            or cubuk_bul(spec, ad) is not None
            or plaka_bul(spec, ad) is not None
            or demet_bul(spec, ad) is not None)
