# -*- coding: utf-8 -*-
"""
================================================================================
 test_regresyon.py  --  Cekirdek katman regresyon testleri
================================================================================

 KULLANIM
   python3 testler/test_regresyon.py            # tum testler (Monte Carlo dahil, ~2 dk)
   python3 testler/test_regresyon.py --hizli    # kosu gerektirmeyen testler (~10 s)

 TESTLER
   1. Dogrulama: temiz model temiz gecer
   2. Dogrulama: 14 bozuk model yakalanir (negatif testler)
   3. Geometri: uc ornegin olculeri analitik degerlerle uyusur
   4. Cizim: Model.plot() uc ornekte de calisir
   5. REGRESYON CIPASI: pin hucre k-inf = 1.3570 +/- 0.0020 (2 sigma icinde)
   6. BETIK ESDEGERLIGI: kurucu.py ve uretilen betik ayni k-eff'i verir

 5 ve 6 numarali testler bu katmanin dogru oldugunun tek gercek kanitidir.
 kurucu.py ya da kod_uret.py degistirilirse mutlaka tekrar kosulmalidir.
================================================================================
"""

import copy
import importlib.util
import os
import shutil
import sys
import tempfile
import warnings

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)
warnings.filterwarnings("ignore")

from cekirdek import sema, kurucu, dogrula, kod_uret       # noqa: E402

ORNEK = os.path.join(KOK, "ornekler")

# Regresyon cipasi -- arayuz gelistirilirken olculen referans
REFERANS_K = 1.3570
REFERANS_SAPMA = 0.0020

_gecti = []
_kaldi = []


def kontrol(baslik, kosul, ayrinti=""):
    if kosul:
        _gecti.append(baslik)
        print("  [GECTI] %s %s" % (baslik, ayrinti))
    else:
        _kaldi.append(baslik)
        print("  [KALDI] %s %s" % (baslik, ayrinti))
    return kosul


# ============================================================================
# 1-2. DOGRULAMA
# ============================================================================

def test_dogrulama_temiz():
    print("\n[1] Temiz modeller dogrulamadan hatasiz gecmeli")
    for ad in ("pwr_pinhucre", "pwr_17x17", "mtr_plaka", "sfr_altigen"):
        spec = sema.yukle(os.path.join(ORNEK, ad + ".json"))
        b = dogrula.tum_kontroller(spec)
        kontrol(ad, not dogrula.hata_var(b), "(%s)" % dogrula.ozet(b))


def test_dogrulama_negatif():
    print("\n[2] Bozuk modeller yakalanmali")
    temiz = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))

    def dene(baslik, degistir, anahtar):
        s = copy.deepcopy(temiz)
        degistir(s)
        b = dogrula.tum_kontroller(s)
        bulundu = any(anahtar.lower() in x.mesaj.lower() for x in b)
        kontrol(baslik, bulundu)

    def sab_sil(s):
        for m in s["malzemeler"]:
            if m["ad"] == "su":
                m["sab"] = []

    dene("S(a,b)'siz su", sab_sil, "S(a,b)")
    dene("yogunluk yok", lambda s: s["malzemeler"][0]["yogunluk"].update({"deger": None}), "yogunluk")
    dene("yaricap sirasi", lambda s: s["cubuklar"][0]["bolgeler"].__setitem__(0, sema.bolge(0.9, "uo2")), "artan sirada")
    dene("son bolge kapali", lambda s: s["cubuklar"][0]["bolgeler"].__setitem__(2, sema.bolge(0.8, "su")), "null olmali")
    dene("cubuk sigmiyor", lambda s: s["kor"].update({"adim": 0.5}), "adimindan")
    dene("tanimsiz malzeme", lambda s: s["cubuklar"][0]["bolgeler"].__setitem__(0, sema.bolge(0.39, "yok")), "tanimsiz malzeme")
    dene("olmayan nuklid", lambda s: s["malzemeler"][0].update({"bilesim": [sema.bilesen("Xx999", 1.0, tur="nuklid")]}), "nuklid")
    dene("olmayan S(a,b)", lambda s: s["malzemeler"][2].update({"sab": ["c_Yok"]}), "termal sacilma")
    dene("pasif >= cevrim", lambda s: s["ayarlar"].update({"pasif": 60, "cevrim": 60}), "pasif cevrim")
    dene("gecersiz sinir", lambda s: s["kor"]["sinir"].update({"yan": "xx"}), "gecersiz sinir")
    dene("vacuum sizinti", lambda s: s["kor"]["sinir"].update({"yan": "vacuum"}), "sizinti")
    dene("zenginlik araligi", lambda s: s["malzemeler"][0]["bilesim"][0].update({"zenginlik": 150.0}), "zenginligi")
    dene("yuksek zenginlik", lambda s: s["malzemeler"][0]["bilesim"][0].update({"zenginlik": 19.75}), "U234")
    dene("kafeste tanimsiz harf",
         lambda s: s.update({"demetler": [sema.demet("d", 1.26, [2, 2], ["yy", "yz"], {"y": "yakit_cubugu"}, "su")]}),
         "tanimsiz harf")
    dene("kafes satir uzunlugu",
         lambda s: s.update({"demetler": [sema.demet("d", 1.26, [3, 2], ["yy", "yy"], {"y": "yakit_cubugu"}, "su")]}),
         "karakter")


