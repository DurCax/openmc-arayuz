# -*- coding: utf-8 -*-
"""
 test_k3_tukenme_guc.py  --  v3 K3: tukenmede adim basina pin gucu
                              (cekirdek/tukenme_guc.py)

   [TG1] Adim dosyalari: openmc_simulation_n<i>.h5 SAYISAL sirayla (n10, n9'dan
         sonra); sonuc dosyasindan fazla (eski kosudan kalan) adim yok sayilir
         ve not dusulur.
   [TG2] Fixture'da adim basina tablo: 3 adim (0, 2, 10 gun), her adimda 24
         pin; tablo = o adimin haritasi; Σ W = adimin kaynak gucu × hedef payi;
         korunum < 1e-6; F_ΔH/F_q adim basina.
   [TG3] Seriler: secili pin icin (yanma, bagil, σ, q′); F_ΔH/F_q serisi.
   [TG4] CSV (adim × pin): baslik + 3 × 24 satir; adim, gun, MWd/kg sutunlari;
         ondalik nokta.
   [TG5] Olcum spec'i: guc tally'si kurulabilen modelde tukenme kosusu guc
         dagilimini acar (tukenme.adim_gucu = false kapatir); pin hucrede
         degismez; girdi spec degismez.
   [TG6] tukenme.calistir onceki kosunun adim statepoint'lerini siler (eski
         adim yeni sonuca karismasin) -- transport KOSULMAZ (sahte operator).
   [TG7] Guc tally'si olmayan adim: tablo yok, hata metni (sessiz degil).

 Fixture: testler/veri/tukenme_guc_ornek (uret.py; Monte Carlo KOSULMAZ).
"""

import copy
import csv
import io
import json
import os
import shutil

from testler.ortak_test import KOK, ORNEK, kontrol

FIXTURE = os.path.join(KOK, "testler", "veri", "tukenme_guc_ornek")


def _spec():
    with open(os.path.join(FIXTURE, "tukenme_spec.json"), encoding="utf-8") as f:
        return json.load(f)


def _oku():
    from cekirdek import tukenme_guc
    return tukenme_guc.adim_gucleri(FIXTURE, _spec())


def test_adim_dosyalari(gecici):
    print("\n[TG1] adim dosyalari sayisal sirayla; eski adimlar yok sayilir")
    from cekirdek import tukenme_guc
    for i in (0, 1, 2, 9, 10):
        open(os.path.join(gecici, "openmc_simulation_n%d.h5" % i), "w").close()
    open(os.path.join(gecici, "openmc_simulation_nX.h5"), "w").close()
    adimlar = [i for i, _y in tukenme_guc.adim_dosyalari(gecici)]
    kontrol("0, 1, 2, 9, 10 (sayisal sira; bozuk ad yok sayilir)", adimlar == [0, 1, 2, 9, 10],
            "-> %r" % adimlar)
    kontrol("dizin yoksa bos liste", tukenme_guc.adim_dosyalari(os.path.join(gecici, "yok")) == [])
    # fixture'a fazladan (eski) bir adim kopyala: sonuc dosyasi 3 zaman noktasi
    kopya = os.path.join(gecici, "fx")
    shutil.copytree(FIXTURE, kopya)
    shutil.copy(os.path.join(kopya, "openmc_simulation_n2.h5"),
                os.path.join(kopya, "openmc_simulation_n3.h5"))
    s = tukenme_guc.adim_gucleri(kopya, _spec())
    kontrol("sonuctan fazla adim yok sayilir (3 adim) ve not dusulur",
            len(s["adimlar"]) == 3 and any("3" in n for n in s["notlar"]), "-> %r" % (s["notlar"],))


