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
    for ad in ("pwr_pinhucre", "pwr_17x17", "mtr_plaka", "sfr_altigen",
                   "godiva_kriter"):
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
    for ad in ("pwr_pinhucre", "pwr_17x17", "mtr_plaka", "sfr_altigen",
                   "godiva_kriter"):
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
# 3f. KAYNAK YAKINSAMASI (Shannon entropisi)
# ============================================================================

def test_entropi_ayristirma():
    """Cevrim satiri ayristirici entropili ve entropisiz bicimi de tanimali."""
    print("\n[3f] Entropi cikti ayristirma (iki bicim)")
    from cekirdek.kosucu import cevrim_satiri
    durumlar = [
        ("entropisiz pasif", "        5/1    1.19846", (5, 1.19846, None, None)),
        ("entropisiz aktif", "       54/1    1.32041    1.36400 +/- 0.00368",
         (54, 1.32041, None, 1.364)),
        ("entropili pasif", "        5/1    1.22935    5.96734",
         (5, 1.22935, 5.96734, None)),
        ("entropili aktif", "       10/1    1.16569    5.94225    1.15720 +/- 0.00849",
         (10, 1.16569, 5.94225, 1.15720)),
    ]
    for ad, satir, beklenen in durumlar:
        r = cevrim_satiri(satir)
        ok = (r is not None and r["cevrim"] == beklenen[0]
              and abs(r["k"] - beklenen[1]) < 1e-9
              and ((r["entropi"] is None and beklenen[2] is None)
                   or (r["entropi"] is not None and abs(r["entropi"] - beklenen[2]) < 1e-9))
              and ((r["ortalama"] is None and beklenen[3] is None)
                   or (r["ortalama"] is not None and abs(r["ortalama"] - beklenen[3]) < 1e-9)))
        kontrol(ad, ok)
    for ad, satir in (("statepoint satiri", " Creating state point statepoint.60.h5..."),
                      ("zaman satiri", " Total time elapsed = 6.5384e+00 seconds")):
        kontrol("%s reddedilmeli" % ad, cevrim_satiri(satir) is None)


def test_entropi_yakinsama():
    """Yakinsama karari sentetik veride dogru olmali."""
    print("\n[3g] Kaynak yakinsamasi karari")
    import random
    from cekirdek.kosucu import entropi_yakinsama
    random.seed(7)

    def gurultu(n, taban, sigma):
        return [taban + random.gauss(0, sigma) for _ in range(n)]

    sabit = gurultu(30, 5.95, 0.01) + gurultu(70, 5.95, 0.01)
    kontrol("sabit entropi -> yakinsamis",
            entropi_yakinsama(sabit, 30)[0] is True)
    kayan = [5.50 + 0.015 * i + random.gauss(0, 0.01) for i in range(30)]
    kontrol("kayan entropi -> yakinsamamis",
            entropi_yakinsama(kayan + gurultu(70, 5.95, 0.01), 30)[0] is False)
    kontrol("pasif=2 -> karar verilemez",
            entropi_yakinsama(gurultu(40, 5.95, 0.01), 2)[0] is None)
    kontrol("entropi yok -> karar verilemez",
            entropi_yakinsama([None] * 40, 20)[0] is None)


def test_onbellek():
    """Model onbellegi ayni spec icin yeniden kurmamali, degisince kurmali."""
    print("\n[3h] Model onbellegi")
    from cekirdek import onbellek
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    m1, _ = onbellek.kur_onbellekli(spec)
    m2, _ = onbellek.kur_onbellekli(spec)
    kontrol("ayni spec -> ayni nesne", m1 is m2)
    import copy as _copy
    degisik = _copy.deepcopy(spec)
    degisik["kor"]["adim"] = 1.30
    m3, _ = onbellek.kur_onbellekli(degisik)
    kontrol("degisen spec -> yeni nesne", m3 is not m1)
    kontrol("kur_taze her zaman yeni", onbellek.kur_taze(spec)[0] is not m1)


# ============================================================================
# 3i. REAKTIVITE, TARAMA VE KRITIK ARAMA
# ============================================================================

def test_reaktivite():
    """rho = (k-1)/k ve belirsizlik yayilimi dogru olmali."""
    print("\n[3i] Reaktivite hesabi")
    from cekirdek.tarama import reaktivite
    for k, beklenen in ((1.0, 0.0), (1.05, 4761.9), (0.95, -5263.2)):
        r, _ = reaktivite(k, 0.001)
        kontrol("k=%.2f -> %.1f pcm" % (k, beklenen), abs(r - beklenen) < 0.1)
    # sigma_rho = sigma_k / k^2
    _, s = reaktivite(1.25, 0.001)
    kontrol("belirsizlik yayilimi", abs(s - 1e5 * 0.001 / 1.25 ** 2) < 1e-6)


