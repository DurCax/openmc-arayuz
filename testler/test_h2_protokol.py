# -*- coding: utf-8 -*-
"""
 test_h2_protokol.py  --  v3 H2 onizleme motoru: cerceve protokolu, kesit
                          olculeri, istek dogrulamasi ve id haritasi boyamasi
                          (openmc.lib ve alt surec GEREKMEZ)
"""

import numpy as np

from testler.ortak_test import kontrol


def test_cerceve_gidis_donus():
    print("\n[H2P-1] cerceve: baslik + diziler bayt duzeyinde geri okunur")
    from cekirdek import cizim_sureci as cs
    # Arrange
    geom = np.arange(2 * 3 * 3, dtype=np.int32).reshape(2, 3, 3) - 3
    veri = cs.cerceve({"tur": "kesit", "no": 7, "ad": "çakışma"}, {"geom": geom})
    cozucu = cs.CerceveCozucu()
    # Act: parca parca beslenir (boru tek seferde gelmeyebilir)
    cikan = []
    for i in range(0, len(veri), 5):
        cikan += cozucu.besle(veri[i:i + 5])
    # Assert
    kontrol("tek cerceve cozuldu", len(cikan) == 1, "-> %d" % len(cikan))
    c = cikan[0]
    kontrol("baslik ayni (UTF-8 dahil)", c.baslik == {"tur": "kesit", "no": 7, "ad": "çakışma"})
    kontrol("dizi ayni (dtype, sekil, deger)",
            c.diziler["geom"].dtype == np.int32 and np.array_equal(c.diziler["geom"], geom))
    kontrol("ic alan (diziler) baslikta kalmaz", "_diziler" not in c.baslik)


def test_cerceve_ardisik_ve_bos():
    print("\n[H2P-2] cerceve: ardisik cerceveler tek beslemede, dizisiz cerceve")
    from cekirdek import cizim_sureci as cs
    veri = cs.cerceve({"tur": "a"}) + cs.cerceve({"tur": "b"}, {"x": np.zeros(4, np.uint8)})
    cikan = cs.CerceveCozucu().besle(veri)
    kontrol("iki cerceve sirasiyla", [c.baslik["tur"] for c in cikan] == ["a", "b"])
    kontrol("dizisiz cercevede diziler bos", cikan[0].diziler == {})


def test_cerceve_bozuk_girdi_reddedilir():
    print("\n[H2P-3] cerceve: bozuk sihir / asiri boyut / izinsiz dtype ProtokolHatasi")
    from cekirdek import cizim_sureci as cs
    hatalar = []
    for ad, veri in (("sihir", b"XXXX" + b"\0" * 12),
                     ("asiri baslik", cs._SIHIR + (cs.BASLIK_SINIRI + 1).to_bytes(4, "big")
                      + b"\0" * 8)):
        try:
            cs.CerceveCozucu().besle(veri)
        except cs.ProtokolHatasi:
            hatalar.append(ad)
    kontrol("bozuk sihir ve asiri baslik reddedildi", hatalar == ["sihir", "asiri baslik"],
            "-> %s" % hatalar)
    try:
        cs.cerceve({"tur": "a"}, {"x": np.zeros(2, dtype=object)})
        izinsiz = False
    except cs.ProtokolHatasi:
        izinsiz = True
    kontrol("izinsiz dtype (object) gonderilmez", izinsiz)
    # baslik dizi tanimi gercek boyutla uyusmuyorsa
    import json
    baslik = json.dumps({"tur": "a", "_diziler": [
        {"ad": "x", "dtype": "int32", "sekil": [-1]}]}).encode()
    veri = cs._SIHIR + len(baslik).to_bytes(4, "big") + (0).to_bytes(8, "big") + baslik
    try:
        cs.CerceveCozucu().besle(veri)
        sekil = False
    except cs.ProtokolHatasi:
        sekil = True
    kontrol("negatif sekilli dizi tanimi reddedildi", sekil)


def test_kesit_genisligi():
    print("\n[H2P-4] kesit olculeri: xy sinir kutusu, xz/yz model yuksekligi")
    from cekirdek import cizim_sureci as cs
    kontrol("xy = (gx, gy)", cs.kesit_genisligi("xy", (10.0, 8.0), 50.0) == (10.0, 8.0))
    kontrol("xz = (gx, h)", cs.kesit_genisligi("xz", (10.0, 8.0), 50.0) == (10.0, 50.0))
    kontrol("yz = (gy, h)", cs.kesit_genisligi("yz", (10.0, 8.0), 50.0) == (8.0, 50.0))
    kontrol("2B (h yok): dikey = en buyuk yatay olcu",
            cs.kesit_genisligi("xz", (10.0, 8.0), None) == (10.0, 10.0))
    try:
        cs.kesit_genisligi("zz", (1.0, 1.0), None)
        gecersiz = False
    except cs.ProtokolHatasi:
        gecersiz = True
    kontrol("bilinmeyen eksen reddedilir", gecersiz)


