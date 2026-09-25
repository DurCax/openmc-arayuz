# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_tukenme.py  --  Yanma (tukenme) ayarlari, kosusu ve sonuclari
================================================================================
 Ayarlar spec'in "tukenme" bolumune yazilir (diger editor sekmeleri gibi).
 Kosu `python -m cekirdek.tukenme` ALT SURECI olarak QProcess ile yapilir:
 openmc.lib icindeki bir C++ terminate() tum sureci oldurur (onizlemede
 yasandi); arayuz bu kodu kendi surecinde asla calistirmaz.

 Ilerleme olculur, tahmin edilmez: toplam transport sayisi bilinir
 ((adim x entegrator basina) + 1) ve ILK transport bittiginde kalan sure
 onun gercek suresinden hesaplanir.
================================================================================
"""

import json
import os
import sys
import time

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6 import QtCore, QtWidgets

from cekirdek import tukenme as _tk
from arayuz.ortak import SekmeTabani, ayrac, baslik, ipucu, sayi

ZINCIR_SECENEK = [
    ("otomatik",    "Otomatik (spektrumdan)"),
    ("termal",      "ENDF/B-VIII.0 termal (3820 nuklid)"),
    ("hizli",       "ENDF/B-VIII.0 hizli (3820 nuklid)"),
    ("casl_termal", "CASL basit termal (228 nuklid, ~3x hizli)"),
    ("casl_hizli",  "CASL basit hizli (228 nuklid, ~3x hizli)"),
]

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _OncekiIsci(QtCore.QThread):
    """
    Onceki sonucu arka planda okur.

    Olculdu: 3.4 s -- openmc.deplete ice aktarimi (kutuphane yukleniyor,
    1.2 s) + Results() dosyadaki 3820 nuklidin hepsini ayristiriyor (2.0 s).
    Ikisi de resmi API'de kacinilmaz; OpenMC'nin ic dosya bicimini elle okumak
    surum degisince kirilirdi. Arayuzde calissa dosya acilisi 3.4 s donardi.
    """
    bitti = QtCore.Signal(object, object)      # (anahtar, sonuc | Exception)

    def __init__(self, spec, dizin, anahtar, parent=None):
        super().__init__(parent)
        import copy
        self._spec = copy.deepcopy(spec)       # arayuz spec'i degistirirse yaris olmasin
        self._dizin = dizin
        self._anahtar = anahtar

    def run(self):
        try:
            self.bitti.emit(self._anahtar, _tk.onceki_sonuc(self._spec, self._dizin))
        except Exception as e:
            self.bitti.emit(self._anahtar, e)


class TukenmeSekmesi(SekmeTabani):

    KONU = "tukenme"
    durum = QtCore.Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.proje_yolu = None
        self._kapi = lambda: (False, "hazir degil")
        self._surec = None
        self._dizin = None
        self._tampon = ""
        self._transport = 0
        self._t0 = None
        self._t_ilk = None

        # ---------------- ayarlar ----------------
        self.var = QtWidgets.QCheckBox("Tukenme (yanma) hesabini etkinlestir")
        self.zincir = QtWidgets.QComboBox()
        for k, ad in ZINCIR_SECENEK:
            self.zincir.addItem(ad, k)
        self.zincir_bilgi = QtWidgets.QLabel("-")
        self.zincir_bilgi.setWordWrap(True)
        self.guc = sayi(40.0, 3, 0.001, 10000.0, 1.0, " W/gHM")
        self.guc.setToolTip(
            "GUC YOGUNLUGU, agir metalin gramı basina. Mutlak guc kullanilmaz:\n"
            "2B bir modelde 'cm basina' olmak zorunda kalirdi.\n\n"
            "Tipik: PWR 38-40, BWR ~25, SFR 50-100 W/gHM.")
        self.birim = QtWidgets.QComboBox()
        self.birim.addItem("gun", "d")
        self.birim.addItem("MWd/kg (yanma)", "MWd/kg")
        self.adimlar = QtWidgets.QLineEdit()
        self.adimlar.setToolTip(
            "Adim uzunluklari, virgulle. Ilk adimlari KISA tutun (or. 0.5, 1.5):\n"
            "Xe-135 ~2 gunde dengeye gelir ve PWR'da birkac bin pcm'lik hizli\n"
            "bir dusus yaratir; uzun bir ilk adim bunu gorunmez kilar.")
        self.adim_ozet = QtWidgets.QLabel("-")
        self.adim_ozet.setWordWrap(True)
        self.entegrator = QtWidgets.QComboBox()
        self.entegrator.addItem("CECM (ongorucu-duzeltici, adim basina 2 transport)", "cecm")
        self.entegrator.addItem("Predictor (adim basina 1 transport, kaba)", "predictor")
        self.ayir = QtWidgets.QCheckBox("Cubuk cubuk yanma (her hucre ayri malzeme -- cok agir)")
        self.izlenen = QtWidgets.QLineEdit()
        self.malzeme_bilgi = QtWidgets.QLabel("-")
        self.malzeme_bilgi.setWordWrap(True)
        self.malzeme_bilgi.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        form = QtWidgets.QFormLayout()
        form.addRow(self.var)
        form.addRow("Zincir:", self.zincir)
        form.addRow("", self.zincir_bilgi)
        form.addRow("Guc yogunlugu:", self.guc)
        form.addRow("Adim birimi:", self.birim)
        form.addRow("Adimlar:", self.adimlar)
        form.addRow("", self.adim_ozet)
        form.addRow("Entegrator:", self.entegrator)
        form.addRow(self.ayir)
        form.addRow("Izlenen nuklidler:", self.izlenen)

        # ---------------- kosu ----------------
        self.d_baslat = QtWidgets.QPushButton("TUKENMEYI BASLAT")
        self.d_baslat.setMinimumHeight(32)
        f = self.d_baslat.font(); f.setBold(True); self.d_baslat.setFont(f)
        self.d_durdur = QtWidgets.QPushButton("Durdur")
        self.d_durdur.setEnabled(False)
        self.ilerleme = QtWidgets.QProgressBar()
        self.ilerleme.setTextVisible(True)
        self.kapi_etiket = QtWidgets.QLabel("-")
        self.kapi_etiket.setWordWrap(True)
        self.sure_etiket = QtWidgets.QLabel("")
        self.onceki_etiket = QtWidgets.QLabel("")
        self.onceki_etiket.setWordWrap(True)
        self._onceki = None           # onceki_sonuc() ciktisi
        self._onceki_anahtar = None   # (h5 yolu, degisiklik zamani) -- yeniden okumayi onler
        self._isci = None
        self.d_baslat.clicked.connect(self.baslat)
        self.d_durdur.clicked.connect(self.durdur)

        self.figur = Figure(figsize=(5, 4.2), tight_layout=True)
        self.tuval = FigureCanvasQTAgg(self.figur)
        self.tuval.setMinimumHeight(260)
        self.eksen_k = self.figur.add_subplot(211)
        self.eksen_n = self.figur.add_subplot(212)
        self._grafik_bos()

        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        lf = self.log.font(); lf.setFamily("monospace"); lf.setPointSizeF(8.5)
        self.log.setFont(lf)
        self.log.setMaximumBlockCount(4000)
        self.tablo = QtWidgets.QTableWidget(0, 4)
        self.tablo.setHorizontalHeaderLabels(["gun", "MWd/kg", "k-eff", "rho [pcm]"])
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.verticalHeader().setVisible(False)
        alt = QtWidgets.QTabWidget()
        alt.addTab(self.tablo, "Sonuc tablosu")
        alt.addTab(self.log, "Kosu ciktisi")
        self.alt = alt

        # ---------------- yerlesim ----------------
        sol = QtWidgets.QVBoxLayout()
        sol.addWidget(baslik("Tukenme ayarlari"))
        sol.addLayout(form)
        sol.addWidget(ayrac())
        sol.addWidget(baslik("Yanabilir malzemeler"))
        sol.addWidget(self.malzeme_bilgi)
        sol.addWidget(ipucu(
            "Fisil malzemeler ve yanabilir zehirler (Gd, Er) otomatik yanar. "
            "Hacimler ANALITIK hesaplanir: yanlis bir hacim yanma hizini ayni "
            "oranda bozar ve k-eff'te iz birakmaz. Testte OpenMC'nin stokastik "
            "hacim hesabiyla 1 sigma icinde uyustugu olculdu."))
        sol.addStretch(1)

        sag = QtWidgets.QVBoxLayout()
        sag.addWidget(baslik("Kosu"))
        sag.addWidget(self.kapi_etiket)
        ust = QtWidgets.QHBoxLayout()
        ust.addWidget(self.d_baslat)
        ust.addWidget(self.d_durdur)
        ust.addWidget(self.ilerleme, 1)
        sag.addLayout(ust)
        sag.addWidget(self.sure_etiket)
        sag.addWidget(self.onceki_etiket)
        sag.addWidget(self.tuval)
        sag.addWidget(alt, 1)

        sol_k = QtWidgets.QWidget(); sol_k.setLayout(sol)
        sag_k = QtWidgets.QWidget(); sag_k.setLayout(sag)
        bolucu = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        bolucu.addWidget(sol_k); bolucu.addWidget(sag_k)
        bolucu.setStretchFactor(0, 4); bolucu.setStretchFactor(1, 5)
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(bolucu)

        # ---------------- sinyaller ----------------
        self.var.toggled.connect(self._kaydet)
        self.ayir.toggled.connect(self._kaydet)
        for w in (self.zincir, self.birim, self.entegrator):
            w.currentIndexChanged.connect(self._kaydet)
        self.guc.valueChanged.connect(self._kaydet)
        for w in (self.adimlar, self.izlenen):
            w.editingFinished.connect(self._kaydet)

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
        self.izlenen.setText(", ".join(t.get("izlenen") or []))
        self._ozet_guncelle()
        self._onceki_yukle()

    @staticmethod
    def _sayilar(metin):
        cikti = []
        for p in (metin or "").replace(";", ",").split(","):
            p = p.strip()
            if not p:
                continue
            try:
                cikti.append(float(p))
            except ValueError:
                pass
        return cikti

    def _kaydet(self, *_):
        if self._yukleniyor:
            return
        # Sozluk BASTAN YAZILMAZ: arayuzde duzenlenmeyen alanlar (ek_malzemeler)
        # korunur. Kaynak sekmesinde bu hatayi bir kez yapmistik.
        t = self.spec.setdefault("tukenme", {})
        t["var"] = self.var.isChecked()
        t["zincir"] = self.zincir.currentData()
        t["guc_yogunlugu"] = self.guc.value()
        t["adim_birimi"] = self.birim.currentData()
        t["adimlar"] = self._sayilar(self.adimlar.text())
        t["entegrator"] = self.entegrator.currentData()
        t["malzemeleri_ayir"] = self.ayir.isChecked()
        t["izlenen"] = [x.strip() for x in self.izlenen.text().split(",") if x.strip()]
        self._ozet_guncelle()
        self.bildir()

    def _ozet_guncelle(self):
        t = self.spec.get("tukenme") or {}
        acik = bool(t.get("var"))
        for w in (self.zincir, self.guc, self.birim, self.adimlar,
                  self.entegrator, self.ayir, self.izlenen):
            w.setEnabled(acik)

        # --- zincir ---
        try:
            zs = _tk.zincir_secimi(self.spec)
            from cekirdek import veri_bilgi
            tamam, mesaj, _ = veri_bilgi.zincir_kontrol(zs["yol"])
            metin = ("%s  |  fisyon verimi %s eV (%s)\n%s"
                     % (os.path.basename(zs["yol"]), "%g" % zs["verim_enerjisi"],
                        zs["temel"], zs["gerekce"]))
            if not tamam:
                metin += "\n!! " + mesaj
            self.zincir_bilgi.setText(metin)
            self.zincir_bilgi.setStyleSheet("" if tamam else "color: #d04437;")
        except Exception as e:
            self.zincir_bilgi.setText("zincir secilemedi: %s" % e)

        # --- adimlar ---
        adimlar = [float(a) for a in (t.get("adimlar") or [])]
        p = float(t.get("guc_yogunlugu") or 0.0)
        if adimlar and p > 0:
            if (t.get("adim_birimi") or "d") == "d":
                gun = sum(adimlar)
                bu = _tk.yanma(gun, p)
            else:
                bu = sum(adimlar)
                gun = bu * 1000.0 / p
            self.adim_ozet.setText(
                "%d adim  |  toplam %.4g gun = %.4g MWd/kg  |  %d transport cozumu"
                % (len(adimlar), gun, bu, _tk.transport_sayisi(self.spec)))
        else:
            self.adim_ozet.setText("adim yok")

        # --- yanabilir malzemeler ---
        try:
            hv = _tk.hacimler(self.spec)
            if not hv:
                self.malzeme_bilgi.setText("Yanabilir (fisil) malzeme bulunamadi.")
            else:
                satirlar = []
                for ad, v in hv.items():
                    satirlar.append("%s: %s  [%s]\n    %s"
                                    % (ad, ("%.6g cm3" % v["hacim"]) if v["hacim"] else "HACIM YOK",
                                       v["yontem"], v["ayrinti"]))
                self.malzeme_bilgi.setText("\n".join(satirlar))
        except Exception as e:
            self.malzeme_bilgi.setText("hesaplanamadi: %s" % e)
        self._onceki_durum_guncelle()
        self.kapi_guncelle()

    # ==================================================================
    # kosu
    # ==================================================================
    def kapi_ayarla(self, fonksiyon):
        self._kapi = fonksiyon

    def proje_ayarla(self, proje_yolu):
        self.proje_yolu = proje_yolu

    def kapi_guncelle(self):
        if self._surec is not None:
            return
        if not (self.spec or {}).get("tukenme", {}).get("var"):
            izin, mesaj = False, "Tukenme kapali -- yukaridan etkinlestirin."
        else:
            izin, mesaj = self._kapi()
        self.d_baslat.setEnabled(izin)
        self.kapi_etiket.setStyleSheet("color: %s;" % ("palette(mid)" if izin else "#c0392b"))
        self.kapi_etiket.setText(mesaj)

    def baslat(self):
        izin, mesaj = self._kapi()
        if not izin or not self.spec.get("tukenme", {}).get("var"):
            QtWidgets.QMessageBox.warning(self, "Baslatilamaz", mesaj)
            return
        dizin = _tk.kosu_dizini(self.spec, self.proje_yolu)
        os.makedirs(dizin, exist_ok=True)
        eski = os.path.join(dizin, "depletion_results.h5")
        if os.path.exists(eski):
            os.remove(eski)
        # Kaydedilmemis degisiklikler de kosulsun: spec kosu dizinine yazilir.
        spec_yolu = os.path.join(dizin, "tukenme_spec.json")
        with open(spec_yolu, "w", encoding="utf-8") as f:
            json.dump(self.spec, f, indent=2, ensure_ascii=False)
        self._dizin = dizin

        self.log.clear()
        self.onceki_etiket.setText("")
        self._onceki = self._onceki_anahtar = None
        self._tampon = ""
        self._transport = 0
        self._t0 = time.time()
        self._t_ilk = None
        toplam = _tk.transport_sayisi(self.spec)
        self.ilerleme.setRange(0, toplam)
        self.ilerleme.setValue(0)
        self.ilerleme.setFormat("%v / %m transport")
        self.sure_etiket.setText("ilk transport bekleniyor -- kalan sure ondan olculecek")
        self.alt.setCurrentWidget(self.log)
        self._grafik_bos()

        n = (self.spec.get("calistirma") or {}).get("is_parcacigi", 8)
        self._surec = QtCore.QProcess(self)
        self._surec.setWorkingDirectory(KOK)
        ortam = QtCore.QProcessEnvironment.systemEnvironment()
        ortam.insert("PYTHONPATH", KOK)
        ortam.insert("PYTHONUNBUFFERED", "1")
        self._surec.setProcessEnvironment(ortam)
        self._surec.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self._surec.readyReadStandardOutput.connect(self._cikti_oku)
        self._surec.finished.connect(self._bitti)
        arg = ["-m", "cekirdek.tukenme", spec_yolu, "-s", str(int(n)), "--dizin", dizin]
        self.log.appendPlainText("# %s %s\n" % (sys.executable, " ".join(arg)))
        self._surec.start(sys.executable, arg)
        self.d_baslat.setEnabled(False)
        self.d_durdur.setEnabled(True)
        self.durum.emit("Tukenme basladi -> %s" % dizin, True)

    def durdur(self):
        if self._surec is not None:
            self._surec.kill()
            self.log.appendPlainText("\n# kullanici tarafindan durduruldu")

    def _cikti_oku(self):
        ham = bytes(self._surec.readAllStandardOutput()).decode("utf-8", "replace")
        self._tampon += ham
        while "\n" in self._tampon:
            satir, self._tampon = self._tampon.split("\n", 1)
            satir = satir.rstrip()
            # transport ciktisi cok uzun; yalnizca anlamli satirlar loga
            # Bizim terminal satirlarimiz TAM 2 bosluk girintili; OpenMC'nin
            # cevrim satirlari cok daha derin girintili ve logu bogar.
            bizim = satir.startswith("  ") and not satir.startswith("   ")
            if (satir.startswith("[openmc.deplete]") or bizim
                    or "Combined k-effective" in satir or "TUKENME" in satir
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
                    "gecen %s  |  transport basina %.0f s (olculen)  |  kalan ~%s"
                    % (_sure(gecen), gecen / self._transport, _sure(kalan)))

    def _bitti(self, cikis_kodu, _durum):
        self._surec = None
        self.d_durdur.setEnabled(False)
        self.kapi_guncelle()
        h5 = os.path.join(self._dizin or "", "depletion_results.h5")
        if cikis_kodu != 0 or not os.path.exists(h5):
            self.durum.emit("Tukenme basarisiz (cikis kodu %d)" % cikis_kodu, False)
            self.sure_etiket.setText("BASARISIZ -- 'Kosu ciktisi' sekmesine bakin")
            return
        try:
            s = _tk.sonuc_oku(h5, self.spec)
        except Exception as e:
            self.durum.emit("Sonuc okunamadi: %s" % e, False)
            return
        self._sonuc_goster(s)
        self.sure_etiket.setText("tamamlandi: %s" % _sure(time.time() - self._t0))
        self.durum.emit("Tukenme tamamlandi", True)

    # ==================================================================
    # onceki kosu
    # ==================================================================
    def _onceki_yukle(self):
        """
        Dizinde bir sonuc varsa gosterir. Dosya degismediyse tekrar okumaz:
        sekme her tazelendiginde 3.7 MB'lik sonucu okumak gereksiz.
        """
        if self._surec is not None or not self.spec:
            return
        dizin = _tk.kosu_dizini(self.spec, self.proje_yolu)
        h5 = os.path.join(dizin, "depletion_results.h5")
        if not os.path.exists(h5):
            self._onceki = self._onceki_anahtar = None
            self.onceki_etiket.setText("")
            self._grafik_bos()
            self.tablo.setRowCount(0)
            return
        anahtar = (h5, os.path.getmtime(h5))
        if anahtar == self._onceki_anahtar:
            self._onceki_durum_guncelle()
            return
        if self._isci is not None and self._isci.isRunning():
            return                              # zaten okunuyor
        self.onceki_etiket.setStyleSheet("")
        self.onceki_etiket.setText("Onceki kosunun sonucu okunuyor...")
        self._isci = _OncekiIsci(self.spec, dizin, anahtar, self)
        self._isci.bitti.connect(self._onceki_geldi)
        # Pencere disi bir cikis yolunda da (or. uygulama kapanirken) calisan
        # is parcacigi yok edilmesin -- Qt bu durumda sureci dusurur.
        uyg = QtWidgets.QApplication.instance()
        if uyg is not None and not getattr(self, "_cikis_bagli", False):
            uyg.aboutToQuit.connect(self.bekle)
            self._cikis_bagli = True
        self._isci.start()

    def _onceki_geldi(self, anahtar, sonuc):
        if self._surec is not None:
            return                              # bu arada yeni kosu basladi
        if isinstance(sonuc, Exception):
            self._onceki = None
            self.onceki_etiket.setText("Onceki sonuc okunamadi: %s" % sonuc)
            return
        if sonuc is None:
            return
        self._onceki, self._onceki_anahtar = sonuc, anahtar
        self._sonuc_goster(sonuc["sonuc"])
        self._onceki_durum_guncelle()

    def bekle(self, ms=30000):
        """Arka plandaki okuma bitene kadar bekler (testler ve kapanis icin)."""
        if self._isci is not None:
            self._isci.wait(ms)
            QtWidgets.QApplication.processEvents()

    def _onceki_durum_guncelle(self):
        """Gosterilen sonucun SU ANKI spec'e ait olup olmadigini yazar."""
        if not self._onceki or self._surec is not None:
            return
        dizin = os.path.dirname(self._onceki["h5"])
        durum, farklar = _tk.eskime(self.spec, dizin)
        tarih = time.strftime("%d.%m.%Y %H:%M", time.localtime(self._onceki["tarih"]))
        if durum == "guncel":
            metin = "Onceki kosunun sonucu (%s) -- bu modele AIT." % tarih
            stil = ""
        elif durum == "eski":
            metin = ("ESKI SONUC (%s): model o kosudan beri degisti (%s). "
                     "Gosterilen sayilar bu modele ait DEGIL -- yeniden kosun."
                     % (tarih, ", ".join(farklar)))
            stil = "color: #d04437; font-weight: bold;"
        else:
            metin = ("Onceki kosunun sonucu (%s). Kosunun spec kaydi yok; bu modele "
                     "ait oldugu DOGRULANAMIYOR." % tarih)
            stil = "color: #c9820a;"
        self.onceki_etiket.setText(metin)
        self.onceki_etiket.setStyleSheet(stil)

    # ==================================================================
    # sonuclar
    # ==================================================================
    def _grafik_bos(self):
        for e, y in ((self.eksen_k, "k-eff"), (self.eksen_n, "atom/b-cm")):
            e.clear(); e.grid(alpha=0.3)
            e.set_ylabel(y, fontsize=8); e.tick_params(labelsize=7)
        self.eksen_n.set_xlabel("yanma [MWd/kg]", fontsize=8)
        self.tuval.draw_idle()

    def _sonuc_goster(self, s):
        from arayuz import tema as _t
        bu, k, sk = s["yanma"], s["k"], s["k_sapma"]
        self._grafik_bos()
        self.eksen_k.errorbar(bu, k, yerr=sk, fmt="o-", ms=3, lw=1.2,
                              color=_t.renk("vurgu"), capsize=2)
        self.eksen_k.axhline(1.0, color=_t.renk("metin_soluk"), lw=0.8, ls="--")
        for ad, yog in s["yogunluk"].items():
            for n, v in yog.items():
                if any(x > 0 for x in v):
                    xs = [b for b, x in zip(bu, v) if x > 0]
                    ys = [x for x in v if x > 0]
                    self.eksen_n.plot(xs, ys, "o-", ms=2, lw=1.0,
                                      label=n if len(s["yogunluk"]) == 1 else "%s (%s)" % (n, ad))
        self.eksen_n.set_yscale("log")
        self.eksen_n.legend(fontsize=6, ncol=2, loc="best")
        self.tuval.draw_idle()

        self.tablo.setRowCount(0)
        for z, b, kk, ss in zip(s["zaman_d"], bu, k, sk):
            r = self.tablo.rowCount()
            self.tablo.insertRow(r)
            rho = (kk - 1.0) / kk * 1e5
            for c, metin in enumerate(("%.3f" % z, "%.4f" % b,
                                       "%.5f +/- %.5f" % (kk, ss), "%+.0f" % rho)):
                self.tablo.setItem(r, c, QtWidgets.QTableWidgetItem(metin))
        self.tablo.resizeColumnsToContents()
        self.alt.setCurrentWidget(self.tablo)


def _sure(s):
    s = int(max(s, 0))
    if s < 90:
        return "%d s" % s
    if s < 5400:
        return "%d dk" % round(s / 60.0)
    return "%.1f sa" % (s / 3600.0)
