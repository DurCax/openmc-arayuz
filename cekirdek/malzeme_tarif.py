# -*- coding: utf-8 -*-
"""
================================================================================
 malzeme_tarif.py  --  Malzeme asistaninin tarifleri ve dogrulama adimi
================================================================================

 Asistan "Ne tasarliyorsun?" sorusuyla bir KATEGORI secer; her kategoride
 tarifler (UO2, borlu su, B4C ...) vardir. Bir tarif = sirali alanlar + bir
 uretici: uret(anahtar, param) yeni bir sema malzemesi dondurur. Hesaplar
 malzeme_hesap (bilesim, TD, karisim) ve malzeme_sogutucu (IF97, D2O, Na)
 modullerindedir; burada yalnizca baglanir.

 Katalogdaki (malzeme_kutup.KATALOG) malzemelerin tarifleri katalog islevini
 parametrik_uret ile cagirir: "kutup" kaydi tasir, Duzenle ayni formu acar.

 ALAN SINIRLARI GIRDI SINIRIDIR (yazim hatasini yakalar), fiziksel esik degil;
 fiziksel gecerlilik (IF97 bolgesi, D2O tablosu, Na korelasyonu, Pu vektoru)
 hesap modullerinde kaynakli olarak denetlenir.
================================================================================
"""

import os

from cekirdek import malzeme_hesap as mh
from cekirdek import malzeme_kutup as mk
from cekirdek import malzeme_sogutucu as ms
from cekirdek.ceviri import _, N_
from cekirdek.sema import malzeme, bilesen

KATEGORILER = (
    ("yakit", N_("Yakıt")), ("kilif", N_("Kılıf (zarf)")),
    ("moderator", N_("Moderatör / soğutucu")), ("emici", N_("Emici")),
    ("yapi", N_("Yapı malzemesi")), ("ozel", N_("Özel karışım")),
)

# PuO2 kuramsal yogunlugu [g/cm3] -- Carbajo, Yoder, Popov, Ivanov, "A review
# of the thermophysical properties of MOX and UO2 fuels", J. Nucl. Mater. 299
# (2001) 181, Bolum 2: 11.46 g/cm3.
PUO2_TD = 11.46
_YUZDE = 100.0

# M5 -- Zr-1Nb-O (Mardon vd., "Influence of composition and fabrication process
# on out-of-pile and in-pile properties of M5 alloy", ASTM STP 1354 (2000)
# 505): Nb %1.0, O %0.125 (agirlikca, nominal), Fe ~%0.03; Zr kalan.
# Yogunluk 6.50 g/cm3 (Zr-1Nb; saf Zr 6.52 g/cm3, CRC Handbook).
_M5 = (("Zr", 98.845), ("Nb", 1.0), ("O", 0.125), ("Fe", 0.03))
_M5_YOGUNLUK = 6.50
# SS304 -- SCALE 6.2 Standard Composition Library (ORNL/TM-2005/39, Tablo
# M8.2.4 "SS304"): agirlikca %, rho = 7.94 g/cm3.
_SS304 = (("C", 0.08), ("Si", 1.0), ("P", 0.045), ("Cr", 19.0), ("Mn", 2.0),
          ("Fe", 68.375), ("Ni", 9.5))
_SS304_YOGUNLUK = 7.94

# Ornek Pu vektoru (agirlikca %, Pu + Am-241) -- KULLANICININ DEGISTIRMESI
# BEKLENIR; olculmus vektor girilmeli. Toplam 100.
_ORNEK_PU = {"pu238": 2.0, "pu239": 55.0, "pu240": 25.0, "pu241": 10.0,
             "pu242": 8.0, "am241": 0.0}
_PU_ALANLARI = (("pu238", "Pu238"), ("pu239", "Pu239"), ("pu240", "Pu240"),
                ("pu241", "Pu241"), ("pu242", "Pu242"), ("am241", "Am241"))


# ============================================================================
# Alanlar
# ============================================================================

def _a(etiket, en_az, en_cok, varsayilan, ondalik=2, adim=1.0, sonek="", ipucu="",
       tur="sayi", secenekler=()):
    return {"etiket": etiket, "en_az": en_az, "en_cok": en_cok, "varsayilan": varsayilan,
            "ondalik": ondalik, "adim": adim, "sonek": sonek, "ipucu": ipucu, "tur": tur,
            "secenekler": secenekler}


