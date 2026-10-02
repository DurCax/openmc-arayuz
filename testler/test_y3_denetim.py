# -*- coding: utf-8 -*-
"""
 test_y3_denetim.py  --  v3 Y3 inceleme bulgulari (python-reviewer + fizik denetimi)

 HIZLI: birden cok yakit malzemesinde spektrum (n_mat, G) toplanir; kismi /
        eksik Y3 tally'leri ve eksik sizinti sessiz 0 olmaz; ayar dayanikliligi;
        tukenmede Y3 kapali (klonlu malzeme filtresi); dogrulama (y3_ oneki,
        gecersiz grup, tukenme bilgisi); spektrum kapali betik bayt bayt ayni;
        sonuc karti hata/sizinti-bilinmiyor/homojen notlari; ayar karti
        gecersiz grubu uyarir.
 YAVAS: iki yakit malzemeli pin hucre kosusu: spektrum = malzemeler toplami.
"""

import os

import pandas as pd

from cekirdek import sema
from testler.ortak_test import kontrol, ISLEM_PARCACIGI
from testler.regresyon_ortak import ORNEK, _qt

_GOR_TOL = 1e-12


def _pin(var=True, grup="CASMO-70"):
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    spec["ayarlar"]["spektrum"] = {"var": var, "grup_yapisi": grup}
    return spec


def _iki_yakitli_pin():
    """Yakit iki radyal bolge: ic uo2_ic (%4), dis uo2 (%3)."""
    spec = _pin()
    ic = dict(spec["malzemeler"][0], ad="uo2_ic", gorunen_ad="UO2 %4.0")
    ic["bilesim"] = [dict(ic["bilesim"][0], zenginlik=4.0), dict(ic["bilesim"][1])]
    spec["malzemeler"] = [ic] + spec["malzemeler"]
    bolgeler = spec["cubuklar"][0]["bolgeler"]
    spec["cubuklar"][0]["bolgeler"] = [{"r": 0.2, "malzeme": "uo2_ic"}] + bolgeler
    return spec


# ---------------------------------------------------------------------------
# sahte statepoint (kosusuz okuma testleri)
# ---------------------------------------------------------------------------

class _Tally:
    def __init__(self, ad, satirlar):
        self.name = ad
        self._df = pd.DataFrame(satirlar)

    def get_pandas_dataframe(self):
        return self._df.copy()


class _K:
    nominal_value, std_dev = 1.30, 0.002


class _SP:
    run_mode = "eigenvalue"
    keff = _K()

    def __init__(self, tallyler, sizinti=True):
        self.tallies = {i: t for i, t in enumerate(tallyler)}
        self.global_tallies = ([{"name": b"leakage", "mean": 0.0, "std_dev": 0.0}]
                               if sizinti else [])

    def get_tally(self, name):
        for t in self.tallies.values():
            if t.name == name:
                return t
        raise LookupError(name)


def _toplam_tally(xn_eksik=False):
    from cekirdek import spektrum as s
    satir = [{"score": "nu-fission", "mean": 1.3, "std. dev.": 0.004},
             {"score": "absorption", "mean": 1.0, "std. dev.": 0.003}]
    for skor, _x in s.XN_SKORLARI[(1 if xn_eksik else 0):]:
        satir.append({"score": skor, "mean": 0.0002, "std. dev.": 1e-5})
    return _Tally(s.T_TOPLAM, satir)


def _termal_tally():
    from cekirdek import spektrum as s
    return _Tally(s.T_TERMAL, [{"score": "nu-fission", "mean": 1.05, "std. dev.": 0.004},
                               {"score": "absorption", "mean": 0.66, "std. dev.": 0.002}])


def test_spektrum_dizisi_malzemeler_uzerinden_toplanir():
    print("\n[Y3-D1] (n_mat*G) duz dizi -> G grup; ortalamalar ve varyanslar toplanir")
    from cekirdek import spektrum as s
    # Arrange: 2 malzeme x 3 grup (enerji filtresi son, en hizli degisen)
    ort = [1.0, 2.0, 3.0, 10.0, 20.0, 30.0]
    sap = [0.3, 0.4, 0.0, 0.4, 0.3, 1.0]
    # Act
    aki, sapma = s.spektrum_dizisi(ort, sap, 3)
    # Assert
    kontrol("3 grup", len(aki) == 3 and len(sapma) == 3)
    kontrol("toplam el hesabi", list(aki) == [11.0, 22.0, 33.0])
    kontrol("sapma karesel toplam", abs(sapma[0] - 0.5) < _GOR_TOL and abs(sapma[2] - 1.0) < _GOR_TOL)


