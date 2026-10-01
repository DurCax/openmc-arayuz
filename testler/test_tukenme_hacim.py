# -*- coding: utf-8 -*-
"""
 test_tukenme_hacim.py  --  D1-B: tukenme hacimleri, ornek hacimleri, kapi, zehirler

 Kapsam
   * bulgu 2: haritaya / demet anahtarina DOGRUDAN konan yakit malzemesinin
     hacmi (altigen hucre (sqrt3/2) P^2 h, kare P^2 h); kesin degilse
     "stokastik hesap gerekli" (sessizce yanlis sayi YOK)
   * bulgu 4: cubuk cubuk yanmada (diff_burnable_mats) ornek basina hacim:
     esit olmayan eksenel katmanlar ve ayni yakiti farkli yaricapla kullanan
     iki cubuk turu
   * bulgu 3: tukenme.calistir ve terminal dogrulama kapisindan gecer; hatali
     spec onceki sonucu SILMEZ
   * bulgu 6: kati malzemedeki bor (Pyrex) yanabilir, borlu su yanmaz
   * YAVAS: analitik hacim = OpenMC stokastik hacim (3 sigma), Python ornek
     sirasi = C++ distribcell sirasi (openmc.lib), kisa cubuk cubuk tukenme

 Sozlesme: testler/ortak_test.py. Hizli testler nukleer veri, openmc.lib ve
 cizim KULLANMAZ (hacim ve ornek hesabi saf Python; Geometry yollari).
"""

import copy
import io
import math
import os
import shutil
import tempfile
import warnings
from contextlib import redirect_stdout

from testler.ortak_test import kontrol, ORNEK, ISLEM_PARCACIGI
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik
from testler import test_altigen_kor as T

warnings.filterwarnings("ignore")

SQ3 = math.sqrt(3.0)
H = 100.0
PIN = math.pi * T.R_YAKIT ** 2


# ============================================================================
# model yardimcilari
# ============================================================================

def _altigen_merkez_uo2(yukseklik=H):
    """7 demetli altigen kor, merkez konumda dogrudan 'uo2'."""
    s = T._kor_spec()
    s["kor"]["yukseklik"] = yukseklik
    s["kor"]["anahtar"]["U"] = "uo2"
    s["kor"]["harita"][1] = "U"
    return s


def _kare_demet(sema, ad="kd", adim=1.26, harita=("yyy", "yuy", "yyy"), anahtar=None):
    return sema.demet(ad, adim, [3, 3], list(harita),
                      anahtar or {"y": "yakit_cubugu", "u": "uo2"}, "su")


def _kare_kor(harita=("AA", "AU"), demet_harita=("yyy", "yyy", "yyy")):
    """2x2 kare kor (demet adimi 3 x 1.26), U = dogrudan 'uo2'."""
    from cekirdek import sema
    s = T._tek_demet_spec()
    s["demetler"] = [_kare_demet(sema, harita=demet_harita)]
    s["kor"].update(tur="kare_kafes", demet=None, adim=3 * 1.26, boyut=[2, 2],
                    harita=list(harita), anahtar={"A": "kd", "U": "uo2"})
    s["kor"]["yukseklik"] = H
    sema.kor_alanlarini_ayikla(s["kor"])
    return s


def _hacim(s, ad="uo2"):
    from cekirdek import tukenme
    return tukenme.hacimler(s).get(ad) or {}


# ============================================================================
# bulgu 2: dogrudan malzeme yerlesimi
# ============================================================================