_ALAN = {
    "zenginlik": _a(N_("U-235 ağırlıkça %"), 0.0, 98.0, 3.2, 3, 0.1, "%",
                    N_("U-234 ve U-236 ORNL/CSD/TM-244 bağıntısıyla eklenir (OpenMC ile aynı).")),
    "u_zenginlik": _a(N_("Taşıyıcı U'da U-235 %"), 0.0, 98.0, 0.25, 3, 0.05, "%"),
    "yogunluk_yolu": _a(N_("Yoğunluk"), None, None, "td", tur="secim",
                        secenekler=(("td", N_("kuramsal yoğunluk yüzdesinden")),
                                    ("dogrudan", N_("doğrudan g/cm³")))),
    "td_yuzde": _a(N_("Kuramsal yoğunluk (%TD)"), 1.0, 100.0, 95.0, 2, 0.5, "%",
                   N_("Gözeneklilik = 1 − %TD/100.")),
    "yogunluk": _a(N_("Yoğunluk"), 1.0e-4, 30.0, 10.40, 4, 0.01, "g/cm³"),
    "om": _a(N_("O/M oranı"), 1.5, 2.5, 2.0, 3, 0.01, "",
             N_("Oksijen / ağır metal atom oranı; stokiyometrik oksit 2.000.")),
    "sicaklik": _a(N_("Sıcaklık"), 250.0, 3000.0, 900.0, 2, 10.0, "K", tur="sicaklik"),
    "gd2o3_yuzde": _a(N_("Gd₂O₃ ağırlıkça %"), 0.0, 30.0, 8.0, 2, 0.5, "%"),
    "pu_hm_yuzde": _a(N_("Pu / ağır metal (ağırlıkça %)"), 0.1, 100.0, 7.0, 2, 0.5, "%"),
    "yas_yil": _a(N_("Ayrıştırmadan bu yana süre"), 0.0, 50.0, 0.0, 2, 0.5, N_("yıl"),
                  N_("Pu-241 (T½ = 14.29 y) Am-241'e bozunur; Bateman çözümü.")),
    "mo_yuzde": _a(N_("Mo ağırlıkça %"), 0.0, 20.0, 10.0, 2, 0.5, "%"),
    "basinc": _a(N_("Basınç"), 1.0e-3, 100.0, 0.101325, 4, 0.5, "MPa"),
    "bor_ppm": _a(N_("Çözünmüş bor (kütlece ppm)"), 0.0, 10000.0, 0.0, 1, 50.0, "ppm"),
    "b10_yuzde": _a(N_("B-10 atomca %"), 0.0, 100.0, None, 2, 1.0, "%",
                    N_("Boş bırakılırsa doğal bor (IUPAC 2013: %19.82)."), tur="dogal_ya_da"),
    "saflik": _a(N_("D₂O saflığı (mol %)"), 50.0, 100.0, 99.75, 3, 0.05, "%"),
}
for _ad, _nk in _PU_ALANLARI:
    _ALAN[_ad] = dict(_a(N_("%s (Pu+Am içinde ağırlıkça %%)"), 0.0, 100.0, _ORNEK_PU[_ad],
                         3, 0.5, "%", N_("Örnek değer; ölçülmüş vektörü girin.")),
                      etiket_arg=_nk)


# ============================================================================
# Ureticiler
# ============================================================================

def _yogunluk(p, td):
    if p.get("yogunluk_yolu", "td") == "dogrudan":
        return p["yogunluk"]
    return mh.yogunluk_td(td, td_orani=p["td_yuzde"] / _YUZDE)


def _uo2(p):
    rho = _yogunluk(p, mh.UO2_TD)
    return malzeme("uo2", [bilesen("U", 1.0, zenginlik=p["zenginlik"]), bilesen("O", p["om"])],
                   rho, sicaklik=p["sicaklik"], renk=mk.RENK["yakit"],
                   gorunen_ad="UO2 %%%.2f" % p["zenginlik"])


def _uo2_gd(p):
    g = p["gd2o3_yuzde"] / _YUZDE
    td = mh.karisim_td([1.0 - g, g], [mh.UO2_TD, mh.GD2O3_TD])
    return malzeme("uo2_gd", mh.uo2_gd2o3_bilesimi(p["zenginlik"], g),
                   mh.yogunluk_td(td, td_orani=p["td_yuzde"] / _YUZDE), sicaklik=p["sicaklik"],
                   renk=mk.RENK["yakit2"],
                   gorunen_ad="UO2 %%%.2f + %%%.1f Gd2O3" % (p["zenginlik"], p["gd2o3_yuzde"]))


