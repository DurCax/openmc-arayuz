# -*- coding: utf-8 -*-
"""
 test_y9_arayuz.py  --  v3 Y9: Parcalar > TRISO formu, onizleme kapsami (alt model)

 HIZLI: bolum gorunurlugu, form <-> spec, ekleme sablonu, ad degisimi, silme, alt model.
"""

import os

from testler.ortak_test import kontrol, ORNEK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _yukle(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _sekme(spec):
    from arayuz.sekme_cubuk import CubukSekmesi
    w = CubukSekmesi()
    w.spec_yukle(spec)
    return w


def test_triso_bolumu_gorunurluk_ve_secim_formu_doldurur():
    print("\n[Y9-U1] TRISO bolumu: gelismis modda gorunur, sablonda gizli; secim formu doldurur")
    _qt()
    # Arrange
    w = _sekme(_yukle("htgr_kompakt"))
    # Act
    w._triso_sec("agr1_kompakt")
    # Assert
    kontrol("gelismis: bolum gorunur", not w.triso_karti.isHidden())
    kontrol("listede agr1_kompakt", [w.x_liste.item(i).text() for i in range(w.x_liste.count())]
            == ["agr1_kompakt"])
    kontrol("secim TRISO sayfasini acar", w.yigin.currentWidget() is w.triso_sayfa)
    kontrol("pf 0.35", abs(w.x_pf.value() - 0.35) < 1e-9)
    kontrol("5 katman satiri", len(w.x_katman_kutular) == 5)
    kontrol("cekirdek yaricapi 0.0175", abs(w.x_katman_kutular[0][0].value() - 0.0175) < 1e-9)
    kontrol("ozet parcacik sayisi", "parçacık" in w.x_ozet.text(), "-> %s" % w.x_ozet.text())
    kontrol("secili oge kapsami", w.secili_oge() == ("triso", "agr1_kompakt"))
    w.spec_yukle(_yukle("pwr_17x17"))
    kontrol("sablon modu: bolum gizli", w.triso_karti.isHidden())


def test_form_degisikligi_spec_e_yazilir():
    print("\n[Y9-U2] form: pf, yontem ve katman yaricapi spec['trisolar']'a yazilir")
    _qt()
    # Arrange
    spec = _yukle("htgr_kompakt")
    w = _sekme(spec)
    w._triso_sec("agr1_kompakt")
    # Act
    w.x_pf.setValue(0.25)
    w.x_yontem.setCurrentIndex(w.x_yontem.findData("duzenli"))
    w.x_katman_kutular[3][0].setValue(0.0360)
    t = w.spec["trisolar"][0]
    # Assert
    kontrol("pf yazildi", abs(t["paketleme"] - 0.25) < 1e-9)
    kontrol("yontem duzenli", t["yontem"] == "duzenli")
    kontrol("katman 4 yaricapi", abs(t["katmanlar"][3]["r"] - 0.0360) < 1e-9)
    kontrol("ozet duzenli adim gosterir", "kübik adım" in w.x_ozet.text(), "-> %s" % w.x_ozet.text())


def test_ekle_ad_degistir_ve_sil():
    print("\n[Y9-U3] ekle (AGR-1 sablonu), ad degistir (agac basvurusu da), kullanilan tanimi sil")
    _qt()
    # Arrange
    spec = _yukle("htgr_kompakt")
    w = _sekme(spec)
    # Act / Assert: ekle
    ad = w.triso_ekle("htr10")
    kontrol("benzersiz ad", ad == "htr10" and len(w.spec["trisolar"]) == 2)
    kontrol("pebble sayfasi: yakit yaricapi gorunur", not w.x_yakit_yaricap.isHidden()
            or w.x_sekil.currentData() == "pebble")
    # ad degistir
    w._triso_sec("agr1_kompakt")
    w.x_ad.setText("kompakt_yeni")
    w._triso_ad_degisti()
    ic = w.spec["geometri"]["kok"]["ic"]
    kontrol("tanim yeniden adlandirildi", [t["ad"] for t in w.spec["trisolar"]]
            == ["kompakt_yeni", "htr10"])
    kontrol("agac basvurusu da", ic.get("ad") == "kompakt_yeni", "-> %r" % ic)
    # sil (kullanilmayan)
    w._triso_sec("htr10")
    w._triso_sil()
    kontrol("htr10 silindi", [t["ad"] for t in w.spec["trisolar"]] == ["kompakt_yeni"])


def test_alt_model_triso_kompakt_ve_pebble():
    print("\n[Y9-U4] onizleme kapsami: TRISO alt modeli kompaktta silindir+yukseklik, pebblede kure")
    from cekirdek import alt_model, triso
    # Arrange
    spec = _yukle("htgr_kompakt")
    pebble = triso.sablon("htr10", "peb", {k: "uco" for k in triso.KATMAN_ADLARI}
                          | {"matris": "matris", "kabuk": "grafit", "dis": "grafit"})
    spec["trisolar"].append(pebble)
    # Act
    a = alt_model.parca_alt_modeli(spec, "triso", "agr1_kompakt")
    b = alt_model.parca_alt_modeli(spec, "triso", "peb")
    # Assert
    kok_a, kok_b = a["geometri"]["kok"], b["geometri"]["kok"]
    kontrol("kompakt: silindir kesit", kok_a["kesit"]["sekil"] == "silindir")
    kontrol("kompakt: yukseklik tanim yuksekligi", abs(kok_a["yukseklik"] - 0.5) < 1e-12)
    kontrol("pebble: kure kesit", kok_b["kesit"] == {"sekil": "kure", "yaricap": 3.0})
    kontrol("pebble: yukseklik yok", kok_b["yukseklik"] is None)


HIZLI = [test_triso_bolumu_gorunurluk_ve_secim_formu_doldurur,
         test_form_degisikligi_spec_e_yazilir, test_ekle_ad_degistir_ve_sil,
         test_alt_model_triso_kompakt_ve_pebble]
YAVAS = []


# ---------------------------------------------------------------------------
# varyans azaltma karti ve FOM karti
# ---------------------------------------------------------------------------

def test_varyans_formu_spec_e_yazar_ve_kapaliyken_alan_eklemez():
    print("\n[Y9-U5] varyans formu: dolduruken spec degismez; acinca ayar yazilir; kapali alan yok")
    import copy
    from arayuz.ayar.varyans_formu import VaryansFormu
    from cekirdek import varyans
    _qt()
    # Arrange
    spec = _yukle("zirh_agirlik_pencere")
    ilk = copy.deepcopy(spec)
    f = VaryansFormu()
    # Act
    f.doldur(spec)
    degisen = []
    f.degisti.connect(lambda: degisen.append(1))
    f.ag_turu.setCurrentIndex(f.ag_turu.findData("kuresel"))
    kontrol("kapaliyken degisiklik spec'e alan eklemez", "varyans" not in spec["ayarlar"])
    f.var.setChecked(True)
    f.nx.setValue(8)
    f.ny.setValue(1)
    f.nz.setValue(1)
    f.enerji.setText("0, 1e6, 2e7")
    f.enerji.editingFinished.emit()
    f.max_gerceklesme.setValue(40)
    a = varyans.ayar(spec)
    # Assert
    kontrol("doldur spec'i degistirmedi (ilk durum)", ilk["ayarlar"] == _yukle("zirh_agirlik_pencere")["ayarlar"])
    kontrol("ayar acik, kuresel, 8x1x1", a.var and a.mesh_turu == "kuresel" and a.boyut == (8, 1, 1))
    kontrol("enerji sinirlari", a.enerji_siniri == (0.0, 1e6, 2e7), "-> %r" % (a.enerji_siniri,))
    kontrol("gerceklesme 40, mod uret", a.max_gerceklesme == 40 and a.mod == "uret")
    kontrol("degisti sinyali", degisen)
    f.mod.setCurrentIndex(f.mod.findData("uygula"))
    kontrol("uygula: dosya alani etkin, ag alanlari pasif", f.dosya.isEnabled() and not f.nx.isEnabled())


def test_varyans_formu_gelismis_bolumde_ve_fom_karti_tablosu():
    print("\n[Y9-U6] Hesap ayarlari Gelismis'te varyans formu; FOM karti tablo yazar")
    from arayuz.sekme_ayar import AyarSekmesi
    from arayuz.sonuc.varyans import VaryansKarti
    from cekirdek.varyans import FomSatiri
    _qt()
    # Arrange
    s = AyarSekmesi()
    s.spec_yukle(_yukle("zirh_agirlik_pencere"))
    k = VaryansKarti()
    # Act
    k.goster([FomSatiri("aki_dedektor", 1.7e9, 1.0e8, 0.0588, 100.0, 2.9)], pencere=True)
    # Assert
    kontrol("form ayar sekmesinde", hasattr(s, "y9_formu") and s.y9_formu.parent() is not None)
    kontrol("kart gorunur", not k.isHidden())
    kontrol("tablo FOM ve tally adi", "aki_dedektor" in k.tablo.text() and "2.9" in k.tablo.text())
    kontrol("pencere notu", "analog" in k.notlar.text())
    k.goster(None)
    kontrol("None: gizli", k.isHidden())


HIZLI += [test_varyans_formu_spec_e_yazar_ve_kapaliyken_alan_eklemez,
          test_varyans_formu_gelismis_bolumde_ve_fom_karti_tablosu]
