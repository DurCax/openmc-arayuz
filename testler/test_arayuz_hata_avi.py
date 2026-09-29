# -*- coding: utf-8 -*-
"""
 test_arayuz_hata_avi.py  --  18a-. ARAYUZ HATA AVI (sekme alanlari): veriyi sessizce degistiren/kaybeden hatalar

 testler/test_regresyon.py'den tasindi (Dalga 0; test metinleri aynen).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri, kendiliginden bulunur).
"""

import copy
import importlib.util
import os
import shutil
import tempfile

from cekirdek import sema, kurucu, dogrula, kod_uret
from testler.ortak_test import kontrol
from testler.regresyon_ortak import (
    ORNEK, _ana_pencere, _kor_turu, _ornek_adlari, _pencere_kapat, _qt, _tally_mesh)


# ============================================================================
# 18. ARAYUZ HATA AVI -- veriyi SESSIZCE degistiren / kaybeden / yanlis
#     sonuc gosteren hatalar (kullanilabilirlik denetimi, dalga 1)
#
#   Her test once DUZELTMEDEN ONCEKI kodda calistirilip KALDIGI gorulmustur;
#   duzeltmeden once gecen bir test hicbir sey kanitlamaz.
# ============================================================================

def test_arayuz_tekerlek(gecici=None):
    """
    [1] Fare tekerlegi ODAKSIZ secim/sayi kutularini degistirmemeli.

    Her sekme bir QScrollArea icinde. Sayfayi tekerlekle kaydiran kullanici
    imlecin altindan gecen kutunun degerini SESSIZCE degistiriyordu
    (denetimde olculdu: kor turu tek_cubuk -> tek_plaka, yan sinir
    reflective -> vacuum, hucre adimi 1.26 -> 1.25).
    """
    print("\n[18a] ARAYUZ: fare tekerlegi odaksiz kutulari degistirmiyor")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtCore, QtGui, QtWidgets
    p = _ana_pencere(os.path.join(ORNEK, "pwr_pinhucre.json"))
    try:
        def tekerlek(w, delta=-120):
            olay = QtGui.QWheelEvent(QtCore.QPointF(4, 4), QtCore.QPointF(4, 4),
                                     QtCore.QPoint(0, 0), QtCore.QPoint(0, delta),
                                     QtCore.Qt.NoButton, QtCore.Qt.NoModifier,
                                     QtCore.Qt.NoScrollPhase, False)
            QtWidgets.QApplication.sendEvent(w, olay)

        k, a = p.s_kor, p.s_ayar
        for ad, w, oku in (
                ("yukseklik secimi (QComboBox)", k.yukseklik_modu, lambda w: w.currentIndex()),
                ("yan sinir (QComboBox)", k.bc_yan, lambda w: w.currentIndex()),
                ("hucre adimi (ortak.sayi)", k.adim, lambda w: w.value()),
                ("kosu modu (ayarlar)", a.mod, lambda w: w.currentIndex()),
                ("parcacik (ortak.tamsayi)", a.parcacik, lambda w: w.value())):
            # Her olaydan SONRA okunur: asagi+yukari ciftinde secim kutusu
            # geri doner ve hata gizlenirdi.
            once = oku(w)
            degerler = []
            for delta in (-120, -120, +120):
                tekerlek(w, delta)
                degerler.append(oku(w))
            kontrol("odaksiz %s tekerlekle degismedi" % ad,
                    all(x == once for x in degerler), "-> %r -> %r" % (once, degerler))
        kor = p.spec["kor"]
        kontrol("spec degismedi (tur/sinir/adim)",
                kor["tur"] == "tek_cubuk" and kor["sinir"]["yan"] == "reflective"
                and abs(kor["adim"] - 1.26) < 1e-12,
                "-> %s %s %s" % (kor["tur"], kor["sinir"]["yan"], kor["adim"]))
        p.ensurePolished()
        kontrol("kutularin odak politikasi StrongFocus (tekerlek odak VERMEZ)",
                k.yukseklik_modu.focusPolicy() == QtCore.Qt.StrongFocus
                and k.adim.focusPolicy() == QtCore.Qt.StrongFocus,
                "-> %s" % k.yukseklik_modu.focusPolicy())

        # Odakli kutu tekerlekle CALISMAYA devam etmeli (yalnizca offscreen'de
        # pencere gosterilir -- gercek ekranda pencere acilmaz).
        if QtGui.QGuiApplication.platformName() == "offscreen":
            p.show()
            p.sekmeye_git("kor")
            p.activateWindow()
            k.adim.setFocus()
            uyg.processEvents()
            if k.adim.hasFocus():
                once = k.adim.value()
                tekerlek(k.adim)
                kontrol("ODAKLI sayi kutusu tekerlekle degisiyor", k.adim.value() != once,
                        "-> %g -> %g" % (once, k.adim.value()))
            else:
                kontrol("odakli kutu denemesi atlandi (odak verilemedi)", True)
    finally:
        _pencere_kapat(p)


