# -*- coding: utf-8 -*-
"""
test_calistir_akis.py -- Dalga 2 / Ajan 8: Calistir sayfasinin kosu akisi
(sahte openmc betigiyle, Monte Carlo'suz; hizli suitte kosar).

  * Kapi izni yok / dogrulama hatasi / model kurulamadi / openmc yok:
    kosu baslamaz, kullaniciya gosterilir, onceki sonuc silinmez.
  * Basarili kosu: canli cevrimler grafige, gunlukteki sure/hiz panoya,
    sonuc gosterilir; kosu_durumu_degisti True -> False.
  * Cikis kodu != 0, statepoint yok, sonuc okunamadi, durdurma, baslatilamayan
    surec (FailedToStart): basarisiz durum + ayrintili cikti acilir.
  * Kosu ayarlari spec["calistirma"]'ya yazilir; gunluk kopyala, klasoru ac.

Modal diyaloglar exec() EDILMEZ (QMessageBox yamalanir).
"""

import copy
import os
import shutil
import stat
import tempfile
import time

from testler.ortak_test import kontrol, ORNEK

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SAHTE_K = {"mod": "eigenvalue", "keff": (1.18342, 0.00061), "cevrim": 6, "pasif": 2,
           "parcacik": 1000, "tallyler": {}, "entropi": [], "malzeme_adlari": {}}

CIKTI = ('i=1\nwhile [ $i -le 6 ]; do\n'
         '  echo "        $i/1    1.1$i    7.0$i    1.1000$i +/- 0.00100"\n'
         '  i=$((i+1))\ndone\n'
         'echo " Total time elapsed                = 2.5000e+00 seconds"\n'
         'echo " Calculation Rate (active)         = 4000.0 particles/second"\n')


def _qt():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _bekle(kosul, saniye=20.0):
    from PySide6 import QtWidgets
    son = time.time() + saniye
    while time.time() < son:
        QtWidgets.QApplication.processEvents()
        if kosul():
            return True
        time.sleep(0.02)
    return False


def _betik(dizin, govde):
    yol = os.path.join(dizin, "sahte_openmc")
    with open(yol, "w") as f:
        f.write("#!/bin/sh\n" + govde)
    os.chmod(yol, os.stat(yol).st_mode | stat.S_IEXEC)
    return yol


class _Ortam(object):
    """kosucu/dogrula/QMessageBox yamalari; cikista geri alinir."""

    def __init__(self):
        from PySide6 import QtWidgets
        from cekirdek import dogrula, kosucu
        self.kosucu, self.dogrula, self.qm = kosucu, dogrula, QtWidgets.QMessageBox
        self.eski = (kosucu.openmc_yolu, kosucu.son_statepoint, kosucu.sonuc_oku,
                     kosucu.xml_yaz, dogrula.kapi, self.qm.warning, self.qm.critical)
        self.mesajlar = []
        self.gecici = tempfile.mkdtemp(prefix="calistir_akis_")

    def __enter__(self):
        k = self.kosucu
        k.xml_yaz = lambda spec, dizin: None
        k.son_statepoint = lambda d: os.path.join(d, "statepoint.6.h5")
        k.sonuc_oku = lambda sp: copy.deepcopy(SAHTE_K)
        self.dogrula.kapi = lambda spec, veri_kontrolu=True: []
        self.qm.warning = lambda *a: self.mesajlar.append(("uyari",) + a[1:])
        self.qm.critical = lambda *a: self.mesajlar.append(("kritik",) + a[1:])
        return self

    def __exit__(self, *_a):
        (self.kosucu.openmc_yolu, self.kosucu.son_statepoint, self.kosucu.sonuc_oku,
         self.kosucu.xml_yaz, self.dogrula.kapi, self.qm.warning,
         self.qm.critical) = self.eski
        shutil.rmtree(self.gecici, ignore_errors=True)

    def sayfa(self, govde=CIKTI):
        from cekirdek import sema
        from arayuz.sekme_calistir import CalistirSekmesi
        exe = _betik(self.gecici, govde)
        self.kosucu.openmc_yolu = lambda: exe
        c = CalistirSekmesi()
        c.kapi_ayarla(lambda: (True, "hazır"))
        c.spec_ayarla(sema.yukle(os.path.join(ORNEK, "pwr_pinhucre.json")),
                      os.path.join(self.gecici, "proje.json"))
        return c


