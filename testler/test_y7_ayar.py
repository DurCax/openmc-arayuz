# -*- coding: utf-8 -*-
"""
 test_y7_ayar.py  --  v3 Y7: foton tasinimi ve sicaklik isleme ayarlari

 HIZLI: ayar okuyuculari (alan yoksa OpenMC varsayilani), kurucu ve uretilen
        betigin AYNI openmc.Settings'i kurmasi, OpenMC 0.16 sicaklik secim
        kurali (nuclide.cpp / thermal.cpp) el hesabiyla, cross_sections.xml
        foton/wmp kayitlari (sahte kutuphane), dogrulama bulgulari.
"""

import os
import tempfile

from cekirdek import sema
from testler.ortak_test import kontrol
from testler.regresyon_ortak import ORNEK


def _pin():
    return sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))


def _betik_ayari(spec):
    """Uretilen betigi calistirip openmc.Settings'ini dondurur (kosu yok)."""
    import importlib.util
    from cekirdek import kod_uret
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, "model.py")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(kod_uret.uret(spec, "model.py"))
        eski = os.getcwd()
        os.chdir(d)
        try:
            sm = importlib.util.spec_from_file_location("y7_betik", yol)
            mod = importlib.util.module_from_spec(sm)
            sm.loader.exec_module(mod)
        finally:
            os.chdir(eski)
    return mod.model.settings


def _veri_yoksa_atla():
    """Gercek nukleer veri isteyen hizli testler veri yoksa atlanir (CI)."""
    import pytest
    yol = os.environ.get("OPENMC_CROSS_SECTIONS", "")
    if not (yol and os.path.exists(yol)):
        pytest.skip("nukleer veri yok (OPENMC_CROSS_SECTIONS)")


def _sahte_kutuphane(dizin, kayitlar):
    """[(tur, malzemeler)] -> sahte cross_sections.xml yolu."""
    yol = os.path.join(dizin, "cross_sections.xml")
    govde = "".join('<library materials="%s" path="x/%s.h5" type="%s" />'
                    % (m, m.split()[0], t) for t, m in kayitlar)
    with open(yol, "w", encoding="utf-8") as f:
        f.write("<?xml version='1.0'?><cross_sections>%s</cross_sections>" % govde)
    return yol


# ---------------------------------------------------------------------------
# foton ayari
# ---------------------------------------------------------------------------

def test_foton_ayari_yoksa_kapali_ve_openmc_varsayilani():
    print("\n[Y7-1] foton ayari yoksa kapali; elektron islemi OpenMC varsayilani (ttb)")
    from cekirdek import foton
    # Arrange
    spec = _pin()
    # Act
    a = foton.ayar(spec)
    # Assert
    kontrol("kapali", a.var is False)
    kontrol("ttb (settings.cpp: ElectronTreatment::TTB)", a.elektron == "ttb")
    kontrol("foton tasinimi istenmiyor", not foton.tasinim_var_mi(spec))


def test_foton_ayari_bilinmeyen_elektron_hata():
    print("\n[Y7-2] bilinmeyen elektron islemi: acikken ValueError, kapaliyken varsayilan")
    from cekirdek import foton
    # Arrange
    spec = _pin()
    spec["ayarlar"]["foton"] = {"var": True, "elektron": "xyz"}
    # Act / Assert
    try:
        foton.ayar(spec)
        kontrol("ValueError bekleniyordu", False)
    except ValueError as e:
        kontrol("ValueError, mesajda gecerliler", "led" in str(e) and "ttb" in str(e))
    spec["ayarlar"]["foton"]["var"] = False
    kontrol("kapaliyken varsayilana duser", foton.ayar(spec).elektron == "ttb")


def test_foton_kaynagi_tasinimi_acar():
    print("\n[Y7-3] foton kaynagi, ayar kapali olsa da foton tasinimi ister")
    from cekirdek import foton
    # Arrange
    spec = _pin()
    spec["ayarlar"]["kaynak"]["parcacik"] = "photon"
    # Act / Assert
    kontrol("tasinim var", foton.tasinim_var_mi(spec))


def test_kurucu_foton_ve_elektron_ayari():
    print("\n[Y7-4] kurucu: foton acik -> photon_transport True, electron_treatment led")
    from cekirdek import kurucu
    # Arrange
    spec = _pin()
    spec["ayarlar"]["foton"] = {"var": True, "elektron": "led"}
    # Act
    model, _b = kurucu.kur(spec)
    # Assert
    kontrol("photon_transport True", model.settings.photon_transport is True)
    kontrol("electron_treatment led", model.settings.electron_treatment == "led")


