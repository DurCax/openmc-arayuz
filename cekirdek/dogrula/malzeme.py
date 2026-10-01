# -*- coding: utf-8 -*-
"""
 cekirdek/dogrula/malzeme.py  --  2. malzeme kontrolleri ve S(a,b) kurallari

 cekirdek/dogrula.py'den bolundu (davranis degismedi). Disaridan
 `from cekirdek import dogrula; dogrula.X` ile kullanilir.
"""

from cekirdek.sema import BOSLUK
from cekirdek.dogrula._ortak import Bulgu
from cekirdek.ceviri import _, N_


# ----------------------------------------------------------------------------
# S(a,b) beklentisi -- SAFLIK KURALLARIYLA
#
# Naif kural ("bilesimde C varsa grafittir") SS316 (agirlikca %0.5 C), B4C ve
# SiC icin yanlis alarm uretir. Dogru olcut, malzemenin gercekten o baglayici
# fazda olup olmadigidir; bu yuzden her kural bilesimin TAMAMINA bakar.
#
# Her giris: (uygun_element_kumesi, onerilen_sab, insan_okunur_ad)
#   bilesimdeki tum elementler kumenin icindeyse kural tetiklenir.
# ----------------------------------------------------------------------------
# (izin verilen elementler, ZORUNLU elementler, onerilen S(a,b), tanim)
#   Eslesme sarti: zorunlu <= malzeme <= izin verilen.
#   ZORUNLU kume sonradan eklendi. Once yalnizca "malzeme <= izin verilen"
#   bakiliyordu; {Zr} kumesi {H, Zr}'nin alt kumesi oldugu icin SAF ZIRKONYUM
#   "zirkonyum hidrur" sayiliyor ve kullaniciya c_H_in_ZrH eklemesi
#   oneriliyordu -- hidrojensiz bir malzemeye hidrojen S(a,b)'si, yani yanlis
#   fizik. Ayni mantikla B2O3 "borlu su" cikardi.
_SAB_KURALLARI = [
    ({"H", "O"},      {"H"},       "c_H_in_H2O",  N_("su (H₂O)")),
    ({"H", "O", "B"}, {"H"},       "c_H_in_H2O",  N_("borlu su")),
    ({"H", "Zr"},     {"H", "Zr"}, "c_H_in_ZrH",  N_("zirkonyum hidrür")),
    ({"H", "C"},      {"H", "C"},  "c_H_in_CH2",  N_("polietilen / plastik")),
    ({"C"},           {"C"},       "c_Graphite",  N_("grafit")),
    ({"Be"},          {"Be"},      "c_Be",        N_("berilyum")),
    ({"Be", "O"},     {"Be", "O"}, "c_Be_in_BeO", N_("berilyum oksit")),
    ({"D", "O"},      {"D"},       "c_D_in_D2O",  N_("ağır su (D₂O)")),
]


# Yogunlastirilmis faz esigi [g/cm3] -- bunun altinda gaz kabul edilir,
# termal sacilma baglama etkisi anlamsizdir.
_YOGUN_FAZ_ESIGI = 0.1


# ============================================================================
# 2. MALZEMELER
# ============================================================================

