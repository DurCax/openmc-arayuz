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
                   "godiva_kriter", "pwr_3b", "pwr_kontrol",
                   "tamburlu_kor"):
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
                   "godiva_kriter", "pwr_3b", "pwr_kontrol",
                   "tamburlu_kor"):
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
# 3p. GUC DAGILIMI
# ============================================================================

def test_distribcell_ornek_sayisi():
    """Yakit hucresi kafesteki yakit konumu sayisi kadar ornek vermeli."""
    print("\n[3p] Distribcell ornek sayisi")
    spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    model, _ = kurucu.kur(spec)
    g = model.geometry
    g.determine_paths()
    yakit = [c for c in g.get_all_cells().values()
             if hasattr(c.fill, "name") and "UO2" in str(c.fill.name)]
    kontrol("tek yakit hucresi bulundu", len(yakit) == 1)
    if yakit:
        # haritadaki 'y' harfi sayisi
        d = sema.demet_bul(spec, "demet_17x17")
        beklenen = sum(s.count("y") for s in d["harita"])
        kontrol("ornek sayisi haritadaki yakit sayisina esit",
                yakit[0].num_instances == beklenen,
                "%d ornek, haritada %d yakit" % (yakit[0].num_instances, beklenen))


def test_altigen_distribcell_koprusu():
    """(x,alfa) -> (halka,sira) cevrimi altigen.konumlar ile ortusmeli."""
    print("\n[3q] Altigen distribcell koprusu")
    import openmc
    from cekirdek import altigen
    m = openmc.Material(); m.add_element("U", 1, enrichment=19.75)
    m.set_density("g/cm3", 17.0)
    pin = openmc.model.pin([openmc.ZCylinder(r=0.32)], [m, None])
    dis = openmc.Universe(cells=[openmc.Cell(fill=None)])
    for yonelim in ("y", "x"):
        for N in (2, 3, 7):
            lat = openmc.HexLattice()
            lat.center = (0.0, 0.0); lat.pitch = (0.9,); lat.orientation = yonelim
            lat.outer = dis
            lat.universes = [[pin] * u for u in altigen.halka_uzunluklari(N)]
            cevrilen = {tuple(lat.get_universe_index(ix))
                        for ix in lat._natural_indices}
            kontrol("yonelim=%s N=%d" % (yonelim, N),
                    cevrilen == set(altigen.konumlar(N, yonelim)))


def test_tepe_faktorleri_sentetik():
    """tepe_faktorleri bilinen bir dagilimda dogru F_dH ve F_q vermeli."""
    print("\n[3r] Tepe faktorleri (sentetik)")
    from cekirdek import guc
    # 4 cubuk x 2 dilim; cubuk toplamlari 1,1,1,2 -> ortalama 1.25, F_dH = 1.6
    # yerel degerler 0.5,0.5 / 0.5,0.5 / 0.5,0.5 / 0.5,1.5 -> ort 0.625, F_q = 2.4
    konumlar = {
        (0, 0): {"eksenel": [(0.5, 0.01), (0.5, 0.01)], "toplam": (1.0, 0.014)},
        (1, 0): {"eksenel": [(0.5, 0.01), (0.5, 0.01)], "toplam": (1.0, 0.014)},
        (0, 1): {"eksenel": [(0.5, 0.01), (0.5, 0.01)], "toplam": (1.0, 0.014)},
        (1, 1): {"eksenel": [(0.5, 0.01), (1.5, 0.01)], "toplam": (2.0, 0.014)},
    }
    d = {"kafes_turu": "kare", "kafes": None, "eksenel_dilim": 2,
         "konumlar": konumlar, "notlar": []}
    f = guc.tepe_faktorleri(d)
    kontrol("F_dH = 1.6", abs(f["F_dH"] - 1.6) < 1e-9, "%.6f" % f["F_dH"])
    kontrol("F_q = 2.4", abs(f["F_q"] - 2.4) < 1e-9, "%.6f" % f["F_q"])
    kontrol("sicak cubuk (1,1)", f["sicak_cubuk"] == (1, 1))
    kontrol("sicak dilim 2.", f["sicak_dilim"] == ((1, 1), 1))
    ort = sum(v[0] for v in f["bagil"].values()) / len(f["bagil"])
    kontrol("bagil ortalama tam 1.000", abs(ort - 1.0) < 1e-12, "%.12f" % ort)
    # 2B: F_q tanimsiz
    d2 = {"kafes_turu": "kare", "kafes": None, "eksenel_dilim": 1,
          "konumlar": {k: {"eksenel": [v["toplam"]], "toplam": v["toplam"]}
                       for k, v in konumlar.items()}, "notlar": []}
    kontrol("2B -> F_q None", guc.tepe_faktorleri(d2)["F_q"] is None)


