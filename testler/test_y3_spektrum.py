# -*- coding: utf-8 -*-
"""
 test_y3_spektrum.py  --  v3 Y3: enerji spektrumu, dort faktor, spektral indeksler

 HIZLI: saf hesaplar el hesabiyla (oran belirsizligi, dort faktor, spektral
        indeksler, letarji basina aki), tally tanimlari, kurucu kancasi ve
        uretilen betigin AYNI tally'leri kurmasi (kosu yok).
 YAVAS: yansiticili pin hucrede (sonsuz kafes) eps*p*f*eta*c_xn = k-sonsuz
        (belirsizlik icinde), spektral indeksler ayni tally'lerden el hesabiyla;
        Godiva'da (vakum sinir) sizinti carpani ile k-eff; betik esdegerligi.
"""

import importlib.util
import math
import os

from cekirdek import sema
from testler.ortak_test import kontrol, ISLEM_PARCACIGI
from testler.regresyon_ortak import ORNEK

_GOR_TOL = 1e-12            # ayni sayilardan cebirsel ozdeslik (kayan nokta)
_K_SIGMA = 2.0              # "belirsizlik icinde": 2 sigma (yaklasik %95)
_TL_TOL = 1e-6              # ayni tahminci, ayni normalizasyon: yalniz yuvarlama farki


def _pin(var=True, grup="XMAS-172"):
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    spec["ayarlar"]["spektrum"] = {"var": var, "grup_yapisi": grup}
    return spec


def _yakin(a, b, tol=_GOR_TOL):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


# ---------------------------------------------------------------------------
# saf hesaplar
# ---------------------------------------------------------------------------

def test_oran_birinci_derece_belirsizlik():
    print("\n[Y3-1] oran: (s_r/r)^2 = (s_a/a)^2 + (s_b/b)^2 (korelasyon yok sayilir)")
    from cekirdek import spektrum as s
    # Arrange
    a, b = s.Deger(2.0, 0.02), s.Deger(4.0, 0.12)
    # Act
    r = s.oran(a, b)
    # Assert
    beklenen = 0.5 * math.sqrt(0.01 ** 2 + 0.03 ** 2)
    kontrol("oran degeri 0.5", _yakin(r.ort, 0.5))
    kontrol("oran sapmasi el hesabi", _yakin(r.sapma, beklenen), "-> %r" % (r,))
    kontrol("payda sifirsa None", s.oran(a, s.Deger(0.0, 0.0)) is None)
    f = s.fark(s.Deger(5.0, 0.3), s.Deger(1.0, 0.4))
    kontrol("fark: 4 +- 0.5", _yakin(f.ort, 4.0) and _yakin(f.sapma, 0.5))


def _hizlar():
    from cekirdek import spektrum as s
    return {"nF": s.Deger(1.30, 0.004), "A": s.Deger(1.00, 0.003),
            "X": s.Deger(0.002, 0.0001), "nF_th": s.Deger(1.05, 0.004),
            "A_th": s.Deger(0.66, 0.002), "A_yakit_th": s.Deger(0.60, 0.002),
            "L": s.Deger(0.0, 0.0)}


def test_dort_faktor_el_hesabi():
    print("\n[Y3-2] dort faktor: OpenMC tally-arithmetic tanimlari, el hesabi")
    from cekirdek import spektrum as s
    # Arrange
    h = _hizlar()
    # Act
    f = s.faktorleri_hesapla(h)
    # Assert
    kontrol("eps = nF / nF_th", _yakin(f["eps"].ort, 1.30 / 1.05))
    kontrol("p = A_th / A", _yakin(f["p"].ort, 0.66 / 1.00))
    kontrol("f = A_yakit_th / A_th", _yakin(f["f"].ort, 0.60 / 0.66))
    kontrol("eta = nF_th / A_yakit_th", _yakin(f["eta"].ort, 1.05 / 0.60))
    kontrol("carpim = nF / A (ozdeslik)", _yakin(f["carpim"].ort, 1.30 / 1.00))
    kontrol("carpim degeri = eps*p*f*eta",
            _yakin(f["carpim"].ort, f["eps"].ort * f["p"].ort * f["f"].ort * f["eta"].ort))
    kontrol("carpim sapmasi nF/A oranindan",
            _yakin(f["carpim"].sapma, s.oran(h["nF"], h["A"]).sapma))
    kontrol("c_xn = A / (A - X)", _yakin(f["c_xn"].ort, 1.0 / 0.998))
    kontrol("sizintisiz: P_NL = 1 kesin (sapma 0)", f["p_nl"] == s.Deger(1.0, 0.0))
    kontrol("k = nF / (A - X + L)", _yakin(f["k"].ort, 1.30 / 0.998))
    kontrol("k = carpim * c_xn * P_NL",
            _yakin(f["k"].ort, f["carpim"].ort * f["c_xn"].ort * f["p_nl"].ort))