def _mox_td(pu_hm, pu_vektor, u_zenginlik):
    """(U,Pu)O2 ideal karisim TD: UO2 ve PuO2 (+AmO2) oksit kutle kesirleriyle."""
    m_o2 = 2.0 * mh.ortalama_kutle(mh.dogal_vektor("O"))
    m_u = mh.ortalama_kutle(mh.wo_to_ao(mh.uranyum_vektoru(u_zenginlik)))
    w_uo2 = (1.0 - pu_hm) * (1.0 + m_o2 / m_u)
    w_puo2 = sum(pu_hm * w * (1.0 + m_o2 / mh.kutle(n)) for n, w in pu_vektor.items())
    toplam = w_uo2 + w_puo2
    return mh.karisim_td([w_uo2 / toplam, w_puo2 / toplam], [mh.UO2_TD, PUO2_TD])


def _mox(p):
    vektor = {nk: p[ad] / _YUZDE for ad, nk in _PU_ALANLARI if p[ad] > 0.0}
    if abs(sum(vektor.values()) - 1.0) > 1.0e-6:
        raise ValueError(_("Pu vektörünün toplamı %%100 olmalı (şu an %%%.3f)")
                         % (_YUZDE * sum(vektor.values())))
    if p["yas_yil"] > 0.0:
        vektor = mh.pu_yaslandir(vektor, p["yas_yil"])
    pu_hm = p["pu_hm_yuzde"] / _YUZDE
    td = _mox_td(pu_hm, vektor, p["u_zenginlik"])
    return malzeme("mox", mh.mox_bilesimi(pu_hm, vektor, p["u_zenginlik"], om=p["om"]),
                   mh.yogunluk_td(td, td_orani=p["td_yuzde"] / _YUZDE), sicaklik=p["sicaklik"],
                   renk=mk.RENK["yakit2"], gorunen_ad="MOX %%%.1f Pu" % p["pu_hm_yuzde"])


def _umo(p):
    mo = p["mo_yuzde"]
    return malzeme("umo", [bilesen("U", _YUZDE - mo, birim="wo", zenginlik=p["zenginlik"]),
                           bilesen("Mo", mo, birim="wo")],
                   p["yogunluk"], sicaklik=p["sicaklik"], renk=mk.RENK["yakit"],
                   gorunen_ad="U-%gMo %%%.2f" % (mo, p["zenginlik"]))


def _alasim(ad, gorunen, satirlar, renk):
    def uretici(p):
        return malzeme(ad, [bilesen(e, w, birim="wo") for e, w in satirlar], p["yogunluk"],
                       sicaklik=p["sicaklik"], renk=renk, gorunen_ad=gorunen)
    return uretici


def _h2o(p):
    # Cozunmus borun yogunluga etkisi ihmal edilir: yogunluk saf suyun IF97
    # degeridir (katalogdaki su() ile ayni yaklasim); bor yalnizca bilesime girer.
    rho = ms.su_yogunlugu(p["sicaklik"], p["basinc"])
    b10 = None if p.get("b10_yuzde") is None else p["b10_yuzde"] / _YUZDE
    if p["bor_ppm"] > 0.0:
        bil = mh.borlu_su_bilesimi(p["bor_ppm"], b10_ao=b10)
        gad = "H2O + %.0f ppm B" % p["bor_ppm"]
    else:
        bil, gad = [bilesen("H", 2.0), bilesen("O", 1.0)], "H2O"
    return malzeme("su", bil, rho, sicaklik=p["sicaklik"], sab=["c_H_in_H2O"],
                   renk=mk.RENK["sogutucu"],
                   gorunen_ad="%s %.1f K %.2f MPa" % (gad, p["sicaklik"], p["basinc"]))


def _d2o(p):
    x = p["saflik"] / _YUZDE
    rho = ms.agir_su_karisim_yogunlugu(p["sicaklik"], p["basinc"], x)
    return malzeme("agir_su", [bilesen("H2", 2.0 * x, tur="nuklid"),
                               bilesen("H1", 2.0 * (1.0 - x), tur="nuklid"), bilesen("O", 1.0)],
                   rho, sicaklik=p["sicaklik"], sab=["c_D_in_D2O"], renk=mk.RENK["sogutucu"],
                   gorunen_ad="D2O %%%.2f %.1f K" % (p["saflik"], p["sicaklik"]))


