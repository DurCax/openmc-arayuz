# -*- coding: utf-8 -*-
"""
 test_geometri_esdegerlik.py  --  G-1 ESDEGERLIK KAPISI (docs/GEOMETRI_MODELI.md §9)

 Eski kor kurucusu (cekirdek/_eski_kurucu.py, DONMUS) ile agac kurucusu
 (cekirdek/geometri) karsilastirilir:
   A  nokta parmak izi (testler/geometri_iz.py): malzeme, kafes indeksleri,
      oteleme, donme, distribcell ornek sirasi -- %100 esit
      (hizli: 300 rastgele + kafes/yuzey komsu noktasi; yavas: 1e5 rastgele)
   B  yapi: her malzemenin ornek sayisi, sinir kutusu, kaynak kutusu, aktif aralik
   C  hacim: tukenen malzemelerin ornek hacimleri (Cell.paths sirasiyla)
   D  betik: kod_uret betiginin geometri XML'i kurucununkiyle AYNI (kimlikler dahil)
 27 ornek + sentetik fikstürler (her sablon x 2B/3B, eksenel, katman
 anahtari, yansitici, kilif, kontrol cubugu, tambur 0/8, sinir turleri,
 silindirle kirpilan kafes).

 BILINCLI FARK (§15 karar 5): kontrol cubugu yeni kurucuda her konumda AYRI
 evrendir; o hucrelerde ornek sirasi karsilastirilmaz ("kc"), malzeme,
 konum ve cerceve karsilastirilir.

 KALICI KAPI: eski kurucu silindikten sonra da calissin diye 27 ornegin
 parmak izi testler/veri/geometri_parmak_izi.json.gz'dedir
 (kayit_uret() ile uretildi; eski kurucudan).
"""

import copy
import glob
import gzip
import json
import os

from testler.ortak_test import kontrol, ORNEK, KOK
from testler import geometri_iz as gi

KAYIT = os.path.join(KOK, "testler", "veri", "geometri_parmak_izi.json.gz")
KAYIT_NOKTA = 400
R3B = ("sfr_met1000_kor", "vver1000_kor")


