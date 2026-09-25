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
  12. KAYNAK TAYFI: orneklenen ortalama = analitik ortalama
  13. ANALITIK ZAYIFLATMA: saf sogurucuda 1 - exp(-tau)
  14. EKSENEL HETEROJENLIK: katman yigini, uc ayri eksenel aralik
  15. EKSENEL betik esdegerligi + guc korunumu

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


# ============================================================================
# 12. KAYNAK TAYFI VE SABIT KAYNAK
# ============================================================================

def test_kaynak_tayfi():
    """
    Tayflarin PARAMETRELERI dogru yere gidiyor mu?
    Kurulan dagilim orneklenir ve ortalamasi ANALITIK degerle karsilastirilir.
    a ile b'nin yer degistirmesi gibi bir hata ancak boyle yakalanir --
    "hata vermedi" testi bunu gormez.
    """
    print("\n[12] KAYNAK TAYFI: orneklenen ortalama = analitik ortalama")
    import numpy as np
    from cekirdek import kaynak

    def orn(d, n=200000):
        x, w = d.sample(n, seed=12345)
        return float(np.average(np.asarray(x), weights=np.asarray(w)))

    a, b = 988.0e3, 2.249e-6
    d = kaynak.enerji_dagilimi({"tur": "watt", "a": a, "b": b})
    bekl = 1.5 * a + a * a * b / 4.0          # Watt tayfinin analitik ortalamasi
    olc = orn(d)
    kontrol("watt ortalamasi %.4f MeV (analitik %.4f)" % (olc / 1e6, bekl / 1e6),
            abs(olc - bekl) / bekl < 0.01)
    kontrol("watt ortalama_enerji() analitikle ayni",
            abs(kaynak.ortalama_enerji({"tur": "watt", "a": a, "b": b}) - bekl) < 1.0)

    th = 1.2932e6
    olc = orn(kaynak.enerji_dagilimi({"tur": "maxwell", "theta": th}))
    kontrol("maxwell ortalamasi %.4f MeV (analitik %.4f)" % (olc / 1e6, 1.5 * th / 1e6),
            abs(olc - 1.5 * th) / (1.5 * th) < 0.01)

    olc = orn(kaynak.enerji_dagilimi({"tur": "tek", "enerji": 14.1e6}))
    kontrol("tek enerjili kaynak tam 14.1 MeV veriyor", abs(olc - 14.1e6) < 1.0)

    # Muir/fuzyon genislemesi: D-T icin FWHM = 177*sqrt(kT[keV]) keV
    kt = 20.0e3
    x, w = kaynak.enerji_dagilimi(
        {"tur": "fuzyon", "e0": 14.08e6, "kutle_orani": 5.0,
         "iyon_sicaklik": kt}).sample(200000, seed=7)
    x = np.asarray(x)
    sigma = float(x.std())
    bekl_s = 177.0 * (kt / 1e3) ** 0.5 * 1e3 / 2.3548
    kontrol("fuzyon genislemesi sigma = %.1f keV (analitik %.1f)"
            % (sigma / 1e3, bekl_s / 1e3), abs(sigma - bekl_s) / bekl_s < 0.03)

    # ayrik cizgiler: Co-60
    ort = kaynak.ortalama_enerji({"tur": "ayrik",
                                  "noktalar": [[1.173e6, 0.5], [1.333e6, 0.5]]})
    kontrol("ayrik cizgi ortalamasi %.4f MeV" % (ort / 1e6), abs(ort - 1.253e6) < 1.0)

    # histogram: kenar/deger uzunlugu tutmuyorsa ACIK hata
    try:
        kaynak.enerji_dagilimi({"tur": "histogram", "kenarlar": [1.0, 2.0, 3.0],
                                "degerler": [1.0]})
        kontrol("histogram uzunluk hatasi yakalaniyor", False, "-> hata atmadi")
    except ValueError as e:
        kontrol("histogram uzunluk hatasi yakalaniyor", "2 deger olmali" in str(e))


