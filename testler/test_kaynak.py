# -*- coding: utf-8 -*-
"""
 test_kaynak.py  --  12-13. kaynak tayfi, yonu, dogrulama, sabit kaynak, analitik zayiflatma

 testler/test_regresyon.py'den tasindi (Dalga 0; test metinleri aynen).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

import copy
import importlib.util
import os
import shutil
import tempfile

from cekirdek import sema, kurucu, kod_uret
from testler.ortak_test import kontrol
from testler.regresyon_ortak import ORNEK


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
        kontrol("histogram uzunluk hatasi yakalaniyor", "2 değer olmalı" in str(e))


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
    v = bul(s, "hiçbir tally")
    kontrol("sabit kaynakta tally yoksa HATA", v and v[0].seviye == "hata")

    s = copy.deepcopy(temel)
    s["ayarlar"]["kaynak"]["parcacik"] = "photon"
    s["ayarlar"]["mod"] = "eigenvalue"
    v = bul(s, "foton kaynağı Özdeğer")
    kontrol("ozdeger modunda foton kaynagi HATA", v and v[0].seviye == "hata")

    s = copy.deepcopy(temel)
    s["ayarlar"]["kaynak"]["kuvvet"] = 0.0
    kontrol("sifir kaynak siddeti HATA", bool(bul(s, "şiddeti sıfırdan büyük")))

    s = copy.deepcopy(temel)
    s["ayarlar"]["kaynak"]["aci"] = {"tur": "tek_yon", "yon": [0.0, 0.0, 0.0]}
    kontrol("sifir yon vektoru HATA", bool(bul(s, "sıfır vektör")))

    # nokta kaynak model disinda -- yuksekligi olan bir modelde
    s = sema.yukle(os.path.join(ORNEK, "pwr_3b.json"))
    h = s["kor"]["yukseklik"]
    s["ayarlar"]["kaynak"] = {"tur": "nokta", "konum": [0.0, 0.0, h]}
    kontrol("nokta kaynak geometri disinda HATA", bool(bul(s, "modelin dışında")))

    # enerji tavani: 40 MeV kaynak, ENDF/B-VIII.0 su+celik icin tavan 20 MeV
    s = copy.deepcopy(temel)
    s["ayarlar"]["kaynak"]["enerji"] = {"tur": "tek", "enerji": 40.0e6}
    v = [x for x in dg.kaynak_kontrol(s, veri_kontrolu=True)
         if "veri tavanı" in x.mesaj]
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
            "kurulamad" in sekme.tayf_ozet.text()        # "kurulamadı" (Dalga 3 Turkce)
            and "color" in sekme.tayf_ozet.styleSheet())
    uyg  # noqa: B018  -- uygulama nesnesi yasasin diye


def test_kaynak_kutusu_yansitici():
    """
    Baslangic kaynagi kutusu korun YANSITICI HARIC olcusunu kapsamali.

    Once modelin tum sinir kutusu kullaniliyordu: 17x17 + 20 cm su
    yansiticida yakit kutunun ~%3.7'si kaliyor, OpenMC "Too few source sites
    satisfied the constraints" diyerek kosuyu durduruyordu (olculdu). Yani
    yansitici ekleyen her kullanici bu hatayla karsilasiyordu. Uretilen betik
    de AYNI kutuyu kurmali (betik esdegerligi).
    """
    print("\n[19] KAYNAK KUTUSU: yansitici haric kor olcusu")
    import importlib.util as _iu
    sp = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    sp["kor"]["yansitici"].update(var=True, kalinlik=20.0, malzeme="su")
    sp["ayarlar"]["kaynak"] = {"tur": "kutu", "alt": None, "ust": None}
    model, bilgi = kurucu.kur(sp)
    u = model.settings.source[0].space
    kontrol("model 61.42 cm, kaynak kutusu x = +/-10.71 (yalniz kor)",
            abs(bilgi["sinir_kutu"][0] - 61.42) < 1e-9
            and abs(u.upper_right[0] - 10.71) < 1e-9 and abs(u.lower_left[0] + 10.71) < 1e-9,
            "-> %.4f .. %.4f" % (u.lower_left[0], u.upper_right[0]))
    d = tempfile.mkdtemp(prefix="kutu_")
    try:
        yol_b = os.path.join(d, "model.py")
        with open(yol_b, "w", encoding="utf-8") as f:
            f.write(kod_uret.uret(sp, "model.py"))
        sm = _iu.spec_from_file_location("kutubetik", yol_b)
        mod = _iu.module_from_spec(sm)
        sm.loader.exec_module(mod)
        ub = mod.model.settings.source[0].space
        kontrol("uretilen betik ayni kaynak kutusunu kuruyor",
                list(ub.lower_left) == list(u.lower_left)
                and list(ub.upper_right) == list(u.upper_right))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    t = sema.yukle(os.path.join(ORNEK, "tamburlu_kor.json"))
    t["ayarlar"]["kaynak"] = {"tur": "kutu", "alt": None, "ust": None}
    ut = kurucu.kur(t)[0].settings.source[0].space
    R = float(t["kor"]["kor_yaricap"])
    kontrol("tamburlu: kutu kor silindirini kapsiyor (+/-%g)" % R,
            abs(ut.upper_right[0] - R) < 1e-9, "-> %.4f" % ut.upper_right[0])
    duz = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    duz["ayarlar"]["kaynak"] = {"tur": "kutu", "alt": None, "ust": None}
    ud = kurucu.kur(duz)[0].settings.source[0].space
    kontrol("yansiticisiz modelde kutu degismedi (+/-10.71)",
            abs(ud.upper_right[0] - 10.71) < 1e-9)


HIZLI = [
    test_kaynak_kutusu_yansitici, test_kaynak_tayfi, test_kaynak_betik_esleme,
    test_kaynak_yonu, test_kaynak_dogrulama, test_sema_derin_birlestirme,
    test_entropi_mesh_eksenel, test_arayuz_kaynak_gidip_gelme,
]
YAVAS = [
    test_zayiflatma_analitik, test_sabit_kaynak_betik,
]