def test_arayuz_tambur_yansitici():
    """
    [2] 'tamburlu' secmek 'Yansitici kusak ekle'yi zorla isaretliyordu; geri
    donunce isaret kaliyordu: pwr_17x17 -> tamburlu -> tek_demet, 21.42 cm'lik
    demet SESSIZCE 20 cm su ile 61.42 cm oluyordu.
    """
    print("\n[18b] ARAYUZ: tamburlu gidis-donus yansiticiyi degistirmiyor")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz.sekme_kor import KorSekmesi
    spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    olcu0 = kurucu.kur(spec)[1]["sinir_kutu"]
    var0 = spec["kor"]["yansitici"]["var"]
    k = KorSekmesi()
    k.spec_yukle(spec)
    hafiza = {}
    _kor_turu(k, spec, "tamburlu", hafiza)
    kontrol("tamburlu'da 'Yansitici kusak ekle' kutusu gizli (zorunlu)",
            not k.yans_var.isVisibleTo(k))
    kontrol("tamburlu'da kalinlik/malzeme duzenlenebilir",
            k.yans_kal.isEnabled() and k.yans_mal.isEnabled())
    k._kaydet()                   # sekmenin kaydi da 'var'i zorlamamali
    _kor_turu(k, spec, "tek_demet", hafiza)
    k._kaydet()
    kontrol("gidis-donus: yansitici.var degismedi (%s)" % var0,
            spec["kor"]["yansitici"]["var"] == var0,
            "-> %s" % spec["kor"]["yansitici"]["var"])
    olcu1 = kurucu.kur(spec)[1]["sinir_kutu"]
    kontrol("gidis-donus: model olcusu degismedi (%.2f cm)" % olcu0[0],
            abs(olcu1[0] - olcu0[0]) < 1e-9 and abs(olcu1[1] - olcu0[1]) < 1e-9,
            "-> %.2f x %.2f" % olcu1)
    # tamburlu ornegi: yansitici hala kuruluyor (var alanindan bagimsiz, zorunlu)
    t = sema.yukle(os.path.join(ORNEK, "tamburlu_kor.json"))
    t["kor"]["yansitici"]["var"] = False
    olcu_t = kurucu.kur(t)[1]["sinir_kutu"]
    kontrol("tamburlu korda yansitici 'var' alanindan bagimsiz kuruluyor",
            abs(olcu_t[0] - 2 * (16.0 + 12.0)) < 1e-9, "-> %.2f" % olcu_t[0])
    b = [x for x in dogrula.tum_kontroller(t, veri_kontrolu=False)
         if "kullanılmayan malzeme: berilyum" in x.mesaj]
    kontrol("tamburlu yansitici malzemesi 'kullaniliyor' sayiliyor", not b)
    uyg  # noqa: B018


