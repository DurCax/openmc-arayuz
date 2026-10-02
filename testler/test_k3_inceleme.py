# -*- coding: utf-8 -*-
"""
 test_k3_inceleme.py  --  v3 K3 inceleme duzeltmeleri (python-reviewer + profesor)

   [IN1] E1: pin gucu TUM radyal yakit bolgelerinin toplami -- varsayilan
         hedefler her yakit bolgesini alir; ayni konumun bolgeleri toplanir ve
         "katman" notu yerine "bolge" notu duser; kesik yoklamasi en dis yakit
         yaricapiyla.
   [IN2] H1: onceki ciktinin temizligi -- yalniz kayitli dizinde, yalniz desene
         TAM uyan duzenli dosyalar; alt dizin, sembolik bag, ilgisiz dosya
         dokunulmaz; kayitsiz dizinde uyari; silme hatasi anlasilir hata.
   [IN3] H3: onbellek -- kilitli LRU; donen sonuc degismez (satirlar
         degistirilemez); es zamanli cagrilar ayni sonucu verir.
   [IN4] M4/M5: CSV/Excel hucre guvenligi (formul enjeksiyonu), utf-8-sig,
         dosya basliklari sabit anahtarlar (dilden bagimsiz).
   [IN5] M6: ceyrek katlama -- otelenmis kafes dolgusu, farkli sekilli demetler
         reddedilir; gercekten asimetrik veride uyari; D2 katli σ; D4 tepeden
         ayirt edilemeyen pinler.
   [IN6] M7: kosucu.guc_oku genel API; son adimin kaynak gucu.
   [IN7] H2: adim_gucleri iptal edilebilir.
"""

import copy
import csv
import io
import math
import os
import threading

from testler.ortak_test import KOK, ORNEK, kontrol

FIXTURE = os.path.join(KOK, "testler", "veri", "tukenme_guc_ornek")
KOSU = os.path.join(KOK, "testler", "veri", "kosu_ornek")