def test_dogrudan_malzeme_hacmi():
    print("\n[TH1] TUKENME HACMI: haritaya/anahtara dogrudan konan yakit sayilir")
    from cekirdek import tukenme
    P = T.ZARF
    # (a) altigen kor merkezinde uo2: 6 x 19 pin + bir altigen hucre
    v = _hacim(_altigen_merkez_uo2())
    beklenen = 6 * 19 * PIN * H + SQ3 / 2 * P * P * H
    kontrol("altigen kor merkez uo2: %.6g cm3 (beklenen %.6g = 5336 + 2806)"
            % (v.get("hacim") or 0, beklenen),
            v.get("hacim") and abs(v["hacim"] - beklenen) / beklenen < 1e-12
            and v["yontem"] == "analitik", "-> %s" % v)
    kontrol("altigen kor: yakit ornek sayisi 114 pin + 1 hucre",
            tukenme.yakit_ornek_sayisi(_altigen_merkez_uo2()) == 115)
    # (b) kare kor, bir kor konumu dogrudan uo2
    Pk = 3 * 1.26
    v = _hacim(_kare_kor())
    beklenen = 3 * 9 * PIN * H + Pk * Pk * H
    kontrol("kare kor konumu uo2: %.6g (beklenen %.6g)" % (v.get("hacim") or 0, beklenen),
            v.get("hacim") and abs(v["hacim"] - beklenen) / beklenen < 1e-12, "-> %s" % v)
    # (c) kare demet anahtarinda dogrudan uo2 (merkez pin konumu)
    v = _hacim(_kare_kor(harita=("AA", "AA"), demet_harita=("yyy", "yuy", "yyy")))
    beklenen = 4 * (8 * PIN + 1.26 ** 2) * H
    kontrol("kare demet konumu uo2 (4 demet): %.6g (beklenen %.6g)"
            % (v.get("hacim") or 0, beklenen),
            v.get("hacim") and abs(v["hacim"] - beklenen) / beklenen < 1e-12, "-> %s" % v)
    # (d) altigen demetin IC halkasinda uo2 (merkez pin): tam altigen hucre
    s = T._kor_spec()
    s["kor"]["yukseklik"] = H
    d = s["demetler"][0]
    d["anahtar"]["u"] = "uo2"
    d["harita"][-1] = "u"
    v = _hacim(s)
    beklenen = 7 * (18 * PIN + SQ3 / 2 * T.PIN_ADIM ** 2) * H
    kontrol("altigen demet merkez pin konumu uo2: %.6g (beklenen %.6g)"
            % (v.get("hacim") or 0, beklenen),
            v.get("hacim") and abs(v["hacim"] - beklenen) / beklenen < 1e-12, "-> %s" % v)
    # (e) altigen demetin DIS halkasi: hucre zarfla kirpilir -> kesin degil
    d["harita"][-1] = "y"
    d["harita"][0] = "u" + d["harita"][0][1:]
    v = _hacim(s)
    kontrol("altigen demet dis halka uo2: hacim yok, stokastik hesap gerekli",
            v.get("hacim") is None and v.get("yontem") == "stokastik hesap gerekli",
            "-> %s" % v)
    # (f) demetin dis dolgusu / kilifi yakit: kesin degil
    s = T._kor_spec(kilif=True)
    s["demetler"][0]["kilif"]["malzeme"] = "uo2"
    v = _hacim(s)
    kontrol("kilif malzemesi uo2: stokastik hesap gerekli",
            v.get("hacim") is None and v.get("yontem") == "stokastik hesap gerekli",
            "-> %s" % v)
    # (g) altigen kor katmanini dogrudan dolduran yakit (homojen ortu)
    from cekirdek import sema
    s = T._kor_spec()
    s["kor"]["eksenel"] = {"var": True, "bolgeler": [
        sema.eksenel_bolge("ortu", 20.0, "uo2"), sema.eksenel_bolge("aktif", 50.0, None)]}
    v = _hacim(s)
    beklenen = 7 * SQ3 / 2 * T.ZARF ** 2 * 20.0 + 7 * 19 * PIN * 50.0
    kontrol("altigen kor katman dolgusu uo2: %.6g (beklenen %.6g)"
            % (v.get("hacim") or 0, beklenen),
            v.get("hacim") and abs(v["hacim"] - beklenen) / beklenen < 1e-12, "-> %s" % v)


def test_tukenme_dogrulama_dogrudan():
    """Kesin olmayan dogrudan yerlesim dogrulamada hata olur (kosu engellenir)."""
    print("\n[TH2] TUKENME DOGRULAMA: kesin olmayan hacim -> HATA")
    from cekirdek import dogrula
    s = T._kor_spec(kilif=True)
    s["demetler"][0]["kilif"]["malzeme"] = "uo2"
    s["tukenme"]["var"] = True
    h = [b for b in dogrula.tukenme_kontrol(s, veri_kontrolu=False)
         if b.seviye == "hata" and b.yer == "tukenme/uo2"]
    kontrol("tukenme/uo2 hacim hatasi", bool(h), "-> %s" % [b.mesaj for b in h])


# ============================================================================
# bulgu 4: cubuk cubuk yanmada ornek basina hacim
# ============================================================================

def _iki_cubuklu_kare(eksenel=True):
    """2x2 kare kor, demette iki cubuk turu (r 0.386 ve 0.30, ikisi de uo2);
    eksenel katmanlar 50 + 20 cm (esit degil)."""
    from cekirdek import sema
    s = _kare_kor(harita=("AA", "AA"), demet_harita=("yzy", "zyz", "yzy"))
    s["cubuklar"].append(sema.cubuk("ince", [sema.bolge(0.30, "uo2"),
                                            sema.bolge(T.R_ZARF, "zr"),
                                            sema.bolge(None, "su")]))
    s["demetler"][0]["anahtar"]["z"] = "ince"
    if eksenel:
        s["kor"]["eksenel"] = {"var": True, "bolgeler": [
            sema.eksenel_bolge("alt", 50.0, None), sema.eksenel_bolge("ust", 20.0, None)]}
    s["tukenme"].update(var=True, malzemeleri_ayir=True)
    return s


def _iki_cubuklu_altigen():
    from cekirdek import sema
    s = T._kor_spec(kilif=True)
    s["cubuklar"].append(sema.cubuk("ince", [sema.bolge(0.30, "uo2"),
                                            sema.bolge(T.R_ZARF, "zr"),
                                            sema.bolge(None, "su")]))
    d = s["demetler"][0]
    d["anahtar"]["z"] = "ince"
    d["harita"][0] = "zy" * 6
    s["kor"]["eksenel"] = {"var": True, "bolgeler": [
        sema.eksenel_bolge("alt", 50.0, None), sema.eksenel_bolge("ust", 20.0, None)]}
    s["tukenme"].update(var=True, malzemeleri_ayir=True)
    return s


