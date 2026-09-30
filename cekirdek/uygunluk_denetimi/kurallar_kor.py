# -*- coding: utf-8 -*-
"""
uygunluk_denetimi/kurallar_kor.py -- Profil C: reaktor kor tasarimi.

GIRDI (baglam.kor; denetle() ya parametreden ya da kosu dizinindeki
uygunluk_girdisi.json'un "kor" anahtarindan alir):
    {"katsayilar": {"guc" | "yakit_sicaklik" | "sogutucu_sicaklik" | "void_orani":
                        {"egim": e, "egim_sapma": s, "birim": "pcm/K"}},   # tarama.katsayi
     "kapatma_marji": {"deger_pcm": Δρ·1e5, "sapma_pcm": σ,
                       "en_degerli_cubuk_sikisik": bool},
     "faktorler": {"F_dH", "F_dH_sapma", "F_q", "F_q_sapma"},  # yoksa statepoint'ten
     "dogrulama": ["kor yonteminin dogrulandigi kriter(ler)", ...]}

  K7      katsayi isaretleri -- GDC 11 cercevesi (STANDARTLAR.md §6 madde 8):
          net guc geri beslemesi (guc katsayisi) anlamli pozitifse HATA,
          Doppler anlamli pozitifse UYARI; pozitif MTC / bosluk katsayisi
          tek basina HATA DEGILDIR (bilgi + gecici rejim notu).
  K7-SDM  kapatma marji, en degerli cubuk sikisik (N-1); sinir kullanicidan
  K7-F    F_ΔH / F_q; sinir kullanicidan (varsayilan YOK)
  K16     kor yonteminin dogrulama referansi (ANS-19.3-2022 / ISO 18075)
"""

from cekirdek.ceviri import _, N_
from cekirdek.uygunluk_denetimi.kurallar import (KULLANICI_SINIRI, STANDART, Kural)
from cekirdek.uygunluk_denetimi.profiller import SRP_43

_KAYNAK_TURU = {
    "guc": SRP_43 + " II.2 (GDC 11); IAEA SSG-52 (2019)",
    "arastirma": "IAEA SSR-3 (2016) Bölüm 6; IAEA SSG-22 (Rev. 1) (madde no. DOĞRULANMADI)",
}
_KATSAYI_ADLARI = {
    "guc": N_("güç katsayısı"), "yakit_sicaklik": N_("Doppler (yakıt sıcaklık) katsayısı"),
    "sogutucu_sicaklik": N_("moderatör sıcaklık katsayısı (MTC)"),
    "void_orani": N_("boşluk (void) katsayısı"),
}


def _kaynak(baglam):
    return _KAYNAK_TURU.get(baglam.esik("reaktor_turu", "guc"), _KAYNAK_TURU["guc"])


def _isaret(kats, c):
    """+1 / -1 anlamli isaret, 0 anlamsiz."""
    e, s = float(kats["egim"]), float(kats.get("egim_sapma") or 0.0)
    if abs(e) <= c * s:
        return 0
    return 1 if e > 0 else -1


def _katsayi_bulgusu(kural, baglam, ad, kats):
    c = baglam.esik("anlamlilik_carpani", 2.0)
    isaret = _isaret(kats, c)
    metin = "%s = %+.3g ± %.2g %s (1σ)" % (_(_KATSAYI_ADLARI[ad]), kats["egim"],
                                          kats.get("egim_sapma") or 0.0, kats.get("birim", ""))
    kw = {"kimlik": "K7-" + ad, "kaynak": _kaynak(baglam)}
    if isaret < 0:
        return kural.gecti(metin + _(": negatif."), **kw)
    if isaret == 0:
        seviye = "uyari" if ad == "guc" else "bilgi"
        return kural.ihlal(seviye, metin + _(": işaret istatistiksel olarak belirlenemedi "
                                             "(|eğim| ≤ %gσ).") % c,
                           _("Tarama aralığını genişletin ya da istatistiği artırın."), **kw)
    if ad == "guc":
        return kural.ihlal("hata", metin + _(": POZİTİF — güç işletme aralığında net anlık "
                                             "geri besleme reaktivite artışını karşılamıyor."),
                           _("Tasarım GDC 11 çerçevesini karşılamıyor; kor bileşimini "
                             "gözden geçirin."), **kw)
    if ad == "yakit_sicaklik":
        return kural.ihlal("uyari", metin + _(": POZİTİF Doppler katsayısı olağan dışıdır."),
                           _("Yakıt bileşimini ve sıcaklık taramasını denetleyin; net güç "
                             "katsayısını hesaplayın."), **kw)
    return kural.not_(metin + _(": pozitif. Tek başına hata değildir (SRP 4.3 pozitif "
                                "MTC'yi dışlamaz); geçici rejim analizinde "
                                "değerlendirilmelidir."), **kw)