def test_sizinti_carpani():
    print("\n[Y3-3] sizinti: P_NL = (A - X) / (A - X + L), k = nF / (A - X + L)")
    from cekirdek import spektrum as s
    # Arrange
    h = dict(_hizlar(), L=s.Deger(0.25, 0.002))
    # Act
    f = s.faktorleri_hesapla(h)
    # Assert
    kontrol("P_NL el hesabi", _yakin(f["p_nl"].ort, 0.998 / 1.248))
    kontrol("k el hesabi", _yakin(f["k"].ort, 1.30 / 1.248))
    kontrol("k = carpim*c_xn*P_NL",
            _yakin(f["k"].ort, f["carpim"].ort * f["c_xn"].ort * f["p_nl"].ort))


def test_hizli_sistemde_dort_faktor_tanimsiz():
    print("\n[Y3-4] termal fisyon yoksa (hizli sistem) eps/p/f/eta tanimsiz, k tanimli")
    from cekirdek import spektrum as s
    # Arrange
    h = dict(_hizlar(), nF_th=s.Deger(0.0, 0.0), A_th=s.Deger(0.0, 0.0),
             A_yakit_th=s.Deger(0.0, 0.0), L=s.Deger(0.4, 0.01))
    # Act
    f = s.faktorleri_hesapla(h)
    # Assert
    kontrol("eps, f, eta None", f["eps"] is None and f["f"] is None and f["eta"] is None)
    kontrol("k yine tanimli", f["k"] is not None and _yakin(f["k"].ort, 1.30 / 1.398))
    kontrol("yakit yoksa (A_yakit_th None) f ve eta None",
            s.faktorleri_hesapla(dict(_hizlar(), A_yakit_th=None))["f"] is None)


def test_spektral_indeksler_el_hesabi():
    print("\n[Y3-5] rho28, delta25, delta28, C* (CSEWG tanimlari) el hesabi")
    from cekirdek import spektrum as s
    # Arrange
    d = {"F25_th": s.Deger(0.457, 0.0015), "F25_epi": s.Deger(0.0701, 0.00015),
         "F28_th": s.Deger(4.9e-7, 1.6e-9), "F28_epi": s.Deger(0.0289, 0.0001),
         "C28_th": s.Deger(0.0709, 0.0002), "C28_epi": s.Deger(0.198, 0.0008)}
    # Act
    i = s.indeksleri_hesapla(d)
    # Assert
    kontrol("rho28 = C28_epi / C28_th", _yakin(i["rho28"].ort, 0.198 / 0.0709))
    kontrol("delta25 = F25_epi / F25_th", _yakin(i["delta25"].ort, 0.0701 / 0.457))
    kontrol("delta28 = F28 / F25", _yakin(i["delta28"].ort, (0.0289 + 4.9e-7) / (0.457 + 0.0701)))
    kontrol("C* = C28 / F25", _yakin(i["C*"].ort, (0.198 + 0.0709) / (0.457 + 0.0701)))
    beklenen = (0.198 / 0.0709) * math.hypot(0.0008 / 0.198, 0.0002 / 0.0709)
    kontrol("rho28 sapmasi el hesabi", _yakin(i["rho28"].sapma, beklenen))


