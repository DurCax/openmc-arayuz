# -*- coding: utf-8 -*-
"""
 test_geometri_esdegerlik.py  --  G-1 ESDEGERLIK KAPISI (docs/GEOMETRI_MODELI.md §9)

 Eski kor kurucusu ile agac kurucusunun (cekirdek/geometri) esdegerligi.
 Kapi 30.09.2026'da eski kurucuyla (cekirdek/_eski_kurucu.py, 89d6bc5..fef6903)
 gecti -- 27 ornek x 1e5 rastgele nokta + 16 fikstur -- ve eski kurucu
 silindi. Kapi KALICIDIR: eski kurucunun ciktilari, spec'in kendisiyle
 birlikte testler/veri/geometri_parmak_izi.json.gz'de kayitlidir (ornek
 dosyalari sonradan degisse de kayit kendi spec'ini tasir):
   A  nokta parmak izi (testler/geometri_iz.py): malzeme, kafes indeksleri,
      oteleme, donme, distribcell ornek sirasi -- %100 esit
      (400 rastgele + kafes eleman / yuzey komsu noktalari)
   B  yapi: her malzemenin ornek sayisi, sinir kutusu, kaynak kutusu, aktif aralik
   C  hacim: tukenen malzemelerin ornek hacimleri (Cell.paths sirasiyla)
   D  betik: kod_uret betiginin geometri XML'i kurucununkiyle AYNI (kimlikler dahil)

 BILINCLI FARK (§15 karar 5): kontrol cubugu yeni kurucuda her konumda AYRI
 evrendir; o hucrelerde ornek sirasi karsilastirilmaz ("kc").
 Kaydi yeniden uretmek: eski kurucuyu iceren commit.e (fef6903) donup
 kayit_uret() (git show fef6903:testler/test_geometri_esdegerlik.py).
"""

import copy
import glob
import gzip
import json
import os

from testler.ortak_test import kontrol, ORNEK, KOK
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik
from cekirdek import geometri  # noqa: E402
from cekirdek.geometri import eksenel as geo_eks  # noqa: E402,F401
from testler import geometri_iz as gi

KAYIT = os.path.join(KOK, "testler", "veri", "geometri_parmak_izi.json.gz")
R3B = ("sfr_met1000_kor", "vver1000_kor")
_ONBELLEK = {}


def _kayit():
    if "k" not in _ONBELLEK:
        with gzip.open(KAYIT, "rt", encoding="utf-8") as f:
            _ONBELLEK["k"] = json.load(f)
    return _ONBELLEK["k"]


