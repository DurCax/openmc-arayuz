# -*- coding: utf-8 -*-
"""
 test_y9_varyans.py  --  v3 Y9: varyans azaltma (agirlik pencereleri, MAGIC) ve FOM

 HIZLI: ayar okuma ve dogrulama, kurucu Settings'i, betik esdegerligi, FOM formulu, dogrula.
 YAVAS (zirh_agirlik_pencere: 14.1 MeV nokta kaynak, su/celik/su, dedektor suyu):
   analog kosu -> MAGIC uretimi (kuresel ag, analog tasima) -> pencereli kosu.
   * YANLILIKSIZLIK: pencereli sonuc analog ile |fark| <= 2 sigma_birlesik (iki bagimsiz
     kosu, 5e5 / 2e4 tarih; olculen degerler asagida yazilidir).
   * FOM: olculur ve yazilir; kabul olcutu yalniz FOM_pencere > FOM_analog (olculen ~3x).
"""

import os

from cekirdek import sema
from testler.ortak_test import kontrol, ORNEK, ISLEM_PARCACIGI
from testler.ortak_test import gereksinim  # v3 izlenebilirlik

_K_SIGMA = 2.0          # iki bagimsiz tahminin uyumu (birlesik sapmaya gore)
_ANALOG = (20000, 100)  # parcacik, cevrim (2e6 tarih; ~%10 bagil hata)
_URETIM = (20000, 40)
_PENCERELI = (1000, 20)  # 2e4 tarih; her tarih analogdan ~100x pahali


def _zirh():
    return sema.yukle(os.path.join(ORNEK, "zirh_agirlik_pencere.json"))


def _varyans(spec, **alan):
    s = sema.yukle(os.path.join(ORNEK, "zirh_agirlik_pencere.json")) if spec is None else spec
    s["ayarlar"]["varyans"] = dict({"var": True}, **alan)
    return s


# ---------------------------------------------------------------------------
# HIZLI
# ---------------------------------------------------------------------------

def test_ayar_yoksa_kapali_ve_gecersiz_degerler_hata():
    print("\n[Y9-V1] ayar yoksa kapali; gecersiz mod/yontem/ag/enerji ValueError")
    from cekirdek import varyans
    # Arrange / Act / Assert
    kontrol("alan yok -> kapali", varyans.ayar(_zirh()).var is False)
    varsayilan = varyans.ayar(_varyans(None))
    kontrol("varsayilan: uret, magic, 10^3 ag", (varsayilan.mod, varsayilan.yontem,
            varsayilan.boyut) == ("uret", "magic", (10, 10, 10)))
    hatali = {"mod": "x"}, {"yontem": "fw_cadis"}, {"mesh_boyut": [0, 1, 1]}, \
        {"mesh_boyut": [1, 1]}, {"enerji_siniri": [1.0]}, {"enerji_siniri": [2.0, 1.0]}, \
        {"mod": "uygula"}, {"mesh_turu": "altigen"}, {"max_gerceklesme": 0}
    for h in hatali:
        try:
            varyans.ayar(_varyans(None, **h))
            kontrol("ValueError bekleniyordu: %r" % (h,), False)
        except ValueError:
            kontrol("ValueError: %r" % (h,), True)


def test_kurucu_settings_uretim_ve_uygulama_kipleri():
    print("\n[Y9-V2] kurucu: 'uret' on_the_fly=False + windows_on=False; 'uret_uygula' True; 'uygula' dosya")
    from cekirdek import kurucu
    # Arrange / Act
    uret, _b = kurucu.kur(_varyans(None, mod="uret", mesh_boyut=[6, 6, 6]))
    otf, _b = kurucu.kur(_varyans(None, mod="uret_uygula", mesh_turu="kuresel",
                                  mesh_boyut=[8, 1, 1], enerji_siniri=[0.0, 1e6, 2e7]))
    dosya, _b = kurucu.kur(_varyans(None, mod="uygula", dosya="/tmp/ww.h5"))
    g = uret.settings.weight_window_generators[0]
    g2 = otf.settings.weight_window_generators[0]
    # Assert
    kontrol("uret: analog uretim", g.on_the_fly is False and uret.settings.weight_windows_on is False)
    kontrol("uret: 6x6x6 duzenli ag, kutu = sinir kutusu",
            tuple(g.mesh.dimension) == (6, 6, 6) and tuple(g.mesh.upper_right) == (110.0,) * 3,
            "-> %r" % (g.mesh.upper_right,))
    kontrol("uret_uygula: ayni kosuda uygulanir", g2.on_the_fly is True and otf.settings.weight_windows_on)
    kontrol("kuresel ag, 8 yaricap bolmesi", type(g2.mesh).__name__ == "SphericalMesh"
            and len(g2.mesh.r_grid) == 9 and g2.mesh.r_grid[-1] == 110.0)
    kontrol("enerji gruplari", list(g2.energy_bounds) == [0.0, 1e6, 2e7])
    kontrol("uygula: dosya", str(dosya.settings.weight_windows_file).endswith("ww.h5")
            and dosya.settings.weight_windows_on is True)
    kontrol("ayar yoksa generator yok", len(kurucu.kur(_zirh())[0].settings.weight_window_generators) == 0)


