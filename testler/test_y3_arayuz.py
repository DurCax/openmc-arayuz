# -*- coding: utf-8 -*-
"""
 test_y3_arayuz.py  --  v3 Y3: Hesap ayarlari "Spektrum ve dört faktör" karti ve
                        Calistir sayfasindaki sonuc karti (offscreen)

 HIZLI: ayar karti spec'e yazar / spec'ten doldurur; sonuc karti sahte sonucla
        tablo, varsayim notlari ve log-log grafik; Y3 sonucu yokken gizli.
 YAVAS: gercek pin hucre kosusu diskten yuklenince kart gorunur (uctan uca).
"""

import os

import numpy as np

from cekirdek import sema
from testler.ortak_test import kontrol, ISLEM_PARCACIGI
from testler.regresyon_ortak import ORNEK, _qt


def _pin(var=False):
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    if var:
        spec["ayarlar"]["spektrum"] = {"var": True, "grup_yapisi": "CASMO-70"}
    return spec


def _sahte_sonuc(sizinti=0.0, ozdeger=True):
    from cekirdek import spektrum as s
    d = s.Deger
    h = {"nF": d(1.36, 0.004), "A": d(1.0, 0.003), "X": d(0.0014, 0.0001),
         "nF_th": d(1.11, 0.004), "A_th": d(0.654, 0.002), "A_yakit_th": d(0.607, 0.002),
         "L": d(sizinti, 0.001 if sizinti else 0.0)}
    kenar = np.geomspace(1e-5, 2e7, 71)
    aki = np.ones(70)
    return {"faktorler": s.faktorleri_hesapla(h) if ozdeger else None,
            "indeksler": s.indeksleri_hesapla({k: d(v, v / 100) for k, v in (
                ("F25_th", 0.457), ("F25_epi", 0.0701), ("F28_th", 5e-7),
                ("F28_epi", 0.0289), ("C28_th", 0.0709), ("C28_epi", 0.198))}),
            "spektrum": {"kenarlar": kenar, "model": (aki, aki * 0.01),
                         "yakit": (aki * 0.8, aki * 0.01)},
            "keff": d(1.3614, 0.0021) if ozdeger else None, "sizinti": d(sizinti, 0.0),
            "termal_fisyon_payi": 0.8, "termal_kesim": 0.625}


def test_ayar_karti_spec_yazar():
    print("\n[Y3-A1] ayar karti: onay kutusu ve grup yapisi spec['ayarlar']['spektrum']'a")
    if _qt() is None:
        return
    from arayuz.sekme_ayar import AyarSekmesi
    # Arrange
    sekme = AyarSekmesi()
    spec = _pin()
    sekme.spec_yukle(spec)
    bildirimler = []
    sekme.degisti.connect(bildirimler.append)
    kart = sekme.spektrum_karti
    # Act
    kontrol("baslangicta kapali, grup kutusu pasif",
            not kart.var.isChecked() and not kart.grup.isEnabled())
    kart.var.setChecked(True)
    kart.grup.setCurrentIndex(kart.grup.findData("SHEM-361"))
    # Assert
    kontrol("spec yazildi", spec["ayarlar"]["spektrum"] == {"var": True,
                                                            "grup_yapisi": "SHEM-361"},
            "-> %s" % spec["ayarlar"].get("spektrum"))
    kontrol("degisti('ayar') yayildi", "ayar" in bildirimler)
    kontrol("grup kutusu etkin", kart.grup.isEnabled())
    sekme.deleteLater()


def test_ayar_karti_doldurur_ve_gecersizi_duzeltir():
    print("\n[Y3-A2] ayar karti: spec'ten doldurur (sinyalsiz); gecersiz grup varsayilana")
    if _qt() is None:
        return
    from arayuz.ayar.spektrum_karti import SpektrumAyarKarti
    # Arrange
    kart = SpektrumAyarKarti()
    sinyal = []
    kart.degisti.connect(lambda: sinyal.append(1))
    spec = _pin()
    spec["ayarlar"]["spektrum"] = {"var": True, "grup_yapisi": "CCFE-709"}
    # Act
    kart.doldur(spec)
    # Assert
    kontrol("onay ve grup spec'ten", kart.var.isChecked()
            and kart.grup.currentData() == "CCFE-709")
    kontrol("doldurma sinyal yaymaz", not sinyal)
    spec["ayarlar"]["spektrum"] = {"var": True, "grup_yapisi": "BOZUK"}
    kart.doldur(spec)
    kontrol("gecersiz grup -> varsayilan XMAS-172, kapali",
            kart.grup.currentData() == "XMAS-172" and not kart.var.isChecked())
    kart.deleteLater()


