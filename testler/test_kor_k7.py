# -*- coding: utf-8 -*-
"""
test_kor_k7.py -- Profil C K7 duzeltmeleri (profesor denetimi, Dalga 4).

  [K7a] K7-F: cok tohum ozeti (F_dH_harita / _harita_sapma) varsa o kullanilir;
        yoksa bulgu "σ iyimser" notunu tasir.
  [K7b] K7: SFR'de (su moderatorlu olmayan) sogutucu katsayisina "MTC" denmez.

Monte Carlo KOSULMAZ.
"""

from testler.ortak_test import kontrol


def _baglam(kor, spec=None, esikler=None):
    from cekirdek.uygunluk_denetimi.kurallar import Baglam
    return Baglam(spec=spec, kor=kor, esikler=esikler or {})


def _kural(kimlik):
    from cekirdek.uygunluk_denetimi import kurallar_kor as kk
    return [k for k in kk.KURALLAR if k.kimlik == kimlik][0]


def test_k7f_cok_tohum_sigmasi():
    print("\n[K7a] K7-F: cok tohum sacilmasi varsa o; yoksa 'σ iyimser'")
    from cekirdek.uygunluk_denetimi import kurallar_kor as kk
    tek = kk.k7_faktorler(_kural("K7-F"), _baglam(
        {"faktorler": {"F_dH": 1.07, "F_dH_sapma": 0.001}}))
    kontrol("tek kosu -> iyimser notu", "iyimser" in tek[0].mesaj, "-> %s" % tek[0].mesaj)
    cok = kk.k7_faktorler(_kural("K7-F"), _baglam(
        {"faktorler": {"F_dH": 1.08, "F_dH_sapma": 0.001, "F_dH_harita": 1.0755,
                       "F_dH_harita_sapma": 0.0086}}))
    m = cok[0].mesaj
    kontrol("cok tohum -> harita degeri ve σ", "1.0755" in m and "0.0086" in m
            and "çok tohum" in m and "iyimser" not in m, "-> %s" % m)


def test_k7_sfr_mtc_demez():
    print("\n[K7b] K7: SFR'de 'MTC' denmez (sogutucu sicaklik katsayisi)")
    from cekirdek.uygunluk_denetimi import kurallar_kor as kk
    kor = {"katsayilar": {"sogutucu_sicaklik": {"egim": 0.3, "egim_sapma": 0.05,
                                                "birim": "pcm/K"}}}
    sfr = kk.k7_katsayilar(_kural("K7"), _baglam(kor, spec={"kategori": "sfr"}))
    m = " ".join(b.mesaj for b in sfr)
    kontrol("SFR: MTC yok, soğutucu sıcaklık katsayısı var", "MTC" not in m
            and "soğutucu sıcaklık katsayısı" in m, "-> %s" % m)
    pwr = kk.k7_katsayilar(_kural("K7"), _baglam(kor, spec={"kategori": "pwr"}))
    kontrol("PWR: MTC", any("MTC" in b.mesaj for b in pwr))


HIZLI = [test_k7f_cok_tohum_sigmasi, test_k7_sfr_mtc_demez]
YAVAS = []
