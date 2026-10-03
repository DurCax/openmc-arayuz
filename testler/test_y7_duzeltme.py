# -*- coding: utf-8 -*-
"""
 test_y7_duzeltme.py  --  v3 Y7 inceleme bulgulari (python-reviewer + profesor)

 HIZLI: kutu tablosunda eksik mesh sutunu / beklenmeyen bin adi acik hata;
        ozdegerde denge "istatistiksel" (tam degil) etiketi; foton acikken
        global sizinti karsilastirmasi gizli; heating-local uyarisi yalniz
        heating ile birlikteyse; yuzey tally adi tekilligi; betikte bilinmeyen
        filtre; denge tally'si eksik skor; tek sicaklikli veride KURESEL
        nearest; 0 K verisi; range karari degistirmez; onbellek anahtari yol;
        XML boyut/kodlama; y7_ oneki kosuyu durdurur; kuyruk dinleyici_cikar
        bagli yontem; tally_metni mesh tablolari bicimli; altin betik.
 YAVAS: ozdegerde kutu dengesi |artik| <= 3 sigma (pin hucre).
"""

import os
import re

import pytest

from cekirdek import sema
from testler.ortak_test import kontrol, ISLEM_PARCACIGI, KOK
from testler.regresyon_ortak import ORNEK

_ALTIN = os.path.join(KOK, "testler", "veri", "y7_altin_pinhucre.py")


def _veri_yoksa_atla():
    yol = os.environ.get("OPENMC_CROSS_SECTIONS", "")
    if not (yol and os.path.exists(yol)):
        pytest.skip("nukleer veri yok (OPENMC_CROSS_SECTIONS)")


def _kure(*filtreler, ad="kacak"):
    spec = sema.yukle(os.path.join(ORNEK, "zirh_kure.json"))
    spec["tallyler"] = [dict(sema.tally(ad, ["current"]), filtreler=list(filtreler))]
    return spec


# ---------------------------------------------------------------------------
# python-reviewer HIGH
# ---------------------------------------------------------------------------

def test_kutu_tablosunda_mesh_sutunu_yoksa_acik_hata():
    print("\n[Y7D-1] kutu_akimlari: mesh sutunu yok -> ValueError (StopIteration degil)")
    import pandas as pd
    from cekirdek import yuzey_akim as y
    # Arrange
    df = pd.DataFrame({"mean": [1.0], "std. dev.": [0.1]})
    # Act / Assert
    with pytest.raises(ValueError, match="mesh"):
        y.kutu_akimlari(df, (1, 1, 1))


def test_kutu_tablosunda_beklenmeyen_bin_adi_acik_hata():
    print("\n[Y7D-2] kutu_akimlari: 'x-min yan' gibi bilinmeyen bin -> ValueError")
    import pandas as pd
    from cekirdek import yuzey_akim as y
    # Arrange
    satir = {("mesh 1", "x"): 1, ("mesh 1", "y"): 1, ("mesh 1", "z"): 1,
             ("mesh 1", "surf"): "x-min yan", ("mean", ""): 1.0, ("std. dev.", ""): 0.1}
    df = pd.DataFrame([satir])
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    # Act / Assert
    with pytest.raises(ValueError, match="x-min yan"):
        y.kutu_akimlari(df, (1, 1, 1))


# ---------------------------------------------------------------------------
# fizik E1, D1, D2
# ---------------------------------------------------------------------------

def _kutu_sonucu():
    from cekirdek.spektrum import Deger as D
    yuz = {"giren": D(0.1, 0.01), "cikan": D(0.2, 0.01)}
    return {"ad": "kutu", "tur": "yuzey_kutu", "boyut": (1, 1, 1),
            "sinirlar": ([-1] * 3, [1] * 3),
            "yuzler": {"%s-%s" % (e, u): yuz for e in "xyz" for u in ("min", "max")},
            "giren": D(0.6, 0.02), "cikan": D(1.2, 0.03), "net_cikan": D(0.6, 0.04),
            "spektrum": None, "kaynak": D(1.0, 0.0),
            "terimler": {"A": D(0.41, 0.01), "U": D(0.01, 0.001), "X": D(0.01, 0.001),
                         "nuF": D(0.0, 0.0)},
            "denge": {"artik": D(0.0, 0.03), "bagil": 0.0}}


