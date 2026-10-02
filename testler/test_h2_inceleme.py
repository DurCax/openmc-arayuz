# -*- coding: utf-8 -*-
"""
 test_h2_inceleme.py  --  v3 H2 inceleme bulgulari (python-reviewer + security-reviewer):
   1 Calistir kapisi istek surerken / bozuk spec'e geciste kapali
   2 alt surec cwd'den modul kacirmaya karsi (-P, sabit calisma dizini)
   3 istek bekcisi (watchdog), bellek siniri, piksel ust siniri
   4 SIGTERM ve finalize hatasinda gecici dizin sizmaz
   5 cozucu sinir disi degerleri reddeder
   6 kismi yazmada tam yazma
   9 ardisik cokmede geri cekilme ve durma
  10 kapatilan widget isciyi yeniden baslatmaz
  11 onbellekten boyamada bosta olum cizimi bozmaz; iptal isciye iletilir
  12 stderr halka tamponu sinirli
"""

import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import time

import numpy as np

from testler.ortak_test import kontrol, KOK, ORNEK

_ZAMAN_ASIMI = 60.0


def _uyg():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _bekle(kosul, sure=_ZAMAN_ASIMI):
    from PySide6 import QtCore
    uyg = _uyg()
    bas = time.monotonic()
    while not kosul() and time.monotonic() - bas < sure:
        uyg.processEvents(QtCore.QEventLoop.AllEvents, 20)
        time.sleep(0.002)
    return kosul()


def _spec(ad):
    from cekirdek import sema
    return sema.yukle(os.path.join(ORNEK, ad + ".json"))


def _sahte_isci(govde):
    """'hazir' yazip `govde` Python kodunu calistiran sahte isci komutu."""
    kod = ("import os, sys, time; sys.path.insert(0, %r); "
           "from cekirdek import cizim_sureci as c; "
           "os.write(1, c.cerceve({'tur': 'hazir', 'no': 0, 'surum': 1, 'pid': os.getpid()})); "
           % KOK) + govde
    return (sys.executable, ["-c", kod])


# ----------------------------------------------------------------------------
# 1 kapi
# ----------------------------------------------------------------------------

def test_kapi_istek_surerken_kapali():
    print("\n[H2R-1] kapi: ilk cizim surerken ve iyi -> bozuk spec gecisinde cizildi_mi False")
    _uyg()
    import copy
    from arayuz.onizleme import OnizlemeWidget
    w = OnizlemeWidget()
    try:
        w.spec_ayarla(_spec("pwr_17x17"))
        kontrol("spec verildi, cizim yok: kapi kapali", not w.cizildi_mi())
        w._ciz()
        kontrol("istek suruyor: kapi kapali", not w.cizildi_mi())
        w.bekle(_ZAMAN_ASIMI)
        kontrol("cizim bitti: kapi acik", w.cizildi_mi())
        bozuk = copy.deepcopy(w.spec)
        bozuk["malzemeler"] = []
        w.spec_ayarla(bozuk)
        kontrol("bozuk spec verildi (gecikme suruyor): kapi hemen kapali", not w.cizildi_mi())
        w._ciz()
        kontrol("bozuk istek suruyor: kapi kapali", not w.cizildi_mi())
        w.bekle(_ZAMAN_ASIMI)
        kontrol("bozuk istek bitti: kapi kapali", not w.cizildi_mi())
    finally:
        w.kapat()


# ----------------------------------------------------------------------------
# 2 modul kacirma
# ----------------------------------------------------------------------------

