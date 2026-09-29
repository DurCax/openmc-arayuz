# -*- coding: utf-8 -*-
"""
 test_tukenme_gorunum.py  --  Dalga 2 / Ajan 8c: nuklid gruplari (fizik),
                              Tukenme ve Analiz sekmelerinin yeni gorunumu,
                              cubuk cubuk yanma sonuc adlari, kapanis cokmesi.

 Nuklid gruplari reaktor fizigine gore kurulur (nedenleri cekirdek/nuklidler.py
 basinda). Her grup adinin pwr_tukenme'nin zincirinde (ENDF/B-VIII.0 termal)
 COZULMESI zorunludur; baska zincirlerde (CASL) cozulmeyenler listelenir.
 Sozlesme: testler/ortak_test.py (HIZLI / YAVAS).
"""

import copy
import gc
import os
import time

from testler.ortak_test import kontrol, ORNEK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SENTETIK = ("H1", "O16", "Th232", "Th233", "Pa231", "Pa233", "U232", "U233", "U235",
            "U238", "Np237", "Pu239", "Am241", "Cm243", "Cm244", "Cm246", "I135",
            "Xe135", "Pm148", "Pm148_m1", "Pm149", "Sm149", "Sm152", "Mo95", "Ru101",
            "Ag109", "Nd148", "Cs134", "Cs137", "Sr90", "Tc99", "I129", "Se79", "Zr93",
            "Pd107", "Sn126", "Cs135")