def test_kaynak_betik_esleme():
    """enerji_dagilimi() ile enerji_kod() AYNI dagilimi uretmeli."""
    print("\n[12b] KAYNAK: nesne ile uretilen betik metni ayni dagilimi veriyor")
    import numpy as np
    import openmc                                              # noqa: F401
    from cekirdek import kaynak

    ornekler = [
        {"tur": "watt", "a": 1.1e6, "b": 3.0e-6},
        {"tur": "maxwell", "theta": 1.4e6},
        {"tur": "tek", "enerji": 2.45e6},
        {"tur": "ayrik", "noktalar": [[1.173e6, 0.5], [1.333e6, 0.5]]},
        {"tur": "histogram", "kenarlar": [1.0e5, 1.0e6, 1.0e7], "degerler": [1.0, 3.0]},
        {"tur": "fuzyon", "e0": 2.45e6, "kutle_orani": 4.0, "iyon_sicaklik": 10.0e3},
    ]
    for e in ornekler:
        a = kaynak.enerji_dagilimi(e)
        b = eval(kaynak.enerji_kod(e), {"openmc": __import__("openmc")})
        xa, wa = a.sample(30000, seed=3)
        xb, wb = b.sample(30000, seed=3)
        ayni = np.allclose(np.asarray(xa), np.asarray(xb))
        kontrol("enerji '%s' betik metni ile ayni" % e["tur"], ayni)
    for ac in ({"tur": "izotropik"},
               {"tur": "tek_yon", "yon": [0.0, 0.0, 1.0]},
               {"tur": "koni", "yon": [1.0, 0.0, 0.0], "koni_aci": 15.0}):
        a = kaynak.aci_dagilimi(ac)
        b = eval(kaynak.aci_kod(ac), {"openmc": __import__("openmc")})
        ayni = type(a) is type(b) and a.to_xml_element().attrib == b.to_xml_element().attrib
        kontrol("aci '%s' betik metni ile ayni" % ac["tur"], ayni)


def test_kaynak_yonu():
    """
    ACISAL DAGILIM GERCEKTEN OLCULUYOR.

    Yonu tarif etmek yetmiyor: OpenMC'nin kendi ornekleyicisinden parcacik
    cekilip yonleri sayiliyor. Bu test bir hatayi zaten yakaladi -- koni
    kaynagi +x yonunde kuruldugunda OpenMC "referans vektorler paralel"
    diye cokuyordu, cunku ikinci referans vektorun varsayilani (1,0,0).
    """
    print("\n[12f] KAYNAK YONU: orneklenen parcaciklarin yonu olculuyor")
    import math
    import numpy as np
    spec = sema.yukle(os.path.join(ORNEK, "zirh_kure.json"))
    spec["ayarlar"]["kaynak"]["enerji"] = {"tur": "tek", "enerji": 14.1e6}
    eski_dizin = os.getcwd()
    gecici = tempfile.mkdtemp(prefix="kaynak_yon_")
    try:
        os.chdir(gecici)
        for yon in ([1, 0, 0], [0, 0, 1], [3, -4, 0]):
            b = np.array(yon, float)
            b /= np.linalg.norm(b)
            for tur, yari in (("tek_yon", 0.0), ("koni", 20.0)):
                spec["ayarlar"]["kaynak"]["aci"] = {
                    "tur": tur, "yon": yon, "koni_aci": yari or 30.0}
                model, _ = kurucu.kur(spec)
                u = np.array([p.u for p in
                              model.sample_external_source(20000, prn_seed=11)])
                eksen = u.mean(axis=0)
                eksen /= np.linalg.norm(eksen)
                genis = math.degrees(math.acos(float(np.clip((u @ b).min(), -1, 1))))
                kontrol("%s yon %s -> eksen dogru, en genis aci %.2f (istenen %.0f)"
                        % (tur, yon, genis, yari),
                        np.linalg.norm(eksen - b) < 0.01 and abs(genis - yari) < 0.5)
    finally:
        os.chdir(eski_dizin)
        shutil.rmtree(gecici, ignore_errors=True)


def test_kaynak_dogrulama():
    """Sabit kaynak modunun tuzaklari yakalaniyor mu?"""
    print("\n[12c] KAYNAK DOGRULAMA: sessizce anlamsiz kalan durumlar")
    from cekirdek import dogrula as dg

    def bul(spec, parca):
        b = dg.kaynak_kontrol(spec, veri_kontrolu=False)
        return [x for x in b if parca in x.mesaj]

    temel = sema.yukle(os.path.join(ORNEK, "zirh_kure.json"))

    s = copy.deepcopy(temel)
    s["tallyler"] = []
    v = bul(s, "hicbir tally")
    kontrol("sabit kaynakta tally yoksa HATA", v and v[0].seviye == "hata")

    s = copy.deepcopy(temel)
    s["ayarlar"]["kaynak"]["parcacik"] = "photon"
    s["ayarlar"]["mod"] = "eigenvalue"
    v = bul(s, "foton kaynagi ozdeger")
    kontrol("ozdeger modunda foton kaynagi HATA", v and v[0].seviye == "hata")

    s = copy.deepcopy(temel)
    s["ayarlar"]["kaynak"]["kuvvet"] = 0.0
    kontrol("sifir kaynak siddeti HATA", bool(bul(s, "siddeti pozitif")))

    s = copy.deepcopy(temel)
    s["ayarlar"]["kaynak"]["aci"] = {"tur": "tek_yon", "yon": [0.0, 0.0, 0.0]}
    kontrol("sifir yon vektoru HATA", bool(bul(s, "sifir vektor")))

    # nokta kaynak model disinda -- yuksekligi olan bir modelde
    s = sema.yukle(os.path.join(ORNEK, "pwr_3b.json"))
    h = s["kor"]["yukseklik"]
    s["ayarlar"]["kaynak"] = {"tur": "nokta", "konum": [0.0, 0.0, h]}
    kontrol("nokta kaynak geometri disinda HATA", bool(bul(s, "modelin disinda")))

    # enerji tavani: 40 MeV kaynak, ENDF/B-VIII.0 su+celik icin tavan 20 MeV
    s = copy.deepcopy(temel)
    s["ayarlar"]["kaynak"]["enerji"] = {"tur": "tek", "enerji": 40.0e6}
    v = [x for x in dg.kaynak_kontrol(s, veri_kontrolu=True)
         if "veri tavani" in x.mesaj]
    kontrol("kutuphane enerji tavani asilirsa HATA",
            bool(v) and v[0].seviye == "hata",
            "-> %s" % (v[0].mesaj if v else "bulgu yok"))

    # temiz model temiz gecmeli
    kontrol("zirh_kure temiz gecer",
            not dg.hata_var(dg.kaynak_kontrol(temel, veri_kontrolu=False)))