def test_ozdegerde_denge_istatistiksel_etiketli():
    print("\n[Y7D-3] notlar: sabit kaynakta 'her gecmiste tam', ozdegerde 'istatistiksel'")
    from arayuz.sonuc.yuzey import notlar
    # Act
    sabit = " ".join(notlar([_kutu_sonucu()], True, 1.0))
    ozdeger = " ".join(notlar([_kutu_sonucu()], False, 1.0))
    # Assert
    kontrol("sabit kaynak: tam", "her geçmişte tam" in sabit)
    kontrol("ozdeger: istatistiksel, tam denmez", "istatistiksel" in ozdeger
            and "her geçmişte tam" not in ozdeger, "-> %s" % ozdeger)
    kontrol("± 'yaklasik' (ust sinir denmez)", "üst sınır" not in sabit + ozdeger
            and "yaklaşık" in sabit)


def test_foton_acikken_global_sizinti_karsilastirilmaz():
    print("\n[Y7D-4] foton tasinimi acik: global sizinti fotonlari da sayar -> gosterilmez")
    import pandas as pd
    from cekirdek import yuzey_oku
    from cekirdek.spektrum import Deger

    class _T:
        name = "kacak"

        @staticmethod
        def get_pandas_dataframe():
            return pd.DataFrame({"surface": [1], "particle": ["neutron"], "nuclide": ["total"],
                                 "score": ["current"], "mean": [0.3], "std. dev.": [0.01]})
    # Act
    kapali = yuzey_oku._sinir_sonucu(_T(), Deger(0.3, 0.01), 1.0, foton_var=False)
    acik = yuzey_oku._sinir_sonucu(_T(), Deger(0.5, 0.01), 1.0, foton_var=True)
    # Assert
    kontrol("foton kapali: global sizinti var", kapali["global_sizinti"] is not None)
    kontrol("foton acik: global sizinti yok, isaretli",
            acik["global_sizinti"] is None and acik["global_foton_karisik"])


def test_heating_local_yalniz_heating_ile_birlikte_uyarilir():
    print("\n[Y7D-5] foton acik: heating-local tek basina uyari degil; heating ile birlikte uyari")
    from cekirdek.dogrula import y7
    # Arrange
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    spec["ayarlar"]["foton"] = {"var": True}
    spec["tallyler"] = [sema.tally("yerel", ["heating-local"])]
    # Act
    tek = y7.y7_kontrol(spec, veri_kontrolu=False)
    spec["tallyler"].append(sema.tally("toplam", ["heating"]))
    ikisi = y7.y7_kontrol(spec, veri_kontrolu=False)
    # Assert
    kontrol("tek basina uyari yok", not any("heating-local" in x.mesaj for x in tek),
            "-> %s" % [x.mesaj for x in tek])
    kontrol("heating ile birlikte uyari", any(x.seviye == "uyari" and "heating-local" in x.mesaj
                                               for x in ikisi), "-> %s" % [x.mesaj for x in ikisi])


# ---------------------------------------------------------------------------
# python-reviewer MEDIUM / LOW
# ---------------------------------------------------------------------------

def test_yuzey_tally_adi_tekil_olmali():
    print("\n[Y7D-6] iki yuzey tally'si ayni ad -> hata (y7_denge:<ad> cakismasi)")
    from cekirdek import yuzey_akim as y
    from cekirdek.dogrula import yuzey
    # Arrange
    spec = _kure(y.filtre_kutu([1, 1, 1]))
    spec["tallyler"].append(dict(sema.tally("kacak", ["current"]),
                                 filtreler=[y.filtre_sinir()]))
    # Act
    b = yuzey.yuzey_kontrol(spec)
    # Assert
    kontrol("hata", any(x.seviye == "hata" and "kacak" in x.mesaj for x in b),
            "-> %s" % [x.mesaj for x in b])