def test_mutlak_guc():
    """Mutlak guc ve lineer guc hesabi dogru olmali."""
    print("\n[3s] Mutlak guc")
    from cekirdek import guc
    f = {"cubuk_sayisi": 264, "F_dH": 1.10, "F_q": 1.80, "eksenel_dilim": 20}
    m = guc.mutlak_guc(f, 17.6e6, 366.0)
    kontrol("cubuk ortalama = P/N", abs(m["cubuk_ortalama_W"] - 17.6e6 / 264) < 1e-6)
    kontrol("lineer ortalama ~182 W/cm",
            abs(m["lineer_ortalama_W_cm"] - 17.6e6 / 264 / 366) < 1e-9,
            "%.1f W/cm" % m["lineer_ortalama_W_cm"])
    kontrol("lineer maks F_q ile olceklendi",
            abs(m["lineer_maks_W_cm"] - m["lineer_ortalama_W_cm"] * 1.80) < 1e-9)
    kontrol("guc yoksa None", guc.mutlak_guc(f, None, 366.0) is None)


def test_guc_dogrulama():
    """Guc dagilimi ayarlarindaki hatalar yakalanmali."""
    print("\n[3t] Guc dagilimi dogrulamasi")
    import copy as _c
    temiz = sema.yukle(os.path.join(ORNEK, "pwr_3b.json"))
    kontrol("temiz model hatasiz",
            not dogrula.hata_var(dogrula.tum_kontroller(temiz)))

    def dene(ad, degistir, anahtar):
        s = _c.deepcopy(temiz)
        degistir(s)
        b = dogrula.tum_kontroller(s)
        kontrol(ad, any(anahtar.lower() in x.mesaj.lower() for x in b))

    dene("gecersiz bolge", lambda s: s["guc_dagilimi"].update({"bolge": 99}),
         "gecersiz bolge")
    dene("fisil olmayan bolge", lambda s: s["guc_dagilimi"].update({"bolge": 2}),
         "fisil gorunmuyor")
    dene("enerji olmayan skor", lambda s: s["guc_dagilimi"].update({"skor": "fission"}),
         "ENERJI skoru")
    dene("2B'de F_q yok", lambda s: s["kor"].update({"yukseklik": None}),
         "F_q hesaplanamaz")
    dene("az eksenel dilim", lambda s: s["guc_dagilimi"].update({"eksenel_dilim": 3}),
         "KUCUK cikar")
    dene("uydurma skor", lambda s: s["tallyler"][0].update({"skorlar": ["yok-boyle"]}),
         "bilinen skorlar")


# ============================================================================
# 3u. KONTROL CUBUGU
# ============================================================================