def test_sema_derin_birlestirme():
    """
    Eski bir dosyada 'kaynak' sozlugu var ama yeni alt alanlar yok.
    Sig update() bu durumda YENI ALANLARI SILIYORDU ve hata ancak
    kurucu.py'de KeyError olarak cikiyordu.
    """
    print("\n[12d] SEMA: eski dosyalar yeni ic ice alanlari aliyor mu")
    eski = {"ad": "eski", "kor": {"tur": "tek_cubuk"},
            "ayarlar": {"kaynak": {"tur": "nokta", "konum": [0, 0, 0]}}}
    s = sema.tamamla(eski)
    kontrol("kaynak.enerji varsayilani geldi",
            (s["ayarlar"]["kaynak"].get("enerji") or {}).get("tur") == "watt")
    kontrol("kaynak.aci varsayilani geldi",
            (s["ayarlar"]["kaynak"].get("aci") or {}).get("tur") == "izotropik")
    kontrol("kullanicinin kendi degeri korundu",
            s["ayarlar"]["kaynak"]["tur"] == "nokta")
    kontrol("kor.sinir varsayilani geldi",
            s["kor"].get("sinir", {}).get("yan") == "reflective")


def test_entropi_mesh_eksenel():
    """
    3B modelde entropi mesh'inin z sinirlari GERCEK yukseklik olmali.
    Onceden +/-1e10 sabitti; nz>1 istendiginde butun parcaciklar tek dilime
    dusuyor ve eksenel yakinsama olculmemis oluyordu.
    """
    print("\n[12e] ENTROPI MESH: eksenel sinirlar gercek yukseklikten geliyor")
    spec = sema.yukle(os.path.join(ORNEK, "pwr_3b.json"))
    spec["ayarlar"]["entropi_mesh"] = {"var": True, "boyut": [4, 4, 10]}
    h = float(spec["kor"]["yukseklik"])
    model, _ = kurucu.kur(spec)
    m = model.settings.entropy_mesh
    kontrol("mesh z alt siniri -H/2 (%.2f)" % (-h / 2),
            abs(m.lower_left[2] + h / 2) < 1e-9, "-> %.4g" % m.lower_left[2])
    kontrol("mesh z ust siniri +H/2 (%.2f)" % (h / 2),
            abs(m.upper_right[2] - h / 2) < 1e-9, "-> %.4g" % m.upper_right[2])
    # 2B modelde eksenel sinir yok: mesh genis kalmali
    spec2 = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    m2 = kurucu.kur(spec2)[0].settings.entropy_mesh
    kontrol("2B modelde mesh eksenel yonde genis kaliyor",
            m2.upper_right[2] > 1e9, "-> %.3g" % m2.upper_right[2])


