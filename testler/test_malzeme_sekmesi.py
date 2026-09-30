# -*- coding: utf-8 -*-
"""
test_malzeme_sekmesi.py -- Dalga 3 Malzemeler sekmesi.

  [M1] Kutuphane listesi   : rol gruplari (uygunluk ile celismez), okunur ad,
                             varsayilan UO2, dosya adi ipucu yok
  [M2] Parametre formlari  : yalnizca anlamli parametreler, her malzemede
                             sicaklik + canli °C, gercek Turkce etiketler
  [M3] Parametrik malzeme  : kutup kaydi, Duzenle ayni formu acar, yeniden
                             uretim (su 580->600 K, UO2 %3.2->%4.5), bit bit
                             ayni yeniden uretim, elle degismis malzeme
  [M4] kurucu / kod_uret   : "kutup" anahtarini yok sayar
  [M5] Bilesim tablosu     : zenginlik yalnizca U elementinde, tur/birim acilir
                             liste, spec degerleri aynen
  [M6] Gelismis + tek ad   : nadir alanlar Gelismis'te, S(a,b) onerisi
                             dogrula kurallariyla ayni
  [M7] Sekme               : Duzenle/Kopyala/Sil yalniz secimle, bos durum
  [M8] Ad degisimi         : 11 ornekte her malzeme -> ayni hucre-malzeme
                             eslemesi, dogrula ayni bulgular; genel ad
                             alanlari, golgeleme, cakisma
  [M9] Uctan uca           : sekmeden ad degisimi butun referanslari tasir
  [M10] Turkce metinler

Yalnizca offscreen calisir; modal diyaloglar exec() EDILMEZ (sekmenin
_diyalog_calistir kancasi ezilir).
"""

import copy
import glob
import json
import os
import re
import warnings

from testler.ortak_test import kontrol, ORNEK, KOK   # noqa: F401