def _ic_ice_katmanli_kare():
    """2x2 kare kor (kafes icinde kafes), iki demet turu; esit olmayan uc
    katman (40 / 10 / 20 cm) ve ortadaki katmanda demetler yer degistirir
    (katmana ozel anahtar). Toplam yukseklik 70 cm (z = +-35)."""
    from cekirdek import sema
    s = _iki_cubuklu_kare(eksenel=False)
    s["demetler"].append(_kare_demet(sema, ad="kd2", harita=("zzz", "zyz", "zzz"),
                                     anahtar={"y": "yakit_cubugu", "z": "ince"}))
    s["kor"]["anahtar"]["B"] = "kd2"
    s["kor"]["harita"] = ["AB", "BA"]
    s["kor"]["eksenel"] = {"var": True, "bolgeler": [
        sema.eksenel_bolge("alt", 40.0, None),
        sema.eksenel_bolge("orta", 10.0, None, anahtar={"A": "kd2", "B": "kd"}),
        sema.eksenel_bolge("ust", 20.0, None)]}
    return s


def _ayrilmis(spec):
    """(modelin uo2 klonlarinin hacimleri, analitik toplam)."""
    from cekirdek import kurucu, tukenme, tukenme_hacim
    model, kb = kurucu.kur(spec)
    hv = tukenme.hacimler(spec)
    m = kb["malzemeler"]["uo2"]
    m.depletable = True
    m.volume = hv["uo2"]["hacim"]
    tukenme_hacim.ornekleri_ayir(model, spec, hv, {"uo2": m})
    klonlar = [x for x in model.geometry.get_all_materials().values()
               if x.depletable and x.name == m.name]
    return [x.volume for x in klonlar], hv["uo2"]["hacim"]


@gereksinim("R-TK-02")
def test_ornek_hacimleri():
    print("\n[TH3] CUBUK CUBUK YANMA: ornek basina hacim (katman + iki yaricap)")
    for ad, s, n_kalin, n_ince in (
            ("kare 2x2", _iki_cubuklu_kare(), 4 * 5, 4 * 4),
            ("altigen 7 kilifli", _iki_cubuklu_altigen(), 7 * 13, 7 * 6)):
        hacimler, toplam = _ayrilmis(s)
        beklenen = sorted([PIN * h for h in (50.0, 20.0) for _ in range(n_kalin)]
                          + [math.pi * 0.30 ** 2 * h for h in (50.0, 20.0)
                             for _ in range(n_ince)])
        kontrol("%s: %d ornek (beklenen %d)" % (ad, len(hacimler), len(beklenen)),
                len(hacimler) == len(beklenen))
        uyusan = len(hacimler) == len(beklenen) and all(
            abs(a - b) < 1e-9 * b for a, b in zip(sorted(hacimler), beklenen))
        kontrol("%s: her ornegin hacmi = pi r^2 x kendi katman yuksekligi" % ad, uyusan,
                "-> %s" % sorted(set(round(v, 6) for v in hacimler)))
        kontrol("%s: ornek toplami = analitik toplam" % ad,
                abs(sum(hacimler) - toplam) < 1e-9 * toplam)
    # OpenMC'nin 'divide equally' yontemi ne verirdi (kanit): tek deger
    s = _iki_cubuklu_kare()
    hacimler, toplam = _ayrilmis(s)
    esit = toplam / len(hacimler)
    kontrol("esit bolme bu modelde yanlis olurdu (%.4g cm3 tek deger; gercek %.4g..%.4g)"
            % (esit, min(hacimler), max(hacimler)), max(hacimler) / min(hacimler) > 3)


def test_ornek_hacimleri_ic_ice_katmanli():
    print("\n[TH3b] CUBUK CUBUK YANMA: ic ice kafes + 3 esit olmayan katman + "
          "katmana ozel demet")
    hacimler, toplam = _ayrilmis(_ic_ice_katmanli_kare())
    # katman basina 12 kalin (2x5 + 2x1) ve 24 ince (2x4 + 2x8) cubuk
    beklenen = sorted([PIN * h for h in (40.0, 10.0, 20.0) for _ in range(12)]
                      + [math.pi * 0.30 ** 2 * h for h in (40.0, 10.0, 20.0)
                         for _ in range(24)])
    kontrol("%d ornek (beklenen %d)" % (len(hacimler), len(beklenen)),
            len(hacimler) == len(beklenen))
    kontrol("her ornek = pi r^2 x kendi katmani", len(hacimler) == len(beklenen) and all(
        abs(a - b) < 1e-9 * b for a, b in zip(sorted(hacimler), beklenen)))
    kontrol("ornek toplami = analitik", abs(sum(hacimler) - toplam) < 1e-9 * toplam)


def test_ornek_hacimleri_2b_ve_tek_ornek():
    print("\n[TH4] CUBUK CUBUK YANMA: 2B model ve tek ornekli malzeme")
    from cekirdek import kurucu, tukenme, tukenme_hacim
    s = _iki_cubuklu_kare(eksenel=False)
    s["kor"]["yukseklik"] = None
    hacimler, toplam = _ayrilmis(s)
    kontrol("2B: 1 cm yukseklik, 36 ornek, toplam tutuyor",
            len(hacimler) == 36 and abs(sum(hacimler) - toplam) < 1e-9 * toplam
            and abs(max(hacimler) - PIN) < 1e-12)
    # tek ornek: pin hucre -> klon yok, hacim aynen kalir
    from cekirdek import sema
    p = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    model, kb = kurucu.kur(p)
    hv = tukenme.hacimler(p)
    m = kb["malzemeler"]["uo2"]
    m.depletable, m.volume = True, hv["uo2"]["hacim"]
    n = tukenme_hacim.ornekleri_ayir(model, p, hv, {"uo2": m})
    kontrol("pin hucre: ayrilacak ornek yok", n == 0 and m.volume == hv["uo2"]["hacim"])