def test_alt_surec_cwd_modul_kacirma():
    print("\n[H2R-2] alt surec: calisma dizinindeki sahte 'cekirdek' paketi yuklenmez")
    from cekirdek import giris, yollar
    program, arg = giris.alt_surec_komutu(giris.ALT_CIZIM, [])
    kontrol("komutta -P (Python >= 3.11: guvensiz yol eklenmez)",
            sys.version_info < (3, 11) or arg[0] == "-P", "-> %s" % arg)
    with tempfile.TemporaryDirectory() as tuzak:
        os.makedirs(os.path.join(tuzak, "cekirdek"))
        for ad in ("__init__.py", "giris.py"):
            with open(os.path.join(tuzak, "cekirdek", ad), "w", encoding="utf-8") as f:
                f.write("import sys\nsys.exit(99)\n")
        ortam = dict(os.environ)
        yol = giris.alt_surec_pythonpath(ortam.get("PYTHONPATH"))
        if yol:
            ortam["PYTHONPATH"] = yol
        r = subprocess.run([program] + arg + ["fazla"], cwd=tuzak, env=ortam,
                           capture_output=True, text=True, timeout=120)
    kontrol("gercek dagitici calisti (kullanim hatasi 2, sahte 99 degil)", r.returncode == 2,
            "-> %s %s" % (r.returncode, r.stderr[-200:]))
    _uyg()
    from arayuz.onizleme_istemci import CizimIstemcisi
    ist = CizimIstemcisi()
    ist.baslat()
    try:
        kontrol("isci calisma dizini paket koku",
                os.path.realpath(ist._surec.workingDirectory()) == os.path.realpath(
                    yollar.paket_koku()), "-> %s" % ist._surec.workingDirectory())
    finally:
        ist.kapat()


# ----------------------------------------------------------------------------
# 3 bekci, bellek, piksel
# ----------------------------------------------------------------------------

def test_istek_bekcisi():
    print("\n[H2R-3] bekci: yanit vermeyen isci zaman asiminda oldurulur, acik ileti")
    _uyg()
    from arayuz.onizleme_istemci import CizimIstemcisi
    ist = CizimIstemcisi(komut=_sahte_isci("time.sleep(600)"), zaman_asimi_ms=800)
    coktu = []
    ist.coktu.connect(coktu.append)
    try:
        _bekle(lambda: (ist.baslat() or True) and ist.hazir_mi(), 30)
        pid = ist.pid()
        ist.iste({"tur": "ciz", "spec": {}, "kesitler": [{"eksen": "xy", "piksel": 16}]})
        kontrol("zaman asiminda ileti", _bekle(lambda: bool(coktu), 20)
                and "ağır" in coktu[0], "-> %s" % coktu)
        kontrol("mesgul degil", not ist.mesgul_mu())
        kontrol("asili isci olduruldu", ist.pid() != pid)
    finally:
        ist.kapat()


def test_bellek_siniri_ve_piksel():
    print("\n[H2R-3b] bellek siniri (gerekceli, ayarlanabilir) ve piksel ust siniri")
    from cekirdek import cizim_sureci as cs
    kontrol("piksel ust siniri arayuzun en buyugune yakin (<= 2048)", cs.PIKSEL_EN_COK <= 2048)
    try:
        cs.istegi_dogrula({"tur": "ciz", "no": 1, "spec": {},
                           "kesitler": [{"eksen": "xy", "piksel": 4096}]})
        red = False
    except cs.ProtokolHatasi:
        red = True
    kontrol("4096 px reddedilir", red)
    kontrol("varsayilan sinir cekirdek sayisiyla buyur",
            cs.bellek_siniri({}, 8) < cs.bellek_siniri({}, 64))
    kontrol("ortamdan MB ile ayarlanir", cs.bellek_siniri({cs.BELLEK_ORTAMI: "2048"}, 8)
            == 2048 * 1024 * 1024)
    kontrol("0 sinirsiz (None)", cs.bellek_siniri({cs.BELLEK_ORTAMI: "0"}, 8) is None)
    kontrol("bozuk deger varsayilana duser",
            cs.bellek_siniri({cs.BELLEK_ORTAMI: "abc"}, 8) == cs.bellek_siniri({}, 8))


# ----------------------------------------------------------------------------
# 4 gecici dizin
# ----------------------------------------------------------------------------