def test_zayiflatma_analitik(gecici):
    """
    SAF SOGURUCU KUREDE ANALITIK KARSILASTIRMA.

    Merkezde monoenerjetik termal kaynak, cevresinde optik kalinligi tau=1
    olan B-10 kuresi. B-10'da termalde sacilma (2.1 b) sogurmanin (3847 b)
    yaninda ihmal edilebilir, dolayisiyla sogurulan kesir TAM OLARAK
        1 - exp(-tau) = 0.63212
    olmalidir. Bu tek test ayni anda sunlari dogrular: tek enerjili kaynagin
    enerjisi dogru, sabit kaynak modu calisiyor, tally normalizasyonu
    kaynak parcacigi basina.
    """
    print("\n[13] ANALITIK ZAYIFLATMA: 1 - exp(-tau) ile karsilastirma")
    import math
    import numpy as np
    import openmc

    E0 = 0.0253
    b10 = openmc.Material()
    b10.add_nuclide("B10", 1.0)
    b10.set_density("g/cm3", 2.34)
    N = b10.get_nuclide_atom_densities()["B10"]
    kit = openmc.data.DataLibrary.from_xml(os.environ["OPENMC_CROSS_SECTIONS"])
    nuc = openmc.data.IncidentNeutron.from_hdf5(kit.get_by_material("B10")["path"])
    sig_t = float(np.interp(E0, nuc[1].xs["294K"].x, nuc[1].xs["294K"].y))
    R = 1.0 / (N * sig_t)                      # tau = 1

    spec = sema.yeni_spec("B10 analitik")
    spec["malzemeler"] = [sema.malzeme(
        "b10", [{"tur": "nuklid", "isim": "B10", "miktar": 1.0, "birim": "ao"}],
        2.34, "g/cm3", 293.6)]
    spec["kor"].update({"tur": "kuresel", "yukseklik": None,
                        "kabuklar": [sema.kabuk(R, "b10")],
                        "sinir": {"yan": "vacuum", "alt": "vacuum", "ust": "vacuum"}})
    spec["ayarlar"].update({"mod": "fixed source", "parcacik": 50000,
                            "cevrim": 20, "pasif": 0,
                            "entropi_mesh": {"var": False, "boyut": [8, 8, 1]}})
    spec["ayarlar"]["kaynak"]["enerji"] = {"tur": "tek", "enerji": E0}
    spec["tallyler"] = [{"ad": "sog", "skorlar": ["absorption"],
                         "nuklidler": [], "filtreler": []}]

    eski = os.getcwd()
    yol = os.path.join(gecici, "b10")
    os.makedirs(yol, exist_ok=True)
    try:
        os.chdir(yol)
        model, _ = kurucu.kur(spec)
        sp_yolu = model.run(threads=8, output=False)
    finally:
        os.chdir(eski)
    with openmc.StatePoint(sp_yolu) as sp:
        t = list(sp.tallies.values())[0]
        olc = float(t.mean.ravel()[0])
        sap = float(t.std_dev.ravel()[0])
    bekl = 1.0 - math.exp(-1.0)
    z = abs(olc - bekl) / sap
    kontrol("sogurulan kesir %.5f +/- %.5f  (analitik %.5f)" % (olc, sap, bekl),
            z < 3.0, "-> %.2f sigma" % z)


def test_sabit_kaynak_betik(gecici):
    """
    Sabit kaynak modelinde de uretilen betik ayni sonucu vermeli.

    TEK IS PARCACIGIYLA kosulur ve BIT DUZEYINDE esitlik aranir. Sebep
    olculdu: OpenMP indirgemesi 8 is parcacigiyla ayni modeli iki kez
    kosunca bile ~6e-15 bagil fark uretiyor (kayan nokta toplama sirasi
    degisiyor), tek is parcacigiyla ise sonuc tekrarlanabilir. k-eff
    testlerinde bu gurultu 1e-10'luk pencereye sigiyor ama 1e11
    mertebesindeki bir tally degerinde sigmiyor.
    """
    print("\n[13b] SABIT KAYNAK BETIK ESDEGERLIGI (tek is parcacigi, bit esitligi)")
    import openmc
    spec = sema.yukle(os.path.join(ORNEK, "zirh_kure.json"))
    spec["ayarlar"]["parcacik"] = 4000
    spec["ayarlar"]["cevrim"] = 10

    def sog(sp_yolu):
        with openmc.StatePoint(sp_yolu) as sp:
            t = [x for x in sp.tallies.values() if x.name == "soğurma"][0]
            return float(t.mean.ravel()[0])

    eski = os.getcwd()
    try:
        ya = os.path.join(gecici, "zirh_a")
        os.makedirs(ya, exist_ok=True)
        os.chdir(ya)
        model_a, _ = kurucu.kur(spec)
        a = sog(model_a.run(threads=1, output=False))

        yb = os.path.join(gecici, "zirh_b")
        os.makedirs(yb, exist_ok=True)
        os.chdir(yb)
        betik = os.path.join(yb, "model.py")
        with open(betik, "w", encoding="utf-8") as f:
            f.write(kod_uret.uret(spec, "model.py"))
        sm = importlib.util.spec_from_file_location("zirhuret", betik)
        mod = importlib.util.module_from_spec(sm)
        sm.loader.exec_module(mod)
        b = sog(mod.model.run(threads=1, output=False))
    finally:
        os.chdir(eski)
    kontrol("kurucu %.17g vs betik %.17g" % (a, b), a == b,
            "-> bit duzeyinde %s" % ("ayni" if a == b else "FARKLI"))


