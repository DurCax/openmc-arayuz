# -*- coding: utf-8 -*-
"""
 test_guc_kor.py  --  Tam korda (birden cok demet) guc haritasi

 HATA (M1, olculdu): guc.dagilim_oku haritayi yalnizca EN ICTEKI kafesin (x, y)
 konumuna gore anahtarliyordu. Farkli demetlerde ayni konumdaki cubuklar ayni
 anahtara yaziliyor, harita SON demetin degerlerini gosteriyordu; toplam
 korunmuyor, F_dH yanlis demetten okunuyordu. Ayni kusur eksenel katmanlarda da
 vardi: ayni cubuk konumu iki katmanda gecince ust katmanin (o dilimde SIFIR
 olan) degeri alt katmaninkinin uzerine yaziliyordu.

 HIZLI: sentetik DataFrame ve gercek openmc kafes nesneleriyle anahtar/donusum
        mantigi, tepe faktorleri, arayuz cizimi, dogrulama kurali.
 YAVAS: 2x2 kare kor ve altigen-icinde-altigen kor (Monte Carlo); konum
        eslesmesi AYRI SURECTE openmc.lib.find_cell ile nokta-hucre olcumu.
"""

import json
import math
import os
import re
import subprocess
import sys
from types import SimpleNamespace

from testler.ortak_test import kontrol, KOK, ORNEK, ISLEM_PARCACIGI


# ============================================================================
# SENTETIK STATEPOINT
# ============================================================================

class _SahteTally:
    def __init__(self, df):
        self._df = df

    def get_pandas_dataframe(self, paths=True):
        return self._df


class _SahteGeometri:
    def __init__(self, kafesler):
        self._kafesler = {k.id: k for k in kafesler}

    def determine_paths(self):
        return None

    def get_all_lattices(self):
        return dict(self._kafesler)


def _sahte_sp(satirlar, duzeyler, kafesler, dilim_var=False):
    """
    satirlar: [{"duzeyler": [(kafes_id, x, y), ...], "hucreler": [...],
                "z": 1, "ort": .., "sap": ..}, ...]
    DataFrame sutunlari OpenMC 0.16'nin get_pandas_dataframe(paths=True)
    ciktisiyla ayni bicimdedir (olculdu: ('level N','lat','id'/'x'/'y')).
    """
    import pandas as pd
    sutunlar, veri = [], []
    for sat_no, s in enumerate(satirlar):
        satir = {}
        seviye = 1
        for d in range(duzeyler):
            satir[("level %d" % seviye, "univ", "id")] = 100 + d
            satir[("level %d" % seviye, "cell", "id")] = s.get("hucreler", [0] * duzeyler)[d]
            lid, x, y = s["duzeyler"][d]
            satir[("level %d" % (seviye + 1), "lat", "id")] = lid
            satir[("level %d" % (seviye + 1), "lat", "x")] = x
            satir[("level %d" % (seviye + 1), "lat", "y")] = y
            seviye += 2
        satir[("level %d" % seviye, "univ", "id")] = 999
        satir[("level %d" % seviye, "cell", "id")] = 998
        satir[("distribcell", "", "")] = s.get("ornek", sat_no)
        if dilim_var:
            satir[("mesh 1", "x", "")] = 1
            satir[("mesh 1", "y", "")] = 1
            satir[("mesh 1", "z", "")] = s["z"]
        satir[("mean", "", "")] = s["ort"]
        satir[("std. dev.", "", "")] = s["sap"]
        veri.append(satir)
        if not sutunlar:
            sutunlar = list(satir.keys())
    df = pd.DataFrame([[v[c] for c in sutunlar] for v in veri],
                      columns=pd.MultiIndex.from_tuples(sutunlar))
    return SimpleNamespace(get_tally=lambda name=None: _SahteTally(df),
                           summary=SimpleNamespace(geometry=_SahteGeometri(kafesler)))


def _kare_kafes(lid, n, adim):
    import openmc
    import warnings
    with warnings.catch_warnings():
        # sabit kimlik bilerek: sentetik DataFrame bu kimlige basvurur
        warnings.simplefilter("ignore", openmc.IDWarning)
        lat = openmc.RectLattice(lattice_id=lid)
    lat.pitch = (adim, adim)
    lat.lower_left = (-adim * n / 2.0, -adim * n / 2.0)
    u = openmc.Universe()
    lat.universes = [[u] * n for _ in range(n)]
    return lat


