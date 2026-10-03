# -*- coding: utf-8 -*-
"""
 test_y6_kinetik.py  --  v3 Y6: nokta kinetigi cozucusu (cekirdek/kinetik.py)

 Fizik kabulu (profesor denetimi):
   - birim donusumleri (pcm, $, k -> rho)
   - ters saat (Inhour) denklemi: tek grupta kapali bicimli ikinci derece kok,
     cok grupta her kok rho(omega) = rho'yu saglar
   - tek grup basamak: cozucu = analitik iki ustel cozum
   - 6 grup basamak: cozucu = matris ustel (tam dogrusal cozum); asimptotik
     periyot = 1/omega_0 (Inhour en buyuk koku)
   - kati (stiff) durum: Lambda = 1e-7 s; ani sicrama yaklasimi
   - rampa: Radau ve BDF birbirini tutar; kirilma noktasinda sureklilik
   - rho >= beta: ani kritik uyarisi; tasma olayinda cokme yerine uyari
   - adiyabatik geri besleme: Nordheim-Fuchs toplam sicaklik artisi
"""

import math

import numpy as np

from testler.ortak_test import kontrol

from cekirdek import kinetik as kin
from testler.ortak_test import gereksinim  # v3 izlenebilirlik

_BIR_GRUP = kin.GrupVerisi(beta=(0.0065,), lam=(0.0767,), nesil_suresi=1e-4,
                           kaynak="test: tek grup")


