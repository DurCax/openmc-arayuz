# -*- coding: utf-8 -*-
"""
 test_sonuc_hata_yollari.py  --  sonuc_oku / Calistir sekmesi hata yollari
                                 (D1-Kapanis, sessiz hata incelemesi A1-A7)

 HATA (inceleme, dogrulandi):
   A1 guc_toplam_ref tally'si yokken korunum denetimi iz birakmadan kayboluyordu.
   A2 Calistir sekmesi kosucu.calistir'i kullanmadigi icin dogrula.kapi GUI
      kosusunu korumuyordu (izin 250 ms debounce'lu ve veri denetimsiz).
   A3 entropi okuma hatasi "entropi kapali" ile ayni [] idi.
   A4 hedef payi: LookupError (eski kosu) ile gercek hata ayni None idi.
   A5 tepe_faktorleri korumasizdi: sonuc_oku cokuyordu.
   A6 _terminal hata yolunda tum_kontroller'i ikinci kez cagiriyordu.
   A7 guc haritasi korunum notunu "denetlenemedi: ... denetlenemedi." diye
      iki kez yaziyordu.

 HIZLI: sahte StatePoint (test_guc_sonuc yardimcilari), nukleer veri yok.
"""

import io
import logging
import os
import shutil
import tempfile
from contextlib import redirect_stdout

from testler.ortak_test import kontrol, ORNEK
from testler.test_guc_sonuc import _Tally, _oku, _sahte_sp, _TOPLAM_2X2


def _uyg():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_ref_yok_notu():
    print("\n[SH1] Korunum: guc_toplam_ref yok -> korunum_notu, satirlarda gorunur")
    from cekirdek import kosucu
    s, _log = _oku(_sahte_sp(ref=None))
    g = s.get("guc") or {}
    notu = g.get("korunum_notu") or ""
    kontrol("korunum_notu 'Referans tally yok'", "Referans tally yok" in notu, "-> %r" % notu)
    kontrol("korunum hesaplanmadi", "korunum" not in g and "korunum_hata" not in g)
    satirlar = kosucu.korunum_satirlari(g)
    kontrol("korunum_satirlari notu gosterir", any("Referans tally yok" in x for x in satirlar),
            "-> %r" % satirlar)


def test_hedef_payi_hata_ayrimi():
    print("\n[SH2] Hedef payi: eski kosu (LookupError) ile okuma hatasi ayri")
    from cekirdek import guc
    s_eski, log_eski = _oku(_sahte_sp(ref=_TOPLAM_2X2, model=None))
    g_eski = s_eski["guc"]
    kontrol("eski kosu: pay None, hata alani yok",
            g_eski.get("hedef_payi") is None and "hedef_payi_hata" not in g_eski,
            "-> %r" % sorted(g_eski))
    s, log = _oku(_sahte_sp(ref=_TOPLAM_2X2,
                            model=_Tally("guc_model_toplam", hata=OSError("hdf5 bozuk 11"))))
    g = s["guc"]
    kontrol("gercek hata: hedef_payi_hata metni", g.get("hedef_payi_hata") == "hdf5 bozuk 11",
            "-> %r" % g.get("hedef_payi_hata"))
    kontrol("gercek hata ERROR + exc_info",
            any(sv >= logging.ERROR and e for sv, _m, e in log), "-> %r" % log)
    f = g["faktorler"]
    m = guc.mutlak_guc(f, 1.6e6, 100.0)
    eski = " ".join(guc.yorumla(f, m))
    hatali = " ".join(guc.yorumla(f, m, hedef_payi_hata=g["hedef_payi_hata"]))
    kontrol("eski kosu metni 'eski koşu'", "eski koşu" in eski, eski[-300:])
    kontrol("hata metni 'okunamadı: hdf5 bozuk 11', eski koşu demez",
            "okunamadı: hdf5 bozuk 11" in hatali and "eski koşu" not in hatali, hatali[-300:])


def test_tepe_faktorleri_hatasi_cokmez():
    print("\n[SH3] tepe_faktorleri hatasi: sonuc_oku cokmez, guc_hata + exc_info log")
    from cekirdek import guc
    eski = guc.tepe_faktorleri

    def bozuk(_d):
        raise ZeroDivisionError("sifir ortalama 3")
    guc.tepe_faktorleri = bozuk
    try:
        try:
            s, log = _oku(_sahte_sp(ref=_TOPLAM_2X2))
            hata = None
        except Exception as e:      # test: cokme KALDI olarak raporlanir
            s, log, hata = {}, [], e
    finally:
        guc.tepe_faktorleri = eski
    kontrol("sonuc_oku cokmedi", hata is None, "-> %r" % hata)
    kontrol("guc_hata metni", s.get("guc_hata") == "sifir ortalama 3", "-> %r" % s.get("guc_hata"))
    kontrol("ERROR + exc_info", any(sv >= logging.ERROR and e for sv, _m, e in log), "-> %r" % log)