def test_adim_basina_tablo():
    print("\n[TG2] fixture: adim basina pin tablosu")
    from cekirdek import guc_tablo
    s = _oku()
    adimlar = s["adimlar"]
    kontrol("3 adim: 0, 2, 10 gun", [a["zaman_d"] for a in adimlar] == [0.0, 2.0, 10.0],
            "-> %r" % [a["zaman_d"] for a in adimlar])
    kontrol("yanma = 40 W/g × gun / 1000",
            [round(a["yanma"], 12) for a in adimlar] == [0.0, 0.08, 0.4])
    for a in adimlar:
        f = a["guc"]["faktorler"]
        tablo = a["tablo"]
        kontrol("adim %d: 24 pin, tablo = harita" % a["adim"],
                len(tablo) == 24 and all((r["bagil"], r["sigma"]) == f["bagil"][r["anahtar"]]
                                         for r in tablo))
        toplam = guc_tablo.tablo_toplami(tablo)
        beklenen = a["kaynak_W"] * a["guc"]["hedef_payi"]
        kontrol("adim %d: Σ W = kaynak gucu × hedef payi" % a["adim"],
                abs(toplam / beklenen - 1.0) < 1e-12, "-> %.6g / %.6g" % (toplam, beklenen))
        kontrol("adim %d: korunum < 1e-6" % a["adim"], a["guc"]["korunum"] < 1e-6)
        kontrol("adim %d: F_ΔH ve F_q tanimli (3B)" % a["adim"],
                f["F_dH"] > 1.0 and f["F_q"] > f["F_dH"])
    kontrol("kaynak gucu = 40 W/g × agir metal (185.5 kW)",
            abs(adimlar[0]["kaynak_W"] - 185540.77) < 1.0, "-> %r" % adimlar[0]["kaynak_W"])
    kontrol("q′ paydasi 40 cm", abs(adimlar[0]["yukseklik"] - 40.0) < 1e-9)


def test_seriler():
    print("\n[TG3] secili pin ve tepe faktoru serileri")
    from cekirdek import guc_tablo, tukenme_guc
    s = _oku()
    sicak = s["adimlar"][0]["guc"]["faktorler"]["sicak_cubuk"]
    seri = tukenme_guc.pin_serisi(s, sicak)
    kontrol("3 nokta", len(seri) == 3)
    beklenen = [guc_tablo.satir_bul(a["tablo"], sicak) for a in s["adimlar"]]
    kontrol("seri degerleri adim tablolariyla ayni",
            all(p["yanma"] == a["yanma"] and p["bagil"] == r["bagil"] and p["q"] == r["q"]
                for p, a, r in zip(seri, s["adimlar"], beklenen)))
    fs = tukenme_guc.faktor_serisi(s)
    kontrol("F serisi adim basina F_ΔH, F_q",
            [x["F_dH"] for x in fs] == [a["guc"]["faktorler"]["F_dH"] for a in s["adimlar"]]
            and all(x["F_q"] for x in fs))
    kontrol("bilinmeyen pin: bos seri", tukenme_guc.pin_serisi(s, ("yok",)) == [])


def test_csv():
    print("\n[TG4] CSV adim × pin")
    from cekirdek import tukenme_guc
    s = _oku()
    satirlar = list(csv.reader(io.StringIO(tukenme_guc.csv_metni(s))))
    kontrol("baslik + 72 satir", len(satirlar) == 73, "-> %d" % len(satirlar))
    b = satirlar[0]
    kontrol("ilk sutunlar adim, gun, MWd/kg (sabit anahtar)",
            b[:3] == ["adim", "zaman_gun", "yanma_MWd_kg"],
            "-> %r" % b[:4])
    son = satirlar[-1]
    kontrol("son satir adim 2, 10 gun", son[0] == "2" and float(son[1]) == 10.0)
    kontrol("ozet CSV: adim basina F_ΔH, F_q",
            len(list(csv.reader(io.StringIO(tukenme_guc.faktor_csv_metni(s))))) == 4)