def test_letarji_basina_aki():
    print("\n[Y3-6] letarji basina aki: phi_g / ln(E_ust / E_alt)")
    from cekirdek import spektrum as s
    # Arrange
    kenarlar = [1.0e-5, 1.0, 1.0e6]
    aki, sapma = [2.0, 4.0], [0.2, 0.1]
    # Act
    e, y, ys = s.letarji_basina(kenarlar, aki, sapma)
    # Assert
    du = (math.log(1.0 / 1.0e-5), math.log(1.0e6 / 1.0))
    kontrol("iki grup", len(y) == 2 and len(e) == 3)
    kontrol("deger el hesabi", _yakin(y[0], 2.0 / du[0]) and _yakin(y[1], 4.0 / du[1]))
    kontrol("sapma el hesabi", _yakin(ys[1], 0.1 / du[1]))
    e0, y0, _ys0 = s.letarji_basina([0.0, 1.0, 10.0], [1.0, 1.0], [0.0, 0.0])
    kontrol("alt kenar 0 olan grup atlanir (letarji sonsuz)", len(y0) == 1 and e0[0] == 1.0)


# ---------------------------------------------------------------------------
# ayar ve tally tanimlari
# ---------------------------------------------------------------------------

def test_ayar_varsayilan_ve_dogrulama():
    print("\n[Y3-7] ayar: varsayilan kapali, bilinmeyen grup yapisi acik hata")
    from cekirdek import spektrum as s
    # Arrange
    bos = sema.yeni_spec()
    # Act / Assert
    kontrol("varsayilan kapali", s.ayar(bos)["var"] is False)
    kontrol("varsayilan grup yapisi XMAS-172", s.ayar(bos)["grup_yapisi"] == "XMAS-172")
    kontrol("acik pin: etkin", s.etkin_mi(_pin()))
    try:
        s.ayar(_pin(grup="YOK-1"))
        hata = None
    except ValueError as e:
        hata = str(e)
    kontrol("bilinmeyen grup yapisi ValueError", hata is not None and "YOK-1" in hata)
    kontrol("termal kesim 0.625 eV", s.TERMAL_KESIM_EV == 0.625)


def test_tally_tanimlari():
    print("\n[Y3-8] tally tanimlari: kapaliyken bos; acikken toplam/termal/yakit/indeks/spektrum")
    from cekirdek import spektrum as s
    # Arrange / Act
    kapali = s.tally_tanimlari(_pin(var=False))
    tanim = {t["ad"]: t for t in s.tally_tanimlari(_pin())}
    # Assert
    kontrol("kapaliyken tally yok", kapali == ())
    kontrol("alti tally", set(tanim) == {s.T_TOPLAM, s.T_TERMAL, s.T_YAKIT_TERMAL,
                                         s.T_INDEKS, s.T_SPEKTRUM, s.T_SPEKTRUM_YAKIT},
            "-> %s" % sorted(tanim))
    kontrol("toplam: nu-fission, absorption ve (n,xn) kanallari (MT 11,16,17,24,25,30,37,41,42)",
            set(tanim[s.T_TOPLAM]["skorlar"]) == {"nu-fission", "absorption"}
            | {k for k, _x in s.XN_SKORLARI} and len(s.XN_SKORLARI) == 9)
    kontrol("termal sinirlar [0, 0.625]", tanim[s.T_TERMAL]["enerji"] == (0.0, 0.625))
    kontrol("yakit termal: uo2 malzemesi", tanim[s.T_YAKIT_TERMAL]["malzemeler"] == ("uo2",))
    kontrol("indeks: U235 + U238, fission + (n,gamma)",
            tanim[s.T_INDEKS]["nuklidler"] == ("U235", "U238")
            and set(tanim[s.T_INDEKS]["skorlar"]) == {"fission", "(n,gamma)"})
    kontrol("spektrum grup yapisi", tanim[s.T_SPEKTRUM]["grup_yapisi"] == "XMAS-172")
    hizli = sema.yukle(os.path.join(ORNEK, "godiva_kriter.json"))
    hizli["ayarlar"]["spektrum"] = {"var": True}
    adlar = {t["ad"] for t in s.tally_tanimlari(hizli)}
    kontrol("Godiva (HEU, U elementi): indeks tally'si var", s.T_INDEKS in adlar)


