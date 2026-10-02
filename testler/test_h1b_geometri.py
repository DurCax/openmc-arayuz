# -*- coding: utf-8 -*-
"""
 test_h1b_geometri.py  --  v3 H1b: on hesapli kesit icermesi esdegerligi

 geometri/kesit.py artik altigen yuz normallerini ve daire sinir noktalarini
 tablodan okur; geometri/bolge.py kesit bolgelerini olculeri bir kez okunan
 islevlerle (kesit.icinde_islevi) kurar. Bu test eski formullerin AYNI
 sonucu (bit duzeyinde ayni nokta, ayni bool) verdigini dogrular. Agac
 gezintisinin butun ciktisi icin ayrica: test_geometri_esdegerlik,
 test_betik*, test_capa.
"""

import math
import random

from testler.ortak_test import kontrol

_NOKTA = 4000                 # rastgele yoklama noktasi (sekil basina)
_KESITLER = (
    {"sekil": "dikdortgen", "boyut": [2.0, 1.3]},
    {"sekil": "dikdortgen", "boyut": [3, 1]},                 # tamsayi olculer
    {"sekil": "silindir", "yaricap": 0.7},
    {"sekil": "kure", "yaricap": 1.1},
    {"sekil": "altigen", "apotem": 0.9, "yonelim": "y"},
    {"sekil": "altigen", "apotem": 1.2, "yonelim": "x"},
    {"sekil": "altigen", "apotem": 1.0},                      # yonelim yok -> 'y'
)


def _eski_altigen_icinde(kesit, x, y, merkez, pay):
    """H1b oncesi formul (her cagrida radians/cos/sin)."""
    from cekirdek.geometri.kesit import altigen_normal_acilari
    px, py = x - merkez[0], y - merkez[1]
    a = float(kesit["apotem"])
    for aci in altigen_normal_acilari(kesit.get("yonelim", "y")):
        t = math.radians(aci)
        if px * math.cos(t) + py * math.sin(t) > a + pay:
            return False
    return True


def _eski_sinir_noktalari(kesit, merkez=(0.0, 0.0), n_daire=72):
    from cekirdek.geometri.kesit import SQ3, altigen_normal_acilari, sinir_noktalari
    cx, cy = merkez
    s = kesit.get("sekil")
    if s in ("silindir", "kure"):
        r = float(kesit["yaricap"])
        return [(cx + r * math.cos(2 * math.pi * i / n_daire),
                 cy + r * math.sin(2 * math.pi * i / n_daire)) for i in range(n_daire)]
    if s == "altigen":
        a = float(kesit["apotem"])
        r = 2.0 * a / SQ3
        noktalar = []
        for aci in altigen_normal_acilari(kesit.get("yonelim", "y")):
            t = math.radians(aci)
            noktalar.append((cx + a * math.cos(t), cy + a * math.sin(t)))
            k = math.radians(aci + 30.0)
            noktalar.append((cx + r * math.cos(k), cy + r * math.sin(k)))
        return noktalar
    return sinir_noktalari(kesit, merkez, n_daire)


def _noktalar(kesit, merkez, rnd):
    """Rastgele + sinir uzerinde + NaN noktalar (en zor durumlar)."""
    nk = [(rnd.uniform(-2, 2) + merkez[0], rnd.uniform(-2, 2) + merkez[1])
          for _i in range(_NOKTA)]
    nk += _eski_sinir_noktalari(kesit, merkez)
    return nk + [(float("nan"), 0.0), (0.0, float("nan"))]


def test_icinde_islevi_eski_icinde_ile_ayni():
    print("\n[H1b-G1] kesit.icinde_islevi ve tablolu icinde: eski formulle ayni bool")
    from cekirdek.geometri import kesit as _k
    rnd = random.Random(11)
    for kes in _KESITLER:
        for merkez in ((0.0, 0.0), (0.37, -0.81), (2, 1)):
            f = _k.icinde_islevi(kes, merkez)
            fark = 0
            for x, y in _noktalar(kes, merkez, rnd):
                for pay in (_k.PAY, -_k.PAY, 0.0, -1.0e-7):
                    eski = _eski_altigen_icinde(kes, x, y, merkez, pay) \
                        if kes["sekil"] == "altigen" else _k.icinde(kes, x, y, merkez, pay)
                    if f(x, y, pay) != eski or _k.icinde(kes, x, y, merkez, pay) != eski:
                        fark += 1
            kontrol("%s %s merkez %s: fark yok" % (kes["sekil"], kes.get("yonelim", ""), merkez),
                    fark == 0, "fark=%d" % fark)