def test_kontrol_cubugu_geometri():
    """Kontrol cubugu emici bolgeyi eksenel olarak ikiye bolmeli."""
    print("\n[3u] Kontrol cubugu geometrisi")
    spec = sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json"))
    _, bilgi = kurucu.kur(spec)
    u = bilgi["universeler"]["kontrol_cubugu"]
    c = sema.cubuk_bul(spec, "kontrol_cubugu")
    kontrol("hucre sayisi = bolge + 1 (eksenel bolme)",
            len(u.cells) == len(c["bolgeler"]) + 1,
            "%d hucre, %d bolge" % (len(u.cells), len(c["bolgeler"])))
    dolgular = [getattr(x.fill, "name", "") for x in u.cells.values()]
    kontrol("emici malzeme universe'de var", any("B4C" in d for d in dolgular))

    # daldirma -> uc konumu: universe'deki ZPlane'in GERCEK konumu olculur
    h = spec["kor"]["yukseklik"]
    import copy as _c
    import openmc

    def uc_konumu(universe):
        """Kontrol universe'undeki tek ZPlane'i bulur (cubugun ucu)."""
        bulunan = set()
        for hucre in universe.cells.values():
            if hucre.region is None:
                continue
            for y in hucre.region.get_surfaces().values():
                if isinstance(y, openmc.ZPlane):
                    bulunan.add(round(float(y.z0), 9))
        return bulunan

    for d, beklenen in ((0.0, h / 2), (25.0, h / 2 - 0.25 * h),
                        (50.0, 0.0), (100.0, -h / 2)):
        s = _c.deepcopy(spec)
        sema.cubuk_bul(s, "kontrol_cubugu")["daldirma"] = d
        _, b2 = kurucu.kur(s)
        z = uc_konumu(b2["universeler"]["kontrol_cubugu"])
        kontrol("daldirma %%%.0f -> uc z = %+.2f cm" % (d, beklenen),
                len(z) == 1 and abs(list(z)[0] - beklenen) < 1e-9,
                "olculen %s" % sorted(z))

    # 2B modelde HATA vermeli
    s2 = _c.deepcopy(spec)
    s2["kor"]["yukseklik"] = None
    try:
        kurucu.kur(s2)
        kontrol("2B modelde hata veriyor", False, "hata vermedi")
    except ValueError as e:
        kontrol("2B modelde hata veriyor", "3B model gerektirir" in str(e))


def test_kontrol_cubugu_parametre():
    """cubuk_daldirma parametresi dogru uygulanmali."""
    print("\n[3v] Kontrol cubugu tarama parametresi")
    from cekirdek import tarama
    spec = sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json"))
    kontrol("tarama turunde var", "cubuk_daldirma" in tarama.TURLER)
    y, _ = tarama.parametre_uygula(spec, "cubuk_daldirma", "kontrol_cubugu", 75.0)
    kontrol("daldirma uygulandi",
            abs(sema.cubuk_bul(y, "kontrol_cubugu")["daldirma"] - 75.0) < 1e-9)
    kontrol("kaynak spec bozulmadi",
            abs(sema.cubuk_bul(spec, "kontrol_cubugu")["daldirma"] - 0.0) < 1e-9)
    # kontrol olmayan cubukta reddetmeli
    try:
        tarama.parametre_uygula(spec, "cubuk_daldirma", "yakit_cubugu", 50.0)
        kontrol("kontrol olmayan cubugu reddediyor", False, "reddetmedi")
    except ValueError as e:
        kontrol("kontrol olmayan cubugu reddediyor", "kontrol cubugu degil" in str(e))
    # aralik disi
    for d in (-5.0, 150.0):
        try:
            tarama.parametre_uygula(spec, "cubuk_daldirma", "kontrol_cubugu", d)
            kontrol("daldirma %g reddedilmeli" % d, False, "reddedilmedi")
        except ValueError:
            kontrol("daldirma %g reddedildi" % d, True)


def test_kontrol_cubugu_dogrulama():
    """Kontrol cubugu ayar hatalari yakalanmali."""
    print("\n[3w] Kontrol cubugu dogrulamasi")
    import copy as _c
    temiz = sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json"))
    kontrol("temiz model hatasiz",
            not dogrula.hata_var(dogrula.tum_kontroller(temiz)))

    def dene(ad, degistir, anahtar):
        s = _c.deepcopy(temiz)
        degistir(s)
        b = dogrula.tum_kontroller(s)
        kontrol(ad, any(anahtar.lower() in x.mesaj.lower() for x in b))

    dene("2B model -> hata", lambda s: s["kor"].update({"yukseklik": None}),
         "3B model gerektirir")
    dene("daldirma araligi",
         lambda s: sema.cubuk_bul(s, "kontrol_cubugu").update({"daldirma": 150.0}),
         "daldirma")
    dene("gecersiz emici bolge",
         lambda s: sema.cubuk_bul(s, "kontrol_cubugu").update({"emici_bolge": 9}),
         "gecersiz emici bolge")
    dene("sogurucu olmayan emici",
         lambda s: sema.cubuk_bul(s, "kontrol_cubugu").update({"emici_bolge": 1}),
         "sogurucu icermiyor")
    dene("tanimsiz izleyici",
         lambda s: sema.cubuk_bul(s, "kontrol_cubugu").update(
             {"izleyici_malzeme": "yok_boyle"}), "tanimsiz izleyici")