def k7_katsayilar(kural, baglam):
    katsayilar = (baglam.kor or {}).get("katsayilar") or {}
    bilinen = [a for a in _KATSAYI_ADLARI if a in katsayilar]
    if not bilinen:
        return [kural.uygulanamadi(_("Reaktivite katsayısı sonucu verilmedi."),
                                   _("Analiz sekmesinde sıcaklık/boşluk taraması yapın."),
                                   kaynak=_kaynak(baglam))]
    bulgular = [_katsayi_bulgusu(kural, baglam, a, katsayilar[a]) for a in bilinen]
    if "guc" not in katsayilar:
        bulgular.append(kural.ihlal(
            "bilgi", _("Net güç katsayısı verilmedi: GDC 11 (net geri besleme) yalnız "
                       "bileşen katsayılarından yargılanamaz."), kimlik="K7-guc",
            kaynak=_kaynak(baglam)))
    return bulgular


def _sinirla_karsilastir(kural, baglam, ad, deger, sapma, esik_adi, kimlik):
    """deger <= sinir beklenir (F_dH, F_q). sinir yoksa uygulanamadi."""
    sinir = baglam.esik(esik_adi)
    kaynak = baglam.esik_kaynagi(esik_adi)
    metin = "%s = %.3f ± %.3f (1σ)" % (ad, deger, sapma or 0.0)
    if sinir is None:
        return kural.uygulanamadi(metin + _("; sınır girilmedi, karşılaştırılamadı "
                                            "(tesise özel; varsayılan yok)."),
                                  _("Profil C'de %s eşiğini kaynağıyla girin.") % esik_adi,
                                  kimlik=kimlik, kaynak=kaynak)
    if deger > sinir:
        return kural.ihlal("hata", metin + _(" > sınır %.3f.") % sinir, kimlik=kimlik,
                           kaynak=kaynak)
    if deger + 2 * (sapma or 0.0) > sinir:
        return kural.ihlal("uyari", metin + _(": sınırdan (%.3f) 2σ içinde; istatistiksel "
                                              "olarak ayırt edilemiyor.") % sinir,
                           _("İstatistiği artırın."), kimlik=kimlik, kaynak=kaynak)
    return kural.gecti(metin + _(" ≤ sınır %.3f.") % sinir, kimlik=kimlik, kaynak=kaynak)


def _faktorler(baglam):
    """(faktorler | None, hata | None): once kor girdisi, sonra statepoint."""
    f = (baglam.kor or {}).get("faktorler")
    if f:
        return f, None
    if baglam.kosu is None:
        return None, None
    from cekirdek.uygunluk_denetimi import ayristir
    return ayristir.guc_faktorleri(baglam.kosu.statepoint)


def k7_faktorler(kural, baglam):
    f, hata = _faktorler(baglam)
    if hata:
        return [kural.ihlal("uyari", _("Güç dağılımı okunamadı: %s") % hata)]
    if not f or f.get("F_dH") is None:
        return [kural.uygulanamadi(_("Güç dağılımı sonucu yok (F_ΔH / F_q)."),
                                   _("Güç dağılımını açıp koşuyu yineleyin."))]
    bulgular = [_sinirla_karsilastir(kural, baglam, "F_ΔH", f["F_dH"], f.get("F_dH_sapma"),
                                     "F_dH_siniri", "K7-FdH")]
    if f.get("F_q") is not None:
        bulgular.append(_sinirla_karsilastir(kural, baglam, "F_q", f["F_q"],
                                             f.get("F_q_sapma"), "F_q_siniri", "K7-Fq"))
    return bulgular


