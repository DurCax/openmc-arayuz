# -*- coding: utf-8 -*-
"""
 test_y1_mesh_sonuc.py  --  v3 Y1: mesh tally SONUCU (cekirdek/mesh_tally/sonuc.py, vtk.py)

 Hacim (OpenMC ile ayni), grup secimi/toplami, normalizasyon (kaynak basina,
 hacim basina, ortalamaya bagil, mutlak), bagil hata ve yuksek hata isareti,
 2B dilim koordinatlari, VTK (legacy) dosyasi: nokta sirasi OpenMC'nin
 _create_vtk_structured_grid sirasiyla ayni. YAVAS: ornek kosu (pwr_mesh_aki).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import math
import os
import warnings

import numpy as np

from testler.ortak_test import kontrol, ORNEK, ISLEM_PARCACIGI


def _openmc_mesh(tur):
    import openmc
    if tur == "duzenli":
        m = openmc.RegularMesh()
        m.dimension = [3, 2, 2]
        m.lower_left = [-3.0, -1.0, 0.0]
        m.upper_right = [3.0, 1.0, 4.0]
        return m
    if tur == "silindirik":
        return openmc.CylindricalMesh(r_grid=np.linspace(0, 4, 3), z_grid=np.linspace(-1, 1, 3),
                                      phi_grid=np.linspace(0, 2 * math.pi, 5), origin=[1, 2, 0])
    return openmc.SphericalMesh(r_grid=np.linspace(0, 5, 3), theta_grid=np.linspace(0, math.pi, 3),
                                phi_grid=np.linspace(0, 2 * math.pi, 4), origin=[0, 0, 1])


def _sentetik(tur="duzenli", ne=2, skorlar=("flux", "kappa-fission")):
    """Bilinen degerli MeshSonuc: deger = 1 + i + 10 j + 100 k (+ grup), sigma %5."""
    from cekirdek import mesh_tally as mt
    m = _openmc_mesh(tur)
    izg = mt.mesh_izgaralari(m)
    boyut = tuple(len(g) - 1 for g in izg)
    i, j, k = np.meshgrid(*[np.arange(n) for n in boyut], indexing="ij")
    taban = 1.0 + i + 10.0 * j + 100.0 * k
    ort = np.stack([np.stack([taban * (g + 1) * (s + 1) for s in range(len(skorlar))], -1)
                    for g in range(ne)], axis=3)[:, :, :, :, None, :]
    return mt.MeshSonuc(ad="t", tur=tur, izgaralar=izg,
                        merkez=tuple(float(x) for x in getattr(m, "origin", (0, 0, 0))),
                        skorlar=tuple(skorlar), nuklidler=("total",),
                        enerji=(0.0, 0.625, 2.0e7) if ne == 2 else None,
                        ortalama=ort, sapma=0.05 * ort, ozdeger=True)


def test_hacimler_openmc_ile_ayni():
    print("\n[Y1-S1] hacimler ve izgaralar OpenMC mesh.volumes ile ayni (3 tur)")
    from cekirdek import mesh_tally as mt
    for tur in ("duzenli", "silindirik", "kuresel"):
        m = _openmc_mesh(tur)
        h = mt.hacimler(tur, mt.mesh_izgaralari(m))
        kontrol("%s hacim" % tur, np.allclose(h, m.volumes), "-> %s" % h.ravel()[:3])
        kontrol("%s tur_bul" % tur, mt.mesh_tur_bul(m) == tur)


def test_secim_grup_toplami():
    print("\n[Y1-S2] skor/grup secimi; tum gruplar toplaminda sigma karelerin toplami")
    from cekirdek import mesh_tally as mt
    s = _sentetik()
    o0, s0 = mt.secim(s, "flux", grup=0)
    o1, _s1 = mt.secim(s, "flux", grup=1)
    ot, st = mt.secim(s, "flux", grup=None)
    kontrol("grup 0 = taban", o0[1, 1, 1] == 1 + 1 + 10 + 100)
    kontrol("toplam = g0 + g1", np.allclose(ot, o0 + o1))
    kontrol("sigma toplami karelerden", np.allclose(st, np.sqrt(s0 ** 2 + (0.05 * o1) ** 2)))
    try:
        mt.secim(s, "absorption")
        hata = False
    except ValueError:
        hata = True
    kontrol("tally'de olmayan skor ValueError", hata)


def test_normalizasyon():
    print("\n[Y1-S3] normalizasyon: kaynak, hacim, bagil (ortalama 1), mutlak (W/cm3)")
    from cekirdek import mesh_tally as mt
    s = _sentetik()
    o, sg = mt.secim(s, "kappa-fission", grup=None)
    h = mt.hacimler(s.tur, s.izgaralar)
    ok, sk, bk = mt.normalize(o, sg, h, "kaynak", skor="kappa-fission")
    kontrol("kaynak: degismez, yeni dizi", np.array_equal(ok, o) and ok is not o)
    oh, sh, _b = mt.normalize(o, sg, h, "hacim", skor="kappa-fission")
    kontrol("hacim: deger / V", np.allclose(oh, o / h) and np.allclose(sh, sg / h))
    ob, sb, bb = mt.normalize(o, sg, h, "bagil", skor="kappa-fission")
    kontrol("bagil: ortalama 1", math.isclose(float(ob[o > 0].mean()), 1.0))
    kontrol("bagil: bagil hata korunur", np.allclose(sb / ob, sg / o))
    hiz = mt.kaynak_hizi(1.0e6, 2.0e8)
    kontrol("kaynak hizi = P / (H e)", math.isclose(hiz, 1.0e6 / (2.0e8 * mt.EV_JOULE)))
    om, _sm, bm = mt.normalize(o, sg, h, "mutlak", kaynak_hizi=hiz, skor="kappa-fission")
    kontrol("mutlak isi: W/cm3", np.allclose(om, o * hiz * mt.EV_JOULE / h) and "W" in bm)
    of, _sf, bf = mt.normalize(o, sg, h, "mutlak", kaynak_hizi=hiz, skor="flux")
    kontrol("mutlak aki: n/cm2/s (eV->J yok)", np.allclose(of, o * hiz / h) and "cm²" in bf)
    for kotu in (dict(yontem="mutlak"), dict(yontem="yok")):
        try:
            mt.normalize(o, sg, h, kaynak_hizi=None, skor="flux", **kotu)
            hata = False
        except ValueError:
            hata = True
        kontrol("%s gecersiz -> ValueError" % kotu["yontem"], hata)
    try:
        mt.kaynak_hizi(1.0e6, 0.0)
        hata = False
    except ValueError:
        hata = True
    kontrol("sifir isi -> ValueError", hata)


def test_isi_toplami():
    print("\n[Y1-S4] isi_toplami: tally'deki isinma skoru agin ve gruplarin toplami")
    from cekirdek import mesh_tally as mt
    s = _sentetik()
    o, _ = mt.secim(s, "kappa-fission", grup=None)
    kontrol("toplam", math.isclose(mt.isi_toplami(s), float(o.sum())))
    kontrol("isinma skoru yoksa None", mt.isi_toplami(_sentetik(skorlar=("flux",))) is None)


def test_bagil_hata_ve_isaret():
    print("\n[Y1-S5] bagil hata; esik ustu ve skorsuz hucreler isaretli")
    from cekirdek import mesh_tally as mt
    o = np.array([[[1.0, 2.0, 0.0, 4.0]]])
    sg = np.array([[[0.01, 0.5, 0.0, 0.2]]])
    b = mt.bagil_hata(o, sg)
    kontrol("bagil = sigma / deger", np.allclose(b[0, 0, [0, 1, 3]], [0.01, 0.25, 0.05]))
    kontrol("skorsuz hucre NaN", math.isnan(b[0, 0, 2]))
    m = mt.yuksek_hata_maskesi(o, sg, mt.BAGIL_HATA_ESIGI)
    kontrol("esik %10: yalniz 0.25 ve skorsuz isaretli", m.ravel().tolist() == [False, True, True, False])
    oz = mt.ozet(o, sg, mt.BAGIL_HATA_ESIGI)
    kontrol("ozet", oz["hucre"] == 4 and oz["skorsuz"] == 1 and oz["yuksek"] == 1
            and math.isclose(oz["en_buyuk_bagil"], 0.25), "-> %s" % oz)
    kontrol("esik kaynakli (MCNP)", "MCNP" in mt.BAGIL_HATA_KAYNAGI)


def test_dilim_koordinatlari():
    print("\n[Y1-S6] 2B dilim: duzenli xy, silindirik (r, phi) -> kartezyen, kuresel meridyen")
    from cekirdek import mesh_tally as mt
    s = _sentetik()
    o, _ = mt.secim(s, "flux", grup=0)
    d = mt.dilim(s, o, eksen=2, indeks=1)
    kontrol("duzenli z dilimi: deger (nx, ny)", d.deger.shape == (3, 2)
            and np.array_equal(d.deger, o[:, :, 1]))
    kontrol("duzenli kose koordinatlari", d.x.shape == (4, 3) and d.x[0, 0] == -3.0
            and d.y[0, -1] == 1.0)
    c = _sentetik("silindirik")
    oc, _ = mt.secim(c, "flux", grup=0)
    dc = mt.dilim(c, oc, eksen=2, indeks=0)
    kontrol("silindirik z dilimi: (nr, nphi)", dc.deger.shape == (2, 4))
    kontrol("silindirik dis kose (r=4, phi=0) merkez kaydirmali",
            math.isclose(dc.x[-1, 0], 5.0) and math.isclose(dc.y[-1, 0], 2.0))
    drz = mt.dilim(c, oc, eksen=1, indeks=0)
    kontrol("silindirik phi dilimi: r-z", drz.deger.shape == (2, 2) and drz.x[-1, 0] == 4.0)
    k = _sentetik("kuresel")
    ok_, _ = mt.secim(k, "flux", grup=0)
    dk = mt.dilim(k, ok_, eksen=2, indeks=0)
    kontrol("kuresel phi dilimi (r, theta): kutup noktasi z = r + oz",
            dk.deger.shape == (2, 2) and math.isclose(dk.y[-1, 0], 6.0))
    try:
        mt.dilim(s, o, eksen=2, indeks=5)
        hata = False
    except ValueError:
        hata = True
    kontrol("aralik disi dilim ValueError", hata)


def _vtk_oku(yol):
    with open(yol, encoding="ascii") as f:
        satirlar = f.read().split("\n")
    i = next(n for n, s in enumerate(satirlar) if s.startswith("POINTS"))
    np_ = int(satirlar[i].split()[1])
    noktalar = np.array([[float(x) for x in s.split()] for s in satirlar[i + 1:i + 1 + np_]])
    alanlar, n = {}, i + 1 + np_
    while n < len(satirlar):
        if satirlar[n].startswith("SCALARS"):
            ad = satirlar[n].split()[1]
            nc = int(next(s for s in satirlar if s.startswith("CELL_DATA")).split()[1])
            alanlar[ad] = np.array([float(x) for x in satirlar[n + 2:n + 2 + nc]])
            n += 2 + nc
        else:
            n += 1
    return satirlar, noktalar, alanlar


def test_vtk_yazici(gecici=None):
    print("\n[Y1-S7] VTK (legacy STRUCTURED_GRID): OpenMC ile ayni nokta ve hucre sirasi")
    import tempfile
    from cekirdek import mesh_tally as mt
    with tempfile.TemporaryDirectory() as d:
        for tur in ("duzenli", "silindirik", "kuresel"):
            s = _sentetik(tur)
            yol = os.path.join(d, "%s.vtk" % tur)
            adlar = mt.vtk_yaz(s, yol, yontem="kaynak", yerlesik=True)
            satirlar, noktalar, alanlar = _vtk_oku(yol)
            m = _openmc_mesh(tur)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)   # 0.14 kartezyen notu
                beklenen = np.swapaxes(m.vertices, 0, 2).reshape(-1, 3)
            kontrol("%s: noktalar OpenMC sirasinda" % tur,
                    noktalar.shape == beklenen.shape and np.allclose(noktalar, beklenen, atol=1e-9))
            kontrol("%s: DIMENSIONS" % tur, ("DIMENSIONS %d %d %d" % tuple(
                n + 1 for n in m.dimension)) in satirlar)
            o, _ = mt.secim(s, "flux", grup=0)
            kontrol("%s: hucre verisi i en hizli (T.ravel)" % tur,
                    np.allclose(alanlar["flux_g1"], o.T.ravel()))
            kontrol("%s: sigma ve bagil hata alanlari" % tur,
                    "flux_g1_sigma" in alanlar and "flux_toplam_bagil_hata" in alanlar
                    and set(adlar) == set(alanlar), "-> %s" % sorted(alanlar)[:4])


def test_tally_metni_mesh_ve_enerji():
    print("\n[Y1-S9] kosucu.tally_metni: mesh + enerji filtreli tally (MultiIndex sutun) cokmez")
    import pandas as pd
    from cekirdek import kosucu
    # OpenMC'nin mesh filtreli DataFrame'i: sutunlar MultiIndex ("mesh 1", "x") ...
    sutun = pd.MultiIndex.from_tuples(
        [("mesh 1", "x"), ("mesh 1", "y"), ("mesh 1", "z"), ("energy low [eV]", ""),
         ("energy high [eV]", ""), ("nuclide", ""), ("score", ""), ("mean", ""),
         ("std. dev.", "")])
    df = pd.DataFrame([[1, 1, 1, 0.0, 0.625, "total", "flux", 2.0, 0.1],
                       [1, 1, 1, 0.625, 2e7, "total", "flux", 3.0, 0.1]], columns=sutun)
    try:
        metin = kosucu.tally_metni("mesh_aki", df)
        hata = None
    except ValueError as e:
        metin, hata = "", e
    kontrol("metin uretildi (tam tablo)", hata is None and "mesh_aki" in metin
            and "flux" in metin, "-> %s" % hata)


def test_yavas_ornek_kosu_mesh_haritasi(gecici):
    print("\n[Y1-S8] YAVAS: pwr_mesh_aki kosusu -> mesh sonuclari, simetri, VTK")
    import openmc
    from cekirdek import kurucu, sema, mesh_tally as mt
    spec = sema.yukle(os.path.join(ORNEK, "pwr_mesh_aki.json"))
    spec["ayarlar"].update(parcacik=4000, cevrim=30, pasif=10)
    eski = os.getcwd()
    try:
        os.chdir(gecici)
        model, _n = kurucu.kur(spec)
        sp = model.run(threads=ISLEM_PARCACIGI, output=False)
    finally:
        os.chdir(eski)
    sonuclar, atlanan = mt.oku(sp)
    adlar = {s.ad: s for s in sonuclar}
    kontrol("iki mesh tally okundu, atlanan yok",
            set(adlar) == {"mesh_aki_guc", "silindirik_aki"} and not atlanan, "-> %s %s"
            % (sorted(adlar), atlanan))
    s = adlar["mesh_aki_guc"]
    kontrol("duzenli 17x17x1, 2 grup", s.tur == "duzenli" and s.ortalama.shape[:4] == (17, 17, 1, 2))
    o, sg = mt.secim(s, "kappa-fission", grup=None)
    fark = np.abs(o[:, :, 0] - o[:, :, 0].T)
    birlesik = np.sqrt(sg[:, :, 0] ** 2 + sg[:, :, 0].T ** 2)
    oran = float(np.mean(fark <= 4.0 * birlesik + 1e-30))
    kontrol("kosegen simetrisi: hucrelerin >= %95'i 4 sigma icinde", oran >= 0.95, "-> %.3f" % oran)
    c = adlar["silindirik_aki"]
    kontrol("silindirik (8, 12, 1)", c.tur == "silindirik" and c.ortalama.shape[:3] == (8, 12, 1))
    oc, _ = mt.secim(c, "flux")
    kontrol("silindirikte dis halka koseleri kesiyor ama skor var", float(oc[-1].min()) > 0.0)
    yol = os.path.join(gecici, "harita.vtk")
    adlar_vtk = mt.vtk_yaz(s, yol, yontem="bagil")
    kontrol("VTK yazildi", os.path.getsize(yol) > 1000 and "kappa_fission_toplam" in adlar_vtk)
    # 2B: cizgisel guc q' [W/cm], payda hucre ALANI, H genel isinma tally'sinden
    q = 17.6e6 / 366.0
    genel = mt.genel_isi_oku(sp)
    isi, h_skoru = mt.isi_payi(genel, "kappa-fission")
    kontrol("duzenli ag butun isinmayi kapsar: ag ici H = genel H",
            math.isclose(mt.isi_toplami(s), isi, rel_tol=1e-9) and h_skoru == "kappa-fission")
    alan, tur = mt.olcu(s, eksenel_sonsuz=True)
    om, _sm, birim = mt.normalize(o, sg, alan, "mutlak", mt.kaynak_hizi(q, isi),
                                  "kappa-fission", True, tur)
    toplam = float((om * alan).sum())
    kontrol("mutlak 2B: alan x yogunluk toplami = cizgisel guc (W/cm)",
            tur == "alan" and math.isclose(toplam, q, rel_tol=1e-9),
            "-> %.4g %s" % (toplam, birim))


HIZLI = [test_hacimler_openmc_ile_ayni, test_secim_grup_toplami, test_normalizasyon,
         test_isi_toplami, test_bagil_hata_ve_isaret, test_dilim_koordinatlari,
         test_vtk_yazici, test_tally_metni_mesh_ve_enerji]
YAVAS = [test_yavas_ornek_kosu_mesh_haritasi]
