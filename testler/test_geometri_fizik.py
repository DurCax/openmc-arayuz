# -*- coding: utf-8 -*-
"""
================================================================================
 test_geometri_fizik.py  --  Dalga G-4: yeni ornekler ve geometri agacinin fizik kabulu
================================================================================
 Plan "Dalga G" G-4; docs/GEOMETRI_MODELI.md §4, §15. Olcumler docs/ORNEKLER.md'de.

 HIZLI
   [GF1] Uc yeni ornek (gelismis mod, sema 3): meta + referans olcumu tam,
         dogrulama kapisi hatasiz; UYARI yalniz (a)'daki beklenen "kesik blok".
   [GF2] Yeni orneklerde en az bir yakit malzemesinin hacmi ANALITIK (kesin).
   [GF3] Fizik fiksturleri: hepsi kapidan gecer; 60 derece dondurulmus model
         dondurulmemisle noktasal olarak AYNI malzemeyi verir (Monte Carlo'suz).
 YAVAS (OMP_NUM_THREADS / TEST_IS_PARCACIGI is parcacigi)
   [GF4] Sonsuz ortam: kafesin butun konumlari ayni demet, yansitici yok, sinir
         reflective -> k = tek demetin k-sonsuzu (2 sigma). Kare ve altigen.
   [GF5] Eski tamburlu_kor gelismise_gec ile agaca -> ayni k (2 sigma) ve ayni
         donme konvansiyonu (donme 0 -> en dusuk k).
   [GF6] 6 tamburlu altigen kor: donme 0 -> 180 k monoton artar (4 nokta).
         Toplam deger / (tek tambur x 6) yalniz BILGI (kabul olcutu degil).
   [GF7] Simetri: butun model 60 derece dondurulur (donusum dugumu; tambur
         donmesi ayni, 90 derece = kiral konum) -> k 2 sigma icinde ayni.
   [GF8] Yeni orneklerin yakit hacmi: analitik = OpenMC stokastik (her biri
         3 sigma, cogu 1 sigma).
   [GF9] Kare ve altigen kesitli pin demetlerinin yakit hacmi: analitik =
         stokastik (her biri 3 sigma, cogu 1 sigma).
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
================================================================================
"""

import copy
import math
import os
import random

from testler.ortak_test import kontrol, ORNEK, ISLEM_PARCACIGI
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik
from testler import geometri_ortak as go

YENI = ("pwr_kare_altigen_halka", "altigen_tambur_halkasi", "kafes_tamburlu_yansitici")
YAKIT = {"pwr_kare_altigen_halka": "uo2_24", "altigen_tambur_halkasi": "u10mo",
         "kafes_tamburlu_yansitici": "uo2_31"}
NORMAL = (10000, 150, 40)
TURKCE = set("çğıöşüÇĞİÖŞÜ")
OLCUM_ALANLARI = ("k", "sigma", "parcacik", "sure_s", "is_parcacigi", "openmc", "kutuphane")
Z_KABUL = 2.0                    # k karsilastirmalari: 2 sigma
HACIM_Z = 3.0                    # hacim: her olcum 3 sigma, cogu 1 sigma