def test_sinir_noktalari_bit_duzeyinde_ayni():
    print("\n[H1b-G2] kesit.sinir_noktalari: tablolu degerler eski formulle bit duzeyinde ayni")
    from cekirdek.geometri import kesit as _k
    for kes in _KESITLER:
        for merkez in ((0.0, 0.0), (0.37, -0.81)):
            for n in (72, 16):
                yeni = _k.sinir_noktalari(kes, merkez, n_daire=n)
                kontrol("%s %s n=%d: ayni" % (kes["sekil"], kes.get("yonelim", ""), n),
                        yeni == _eski_sinir_noktalari(kes, merkez, n_daire=n))


def test_bilinmeyen_kesit_cagrida_hata_verir():
    print("\n[H1b-G3] bilinmeyen kesit: icinde_islevi kurulur, cagrida ValueError (eskisi gibi)")
    from cekirdek.geometri import kesit as _k
    f = _k.icinde_islevi({"sekil": "kafes_zarfi"})
    try:
        f(0.0, 0.0, 0.0)
    except ValueError:
        kontrol("ValueError", True)
        return
    kontrol("ValueError", False)


def test_kapsar_daire_cokgende_eski_formulle_ayni():
    print("\n[H1b-G4] kesit.kapsar (daire altigende): tablolu normal ile ayni karar")
    from cekirdek.geometri import kesit as _k
    rnd = random.Random(4)
    fark = 0
    for _i in range(3000):
        dis = {"sekil": "altigen", "apotem": rnd.uniform(0.5, 2.0),
               "yonelim": rnd.choice(("x", "y"))}
        merkez, r = (rnd.uniform(-1, 1), rnd.uniform(-1, 1)), rnd.uniform(0.05, 1.0)
        eski = all(merkez[0] * math.cos(math.radians(a)) + merkez[1] * math.sin(math.radians(a))
                   + r <= dis["apotem"] + _k.PAY
                   for a in _k.altigen_normal_acilari(dis["yonelim"]))
        fark += _k._daire_cokgende(dis, merkez, r, _k.PAY) != eski
    kontrol("3000 rastgele daire: fark yok", fark == 0, "fark=%d" % fark)


def test_yavas_sfr_gezintisi_hizlandi():
    print("\n[H1b-G5] SFR-MET1000 gelismis agac gezintisi: CPU <= 0.20 s (taban 0.40 s)")
    import time
    from testler.test_h1_hiz import _sfr_gelismis
    from cekirdek import geometri
    from cekirdek.geometri import gezinti
    m = geometri.model(_sfr_gelismis())
    sureler = []
    for _i in range(3):
        t = time.process_time()
        sum(1 for _z in gezinti.gez(m))
        sureler.append(time.process_time() - t)
    # esik: taban 0.40 s'nin yarisi (>= 2x hizlanma); olculen 0.106 s
    kontrol("gezinti <= 0.20 s", min(sureler) <= 0.20, "%.3f s" % min(sureler))


HIZLI = [test_icinde_islevi_eski_icinde_ile_ayni, test_sinir_noktalari_bit_duzeyinde_ayni,
         test_bilinmeyen_kesit_cagrida_hata_verir, test_kapsar_daire_cokgende_eski_formulle_ayni]
YAVAS = [test_yavas_sfr_gezintisi_hizlandi]


def test_ziyaretler_bellekli_ve_gez_ile_ayni():
    print("\n[H1b-G6] gezinti.ziyaretler: gez ile ayni, ayni icerikte ikinci cagri gezmez")
    from cekirdek import geometri, sema, uygunluk_bellek
    from cekirdek.geometri import gezinti
    from testler.ortak_test import ORNEK
    import os
    s = geometri.gelismise_gec(sema.yukle(os.path.join(ORNEK, "pwr_kare_altigen_halka.json")))
    uygunluk_bellek.temizle()
    m = geometri.model(s)
    ilk = gezinti.ziyaretler(m)
    kontrol("gez ile ayni ziyaretler", [(z.yol, z.carpan, z.kesik) for z in ilk]
            == [(z.yol, z.carpan, z.kesik) for z in gezinti.gez(m)])
    sayi = [0]
    asil = gezinti.gez

    def sayan(mm):
        sayi[0] += 1
        return asil(mm)
    gezinti.gez = sayan
    try:
        ikinci = gezinti.ziyaretler(geometri.model(s))
    finally:
        gezinti.gez = asil
    kontrol("ikinci cagri gezmez ve ayni demet", sayi[0] == 0 and ikinci is ilk)