def _na(p):
    return malzeme("sodyum", [bilesen("Na", 1.0)], ms.sodyum_yogunlugu(p["sicaklik"]),
                   sicaklik=p["sicaklik"], renk=(200, 200, 120),
                   gorunen_ad="Na %.0f K" % p["sicaklik"])


def _b4c(p):
    rho = mh.yogunluk_td(mh.B4C_TD, td_orani=p["td_yuzde"] / _YUZDE)
    if p.get("b10_yuzde") is None:
        bil, gad = [bilesen("B", 4.0), bilesen("C", 1.0)], "B4C"
    else:
        f = p["b10_yuzde"] / _YUZDE
        bil = [bilesen("B10", 4.0 * f, tur="nuklid"), bilesen("B11", 4.0 * (1.0 - f), tur="nuklid"),
               bilesen("C", 1.0)]
        gad = "B4C %%%.1f B10" % p["b10_yuzde"]
    return malzeme("b4c", bil, rho, sicaklik=p["sicaklik"], renk=mk.RENK["emici"],
                   gorunen_ad=gad)


def _katalog(anahtar):
    """Katalog islevini parametrik uretimle cagiran uretici ('kutup' kaydi)."""
    def uretici(p):
        return mk.parametrik_uret(anahtar, dict(p))
    return uretici


def _katalog_alanlari(anahtar):
    v = mk.varsayilan_parametreler(anahtar)
    return [("yogunluk", {"varsayilan": v["yogunluk"]}), ("sicaklik", {"varsayilan": v["sicaklik"]})]


# ============================================================================
# Tarif kaydi: anahtar -> (kategoriler, etiket, aciklama, alanlar, uretici)
# ============================================================================

def _katalog_tarifi(anahtar, kategoriler):
    return (kategoriler, mk.KATALOG[anahtar][0], mk.KATALOG[anahtar][1],
            _katalog_alanlari(anahtar), _katalog(anahtar))


_SIC = ("sicaklik", {"varsayilan": 600.0})
_TARIFLER = {
    "uo2": (("yakit",), N_("UO₂ — uranyum dioksit"), N_("Zenginlik, %TD ve O/M'den seramik yakıt."),
            ["zenginlik", "yogunluk_yolu", "td_yuzde", "yogunluk", "om", "sicaklik"], _uo2),
    "uo2_gd": (("yakit",), N_("UO₂-Gd₂O₃ — gadolinyumlu yakıt"),
               N_("Yanabilir zehirli yakıt; kuramsal yoğunluk ideal karışımdan."),
               ["zenginlik", "gd2o3_yuzde", "td_yuzde", "sicaklik"], _uo2_gd),
    "mox": (("yakit",), N_("MOX — (U,Pu)O₂"),
            N_("Pu vektörü, Pu/HM ve Am-241 yaşlanmasıyla karışık oksit."),
            ["pu_hm_yuzde"] + [a for a, _n in _PU_ALANLARI]
            + ["u_zenginlik", "yas_yil", "td_yuzde", "om", "sicaklik"], _mox),
    "umo": (("yakit",), N_("U-Mo — metalik alaşım"), N_("Araştırma reaktörü metalik yakıtı."),
            ["zenginlik", "mo_yuzde", ("yogunluk", {"varsayilan": 17.0}), "sicaklik"], _umo),
    "m5": (("kilif",), N_("M5 — Zr-1Nb-O"), N_("PWR yakıt zarfı alaşımı (nominal bileşim)."),
           [("yogunluk", {"varsayilan": _M5_YOGUNLUK}), _SIC],
           _alasim("m5", "M5", _M5, mk.RENK["zarf"])),
    "ss304": (("kilif", "yapi"), N_("SS-304 paslanmaz çelik"),
              N_("SCALE standart bileşim kütüphanesi değerleri."),
              [("yogunluk", {"varsayilan": _SS304_YOGUNLUK}), _SIC],
              _alasim("ss304", "SS-304", _SS304, mk.RENK["yapisal"])),
    "h2o": (("moderator",), N_("Hafif su (H₂O), isteğe bağlı borlu"),
            N_("Yoğunluk IAPWS-IF97 ile sıcaklık ve basınçtan."),
            [("sicaklik", {"varsayilan": 293.6, "en_az": 273.15, "en_cok": 623.15}),
             "basinc", "bor_ppm", "b10_yuzde"], _h2o),
    "d2o": (("moderator",), N_("Ağır su (D₂O)"),
            N_("Yoğunluk IAPWS R16-17 (NIST) tablosundan; kalanı hafif su."),
            [("sicaklik", {"varsayilan": 340.0, "en_az": 280.0, "en_cok": 637.0}),
             ("basinc", {"varsayilan": 0.1, "en_az": 0.1, "en_cok": 20.0}), "saflik"], _d2o),
    "na": (("moderator",), N_("Sıvı sodyum (Na)"), N_("Yoğunluk Fink & Leibowitz (ANL/RE-95/2)."),
           [("sicaklik", {"varsayilan": 673.0, "en_az": 371.0, "en_cok": 2503.7})], _na),
    "b4c": (("emici",), N_("B₄C — bor karbür"), N_("B-10 zenginliği ve %TD ile emici."),
            ["b10_yuzde", ("td_yuzde", {"varsayilan": 100.0}), _SIC], _b4c),
}
for _k, _kat in (("zirkaloy4", ("kilif", "yapi")), ("fecral", ("kilif",)), ("ss316", ("kilif", "yapi")),
                 ("sic", ("kilif",)), ("al6061", ("yapi",)), ("grafit", ("moderator",)),
                 ("berilyum", ("moderator",)), ("agincd", ("emici",)), ("gd2o3", ("emici",))):
    _TARIFLER[_k] = _katalog_tarifi(_k, _kat)


