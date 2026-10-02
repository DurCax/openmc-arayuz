# -*- coding: utf-8 -*-
"""
 test_y2_gorunum.py  --  v3 Y2 goruntuleyici saf mantigi (Qt'siz): kesit gorunumu
                         (yakinlastir/kaydir, piksel <-> koordinat), renk kipleri
                         (malzeme/hucre/cakisma), mesh tally bindirmesinin konum
                         dogrulugu ve sigma maskesi, kaynak izdusumu, 3B kamera
"""

import math

import numpy as np

from testler.ortak_test import kontrol


def _geom(hucre, malzeme):
    hucre, malzeme = np.asarray(hucre, np.int32), np.asarray(malzeme, np.int32)
    return np.stack([hucre, np.zeros_like(hucre), malzeme], axis=-1)


# ----------------------------------------------------------------------------
# gorunum
# ----------------------------------------------------------------------------

def test_varsayilan_gorunum_ve_istek():
    print("\n[Y2G-1] gorunum: varsayilan merkez orijin, genislik sinir kutusu; isci istegi")
    from arayuz.goruntuleyici import gorunum as gr
    # Act
    xy = gr.varsayilan((20.0, 10.0), 100.0, "xy", 400)
    xz = gr.varsayilan((20.0, 10.0), 100.0, "xz", 400)
    iki_b = gr.varsayilan((20.0, 10.0), None, "yz", 400)
    # Assert
    kontrol("xy: genislik (20, 10), dikey piksel 200 (kare piksel)",
            xy.genislik == (20.0, 10.0) and xy.piksel_dikey == 200)
    kontrol("xz: dikey = yukseklik", xz.genislik == (20.0, 100.0))
    kontrol("2B yz: dikey = en buyuk yatay olcu", iki_b.genislik == (10.0, 20.0))
    oge = xy.istek_ogesi()
    kontrol("istek ogesi isci dogrulamasindan gecer", oge == {
        "eksen": "xy", "piksel": 400, "piksel_dikey": 200, "merkez": [0.0, 0.0, 0.0],
        "genislik": [20.0, 10.0]})
    from cekirdek import cizim_sureci as cs
    kontrol("cs.istegi_dogrula kabul eder", cs.istegi_dogrula(
        {"tur": "ciz", "no": 1, "spec": {}, "kesitler": [oge]}) is not None)


def test_yakinlastir_kaydir_degismez():
    print("\n[Y2G-2] gorunum: yakinlastirma odak noktasini sabit tutar, kaydirma; girdi degismez")
    from arayuz.goruntuleyici import gorunum as gr
    g = gr.Gorunum("xz", (1.0, 2.0, 3.0), (10.0, 20.0), 100)
    # Act
    yakin = gr.yakinlastir(g, 2.0, odak=(4.0, 3.0))
    kayik = gr.kaydir(g, 1.5, -2.0)
    konum = gr.konum_ayarla(g, 7.0)
    # Assert: odagin goreli konumu ayni kalir
    u0, u1, v0, v1 = g.kapsam
    y0, y1, w0, w1 = yakin.kapsam
    kontrol("genislik yariya iner", yakin.genislik == (5.0, 10.0))
    kontrol("odak noktasinin goreli yeri ayni", math.isclose((4.0 - u0) / (u1 - u0),
                                                            (4.0 - y0) / (y1 - y0))
            and math.isclose((3.0 - v0) / (v1 - v0), (3.0 - w0) / (w1 - w0)))
    kontrol("xz kaydirma: x ve z degisir, y (konum) sabit", kayik.merkez == (2.5, 2.0, 1.0))
    kontrol("konum ayari normal ekseni (y) degistirir", konum.merkez == (1.0, 7.0, 3.0)
            and konum.konum == 7.0)
    kontrol("girdi gorunum degismedi", g.merkez == (1.0, 2.0, 3.0) and g.genislik == (10.0, 20.0))
    kontrol("cok kucuk genislik sinirlanir", gr.yakinlastir(g, 1e9).genislik[0] >= gr.EN_KUCUK_GENISLIK)


