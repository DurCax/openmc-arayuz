# -*- coding: utf-8 -*-
"""
 test_y2_isci.py  --  v3 Y2 goruntuleyici: cizim iscisi protokol ekleri
                      (ozel kesit penceresi, adlar, 3B isin izleme, kaynak
                      noktalari), bilinen cakismali modelde -3/-2 pikselleri,
                      3B goruntu testi
"""

import io
import os

import numpy as np

from testler.ortak_test import kontrol, ORNEK

_KIRMIZI, _MAVI = (200, 0, 0), (0, 0, 200)


# ----------------------------------------------------------------------------
# yardimcilar
# ----------------------------------------------------------------------------

def _kutu(yari, sinir="vacuum"):
    import openmc
    yuz = [openmc.XPlane(-yari, boundary_type=sinir), openmc.XPlane(yari, boundary_type=sinir),
           openmc.YPlane(-yari, boundary_type=sinir), openmc.YPlane(yari, boundary_type=sinir),
           openmc.ZPlane(-yari, boundary_type=sinir), openmc.ZPlane(yari, boundary_type=sinir)]
    return +yuz[0] & -yuz[1] & +yuz[2] & -yuz[3] & +yuz[4] & -yuz[5]


def _malzemeler():
    import openmc
    m1 = openmc.Material(name="yakit")
    m1.add_nuclide("U235", 1.0)
    m1.set_density("g/cm3", 10.0)
    m2 = openmc.Material(name="su")
    m2.add_nuclide("H1", 2.0)
    m2.add_nuclide("O16", 1.0)
    m2.set_density("g/cm3", 1.0)
    return m1, m2


def _ayarlar(yari):
    import openmc
    s = openmc.Settings()
    s.batches, s.inactive, s.particles = 2, 1, 100
    s.source = openmc.IndependentSource(
        space=openmc.stats.Box((-yari,) * 3, (yari,) * 3), constraints={"fissionable": True})
    return s


def cakismali_model():
    """Bilinen cakisma: 10 cm kutu; A (yakit) x < 1, B (su) x > -1, ikisi de y < 3.
    -1 < x < 1, y < 3 iki hucrede (cakisma, -3); y > 3 hicbir hucrede (tanimsiz, -2)."""
    import openmc
    openmc.reset_auto_ids()
    m1, m2 = _malzemeler()
    kutu = _kutu(5.0)
    sag, sol, ust = openmc.XPlane(1.0), openmc.XPlane(-1.0), openmc.YPlane(3.0)
    a = openmc.Cell(name="A", fill=m1, region=kutu & -sag & -ust)
    b = openmc.Cell(name="B", fill=m2, region=kutu & +sol & -ust)
    model = openmc.Model(geometry=openmc.Geometry([a, b]),
                         materials=openmc.Materials([m1, m2]), settings=_ayarlar(5.0))
    return model, {"sinir_kutu": (10.0, 10.0), "renkler": {m1: _KIRMIZI, m2: _MAVI}}


def kure_modeli():
    """Bosluk dolu 10 cm kutuda r = 3 cm yakit kuresi (3B isin izleme)."""
    import openmc
    openmc.reset_auto_ids()
    m1, m2 = _malzemeler()
    kure = openmc.Sphere(r=3.0)
    ic = openmc.Cell(name="kure", fill=m1, region=-kure)
    dis = openmc.Cell(name="bosluk", fill=None, region=+kure & _kutu(5.0))
    model = openmc.Model(geometry=openmc.Geometry([ic, dis]),
                         materials=openmc.Materials([m1, m2]), settings=_ayarlar(3.0))
    return model, {"sinir_kutu": (10.0, 10.0), "renkler": {m1: _KIRMIZI, m2: _MAVI}}


