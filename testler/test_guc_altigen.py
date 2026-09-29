# -*- coding: utf-8 -*-
"""
 test_guc_altigen.py  --  Altigen tam korda (altigen_kafes) guc haritasi

 HATA (D1-A bulgu 1, CRITICAL, olculdu): altigen_kafes korunda kor duzeyinde
 KAFES YOKTUR; demet konumlari `translation`li kok hucrelerdir
 (cekirdek/altigen_kor.py). guc.dagilim_oku anahtari yalniz kafes duzeylerinden
 kurdugu icin 7 demetin 133 cubugu 19 anahtara katlaniyordu (birlesen = 114):
 harita tek demet gosteriyor, F_dH yanlis (profesor olcumu: 1.066, dogrusu
 1.201), cubuk_sayisi 19 -> mutlak guc x7 fazla.

 HIZLI: gercek kurucu modeli + OpenMC'nin kendi DistribcellFilter DataFrame'i
        (nukleer veri ve openmc.lib YOK). Degerler yoldan BAGIMSIZ hesaplanir:
        demet sirasi kok hucre KIMLIK sirasindan (altigen_kor_hucreleri
        sozlesmesi: konum i, katman j -> i * katman_sayisi + j), cubuk konumu
        HexLattice.get_universe_index'ten.
 YAVAS: 7 demetli kor, tek yakit cubugu turu; merkez demet tam yakitli (sicak),
        cevre demetlerde yakitin bir kismi su ile degistirilmis.
"""

import math
import os
import re
import warnings
from types import SimpleNamespace

from testler.ortak_test import kontrol, ISLEM_PARCACIGI

warnings.filterwarnings("ignore")

PIN_ADIM = 1.275
PIN_HALKA = 3
R_YAKIT, R_ZARF = 0.3860, 0.4550
SQ3 = math.sqrt(3.0)
ZARF = (PIN_HALKA - 1) * PIN_ADIM * SQ3 + PIN_ADIM
KILIF_IC, KILIF_KAL, KILIF_BOSLUK = ZARF + 0.10, 0.15, 0.20


# ============================================================================
# model kurucular (test_altigen_kor ile ayni olculer; o dosya D1-B'nin)
# ============================================================================

def _malzemeler(sema):
    return [
        sema.malzeme("uo2", [sema.bilesen("U", 1.0, zenginlik=4.0),
                             sema.bilesen("O", 2.0)], 10.4, renk=(200, 60, 60)),
        sema.malzeme("zr", [sema.bilesen("Zr", 1.0)], 6.55, renk=(150, 150, 150)),
        sema.malzeme("su", [sema.bilesen("H", 2.0), sema.bilesen("O", 1.0)], 0.72,
                     sab=["c_H_in_H2O"], renk=(90, 140, 230)),
        sema.malzeme("celik", [sema.bilesen("Fe", 1.0)], 7.9, renk=(90, 90, 90)),
        sema.malzeme("b4c", [sema.bilesen("B", 4.0), sema.bilesen("C", 1.0)], 2.52,
                     renk=(40, 40, 40)),
    ]


def _demet(sema, ad="hex", harita=None, kilif=False):
    from cekirdek import altigen
    d = sema.demet_altigen(ad, PIN_ADIM, PIN_HALKA,
                           harita or altigen.bos_harita(PIN_HALKA, "y"),
                           {"y": "yakit_cubugu", "s": "su", "e": "b4c"}, "su", yonelim="y")
    if kilif:
        d["kilif"] = {"ic_duz": KILIF_IC, "kalinlik": KILIF_KAL, "malzeme": "celik"}
    return d