def test_arama_tekrar_etmiyor():
    """Kritik arama ayni noktayi iki kez KOSMAMALI (parantez korumali yontem)."""
    print("\n[3x] Kritik arama: tekrar eden nokta yok")
    from cekirdek import kritik_arama
    import tempfile as _t
    cagrilar = []

    def sahte(spec, tur, hedef, deger, dizin, is_parcacigi, taban):
        cagrilar.append(deger)
        return 1.3 - 0.0001 * deger, 0.0005

    orj = kritik_arama._nokta_kos
    kritik_arama._nokta_kos = sahte
    try:
        spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
        s = kritik_arama.ara(spec, "bor_ppm", "su", 0, 5000, _t.mkdtemp())
        kontrol("cozum bulundu", s.basarili)
        yuvarlak = [round(x, 6) for x in cagrilar]
        kontrol("hicbir nokta tekrar edilmedi",
                len(yuvarlak) == len(set(yuvarlak)),
                "%d kosu, %d benzersiz" % (len(yuvarlak), len(set(yuvarlak))))
        kontrol("kok belirsizligi raporlandi", s.cozum_belirsizlik is not None)
    finally:
        kritik_arama._nokta_kos = orj


# ============================================================================
# 3y. KONTROL TAMBURU
# ============================================================================

def test_tambur_yerlesim():
    """Tambur yerlesimi ve psi acisi dogru olmali."""
    print("\n[3y] Tambur yerlesimi")
    import math
    from cekirdek import tambur
    t = {"sayi": 8, "yaricap": 4.0, "merkez_yaricap": 19.5,
         "emici_aci": 120.0, "donme": 0.0}
    yer = tambur.yerlesim(t)
    kontrol("tambur sayisi", len(yer) == 8)
    # her tamburda psi - azimut = 180 (emici kore bakiyor)
    tamam = True
    for x, y, psi in yer:
        fi = math.degrees(math.atan2(y, x)) % 360
        tamam &= abs(((psi - fi) % 360) - 180.0) < 1e-6
    kontrol("donme=0 -> psi = azimut + 180 (emici kore bakiyor)", tamam)
    # donme uygulanınca psi kadar kayar
    yer2 = tambur.yerlesim(dict(t, donme=90.0))
    kontrol("donme 90 -> psi 90 derece kayiyor",
            all(abs(((b[2] - a[2]) % 360) - 90.0) < 1e-6 for a, b in zip(yer, yer2)))
    # merkezden uzaklik sabit
    kontrol("tum tamburlar merkez yaricapinda",
            all(abs(math.hypot(x, y) - 19.5) < 1e-9 for x, y, _ in yer))


def test_tambur_geometri_kontrol():
    """Yerlesim hatalari yakalanmali."""
    print("\n[3z] Tambur geometri kontrolu")
    from cekirdek import tambur
    saglam = {"sayi": 8, "yaricap": 4.0, "merkez_yaricap": 19.5,
              "emici_ic_yaricap": 2.6, "emici_aci": 120.0, "donme": 0.0}
    kontrol("saglam yerlesim temiz",
            not tambur.geometri_kontrol(saglam, 14.0, 12.0))
    for ad, degisim, anahtar in (
            ("kora giriyor", {"merkez_yaricap": 16.0}, "kora giriyor"),
            ("yansiticidan tasiyor", {"merkez_yaricap": 24.0}, "tasiyor"),
            ("komsular cakisiyor", {"sayi": 20}, "cakisiyor"),
            ("emici ic yaricap buyuk", {"emici_ic_yaricap": 5.0}, "kucuk olmali")):
        h = tambur.geometri_kontrol(dict(saglam, **degisim), 14.0, 12.0)
        kontrol(ad, any(anahtar in x for x in h))


