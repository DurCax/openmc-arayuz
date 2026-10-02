# -*- coding: utf-8 -*-
"""
 test_y7_arayuz.py  --  v3 Y7: Hesap ayarlari foton/sicaklik formu, tally formunda
                        yuzey turu, Calistir sayfasinda yuzey akimi karti (offscreen)

 HIZLI: formlar spec'e yazar / spec'ten doldurur (degismeyen alan yazilmaz),
        tally turu yuzeye cevrilince skor 'current' ve yuzey filtresi, kutu
        bolmeleri/sinirlari; sonuc karti sahte sonucla tablo ve spektrum.
 YAVAS: gercek sabit kaynak kosusu diskten yuklenince kart dolu (uctan uca).
"""

import copy
import os

from cekirdek import sema
from testler.ortak_test import kontrol, ISLEM_PARCACIGI
from testler.regresyon_ortak import ORNEK, _qt


def _pin():
    return sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))


def _kure():
    return sema.yukle(os.path.join(ORNEK, "zirh_kure.json"))


def _sekme(spec):
    from arayuz.sekme_ayar import AyarSekmesi
    sekme = AyarSekmesi()
    sekme.spec_yukle(spec)
    return sekme


# ---------------------------------------------------------------------------
# foton / sicaklik formu
# ---------------------------------------------------------------------------

def test_doldurma_spec_degistirmez():
    print("\n[Y7-A1] form doldurulur, hicbir sey degismeden spec ayni kalir")
    if _qt() is None:
        return
    # Arrange
    spec = _pin()
    eski = copy.deepcopy(spec)
    # Act
    sekme = _sekme(spec)
    form = sekme.y7_formu
    # Assert
    kontrol("foton kapali, elektron ttb", not form.foton.isChecked()
            and form.elektron.currentData() == "ttb")
    kontrol("tolerans 10 K, varsayilan 293.6 K", form.tolerans.value() == 10.0
            and abs(form.varsayilan.value() - 293.6) < 1e-9)
    kontrol("spec degismedi", spec == eski)
    sekme.deleteLater()


def test_foton_formu_spec_yazar():
    print("\n[Y7-A2] foton onay kutusu ve elektron islemi spec['ayarlar']['foton']'a")
    if _qt() is None:
        return
    # Arrange
    spec = _pin()
    sekme = _sekme(spec)
    bildirim = []
    sekme.degisti.connect(bildirim.append)
    form = sekme.y7_formu
    # Act
    form.foton.setChecked(True)
    ilk = copy.deepcopy(spec["ayarlar"].get("foton"))
    form.elektron.setCurrentIndex(form.elektron.findData("led"))
    # Assert
    kontrol("acilinca yalniz var (elektron varsayilan yazilmaz)", ilk == {"var": True},
            "-> %r" % ilk)
    kontrol("led yazildi", spec["ayarlar"]["foton"] == {"var": True, "elektron": "led"})
    kontrol("bildirildi", "ayar" in bildirim)
    sekme.deleteLater()


def test_sicaklik_formu_yalniz_degisen_alan():
    print("\n[Y7-A3] sicaklik: degisen alan yazilir; aralik onay kutusuyla")
    if _qt() is None:
        return
    # Arrange
    spec = _pin()
    sekme = _sekme(spec)
    form = sekme.y7_formu
    # Act
    form.tolerans.setValue(50.0)
    form.aralik_var.setChecked(True)
    form.aralik_alt.setValue(300.0)
    form.aralik_ust.setValue(1200.0)
    form.multipole.setChecked(True)
    # Assert
    kontrol("sozluk", spec["ayarlar"]["sicaklik"] == {"tolerans": 50.0, "aralik": [300.0, 1200.0],
                                                      "multipole": True},
            "-> %r" % spec["ayarlar"].get("sicaklik"))
    form.aralik_var.setChecked(False)
    kontrol("aralik kapatilinca silinir", "aralik" not in spec["ayarlar"]["sicaklik"])
    sekme.deleteLater()


def test_form_spec_ten_doldurur():
    print("\n[Y7-A4] form dosyadaki foton ve sicaklik alanlarini gosterir (sinyalsiz)")
    if _qt() is None:
        return
    from arayuz.ayar.foton_sicaklik import FotonSicaklikFormu
    # Arrange
    form = FotonSicaklikFormu()
    sinyal = []
    form.degisti.connect(lambda: sinyal.append(1))
    spec = _pin()
    spec["ayarlar"]["foton"] = {"var": True, "elektron": "led"}
    spec["ayarlar"]["sicaklik"] = {"tolerans": 25.0, "varsayilan": 600.0, "aralik": [294, 900]}
    # Act
    form.doldur(spec)
    # Assert
    kontrol("foton led", form.foton.isChecked() and form.elektron.currentData() == "led")
    kontrol("tolerans 25, varsayilan 600", form.tolerans.value() == 25.0
            and form.varsayilan.value() == 600.0)
    kontrol("aralik 294-900", form.aralik_var.isChecked() and form.aralik_ust.value() == 900.0)
    kontrol("sinyal yok", not sinyal)
    form.deleteLater()