def _kor_spec(kilif=False, yansitici=False, harita=None, anahtar=None, demetler=None):
    """7 demetli altigen tam kor (kor 'x', demet 'y'); guc dagilimi acik."""
    from cekirdek import altigen, sema
    s = sema.yeni_spec("altigen kor guc")
    s["malzemeler"] = _malzemeler(sema)
    s["cubuklar"] = [sema.cubuk("yakit_cubugu", [sema.bolge(R_YAKIT, "uo2"),
                                                 sema.bolge(R_ZARF, "zr"),
                                                 sema.bolge(None, "su")])]
    s["demetler"] = demetler or [_demet(sema, kilif=kilif)]
    dis = (KILIF_IC + 2 * KILIF_KAL) if kilif else ZARF
    s["kor"].update(tur="altigen_kafes", demet=None,
                    adim=dis + (KILIF_BOSLUK if kilif else 0.0),
                    halka_sayisi=2, yonelim="x",
                    harita=harita or altigen.bos_harita(2, "A"),
                    anahtar=anahtar or {"A": "hex"})
    s["kor"]["sinir"] = {"yan": "vacuum" if yansitici else "reflective",
                         "alt": "reflective", "ust": "reflective"}
    s["kor"]["yansitici"] = {"var": yansitici, "kalinlik": 5.0, "malzeme": "su"}
    sema.kor_alanlarini_ayikla(s["kor"])
    s["guc_dagilimi"] = {"var": True, "cubuk": "yakit_cubugu", "bolge": 0,
                         "skor": "kappa-fission", "eksenel_dilim": 1, "toplam_guc": None}
    return s


def _katmanli(spec, dilim=2):
    """Iki eksenel katman, ikisi de ana harita: ayni demet iki kok hucresinde."""
    from cekirdek import sema
    spec["kor"]["eksenel"] = {"var": True, "bolgeler": [
        sema.eksenel_bolge("alt aktif", 20.0, None),
        sema.eksenel_bolge("ust aktif", 20.0, None)]}
    spec["guc_dagilimi"]["eksenel_dilim"] = dilim
    return spec


# ============================================================================
# sentetik statepoint: gercek geometri + OpenMC'nin DistribcellFilter DataFrame'i
# ============================================================================

class _SahteTally:
    def __init__(self, df):
        self._df = df

    def get_pandas_dataframe(self, paths=True):
        return self._df


def _yol_dataframe(model, hedef):
    """OpenMC'nin kendi DistribcellFilter.get_pandas_dataframe(paths=True) ciktisi."""
    import openmc
    model.geometry.determine_paths()
    f = openmc.DistribcellFilter(hedef)
    f._paths = list(hedef.paths)
    f._num_bins = len(hedef.paths)
    return f.get_pandas_dataframe(len(hedef.paths), 1, paths=True), list(hedef.paths)


def _sentetik_sp(model, deger, dilim=1):
    """deger(yol, ornek, z) -> ortalama. DataFrame satir duzeni OpenMC'ninki
    (distribcell yavas, mesh z hizli)."""
    import pandas as pd
    t = next(t for t in model.tallies if t.name == "guc_dagilimi")
    hedef = model.geometry.get_all_cells()[int(t.filters[0].bins[0])]
    yol_df, yollar = _yol_dataframe(model, hedef)
    yol_sut = [c for c in yol_df.columns if isinstance(c, tuple)]
    satirlar = []
    for i, yol in enumerate(yollar):
        for z in range(1, dilim + 1):
            s = [yol_df[c].iloc[i] for c in yol_sut] + [i]
            if dilim > 1:
                s += [1, 1, z]
            s += [deger(yol, i, z), 0.01]
            satirlar.append(s)
    sut = yol_sut + [("distribcell", "", "")]
    if dilim > 1:
        sut += [("mesh 1", "x", ""), ("mesh 1", "y", ""), ("mesh 1", "z", "")]
    sut += [("mean", "", ""), ("std. dev.", "", "")]
    df = pd.DataFrame(satirlar, columns=pd.MultiIndex.from_tuples(sut))
    return SimpleNamespace(get_tally=lambda name=None: _SahteTally(df),
                           summary=SimpleNamespace(geometry=model.geometry)), hedef, yollar


