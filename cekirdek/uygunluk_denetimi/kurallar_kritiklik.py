# -*- coding: utf-8 -*-
"""
uygunluk_denetimi/kurallar_kritiklik.py -- Profil B: kritiklik guvenligi.

Yontem kaynagi NUREG/CR-6698 (STANDARTLAR.md §4). Yanlilik ve USL'yi S-3
(cekirdek/vv/) HESAPLAR ve vv_arayuz.VVOzeti olarak verir; burada yalniz
kurallar denetlenir. VVOzeti yoksa K6 "USL hesaplanamadi" der.

  K6      k + 2σ < USL (eş. 36; kati esitsizlik)
  K6-AOA  uygulamanin kategorik AOA ozellikleri kumede var mi (Tablo 2.3)
  K8      pozitif yanlilik kredilendirilmez (eş. 8)
  K9      k_calc / k_exp normallestirmesi (eş. 9)
  K10     n < 10 gerekce; parametrik olmayanda β ≤ %40 -> USL yok (Tablo 2.2)
  K11     ΔSM ≥ 0.02 (§2.4.5)
  K12     uygulama parametresi dogrulama araliginin disinda mi (§5)
  K13     egilim ve normallik sonuclari; yontem secimiyle tutarlilik (§2.4.2-3)
  K14     ayni deney serisinden cok vaka: bagimsizlik notu (UACSA)
"""

from cekirdek.ceviri import _, N_
from cekirdek.uygunluk_denetimi.kurallar import STANDART, IYI_UYGULAMA, Kural
from cekirdek.uygunluk_denetimi.profiller import NUREG_6698, ESITLIK, TABLO
from cekirdek.uygunluk_denetimi.kurallar_rapor import belirsizlik_metni
from cekirdek.uygunluk_denetimi.vv_arayuz import AOA_KATEGORILERI

_VV_YOK = N_("Doğrulama (V&V) kümesi yok: bu kural değerlendirilemedi.")
_VV_ONERI = N_("Kritiklik güvenliği için S-3 doğrulama kümesi (yanlılık, USL, AOA) "
               "gereklidir.")


def _vv_yok(kural, baglam):
    if baglam.vv is None:
        return [kural.uygulanamadi(_(_VV_YOK), _(_VV_ONERI))]
    return None


def k6_usl(kural, baglam):
    kosu = baglam.kosu
    if kosu is None or not kosu.ozdeger:
        return [kural.uygulanamadi(_("Özdeğer koşusu sonucu yok: k + 2σ < USL "
                                     "denetlenemedi."))]
    vv = baglam.vv
    if vv is None or vv.usl is None:
        neden = (vv.usl_neden if vv is not None and vv.usl_neden
                 else _("doğrulama (V&V) kümesi yok"))
        return [kural.uygulanamadi(
            _("USL hesaplanamadı (%s). k = %s bir alt-kritiklik "
              "sınırıyla karşılaştırılmadı; bu sonuç kritiklik güvenliği kanıtı "
              "değildir.") % (neden, belirsizlik_metni(kosu.keff, kosu.sigma)),
            _(_VV_ONERI))]
    c = baglam.esik("kabul_carpani", 2.0)
    ust = kosu.keff + c * kosu.sigma
    if ust < vv.usl:
        return [kural.gecti(_("k + %gσ = %.5f < USL = %.5f.") % (c, ust, vv.usl))]
    return [kural.ihlal("hata", _("k + %gσ = %.5f, USL = %.5f: kabul koşulu "
                                  "sağlanmıyor.") % (c, ust, vv.usl),
                        _("Sistem alt-kritiklik ölçütünü karşılamıyor; tasarımı ya da "
                          "denetim parametrelerini değiştirin."))]


def k6_aoa(kural, baglam):
    erken = _vv_yok(kural, baglam)
    if erken:
        return erken
    ortak = [k for k in AOA_KATEGORILERI
             if k in baglam.uygulama and k in baglam.vv.aoa_kategorik]
    if not ortak:
        return [kural.uygulanamadi(_("Uygulamanın kategorik AOA özellikleri (bölünebilir "
                                     "element, fiziksel biçim, yansıtıcı, tayf) "
                                     "verilmedi."))]
    bulgular = []
    for k in ortak:
        deger, kume = baglam.uygulama[k], tuple(baglam.vv.aoa_kategorik[k])
        if deger in kume:
            bulgular.append(kural.gecti(_("%s: %s kümede var.") % (k, deger)))
        else:
            bulgular.append(kural.ihlal(
                "uyari", _("%s: uygulama '%s', doğrulama kümesi yalnız %s içeriyor — "
                           "uygulanabilirlik alanının dışında.") % (k, deger, ", ".join(kume)),
                _("Bu özelliği taşıyan kriter deneyleri kümeye ekleyin.")))
    return bulgular