def _qt():
    try:
        from PySide6 import QtWidgets
    except ImportError as e:                         # pragma: no cover
        kontrol("PySide6 yok, arayuz testi atlandi", True, "-> %s" % e)
        return None
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _spec(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


# ============================================================================
# 1. Gruplar ve setler (saf)
# ============================================================================

def test_yeni_gruplar():
    print("\n[TG1] NUKLID GRUPLARI: yanma gostergesi, Th/Pa, Xe/Sm, atik/isi ayrimi")
    from cekirdek import nuklidler as nk
    g = {x.anahtar: x for x in nk.gruplar(SENTETIK)}
    kontrol("Th/Pa grubu (Th232, Th233, Pa231, Pa233)",
            g.get("toryum") is not None
            and g["toryum"].nuklidler == ("Th232", "Th233", "Pa231", "Pa233"),
            "-> %r" % (g.get("toryum") and g["toryum"].nuklidler,))
    kontrol("yanma gostergesi Nd148, Cs134, Cs137",
            g.get("yanma") is not None
            and g["yanma"].nuklidler == ("Nd148", "Cs134", "Cs137"))
    kontrol("Xe/Sm dinamigi: oncu I135 ve Pm149 dahil",
            g.get("xe_sm") is not None
            and g["xe_sm"].nuklidler == ("I135", "Xe135", "Pm149", "Sm149"))
    zehir = set(g["zehirler"].nuklidler)
    kontrol("zehirler: Pm148_m1, Sm152, Mo95, Ru101, Ag109 eklendi",
            {"Pm148_m1", "Sm152", "Mo95", "Ru101", "Ag109"} <= zehir, "-> %r" % sorted(zehir))
    kontrol("Cm243 ve Cm246 kuriyum grubunda",
            {"Cm243", "Cm246"} <= set(g["kuriyum"].nuklidler))
    atik = g["uzun_omurlu"]
    alt = {a.anahtar: a.nuklidler for a in atik.altgruplar}
    kontrol("'Atik / isi' iki alt grup: 7 LLFP + orta omurlu Cs137/Sr90",
            alt.get("llfp") == ("Se79", "Zr93", "Tc99", "Pd107", "Sn126", "I129", "Cs135")
            and alt.get("orta_omurlu") == ("Cs137", "Sr90"), "-> %r" % alt)
    kontrol("'Atik / isi' ust grubu iki alt grubun birlesimi",
            set(atik.nuklidler) == set(alt["llfp"]) | set(alt["orta_omurlu"]))
    kontrol("bos alt grup gosterilmez", all(a.nuklidler for x in g.values()
                                             for a in x.altgruplar))
    kontrol("alt grup yalniz zincirdekiler", [a.nuklidler for a in
            {x.anahtar: x for x in nk.gruplar(("Cs137", "U235"))}["uzun_omurlu"].altgruplar]
            == [("Cs137",)])


def test_yeni_setler():
    print("\n[TG2] HAZIR SETLER: eski bes set aynen; yeni setler tum_setler'de")
    from cekirdek import nuklidler as nk
    eski = [s.anahtar for s in nk.hazir_setler(SENTETIK)]
    kontrol("hazir_setler degismedi", eski == ["temel", "pu", "zehirler", "minor", "atik"])
    tum = {s.anahtar: s.nuklidler for s in nk.tum_setler(SENTETIK)}
    kontrol("tum_setler = eski + yanma, toryum, hizli",
            list(tum) == eski + ["yanma", "toryum", "hizli"], "-> %r" % list(tum))
    kontrol("toryum seti Th232 -> Pa233 -> U233 zinciri",
            tum["toryum"] == ("Th232", "Th233", "Pa231", "Pa233", "U232", "U233"),
            "-> %r" % (tum["toryum"],))
    kontrol("hizli spektrum seti: Xe/Sm zehiri YOK, U238 ve Pu239 var",
            "Xe135" not in tum["hizli"] and {"U238", "Pu239"} <= set(tum["hizli"]))
    kontrol("minor setinde Cm243, Cm246", {"Cm243", "Cm246"} <= set(tum["minor"]))


def test_zincirde_cozulme():
    print("\n[TG3] ZINCIR: her grup/set adi pwr_tukenme zincirinde cozulur; digerleri listelenir")
    from cekirdek import nuklidler as nk
    from cekirdek import sema, tukenme, veri_bilgi
    zs = tukenme.zincir_secimi(_spec("pwr_tukenme"))
    if not os.path.isfile(zs["yol"]):
        kontrol("zincir yok (%s) -- test atlandi" % zs["yol"], True)
        return
    adlar = nk.zincir_nuklidleri(zs["yol"])
    eksik = nk.cozulmeyenler(adlar)
    kontrol("pwr_tukenme zinciri (%s): cozulmeyen yok" % os.path.basename(zs["yol"]),
            eksik == {}, "-> %r" % eksik)
    kontrol("tum sabit adlar normallestirilmis OpenMC adi",
            all(nk.normallestir(n) == n for n in nk.tum_sabit_adlar()))
    for tur, dosya in sorted(tukenme.ZINCIRLER.items()):
        yol = os.path.join(veri_bilgi.zincir_dizini(), dosya)
        if not os.path.isfile(yol):
            continue
        e = nk.cozulmeyenler(nk.zincir_nuklidleri(yol))
        print("    bilgi: %s cozulmeyen: %s" % (tur, e or "yok"))
        kontrol("%s: cozulmeyenler sozluk (anahtar -> ad listesi)" % tur,
                all(isinstance(v, tuple) and v for v in e.values()))
    sema  # noqa: B018


# ============================================================================
# 2. Kapanis: bekleyen cizim ve gec gelen sonuc (D1-A cokmesi)
# ============================================================================

SAHTE_SONUC = {"zaman_d": [0.0, 1.0], "yanma": [0.0, 0.04], "k": [1.30, 1.28],
               "k_sapma": [0.0010, 0.0011], "atomlar": {"uo2": {"U235": [1e21, 9e20]}},
               "yogunluk": {"uo2": {"U235": [7.0e-4, 6.8e-4]}},
               "adim_sayisi": 1, "bulunamayan": []}


def _sekme(ad="pwr_tukenme"):
    from arayuz.sekme_tukenme import TukenmeSekmesi
    t = TukenmeSekmesi()
    t.spec_yukle(_spec(ad))
    t.bekle()
    return t


def test_silinmis_sekmeye_gec_sonuc():
    """D1-A: sekme silindikten sonra gelen okuma sonucu / bekleyen cizim coktururdu
    (RuntimeError: Internal C++ object already deleted)."""
    print("\n[TG4] KAPANIS: silinmis sekmeye gelen gec sonuc ve bekleyen cizim cokmez")
    uyg = _qt()
    if uyg is None:
        return
    import shiboken6
    from PySide6 import QtWidgets
    t = _sekme()
    t.show()
    uyg.processEvents()
    tuval = t.tuval
    t._grafik_bos()                       # bekleyen bir cizim birak
    t.close()
    shiboken6.delete(t)                   # kabuk sayfayi sildi / test islevi dondu
    kontrol("(on kosul) C++ nesnesi silindi",
            not shiboken6.isValid(t) and not shiboken6.isValid(tuval))
    hatalar = []
    for ad, f in (("tuval.draw_idle", lambda: tuval.draw_idle()),
                  ("_grafik_bos", lambda: t._grafik_bos()),
                  ("_sonuc_goster", lambda: t._sonuc_goster(copy.deepcopy(SAHTE_SONUC))),
                  ("_onceki_geldi", lambda: t._onceki_geldi(
                      ("/yok/x.h5", 1.0),
                      {"h5": "/yok/x.h5", "tarih": time.time(), "durum": "guncel",
                       "farklar": [], "sonuc": copy.deepcopy(SAHTE_SONUC)})),
                  ("_secim_geldi", lambda: t._secim_geldi(
                      (t._kusak, "/yok/x.h5"), copy.deepcopy(SAHTE_SONUC))),
                  ("_bulunamayan_yaz", lambda: t._bulunamayan_yaz(["Xe-135"]))):
        try:
            f()
        except RuntimeError as e:
            hatalar.append("%s: %s" % (ad, e))
    kontrol("silinmis sekmede gec cagrilar sessizce yok sayiliyor", not hatalar,
            "-> %r" % hatalar)
    for _i in range(5):
        QtWidgets.QApplication.processEvents()
    kontrol("bekleyen cizim olay dongusunde cokmuyor", True)


def test_kapanista_bekleyen_cizim_iptal():
    print("\n[TG5] KAPANIS: close() bekleyen cizimi iptal eder ve okumayi bekler")
    uyg = _qt()
    if uyg is None:
        return
    from PySide6 import QtCore
    t = _sekme()
    t.show()
    uyg.processEvents()
    t._grafik_bos()
    kontrol("(on kosul) cizim bekliyor", t.tuval._draw_pending is True,
            "-> %r" % getattr(t.tuval, "_draw_pending", None))
    t.close()
    kontrol("close(): bekleyen cizim iptal edildi", t.tuval._draw_pending is False)

    class _Yavas(QtCore.QThread):
        def run(self):
            self.msleep(300)
    t2 = _sekme()
    isci = _Yavas(t2)
    t2._secim_isci = isci
    t2._secim_okunuyor = True
    isci.finished.connect(lambda: setattr(t2, "_secim_okunuyor", False))
    isci.start()
    t2.close()
    kontrol("close(): suren okuma beklendi (QThread calisir durumda degil)",
            not isci.isRunning() and not t2._secim_okunuyor)
    gc.collect()


# ============================================================================
# 3. Cubuk cubuk yanma: klon malzemelerin adi ve yogunlugu
# ============================================================================

def _ayirmali_spec():
    s = _spec("pwr_17x17")
    s.setdefault("tukenme", {}).update(var=True, malzemeleri_ayir=True,
                                       guc_yogunlugu=40.0, adimlar=[0.5],
                                       izlenen=["U235", "Pu239"])
    return s


class _SahteSonuclar:
    """openmc.deplete.Results taklidi (MC'siz): iki adim, iki nuklid."""

    def __init__(self, malzeme_idleri, nuklidler=("U235", "Pu239")):
        self.index_mat = {str(i): k for k, i in enumerate(malzeme_idleri)}
        self.index_nuc = {n: k for k, n in enumerate(nuklidler)}

    def __getitem__(self, i):
        return self

    def get_keff(self, time_units="d"):
        import numpy as np
        return np.array([0.0, 0.5]), np.array([[1.30, 0.001], [1.29, 0.001]])

    def get_atoms(self, mid, nuklid):
        import numpy as np
        taban = 1.0e20 if nuklid == "U235" else 1.0e18
        return np.array([0.0, 0.5]), np.array([taban, taban * 0.99])


def test_klon_adlari_ve_hacimleri():
    print("\n[TG6] CUBUK CUBUK YANMA: klonlar 'uo2 #k' adini ve kendi hacmini alir")
    from cekirdek import tukenme
    s = _ayirmali_spec()
    ad_by_id, hacim = tukenme._malzeme_haritasi(s)
    klonlar = sorted(a for a in ad_by_id.values() if a.startswith("uo2 #"))
    kontrol("264 klon adlandirildi", len(klonlar) == 264, "-> %d" % len(klonlar))
    kontrol("adlar 'uo2 #1' ... 'uo2 #264'",
            "uo2 #1" in klonlar and "uo2 #264" in klonlar, "-> %r" % klonlar[:3])
    kontrol("kimlik numarasi ad olarak kullanilmiyor",
            not any(a.isdigit() for a in ad_by_id.values()), "-> %r" % list(ad_by_id.values())[:4])
    toplam = sum(hacim[a] for a in klonlar)
    beklenen = tukenme.hacimler(s)["uo2"]["hacim"]
    kontrol("klon hacimleri toplami analitik hacme esit (%.6g = %.6g)" % (toplam, beklenen),
            abs(toplam - beklenen) < 1e-9 * beklenen)
    kontrol("her klonun hacmi var", all(hacim[a] for a in klonlar))
    tek = tukenme._malzeme_haritasi(_spec("pwr_tukenme"))[0]
    kontrol("ayirma kapaliyken adlar degismiyor", "uo2" in tek.values()
            and not any("#" in a for a in tek.values()))


def test_sonuc_oku_klon_yogunlugu():
    print("\n[TG7] SONUC OKUMA: klon malzemelerin yogunlugu ve CSV basligi")
    import tempfile
    import openmc.deplete as d
    from cekirdek import tukenme
    from arayuz.tukenme_sonuc import csv_metni
    s = _ayirmali_spec()
    ad_by_id, _h = tukenme._malzeme_haritasi(s)
    idler = [int(i) for i in ad_by_id if ad_by_id[i].startswith("uo2 #")][:5]
    eski = d.Results
    d.Results = lambda yol: _SahteSonuclar(idler)
    tutucu = tempfile.NamedTemporaryFile(suffix=".h5", delete=False)
    tutucu.write(b"x")
    tutucu.close()
    try:
        tukenme._SONUC_KAYNAGI.clear()
        sonuc = tukenme.sonuc_oku(tutucu.name, s, izlenen=["U235", "Pu239"])
    finally:
        d.Results = eski
        tukenme._SONUC_KAYNAGI.clear()
        os.unlink(tutucu.name)
    adlar = sorted(sonuc["yogunluk"])
    kontrol("sonuc klon adlariyla geliyor", all(a.startswith("uo2 #") for a in adlar)
            and len(adlar) == 5, "-> %r" % adlar)
    yog = sonuc["yogunluk"][adlar[0]]
    kontrol("yogunluk BOS DEGIL (klon hacmi kullanildi)",
            set(yog) == {"U235", "Pu239"} and all(v > 0 for v in yog["U235"]),
            "-> %r" % yog)
    beklenen = 1.0e20 / _h[adlar[0]] * 1e-24
    kontrol("yogunluk = atom / klon hacmi (%.6g)" % beklenen,
            abs(yog["U235"][0] - beklenen) < 1e-12 * beklenen)
    basliklar = csv_metni(sonuc).splitlines()[0]
    kontrol("CSV basliginda klon adi ve yogunluk sutunu",
            "uo2 #1 U235 [atom/b-cm]" in basliklar, "-> %r" % basliklar[:120])


HIZLI = [test_yeni_gruplar, test_yeni_setler, test_zincirde_cozulme,
         test_silinmis_sekmeye_gec_sonuc, test_kapanista_bekleyen_cizim_iptal,
         test_klon_adlari_ve_hacimleri, test_sonuc_oku_klon_yogunlugu]
YAVAS = []
ZINCIR_GEREKEN = [test_zincirde_cozulme, test_silinmis_sekmeye_gec_sonuc,
                  test_kapanista_bekleyen_cizim_iptal]