# ============================================================================
# 3-4. GEOMETRI VE CIZIM
# ============================================================================

def test_geometri_olculeri():
    print("\n[3] Geometri olculeri analitik degerlerle uyusmali")
    beklenen = {
        "pwr_pinhucre": (1.26, 1.26),
        "pwr_17x17": (17 * 1.26, 17 * 1.26),
        # 23 plaka * (2*0.038 + 0.051) + 24 kanal * 0.200  x  6.30 + 2*0.475
        "mtr_plaka": (23 * (2 * 0.038 + 0.051) + 24 * 0.200, 6.30 + 2 * 0.475),
    }
    for ad, (bx, by) in beklenen.items():
        spec = sema.yukle(os.path.join(ORNEK, ad + ".json"))
        _, bilgi = kurucu.kur(spec)
        gx, gy = bilgi["sinir_kutu"]
        uyum = abs(gx - bx) < 1e-9 and abs(gy - by) < 1e-9
        kontrol(ad, uyum, "olculen %.4f x %.4f, beklenen %.4f x %.4f" % (gx, gy, bx, by))


def test_cizim():
    print("\n[4] Model.plot() calismali")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for ad in ("pwr_pinhucre", "pwr_17x17", "mtr_plaka", "sfr_altigen"):
        spec = sema.yukle(os.path.join(ORNEK, ad + ".json"))
        model, bilgi = kurucu.kur(spec)
        try:
            model.plot(basis="xy", width=bilgi["sinir_kutu"], pixels=(200, 200),
                       color_by="material", colors=bilgi["renkler"])
            plt.close("all")
            kontrol(ad, True)
        except Exception as e:
            kontrol(ad, False, "-> %s" % e)


# ============================================================================
# 3b. ALTIGEN KAFES
# ============================================================================

def test_altigen_duzen():
    """altigen.py halka duzeni OpenMC'nin show_indices ciktisiyla uyusmali."""
    print("\n[3b] Altigen halka duzeni OpenMC ile uyusmali")
    import openmc
    import re as _re
    from cekirdek import altigen
    for yonelim in ("y", "x"):
        for n in (2, 3, 5):
            metin = openmc.HexLattice.show_indices(n, orientation=yonelim)
            omc = set()
            for satir in metin.split("\n"):
                for m in _re.finditer(r"\((\s*\d+),\s*(\d+)\)", satir):
                    omc.add((int(m.group(1)), int(m.group(2))))
            bizim = set(altigen.konumlar(n, yonelim))
            kontrol("yonelim=%s n=%d (%d hucre)" % (yonelim, n, altigen.toplam_hucre(n)),
                    omc == bizim)


