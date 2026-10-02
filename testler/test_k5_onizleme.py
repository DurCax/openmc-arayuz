# -*- coding: utf-8 -*-
"""
 test_k5_onizleme.py  --  v3 K5: onizleme kapsami (basliksiz goruntu testleri)
                          ve Calistir kapisinin YALNIZ tam modele bakmasi

 Goruntu testleri iscinin gercek id haritasini okur: kapsamli cizimde
 beklenen malzemeler kesitte VAR, kapsam disi malzeme YOK; gosterge yalniz
 kesitteki malzemeleri listeler. Kapi: kapsamli cizim surerken ve basarisizken
 cizildi_mi() tam modelin sonucunu verir; tam model 'kontrol'u ayrica surulur.
"""

import copy
import os

import numpy as np

from testler.ortak_test import kontrol, ORNEK

_ZAMAN_ASIMI = 120.0


def _uyg():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _spec(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _gorunen(spec, adlar):
    return {m.get("gorunen_ad") or m["ad"] for m in spec["malzemeler"] if m["ad"] in adlar}


def _cizilen_malzemeler(w):
    """Son cizimin kesitlerinde GERCEKTEN bulunan malzemelerin gorunen adlari."""
    meta = w._kesit_onbellegi["meta"]
    harita = {int(i): g[0] for i, g in zip(meta["renkler"], meta["gosterge"])}
    var = set()
    for _b, geom in w._kesit_onbellegi["kesitler"].values():
        var |= {harita[int(m)] for m in np.unique(geom[..., 2]) if m >= 0}
    return var


class _Saglayici:
    """Pencere yerine sabit bir kapsam (sayfa + secim) veren saglayici."""

    def __init__(self, uret):
        self.uret = uret

    def __call__(self, spec):
        from arayuz.onizleme_kapsam import KapsamSonucu
        alt = self.uret(spec)
        return KapsamSonucu(alt, alt["ad"] if alt else "")


def _widget(spec, uret=None, istekler=None):
    _uyg()
    from arayuz.onizleme import OnizlemeWidget
    w = OnizlemeWidget()
    if istekler is not None:
        asil = w._istemci.iste
        w._istemci.iste = lambda istek: (istekler.append(copy.deepcopy(istek)), asil(istek))[1]
    if uret is not None:
        w.kapsam_saglayici_ayarla(_Saglayici(uret))
    w.spec_ayarla(spec)
    w._ciz()
    w.bekle(_ZAMAN_ASIMI)
    return w


def _kapsam_goruntusu(ad, uret, beklenen, disarida):
    spec = _spec(ad)
    w = _widget(spec, uret)
    try:
        var = _cizilen_malzemeler(w)
        kontrol("%s: kapsamli cizim, goruntu var" % ad, any(len(a.images) for a in w.figur.axes)
                and w.etkin_kapsam.spec is not None, "-> %s" % (w.son_hata() or "")[-200:])
        kontrol("%s: beklenen malzemeler kesitte" % ad, _gorunen(spec, beklenen) <= var,
                "-> %s" % var)
        kontrol("%s: kapsam disi malzeme yok" % ad, not var & _gorunen(spec, disarida),
                "-> %s" % var)
        gosterge = {g[0] for g in w._son_gosterge}
        kontrol("%s: gosterge yalniz kesitteki malzemeler" % ad, gosterge <= var,
                "-> %s" % gosterge)
        kontrol("%s: tam model denetlendi, kapi acik" % ad, w.cizildi_mi())
    finally:
        w.kapat()


def test_parcalar_pin_kapsami():
    print("\n[K5W-1] Parcalar: secili pin (3B ceyrek kor) -> yalniz pinin malzemeleri")
    from cekirdek import alt_model as am
    _kapsam_goruntusu("pwr_ceyrek_kor", lambda s: am.parca_alt_modeli(s, "cubuk", "yakit_24"),
                      {"uo2_24", "helyum", "zirkaloy4", "su"}, {"uo2_31"})


def test_demet_kapsami():
    print("\n[K5W-2] Demet: secili demet -> o demetin yakiti, diger demetin yakiti yok")
    from cekirdek import alt_model as am
    _kapsam_goruntusu("pwr_ceyrek_kor", lambda s: am.parca_alt_modeli(s, "demet", "demet_31"),
                      {"uo2_31", "zirkaloy4", "su"}, {"uo2_24"})


def test_plaka_ve_tambur_kapsami():
    print("\n[K5W-3] Parcalar: plaka (MTR kor) ve tambur (gelismis) kapsami")
    from cekirdek import alt_model as am
    _kapsam_goruntusu("mtr_kor", lambda s: am.parca_alt_modeli(s, "plaka", "mtr_eleman"),
                      {"u3si2_al", "al6061", "su"}, {"berilyum", "grafit"})
    _kapsam_goruntusu("kafes_tamburlu_yansitici",
                      lambda s: am.parca_alt_modeli(s, "tambur", "tambur_b4c"),
                      {"berilyum", "b4c"}, {"uo2_24", "uo2_31", "su"})


def test_geometri_dugum_kapsami():
    print("\n[K5W-4] Geometri (gelismis): secili kafes dugumu -> tamburlar ve yansitici yok")
    from cekirdek import alt_model as am
    _kapsam_goruntusu("kafes_tamburlu_yansitici",
                      lambda s: am.dugum_alt_modeli(s, ("kok", "ic")),
                      {"uo2_24", "uo2_31", "su"}, {"b4c"})


def test_tam_model_kipi_ve_kapsamsiz():
    print("\n[K5W-5] 'Tam model' kipi saglayiciyi yok sayar; tam kor iki yakiti da gosterir")
    from cekirdek import alt_model as am
    from arayuz.onizleme_kapsam import KAPSAM_TAM
    spec = _spec("pwr_ceyrek_kor")
    w = _widget(spec, lambda s: am.parca_alt_modeli(s, "cubuk", "yakit_24"))
    try:
        w.kapsam.setCurrentIndex(w.kapsam.findData(KAPSAM_TAM))
        w.bekle(_ZAMAN_ASIMI)
        var = _cizilen_malzemeler(w)
        kontrol("tam model: iki yakit da kesitte", _gorunen(spec, {"uo2_24", "uo2_31"}) <= var,
                "-> %s" % var)
        kontrol("tam model: etkin kapsam yok", w.etkin_kapsam.spec is None)
        kontrol("tam model: kapi acik", w.cizildi_mi())
    finally:
        w.kapat()


def test_kapi_tam_modele_bakar_kapsamli_basarili():
    print("\n[K5K-1] kapsamli cizim basarili ama tam model kurulamaz -> kapi KAPALI")
    from cekirdek import alt_model as am
    spec = _spec("pwr_ceyrek_kor")
    harf = next(iter(spec["kor"]["anahtar"]))
    spec["kor"]["anahtar"][harf] = "tanimsiz_demet"
    istekler = []
    w = _widget(spec, lambda s: am.parca_alt_modeli(s, "cubuk", "yakit_24"), istekler)
    try:
        kontrol("kapsamli cizim goruntu verdi", any(len(a.images) for a in w.figur.axes))
        kontrol("tam model kontrolu ayrica suruldu",
                [i["tur"] for i in istekler] == ["ciz", "kontrol"]
                and istekler[1]["spec"]["kor"]["tur"] == "kare_kafes", "-> %s"
                % [i["tur"] for i in istekler])
        kontrol("kapi kapali (tam model hatasi)", not w.cizildi_mi() and w.son_hata())
    finally:
        w.kapat()


def test_kapi_tam_modele_bakar_kapsamli_basarisiz():
    print("\n[K5K-2] kapsamli cizim basarisiz ama tam model iyi -> kapi ACIK; surerken de")
    from cekirdek import alt_model as am, sema
    spec = _spec("pwr_ceyrek_kor")
    bozuk = sema.cubuk("kullanilmayan", [sema.bolge(0.4, "tanimsiz_malzeme"), sema.bolge(None, "su")])
    spec["cubuklar"].append(bozuk)
    w = _widget(spec, lambda s: am.parca_alt_modeli(s, "cubuk", "kullanilmayan"))
    try:
        kontrol("kapsamli cizim basarisiz: tuvalde hata", not any(len(a.images) for a in w.figur.axes))
        kontrol("tam model iyi: kapi acik", w.cizildi_mi(), "-> %s" % (w.son_hata() or "")[-200:])
        w.kapsam_degisti()                     # kapsam degisti (secim): tam model ayni
        w._ciz()
        kontrol("kapsamli cizim surerken kapi tam model sonucuna gore (acik)",
                w.mesgul_mu() and w.cizildi_mi())
        w.bekle(_ZAMAN_ASIMI)
    finally:
        w.kapat()


def test_kapsam_degisince_tam_model_yeniden_denetlenmez():
    print("\n[K5K-3] ayni tam modelde kapsam degisimi: yalniz 'ciz' (kontrol tekrarlanmaz)")
    from cekirdek import alt_model as am
    spec = _spec("pwr_ceyrek_kor")
    istekler = []
    secim = {"ad": "yakit_24"}
    w = _widget(spec, lambda s: am.parca_alt_modeli(s, "cubuk", secim["ad"]), istekler)
    try:
        ilk = [i["tur"] for i in istekler]
        secim["ad"] = "yakit_31"
        w.kapsam_degisti()
        w.bekle(_ZAMAN_ASIMI)
        sonra = [i["tur"] for i in istekler][len(ilk):]
        kontrol("ilk: ciz + kontrol", ilk == ["ciz", "kontrol"], "-> %s" % ilk)
        kontrol("kapsam degisimi: yalniz ciz", sonra == ["ciz"], "-> %s" % sonra)
        kontrol("yeni pin cizildi", _gorunen(spec, {"uo2_31"}) <= _cizilen_malzemeler(w))
        sema_cubuk = {c["ad"]: c for c in spec["cubuklar"]}
        sema_cubuk["yakit_24"]["bolgeler"][0]["r"] *= 0.99   # secili OLMAYAN pin degisti
        w.iste()
        kontrol("tam model degisince kapi hemen kapanir", not w.cizildi_mi())
        w.bekle(_ZAMAN_ASIMI)
        n = len(istekler)
        son = [i["tur"] for i in istekler][len(ilk) + len(sonra):]
        kontrol("alt model ayni (onbellekten boyanir), yalniz tam model kontrolu",
                son == ["kontrol"], "-> %s" % son)
        kontrol("yeniden denetlendi: kapi acik", w.cizildi_mi())
        sema_cubuk["yakit_31"]["bolgeler"][0]["r"] *= 0.99   # secili pin degisti
        w.iste()
        w.bekle(_ZAMAN_ASIMI)
        son = [i["tur"] for i in istekler][n:]
        kontrol("secili pin degisti: ciz + kontrol", son == ["ciz", "kontrol"], "-> %s" % son)
        kontrol("kapi yine acik", w.cizildi_mi())
    finally:
        w.kapat()


HIZLI = [test_parcalar_pin_kapsami, test_demet_kapsami, test_plaka_ve_tambur_kapsami,
         test_geometri_dugum_kapsami, test_tam_model_kipi_ve_kapsamsiz,
         test_kapi_tam_modele_bakar_kapsamli_basarili,
         test_kapi_tam_modele_bakar_kapsamli_basarisiz,
         test_kapsam_degisince_tam_model_yeniden_denetlenmez]
YAVAS = []