def test_oku_y3siz_kismi_ve_sizintisiz():
    print("\n[Y3-D2] oku: Y3 yoksa None; kismi ise eksik + faktor yok; sizinti yoksa P_NL/k None")
    from cekirdek import spektrum as s
    # Arrange
    yok = _SP([_Tally("kullanici", [{"score": "flux", "mean": 1.0, "std. dev.": 0.1}])])
    kismi = _SP([_termal_tally()])
    sizintisiz = _SP([_toplam_tally(), _termal_tally()], sizinti=False)
    # Act
    r_yok, r_kismi, r_siz = s.oku(yok), s.oku(kismi), s.oku(sizintisiz)
    # Assert
    kontrol("Y3 tally'si yok -> None", r_yok is None)
    kontrol("kismi: eksik listesi ve faktorler None",
            r_kismi["eksik"] == [s.T_TOPLAM] and r_kismi["faktorler"] is None)
    f = r_siz["faktorler"]
    kontrol("sizinti bilinmiyor -> sizinti None, P_NL None, k None",
            r_siz["sizinti"] is None and f["p_nl"] is None and f["k"] is None)
    kontrol("sizinti bilinmese de eps ve carpim tanimli",
            f["eps"] is not None and f["carpim"] is not None)


def test_eksik_skor_sessiz_sifir_olmaz():
    print("\n[Y3-D3] eksik (n,xn) skoru: X None -> c_xn ve k None (0 sayilmaz)")
    from cekirdek import spektrum as s
    # Arrange
    sp = _SP([_toplam_tally(xn_eksik=True), _termal_tally()])
    # Act
    f = s.oku(sp)["faktorler"]
    # Assert
    kontrol("c_xn None", f["c_xn"] is None)
    kontrol("k None", f["k"] is None)
    kontrol("carpim (nF/A) yine tanimli", f["carpim"] is not None)


def test_ayar_dayanikliligi():
    print("\n[Y3-D4] ayar: sozluk degilse kapali; kapaliyken gecersiz grup hata vermez")
    from cekirdek import spektrum as s
    # Arrange
    a, b = _pin(), _pin(var=False, grup="BOZUK")
    a["ayarlar"]["spektrum"] = "evet"
    # Act / Assert
    kontrol("sozluk degil -> kapali varsayilan",
            s.ayar(a) == {"var": False, "grup_yapisi": s.VARSAYILAN_GRUP})
    kontrol("kapali + gecersiz grup -> varsayilan grup, hata yok",
            s.ayar(b) == {"var": False, "grup_yapisi": s.VARSAYILAN_GRUP})


def test_tukenmede_y3_kapali():
    print("\n[Y3-D5] tukenme_icin: Y3 kapali YENI spec (girdi degismez); kurucu y3 kurmaz")
    from cekirdek import kurucu, spektrum as s
    # Arrange
    spec = _pin()
    # Act
    kopya = s.tukenme_icin(spec)
    model, _b = kurucu.kur(kopya)
    # Assert
    kontrol("girdi spec degismedi", spec["ayarlar"]["spektrum"]["var"] is True)
    kontrol("kopyada kapali", s.ayar(kopya)["var"] is False)
    kontrol("tukenme modelinde y3 tally'si yok",
            not any((t.name or "").startswith(s.TALLY_ONEKI) for t in model.tallies))
    kapali = _pin(var=False)
    kontrol("kapaliyken ayni nesne doner", s.tukenme_icin(kapali) is kapali)


def test_tukenme_hazirla_cubuk_cubuk_y3siz():
    print("\n[Y3-D6] tukenme.hazirla (cubuk cubuk yanma, spektrum acik): klonlar var, y3 yok")
    from cekirdek import tukenme, spektrum as s
    # Arrange
    spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    spec["tukenme"]["var"] = True
    spec["tukenme"]["malzemeleri_ayir"] = True
    spec["ayarlar"]["spektrum"] = {"var": True, "grup_yapisi": "CASMO-70"}
    # Act
    model, bilgi = tukenme.hazirla(spec)
    # Assert
    kontrol("klon (ornek) ayrildi", bilgi["ornek_sayisi"] > 1, "-> %s" % bilgi["ornek_sayisi"])
    kontrol("y3 tally'si yok",
            not any((t.name or "").startswith(s.TALLY_ONEKI) for t in model.tallies))