def test_altigen_sinir():
    """HexagonalPrism duvarlari tum pinlere tam yarim adim mesafede olmali."""
    print("\n[3c] Altigen duct olcusu -- yarim adim aciklik")
    import math
    import openmc
    from cekirdek import altigen, kurucu

    def mesafeler(prizma, nokta):
        x, y = nokta
        cikti = []
        for ad in ("plane_max", "plane_min", "upper_right", "lower_left",
                   "upper_left", "lower_right"):
            yuzey = getattr(prizma, ad)
            if isinstance(yuzey, openmc.XPlane):
                a, b, d = 1.0, 0.0, yuzey.x0
            elif isinstance(yuzey, openmc.YPlane):
                a, b, d = 0.0, 1.0, yuzey.y0
            else:
                a, b, d = yuzey.a, yuzey.b, yuzey.d
            cikti.append(abs(d - (a * x + b * y)) / math.hypot(a, b))
        return cikti

    for yonelim in ("y", "x"):
        for n, p in ((2, 0.9), (7, 0.9), (10, 1.3)):
            prizma = kurucu._altigen_sinir(n, p, yonelim, "reflective")
            kon = altigen.konumlar(n, yonelim)
            en_yakin = min(min(mesafeler(prizma, (x * p, y * p)))
                           for x, y in kon.values())
            kontrol("yonelim=%s n=%d adim=%.1f" % (yonelim, n, p),
                    abs(en_yakin - p / 2.0) < 1e-9,
                    "en yakin duvar %.6f, beklenen %.6f" % (en_yakin, p / 2.0))


def test_ice_aktarma():
    """XML'e yazilip geri okunan malzemeler dogrulamadan gecmeli."""
    print("\n[3d] Malzeme ice aktarma (XML -> spec)")
    import tempfile
    from cekirdek import ice_aktar
    for ad in ("pwr_17x17", "sfr_altigen"):
        spec = sema.yukle(os.path.join(ORNEK, ad + ".json"))
        model, _ = kurucu.kur(spec)
        with tempfile.TemporaryDirectory() as gecici:
            yol = os.path.join(gecici, "materials.xml")
            model.materials.export_to_xml(yol)
            aktarilan, _notlar = ice_aktar.malzemeleri_oku(yol)
            yeni = sema.yeni_spec("t")
            yeni["malzemeler"] = aktarilan
            b = dogrula.malzeme_kontrol(yeni) + dogrula.nuklid_kontrol(yeni)
            kontrol("%s (%d malzeme)" % (ad, len(aktarilan)),
                    len(aktarilan) == len(spec["malzemeler"]) and not dogrula.hata_var(b),
                    "(%s)" % dogrula.ozet(b))


def test_sab_yanlis_alarm():
    """S(a,b) kontrolu karbon iceren alasimlarda yanlis alarm vermemeli."""
    print("\n[3e] S(a,b) yanlis alarm kontrolu")
    from cekirdek import malzeme_kutup as mk
    durumlar = [
        ("SS316 (%0.5 C)", mk.ss316(), False),
        ("B4C", mk.b4c(b10_zenginlik=90), False),
        ("SiC", mk.sic(), False),
        ("Helyum (gaz)", mk.helyum(), False),
        ("Su (S(a,b) yok)", dict(mk.su(), sab=[]), True),
        ("Grafit (S(a,b) yok)", dict(mk.grafit(), sab=[]), True),
        ("Su (S(a,b) var)", mk.su(), False),
    ]
    for ad, m, beklenen in durumlar:
        uyardi = bool(dogrula._sab_kontrol(m, "t"))
        kontrol(ad, uyardi == beklenen, "uyari=%s beklenen=%s" % (uyardi, beklenen))
    # grafit dogru etiketlenmeli ("polietilen" degil)
    b = dogrula._sab_kontrol(dict(mk.grafit(), sab=[]), "t")
    kontrol("grafit dogru tanimlanmis", b and "grafit" in b[0].mesaj)


# ============================================================================
# 5-6. MONTE CARLO (yavas)
# ============================================================================

def test_regresyon_cipasi(gecici):
    print("\n[5] REGRESYON CIPASI -- pin hucre k-inf")
    import openmc
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    dizin = os.path.join(gecici, "cipa")
    os.makedirs(dizin, exist_ok=True)
    eski = os.getcwd()
    try:
        os.chdir(dizin)
        model, _ = kurucu.kur(spec)
        k = openmc.StatePoint(model.run(threads=8, output=False)).keff
    finally:
        os.chdir(eski)
    fark = abs(k.nominal_value - REFERANS_K)
    sigma = (k.std_dev ** 2 + REFERANS_SAPMA ** 2) ** 0.5
    kontrol("k-inf = %.5f +/- %.5f (referans %.4f)" % (k.nominal_value, k.std_dev, REFERANS_K),
            fark < 2 * sigma, "-> %.2f sigma" % (fark / sigma))