def test_kosu_basarili_akis():
    _qt()
    with _Ortam() as o:
        c = o.sayfa()
        durumlar = []
        c.kosu_durumu_degisti.connect(durumlar.append)
        c.calistir()
        kontrol("kosu basladi, Durdur etkin", c._surec is not None and c.d_durdur.isEnabled())
        c.calistir()                       # suren kosuda ikinci basis yok sayilir
        kontrol("kosu surerken ayarlar kilitli", not c.is_parcacigi.isEnabled())
        _bekle(lambda: c._surec is None)
        kontrol("sonuc gosterildi", c.sonuc_var() and "1.18342" in c.keff_etiket.text())
        kontrol("canli cevrimler okundu", len(c._cevrimler) == 6
                and c.yakinsama.isVisibleTo(c), "-> %d" % len(c._cevrimler))
        kontrol("sure ve hiz gunlukten", c.pano.sure.deger.text() == "0:02"
                and c.pano.hiz.deger.text() == "4 000",
                "-> %r %r" % (c.pano.sure.deger.text(), c.pano.hiz.deger.text()))
        kontrol("dogrulama satiri: hata yok", c.pano.dogrulama_rozeti.text() == "Hata yok")
        kontrol("kosu_durumu_degisti True -> False", durumlar == [True, False],
                "-> %r" % durumlar)
        kontrol("son kosu dizini", c.son_kosu_dizini() and c.d_klasor.isEnabled())
        from PySide6 import QtGui, QtWidgets
        acilan = []
        eski = QtGui.QDesktopServices.openUrl
        QtGui.QDesktopServices.openUrl = lambda url: acilan.append(url) or True
        try:
            kontrol("klasoru ac", c.klasoru_ac() and acilan)
        finally:
            QtGui.QDesktopServices.openUrl = eski
        c.gunlugu_kopyala()
        kontrol("gunluk panoya", "1/1" in QtWidgets.QApplication.clipboard().text())
        c.sifirla()
        kontrol("sifirla: sonuc yok, klasor kapali", not c.sonuc_var()
                and not c.klasoru_ac())
        c.deleteLater()


def test_kosu_baslamayan_yollar():
    _qt()
    from cekirdek import dogrula
    with _Ortam() as o:
        c = o.sayfa()
        c.kapi_ayarla(lambda: (False, "önizleme yok"))
        c.calistir()
        kontrol("kapi izni yok: uyari, kosu yok", c._surec is None
                and o.mesajlar[-1][2] == "önizleme yok")
        c.kapi_ayarla(lambda: (True, "hazır"))

        class _B(object):
            seviye, mesaj = "hata", "yakıt yok"

        def hatali(spec, veri_kontrolu=True):
            raise dogrula.DogrulamaHatasi([_B()] * 7)
        dogrula.kapi = hatali
        c.calistir()
        kontrol("dogrulama hatasi: 5 hata + '2 hata daha', pano 7 hata",
                c._surec is None and "2 hata daha" in o.mesajlar[-1][2]
                and c.pano.dogrulama_rozeti.text() == "7 hata", "-> %r" % (o.mesajlar[-1],))
        dogrula.kapi = lambda spec, veri_kontrolu=True: []

        def kurulamaz(spec, dizin):
            raise ValueError("geometri bozuk")
        o.kosucu.xml_yaz = kurulamaz
        c.calistir()
        kontrol("model kurulamadi: kritik ileti", o.mesajlar[-1][0] == "kritik"
                and "geometri bozuk" in o.mesajlar[-1][2])
        o.kosucu.xml_yaz = lambda spec, dizin: None
        o.kosucu.openmc_yolu = lambda: None
        c.calistir()
        kontrol("openmc yok: kritik ileti", c._surec is None
                and o.mesajlar[-1][1] == "openmc bulunamadı")
        c.deleteLater()


