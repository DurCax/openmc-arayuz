# -*- coding: utf-8 -*-
"""
 test_nuklid_secici.py  --  Izlenen nuklidler: ad normallestirme, zincir, dogrulama,
                            sonuc okuma, secici widget'i ve CSV disa aktarma

 Eskiden "Izlenen nuklidler" serbest metindi ve sonuc okuma yazim hatalarini
 SESSIZCE atliyordu ("Xe-135" yazan kullanici grafikte Xe'yi hic goremiyor,
 nedenini de bilmiyordu).

 Zincir ya da onceki tukenme sonucu (depletion_results.h5) gereken testler
 bunlar yoksa acik bir mesajla erken doner.
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri).
"""

import copy
import csv
import io
import os
import subprocess
import time

from testler.ortak_test import kontrol, KOK, ORNEK, ISLEM_PARCACIGI
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Ekran goruntuleri (depoya girmez). TEST_EKRAN_DIZINI verilmezse gecici dizin.
EKRAN_DIZINI = os.environ.get("TEST_EKRAN_DIZINI") or os.path.join(
    os.environ.get("TMPDIR", "/tmp"), "nuklid_secici_ekran")

# Sentetik, kucuk bir "zincir" (zincirsiz testler icin).
SENTETIK_ADLAR = ("H1", "O16", "U234", "U235", "U236", "U238", "Np237", "Np239",
                  "Pu238", "Pu239", "Pu240", "Pu241", "Pu242", "Am241", "Am242_m1",
                  "Am243", "Cm242", "Cm244", "Xe135", "Xe136", "Sm149", "Sm151",
                  "Gd155", "Gd157", "Er167", "Tc99", "I129", "Cs137", "Rh103")


def _qt():
    try:
        from PySide6 import QtWidgets
    except ImportError as e:                         # pragma: no cover
        kontrol("PySide6 yok, arayuz testi atlandi", True, "-> %s" % e)
        return None
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _bekle(kosul, saniye=30.0):
    from PySide6 import QtWidgets
    son = time.time() + saniye
    while time.time() < son:
        QtWidgets.QApplication.processEvents()
        if kosul():
            return True
        time.sleep(0.02)
    QtWidgets.QApplication.processEvents()
    return kosul()


def _zincir_yolu(dosya="chain_endfb80_thermal.xml"):
    """Zincir dosyasi varsa yolu; yoksa None (test acik mesajla erken doner)."""
    from cekirdek import veri_bilgi
    yol = os.path.join(veri_bilgi.zincir_dizini(), dosya)
    if os.path.isfile(yol):
        return yol
    kontrol("tukenme zinciri yok (%s) -- test atlandi" % yol, True)
    return None


def _ana_depo_koku():
    """Git worktree'de calisiliyorsa ana deponun koku (sonuclar orada olabilir)."""
    try:
        r = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=KOK,
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    ortak = os.path.abspath(os.path.join(KOK, r.stdout.strip()))
    return os.path.dirname(ortak)


def _onceki_h5():
    """pwr_tukenme orneginin mevcut depletion_results.h5'i: (ornek_yolu, h5) ya da None."""
    from cekirdek import sema, tukenme
    for kok in (KOK, _ana_depo_koku()):
        if not kok:
            continue
        ornek = os.path.join(kok, "ornekler", "pwr_tukenme.json")
        if not os.path.isfile(ornek):
            continue
        h5 = os.path.join(tukenme.kosu_dizini(sema.yukle(ornek), ornek),
                          "depletion_results.h5")
        if os.path.isfile(h5):
            return ornek, h5
    kontrol("pwr_tukenme'nin onceki sonucu (depletion_results.h5) yok -- test atlandi "
            "(YAVAS test_kisa_kosu_yeni_secim ayni seyi kisa bir kosuyla sinar)", True)
    return None


# ============================================================================
# 1. Ad normallestirme ve oneri (saf, zincirsiz)
# ============================================================================