def _ag_ozeti(mesh):
    if hasattr(mesh, "r_grid"):
        return ([float(x) for x in mesh.r_grid], [float(x) for x in mesh.theta_grid],
                [float(x) for x in mesh.phi_grid])
    return (list(mesh.dimension), [float(x) for x in mesh.lower_left],
            [float(x) for x in mesh.upper_right])


def test_betik_ayni_ayarlari_kurar():
    print("\n[Y9-V3] betik esdegerligi: uretilen betigin Settings'i kurucuyla ayni")
    import importlib.util
    import tempfile
    from cekirdek import kod_uret, kurucu
    for alan in ({"mod": "uret", "mesh_boyut": [5, 5, 5]},
                 {"mod": "uret_uygula", "mesh_turu": "kuresel", "mesh_boyut": [7, 1, 1],
                  "max_gerceklesme": 12, "guncelleme_araligi": 2, "enerji_siniri": [0.0, 1e6, 2e7]}):
        # Arrange
        spec = _varyans(None, **alan)
        model, _b = kurucu.kur(spec)
        # Act
        with tempfile.TemporaryDirectory() as d:
            yol = os.path.join(d, "model.py")
            with open(yol, "w", encoding="utf-8") as f:
                f.write(kod_uret.uret(spec, "model.py"))
            eski = os.getcwd()
            os.chdir(d)
            try:
                sm = importlib.util.spec_from_file_location("y9_betik", yol)
                mod = importlib.util.module_from_spec(sm)
                sm.loader.exec_module(mod)
            finally:
                os.chdir(eski)
        a, b = model.settings.weight_window_generators[0], mod.model.settings.weight_window_generators[0]
        # Assert
        kontrol("%s: yontem/gerceklesme/aralik/on_the_fly" % alan["mod"],
                (a.method, a.max_realizations, a.update_interval, a.on_the_fly)
                == (b.method, b.max_realizations, b.update_interval, b.on_the_fly))
        kontrol("%s: ag ayni" % alan["mod"], type(a.mesh) is type(b.mesh)
                and _ag_ozeti(a.mesh) == _ag_ozeti(b.mesh), "-> %r / %r"
                % (_ag_ozeti(a.mesh), _ag_ozeti(b.mesh)))
        kontrol("%s: windows_on" % alan["mod"], model.settings.weight_windows_on
                == mod.model.settings.weight_windows_on)


def test_fom_formulu_ve_tanimsiz_durumlar():
    print("\n[Y9-V4] FOM = 1/(sigma_bagil^2 T): el hesabi; sifir deger/sapma/sure -> None")
    from cekirdek import varyans
    # Arrange / Act / Assert
    kontrol("1/(0.01^2 * 100) = 100", abs(varyans.fom(1.0, 0.01, 100.0) - 100.0) < 1e-9)
    kontrol("sure 2x -> FOM 1/2", abs(varyans.fom(5.0, 0.05, 200.0) - 50.0) < 1e-9)
    kontrol("negatif deger: |deger|", abs(varyans.fom(-1.0, 0.01, 100.0) - 100.0) < 1e-9)
    kontrol("deger 0 -> None", varyans.fom(0.0, 0.1, 10.0) is None)
    kontrol("sapma 0 -> None", varyans.fom(1.0, 0.0, 10.0) is None)
    kontrol("sure 0 -> None", varyans.fom(1.0, 0.1, 0.0) is None)
    s = varyans.fom_satiri("t", 2.0, 0.02, 10.0)
    kontrol("satir bagil hata 1 %", abs(s.bagil_hata - 0.01) < 1e-12 and abs(s.fom - 1000.0) < 1e-9)


def test_fom_kalemleri_skor_nuklid_basina_bin_toplanmaz():
    print("\n[Y9-V4b] FOM: (skor, nuklid) basina; filtre bin'leri toplanmaz")
    from types import SimpleNamespace
    import numpy as np
    from cekirdek import varyans
    # Arrange
    tek = SimpleNamespace(scores=["flux"], nuclides=["total"], mean=np.array([[[2.0]]]),
                          std_dev=np.array([[[0.02]]]))
    iki = SimpleNamespace(scores=["flux", "heating"], nuclides=["total"],
                          mean=np.array([[[1.0, 1e6]]]), std_dev=np.array([[[0.01, 5e4]]]))
    bin3 = SimpleNamespace(scores=["flux"], nuclides=["total"],
                           mean=np.array([[[1.0]], [[1.0]], [[0.0]]]),
                           std_dev=np.array([[[0.01]], [[0.1]], [[0.0]]]))
    # Act / Assert
    k1 = varyans._tally_fom_kalemleri(tek)
    kontrol("tek skor/bin: tally'nin kendi degeri, ek yok", k1 == [("", 2.0, 0.02)], repr(k1))
    k2 = varyans._tally_fom_kalemleri(iki)
    kontrol("iki skor: iki kalem, birim karismaz", [x[1] for x in k2] == [1.0, 1e6]
            and "flux" in k2[0][0] and "heating" in k2[1][0], repr(k2))
    k3 = varyans._tally_fom_kalemleri(bin3)
    kontrol("bin'ler: en kotu (en buyuk bagil hata) bin, sifir bin atlanir",
            len(k3) == 1 and k3[0][2] == 0.1, repr(k3))


