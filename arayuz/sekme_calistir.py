# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_calistir.py  --  Kosu, canli takip ve SONUC PANOSU (tek akisli sayfa)
================================================================================
 openmc alt surec olarak QProcess ile calistirilir; Qt olay dongusune dogal
 entegre oldugu icin arayuz kosu boyunca donmaz.

 SAYFA (alt sekme YOK, yukaridan asagiya tek akis; maket: sonuclar_*.png)
   kosu karti    : Calistir / Durdur / ilerleme + is parcacigi + kosu dizini
   pano          : k-eff ± sigma (pcm rozeti), Shannon entropisi, sure, hiz ve
                   kosu oncesi DOGRULAMA KAPISININ sonucu (arayuz/calistir/pano.py)
   grafikler     : yakinsama (k-eff) ve kaynak entropisi kartlari
                   (arayuz/calistir/yakinsama.py). Sabit kaynakta k-eff
                   tanimsizdir: bu kartlar hic gosterilmez.
   guc haritasi  : yalnizca guc dagilimi etkin VE sonuc varsa
   sonuc karti   : kritiklik yorumu, ozet (sabit kaynakta tally'ler)
   ayrintili cikti (katlanir, varsayilan kapali; hata olursa kendiliginden
                   acilir): ham OpenMC ciktisi ve tam sonuc metni

 !!! ONCE CIZ, SONRA CALISTIR !!!
   Geometri onizlemesi basariyla uretilmeden ve dogrulama hatalari giderilmeden
   Calistir dugmesi etkinlesmez (kapi: ana pencere verir). Kosu dizini
   TEMIZLENMEDEN once ayrica dogrula.kapi cagrilir (_dogrulama_kapisi).

 PROJE KUSAGI
   sifirla() (proje degisti) bir kusak sayacini artirir. Onceki projede
   baslamis bir kosu arka planda bitebilir; o kusagin ciktisi ve sonucu YENI
   projeye yazilmaz (dosyalari eski projenin dizininde kalir).
================================================================================
"""

import os

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import kosucu
from cekirdek import dogrula, sema, uygunluk
from cekirdek.ceviri import _
from cekirdek import kaynak as _kaynak
from cekirdek import guc as _guc
from arayuz import bilesenler as b
from arayuz import tema
from arayuz.calistir import gunluk_ozeti
from arayuz.calistir.pano import SonucPanosu
from arayuz.calistir.yakinsama import EntropiKarti, YakinsamaKarti
from arayuz.ortak import GelismisBolum, tamsayi
from arayuz.tasarim import tokenlar

A = tokenlar.ARALIK


def _yazi_tipi_es_aralikli(w, boyut=8.5):
    f = w.font()
    f.setFamily("monospace")
    f.setStyleHint(QtGui.QFont.StyleHint.Monospace)
    f.setPointSizeF(boyut)
    w.setFont(f)


class CalistirSekmesi(QtWidgets.QWidget):
    """Kosuyu baslatir, ciktiyi canli gosterir, sonucu panoda okur."""

    durum = QtCore.Signal(str, bool)
    # Kosu ayarlari (is parcacigi, dizin) degisti -> ana pencere "calistirma"
    # konusu ile kirli/gecmis isler (editor sozlesmesiyle ayni bicim).
    degisti = QtCore.Signal(str)
    # Gosterilen sonucun durumu degisti (kosu bitti / basarisiz / sifirlandi).
    sonuc_degisti = QtCore.Signal()
    # Kosu basladi (True) / bitti (False): kabuk Calistir <-> Durdur dugmesi.
    kosu_durumu_degisti = QtCore.Signal(bool)
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
        self._entropi_grafik = None      # entropi karti gosteriliyor mu
        self._kusak = 0                  # proje kusagi (sifirla artirir)
        self._kosu_kusagi = None         # suren/son kosunun kusagi
        self._yukleniyor = False
        self._sayac = QtCore.QElapsedTimer()   # canli sure (gunluk ozeti yoksa)
        self._zaman = {}                 # {"sure_s", "hiz"} -- panoya yazilir

        self.kosu_karti = self._kosu_karti_kur()
        self.bos = b.BosDurum("play", _("Henüz koşu yok"),
                              _("Çalıştır'a basın; k-eff yakınsaması ve sonuçlar "
                                "bu sayfada görünür."), _("Çalıştır"), "play")
        self.bos.eylem_istendi.connect(self.calistir)
        self.pano = SonucPanosu()
        self.yakinsama = YakinsamaKarti()
        self.entropi_karti = EntropiKarti()
        # Geriye uyumlu adlar (mevcut testler ve ana pencere bunlari kullanir).
        self.keff_etiket = self.pano.k.deger
        self.keff_baslik = self.pano.k.etiket
        self.figur = self.yakinsama.figur
        self.tuval = self.yakinsama.tuval
        self.eksen = self.yakinsama.eksen
        self.eksen_ent = self.entropi_karti.eksen

        from arayuz.guc_harita import GucHaritaWidget
        self.guc_harita = GucHaritaWidget()

        self.kart = self._sonuc_karti_kur()
        self.ayrinti_karti = self._ayrinti_karti_kur()

        grafikler = QtWidgets.QHBoxLayout()
        grafikler.setSpacing(A["l"])
        grafikler.addWidget(self.yakinsama, 5)
        grafikler.addWidget(self.entropi_karti, 3)

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setSpacing(A["l"])
        duzen.addWidget(self.kosu_karti)
        duzen.addWidget(self.bos, 1)
        duzen.addWidget(self.pano)
        duzen.addLayout(grafikler)
        duzen.addWidget(self.guc_harita)
        duzen.addWidget(self.kart)
        duzen.addWidget(self.ayrinti_karti)
        duzen.addStretch(0)

        self._gorunum_guncelle()

    # ==================================================================
    # kurulum (her biri tek bir kart)
    # ==================================================================
    def _kosu_karti_kur(self):
        """Calistir / Durdur / ilerleme + kosu ayarlari + kapi mesaji."""
        self.d_calistir = b.birincil_dugme(_("Çalıştır"), "play",
                                           _("Modeli OpenMC ile çalıştırır (F9)."))
        self.d_durdur = b.ikincil_dugme(_("Durdur"), "square")
        self.d_durdur.setEnabled(False)
        self.d_klasor = b.duz_dugme(_("Klasörü aç"), "folder-open")
        self.d_klasor.setEnabled(False)
        self.d_calistir.clicked.connect(self.calistir)
        self.d_durdur.clicked.connect(self.durdur)
        self.d_klasor.clicked.connect(self.klasoru_ac)
        self.ilerleme = QtWidgets.QProgressBar()
        self.ilerleme.setProperty("metinli", True)
        self.ilerleme.setTextVisible(True)
        self.ilerleme.setRange(0, 1)
        self.ilerleme.setValue(0)
        self.kapi_etiket = QtWidgets.QLabel("-")
        self.kapi_etiket.setWordWrap(True)
        self.kapi_etiket.setObjectName("kucuk")

        kart = b.Kart(_("Koşu"), eylem=self.d_klasor)
        ust = QtWidgets.QHBoxLayout()
        ust.setSpacing(A["s"])
        ust.addWidget(self.d_calistir)
        ust.addWidget(self.d_durdur)
        ust.addWidget(self.ilerleme, 1)
        kart.govde.addLayout(ust)
        kart.govde.addLayout(self._kosu_ayarlari())
        kart.ekle(self.kapi_etiket)
        return kart

    def _kosu_ayarlari(self):
        """Is parcacigi ve kosu dizini satiri (spec["calistirma"])."""
        self.is_parcacigi = tamsayi(8, 1, 512, 1)
        self.is_parcacigi.setMinimumWidth(70)
        n_cekirdek = QtCore.QThread.idealThreadCount()
        self.is_parcacigi.setToolTip(
            _("OpenMP iş parçacığı sayısı (openmc -s N). Bu bilgisayarda %d mantıksal "
              "çekirdek var; tüm çekirdekleri kullanmak arayüzü yavaşlatabilir.")
            % max(n_cekirdek, 1))
        self.kosu_dizini = QtWidgets.QLineEdit()
        self.kosu_dizini.setPlaceholderText("kosu")
        self.kosu_dizini.setToolTip(
            _("Koşu dosyalarının yazılacağı dizin. Göreli yol proje dosyasının "
              "yanına yazılır; her koşuda içi temizlenir."))
        self.dizin_yolu = QtWidgets.QLabel("")
        self.dizin_yolu.setObjectName("kucuk")
        self.dizin_yolu.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.is_parcacigi.valueChanged.connect(self._calistirma_kaydet)
        self.kosu_dizini.editingFinished.connect(self._calistirma_kaydet)
        satir = QtWidgets.QHBoxLayout()
        satir.setSpacing(A["s"])
        for etiket, w, esnek in ((_("İş parçacığı:"), self.is_parcacigi, 0),
                                 (_("Koşu dizini:"), self.kosu_dizini, 1)):
            e = QtWidgets.QLabel(etiket)
            e.setObjectName("ikincil")
            satir.addWidget(e)
            satir.addWidget(w, esnek)
        satir.addWidget(self.dizin_yolu, 2)
        return satir

    def _sonuc_karti_kur(self):
        """Kritiklik yorumu, ozet metni ve (sabit kaynakta) tally tablolari."""
        self.durum_etiket = QtWidgets.QLabel("")
        self.durum_etiket.setWordWrap(True)
        self.durum_etiket.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.ozet_etiket = QtWidgets.QLabel("")
        self.ozet_etiket.setWordWrap(True)
        self.ozet_etiket.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        _yazi_tipi_es_aralikli(self.ozet_etiket, 9.0)
        self.tally_baslik = QtWidgets.QLabel(_("Tally sonuçları"))
        self.tally_baslik.setObjectName("altBaslik")
        self.tally_metin = QtWidgets.QPlainTextEdit()
        self.tally_metin.setReadOnly(True)
        self.tally_metin.setProperty("mono", True)
        self.tally_metin.setMinimumHeight(180)
        _yazi_tipi_es_aralikli(self.tally_metin)
        kart = b.Kart(_("Sonuç"))
        for w in (self.durum_etiket, self.ozet_etiket, self.tally_baslik,
                  self.tally_metin):
            kart.ekle(w)
        return kart

    def _ayrinti_karti_kur(self):
        """Katlanir ayrintili cikti (ham gunluk + tam sonuc metni)."""
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        self.log.setMinimumHeight(200)
        self.log.setProperty("mono", True)
        _yazi_tipi_es_aralikli(self.log)
        self.sonuc_metin = QtWidgets.QPlainTextEdit()
        self.sonuc_metin.setReadOnly(True)
        self.sonuc_metin.setMinimumHeight(160)
        self.sonuc_metin.setProperty("mono", True)
        _yazi_tipi_es_aralikli(self.sonuc_metin)
        self.d_kopyala = b.duz_dugme(_("Kopyala"), "copy")
        self.d_kopyala.clicked.connect(self.gunlugu_kopyala)
        self.ayrinti = GelismisBolum("calistir_ayrinti", _("Ayrıntılı çıktı"))
        self.ayrinti.ekle(QtWidgets.QLabel(_("OpenMC çıktısı")))
        self.ayrinti.ekle(self.log)
        self.ayrinti.ekle(self.d_kopyala)
        self.ayrinti.ekle(QtWidgets.QLabel(
            _("Tam sonuç metni (statepoint ve tüm tally tabloları)")))
        self.ayrinti.ekle(self.sonuc_metin)
        kart = b.Kart()
        kart.ekle(self.ayrinti)
        return kart

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

    def son_kosu_dizini(self):
        """Bu projedeki son BASARILI kosunun mutlak dizini; yoksa None (rapor)."""
        return self._dizin if self._son_basarili and self._dizin else None

    def klasoru_ac(self):
        """Son basarili kosunun dizinini dosya yoneticisinde acar."""
        dizin = self.son_kosu_dizini()
        if not dizin:
            return False
        return QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(dizin))

    def gunlugu_kopyala(self):
        """Ham OpenMC ciktisini panoya kopyalar."""
        QtWidgets.QApplication.clipboard().setText(self.log.toPlainText())
        self.durum.emit(_("OpenMC çıktısı panoya kopyalandı"), True)

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
        self._zaman = {}
        self.log.clear()
        self.sonuc_metin.clear()
        self.tally_metin.clear()
        self.pano.temizle()
        self.pano.dogrulama_ayarla(_("Denetlenmedi"), "notr",
                                   _("Çalıştır'a basınca koşu öncesi doğrulama yapılır."))
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
                self._kapi_yaz(False, _("Önceki projenin koşusu arka planda sürüyor; "
                                        "sonucu bu projeye yazılmayacak. Yeni koşu için "
                                        "Durdur ile sonlandırın."))
            return
        izin, mesaj = self._kapi()
        self.d_calistir.setEnabled(izin)
        self._kapi_yaz(izin, mesaj)

    def _kapi_yaz(self, izin, mesaj):
        self.kapi_etiket.setStyleSheet(
            "color: %s;" % tema.renk("metin_soluk" if izin else "hata"))
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

    def _calistirma_kaydet(self, *_a):
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
            return bool(uygunluk.ayar_alanlari(spec).get("guc_dagilimi"))
        except Exception:
            from cekirdek.gunluk import kaydedici
            kaydedici(__name__).warning("guc dagilimi uygunlugu okunamadi; harita "
                                        "gosteriliyor", exc_info=True)
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
          pano       : kosu surerken, sonuc varken ya da kosu basarisizken
          k-eff karti: sabit kaynakta gizli
          grafikler  : ozdeger modunda, kosu surerken ya da cevrim verisi varken
                       (entropi karti ayrica entropi aciksa)
          sonuc karti: pano ile ayni kosulda
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
        self.pano.setVisible(kart)
        self.pano.k.setVisible(not sabit)
        self.yakinsama.setVisible(grafik)
        self.entropi_karti.setVisible(grafik and bool(self._entropi_grafik))
        self.kart.setVisible(kart)
        tally = sonuc and sabit and bool(self.tally_metin.toPlainText())
        self.tally_baslik.setVisible(tally)
        self.tally_metin.setVisible(tally)
        self.ozet_etiket.setVisible(bool(self.ozet_etiket.text()))
        self.guc_harita.setVisible(sonuc and self._guc_var and self._guc_etkin())
        self.bos.setVisible(not (kart or grafik))
        self.d_klasor.setEnabled(bool(self.son_kosu_dizini()))
        # Ayrintili cikti yalnizca gosterecek bir sey varken (bos bolum gurultudur)
        self.ayrinti_karti.setVisible(kosuyor or bool(self.log.toPlainText())
                                      or bool(self.sonuc_metin.toPlainText()))
        # ayarlar: kosu surerken degistirilemez (suren kosuyu etkilemez, yaniltir)
        for w in (self.is_parcacigi, self.kosu_dizini):
            w.setEnabled(self._surec is None)

    # ==================================================================
    # grafikler
    # ==================================================================
    def _grafik_kur(self, entropi):
        """Entropi kartinin gosterilip gosterilmeyecegini belirler ve temizler."""
        self._entropi_grafik = bool(entropi)
        self.yakinsama.sifirla()
        self.entropi_karti.sifirla()

    def _grafik_guncelle(self):
        if not self._cevrimler:
            return
        pasif = int((self.spec or {}).get("ayarlar", {}).get("pasif", 0) or 0)
        self.yakinsama.ciz(self._cevrimler, pasif)
        if self._entropi_grafik:
            self.entropi_karti.ciz(self._cevrimler, pasif)

    # ==================================================================
    # kosu
    # ==================================================================
    def calistir(self):
        izin, mesaj = self._kapi()
        if not izin:
            QtWidgets.QMessageBox.warning(self, _("Çalıştırılamaz"), mesaj)
            return
        if self._surec is not None:
            return
        self._calistirma_kaydet()           # yazilip Enter'a basilmamis dizin
        dizin = self._kosu_dizini()
        if not self._dogrulama_kapisi():
            return
        self._dizin = dizin

        try:
            kosucu.dizin_hazirla(dizin, temizle=True)
            kosucu.xml_yaz(self.spec, dizin)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, _("Model kurulamadı"), str(e))
            return

        exe = kosucu.openmc_yolu()
        if exe is None:
            QtWidgets.QMessageBox.critical(
                self, _("openmc bulunamadı"),
                _("openmc çalıştırılabilir dosyası PATH'te yok.\n"
                  "Conda ortamının etkin olduğundan emin olun (openmc-env)."))
            return
        self._kosuyu_baslat(exe, dizin)

    def _kosuyu_baslat(self, exe, dizin):
        """Sayfayi kosu durumuna alir ve alt sureci baslatir."""
        self._kosu_kusagi = self._kusak
        self._son_basarili = False
        self._basarisiz = False
        self._durduruldu = False
        self._guc_var = False
        self._zaman = {}
        sabit = self._sabit_mi(self.spec)
        self._gosterilen_sabit = sabit
        self.log.clear()
        self.sonuc_metin.clear()
        self.tally_metin.clear()
        self.ozet_etiket.setText("")
        self.guc_harita.sonuc_ayarla(None, None)
        self.pano.temizle()
        self.keff_etiket.setText(_("koşuyor…"))
        self.durum_etiket.setStyleSheet("")
        self.durum_etiket.setText(
            _("Sabit kaynak — k-eff tanımsız; sonuç tally'lerdir.") if sabit
            else _("Koşu sürüyor; k-eff kümülatif ortalamadır."))
        self._cevrimler = []
        self._tampon = ""
        self._grafik_kur(self._entropi_acik(self.spec) and not sabit)

        toplam = int((self.spec.get("ayarlar") or {}).get("cevrim", 1) or 1)
        self.ilerleme.setRange(0, toplam)
        self.ilerleme.setValue(0)
        self.ilerleme.setFormat(_("%v / %m çevrim"))

        n = int(self.spec.get("calistirma", {}).get("is_parcacigi", 8) or 8)
        self._surec = QtCore.QProcess(self)
        self._surec.setWorkingDirectory(dizin)
        self._surec.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self._surec.readyReadStandardOutput.connect(self._cikti_oku)
        self._surec.finished.connect(self._bitti)
        self._surec.errorOccurred.connect(self._hata)

        self._yaz("# komut: %s -s %d" % (exe, n))
        self._yaz("# dizin: %s\n" % dizin)
        self._sayac.start()
        self._surec.start(exe, ["-s", str(n)])

        self.d_calistir.setEnabled(False)
        self.d_durdur.setEnabled(True)
        self._kapi_yaz(True, _("Koşu sürüyor (%d iş parçacığı) → %s") % (n, dizin))
        self._gorunum_guncelle()
        self.sonuc_degisti.emit()
        self.durum.emit(_("Koşu başladı → %s") % dizin, True)
        self.kosu_durumu_degisti.emit(True)

    # En fazla bu kadar dogrulama hatasi mesaj kutusunda listelenir.
    _KAPI_GOSTERILEN_HATA = 5

    def _dogrulama_kapisi(self):
        """
        Kosu dizini temizlenmeden ONCE tek dogrulama kapisi (dogrula.kapi,
        nukleer veri denetimi dahil). Ana pencerenin izni (self._kapi) 250 ms
        gecikmeli ve veri denetimsizdir; bayat izinle gecersiz bir spec eski
        sonucu silmesin. Sonuc PANODA da gosterilir. DONER True: kosu baslar.
        """
        try:
            bulgular = dogrula.kapi(self.spec, veri_kontrolu=True)
        except dogrula.DogrulamaHatasi as e:
            self.pano.dogrulama_ayarla(_("%d hata") % len(e.bulgular), "hata",
                                       _("Koşu başlatılmadı; önceki sonuç silinmedi."))
            QtWidgets.QMessageBox.warning(self, _("Çalıştırılamaz"),
                                          self._kapi_hata_metni(e))
            return False
        uyari = [b_ for b_ in bulgular if b_.seviye == "uyari"]
        self.pano.dogrulama_ayarla(_("Hata yok"), "uyari" if uyari else "basari",
                                   dogrula.ozet(bulgular))
        return True

    def _kapi_hata_metni(self, e):
        """Dogrulama kapisi mesaj kutusunun metni (ilk birkac hata)."""
        ilk = e.bulgular[:self._KAPI_GOSTERILEN_HATA]
        metin = _("Doğrulama hataları giderilmeden koşu başlatılmaz "
                  "(%d hata); önceki sonuç silinmedi.") % len(e.bulgular)
        metin += "\n\n" + "\n".join("• %s" % b_.mesaj for b_ in ilk)
        if len(e.bulgular) > len(ilk):
            metin += "\n" + _("… ve %d hata daha.") % (len(e.bulgular) - len(ilk))
        return metin

    def durdur(self):
        if self._surec is not None:
            self._durduruldu = True
            self._surec.kill()
            if not self._eski_kosu():
                self._yaz(_("\n# kullanıcı tarafından durduruldu"))

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
            self._satir_isle(satir.rstrip())

    def _satir_isle(self, satir):
        """Tek bir gunluk satiri: loga yaz, cevrim/ilerleme bilgisini cikar."""
        self._yaz(satir)
        bilgi = kosucu.cevrim_satiri(satir)
        if bilgi:
            self._cevrimler.append(bilgi)
            self.ilerleme.setValue(bilgi["cevrim"])
            if len(self._cevrimler) % 5 == 0:
                self._grafik_guncelle()
            if bilgi["ortalama"] is not None:
                self.keff_etiket.setText("%.5f ± %.5f"
                                         % (bilgi["ortalama"], bilgi["sapma"]))
            return
        # Sabit kaynak: " Simulating batch N" (k-eff sutunu yok)
        n = kosucu.sabit_kaynak_cevrimi(satir)
        if n is not None:
            self.ilerleme.setValue(n)

    def _hata(self, kod):
        if self._surec is None:
            return
        if not self._eski_kosu():
            self._yaz(_("\n# Süreç hatası: %s") % self._surec.errorString())
        # Baslatilamayan surec finished() YAYMAZ: dugmeler kilitli kalirdi.
        if kod == QtCore.QProcess.FailedToStart:
            self._bitti(-1, None)

    def _bitti(self, cikis_kodu, _durum):
        eski = self._eski_kosu()
        surec, self._surec = self._surec, None
        if surec is not None:
            surec.deleteLater()
        self.d_durdur.setEnabled(False)
        self.kapi_guncelle()
        self.kosu_durumu_degisti.emit(False)
        if eski:
            # Onceki projenin kosusu: sonucu bu projeye YAZILMAZ.
            self._kosu_kusagi = None
            self._gorunum_guncelle()
            self.durum.emit(_("Önceki projenin koşusu bitti; sonucu bu projeye "
                              "yazılmadı (dosyalar: %s).") % self._dizin, True)
            return
        self._grafik_guncelle()
        self._zaman = self._zamanlama(self.log.toPlainText())
        if self._durduruldu:
            self._durduruldu_goster()
            return
        if cikis_kodu != 0:
            self._basarisiz_goster(_("Koşu başarısız (çıkış kodu %d). OpenMC çıktısı "
                                     "aşağıda, 'Ayrıntılı çıktı' bölümünde.") % cikis_kodu)
            self.durum.emit(_("Koşu başarısız (çıkış kodu %d)") % cikis_kodu, False)
            return
        self._sonucu_oku()

    def _zamanlama(self, gunluk):
        """Gunlukten sure/hiz; gunlukte yoksa canli sayactan sure."""
        z = gunluk_ozeti.ozetle(gunluk)
        if z["sure_s"] is None and self._sayac.isValid():
            z["sure_s"] = self._sayac.elapsed() / 1000.0
        return z

    def _durduruldu_goster(self):
        self._basarisiz = True
        self.keff_etiket.setText(_("durduruldu"))
        self.durum_etiket.setStyleSheet("")
        self.durum_etiket.setText(_("Koşu kullanıcı tarafından durduruldu; sonuç yok."))
        self._gorunum_guncelle()
        self.sonuc_degisti.emit()
        self.durum.emit(_("Koşu durduruldu"), False)

    def _sonucu_oku(self):
        """Kosu 0 ile bitti: statepoint bulunur ve panoya yazilir."""
        sp = kosucu.son_statepoint(self._dizin)
        if sp is None:
            self._basarisiz_goster(_("Koşu bitti ama statepoint dosyası bulunamadı."))
            self.durum.emit(_("Koşu bitti ama statepoint bulunamadı"), False)
            return
        try:
            s = kosucu.sonuc_oku(sp)
        except Exception as e:
            self._basarisiz_goster(_("Sonuç okunamadı: %s") % e)
            self.durum.emit(_("Sonuç okunamadı: %s") % e, False)
            return
        self._sonuc_goster(s, sp)

    def _basarisiz_goster(self, metin):
        self._son_basarili = False
        self._basarisiz = True
        self.pano.temizle()
        self.keff_etiket.setText(_("başarısız"))
        self.durum_etiket.setText(metin)
        self.durum_etiket.setStyleSheet("color: %s; font-weight: bold;"
                                        % tema.renk("hata"))
        self.ayrinti.ac(True)            # hata: ayrintili cikti kendiliginden acilir
        self._gorunum_guncelle()
        self.sonuc_degisti.emit()

    # ==================================================================
    # var olan bir kosu dizinini yukleme (fixture / onceki kosu)
    # ==================================================================
    def kosu_dizinini_yukle(self, dizin):
        """
        Diskteki bir kosu dizinini panoya yukler (kosu.log + son statepoint).
        Kosu BASLATMAZ. DONER True: sonuc gosterildi.
        """
        sp = kosucu.son_statepoint(dizin)
        if sp is None:
            self._basarisiz_goster(_("Koşu dizininde statepoint dosyası yok: %s") % dizin)
            return False
        gunluk = self._gunlugu_oku(dizin)
        self.log.setPlainText(gunluk)
        self._zaman = gunluk_ozeti.ozetle(gunluk)
        self._dizin = dizin
        self._kosu_kusagi = self._kusak
        try:
            s = kosucu.sonuc_oku(sp)
        except Exception as e:
            self._basarisiz_goster(_("Sonuç okunamadı: %s") % e)
            return False
        self._cevrimler = []
        self._sonuc_goster(s, sp)
        return True

    @staticmethod
    def _gunlugu_oku(dizin, ad="kosu.log"):
        """Kosu dizinindeki gunluk metni; okunamazsa bos metin (loglanir)."""
        yol = os.path.join(dizin, ad)
        try:
            with open(yol, encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError:
            from cekirdek.gunluk import kaydedici
            kaydedici(__name__).info("koşu günlüğü okunamadı: %s", yol, exc_info=True)
            return ""

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
        self.pano.sonuc_yaz(s, self.spec, self._zaman)
        ozet = self._sabit_ozeti(s) if sabit else self._ozdeger_ozeti(s)
        ozet += self._guc_ozeti(s)
        tally = self._tally_metinleri(s, sabit)
        tam = ([] if sabit else ["k-eff    = %.5f ± %.5f" % s["keff"]]) + ozet
        tam += ["statepoint: %s" % sp, ""] + tally
        self.ozet_etiket.setText("\n".join(ozet))
        self.sonuc_metin.setPlainText("\n".join(tam))
        self.tally_metin.setPlainText("\n".join(tally) if sabit else "")
        self.guc_harita.sonuc_ayarla(s, self.spec)
        self._guc_var = bool((s.get("guc") or {}).get("faktorler"))
        self._son_basarili = True
        self._basarisiz = False
        self._gorunum_guncelle()
        self.sonuc_degisti.emit()
        if sabit:
            self.durum.emit(_("Koşu tamamlandı (sabit kaynak) — sonuçlar tally'lerde"),
                            True)
        else:
            self.durum.emit(_("Koşu tamamlandı: k-eff = %.5f ± %.5f") % s["keff"], True)

    def _sabit_ozeti(self, s):
        """Sabit kaynak sonucunun ozet satirlari (k-eff tanimsiz)."""
        k_tanim = ((self.spec or {}).get("ayarlar") or {}).get("kaynak") or {}
        kuvvet = float(k_tanim.get("kuvvet") or 1.0)
        self.keff_etiket.setText("-")
        self.durum_etiket.setText(
            _("Sabit kaynak — k-eff tanımsız\nSonuç tally'lerdir (aşağıda)."))
        self.durum_etiket.setStyleSheet("color: %s; font-weight: bold;"
                                        % tema.renk("vurgu"))
        ozet = [
            "mod      = sabit kaynak (k-eff tanımsız)",
            "kaynak   = %s" % _kaynak.ozet(k_tanim),
            "şiddet   = %.4g parçacık/s" % kuvvet,
            "çevrim   = %d, %d parçacık/çevrim" % (s["cevrim"], s["parcacik"]),
            "Sonuçlar akı ve tepkime hızlarıdır; doz hesaplanmaz. Akı hacim-"
            "integrallidir (n·cm/s): ortalama akı [n/cm²/s] için bölgenin "
            "hacmine bölün.",
        ]
        # OLCULDU (kosucu.py): OpenMC sabit kaynak tally'lerini kaynak
        # siddetiyle ZATEN carpar; "siddetle carpin" demek cift sayim olurdu.
        if kuvvet == 1.0:
            ozet.append("NOT: tally değerleri kaynak parçacığı başınadır "
                        "(şiddet 1). Mutlak birim için şiddeti girin.")
        else:
            ozet.append("Not: tally değerleri mutlak birimdedir — OpenMC "
                        "şiddeti zaten uygulamıştır, tekrar çarpmayın.")
        return ozet

    def _ozdeger_ozeti(self, s):
        """Ozdeger sonucunun ozet satirlari (+ kritiklik yorumu, kinetik)."""
        self.keff_etiket.setText("%.5f ± %.5f" % s["keff"])
        kin = s.get("kinetik") or {}
        sonsuz = uygunluk.sonsuz_ortam(self.spec or {})
        self.keff_baslik.setText("k∞" if sonsuz else "k-eff")
        durum, ayrinti = kosucu.keff_yorumu(s["keff"][0], s["keff"][1],
                                            kin.get("beta_eff"), sonsuz=sonsuz)
        self.durum_etiket.setText("%s\n%s" % (durum, ayrinti))
        renk = ("basari" if durum.startswith("Kritik (")
                else ("hata" if "üstü" in durum else "vurgu"))
        self.durum_etiket.setStyleSheet("color: %s; font-weight: bold;" % tema.renk(renk))
        ozet = ["çevrim   = %d (%d pasif), %d parçacık/çevrim"
                % (s["cevrim"], s["pasif"], s["parcacik"])]
        ozet.append(self._kaynak_satiri(s))
        if kin:
            ozet.append("β_eff    = %.1f ± %.1f pcm   (reaktivite birimi: 1 $ = β_eff)"
                        % (kin["beta_eff"] * 1e5, kin["beta_eff_sapma"] * 1e5))
            ozet.append("Λ        = %-22s (nötron üretim zamanı)"
                        % kosucu.lambda_metni(kin["lambda"], kin["lambda_sapma"]))
        return ozet

    def _kaynak_satiri(self, s):
        """Kaynak yakinsamasi degerlendirmesi (Shannon entropisi)."""
        if s.get("entropi"):
            yakinsadi, mesaj = kosucu.entropi_yakinsama(s["entropi"], s["pasif"])
            isaret = {True: "[tamam]", False: "[uyarı]", None: "[  ?  ]"}[yakinsadi]
            if yakinsadi is False:
                self.durum.emit(_("Dikkat: kaynak yakınsamamış olabilir — "
                                  "pasif çevrim sayısını artırın"), False)
            return "kaynak   = %s %s" % (isaret, mesaj)
        if s.get("entropi_hata"):
            return "kaynak   = [  ?  ] " + _("Shannon entropisi okunamadı: %s") \
                % s["entropi_hata"]
        return ("kaynak   = [  ?  ] Shannon entropisi kapalı — "
                "kaynak yakınsaması doğrulanamıyor")

    @staticmethod
    def _guc_ozeti(s):
        """Guc dagilimi ozet satirlari (tepe faktorleri, korunum)."""
        g = s.get("guc") or {}
        gf = g.get("faktorler")
        if not gf:
            return (["güç dağılımı okunamadı: %s" % s["guc_hata"]]
                    if s.get("guc_hata") else [])
        zayif = (gf.get("yanlilik_orani") or 0.0) > 0.3
        ozet = ["F_ΔH     = %.4f   (en yüksek çubuk gücü / ortalama)%s"
                % (gf["F_dH"], "\n           ⚠ istatistik zayıf: bu değer yukarı "
                   "yanlı, güvenilir F_ΔH için Normal ya da Hassas hassasiyetle "
                   "koşun" if zayif else "")]
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
        return ozet + list(kosucu.korunum_satirlari(g))

    def _tally_metinleri(self, s, sabit):
        k_tanim = ((self.spec or {}).get("ayarlar") or {}).get("kaynak") or {}
        tally = []
        for ad, df in s["tallyler"].items():
            tally.append(kosucu.tally_metni(ad, df, s.get("malzeme_adlari"), sabit,
                                            float(k_tanim.get("kuvvet") or 1.0)))
            tally.append("")
        return tally
