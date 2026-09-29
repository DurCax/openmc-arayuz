# -*- coding: utf-8 -*-
"""
================================================================================
 test_parca_demet.py  --  Parcalar ve Demet sekmeleri (Dalga 3, ajan 5)
================================================================================
 Olculen davranislar:
   [P1] Parcalar: yalnizca modelde anlamli ekleme secenekleri gorunur
        (uygunluk.parca_turleri), malzeme yokken kapali; emici/izleyici/
        plaka listeleri role gore suzulu; yan levha 0 iken malzemesi kapali.
   [P2] Sablonlar malzemeyi ROLUNDEN secer; eksik rol acikca isaretlenir;
        bos modelde ilk cubuk kora atanir ve model kurulur.
   [P3] Bolge tablosu: yaricaplar artan sirada zorunlu, tasima yalnizca
        malzemeyi tasir, dis bolge silinemez/tasinamaz.
   [P4] Ad degisimi: 11 ornekte her cubuk/plaka/demet ARAYUZDEN yeniden
        adlandirilir -> kurulan model XML'i (adlar haric) AYNI, dogrulama
        bulgulari (adlar haric) AYNI, eski ad spec'te kalmaz.
   [P5] Demet paleti: yalnizca uygun parcalar (kendisi, dongu, tip/olcu
        uyumsuz ic demet cikmaz); varsayilan firca en sik parca.
   [P6] Surukleyerek boyama spec'e harf haritasi yazar (harfler korunur,
        bir darbe = bir bildirim); sag tik firca secer; halka/tumunu doldur.
   [P7] Yerlesim: gercek pencerede 17x17 harita kaydirmasiz, hucre >= 28 px.
   [P8] Adim alt siniri, dis dolgu gorunurlugu, demet ekleme mesaji ve
        bos durum; kafes tipi kutusu yok.
   [Y1] (yavas) bos modelde "+ Cubuk > PWR yakit cubugu" ile kurulan pin
        hucre fiziksel olarak makul k-inf verir.
================================================================================
"""

import copy
import glob
import json
import os
import re
import tempfile

from testler.ortak_test import kontrol, KOK, ORNEK, ISLEM_PARCACIGI  # noqa: F401


