# -*- coding: utf-8 -*-
"""
 test_k3_pin_tablosu.py  --  v3 K3: pin gucu tablosu (cekirdek/guc_tablo.py)

   [PT1] Tablo = harita: her satirin bagil gucu ve σ'si haritanin cizdigi
         faktorler["bagil"] degeriyle AYNI; sicak pin tek ve F_ΔH'nin cubugu.
   [PT2] Toplam = toplam guc: Σ W = toplam_guc × hedef_payi; ortalama q′
         mutlak_guc'un lineer ortalamasi; kesik cubuk dahil toplam korunur.
   [PT3] 3B dilimler: Σ_k W_k = W; dilim q′ = W_k / Δz; tepe dilimin bagil
         degeri F_q; z araliklari guc mesh'inden.
   [PT4] Demet ortalamasi: tam korda faktorler["demetler"] ile ayni.
   [PT5] Ceyrek katlama: simetrik kafeste yorunge ortalamasi; asimetrik kafes,
         altigen ve gelismis modda REDDEDILIR (gerekceyle).
   [PT6] CSV: ondalik nokta, tam hassasiyet, baslik + pin basina satir; Excel
         yalniz openpyxl varsa (yeni bagimlilik yok; sahte modulle sinanir).

 Fixture: testler/veri/kosu_ornek (17x17 3B, 10 eksenel dilim; Monte Carlo
 KOSULMAZ). Sentetik dagilimlar kesik cubuk ve tam kor icin.
"""

import csv
import io
import math
import os
import sys
import types

from testler.ortak_test import KOK, kontrol
from testler.ortak_test import gereksinim  # v3 izlenebilirlik

FIXTURE = os.path.join(KOK, "testler", "veri", "kosu_ornek")


def _fixture():
    """(spec, guc sozlugu, mutlak, yukseklik) -- kosu_ornek'ten."""
    import json
    from cekirdek import geometri, guc, kosucu
    with open(os.path.join(FIXTURE, "spec.json"), encoding="utf-8") as f:
        spec = json.load(f)
    s = kosucu.sonuc_oku(os.path.join(FIXTURE, "statepoint.40.h5"))
    g = s["guc"]
    h = geometri.hedef_yuksekligi(spec)
    m = guc.mutlak_guc(g["faktorler"], spec["guc_dagilimi"]["toplam_guc"], h,
                       hedef_payi=g.get("hedef_payi"))
    return spec, g, m, h


def _konum(eksenel, sigma=0.001):
    toplam = sum(eksenel)
    return {"eksenel": [(d, sigma) for d in eksenel],
            "toplam": (toplam, sigma * math.sqrt(len(eksenel)))}


@gereksinim("R-V3-06")
def test_tablo_haritayla_ayni():
    print("\n[PT1] Tablo = harita (bagil, σ, sicak pin)")
    from cekirdek import guc_tablo
    _spec, g, m, h = _fixture()
    f = g["faktorler"]
    tablo = guc_tablo.pin_tablosu(g["dagilim"], f, m, h)
    kontrol("satir sayisi = konum sayisi (264)",
            len(tablo) == len(g["dagilim"]["konumlar"]) == 264, "-> %d" % len(tablo))
    farkli = [r["anahtar"] for r in tablo
              if (r["bagil"], r["sigma"]) != f["bagil"][r["anahtar"]]]
    kontrol("her satirin bagil gucu haritanin degeri (bit duzeyinde)", not farkli,
            "-> %d farkli" % len(farkli))
    sicak = [r for r in tablo if r["sicak"]]
    kontrol("tek sicak pin = F_ΔH cubugu",
            len(sicak) == 1 and sicak[0]["anahtar"] == f["sicak_cubuk"])
    kontrol("tablonun en buyuk bagil degeri = F_ΔH",
            max(r["bagil"] for r in tablo) == f["F_dH"])
    r0 = guc_tablo.satir_bul(tablo, f["sicak_cubuk"])
    kontrol("satir_bul anahtarla satiri verir; konum metni dolu",
            r0 is sicak[0] and r0["konum"].startswith("x = "))
    from cekirdek import guc
    kontrol("x/y = cubuk_merkezi [cm]",
            (r0["x"], r0["y"]) == guc.cubuk_merkezi(g["dagilim"], r0["anahtar"]))


