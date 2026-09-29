# -*- coding: utf-8 -*-
"""
test_guc_coklu.py -- cok turlu guc dagilimi semasi (guc_dagilimi.cubuklar).

Sema karari cekirdek/sema.py'de VARSAYILAN_GUC ustundeki "SEMA KARARI"
notundadir (Dalga 2 on-commit 2; uygulama Ajan 8b). GC1-GC4 sema, GC5-GC13
cok tally / normalizasyon / betik / arayuz (HIZLI, Monte Carlo yok),
GC14-GC15 Monte Carlo kabul (YAVAS).
Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import copy
import glob
import json
import os

from testler.ortak_test import kontrol, ORNEK


def _eski_bicimli(cubuk="yakit_cubugu", bolge=0):
    from cekirdek import sema
    ham = sema.yeni_spec("guc")
    ham["guc_dagilimi"] = {"var": True, "cubuk": cubuk, "bolge": bolge,
                           "skor": "kappa-fission"}
    return ham


def test_varsayilan_cubuklar_bos():
    print("\n[GC1] VARSAYILAN_GUC: cubuklar = [] ve eski alanlar yok")
    from cekirdek import sema
    g = sema.yeni_spec("x")["guc_dagilimi"]
    kontrol("cubuklar bos liste", g.get("cubuklar") == [])
    kontrol("eski cubuk/bolge alani yok", "cubuk" not in g and "bolge" not in g)


def test_eski_bicim_tek_ogeli_listeye():
    print("\n[GC2] eski cubuk/bolge okunur -> tek ogeli cubuklar listesi")
    from cekirdek import sema
    g = sema.tamamla(_eski_bicimli("yakit_cubugu", 1))["guc_dagilimi"]
    kontrol("tek oge", g.get("cubuklar") == [{"cubuk": "yakit_cubugu", "bolge": 1}])
    kontrol("eski alanlar kaydedilmez", "cubuk" not in g and "bolge" not in g)
    bos = sema.tamamla(_eski_bicimli(None))["guc_dagilimi"]
    kontrol("eski cubuk None -> []", bos.get("cubuklar") == [])


def test_yeni_bicim_kazanir():
    print("\n[GC3] hem eski hem yeni alan varsa 'cubuklar' kazanir; tamamla girdiyi degistirmez")
    from cekirdek import sema
    ham = _eski_bicimli("eski")
    ham["guc_dagilimi"]["cubuklar"] = [{"cubuk": "a", "bolge": 0}, {"cubuk": "b", "bolge": 0}]
    once = copy.deepcopy(ham)
    g = sema.tamamla(ham)["guc_dagilimi"]
    kontrol("yeni liste aynen", g.get("cubuklar") == once["guc_dagilimi"]["cubuklar"])
    kontrol("girdi degismedi", ham == once)


def test_ornekler_yeni_bicimde_yuklenir():
    print("\n[GC4] guc_dagilimi olan her ornek yeni bicimle yuklenir")
    from cekirdek import sema
    for yol in sorted(glob.glob(os.path.join(ORNEK, "*.json"))):
        with open(yol, encoding="utf-8") as f:
            ham = json.load(f)
        if "guc_dagilimi" not in ham:
            continue
        g = sema.yukle(yol)["guc_dagilimi"]
        eski = ham["guc_dagilimi"].get("cubuk")
        beklenen = ham["guc_dagilimi"].get("cubuklar") or (
            [{"cubuk": eski, "bolge": ham["guc_dagilimi"].get("bolge") or 0}] if eski else [])
        kontrol("%s: cubuklar" % os.path.basename(yol), g.get("cubuklar") == beklenen,
                "-> %s" % g.get("cubuklar"))


# ============================================================================
# COK TURLU GUC (Ajan 8b)
# ============================================================================
#
# Ornek model: 3x3 kare kor, 5x5 demetler (merkezde kilavuz boru), UC
# zenginlik ve UC ayri cubuk tanimi (yakit_a %2.0, yakit_b %3.1, yakit_c
# %4.5); kor haritasi ABA / BCB / ABA, su yansitici, yan sinir vakum.

ZENGINLIKLER = {"a": 2.0, "b": 3.1, "c": 4.5}
DEMET_N = 5
PIN_ADIMI = 1.26


def uc_zenginlik_kor(hedefler="tum", parcacik=3000, cevrim=50, pasif=20):
    """Uc zenginlikli 3x3 kare kor spec'i. hedefler: "tum" (uc tur) ya da
    cubuk adlari listesi."""
    from cekirdek import sema
    s = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    uo2 = sema.malzeme_bul(s, "uo2")
    yakit = sema.cubuk_bul(s, "yakit_cubugu")
    malzemeler = [m for m in s["malzemeler"] if m["ad"] != "uo2"]
    cubuklar = [sema.cubuk_bul(s, "kilavuz_boru")]
    demetler = []
    for k, z in ZENGINLIKLER.items():
        m = copy.deepcopy(uo2)
        m["ad"], m["gorunen_ad"] = "uo2_%s" % k, "UO2 %%%.1f" % z
        m["bilesim"][0]["zenginlik"] = z
        malzemeler.append(m)
        c = copy.deepcopy(yakit)
        c["ad"] = "yakit_%s" % k
        c["bolgeler"][0]["malzeme"] = m["ad"]
        cubuklar.append(c)
        demetler.append(sema.demet("d_%s" % k, PIN_ADIMI, [DEMET_N, DEMET_N],
                                   ["yyyyy", "yyyyy", "yykyy", "yyyyy", "yyyyy"],
                                   {"y": c["ad"], "k": "kilavuz_boru"}, "su"))
    s.update(malzemeler=malzemeler, cubuklar=cubuklar, demetler=demetler)
    s["kor"].update(tur="kare_kafes", demet=None, adim=PIN_ADIMI * DEMET_N, boyut=[3, 3],
                    harita=["ABA", "BCB", "ABA"],
                    anahtar={"A": "d_a", "B": "d_b", "C": "d_c"})
    s["kor"]["yansitici"] = {"var": True, "kalinlik": 10.0, "malzeme": "su"}
    s["kor"]["sinir"]["yan"] = "vacuum"
    adlar = ["yakit_a", "yakit_b", "yakit_c"] if hedefler == "tum" else list(hedefler)
    s["guc_dagilimi"] = dict(s["guc_dagilimi"], var=True, eksenel_dilim=1,
                             cubuklar=[{"cubuk": a, "bolge": 0} for a in adlar])
    s["guc_dagilimi"].pop("cubuk", None)
    s["guc_dagilimi"].pop("bolge", None)
    s["ayarlar"].update(parcacik=parcacik, cevrim=cevrim, pasif=pasif)
    s["ayarlar"]["kaynak"] = dict(s["ayarlar"]["kaynak"], tur="kutu")
    return s


def _guc_tallyleri(model):
    return [t for t in model.tallies if t.name == "guc_dagilimi"]


def _dc_hucresi(tal, model):
    """Distribcell filtresinin hucresi (bin hucre KIMLIGIDIR)."""
    import openmc
    cid = int(next(f for f in tal.filters if isinstance(f, openmc.DistribcellFilter)).bins[0])
    return model.geometry.get_all_cells()[cid]


def test_kurucu_tur_basina_tally():
    print("\n[GC5] kurucu: tur basina 'guc_dagilimi' tally'si, ortak ref ve adli hucreler")
    import openmc
    from cekirdek import kurucu
    s = uc_zenginlik_kor()
    model, bilgi = kurucu.kur(s)
    taller = _guc_tallyleri(model)
    kontrol("3 guc tally'si", len(taller) == 3, "-> %d" % len(taller))
    adlar = [_dc_hucresi(t, model).name for t in taller]
    kontrol("hucre adlari = tur adlari (liste sirasi)",
            adlar == ["yakit_a", "yakit_b", "yakit_c"], "-> %s" % adlar)
    kontrol("bilgi guc_hucreler 3, eksik yok",
            len(bilgi["guc_hucreler"]) == 3 and bilgi["guc_eksik"] == [])
    ref = next(t for t in model.tallies if t.name == "guc_toplam_ref")
    cf = next(f for f in ref.filters if isinstance(f, openmc.CellFilter))
    kontrol("ref CellFilter uc hedef hucre",
            sorted(int(getattr(b, "id", b)) for b in cf.bins)
            == sorted(_dc_hucresi(t, model).id for t in taller))
    kontrol("model toplam tally'si tek", sum(t.name == "guc_model_toplam"
                                              for t in model.tallies) == 1)


def test_tek_tur_eski_yeni_ayni_xml():
    print("\n[GC6] tek tur: eski tek alan ve yeni liste AYNI model XML'ini verir")
    from cekirdek import kurucu, sema
    yeni = sema.yukle(os.path.join(ORNEK, "pwr_3b.json"))
    eski = copy.deepcopy(yeni)
    eski["guc_dagilimi"].pop("cubuklar")
    eski["guc_dagilimi"].update(cubuk="yakit_cubugu", bolge=0)

    def xml(spec):
        import tempfile
        m, _b = kurucu.kur(spec)
        d = tempfile.mkdtemp(prefix="gc6_")
        m.export_to_model_xml(os.path.join(d, "model.xml"))
        with open(os.path.join(d, "model.xml"), encoding="utf-8") as f:
            return f.read()
    x_yeni, x_eski = xml(yeni), xml(eski)
    kontrol("XML ayni", x_yeni == x_eski)
    kontrol("tek turde hucreye ad yazilmaz", 'name="yakit_cubugu"' not in x_yeni)


def test_modelde_olmayan_tur_atlanir():
    print("\n[GC7] listede modelde olmayan tur: atlanir + uyari; hicbiri yoksa hata")
    from cekirdek import kurucu, sema, dogrula
    s = uc_zenginlik_kor()
    s["kor"]["harita"] = ["ABA", "BAB", "ABA"]          # d_c kullanilmiyor
    model, bilgi = kurucu.kur(s)
    kontrol("2 tally, eksik = ['yakit_c']",
            len(_guc_tallyleri(model)) == 2 and bilgi["guc_eksik"] == ["yakit_c"],
            "-> %s" % bilgi["guc_eksik"])
    b = [x for x in dogrula.tum_kontroller(s, veri_kontrolu=False) if x.yer == "guc dagilimi"]
    kontrol("dogrula: 'modelde yok' uyarisi, hata yok",
            any(x.seviye == "uyari" and "modelde yok" in x.mesaj for x in b)
            and not any(x.seviye == "hata" for x in b), "-> %r" % [(x.seviye, x.mesaj) for x in b])
    s["guc_dagilimi"]["cubuklar"] = [{"cubuk": "yakit_c", "bolge": 0}]
    try:
        kurucu.kur(s)
        durdu = False
    except ValueError as e:
        durdu = "modelde kullanılmıyor" in str(e)
    kontrol("tek hedef modelde yok -> ValueError (eskisi gibi)", durdu)
    s["guc_dagilimi"]["cubuklar"] = [{"cubuk": "yakit_a", "bolge": 0}] * 2
    model, _b = kurucu.kur(s)
    kontrol("ayni hedef iki kez -> tek tally", len(_guc_tallyleri(model)) == 1)
    kontrol("sema.guc_hedefleri girdiyi kopyalar",
            sema.guc_hedefleri(s["guc_dagilimi"])[0] is not s["guc_dagilimi"]["cubuklar"][0])


def test_dogrula_cok_tur_kapsam():
    print("\n[GC8] dogrula: butun turler hedefteyse 'yalniz kapsar' ve bos demet uyarisi yok")
    from cekirdek.dogrula import referans
    tum = [(b.seviye, b.mesaj) for b in referans.guc_dagilimi_kontrol(uc_zenginlik_kor())]
    kontrol("uc tur: kapsam uyarisi yok", not any("kapsar" in m for _s, m in tum), "-> %r" % tum)
    kontrol("uc tur: bos demet uyarisi yok", not any("içermeyen demetler" in m for _s, m in tum))
    tek = [(b.seviye, b.mesaj) for b in
           referans.guc_dagilimi_kontrol(uc_zenginlik_kor(["yakit_b"]))]
    kontrol("tek tur: 'yalnız ... kapsar' uyarisi ve bos demetler",
            any("F_ΔH yalnız" in m and "yakit_a" in m for _s, m in tek)
            and any("içermeyen demetler" in m for _s, m in tek), "-> %r" % tek)


def _betik_modeli(spec, dizin):
    import importlib.util
    from cekirdek import kod_uret
    os.makedirs(dizin, exist_ok=True)
    yol = os.path.join(dizin, "model.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kod_uret.uret(spec, "model.py"))
    sm = importlib.util.spec_from_file_location("gc_betik_%d" % id(spec), yol)
    mo = importlib.util.module_from_spec(sm)
    eski = os.getcwd()
    try:
        os.chdir(dizin)
        sm.loader.exec_module(mo)
    finally:
        os.chdir(eski)
    return mo.model


def _tally_ozeti(model):
    """Karsilastirma icin betik/kurucu bagimsiz tally ozeti."""
    import openmc
    ozet = []
    for t in model.tallies:
        if not t.name.startswith("guc_"):
            continue
        f_oz = []
        for f in t.filters:
            if isinstance(f, openmc.DistribcellFilter):
                h = _dc_hucresi(t, model)
                f_oz.append(("dc", h.name, h.fill.name))
            elif isinstance(f, openmc.MeshFilter):
                f_oz.append(("mesh", tuple(f.mesh.dimension), tuple(f.mesh.lower_left),
                             tuple(f.mesh.upper_right)))
            elif isinstance(f, openmc.CellFilter):
                f_oz.append(("hucre", len(f.bins)))
        ozet.append((t.name, tuple(t.scores), tuple(f_oz)))
    return ozet


def test_betik_cok_tur_yapisi(gecici=None):
    print("\n[GC9] kod_uret: cok turlu tally yapisi kurucu ile ayni (kosu yok)")
    import tempfile
    from cekirdek import kurucu
    for eksenel in (False, True):
        s = uc_zenginlik_kor()
        if eksenel:
            s["kor"]["yukseklik"] = 100.0
            s["kor"]["sinir"].update(alt="vacuum", ust="vacuum")
            s["guc_dagilimi"]["eksenel_dilim"] = 8
        m_k, _b = kurucu.kur(s)
        m_b = _betik_modeli(s, tempfile.mkdtemp(prefix="gc9_", dir=gecici))
        a, b = _tally_ozeti(m_k), _tally_ozeti(m_b)
        kontrol("%s: tally ozeti ayni" % ("3B" if eksenel else "2B"), a == b,
                "-> %s\n   %s" % (a, b))
        if eksenel:
            meshler = {id(f) for t in m_b.tallies if t.name == "guc_dagilimi"
                       for f in t.filters if f.__class__.__name__ == "MeshFilter"}
            kontrol("3B betik: mesh filtresi turler arasinda ortak", len(meshler) == 1)


def test_kaydet_yeni_bicim(gecici=None):
    print("\n[GC10] sema.kaydet: guc yalniz yeni bicimde; spec degismez")
    import tempfile
    from cekirdek import sema
    s = sema.yukle(os.path.join(ORNEK, "pwr_3b.json"))
    s["guc_dagilimi"].update(cubuk="yakit_cubugu", bolge=0)     # arayuzun eski yazimi
    once = copy.deepcopy(s)
    yol = os.path.join(tempfile.mkdtemp(prefix="gc10_", dir=gecici), "x.json")
    sema.kaydet(s, yol)
    with open(yol, encoding="utf-8") as f:
        ham = json.load(f)["guc_dagilimi"]
    kontrol("dosyada cubuk/bolge yok, cubuklar var",
            "cubuk" not in ham and "bolge" not in ham
            and ham["cubuklar"] == [{"cubuk": "yakit_cubugu", "bolge": 0}], "-> %s" % ham)
    kontrol("bellekteki spec degismedi", s == once)
    kontrol("yeniden yukleme ayni hedef",
            sema.guc_hedefleri(sema.yukle(yol)["guc_dagilimi"]) == [{"cubuk": "yakit_cubugu",
                                                                    "bolge": 0}])


# ---------------------------------------------------------------------------
# sentetik iki tally (dagilim_oku birlestirme)
# ---------------------------------------------------------------------------

def _iki_turlu_sp():
    """Tek demet 2x2 kafes: (0,0),(1,0) 'a' turu, (0,1),(1,1) 'b' turu."""
    from types import SimpleNamespace
    import openmc
    from testler.test_guc_kor import _sahte_sp, _kare_kafes
    kafes = _kare_kafes(9101, 2, 1.0)
    hucreler = {}
    taller = {}
    for i, (tur, konumlar, degerler) in enumerate(
            (("a", [(0, 0), (1, 0)], [1.0, 2.0]), ("b", [(0, 1), (1, 1)], [3.0, 6.0]))):
        hucre = openmc.Cell(name=tur)
        hucreler[hucre.id] = hucre
        satirlar = [{"duzeyler": [(9101, x, y)], "ort": v, "sap": 0.1}
                    for (x, y), v in zip(konumlar, degerler)]
        sp = _sahte_sp(satirlar, 1, [kafes])
        tal = sp.get_tally()
        tal.name = "guc_dagilimi"
        tal.filters = [openmc.DistribcellFilter(hucre.id)]
        taller[10 + i] = tal
    geo = sp.summary.geometry
    geo.get_all_cells = lambda: dict(hucreler)
    return SimpleNamespace(get_tally=lambda name=None: taller[10], tallies=taller,
                           summary=SimpleNamespace(geometry=geo))


def test_dagilim_birlestirme_sentetik():
    print("\n[GC11] dagilim_oku: iki tur tek haritada, normalizasyon TUM cubuklar")
    from cekirdek import guc
    d = guc.dagilim_oku(_iki_turlu_sp())
    kontrol("4 konum, turler ['a','b']", len(d["konumlar"]) == 4 and d["turler"] == ["a", "b"],
            "-> %s %s" % (sorted(d["konumlar"]), d["turler"]))
    kontrol("cubuk turleri konumdan", d["cubuk_turleri"] == {(0, 0): "a", (1, 0): "a",
                                                            (0, 1): "b", (1, 1): "b"})
    f = guc.tepe_faktorleri(d)
    ort = sum(v[0] for v in f["bagil"].values()) / len(f["bagil"])
    kontrol("bagil ortalama 1.000 (tum turler)", abs(ort - 1.0) < 1e-12, "-> %.15f" % ort)
    kontrol("F_dH = 6 / 3 = 2.0", abs(f["F_dH"] - 2.0) < 1e-12, "-> %s" % f["F_dH"])
    oz = f["tur_ozeti"] or {}
    kontrol("tur ozeti: a ort 0.5, b ort 1.5",
            abs(oz["a"]["ortalama"] - 0.5) < 1e-12 and abs(oz["b"]["ortalama"] - 1.5) < 1e-12
            and oz["b"]["tepe_cubuk"] == (1, 1), "-> %s" % oz)
    kontrol("not: cok turlu", any("Çok türlü" in n for n in d["notlar"]))
    y = " ".join(guc.yorumla(f))
    kontrol("yorum tur basina ozeti yazar", "a:" in y and "b:" in y, y[:300])


def test_varsayilan_hedefler_fisil_bolge():
    print("\n[GC12] varsayilan_hedefler: uygun her cubuk, ILK fisil bolgesiyle")
    from cekirdek import guc
    s = uc_zenginlik_kor(["yakit_a"])
    kontrol("uc tur, bolge 0", guc.varsayilan_hedefler(s)
            == [{"cubuk": "yakit_%s" % k, "bolge": 0} for k in "abc"])
    c = next(c for c in s["cubuklar"] if c["ad"] == "yakit_b")
    c["bolgeler"].insert(0, {"r": 0.07, "malzeme": "helyum"})     # pelet merkez deligi
    kontrol("merkez delikli cubukta yakit bolgesi 1",
            guc.varsayilan_hedefler(s)[1] == {"cubuk": "yakit_b", "bolge": 1})


# ---------------------------------------------------------------------------
# arayuz: hedef cubuk kutusu
# ---------------------------------------------------------------------------

def test_arayuz_tum_yakit_cubuklari():
    print("\n[GC13] Ayar sekmesi: 'Tüm yakıt çubukları' secimi listeyi kurar")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtWidgets
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from cekirdek import sema
    from arayuz.sekme_ayar import AyarSekmesi
    s = uc_zenginlik_kor()
    a = AyarSekmesi()
    a.spec_yukle(s)
    veriler = [a.guc_cubuk.itemData(i) for i in range(a.guc_cubuk.count())]
    kontrol("ogeler: Tum + uc tur", veriler == [sema.GUC_TUM, "yakit_a", "yakit_b", "yakit_c"],
            "-> %s" % veriler)
    kontrol("uc turlu dosya -> 'Tum' secili", a.guc_cubuk.currentData() == sema.GUC_TUM)
    once = copy.deepcopy(s)
    a._kaydet()
    kontrol("degisikliksiz kayit spec'i degistirmez", s == once,
            "-> %s" % s["guc_dagilimi"])
    a.guc_cubuk.setCurrentIndex(a.guc_cubuk.findData("yakit_b"))
    kontrol("tek tur secimi -> cubuklar tek oge",
            sema.guc_hedefleri(s["guc_dagilimi"]) == [{"cubuk": "yakit_b", "bolge": 0}]
            and s["guc_dagilimi"]["cubuklar"] == [{"cubuk": "yakit_b", "bolge": 0}],
            "-> %s" % s["guc_dagilimi"])
    a.guc_cubuk.setCurrentIndex(a.guc_cubuk.findData(sema.GUC_TUM))
    kontrol("Tum secimi -> uc tur, eski alan yok",
            s["guc_dagilimi"].get("cubuklar") == [{"cubuk": "yakit_%s" % k, "bolge": 0}
                                                  for k in "abc"]
            and "cubuk" not in s["guc_dagilimi"], "-> %s" % s["guc_dagilimi"])
    s2 = uc_zenginlik_kor(["yakit_a", "yakit_c"])
    a.spec_yukle(s2)
    kontrol("alt kume dosyadan -> 'Dosyadaki secim' ogesi secili",
            a.guc_cubuk.currentData() == sema.GUC_LISTE)
    once = copy.deepcopy(s2)
    a._kaydet()
    kontrol("dosyadaki alt kume kayitta korunur", s2["guc_dagilimi"]["cubuklar"]
            == once["guc_dagilimi"]["cubuklar"] and "cubuk" not in s2["guc_dagilimi"])
    uyg  # noqa: B018


# ============================================================================
# YAVAS -- Monte Carlo kabul
# ============================================================================

def _kos(model, dizin):
    import openmc
    from testler.ortak_test import ISLEM_PARCACIGI
    os.makedirs(dizin, exist_ok=True)
    eski = os.getcwd()
    try:
        os.chdir(dizin)
        return openmc.StatePoint(model.run(threads=ISLEM_PARCACIGI, output=False))
    finally:
        os.chdir(eski)


def _pin_mesh_tally(model, spec):
    """Bagimsiz referans: pin adimina hizali RegularMesh (15x15), kappa-fission.
    Kor kafesi merkezde: lower_left = -(3 x 5 x adim)/2."""
    import openmc
    n = 3 * DEMET_N
    yari = n * PIN_ADIMI / 2.0
    mesh = openmc.RegularMesh()
    mesh.dimension = [n, n]
    mesh.lower_left = (-yari, -yari)
    mesh.upper_right = (yari, yari)
    t = openmc.Tally(name="bagimsiz_pin_mesh")
    t.filters = [openmc.MeshFilter(mesh)]
    t.scores = ["kappa-fission"]
    model.tallies = openmc.Tallies(list(model.tallies) + [t])


def _mesh_cubuk_gucleri(sp):
    """{(gx, gy): deger} -- sifir olmayan (yakitli) pin bin'leri."""
    t = sp.get_tally(name="bagimsiz_pin_mesh")
    n = 3 * DEMET_N
    dizi = t.mean.reshape((n, n))       # OpenMC mesh sirasi: x en hizli -> [iy, ix]
    return {(ix, iy): float(dizi[iy, ix]) for iy in range(n) for ix in range(n)
            if dizi[iy, ix] > 0.0}


