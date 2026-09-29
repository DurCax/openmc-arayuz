# -*- coding: utf-8 -*-
"""
 test_altigen_esdeger.py  --  D1-B: altigen tam kor esdegerligi ve sinir uyarilari

 Kapsam (profesor onerileri, bulgu 5 ve 7)
   * (a) deterministik esdegerlik (Monte Carlo YOK): her kok hucresi i icin
         rastgele noktalarda malzeme(kor, p) == malzeme(tek konumlu kor, p - c_i);
         kilifli + demetler arasi bosluklu, kor yonelimi x ve y
   * (b) asimetrik harita: 3 halkali (19 demet) korda yalniz (halka 0, sira k)
         konumunda farkli demet -> Geometry.find ile bulunan konum
         altigen.konumlar * P ve OpenMC HexLattice.find_element ile uyusur
   * sinir uyarilari: kilifli tek demet (demetler arasi bosluk yok), birden
     fazla demet turlu altigen kor + reflective yan sinir
   * YAVAS (c): 7 kilifli demet + bosluk + reflective = halka=1 kilifli tek
     konum (k-eff, 2 sigma)

 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS listeleri). Hizli testler
 nukleer veri, openmc.lib ya da cizim KULLANMAZ (Geometry.find saf Python).
"""

import copy
import math
import os
import random
import warnings

from testler.ortak_test import kontrol, ISLEM_PARCACIGI
from testler import test_altigen_kor as T

warnings.filterwarnings("ignore")

# (a) icin konum basina nokta sayisi. 2000 nokta, hucre alaninin ~%0.05'i
# kadar bir farki (or. bosluk yerine kilif) 1 - exp(-1) ~ %63 olasilikla,
# %0.5'i kadar bir farki pratikte kesin (1 - e^-10) yakalar; kilif kalinligi
# (0.15 cm) hucrenin ~%10'udur.
NOKTA_SAYISI = 2000


# ============================================================================
# model yardimcilari
# ============================================================================

def _kilifli_kor(halka, yonelim):
    """Kilifli + bosluklu altigen kor; pin kafesi kor yoneliminin tersi."""
    from cekirdek import altigen_kor
    s = T._kor_spec(kilif=True, halka=halka, yonelim=yonelim)
    s["demetler"][0]["yonelim"] = altigen_kor.ters_yonelim(yonelim)
    return s


def _tek_konum(s):
    """Ayni demet ve adimla halka=1 (tek konumlu) altigen kor."""
    from cekirdek import altigen
    t = copy.deepcopy(s)
    t["kor"].update(halka_sayisi=1, harita=altigen.bos_harita(1, "A"))
    return t


def _malzeme(model, x, y, z=0.0):
    """Noktadaki yaprak malzemenin adi; model disi None, bosluk 'void'."""
    yol = model.geometry.find((x, y, z))
    if not yol:
        return None
    hucre = yol[-1]
    return getattr(hucre.fill, "name", None) if hucre.fill is not None else "void"


def _hucrede_nokta(rnd, cx, cy, P, kor_yonelim):
    """Kok hucresinin (apotem P/2) icinden duzgun dagilimli nokta."""
    from cekirdek import altigen_kor
    normaller = [(math.cos(math.radians(a)), math.sin(math.radians(a)))
                 for a in altigen_kor.yuz_normali_acilari(kor_yonelim)[:3]]
    r = P / math.sqrt(3.0)
    while True:
        x, y = rnd.uniform(-r, r), rnd.uniform(-r, r)
        if all(abs(x * nx + y * ny) < P / 2.0 * (1.0 - 1e-9) for nx, ny in normaller):
            return cx + x, cy + y


# ============================================================================
# (a) deterministik esdegerlik
# ============================================================================

def test_altigen_nokta_esdegerligi():
    """Her kor hucresinin icerigi, tek konumlu korun otelenmis icerigidir."""
    print("\n[AE1] ALTIGEN KOR: kok hucresi = otelenmis tek konum (nokta testi)")
    from cekirdek import altigen_kor, kurucu
    for yonelim in ("x", "y"):
        s = _kilifli_kor(3, yonelim)
        P = float(s["kor"]["adim"])
        kor, _b = kurucu.kur(s)
        tek, _b = kurucu.kur(_tek_konum(s))
        merkezler = altigen_kor.kor_merkezleri(3, P, yonelim)
        rnd = random.Random(19)
        farkli, gorulen = 0, set()
        for cx, cy in merkezler:
            for _ in range(NOKTA_SAYISI):
                x, y = _hucrede_nokta(rnd, cx, cy, P, yonelim)
                a = _malzeme(kor, x, y)
                gorulen.add(a)
                farkli += a != _malzeme(tek, x - cx, y - cy)
        kontrol("yonelim %s: %d konum x %d nokta, farkli nokta yok (goruldu: %s)"
                % (yonelim, len(merkezler), NOKTA_SAYISI, sorted(map(str, gorulen))),
                farkli == 0 and {"uo2", "zr", "su", "celik"} <= gorulen,
                "-> %d farkli" % farkli)