# ============================================================================
# Genel arayuz
# ============================================================================

def tarifler(kategori):
    """Kategorideki tarif anahtarlari (kayit sirasiyla)."""
    return [k for k, t in _TARIFLER.items() if kategori in t[0]]


def etiket(anahtar):
    return _(_TARIFLER[anahtar][1])


def aciklama(anahtar):
    return _(_TARIFLER[anahtar][2])


def _tarif(anahtar):
    if anahtar not in _TARIFLER:
        raise ValueError(_("bilinmeyen tarif: %r") % (anahtar,))
    return _TARIFLER[anahtar]


def alanlar(anahtar):
    """Sirali alan tanimlari [{ad, etiket, en_az, en_cok, varsayilan, ...}] (etkin dilde)."""
    cikti = []
    for oge in _tarif(anahtar)[3]:
        ad, ezme = (oge, {}) if isinstance(oge, str) else oge
        a = dict(_ALAN[ad], **ezme)
        a["ad"] = ad
        for alan in ("etiket", "ipucu", "sonek"):
            a[alan] = _(a[alan]) if a[alan] else ""
        if a.get("etiket_arg"):
            a["etiket"] = a["etiket"] % a.pop("etiket_arg")
        a["secenekler"] = tuple((d, _(e)) for d, e in a["secenekler"])
        cikti.append(a)
    return cikti


def varsayilanlar(anahtar):
    return {a["ad"]: a["varsayilan"] for a in alanlar(anahtar)}


def _deger_dogrula(a, deger):
    if a["tur"] == "secim":
        if deger not in [d for d, _e in a["secenekler"]]:
            raise ValueError(_("%s: geçersiz seçim %r") % (a["etiket"], deger))
        return deger
    if deger is None and a["tur"] == "dogal_ya_da":
        return None
    try:
        x = float(deger)
    except (TypeError, ValueError):
        raise ValueError(_("%s: sayı olmalı (%r)") % (a["etiket"], deger)) from None
    if not a["en_az"] <= x <= a["en_cok"]:
        raise ValueError(_("%s: %g, %g–%g aralığında olmalı") % (a["etiket"], x, a["en_az"],
                                                                a["en_cok"]))
    return x


def uret(anahtar, param):
    """Tarifin malzemesi (yeni sozluk). Eksik parametre varsayilandir; aralik
    disi ya da fiziksel gecersiz deger ValueError (alan adiyla)."""
    tarif = _tarif(anahtar)
    p = {}
    for a in alanlar(anahtar):
        p[a["ad"]] = _deger_dogrula(a, (param or {}).get(a["ad"], a["varsayilan"]))
    return tarif[4](p)


