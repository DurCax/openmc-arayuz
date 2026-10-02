# -*- coding: utf-8 -*-
"""
 test_k5_alt_model.py  --  v3 K5: tek parca / demet / dugum alt modeli
                           (cekirdek/alt_model.py; saf, K4 de kullanir)

 Alt model gercekten kurulur (kurucu.kur) ve geometrideki malzemeler
 openmc'nin kendisinden okunur: beklenen malzemeler var, kapsam disi yok;
 butun dis sinirlar yansitici; girdi spec degismez.
"""

import copy
import os

from testler.ortak_test import kontrol, ORNEK


def _spec(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


class _Kurulu:
    """kurucu.kur sonucu: model + spec adlariyla malzeme nesneleri."""

    def __init__(self, spec):
        from cekirdek import kurucu
        self.model, bilgi = kurucu.kur(spec)
        self.ad = {id(m): ad for ad, m in bilgi["malzemeler"].items()}


def _kur(spec):
    return _Kurulu(spec)


def _malzemeler(kurulu):
    """Geometride GERCEKTEN kullanilan malzemelerin spec adlari."""
    return {kurulu.ad[id(m)] for m in kurulu.model.geometry.get_all_materials().values()}


def _sinir_turleri(kurulu):
    return {s.boundary_type for s in kurulu.model.geometry.get_all_surfaces().values()
            if s.boundary_type != "transmission"}


def test_cubuk_alt_modeli_yalniz_pinin_malzemeleri():
    print("\n[K5A-1] cubuk alt modeli: yalniz pinin malzemeleri, yansitici sinir, girdi degismez")
    from cekirdek import alt_model as am
    # Arrange
    spec = _spec("pwr_beavrs_kor")
    once = copy.deepcopy(spec)
    # Act
    alt = am.parca_alt_modeli(spec, "cubuk", "yakit_a")
    model = _kur(alt)
    # Assert
    kontrol("tek cubuk sablonu", alt["kor"]["tur"] == "tek_cubuk" and alt["kor"]["cubuk"] == "yakit_a")
    kontrol("malzemeler = pinin malzemeleri",
            _malzemeler(model) == {"uo2_a", "helyum", "zirkaloy4", "su_borlu"},
            "-> %s" % _malzemeler(model))
    kontrol("malzeme listesi budandi (kapsam disi malzeme yok)",
            {m["ad"] for m in alt["malzemeler"]} == {"uo2_a", "helyum", "zirkaloy4", "su_borlu"})
    kontrol("adim demetin adimi (1.25984 cm)", abs(alt["kor"]["adim"] - 1.25984) < 1e-12)
    kontrol("dis sinirlar yalniz yansitici", _sinir_turleri(model) == {"reflective"},
            "-> %s" % _sinir_turleri(model))
    kontrol("tally / guc / tukenme kapali",
            not alt["tallyler"] and not alt["guc_dagilimi"]["var"] and not alt["tukenme"]["var"])
    kontrol("girdi spec degismedi", spec == once)


def test_demet_alt_modeli_kapsam_disi_malzeme_yok():
    print("\n[K5A-2] demet alt modeli: demetin pinleri var, diger demetlerin yakiti yok")
    from cekirdek import alt_model as am
    spec = _spec("pwr_beavrs_kor")
    alt = am.parca_alt_modeli(spec, "demet", "dc_6s")
    mal = _malzemeler(_kur(alt))
    kontrol("tek demet sablonu", alt["kor"]["tur"] == "tek_demet" and alt["kor"]["demet"] == "dc_6s")
    kontrol("pyrex (demetin emici cubugu) var", "pyrex" in mal, "-> %s" % mal)
    kontrol("baska zenginlikler yok", not mal & {"uo2_a", "uo2_b"}, "-> %s" % mal)
    kontrol("yansitici yok", alt["kor"]["yansitici"]["var"] is False)
    kontrol("demet kutuphanesi budandi", [d["ad"] for d in alt["demetler"]] == ["dc_6s"])


def test_altigen_demet_alt_modeli_kurulur():
    print("\n[K5A-3] altigen demet (SFR) alt modeli kurulur, yansitici altigen sinir")
    from cekirdek import alt_model as am
    spec = _spec("sfr_met1000_kor")
    alt = am.parca_alt_modeli(spec, "demet", "surucu_ic1")
    model = _kur(alt)
    mal = _malzemeler(model)
    kontrol("surucu demetin malzemeleri", "yakit_ic1" in mal and not mal & {"yakit_ic2", "b4c"},
            "-> %s" % mal)
    kontrol("sinirlar yansitici", _sinir_turleri(model) == {"reflective"})


def test_plaka_alt_modeli():
    print("\n[K5A-4] plaka alt modeli: yansitici ve grafit kapsam disi")
    from cekirdek import alt_model as am
    alt = am.parca_alt_modeli(_spec("mtr_kor"), "plaka", "mtr_eleman")
    mal = _malzemeler(_kur(alt))
    kontrol("tek plaka", alt["kor"]["tur"] == "tek_plaka")
    kontrol("plaka malzemeleri", mal == {"u3si2_al", "al6061", "su"}, "-> %s" % mal)


def test_tambur_alt_modeli_gelismis():
    print("\n[K5A-5] tambur alt modeli (gelismis): yalniz govde + emici")
    from cekirdek import alt_model as am
    spec = _spec("kafes_tamburlu_yansitici")
    alt = am.parca_alt_modeli(spec, "tambur", "tambur_b4c")
    model = _kur(alt)
    kontrol("gelismis kipte tek kok", alt["kor"]["tur"] == "agac")
    kontrol("tambur malzemeleri", _malzemeler(model) == {"berilyum", "b4c"},
            "-> %s" % _malzemeler(model))
    kontrol("sinirlar yansitici", _sinir_turleri(model) == {"reflective"})


def test_dugum_alt_modeli():
    print("\n[K5A-6] dugum alt modeli: kafes dugumu tamburlari dislar; kok/malzeme -> tam model")
    from cekirdek import alt_model as am
    spec = _spec("kafes_tamburlu_yansitici")
    alt = am.dugum_alt_modeli(spec, ("kok", "ic"))
    model = _kur(alt)
    mal = _malzemeler(model)
    kontrol("kafes dugumu: yakit var, emici tambur yok", "uo2_24" in mal and "b4c" not in mal,
            "-> %s" % mal)
    kontrol("kafes dugumu: sinir yansitici", _sinir_turleri(model) == {"reflective"})
    kontrol("kok dugumu -> None (tam kor)", am.dugum_alt_modeli(spec, ("kok",)) is None)
    kontrol("bos yol -> None", am.dugum_alt_modeli(spec, ()) is None)
    kontrol("halka icerigi malzeme -> None",
            am.dugum_alt_modeli(spec, ("kok", "halkalar", 0, "icerik")) is None)
    yerlesim = am.dugum_alt_modeli(spec, ("kok", "halkalar", 0, "yerlesimler", 0))
    kontrol("tambur yerlesimi -> tamburun alt modeli",
            yerlesim is not None and _malzemeler(_kur(yerlesim)) == {"berilyum", "b4c"})
    harf = am.dugum_alt_modeli(spec, ("kok", "ic", "anahtar", "A"))
    kontrol("kafes harfi (bilesen) -> demetin alt modeli",
            harf is not None and harf["kor"]["demet"] == "demet_24")
    kontrol("sablon modunda dugum -> None", am.dugum_alt_modeli(_spec("pwr_17x17"), ("kok", "ic"))
            is None)


def test_yukseklik_ve_k4_iki_boyutlu():
    print("\n[K5A-7] 3B modelde alt model 3B kalir; K4 icin 2B tek demet istenebilir")
    from cekirdek import alt_model as am, sema
    spec = _spec("pwr_3b")
    pin = am.parca_alt_modeli(spec, "cubuk", "yakit_cubugu")
    kontrol("3B modelde pin alt modeli ayni yukseklik",
            sema.model_yuksekligi(pin) == sema.model_yuksekligi(spec))
    demet = am.demet_alt_modeli(spec, "demet_17x17", uc_boyutlu=False)
    kontrol("2B tek demet (k-sonsuz)", sema.model_yuksekligi(demet) is None
            and demet["kor"]["tur"] == "tek_demet")
    kontrol("kontrol cubugu 3B modelde kurulur",
            "b4c" in _malzemeler(_kur(am.parca_alt_modeli(_spec("pwr_kontrol"), "cubuk",
                                                           "kontrol_cubugu"))))


def test_tanimsiz_ad_hatasi():
    print("\n[K5A-8] tanimsiz parca / bilinmeyen tur: AltModelHatasi (acik mesaj)")
    from cekirdek import alt_model as am
    spec = _spec("pwr_17x17")
    for tur, ad in (("cubuk", "yok_boyle"), ("demet", "yok"), ("plaka", "x"), ("tambur", "t"),
                    ("bilinmez", "yakit_cubugu")):
        try:
            am.parca_alt_modeli(spec, tur, ad)
        except am.AltModelHatasi as e:
            kontrol("%s %s: hata mesaji adi icerir" % (tur, ad), ad in str(e) or tur in str(e),
                    "-> %s" % e)
        else:
            kontrol("%s %s: hata bekleniyordu" % (tur, ad), False)


def test_kutuphanede_kullanilmayan_pin_adimi():
    print("\n[K5A-9] demette kullanilmayan pin: adim dis yaricaptan (paylı), pin sigar")
    from cekirdek import alt_model as am
    spec = _spec("pwr_17x17")
    spec["demetler"] = []
    spec["kor"]["tur"] = "tek_cubuk"
    alt = am.parca_alt_modeli(spec, "cubuk", "yakit_cubugu")
    r_dis = max(b["r"] for b in spec["cubuklar"][0]["bolgeler"] if b.get("r"))
    kontrol("adim > pin capi", alt["kor"]["adim"] > 2 * r_dis, "-> %s" % alt["kor"]["adim"])
    kontrol("kurulur", "uo2" in _malzemeler(_kur(alt)))


HIZLI = [test_cubuk_alt_modeli_yalniz_pinin_malzemeleri, test_demet_alt_modeli_kapsam_disi_malzeme_yok,
         test_altigen_demet_alt_modeli_kurulur, test_plaka_alt_modeli, test_tambur_alt_modeli_gelismis,
         test_dugum_alt_modeli, test_yukseklik_ve_k4_iki_boyutlu, test_tanimsiz_ad_hatasi,
         test_kutuphanede_kullanilmayan_pin_adimi]
YAVAS = []
