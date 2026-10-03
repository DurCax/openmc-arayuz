# -*- coding: utf-8 -*-
"""
 test_h1b_ithal.py  --  v3 H1b: openmc tembel ice aktarma (acilis ~1.45 s)

 cekirdek'in acilista yuklenen modulleri openmc'yi modul duzeyinde ice
 aktarmaz (dogrula -> kurucu, kod_uret -> yapici, tarama -> kosucu -> kurucu,
 kaynak, tambur). Bos model dogrulamasi da openmc'yi yuklemez: sema
 varsayilani kaynak dagilimlari kurulmadan gecilir (kurulabilirligi burada
 openmc ile dogrulanir) ve bos malzeme listesi kurulmaz.
 Kalan (sahipligim disi): arayuz/onizleme.py (H2), arayuz/sekme_kor.py
 _ozet_guncelle (kur_onbellekli), arayuz kaynak_formu._tayf_gorunurluk.
"""

import os
import subprocess
import sys

from testler.ortak_test import kontrol, KOK

_MODULLER = ("cekirdek.dogrula", "cekirdek.kod_uret", "cekirdek.tarama", "cekirdek.kosucu",
             "cekirdek.kaynak", "cekirdek.tambur", "cekirdek.geometri", "cekirdek.uygunluk",
             "cekirdek.kritik_arama")


def _alt_surec(kod):
    ortam = dict(os.environ, PYTHONPATH=KOK)
    r = subprocess.run([sys.executable, "-c", kod], cwd=KOK, env=ortam, capture_output=True,
                       text=True, timeout=300)
    return r.returncode, (r.stdout.strip().splitlines() or [""])[-1], r.stderr


def test_cekirdek_modulleri_openmc_yuklemez():
    print("\n[H1b-I1] acilis zincirindeki cekirdek modulleri openmc'yi yuklemez")
    kod = "import sys\n" + "".join("import %s\n" % m for m in _MODULLER) + \
        "print('openmc' in sys.modules)"
    kodu, cikti, hata = _alt_surec(kod)
    kontrol("alt surec basarili", kodu == 0, hata[-300:])
    kontrol("openmc yuklenmedi", cikti == "False", "-> %r" % cikti)


def test_bos_model_dogrulamasi_openmc_yuklemez():
    print("\n[H1b-I2] bos model (yeni_spec) tam dogrulamasi openmc'yi yuklemez")
    kod = ("import sys\nfrom cekirdek import sema, dogrula\n"
           "b = dogrula.tum_kontroller(sema.yeni_spec('x'))\n"
           "print('openmc' in sys.modules)")
    kodu, cikti, hata = _alt_surec(kod)
    kontrol("alt surec basarili", kodu == 0, hata[-300:])
    kontrol("openmc yuklenmedi", cikti == "False", "-> %r" % cikti)


def test_varsayilan_kaynak_dagilimlari_kurulur():
    print("\n[H1b-I3] atlanan (varsayilan/bos) kaynak dagilimlari openmc ile kurulabilir")
    from cekirdek import kaynak, sema
    vars_ = sema.VARSAYILAN_AYARLAR["kaynak"]
    for ad, fn in (("enerji", kaynak.enerji_dagilimi), ("aci", kaynak.aci_dagilimi)):
        for arg in (vars_.get(ad), {}, None):
            try:
                fn(arg)
                tamam, ayrinti = True, ""
            except Exception as e:      # noqa: BLE001 -- test: her hata kaldi
                tamam, ayrinti = False, repr(e)
            kontrol("%s %r kurulur" % (ad, arg), tamam, ayrinti)


def test_varsayilan_disi_hatali_dagilim_yine_yakalanir():
    print("\n[H1b-I4] varsayilan disi hatali tayf/aci: 'kurulamadi' HATA'si aynen")
    import copy
    from cekirdek import sema
    from cekirdek.dogrula.kaynak import kaynak_kontrol
    spec = sema.yeni_spec("x")
    s1 = copy.deepcopy(spec)
    s1["ayarlar"]["kaynak"]["enerji"] = {"tur": "histogram", "kenarlar": [1.0], "degerler": []}
    s2 = copy.deepcopy(spec)
    s2["ayarlar"]["kaynak"]["aci"] = {"tur": "tek_yon", "yon": [0.0, 0.0, 0.0]}
    for ad, s in (("enerji", s1), ("aci", s2)):
        b = [x for x in kaynak_kontrol(s, veri_kontrolu=False) if "kurulamadı" in x.mesaj]
        kontrol("%s: kurulamadi HATA" % ad, len(b) == 1 and b[0].seviye == "hata",
                "-> %s" % [x.mesaj for x in b])
    temiz = [x for x in kaynak_kontrol(spec, veri_kontrolu=False) if "kurulamadı" in x.mesaj]
    kontrol("varsayilan kaynak: kurulamadi yok", not temiz)


