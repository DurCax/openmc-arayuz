# -*- coding: utf-8 -*-
"""
 test_gs_duzeltme.py  --  Dalga G+S inceleme duzeltmeleri (v2-gs-duzeltme).

 Her test bir inceleme bulgusunu kilitler (madde numarasi test basliginda).
 Sozlesme: testler/ortak_test.py.
"""

import copy

from testler import geometri_ortak as go
from testler.ortak_test import kontrol


def _sinir_hatalari(spec):
    from cekirdek import geometri
    return [b for b in geometri.yapisal_denetim(spec)
            if b.seviye == "hata" and "sinir" in b.yer]


def test_periyodik_es_etkin_bc():
    print("\n[GS1] dikdortgen sinir: eksik yuz 'yan'i miras alir; periyodik es etkin BC ile")
    s = go.duzenek_e_ceyrek()
    s["geometri"]["kok"]["sinir"] = {"yan": "periodic", "alt": "reflective",
                                     "ust": "reflective", "yuzler": {"-x": "reflective"}}
    kontrol("yan=periodic, -x reflective -> +x essiz periyodik HATA", _sinir_hatalari(s),
            "-> bulgu yok")
    t = copy.deepcopy(s)
    t["geometri"]["kok"]["sinir"]["yuzler"] = {"-x": "reflective", "+x": "vacuum"}
    kontrol("yan=periodic, x yuzleri acik, y yuzleri miras periyodik cift -> hata yok",
            not _sinir_hatalari(t), "-> %s" % _sinir_hatalari(t))
    u = copy.deepcopy(s)
    u["geometri"]["kok"]["sinir"] = {"yan": "reflective", "yuzler": {"+y": "periodic"}}
    kontrol("yan=reflective, yalniz +y periodic -> HATA", _sinir_hatalari(u))


def _tukenmeli(spec, ayir=False):
    spec["tukenme"] = dict(spec.get("tukenme") or {}, var=True, malzemeleri_ayir=ayir)
    return spec


def _sahte_stokastik(sonuc):
    """geometri.hacim.stokastik'i MC'siz sahtesiyle degistirir; eskiyi doner."""
    from cekirdek.geometri import hacim
    eski = hacim.stokastik
    hacim.stokastik = lambda spec, adlar, orneklem=0, dizin=None: {
        a: sonuc[a] for a in adlar if a in sonuc}
    return eski


def test_betik_kesik_yakit_hacmi():
    print("\n[GS2] betik: kesik yakitta kosucunun (stokastik) hacmi; hacim yoksa acik hata")
    from cekirdek import kod_uret
    from cekirdek.geometri import hacim
    spec = _tukenmeli(go.duzenek_a(yakit_blok=True))
    eski = _sahte_stokastik({"uo2_24": (1234.5, 1.0)})
    try:
        kod = kod_uret.uret(spec, "model.py")
    finally:
        hacim.stokastik = eski
    kontrol("betikte 'volume = None' yok", ".volume = None" not in kod)
    kontrol("betik kosucunun stokastik hacmini yazar", "uo2_24.volume = 1234.5 " in kod,
            "-> %s" % [s for s in kod.splitlines() if "uo2_24.volume" in s])
    eski = _sahte_stokastik({})
    try:
        kod_uret.uret(spec, "model.py")
        hata = None
    except ValueError as e:
        hata = str(e)
    finally:
        hacim.stokastik = eski
    kontrol("zorunlu yakitin hacmi yoksa uretim acik hatayla durur",
            hata is not None and "uo2_24" in hata, "-> %s" % hata)


