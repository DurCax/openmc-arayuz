# -*- coding: utf-8 -*-
"""
 test_geometri_yonelim.py  --  G-1: yonelim ve "kora bakan yon" OLCUMLERI (§9, R9)

 Nokta-hucre sorgusuyla (testler/geometri_iz.nokta_izi; C++ ile ayni R (p - t)
 gezintisi) olculur:
   1. Bakis: her yerlesim modu (halka, liste, kafes_konumu) x ust donme
      {0, 60} x D {0, 90, 180}: c + 1/2 (r_ic + R) u noktasinda D = 0 emici
      (u kora dogru), D = 180 govde (emici karsi yonde), D = 90 emici yanda.
      halka modunda psi eski tambur.yerlesim ile BIT DUZEYINDE ayni.
   2. Karisik kafes yonelimi: altigen demet -> altigen eleman (dogru ve yanlis
      yonelim), kare kafes -> altigen eleman, altigen demet -> kare eleman.
   3. Pin kesiti: kare ve altigen pin kosesi yakitta; altigen pin eleman
      hucresiyle ayni yonde (kesit_yonelim = ters(kafes.yonelim)).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri).
"""

import copy
import math

from testler.ortak_test import kontrol
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik
from testler import geometri_iz as gi
from testler import geometri_ortak as go

SQ3 = math.sqrt(3.0)


def _kur(spec):
    import openmc
    from cekirdek import geometri, kurucu
    openmc.reset_auto_ids()
    nesneler, _m, _r = kurucu.malzemeleri_kur(spec)
    kok, kutu, dizin = geometri.kur(spec, nesneler, {})
    return kok, {id(m): ad for ad, m in nesneler.items()}, dizin


def _sorgu(kok, mat_adi, x, y, z=0.0):
    iz = gi.nokta_izi(kok, (x, y, z), mat_adi, gi.OrnekSayaci())
    return iz[0], (iz[1] if len(iz) > 1 else ())


def _malz(ornek, ad, yeni=None):
    return go.malzeme(ornek, ad, yeni)


# ----------------------------------------------------------------------------
# 1. bakis
# ----------------------------------------------------------------------------

R_T, R_IC = 4.0, 2.0


def _tambur_spec(mod, ust_donme, D):
    from cekirdek import sema
    spec = sema.yeni_spec("bakis olcumu")
    spec["malzemeler"] = [_malz("tamburlu_kor", "berilyum", "govde"),
                          _malz("tamburlu_kor", "b4c"), _malz("tamburlu_kor", "berilyum", "yans"),
                          _malz("tamburlu_kor", "u10mo")]
    spec["tamburlar"] = [{"ad": "tb", "yaricap": R_T, "govde_malzeme": "govde",
                          "emici_malzeme": "b4c", "emici_ic_yaricap": R_IC, "emici_aci": 120.0}]
    spec["kor"] = {"tur": "agac"}
    y = {"ad": "yer", "mod": mod, "icerik": {"tur": "bilesen", "ad": "tb"}}
    if mod == "halka":
        y.update(sayi=5, merkez_yaricap=30.0, baslangic_acisi=10.0)
        ic = {"tur": "malzeme", "ad": "u10mo"}
        halka_icerik = {"tur": "malzeme", "ad": "yans"}
        yer_halkada = True
    elif mod == "liste":
        y.update(konumlar=[[31.0, 2.0], [-5.0, 28.0], [-20.0, -22.0], [3.0, -33.0]])
        ic = {"tur": "malzeme", "ad": "u10mo"}
        halka_icerik = {"tur": "malzeme", "ad": "yans"}
        yer_halkada = True
    else:
        # 5x5 kare kafes (adim 12): kenar konumlarinda 'K' -> tambur deligi
        y.update(kafes="kk", harf="K")
        ic = {"tur": "kafes", "id": "kk", "sekil": "kare", "adim": 12.0, "boyut": [5, 5],
              "harita": ["RRKRR", "RYYYR", "KYYYK", "RYYYR", "RRKRR"],
              "anahtar": {"R": "yans", "Y": "u10mo", "K": "yans"}, "dis": "yans"}
        halka_icerik = {"tur": "malzeme", "ad": "yans"}
        yer_halkada = False
    kap = {"tur": "kap", "id": "ic_kap", "kesit": {"sekil": "silindir", "yaricap": 25.0}
           if mod != "kafes_konumu" else {"sekil": "dikdortgen", "boyut": [60.0, 60.0]},
           "ic": ic, "yerlesimler": [] if yer_halkada else [y],
           "halkalar": [{"kalinlik": 15.0, "icerik": halka_icerik,
                         "yerlesimler": [y] if yer_halkada else []}],
           "dis": {"tur": "malzeme", "ad": "yans"}}
    spec["geometri"] = {
        "parcalar": [{"ad": "duzenek", "dugum": kap}],
        "kok": {"tur": "kap", "id": "kok", "kesit": {"sekil": "silindir", "yaricap": 60.0},
                "ic": {"tur": "bilesen", "ad": "duzenek", "donusum": {"donme": ust_donme}},
                "halkalar": [], "yerlesimler": [], "yukseklik": None,
                "sinir": {"yan": "vacuum"}},
        "gruplar": [{"ad": "g", "tur": "donme", "deger": D, "uyeler": ["yer"]}]}
    return spec, kap


