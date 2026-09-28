# -*- coding: utf-8 -*-
"""
 test_tukenme_temel.py  --  17-18. tukenme: zincir, Bateman, hacimler, dogrulama, kosu, betik, eskime

 testler/test_regresyon.py'den tasindi (Dalga 0; test metinleri aynen).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

import copy
import os
import shutil
import sys
import tempfile

from cekirdek import sema, kod_uret
from testler.ortak_test import kontrol
from testler.regresyon_ortak import KOK, ORNEK


# ============================================================================
# 17. TUKENME
# ============================================================================

def test_zincir_butunlugu():
    """
    Yarim indirilmis zincir ANINDA yakalanmali.

    23.09.2026'daki ilk indirme %13'te sessizce kesilmisti (3 645 440 /
    27 526 672 bayt). Adi ve yeri dogruydu; bakan biri sorun gormezdi.
    """
    print("\n[17] ZINCIR BUTUNLUGU: kesik dosya yakalaniyor")
    from cekirdek import veri_bilgi, tukenme
    dizin = veri_bilgi.zincir_dizini()
    for tur, dosya in sorted(tukenme.ZINCIRLER.items()):
        tamam, mesaj, _n = veri_bilgi.zincir_kontrol(os.path.join(dizin, dosya))
        kontrol("%s zinciri kurulu ve tam" % tur, tamam, "-> %s" % mesaj)
    # yarisindan kesilmis bir kopya
    kaynak = os.path.join(dizin, "chain_casl_thermal.xml")
    gecici = tempfile.mkdtemp(prefix="zincir_")
    try:
        kesik = os.path.join(gecici, "kesik.xml")
        with open(kaynak, "rb") as f:
            veri = f.read()
        with open(kesik, "wb") as f:
            f.write(veri[: len(veri) // 2])
        tamam, mesaj, _ = veri_bilgi.zincir_kontrol(kesik)
        kontrol("yarim kesilmis zincir reddediliyor", not tamam and "yarım" in mesaj,
                "-> %s" % mesaj)
        tamam, _m, n = veri_bilgi.zincir_kontrol(
            os.path.join(dizin, "chain_endfb80_thermal.xml"), tam=True)
        kontrol("ENDF/B-VIII.0 zinciri ayristiriliyor: %s nuklid" % n, tamam and n == 3820)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def test_bateman_bozunum(gecici=None):
    """
    ANALITIK: zincirin bozunum verisi + OpenMC'nin CRAM cozucusu.

    Guc sifirken tek bir radyonuklid N(t) = N0 exp(-ln2 t / T1/2) izlemeli.
    Yari omur ZINCIRIN KENDISINDEN okunur -- test boylece hem zincir
    dosyasinin butunlugunu hem cozucuyu sinar.
    """
    print("\n[17b] BATEMAN: sifir gucte bozunum = exp(-lambda t)")
    import math
    import numpy as np
    import openmc.deplete as d
    from cekirdek import veri_bilgi
    yol = os.path.join(veri_bilgi.zincir_dizini(), "chain_endfb80_thermal.xml")
    zincir = d.Chain.from_xml(yol)
    for ad in ("Xe135", "I131", "Co60"):
        n = zincir[ad]
        T = n.half_life
        lam = math.log(2.0) / T
        # guc sifir -> yalnizca bozunum matrisi (reaksiyon terimi yok)
        A = zincir.decay_matrix
        n0 = np.zeros(len(zincir))
        i = zincir.nuclide_dict[ad]
        n0[i] = 1.0e20
        t = T                                   # tam bir yari omur
        n1 = d.cram.CRAM48(A, n0, t)
        oran = n1[i] / n0[i]
        kontrol("%s: bir yari omur (%.4g s) sonra N/N0 = %.10f (beklenen 0.5)"
                % (ad, T, oran), abs(oran - 0.5) < 1e-8)
        # iki yari omur
        n2 = d.cram.CRAM48(A, n0, 2.0 * t)
        kontrol("%s: iki yari omur sonra N/N0 = %.10f (beklenen %.10f)"
                % (ad, n2[i] / n0[i], math.exp(-lam * 2 * t)),
                abs(n2[i] / n0[i] - 0.25) < 1e-8)


def test_tukenme_zincir_secimi():
    """Spektrum tahmini ve fisyon verimi enerjisi."""
    print("\n[17c] TUKENME: zincir ve fisyon verimi spektruma gore")
    from cekirdek import tukenme
    beklenen = {"pwr_pinhucre": "termal", "pwr_17x17": "termal",
                "mtr_plaka": "termal", "sfr_altigen": "hizli",
                "godiva_kriter": "hizli",
                # Be yalnizca yansitici: kor spektrumu hizli
                "tamburlu_kor": "hizli"}
    for ad, tur in beklenen.items():
        z = tukenme.zincir_secimi(sema.yukle(os.path.join(ORNEK, ad + ".json")))
        kontrol("%s -> %s zincir" % (ad, tur), z["tur"] == tur, "-> %s (%s)" % (z["tur"], z["gerekce"]))
    sp = sema.yukle(os.path.join(ORNEK, "sfr_altigen.json"))
    z = tukenme.zincir_secimi(sp)
    kontrol("hizli sistemde fisyon verimi 500 keV (varsayilan 0.0253 eV DEGIL)",
            z["verim_enerjisi"] == 5.0e5)
    sp["tukenme"]["zincir"] = "termal"
    kontrol("kullanici secimi otomatigi eziyor",
            tukenme.zincir_secimi(sp)["tur"] == "termal")


def test_tukenme_hacimleri():
    """
    Hacimler analitik ve geometrinin TAM karsiligi olmali.

    Hacim f kat yanlissa yanma hizi da f kat yanlis olur -- k-eff'te hicbir
    iz birakmadan. Elle hesap + OpenMC'nin stokastik hacim hesabi.
    """
    print("\n[17d] TUKENME: analitik hacimler")
    import math
    from cekirdek import tukenme
    elle = {
        "pwr_pinhucre": ("uo2", math.pi * 0.39218 ** 2),
        "pwr_17x17": ("uo2", 264 * math.pi * 0.4096 ** 2),
        "mtr_plaka": ("u3si2_al", 0.051 * 6.3 * 23),
        "sfr_altigen": ("u10mo", 127 * math.pi * 0.32 ** 2),
        "godiva_kriter": ("heu", 4.0 / 3.0 * math.pi * 8.7407 ** 3),
        "tamburlu_kor": ("u10mo", math.pi * 16.0 ** 2 * 45.0),
        "pwr_eksenel": ("uo2", 264 * math.pi * 0.4096 ** 2 * 300.0),
    }
    for ad, (malz, V) in elle.items():
        h = tukenme.hacimler(sema.yukle(os.path.join(ORNEK, ad + ".json")))
        a = (h.get(malz) or {}).get("hacim")
        kontrol("%s %s = %.6g cm3 (elle %.6g)" % (ad, malz, a or 0, V),
                a is not None and abs(a - V) / V < 1e-12)
    h = tukenme.hacimler(sema.yukle(os.path.join(ORNEK, "pwr_eksenel.json")))
    kontrol("blanket iki katmanda: 2 x 15 cm x 264",
            abs(h["uo2_dogal"]["hacim"] - 264 * math.pi * 0.4096 ** 2 * 30.0) < 1e-6)

    # Agir metal: OpenMC'nin kendi hesabi ile bizimki ayni olmali
    import openmc.deplete as d
    sp = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    model, bilgi = tukenme.hazirla(sp)
    eski = os.getcwd()
    gecici = tempfile.mkdtemp(prefix="hm_")
    try:
        os.chdir(gecici)
        op = d.CoupledOperator(model, bilgi["zincir"]["yol"])
        kontrol("agir metal: OpenMC %.8g g = bizim %.8g g"
                % (op.heavy_metal, bilgi["agir_metal_g"]),
                abs(op.heavy_metal - bilgi["agir_metal_g"]) / bilgi["agir_metal_g"] < 1e-10)
    finally:
        os.chdir(eski)
        shutil.rmtree(gecici, ignore_errors=True)
    kontrol("yanma muhasebesi: 40 W/g x 500 gun = 20 MWd/kg",
            abs(tukenme.yanma(500.0, 40.0) - 20.0) < 1e-12)


def test_tukenme_dogrulama():
    """Tukenmenin sessiz hatalari kosudan once yakalaniyor mu?"""
    print("\n[17e] TUKENME DOGRULAMA")
    from cekirdek import dogrula as dg
    temel = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    kontrol("pwr_tukenme temiz", not dg.hata_var(dg.tukenme_kontrol(temel)))

    def bul(degistir, seviye, parca):
        t = copy.deepcopy(temel)
        degistir(t)
        return any(b.seviye == seviye and parca in b.mesaj
                   for b in dg.tukenme_kontrol(t))

    kontrol("sabit kaynak modunda HATA",
            bul(lambda t: t["ayarlar"].update(mod="fixed source"), "hata", "Özdeğer"))
    kontrol("negatif guc HATA",
            bul(lambda t: t["tukenme"].update(guc_yogunlugu=-1), "hata", "sıfırdan büyük"))
    kontrol("sifir adim HATA",
            bul(lambda t: t["tukenme"].update(adimlar=[1.0, 0.0]), "hata", "sıfırdan büyük"))
    kontrol("uzun ilk adim (Xe dengesi) UYARI",
            bul(lambda t: t["tukenme"].update(adimlar=[10.0]), "uyari", "Xe-135"))
    kontrol("MWd/kg biriminde uzun ilk adim da UYARI",
            bul(lambda t: t["tukenme"].update(adimlar=[1.0], adim_birimi="MWd/kg"),
                "uyari", "Xe-135"))
    kontrol("termal modelde hizli zincir UYARI",
            bul(lambda t: t["tukenme"].update(zincir="hizli"), "uyari", "spektrumlu"))
    kontrol("olagan disi guc yogunlugu UYARI",
            bul(lambda t: t["tukenme"].update(guc_yogunlugu=1000.0), "uyari", "olağan dışı"))


def test_tukenme_kosu(gecici):
    """
    Kucuk bir gercek tukenme kosusu: yon, Xe dengesi, betik esdegerligi.

    Tam fizik degerleri (Xe-135 degeri) ornek kosusunda olculup README'ye
    yazildi; burada hizli CASL zinciriyle YON ve TUTARLILIK sinanir.
    """
    print("\n[18] TUKENME KOSUSU (CASL zinciri, dusuk istatistik)")
    from cekirdek import tukenme
    sp = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    sp["ayarlar"].update(parcacik=1500, cevrim=20, pasif=5)
    sp["tukenme"].update(zincir="casl_termal", entegrator="predictor",
                         adimlar=[0.5, 1.5, 3.0])
    dizin = os.path.join(gecici, "tukenme")
    h5, bilgi = tukenme.calistir(sp, dizin)
    s = tukenme.sonuc_oku(h5, sp)
    y = s["yogunluk"]["uo2"]
    kontrol("4 zaman noktasi (0 + 3 adim)", len(s["k"]) == 4)
    kontrol("yanma = p x t: %s" % ["%.3f" % b for b in s["yanma"]],
            abs(s["yanma"][-1] - 40.0 * 5.0 / 1000.0) < 1e-12)
    kontrol("U-235 azaliyor", all(a > b for a, b in zip(y["U235"], y["U235"][1:])))
    kontrol("Pu-239 artiyor", all(a < b for a, b in zip(y["Pu239"], y["Pu239"][1:])))
    xe = y["Xe135"]
    kontrol("Xe-135 ~2 gunde dengeye yaklasiyor: %s" % ["%.3e" % v for v in xe],
            xe[0] == 0.0 and abs(xe[3] - xe[2]) / xe[3] < 0.1)
    kontrol("k Xe birikimiyle dusuyor: %.5f -> %.5f" % (s["k"][0], s["k"][2]),
            s["k"][2] < s["k"][0])

    # --- onceki sonuc: kosu kendi spec kaydini birakti mi, arayuz gosteriyor mu ---
    o = tukenme.onceki_sonuc(sp, dizin)
    kontrol("kosu spec kaydini birakti -> onceki sonuc 'guncel'",
            o is not None and o["durum"] == "guncel", "-> %s" % (o and o["durum"]))
    kontrol("onceki sonuc ayni k'yi veriyor", o is not None and o["sonuc"]["k"] == s["k"])
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6 import QtWidgets
    except Exception:
        return
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.sekme_tukenme import TukenmeSekmesi
    proje = os.path.join(gecici, "proje.json")
    sp_ui = copy.deepcopy(sp)
    sp_ui["calistirma"]["dizin"] = "arayuz"
    hedef = tukenme.kosu_dizini(sp_ui, proje)
    shutil.copytree(dizin, hedef)
    w = TukenmeSekmesi()
    w.proje_ayarla(proje)
    w.spec_yukle(sp_ui)
    w.bekle()
    kontrol("arayuz acilista onceki sonucu gosteriyor (%d satir)" % w.tablo.rowCount(),
            w.tablo.rowCount() == len(s["k"]))
    kontrol("arayuz 'bu modele ait' diyor", "bu modele ait." in w.onceki_etiket.text(),
            "-> %s" % w.onceki_etiket.text())
    w.guc.setValue(41.0)
    kontrol("model degisince arayuz ESKI diyor", "Eski sonuç" in w.onceki_etiket.text())

    # --- pencere, onceki sonuc OKUNURKEN kapatiliyor ---
    # Duzeltmeden once surec kapanista ASILI kaliyordu (olculdu: 60 s zaman
    # asimi); calisan QThread'in yok edilmesi Qt'de sureci de dusurebilir.
    # Hata sureci oldurdugu icin alt surecte, zaman siniriyla sinanir.
    import subprocess
    sema.kaydet(sp_ui, proje)
    betik = (
        "import sys, os, warnings; warnings.filterwarnings('ignore')\n"
        "sys.path.insert(0, %r)\n"
        "from PySide6 import QtCore, QtWidgets\n"
        "from arayuz.ana_pencere import AnaPencere\n"
        "app = QtWidgets.QApplication([])\n"
        "p = AnaPencere(%r); p.show()\n"
        "print('okuma_suruyor', p.s_tukenme._isci is not None and p.s_tukenme._isci.isRunning())\n"
        "QtCore.QTimer.singleShot(100, p.close)\n"
        "QtCore.QTimer.singleShot(200, app.quit)\n"
        "app.exec()\n" % (KOK, proje))
    try:
        r = subprocess.run([sys.executable, "-c", betik], capture_output=True, text=True,
                           timeout=60, env=dict(os.environ, QT_QPA_PLATFORM="offscreen"))
        kod, cikti = r.returncode, r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        kod, cikti = "ZAMAN ASIMI (asili kaldi)", ""
    kontrol("okuma surerken pencereyi kapatmak temiz cikiyor",
            kod == 0 and "QThread" not in cikti,
            "-> cikis %s, %s" % (kod, "okuma suruyordu" if "okuma_suruyor True" in cikti
                                 else "okuma bitmisti (senaryo zayif)"))
    uyg  # noqa: B018



def test_tukenme_betik_esdegerligi(gecici):
    """
    Uretilen betigin tukenme_kos()'u ile cekirdek/tukenme.py AYNI sonucu vermeli.

    Iki yol da AYRI ALT SURECTE, OMP_NUM_THREADS=1 ile kosulur: openmc.lib
    bir kez yuklendikten sonra is parcacigi sayisi degistirilemiyor ve 8 is
    parcacigi ~1e-15 bagil gurultu uretiyor (olculdu). Tek is parcacigiyla
    her adimin k'si BIT DUZEYINDE ayni olmali.
    """
    print("\n[18b] TUKENME BETIK ESDEGERLIGI (alt surec, tek is parcacigi)")
    import subprocess
    import openmc.deplete as d
    sp = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    sp["ayarlar"].update(parcacik=500, cevrim=12, pasif=4)
    sp["tukenme"].update(zincir="casl_termal", entegrator="predictor", adimlar=[1.0])
    spec_yolu = os.path.join(gecici, "tk_esd.json")
    sema.kaydet(sp, spec_yolu)
    ortam = dict(os.environ, OMP_NUM_THREADS="1", PYTHONPATH=KOK)

    da = os.path.join(gecici, "tk_a")
    r = subprocess.run([sys.executable, "-m", "cekirdek.tukenme", spec_yolu,
                        "-s", "1", "--dizin", da],
                       cwd=KOK, env=ortam, capture_output=True, text=True)
    kontrol("cekirdek yolu kostu", r.returncode == 0, r.stderr[-300:])

    db = os.path.join(gecici, "tk_b")
    os.makedirs(db, exist_ok=True)
    with open(os.path.join(db, "model.py"), "w", encoding="utf-8") as f:
        f.write(kod_uret.uret(sp, "model.py"))
    r = subprocess.run([sys.executable, "-c", "import model; model.tukenme_kos()"],
                       cwd=db, env=ortam, capture_output=True, text=True)
    kontrol("uretilen betigin tukenme_kos() kostu", r.returncode == 0, r.stderr[-300:])

    try:
        _t, ka = d.Results(os.path.join(da, "depletion_results.h5")).get_keff()
        _t, kb = d.Results(os.path.join(db, "depletion_results.h5")).get_keff()
    except Exception as e:
        kontrol("sonuclar okunabildi", False, "-> %s" % e)
        return
    for i in range(len(ka)):
        kontrol("adim %d: cekirdek %.12f vs betik %.12f" % (i, ka[i][0], kb[i][0]),
                ka[i][0] == kb[i][0],
                "-> bit duzeyinde %s" % ("ayni" if ka[i][0] == kb[i][0] else "FARKLI"))



def test_tukenme_eskime():
    """
    Onceki sonuc SU ANKI modele mi ait?

    Eski bir sonucu guncelmis gibi gostermek hic gostermemekten kotudur.
    Karsilastirma metinle degil Python esitligiyle yapilir: JSON'da 3 ile 3.0
    farkli metindir ama ayni sayidir.
    """
    print("\n[17g] TUKENME: onceki sonucun eskimesi")
    from cekirdek import tukenme
    sp = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    d = tempfile.mkdtemp(prefix="eskime_")
    try:
        kontrol("kayit yoksa 'bilinmiyor'", tukenme.eskime(sp, d)[0] == "bilinmiyor")
        kontrol("sonuc dosyasi yoksa onceki_sonuc None", tukenme.onceki_sonuc(sp, d) is None)
        tukenme.spec_kaydet(sp, d)
        kontrol("ayni spec -> guncel", tukenme.eskime(sp, d) == ("guncel", []))

        def durum(degistir):
            t = copy.deepcopy(sp)
            degistir(t)
            return tukenme.eskime(t, d)

        kontrol("guc degisti -> eski (tukenme)",
                durum(lambda t: t["tukenme"].update(guc_yogunlugu=41.0)) == ("eski", ["tukenme"]))
        kontrol("zenginlik degisti -> eski (malzemeler)",
                durum(lambda t: t["malzemeler"][0].update(yogunluk={"deger": 10.1, "birim": "g/cm3"}))[0] == "eski")
        kontrol("ad / aciklama / kosu dizini degisti -> guncel (fizik degil)",
                durum(lambda t: (t.update(ad="baska", aciklama="x"),
                                 t["calistirma"].update(dizin="y", is_parcacigi=3)))[0] == "guncel")
        kontrol("tukenmeyi kapatip acmak eskitmez",
                durum(lambda t: t["tukenme"].update(var=False))[0] == "guncel")
        kontrol("3 ile 3.0 ayni sayi -> guncel",
                durum(lambda t: t["tukenme"].update(
                    adimlar=[float(a) if float(a) != int(a) else int(a)
                             for a in t["tukenme"]["adimlar"]]))[0] == "guncel")
        kontrol("kosu dizini proje dizinine gore",
                tukenme.kosu_dizini(sp, "/a/b/p.json") == "/a/b/kosu_pin_tukenme")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_arayuz_tukenme_gidip_gelme():
    """
    8. Tukenme sekmesi spec'i bozmuyor mu?

    Ozellikle arayuzde duzenlenmeyen "ek_malzemeler": kaynak sekmesinde bir
    kez sozlugu bastan yazip alan silmistik; ayni hata burada olmasin.
    """
    print("\n[17f] ARAYUZ: tukenme sekmesi gidip gelmede bozmuyor")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6 import QtWidgets
    except Exception as e:
        kontrol("PySide6 yok, arayuz testi atlandi", True, "-> %s" % e)
        return
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.sekme_tukenme import TukenmeSekmesi
    spec = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    spec["tukenme"]["ek_malzemeler"] = ["zirkaloy"]
    t = TukenmeSekmesi()
    t.spec_yukle(spec)
    kontrol("tukenme acik yuklendi", t.var.isChecked())
    kontrol("adimlar yuklendi", t._sayilar(t.adimlar.text())
            == [float(a) for a in spec["tukenme"]["adimlar"]])
    kontrol("ozet toplam yanmayi gosteriyor (20 MWd/kg)", "20 MWd/kg" in t.adim_ozet.text(),
            "-> %s" % t.adim_ozet.text())
    kontrol("ozet transport sayisini gosteriyor (17)", "17 transport" in t.adim_ozet.text())
    kontrol("yanabilir malzeme ve analitik hacim gosteriliyor",
            "uo2" in t.malzeme_bilgi.text() and "analitik" in t.malzeme_bilgi.text())
    t.guc.setValue(38.0)
    kontrol("guc spec'e yazildi", spec["tukenme"]["guc_yogunlugu"] == 38.0)
    kontrol("duzenlenmeyen ek_malzemeler KORUNDU",
            spec["tukenme"].get("ek_malzemeler") == ["zirkaloy"])
    t.adimlar.setText("1, 2, 3")
    t._kaydet()
    kontrol("adimlar spec'e yazildi", spec["tukenme"]["adimlar"] == [1.0, 2.0, 3.0])
    t.var.setChecked(False)
    kontrol("kapaliyken baslat devre disi", not t.d_baslat.isEnabled())
    uyg  # noqa: B018


HIZLI = [
    test_zincir_butunlugu, test_tukenme_zincir_secimi,
    test_tukenme_hacimleri, test_tukenme_dogrulama, test_tukenme_eskime,
    test_arayuz_tukenme_gidip_gelme,
]
YAVAS = [
    test_tukenme_kosu, test_tukenme_betik_esdegerligi, test_bateman_bozunum]
