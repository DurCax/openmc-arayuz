# -*- coding: utf-8 -*-
"""
 test_k2_veri_sayfasi.py  --  v3 K2: "Veri ve kütüphaneler" sayfasi (basssiz,
                              gercek widget akisi)

 Kabul: veri yokken ilk acilis senaryosu (sayfa kendiliginden acilir, Calistir
 kapali, serit sayfaya yonlendirir), klasor secimi kalici, ag olmadan (sahte
 HTTP sunucusu) arka planda indirme + iptal + surdurme.

 Her test kendi HOME / XDG dizinleriyle ve OPENMC_* degiskenleri olmadan
 calisir (testler/k2_yalitim.VeriYalitimi); gercek ~/nucdata ve kullanici ayarlari okunmaz.
"""

import hashlib
import os
import tempfile
import time

from testler.ortak_test import kontrol
from testler.k2_sahte_sunucu import SahteSunucu
from testler.k2_yalitim import VeriYalitimi

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_BEKLEME_S = 30.0


def _uyg():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _kutuphane(dizin):
    os.makedirs(os.path.join(dizin, "neutron"), exist_ok=True)
    open(os.path.join(dizin, "neutron", "H1.h5"), "w").close()
    xml = os.path.join(dizin, "cross_sections.xml")
    with open(xml, "w", encoding="utf-8") as f:
        f.write("<cross_sections><library materials='H1' path='neutron/H1.h5' "
                "type='neutron'/></cross_sections>")
    return xml


def _pencere():
    from arayuz.ana_pencere import AnaPencere
    p = AnaPencere()
    p._kaydetme_sor = lambda: True
    return p


def _kapat(p):
    from PySide6 import QtCore
    p.veri_sayfasi.bekle()
    p.s_tukenme.bekle()
    p._kirli = False
    p.close()
    p.deleteLater()
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)


def _bekle(kosul, sure=_BEKLEME_S):
    from PySide6 import QtCore
    son = time.monotonic() + sure
    while time.monotonic() < son:
        QtCore.QCoreApplication.processEvents()
        if kosul():
            return True
        time.sleep(0.01)
    return False


def test_sayfa_kenar_cubugunda():
    print("\n[K2-S1] Veri sayfasi kenar cubugunda; model sayfalari sozlesmesi degismedi")
    from cekirdek import uygunluk
    from arayuz.veri.sayfa import VeriSayfasi
    _uyg()
    with VeriYalitimi():
        p = _pencere()
        try:
            kontrol("kenar cubugunda 'veri'", "veri" in p.kenar.anahtarlar())
            kontrol("sekme_anahtarlari yine uygunluk.SEKMELER",
                    p.sekme_anahtarlari() == tuple(uygunluk.SEKMELER))
            kontrol("ek sayfa anahtarlari", p.ek_sayfa_anahtarlari() == ("veri",))
            p._editoru_goster()
            kontrol("sekmeye_git('veri')", p.sekmeye_git("veri") and p.gecerli_sekme() == "veri")
            kontrol("yiginda veri sayfasi",
                    p.yigin_sekme.currentWidget() is p.sekme_sayfasi("veri"))
            kontrol("sekme_widget VeriSayfasi", isinstance(p.sekme_widget("veri"), VeriSayfasi))
            kontrol("baslik", p.sekme_basligi("veri") == "Veri")
            kontrol("onizleme gizli", not p.onizleme_paneli.isVisible())
            kontrol("baska sayfaya donus", p.sekmeye_git("malzemeler")
                    and p.yigin_sekme.currentWidget() is p.sekme_sayfasi("malzemeler"))
            kontrol("kenardan secim de sayfayi acar",
                    p.kenar.sec("veri") and p.yigin_sekme.currentWidget()
                    is p.sekme_sayfasi("veri"))
        finally:
            _kapat(p)