@gereksinim("R-A2-01")
def test_normallestirme_ve_oneri():
    print("\n[NS1] NUKLID ADI: normallestirme ve en yakin eslesme onerisi")
    from cekirdek import nuklidler as nk
    tablo = [
        ("Xe135", "Xe135"), ("Xe-135", "Xe135"), ("xe135", "Xe135"),
        ("XE135", "Xe135"), ("Xe 135", "Xe135"), (" xe-135 ", "Xe135"),
        ("Am242m", "Am242_m1"), ("Am-242m", "Am242_m1"), ("am242m1", "Am242_m1"),
        ("Am242_m1", "Am242_m1"), ("Tc-99m", "Tc99_m1"), ("135Xe", "Xe135"),
        ("U-235", "U235"), ("u235", "U235"), ("H1", "H1"),
        ("", None), ("Xe", None), ("Xe-136x", None), ("Qq135", None),
        ("135", None), ("Xe-", None), (None, None),
    ]
    for girdi, beklenen in tablo:
        sonuc = nk.normallestir(girdi)
        kontrol("normallestir(%r) = %r" % (girdi, beklenen), sonuc == beklenen,
                "-> %r" % sonuc)
    oneriler = [("Xe-135", "Xe135"), ("Xe-136x", "Xe136"), ("am242m", "Am242_m1"),
                ("Pu-239", "Pu239"), ("Cs-137", "Cs137"), ("Zzz999", None)]
    for girdi, beklenen in oneriler:
        sonuc = nk.oneri(girdi, SENTETIK_ADLAR)
        kontrol("oneri(%r) = %r" % (girdi, beklenen), sonuc == beklenen, "-> %r" % sonuc)
    eksik = nk.eksikler(["U235", "Xe-135", "Foo"], SENTETIK_ADLAR)
    kontrol("eksikler: zincirde olmayanlar oneriyle", eksik == [("Xe-135", "Xe135"),
                                                              ("Foo", None)],
            "-> %r" % eksik)
    kontrol("oneri_metni 'Xe-135 → Xe135?'", nk.oneri_metni("Xe-135", "Xe135")
            == "Xe-135 → Xe135?", "-> %r" % nk.oneri_metni("Xe-135", "Xe135"))


def test_gruplar_ve_setler_sentetik():
    print("\n[NS2] GRUPLAR VE HAZIR SETLER: yalnizca zincirde olanlar")
    from cekirdek import nuklidler as nk
    from cekirdek import sema
    gruplar = {g.anahtar: g.nuklidler for g in nk.gruplar(SENTETIK_ADLAR)}
    kontrol("uranyum grubu", gruplar.get("uranyum") == ("U234", "U235", "U236", "U238"),
            "-> %r" % (gruplar.get("uranyum"),))
    kontrol("amerikyum grubu metastabil dahil",
            gruplar.get("amerikyum") == ("Am241", "Am242_m1", "Am243"),
            "-> %r" % (gruplar.get("amerikyum"),))
    kontrol("zehirler yalnizca zincirdekiler (Sm151 var, Eu155 yok)",
            "Sm151" in gruplar.get("zehirler", ()) and "Eu155" not in gruplar["zehirler"])
    kontrol("yanabilir zehirler Gd ve Er", set(gruplar.get("yanabilir", ())) ==
            {"Gd155", "Gd157", "Er167"}, "-> %r" % (gruplar.get("yanabilir"),))
    kontrol("uzun omurlu fisyon urunleri", set(gruplar.get("uzun_omurlu", ())) ==
            {"Tc99", "I129", "Cs137"}, "-> %r" % (gruplar.get("uzun_omurlu"),))
    diger = gruplar.get("diger", ())
    kontrol("'digerleri' grubu kalan nuklidleri tutar (H1, O16, Xe136)",
            {"H1", "O16", "Xe136"} <= set(diger) and "U235" not in diger)
    setler = {s.anahtar: s.nuklidler for s in nk.hazir_setler(SENTETIK_ADLAR)}
    kontrol("hazir setler: temel, pu, zehirler, minor, atik",
            list(setler) == ["temel", "pu", "zehirler", "minor", "atik"], "-> %r" % list(setler))
    kontrol("'Temel' seti sema varsayilaniyla ayni",
            list(setler["temel"]) == sema.VARSAYILAN_TUKENME["izlenen"])
    kontrol("'Pu vektoru' Pu238-242", setler["pu"] == ("Pu238", "Pu239", "Pu240",
                                                         "Pu241", "Pu242"))
    kontrol("'Minor aktinitler' zincirde olmayan Cm245'i dondurmez",
            "Cm245" not in setler["minor"] and "Am242_m1" in setler["minor"],
            "-> %r" % (setler["minor"],))
    bulunan = nk.ara("xe-13", SENTETIK_ADLAR)
    kontrol("arama normallestirmeli: 'xe-13' -> Xe135, Xe136", bulunan == ["Xe135", "Xe136"],
            "-> %r" % bulunan)
    kontrol("arama 'am242m' -> Am242_m1", nk.ara("am242m", SENTETIK_ADLAR) == ["Am242_m1"])
    kontrol("bos arama hepsini dondurur", len(nk.ara("  ", SENTETIK_ADLAR))
            == len(SENTETIK_ADLAR))