def _qt():
    try:
        from PySide6 import QtWidgets
    except Exception as e:                         # pragma: no cover
        kontrol("PySide6 yok, arayuz testi atlandi", True, "-> %s" % e)
        return None
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _yukle(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _kutu_verileri(k):
    return [k.itemData(i) for i in range(k.count())]


def _cubuk_sec(w, ad, tur="cubuk"):
    w._sec((tur, ad))
    return w._secili() == (tur, ad)


def _fare(w, tur, nokta, dugme, dugmeler):
    from PySide6 import QtCore, QtGui, QtWidgets
    olay = QtGui.QMouseEvent(tur, QtCore.QPointF(nokta), w.mapToGlobal(QtCore.QPointF(nokta)),
                             dugme, dugmeler, QtCore.Qt.NoModifier)
    QtWidgets.QApplication.sendEvent(w, olay)


# ============================================================================
# [P1] gorunurluk / etkinlik
# ============================================================================

def test_parca_gorunurluk():
    print("\n[P1] PARCALAR: yalnizca anlamli secenekler gorunur")
    if _qt() is None:
        return
    from cekirdek import sema, uygunluk
    from arayuz.sekme_cubuk import CubukSekmesi
    w = CubukSekmesi()
    beklenen = {                     # (+Cubuk, +Plaka, Kontrol sablonu)
        "pwr_pinhucre": (True, False, False),
        "pwr_17x17": (True, False, False),     # 2B: kontrol cubugu yok
        "pwr_kontrol": (True, False, True),    # 3B demet
        "mtr_plaka": (False, True, False),
        "sfr_altigen": (True, False, False),
        "tamburlu_kor": (True, False, True),
        "godiva_kriter": (False, False, False),
    }
    for ad, (c, p, k) in beklenen.items():
        s = _yukle(ad)
        w.spec_yukle(s)
        t = uygunluk.parca_turleri(s)
        durum = (w.d_cubuk.isVisibleTo(w), w.d_plaka.isVisibleTo(w),
                 w.sablon_eylemleri["kontrol"].isVisible())
        kontrol("%s: +Cubuk/+Plaka/Kontrol = %s (uygunluk ile ayni)" % (ad, (c, p, k)),
                durum == (c, p, k) == (t["cubuk"], t["plaka"], t["kontrol_cubugu"]),
                "-> %s" % (durum,))

    # malzeme yokken + dugmeleri kapali, ipucu yol gosteriyor
    bos = sema.yeni_spec("bos")
    w.spec_yukle(bos)
    kontrol("malzeme yok: + Cubuk kapali, ipucu Malzemeler'i gosteriyor",
            not w.d_cubuk.isEnabled()
            and w.d_cubuk.toolTip() == "Önce Malzemeler sekmesinden malzeme ekleyin.",
            "-> %s %r" % (w.d_cubuk.isEnabled(), w.d_cubuk.toolTip()))
    kontrol("malzeme yok: bos durum paneli ve eylemsiz",
            w.yigin.currentWidget() is w.bos and "malzeme" in w.bos.baslik.text()
            and not w.bos.dugme.isVisibleTo(w.bos), "-> %r" % w.bos.baslik.text())
    kontrol("malzeme yok: cubuk_ekle bir sey eklemiyor", w.cubuk_ekle("yakit") is None
            and not bos["cubuklar"])
    kontrol("secim yokken Kopyala/Sil kapali",
            not w.d_kopya.isEnabled() and not w.d_sil.isEnabled())

    # 2B modelde Tur satiri yok (kontrol cubugu secilemez); 3B'de var
    s = _yukle("pwr_17x17")
    w.spec_yukle(s)
    _cubuk_sec(w, "yakit_cubugu")
    kontrol("2B: Tur satiri gizli, kontrol secenegi yok",
            not w.c_tur.isVisibleTo(w) and "kontrol" not in _kutu_verileri(w.c_tur))
    s = _yukle("pwr_kontrol")
    w.spec_yukle(s)
    _cubuk_sec(w, "yakit_cubugu")
    kontrol("3B demet: Tur satiri ve kontrol secenegi var",
            w.c_tur.isVisibleTo(w) and "kontrol" in _kutu_verileri(w.c_tur))

    # emici listesi: dis bolge yok, numaralandirma 1'den
    _cubuk_sec(w, "kontrol_cubugu")
    kc = sema.cubuk_bul(s, "kontrol_cubugu")
    n = len(kc["bolgeler"])
    kontrol("emici listesinde dis bolge yok",
            _kutu_verileri(w.c_emici) == list(range(n - 1)),
            "-> %s" % _kutu_verileri(w.c_emici))
    kontrol("emici bolgeleri 1'den numaralaniyor",
            w.c_emici.itemText(0).startswith("1. bölge"), "-> %r" % w.c_emici.itemText(0))
    iz = _kutu_verileri(w.c_izleyici)
    kontrol("izleyici listesinde yakit (uo2) ve emici (b4c) yok",
            "uo2" not in iz and "b4c" not in iz and "su" in iz and sema.BOSLUK in iz,
            "-> %s" % iz)
    kontrol("izleyici mevcut deger secili", w.c_izleyici.currentData() == "su")
    kontrol("Bos etiketi Turkce", w.c_izleyici.itemText(
        w.c_izleyici.findData(sema.BOSLUK)) == "Boş (madde yok)")

    # plaka: listeler role gore, yan levha 0 iken malzemesi kapali
    s = _yukle("mtr_plaka")
    w.spec_yukle(s)
    _cubuk_sec(w, "mtr_eleman", "plaka")
    kontrol("plaka yakit listesi yalnizca yakit", _kutu_verileri(w.p_et_mal) == ["u3si2_al"],
            "-> %s" % _kutu_verileri(w.p_et_mal))
    kontrol("plaka zarf listesi yalnizca yapisal", _kutu_verileri(w.p_zarf_mal) == ["al6061"],
            "-> %s" % _kutu_verileri(w.p_zarf_mal))
    kontrol("plaka sogutucu listesi yalnizca sogutucu", _kutu_verileri(w.p_sog) == ["su"],
            "-> %s" % _kutu_verileri(w.p_sog))
    kontrol("yan levha > 0: malzemesi acik", w.p_yan_mal.isEnabled())
    w.p_yan.setValue(0.0)
    kontrol("yan levha 0: malzemesi kapali, spec'e 0 yazildi",
            not w.p_yan_mal.isEnabled() and sema.plaka_bul(s, "mtr_eleman")["yan_levha_kalinlik"] == 0)
    w.p_yan.setValue(0.3)
    kontrol("yan levha tekrar > 0: malzemesi acik", w.p_yan_mal.isEnabled())

    # dosyadaki role uymayan deger gizlenmez / degismez
    s = _yukle("mtr_plaka")
    sema.plaka_bul(s, "mtr_eleman")["zarf_malzeme"] = "su"
    w.spec_yukle(s)
    _cubuk_sec(w, "mtr_eleman", "plaka")
    kontrol("role uymayan mevcut deger listede ve secili (veri degismez)",
            w.p_zarf_mal.currentData() == "su"
            and sema.plaka_bul(s, "mtr_eleman")["zarf_malzeme"] == "su")

    # eski numarali sekme atiflari ve ASCII "bosluk (void)" yok
    from PySide6 import QtWidgets
    from arayuz.sekme_demet import DemetSekmesi
    d = DemetSekmesi()
    d.spec_yukle(_yukle("pwr_17x17"))
    metinler = []
    for kok in (w, d):
        for e in kok.findChildren(QtWidgets.QLabel):
            metinler.append(e.text())
        for b in kok.findChildren(QtWidgets.QAbstractButton):
            metinler.append(b.text())
            metinler.append(b.toolTip())
    numarali = [m for m in metinler if re.search(r"\b\d\. ?(Analiz|Kor|Malzeme|Cubuk|Çubuk|"
                                                  r"Kafes|Demet|Hesap|Tükenme|Tukenme)", m)]
    kontrol("numarali sekme atfi yok", not numarali, "-> %s" % numarali[:2])
    kontrol("'bosluk (void)' gibi ham etiket yok",
            not any("bosluk (void)" in m or "(RectLattice)" in m for m in metinler))


# ============================================================================
# [P2] sablonlar
# ============================================================================

def test_sablon_malzemeleri():
    print("\n[P2] PARCALAR: sablonlar malzemeyi rolunden secer")
    if _qt() is None:
        return
    from cekirdek import dogrula, kurucu, sema
    from arayuz.sekme_cubuk import CubukSekmesi, MalzemeKutusu, sablon_eksik_roller
    w = CubukSekmesi()

    def bolge_malz(s, ad):
        return [b["malzeme"] for b in sema.cubuk_bul(s, ad)["bolgeler"]]

    s = _yukle("pwr_17x17")
    w.spec_yukle(s)
    ad = w.cubuk_ekle("yakit")
    kontrol("PWR yakit cubugu: yakit / gaz / zarf / sogutucu",
            bolge_malz(s, ad) == ["uo2", "helyum", "zirkaloy4", "su"], "-> %s" % bolge_malz(s, ad))
    c = sema.cubuk_bul(s, ad)
    kontrol("yakit cubugu yaricaplari artan, zarfli (dis cap 0.95 cm)",
            [b["r"] for b in c["bolgeler"]] == [0.4096, 0.418, 0.475, None])
    kontrol("yeni cubuk secili ve ad benzersiz", w._secili() == ("cubuk", "yakit_cubugu_2")
            and ad == "yakit_cubugu_2")
    ad = w.cubuk_ekle("kilavuz")
    kontrol("kilavuz boru: sogutucu / zarf / sogutucu",
            bolge_malz(s, ad) == ["su", "zirkaloy4", "su"], "-> %s" % bolge_malz(s, ad))
    kontrol("sablonlar dogrulamada hata vermiyor",
            not dogrula.hata_var(dogrula.tum_kontroller(s, veri_kontrolu=False)))

    s = _yukle("pwr_kontrol")
    w.spec_yukle(s)
    ad = w.cubuk_ekle("kontrol")
    c = sema.cubuk_bul(s, ad)
    kontrol("kontrol cubugu: emici / sogutucu / zarf / sogutucu",
            bolge_malz(s, ad) == ["b4c", "su", "zirkaloy4", "su"], "-> %s" % bolge_malz(s, ad))
    kontrol("kontrol cubugu: tur, emici bolge 0, izleyici sogutucu",
            c["tur"] == "kontrol" and c["emici_bolge"] == 0 and c["izleyici_malzeme"] == "su")

    # gaz yoksa aralik Bos; zarf yapisal (celik), dis sogutucu (sodyum)
    s = _yukle("sfr_altigen")
    w.spec_yukle(s)
    ad = w.cubuk_ekle("yakit")
    kontrol("SFR: gaz yok -> aralik Bos (madde yok); zarf ss316; dis sodyum",
            bolge_malz(s, ad) == ["u10mo", sema.BOSLUK, "ss316", "sodyum"],
            "-> %s" % bolge_malz(s, ad))

    # zarf icin zirkonyum tercih edilir (celik once tanimli olsa da)
    s = _yukle("pwr_17x17")
    celik = copy.deepcopy(_yukle("sfr_altigen")["malzemeler"])
    s["malzemeler"] = [m for m in celik if m["ad"] == "ss316"] + s["malzemeler"]
    w.spec_yukle(s)
    ad = w.cubuk_ekle("yakit")
    kontrol("zarf: celikten once tanimli olsa da zirkaloy secilir",
            bolge_malz(s, ad)[2] == "zirkaloy4", "-> %s" % bolge_malz(s, ad))

    # plaka sablonu
    s = _yukle("mtr_plaka")
    w.spec_yukle(s)
    ad = w.plaka_ekle()
    p = sema.plaka_bul(s, ad)
    kontrol("plaka sablonu: yakit u3si2_al, zarf al6061, sogutucu su",
            (p["et_malzeme"], p["zarf_malzeme"], p["sogutucu"]) == ("u3si2_al", "al6061", "su"))

    # rol onbellegi uygunluk ile birebir ayni (kural uygunluk'ta kalir)
    from cekirdek import uygunluk
    from arayuz.sekme_cubuk import roller, rol_listesi
    esit = True
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        x = sema.yukle(yol)
        esit &= roller(x) == uygunluk.malzeme_rolleri(x)
        esit &= all(rol_listesi(x, r) == uygunluk.rol_malzemeleri(x, r) for r in uygunluk.ROLLER)
    x = _yukle("pwr_17x17")
    roller(x)
    sema.malzeme_bul(x, "su")["bilesim"] = [sema.bilesen("B", 4.0), sema.bilesen("C", 1.0)]
    kontrol("rol onbellegi uygunluk ile ayni, malzeme degisince yenileniyor",
            esit and "emici" in roller(x)["su"])

    # rolu karsilanmayan bolge ACIKCA isaretlenir (sessizce bosluk olmaz)
    s = _yukle("tamburlu_kor")
    w.spec_yukle(s)
    kontrol("(on kosul) tamburlu_kor'da zarf ve sogutucu rolu yok",
            sablon_eksik_roller(s, "yakit") == ["zarf (yapısal)", "soğutucu"],
            "-> %s" % sablon_eksik_roller(s, "yakit"))
    ad = w.cubuk_ekle("yakit")
    m = bolge_malz(s, ad)
    kontrol("eksik roller None kalir (bosluga donusmez)", m[2] is None and m[3] is None,
            "-> %s" % m)
    kutular = [w.c_tablo.cellWidget(i, 1) for i in range(w.c_tablo.rowCount())]
    kontrol("eksik bolgelerin kutusu kirmizi 'Malzeme secin'",
            isinstance(kutular[2], MalzemeKutusu) and kutular[2].eksik_mi()
            and kutular[3].eksik_mi() and not kutular[0].eksik_mi()
            and kutular[2].currentText() == "— Malzeme seçin —")
    kontrol("eksik uyarisi rolu adiyla soyluyor",
            w.c_eksik.isVisibleTo(w) and "zarf (yapısal)" in w.c_eksik.text(),
            "-> %r" % w.c_eksik.text())
    kontrol("listede eksik isareti", "⚠" in w.liste.currentItem().text())
    # kullanici malzeme secince isaret kalkar ve spec'e yazilir
    kutular[3].setCurrentIndex(kutular[3].findData("berilyum"))
    kutular = [w.c_tablo.cellWidget(i, 1) for i in range(w.c_tablo.rowCount())]
    kontrol("secim spec'e yazildi", bolge_malz(s, ad)[3] == "berilyum")

    # bos modelde ilk cubuk kora atanir -> model kurulur
    s = _yukle("pwr_pinhucre")
    s["cubuklar"] = []
    s["kor"]["cubuk"] = None
    w.spec_yukle(s)
    kontrol("bos durum eylemi 'Yakit cubugu ekle'",
            w.bos.dugme.isVisibleTo(w.bos) and w.bos.dugme.text() == "Yakıt çubuğu ekle")
    w.bos.dugme.click()
    kontrol("ilk cubuk kora atandi", s["kor"]["cubuk"] == "yakit_cubugu",
            "-> %s" % s["kor"]["cubuk"])
    kontrol("bos modelden pin hucre: dogrulama hatasiz",
            not dogrula.hata_var(dogrula.tum_kontroller(s, veri_kontrolu=False)),
            "-> %s" % [b.mesaj for b in dogrula.tum_kontroller(s, veri_kontrolu=False)
                       if b.seviye == "hata"])
    try:
        kurucu.kur(s)
        kontrol("bos modelden pin hucre: model kuruluyor", True)
    except Exception as e:
        kontrol("bos modelden pin hucre: model kuruluyor", False, "-> %s" % e)
    ad2 = w.cubuk_ekle("kilavuz")
    kontrol("dolu kor secimi degismez", s["kor"]["cubuk"] == "yakit_cubugu" and ad2)


# ============================================================================
# [P3] bolge tablosu
# ============================================================================

def test_bolge_tablosu():
    print("\n[P3] PARCALAR: yaricaplar artan sirada zorunlu")
    if _qt() is None:
        return
    from cekirdek import sema
    from arayuz.sekme_cubuk import CubukSekmesi
    w = CubukSekmesi()
    s = _yukle("pwr_17x17")
    w.spec_yukle(s)
    _cubuk_sec(w, "yakit_cubugu")
    c = sema.cubuk_bul(s, "yakit_cubugu")
    kutular = w._yaricap_kutulari()
    kontrol("dis bolge satirinda yaricap kutusu yok, 'dış bölge' yaziyor",
            w.c_tablo.cellWidget(3, 0) is None and w.c_tablo.item(3, 0).text() == "dış bölge")
    kontrol("dis bolge aciklamasi", w.c_tablo.item(3, 2).text().startswith("Dış bölge"))
    kontrol("bolge aciklamalari role gore",
            [w.c_tablo.item(i, 2).text() for i in range(3)]
            == ["Yakıt", "Yakıt-zarf aralığı", "Zarf / yapı"],
            "-> %s" % [w.c_tablo.item(i, 2).text() for i in range(3)])
    kontrol("siniri komsulardan: r2 in (r1, r3)",
            abs(kutular[1].minimum() - 0.40961) < 1e-9 and abs(kutular[1].maximum() - 0.47499) < 1e-9,
            "-> %s %s" % (kutular[1].minimum(), kutular[1].maximum()))
    kutular[1].setValue(0.30)                  # r1'in altina indirmeye calis
    r = [b["r"] for b in c["bolgeler"][:-1]]
    kontrol("yaricap komsusunu gecemez, spec artan kaldi",
            all(r[i] < r[i + 1] for i in range(len(r) - 1)) and abs(r[1] - 0.40961) < 1e-9,
            "-> %s" % r)
    kutular[1].setValue(0.418)

    # tasima: malzeme tasinir, yaricaplar yerinde
    r0 = [b["r"] for b in c["bolgeler"]]
    w.c_tablo.setCurrentCell(1, 2)
    kontrol("ic bolge secili: sil/ice/disa acik",
            w.d_bolge_sil.isEnabled() and w.d_ice.isEnabled() and w.d_disa.isEnabled())
    w.d_disa.click()
    kontrol("disa tasi: malzeme yer degisti, yaricaplar AYNI",
            [b["malzeme"] for b in c["bolgeler"]] == ["uo2", "zirkaloy4", "helyum", "su"]
            and [b["r"] for b in c["bolgeler"]] == r0)
    kontrol("secim tasinan bolgeyi izliyor", w.c_tablo.currentRow() == 2)
    kontrol("dis bolgeye tasinamaz (Disa tasi kapali)", not w.d_disa.isEnabled())
    w.d_ice.click()
    kontrol("ice tasi geri aldi", [b["malzeme"] for b in c["bolgeler"]]
            == ["uo2", "helyum", "zirkaloy4", "su"])
    w.c_tablo.setCurrentCell(3, 2)
    kontrol("dis bolge secili: sil/ice/disa kapali",
            not w.d_bolge_sil.isEnabled() and not w.d_ice.isEnabled()
            and not w.d_disa.isEnabled())

    # hucre widget'ina odaklanmak satiri secer
    from PySide6 import QtCore, QtGui, QtWidgets
    QtWidgets.QApplication.sendEvent(w._yaricap_kutulari()[0],
                                     QtGui.QFocusEvent(QtCore.QEvent.FocusIn))
    kontrol("yaricap kutusuna odak o satiri secer", w.c_tablo.currentRow() == 0)

    # ekle: dis bolgenin icine, malzemesi SECILMEMIS
    w.d_bolge_ekle.click()
    kontrol("bolge ekle: dis bolgenin icine, r artan, malzeme secilmemis",
            len(c["bolgeler"]) == 5 and c["bolgeler"][3]["malzeme"] is None
            and c["bolgeler"][3]["r"] > c["bolgeler"][2]["r"] and c["bolgeler"][4]["r"] is None)
    w.c_tablo.setCurrentCell(3, 2)
    w.d_bolge_sil.click()
    kontrol("bolge sil geri aldi", [b["malzeme"] for b in c["bolgeler"]]
            == ["uo2", "helyum", "zirkaloy4", "su"])

    # iki bolgeli cubukta sil kapali
    s = _yukle("pwr_pinhucre")
    sema.cubuk_bul(s, "yakit_cubugu")["bolgeler"] = [sema.bolge(0.45, "uo2"),
                                                    sema.bolge(None, "su")]
    w.spec_yukle(s)
    _cubuk_sec(w, "yakit_cubugu")
    w.c_tablo.setCurrentCell(0, 2)
    kontrol("iki bolgede sil kapali", not w.d_bolge_sil.isEnabled())

    # dosyadaki bozuk sira: sinir uygulanmaz (deger sessizce degismez), uyari gorunur
    s = _yukle("pwr_17x17")
    sema.cubuk_bul(s, "yakit_cubugu")["bolgeler"][1]["r"] = 0.40
    w.spec_yukle(s)
    _cubuk_sec(w, "yakit_cubugu")
    kontrol("bozuk sirali dosya: degerler degismedi, uyari gorunur",
            abs(w._yaricap_kutulari()[1].value() - 0.40) < 1e-9
            and w.c_sira_uyari.isVisibleTo(w)
            and sema.cubuk_bul(s, "yakit_cubugu")["bolgeler"][1]["r"] == 0.40)

    # kontrol cubugunda tasima emici bolgeyi izler
    s = _yukle("pwr_kontrol")
    w.spec_yukle(s)
    _cubuk_sec(w, "kontrol_cubugu")
    w.c_tablo.setCurrentCell(0, 2)
    w.d_disa.click()
    kc = sema.cubuk_bul(s, "kontrol_cubugu")
    kontrol("emici malzeme disa tasininca emici bolge onu izler",
            kc["bolgeler"][1]["malzeme"] == "b4c" and kc["emici_bolge"] == 1)


# ============================================================================
# [P4] ad degisimi
# ============================================================================

def _model_xml(spec):
    """Kurulan modelin XML'i; 'name' ozellikleri (parca adlari) cikarilmis."""
    from cekirdek import kurucu
    model, _ = kurucu.kur(spec)
    with tempfile.TemporaryDirectory() as t:
        yol = os.path.join(t, "model.xml")
        model.export_to_model_xml(yol)
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
    return re.sub(r'\sname="[^"]*"', "", metin)


def _bulgular(spec, esleme=None):
    from cekirdek import dogrula
    sonuc = []
    for b in dogrula.tum_kontroller(spec, veri_kontrolu=False):
        metin = "%s|%s|%s" % (b.seviye, b.yer, b.mesaj)
        for eski, yeni in (esleme or {}).items():
            metin = metin.replace(yeni, eski)
        sonuc.append(metin)
    return sorted(sonuc)


def test_ad_degisimi(gecici=None):
    print("\n[P4] AD DEGISIMI: 11 ornekte her parca/demet yeniden adlandirilir")
    if _qt() is None:
        return
    import warnings
    warnings.filterwarnings("ignore")
    from cekirdek import dogrula, sema
    from arayuz.sekme_cubuk import CubukSekmesi, parca_adini_degistir
    from arayuz.sekme_demet import DemetSekmesi
    ornekler = sorted(glob.glob(os.path.join(ORNEK, "*.json")))
    kontrol("11 ornek bulundu", len(ornekler) == 11, "-> %d" % len(ornekler))
    toplam = 0
    for yol in ornekler:
        ad = os.path.splitext(os.path.basename(yol))[0]
        s = sema.yukle(yol)
        once_xml = _model_xml(copy.deepcopy(s))
        once_bulgu = _bulgular(s)
        esleme = {}
        c = CubukSekmesi()
        c.spec_yukle(s)
        for tur, liste, alan in (("cubuk", "cubuklar", c.c_ad), ("plaka", "plakalar", c.p_ad)):
            for eski in [x["ad"] for x in s.get(liste, [])]:
                c._sec((tur, eski))
                yeni = "yeni_" + eski
                alan.setText(yeni)
                alan.editingFinished.emit()
                esleme[eski] = yeni
        d = DemetSekmesi()
        d.spec_yukle(s)
        for eski in [x["ad"] for x in s.get("demetler", [])]:
            d._sec(eski)
            yeni = "yeni_" + eski
            d.ad.setText(yeni)
            d.ad.editingFinished.emit()
            esleme[eski] = yeni
        toplam += len(esleme)
        adlar = {x["ad"] for l in ("cubuklar", "plakalar", "demetler") for x in s.get(l, [])}
        kontrol("%s: %d ad degisti" % (ad, len(esleme)), adlar == set(esleme.values()),
                "-> %s" % sorted(adlar))
        metin = json.dumps(s, ensure_ascii=False)
        kalan = [e for e in esleme if '"%s"' % e in metin]
        kontrol("%s: eski ad spec'te kalmadi" % ad, not kalan, "-> %s" % kalan)
        kontrol("%s: model XML'i ayni" % ad, _model_xml(copy.deepcopy(s)) == once_xml)
        sonra = _bulgular(s, esleme)
        kontrol("%s: dogrulama bulgulari ayni (yeni hata yok)" % ad,
                sonra == once_bulgu and not dogrula.hata_var(
                    dogrula.tum_kontroller(s, veri_kontrolu=False)),
                "-> %s" % sorted(set(sonra) ^ set(once_bulgu))[:3])
    kontrol("toplam en az 15 parca/demet yeniden adlandirildi", toplam >= 15, "-> %d" % toplam)

    # referanslarin HEPSI (ornekte gecmeyenler dahil): sentetik spec
    s = _yukle("pwr_eksenel")
    s["kor"]["dolgu"] = "demet_blanket"
    s["kor"]["anahtar"] = {"A": "demet_blanket"}
    s["kor"]["eksenel"]["bolgeler"][1]["anahtar"] = {"A": "demet_blanket"}
    s["guc_dagilimi"]["cubuk"] = "blanket_cubugu"
    n1 = parca_adini_degistir(s, "demet_blanket", "db")
    n2 = parca_adini_degistir(s, "blanket_cubugu", "bc")
    kor = s["kor"]
    kontrol("referanslar: kor dolgu/anahtar, katman dolgu/anahtar, demet anahtari, guc",
            kor["dolgu"] == "db" and kor["anahtar"] == {"A": "db"}
            and kor["eksenel"]["bolgeler"][1]["dolgu"] == "db"
            and kor["eksenel"]["bolgeler"][1]["anahtar"] == {"A": "db"}
            and s["guc_dagilimi"]["cubuk"] == "bc"
            and sema.demet_bul(s, "db")["anahtar"]["y"] == "bc", "-> %d %d" % (n1, n2))

    # gecersiz adlar reddedilir, spec degismez, hata gorunur
    s = _yukle("pwr_17x17")
    c = CubukSekmesi()
    c.spec_yukle(s)
    c._sec(("cubuk", "yakit_cubugu"))
    once = json.dumps(s, sort_keys=True)
    for yeni, neden in (("su", "malzeme adi"), ("kilavuz_boru", "baska cubuk"),
                        ("demet_17x17", "demet adi"), ("bosluk", "ayrilmis"), ("  ", "bos"),
                        ("kilavuz-boru", "betikte ayni degisken")):
        c.c_ad.setText(yeni)
        c.c_ad.editingFinished.emit()
        kontrol("gecersiz ad reddedildi (%s)" % neden,
                json.dumps(s, sort_keys=True) == once and c.c_ad.text() == "yakit_cubugu"
                and c.c_ad_hata.isVisibleTo(c), "-> %r" % c.c_ad_hata.text())
    d = DemetSekmesi()
    d.spec_yukle(s)
    d.ad.setText("yakit_cubugu")
    d.ad.editingFinished.emit()
    kontrol("demet adi cubuk adina cakisamaz",
            json.dumps(s, sort_keys=True) == once and d.ad_hata.isVisibleTo(d))


# ============================================================================
# [P5] palet
# ============================================================================

def test_demet_palet():
    print("\n[P5] DEMET: palet yalnizca uygun parcalari gosterir")
    if _qt() is None:
        return
    from cekirdek import sema
    from arayuz.sekme_demet import DemetSekmesi, palet_listesi, en_sik_parca
    w = DemetSekmesi()
    s = _yukle("pwr_17x17")
    w.spec_yukle(s)
    kontrol("17x17 paleti: cubuklar + sogutucu hucresi",
            w.palet.adlar() == ["yakit_cubugu", "kilavuz_boru", "su"], "-> %s" % w.palet.adlar())
    kontrol("varsayilan firca en sik parca (yakit cubugu; eskiden 'e' = enstruman borusu)",
            w.palet.secili() == "yakit_cubugu" and w.kare_izgara.firca() == "yakit_cubugu")
    kontrol("palet etiketlerinde harf yok",
            all(len(w.palet.etiket(a)) > 2 for a in w.palet.adlar()))

    s = _yukle("pwr_eksenel")
    d = sema.demet_bul(s, "demet_17x17")
    adlar = [o[0] for o in palet_listesi(s, d)]
    kontrol("kendisi ve sigmayan ic demetler palette yok",
            "demet_17x17" not in adlar and "demet_blanket" not in adlar, "-> %s" % adlar)
    w.spec_yukle(s)
    kontrol("sigmayan ic demet icin yol gosteren not",
            w.palet_notu.isVisibleTo(w) and "demet_blanket" in w.palet_notu.text())
    # buyuk adimli bir dis demet: sigan ayni tip ic demetler listelenir
    dis = sema.demet("kor_demeti", 21.5, [2, 2], ["yy", "yy"], {"y": "demet_17x17"}, "su")
    s["demetler"].append(dis)
    adlar = [o[0] for o in palet_listesi(s, dis)]
    kontrol("adim yeterliyse ayni tipte ic demetler palette",
            {"demet_17x17", "demet_blanket", "demet_plenum"} <= set(adlar)
            and "kor_demeti" not in adlar, "-> %s" % adlar)
    adlar = [o[0] for o in palet_listesi(s, d)]
    kontrol("dongu yok: 17x17 paletinde onu iceren kor_demeti yok", "kor_demeti" not in adlar)

    s = _yukle("sfr_altigen")
    s["demetler"].append(sema.demet("kare_ic", 20.0, [1, 1], ["y"], {"y": "yakit_cubugu"},
                                    "sodyum"))
    hexd = sema.demet_bul(s, "demet_hex")
    hexd["adim"] = 25.0                         # olcu bahane olmasin: tip uyumsuzlugu
    adlar = [o[0] for o in palet_listesi(s, hexd)]
    kontrol("altigen icinde kare demet yok", "kare_ic" not in adlar, "-> %s" % adlar)
    kontrol("kare icinde altigen demet yok",
            "demet_hex" not in [o[0] for o in palet_listesi(s, sema.demet_bul(s, "kare_ic"))])
    s = _yukle("sfr_altigen")
    w.spec_yukle(s)
    kontrol("SFR paleti: yakit, emici, sodyum; firca yakit",
            w.palet.adlar() == ["yakit_cubugu", "emici_cubuk", "sodyum"]
            and w.palet.secili() == "yakit_cubugu", "-> %s" % w.palet.adlar())
    w.tum_malzemeler.setChecked(True)
    kontrol("Gelismis: butun malzemeler ve Bos hucre",
            {"u10mo", "ss316", "b4c", "bosluk"} <= set(w.palet.adlar()))
    i = w.palet.adlar().index("bosluk")
    kontrol("Bos hucre etiketi Turkce", w.palet.liste.item(i).text() == "Boş (madde yok)")
    w.tum_malzemeler.setChecked(False)
    kontrol("haritada gecen parca her zaman listede",
            set(a for r in w.hex_izgara.adlar() for a in r) <= set(w.palet.adlar()))
    kontrol("en_sik_parca", en_sik_parca([["a", "b"], ["b", None]]) == "b"
            and en_sik_parca([[None]]) is None)


# ============================================================================
# [P6] boyama
# ============================================================================

def test_demet_boyama():
    print("\n[P6] DEMET: surukleyerek boyama spec'e harita yazar")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtCore
    from cekirdek import altigen, sema
    from arayuz.sekme_demet import DemetSekmesi
    L, N, R = QtCore.Qt.LeftButton, QtCore.Qt.NoButton, QtCore.Qt.RightButton
    E = QtCore.QEvent
    s = _yukle("pwr_17x17")
    d = sema.demet_bul(s, "demet_17x17")
    harita0, anahtar0 = list(d["harita"]), dict(d["anahtar"])
    w = DemetSekmesi()
    w.resize(900, 800)
    w.spec_yukle(s)
    bildirim = []
    w.degisti.connect(bildirim.append)
    iz = w.kare_izgara
    iz.resize(560, 560)
    kontrol("kare harita KareIzgara'da, harfsiz adlarla",
            w.harita_yigin.currentWidget() is iz and iz.adlar()[0][0] == "yakit_cubugu")
    w.palet.sec("kilavuz_boru")
    kontrol("palet secimi izgaranin fircasi", iz.firca() == "kilavuz_boru")
    _fare(iz, E.MouseButtonPress, iz.hucre_merkezi((0, 0)), L, L)
    _fare(iz, E.MouseMove, iz.hucre_merkezi((0, 4)), N, L)
    _fare(iz, E.MouseButtonRelease, iz.hucre_merkezi((0, 4)), L, N)
    kontrol("surukleme ilk satirin 5 hucresini boyadi (harita 'k')",
            d["harita"][0][:5] == "kkkkk" and d["harita"][0][5:] == harita0[0][5:],
            "-> %s" % d["harita"][0])
    kontrol("diger satirlar ve anahtar degismedi",
            d["harita"][1:] == harita0[1:] and d["anahtar"] == anahtar0)
    kontrol("bir darbe = bir bildirim", bildirim == ["demet"], "-> %s" % bildirim)
    # 'e' harfli (enstruman borusu) hucre ayni parca: harfi korunur
    e_konum = [(r, c) for r, satir in enumerate(harita0) for c, h in enumerate(satir) if h == "e"]
    kontrol("(on kosul) 'e' harfli hucre var", bool(e_konum))
    r, c = e_konum[0]
    kontrol("dokunulmayan 'e' hucresi harfini korur", d["harita"][r][c] == "e")
    # sag tik: hucrenin parcasi firca olur
    w.palet.sec("su")
    _fare(iz, E.MouseButtonPress, iz.hucre_merkezi((8, 8)), R, R)
    kontrol("sag tik hucrenin parcasini secer", w.palet.secili() == iz.adlar()[8][8]
            == "kilavuz_boru", "-> %s" % w.palet.secili())
    # yeni parca (malzeme hucresi): yeni harf eklenir, eskiler korunur
    w.palet.sec("su")
    _fare(iz, E.MouseButtonPress, iz.hucre_merkezi((16, 16)), L, L)
    _fare(iz, E.MouseButtonRelease, iz.hucre_merkezi((16, 16)), L, N)
    yeni_harf = [h for h, a in d["anahtar"].items() if a == "su"]
    kontrol("yeni parca yeni harf aldi, eski anahtar korundu",
            len(yeni_harf) == 1 and d["harita"][16][16] == yeni_harf[0]
            and all(d["anahtar"][h] == a for h, a in anahtar0.items()),
            "-> %s" % d["anahtar"])
    # tumunu doldur
    w.palet.sec("yakit_cubugu")
    w.d_hepsi.click()
    kontrol("tumunu doldur: butun hucreler 'y'",
            all(set(satir) == {"y"} for satir in d["harita"]) and len(d["harita"]) == 17)

    # altigen: halka doldurma merkezden disa numarali; var olan harf ('e') kullanilir
    s = _yukle("sfr_altigen")
    h = sema.demet_bul(s, "demet_hex")
    w.spec_yukle(s)
    kontrol("altigen harita AltigenIzgara'da", w.harita_yigin.currentWidget() is w.hex_izgara)
    kontrol("halka listesi merkezden: 'Merkez hücre' ilk",
            w.halka_secim.itemText(0) == "Merkez hücre" and w.halka_secim.count() == 7)
    w.palet.sec("emici_cubuk")
    w.halka_secim.setCurrentIndex(0)
    w.d_halka_doldur.click()
    kontrol("merkez hucre emici; anahtardaki 'e' harfi kullanildi",
            h["harita"][-1] == "e" and h["anahtar"] == {"y": "yakit_cubugu", "e": "emici_cubuk"},
            "-> %s %s" % (h["harita"][-1], h["anahtar"]))
    w.halka_secim.setCurrentIndex(1)
    w.d_halka_doldur.click()
    kontrol("1. halka (6 hucre) emici", h["harita"][-2] == "eeeeee", "-> %s" % h["harita"][-2])
    kontrol("halka uzunluklari degismedi",
            [len(x) for x in h["harita"]] == altigen.halka_uzunluklari(7))
    uyg  # noqa: B018


# ============================================================================
# [P7] yerlesim (gercek pencere)
# ============================================================================

def test_demet_yerlesim(gecici=None):
    print("\n[P7] DEMET: iki sutun, 17x17 harita kaydirmasiz")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtCore
    from arayuz.ana_pencere import AnaPencere
    p = AnaPencere()
    p._kaydetme_sor = lambda: True
    try:
        p.resize(1600, 950)
        p.show()
        p._proje_kur(_yukle("pwr_17x17"), None, None)
        p.sekmeye_git("demet", sessiz=True)
        for _ in range(6):
            uyg.processEvents()
        alan = p.sekme_sayfasi(p.gecerli_sekme())
        w = p.s_demet
        iz = w.kare_izgara
        iz._geometri()
        kontrol("demet sekmesi dikey/yatay kaydirmasiz",
                alan.verticalScrollBar().maximum() == 0
                and alan.horizontalScrollBar().maximum() == 0,
                "-> %d %d" % (alan.verticalScrollBar().maximum(),
                              alan.horizontalScrollBar().maximum()))
        kontrol("hucre boyutu >= 28 px (17x17)", iz._olcek >= 28, "-> %.1f px" % iz._olcek)
        kontrol("harita tamamen gorunur", iz._olcek * 17 <= min(iz.width(), iz.height()))
        sol = iz.mapTo(w, QtCore.QPoint(0, 0)).x()
        sag = w._sag.mapTo(w, QtCore.QPoint(0, 0)).x()
        kontrol("harita solda ve sag sutundan genis",
                sol < sag and iz.width() > w._sag.width(),
                "-> harita %d px, sag %d px" % (iz.width(), w._sag.width()))
        print("    olculen: hucre %.1f px, harita %dx%d, sag sutun %d px"
              % (iz._olcek, iz.width(), iz.height(), w._sag.width()))
        p._proje_kur(_yukle("sfr_altigen"), None, None)
        p.sekmeye_git("demet", sessiz=True)
        for _ in range(6):
            uyg.processEvents()
        w.hex_izgara._geometri()
        kontrol("altigen 7 halka: hucre >= 28 px, kaydirmasiz",
                w.hex_izgara._olcek >= 28 and alan.verticalScrollBar().maximum() == 0,
                "-> %.1f px" % w.hex_izgara._olcek)
        p._proje_kur(_yukle("pwr_eksenel"), None, None)      # uc demet: uzun liste
        p.sekmeye_git("demet", sessiz=True)
        for _ in range(6):
            uyg.processEvents()
        iz._geometri()
        kontrol("uc demetli model: kaydirmasiz, hucre >= 28 px",
                alan.verticalScrollBar().maximum() == 0 and iz._olcek >= 28,
                "-> kaydirma %d, %.1f px" % (alan.verticalScrollBar().maximum(), iz._olcek))
    finally:
        p._kirli = False
        p.close()
        p.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


# ============================================================================
# [P8] adim, dis dolgu, ekleme, bos durum
# ============================================================================

def test_demet_ozellikler():
    print("\n[P8] DEMET: adim siniri, dis dolgu, ekleme ve bos durum")
    if _qt() is None:
        return
    from cekirdek import dogrula, kurucu, sema
    from arayuz.sekme_demet import DemetSekmesi
    w = DemetSekmesi()
    s = _yukle("pwr_17x17")
    w.spec_yukle(s)
    kontrol("kafes tipi kutusu yok", not hasattr(w, "tur"))
    kontrol("adim alt siniri = en buyuk cubuk dis capi (kilavuz 1.204 cm)",
            abs(w.adim.minimum() - 1.204) < 1e-9, "-> %s" % w.adim.minimum())
    w.adim.setValue(1.0)
    kontrol("adim cubuk capinin altina inemez", abs(sema.demet_bul(s, "demet_17x17")["adim"]
                                                     - 1.204) < 1e-9)
    s = _yukle("pwr_17x17")
    sema.demet_bul(s, "demet_17x17")["adim"] = 1.1        # bozuk dosya
    w.spec_yukle(s)
    kontrol("dosyadaki kucuk adim sessizce buyutulmez",
            abs(w.adim.value() - 1.1) < 1e-9 and sema.demet_bul(s, "demet_17x17")["adim"] == 1.1)
    s = _yukle("sfr_altigen")
    w.spec_yukle(s)
    kontrol("altigen adim siniri = en buyuk cubuk (0.79 cm)",
            abs(w.adim.minimum() - 0.79) < 1e-9, "-> %s" % w.adim.minimum())

    # dis dolgu: tek demetin kendisi kare demetse kullanilmaz -> gizli
    w.spec_yukle(_yukle("pwr_17x17"))
    kontrol("kare tek demet: 'Demet disi' gizli", not w.e_dis.isVisibleTo(w))
    w.spec_yukle(s)
    kontrol("altigen: 'Demet disi' gorunur, yakit listede yok",
            w.e_dis.isVisibleTo(w) and "u10mo" not in _kutu_verileri(w.dis)
            and w.dis.currentData() == "sodyum")

    # tam kor modelinde altigen demet sunulmaz
    s = _yukle("pwr_17x17")
    s["kor"]["tur"] = "kare_kafes"
    w.spec_yukle(s)
    kontrol("tam kor: '+ Altigen demet' gizli, '+ Kare demet' gorunur",
            not w.d_hex.isVisibleTo(w) and w.d_kare.isVisibleTo(w))

    # cubuk yokken: + kapali, bos durum, mesaj kontrol ettigiyle ayni
    s = _yukle("mtr_plaka")
    s["kor"]["tur"] = "tek_demet"
    s["kor"]["demet"] = None
    w.spec_yukle(s)
    mesajlar = []
    w._bilgi = lambda b, m: mesajlar.append(m)
    kontrol("cubuk yok (yalniz plaka): + dugmeleri kapali, ipucu cubuk istiyor",
            not w.d_kare.isEnabled() and "çubuk" in w.d_kare.toolTip()
            and "plaka" not in w.d_kare.toolTip())
    kontrol("bos durum: 'Once cubuk gerekli', eylemsiz",
            w.harita_yigin.currentWidget() is w.bos and "çubuk" in w.bos.baslik.text()
            and not w.bos.dugme.isVisibleTo(w.bos))
    kontrol("demet yokken ozellikler ve palet gizli/kapali",
            not w.ozellik.isVisibleTo(w) and not w.palet.isEnabled())
    w._yeni("kare")
    kontrol("mesaj yalnizca kontrol edileni (cubuk) soyluyor",
            len(mesajlar) == 1 and "çubuk" in mesajlar[0] and "plaka" not in mesajlar[0],
            "-> %s" % mesajlar)

    # cubuk var, demet yok: bos durum eylemi demet kurar, kora atanir, model kurulur
    s = _yukle("pwr_17x17")
    s["demetler"] = []
    s["kor"]["demet"] = None
    w.spec_yukle(s)
    kontrol("bos durum eylemi '+ Kare demet'",
            w.bos.dugme.isVisibleTo(w.bos) and w.bos.dugme.text() == "+ Kare demet")
    w.bos.dugme.click()
    d = s["demetler"][0] if s["demetler"] else None
    kontrol("yeni demet yakit cubuguyla dolu, kora atandi",
            d is not None and s["kor"]["demet"] == d["ad"]
            and set(d["anahtar"].values()) == {"yakit_cubugu"}, "-> %s" % (d and d["anahtar"]))
    kontrol("yeni demet dogrulamada hatasiz ve kuruluyor",
            not dogrula.hata_var(dogrula.tum_kontroller(s, veri_kontrolu=False)))
    try:
        kurucu.kur(s)
        kontrol("yeni demetli model kuruldu", True)
    except Exception as e:
        kontrol("yeni demetli model kuruldu", False, "-> %s" % e)
    ad = w._yeni("altigen")
    h = sema.demet_bul(s, ad)
    kontrol("altigen demet: adim cubuk capina sigiyor",
            h["tur"] == "altigen" and h["adim"] >= 0.95, "-> %s" % h["adim"])
    kontrol("ikinci demet kor secimini degistirmez", s["kor"]["demet"] == d["ad"])


# ============================================================================
# [Y1] yavas: sablondan pin hucre fiziksel olarak makul
# ============================================================================

def test_yavas_sablon_pin(gecici):
    print("\n[Y1] SABLON: bos modelde '+ Cubuk > PWR yakit cubugu' k-inf makul")
    if _qt() is None:
        return
    import warnings
    warnings.filterwarnings("ignore")
    from cekirdek import dogrula, kurucu, sema
    from arayuz.sekme_cubuk import CubukSekmesi
    s = _yukle("pwr_pinhucre")
    s["cubuklar"] = []
    s["kor"]["cubuk"] = None
    s["ayarlar"]["parcacik"] = 2000
    s["ayarlar"]["cevrim"] = 40
    s["ayarlar"]["pasif"] = 10
    w = CubukSekmesi()
    w.spec_yukle(s)
    w.cubuk_ekle("yakit")
    kontrol("(on kosul) dogrulama hatasiz",
            not dogrula.hata_var(dogrula.tum_kontroller(s, veri_kontrolu=False)))
    model, _ = kurucu.kur(s)
    dizin = os.path.join(gecici, "sablon_pin")
    os.makedirs(dizin, exist_ok=True)
    try:
        import openmc
        sp = model.run(cwd=dizin, threads=ISLEM_PARCACIGI, output=False)
        with openmc.StatePoint(sp) as st:
            k = st.keff
        kontrol("sablon pin hucre k-inf 1.25-1.50 (PWR UO2 %3.x)",
                1.25 < k.nominal_value < 1.50, "-> %.4f +/- %.4f" % (k.nominal_value, k.std_dev))
    except Exception as e:
        kontrol("sablon pin hucre kosusu", False, "-> %s" % e)


HIZLI = [test_parca_gorunurluk, test_sablon_malzemeleri, test_bolge_tablosu,
         test_demet_palet, test_demet_boyama, test_demet_ozellikler]
YAVAS = [test_yavas_sablon_pin, test_demet_yerlesim, test_ad_degisimi]


if __name__ == "__main__":
    import sys
    import shutil
    hizli = "--hizli" in sys.argv
    for f in HIZLI:
        f()
    if not hizli:
        g = tempfile.mkdtemp(prefix="parca_demet_")
        for f in YAVAS:
            f(g)
        shutil.rmtree(g, True)
    from testler.ortak_test import _gecti, _kaldi
    print("\nSONUC: %d gecti, %d kaldi" % (len(_gecti), len(_kaldi)))
    for k in _kaldi:
        print("  KALDI:", k)