def test_foton_kaynaginda_not():
    print("\n[Y7-A5] foton kaynaginda tasinim zaten acik: not gorunur")
    if _qt() is None:
        return
    from arayuz.ayar.foton_sicaklik import FotonSicaklikFormu
    # Arrange
    form = FotonSicaklikFormu()
    spec = _kure()
    spec["ayarlar"]["kaynak"]["parcacik"] = "photon"
    # Act
    form.doldur(spec)
    # Assert
    kontrol("not gorunur", not form.kaynak_notu.isHidden())
    form.doldur(_pin())
    kontrol("notron kaynaginda gizli", form.kaynak_notu.isHidden())
    form.deleteLater()


# ---------------------------------------------------------------------------
# tally formu: yuzey turu
# ---------------------------------------------------------------------------

def test_tally_turu_sinira_cevrilir():
    print("\n[Y7-A6] tally turu 'model siniri': skor current, yuzey_sinir filtresi, enerji korunur")
    if _qt() is None:
        return
    from cekirdek import yuzey_akim as y
    # Arrange
    spec = _kure()
    sekme = _sekme(spec)
    sekme.tally_liste.setCurrentRow(0)
    t = spec["tallyler"][0]
    # Act
    sekme.t_tur.setCurrentIndex(sekme.t_tur.findData(y.FILTRE_SINIR))
    # Assert
    turler = [f["tur"] for f in t["filtreler"]]
    kontrol("skor current", t["skorlar"] == ["current"])
    kontrol("yuzey_sinir + enerji (malzeme kaldirildi)", turler == [y.FILTRE_SINIR, "enerji"],
            "-> %s" % turler)
    kontrol("skor listesi gizli", sekme.t_skor.isHidden() and sekme.t_set.isHidden())
    kontrol("kutu satirlari gizli", sekme.kutu_satiri.isHidden())
    sekme.deleteLater()


def test_tally_turu_kutu_ve_sinirlar():
    print("\n[Y7-A7] kutu agi: bolmeler ve elle sinirlar; bos sinir = otomatik")
    if _qt() is None:
        return
    from cekirdek import yuzey_akim as y
    # Arrange
    spec = _kure()
    sekme = _sekme(spec)
    sekme.tally_liste.setCurrentRow(1)
    t = spec["tallyler"][1]
    # Act
    sekme.t_tur.setCurrentIndex(sekme.t_tur.findData(y.FILTRE_KUTU))
    oto = copy.deepcopy(y.yuzey_filtresi(t))
    sekme.t_kutu_nx.setValue(3)
    sekme.t_kutu_alt.setText("-10, -10, -10")
    sekme.t_kutu_ust.setText("10, 10, 10")
    sekme.t_kutu_ust.editingFinished.emit()
    elle = y.yuzey_filtresi(t)
    # Assert
    kontrol("baslangic otomatik 1x1x1", oto == y.filtre_kutu([1, 1, 1]), "-> %r" % (oto,))
    kontrol("elle sinir ve 3 bolme", elle == y.filtre_kutu([3, 1, 1], [-10, -10, -10],
                                                            [10, 10, 10]), "-> %r" % (elle,))
    kontrol("kutu satiri gorunur", not sekme.kutu_satiri.isHidden())
    sekme.t_tur.setCurrentIndex(sekme.t_tur.findData(""))
    kontrol("hacme donunce yuzey filtresi kalkar, skor flux",
            not y.yuzey_tally_mi(t) and t["skorlar"] == ["flux"])
    sekme.deleteLater()


def test_gecersiz_sinir_metni_filtreyi_silmez():
    print("\n[Y7-A8] okunamayan sinir metni mevcut filtreyi bozmaz")
    if _qt() is None:
        return
    from cekirdek import yuzey_akim as y
    # Arrange
    spec = _kure()
    spec["tallyler"][0] = dict(sema.tally("k", ["current"]),
                               filtreler=[y.filtre_kutu([1, 1, 1], [-5, -5, -5], [5, 5, 5])])
    sekme = _sekme(spec)
    sekme.tally_liste.setCurrentRow(0)
    # Act
    sekme.t_kutu_alt.setText("abc")
    sekme.t_kutu_alt.editingFinished.emit()
    # Assert
    kontrol("tur kutu gosterilir", sekme.t_tur.currentData() == y.FILTRE_KUTU)
    kontrol("filtre ayni", y.yuzey_filtresi(spec["tallyler"][0])["alt"] == [-5.0, -5.0, -5.0])
    sekme.deleteLater()


# ---------------------------------------------------------------------------
# sonuc karti
# ---------------------------------------------------------------------------

