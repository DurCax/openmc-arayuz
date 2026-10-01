# -*- coding: utf-8 -*-
"""
 arayuz/pencere/proje.py  --  ac / kaydet / son kullanilanlar / ice ve disa aktarma

 arayuz/ana_pencere.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import ana_pencere; ana_pencere.X` aynen calisir.
"""

import os

from PySide6 import QtCore, QtGui, QtWidgets
from cekirdek import sema, ice_aktar, kod_uret, onbellek
from cekirdek.ceviri import _, _n, N_
from cekirdek.gunluk import kaydedici
from arayuz.pencere.model_islemleri import ORNEKLER

_log = kaydedici(__name__)


# Yalniz isaretlenir (N_); gosterirken _(_ICE_AKTAR_NOTU).
_ICE_AKTAR_NOTU = N_("Yalnızca malzemeler aktarılır: OpenMC geometrisi ham CSG'dir "
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
            _log.warning("son kullanilanlar listesi okunamadi", exc_info=True)
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
            e = self.m_son.addAction(_("(boş)"))
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
            QtWidgets.QMessageBox.Question, _("Kaydedilmemiş değişiklikler"),
            _("Değişiklikler kaydedilmedi. Kaydedilsin mi?"),
            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard
            | QtWidgets.QMessageBox.Cancel, self)
        # Qt'nin Turkce cevirisinde "Discard" -> "At"; burada acik adlar.
        for dugme, ad in ((QtWidgets.QMessageBox.Save, _("Kaydet")),
                          (QtWidgets.QMessageBox.Discard, _("Kaydetme")),
                          (QtWidgets.QMessageBox.Cancel, _("Vazgeç"))):
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
        yol, _suzgec = QtWidgets.QFileDialog.getOpenFileName(
            self, _("Model aç"), ORNEKLER, _("JSON model (*.json);;Tüm dosyalar (*)"))
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
            _log.exception("proje islemi basarisiz: %s", "Açılamadı")
            QtWidgets.QMessageBox.critical(self, _("Açılamadı"), str(e))
            return False
        self._proje_kur(yeni, proje_yolu=os.path.abspath(yol), ornek_kaynagi=None)
        self._sona_ekle(yol)
        self.bildir_mesaj(_("Açıldı: %s") % yol, "basari", 6000)
        return True

    def ornek_ac(self, yol):
        """Bir ornegi kaydedilmemis KOPYA olarak acar (proje_yolu = None)."""
        if not self._kaydetme_sor():
            return False
        try:
            yeni = sema.yukle(yol)
        except Exception as e:
            _log.exception("proje islemi basarisiz: %s", "Açılamadı")
            QtWidgets.QMessageBox.critical(self, _("Açılamadı"), str(e))
            return False
        self._proje_kur(yeni, proje_yolu=None, ornek_kaynagi=os.path.abspath(yol))
        self.bildir_mesaj(
            _("Örnek kopya olarak açıldı: %s — kaydetmek için 'Farklı kaydet' "
              "kullanın (örnek dosyası değişmez)") % os.path.basename(yol), "basari", 8000)
        return True

    def proje_kaydet(self):
        if self.proje_yolu is None:
            return self.proje_farkli_kaydet()
        try:
            sema.kaydet(self.spec, self.proje_yolu)
        except Exception as e:
            _log.exception("proje islemi basarisiz: %s", "Kaydedilemedi")
            QtWidgets.QMessageBox.critical(self, _("Kaydedilemedi"), str(e))
            return False
        self._kirli = False
        self._baslik_guncelle()
        self._sona_ekle(self.proje_yolu)
        self.bildir_mesaj(_("Kaydedildi: %s") % self.proje_yolu, "basari", 5000)
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
        yol, _suzgec = QtWidgets.QFileDialog.getSaveFileName(
            self, _("Modeli kaydet"), varsayilan, _("JSON model (*.json)"))
        if not yol:
            return False
        if not yol.endswith(".json"):
            yol += ".json"
        self.proje_yolu = yol
        self.ornek_kaynagi = None
        self.s_calistir.spec_ayarla(self.spec, self.proje_yolu)
        self.s_tukenme.proje_ayarla(self.proje_yolu)
        return self.proje_kaydet()

    # ==================================================================
    # rapor (Ajan 10'un cekirdek/rapor.py sozlesmesi)
    # ==================================================================
    RAPOR_SUZGECI = "HTML (*.html);;PDF (*.pdf)"

    def rapor_olustur(self):
        """Dosya > Rapor olustur…: model (+ varsa son basarili kosu) raporu."""
        varsayilan = os.path.splitext(self.proje_yolu or "rapor.json")[0] + ".html"
        yol, suzgec = QtWidgets.QFileDialog.getSaveFileName(
            self, _("Rapor oluştur"), varsayilan, self.RAPOR_SUZGECI)
        if not yol:
            return False
        bicim = "pdf" if (yol.lower().endswith(".pdf")
                          or "pdf" in (suzgec or "").lower()) else "html"
        if not yol.lower().endswith("." + bicim):
            yol += "." + bicim
        from cekirdek import rapor            # tembel: Qt'siz cekirdek modulu
        kosu, kosu_notu = self._rapor_kosusu()
        try:
            sonuc = rapor.olustur(self.spec, kosu, yol, bicim)
        except rapor.RaporHatasi as e:        # metni dogrudan gosterilebilir
            _log.warning("rapor olusturulamadi: %s", e)
            QtWidgets.QMessageBox.critical(self, _("Rapor oluşturulamadı"), str(e))
            return False
        metin = _("Rapor yazıldı: %s") % os.path.basename(sonuc.yol)
        uyarilar = list(sonuc.uyarilar) + ([kosu_notu] if kosu_notu else [])
        if uyarilar:
            metin += "\n" + "\n".join(uyarilar)
        self.bildir_mesaj(metin, "uyari" if uyarilar else "basari", 8000,
                          eylem_metni=_("Aç"), eylem=lambda: self._dosyayi_ac(sonuc.yol))
        return True

    def _rapor_kosusu(self):
        """(kosu dizini | None, not). Bu oturumda basarili kosu yoksa projenin kosu
        dizininde kayitli bir statepoint aranir ve kullaniciya SORULUR (QA14-Q8);
        kosusuz rapor sessizce yazilmaz: not bildirimde gorunur."""
        from cekirdek import kosucu
        kosu = self.s_calistir.son_kosu_dizini()
        if kosu:
            return kosu, ""
        aday = self.s_calistir._kosu_dizini()
        if aday and os.path.isdir(aday) and kosucu.son_statepoint(aday):
            if self._rapor_kosusu_sor(aday):
                return aday, _("Rapora diskteki kayıtlı koşu eklendi (%s); modelin şimdiki "
                               "hâliyle aynı olmayabilir.") % aday
        return None, _("Koşu sonucu yüklü değil: rapor yalnız modeli içerir.")

    def _rapor_kosusu_sor(self, dizin):
        """Kayitli kosu rapora eklensin mi (testler bunu degistirir)."""
        cevap = QtWidgets.QMessageBox.question(
            self, _("Kayıtlı koşu"), _("Bu oturumda koşu yapılmadı, ama proje dizininde kayıtlı "
                                       "bir koşu var:\n%s\n\nRapora eklensin mi? (Hayır: "
                                       "rapor yalnız modeli içerir.)") % dizin,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes)
        return cevap == QtWidgets.QMessageBox.Yes

    @staticmethod
    def _dosyayi_ac(yol):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(yol))

    def malzeme_ice_aktar(self):
        yol, _suzgec = QtWidgets.QFileDialog.getOpenFileName(
            self, _("Malzeme içeren OpenMC XML dosyası"),
            os.path.dirname(self.proje_yolu) if self.proje_yolu else os.path.expanduser("~"),
            _("OpenMC XML (materials.xml model.xml *.xml);;Tüm dosyalar (*)"))
        if not yol:
            return
        try:
            yeni_malzemeler, notlar = ice_aktar.malzemeleri_oku(yol)
        except Exception as e:
            _log.exception("proje islemi basarisiz: %s", "Okunamadı")
            QtWidgets.QMessageBox.critical(self, _("Okunamadı"), str(e))
            return
        if not yeni_malzemeler:
            QtWidgets.QMessageBox.information(self, _("Boş"),
                                              _("Dosyada malzeme bulunamadı."))
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
        k = len(yeni_malzemeler)
        mesaj = _n("%d malzeme eklendi.", "%d malzeme eklendi.", k) % k + "\n\n"
        if notlar:
            mesaj += _("Notlar:") + "\n" + "\n".join("  - " + n for n in notlar) + "\n\n"
        mesaj += _(_ICE_AKTAR_NOTU)
        self.bildir_mesaj(_n("%d malzeme içe aktarıldı — geometri aktarılmaz, "
                             "arayüzde kurulur.",
                             "%d malzeme içe aktarıldı — geometri aktarılmaz, "
                             "arayüzde kurulur.", k) % k, "basari", 8000)
        QtWidgets.QMessageBox.information(self, _("İçe aktarıldı"), mesaj)

    def betik_disa_aktar(self):
        varsayilan = os.path.splitext(self.proje_yolu or "model.json")[0] + ".py"
        yol, _suzgec = QtWidgets.QFileDialog.getSaveFileName(
            self, _("Python betiği olarak dışa aktar"), varsayilan, "Python (*.py)")
        if not yol:
            return
        try:
            kod = kod_uret.uret(self.spec, os.path.basename(yol))
            with open(yol, "w", encoding="utf-8") as f:
                f.write(kod)
        except Exception as e:
            _log.exception("proje islemi basarisiz: %s", "Üretilemedi")
            QtWidgets.QMessageBox.critical(self, _("Üretilemedi"), str(e))
            return
        satir = len(kod.splitlines())
        QtWidgets.QMessageBox.information(
            self, _("Dışa aktarıldı"),
            _n("Betik yazıldı:\n%s\n\n%d satır. Tek başına çalışır; arayüze geri "
               "yüklenemez.",
               "Betik yazıldı:\n%s\n\n%d satır. Tek başına çalışır; arayüze geri "
               "yüklenemez.", satir) % (yol, satir))

    def xml_disa_aktar(self):
        dizin = QtWidgets.QFileDialog.getExistingDirectory(
            self, _("XML'lerin yazılacağı dizin"),
            os.path.dirname(self.proje_yolu) if self.proje_yolu else os.path.expanduser("~"))
        if not dizin:
            return
        try:
            model, _bilgi = onbellek.kur_taze(self.spec)
            model.export_to_model_xml(os.path.join(dizin, "model.xml"))
        except Exception as e:
            _log.exception("proje islemi basarisiz: %s", "Üretilemedi")
            QtWidgets.QMessageBox.critical(self, _("Üretilemedi"), str(e))
            return
        self.bildir_mesaj(_("XML yazıldı: %s/model.xml") % dizin, "basari", 6000)

    def png_kaydet(self):
        yol, _suzgec = QtWidgets.QFileDialog.getSaveFileName(
            self, _("Önizlemeyi kaydet"), "geometri.png", "PNG (*.png)")
        if yol:
            self.onizleme.kaydet(yol)
            self.bildir_mesaj(_("Kaydedildi: %s") % yol, "basari", 5000)