def test_betik_bilinmeyen_yuzey_filtresinde_hata():
    print("\n[Y7D-7] kod_uret: yuzey tally'sinde bilinmeyen filtre -> ValueError (kurucu gibi)")
    from cekirdek import yuzey_akim as y
    from cekirdek.kod_uret import yuzey as ky
    # Arrange
    spec = _kure(y.filtre_sinir(), {"tur": "malzeme", "adlar": ["su"]})
    t = spec["tallyler"][0]
    # Act / Assert
    with pytest.raises(ValueError):
        ky._filtre_satirlari(spec, t, (70.0, 70.0), [])


def test_denge_tallysinde_eksik_skor_none():
    print("\n[Y7D-8] denge tally'sinde skor eksikse terimler None (sessiz 0 degil)")
    import pandas as pd
    from cekirdek import yuzey_oku

    class _Tal:
        @staticmethod
        def get_pandas_dataframe():
            return pd.DataFrame({"score": ["absorption"], "mean": [1.0], "std. dev.": [0.1]})

    class _Sp:
        @staticmethod
        def get_tally(name):
            return _Tal()
    # Act
    t = yuzey_oku._denge_terimleri(_Sp(), "kutu", sabit=True)
    # Assert
    kontrol("None", t is None)


def test_tek_sicaklikli_veride_kuresel_nearest(monkeypatch):
    print("\n[Y7D-9] tek sicaklikli bir bilesen OpenMC'yi TUM model icin nearest'e dondurur")
    from cekirdek import sicaklik
    from cekirdek.dogrula import y7
    # Arrange: uo2 nuklidleri 600/900, biri tek sicaklik
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    spec["ayarlar"]["sicaklik_yontemi"] = "interpolation"
    next(m for m in spec["malzemeler"] if m["ad"] == "uo2")["sicaklik"] = 750.0

    def sahte(tur, ad, yol=None):
        return (293.6,) if ad == "O17" else (293.6, 600.0, 900.0, 1200.0)
    monkeypatch.setattr(sicaklik, "kutuphane_sicakliklari", sahte)
    # Act
    b = y7.y7_kontrol(spec, veri_kontrolu=True, kutuphane=None)
    # Assert
    kontrol("tek sicaklik bulgusu", any("O17" in x.mesaj and "nearest" in x.mesaj for x in b),
            "-> %s" % [x.mesaj for x in b])
    kontrol("750 K artik hata (kuresel nearest)", any(x.seviye == "hata" and "750" in x.mesaj
                                                       for x in b))


def test_sifir_kelvin_verisi_listede():
    print("\n[Y7D-10] 0 K verisi OpenMC'deki gibi listede (temps_available)")
    from cekirdek import sicaklik
    # Act
    k = sicaklik.degerlendir(5.0, (0.0, 293.6, 600.0), "nearest", 10.0)
    # Assert
    kontrol("5 K -> 0 K verisi (tolerans icinde)", k.kullanilan == (0,) and k.durum == "yakin")


def test_aralik_karari_degistirmez():
    print("\n[Y7D-11] range: aralik yuklense de OpenMC'nin T basina karari ayni (nuclide.cpp)")
    from cekirdek import sicaklik
    # Arrange
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    spec["ayarlar"]["sicaklik_yontemi"] = "nearest"
    spec["ayarlar"]["sicaklik"] = {"aralik": [294.0, 1200.0]}
    # Act
    a = sicaklik.ayar(spec)
    k = sicaklik.degerlendir(750.0, (293.6, 600.0, 900.0), a.yontem, a.tolerans)
    # Assert
    kontrol("hala yok (fatal)", k.durum == "yok")


def test_sicaklik_onbellegi_kutuphane_yoluna_bagli(gecici, monkeypatch):
    print("\n[Y7D-12] onbellek anahtari cozulmus kutuphane yolu: OPENMC_CROSS_SECTIONS degisirse yeniden okunur")
    from cekirdek import sicaklik
    # Arrange
    yol = os.path.join(gecici, "cross_sections.xml")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("<?xml version='1.0'?><cross_sections/>")
    # Act
    monkeypatch.setenv("OPENMC_CROSS_SECTIONS", yol)
    bos = sicaklik.kutuphane_sicakliklari("neutron", "U235")
    # Assert
    kontrol("sahte kutuphanede U235 yok -> None (eski onbellek kullanilmaz)", bos is None)