def _merkezler(spec, kap, ust_donme):
    from cekirdek.geometri import yerlesim
    y = (kap["yerlesimler"] or kap["halkalar"][0]["yerlesimler"])[0]
    kon, _f = yerlesim.merkezler(y, kap)
    t = math.radians(ust_donme)
    return [(x * math.cos(t) - yy * math.sin(t), x * math.sin(t) + yy * math.cos(t))
            for x, yy in kon]


def test_bakis_olcumu():
    print("\n[GY1] bakis: 3 mod x ust donme {0, 60} x D {0, 90, 180} -- emici yonu olculdu")
    rho = 0.5 * (R_IC + R_T)
    for mod in ("halka", "liste", "kafes_konumu"):
        for ust in (0.0, 60.0):
            for D in (0.0, 90.0, 180.0):
                spec, kap = _tambur_spec(mod, ust, D)
                kok, mat, _d = _kur(spec)
                tamam = True
                for cx, cy in _merkezler(spec, kap, ust):
                    u = math.atan2(-cy, -cx) + math.radians(D)
                    on = _sorgu(kok, mat, cx + rho * math.cos(u), cy + rho * math.sin(u))[0]
                    arka = _sorgu(kok, mat, cx - rho * math.cos(u), cy - rho * math.sin(u))[0]
                    tamam = tamam and on == "b4c" and arka == "govde"
                kontrol("%s, ust donme %g, D %g: emici beklenen yonde" % (mod, ust, D), tamam)


def test_halka_psi_bit_esit():
    print("\n[GY2] halka modu psi = eski tambur.yerlesim (bit duzeyinde)")
    from cekirdek import geometri, sema, tambur
    from cekirdek.geometri import yerlesim
    spec = sema.yukle(go.ORNEK + "/tamburlu_kor.json")
    for donme in (0.0, 37.3, 180.0, -12.5):
        s = copy.deepcopy(spec)
        s["kor"]["tambur"]["donme"] = donme
        s["kor"]["tambur"]["baslangic_acisi"] = 7.1
        m = geometri.model(s)
        y = m.kok["halkalar"][0]["yerlesimler"][0]
        yeni = yerlesim.ornekler(y, m.kok, m.tanimlar, m.gruplar)
        kontrol("donme %g: (x, y, psi) ayni" % donme, yeni == tambur.yerlesim(s["kor"]["tambur"]))


# ----------------------------------------------------------------------------
# 2. karisik kafes yonelimi
# ----------------------------------------------------------------------------

def _altigen_ic_altigen(kor_yon, pin_yon):
    """7 elemanli altigen kafes (kor_yon), elemanlar pin_yon'lu demet_hex."""
    malz, cub, dem = go.sfr_kutuphane()
    d = copy.deepcopy(dem[0])
    d["yonelim"] = pin_yon
    spec = go._taban("altigen x altigen", malz, cub, [d])
    P = 6 * 0.9 * SQ3 + 0.9
    spec["geometri"] = {"parcalar": [], "gruplar": [], "kok": {
        "tur": "kap", "id": "kok", "kesit": {"sekil": "silindir", "yaricap": 3 * P},
        "ic": {"tur": "kafes", "id": "kk", "sekil": "altigen", "adim": P, "halka_sayisi": 2,
               "yonelim": kor_yon, "harita": ["DDDDDD", "D"], "anahtar": {"D": d["ad"]},
               "dis": "sodyum"},
        "halkalar": [], "yerlesimler": [], "yukseklik": None, "sinir": {"yan": "vacuum"}}}
    return spec, P