def _sdm_sinir(kural, baglam, deger, sapma):
    sinir = baglam.esik("sdm_siniri_pcm")
    kaynak = baglam.esik_kaynagi("sdm_siniri_pcm")
    metin = _("Kapatma marjı = %.0f ± %.0f pcm (Δρ × 10⁵, 1σ)") % (deger, sapma)
    if sinir is None:
        return kural.uygulanamadi(metin + _("; sınır girilmedi, karşılaştırılamadı."),
                                  _("Profil C'de sdm_siniri_pcm eşiğini kaynağıyla girin."),
                                  kaynak=kaynak)
    if deger < sinir:
        return kural.ihlal("hata", metin + _(" < sınır %.0f pcm.") % sinir, kaynak=kaynak)
    if deger - 2 * sapma < sinir:
        return kural.ihlal("uyari", metin + _(": sınırdan (%.0f pcm) 2σ içinde.") % sinir,
                           kaynak=kaynak)
    return kural.gecti(metin + _(" ≥ sınır %.0f pcm.") % sinir, kaynak=kaynak)


def k7_kapatma(kural, baglam):
    sdm = (baglam.kor or {}).get("kapatma_marji")
    if not sdm or sdm.get("deger_pcm") is None:
        return [kural.uygulanamadi(_("Kapatma marjı sonucu verilmedi."))]
    bulgular = []
    if not sdm.get("en_degerli_cubuk_sikisik"):
        bulgular.append(kural.ihlal("uyari", _("Kapatma marjı en değerli çubuk sıkışık "
                                               "(N−1) varsayımıyla hesaplanmamış ya da "
                                               "belirtilmemiş."),
                                    _("En değerli çubuğu dışarıda bırakarak yeniden "
                                      "hesaplayın."), kimlik="K7-SDM-N1"))
    if sdm.get("sapma_pcm") is None:
        bulgular.append(kural.ihlal("uyari", _("Kapatma marjının belirsizliği (yöntem hatası "
                                               "dahil) verilmemiş."), kimlik="K7-SDM-sigma"))
    bulgular.append(_sdm_sinir(kural, baglam, float(sdm["deger_pcm"]),
                               float(sdm.get("sapma_pcm") or 0.0)))
    return bulgular


def k16_dogrulama(kural, baglam):
    ref = (baglam.kor or {}).get("dogrulama")
    if not ref:
        return [kural.ihlal("bilgi", _("Kor hesap yönteminin hangi kriterlerle doğrulandığı "
                                       "ve uygulama aralığı belirtilmedi."),
                            _("Doğrulama referanslarını (IRPhEP / hesap-hesap "
                              "karşılaştırması) girin."))]
    return [kural.gecti(_("Doğrulama referansları: %s") % "; ".join(map(str, ref)))]


KURALLAR = (
    Kural("K7", "C", N_("Reaktivite katsayılarının işareti (GDC 11)"),
          SRP_43 + " II.2 (GDC 11), III", STANDART, k7_katsayilar),
    Kural("K7-SDM", "C", N_("Kapatma marjı (en değerli çubuk sıkışık)"),
          SRP_43 + "; GDC 26/27", KULLANICI_SINIRI, k7_kapatma),
    Kural("K7-F", "C", N_("Güç tepe faktörleri F_ΔH / F_q"),
          SRP_43 + N_(" (sınırlar tesise özel)"), KULLANICI_SINIRI, k7_faktorler),
    Kural("K16", "C", N_("Kor yöntem doğrulaması referansı"),
          "ANSI/ANS-19.3-2022; ISO 18075:2018 (madde ayrıntısı DOĞRULANMADI)",
          STANDART, k16_dogrulama),
)