def test_kapat_finalize_hatasinda_temizler(monkeypatch):
    print("\n[H2R-4] Oturum.kapat: finalize hata verse de calisma dizini doner, gecici dizin silinir")
    import openmc.lib
    from cekirdek import cizim_sureci as cs
    eski = os.getcwd()
    dizin = tempfile.mkdtemp(prefix="openmc_arayuz_cizim_")
    oturum = cs.Oturum()
    oturum._dizin, oturum._eski_dizin = dizin, eski
    os.chdir(dizin)

    def bozuk_finalize():
        raise RuntimeError("finalize bozuk")
    monkeypatch.setattr(openmc.lib, "is_initialized", True)
    monkeypatch.setattr(openmc.lib, "finalize", bozuk_finalize)
    try:
        oturum.kapat()
        hata = False
    except RuntimeError:
        hata = True
    finally:
        os.chdir(eski) if os.getcwd() != eski else None
    kontrol("hata yutulmadi", hata)
    kontrol("dizin silindi", not os.path.exists(dizin))
    kontrol("durum sifirlandi", oturum.ozet is None and oturum._dizin is None)


def test_sigterm_gecici_dizin_sizdirmaz():
    print("\n[H2R-4b] isci SIGTERM alinca (hazirla sonrasi) gecici dizinini siler")
    from cekirdek import cizim_sureci as cs, giris
    with tempfile.TemporaryDirectory() as tmp:
        program, arg = giris.alt_surec_komutu(giris.ALT_CIZIM, [])
        ortam = dict(os.environ, TMPDIR=tmp)
        yol = giris.alt_surec_pythonpath(ortam.get("PYTHONPATH"))
        if yol:
            ortam["PYTHONPATH"] = yol
        p = subprocess.Popen([program] + arg, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, env=ortam, cwd=KOK)
        try:
            p.stdin.write(cs.cerceve({"tur": "kontrol", "no": 1, "spec": _spec("pwr_17x17")}))
            p.stdin.flush()
            bas = time.monotonic()
            while time.monotonic() - bas < 60 and not any(
                    a.startswith("openmc_arayuz_cizim_") for a in os.listdir(tmp)):
                time.sleep(0.02)
            olustu = any(a.startswith("openmc_arayuz_cizim_") for a in os.listdir(tmp))
            time.sleep(0.5)
            p.send_signal(signal.SIGTERM)
            kod = p.wait(30)
        finally:
            if p.poll() is None:
                p.kill()
                p.wait()
        kalan = [a for a in os.listdir(tmp) if a.startswith("openmc_arayuz_cizim_")]
    kontrol("oturum dizini olustu (test anlamli)", olustu)
    kontrol("SIGTERM sonrasi dizin kalmadi", not kalan, "-> %s" % kalan)
    kontrol("cikis kodu SIGTERM'e ozgu (143 = 128 + 15)", kod == 128 + signal.SIGTERM,
            "-> %s" % kod)


# ----------------------------------------------------------------------------
# 5 cozucu
# ----------------------------------------------------------------------------

def _ham(baslik, veri=b""):
    from cekirdek import cizim_sureci as cs
    b = json.dumps(baslik).encode() if not isinstance(baslik, bytes) else baslik
    return cs._SIHIR + len(b).to_bytes(4, "big") + len(veri).to_bytes(8, "big") + b + veri


def test_cozucu_sinir_disi():
    print("\n[H2R-5] cozucu: tasan sekil, kesik baslik, eksik veri, yinelenen ad, bool -> ProtokolHatasi")
    from cekirdek import cizim_sureci as cs
    durumlar = {
        "tasan sekil": _ham({"tur": "a", "_diziler": [
            {"ad": "x", "dtype": "int32", "sekil": [10 ** 12, 10 ** 12]}]}),
        "kesik baslik (bozuk JSON)": _ham(b'{"tur": "a", "_diz'),
        "derin ic ice JSON": _ham(b"[" * 100000 + b"]" * 100000),
        "eksik dizi verisi": _ham({"tur": "a", "_diziler": [
            {"ad": "x", "dtype": "int32", "sekil": [4]}]}, b"\0" * 8),
        "yinelenen ad": _ham({"tur": "a", "_diziler": [
            {"ad": "x", "dtype": "uint8", "sekil": [1]},
            {"ad": "x", "dtype": "uint8", "sekil": [1]}]}, b"\0\0"),
        "bool sekil": _ham({"tur": "a", "_diziler": [
            {"ad": "x", "dtype": "uint8", "sekil": [True]}]}, b"\0"),
        "ondalik sekil": _ham({"tur": "a", "_diziler": [
            {"ad": "x", "dtype": "uint8", "sekil": [1.5]}]}, b"\0"),
        "cok boyut": _ham({"tur": "a", "_diziler": [
            {"ad": "x", "dtype": "uint8", "sekil": [1] * 40}]}, b"\0"),
    }
    gecen = []
    for ad, veri in durumlar.items():
        try:
            cs.CerceveCozucu().besle(veri)
            gecen.append(ad)
        except cs.ProtokolHatasi:
            pass
    kontrol("hepsi ProtokolHatasi", not gecen, "-> gecti: %s" % gecen)