# ============================================================================
# 2. Zincir okuma (gercek zincirler)
# ============================================================================

def test_zincir_nuklidleri():
    print("\n[NS3] ZINCIR: nuklid adlari hizli ve onbellekli okunuyor")
    from cekirdek import nuklidler as nk
    from cekirdek import tukenme, veri_bilgi
    if _zincir_yolu() is None:
        return
    beklenen = {"termal": 3820, "hizli": 3820, "casl_termal": 228, "casl_hizli": 228}
    for tur, dosya in sorted(tukenme.ZINCIRLER.items()):
        yol = os.path.join(veri_bilgi.zincir_dizini(), dosya)
        nk.onbellegi_temizle()
        t0 = time.perf_counter()
        adlar = nk.zincir_nuklidleri(yol)
        sure = time.perf_counter() - t0
        kontrol("%s: %d nuklid, %.3f s (< 1 s)" % (tur, len(adlar), sure),
                len(adlar) == beklenen[tur] and sure < 1.0)
        t0 = time.perf_counter()
        ikinci = nk.zincir_nuklidleri(yol)
        kontrol("%s: ikinci okuma onbellekten (%.1f ms)" % (tur, (time.perf_counter() - t0) * 1e3),
                ikinci is adlar)
        setler = {s.anahtar: s.nuklidler for s in nk.hazir_setler(adlar)}
        kontrol("%s: 'Temel' setinin 7 nuklidi de zincirde" % tur, len(setler["temel"]) == 7)
    try:
        nk.zincir_nuklidleri(os.path.join(KOK, "yok_boyle_zincir.xml"))
        kontrol("olmayan zincir hata veriyor", False)
    except nk.ZincirOkunamadi as e:
        kontrol("olmayan zincir ZincirOkunamadi veriyor", "yok_boyle_zincir" in str(e),
                "-> %s" % e)


# ============================================================================
# 3. Dogrulama: yazim hatasi HATA + oneri
# ============================================================================

def _pwr_tukenme():
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))


def _izlenen_bulgulari(spec):
    from cekirdek import dogrula as dg
    return [b for b in dg.tukenme_kontrol(spec) if "izlenen" in b.mesaj]


