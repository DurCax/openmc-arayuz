# -*- coding: utf-8 -*-
"""
 test_y2_inceleme.py  --  v3 Y2 inceleme bulgulari (python/security): bindirme
                          boyut siniri, okuyucu is parcacigi kapanisi, istek
                          sirasi + eszamanli cokme, H2 hucre kanalinda cakisma
                          (-4), isci buyukluk sinirlari, kaynak ornekleme butcesi
                          ve iptal, statepoint kenar durumlari, istek basina bekci
"""

import math
import os
import sys
import tempfile
import time

import numpy as np

from testler.ortak_test import kontrol, KOK

_ZAMAN = 30.0


def _uyg():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _bekle(kosul, sure=_ZAMAN):
    from PySide6 import QtCore
    uyg = _uyg()
    bas = time.monotonic()
    while not kosul() and time.monotonic() - bas < sure:
        uyg.processEvents(QtCore.QEventLoop.AllEvents, 20)
        time.sleep(0.002)
    return kosul()


def _reddedilir(istek):
    from cekirdek import cizim_sureci as cs
    try:
        cs.istegi_dogrula(istek)
    except cs.ProtokolHatasi:
        return True
    return False


# ----------------------------------------------------------------------------
# HIGH 1: bindirme boyutu
# ----------------------------------------------------------------------------

def test_bindirme_asiri_en_boy_sinirli():
    print("\n[Y2R-1] bindirme: 400:1 en-boy oraninda raster satir sayisi sinirli")
    from cekirdek import cizim_sureci as cs
    from cekirdek.mesh_tally.sonuc import MeshSonuc
    from arayuz.goruntuleyici import bindirme as bd, gorunum as gr
    izg = (np.array([-1.0, 1.0]), np.array([-1.0, 1.0]), np.linspace(-200, 200, 5))
    o = np.ones((1, 1, 4, 1, 1, 1))
    s = MeshSonuc("t", "duzenli", izg, (0.0, 0.0, 0.0), ("flux",), ("total",), None, o,
                  0.01 * o, True)
    g = gr.Gorunum("xz", (0.0, 0.0, 0.0), (1.0, 400.0), 400)
    # Act
    r = bd.raster(s, o[..., 0, 0, 0], np.zeros((1, 1, 4), bool), g)
    r_geom = bd.raster(s, o[..., 0, 0, 0], np.zeros((1, 1, 4), bool), g, sekil=(2048, 16))
    # Assert
    kontrol("satir <= PIKSEL_EN_COK", r.deger.shape[0] <= cs.PIKSEL_EN_COK,
            "-> %s" % (r.deger.shape,))
    kontrol("geom sekli verilince ondan (<= 2048 x 16)", r_geom.deger.shape[0] <= 2048
            and r_geom.deger.shape[1] <= 16, "-> %s" % (r_geom.deger.shape,))
    kontrol("deger yine dogru (1)", np.nanmax(r.deger) == 1.0)


# ----------------------------------------------------------------------------
# HIGH 3: istek sirasi + eszamanli cokme
# ----------------------------------------------------------------------------

def test_istek_sirasi_eszamanli_cokme():
    print("\n[Y2R-2] istek sirasi: gonderim sirasinda cokme (sifirla) sira kalici mesgul kalmaz")
    from arayuz.goruntuleyici.istek_sirasi import IstekSirasi
    sira = None
    giden = []

    def gonder(istek):
        giden.append(istek["ad"])
        if istek["ad"] == "olu":
            sira.sifirla()               # istemci iste() icinde coktu yaydi
        return len(giden)

    sira = IstekSirasi(gonder)
    sira.iste("kesit", {"ad": "olu"})
    kontrol("cokme sonrasi mesgul degil", not sira.mesgul_mu())
    sira.iste("kaynak", {"ad": "yeni"})
    kontrol("sonraki istek hemen gider", giden == ["olu", "yeni"] and sira.tur(2) == "kaynak")


# ----------------------------------------------------------------------------
# MEDIUM 4: H2 hucre kanalinda cakisma
# ----------------------------------------------------------------------------

def test_hucre_goruntusu_cakisma_dort():
    print("\n[Y2R-3] onizleme boyama: hucre kanalinda -4 (cakisma) cakisma rengiyle boyanir")
    from arayuz import onizleme_boyama as ob
    geom = np.zeros((1, 3, 3), np.int32)
    geom[0, :, 0] = [5, -4, -2]
    img = ob.hucre_goruntusu(geom, None, None, cakisma_rengi=(0.0, 1.0, 0.0))
    kontrol("-4 cakisma rengi", tuple(img[0, 1]) == (0, 255, 0, 255), "-> %s" % (img[0, 1],))
    kontrol("-2 saydam", img[0, 2, 3] == 0)


