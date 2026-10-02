# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_tukenme.py  --  Yanma (tukenme) ayarlari, kosusu ve sonuclari
================================================================================
 Ayarlar spec'in "tukenme" bolumune yazilir (diger editor sekmeleri gibi).
 Kosu `openmc-arayuz-kosu --alt tukenme` ALT SURECI olarak QProcess ile yapilir
 (komut: cekirdek.giris.alt_surec_komutu):
 openmc.lib icindeki bir C++ terminate() tum sureci oldurur (onizlemede
 yasandi); arayuz bu kodu kendi surecinde asla calistirmaz.

 SAYFA (alt sekme YOK, yukaridan asagiya tek akis)
   acma anahtari + kisa aciklama      -- tukenme kapaliyken YALNIZCA bunlar
   guc, adim birimi, adimlar, yanan malzemeler
   Gelismis: zincir, entegrator, cubuk cubuk yanma (yakit birden fazla
             ornekse)
   Izlenen nuklidler: aranabilir gruplu secici (arayuz/nuklid_secici.py);
             secim degisince gosterilen sonuc h5'ten yeniden okunur
   kosu cubugu, onceki sonuc/eskime isareti, grafik, tablo, CSV
             (sonuc bolumu: arayuz/tukenme_sonuc.py)
   Ayrintili cikti (katlanir; hata olursa kendiliginden acilir)
 Modelde tukenme uygun degilse (uygunluk.tukenme_uygun) sekme zaten gizlidir;
 sekme yine de gosterilirse yalnizca nedenini soyleyen bos durum gorunur.

 Ilerleme olculur, tahmin edilmez: toplam transport sayisi bilinir
 ((adim x entegrator basina) + 1) ve ILK transport bittiginde kalan sure
 onun gercek suresinden hesaplanir.

 PROJE KUSAGI
   sifirla() bir kusak sayacini artirir; onceki projede baslamis bir kosunun
   ya da onceki-sonuc okumasinin sonucu YENI projeye yazilmaz.
================================================================================
"""

import copy
import json
import os
import sys
import time

from PySide6 import QtCore, QtWidgets

from cekirdek import giris as _giris
from cekirdek import tukenme as _tk
from cekirdek import yollar
from cekirdek.tukenme_hacim import yontem_metni
from cekirdek.ceviri import _, _n
from cekirdek.gunluk import kaydedici
from arayuz.analiz.adlar import renk
from arayuz.ortak import SekmeTabani, cumle_basi
from arayuz.tukenme_arayuz import ZINCIR_SECENEK, TukenmeArayuzu  # noqa: F401 (geriye uyum)
from arayuz.tukenme_sonuc import SonucBolumu

_log = kaydedici(__name__)

KOK = yollar.paket_koku()   # alt surecin calisma dizini (eski davranis)


def yakit_ornek_sayisi(spec):
    """Geriye uyum: sayim cekirdek/tukenme.py'de."""
    return _tk.yakit_ornek_sayisi(spec)