def _altigen_kafes(lid, halka, adim, yonelim):
    import openmc
    from cekirdek import altigen
    import warnings
    with warnings.catch_warnings():
        # sabit kimlik bilerek: sentetik DataFrame bu kimlige basvurur
        warnings.simplefilter("ignore", openmc.IDWarning)
        lat = openmc.HexLattice(lattice_id=lid)
    lat.center = (0.0, 0.0)
    lat.pitch = (adim,)
    lat.orientation = yonelim
    u = openmc.Universe()
    lat.universes = [[u] * k for k in altigen.halka_uzunluklari(halka)]
    return lat


def _kare_2x2_sentetik():
    """2x2 demet x 2x2 cubuk; deger = 100*(demet no+1) + cubuk no."""
    kor = _kare_kafes(9001, 2, 4.0)
    ic = _kare_kafes(9002, 2, 2.0)
    satirlar = []
    for dy in range(2):
        for dx in range(2):
            for cy in range(2):
                for cx in range(2):
                    dno, cno = dy * 2 + dx, cy * 2 + cx
                    satirlar.append({"duzeyler": [(9001, dx, dy), (9002, cx, cy)],
                                     "ort": 100.0 * (dno + 1) + cno, "sap": 1.0})
    return _sahte_sp(satirlar, 2, [kor, ic])


# ============================================================================
# HIZLI -- anahtar ve donusum mantigi
# ============================================================================

def test_kare_kor_anahtar_sentetik():
    """Kare korda her cubuk ayri anahtar almali; toplam korunmali."""
    print("\n[GK1] Kare kor: tam yol anahtari (sentetik)")
    from cekirdek import guc
    d = guc.dagilim_oku(_kare_2x2_sentetik())
    k = d["konumlar"]
    beklenen_toplam = sum(100.0 * (dn + 1) + cn for dn in range(4) for cn in range(4))
    toplam = sum(v["toplam"][0] for v in k.values())
    kontrol("16 cubuk (4 demet x 4)", len(k) == 16, "-> %d anahtar" % len(k))
    kontrol("toplam korunur", abs(toplam - beklenen_toplam) < 1e-9,
            "%.1f / %.1f" % (toplam, beklenen_toplam))
    kontrol("tam_kor isareti", d.get("tam_kor") is True)
    kontrol("anahtar (demet, cubuk) bicimi",
            ((1, 0), (1, 1)) in k and k.get(((1, 0), (1, 1)), {}).get("toplam", (0,))[0] == 203.0,
            "-> %r" % sorted(k)[:3])
    kontrol("kafes_turleri [kare, kare]", d.get("kafes_turleri") == ["kare", "kare"])


def test_altigen_ic_ice_anahtar_sentetik():
    """Altigen-icinde-altigen: her duzeyde get_universe_index; 49 ayri anahtar."""
    print("\n[GK2] Altigen ic ice: her duzeyde (halka, sira) (sentetik)")
    from cekirdek import guc, altigen
    kor = _altigen_kafes(9101, 2, 5.0, "x")
    ic = _altigen_kafes(9102, 2, 1.3, "y")
    satirlar, beklenen = [], {}
    for n, (kx, ky) in enumerate(sorted(kor._natural_indices)):
        for m, (cx, cy) in enumerate(sorted(ic._natural_indices)):
            deger = 10.0 * (n + 1) + m
            satirlar.append({"duzeyler": [(9101, kx, ky), (9102, cx, cy)],
                             "ort": deger, "sap": 0.5})
            anahtar = (tuple(kor.get_universe_index((kx, ky))),
                       tuple(ic.get_universe_index((cx, cy))))
            beklenen[anahtar] = deger
    d = guc.dagilim_oku(_sahte_sp(satirlar, 2, [kor, ic]))
    k = d["konumlar"]
    kontrol("49 ayri anahtar", len(k) == 49, "-> %d" % len(k))
    kontrol("her anahtarin degeri dogru",
            all(abs(k.get(a, {"toplam": (-1,)})["toplam"][0] - v) < 1e-12
                for a, v in beklenen.items()))
    kor_kon = set(altigen.konumlar(2, "x"))
    ic_kon = set(altigen.konumlar(2, "y"))
    kontrol("anahtarlar altigen.konumlar ile ortusur",
            all(len(a) == 2 and a[0] in kor_kon and a[1] in ic_kon for a in k))
    kontrol("kafes_turleri [altigen, altigen]",
            d.get("kafes_turleri") == ["altigen", "altigen"])


