# -*- coding: utf-8 -*-
"""
 test_geometri_agac.py  --  G-1: gelismis (agac) modu duzenekleri ve yeni yetenekler

 (a) 5x5 kare cekirdek + altigen blok halkasi (yansitici ve yakit blok)
 (b) altigen kor + yansiticida 6 tambur        (c) kare kafesli kor + 4 tambur
 (d) altigen ve kare kesitli pin demetleri     (e) ceyrek kor: 2 yuz reflective
 Kurulur (kurucu.kur, agac modu), betik XML'i kurucuyla ayni, yuz basina
 sinir kosulu, kontrol cubugu ayri ornek, kesik konumlar. Yavas: kisa MC.
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri).
"""

import copy
import math
import os

from testler.ortak_test import kontrol, ISLEM_PARCACIGI
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik
from testler import geometri_ortak as go

DUZENEKLER = (("a", lambda: go.duzenek_a()), ("a-yakit", lambda: go.duzenek_a(True)),
              ("b", go.duzenek_b), ("c", go.duzenek_c),
              ("d-kare", lambda: go.duzenek_d("kare")),
              ("d-altigen", lambda: go.duzenek_d("altigen")),
              ("e-ceyrek", go.duzenek_e_ceyrek), ("e-tam", go.duzenek_e_tam))


def _sorgu(model, bilgi, x, y, z=0.0):
    from testler import geometri_iz as gi
    mat = {id(m): a for a, m in bilgi["malzemeler"].items()}
    return gi.nokta_izi(model.geometry.root_universe, (x, y, z), mat, gi.OrnekSayaci())


@gereksinim("R-G-11")
def test_duzenekler_kurulur():
    print("\n[GA1] (a)-(e) agac modunda kurulur; betik geometri XML'i kurucuyla ayni")
    from cekirdek import kurucu
    from testler.test_geometri_esdegerlik import betik_xml_farki
    for ad, uret in DUZENEKLER:
        spec = uret()
        try:
            model, bilgi = kurucu.kur(copy.deepcopy(spec))
            hata = None
        except Exception as e:     # noqa: BLE001 -- test: her hata raporlanir
            model, hata = None, "%s: %s" % (type(e).__name__, e)
        kontrol("(%s) kuruldu" % ad, hata is None, "-> %s" % hata)
        if model is not None:
            kontrol("(%s) betik = kurucu (XML)" % ad, betik_xml_farki(spec))


@gereksinim("R-G-04")
def test_a_kesik_ve_nokta():
    print("\n[GA2] (a): 1. halka gizli, 2. halka kesik (UYARI), kare cekirdek merkezde")
    from cekirdek import geometri, kurucu
    spec = go.duzenek_a()
    m = geometri.model(spec)
    kesik = geometri.kesik_konumlar(m)
    say = {}
    for k in kesik:
        if k["kafes"] == "blok_kafesi":
            say[(k["indeks"][0], k["durum"])] = say.get((k["indeks"][0], k["durum"]), 0) + 1
    kontrol("halka 2 (harita satiri 2, 12 blok): kesik", say.get((2, "kesik"), 0) == 12,
            "-> %s" % say)
    # olculdu: kare deligin koseleri (75.7 cm) 3. yaricap halkasindaki 4 blogu da
    # kirpar (belge §4.1 yalniz 2. halkayi bekliyordu); en dis halka tam.
    kontrol("yaricap 3 halkasinda 4 kesik blok (kare kose), en dis halka tam",
            say.get((1, "kesik")) == 4 and not any(r == 0 for r, _d in say), "-> %s" % say)
    kontrol("ic halka ve merkez gizli (7 konum)",
            say.get((3, "gizli")) == 6 and say.get((4, "gizli")) == 1)
    model, bilgi = kurucu.kur(spec)
    kontrol("dizin.kesik kurulumda dolu", bool(bilgi["geometri_dizini"].kesik))
    iz = _sorgu(model, bilgi, 0.3, 0.2)
    kontrol("merkez noktasi kare cekirdek kafesinde", iz[0] in ("uo2_24", "uo2_31", "helyum",
                                                                 "zirkaloy4", "su")
            and len(iz[1]) >= 1, "-> %s" % (iz,))
    iz = _sorgu(model, bilgi, 4 * 30.0 * math.sqrt(3) / 2, 0.0)
    kontrol("dis halka blogunda celik (ss304) ya da kanal suyu", iz[0] in ("ss304", "su"),
            "-> %s" % (iz,))