def _tally_ozeti(model):
    """{ad: (skorlar, nuklidler, [(filtre turu, bins)])} -- karsilastirma icin.
    Malzeme filtresi kimlik yerine malzeme ADIYLA (iki yolda kimlikler farkli)."""
    adlar = {m.id: m.name for m in model.materials}
    ozet = {}
    for t in model.tallies:
        if not (t.name or "").startswith("y3_"):
            continue
        filtreler = []
        for f in t.filters:
            if hasattr(f, "values") and type(f).__name__ == "EnergyFilter":
                filtreler.append(("enerji", tuple(round(float(v), 9) for v in f.values)))
            else:
                filtreler.append((type(f).__name__,
                                  tuple(sorted(adlar.get(int(b), str(b)) for b in f.bins))))
        ozet[t.name] = (tuple(t.scores), tuple(t.nuclides), tuple(filtreler))
    return ozet


def _betik_modeli(spec, dizin):
    from cekirdek import kod_uret
    yol = os.path.join(dizin, "model.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kod_uret.uret(spec, "model.py"))
    sm = importlib.util.spec_from_file_location("y3_uretilen", yol)
    mod = importlib.util.module_from_spec(sm)
    sm.loader.exec_module(mod)
    return mod.model


def test_kurucu_ve_betik_ayni_tallyler():
    print("\n[Y3-9] kurucu kancasi ve uretilen betik AYNI y3 tally'lerini kurar")
    import tempfile
    from cekirdek import kurucu
    # Arrange
    spec = _pin()
    # Act
    model, _b = kurucu.kur(spec)
    with tempfile.TemporaryDirectory() as d:
        eski = os.getcwd()
        os.chdir(d)
        try:
            betik = _betik_modeli(spec, d)
        finally:
            os.chdir(eski)
    a, b = _tally_ozeti(model), _tally_ozeti(betik)
    # Assert
    kontrol("kurucu 6 y3 tally'si", len(a) == 6, "-> %s" % sorted(a))
    kontrol("betik = kurucu (skor, nuklid, filtre)", a == b,
            "-> fark %s" % {k for k in set(a) | set(b) if a.get(k) != b.get(k)})
    kontrol("XMAS-172: 173 kenar", len(a["y3_spektrum"][2][0][1]) == 173)


def test_kapaliyken_model_degismez():
    print("\n[Y3-10] spektrum kapaliyken kurucu ve betik eskisi gibi (y3 tally'si yok)")
    from cekirdek import kurucu, kod_uret
    # Arrange
    spec = _pin(var=False)
    # Act
    model, _b = kurucu.kur(spec)
    kod = kod_uret.uret(spec, "model.py")
    # Assert
    kontrol("kurucuda y3 tally'si yok", not _tally_ozeti(model))
    kontrol("betikte y3 yok", "y3_" not in kod)


# ---------------------------------------------------------------------------
# YAVAS: Monte Carlo kabul testleri
# ---------------------------------------------------------------------------

def _kos(model, dizin):
    import openmc
    os.makedirs(dizin, exist_ok=True)
    eski = os.getcwd()
    os.chdir(dizin)
    try:
        return model.run(threads=ISLEM_PARCACIGI, output=False)
    finally:
        os.chdir(eski)


def _df_degeri(df, **kosul):
    sat = df
    for sutun, deger in kosul.items():
        sat = sat[sat[sutun] == deger]
    return float(sat["mean"].sum())


def test_pin_hucre_dort_faktor_k_sonsuz(gecici):
    print("\n[Y3-Y1] yansiticili pin hucre: eps*p*f*eta*c_xn = k-sonsuz (2 sigma)")
    import openmc
    from cekirdek import kurucu, spektrum as s
    # Arrange
    spec = _pin()
    spec["ayarlar"].update(parcacik=5000, cevrim=60, pasif=15)
    model, _b = kurucu.kur(spec)
    # Act
    yol = _kos(model, os.path.join(gecici, "pin"))
    sonuc = s.oku(yol)
    f, i = sonuc["faktorler"], sonuc["indeksler"]
    k = sonuc["keff"]
    # Assert
    kontrol("sizinti sifir (yansitici)", abs(sonuc["sizinti"].ort) < 1e-12)
    kontrol("carpim = eps*p*f*eta",
            _yakin(f["carpim"].ort, f["eps"].ort * f["p"].ort * f["f"].ort * f["eta"].ort, 1e-9))
    fark = abs(f["k"].ort - k.ort)
    sinir = _K_SIGMA * math.hypot(f["k"].sapma, k.sapma)
    print("  eps=%.4f p=%.4f f=%.4f eta=%.4f c_xn=%.5f  k_tally=%.5f+-%.5f  keff=%.5f+-%.5f"
          % (f["eps"].ort, f["p"].ort, f["f"].ort, f["eta"].ort, f["c_xn"].ort,
             f["k"].ort, f["k"].sapma, k.ort, k.sapma))
    kontrol("eps*p*f*eta*c_xn = k-sonsuz (2 sigma, korelasyonsuz birlesik)", fark <= sinir,
            "-> fark %.5f, sinir %.5f" % (fark, sinir))
    # Iki tahminci AYNI gecmislerden: farklari tek basina k-eff sapmasindan bile
    # kucuk dalgalanir. Korelasyonsuz sinir gevsek oldugu icin ek, siki denetim.
    kontrol("siki: fark <= 2 sigma(k-eff)", fark <= _K_SIGMA * k.sapma,
            "-> fark %.5f, sinir %.5f" % (fark, _K_SIGMA * k.sapma))
    kontrol("fiziksel aralik: 1 < eps < 1.5, 0.5 < p < 1, 0.8 < f < 1, 1.5 < eta < 2.2",
            1.0 < f["eps"].ort < 1.5 and 0.5 < f["p"].ort < 1.0 and 0.8 < f["f"].ort < 1.0
            and 1.5 < f["eta"].ort < 2.2)
    sp = openmc.StatePoint(yol)
    df = sp.get_tally(name=s.T_INDEKS).get_pandas_dataframe()
    eb = "energy low [eV]"
    c28e = _df_degeri(df, nuclide="U238", score="(n,gamma)", **{eb: s.TERMAL_KESIM_EV})
    c28t = _df_degeri(df, nuclide="U238", score="(n,gamma)", **{eb: 0.0})
    f25e = _df_degeri(df, nuclide="U235", score="fission", **{eb: s.TERMAL_KESIM_EV})
    f25t = _df_degeri(df, nuclide="U235", score="fission", **{eb: 0.0})
    f28 = _df_degeri(df, nuclide="U238", score="fission")
    kontrol("rho28 el hesabi", _yakin(i["rho28"].ort, c28e / c28t, 1e-9))
    kontrol("delta25 el hesabi", _yakin(i["delta25"].ort, f25e / f25t, 1e-9))
    kontrol("delta28 el hesabi", _yakin(i["delta28"].ort, f28 / (f25e + f25t), 1e-9))
    kontrol("C* el hesabi", _yakin(i["C*"].ort, (c28e + c28t) / (f25e + f25t), 1e-9))
    spk = sonuc["spektrum"]
    kontrol("spektrum: 172 grup, pozitif aki",
            len(spk["model"][0]) == 172 and float(spk["model"][0].sum()) > 0)
    _normalizasyon_ve_denge(sp, s)


def _normalizasyon_ve_denge(sp, s):
    """
    Kabulun SIKI kisimlari (korelasyonsuz 2 sigma siniri gevsektir):
      1. filtresiz nu-fission tracklength tally'si = global k-tracklength
         (ikisi de kaynak notronu basina AYNI tahminci; ~1e-6 bagil)
      2. notron dengesi (kaynak notronu basina): A - X + L = 1 (2 sigma)
    c_xn (X/A ~ %0.14) MC belirsizligiyle COZULEMEZ (A'nin sapmasi ~%0.2):
    yalniz analitik (el hesabi) testte dogrulanir.
    """
    df = sp.get_tally(name=s.T_TOPLAM).get_pandas_dataframe()
    nf = float(df[df["score"] == "nu-fission"]["mean"].iloc[0])
    ktl = [float(g["mean"]) for g in sp.global_tallies if g["name"] in (b"k-tracklength",
                                                                         "k-tracklength")][0]
    kontrol("nu-fission tally = global k-tracklength (1e-6 bagil)",
            abs(nf / ktl - 1.0) < _TL_TOL, "-> %.3e" % abs(nf / ktl - 1.0))
    h = s._hizlar_oku(sp, df, sp.get_tally(name=s.T_TERMAL).get_pandas_dataframe())
    denge = s.toplam(s.fark(h["A"], h["X"]), h["L"])
    print("  A - X + L = %.5f +- %.5f" % denge)
    kontrol("notron dengesi: A - X + L = 1 (2 sigma)",
            abs(denge.ort - 1.0) <= _K_SIGMA * denge.sapma,
            "-> %.5f +- %.5f" % denge)


def test_godiva_sizinti_carpani(gecici):
    print("\n[Y3-Y2] Godiva (vakum): k = nF/(A-X+L) = k-eff (2 sigma); termal faktor yok")
    from cekirdek import kurucu, spektrum as s
    # Arrange
    spec = sema.yukle(os.path.join(ORNEK, "godiva_kriter.json"))
    spec["ayarlar"].update(parcacik=4000, cevrim=50, pasif=15)
    spec["ayarlar"]["spektrum"] = {"var": True, "grup_yapisi": "CASMO-70"}
    model, _b = kurucu.kur(spec)
    # Act
    yol = _kos(model, os.path.join(gecici, "godiva"))
    sonuc = s.oku(yol)
    f, k = sonuc["faktorler"], sonuc["keff"]
    # Assert
    print("  P_NL=%.4f  k_tally=%.5f+-%.5f  keff=%.5f+-%.5f"
          % (f["p_nl"].ort, f["k"].ort, f["k"].sapma, k.ort, k.sapma))
    kontrol("sizinti > 0", sonuc["sizinti"].ort > 0.1)
    kontrol("P_NL < 1", f["p_nl"].ort < 1.0)
    fark = abs(f["k"].ort - k.ort)
    sinir = _K_SIGMA * math.hypot(f["k"].sapma, k.sapma)
    kontrol("k = carpim*c_xn*P_NL = k-eff (2 sigma)", fark <= sinir,
            "-> fark %.5f, sinir %.5f" % (fark, sinir))
    kontrol("siki: fark <= 2 sigma(k-eff)", fark <= _K_SIGMA * k.sapma,
            "-> fark %.5f, sinir %.5f" % (fark, _K_SIGMA * k.sapma))
    kontrol("hizli sistem: eta (termal) tanimsiz ya da termal pay ihmal",
            f["eta"] is None or sonuc["termal_fisyon_payi"] < 1e-3)
    import openmc
    with openmc.StatePoint(yol) as sp:
        _normalizasyon_ve_denge(sp, s)


def test_betik_esdegerligi_spektrum_acik(gecici):
    print("\n[Y3-Y3] spektrum acikken kurucu ve betik ayni k-eff ve ayni y3 sonucunu verir")
    import openmc
    from cekirdek import kurucu, spektrum as s
    # Arrange
    spec = _pin(grup="CASMO-70")
    spec["ayarlar"].update(parcacik=1000, cevrim=20, pasif=5)
    # Act
    ya = _kos(kurucu.kur(spec)[0], os.path.join(gecici, "a"))
    dizin_b = os.path.join(gecici, "b")
    os.makedirs(dizin_b, exist_ok=True)
    eski = os.getcwd()
    os.chdir(dizin_b)
    try:
        yb = _kos(_betik_modeli(spec, dizin_b), dizin_b)
    finally:
        os.chdir(eski)
    ka, kb = openmc.StatePoint(ya).keff, openmc.StatePoint(yb).keff
    sa, sb = s.oku(ya), s.oku(yb)
    # Assert
    kontrol("k-eff birebir", abs(ka.nominal_value - kb.nominal_value) < 1e-10)
    kontrol("dort faktor carpimi birebir",
            _yakin(sa["faktorler"]["carpim"].ort, sb["faktorler"]["carpim"].ort, 1e-10))


HIZLI = [test_oran_birinci_derece_belirsizlik, test_dort_faktor_el_hesabi, test_sizinti_carpani,
         test_hizli_sistemde_dort_faktor_tanimsiz, test_spektral_indeksler_el_hesabi,
         test_letarji_basina_aki, test_ayar_varsayilan_ve_dogrulama, test_tally_tanimlari,
         test_kurucu_ve_betik_ayni_tallyler, test_kapaliyken_model_degismez]
YAVAS = [test_pin_hucre_dort_faktor_k_sonsuz, test_godiva_sizinti_carpani,
         test_betik_esdegerligi_spektrum_acik]