def test_piksel_koordinat_eslemesi():
    print("\n[Y2G-3] gorunum: piksel merkezi <-> koordinat (OpenMC: satir 0 ustte)")
    from arayuz.goruntuleyici import gorunum as gr
    g = gr.Gorunum("xy", (0.0, 0.0, 5.0), (10.0, 10.0), 20)       # 0.5 cm piksel
    # Act / Assert
    kontrol("sol ust piksel merkezi (-4.75, 4.75)", gr.piksel_merkezi(g, 0, 0) == (-4.75, 4.75))
    kontrol("(-4.75, 4.75) -> piksel (0, 0)", gr.piksel_indeksi(g, -4.75, 4.75) == (0, 0))
    kontrol("(0.2, -0.2) -> piksel (10, 10)", gr.piksel_indeksi(g, 0.2, -0.2) == (10, 10))
    kontrol("dikey piksel isci alt sinirina kirpilir", gr.Gorunum(
        "xy", (0, 0, 0), (100.0, 1.0), 100).piksel_dikey == 16)
    kontrol("pencere disi -> None", gr.piksel_indeksi(g, 6.0, 0.0) is None)
    kontrol("duzlem noktasi 3B (z = konum)", gr.nokta(g, 1.0, 2.0) == (1.0, 2.0, 5.0))
    yz = gr.Gorunum("yz", (3.0, 0.0, 0.0), (4.0, 4.0), 4)
    kontrol("yz duzlemi: x = konum", gr.nokta(yz, 1.0, 2.0) == (3.0, 1.0, 2.0))


def test_nokta_bilgisi():
    print("\n[Y2G-4] gorunum: fare altindaki hucre/malzeme bilgisi ve ozel kodlar")
    from arayuz.goruntuleyici import gorunum as gr
    g = gr.Gorunum("xy", (0.0, 0.0, 0.0), (2.0, 2.0), 2)
    geom = _geom([[7, -2], [-4, 8]], [[1, -2], [-3, -1]])
    adlar = {"malzeme_adlari": {"1": "yakit"}, "hucre_adlari": {"7": "pin"}}
    # Act
    yakit = gr.nokta_bilgisi(g, geom, -0.5, 0.5, adlar)
    tanimsiz = gr.nokta_bilgisi(g, geom, 0.5, 0.5, adlar)
    cakisma = gr.nokta_bilgisi(g, geom, -0.5, -0.5, adlar)
    bosluk = gr.nokta_bilgisi(g, geom, 0.5, -0.5, adlar)
    # Assert
    kontrol("hucre 7 'pin', malzeme 1 'yakit'", yakit.hucre == 7 and yakit.hucre_adi == "pin"
            and yakit.malzeme_adi == "yakit" and yakit.durum == gr.DURUM_NORMAL)
    kontrol("-2 tanimsiz", tanimsiz.durum == gr.DURUM_TANIMSIZ)
    kontrol("-3 cakisma", cakisma.durum == gr.DURUM_CAKISMA)
    kontrol("-1 bosluk", bosluk.durum == gr.DURUM_BOSLUK and bosluk.hucre == 8)
    kontrol("metin koordinat icerir", "x = -0.5" in gr.bilgi_metni(yakit))
    kontrol("pencere disi None", gr.nokta_bilgisi(g, geom, 5.0, 0.0, adlar) is None)


# ----------------------------------------------------------------------------
# renk kipleri
# ----------------------------------------------------------------------------

def test_renk_kipleri():
    print("\n[Y2G-5] renk kipleri: malzeme/hucre/cakisma; -3 ve -2 vurgusu")
    from arayuz.goruntuleyici import renk_kipi as rk
    # Arrange: cakisma hucre kanalinda -4, malzeme kanalinda -3 (OpenMC 0.16, olculdu)
    geom = _geom([[1, 2], [-4, -2]], [[10, 20], [-3, -2]])
    renkler = {10: (255, 0, 0), 20: (0, 0, 255)}
    cak, tan = (1.0, 0.0, 1.0), (1.0, 0.5, 0.0)
    # Act
    malzeme = rk.goruntu(geom, rk.MALZEME, renkler, cak, tan)
    hucre = rk.goruntu(geom, rk.HUCRE, renkler, cak, tan)
    vurgu = rk.goruntu(geom, rk.CAKISMA_KIPI, renkler, cak, tan)
    # Assert
    kontrol("malzeme: 10 kirmizi, 20 mavi", tuple(malzeme[0, 0]) == (255, 0, 0, 255)
            and tuple(malzeme[0, 1]) == (0, 0, 255, 255))
    kontrol("malzeme: cakisma rengi, tanimsiz saydam",
            tuple(malzeme[1, 0]) == (255, 0, 255, 255) and malzeme[1, 1, 3] == 0)
    kontrol("hucre kipinde de cakisma (-4) cakisma rengi",
            tuple(hucre[1, 0]) == (255, 0, 255, 255))
    kontrol("cakisma kipi: -3 ve -2 opak vurgu", tuple(vurgu[1, 0]) == (255, 0, 255, 255)
            and tuple(vurgu[1, 1]) == (255, 128, 0, 255))
    kontrol("cakisma kipi: normal bolge soluk gri", vurgu[0, 0, 0] == vurgu[0, 0, 1]
            == vurgu[0, 0, 2] and vurgu[0, 0, 3] < 255)
    kontrol("sayim", rk.sayim(geom) == {"cakisma": 1, "tanimsiz": 1})
    try:
        rk.goruntu(geom, "sicaklik", renkler, cak, tan)
        hata = False
    except ValueError:
        hata = True
    kontrol("bilinmeyen kip ValueError", hata)