def _hata(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(np.max(np.abs(a - b) / np.maximum(np.abs(b), 1e-300)))


def test_birim_donusumleri():
    print("\n[Y6-1] pcm, dolar ve k -> rho donusumleri")
    kontrol("100 pcm = 1e-3", math.isclose(kin.pcm_den(100.0), 1e-3))
    kontrol("1e-3 = 100 pcm", math.isclose(kin.pcm_e(1e-3), 100.0))
    kontrol("0.5 $ (beta=0.0065) = 0.00325", math.isclose(kin.dolar_dan(0.5, 0.0065), 0.00325))
    kontrol("0.0065 rho = 1 $", math.isclose(kin.dolar_a(0.0065, 0.0065), 1.0))
    kontrol("k=1.01 -> rho = 0.01/1.01", math.isclose(kin.k_den_rho(1.01), 0.01 / 1.01))
    for hatali in (lambda: kin.dolar_a(1e-3, 0.0), lambda: kin.k_den_rho(0.0)):
        try:
            hatali()
            kontrol("gecersiz girdi ValueError", False)
        except ValueError:
            kontrol("gecersiz girdi ValueError", True)


def test_grup_verisi_dogrulama():
    print("\n[Y6-2] GrupVerisi sinir dogrulamasi ve Keepin hazir verisi")
    hatalar = [dict(beta=(0.001, 0.002), lam=(0.1,), nesil_suresi=1e-5),
               dict(beta=(-0.001,), lam=(0.1,), nesil_suresi=1e-5),
               dict(beta=(0.001,), lam=(0.0,), nesil_suresi=1e-5),
               dict(beta=(0.001,), lam=(0.1,), nesil_suresi=0.0),
               dict(beta=(), lam=(), nesil_suresi=1e-5),
               dict(beta=(0.0,), lam=(0.1,), nesil_suresi=1e-5),
               dict(beta=(float("nan"),), lam=(0.1,), nesil_suresi=1e-5),
               dict(beta=(0.001,) * 9, lam=(0.1,) * 9, nesil_suresi=1e-5)]
    for h in hatalar:
        try:
            kin.GrupVerisi(**h)
            kontrol("gecersiz grup verisi reddedildi: %s" % h, False)
        except ValueError:
            kontrol("gecersiz grup verisi reddedildi", True)
    k = kin.KEEPIN_U235_TERMAL
    kontrol("Keepin U-235 termal: 6 grup", len(k.beta) == 6 and len(k.lam) == 6)
    kontrol("Keepin toplam beta = 0.0065", abs(k.beta_toplam - 0.0065) < 5e-6,
            "-> %.6f" % k.beta_toplam)
    kontrol("lambda artan sirada (grup 1 en uzun omurlu)", list(k.lam) == sorted(k.lam))
    yeni = k.nesil_suresi_ile(3e-5)
    kontrol("nesil_suresi_ile yeni nesne doner, girdi degismez",
            yeni.nesil_suresi == 3e-5 and k.nesil_suresi != 3e-5 and yeni.beta == k.beta)


def test_inhour_tek_grup_kapali_bicim():
    print("\n[Y6-3] Inhour tek grup: Lambda w^2 + (Lambda l + b - r) w - r l = 0")
    b, l, L = 0.0065, 0.0767, 1e-4
    for rho in (0.001, -0.002, 0.0065, 0.01):
        a2, a1, a0 = L, L * l + b - rho, -rho * l
        d = math.sqrt(a1 * a1 - 4 * a2 * a0)
        beklenen = sorted([(-a1 + d) / (2 * a2), (-a1 - d) / (2 * a2)], reverse=True)
        kok = kin.inhour_kokleri(_BIR_GRUP, rho)
        kontrol("rho=%g: iki kok kapali bicimle ayni" % rho, len(kok) == 2
                and _hata(kok, beklenen) < 1e-9, "-> %s / %s" % (kok, beklenen))


@gereksinim("R-V3-18")
def test_inhour_cok_grup():
    print("\n[Y6-4] Inhour 6 grup: N+1 kok, rho(w)=rho, isaret kurallari")
    v = kin.KEEPIN_U235_TERMAL.nesil_suresi_ile(2e-5)
    for rho in (0.001, -0.003, 0.0, 0.008):
        kok = kin.inhour_kokleri(v, rho)
        kontrol("rho=%g: 7 kok" % rho, len(kok) == 7)
        kontrol("rho=%g: her kok ters saat denklemini saglar" % rho,
                all(abs(kin.inhour_rho(v, w) - rho) < 1e-10 for w in kok))
        if rho > 0:
            kontrol("pozitif rho: tek pozitif kok", sum(w > 0 for w in kok) == 1)
        elif rho < 0:
            kontrol("negatif rho: tum kokler negatif, en buyugu > -lambda_1",
                    max(kok) < 0 and max(kok) > -v.lam[0])
        else:
            kontrol("rho=0: en buyuk kok 0", abs(kok[0]) < 1e-12)
    kontrol("rho=0: kararli periyot sonsuz", math.isinf(kin.kararli_periyot(v, 0.0)))
    # 100 pcm (~0.15 $) LWR icin ders kitabi buyuklugu: ~ 1 dakika
    t = kin.kararli_periyot(v, 0.001)
    kontrol("Keepin, 100 pcm: periyot 40-80 s", 40.0 < t < 80.0, "-> %.1f s" % t)


@gereksinim("R-V3-18")
def test_tek_grup_basamak_analitik():
    print("\n[Y6-5] tek grup basamak: cozucu = analitik iki ustel")
    for rho in (0.001, -0.002, 0.003):
        w1, w2 = kin.inhour_kokleri(_BIR_GRUP, rho)
        L = _BIR_GRUP.nesil_suresi
        a1 = (rho / L - w2) / (w1 - w2)
        a2 = 1.0 - a1
        coz = kin.coz(_BIR_GRUP, kin.Basamak(rho), 20.0, nokta=201)
        t = np.asarray(coz.t)
        beklenen = a1 * np.exp(w1 * t) + a2 * np.exp(w2 * t)
        e = _hata(coz.guc, beklenen)
        kontrol("rho=%g: bagil hata < 1e-6" % rho, coz.basarili and e < 1e-6, "-> %.2e" % e)
    coz = kin.coz(_BIR_GRUP, kin.Basamak(0.001), 200.0, nokta=401)
    w1 = kin.inhour_kokleri(_BIR_GRUP, 0.001)[0]
    kontrol("cozumden olculen periyot = 1/w0 (%%0.1)",
            abs(kin.periyot_tahmini(coz) * w1 - 1.0) < 1e-3,
            "-> %.4f s / %.4f s" % (kin.periyot_tahmini(coz), 1.0 / w1))


@gereksinim("R-V3-18")
def test_alti_grup_basamak_matris_ustel():
    print("\n[Y6-6] 6 grup basamak: cozucu = matris ustel; periyot = Inhour")
    v = kin.KEEPIN_U235_TERMAL.nesil_suresi_ile(2e-5)
    for rho in (0.001, -0.003):
        coz = kin.coz(v, kin.Basamak(rho), 30.0, nokta=151)
        tam = kin.analitik_basamak(v, rho, coz.t)
        e = _hata(coz.guc, tam)
        kontrol("rho=%g: Radau ~ expm (bagil < 1e-6)" % rho, e < 1e-6, "-> %.2e" % e)
    coz = kin.coz(v, kin.Basamak(0.001), 600.0, nokta=601)
    t0 = kin.kararli_periyot(v, 0.001)
    kontrol("asimptotik periyot Inhour koku ile %0.1 uyumlu",
            abs(kin.periyot_tahmini(coz) / t0 - 1.0) < 1e-3,
            "-> %.3f / %.3f s" % (kin.periyot_tahmini(coz), t0))
    kontrol("kritik altinda periyot negatif",
            kin.periyot_tahmini(kin.coz(v, kin.Basamak(-0.003), 600.0)) < 0)


def test_kati_durum_ani_sicrama():
    print("\n[Y6-7] kati (stiff) Lambda=1e-7 s; ani sicrama n = b/(b-r)")
    v = kin.KEEPIN_U235_TERMAL.nesil_suresi_ile(1e-7)
    rho = 0.5 * v.beta_toplam
    coz = kin.coz(v, kin.Basamak(rho), 0.01, nokta=11)
    sicrama = v.beta_toplam / (v.beta_toplam - rho)
    kontrol("t=0.01 s: n ~ ani sicrama (%1)", abs(coz.guc[-1] / sicrama - 1.0) < 0.01,
            "-> %.4f / %.4f" % (coz.guc[-1], sicrama))
    e = _hata(coz.guc[1:], kin.analitik_basamak(v, rho, coz.t)[1:])
    kontrol("kati durumda da matris ustel ile uyum (< 1e-5)", e < 1e-5, "-> %.2e" % e)


def test_rampa():
    print("\n[Y6-8] rampa reaktivitesi: profil, Radau=BDF, sureklilik")
    r = kin.Rampa(hiz=1e-4, sure=5.0, t0=1.0)
    kontrol("rampa degerleri", r.deger(0.5) == 0.0 and math.isclose(r.deger(3.5), 2.5e-4)
            and math.isclose(r.deger(100.0), 5e-4))
    kontrol("rampa kirilmalari", r.kirilmalar() == (1.0, 6.0))
    v = kin.KEEPIN_U235_TERMAL.nesil_suresi_ile(2e-5)
    a = kin.coz(v, r, 20.0, nokta=201, yontem="Radau")
    b = kin.coz(v, r, 20.0, nokta=201, yontem="BDF")
    e = _hata(a.guc, b.guc)
    kontrol("Radau ve BDF ayni sonuc (< 1e-5)", e < 1e-5, "-> %.2e" % e)
    kontrol("rho(t) cozumde de profille ayni",
            all(math.isclose(p, r.deger(t), abs_tol=1e-15) for t, p in zip(a.t, a.rho)))
    kontrol("rampa sonrasi asimptot: 5e-4 basamak periyoduna yaklasir",
            abs(kin.periyot_tahmini(kin.coz(v, r, 900.0, nokta=901))
                / kin.kararli_periyot(v, 5e-4) - 1.0) < 1e-2)
    for hatali in (lambda: kin.Rampa(hiz=1e-4, sure=-1.0), lambda: kin.Basamak(float("inf"))):
        try:
            hatali()
            kontrol("gecersiz reaktivite profili reddedildi", False)
        except ValueError:
            kontrol("gecersiz reaktivite profili reddedildi", True)


def test_ani_kritik_ve_tasma():
    print("\n[Y6-9] rho >= beta: ani kritik uyarisi; tasmada durur, cokmez")
    v = kin.KEEPIN_U235_TERMAL.nesil_suresi_ile(2e-5)
    coz = kin.coz(v, kin.Basamak(1.2 * v.beta_toplam), 10.0)
    kontrol("ani kritik uyarisi", any(u.kod == "ani_kritik" for u in coz.uyarilar),
            "-> %s" % [u.kod for u in coz.uyarilar])
    kontrol("tasma siniri asildi uyarisi ve erken durma",
            any(u.kod == "tasma" for u in coz.uyarilar) and coz.t[-1] < 10.0
            and max(coz.guc) <= kin.AZAMI_GUC_ORANI * 1.01)
    temiz = kin.coz(v, kin.Basamak(0.5 * v.beta_toplam), 1.0)
    kontrol("0.5 $: uyari yok", not temiz.uyarilar, "-> %s" % [u.kod for u in temiz.uyarilar])
    try:
        kin.coz(v, kin.Basamak(1e-3), -1.0)
        kontrol("negatif sure reddedildi", False)
    except ValueError:
        kontrol("negatif sure reddedildi", True)


def test_adiyabatik_nordheim_fuchs():
    print("\n[Y6-10] adiyabatik geri besleme: Nordheim-Fuchs dT = 2(r-b)/|a|")
    v = kin.KEEPIN_U235_TERMAL.nesil_suresi_ile(1e-5)
    b = v.beta_toplam
    rho0 = b + 0.002
    gb = kin.GeriBesleme(alfa=kin.pcm_den(-2.0), isi_kapasitesi=1e5, guc0=1.0)
    coz = kin.coz(v, kin.Basamak(rho0), 0.3, geri_besleme=gb, nokta=3001)
    tepe = int(np.argmax(coz.guc))
    # Nordheim-Fuchs (ani notronlar, adiyabatik): tepede DT = (r-b)/|a|,
    # P_max/P0 = (r-b)^2 C / (2 |a| Lambda P0); patlama sonunda DT = 2(r-b)/|a|
    fazla = rho0 - b
    kontrol("tepede DT = (r-b)/|a| (%2)",
            abs(coz.sicaklik[tepe] / (fazla / abs(gb.alfa)) - 1.0) < 0.02,
            "-> %.2f K" % coz.sicaklik[tepe])
    p_nf = fazla ** 2 * gb.isi_kapasitesi / (2 * abs(gb.alfa) * v.nesil_suresi * gb.guc0)
    kontrol("tepe gucu Nordheim-Fuchs ile %5", abs(coz.guc[tepe] / p_nf - 1.0) < 0.05,
            "-> %.3e / %.3e" % (coz.guc[tepe], p_nf))
    sonra = [i for i in range(tepe, len(coz.t)) if coz.guc[i] < 0.05 * coz.guc[tepe]]
    kontrol("guc tepe yapar ve geri besleme ile duser", tepe > 0 and bool(sonra))
    dt = coz.sicaklik[sonra[0]]
    beklenen = 2.0 * fazla / abs(gb.alfa)
    kontrol("patlama sonu sicaklik artisi 2(r-b)/|a| ile %5", abs(dt / beklenen - 1.0) < 0.05,
            "-> %.2f K / %.2f K" % (dt, beklenen))
    kontrol("geri besleme reaktivitesi rho'ya katildi",
            math.isclose(coz.rho[-1], rho0 + gb.alfa * coz.sicaklik[-1], rel_tol=1e-9))
    sifir = kin.coz(v, kin.Basamak(1e-3), 5.0,
                    geri_besleme=kin.GeriBesleme(alfa=0.0, isi_kapasitesi=1e5, guc0=1.0))
    duz = kin.coz(v, kin.Basamak(1e-3), 5.0)
    kontrol("alfa=0 geri beslemesiz cozumle ayni", _hata(sifir.guc, duz.guc) < 1e-7)
    pozitif = kin.coz(v, kin.Basamak(1e-4), 1.0,
                      geri_besleme=kin.GeriBesleme(alfa=1e-5, isi_kapasitesi=1e5, guc0=1.0))
    kontrol("pozitif alfa uyarisi", any(u.kod == "pozitif_alfa" for u in pozitif.uyarilar))
    try:
        kin.GeriBesleme(alfa=-1e-5, isi_kapasitesi=0.0, guc0=1.0)
        kontrol("sifir isi kapasitesi reddedildi", False)
    except ValueError:
        kontrol("sifir isi kapasitesi reddedildi", True)


def test_sifir_beta_grubu_ve_esit_lambda():
    print("\n[Y6-11] beta_i = 0 grubu (kaldirilabilir kutup) ve neredeyse esit lambda")
    sifirli = kin.GrupVerisi(beta=(0.0065, 0.0), lam=(0.0767, 1.0), nesil_suresi=1e-4)
    for rho in (0.001, -0.002):
        kok = kin.inhour_kokleri(sifirli, rho)
        kontrol("rho=%g: beta=0 grubu atilir, tek grupla ayni kokler" % rho,
                _hata(kok, kin.inhour_kokleri(_BIR_GRUP, rho)) < 1e-12, "-> %s" % (kok,))
    coz = kin.coz(sifirli, kin.Basamak(0.001), 20.0, nokta=21)
    duz = kin.coz(_BIR_GRUP, kin.Basamak(0.001), 20.0, nokta=21)
    kontrol("beta=0 grubu cozumu degistirmez", _hata(coz.guc, duz.guc) < 1e-7)
    yakin = kin.GrupVerisi(beta=(0.003, 0.0035), lam=(0.0767, 0.0767 * (1 + 1e-10)),
                           nesil_suresi=1e-4)
    kok = kin.inhour_kokleri(yakin, 0.001)
    kontrol("neredeyse esit lambda birlesir: 2 kok, tek grupla ayni",
            len(kok) == 2 and _hata(kok, kin.inhour_kokleri(_BIR_GRUP, 0.001)) < 1e-8,
            "-> %s" % (kok,))
    try:
        kin.inhour_rho(_BIR_GRUP, -0.0767)
        kontrol("kutupta inhour_rho ValueError", False)
    except ValueError:
        kontrol("kutupta inhour_rho ValueError", True)


def test_gecikmeli_basamak_ve_girdi_turleri():
    print("\n[Y6-12] t0 > 0 basamak = kaydirilmis analitik; t0/nokta tur denetimi")
    v = kin.KEEPIN_U235_TERMAL.nesil_suresi_ile(2e-5)
    coz = kin.coz(v, kin.Basamak(0.001, t0=2), 12.0, nokta=121)
    t = np.asarray(coz.t)
    once = t < 2.0
    kontrol("t < t0: P = P0", np.allclose(np.asarray(coz.guc)[once], 1.0, rtol=1e-9))
    sonra = ~once
    tam = kin.analitik_basamak(v, 0.001, t[sonra] - 2.0)
    e = _hata(np.asarray(coz.guc)[sonra], tam)
    kontrol("t >= t0: kaydirilmis matris ustel ile ayni (< 1e-6)", e < 1e-6, "-> %.2e" % e)
    kontrol("t0 float'a zorlanir", isinstance(kin.Basamak(0.001, t0=2).t0, float))
    for hatali in (lambda: kin.coz(v, kin.Basamak(1e-3), 1.0, nokta="abc"),
                   lambda: kin.coz(v, kin.Basamak(1e-3), 1.0, nokta=1),
                   lambda: kin.Basamak(1e-3, t0="x")):
        try:
            hatali()
            kontrol("gecersiz tur reddedildi", False)
        except (ValueError, TypeError):
            kontrol("gecersiz tur reddedildi", True)


def test_uzun_scram_bagil_dogruluk():
    print("\n[Y6-13] uzun scram: P/P0 ~ 1e-16 duzeyinde bagil dogruluk (atol tabani)")
    v = kin.KEEPIN_U235_TERMAL.nesil_suresi_ile(2e-5)
    rho = -kin.dolar_dan(10.0, v.beta_toplam)
    coz = kin.coz(v, kin.Basamak(rho), 3000.0, nokta=31)
    tam = kin.analitik_basamak(v, rho, coz.t)
    kontrol("son guc < 1e-14 (gercekten derin)", tam[-1] < 1e-14, "-> %.2e" % tam[-1])
    e = _hata(coz.guc, tam)
    kontrol("bagil hata < 1e-5 butun eksende", e < 1e-5, "-> %.2e" % e)


HIZLI = [test_birim_donusumleri, test_grup_verisi_dogrulama, test_inhour_tek_grup_kapali_bicim,
         test_inhour_cok_grup, test_tek_grup_basamak_analitik, test_alti_grup_basamak_matris_ustel,
         test_kati_durum_ani_sicrama, test_rampa, test_ani_kritik_ve_tasma,
         test_adiyabatik_nordheim_fuchs, test_sifir_beta_grubu_ve_esit_lambda,
         test_gecikmeli_basamak_ve_girdi_turleri, test_uzun_scram_bagil_dogruluk]
YAVAS = []