def test_tambur_kor():
    """Tamburlu kor kurulmali ve olculeri dogru olmali."""
    print("\n[3aa] Tamburlu kor")
    spec = sema.yukle(os.path.join(ORNEK, "tamburlu_kor.json"))
    b = dogrula.tum_kontroller(spec)
    kontrol("ornek dogrulamadan geciyor", not dogrula.hata_var(b),
            "(%s)" % dogrula.ozet(b))
    model, bilgi = kurucu.kur(spec)
    R = spec["kor"]["kor_yaricap"] + spec["kor"]["yansitici"]["kalinlik"]
    kontrol("sinir kutusu = 2 x dis yaricap",
            abs(bilgi["sinir_kutu"][0] - 2 * R) < 1e-9,
            "%.3f" % bilgi["sinir_kutu"][0])
    n = int(spec["kor"]["tambur"]["sayi"])
    kontrol("kok hucre sayisi = 1 kor + %d tambur + 1 yansitici" % n,
            len(model.geometry.root_universe.cells) == n + 2,
            "%d hucre" % len(model.geometry.root_universe.cells))

    # cakisan yerlesim kurulumda HATA vermeli
    import copy as _c
    bozuk = _c.deepcopy(spec)
    bozuk["kor"]["tambur"]["sayi"] = 24
    try:
        kurucu.kur(bozuk)
        kontrol("cakisan yerlesim reddediliyor", False, "reddetmedi")
    except ValueError as e:
        kontrol("cakisan yerlesim reddediliyor", "cakisiyor" in str(e))


def test_tambur_emici_yonu():
    """
    Emici yay GERCEKTEN dogru yone bakmali -- geometriye nokta sorgusu.
    (Bu, 'cell.rotation nesneyi mi cerceveyi mi donduruyor' sorusunu
    tahminle degil olcumle cozer.)
    """
    print("\n[3ab] Tambur emici yonu (nokta sorgusu)")
    import math
    import openmc
    spec = sema.yukle(os.path.join(ORNEK, "tamburlu_kor.json"))
    emici_ad = spec["kor"]["tambur"]["emici_malzeme"]

    def emici_acisi(donme, tambur_ix=0):
        import copy as _c
        s = _c.deepcopy(spec)
        s["kor"]["tambur"]["donme"] = donme
        model, bilgi = kurucu.kur(s)
        emici_mat = bilgi["malzemeler"][emici_ad]
        t = s["kor"]["tambur"]
        from cekirdek import tambur as _t
        x0, y0, _ = _t.yerlesim(t)[tambur_ix]
        r = (float(t["emici_ic_yaricap"]) + float(t["yaricap"])) / 2.0
        bulunan = []
        for a in range(0, 360, 2):
            x = x0 + r * math.cos(math.radians(a))
            y = y0 + r * math.sin(math.radians(a))
            try:
                yol = model.geometry.find((x, y, 0.0))
            except Exception:
                continue
            if any(isinstance(o, openmc.Cell) and o.fill is emici_mat for o in yol):
                bulunan.append(a)
        if not bulunan:
            return None
        sx = sum(math.cos(math.radians(a)) for a in bulunan)
        sy = sum(math.sin(math.radians(a)) for a in bulunan)
        return math.degrees(math.atan2(sy, sx)) % 360

    # 0. tambur +x ekseninde (azimut 0); emici kore bakmasi = 180 derece
    a0 = emici_acisi(0.0)
    kontrol("donme=0 -> emici KORE bakiyor (180 derece)",
            a0 is not None and abs(((a0 - 180.0) % 360)) < 12.0,
            "olculen %.1f derece" % (a0 if a0 is not None else -1))
    a180 = emici_acisi(180.0)
    kontrol("donme=180 -> emici DISA bakiyor (0 derece)",
            a180 is not None and min(a180, 360 - a180) < 12.0,
            "olculen %.1f derece" % (a180 if a180 is not None else -1))


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