def _spec(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


# ---------------------------------------------------------------------------
# IN1 -- pin gucu = butun yakit bolgeleri
# ---------------------------------------------------------------------------
def test_varsayilan_hedefler_butun_yakit_bolgeleri():
    print("\n[IN1a] varsayilan hedefler: her cubugun butun yakit bolgeleri")
    from cekirdek import guc
    h = guc.varsayilan_hedefler(_spec("pwr_gd_tukenme"))
    kontrol("Gd pini 5 halka + yakit pini 1 bolge",
            sorted((x["cubuk"], x["bolge"]) for x in h)
            == [("gd_cubugu", i) for i in range(5)] + [("yakit_cubugu", 0)], "-> %r" % h)
    h17 = guc.varsayilan_hedefler(_spec("pwr_17x17"))
    kontrol("tek bolgeli pin: degismez (yakit_cubugu, 0)",
            h17 == [{"cubuk": "yakit_cubugu", "bolge": 0}], "-> %r" % h17)


def test_bolge_notu_katman_notundan_ayri():
    print("\n[IN1b] ayni turun bolgeleri toplanir: 'bolge' notu, 'katman' notu degil")
    from cekirdek import guc
    p = {"anahtarlar": [(0, 0), (1, 0)], "dilimler": [0, 0], "ortalar": [1.0, 2.0],
         "sapmalar": [0.1, 0.1], "kafesler": [object()], "eksenel_dilim": 1,
         "isimler": [], "oteleme": None}
    q = dict(p, ortalar=[0.5, 0.25])
    konumlar, birlesen, turler = guc._parcalari_birlestir([p, q], ["gd", "gd"])
    kontrol("bolgeler konum basina toplandi", konumlar[(0, 0)]["eksenel"][0][0] == 1.5
            and konumlar[(1, 0)]["eksenel"][0][0] == 2.25)
    notlar = guc._birlesim_notlari([p, q], ["gd", "gd"], birlesen)
    kontrol("bolge notu var, katman notu ve cok tur notu yok",
            any("bölge" in n for n in notlar) and not any("katman" in n for n in notlar)
            and not any("türlü" in n for n in notlar), "-> %r" % notlar)


def test_kesik_yoklamasi_dis_yaricap():
    print("\n[IN1c] kesik yoklamasi: hedef hucrenin evrenindeki en dis yakit yaricapi")
    import openmc
    from cekirdek import guc_faktor
    c1, c2 = openmc.ZCylinder(r=0.2), openmc.ZCylinder(r=0.4)
    m = openmc.Material()
    i = openmc.Cell(fill=m, region=-c1)
    d = openmc.Cell(fill=m, region=+c1 & -c2)
    dis = openmc.Cell(region=+c2)
    u = openmc.Universe(cells=[i, d, dis])
    geo = openmc.Geometry(openmc.Universe(cells=[openmc.Cell(fill=u)]))
    r = guc_faktor.dis_yakit_yaricaplari(geo, {i.id, d.id})
    kontrol("ic halka da dis halka da 0.4 cm", r == {i.id: 0.4, d.id: 0.4}, "-> %r" % r)


def test_gd_statik_kosu_korunum(gecici):
    print("\n[IN1d] Gd super hucre statik kosu: halkalar toplami = guc_toplam_ref")
    from cekirdek import guc, kosucu
    s = _spec("pwr_gd_tukenme")
    s["tukenme"]["var"] = False
    s["guc_dagilimi"].update({"var": True, "cubuklar": guc.varsayilan_hedefler(s)})
    s["guc_dagilimi"].pop("cubuk", None)
    s["guc_dagilimi"].pop("bolge", None)
    s["ayarlar"].update({"parcacik": 2000, "cevrim": 30, "pasif": 10})
    r = kosucu.calistir(s, gecici, is_parcacigi=4)
    sonuc = kosucu.sonuc_oku(r["statepoint"])
    g = sonuc["guc"]
    f = g["faktorler"]
    kontrol("korunum < 1e-6 (5 halka + yakit)", g["korunum"] < 1e-6, "-> %r" % g.get("korunum"))
    gd = [a for a, t in g["dagilim"]["cubuk_turleri"].items() if t == "gd_cubugu"]
    kontrol("tek Gd pini", len(gd) == 1, "-> %r" % gd)
    b = f["bagil"][gd[0]][0]
    print("    bilgi: Gd pini bagil guc %.3f, F_ΔH %.4f" % (b, f["F_dH"]))
    # olculdu (2000 x 30): butun halkalar 0.214; yalniz ic halka bunun ~1/5'i
    kontrol("Gd pini butun halkalarla: bagil > 0.12 (yalniz ic halka ~0.04)", b > 0.12)


# ---------------------------------------------------------------------------
# IN2 -- temizlik
# ---------------------------------------------------------------------------
def _dosya(yol):
    with open(yol, "w") as f:
        f.write("x")
    return yol


def test_temizlik_yalniz_kayitli_ve_tam_ad(gecici):
    print("\n[IN2a] temizlik: kayitli dizinde yalniz desene tam uyan duzenli dosyalar")
    from cekirdek import tukenme_temizlik as tt
    d = os.path.join(gecici, "k")
    os.makedirs(d)
    _dosya(os.path.join(d, tt.SPEC_KAYDI))
    silinecek = [_dosya(os.path.join(d, "openmc_simulation_n%d.h5" % i)) for i in (0, 1, 12)]
    sonuc_h5 = _dosya(os.path.join(d, tt.SONUC_DOSYASI))
    kalacak = [_dosya(os.path.join(d, ad)) for ad in
               ("openmc_simulation_n1.h5.bak", "xopenmc_simulation_n2.h5",
                "openmc_simulation_nA.h5", "notlar.txt")]
    os.makedirs(os.path.join(d, "openmc_simulation_n3.h5"))          # dizin
    disarida = _dosya(os.path.join(gecici, "kullanici.h5"))
    os.symlink(disarida, os.path.join(d, "openmc_simulation_n4.h5"))   # sembolik bag
    alt = os.path.join(d, "alt")
    os.makedirs(alt)
    alt_adim = _dosya(os.path.join(alt, "openmc_simulation_n0.h5"))
    s = tt.onceki_sonucu_temizle(d)
    kontrol("adim dosyalari ve sonuc silindi",
            all(not os.path.exists(y) for y in silinecek + [sonuc_h5])
            and sorted(s["silinen"]) == sorted(silinecek + [sonuc_h5]), "-> %r" % s)
    kontrol("ilgisiz dosyalar, dizin, alt dizin, sembolik bag ve hedefi duruyor",
            all(os.path.exists(y) for y in kalacak + [alt_adim, disarida])
            and os.path.isdir(os.path.join(d, "openmc_simulation_n3.h5"))
            and os.path.islink(os.path.join(d, "openmc_simulation_n4.h5")))
    kontrol("uyari yok", s["uyari"] is None)


def test_temizlik_kayitsiz_dizin(gecici):
    print("\n[IN2b] kayitsiz dizin: adim dosyalari silinmez, uyari")
    from cekirdek import tukenme_temizlik as tt
    adim = _dosya(os.path.join(gecici, "openmc_simulation_n0.h5"))
    s = tt.onceki_sonucu_temizle(gecici)
    kontrol("dokunulmadi ve uyari", os.path.exists(adim) and s["uyari"] and not s["silinen"],
            "-> %r" % s)


def test_temizlik_silme_hatasi(gecici, monkeypatch):
    print("\n[IN2c] silme hatasi: anlasilir TemizlikHatasi (OSError)")
    from cekirdek import tukenme_temizlik as tt
    _dosya(os.path.join(gecici, tt.SPEC_KAYDI))
    adim = _dosya(os.path.join(gecici, "openmc_simulation_n0.h5"))

    def izin_yok(yol):
        raise PermissionError(13, "izin yok", yol)

    monkeypatch.setattr(tt.os, "remove", izin_yok)
    try:
        tt.onceki_sonucu_temizle(gecici)
        hata = None
    except tt.TemizlikHatasi as e:
        hata = e
    kontrol("TemizlikHatasi, mesajda dosya", hata is not None and adim in str(hata)
            and isinstance(hata, OSError), "-> %r" % hata)


def test_calistir_temizligi_kullanir(gecici, monkeypatch):
    print("\n[IN2d] tukenme.calistir: kayitsiz dizinde adim dosyasi silinmez")
    import openmc.deplete
    from cekirdek import tukenme
    adim = _dosya(os.path.join(gecici, "openmc_simulation_n0.h5"))

    class Dur(Exception):
        pass

    monkeypatch.setattr(tukenme, "kapi", lambda spec, veri_kontrolu=True: [])
    monkeypatch.setattr(tukenme, "hazirla", lambda spec: (object(), {"zincir": {
        "yol": "z.xml", "verim_enerjisi": 0.0253}}))
    monkeypatch.setattr(openmc.deplete, "CoupledOperator",
                        lambda *a, **k: (_ for _ in ()).throw(Dur()))
    import json
    with open(os.path.join(FIXTURE, "tukenme_spec.json"), encoding="utf-8") as f:
        s = json.load(f)
    try:
        tukenme.calistir(s, gecici)
    except Dur:
        pass
    kontrol("kayitsiz dizindeki adim dosyasi duruyor", os.path.exists(adim))


# ---------------------------------------------------------------------------
# IN3 -- onbellek
# ---------------------------------------------------------------------------
def _fixture_spec():
    import json
    with open(os.path.join(FIXTURE, "tukenme_spec.json"), encoding="utf-8") as f:
        return json.load(f)


def test_onbellek_degismez_ve_kilitli():
    print("\n[IN3] onbellek: degismez sonuc, es zamanli cagri")
    from cekirdek import tukenme_guc
    tukenme_guc.onbellegi_bosalt()
    sonuclar = []

    def oku():
        sonuclar.append(tukenme_guc.adim_gucleri(FIXTURE, _fixture_spec()))

    isler = [threading.Thread(target=oku) for _i in range(3)]
    for i in isler:
        i.start()
    for i in isler:
        i.join()
    kontrol("uc cagri da 3 adim", all(len(s["adimlar"]) == 3 for s in sonuclar))
    s = sonuclar[0]
    r = s["adimlar"][0]["tablo"][0]
    try:
        r["bagil"] = 99.0
        yazildi = True
    except TypeError:
        yazildi = False
    try:
        s["adimlar"][0]["tablo"].append(None)
        eklendi = True
    except AttributeError:
        eklendi = False
    kontrol("satir ve tablo degistirilemez", not yazildi and not eklendi)
    from cekirdek import tukenme
    kontrol("tukenme sonuc kaynagi kilitli LRU",
            hasattr(tukenme, "_SONUC_KILIDI") and hasattr(tukenme._SONUC_KAYNAGI, "move_to_end"))


# ---------------------------------------------------------------------------
# IN4 -- disa aktarma guvenligi
# ---------------------------------------------------------------------------
def test_hucre_guvenli_ve_sabit_basliklar(gecici):
    print("\n[IN4] formul enjeksiyonu, utf-8-sig, sabit basliklar")
    from cekirdek import ceviri, guc_tablo
    for metin in ("=1+1", "+cmd", "-2", "@SUM(A1)", "\tx", "\rx"):
        kontrol("%r -> ' onekli" % metin, guc_tablo.hucre_guvenli(metin) == "'" + metin)
    kontrol("sayi ve normal metin degismez", guc_tablo.hucre_guvenli(-2.5) == -2.5
            and guc_tablo.hucre_guvenli("x = 1") == "x = 1")
    yol = os.path.join(gecici, "t.csv")
    guc_tablo.dosyaya_yaz(yol, [["a", "b"], ["=EVIL()", 1.5]])
    with open(yol, "rb") as f:
        ham = f.read()
    kontrol("utf-8-sig (BOM)", ham.startswith(b"\xef\xbb\xbf"))
    kontrol("formul hucresi onekli", b"'=EVIL()" in ham)
    once = ceviri.etkin_dil()
    try:
        ceviri.dil_ayarla("en")
        en = guc_tablo.basliklar([])
    finally:
        ceviri.dil_ayarla(once)
    kontrol("dosya basliklari dilden bagimsiz", en == guc_tablo.basliklar([])
            and "bagil" in en and "q_W_cm" in en, "-> %r" % en)


# ---------------------------------------------------------------------------
# IN5 -- ceyrek katlama denetimleri
# ---------------------------------------------------------------------------
def _kare(n, adim=1.0, evren=None):
    import openmc
    k = openmc.RectLattice()
    k.pitch = (adim, adim)
    k.lower_left = (-n * adim / 2.0, -n * adim / 2.0)
    u = evren or openmc.Universe(cells=[openmc.Cell()])
    k.universes = [[u] * n for _i in range(n)]
    return k


def _konum(v, s=0.001):
    return {"eksenel": [(v, s)], "toplam": (v, s)}


def _tek_dagilim(kafes, degerler, geometri=None):
    return {"konumlar": {a: _konum(v) for a, v in degerler.items()}, "eksenel_dilim": 1,
            "tam_kor": False, "kafes_turu": "kare", "kafesler": [kafes],
            "tum_kafesler": {kafes.id: kafes}, "kesik_cubuklar": [], "geometri": geometri}


def test_katlama_dolgu_otelemesi_reddedilir():
    print("\n[IN5a] kafesi dolduran hucre otelenmis: reddedilir")
    import openmc
    from cekirdek import guc, guc_tablo
    k = _kare(2)
    hucre = openmc.Cell(fill=k)
    hucre.translation = (0.3, 0.0, 0.0)
    geo = openmc.Geometry(openmc.Universe(cells=[hucre]))
    d = _tek_dagilim(k, {(i, j): 1.0 for i in range(2) for j in range(2)}, geo)
    katli, neden = guc_tablo.ceyrek_katla(guc_tablo.pin_tablosu(d, guc.tepe_faktorleri(d)), d)
    kontrol("otelenmis dolgu reddedildi", katli is None and neden, neden)


def test_katlama_farkli_sekilli_demetler():
    print("\n[IN5b] ayni duzeyde farkli sekilli demetler: reddedilir")
    import openmc
    from cekirdek import guc_tablo
    k2, k3 = _kare(2), _kare(3)
    u2 = openmc.Universe(cells=[openmc.Cell(fill=k2)])
    u3 = openmc.Universe(cells=[openmc.Cell(fill=k3)])
    kor = openmc.RectLattice()
    kor.pitch = (4.0, 4.0)
    kor.lower_left = (-6.0, -6.0)
    kor.universes = [[u3, u2, u3], [u2, u3, u2], [u3, u2, u3]]     # ayna simetrik
    geo = openmc.Geometry(openmc.Universe(cells=[openmc.Cell(fill=kor)]))
    d = {"tam_kor": True, "kafes_turleri": ["kare", "kare"], "kafesler": [kor, k2],
         "tum_kafesler": {x.id: x for x in (kor, k2, k3)}, "kesik_cubuklar": [],
         "geometri": geo}
    tamam, neden = guc_tablo.ceyrek_simetri([], d)
    kontrol("farkli sekil reddedildi", not tamam and neden, neden)


def test_katlama_asimetri_uyarisi_ve_sigma():
    print("\n[IN5c] gercek asimetri: uyari; katli σ en az uye sacilmasi/√m")
    from cekirdek import guc, guc_tablo
    k = _kare(2)
    d = _tek_dagilim(k, {(0, 0): 1.0, (1, 0): 1.3, (0, 1): 1.0, (1, 1): 1.0})
    t = guc_tablo.pin_tablosu(d, guc.tepe_faktorleri(d))
    katli, not_ = guc_tablo.ceyrek_katla(t, d)
    kontrol("katlandi (geometri simetrik), asimetri uyarisi", katli is not None
            and "asimetri" in (not_ or "").lower(), "-> %r" % not_)
    r = katli[0]
    b = [x["bagil"] for x in t]
    m = len(b)
    ort = sum(b) / m
    s_uye = math.sqrt(sum((x - ort) ** 2 for x in b) / (m - 1))
    kontrol("σ_katli = max(√Σσ²/m, s_uye/√m)", abs(r["sigma"] - s_uye / math.sqrt(m)) < 1e-12,
            "-> %r" % r["sigma"])
    kontrol("asimetri/σ orani satirda", r["asimetri_sigma"] > 3.0, "-> %r" % r["asimetri_sigma"])


def test_tepeden_ayirt_edilemez():
    print("\n[IN5d] D4: tepeden 2σ icindeki pinler isaretli")
    from cekirdek import guc, guc_tablo
    k = _kare(2)
    d = _tek_dagilim(k, {(0, 0): 1.000, (1, 0): 1.0005, (0, 1): 0.5, (1, 1): 0.5})
    t = guc_tablo.pin_tablosu(d, guc.tepe_faktorleri(d))
    yakin = sorted(r["anahtar"] for r in t if r["tepe_yakini"])
    kontrol("iki pin tepeden ayirt edilemez", yakin == [(0, 0), (1, 0)], "-> %r" % yakin)


# ---------------------------------------------------------------------------
# IN6 / IN7 -- genel okuma API'si, son adim, iptal
# ---------------------------------------------------------------------------
def test_guc_oku_genel_api():
    print("\n[IN6a] kosucu.guc_oku: (guc, hata)")
    import openmc
    from cekirdek import kosucu
    with openmc.StatePoint(os.path.join(KOSU, "statepoint.40.h5")) as sp:
        g, hata = kosucu.guc_oku(sp)
    kontrol("guc sozlugu, hata yok", hata is None and g["faktorler"]["F_dH"] > 1.0)


def test_son_adim_kaynak_gucu():
    print("\n[IN6b] son adim (son transport) kaynak gucu = son adimin gucu")
    from cekirdek import tukenme, tukenme_guc
    s = tukenme_guc.adim_gucleri(FIXTURE, _fixture_spec())
    r = tukenme._sonuc_kaynagi(os.path.join(FIXTURE, "depletion_results.h5"),
                               _fixture_spec())[0]
    oranlar = list(r.get_source_rates())
    kontrol("Results son nokta icin ayri oran saklamaz (N oran, N+1 zaman)",
            len(oranlar) == len(s["adimlar"]) - 1, "-> %r" % oranlar)
    kontrol("son adimin kaynak gucu son araliginki", s["adimlar"][-1]["kaynak_W"] == oranlar[-1])


def test_iptal():
    print("\n[IN7] adim_gucleri iptal edilebilir")
    from cekirdek import tukenme_guc
    tukenme_guc.onbellegi_bosalt()
    try:
        tukenme_guc.adim_gucleri(FIXTURE, _fixture_spec(), iptal=lambda: True)
        iptal = False
    except tukenme_guc.Iptal:
        iptal = True
    kontrol("Iptal yukseldi", iptal)
    s = tukenme_guc.adim_gucleri(FIXTURE, _fixture_spec())
    kontrol("iptal onbellege bozuk sonuc birakmadi", len(s["adimlar"]) == 3)


HIZLI = [test_varsayilan_hedefler_butun_yakit_bolgeleri, test_bolge_notu_katman_notundan_ayri,
         test_kesik_yoklamasi_dis_yaricap, test_temizlik_yalniz_kayitli_ve_tam_ad,
         test_temizlik_kayitsiz_dizin, test_temizlik_silme_hatasi,
         test_calistir_temizligi_kullanir, test_onbellek_degismez_ve_kilitli,
         test_hucre_guvenli_ve_sabit_basliklar, test_katlama_dolgu_otelemesi_reddedilir,
         test_katlama_farkli_sekilli_demetler, test_katlama_asimetri_uyarisi_ve_sigma,
         test_tepeden_ayirt_edilemez, test_guc_oku_genel_api, test_son_adim_kaynak_gucu,
         test_iptal]
YAVAS = [test_gd_statik_kosu_korunum]