def test_b_tambur_ve_r3b():
    print("\n[GA3] (b): R3b konum hucreleri + yansiticidaki 6 tamburun deligi")
    from cekirdek import kurucu
    spec = go.duzenek_b()
    model, bilgi = kurucu.kur(spec)
    for i in range(6):
        fi = math.radians(30.0 + 60.0 * i)
        iz = _sorgu(model, bilgi, 36.0 * math.cos(fi), 36.0 * math.sin(fi))
        kontrol("tambur %d merkezi govde (celik) -- delik oyuldu, donme uygulandi" % i,
                iz[0] == "celik" and len(iz[3]) == 1, "-> %s" % (iz,))
    # D = 180: emici disa bakiyor
    fi = math.radians(30.0)
    rho = 0.5 * (4.5 + 6.0)
    dis = _sorgu(model, bilgi, (36.0 + rho) * math.cos(fi), (36.0 + rho) * math.sin(fi))
    kontrol("grup donmesi 180: emici disa bakiyor (b4c)", dis[0] == "b4c", "-> %s" % (dis,))
    kontrol("yan sinir vacuum (yansitici disi)", bilgi["sinir_kutu"][0] > 90)


def _bc(model, tur, deger):
    for s in model.geometry.get_all_surfaces().values():
        if s.type == tur and abs(getattr(s, {"x-plane": "x0", "y-plane": "y0"}[tur]) - deger) < 1e-9:
            return s.boundary_type
    return None


@gereksinim("R-G-06")
def test_yuz_basina_sinir():
    print("\n[GA4] yuz basina yan sinir: ceyrek kor -x,-y reflective; +x,+y vacuum; periodic cift")
    from cekirdek import kurucu
    model, _b = kurucu.kur(go.duzenek_e_ceyrek())
    L = 21.42 * 4 / 2
    kontrol("-x reflective, +x vacuum", _bc(model, "x-plane", -L) == "reflective"
            and _bc(model, "x-plane", L) == "vacuum")
    kontrol("-y reflective, +y vacuum", _bc(model, "y-plane", -L) == "reflective"
            and _bc(model, "y-plane", L) == "vacuum")
    s = go.duzenek_e_ceyrek()
    s["geometri"]["kok"]["sinir"]["yuzler"] = {"-x": "periodic", "+x": "periodic",
                                               "-y": "reflective", "+y": "vacuum"}
    model, _b = kurucu.kur(s)
    xs = [x for x in model.geometry.get_all_surfaces().values() if x.type == "x-plane"]
    kontrol("periodic x cifti eslendi", any(getattr(x, "periodic_surface", None) is not None
                                            for x in xs))
    # altigen dis sinir: 6 yuz
    a = go.duzenek_a()
    yuzler = ["vacuum", "reflective", "vacuum", "white", "vacuum", "reflective"]
    a["geometri"]["kok"]["sinir"]["yuzler"] = yuzler
    model, _b = kurucu.kur(a)
    bcler = sorted(x.boundary_type for x in model.geometry.get_all_surfaces().values()
                   if x.boundary_type != "transmission")
    kontrol("altigen: 6 yuz ayri BC", bcler == sorted(yuzler), "-> %s" % bcler)


