# -*- coding: utf-8 -*-
"""
 test_tarama_kapsam.py  --  tarama.py ve kritik_arama.py (Monte Carlo'suz)

 kosucu.calistir / kosucu.sonuc_oku taklit edilir: her nokta icin k(x)
 analitik bir fonksiyondan gelir (MC yok, nukleer veri yok). Boylece
 parametre uygulama, katsayi, tarama dongusu (basari, basarisizlik, istisna,
 durdurma), kritik aramanin butun dallari ve iki terminal girisi sinanir.
 Istisnalar loglanir (sessiz hata yok: test_hata_yutma IZINLI'den
 cekirdek.tarama:calistir silindi).

 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import contextlib
import io
import logging
import os
import tempfile

from testler.ortak_test import kontrol, ORNEK


# ============================================================================
# TAKLIT KOSUCU
# ============================================================================

class _SahteKosucu(object):
    """kosucu.calistir + sonuc_oku yerine: k = k_fonk(spec). Istenirse
    belirli cagrilarda basarisiz kosu ya da istisna uretir."""

    def __init__(self, k_fonk, sigma=0.0005, basarisiz=(), istisna=()):
        self.k_fonk, self.sigma = k_fonk, sigma
        self.basarisiz, self.istisna = set(basarisiz), set(istisna)
        self.cagri = 0
        self.specler = []

    def calistir(self, spec, dizin, is_parcacigi=None, **_k):
        i = self.cagri
        self.cagri += 1
        self.specler.append(spec)
        if i in self.istisna:
            raise RuntimeError("sahte kosu istisnasi %d" % i)
        if i in self.basarisiz:
            return {"basarili": False, "cikis_kodu": 3, "statepoint": None,
                    "log": os.path.join(dizin, "openmc.log")}
        return {"basarili": True, "cikis_kodu": 0, "statepoint": ("sp", len(self.specler) - 1),
                "log": ""}

    def sonuc_oku(self, sp):
        spec = self.specler[sp[1]]
        return {"keff": (self.k_fonk(spec), self.sigma), "entropi": [1.0, 1.0],
                "pasif": 10}


@contextlib.contextmanager
def _taklit(sahte):
    from cekirdek import kosucu
    eski = kosucu.calistir, kosucu.sonuc_oku
    kosucu.calistir, kosucu.sonuc_oku = sahte.calistir, sahte.sonuc_oku
    try:
        yield sahte
    finally:
        kosucu.calistir, kosucu.sonuc_oku = eski


@contextlib.contextmanager
def _log_yakala(ad):
    kayitlar = []

    class _Tutucu(logging.Handler):
        def emit(self, kayit):
            kayitlar.append(kayit)
    t = _Tutucu(level=logging.DEBUG)
    lg = logging.getLogger("openmc_arayuz." + ad)
    lg.addHandler(t)
    try:
        yield kayitlar
    finally:
        lg.removeHandler(t)


def _yukle(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _bor_wo(spec):
    """Su malzemesindeki bor agirlik yuzdesi."""
    from cekirdek import sema
    m = sema.malzeme_bul(spec, "su")
    return sum(x.get("miktar", 0.0) for x in m["bilesim"] if x.get("isim") == "B")


def _bor(spec):
    """Sahte k: bor arttikca dogrusal duser (0.1 wo = 1000 ppm -> -5000 pcm)."""
    return 1.10 - 0.5 * _bor_wo(spec)


def _cikti(fonk, *a):
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        kod = fonk(*a)
    return kod, tampon.getvalue()


# ============================================================================
# tarama.py
# ============================================================================

def test_parametre_uygula_turleri():
    print("\n[TK1] tarama.parametre_uygula: her tur, girdi degismez, hatalar")
    import copy
    from cekirdek import tarama, sema
    s = _yukle("pwr_kontrol")
    once = copy.deepcopy(s)
    y, n = tarama.parametre_uygula(s, "yakit_sicaklik", "uo2", 1200.0)
    kontrol("yakit sicakligi", sema.malzeme_bul(y, "uo2")["sicaklik"] == 1200.0 and n is None)
    y, n = tarama.parametre_uygula(s, "sogutucu_sicaklik", "su", 580.0)
    kontrol("su sicakligi + yogunluk korelasyonu",
            sema.malzeme_bul(y, "su")["yogunluk"]["deger"] < 0.75 and n is None)
    y, n = tarama.parametre_uygula(s, "sogutucu_sicaklik", "zirkaloy4", 600.0)
    kontrol("korelasyonsuz malzeme -> not", n and "korelasyon" in n)
    y, _n = tarama.parametre_uygula(s, "malzeme_yogunluk", "su", 0.5)
    kontrol("yogunluk", sema.malzeme_bul(y, "su")["yogunluk"]["deger"] == 0.5)
    y, _n = tarama.parametre_uygula(s, "void_orani", "su", 40.0)
    rho0 = sema.malzeme_bul(s, "su")["yogunluk"]["deger"]
    kontrol("void %40", abs(sema.malzeme_bul(y, "su")["yogunluk"]["deger"] - 0.6 * rho0) < 1e-12)
    y, _n = tarama.parametre_uygula(s, "bor_ppm", "su", 500.0)
    kontrol("bor ppm bilesime girer (500 ppm = 0.05 wo)", abs(_bor_wo(y) - 0.05) < 1e-9,
            "-> %s" % _bor_wo(y))
    y, _n = tarama.parametre_uygula(s, "zenginlik", "uo2", 4.5)
    kontrol("zenginlik", sema.malzeme_bul(y, "uo2")["bilesim"][0]["zenginlik"] == 4.5)
    y, _n = tarama.parametre_uygula(s, "kafes_adim", s["kor"]["demet"], 1.3)
    kontrol("demet adimi", sema.demet_bul(y, s["kor"]["demet"])["adim"] == 1.3)
    y, _n = tarama.parametre_uygula(s, "kor_adim", None, 2.0)
    kontrol("kor adimi", y["kor"]["adim"] == 2.0)
    y, _n = tarama.parametre_uygula(s, "cubuk_daldirma", "kontrol_cubugu", 50.0)
    kontrol("daldirma", sema.cubuk_bul(y, "kontrol_cubugu")["daldirma"] == 50.0)
    y, _n = tarama.parametre_uygula(s, "cubuk_yaricap", ("yakit_cubugu", 0), 0.40)
    kontrol("yaricap", sema.cubuk_bul(y, "yakit_cubugu")["bolgeler"][0]["r"] == 0.40)
    y, _n = tarama.parametre_uygula(s, "yansitici_kalinlik", None, 15.0)
    kontrol("yansitici", y["kor"]["yansitici"] == dict(y["kor"]["yansitici"], var=True,
                                                     kalinlik=15.0))
    t = _yukle("tamburlu_kor")
    y, _n = tarama.parametre_uygula(t, "tambur_donme", None, 90.0)
    kontrol("tambur donme", y["kor"]["tambur"]["donme"] == 90.0)
    kontrol("girdi spec degismedi", s == once)
    _parametre_hatalari(s)


def _parametre_hatalari(s):
    from cekirdek import tarama
    hatalar = [("yakit_sicaklik", "yok", 1.0, KeyError), ("sogutucu_sicaklik", "yok", 1.0, KeyError),
               ("void_orani", "su", 150.0, ValueError), ("zenginlik", "su", 3.0, ValueError),
               ("kafes_adim", "yok", 1.0, KeyError), ("cubuk_daldirma", "yok", 1.0, KeyError),
               ("cubuk_daldirma", "yakit_cubugu", 1.0, ValueError),
               ("cubuk_daldirma", "kontrol_cubugu", 120.0, ValueError),
               ("cubuk_yaricap", ("yok", 0), 1.0, KeyError),
               ("tambur_donme", None, 1.0, ValueError), ("uydurma", None, 1.0, ValueError)]
    for tur, hedef, deger, beklenen in hatalar:
        try:
            tarama.parametre_uygula(s, tur, hedef, deger)
            olan = None
        except (KeyError, ValueError) as e:
            olan = type(e)
        kontrol("hata: %s(%s, %s) -> %s" % (tur, hedef, deger, beklenen.__name__),
                olan is beklenen, "-> %s" % olan)


def test_korelasyon_noktalar_reaktivite():
    print("\n[TK2] yogunluk korelasyonlari, noktalar, reaktivite")
    from cekirdek import tarama
    su = {"ad": "su", "bilesim": [{"isim": "H"}, {"isim": "O"}]}
    lbe = {"ad": "lbe", "bilesim": [{"isim": "Pb"}, {"isim": "Bi"}]}
    na = {"ad": "na", "bilesim": [{"isim": "Na"}]}
    f_su, _a = tarama._yogunluk_korelasyonu(su)
    f_lbe, _a = tarama._yogunluk_korelasyonu(lbe)
    f_na, _a = tarama._yogunluk_korelasyonu(na)
    kontrol("su 300 K ~ 0.996", abs(f_su(300.0) - 0.9965) < 0.002, "-> %s" % f_su(300.0))
    kontrol("LBE 700 K", abs(f_lbe(700.0) - (11096.0 - 1.3236 * 700) / 1000.0) < 1e-12)
    kontrol("Na 700 K", abs(f_na(700.0) - (1014.0 - 0.235 * 700) / 1000.0) < 1e-12)
    kontrol("bilinmeyen -> None + sebep",
            tarama._yogunluk_korelasyonu({"ad": "x", "bilesim": [{"isim": "Fe"}]})[0] is None)
    kontrol("noktalar 5", tarama.noktalar(0, 1, 5) == [0.0, 0.25, 0.5, 0.75, 1.0])
    kontrol("noktalar 1 -> bas", tarama.noktalar(2, 9, 1) == [2.0])
    r, s = tarama.reaktivite(1.25, 0.01)
    kontrol("rho(1.25) = 20000 pcm, sigma 640", abs(r - 20000) < 1e-9 and abs(s - 640) < 1e-9)
    r, s = tarama.reaktivite(0.0)
    kontrol("k <= 0 -> nan", r != r and s != s)


def test_katsayi_ve_yorum():
    print("\n[TK3] katsayi (agirlikli EKK) ve yorumlar")
    from cekirdek import tarama
    veri = [{"deger": x, "keff": 1.0 / (1.0 - (-10.0 * x) * 1e-5), "sapma": 1e-4}
            for x in (0.0, 10.0, 20.0, 30.0)]
    k = tarama.katsayi(veri)
    kontrol("egim -10 pcm/birim", k and abs(k["egim"] + 10.0) < 1e-6 and k["nokta"] == 4
            and abs(k["r2"] - 1.0) < 1e-9, "-> %s" % (k and k["egim"]))
    kontrol("tek nokta -> None", tarama.katsayi(veri[:1]) is None)
    kontrol("ayni x -> None (payda 0)",
            tarama.katsayi([dict(v, deger=1.0) for v in veri]) is None)
    kontrol("sapmasiz nokta atlanir",
            tarama.katsayi([dict(veri[0], sapma=0.0), veri[1]]) is None)
    kontrol("yorum: None", "hesaplanamadı" in tarama.yorumla("bor_ppm", None))
    kontrol("yorum: anlamsiz egim", "ayırt edilemiyor" in tarama.yorumla(
        "bor_ppm", {"egim": 0.1, "egim_sapma": 1.0}))
    for tur in list(tarama.TURLER) + ["uydurma"]:
        y = tarama.yorumla(tur, {"egim": -5.0, "egim_sapma": 0.1})
        if not y.startswith("Eğim negatif"):
            kontrol("yorum %s" % tur, False, "-> %s" % y)
    kontrol("yorum pozitif", tarama.yorumla("zenginlik", {"egim": 5.0, "egim_sapma": 0.1})
            .startswith("Eğim pozitif"))


def test_tarama_dongusu_taklit():
    print("\n[TK4] tarama.calistir: basari, basarisiz kosu, istisna (loglanir), durdurma")
    from cekirdek import tarama
    s = _yukle("pwr_17x17")
    kok = tempfile.mkdtemp(prefix="tk4_")
    cagrilar = []
    sahte = _SahteKosucu(_bor, basarisiz={1}, istisna={2})
    with _taklit(sahte), _log_yakala("cekirdek.tarama") as kayit:
        sonuclar, notlar = tarama.calistir(
            s, "bor_ppm", "su", [0.0, 500.0, 1000.0, 1500.0], kok,
            geri_cagir=lambda i, n, r: cagrilar.append((i, n, r.get("keff"))))
    kontrol("4 nokta, geri cagri 4", len(sonuclar) == 4 and len(cagrilar) == 4)
    kontrol("nokta 0 ve 3 basarili", sonuclar[0]["keff"] and sonuclar[3]["keff"]
            and sonuclar[3]["keff"] < sonuclar[0]["keff"])
    kontrol("basarisiz kosu -> cikis kodu metni", "çıkış kodu 3" in sonuclar[1]["hata"])
    kontrol("istisna -> hata alani", "istisnasi 2" in sonuclar[2]["hata"])
    kontrol("istisna LOGLANDI (sessiz degil)",
            any(k.levelno >= logging.ERROR and k.exc_info for k in kayit), "-> %d" % len(kayit))
    kontrol("nokta dizinleri", sonuclar[0]["dizin"].endswith("nokta_00"))
    kontrol("entropi ve pasif tasinir", sonuclar[0]["entropi"] == [1.0, 1.0]
            and sonuclar[0]["pasif"] == 10)
    k = tarama.katsayi(sonuclar)
    kontrol("iki basarili noktadan negatif bor katsayisi", k and k["egim"] < 0)
    with _taklit(_SahteKosucu(_bor)):
        sonuclar, notlar = tarama.calistir(s, "bor_ppm", "su", [0.0, 1.0, 2.0], kok,
                                           dur_bayragi=lambda: True)
    kontrol("durdurma: nokta yok, not var", sonuclar == [] and "durduruldu" in notlar[0])
    with _taklit(_SahteKosucu(lambda sp: 1.0)):
        _s, notlar = tarama.calistir(s, "sogutucu_sicaklik", "zirkaloy4", [500.0, 600.0], kok)
    kontrol("korelasyonsuz not bir kez", len(notlar) == 1 and "korelasyon" in notlar[0])


def test_tarama_terminal_taklit():
    print("\n[TK5] tarama._terminal: yardim, hatali secenek, eksik, bilinmeyen, tam kosu")
    from cekirdek import tarama
    yol = os.path.join(ORNEK, "pwr_17x17.json")
    kok = tempfile.mkdtemp(prefix="tk5_")
    kod, metin = _cikti(tarama._terminal, [])
    kontrol("yardim 0 + turler", kod == 0 and "TARAMA TÜRLERİ" in metin)
    kontrol("bilinmeyen secenek 2", _cikti(tarama._terminal, [yol, "--xyz", "1"])[0] == 2)
    kontrol("eksik zorunlu 2", _cikti(tarama._terminal, [yol, "--tur", "bor_ppm"])[0] == 2)
    kontrol("bilinmeyen tur 2", _cikti(tarama._terminal, [
        yol, "--tur", "yok", "--bas", "0", "--son", "1"])[0] == 2)
    with _taklit(_SahteKosucu(_bor, basarisiz={2})):
        kod, metin = _cikti(tarama._terminal, [
            yol, "--tur", "bor_ppm", "--hedef", "su", "--bas", "0", "--son", "1000",
            "--adet", "3", "--dizin", kok, "-s", "2"])
    kontrol("tam kosu 0, katsayi yazildi", kod == 0 and "Katsayı" in metin
            and "başarısız" in metin, metin[-300:])
    with _taklit(_SahteKosucu(lambda sp: 1.0, basarisiz={0, 1})):
        kod, metin = _cikti(tarama._terminal, [
            yol, "--tur", "cubuk_yaricap", "--hedef", "yakit_cubugu:0", "--bas", "0.40",
            "--son", "0.41", "--adet", "2", "--dizin", kok])
    kontrol("cubuk_yaricap hedef ayristirma, katsayi yok",
            kod == 0 and "hesaplanamadı" in metin, metin[-200:])


# ============================================================================
# kritik_arama.py
# ============================================================================

def _dogrusal(k0, egim, tur="bor_ppm"):
    """k = k0 + egim * x; x spec'ten tarama parametresine gore okunur."""
    from cekirdek import sema

    def fonk(spec):
        if tur == "yansitici_kalinlik":
            x = spec["kor"]["yansitici"]["kalinlik"]
        else:
            x = sema.malzeme_bul(spec, "su")["yogunluk"]["deger"]
        return k0 + egim * x
    return fonk


