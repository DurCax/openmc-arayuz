# -*- coding: utf-8 -*-
"""
 test_q_duzeltme.py  --  v3 Q duzeltmeleri (Q1 ogrenci QA + Q2 profesor denetimi)

   [Q-D3]  atik sinifi: tablo nuklidi yoksa (taze yakit) "uygulanamaz", varsa OpenMC sinifi
   [Q-D5]  dal: tukenmede kritik arama aciksa not; kapaliysa yok
   [Q-D6]  dal tablosu: drho = 1/k_taban - 1/k (kosu_gecmisi.k_farki ile ayni)
   [Q-Q1b] tam kor: haritadaki ic ice demet adima sigmiyorsa adim onerisi; bos harita mesaji
   [Q-Q1c] Zr96 "probability table" uyarisi icin aciklama satiri
   [Q-Q1d] EN: yeni sablonun varsayilan cubuk/demet adlari Ingilizce, TR'de degismez
   [Q-Q1e] onizleme degisince kapi_degisti sinyali (Calistir kapisi yeniden okunur)
"""

import copy
import os

from testler.ortak_test import ORNEK, kontrol


def test_atik_sinifi_uygulanamaz_ve_tablo_nuklidi():
    print("\n[Q-D3] atik sinifi: tablo nuklidi yoksa 'uygulanamaz'")
    import openmc
    from cekirdek import tukenme_cikti
    taze = openmc.Material()
    taze.add_nuclide("U235", 0.03)
    taze.add_nuclide("U238", 0.97)
    taze.add_nuclide("O16", 2.0)
    taze.set_density("g/cm3", 10.4)
    kontrol("taze UO2 -> uygulanamaz",
            tukenme_cikti.atik_sinifi(taze) == tukenme_cikti.ATIK_UYGULANAMAZ)
    sezyum = openmc.Material()
    sezyum.add_nuclide("Cs137", 1.0)
    sezyum.set_density("g/cm3", 1.0)
    sinif = tukenme_cikti.atik_sinifi(sezyum)
    kontrol("Cs-137 (tablo nuklidi) -> bir sinif, 'uygulanamaz' degil",
            sinif in ("Class A", "Class B", "Class C", "GTCC"), repr(sinif))


def test_dal_kritik_arama_notu_ve_reaktivite_sutunu():
    print("\n[Q-D5/D6] dal: kritik arama notu; drho sutunu")
    from cekirdek import dal, kosu_gecmisi, sema
    s = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    s["tukenme"]["kritik_arama"] = {"var": False}
    kontrol("arama kapali: not yok", dal.kritik_arama_notu(s) is None)
    s["tukenme"]["kritik_arama"] = {"var": True, "tur": "bor", "hedef": "su"}
    kontrol("arama acik: not var", bool(dal.kritik_arama_notu(s)))
    kf = kosu_gecmisi.k_farki(1.3643, 0.0056, 1.2895, 0.0042)
    rho = (1.0 / 1.3643 - 1.0 / 1.2895) * 1e5
    kontrol("bor 500 ppm: drho ~ -4250 pcm (-8.5 pcm/ppm)",
            abs(kf.rho_fark_pcm - rho) < 1e-6 and -4300 < rho < -4200, "%.0f" % rho)


def _tam_kor_spec():
    from cekirdek import sema
    from arayuz import baslangic
    s = baslangic.bos_sablon("tam_kor")
    s["kor"]["adim"] = sema.VARSAYILAN_KOR["adim"]       # ogrencinin bos varsayilani 1.26
    return s


