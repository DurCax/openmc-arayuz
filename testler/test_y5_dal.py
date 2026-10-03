# -*- coding: utf-8 -*-
"""
 test_y5_dal.py  --  v3 Y5: dal (branch) hesaplari (cekirdek/dal.py)

   [Y5-D1] Noktalar: taban once, sonra kartezyen carpim; sinirlar ve girdi hatalari.
   [Y5-D2] Kosul uygulama tek degiskenli tarama ile AYNI (tarama.parametre_uygula);
           taban spec degismez; cok malzemeli hedef.
   [Y5-D3] Varsayilan hedefler: T_yakit fisil yakita, C_bor / T_mod / rho_mod sogutucuya.
   [Y5-D4] Bilesim yazma: sonuc adimindaki atom sayilari malzemeye gecer (hacim
           ve kimlik denetimli); uyusmayan hacim / eksik kimlik ValueError.
   [Y5-D5] Tablo: dk = (k - k_taban) x 1e5, sigma = hypot; basarisiz is hata ile;
           CSV baslik ve formul korumasi.
   [Y5-D6] (YAVAS) Gercek dal koşulari: adim 0 ve 1; taban dal tukenmenin k'siyla
           ve adim-0 dallari tek degiskenli taramayla 2 sigma icinde tutarli.
"""

import copy
import math
import os

from testler.ortak_test import ORNEK, kontrol


def _spec():
    from cekirdek import sema
    s = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    s["tukenme"].update(var=True, zincir="casl_termal")
    return s


def test_noktalar_ve_hatalar():
    print("\n[Y5-D1] noktalar: taban + kartezyen; hatalar")
    from cekirdek import dal
    s = _spec()
    a = dal.DalAyar((0, 2), (dal.degisken(s, "yakit_sicaklik", [600, 900]),
                             dal.degisken(s, "bor_ppm", [0, 500, 1000])))
    n = dal.noktalar(a)
    kontrol("1 taban + 2x3 nokta", len(n) == 7 and n[0] == {}, repr(n))
    kontrol("ilk degisken en dista",
            [x["T_yakit"] for x in n[1:]] == [600, 600, 600, 900, 900, 900])
    tek = dal.noktalar(dal.DalAyar((0,), a.degiskenler, bicim="tek"))
    kontrol("tek bicim: taban + 2 + 3 nokta, her biri tek degisken",
            len(tek) == 6 and all(len(x) <= 1 for x in tek), repr(tek))
    kontrol("bilinmeyen bicim reddedilir", _hata(lambda: dal.DalAyar((0,), bicim="x")))
    kontrol("taban kapaliysa yok", dal.noktalar(dal.DalAyar((0,), a.degiskenler, taban=False))[0]
            != {})
    for ad, f in (("adimsiz", lambda: dal.DalAyar(())),
                  ("negatif adim", lambda: dal.DalAyar((-1,))),
                  ("degiskensiz ve tabansiz", lambda: dal.DalAyar((0,), (), taban=False)),
                  ("bilinmeyen tur", lambda: dal.DalDegiskeni("yok", ("su",), (1.0,))),
                  ("bos deger", lambda: dal.DalDegiskeni("bor_ppm", ("su",), ())),
                  ("NaN deger", lambda: dal.DalDegiskeni("bor_ppm", ("su",), (float("nan"),))),
                  ("tekrarli degisken", lambda: dal.DalAyar(
                      (0,), (a.degiskenler[0], a.degiskenler[0]))),
                  ("cok nokta", lambda: dal.DalAyar(
                      tuple(range(101)), (dal.degisken(s, "bor_ppm", range(101)),)))):
        try:
            f()
            kontrol("%s reddedilir" % ad, False)
        except ValueError:
            kontrol("%s reddedilir" % ad, True)