def karisim_malzemesi(malzemeler, oranlar, tur, ad="karisim", sicaklik=293.6):
    """
    Malzemelerin wo/ao/vo karisimi -> nuklid (ao) satirli yeni malzeme, g/cm3.
    Ideal karisim (hacim toplanabilir; malzeme_hesap.karistir). S(a,b) tasinmaz:
    dogrulama adimi bilesime uyan tabloyu onerir.
    """
    bilesenler = [(mh.nuklid_atom_kesirleri(m["bilesim"]), mh.turetilmis(m)["yogunluk_gcm3"])
                  for m in malzemeler]
    vektor, rho = mh.karistir(bilesenler, list(oranlar), tur)
    bil = [bilesen(n, a, tur="nuklid") for n, a in sorted(vektor.items())]
    gad = " + ".join("%g %s %s" % (_YUZDE * f, tur, m.get("gorunen_ad") or m["ad"])
                     for f, m in zip(oranlar, malzemeler))
    return malzeme(ad, bil, rho, sicaklik=sicaklik, gorunen_ad=gad)


# ============================================================================
# Dogrulama adimi
# ============================================================================

def _nuklid_bulgulari(m, yol):
    """Kesit kutuphanesinde eksik nuklid / S(a,b) (OpenMC'nin acilim kuraliyla)."""
    import openmc
    from cekirdek import dogrula
    notron, termal = dogrula._kutuphane_icerigi()
    if notron is None:
        return [("uyari", _("cross_sections.xml okunamadı; eksik nüklid denetimi atlandı."))]
    eksik, bulgular = set(), []
    for s in m["bilesim"]:
        if s.get("tur") == "nuklid":
            eksik |= {s["isim"]} - notron
            continue
        try:
            acilim = openmc.Element(s["isim"]).expand(1.0, "ao", enrichment=s.get("zenginlik"),
                                                       cross_sections=yol)
            eksik |= {n for n, _a, _t in acilim} - notron
        except ValueError as e:              # OpenMC elementi kutuphaneyle acamiyor
            bulgular.append(("hata", _("%s elementi bu kütüphaneyle açılamıyor: %s") % (s["isim"], e)))
    if eksik:
        bulgular.append(("hata", _("Tesir kesiti kütüphanesinde olmayan nüklid: %s") % ", ".join(sorted(eksik))))
    for s in m.get("sab") or []:
        if s not in termal:
            bulgular.append(("hata", _("S(α,β) tablosu kütüphanede yok: %s") % s))
    return bulgular


def _sicaklik_bulgulari(m):
    from cekirdek import veri_bilgi
    nuklidler = sorted(mh.nuklid_atom_kesirleri(m["bilesim"]))
    alt, ust, kisit = veri_bilgi.malzeme_araligi(nuklidler, m.get("sab") or [])
    if alt is None:
        return [("bilgi", _("Kütüphanenin sıcaklık aralığı okunamadı; sıcaklık denetimi atlandı."))]
    t = m.get("sicaklik")
    if t is not None and not alt <= t <= ust:
        return [("uyari", _("Sıcaklık %.1f K, kütüphane aralığının (%.0f–%.0f K, %s) dışında; "
                            "koşu sıcaklık ayarına göre hata verebilir.") % (t, alt, ust, kisit))]
    return []


def dogrula_malzeme(m):
    """
    Asistanin dogrulama adimi: [(seviye, metin)], seviye hata|uyari|bilgi.
    Sema, turetilmis degerler, dogrula.malzeme_kontrol (bilesim + S(a,b)
    onerisi), kesit kutuphanesinde eksik nuklid ve sicaklik araligi. Kesit
    kutuphanesi yolu yoksa nuklid denetimi UYARIYLA atlanir.
    """
    from cekirdek import dogrula, malzeme_kullanici as mku
    sorun = mku.malzeme_sorunu(m)
    if sorun:
        return [("hata", sorun)]
    try:
        mh.turetilmis(m)
    except ValueError as e:
        return [("hata", str(e))]
    bulgular = [(b.seviye, b.mesaj + (" — " + b.oneri if b.oneri else ""))
                for b in dogrula.malzeme_kontrol({"malzemeler": [m]})]
    yol = os.environ.get("OPENMC_CROSS_SECTIONS")
    if not yol or not os.path.isfile(yol):
        return bulgular + [("uyari", _("Tesir kesiti kütüphanesi yolu tanımlı değil "
                                       "(OPENMC_CROSS_SECTIONS); eksik nüklid denetimi atlandı."))]
    return bulgular + _nuklid_bulgulari(m, yol) + _sicaklik_bulgulari(m)