def test_dogrula_kurucu_ad_alani_korunur():
    print("\n[H1b-I5] dogrula.kurucu eski ad alani tembel olarak erisilebilir")
    from cekirdek import dogrula, kurucu
    kontrol("dogrula.kurucu is cekirdek.kurucu", dogrula.kurucu is kurucu)
    kontrol("ad alaninda ve dir() icinde", "kurucu" in vars(dogrula) and "kurucu" in dir(dogrula))
    try:
        dogrula.boyle_bir_ad_yok
        kontrol("bilinmeyen ad AttributeError", False)
    except AttributeError:
        kontrol("bilinmeyen ad AttributeError", True)


def test_malzeme_anahtari_yoksa_hata_aynen():
    print("\n[H1b-I6] nuklid_kontrol: 'malzemeler' anahtari yoksa (bos liste degil) eski HATA")
    from cekirdek.dogrula import veri
    notron, _t = veri._kutuphane_icerigi()
    if notron is None:
        kontrol("kutuphane yok: denetim atlandi (eski davranis)", True)
        return
    b = veri.nuklid_kontrol({"ad": "x"})
    kontrol("'malzemeler kurulamadı' HATA", any(x.seviye == "hata" and "kurulamadı" in x.mesaj
                                               for x in b), "-> %s" % [x.mesaj for x in b])
    kontrol("bos liste: bulgu yok", veri.nuklid_kontrol({"malzemeler": []}) == [])


_ANA_ISLEM_IZI = """
import builtins, os, sys, threading
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
_asil, ana = builtins.__import__, []
def _iz(ad, *a, **k):
    if ad == 'openmc' and 'openmc' not in sys.modules and \
            threading.current_thread() is threading.main_thread():
        ana.append(1)
    return _asil(ad, *a, **k)
builtins.__import__ = _iz
from PySide6 import QtWidgets
app = QtWidgets.QApplication([])
from arayuz import tema
from arayuz.ana_pencere import AnaPencere
tema.uygula(app)
p = AnaPencere()
p.show()
[app.processEvents() for _i in range(5)]
print(bool(ana))
"""


def test_ana_pencere_acilisi_openmc_yuklemez():
    print("\n[H1b-I7] AnaPencere kurulumu + gosterim (bos model) openmc'yi ANA is "
          "parcaciginda yuklemez (K2 veri sayfasi arka plan isinde yukleyebilir)")
    kodu, cikti, hata = _alt_surec(_ANA_ISLEM_IZI)
    kontrol("alt surec basarili", kodu == 0, hata[-300:])
    kontrol("ana is parcaciginda openmc ice aktarilmadi", cikti == "False", "-> %r" % cikti)


def test_kor_ozeti_kurucu_olcusuyle_ayni():
    print("\n[H1b-I8] Kor ozeti olcusu (openmc'siz) kurucu sinir_kutu ile tum orneklerde ayni")
    from cekirdek import geometri, kurucu, sema
    specler = [("yeni", sema.yeni_spec("x"))] + [
        (ad, sema.yukle(os.path.join(KOK, "ornekler", ad)))
        for ad in sorted(os.listdir(os.path.join(KOK, "ornekler"))) if ad.endswith(".json")]

    def sonuc(islev):
        try:
            return tuple(islev())
        except Exception as e:      # noqa: BLE001 -- hata metni de karsilastirilir
            return ("hata", str(e))
    fark = [ad for ad, s in specler
            if sonuc(lambda: kurucu.kur(s)[1]["sinir_kutu"])
            != sonuc(lambda: geometri.sinir_kutusu(geometri.model(s)))]
    kontrol("%d spec: fark yok" % len(specler), not fark, "-> %s" % fark)


HIZLI = [test_ana_pencere_acilisi_openmc_yuklemez, test_kor_ozeti_kurucu_olcusuyle_ayni,
         test_cekirdek_modulleri_openmc_yuklemez, test_bos_model_dogrulamasi_openmc_yuklemez,
         test_varsayilan_kaynak_dagilimlari_kurulur,
         test_varsayilan_disi_hatali_dagilim_yine_yakalanir, test_dogrula_kurucu_ad_alani_korunur,
         test_malzeme_anahtari_yoksa_hata_aynen]
YAVAS = []