def _oturum(model_kurucu, monkeypatch):
    """Gercek cizim oturumu; kurucu.kur verilen modeli dondurur."""
    from cekirdek import cizim_sureci as cs, kurucu, sema
    monkeypatch.setattr(kurucu, "kur", lambda _spec: model_kurucu())
    oturum = cs.Oturum()
    oturum.hazirla(sema.yukle(os.path.join(ORNEK, "pwr_17x17.json")))
    return oturum


class _SahteOturum:
    """openmc.lib'siz oturum: cagrilari kaydeder."""

    def __init__(self):
        self.kesit_ekleri = []
        self.isin_istekleri = []

    def hazirla(self, spec):
        return True

    def ozellikler(self):
        return {"sinir_kutu": [2.0, 2.0], "yukseklik": None, "renkler": {}, "gosterge": []}

    def adlar(self):
        return {"malzeme_adlari": {"1": "yakit"}, "hucre_adlari": {"7": "pin"}}

    def kesit(self, eksen, piksel, cakisma=False, **ek):
        self.kesit_ekleri.append(ek)
        dikey = ek.get("piksel_dikey", piksel)
        return ek.get("genislik", (2.0, 2.0)), np.ones((dikey, piksel, 3), np.int32), []

    def isin(self, istek):
        self.isin_istekleri.append(istek)
        w, h = istek["piksel"]
        return np.zeros((h, w, 3), np.uint8)

    def kaynak(self, istek):
        from cekirdek import cizim_goruntu as cg
        return ({"tur": cg.YANIT_KAYNAK, "no": istek["no"], "kaynak": "ayar", "toplam": 2,
                 "deneme": 2, "sure": 0.0}, {"r": np.zeros((2, 3))})

    def kapat(self):
        pass


def _isle(istek, oturum):
    from cekirdek import cizim_sureci as cs
    oku, yaz = os.pipe()
    os.close(yaz)
    cikis = io.BytesIO()
    durum = cs.isle(cs.istegi_dogrula(istek), oturum, cs.Kanal(oku, cikis))
    os.close(oku)
    return durum, cs.CerceveCozucu().besle(cikis.getvalue())


def _isin_istegi(**ek):
    istek = {"tur": "isin", "no": 3, "spec": {"ad": "x"}, "kamera": [20.0, 0.0, 0.0],
             "bakis": [0.0, 0.0, 0.0], "yukari": [0.0, 0.0, 1.0], "gorus": 40.0,
             "piksel": [64, 48]}
    istek.update(ek)
    return istek


# ----------------------------------------------------------------------------
# protokol (openmc.lib'siz)
# ----------------------------------------------------------------------------

def test_kesit_ekleri_dogrulanir():
    print("\n[Y2I-1] protokol: kesit ogesinde istege bagli merkez/genislik/piksel_dikey")
    from cekirdek import cizim_sureci as cs
    taban = {"tur": "ciz", "no": 1, "spec": {}}
    # Arrange
    iyi = dict(taban, kesitler=[{"eksen": "xz", "piksel": 64, "merkez": [1, 2, 3],
                                 "genislik": [4.0, 8.0], "piksel_dikey": 128}])
    kotuler = [{"merkez": [1, 2]}, {"merkez": [0, 0, float("nan")]}, {"genislik": [0, 1]},
               {"genislik": [1.0]}, {"piksel_dikey": 4}, {"piksel_dikey": True}]
    # Act
    dogru = cs.istegi_dogrula(iyi)
    reddedilen = []
    for ek in kotuler:
        try:
            cs.istegi_dogrula(dict(taban, kesitler=[dict({"eksen": "xy", "piksel": 64}, **ek)]))
        except cs.ProtokolHatasi:
            reddedilen.append(ek)
    # Assert
    kontrol("gecerli ekli kesit kabul", dogru["kesitler"][0]["piksel_dikey"] == 128)
    kontrol("bozuk ekler reddedilir", len(reddedilen) == len(kotuler), "-> %s" % reddedilen)
    kontrol("eksiz eski istek gecerli (geri uyum)",
            cs.istegi_dogrula(dict(taban, kesitler=[{"eksen": "xy", "piksel": 64}])) is not None)