@gereksinim("R-A2-01")
def test_dogrulama_yazim_hatasi():
    print("\n[NS4] DOGRULAMA: zincirde olmayan izlenen nuklid HATA + oneri")
    if _zincir_yolu() is None:
        return
    sp = _pwr_tukenme()
    kontrol("ornekteki izlenen listesi temiz", _izlenen_bulgulari(sp) == [],
            "-> %r" % [b.mesaj for b in _izlenen_bulgulari(sp)])
    sp["tukenme"]["izlenen"] = ["U235", "Xe-135", "Am242m", "Xyz1"]
    bulgular = _izlenen_bulgulari(sp)
    metin = " | ".join("%s: %s (%s)" % (b.seviye, b.mesaj, b.oneri) for b in bulgular)
    kontrol("3 hata bulgusu (Xe-135, Am242m, Xyz1)",
            len(bulgular) == 3 and all(b.seviye == "hata" for b in bulgular), "-> %s" % metin)
    kontrol("oneri 'Xe-135 → Xe135?'", any("Xe-135 → Xe135?" in (b.oneri or "")
                                           for b in bulgular), "-> %s" % metin)
    kontrol("oneri 'Am242m → Am242_m1?'", any("Am242m → Am242_m1?" in (b.oneri or "")
                                              for b in bulgular), "-> %s" % metin)
    # Zincir okunamiyorsa izlenen icin YENI hata uretilmez (zincir bulgusu yeter).
    eski = os.environ.get("OPENMC_CHAIN_FILE")
    os.environ["OPENMC_CHAIN_FILE"] = os.path.join(KOK, "yok_dizin", "yok.xml")
    try:
        from cekirdek import dogrula as dg
        hepsi = dg.tukenme_kontrol(sp)
    finally:
        if eski is None:
            os.environ.pop("OPENMC_CHAIN_FILE", None)
        else:
            os.environ["OPENMC_CHAIN_FILE"] = eski
    kontrol("zincir yokken: zincir hatasi var, izlenen hatasi yok",
            any("zincir" in b.mesaj for b in hepsi)
            and not any("izlenen" in b.mesaj for b in hepsi),
            "-> %r" % [b.mesaj for b in hepsi])


# ============================================================================
# 4. Sonuc okuma: bulunamayanlar sessizce atlanmaz; izlenen parametre
# ============================================================================

@gereksinim("R-A2-02")
def test_sonuc_oku_bulunamayan():
    print("\n[NS5] SONUC OKUMA: yazim hatasi 'bulunamayan'da, secim h5'ten yeniden okunur")
    from cekirdek import sema, tukenme
    bulunan = _onceki_h5()
    if bulunan is None:
        return
    _ornek, h5 = bulunan
    kayit = sema.yukle(os.path.join(os.path.dirname(h5), tukenme.SPEC_KAYDI))
    varsayilan = tukenme.sonuc_oku(h5, kayit)
    kontrol("eski donus anahtarlari korunuyor",
            {"zaman_d", "yanma", "k", "k_sapma", "atomlar", "yogunluk",
             "adim_sayisi"} <= set(varsayilan), "-> %r" % sorted(varsayilan))
    kontrol("izlenen verilmezse spec'teki liste", set(varsayilan["yogunluk"]["uo2"])
            == set(kayit["tukenme"]["izlenen"]))
    kontrol("temiz listede bulunamayan bos", varsayilan.get("bulunamayan") == [],
            "-> %r" % varsayilan.get("bulunamayan"))
    t0 = time.perf_counter()
    s = tukenme.sonuc_oku(h5, kayit, izlenen=["U235", "Xe-135", "Pu238", "Am242_m1"])
    sure = time.perf_counter() - t0
    kontrol("yazim hatasi sessizce atlanmiyor: bulunamayan = ['Xe-135']",
            s.get("bulunamayan") == ["Xe-135"], "-> %r" % s.get("bulunamayan"))
    kontrol("yeni secim (Pu238, Am242_m1) kosu tekrarlanmadan okundu",
            {"U235", "Pu238", "Am242_m1"} == set(s["yogunluk"]["uo2"]),
            "-> %r" % sorted(s["yogunluk"]["uo2"]))
    kontrol("ayni h5'ten yeniden okuma onbellekli (%.3f s < 0.5 s)" % sure, sure < 0.5)
    kontrol("k ayni", s["k"] == varsayilan["k"])