def test_tek_demet_geriye_uyum_sentetik():
    """Tek duzeyli (tek demet) model: anahtarlar (x, y), degerler aynen."""
    print("\n[GK3] Tek demet: geriye uyum (sentetik)")
    from cekirdek import guc
    ic = _kare_kafes(9201, 3, 1.26)
    satirlar = [{"duzeyler": [(9201, x, y)], "ort": 1.0 + 0.1 * x + 0.01 * y,
                 "sap": 0.001 * (x + 1)} for y in range(3) for x in range(3)]
    d = guc.dagilim_oku(_sahte_sp(satirlar, 1, [ic]))
    k = d["konumlar"]
    kontrol("9 anahtar, (x, y) int ikilisi",
            len(k) == 9 and all(isinstance(a, tuple) and len(a) == 2
                                and all(type(i) is int for i in a) for a in k))
    kontrol("sira DataFrame sirasi", list(k) == [(x, y) for y in range(3) for x in range(3)])
    kontrol("degerler bitwise ayni",
            all(k[(x, y)]["eksenel"] == [(1.0 + 0.1 * x + 0.01 * y, 0.001 * (x + 1))]
                for y in range(3) for x in range(3)))
    kontrol("tam_kor False", d.get("tam_kor") is False)
    kontrol("eski alanlar", all(a in d for a in ("kafes_turu", "kafes", "kafes_id",
                                                 "eksenel_dilim", "konumlar", "notlar")))
    f = guc.tepe_faktorleri(d)
    kontrol("tek demette demet alanlari None",
            f["demetler"] is None and f["sicak_demet"] is None and f["tam_kor"] is False)


def test_katmanli_ayni_konum_toplanir():
    """Ayni cubuk konumu iki eksenel katmanda: dilimler toplanmali, ezilmemeli."""
    print("\n[GK4] Eksenel katman: ayni konum iki katmanda (sentetik)")
    from cekirdek import guc
    ic = _kare_kafes(9301, 2, 1.26)
    satirlar = []
    ornek = 0
    for katman, hucre in ((0, 11), (1, 12)):          # alt katman, ust katman
        for y in range(2):
            for x in range(2):
                for z in (1, 2):
                    deger = (5.0 + x + y) if z - 1 == katman else 0.0
                    satirlar.append({"duzeyler": [(9301, x, y)], "hucreler": [hucre],
                                     "ornek": ornek, "z": z, "ort": deger, "sap": 0.1})
                ornek += 1
    d = guc.dagilim_oku(_sahte_sp(satirlar, 1, [ic], dilim_var=True))
    k = d["konumlar"]
    kontrol("4 cubuk konumu", len(k) == 4, "-> %d" % len(k))
    iyi = all(abs(k[(x, y)]["eksenel"][0][0] - (5.0 + x + y)) < 1e-12
              and abs(k[(x, y)]["eksenel"][1][0] - (5.0 + x + y)) < 1e-12
              for y in range(2) for x in range(2))
    kontrol("alt dilim ust katmanin sifiriyla ezilmedi", iyi,
            "-> (0,0): %r" % (k.get((0, 0), {}).get("eksenel"),))
    kontrol("birlesme notu var", any("katman" in n for n in d["notlar"]))