# ============================================================================
# bulgu 6: yanabilir zehirler
# ============================================================================

def _pyrex(sema):
    return sema.malzeme("pyrex", [sema.bilesen("Si", 0.26), sema.bilesen("O", 0.64),
                                  sema.bilesen("B", 0.08), sema.bilesen("Na", 0.02)],
                        2.23)


def _borlu_su(sema, ppm=1300.0):
    b = ppm * 1e-6 * 18.0 / 10.8          # kutle ppm -> atom orani (yaklasik)
    return sema.malzeme("borlu_su", [sema.bilesen("H", 2.0), sema.bilesen("O", 1.0),
                                     sema.bilesen("B", b)], 0.74, sab=["c_H_in_H2O"])


def test_yanabilir_bor():
    print("\n[TH5] YANABILIR ZEHIR: kati bor (Pyrex) yanar, borlu su yanmaz")
    from cekirdek import sema, tukenme
    s = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    once = tukenme.hacimler(s)
    kontrol("pwr_tukenme yanabilir listesi degismedi",
            tukenme.yanabilir_adlar(s) == ["uo2"], "-> %s" % tukenme.yanabilir_adlar(s))
    s["malzemeler"] += [_pyrex(sema), _borlu_su(sema)]
    adlar = tukenme.yanabilir_adlar(s)
    kontrol("Pyrex (Si-O-B, rol %s) yanabilir" % sorted(_roller(s, "pyrex")), "pyrex" in adlar,
            "-> %s" % adlar)
    kontrol("1300 ppm borlu su (rol %s) yanabilir DEGIL" % sorted(_roller(s, "borlu_su")),
            "borlu_su" not in adlar)
    kontrol("pwr_tukenme uo2 hacmi aynen", tukenme.hacimler(s)["uo2"] == once["uo2"])
    # B10 nuklid olarak da sayilir
    t = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    t["malzemeler"].append(sema.malzeme("b4c10", [sema.bilesen("B10", 4.0, tur="nuklid"),
                                                  sema.bilesen("C", 1.0)], 2.5))
    kontrol("B10 nuklidli B4C yanabilir", "b4c10" in tukenme.yanabilir_adlar(t))


def _roller(s, ad):
    from cekirdek import sema, uygunluk
    return uygunluk.tek_malzeme_rolleri(sema.malzeme_bul(s, ad))


def _kontrol_spec(daldirma, katmanli=False):
    from cekirdek import sema
    s = sema.yukle(os.path.join(ORNEK, "pwr_kontrol.json"))
    s["tukenme"]["var"] = True
    sema.cubuk_bul(s, "kontrol_cubugu")["daldirma"] = daldirma
    if katmanli:
        h = sema.kor_yuksekligi(s["kor"])
        s["kor"]["eksenel"] = {"var": True, "bolgeler": [
            sema.eksenel_bolge("alt", h / 2.0, None), sema.eksenel_bolge("ust", h / 2.0, None)]}
    return s


def test_hacimsiz_zehir():
    """
    Kontrol cubugu emicisi (B4C): katmansiz 3B modelde hacim ANALITIK
    (tukenme_hacim.kontrol_emici_uzunlugu: daldirma x yukseklik) ve tukenmeye
    katilir; tamamen cekili cubukta emici geometride yok (uyari da yok).
    Katmanli modelde emici katman sinirlarini asabilir: hacimsiz zehir, UYARI.
    """
    print("\n[TH6] YANABILIR ZEHIR: kontrol cubugu B4C -- analitik / cekili / katmanli")
    import math
    from cekirdek import dogrula, sema, tukenme, tukenme_hacim

    def uyarilar(s):
        return [x for x in dogrula.tukenme_kontrol(s, veri_kontrolu=False)
                if x.yer == "tukenme/b4c"]

    s = _kontrol_spec(50.0)
    c = sema.cubuk_bul(s, "kontrol_cubugu")
    em, _iz = tukenme_hacim.kontrol_emici_uzunlugu(s, c)
    d = sema.demet_bul(s, s["kor"]["demet"])
    adet = sum(r.count(h) for r in d["harita"] for h, ad in d["anahtar"].items()
               if ad == "kontrol_cubugu")
    beklenen = math.pi * c["bolgeler"][0]["r"] ** 2 * em * adet
    hv = tukenme.hacimler(s)
    kontrol("daldirma %%50: b4c analitik hacim %.6g cm3 (%d cubuk)" % (beklenen, adet),
            "b4c" in hv and hv["b4c"]["yontem"] == "analitik"
            and abs(hv["b4c"]["hacim"] - beklenen) < 1e-9 * beklenen, "-> %s" % hv.get("b4c"))
    kontrol("daldirma %50: hacimsiz zehir yok, dogrulama uyarisi yok",
            "b4c" not in tukenme.hacimsiz_zehirler(s) and not uyarilar(s))

    s0 = _kontrol_spec(0.0)
    kontrol("daldirma %0 (cekili): b4c ne hacimlerde ne hacimsiz zehirlerde, uyari yok",
            "b4c" not in tukenme.hacimler(s0) and "b4c" not in tukenme.hacimsiz_zehirler(s0)
            and not uyarilar(s0), "-> %s" % tukenme._hacim_tablosu(s0).get("b4c"))

    sk = _kontrol_spec(50.0, katmanli=True)
    kontrol("katmanli model: b4c hacimler listesinde yok (kesin hacim yok)",
            "b4c" not in tukenme.hacimler(sk))
    z = tukenme.hacimsiz_zehirler(sk)
    kontrol("katmanli model: b4c hacimsiz zehir: %s" % z.get("b4c"), "b4c" in z)
    b = uyarilar(sk)
    kontrol("dogrulama: b4c UYARI (hata degil)",
            b and all(x.seviye == "uyari" for x in b), "-> %s" % [(x.seviye, x.mesaj) for x in b])