def test_demet_adim_onerisi_ve_bos_harita_mesaji():
    print("\n[Q-Q1b] tam kor: demet adimi onerisi; bos harita mesaji")
    from cekirdek import sema
    from cekirdek.dogrula import geometri as dg
    from cekirdek.geometri import sablon
    s = _tam_kor_spec()
    oneri = dg.demet_adim_onerisi(s)
    d = s["demetler"][0]
    beklenen = d["adim"] * d["boyut"][0]
    kontrol("oneri = demetin dis olcusu", oneri is not None and abs(oneri - beklenen) < 1e-9,
            repr(oneri))
    bos = copy.deepcopy(s)
    bos["kor"].update(harita=[], anahtar={}, boyut=[1, 1])
    kontrol("bos harita: oneri yok", dg.demet_adim_onerisi(bos) is None)
    try:
        sablon._kare_kafes(bos, bos["kor"])
        mesaj = ""
    except ValueError as e:
        mesaj = str(e)
    kontrol("bos harita: anlasilir mesaj ('0 satir' degil)", "boş" in mesaj and "0 satır" not in mesaj,
            repr(mesaj))
    kontrol("sema varsayilan adim 1.26", sema.VARSAYILAN_KOR["adim"] == 1.26)


def test_probability_table_notu():
    print("\n[Q-Q1c] Zr96 probability table uyarisi icin aciklama")
    from cekirdek.uygunluk_denetimi import ayristir
    ozet = ayristir.CiktiOzeti(
        log_var=True,
        uyarilar=("Negative value(s) found on probability table for nuclide Zr96 at 600K",))
    satirlar = ayristir.ozet_satirlari(ozet)
    kontrol("uyari satiri + aciklama notu", len(satirlar) == 3 and "Not:" in satirlar[-1],
            repr(satirlar))
    digeri = ayristir.CiktiOzeti(log_var=True, uyarilar=("baska uyari",))
    kontrol("baska uyarida not yok", len(ayristir.ozet_satirlari(digeri)) == 2)


def test_en_varsayilan_adlar_tr_degismez():
    print("\n[Q-Q1d] yeni sablon adlari: EN fuel_pin, TR yakit_cubugu")
    from cekirdek import ceviri
    from arayuz import baslangic
    tr = baslangic.bos_sablon("tam_kor")
    kontrol("TR: yakit_cubugu", "yakit_cubugu" in [c["ad"] for c in tr["cubuklar"]])
    eski = ceviri.etkin_dil()
    ceviri.dil_ayarla("en")
    try:
        en = baslangic.bos_sablon("tam_kor")
    finally:
        ceviri.dil_ayarla(eski)
    adlar = [c["ad"] for c in en["cubuklar"]]
    kontrol("EN: fuel_pin, guide_tube", "fuel_pin" in adlar and "guide_tube" in adlar, repr(adlar))
    d = en["demetler"][0]
    kontrol("EN: demet adi ve kor anahtari tutarli",
            d["ad"] == "assembly_17x17" and d["ad"] in en["kor"]["anahtar"].values()
            and set(d["anahtar"].values()) <= set(adlar), repr(d["ad"]))
    from cekirdek import dogrula
    kontrol("EN sablon: dogrulama hatasi yok",
            not [b for b in dogrula.tum_kontroller(en, veri_kontrolu=False) if b.seviye == "hata"])


def test_onizleme_kapi_degisti_sinyali(qapp=None):
    print("\n[Q-Q1e] onizleme.iste() kapi_degisti yayar")
    from PySide6 import QtWidgets
    from arayuz.onizleme import OnizlemeWidget as Onizleme
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    o = Onizleme()
    sayac = []
    o.kapi_degisti.connect(lambda: sayac.append(1))
    o.iste()
    kontrol("iste() sinyal yayar", len(sayac) == 1)
    o.deleteLater()
    del uyg


HIZLI = [test_atik_sinifi_uygulanamaz_ve_tablo_nuklidi,
         test_dal_kritik_arama_notu_ve_reaktivite_sutunu,
         test_demet_adim_onerisi_ve_bos_harita_mesaji, test_probability_table_notu,
         test_en_varsayilan_adlar_tr_degismez, test_onizleme_kapi_degisti_sinyali]