def test_kosul_taramayla_ayni():
    print("\n[Y5-D2] dal kosulu = tarama.parametre_uygula; taban degismez")
    from cekirdek import dal, tarama
    s = _spec()
    kopya = copy.deepcopy(s)
    a = dal.DalAyar((0,), (dal.degisken(s, "yakit_sicaklik", [700]),
                           dal.degisken(s, "bor_ppm", [400]),
                           dal.degisken(s, "sogutucu_sicaklik", [580])))
    y, notlar = dal.dal_spec(s, a, {"T_yakit": 700, "C_bor": 400, "T_mod": 580})
    kontrol("taban degismedi", s == kopya)
    ref, _n = tarama.parametre_uygula(s, "yakit_sicaklik", "uo2", 700, taban=s)
    kontrol("yakit sicakligi taramayla ayni",
            y["malzemeler"][0]["sicaklik"] == ref["malzemeler"][0]["sicaklik"] == 700.0)
    ref, _n = tarama.parametre_uygula(s, "bor_ppm", "su", 400, taban=s)
    su = [m for m in y["malzemeler"] if m["ad"] == "su"][0]
    kontrol("bor bilesimi taramayla ayni (T_mod ile birlikte degisen yogunluk haric)",
            su["sicaklik"] == 580.0 and any(b["isim"].startswith("B") for b in su["bilesim"]))
    y2, _n = dal.dal_spec(s, dal.DalAyar((0,), (dal.degisken(s, "bor_ppm", [400]),)), {"C_bor": 400})
    ref = tarama.parametre_uygula(s, "bor_ppm", "su", 400, taban=s)[0]
    kontrol("tek degiskenli: spec tarama ile birebir", y2 == ref)
    y3, _n = dal.dal_spec(s, a, {})
    kontrol("taban nokta: spec ayni", y3 == s)
    s["malzemeler"].append(dict(copy.deepcopy(s["malzemeler"][0]), ad="uo2_b"))
    a2 = dal.DalAyar((0,), (dal.DalDegiskeni("yakit_sicaklik", ("uo2", "uo2_b"), (650.0,)),))
    y4, _n = dal.dal_spec(s, a2, {"T_yakit": 650.0})
    kontrol("cok malzemeli hedef: hepsi", [m["sicaklik"] for m in y4["malzemeler"]
            if m["ad"] in ("uo2", "uo2_b")] == [650.0, 650.0])


def test_varsayilan_hedefler():
    print("\n[Y5-D3] varsayilan hedefler")
    from cekirdek import dal
    s = _spec()
    kontrol("T_yakit -> uo2", dal.varsayilan_hedefler(s, "yakit_sicaklik") == ("uo2",))
    for t in ("bor_ppm", "sogutucu_sicaklik", "malzeme_yogunluk"):
        kontrol("%s -> su" % t, dal.varsayilan_hedefler(s, t) == ("su",))
    kontrol("bilinmeyen tur reddedilir", _hata(lambda: dal.varsayilan_hedefler(s, "x")))


def _hata(f):
    try:
        f()
    except ValueError:
        return True
    return False


class _SahteSonuc:
    """openmc.deplete StepResult'in dal.bilesim_uygula'nin kullandigi yuzu."""
    def __init__(self, hacimler, atomlar):
        self.index_mat = {k: i for i, k in enumerate(hacimler)}
        self.volume = hacimler
        self._atom = atomlar
        self.index_nuc = sorted({n for d in atomlar.values() for n in d})

    def __getitem__(self, anahtar):
        mid, nuklid = anahtar
        return self._atom.get(mid, {}).get(nuklid, 0.0)


class _SahteSonuclar(list):
    pass