@gereksinim("R-V3-06")
def test_tablo_toplami_toplam_guc():
    print("\n[PT2] Toplam = toplam guc; ortalama q′")
    from cekirdek import guc_tablo
    spec, g, m, h = _fixture()
    tablo = guc_tablo.pin_tablosu(g["dagilim"], g["faktorler"], m, h)
    beklenen = spec["guc_dagilimi"]["toplam_guc"] * (g.get("hedef_payi") or 1.0)
    toplam = guc_tablo.tablo_toplami(tablo)
    kontrol("Σ W = toplam_guc × hedef_payi", abs(toplam / beklenen - 1.0) < 1e-12,
            "-> %.6g / %.6g" % (toplam, beklenen))
    q_ort = sum(r["q"] for r in tablo) / len(tablo)
    kontrol("ortalama q′ = mutlak lineer ortalama",
            abs(q_ort / m["lineer_ortalama_W_cm"] - 1.0) < 1e-12,
            "-> %.4f / %.4f W/cm" % (q_ort, m["lineer_ortalama_W_cm"]))
    kontrol("q′ = W / aktif yukseklik", all(abs(r["q"] - r["W"] / h) < 1e-9 for r in tablo))
    bos = guc_tablo.pin_tablosu(g["dagilim"], g["faktorler"])
    kontrol("mutlak guc yoksa W/q′ None, toplam None",
            all(r["W"] is None and r["q"] is None for r in bos)
            and guc_tablo.tablo_toplami(bos) is None)


def test_kesik_cubuk_toplami():
    print("\n[PT2b] Kesik cubuk: F_ΔH disi ama toplam guc korunur")
    from cekirdek import guc, guc_tablo
    konumlar = {(0, 0): _konum([2.0]), (1, 0): _konum([1.0]), (0, 1): _konum([1.0]),
                (1, 1): _konum([0.4])}
    d = {"konumlar": konumlar, "eksenel_dilim": 1, "tam_kor": False,
         "kafes_turu": "kare", "kesik_cubuklar": [(1, 1)], "kafesler": [_kare(2)]}
    f = guc.tepe_faktorleri(d)
    m = guc.mutlak_guc(f, 1000.0, 10.0, hedef_payi=0.8)
    tablo = guc_tablo.pin_tablosu(d, f, m, 10.0)
    kesik = guc_tablo.satir_bul(tablo, (1, 1))
    kontrol("kesik satir isaretli, sicak degil", kesik["kesik"] and not kesik["sicak"])
    kontrol("Σ W (kesik dahil) = 1000 × 0.8", abs(guc_tablo.tablo_toplami(tablo) - 800.0) < 1e-9,
            "-> %r" % guc_tablo.tablo_toplami(tablo))
    kontrol("kesik bagil = toplam / ortalama_cubuk",
            abs(kesik["bagil"] - 0.4 / f["ortalama_cubuk"]) < 1e-12)


def test_dilimler():
    print("\n[PT3] 3B: dilim gucu, q′_k, F_q")
    from cekirdek import guc_tablo
    _spec, g, m, h = _fixture()
    f = g["faktorler"]
    tablo = guc_tablo.pin_tablosu(g["dagilim"], f, m, h)
    r = tablo[0]
    n = f["eksenel_dilim"]
    kontrol("her satirda %d dilim" % n, all(len(x["dilimler"]) == n for x in tablo))
    kontrol("Σ_k W_k = W", all(abs(sum(d["W"] for d in x["dilimler"]) - x["W"]) < 1e-6 * x["W"]
                               for x in tablo))
    z0, z1 = g["dagilim"]["eksenel_sinirlar"]
    dz = (z1 - z0) / n
    d0 = r["dilimler"][0]
    kontrol("dilim z araligi guc mesh'inden", abs(d0["z_alt"] - z0) < 1e-9
            and abs(d0["z_ust"] - (z0 + dz)) < 1e-9, "-> %r" % ((z0, z1),))
    kontrol("q′_k = W_k / Δz", all(abs(d["q"] - d["W"] / dz) < 1e-9 for d in r["dilimler"]))
    kontrol("dilim bagil = faktorler bagil_eksenel",
            [(d["bagil"], d["sigma"]) for d in r["dilimler"]] == f["bagil_eksenel"][r["anahtar"]])
    tepe = max(d["bagil"] for x in tablo for d in x["dilimler"])
    kontrol("en buyuk dilim bagil = F_q", abs(tepe - f["F_q"]) < 1e-12)
    kontrol("tepe_q = satirin en buyuk dilim q′",
            all(x["tepe_q"] == max(d["q"] for d in x["dilimler"]) for x in tablo))