def test_altigen_icinde_altigen():
    print("\n[GY3] altigen demet -> altigen eleman: dogru yonelim ters(kafes); kose olcumu")
    from cekirdek.geometri import kesit as _k
    for kor_yon in ("x", "y"):
        for pin_yon in ("x", "y"):
            spec, P = _altigen_ic_altigen(kor_yon, pin_yon)
            kok, mat, _d = _kur(spec)
            eleman = _k.ters_yonelim(kor_yon)          # eleman hucresi prizma yonelimi
            r_kose = P / SQ3
            koseler, yuzler = [], []
            for aci in _k.altigen_normal_acilari(eleman):
                t, k = math.radians(aci), math.radians(aci + 30.0)
                yuzler.append(len(_sorgu(kok, mat, 0.99 * P / 2 * math.cos(t),
                                         0.99 * P / 2 * math.sin(t))[1]) == 2 and
                              _sorgu(kok, mat, 0.99 * P / 2 * math.cos(t),
                                     0.99 * P / 2 * math.sin(t))[1][1] != "dis")
                koseler.append(_sorgu(kok, mat, 0.98 * r_kose * math.cos(k),
                                      0.98 * r_kose * math.sin(k))[1][1] != "dis")
            dogru = pin_yon == eleman
            kontrol("kor %s, pin %s (%s): yuz ortalari pinde" % (kor_yon, pin_yon,
                    "dogru" if dogru else "yanlis"), all(yuzler))
            kontrol("kor %s, pin %s: koseler %s" % (kor_yon, pin_yon,
                    "pinde (oturuyor)" if dogru else "kafes disinda (kirpilir; +1640 pcm)"),
                    all(koseler) if dogru else not any(koseler))


def test_kare_altigen_karisimi():
    print("\n[GY4] kare kafes -> altigen eleman; altigen demet -> kare eleman (olculdu)")
    from cekirdek.geometri import kesit as _k
    malz, cub, dem = go.pwr_kutuphane()
    kare_demet = next(d for d in dem if d["ad"] == "demet_24")          # 21.42 x 21.42
    Ph = 21.42 / (SQ3 - 1.0) + 0.5                                         # a <= (sqrt3-1) P
    spec = go._taban("kare in altigen", malz, cub, [kare_demet])
    for yon in ("x", "y"):
        spec["geometri"] = {"parcalar": [], "gruplar": [], "kok": {
            "tur": "kap", "kesit": {"sekil": "silindir", "yaricap": 3 * Ph},
            "ic": {"tur": "kafes", "id": "hk", "sekil": "altigen", "adim": Ph, "halka_sayisi": 2,
                   "yonelim": yon, "harita": ["AAAAAA", "A"], "anahtar": {"A": "demet_24"},
                   "dis": "su"},
            "halkalar": [], "yerlesimler": [], "yukseklik": None, "sinir": {"yan": "vacuum"}}}
        kok, mat, _d = _kur(spec)
        kose = [_sorgu(kok, mat, sx * 0.99 * 10.71, sy * 0.99 * 10.71)[1] for sx in (-1, 1)
                for sy in (-1, 1)]
        kontrol("altigen %s: kare demet koseleri demet kafesinde (sigar: a <= 0.732 P)" % yon,
                all(len(k) == 2 and k[1] != "dis" for k in kose)
                and _k.kare_altigene_sigar(21.42, Ph))
        eleman = _k.ters_yonelim(yon)
        yuz = [_sorgu(kok, mat, 0.99 * Ph / 2 * math.cos(math.radians(a)),
                      0.99 * Ph / 2 * math.sin(math.radians(a)))[1]
               for a in _k.altigen_normal_acilari(eleman)]
        kontrol("altigen %s: eleman yuz ortalari kare demetin DISINDA (dis dolgusu)" % yon,
                all(k[1] == "dis" for k in yuz), "-> %s" % yuz)
    # altigen demet -> kare eleman
    hmalz, hcub, hdem = go.sfr_kutuphane()
    d = hdem[0]                                     # pin 'y', zarf 10.253
    zarf = 6 * 0.9 * SQ3 + 0.9
    a = 2.0 * zarf / SQ3 + 0.2                      # 'y' prizma yuksekligi 2d/sqrt3 <= a
    spec = go._taban("altigen in kare", hmalz, hcub, [d])
    spec["geometri"] = {"parcalar": [], "gruplar": [], "kok": {
        "tur": "kap", "kesit": {"sekil": "dikdortgen", "boyut": [2 * a, 2 * a]},
        "ic": {"tur": "kafes", "id": "kk", "sekil": "kare", "adim": a, "boyut": [2, 2],
               "harita": ["DD", "DD"], "anahtar": {"D": d["ad"]}, "dis": "sodyum"},
        "halkalar": [], "yerlesimler": [], "yukseklik": None, "sinir": {"yan": "vacuum"}}}
    kok, mat, _d = _kur(spec)
    c = (a / 2.0, a / 2.0)
    yuz = [_sorgu(kok, mat, c[0] + 0.99 * zarf / 2 * math.cos(math.radians(t)),
                  c[1] + 0.99 * zarf / 2 * math.sin(math.radians(t)))[1]
           for t in _k.altigen_normal_acilari("y")]
    kontrol("kare eleman: altigen demet yuz ortalari pinde (sigar)",
            all(len(k) == 2 and k[1] != "dis" for k in yuz)
            and _k.altigen_kareye_sigar(zarf, "y", a), "-> %s" % yuz)
    kose = _sorgu(kok, mat, c[0] + 0.49 * a, c[1] + 0.49 * a)[1]
    kontrol("kare eleman kosesi demetin disinda (dis dolgusu)", kose[1] == "dis", "-> %s" % (kose,))