def test_xml_kodlama_ve_boyut_hatasi(gecici):
    print("\n[Y7D-13] bozuk kodlamali / asiri buyuk cross_sections.xml -> None (loglanir)")
    from cekirdek import sicaklik
    # Arrange
    bozuk = os.path.join(gecici, "bozuk.xml")
    with open(bozuk, "wb") as f:
        f.write(b"<?xml version='1.0' encoding='utf-8'?><a>\xff\xfe</a>")
    # Act / Assert
    kontrol("bozuk -> None", sicaklik.kutuphane_kayitlari(bozuk) is None)
    kontrol("boyut siniri adli sabit", sicaklik.XML_EN_BUYUK_BAYT > 0)


def test_y7_oneki_kosuyu_durdurur():
    print("\n[Y7D-14] 'y7_' onekli kullanici tally'si: dogrulama hatasi -> kosu baslamaz")
    from cekirdek import dogrula
    # Arrange
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    spec["tallyler"] = [sema.tally("y7_benim", ["flux"])]
    # Act
    b = dogrula.tum_kontroller(spec, veri_kontrolu=False)
    # Assert
    kontrol("hata_var", dogrula.hata_var(b))


# ---------------------------------------------------------------------------
# ortak hatalar (K4 bildirdi)
# ---------------------------------------------------------------------------

def test_kuyruk_dinleyici_cikar_bagli_yontem():
    print("\n[Y7D-15] kuyruk.dinleyici_cikar: her obj._olay yeni nesne -> == ile cikarilir")
    from cekirdek import kuyruk

    class _Dinleyen:
        def _olay(self, durum):
            pass
    # Arrange
    k = kuyruk.Kuyruk(en_fazla_paralel=1, is_parcacigi_butcesi=1)
    d = _Dinleyen()
    try:
        k.dinleyici_ekle(d._olay)
        # Act
        k.dinleyici_cikar(d._olay)
        # Assert
        kontrol("cikarildi", not k._dinleyiciler, "-> %r" % (k._dinleyiciler,))
    finally:
        k.kapat()


def _mesh_kosusu(dizin):
    import openmc
    os.makedirs(dizin, exist_ok=True)
    su = openmc.Material()
    su.add_nuclide("H1", 2)
    su.add_nuclide("O16", 1)
    su.set_density("g/cm3", 1.0)
    kure = openmc.Sphere(r=10, boundary_type="vacuum")
    geo = openmc.Geometry([openmc.Cell(fill=su, region=-kure)])
    s = openmc.Settings()
    s.run_mode, s.particles, s.batches = "fixed source", 200, 2
    s.source = openmc.IndependentSource(space=openmc.stats.Point(),
                                        energy=openmc.stats.Discrete([1e6], [1]))
    m = openmc.RegularMesh()
    m.lower_left, m.upper_right, m.dimension = (-5, -5, -5), (5, 5, 5), (2, 1, 1)
    t = {"m": [openmc.MeshFilter(m)], "me": [openmc.MeshFilter(m), openmc.EnergyFilter([0, 1, 2e7])],
         "ms": [openmc.MeshSurfaceFilter(m)]}
    tallyler = []
    for ad, f in t.items():
        tal = openmc.Tally(name=ad)
        tal.filters = f
        tal.scores = ["current"] if ad == "ms" else ["flux"]
        tallyler.append(tal)
    eski = os.getcwd()
    os.chdir(dizin)
    try:
        yol = openmc.Model(geo, openmc.Materials([su]), s,
                           openmc.Tallies(tallyler)).run(output=False, threads=ISLEM_PARCACIGI)
    finally:
        os.chdir(eski)
    with openmc.StatePoint(yol) as sp:
        return {ad: sp.get_tally(name=ad).get_pandas_dataframe() for ad in t}


