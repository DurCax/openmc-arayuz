# -*- coding: utf-8 -*-
"""
 test_guc_sonuc.py  --  kosucu.sonuc_oku hata yollari, korunum, mutlak guc,
                        dogrulama kapisi (D1-A bulgu 2b, 3, 4, 5)

 HATA (olculdu):
   * sonuc_oku guc korunum blogu `except Exception: pass` idi: tally eksik de
     olsa, dosya bozuk da olsa korunum sessizce kayboluyordu (bulgu 3).
   * guc okuma, tally okuma, entropi ve malzeme adi hatalari loglanmiyordu
     (bulgu 4).
   * mutlak guc tum toplam_guc'u hedef cubuga yaziyordu; baska fisil bolge
     (blanket, ikinci cubuk turu) varsa cubuk gucu fazla cikar (bulgu 2b).
   * kosucu.calistir dogrulamadan kosu dizinini temizliyordu (bulgu 5).

 HIZLI: sahte StatePoint (openmc.StatePoint yerine), nukleer veri yok.
"""

import logging
import os
import shutil
import tempfile
from types import SimpleNamespace

from testler.ortak_test import kontrol, ORNEK


class _Toplayici(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.kayitlar = []

    def emit(self, kayit):
        self.kayitlar.append((kayit.levelno, kayit.getMessage(), kayit.exc_info is not None))


def _loglu(fn):
    """fn()'i uygulama kaydedicisi DEBUG'da toplanarak calistirir."""
    from cekirdek import gunluk
    k = logging.getLogger(gunluk.KOK_KAYDEDICI)
    t = _Toplayici()
    eski = k.level
    k.addHandler(t)
    k.setLevel(logging.DEBUG)
    try:
        return fn(), t.kayitlar
    finally:
        k.removeHandler(t)
        k.setLevel(eski)


class _Tally:
    def __init__(self, ad, df=None, hata=None, tid=1):
        self.name, self.id, self._df, self._hata = ad, tid, df, hata

    def get_pandas_dataframe(self, paths=True):
        if self._hata:
            raise self._hata
        return self._df


def _df(ortalar):
    import pandas as pd
    return pd.DataFrame({"mean": list(ortalar), "std. dev.": [0.0] * len(ortalar)})


def _sahte_sp(guc=True, ref=None, model=None, ek_tally=None, entropi_hata=False,
              malzeme_hata=False):
    """guc: kare 2x2 sentetik guc tally'si (test_guc_kor); ref/model: toplam
    degeri, _Tally ya da None (tally yok)."""
    from testler.test_guc_kor import _kare_2x2_sentetik
    kaynak = _kare_2x2_sentetik()
    tallyler = {}
    if guc:
        tallyler["guc_dagilimi"] = _Tally("guc_dagilimi", kaynak.get_tally().get_pandas_dataframe())
    for ad, v in (("guc_toplam_ref", ref), ("guc_model_toplam", model)):
        if isinstance(v, _Tally):
            tallyler[ad] = v
        elif v is not None:
            tallyler[ad] = _Tally(ad, _df([v]))
    for t in ek_tally or []:
        tallyler[t.name] = t

    def get_tally(name=None):
        if name not in tallyler:
            raise LookupError("'%s' yok" % name)
        return tallyler[name]

    class _Sp(SimpleNamespace):
        @property
        def entropy(self):
            if entropi_hata:
                raise KeyError("entropy veri kumesi yok")
            return [1.0, 2.0]

    ozet = kaynak.summary
    if malzeme_hata:
        ozet = SimpleNamespace(geometry=kaynak.summary.geometry)     # materials yok
    else:
        ozet = SimpleNamespace(geometry=kaynak.summary.geometry,
                               materials=[SimpleNamespace(id=1, name="uo2")])
    return _Sp(keff=None, n_batches=10, n_inactive=0, n_particles=100, summary=ozet,
               tallies={i: t for i, t in enumerate(tallyler.values())}, get_tally=get_tally)


def _oku(sp):
    import openmc
    from cekirdek import kosucu
    eski = openmc.StatePoint
    openmc.StatePoint = lambda yol: sp
    try:
        return _loglu(lambda: kosucu.sonuc_oku("sahte.h5"))
    finally:
        openmc.StatePoint = eski


_TOPLAM_2X2 = sum(100.0 * (d + 1) + c for d in range(4) for c in range(4))


# ============================================================================
# bulgu 3: korunum blogu
# ============================================================================

def test_korunum_tally_yok_debug():
    print("\n[GS1] Korunum: guc_toplam_ref yok -> yalniz DEBUG, hata alani yok")
    s, log = _oku(_sahte_sp(ref=None))
    g = s.get("guc") or {}
    kontrol("guc okundu", bool(g.get("faktorler")), "-> %r" % s.get("guc_hata"))
    kontrol("korunum yok, korunum_hata yok", "korunum" not in g and "korunum_hata" not in g,
            "-> %r" % sorted(g))
    kontrol("DEBUG kaydi 'guc_toplam_ref'",
            any(sv == logging.DEBUG and "guc_toplam_ref" in m for sv, m, _e in log),
            "-> %r" % log)
    kontrol("ERROR kaydi yok", not any(sv >= logging.ERROR for sv, _m, _e in log))


def test_korunum_bozuk_tally_loglanir():
    print("\n[GS2] Korunum: tally okunamiyor -> korunum_hata + log.exception")
    s, log = _oku(_sahte_sp(ref=_Tally("guc_toplam_ref", hata=ValueError("bozuk veri 42"))))
    g = s.get("guc") or {}
    kontrol("korunum_hata metni", g.get("korunum_hata") == "bozuk veri 42",
            "-> %r" % g.get("korunum_hata"))
    kontrol("ERROR kaydi exc_info ile",
            any(sv >= logging.ERROR and e for sv, _m, e in log), "-> %r" % log)


def test_korunum_ref_sifir_notu():
    print("\n[GS3] Korunum: ref <= 0 -> korunum_notu")
    s, _log = _oku(_sahte_sp(ref=0.0))
    g = s.get("guc") or {}
    kontrol("korunum_notu var", bool(g.get("korunum_notu")), "-> %r" % sorted(g))
    kontrol("korunum hesaplanmadi", "korunum" not in g)


def test_korunum_tamam():
    print("\n[GS4] Korunum: esit toplam -> korunum ~ 0")
    s, _log = _oku(_sahte_sp(ref=_TOPLAM_2X2))
    g = s.get("guc") or {}
    kontrol("korunum < 1e-12", g.get("korunum") is not None and g["korunum"] < 1e-12,
            "-> %r" % g.get("korunum"))
    kontrol("guc tally'leri tablo listesinde yok",
            not any(a.startswith("guc_") for a in s["tallyler"]), "-> %r" % list(s["tallyler"]))


# ============================================================================
# bulgu 4: diger okuma hatalari loglanir
# ============================================================================

def test_okuma_hatalari_loglanir():
    print("\n[GS5] sonuc_oku: guc / tally / entropi / malzeme hatalari loglanir")
    from cekirdek import guc
    eski = guc.dagilim_oku

    def bozuk(_sp, tally_adi="guc_dagilimi"):
        raise RuntimeError("summary.h5 bozuk 7")
    guc.dagilim_oku = bozuk
    try:
        s, log = _oku(_sahte_sp(ref=1.0, entropi_hata=True, malzeme_hata=True,
                                ek_tally=[_Tally("aki", hata=OSError("okuma 9"), tid=5)]))
    finally:
        guc.dagilim_oku = eski
    kontrol("guc_hata metni", s.get("guc_hata") == "summary.h5 bozuk 7", "-> %r" % s.get("guc_hata"))
    kontrol("guc hatasi ERROR + exc_info",
            any(sv >= logging.ERROR and e and "güç" in m for sv, m, e in log), "-> %r" % log)
    kontrol("tally hatasi kullaniciya", str(s["tallyler"].get("aki", "")).startswith("okunamadı"))
    kontrol("tally hatasi WARNING + exc_info",
            any(sv == logging.WARNING and e and "aki" in m for sv, m, e in log))
    kontrol("entropi hatasi loglandi, entropi bos",
            s["entropi"] == [] and any("entropi" in m for _sv, m, _e in log))
    kontrol("malzeme adi hatasi loglandi",
            s["malzeme_adlari"] == {} and any("malzeme" in m for _sv, m, _e in log))


# ============================================================================
# bulgu 2b: mutlak guc model geneli kappa'dan
# ============================================================================

def test_mutlak_guc_hedef_payi():
    print("\n[GS6] Mutlak guc: pay = kappa_hedef / kappa_model")
    from cekirdek import guc
    s, _log = _oku(_sahte_sp(ref=_TOPLAM_2X2, model=4.0 * _TOPLAM_2X2))
    g = s["guc"]
    kontrol("hedef_payi = 0.25", abs((g.get("hedef_payi") or 0) - 0.25) < 1e-15,
            "-> %r" % g.get("hedef_payi"))
    f = g["faktorler"]
    m = guc.mutlak_guc(f, 1.6e6, 100.0, hedef_payi=g["hedef_payi"])
    kontrol("cubuk ortalamasi = P * pay / n (elle)",
            abs(m["cubuk_ortalama_W"] - 1.6e6 * 0.25 / 16) < 1e-9, "-> %r" % m["cubuk_ortalama_W"])
    kontrol("hedef gucu alani", abs(m["hedef_guc"] - 0.4e6) < 1e-9)
    kontrol("lineer ortalama", abs(m["lineer_ortalama_W_cm"] - 1.6e6 * 0.25 / 16 / 100) < 1e-12)
    m0 = guc.mutlak_guc(f, 1.6e6, 100.0)
    kontrol("pay yoksa eski davranis (P / n)", abs(m0["cubuk_ortalama_W"] - 1.0e5) < 1e-9
            and m0.get("hedef_payi") is None)
    yorum = " ".join(guc.yorumla(f, m))
    kontrol("yorum payi soyler", "%25.0" in yorum or "25.0" in yorum, yorum[-300:])


def test_mutlak_guc_eski_statepoint():
    print("\n[GS7] Mutlak guc: guc_model_toplam yok (eski statepoint) -> pay None")
    s, log = _oku(_sahte_sp(ref=_TOPLAM_2X2, model=None))
    kontrol("hedef_payi None", s["guc"].get("hedef_payi") is None)
    kontrol("ERROR yok", not any(sv >= logging.ERROR for sv, _m, _e in log))


def test_model_toplam_tally_kurulur_ve_betik():
    print("\n[GS8] kurucu + betik: guc_model_toplam tally'si (filtresiz, ayni skor)")
    from cekirdek import kod_uret, kurucu, sema
    spec = sema.yukle(os.path.join(ORNEK, "pwr_17x17.json"))
    spec["guc_dagilimi"].update(var=True, cubuk="yakit_cubugu", bolge=0)
    model, _b = kurucu.kur(spec)
    t = {x.name: x for x in model.tallies}
    kontrol("uc guc tally'si", {"guc_dagilimi", "guc_toplam_ref", "guc_model_toplam"} <= set(t),
            "-> %r" % sorted(t))
    mt = t.get("guc_model_toplam")
    kontrol("model toplam filtresiz, skor ayni",
            mt is not None and not mt.filters and mt.scores == t["guc_dagilimi"].scores)
    kod = kod_uret.uret(spec, "model.py")
    kontrol("betikte guc_model_toplam", "name='guc_model_toplam'" in kod)
    import importlib.util
    eski = os.getcwd()
    d = tempfile.mkdtemp()
    try:
        os.chdir(d)
        with open("model.py", "w", encoding="utf-8") as f:
            f.write(kod)
        sm = importlib.util.spec_from_file_location("guc_betik", os.path.join(d, "model.py"))
        mod = importlib.util.module_from_spec(sm)
        sm.loader.exec_module(mod)
    finally:
        os.chdir(eski)
        shutil.rmtree(d, True)
    ns = {"model": mod.model}
    bt = {x.name: x for x in ns["model"].tallies} if "model" in ns else {}
    kontrol("betik modeli ayni guc tally adlari ve skorlari",
            {a: list(x.scores) for a, x in bt.items() if a.startswith("guc_")}
            == {a: list(x.scores) for a, x in t.items() if a.startswith("guc_")},
            "-> %r" % sorted(bt))


# ============================================================================
# bulgu 3 (arayuz): Calistir sekmesi guc ozeti
# ============================================================================

def test_sekme_korunum_hata_gorunur():
    print("\n[GS9] Calistir sekmesi: korunum_hata / notu ve tam kor konum metni")
    from PySide6 import QtWidgets
    uyg = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from cekirdek import guc, sema
    from arayuz.sekme_calistir import CalistirSekmesi
    from testler.test_guc_kor import _kare_2x2_sentetik
    d = guc.dagilim_oku(_kare_2x2_sentetik())
    f = guc.tepe_faktorleri(d)
    c = CalistirSekmesi()
    c.spec_ayarla(sema.yukle(os.path.join(ORNEK, "pwr_17x17.json")), None)
    temel = {"mod": "eigenvalue", "keff": (1.1, 0.001), "cevrim": 10, "pasif": 2,
             "parcacik": 100, "entropi": [], "tallyler": {}}
    c._sonuc_goster(dict(temel, guc={"dagilim": d, "faktorler": f,
                                     "korunum_hata": "bozuk veri 42"}), "sp.h5")
    metin = c.ozet_etiket.text()
    kontrol("korunum_hata metni gorunur", "bozuk veri 42" in metin, metin[-400:])
    kontrol("tam kor konum metni demet + cubuk", "demet" in metin and "çubuk" in metin)
    c._sonuc_goster(dict(temel, guc={"dagilim": d, "faktorler": f,
                                     "korunum_notu": "referans toplam sıfır"}), "sp.h5")
    kontrol("korunum_notu gorunur", "referans toplam sıfır" in c.ozet_etiket.text())
    c.close()
    uyg  # noqa: B018


# ============================================================================
# bulgu 5: dogrulama kapisi
# ============================================================================

def _hatali_spec():
    from cekirdek import sema
    s = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    s["ayarlar"]["parcacik"] = 0
    return s


def test_calistir_kapi_dizini_korur():
    print("\n[GS10] calistir: hatali spec -> DogrulamaHatasi, onceki kosu SILINMEZ")
    from cekirdek import kosucu
    from cekirdek.dogrula import DogrulamaHatasi
    d = tempfile.mkdtemp()
    try:
        for ad in ("statepoint.10.h5", "kosu.log", "model.xml"):
            with open(os.path.join(d, ad), "w") as f:
                f.write("onceki kosu")
        try:
            kosucu.calistir(_hatali_spec(), d, veri_kontrolu=False)
            hata = None
        except DogrulamaHatasi as e:
            hata = e
        kontrol("DogrulamaHatasi", hata is not None and hata.bulgular)
        kontrol("onceki kosu dosyalari yerinde",
                sorted(os.listdir(d)) == ["kosu.log", "model.xml", "statepoint.10.h5"],
                "-> %r" % sorted(os.listdir(d)))
    finally:
        shutil.rmtree(d, True)


def test_calistir_dogrulama_kapali_eski_davranis():
    print("\n[GS11] calistir(dogrulama=False): kapi cagrilmaz, dizin temizlenir")
    from cekirdek import dogrula, kosucu, sema
    d = tempfile.mkdtemp()
    eski_kapi, eski_yol = dogrula.kapi, kosucu.openmc_yolu
    cagri = []
    dogrula.kapi = lambda *a, **k: cagri.append(1)
    kosucu.openmc_yolu = lambda: None
    try:
        with open(os.path.join(d, "statepoint.10.h5"), "w") as f:
            f.write("x")
        try:
            kosucu.calistir(sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json")), d,
                            dogrulama=False)
            hata = None
        except RuntimeError as e:
            hata = str(e)
        kontrol("kapi cagrilmadi", cagri == [])
        kontrol("eski davranis: dizin temizlendi, model.xml yazildi, openmc aranir",
                "statepoint.10.h5" not in os.listdir(d) and "model.xml" in os.listdir(d)
                and hata and "openmc" in hata, "-> %r / %r" % (os.listdir(d), hata))
    finally:
        dogrula.kapi, kosucu.openmc_yolu = eski_kapi, eski_yol
        shutil.rmtree(d, True)


def test_calistir_varsayilan_kapi_cagrilir():
    print("\n[GS12] calistir(): varsayilan kapi cagrilir (veri_kontrolu iletilir)")
    from cekirdek import dogrula, kosucu, sema
    d = tempfile.mkdtemp()
    eski_kapi, eski_yol = dogrula.kapi, kosucu.openmc_yolu
    cagri = []
    dogrula.kapi = lambda spec, veri_kontrolu=True: cagri.append(veri_kontrolu) or []
    kosucu.openmc_yolu = lambda: None
    try:
        try:
            kosucu.calistir(sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json")), d,
                            veri_kontrolu=False)
        except RuntimeError:
            pass
        kontrol("kapi bir kez, veri_kontrolu=False", cagri == [False], "-> %r" % cagri)
    finally:
        dogrula.kapi, kosucu.openmc_yolu = eski_kapi, eski_yol
        shutil.rmtree(d, True)


def test_cli_hatali_spec_cikis_kodu():
    print("\n[GS13] Terminal: hatali spec -> cikis kodu != 0, calistir cagrilmaz")
    import json
    from cekirdek import kosucu
    d = tempfile.mkdtemp()
    eski = kosucu.calistir
    cagri = []
    kosucu.calistir = lambda *a, **k: cagri.append(1)
    try:
        yol = os.path.join(d, "hatali.json")
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(_hatali_spec(), f)
        kod = kosucu._terminal([yol, "--dizin", os.path.join(d, "kosu")])
        kontrol("cikis kodu != 0", kod != 0, "-> %r" % kod)
        kontrol("calistir cagrilmadi", cagri == [])
    finally:
        kosucu.calistir = eski
        shutil.rmtree(d, True)


HIZLI = [
    test_korunum_tally_yok_debug, test_korunum_bozuk_tally_loglanir,
    test_korunum_ref_sifir_notu, test_korunum_tamam, test_okuma_hatalari_loglanir,
    test_mutlak_guc_hedef_payi, test_mutlak_guc_eski_statepoint,
    test_model_toplam_tally_kurulur_ve_betik, test_sekme_korunum_hata_gorunur,
    test_calistir_kapi_dizini_korur, test_calistir_dogrulama_kapali_eski_davranis,
    test_calistir_varsayilan_kapi_cagrilir, test_cli_hatali_spec_cikis_kodu,
]
YAVAS = []