def test_yavas_betik_kesik_hacim_kosucuyla_ayni(gecici):
    print("\n[GS2y] kesik yakitli agac modeli: betik calisir, hacimler kosucuyla ayni")
    import importlib.util
    import os
    from cekirdek import kod_uret, tukenme
    spec = _tukenmeli(go.duzenek_a(yakit_blok=True))
    model, bilgi = tukenme.hazirla(spec)
    kosucu = {m.name: m.volume for m in model.materials if m.depletable}
    yol = os.path.join(gecici, "model.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kod_uret.uret(spec, "model.py"))
    eski = os.getcwd()
    try:
        os.chdir(gecici)
        sm = importlib.util.spec_from_file_location("uretilen_gs2", yol)
        mod = importlib.util.module_from_spec(sm)
        sm.loader.exec_module(mod)
    finally:
        os.chdir(eski)
    betik = {m.name: m.volume for m in mod.model.materials if m.depletable}
    kontrol("stokastik yedek kullanildi", "uo2_24" in bilgi["stokastik"], "-> %s" % bilgi)
    kontrol("betik hacimleri = kosucu hacimleri", betik == kosucu,
            "-> betik %s kosucu %s" % (betik, kosucu))


def _belge(ad):
    import os
    from testler.ortak_test import KOK
    with open(os.path.join(KOK, "docs", ad), encoding="utf-8") as f:
        return f.read()


def test_k2_brown_atiflari():
    print("\n[GS3] K2: Brown 2009 kaynakcada; bolum/sayi birincil kaynakla uyumlu")
    import inspect
    from cekirdek.uygunluk_denetimi import kurallar_mc, profiller
    belge = _belge("STANDARTLAR.md")
    kaynakca = belge[belge.index("## Kaynakça"):]
    kontrol("STANDARTLAR.md kaynakcasinda LA-UR-09-03136 (URL ile)",
            "LA-UR-09-03136" in kaynakca and "mcnpx.lanl.gov" in kaynakca)
    e = profiller._A.esikler
    kontrol("1000: §III.C ('1000s of neutrons/cycle')", e["parcacik_asgari"].deger == 1000
            and "§III.C" in e["parcacik_asgari"].kaynak and "1000s" in e["parcacik_asgari"].kaynak)
    kontrol("5000: §V ('at least 5000')", e["parcacik_uretim"].deger == 5000
            and "§V" in e["parcacik_uretim"].kaynak and "5000" in e["parcacik_uretim"].kaynak)
    kaynak = inspect.getsource(kurallar_mc)
    kontrol("k-eff icin '2–5 kat' iddiasi yok (Brown bunu yerel tally'ler icin soyler)",
            "2–5 kat" not in kaynak and "Tablo 2" in kaynak)


def _db(kural, durum, seviye="bilgi"):
    from cekirdek.uygunluk_denetimi.kurallar import DenetimBulgusu
    return DenetimBulgusu(seviye, kural, "m", durum=durum, profil="A")


def test_panel_rozeti_degerlendirilemedi():
    print("\n[GS4] panel rozeti: hic kural degerlendirilmediyse 'Sorun yok' DEGIL")
    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from arayuz.uygunluk_paneli import UygunlukPaneli
    p = UygunlukPaneli()
    try:
        p.goster([_db("K1", "uygulanamadi"), _db("K2", "uygulanamadi"),
                  _db("K2", "uygulanamadi")], ("A",))
        kontrol("hicbiri degerlendirilmedi -> notr 'Değerlendirilemedi: 2 kural'",
                p.rozet.tur() == "notr" and p.rozet.text() == "Değerlendirilemedi: 2 kural",
                "-> %s %r" % (p.rozet.tur(), p.rozet.text()))
        p.goster([_db("K1", "karsilandi"), _db("K3", "uygulanamadi")], ("A",))
        kontrol("bir kismi -> notr, '1 kural değerlendirilemedi' notu",
                p.rozet.tur() == "notr" and "1 kural değerlendirilemedi" in p.rozet.text(),
                "-> %s %r" % (p.rozet.tur(), p.rozet.text()))
        p.goster([_db("K1", "karsilandi")], ("A",))
        kontrol("hepsi gecti -> basari", p.rozet.tur() == "basari", "-> %s" % p.rozet.tur())
        p.goster([_db("K1", "karsilanmadi", "hata"), _db("K3", "uygulanamadi")], ("A",))
        kontrol("hata onceliklidir", p.rozet.tur() == "hata")
    finally:
        p.deleteLater()


def test_stokastik_hacim_sigma_denetimi():
    print("\n[GS5] stokastik yedek hacim: bagil sigma esigi; asilirsa orneklem artar ya da HATA")
    from cekirdek import tukenme_hacim
    from cekirdek.geometri import hacim
    spec = _tukenmeli(go.duzenek_a(yakit_blok=True))
    tablo = {"uo2_24": {"hacim": None, "yontem": hacim.KESIN_DEGIL, "ayrinti": "kesik",
                        "zorunlu": True}}
    eski = hacim.stokastik
    cagri = []

    def sahte(sonuclar):
        def f(spec, adlar, orneklem=0, dizin=None):
            cagri.append(orneklem)
            return {a: sonuclar[min(len(cagri), len(sonuclar)) - 1] for a in adlar}
        return f
    try:
        hacim.stokastik = sahte([(1000.0, 10.0), (1000.0, 2.0)])     # %1 -> %0.2
        yeni, dusen = tukenme_hacim.stokastik_tamamla(spec, tablo, orneklem=1000)
        kontrol("esik asildi -> orneklem artirilip yeniden olculdu",
                len(cagri) == 2 and cagri[1] > cagri[0] and yeni["uo2_24"]["hacim"] == 1000.0
                and dusen == ["uo2_24"], "-> %s %s" % (cagri, yeni["uo2_24"]))
        cagri.clear()
        hacim.stokastik = sahte([(1000.0, 10.0)])                    # hep %1
        try:
            tukenme_hacim.stokastik_tamamla(spec, tablo, orneklem=1000)
            hata = None
        except ValueError as e:
            hata = str(e)
        kontrol("artirmaya ragmen esik asiliyor -> ValueError", hata and "σ" in hata,
                "-> %s" % hata)
        cagri.clear()
        hacim.stokastik = sahte([(0.0, 0.0)])
        yeni, dusen = tukenme_hacim.stokastik_tamamla(spec, tablo, orneklem=1000)
        kontrol("v = 0 -> nedeni ayrintida (sessiz KESIN_DEGIL degil)",
                not dusen and "sıfır" in yeni["uo2_24"]["ayrinti"], "-> %s" % yeni["uo2_24"])
        hacim.stokastik = lambda spec, adlar, orneklem=0, dizin=None: {}
        k = hacim.hesapla(spec, "uo2_24", orneklem=1000)
        kontrol("hesapla: malzeme olcum disi -> nedeni ayrintida",
                k.yontem == hacim.KESIN_DEGIL and "stokastik" in k.ayrinti, "-> %s" % k.ayrinti[-120:])
    finally:
        hacim.stokastik = eski


def test_stokastik_hacim_chdir_yok():
    print("\n[GS6] stokastik hacim surec genelinde os.chdir yapmaz (cwd= / model.xml yolu)")
    import os
    import tempfile
    import openmc
    from cekirdek.geometri import hacim
    dizin = tempfile.mkdtemp(prefix="gs6_")
    gelen = {}

    def sahte_hesap(threads=None, output=True, cwd=".", **kw):
        gelen["cwd"] = cwd
        gelen["xml"] = os.path.exists(os.path.join(dizin, "model.xml"))
        raise RuntimeError("sahte: hesap yapilmadi")

    def yasak(_yol):
        raise AssertionError("os.chdir cagrildi")
    eski = (os.chdir, openmc.calculate_volumes)
    os.chdir, openmc.calculate_volumes = yasak, sahte_hesap
    try:
        hacim.stokastik(go.duzenek_c(), ["b4c"], 1000, dizin)
        hata = None
    except (RuntimeError, AssertionError) as e:
        hata = e
    finally:
        os.chdir, openmc.calculate_volumes = eski
    kontrol("chdir yok; calculate_volumes(cwd=dizin); model.xml dizinde",
            isinstance(hata, RuntimeError) and gelen.get("cwd") == dizin and gelen.get("xml"),
            "-> %r %s" % (hata, gelen))


def _ia_malzemeler():
    import openmc
    yakit = openmc.Material(name="yakit")
    yakit.add_nuclide("U235", 0.03)
    yakit.add_nuclide("U238", 0.97)
    su = openmc.Material(name="su")
    su.add_nuclide("H1", 2.0)
    su.add_nuclide("O16", 1.0)
    b4c = openmc.Material(name="b4c")
    b4c.add_nuclide("B10", 4.0)
    b4c.add_nuclide("C12", 1.0)
    return yakit, su, b4c


def _ia_pin(ad, r, ic, dis):
    import openmc
    c = openmc.ZCylinder(r=r)
    return openmc.Universe(name=ad, cells=[openmc.Cell(fill=ic, region=-c),
                                           openmc.Cell(fill=dis, region=+c)])


def _ia_kafes(evrenler, P=1.26):
    import openmc
    n = len(evrenler)
    lat = openmc.RectLattice()
    lat.pitch, lat.lower_left = (P, P), (-P * n / 2, -P * n / 2)
    lat.universes = evrenler
    kutu = openmc.model.RectangularPrism(P * n, P * n, boundary_type="reflective")
    return openmc.Geometry(openmc.Universe(cells=[openmc.Cell(fill=lat, region=-kutu)]))


def _ia_cevir(geo, malzemeler):
    from cekirdek.geometri.ice_aktar import xml_den
    return xml_den(geo, {m.id: m.name for m in malzemeler})


def test_ice_aktar_ayni_adli_evrenler():
    print("\n[GS7a] ice aktarma: ayni adli FARKLI evrenler birlesmez; ayni icerik tekil")
    yakit, su, b4c = _ia_malzemeler()
    a, b = _ia_pin("pin", 0.40, yakit, su), _ia_pin("pin", 0.50, yakit, su)
    agac, notlar = _ia_cevir(_ia_kafes([[a, b], [b, a]]), (yakit, su, b4c))
    yar = {c["ad"]: c["bolgeler"][0]["r"] for c in (agac or {}).get("cubuklar", [])}
    kontrol("iki ayri cubuk (r 0.40 / 0.50), ad cakismaz",
            sorted(yar.values()) == [0.40, 0.50] and len(yar) == 2, "-> %s %s" % (yar, notlar))
    a2 = _ia_pin("pin", 0.40, yakit, su)
    agac, _n = _ia_cevir(_ia_kafes([[a, a2], [a2, a]]), (yakit, su, b4c))
    kontrol("ayni adli ayni icerikli iki evren -> tek cubuk",
            len((agac or {}).get("cubuklar", [])) == 1, "-> %s" % (agac or {}).get("cubuklar"))
    su_cubugu = _ia_pin("su_kanali", 0.5, su, su)
    agac, _n = _ia_cevir(_ia_kafes([[a, su_cubugu], [su_cubugu, a]]), (yakit, su, b4c))
    turler = {c["ad"]: c["tur"] for c in (agac or {}).get("cubuklar", [])}
    kontrol("cubuk turu semadaki 'silindirik' (yakit rolu malzemeden gelir; 'yakit' tur degil)",
            set(turler.values()) == {"silindirik"}, "-> %s" % turler)


def _ia_tambur(ters):
    import math
    import openmc
    yakit, su, b4c = _ia_malzemeler()
    dis, ic = openmc.ZCylinder(r=5.0), openmc.ZCylinder(r=4.0)
    yari = math.radians(60.0)
    p1 = openmc.Plane(a=math.sin(yari), b=math.cos(yari), c=0.0, d=0.0)     # -yari
    p2 = openmc.Plane(a=-math.sin(yari), b=math.cos(yari), c=0.0, d=0.0)    # +yari
    kama = (-p1 & +p2) if ters else (+p1 & -p2)
    emici = +ic & -dis & kama
    u = openmc.Universe(name="tambur", cells=[openmc.Cell(fill=b4c, region=emici),
                                              openmc.Cell(fill=su, region=-dis & ~emici),
                                              openmc.Cell(fill=su, region=+dis)])
    return u, (yakit, su, b4c)


def test_ice_aktar_tambur_yonu_harf_sinir():
    print("\n[GS7b] ice aktarma: tambur emici yonu noktasal; 62+ evren; periyodik karsit yuz")
    import openmc
    from cekirdek.geometri import ice_aktar_kap
    from cekirdek.geometri.ice_aktar import Desteklenmez, _Donusturucu
    for ters, beklenen in ((False, "kabul"), (True, "red")):
        u, mal = _ia_tambur(ters)
        d = _Donusturucu(openmc.Geometry(u), {m.id: m.name for m in mal})
        try:
            sonuc = d.tambur(u, list(u.cells.values()))
            durum = "kabul" if sonuc else "taninmadi"
        except Desteklenmez as e:
            durum, sonuc = "red", str(e)
        kontrol("emici %s -> %s" % ("-x (ters)" if ters else "+x", beklenen), durum == beklenen,
                "-> %s %s" % (durum, sonuc))
        if not ters:
            kontrol("emici_aci 120", abs(d.tamburlar[0]["emici_aci"] - 120.0) < 1e-6)
    d = _Donusturucu(openmc.Geometry(u), {m.id: m.name for m in mal})
    anahtar = {}
    try:
        for i in range(70):
            d._harita_harfi({"tur": "bilesen", "ad": "u%d" % i}, anahtar)
        hata = None
    except Desteklenmez as e:
        hata = e
    except StopIteration as e:
        hata = e
    kontrol("62'den cok farkli evren -> Desteklenmez (StopIteration degil)",
            isinstance(hata, Desteklenmez), "-> %r" % hata)
    x0 = openmc.XPlane(-5.0, boundary_type="periodic")
    x1 = openmc.XPlane(5.0, boundary_type="vacuum")
    y0 = openmc.YPlane(-5.0, boundary_type="periodic")
    y1 = openmc.YPlane(5.0, boundary_type="vacuum")
    x0.periodic_surface = y0
    h = [openmc.Cell(region=+x0 & -x1 & +y0 & -y1)]
    try:
        ice_aktar_kap._sinir(h)
        hata = None
    except Desteklenmez as e:
        hata = e
    kontrol("periyodik es karsit yuz degil (x <-> y donel) -> Desteklenmez",
            isinstance(hata, Desteklenmez), "-> %r" % hata)
    x1b = openmc.XPlane(5.0, boundary_type="periodic")
    y0b = openmc.YPlane(-5.0, boundary_type="vacuum")
    x0b = openmc.XPlane(-5.0, boundary_type="periodic")
    x0b.periodic_surface = x1b
    s = ice_aktar_kap._sinir([openmc.Cell(region=+x0b & -x1b & +y0b & -y1)])
    kontrol("karsit yuz esi (-x <-> +x) kabul", s.get("yuzler", {}).get("+x") == "periodic",
            "-> %s" % s)


def test_arayuz_sessiz_yedek_yok():
    print("\n[GS8] arayuz: kesik/cizim hesaplanamazsa 'hesaplanamadı' (bos sonuc degil) + warning")
    import logging
    import os
    from PySide6 import QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from cekirdek import geometri, sema
    from testler.ortak_test import ORNEK
    from arayuz.geometri import cizim, cizim_xz, sablonlar
    from arayuz.geometri.editor import GelismisEditor
    spec = sablonlar.uret(sema.yukle(os.path.join(ORNEK, "pwr_ceyrek_kor.json")), "kare_altigen")
    kayitlar = []

    class _Tut(logging.Handler):
        def emit(self, r):
            kayitlar.append(r)
    tut = _Tut(level=logging.WARNING)
    logging.getLogger().addHandler(tut)
    eski_k, eski_m = geometri.kesik_konumlar, geometri.model

    def bozuk(*_a, **_k):
        raise RuntimeError("sahte hata")
    e = GelismisEditor()
    try:
        geometri.kesik_konumlar = bozuk
        e.yukle(spec)
        kontrol("editor: 'Kesik konum yok' DEGIL, 'hesaplanamadı'",
                "hesaplanamadı" in e.kesik_etiketi.text(), "-> %s" % e.kesik_etiketi.text())
        f = e.formlar["kafes"]
        f._kesikleri_isaretle(spec["geometri"]["kok"]["ic"], f.altigen)
        kontrol("kafes formu: kesik notu 'hesaplanamadı' ve gorunur",
                "hesaplanamadı" in f.kesik_notu.text(), "-> %r" % f.kesik_notu.text())
        geometri.kesik_konumlar = eski_k
        geometri.model = bozuk
        hatalar = []
        cizim.xy_ogeleri(spec, hatalar=hatalar)
        hatalar_xz = []
        cizim_xz.xz_ogeleri(spec, hatalar=hatalar_xz)
        kontrol("cizim/cizim_xz hatayi cagirana bildirir", hatalar and hatalar_xz,
                "-> %s %s" % (hatalar, hatalar_xz))
        e.kesit.tazele()
        kontrol("kesit tuvali hata metnini tasir (2B mesaji degil)",
                "hesaplanamadı" in (e.kesit.tuval.hata or ""), "-> %r" % e.kesit.tuval.hata)
    finally:
        geometri.kesik_konumlar, geometri.model = eski_k, eski_m
        logging.getLogger().removeHandler(tut)
        e.close()
        e.deleteLater()
    kontrol("hatalar warning duzeyinde gunluge yazildi",
            sum(1 for r in kayitlar if "sahte hata" in str(r.exc_info or r.getMessage())) >= 3,
            "-> %d kayit" % len(kayitlar))


def test_cli_siki_cikis_kodu():
    print("\n[GS9] uygunluk CLI --siki: degerlendirilemeyen kural -> cikis 3")
    import contextlib
    import io
    import os
    from cekirdek import giris, rapor_uygunluk
    from testler.ortak_test import KOK
    kontrol("cikis_kodu(siki): uygulanamadi -> 3",
            rapor_uygunluk.cikis_kodu([_db("K1", "uygulanamadi")], siki=True) == 3
            and rapor_uygunluk.cikis_kodu([_db("K1", "uygulanamadi")]) == 0)
    kontrol("hata her zaman 1 (siki da)",
            rapor_uygunluk.cikis_kodu([_db("K3", "karsilanmadi", "hata"),
                                       _db("K1", "uygulanamadi")], siki=True) == 1)
    fixture = os.path.join(KOK, "testler", "veri", "kosu_ornek")
    cikti = io.StringIO()
    with contextlib.redirect_stdout(cikti), contextlib.redirect_stderr(io.StringIO()):
        kod = giris.kosu(["uygunluk", fixture, "--profil", "A", "--siki"])
        kod0 = giris.kosu(["uygunluk", fixture, "--profil", "A"])
        yardim = giris.kosu(["uygunluk", "--yardim"])
    kontrol("CLI: fixture (σ hedefi yok -> uygulanamadi) --siki ile 3, siz 0",
            kod == 3 and kod0 == 0 and yardim == 0 and "--siki" in cikti.getvalue(),
            "-> %r %r" % (kod, kod0))


def test_k7_sigma_ve_dil():
    print("\n[GS10] K7: sigma yok/<=0 -> uygulanamadi; dil 'işaret beklentisi' (GDC yargisi degil)")
    import os
    from cekirdek.uygunluk_denetimi.denetle import denetle
    from testler.ortak_test import KOK
    fixture = os.path.join(KOK, "testler", "veri", "kosu_ornek")
    for s in (None, 0.0, -1.0):
        kats = {"egim": -5.0, "birim": "pcm/K"} if s is None else \
            {"egim": -5.0, "egim_sapma": s, "birim": "pcm/K"}
        b = denetle(None, fixture, ("C",), kor={"katsayilar": {"yakit_sicaklik": kats}})
        dop = [x for x in b if "Doppler" in x.mesaj]
        kontrol("Doppler σ=%r -> uygulanamadi (anlamli sayilmaz)" % s,
                dop and dop[0].durum == "uygulanamadi", "-> %s" % [(x.durum, x.mesaj) for x in dop])
    b = denetle(None, fixture, ("C",), kor={"katsayilar": {
        "guc": {"egim": 5.0, "egim_sapma": 1.0, "birim": "pcm/%"}}})
    guc = [x for x in b if "güç katsayısı" in x.mesaj]
    metin = " ".join((x.mesaj or "") + " " + (x.oneri or "") for x in guc)
    kontrol("pozitif guc: 'çelişiyor', 'GDC 11 çerçevesini karşılamıyor' YOK",
            "çelişiyor" in metin and "karşılamıyor" not in metin, "-> %s" % metin)
    b = denetle(None, fixture, ("C",), kor={"katsayilar": {
        "guc": {"egim": -5.0, "egim_sapma": 1.0, "birim": "pcm/%"}}})
    guc = [x for x in b if "güç katsayısı" in x.mesaj]
    kontrol("negatif guc: 'işaret beklentisiyle tutarlı (net geri besleme yargısı değildir)'",
            guc and "tutarlı" in guc[0].mesaj and "yargısı değildir" in guc[0].mesaj,
            "-> %s" % [x.mesaj for x in guc])


def test_rapor_eki_ve_panel_dili():
    print("\n[GS11] rapor eki/panel: 'kontrol listesi — sertifika değildir', 'Kontrolü geçen'")
    from cekirdek.rapor_sablon import uygunluk_eki
    from arayuz import uygunluk_paneli
    ek = {"profiller": [("A", "A")], "gruplar": {"karsilandi": [], "karsilanmadi": []},
          "ozet": {"durum": {"karsilandi": 1, "karsilanmadi": 0, "uygulanamadi": 0, "bilgi": 0}},
          "cerceve": "c", "usl_notu": "", "hata": ""}
    metin = uygunluk_eki.html(ek)
    kontrol("baslik", "Standart ve iyi uygulama kontrol listesi — sertifika değildir" in metin)
    kontrol("'Kontrolü geçen', 'Karşılanan' yok", "Kontrolü geçen" in metin
            and "Karşılan" not in metin and "karşılan" not in metin)
    adlar = " ".join(uygunluk_paneli._DURUM_ADLARI.values())
    kontrol("panel durum adlari 'kontrolü geçti'", "kontrolü geçti" in adlar
            and "karşılan" not in adlar, "-> %s" % adlar)


def _k5(metin=None, dizin=None):
    import os
    from cekirdek.uygunluk_denetimi.denetle import denetle
    from testler.ortak_test import KOK
    dizin = dizin or os.path.join(KOK, "testler", "veri", "kosu_ornek")
    return [b for b in denetle(None, dizin, ("D",), rapor_metni=metin)
            if b.kural.startswith("K5")]


def test_k5_bolum_parantez_dosya():
    print("\n[GS12] K5: pcm tanimi ayni bolumde (ya da belge basinda); 1.00038(25); rapor.html")
    import os
    import shutil
    import tempfile

    def pcm_sorunu(metin):
        return any("pcm" in b.mesaj for b in _k5(metin) if b.durum == "karsilanmadi")
    kontrol("tanim baska bolumde (ekte) -> K5-pcm", pcm_sorunu(
        "<h1>R</h1><p>x</p><h2>Sonuç</h2><p>Δk 120 pcm</p><h2>Ek</h2><p>pcm = Δk × 10⁵</p>"))
    kontrol("tanim belge basinda (gosterim notu) -> temiz", not pcm_sorunu(
        "<h1>R</h1><p>pcm = Δρ × 10⁵</p><h2>Sonuç</h2><p>120 pcm</p>"))
    kontrol("tanim ayni bolumde -> temiz", not pcm_sorunu(
        "<h1>R</h1><h2>Sonuç</h2><p>120 pcm (pcm = Δk × 10⁵)</p>"))
    etiketsiz = [b for b in _k5("k = 1.00038(25)") if b.durum == "karsilanmadi"]
    kontrol("parantez bicimi cift sayilir: etiket yoksa uyari",
            any("1σ" in b.mesaj for b in etiketsiz), "-> %s" % [b.mesaj for b in etiketsiz])
    uc = [b for b in _k5("k = 1.00038(253) (1σ standart belirsizlik)")
          if b.durum == "karsilanmadi"]
    kontrol("parantezde 3 anlamli rakam -> uyari", any("anlamlı" in b.mesaj for b in uc),
            "-> %s" % [b.mesaj for b in uc])
    kontrol("1.00038(25) (1σ) temiz",
            not [b for b in _k5("k = 1.00038(25) (1σ standart belirsizlik)")
                 if b.durum == "karsilanmadi"])
    kok = tempfile.mkdtemp(prefix="gs12_")
    try:
        with open(os.path.join(kok, "a_eski.html"), "w", encoding="utf-8") as f:
            f.write("<p>120 pcm</p>")
        with open(os.path.join(kok, "rapor.html"), "w", encoding="utf-8") as f:
            f.write("<p>k = 1.0 ± 0.1 (1σ)</p>")
        b = _k5(dizin=kok)
        kontrol("bilinen ad rapor.html secilir (alfabetik ilk degil)",
                b and all(x.durum == "karsilandi" for x in b) and "rapor.html" in b[0].mesaj,
                "-> %s" % [(x.durum, x.mesaj) for x in b])
        os.remove(os.path.join(kok, "rapor.html"))
        with open(os.path.join(kok, "b.html"), "w", encoding="utf-8") as f:
            f.write("<p>x</p>")
        b = _k5(dizin=kok)
        kontrol("rapor.html yok, birden cok .html -> uygulanamadi (belirsiz)",
                b and b[0].durum == "uygulanamadi", "-> %s" % [(x.durum, x.mesaj) for x in b])
    finally:
        shutil.rmtree(kok, True)


def test_tambur_degeri_pcm_tanimi():
    print("\n[GS13] tambur degeri: pcm = x 1e5, dk ve drho = (k2-k1)/(k1 k2) birlikte")
    from testler import test_geometri_fizik as gf
    dk, dr = gf._deger_pcm(1.04533, 1.03251)
    kontrol("dk = 1282 pcm, drho = 1188 pcm", round(dk) == 1282 and round(dr) == 1188,
            "-> %s %s" % (dk, dr))
    belge = _belge("ORNEKLER.md")
    kontrol("ORNEKLER.md pcm tanimini yazar (Δk × 10⁵ ve Δρ = (k₂ − k₁)/(k₁k₂))",
            "Δk × 10⁵" in belge and "(k₂ − k₁)/(k₁k₂)" in belge)


def test_dusuk_oncelikli():
    print("\n[GS-LOW] kayip iletileri (0.16), nesil/cevrim dilimi, profil tekil, gezinti, R=0 psi")
    import os
    import shutil
    import tempfile
    from cekirdek.uygunluk_denetimi import ayristir, kurallar_mc
    from cekirdek.uygunluk_denetimi.denetle import denetle
    from testler.ortak_test import KOK
    kok = tempfile.mkdtemp(prefix="gslow_")
    try:
        with open(os.path.join(kok, "kosu.log"), "w", encoding="utf-8") as f:
            f.write(" WARNING: Particle 5 left lattice 3, but it has no outer definition.\n"
                    " WARNING: Could not find the cell containing particle 7\n"
                    " WARNING: Couldn't find particle after hitting periodic boundary on "
                    "surface 4.\n"
                    " WARNING: Particle 9 had a negative distance to a lattice boundary.\n")
        o = ayristir.cikti_ozeti(kok)
        kontrol("OpenMC 0.16 kayip parcacik iletileri (libopenmc dizgileri) sayilir",
                o.kayip_parcacik == 4 and not o.uyarilar, "-> %d %s" % (o.kayip_parcacik, o.uyarilar))
    finally:
        shutil.rmtree(kok, True)
    # generations_per_batch = 3: pasif 2 cevrim = 6 nesil; pasif nesiller 2.0 (gecis)
    import random
    r = random.Random(3)
    g, pasif, cevrim = 3, 2, 40
    nesil = [2.0] * (pasif * g) + [1.0 + r.gauss(0, 1e-3) for _ in range((cevrim - pasif) * g)]
    kosu = ayristir.KosuVerisi("sp", "eigenvalue", 1.0, 1e-4, 1000, cevrim, pasif,
                               k_nesil=tuple(nesil), nesil_basina=g)
    aktif = kurallar_mc.aktif_cevrim_k(kosu)
    kontrol("aktif cevrim k: %d cevrim ortalamasi, pasif nesiller disarida" % (cevrim - pasif),
            len(aktif) == cevrim - pasif and max(aktif) < 1.01, "-> %d, max %.3f"
            % (len(aktif), max(aktif)))
    fixture = os.path.join(KOK, "testler", "veri", "kosu_ornek")
    kontrol("ayni profil iki kez -> tek denetim",
            len(denetle(None, fixture, ("A", "A"))) == len(denetle(None, fixture, ("A",))))
    from cekirdek.geometri import yerlesim
    try:
        yerlesim._psi({"tur": "merkez", "merkez": [0.0, 0.0]}, 0.0, 0.0, 0.0, 30.0, {})
        hata = None
    except ValueError as e:
        hata = str(e)
    kontrol("R = 0 halka: ornek bakis merkezinde -> ValueError (yon tanimsiz)",
            hata and "çakışıyor" in hata, "-> %s" % hata)
    from cekirdek import geometri
    from cekirdek.dogrula import agac
    eski = geometri.gez

    def bozuk(_m):
        raise AttributeError("sahte gezinti hatasi")
    geometri.gez = bozuk
    try:
        b = agac.agac_kontrol(go.duzenek_c())
        sonuc = [x.mesaj for x in b if x.seviye == "hata"]
    except AttributeError as e:
        sonuc = "yakalanmadi: %s" % e
    finally:
        geometri.gez = eski
    kontrol("dogrula/agac: beklenmeyen gezinti hatasi bulguya doner (cokme yok)",
            isinstance(sonuc, list) and any("gezilemedi" in m for m in sonuc), "-> %s" % sonuc)


TAMBUR_R = 6.0  # altigen_tambur_halkasi tambur yaricapi (cm)


def _harita(spec, noktalar):
    from cekirdek import geometri
    from testler import geometri_iz as gi
    kok, _kutu, mat_adi, _k = gi.kok_kur(geometri.kur, spec)
    sayac = gi.OrnekSayaci()
    return [gi.nokta_izi(kok, p, mat_adi, sayac)[0] for p in noktalar]


def test_tek_tambur_yonu_asil_modelle_ayni():
    print("\n[GS14] liste modunda 0 derece tek tambur = halka modu 0 derece (malzeme haritasi)")
    import math
    import random
    from araclar import tambur_etkilesim as te
    t = te.taban()
    r = random.Random(14)
    merkez = te.tambur_konumlari(t)[0]
    yakin = []
    while len(yakin) < 1500:
        x, y = r.uniform(-TAMBUR_R, TAMBUR_R), r.uniform(-TAMBUR_R, TAMBUR_R)
        if math.hypot(x, y) < TAMBUR_R - 0.05:
            yakin.append((merkez[0] + x, merkez[1] + y, r.uniform(-39.9, 39.9)))
    genel = []
    while len(genel) < 1500:
        p = (r.uniform(-48.6, 48.6), r.uniform(-48.6, 48.6), r.uniform(-39.9, 39.9))
        if math.hypot(p[0] - merkez[0], p[1] - merkez[1]) > TAMBUR_R + 0.05 and all(
                abs(p[0] * math.cos(a) + p[1] * math.sin(a)) < 48.69
                for a in (math.radians(30 + 60 * i) for i in range(6))):
            genel.append(p)
    ic, dis = te.hepsi(t, te.ICERI), te.hepsi(t, te.DISARI)
    tek = te.secili(t, (0,))
    kontrol("tambur 0 diski: tek(0) = halka modu 0 derece",
            _harita(tek, yakin) == _harita(ic, yakin))
    kontrol("tambur 0 disinda: tek(0) = halka modu 180 derece",
            _harita(tek, genel) == _harita(dis, genel))
    kontrol("duyarlilik: disk icinde 0 ve 180 farkli (emici yayi doner)",
            _harita(ic, yakin) != _harita(dis, yakin))
    hepsi_ic = te.secili(t, tuple(range(6)))
    kontrol("liste modunda 6 tambur iceri = halka modu iceri",
            _harita(hepsi_ic, yakin + genel) == _harita(ic, yakin + genel))


HIZLI = [test_dusuk_oncelikli, test_periyodik_es_etkin_bc, test_betik_kesik_yakit_hacmi, test_k2_brown_atiflari,
         test_panel_rozeti_degerlendirilemedi, test_tek_tambur_yonu_asil_modelle_ayni,
         test_stokastik_hacim_sigma_denetimi, test_stokastik_hacim_chdir_yok,
         test_ice_aktar_ayni_adli_evrenler, test_ice_aktar_tambur_yonu_harf_sinir,
         test_arayuz_sessiz_yedek_yok, test_cli_siki_cikis_kodu, test_k7_sigma_ve_dil,
         test_rapor_eki_ve_panel_dili, test_k5_bolum_parantez_dosya,
         test_tambur_degeri_pcm_tanimi]
YAVAS = [test_yavas_betik_kesik_hacim_kosucuyla_ayni]