def test_arayuz_kor_tur_alanlari():
    """
    [3] KorSekmesi._kaydet() tur ne olursa olsun HER alani yaziyordu:
    pwr_3b (tek_demet) tek bir sinir degisikliginden sonra cubuk='yakit_cubugu',
    dolgu='bosluk' ve tam bir tambur blogu kazaniyordu. dogrula/kurucu "ana
    dolgu"yu cubuk-or-demet-or-... zinciriyle okudugu icin bu kalinti degerler
    aktif araligi ve dogrulamayi degistirir.
    """
    print("\n[18c] ARAYUZ: kor sekmesi yalnizca secili turun alanlarini yaziyor")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz.sekme_kor import KorSekmesi
    spec = sema.yukle(os.path.join(ORNEK, "pwr_3b.json"))
    k = KorSekmesi()
    k.spec_yukle(spec)
    k.bc_yan.setCurrentIndex(k.bc_yan.findData("vacuum"))
    kor = spec["kor"]
    kontrol("sinir degisikligi yazildi", kor["sinir"]["yan"] == "vacuum")
    kontrol("tek_demet: 'cubuk' kalintisi yok", kor.get("cubuk") is None,
            "-> %r" % kor.get("cubuk"))
    kontrol("tek_demet: 'dolgu' kalintisi yok", kor.get("dolgu") is None,
            "-> %r" % kor.get("dolgu"))
    kontrol("tek_demet: 'plaka' kalintisi yok", kor.get("plaka") is None)
    kontrol("tek_demet: tambur blogu varsayilan",
            kor.get("tambur") == sema.VARSAYILAN_KOR["tambur"], "-> %r" % kor.get("tambur"))
    kontrol("tek_demet: demet korundu", kor.get("demet") == "demet_17x17")
    kontrol("tur -> alan tablosu sema'da TEK yerde (KOR_TUR_ALANLARI)",
            hasattr(sema, "KOR_TUR_ALANLARI"))
    # tek_cubuk'a gecip donmek demeti geri getirir (tur hafizasi tutuyor)
    hafiza = {}
    _kor_turu(k, spec, "tek_cubuk", hafiza)
    k._kaydet()
    kontrol("tek_cubuk: cubuk yazildi, demet temizlendi",
            kor.get("cubuk") == "yakit_cubugu" and kor.get("demet") is None,
            "-> cubuk=%r demet=%r" % (kor.get("cubuk"), kor.get("demet")))
    _kor_turu(k, spec, "tek_demet", hafiza)
    k._kaydet()
    kontrol("tek_demet'e donus: demet geri geldi, cubuk temizlendi",
            kor.get("demet") == "demet_17x17" and kor.get("cubuk") is None)
    # JSON'dan baska yolla duzenlenemeyen kuresel kabuklar tur degisince SILINMEMELI
    g = sema.yukle(os.path.join(ORNEK, "godiva_kriter.json"))
    kabuk0 = copy.deepcopy(g["kor"]["kabuklar"])
    k2 = KorSekmesi()
    k2.spec_yukle(g)
    h2 = {}
    _kor_turu(k2, g, "tek_cubuk", h2)
    k2._kaydet()
    _kor_turu(k2, g, "kuresel", h2)
    k2._kaydet()
    kontrol("kuresel kabuklar gidis-donuste korundu", g["kor"]["kabuklar"] == kabuk0)

    # Butun ornekler: arayuzden bir kez kaydetmek (degisiklik yok) modeli ve
    # dogrulamayi DEGISTIRMEMELI -- ayiklama gerekli bir alani silmesin.
    for ad in _ornek_adlari():
        s = sema.yukle(os.path.join(ORNEK, ad + ".json"))
        olcu0 = kurucu.kur(s)[1]["sinir_kutu"]
        bul0 = sorted((b.seviye, b.mesaj) for b in dogrula.tum_kontroller(s, veri_kontrolu=False))
        kk = KorSekmesi()
        kk.spec_yukle(s)
        kk._kaydet()
        olcu1 = kurucu.kur(s)[1]["sinir_kutu"]
        bul1 = sorted((b.seviye, b.mesaj) for b in dogrula.tum_kontroller(s, veri_kontrolu=False))
        kontrol("%s: arayuz kaydi olcuyu ve dogrulamayi degistirmiyor" % ad,
                olcu0 == olcu1 and bul0 == bul1,
                "" if bul0 == bul1 else "-> %s" % sorted(set(bul1) ^ set(bul0)))
    uyg  # noqa: B018


