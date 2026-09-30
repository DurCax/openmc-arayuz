# -*- coding: utf-8 -*-
"""
 test_geometri_guc.py  --  G-2: guc dagilimi agac modunda (karisik kafes, yerlesim, kesik)

 Kisa MC ile: (a) kare cekirdek altigen blok deliginde, (b) R3b altigen kor,
 (c) kare kor + tamburlar, iki ornekli yerlesim (ayni kafes iki kez) ve
 (a-yakit) kesik yakit bloklari. Olculen: anahtar sayisi = hedef cubuk ornegi
 (geometri.hacim.ornek_sayisi), toplam korunumu, kesik cubuklar F_dH disi.
 Hizli: anahtar metni ve yerlesim duzeyi merkezleri.
 Sozlesme: testler/ortak_test.py.
"""

import copy
import os

from testler.ortak_test import kontrol, ISLEM_PARCACIGI
from testler import geometri_ortak as go


def iki_ornekli():
    """(c)'nin kare kafesi bir parca; kok kutuya iki liste ornegiyle konur."""
    s = go.duzenek_c()
    kok = s["geometri"]["kok"]
    s["geometri"]["parcalar"] = [{"ad": "kor3", "dugum": kok["ic"]}]
    kok.update(kesit={"sekil": "dikdortgen", "boyut": [140.0, 70.0]},
               ic={"tur": "malzeme", "ad": "berilyum"}, halkalar=[],
               sinir={"yan": "reflective", "alt": "reflective", "ust": "reflective"},
               yerlesimler=[{"ad": "iki_kor", "mod": "liste",
                             "konumlar": [[-34.0, 0.0], [34.0, 0.0]],
                             "kesit": {"sekil": "dikdortgen", "boyut": [64.26, 64.26]},
                             "icerik": {"tur": "bilesen", "ad": "kor3"}}])
    s["tamburlar"], s["geometri"]["gruplar"] = [], []
    return s


def _gucle(spec):
    yakit = [c["ad"] for c in spec["cubuklar"] if c["ad"].startswith("yakit")]
    spec["guc_dagilimi"] = {"var": True, "cubuklar": [{"cubuk": c, "bolge": 0} for c in yakit],
                            "skor": "kappa-fission", "eksenel_dilim": 1, "toplam_guc": None}
    spec["ayarlar"].update(parcacik=2000, cevrim=20, pasif=8)
    return spec, yakit


def test_yerlesim_konum_metni():
    print("\n[GG1] yerlesim duzeyi anahtar metni ve merkezi")
    from cekirdek import guc, guc_kor
    d = guc_kor.YerlesimDuzeyi(merkezler={("iki_kor", 0): (-34.0, 0.0),
                                          ("iki_kor", 1): (34.0, 0.0)})
    kontrol("eleman_merkezi = oteleme", guc.eleman_merkezi(d, ("iki_kor", 1)) == (34.0, 0.0))
    metin = guc.konum_metni((("iki_kor", 1), (0, 0), (2, 3)), None,
                            ["yerlesim", "kare", "kare"])
    kontrol("konum metni 'iki_kor #2'", "iki_kor #2" in metin, "-> %s" % metin)


def test_yavas_guc_agac(gecici):
    print("\n[GG2] agac modunda guc: anahtar = cubuk ornegi, korunum, kesik F_dH disi")
    from cekirdek import geometri, kosucu, kurucu
    from cekirdek.geometri import hacim
    for ad, uret, kesikli in (("a", go.duzenek_a, False), ("b", go.duzenek_b, False),
                              ("c", go.duzenek_c, False), ("iki", iki_ornekli, False),
                              ("a-yakit", lambda: go.duzenek_a(True), True)):
        spec, yakit = _gucle(uret())
        # beklenen anahtar = hedef hucrelerin distribcell ornek sayisi (gizli
        # konumlar dahil: OpenMC onlari da sayar); kesiksizde agac gezintisinin
        # yakit ornegiyle ayni
        model, bilgi = kurucu.kur(copy.deepcopy(spec))
        model.geometry.determine_paths()
        beklenen = sum(h.num_instances for _a, h in bilgi.get("guc_hucreler") or [])
        if not kesikli:
            m = geometri.model(spec)
            gezinti = sum(hacim.ornek_sayisi(m, mal) for mal in
                          {m.tanimlar["cubuk"][c]["bolgeler"][0]["malzeme"] for c in yakit})
            kontrol("(%s) distribcell ornegi = gezinti ornegi" % ad, beklenen == gezinti,
                    "-> %d / %d" % (beklenen, gezinti))
        kosu = kosucu.calistir(spec, os.path.join(gecici, ad), is_parcacigi=ISLEM_PARCACIGI)
        r = kosucu.sonuc_oku(kosu["statepoint"]) if kosu["basarili"] else {}
        g = r.get("guc") or {}
        d, f = g.get("dagilim") or {}, g.get("faktorler") or {}
        n = len(d.get("konumlar") or {})
        kesik = len(d.get("kesik_cubuklar") or [])
        print("  (%s) k = %.5f, %d anahtar (beklenen %d), kesik %d, F_dH %.3f"
              % (ad, (r.get("keff") or (0, 0))[0], n, beklenen, kesik, f.get("F_dH") or 0))
        kontrol("(%s) anahtar sayisi = yakit ornegi" % ad, n == beklenen, "-> %d" % n)
        kontrol("(%s) toplam korunumu" % ad, g.get("korunum") is not None
                and abs(g["korunum"]) < 1e-9, "-> %s" % g.get("korunum"))
        kontrol("(%s) kesik cubuk %s" % (ad, "var, F_dH disi" if kesikli else "yok"),
                (kesik > 0 and f.get("cubuk_sayisi") == n - kesik) if kesikli else kesik == 0)


HIZLI = [test_yerlesim_konum_metni]
YAVAS = [test_yavas_guc_agac]