def test_isin_ve_kaynak_istekleri_dogrulanir():
    print("\n[Y2I-2] protokol: 'isin' ve 'kaynak' istekleri sinirda denetlenir")
    from cekirdek import cizim_sureci as cs
    # Arrange
    kotu_isin = [dict(kamera=[0.0, 0.0, 0.0]), dict(yukari=[0.0, 0.0, 0.0]),
                 dict(gorus=180.0), dict(piksel=[64]), dict(piksel=[64, 4000]),
                 dict(renk="sicaklik"), dict(gizli=["a"]), dict(dagilim=2.0)]
    kotu_kaynak = [{"sayi": 0}, {"sayi": 10 ** 9}, {"sayi": 5, "tohum": -1},
                   {"sayi": 5, "statepoint": 3}]
    # Act
    red_isin = [k for k in kotu_isin if _reddedilir(cs, _isin_istegi(**k))]
    red_kaynak = [k for k in kotu_kaynak
                  if _reddedilir(cs, dict({"tur": "kaynak", "no": 1, "spec": {}}, **k))]
    # Assert
    kontrol("gecerli isin istegi kabul", not _reddedilir(cs, _isin_istegi()))
    kontrol("bozuk isin istekleri reddedilir", len(red_isin) == len(kotu_isin),
            "-> %d/%d" % (len(red_isin), len(kotu_isin)))
    kontrol("gecerli kaynak istegi kabul",
            not _reddedilir(cs, {"tur": "kaynak", "no": 1, "spec": {}, "sayi": 100}))
    kontrol("bozuk kaynak istekleri reddedilir", len(red_kaynak) == len(kotu_kaynak))


def _reddedilir(cs, istek):
    try:
        cs.istegi_dogrula(istek)
    except cs.ProtokolHatasi:
        return True
    return False


def test_isle_yeni_istekleri_yanitlar():
    print("\n[Y2I-3] isci: isin -> 'goruntu' (rgb), kaynak -> 'kaynak_noktalari' (r), "
          "kesit ekleri ve adlar oturuma gecer")
    oturum = _SahteOturum()
    # Act
    d_isin, y_isin = _isle(_isin_istegi(), oturum)
    d_kay, y_kay = _isle({"tur": "kaynak", "no": 4, "spec": {}, "sayi": 2}, oturum)
    d_kes, y_kes = _isle({"tur": "ciz", "no": 5, "spec": {}, "adlar": True,
                          "kesitler": [{"eksen": "xy", "piksel": 16, "merkez": [1, 0, 0],
                                        "genislik": [1.0, 2.0], "piksel_dikey": 32}]}, oturum)
    # Assert
    turler = [c.baslik["tur"] for c in y_isin]
    kontrol("isin: model, goruntu, son tamam", turler == ["model", "goruntu", "son"]
            and d_isin == "tamam", "-> %s" % turler)
    kontrol("goruntu dizisi (48, 64, 3) uint8",
            y_isin[1].diziler["rgb"].shape == (48, 64, 3) and y_isin[1].diziler["rgb"].dtype
            == np.uint8)
    kontrol("kaynak: kaynak_noktalari + r (2, 3)", d_kay == "tamam"
            and y_kay[1].baslik["tur"] == "kaynak_noktalari"
            and y_kay[1].diziler["r"].shape == (2, 3))
    kontrol("kesit ekleri oturuma gecer", oturum.kesit_ekleri[-1] == {
        "merkez": (1.0, 0.0, 0.0), "genislik": (1.0, 2.0), "piksel_dikey": 32})
    kontrol("kesit yanitinda merkez ve (32, 16) geom",
            y_kes[1].baslik["merkez"] == [1.0, 0.0, 0.0]
            and y_kes[1].diziler["geom"].shape == (32, 16, 3) and d_kes == "tamam")
    kontrol("adlar istenince model yanitinda", y_kes[0].baslik["hucre_adlari"] == {"7": "pin"})
    kontrol("adlar istenmezse model yanitinda yok",
            "hucre_adlari" not in y_isin[0].baslik)