# ============================================================================
# 5. Eski JSON'lar: izlenen aynen yuklenir ve kaydedilir
# ============================================================================

@gereksinim("R-A2-03")
def test_eski_json_izlenen():
    print("\n[NS6] ESKI JSON: izlenen listesi aynen yukleniyor ve kaydediliyor")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz.sekme_tukenme import TukenmeSekmesi
    sp = _pwr_tukenme()
    ozgun = list(sp["tukenme"]["izlenen"])
    t = TukenmeSekmesi()
    t.spec_yukle(sp)
    t.bekle()
    kontrol("secici eski listeyi gosteriyor", t.izlenen.secim() == ozgun,
            "-> %r" % t.izlenen.secim())
    t.guc.setValue(39.0)                       # baska bir alan kaydedilir
    kontrol("kaydedince liste aynen (sira dahil)", sp["tukenme"]["izlenen"] == ozgun,
            "-> %r" % sp["tukenme"]["izlenen"])
    sp2 = _pwr_tukenme()
    sp2["tukenme"]["izlenen"] = ["U235", "Xe-135"]
    t.spec_yukle(sp2)
    t.bekle()
    t.guc.setValue(38.0)
    kontrol("zincirde olmayan yazim bile silinmeden korunuyor",
            sp2["tukenme"]["izlenen"] == ["U235", "Xe-135"], "-> %r" % sp2["tukenme"]["izlenen"])
    t.izlenen.ekle("Pu239")
    kontrol("secim degisince spec'e LISTE olarak yaziliyor",
            sp2["tukenme"]["izlenen"] == ["U235", "Xe-135", "Pu239"],
            "-> %r" % sp2["tukenme"]["izlenen"])
    kontrol("secici Gelismis'in DISINDA gorunur bir bolumde",
            not t.gelismis.isAncestorOf(t.izlenen) and t.izlenen.isVisibleTo(t))
    t.bekle()


# ============================================================================
# 6. Widget
# ============================================================================

def _yaprak_gorunur(secici, ad):
    return any(not o.isHidden() and not o.parent().isHidden()
               for o in secici.ogeler(ad))