def test_yavas_sfr_zamanlayici_dogrulamasi_hizli():
    print("\n[H1b-G7] SFR gelismis: tus sonrasi dogrulama (yoklama arka planda) <= 0.2 s CPU")
    import os
    import time
    from cekirdek import dogrula, geometri, sema, uygunluk
    from cekirdek.geometri import yoklama
    from testler.ortak_test import ORNEK
    s = geometri.gelismise_gec(sema.yukle(os.path.join(ORNEK, "sfr_met1000_kor.json")))
    uygunluk.gecerli_sekmeler(s)            # tusun kendi gezintisi (arayuzdeki sira)
    t = time.process_time()
    with yoklama.arka_planda(lambda: None):
        dogrula.tum_kontroller(s, veri_kontrolu=False)
    sure = time.process_time() - t
    # gerekce: plan hedefi "hicbir islemde > 200 ms donma"; taban 12.4 s
    kontrol("dogrulama <= 0.2 s", sure <= 0.2, "%.3f s" % sure)


HIZLI.append(test_ziyaretler_bellekli_ve_gez_ile_ayni)


def _rastgele_bolge(rnd):
    from cekirdek.geometri import bolge as _b
    sekil = rnd.choice(("altigen", "dikdortgen", "silindir"))
    if sekil == "altigen":
        kes = {"sekil": "altigen", "apotem": rnd.uniform(0.5, 2.0), "yonelim": rnd.choice("xy")}
    elif sekil == "dikdortgen":
        kes = {"sekil": "dikdortgen", "boyut": [rnd.uniform(1.0, 4.0), rnd.uniform(1.0, 4.0)]}
    else:
        kes = {"sekil": "silindir", "yaricap": rnd.uniform(0.5, 2.0)}
    merkez = (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3)) if rnd.random() < 0.5 else (0.0, 0.0)
    return _b.kesit_bolgesi(kes, merkez)


def test_sigar_kesin_kisayolu_tam_denetimle_ayni():
    print("\n[H1b-G8] bolge.sigar daire kisayolu: kesisim/otele/geri_cek bilesimlerinde tam "
          "sinir noktasi denetimiyle ayni karar")
    from cekirdek.geometri import bolge as _b
    from cekirdek.geometri import kesit as _k
    rnd = random.Random(21)
    fark = kisayol = 0
    for _i in range(4000):
        a, b = _rastgele_bolge(rnd), _rastgele_bolge(rnd)
        secim = rnd.randrange(4)
        if secim == 0:
            bolge = _b.kesisim(a, _b.otele(b, rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5)))
        elif secim == 1:
            bolge = _b.geri_cek(a, rnd.uniform(0, 360), (rnd.uniform(-0.3, 0.3), 0.1))
        elif secim == 2:
            bolge = _b.kesisim(_b.geri_cek(a, 30.0, (0.0, 0.2)), b)
        else:
            bolge = a
        pin = _k.pin_bolge_kesiti(rnd.choice(("silindir", "kare", "altigen")),
                                  rnd.uniform(0.05, 1.5), rnd.choice("xy"))
        merkez = (rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5))
        tam = bolge.hepsi_icinde(_k.sinir_noktalari(pin, merkez))
        fark += _b.sigar(bolge, pin, merkez) != tam
        kisayol += bool(bolge.daire is not None and bolge.daire(merkez[0], merkez[1],
                                                                _k.dis_yaricap(pin)))
    kontrol("4000 rastgele durumda fark yok", fark == 0, "fark=%d" % fark)
    kontrol("kisayol gercekten devrede (> 400)", kisayol > 400, "kisayol=%d" % kisayol)


HIZLI.append(test_sigar_kesin_kisayolu_tam_denetimle_ayni)
YAVAS.append(test_yavas_sfr_zamanlayici_dogrulamasi_hizli)