def _sahte_sonuclar():
    from cekirdek.spektrum import Deger as D
    sinir = {"ad": "kacak", "tur": "yuzey_sinir", "yuzeyler": {7: D(0.25, 0.004)},
             "toplam": D(0.25, 0.004), "global_sizinti": D(0.25, 0.004),
             "spektrum": {"kenarlar": [1e-5, 0.625, 1e5, 2e7], "deger": [0.05, 0.1, 0.1],
                          "sapma": [0.001] * 3}}
    yuz = {"giren": D(0.1, 0.01), "cikan": D(0.2, 0.01)}
    kutu = {"ad": "kutu", "tur": "yuzey_kutu", "boyut": (1, 1, 1),
            "sinirlar": ([-10, -10, -10], [10, 10, 10]),
            "yuzler": {"%s-%s" % (e, u): yuz for e in "xyz" for u in ("min", "max")},
            "giren": D(0.6, 0.02), "cikan": D(1.2, 0.03), "net_cikan": D(0.6, 0.04),
            "spektrum": None, "kaynak": D(1.0, 0.0),
            "terimler": {"A": D(0.41, 0.01), "U": D(0.01, 0.001), "X": D(0.01, 0.001),
                         "nuF": D(0.0, 0.0)},
            "denge": {"artik": D(0.0, 0.03), "bagil": 0.0}}
    return [sinir, kutu]


def test_sonuc_karti_tablo_ve_spektrum():
    print("\n[Y7-A9] sonuc karti: kacak, giren/cikan, denge satiri, kacak spektrumu (log x)")
    if _qt() is None:
        return
    from arayuz.sonuc.yuzey import YuzeyKarti
    # Arrange
    kart = YuzeyKarti()
    # Act
    kart.goster(_sahte_sonuclar(), sabit=True)
    metin = kart.tablo.text()
    # Assert
    kontrol("gorunur", not kart.isHidden())
    kontrol("kacak ve global sizinti", "kacak" in metin and "2.5000e-01" in metin)
    kontrol("denge satiri", "S + J" in metin, "-> %s" % metin[:300])
    kontrol("isaret/birim notu", "kaynak parçacığı" in kart.notlar.text()
            or "1/s" in kart.notlar.text())
    kontrol("spektrum log x", kart.eksen.get_xscale() == "log")
    kart.goster(None)
    kontrol("None gizler", kart.isHidden())
    kart.deleteLater()


def test_calistir_sekmesinde_kart_sifirlanir():
    print("\n[Y7-A10] Calistir: yuzey karti gizli baslar, sifirlaninca gizlenir")
    if _qt() is None:
        return
    from arayuz.sekme_calistir import CalistirSekmesi
    # Arrange
    sekme = CalistirSekmesi()
    sekme.spec_ayarla(_kure())
    gizli = sekme.yuzey_karti.isHidden()
    sekme.yuzey_karti.goster(_sahte_sonuclar(), sabit=True)
    # Act
    sekme.sifirla()
    # Assert
    kontrol("baslangicta gizli", gizli)
    kontrol("sifirla sonrasi gizli", sekme.yuzey_karti.isHidden())
    sekme.deleteLater()


def test_gercek_kosu_diskten_yuklenir(gecici):
    print("\n[Y7-AY1] zirh_kure kosusu (yuzey tally'leri) diskten yuklenince kart dolu")
    if _qt() is None:
        return
    from cekirdek import kurucu, yuzey_akim as y
    from arayuz.sekme_calistir import CalistirSekmesi
    # Arrange
    spec = _kure()
    spec["ayarlar"].update(parcacik=1000, cevrim=3)
    spec["tallyler"] = [
        dict(sema.tally("kacak", ["current"]),
             filtreler=[y.filtre_sinir(), sema.filtre_enerji([1e-5, 0.625, 1e5, 2e7])]),
        dict(sema.tally("kutu", ["current"]),
             filtreler=[y.filtre_kutu([1, 1, 1], [-10, -10, -10], [10, 10, 10])])]
    dizin = os.path.join(gecici, "kosu")
    os.makedirs(dizin)
    eski = os.getcwd()
    os.chdir(dizin)
    try:
        kurucu.kur(spec)[0].run(threads=ISLEM_PARCACIGI, output=False)
    finally:
        os.chdir(eski)
    sekme = CalistirSekmesi()
    sekme.spec_ayarla(spec)
    # Act
    yuklendi = sekme.kosu_dizinini_yukle(dizin)
    # Assert
    kart = sekme.yuzey_karti
    kontrol("kosu yuklendi", yuklendi)
    kontrol("kart gorunur, iki tally", not kart.isHidden() and len(kart.sonuclar) == 2)
    kontrol("denge satiri tabloda", "S + J" in kart.tablo.text())
    kontrol("y7_denge tally metnine girmez", "y7_" not in sekme.sonuc_metin.toPlainText())
    sekme.deleteLater()


HIZLI = [test_doldurma_spec_degistirmez, test_foton_formu_spec_yazar,
         test_sicaklik_formu_yalniz_degisen_alan, test_form_spec_ten_doldurur,
         test_foton_kaynaginda_not, test_tally_turu_sinira_cevrilir,
         test_tally_turu_kutu_ve_sinirlar, test_gecersiz_sinir_metni_filtreyi_silmez,
         test_sonuc_karti_tablo_ve_spektrum, test_calistir_sekmesinde_kart_sifirlanir]
YAVAS = [test_gercek_kosu_diskten_yuklenir]