# ----------------------------------------------------------------------------
# 6 tam yazma
# ----------------------------------------------------------------------------

class _KisaYazan(io.RawIOBase):
    """Her cagrida en cok 7 bayt yazar (kismi yazma)."""

    def __init__(self):
        self.veri = bytearray()

    def writable(self):
        return True

    def write(self, b):
        parca = bytes(memoryview(b)[:7])
        self.veri += parca
        return len(parca)


def test_kanal_kismi_yazmada_tam_yazar():
    print("\n[H2R-6] Kanal.gonder: kismi yazan akista cerceve eksiksiz gider")
    from cekirdek import cizim_sureci as cs
    akis = _KisaYazan()
    dizi = np.arange(100, dtype=np.int32).reshape(10, 10)
    cs.Kanal(0, akis).gonder({"tur": "kesit", "no": 3}, {"geom": dizi})
    c = cs.CerceveCozucu().besle(bytes(akis.veri))
    kontrol("tek cerceve, dizi ayni", len(c) == 1 and np.array_equal(c[0].diziler["geom"], dizi))


# ----------------------------------------------------------------------------
# 9 geri cekilme, 10 kapandi, 11 iptal, 12 stderr
# ----------------------------------------------------------------------------

def test_ardisik_cokmede_durur():
    print("\n[H2R-9] istemci: ardisik cokmede geri cekilerek yeniden baslar, 3. cokmede durur")
    _uyg()
    from arayuz import onizleme_istemci as oi
    ist = oi.CizimIstemcisi(komut=_sahte_isci("sys.exit(1)"))
    hazir, coktu = [], []
    ist.hazir.connect(lambda: hazir.append(time.monotonic()))
    ist.coktu.connect(coktu.append)
    try:
        ist.baslat()
        _bekle(lambda: len(coktu) >= oi.EN_COK_ARDISIK_COKME, 30)
        _bekle(lambda: False, 1.5)        # durduysa yeni baslatma olmaz
        kontrol("%d cokmeden sonra durdu" % oi.EN_COK_ARDISIK_COKME,
                len(coktu) == oi.EN_COK_ARDISIK_COKME and not ist.calisiyor_mu(),
                "-> %d cokme" % len(coktu))
        araliklar = np.diff(hazir).tolist()
        kontrol("geri cekilme buyur", len(araliklar) >= 2 and araliklar[1] > araliklar[0],
                "-> %s" % araliklar)
        kontrol("son ileti durdugunu soyler", "durduruldu" in coktu[-1], "-> %s" % coktu[-1:])
        ist.iste({"tur": "kontrol", "spec": {}})
        kontrol("sonraki istekte yeniden denenir", _bekle(lambda: len(hazir) > len(coktu), 10))
    finally:
        ist.kapat()


def test_kapatilan_widget_isciyi_baslatmaz():
    print("\n[H2R-10] kapat() sonrasi cizim istegi isciyi yeniden baslatmaz")
    _uyg()
    from arayuz.onizleme import OnizlemeWidget
    w = OnizlemeWidget()
    w.spec_ayarla(_spec("pwr_17x17"))
    w.kapat()
    w._ciz()
    w.iste()
    _bekle(lambda: False, 0.5)
    kontrol("isci calismiyor", not w._istemci.calisiyor_mu() and not w.mesgul_mu())
    w._istemci.baslat()
    kontrol("istemci de kapali kalir", not w._istemci.calisiyor_mu())