def _yukle(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _ornek_adlari():
    return [os.path.basename(p)[:-5] for p in sorted(glob.glob(os.path.join(ORNEK, "*.json")))]


def _yeni():
    from cekirdek import geometri
    return geometri.kur


def _tuple(x):
    return tuple(_tuple(v) for v in x) if isinstance(x, list) else x


def kayitla_karsilastir(ad, en_cok=None):
    """Kayitli (eski kurucu) iz ile yeni kurucunun farki; bos = ayni."""
    k = _kayit()[ad]
    nok = [tuple(p) for p in k["noktalar"]][:en_cok]
    b = gi.parmak_izi(_yeni(), k["spec"], noktalar=nok)
    a = {"kutu": tuple(k["kutu"]), "noktalar": nok,
         "izler": [_tuple(x) for x in k["izler"][:len(nok)]],
         "malzeme_ornekleri": k["malzeme_ornekleri"]}
    b["izler"] = [_tuple(x) for x in json.loads(json.dumps(b["izler"]))]
    return gi.iz_farki(a, b), len(nok)


def _grup(i):
    adlar = sorted(_kayit())[i::4]
    for ad in adlar:
        fark, n = kayitla_karsilastir(ad, 150 if ad in R3B else None)
        kontrol("A %s: %d noktada iz ayni" % (ad, n), not fark, "-> %s" % fark)


@gereksinim("R-G-01")
def test_iz_kayit_1():
    print("\n[GE1] A: kayitli parmak izi = yeni kurucu (1/4)")
    kontrol("kayit: 27 ornek + fikstürler", len(_kayit()) >= 27 + 16, "-> %d" % len(_kayit()))
    _grup(0)


@gereksinim("R-G-01")
def test_iz_kayit_2():
    print("\n[GE2] A: (2/4)")
    _grup(1)


@gereksinim("R-G-01")
def test_iz_kayit_3():
    print("\n[GE3] A: (3/4)")
    _grup(2)


@gereksinim("R-G-01")
def test_iz_kayit_4():
    print("\n[GE4] A: (4/4)")
    _grup(3)


@gereksinim("R-G-01")
def test_yapi():
    print("\n[GE6] B: sinir/kaynak kutusu ve aktif aralik kayitla ayni")
    import openmc
    from cekirdek import kurucu
    for ad, k in sorted(_kayit().items()):
        spec = k["spec"]
        openmc.reset_auto_ids()
        n, _m, _r = kurucu.malzemeleri_kur(spec)
        kutu = tuple(geometri.kur(spec, n, {})[1])
        ar = geometri.aktif_aralik(spec)
        yeni = [list(kutu), list(geometri.ic_olcusu(geometri.model(spec))), list(ar) if ar else None]
        kontrol("B %s" % ad, yeni == [k["kutu"], k["ic_kutu"], k["aktif"]],
                "-> %s / %s" % (yeni, [k["kutu"], k["ic_kutu"], k["aktif"]]))


def ornek_hacimleri(kok, mat_adi, adlar):
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


@gereksinim("R-G-01")
def test_hacim():
    print("\n[GE7] C: tukenen malzemelerin ornek hacimleri kayitla ayni")
    for ad, k in sorted(_kayit().items()):
        if not k.get("hacimler"):
            continue
        kok, _kutu, mat_adi, _kc = gi.kok_kur(_yeni(), k["spec"])
        yeni = ornek_hacimleri(kok, mat_adi, set(k["hacimler"]))
        kontrol("C %s: %d malzeme" % (ad, len(yeni)), yeni == k["hacimler"])


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


@gereksinim("R-FZ-04")
def test_betik_xml_kucuk():
    print("\n[GE8] D: betik geometri XML'i = kurucu (kucuk ornekler + fikstürler)")
    for ad in ("pwr_pinhucre", "tamburlu_kor", "mtr_kor", "pwr_kontrol", "sfr_altigen",
               "zirh_katmanli"):
        kontrol("D %s" % ad, betik_xml_farki(_yukle(ad)))
    for ad, k in sorted(_kayit().items()):
        if ad.startswith(("F tamburlu 8", "F kilifli", "F kare kafes +")):
            kontrol("D %s" % ad, betik_xml_farki(k["spec"]))


@gereksinim("R-FZ-04")
def test_betik_xml_hepsi(gecici=None):
    print("\n[GE9] D: 27 ornek + fikstürler betik XML = kurucu")
    for ad in _ornek_adlari():
        kontrol("D %s" % ad, betik_xml_farki(_yukle(ad)))
    for ad, k in sorted(_kayit().items()):
        if ad.startswith("F "):
            kontrol("D %s" % ad, betik_xml_farki(k["spec"]))


@gereksinim("R-G-01")
def test_yavas_kayit_tam(gecici=None):
    print("\n[GE10] A (yavas): kayittaki butun noktalar (R3b dahil)")
    for ad in sorted(_kayit()):
        fark, n = kayitla_karsilastir(ad)
        kontrol("A %s: %d nokta" % (ad, n), not fark, "-> %s" % fark)


HIZLI = [test_iz_kayit_1, test_iz_kayit_2, test_iz_kayit_3, test_iz_kayit_4,
         test_yapi, test_hacim, test_betik_xml_kucuk]
YAVAS = [test_betik_xml_hepsi, test_yavas_kayit_tam]