def test_dogrulama_bulgulari():
    print("\n[Y3-D7] dogrula: y3_ onekli kullanici tally'si hata; gecersiz grup hata; tukenme bilgi")
    from cekirdek import dogrula, sema_yapici
    # Arrange
    a = _pin(var=False)
    a["tallyler"] = [sema_yapici.tally("y3_benim", ["flux"])]
    b = _pin(grup="BOZUK")
    c = _pin()
    c["tukenme"]["var"] = True
    # Act
    ba, bb, bc = (dogrula.spektrum_kontrol(x) for x in (a, b, c))
    # Assert
    kontrol("y3_ oneki hata", any(x.seviye == "hata" and "y3_" in x.mesaj for x in ba))
    kontrol("gecersiz grup hata", any(x.seviye == "hata" and "BOZUK" in x.mesaj for x in bb))
    kontrol("tukenme + spektrum bilgi", any(x.seviye == "bilgi" for x in bc))
    kontrol("tum_kontroller kancasi", any("y3_" in x.mesaj
                                          for x in dogrula.tum_kontroller(a, veri_kontrolu=False)))


def test_spektrum_kapali_betik_bayt_bayt_ayni():
    print("\n[Y3-D8] spektrum alani yok / kapali: uretilen betik bayt bayt ayni")
    from cekirdek import kod_uret
    # Arrange
    yok = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    kapali = _pin(var=False)
    # Act
    k1, k2 = kod_uret.uret(yok, "model.py"), kod_uret.uret(kapali, "model.py")
    # Assert
    kontrol("bayt bayt ayni", k1.encode("utf-8") == k2.encode("utf-8"))
    kontrol("y3 izi yok", "y3_" not in k1)


def test_betik_adlari_islevde():
    print("\n[Y3-D9] betik: Y3 gecici adlari modul ad alanina sizmaz")
    import tempfile
    import importlib.util
    from cekirdek import kod_uret
    # Arrange
    spec = _pin()
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, "model.py")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(kod_uret.uret(spec, "model.py"))
        eski = os.getcwd()
        os.chdir(d)
        try:
            sm = importlib.util.spec_from_file_location("y3_ad_testi", yol)
            mod = importlib.util.module_from_spec(sm)
            sm.loader.exec_module(mod)
        finally:
            os.chdir(eski)
    # Assert
    kontrol("_t ve _liste yok", not hasattr(mod, "_t") and not hasattr(mod, "_liste"))
    kontrol("model'de y3 tally'leri", any(t.name == "y3_toplam" for t in mod.model.tallies))


def _sahte_sonuc(**ek):
    from cekirdek import spektrum as s
    import numpy as np
    d = s.Deger
    h = {"nF": d(1.3, 0.004), "A": d(1.0, 0.003), "X": d(0.001, 1e-4), "nF_th": d(1.0, 0.004),
         "A_th": d(0.6, 0.002), "A_yakit_th": d(0.6, 0.002), "L": d(0.0, 0.0)}
    h.update(ek)
    return {"faktorler": s.faktorleri_hesapla(h), "indeksler": None,
            "spektrum": {"kenarlar": np.geomspace(1e-5, 2e7, 4), "model": (np.ones(3), np.zeros(3))},
            "keff": d(1.3, 0.002), "sizinti": h["L"], "termal_fisyon_payi": 0.8,
            "termal_kesim": 0.625, "eksik": []}


def test_sonuc_karti_notlari_ve_hata_korumasi():
    print("\n[Y3-D10] sonuc karti: homojen f=1 notu, sizinti bilinmiyor -> 'k', cizim hatasi yutulmaz")
    if _qt() is None:
        return
    from arayuz.sonuc.spektrum import SpektrumKarti, tablo_satirlari, varsayim_notlari
    # Arrange
    homojen = _sahte_sonuc()
    bilinmiyor = _sahte_sonuc(L=None)
    kart = SpektrumKarti()
    bozuk = dict(homojen, spektrum={"kenarlar": [1.0, 2.0, 3.0], "model": ([1.0] * 5, [0.0] * 5)})
    # Act
    notlar = " ".join(varsayim_notlari(homojen, True))
    semboller = [x[0] for x in tablo_satirlari(bilinmiyor, None)]
    import cekirdek.spektrum as s
    asil = s.oku
    s.oku = lambda _yol: bozuk
    try:
        kart.sonuc_ayarla("sahte.h5")
    finally:
        s.oku = asil
    # Assert
    kontrol("homojen f = 1 notu", "f = 1" in notlar)
    kontrol("X kanallari notu", "MT 11" in notlar)
    kontrol("sizinti bilinmiyor: k (k∞ degil)", "k" in semboller and "k∞" not in semboller)
    kontrol("bilinmiyor notu", "Sızıntı bilinmiyor" in " ".join(varsayim_notlari(bilinmiyor, None)))
    kontrol("cizim hatasi kartta gosterilir, istisna yukari cikmaz",
            not kart.isHidden() and "okunamadı" in kart.tablo.text())
    kart.deleteLater()