def test_sonuc_karti_tablo_ve_notlar():
    print("\n[Y3-A3] sonuc karti: tablo (ε … C*), k∞ etiketi, varsayim notlari, grafik")
    if _qt() is None:
        return
    from arayuz.sonuc.spektrum import SpektrumKarti, tablo_satirlari, varsayim_notlari
    # Arrange
    kart = SpektrumKarti()
    sonuc = _sahte_sonuc()
    # Act
    kart.goster(sonuc, sonsuz=True)
    satirlar = tablo_satirlari(sonuc, True)
    # Assert
    semboller = [s for s, _a, _t, _d in satirlar]
    kontrol("kart gorunur (isHidden degil)", not kart.isHidden())
    kontrol("faktor ve indeks satirlari", all(x in semboller for x in
            ("ε", "p", "f", "η", "ε·p·f·η", "c_xn", "P_NL", "k∞", "ρ28", "δ25", "δ28", "C*")),
            "-> %s" % semboller)
    kontrol("tabloda deger metni", "± " in kart.tablo.text())
    notlar = " ".join(varsayim_notlari(sonuc, True))
    kontrol("termal kesim ve korelasyon notu", "0.625" in notlar and "korelasyon" in notlar)
    kontrol("sizintisizda P_FNL notu yok", "P_FNL" not in notlar)
    kontrol("grafik log-log", kart.eksen.get_xscale() == "log"
            and kart.eksen.get_yscale() == "log")
    kontrol("iki egri (model, yakit)", len(kart.eksen.patches) >= 2 or
            len(kart.eksen.get_legend().get_texts()) == 2)
    kart.deleteLater()


def test_sonuc_karti_sizinti_ve_sabit_kaynak():
    print("\n[Y3-A4] sizintida k-eff etiketi + P_FNL notu; sabit kaynakta yalniz spektrum")
    if _qt() is None:
        return
    from arayuz.sonuc.spektrum import SpektrumKarti, tablo_satirlari, varsayim_notlari
    # Arrange
    sizan, sabit = _sahte_sonuc(sizinti=0.3), _sahte_sonuc(ozdeger=False)
    # Act
    s_sat = [s for s, _a, _t, _d in tablo_satirlari(sizan, False)]
    notlar = " ".join(varsayim_notlari(sizan, False))
    sabit_sat = [s for s, _a, _t, _d in tablo_satirlari(sabit, True)]
    # Assert
    kontrol("sizintida k-eff", "k-eff" in s_sat and "k∞" not in s_sat)
    kontrol("P_FNL ayri verilmez notu", "P_FNL" in notlar)
    kontrol("sabit kaynakta faktor yok, indeks var", "ε" not in sabit_sat and "ρ28" in sabit_sat)
    kontrol("sabit kaynak notu", "Sabit kaynak" in " ".join(varsayim_notlari(sabit, True)))
    kart = SpektrumKarti()
    kart.goster(sabit)
    kart.goster(None)
    kontrol("goster(None) karti gizler", kart.isHidden())
    kart.deleteLater()


def test_calistir_sekmesinde_kart_gizli_baslar():
    print("\n[Y3-A5] Calistir sekmesi: kart var, sonuc yokken gizli; statepoint yoksa gizli")
    if _qt() is None:
        return
    from arayuz.sekme_calistir import CalistirSekmesi
    # Arrange
    sekme = CalistirSekmesi()
    sekme.spec_ayarla(_pin(var=True))
    # Act
    sekme.sifirla()
    sekme.spektrum_karti.sonuc_ayarla(None)
    # Assert
    kontrol("spektrum_karti ozniteligi", hasattr(sekme, "spektrum_karti"))
    kontrol("sonucsuz gizli", sekme.spektrum_karti.isHidden())
    sekme.deleteLater()


def test_y3siz_statepoint_karti_gizler():
    print("\n[Y3-A6] Y3 tally'si olmayan gercek statepoint: oku() None, kart gizli (hata yok)")
    if _qt() is None:
        return
    import glob
    from cekirdek import spektrum
    from arayuz.sonuc.spektrum import SpektrumKarti
    from testler.ortak_test import KOK
    # Arrange
    sp = sorted(glob.glob(os.path.join(KOK, "testler", "veri", "kosu_ornek", "statepoint.*.h5")))[-1]
    kart = SpektrumKarti()
    kart.goster(_sahte_sonuc())
    # Act
    sonuc = spektrum.oku(sp)
    kart.sonuc_ayarla(sp)
    # Assert
    kontrol("oku() None", sonuc is None)
    kontrol("kart gizli", kart.isHidden())
    kart.deleteLater()


def test_gercek_kosu_diskten_yuklenir(gecici):
    print("\n[Y3-AY1] pin hucre kosusu (spektrum acik) diskten yuklenince kart dolu")
    if _qt() is None:
        return
    from cekirdek import kurucu
    from arayuz.sekme_calistir import CalistirSekmesi
    # Arrange
    spec = _pin(var=True)
    spec["ayarlar"].update(parcacik=1000, cevrim=20, pasif=5)
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
    kart = sekme.spektrum_karti
    kontrol("kosu yuklendi", yuklendi)
    kontrol("kart gorunur ve sonuc dolu", not kart.isHidden() and kart.sonuc is not None)
    kontrol("tablo k∞ (yansitici pin)", "k∞" in kart.tablo.text())
    kontrol("y3 tally'leri kullanici tally metnine girmez", "y3_" not in sekme.sonuc_metin.toPlainText())
    sekme.deleteLater()


HIZLI = [test_ayar_karti_spec_yazar, test_ayar_karti_doldurur_ve_gecersizi_duzeltir,
         test_sonuc_karti_tablo_ve_notlar, test_sonuc_karti_sizinti_ve_sabit_kaynak,
         test_calistir_sekmesinde_kart_gizli_baslar, test_y3siz_statepoint_karti_gizler]
YAVAS = [test_gercek_kosu_diskten_yuklenir]