def _ara(k_fonk, alt, ust, sigma=0.0005, **k):
    from cekirdek import kritik_arama
    s = _yukle("pwr_17x17")
    sahte = _SahteKosucu(k_fonk, sigma=sigma, istisna=k.pop("istisna", ()))
    with _taklit(sahte):
        r = kritik_arama.ara(s, k.pop("tur", "malzeme_yogunluk"), k.pop("hedef", "su"),
                             alt, ust, tempfile.mkdtemp(prefix="ka_"), **k)
    return r, sahte


def test_kritik_arama_dallari():
    print("\n[KA1] kritik_arama.ara: parantez, uc, yakinsama, ikiye bolme, cozunurluk")
    # k = 0.6 + 0.5 rho: kok rho = 0.8
    r, _s = _ara(_dogrusal(0.6, 0.5), 0.5, 1.0)
    kontrol("dogrusal: yakinsadi, kok 0.8", r.basarili and abs(r.cozum - 0.8) < 0.01
            and "Yakınsadı" in r.mesaj, "-> %s %s" % (r.cozum, r.mesaj))
    kontrol("ozet metni", "Çözüm:" in r.ozet() and "yineleme" in r.ozet())
    r, _s = _ara(_dogrusal(0.6, 0.5), 0.9, 1.0)
    kontrol("aralikta degil -> mesaj, basarisiz",
            not r.basarili and "aralıkta değil" in r.mesaj and "büyük" in r.mesaj)
    kontrol("basarisiz ozet", r.ozet().startswith("Arama başarısız"))
    r, _s = _ara(_dogrusal(0.6, 0.5), 0.8, 1.0)
    kontrol("uc zaten hedefte", r.basarili and r.cozum == 0.8 and "ucu zaten" in r.mesaj)
    # dogrusal olmayan (basamak benzeri): sekant parantez disina / tekrar -> ikiye bol
    r, s = _ara(lambda sp: 0.9 if _dogrusal(0, 1)(sp) < 0.73 else 1.1, 0.5, 1.0,
                sigma=0.001, en_fazla=40)
    kontrol("basamak: cozunurluk siniri ya da en yakin nokta raporu",
            r.cozum is not None and len(r.adimlar) >= 3, "-> %s | %s" % (r.cozum, r.mesaj))
    # gurultulu buyuk sigma: parantez kok belirsizliginin altina iner
    r, _s = _ara(lambda sp: 0.6 + 0.5 * _dogrusal(0, 1)(sp) + 0.0, 0.5, 1.0, sigma=1e-9,
                 tolerans_sigma=1e-6, en_fazla=3)
    kontrol("en_fazla=3: en yakin nokta raporu", r.cozum is not None and len(r.adimlar) <= 5,
            "-> %s" % r.mesaj)