def test_tally_metni_mesh_tablolari_bicimli(gecici):
    print("\n[Y7D-16] tally_metni: MeshFilter, +EnergyFilter, MeshSurfaceFilter bicimli tablo")
    _veri_yoksa_atla()
    from cekirdek import kosucu
    # Arrange
    tablolar = _mesh_kosusu(os.path.join(gecici, "mesh"))
    for ad, df in tablolar.items():
        # Act
        metin = kosucu.tally_metni(ad, df)
        # Assert
        kontrol("%s: bicimli baslik" % ad, "Bölge / enerji" in metin, "-> %s" % metin[:200])
        kontrol("%s: ag etiketi" % ad, "ağ" in metin)
    kontrol("ms: yuzey adi", "x-min out" in kosucu.tally_metni("ms", tablolar["ms"]))
    kontrol("me: enerji araligi", "MeV" in kosucu.tally_metni("me", tablolar["me"]))


def _betik_normal(metin):
    return re.sub(r"üretilmiştir \(\d{4}-\d{2}-\d{2}\)", "üretilmiştir (TARIH)", metin)


def test_y7_ayari_yoksa_betik_altinla_ayni():
    print("\n[Y7D-17] Y7 alani olmayan ornek: uretilen betik ana dalinkiyle bayt bayt ayni")
    from cekirdek import kod_uret
    # Arrange
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    with open(_ALTIN, encoding="utf-8") as f:
        altin = f.read()
    # Act
    kod = kod_uret.uret(spec, "model.py")
    # Assert
    kontrol("ayni", _betik_normal(kod) == _betik_normal(altin))


# ---------------------------------------------------------------------------
# YAVAS: ozdegerde kutu dengesi
# ---------------------------------------------------------------------------

def test_ozdeger_kutu_dengesi_istatistiksel(gecici):
    print("\n[Y7D-Y1] ozdeger (pin hucre): S = nuF/k ile kutu dengesi |artik| <= 3 sigma")
    from cekirdek import kurucu, yuzey_akim as y, yuzey_oku
    # Arrange
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    spec["ayarlar"].update(parcacik=5000, cevrim=40, pasif=10)
    spec["tallyler"] = [dict(sema.tally("kutu", ["current"]),
                             filtreler=[y.filtre_kutu([1, 1, 1], [-0.3, -0.3, -0.5],
                                                      [0.3, 0.3, 0.5])])]
    dizin = os.path.join(gecici, "pin")
    os.makedirs(dizin)
    eski = os.getcwd()
    os.chdir(dizin)
    try:
        yol = kurucu.kur(spec)[0].run(threads=ISLEM_PARCACIGI, output=False)
    finally:
        os.chdir(eski)
    # Act
    r = yuzey_oku.oku(yol, spec)[0]
    artik = r["denge"]["artik"]
    olcek = r["terimler"]["A"].ort
    print("  S=%.4f giren=%.4f cikan=%.4f U=%.5f A=%.4f artik=%.5f +- %.5f (bagil %.2e)"
          % (r["kaynak"].ort, r["giren"].ort, r["cikan"].ort, r["terimler"]["U"].ort,
             olcek, artik.ort, artik.sapma, artik.ort / olcek))
    # Assert
    kontrol("|artik| <= 3 sigma", abs(artik.ort) <= 3.0 * artik.sapma)
    kontrol("artik sifir degil (ozdegerde tam degil)", artik.ort != 0.0)


HIZLI = [test_kutu_tablosunda_mesh_sutunu_yoksa_acik_hata,
         test_kutu_tablosunda_beklenmeyen_bin_adi_acik_hata,
         test_ozdegerde_denge_istatistiksel_etiketli,
         test_foton_acikken_global_sizinti_karsilastirilmaz,
         test_heating_local_yalniz_heating_ile_birlikte_uyarilir,
         test_yuzey_tally_adi_tekil_olmali, test_betik_bilinmeyen_yuzey_filtresinde_hata,
         test_denge_tallysinde_eksik_skor_none, test_tek_sicaklikli_veride_kuresel_nearest,
         test_sifir_kelvin_verisi_listede, test_aralik_karari_degistirmez,
         test_sicaklik_onbellegi_kutuphane_yoluna_bagli, test_xml_kodlama_ve_boyut_hatasi,
         test_y7_oneki_kosuyu_durdurur, test_kuyruk_dinleyici_cikar_bagli_yontem,
         test_tally_metni_mesh_tablolari_bicimli, test_y7_ayari_yoksa_betik_altinla_ayni]
YAVAS = [test_ozdeger_kutu_dengesi_istatistiksel]