def test_arayuz_kuresel_yukseklik():
    """
    [4] Kuresel duzenekte yukseklik kutusu gorunur/etkindi; isaretlenince alt/ust
    sinirlar da aciliyordu -- Godiva "17.48 x 17.48 x 366 cm" oluyor ve bu
    yukseklik entropi mesh'ine, kaynak kutusuna, tally'lere giriyordu.
    """
    print("\n[18d] ARAYUZ: kuresel duzenekte yukseklik yok")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz.sekme_kor import KorSekmesi
    g = sema.yukle(os.path.join(ORNEK, "godiva_kriter.json"))
    k = KorSekmesi()
    k.spec_yukle(g)
    kontrol("kuresel: yukseklik kutusu gizli", not k.yukseklik_modu.isVisibleTo(k))
    kontrol("kuresel: yukseklik alani gizli", not k.yukseklik.isVisibleTo(k))
    kontrol("kuresel: alt/ust sinir gizli",
            not k.bc_alt.isVisibleTo(k) and not k.bc_ust.isVisibleTo(k))
    _kor_turu(k, g, "tek_cubuk", {})
    kontrol("tek_cubuk: yukseklik kutusu yeniden gorunur", k.yukseklik_modu.isVisibleTo(k))

    s = sema.yukle(os.path.join(ORNEK, "pwr_3b.json"))
    k2 = KorSekmesi()
    k2.spec_yukle(s)
    _kor_turu(k2, s, "kuresel", {})
    k2._kaydet()
    kontrol("kuresel'e geciste yukseklik temizlendi", s["kor"].get("yukseklik") is None,
            "-> %r" % s["kor"].get("yukseklik"))
    kontrol("kuresel'de eksenel yukseklik yok (kor_yuksekligi None)",
            sema.kor_yuksekligi(s["kor"]) is None)

    g2 = sema.yukle(os.path.join(ORNEK, "godiva_kriter.json"))   # g arayuzde degisti
    g2["kor"]["yukseklik"] = 366.0
    b = [x for x in dogrula.tum_kontroller(g2, veri_kontrolu=False)
         if x.seviye == "hata" and "kseklik" in x.mesaj]
    kontrol("dogrulama: kuresel + yukseklik -> HATA", bool(b),
            "-> %s" % (b[0].mesaj if b else "yok"))
    uyg  # noqa: B018


def test_arayuz_tambur_kaydirici():
    """[5] Tambur donme kaydiricisi '% 3601' kullaniyordu: -90 derece 270.1 gorunuyordu."""
    print("\n[18e] ARAYUZ: tambur donme kaydiricisi")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz.sekme_kor import KorSekmesi
    t = sema.yukle(os.path.join(ORNEK, "tamburlu_kor.json"))
    k = KorSekmesi()
    k.spec_yukle(t)
    k.tb_donme.setValue(-90.0)
    kontrol("donme -90 -> kaydirici 270.0 derece", k.tb_donme_kaydirici.value() == 2700,
            "-> %.1f" % (k.tb_donme_kaydirici.value() / 10.0))
    t2 = copy.deepcopy(t)
    t2["kor"]["tambur"]["donme"] = -90.0
    k2 = KorSekmesi()
    k2.spec_yukle(t2)
    kontrol("dosyadan -90 -> kaydirici 270.0 derece", k2.tb_donme_kaydirici.value() == 2700,
            "-> %.1f" % (k2.tb_donme_kaydirici.value() / 10.0))
    kontrol("donme degeri korundu (-90)", abs(t2["kor"]["tambur"]["donme"] + 90.0) < 1e-12)
    uyg  # noqa: B018