def test_olcum_spec():
    print("\n[TG5] tukenme kosusunda guc tally'si")
    from cekirdek import sema, tukenme_guc
    s = _spec()
    s["guc_dagilimi"]["var"] = False
    once = copy.deepcopy(s)
    o = tukenme_guc.olcum_spec(s)
    kontrol("demet modelinde guc dagilimi acilir", o["guc_dagilimi"]["var"] is True)
    kontrol("girdi spec degismez", s == once)
    s2 = copy.deepcopy(s)
    s2["tukenme"]["adim_gucu"] = False
    kontrol("tukenme.adim_gucu = false: degismez", tukenme_guc.olcum_spec(s2) == s2)
    pin = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    kontrol("pin hucre (kafes yok): degismez", tukenme_guc.olcum_spec(pin) == pin)
    # hedefsiz guc sozlugu (ornekte "cubuk": null): butun yakit cubuklari hedef olur
    from cekirdek import kurucu
    gd = sema.yukle(os.path.join(ORNEK, "pwr_gd_tukenme.json"))
    o = tukenme_guc.olcum_spec(gd)
    hedefler = sema.guc_hedefleri(o["guc_dagilimi"])
    # Pin gucu = TUM radyal yakit bolgelerinin toplami (profesor E1; NUREG-0800
    # SRP 4.3/4.4): Gd pininin 5 halkasi da hedef, yakit pininde tek bolge.
    kontrol("Gd super hucre: yakit pini 1 + Gd pini 5 halka hedef",
            sorted((h["cubuk"], h["bolge"]) for h in hedefler)
            == [("gd_cubugu", i) for i in range(5)] + [("yakit_cubugu", 0)],
            "-> %r" % hedefler)
    model, _b = kurucu.kur(o)
    adlar = [t.name for t in model.tallies]
    kontrol("model guc tally'leriyle kurulur (hedef bolge basina bir)",
            adlar.count("guc_dagilimi") == 6 and "guc_toplam_ref" in adlar, "-> %r" % adlar)


def test_olcumlu_hazirla_geri_duser():
    print("\n[TG5b] guc tally'si kurulamazsa tukenme olcumsuz kurulur; model hatasi gizlenmez")
    from cekirdek import tukenme_guc
    s = _spec()
    s["guc_dagilimi"]["var"] = False
    cagrilar = []

    def guc_varsa_hata(spec):
        cagrilar.append(spec["guc_dagilimi"]["var"])
        if spec["guc_dagilimi"]["var"]:
            raise ValueError("guc tally'si kurulamadi")
        return "model", {}

    sonuc = tukenme_guc.olcumlu_hazirla(guc_varsa_hata, s)
    kontrol("once olcumlu, sonra olcumsuz denendi", cagrilar == [True, False]
            and sonuc == ("model", {}), "-> %r" % cagrilar)

    def hep_hata(spec):
        raise ValueError("model bozuk")

    s2 = copy.deepcopy(s)
    s2["tukenme"]["adim_gucu"] = False          # olcum spec'i = spec: yeniden denenmez
    try:
        tukenme_guc.olcumlu_hazirla(hep_hata, s2)
        yukseldi = False
    except ValueError:
        yukseldi = True
    kontrol("olcum yoksa hata yukari cikar", yukseldi)


class _Dur(Exception):
    pass