def test_secici_widget():
    print("\n[NS7] SECICI: arama, set dugmesi, cip kaldirma, sinyal, zincir degisimi")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz.nuklid_secici import NuklidSecici
    w = NuklidSecici()
    w.adlar_ayarla(SENTETIK_ADLAR, "sentetik")
    gelen = []
    w.secim_degisti.connect(lambda liste: gelen.append(list(liste)))
    w.arama.setText("xe-13")
    kontrol("arama 'xe-13': Xe135 gorunur, U235 gizli",
            _yaprak_gorunur(w, "Xe135") and not _yaprak_gorunur(w, "U235"))
    w.arama.setText("")
    kontrol("arama temizlenince U235 gorunur", _yaprak_gorunur(w, "U235"))
    w.set_dugmeleri["pu"].click()
    kontrol("'Pu vektoru' dugmesi 5 Pu ekledi", w.secim() == ["Pu238", "Pu239", "Pu240",
                                                              "Pu241", "Pu242"],
            "-> %r" % w.secim())
    kontrol("sinyal secim listesini tasidi", gelen and gelen[-1] == w.secim())
    kontrol("grup basliginda secili sayisi", "5/5" in w.grup_ogesi("plutonyum").text(0),
            "-> %r" % w.grup_ogesi("plutonyum").text(0))
    kontrol("5 cip", sorted(w.cipler) == sorted(w.secim()))
    w.cipler["Pu240"].kaldir.click()
    kontrol("cipteki x Pu240'i kaldirdi", "Pu240" not in w.secim() and "Pu240" not in w.cipler)
    kontrol("agacta Pu240 isareti kalkti", all(
        not w.isaretli_mi(o) for o in w.ogeler("Pu240")))
    oge = w.ogeler("Xe135")[0]
    from PySide6 import QtCore
    oge.setCheckState(0, QtCore.Qt.Checked)
    kontrol("agacta isaretleme secime ekledi", w.secim()[-1] == "Xe135")
    kontrol("ayni nuklidin diger gruptaki ogesi de isaretli",
            all(w.isaretli_mi(o) for o in w.ogeler("Xe135")))
    w.secim_ayarla(["U235", "Xe-135"], sinyal=False)
    kontrol("zincirde olmayan secim kirmizi cip (silinmez)",
            w.secim() == ["U235", "Xe-135"] and w.cipler["Xe-135"].eksik
            and not w.cipler["U235"].eksik)
    kontrol("kirmizi cipte oneri", "Xe135" in w.cipler["Xe-135"].toolTip(),
            "-> %r" % w.cipler["Xe-135"].toolTip())
    w.adlar_ayarla(("U235", "U238"), "kucuk")
    kontrol("zincir degisti: secim korunuyor", w.secim() == ["U235", "Xe-135"])
    w.secim_ayarla(["U235", "Pu239"], sinyal=False)
    kontrol("yeni zincirde olmayan Pu239 kirmizi", w.cipler["Pu239"].eksik)
    w.adlar_ayarla(SENTETIK_ADLAR, "sentetik")
    kontrol("zincir geri gelince kirmizi kalkti", not w.cipler["Pu239"].eksik)
    once = len(gelen)
    w.temizle.click()
    kontrol("temizle hepsini kaldirdi ve bildirdi", w.secim() == [] and len(gelen) == once + 1)
    w.adlar_ayarla(None, "zincir okunamadı")
    kontrol("zincir okunamiyorsa liste bos, uyari gorunur",
            w.agac.topLevelItemCount() == 0 and "okunamadı" in w.bilgi.text())
    w.adlar_ayarla(SENTETIK_ADLAR, "sentetik")
    w.set_dugmeleri["temel"].click()
    w.secim_ayarla(w.secim() + ["Xe-135"], sinyal=False)
    w.resize(560, 520)
    w.show()
    uyg.processEvents()
    os.makedirs(EKRAN_DIZINI, exist_ok=True)
    yol = os.path.join(EKRAN_DIZINI, "nuklid_secici.png")
    kontrol("ekran goruntusu kaydedildi: %s" % yol, w.grab().save(yol))
    w.close()


# ============================================================================
# 7. CSV disa aktarma (saf)
# ============================================================================

SAHTE = {"zaman_d": [0.0, 0.5, 2.0], "yanma": [0.0, 0.02, 0.08],
         "k": [1.35, 1.33, 1.31], "k_sapma": [0.0012, 0.0011, 0.0010],
         "atomlar": {"uo2": {"U235": [1.0e21, 9.9e20, 9.7e20], "Xe135": [0.0, 1.5e16, 2e16]}},
         "yogunluk": {"uo2": {"U235": [7.0e-4, 6.9e-4, 6.8e-4],
                              "Xe135": [0.0, 1.1e-8, 1.4e-8]}},
         "adim_sayisi": 2, "bulunamayan": []}