# ============================================================================
# (b) asimetrik harita: konum sirasi = OpenMC HexLattice sirasi
# ============================================================================

def _openmc_kafesi(harita, P, yonelim):
    """Ayni harita ile saf bir OpenMC HexLattice (isaret universe'leri)."""
    import openmc
    isaret = {}
    lat = openmc.HexLattice()
    lat.center = (0.0, 0.0)
    lat.pitch = (P,)
    lat.orientation = yonelim
    lat.universes = [[isaret.setdefault(h, openmc.Universe(name=h)) for h in satir]
                     for satir in harita]
    return lat


def test_altigen_asimetrik_harita():
    """(halka 0, sira k) konumu Geometry.find, altigen.konumlar ve HexLattice'te ayni yer."""
    print("\n[AE2] ALTIGEN KOR: asimetrik harita, konum sirasi OpenMC ile ayni")
    from cekirdek import altigen, kurucu
    for yonelim in ("x", "y"):
        s = _kilifli_kor(3, yonelim)
        s["demetler"].append(dict(copy.deepcopy(s["demetler"][0]), ad="hex2"))
        P = float(s["kor"]["adim"])
        kon = altigen.konumlar(3, yonelim)
        uyusan = 0
        for k in range(altigen.halka_uzunlugu(2)):
            t = copy.deepcopy(s)
            satir = list(t["kor"]["harita"][0])
            satir[k] = "B"
            t["kor"]["harita"][0] = "".join(satir)
            t["kor"]["anahtar"]["B"] = "hex2"
            model, _b = kurucu.kur(t)
            x, y = kon[(0, k)][0] * P, kon[(0, k)][1] * P
            yol = model.geometry.find((x, y, 0.0))
            kok = yol[1] if len(yol) > 1 else None
            bulunan = getattr(getattr(kok, "fill", None), "name", None)
            lat = _openmc_kafesi(t["kor"]["harita"], P, yonelim)
            idx, _yerel = lat.find_element((x, y, 0.0))
            openmc_ad = lat.get_universe(idx).name
            # baska hicbir konumda hex2 yok
            digerleri = [(a, b) for kk, (a, b) in kon.items() if kk != (0, k)]
            tek = all(getattr(model.geometry.find((a * P, b * P, 0.0))[1].fill, "name", "")
                      != "hex2" for a, b in digerleri)
            uyusan += bulunan == "hex2" and openmc_ad == "B" and tek
        kontrol("yonelim %s: 12 konumun hepsinde find = konumlar x P = HexLattice"
                % yonelim, uyusan == 12, "-> %d/12" % uyusan)


# ============================================================================
# sinir uyarilari (bulgu 5)
# ============================================================================

def _mesajlar(spec, seviyeler=("uyari", "bilgi")):
    from cekirdek import dogrula
    return [(b.seviye, b.mesaj, b.oneri or "")
            for b in dogrula.tum_kontroller(spec, veri_kontrolu=False)
            if b.seviye in seviyeler]