# ----------------------------------------------------------------------------
# 3. pin kesiti
# ----------------------------------------------------------------------------

@gereksinim("R-G-05")
def test_pin_kesiti_olcumu():
    print("\n[GY5] kare ve altigen kesitli pin: kose noktalari yakitta, disari sogutucu")
    for sekil in ("kare", "altigen"):
        spec = go.duzenek_d(sekil)
        kok, mat, _d = _kur(spec)
        pin = spec["cubuklar"][0]
        r = pin["bolgeler"][0]["r"]
        yakit = pin["bolgeler"][0]["malzeme"]
        # merkez pinin (kafesin merkezi) kosesi
        if sekil == "kare":
            ofs = (0.0, 0.0)                         # 17x17: merkez pin (8, 8) kilavuz; komsu
            P = 1.26
            ofs = (P, 0.0)
            kose = [(ofs[0] + sx * 0.97 * r, sy * 0.97 * r) for sx in (-1, 1) for sy in (-1, 1)]
            disari = [(ofs[0] + sx * 1.1 * r * SQ3 / 1.7, 0.0) for sx in (-1, 1)]
        else:
            from cekirdek.geometri import kesit as _k
            yon = pin.get("kesit_yonelim")
            kose = [(0.97 * 2 * r / SQ3 * math.cos(math.radians(a + 30)),
                     0.97 * 2 * r / SQ3 * math.sin(math.radians(a + 30)))
                    for a in _k.altigen_normal_acilari(yon)]
            disari = [(1.05 * 2 * r / SQ3 * math.cos(math.radians(a + 30)),
                       1.05 * 2 * r / SQ3 * math.sin(math.radians(a + 30)))
                      for a in _k.altigen_normal_acilari(yon)]
        kontrol("%s pin: koseler yakitta (%s)" % (sekil, yakit),
                all(_sorgu(kok, mat, x, y)[0] == yakit for x, y in kose),
                "-> %s" % [_sorgu(kok, mat, x, y)[0] for x, y in kose])
        kontrol("%s pin: kosenin disi yakit degil" % sekil,
                all(_sorgu(kok, mat, x, y)[0] != yakit for x, y in disari))


def test_altigen_pin_yonelimi():
    print("\n[GY6] altigen pin: kesit_yonelim = ters(kafes) eleman hucresiyle ayni yonde")
    from cekirdek.geometri import kesit as _k
    spec = go.duzenek_d("altigen")
    kafes_yon = spec["demetler"][0]["yonelim"]
    P = spec["demetler"][0]["adim"]
    for pin_yon in ("x", "y"):
        s = copy.deepcopy(spec)
        for c in s["cubuklar"]:
            c["bolgeler"][-2]["r"] = 0.999 * P / 2.0      # kilif, eleman hucresine yakin
            c["kesit_yonelim"] = pin_yon
        kok, mat, _d = _kur(s)
        kilif = s["cubuklar"][0]["bolgeler"][-2]["malzeme"]
        eleman = _k.ters_yonelim(kafes_yon)
        kose = [(0.99 * P / SQ3 * math.cos(math.radians(a + 30)),
                 0.99 * P / SQ3 * math.sin(math.radians(a + 30)))
                for a in _k.altigen_normal_acilari(eleman)]
        icte = [_sorgu(kok, mat, x, y)[0] == kilif for x, y in kose]
        kontrol("pin %s (%s): eleman koselerinde kilif %s" % (
            pin_yon, "uyumlu" if pin_yon == eleman else "uyumsuz",
            "var" if pin_yon == eleman else "yok (kose sogutucuda)"),
            all(icte) if pin_yon == eleman else not any(icte))


HIZLI = [test_bakis_olcumu, test_halka_psi_bit_esit, test_altigen_icinde_altigen,
         test_kare_altigen_karisimi, test_pin_kesiti_olcumu, test_altigen_pin_yonelimi]
YAVAS = []
