# -*- coding: utf-8 -*-
"""
test_uygunluk_denetimi.py -- Dalga S-1 sonuc uygunluk denetcisi
(cekirdek/uygunluk_denetimi/, kosucu cikti ayristirmasi).

Her kural icin KIRMIZI -> YESIL: kurali kasitli ihlal eden sahte kosu dizini
(testler/veri/kosu_ornek'in gecici kopyasi; statepoint alanlari h5py ile
degistirilir, kosu.log'a OpenMC bicimli uyari eklenir) ihlali, duzeltilmis
kopya "karsilandi"yi vermelidir. Monte Carlo KOSULMAZ, nukleer veri gerekmez.
Yanlis alarm: ornekler/kosu*/ (varsa) ve kosu_ornek A profilinde alarmsiz.
Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import copy
import glob
import json
import os
import shutil
import stat
import tempfile

from testler.ortak_test import kontrol, KOK
from testler.ortak_test import gereksinim  # S-4 izlenebilirlik

FIXTURE = os.path.join(KOK, "testler", "veri", "kosu_ornek")

# OpenMC 0.16 warning() bicimi: " WARNING: " + 80 sutunda kaydirma, devam 10 bosluk
KAYIP_UYARISI = (
    " WARNING: After particle 1234 crossed surface 17 it could not be located in\n"
    "          any cell and it did not leak.\n")
KAFES_UYARISI = (" WARNING: Particle 99 could not be located after crossing a boundary of\n"
                 "          lattice 4\n")


# ----------------------------------------------------------------------------
# yardimcilar
# ----------------------------------------------------------------------------

def _kopya(h5=None, log_ek="", log_sil=False):
    """kosu_ornek'in gecici kopyasi. h5: {dataset: yeni deger} statepoint'e yazilir."""
    d = tempfile.mkdtemp(prefix="uygunluk_test_")
    for ad in os.listdir(FIXTURE):
        kaynak = os.path.join(FIXTURE, ad)
        # yalniz fixture dosyalari; __pycache__ gibi klasorler kopyalanmaz
        if ad != "uret.py" and os.path.isfile(kaynak):
            shutil.copy(kaynak, d)
    if h5:
        import h5py
        sp = glob.glob(os.path.join(d, "statepoint.*.h5"))[0]
        with h5py.File(sp, "r+") as f:
            for anahtar, deger in h5.items():
                del f[anahtar]
                f[anahtar] = deger
    if log_ek:
        with open(os.path.join(d, "kosu.log"), "a", encoding="utf-8") as f:
            f.write(log_ek)
    if log_sil:
        os.remove(os.path.join(d, "kosu.log"))
    return d


def _spec():
    with open(os.path.join(FIXTURE, "spec.json"), encoding="utf-8") as f:
        return json.load(f)


def _denetle(dizin, profiller=("A",), **kw):
    from cekirdek.uygunluk_denetimi.denetle import denetle
    return denetle(kw.pop("spec", None), dizin, profiller, **kw)


def _bul(bulgular, kimlik):
    return [b for b in bulgular if b.kural == kimlik]


def _durum(bulgular, kimlik):
    b = _bul(bulgular, kimlik)
    return (b[0].seviye, b[0].durum) if b else None


def _vv(**kw):
    from cekirdek.uygunluk_denetimi.vv_arayuz import VVOzeti
    temel = dict(n=25, yontem="tolerans_bandi", usl=0.95, bias=-0.002,
                 bias_kullanilan=-0.002, delta_sm=0.05, normallik={"test": "shapiro",
                                                                   "p": 0.3, "normal": True},
                 egilim={"H/X": {"egim": -2.8e-5, "anlamli": True}},
                 aralik={"zenginlik": (2.0, 5.0)}, aoa_kategorik={"tayf": ("termal",)},
                 seriler={"LCT-001": 1})
    temel.update(kw)
    return VVOzeti(**temel)


# ----------------------------------------------------------------------------
# ayristir + kosucu (M5)
# ----------------------------------------------------------------------------

@gereksinim("R-S-04")
def test_ayristir_log():
    print("\n[U1] OpenMC WARNING/ERROR ayristirma: kaydirilmis satirlar, kayip sayimi")
    from cekirdek.uygunluk_denetimi import ayristir
    satirlar = (" Reading U235 from x.h5\n" + KAYIP_UYARISI + "        1/1    1.1   7.9\n"
                + " WARNING: Negative value(s) found on probability table\n"
                + KAFES_UYARISI
                + " ERROR: Maximum number of lost particles has been reached.\n").splitlines()
    uyarilar, hatalar = ayristir.iletileri_topla(satirlar)
    kontrol("3 uyari, 1 hata", len(uyarilar) == 3 and len(hatalar) == 1, "-> %r" % (uyarilar,))
    kontrol("kaydirilmis ileti birlestirildi",
            "could not be located in any cell and it did not leak." in uyarilar[0])
    kontrol("cevrim satiri devam sayilmadi", "1/1" not in uyarilar[0])
    d = _kopya(log_ek=KAYIP_UYARISI + KAFES_UYARISI)
    try:
        ozet = ayristir.cikti_ozeti(d)
        kontrol("fixture + 2 kayip", ozet.log_var and ozet.kayip_parcacik == 2
                and len(ozet.uyarilar) == 2, "-> %r" % (ozet,))
        satir = ayristir.ozet_satirlari(ozet)
        kontrol("ozet satirlari KAYIP ile baslar", satir and satir[0].startswith("KAYIP PARÇACIK: 2"))
        os.remove(os.path.join(d, "kosu.log"))
        for i in range(3):
            open(os.path.join(d, "particle_4_%d.h5" % i), "w").close()
        ozet = ayristir.cikti_ozeti(d)
        kontrol("log yok, 3 restart dosyasi -> 3 kayip", not ozet.log_var
                and ozet.kayip_parcacik == 3)
    finally:
        shutil.rmtree(d, True)
    kontrol("None ozet -> bos satir", ayristir.ozet_satirlari(None) == [])
    kontrol("dizin yok -> log_var False", not ayristir.cikti_ozeti("/yok/boyle/dizin").log_var)


def _sahte_openmc(dizin):
    yol = os.path.join(dizin, "openmc")
    with open(yol, "w") as f:
        f.write("#!/bin/sh\n"
                "echo '  1/1   1.32041'\n"
                "echo ' WARNING: After particle 7 crossed surface 3 it could not be located in' >&2\n"
                "echo '          any cell and it did not leak.' >&2\n"
                "echo '  2/1   1.33000   1.32500 +/- 0.00400'\n"
                "echo x > particle_2_7.h5\n"
                "echo sp > statepoint.2.h5\n")
    os.chmod(yol, os.stat(yol).st_mode | stat.S_IEXEC)
    return yol


@gereksinim("R-S-04")
def test_kosucu_kayip_parcacik():
    print("\n[U2] kosucu.calistir: kayip parcacik sonucta; eski particle_*.h5 silinir; terminal")
    from cekirdek import kosucu, sema
    d = tempfile.mkdtemp()
    kosu_d = os.path.join(d, "kosu")
    os.makedirs(kosu_d)
    open(os.path.join(kosu_d, "particle_9_9.h5"), "w").close()     # onceki kosudan kalan
    eski = kosucu.openmc_yolu
    kosucu.openmc_yolu = lambda: _sahte_openmc(d)
    try:
        spec = sema.yukle(os.path.join(KOK, "ornekler", "pwr_pinhucre.json"))
        kosu = kosucu.calistir(spec, kosu_d, veri_kontrolu=False)
    finally:
        kosucu.openmc_yolu = eski
    c = kosu["cikti"]
    kontrol("1 kayip (eski restart silindi)", c.kayip_parcacik == 1
            and not os.path.exists(os.path.join(kosu_d, "particle_9_9.h5")), "-> %r" % (c,))
    kontrol("cevrimler hala ayristiriliyor", len(kosu["cevrimler"]) == 2)
    # terminal: calistir sahte, cikti ozeti basilir
    from testler.test_kosucu_yollar import _terminal, _spec_dosyasi
    yol = _spec_dosyasi(d)
    sonuc_k = dict(kosu, statepoint="sp.h5")
    kod, cikti, _c = _terminal([yol, "--dizin", d], {
        "mod": "eigenvalue", "keff": (1.0, 0.1), "cevrim": 5, "pasif": 1, "parcacik": 10,
        "entropi": [], "tallyler": {}}, sonuc_k)
    kontrol("terminal KAYIP PARCACIK satiri", kod == 0 and "KAYIP PARÇACIK: 1" in cikti,
            "-> %s" % cikti[-400:])
    shutil.rmtree(d, True)


# ----------------------------------------------------------------------------
# Profil A
# ----------------------------------------------------------------------------

@gereksinim("R-S-02")
def test_k1_entropi():
    print("\n[U3] K1 entropi platosu: kirmizi (pasif sonunda kayan) -> yesil (fixture)")
    import numpy as np
    # Fixture'in entropisi aktif donemde de duser (7.90 -> 7.84, σ ≈ 0.013): QA14-Q4'ten
    # beri K1 bunu dogru olarak yakalar. Yesil durum duz platolu sentetik dizidir.
    kontrol("fixture (aktifte kayan) -> uyari", _durum(_denetle(FIXTURE), "K1")
            == ("uyari", "karsilanmadi"))
    duz = np.concatenate([np.linspace(5.0, 7.9, 8), 7.9 + 0.002 * np.sin(np.arange(32))])
    d = _kopya(h5={"entropy": duz})
    try:
        kontrol("yesil: pasifte duzlesen plato -> karsilandi",
                _durum(_denetle(d), "K1") == ("bilgi", "karsilandi"))
    finally:
        shutil.rmtree(d, True)
    kayan = np.concatenate([np.linspace(5.0, 7.9, 15), 7.9 + 0.002 * np.sin(np.arange(25))])
    d = _kopya(h5={"entropy": kayan})
    try:
        kontrol("kirmizi: kayan kaynak -> uyari", _durum(_denetle(d), "K1")
                == ("uyari", "karsilanmadi"))
    finally:
        shutil.rmtree(d, True)
    d = _kopya(h5={"n_inactive": np.int32(2)})
    try:
        kontrol("pasif < 4 -> uygulanamadi", _durum(_denetle(d), "K1")
                == ("bilgi", "uygulanamadi"))
    finally:
        shutil.rmtree(d, True)
    d = _kopya(h5={"run_mode": np.bytes_(b"fixed source")})
    try:
        b = _denetle(d)
        kontrol("sabit kaynak -> K1/K2 uygulanamadi", _durum(b, "K1") == ("bilgi", "uygulanamadi")
                and _durum(b, "K2") == ("bilgi", "uygulanamadi"))
    finally:
        shutil.rmtree(d, True)


@gereksinim("R-S-02")
def test_k1_entropi_kapali_ve_bozuk():
    print("\n[U4] K1: entropi kapali -> uyari; statepoint bozuk -> uyari; statepoint yok")
    from cekirdek.uygunluk_denetimi import kurallar
    from cekirdek.uygunluk_denetimi.ayristir import KosuVerisi
    k1 = kurallar.kural_getir("K1")
    kosu = KosuVerisi("sp", "eigenvalue", 1.0, 0.001, 5000, 40, 15)
    b = k1.islev(k1, kurallar.Baglam(kosu=kosu))
    kontrol("entropi yok -> uyari", (b[0].seviye, b[0].durum) == ("uyari", "karsilanmadi"))
    d = _kopya()
    try:
        sp = glob.glob(os.path.join(d, "statepoint.*.h5"))[0]
        with open(sp, "wb") as f:
            f.write(b"bozuk")
        kontrol("bozuk statepoint -> uyari", _durum(_denetle(d), "K1")[0] == "uyari")
        os.remove(sp)
        kontrol("statepoint yok -> uygulanamadi", _durum(_denetle(d), "K1")
                == ("bilgi", "uygulanamadi"))
    finally:
        shutil.rmtree(d, True)


@gereksinim("R-S-03")
def test_k2_istatistik():
    print("\n[U5] K2: sigma hedefi, parcacik alt siniri, aktif cevrim, cevrimler arasi ilinti")
    import numpy as np
    from cekirdek.uygunluk_denetimi import profiller as P
    A = P.profil_getir("A")
    kontrol("sigma hedefi yok -> uygulanamadi", _durum(_denetle(FIXTURE), "K2-sigma")
            == ("bilgi", "uygulanamadi"))
    kirmizi = _denetle(FIXTURE, (P.uyarla(A, sigma_hedef=(0.001, "ders hedefi")),))
    yesil = _denetle(FIXTURE, (P.uyarla(A, sigma_hedef=(0.005, "ders hedefi")),))
    kontrol("sigma 0.00286 > 0.001 -> uyari", _durum(kirmizi, "K2-sigma") == ("uyari", "karsilanmadi"))
    kontrol("sigma <= 0.005 -> karsilandi", _durum(yesil, "K2-sigma") == ("bilgi", "karsilandi"))
    kontrol("kullanici kaynagi bulguda", _bul(kirmizi, "K2-sigma")[0].kaynak == "ders hedefi")
    for n, beklenen in ((500, ("uyari", "karsilanmadi")), (3000, ("bilgi", "bilgi")),
                        (5000, ("bilgi", "karsilandi"))):
        d = _kopya(h5={"n_particles": np.int64(n)})
        try:
            kontrol("parcacik %d -> %s" % (n, beklenen), _durum(_denetle(d), "K2-parcacik")
                    == beklenen)
        finally:
            shutil.rmtree(d, True)
    kontrol("aktif 25 < 100 -> uyari", _durum(_denetle(FIXTURE, (P.uyarla(A, aktif_asgari=100),)),
                                              "K2-aktif") == ("uyari", "karsilanmadi"))
    kontrol("aktif 25 >= 20 -> karsilandi", _durum(_denetle(
        FIXTURE, (P.uyarla(A, aktif_asgari=20),)), "K2-aktif") == ("bilgi", "karsilandi"))
    kg = np.full(40, 1.18)
    kg[15:] = 1.18 + 0.01 * np.sin(np.arange(25) / 4.0)            # yavas salinim: ilintili
    d = _kopya(h5={"k_generation": kg})
    try:
        kontrol("ilintili dizi -> bilgi/karsilanmadi", _durum(_denetle(d), "K2-ilinti")
                == ("bilgi", "bilgi"))
    finally:
        shutil.rmtree(d, True)
    kg[15:] = 1.18 + 0.01 * (-1.0) ** np.arange(25)                 # ters ilinti
    d = _kopya(h5={"k_generation": kg})
    try:
        kontrol("ilintisiz -> karsilandi", _durum(_denetle(d), "K2-ilinti") == ("bilgi", "karsilandi"))
    finally:
        shutil.rmtree(d, True)
    from cekirdek.uygunluk_denetimi.kurallar_mc import gecikme1_ilinti
    kontrol("ilinti tanimsiz -> None", gecikme1_ilinti([1.0, 1.0, 1.0]) is None
            and gecikme1_ilinti([1.0]) is None)


@gereksinim("R-S-04")
def test_k3_kayip_parcacik():
    print("\n[U6] K3: kayip parcacik kirmizi -> yesil; log yok; OpenMC ERROR")
    temiz = _denetle(FIXTURE)
    kontrol("yesil: fixture kayipsiz", _durum(temiz, "K3") == ("bilgi", "karsilandi"))
    kontrol("fixture Zr96 uyarilari bilgi (alarm degil)", _durum(temiz, "K3-uyari")
            == ("bilgi", "bilgi"))
    d = _kopya(log_ek=KAYIP_UYARISI + KAFES_UYARISI)
    try:
        b = _bul(_denetle(d), "K3")[0]
        kontrol("kirmizi: 2 kayip -> hata", (b.seviye, b.durum) == ("hata", "karsilanmadi")
                and "2 kayıp" in b.mesaj, "-> %s" % b.mesaj)
    finally:
        shutil.rmtree(d, True)
    d = _kopya(log_sil=True)
    try:
        kontrol("log yok -> uygulanamadi", _durum(_denetle(d), "K3") == ("bilgi", "uygulanamadi"))
        open(os.path.join(d, "particle_3_1.h5"), "w").close()
        kontrol("log yok ama restart var -> hata", _durum(_denetle(d), "K3")
                == ("hata", "karsilanmadi"))
    finally:
        shutil.rmtree(d, True)
    d = _kopya(log_ek=" ERROR: No fission sites banked on MPI rank 0\n")
    try:
        kontrol("OpenMC ERROR -> K3-hata", _durum(_denetle(d), "K3-hata") == ("hata", "karsilanmadi"))
    finally:
        shutil.rmtree(d, True)


# ----------------------------------------------------------------------------
# Profil B
# ----------------------------------------------------------------------------

@gereksinim("R-S-07")
def test_k6_usl():
    print("\n[U7] K6: V&V yok -> 'USL hesaplanamadi'; k + 2σ < USL kati esitsizlik")
    b = _bul(_denetle(FIXTURE, ("B",)), "K6")[0]
    kontrol("V&V yok -> uygulanamadi + durust metin", b.durum == "uygulanamadi"
            and "USL hesaplanamadı" in b.mesaj and "kanıtı değildir" in b.mesaj)
    b = _bul(_denetle(FIXTURE, ("B",), vv=_vv(usl=None, usl_neden="n < 10")), "K6")[0]
    kontrol("usl None -> neden gosterilir", b.durum == "uygulanamadi" and "n < 10" in b.mesaj)
    from cekirdek.uygunluk_denetimi.ayristir import kosu_verisi
    kv = kosu_verisi(FIXTURE)[0]
    esit = kv.keff + 2 * kv.sigma                  # statepoint'teki tam degerler
    kontrol("k + 2σ = USL -> hata (kati <)", _durum(_denetle(FIXTURE, ("B",), vv=_vv(usl=esit)),
                                                     "K6") == ("hata", "karsilanmadi"))
    kontrol("k + 2σ = USL + ε -> hata", _durum(_denetle(FIXTURE, ("B",), vv=_vv(usl=esit - 1e-6)),
                                                "K6") == ("hata", "karsilanmadi"))
    kontrol("k + 2σ = USL − ε -> karsilandi", _durum(_denetle(FIXTURE, ("B",), vv=_vv(usl=esit + 1e-6)),
                                                  "K6") == ("bilgi", "karsilandi"))
    d = _kopya(h5={"run_mode": __import__("numpy").bytes_(b"fixed source")})
    try:
        kontrol("sabit kaynak -> uygulanamadi", _durum(_denetle(d, ("B",), vv=_vv()), "K6")
                == ("bilgi", "uygulanamadi"))
    finally:
        shutil.rmtree(d, True)


@gereksinim("R-S-08")
def test_k8_k9_k10_k11():
    print("\n[U8] K8 pozitif yanlilik, K9 normallestirme, K10 vaka/guven, K11 ΔSM")
    from cekirdek.uygunluk_denetimi import profiller as P
    kontrol("K8 kirmizi", _durum(_denetle(FIXTURE, ("B",), vv=_vv(bias=0.003, bias_kullanilan=0.003)),
                                 "K8") == ("hata", "karsilanmadi"))
    kontrol("K8 yesil", _durum(_denetle(FIXTURE, ("B",), vv=_vv(bias=0.003, bias_kullanilan=0.0)),
                               "K8") == ("bilgi", "karsilandi"))
    kontrol("K9 kirmizi", _durum(_denetle(FIXTURE, ("B",), vv=_vv(normallestirildi=False)), "K9")
            == ("uyari", "karsilanmadi"))
    kontrol("K9 yesil", _durum(_denetle(FIXTURE, ("B",), vv=_vv()), "K9") == ("bilgi", "karsilandi"))
    kontrol("K10 n=5 uyari, n=9 uyari, n=10 yesil", [
        _durum(_denetle(FIXTURE, ("B",), vv=_vv(n=n)), "K10") for n in (5, 9, 10)]
        == [("uyari", "karsilanmadi")] * 2 + [("bilgi", "karsilandi")])
    npo = dict(yontem="parametrik_olmayan", n=12)
    kontrol("K10 β=0.40 iken USL verilmis -> hata", _durum(_denetle(
        FIXTURE, ("B",), vv=_vv(guven=0.40, **npo)), "K10-guven") == ("hata", "karsilanmadi"))
    kontrol("K10 β=0.72 -> guven bulgusu yok", not _bul(_denetle(
        FIXTURE, ("B",), vv=_vv(guven=0.7226, **npo)), "K10-guven"))
    kontrol("K10 β bildirilmedi -> uyari", _durum(_denetle(
        FIXTURE, ("B",), vv=_vv(guven=None, **npo)), "K10-guven") == ("uyari", "karsilanmadi"))
    B = P.profil_getir("B")
    kontrol("K11 profil ΔSM 0.01 -> hata", _durum(_denetle(FIXTURE, (P.uyarla(B, delta_sm=0.01),)),
                                                   "K11") == ("hata", "karsilanmadi"))
    kontrol("K11 varsayilan 0.05 -> karsilandi", _durum(_denetle(FIXTURE, ("B",)), "K11")
            == ("bilgi", "karsilandi"))
    kontrol("K11 V&V ΔSM 0.019 -> hata", _durum(_denetle(FIXTURE, ("B",), vv=_vv(delta_sm=0.019)),
                                                 "K11") == ("hata", "karsilanmadi"))
    kontrol("K11 ΔSM None -> uygulanamadi", _durum(_denetle(
        FIXTURE, (P.uyarla(B, delta_sm=None),)), "K11") == ("bilgi", "uygulanamadi"))


@gereksinim("R-S-09")
def test_k12_k6aoa_k13_k14():
    print("\n[U9] K12 dis degerleme, K6-AOA kategorik, K13 egilim/normallik, K14 seri")
    def k12(uyg, **vv):
        return [(b.seviye, b.durum) for b in _bul(_denetle(FIXTURE, ("B",), vv=_vv(**vv),
                                                           uygulama=uyg), "K12")]
    kontrol("icinde -> karsilandi", k12({"zenginlik": 4.0}) == [("bilgi", "karsilandi")])
    kontrol("%12 disarida -> uyari (genislet)", k12({"zenginlik": 5.36}) == [("uyari", "karsilanmadi")])
    kontrol("%5 disarida, ΔAOA=0 -> uyari", k12({"zenginlik": 5.15}) == [("uyari", "karsilanmadi")])
    kontrol("%5 disarida, ΔAOA>0 -> bilgi", k12({"zenginlik": 5.15}, delta_aoa=0.01)
            == [("bilgi", "bilgi")])
    kontrol("tolerans siniri dis degerleme -> hata",
            k12({"zenginlik": 5.15}, yontem="tolerans_siniri", egilim={}) == [("hata", "karsilanmadi")])
    kontrol("parametre yok -> uygulanamadi", k12({}) == [("bilgi", "uygulanamadi")])
    aoa = lambda t: _durum(_denetle(FIXTURE, ("B",), vv=_vv(), uygulama={"tayf": t}), "K6-AOA")
    kontrol("K6-AOA hizli ∉ {termal} -> uyari; termal -> yesil",
            aoa("hizli") == ("uyari", "karsilanmadi") and aoa("termal") == ("bilgi", "karsilandi"))
    kontrol("K6-AOA uygulama yok -> uygulanamadi", _durum(_denetle(FIXTURE, ("B",), vv=_vv()),
                                                           "K6-AOA") == ("bilgi", "uygulanamadi"))
    k13 = lambda kod, **vv: _durum(_denetle(FIXTURE, ("B",), vv=_vv(**vv)), kod)
    kontrol("K13 normal degil + parametrik -> hata",
            k13("K13-normallik", normallik={"test": "shapiro", "normal": False}) == ("hata", "karsilanmadi"))
    kontrol("K13 normal degil + parametrik olmayan -> yesil", k13(
        "K13-normallik", normallik={"normal": False}, yontem="parametrik_olmayan", guven=0.72)
        == ("bilgi", "karsilandi"))
    kontrol("K13 normallik yok -> uyari", k13("K13-normallik", normallik=None) == ("uyari", "karsilanmadi"))
    kontrol("K13 egilim + tolerans siniri -> uyari", k13("K13-egilim", yontem="tolerans_siniri")
            == ("uyari", "karsilanmadi"))
    kontrol("K13 egilim + bant -> yesil", k13("K13-egilim") == ("bilgi", "karsilandi"))
    kontrol("K13 egilim yok -> uyari", k13("K13-egilim", egilim={}) == ("uyari", "karsilanmadi"))
    kontrol("K14 tek seriden 10 vaka -> bilgi", k13("K14", seriler={"LCT-008": 10})
            == ("bilgi", "bilgi"))
    kontrol("K14 bagimsiz -> yesil", k13("K14") == ("bilgi", "karsilandi"))
    try:
        _vv(yontem="yok")
        kontrol("bilinmeyen yontem ValueError", False)
    except ValueError:
        kontrol("bilinmeyen yontem ValueError", True)


# ----------------------------------------------------------------------------
# Profil C
# ----------------------------------------------------------------------------

def _kats(e, s=0.1, birim="pcm/K"):
    return {"egim": e, "egim_sapma": s, "birim": birim}


@gereksinim("R-S-10")
def test_k7_katsayilar():
    print("\n[U10] K7 GDC 11: pozitif MTC HATA DEGIL; pozitif guc katsayisi HATA")
    kor = {"katsayilar": {"yakit_sicaklik": _kats(-2.5), "sogutucu_sicaklik": _kats(+3.0)}}
    b = _denetle(FIXTURE, ("C",), kor=kor)
    kontrol("pozitif MTC -> bilgi (alarm degil)", _durum(b, "K7-sogutucu_sicaklik") == ("bilgi", "bilgi"))
    kontrol("negatif Doppler -> karsilandi", _durum(b, "K7-yakit_sicaklik") == ("bilgi", "karsilandi"))
    kontrol("guc katsayisi yok -> bilgi notu", _durum(b, "K7-guc") == ("bilgi", "karsilanmadi"))
    kirmizi = _denetle(FIXTURE, ("C",), kor={"katsayilar": {"guc": _kats(+5.0, 1.0, "pcm/%")}})
    yesil = _denetle(FIXTURE, ("C",), kor={"katsayilar": {"guc": _kats(-5.0, 1.0, "pcm/%")}})
    kontrol("kirmizi: pozitif guc -> hata", _durum(kirmizi, "K7-guc") == ("hata", "karsilanmadi"))
    kontrol("yesil: negatif guc -> karsilandi", _durum(yesil, "K7-guc") == ("bilgi", "karsilandi"))
    kontrol("guc anlamsiz -> uyari", _durum(_denetle(FIXTURE, ("C",), kor={
        "katsayilar": {"guc": _kats(0.5, 1.0)}}), "K7-guc") == ("uyari", "karsilanmadi"))
    kontrol("pozitif Doppler -> uyari", _durum(_denetle(FIXTURE, ("C",), kor={
        "katsayilar": {"yakit_sicaklik": _kats(2.0)}}), "K7-yakit_sicaklik") == ("uyari", "karsilanmadi"))
    kontrol("katsayi yok -> uygulanamadi", _durum(_denetle(FIXTURE, ("C",)), "K7")
            == ("bilgi", "uygulanamadi"))
    from cekirdek.uygunluk_denetimi import profiller as P
    ar = P.uyarla(P.profil_getir("C"), reaktor_turu="arastirma")
    kontrol("arastirma reaktoru -> SSR-3 kaynagi", "SSR-3" in _bul(
        _denetle(FIXTURE, (ar,), kor=kor), "K7-yakit_sicaklik")[0].kaynak)
    # uygunluk_girdisi.json uzerinden (CLI yolu)
    d = _kopya()
    try:
        with open(os.path.join(d, "uygunluk_girdisi.json"), "w", encoding="utf-8") as f:
            json.dump({"kor": {"katsayilar": {"guc": _kats(+5.0, 1.0)}}}, f)
        kontrol("girdi dosyasindan pozitif guc -> hata", _durum(_denetle(d, ("C",)), "K7-guc")
                == ("hata", "karsilanmadi"))
        with open(os.path.join(d, "uygunluk_girdisi.json"), "w", encoding="utf-8") as f:
            f.write("[1, 2")
        try:
            _denetle(d, ("C",))
            kontrol("bozuk girdi dosyasi ValueError", False)
        except ValueError:
            kontrol("bozuk girdi dosyasi ValueError", True)
    finally:
        shutil.rmtree(d, True)


@gereksinim("R-S-10")
def test_k7_kapatma_ve_faktorler():
    print("\n[U11] K7-SDM (N-1, kullanici siniri) ve K7-F (F_ΔH/F_q; varsayilan sinir YOK)")
    from cekirdek.uygunluk_denetimi import profiller as P
    C = P.profil_getir("C")
    sdm = {"deger_pcm": 1500.0, "sapma_pcm": 100.0, "en_degerli_cubuk_sikisik": True}
    kontrol("sinir yok -> uygulanamadi", _durum(_denetle(FIXTURE, ("C",), kor={"kapatma_marji": sdm}),
                                                "K7-SDM") == ("bilgi", "uygulanamadi"))
    s = lambda sinir, **kw: _durum(_denetle(FIXTURE, (P.uyarla(C, sdm_siniri_pcm=(sinir, "TS 3.1")),),
                                            kor={"kapatma_marji": dict(sdm, **kw)}), "K7-SDM")
    kontrol("kirmizi: 1500 < 1600 -> hata", s(1600) == ("hata", "karsilanmadi"))
    kontrol("2σ icinde -> uyari", s(1400) == ("uyari", "karsilanmadi"))
    kontrol("yesil: 1500 ≥ 1000 -> karsilandi", s(1000) == ("bilgi", "karsilandi"))
    b = _denetle(FIXTURE, (P.uyarla(C, sdm_siniri_pcm=1000),), kor={"kapatma_marji": {
        "deger_pcm": 1500.0}})
    kontrol("N-1 ve sigma belirtilmemis -> uyari", _durum(b, "K7-SDM-N1") == ("uyari", "karsilanmadi")
            and _durum(b, "K7-SDM-sigma") == ("uyari", "karsilanmadi"))
    kontrol("SDM yok -> uygulanamadi", _durum(_denetle(FIXTURE, ("C",)), "K7-SDM")
            == ("bilgi", "uygulanamadi"))
    f = _bul(_denetle(FIXTURE, ("C",)), "K7-FdH")
    kontrol("fixture F_ΔH statepoint'ten, sinir yok -> uygulanamadi",
            f and f[0].durum == "uygulanamadi" and "F_ΔH = " in f[0].mesaj, "-> %s" % f)
    fs = lambda sinir, kod="K7-FdH", ad="F_dH_siniri": _durum(
        _denetle(FIXTURE, (P.uyarla(C, **{ad: sinir}),)), kod)
    kontrol("kirmizi: F_ΔH > 1.0 -> hata", fs(1.0) == ("hata", "karsilanmadi"))
    kontrol("yesil: F_ΔH ≤ 3.0 -> karsilandi", fs(3.0) == ("bilgi", "karsilandi"))
    kontrol("F_q kirmizi/yesil", fs(1.0, "K7-Fq", "F_q_siniri") == ("hata", "karsilanmadi")
            and fs(9.0, "K7-Fq", "F_q_siniri") == ("bilgi", "karsilandi"))
    yakin = _denetle(FIXTURE, (P.uyarla(C, F_dH_siniri=1.51),), kor={
        "faktorler": {"F_dH": 1.50, "F_dH_sapma": 0.01}})
    kontrol("F_ΔH sinira 2σ icinde -> uyari", _durum(yakin, "K7-FdH") == ("uyari", "karsilanmadi"))
    d = _kopya()
    try:
        from cekirdek.uygunluk_denetimi import kurallar
        from cekirdek.uygunluk_denetimi.ayristir import KosuVerisi
        k = kurallar.kural_getir("K7-F")
        yok = k.islev(k, kurallar.Baglam(kosu=KosuVerisi(os.path.join(d, "yok.h5"), "eigenvalue",
                                                         1.0, 0.001, 1, 2, 1)))
        kontrol("okunamayan statepoint -> uyari", yok[0].seviye == "uyari")
        kontrol("kosu yok -> uygulanamadi", k.islev(k, kurallar.Baglam())[0].durum == "uygulanamadi")
    finally:
        shutil.rmtree(d, True)
    kontrol("K16 kirmizi -> yesil", _durum(_denetle(FIXTURE, ("C",)), "K16")
            == ("bilgi", "karsilanmadi") and _durum(_denetle(
                FIXTURE, ("C",), kor={"dogrulama": ["IRPhEP VVER-PHYS-REACTOR"]}), "K16")
            == ("bilgi", "karsilandi"))


# ----------------------------------------------------------------------------
# Profil D
# ----------------------------------------------------------------------------

@gereksinim("R-S-05")
def test_k4_izlenebilirlik():
    print("\n[U12] K4: sicakliksiz malzeme ve bilinmeyen kutuphane kirmizi; fixture tutarli")
    from cekirdek import rapor
    spec = _spec()
    b = _denetle(FIXTURE, ("D",), spec=spec)
    _alan, uyarilar = rapor.tekrarlanabilirlik(spec, FIXTURE)
    k4 = [x for x in b if x.kural.startswith("K4")]
    if uyarilar:
        kontrol("yesil: K4 alarmi = rapor uyarilari", len(k4) == len(uyarilar), "-> %s" % uyarilar)
    else:
        kontrol("yesil: fixture K4 karsilandi", _durum(b, "K4") == ("bilgi", "karsilandi"),
                "-> %s" % [x.mesaj for x in k4])
    kirik = copy.deepcopy(spec)
    kirik["malzemeler"][0]["sicaklik"] = None
    b = _denetle(FIXTURE, ("D",), spec=kirik)
    kontrol("kirmizi: sicakliksiz malzeme -> uyari", _durum(b, "K4-sicaklik") == ("uyari", "karsilanmadi"))
    kontrol("spec degismedi (girdi)", kirik["malzemeler"][0]["sicaklik"] is None
            and spec["malzemeler"][0]["sicaklik"] == 900.0)
    d = _kopya(log_sil=True)
    eski = os.environ.pop("OPENMC_CROSS_SECTIONS", None)
    try:
        b = _denetle(d, ("D",))                         # spec kosu dizininden okunur
        kontrol("kirmizi: log + ortam yok -> kutuphane bilinmiyor uyarisi", any(
            x.kural == "K4" and x.seviye == "uyari" and "kütüphanesi" in x.mesaj for x in b))
    finally:
        if eski is not None:
            os.environ["OPENMC_CROSS_SECTIONS"] = eski
        shutil.rmtree(d, True)
    kontrol("spec yok -> uygulanamadi", _durum(_denetle(tempfile.gettempdir(), ("D",)), "K4")
            == ("bilgi", "uygulanamadi"))


UYGUN_METIN = ("k-eff = %s — belirsizlik 1σ standart belirsizliktir. Reaktivite +15400 ± 21 pcm; "
               "pcm = Δρ × 10⁵. Yükseklik 365.76 cm.")


@gereksinim("R-S-06")
def test_k5_belirsizlik():
    print("\n[U13] K5: 1σ etiketi, 2 anlamli rakam, yuvarlama, pcm tanimi, SI")
    from cekirdek.uygunluk_denetimi.kurallar_rapor import belirsizlik_metni, pcm_tanimi
    kontrol("belirsizlik_metni", belirsizlik_metni(1.18218, 0.00286) == "1.1822 ± 0.0029 (1σ)"
            and belirsizlik_metni(1.0, 0.00996) == "1.000 ± 0.010 (1σ)"
            and belirsizlik_metni(15432.0, 123.0) == "(154.3 ± 1.2) × 10² (1σ)"
            and belirsizlik_metni(15432.0, 23.0, birim="pcm") == "15432 ± 23 pcm (1σ)"
            and belirsizlik_metni(2.5, 0) == "2.5", "-> %s" % belirsizlik_metni(1.0, 0.00996))
    kontrol("pcm tanimlari", "Δk" in pcm_tanimi("dk") and "Δρ" in pcm_tanimi())
    yesil = _denetle(FIXTURE, ("D",), spec=_spec(),
                     rapor_metni=UYGUN_METIN % belirsizlik_metni(1.18218, 0.00286))
    kontrol("yesil: uygun metin karsilandi", _durum(yesil, "K5") == ("bilgi", "karsilandi"),
            "-> %s" % [x.mesaj for x in _bul(yesil, "K5")])
    kirmizi = _denetle(FIXTURE, ("D",), spec=_spec(), rapor_metni=(
        "<p>k-eff = <b>1.18218 &plusmn; 0.00286</b></p><p>F = 1.2 ± 0.0351</p>"
        "<p>ρ = +15432 ± 123 pcm; k = 1.182 ± 0.0029</p><p>boy 12 ft, 550 °F</p>"))
    for kod in ("K5-etiket", "K5-rakam", "K5-yuvarlama", "K5-pcm", "K5-SI"):
        kontrol("kirmizi: %s -> uyari" % kod, _durum(kirmizi, kod) == ("uyari", "karsilanmadi"))
    kontrol("yuzde belirsizlik yuvarlama saymaz", not _bul(_denetle(
        FIXTURE, ("D",), spec=_spec(), rapor_metni="a = 1.2345e-03 ± 1.2% (1σ)"), "K5-yuvarlama"))
    kontrol("rapor yok -> uygulanamadi", _durum(_denetle(FIXTURE, ("D",), spec=_spec()), "K5")
            == ("bilgi", "uygulanamadi"))
    d = _kopya()
    try:
        with open(os.path.join(d, "rapor.html"), "w", encoding="utf-8") as f:
            f.write("<p>k = 1.18218 ± 0.00286</p>")
        kontrol("kosu dizinindeki rapor.html denetlenir", _durum(_denetle(d, ("D",)), "K5-rakam")
                == ("uyari", "karsilanmadi"))
    finally:
        shutil.rmtree(d, True)


# ----------------------------------------------------------------------------
# API, profiller, yanlis alarm
# ----------------------------------------------------------------------------

@gereksinim("R-S-01")
def test_api_sozlesmesi():
    print("\n[U14] denetle API: Bulgu alt sinifi, alanlar, ozet, kural istisnasi, profil hatasi")
    from cekirdek import dogrula
    from cekirdek.uygunluk_denetimi import denetle as D, kurallar
    spec = _spec()
    once = json.dumps(spec, sort_keys=True)
    b = D.denetle(spec, FIXTURE, ("A", "B", "C", "D"))
    kontrol("spec degismedi", json.dumps(spec, sort_keys=True) == once)
    kontrol("hepsi Bulgu alt sinifi + alanlar", all(
        isinstance(x, dogrula.Bulgu) and x.kural and x.kaynak and x.etiket and x.profil
        and x.durum in kurallar.DURUMLAR for x in b))
    kontrol("her kural en az bir bulgu", {x.kural.split("-")[0] for x in b} >= {
        "K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8", "K9", "K10", "K11", "K12", "K13", "K14", "K16"})
    kontrol("K1-K3 iyi uygulama etiketli", all(x.etiket == kurallar.IYI_UYGULAMA for x in b
                                               if x.profil == "A"))
    o = D.ozet(b)
    kontrol("ozet sayilari", sum(o["seviye"].values()) == len(b) == sum(o["durum"].values()))
    kontrol("sorunlar/alarmlar alt kume", set(D.alarmlar(b)) <= set(b) and all(
        x.durum == "karsilanmadi" for x in D.sorunlar(b)))
    kontrol("sozluk JSON'a yazilir", json.loads(json.dumps(b[0].sozluk()))["kural"] == b[0].kural)
    kontrol("str/repr", "uygunluk:" in str(b[0]) and "DenetimBulgusu" in repr(b[0]))
    kontrol("varsayilan profil A", {x.profil for x in D.denetle(None, FIXTURE)} == {"A"})
    try:
        D.denetle(None, FIXTURE, ("Z",))
        kontrol("bilinmeyen profil ValueError", False)
    except ValueError as e:
        kontrol("bilinmeyen profil ValueError", "Z" in str(e))
    patlak = kurallar.Kural("KX", "A", "x", "x", kurallar.IYI_UYGULAMA,
                            lambda k, b: 1 / 0)
    sonuc = D._kurali_isle(patlak, kurallar.Baglam())
    kontrol("kural istisnasi -> hata bulgusu", sonuc[0].seviye == "hata"
            and "ZeroDivisionError" in sonuc[0].mesaj)
    kontrol("etiket metni", "iyi uygulama" in kurallar.etiket_metni(kurallar.IYI_UYGULAMA))
    try:
        kurallar.kural_getir("K99")
        kontrol("kural_getir KeyError", False)
    except KeyError:
        kontrol("kural_getir KeyError", True)
    d = _kopya()
    try:
        with open(os.path.join(d, "spec.json"), "w") as f:
            f.write("{bozuk")
        kontrol("bozuk spec.json -> spec None, K4 uygulanamadi", _durum(D.denetle(None, d, ("D",)),
                                                                         "K4")[1] == "uygulanamadi")
    finally:
        shutil.rmtree(d, True)


def test_profiller():
    print("\n[U15] profiller: her esik kaynakli; uyarla/dosyadan_uyarla degismez kopya")
    from cekirdek.uygunluk_denetimi import profiller as P
    kontrol("her varsayilan esikte kaynak var", all(
        e.kaynak for p in P.VARSAYILAN.values() for e in p.esikler.values()))
    kontrol("C'de varsayilan sinir YOK", all(P.profil_getir("C").esikler[a].deger is None
                                            for a in ("F_dH_siniri", "F_q_siniri", "sdm_siniri_pcm")))
    kontrol("K6 carpani 2, ΔSM alt siniri 0.02", P.profil_getir("B").esikler["kabul_carpani"].deger == 2.0
            and P.profil_getir("B").esikler["delta_sm_asgari"].deger == 0.02)
    C = P.profil_getir("C")
    yeni = P.uyarla(C, F_dH_siniri=1.55)
    kontrol("uyarla yeni kopya, kaynak belirtilmedi notu", C.esikler["F_dH_siniri"].deger is None
            and yeni.esikler["F_dH_siniri"].deger == 1.55
            and "kaynak belirtilmedi" in yeni.esikler["F_dH_siniri"].kaynak)
    try:
        P.uyarla(C, F_dh_siniri=1.5)
        kontrol("yazim hatasi ValueError", False)
    except ValueError:
        kontrol("yazim hatasi ValueError", True)
    d = tempfile.mkdtemp()
    try:
        yol = os.path.join(d, "profil.json")
        with open(yol, "w", encoding="utf-8") as f:
            json.dump({"C": {"F_q_siniri": {"deger": 2.5, "kaynak": "TS 3.2.1"}}}, f)
        p = P.dosyadan_uyarla(yol)
        kontrol("dosyadan_uyarla", p["C"].esikler["F_q_siniri"] == P.Esik(2.5, "TS 3.2.1", "")
                and p["A"] is P.VARSAYILAN["A"])
        for icerik in ("[1]", "{bozuk"):
            with open(yol, "w") as f:
                f.write(icerik)
            try:
                P.dosyadan_uyarla(yol)
                kontrol("bozuk profil dosyasi ValueError %s" % icerik, False)
            except ValueError:
                kontrol("bozuk profil dosyasi ValueError %s" % icerik, True)
    finally:
        shutil.rmtree(d, True)
    kontrol("durust cerceve metni", "sertifika vermez" in P.durust_cerceve())
    kontrol("gorunen ad", P.profil_getir("A").gorunen_ad() == "Monte Carlo iyi uygulaması")
    kontrol("Esik nesnesi aynen", P.uyarla(C, F_q_siniri=P.Esik(2.0, "x")).esikler[
        "F_q_siniri"].kaynak == "x")


@gereksinim("R-S-11")
def test_yanlis_alarm_ornekler():
    print("\n[U16] Yanlis alarm: kayitli kosu dizinleri A profilinde alarmsiz (hata/uyari 0)")
    from cekirdek.uygunluk_denetimi import denetle as D
    dizinler = [FIXTURE] + sorted(d for d in glob.glob(os.path.join(KOK, "ornekler", "kosu*"))
                                  if os.path.isdir(d))
    for d in dizinler:
        alarm = D.alarmlar(D.denetle(None, d, ("A",)))
        if d == FIXTURE:   # fixture'in entropisi aktifte kayar: K1 alarmi GERCEKTIR (QA14-Q4)
            alarm = [x for x in alarm if x.kural != "K1"]
        kontrol("%s alarmsiz" % os.path.relpath(d, KOK), not alarm,
                "-> %s" % [(x.kural, x.mesaj) for x in alarm])
    print("  (%d kosu dizini denetlendi; ornekler/kosu* git'te yoktur, varsa denetlenir)"
          % len(dizinler))


HIZLI = [test_ayristir_log, test_kosucu_kayip_parcacik, test_k1_entropi,
         test_k1_entropi_kapali_ve_bozuk, test_k2_istatistik, test_k3_kayip_parcacik,
         test_k6_usl, test_k8_k9_k10_k11, test_k12_k6aoa_k13_k14, test_k7_katsayilar,
         test_k7_kapatma_ve_faktorler, test_k4_izlenebilirlik, test_k5_belirsizlik,
         test_api_sozlesmesi, test_profiller, test_yanlis_alarm_ornekler]
YAVAS = []