@gereksinim("R-G-07")
def test_kontrol_cubugu_ayri_ornek():
    print("\n[GA5] kontrol cubugu: her konum ayri evren/hucre (karar 5); grup daldirmasi")
    import openmc
    from cekirdek import kurucu, sema
    spec = sema.yukle(os.path.join(go.ORNEK, "pwr_kontrol.json"))
    model, bilgi = kurucu.kur(spec)
    d = spec["demetler"][0]
    harfler = [h for h, v in d["anahtar"].items() if v == "kontrol_cubugu"]
    n = sum(s.count(h) for s in d["harita"] for h in harfler)
    evrenler = bilgi["geometri_dizini"].kontrol_cubuklari["kontrol_cubugu"]
    kontrol("%d konum -> %d ayri evren" % (n, len(evrenler)),
            len(evrenler) == n and len({id(u) for u in evrenler}) == n)
    model.geometry.determine_paths()
    ornek = {c.num_instances for u in evrenler for c in u.cells.values()}
    kontrol("her cubuk hucresinin tek ornegi var", ornek == {1}, "-> %s" % ornek)
    # agac modunda daldirma grubu tanimdaki degeri ezer
    from cekirdek import geometri
    g = geometri.gelismise_gec(spec)
    g["geometri"]["gruplar"] = [{"ad": "Banka A", "tur": "daldirma", "deger": 50.0,
                                 "uyeler": ["kontrol_cubugu"]}]
    openmc.reset_auto_ids()
    _m, b2 = kurucu.kur(g)
    u = b2["geometri_dizini"].kontrol_cubuklari["kontrol_cubugu"][0]
    z = sorted({round(s.z0, 6) for c in u.cells.values() for s in c.region.get_surfaces().values()
                if s.type == "z-plane"})
    kontrol("grup %%50 -> uc z = 0 (aktif aralik ortasi)", z == [0.0], "-> %s" % z)


def test_agac_ayarlari():
    print("\n[GA6] agac modunda ayarlar: kaynak kutusu kok kesitinden, yukseklikten")
    from cekirdek import kurucu
    model, bilgi = kurucu.kur(go.duzenek_c())
    uzay = model.settings.source[0].space
    kontrol("kaynak kutusu = kare kor (64.26), z = +/-100",
            abs(uzay.upper_right[0] - 32.13) < 1e-9 and abs(uzay.upper_right[2] - 100.0) < 1e-9,
            "-> %s" % (list(uzay.upper_right),))
    kontrol("sinir kutusu = silindir capi 160", tuple(bilgi["sinir_kutu"]) == (160.0, 160.0))


# ----------------------------------------------------------------------------
# yavas: kisa Monte Carlo
# ----------------------------------------------------------------------------

def _k(spec, dizin, parcacik=3000, cevrim=60, pasif=20):
    import openmc
    from cekirdek import kurucu
    s = copy.deepcopy(spec)
    s["ayarlar"].update(parcacik=parcacik, cevrim=cevrim, pasif=pasif)
    os.makedirs(dizin, exist_ok=True)
    eski = os.getcwd()
    try:
        os.chdir(dizin)
        model, _b = kurucu.kur(s)
        return openmc.StatePoint(model.run(threads=ISLEM_PARCACIGI, output=False)).keff
    finally:
        os.chdir(eski)


OLCULEN = {}


@gereksinim("R-G-11")
def test_duzenekler_kosar(gecici):
    print("\n[GA7] (a)-(e) kisa MC kosar; k olculur")
    for ad, uret in DUZENEKLER:
        k = _k(uret(), os.path.join(gecici, "ga_" + ad))
        OLCULEN[ad] = k
        kontrol("(%s) k = %.5f +/- %.5f" % (ad, k.nominal_value, k.std_dev),
                0.05 < k.nominal_value < 2.0)


@gereksinim("R-G-06")
def test_ceyrek_tam_esit(gecici):
    print("\n[GA8] (e) ceyrek kor (2 reflective + 2 vacuum yuz) = tam kor (2 sigma)")
    kc = _k(go.duzenek_e_ceyrek(), os.path.join(gecici, "ceyrek"), 8000, 120, 30)
    kt = _k(go.duzenek_e_tam(), os.path.join(gecici, "tam"), 16000, 120, 30)
    s = math.hypot(kc.std_dev, kt.std_dev)
    kontrol("ceyrek %.5f +/- %.5f  vs  tam %.5f +/- %.5f  (fark %.1f sigma)"
            % (kc.nominal_value, kc.std_dev, kt.nominal_value, kt.std_dev,
               abs(kc.nominal_value - kt.nominal_value) / s),
            abs(kc.nominal_value - kt.nominal_value) <= 2 * s)


HIZLI = [test_duzenekler_kurulur, test_a_kesik_ve_nokta, test_b_tambur_ve_r3b,
         test_yuz_basina_sinir, test_kontrol_cubugu_ayri_ornek, test_agac_ayarlari]
YAVAS = [test_duzenekler_kosar, test_ceyrek_tam_esit]
