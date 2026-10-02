# -*- coding: utf-8 -*-
"""
 test_y1_mesh_arayuz.py  --  v3 Y1: mesh tally arayuzu (basssiz, gercek widget akisi)

   Hesap ayarlari > Tally'ler: ag turu, otomatik/acik sinirlar (sinir kutusundan
   oneri), enerji grup yapisi (CASMO-2/4/8 ...), spec'e yazim; arayuz modeli =
   uretilen betik modeli.
   Calistir > Ag (mesh) haritasi: tally/skor/grup/dilim secimi, normalizasyon,
   sigma ve bagil hata, yuksek hatali hucre isareti, VTK disa aktarma.
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import math
import os
import tempfile

import numpy as np

from testler.ortak_test import kontrol, ORNEK


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _sekme(ornek="pwr_17x17.json"):
    from cekirdek import sema
    from arayuz.sekme_ayar import AyarSekmesi
    _qt()
    spec = sema.yukle(os.path.join(ORNEK, ornek))
    a = AyarSekmesi()
    a.spec_yukle(spec)
    return a, spec


def _mesh(spec):
    t = spec["tallyler"][-1]
    return next((f for f in t["filtreler"] if f["tur"] == "mesh"), None)


def _kutu_sec(kutu, veri):
    i = kutu.findData(veri)
    kutu.setCurrentIndex(i)
    return i


def test_form_ag_turu_ve_sinirlar():
    print("\n[Y1-A1] form: ag turu, eksen etiketleri, otomatik -> acik sinir (oneriden)")
    from cekirdek import mesh_tally as mt
    a, spec = _sekme()
    a._tally_ekle()
    a.t_mesh_var.setChecked(True)
    kontrol("yeni ag duzenli + otomatik", _mesh(spec) == mt.filtre_duzenli([10, 10, 1]),
            "-> %s" % _mesh(spec))
    kontrol("oneri metni sinir kutusunu soyler", "10.71" in a.t_mesh_oneri.text(),
            "-> %s" % a.t_mesh_oneri.text())
    # Act: silindirik
    _kutu_sec(a.t_mesh_tur, mt.SILINDIRIK)
    f = _mesh(spec)
    kontrol("silindirik + otomatik yazildi", f.get("mesh_turu") == mt.SILINDIRIK
            and f.get("otomatik") is True, "-> %s" % f)
    kontrol("eksen etiketleri r, φ, z", [w._etiket.text() for w in
            (a.t_mesh_nx, a.t_mesh_ny, a.t_mesh_nz)] == ["r", "φ", "z"])
    kontrol("2B modelde ikinci bolme (φ) gorunur",
            not a.t_mesh_ny.isHidden())
    # Act: otomatigi kapat -> oneri acik sinira yazilir
    a.t_mesh_oto.setChecked(False)
    f = _mesh(spec)
    kontrol("acik r_ust = oneri (10.71)", math.isclose(f.get("r_ust", 0), 10.71)
            and "otomatik" not in f, "-> %s" % f)
    a.t_mesh_r.setValue(8.0)
    kontrol("yaricap degisince spec'e yazilir", math.isclose(_mesh(spec)["r_ust"], 8.0))
    # duzenli acik sinir
    _kutu_sec(a.t_mesh_tur, mt.DUZENLI)
    f = _mesh(spec)
    z2 = mt.Z_2B_YARI
    kontrol("duzenliye donus: acik alt/ust = oneri", f.get("alt") == [-10.71, -10.71, -z2]
            and f.get("ust") == [10.71, 10.71, z2] and "mesh_turu" not in f, "-> %s" % f)
    kontrol("hata yok", mt.filtre_hatalari(f) == [])


def test_form_dosyadan_yukler_ve_korur():
    print("\n[Y1-A2] form dosyadaki silindirik agi yukler; bilinmeyen alan (merkez) korunur")
    from cekirdek import mesh_tally as mt
    a, spec = _sekme("pwr_mesh_aki.json")
    spec["tallyler"][1]["filtreler"][0]["merkez"] = [1.0, 0.0, 0.0]
    a.spec_yukle(spec)
    a.tally_liste.setCurrentRow(1)
    kontrol("tur kutusu silindirik", a.t_mesh_tur.currentData() == mt.SILINDIRIK)
    kontrol("bolmeler 8 x 12", (a.t_mesh_nx.value(), a.t_mesh_ny.value()) == (8, 12))
    a.t_mesh_nx.setValue(6)
    f = spec["tallyler"][1]["filtreler"][0]
    kontrol("bolme yazildi, merkez korundu", f["boyut"][0] == 6 and f.get("merkez") == [1.0, 0.0, 0.0],
            "-> %s" % f)
    a.tally_liste.setCurrentRow(0)
    kontrol("duzenli tally'de grup yapisi CASMO-2 gosterilir",
            a.t_enerji_yapi.currentData() == "CASMO-2", "-> %s" % a.t_enerji_yapi.currentData())


def test_form_enerji_grup_yapisi():
    print("\n[Y1-A3] enerji grup yapisi secimi sinirlari OpenMC'den yazar")
    from cekirdek import mesh_tally as mt
    a, spec = _sekme()
    a._tally_ekle()
    a.t_enerji_var.setChecked(True)
    _kutu_sec(a.t_enerji_yapi, "CASMO-8")
    e = next(f for f in spec["tallyler"][-1]["filtreler"] if f["tur"] == "enerji")
    kontrol("CASMO-8 sinirlari", e["gruplar"] == mt.grup_sinirlari("CASMO-8"))
    kontrol("metin kutusu da guncel", a._sayi_listesi(a.t_enerji.text()) == e["gruplar"])
    a.t_enerji.setText("0.0, 1.0, 2.0e7")
    a.t_enerji.editingFinished.emit()
    kontrol("elle sinir -> 'Elle'", a.t_enerji_yapi.currentData() is None)


def test_form_betik_esdegerligi():
    print("\n[Y1-A4] formla kurulan kuresel ag: kurucu modeli = uretilen betik modeli")
    import importlib.util
    from cekirdek import kurucu, kod_uret, mesh_tally as mt
    a, spec = _sekme("godiva_kriter.json")
    a._tally_ekle()
    a.t_mesh_var.setChecked(True)
    _kutu_sec(a.t_mesh_tur, mt.KURESEL)
    a.t_mesh_nx.setValue(7)
    model, _b = kurucu.kur(spec)
    eski = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        try:
            os.chdir(d)
            with open("model.py", "w", encoding="utf-8") as f:
                f.write(kod_uret.uret(spec, "model.py"))
            sm = importlib.util.spec_from_file_location("y1_form_betik", os.path.join(d, "model.py"))
            mod = importlib.util.module_from_spec(sm)
            sm.loader.exec_module(mod)
        finally:
            os.chdir(eski)

    def izg(m):
        import openmc
        t = [t for t in m.tallies if t.name == spec["tallyler"][-1]["ad"]][0]
        mesh = [f for f in t.filters if isinstance(f, openmc.MeshFilter)][0].mesh
        return type(mesh).__name__, [np.asarray(g).tolist() for g in mesh._grids]
    ia, ib = izg(model), izg(mod.model)
    kontrol("SphericalMesh, r 7 bolme", ia[0] == "SphericalMesh" and len(ia[1][0]) == 8)
    kontrol("kurucu = betik", ia == ib)


# ---------------------------------------------------------------------------
# sonuc haritasi
# ---------------------------------------------------------------------------

def _sonuclar():
    from testler.test_y1_mesh_sonuc import _sentetik
    from cekirdek import mesh_tally as mt
    d = _sentetik("duzenli")
    # bir hucrede yuksek hata, bir hucrede skor yok
    sapma = d.sapma.copy()
    sapma[0, 0, 0] = 0.5 * d.ortalama[0, 0, 0]
    ort = d.ortalama.copy()
    ort[2, 1, 1] = 0.0
    sapma[2, 1, 1] = 0.0
    import dataclasses
    d = dataclasses.replace(d, ortalama=ort, sapma=sapma)
    return [d, _sentetik("silindirik", ne=1, skorlar=("flux",))], mt


def test_harita_secim_ve_isaret():
    print("\n[Y1-A5] harita: tally/skor/grup/dilim; sigma ve bagil hata; isaretli hucre")
    _qt()
    from arayuz.sonuc.mesh_harita import MeshHaritaWidget
    sonuclar, mt = _sonuclar()
    w = MeshHaritaWidget()
    kontrol("bos durumda gizli", w.isHidden() or not w.isVisibleTo(None))
    w.sonuclari_ayarla(sonuclar, toplam_guc=None)
    kontrol("iki tally listede", w.tally.count() == 2)
    kontrol("skorlar flux, kappa-fission", [w.skor.itemData(i) for i in range(w.skor.count())]
            == ["flux", "kappa-fission"])
    kontrol("gruplar: toplam + 2 grup", w.grup.count() == 3)
    _kutu_sec(w.eksen, 2)
    kontrol("z dilim kaydiricisi 1..2", (w.dilim.minimum(), w.dilim.maximum()) == (1, 2))
    w.dilim.setValue(1)
    _kutu_sec(w.grup, 0)
    _kutu_sec(w.normalizasyon, "kaynak")
    _kutu_sec(w.gosterim, "deger")
    o, _s = mt.secim(sonuclar[0], "flux", 0)
    kontrol("cizilen deger = dilim", np.allclose(w.gosterilen.deger, o[:, :, 0]))
    _kutu_sec(w.gosterim, "bagil")
    kontrol("bagil hata haritasi (0,0) = 0.5", math.isclose(w.gosterilen.deger[0, 0], 0.5))
    kontrol("isaretli hucre sayisi (dilimde 1)", int(w.isaretli.sum()) == 1)
    w.dilim.setValue(2)
    kontrol("ikinci dilimde skorsuz hucre isaretli", bool(w.isaretli[2, 1]))
    kontrol("ozet yuksek hatali hucreyi soyler", "1" in w.ozet.text() and "%" in w.ozet.text(),
            "-> %s" % w.ozet.text())
    w.tally.setCurrentIndex(1)
    kontrol("silindirik tally: tek grup (toplam)", w.grup.count() == 1)


_GENEL = {"kappa-fission": 1.0e8, "heating-local": 1.05e8}   # genel isinma (eV/kaynak)


def test_harita_normalizasyon_ve_vtk():
    print("\n[Y1-A6] harita: mutlak normalizasyon toplam guc ister; VTK disa aktarma")
    _qt()
    from arayuz.sonuc.mesh_harita import MeshHaritaWidget
    sonuclar, mt = _sonuclar()
    w = MeshHaritaWidget()
    w.sonuclari_ayarla(sonuclar, toplam_guc=None, genel_isi=_GENEL)
    _kutu_sec(w.normalizasyon, "mutlak")
    kontrol("guc yokken mutlak secilemez (uyari)", w.normalizasyon.currentData() != "mutlak"
            or "güç" in w.uyari.text().lower(), "-> %s" % w.uyari.text())
    w.sonuclari_ayarla(sonuclar, toplam_guc=1.0e6, genel_isi=_GENEL)
    _kutu_sec(w.skor, "kappa-fission")
    _kutu_sec(w.normalizasyon, "mutlak")
    _kutu_sec(w.gosterim, "deger")
    kontrol("mutlak birim W/cm3", "W/cm³" in w.birim_metni, "-> %s" % w.birim_metni)
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, "aki.vtk")
        ok = w.vtk_disa_aktar(yol)
        kontrol("VTK yazildi", ok and os.path.getsize(yol) > 500)
        kotu = w.vtk_disa_aktar(os.path.join(d, "yok", "x.vtk"))
        kontrol("yazilamayan yol: False + uyari (cokmez)", kotu is False and w.uyari.text())


def test_yavas_calistir_sayfasi_mesh_karti(gecici):
    print("\n[Y1-A7] YAVAS: kosu dizini Calistir sayfasina yuklenince ag haritasi gorunur")
    from cekirdek import kurucu, sema
    from testler.ortak_test import ISLEM_PARCACIGI
    uyg = _qt()
    spec = sema.yukle(os.path.join(ORNEK, "pwr_mesh_aki.json"))
    spec["ayarlar"].update(parcacik=2000, cevrim=20, pasif=8)
    eski = os.getcwd()
    try:
        os.chdir(gecici)
        model, _b = kurucu.kur(spec)
        model.run(threads=ISLEM_PARCACIGI, output=False)
    finally:
        os.chdir(eski)
    from arayuz.sekme_calistir import CalistirSekmesi
    s = CalistirSekmesi()
    s.spec_ayarla(spec)
    kontrol("kosudan once ag karti gizli", not s.mesh_karti.isVisibleTo(s))
    ok = s.kosu_dizinini_yukle(gecici)
    uyg.processEvents()
    kontrol("kosu yuklendi", ok)
    kontrol("ag karti gorunur, iki tally", s.mesh_karti.isVisibleTo(s)
            and s.mesh_harita.tally.count() == 2)
    kontrol("harita cizildi", s.mesh_harita.gosterilen is not None
            and s.mesh_harita.gosterilen.deger.shape == (17, 17))
    s.sifirla()          # proje degisince (yeni/ac/ornek)
    kontrol("yeni projede ag karti temizlendi", not s.mesh_karti.isVisibleTo(s)
            and not s.mesh_harita.sonuclar)
    s.deleteLater()


HIZLI = [test_form_ag_turu_ve_sinirlar, test_form_dosyadan_yukler_ve_korur,
         test_form_enerji_grup_yapisi, test_form_betik_esdegerligi,
         test_harita_secim_ve_isaret, test_harita_normalizasyon_ve_vtk]
YAVAS = [test_yavas_calistir_sayfasi_mesh_karti]