@gereksinim("R-A2-04")
def test_csv_bicimi():
    print("\n[NS8] CSV: zaman, yanma, k, sigma, malzeme x nuklid atom ve yogunluk")
    from arayuz.tukenme_sonuc import csv_metni
    metin = csv_metni(SAHTE)
    satirlar = list(csv.reader(io.StringIO(metin)))
    beklenen_baslik = ["zaman [gün]", "yanma [MWd/kg]", "k", "σ",
                       "uo2 U235 atom", "uo2 U235 [atom/b-cm]",
                       "uo2 Xe135 atom", "uo2 Xe135 [atom/b-cm]"]
    kontrol("baslik", satirlar[0] == beklenen_baslik, "-> %r" % satirlar[0])
    kontrol("3 veri satiri", len(satirlar) == 4)
    kontrol("ondalik NOKTA, virgul yalnizca ayirici",
            satirlar[2][0] == "0.5" and all("," not in h for s in satirlar[1:] for h in s))
    kontrol("sayilar tam hassasiyetle geri okunuyor",
            float(satirlar[3][6]) == 2e16 and float(satirlar[2][5]) == 6.9e-4
            and float(satirlar[1][3]) == 0.0012)
    import locale
    eski = locale.setlocale(locale.LC_NUMERIC)
    try:
        try:
            locale.setlocale(locale.LC_NUMERIC, "tr_TR.UTF-8")
        except locale.Error:
            pass
        kontrol("yerel ayardan bagimsiz (tr_TR'de de nokta)", csv_metni(SAHTE) == metin)
    finally:
        locale.setlocale(locale.LC_NUMERIC, eski)
    bos = csv_metni(dict(SAHTE, atomlar={}, yogunluk={}))
    kontrol("nuklid yokken yalnizca zaman/yanma/k/σ", list(csv.reader(io.StringIO(bos)))[0]
            == beklenen_baslik[:4])


# ============================================================================
# 8. Sekme: onceki sonuc yeni secimle, kosu tekrarlanmadan; CSV dugmesi
# ============================================================================

def _cizgi_etiketleri(sekme):
    return sorted(c.get_label() for c in sekme.eksen_n.get_lines()
                  if not c.get_label().startswith("_"))


def _sekme_yeni_secim(sekme, beklenen_satir):
    """Onceki sonucu gosteren sekmede secimi degistirir; grafik/tablo/CSV sinanir."""
    from PySide6 import QtWidgets
    sekme.bekle()
    kontrol("onceki sonuc gosteriliyor (%d satir)" % sekme.tablo.rowCount(),
            sekme.tablo.rowCount() == beklenen_satir)
    kontrol("baslangicta Xe135 cizgisi var", "Xe135" in _cizgi_etiketleri(sekme),
            "-> %r" % _cizgi_etiketleri(sekme))
    sekme.izlenen.secim_ayarla(["Pu238", "Am242_m1", "Xe-135"])
    kontrol("yeni secim cizildi (Pu238, Am242_m1), kosu baslamadi",
            _bekle(lambda: "Pu238" in _cizgi_etiketleri(sekme), 20)
            and sekme._surec is None, "-> %r" % _cizgi_etiketleri(sekme))
    kontrol("secimden cikan Xe135 cizgisi kalkti", "Xe135" not in _cizgi_etiketleri(sekme))
    kontrol("bulunamayan 'Xe-135' kullaniciya soyleniyor",
            "Xe-135" in sekme.bulunamayan_etiket.text()
            and sekme.bulunamayan_etiket.isVisibleTo(sekme),
            "-> %r" % sekme.bulunamayan_etiket.text())
    kontrol("secim degisikligi sonucu 'eski' yapmiyor",
            "Eski sonuç" not in sekme.onceki_etiket.text(), "-> %r" % sekme.onceki_etiket.text())
    hedef = os.path.join(EKRAN_DIZINI, "tukenme_secim.csv")
    os.makedirs(EKRAN_DIZINI, exist_ok=True)
    eski = QtWidgets.QFileDialog.getSaveFileName
    QtWidgets.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (hedef, "CSV (*.csv)"))
    try:
        kontrol("CSV dugmesi etkin", sekme.csv_dugmesi.isEnabled())
        sekme.csv_dugmesi.click()
    finally:
        QtWidgets.QFileDialog.getSaveFileName = eski
    with open(hedef, encoding="utf-8") as f:
        satirlar = list(csv.reader(f))
    kontrol("CSV yazildi: secili nuklidler, %d satir" % (len(satirlar) - 1),
            len(satirlar) == beklenen_satir + 1 and "uo2 Pu238 [atom/b-cm]" in satirlar[0]
            and not any("Xe135" in h for h in satirlar[0]), "-> %r" % satirlar[0])
    # Okuma surerken secim yine degisirse SON secim gosterilir.
    sekme.izlenen.secim_ayarla(["U235"])
    sekme.izlenen.secim_ayarla(["U238", "Pu239"])
    sekme.bekle()
    kontrol("art arda iki secim: son secim cizildi", _cizgi_etiketleri(sekme)
            == ["Pu239", "U238"] and sekme.bulunamayan_etiket.isHidden(),
            "-> %r" % _cizgi_etiketleri(sekme))