def test_ayar_kaynagi_nokta_ve_kutu():
    print("\n[Y2I-4] kaynak: Point tek nokta, kisitsiz Box kutu icinde, kabul orani dusukse hata")
    import openmc
    from cekirdek import cizim_goruntu as cg
    # Arrange
    nokta = openmc.IndependentSource(space=openmc.stats.Point((1.0, 2.0, 3.0)))
    kutu = openmc.IndependentSource(space=openmc.stats.Box((-1, -2, -3), (1, 2, 3)))
    kisitli = openmc.IndependentSource(space=openmc.stats.Box((-1, -1, -1), (1, 1, 1)),
                                       constraints={"fissionable": True})
    # Act
    r_nokta, _d = cg.ayar_kaynagi([nokta], frozenset(), 10, 1)
    r_kutu, _d = cg.ayar_kaynagi([kutu], frozenset(), 500, 1)
    r_tekrar, _d = cg.ayar_kaynagi([kutu], frozenset(), 500, 1)
    eski = cg._fisil_noktalar
    cg._fisil_noktalar = lambda noktalar, fisil: np.zeros(len(noktalar), dtype=bool)
    try:
        cg.ayar_kaynagi([kisitli], frozenset({1}), 10, 1)
        hata = None
    except ValueError as e:
        hata = str(e)
    finally:
        cg._fisil_noktalar = eski
    # Assert
    kontrol("Point: 10 nokta, hepsi (1, 2, 3)", r_nokta.shape == (10, 3)
            and np.allclose(r_nokta, (1.0, 2.0, 3.0)))
    kontrol("Box: 500 nokta kutu icinde", r_kutu.shape == (500, 3)
            and (np.abs(r_kutu) <= (1, 2, 3)).all())
    kontrol("ayni tohum ayni noktalar", np.array_equal(r_kutu, r_tekrar))
    kontrol("hic kabul yoksa kabul orani hatasi", hata is not None and "%" in hata, "-> %s" % hata)


def test_ayar_kaynagi_desteklenmeyen():
    print("\n[Y2I-5] kaynak: desteklenmeyen dagilim ve bolge kisiti acik hata verir")
    import openmc
    from cekirdek import cizim_goruntu as cg
    kure = openmc.IndependentSource(space=openmc.stats.spherical_uniform(r_outer=2.0))
    bolge = openmc.IndependentSource(space=openmc.stats.Point(),
                                     constraints={"domains": [openmc.Material()]})
    hatalar = []
    for kaynak in (kure, bolge):
        try:
            cg.ayar_kaynagi([kaynak], frozenset(), 5, 1)
        except ValueError as e:
            hatalar.append(str(e))
    kontrol("iki durum da ValueError", len(hatalar) == 2, "-> %s" % hatalar)
    kontrol("bos kaynak listesi hata", _deger_hatasi(lambda: cg.ayar_kaynagi([], frozenset(), 5, 1)))


def _deger_hatasi(islev):
    try:
        islev()
    except ValueError:
        return True
    return False