def test_arayuz_kaynak_gidip_gelme():
    """
    Arayuz -> spec -> arayuz turu bilgi kaybetmemeli.

    Bu testin sebebi gercek bir hata: AyarSekmesi._kaydet() kaynak sozlugunu
    BASTAN YAZIYORDU, dolayisiyla kullanici nokta konumunu her degistirdiginde
    enerji tayfi, acisal dagilim, parcacik turu ve siddet siliniyordu.
    Arayuz yine de duzgun gorunuyordu -- kayip ancak kosuda ortaya cikardi.
    """
    print("\n[12g] ARAYUZ: kaynak ayarlari gidip gelmede korunuyor mu")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6 import QtWidgets
    except Exception as e:
        kontrol("PySide6 yok, arayuz testi atlandi", True, "-> %s" % e)
        return
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.sekme_ayar import AyarSekmesi

    spec = sema.yukle(os.path.join(ORNEK, "zirh_kure.json"))
    sekme = AyarSekmesi()
    sekme.spec = spec
    sekme._yukleniyor = True
    sekme.doldur()
    sekme._yukleniyor = False
    kontrol("dosyadaki fuzyon tayfi arayuze yansidi",
            sekme.tayf.currentData() == "fuzyon")
    kontrol("kaynak siddeti 1e12 okundu",
            abs(sekme.kaynak_kuvvet.deger() - 1.0e12) < 1.0)

    # nokta konumunu degistir: tayf ve siddet KAYBOLMAMALI
    sekme.kz.setValue(1.0)
    k = spec["ayarlar"]["kaynak"]
    kontrol("konum degisince enerji tayfi duruyor",
            (k.get("enerji") or {}).get("tur") == "fuzyon")
    kontrol("konum degisince siddet duruyor", abs(k.get("kuvvet", 0) - 1e12) < 1.0)
    kontrol("konum degisince acisal dagilim duruyor",
            (k.get("aci") or {}).get("tur") == "izotropik")

    # gecersiz tayf arayuzde acikca bildirilmeli, sessizce yutulmamali
    i = [j for j in range(sekme.tayf.count())
         if sekme.tayf.itemData(j) == "histogram"][0]
    sekme.tayf.setCurrentIndex(i)
    sekme.hist_kenar.setText("1e5, 1e6, 1e7")
    sekme.hist_deger.setText("1.0")
    sekme._kaydet()
    kontrol("gecersiz histogram arayuzde uyari veriyor",
            "kurulamadi" in sekme.tayf_ozet.text()
            and "color" in sekme.tayf_ozet.styleSheet())
    uyg  # noqa: B018  -- uygulama nesnesi yasasin diye


# ============================================================================
# 14. EKSENEL HETEROJENLIK
# ============================================================================

def _eksenel_spec():
    """pwr_3b uzerine uc katman: su / aktif / su."""
    spec = sema.yukle(os.path.join(ORNEK, "pwr_3b.json"))
    spec["kor"]["yukseklik"] = None
    spec["kor"]["eksenel"] = {"var": True, "bolgeler": [
        sema.eksenel_bolge("alt yansitici", 20.0, "su"),
        sema.eksenel_bolge("aktif", 366.0, None),
        sema.eksenel_bolge("ust yansitici", 20.0, "su"),
    ]}
    return spec


def test_eksenel_geometri():
    """
    Katman yigini dogru mu kuruluyor?

    En kritik nokta IC ARAYUZLERIN SINIR KOSULU: ic bir yuzeye yansitici
    sinir konsa korun ustu altindan KOPAR ve bunu k-eff'e bakarak fark etmek
    neredeyse imkansizdir. Bu yuzden her z duzleminin bc'si tek tek okunuyor.
    """
    print("\n[14] EKSENEL GEOMETRI: katman siniri ve sinir kosullari")
    spec = _eksenel_spec()
    h = sema.kor_yuksekligi(spec["kor"])
    kontrol("toplam yukseklik katman toplami (406 cm)", abs(h - 406.0) < 1e-9,
            "-> %g" % h)

    model, _ = kurucu.kur(spec)
    kok = model.geometry.root_universe
    kontrol("kok universe'de 3 katman hucresi var",
            {c.name for c in kok.cells.values()}
            == {"alt yansitici", "aktif", "ust yansitici"},
            "-> %s" % sorted(c.name for c in kok.cells.values()))
    # Fiziksel sira: ad degil z konumu belirleyici
    z_sirali = [c.name for c in sorted(kok.cells.values(),
                                      key=lambda c: c.region.bounding_box[0][2])]
    kontrol("katmanlar ALTTAN USTE dogru sirada",
            z_sirali == ["alt yansitici", "aktif", "ust yansitici"],
            "-> %s" % z_sirali)

    duzlemler = sorted((srf.z0, srf.boundary_type)
                       for srf in model.geometry.get_all_surfaces().values()
                       if srf.type == "z-plane")
    beklenen = [(-203.0, "vacuum"), (-183.0, "transmission"),
                (183.0, "transmission"), (203.0, "vacuum")]
    kontrol("z duzlemleri ve sinir kosullari dogru", duzlemler == beklenen,
            "-> %s" % duzlemler)

    # katman z araliklari
    kutular = sorted((float(c.region.bounding_box[0][2]),
                      float(c.region.bounding_box[1][2]), c.name)
                     for c in kok.cells.values())
    kontrol("katmanlar bitisik ve bosluksuz",
            all(abs(kutular[i][1] - kutular[i + 1][0]) < 1e-9
                for i in range(len(kutular) - 1)),
            "-> %s" % [(a, b) for a, b, _ in kutular])


