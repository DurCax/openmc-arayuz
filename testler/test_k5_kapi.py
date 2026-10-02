# -*- coding: utf-8 -*-
"""
 test_k5_kapi.py  --  v3 K5 inceleme: Calistir kapisi kalici kapali kalmaz

 (a) ayni icerikle spec_ayarla (duzenle-geri al): kapi bilinmez olur ve
     kapsamli cizimin ardindan tam model yeniden denetlenir;
 (b) tam model cizimi kapsamli cizimle yarida kesilirse ayni;
 (c) kapsamli cizim sirasinda isci coker: tam model denetimi yine surulur,
     gecici hata kapi sonucu olarak hatirlanmaz.
"""

import copy

from testler.ortak_test import kontrol
from testler.test_k5_onizleme import _ZAMAN_ASIMI, _spec, _widget


def _pin(ad="yakit_24"):
    from cekirdek import alt_model as am
    return lambda s: am.parca_alt_modeli(s, "cubuk", ad)


def test_ayni_icerikle_spec_ayarla_kapiyi_kilitlemez():
    print("\n[K5G-1] ayni icerikli spec_ayarla: kapsamli cizimden sonra kontrol, kapi acik")
    istekler = []
    spec = _spec("pwr_ceyrek_kor")
    w = _widget(spec, _pin(), istekler)
    try:
        kontrol("ilk durum: kapi acik", w.cizildi_mi())
        n = len(istekler)
        w.spec_ayarla(copy.deepcopy(spec))          # ayni icerik (duzenle + geri al)
        w.bekle(_ZAMAN_ASIMI)
        sonra = [i["tur"] for i in istekler[n:]]
        kontrol("tam model yeniden denetlendi", "kontrol" in sonra, "-> %s" % sonra)
        kontrol("kapi acik", w.cizildi_mi(), "-> %s" % (w.son_hata() or ""))
    finally:
        w.kapat()


def test_yarida_kesilen_tam_cizim_kapiyi_kilitlemez():
    print("\n[K5G-2] tam model cizimi kapsamli cizimle kesilir: kapi yine acilir")
    from arayuz.onizleme_kapsam import KAPSAM_OTOMATIK, KAPSAM_TAM
    istekler = []
    w = _widget(_spec("pwr_ceyrek_kor"), _pin(), istekler)
    try:
        w.kapsam.setCurrentIndex(w.kapsam.findData(KAPSAM_TAM))      # tam cizim baslar
        kontrol("tam model istegi yolda", w._istek is not None and not w._istek["kapsam"])
        w.kapsam.setCurrentIndex(w.kapsam.findData(KAPSAM_OTOMATIK))  # hemen kapsamliya don
        w.bekle(_ZAMAN_ASIMI)
        kontrol("kapi acik (tam model yeniden denetlendi)", w.cizildi_mi(),
                "-> %s" % [i["tur"] for i in istekler])
    finally:
        w.kapat()


def test_kapsamli_cokme_kapi_denetimini_surer():
    print("\n[K5G-3] kapsamli cizimde cokme: tuvalde hata, tam model kontrolu surulur, kapi acik")
    istekler = []
    spec = _spec("pwr_ceyrek_kor")
    w = _widget(spec, _pin(), istekler)
    try:
        spec["cubuklar"][0]["bolgeler"][0]["r"] *= 0.99     # tam model degisti: kapi bilinmez
        w._ciz()
        kontrol("kapsamli istek yolda", w._istek is not None and w._istek["kapsam"])
        n = len(istekler)
        w._coktu("test: isci coktu")                          # istemcinin coktu sinyali
        kontrol("cokmeden sonra tam model kontrolu gonderildi",
                [i["tur"] for i in istekler[n:]] == ["kontrol"],
                "-> %s" % [i["tur"] for i in istekler[n:]])
        w.bekle(_ZAMAN_ASIMI)
        kontrol("kapi tam model sonucuna gore acik", w.cizildi_mi(), "-> %s" % (w.son_hata() or ""))
    finally:
        w.kapat()


def test_gecici_kapi_hatasi_hatirlanmaz():
    print("\n[K5G-4] tam model kontrolunde cokme: kapi kapali ama sonraki kapsamli cizim yeniden dener")
    istekler = []
    spec = _spec("pwr_ceyrek_kor")
    w = _widget(spec, _pin(), istekler)
    try:
        spec["cubuklar"][0]["bolgeler"][0]["r"] *= 0.99
        w._ciz()
        # kapsamli cizimin bitmesini bekle, kontrol yola cikinca coktur
        from testler.test_h2_onizleme import _bekle
        _bekle(lambda: w._istek is not None and w._istek.get("kapi"), _ZAMAN_ASIMI)
        w._coktu("test: isci coktu")
        kontrol("gecici hata: kapi kapali", not w.cizildi_mi())
        n = len(istekler)
        w.kapsam_degisti()
        w.bekle(_ZAMAN_ASIMI)
        kontrol("sonraki kapsamli cizimde kontrol yeniden denendi",
                "kontrol" in [i["tur"] for i in istekler[n:]],
                "-> %s" % [i["tur"] for i in istekler[n:]])
        kontrol("kapi acik", w.cizildi_mi())
    finally:
        w.kapat()


HIZLI = [test_ayni_icerikle_spec_ayarla_kapiyi_kilitlemez, test_yarida_kesilen_tam_cizim_kapiyi_kilitlemez,
         test_kapsamli_cokme_kapi_denetimini_surer, test_gecici_kapi_hatasi_hatirlanmaz]
YAVAS = []