# ============================================================================
# bulgu 3: dogrulama kapisi (calistir, terminal)
# ============================================================================

def _onceki_kosu(dizin):
    os.makedirs(dizin, exist_ok=True)
    with open(os.path.join(dizin, "depletion_results.h5"), "wb") as f:
        f.write(b"ONCEKI")
    with open(os.path.join(dizin, "tukenme_spec.json"), "w", encoding="utf-8") as f:
        f.write('{"onceki": true}')


def _onceki_duruyor(dizin):
    with open(os.path.join(dizin, "depletion_results.h5"), "rb") as f:
        h5 = f.read() == b"ONCEKI"
    with open(os.path.join(dizin, "tukenme_spec.json"), encoding="utf-8") as f:
        kayit = f.read() == '{"onceki": true}'
    return h5 and kayit


def _hatali_tukenme():
    from cekirdek import sema
    s = sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json"))
    s["tukenme"]["guc_yogunlugu"] = 0.0          # dogrula: hata
    return s


def test_calistir_kapisi():
    print("\n[TH7] TUKENME KAPISI: hatali spec onceki sonucu silmez")
    from cekirdek import dogrula, tukenme
    dizin = tempfile.mkdtemp(prefix="tk_kapi_")
    try:
        _onceki_kosu(dizin)
        s = _hatali_tukenme()
        once = copy.deepcopy(s)
        try:
            tukenme.calistir(s, dizin, veri_kontrolu=False)
            kontrol("calistir DogrulamaHatasi firlatti", False, "-> istisna yok")
        except dogrula.DogrulamaHatasi as e:
            kontrol("calistir DogrulamaHatasi firlatti", True)
            kontrol("bulgu guc yogunlugu",
                    any("güç yoğunluğu" in b.mesaj for b in e.bulgular),
                    "-> %s" % [b.mesaj for b in e.bulgular])
        kontrol("onceki h5 ve spec kaydi duruyor", _onceki_duruyor(dizin))
        kontrol("spec degismedi", s == once)
        # tukenme.var kapali spec de tukenme kurallarina gore denetlenir
        s["tukenme"]["var"] = False
        try:
            tukenme.calistir(s, dizin, veri_kontrolu=False)
            kontrol("var=False iken de kapi tukenmeyi denetler", False)
        except dogrula.DogrulamaHatasi:
            kontrol("var=False iken de kapi tukenmeyi denetler", True)
        kontrol("spec var alani degismedi", s["tukenme"]["var"] is False)
    finally:
        shutil.rmtree(dizin, ignore_errors=True)


def test_terminal_kapisi():
    print("\n[TH8] TUKENME TERMINAL: dogrulama hatasi -> bulgular basilir, cikis kodu != 0")
    from cekirdek import sema, tukenme
    dizin = tempfile.mkdtemp(prefix="tk_term_")
    try:
        _onceki_kosu(os.path.join(dizin, "kosu"))
        s = _hatali_tukenme()
        s["tukenme"]["var"] = False              # terminal var=True yapar, sonra kapi
        yol = os.path.join(dizin, "hatali.json")
        sema.kaydet(s, yol)
        cikti = io.StringIO()
        with redirect_stdout(cikti):
            kod = tukenme._terminal([yol, "--dizin", os.path.join(dizin, "kosu"),
                                     "--veri-kontrolu-yok"])
        metin = cikti.getvalue()
        kontrol("cikis kodu != 0 (%s)" % kod, kod not in (0, None))
        kontrol("bulgu basildi ([HATA ] ... güç yoğunluğu sıfırdan büyük olmalı)",
                any("[HATA ]" in x and "güç yoğunluğu sıfırdan büyük" in x
                    for x in metin.splitlines()), "-> %s" % metin[-300:])
        kontrol("onceki sonuc silinmedi", _onceki_duruyor(os.path.join(dizin, "kosu")))
    finally:
        shutil.rmtree(dizin, ignore_errors=True)


# ============================================================================
# birim: bolge alani, dogrudan yerlesimli ornekler, nokta yolu, hazirla
# ============================================================================