# ----------------------------------------------------------------------------
# mesh bindirmesi
# ----------------------------------------------------------------------------

def _sonuc(tur, izgaralar, merkez=(0.0, 0.0, 0.0)):
    from cekirdek.mesh_tally.sonuc import MeshSonuc
    boyut = tuple(len(g) - 1 for g in izgaralar)
    o = np.arange(np.prod(boyut), dtype=float).reshape(boyut + (1, 1, 1)) + 1.0
    return MeshSonuc(ad="t", tur=tur, izgaralar=tuple(np.asarray(g, float) for g in izgaralar),
                     merkez=merkez, skorlar=("flux",), nuklidler=("total",), enerji=None,
                     ortalama=o, sapma=0.01 * o, ozdeger=True)


def test_duzenli_mesh_bindirme_konumu():
    print("\n[Y2G-6] bindirme: duzenli agda bilinen hucre <-> geometri koordinati (xy ve xz)")
    from arayuz.goruntuleyici import bindirme as bd, gorunum as gr
    # Arrange: x 4 bolme (-2..2), y 2 bolme (0..2), z 3 bolme (0..3)
    s = _sonuc("duzenli", (np.linspace(-2, 2, 5), np.linspace(0, 2, 3), np.linspace(0, 3, 4)))
    deger = s.ortalama[..., 0, 0, 0]
    g = gr.Gorunum("xy", (0.0, 0.0, 2.5), (8.0, 8.0), 80)
    gxz = gr.Gorunum("xz", (0.0, 0.5, 0.0), (8.0, 8.0), 80)
    # Act
    r = bd.raster(s, deger, np.zeros_like(deger, bool), g)
    rxz = bd.raster(s, deger, np.zeros_like(deger, bool), gxz)
    # Assert: (x, y) = (1.5, 0.5) -> hucre (3, 0, 2); z = 2.5 -> k = 2
    i, j = gr.piksel_indeksi(g, 1.5, 0.5, r.deger.shape)
    kontrol("(1.5, 0.5, 2.5) degeri hucre (3, 0, 2)", r.deger[i, j] == deger[3, 0, 2],
            "-> %s / %s" % (r.deger[i, j], deger[3, 0, 2]))
    i, j = gr.piksel_indeksi(g, -1.5, 1.5, r.deger.shape)
    kontrol("(-1.5, 1.5, 2.5) degeri hucre (0, 1, 2)", r.deger[i, j] == deger[0, 1, 2])
    i, j = gr.piksel_indeksi(g, 3.0, 0.5, r.deger.shape)
    kontrol("ag disi NaN", math.isnan(r.deger[i, j]))
    i, j = gr.piksel_indeksi(gxz, -0.5, 0.5, rxz.deger.shape)
    kontrol("xz (y = 0.5): (-0.5, z 0.5) -> hucre (1, 0, 0)", rxz.deger[i, j] == deger[1, 0, 0])
    kontrol("kapsam gorunumle ayni", r.kapsam == g.kapsam)