def test_istek_dogrulamasi():
    print("\n[H2P-5] istek dogrulamasi: tur, kesitler, piksel sinirlari")
    from cekirdek import cizim_sureci as cs
    iyi = {"tur": "ciz", "no": 1, "spec": {"ad": "x"},
           "kesitler": [{"eksen": "xy", "piksel": 800}], "cakisma": False}
    kontrol("gecerli istek kabul", cs.istegi_dogrula(iyi) == iyi)
    kotu = [
        {"tur": "sil", "no": 1},
        {"tur": "ciz", "no": "1", "spec": {}, "kesitler": []},
        {"tur": "ciz", "no": 1, "spec": [], "kesitler": []},
        {"tur": "ciz", "no": 1, "spec": {}, "kesitler": [{"eksen": "xy", "piksel": 5}]},
        {"tur": "ciz", "no": 1, "spec": {}, "kesitler": [{"eksen": "xy", "piksel": 10 ** 6}]},
        {"tur": "ciz", "no": 1, "spec": {}, "kesitler": [{"eksen": "ab", "piksel": 800}]},
        {"tur": "ciz", "no": 1, "spec": {}, "kesitler": [{"eksen": "xy", "piksel": 800}] * 4},
    ]
    reddedilen = 0
    for istek in kotu:
        try:
            cs.istegi_dogrula(istek)
        except cs.ProtokolHatasi:
            reddedilen += 1
    kontrol("gecersiz isteklerin hepsi reddedildi", reddedilen == len(kotu),
            "-> %d / %d" % (reddedilen, len(kotu)))
    kontrol("kontrol istegi kesitsiz gecerli",
            cs.istegi_dogrula({"tur": "kontrol", "no": 2, "spec": {}})["tur"] == "kontrol")
    kontrol("cik istegi gecerli", cs.istegi_dogrula({"tur": "cik", "no": 0})["tur"] == "cik")


def _geom(malzeme, hucre=None):
    m = np.asarray(malzeme, dtype=np.int32)
    h = m.copy() if hucre is None else np.asarray(hucre, dtype=np.int32)
    return np.stack([h, np.zeros_like(m), m], axis=-1)


def test_malzeme_boyama():
    print("\n[H2P-6] boyama: malzeme renkleri, bosluk beyaz, tanimsiz saydam, cakisma rengi")
    from arayuz import onizleme_boyama as ob
    # Arrange: 1 ve 2 malzeme, -1 bosluk, -2 tanimsiz (hucre yok), -3 cakisma
    geom = _geom([[1, 2], [-1, -3]], hucre=[[5, 6], [7, -3]])
    geom2 = _geom([[-2]], hucre=[[-2]])
    renkler = {1: (255, 0, 0), 2: (0, 0, 255)}
    # Act
    img = ob.malzeme_goruntusu(geom, renkler, cakisma_rengi=(0.0, 1.0, 0.0)) / 255.0
    img2 = ob.malzeme_goruntusu(geom2, renkler, cakisma_rengi=(0.0, 1.0, 0.0)) / 255.0
    # Assert
    kontrol("RGBA sekli", img.shape == (2, 2, 4))
    kontrol("uint8 (bellek: float64'in sekizde biri)",
            ob.malzeme_goruntusu(geom, renkler, (0, 1, 0)).dtype == np.uint8)
    kontrol("malzeme 1 kirmizi, 2 mavi", np.allclose(img[0, 0], (1, 0, 0, 1))
            and np.allclose(img[0, 1], (0, 0, 1, 1)))
    kontrol("bosluk (-1) beyaz (Model.plot ile ayni)", np.allclose(img[1, 0], (1, 1, 1, 1)))
    kontrol("cakisma (-3) verilen renkte", np.allclose(img[1, 1], (0, 1, 0, 1)))
    kontrol("tanimsiz bolge (-2) saydam", img2[0, 0, 3] == 0.0)


def test_hucre_boyama_model_plot_ile_ayni():
    print("\n[H2P-7] boyama: hucre renkleri openmc'nin varsayilan rastgele renkleriyle ayni")
    from arayuz import onizleme_boyama as ob
    geom = _geom([[1, 1, 1]], hucre=[[12, 3, 40]])
    img = ob.hucre_goruntusu(geom) / 255.0
    rng = np.random.RandomState(1)            # openmc.plots._id_map_to_rgb sirasi
    beklenen = {k: rng.randint(0, 256, (3,)) / 255.0 for k in (3, 12, 40)}
    kontrol("siralanmis kimlik sirasinda RandomState(1) renkleri",
            all(np.allclose(img[0, i, :3], beklenen[k]) for i, k in enumerate((12, 3, 40))))
    vurgu = ob.hucre_goruntusu(geom, renkler={3: (0, 255, 0)}, varsayilan=(0, 0, 0)) / 255.0
    kontrol("verilen renk sozlugu + varsayilan renk", np.allclose(vurgu[0, 1, :3], (0, 1, 0))
            and np.allclose(vurgu[0, 0, :3], (0, 0, 0)))


def test_gosterge_ogeleri():
    print("\n[H2P-8] gosterge: modeldeki malzemeler + varsa cakisma ogesi")
    from arayuz import onizleme_boyama as ob
    gosterge = [["yakit", [255, 0, 0]], ["su", [0, 0, 255]]]
    temiz = ob.gosterge_ogeleri(gosterge, cakisma_var=False, cakisma_rengi=(0, 1, 0))
    kirli = ob.gosterge_ogeleri(gosterge, cakisma_var=True, cakisma_rengi=(0, 1, 0))
    kontrol("malzeme ogeleri sirali, 0-1 olcekli",
            [a for a, _r in temiz] == ["yakit", "su"] and np.allclose(temiz[0][1], (1, 0, 0)))
    kontrol("cakisma varsa son oge 'Çakışma'", len(kirli) == 3 and kirli[-1][0] == "Çakışma")


HIZLI = [test_cerceve_gidis_donus, test_cerceve_ardisik_ve_bos,
         test_cerceve_bozuk_girdi_reddedilir, test_kesit_genisligi, test_istek_dogrulamasi,
         test_malzeme_boyama, test_hucre_boyama_model_plot_ile_ayni, test_gosterge_ogeleri]
YAVAS = []