def k8_pozitif_yanlilik(kural, baglam):
    erken = _vv_yok(kural, baglam)
    if erken:
        return erken
    vv = baglam.vv
    if vv.bias_kullanilan > 0:
        return [kural.ihlal("hata", _("USL'de pozitif yanlılık (%+.5f) kredilendirilmiş.")
                            % vv.bias_kullanilan,
                            _("Yanlılık > 0 ise USL hesabında 0 alınmalıdır."))]
    return [kural.gecti(_("Kullanılan yanlılık %+.5f (ham %+.5f); pozitif yanlılık "
                          "kredilendirilmedi.") % (vv.bias_kullanilan, vv.bias))]


def k9_normallestirme(kural, baglam):
    erken = _vv_yok(kural, baglam)
    if erken:
        return erken
    if not baglam.vv.normallestirildi:
        return [kural.ihlal("uyari", _("Kriter k_exp ≠ 1 olan vakalar k_calc / k_exp ile "
                                       "normalleştirilmemiş."),
                            _("k_norm = k_calc / k_exp ve σ = √(σ_calc² + σ_exp²) "
                              "kullanın."))]
    return [kural.gecti(_("k_calc / k_exp normalleştirmesi uygulandı."))]


def k10_vaka_sayisi(kural, baglam):
    erken = _vv_yok(kural, baglam)
    if erken:
        return erken
    vv, bulgular = baglam.vv, []
    n_asgari = baglam.esik("n_asgari", 10)
    if vv.n < n_asgari:
        bulgular.append(kural.ihlal("uyari", _("Kümede %d vaka (< %d): teknik gerekçe "
                                               "gerekli.") % (vv.n, n_asgari),
                                    _("Kümeye bağımsız kriter deneyleri ekleyin.")))
    else:
        bulgular.append(kural.gecti(_("Kümede %d vaka.") % vv.n))
    if vv.yontem == "parametrik_olmayan":
        esik = baglam.esik("guven_asgari", 0.40)
        if vv.guven is None:
            bulgular.append(kural.ihlal("uyari", _("Parametrik olmayan yöntemde güven "
                                                   "düzeyi (β) bildirilmemiş."),
                                        kimlik="K10-guven"))
        elif vv.guven <= esik and vv.usl is not None:
            bulgular.append(kural.ihlal(
                "hata", _("β = %%%.1f ≤ %%%.0f iken USL verilmiş; ek veri gerekir, USL "
                          "hesaplanamaz.") % (100 * vv.guven, 100 * esik),
                kimlik="K10-guven"))
    return bulgular


def k11_pay(kural, baglam):
    asgari = baglam.esik("delta_sm_asgari", 0.02)
    if baglam.vv is not None:
        dsm, nereden = baglam.vv.delta_sm, _("doğrulama kümesi")
    else:
        dsm, nereden = baglam.esik("delta_sm"), _("profil")
    if dsm is None:
        return [kural.uygulanamadi(_("Alt-kritik pay (ΔSM) tanımlı değil."))]
    if dsm < asgari:
        return [kural.ihlal("hata", _("ΔSM = %.3f (%s) mutlak alt sınırın (%.2f) altında: "
                                      "profil geçersiz.") % (dsm, nereden, asgari),
                            _("ΔSM'yi en az %.2f yapın ve gerekçesini yazın.") % asgari)]
    return [kural.gecti(_("ΔSM = %.3f (%s) ≥ %.2f; seçilen değerin gerekçesi "
                          "kullanıcı kuruluşa aittir.") % (dsm, nereden, asgari),
                        kaynak=kural.kaynak + "; " + baglam.esik_kaynagi("delta_sm"))]


def _dis_degerleme(deger, alt, ust):
    """Aralik disina tasma orani (aralik genisligine gore); icindeyse 0."""
    genislik = ust - alt
    tasma = max(alt - deger, deger - ust, 0.0)
    if tasma == 0:
        return 0.0
    return float("inf") if genislik <= 0 else tasma / genislik


def _k12_parametre(kural, baglam, ad, deger):
    alt, ust = baglam.vv.aralik[ad]
    oran = _dis_degerleme(deger, alt, ust)
    if oran == 0:
        return kural.gecti(_("%s = %g doğrulama aralığında [%g, %g].") % (ad, deger, alt, ust))
    metin = _("%s = %g doğrulama aralığının [%g, %g] dışında (taşma %%%.0f).") % (
        ad, deger, alt, ust, 100 * oran if oran != float("inf") else 999)
    if baglam.vv.yontem == "tolerans_siniri":
        return kural.ihlal("hata", metin + " " + _("Tolerans sınırı yöntemi dış değerleme "
                                                   "için kullanılamaz."),
                           _("Tolerans bandı yöntemini kullanın ya da kümeyi genişletin."))
    if oran > baglam.esik("dis_degerleme_azami", 0.10):
        return kural.ihlal("uyari", metin, _("Doğrulama kümesi genişletilmeli."))
    if baglam.vv.delta_aoa == 0:
        return kural.ihlal("uyari", metin, _("Dış değerleme için ΔAOA payı ve gerekçesi "
                                             "girilmeli."))
    return kural.not_(metin + " " + _("ΔAOA = %.3f uygulandı.") % baglam.vv.delta_aoa)