def test_ayar_yoksa_settings_eskisiyle_ayni():
    print("\n[Y7-5] Y7 alanlari yoksa Settings eskisi gibi (yalniz method)")
    from cekirdek import kurucu
    # Arrange
    spec = _pin()
    # Act
    s = kurucu.kur(spec)[0].settings
    # Assert
    kontrol("temperature yalniz method", s.temperature == {"method": "interpolation"},
            "-> %r" % s.temperature)
    kontrol("photon_transport atanmadi", s.photon_transport is None)
    kontrol("electron_treatment atanmadi", s.electron_treatment is None)


# ---------------------------------------------------------------------------
# sicaklik ayari
# ---------------------------------------------------------------------------

def test_sicaklik_ayari_ve_settings_sozlugu():
    print("\n[Y7-6] sicaklik: tolerans, multipole, aralik, varsayilan -> settings.temperature")
    from cekirdek import sicaklik
    # Arrange
    spec = _pin()
    spec["ayarlar"]["sicaklik_yontemi"] = "nearest"
    spec["ayarlar"]["sicaklik"] = {"tolerans": 50.0, "multipole": True,
                                   "aralik": [300.0, 1200.0], "varsayilan": 600.0}
    # Act
    a = sicaklik.ayar(spec)
    d = sicaklik.settings_sozlugu(spec)
    # Assert
    kontrol("yontem nearest", a.yontem == "nearest")
    kontrol("sozluk tam", d == {"method": "nearest", "tolerance": 50.0, "multipole": True,
                                "range": (300.0, 1200.0), "default": 600.0}, "-> %r" % d)


def test_sicaklik_ayari_yoksa_openmc_varsayilanlari():
    print("\n[Y7-7] sicaklik ayari yoksa OpenMC varsayilanlari (tol 10 K, 293.6 K)")
    from cekirdek import sicaklik
    # Arrange
    spec = _pin()
    spec["ayarlar"].pop("sicaklik_yontemi", None)
    # Act
    a = sicaklik.ayar(spec)
    # Assert
    kontrol("nearest (settings.cpp)", a.yontem == "nearest")
    kontrol("tolerans 10 K", a.tolerans == 10.0)
    kontrol("varsayilan 293.6 K", a.varsayilan == 293.6)
    kontrol("multipole kapali, aralik yok", a.multipole is False and a.aralik is None)
    kontrol("settings sozlugu bos", sicaklik.settings_sozlugu(spec) == {})


def test_sicaklik_ayari_gecersiz_degerler():
    print("\n[Y7-8] sicaklik: negatif tolerans, ters aralik, bilinmeyen yontem -> ValueError")
    from cekirdek import sicaklik
    for alan, deger in (("tolerans", -1.0), ("aralik", [900.0, 300.0]),
                        ("varsayilan", 0.0)):
        # Arrange
        spec = _pin()
        spec["ayarlar"]["sicaklik"] = {alan: deger}
        # Act / Assert
        try:
            sicaklik.ayar(spec)
            kontrol("%s reddedilmeli" % alan, False)
        except ValueError:
            kontrol("%s reddedildi" % alan, True)
    spec = _pin()
    spec["ayarlar"]["sicaklik_yontemi"] = "spline"
    try:
        sicaklik.ayar(spec)
        kontrol("bilinmeyen yontem reddedilmeli", False)
    except ValueError:
        kontrol("bilinmeyen yontem reddedildi", True)


def test_kurucu_ve_betik_ayni_ayarlar():
    print("\n[Y7-9] kurucu ve uretilen betik AYNI Settings (foton + sicaklik)")
    from cekirdek import kurucu
    # Arrange
    spec = _pin()
    spec["ayarlar"]["foton"] = {"var": True, "elektron": "led"}
    spec["ayarlar"]["sicaklik"] = {"tolerans": 25.0, "multipole": False,
                                   "aralik": [294.0, 900.0]}
    # Act
    a = kurucu.kur(spec)[0].settings
    b = _betik_ayari(spec)
    # Assert
    for alan in ("photon_transport", "electron_treatment", "temperature"):
        kontrol("%s ayni" % alan, getattr(a, alan) == getattr(b, alan),
                "-> %r / %r" % (getattr(a, alan), getattr(b, alan)))