def malzeme_kontrol(spec):
    """Yogunluk, bilesim ve S(a,b) tutarliligi."""
    bulgular = []
    adlar = [m["ad"] for m in spec["malzemeler"]]

    for ad in set(adlar):
        if adlar.count(ad) > 1:
            bulgular.append(Bulgu("hata", "malzeme:%s" % ad,
                                  _("aynı ad %d kez tanımlanmış") % adlar.count(ad)))
    if BOSLUK in adlar:
        bulgular.append(Bulgu("hata", "malzemeler",
                              _("'%s' ayrılmış bir addır (Boş, madde yok); malzeme adı olarak kullanılamaz") % BOSLUK))

    for m in spec["malzemeler"]:
        yer = "malzeme:%s" % m["ad"]
        if not m.get("bilesim"):
            bulgular.append(Bulgu("hata", yer, _("bileşim boş")))
            continue
        yog = (m.get("yogunluk") or {}).get("deger")
        if yog is None:
            bulgular.append(Bulgu("hata", yer, _("yoğunluk verilmemiş")))
        elif yog <= 0:
            bulgular.append(Bulgu("hata", yer, _("yoğunluk sıfırdan büyük olmalı: %s") % yog))

        for b in m["bilesim"]:
            # Kurucu "nuklid" disindaki her turu element sayar ve birimi
            # OpenMC'ye aynen verir: "nuclide"/"atom" gibi bir yazim ancak
            # kosuda patlar ya da nuklidi element diye ekler.
            if b.get("tur", "element") not in ("element", "nuklid"):
                bulgular.append(Bulgu(
                    "hata", yer,
                    _("'%s' satırının türü geçersiz: %s") % (b.get("isim"), b.get("tur")),
                    _("Tür 'element' (doğal element) ya da 'nuklid' (izotop) olmalı.")))
            if b.get("birim", "ao") not in ("ao", "wo"):
                bulgular.append(Bulgu(
                    "hata", yer,
                    _("'%s' satırının birimi geçersiz: %s") % (b.get("isim"), b.get("birim")),
                    _("Birim 'ao' (atom oranı) ya da 'wo' (ağırlık oranı) olmalı.")))
            if b.get("miktar", 0) <= 0:
                bulgular.append(Bulgu("hata", yer,
                                      _("'%s' miktarı sıfırdan büyük olmalı: %s")
                                      % (b.get("isim"), b.get("miktar"))))
            z = b.get("zenginlik")
            # OpenMC zenginligi yalnizca U ELEMENTINE uygular: baska bir
            # elementte kosu sirasinda reddeder ("Unable to use enrichment for
            # element O which is not uranium"); nuklid satirinda kurucu onu
            # sessizce yok sayar. Ikisi de kosudan ONCE yakalanmali.
            if z is not None and b.get("tur", "element") == "nuklid":
                bulgular.append(Bulgu(
                    "hata", yer,
                    _("'%s' nüklid satırında zenginlik tanımlı — nüklidde zenginlik "
                    "yok sayılır") % b.get("isim"),
                    _("Zenginlik yalnızca U elementi satırında kullanılabilir. "
                    "İzotopları nüklid olarak giriyorsanız miktarları doğrudan verin.")))
            elif z is not None and b.get("isim") != "U":
                bulgular.append(Bulgu(
                    "hata", yer,
                    _("'%s' elementinde zenginlik tanımlı — zenginlik yalnızca U "
                    "elementinde kullanılabilir") % b.get("isim"),
                    _("OpenMC koşu sırasında reddeder (\"Unable to use enrichment for "
                    "element %s which is not uranium\"). Zenginliği U satırına "
                    "taşıyın ya da bu satırdan silin.") % b.get("isim")))
            if z is not None and not (0.0 < z < 100.0):
                bulgular.append(Bulgu("hata", yer,
                                      _("'%s' zenginliği %%0–100 aralığında olmalı: %s")
                                      % (b["isim"], z)))
            elif z is not None and b.get("isim") == "U" and z > 5.0:
                bulgular.append(Bulgu(
                    "uyari", yer,
                    _("U zenginliği %%%.2f — OpenMC'nin zenginlik kısayolu U234/U235 "
                    "kütle oranını sabit 0.008 varsayar; bu yalnızca düşük "
                    "zenginliklerde geçerlidir") % z,
                    _("Bileşimi nüklid bazında verin (U234/U235/U238) ya da sonucun "
                    "U234'e duyarlılığını kabul edin.")))

        # --- S(a,b) unutulmus mu? termal spektrumun en klasik hatasi ---
        bulgular += _sab_kontrol(m, yer)
    return bulgular


def _element_kumesi(malzeme):
    """
    Bilesimdeki element sembollerini dondurur. Nuklidler element sembolune
    indirgenir (U235 -> U, H2 -> D cunku agir su ayri bir kuraldir).
    """
    kume = set()
    for b in malzeme.get("bilesim", []):
        isim = b.get("isim", "")
        if b.get("tur") == "nuklid":
            if isim in ("H2", "D"):
                kume.add("D")
                continue
            # "U235" -> "U",  "Pu239" -> "Pu"
            sembol = "".join(ch for ch in isim if ch.isalpha())
            kume.add(sembol)
        else:
            kume.add(isim)
    return kume


def _sab_kontrol(malzeme, yer):
    """
    Yogunlastirilmis fazdaki moderatorlerde S(a,b) eksikligini arar.

    Kural bilesimin TAMAMINA bakar: SS316 (%0.5 C), B4C ve SiC karbon icerir
    ama grafit degildir; bu yuzden "C var -> grafit" gibi bir kisayol
    kullanilmaz.
    """
    if malzeme.get("sab"):
        return []
    yog = (malzeme.get("yogunluk") or {}).get("deger") or 0.0
    if yog <= _YOGUN_FAZ_ESIGI:
        return []          # gaz -- baglama etkisi yok
    elemanlar = _element_kumesi(malzeme)
    if not elemanlar:
        return []
    # Birden fazla kural eslesebilir (saf karbon hem {"C"} hem {"H","C"}
    # kumesinin alt kumesidir). EN DAR kural kazanir -- yoksa grafit
    # "polietilen" diye raporlanir.
    eslesenler = [(len(uygun), onerilen, tanim)
                  for uygun, zorunlu, onerilen, tanim in _SAB_KURALLARI
                  if zorunlu <= elemanlar <= uygun]
    if eslesenler:
        _uzaklik, onerilen, tanim = min(eslesenler)
        return [Bulgu(
            "uyari", yer,
            _("%s görünümünde ama termal saçılma verisi (S(α,β)) eklenmemiş") % _(tanim),
            _("Termal spektrumda k'yi yüzde mertebesinde kaydırır. Malzemeler "
            "sekmesinde S(α,β) olarak %s ekleyin.") % onerilen)]
    # Kurala uymayan ama hidrojen iceren yogun malzeme -- yine de uyar
    if "H" in elemanlar:
        return [Bulgu(
            "uyari", yer,
            _("yoğun fazda hidrojen var ama termal saçılma verisi (S(α,β)) eklenmemiş"),
            _("Hidrojenin bağlı olduğu faza uygun bir S(α,β) seçin "
            "(ör. c_H_in_H2O, c_H_in_ZrH, c_H_in_CH2)."))]
    return []