warnings.filterwarnings("ignore")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _yukle(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _j(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False)


def _dogal_metinler(w):
    """Bir widget agacindaki kullaniciya gorunen metinler (etiket, dugme, baslik)."""
    from PySide6 import QtWidgets
    metinler = []
    if isinstance(w, QtWidgets.QWidget) and w.windowTitle():
        metinler.append(w.windowTitle())
    for c in w.findChildren(QtWidgets.QLabel):
        metinler.append(c.text())
    for c in w.findChildren(QtWidgets.QAbstractButton):
        metinler.append(c.text())
        metinler.append(c.toolTip())
    for c in w.findChildren(QtWidgets.QGroupBox):
        metinler.append(c.title())
    for c in w.findChildren(QtWidgets.QTableWidget):
        metinler += [c.horizontalHeaderItem(i).text() for i in range(c.columnCount())]
    for c in w.findChildren(QtWidgets.QTreeWidget):
        it = QtWidgets.QTreeWidgetItemIterator(c)
        while it.value():
            metinler.append(it.value().text(0))
            it += 1
    return [m for m in metinler if m]


# ----------------------------------------------------------------------------
# [M1] kutuphane listesi
# ----------------------------------------------------------------------------

BEKLENEN_GRUP = {
    "uo2": "yakit", "mox": "yakit", "un": "yakit", "u10mo": "yakit", "u3si2_al": "yakit",
    "zirkaloy4": "yapisal", "ss316": "yapisal", "fecral": "yapisal", "ma956": "yapisal",
    "sic": "yapisal", "al6061": "yapisal",
    "su": "sogutucu", "agir_su": "sogutucu", "sodyum": "sogutucu", "lbe": "sogutucu",
    "grafit": "sogutucu", "berilyum": "sogutucu",
    "b4c": "emici", "agincd": "emici", "gd2o3": "emici",
    "helyum": "gaz",
}


def test_kutuphane_listesi():
    print("\n[M1] KUTUPHANE LISTESI: rol gruplari, okunur ad, varsayilan UO2")
    _qt()
    from PySide6 import QtCore
    from cekirdek import malzeme_kutup as mk, uygunluk
    from arayuz import sekme_malzeme as sm

    gruplar = sm.kutuphane_gruplari()
    grup_of = {k: g for g, _e, ks in gruplar for k in ks}
    kontrol("kutuphanenin her malzemesi tam bir grupta",
            sorted(grup_of) == sorted(mk.KUTUPHANE)
            and sum(len(ks) for _g, _e, ks in gruplar) == len(mk.KUTUPHANE))
    kontrol("grup sirasi Yakit / Zarf ve yapisal / Sogutucu ve moderator / Emici / Gaz",
            [e for _g, e, _k in gruplar] == ["Yakıt", "Zarf ve yapısal",
                                               "Soğutucu ve moderatör", "Emici", "Gaz"],
            "-> %s" % [e for _g, e, _k in gruplar])
    yanlis = {k: g for k, g in grup_of.items() if BEKLENEN_GRUP.get(k) != g}
    kontrol("her malzeme beklenen grupta", not yanlis, "(yanlis: %s)" % yanlis)
    # uygunluk ile celismez: grup, rollerin ailesinden
    celiski = []
    for k, g in grup_of.items():
        r = uygunluk.tek_malzeme_rolleri(mk.uret(k))
        tamam = {"yakit": "yakit" in r, "emici": "emici" in r, "gaz": "gaz" in r,
                 "sogutucu": bool(r & {"sogutucu", "moderator"}) and not r & {"yakit", "emici"},
                 "yapisal": r == {"yapisal"}}[g]
        if not tamam:
            celiski.append((k, g, sorted(r)))
    kontrol("grup uygunluk.tek_malzeme_rolleri ile celismez", not celiski, "%s" % celiski)

    d = sm.KutuphaneDiyalog(_yukle("pwr_17x17"))
    ust = [d.liste.topLevelItem(i) for i in range(d.liste.topLevelItemCount())]
    kontrol("liste basliklari = gruplar",
            [u.text(0) for u in ust] == [e for _g, e, _k in gruplar])
    kontrol("grup basliklari secilemez",
            all(not (u.flags() & QtCore.Qt.ItemIsSelectable) for u in ust))
    cocuk = [u.child(i) for u in ust for i in range(u.childCount())]
    anahtarlar = [c.data(0, QtCore.Qt.UserRole) for c in cocuk]
    kontrol("her anahtar bir kez listede", sorted(anahtarlar) == sorted(mk.KUTUPHANE))
    ham = [c.text(0) for c in cocuk if c.text(0) in mk.KUTUPHANE or "_" in c.text(0)]
    kontrol("ham anahtar ('u3si2_al') gosterilmiyor; okunur ad var", not ham, "%s" % ham)
    kontrol("U3Si2-Al okunur adla: 'U₃Si₂-Al — dispersiyon yakıtı'",
            mk.okunur_ad("u3si2_al") in [c.text(0) for c in cocuk])
    kontrol("varsayilan secim UO2 (eskiden alfabetik ilk: agincd)", d.secilen() == "uo2",
            "-> %s" % d.secilen())
    kontrol("ilk grubun ilk ogesi UO2", ust[0].child(0).data(0, QtCore.Qt.UserRole) == "uo2")
    metin = " ".join(_dogal_metinler(d))
    kontrol("dosya adi ipucu yok (malzeme_kutup.py)", "malzeme_kutup" not in metin
            and ".py" not in metin)
    kontrol("pencere basligi Turkce", d.windowTitle() == "Kütüphaneden malzeme ekle")
    # yeni malzeme adi benzersiz ve sonucta kutup kaydi var
    kontrol("var olan 'uo2' -> yeni ad 'uo2_2'", d.ad.text() == "uo2_2", "-> %s" % d.ad.text())
    d.sec("su")
    kontrol("secim degisince (ad elle degismediyse) ad da degisir: 'su_2'",
            d.ad.text() == "su_2", "-> %s" % d.ad.text())
    d.ad.setText("sogutucu")
    d._ad_duzenlendi("sogutucu")
    d.sec("lbe")
    kontrol("elle verilen ad secim degisince korunur", d.ad.text() == "sogutucu")
    d.ad.setText("uo2")
    kontrol("var olan ada izin yok: Ekle pasif + hata metni",
            not d.d_tamam.isEnabled() and d.ad_hata.isVisibleTo(d)
            and "başka bir malzeme" in d.ad_hata.text())
    d.ad.setText("yakit_cubugu")
    kontrol("cubuk adiyla cakisan ada izin yok", not d.d_tamam.isEnabled())
    d.close()


# ----------------------------------------------------------------------------
# [M2] parametre formlari
# ----------------------------------------------------------------------------

def test_parametre_formlari():
    print("\n[M2] PARAMETRE FORMLARI: yalnizca anlamli parametreler, sicaklik + °C")
    _qt()
    from cekirdek import malzeme_kutup as mk
    from arayuz import sekme_malzeme as sm

    eksik_sicaklik, ham_etiket = [], []
    for k in mk.KUTUPHANE:
        f = sm.ParametreFormu(k)
        if not isinstance(f.alanlar.get("sicaklik"), sm.SicaklikGirdi):
            eksik_sicaklik.append(k)
        for e in f.etiketler.values():
            if "_" in e.text():
                ham_etiket.append((k, e.text()))
    kontrol("her kutuphane malzemesinde sicaklik soruluyor", not eksik_sicaklik,
            "%s" % eksik_sicaklik)
    kontrol("etiketlerde ham anahtar yok", not ham_etiket, "%s" % ham_etiket)

    f = sm.ParametreFormu("uo2")
    kontrol("UO2: 'U-235 ağırlıkça %' etiketi",
            f.etiketler["zenginlik"].text() == "U-235 ağırlıkça %:")
    kontrol("UO2 formunda bor YOK (UO2 uzerinde bor cikmasin)", "bor_ppm" not in f.alanlar)
    kontrol("UO2: yogunluk sorulur (hesaplanan yok)",
            "yogunluk" in f.alanlar and f.hesaplanan is None)
    s = f.alanlar["sicaklik"]
    s.setValue(600.0)
    kontrol("°C canli: 600 K -> '= 326.9 °C'", s.celsius.text() == "= 326.9 °C",
            "-> %s" % s.celsius.text())
    s.setValue(900.0)
    kontrol("°C canli: 900 K -> '= 626.9 °C'", s.celsius.text() == "= 626.9 °C")

    f = sm.ParametreFormu("su")
    kontrol("su: 'Çözünmüş bor [ppm]' etiketi",
            f.etiketler["bor_ppm"].text() == "Çözünmüş bor [ppm]:")
    kontrol("su formunda zenginlik yok, yogunluk SORULMAZ (sicakliktan)",
            "zenginlik" not in f.alanlar and "yogunluk" not in f.alanlar
            and f.hesaplanan is not None)
    f.alanlar["sicaklik"].setValue(600.0)
    kontrol("su: hesaplanan yogunluk sicaklikla canli",
            f.hesaplanan.text() == "%.4f g/cm³" % mk.su_yogunluk(600.0),
            "-> %s" % f.hesaplanan.text())
    kontrol("su: sicaklik araligi tablo araligi (273.15-623.15 K)",
            f.alanlar["sicaklik"].kutu.minimum() == 273.15
            and f.alanlar["sicaklik"].kutu.maximum() == 623.15)

    f = sm.ParametreFormu("b4c")
    kontrol("B4C varsayilan: dogal bor (None), kutuda 'doğal' yazar",
            f.param()["b10_zenginlik"] is None
            and "doğal" in f.alanlar["b10_zenginlik"].text())
    f.alanlar["b10_zenginlik"].setValue(90.0)
    m = f.malzeme()
    kontrol("B4C %90 B-10 -> B10 nuklid satiri",
            any(b["isim"] == "B10" and b["tur"] == "nuklid" for b in m["bilesim"])
            and m["kutup"]["param"]["b10_zenginlik"] == 90.0)

    # Yogunluk artik U yuklemesi ve gozeneklilikten hesaplanir (eskiden 5.4
    # g/cm3 sabitti ve form tutarsizlik uyarisi gosteriyordu).
    f = sm.ParametreFormu("u3si2_al")
    kontrol("U3Si2-Al: yogunluk sorulmuyor, gozeneklilik soruluyor",
            "yogunluk" not in f.alanlar and "gozeneklilik" in f.alanlar)
    kontrol("varsayilanda uyari yok, yogunluk ~6.73",
            not f.uyari.isVisibleTo(f) and abs(f.malzeme()["yogunluk"]["deger"] - 6.7316) < 1e-3)
    f.alanlar["u_yukleme"].setValue(9.0)
    f.alanlar["gozeneklilik"].setValue(0.3)
    kontrol("Al'a yer kalmayan yuklemede uyari gorunur",
            f.uyari.isVisibleTo(f) and "alüminyuma yer" in f.uyari.text(), "-> %s" % f.uyari.text())
    kontrol("kurulamayan parametrede uretim_sorunu dolu", bool(f.uretim_sorunu()))
    d = sm.KutuphaneDiyalog()
    d.sec("u3si2_al")
    kontrol("diyalog: gecerli U3Si2-Al'da Ekle acik", d.d_tamam.isEnabled())
    d.form.alanlar["u_yukleme"].setValue(9.0)
    d.form.alanlar["gozeneklilik"].setValue(0.3)
    kontrol("diyalog: kurulamayan degerde Ekle kapali, ozet nedeni soyluyor",
            not d.d_tamam.isEnabled() and "kurulamıyor" in d.ozet.text(), "-> %s" % d.ozet.text())
    f = sm.ParametreFormu("zirkaloy4")
    kontrol("Zircaloy-4: yalnizca yogunluk + sicaklik",
            sorted(f.alanlar) == ["sicaklik", "yogunluk"])


# ----------------------------------------------------------------------------
# [M3] parametrik malzeme
# ----------------------------------------------------------------------------

def _sekme(spec):
    from arayuz import sekme_malzeme as sm
    t = sm.MalzemeSekmesi()
    t.spec_yukle(spec)
    t._yayilan = []
    t.degisti.connect(t._yayilan.append)
    return t


def _kanca(sekme, islem):
    """Sekmenin bir sonraki diyalogunu 'islem(d)' ile doldurup kabul eder."""
    def calistir(d):
        sekme._son_diyalog = d
        return islem(d) is not False
    sekme._diyalog_calistir = calistir


def test_parametrik_malzeme():
    print("\n[M3] PARAMETRIK MALZEME: kutup kaydi, ayni form, yeniden uretim")
    _qt()
    from cekirdek import malzeme_kutup as mk, sema
    from arayuz import sekme_malzeme as sm

    spec = sema.yeni_spec("t")
    t = _sekme(spec)

    def su_ekle(d):
        d.sec("su")
        d.form.alanlar["sicaklik"].setValue(580.0)
        d.form.alanlar["bor_ppm"].setValue(1300.0)
    _kanca(t, su_ekle)
    t._kutuphaneden()
    m = sema.malzeme_bul(spec, "su")
    kontrol("kutuphaneden su eklendi", m is not None and t._yayilan == ["malzeme"])
    kontrol("spec'te uretim parametreleri: kutup={anahtar: su, param: {sicaklik: 580, bor_ppm: 1300}}",
            m and m.get("kutup") == {"anahtar": "su",
                                     "param": {"sicaklik": 580.0, "bor_ppm": 1300.0}},
            "-> %s" % (m or {}).get("kutup"))
    kontrol("yogunluk 580 K doymus su tablosundan (0.6965)",
            m["yogunluk"]["deger"] == mk.su_yogunluk(580.0))
    rho580, ad580 = m["yogunluk"]["deger"], m["gorunen_ad"]

    # Duzenle -> AYNI parametre formu
    t.tablo.selectRow(0)
    d = sm.MalzemeDiyalog(m, spec)
    kontrol("Duzenle parametrik kipte acilir (parametre formu gorunur, bilesim tablosu yok)",
            d.parametrik_kip() and d.param_sayfa.isVisibleTo(d)
            and not d.elle_sayfa.isVisibleTo(d))
    kontrol("form ayni parametreleri tasir (580 K, 1300 ppm)",
            d.form.alanlar["sicaklik"].value() == 580.0
            and d.form.alanlar["bor_ppm"].value() == 1300.0)
    kontrol("ham bilesim Gelismis'te ve salt okunur",
            d.gelismis.icerik.isAncestorOf(d.ham_tablo) and d.ham_model.salt_okunur)

    def ısıt(d):
        d.form.alanlar["sicaklik"].setValue(600.0)
    _kanca(t, ısıt)
    t._duzenle()
    m = sema.malzeme_bul(spec, "su")
    beklenen = mk.su(sicaklik=600.0, bor_ppm=1300.0)
    kontrol("su 580 -> 600 K: yogunluk yeniden uretildi (%.4f -> %.4f)"
            % (rho580, m["yogunluk"]["deger"]),
            m["yogunluk"]["deger"] == mk.su_yogunluk(600.0) != rho580)
    kontrol("su 580 -> 600 K: sicaklik 600", m["sicaklik"] == 600.0)
    kontrol("su 580 -> 600 K: aciklama yeniden uretildi ('%s' -> '%s')"
            % (ad580, m["gorunen_ad"]),
            m["gorunen_ad"] == beklenen["gorunen_ad"] != ad580)
    kontrol("su 580 -> 600 K: bilesim ve S(a,b) kutuphaneyle ayni",
            m["bilesim"] == beklenen["bilesim"] and m["sab"] == ["c_H_in_H2O"])
    kontrol("su 580 -> 600 K: kutup parametresi guncel, ad ayni",
            m["kutup"]["param"]["sicaklik"] == 600.0 and m["ad"] == "su")

    # UO2 zenginlik
    def uo2_ekle(d):
        d.sec("uo2")
    _kanca(t, uo2_ekle)
    t._kutuphaneden()
    u = sema.malzeme_bul(spec, "uo2")
    kontrol("UO2 eklendi: 'UO2 %3.20'", u and u["gorunen_ad"] == "UO2 %3.20")
    t.tablo.selectRow([x["ad"] for x in spec["malzemeler"]].index("uo2"))

    def zenginlestir(d):
        d.form.alanlar["zenginlik"].setValue(4.5)
    _kanca(t, zenginlestir)
    t._duzenle()
    u = sema.malzeme_bul(spec, "uo2")
    kontrol("UO2 %3.20 -> %4.50: aciklama 'UO2 %4.50'", u["gorunen_ad"] == "UO2 %4.50",
            "-> %s" % u["gorunen_ad"])
    kontrol("UO2 %4.50: U satirinda zenginlik 4.5",
            [b.get("zenginlik") for b in u["bilesim"] if b["isim"] == "U"] == [4.5])

    # bit bit ayni yeniden uretim + dokunmadan Tamam
    kirik, kayan = [], []
    for k in mk.KUTUPHANE:
        for param in (mk.varsayilan_parametreler(k), None):
            if param is None:
                # spinbox ondaligindan fazla basamakli degerler
                param = {a: (v * 1.0001234567 if isinstance(v, float) else v)
                         for a, v in mk.varsayilan_parametreler(k).items()}
            m = json.loads(_j(mk.parametrik_uret(k, param)))
            m["ad"] = k
            y = mk.yeniden_uret(m)
            if not mk.parametrik_mi(m) or any(_j(y[a]) != _j(m[a]) for a in mk.FIZIK_ALANLARI):
                kirik.append(k)
            s = sema.yeni_spec()
            s["malzemeler"] = [m]
            d = sm.MalzemeDiyalog(m, s)
            if _j(d.sonuc()) != _j(m):
                kayan.append(k)
    kontrol("21 kutuphane malzemesi: ayni parametrelerle yeniden uretim bit bit ayni "
            "(JSON gidis-donus dahil)", not kirik, "%s" % kirik)
    kontrol("21 malzeme: Duzenle + dokunmadan Tamam malzemeyi bit bit korur "
            "(fazla basamakli degerler dahil)", not kayan, "%s" % kayan)

    # elle degistirilmis (bayat) kutup kaydi -> bilesim tablosu
    b = json.loads(_j(mk.parametrik_uret("su", {"sicaklik": 580.0})))
    b["ad"] = "su"
    b["yogunluk"]["deger"] = 0.7
    kontrol("parametre formu disinda degisen malzeme parametrik sayilmaz",
            not mk.parametrik_mi(b))
    s = sema.yeni_spec()
    s["malzemeler"] = [b]
    d = sm.MalzemeDiyalog(b, s)
    kontrol("bayat kutup: bilesim tablosuyla acilir + not gorunur",
            not d.parametrik_kip() and d.elle_sayfa.isVisibleTo(d)
            and d.kopuk_not.isVisibleTo(d))
    kontrol("bayat kutup: yogunluk EZILMEZ (0.7 kalir), kayit dusurulur",
            d.sonuc()["yogunluk"]["deger"] == 0.7 and "kutup" not in d.sonuc())
    # kutuphaneden ayirma
    u = mk.parametrik_uret("uo2", {"zenginlik": 4.95})
    u["ad"] = "uo2"
    s["malzemeler"] = [u]
    d = sm.MalzemeDiyalog(u, s)
    d.elle_duzenlemeye_gec()
    r = d.sonuc()
    kontrol("'Bileşimi elle düzenle': tabloya gecer, kutup duser, bilesim ayni",
            not d.parametrik_kip() and "kutup" not in r and r["bilesim"] == u["bilesim"]
            and r["yogunluk"] == u["yogunluk"] and r["gorunen_ad"] == "UO2 %4.95")
    # eski / elle malzeme -> bugunku gibi bilesim tablosu
    p = _yukle("pwr_17x17")
    d = sm.MalzemeDiyalog(sema.malzeme_bul(p, "su"), p)
    kontrol("kutup'suz eski malzeme bilesim tablosuyla duzenlenir",
            not d.parametrik_kip() and d.model.rowCount() == 3)
    kontrol("eski malzeme: dokunmadan Tamam birebir ayni",
            _j(d.sonuc()) == _j(sema.malzeme_bul(p, "su")))
    he = sema.malzeme_bul(p, "helyum")
    d = sm.MalzemeDiyalog(he, p)
    kontrol("helyum 0.0001785 g/cm3 yuvarlanmaz (eski spinbox 0.000179 yapiyordu)",
            d.sonuc()["yogunluk"]["deger"] == 0.0001785)


# ----------------------------------------------------------------------------
# [M4] kurucu / kod_uret kutup'u yok sayar
# ----------------------------------------------------------------------------

def _malzeme_imzasi(model):
    return [(m.name, m.density, m.density_units, m.temperature,
             sorted((n.name, round(n.percent, 12), n.percent_type) for n in m.nuclides),
             sorted(m._sab)) for m in model.materials]


def test_kutup_yok_sayilir():
    print("\n[M4] kurucu ve kod_uret 'kutup' anahtarini yok sayar")
    from cekirdek import kurucu, kod_uret, dogrula, malzeme_kutup as mk
    for ad in ("pwr_pinhucre", "sfr_altigen"):
        s = _yukle(ad)
        s2 = copy.deepcopy(s)
        for m in s2["malzemeler"]:
            # bilerek TUTARSIZ bir kayit: okunsaydi model degisirdi
            m["kutup"] = {"anahtar": "uo2", "param": {"zenginlik": 90.0}}
        m1, _ = kurucu.kur(s)
        m2, _ = kurucu.kur(s2)
        kontrol("%s: kurucu ayni malzemeleri kurar" % ad,
                _malzeme_imzasi(m1) == _malzeme_imzasi(m2))
        k1 = kod_uret.uret(s)
        k2 = kod_uret.uret(s2)
        kontrol("%s: kod_uret ayni betigi uretir" % ad, k1 == k2 and "kutup" not in k2)
        b1 = [str(b) for b in dogrula.tum_kontroller(s, veri_kontrolu=False)]
        b2 = [str(b) for b in dogrula.tum_kontroller(s2, veri_kontrolu=False)]
        kontrol("%s: dogrula ayni bulgular" % ad, b1 == b2)
    # tamamen parametrik bir model kurulur ve betigi uretilir
    s = _yukle("pwr_pinhucre")
    yeni = {"uo2": mk.parametrik_uret("uo2", {"zenginlik": 3.0}),
            "zirkaloy": mk.parametrik_uret("zirkaloy4", {}),
            "su": mk.parametrik_uret("su", {"sicaklik": 565.0, "bor_ppm": 600.0})}
    for ad, m in yeni.items():
        m["ad"] = ad
    s["malzemeler"] = list(yeni.values())
    try:
        kurucu.kur(s)
        kod_uret.uret(s)
        tamam = not dogrula.hata_var(dogrula.tum_kontroller(s, veri_kontrolu=False))
    except Exception as e:
        tamam = False
        print("   ", e)
    kontrol("parametrik malzemeli pin hucre kurulur, betik uretilir, hata yok", tamam)


# ----------------------------------------------------------------------------
# [M5] bilesim tablosu
# ----------------------------------------------------------------------------

def test_bilesim_tablosu():
    print("\n[M5] BILESIM TABLOSU: zenginlik yalnizca U elementinde, acilir listeler")
    _qt()
    from PySide6 import QtCore, QtWidgets
    from arayuz import sekme_malzeme as sm
    B = sm.BilesimModeli
    model = B([{"tur": "element", "isim": "U", "miktar": 1.0, "birim": "ao", "zenginlik": 3.2},
               {"tur": "element", "isim": "O", "miktar": 2.0, "birim": "ao"},
               {"tur": "nuklid", "isim": "U235", "miktar": 0.01, "birim": "ao"},
               {"tur": "element", "isim": "B", "miktar": 0.1, "birim": "wo"}])
    ix = lambda r, c: model.index(r, c)
    duz = lambda r: bool(model.flags(ix(r, B.S_ZENG)) & QtCore.Qt.ItemIsEditable)
    etkin = lambda r: bool(model.flags(ix(r, B.S_ZENG)) & QtCore.Qt.ItemIsEnabled)
    kontrol("zenginlik: U element satirinda duzenlenebilir", duz(0) and etkin(0))
    kontrol("zenginlik: O / U235 nuklid / B satirlarinda duzenlenemez ve gri",
            not any(duz(r) or etkin(r) for r in (1, 2, 3)))
    kontrol("zenginlik hucresi O satirinda bos", model.data(ix(1, B.S_ZENG)) == "")
    kontrol("O satirina zenginlik yazilamaz",
            not model.setData(ix(1, B.S_ZENG), "3.0") and "zenginlik" not in model.bilesim[1])
    kontrol("tur/birim okunur gosterilir: 'Doğal element' / 'Atom oranı' / 'İzotop (nüklid)' / 'Ağırlık oranı'",
            [model.data(ix(0, B.S_TUR)), model.data(ix(0, B.S_BIRIM)),
             model.data(ix(2, B.S_TUR)), model.data(ix(3, B.S_BIRIM))]
            == ["Doğal element", "Atom oranı", "İzotop (nüklid)", "Ağırlık oranı"])

    t = sm._bilesim_tablosu(model)
    sec = QtWidgets.QStyleOptionViewItem()
    for sutun, beklenen in ((B.S_TUR, [("Doğal element", "element"), ("İzotop (nüklid)", "nuklid")]),
                            (B.S_BIRIM, [("Atom oranı", "ao"), ("Ağırlık oranı", "wo")])):
        dlg = t.itemDelegateForColumn(sutun)
        ed = dlg.createEditor(t.viewport(), sec, ix(1, sutun))
        ogeler = [(ed.itemText(i), ed.itemData(i)) for i in range(ed.count())]
        kontrol("'%s' serbest metin degil acilir liste: %s" % (B.BASLIKLAR[sutun], ogeler),
                isinstance(ed, QtWidgets.QComboBox) and ogeler == beklenen)
        dlg.setEditorData(ed, ix(1, sutun))
        ed.setCurrentIndex(1)
        dlg.setModelData(ed, model, ix(1, sutun))
    kontrol("acilir listeden secim spec'e AYNEN yazilir (nuklid / wo)",
            model.bilesim[1]["tur"] == "nuklid" and model.bilesim[1]["birim"] == "wo")
    kontrol("isim yazimi duzelir: 'zr' -> 'Zr', nuklid 'u238' -> 'U238'",
            model.setData(ix(3, B.S_ISIM), "zr") and model.bilesim[3]["isim"] == "Zr"
            and model.setData(ix(1, B.S_ISIM), "u238") and model.bilesim[1]["isim"] == "U238")
    model.setData(ix(0, B.S_TUR), "nuklid")
    kontrol("U satiri nuklide cevrilince gecersiz zenginlik duser",
            "zenginlik" not in model.bilesim[0] and not duz(0))
    model.setData(ix(0, B.S_TUR), "element")
    kontrol("U element satirinda bos zenginlik 'doğal' gosterilir",
            model.data(ix(0, B.S_ZENG)) == "doğal" and duz(0))
    model.setData(ix(0, B.S_ZENG), "4.95")
    kontrol("U zenginligi yazilir", model.bilesim[0].get("zenginlik") == 4.95)
    eski = B([{"tur": "element", "isim": "O", "miktar": 2.0, "birim": "ao", "zenginlik": 3.0}])
    kontrol("eski dosyadaki gecersiz zenginlik (O'da) silinebilir, degistirilemez",
            bool(eski.flags(eski.index(0, B.S_ZENG)) & QtCore.Qt.ItemIsEditable)
            and not eski.setData(eski.index(0, B.S_ZENG), "4.0")
            and eski.setData(eski.index(0, B.S_ZENG), "") and "zenginlik" not in eski.bilesim[0])


# ----------------------------------------------------------------------------
# [M6] Gelismis + tek ad + S(a,b)
# ----------------------------------------------------------------------------

def test_gelismis_ve_sab():
    print("\n[M6] GELISMIS, TEK AD ALANI, S(a,b) ONERISI")
    _qt()
    from cekirdek import malzeme_kutup as mk, sema, dogrula
    from arayuz import sekme_malzeme as sm

    p = _yukle("pwr_17x17")
    d = sm.MalzemeDiyalog(sema.malzeme_bul(p, "uo2"), p)
    etiketler = [e for e in _dogal_metinler(d)]
    kontrol("tek ad alani: 'Ad:' var, 'Görünen ad' yok",
            etiketler.count("Ad:") == 1 and not any("örünen" in e or "orunen" in e
                                                     for e in etiketler))
    g = d.gelismis.icerik
    kontrol("Gelismis varsayilan kapali", not d.gelismis.acik_mi() and not g.isVisibleTo(d))
    kontrol("renk, yogunluk birimi ve serbest S(a,b) Gelismis'te",
            all(g.isAncestorOf(w) for w in (d.renk, d.birim, d.sab_elle)))
    kontrol("elle malzemede bilesim tablosu ANA alanda",
            not g.isAncestorOf(d.tablo) and d.tablo.isVisibleTo(d))
    kontrol("yogunluk birimleri: g/cm³, atom/b-cm, kg/m³ (spec: g/cm3, atom/b-cm, kg/m3)",
            [(d.birim.itemText(i), d.birim.itemData(i)) for i in range(d.birim.count())]
            == [("g/cm³", "g/cm3"), ("atom/b-cm", "atom/b-cm"), ("kg/m³", "kg/m3")])
    kontrol("UO2 (elle): S(a,b) satiri gizli (uygun kural yok)",
            not d.elle_form.isRowVisible(d.sab_kutu))
    d = sm.MalzemeDiyalog(sema.malzeme_bul(p, "su"), p)
    kontrol("borlu su (elle): S(a,b) listesi gorunur, c_H_in_H2O secili",
            d.elle_form.isRowVisible(d.sab_kutu) and d.sab_kutu.currentData() == ["c_H_in_H2O"]
            and d.sab_kutu.itemData(0) == ["c_H_in_H2O"])
    kontrol("S(a,b) listesinin son secenegi 'Yok'",
            d.sab_kutu.itemData(d.sab_kutu.count() - 1) == [])
    d.sab_kutu.setCurrentIndex(d.sab_kutu.count() - 1)
    d._sab_secildi(d.sab_kutu.count() - 1)
    kontrol("'Yok' secilince spec'e sab=[] yazilir", d.sonuc()["sab"] == [])
    d = sm.MalzemeDiyalog(sema.malzeme_bul(p, "zirkaloy4"), p)
    kontrol("Zircaloy (elle): S(a,b) satiri gizli", not d.elle_form.isRowVisible(d.sab_kutu))
    # parametrik malzemede ham tablo Gelismis'te, param formu ana alanda
    m = mk.parametrik_uret("uo2", {})
    m["ad"] = "uo2"
    d = sm.MalzemeDiyalog(m, p)
    kontrol("parametrik: ham bilesim Gelismis'te, yogunluk birimi/serbest S(a,b) gizli",
            d.gelismis.icerik.isAncestorOf(d.ham_tablo) and not d.birim.isVisibleTo(d)
            and not d.sab_elle.isVisibleTo(d) and not d.gelismis.icerik.isAncestorOf(d.form))

    # oneriler dogrula kurallariyla ayni
    celiski = []
    for k in mk.KUTUPHANE:
        m = mk.uret(k)
        m["sab"] = []
        uyari = [b for b in dogrula._sab_kontrol(m, "t") if "S(α,β) olarak " in (b.oneri or "")]
        oneriler = sm.sab_onerileri(m)
        dogrula_der = re.findall(r"S\(α,β\) olarak (\S+) ekleyin", uyari[0].oneri)[0] if uyari else None
        bizim = oneriler[0][0] if oneriler else None
        if dogrula_der != bizim:
            celiski.append((k, dogrula_der, bizim))
    kontrol("21 malzemede S(a,b) onerisi = dogrula'nin onerdigi tablo", not celiski,
            "%s" % celiski)
    kontrol("hidrojen GAZI icin S(a,b) onerilmez",
            not sm.sab_onerileri(sema.malzeme("h2", [sema.bilesen("H", 2.0)], 8.9e-5)))

    # yeni elle malzeme: bilesim su gorunumune gelince oneri kendiliginden secilir
    s = sema.yeni_spec()
    yeni = sema.malzeme("malzeme", [], 1.0)
    d = sm.MalzemeDiyalog(yeni, s, yeni=True)
    kontrol("yeni elle malzeme bos bir bilesim satiriyla acilir", d.model.rowCount() == 1)
    B = sm.BilesimModeli
    d.model.setData(d.model.index(0, B.S_ISIM), "H")
    d.model.setData(d.model.index(0, B.S_MIKTAR), "2")
    d.model.satir_ekle()
    d.model.setData(d.model.index(1, B.S_ISIM), "O")
    kontrol("H2O yazilinca c_H_in_H2O kendiliginden secilir", d.sonuc()["sab"] == ["c_H_in_H2O"])
    kontrol("yeni elle malzemede 'bilesim tanindi: sogutucu, moderator'",
            "soğutucu" in d.ozet.text() and "moderatör" in d.ozet.text())
    # var olan su'da sab=[] ise acilis onu DEGISTIRMEZ
    w = copy.deepcopy(sema.malzeme_bul(p, "su"))
    w["sab"] = []
    d = sm.MalzemeDiyalog(w, p)
    kontrol("var olan malzemenin bos S(a,b)'si sessizce degistirilmez", d.sonuc()["sab"] == [])
    # bos bilesim / bos isim kaydi engeller
    d = sm.MalzemeDiyalog(sema.malzeme("x", [], 1.0), s, yeni=True)
    kontrol("isimsiz bilesim satiri kaydi engeller", d.icerik_sorunu() is not None)


# ----------------------------------------------------------------------------
# [M7] sekme dugmeleri ve bos durum
# ----------------------------------------------------------------------------

def test_sekme_dugmeleri():
    print("\n[M7] SEKME: dugme etkinligi, bos durum, kopyala/sil")
    _qt()
    from cekirdek import sema, malzeme_kutup as mk
    from arayuz import sekme_malzeme as sm
    from arayuz.ortak import BosDurum

    bos = _sekme(sema.yeni_spec("bos"))
    kontrol("bos listede BosDurum gorunur, tablo gizli",
            bos.yigin.currentIndex() == 0 and isinstance(bos.bos, BosDurum)
            and bos.yigin.currentWidget().isAncestorOf(bos.bos))
    kontrol("BosDurum: 'Henüz malzeme yok' + 'Kütüphaneden ekle…'",
            bos.bos.baslik.text() == "Henüz malzeme yok"
            and bos.bos.dugme.text() == "Kütüphaneden ekle…")
    acilan = []
    _kanca(bos, lambda d: (acilan.append(type(d).__name__), False)[1])
    bos.bos.dugme.click()
    kontrol("BosDurum dugmesi kutuphane diyalogunu acar", acilan == ["KutuphaneDiyalog"])
    bos.d_bos_elle.click()
    kontrol("'ya da bileşimi elle tanımlayın' elle diyalogunu acar",
            acilan == ["KutuphaneDiyalog", "MalzemeDiyalog"])

    p = _yukle("pwr_17x17")
    t = _sekme(p)
    dugmeler = (t.d_duzenle, t.d_kopya, t.d_sil)
    kontrol("dolu listede tablo gorunur", t.yigin.currentIndex() == 1)
    kontrol("secim yokken Duzenle/Kopyala/Sil pasif", not any(d.isEnabled() for d in dugmeler))
    t.tablo.selectRow(1)
    kontrol("satir secilince uc dugme etkin", all(d.isEnabled() for d in dugmeler))
    t.tablo.clearSelection()
    kontrol("secim kalkinca yine pasif", not any(d.isEnabled() for d in dugmeler))
    kontrol("tablo basliklari Turkce",
            [t.tablo.horizontalHeaderItem(i).text() for i in range(t.tablo.columnCount())]
            == ["Renk", "Ad", "Açıklama", "Rol", "Yoğunluk", "Sıcaklık", "S(α,β)", "Bileşim"])
    kontrol("Rol sutunu uygunluk'tan: su -> 'soğutucu, moderatör'",
            t.tablo.item(3, 3).text() == "soğutucu, moderatör")
    kontrol("Sicaklik K ve °C: '580.0 K (306.9 °C)'", t.tablo.item(3, 5).text() == "580.0 K (306.9 °C)")

    # kopyala: kutup korunur, ad benzersiz
    m = mk.parametrik_uret("uo2", {"zenginlik": 4.5})
    m["ad"] = "uo2_b"
    p["malzemeler"].append(m)
    t.spec_yukle(p)
    t.tablo.selectRow(4)
    t._kopyala()
    k = p["malzemeler"][-1]
    kontrol("Kopyala: 'uo2_b_2', kutup kaydi korunur, kopya secili",
            k["ad"] == "uo2_b_2" and k.get("kutup") == m["kutup"]
            and t._secili_satir() == len(p["malzemeler"]) - 1)
    # sil: kullanilan malzeme icin soru, referans sayisi
    sorular = []
    t._soru = lambda b, metin: (sorular.append(metin), False)[1]
    t.tablo.selectRow(3)
    n = len(p["malzemeler"])
    t._sil()
    kontrol("kullanilan 'su' silinmek istenince soru sorulur (5 yer), hayir -> silinmez",
            len(sorular) == 1 and "5 yerde" in sorular[0] and len(p["malzemeler"]) == n,
            "-> %s" % sorular[:1])
    kontrol("silme sorusu okunur yer adlariyla (ham spec yolu yok)",
            "çubuğunun 4. bölgesi" in sorular[0] and "/" not in sorular[0])
    ham = []
    for f in glob.glob(os.path.join(ORNEK, "*.json")):
        s_ = sema.yukle(f)
        for m_ in s_["malzemeler"]:
            ham += [y for y in sema.malzeme_referanslari(s_, m_["ad"])
                    if "/" in sm.yol_okunur(y)]
    for y in ("kor/anahtar/w", "kor/eksenel/2/anahtar/w", "demetler/d/anahtar/w",
              "tukenme/ek_malzemeler/0", "kor/dolgu"):
        if "/" in sm.yol_okunur(y):
            ham.append(y)
    kontrol("butun referans yollari okunur Turkceye cevrilir", not ham, "%s" % ham[:5])
    kontrol("demet kilifi yolu okunur: 'tvs' demetinin kilifi",
            sm.yol_okunur("demetler/tvs/kilif") == "‘tvs’ demetinin kılıfı",
            "-> %r" % sm.yol_okunur("demetler/tvs/kilif"))
    t.tablo.selectRow(n - 1)
    t._sil()
    kontrol("kullanilmayan kopya sorusuz silinir",
            len(sorular) == 1 and len(p["malzemeler"]) == n - 1)
    kontrol("silinince secim ve dugmeler temizlenir",
            t._secili_satir() == -1 and not t.d_sil.isEnabled())


# ----------------------------------------------------------------------------
# [M8] ad degisimi -- 11 ornek
# ----------------------------------------------------------------------------

def _hucre_eslemesi(spec):
    """{hucre_id: dolgu} -- malzeme dolgusu spec ADIYLA."""
    from cekirdek import kurucu
    model, bilgi = kurucu.kur(spec)
    ters = {id(m): ad for ad, m in bilgi["malzemeler"].items()}
    esleme = {}
    for cid, h in model.geometry.get_all_cells().items():
        f = h.fill
        if f is None:
            esleme[cid] = None
        elif id(f) in ters:
            esleme[cid] = "M:" + ters[id(f)]
        else:
            esleme[cid] = "%s:%s" % (type(f).__name__, f.id)
    malzemeler = [ters[id(m)] for m in model.materials]
    return esleme, malzemeler


def _bulgular(spec, degis=None):
    from cekirdek import dogrula
    cikti = []
    for b in dogrula.tum_kontroller(spec, veri_kontrolu=False):
        s = "%s|%s|%s|%s" % (b.seviye, b.yer, b.mesaj, b.oneri)
        if degis:
            s = s.replace(degis[1], degis[0])
        cikti.append(s)
    return sorted(cikti)


def _dizeler(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from _dizeler(v)
    elif isinstance(x, list):
        for v in x:
            yield from _dizeler(v)
    elif isinstance(x, str):
        yield x


def _ad_degisimi_olc(spec, eski, yeni, baslik):
    """Ad degisimi modeli degistirmiyor mu? (kurulum + dogrula + artik referans)"""
    from cekirdek import sema
    e0, mz0 = _hucre_eslemesi(spec)
    b0 = _bulgular(spec)
    s2 = copy.deepcopy(spec)
    try:
        sema.malzeme_adini_degistir(s2, eski, yeni)
        e1, mz1 = _hucre_eslemesi(s2)
    except Exception as ex:
        return "%s: %s" % (baslik, ex)
    beklenen = {k: ("M:" + yeni if v == "M:" + eski else v) for k, v in e0.items()}
    if e1 != beklenen:
        return "%s: hucre eslemesi farkli" % baslik
    if mz1 != [yeni if a == eski else a for a in mz0]:
        return "%s: malzeme listesi farkli" % baslik
    if _bulgular(s2, (eski, yeni)) != b0:
        return "%s: dogrula bulgulari farkli" % baslik
    # golgeleme (sema.malzeme_adini_degistir): ayni adli cubuk/plaka/demet genel
    # alanda (demet haritasi anahtari, guc hedefi) KAZANIR ve ad dizesi o ogenin
    # adi olarak kalir (pwr_mox_demet: malzeme 'mox_25' + cubuk 'mox_25').
    golgeli = any(x.get("ad") == eski for bolum in ("cubuklar", "plakalar", "demetler")
                  for x in s2.get(bolum) or [])
    if eski in set(_dizeler(s2)) and not golgeli:
        return "%s: eski ad spec'te kaldi" % baslik
    return None


def test_ad_degisimi_ornekler(gecici=None):
    print("\n[M8] AD DEGISIMI: butun ornekte her malzeme yeni ada")
    from cekirdek import sema
    dosyalar = sorted(glob.glob(os.path.join(ORNEK, "*.json")))
    kontrol("butun ornekler bulundu (>= 27)", len(dosyalar) >= 27, "(%d)" % len(dosyalar))
    toplam = 0
    for f in dosyalar:
        spec = sema.yukle(f)
        sorunlar = []
        for i, m in enumerate(spec["malzemeler"]):
            sorun = _ad_degisimi_olc(spec, m["ad"], "Yeni Ad %d ç" % i, m["ad"])
            toplam += 1
            if sorun:
                sorunlar.append(sorun)
        kontrol("%s: %d malzemenin her biri yeniden adlandirildi, model ayni kuruldu, "
                "dogrula ayni" % (os.path.basename(f), len(spec["malzemeler"])),
                not sorunlar, "%s" % sorunlar)
    kontrol("toplam %d ad degisimi olculdu" % toplam, toplam >= 35)


def test_ad_degisimi_genel_alanlar():
    print("\n[M8b] AD DEGISIMI: genel ad alanlari, golgeleme, cakisma")
    from cekirdek import sema, dogrula

    # (a) demet anahtarinda malzeme harfi (su deligi)
    s = _yukle("pwr_17x17")
    d = s["demetler"][0]
    d["anahtar"]["w"] = "su"
    d["harita"][0] = "w" + d["harita"][0][1:]
    kontrol("demet harita anahtari -> malzeme", _ad_degisimi_olc(s, "su", "suyeni", "demet") is None,
            "%s" % _ad_degisimi_olc(s, "su", "suyeni", "demet"))

    # (b) kare_kafes: kor anahtari + eksenel katman dolgusu + katman anahtari
    s = _yukle("pwr_17x17")
    s["kor"].update(tur="kare_kafes", adim=21.42, boyut=[2, 1], harita=["dw"],
                    anahtar={"d": "demet_17x17", "w": "su"})
    s["kor"]["eksenel"] = {"var": True, "bolgeler": [
        sema.eksenel_bolge("alt", 10.0, dolgu="su"),
        sema.eksenel_bolge("orta", 20.0),
        sema.eksenel_bolge("ust", 10.0, anahtar={"w": "zirkaloy4"})]}
    s["kor"]["sinir"] = {"yan": "reflective", "alt": "vacuum", "ust": "vacuum"}
    kontrol("kurgu gecerli (kurulur, hata yok)",
            not dogrula.hata_var(dogrula.tum_kontroller(s, veri_kontrolu=False)))
    for eski in ("su", "zirkaloy4"):
        sorun = _ad_degisimi_olc(s, eski, eski + "_yeni", "kor")
        kontrol("kor anahtari / katman dolgusu / katman anahtari: '%s'" % eski,
                sorun is None, "%s" % sorun)
    s2 = copy.deepcopy(s)
    yollar = sema.malzeme_adini_degistir(s2, "su", "su_yeni")
    kontrol("donen yollar genel alanlari icerir",
            {"kor/anahtar/w", "kor/eksenel/0/dolgu"} <= set(yollar), "%s" % yollar)

    # (c) tukenme ek malzemeleri
    s = _yukle("pwr_tukenme")
    s["tukenme"]["ek_malzemeler"] = ["zirkaloy"]
    sema.malzeme_adini_degistir(s, "zirkaloy", "zarf")
    kontrol("tukenme ek_malzemeler guncellenir", s["tukenme"]["ek_malzemeler"] == ["zarf"])

    # (d) golgeleme: ayni adli cubuk genel alanda KAZANIR -- dokunulmaz
    s = _yukle("pwr_17x17")
    kopya = copy.deepcopy(sema.malzeme_bul(s, "su"))
    kopya["ad"] = "yakit_cubugu"
    s["malzemeler"].append(kopya)
    harf = [h for h, v in s["demetler"][0]["anahtar"].items() if v == "yakit_cubugu"][0]
    sorun = _ad_degisimi_olc(s, "yakit_cubugu", "eski_su", "golge")
    s2 = copy.deepcopy(s)
    sema.malzeme_adini_degistir(s2, "yakit_cubugu", "eski_su")
    kontrol("cubukla ayni adli malzeme yeniden adlandirilinca demet anahtari cubugu gostermeye devam eder",
            s2["demetler"][0]["anahtar"][harf] == "yakit_cubugu"
            and sema.malzeme_bul(s2, "eski_su") is not None
            and (sorun is None or "eski ad" in sorun), "%s" % sorun)

    # (e) cakisma ve gecersiz adlar
    s = _yukle("pwr_17x17")
    for yeni, neden in (("uo2", "var olan malzeme"), ("yakit_cubugu", "cubuk adi"),
                        ("demet_17x17", "demet adi"), ("bosluk", "ayrilmis ad"),
                        ("", "bos"), (" su2", "bosluk ile baslayan")):
        try:
            sema.malzeme_adini_degistir(s, "su", yeni)
            olmadi = False
        except ValueError:
            olmadi = True
        kontrol("'su' -> %r reddedilir (%s)" % (yeni, neden),
                olmadi and sema.malzeme_bul(s, "su") is not None)
    try:
        sema.malzeme_adini_degistir(s, "yok_boyle", "x")
        hata = False
    except KeyError:
        hata = True
    kontrol("tanimsiz malzeme KeyError", hata)
    kontrol("ad degismiyorsa her zaman gecerli (eski dosyadaki cakisma kilitlemez)",
            sema.malzeme_adi_sorunu(s, "su", haric="su") is None)
    kontrol("malzeme_etiketi: 'su — H2O ...' ; aciklama adla ayniysa yalnizca ad",
            sema.malzeme_etiketi(sema.malzeme_bul(s, "su")) == "su — H2O 0.700 g/cm³ + 1300 ppm B"
            and sema.malzeme_etiketi({"ad": "yakit", "gorunen_ad": "yakit"}) == "yakit")
    kontrol("referans listesi spec'i degistirmez",
            len(sema.malzeme_referanslari(s, "su")) == 5 and sema.malzeme_bul(s, "su") is not None)


# ----------------------------------------------------------------------------
# [M9] uctan uca: sekmeden ad degisimi
# ----------------------------------------------------------------------------

def test_sekmeden_ad_degisimi():
    print("\n[M9] UCTAN UCA: Duzenle ile ad degisimi butun referanslari tasir")
    _qt()
    from cekirdek import sema, kurucu, dogrula
    for ornek, eski, yeni in (("pwr_kontrol", "su", "sogutucu"),
                              ("tamburlu_kor", "berilyum", "yansıtıcı Be"),
                              ("zirh_kure", "celik", "çelik")):
        s = _yukle(ornek)
        t = _sekme(s)
        t.tablo.selectRow([m["ad"] for m in s["malzemeler"]].index(eski))
        _kanca(t, lambda d, y=yeni: d.ad.setText(y))
        t._duzenle()
        tamam = True
        try:
            kurucu.kur(s)
        except Exception as e:
            tamam = False
            print("   ", e)
        kontrol("%s: '%s' -> '%s': model kurulur, eski ad hicbir yerde kalmaz, "
                "dogrula hata yok, secim korunur" % (ornek, eski, yeni),
                tamam and eski not in set(_dizeler(s))
                and not dogrula.hata_var(dogrula.tum_kontroller(s, veri_kontrolu=False))
                and t._secili_satir() >= 0
                and s["malzemeler"][t._secili_satir()]["ad"] == yeni
                and t._yayilan == ["malzeme"])
    # var olan ada cevirme diyalogda engellenir
    from arayuz import sekme_malzeme as sm
    s = _yukle("pwr_kontrol")
    d = sm.MalzemeDiyalog(sema.malzeme_bul(s, "su"), s)
    d.ad.setText("b4c")
    kontrol("diyalogda var olan ada cevirme: Tamam pasif, hata metni gorunur",
            not d.d_tamam.isEnabled() and d.ad_hata.isVisibleTo(d))
    d.ad.setText("su")
    kontrol("ad geri alininca Tamam etkin", d.d_tamam.isEnabled())


# ----------------------------------------------------------------------------
# [M10] Turkce metinler
# ----------------------------------------------------------------------------

_ASCII_TURKCE = re.compile(
    r"Duzenle|Kutuphane|kutuphane|Yogunluk|yogunluk|Sicaklik|sicaklik|Bilesim|"
    r"bilesim|Satir|Gorunen|Cozunmus|Agirlik|agirlik|orani\b|Bos malzeme|dogal\b|"
    r"\bTur\b|\bIsim\b|malzeme_kutup|\.py\b|S\(a,b\)")


def test_turkce_metinler():
    print("\n[M10] TURKCE METINLER")
    _qt()
    from cekirdek import sema, malzeme_kutup as mk
    from arayuz import sekme_malzeme as sm
    p = _yukle("pwr_17x17")
    m = mk.parametrik_uret("b4c", {})
    m["ad"] = "b4c"
    pencereler = {"sekme": _sekme(p), "bos sekme": _sekme(sema.yeni_spec()),
                  "kutuphane": sm.KutuphaneDiyalog(p),
                  "elle": sm.MalzemeDiyalog(sema.malzeme_bul(p, "su"), p),
                  "parametrik": sm.MalzemeDiyalog(m, p)}
    for ad, w in pencereler.items():
        kotu = [x for x in _dogal_metinler(w) if _ASCII_TURKCE.search(x)]
        kontrol("%s: ASCII'lestirilmis metin yok" % ad, not kotu, "%s" % kotu)
    b = sm.BilesimModeli([{"tur": "element", "isim": "U", "miktar": 1, "birim": "ao"}])
    kontrol("bilesim basliklari: Tür, İsim, Miktar, Birim, Zenginlik %",
            [b.headerData(i, __import__("PySide6").QtCore.Qt.Horizontal) for i in range(5)]
            == ["Tür", "İsim", "Miktar", "Birim", "Zenginlik %"])
    kontrol("B4C aciklamasi 'B4C (doğal)'", mk.b4c()["gorunen_ad"] == "B4C (doğal)")


HIZLI = [test_kutuphane_listesi, test_parametre_formlari, test_parametrik_malzeme,
         test_kutup_yok_sayilir, test_bilesim_tablosu, test_gelismis_ve_sab,
         test_sekme_dugmeleri, test_ad_degisimi_genel_alanlar,
         test_sekmeden_ad_degisimi, test_turkce_metinler]
YAVAS = [test_ad_degisimi_ornekler]


if __name__ == "__main__":
    from testler.ortak_test import _gecti, _kaldi
    for fn in HIZLI:
        fn()
    print("\n SONUC: %d gecti, %d kaldi" % (len(_gecti), len(_kaldi)))
    for t in _kaldi:
        print("   - %s" % t)