# ---------------------------------------------------------------------------
# OpenMC 0.16 sicaklik secim kurali (nuclide.cpp, thermal.cpp)
# ---------------------------------------------------------------------------

_MEVCUT = (250.0, 293.6, 600.0, 900.0, 1200.0, 2500.0)


def test_en_yakin_yontemi_tolerans_icinde_ve_disinda():
    print("\n[Y7-10] nearest: |T_k - T| < tolerans ise en yakin, degilse OpenMC durur")
    from cekirdek import sicaklik
    # Act
    tam = sicaklik.degerlendir(293.6, _MEVCUT, "nearest", 10.0)
    yakin = sicaklik.degerlendir(300.0, _MEVCUT, "nearest", 10.0)
    yok = sicaklik.degerlendir(750.0, _MEVCUT, "nearest", 10.0)
    sinir = sicaklik.degerlendir(610.0, _MEVCUT, "nearest", 10.0)
    # Assert
    kontrol("293.6: tam", tam.durum == "tam" and tam.kullanilan == (294,))
    kontrol("300: yakin (294 K verisi)", yakin.durum == "yakin" and yakin.kullanilan == (294,))
    kontrol("750: yok (OpenMC fatal_error)", yok.durum == "yok" and yok.kullanilan == ())
    kontrol("610: |600-610| = 10 tolerans esit -> yok (kati esitsizlik)",
            sinir.durum == "yok")


def test_interpolasyon_komsu_ciftler_ve_kenar():
    print("\n[Y7-11] interpolation: T_j <= T < T_j+1 cifti; disarida tolerans icinde kenar")
    from cekirdek import sicaklik
    # Act
    ara = sicaklik.degerlendir(750.0, _MEVCUT, "interpolation", 10.0)
    tam = sicaklik.degerlendir(600.0, _MEVCUT, "interpolation", 10.0)
    kenar = sicaklik.degerlendir(2505.0, _MEVCUT, "interpolation", 10.0)
    ust = sicaklik.degerlendir(2500.0, _MEVCUT, "interpolation", 10.0)
    yok = sicaklik.degerlendir(3000.0, _MEVCUT, "interpolation", 10.0)
    alt = sicaklik.degerlendir(245.0, _MEVCUT, "interpolation", 10.0)
    # Assert
    kontrol("750: 600-900 arasi", ara.durum == "ara" and ara.kullanilan == (600, 900))
    kontrol("600: tam (600-900 cifti yuklenir)", tam.durum == "tam"
            and tam.kullanilan == (600, 900))
    kontrol("2505: ust kenar (tolerans icinde)", kenar.durum == "kenar"
            and kenar.kullanilan == (2500,))
    kontrol("2500: ust deger tam", ust.durum == "tam" and ust.kullanilan == (2500,))
    kontrol("3000: yok", yok.durum == "yok")
    kontrol("245: alt kenar", alt.durum == "kenar" and alt.kullanilan == (250,))


def test_tek_sicaklikli_veride_en_yakina_doner():
    print("\n[Y7-12] tek sicaklik varsa OpenMC interpolasyondan en yakina doner")
    from cekirdek import sicaklik
    # Act
    k = sicaklik.degerlendir(600.0, (293.6,), "interpolation", 10.0)
    # Assert
    kontrol("yok (nearest kurali; 600 tolerans disi)", k.durum == "yok")


# ---------------------------------------------------------------------------
# kutuphane: foton ve wmp kayitlari, sicaklik listesi
# ---------------------------------------------------------------------------

def test_kutuphane_foton_ve_wmp_kayitlari(gecici):
    print("\n[Y7-13] cross_sections.xml: foton elementleri ve wmp kaydi okunur")
    from cekirdek import foton, sicaklik
    # Arrange
    yol = _sahte_kutuphane(gecici, [("neutron", "U235"), ("photon", "U"), ("photon", "O")])
    d2 = os.path.join(gecici, "wmp")
    os.makedirs(d2)
    yol_wmp = _sahte_kutuphane(d2, [("neutron", "U235"), ("wmp", "U235")])
    # Act
    el = foton.kutuphane_elementleri(yol)
    # Assert
    kontrol("foton elementleri {U, O}", el == frozenset({"U", "O"}), "-> %r" % (el,))
    kontrol("wmp yok", sicaklik.wmp_nuklidleri(yol) == frozenset())
    kontrol("wmp: U235", sicaklik.wmp_nuklidleri(yol_wmp) == frozenset({"U235"}))
    kontrol("dosya yoksa None", foton.kutuphane_elementleri(os.path.join(gecici, "yok.xml"))
            is None)