def test_tepe_faktorleri_tam_kor():
    """Demet ortalamalari, demet tepeleri ve kor geneli F_dH."""
    print("\n[GK5] Tepe faktorleri: tam kor (sentetik)")
    from cekirdek import guc
    d = guc.dagilim_oku(_kare_2x2_sentetik())
    f = guc.tepe_faktorleri(d)
    ort = sum(100.0 * (dn + 1) + cn for dn in range(4) for cn in range(4)) / 16.0
    kontrol("F_dH kor geneli", abs(f["F_dH"] - 403.0 / ort) < 1e-12, "%.6f" % f["F_dH"])
    kontrol("sicak cubuk sicak demette", f["sicak_cubuk"] == ((1, 1), (1, 1)),
            "-> %r" % (f["sicak_cubuk"],))
    dm = f.get("demetler") or {}
    kontrol("4 demet", len(dm) == 4)
    kontrol("demet ortalamasi (bagil)",
            abs(dm[(0, 0)]["ortalama"][0] - 101.5 / ort) < 1e-12)
    kontrol("demet tepesi ve konumu",
            abs(dm[(1, 0)]["tepe"][0] - 203.0 / ort) < 1e-12
            and dm[(1, 0)]["tepe_cubuk"] == ((1, 0), (1, 1)))
    kontrol("demet ici F_dH", abs(dm[(0, 1)]["F_dH_ic"] - 303.0 / 301.5) < 1e-12)
    kontrol("sicak demet (1,1)", f["sicak_demet"] == (1, 1))
    kontrol("F_demet", abs(f["F_demet"] - 401.5 / ort) < 1e-12)
    kontrol("demet ortalamalarinin ortalamasi 1 (esit cubuk sayisi)",
            abs(sum(v["ortalama"][0] for v in dm.values()) / 4 - 1.0) < 1e-12)
    kontrol("konum metni demet + cubuk",
            "demet" in guc.konum_metni(f["sicak_cubuk"], "kare").lower())


def test_konum_metni_ic_ice():
    print("\n[GK6] konum_metni ic ice anahtar")
    from cekirdek import guc
    m = guc.konum_metni(((0, 1), (2, 3)), "kare")
    kontrol("kare: demet ve cubuk", "x = 1, y = 2" in m and "x = 3, y = 4" in m, m)
    m = guc.konum_metni(((0, 1), (1, 0)), "altigen", ["altigen", "altigen"])
    kontrol("altigen: iki duzey halka", m.count("halka") == 2, m)
    kontrol("tek demet eski metin", guc.konum_metni((0, 0), "kare") == "x = 1, y = 1")


def test_cubuk_merkezi_kare():
    """Konum -> fiziksel merkez (cizim ve nokta-hucre olcumu ayni islevi kullanir)."""
    print("\n[GK7] cubuk_merkezi (kare)")
    from cekirdek import guc
    d = guc.dagilim_oku(_kare_2x2_sentetik())
    x, y = guc.cubuk_merkezi(d, ((1, 0), (0, 1)))
    kontrol("merkez (1.0, -1.0)", abs(x - 1.0) < 1e-12 and abs(y + 1.0) < 1e-12,
            "-> (%.3f, %.3f)" % (x, y))


def test_referans_eksik_demet_uyarisi():
    """Hedef cubuk kordaki her demette yoksa harita eksik kalir: uyari."""
    print("\n[GK8] Dogrulama: hedef cubuk bazi demetlerde yok")
    from cekirdek.dogrula import referans
    spec = _kor_spec_2x2()
    b = referans.guc_dagilimi_kontrol(spec)
    kontrol("tum demetlerde varken uyari yok",
            not any("içermeyen" in x.mesaj for x in b))
    import copy
    s2 = copy.deepcopy(spec)
    d = copy.deepcopy(s2["demetler"][0])
    d["ad"] = "d5_bos"
    d["harita"] = ["kkkkk"] * 5
    s2["demetler"].append(d)
    s2["kor"]["harita"] = ["AB", "AA"]
    s2["kor"]["anahtar"] = {"A": "d5", "B": "d5_bos"}
    b = referans.guc_dagilimi_kontrol(s2)
    kontrol("eksik demet uyarisi", any("içermeyen" in x.mesaj for x in b),
            "-> %r" % [x.mesaj for x in b])


# ============================================================================
# HIZLI -- arayuz
# ============================================================================

def _uygulama():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _widget_kur(dagilim):
    from cekirdek import guc
    from arayuz.guc_harita import GucHaritaWidget
    w = GucHaritaWidget()
    w.resize(900, 700)
    f = guc.tepe_faktorleri(dagilim)
    w.sonuc_ayarla({"guc": {"dagilim": dagilim, "faktorler": f, "korunum": 0.0}})
    return w, f