def test_kritik_arama_hatalar():
    print("\n[KA2] kritik_arama: kosu istisnasi, basarisiz kosu, durdurma, belirsizlik durusu")
    from cekirdek import kritik_arama
    for no in (0, 2):
        with _log_yakala("cekirdek.kritik_arama") as kayit:
            r, _s = _ara(_dogrusal(0.6, 0.5), 0.5, 1.0, istisna={no})
        kontrol("istisna %d. adimda -> basarisiz + mesaj + log" % no,
                not r.basarili and "istisnasi" in r.mesaj
                and any(k.exc_info for k in kayit), "-> %s" % r.mesaj)
    s = _yukle("pwr_17x17")
    with _taklit(_SahteKosucu(_dogrusal(0.6, 0.5), basarisiz={0})):
        r = kritik_arama.ara(s, "malzeme_yogunluk", "su", 0.5, 1.0, tempfile.mkdtemp())
    kontrol("basarisiz kosu -> RuntimeError metni", "çıkış kodu 3" in r.mesaj)
    with _taklit(_SahteKosucu(_dogrusal(0.6, 0.5))):
        r = kritik_arama.ara(s, "malzeme_yogunluk", "su", 0.5, 1.0, tempfile.mkdtemp(),
                             dur_bayragi=lambda: True)
    kontrol("durdurma ilk adimda", not r.basarili and "durdurdu" in r.mesaj)
    durdur = {"n": 0}

    def ucuncude():
        durdur["n"] += 1
        return durdur["n"] > 2
    with _taklit(_SahteKosucu(_dogrusal(0.6, 0.5))):
        r = kritik_arama.ara(s, "malzeme_yogunluk", "su", 0.5, 1.0, tempfile.mkdtemp(),
                             dur_bayragi=ucuncude, tolerans_sigma=1e-9)
    kontrol("durdurma yinelemede", not r.basarili and "durdurdu" in r.mesaj)
    # buyuk sigma, siki tolerans: parantez kok belirsizligine iner
    r, _s = _ara(_dogrusal(0.6, 0.5), 0.5, 1.0, sigma=0.02, tolerans_sigma=0.01)
    kontrol("belirsizlik durusu: basarili, cozum_belirsizlik > 0",
            r.basarili and r.cozum_belirsizlik and r.egim, "-> %s" % r.mesaj)
    cagri = []
    r, _s = _ara(_dogrusal(0.6, 0.5), 0.5, 1.0, geri_cagir=lambda i, k: cagri.append(i))
    kontrol("geri cagri her adimda", cagri == list(range(len(r.adimlar))))