def _kor_konumu(anahtar):
    (dx, dy), (x, y) = anahtar
    return (dx * DEMET_N + x, dy * DEMET_N + y)


def test_uc_zenginlik_mc_fdh(gecici):
    """
    KABUL (plan, Ajan 8b): uc zenginlikli 3x3 kare korda cok tally F_dH,
    pin adimina hizali bagimsiz RegularMesh kappa-fission F_dH ile 2 sigma
    icinde (5 tohum); normalize cubuk guclerinin ortalamasi 1.000; toplam
    korunumu; en sicak cubuk ayni konum.
    """
    print("\n[GC14] 3x3 kor, uc zenginlik: cok tally F_dH vs pin-mesh F_dH (5 tohum)")
    import statistics as st
    from cekirdek import kurucu, guc
    f_cok, f_mesh, en_fark = [], [], 0.0
    for tohum in (1, 2, 3, 4, 5):
        s = uc_zenginlik_kor()
        s["ayarlar"]["tohum"] = tohum
        model, _b = kurucu.kur(s)
        _pin_mesh_tally(model, s)
        sp = _kos(model, os.path.join(gecici, "gc14_%d" % tohum))
        d = guc.dagilim_oku(sp)
        f = guc.tepe_faktorleri(d)
        mesh = _mesh_cubuk_gucleri(sp)
        ort_m = sum(mesh.values()) / len(mesh)
        f_cok.append(f["F_dH"])
        f_mesh.append(max(mesh.values()) / ort_m)
        bagil_ort = sum(v[0] for v in f["bagil"].values()) / len(f["bagil"])
        kontrol("tohum %d: 216 cubuk, bagil ortalama %.6f" % (tohum, bagil_ort),
                f["cubuk_sayisi"] == 216 and len(mesh) == 216 and abs(bagil_ort - 1) < 1e-12)
        ref = float(sp.get_tally(name="guc_toplam_ref").mean.sum())
        top = sum(k["toplam"][0] for k in d["konumlar"].values())
        kontrol("tohum %d: toplam korunumu %.1e" % (tohum, abs(top / ref - 1)),
                abs(top / ref - 1) < 1e-9)
        for a, v in f["bagil"].items():
            en_fark = max(en_fark, abs(v[0] - mesh[_kor_konumu(a)] / ort_m))
        kontrol("tohum %d: en sicak cubuk ayni konum" % tohum,
                _kor_konumu(f["sicak_cubuk"]) == max(mesh, key=mesh.get))
        tur = f["tur_ozeti"]
        kontrol("tohum %d: tur ortalamalari zenginlik sirasinda" % tohum,
                tur["yakit_a"]["ortalama"] < tur["yakit_b"]["ortalama"]
                < tur["yakit_c"]["ortalama"], "-> %s" % {k: round(v["ortalama"], 4)
                                                         for k, v in tur.items()})
    s_cok, s_mesh = st.stdev(f_cok), st.stdev(f_mesh)
    fark = abs(st.mean(f_cok) - st.mean(f_mesh))
    sigma = (s_cok ** 2 / 5 + s_mesh ** 2 / 5) ** 0.5
    print("  F_dH cok tally = %.5f +- %.5f ; pin mesh = %.5f +- %.5f (5 tohum, sacilma)"
          % (st.mean(f_cok), s_cok, st.mean(f_mesh), s_mesh))
    print("  |fark| = %.2e, 2 sigma = %.2e, en buyuk cubuk farki = %.2e" % (fark, 2 * sigma, en_fark))
    kontrol("F_dH 2 sigma icinde", fark <= 2 * sigma + 1e-12)
    kontrol("cubuk cubuk bagil guc ayni (< 1e-9)", en_fark < 1e-9)


