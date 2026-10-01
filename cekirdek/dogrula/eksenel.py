# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/eksenel.py  --  eksenel katman kontrolleri

 cekirdek/dogrula.py'den bolundu (davranis degismedi). Disaridan
 `from cekirdek import dogrula; dogrula.X` ile kullanilir.
"""

from cekirdek.sema import BOSLUK, malzeme_bul, cubuk_bul, plaka_bul, demet_bul
from cekirdek import geometri, sema
from cekirdek.geometri import eksenel as _geo_eks
from cekirdek.dogrula._ortak import Bulgu, _kor_turu_adi
from cekirdek.gunluk import kaydedici, uyar_bir_kez
from cekirdek.ceviri import _

_log = kaydedici(__name__)


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
    if sema.agac_modu(spec):
        return _agac_eksenel_kontrol(spec)
    bulgular = []
    kor = spec["kor"]
    eks = kor.get("eksenel") or {}
    if not eks.get("var"):
        return bulgular

    tur = kor.get("tur")
    if tur not in sema.EKSENEL_DESTEKLI:
        bulgular.append(Bulgu(
            "hata", "kor",
            _("eksenel katmanlar '%s' kor türünde desteklenmiyor") % _kor_turu_adi(tur),
            _("Destekleyen türler: %s. Küresel düzenekte eksen kavramı yoktur; "
            "orada katmanı eş merkezli kabuklarla kurun.")
            % ", ".join(_kor_turu_adi(x) for x in sema.EKSENEL_DESTEKLI)))
        return bulgular

    katmanlar = eks.get("bolgeler") or []
    if not katmanlar:
        bulgular.append(Bulgu("hata", "kor",
                              _("eksenel katmanlar açık ama hiç katman tanımlı değil")))
        return bulgular

    adlar = set()
    for i, b in enumerate(katmanlar):
        yer = "kor/katman %d (%s)" % (i + 1, b.get("ad") or _("adsız"))
        h = b.get("yukseklik")
        if not h or float(h) <= 0:
            bulgular.append(Bulgu("hata", yer, _("katman yüksekliği sıfırdan büyük olmalı")))
        ad = b.get("ad") or ""
        if ad and ad in adlar:
            bulgular.append(Bulgu("uyari", yer,
                                  _("aynı ad birden fazla katmanda kullanılmış: '%s'") % ad))
        adlar.add(ad)

        dolgu = b.get("dolgu")
        if dolgu and not _ad_var(spec, dolgu):
            bulgular.append(Bulgu(
                "hata", yer, _("tanımsız dolgu adı: '%s'") % dolgu,
                _("Dolgu bir çubuk, plaka elemanı, demet ya da malzeme adı olmalı.")))

        anahtar = b.get("anahtar") or {}
        # Katmana ozel harf eslemesi haritali her tam korda kurulur (kare:
        # kurucu._kare_kafes_kur, altigen: altigen_kor.konum_dolgu_adlari).
        if anahtar and tur not in sema.HARITALI_KORLAR:
            bulgular.append(Bulgu(
                "hata", yer,
                _("katmana özel harf eşlemesi yalnızca kare haritalı tam korda ya da "
                  "altıgen haritalı tam korda kullanılabilir")))
        for harf, hedef in anahtar.items():
            if not any(harf in satir for satir in (kor.get("harita") or [])):
                bulgular.append(Bulgu(
                    "uyari", yer,
                    _("'%s' harfi kor haritasında hiç geçmiyor") % harf))
            if not _ad_var(spec, hedef):
                bulgular.append(Bulgu("hata", yer,
                                      _("tanımsız demet/malzeme adı: '%s'") % hedef))

    if kor.get("yukseklik"):
        toplam = sema.kor_yuksekligi(kor)
        bulgular.append(Bulgu(
            "bilgi", "kor",
            _("eksenel katmanlar açıkken yükseklik alanı (%g cm) yok sayılır; "
            "geçerli yükseklik katmanların toplamıdır (%g cm)")
            % (float(kor["yukseklik"]), toplam or 0.0)))

    # --- fisil katman var mi ---
    if spec["ayarlar"].get("mod", "eigenvalue") == "eigenvalue":
        try:
            aralik = geometri.aktif_aralik(spec)
            toplam = sema.kor_yuksekligi(kor)
            fisil_var = any(
                _geo_eks.fisil_mi(spec, x)
                for b in katmanlar for x in sema.katman_adaylari(kor, b))
        except Exception:
            uyar_bir_kez(_log, "eksenel denetim: aktif aralik hesaplanamadi")
            aralik, toplam, fisil_var = None, None, True
        bulgular += _aktif_bulgulari(aralik, toplam, fisil_var)
    return bulgular + _ortak_bulgular(spec)


def _aktif_bulgulari(aralik, toplam, fisil_var):
    """Fisil katman yoksa HATA; aktif aralik toplamdan kisaysa BILGI."""
    if not fisil_var:
        return [Bulgu(
            "hata", "kor",
            _("hiçbir eksenel katmanda fisil malzeme yok — özdeğer koşusu "
            "başlangıç kaynağı bulamaz"))]
    if aralik and toplam and aralik[1] - aralik[0] < toplam:
        return [Bulgu(
            "bilgi", "kor",
            _("aktif yakıt yüksekliği %g cm / toplam %g cm "
            "(z = %g … %g)") % (aralik[1] - aralik[0], toplam, aralik[0], aralik[1]),
            _("Başlangıç kaynağı kutusu ve kontrol çubuğu daldırması bu "
            "fisil aralığa göre tanımlıdır. Güç dağılımının eksenel ağı "
            "ise hedef çubuğun bulunduğu aralığa göre — ikisi aynı "
            "olmak zorunda değil (doğal uranyum örtü fisildir ama "
            "içinde yakıt çubuğu yoktur)."))]
    return []


def _ortak_bulgular(spec):
    """Sablon ve agac modunda ayni: mutlak guc payi uyarisi ve kontrol cubugu notu.

    Mutlak guc normalizasyonu uyarisi: distribcell yalnizca HEDEF cubugu
    kapsar, ama toplam_guc tum modelin gucudur. Katmanlamada fisil ama
    hedef cubugu icermeyen katmanlar (blanket) varsa onlarin gucu de hedef
    cubuklara paylastirilmis olur ve W/cm YUKSEK cikar."""
    bulgular = []
    g = spec.get("guc_dagilimi") or {}
    adlar = list(dict.fromkeys(h["cubuk"] for h in sema.guc_hedefleri(g) if h["cubuk"]))
    if g.get("var") and g.get("toplam_guc") and adlar:
        try:
            ar = geometri.aktif_aralik(spec)
            cr = geometri.hedef_araligi(spec, adlar)
        except Exception:
            uyar_bir_kez(_log, "eksenel denetim: cubuk araligi hesaplanamadi")
            ar = cr = None
        if ar and cr and (cr[1] - cr[0]) < (ar[1] - ar[0]) - 1e-9:
            bulgular.append(Bulgu(
                "uyari", "guc_dagilimi",
                _("fisil aralık %g cm ama '%s' çubuğu yalnızca %g cm boyunca var")
                % (ar[1] - ar[0], "', '".join(adlar), cr[1] - cr[0]),
                _("Güç dağılımı yalnızca bu çubuğu sayar; toplam güç ise tüm "
                "modelin gücüdür. Aradaki fisil katmanların (örtü gibi) gücü "
                "de bu çubuklara paylaştırılmış olur ve W/cm olduğundan yüksek "
                "çıkar. Mutlak sayıları kullanacaksanız toplam gücü yalnızca bu "
                "çubukların ürettiği güç olarak girin.")))

    if any(c.get("tur") == "kontrol" for c in spec.get("cubuklar", [])):
        bulgular.append(Bulgu(
            "bilgi", "kor",
            _("kontrol çubuğu daldırması aktif yakıt aralığında ölçülür"),
            _("%0 = uç aktif bölgenin tepesinde, %100 = dibinde; modelin toplam "
            "yüksekliği değil.")))
    return bulgular


def _agac_eksenel_kontrol(spec):
    """
    Gelismis (agac) mod: yigin yapisi yapisal denetimde (geometri.yapisal_denetim,
    dogrula/agac); burada sablonla ayni fizik kurallari agactaki eksenel
    dilimlerden: fisil katman yoksa HATA, aktif aralik BILGI, guc payi UYARI.
    """
    from cekirdek.geometri.eksenel import eksenel_dilimler
    m = geometri.model(spec)
    dilim = eksenel_dilimler(m)
    if not dilim:
        return []
    bulgular = []
    if spec["ayarlar"].get("mod", "eigenvalue") == "eigenvalue":
        fisil_var = any(_geo_eks.dugum_iceriyor(m, ic, _geo_eks._fisil_sinama)
                        for _z0, _z1, _ad, ic in dilim)
        bulgular += _aktif_bulgulari(geometri.aktif_aralik(spec), geometri.yukseklik(m),
                                     fisil_var)
    return bulgular + _ortak_bulgular(spec)


def _ad_var(spec, ad):
    """Ad bir cubuk / plaka / demet / malzeme (ya da bosluk) mu?"""
    return (ad == BOSLUK
            or malzeme_bul(spec, ad) is not None
            or cubuk_bul(spec, ad) is not None
            or plaka_bul(spec, ad) is not None
            or demet_bul(spec, ad) is not None)