def _kare(n, adim=1.0, evrenler=None):
    import openmc
    k = openmc.RectLattice()
    k.pitch = (adim, adim)
    k.lower_left = (-n * adim / 2.0, -n * adim / 2.0)
    if evrenler is None:
        u = openmc.Universe()
        evrenler = [[u] * n for _i in range(n)]
    k.universes = evrenler
    return k


def _tam_kor_dagilimi():
    """2x2 kor x 2x2 demet; demetler farkli gucte."""
    from cekirdek import guc
    konumlar = {}
    for D, carpan in (((0, 0), 1.2), ((1, 0), 1.0), ((0, 1), 1.0), ((1, 1), 0.8)):
        for p in ((0, 0), (1, 0), (0, 1), (1, 1)):
            konumlar[(D, p)] = _konum([carpan * (1.1 if p == (0, 0) else 1.0)])
    kor, demet = _kare(2, 2.0), _kare(2, 1.0)
    d = {"konumlar": konumlar, "eksenel_dilim": 1, "tam_kor": True, "kafes_turu": "kare",
         "kafes_turleri": ["kare", "kare"], "kafesler": [kor, demet], "duzey_sayisi": 2,
         "kesik_cubuklar": [], "tum_kafesler": {kor.id: kor, demet.id: demet}}
    return d, guc.tepe_faktorleri(d)


def test_demet_ozeti():
    print("\n[PT4] Demet ortalamasi = faktorler['demetler']")
    from cekirdek import guc_tablo
    d, f = _tam_kor_dagilimi()
    tablo = guc_tablo.pin_tablosu(d, f)
    ozet = guc_tablo.demet_ozeti(tablo)
    kontrol("4 demet", len(ozet) == 4)
    uyusur = all(abs(o["ortalama"] - f["demetler"][o["demet_anahtari"]]["ortalama"][0]) < 1e-12
                 and o["tepe"] == f["demetler"][o["demet_anahtari"]]["tepe"][0] for o in ozet)
    kontrol("ortalama ve tepe faktorlerle ayni", uyusur)
    kontrol("demet metni dolu", all(r["demet"] for r in tablo))


@gereksinim("R-V3-07")
def test_ceyrek_katlama():
    print("\n[PT5] Ceyrek katlama yalniz simetri dogrulanirsa")
    from cekirdek import guc_tablo
    _spec, g, m, h = _fixture()
    tablo = guc_tablo.pin_tablosu(g["dagilim"], g["faktorler"], m, h)
    katli, neden = guc_tablo.ceyrek_katla(tablo, g["dagilim"], _spec)
    kontrol("17x17 simetrik demet katlanir", katli is not None, "-> %s" % neden)
    # 17x17: ceyrek (9x9 = 81, orta satir/sutun dahil) - ceyrekteki kilavuz/olcum
    # konumlari (satir 9: 3, satir 12: 3, satir 14: 1, satir 15: 2 -> 9)
    kontrol("yorunge sayisi 81 - 9 = 72", katli is not None and len(katli) == 72,
            "-> %r" % (katli and len(katli)))
    r = katli[0]
    uyeler = [guc_tablo.satir_bul(tablo, a) for a in r["uyeler"]]
    kontrol("katli bagil = yorunge ortalamasi",
            abs(r["bagil"] - sum(u["bagil"] for u in uyeler) / len(uyeler)) < 1e-12)
    kontrol("katli σ = karesel toplam / m",
            abs(r["sigma"] - math.sqrt(sum(u["sigma"] ** 2 for u in uyeler)) / len(uyeler))
            < 1e-15)
    kontrol("Σ uye = 264", sum(len(x["uyeler"]) for x in katli) == 264)
    kontrol("asimetri olcusu raporlanir", all(x["asimetri"] >= 0 for x in katli))
    # asimetrik kafes: bir eleman farkli evren
    import openmc
    u1, u2 = openmc.Universe(), openmc.Universe()
    asim = _kare(2, evrenler=[[u1, u1], [u1, u2]])
    d = {"konumlar": {(i, j): _konum([1.0]) for i in range(2) for j in range(2)},
         "eksenel_dilim": 1, "tam_kor": False, "kafes_turu": "kare",
         "kafesler": [asim], "tum_kafesler": {asim.id: asim}, "kesik_cubuklar": []}
    from cekirdek import guc
    t2 = guc_tablo.pin_tablosu(d, guc.tepe_faktorleri(d))
    katli2, neden2 = guc_tablo.ceyrek_katla(t2, d)
    kontrol("asimetrik kafes reddedilir (gerekceli)", katli2 is None and neden2, neden2)
    katli3, neden3 = guc_tablo.ceyrek_katla(t2, dict(d, kafes_turu="altigen"))
    kontrol("altigen reddedilir", katli3 is None and neden3)
    katli4, neden4 = guc_tablo.ceyrek_katla(tablo, g["dagilim"], dict(_spec, kor={"tur": "agac"}))
    kontrol("gelismis (agac) modu reddedilir", katli4 is None and neden4)
    d5, f5 = _tam_kor_dagilimi()
    katli5, _n5 = guc_tablo.ceyrek_katla(guc_tablo.pin_tablosu(d5, f5), d5)
    kontrol("tam kor 2x2 x (2x2): 16 pin -> 4 yorunge",
            katli5 is not None and len(katli5) == 4, "-> %r" % (katli5 and len(katli5)))