def test_eksenel_araliklar():
    """
    Uc ayri yuksekligin uc ayri tanimi oldugunu dogrular:
      toplam model / fisil aralik / hedef cubugun araligi
    Bunlari karistirmak iki gercek hataya yol acti (kaynak kutusu 1300 pcm,
    F_q %6 sisme), bu yuzden sayilar teste caktirildi.
    """
    print("\n[14b] EKSENEL ARALIKLAR: toplam / fisil / cubuk ayri ayri")
    spec = sema.yukle(os.path.join(ORNEK, "pwr_eksenel.json"))
    kontrol("toplam yukseklik 395 cm",
            abs(sema.kor_yuksekligi(spec["kor"]) - 395.0) < 1e-9)
    ar = kurucu.aktif_eksenel_aralik(spec)
    kontrol("fisil aralik (-177.5, 152.5) -- blanket dahil",
            ar is not None and abs(ar[0] + 177.5) < 1e-9 and abs(ar[1] - 152.5) < 1e-9,
            "-> %s" % (ar,))
    cr = kurucu.cubuk_eksenel_aralik(spec, "yakit_cubugu")
    kontrol("yakit_cubugu araligi (-162.5, 137.5) -- blanket HARIC",
            cr is not None and abs(cr[0] + 162.5) < 1e-9 and abs(cr[1] - 137.5) < 1e-9,
            "-> %s" % (cr,))
    kontrol("blanket cubugu blanket katmanlarinda",
            kurucu.cubuk_eksenel_aralik(spec, "blanket_cubugu") is not None)

    # kaynak kutusu ve guc mesh'i dogru araligi kullaniyor mu
    model, bilgi = kurucu.kur(spec)
    uzay = model.settings.source[0].space
    kontrol("kaynak kutusu FISIL araligi kapsiyor",
            abs(uzay.lower_left[2] + 177.5) < 1e-9
            and abs(uzay.upper_right[2] - 152.5) < 1e-9,
            "-> [%g, %g]" % (uzay.lower_left[2], uzay.upper_right[2]))
    mesh = None
    for t in model.tallies:
        if t.name == "guc_dagilimi":
            for f in t.filters:
                if hasattr(f, "mesh"):
                    mesh = f.mesh
    kontrol("guc mesh'i CUBUK araligini kapsiyor",
            mesh is not None and abs(mesh.lower_left[2] + 162.5) < 1e-9
            and abs(mesh.upper_right[2] - 137.5) < 1e-9,
            "-> [%g, %g]" % (mesh.lower_left[2], mesh.upper_right[2]) if mesh else "")

    # GERIYE DONUK UYUM: katmansiz modelde ikisi de +/-H/2 olmali
    duz = sema.yukle(os.path.join(ORNEK, "pwr_3b.json"))
    h = sema.kor_yuksekligi(duz["kor"])
    kontrol("katmansiz modelde fisil aralik = +/-H/2 (geriye donuk uyum)",
            kurucu.aktif_eksenel_aralik(duz) == (-h / 2.0, h / 2.0))
    kontrol("katmansiz modelde cubuk araligi = +/-H/2",
            kurucu.cubuk_eksenel_aralik(duz, "yakit_cubugu") == (-h / 2.0, h / 2.0))
    kontrol("2B modelde aralik None",
            kurucu.aktif_eksenel_aralik(
                sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))) is None)