def test_guc_esdegerlik_ve_korunum(gecici):
    """
    Guc dagilimli bir modelde:
      1. Cubuk guclerinin toplami filtresiz tally'ye ESIT olmali (haritalama
         hatasi toplami bozar -- en guclu kontrol).
      2. Uretilen betik ayni k-eff VE ayni tepe faktorlerini vermeli.
    """
    print("\n[9] GUC DAGILIMI: toplam korunumu + betik esdegerligi")
    import openmc
    from cekirdek import guc
    spec = sema.yukle(os.path.join(ORNEK, "pwr_3b.json"))
    spec["ayarlar"].update(parcacik=2500, cevrim=35, pasif=12)
    spec["guc_dagilimi"]["eksenel_dilim"] = 6

    def kos(dizin, betikten=False):
        os.makedirs(dizin, exist_ok=True)
        eski = os.getcwd()
        try:
            os.chdir(dizin)
            if betikten:
                betik = os.path.join(dizin, "model.py")
                with open(betik, "w", encoding="utf-8") as f:
                    f.write(kod_uret.uret(spec, "model.py"))
                sm = importlib.util.spec_from_file_location("gucuret", betik)
                mo = importlib.util.module_from_spec(sm)
                sm.loader.exec_module(mo)
                model = mo.model
            else:
                model, _ = kurucu.kur(spec)
            sp = openmc.StatePoint(model.run(threads=8, output=False))
        finally:
            os.chdir(eski)
        return sp

    sp_a = kos(os.path.join(gecici, "guc_a"))
    f_a = guc.tepe_faktorleri(guc.dagilim_oku(sp_a))
    dag_toplam = sum(k["toplam"][0]
                     for k in guc.dagilim_oku(sp_a)["konumlar"].values())
    ref = float(sp_a.get_tally(name="guc_toplam_ref")
                .get_pandas_dataframe()["mean"].sum())
    bagil = abs(dag_toplam / ref - 1.0)
    kontrol("toplam korunumu (bagil fark %.1e)" % bagil, bagil < 1e-9)

    sp_b = kos(os.path.join(gecici, "guc_b"), betikten=True)
    f_b = guc.tepe_faktorleri(guc.dagilim_oku(sp_b))
    kontrol("betik ayni F_dH (%.6f vs %.6f)" % (f_a["F_dH"], f_b["F_dH"]),
            abs(f_a["F_dH"] - f_b["F_dH"]) < 1e-10)
    kontrol("betik ayni F_q (%.6f vs %.6f)" % (f_a["F_q"], f_b["F_q"]),
            abs(f_a["F_q"] - f_b["F_q"]) < 1e-10)
    kontrol("betik ayni sicak cubuk", f_a["sicak_cubuk"] == f_b["sicak_cubuk"])
    kontrol("bagil ortalama 1.000",
            abs(sum(v[0] for v in f_a["bagil"].values()) / len(f_a["bagil"]) - 1.0) < 1e-12)


def test_kontrol_cubugu_fizik(gecici):
    """
    Kontrol cubugu daldirildikca k DUSMELI, ve uretilen betik ayni sonucu
    vermeli.
    """
    print("\n[10] KONTROL CUBUGU: daldirma -> k ve betik esdegerligi")
    import openmc
    from cekirdek import tarama
    spec = sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json"))
    spec["ayarlar"].update(parcacik=2500, cevrim=35, pasif=12)

    kler = []
    for d in (0.0, 100.0):
        s2, _ = tarama.parametre_uygula(spec, "cubuk_daldirma", "kontrol_cubugu", d)
        dizin = os.path.join(gecici, "kontrol_%d" % int(d))
        os.makedirs(dizin, exist_ok=True)
        eski = os.getcwd()
        try:
            os.chdir(dizin)
            model, _ = kurucu.kur(s2)
            kler.append(openmc.StatePoint(model.run(threads=8, output=False)).keff)
        finally:
            os.chdir(eski)
    kontrol("daldirma k'yi dusuruyor (%.5f -> %.5f)"
            % (kler[0].nominal_value, kler[1].nominal_value),
            kler[1].nominal_value < kler[0].nominal_value - 0.05)

    # betik esdegerligi (daldirma %50)
    s3, _ = tarama.parametre_uygula(spec, "cubuk_daldirma", "kontrol_cubugu", 50.0)
    sonuclar = []
    for ad, betikten in (("kk_a", False), ("kk_b", True)):
        dizin = os.path.join(gecici, ad)
        os.makedirs(dizin, exist_ok=True)
        eski = os.getcwd()
        try:
            os.chdir(dizin)
            if betikten:
                betik = os.path.join(dizin, "model.py")
                with open(betik, "w", encoding="utf-8") as f:
                    f.write(kod_uret.uret(s3, "model.py"))
                sm = importlib.util.spec_from_file_location("kkuret", betik)
                mo = importlib.util.module_from_spec(sm)
                sm.loader.exec_module(mo)
                model = mo.model
            else:
                model, _ = kurucu.kur(s3)
            sonuclar.append(openmc.StatePoint(model.run(threads=8, output=False)).keff)
        finally:
            os.chdir(eski)
    fark = abs(sonuclar[0].nominal_value - sonuclar[1].nominal_value)
    kontrol("betik ayni k (%.8f vs %.8f)"
            % (sonuclar[0].nominal_value, sonuclar[1].nominal_value), fark < 1e-10)