def test_statepoint_kaynak_bankasi(gecici=None):
    print("\n[Y2I-6] kaynak: statepoint kaynak bankasi (source_bank) okunur, alt kume rastgele")
    import tempfile
    import h5py
    from cekirdek import cizim_goruntu as cg
    # Arrange: openmc'nin source_bank bicimi (r, u, E, wgt ...)
    dizin = gecici or tempfile.mkdtemp(prefix="y2_sp_")
    yol = os.path.join(str(dizin), "statepoint.5.h5")
    xyz = np.dtype([("x", "<f8"), ("y", "<f8"), ("z", "<f8")])
    tur = np.dtype([("r", xyz), ("u", xyz), ("E", "<f8"), ("wgt", "<f8")])
    banka = np.zeros(50, dtype=tur)
    banka["r"]["x"] = np.arange(50.0)
    banka["r"]["z"] = -1.0
    with h5py.File(yol, "w") as f:
        f.attrs["source_present"] = 1
        f.create_dataset("source_bank", data=banka)
    bos = os.path.join(str(dizin), "bos.h5")
    with h5py.File(bos, "w") as f:
        f.attrs["source_present"] = 0
    # Act
    tumu, toplam = cg.statepoint_kaynagi(yol, 100, 1)
    alt, _t = cg.statepoint_kaynagi(yol, 10, 1)
    # Assert
    kontrol("tum banka (50, 3), toplam 50", tumu.shape == (50, 3) and toplam == 50)
    kontrol("x ve z alanlari dogru", np.array_equal(tumu[:, 0], np.arange(50.0))
            and (tumu[:, 2] == -1.0).all())
    kontrol("alt kume 10 farkli nokta", alt.shape == (10, 3) and len(set(alt[:, 0])) == 10)
    kontrol("kaynaksiz statepoint ve olmayan dosya acik hata",
            _deger_hatasi(lambda: cg.statepoint_kaynagi(bos, 5, 1))
            and _deger_hatasi(lambda: cg.statepoint_kaynagi(yol + ".yok", 5, 1)))


# ----------------------------------------------------------------------------
# gercek openmc.lib oturumu (nukleer veri gerekmez ama conftest init'i korur)
# ----------------------------------------------------------------------------

def test_cakismali_modelde_kodlar(monkeypatch):
    print("\n[Y2I-7] bilinen cakismali model: -1<x<1, y<3 -> -3 (cakisma); y>3 -> -2 (tanimsiz)")
    from cekirdek import cizim_sureci as cs
    oturum = _oturum(cakismali_model, monkeypatch)
    try:
        # Act: 10 x 10 piksel = 1 cm piksel; piksel merkezi x = -4.5 + j, y = 4.5 - i
        _g, geom, cakismalar = oturum.kesit("xy", 10, cakisma=True)
        _g, temiz, _c = oturum.kesit("xy", 10, cakisma=False)
    finally:
        oturum.kapat()
    hucre = geom[..., 0]
    beklenen = np.zeros((10, 10), dtype=bool)
    beklenen[2:, 4:6] = True                       # y = 2.5 .. -4.5, x = -0.5, 0.5
    kontrol("cakisma pikselleri tam olarak bilinen bolge", np.array_equal(hucre == cs.CAKISMA,
                                                                         beklenen),
            "-> %s" % (hucre == cs.CAKISMA).astype(int).tolist())
    kontrol("y > 3 satirlari tanimsiz (-2)", (hucre[:2] == cs.TANIMSIZ).all())
    kontrol("cakisma bilgisi A ve B hucreleri", len(cakismalar) == 1
            and sorted(cakismalar[0][1:]) == [1, 2], "-> %s" % cakismalar)
    kontrol("denetimsiz kesitte -3 yok", not (temiz[..., 0] == cs.CAKISMA).any())


def test_ozel_kesit_penceresi(monkeypatch):
    print("\n[Y2I-8] ozel kesit: merkez/genislik verilen pencereyi dilimler (konum dogrulugu)")
    import openmc.lib
    oturum = _oturum(cakismali_model, monkeypatch)
    try:
        sol_g, sol, _c = oturum.kesit("xy", 16, merkez=(-3.0, 0.0, 0.0), genislik=(2.0, 2.0))
        sag_g, sag, _c = oturum.kesit("xy", 16, merkez=(3.0, 0.0, 0.0), genislik=(2.0, 2.0))
        _g, xz, _c = oturum.kesit("xz", 20, merkez=(0.0, 4.0, 0.0), genislik=(10.0, 4.0),
                                  piksel_dikey=8)
        m_sol = openmc.lib.find_material((-3.0, 0.0, 0.0)).id
        m_sag = openmc.lib.find_material((3.0, 0.0, 0.0)).id
    finally:
        oturum.kapat()
    kontrol("x = -3 penceresi tamamen sol malzeme", (sol[..., 2] == m_sol).all())
    kontrol("x = 3 penceresi tamamen sag malzeme", (sag[..., 2] == m_sag).all())
    kontrol("genislik yanitta doner", sol_g == (2.0, 2.0) and sag_g == (2.0, 2.0))
    kontrol("y = 4 xz duzlemi (8, 20) ve tamamen tanimsiz",
            xz.shape == (8, 20, 3) and (xz[..., 0] == -2).all())