def test_silindirik_mesh_bindirme_ve_sigma():
    print("\n[Y2G-7] bindirme: silindirik agda (r, phi) hucresi; sigma maskesi guvenilmezi gizler")
    from arayuz.goruntuleyici import bindirme as bd, gorunum as gr
    s = _sonuc("silindirik", ([0.0, 1.0, 2.0], np.linspace(0, 2 * np.pi, 5), [-1.0, 1.0]),
               merkez=(1.0, 0.0, 0.0))
    deger = s.ortalama[..., 0, 0, 0]
    maske = np.zeros_like(deger, bool)
    maske[1, 2, 0] = True                         # r 1-2, phi pi..3pi/2 guvenilmez
    g = gr.Gorunum("xy", (1.0, 0.0, 0.0), (6.0, 6.0), 120)
    # Act
    r = bd.raster(s, deger, maske, g, sigma_maskesi=True)
    acik = bd.raster(s, deger, maske, g, sigma_maskesi=False)
    # Assert: nokta (1 + 1.5 cos 45, 1.5 sin 45) -> r 1, phi 0
    x, y = 1.0 + 1.5 * math.cos(math.pi / 4), 1.5 * math.sin(math.pi / 4)
    i, j = gr.piksel_indeksi(g, x, y, r.deger.shape)
    kontrol("(r 1.5, phi 45) -> hucre (1, 0, 0)", r.deger[i, j] == deger[1, 0, 0])
    x, y = 1.0 + 0.5 * math.cos(-math.pi / 4), 0.5 * math.sin(-math.pi / 4)
    i, j = gr.piksel_indeksi(g, x, y, r.deger.shape)
    kontrol("(r 0.5, phi -45 = 315) -> hucre (0, 3, 0)", r.deger[i, j] == deger[0, 3, 0])
    x, y = 1.0 + 1.5 * math.cos(1.25 * math.pi), 1.5 * math.sin(1.25 * math.pi)
    i, j = gr.piksel_indeksi(g, x, y, r.deger.shape)
    kontrol("sigma maskesi: guvenilmez hucre NaN ve isaretli", math.isnan(r.deger[i, j])
            and r.guvenilmez[i, j])
    kontrol("maske kapali: deger gorunur", acik.deger[i, j] == deger[1, 2, 0])
    kontrol("renk araligi sonlu degerlerden", r.aralik[0] >= 1.0 and r.aralik[1] <= deger.max())


def test_kuresel_mesh_bindirme():
    print("\n[Y2G-8] bindirme: kuresel agda (r, theta) hucresi xz duzleminde")
    from arayuz.goruntuleyici import bindirme as bd, gorunum as gr
    s = _sonuc("kuresel", ([0.0, 1.0, 2.0], [0.0, np.pi / 2, np.pi], [0.0, 2 * np.pi]))
    deger = s.ortalama[..., 0, 0, 0]
    g = gr.Gorunum("xz", (0.0, 0.0, 0.0), (5.0, 5.0), 100)
    r = bd.raster(s, deger, np.zeros_like(deger, bool), g)
    i, j = gr.piksel_indeksi(g, 0.3, -1.5, r.deger.shape)       # r ~1.53, theta > 90
    kontrol("(x 0.3, z -1.5) -> hucre (1, 1, 0)", r.deger[i, j] == deger[1, 1, 0])
    i, j = gr.piksel_indeksi(g, 0.3, 0.5, r.deger.shape)
    kontrol("(x 0.3, z 0.5) -> hucre (0, 0, 0)", r.deger[i, j] == deger[0, 0, 0])


# ----------------------------------------------------------------------------
# kaynak ve kamera
# ----------------------------------------------------------------------------

def test_kaynak_izdusumu():
    print("\n[Y2G-9] kaynak: yalniz dilim kalinligindaki ve penceredeki noktalar izdusurulur")
    from arayuz.goruntuleyici import bindirme as bd, gorunum as gr
    g = gr.Gorunum("xz", (0.0, 1.0, 0.0), (4.0, 4.0), 40)
    noktalar = np.array([[0.5, 1.1, -0.5], [0.5, 3.0, 0.5], [5.0, 1.0, 0.0]])
    u, v = bd.izdusum(noktalar, g, kalinlik=0.5)
    kontrol("bir nokta: (x, z) = (0.5, -0.5)", list(u) == [0.5] and list(v) == [-0.5])
    u, v = bd.izdusum(noktalar, g, kalinlik=None)
    kontrol("kalinlik yok: penceredeki tum noktalar", len(u) == 2)