@gereksinim("R-A2-03")
def test_sekme_onceki_sonuc_yeni_secim():
    print("\n[NS9] SEKME: pwr_tukenme'nin onceki sonucu yeni secimle, kosu tekrarlanmadan")
    uyg = _qt()
    if uyg is None:
        return
    bulunan = _onceki_h5()
    if bulunan is None or _zincir_yolu() is None:
        return
    ornek, _h5 = bulunan
    from cekirdek import sema
    from arayuz.sekme_tukenme import TukenmeSekmesi
    t = TukenmeSekmesi()
    t.proje_ayarla(None, okuma_kaynagi=ornek)
    t.spec_yukle(sema.yukle(ornek))
    _sekme_yeni_secim(t, 9)
    t.resize(900, 1500)
    t.show()
    uyg.processEvents()
    yol = os.path.join(EKRAN_DIZINI, "tukenme_sekmesi.png")
    kontrol("ekran goruntusu kaydedildi: %s" % yol, t.grab().save(yol))
    t.close()


def test_kisa_kosu_yeni_secim(gecici):
    """Onceki sonuc yoksa da (CI) ayni kabul: kisa bir CASL kosusu."""
    print("\n[NS10] KISA KOSU: yazim hatasi raporlaniyor, sekme yeni secimi kosmadan ciziyor")
    import shutil
    from cekirdek import sema, tukenme
    sp = _pwr_tukenme()
    sp["ayarlar"].update(parcacik=1000, cevrim=15, pasif=5)
    sp["calistirma"].update(is_parcacigi=ISLEM_PARCACIGI)
    sp["tukenme"].update(zincir="casl_termal", entegrator="predictor", adimlar=[0.5, 1.5])
    dizin = os.path.join(gecici, "tukenme")
    h5, _bilgi = tukenme.calistir(sp, dizin)
    s = tukenme.sonuc_oku(h5, sp, izlenen=["U235", "Xe-135"])
    kontrol("kisa kosu: 'Xe-135' bulunamayan", s["bulunamayan"] == ["Xe-135"])
    uyg = _qt()
    if uyg is None:
        return
    from arayuz.sekme_tukenme import TukenmeSekmesi
    proje = os.path.join(gecici, "proje.json")
    sp_ui = copy.deepcopy(sp)
    # Kendine ozgu kosu dizini: eski calistirici butun YAVAS testlere AYNI gecici
    # dizini verir; test_tukenme_temel de "arayuz" adini kullanir (FileExistsError).
    sp_ui["calistirma"]["dizin"] = "arayuz_nuklid"
    shutil.copytree(dizin, tukenme.kosu_dizini(sp_ui, proje))
    sema.kaydet(sp_ui, proje)
    t = TukenmeSekmesi()
    t.proje_ayarla(proje)
    t.spec_yukle(sp_ui)
    _sekme_yeni_secim(t, 3)


HIZLI = [test_normallestirme_ve_oneri, test_gruplar_ve_setler_sentetik,
         test_zincir_nuklidleri, test_dogrulama_yazim_hatasi, test_sonuc_oku_bulunamayan,
         test_eski_json_izlenen, test_secici_widget, test_csv_bicimi,
         test_sekme_onceki_sonuc_yeni_secim]
YAVAS = [test_kisa_kosu_yeni_secim]