class TukenmeSekmesi(SekmeTabani, SonucBolumu, TukenmeArayuzu):

    KONU = "tukenme"
    durum = QtCore.Signal(str, bool)
    # Gosterilen tukenme sonucunun durumu degisti (bitti / basarisiz / okundu /
    # sifirlandi).
    sonuc_degisti = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.proje_yolu = None
        self.okuma_kaynagi = None     # kopyasi acilmis ornek (yalnizca OKUMA)
        self._kapi = lambda: (False, _("hazır değil"))
        self._surec = None
        self._dizin = None
        self._tampon = ""
        self._transport = 0
        self._t0 = None
        self._t_ilk = None
        self._kusak = 0               # proje kusagi (sifirla artirir)
        self._kosu_kusagi = None      # suren kosunun kusagi
        self._okuma_kusagi = None     # suren onceki-sonuc okumasinin kusagi
        self._kosu_spec = None        # kosunun baslatildigi spec (kopya)
        self._uygun = (True, "")

        self._onceki = None           # onceki_sonuc() ciktisi
        self._onceki_anahtar = None   # (h5 yolu, degisiklik zamani) -- yeniden okumayi onler
        self._isci = None
        self._secim_isci = None       # secim degisince h5'ten yeniden okuma
        self._secim_okunuyor = False
        self._secim_bekliyor = False  # okuma surerken secim yine degisti
        self._sonuc = None            # gosterilen sonuc_oku() ciktisi
        self._kaynak = None           # (h5, okuma spec'i): secim degisince yeniden okunur
        self._arayuzu_kur()           # widget'lar ve yerlesim: tukenme_arayuz.py
        self._adim_gucu_kur()         # v3 K3: "Adim basina pin gucu" (Gelismis)
        # Kapanista calisan okuma iscileri yok edilmesin (Qt sureci dusurur).
        uyg = QtWidgets.QApplication.instance()
        if uyg is not None:
            uyg.aboutToQuit.connect(self.isleri_durdur)

        # ---------------- sinyaller ----------------
        self.var.toggled.connect(self._kaydet)
        self.ayir.toggled.connect(self._kaydet)
        self.adim_gucu.toggled.connect(self._kaydet)
        for w in (self.zincir, self.birim, self.entegrator):
            w.currentIndexChanged.connect(self._kaydet)
        self.guc.valueChanged.connect(self._kaydet)
        self.adimlar.editingFinished.connect(self._kaydet)
        self.ek_liste.degisti.connect(self._kaydet)
        self._gorunum_guncelle()

    # ==================================================================
    # spec <-> arayuz
    # ==================================================================
    def doldur(self):
        t = self.spec.get("tukenme") or {}
        self.var.setChecked(bool(t.get("var")))
        i = self.zincir.findData(t.get("zincir") or "otomatik")
        self.zincir.setCurrentIndex(max(i, 0))
        self.guc.setValue(float(t.get("guc_yogunlugu") or 40.0))
        i = self.birim.findData(t.get("adim_birimi") or "d")
        self.birim.setCurrentIndex(max(i, 0))
        self.adimlar.setText(", ".join("%g" % float(a) for a in (t.get("adimlar") or [])))
        i = self.entegrator.findData(t.get("entegrator") or "cecm")
        self.entegrator.setCurrentIndex(max(i, 0))
        self.ayir.setChecked(bool(t.get("malzemeleri_ayir")))
        self.adim_gucu.setChecked(t.get("adim_gucu") is not False)     # varsayilan acik
        # Eski JSON'lardaki liste AYNEN korunur (zincirde olmayan ad bile silinmez).
        self.izlenen.secim_ayarla(list(t.get("izlenen") or []), sinyal=False)
        self.ek_liste.doldur(self.spec)
        self._ozet_guncelle()
        self._onceki_yukle()

    @staticmethod
    def _gecersiz_parcalar(metin):
        """Adim metninde sayiya cevrilemeyen parcalar."""
        kotu = []
        for p in (metin or "").replace(";", ",").split(","):
            p = p.strip()
            if not p:
                continue
            try:
                float(p)
            except ValueError:
                kotu.append(p)
        return kotu

    @staticmethod
    def _sayilar(metin):
        cikti = []
        for p in (metin or "").replace(";", ",").split(","):
            p = p.strip()
            if not p:
                continue
            try:
                cikti.append(float(p))
            except ValueError:   # gecersiz parca adim ozetinde gosterilir (_gecersiz_parcalar)
                continue
        return cikti

    def _kaydet(self, *_args):
        if self._yukleniyor:
            return
        # Sozluk BASTAN YAZILMAZ: arayuzde duzenlenmeyen alanlar korunur. Kaynak sekmesinde bu hatayi bir kez yapmistik. Gizli alanlarin
        # (or. tek ornekli modelde "cubuk cubuk yanma") degeri de korunur: kutu
        # spec'ten yuklenmistir ve kullanici degistiremez.
        t = self.spec.setdefault("tukenme", {})
        t["var"] = self.var.isChecked()
        t["zincir"] = self.zincir.currentData()
        t["guc_yogunlugu"] = self.guc.value()
        t["adim_birimi"] = self.birim.currentData()
        t["adimlar"] = self._sayilar(self.adimlar.text())
        t["entegrator"] = self.entegrator.currentData()
        t["malzemeleri_ayir"] = self.ayir.isChecked()
        # Varsayilan (acik) dosyaya yazilmaz: eski spec'ler gidis-donuste degismesin.
        if not self.adim_gucu.isChecked() or "adim_gucu" in t:
            t["adim_gucu"] = self.adim_gucu.isChecked()
        t["izlenen"] = self.izlenen.secim()
        t["ek_malzemeler"] = self.ek_liste.secim()
        self._ozet_guncelle()
        self.bildir()

    def _adim_gucu_kur(self):
        """Adim basina pin gucu (tukenme.adim_gucu; varsayilan acik). Gerekce:
        yanmaya gore pin gucu kullanici karari 3'tur; maliyet kucuk ama sifir degil."""
        self.adim_gucu = QtWidgets.QCheckBox(_("Adım başına pin gücü"))
        self.adim_gucu.setToolTip(_(
            "Her tükenme adımında çubuk güç dağılımı (distribcell + eksenel mesh tally'si) "
            "sayılır ve adım başına bir statepoint dosyası yazılır. Transport süresine etkisi "
            "küçüktür; disk ve bellek çubuk × eksenel dilim sayısıyla artar (ölçüldü: 24 "
            "çubuk × 4 dilimde adım başına 52 kB). On binlerce çubuklu tam korda kapatmayı "
            "düşünün."))
        self.gelismis_form.addRow("", self.adim_gucu)

    def _adim_gucu_anlamli(self):
        """Guc tally'si kurulabilen modelde (cubuklar bir kafeste) anlamli."""
        try:
            from cekirdek import uygunluk
            return bool(uygunluk.guc_cubuklari(self.spec))
        except Exception:
            _log.exception("güç çubukları belirlenemedi; 'adım başına pin gücü' gösteriliyor")
            return True

    def _uygunluk_oku(self):
        if not self.spec:
            return (False, _("model yok"))
        try:
            from cekirdek import uygunluk
            return uygunluk.tukenme_uygun(self.spec)
        except Exception:
            _log.exception("tükenme uygunluğu belirlenemedi; sekme açık bırakıldı")
            return (True, "")

    def _ayirma_anlamli(self):
        try:
            from cekirdek import uygunluk
            return uygunluk.tukenme_ayirma_anlamli(self.spec)
        except Exception:
            _log.exception("yakıt örnekleri sayılamadı; 'çubuk çubuk yanma' gösteriliyor")
            return True                  # sayilamadi: secenegi saklama

    def _ozet_guncelle(self):
        t = (self.spec or {}).get("tukenme") or {}
        self._uygun = self._uygunluk_oku()

        # --- cubuk cubuk yanma: yalnizca yakit birden fazla ornekse ---
        self.gelismis_form.setRowVisible(self.ayir, self._ayirma_anlamli())
        self.gelismis_form.setRowVisible(self.adim_gucu, self._adim_gucu_anlamli())

        # --- zincir ---
        self.zincir_uyari.setText("")
        try:
            zs = _tk.zincir_secimi(self.spec)
            self.izlenen.zincir_ayarla(zs["yol"])
            from cekirdek import veri_bilgi
            tamam, mesaj, _ayrinti = veri_bilgi.zincir_kontrol(zs["yol"])
            metin = (_("%s  |  fisyon verimi %s eV (%s spektrum)\n%s")
                     % (os.path.basename(zs["yol"]), "%g" % zs["verim_enerjisi"],
                        _tk.spektrum_adi(zs["temel"]),
                        cumle_basi(zs["gerekce"])))
            if not tamam:
                metin += "\n" + mesaj
                # Gelismis kapaliyken de gorulsun: kosuyu engelleyen bir sorun.
                self.zincir_uyari.setText(_("Zincir dosyası kullanılamıyor: %s "
                                            "(Gelişmiş › Zincir)") % mesaj)
            self.zincir_bilgi.setText(metin)
            self.zincir_bilgi.setStyleSheet(
                "" if tamam else "color: %s;" % renk("hata"))
        except Exception as e:
            self.zincir_bilgi.setText(_("zincir seçilemedi: %s") % e)
        self.zincir_uyari.setStyleSheet("color: %s;" % renk("hata"))

        # --- adimlar ---
        adimlar = [float(a) for a in (t.get("adimlar") or [])]
        p = float(t.get("guc_yogunlugu") or 0.0)
        # Sayi olmayan parca eskiden SESSIZCE atiliyordu; eksi adimla da
        # "toplam -4 gün" yaziliyordu (Ajan 9 bulgusu).
        gecersiz = self._gecersiz_parcalar(self.adimlar.text())
        self.adim_ozet.setStyleSheet("")
        if gecersiz or any(a <= 0 for a in adimlar):
            neden = ((_("sayı olmayan: %s") % ", ".join(gecersiz)) if gecersiz
                     else _("her adım sıfırdan büyük olmalı"))
            self.adim_ozet.setText(_("Adımlar geçersiz — %s. Virgülle ayrılmış pozitif "
                                     "sayılar girin (ör. 1, 5, 30).") % neden)
            self.adim_ozet.setStyleSheet("color: %s;" % renk("hata"))
        elif adimlar and p > 0:
            if (t.get("adim_birimi") or "d") == "d":
                gun = sum(adimlar)
                bu = _tk.yanma(gun, p)
            else:
                bu = sum(adimlar)
                gun = bu * 1000.0 / p
            self.adim_ozet.setText(
                _n("%d adım · toplam %.4g gün = %.4g MWd/kg · %d transport çözümü",
                   "%d adım · toplam %.4g gün = %.4g MWd/kg · %d transport çözümü",
                   len(adimlar))
                % (len(adimlar), gun, bu, _tk.transport_sayisi(self.spec)))
        else:
            self.adim_ozet.setText(_("Adım yok — virgülle adım uzunlukları girin."))

        # --- yanabilir malzemeler ---
        try:
            hv = _tk.hacimler(self.spec)
            if not hv:
                self.malzeme_bilgi.setText(_("Yanabilir (fisil) malzeme bulunamadı."))
            else:
                satirlar = []
                for ad, v in hv.items():
                    satirlar.append("%s: %s  [%s]\n    %s"
                                    % (ad, ("%.6g cm³" % v["hacim"]) if v["hacim"]
                                       else _("hacim yok"), yontem_metni(v["yontem"]), v["ayrinti"]))
                self.malzeme_bilgi.setText("\n".join(satirlar))
        except Exception as e:
            self.malzeme_bilgi.setText(_("hesaplanamadı: %s") % e)
        self._onceki_durum_guncelle()
        self._gorunum_guncelle()
        self.kapi_guncelle()

    def _gorunum_guncelle(self):
        """
        Bolumlerin gorunurlugu tek yerden:
          uygun degil : yalnizca bos durum (nedeni)
          kapali      : acma anahtari + aciklama (+ varsa gosterilen sonuc)
          acik        : ayarlar, Gelismis, kosu cubugu
          kosu surerken kapatilsa da kosu cubugu gorunur kalir (Durdur)
        """
        uygun, neden = self._uygun
        acik = bool(((self.spec or {}).get("tukenme") or {}).get("var"))
        kosuyor = self._surec is not None
        self.bos.setVisible(not uygun and not kosuyor)
        if not uygun:
            self.bos.ayarla(metin=_cumle(neden or _("model uygun değil")))
        self.icerik.setVisible(uygun or kosuyor)
        self.ayar_kutusu.setVisible(acik)
        self.izlenen_kutusu.setVisible(acik or self.sonuc_var())
        self.kosu_kutusu.setVisible(acik or kosuyor)
        self.aciklama.setVisible(True)
        self.sonuc_kutusu.setVisible(self.sonuc_var() or kosuyor
                                     or bool(self.onceki_etiket.text()))
        self.ayrinti.setVisible(kosuyor or bool(self.log.toPlainText()))

    # ==================================================================
    # kosu
    # ==================================================================
    def kapi_ayarla(self, fonksiyon):
        self._kapi = fonksiyon

    def proje_ayarla(self, proje_yolu, okuma_kaynagi=None):
        """
        proje_yolu    : kaydedilmis proje dosyasi (yeni kosu buraya gore yazilir)
        okuma_kaynagi : kopyasi acilmis ornek/sablon dosyasi. Onceki sonuclar
                        yalnizca OKUMAK icin oradan aranir; yeni kosu asla
                        ornek dizinine yazilmaz.
        """
        self.proje_yolu = proje_yolu
        self.okuma_kaynagi = okuma_kaynagi

    def _okuma_dizini(self):
        """Onceki sonucun aranacagi dizin (bkz. proje_ayarla)."""
        dizin = _tk.kosu_dizini(self.spec, self.proje_yolu)
        if (self.proje_yolu is None and getattr(self, "okuma_kaynagi", None)
                and not os.path.exists(os.path.join(dizin, "depletion_results.h5"))):
            dizin = _tk.kosu_dizini(self.spec, self.okuma_kaynagi)
        return dizin

    def sonuc_var(self):
        """Bir tukenme sonucu (bu kosunun ya da onceki kosunun) gosteriliyor mu."""
        return self.tablo.rowCount() > 0

    def _eski_kosu(self):
        return self._kosu_kusagi is not None and self._kosu_kusagi != self._kusak

    def sifirla(self):
        """
        PROJE degisince onceki projenin gosterilen sonucunu siler. Kusak artar:
        onceki projede baslamis ve hala suren kosunun ciktisi/sonucu, ya da
        onceki-sonuc okumasi, yeni projeye yazilmaz.
        """
        self._kusak += 1
        self.bekle()                  # suren okuma biter; sonucu kusaktan atilir
        self._onceki = self._onceki_anahtar = None
        self._sonucu_unut()
        self.onceki_etiket.setText("")
        self.onceki_etiket.setStyleSheet("")
        self.tablo.setRowCount(0)
        self._grafik_bos()
        self.log.clear()
        self.sure_etiket.setText("")
        if self._surec is None:
            self.ilerleme.setRange(0, 1)
            self.ilerleme.setValue(0)
            self.ilerleme.resetFormat()
        else:
            self.ilerleme.setRange(0, 0)
            self.kapi_etiket.setStyleSheet("color: %s;" % renk("hata"))
            self.kapi_etiket.setText(
                _("Önceki projenin tükenme koşusu arka planda sürüyor; sonucu bu projeye "
                  "yazılmayacak. Yeni koşu için Durdur ile sonlandırın."))
        self._gorunum_guncelle()
        self.sonuc_degisti.emit()

    def kapi_guncelle(self):
        if self._surec is not None:
            return
        uygun, neden = self._uygun
        if not uygun:
            izin, mesaj = False, _("Bu modelde yapılamaz: %s") % _cumle(neden)
        elif not (self.spec or {}).get("tukenme", {}).get("var"):
            izin, mesaj = False, _("Tükenme kapalı — yukarıdan etkinleştirin.")
        else:
            izin, mesaj = self._kapi()
        self.d_baslat.setEnabled(izin)
        self.kapi_etiket.setStyleSheet(
            "color: %s;" % (renk("metin_soluk") if izin else renk("hata")))
        self.kapi_etiket.setText(mesaj)

    def baslat(self):
        izin, mesaj = self._kapi()
        uygun, neden = self._uygunluk_oku()
        if not uygun:
            QtWidgets.QMessageBox.warning(self, _("Başlatılamaz"),
                                          _("Bu modelde yapılamaz: %s") % _cumle(neden))
            return
        if not izin or not self.spec.get("tukenme", {}).get("var"):
            QtWidgets.QMessageBox.warning(self, _("Başlatılamaz"), mesaj)
            return
        if self._surec is not None:
            return
        dizin = _tk.kosu_dizini(self.spec, self.proje_yolu)
        os.makedirs(dizin, exist_ok=True)
        eski = os.path.join(dizin, "depletion_results.h5")
        if os.path.exists(eski):
            os.remove(eski)
        # Kaydedilmemis degisiklikler de kosulsun: spec kosu dizinine yazilir.
        # Sonuc da BU kopyaya gore okunur (kosu surerken spec duzenlenebilir).
        self._kosu_spec = copy.deepcopy(self.spec)
        spec_yolu = os.path.join(dizin, "tukenme_spec.json")
        with open(spec_yolu, "w", encoding="utf-8") as f:
            json.dump(self._kosu_spec, f, indent=2, ensure_ascii=False)
        self._dizin = dizin
        self._kosu_kusagi = self._kusak

        self.log.clear()
        self.onceki_etiket.setText("")
        self._onceki = self._onceki_anahtar = None
        self._sonucu_unut()
        self.tablo.setRowCount(0)
        self._tampon = ""
        self._transport = 0
        self._t0 = time.time()
        self._t_ilk = None
        toplam = _tk.transport_sayisi(self.spec)
        self.ilerleme.setRange(0, toplam)
        self.ilerleme.setValue(0)
        self.ilerleme.setFormat(_("%v / %m transport"))
        self.sure_etiket.setText(_("İlk transport bekleniyor — kalan süre ondan ölçülecek."))
        self._grafik_bos()

        n = (self.spec.get("calistirma") or {}).get("is_parcacigi", 8)
        self._surec = QtCore.QProcess(self)
        self._surec.setWorkingDirectory(KOK)
        ortam = QtCore.QProcessEnvironment.systemEnvironment()
        yol = _giris.alt_surec_pythonpath(ortam.value("PYTHONPATH"))
        if yol:                         # kaynak agaci: paket koku MEVCUDUN onune
            ortam.insert("PYTHONPATH", yol)
        ortam.insert("PYTHONUNBUFFERED", "1")
        from cekirdek import ceviri as _ceviri
        ortam.insert(_ceviri.ORTAM_DEGISKENI, _ceviri.etkin_dil())   # alt surec ayni dilde
        self._surec.setProcessEnvironment(ortam)
        self._surec.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self._surec.readyReadStandardOutput.connect(self._cikti_oku)
        self._surec.finished.connect(self._bitti)
        self._surec.errorOccurred.connect(self._surec_hatasi)
        program, arg = _giris.alt_surec_komutu(
            _giris.ALT_TUKENME, [spec_yolu, "-s", str(int(n)), "--dizin", dizin],
            python=sys.executable)
        self.log.appendPlainText("# %s %s\n" % (program, " ".join(arg)))
        self._surec.start(program, arg)
        self.d_baslat.setEnabled(False)
        self.d_durdur.setEnabled(True)
        self.kapi_etiket.setStyleSheet("color: %s;" % renk("metin_soluk"))
        self.kapi_etiket.setText(_("Tükenme koşusu sürüyor → %s") % dizin)
        self._gorunum_guncelle()
        self.sonuc_degisti.emit()
        self.durum.emit(_("Tükenme başladı → %s") % dizin, True)

    def durdur(self):
        if self._surec is not None:
            self._surec.kill()
            if not self._eski_kosu():
                self.log.appendPlainText(_("\n# kullanıcı tarafından durduruldu"))

    def _cikti_oku(self):
        if self._surec is None:
            return
        ham = bytes(self._surec.readAllStandardOutput()).decode("utf-8", "replace")
        if self._eski_kosu():
            return                    # onceki projenin kosusu: bu projeye yazilmaz
        self._tampon += ham
        while "\n" in self._tampon:
            satir, self._tampon = self._tampon.split("\n", 1)
            satir = satir.rstrip()
            # transport ciktisi cok uzun; yalnizca anlamli satirlar loga
            # Bizim terminal satirlarimiz TAM 2 bosluk girintili; OpenMC'nin
            # cevrim satirlari cok daha derin girintili ve logu bogar.
            bizim = satir.startswith("  ") and not satir.startswith("   ")
            if (satir.startswith("[openmc.deplete]") or bizim
                    or "Combined k-effective" in satir or "TÜKENME" in satir
                    or "Error" in satir or "HATA" in satir or "Traceback" in satir):
                self.log.appendPlainText(satir)
            # Transport basina TAM BIR KEZ yazilan satir. "Creating state point"
            # SAYILMAZ: adim basi transportu iki statepoint yazar
            # (openmc_simulation_nX.h5 + statepoint.N.h5), CECM ara transportu
            # bir -- olculdu: 17 transportta 26 satir. Onu saymak cubugu
            # tasiriyor ve kalan sure tahminini bozuyordu.
            if "Combined k-effective" in satir:
                self._transport += 1
                self.ilerleme.setValue(self._transport)
                gecen = time.time() - self._t0
                if self._t_ilk is None:
                    self._t_ilk = gecen
                kalan = (self.ilerleme.maximum() - self._transport) * gecen / self._transport
                self.sure_etiket.setText(
                    _("geçen %s  |  transport başına %.0f s (ölçülen)  |  kalan ~%s")
                    % (_sure(gecen), gecen / self._transport, _sure(kalan)))

    def _surec_hatasi(self, kod):
        # Baslatilamayan surec finished() YAYMAZ: dugmeler kilitli kalirdi.
        if self._surec is not None and kod == QtCore.QProcess.FailedToStart:
            if not self._eski_kosu():
                self.log.appendPlainText(_("\n# Süreç başlatılamadı: %s")
                                         % self._surec.errorString())
            self._bitti(-1, None)

    def _bitti(self, cikis_kodu, _durum):
        eski = self._eski_kosu()
        surec, self._surec = self._surec, None
        if surec is not None:
            try:
                surec.deleteLater()
            except RuntimeError:         # C++ nesnesi zaten silinmis
                _log.debug("tükenme süreci zaten silinmiş", exc_info=True)
        self._kosu_kusagi = None
        self.d_durdur.setEnabled(False)
        self.kapi_guncelle()
        if eski:
            # Onceki projenin kosusu: sonucu bu projeye YAZILMAZ; bu projenin
            # (varsa) onceki sonucu okunur.
            self.ilerleme.setRange(0, 1)
            self.ilerleme.setValue(0)
            self.ilerleme.resetFormat()
            self._gorunum_guncelle()
            self.durum.emit(_("Önceki projenin tükenme koşusu bitti; sonucu bu projeye "
                              "yazılmadı (dosyalar: %s).") % self._dizin, True)
            self._onceki_yukle()
            return
        h5 = os.path.join(self._dizin or "", "depletion_results.h5")
        if cikis_kodu != 0 or not os.path.exists(h5):
            self.durum.emit(_("Tükenme başarısız (çıkış kodu %d)") % cikis_kodu, False)
            self.sure_etiket.setText(_("Başarısız — ayrıntılı çıktı aşağıda açıldı."))
            self.ayrinti.ac(True)
            self._gorunum_guncelle()
            self.sonuc_degisti.emit()
            return
        try:
            s = _tk.sonuc_oku(h5, self._kosu_spec or self.spec, izlenen=self.izlenen.secim())
        except Exception as e:
            _log.exception("tükenme sonucu okunamadı: %s", h5)
            self.durum.emit(_("Sonuç okunamadı: %s") % e, False)
            self.sure_etiket.setText(_("Sonuç okunamadı — ayrıntılı çıktıya bakın."))
            self.log.appendPlainText(_("\n# Sonuç okunamadı: %s") % e)
            self.ayrinti.ac(True)
            self._gorunum_guncelle()
            self.sonuc_degisti.emit()
            return
        self._sonuc_goster(s, (h5, copy.deepcopy(self._kosu_spec or self.spec)))
        self.sure_etiket.setText(_("Tamamlandı: %s") % _sure(time.time() - self._t0))
        self.durum.emit(_("Tükenme tamamlandı"), True)

    # ==================================================================
    # kapanis
    # ==================================================================
    def closeEvent(self, olay):                        # noqa: N802 (Qt API)
        """
        Sekme kapanirken ARKADA bir sey birakilmaz: suren okuma beklenir ve
        kuyruktaki matplotlib cizimi iptal edilir. Ikisi de birakilirsa sekme
        silindikten sonra olu C++ nesnesine gidip sureci dusuruyordu
        (bkz. arayuz/analiz/tuval.py).
        """
        self.bekle()
        self.tuval.cizimi_iptal_et()
        super().closeEvent(olay)


def _cumle(metin):
    """uygunluk'un kucuk harfle baslayan nedenini cumleye cevirir (Turkce buyuk harf)."""
    metin = (metin or "").strip()
    if not metin:
        return ""
    ilk = {"i": "İ", "ı": "I"}.get(metin[0], metin[0].upper())
    return ilk + metin[1:] + ("" if metin.endswith(".") else ".")


def _sure(s):
    s = int(max(s, 0))
    if s < 90:
        return "%d s" % s
    if s < 5400:
        return _("%d dk") % round(s / 60.0)
    return _("%.1f sa") % (s / 3600.0)