def test_dogrula_2b_dosya_yok_ve_otf_bilgisi():
    print("\n[Y9-V5] dogrula: 2B model hata, olmayan pencere dosyasi hata, uret_uygula bilgi")
    from cekirdek import dogrula
    # Arrange
    pin = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    pin["ayarlar"]["varyans"] = {"var": True}
    dosyasiz = _varyans(None, mod="uygula", dosya="/yok/ww.h5")
    otf = _varyans(None, mod="uret_uygula")
    # Act
    b_pin = dogrula.tum_kontroller(pin, veri_kontrolu=False)
    b_dosya = dogrula.tum_kontroller(dosyasiz, veri_kontrolu=False)
    b_otf = dogrula.tum_kontroller(otf, veri_kontrolu=False)
    # Assert
    kontrol("2B: hata", any(b.seviye == "hata" and "3B" in b.mesaj for b in b_pin))
    kontrol("dosya yok: hata", any(b.seviye == "hata" and "dosyası yok" in b.mesaj for b in b_dosya))
    kontrol("uret_uygula: bilgi", any(b.seviye == "bilgi" and "'üret'" in b.mesaj for b in b_otf))
    kontrol("temiz uret: varyans bulgusu yok", not [b for b in dogrula.tum_kontroller(
        _varyans(None, mod="uret"), veri_kontrolu=False) if b.yer == "ayarlar" and "ağırlık" in b.mesaj])


# ---------------------------------------------------------------------------
# YAVAS
# ---------------------------------------------------------------------------

def _kos(spec, dizin, parcacik, cevrim):
    from cekirdek import kosucu, varyans
    s = sema.yukle(os.path.join(ORNEK, "zirh_agirlik_pencere.json")) if spec is None else spec
    s["ayarlar"].update(parcacik=parcacik, cevrim=cevrim)
    os.makedirs(dizin, exist_ok=True)
    kosucu.calistir(s, dizin, is_parcacigi=ISLEM_PARCACIGI)
    sp = kosucu.son_statepoint(dizin)
    satir = varyans.fom_tablosu(sp)[0]
    return satir


@gereksinim("R-V3-27")
def test_agirlik_penceresi_yanliliksiz_ve_fom_artar(gecici):
    print("\n[Y9-Y1] zirh: pencereli sonuc analog ile 2 sigma icinde; FOM olculur")
    import math
    from cekirdek import varyans
    # Arrange / Act
    analog = _kos(None, os.path.join(gecici, "analog"), *_ANALOG)
    uret_spec = _varyans(None, mod="uret", mesh_turu="kuresel", mesh_boyut=[8, 1, 1],
                         max_gerceklesme=_URETIM[1])
    _kos(uret_spec, os.path.join(gecici, "uret"), *_URETIM)
    h5 = varyans.kosu_dosyasi(os.path.join(gecici, "uret"))
    kontrol("weight_windows.h5 yazildi", os.path.isfile(h5))
    pencere = _kos(_varyans(None, mod="uygula", dosya=h5), os.path.join(gecici, "pencere"),
                   *_PENCERELI)
    # Assert
    fark = abs(pencere.deger - analog.deger)
    birlesik = math.hypot(pencere.sapma, analog.sapma)
    print("  analog  : %.4e +- %.2e (%.1f %%) T=%.0f s FOM=%.2f" % (
        analog.deger, analog.sapma, 100 * analog.bagil_hata, analog.sure_s, analog.fom))
    print("  pencere : %.4e +- %.2e (%.1f %%) T=%.0f s FOM=%.2f" % (
        pencere.deger, pencere.sapma, 100 * pencere.bagil_hata, pencere.sure_s, pencere.fom))
    print("  fark %.2f sigma_birlesik; FOM orani %.2f (uretim suresi haric)" % (
        fark / birlesik, pencere.fom / analog.fom))
    kontrol("yanliliksiz: |fark| <= %g sigma" % _K_SIGMA, fark <= _K_SIGMA * birlesik,
            "-> fark %.3g, birlesik sigma %.3g" % (fark, birlesik))
    kontrol("FOM_pencere > FOM_analog", pencere.fom > analog.fom,
            "-> %.2f / %.2f" % (pencere.fom, analog.fom))


HIZLI = [test_ayar_yoksa_kapali_ve_gecersiz_degerler_hata,
         test_kurucu_settings_uretim_ve_uygulama_kipleri, test_betik_ayni_ayarlari_kurar,
         test_fom_formulu_ve_tanimsiz_durumlar, test_fom_kalemleri_skor_nuklid_basina_bin_toplanmaz, test_dogrula_2b_dosya_yok_ve_otf_bilgisi]
YAVAS = [test_agirlik_penceresi_yanliliksiz_ve_fom_artar]