def test_betik_esdegerligi(gecici):
    print("\n[6] BETIK ESDEGERLIGI -- kurucu.py ile uretilen betik ayni mi")
    import openmc
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    eski = os.getcwd()
    try:
        yol_a = os.path.join(gecici, "yol_a")
        os.makedirs(yol_a, exist_ok=True)
        os.chdir(yol_a)
        model_a, _ = kurucu.kur(spec)
        k_a = openmc.StatePoint(model_a.run(threads=8, output=False)).keff

        yol_b = os.path.join(gecici, "yol_b")
        os.makedirs(yol_b, exist_ok=True)
        os.chdir(yol_b)
        betik = os.path.join(yol_b, "model.py")
        with open(betik, "w", encoding="utf-8") as f:
            f.write(kod_uret.uret(spec, "model.py"))
        sm = importlib.util.spec_from_file_location("uretilen", betik)
        mod = importlib.util.module_from_spec(sm)
        sm.loader.exec_module(mod)
        k_b = openmc.StatePoint(mod.model.run(threads=8, output=False)).keff
    finally:
        os.chdir(eski)
    fark = abs(k_a.nominal_value - k_b.nominal_value)
    kontrol("kurucu %.8f  vs  betik %.8f" % (k_a.nominal_value, k_b.nominal_value),
            fark < 1e-10, "-> fark %.2e" % fark)


# ============================================================================
# ANA GIRIS
# ============================================================================

def test_altigen_betik_esdegerligi(gecici):
    print("\n[7] ALTIGEN BETIK ESDEGERLIGI")
    import openmc
    spec = sema.yukle(os.path.join(ORNEK, "sfr_altigen.json"))
    spec["ayarlar"].update(parcacik=2000, cevrim=30, pasif=10)
    eski = os.getcwd()
    try:
        ya = os.path.join(gecici, "hex_a"); os.makedirs(ya, exist_ok=True)
        os.chdir(ya)
        ma, _ = kurucu.kur(spec)
        ka = openmc.StatePoint(ma.run(threads=8, output=False)).keff
        yb = os.path.join(gecici, "hex_b"); os.makedirs(yb, exist_ok=True)
        os.chdir(yb)
        betik = os.path.join(yb, "model.py")
        with open(betik, "w", encoding="utf-8") as f:
            f.write(kod_uret.uret(spec, "model.py"))
        sm = importlib.util.spec_from_file_location("hexuret", betik)
        mo = importlib.util.module_from_spec(sm)
        sm.loader.exec_module(mo)
        kb = openmc.StatePoint(mo.model.run(threads=8, output=False)).keff
    finally:
        os.chdir(eski)
    fark = abs(ka.nominal_value - kb.nominal_value)
    kontrol("kurucu %.8f vs betik %.8f" % (ka.nominal_value, kb.nominal_value),
            fark < 1e-10, "-> fark %.2e" % fark)


def main(argv):
    hizli = "--hizli" in argv
    print("=" * 74)
    print(" openmc_arayuz cekirdek regresyon testleri%s" % (" (HIZLI MOD)" if hizli else ""))
    print("=" * 74)

    test_dogrulama_temiz()
    test_dogrulama_negatif()
    test_geometri_olculeri()
    test_altigen_duzen()
    test_altigen_sinir()
    test_ice_aktarma()
    test_sab_yanlis_alarm()
    test_cizim()

    if not hizli:
        gecici = tempfile.mkdtemp(prefix="openmc_arayuz_test_")
        try:
            test_regresyon_cipasi(gecici)
            test_betik_esdegerligi(gecici)
            test_altigen_betik_esdegerligi(gecici)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)
    else:
        print("\n[5-7] Monte Carlo testleri atlandi (--hizli)")

    print("\n" + "=" * 74)
    print(" SONUC: %d gecti, %d kaldi" % (len(_gecti), len(_kaldi)))
    if _kaldi:
        print(" KALAN TESTLER:")
        for t in _kaldi:
            print("   - %s" % t)
    print("=" * 74)
    return 1 if _kaldi else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