# ----------------------------------------------------------------------------
# MEDIUM 5: isci buyukluk sinirlari
# ----------------------------------------------------------------------------

def _isin(**ek):
    istek = {"tur": "isin", "no": 1, "spec": {}, "kamera": [20.0, 0.0, 0.0],
             "bakis": [0.0, 0.0, 0.0], "yukari": [0.0, 0.0, 1.0], "gorus": 40.0,
             "piksel": [64, 48]}
    istek.update(ek)
    return istek


def test_isci_buyukluk_sinirlari():
    print("\n[Y2R-4] isci: genislik/merkez/kamera/bakis/yukari/isik buyukluk sinirlari; "
          "yukari bakisa paralel reddedilir")
    from cekirdek import cizim_goruntu as cg
    kesit = {"tur": "ciz", "no": 1, "spec": {}}
    kotu_kesit = [{"genislik": [1e9, 1.0]}, {"genislik": [1e-9, 1.0]},
                  {"merkez": [1e9, 0.0, 0.0]}, {"genislik": [float("inf"), 1.0]}]
    red_kesit = [k for k in kotu_kesit if _reddedilir(dict(kesit, kesitler=[
        dict({"eksen": "xy", "piksel": 64}, **k)]))]
    kotu_isin = [dict(kamera=[1e9, 0.0, 0.0]), dict(bakis=[0.0, 1e9, 0.0]),
                 dict(isik=[0.0, 0.0, -1e9]), dict(yukari=[1.0, 0.0, 0.0]),
                 dict(yukari=[1e9, 0.0, 1.0])]
    red_isin = [k for k in kotu_isin if _reddedilir(_isin(**k))]
    kontrol("kesit: dev/kucuk/sonsuz reddedilir", len(red_kesit) == len(kotu_kesit),
            "-> %d/%d" % (len(red_kesit), len(kotu_kesit)))
    kontrol("isin: dev ve paralel reddedilir", len(red_isin) == len(kotu_isin),
            "-> %d/%d" % (len(red_isin), len(kotu_isin)))
    kontrol("sinir arayuzle ayni", cg.KOORDINAT_SINIRI == 1.0e6)
    from arayuz.goruntuleyici import gorunum as gr
    kontrol("gorunum sinirlari ciszim_goruntu'den", gr.EN_BUYUK_GENISLIK == cg.KOORDINAT_SINIRI
            and gr.EN_KUCUK_GENISLIK == cg.GENISLIK_EN_AZ)


# ----------------------------------------------------------------------------
# MEDIUM 6: kaynak ornekleme
# ----------------------------------------------------------------------------

def test_kaynak_dogrulama_ve_iptal():
    print("\n[Y2R-5] kaynak: sonsuz Box ve inf/NaN siddet reddedilir; iptal partiler arasinda")
    import openmc
    from cekirdek import cizim_goruntu as cg
    sonsuz = openmc.IndependentSource(space=openmc.stats.Box((-1, -1, -np.inf), (1, 1, 1)))
    nan = openmc.IndependentSource(space=openmc.stats.Point(), strength=1.0)
    nan.strength = float("nan")
    hatalar = []
    for k in (sonsuz, nan):
        try:
            cg.ayar_kaynagi([k], frozenset(), 5, 1)
        except ValueError as e:
            hatalar.append(str(e))
    kontrol("sonsuz kutu ve NaN siddet ValueError", len(hatalar) == 2, "-> %s" % hatalar)
    kisitli = openmc.IndependentSource(space=openmc.stats.Box((-1,) * 3, (1,) * 3),
                                       constraints={"fissionable": True})
    eski = cg._fisil_noktalar
    cg._fisil_noktalar = lambda n, f: np.arange(len(n)) % 10 == 0      # %10 kabul
    try:
        try:
            cg.ayar_kaynagi([kisitli], frozenset({1}), cg.KAYNAK_EN_COK, 1, iptal=lambda: True)
            iptal = False
        except cg.Iptal:
            iptal = True
    finally:
        cg._fisil_noktalar = eski
    kontrol("iptal istenince cg.Iptal", iptal)
    kontrol("deneme butcesi tanimli", cg.KAYNAK_DENEME_EN_COK >= cg.KAYNAK_EN_COK)