def test_cok_tur_betik_esdegerligi(gecici):
    """Cok turlu spec: kurucu ve uretilen betik ayni k ve ayni F_dH."""
    print("\n[GC15] cok turlu betik esdegerligi (kurucu vs kod_uret, Monte Carlo)")
    from cekirdek import kurucu, guc
    s = uc_zenginlik_kor(parcacik=2000, cevrim=30, pasif=10)
    s["kor"]["yukseklik"] = 100.0
    s["kor"]["sinir"].update(alt="vacuum", ust="vacuum")
    s["guc_dagilimi"]["eksenel_dilim"] = 6
    m_k, _b = kurucu.kur(s)
    sp_k = _kos(m_k, os.path.join(gecici, "gc15_k"))
    m_b = _betik_modeli(s, os.path.join(gecici, "gc15_b"))
    sp_b = _kos(m_b, os.path.join(gecici, "gc15_b"))
    f_k = guc.tepe_faktorleri(guc.dagilim_oku(sp_k))
    f_b = guc.tepe_faktorleri(guc.dagilim_oku(sp_b))
    dk = abs(sp_k.keff.n - sp_b.keff.n)
    print("  k kurucu = %.8f, betik = %.8f (fark %.1e); F_dH %.10f / %.10f; F_q %.6f / %.6f"
          % (sp_k.keff.n, sp_b.keff.n, dk, f_k["F_dH"], f_b["F_dH"], f_k["F_q"], f_b["F_q"]))
    kontrol("ayni k (fark %.1e)" % dk, dk < 1e-10)
    kontrol("ayni F_dH", abs(f_k["F_dH"] - f_b["F_dH"]) < 1e-10)
    kontrol("ayni F_q", abs(f_k["F_q"] - f_b["F_q"]) < 1e-10)
    kontrol("ayni tur listesi", guc.dagilim_oku(sp_b)["turler"] == ["yakit_a", "yakit_b",
                                                                    "yakit_c"])


BEKLEYEN = []
HIZLI = [test_varsayilan_cubuklar_bos, test_eski_bicim_tek_ogeli_listeye,
         test_yeni_bicim_kazanir, test_ornekler_yeni_bicimde_yuklenir,
         test_kurucu_tur_basina_tally, test_tek_tur_eski_yeni_ayni_xml,
         test_modelde_olmayan_tur_atlanir, test_dogrula_cok_tur_kapsam,
         test_betik_cok_tur_yapisi, test_kaydet_yeni_bicim,
         test_dagilim_birlestirme_sentetik, test_varsayilan_hedefler_fisil_bolge,
         test_arayuz_tum_yakit_cubuklari]
YAVAS = [test_uc_zenginlik_mc_fdh, test_cok_tur_betik_esdegerligi]