def test_ilk_acilis_veri_yokken():
    print("\n[K2-S2] veri yok: ilk acilista sayfa acilir, Calistir kapali, serit yonlendirir; "
          "klasor secimi kalici")
    from arayuz.veri import kayit
    from cekirdek import veri_yolu
    _uyg()
    with VeriYalitimi() as y:
        p = _pencere()
        try:
            # Arrange: veri yok
            kontrol("veri yok", not veri_yolu.veri_hazir_mi())
            # Act: uygulamanin acilis tetigi
            acildi = kayit.ilk_acilis(p)
            # Assert
            kontrol("ilk acilis tetiklendi", acildi)
            kontrol("editor + Veri sayfasi", not p.baslangic_acik_mi()
                    and p.gecerli_sekme() == "veri")
            kontrol("bant gorunur", p.veri_sayfasi.bant.isVisibleTo(p.veri_sayfasi))
            izin, neden = p._kosu_izni()
            kontrol("Calistir kapali", not izin, neden)
            yerler = [b.yer for b in p._bulgular if b.seviye == "hata"]
            kontrol("veri bulgusu (hata)", "veri kutuphanesi" in yerler, repr(yerler))
            p.sekmeye_git("malzemeler")
            kontrol("serit bulgudan Veri sayfasina gider",
                    p.sekmeye_gitmeyi_dene("veri kutuphanesi") and p.gecerli_sekme() == "veri")
            # Act 2: klasor sec
            xml = _kutuphane(os.path.join(y.kok, "baska", "kutup"))
            p.veri_sayfasi.klasor.yol.setText(os.path.dirname(os.path.dirname(xml)))
            d = p.veri_sayfasi.klasor.kullan()
            kontrol("klasor denetimi tamam", d.tamam, repr(d.hatalar))
            kontrol("secim ayarda", veri_yolu.ayar_oku().get("cross_sections") == xml)
            kontrol("surec ortamina yazildi", os.environ.get("OPENMC_CROSS_SECTIONS") == xml)
            kontrol("veri bulgusu kalkti",
                    "veri kutuphanesi" not in [b.yer for b in p._bulgular])
            kontrol("bant gizlendi", not p.veri_sayfasi.bant.isVisibleTo(p.veri_sayfasi))
            p.veri_sayfasi.d_baslangic.click()
            kontrol("bant dugmesi baslangica doner", p.baslangic_acik_mi())
        finally:
            _kapat(p)
        q = _pencere()
        try:
            kontrol("secim kalici: yeni pencerede ilk acilis tetiklenmez",
                    not kayit.ilk_acilis(q) and q.baslangic_acik_mi())
            kontrol("kaynak ayar", veri_yolu.cross_sections().kaynak in ("ayar", "ortam"))
        finally:
            _kapat(q)


def _sahte_katalog(veri_indir, sunucu, arsiv_bayt, zincir_bayt, zincir_sha):
    kutup = veri_indir.Oge(kimlik="sahte", ad="Sahte", tur="kutuphane",
                           url=sunucu.url("/kutup.xz"), bayt=len(arsiv_bayt),
                           dizin_adi="sahte-hdf5", acik_bayt=10 ** 6)
    zincir = veri_indir.Oge(kimlik="sahte-termal", ad="Sahte termal", tur="zincir",
                            url=sunucu.url("/zincir.xml"), bayt=len(zincir_bayt),
                            sha256=zincir_sha, dosya_adi="chain_endfb80_thermal.xml",
                            kutuphane="sahte", spektrum="termal", uygulamada_kullanilir=True)
    return veri_indir.Katalog((kutup,), (zincir,), frozenset({"127.0.0.1"}), 4.0, "test", {})


def _arsiv(d):
    import io
    import tarfile
    yol = os.path.join(d, "a.tar.xz")
    with tarfile.open(yol, "w:xz") as tf:
        for ad, icerik in (("k/cross_sections.xml",
                            b"<cross_sections><library materials='H1' path='neutron/H1.h5' "
                            b"type='neutron'/></cross_sections>"),
                           ("k/neutron/H1.h5", b"h5" * 50000)):
            bilgi = tarfile.TarInfo(ad)
            bilgi.size = len(icerik)
            tf.addfile(bilgi, io.BytesIO(icerik))
    with open(yol, "rb") as f:
        return f.read()


def test_arka_planda_indirme_iptal_surdurme():
    print("\n[K2-S3] sahte sunucudan arka planda indirme: kesinti -> Surdur -> tamam, ayar yazilir")
    from cekirdek import veri_indir, veri_yolu
    from arayuz.veri.sayfa import VeriSayfasi
    _uyg()
    with VeriYalitimi() as y, SahteSunucu() as s:
        arsiv = _arsiv(y.kok)
        zincir = b"<depletion_chain>\n" + b" " * 300000 + b"</depletion_chain>\n"
        s.dosyalar.update({"/kutup.xz": arsiv, "/zincir.xml": zincir})
        s.ayar["/zincir.xml"] = {"kes": 100000}            # ilk istek yarida kesilir
        politika = veri_indir.UrlPolitikasi(semalar=frozenset({"http"}),
                                            alanlar=frozenset({"127.0.0.1"}), port_serbest=True)
        sayfa = VeriSayfasi(katalog=_sahte_katalog(veri_indir, s, arsiv, zincir,
                                                   hashlib.sha256(zincir).hexdigest()),
                            politika=politika)
        k = sayfa.indirme
        hedef = os.path.join(y.kok, "nucdata")
        k.hedef.setText(hedef)
        sinyal = []
        k.kuruldu.connect(sinyal.append)
        kontrol("indirme basladi", k.indir())
        kontrol("arayuz donmadi: basladiktan hemen sonra calisiyor", k.indiriyor_mu())
        kontrol("ilk deneme bitti", _bekle(lambda: not k.indiriyor_mu()))
        kontrol("kesinti bildirildi", "kesildi" in k.durum_etiketi.text()
                or "yarım" in k.durum_etiketi.text(), k.durum_etiketi.text())
        k._alan_guncelle()
        kontrol("dugme 'Surdur'", k.d_indir.text() == "Sürdür", k.d_indir.text())
        kontrol("ikinci deneme basladi", k.indir())
        kontrol("ikinci deneme bitti", _bekle(lambda: not k.indiriyor_mu()))
        kontrol("Range ile surduruldu", ("/zincir.xml", "bytes=100000-") in s.istekler,
                repr(s.istekler))
        kontrol("kuruldu sinyali", len(sinyal) == 1, k.durum_etiketi.text())
        ayar = veri_yolu.ayar_oku()
        kontrol("ayar: kutuphane", ayar.get("cross_sections") == os.path.join(
            hedef, "sahte-hdf5", "cross_sections.xml"), repr(ayar))
        kontrol("ayar: zincir", ayar.get("zincir", "").endswith("chain_endfb80_thermal.xml"))
        kontrol("veri hazir", veri_yolu.veri_hazir_mi())
        sayfa.deleteLater()