def test_calistir_eski_adimlari_siler(gecici, monkeypatch):
    print("\n[TG6] calistir (kayitli dizinde) onceki adim statepoint'lerini siler")
    import openmc.deplete
    from cekirdek import tukenme
    shutil.copy(os.path.join(FIXTURE, "tukenme_spec.json"), gecici)    # onceki kosunun kaydi
    for i in range(4):
        open(os.path.join(gecici, "openmc_simulation_n%d.h5" % i), "w").close()
    yakalanan = {}

    def sahte_hazirla(spec):
        yakalanan["guc_var"] = (spec.get("guc_dagilimi") or {}).get("var")
        return object(), {"zincir": {"yol": "z.xml", "verim_enerjisi": 0.0253}}

    def sahte_operator(*_a, **_k):
        raise _Dur()

    monkeypatch.setattr(tukenme, "kapi", lambda spec, veri_kontrolu=True: [])
    monkeypatch.setattr(tukenme, "hazirla", sahte_hazirla)
    monkeypatch.setattr(openmc.deplete, "CoupledOperator", sahte_operator)
    s = _spec()
    s["guc_dagilimi"]["var"] = False
    try:
        tukenme.calistir(s, gecici)
    except _Dur:
        pass
    kalan = [a for a in os.listdir(gecici) if a.startswith("openmc_simulation_n")]
    kontrol("eski adim dosyalari silindi", kalan == [], "-> %r" % kalan)
    kontrol("model guc tally'siyle kuruldu (olcum spec'i)", yakalanan.get("guc_var") is True)
    kayit = tukenme._kayit_oku(gecici)
    kontrol("spec kaydi kullanicinin spec'i (guc kapali)",
            kayit["guc_dagilimi"]["var"] is False)


def test_tally_olmayan_adim(gecici):
    print("\n[TG7] guc tally'si olmayan adim: hata metni")
    from cekirdek import tukenme_guc
    kopya = os.path.join(gecici, "fx")
    shutil.copytree(FIXTURE, kopya)
    os.remove(os.path.join(kopya, "openmc_simulation_n1.h5"))
    s = tukenme_guc.adim_gucleri(kopya, _spec())
    kontrol("eksik adim atlanir, not dusulur", [a["adim"] for a in s["adimlar"]] == [0, 2]
            and any("1" in n for n in s["notlar"]), "-> %r" % (s["notlar"],))
    bos = os.path.join(gecici, "bos")
    os.makedirs(bos)
    kontrol("adim dosyasi yoksa None", tukenme_guc.adim_gucleri(bos, _spec()) is None)


def test_gercek_kosu_adim_basina_guc(gecici):
    print("\n[TG8] gercek tukenme kosusu: guc kapali spec'te adim basina tablo uretilir")
    import importlib.util
    from cekirdek import guc_tablo, tukenme, tukenme_guc
    yol = os.path.join(FIXTURE, "uret.py")
    tanim = importlib.util.spec_from_file_location("k3_uret", yol)
    uret = importlib.util.module_from_spec(tanim)
    tanim.loader.exec_module(uret)
    s = uret.fixture_spec()
    s["guc_dagilimi"]["var"] = False             # kullanici guc dagilimini acmamis
    s["ayarlar"].update({"parcacik": 400, "cevrim": 12, "pasif": 4})
    s["tukenme"]["adimlar"] = [2.0]
    dizin = os.path.join(gecici, "k")
    tukenme.calistir(s, dizin)
    sonuc = tukenme_guc.adim_gucleri(dizin, s)
    kontrol("2 zaman noktasi = 2 adim dosyasi",
            [a["adim"] for a in sonuc["adimlar"]] == [0, 1], "-> %r" % sonuc)
    kontrol("her adimda 24 pin ve Σ W = kaynak × pay",
            all(len(a["tablo"]) == 24 and abs(guc_tablo.tablo_toplami(a["tablo"])
                / (a["kaynak_W"] * a["guc"]["hedef_payi"]) - 1.0) < 1e-12
                for a in sonuc["adimlar"]))
    kontrol("spec kaydi guc kapali (kullanicinin spec'i)",
            tukenme._kayit_oku(dizin)["guc_dagilimi"]["var"] is False)


HIZLI = [test_adim_dosyalari, test_adim_basina_tablo, test_seriler, test_csv, test_olcum_spec,
         test_olcumlu_hazirla_geri_duser,
         test_calistir_eski_adimlari_siler, test_tally_olmayan_adim]
YAVAS = [test_gercek_kosu_adim_basina_guc]
ZINCIR_GEREKEN = [test_gercek_kosu_adim_basina_guc]