def test_eksenel_dogrulama():
    """Katmanlamanin sessiz hatalari kosudan once yakalaniyor mu?"""
    print("\n[14c] EKSENEL DOGRULAMA: bozuk katmanlamalar")
    from cekirdek import dogrula as dg
    temel = _eksenel_spec()

    def hata(degistir):
        t = copy.deepcopy(temel)
        degistir(t)
        v = [b for b in dg.eksenel_kontrol(t) if b.seviye == "hata"]
        return v[0].mesaj if v else None

    for ad, degistir, parca in (
            ("desteklenmeyen kor turu",
             lambda t: t["kor"].update(tur="kuresel"), "desteklenmiyor"),
            ("tanimsiz dolgu adi",
             lambda t: t["kor"]["eksenel"]["bolgeler"][0].update(dolgu="yok_boyle"),
             "tanimsiz dolgu"),
            ("sifir katman yuksekligi",
             lambda t: t["kor"]["eksenel"]["bolgeler"][1].update(yukseklik=0.0),
             "pozitif olmali"),
            ("hic katman yok",
             lambda t: t["kor"]["eksenel"].update(bolgeler=[]), "hic katman"),
            ("fisil katman yok",
             lambda t: t["kor"]["eksenel"].update(
                 bolgeler=[sema.eksenel_bolge("su", 20.0, "su")]), "fisil malzeme yok"),
            ("anahtar kare_kafes disinda",
             lambda t: t["kor"]["eksenel"]["bolgeler"][1].update(
                 anahtar={"y": "demet_17x17"}), "yalnizca kare_kafes"),
    ):
        m = hata(degistir)
        kontrol("%s -> HATA" % ad, bool(m) and parca in m,
                "-> %s" % (m or "YAKALANMADI"))

    kontrol("temiz katmanlama hata vermiyor",
            not dg.hata_var(dg.eksenel_kontrol(temel)))


def test_kontrol_cubugu_eksenel():
    """
    Katmanli modelde cubuk ucu AKTIF araliktan hesaplanmali.

    Gercek z0 geometriden okunuyor -- "hata vermedi" testi bu hatayi gormez.
    """
    print("\n[14d] KONTROL CUBUGU: daldirma aktif aralikta olculuyor")
    spec = sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json"))
    spec["kor"]["yukseklik"] = None
    spec["kor"]["eksenel"] = {"var": True, "bolgeler": [
        sema.eksenel_bolge("alt yansitici", 25.0, "su"),
        sema.eksenel_bolge("aktif", 300.0, None),
        sema.eksenel_bolge("plenum", 30.0, "su"),
    ]}
    ar = kurucu.aktif_eksenel_aralik(spec)
    kontrol("aktif aralik plenumu disliyor (-152.5, 147.5)",
            abs(ar[0] + 152.5) < 1e-9 and abs(ar[1] - 147.5) < 1e-9, "-> %s" % (ar,))

    kontrol_cubugu = [c for c in spec["cubuklar"] if c.get("tur") == "kontrol"][0]
    for daldirma, beklenen in ((0.0, 147.5), (50.0, -2.5), (100.0, -152.5)):
        kontrol_cubugu["daldirma"] = daldirma
        univ = kurucu.cubuk_universe(spec, kontrol_cubugu["ad"],
                                     kurucu.malzemeleri_kur(spec)[0])
        z0lar = sorted({float(srf.z0)
                        for c in univ.cells.values()
                        for srf in c.region.get_surfaces().values()
                        if srf.type == "z-plane"})
        kontrol("daldirma %%%g -> uc z = %g" % (daldirma, beklenen),
                any(abs(z - beklenen) < 1e-9 for z in z0lar), "-> %s" % z0lar)


def test_arayuz_eksenel_gidip_gelme():
    """
    Katman tablosu spec'i bozmuyor mu?

    Ozellikle katmana ozel 'anahtar' alani: arayuzde duzenlenmiyor, bu yuzden
    kaydederken SESSIZCE SILINMESI cok kolay olurdu (ayni hatayi kaynak
    sekmesinde bir kez yaptim).
    """
    print("\n[14e] ARAYUZ: eksenel katman tablosu gidip gelmede bozmuyor")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6 import QtWidgets
    except Exception as e:
        kontrol("PySide6 yok, arayuz testi atlandi", True, "-> %s" % e)
        return
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.sekme_kor import KorSekmesi

    spec = sema.yukle(os.path.join(ORNEK, "pwr_eksenel.json"))
    sekme = KorSekmesi()
    sekme.spec = spec
    sekme._yukleniyor = True
    sekme.doldur()
    sekme._yukleniyor = False
    kontrol("6 katman tabloya yuklendi", sekme.katman_tablo.rowCount() == 6,
            "-> %d" % sekme.katman_tablo.rowCount())
    kontrol("ozet uc araligi da gosteriyor",
            "395" in sekme.katman_ozet.text()
            and "330" in sekme.katman_ozet.text()
            and "300" in sekme.katman_ozet.text())

    adlar = lambda: [b["ad"] for b in spec["kor"]["eksenel"]["bolgeler"]]
    ilk = adlar()
    sekme._katman_ekle()
    kontrol("katman eklendi", len(adlar()) == 7)
    sekme.katman_tablo.setCurrentCell(6, 0)
    sekme._katman_sil()
    kontrol("katman silindi, sira bozulmadi", adlar() == ilk)
    sekme.katman_tablo.setCurrentCell(0, 0)
    sekme._katman_tasi(+1)
    kontrol("katman kaydirildi", adlar()[:2] == [ilk[1], ilk[0]])
    sekme._katman_tasi(-1)
    kontrol("geri kaydirildi", adlar() == ilk)

    kontrol("katmanli modelde kor.yukseklik None (tek gercek kaynak)",
            spec["kor"]["yukseklik"] is None)

    # katmana ozel anahtar korunmali
    spec["kor"]["eksenel"]["bolgeler"][2]["anahtar"] = {"y": "demet_blanket"}
    sekme._yukleniyor = True
    sekme._katman_doldur()
    sekme._yukleniyor = False
    sekme.katman_tablo.cellWidget(1, 1).setValue(30.0)
    kontrol("katmana ozel anahtar KORUNDU",
            spec["kor"]["eksenel"]["bolgeler"][2].get("anahtar")
            == {"y": "demet_blanket"})
    kontrol("anahtarli katmanin dolgu kutusu devre disi",
            not sekme.katman_tablo.cellWidget(2, 2).isEnabled())
    uyg  # noqa: B018