def _yukle(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _ornek_adlari():
    return [os.path.basename(p)[:-5] for p in sorted(glob.glob(os.path.join(ORNEK, "*.json")))]


def _eski():
    from cekirdek import _eski_kurucu
    return _eski_kurucu.kor_kur


def _yeni():
    from cekirdek import geometri
    return geometri.kur


def iz_karsilastir(spec, n=300):
    """Eski ve yeni kurucunun parmak izi farki (bos = ayni)."""
    a = gi.parmak_izi(_eski(), spec, n=n)
    b = gi.parmak_izi(_yeni(), spec, noktalar=a["noktalar"])
    return gi.iz_farki(a, b), len(a["noktalar"])


def _grup(adlar, n):
    for ad in adlar:
        fark, sayi = iz_karsilastir(_yukle(ad), n=60 if ad in R3B else n)
        kontrol("A %s: %d noktada iz ayni" % (ad, sayi), not fark, "-> %s" % fark)


def _dort(i):
    adlar = _ornek_adlari()
    return adlar[i::4]


def test_iz_ornekler_1():
    print("\n[GE1] A: 27 ornek (1/4) eski = yeni parmak izi")
    _grup(_dort(0), 300)


def test_iz_ornekler_2():
    print("\n[GE2] A: 27 ornek (2/4)")
    _grup(_dort(1), 300)


def test_iz_ornekler_3():
    print("\n[GE3] A: 27 ornek (3/4)")
    _grup(_dort(2), 300)


def test_iz_ornekler_4():
    print("\n[GE4] A: 27 ornek (4/4)")
    _grup(_dort(3), 300)


# ----------------------------------------------------------------------------
# sentetik fikstürler
# ----------------------------------------------------------------------------

def _eksenel(spec, bolgeler):
    s = copy.deepcopy(spec)
    s["kor"]["eksenel"] = {"var": True, "bolgeler": bolgeler}
    return s


def fiksturler():
    """[(ad, spec)] -- her sablonun degiskeleri."""
    from cekirdek import sema
    f = []
    pin = _yukle("pwr_pinhucre")
    f.append(("cubuk 2B", pin))
    p3 = copy.deepcopy(pin)
    p3["kor"].update(yukseklik=100.0, sinir={"yan": "reflective", "alt": "vacuum", "ust": "white"})
    f.append(("cubuk 3B vacuum/white", p3))
    f.append(("cubuk eksenel + ayni cubuk katmanda", _eksenel(p3, [
        sema.eksenel_bolge("alt", 10.0, "su"), sema.eksenel_bolge("aktif", 80.0),
        sema.eksenel_bolge("ayni", 20.0, "yakit_cubugu"), sema.eksenel_bolge("sifir", 0.0, "su")])))
    pl = _yukle("mtr_plaka")
    pl3 = copy.deepcopy(pl)
    pl3["kor"]["yukseklik"] = 60.0
    f += [("plaka 2B", pl), ("plaka 3B", pl3)]
    d = _yukle("pwr_17x17")
    dy = copy.deepcopy(d)
    dy["kor"]["yansitici"] = {"var": True, "kalinlik": 10.0, "malzeme": "su"}
    dy["kor"]["sinir"]["yan"] = "vacuum"
    f.append(("kare demet + yansitici", dy))
    f.append(("kare demet eksenel", _eksenel(dict(dy, kor=dict(dy["kor"], yukseklik=50.0)), [
        sema.eksenel_bolge("alt", 10.0, "su"), sema.eksenel_bolge("aktif", 40.0)])))
    hx = _yukle("sfr_altigen")
    hxy = copy.deepcopy(hx)
    hxy["kor"]["yansitici"] = {"var": True, "kalinlik": 3.0, "malzeme": "sodyum"}
    f += [("altigen demet + yansitici", hxy)]
    kl = _yukle("sfr_met1000_demet")
    klt = copy.deepcopy(kl)
    d0 = klt["demetler"][0]
    klt["kor"] = dict(sema.VARSAYILAN_KOR, tur="tek_demet", demet=d0["ad"],
                      yansitici={"var": True, "kalinlik": 2.0, "malzeme": "sodyum"})
    f.append(("kilifli altigen demet + yansitici", klt))
    kk = _yukle("pwr_ceyrek_kor")
    kky = copy.deepcopy(kk)
    kky["kor"]["yansitici"] = {"var": True, "kalinlik": 15.0, "malzeme": "su"}
    kky["kor"]["eksenel"]["bolgeler"][1]["anahtar"] = {"A": "demet_31"}
    f.append(("kare kafes + yansitici + katman anahtari", kky))
    kp = copy.deepcopy(kk)
    kp["kor"]["eksenel"] = {"var": False, "bolgeler": []}
    kp["kor"]["sinir"]["yan"] = "periodic"
    f.append(("kare kafes 2B periodic", kp))
    vv = _yukle("vver1000_kor")
    vv2 = copy.deepcopy(vv)
    vv2["kor"]["eksenel"] = {"var": False, "bolgeler": []}
    vv2["kor"]["yansitici"]["var"] = False
    f.append(("altigen kafes 2B yansiticisiz (kirik cizgi)", vv2))
    t = _yukle("tamburlu_kor")
    t0 = copy.deepcopy(t)
    t0["kor"]["tambur"]["sayi"] = 0
    f.append(("tamburlu 0 tambur", t0))
    te = _eksenel(t, [sema.eksenel_bolge("alt", 5.0, "berilyum"),
                      sema.eksenel_bolge("aktif", 35.0), sema.eksenel_bolge("ust", 5.0, "berilyum")])
    te["kor"]["tambur"]["donme"] = 37.0
    f.append(("tamburlu 8 tambur + eksenel (R-4)", te))
    kc = _yukle("pwr_kontrol")
    kce = _eksenel(kc, [sema.eksenel_bolge("alt", 30.0, "su"), sema.eksenel_bolge("aktif", 306.0),
                        sema.eksenel_bolge("ust", 30.0, "su")])
    f.append(("kontrol cubugu + eksenel", kce))
    f.append(("kure", _yukle("zirh_katmanli")))
    return f


def test_iz_fiksturler():
    print("\n[GE5] A: sentetik fikstürler eski = yeni")
    for ad, spec in fiksturler():
        fark, sayi = iz_karsilastir(spec, n=200)
        kontrol("A %s: %d nokta" % (ad, sayi), not fark, "-> %s" % fark)


# ----------------------------------------------------------------------------
# B, C
# ----------------------------------------------------------------------------

def _eski_ic_olcusu(spec, sinir_kutu):
    """Eski kurucu.kor_ic_olcusu (donmus kopya)."""
    from cekirdek import altigen_kor as _akor
    kor = spec["kor"]
    tur = kor.get("tur")
    if tur == "altigen_kafes":
        return _akor.kor_ic_olcusu(kor)
    yans = kor.get("yansitici") or {}
    var = tur == "tamburlu" or (yans.get("var") and tur in ("tek_demet", "kare_kafes"))
    if not var:
        return tuple(sinir_kutu)
    kal = float(yans.get("kalinlik") or 0.0)
    return (sinir_kutu[0] - 2.0 * kal, sinir_kutu[1] - 2.0 * kal)


def test_yapi():
    print("\n[GE6] B: sinir/kaynak kutusu ve aktif aralik eski kurucuyla ayni")
    import openmc
    from cekirdek import kurucu, _eski_kurucu as ek
    for ad, spec in [(a, _yukle(a)) for a in _ornek_adlari()] + fiksturler():
        openmc.reset_auto_ids()
        n, _m, _r = kurucu.malzemeleri_kur(spec)
        _k, kutu = ek.kor_kur(spec, n, {})
        eski = (tuple(kutu), _eski_ic_olcusu(spec, kutu), ek.aktif_eksenel_aralik(spec))
        yeni = (tuple(kurucu.kor_kur(spec, n, {})[1]), kurucu.kor_ic_olcusu(spec, kutu),
                kurucu.aktif_eksenel_aralik(spec))
        kontrol("B %s: kutu, kaynak kutusu, aktif aralik" % ad, eski == yeni,
                "-> %s / %s" % (eski, yeni))


def _ornek_hacimleri(kok, mat_adi, adlar):
    import openmc
    from cekirdek import tukenme_hacim as th
    geo = openmc.Geometry(kok)
    geo.determine_paths()
    hucreler, kafesler = geo.get_all_cells(), geo.get_all_lattices()
    sonuc = {}
    for c in hucreler.values():
        if c.fill_type == "material" and mat_adi.get(id(c.fill)) in adlar:
            sonuc.setdefault(mat_adi[id(c.fill)], []).extend(
                round(th.ornek_hacmi(y, hucreler, kafesler) or -1.0, 9) for y in c.paths)
    return {a: sorted(v) for a, v in sonuc.items()}


def test_hacim():
    print("\n[GE7] C: tukenen malzemelerin ornek hacimleri ayni")
    from cekirdek import tukenme
    for ad in ("pwr_tukenme", "pwr_gd_tukenme", "tamburlu_kor", "pwr_pinhucre"):
        spec = _yukle(ad)
        adlar = set(tukenme.hacimler(spec)) or {m["ad"] for m in spec["malzemeler"]}
        sonuc = []
        for islev in (_eski(), _yeni()):
            kok, _kutu, mat_adi, _kc = gi.kok_kur(islev, spec)
            sonuc.append(_ornek_hacimleri(kok, mat_adi, adlar))
        kontrol("C %s: %d malzeme, ornek hacimleri ayni" % (ad, len(sonuc[0])),
                sonuc[0] == sonuc[1] and sonuc[0], "-> %s" % (sonuc,))


# ----------------------------------------------------------------------------
# D: betik = kurucu (ayni gezinti)
# ----------------------------------------------------------------------------

def betik_xml_farki(spec):
    """Betigin geometri XML'i kurucununkiyle ayni mi (kimlik ve adlar dahil)."""
    import importlib.util
    import tempfile
    import openmc
    from cekirdek import kurucu, kod_uret
    d = tempfile.mkdtemp(prefix="ge_betik_")
    openmc.reset_auto_ids()
    a, _b = kurucu.kur(copy.deepcopy(spec))
    a.geometry.export_to_xml(os.path.join(d, "a.xml"))
    yol = os.path.join(d, "model.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kod_uret.uret(spec, "model.py"))
    openmc.reset_auto_ids()
    sm = importlib.util.spec_from_file_location("ge_betik_%d" % id(spec), yol)
    mo = importlib.util.module_from_spec(sm)
    sm.loader.exec_module(mo)
    mo.model.geometry.export_to_xml(os.path.join(d, "b.xml"))
    with open(os.path.join(d, "a.xml")) as fa, open(os.path.join(d, "b.xml")) as fb:
        return fa.read() == fb.read()


def test_betik_xml_kucuk():
    print("\n[GE8] D: betik geometri XML'i = kurucu (kucuk ornekler + R-4 fikstürü)")
    for ad in ("pwr_pinhucre", "tamburlu_kor", "mtr_kor", "pwr_kontrol", "sfr_altigen",
               "zirh_katmanli"):
        kontrol("D %s" % ad, betik_xml_farki(_yukle(ad)))
    for ad, spec in fiksturler():
        if ad.startswith(("tamburlu 8", "kilifli", "kare kafes +")):
            kontrol("D %s" % ad, betik_xml_farki(spec))


def test_betik_xml_hepsi(gecici=None):
    print("\n[GE9] D: 27 ornek + fikstürler betik XML = kurucu")
    for ad in _ornek_adlari():
        kontrol("D %s" % ad, betik_xml_farki(_yukle(ad)))
    for ad, spec in fiksturler():
        kontrol("D %s" % ad, betik_xml_farki(spec))


# ----------------------------------------------------------------------------
# kalici kapi (eski kurucu olmadan)
# ----------------------------------------------------------------------------

def _json_iz(iz):
    return json.loads(json.dumps(iz))


def kayit_uret(yol=KAYIT):
    """Eski kurucudan 27 ornegin parmak izi kaydini uretir (bir kez)."""
    kayit = {}
    for ad in _ornek_adlari():
        a = gi.parmak_izi(_eski(), _yukle(ad), n=KAYIT_NOKTA)
        kayit[ad] = {"kutu": list(a["kutu"]), "noktalar": a["noktalar"],
                     "izler": _json_iz(a["izler"]), "malzeme_ornekleri": a["malzeme_ornekleri"]}
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with gzip.open(yol, "wt", encoding="utf-8") as f:
        json.dump(kayit, f, separators=(",", ":"))
    return yol


def test_kayitli_parmak_izi():
    print("\n[GE10] A (kalici): yeni kurucu = kayitli parmak izi (eski kurucudan)")
    kontrol("kayit dosyasi var", os.path.exists(KAYIT), KAYIT)
    if not os.path.exists(KAYIT):
        return
    with gzip.open(KAYIT, "rt", encoding="utf-8") as f:
        kayit = json.load(f)
    kontrol("27 ornek kayitli", sorted(kayit) == _ornek_adlari())
    for ad, k in sorted(kayit.items()):
        nok = [tuple(p) for p in k["noktalar"]]
        if ad in R3B:
            nok = nok[:150]
        b = gi.parmak_izi(_yeni(), _yukle(ad), noktalar=nok)
        a = {"kutu": tuple(k["kutu"]), "noktalar": nok, "izler": [tuple(_tuple(x)) for x in k["izler"][:len(nok)]],
             "malzeme_ornekleri": k["malzeme_ornekleri"]}
        b["izler"] = [tuple(_tuple(x)) for x in _json_iz(b["izler"])]
        fark = gi.iz_farki(a, b)
        kontrol("kayit %s (%d nokta)" % (ad, len(nok)), not fark, "-> %s" % fark)


def _tuple(x):
    return tuple(_tuple(v) for v in x) if isinstance(x, list) else x


def test_yavas_iz_1e5(gecici=None):
    print("\n[GE11] A (yavas): 27 ornekte 1e5 rastgele nokta")
    for ad in _ornek_adlari():
        fark, sayi = iz_karsilastir(_yukle(ad), n=100000)
        kontrol("A %s: %d nokta" % (ad, sayi), not fark, "-> %s" % fark)


HIZLI = [test_iz_ornekler_1, test_iz_ornekler_2, test_iz_ornekler_3, test_iz_ornekler_4,
         test_iz_fiksturler, test_yapi, test_hacim, test_betik_xml_kucuk,
         test_kayitli_parmak_izi]
YAVAS = [test_betik_xml_hepsi, test_yavas_iz_1e5]
