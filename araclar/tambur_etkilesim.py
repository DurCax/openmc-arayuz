# -*- coding: utf-8 -*-
"""
================================================================================
 araclar/tambur_etkilesim.py  --  altigen_tambur_halkasi: tambur etkilesimi
================================================================================
 G-4 BILGI bulgusu (toplam / (6 x tek) = 1.22, istatistik +-0.23) siki yontemle
 yeniden olculur. Yapilandirmalar (iceri = donme 0, disari = donme 180):

   dis       6 tambur disari (halka modu; asil model)
   ic        6 tambur iceri  (halka modu)
   tek       tambur 0 iceri, digerleri disari (liste modu)
   komsu2    tambur 0, 1 iceri
   karsit2   tambur 0, 3 iceri
   uc        tambur 0, 2, 4 iceri (120 derece arayla)

 Yontem: her yapilandirma AYRI tohumla (bagimsiz), varsayilan 20000 x 230 /
 100 pasif = 2.6e6 aktif tarih (G-4'un 4000 x 80/20 = 2.4e5'inin ~11 kati);
 her kosuda Shannon entropisi platosu kosucu.entropi_yakinsama ile denetlenir.
 Deger: dk = k_dis - k_X ; drho = (k_dis - k_X) / (k_X k_dis) ; pcm = x 1e5.

   python araclar/tambur_etkilesim.py CIKTI_DIZINI [--parcacik N --cevrim C --pasif P]
 Sonuc CIKTI_DIZINI/sonuc.json ve ekrana (oranlar +- 1 sigma).
 Is parcacigi: OMP_NUM_THREADS (yoksa 6).
================================================================================
"""

import argparse
import copy
import json
import math
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

YAPILANDIRMALAR = (("dis", None), ("ic", None), ("tek", (0,)), ("komsu2", (0, 1)),
                   ("karsit2", (0, 3)), ("uc", (0, 2, 4)))
ICERI, DISARI = 0.0, 180.0
TOHUM_TABANI = 1001


def taban():
    from cekirdek import sema
    return sema.yukle(os.path.join(KOK, "ornekler", "altigen_tambur_halkasi.json"))


def hepsi(spec, donme):
    from cekirdek import geometri
    return geometri.grup_degeri_yaz(spec, "tamburlar", float(donme))


def tambur_konumlari(spec):
    y = spec["geometri"]["kok"]["halkalar"][0]["yerlesimler"][0]
    R, fi0, n = y["merkez_yaricap"], y["baslangic_acisi"], y["sayi"]
    return [(R * math.cos(math.radians(fi0 + 360.0 * i / n)),
             R * math.sin(math.radians(fi0 + 360.0 * i / n))) for i in range(n)]


def secili(spec, iceri, donme_ic=ICERI, donme_dis=DISARI):
    """Halkayi iki liste yerlesimine boler: 'iceri' indisleri donme_ic, digerleri
    donme_dis. liste + merkeze bakis, halka modundaki yonle aynidir (§3.8;
    testler/test_geometri_fizik.tek_tambur genellemesi)."""
    yeni = copy.deepcopy(spec)
    halka = yeni["geometri"]["kok"]["halkalar"][0]
    y = halka["yerlesimler"][0]
    konum = [list(p) for p in tambur_konumlari(spec)]
    ortak = {"mod": "liste", "icerik": y["icerik"], "kesit": None,
             "bakis": {"tur": "merkez", "merkez": [0.0, 0.0]}}
    ic = [konum[i] for i in iceri]
    dis = [p for i, p in enumerate(konum) if i not in iceri]
    halka["yerlesimler"] = [dict(ortak, ad="tambur_ic", konumlar=ic)]
    gruplar = [{"ad": "ic", "tur": "donme", "deger": float(donme_ic), "uyeler": ["tambur_ic"]}]
    if dis:
        halka["yerlesimler"].append(dict(ortak, ad="tambur_dis", konumlar=dis))
        gruplar.append({"ad": "dis", "tur": "donme", "deger": float(donme_dis),
                        "uyeler": ["tambur_dis"]})
    yeni["geometri"]["gruplar"] = gruplar
    return yeni


def yapilandirma(spec, ad, iceri):
    if ad == "dis":
        return hepsi(spec, DISARI)
    if ad == "ic":
        return hepsi(spec, ICERI)
    return secili(spec, iceri)