def test_arayuz_tam_kor_gorunumleri():
    print("\n[GK9] Arayuz: Demet / Cubuk gorunumu")
    uyg = _uygulama()
    from cekirdek import guc
    w, f = _widget_kur(guc.dagilim_oku(_kare_2x2_sentetik()))
    kontrol("olcek anahtari gorunur", not w.olcek.isHidden())
    kontrol("iki secenek (demet, cubuk)",
            [w.olcek.itemData(i) for i in range(w.olcek.count())] == ["demet", "cubuk"])
    w.olcek.setCurrentIndex(w.olcek.findData("demet"))
    kontrol("demet gorunumu cizildi", len(w._ipucu_ogeleri) == 4)
    w.olcek.setCurrentIndex(w.olcek.findData("cubuk"))
    kontrol("cubuk gorunumu cizildi", len(w._ipucu_ogeleri) == 16)
    x, y = guc.cubuk_merkezi(w.dagilim, f["sicak_cubuk"])
    m = w.ipucu_metni(x, y) or ""
    kontrol("ipucu konum + deger +- sigma", "demet" in m and "±" in m, m)
    kontrol("belirsizlik notu gorunur", not w.belirsizlik.isHidden()
            and "korelasyon" in w.belirsizlik.text())
    uyg  # noqa: B018


def test_arayuz_altigen_kor():
    print("\n[GK10] Arayuz: altigen kor")
    uyg = _uygulama()
    from cekirdek import guc
    kor = _altigen_kafes(9401, 2, 5.0, "x")
    ic = _altigen_kafes(9402, 2, 1.3, "y")
    satirlar = [{"duzeyler": [(9401, kx, ky), (9402, cx, cy)],
                 "ort": 1.0 + 0.1 * n + 0.01 * m, "sap": 0.01}
                for n, (kx, ky) in enumerate(sorted(kor._natural_indices))
                for m, (cx, cy) in enumerate(sorted(ic._natural_indices))]
    w, f = _widget_kur(guc.dagilim_oku(_sahte_sp(satirlar, 2, [kor, ic])))
    w.olcek.setCurrentIndex(w.olcek.findData("cubuk"))
    kontrol("49 cubuk cizildi", len(w._ipucu_ogeleri) == 49)
    w.olcek.setCurrentIndex(w.olcek.findData("demet"))
    kontrol("7 demet cizildi", len(w._ipucu_ogeleri) == 7)
    uyg  # noqa: B018


def test_arayuz_tek_demet_degismedi():
    print("\n[GK11] Arayuz: tek demet gorunumu degismedi")
    uyg = _uygulama()
    from cekirdek import guc
    ic = _kare_kafes(9501, 3, 1.26)
    satirlar = [{"duzeyler": [(9501, x, y)], "ort": 1.0 + x, "sap": 0.01}
                for y in range(3) for x in range(3)]
    w, f = _widget_kur(guc.dagilim_oku(_sahte_sp(satirlar, 1, [ic])))
    kontrol("olcek anahtari gizli", w.olcek.isHidden())
    kontrol("gorunum secenekleri aynen",
            [w.gorunum.itemData(i) for i in range(w.gorunum.count())] == ["toplam", "dilim"])
    kontrol("belirsizlik etiketi tek demette gizli", w.belirsizlik.isHidden())
    uyg  # noqa: B018


# ============================================================================
# YAVAS -- Monte Carlo: 2x2 kare kor
# ============================================================================

# Demet konumu (x, y; y alttan) -> zenginlik (%). (0,0) bilerek en sicak.
ZENGINLIK_2X2 = {(0, 0): 5.0, (1, 0): 3.5, (0, 1): 2.6, (1, 1): 2.0}


def _kor_spec_2x2():
    from cekirdek import sema
    spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    d = sema.demet_bul(spec, "demet_17x17")
    d["ad"] = "d5"
    d["boyut"] = [5, 5]
    d["harita"] = ["yyyyy", "yyyyy", "yykyy", "yyyyy", "yyyyy"]
    spec["demetler"] = [d]
    spec["kor"].update(tur="kare_kafes", demet=None, adim=1.26 * 5, boyut=[2, 2],
                       harita=["AA", "AA"], anahtar={"A": "d5"})
    spec["guc_dagilimi"] = {"var": True, "cubuk": "yakit_cubugu", "bolge": 0,
                            "skor": "kappa-fission", "eksenel_dilim": 1,
                            "toplam_guc": None}
    spec["ayarlar"].update(parcacik=2000, cevrim=40, pasif=10)
    return spec


def _hedef_hucre(model):
    t = next(t for t in model.tallies if t.name == "guc_dagilimi")
    cid = int(t.filters[0].bins[0])
    return model.geometry.get_all_cells()[cid]