def test_kosu_basarisiz_yollar():
    _qt()
    with _Ortam() as o:
        c = o.sayfa('echo "bozuk"\nexit 3\n')
        c.calistir()
        _bekle(lambda: c._surec is None)
        kontrol("cikis kodu 3: basarisiz, ayrinti acik", c._basarisiz
                and "çıkış kodu 3" in c.durum_etiket.text() and c.ayrinti.dugme.isChecked())
        c2 = o.sayfa()
        o.kosucu.son_statepoint = lambda d: None
        c2.calistir()
        _bekle(lambda: c2._surec is None)
        kontrol("statepoint yok", not c2.sonuc_var() and "statepoint" in
                c2.durum_etiket.text())
        o.kosucu.son_statepoint = lambda d: os.path.join(d, "sp.h5")

        def bozuk(_sp):
            raise ValueError("okunamaz")
        o.kosucu.sonuc_oku = bozuk
        c2.calistir()
        _bekle(lambda: c2._surec is None)
        kontrol("sonuc okunamadi", "okunamaz" in c2.durum_etiket.text())
        c3 = o.sayfa("sleep 5\n")
        c3.calistir()
        c3.durdur()
        _bekle(lambda: c3._surec is None)
        kontrol("durduruldu", c3._basarisiz and c3.keff_etiket.text() == "durduruldu"
                and "durduruldu" in c3.log.toPlainText())
        o.kosucu.openmc_yolu = lambda: os.path.join(o.gecici, "yok", "openmc")
        c3.calistir()
        _bekle(lambda: c3._surec is None)
        kontrol("baslatilamayan surec: dugmeler acilir", c3._surec is None
                and c3.d_calistir.isEnabled() and "Süreç hatası" in c3.log.toPlainText())
        for w in (c, c2, c3):
            w.deleteLater()


def test_kosu_ayarlari_speci():
    _qt()
    with _Ortam() as o:
        c = o.sayfa()
        degisen = []
        c.degisti.connect(degisen.append)
        c.is_parcacigi.setValue(3)
        c.kosu_dizini.setText("  ")
        c._calistirma_kaydet()
        kontrol("is parcacigi ve dizin spec'e", c.spec["calistirma"]["is_parcacigi"] == 3
                and c.spec["calistirma"]["dizin"] == "kosu" and c.kosu_dizini.text() == "kosu")
        kontrol("degisti(calistirma)", degisen and set(degisen) == {"calistirma"})
        n = len(degisen)
        c._calistirma_kaydet()
        kontrol("degisiklik yoksa sinyal yok", len(degisen) == n)
        c.kosu_dizini.setText(os.path.join(o.gecici, "mutlak"))
        c._calistirma_kaydet()
        kontrol("mutlak dizin aynen", c._kosu_dizini() == os.path.join(o.gecici, "mutlak"))
        kontrol("dizin yolu etiketi tam yol", c.dizin_yolu.text().endswith("mutlak"))
        c.deleteLater()


HIZLI = [test_kosu_basarili_akis, test_kosu_baslamayan_yollar, test_kosu_basarisiz_yollar,
         test_kosu_ayarlari_speci]
YAVAS = []


if __name__ == "__main__":
    from testler.ortak_test import _gecti, _kaldi
    for fn in HIZLI:
        fn()
    print("\n SONUC: %d gecti, %d kaldi" % (len(_gecti), len(_kaldi)))
    for t in _kaldi:
        print("   - %s" % t)