def kos(spec, dizin, n, c, p, tohum, is_parcacigi):
    from cekirdek import kosucu
    s = copy.deepcopy(spec)
    s["ayarlar"].update(parcacik=n, cevrim=c, pasif=p, tohum=tohum)
    s["tallyler"] = []
    r = kosucu.calistir(s, dizin, is_parcacigi=is_parcacigi)
    if not r["basarili"]:
        raise RuntimeError("koşu başarısız: %s" % r.get("log"))
    sonuc = kosucu.sonuc_oku(r["statepoint"])
    yakinsadi, mesaj = kosucu.entropi_yakinsama(list(sonuc.get("entropi") or []), p)
    k, s_k = sonuc["keff"]
    return {"k": float(k), "sigma": float(s_k), "tohum": tohum, "sure": r["sure"],
            "entropi_yakinsadi": yakinsadi, "entropi_mesaj": mesaj}


def deger(dis, x):
    """(dk, s_dk, drho, s_drho) pcm; k'lar bagimsiz (ayri tohum)."""
    k0, s0, k1, s1 = dis["k"], dis["sigma"], x["k"], x["sigma"]
    dk = k0 - k1
    drho = dk / (k0 * k1)               # = 1/k1 - 1/k0
    s_drho = math.hypot(s1 / k1 ** 2, s0 / k0 ** 2)
    return 1e5 * dk, 1e5 * math.hypot(s0, s1), 1e5 * drho, 1e5 * s_drho


def oran(a, sa, b, sb, carpan):
    """a / (carpan * b) ve 1 sigma (a, b bagimsiz kabul edilir; ortak 'dis'
    kosusu nedeniyle hafif pozitif ilinti vardir -> sigma ust sinir)."""
    r = a / (carpan * b)
    return r, abs(r) * math.hypot(sa / a, sb / b)


def ozet(kosular):
    dis = kosular["dis"]
    degerler = {ad: deger(dis, x) for ad, x in kosular.items() if ad != "dis"}
    oranlar = {}
    tek = degerler["tek"]
    for ad, carpan in (("ic", 6), ("komsu2", 2), ("karsit2", 2), ("uc", 3)):
        d = degerler[ad]
        oranlar[ad] = {"dk": oran(d[0], d[1], tek[0], tek[1], carpan),
                       "drho": oran(d[2], d[3], tek[2], tek[3], carpan), "carpan": carpan}
    return degerler, oranlar


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dizin")
    ap.add_argument("--parcacik", type=int, default=20000)
    ap.add_argument("--cevrim", type=int, default=230)
    ap.add_argument("--pasif", type=int, default=100)
    a = ap.parse_args(argv)
    is_p = int(os.environ.get("OMP_NUM_THREADS") or 6)
    os.makedirs(a.dizin, exist_ok=True)
    yol = os.path.join(a.dizin, "sonuc.json")
    kosular = {}
    if os.path.exists(yol):
        with open(yol, encoding="utf-8") as f:
            kosular = json.load(f).get("kosular", {})
    t = taban()
    for i, (ad, iceri) in enumerate(YAPILANDIRMALAR):
        if ad in kosular:
            continue
        kosular[ad] = kos(yapilandirma(t, ad, iceri), os.path.join(a.dizin, ad),
                          a.parcacik, a.cevrim, a.pasif, TOHUM_TABANI + i, is_p)
        print("%-8s k = %.5f +/- %.5f  entropi %s  (%.0f s)" % (
            ad, kosular[ad]["k"], kosular[ad]["sigma"], kosular[ad]["entropi_yakinsadi"],
            kosular[ad]["sure"]), flush=True)
        with open(yol, "w", encoding="utf-8") as f:
            json.dump({"ayar": vars(a), "kosular": kosular}, f, indent=1)
    degerler, oranlar = ozet(kosular)
    for ad, (dk, sdk, dr, sdr) in degerler.items():
        print("%-8s dk = %6.0f +/- %3.0f pcm   drho = %6.0f +/- %3.0f pcm" % (ad, dk, sdk, dr, sdr))
    for ad, o in oranlar.items():
        print("%-8s / (%d x tek): dk %.3f +/- %.3f   drho %.3f +/- %.3f" % (
            ad, o["carpan"], o["dk"][0], o["dk"][1], o["drho"][0], o["drho"][1]))
    with open(yol, "w", encoding="utf-8") as f:
        json.dump({"ayar": vars(a), "kosular": kosular, "degerler": degerler,
                   "oranlar": oranlar}, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