def test_altigen_sinir_uyarilari():
    print("\n[AE3] ALTIGEN: kilifli tek demet ve cok demet turlu kor uyarilari")
    # kilifli tek demet: demetler arasi bosluk yok -> halka=1 altigen_kafes onerisi
    m = _mesajlar(T._tek_demet_spec(kilif=True))
    kontrol("kilifli tek demet: halka=1 altigen_kafes onerisi",
            any("halka=1" in x[1] + x[2] for x in m), "-> %s" % m)
    m = _mesajlar(T._tek_demet_spec(kilif=False))
    kontrol("kilifsiz tek demet: oneri yok", not any("halka=1" in x[1] + x[2] for x in m))
    # tek demet turlu kor + reflective: sonsuz kafes uyarisi YOK
    m = _mesajlar(T._kor_spec(kilif=True))
    kontrol("tek demet turu + reflective: sonsuz kafes uyarisi yok",
            not any("sonsuz kafes" in x[1] for x in m if x[0] == "uyari"), "-> %s" % m)
    # iki demet turu + reflective: uyari
    s = T._kor_spec(kilif=True)
    s["demetler"].append(dict(copy.deepcopy(s["demetler"][0]), ad="hex2"))
    s["kor"]["anahtar"]["B"] = "hex2"
    s["kor"]["harita"][1] = "B"
    m = _mesajlar(s)
    kontrol("iki demet turu + reflective: sonsuz kafes esdegerligi uyarisi",
            any(x[0] == "uyari" and "sonsuz kafes" in x[1] for x in m), "-> %s" % m)
    # katman basina bakilir: bir katmanda BUTUN konumlar hex2 ise o katman yine
    # tek turludur (esdegerlik gecerli); karisik katman uyarir
    from cekirdek import sema
    k = T._kor_spec(kilif=True)
    k["demetler"].append(dict(copy.deepcopy(k["demetler"][0]), ad="hex2"))
    k["kor"]["eksenel"] = {"var": True, "bolgeler": [
        sema.eksenel_bolge("alt", 20.0, None),
        sema.eksenel_bolge("ust", 20.0, None, anahtar={"A": "hex2"})]}
    m = _mesajlar(k)
    kontrol("katmanda tum konumlar hex2: uyari yok",
            not any("sonsuz kafes" in x[1] for x in m if x[0] == "uyari"), "-> %s" % m)
    k["kor"]["anahtar"]["B"] = "hex"
    k["kor"]["harita"][1] = "B"
    m = _mesajlar(k)
    kontrol("ust katmanda A -> hex2, B -> hex (karisik): uyari",
            any(x[0] == "uyari" and "sonsuz kafes" in x[1] for x in m), "-> %s" % m)
    # vacuum yan sinirda uyari yok
    s["kor"]["sinir"]["yan"] = "vacuum"
    m = _mesajlar(s)
    kontrol("iki tur + vacuum: uyari yok",
            not any("sonsuz kafes" in x[1] for x in m if x[0] == "uyari"))
    # periodic hatasinin onerisi: "ayni sonucu verir" yalniz tek demet turunde
    s["kor"]["sinir"]["yan"] = "periodic"
    h = _mesajlar(s, ("hata",))
    kontrol("iki tur + periodic: 'aynı sonucu verir' denmez",
            h and not any("aynı sonucu verir" in x[2] for x in h), "-> %s" % h)
    t = T._kor_spec(kilif=True)
    t["kor"]["sinir"]["yan"] = "periodic"
    h = _mesajlar(t, ("hata",))
    kontrol("tek tur + periodic: 'aynı sonucu verir' onerisi korunur",
            any("aynı sonucu verir" in x[2] for x in h), "-> %s" % h)


# ============================================================================
# (c) YAVAS: Monte Carlo esdegerligi
# ============================================================================

# Parcacik sayisi ve olcut: tek demet sonsuz kafesiyle 7 demet AYNI fiziksel
# sistemdir (demetler 6 katli ve ayna simetrik; reflective kirik cizgi sinir
# her demeti komsusunun yansimasiyla cevreler). Beklenen fark 0 oldugu icin
# olcut |k1 - k2| <= 2 sigma_birlesik; rastgele bir tohumda yanlis alarm
# olasiligi ~%4.6 (iki yanli normal). Tohum sabittir (11): OpenMC sonucu
# is parcacigi sayisindan bagimsiz tekrarlanir, yani ayni surumde test ya hep
# gecer ya hep kalir. 40 000 x 100 aktif cevrimde sigma ~45-55 pcm (AK13'te
# olculdu), 2 sigma ~140 pcm; yonelim hatasi (+1640 pcm) ya da vadilere dolgu
# kacmasi (+5300 pcm) bunun 10 katindan buyuktur.
MC_PARCACIK = 40000


def test_altigen_kilifli_mc_esdegerligi(gecici):
    print("\n[AE4] MC: 7 kilifli demet + bosluk (reflective) = halka=1 tek konum")
    from cekirdek import kurucu
    s = _kilifli_kor(2, "x")
    kor, _b = kurucu.kur(s)
    tek, _b = kurucu.kur(_tek_konum(s))
    k1 = T._kos(tek, os.path.join(gecici, "tek"), MC_PARCACIK)
    k2 = T._kos(kor, os.path.join(gecici, "kor"), MC_PARCACIK)
    fark = abs(k1.nominal_value - k2.nominal_value)
    sigma = math.hypot(k1.std_dev, k2.std_dev)
    kontrol("halka=1 %.5f +/- %.5f  vs  7 demet %.5f +/- %.5f  (fark %.2f sigma)"
            % (k1.nominal_value, k1.std_dev, k2.nominal_value, k2.std_dev, fark / sigma),
            fark <= 2 * sigma, "-> 2 sigma = %.0f pcm (is parcacigi %d)"
            % (2e5 * sigma, ISLEM_PARCACIGI))


HIZLI = [test_altigen_nokta_esdegerligi, test_altigen_asimetrik_harita,
         test_altigen_sinir_uyarilari]
YAVAS = [test_altigen_kilifli_mc_esdegerligi]