def test_kamera_vektorleri():
    print("\n[Y2G-10] 3B kamera: azimut/yukselti -> kamera konumu, bakis merkez, yukari z")
    from arayuz.goruntuleyici import kamera as km
    k = km.Kamera(azimut=0.0, yukselti=0.0, uzaklik_kati=1.0, gorus=60.0)
    v = km.vektorler(k, (6.0, 8.0), 0.0 or None)
    d = v["kamera"]
    kontrol("azimut 0, yukselti 0: +x ekseninde", d[0] > 0 and abs(d[1]) < 1e-9
            and abs(d[2]) < 1e-9)
    kontrol("bakis orijin, yukari z", v["bakis"] == [0.0, 0.0, 0.0]
            and np.allclose(v["yukari"], (0, 0, 1)))
    ust = km.vektorler(km.Kamera(azimut=90.0, yukselti=90.0), (6.0, 8.0), 10.0)
    kontrol("tepeden bakis: yukari vektoru bakisa paralel degil",
            abs(np.dot(np.subtract(ust["kamera"], ust["bakis"]), ust["yukari"])) <
            0.99 * np.linalg.norm(ust["kamera"]))
    uzak = km.vektorler(km.Kamera(uzaklik_kati=2.0, gorus=60.0), (6.0, 8.0), 10.0)
    yakin = km.vektorler(km.Kamera(uzaklik_kati=1.0, gorus=60.0), (6.0, 8.0), 10.0)
    kontrol("uzaklik kati mesafeyi olcekler", math.isclose(
        np.linalg.norm(uzak["kamera"]), 2 * np.linalg.norm(yakin["kamera"])))
    from cekirdek import cizim_sureci as cs
    istek = dict(km.istek(k, (6.0, 8.0), None, (64, 48), "material", []), tur="isin", no=1,
                 spec={})
    kontrol("isin istegi isci dogrulamasindan gecer", cs.istegi_dogrula(istek) is not None)


def test_tally_dizileri_normalizasyon_ve_maske():
    print("\n[Y2G-11] bindirme: hacim normalizasyonu, skorsuz NaN, sigma maskesi esikle")
    from dataclasses import replace
    from arayuz.goruntuleyici import bindirme as bd
    s = _sonuc("duzenli", ([0.0, 1.0, 3.0], [0.0, 1.0], [0.0, 1.0]))
    o = np.array(s.ortalama)
    o[0, 0, 0] = 0.0
    sg = np.array(s.sapma)
    sg[1, 0, 0] = 0.5 * o[1, 0, 0]                     # %50 bagil hata
    s = replace(s, ortalama=o, sapma=sg)
    deger, maske, birim = bd.tally_dizileri(s, "flux", None, "hacim", 0.10, False)
    kontrol("skorsuz hucre NaN", math.isnan(deger[0, 0, 0]))
    kontrol("hacim basina: deger / 2 cm3", math.isclose(deger[1, 0, 0],
                                                        o[1, 0, 0, 0, 0, 0] / 2.0))
    kontrol("maske: skorsuz ve %50 hatali hucre", maske[0, 0, 0] and maske[1, 0, 0])
    kontrol("birim n/cm2", "n/cm²" in birim, "-> %s" % birim)


def test_istek_sirasi():
    print("\n[Y2G-12] istek sirasi: ayni tur hemen gider, farkli tur bekler, son -> siradaki")
    from arayuz.goruntuleyici.istek_sirasi import IstekSirasi
    giden = []
    sira = IstekSirasi(lambda istek: giden.append(istek["ad"]) or len(giden))
    sira.iste("kesit", {"ad": "k1"})
    sira.iste("kesit", {"ad": "k2"})                 # k1'i iptal eder (istemci)
    sira.iste("kaynak", {"ad": "q1"})
    sira.iste("kaynak", {"ad": "q2"})                # q1 atlanir
    sira.iste("isin", {"ad": "i1"})
    kontrol("k1, k2 hemen; kaynak bekler", giden == ["k1", "k2"])
    kontrol("guncel no 2 -> kesit", sira.tur(2) == "kesit" and sira.tur(1) is None)
    sira.bitti(1)
    kontrol("eski son etkisiz", giden == ["k1", "k2"])
    sira.bitti(2)
    kontrol("son -> q2 (q1 atlandi)", giden == ["k1", "k2", "q2"] and sira.tur(3) == "kaynak")
    sira.sifirla()
    kontrol("cokme -> siradaki isin", giden[-1] == "i1" and sira.mesgul_mu())
    sira.bitti(4)
    kontrol("bos", not sira.mesgul_mu())


HIZLI = [test_varsayilan_gorunum_ve_istek, test_yakinlastir_kaydir_degismez,
         test_piksel_koordinat_eslemesi, test_nokta_bilgisi, test_renk_kipleri,
         test_duzenli_mesh_bindirme_konumu, test_silindirik_mesh_bindirme_ve_sigma,
         test_kuresel_mesh_bindirme, test_kaynak_izdusumu, test_kamera_vektorleri,
         test_tally_dizileri_normalizasyon_ve_maske, test_istek_sirasi]
YAVAS = []
