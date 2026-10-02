# -*- coding: utf-8 -*-
"""
 test_y1_harita_duzeltme.py  --  v3 Y1 inceleme: ag haritasi arayuzu duzeltmeleri

   E1  2B'de guc kutusu "Cizgisel guc" [W/cm] ve guc_dagilimi.toplam_guc ile ON
       DOLDURULMAZ (aktif yukseklik yok); 3B'de toplam guc [W] doldurulur
   E2  mutlak H genel isinma tally'sinden; genel tally yoksa uyari + hacim
   15  bagil kipte skorsuz ag: uyari + bos cizim, istisna yok
   14  bozuk statepoint: kart gorunur, uyari, cokme yok
   4   uzantisiz yol + mevcut dosya: uzerine yazma onayi sorulur
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import os
import tempfile

import numpy as np

from testler.ortak_test import kontrol


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _sonuc(z=1.0, ort=None):
    from cekirdek import mesh_tally as mt
    izg = (np.array([0.0, 1.0, 2.0]), np.array([0.0, 1.0]), np.array([-z, z]))
    ort = np.ones((2, 1, 1, 1, 1, 2)) if ort is None else ort
    return mt.MeshSonuc(ad="t", tur="duzenli", izgaralar=izg, merkez=(0.0, 0.0, 0.0),
                        skorlar=("flux", "kappa-fission"), nuklidler=("total",), enerji=None,
                        ortalama=ort, sapma=0.01 * ort, ozdeger=True)


def _kutu(w, veri):
    w.setCurrentIndex(w.findData(veri))


def test_2b_cizgisel_guc_kutusu():
    print("\n[Y1-H1] 2B: guc kutusu W/cm, toplam_guc ile on doldurulmaz; 3B'de W")
    _qt()
    from cekirdek import mesh_tally as mt
    from arayuz.sonuc.mesh_harita import MeshHaritaWidget
    w = MeshHaritaWidget()
    w.sonuclari_ayarla([_sonuc(z=mt.Z_2B_YARI)], toplam_guc=17.6e6,
                       genel_isi={"kappa-fission": 4.0, "heating-local": 4.2},
                       eksenel_sonsuz=True, aktif_yukseklik=None)
    kontrol("etiket Cizgisel guc, birim W/cm", "W/cm" in w.guc.suffix()
            and "izgisel" in w.guc_etiket.text(), "-> %s %s" % (w.guc_etiket.text(), w.guc.suffix()))
    kontrol("2B'de toplam_guc on doldurulmadi", w.guc.value() == 0.0)
    w.guc.setValue(100.0)
    _kutu(w.skor, "kappa-fission")
    _kutu(w.normalizasyon, "mutlak")
    _kutu(w.gosterim, "deger")
    # el hesabi: q'=100 W/cm, H=4 eV/kaynak, iki hucre esit (o=1): her hucre 50 W/cm / 1 cm2
    kontrol("2B mutlak deger 25 W/cm3 (q' o / (H A); o/H = 1/4)",
            np.allclose(w.gosterilen.deger, 25.0), "-> %s" % w.gosterilen.deger.ravel())
    w.sonuclari_ayarla([_sonuc(z=100.0)], toplam_guc=17.6e6,
                       genel_isi={"kappa-fission": 4.0}, eksenel_sonsuz=False,
                       aktif_yukseklik=366.0)
    kontrol("3B: Toplam guc [W] = guc_dagilimi.toplam_guc",
            w.guc.value() == 17.6e6 and w.guc.suffix().strip() == "W")


def test_2b_aktif_yukseklik_varsa_cizgisel_guc():
    print("\n[Y1-H2] 2B ama aktif yukseklik biliniyorsa q' = P / L on doldurulur")
    _qt()
    from cekirdek import mesh_tally as mt
    from arayuz.sonuc.mesh_harita import MeshHaritaWidget
    w = MeshHaritaWidget()
    w.sonuclari_ayarla([_sonuc(z=mt.Z_2B_YARI)], toplam_guc=17.6e6, genel_isi={},
                       eksenel_sonsuz=True, aktif_yukseklik=366.0)
    kontrol("q' = 17.6e6 / 366", abs(w.guc.value() - 17.6e6 / 366.0) < 0.1)


def test_genel_tally_yoksa_uyari():
    print("\n[Y1-H3] eski kosu (genel isinma yok): mutlak secilince uyari, hacim gosterilir")
    _qt()
    from arayuz.sonuc.mesh_harita import MeshHaritaWidget
    w = MeshHaritaWidget()
    w.sonuclari_ayarla([_sonuc()], toplam_guc=1e6, genel_isi={}, eksenel_sonsuz=False)
    _kutu(w.normalizasyon, "mutlak")
    kontrol("uyari yazildi", "tekrar" in w.uyari.text() or "genel" in w.uyari.text(),
            "-> %s" % w.uyari.text())
    kontrol("hacim basina cizildi", w.gosterilen is not None and "/kaynak" not in w.birim_metni
            or "cm" in w.birim_metni)


def test_bagil_skorsuz_ag_cokmez():
    print("\n[Y1-H4] bagil kipte butun ag skorsuz: uyari + bos cizim, istisna yok")
    _qt()
    from arayuz.sonuc.mesh_harita import MeshHaritaWidget
    w = MeshHaritaWidget()
    w.sonuclari_ayarla([_sonuc(ort=np.zeros((2, 1, 1, 1, 1, 2)))], genel_isi={})
    try:
        _kutu(w.normalizasyon, "bagil")
        hata = None
    except ValueError as e:
        hata = e
    kontrol("istisna yok", hata is None, "-> %s" % hata)
    kontrol("uyari skorlu hucre yok der", "skorlu" in w.uyari.text(), "-> %s" % w.uyari.text())


def test_bozuk_statepoint():
    print("\n[Y1-H5] bozuk statepoint: kart gorunur, uyari, cokme yok")
    _qt()
    from arayuz.sonuc.mesh_harita import MeshHaritaWidget
    w = MeshHaritaWidget()
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, "statepoint.10.h5")
        with open(yol, "wb") as f:
            f.write(b"bu bir hdf5 degil")
        w.statepoint_ayarla(yol, {})
    kontrol("uyari okunamadi", "okunamadı" in w.uyari.text(), "-> %s" % w.uyari.text())
    kontrol("kart gorunur (uyari okunabilsin)", w.isVisibleTo(None) or not w.isHidden())


def test_uzantisiz_yol_ve_mevcut_dosya():
    print("\n[Y1-H6] uzantisiz yol .vtk alir; mevcut dosyada uzerine yazma onayi sorulur")
    _qt()
    from arayuz.sonuc.mesh_harita import MeshHaritaWidget
    w = MeshHaritaWidget()
    w.sonuclari_ayarla([_sonuc()], genel_isi={})
    sorulan = []
    with tempfile.TemporaryDirectory() as d:
        mevcut = os.path.join(d, "aki.vtk")
        with open(mevcut, "w") as f:
            f.write("eski")
        w._uzerine_yaz_onayi = lambda yol: sorulan.append(yol) or False
        sonuc = w.secilen_yolu_yaz(os.path.join(d, "aki"))
        kontrol("onay soruldu ve reddedilince yazilmadi", sorulan == [mevcut] and sonuc is False
                and open(mevcut).read() == "eski")
        w._uzerine_yaz_onayi = lambda yol: True
        kontrol("onaylaninca yazildi", w.secilen_yolu_yaz(os.path.join(d, "aki")) is True
                and open(mevcut).read().startswith("# vtk"))
        kontrol("onerilen ad temiz", "/" not in w.onerilen_ad("a/b c"))


HIZLI = [test_2b_cizgisel_guc_kutusu, test_2b_aktif_yukseklik_varsa_cizgisel_guc,
         test_genel_tally_yoksa_uyari, test_bagil_skorsuz_ag_cokmez, test_bozuk_statepoint,
         test_uzantisiz_yol_ve_mevcut_dosya]