def test_entropi_hata_alani():
    print("\n[SH4] Entropi okuma hatasi: entropi_hata alani, sekme 'okunamadı' der")
    s, _log = _oku(_sahte_sp(ref=_TOPLAM_2X2, entropi_hata=True))
    kontrol("entropi [] ve entropi_hata dolu",
            s["entropi"] == [] and "entropy" in (s.get("entropi_hata") or ""),
            "-> %r" % s.get("entropi_hata"))
    s_ok, _l = _oku(_sahte_sp(ref=_TOPLAM_2X2))
    kontrol("normal okumada entropi_hata yok", "entropi_hata" not in s_ok)
    _uyg()
    from cekirdek import sema
    from arayuz.sekme_calistir import CalistirSekmesi
    c = CalistirSekmesi()
    c.spec_ayarla(sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json")), None)
    temel = {"mod": "eigenvalue", "keff": (1.1, 0.001), "cevrim": 10, "pasif": 2,
             "parcacik": 100, "entropi": [], "tallyler": {}}
    c._sonuc_goster(dict(temel, entropi_hata="entropy veri kumesi yok"), "sp.h5")
    metin = c.ozet_etiket.text() + c.sonuc_metin.toPlainText()
    kontrol("ozet 'entropisi okunamadı: ...'", "entropisi okunamadı: entropy veri kumesi yok" in metin,
            metin[-300:])
    kontrol("ozet 'kapalı' demez", "entropisi kapalı" not in metin)
    c._sonuc_goster(dict(temel), "sp.h5")
    kontrol("hata yoksa eski 'kapalı' metni", "entropisi kapalı" in c.ozet_etiket.text())
    c.close()


def test_gui_calistir_kapisi():
    print("\n[SH5] GUI Calistir: bayat izne ragmen dogrula.kapi(veri_kontrolu=True); "
          "hata -> mesaj, dizin silinmez, surec yok")
    _uyg()
    from PySide6 import QtWidgets
    from cekirdek import dogrula, sema
    from arayuz.sekme_calistir import CalistirSekmesi
    d = tempfile.mkdtemp()
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    spec["ayarlar"]["parcacik"] = 0
    spec.setdefault("calistirma", {})["dizin"] = d
    with open(os.path.join(d, "statepoint.10.h5"), "w") as f:
        f.write("onceki kosu")
    cagri, mesajlar = [], []
    gercek = dogrula.kapi

    def kayitli_kapi(sp, veri_kontrolu=True):
        cagri.append(veri_kontrolu)
        return gercek(sp, veri_kontrolu=False)      # nukleer veri gerektirmesin
    eski_w, eski_c = QtWidgets.QMessageBox.warning, QtWidgets.QMessageBox.critical
    dogrula.kapi = kayitli_kapi
    QtWidgets.QMessageBox.warning = staticmethod(lambda *a, **k: mesajlar.append(a))
    QtWidgets.QMessageBox.critical = staticmethod(lambda *a, **k: mesajlar.append(a))
    c = CalistirSekmesi()
    try:
        c.kapi_ayarla(lambda: (True, ""))
        c.spec_ayarla(spec, None)
        c.calistir()
        kontrol("kapi veri_kontrolu=True ile cagrildi", cagri == [True], "-> %r" % cagri)
        kontrol("QMessageBox gosterildi, ilk hata metinde",
                len(mesajlar) == 1 and "parçacık" in " ".join(str(x) for x in mesajlar[0]).lower(),
                "-> %r" % mesajlar)
        kontrol("onceki kosu dosyasi yerinde", os.listdir(d) == ["statepoint.10.h5"],
                "-> %r" % os.listdir(d))
        kontrol("surec baslamadi", c._surec is None)
    finally:
        dogrula.kapi = gercek
        QtWidgets.QMessageBox.warning, QtWidgets.QMessageBox.critical = eski_w, eski_c
        c.close()
        shutil.rmtree(d, True)


def test_dogrulama_hatasi_tum_bulgular():
    print("\n[SH6] DogrulamaHatasi tum bulgulari tasir; _terminal tum_kontroller'i bir kez cagirir")
    import json
    from cekirdek import dogrula, kosucu, sema
    spec = sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json"))
    spec["ayarlar"]["parcacik"] = 0
    try:
        dogrula.kapi(spec, veri_kontrolu=False)
        e = None
    except dogrula.DogrulamaHatasi as h:
        e = h
    kontrol("bulgular yalniz hatalar", e is not None and e.bulgular
            and all(b.seviye == "hata" for b in e.bulgular))
    kontrol("tum_bulgular = tum_kontroller", e is not None and
            [str(b) for b in e.tum_bulgular]
            == [str(b) for b in dogrula.tum_kontroller(spec, veri_kontrolu=False)])
    d = tempfile.mkdtemp()
    eski = dogrula.tum_kontroller
    sayac = []

    def sayan(*a, **k):
        sayac.append(1)
        return eski(*a, **k)
    dogrula.tum_kontroller = sayan
    try:
        yol = os.path.join(d, "hatali.json")
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(spec, f)
        with redirect_stdout(io.StringIO()) as cikti:
            kod = kosucu._terminal([yol, "--dizin", os.path.join(d, "kosu")])
        kontrol("cikis kodu 1", kod == 1, "-> %r" % kod)
        kontrol("tum_kontroller bir kez", len(sayac) == 1, "-> %d" % len(sayac))
        kontrol("hata bulgusu basildi", "parçacık" in cikti.getvalue().lower())
    finally:
        dogrula.tum_kontroller = eski
        shutil.rmtree(d, True)


def test_tukenme_terminal_tum_bulgular():
    print("\n[SH6b] tukenme._terminal: DogrulamaHatasi'nda uyarilar da basilir")
    import json
    from cekirdek import dogrula, sema, tukenme
    hata = dogrula.Bulgu("hata", "ayarlar", "HATA-METNI-1")
    uyari = dogrula.Bulgu("uyari", "ayarlar", "UYARI-METNI-2")
    d = tempfile.mkdtemp()
    eski = (tukenme.zincir_secimi, tukenme.hacimler, tukenme.calistir)
    tukenme.zincir_secimi = lambda s: {"yol": "zincir.xml", "gerekce": "test",
                                       "verim_enerjisi": 0.0253, "temel": "termal"}
    tukenme.hacimler = lambda s: {}

    def cal(*a, **k):
        raise dogrula.DogrulamaHatasi([hata], tum_bulgular=[hata, uyari])
    tukenme.calistir = cal
    try:
        yol = os.path.join(d, "t.json")
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(sema.yukle(os.path.join(ORNEK, "pwr_tukenme.json")), f)
        with redirect_stdout(io.StringIO()) as cikti:
            kod = tukenme._terminal([yol, "--dizin", os.path.join(d, "k")])
        metin = cikti.getvalue()
        kontrol("cikis kodu 2", kod == 2, "-> %r" % kod)
        kontrol("hata ve uyari basildi", "HATA-METNI-1" in metin and "UYARI-METNI-2" in metin,
                metin[-300:])
    finally:
        tukenme.zincir_secimi, tukenme.hacimler, tukenme.calistir = eski
        shutil.rmtree(d, True)


def test_guc_harita_korunum_notu_tekrarsiz():
    print("\n[SH7] Guc haritasi: korunum notu onek tekrari yok")
    _uyg()
    from cekirdek import guc
    from arayuz.guc_harita import GucHaritaWidget
    from testler.test_guc_kor import _kare_2x2_sentetik
    dg = guc.dagilim_oku(_kare_2x2_sentetik())
    f = guc.tepe_faktorleri(dg)
    h = GucHaritaWidget()
    notu = "Referans tally yok — korunum denetlenemedi (eski statepoint ya da model regresyonu)."
    h.sonuc_ayarla({"guc": {"dagilim": dg, "faktorler": f, "korunum_notu": notu}})
    metin = h.ozet.text()
    kontrol("not bir kez, 'denetlenemedi' bir kez",
            "Referans tally yok" in metin and metin.count("denetlenemedi") == 1, metin[-400:])
    h.sonuc_ayarla({"guc": {"dagilim": dg, "faktorler": f, "korunum_hata": "bozuk 42"}})
    metin = h.ozet.text()
    kontrol("korunum_hata onekle", "denetlenemedi: bozuk 42" in metin, metin[-300:])
    h.close()


HIZLI = [test_ref_yok_notu, test_hedef_payi_hata_ayrimi, test_tepe_faktorleri_hatasi_cokmez,
         test_entropi_hata_alani, test_gui_calistir_kapisi, test_dogrulama_hatasi_tum_bulgular,
         test_tukenme_terminal_tum_bulgular, test_guc_harita_korunum_notu_tekrarsiz]
YAVAS = []