def test_bilesim_yazma():
    print("\n[Y5-D4] bilesim yazma: atom sayilari -> yogunluk; hacim/kimlik denetimi")
    from cekirdek import tukenme
    from cekirdek import dal
    s = _spec()
    s["tukenme"]["malzemeleri_ayir"] = False
    model, bilgi = tukenme.hazirla(s)
    uo2 = [m for m in model.materials if m.depletable][0]
    V = uo2.volume
    atom = 2.0e20
    sonuc = _SahteSonuc({str(uo2.id): V}, {str(uo2.id): {"U235": atom, "Xe135": 1.0e15,
                                                             "Yok999": 5.0e19}})
    veri = frozenset(["U235", "U238", "Xe135", "O16"])
    n = dal.bilesim_uygula(model, _SahteSonuclar([sonuc]), 0, veri)
    yog = uo2.get_nuclide_atom_densities()
    kontrol("1 malzeme yazildi", n == 1)
    kontrol("U235 = atom/hacim (atom/b-cm)", abs(yog["U235"] - 1e-24 * atom / V) < 1e-12 * yog["U235"],
            repr(yog["U235"]))
    kontrol("Xe135 eklendi", abs(yog["Xe135"] - 1e-24 * 1e15 / V) < 1e-12 * yog["Xe135"])
    kontrol("verisi olmayan nuklid yazilmadi", "Yok999" not in yog)
    kontrol("U238 ilk bilesimden korundu", yog.get("U238", 0) > 0)
    kontrol("dal malzemesi yanmaz", not uo2.depletable)
    bozuk = _SahteSonuc({str(uo2.id): V * 1.01}, {})
    kontrol("hacim uyusmazligi", _hata(lambda: dal.bilesim_uygula(
        model, _SahteSonuclar([bozuk]), 0, veri)))
    eksik = _SahteSonuc({"99999": V}, {})
    kontrol("modelde olmayan kimlik", _hata(lambda: dal.bilesim_uygula(
        model, _SahteSonuclar([eksik]), 0, veri)))
    kontrol("olmayan adim", _hata(lambda: dal.bilesim_uygula(
        model, _SahteSonuclar([sonuc]), 3, veri)))


def _durum(kimlik, adim, nokta, degerler, k, asama="bitti", hata=None):
    from cekirdek import kuyruk
    return kuyruk.IsDurumu(kimlik=kimlik, ad=kimlik, dizin="/tmp/x",
                           asama=kuyruk.Asama(asama), k=k, hata=hata,
                           etiket={"dal": {"adim": adim, "yanma": 10.0 * adim, "zaman_d": 25.0 * adim,
                                           "nokta": nokta, "degerler": degerler, "notlar": []}})


def test_tablo_ve_csv():
    print("\n[Y5-D5] tablo: dk, sigma, hata, CSV")
    from cekirdek import dal
    d = [_durum("c", 1, 1, {"T_yakit": 900.0}, (1.0100, 0.0004)),
         _durum("a", 0, 0, {}, (1.2000, 0.0003)),
         _durum("b", 0, 1, {"T_yakit": 900.0}, (1.1900, 0.0004)),
         _durum("d", 1, 0, {}, (1.0200, 0.0003)),
         _durum("e", 1, 2, {"T_yakit": 1200.0}, None, "basarisiz", "koşu başarısız")]
    t = dal.dal_tablosu(d)
    kontrol("adim, nokta sirasi", [(x.adim, x.nokta) for x in t]
            == [(0, 0), (0, 1), (1, 0), (1, 1), (1, 2)])
    kontrol("taban dk = 0", t[0].dk_pcm == 0.0)
    kontrol("dk = (k - k0) 1e5", abs(t[1].dk_pcm - (-1000.0)) < 1e-6, repr(t[1].dk_pcm))
    kontrol("sigma = hypot", abs(t[1].dk_sapma_pcm - math.hypot(0.0004, 0.0003) * 1e5) < 1e-6)
    kontrol("basarisiz: k yok, hata var", t[4].k is None and t[4].dk_pcm is None and t[4].hata)
    kontrol("etiketsiz is atlanir", len(dal.dal_tablosu(d + [_durum_etiketsiz()])) == 5)
    metin = dal.csv_metni(t)
    ilk = metin.splitlines()[0]
    kontrol("CSV basligi sabit anahtarlar",
            ilk == "adim,zaman_gun,yanma_MWd_kg,T_yakit,k,k_sigma,dk_pcm,dk_sigma_pcm,hata", ilk)
    kontrol("CSV satir sayisi", len(metin.strip().splitlines()) == 6)
    kasit = [_durum("f", 0, 0, {}, None, "basarisiz", "=HYPERLINK(\"x\")")]
    kontrol("hata metni formul korumali", "'=HYPERLINK" in dal.csv_metni(dal.dal_tablosu(kasit)))


def _durum_etiketsiz():
    from cekirdek import kuyruk
    return kuyruk.IsDurumu(kimlik="z", ad="z", dizin="/tmp/z")


