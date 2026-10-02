# -*- coding: utf-8 -*-
"""
 test_y1_duzeltme.py  --  v3 Y1 inceleme duzeltmeleri (profesor + python-reviewer)

   E1  2B mutlak: payda hucre ALANI ve cizgisel guc [W/cm]; Z_2B_YARI sonuca girmez
   E2  H filtresiz genel tally'den (ag fisil bolgeyi kapsamasa da S dogru)
   H3  v2 otomatik 2B proje: eski betik +/-1 cm, yeni +/-1e4 cm (belgeli fark);
       z sinirli geometri varsa ag modele kirpilir
   F8  bagil kip hacim agirlikli; F7 H adayi fission-q-prompt degil
   VTK bagimsiz beklenen dosya (2x3x4), skorsuz bagil hata -1, cok nuklid, atomik yazma
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import importlib.util
import math
import os
import tempfile

import numpy as np

from testler.ortak_test import kontrol, ORNEK, ISLEM_PARCACIGI, KOK


def _spec(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad))


def _sonuc(tur="duzenli", izg=None, ort=None, skorlar=("kappa-fission",),
           nuklidler=("total",), merkez=(0.0, 0.0, 0.0)):
    from cekirdek import mesh_tally as mt
    izg = tuple(np.asarray(g, float) for g in izg)
    boyut = tuple(len(g) - 1 for g in izg)
    if ort is None:
        ort = np.ones(boyut + (1, len(nuklidler), len(skorlar)))
    return mt.MeshSonuc(ad="t", tur=tur, izgaralar=izg, merkez=merkez, skorlar=skorlar,
                        nuklidler=nuklidler, enerji=None, ortalama=ort, sapma=0.01 * ort,
                        ozdeger=True)


# ---------------------------------------------------------------------------
# E1 -- 2B mutlak normalizasyon: el hesabi
# ---------------------------------------------------------------------------

def test_2b_mutlak_alan_ve_cizgisel_guc():
    print("\n[Y1-D1] 2B mutlak: W/cm3 = q' * o / (H * e * A) -- el hesabi, Z_2B_YARI'dan bagimsiz")
    from cekirdek import mesh_tally as mt
    z = mt.Z_2B_YARI
    # iki hucre: 1 cm x 2 cm ve 1 cm x 2 cm (A = 2 cm2), tum z kolonu
    s = _sonuc(izg=([0.0, 1.0, 2.0], [0.0, 2.0], [-z, z]),
               ort=np.array([3.0, 1.0]).reshape(2, 1, 1, 1, 1, 1))
    olcu, tur = mt.olcu(s, eksenel_sonsuz=True)
    kontrol("2B tam kolon: olcu = alan", tur == "alan" and np.allclose(olcu, 2.0), "-> %s %s"
            % (tur, olcu.ravel()))
    q = 100.0                              # W/cm (cizgisel guc)
    H = 4.0                                # eV / kaynak (genel tally)
    S = mt.kaynak_hizi(q, H)               # kaynak / (s cm)
    o, sg = mt.secim(s, "kappa-fission")
    w, _sw, birim = mt.normalize(o, sg, olcu, "mutlak", S, "kappa-fission", True, tur)
    # el hesabi: hucre 1 gucun 3/4'u -> 75 W/cm / 2 cm2 = 37.5 W/cm3; hucre 2 12.5 W/cm3
    kontrol("hucre degerleri 37.5 ve 12.5 W/cm3", np.allclose(w.ravel(), [37.5, 12.5]),
            "-> %s" % w.ravel())
    kontrol("birim W/cm3", birim == "W/cm³")
    # Z_2B_YARI degisirse sonuc degismez (alan payda)
    s2 = _sonuc(izg=([0.0, 1.0, 2.0], [0.0, 2.0], [-2 * z, 2 * z]),
                ort=np.array([3.0, 1.0]).reshape(2, 1, 1, 1, 1, 1))
    olcu2, tur2 = mt.olcu(s2, eksenel_sonsuz=True)
    w2 = mt.normalize(o, sg, olcu2, "mutlak", S, "kappa-fission", True, tur2)[0]
    kontrol("ag yuksekligi sonuca girmez", np.allclose(w, w2))


def test_2b_dar_dilim_mutlak_reddedilir():
    print("\n[Y1-D2] 2B'de elle dar z dilimi: mutlak reddedilir (kolon integrali degil)")
    from cekirdek import mesh_tally as mt
    s = _sonuc(izg=([0.0, 1.0], [0.0, 1.0], [-1.0, 1.0]))
    olcu, tur = mt.olcu(s, eksenel_sonsuz=True)
    kontrol("tur = dilim2b, olcu hacim", tur == "dilim2b" and np.allclose(olcu, 2.0))
    o, sg = mt.secim(s, "kappa-fission")
    try:
        mt.normalize(o, sg, olcu, "mutlak", 1.0, "kappa-fission", True, tur)
        hata = False
    except ValueError:
        hata = True
    kontrol("mutlak ValueError", hata)
    s3 = _sonuc(izg=([0.0, 1.0], [0.0, 1.0], [-1.0, 1.0]))
    kontrol("3B: olcu = hacim", mt.olcu(s3, eksenel_sonsuz=False)[1] == "hacim")


def test_3b_mutlak_guc_py_ile_tutarli():
    print("\n[Y1-D3] 3B mutlak: ayni P ile guc.py cubuk ortalamasi = ag ortalama W/cm3 x V")
    from cekirdek import mesh_tally as mt, guc
    # 4 esit cubuk hucresi (1.26 cm), 366 cm; kappa her hucrede ayni
    p, L, n = 17.6e6, 366.0, 4
    s = _sonuc(izg=([0, 1.26, 2.52], [0, 1.26, 2.52], [-L / 2, L / 2]),
               ort=np.full((2, 2, 1, 1, 1, 1), 2.5e7))
    olcu, tur = mt.olcu(s, eksenel_sonsuz=False)
    o, sg = mt.secim(s, "kappa-fission")
    H = float(o.sum())                       # ag butun fisil bolge
    w = mt.normalize(o, sg, olcu, "mutlak", mt.kaynak_hizi(p, H), "kappa-fission", True, tur)[0]
    faktor = {"cubuk_sayisi": n, "F_dH": 1.0, "F_q": None, "eksenel_dilim": 1}
    mg = guc.mutlak_guc(faktor, p, L)
    kontrol("guc.py cubuk ortalamasi = W/cm3 x hucre hacmi",
            math.isclose(mg["cubuk_ortalama_W"], float(w[0, 0, 0] * olcu[0, 0, 0]), rel_tol=1e-12),
            "-> %.6g vs %.6g" % (mg["cubuk_ortalama_W"], w[0, 0, 0] * olcu[0, 0, 0]))


# ---------------------------------------------------------------------------
# E2 -- genel isinma tally'si
# ---------------------------------------------------------------------------

def test_genel_isi_tally_kurucu_ve_betik():
    print("\n[Y1-D4] ozdegerde mesh tally varsa filtresiz genel isinma tally'si (kurucu = betik)")
    from cekirdek import kurucu, mesh_tally as mt
    spec = _spec("pwr_mesh_aki.json")
    model, _b = kurucu.kur(spec)
    g = [t for t in model.tallies if t.name == mt.GENEL_ISI_TALLY]
    kontrol("kurucu genel tally'yi ekledi", len(g) == 1 and not g[0].filters
            and list(g[0].scores) == list(mt.GENEL_ISI_SKORLARI))
    m2 = _betik_modeli(spec)
    g2 = [t for t in m2.tallies if t.name == mt.GENEL_ISI_TALLY]
    kontrol("betik de ekledi (ayni skorlar)", len(g2) == 1
            and list(g2[0].scores) == list(g[0].scores))
    meshsiz, _b = kurucu.kur(_spec("pwr_17x17.json"))
    kontrol("mesh'siz modelde eklenmez",
            not any(t.name == mt.GENEL_ISI_TALLY for t in meshsiz.tallies))
    sabit = _spec("pwr_mesh_aki.json")
    sabit["ayarlar"]["mod"] = "fixed source"
    kontrol("sabit kaynakta eklenmez", not mt.genel_isi_gerekli(sabit))


def test_isi_payi_secimi():
    print("\n[Y1-D5] H secimi: ayni skor > heating-local > kappa-fission; prompt aday degil")
    from cekirdek import mesh_tally as mt
    genel = {"kappa-fission": 10.0, "heating-local": 11.0}
    kontrol("isinma skoru kendi H'si", mt.isi_payi(genel, "kappa-fission") == (10.0, "kappa-fission"))
    kontrol("aki icin heating-local (yakalanma gamalari dahil)",
            mt.isi_payi(genel, "flux") == (11.0, "heating-local"))
    kontrol("fission-q-prompt H adayi degil", "fission-q-prompt" not in mt.H_SKORLARI)
    try:
        mt.isi_payi({}, "flux")
        hata = False
    except ValueError:
        hata = True
    kontrol("genel tally yok (eski kosu) -> ValueError", hata)


# ---------------------------------------------------------------------------
# H3 -- v2 geri uyum ve z sinirli geometri
# ---------------------------------------------------------------------------

def _betik_modeli(spec):
    from cekirdek import kod_uret
    eski = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        try:
            os.chdir(d)
            with open("model.py", "w", encoding="utf-8") as f:
                f.write(kod_uret.uret(spec, "model.py"))
            sm = importlib.util.spec_from_file_location("y1d_%d" % id(spec),
                                                        os.path.join(d, "model.py"))
            mod = importlib.util.module_from_spec(sm)
            sm.loader.exec_module(mod)
            return mod.model
        finally:
            os.chdir(eski)


def test_v2_otomatik_2b_proje_betik_farki():
    print("\n[Y1-D6] v2 otomatik 2B mesh projesi: eski betik z +/-1 cm, yeni +/-1e4 cm (belgeli)")
    from cekirdek import kod_uret, sema, sema_yapici, mesh_tally as mt
    spec = _spec("pwr_17x17.json")
    spec["tallyler"].append(sema_yapici.tally("v2_aki", ["flux"],
                                              [sema_yapici.filtre_mesh_otomatik([17, 17, 1])]))
    betik = kod_uret.uret(spec, "model.py")
    # v2.0.0 betigi (testler/veri/y1_v2_mesh_betik.txt'de saklanan satirlar)
    with open(os.path.join(KOK, "testler", "veri", "y1_v2_mesh_betik.txt"), encoding="utf-8") as f:
        eski = [s.strip() for s in f if s.strip() and not s.startswith("#")]
    kontrol("v2 betigi z = +/-1 cm yaziyordu", "tally_3_mesh_0.lower_left = [-10.71, -10.71, -1.0]"
            in eski)
    yeni = "tally_3_mesh_0.lower_left = [-10.71, -10.71, %r]" % -mt.Z_2B_YARI
    kontrol("yeni betik z = -Z_2B_YARI", yeni in betik, "-> %s" % yeni)
    kontrol("x/y ve bolmeler degismedi", "tally_3_mesh_0.dimension  = [17, 17, 1]" in betik
            and "tally_3_mesh_0.dimension  = [17, 17, 1]" in eski)
    _ = sema


def test_z_sinirli_geometride_kirpma():
    print("\n[Y1-D7] eksenel_sonsuz = geometri z'de sinirsiz (butun ornekler); z_aralik kirpar")
    import openmc
    from cekirdek import kurucu, mesh_tally as mt
    uyumsuz = []
    for ad in sorted(os.listdir(ORNEK)):
        if not ad.endswith(".json"):
            continue
        s = _spec(ad)
        model, _b = kurucu.kur(s)
        zbb = model.geometry.bounding_box
        sinirsiz = not (np.isfinite(zbb[0][2]) and np.isfinite(zbb[1][2]))
        if mt.eksenel_sonsuz(s) and not sinirsiz:
            uyumsuz.append(ad)
    kontrol("eksenel_sonsuz olan her ornekte geometri z'de sinirsiz", not uyumsuz,
            "-> %s" % uyumsuz)
    spec = _spec("pwr_17x17.json")
    t = mt.mesh_tanimi(spec, mt.filtre_duzenli([1, 1, 1]), (10.0, 10.0), z_aralik=(-50.0, 50.0))
    kontrol("z_aralik verilince ag ona kirpilir", (t["alt"][2], t["ust"][2]) == (-50.0, 50.0))
    u = openmc.Universe(cells=[openmc.Cell(region=-openmc.ZPlane(5.0) & +openmc.ZPlane(-3.0))])
    kontrol("geometri_z_araligi sonlu z'yi bulur", mt.geometri_z_araligi(u) == (-3.0, 5.0))
    u2 = openmc.Universe(cells=[openmc.Cell(region=-openmc.ZCylinder(r=1.0))])
    kontrol("sinirsiz z -> None", mt.geometri_z_araligi(u2) is None)


def test_bozuk_v2_filtre_kullaniciya_mesaj():
    print("\n[Y1-D8] bozuk v2 mesh filtresi: kurucu.kur acik ValueError (bolme metni)")
    from cekirdek import kurucu
    spec = _spec("pwr_17x17.json")
    spec["tallyler"][0]["filtreler"] = [{"tur": "mesh", "boyut": [0, 4.5, 1], "otomatik": True}]
    try:
        kurucu.kur(spec)
        metin = ""
    except ValueError as e:
        metin = str(e)
    kontrol("mesaj bolme sayisini soyler", "bölme" in metin, "-> %s" % metin)


# ---------------------------------------------------------------------------
# F8, F9 -- bagil ve grup toplami
# ---------------------------------------------------------------------------

def test_bagil_hacim_agirlikli():
    print("\n[Y1-D9] bagil kip: ortalama hacim agirlikli (sum o / sum V)")
    from cekirdek import mesh_tally as mt
    s = _sonuc(izg=([0.0, 1.0, 3.0], [0.0, 1.0], [0.0, 1.0]),
               ort=np.array([1.0, 4.0]).reshape(2, 1, 1, 1, 1, 1))
    olcu, tur = mt.olcu(s, False)
    o, sg = mt.secim(s, "kappa-fission")
    b = mt.normalize(o, sg, olcu, "bagil", None, "kappa-fission", True, tur)[0]
    # yogunluk 1 ve 2; hacim agirlikli ortalama (1+4)/(1+2) = 5/3 -> 0.6, 1.2
    kontrol("bagil 0.6 ve 1.2", np.allclose(b.ravel(), [0.6, 1.2]), "-> %s" % b.ravel())
    kontrol("grup toplami sigma'si 'iyimser' diye etiketli", "iyimser" in mt.GRUP_TOPLAMI_NOTU)


def test_dizi_salt_okunur():
    print("\n[Y1-D10] MeshSonuc dizileri salt okunur; eq=False")
    from cekirdek import mesh_tally as mt
    s = mt.salt_okunur(_sonuc(izg=([0, 1], [0, 1], [0, 1])))
    try:
        s.ortalama[0, 0, 0, 0, 0, 0] = 5.0
        yazildi = True
    except ValueError:
        yazildi = False
    kontrol("ortalama yazilamaz", not yazildi)


# ---------------------------------------------------------------------------
# VTK
# ---------------------------------------------------------------------------

def test_vtk_bagimsiz_beklenen_dosya():
    print("\n[Y1-D11] VTK 2x3x4 duzenli ag: noktalar ve hucre verisi elle yazilan beklenenle ayni")
    from cekirdek import mesh_tally as mt
    x, y, z = [0.0, 1.0, 2.0], [0.0, 1.0, 2.0, 3.0], [0.0, 1.0, 2.0, 3.0, 4.0]
    ort = np.zeros((2, 3, 4, 1, 1, 1))
    for i in range(2):
        for j in range(3):
            for k in range(4):
                ort[i, j, k, 0, 0, 0] = 100 * k + 10 * j + i + 1
    s = _sonuc(izg=(x, y, z), ort=ort)
    beklenen_nokta = [(xi, yj, zk) for zk in z for yj in y for xi in x]   # i en hizli
    beklenen_hucre = [100 * k + 10 * j + i + 1 for k in range(4) for j in range(3) for i in range(2)]
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, "k.vtk")
        mt.vtk_yaz(s, yol, yontem="kaynak", yerlesik=True)
        with open(yol, encoding="ascii") as f:
            sat = f.read().split("\n")
    i = sat.index("POINTS 60 double")
    noktalar = [tuple(float(v) for v in s_.split()) for s_ in sat[i + 1:i + 61]]
    kontrol("60 nokta, sira elle beklenenle ayni", noktalar == beklenen_nokta)
    j = sat.index("SCALARS kappa_fission_toplam double 1")
    hucre = [float(v) for v in sat[j + 2:j + 26]]
    kontrol("24 hucre degeri elle beklenen sirada", hucre == beklenen_hucre, "-> %s" % hucre[:5])
    kontrol("baslik satiri <= 256 karakter", len(sat[1]) <= 256)


def test_vtk_skorsuz_cok_nuklid_atomik():
    print("\n[Y1-D12] VTK: skorsuz bagil hata -1; cok nuklid alan adinda; atomik; yol once denetlenir")
    from cekirdek import mesh_tally as mt
    ort = np.ones((2, 1, 1, 1, 2, 1))
    ort[1, 0, 0, 0, :, 0] = 0.0
    s = _sonuc(izg=([0, 1, 2], [0, 1], [0, 1]), ort=ort, nuklidler=("U235", "U238"))
    with tempfile.TemporaryDirectory() as d:
        yol = os.path.join(d, "n.vtk")
        adlar = mt.vtk_yaz(s, yol, yontem="kaynak", yerlesik=True)
        kontrol("iki nuklidin alani", "kappa_fission_U235_toplam" in adlar
                and "kappa_fission_U238_toplam" in adlar, "-> %s" % adlar[:4])
        with open(yol, encoding="ascii") as f:
            metin = f.read()
        i = metin.index("SCALARS kappa_fission_U235_toplam_bagil_hata")
        degerler = metin[i:].split("\n")[2:4]
        kontrol("skorsuz hucre bagil hata -1", degerler == ["0.01", "-1"], "-> %s" % degerler)
        kontrol("gecici dosya kalmadi", sorted(os.listdir(d)) == ["n.vtk"])
        try:
            mt.vtk_yaz(s, os.path.join(d, "yok", "a.vtk"), yerlesik=True)
            hata = None
        except (OSError, ValueError) as e:
            hata = e
        kontrol("olmayan dizin: hesaptan once acik hata", isinstance(hata, (OSError, ValueError)))


def test_meshsiz_altin_betik():
    print("\n[Y1-D14] mesh'siz orneklerde betik Y1 oncesiyle (ana) birebir ayni")
    import re
    from cekirdek import kod_uret
    for ad in ("pwr_pinhucre", "pwr_17x17", "pwr_3b", "godiva_kriter"):
        metin = kod_uret.uret(_spec(ad + ".json"), "model.py")
        metin = re.sub(r"tarafından üretilmiştir \(\d{4}-\d{2}-\d{2}\)",
                       "tarafından üretilmiştir (TARIH)", metin)
        with open(os.path.join(KOK, "testler", "veri", "y1_altin_%s.py.txt" % ad),
                  encoding="utf-8") as f:
            altin = f.read()
        kontrol("%s: altin betikle ayni" % ad, metin == altin)


def test_yavas_genel_isi_ve_kapsama(gecici):
    print("\n[Y1-D13] YAVAS: genel H; silindirik ag koseleri kacirir ama S genel H'den dogru")
    from cekirdek import kurucu, mesh_tally as mt
    spec = _spec("pwr_mesh_aki.json")
    spec["ayarlar"].update(parcacik=3000, cevrim=25, pasif=8)
    spec["tallyler"][1]["skorlar"] = ["flux", "kappa-fission"]
    eski = os.getcwd()
    try:
        os.chdir(gecici)
        model, _b = kurucu.kur(spec)
        sp = model.run(threads=ISLEM_PARCACIGI, output=False)
    finally:
        os.chdir(eski)
    genel = mt.genel_isi_oku(sp)
    kontrol("genel tally okundu", set(genel) == set(mt.GENEL_ISI_SKORLARI), "-> %s" % genel)
    sonuclar = {s.ad: s for s in mt.oku(sp)[0]}
    duz, sil = sonuclar["mesh_aki_guc"], sonuclar["silindirik_aki"]
    h_duz = float(mt.secim(duz, "kappa-fission")[0].sum())
    h_sil = float(mt.secim(sil, "kappa-fission")[0].sum())
    oran = h_sil / genel["kappa-fission"]
    kontrol("duzenli ag butun isinmayi kapsar (= genel)",
            math.isclose(h_duz, genel["kappa-fission"], rel_tol=1e-9))
    kontrol("silindirik ag ~%78.5 (pi/4) kapsar", 0.70 < oran < 0.86, "-> %.3f" % oran)


HIZLI = [test_2b_mutlak_alan_ve_cizgisel_guc, test_2b_dar_dilim_mutlak_reddedilir,
         test_3b_mutlak_guc_py_ile_tutarli, test_genel_isi_tally_kurucu_ve_betik,
         test_isi_payi_secimi, test_v2_otomatik_2b_proje_betik_farki,
         test_z_sinirli_geometride_kirpma, test_bozuk_v2_filtre_kullaniciya_mesaj,
         test_bagil_hacim_agirlikli, test_dizi_salt_okunur, test_vtk_bagimsiz_beklenen_dosya,
         test_vtk_skorsuz_cok_nuklid_atomik, test_meshsiz_altin_betik]
YAVAS = [test_yavas_genel_isi_ve_kapsama]