def test_arayuz_tally_filtre_korunur():
    """
    [6] Tally editoru filtre listesini yalnizca KENDI kutularindan (enerji, mesh)
    yeniden kuruyordu: zirh_kure'de ad alaninda Enter'a basmak 'akı_gruplu'
    tally'sinin [malzeme, enerji] filtrelerini [enerji]'ye indiriyordu.
    """
    print("\n[18f] ARAYUZ: tally editoru yonetmedigi filtreleri silmiyor")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz.sekme_ayar import AyarSekmesi
    spec = sema.yukle(os.path.join(ORNEK, "zirh_kure.json"))
    a = AyarSekmesi()
    a.spec_yukle(spec)
    a.tally_liste.setCurrentRow(0)
    t = spec["tallyler"][0]
    once = copy.deepcopy(t["filtreler"])
    a.t_ad.editingFinished.emit()
    kontrol("Enter sonrasi filtre turleri [malzeme, enerji]",
            [f["tur"] for f in t["filtreler"]] == ["malzeme", "enerji"],
            "-> %s" % [f["tur"] for f in t["filtreler"]])
    kontrol("filtreler birebir ayni", t["filtreler"] == once)
    a.t_enerji_var.setChecked(False)
    kontrol("enerji kapatilinca malzeme filtresi kaliyor",
            [f["tur"] for f in t["filtreler"]] == ["malzeme"],
            "-> %s" % [f["tur"] for f in t["filtreler"]])
    a.t_enerji_var.setChecked(True)
    kontrol("enerji geri acilinca [malzeme, enerji]",
            [f["tur"] for f in t["filtreler"]] == ["malzeme", "enerji"])
    uyg  # noqa: B018


def test_tally_mesh_otomatik():
    """
    [7] Tally mesh sinirlari olusturma aninda donduruluyordu: yansitici
    eklendikten sonra model 61.42 cm ama mesh +/-10.71 cm'de kaliyordu.
    Artik mesh "otomatik" isaretlenir ve sinirlar model KURULURKEN turetilir --
    kurucu ve uretilen betik AYNI mesh'i kurmali.
    """
    print("\n[18g] TALLY MESH: sinirlar modelle birlikte buyuyor (+ betik esdegerligi)")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz.sekme_ayar import AyarSekmesi
    spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    a = AyarSekmesi()
    a.spec_yukle(spec)
    a._tally_ekle()
    a.t_mesh_var.setChecked(True)
    t = spec["tallyler"][-1]
    mf = [f for f in t["filtreler"] if f["tur"] == "mesh"]
    kontrol("yeni mesh filtresi 'otomatik'", bool(mf) and mf[0].get("otomatik") is True,
            "-> %r" % (mf[0] if mf else None))

    spec["kor"]["yansitici"].update({"var": True, "kalinlik": 20.0})
    model, bilgi = kurucu.kur(spec)
    gx, gy = bilgi["sinir_kutu"]
    m = _tally_mesh(model.tallies, t["ad"])
    kontrol("mesh sinirlari yansiticili modeli kapsiyor (+/-%.2f cm)" % (gx / 2),
            m is not None and abs(m[1][0] + gx / 2) < 1e-9 and abs(m[2][1] - gy / 2) < 1e-9,
            "-> %s" % (m,))

    gecici = tempfile.mkdtemp(prefix="mesh_betik_")
    try:
        betik = os.path.join(gecici, "model.py")
        with open(betik, "w", encoding="utf-8") as f:
            f.write(kod_uret.uret(spec, "model.py"))
        sm = importlib.util.spec_from_file_location("uretilen_mesh", betik)
        mod = importlib.util.module_from_spec(sm)
        sm.loader.exec_module(mod)
        mb = _tally_mesh(mod.model.tallies, t["ad"])
    except Exception as e:
        mb = "HATA: %s" % e
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    kontrol("uretilen betik AYNI mesh'i kuruyor", mb == m, "-> kurucu %s | betik %s" % (m, mb))

    # Eski dosyalar: acik alt/ust sinirlari AYNEN kullanilir
    eski = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    eski["tallyler"].append(sema.tally("eski_mesh", ["flux"], [
        sema.filtre_mesh([2, 2, 1], [-5.0, -5.0, -1.0], [5.0, 5.0, 1.0])]))
    me = _tally_mesh(kurucu.kur(eski)[0].tallies, "eski_mesh")
    kontrol("eski dosyadaki acik mesh sinirlari korunuyor",
            me == ([2, 2, 1], [-5.0, -5.0, -1.0], [5.0, 5.0, 1.0]), "-> %s" % (me,))
    uyg  # noqa: B018