def _yol_kafes_indeksi(yol, sira=0):
    """'u8->c11->l1(0,1)->...' -> sira. kafes duzeyinin (x, y) indeksi."""
    bulunan = re.findall(r"l\d+\((-?\d+),(-?\d+)(?:,(-?\d+))?\)", yol)
    return (int(bulunan[sira][0]), int(bulunan[sira][1]))


def _uo2(zenginlik, sicaklik=None):
    import openmc
    m = openmc.Material(name="UO2 %%%.1f" % zenginlik)
    m.add_element("U", 1.0, enrichment=zenginlik)
    m.add_element("O", 2.0)
    m.set_density("g/cm3", 10.4)
    if sicaklik:
        m.temperature = sicaklik
    return m


def _dagitik_malzeme(model, hucre, esleme):
    """Tek hucreye ornek basina malzeme (OpenMC 'distribmat'); esleme: yol -> mal."""
    import openmc
    model.geometry.determine_paths()
    mats = [esleme(yol) for yol in hucre.paths]
    hucre.fill = mats
    model.materials = openmc.Materials(
        list(model.materials) + [m for m in {id(m): m for m in mats}.values()])


def _kos(model, dizin):
    import openmc
    os.makedirs(dizin, exist_ok=True)
    eski = os.getcwd()
    try:
        os.chdir(dizin)
        sp = openmc.StatePoint(model.run(threads=ISLEM_PARCACIGI, output=False))
    finally:
        os.chdir(eski)
    return sp


_BUL_BETIGI = """
import json, sys, os
import openmc.lib
os.chdir(sys.argv[1])
noktalar = json.loads(sys.argv[2])
openmc.lib.init(args=["-s", "1"], output=False)
cikti = []
for p in noktalar:
    h, ornek = openmc.lib.find_cell(p)
    cikti.append([h.id, ornek])
openmc.lib.finalize()
print("SONUC" + json.dumps(cikti))
"""


def _nokta_hucre(dizin, noktalar):
    """Noktalari AYRI SURECTE openmc.lib.find_cell ile bulur: [(hucre, ornek)].
    openmc.lib ayni surecte C++ terminate ile tum pytest'i oldurebilir.
    XML'ler ayri dizine kopyalanir: init summary.h5 yazar, acik StatePoint
    ayni dosyayi kilitler."""
    import glob
    import shutil
    bul = os.path.join(dizin, "nokta_hucre")
    os.makedirs(bul, exist_ok=True)
    for xml in glob.glob(os.path.join(dizin, "*.xml")):
        shutil.copy(xml, bul)
    r = subprocess.run([sys.executable, "-c", _BUL_BETIGI, bul, json.dumps(noktalar)],
                       capture_output=True, text=True, timeout=300,
                       env=dict(os.environ, OMP_NUM_THREADS="1"))
    satir = [s for s in r.stdout.splitlines() if s.startswith("SONUC")]
    if r.returncode != 0 or not satir:
        raise RuntimeError("find_cell alt sureci basarisiz: %s" % r.stderr[-2000:])
    return [tuple(x) for x in json.loads(satir[0][5:])]


def _ornek_degerleri(sp):
    """distribcell ornek indeksi -> ham ortalama (2B, tek bin)."""
    df = sp.get_tally(name="guc_dagilimi").get_pandas_dataframe()
    return {int(i): float(m) for i, m in zip(df[("distribcell")] if "distribcell" in df
                                              else df.iloc[:, 0], df["mean"])}


def _nokta_hucre_dogrula(etiket, sp, dagilim, dizin, hucre_id):
    """Her anahtarin fiziksel merkezi (guc.cubuk_merkezi) gercekten o degerin
    geldigi distribcell ornegine mi dusuyor?"""
    from cekirdek import guc
    anahtarlar = list(dagilim["konumlar"])
    noktalar = [list(guc.cubuk_merkezi(dagilim, a)) + [0.0] for a in anahtarlar]
    bulunan = _nokta_hucre(dizin, noktalar)
    ornek_deger = _ornek_degerleri(sp)
    hatali = []
    for a, (hid, ornek) in zip(anahtarlar, bulunan):
        if hid != hucre_id or abs(ornek_deger[ornek] - dagilim["konumlar"][a]["toplam"][0]) > 0:
            hatali.append((a, hid, ornek))
    kontrol("%s: nokta-hucre eslesmesi %d/%d" % (etiket, len(anahtarlar) - len(hatali),
                                                 len(anahtarlar)),
            not hatali, "-> ilk hatalar %r" % hatali[:3])


