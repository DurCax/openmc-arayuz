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


TAMBUR_R = 6.0           # altigen_tambur_halkasi tambur yaricapi (cm)


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


HIZLI = [test_periyodik_es_etkin_bc, test_betik_kesik_yakit_hacmi, test_k2_brown_atiflari,
         test_panel_rozeti_degerlendirilemedi, test_tek_tambur_yonu_asil_modelle_ayni,
         test_stokastik_hacim_sigma_denetimi]
YAVAS = [test_yavas_betik_kesik_hacim_kosucuyla_ayni]