def test_kritik_arama_terminal():
    print("\n[KA3] kritik_arama._terminal")
    from cekirdek import kritik_arama
    yol = os.path.join(ORNEK, "pwr_17x17.json")
    kod, metin = _cikti(kritik_arama._terminal, ["--yardim"])
    kontrol("yardim", kod == 0 and "Kullanım" in metin)
    kontrol("bilinmeyen secenek", _cikti(kritik_arama._terminal, [yol, "--q", "1"])[0] == 2)
    kontrol("eksik", _cikti(kritik_arama._terminal, [yol, "--tur", "bor_ppm"])[0] == 2)
    kok = tempfile.mkdtemp(prefix="ka3_")
    with _taklit(_SahteKosucu(_dogrusal(0.6, 0.5))):
        kod, metin = _cikti(kritik_arama._terminal, [
            yol, "--tur", "malzeme_yogunluk", "--hedef", "su", "--alt", "0.5", "--ust", "1.0",
            "--dizin", kok, "-s", "2"])
    kontrol("cozum bulundu, 0", kod == 0 and "Çözüm:" in metin, metin[-300:])
    with _taklit(_SahteKosucu(_dogrusal(0.6, 0.5))):
        kod, metin = _cikti(kritik_arama._terminal, [
            yol, "--tur", "cubuk_yaricap", "--hedef", "yakit_cubugu:0", "--alt", "0.40",
            "--ust", "0.41", "--dizin", kok])
    kontrol("cozum yok -> 1", kod == 1 and "bulunamadı" in metin, metin[-300:])


HIZLI = [test_parametre_uygula_turleri, test_korelasyon_noktalar_reaktivite,
         test_katsayi_ve_yorum, test_tarama_dongusu_taklit, test_tarama_terminal_taklit,
         test_kritik_arama_dallari, test_kritik_arama_hatalar, test_kritik_arama_terminal]
YAVAS = []