def test_csv():
    print("\n[PT6] CSV: ondalik nokta, tam hassasiyet")
    from cekirdek import guc_tablo
    _spec, g, m, h = _fixture()
    tablo = guc_tablo.pin_tablosu(g["dagilim"], g["faktorler"], m, h)
    metin = guc_tablo.csv_metni(tablo)
    satirlar = list(csv.reader(io.StringIO(metin)))
    kontrol("baslik + 264 satir", len(satirlar) == 265, "-> %d" % len(satirlar))
    baslik = satirlar[0]
    kontrol("baslikta bagil guc, W, q′ ve dilim sutunlari (sabit anahtarlar)",
            "bagil" in baslik and "W" in baslik and "q_W_cm" in baslik
            and "q_W_cm_10" in baslik, "-> %r" % baslik[:12])
    i_b = baslik.index("bagil")
    r0 = satirlar[1]
    kontrol("bagil guc tam hassasiyet (repr)", float(r0[i_b]) == tablo[0]["bagil"])
    sayisal = r0[2:4] + r0[i_b:]
    kontrol("sayisal alanlarda virgul yok (ondalik nokta)",
            all("," not in x for x in sayisal) and "." in r0[i_b], "-> %r" % sayisal[:4])


class _SahteHucre:
    def __init__(self, deger):
        self.value = deger
        self.data_type = "n"


class _SahteSayfa:
    def __init__(self):
        self.hucreler = {}
        self.title = ""

    def cell(self, row, column, value=None):
        h = self.hucreler[(row, column)] = _SahteHucre(value)
        return h

    @property
    def satirlar(self):
        n = max((r for r, _c in self.hucreler), default=0)
        m = max((c for _r, c in self.hucreler), default=0)
        return [[getattr(self.hucreler.get((r, c)), "value", None) for c in range(1, m + 1)]
                for r in range(1, n + 1)]


class _SahteKitap:
    son = None

    def __init__(self):
        self.active = _SahteSayfa()
        self.kaydedilen = None
        _SahteKitap.son = self

    def save(self, yol):
        self.kaydedilen = yol


def test_excel_istege_bagli():
    print("\n[PT6b] Excel yalniz openpyxl varsa")
    from cekirdek import guc_tablo
    _spec, g, m, h = _fixture()
    tablo = guc_tablo.pin_tablosu(g["dagilim"], g["faktorler"], m, h)
    eski = sys.modules.get("openpyxl")
    try:
        sys.modules["openpyxl"] = None           # ice aktarma ImportError verir
        kontrol("openpyxl yoksa excel_var() False", guc_tablo.excel_var() is False)
        sahte = types.ModuleType("openpyxl")
        sahte.Workbook = _SahteKitap
        sys.modules["openpyxl"] = sahte
        kontrol("openpyxl varsa excel_var() True", guc_tablo.excel_var() is True)
        guc_tablo.excel_yaz(tablo, "/tmp/k3_sahte.xlsx")
        k = _SahteKitap.son
        kontrol("Excel: baslik + 264 satir, sayilar float",
                len(k.active.satirlar) == 265 and isinstance(k.active.satirlar[1][-1], float)
                and k.kaydedilen == "/tmp/k3_sahte.xlsx",
                "-> %d" % len(k.active.satirlar))
        kontrol("metin hucreleri data_type 's'",
                k.active.hucreler[(2, 2)].data_type == "s")
    finally:
        if eski is None:
            sys.modules.pop("openpyxl", None)
        else:
            sys.modules["openpyxl"] = eski


HIZLI = [test_tablo_haritayla_ayni, test_tablo_toplami_toplam_guc, test_kesik_cubuk_toplami,
         test_dilimler, test_demet_ozeti, test_ceyrek_katlama, test_csv,
         test_excel_istege_bagli]
YAVAS = []