def _kok_sirasi(model):
    """Kok hucre kimligi -> (konum sirasi, katman sirasi): altigen_kor_hucreleri
    konum i, katman j icin hucreleri i*nk+j sirasinda kurar (sozlesme)."""
    kok = sorted(model.geometry.root_universe.cells.values(), key=lambda c: c.id)
    return {c.id: n for n, c in enumerate(kok)}


def _beklenen_anahtar(model, yol, nk, halka=2, yonelim="x"):
    """Yoldan BAGIMSIZ beklenen anahtar: (demet (halka, sira), cubuk (halka, sira))."""
    from cekirdek import altigen
    sira = _kok_sirasi(model)
    kok_hucre = int(re.match(r"u\d+->c(\d+)", yol).group(1))
    demet = sorted(altigen.konumlar(halka, yonelim))[sira[kok_hucre] // nk]
    lid, x, y = re.findall(r"l(\d+)\((-?\d+),(-?\d+)\)", yol)[-1]
    kafes = model.geometry.get_all_lattices()[int(lid)]
    cubuk = tuple(int(i) for i in kafes.get_universe_index((int(x), int(y))))[:2]
    return (demet, cubuk)


def _asimetrik(model, nk):
    """Deger = 100 * (demet no + 1) + cubuk no (her demet farkli)."""
    from cekirdek import altigen
    demet_no = {k: i for i, k in enumerate(sorted(altigen.konumlar(2, "x")))}
    cubuk_no = {k: i for i, k in enumerate(sorted(altigen.konumlar(PIN_HALKA, "y")))}

    def deger(yol, _i, _z):
        d, c = _beklenen_anahtar(model, yol, nk)
        return 100.0 * (demet_no[d] + 1) + cubuk_no[c]
    return deger


def _oku(spec, deger=None, dilim=1, nk=1):
    from cekirdek import guc, kurucu
    model, _b = kurucu.kur(spec)
    sp, hedef, yollar = _sentetik_sp(model, deger or _asimetrik(model, nk), dilim)
    return model, guc.dagilim_oku(sp), hedef, yollar


# ============================================================================
# HIZLI
# ============================================================================

def test_altigen_kor_133_anahtar():
    """7 demet x 19 cubuk: 133 ayri anahtar, tam kor, birlesme yok."""
    print("\n[GA1] Altigen tam kor: 133 anahtar (sentetik, gercek geometri)")
    from cekirdek import guc
    model, d, _h, yollar = _oku(_kor_spec())
    k = d["konumlar"]
    kontrol("133 distribcell ornegi", len(yollar) == 133, "-> %d" % len(yollar))
    kontrol("133 anahtar", len(k) == 133, "-> %d" % len(k))
    kontrol("tam_kor True", d.get("tam_kor") is True)
    kontrol("birlesen 0", d.get("birlesen_bin") == 0, "-> %r" % d.get("birlesen_bin"))
    kontrol("kor duzeyi oteleme", d.get("kor_duzeyi") == "oteleme",
            "-> %r" % d.get("kor_duzeyi"))
    kontrol("kafes_turleri [altigen, altigen]",
            d.get("kafes_turleri") == ["altigen", "altigen"], "-> %r" % d.get("kafes_turleri"))
    f = guc.tepe_faktorleri(d)
    kontrol("demet_sayisi 7", f.get("demet_sayisi") == 7, "-> %r" % f.get("demet_sayisi"))
    kontrol("cubuk_sayisi 133", f["cubuk_sayisi"] == 133)
    m = guc.mutlak_guc(f, 133.0e3)
    kontrol("mutlak guc: cubuk ortalamasi toplam/133",
            abs(m["cubuk_ortalama_W"] - 1000.0) < 1e-9, "-> %.3f" % m["cubuk_ortalama_W"])


def test_altigen_kor_asimetrik_konumlar():
    """Her demet farkli degerde: anahtar yoldan bagimsiz beklenenle ayni; merkez
    kok hucre otelemesine esit; cubuk merkezi nokta-hucre ile ayni ornege duser."""
    print("\n[GA2] Altigen tam kor: asimetrik harita, demet kimligi dogru konumda")
    from cekirdek import altigen, guc, altigen_kor
    model, d, hedef, yollar = _oku(_kor_spec())
    k = d["konumlar"]
    deger = _asimetrik(model, 1)
    hatali = [y for i, y in enumerate(yollar)
              if abs(k.get(_beklenen_anahtar(model, y, 1), {"toplam": (-1,)})["toplam"][0]
                     - deger(y, i, 1)) > 0]
    kontrol("her anahtarin degeri bagimsiz beklenenle ayni", not hatali,
            "-> %d hatali, ilk %r" % (len(hatali), hatali[:1]))
    P = _kor_spec()["kor"]["adim"]
    merkez = dict(zip(sorted(altigen.konumlar(2, "x")), altigen_kor.kor_merkezleri(2, P, "x")))
    uzak = max(math.hypot(guc.demet_merkezi(d, dm)[0] - merkez[dm][0],
                          guc.demet_merkezi(d, dm)[1] - merkez[dm][1]) for dm in merkez)
    kontrol("demet_merkezi = kor_merkezleri", uzak < 1e-9, "-> %.2e" % uzak)
    # nokta-hucre (saf Python Geometry.find): cubuk merkezi o anahtarin ornegine
    yanlis = 0
    for yol in yollar:
        a = _beklenen_anahtar(model, yol, 1)
        x, y = guc.cubuk_merkezi(d, a)
        bulunan = model.geometry.find((x, y, 0.0))
        kok = bulunan[1].id
        if bulunan[-1] is not hedef or kok != int(re.match(r"u\d+->c(\d+)", yol).group(1)):
            yanlis += 1
    kontrol("nokta-hucre: 133/133 cubuk merkezi dogru kok hucrede ve hedef hucrede",
            yanlis == 0, "-> %d yanlis" % yanlis)
    f = guc.tepe_faktorleri(d)
    kontrol("sicak demet: en buyuk demet no (merkez, (1, 0))", f["sicak_demet"] == (1, 0),
            "-> %r" % (f["sicak_demet"],))
    metin = guc.demet_metni(f["sicak_demet"], f)
    kontrol("demet metni halka", "halka" in metin, metin)
    kontrol("konum metni iki duzey",
            guc.konum_metni(f["sicak_cubuk"], None, f["kafes_turleri"]).count("halka") == 2)


def test_altigen_kor_katmanli():
    """Iki eksenel katman (ayni demet iki kok hucresi, ayni oteleme): 133 anahtar,
    katman ornekleri AYNI anahtarda birlesir."""
    print("\n[GA3] Altigen tam kor: eksenel katmanli")
    spec = _katmanli(_kor_spec())
    from cekirdek import kurucu
    model, _b = kurucu.kur(spec)
    asim = _asimetrik(model, 2)
    sira = _kok_sirasi(model)

    def deger(yol, i, z):
        katman = sira[int(re.match(r"u\d+->c(\d+)", yol).group(1))] % 2
        return asim(yol, i, z) if katman == z - 1 else 0.0
    from cekirdek import guc
    sp, _h, yollar = _sentetik_sp(model, deger, 2)
    d = guc.dagilim_oku(sp)
    k = d["konumlar"]
    kontrol("266 ornek (133 x 2 katman)", len(yollar) == 266, "-> %d" % len(yollar))
    kontrol("133 anahtar", len(k) == 133, "-> %d" % len(k))
    kontrol("birlesen > 0", d["birlesen_bin"] > 0, "-> %d" % d["birlesen_bin"])
    iyi = all(abs(v["eksenel"][0][0] - v["eksenel"][1][0]) < 1e-12 and v["eksenel"][0][0] > 0
              for v in k.values())
    kontrol("iki dilim de dolu (ust katmanin sifiri alt katmani ezmedi)", iyi)


def test_altigen_kor_kilif_ve_yansitici():
    print("\n[GA4] Altigen tam kor: kilifli ve yansiticili")
    for etiket, spec in (("kilifli", _kor_spec(kilif=True)),
                         ("yansiticili", _kor_spec(yansitici=True)),
                         ("kilifli + yansiticili", _kor_spec(kilif=True, yansitici=True))):
        model, d, _h, yollar = _oku(spec)
        k = d["konumlar"]
        dogru = all(_beklenen_anahtar(model, y, 1) in k for y in yollar)
        kontrol("%s: 133 anahtar, tam kor, birlesen 0" % etiket,
                len(k) == 133 and d["tam_kor"] and d["birlesen_bin"] == 0,
                "-> %d / %r / %r" % (len(k), d["tam_kor"], d["birlesen_bin"]))
        kontrol("%s: anahtarlar beklenen konumlarda" % etiket, dogru)


def test_altigen_kor_malzeme_konumu():
    """Bir demet konumu malzemeyle dolu (translation = None): 6 x 19 anahtar,
    halka numaralari DIS halkaya gore kalir (halka sayisi 2 bulunur)."""
    print("\n[GA5] Altigen tam kor: malzemeyle dolu konum")
    spec = _kor_spec(harita=["SAAAAA", "A"], anahtar={"A": "hex", "S": "su"})
    model, d, _h, yollar = _oku(spec)
    k = d["konumlar"]
    kontrol("114 anahtar", len(k) == 114, "-> %d" % len(k))
    demetler = {a[0] for a in k}
    kontrol("bos konum (0, 0) yok, digerleri dogru",
            (0, 0) not in demetler and demetler == {(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (1, 0)},
            "-> %r" % sorted(demetler))
    kontrol("anahtarlar beklenenle ayni",
            all(_beklenen_anahtar(model, y, 1) in k for y in yollar))


def test_altigen_kor_sifir_oteleme_summary():
    """summary.h5 (0, 0, 0) otelemeyi yazmaz (olculdu, MC): merkez demetin kok
    hucresi translation=None okunur. None yalniz hucrenin altigen merkezi (0, 0)
    ise sifir sayilir; baska bir konumda None ise ACIK hata."""
    print("\n[GA5b] Altigen tam kor: summary'de sifir oteleme (None)")
    from cekirdek import guc, kurucu
    model, _b = kurucu.kur(_kor_spec())
    kok = sorted(model.geometry.root_universe.cells.values(), key=lambda c: c.id)
    merkez = next(c for c in kok if c.translation is not None and not any(c.translation))
    merkez._translation = None          # summary okumasinin taklidi
    sp, _h, yollar = _sentetik_sp(model, _asimetrik(model, 1))
    d = guc.dagilim_oku(sp)
    kontrol("merkez None -> (0, 0): 133 anahtar", len(d["konumlar"]) == 133)
    kontrol("anahtarlar beklenenle ayni",
            all(_beklenen_anahtar(model, y, 1) in d["konumlar"] for y in yollar))
    kok[0]._translation = None          # dis halkada bir demet: None olamaz
    try:
        guc.dagilim_oku(sp)
        hata = None
    except RuntimeError as e:
        hata = str(e)
    kontrol("dis konumda oteleme yok -> acik RuntimeError", hata is not None
            and "öteleme" in hata, "-> %r" % hata)


def test_altigen_kor_farkli_demet_turleri():
    """Cevre demetlerinde yakitin bir kismi su: demet basina cubuk sayisi farkli."""
    print("\n[GA6] Altigen tam kor: farkli demet turleri (tek yakit cubugu)")
    from cekirdek import sema, guc
    seyrek = _demet(sema, "seyrek", harita=["ysysysysysys", "yyyyyy", "y"])
    spec = _kor_spec(harita=["BBBBBB", "A"], anahtar={"A": "hex", "B": "seyrek"},
                     demetler=[_demet(sema), seyrek])
    model, d, _h, yollar = _oku(spec)
    f = guc.tepe_faktorleri(d)
    dm = f["demetler"]
    kontrol("19 + 6 x 13 = 97 anahtar", len(d["konumlar"]) == 97, "-> %d" % len(d["konumlar"]))
    kontrol("merkez demet 19, cevre 13 cubuk",
            dm[(1, 0)]["cubuk_sayisi"] == 19
            and all(dm[(0, i)]["cubuk_sayisi"] == 13 for i in range(6)))


def test_kafesli_korlar_degismedi():
    """kare_kafes ve tek_demet anahtar bicimi aynen (kor duzeyi 'kafes'/None)."""
    print("\n[GA7] Kafesli kor ve tek demet: anahtarlar degismedi")
    from cekirdek import guc, kurucu, sema
    from testler.test_guc_kor import _kor_spec_2x2
    spec = _kor_spec_2x2()
    model, _b = kurucu.kur(spec)
    sp, _h, yollar = _sentetik_sp(model, lambda y, i, z: 1.0 + i)
    d = guc.dagilim_oku(sp)
    kontrol("kare kor: 96 anahtar ((dx,dy),(x,y))",
            len(d["konumlar"]) == 96 and all(len(a) == 2 and isinstance(a[0], tuple)
                                             for a in d["konumlar"]))
    kontrol("kare kor: kor_duzeyi 'kafes'", d.get("kor_duzeyi") == "kafes")
    kontrol("kare kor: degerler ornek sirasinda bitwise",
            [v["toplam"][0] for v in d["konumlar"].values()] == [1.0 + i for i in range(96)])
    tek = sema.yukle(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "ornekler", "pwr_17x17.json"))
    tek["guc_dagilimi"] = dict(spec["guc_dagilimi"])
    model, _b = kurucu.kur(tek)
    sp, _h, yollar = _sentetik_sp(model, lambda y, i, z: 2.0 + i)
    d = guc.dagilim_oku(sp)
    kontrol("tek demet: (x, y) anahtarlar, tam_kor False",
            d["tam_kor"] is False and all(type(a[0]) is int for a in d["konumlar"]),
            "-> %r" % list(d["konumlar"])[:2])
    kontrol("tek demet: kor_duzeyi None", d.get("kor_duzeyi") is None)
    # tek konumlu altigen_kafes (1 halka) eski tek demet bicimini korur
    s1 = _kor_spec(harita=["A"])
    s1["kor"]["halka_sayisi"] = 1
    model, _b = kurucu.kur(s1)
    sp, _h, _y = _sentetik_sp(model, lambda y, i, z: 1.0)
    d = guc.dagilim_oku(sp)
    kontrol("1 halkali altigen_kafes: 19 anahtar, tek duzey", len(d["konumlar"]) == 19
            and d["tam_kor"] is False)


def test_arayuz_altigen_oteleme_cizimi():
    print("\n[GA8] Arayuz: altigen tam kor (oteleme) cizimi")
    from PySide6 import QtWidgets
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from cekirdek import guc
    from arayuz.guc_harita import GucHaritaWidget
    _m, d, _h, _y = _oku(_kor_spec())
    w = GucHaritaWidget()
    w.resize(900, 700)
    f = guc.tepe_faktorleri(d)
    w.sonuc_ayarla({"guc": {"dagilim": d, "faktorler": f, "korunum": 0.0}})
    w.olcek.setCurrentIndex(w.olcek.findData("demet"))
    kontrol("7 demet cizildi", len(w._ipucu_ogeleri) == 7, "-> %d" % len(w._ipucu_ogeleri))
    w.olcek.setCurrentIndex(w.olcek.findData("cubuk"))
    kontrol("133 cubuk cizildi", len(w._ipucu_ogeleri) == 133, "-> %d" % len(w._ipucu_ogeleri))
    x, y = guc.demet_merkezi(d, f["sicak_demet"])
    w.olcek.setCurrentIndex(w.olcek.findData("demet"))
    m = w.ipucu_metni(x, y) or ""
    kontrol("demet ipucu: 19 cubuk", "19" in m and "demet" in m, m)
    uyg  # noqa: B018


# ============================================================================
# YAVAS -- Monte Carlo
# ============================================================================

def test_altigen_kor_mc(gecici):
    """
    7 demet, TEK yakit cubugu turu. Merkez demet tam yakitli; cevre 6 demette
    dis halkanin her ikinci konumu B4C emici (6 konum). Beklenen: sicak demet
    merkezde; cevre demetler (simetrik) birbirine 3 sigma icinde; korunum.
    (Once su denendi: bu sik (az yavaslatilmis) demette su konumu komsu
    cubuklari ISITIR, cevre demetler sicak cikti -- 1.04 / merkez 0.84; olculdu.)
    """
    print("\n[GA9] Altigen tam kor (Monte Carlo)")
    from cekirdek import kosucu, sema
    seyrek = _demet(sema, "seyrek", harita=["yeyeyeyeyeye", "yyyyyy", "y"])
    spec = _kor_spec(harita=["BBBBBB", "A"], anahtar={"A": "hex", "B": "seyrek"},
                     demetler=[_demet(sema), seyrek])
    spec["ayarlar"].update(parcacik=20000, cevrim=60, pasif=20, tohum=7)
    spec["calistirma"]["is_parcacigi"] = ISLEM_PARCACIGI
    kosu = kosucu.calistir(spec, os.path.join(gecici, "altigen_mc"),
                           is_parcacigi=ISLEM_PARCACIGI)
    kontrol("kosu basarili", kosu["basarili"])
    s = kosucu.sonuc_oku(kosu["statepoint"])
    g = s.get("guc") or {}
    f = g.get("faktorler") or {}
    d = g.get("dagilim") or {}
    kontrol("97 cubuk", len(d.get("konumlar") or {}) == 97, "-> %r" % s.get("guc_hata"))
    kontrol("korunum |sum/ref - 1| < 1e-6", g.get("korunum") is not None
            and g["korunum"] < 1e-6, "-> %r" % g.get("korunum"))
    kontrol("sicak demet merkezde (1, 0)", f.get("sicak_demet") == (1, 0),
            "-> %r" % (f.get("sicak_demet"),))
    dm = f.get("demetler") or {}
    cevre = [dm[(0, i)]["ortalama"] for i in range(6) if (0, i) in dm]
    ort = sum(c[0] for c in cevre) / max(len(cevre), 1)
    sapma = [abs(c[0] - ort) / c[1] if c[1] else float("inf") for c in cevre]
    print("  F_dH = %.4f, F_demet = %.4f, cevre ortalamalari %s"
          % (f.get("F_dH", float("nan")), f.get("F_demet") or float("nan"),
             ["%.4f±%.4f" % c for c in cevre]))
    kontrol("6 cevre demeti birbirine 3 sigma icinde", len(cevre) == 6 and max(sapma) < 3.0,
            "-> maks %.2f sigma" % max(sapma or [float("inf")]))
    kontrol("F_demet > 1 (merkez sicak)", (f.get("F_demet") or 0) > 1.0)


HIZLI = [
    test_altigen_kor_133_anahtar, test_altigen_kor_asimetrik_konumlar,
    test_altigen_kor_katmanli, test_altigen_kor_kilif_ve_yansitici,
    test_altigen_kor_malzeme_konumu, test_altigen_kor_sifir_oteleme_summary,
    test_altigen_kor_farkli_demet_turleri,
    test_kafesli_korlar_degismedi, test_arayuz_altigen_oteleme_cizimi,
]
YAVAS = [test_altigen_kor_mc]