def test_onbellek_boyamasinda_bosta_olum():
    print("\n[H2R-11] onbellekten boyama surerken bosta isci olumu cizimi basarisiz saymaz")
    _uyg()
    from arayuz.onizleme import OnizlemeWidget
    w = OnizlemeWidget()
    try:
        w.spec_ayarla(_spec("pwr_3b"))
        w._ciz()
        w.bekle(_ZAMAN_ASIMI)
        w.renklendirme.setCurrentIndex(1)       # onbellekten, isciye gitmez
        kontrol("onbellek zinciri basladi", w._istek is not None and w._istek["no"] is None)
        w._coktu("Önizleme süreci beklenmedik biçimde sonlandı (test)")
        w.bekle(_ZAMAN_ASIMI)
        kontrol("cizim gecerli, hata yok", w.cizildi_mi() and w.son_hata() is None,
                "-> %s" % w.son_hata())
    finally:
        w.kapat()


def test_iptal_isciye_iletilir():
    print("\n[H2R-11b] istemci.iptal isciye 'iptal' istegi yollar; isci isi birakir")
    from cekirdek import cizim_sureci as cs
    kontrol("iptal istegi gecerli", cs.istegi_dogrula({"tur": "iptal", "no": 4})["tur"] == "iptal")
    oku, yaz = os.pipe()
    istek = {"tur": "ciz", "no": 1, "spec": {"ad": "A"},
             "kesitler": [{"eksen": "xy", "piksel": 16}, {"eksen": "xz", "piksel": 16}]}

    class _Oturum:
        def hazirla(self, spec):
            return False

        def ozellikler(self):
            return {"sinir_kutu": [1.0, 1.0], "yukseklik": None, "renkler": {}, "gosterge": []}

        def kesit(self, eksen, piksel, cakisma=False):
            os.write(yaz, cs.cerceve({"tur": "iptal", "no": 2}))
            return (1.0, 1.0), np.zeros((piksel, piksel, 3), np.int32), []

        def kapat(self):
            pass
    os.write(yaz, cs.cerceve(istek))
    cikis = io.BytesIO()
    kanal = cs.Kanal(oku, cikis)
    gelen = kanal.sonraki()
    cs.isle(cs.istegi_dogrula(gelen.baslik), _Oturum(), kanal)
    os.close(yaz)
    kontrol("dongu iptal istegini atlar", cs.dongu(kanal, _Oturum()) == 0)
    os.close(oku)
    sonlar = [c.baslik["durum"] for c in cs.CerceveCozucu().besle(cikis.getvalue())
              if c.baslik["tur"] == "son"]
    kontrol("is birakildi (iptal), ikinci kesit cizilmedi", sonlar[:1] == ["iptal"], "-> %s" % sonlar)


def test_stderr_halka_tamponu():
    print("\n[H2R-12] istemci stderr'i sinirli halka tamponunda tutar")
    _uyg()
    from arayuz import onizleme_istemci as oi
    ist = oi.CizimIstemcisi(komut=_sahte_isci(
        "sys.stderr.write('x' * 300000); sys.stderr.write('SON'); sys.stderr.flush(); "
        "time.sleep(600)"))
    try:
        ist.baslat()
        _bekle(lambda: ist.hazir_mi() and ist.stderr_ozeti().endswith("SON"), 20)
        ozet = ist.stderr_ozeti()
        kontrol("tampon sinirli ve son kismi tutar",
                len(ozet) <= oi.STDERR_SINIRI and ozet.endswith("SON"), "-> %d" % len(ozet))
    finally:
        ist.kapat()


HIZLI = [test_kapi_istek_surerken_kapali, test_alt_surec_cwd_modul_kacirma, test_istek_bekcisi,
         test_bellek_siniri_ve_piksel, test_kapat_finalize_hatasinda_temizler,
         test_sigterm_gecici_dizin_sizdirmaz, test_cozucu_sinir_disi,
         test_kanal_kismi_yazmada_tam_yazar, test_ardisik_cokmede_durur,
         test_kapatilan_widget_isciyi_baslatmaz, test_onbellek_boyamasinda_bosta_olum,
         test_iptal_isciye_iletilir, test_stderr_halka_tamponu]
YAVAS = []