def test_parametre_uygula():
    """Tarama parametreleri spec'i dogru degistirmeli, kaynagi bozmamali."""
    print("\n[3j] Parametre uygulama")
    from cekirdek import tarama
    from cekirdek import malzeme_kutup as mk
    spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    ilk_sicaklik = sema.malzeme_bul(spec, "su")["sicaklik"]

    y, _ = tarama.parametre_uygula(spec, "yakit_sicaklik", "uo2", 1100.0)
    kontrol("yakit sicakligi", sema.malzeme_bul(y, "uo2")["sicaklik"] == 1100.0)
    kontrol("kaynak spec bozulmadi",
            sema.malzeme_bul(spec, "su")["sicaklik"] == ilk_sicaklik)

    # sogutucu sicakligi: YOGUNLUK DA degismeli (en kritik davranis)
    y, _ = tarama.parametre_uygula(spec, "sogutucu_sicaklik", "su", 620.0)
    yeni_rho = sema.malzeme_bul(y, "su")["yogunluk"]["deger"]
    kontrol("sogutucu sicakligi yogunlugu da degistirdi",
            abs(yeni_rho - mk.su_yogunluk(620.0)) < 1e-9,
            "rho = %.4f" % yeni_rho)

    # void: rho0*(1-alfa)
    rho0 = sema.malzeme_bul(spec, "su")["yogunluk"]["deger"]
    y, _ = tarama.parametre_uygula(spec, "void_orani", "su", 40.0)
    kontrol("void %40 -> rho0*0.6",
            abs(sema.malzeme_bul(y, "su")["yogunluk"]["deger"] - rho0 * 0.6) < 1e-9)

    y, _ = tarama.parametre_uygula(spec, "zenginlik", "uo2", 4.5)
    z = [b.get("zenginlik") for b in sema.malzeme_bul(y, "uo2")["bilesim"]
         if b.get("zenginlik")]
    kontrol("zenginlik", z and abs(z[0] - 4.5) < 1e-9)

    y, _ = tarama.parametre_uygula(spec, "kafes_adim", "demet_17x17", 1.40)
    kontrol("kafes adimi", abs(sema.demet_bul(y, "demet_17x17")["adim"] - 1.40) < 1e-9)


def test_katsayi_uyumu():
    """Agirlikli dogrusal uyum bilinen bir egimi geri vermeli."""
    print("\n[3k] Katsayi uyumu (sentetik)")
    from cekirdek import tarama
    # rho(p) = -3.0 * p + 5000 pcm olacak sekilde k uret
    sonuclar = []
    for p in (0, 100, 200, 300, 400):
        rho = (5000.0 - 3.0 * p) / 1e5
        k = 1.0 / (1.0 - rho)
        sonuclar.append({"deger": float(p), "keff": k, "sapma": 1e-5})
    kats = tarama.katsayi(sonuclar)
    kontrol("egim -3.0 pcm/birim geri geldi",
            abs(kats["egim"] + 3.0) < 0.02, "olculen %.4f" % kats["egim"])
    kontrol("R2 ~ 1", kats["r2"] > 0.999)
    kontrol("tek nokta -> None", tarama.katsayi(sonuclar[:1]) is None)


def test_kritik_arama_kok_sarti():
    """Hedef aralik disindaysa arama EKSTRAPOLASYON YAPMAMALI."""
    print("\n[3l] Kritik arama kok sarti")
    from cekirdek import kritik_arama
    import tempfile as _t

    class SahteKosucu:
        """k(p) = 1.3 - 0.0001*p  -- gercek kosu yapmadan mantigi sinar."""
        @staticmethod
        def sahte(spec, tur, hedef, deger, dizin, is_parcacigi, taban):
            return 1.3 - 0.0001 * deger, 0.0005

    orj = kritik_arama._nokta_kos
    kritik_arama._nokta_kos = SahteKosucu.sahte
    try:
        spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
        # k(0)=1.3, k(1000)=1.2 -> hedef 1.0 aralikta DEGIL
        s = kritik_arama.ara(spec, "bor_ppm", "su", 0, 1000, _t.mkdtemp())
        kontrol("aralik disi -> reddetti", not s.basarili and "aralikta degil" in s.mesaj)
        # k(0)=1.3, k(5000)=0.8 -> hedef 1.0 aralikta
        s = kritik_arama.ara(spec, "bor_ppm", "su", 0, 5000, _t.mkdtemp())
        kontrol("aralik icinde -> buldu", s.basarili, "cozum=%.1f" % (s.cozum or -1))
        kontrol("cozum dogru (beklenen 3000)", s.basarili and abs(s.cozum - 3000) < 60,
                "cozum=%.1f" % (s.cozum or -1))
    finally:
        kritik_arama._nokta_kos = orj