def test_isle_kaynak_iptali_yanit():
    print("\n[Y2R-6] isci: kaynak ornekleme iptal edilirse 'son' durumu iptal")
    import io
    from cekirdek import cizim_sureci as cs, cizim_goruntu as cg

    class _O:
        def hazirla(self, spec):
            return False

        def ozellikler(self):
            return {"sinir_kutu": [1.0, 1.0], "yukseklik": None, "renkler": {}, "gosterge": []}

        def kaynak(self, istek, iptal=None):
            raise cg.Iptal()

    oku, yaz = os.pipe()
    os.close(yaz)
    cikis = io.BytesIO()
    durum = cs.isle(cs.istegi_dogrula({"tur": "kaynak", "no": 2, "spec": {}, "sayi": 5}),
                    _O(), cs.Kanal(oku, cikis))
    os.close(oku)
    son = cs.CerceveCozucu().besle(cikis.getvalue())[-1].baslik
    kontrol("durum iptal", durum == cs.DURUM_IPTAL and son["durum"] == cs.DURUM_IPTAL)


# ----------------------------------------------------------------------------
# MEDIUM 7: statepoint kenar durumlari
# ----------------------------------------------------------------------------

def _banka(yol, n, alanlar=("r", "E")):
    import h5py
    xyz = np.dtype([("x", "<f8"), ("y", "<f8"), ("z", "<f8")])
    tur = np.dtype([(a, xyz if a == "r" else "<f8") for a in alanlar])
    b = np.zeros(n, dtype=tur)
    if "r" in alanlar:
        b["r"]["x"] = np.arange(float(n))
    with h5py.File(yol, "w") as f:
        f.attrs["source_present"] = 1
        f.create_dataset("source_bank", data=b)


def test_statepoint_kenar_durumlari():
    print("\n[Y2R-7] statepoint: eksik 'r' acik ileti, goreli yol reddi, adimli alt kume")
    from cekirdek import cizim_goruntu as cg
    d = tempfile.mkdtemp(prefix="y2_sp2_")
    eksik = os.path.join(d, "eksik.h5")
    _banka(eksik, 5, alanlar=("E",))
    try:
        cg.statepoint_kaynagi(eksik, 5, 1)
        metin = ""
    except ValueError as e:
        metin = str(e)
    kontrol("eksik r alani acik ileti", "'r'" in metin, "-> %s" % metin)
    kontrol("goreli yol reddedilir", _reddedilir({"tur": "kaynak", "no": 1, "spec": {},
                                                  "sayi": 5, "statepoint": "sp.h5"}))
    buyuk = os.path.join(d, "buyuk.h5")
    _banka(buyuk, 1000)
    r, toplam = cg.statepoint_kaynagi(buyuk, 10, 3)
    adim = np.diff(r[:, 0])
    kontrol("10 nokta, esit adim (100)", len(r) == 10 and toplam == 1000
            and np.all(adim == 100.0), "-> %s" % r[:, 0])
    tum, _t = cg.statepoint_kaynagi(buyuk, 5000, 3)
    kontrol("sayi >= toplam: hepsi", len(tum) == 1000)


# ----------------------------------------------------------------------------
# MEDIUM 8: istek basina bekci
# ----------------------------------------------------------------------------

_ASILI_ISCI = r"""
import os, sys, time
sys.path.insert(0, %r)
from cekirdek import cizim_sureci as cs
cikis = os.fdopen(sys.stdout.fileno(), "wb", buffering=0)
cikis.write(cs.cerceve({"tur": "hazir", "no": 0, "surum": 1, "pid": os.getpid()}))
while True:
    time.sleep(1)
"""


def test_bekci_istek_basina():
    print("\n[Y2R-8] bekci: asili isci oldurulur; yeni istek bekciyi ertelemez; ilk istek "
          "daha uzun butce")
    _uyg()
    from arayuz.onizleme_istemci import CizimIstemcisi
    komut = (sys.executable, ["-c", _ASILI_ISCI % KOK])
    ist = CizimIstemcisi(komut=komut, zaman_asimi_ms=400, ilk_zaman_asimi_ms=400)
    coktu = []
    ist.coktu.connect(coktu.append)
    try:
        ist.baslat()
        kontrol("isci hazir", _bekle(ist.hazir_mi, 10))
        t0 = time.monotonic()
        ist.iste({"tur": "kontrol", "spec": {}})
        _bekle(lambda: False, 0.25)
        ist.iste({"tur": "kontrol", "spec": {}})          # ertelememeli
        _bekle(lambda: bool(coktu), 5)
        sure = time.monotonic() - t0
        kontrol("asili isci oldu (coktu)", bool(coktu))
        kontrol("ikinci istek bekciyi ertelemedi (< 0.6 s)", sure < 0.6, "-> %.2f s" % sure)
    finally:
        ist.kapat()
    ilk = CizimIstemcisi(komut=komut, zaman_asimi_ms=400, ilk_zaman_asimi_ms=5000)
    kontrol("ilk istek butcesi (soguk hazirla)", ilk._butce_ms() == 5000)
    ilk.kapat()