def test_isin_izleme_goruntusu(monkeypatch):
    print("\n[Y2I-9] 3B gorunum: kure modelinde merkez piksel yakit rengi, kose zemin; "
          "gizlenince zemin")
    from cekirdek import cizim_goruntu as cg
    oturum = _oturum(kure_modeli, monkeypatch)
    try:
        img = oturum.isin(_isin_istegi())
        hucre = oturum.isin(_isin_istegi(renk="cell"))
        mid = next(m.id for m in oturum.bilgi["renkler"] if m.name == "yakit")
        gizli = oturum.isin(_isin_istegi(gizli=[mid]))
        tekrar = oturum.isin(_isin_istegi())
    finally:
        oturum.kapat()
    orta, kose = img[24, 32].astype(int), img[0, 0].astype(int)
    kontrol("goruntu (48, 64, 3) uint8", img.shape == (48, 64, 3) and img.dtype == np.uint8)
    kontrol("merkez piksel kirmizi baskin (golgeli yakit)", orta[0] > 2 * max(orta[1], orta[2])
            and orta[0] > 40, "-> %s" % orta.tolist())
    kontrol("kose zemin (kure disi)", not np.array_equal(kose, orta), "-> %s" % kose.tolist())
    kontrol("hucre kipinde renk farkli", not np.array_equal(hucre[24, 32], img[24, 32]))
    kontrol("yakit gizlenince merkez zemin rengi", np.array_equal(gizli[24, 32], img[0, 0]))
    kontrol("ayni istek ayni goruntu (cizim nesnesi yeniden kullanilir)",
            np.array_equal(img, tekrar))
    kontrol("renk kipi sabitleri", cg.RENK_HUCRE == "cell")


def test_fisil_kisitli_kaynak(monkeypatch):
    print("\n[Y2I-10] kaynak: fisil kisitli kutu kaynagi yalniz yakitta (x < 1, y < 3)")
    oturum = _oturum(cakismali_model, monkeypatch)
    try:
        baslik, diziler = oturum.kaynak({"no": 9, "sayi": 300, "tohum": 2})
    finally:
        oturum.kapat()
    r = diziler["r"]
    kontrol("300 nokta, kaynak 'ayar'", r.shape == (300, 3) and baslik["kaynak"] == "ayar")
    kontrol("hepsi yakit bolgesinde", (r[:, 0] < 1.0).all() and (r[:, 1] < 3.0).all())
    kontrol("deneme > kabul (reddedilen var)", baslik["deneme"] > 300)


HIZLI = [test_kesit_ekleri_dogrulanir, test_isin_ve_kaynak_istekleri_dogrulanir,
         test_isle_yeni_istekleri_yanitlar, test_ayar_kaynagi_nokta_ve_kutu,
         test_ayar_kaynagi_desteklenmeyen, test_statepoint_kaynak_bankasi,
         test_cakismali_modelde_kodlar, test_ozel_kesit_penceresi, test_isin_izleme_goruntusu,
         test_fisil_kisitli_kaynak]
YAVAS = []
# '-p' kipi veri istemez; conftest koruyucusu veri yokken openmc.lib.init'i yasaklar.
VERI_GEREKEN = [test_cakismali_modelde_kodlar, test_ozel_kesit_penceresi,
                test_isin_izleme_goruntusu, test_fisil_kisitli_kaynak]