def test_eksik_foton_elementleri(gecici):
    print("\n[Y7-14] modeldeki elementlerden foton verisi olmayanlar")
    from cekirdek import foton
    # Arrange
    yol = _sahte_kutuphane(gecici, [("photon", "U"), ("photon", "O")])
    spec = _pin()
    # Act
    eksik = foton.eksik_elementler(spec, yol)
    # Assert
    kontrol("H ve Zr eksik (pin: UO2, Zr, su)", {"H", "Zr"} <= set(eksik), "-> %r" % (eksik,))
    kontrol("U, O eksik degil", not ({"U", "O"} & set(eksik)))


def test_kutuphane_sicakliklari_gercek_veri():
    print("\n[Y7-15] ENDF/B-VIII.0: U235 sicakliklari kT/k_B (293.6 K dahil)")
    _veri_yoksa_atla()
    from cekirdek import sicaklik
    # Act
    t = sicaklik.kutuphane_sicakliklari("neutron", "U235")
    h = sicaklik.kutuphane_sicakliklari("thermal", "c_H_in_H2O")
    # Assert
    kontrol("okundu", t is not None and len(t) >= 2, "-> %r" % (t,))
    kontrol("sirali", list(t) == sorted(t))
    kontrol("293.6 K var (0.1 K)", any(abs(x - 293.6) < 0.1 for x in t), "-> %r" % (t,))
    kontrol("su S(a,b) okundu", h is not None and h[0] < 300 < h[-1], "-> %r" % (h,))


# ---------------------------------------------------------------------------
# dogrulama
# ---------------------------------------------------------------------------

def _bulgular(spec, **kw):
    from cekirdek.dogrula import y7
    return y7.y7_kontrol(spec, **kw)


def test_dogrula_foton_verisi_yoksa_hata(gecici):
    print("\n[Y7-16] foton acik, kutuphanede element foton verisi yok -> hata")
    # Arrange
    yol = _sahte_kutuphane(gecici, [("photon", "U")])
    spec = _pin()
    spec["ayarlar"]["foton"] = {"var": True}
    # Act
    b = _bulgular(spec, veri_kontrolu=True, kutuphane=yol)
    # Assert
    h = [x for x in b if x.seviye == "hata" and "foton" in x.mesaj]
    kontrol("hata var", bool(h), "-> %s" % [x.mesaj for x in b])
    kontrol("eksik element adi mesajda", h and "H" in h[0].mesaj)


def test_dogrula_isinma_skoru_foton_uyumu():
    print("\n[Y7-17] heating foton kapali -> uyari; heating-local foton acik -> uyari")
    # Arrange
    spec = _pin()
    spec["tallyler"] = [sema.tally("isi", ["heating", "kappa-fission"])]
    # Act
    kapali = _bulgular(spec, veri_kontrolu=False)
    spec["ayarlar"]["foton"] = {"var": True}
    spec["tallyler"] = [sema.tally("isi", ["heating-local"])]
    acik = _bulgular(spec, veri_kontrolu=False)
    # Assert
    kontrol("heating + foton kapali -> uyari",
            any(x.seviye == "uyari" and "heating" in x.mesaj for x in kapali),
            "-> %s" % [x.mesaj for x in kapali])
    kontrol("heating-local + foton acik -> uyari",
            any(x.seviye == "uyari" and "heating-local" in x.mesaj for x in acik),
            "-> %s" % [x.mesaj for x in acik])


def test_dogrula_multipole_wmp_yoksa_uyari(gecici):
    print("\n[Y7-18] multipole acik, wmp verisi yok -> uyari (OpenMC yalniz uyarir)")
    # Arrange
    yol = _sahte_kutuphane(gecici, [("neutron", "U235")])
    spec = _pin()
    spec["ayarlar"]["sicaklik"] = {"multipole": True}
    # Act
    b = _bulgular(spec, veri_kontrolu=True, kutuphane=yol, sicaklik_denetimi=False)
    # Assert
    kontrol("uyari", any(x.seviye == "uyari" and "multipole" in x.mesaj for x in b),
            "-> %s" % [x.mesaj for x in b])