# ----------------------------------------------------------------------------
# HIGH 2 + MEDIUM 9: okuyucu kapanisi, tekil pencere, bayat durum
# ----------------------------------------------------------------------------

def test_okuyucu_kapanisi_ve_tekil():
    print("\n[Y2R-9] okuma surerken kapat: butun okuyucular beklenir; kapattiktan sonra ac() "
          "yeni pencere; eski okuyucunun sonucu atilir (kusak)")
    _uyg()
    from arayuz.goruntuleyici import okuyucu, pencere as gp
    eski_oku = okuyucu.mt.oku

    def yavas(yol):
        time.sleep(0.4)
        return ([], [("x", yol)])

    okuyucu.mt.oku = yavas
    try:
        p = gp.ac(None)
        p.statepoint_ayarla("/yok/a.h5")
        p.statepoint_ayarla("/yok/b.h5")
        okuyucular = list(p._okuyucular)
        p.close()
        kontrol("iki okuyucu da bitti", all(o.isFinished() for o in okuyucular))
        kontrol("_TEKIL kapanista temizlendi", "pencere" not in gp._TEKIL)
        p2 = gp.ac(None)
        kontrol("ac() yeni pencere", p2 is not p and p2.isVisible())
        sonuclar = []
        p2.p_tally.sonuclari_ayarla = lambda yol, s: sonuclar.append(yol)
        p2.statepoint_ayarla("/yok/a.h5")
        p2.statepoint_ayarla("/yok/a.h5")
        _bekle(lambda: not p2.mesgul_mu(), 5)
        kontrol("ayni yol iki okuma: yalniz son kusak teslim", sonuclar.count("/yok/a.h5") == 1,
                "-> %s" % sonuclar)
        p2.close()
    finally:
        okuyucu.mt.oku = eski_oku


def test_spec_ayarla_bayat_durum():
    print("\n[Y2R-10] spec_ayarla meta'yi temizler; kaynak anahtari statepoint mtime icerir; "
          "basarisiz kaynak istegi her boyamada tekrarlanmaz")
    _uyg()
    from arayuz.goruntuleyici.pencere import GoruntuleyiciPenceresi

    class _I:
        def __init__(self):
            from PySide6 import QtCore

            class _S(QtCore.QObject):
                cerceve_geldi = QtCore.Signal(object)
                coktu = QtCore.Signal(str)
            self._s = _S()
            self.cerceve_geldi, self.coktu = self._s.cerceve_geldi, self._s.coktu
            self.giden = []

        def iste(self, istek):
            self.giden.append(istek)
            return len(self.giden)

        def kapat(self):
            pass

    ist = _I()
    p = GoruntuleyiciPenceresi({"ad": "a"}, istemci=ist)
    try:
        p._meta = {"sinir_kutu": [1, 1], "yukseklik": None, "renkler": {}}
        p.spec_ayarla({"ad": "b"})
        kontrol("meta temizlendi", p._meta is None)
        d = tempfile.mkdtemp(prefix="y2_mt_")
        yol = os.path.join(d, "statepoint.1.h5")
        _banka(yol, 3)
        p.statepoint = yol
        p.p_kaynak.kaynak.setCurrentIndex(1)
        a1 = p._kaynak_anahtari()
        os.utime(yol, (time.time() + 10, time.time() + 10))
        kontrol("mtime degisince anahtar degisir", p._kaynak_anahtari() != a1)
        p.p_kaynak.kaynak.setCurrentIndex(0)
        p._istenen_kaynak = p._kaynak_anahtari()
        p._kaynak_hatasi = p._kaynak_anahtari()
        n = len(ist.giden)
        p._kaynak_iste()
        kontrol("basarisiz anahtar yeniden istenmez", len(ist.giden) == n)
    finally:
        p.kapat()


HIZLI = [test_bindirme_asiri_en_boy_sinirli, test_istek_sirasi_eszamanli_cokme,
         test_hucre_goruntusu_cakisma_dort, test_isci_buyukluk_sinirlari,
         test_kaynak_dogrulama_ve_iptal, test_isle_kaynak_iptali_yanit,
         test_statepoint_kenar_durumlari, test_bekci_istek_basina,
         test_okuyucu_kapanisi_ve_tekil, test_spec_ayarla_bayat_durum]
YAVAS = []
