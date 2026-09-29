# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_calistir.py  --  Kosu, canli takip ve sonuclar (tek akisli sayfa)
================================================================================
 openmc alt surec olarak QProcess ile calistirilir; Qt olay dongusune dogal
 entegre oldugu icin arayuz kosu boyunca donmaz.

 SAYFA (alt sekme YOK, yukaridan asagiya tek akis)
   kosu cubugu   : Calistir / Durdur / ilerleme + is parcacigi + kosu dizini
   grafik        : k-eff yakinsamasi (+ Shannon entropisi, yalnizca aciksa).
                   Sabit kaynakta k-eff tanimsizdir: grafik hic gosterilmez.
   sonuc karti   : k-eff, kritiklik yorumu, ozet (sabit kaynakta tally'ler)
   guc haritasi  : yalnizca guc dagilimi etkin VE sonuc varsa
   ayrintili cikti (katlanir, varsayilan kapali; hata olursa kendiliginden
                   acilir): ham OpenMC ciktisi ve tam sonuc metni

 !!! ONCE CIZ, SONRA CALISTIR !!!
   Geometri onizlemesi basariyla uretilmeden ve dogrulama hatalari giderilmeden
   Calistir dugmesi etkinlesmez (kapi: ana pencere verir).

 PROJE KUSAGI
   sifirla() (proje degisti) bir kusak sayacini artirir. Onceki projede
   baslamis bir kosu arka planda bitebilir; o kusagin ciktisi ve sonucu YENI
   projeye yazilmaz (dosyalari eski projenin dizininde kalir).
================================================================================
"""

import os

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import kosucu
from cekirdek import sema, uygunluk
from cekirdek import kaynak as _kaynak
from cekirdek import guc as _guc
from arayuz.ortak import BosDurum, GelismisBolum, tamsayi


def _tema_renk(ad, vars_="#6b7785"):
    try:
        from arayuz import tema
        return tema.renk(ad)
    except Exception:
        return vars_


def _yazi_tipi_es_aralikli(w, boyut=8.5):
    f = w.font()
    f.setFamily("monospace")
    f.setStyleHint(QtGui.QFont.StyleHint.Monospace)
    f.setPointSizeF(boyut)
    w.setFont(f)


class CalistirSekmesi(QtWidgets.QWidget):
    """Kosuyu baslatir, ciktiyi canli gosterir, sonucu okur."""

    durum = QtCore.Signal(str, bool)
    # Kosu ayarlari (is parcacigi, dizin) degisti -> ana pencere "calistirma"
    # konusu ile kirli/gecmis isler (editor sozlesmesiyle ayni bicim).
    degisti = QtCore.Signal(str)
    # Gosterilen sonucun durumu degisti (kosu bitti / basarisiz / sifirlandi).
    sonuc_degisti = QtCore.Signal()
    KONU = "calistirma"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec = None
        self.proje_yolu = None
        self._kapi = lambda: (False, "hazır değil")
        self._surec = None
        self._dizin = None
        self._tampon = ""
        self._cevrimler = []
        self._son_basarili = False
        self._basarisiz = False          # bu kusakta kosu basarisiz bitti
        self._durduruldu = False
        self._gosterilen_sabit = None    # gosterilen kosunun modu (sabit kaynak mi)
        self._guc_var = False            # gosterilen sonucta guc dagilimi var mi
        self._entropi_grafik = None      # grafik iki eksenli mi (entropi)
        self._kusak = 0                  # proje kusagi (sifirla artirir)
        self._kosu_kusagi = None         # suren/son kosunun kusagi
        self._yukleniyor = False

        # ---------------- kosu cubugu ----------------
        self.d_calistir = QtWidgets.QPushButton("Çalıştır")
        self.d_calistir.setObjectName("birincil")
        self.d_calistir.setMinimumHeight(34)
        self.d_calistir.setMinimumWidth(120)
        self.d_calistir.setToolTip("Modeli OpenMC ile çalıştırır (F9).")
        self.d_durdur = QtWidgets.QPushButton("Durdur")
        self.d_durdur.setMinimumHeight(34)
        self.d_durdur.setEnabled(False)
        self.ilerleme = QtWidgets.QProgressBar()
        self.ilerleme.setTextVisible(True)
        self.ilerleme.setRange(0, 1)
        self.ilerleme.setValue(0)
        self.kapi_etiket = QtWidgets.QLabel("-")
        self.kapi_etiket.setWordWrap(True)

        self.d_calistir.clicked.connect(self.calistir)
        self.d_durdur.clicked.connect(self.durdur)

        ust = QtWidgets.QHBoxLayout()
        ust.addWidget(self.d_calistir)
        ust.addWidget(self.d_durdur)
        ust.addWidget(self.ilerleme, 1)

        # ---------------- kosu ayarlari ----------------
        self.is_parcacigi = tamsayi(8, 1, 512, 1)
        self.is_parcacigi.setMinimumWidth(70)
        n_cekirdek = QtCore.QThread.idealThreadCount()
        self.is_parcacigi.setToolTip(
            "OpenMP iş parçacığı sayısı (openmc -s N). Bu bilgisayarda %d mantıksal "
            "çekirdek var; tüm çekirdekleri kullanmak arayüzü yavaşlatabilir."
            % max(n_cekirdek, 1))
        self.kosu_dizini = QtWidgets.QLineEdit()
        self.kosu_dizini.setPlaceholderText("kosu")
        self.kosu_dizini.setToolTip(
            "Koşu dosyalarının yazılacağı dizin. Göreli yol proje dosyasının "
            "yanına yazılır; her koşuda içi temizlenir.")
        self.dizin_yolu = QtWidgets.QLabel("")
        self.dizin_yolu.setObjectName("soluk")
        self.dizin_yolu.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.is_parcacigi.valueChanged.connect(self._calistirma_kaydet)
        self.kosu_dizini.editingFinished.connect(self._calistirma_kaydet)

        ayar = QtWidgets.QHBoxLayout()
        ayar.addWidget(QtWidgets.QLabel("İş parçacığı:"))
        ayar.addWidget(self.is_parcacigi)
        ayar.addSpacing(16)
        ayar.addWidget(QtWidgets.QLabel("Koşu dizini:"))
        ayar.addWidget(self.kosu_dizini, 1)
        ayar.addWidget(self.dizin_yolu, 2)

        # ---------------- bos durum ----------------
        self.bos = BosDurum(
            "Henüz koşu yok",
            "Çalıştır'a basın; k-eff yakınsaması ve sonuçlar bu sayfada görünür.",
            None, "▶")

        # ---------------- yakinsama grafigi ----------------
        # Ust: k-eff yakinsamasi, alt (yalnizca entropi aciksa): Shannon entropisi
        self.figur = Figure(figsize=(5, 2.8), tight_layout=True)
        self.tuval = FigureCanvasQTAgg(self.figur)
        self.eksen = None
        self.eksen_ent = None
        self._grafik_kur(True)

        # ---------------- sonuc karti ----------------
        self.kart = QtWidgets.QFrame()
        self.kart.setObjectName("sonucKarti")
        self.kart.setStyleSheet(
            "QFrame#sonucKarti { background: palette(base); border: 1px solid palette(mid);"
            " border-radius: 10px; }"
            "QFrame#sonucKarti QLabel { background: transparent; border: none; }")
        self.keff_baslik = QtWidgets.QLabel("k-eff")
        self.keff_baslik.setObjectName("soluk")
        self.keff_etiket = QtWidgets.QLabel("-")
        # Tema stil sayfasi "QWidget { font-size }" setFont'u ezer: boyut burada.
        self.keff_etiket.setStyleSheet("font-size: 17pt; font-weight: 700;")
        self.keff_etiket.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.durum_etiket = QtWidgets.QLabel("")
        self.durum_etiket.setWordWrap(True)
        self.durum_etiket.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.ozet_etiket = QtWidgets.QLabel("")
        self.ozet_etiket.setWordWrap(True)
        self.ozet_etiket.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        _yazi_tipi_es_aralikli(self.ozet_etiket, 9.0)
        self.tally_baslik = QtWidgets.QLabel("Tally sonuçları")
        self.tally_baslik.setStyleSheet("font-weight: 600;")
        self.tally_metin = QtWidgets.QPlainTextEdit()
        self.tally_metin.setReadOnly(True)
        self.tally_metin.setMinimumHeight(180)
        _yazi_tipi_es_aralikli(self.tally_metin)

        kd = QtWidgets.QVBoxLayout(self.kart)
        kd.setContentsMargins(14, 10, 14, 12)
        kd.setSpacing(4)
        satir = QtWidgets.QHBoxLayout()
        satir.addWidget(self.keff_baslik, 0, QtCore.Qt.AlignBottom)
        satir.addWidget(self.keff_etiket, 0, QtCore.Qt.AlignBottom)
        satir.addStretch(1)
        kd.addLayout(satir)
        kd.addWidget(self.durum_etiket)
        kd.addWidget(self.ozet_etiket)
        kd.addWidget(self.tally_baslik)
        kd.addWidget(self.tally_metin)

        # ---------------- guc haritasi ----------------
        from arayuz.guc_harita import GucHaritaWidget
        self.guc_harita = GucHaritaWidget()

        # ---------------- ayrintili cikti ----------------
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        self.log.setMinimumHeight(200)
        _yazi_tipi_es_aralikli(self.log)
        # Tam sonuc metni: ozet + statepoint yolu + tum tally tablolari
        self.sonuc_metin = QtWidgets.QPlainTextEdit()
        self.sonuc_metin.setReadOnly(True)
        self.sonuc_metin.setMinimumHeight(160)
        _yazi_tipi_es_aralikli(self.sonuc_metin)
        self.ayrinti = GelismisBolum("calistir_ayrinti", "Ayrıntılı çıktı")
        self.ayrinti.ekle(QtWidgets.QLabel("OpenMC çıktısı"))
        self.ayrinti.ekle(self.log)
        self.ayrinti.ekle(QtWidgets.QLabel("Tam sonuç metni (statepoint ve tüm tally tabloları)"))
        self.ayrinti.ekle(self.sonuc_metin)

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setSpacing(8)
        duzen.addLayout(ust)
        duzen.addLayout(ayar)
        duzen.addWidget(self.kapi_etiket)
        duzen.addWidget(self.bos, 1)
        duzen.addWidget(self.tuval)
        duzen.addWidget(self.kart)
        duzen.addWidget(self.guc_harita)
        duzen.addWidget(self.ayrinti)
        duzen.addStretch(0)

        self._gorunum_guncelle()

    # ==================================================================
    # disaridan
    # ==================================================================
    def kapi_ayarla(self, fonksiyon):
        """fonksiyon() -> (izin_var_mi, aciklama)"""
        self._kapi = fonksiyon

    def spec_ayarla(self, spec, proje_yolu=None):
        """Spec ve proje yolu; kosu ayarlari (is parcacigi, dizin) yeniden yuklenir."""
        self.spec = spec
        self.proje_yolu = proje_yolu
        self._calistirma_yukle()
        self._gorunum_guncelle()
        self.kapi_guncelle()

    def sonuc_var(self):
        """Bu projede basarili bir kosunun sonucu gosteriliyor mu."""
        return bool(self._son_basarili)

    def sifirla(self):
        """
        PROJE degisince (yeni/ac/ornek/sablon) onceki projenin sonucunu siler.
        Sekme degisiminde CAGRILMAZ. Kusak artar: onceki projede baslamis ve
        hala suren bir kosunun ciktisi/sonucu bu projeye yazilmaz.
        """
        self._kusak += 1
        self._son_basarili = False
        self._basarisiz = False
        self._gosterilen_sabit = None
        self._guc_var = False
        self._cevrimler = []
        self._tampon = ""
        self.log.clear()
        self.sonuc_metin.clear()
        self.tally_metin.clear()
        self.keff_etiket.setText("-")
        self.durum_etiket.setText("")
        self.durum_etiket.setStyleSheet("")
        self.ozet_etiket.setText("")
        self.ilerleme.setRange(0, 1)
        self.ilerleme.setValue(0)
        self.ilerleme.resetFormat()
        self._grafik_kur(self._entropi_acik(self.spec))
        self.guc_harita.sonuc_ayarla(None, None)
        self._gorunum_guncelle()
        self.kapi_guncelle()
        self.sonuc_degisti.emit()

    def kapi_guncelle(self):
        if self._surec is not None:
            if self._eski_kosu():
                self._kapi_yaz(False, "Önceki projenin koşusu arka planda sürüyor; "
                                      "sonucu bu projeye yazılmayacak. Yeni koşu için "
                                      "Durdur ile sonlandırın.")
            return
        izin, mesaj = self._kapi()
        self.d_calistir.setEnabled(izin)
        self._kapi_yaz(izin, mesaj)

    def _kapi_yaz(self, izin, mesaj):
        self.kapi_etiket.setStyleSheet(
            "color: %s;" % (_tema_renk("metin_soluk") if izin else _tema_renk("hata", "#b3261e")))
        self.kapi_etiket.setText(mesaj)

    # ==================================================================
    # kosu ayarlari <-> spec["calistirma"]
    # ==================================================================
    def _calistirma_yukle(self):
        c = (self.spec or {}).get("calistirma") or {}
        self._yukleniyor = True
        try:
            self.is_parcacigi.setValue(int(c.get("is_parcacigi", 8) or 8))
            self.kosu_dizini.setText(str(c.get("dizin", "kosu") or "kosu"))
        finally:
            self._yukleniyor = False
        self._dizin_yolu_guncelle()

    def _calistirma_kaydet(self, *_):
        if self._yukleniyor or self.spec is None:
            return
        c = self.spec.setdefault("calistirma", {})
        yeni = {"is_parcacigi": int(self.is_parcacigi.value()),
                "dizin": self.kosu_dizini.text().strip() or "kosu"}
        if self.kosu_dizini.text() != yeni["dizin"]:
            self._yukleniyor = True
            self.kosu_dizini.setText(yeni["dizin"])
            self._yukleniyor = False
        degisen = [k for k, v in yeni.items() if c.get(k) != v]
        self._dizin_yolu_guncelle()
        if not degisen:
            return
        c.update(yeni)
        self.degisti.emit(self.KONU)

    def _kosu_dizini(self):
        """Kosunun yazilacagi mutlak dizin (spec'teki goreli yol projeye gore)."""
        taban = sema.kosu_tabani(self.proje_yolu)
        dizin = ((self.spec or {}).get("calistirma") or {}).get("dizin", "kosu") or "kosu"
        return dizin if os.path.isabs(dizin) else os.path.join(taban, dizin)

    def _dizin_yolu_guncelle(self):
        yol = self._kosu_dizini()
        self.dizin_yolu.setText("→ " + yol)
        self.dizin_yolu.setToolTip(yol)

    # ==================================================================
    # gorunum
    # ==================================================================
    @staticmethod
    def _sabit_mi(spec):
        return ((spec or {}).get("ayarlar") or {}).get("mod", "eigenvalue") != "eigenvalue"

    @staticmethod
    def _entropi_acik(spec):
        a = (spec or {}).get("ayarlar") or {}
        return bool((a.get("entropi_mesh") or {}).get("var", True))

    def _guc_etkin(self):
        """Guc dagilimi bu modelde acik ve gecerli mi (uygunluk kurali)."""
        spec = self.spec or {}
        if not (spec.get("guc_dagilimi") or {}).get("var"):
            return False
        try:
            from cekirdek import uygunluk
            return bool(uygunluk.ayar_alanlari(spec).get("guc_dagilimi"))
        except Exception:
            return True

    def _eski_kosu(self):
        """Suren (ya da biten) kosu onceki bir projeye mi ait?"""
        return self._kosu_kusagi is not None and self._kosu_kusagi != self._kusak

    def _kosuyor(self):
        return self._surec is not None and not self._eski_kosu()

    def _mod_gorunumu(self, sabit):
        """Geriye uyum: gosterilecek modu sabitler ve gorunumu tazeler."""
        self._gosterilen_sabit = bool(sabit)
        self._gorunum_guncelle()

    def _gorunum_guncelle(self):
        """
        Bolumlerin gorunurlugu tek yerden:
          grafik     : ozdeger modunda, kosu surerken ya da cevrim verisi varken
          sonuc karti: kosu surerken, sonuc varken ya da kosu basarisizken
          k-eff      : sabit kaynakta gizli
          tally'ler  : sabit kaynak sonucunda kartta (ozdegerde ayrintili ciktida)
          guc haritasi: guc dagilimi etkin VE gosterilen sonucta guc verisi var
          bos durum  : hicbiri yokken
        """
        kosuyor = self._kosuyor()
        sonuc = self._son_basarili
        kart = kosuyor or sonuc or self._basarisiz
        if (kosuyor or sonuc) and self._gosterilen_sabit is not None:
            sabit = self._gosterilen_sabit
        else:
            sabit = self._sabit_mi(self.spec)
        grafik = not sabit and (kosuyor or bool(self._cevrimler))
        self.tuval.setVisible(grafik)
        self.kart.setVisible(kart)
        for w in (self.keff_baslik, self.keff_etiket):
            w.setVisible(not sabit)
        tally = sonuc and sabit and bool(self.tally_metin.toPlainText())
        self.tally_baslik.setVisible(tally)
        self.tally_metin.setVisible(tally)
        self.ozet_etiket.setVisible(bool(self.ozet_etiket.text()))
        self.guc_harita.setVisible(sonuc and self._guc_var and self._guc_etkin())
        self.bos.setVisible(not (kart or grafik))
        # Ayrintili cikti yalnizca gosterecek bir sey varken (bos bolum gurultudur)
        self.ayrinti.setVisible(kosuyor or bool(self.log.toPlainText())
                                or bool(self.sonuc_metin.toPlainText()))
        # ayarlar: kosu surerken degistirilemez (suren kosuyu etkilemez, yaniltir)
        for w in (self.is_parcacigi, self.kosu_dizini):
            w.setEnabled(self._surec is None)

    # ==================================================================
    # grafik
    # ==================================================================
    def _grafik_kur(self, entropi):
        """Eksenleri kurar: entropi aciksa iki (k-eff + entropi), degilse tek."""
        self._entropi_grafik = bool(entropi)
        self.figur.clear()
        if entropi:
            self.eksen = self.figur.add_subplot(211)
            self.eksen_ent = self.figur.add_subplot(212, sharex=self.eksen)
            self.tuval.setFixedHeight(300)
        else:
            self.eksen = self.figur.add_subplot(111)
            self.eksen_ent = None
            self.tuval.setFixedHeight(190)
        self._grafik_sifirla()

    def _eksenler(self):
        e = [(self.eksen, "k-eff")]
        if self.eksen_ent is not None:
            e.append((self.eksen_ent, "Shannon entropisi"))
        return e

    def _grafik_sifirla(self):
        for eks, etiket in self._eksenler():
            eks.clear()
            eks.set_ylabel(etiket, fontsize=8)
            eks.tick_params(labelsize=7)
            eks.grid(alpha=0.3)
        self._eksenler()[-1][0].set_xlabel("çevrim", fontsize=8)
        self.tuval.draw_idle()

    def _grafik_guncelle(self):
        if not self._cevrimler:
            return
        from arayuz import tema as _t
        self.eksen.clear()
        self.eksen.grid(alpha=0.3)
        pasif = (self.spec or {}).get("ayarlar", {}).get("pasif", 0)
        x = [c["cevrim"] for c in self._cevrimler]
        y = [c["k"] for c in self._cevrimler]
        self.eksen.plot(x, y, lw=0.8, color=_t.renk("metin_soluk"), label="çevrim k")
        ort = [(c["cevrim"], c["ortalama"], c["sapma"])
               for c in self._cevrimler if c["ortalama"] is not None]
        if ort:
            ox = [a for a, _, _ in ort]
            oy = [b for _, b, _ in ort]
            os_ = [c for _, _, c in ort]
            self.eksen.plot(ox, oy, lw=1.6, color=_t.renk("vurgu"), label="kümülatif ortalama")
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

        # --- entropi grafigi (yalnizca entropi aciksa kurulur) ---
        if self.eksen_ent is not None:
            self.eksen_ent.clear()
            self.eksen_ent.grid(alpha=0.3)
            ent = [(c["cevrim"], c["entropi"]) for c in self._cevrimler
                   if c.get("entropi") is not None]
            if ent:
                self.eksen_ent.plot([a for a, _ in ent], [b for _, b in ent],
                                    lw=1.0, color=_t.renk("vurgu"))
                if pasif:
                    self.eksen_ent.axvline(pasif, color=_t.renk("hata"), ls="--", lw=1.0)
            self.eksen_ent.set_ylabel("Shannon entropisi", fontsize=8)
            self.eksen_ent.set_xlabel("çevrim", fontsize=8)
            self.eksen_ent.tick_params(labelsize=7)
        else:
            self.eksen.set_xlabel("çevrim", fontsize=8)
        self.tuval.draw_idle()

    # ==================================================================
    # kosu
    # ==================================================================
    def calistir(self):
        izin, mesaj = self._kapi()
        if not izin:
            QtWidgets.QMessageBox.warning(self, "Çalıştırılamaz", mesaj)
            return
        if self._surec is not None:
            return
        self._calistirma_kaydet()           # yazilip Enter'a basilmamis dizin
        dizin = self._kosu_dizini()
        self._dizin = dizin

        try:
            kosucu.dizin_hazirla(dizin, temizle=True)
            kosucu.xml_yaz(self.spec, dizin)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Model kurulamadı", str(e))
            return

        exe = kosucu.openmc_yolu()
        if exe is None:
            QtWidgets.QMessageBox.critical(
                self, "openmc bulunamadı",
                "openmc çalıştırılabilir dosyası PATH'te yok.\n"
                "Conda ortamının etkin olduğundan emin olun (openmc-env).")
            return

        self._kosu_kusagi = self._kusak
        self._son_basarili = False
        self._basarisiz = False
        self._durduruldu = False
        self._guc_var = False
        sabit = self._sabit_mi(self.spec)
        self._gosterilen_sabit = sabit
        self.log.clear()
        self.sonuc_metin.clear()
        self.tally_metin.clear()
        self.ozet_etiket.setText("")
        self.guc_harita.sonuc_ayarla(None, None)
        self.keff_etiket.setText("koşuyor…")
        self.durum_etiket.setStyleSheet("")
        self.durum_etiket.setText("Sabit kaynak — k-eff tanımsız; sonuç tally'lerdir."
                                  if sabit else "Koşu sürüyor; k-eff kümülatif ortalamadır.")
        self._cevrimler = []
        self._tampon = ""
        self._grafik_kur(self._entropi_acik(self.spec) and not sabit)

        toplam = int((self.spec.get("ayarlar") or {}).get("cevrim", 1) or 1)
        self.ilerleme.setRange(0, toplam)
        self.ilerleme.setValue(0)
        self.ilerleme.setFormat("%v / %m çevrim")

        n = int(self.spec.get("calistirma", {}).get("is_parcacigi", 8) or 8)
        self._surec = QtCore.QProcess(self)
        self._surec.setWorkingDirectory(dizin)
        self._surec.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self._surec.readyReadStandardOutput.connect(self._cikti_oku)
        self._surec.finished.connect(self._bitti)
        self._surec.errorOccurred.connect(self._hata)

        self._yaz("# komut: %s -s %d" % (exe, n))
        self._yaz("# dizin: %s\n" % dizin)
        self._surec.start(exe, ["-s", str(n)])

        self.d_calistir.setEnabled(False)
        self.d_durdur.setEnabled(True)
        self._kapi_yaz(True, "Koşu sürüyor (%d iş parçacığı) → %s" % (n, dizin))
        self._gorunum_guncelle()
        self.sonuc_degisti.emit()
        self.durum.emit("Koşu başladı → %s" % dizin, True)

    def durdur(self):
        if self._surec is not None:
            self._durduruldu = True
            self._surec.kill()
            if not self._eski_kosu():
                self._yaz("\n# kullanıcı tarafından durduruldu")

    # ------------------------------------------------------------------
    def _yaz(self, metin):
        self.log.appendPlainText(metin)

    def _cikti_oku(self):
        if self._surec is None:
            return
        ham = bytes(self._surec.readAllStandardOutput()).decode("utf-8", "replace")
        if self._eski_kosu():
            return                  # onceki projenin kosusu: cikti bu projeye yazilmaz
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
                continue
            # Sabit kaynak: " Simulating batch N" (k-eff sutunu yok)
            n = kosucu.sabit_kaynak_cevrimi(satir)
            if n is not None:
                self.ilerleme.setValue(n)

    def _hata(self, kod):
        if self._surec is None:
            return
        if not self._eski_kosu():
            self._yaz("\n# Süreç hatası: %s" % self._surec.errorString())
        # Baslatilamayan surec finished() YAYMAZ: dugmeler kilitli kalirdi.
        if kod == QtCore.QProcess.FailedToStart:
            self._bitti(-1, None)

    def _bitti(self, cikis_kodu, _durum):
        eski = self._eski_kosu()
        surec, self._surec = self._surec, None
        if surec is not None:
            try:
                surec.deleteLater()
            except Exception:
                pass
        self.d_durdur.setEnabled(False)
        self.kapi_guncelle()
        if eski:
            # Onceki projenin kosusu: sonucu bu projeye YAZILMAZ.
            self._kosu_kusagi = None
            self._gorunum_guncelle()
            self.durum.emit("Önceki projenin koşusu bitti; sonucu bu projeye yazılmadı "
                            "(dosyalar: %s)." % self._dizin, True)
            return
        self._grafik_guncelle()

        if self._durduruldu:
            self._basarisiz = True
            self.keff_etiket.setText("durduruldu")
            self.durum_etiket.setStyleSheet("")
            self.durum_etiket.setText("Koşu kullanıcı tarafından durduruldu; sonuç yok.")
            self._gorunum_guncelle()
            self.sonuc_degisti.emit()
            self.durum.emit("Koşu durduruldu", False)
            return

        if cikis_kodu != 0:
            self._basarisiz_goster("Koşu başarısız (çıkış kodu %d). OpenMC çıktısı "
                                   "aşağıda, 'Ayrıntılı çıktı' bölümünde." % cikis_kodu)
            self.durum.emit("Koşu başarısız (çıkış kodu %d)" % cikis_kodu, False)
            return

        sp = kosucu.son_statepoint(self._dizin)
        if sp is None:
            self._basarisiz_goster("Koşu bitti ama statepoint dosyası bulunamadı.")
            self.durum.emit("Koşu bitti ama statepoint bulunamadı", False)
            return
        try:
            s = kosucu.sonuc_oku(sp)
        except Exception as e:
            self._basarisiz_goster("Sonuç okunamadı: %s" % e)
            self.durum.emit("Sonuç okunamadı: %s" % e, False)
            return
        self._sonuc_goster(s, sp)

    def _basarisiz_goster(self, metin):
        self._son_basarili = False
        self._basarisiz = True
        self.keff_etiket.setText("başarısız")
        self.durum_etiket.setText(metin)
        self.durum_etiket.setStyleSheet("color: %s; font-weight: bold;" % _tema_renk("hata"))
        self.ayrinti.ac(True)            # hata: ayrintili cikti kendiliginden acilir
        self._gorunum_guncelle()
        self.sonuc_degisti.emit()

    # ==================================================================
    # sonuc
    # ==================================================================
    def _sonuc_goster(self, s, sp):
        """
        kosucu.sonuc_oku() ciktisini gosterir. Sabit kaynak modunda k-eff YOKTUR
        (s["keff"] is None): eskiden "%.5f" % None ile cokuyor, tally'ler hic
        gosterilmiyor ve kosu basarili sayilmiyordu.
        """
        sabit = s.get("keff") is None
        self._gosterilen_sabit = sabit
        ozet = []
        if sabit:
            k_tanim = ((self.spec or {}).get("ayarlar") or {}).get("kaynak") or {}
            kuvvet = float(k_tanim.get("kuvvet") or 1.0)
            self.keff_etiket.setText("-")
            self.durum_etiket.setText(
                "Sabit kaynak — k-eff tanımsız\nSonuç tally'lerdir (aşağıda).")
            self.durum_etiket.setStyleSheet("color: %s; font-weight: bold;"
                                            % _tema_renk("vurgu"))
            ozet += [
                "mod      = sabit kaynak (k-eff tanımsız)",
                "kaynak   = %s" % _kaynak.ozet(k_tanim),
                "şiddet   = %.4g parçacık/s" % kuvvet,
                "çevrim   = %d, %d parçacık/çevrim" % (s["cevrim"], s["parcacik"]),
            ]
            ozet.append("Sonuçlar akı ve tepkime hızlarıdır; doz hesaplanmaz. Akı hacim-"
                        "integrallidir (n·cm/s): ortalama akı [n/cm²/s] için bölgenin "
                        "hacmine bölün.")
            # OLCULDU (kosucu.py): OpenMC sabit kaynak tally'lerini kaynak
            # siddetiyle ZATEN carpar; "siddetle carpin" demek cift sayim olurdu.
            if kuvvet == 1.0:
                ozet.append("NOT: tally değerleri kaynak parçacığı başınadır "
                            "(şiddet 1). Mutlak birim için şiddeti girin.")
            else:
                ozet.append("Not: tally değerleri mutlak birimdedir — OpenMC "
                            "şiddeti zaten uygulamıştır, tekrar çarpmayın.")
        else:
            self.keff_etiket.setText("%.5f ± %.5f" % s["keff"])
            kin0 = s.get("kinetik") or {}
            sonsuz = uygunluk.sonsuz_ortam(self.spec or {})
            self.keff_baslik.setText("k∞" if sonsuz else "k-eff")
            durum, ayrinti = kosucu.keff_yorumu(s["keff"][0], s["keff"][1],
                                                kin0.get("beta_eff"), sonsuz=sonsuz)
            self.durum_etiket.setText("%s\n%s" % (durum, ayrinti))
            renk = (_tema_renk("basari") if durum.startswith("Kritik (")
                    else (_tema_renk("hata") if "üstü" in durum else _tema_renk("vurgu")))
            self.durum_etiket.setStyleSheet("color: %s; font-weight: bold;" % renk)
            ozet += [
                "çevrim   = %d (%d pasif), %d parçacık/çevrim"
                % (s["cevrim"], s["pasif"], s["parcacik"]),
            ]
            # --- kaynak yakinsamasi degerlendirmesi ---
            if s.get("entropi"):
                yakinsadi, mesaj = kosucu.entropi_yakinsama(s["entropi"], s["pasif"])
                isaret = {True: "[tamam]", False: "[uyarı]", None: "[  ?  ]"}[yakinsadi]
                ozet.append("kaynak   = %s %s" % (isaret, mesaj))
                if yakinsadi is False:
                    self.durum.emit("Dikkat: kaynak yakınsamamış olabilir — "
                                    "pasif çevrim sayısını artırın", False)
            else:
                ozet.append("kaynak   = [  ?  ] Shannon entropisi kapalı — "
                            "kaynak yakınsaması doğrulanamıyor")
        kin = s.get("kinetik")
        if kin:
            ozet.append("β_eff    = %.1f ± %.1f pcm   (reaktivite birimi: 1 $ = β_eff)"
                        % (kin["beta_eff"] * 1e5, kin["beta_eff_sapma"] * 1e5))
            ozet.append("Λ        = %-22s (nötron üretim zamanı)"
                        % kosucu.lambda_metni(kin["lambda"], kin["lambda_sapma"]))
        g = s.get("guc") or {}
        gf = g.get("faktorler")
        if gf:
            zayif = (gf.get("yanlilik_orani") or 0.0) > 0.3
            ozet.append("F_ΔH     = %.4f   (en yüksek çubuk gücü / ortalama)%s"
                        % (gf["F_dH"], "\n           ⚠ istatistik zayıf: bu değer yukarı "
                           "yanlı, güvenilir F_ΔH için Normal ya da Hassas hassasiyetle "
                           "koşun" if zayif else ""))
            if gf["F_q"]:
                ozet.append("F_q      = %.4f   (en yüksek yerel güç yoğunluğu / ortalama)"
                            % gf["F_q"])
            else:
                ozet.append("F_q      = tanımsız (model 2B)")
            ozet.append("en sıcak çubuk: %s%s"
                        % (_guc.konum_metni(gf["sicak_cubuk"], gf.get("kafes_turu"),
                                            gf.get("kafes_turleri")),
                           (", dilim %d" % (gf["sicak_dilim"][1] + 1))
                           if gf["sicak_dilim"] else ""))
            # korunum: tamam / bozuk / denetlenemedi (korunum_hata) / not
            ozet.extend(kosucu.korunum_satirlari(g))
        elif s.get("guc_hata"):
            ozet.append("güç dağılımı okunamadı: %s" % s["guc_hata"])

        tally = []
        k_tanim = ((self.spec or {}).get("ayarlar") or {}).get("kaynak") or {}
        for ad, df in s["tallyler"].items():
            tally.append(kosucu.tally_metni(ad, df, s.get("malzeme_adlari"), sabit,
                                            float(k_tanim.get("kuvvet") or 1.0)))
            tally.append("")
        tam = ([] if sabit else ["k-eff    = %.5f ± %.5f" % s["keff"]]) + ozet
        tam += ["statepoint: %s" % sp, ""] + tally
        self.ozet_etiket.setText("\n".join(ozet))
        self.sonuc_metin.setPlainText("\n".join(tam))
        self.tally_metin.setPlainText("\n".join(tally) if sabit else "")
        self.guc_harita.sonuc_ayarla(s, self.spec)
        self._guc_var = bool(gf)
        self._son_basarili = True
        self._basarisiz = False
        self._gorunum_guncelle()
        self.sonuc_degisti.emit()
        if sabit:
            self.durum.emit("Koşu tamamlandı (sabit kaynak) — sonuçlar tally'lerde", True)
        else:
            self.durum.emit("Koşu tamamlandı: k-eff = %.5f ± %.5f" % s["keff"], True)