@gereksinim("R-G-05")
def test_bolge_alani():
    print("\n[TH12] BOLGE ALANI: halka, cokgen, altigen kor hucresi, desteklenmeyen")
    import openmc
    from cekirdek import kurucu, tukenme_hacim as th
    c1, c2 = openmc.ZCylinder(r=0.3), openmc.ZCylinder(r=0.5)
    kontrol("daire pi r^2", abs(th.bolge_alani(-c1) - math.pi * 0.09) < 1e-12)
    kontrol("halka", abs(th.bolge_alani(+c1 & -c2) - math.pi * 0.16) < 1e-12)
    kutu = openmc.model.RectangularPrism(2.0, 3.0)
    kontrol("dikdortgen 2 x 3", abs(th.bolge_alani(-kutu & +openmc.ZPlane(-1.0)) - 6.0) < 1e-9)
    kontrol("sinirsiz yarim duzlem -> None", th.bolge_alani(+openmc.XPlane(0.0)) is None)
    kontrol("dis bolge (+silindir) -> None", th.bolge_alani(+c2) is None)
    kontrol("birlesim -> None", th.bolge_alani(-c1 | -kutu) is None)
    kontrol("silindir + duzlem karisik -> None", th.bolge_alani(-c1 & +openmc.XPlane(0.0)) is None)
    kontrol("bos bolge -> None", th.bolge_alani(None) is None)
    kontrol("kesismeyen duzlemler -> 0",
            th.bolge_alani(+openmc.XPlane(1.0) & -openmc.XPlane(0.0)) == 0.0)
    model, _b = kurucu.kur(_altigen_merkez_uo2())
    P = T.ZARF
    kok = [c for c in model.geometry.root_universe.cells.values()]
    alanlar = [th.bolge_alani(c.region) for c in kok]
    kontrol("7 altigen kor hucresi: (sqrt3/2) P^2 (goreli 1e-10)",
            len(alanlar) == 7 and all(abs(a / (SQ3 / 2 * P * P) - 1) < 1e-10 for a in alanlar),
            "-> %s" % alanlar)


def test_ornek_hacimleri_dogrudan():
    print("\n[TH13] CUBUK CUBUK YANMA: dogrudan yerlesimli ornekler (kor hucresi, kafes, katman)")
    from cekirdek import sema
    P, Pk = T.ZARF, 3 * 1.26
    s1 = _altigen_merkez_uo2(yukseklik=None)
    s1["kor"]["eksenel"] = {"var": True, "bolgeler": [
        sema.eksenel_bolge("alt", 30.0, None), sema.eksenel_bolge("ust", 10.0, None)]}
    s2 = _kare_kor(demet_harita=("yyy", "yuy", "yyy"))
    s3 = T._kor_spec()
    s3["kor"]["eksenel"] = {"var": True, "bolgeler": [
        sema.eksenel_bolge("ortu", 20.0, "uo2"), sema.eksenel_bolge("aktif", 50.0, None)]}
    durumlar = (
        ("altigen merkez hucre", s1, SQ3 / 2 * P * P, {30.0: 1, 10.0: 1}),
        ("kare kor konumu + demet konumu", s2, None, None),
        ("altigen katman dolgusu", s3, SQ3 / 2 * P * P, {20.0: 7}))
    for ad, s, alan, sayilar in durumlar:
        s["tukenme"].update(var=True, malzemeleri_ayir=True)
        hacimler, toplam = _ayrilmis(s)
        kontrol("%s: ornek toplami = analitik (%.6g)" % (ad, toplam),
                abs(sum(hacimler) - toplam) < 1e-9 * toplam)
        if alan:
            for h, n in sayilar.items():
                bulunan = sum(1 for v in hacimler if abs(v - alan * h) < 1e-9 * alan * h)
                kontrol("%s: %d ornek = alan x %g cm" % (ad, n, h), bulunan == n,
                        "-> %d" % bulunan)
    hacimler, _t = _ayrilmis(s2)
    kontrol("kare: kor konumu (P^2 H) ve demet konumu (p^2 H) ornekleri",
            any(abs(v - Pk * Pk * H) < 1e-9 for v in hacimler)
            and sum(1 for v in hacimler if abs(v - 1.26 ** 2 * H) < 1e-9) == 3)


def test_ornek_hacimleri_hatalar():
    print("\n[TH14] CUBUK CUBUK YANMA: toplam tutmazsa / ornek hacmi yoksa ValueError")
    from cekirdek import kurucu, tukenme, tukenme_hacim
    s = _iki_cubuklu_kare()
    model, kb = kurucu.kur(s)
    hv = tukenme.hacimler(s)
    m = kb["malzemeler"]["uo2"]
    m.depletable, m.volume = True, hv["uo2"]["hacim"]
    yanlis = {"uo2": dict(hv["uo2"], hacim=hv["uo2"]["hacim"] * 1.01)}
    try:
        tukenme_hacim.ornekleri_ayir(model, s, yanlis, {"uo2": m})
        kontrol("toplam tutmuyor -> ValueError", False)
    except ValueError as e:
        kontrol("toplam tutmuyor -> ValueError", "tutmuyor" in str(e), "-> %s" % e)
    model, kb = kurucu.kur(s)
    su = kb["malzemeler"]["su"]          # cubuk dis bolgesi: alan tanimsiz
    try:
        tukenme_hacim.ornekleri_ayir(model, s, {"su": {"hacim": 1.0}}, {"su": su})
        kontrol("ornek hacmi yok -> ValueError", False)
    except ValueError as e:
        kontrol("ornek hacmi yok -> ValueError", "hesaplanamıyor" in str(e), "-> %s" % e)


def test_nokta_yolu():
    print("\n[TH15] NOKTA YOLU: Geometry yolu Cell.paths icinde (saf Python)")
    import random
    from cekirdek import kurucu, tukenme_hacim
    for ad, s in (("kare", _iki_cubuklu_kare()), ("altigen", _iki_cubuklu_altigen())):
        model, bilgi = kurucu.kur(s)
        geo = model.geometry
        geo.determine_paths()
        gx, gy = bilgi["sinir_kutu"]
        rnd = random.Random(4)
        bulunan = disari = yok = 0
        for _ in range(1500):
            p = (rnd.uniform(-gx / 2, gx / 2), rnd.uniform(-gy / 2, gy / 2),
                 rnd.uniform(-34.9, 34.9))
            y = tukenme_hacim.nokta_yolu(geo, p)
            if y is None:
                disari += 1
                continue
            hucre, dizi = y
            bulunan += dizi in hucre.paths and geo.find(p)[-1] is hucre
            yok += dizi not in hucre.paths
        kontrol("%s: %d nokta yolu Cell.paths'te, %d eksik (disarida %d)"
                % (ad, bulunan, yok, disari), yok == 0 and bulunan > 500)
    kontrol("model disi nokta -> None",
            tukenme_hacim.nokta_yolu(geo, (1e4, 1e4, 0.0)) is None)