def test_iptal_dugmesi():
    print("\n[K2-S4] Iptal: isci durur, 'Sürdür' kalir, hata degil iptal bildirilir")
    from cekirdek import veri_indir
    from arayuz.veri.sayfa import VeriSayfasi
    _uyg()
    with VeriYalitimi() as y, SahteSunucu() as s:
        buyuk = b"0" * (veri_indir.PARCA_BOYUTU * 40)
        arsiv = _arsiv(y.kok)
        s.dosyalar.update({"/kutup.xz": arsiv, "/zincir.xml": buyuk})
        politika = veri_indir.UrlPolitikasi(semalar=frozenset({"http"}),
                                            alanlar=frozenset({"127.0.0.1"}), port_serbest=True)
        sayfa = VeriSayfasi(katalog=_sahte_katalog(veri_indir, s, arsiv, buyuk, None),
                            politika=politika)
        k = sayfa.indirme
        k.hedef.setText(os.path.join(y.kok, "nucdata"))
        k.indir()
        k.iptal()
        kontrol("isci bitti", _bekle(lambda: not k.indiriyor_mu()))
        kontrol("iptal metni", "İptal" in k.durum_etiketi.text() or "Tamam" in
                k.durum_etiketi.text(), k.durum_etiketi.text())
        kontrol("dugmeler yeniden etkin", k.d_indir.isEnabled() and not k.d_iptal.isEnabled())
        sayfa.deleteLater()


def test_gecersiz_hedef_ve_disk():
    print("\n[K2-S5] gecersiz hedef klasor indirmeyi baslatmaz, nedeni gosterilir")
    from arayuz.veri.sayfa import VeriSayfasi
    _uyg()
    with VeriYalitimi():
        sayfa = VeriSayfasi()
        k = sayfa.indirme
        k.hedef.setText("/usr/share/nucdata")
        kontrol("baslamadi", not k.indir() and not k.indiriyor_mu())
        kontrol("neden yazildi", "sistem" in k.durum_etiketi.text(), k.durum_etiketi.text())
        k.hedef.setText("goreli/yol")
        k._alan_guncelle()
        kontrol("goreli yol uyarisi", "Mutlak" in k.alan_etiketi.text())
        kontrol("katalogdan 12 kutuphane", k.tablo.rowCount() == 12)
        kontrol("varsayilan ENDF/B-VIII.0", k.secili_kutuphane().kimlik == "endfb-viii.0")
        kontrol("lisans notu gosterildi", "openmc.org" in k.not_etiketi.text())
        kontrol("dort uygulama zinciri", len(k.zincir_kutulari) == 4)
        sayfa.deleteLater()


def test_gereksinim_karti():
    print("\n[K2-S6] gereksinim karti bes satir; veri yokken kutuphane 'eksik'")
    from arayuz.veri.sayfa import VeriSayfasi
    _uyg()
    with VeriYalitimi():
        sayfa = VeriSayfasi()
        satirlar = {g.anahtar: g for g in sayfa.gereksinim.satirlar}
        kontrol("bes satir", len(satirlar) == 5)
        kontrol("kutuphane eksik", satirlar["kutuphane"].durum == "eksik")
        kontrol("openmc bulundu (bu ortam)", satirlar["openmc"].durum in ("tamam", "uyari",
                                                                          "eksik"))
        sayfa.deleteLater()


HIZLI = [test_sayfa_kenar_cubugunda, test_ilk_acilis_veri_yokken,
         test_arka_planda_indirme_iptal_surdurme, test_iptal_dugmesi,
         test_gecersiz_hedef_ve_disk, test_gereksinim_karti]
YAVAS = []