def test_kuresel_kor():
    """Kuresel kor kurulmali ve olculeri dogru olmali."""
    print("\n[3m] Kuresel kor turu")
    spec = sema.yukle(os.path.join(ORNEK, "godiva_kriter.json"))
    b = dogrula.tum_kontroller(spec)
    kontrol("godiva dogrulamadan geciyor", not dogrula.hata_var(b),
            "(%s)" % dogrula.ozet(b))
    _, bilgi = kurucu.kur(spec)
    gx, gy = bilgi["sinir_kutu"]
    kontrol("sinir kutusu = 2 x yaricap", abs(gx - 2 * 8.7407) < 1e-9,
            "%.4f cm" % gx)
    # ters siralı kabuk -> hata
    import copy as _c
    bozuk = _c.deepcopy(spec)
    bozuk["kor"]["kabuklar"] = [sema.kabuk(9.0, "heu"), sema.kabuk(5.0, "heu")]
    b = dogrula.tum_kontroller(bozuk)
    kontrol("ters kabuk sirasi yakalandi",
            any("artan sirada" in x.mesaj for x in b))


def test_veri_sicaklik_araligi():
    """Veri kutuphanesi sicaklik araliklari okunabilmeli."""
    print("\n[3n] Veri kutuphanesi sicaklik araliklari")
    from cekirdek import veri_bilgi
    a = veri_bilgi.nuklid_araligi("U235")
    kontrol("U235 araligi okundu", a is not None and a[0] > 0 and a[1] > a[0],
            str(a))
    s = veri_bilgi.sab_araligi("c_H_in_H2O")
    kontrol("c_H_in_H2O araligi okundu", s is not None, str(s))
    kontrol("su S(a,b) araligi notrondan DAR",
            s is not None and a is not None and s[1] < a[1],
            "S(a,b) ust sinir %s < notron %s" % (s[1] if s else "?", a[1] if a else "?"))


def test_keff_yorumu():
    """k-eff yorumu dogru kritiklik durumunu vermeli."""
    print("\n[3o] k-eff yorumu")
    from cekirdek.kosucu import keff_yorumu
    d, _ = keff_yorumu(1.05, 0.001)
    kontrol("k=1.05 -> kritik ustu", "USTU" in d)
    d, _ = keff_yorumu(0.95, 0.001)
    kontrol("k=0.95 -> kritik alti", "ALTI" in d)
    d, _ = keff_yorumu(1.0001, 0.001)
    kontrol("k=1.0001 -> kritik", d.startswith("KRITIK ("))
    _, a = keff_yorumu(1.01, 0.0005, 0.0065)
    kontrol("dolar cinsinden verildi", "$" in a, a[:60])


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


def test_godiva_kriteri(gecici):
    """
    ICSBEP HEU-MET-FAST-001 (Godiva) kriteri: yayimlanmis k_eff = 1.0000 +/- 0.0010.

    Bu test regresyon cipasindan FARKLIDIR: cipa "kod kendiyle tutarli" der,
    bu test "sonuc gercekten dogru" der. Malzeme bilesimi, geometri, tesir
    kesiti kutuphanesi ve tasima zincirinin tamami bagimsiz bir olcume
    karsi sinanir.
    """
    print("\n[8] GODIVA KRITERI (ICSBEP HEU-MET-FAST-001)")
    import math
    import openmc
    spec = sema.yukle(os.path.join(ORNEK, "godiva_kriter.json"))
    spec["ayarlar"].update(parcacik=15000, cevrim=140, pasif=40)
    dizin = os.path.join(gecici, "godiva")
    os.makedirs(dizin, exist_ok=True)
    eski = os.getcwd()
    try:
        os.chdir(dizin)
        model, _ = kurucu.kur(spec)
        k = openmc.StatePoint(model.run(threads=8, output=False)).keff
    finally:
        os.chdir(eski)
    KRITER, KRITER_S = 1.0000, 0.0010
    fark = abs(k.nominal_value - KRITER)
    top = math.sqrt(k.std_dev ** 2 + KRITER_S ** 2)
    kontrol("k = %.5f +/- %.5f  (kriter %.4f +/- %.4f)"
            % (k.nominal_value, k.std_dev, KRITER, KRITER_S),
            fark < 2 * top, "-> %.2f sigma" % (fark / top))


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
    test_entropi_ayristirma()
    test_entropi_yakinsama()
    test_onbellek()
    test_reaktivite()
    test_parametre_uygula()
    test_katsayi_uyumu()
    test_kritik_arama_kok_sarti()
    test_kuresel_kor()
    test_veri_sicaklik_araligi()
    test_keff_yorumu()
    test_cizim()

    if not hizli:
        gecici = tempfile.mkdtemp(prefix="openmc_arayuz_test_")
        try:
            test_regresyon_cipasi(gecici)
            test_betik_esdegerligi(gecici)
            test_altigen_betik_esdegerligi(gecici)
            test_godiva_kriteri(gecici)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)
    else:
        print("\n[5-8] Monte Carlo testleri atlandi (--hizli)")

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