def _spec(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _z(a, b):
    (ka, sa), (kb, sb) = a, b
    return abs(ka - kb) / math.hypot(sa, sb)


# ----------------------------------------------------------------------------
# fiksturler (saf: her cagri yeni spec)
# ----------------------------------------------------------------------------

def _agac(spec, kok, parcalar=(), gruplar=()):
    yeni = copy.deepcopy(spec)
    yeni["kor"] = {"tur": "agac"}
    yeni["geometri"] = {"kok": kok, "parcalar": list(parcalar), "gruplar": list(gruplar)}
    return yeni


def _yansitici(yukseklik=None):
    return {"yan": "reflective", "alt": "reflective", "ust": "reflective"} \
        if yukseklik else {"yan": "reflective"}


def tek_kare_demet():
    """Sablon tek_demet: demet_24 (17x17), 2B, yansitici -> k-sonsuz."""
    from cekirdek import sema
    malz, cub, dem = go.pwr_kutuphane()
    spec = go._taban("GF4 tek kare demet", malz, cub, dem)
    spec["kor"] = sema.tamamla({"kor": {"tur": "tek_demet", "demet": "demet_24",
                                        "sinir": _yansitici()}})["kor"]
    return spec


def sonsuz_kare():
    """Agac: 3x3 kare kafes, iki harf (A, B) AYNI demete; yansitici kok."""
    spec = tek_kare_demet()
    kafes = {"tur": "kafes", "id": "kor_kafesi", "sekil": "kare", "adim": 21.42,
             "boyut": [3, 3], "harita": ["ABA", "BAB", "ABA"],
             "anahtar": {"A": {"tur": "bilesen", "ad": "demet_24"},
                         "B": {"tur": "bilesen", "ad": "demet_24"}},
             "dis": {"tur": "malzeme", "ad": "su"}}
    kok = {"tur": "kap", "id": "kok", "kesit": {"sekil": "dikdortgen", "boyut": [64.26, 64.26]},
           "ic": kafes, "yerlesimler": [], "halkalar": [], "yukseklik": None,
           "sinir": _yansitici()}
    return _agac(spec, kok)


def tek_altigen_demet():
    """Sablon: sfr_altigen (tek altigen demet, 2B, yansitici) -> k-sonsuz."""
    return _spec("sfr_altigen")


def sonsuz_altigen():
    """Agac: tek konumlu altigen kor kafesi ('x') icinde demet_hex (pin 'y');
    kok, kafes elemaninin altigen prizmasi ('y', apotem = demet zarfi)."""
    spec = tek_altigen_demet()
    apotem = (6 * math.sqrt(3.0) + 1.0) * 0.9 / 2.0
    kafes = {"tur": "kafes", "id": "kor_kafesi", "sekil": "altigen", "adim": 2 * apotem + 0.01,
             "halka_sayisi": 1, "yonelim": "x", "harita": ["D"],
             "anahtar": {"D": {"tur": "bilesen", "ad": "demet_hex"}},
             "dis": {"tur": "malzeme", "ad": "sodyum"}}
    kok = {"tur": "kap", "id": "kok",
           "kesit": {"sekil": "altigen", "yonelim": "y", "apotem": apotem},
           "ic": kafes, "yerlesimler": [], "halkalar": [], "yukseklik": None,
           "sinir": _yansitici()}
    return _agac(spec, kok)


def tambur_agaci(donme):
    """tamburlu_kor: sablon ve gelismise_gec ile agac (ikisi de verilen donmede)."""
    from cekirdek import geometri
    sablon = _spec("tamburlu_kor")
    sablon["kor"]["tambur"]["donme"] = float(donme)
    return sablon, geometri.gelismise_gec(sablon)


def _halka_yerlesimi(spec):
    return spec["geometri"]["kok"]["halkalar"][0]["yerlesimler"][0]


def tek_tambur(spec, donme_tek, donme_diger=180.0):
    """6 tamburlu halkayi iki liste yerlesimine boler: 1 tambur 'tek' grubunda,
    5 tambur 'tamburlar' grubunda. liste + merkeze bakis: psi = atan2 + D, halka
    modundaki fi + 180 + D ile ayni yon (§3.8)."""
    yeni = copy.deepcopy(spec)
    halka = yeni["geometri"]["kok"]["halkalar"][0]
    y = halka["yerlesimler"][0]
    R, fi0, n = y["merkez_yaricap"], y["baslangic_acisi"], y["sayi"]
    konum = [[R * math.cos(math.radians(fi0 + 360.0 * i / n)),
              R * math.sin(math.radians(fi0 + 360.0 * i / n))] for i in range(n)]
    ortak = {"mod": "liste", "icerik": y["icerik"], "kesit": None,
             "bakis": {"tur": "merkez", "merkez": [0.0, 0.0]}}
    halka["yerlesimler"] = [dict(ortak, ad="tambur_tek", konumlar=konum[:1]),
                            dict(ortak, ad="tambur_diger", konumlar=konum[1:])]
    yeni["geometri"]["gruplar"] = [
        {"ad": "tek", "tur": "donme", "deger": float(donme_tek), "uyeler": ["tambur_tek"]},
        {"ad": "tamburlar", "tur": "donme", "deger": float(donme_diger),
         "uyeler": ["tambur_diger"]}]
    return yeni


def parcali(spec, donme_derece):
    """altigen_tambur_halkasi'nin butun korunu bir parcaya alir ve kokte
    'donusum.donme' ile dondurur. Kafes zarfi yalniz kokte olabildigi icin
    parcada kafes disi = yansitici malzemesi, tamburlar ic bolgenin delikleri
    (ayni geometri). donme_derece = 0 dondurulmemis karsilastirma modelidir."""
    yeni = copy.deepcopy(spec)
    kok = yeni["geometri"]["kok"]
    halka = kok["halkalar"][0]
    dis = copy.deepcopy(halka["dis"])
    ic = copy.deepcopy(kok["ic"])
    ic["dis"] = copy.deepcopy(halka["icerik"])
    kor = {"tur": "kap", "id": "kor_parcasi", "kesit": dis, "ic": ic,
           "yerlesimler": copy.deepcopy(halka["yerlesimler"]), "halkalar": [],
           "dis": {"tur": "malzeme", "ad": "bosluk"}}
    yeni["geometri"]["parcalar"] = [{"ad": "kor_parcasi", "dugum": kor}]
    yeni["geometri"]["kok"] = {
        "tur": "kap", "id": "kok", "kesit": copy.deepcopy(dis),
        "ic": {"tur": "bilesen", "ad": "kor_parcasi",
               "donusum": {"donme": float(donme_derece)}},
        "yerlesimler": [], "halkalar": [], "yukseklik": kok["yukseklik"],
        "sinir": copy.deepcopy(kok["sinir"])}
    return yeni


def _grup(spec, deger, grup="tamburlar"):
    from cekirdek import geometri
    return geometri.grup_degeri_yaz(spec, grup, float(deger))


# ----------------------------------------------------------------------------
# HIZLI
# ----------------------------------------------------------------------------

def _meta_sorunlari(ad, ham):
    from cekirdek import ornek_bilgi
    sorun = list(ornek_bilgi.dogrula_meta(ham))
    for alan in ("baslik", "baslik_en", "aciklama", "aciklama_en", "kategori", "seviye"):
        if not ham.get(alan):
            sorun.append("%s eksik" % alan)
    if not TURKCE & set(ham.get("aciklama", "")):
        sorun.append("aciklama Turkce karakter icermiyor")
    olcum = (ham.get("referans") or {}).get("olcum") or {}
    sorun += ["olcum.%s eksik" % a for a in OLCUM_ALANLARI if olcum.get(a) in (None, "")]
    if ham.get("surum") != 3 or (ham.get("kor") or {}).get("tur") != "agac":
        sorun.append("gelismis mod (surum 3, kor.tur agac) degil")
    return sorun


def test_yeni_ornekler():
    print("\n[GF1] Uc yeni ornek: meta + referans olcumu, kapi hatasiz, UYARI yalniz kesik blok")
    from cekirdek import dogrula
    for ad in YENI:
        ham = go.ornek_ham(ad)
        sorun = _meta_sorunlari(ad, ham)
        kontrol("%s: meta ve olcum tam" % ad, not sorun, "-> %s" % sorun)
        s = _spec(ad)
        a = s["ayarlar"]
        kontrol("%s: varsayilan hassasiyet Normal (olculen sure <= 15 dk)" % ad,
                (a["parcacik"], a["cevrim"], a["pasif"]) == NORMAL
                and ham["referans"]["olcum"]["sure_s"] <= 900)
        try:
            dogrula.kapi(s, veri_kontrolu=False)
            hata = None
        except dogrula.DogrulamaHatasi as e:
            hata = [b.mesaj for b in e.bulgular]
        kontrol("%s: dogrulama kapisi hatasiz" % ad, hata is None, "-> %s" % hata)
        uyarilar = [b.mesaj for b in dogrula.tum_kontroller(s, veri_kontrolu=False)
                    if b.seviye == "uyari"]
        if ad == "pwr_kare_altigen_halka":
            kontrol("%s: yalniz beklenen 'kesik' UYARISI (16 blok)" % ad,
                    len(uyarilar) == 1 and uyarilar[0].startswith("16 kesik"),
                    "-> %s" % uyarilar)
        else:
            kontrol("%s: UYARI yok" % ad, not uyarilar, "-> %s" % uyarilar)
    for ad in ("altigen_tambur_halkasi", "kafes_tamburlu_yansitici"):
        g = _spec(ad)["geometri"]["gruplar"]
        kontrol("%s: 'tamburlar' donme grubu 180 (cekilmis)" % ad,
                [(x["ad"], x["tur"], x["deger"]) for x in g] == [("tamburlar", "donme", 180.0)])


@gereksinim("R-G-09")
def test_yeni_ornek_hacimleri_analitik():
    print("\n[GF2] Yeni orneklerde yakit hacmi analitik (kesin)")
    from cekirdek import geometri
    from cekirdek.geometri import hacim
    for ad, mal in YAKIT.items():
        k = hacim.analitik(geometri.model(_spec(ad)), mal)
        kontrol("%s: %s analitik %.6g cm3" % (ad, mal, k.hacim or 0), k.yontem == hacim.ANALITIK
                and k.hacim > 0, "-> %s %s" % (k.yontem, k.ayrinti[:120]))


def _malzeme_haritasi(spec, noktalar):
    from cekirdek import geometri
    from testler import geometri_iz as gi
    kok, _kutu, mat_adi, _k = gi.kok_kur(geometri.kur, spec)
    sayac = gi.OrnekSayaci()
    return [gi.nokta_izi(kok, p, mat_adi, sayac)[0] for p in noktalar]


def test_fiksturler():
    print("\n[GF3] Fizik fiksturleri kapidan gecer; 60 derece donme noktasal olarak ayni")
    from cekirdek import dogrula
    taban = _spec("altigen_tambur_halkasi")
    fiks = {"sonsuz_kare": sonsuz_kare(), "tek_kare_demet": tek_kare_demet(),
            "sonsuz_altigen": sonsuz_altigen(), "tambur_agaci": tambur_agaci(0)[1],
            "tek_tambur": tek_tambur(taban, 0.0), "parcali_0": parcali(taban, 0.0),
            "parcali_60": parcali(taban, 60.0)}
    for ad, s in fiks.items():
        try:
            dogrula.kapi(s, veri_kontrolu=False)
            hata = None
        except dogrula.DogrulamaHatasi as e:
            hata = [b.mesaj for b in e.bulgular]
        kontrol("%s: kapidan gecer" % ad, hata is None, "-> %s" % hata)
    r = random.Random(7)
    noktalar = []
    while len(noktalar) < 3000:
        x, y = r.uniform(-48.7, 48.7), r.uniform(-48.7, 48.7)
        if all(abs(x * math.cos(t) + y * math.sin(t)) < 48.69
               for t in (math.radians(30 + 60 * i) for i in range(6))):
            noktalar.append((x, y, r.uniform(-39.9, 39.9)))
    for donme in (90.0, 0.0):
        asil = _malzeme_haritasi(_grup(taban, donme), noktalar)
        for ad, s in (("parcali_0", parcali(taban, 0.0)), ("parcali_60", parcali(taban, 60.0))):
            diger = _malzeme_haritasi(_grup(s, donme), noktalar)
            fark = [(p, a, b) for p, a, b in zip(noktalar, asil, diger) if a != b]
            kontrol("tambur %g: %s = asil model (3000 nokta)" % (donme, ad), not fark,
                    "-> %d fark, ilk %s" % (len(fark), fark[:2]))
    # Duyarlilik: model 60 derece simetrik oldugu icin donusumu YOK SAYAN bir
    # kurucu da yukaridaki denetimi gecerdi. 30 derece simetri degildir: donusum
    # uygulaniyorsa malzeme haritasi DEGISMELIDIR.
    asil = _malzeme_haritasi(_grup(taban, 90.0), noktalar)
    otuz = _malzeme_haritasi(_grup(parcali(taban, 30.0), 90.0), noktalar)
    fark = sum(1 for a, b in zip(asil, otuz) if a != b)
    kontrol("duyarlilik: 30 derece (simetri degil) haritayi degistirir", fark > 100,
            "-> %d / %d nokta farkli" % (fark, len(noktalar)))
    tek = _malzeme_haritasi(tek_tambur(taban, 180.0), noktalar)
    kontrol("tek_tambur(180) = asil model (liste ve halka modu ayni yon)",
            tek == _malzeme_haritasi(taban, noktalar))


# ----------------------------------------------------------------------------
# YAVAS
# ----------------------------------------------------------------------------

def _deger_pcm(k_dis, k_ic):
    """Tambur degeri: (dk, drho) pcm. pcm = x 1e5; dk = k_dis - k_ic,
    drho = (k_dis - k_ic) / (k_dis k_ic) = 1/k_ic - 1/k_dis."""
    return 1e5 * (k_dis - k_ic), 1e5 * (k_dis - k_ic) / (k_dis * k_ic)


PCM_TANIMI = "pcm = x 1e5; dk = k2 - k1, drho = (k2 - k1)/(k1 k2)"


def _kos(spec, gecici, etiket, n, c, p):
    """(k, sigma) ya da None (kosu basarisiz -> KALDI)."""
    import time
    from cekirdek import kosucu
    s = copy.deepcopy(spec)
    s["ayarlar"].update(parcacik=n, cevrim=c, pasif=p)
    if "tukenme" in s:
        s["tukenme"]["var"] = False
    s["tallyler"] = []
    t0 = time.time()
    r = kosucu.calistir(s, os.path.join(gecici, etiket), is_parcacigi=ISLEM_PARCACIGI)
    if not kontrol("%s: kosu basarili" % etiket, r["basarili"], "-> %s" % r.get("log")):
        return None
    k = tuple(kosucu.sonuc_oku(r["statepoint"])["keff"])
    print("   %-22s k = %.5f +/- %.5f  (%d x %d/%d, %.0f s, %d is)"
          % (etiket, k[0], k[1], n, c, p, time.time() - t0, ISLEM_PARCACIGI))
    return k


@gereksinim("R-G-09")
def test_yavas_sonsuz_ortam(gecici):
    print("\n[GF4] Sonsuz ortam: kafes (ayni demet) = tek demet k-sonsuz (2 sigma)")
    for ad, tek, kafes in (("kare", tek_kare_demet(), sonsuz_kare()),
                           ("altigen", tek_altigen_demet(), sonsuz_altigen())):
        a = _kos(tek, gecici, "%s_tek" % ad, 10000, 120, 30)
        b = _kos(kafes, gecici, "%s_kafes" % ad, 10000, 120, 30)
        if a and b:
            z = _z(a, b)
            kontrol("%s: kafes = tek demet (%.2f sigma)" % (ad, z), z <= Z_KABUL)


@gereksinim("R-G-09")
def test_yavas_tamburlu_kor_agacta(gecici):
    print("\n[GF5] tamburlu_kor agacta: ayni k (2 sigma), donme 0 -> en dusuk k")
    k = {}
    for donme in (180, 0):
        sablon, agac = tambur_agaci(donme)
        k["sablon", donme] = _kos(sablon, gecici, "sablon_%d" % donme, 8000, 100, 30)
        k["agac", donme] = _kos(agac, gecici, "agac_%d" % donme, 8000, 100, 30)
    if None in k.values():
        return
    for donme in (180, 0):
        z = _z(k["sablon", donme], k["agac", donme])
        kontrol("donme %d: agac = sablon (%.2f sigma)" % (donme, z), z <= Z_KABUL)
    for tur in ("sablon", "agac"):
        z = (k[tur, 180][0] - k[tur, 0][0]) / math.hypot(k[tur, 180][1], k[tur, 0][1])
        kontrol("%s: k(0) < k(180), daldirilmis en dusuk (%.1f sigma)" % (tur, z), z > 3.0)
    dk, dr = _deger_pcm(k["agac", 180][0], k["agac", 0][0])
    print("   tambur degeri (agac): dk = %.0f pcm, drho = %.0f pcm  (%s)" % (dk, dr, PCM_TANIMI))


@gereksinim("R-G-09")
def test_yavas_tambur_monoton(gecici):
    print("\n[GF6] 6 tamburlu altigen kor: donme 0 -> 180 k monoton artar")
    taban = _spec("altigen_tambur_halkasi")
    acilar = (0, 60, 120, 180)
    k = [_kos(_grup(taban, a), gecici, "donme_%d" % a, 4000, 80, 20) for a in acilar]
    if None in k:
        return
    artis = [(b[0] - a[0]) / math.hypot(a[1], b[1]) for a, b in zip(k, k[1:])]
    kontrol("k monoton artar (adim farklari %s sigma)" % ["%.1f" % z for z in artis],
            all(z > 0 for z in artis))
    tek = _kos(tek_tambur(taban, 0.0), gecici, "tek_tambur_0", 4000, 80, 20)
    if tek is None:
        return
    toplam, toplam_r = _deger_pcm(k[-1][0], k[0][0])
    tek_deger, tek_r = _deger_pcm(k[-1][0], tek[0])
    print("   BILGI (%s): toplam dk %.0f / drho %.0f pcm; tek tambur dk %.0f / drho %.0f "
          "pcm; oran toplam / (6 x tek) = %.2f (dk), %.2f (drho) -- kabul olcutu DEGIL; "
          "siki olcum: araclar/tambur_etkilesim.py"
          % (PCM_TANIMI, toplam, toplam_r, tek_deger, tek_r,
             toplam / (6 * tek_deger) if tek_deger else 0,
             toplam_r / (6 * tek_r) if tek_r else 0))


@gereksinim("R-G-09")
def test_yavas_simetri_60(gecici):
    print("\n[GF7] Butun model 60 derece dondurulur (tambur donmesi 90, kiral): ayni k (2 sigma)")
    taban = _grup(_spec("altigen_tambur_halkasi"), 90.0)
    asil = _kos(taban, gecici, "asil_90", 6000, 100, 30)
    sifir = _kos(parcali(taban, 0.0), gecici, "parcali_0", 6000, 100, 30)
    dondu = _kos(parcali(taban, 60.0), gecici, "parcali_60", 6000, 100, 30)
    if None in (asil, sifir, dondu):
        return
    kontrol("dondurulmus = asil (%.2f sigma)" % _z(asil, dondu), _z(asil, dondu) <= Z_KABUL)
    kontrol("dondurulmemis parca = asil (%.2f sigma)" % _z(asil, sifir), _z(asil, sifir) <= Z_KABUL)


def _hacim_karsilastir(gecici, isler):
    from cekirdek import geometri
    from cekirdek.geometri import hacim
    zler = []
    for ad, spec, mal in isler:
        an = hacim.analitik(geometri.model(spec), mal)
        if not kontrol("%s: %s analitik" % (ad, mal), an.yontem == hacim.ANALITIK,
                       "-> %s" % an.ayrinti[:100]):
            continue
        dizin = os.path.join(gecici, "hacim_%s_%s" % (ad, mal))
        os.makedirs(dizin, exist_ok=True)
        v, sd = hacim.stokastik(spec, [mal], orneklem=4_000_000, dizin=dizin)[mal]
        z = abs(v - an.hacim) / sd if sd else float("inf")
        zler.append(z)
        print("   %-26s %-7s analitik %.6g, stokastik %.6g +/- %.3g cm3 (%.2f sigma)"
              % (ad, mal, an.hacim, v, sd, z))
        kontrol("%s: %s analitik = stokastik (%.2f sigma <= %g)" % (ad, mal, z, HACIM_Z),
                z <= HACIM_Z)
    ic_bir = sum(1 for z in zler if z <= 1.0)
    kontrol("olcumlerin cogu 1 sigma icinde (%d / %d)" % (ic_bir, len(zler)),
            zler and ic_bir >= (len(zler) + 1) // 2)


@gereksinim("R-G-09")
def test_yavas_yeni_ornek_hacimleri(gecici):
    print("\n[GF8] Yeni ornekler: yakit hacmi analitik = stokastik")
    _hacim_karsilastir(gecici, [(ad, _spec(ad), mal) for ad, mal in YAKIT.items()]
                       + [("pwr_kare_altigen_halka", _spec("pwr_kare_altigen_halka"), "uo2_31")])


@gereksinim("R-G-05")
def test_yavas_pin_kesiti_hacmi(gecici):
    print("\n[GF9] Kare ve altigen kesitli pin demetleri: yakit hacmi analitik = stokastik")
    _hacim_karsilastir(gecici, [("kare_pin", go.duzenek_d("kare"), "uo2_24"),
                                ("altigen_pin", go.duzenek_d("altigen"), "u10mo")])


HIZLI = [test_yeni_ornekler, test_yeni_ornek_hacimleri_analitik, test_fiksturler]
YAVAS = [test_yavas_sonsuz_ortam, test_yavas_tamburlu_kor_agacta, test_yavas_tambur_monoton,
         test_yavas_simetri_60, test_yavas_yeni_ornek_hacimleri, test_yavas_pin_kesiti_hacmi]
VERI_GEREKEN = [test_fiksturler]