def k12_aralik(kural, baglam):
    erken = _vv_yok(kural, baglam)
    if erken:
        return erken
    ortak = [a for a in baglam.uygulama if a in baglam.vv.aralik]
    if not ortak:
        return [kural.uygulanamadi(_("Uygulamanın sayısal AOA parametreleri (zenginlik, "
                                     "H/X, EALF…) verilmedi."))]
    return [_k12_parametre(kural, baglam, a, float(baglam.uygulama[a])) for a in ortak]


def k13_egilim_normallik(kural, baglam):
    erken = _vv_yok(kural, baglam)
    if erken:
        return erken
    vv, bulgular = baglam.vv, []
    if vv.normallik is None:
        bulgular.append(kural.ihlal("uyari", _("Normallik testi sonucu raporlanmamış."),
                                    kimlik="K13-normallik"))
    elif not vv.normallik.get("normal") and vv.yontem != "parametrik_olmayan":
        bulgular.append(kural.ihlal("hata", _("Veri normal değil (%s) ama '%s' yöntemi "
                                              "kullanılmış.") % (vv.normallik.get("test", "?"),
                                                                vv.yontem),
                                    _("Parametrik olmayan yöntem zorunludur."),
                                    kimlik="K13-normallik"))
    else:
        bulgular.append(kural.gecti(_("Normallik sonucu yöntemle tutarlı."),
                                    kimlik="K13-normallik"))
    anlamli = sorted(p for p, e in vv.egilim.items() if e.get("anlamli"))
    if anlamli and vv.yontem == "tolerans_siniri":
        bulgular.append(kural.ihlal("uyari", _("Anlamlı eğilim var (%s) ama tolerans sınırı "
                                               "yöntemi kullanılmış.") % ", ".join(anlamli),
                                    _("Eğilim varsa tolerans bandı yöntemini kullanın."),
                                    kimlik="K13-egilim"))
    elif not vv.egilim:
        bulgular.append(kural.ihlal("uyari", _("Eğilim analizi sonucu raporlanmamış."),
                                    kimlik="K13-egilim"))
    else:
        bulgular.append(kural.gecti(_("Eğilim sonucu yöntemle tutarlı."), kimlik="K13-egilim"))
    return bulgular


def k14_seriler(kural, baglam):
    erken = _vv_yok(kural, baglam)
    if erken:
        return erken
    cok = sorted((s, n) for s, n in baglam.vv.seriler.items() if n > 1)
    if cok:
        metin = ", ".join("%s (%d)" % sn for sn in cok)
        return [kural.not_(_("Aynı deney serisinden birden çok vaka: %s. Vakalar bağımsız "
                             "değil; istatistik güveni abartılı olabilir.") % metin)]
    return [kural.gecti(_("Her deney serisinden en çok bir vaka."))]


KURALLAR = (
    Kural("K6", "B", N_("Kabul koşulu k + 2σ < USL"), NUREG_6698 + " " + ESITLIK + " (1), (35), (36)",
          STANDART, k6_usl),
    Kural("K6-AOA", "B", N_("Uygulanabilirlik alanı (kategorik)"),
          NUREG_6698 + " §2.5, " + TABLO + " 2.3", STANDART, k6_aoa),
    Kural("K8", "B", N_("Pozitif yanlılık kredilendirilmez"), NUREG_6698 + " §2.4.1 " + ESITLIK + " (8)",
          STANDART, k8_pozitif_yanlilik),
    Kural("K9", "B", N_("k_calc / k_exp normalleştirmesi"), NUREG_6698 + " §2.4.1 " + ESITLIK + " (9)",
          STANDART, k9_normallestirme),
    Kural("K10", "B", N_("Vaka sayısı ve güven düzeyi"), NUREG_6698 + " §2.2, " + TABLO + " 2.2",
          STANDART, k10_vaka_sayisi),
    Kural("K11", "B", N_("Alt-kritik pay ΔSM ≥ 0.02"), NUREG_6698 + " §2.4.5",
          STANDART, k11_pay),
    Kural("K12", "B", N_("Doğrulama aralığı dışına dış değerleme"), NUREG_6698 + " §5",
          STANDART, k12_aralik),
    Kural("K13", "B", N_("Eğilim ve normallik"), NUREG_6698 + " §2.4.2–2.4.3",
          STANDART, k13_egilim_normallik),
    Kural("K14", "B", N_("Deneyler arası bağımsızlık"),
          "NEA/NSC/WPNCS/DOC(2013)7 (UACSA)", IYI_UYGULAMA, k14_seriler),
)