def test_ayar_karti_gecersiz_grup_uyarisi():
    print("\n[Y3-D11] ayar karti: spec acik + gecersiz grup -> onay acik kalir, uyari gorunur")
    if _qt() is None:
        return
    from arayuz.ayar.spektrum_karti import SpektrumAyarKarti
    # Arrange
    kart = SpektrumAyarKarti()
    spec = _pin(grup="BOZUK")
    # Act
    kart.doldur(spec)
    # Assert
    kontrol("onay spec ile ayni (acik)", kart.var.isChecked())
    kontrol("uyari gorunur ve grubu adlandirir",
            not kart.uyari.isHidden() and "BOZUK" in kart.uyari.text())
    kontrol("spec sessizce degismedi", spec["ayarlar"]["spektrum"]["grup_yapisi"] == "BOZUK")
    kart.grup.setCurrentIndex(kart.grup.findData("SHEM-361"))
    kontrol("secim spec'i duzeltir, uyari kalkar",
            spec["ayarlar"]["spektrum"]["grup_yapisi"] == "SHEM-361" and kart.uyari.isHidden())
    kart.deleteLater()


def test_iki_yakitli_pin_spektrum(gecici):
    print("\n[Y3-DY1] iki yakit malzemeli pin: yakit spektrumu G grup, malzeme toplami; kart cizer")
    import openmc
    from cekirdek import kurucu, spektrum as s
    # Arrange
    spec = _iki_yakitli_pin()
    spec["ayarlar"].update(parcacik=1000, cevrim=20, pasif=5)
    dizin = os.path.join(gecici, "iki")
    os.makedirs(dizin)
    eski = os.getcwd()
    os.chdir(dizin)
    try:
        yol = kurucu.kur(spec)[0].run(threads=ISLEM_PARCACIGI, output=False)
    finally:
        os.chdir(eski)
    # Act
    sonuc = s.oku(yol)
    with openmc.StatePoint(yol) as sp:
        df = sp.get_tally(name=s.T_SPEKTRUM_YAKIT).get_pandas_dataframe()
    # Assert
    aki = sonuc["spektrum"]["yakit"][0]
    kontrol("70 grup", len(aki) == 70, "-> %d" % len(aki))
    kontrol("toplam = iki malzemenin toplami",
            abs(float(aki.sum()) - float(df["mean"].sum())) < 1e-9 * float(df["mean"].sum()))
    kontrol("f iki yakit malzemesini kapsar (0.8 < f < 1)", 0.8 < sonuc["faktorler"]["f"].ort < 1.0)
    if _qt() is not None:
        from arayuz.sonuc.spektrum import SpektrumKarti
        kart = SpektrumKarti()
        kart.sonuc_ayarla(yol)
        kontrol("kart cizdi (hata metni yok)", "okunamadı" not in kart.tablo.text())
        kart.deleteLater()


HIZLI = [test_spektrum_dizisi_malzemeler_uzerinden_toplanir, test_oku_y3siz_kismi_ve_sizintisiz,
         test_eksik_skor_sessiz_sifir_olmaz, test_ayar_dayanikliligi, test_tukenmede_y3_kapali,
         test_tukenme_hazirla_cubuk_cubuk_y3siz, test_dogrulama_bulgulari,
         test_spektrum_kapali_betik_bayt_bayt_ayni, test_betik_adlari_islevde,
         test_sonuc_karti_notlari_ve_hata_korumasi, test_ayar_karti_gecersiz_grup_uyarisi]
YAVAS = [test_iki_yakitli_pin_spektrum]
ZINCIR_GEREKEN = [test_tukenme_hazirla_cubuk_cubuk_y3siz]
VERI_GEREKEN = [test_tukenme_hazirla_cubuk_cubuk_y3siz]
