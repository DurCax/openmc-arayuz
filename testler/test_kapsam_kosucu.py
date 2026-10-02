# -*- coding: utf-8 -*-
"""
test_kapsam_kosucu.py -- cekirdek/kosucu.py'nin kalan dallari icin MC'SIZ
kapsam testleri (yalniz test; kaynak kod degismedi). openmc alt sureci,
calistir ve sonuc_oku taklit edilir; statepoint gerekiyorsa rapor fixture'i
(testler/veri/kosu_ornek) okunur.
Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import contextlib
import io
import os
import shutil
import tempfile

from testler.ortak_test import kontrol, KOK

FIXTURE = os.path.join(KOK, "testler", "veri", "kosu_ornek")


def test_ayristirma_ve_yorum_dallari():
    print("\n[KK1] cevrim_satiri, keff_yorumu, lambda_metni, entropi dallari")
    from cekirdek import kosucu
    kontrol("sayi olmayan sutun None", kosucu.cevrim_satiri("  1/1   1.2.3") is None)
    kontrol("uc sutun None", kosucu.cevrim_satiri("  1/1   1.0   2.0   3.0") is None)
    kontrol("gecersiz k", kosucu.keff_yorumu(0.0, 0.001)[0] == "geçersiz k-eff")
    durum, ayrinti = kosucu.keff_yorumu(1.2, 0.001, beta_eff=0.0065, sonsuz=True)
    kontrol("k-sonsuz + dolar >= 1", durum.startswith("k∞") and "ρ > 1 $" in ayrinti
            and "ρ∞" in ayrinti)
    kontrol("kritik alti", kosucu.keff_yorumu(0.9, 0.001)[0].startswith("Kritik altı"))
    kontrol("kritik", kosucu.keff_yorumu(1.0005, 0.001)[0].startswith("Kritik ("))
    kontrol("lambda ns", kosucu.lambda_metni(6e-9, 1e-10).endswith("ns"))
    kontrol("lambda s", kosucu.lambda_metni(3e-12, 1e-13).endswith(" s"))
    kontrol("entropi az pasif", kosucu.entropi_yakinsama([1.0] * 20, 2)[0] is None)
    kontrol("entropi az aktif", kosucu.entropi_yakinsama([1.0] * 10, 8)[0] is None)
    kontrol("entropi sabit", kosucu.entropi_yakinsama([1.0] * 40, 10)[0] is None)
    kayan = [0.1 * i for i in range(20)] + [5.0 + 0.01 * (i % 2) for i in range(20)]
    kontrol("kayan kaynak False", kosucu.entropi_yakinsama(kayan, 20)[0] is False)


def test_dizin_ve_yol(tmp_path, monkeypatch):
    print("\n[KK2] openmc_yolu, dizin_hazirla (silinemeyen eski cikti)")
    import stat
    from cekirdek import kosucu, yollar
    # Kukla which yerine gercek gecici calistirilabilir + PATH ortami (T2 inceleme)
    bin_dizini = tmp_path / "bin"
    bin_dizini.mkdir()
    exe = bin_dizini / "openmc"
    exe.write_text("#!/bin/sh\nexit 0\n")
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    monkeypatch.delenv(yollar.OPENMC_ORTAM_DEGISKENI, raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    monkeypatch.setenv("PATH", str(bin_dizini))
    monkeypatch.setattr(kosucu.sys, "executable", str(tmp_path / "python"))
    kontrol("openmc_yolu PATH'ten", kosucu.openmc_yolu() == str(exe), kosucu.openmc_yolu())
    d = tempfile.mkdtemp(prefix="kapsam_kosucu_")
    try:
        os.makedirs(os.path.join(d, "statepoint.5.h5"))     # dizin: os.remove basarisiz
        open(os.path.join(d, "kosu.log"), "w").close()
        open(os.path.join(d, "baska.txt"), "w").close()
        kosucu.dizin_hazirla(d)
        kontrol("log silindi, digeri kaldi", not os.path.exists(os.path.join(d, "kosu.log"))
                and os.path.exists(os.path.join(d, "baska.txt")))
        kontrol("silinemeyen yutuldu (dizin)", os.path.isdir(os.path.join(d, "statepoint.5.h5")))
        kontrol("son_statepoint dizin yoksa None",
                kosucu.son_statepoint(os.path.join(d, "yok")) is None)
    finally:
        shutil.rmtree(d, True)


def test_tally_metni_dallari():
    print("\n[KK3] tally_metni: enerji birimleri, birimler, taninmayan filtre, DataFrame degil")
    import pandas as pd
    from cekirdek import kosucu
    kontrol("keV", kosucu._enerji_metni(5.0e3) == "5 keV")
    kontrol("eV", kosucu._enerji_metni(0.625) == "0.625 eV")
    kontrol("MeV", kosucu._enerji_metni(2.0e7) == "20 MeV")
    kontrol("mutlak aki", kosucu._birim("flux", True, 1e12).startswith("n·cm/s"))
    kontrol("mutlak isinma", kosucu._birim("heating", True, 1e12) == "eV/s")
    kontrol("goreli isinma", kosucu._birim("kappa-fission", False, 1.0) == "eV / kaynak nötronu")
    kontrol("mutlak tepkime", kosucu._birim("absorption", True, 5.0) == "1/s")
    df = pd.DataFrame({"mesh 1 x": [0], "score": ["flux"], "mean": [1.0], "std. dev.": [0.1]})
    kontrol("ek sutun -> tam tablo", "mesh 1 x" in kosucu.tally_metni("m", df))
    kontrol("DataFrame degil", kosucu.tally_metni("m", "metin") == "tally: m\nmetin")
    df2 = pd.DataFrame({"material": [7], "nuclide": ["U235"], "score": ["fission"],
                        "mean": [0.0], "std. dev.": [0.0]})
    metin = kosucu.tally_metni("r", df2, {}, sabit=True, kuvvet=2.0)
    kontrol("adsiz malzeme + sifir ortalama", "malzeme 7" in metin and "± 0.0%" in metin)


class _Tally(object):
    def __init__(self, ad, tid, df=None, hata=None):
        self.name, self.id, self._df, self._hata = ad, tid, df, hata

    def get_pandas_dataframe(self):
        if self._hata:
            raise RuntimeError(self._hata)
        return self._df


class _SahteSP(object):
    """_tallyleri_oku / _guc_korunumu / _hedef_payi icin en kucuk statepoint."""
    def __init__(self, tallyler):
        self.tallies = {t.id: t for t in tallyler}

    def get_tally(self, name):
        for t in self.tallies.values():
            if t.name == name:
                return t
        raise LookupError(name)


def _df(ort, sap=0.0):
    import pandas as pd
    return pd.DataFrame({"mean": [ort], "std. dev.": [sap]})


def test_tally_ifp_ve_kinetik():
    print("\n[KK4] _tallyleri_oku: IFP paylari, okunamayan tally, adsiz tally; _kinetik")
    from cekirdek import kosucu
    sp = _SahteSP([_Tally("IFP beta numerator", 1, _df(0.0065, 1e-5)),
                   _Tally("IFP time numerator", 2, _df(2e-5, 1e-7)),
                   _Tally("IFP denominator", 3, _df(1.0, 1e-3)),
                   _Tally("bozuk", 4, hata="okunamadi"),
                   _Tally("", 5, _df(1.0)),
                   _Tally("guc_dagilimi", 6, _df(1.0))])
    sonuc = {"tallyler": {}}
    ifp = kosucu._tallyleri_oku(sp, sonuc)
    kontrol("uc IFP payi", len(ifp) == 3)
    kontrol("okunamayan tally metni", sonuc["tallyler"]["bozuk"].startswith("okunamadı"))
    kontrol("adsiz tally_5", "tally_5" in sonuc["tallyler"])
    kontrol("guc tally'si atlandi", "guc_dagilimi" not in sonuc["tallyler"])
    kin = kosucu._kinetik(ifp)
    kontrol("beta_eff", abs(kin["beta_eff"] - 0.0065) < 1e-12 and kin["omur"] == 2e-5)
    kontrol("eksik pay None", kosucu._kinetik({"IFP denominator": (1.0, 0.0)}) is None)
    kontrol("sifir payda None", kosucu._kinetik({"IFP beta numerator": (1.0, 0.0),
                                                "IFP time numerator": (1.0, 0.0),
                                                "IFP denominator": (0.0, 0.0)}) is None)


def test_guc_korunumu_ve_pay():
    print("\n[KK5] _guc_korunumu: bozuk harita uyarisi, sifir referans; _hedef_payi; bos dagilim")
    from cekirdek import kosucu, guc
    dagilim = {"konumlar": {(0, 0): {"toplam": (1.0, 0.0)}, (0, 1): {"toplam": (1.5, 0.0)}}}
    sp = _SahteSP([_Tally("guc_toplam_ref", 1, _df(2.0)), _Tally("guc_model_toplam", 2, _df(4.0))])
    alanlar = kosucu._guc_korunumu(sp, dagilim)
    kontrol("korunum uyarisi", "korunum_uyari" in alanlar and alanlar["korunum"] > 0.2)
    kontrol("hedef payi 0.5", kosucu._hedef_payi(sp) == {"hedef_payi": 0.5})
    sifir = _SahteSP([_Tally("guc_toplam_ref", 1, _df(0.0))])
    kontrol("sifir referans notu", "korunum_notu" in kosucu._guc_korunumu(sifir, dagilim))
    kontrol("model toplami yok -> None", kosucu._hedef_payi(sifir) == {"hedef_payi": None})
    bozuk = _SahteSP([_Tally("guc_toplam_ref", 1, hata="bozuk dosya")])
    kontrol("okuma hatasi", "korunum_hata" in kosucu._guc_korunumu(bozuk, dagilim)
            and "hedef_payi_hata" in kosucu._hedef_payi(bozuk))
    satirlar = kosucu.korunum_satirlari({"korunum": 0.3, "korunum_hata": "x",
                                         "korunum_notu": "not"})
    kontrol("korunum satirlari (bozuk + hata + not)", len(satirlar) == 3
            and "güvenmeyin" in satirlar[0])
    eski = guc.dagilim_oku
    guc.dagilim_oku = lambda sp: {}
    try:
        sonuc = {}
        kosucu._guc_oku(object(), sonuc)
        kontrol("bos dagilim -> guc yok", sonuc == {})
    finally:
        guc.dagilim_oku = eski


def test_sonuc_oku_kinetik():
    print("\n[KK6] sonuc_oku: kinetik alanlari (IFP taklit) fixture statepoint'le")
    from cekirdek import kosucu
    eski = kosucu._kinetik
    kosucu._kinetik = lambda ifp: {"beta_eff": 0.0065, "beta_eff_sapma": 1e-5,
                                   "omur": 2e-5, "omur_sapma": 1e-7}
    try:
        s = kosucu.sonuc_oku(kosucu.son_statepoint(FIXTURE))
    finally:
        kosucu._kinetik = eski
    kontrol("kinetik eklendi", s.get("kinetik", {}).get("beta_eff") == 0.0065)
    kontrol("guc okundu", s["guc"]["faktorler"]["cubuk_sayisi"] == 264)


class _Tty(io.StringIO):
    def isatty(self):
        return True


def test_terminal_ilerleme_tty():
    print("\n[KK7] _terminal: varsayilan dizin, ilerleme (tty), entropi okunamadi")
    import json
    from cekirdek import dogrula, kosucu, sema
    from testler.ortak_test import ORNEK
    d = tempfile.mkdtemp(prefix="kapsam_terminal_")
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    yol = os.path.join(d, "model.json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(spec, f)
    cagri = {}

    def sahte_calistir(spec, dizin, geri_cagir=None, **k):
        cagri["dizin"] = dizin
        for i in range(1, 25):
            geri_cagir("satir", {"cevrim": i, "ortalama": 1.1, "sapma": 0.01})
        geri_cagir("satir", None)
        return {"basarili": True, "cikis_kodu": 0, "statepoint": "sp.h5", "sure": 1.0,
                "log": "kosu.log", "cevrimler": []}
    sonuc = {"mod": "eigenvalue", "keff": (1.3, 0.001), "cevrim": 60, "pasif": 10,
             "parcacik": 100, "entropi": [], "entropi_hata": "bozuk entropi",
             "tallyler": {}, "malzeme_adlari": {}}
    eski = kosucu.calistir, kosucu.sonuc_oku, dogrula.kapi, kosucu.sys.stdout
    kosucu.calistir, kosucu.sonuc_oku = sahte_calistir, lambda y: sonuc
    dogrula.kapi = lambda s, veri_kontrolu=True: []
    cikti = _Tty()
    try:
        with contextlib.redirect_stdout(cikti):
            kod = kosucu._terminal([yol])
    finally:
        kosucu.calistir, kosucu.sonuc_oku, dogrula.kapi, _s = eski
        shutil.rmtree(d, True)
    metin = cikti.getvalue()
    kontrol("cikis 0", kod == 0)
    kontrol("varsayilan dizin spec yaninda", cagri["dizin"] == os.path.join(d, "kosu"))
    kontrol("tty ilerleme \\r ile", "\rçevrim" in metin.replace("      ", "")
            or "\r      çevrim" in metin)
    kontrol("entropi okunamadi satiri", "Shannon entropisi okunamadı: bozuk entropi" in metin)


def test_xml_yaz_spec_json():
    print("\n[KK8] xml_yaz kosu dizinine spec.json yazar; dizin_hazirla eskisini siler")
    from cekirdek import kosucu, sema
    spec = sema.yukle(os.path.join(KOK, "ornekler", "pwr_pinhucre.json"))
    d = tempfile.mkdtemp(prefix="kapsam_kosucu_")
    try:
        kosucu.xml_yaz(spec, d)
        yol = os.path.join(d, "spec.json")
        kontrol("spec.json yazildi (rapor/CLI buradan okur)", os.path.isfile(yol))
        kontrol("spec.json geri yuklenince ayni model", sema.yukle(yol) == spec)
        kosucu.dizin_hazirla(d)
        kontrol("temizlikte eski spec.json silindi", not os.path.exists(yol))
    finally:
        shutil.rmtree(d, True)


HIZLI = [test_ayristirma_ve_yorum_dallari, test_dizin_ve_yol, test_tally_metni_dallari,
         test_tally_ifp_ve_kinetik, test_guc_korunumu_ve_pay, test_sonuc_oku_kinetik,
         test_terminal_ilerleme_tty, test_xml_yaz_spec_json]
YAVAS = []
