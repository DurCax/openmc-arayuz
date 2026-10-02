# -*- coding: utf-8 -*-
"""
test_k1_akis.py -- v3 K1 kabul: ORNEK KULLANMADAN sifirdan pin hucresi kurup
kosmak, basliksiz (offscreen) GERCEK widget akisiyla:

  Baslangic > Sifirdan (pin hucre) -> Malzemeler: kutuphaneden UO2, Zr-4, He, su
  -> Parcalar: "Cubuk > Yakit cubugu" -> Geometri: cubuk hucreye yerlesti
  -> dogrulama temiz -> onizleme cizildi -> Calistir acik
  -> hizli: kosucu kuru calistirma (model.xml yazilir)
  -> yavas: kisa Monte Carlo kosusu (k-inf fiziksel aralikta)

Malzeme diyalogu exec() EDILMEZ: sekmenin _diyalog_calistir kancasi diyalogu
GERCEKTEN kurar, kutuphane ogesini secer ve "Ekle" ile kabul eder.
"""

import os
import tempfile

from testler.ortak_test import kontrol, ISLEM_PARCACIGI

_ZAMAN_ASIMI = 120.0
# Westinghouse 17x17 olculu pin hucresi, kutuphane varsayilanlariyla (UO2
# %3.0, borsuz su): olculen k-inf 1.373 +- 0.010 (02.10.2026, 1000x20 kisa
# kosu; sicak sablonun 1.3227'sinden yuksek cunku varsayilan sicakliklar daha
# soguk). Kisa kosuda genis pencere yeter (fizik testi degil, akis testi).
_KINF_ARALIGI = (1.15, 1.50)
_KISA_KOSU = {"parcacik": 1000, "cevrim": 20, "pasif": 5}
_MALZEMELER = ("uo2", "zirkaloy4", "helyum", "su")


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _kutuphaneden_kabul(sira):
    """MalzemeSekmesi._diyalog_calistir yerine: sıradaki kutuphane ogesini
    secip "Ekle"ye basar (diyalog gercek, yalniz exec() atlanir)."""
    kalan = list(sira)

    def calistir(d):
        d.sec(kalan.pop(0))
        if not d.d_tamam.isEnabled():
            return False
        d.d_tamam.click()
        return d.result() == 1
    return calistir


def _sifirdan_pin_kur():
    from arayuz.ana_pencere import AnaPencere
    p = AnaPencere()
    p._kaydetme_sor = lambda: True
    b = p.baslangic
    b.sifirdan_turu.setCurrentIndex(b.sifirdan_turu.findData("tek_cubuk"))
    b.d_sifirdan.click()
    p.s_malzeme._diyalog_calistir = _kutuphaneden_kabul(_MALZEMELER)
    for _ad in _MALZEMELER:
        p.adim_rehberi.dugmeler["malzeme"].click()
        p.s_malzeme.d_kutup.click()
    p._dogrula()
    p.adim_rehberi.dugmeler["parca"].click()
    p.s_cubuk.sablon_eylemleri["yakit"].trigger()
    p._dogrula()
    p.adim_rehberi.dugmeler["geometri"].click() if not p.adim_rehberi.isHidden() \
        else p.sekmeye_git("kor")
    p.onizleme._ciz()
    p.onizleme.bekle(_ZAMAN_ASIMI)
    p._dogrula()
    p._kosu_dugmesi_guncelle()
    return p


def _kapat(p):
    from PySide6 import QtCore
    p.s_tukenme.bekle()
    p._kirli = False
    p.close()
    p.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


def _kontrol_hazir(p):
    from cekirdek import dogrula
    kontrol("4 malzeme kutuphaneden eklendi",
            [m["ad"] for m in p.spec["malzemeler"]] == list(_MALZEMELER),
            "-> %s" % [m["ad"] for m in p.spec["malzemeler"]])
    kontrol("yakit cubugu eklendi ve hucreye yerlesti",
            len(p.spec["cubuklar"]) == 1
            and p.spec["kor"]["cubuk"] == p.spec["cubuklar"][0]["ad"])
    kontrol("adim rehberi tamamlaninca gizlendi", p.adim_rehberi.isHidden())
    kontrol("dogrulama temiz (hata yok)", not dogrula.hata_var(p._bulgular),
            "-> %s" % [(b.yer, b.mesaj) for b in p._bulgular if b.seviye == "hata"])
    kontrol("serit eksik adim kipinden cikti",
            p.serit.rozet.property("rozet") in ("basari", "uyari", "bilgi")
            and "aşama" not in p.serit.ozet.text(), "-> %s" % p.serit.ozet.text())
    kontrol("onizleme cizildi", p.onizleme.cizildi_mi())
    izin, neden = p._kosu_izni()
    kontrol("Calistir acik", izin and p.e_calistir.isEnabled(), "-> %s" % neden)


def test_sifirdan_pin_kuru_calistirma():
    print("\n[K1A-1] sifirdan pin hucresi (gercek widget akisi) -> kuru calistirma")
    _qt()
    from cekirdek import kosucu
    p = _sifirdan_pin_kur()
    try:
        _kontrol_hazir(p)
        with tempfile.TemporaryDirectory() as dizin:
            _model, _bilgi, yol = kosucu.xml_yaz(p.spec, dizin)
            kontrol("kuru calistirma: model.xml + spec.json yazildi",
                    os.path.isfile(yol) and os.path.isfile(os.path.join(dizin, "spec.json")))
    finally:
        _kapat(p)


def test_yavas_sifirdan_pin_kosusu(gecici):
    print("\n[K1A-2] sifirdan pin hucresi -> kisa Monte Carlo kosusu")
    _qt()
    import copy
    from cekirdek import kosucu
    p = _sifirdan_pin_kur()
    try:
        _kontrol_hazir(p)
        spec = copy.deepcopy(p.spec)
    finally:
        _kapat(p)
    spec["ayarlar"].update(_KISA_KOSU)
    sonuc = kosucu.calistir(spec, os.path.join(gecici, "k1"), is_parcacigi=ISLEM_PARCACIGI)
    kontrol("kosu basarili", sonuc["basarili"], "-> %s" % sonuc.get("log"))
    if sonuc["basarili"]:
        k, s = kosucu.sonuc_oku(sonuc["statepoint"])["keff"]
        kontrol("k-inf fiziksel aralikta %s" % (_KINF_ARALIGI,),
                _KINF_ARALIGI[0] < k < _KINF_ARALIGI[1], "-> %.4f ± %.4f" % (k, s))


HIZLI = [test_sifirdan_pin_kuru_calistirma]
YAVAS = [test_yavas_sifirdan_pin_kosusu]
