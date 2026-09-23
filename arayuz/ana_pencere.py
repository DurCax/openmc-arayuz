# -*- coding: utf-8 -*-
"""
================================================================================
 ana_pencere.py  --  Ana uygulama penceresi
================================================================================
 Sol tarafta editor sekmeleri, sag tarafta canli geometri onizlemesi, altta
 dogrulama paneli. Butun sekmeler ayni spec sozlugu uzerinde calisir; herhangi
 bir degisiklik dogrulamayi ve onizlemeyi tetikler.
================================================================================
"""

import copy
import os
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import sema, dogrula, ice_aktar, kod_uret, kurucu
from arayuz.onizleme import OnizlemeWidget
from arayuz.sekme_ayar import AyarSekmesi
from arayuz.sekme_calistir import CalistirSekmesi
from arayuz.sekme_cubuk import CubukSekmesi
from arayuz.sekme_demet import DemetSekmesi
from arayuz.sekme_kor import KorSekmesi
from arayuz.sekme_malzeme import MalzemeSekmesi

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORNEKLER = os.path.join(KOK, "ornekler")

_SEVIYE_RENK = {"hata": "#c0392b", "uyari": "#c87f0a", "bilgi": "#7f8c8d"}


class AnaPencere(QtWidgets.QMainWindow):

    def __init__(self, acilis_dosyasi=None):
        super().__init__()
        self.setWindowTitle("OpenMC Reaktor Kuru Arayuzu")
        self.resize(1500, 950)

        self.spec = sema.yeni_spec("yeni model")
        self.proje_yolu = None
        self._kirli = False
        self._bulgular = []

        # --- editor sekmeleri ---
        self.sekmeler = QtWidgets.QTabWidget()
        self.s_malzeme = MalzemeSekmesi()
        self.s_cubuk = CubukSekmesi()
        self.s_demet = DemetSekmesi()
        self.s_kor = KorSekmesi()
        self.s_ayar = AyarSekmesi()
        self.s_calistir = CalistirSekmesi()

        self.editorler = [self.s_malzeme, self.s_cubuk, self.s_demet,
                          self.s_kor, self.s_ayar]
        for ad, w in (("1. Malzemeler", self.s_malzeme),
                      ("2. Cubuk / Plaka", self.s_cubuk),
                      ("3. Kafesler", self.s_demet),
                      ("4. Kor", self.s_kor),
                      ("5. Ayarlar & Tally", self.s_ayar),
                      ("6. Calistir", self.s_calistir)):
            self.sekmeler.addTab(w, ad)
        for e in self.editorler:
            e.degisti.connect(self._degisti)

        # --- onizleme ---
        self.onizleme = OnizlemeWidget()
        self.onizleme.durum.connect(self._onizleme_durum)

        # --- dogrulama paneli ---
        self.dogrulama = QtWidgets.QListWidget()
        self.dogrulama.setAlternatingRowColors(True)
        self.dogrulama_ozet = QtWidgets.QLabel("-")
        dg = QtWidgets.QWidget()
        dgd = QtWidgets.QVBoxLayout(dg)
        dgd.setContentsMargins(4, 4, 4, 4)
        ust = QtWidgets.QHBoxLayout()
        ust.addWidget(QtWidgets.QLabel("Dogrulama:"))
        ust.addWidget(self.dogrulama_ozet)
        ust.addStretch(1)
        d_yenile = QtWidgets.QPushButton("Veri kutuphanesini de kontrol et")
        d_yenile.clicked.connect(lambda: self._dogrula(veri=True))
        ust.addWidget(d_yenile)
        dgd.addLayout(ust)
        dgd.addWidget(self.dogrulama)

        # --- yerlesim ---
        sag = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        sag.addWidget(self.onizleme)
        sag.addWidget(dg)
        sag.setStretchFactor(0, 3)
        sag.setStretchFactor(1, 1)

        bolucu = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        bolucu.addWidget(self.sekmeler)
        bolucu.addWidget(sag)
        bolucu.setStretchFactor(0, 3)
        bolucu.setStretchFactor(1, 2)
        bolucu.setSizes([880, 620])
        self.setCentralWidget(bolucu)

        self._menu_kur()
        self.statusBar().showMessage("Hazir")

        self.s_calistir.kapi_ayarla(self._kosu_izni)
        self.s_calistir.durum.connect(lambda m, ok: self.statusBar().showMessage(m))

        # dogrulama icin gecikme sayaci
        self._dog_sayac = QtCore.QTimer(self)
        self._dog_sayac.setSingleShot(True)
        self._dog_sayac.setInterval(250)
        self._dog_sayac.timeout.connect(lambda: self._dogrula(veri=False))

        if acilis_dosyasi:
            self.proje_ac(acilis_dosyasi)
        else:
            self._spec_uygula()

    # ==================================================================
    # menu
    # ==================================================================
    def _menu_kur(self):
        m_dosya = self.menuBar().addMenu("&Dosya")
        self._eylem(m_dosya, "Yeni", self.proje_yeni, QtGui.QKeySequence.New)
        self._eylem(m_dosya, "Ac...", self._ac_diyalog, QtGui.QKeySequence.Open)

        m_ornek = m_dosya.addMenu("Ornek ac")
        for ad, dosya in (("PWR pin hucre (regresyon cipasi)", "pwr_pinhucre.json"),
                          ("PWR 17x17 yakit demeti", "pwr_17x17.json"),
                          ("MTR plaka yakit elemani", "mtr_plaka.json")):
            yol = os.path.join(ORNEKLER, dosya)
            eylem = QtGui.QAction(ad, self)
            eylem.triggered.connect(lambda _c=False, y=yol: self.proje_ac(y))
            m_ornek.addAction(eylem)

        m_dosya.addSeparator()
        self._eylem(m_dosya, "Kaydet", self.proje_kaydet, QtGui.QKeySequence.Save)
        self._eylem(m_dosya, "Farkli kaydet...", self.proje_farkli_kaydet,
                    QtGui.QKeySequence.SaveAs)
        m_dosya.addSeparator()
        self._eylem(m_dosya, "Malzemeleri OpenMC XML'inden ice aktar...",
                    self.malzeme_ice_aktar)
        self._eylem(m_dosya, "Neden geometri ice aktarilamiyor?",
                    self._geometri_aciklama)
        m_dosya.addSeparator()
        self._eylem(m_dosya, "Python betigi olarak disa aktar...", self.betik_disa_aktar)
        self._eylem(m_dosya, "OpenMC XML disa aktar...", self.xml_disa_aktar)
        self._eylem(m_dosya, "Onizlemeyi PNG kaydet...", self.png_kaydet)
        m_dosya.addSeparator()
        self._eylem(m_dosya, "Cikis", self.close, QtGui.QKeySequence.Quit)

        m_model = self.menuBar().addMenu("&Model")
        self._eylem(m_model, "Dogrulamayi yenile (veri kutuphanesi dahil)",
                    lambda: self._dogrula(veri=True), "F5")
        self._eylem(m_model, "Onizlemeyi yenile", self.onizleme._ciz, "F6")

        m_yardim = self.menuBar().addMenu("&Yardim")
        self._eylem(m_yardim, "Hakkinda", self._hakkinda)

    def _eylem(self, menu, ad, islev, kisayol=None):
        e = QtGui.QAction(ad, self)
        e.triggered.connect(lambda _c=False: islev())
        if kisayol:
            e.setShortcut(kisayol)
        menu.addAction(e)
        return e

    def _hakkinda(self):
        QtWidgets.QMessageBox.information(
            self, "Hakkinda",
            "OpenMC Reaktor Kuru Arayuzu\n\n"
            "Model tanimi JSON 'spec' olarak tutulur; ondan hem openmc.Model\n"
            "hem de tek basina calisan Python betigi uretilir.\n\n"
            "Arayuz bir cikmaz sokak degildir: Dosya > Python betigi olarak\n"
            "disa aktar ile modeli alip elle duzenlemeye devam edebilirsiniz.")

    # ==================================================================
    # spec yasam dongusu
    # ==================================================================
    def _spec_uygula(self):
        for e in self.editorler:
            e.spec_yukle(self.spec)
        self.onizleme.spec_ayarla(self.spec)
        self.s_calistir.spec_ayarla(self.spec, self.proje_yolu)
        self._dogrula(veri=False)
        self._baslik_guncelle()

    def _degisti(self):
        self._kirli = True
        self.onizleme.iste()
        self._dog_sayac.start()
        self._baslik_guncelle()
        # sekmeler birbirine bagimli (malzeme adi -> cubuk kutulari vb.)
        gonderen = self.sender()
        for e in self.editorler:
            if e is not gonderen:
                e.spec_yukle(self.spec)

    def _baslik_guncelle(self):
        ad = os.path.basename(self.proje_yolu) if self.proje_yolu else "kaydedilmemis"
        self.setWindowTitle("OpenMC Reaktor Kuru Arayuzu  --  %s%s"
                            % (ad, " *" if self._kirli else ""))

    # ==================================================================
    # dogrulama
    # ==================================================================
    def _dogrula(self, veri=False):
        try:
            self._bulgular = dogrula.tum_kontroller(self.spec, veri_kontrolu=veri)
        except Exception as e:
            self._bulgular = [dogrula.Bulgu("hata", "dogrulama",
                                            "dogrulama sirasinda hata: %s" % e)]
        self.dogrulama.clear()
        for b in self._bulgular:
            oge = QtWidgets.QListWidgetItem("%s  %s%s"
                                            % (b.seviye.upper().ljust(5), b.yer.ljust(20),
                                               b.mesaj))
            oge.setForeground(QtGui.QColor(_SEVIYE_RENK[b.seviye]))
            if b.oneri:
                oge.setToolTip(b.oneri)
            self.dogrulama.addItem(oge)
        ozet = dogrula.ozet(self._bulgular)
        self.dogrulama_ozet.setText(ozet)
        self.dogrulama_ozet.setStyleSheet(
            "color: %s; font-weight: bold;"
            % (_SEVIYE_RENK["hata"] if dogrula.hata_var(self._bulgular) else "#27ae60"))
        self.s_calistir.kapi_guncelle()

    def _onizleme_durum(self, mesaj, basarili):
        self.statusBar().showMessage(mesaj)
        self.s_calistir.kapi_guncelle()

    def _kosu_izni(self):
        """CALISTIR kapisi: once geometri cizilmeli, sonra hata olmamali."""
        if dogrula.hata_var(self._bulgular):
            n = sum(1 for b in self._bulgular if b.seviye == "hata")
            return False, ("Dogrulamada %d hata var -- once bunlari giderin "
                           "(sag alttaki panel)." % n)
        if not self.onizleme.cizildi_mi():
            return False, ("Geometri onizlemesi henuz basariyla uretilmedi. "
                           "ONCE CIZ, SONRA CALISTIR: yanlis geometriyle saatlerce "
                           "kosmamak icin onizlemenin calismasi bekleniyor.")
        uyari = sum(1 for b in self._bulgular if b.seviye == "uyari")
        if uyari:
            return True, ("Calistirilabilir. %d uyari var -- sonucu etkileyebilir, "
                          "dogrulama panelini gozden gecirin." % uyari)
        return True, "Model calistirilmaya hazir."

    # ==================================================================
    # dosya islemleri
    # ==================================================================
    def _kaydetme_sor(self):
        if not self._kirli:
            return True
        c = QtWidgets.QMessageBox.question(
            self, "Kaydedilmemis degisiklikler",
            "Degisiklikler kaydedilmedi. Kaydedilsin mi?",
            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard
            | QtWidgets.QMessageBox.Cancel)
        if c == QtWidgets.QMessageBox.Save:
            return self.proje_kaydet()
        return c == QtWidgets.QMessageBox.Discard

    def proje_yeni(self):
        if not self._kaydetme_sor():
            return
        self.spec = sema.yeni_spec("yeni model")
        self.proje_yolu = None
        self._kirli = False
        self._spec_uygula()

    def _ac_diyalog(self):
        yol, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Model spec ac", ORNEKLER, "JSON model (*.json);;Tum dosyalar (*)")
        if yol:
            self.proje_ac(yol)

    def proje_ac(self, yol):
        if not self._kaydetme_sor():
            return
        try:
            self.spec = sema.yukle(yol)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Acilamadi", str(e))
            return
        self.proje_yolu = os.path.abspath(yol)
        self._kirli = False
        self._spec_uygula()
        self.statusBar().showMessage("Acildi: %s" % yol)

    def proje_kaydet(self):
        if self.proje_yolu is None:
            return self.proje_farkli_kaydet()
        try:
            sema.kaydet(self.spec, self.proje_yolu)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Kaydedilemedi", str(e))
            return False
        self._kirli = False
        self._baslik_guncelle()
        self.statusBar().showMessage("Kaydedildi: %s" % self.proje_yolu)
        return True

    def proje_farkli_kaydet(self):
        yol, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Model spec kaydet",
            self.proje_yolu or os.path.join(ORNEKLER, "model.json"),
            "JSON model (*.json)")
        if not yol:
            return False
        if not yol.endswith(".json"):
            yol += ".json"
        self.proje_yolu = yol
        self.s_calistir.spec_ayarla(self.spec, self.proje_yolu)
        return self.proje_kaydet()

    def malzeme_ice_aktar(self):
        """Mevcut bir materials.xml / model.xml icindeki malzemeleri spec'e ekler."""
        yol, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Malzeme iceren OpenMC XML dosyasi",
            os.path.dirname(self.proje_yolu) if self.proje_yolu else os.getcwd(),
            "OpenMC XML (materials.xml model.xml *.xml);;Tum dosyalar (*)")
        if not yol:
            return
        try:
            yeni_malzemeler, notlar = ice_aktar.malzemeleri_oku(yol)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Okunamadi", str(e))
            return
        if not yeni_malzemeler:
            QtWidgets.QMessageBox.information(self, "Bos", "Dosyada malzeme bulunamadi.")
            return

        mevcut = {m["ad"] for m in self.spec["malzemeler"]}
        eklenen = 0
        for m in yeni_malzemeler:
            ad, i = m["ad"], 2
            while ad in mevcut:
                ad = "%s_%d" % (m["ad"], i)
                i += 1
            m["ad"] = ad
            mevcut.add(ad)
            self.spec["malzemeler"].append(m)
            eklenen += 1

        self._kirli = True
        self._spec_uygula()
        mesaj = "%d malzeme eklendi.\n\n" % eklenen
        if notlar:
            mesaj += "Notlar:\n" + "\n".join("  - " + n for n in notlar)
        QtWidgets.QMessageBox.information(self, "Ice aktarildi", mesaj)

    def _geometri_aciklama(self):
        QtWidgets.QMessageBox.information(
            self, "Geometri ice aktarma", ice_aktar.geometri_neden_aktarilamaz())

    def betik_disa_aktar(self):
        varsayilan = os.path.splitext(self.proje_yolu or "model.json")[0] + ".py"
        yol, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Python betigi olarak disa aktar", varsayilan, "Python (*.py)")
        if not yol:
            return
        try:
            kod = kod_uret.uret(self.spec, os.path.basename(yol))
            with open(yol, "w", encoding="utf-8") as f:
                f.write(kod)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Uretilemedi", str(e))
            return
        QtWidgets.QMessageBox.information(
            self, "Disa aktarildi",
            "Betik yazildi:\n%s\n\n%d satir. Tek basina calisir; arayuze geri "
            "yuklenemez." % (yol, len(kod.splitlines())))

    def xml_disa_aktar(self):
        dizin = QtWidgets.QFileDialog.getExistingDirectory(
            self, "XML'lerin yazilacagi dizin",
            os.path.dirname(self.proje_yolu) if self.proje_yolu else os.getcwd())
        if not dizin:
            return
        try:
            model, _ = kurucu.kur(self.spec)
            model.export_to_model_xml(os.path.join(dizin, "model.xml"))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Uretilemedi", str(e))
            return
        self.statusBar().showMessage("XML yazildi: %s/model.xml" % dizin)

    def png_kaydet(self):
        yol, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Onizlemeyi kaydet", "geometri.png", "PNG (*.png)")
        if yol:
            self.onizleme.kaydet(yol)
            self.statusBar().showMessage("Kaydedildi: %s" % yol)

    def closeEvent(self, olay):
        if self._kaydetme_sor():
            olay.accept()
        else:
            olay.ignore()


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    app = QtWidgets.QApplication(sys.argv[:1])
    app.setApplicationName("OpenMC Arayuz")
    pencere = AnaPencere(argv[0] if argv else None)
    pencere.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
