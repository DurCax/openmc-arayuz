# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_analiz.py  --  Parametre taramasi ve kritik arama
================================================================================
 Tek bir k-eff sayisindan reaktor fizigine gecilen yer burasi:

   TARAMA        bir parametreyi aralikta degistirir, k(p) egrisini cikarir ve
                 egimden REAKTIVITE KATSAYISINI hesaplar.
                 (Doppler, moderator sicaklik, void, bor degeri, ...)

   KRITIK ARAMA  hedef k-eff'i (genellikle 1.0) veren parametre degerini bulur.
                 (kritik bor konsantrasyonu, kritik yukseklik, ...)

 Her nokta ayri bir OpenMC kosusudur; is arka planda bir QThread'de yurutulur,
 arayuz donmaz ve istenildigi an durdurulabilir.
================================================================================
"""

import os
import tempfile

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import kritik_arama, sema, tarama
from arayuz.ortak import ayrac, baslik, ipucu, sayi, tamsayi


class TaramaIsci(QtCore.QThread):
    """Taramayi arka planda yurutur."""

    nokta = QtCore.Signal(int, int, dict)
    bitti = QtCore.Signal(list, list)
    hata = QtCore.Signal(str)

    def __init__(self, spec, tur, hedef, degerler, dizin, is_parcacigi, parent=None):
        super().__init__(parent)
        self.spec, self.tur, self.hedef = spec, tur, hedef
        self.degerler, self.dizin, self.is_parcacigi = degerler, dizin, is_parcacigi
        self._dur = False

    def durdur(self):
        self._dur = True

    def run(self):
        try:
            sonuclar, notlar = tarama.calistir(
                self.spec, self.tur, self.hedef, self.degerler, self.dizin,
                geri_cagir=lambda i, n, s: self.nokta.emit(i, n, s),
                is_parcacigi=self.is_parcacigi,
                dur_bayragi=lambda: self._dur)
            self.bitti.emit(sonuclar, notlar)
        except Exception as e:
            self.hata.emit(str(e))


class AramaIsci(QtCore.QThread):
    """Kritik aramayi arka planda yurutur."""

    adim = QtCore.Signal(int, dict)
    bitti = QtCore.Signal(object)
    hata = QtCore.Signal(str)

    def __init__(self, spec, tur, hedef, alt, ust, hedef_keff, dizin,
                 is_parcacigi, parent=None):
        super().__init__(parent)
        self.spec, self.tur, self.hedef = spec, tur, hedef
        self.alt, self.ust, self.hedef_keff = alt, ust, hedef_keff
        self.dizin, self.is_parcacigi = dizin, is_parcacigi
        self._dur = False

    def durdur(self):
        self._dur = True

    def run(self):
        try:
            s = kritik_arama.ara(
                self.spec, self.tur, self.hedef, self.alt, self.ust, self.dizin,
                hedef_keff=self.hedef_keff, is_parcacigi=self.is_parcacigi,
                geri_cagir=lambda i, k: self.adim.emit(i, k),
                dur_bayragi=lambda: self._dur)
            self.bitti.emit(s)
        except Exception as e:
            self.hata.emit(str(e))


class AnalizSekmesi(QtWidgets.QWidget):

    durum = QtCore.Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec = None
        self.proje_yolu = None
        self._kapi = lambda: (False, "hazir degil")
        self._isci = None
        self._sonuclar = []

        # ---------------- mod ve parametre ----------------
        self.mod = QtWidgets.QComboBox()
        self.mod.addItem("Parametre taramasi (reaktivite katsayisi)", "tarama")
        self.mod.addItem("Kritik arama (hedef k-eff'i veren deger)", "arama")
        self.mod.currentIndexChanged.connect(self._mod_degisti)

        self.tur = QtWidgets.QComboBox()
        # En yaygin analizler basta: once Doppler, sonra moderator, void, bor.
        # Alfabetik sira "Al-..." gibi ilgisiz bir parametreyi basa koyuyordu.
        ONCELIK = ["yakit_sicaklik", "sogutucu_sicaklik", "void_orani", "bor_ppm",
                   "zenginlik", "kafes_adim"]
        sirali = ([a for a in ONCELIK if a in tarama.TURLER]
                  + [a for a in sorted(tarama.TURLER) if a not in ONCELIK])
        for ad in sirali:
            aciklama, _h, birim, _k = tarama.TURLER[ad]
            self.tur.addItem("%s  [%s]" % (aciklama, birim), ad)
        self.tur.currentIndexChanged.connect(self._tur_degisti)

        self.hedef = QtWidgets.QComboBox()
        self.hedef_etiket = QtWidgets.QLabel("Hedef:")

        self.bas = sayi(600.0, 4, -1e6, 1e6, 10.0)
        self.son = sayi(1200.0, 4, -1e6, 1e6, 10.0)
        self.adet = tamsayi(5, 2, 50, 1, "nokta")
        self.hedef_keff = sayi(1.0, 5, 0.0001, 10.0, 0.01)

        self.e_adet = QtWidgets.QLabel("Nokta sayisi:")
        self.e_hedef_keff = QtWidgets.QLabel("Hedef k-eff:")
        self.e_bas = QtWidgets.QLabel("Baslangic:")
        self.e_son = QtWidgets.QLabel("Bitis:")

        self.birim_etiket = QtWidgets.QLabel("")
        self.tahmin_etiket = QtWidgets.QLabel("")

        form = QtWidgets.QFormLayout()
        form.addRow("Ne yapilacak:", self.mod)
        form.addRow("Parametre:", self.tur)
        form.addRow(self.hedef_etiket, self.hedef)
        form.addRow(self.e_bas, self.bas)
        form.addRow(self.e_son, self.son)
        form.addRow(self.e_adet, self.adet)
        form.addRow(self.e_hedef_keff, self.hedef_keff)
        form.addRow("Birim:", self.birim_etiket)
        form.addRow("Tahmini sure:", self.tahmin_etiket)

        for w in (self.bas, self.son, self.hedef_keff):
            w.valueChanged.connect(self._tahmin_guncelle)
        self.adet.valueChanged.connect(self._tahmin_guncelle)

        # ---------------- calistirma ----------------
        self.d_basla = QtWidgets.QPushButton("ANALIZI BASLAT")
        self.d_basla.setMinimumHeight(32)
        f = self.d_basla.font(); f.setBold(True); self.d_basla.setFont(f)
        self.d_dur = QtWidgets.QPushButton("Durdur")
        self.d_dur.setEnabled(False)
        self.d_basla.clicked.connect(self._basla)
        self.d_dur.clicked.connect(self._durdur)
        self.ilerleme = QtWidgets.QProgressBar()
        self.kapi_etiket = QtWidgets.QLabel("-")
        self.kapi_etiket.setWordWrap(True)

        dugme = QtWidgets.QHBoxLayout()
        dugme.addWidget(self.d_basla)
        dugme.addWidget(self.d_dur)
        dugme.addWidget(self.ilerleme, 1)

        # ---------------- sonuc ----------------
        self.tablo = QtWidgets.QTableWidget(0, 4)
        self.tablo.setHorizontalHeaderLabels(["Deger", "k-eff", "+/-", "rho [pcm]"])
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setMaximumHeight(140)

        self.figur = Figure(figsize=(5, 2.4), tight_layout=True)
        self.tuval = FigureCanvasQTAgg(self.figur)
        self.eksen = self.figur.add_subplot(111)
        self._grafik_sifirla()

        self.sonuc_kutusu = QtWidgets.QLabel("Henuz analiz yapilmadi.")
        self.sonuc_kutusu.setWordWrap(True)
        self.sonuc_kutusu.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.sonuc_kutusu.setTextFormat(QtCore.Qt.RichText)
        self.sonuc_kutusu.setStyleSheet(
            "background: palette(alternate-base); padding: 10px; "
            "border: 1px solid palette(mid); border-radius: 8px;")
        sf = self.sonuc_kutusu.font(); sf.setPointSizeF(sf.pointSizeF() + 1)
        self.sonuc_kutusu.setFont(sf)

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(baslik("Reaktor fizigi analizi"))
        duzen.addWidget(ipucu(
            "Bir k-eff sayisi tek basina bir sey soylemez. Reaktivite katsayilari "
            "(Doppler, moderator sicaklik, void, bor degeri) bir tasarimin guvenli "
            "olup olmadigini belirleyen buyukluklerdir. Burada bir parametreyi "
            "tarayip egimden bu katsayilari cikarirsiniz. Her nokta ayri bir "
            "OpenMC kosusudur -- sure, nokta sayisi x tek kosu suresi kadardir."))
        duzen.addLayout(form)
        duzen.addWidget(self.kapi_etiket)
        duzen.addLayout(dugme)
        duzen.addWidget(ayrac())
        duzen.addWidget(self.sonuc_kutusu)
        duzen.addWidget(self.tuval, 1)
        duzen.addWidget(self.tablo)

        self._mod_degisti()
        # Birim etiketi ve varsayilan aralik acilista da dolsun
        # (once yalnizca kullanici parametre degistirince doluyordu).
        self._tur_degisti()

    # ==================================================================
    def kapi_ayarla(self, fonksiyon):
        self._kapi = fonksiyon

    def spec_ayarla(self, spec, proje_yolu=None):
        self.spec = spec
        self.proje_yolu = proje_yolu
        self._hedefleri_doldur()
        self.kapi_guncelle()
        self._tahmin_guncelle()

    def kapi_guncelle(self):
        if self._isci is not None:
            return
        izin, mesaj = self._kapi()
        self.d_basla.setEnabled(izin)
        self.kapi_etiket.setStyleSheet("color: %s;" % ("palette(mid)" if izin else "#c0392b"))
        self.kapi_etiket.setText(mesaj)

    # ==================================================================
    def _mod_degisti(self, *_):
        arama = self.mod.currentData() == "arama"
        for w in (self.e_adet, self.adet):
            w.setVisible(not arama)
        for w in (self.e_hedef_keff, self.hedef_keff):
            w.setVisible(arama)
        self.e_bas.setText("Alt sinir:" if arama else "Baslangic:")
        self.e_son.setText("Ust sinir:" if arama else "Bitis:")
        self.d_basla.setText("KRITIK ARAMAYI BASLAT" if arama else "TARAMAYI BASLAT")
        self._tahmin_guncelle()

    def _tur_degisti(self, *_):
        self._hedefleri_doldur()
        tur = self.tur.currentData()
        if tur in tarama.TURLER:
            self.birim_etiket.setText(
                "%s   ->   katsayi birimi: %s"
                % (tarama.TURLER[tur][2], tarama.TURLER[tur][3]))
        # makul varsayilan araliklar
        varsayilan = {
            "yakit_sicaklik": (600, 1200, 5), "sogutucu_sicaklik": (540, 620, 5),
            "void_orani": (0, 50, 5), "bor_ppm": (0, 2000, 5),
            "zenginlik": (2.0, 5.0, 5), "kafes_adim": (1.1, 1.5, 5),
            "malzeme_yogunluk": (0.4, 0.8, 5), "kor_adim": (1.1, 1.5, 5),
            "cubuk_yaricap": (0.35, 0.45, 5), "yansitici_kalinlik": (5, 40, 5),
            "cubuk_daldirma": (0, 100, 6),
            "tambur_donme": (0, 180, 5),
        }
        if tur in varsayilan:
            a, b, n = varsayilan[tur]
            self.bas.setValue(a); self.son.setValue(b); self.adet.setValue(n)
        self._tahmin_guncelle()

    def _hedefleri_doldur(self):
        """Parametre turune gore secilebilir hedefleri listeler."""
        self.hedef.clear()
        if self.spec is None:
            return
        tur = self.tur.currentData()
        hedef_turu = tarama.TURLER.get(tur, (None, None, None, None))[1]
        if hedef_turu == "malzeme":
            for m in self.spec["malzemeler"]:
                self.hedef.addItem("%s  --  %s" % (m["ad"], m.get("gorunen_ad") or ""),
                                   m["ad"])
            self.hedef_etiket.setText("Hedef malzeme:")
        elif hedef_turu == "demet":
            for d in self.spec.get("demetler", []):
                self.hedef.addItem(d["ad"], d["ad"])
            self.hedef_etiket.setText("Hedef kafes:")
        elif hedef_turu == "kontrol_cubugu":
            for c in self.spec.get("cubuklar", []):
                if c.get("tur") == "kontrol":
                    self.hedef.addItem("%s  (su an %%%.1f)"
                                       % (c["ad"], c.get("daldirma") or 0.0), c["ad"])
            self.hedef_etiket.setText("Kontrol cubugu:")
        elif hedef_turu == "cubuk_bolge":
            for c in self.spec.get("cubuklar", []):
                for i, b in enumerate(c["bolgeler"][:-1]):
                    self.hedef.addItem("%s -- bolge %d (r=%.4f, %s)"
                                       % (c["ad"], i + 1, b["r"], b["malzeme"]),
                                       (c["ad"], i))
            self.hedef_etiket.setText("Hedef bolge:")
        else:
            self.hedef.addItem("(kor ayari)", None)
            self.hedef_etiket.setText("Hedef:")
        self.hedef.setEnabled(self.hedef.count() > 1 or hedef_turu != "kor")

    # Kosu hizi kalibrasyonu [parcacik/saniye]. Baslangic degeri bu makinede
    # olculmus bir ortalamadir; ilk nokta bitince GERCEK olcume guncellenir,
    # boylece tahmin kendi kendini duzeltir. (Ilk surumde sabit bir formul
    # kullaniliyordu ve 44 saniyelik bir taramaya "6 saniye" diyordu.)
    _HIZ = 33000.0

    def _sure_metni(self, saniye):
        if saniye < 90:
            return "%.0f sn" % saniye
        if saniye < 5400:
            return "%.1f dk" % (saniye / 60.0)
        return "%.1f saat" % (saniye / 3600.0)

    def _tek_kosu_tahmini(self):
        a = self.spec["ayarlar"]
        n = a.get("parcacik", 10000) * a.get("cevrim", 100)
        return n / self._HIZ

    def _tahmin_guncelle(self, *_):
        if self.spec is None:
            self.tahmin_etiket.setText("-")
            return
        tek = self._tek_kosu_tahmini()
        adet = self.adet.value() if self.mod.currentData() == "tarama" else 6
        ek = "" if self.mod.currentData() == "tarama" else " (arama ~4-8 kosu surer)"
        self.tahmin_etiket.setText(
            "~%s   (%d kosu x ~%s)%s"
            % (self._sure_metni(tek * adet), adet, self._sure_metni(tek), ek))

    def _hizi_kalibre_et(self, gecen_saniye):
        """Gercek kosu suresinden parcacik/saniye hizini gunceller."""
        a = self.spec["ayarlar"]
        n = a.get("parcacik", 10000) * a.get("cevrim", 100)
        if gecen_saniye > 0.5 and n > 0:
            olculen = n / gecen_saniye
            # yumusak guncelleme -- tek bir yavas nokta tahmini bozmasin
            self._HIZ = 0.5 * self._HIZ + 0.5 * olculen

    # ==================================================================
    def _grafik_sifirla(self):
        self.eksen.clear()
        self.eksen.set_xlabel("parametre", fontsize=8)
        self.eksen.set_ylabel("k-eff", fontsize=8)
        self.eksen.tick_params(labelsize=7)
        self.eksen.grid(alpha=0.3)
        self.tuval.draw_idle()

    def _grafik_guncelle(self, kats=None):
        self.eksen.clear()
        self.eksen.grid(alpha=0.3)
        gecerli = [s for s in self._sonuclar if s.get("keff")]
        if gecerli:
            x = [s["deger"] for s in gecerli]
            y = [s["keff"] for s in gecerli]
            e = [s["sapma"] for s in gecerli]
            self.eksen.errorbar(x, y, yerr=e, fmt="o-", ms=4, lw=1.2,
                                capsize=3, color="#2c3e50")
            if self.mod.currentData() == "arama":
                self.eksen.axhline(self.hedef_keff.value(), color="#c0392b",
                                   ls="--", lw=1.0, label="hedef k")
                self.eksen.legend(fontsize=7)
            elif kats:
                # rho dogrusunu k olceginde goster: rho = 1 - 1/k -> k = 1/(1-rho)
                import numpy as np
                px = np.linspace(min(x), max(x), 50)
                rho = (kats["kesisim"] + kats["egim"] * px) / 1.0e5
                self.eksen.plot(px, 1.0 / (1.0 - rho), lw=1.0, ls="--",
                                color="#e67e22", label="dogrusal uyum")
                self.eksen.legend(fontsize=7)
        tur = self.tur.currentData()
        birim = tarama.TURLER.get(tur, ("", "", "", ""))[2]
        self.eksen.set_xlabel("%s [%s]" % (tur, birim), fontsize=8)
        self.eksen.set_ylabel("k-eff", fontsize=8)
        self.eksen.tick_params(labelsize=7)
        self.tuval.draw_idle()

    def _tabloya_ekle(self, s):
        satir = self.tablo.rowCount()
        self.tablo.insertRow(satir)
        if s.get("keff"):
            r, sr = tarama.reaktivite(s["keff"], s["sapma"])
            degerler = ["%.6g" % s["deger"], "%.5f" % s["keff"],
                        "%.5f" % s["sapma"], "%+.1f" % r]
        else:
            degerler = ["%.6g" % s["deger"], "BASARISIZ", "-", s.get("hata", "")[:40]]
        for i, d in enumerate(degerler):
            self.tablo.setItem(satir, i, QtWidgets.QTableWidgetItem(d))
        self.tablo.scrollToBottom()

    # ==================================================================
    def _uygunluk(self, tur):
        """
        Secilen parametrenin bu modele uyup uymadigini kabaca kontrol eder.
        Kesin degil -- yalnizca belirgin uyumsuzluklari yakalar ve sorar.
        """
        if self.spec is None:
            return True, ""
        # Butun taramalar reaktiviteye dayanir: rho = (k-1)/k. Sabit kaynak
        # modunda k-eff YOKTUR, dolayisiyla hicbir tarama anlamli degildir.
        if (self.spec["ayarlar"].get("mod") or "eigenvalue") != "eigenvalue":
            return False, ("Bu sekmedeki tum taramalar reaktivite (k-eff) uzerinden "
                           "calisir; model SABIT KAYNAK modunda ve k-eff tanimsiz.\n"
                           "5. Ayarlar sekmesinden kosu modunu 'Ozdeger (k-eff)' "
                           "yapin.")
        hedef = self.hedef.currentData()
        m = sema.malzeme_bul(self.spec, hedef) if isinstance(hedef, str) else None
        if tur == "bor_ppm":
            if m is None:
                return False, "Bor taramasi bir su malzemesi gerektirir."
            elemanlar = {b.get("isim", "") for b in m.get("bilesim", [])}
            if not ({"H", "O"} <= elemanlar):
                return False, ("'%s' su gorunumunde degil (bilesiminde H ve O yok). "
                               "Bor taramasi suda cozunmus bor icindir." % hedef)
        if tur == "zenginlik":
            if m is None or not any(b.get("zenginlik") is not None
                                    for b in m.get("bilesim", [])):
                return False, ("'%s' malzemesinde zenginlik alani olan bir bilesen "
                               "yok. Bilesim nuklid bazinda verilmisse zenginlik "
                               "taramasi uygulanamaz." % hedef)
        if tur == "sogutucu_sicaklik" and m is not None:
            fonk, aciklama = tarama._yogunluk_korelasyonu(m)
            if fonk is None:
                return False, (aciklama + "\n\nSonuc yalnizca spektral etkiyi "
                               "olcer, gercek moderator sicaklik katsayisi degildir.")
        if tur == "cubuk_daldirma":
            kontroller = [c for c in self.spec.get("cubuklar", [])
                          if c.get("tur") == "kontrol"]
            if not kontroller:
                return False, ("Modelde kontrol cubugu yok. 2. sekmede bir cubugun "
                               "turunu 'Kontrol cubugu' yapin.")
            if not self.spec["kor"].get("yukseklik"):
                return False, ("Kontrol cubugu 3B model gerektirir; kor "
                               "yuksekligi tanimli degil.")
        if tur == "tambur_donme":
            t = (self.spec.get("kor") or {}).get("tambur") or {}
            if int(t.get("sayi") or 0) <= 0:
                return False, ("Modelde kontrol tamburu yok. 4. Kor sekmesinde "
                               "kor turunu 'Tamburlu kor' yapin.")
        if tur in ("kafes_adim",) and not self.spec.get("demetler"):
            return False, "Modelde kafes yok."
        if tur == "yansitici_kalinlik" and not (self.spec["kor"].get("yansitici") or {}).get("var"):
            return False, "Modelde yansitici kusak tanimli degil."
        return True, ""

    def _dizin(self, onek):
        taban = os.path.dirname(self.proje_yolu) if self.proje_yolu else tempfile.gettempdir()
        yol = os.path.join(taban, "%s_%s" % (onek, self.tur.currentData()))
        os.makedirs(yol, exist_ok=True)
        return yol

    def _basla(self):
        izin, mesaj = self._kapi()
        if not izin:
            QtWidgets.QMessageBox.warning(self, "Calistirilamaz", mesaj)
            return
        tur = self.tur.currentData()
        # Secilen parametre bu modele uygun mu? (orn. tek malzemeli ciplak bir
        # kurede "suda cozunmus bor" taramasi anlamsizdir.)
        uygun, sebep = self._uygunluk(tur)
        if not uygun:
            c = QtWidgets.QMessageBox.question(
                self, "Bu parametre bu modele uymuyor olabilir",
                "%s\n\nYine de devam edilsin mi?" % sebep)
            if c != QtWidgets.QMessageBox.Yes:
                return
        if self.hedef.count() == 0:
            QtWidgets.QMessageBox.warning(self, "Hedef yok",
                                          "Bu parametre icin uygun bir hedef bulunamadi.")
            return

        self._sonuclar = []
        self.tablo.setRowCount(0)
        self._grafik_sifirla()
        self.sonuc_kutusu.setText("Calisiyor...")
        tur = self.tur.currentData()
        hedef = self.hedef.currentData()
        n = self.spec["calistirma"].get("is_parcacigi", 8)

        if self.mod.currentData() == "tarama":
            degerler = tarama.noktalar(self.bas.value(), self.son.value(),
                                       self.adet.value())
            self.ilerleme.setRange(0, len(degerler))
            self.ilerleme.setValue(0)
            self._isci = TaramaIsci(self.spec, tur, hedef, degerler,
                                    self._dizin("tarama"), n, self)
            self._isci.nokta.connect(self._tarama_noktasi)
            self._isci.bitti.connect(self._tarama_bitti)
            self._isci.hata.connect(self._hata)
        else:
            self.ilerleme.setRange(0, 0)     # belirsiz
            self._isci = AramaIsci(self.spec, tur, hedef, self.bas.value(),
                                   self.son.value(), self.hedef_keff.value(),
                                   self._dizin("arama"), n, self)
            self._isci.adim.connect(self._arama_adimi)
            self._isci.bitti.connect(self._arama_bitti)
            self._isci.hata.connect(self._hata)

        self._isci.finished.connect(self._isci_bitti)
        self._baslangic = __import__("time").perf_counter()
        self._son_nokta_zamani = self._baslangic
        self.d_basla.setEnabled(False)
        self.d_dur.setEnabled(True)
        self._isci.start()
        self.durum.emit("Analiz basladi", True)

    def _durdur(self):
        if self._isci:
            self._isci.durdur()
            self.durum.emit("Durdurma istendi -- suren kosu bitince duracak", True)

    def _isci_bitti(self):
        import time
        if hasattr(self, "_baslangic"):
            self.tahmin_etiket.setText(
                "tamamlandi -- toplam %s"
                % self._sure_metni(time.perf_counter() - self._baslangic))
        self._isci = None
        self.d_dur.setEnabled(False)
        self.ilerleme.setRange(0, 1)
        self.kapi_guncelle()

    def _hata(self, mesaj):
        self.sonuc_kutusu.setText("HATA: %s" % mesaj)
        self.durum.emit("Analiz hatasi: %s" % mesaj, False)

    # ------------------------------------------------------------------
    def _tarama_noktasi(self, i, toplam, s):
        import time
        simdi = time.perf_counter()
        self._hizi_kalibre_et(simdi - self._son_nokta_zamani)
        self._son_nokta_zamani = simdi
        self._sonuclar.append(s)
        self._tabloya_ekle(s)
        self.ilerleme.setValue(i + 1)
        self._grafik_guncelle()
        kalan = (toplam - i - 1) * (simdi - self._baslangic) / (i + 1)
        self.tahmin_etiket.setText(
            "gecen %s  |  kalan ~%s  (olcume gore)"
            % (self._sure_metni(simdi - self._baslangic), self._sure_metni(kalan)))

    def _tarama_bitti(self, sonuclar, notlar):
        self._sonuclar = sonuclar
        tur = self.tur.currentData()
        kats = tarama.katsayi(sonuclar)
        self._grafik_guncelle(kats)
        kbirim = tarama.TURLER[tur][3]
        if kats:
            metin = ("<b>KATSAYI = %+.3f &plusmn; %.3f %s</b><br>"
                     "dogrusal uyum R&sup2; = %.4f, %d nokta<br><br>%s"
                     % (kats["egim"], kats["egim_sapma"], kbirim,
                        kats["r2"], kats["nokta"], tarama.yorumla(tur, kats)))
        else:
            metin = "Katsayi hesaplanamadi (yeterli gecerli nokta yok)."
        if notlar:
            metin += "<br><br><i>Notlar:</i><br>" + "<br>".join("&bull; " + n for n in notlar)
        self.sonuc_kutusu.setText(metin)
        self.durum.emit("Tarama tamamlandi", True)

    def _arama_adimi(self, i, kayit):
        import time
        simdi = time.perf_counter()
        self._hizi_kalibre_et(simdi - self._son_nokta_zamani)
        self._son_nokta_zamani = simdi
        self.tahmin_etiket.setText("gecen %s  |  %d. kosu bitti"
                                   % (self._sure_metni(simdi - self._baslangic), i + 1))
        self._sonuclar.append(kayit)
        self._tabloya_ekle(kayit)
        self._grafik_guncelle()

    def _arama_bitti(self, s):
        self._grafik_guncelle()
        tur = self.tur.currentData()
        birim = tarama.TURLER[tur][2]
        if s.basarili:
            metin = ("<b>COZUM: %s = %.6g %s</b><br>"
                     "k = %.5f &plusmn; %.5f &nbsp;&nbsp; (%d kosu)<br><br>%s"
                     % (tur, s.cozum, birim, s.cozum_keff, s.cozum_sapma,
                        len(s.adimlar), s.mesaj))
        else:
            metin = "<b>Cozum bulunamadi.</b><br><br>%s" % s.mesaj
        self.sonuc_kutusu.setText(metin)
        self.durum.emit("Kritik arama tamamlandi", s.basarili)