class _ZincirVar(object):
    """hazirla'yi zincir dosyasi olmadan sinamak icin zincir_kontrol taklidi."""

    def __enter__(self):
        from cekirdek import veri_bilgi
        self._eski = veri_bilgi.zincir_kontrol
        veri_bilgi.zincir_kontrol = lambda yol, tam=False: (True, "taklit", 0)
        return self

    def __exit__(self, *a):
        from cekirdek import veri_bilgi
        veri_bilgi.zincir_kontrol = self._eski


def test_hazirla():
    print("\n[TH16] HAZIRLA: ornek ayirma, atlanan zehir, eksik hacim hatasi")
    from cekirdek import sema, tukenme
    with _ZincirVar():
        s = _iki_cubuklu_kare()
        model, b = tukenme.hazirla(s)
        kontrol("ornek sayisi 72 (4 demet x 9 cubuk x 2 katman)", b["ornek_sayisi"] == 72,
                "-> %s" % b["ornek_sayisi"])
        kontrol("agir metal > 0", b["agir_metal_g"] > 0)
        _m, b = tukenme.hazirla(_kontrol_spec(50.0, katmanli=True))
        kontrol("katmanli: kontrol cubugu b4c atlandi, uo2 yanar",
                "b4c" in b["atlanan"] and "b4c" not in b["yanabilir"]
                and "uo2" in b["yanabilir"], "-> %s / %s" % (b["atlanan"], b["yanabilir"]))
        _m, b = tukenme.hazirla(_kontrol_spec(50.0))
        kontrol("katmansiz, daldirma %50: b4c de yanar (analitik hacim)",
                "b4c" in b["yanabilir"] and "b4c" not in b["atlanan"]
                and "uo2" in b["yanabilir"], "-> %s / %s" % (b["atlanan"], b["yanabilir"]))
        ks = _kontrol_spec(50.0)
        ks["tukenme"]["malzemeleri_ayir"] = True
        try:
            m, b = tukenme.hazirla(ks)
            b4c = sema.malzeme_bul(ks, "b4c")
            ad = b4c.get("gorunen_ad") or "b4c"          # OpenMC malzeme adi
            klon = [x for x in m.materials if x.name == ad and x.depletable]
            v = sum(x.volume for x in klon)
            kontrol("cubuk cubuk yanma: 25 b4c ornegi", len(klon) == 25, "-> %d" % len(klon))
            kontrol("cubuk cubuk yanma: b4c ornekleri toplami analitik hacim (yari boy)",
                    abs(v - b["hacimler"]["b4c"]["hacim"]) < 1e-6 * v, "-> %g / %g"
                    % (v, b["hacimler"]["b4c"]["hacim"]))
        except ValueError as e:
            kontrol("cubuk cubuk yanma: b4c ornekleri toplami analitik hacim (yari boy)",
                    False, "-> %s" % e)
        _m, b = tukenme.hazirla(_kontrol_spec(0.0))
        kontrol("cekili cubuk: b4c ne yanar ne atlanir (geometride yok)",
                "b4c" not in b["atlanan"] and "b4c" not in b["yanabilir"],
                "-> %s / %s" % (b["atlanan"], b["yanabilir"]))
        f = T._kor_spec(kilif=True)
        f["demetler"][0]["kilif"]["malzeme"] = "uo2"
        try:
            tukenme.hazirla(f)
            kontrol("kesin olmayan fisil hacim -> ValueError", False)
        except ValueError as e:
            kontrol("kesin olmayan fisil hacim -> ValueError", "kesin" in str(e), "-> %s" % e)
        cikti = io.StringIO()
        yol = os.path.join(tempfile.mkdtemp(prefix="tk_haz_"), "s.json")
        sema.kaydet(s, yol)
        with redirect_stdout(cikti):
            kod = tukenme._terminal([yol, "--hazirla"])
        kontrol("terminal --hazirla: agir metal basildi, kod 0",
                kod == 0 and "ağır metal" in cikti.getvalue())
        shutil.rmtree(os.path.dirname(yol), ignore_errors=True)


# ============================================================================
# YAVAS
# ============================================================================

@gereksinim("R-TK-02")
def test_hacim_stokastik(gecici):
    """Analitik hacim (dogrudan yerlesim dahil) = OpenMC stokastik hacim, 3 sigma."""
    print("\n[TH9] HACIM: analitik vs OpenMC stokastik (kare + altigen, dogrudan uo2)")
    from cekirdek import tukenme
    kare = _kare_kor(demet_harita=("yyy", "yuy", "yyy"))
    altigen = _altigen_merkez_uo2(yukseklik=50.0)
    altigen["demetler"][0]["anahtar"]["u"] = "uo2"
    altigen["demetler"][0]["harita"][-1] = "u"
    for ad, s in (("kare", kare), ("altigen", altigen)):
        s["ayarlar"]["tohum"] = 5
        a = tukenme.hacimler(s)["uo2"]["hacim"]
        dizin = os.path.join(gecici, ad)
        os.makedirs(dizin, exist_ok=True)
        v, sd = tukenme.stokastik_hacimler(s, ["uo2"], orneklem=4_000_000,
                                           dizin=dizin)["uo2"]
        kontrol("%s: analitik %.3f cm3 vs stokastik %.3f +/- %.3f (%.2f sigma)"
                % (ad, a, v, sd, abs(a - v) / sd), abs(a - v) <= 3 * sd)