def test_eksenel_betik_ve_korunum(gecici):
    """
    Katmanli modelde betik esdegerligi VE guc toplami korunumu.

    Bu test bu turda bulunan uc hatadan ikisini yakalar:
      * kurucu ile betigin farkli kaynak kutusu kurmasi (1300 pcm)
      * guc mesh'inin hedef cubuktan tasmasi (F_q %6 sisme -> korunum bozulur)
    Tek is parcacigiyla bit esitligi aranir (8 is parcacigi ~6e-15 gurultu uretir).
    """
    print("\n[15] EKSENEL: betik esdegerligi + guc korunumu (tek is parcacigi)")
    import openmc
    spec = sema.yukle(os.path.join(ORNEK, "pwr_eksenel.json"))
    spec["ayarlar"]["parcacik"] = 3000
    spec["ayarlar"]["cevrim"] = 30
    spec["ayarlar"]["pasif"] = 10

    eski = os.getcwd()
    try:
        ya = os.path.join(gecici, "eks_a")
        os.makedirs(ya, exist_ok=True)
        os.chdir(ya)
        model_a, _ = kurucu.kur(spec)
        sp_a = model_a.run(threads=1, output=False)
        k_a = openmc.StatePoint(sp_a).keff

        yb = os.path.join(gecici, "eks_b")
        os.makedirs(yb, exist_ok=True)
        os.chdir(yb)
        betik = os.path.join(yb, "model.py")
        with open(betik, "w", encoding="utf-8") as f:
            f.write(kod_uret.uret(spec, "model.py"))
        sm = importlib.util.spec_from_file_location("eksuret", betik)
        mod = importlib.util.module_from_spec(sm)
        sm.loader.exec_module(mod)
        k_b = openmc.StatePoint(mod.model.run(threads=1, output=False)).keff
    finally:
        os.chdir(eski)
    kontrol("kurucu %.10f vs betik %.10f" % (k_a.nominal_value, k_b.nominal_value),
            k_a.nominal_value == k_b.nominal_value,
            "-> bit duzeyinde %s"
            % ("ayni" if k_a.nominal_value == k_b.nominal_value else "FARKLI"))

    from cekirdek import kosucu as _kos
    s = _kos.sonuc_oku(sp_a)
    g = s.get("guc") or {}
    kor = g.get("korunum")
    kontrol("guc toplami korunuyor (bagil fark %.2e)" % (kor if kor is not None else -1),
            kor is not None and kor < 1e-6)
    f = g.get("faktorler") or {}
    kontrol("F_q hesaplandi ve makul (1.3-2.5): %.4f" % (f.get("F_q") or 0),
            1.3 < (f.get("F_q") or 0) < 2.5)


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
    test_kaynak_tayfi()
    test_kaynak_betik_esleme()
    test_kaynak_yonu()
    test_kaynak_dogrulama()
    test_sema_derin_birlestirme()
    test_entropi_mesh_eksenel()
    test_arayuz_kaynak_gidip_gelme()
    test_eksenel_geometri()
    test_eksenel_araliklar()
    test_eksenel_dogrulama()
    test_kontrol_cubugu_eksenel()
    test_arayuz_eksenel_gidip_gelme()

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
            test_zayiflatma_analitik(gecici)
            test_sabit_kaynak_betik(gecici)
            test_eksenel_betik_ve_korunum(gecici)
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
