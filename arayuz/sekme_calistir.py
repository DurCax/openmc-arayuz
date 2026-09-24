# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_calistir.py  --  Kosu, canli takip ve sonuclar
================================================================================
 openmc alt surec olarak QProcess ile calistirilir; Qt olay dongusune dogal
 entegre oldugu icin arayuz kosu boyunca donmaz.

 !!! ONCE CIZ, SONRA CALISTIR !!!
   Geometri onizlemesi basariyla uretilmeden ve dogrulama hatalari giderilmeden
   CALISTIR dugmesi etkinlesmez. Bu, elle yazilan betiklerdeki
   "plotlar dogruysa model.run() satirinin yorumunu kaldir" aliskanliginin
   arayuze gomulmus halidir -- yanlis geometriyle saatlerce kosmayi onler.
================================================================================
"""

import os

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import kosucu
from arayuz.ortak import baslik, ipucu


class CalistirSekmesi(QtWidgets.QWidget):
    """Kosuyu baslatir, ciktiyi canli gosterir, sonucu okur."""

    durum = QtCore.Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec = None
        self.proje_yolu = None
        self._kapi = lambda: (False, "hazir degil")
        self._surec = None
        self._dizin = None
        self._tampon = ""
        self._cevrimler = []
        self._son_basarili = False

        # --- ust: denetimler ---
        self.d_calistir = QtWidgets.QPushButton("CALISTIR")
        self.d_calistir.setMinimumHeight(34)
        f = self.d_calistir.font(); f.setBold(True); self.d_calistir.setFont(f)
        self.d_durdur = QtWidgets.QPushButton("Durdur")
        self.d_durdur.setEnabled(False)
        self.kapi_etiket = QtWidgets.QLabel("-")
        self.kapi_etiket.setWordWrap(True)
        self.ilerleme = QtWidgets.QProgressBar()
        self.ilerleme.setTextVisible(True)

        self.d_calistir.clicked.connect(self.calistir)
        self.d_durdur.clicked.connect(self.durdur)

        ust = QtWidgets.QHBoxLayout()
        ust.addWidget(self.d_calistir)
        ust.addWidget(self.d_durdur)
        ust.addWidget(self.ilerleme, 1)

        # --- yakinsama grafigi ---
        # Ust: k-eff yakinsamasi, alt: Shannon entropisi (kaynak yakinsamasi)
        self.figur = Figure(figsize=(5, 2.8), tight_layout=True)
        self.tuval = FigureCanvasQTAgg(self.figur)
        self.eksen = self.figur.add_subplot(211)
        self.eksen_ent = self.figur.add_subplot(212, sharex=self.eksen)
        self._grafik_sifirla()

        # --- log ---
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        lf = self.log.font(); lf.setFamily("monospace"); lf.setPointSizeF(8.5)
        self.log.setFont(lf)
        self.log.setMaximumBlockCount(5000)

        # --- sonuclar ---
        self.keff_etiket = QtWidgets.QLabel("-")
        kf = self.keff_etiket.font(); kf.setPointSizeF(kf.pointSizeF() + 4); kf.setBold(True)
        self.keff_etiket.setFont(kf)
        self.sonuc_metin = QtWidgets.QPlainTextEdit()
        self.sonuc_metin.setReadOnly(True)
        self.sonuc_metin.setFont(lf)

        sonuc = QtWidgets.QWidget()
        sd = QtWidgets.QVBoxLayout(sonuc)
        sd.setContentsMargins(0, 0, 0, 0)
        self.durum_etiket = QtWidgets.QLabel("")
        self.durum_etiket.setWordWrap(True)
        kutu = QtWidgets.QHBoxLayout()
        kutu.addWidget(QtWidgets.QLabel("k-eff:"))
        kutu.addWidget(self.keff_etiket)
        kutu.addStretch(1)
        sd.addLayout(kutu)
        sd.addWidget(self.durum_etiket)
        sd.addWidget(self.sonuc_metin, 1)

        from arayuz.guc_harita import GucHaritaWidget
        self.guc_harita = GucHaritaWidget()

        alt_sekme = QtWidgets.QTabWidget()
        alt_sekme.addTab(self.log, "Kosu ciktisi")
        alt_sekme.addTab(sonuc, "Sonuclar")
        alt_sekme.addTab(self.guc_harita, "Guc haritasi")
        self.alt_sekme = alt_sekme

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(baslik("Kosu"))
        duzen.addWidget(self.kapi_etiket)
        duzen.addLayout(ust)
        duzen.addWidget(self.tuval)
        duzen.addWidget(alt_sekme, 1)

    # ------------------------------------------------------------------
    def kapi_ayarla(self, fonksiyon):
        """fonksiyon() -> (izin_var_mi, aciklama)"""
        self._kapi = fonksiyon

    def spec_ayarla(self, spec, proje_yolu=None):
        self.spec = spec
        self.proje_yolu = proje_yolu
        self.kapi_guncelle()

    def kapi_guncelle(self):
        if self._surec is not None:
            return
        izin, mesaj = self._kapi()
        self.d_calistir.setEnabled(izin)
        renk = "palette(mid)" if izin else "#c0392b"
        self.kapi_etiket.setStyleSheet("color: %s;" % renk)
        self.kapi_etiket.setText(mesaj)

    # ------------------------------------------------------------------
    def _grafik_sifirla(self):
        for eks, etiket in ((self.eksen, "k-eff"), (self.eksen_ent, "Shannon entropisi")):
            eks.clear()
            eks.set_ylabel(etiket, fontsize=8)
            eks.tick_params(labelsize=7)
            eks.grid(alpha=0.3)
        self.eksen_ent.set_xlabel("cevrim", fontsize=8)
        self.tuval.draw_idle()

    def _grafik_guncelle(self):
        if not self._cevrimler:
            return
        from arayuz import tema as _t
        self.eksen.clear()
        self.eksen.grid(alpha=0.3)
        pasif = self.spec["ayarlar"].get("pasif", 0)
        x = [c["cevrim"] for c in self._cevrimler]
        y = [c["k"] for c in self._cevrimler]
        self.eksen.plot(x, y, lw=0.8, color=_t.renk("metin_soluk"), label="cevrim k")
        ort = [(c["cevrim"], c["ortalama"], c["sapma"])
               for c in self._cevrimler if c["ortalama"] is not None]
        if ort:
            ox = [a for a, _, _ in ort]
            oy = [b for _, b, _ in ort]
            os_ = [c for _, _, c in ort]
            self.eksen.plot(ox, oy, lw=1.6, color=_t.renk("vurgu"), label="kumulatif ortalama")
            self.eksen.fill_between(ox, [a - b for a, b in zip(oy, os_)],
                                    [a + b for a, b in zip(oy, os_)],
                                    color=_t.renk("vurgu"), alpha=0.18)
        if pasif:
            self.eksen.axvline(pasif, color=_t.renk("hata"), ls="--", lw=1.0)
            self.eksen.text(pasif, self.eksen.get_ylim()[1], " pasif biter",
                            color=_t.renk("hata"), fontsize=7, va="top")
        self.eksen.set_ylabel("k-eff", fontsize=8)
        self.eksen.tick_params(labelsize=7)
        self.eksen.legend(fontsize=7, loc="best")

        # --- entropi grafigi ---
        self.eksen_ent.clear()
        self.eksen_ent.grid(alpha=0.3)
        ent = [(c["cevrim"], c["entropi"]) for c in self._cevrimler
               if c.get("entropi") is not None]
        if ent:
            ex = [a for a, _ in ent]
            ey = [b for _, b in ent]
            self.eksen_ent.plot(ex, ey, lw=1.0, color=_t.renk("vurgu"))
            if pasif:
                self.eksen_ent.axvline(pasif, color=_t.renk("hata"), ls="--", lw=1.0)
        else:
            self.eksen_ent.text(0.5, 0.5, "Shannon entropisi kapali",
                                transform=self.eksen_ent.transAxes,
                                ha="center", va="center", fontsize=8,
                                color=_t.renk("metin_soluk"))
        self.eksen_ent.set_ylabel("Shannon entropisi", fontsize=8)
        self.eksen_ent.set_xlabel("cevrim", fontsize=8)
        self.eksen_ent.tick_params(labelsize=7)
        self.tuval.draw_idle()

    # ------------------------------------------------------------------
    def calistir(self):
        izin, mesaj = self._kapi()
        if not izin:
            QtWidgets.QMessageBox.warning(self, "Calistirilamaz", mesaj)
            return

        taban = os.path.dirname(self.proje_yolu) if self.proje_yolu else os.getcwd()
        dizin = self.spec["calistirma"].get("dizin", "kosu")
        if not os.path.isabs(dizin):
            dizin = os.path.join(taban, dizin)
        self._dizin = dizin

        try:
            kosucu.dizin_hazirla(dizin, temizle=True)
            kosucu.xml_yaz(self.spec, dizin)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Model kurulamadi", str(e))
            return

        exe = kosucu.openmc_yolu()
        if exe is None:
            QtWidgets.QMessageBox.critical(
                self, "openmc bulunamadi",
                "openmc calistirilabilir dosyasi PATH'te yok.\n"
                "Conda ortaminin aktif oldugundan emin olun (openmc-env).")
            return

        self.log.clear()
        self.sonuc_metin.clear()
        self.keff_etiket.setText("kosuyor...")
        self.durum_etiket.setText("")
        self._cevrimler = []
        self._tampon = ""
        self._grafik_sifirla()
        self.alt_sekme.setCurrentIndex(0)

        toplam = self.spec["ayarlar"].get("cevrim", 1)
        self.ilerleme.setRange(0, toplam)
        self.ilerleme.setValue(0)
        self.ilerleme.setFormat("%v / %m cevrim")

        n = self.spec["calistirma"].get("is_parcacigi", 8)
        self._surec = QtCore.QProcess(self)
        self._surec.setWorkingDirectory(dizin)
        self._surec.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self._surec.readyReadStandardOutput.connect(self._cikti_oku)
        self._surec.finished.connect(self._bitti)
        self._surec.errorOccurred.connect(self._hata)

        self._yaz("# komut: %s -s %d" % (exe, n))
        self._yaz("# dizin: %s\n" % dizin)
        self._surec.start(exe, ["-s", str(int(n))])

        self.d_calistir.setEnabled(False)
        self.d_durdur.setEnabled(True)
        self.durum.emit("Kosu basladi -> %s" % dizin, True)

    def durdur(self):
        if self._surec is not None:
            self._surec.kill()
            self._yaz("\n# kullanici tarafindan durduruldu")

    # ------------------------------------------------------------------
    def _yaz(self, metin):
        self.log.appendPlainText(metin)

    def _cikti_oku(self):
        ham = bytes(self._surec.readAllStandardOutput()).decode("utf-8", "replace")
        self._tampon += ham
        while "\n" in self._tampon:
            satir, self._tampon = self._tampon.split("\n", 1)
            satir = satir.rstrip()
            self._yaz(satir)
            bilgi = kosucu.cevrim_satiri(satir)
            if bilgi:
                self._cevrimler.append(bilgi)
                self.ilerleme.setValue(bilgi["cevrim"])
                if len(self._cevrimler) % 5 == 0:
                    self._grafik_guncelle()
                if bilgi["ortalama"] is not None:
                    self.keff_etiket.setText("%.5f +/- %.5f"
                                             % (bilgi["ortalama"], bilgi["sapma"]))

    def _hata(self, _kod):
        self._yaz("\n# SUREC HATASI: %s" % self._surec.errorString())

    def _bitti(self, cikis_kodu, _durum):
        self._grafik_guncelle()
        surec, self._surec = self._surec, None
        self.d_durdur.setEnabled(False)
        self.kapi_guncelle()

        if cikis_kodu != 0:
            self.keff_etiket.setText("basarisiz")
            self.durum.emit("Kosu basarisiz (cikis kodu %d)" % cikis_kodu, False)
            return

        sp = kosucu.son_statepoint(self._dizin)
        if sp is None:
            self.keff_etiket.setText("statepoint yok")
            self.durum.emit("Kosu bitti ama statepoint bulunamadi", False)
            return
        try:
            s = kosucu.sonuc_oku(sp)
        except Exception as e:
            self.durum.emit("Sonuc okunamadi: %s" % e, False)
            return

        self.keff_etiket.setText("%.5f +/- %.5f" % s["keff"])
        kin0 = s.get("kinetik") or {}
        durum, ayrinti = kosucu.keff_yorumu(s["keff"][0], s["keff"][1],
                                            kin0.get("beta_eff"))
        self.durum_etiket.setText("%s\n%s" % (durum, ayrinti))
        from arayuz import tema
        renk = (tema.renk("basari") if durum.startswith("KRITIK (")
                else (tema.renk("hata") if "USTU" in durum else tema.renk("vurgu")))
        self.durum_etiket.setStyleSheet("color: %s; font-weight: bold;" % renk)
        satirlar = [
            "k-eff    = %.5f +/- %.5f" % s["keff"],
            "cevrim   = %d (%d pasif)" % (s["cevrim"], s["pasif"]),
            "parcacik = %d / cevrim" % s["parcacik"],
        ]
        # --- kaynak yakinsamasi degerlendirmesi ---
        if s.get("entropi"):
            yakinsadi, mesaj = kosucu.entropi_yakinsama(s["entropi"], s["pasif"])
            isaret = {True: "[OK]   ", False: "[UYARI]", None: "[  ?  ]"}[yakinsadi]
            satirlar.append("kaynak   = %s %s" % (isaret, mesaj))
            if yakinsadi is False:
                self.durum.emit("DIKKAT: kaynak yakinsamamis olabilir -- "
                                "pasif cevrim sayisini artirin", False)
        else:
            satirlar.append("kaynak   = [  ?  ] Shannon entropisi kapali -- "
                            "kaynak yakinsamasi dogrulanamiyor")
        kin = s.get("kinetik")
        if kin:
            satirlar.append("beta_eff = %.1f +/- %.1f pcm   (reaktivite birimi: 1 $ = beta_eff)"
                            % (kin["beta_eff"] * 1e5, kin["beta_eff_sapma"] * 1e5))
            satirlar.append("Lambda   = %-22s (notron uretim zamani)"
                            % kosucu.lambda_metni(kin["lambda"], kin["lambda_sapma"]))
        g = s.get("guc") or {}
        gf = g.get("faktorler")
        if gf:
            satirlar.append("F_dH     = %.4f   (maks cubuk gucu / ortalama)" % gf["F_dH"])
            if gf["F_q"]:
                satirlar.append("F_q      = %.4f   (maks yerel guc yogunlugu / ortalama)"
                                % gf["F_q"])
            else:
                satirlar.append("F_q      = tanimsiz (model 2B)")
            satirlar.append("sicak cubuk %s%s"
                            % (gf["sicak_cubuk"],
                               (", dilim %d" % (gf["sicak_dilim"][1] + 1))
                               if gf["sicak_dilim"] else ""))
            if "korunum" in g:
                satirlar.append("toplam korunumu: bagil fark %.1e %s"
                                % (g["korunum"],
                                   "OK" if g["korunum"] < 1e-6 else "!!! BOZUK !!!"))
        elif s.get("guc_hata"):
            satirlar.append("guc dagilimi okunamadi: %s" % s["guc_hata"])
        satirlar += ["statepoint: %s" % sp, ""]
        for ad, df in s["tallyler"].items():
            satirlar.append("=" * 70)
            satirlar.append("tally: %s" % ad)
            satirlar.append("=" * 70)
            satirlar.append(str(df))
            satirlar.append("")
        self.sonuc_metin.setPlainText("\n".join(satirlar))
        self.guc_harita.sonuc_ayarla(s, self.spec)
        self._son_basarili = True
        self.alt_sekme.setCurrentIndex(1)
        self.durum.emit("Kosu tamamlandi: k-eff = %.5f +/- %.5f" % s["keff"], True)