def test_gercek_dal_kosulari(gecici):
    print("\n[Y5-D6] gercek dal: taban dal tukenmeyle, adim-0 dallari taramayla tutarli")
    from cekirdek import dal, kuyruk, tarama, tukenme
    s = _spec()
    s["ayarlar"].update(parcacik=3000, cevrim=30, pasif=10, tohum=11)
    s["ayarlar"]["entropi_mesh"]["var"] = False
    s["tukenme"].update(entegrator="predictor", adim_gucu=False, adimlar=[5.0])
    tuk = os.path.join(gecici, "tukenme")
    h5, _b = tukenme.calistir(s, tuk, veri_kontrolu=False)
    r = tukenme.sonuc_oku(h5, s)
    a = dal.DalAyar((0, 1), (dal.degisken(s, "yakit_sicaklik", [900.0]),
                             dal.degisken(s, "bor_ppm", [500.0])), bicim="tek")
    with kuyruk.Kuyruk(en_fazla_paralel=1) as q:
        dal.kuyruga_ekle(s, h5, a, q, os.path.join(gecici, "dal"), is_parcacigi=6)
        q.baslat()
        q.bekle()
        t = dal.dal_tablosu(q.durumlar())
    kontrol("2 adim x (taban + 2 tek degiskenli nokta)", len(t) == 2 * 3, repr(len(t)))
    kontrol("hepsi basarili", all(x.hata is None and x.k for x in t),
            repr([x.hata for x in t]))
    def k_(adim, **kos):
        return [x for x in t if x.adim == adim and x.degerler == kos][0]
    for adim in (0, 1):
        taban = k_(adim)
        sg = math.hypot(taban.sapma, r["k_sapma"][adim])
        kontrol("adim %d: taban dal k = tukenme k (2 sigma)" % adim,
                abs(taban.k - r["k"][adim]) <= 2.0 * sg,
                "%.5f vs %.5f (2 sigma = %.5f)" % (taban.k, r["k"][adim], 2 * sg))
    sonuc, _n = tarama.calistir(s, "yakit_sicaklik", "uo2", [900.0], os.path.join(gecici, "t1"),
                                is_parcacigi=6)
    dd = k_(0, T_yakit=900.0)
    sg = math.hypot(dd.sapma, sonuc[0]["sapma"])
    kontrol("T_yakit=900: dal adim 0 = tek degiskenli tarama (2 sigma)",
            abs(dd.k - sonuc[0]["keff"]) <= 2.0 * sg,
            "%.5f vs %.5f (2 sigma = %.5f)" % (dd.k, sonuc[0]["keff"], 2 * sg))
    sonuc, _n = tarama.calistir(s, "bor_ppm", "su", [500.0], os.path.join(gecici, "t2"),
                                is_parcacigi=6)
    db = k_(0, C_bor=500.0)
    sg = math.hypot(db.sapma, sonuc[0]["sapma"])
    kontrol("C_bor=500: dal adim 0 = tek degiskenli tarama (2 sigma)",
            abs(db.k - sonuc[0]["keff"]) <= 2.0 * sg,
            "%.5f vs %.5f (2 sigma = %.5f)" % (db.k, sonuc[0]["keff"], 2 * sg))
    kontrol("bor k'yi dusurur (> 3 sigma)", db.dk_pcm < -3.0 * db.dk_sapma_pcm,
            "%.0f +- %.0f pcm" % (db.dk_pcm, db.dk_sapma_pcm))
    print("  ozet [adim, kosul, k, sigma, dk pcm]:")
    for x in t:
        print("   ", x.adim, x.degerler, "%.5f %.5f %s" % (x.k, x.sapma, x.dk_pcm))


HIZLI = [test_noktalar_ve_hatalar, test_kosul_taramayla_ayni, test_varsayilan_hedefler,
         test_bilesim_yazma, test_tablo_ve_csv]
YAVAS = [test_gercek_dal_kosulari]
VERI_GEREKEN = [test_bilesim_yazma] + YAVAS
ZINCIR_GEREKEN = [test_bilesim_yazma] + YAVAS