def test_kare_kor_2x2_mc(gecici):
    """
    2x2 kare kor, demetler FARKLI zenginlikte (ornek basina malzeme). Beklenen:
    harita 96 cubugun hepsini ayri gosterir, toplam korunur, demet ortalamalari
    zenginlik sirasinda, F_dH en zengin demette.
    """
    print("\n[GK12] 2x2 kare kor (Monte Carlo)")
    import openmc
    from cekirdek import kurucu, guc
    spec = _kor_spec_2x2()
    model, _ = kurucu.kur(spec)
    hucre = _hedef_hucre(model)
    mats = {k: _uo2(z, 900.0) for k, z in ZENGINLIK_2X2.items()}
    _dagitik_malzeme(model, hucre, lambda yol: mats[_yol_kafes_indeksi(yol, 0)])
    dizin = os.path.join(gecici, "kor2x2")
    sp = _kos(model, dizin)

    d = guc.dagilim_oku(sp)
    f = guc.tepe_faktorleri(d)
    konum = d["konumlar"]

    # Bagimsiz referans: ham DataFrame + summary'deki hucre yollari
    geo = sp.summary.geometry
    geo.determine_paths()
    yollar = geo.get_all_cells()[hucre.id].paths
    ham = _ornek_degerleri(sp)
    demet_ham = {}
    for i, yol in enumerate(yollar):
        demet_ham.setdefault(_yol_kafes_indeksi(yol, 0), []).append(ham[i])
    ref = float(sp.get_tally(name="guc_toplam_ref").get_pandas_dataframe()["mean"].sum())
    toplam = sum(v["toplam"][0] for v in konum.values())
    bagil = abs(toplam / ref - 1.0)
    print("  eski-kod belirtisi olurdu: harita %d anahtar; demet ham ortalamalari: %s"
          % (len(konum), {k: round(sum(v) / len(v) / 1e6, 4) for k, v in demet_ham.items()}))

    kontrol("haritada 96 cubuk (4 x 24)", len(konum) == 96, "-> %d" % len(konum))
    kontrol("toplam korunumu (bagil fark %.1e)" % bagil, bagil < 1e-9)
    dm = f.get("demetler") or {}
    sira = sorted(ZENGINLIK_2X2, key=ZENGINLIK_2X2.get, reverse=True)
    ortalar = [dm.get(k, {"ortalama": (float("nan"),)})["ortalama"][0] for k in sira]
    kontrol("demet ortalamalari zenginlik sirasinda", all(
        ortalar[i] > ortalar[i + 1] for i in range(len(ortalar) - 1)),
        "-> %s" % ["%.4f" % o for o in ortalar])
    sicak = f["sicak_cubuk"]
    kontrol("F_dH en zengin demette (%s)" % (sira[0],),
            isinstance(sicak, tuple) and sicak[0] == sira[0], "-> %r" % (sicak,))
    ham_ort = {k: sum(v) / len(v) for k, v in demet_ham.items()}
    ort_hepsi = sum(ham.values()) / len(ham)
    kontrol("demet ortalamalari ham referansla ayni", all(
        abs(dm[k]["ortalama"][0] - ham_ort[k] / ort_hepsi) < 1e-9 for k in ham_ort))
    _nokta_hucre_dogrula("kare", sp, d, dizin, hucre.id)


# ============================================================================
# YAVAS -- Monte Carlo: altigen-icinde-altigen (spec'e bagli degil)
# ============================================================================