def test_ornek_sirasi_openmc(gecici):
    """
    Ornek hacimleri Cell.paths sirasina gore atanir; bu sira C++ distribcell
    ornek sirasiyla ayni olmali (openmc.lib.find_cell). Olculdu (29.09):
    kare 3000/3000, altigen 1968/1968 nokta uyustu.

    !!! OPENMC SURUMU YUKSELTILIRKEN BU TEST KAPIDIR !!!
      tukenme_hacim.ornekleri_ayir Cell.paths sirasinin C++ distribcell
      sirasiyla ayni oldugunu VARSAYAR; ornek toplami denetimi iki ornegin
      yer degistirmesini YAKALAMAZ (toplam ayni kalir). environment.yml'de
      openmc=0.16.0 sabittir; surum degisirse once bu test kosulur.
      D1-Kapanis (B9): ic ice kafes + esit olmayan UC katman + katmana ozel
      demet eslemesi (ayni hucre farkli katmanlarda farkli kafes yolundan
      gecer) eklendi.
    """
    print("\n[TH10] ORNEK SIRASI: Python Cell.paths = C++ distribcell (openmc.lib)")
    import random
    import openmc.lib
    from cekirdek import kurucu, tukenme_hacim
    for ad, s in (("kare", _iki_cubuklu_kare()), ("altigen", _iki_cubuklu_altigen()),
                  ("kare ic ice + katmana ozel demet", _ic_ice_katmanli_kare())):
        model, bilgi = kurucu.kur(s)
        geo = model.geometry
        geo.determine_paths()
        dizin = os.path.join(gecici, "sira_" + ad)
        os.makedirs(dizin, exist_ok=True)
        eski = os.getcwd()
        uyus = fark = 0
        try:
            os.chdir(dizin)
            model.export_to_model_xml()
            openmc.lib.init(output=False)
            gx, gy = bilgi["sinir_kutu"]
            rnd = random.Random(1)
            for _ in range(3000):
                p = (rnd.uniform(-gx / 2, gx / 2), rnd.uniform(-gy / 2, gy / 2),
                     rnd.uniform(-34.9, 34.9))
                yol = tukenme_hacim.nokta_yolu(geo, p)
                if yol is None:
                    continue
                hucre, dizi = yol
                c, i = openmc.lib.find_cell(p)
                j = hucre.paths.index(dizi)
                uyus += c.id == hucre.id and j == i
                fark += not (c.id == hucre.id and j == i)
        finally:
            openmc.lib.finalize()
            os.chdir(eski)
        kontrol("%s: %d noktada ornek sirasi ayni, %d farkli" % (ad, uyus, fark),
                fark == 0 and uyus > 1000)


def test_cubuk_cubuk_tukenme(gecici):
    """Kisa gercek kosu: sonuc dosyasindaki ornek hacimleri bizimkilerle ayni."""
    print("\n[TH11] CUBUK CUBUK TUKENME: kosu, ornek hacimleri sonuca yazildi")
    import openmc.deplete as d
    from cekirdek import tukenme
    s = _iki_cubuklu_kare()
    s["demetler"][0]["harita"] = ["yz", "zy"]
    s["demetler"][0]["boyut"] = [2, 2]
    s["kor"]["adim"] = 2 * 1.26
    s["ayarlar"].update(parcacik=500, cevrim=12, pasif=4)
    s["calistirma"]["is_parcacigi"] = ISLEM_PARCACIGI
    s["tukenme"].update(zincir="casl_termal", entegrator="predictor", adimlar=[0.5])
    h5, bilgi = tukenme.calistir(s, os.path.join(gecici, "tk"))
    r = d.Results(h5)
    hacimler = sorted(r[0].volume.values())
    beklenen = sorted([PIN * h for h in (50.0, 20.0) for _ in range(8)]
                      + [math.pi * 0.30 ** 2 * h for h in (50.0, 20.0) for _ in range(8)])
    kontrol("sonuc: %d ornek, hacimler bizimkilerle ayni" % len(hacimler),
            len(hacimler) == len(beklenen)
            and all(abs(a - b) < 1e-9 * b for a, b in zip(hacimler, beklenen)),
            "-> %s" % sorted(set(round(v, 5) for v in hacimler)))


HIZLI = [test_dogrudan_malzeme_hacmi, test_tukenme_dogrulama_dogrudan,
         test_ornek_hacimleri, test_ornek_hacimleri_ic_ice_katmanli,
         test_ornek_hacimleri_2b_ve_tek_ornek,
         test_yanabilir_bor, test_hacimsiz_zehir,
         test_calistir_kapisi, test_terminal_kapisi, test_bolge_alani,
         test_ornek_hacimleri_dogrudan, test_ornek_hacimleri_hatalar, test_nokta_yolu,
         test_hazirla]
YAVAS = [test_hacim_stokastik, test_ornek_sirasi_openmc, test_cubuk_cubuk_tukenme]