def test_arayuz_guc_alanlari():
    """[8] doldur() _guc_gorunurluk()'u cagirmiyordu: guc kapaliyken alanlari etkin."""
    print("\n[18h] ARAYUZ: guc dagilimi kapaliyken alanlari devre disi")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz.sekme_ayar import AyarSekmesi
    spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    a = AyarSekmesi()
    a.spec_yukle(spec)
    kontrol("(on kosul) guc dagilimi kapali", not a.guc_var.isChecked())
    kontrol("hedef cubuk devre disi", not a.guc_cubuk.isEnabled())
    kontrol("skor ve toplam guc devre disi",
            not a.guc_skor.isEnabled() and not a.guc_toplam.isEnabled())
    uyg  # noqa: B018


def test_sabit_kaynak_cevrim_satiri():
    """[9a] Sabit kaynak modunda OpenMC ' Simulating batch N' yazar (gercek log satirlari)."""
    print("\n[18i] KOSUCU: sabit kaynak cevrim satiri ayristirma")
    from cekirdek import kosucu
    # ornekler/kosu_zirh/kosu.log satirlari (dosyaya bagimli degil -- kopyalandi)
    ornekler_ = {" Simulating batch 1": 1, " Simulating batch 7": 7,
                 " Simulating batch 50": 50}
    fn = getattr(kosucu, "sabit_kaynak_cevrimi", None)
    kontrol("kosucu.sabit_kaynak_cevrimi var", fn is not None)
    if fn is None:
        return
    for satir, n in ornekler_.items():
        kontrol("'%s' -> %d" % (satir.strip(), n), fn(satir) == n, "-> %r" % fn(satir))
    kontrol("ozdeger cevrim satiri sabit kaynak sayilmiyor",
            fn("  54/1   1.32041   1.36400 +/- 0.00368") is None)
    kontrol("cevrim_satiri 'Simulating batch'i ozdeger sanmiyor",
            kosucu.cevrim_satiri(" Simulating batch 1") is None)
    kontrol("baska satir -> None", fn(" Simulating") is None and fn("") is None)


