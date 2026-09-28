# -*- coding: utf-8 -*-
"""
 arayuz/pencere/proje.py  --  ac / kaydet / son kullanilanlar / ice ve disa aktarma

 arayuz/ana_pencere.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import ana_pencere; ana_pencere.X` aynen calisir.
"""

import os

from PySide6 import QtGui, QtWidgets
from cekirdek import sema, ice_aktar, kod_uret, onbellek
from arayuz.pencere.model_islemleri import ORNEKLER


_ICE_AKTAR_NOTU = ("Yalnızca malzemeler aktarılır: OpenMC geometrisi ham CSG'dir "
                   "ve bu arayüzün malzeme → parça → demet → kor katmanlarına "
                   "güvenle çevrilemez; geometriyi arayüzde yeniden kurun.")


class ProjeMixin(object):
    """Proje yasam dongusu: yeni, ac, kaydet, son kullanilanlar, ice/disa aktarma."""

    # ==================================================================
    # son kullanilanlar
    # ==================================================================
    def _son_listesi(self):
        try:
            ham = self.ayarlar.value("son_dosyalar", []) or []
        except Exception:
            ham = []
        if isinstance(ham, str):
            ham = [ham]
        # Ornekler baslangic ekraninda ayrica listelenir ve kopya olarak
        # acilir; eski surumlerden kalan ornek girdileri burada gosterilmez.
        return [y for y in ham if isinstance(y, str) and os.path.exists(y)
                and not self._ornek_mi(y)]

    def _sona_ekle(self, yol):
        liste = [os.path.abspath(yol)] + [y for y in self._son_listesi()
                                          if os.path.abspath(y) != os.path.abspath(yol)]
        self.ayarlar.setValue("son_dosyalar", liste[:10])
        self._son_menusu_yenile()

    def _son_menusu_yenile(self):
        self.m_son.clear()
        liste = self._son_listesi()
        if not liste:
            e = self.m_son.addAction("(boş)")
            e.setEnabled(False)
            return
        for yol in liste:
            e = QtGui.QAction(os.path.basename(yol), self)
            e.setToolTip(yol)
            e.triggered.connect(lambda _c=False, y=yol: self.proje_ac(y))
            self.m_son.addAction(e)

    # ==================================================================
    # dosya islemleri
    # ==================================================================
    def _kaydetme_sor(self):
        if not self._kirli:
            return True
        soru = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Question, "Kaydedilmemiş değişiklikler",
            "Değişiklikler kaydedilmedi. Kaydedilsin mi?",
            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard
            | QtWidgets.QMessageBox.Cancel, self)
        # Qt'nin Turkce cevirisinde "Discard" -> "At"; burada acik adlar.
        for dugme, ad in ((QtWidgets.QMessageBox.Save, "Kaydet"),
                          (QtWidgets.QMessageBox.Discard, "Kaydetme"),
                          (QtWidgets.QMessageBox.Cancel, "Vazgeç")):
            soru.button(dugme).setText(ad)
        soru.exec()
        c = soru.standardButton(soru.clickedButton())
        if c == QtWidgets.QMessageBox.Save:
            return self.proje_kaydet()
        return c == QtWidgets.QMessageBox.Discard

    def proje_yeni(self):
        """Dosya > Yeni: baslangic ekrani. Kaydetme sorusu bir kart
        SECILINCE sorulur -- vazgecen kullanici modeline geri doner."""
        self.baslangici_goster()

    def _ac_diyalog(self):
        yol, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Model aç", ORNEKLER, "JSON model (*.json);;Tüm dosyalar (*)")
        if yol:
            self.proje_ac(yol)

    @staticmethod
    def _ornek_mi(yol):
        """Dosya ornekler/ dizininde mi? (ornekler ayni zamanda test referansidir)"""
        return (os.path.dirname(os.path.realpath(yol))
                == os.path.realpath(ORNEKLER))

    def proje_ac(self, yol):
        # Ornek dosyalar (baslangic ekrani, Ac..., komut satiri, son
        # kullanilanlar -- hepsi buradan gecer) KAYDEDILMEMIS BIR KOPYA olarak
        # acilir. Eskiden gercek dosya aciliyordu ve Ctrl+S ornekler/*.json'u
        # (testlerin referanslarini) ustune yaziyordu.
        if self._ornek_mi(yol):
            return self.ornek_ac(yol)
        if not self._kaydetme_sor():
            return False
        try:
            yeni = sema.yukle(yol)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Açılamadı", str(e))
            return False
        self._proje_kur(yeni, proje_yolu=os.path.abspath(yol), ornek_kaynagi=None)
        self._sona_ekle(yol)
        self.statusBar().showMessage("Açıldı: %s" % yol, 6000)
        return True

    def ornek_ac(self, yol):
        """Bir ornegi kaydedilmemis KOPYA olarak acar (proje_yolu = None)."""
        if not self._kaydetme_sor():
            return False
        try:
            yeni = sema.yukle(yol)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Açılamadı", str(e))
            return False
        self._proje_kur(yeni, proje_yolu=None, ornek_kaynagi=os.path.abspath(yol))
        self.statusBar().showMessage(
            "Örnek kopya olarak açıldı: %s — kaydetmek için 'Farklı kaydet' "
            "kullanın (örnek dosyası değişmez)" % os.path.basename(yol), 8000)
        return True

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
        self._sona_ekle(self.proje_yolu)
        self.statusBar().showMessage("Kaydedildi: %s" % self.proje_yolu, 5000)
        return True

    def proje_farkli_kaydet(self):
        if self.proje_yolu:
            varsayilan = self.proje_yolu
        elif self.ornek_kaynagi:
            # Ornegin kopyasi: varsayilan yer ornekler/ OLMAMALI.
            varsayilan = os.path.join(os.path.expanduser("~"),
                                      os.path.basename(self.ornek_kaynagi))
        else:
            varsayilan = os.path.join(os.path.expanduser("~"), "model.json")
        yol, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Modeli kaydet", varsayilan, "JSON model (*.json)")
        if not yol:
            return False
        if not yol.endswith(".json"):
            yol += ".json"
        self.proje_yolu = yol
        self.ornek_kaynagi = None
        self.s_calistir.spec_ayarla(self.spec, self.proje_yolu)
        self.s_tukenme.proje_ayarla(self.proje_yolu)
        return self.proje_kaydet()

    def malzeme_ice_aktar(self):
        yol, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Malzeme içeren OpenMC XML dosyası",
            os.path.dirname(self.proje_yolu) if self.proje_yolu else os.path.expanduser("~"),
            "OpenMC XML (materials.xml model.xml *.xml);;Tüm dosyalar (*)")
        if not yol:
            return
        try:
            yeni_malzemeler, notlar = ice_aktar.malzemeleri_oku(yol)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Okunamadı", str(e))
            return
        if not yeni_malzemeler:
            QtWidgets.QMessageBox.information(self, "Boş", "Dosyada malzeme bulunamadı.")
            return
        # Geri alinabilir tek adim: bekleyen duzenleme once kendi adimi olsun.
        self._gecmis_sayac.stop()
        self._gecmise_it()
        mevcut = {m["ad"] for m in self.spec["malzemeler"]}
        for m in yeni_malzemeler:
            ad, i = m["ad"], 2
            while ad in mevcut:
                ad = "%s_%d" % (m["ad"], i)
                i += 1
            m["ad"] = ad
            mevcut.add(ad)
            self.spec["malzemeler"].append(m)
        self._kirli = True
        self._spec_uygula()
        self._gecmise_it()
        mesaj = "%d malzeme eklendi.\n\n" % len(yeni_malzemeler)
        if notlar:
            mesaj += "Notlar:\n" + "\n".join("  - " + n for n in notlar) + "\n\n"
        mesaj += _ICE_AKTAR_NOTU
        self.statusBar().showMessage("%d malzeme içe aktarıldı — geometri aktarılmaz, "
                                     "arayüzde kurulur." % len(yeni_malzemeler), 8000)
        QtWidgets.QMessageBox.information(self, "İçe aktarıldı", mesaj)

    def betik_disa_aktar(self):
        varsayilan = os.path.splitext(self.proje_yolu or "model.json")[0] + ".py"
        yol, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Python betiği olarak dışa aktar", varsayilan, "Python (*.py)")
        if not yol:
            return
        try:
            kod = kod_uret.uret(self.spec, os.path.basename(yol))
            with open(yol, "w", encoding="utf-8") as f:
                f.write(kod)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Üretilemedi", str(e))
            return
        QtWidgets.QMessageBox.information(
            self, "Dışa aktarıldı",
            "Betik yazıldı:\n%s\n\n%d satır. Tek başına çalışır; arayüze geri "
            "yüklenemez." % (yol, len(kod.splitlines())))

    def xml_disa_aktar(self):
        dizin = QtWidgets.QFileDialog.getExistingDirectory(
            self, "XML'lerin yazılacağı dizin",
            os.path.dirname(self.proje_yolu) if self.proje_yolu else os.path.expanduser("~"))
        if not dizin:
            return
        try:
            model, _ = onbellek.kur_taze(self.spec)
            model.export_to_model_xml(os.path.join(dizin, "model.xml"))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Üretilemedi", str(e))
            return
        self.statusBar().showMessage("XML yazıldı: %s/model.xml" % dizin, 6000)

    def png_kaydet(self):
        yol, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Önizlemeyi kaydet", "geometri.png", "PNG (*.png)")
        if yol:
            self.onizleme.kaydet(yol)
            self.statusBar().showMessage("Kaydedildi: %s" % yol, 5000)
