# -*- coding: utf-8 -*-
"""
test_hesap_sekmeleri.py -- Dalga 3: Calistir, Analiz ve Tukenme sekmeleri.

  * sayfa yapisi: alt sekme (QTabWidget) YOK; bolumler moda gore gorunur
  * Analiz listeleri uygunluk.gecerli_taramalar / gecerli_hedefler ile BIREBIR
  * gecersiz secim baslatilmaz ("yine de devam et" yok)
  * proje kusagi: proje degistikten SONRA biten kosu / analiz / tukenme
    okumasi yeni projeye sonuc yazmaz (sahte alt surec ve isci ile, uctan uca)
  * sonuc_degisti / sonuc_var API'si
  * is parcacigi ve kosu dizini spec["calistirma"]'ya yaziliyor

Yalnizca offscreen calisir; modal diyaloglar exec() EDILMEZ (yamalanir).
"""

import copy
import os
import re
import shutil
import stat
import sys
import tempfile
import time
import types
import warnings

from testler.ortak_test import kontrol, ORNEK, KOK   # noqa: F401

warnings.filterwarnings("ignore")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _qt():
    try:
        from PySide6 import QtWidgets
    except Exception as e:                         # pragma: no cover
        kontrol("PySide6 yok, hesap sekmesi testi atlandi", True, "-> %s" % e)
        return None
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _spec(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _gorunur(w, ust):
    return w.isVisibleTo(ust)


def _bekle(kosul, saniye=30.0):
    """Olay dongusunu kosul saglanana (ya da zaman asimina) kadar dondurur."""
    from PySide6 import QtWidgets
    son = time.time() + saniye
    while time.time() < son:
        QtWidgets.QApplication.processEvents()
        if kosul():
            return True
        time.sleep(0.02)
    QtWidgets.QApplication.processEvents()
    return kosul()


def _gelismis_ayari_sil(anahtar):
    from PySide6 import QtCore
    QtCore.QSettings("openmc_arayuz", "arayuz").remove("gelismis/" + anahtar)


def _betik(dizin, ad, govde):
    yol = os.path.join(dizin, ad)
    with open(yol, "w") as f:
        f.write("#!/bin/sh\n" + govde)
    os.chmod(yol, os.stat(yol).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return yol


SAHTE_K = {"mod": "eigenvalue", "keff": (1.18342, 0.00061), "cevrim": 100, "pasif": 20,
           "parcacik": 1000, "entropi": [], "tallyler": {"reaksiyonlar": "TALLY-OZDEGER"}}
SAHTE_S = {"mod": "fixed source", "keff": None, "cevrim": 50, "pasif": 0,
           "parcacik": 2000, "entropi": [], "tallyler": {"akı": "TALLY-SABIT"}}
SAHTE_TUKENME = {"zaman_d": [0.0, 10.0], "yanma": [0.0, 0.4], "k": [1.30, 1.28],
                 "k_sapma": [0.001, 0.001], "atomlar": {},
                 "yogunluk": {"uo2": {"U235": [7e-4, 6.9e-4]}}, "adim_sayisi": 1}


# ============================================================================
# 1. Calistir: sayfa yapisi
# ============================================================================

def test_calistir_sayfa_yapisi():
    print("\n[H1] CALISTIR: tek akisli sayfa, bolumler moda gore")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtWidgets
    from arayuz.sekme_calistir import CalistirSekmesi
    _gelismis_ayari_sil("calistir_ayrinti")
    c = CalistirSekmesi()
    c.spec_ayarla(_spec("pwr_17x17"), None)
    kontrol("alt sekme (QTabWidget) yok", c.findChildren(QtWidgets.QTabWidget) == [],
            "-> %d" % len(c.findChildren(QtWidgets.QTabWidget)))
    kontrol("kosu oncesi: bos durum gorunur; grafik, kart, guc haritasi, ayrinti gizli",
            _gorunur(c.bos, c) and not _gorunur(c.tuval, c) and not _gorunur(c.kart, c)
            and not _gorunur(c.guc_harita, c) and not _gorunur(c.ayrinti, c))
    kontrol("is parcacigi ve kosu dizini bu sayfada",
            _gorunur(c.is_parcacigi, c) and _gorunur(c.kosu_dizini, c))

    # --- ozdeger sonucu ---
    c._sonuc_goster(copy.deepcopy(SAHTE_K), "/yok/statepoint.100.h5")
    kontrol("ozdeger sonucu: kart ve k-eff gorunur, bos durum gizli",
            _gorunur(c.kart, c) and _gorunur(c.keff_etiket, c) and not _gorunur(c.bos, c))
    kontrol("ozdeger: tally tablolari kartta DEGIL (ayrintili ciktida)",
            not _gorunur(c.tally_metin, c)
            and "TALLY-OZDEGER" in c.sonuc_metin.toPlainText())
    kontrol("ayrintili cikti gorunur ve varsayilan KAPALI",
            _gorunur(c.ayrinti, c) and not c.ayrinti.acik_mi())
    kontrol("guc verisi yok -> guc haritasi gizli", not _gorunur(c.guc_harita, c))

    # --- basarisiz kosu: ayrintili cikti kendiliginden acilir ---
    c._bitti(1, None)
    kontrol("basarisiz kosu: ayrintili cikti kendiliginden acildi", c.ayrinti.acik_mi())
    kontrol("basarisiz kosu: sonuc yok, kart nedenini soyluyor",
            not c.sonuc_var() and "başarısız" in c.durum_etiket.text().lower()
            and _gorunur(c.kart, c), "-> %r" % c.durum_etiket.text())
    _gelismis_ayari_sil("calistir_ayrinti")

    # --- sabit kaynak: k grafigi ve k-eff yok, tally'ler kartta ---
    c2 = CalistirSekmesi()
    c2.spec_ayarla(_spec("zirh_kure"), None)
    c2._sonuc_goster(copy.deepcopy(SAHTE_S), "/yok/statepoint.50.h5")
    kontrol("sabit kaynak: k-eff ve grafik gizli",
            not _gorunur(c2.keff_etiket, c2) and not _gorunur(c2.tuval, c2))
    kontrol("sabit kaynak: tally sonuclari kartta gorunur",
            _gorunur(c2.tally_metin, c2) and "TALLY-SABIT" in c2.tally_metin.toPlainText())

    # --- guc haritasi: yalnizca guc dagilimi etkin VE sonucta guc verisi varken ---
    guc = {"faktorler": {"F_dH": 1.2, "F_q": 1.5, "sicak_cubuk": (3, 4),
                         "sicak_dilim": None, "eksenel_dilim": 1},
           "dagilim": {}, "korunum": 0.0}
    sahte = dict(copy.deepcopy(SAHTE_K), guc=guc)
    for ad, acik, beklenen in (("pwr_3b", True, True), ("pwr_3b", False, False),
                               ("pwr_pinhucre", True, False)):
        s = _spec(ad)
        s.setdefault("guc_dagilimi", {})["var"] = acik
        w = CalistirSekmesi()
        w.guc_harita.sonuc_ayarla = lambda *_a, **_k: None   # cizim bu testin konusu degil
        w.spec_ayarla(s, None)
        w._sonuc_goster(copy.deepcopy(sahte), "/yok/sp.h5")
        kontrol("guc haritasi %s (guc_dagilimi.var=%s): %s"
                % (ad, acik, "gorunur" if beklenen else "gizli"),
                _gorunur(w.guc_harita, w) == beklenen)
    uyg  # noqa: B018


# ============================================================================
# 2. Calistir: is parcacigi ve kosu dizini spec'e yaziliyor
# ============================================================================

def test_calistir_calistirma_alanlari():
    print("\n[H2] CALISTIR: is parcacigi ve kosu dizini spec['calistirma']'ya yaziliyor")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz.sekme_calistir import CalistirSekmesi
    c = CalistirSekmesi()
    yayilan = []
    c.degisti.connect(yayilan.append)
    s = _spec("pwr_pinhucre")
    s["calistirma"] = {"is_parcacigi": 3, "dizin": "benim_kosum"}
    gecici = tempfile.mkdtemp(prefix="calistirma_")
    try:
        proje = os.path.join(gecici, "proje.json")
        c.spec_ayarla(s, proje)
        kontrol("spec_ayarla degerleri yukledi (3, benim_kosum)",
                c.is_parcacigi.value() == 3 and c.kosu_dizini.text() == "benim_kosum")
        kontrol("yukleme sirasinda degisti YAYILMADI", yayilan == [], "-> %r" % yayilan)
        kontrol("cozulen dizin proje dizininde gosteriliyor",
                os.path.join(gecici, "benim_kosum") in c.dizin_yolu.text(),
                "-> %r" % c.dizin_yolu.text())
        c.is_parcacigi.setValue(5)
        kontrol("is parcacigi spec'e yazildi (5)", s["calistirma"]["is_parcacigi"] == 5)
        kontrol("degisti('calistirma') yayildi", yayilan == ["calistirma"], "-> %r" % yayilan)
        c.kosu_dizini.setText("yeni_dizin")
        c.kosu_dizini.editingFinished.emit()
        kontrol("kosu dizini spec'e yazildi", s["calistirma"]["dizin"] == "yeni_dizin")
        kontrol("ikinci degisiklik de yayildi", yayilan == ["calistirma", "calistirma"])
        c.kosu_dizini.editingFinished.emit()
        kontrol("degismeyen deger icin tekrar yayilmadi", len(yayilan) == 2)
        c.kosu_dizini.setText("   ")
        c.kosu_dizini.editingFinished.emit()
        kontrol("bos dizin varsayilana ('kosu') doner", s["calistirma"]["dizin"] == "kosu"
                and c.kosu_dizini.text() == "kosu")
        s2 = _spec("pwr_17x17")
        s2["calistirma"] = {"is_parcacigi": 2, "dizin": "baska"}
        n = len(yayilan)
        c.spec_ayarla(s2, proje)
        kontrol("baska spec: degerler yeniden yuklendi (2, baska), yayilmadi",
                c.is_parcacigi.value() == 2 and c.kosu_dizini.text() == "baska"
                and len(yayilan) == n)
        kontrol("onceki spec degismedi", s["calistirma"]["dizin"] == "kosu")
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    uyg  # noqa: B018


# ============================================================================
# 3. Calistir: proje kusagi (sahte openmc ile uctan uca)
# ============================================================================

def test_calistir_kusak(gecici=None):
    """
    Onceki projede baslayan bir kosu, proje degistikten SONRA biterse sonucu
    yeni projeye yazilmamali. Eski kodda sifirla() suren kosuda hicbir sey
    yapmiyordu; kosu bitince k-eff yeni projede 'basarili' gorunuyordu.
    """
    print("\n[H3] CALISTIR: proje degistikten sonra biten kosu yeni projeye yazilmiyor")
    uyg = _qt()
    if uyg is None:
        return
    from cekirdek import kosucu
    from arayuz.sekme_calistir import CalistirSekmesi
    gecici = tempfile.mkdtemp(prefix="calistir_kusak_")
    eski = (kosucu.openmc_yolu, kosucu.son_statepoint, kosucu.sonuc_oku)
    try:
        exe = _betik(gecici, "sahte_openmc",
                     'echo "        1/1    1.10000"\n'
                     'echo "        2/1    1.11000    1.10500 +/- 0.00500"\n'
                     "sleep 0.8\nexit 0\n")
        kosucu.openmc_yolu = lambda: exe
        kosucu.son_statepoint = lambda d: os.path.join(d, "statepoint.100.h5")
        kosucu.sonuc_oku = lambda sp: copy.deepcopy(SAHTE_K)
        proje_a = os.path.join(gecici, "a", "proje.json")
        proje_b = os.path.join(gecici, "b", "proje.json")
        os.makedirs(os.path.dirname(proje_a)); os.makedirs(os.path.dirname(proje_b))

        # --- kontrol: proje degismezse sonuc gosterilir ---
        c = CalistirSekmesi()
        c.kapi_ayarla(lambda: (True, "hazır"))
        sa = _spec("pwr_pinhucre")
        c.spec_ayarla(sa, proje_a)
        c.calistir()
        kontrol("(on kosul) sahte kosu basladi", c._surec is not None)
        kontrol("entropi acik: grafik iki eksenli", len(c.figur.axes) == 2,
                "-> %d" % len(c.figur.axes))
        _bekle(lambda: c._surec is None)
        kontrol("ayni projede biten kosu: sonuc gosterildi",
                c._son_basarili and "1.18342" in c.keff_etiket.text())
        kontrol("canli cikti loga yazildi", "1/1" in c.log.toPlainText())

        # --- proje degisimi kosu surerken ---
        c2 = CalistirSekmesi()
        c2.kapi_ayarla(lambda: (True, "hazır"))
        sayac = []
        if hasattr(c2, "sonuc_degisti"):
            c2.sonuc_degisti.connect(lambda: sayac.append(c2.sonuc_var()))
        c2.spec_ayarla(copy.deepcopy(sa), proje_a)
        c2.calistir()
        c2.sifirla()                                   # ana pencere: _proje_degisti
        c2.spec_ayarla(_spec("godiva_kriter"), proje_b)
        kontrol("eski kosu surerken sayfa 'onceki projenin kosusu' diyor",
                "Önceki projenin" in c2.kapi_etiket.text(), "-> %r" % c2.kapi_etiket.text())
        kontrol("eski kosu surerken Durdur etkin", c2.d_durdur.isEnabled())
        _bekle(lambda: c2._surec is None)
        kontrol("proje degistikten sonra biten kosu: _son_basarili YOK",
                not c2._son_basarili)
        kontrol("yeni projede k-eff gosterilmiyor", "1.18342" not in c2.keff_etiket.text(),
                "-> %r" % c2.keff_etiket.text())
        kontrol("yeni projenin logu eski kosunun ciktisini icermiyor",
                "1/1" not in c2.log.toPlainText())
        kontrol("yeni projede sonuc metni bos", c2.sonuc_metin.toPlainText() == "")
        kontrol("sonuc_var() False ve hic True yayilmadi",
                hasattr(c2, "sonuc_var") and not c2.sonuc_var() and True not in sayac,
                "-> %r" % sayac)
        kontrol("kosu bitince Calistir yeniden kullanilabilir", c2.d_calistir.isEnabled())

        # --- entropi kapali: tek eksen; sabit kaynak: grafik yok ---
        c3 = CalistirSekmesi()
        c3.kapi_ayarla(lambda: (True, "hazır"))
        sk = copy.deepcopy(sa)
        sk["ayarlar"].setdefault("entropi_mesh", {})["var"] = False
        c3.spec_ayarla(sk, proje_a)
        c3.calistir()
        kontrol("entropi kapali: grafik TEK eksenli (yalniz k-eff)", len(c3.figur.axes) == 1,
                "-> %d" % len(c3.figur.axes))
        kontrol("kosu surerken grafik gorunur", _gorunur(c3.tuval, c3))
        _bekle(lambda: c3._surec is None)
        c4 = CalistirSekmesi()
        c4.kapi_ayarla(lambda: (True, "hazır"))
        kosucu.sonuc_oku = lambda sp: copy.deepcopy(SAHTE_S)
        c4.spec_ayarla(_spec("zirh_kure"), proje_a)
        c4.calistir()
        kontrol("sabit kaynak kosusu surerken k grafigi yok", not _gorunur(c4.tuval, c4))
        _bekle(lambda: c4._surec is None)
        kontrol("sabit kaynak sonucu gosterildi", c4._son_basarili)
    finally:
        kosucu.openmc_yolu, kosucu.son_statepoint, kosucu.sonuc_oku = eski
        shutil.rmtree(gecici, ignore_errors=True)
    uyg  # noqa: B018


# ============================================================================
# 4. Analiz: listeler uygunluk ile birebir
# ============================================================================

def _combo_verileri(combo):
    """Ayiraclar haric oge verileri."""
    return [combo.itemData(i) for i in range(combo.count()) if combo.itemText(i) != ""
            or combo.itemData(i) is not None]


def test_analiz_listeler():
    print("\n[H4] ANALIZ: parametre ve hedef listeleri uygunluk ile birebir")
    uyg = _qt()
    if uyg is None:
        return
    import glob
    from PySide6 import QtWidgets
    from cekirdek import uygunluk
    from arayuz import sekme_analiz as sa
    from arayuz.sekme_analiz import AnalizSekmesi
    kontrol("alt sekme (QTabWidget) yok",
            AnalizSekmesi().findChildren(QtWidgets.QTabWidget) == [])
    tur_hatasi, hedef_hatasi, sira_hatasi, mod_hatasi, gel_hatasi = [], [], [], [], []
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        ad = os.path.basename(yol)[:-5]
        spec = _spec(ad)
        an = AnalizSekmesi()
        an.gelismis.ac(True)
        an.spec_ayarla(spec, None)
        katsayi = uygunluk.gecerli_taramalar(spec, "katsayi")
        kritik = uygunluk.gecerli_taramalar(spec, "kritik")
        if not katsayi:
            kontrol("%s: gecerli parametre yok -> bos durum nedeni soyluyor" % ad,
                    _gorunur(an.bos, an) and not _gorunur(an.icerik, an)
                    and an.bos.metin.text() != "", "-> %r" % an.bos.metin.text())
            continue
        turler = [t for t in _combo_verileri(an.tur) if t is not None]
        if sorted(turler) != sorted(katsayi):
            tur_hatasi.append((ad, turler, katsayi))
        # ana parametreler etutlerden once
        ileri = [i for i, t in enumerate(turler) if t in sa.GELISMIS_PARAMETRELER]
        ana = [i for i, t in enumerate(turler) if t not in sa.GELISMIS_PARAMETRELER]
        if ileri and ana and min(ileri) < max(ana):
            sira_hatasi.append((ad, turler))
        for t in katsayi:
            an.tur.setCurrentIndex(an.tur.findData(t))
            beklenen = uygunluk.gecerli_hedefler(spec, t)
            gercek = [an.hedef.itemData(i) for i in range(an.hedef.count())]
            satir = an.form.isRowVisible(an.hedef_etiket)
            if gercek != beklenen or satir != (beklenen != [None]):
                hedef_hatasi.append((ad, t, gercek, beklenen, satir))
        # kritik arama
        modlar = [an.mod.itemData(i) for i in range(an.mod.count())]
        if ("arama" in modlar) != bool(kritik) or \
                an.form.isRowVisible(an.e_mod) != (len(modlar) > 1):
            mod_hatasi.append((ad, modlar, kritik))
        if kritik:
            an.mod.setCurrentIndex(an.mod.findData("arama"))
            k_turler = [t for t in _combo_verileri(an.tur) if t is not None]
            if sorted(k_turler) != sorted(kritik) or \
                    any(t not in uygunluk.KRITIK_PARAMETRELER for t in k_turler):
                mod_hatasi.append((ad, "kritik", k_turler, kritik))
            an.mod.setCurrentIndex(an.mod.findData("tarama"))
        # Gelismis kapaliyken etutler listede yok
        an.gelismis.ac(False)
        kapali = [t for t in _combo_verileri(an.tur) if t is not None]
        beklenen_kapali = [t for t in katsayi if t not in sa.GELISMIS_PARAMETRELER] or katsayi
        if sorted(kapali) != sorted(beklenen_kapali):
            gel_hatasi.append((ad, kapali, beklenen_kapali))
        an.gelismis.ac(True)
    kontrol("11 ornekte parametre listesi = uygunluk.gecerli_taramalar", not tur_hatasi,
            "-> %r" % tur_hatasi[:2])
    kontrol("tasarim etutleri (Gelismis) ana parametrelerden sonra", not sira_hatasi,
            "-> %r" % sira_hatasi[:2])
    kontrol("her parametrede hedef listesi = uygunluk.gecerli_hedefler; kor ayarinda "
            "hedef satiri gizli", not hedef_hatasi, "-> %r" % hedef_hatasi[:2])
    kontrol("kritik arama yalnizca gecerli KRITIK_PARAMETRELER ile; tek modda mod "
            "satiri gizli", not mod_hatasi, "-> %r" % mod_hatasi[:2])
    kontrol("Gelismis kapaliyken yogunluk/yaricap/adim listede yok", not gel_hatasi,
            "-> %r" % gel_hatasi[:2])

    # --- somut ornekler (kullanicinin sikayeti: UO2'ye bor) ---
    an = AnalizSekmesi()
    an.gelismis.ac(True)
    an.spec_ayarla(_spec("pwr_pinhucre"), None)
    an.tur.setCurrentIndex(an.tur.findData("bor_ppm"))
    hedefler = [an.hedef.itemData(i) for i in range(an.hedef.count())]
    kontrol("pin hucre, bor: yalnizca su (uo2 YOK)", hedefler == ["su"], "-> %r" % hedefler)
    an.tur.setCurrentIndex(an.tur.findData("void_orani"))
    hedefler = [an.hedef.itemData(i) for i in range(an.hedef.count())]
    kontrol("pin hucre, void: yalnizca sogutucu (su)", hedefler == ["su"], "-> %r" % hedefler)
    an.spec_ayarla(_spec("tamburlu_kor"), None)
    turler = _combo_verileri(an.tur)
    kontrol("tamburlu: bor ve void yok, tambur donmesi var",
            "bor_ppm" not in turler and "void_orani" not in turler
            and "tambur_donme" in turler, "-> %r" % turler)
    an.tur.setCurrentIndex(an.tur.findData("tambur_donme"))
    kontrol("tambur donmesi: hedef satiri gizli (kor ayari)",
            not an.form.isRowVisible(an.hedef_etiket))
    an.spec_ayarla(_spec("godiva_kriter"), None)
    kontrol("godiva: yalnizca yakit sicakligi, kritik arama yok",
            _combo_verileri(an.tur) == ["yakit_sicaklik"] and an.mod.findData("arama") < 0)
    an.spec_ayarla(_spec("pwr_17x17"), None)
    kontrol("tambursuz modelde tambur donmesi yok, kor adimi yok (tek_demet)",
            an.tur.findData("tambur_donme") < 0 and an.tur.findData("kor_adim") < 0)
    kontrol("gorunen adlarda uygulama notu yok (rho0, alfa, '--')",
            not any(re.search(r"rho0|alfa|--", an.tur.itemText(i))
                    for i in range(an.tur.count())))
    uyg  # noqa: B018


def test_analiz_secim_ve_red():
    print("\n[H5] ANALIZ: secim sekme degisiminde korunuyor; gecersiz secim baslatilmiyor")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtWidgets
    from arayuz.sekme_analiz import AnalizSekmesi
    spec = _spec("pwr_17x17")
    an = AnalizSekmesi()
    an.kapi_ayarla(lambda: (True, "hazır"))
    an.spec_ayarla(spec, None)
    an.tur.setCurrentIndex(an.tur.findData("sogutucu_sicaklik"))
    an.bas.setValue(555.0)
    an.son.setValue(600.0)
    an.spec_ayarla(spec, None)          # sekmeye yeniden giris
    kontrol("yeniden giris: parametre ve aralik korundu",
            an.tur.currentData() == "sogutucu_sicaklik" and an.bas.value() == 555.0
            and an.son.value() == 600.0, "-> %s %g" % (an.tur.currentData(), an.bas.value()))

    # yaricap varsayilan araligi komsu bolgeleri asmaz
    an.gelismis.ac(True)
    an.tur.setCurrentIndex(an.tur.findData("cubuk_yaricap"))
    # findData demet (tuple) verisini eslestiremez: dongu ile secilir
    an.hedef.setCurrentIndex([an.hedef.itemData(i) for i in range(an.hedef.count())]
                             .index(("yakit_cubugu", 0)))
    an._hedef_secildi()
    b = spec["cubuklar"][0]["bolgeler"]
    kontrol("yaricap araligi ic ice bolgelerle cakismiyor (%g-%g, sonraki r=%g)"
            % (an.bas.value(), an.son.value(), b[1]["r"]),
            0 < an.bas.value() < b[0]["r"] < an.son.value() < b[1]["r"])

    # gecersiz (bayat) secim: uyari verilir, SORU sorulmaz, isci baslamaz
    an.tur.setCurrentIndex(an.tur.findData("bor_ppm"))
    an.hedef.addItem("uo2", "uo2")
    an.hedef.setCurrentIndex(an.hedef.count() - 1)
    cagri = {"soru": 0, "uyari": 0}
    eski_q, eski_w = QtWidgets.QMessageBox.question, QtWidgets.QMessageBox.warning

    def soru(*a, **k):
        cagri["soru"] += 1
        return QtWidgets.QMessageBox.Yes

    def uyari(*a, **k):
        cagri["uyari"] += 1
        return QtWidgets.QMessageBox.Ok
    QtWidgets.QMessageBox.question = soru
    QtWidgets.QMessageBox.warning = uyari
    try:
        an._basla()
    finally:
        QtWidgets.QMessageBox.question, QtWidgets.QMessageBox.warning = eski_q, eski_w
    kontrol("gecersiz hedef (UO2'ye bor): 'yine de devam' sorusu YOK", cagri["soru"] == 0)
    kontrol("gecersiz hedef: uyari verildi, analiz baslamadi",
            cagri["uyari"] == 1 and an._isci is None, "-> %r" % cagri)
    kontrol("uyaridan sonra liste yenilendi (uo2 gitti)", an.hedef.findData("uo2") < 0)
    uyg  # noqa: B018


# ============================================================================
# 5. Analiz: proje kusagi
# ============================================================================

def test_analiz_kusak():
    """Proje degistikten sonra biten tarama yeni projeye nokta/katsayi yazmaz."""
    print("\n[H6] ANALIZ: proje degistikten sonra biten tarama yeni projeye yazilmiyor")
    uyg = _qt()
    if uyg is None:
        return
    from cekirdek import tarama
    from arayuz.sekme_analiz import AnalizSekmesi
    eski = tarama.calistir

    def sahte(spec, tur, hedef, degerler, kok, geri_cagir=None, is_parcacigi=None,
              dur_bayragi=None):
        sonuclar = []
        for i, d in enumerate(degerler[:2]):
            time.sleep(0.3)
            s = {"deger": d, "keff": 1.10 - 1e-5 * d, "sapma": 0.0005, "dizin": kok}
            sonuclar.append(s)
            if geri_cagir:
                geri_cagir(i, 2, s)
        return sonuclar, []
    tarama.calistir = sahte
    gecici = tempfile.mkdtemp(prefix="analiz_kusak_")
    try:
        proje = os.path.join(gecici, "proje.json")
        an = AnalizSekmesi()
        an.kapi_ayarla(lambda: (True, "hazır"))
        spec = _spec("pwr_pinhucre")
        an.spec_ayarla(spec, proje)
        an.tur.setCurrentIndex(an.tur.findData("yakit_sicaklik"))
        an._basla()
        kontrol("(on kosul) tarama basladi", an._isci is not None)
        kontrol("isci modelin KOPYASIYLA calisiyor", an._isci.spec is not spec
                and an._isci.spec == spec)
        _bekle(lambda: an._isci is None)
        kontrol("ayni projede: 2 nokta ve Doppler katsayisi gosterildi",
                an.tablo.rowCount() == 2 and "Doppler" in an.sonuc_kutusu.text(),
                "-> %d" % an.tablo.rowCount())
        kontrol("sonuc_var() True", getattr(an, "sonuc_var", lambda: False)())

        an2 = AnalizSekmesi()
        an2.kapi_ayarla(lambda: (True, "hazır"))
        an2.spec_ayarla(copy.deepcopy(spec), proje)
        an2.tur.setCurrentIndex(an2.tur.findData("yakit_sicaklik"))
        an2._basla()
        an2.sifirla()
        an2.spec_ayarla(_spec("godiva_kriter"), proje)
        _bekle(lambda: an2._isci is None)
        kontrol("proje degistikten sonra biten tarama: tablo bos",
                an2.tablo.rowCount() == 0, "-> %d" % an2.tablo.rowCount())
        kontrol("proje degistikten sonra: sonuc listesi bos, katsayi yok",
                an2._sonuclar == [] and "katsay" not in an2.sonuc_kutusu.text().lower(),
                "-> %r" % an2.sonuc_kutusu.text()[:60])
        kontrol("sonuc_var() False", hasattr(an2, "sonuc_var") and not an2.sonuc_var())
        kontrol("isci bitince yeni analiz baslatilabilir", an2.d_basla.isEnabled())
    finally:
        tarama.calistir = eski
        shutil.rmtree(gecici, ignore_errors=True)
    uyg  # noqa: B018


# ============================================================================
# 6. Tukenme: gorunum
# ============================================================================

def test_tukenme_gorunum():
    print("\n[H7] TUKENME: kapaliyken yalniz anahtar; Gelismis; cubuk cubuk yanma kosulu")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtWidgets
    from arayuz.sekme_tukenme import TukenmeSekmesi, yakit_ornek_sayisi
    t = TukenmeSekmesi()
    kontrol("alt sekme (QTabWidget) ve bolucu yok",
            t.findChildren(QtWidgets.QTabWidget) == []
            and t.findChildren(QtWidgets.QSplitter) == [])
    s = _spec("pwr_tukenme")
    s["tukenme"]["malzemeleri_ayir"] = True        # gizli alanin degeri korunmali
    t.spec_yukle(s)
    t.bekle()
    kontrol("acik: ayarlar ve kosu cubugu gorunur",
            _gorunur(t.ayar_kutusu, t) and _gorunur(t.kosu_kutusu, t))
    kontrol("zincir, entegrator, cubuk cubuk yanma 'Gelismis' icinde; izlenen DISINDA",
            all(t.gelismis.isAncestorOf(w) for w in (t.zincir, t.entegrator, t.ayir))
            and not t.gelismis.isAncestorOf(t.izlenen))
    kontrol("guc, adimlar Gelismis DISINDA",
            not t.gelismis.isAncestorOf(t.guc) and not t.gelismis.isAncestorOf(t.adimlar))
    kontrol("pin hucre (tek ornek): cubuk cubuk yanma gizli",
            not t.gelismis_form.isRowVisible(t.ayir))
    t.guc.setValue(39.0)
    kontrol("gizli 'cubuk cubuk yanma' degeri spec'te korundu",
            s["tukenme"]["malzemeleri_ayir"] is True)
    t.var.setChecked(False)
    kontrol("kapali: ayarlar ve kosu cubugu gizli",
            not _gorunur(t.ayar_kutusu, t) and not _gorunur(t.kosu_kutusu, t))
    kontrol("kapali: acma anahtari ve kisa aciklama gorunur",
            _gorunur(t.var, t) and _gorunur(t.aciklama, t))
    kontrol("kapali: baslat devre disi", not t.d_baslat.isEnabled())

    for ad, beklenen in (("pwr_tukenme", 1), ("godiva_kriter", 1), ("pwr_17x17", 264)):
        n = yakit_ornek_sayisi(_spec(ad))
        kontrol("%s: yakit ornek sayisi %d" % (ad, beklenen), n == beklenen, "-> %d" % n)
    n = yakit_ornek_sayisi(_spec("mtr_plaka"))
    kontrol("mtr_plaka: plaka sayisi kadar ornek (>1)", n > 1, "-> %d" % n)
    t2 = TukenmeSekmesi()
    s2 = _spec("pwr_17x17")
    s2["tukenme"] = dict(s["tukenme"], var=True)
    t2.spec_yukle(s2)
    t2.bekle()
    kontrol("17x17 (264 ornek): cubuk cubuk yanma sunuluyor",
            t2.gelismis_form.isRowVisible(t2.ayir))

    t3 = TukenmeSekmesi()
    s3 = _spec("zirh_kure")
    s3.setdefault("tukenme", {})["var"] = True
    t3.spec_yukle(s3)
    kontrol("uygun olmayan model (sabit kaynak): yalnizca nedeni soyleyen bos durum",
            _gorunur(t3.bos, t3) and not _gorunur(t3.icerik, t3)
            and "özdeğer" in t3.bos.metin.text(), "-> %r" % t3.bos.metin.text())
    kontrol("uygun olmayan model: baslat devre disi", not t3.d_baslat.isEnabled())
    kontrol("uygun olmayan model: spec'teki tukenme.var silinmedi", s3["tukenme"]["var"])
    uyg  # noqa: B018


# ============================================================================
# 7. Tukenme: proje kusagi (onceki-sonuc okumasi ve sahte kosu)
# ============================================================================

def test_tukenme_kusak(gecici=None):
    print("\n[H8] TUKENME: proje degistikten sonra biten okuma/kosu yeni projeye yazilmiyor")
    uyg = _qt()
    if uyg is None:
        return
    from cekirdek import tukenme as _tk
    from arayuz import sekme_tukenme as st
    from arayuz.sekme_tukenme import TukenmeSekmesi

    # --- a) onceki-sonuc okumasi eski kusaktan gelir ---
    onceki = {"h5": "/yok/depletion_results.h5", "tarih": time.time(), "durum": "guncel",
              "farklar": [], "sonuc": copy.deepcopy(SAHTE_TUKENME)}
    t = TukenmeSekmesi()
    t.spec_yukle(_spec("pwr_tukenme"))
    t.bekle()
    t._okuma_kusagi = getattr(t, "_kusak", 0)
    t.sifirla()
    t._onceki_geldi(("/yok/depletion_results.h5", 1.0), onceki)
    kontrol("proje degistikten sonra gelen onceki-sonuc atildi", t.tablo.rowCount() == 0,
            "-> %d satir" % t.tablo.rowCount())
    t._okuma_kusagi = getattr(t, "_kusak", 0)
    t._onceki_geldi(("/yok/depletion_results.h5", 1.0), onceki)
    kontrol("(kontrol) ayni kusakta gelen onceki-sonuc gosterildi",
            t.tablo.rowCount() == 2)

    # --- b) sahte tukenme alt sureci ---
    gecici = tempfile.mkdtemp(prefix="tukenme_kusak_")
    eski_sys, eski_oku = st.sys, _tk.sonuc_oku
    try:
        betik = _betik(gecici, "sahte_python",
                       'while [ "$1" != "--dizin" ] && [ $# -gt 0 ]; do shift; done\n'
                       'echo " Combined k-effective = 1.3 +/- 0.001"\n'
                       'sleep 0.8\n: > "$2/depletion_results.h5"\nexit 0\n')
        st.sys = types.SimpleNamespace(executable=betik)
        _tk.sonuc_oku = lambda h5, spec, izlenen=None: copy.deepcopy(SAHTE_TUKENME)
        proje_a = os.path.join(gecici, "a", "proje.json")
        proje_b = os.path.join(gecici, "b", "proje.json")
        os.makedirs(os.path.dirname(proje_a)); os.makedirs(os.path.dirname(proje_b))

        k = TukenmeSekmesi()
        k.kapi_ayarla(lambda: (True, "hazır"))
        k.proje_ayarla(proje_a)
        k.spec_yukle(_spec("pwr_tukenme"))
        k.bekle()
        k.baslat()
        kontrol("(on kosul) sahte tukenme basladi", k._surec is not None)
        _bekle(lambda: k._surec is None)
        kontrol("(kontrol) ayni projede biten tukenme gosterildi", k.tablo.rowCount() == 2,
                "-> %d" % k.tablo.rowCount())

        y = TukenmeSekmesi()
        y.kapi_ayarla(lambda: (True, "hazır"))
        y.proje_ayarla(proje_a)
        y.spec_yukle(_spec("pwr_tukenme"))
        y.bekle()
        y.baslat()
        y.sifirla()                                     # ana pencere: _proje_degisti
        y.proje_ayarla(proje_b)
        s_b = _spec("pwr_17x17")
        s_b["tukenme"] = dict(_spec("pwr_tukenme")["tukenme"])
        y.spec_yukle(s_b)
        kontrol("eski kosu surerken 'onceki projenin' uyarisi",
                "Önceki projenin" in y.kapi_etiket.text(), "-> %r" % y.kapi_etiket.text())
        _bekle(lambda: y._surec is None)
        y.bekle()
        kontrol("proje degistikten sonra biten tukenme: tablo bos", y.tablo.rowCount() == 0,
                "-> %d" % y.tablo.rowCount())
        kontrol("yeni projenin logu eski kosunun satirini icermiyor",
                "Combined" not in y.log.toPlainText())
        kontrol("sonuc_var() False", hasattr(y, "sonuc_var") and not y.sonuc_var())
        kontrol("kosu bitince baslat yeniden etkin", y.d_baslat.isEnabled())
    finally:
        st.sys, _tk.sonuc_oku = eski_sys, eski_oku
        shutil.rmtree(gecici, ignore_errors=True)
    uyg  # noqa: B018


# ============================================================================
# 8. sonuc_degisti / sonuc_var
# ============================================================================

def test_sonuc_api():
    print("\n[H9] SONUC API: sonuc_degisti ve sonuc_var (uc sekme)")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz.sekme_analiz import AnalizSekmesi
    from arayuz.sekme_calistir import CalistirSekmesi
    from arayuz.sekme_tukenme import TukenmeSekmesi

    c = CalistirSekmesi()
    c.spec_ayarla(_spec("pwr_17x17"), None)
    yay = []
    c.sonuc_degisti.connect(lambda: yay.append(c.sonuc_var()))
    kontrol("Calistir: baslangicta sonuc yok", not c.sonuc_var())
    c._sonuc_goster(copy.deepcopy(SAHTE_K), "/yok/sp.h5")
    kontrol("Calistir: sonuc gelince sonuc_var True ve yayildi", yay == [True],
            "-> %r" % yay)
    kontrol("Calistir: _son_basarili (eski ad) ayni", c._son_basarili is True)
    c.sifirla()
    kontrol("Calistir: sifirla -> False ve yayildi", yay == [True, False], "-> %r" % yay)

    an = AnalizSekmesi()
    an.spec_ayarla(_spec("pwr_17x17"), None)
    yay = []
    an.sonuc_degisti.connect(lambda: yay.append(an.sonuc_var()))
    an._analiz_turu, an._analiz_modu = "yakit_sicaklik", "tarama"
    an._tarama_bitti([{"deger": 600.0, "keff": 1.2, "sapma": 0.001},
                      {"deger": 900.0, "keff": 1.19, "sapma": 0.001}], [])
    kontrol("Analiz: tarama bitince sonuc_var True ve yayildi", yay == [True], "-> %r" % yay)
    kontrol("Analiz: basarisiz noktalar sonuc sayilmaz",
            not AnalizSekmesi.sonuc_var(types.SimpleNamespace(
                _sonuclar=[{"deger": 1.0, "keff": None}])))
    an.sifirla()
    kontrol("Analiz: sifirla -> False ve yayildi", yay == [True, False], "-> %r" % yay)

    t = TukenmeSekmesi()
    t.spec_yukle(_spec("pwr_tukenme"))
    t.bekle()
    yay = []
    t.sonuc_degisti.connect(lambda: yay.append(t.sonuc_var()))
    t._sonuc_goster(copy.deepcopy(SAHTE_TUKENME))
    kontrol("Tukenme: sonuc gelince True ve yayildi", yay == [True], "-> %r" % yay)
    kontrol("Tukenme: tablo (eski erisim yolu) dolu", t.tablo.rowCount() == 2)
    t.sifirla()
    kontrol("Tukenme: sifirla -> False ve yayildi", yay[-1] is False and not t.sonuc_var(),
            "-> %r" % yay)
    uyg  # noqa: B018


# ============================================================================
# 9. metin: numarali sekme atifi ve uygulama notu yok
# ============================================================================

def test_metinler():
    print("\n[H10] METIN: numarali sekme atifi yok, 'yine de devam' yok")
    dosyalar = ("arayuz/sekme_calistir.py", "arayuz/sekme_analiz.py",
                "arayuz/sekme_tukenme.py", "arayuz/guc_harita.py")
    desen = re.compile(r"[\"'][^\"'\n]*\b[1-8]\.\s*(?:[A-ZÇĞİÖŞÜ][\wçğıöşü]*\s+)?sekme",
                       re.IGNORECASE)
    bulunan = []
    for d in dosyalar:
        with open(os.path.join(KOK, d), encoding="utf-8") as f:
            for i, satir in enumerate(f, 1):
                if desen.search(satir):
                    bulunan.append("%s:%d" % (d, i))
    kontrol("gorunen metinlerde '5. sekme' gibi numarali atif yok", not bulunan,
            "-> %r" % bulunan)
    with open(os.path.join(KOK, "arayuz/sekme_analiz.py"), encoding="utf-8") as f:
        metin = f.read()
    kontrol("Analiz'de 'Yine de devam' secenegi yok", "Yine de devam" not in metin)


HIZLI = [test_calistir_sayfa_yapisi, test_calistir_calistirma_alanlari, test_analiz_listeler, test_analiz_secim_ve_red, test_analiz_kusak,
         test_tukenme_gorunum, test_sonuc_api, test_metinler]
YAVAS = [test_calistir_kusak, test_tukenme_kusak]


if __name__ == "__main__":
    from testler import ortak_test
    for fn in HIZLI:
        fn()
    print("\n%d gecti, %d kaldi" % (len(ortak_test._gecti), len(ortak_test._kaldi)))
    for k in ortak_test._kaldi:
        print("  KALDI:", k)
    sys.exit(1 if ortak_test._kaldi else 0)