def test_arayuz_sabit_kaynak_sonuc():
    """
    [9b] Sabit kaynak kosusu sonucu gosterirken cokuyordu:
    "%.5f +/- %.5f" % s["keff"] ve keff=None -> TypeError. k-eff etiketi '-'
    kaliyor, tally'ler hic gosterilmiyor, kosu basarili sayilmiyordu.
    """
    print("\n[18j] ARAYUZ: sabit kaynak sonucu gosteriliyor")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtCore
    from cekirdek import kosucu
    from arayuz.sekme_calistir import CalistirSekmesi
    spec = sema.yukle(os.path.join(ORNEK, "zirh_kure.json"))
    c = CalistirSekmesi()
    c.spec_ayarla(spec, None)

    class _SahteSurec:
        def __init__(self, veri):
            self.veri = veri

        def readAllStandardOutput(self):
            v, self.veri = self.veri, b""
            return QtCore.QByteArray(v)

    c.ilerleme.setRange(0, 50)
    c.ilerleme.setValue(0)
    c._surec = _SahteSurec(b" Simulating batch 1\n Simulating batch 7\n")
    try:
        c._cikti_oku()
    finally:
        c._surec = None
    kontrol("ilerleme cubugu sabit kaynak cevrimini sayiyor (7/50)",
            c.ilerleme.value() == 7, "-> %d" % c.ilerleme.value())

    sahte = {"mod": "fixed source", "keff": None, "cevrim": 50, "pasif": 0,
             "parcacik": 20000, "entropi": [],
             "tallyler": {"akı_gruplu": "TALLY-TABLOSU-akı", "soğurma": "TALLY-TABLOSU-sog"}}
    eski_sp, eski_oku = kosucu.son_statepoint, kosucu.sonuc_oku
    kosucu.son_statepoint = lambda d: "/yok/statepoint.50.h5"
    kosucu.sonuc_oku = lambda sp: sahte
    c._dizin = "/yok"
    hata = None
    try:
        c._bitti(0, None)
    except Exception as e:
        hata = e
    finally:
        kosucu.son_statepoint, kosucu.sonuc_oku = eski_sp, eski_oku
    kontrol("sabit kaynak sonucu COKMEDEN gosterildi", hata is None, "-> %r" % (hata,))
    kontrol("'Sabit kaynak -- k-eff tanimsiz' yaziyor",
            "k-eff tanımsız" in c.durum_etiket.text(), "-> %r" % c.durum_etiket.text())
    kontrol("k-eff etiketi gizli", not c.keff_etiket.isVisibleTo(c))
    kontrol("k-eff/entropi grafigi gizli", not c.tuval.isVisibleTo(c))
    metin = c.sonuc_metin.toPlainText()
    kontrol("tally sonuclari gosteriliyor", "TALLY-TABLOSU-akı" in metin
            and "TALLY-TABLOSU-sog" in metin)
    kontrol("kosu basarili sayildi", c._son_basarili)

    # Ozdeger modu bozulmadi
    sahte_k = {"mod": "eigenvalue", "keff": (1.0, 0.001), "cevrim": 100, "pasif": 20,
               "parcacik": 1000, "entropi": [], "tallyler": {}}
    kosucu.son_statepoint = lambda d: "/yok/statepoint.100.h5"
    kosucu.sonuc_oku = lambda sp: sahte_k
    c.spec_ayarla(sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json")), None)
    try:
        c._bitti(0, None)
        hata = None
    except Exception as e:
        hata = e
    finally:
        kosucu.son_statepoint, kosucu.sonuc_oku = eski_sp, eski_oku
    kontrol("ozdeger sonucu hala gosteriliyor", hata is None
            and c.keff_etiket.text() == "1.00000 ± 0.00100"
            and c.keff_etiket.isVisibleTo(c), "-> %r %r" % (hata, c.keff_etiket.text()))
    uyg  # noqa: B018


def test_arayuz_analiz_hedef():
    """[10] Analiz sekmesine her girildiginde secilen hedef sifirlaniyordu (su -> uo2)."""
    print("\n[18k] ARAYUZ: analiz hedefi sekme degisiminde korunuyor")
    uyg = _qt()
    if uyg is None:
        return
    from arayuz.sekme_analiz import AnalizSekmesi
    spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    an = AnalizSekmesi()
    an.spec_ayarla(spec, None)
    an.tur.setCurrentIndex(an.tur.findData("bor_ppm"))
    an.hedef.setCurrentIndex(an.hedef.findData("su"))
    kontrol("(on kosul) hedef su", an.hedef.currentData() == "su")
    an.spec_ayarla(spec, None)           # ana pencere sekmeye her giriste bunu cagirir
    kontrol("sekmeye yeniden giris: hedef hala su", an.hedef.currentData() == "su",
            "-> %r" % an.hedef.currentData())
    uyg  # noqa: B018


HIZLI = [
    test_arayuz_tambur_yansitici, test_arayuz_kor_tur_alanlari,
    test_arayuz_kuresel_yukseklik, test_arayuz_tambur_kaydirici,
    test_arayuz_tally_filtre_korunur, test_tally_mesh_otomatik,
    test_arayuz_guc_alanlari, test_sabit_kaynak_cevrim_satiri,
    test_arayuz_sabit_kaynak_sonuc, test_arayuz_analiz_hedef,
]
YAVAS = [test_arayuz_tekerlek]