def test_dogrula_gecersiz_sicaklik_ayari_hata():
    print("\n[Y7-19] gecersiz sicaklik ayari -> hata bulgusu (istisna degil)")
    # Arrange
    spec = _pin()
    spec["ayarlar"]["sicaklik"] = {"tolerans": -5}
    # Act
    b = _bulgular(spec, veri_kontrolu=False)
    # Assert
    kontrol("hata", any(x.seviye == "hata" for x in b), "-> %s" % [x.mesaj for x in b])


def test_dogrula_malzeme_sicakligi_kutuphanede_yok():
    print("\n[Y7-20] nearest + 750 K yakit: hata; interpolation: bilgi (600-900 K arasi)")
    _veri_yoksa_atla()
    # Arrange
    spec = _pin()
    yakit = next(m for m in spec["malzemeler"] if m["ad"] == "uo2")
    yakit["sicaklik"] = 750.0
    spec["ayarlar"]["sicaklik_yontemi"] = "nearest"
    # Act
    en_yakin = _bulgular(spec, veri_kontrolu=True)
    spec["ayarlar"]["sicaklik_yontemi"] = "interpolation"
    ara = _bulgular(spec, veri_kontrolu=True)
    # Assert
    kontrol("nearest: hata, mesajda 750", any(
        x.seviye == "hata" and "750" in x.mesaj for x in en_yakin),
        "-> %s" % [x.mesaj for x in en_yakin])
    kontrol("interpolation: hata yok", not any(x.seviye == "hata" for x in ara),
            "-> %s" % [x.mesaj for x in ara if x.seviye == "hata"])
    kontrol("interpolation: 600-900 bilgi", any(
        x.seviye == "bilgi" and "600" in x.mesaj and "900" in x.mesaj for x in ara),
        "-> %s" % [x.mesaj for x in ara])


def test_dogrula_yakin_sicaklik_uyarisi():
    print("\n[Y7-21] nearest + 300 K su: uyari (yalniz kutuphane sicakligi, 294 K kullanilir)")
    _veri_yoksa_atla()
    # Arrange
    spec = _pin()
    for m in spec["malzemeler"]:
        m["sicaklik"] = 300.0
    spec["ayarlar"]["sicaklik_yontemi"] = "nearest"
    # Act
    b = _bulgular(spec, veri_kontrolu=True)
    # Assert
    kontrol("uyari: 294 K verisi", any(x.seviye == "uyari" and "294" in x.mesaj for x in b),
            "-> %s" % [x.mesaj for x in b])
    kontrol("hata yok", not any(x.seviye == "hata" for x in b))


def test_tum_kontrollere_bagli():
    print("\n[Y7-22] dogrula.tum_kontroller Y7 kurallarini calistirir")
    from cekirdek import dogrula
    # Arrange
    spec = _pin()
    spec["ayarlar"]["sicaklik"] = {"tolerans": -5}
    # Act
    b = dogrula.tum_kontroller(spec, veri_kontrolu=False)
    # Assert
    kontrol("Y7 hatasi listede", any(x.yer == "sicaklik" and x.seviye == "hata" for x in b))


HIZLI = [test_foton_ayari_yoksa_kapali_ve_openmc_varsayilani,
         test_foton_ayari_bilinmeyen_elektron_hata, test_foton_kaynagi_tasinimi_acar,
         test_kurucu_foton_ve_elektron_ayari, test_ayar_yoksa_settings_eskisiyle_ayni,
         test_sicaklik_ayari_ve_settings_sozlugu, test_sicaklik_ayari_yoksa_openmc_varsayilanlari,
         test_sicaklik_ayari_gecersiz_degerler, test_kurucu_ve_betik_ayni_ayarlar,
         test_en_yakin_yontemi_tolerans_icinde_ve_disinda,
         test_interpolasyon_komsu_ciftler_ve_kenar, test_tek_sicaklikli_veride_en_yakina_doner,
         test_kutuphane_foton_ve_wmp_kayitlari, test_eksik_foton_elementleri,
         test_kutuphane_sicakliklari_gercek_veri, test_dogrula_foton_verisi_yoksa_hata,
         test_dogrula_isinma_skoru_foton_uyumu, test_dogrula_multipole_wmp_yoksa_uyari,
         test_dogrula_gecersiz_sicaklik_ayari_hata, test_dogrula_malzeme_sicakligi_kutuphanede_yok,
         test_dogrula_yakin_sicaklik_uyarisi, test_tum_kontrollere_bagli]
YAVAS = []