def test_tambur_fizik(gecici):
    """
    Tambur donmesi k'yi ARTIRMALI (0 = emici kore bakiyor = en dusuk k),
    ve uretilen betik ayni sonucu vermeli.
    """
    print("\n[11] TAMBUR: donme -> k ve betik esdegerligi")
    import openmc
    from cekirdek import tarama
    spec = sema.yukle(os.path.join(ORNEK, "tamburlu_kor.json"))
    spec["ayarlar"].update(parcacik=2500, cevrim=35, pasif=12)

    kler = []
    for d in (0.0, 180.0):
        s2, _ = tarama.parametre_uygula(spec, "tambur_donme", None, d)
        dizin = os.path.join(gecici, "tambur_%d" % int(d))
        os.makedirs(dizin, exist_ok=True)
        eski = os.getcwd()
        try:
            os.chdir(dizin)
            model, _ = kurucu.kur(s2)
            kler.append(openmc.StatePoint(model.run(threads=8, output=False)).keff)
        finally:
            os.chdir(eski)
    kontrol("donme 0 -> 180 k'yi ARTIRIYOR (%.5f -> %.5f)"
            % (kler[0].nominal_value, kler[1].nominal_value),
            kler[1].nominal_value > kler[0].nominal_value + 0.01)

    s3, _ = tarama.parametre_uygula(spec, "tambur_donme", None, 90.0)
    sonuclar = []
    for ad, betikten in (("tb_a", False), ("tb_b", True)):
        dizin = os.path.join(gecici, ad)
        os.makedirs(dizin, exist_ok=True)
        eski = os.getcwd()
        try:
            os.chdir(dizin)
            if betikten:
                betik = os.path.join(dizin, "model.py")
                with open(betik, "w", encoding="utf-8") as f:
                    f.write(kod_uret.uret(s3, "model.py"))
                sm = importlib.util.spec_from_file_location("tburet", betik)
                mo = importlib.util.module_from_spec(sm)
                sm.loader.exec_module(mo)
                model = mo.model
            else:
                model, _ = kurucu.kur(s3)
            sonuclar.append(openmc.StatePoint(model.run(threads=8, output=False)).keff)
        finally:
            os.chdir(eski)
    fark = abs(sonuclar[0].nominal_value - sonuclar[1].nominal_value)
    kontrol("betik ayni k (%.8f vs %.8f)"
            % (sonuclar[0].nominal_value, sonuclar[1].nominal_value), fark < 1e-10)


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
    test_distribcell_ornek_sayisi()
    test_altigen_distribcell_koprusu()
    test_tepe_faktorleri_sentetik()
    test_mutlak_guc()
    test_guc_dogrulama()
    test_kontrol_cubugu_geometri()
    test_kontrol_cubugu_parametre()
    test_kontrol_cubugu_dogrulama()
    test_arama_tekrar_etmiyor()
    test_tambur_yerlesim()
    test_tambur_geometri_kontrol()
    test_tambur_kor()
    test_tambur_emici_yonu()
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
            test_guc_esdegerlik_ve_korunum(gecici)
            test_kontrol_cubugu_fizik(gecici)
            test_tambur_fizik(gecici)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)
    else:
        print("\n[5-11] Monte Carlo testleri atlandi (--hizli)")

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