def _altigen_model(dizin):
    """7 demet x 7 cubuk; kor 'x', demet 'y' yonelimli (VVER gibi 90 derece).
    Tek yakit hucresi, demet basina farkli zenginlik (distribmat)."""
    import openmc
    from cekirdek import altigen
    su = openmc.Material(name="su")
    su.add_element("H", 2.0)
    su.add_element("O", 1.0)
    su.set_density("g/cm3", 1.0)
    su.add_s_alpha_beta("c_H_in_H2O")
    yakit = _uo2(3.0)
    r = openmc.ZCylinder(r=0.45)
    c_yakit = openmc.Cell(fill=yakit, region=-r)
    cubuk = openmc.Universe(cells=[c_yakit, openmc.Cell(fill=su, region=+r)])
    su_u = openmc.Universe(cells=[openmc.Cell(fill=su)])
    ic = openmc.HexLattice()
    ic.center, ic.pitch, ic.orientation, ic.outer = (0.0, 0.0), (1.3,), "y", su_u
    ic.universes = [[cubuk] * k for k in altigen.halka_uzunluklari(2)]
    demet = openmc.Universe(cells=[openmc.Cell(fill=ic)])
    kor = openmc.HexLattice()
    kor.center, kor.pitch, kor.orientation, kor.outer = (0.0, 0.0), (4.6,), "x", su_u
    kor.universes = [[demet] * k for k in altigen.halka_uzunluklari(2)]
    sinir = openmc.ZCylinder(r=2.2 * 4.6, boundary_type="reflective")
    kok = openmc.Universe(cells=[openmc.Cell(fill=kor, region=-sinir)])
    model = openmc.Model(geometry=openmc.Geometry(kok),
                         materials=openmc.Materials([su, yakit]))
    s = openmc.Settings()
    s.batches, s.inactive, s.particles = 40, 10, 2000
    s.source = openmc.IndependentSource(space=openmc.stats.Point())
    model.settings = s
    tal = openmc.Tally(name="guc_dagilimi")
    tal.scores = ["kappa-fission"]
    tal.filters = [openmc.DistribcellFilter(c_yakit)]
    ref = openmc.Tally(name="guc_toplam_ref")
    ref.scores = ["kappa-fission"]
    ref.filters = [openmc.CellFilter(c_yakit)]
    model.tallies = openmc.Tallies([tal, ref])
    return model, kor, c_yakit


def test_altigen_ic_ice_mc(gecici):
    print("\n[GK13] Altigen-icinde-altigen kor (Monte Carlo)")
    from cekirdek import guc
    model, kor, c_yakit = _altigen_model(gecici)
    # Sicak demet: dis halkanin 3. ogesi (universes[0][2]) %5, digerleri %2
    sicak_demet = (0, 2)
    zengin, fakir = _uo2(5.0), _uo2(2.0)

    def esle(yol):
        idx = _yol_kafes_indeksi(yol, 0)
        return zengin if tuple(kor.get_universe_index(idx)) == sicak_demet else fakir
    _dagitik_malzeme(model, c_yakit, esle)
    dizin = os.path.join(gecici, "altigen")
    sp = _kos(model, dizin)
    d = guc.dagilim_oku(sp)
    f = guc.tepe_faktorleri(d)
    konum = d["konumlar"]
    ref = float(sp.get_tally(name="guc_toplam_ref").get_pandas_dataframe()["mean"].sum())
    toplam = sum(v["toplam"][0] for v in konum.values())
    bagil = abs(toplam / ref - 1.0)
    kontrol("49 cubuk", len(konum) == 49, "-> %d" % len(konum))
    kontrol("toplam korunumu (bagil fark %.1e)" % bagil, bagil < 1e-9)
    kontrol("kafes turleri", d.get("kafes_turleri") == ["altigen", "altigen"])
    kontrol("sicak demet %%5'lik demet", f.get("sicak_demet") == sicak_demet,
            "-> %r" % (f.get("sicak_demet"),))
    kontrol("F_dH %%5'lik demette", f["sicak_cubuk"][0] == sicak_demet,
            "-> %r" % (f["sicak_cubuk"],))
    _nokta_hucre_dogrula("altigen", sp, d, dizin, c_yakit.id)


HIZLI = [
    test_kare_kor_anahtar_sentetik, test_altigen_ic_ice_anahtar_sentetik,
    test_tek_demet_geriye_uyum_sentetik, test_katmanli_ayni_konum_toplanir,
    test_tepe_faktorleri_tam_kor, test_konum_metni_ic_ice, test_cubuk_merkezi_kare,
    test_referans_eksik_demet_uyarisi,
    test_arayuz_tam_kor_gorunumleri, test_arayuz_altigen_kor, test_arayuz_tek_demet_degismedi,
]
YAVAS = [
    test_kare_kor_2x2_mc, test_altigen_ic_ice_mc,
]
