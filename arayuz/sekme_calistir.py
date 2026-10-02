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
   sonuc karti   : kritiklik yorumu, kayip parcacik / OpenMC uyarilari (M5),
                   ozet (sabit kaynakta tally'ler)
   uygunluk      : uygunluk denetimi bulgulari ve profil secimi
                   (arayuz/uygunluk_paneli.py; secim spec["calistirma"]'da)
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
from cekirdek import dogrula, rapor_uygunluk, sema, uygunluk
from cekirdek.ceviri import _, _n
from cekirdek.gunluk import kaydedici
from arayuz import bilesenler as b
from arayuz import tema
from arayuz.calistir import cikti, gunluk_ozeti
from arayuz.calistir.kartlar import AyrintiCekmecesi, KosuKarti, SonucKarti
from arayuz.calistir.pano import SonucPanosu
from arayuz.calistir.sonuc_gosterimi import SonucGosterimiMixin
from arayuz.calistir.yakinsama import EntropiKarti, YakinsamaKarti
from arayuz.tasarim import tokenlar
from arayuz.uygunluk_paneli import UygunlukPaneli
from arayuz.yardim_baglanti import yardim_dugmesi

A = tokenlar.ARALIK
_log = kaydedici(__name__)
# Canli kosuda grafik her bu kadar cevrimde bir yeniden cizilir.
_GRAFIK_ADIMI = 5


class CalistirSekmesi(SonucGosterimiMixin, QtWidgets.QWidget):
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
        self._kapi = lambda: (False, _("hazır değil"))
        self._surec = None
        self._dizin = None
        self._tampon = ""
        self._gunluk = []                # QProcess ham ciktisi -> kosu.log
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

        self._kartlari_kur()
        self._yerlesim_kur()
        self._gorunum_guncelle()

    # ==================================================================
    # kurulum (kartlar arayuz/calistir/ altinda)
    # ==================================================================
    def _kartlari_kur(self):
        """Kartlari kurar; eski ozellik adlari (testler, ana pencere) korunur."""
        self.kosu_karti = KosuKarti()
        k = self.kosu_karti
        k.eylem_ekle(yardim_dugmesi("calistir", k))
        self.d_calistir, self.d_durdur, self.d_klasor = k.d_calistir, k.d_durdur, k.d_klasor
        self.ilerleme, self.kapi_etiket = k.ilerleme, k.kapi_etiket
        self.is_parcacigi, self.kosu_dizini = k.is_parcacigi, k.kosu_dizini
        self.dizin_yolu = k.dizin_yolu
        self.d_calistir.clicked.connect(self.calistir)
        self.d_durdur.clicked.connect(self.durdur)
        self.d_klasor.clicked.connect(self.klasoru_ac)
        self.is_parcacigi.valueChanged.connect(self._calistirma_kaydet)
        self.kosu_dizini.editingFinished.connect(self._calistirma_kaydet)

        self.bos = b.BosDurum("play", _("Henüz koşu yok"),
                              _("Çalıştır'a basın; k-eff yakınsaması ve sonuçlar "
                                "bu sayfada görünür."), _("Çalıştır"), "play")
        self.bos.eylem_istendi.connect(self.calistir)
        self.pano = SonucPanosu()
        self.yakinsama = YakinsamaKarti()
        self.entropi_karti = EntropiKarti()
        self.keff_etiket, self.keff_baslik = self.pano.k.deger, self.pano.k.etiket
        self.figur, self.tuval = self.yakinsama.figur, self.yakinsama.tuval
        self.eksen, self.eksen_ent = self.yakinsama.eksen, self.entropi_karti.eksen

        from arayuz.guc_harita import GucHaritaWidget
        self.guc_harita = GucHaritaWidget()
        self.guc_karti = b.Kart()
        self.guc_karti.ekle(self.guc_harita)
        from arayuz.sonuc.spektrum import SpektrumKarti     # Y3: kendi gorunurlugu
        self.spektrum_karti = SpektrumKarti()
        from arayuz.sonuc.yuzey import YuzeyKarti           # Y7: kendi gorunurlugu
        self.yuzey_karti = YuzeyKarti()

        self.kart = SonucKarti()
        self.durum_etiket, self.ozet_etiket = self.kart.durum_etiket, self.kart.ozet_etiket
        self.tally_baslik, self.tally_metin = self.kart.tally_baslik, self.kart.tally_metin
        self.uygunluk = UygunlukPaneli()
        self.uygunluk.profiller_degisti.connect(self._profiller_degisti)
        self.uygunluk.git_istendi.connect(self._sayfaya_git)
        self.uygunluk.tally_eklensin.connect(self._tally_ekle)

        self.ayrinti_karti = AyrintiCekmecesi()
        c = self.ayrinti_karti
        self.log, self.sonuc_metin, self.ayrinti = c.log, c.sonuc_metin, c.ayrinti
        self.d_kopyala = c.d_kopyala
        self.d_kopyala.clicked.connect(self.gunlugu_kopyala)

    def _yerlesim_kur(self):
        """Yukaridan asagiya tek akis (maket: sonuclar_*)."""
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
        duzen.addWidget(self.guc_karti)
        duzen.addWidget(self.spektrum_karti)
        duzen.addWidget(self.yuzey_karti)
        duzen.addWidget(self.kart)
        duzen.addWidget(self.uygunluk)
        duzen.addWidget(self.ayrinti_karti)
        duzen.addStretch(0)

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
        self.uygunluk.profilleri_ayarla(rapor_uygunluk.secili_profiller(spec))
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
        self._gunluk = []
        self.kart.cikti_yaz([])
        self.uygunluk.temizle()
        self.ilerleme.setRange(0, 1)
        self.ilerleme.setValue(0)
        self.ilerleme.resetFormat()
        self._grafik_kur(self._entropi_acik(self.spec))
        self.guc_harita.sonuc_ayarla(None, None)
        self.spektrum_karti.goster(None)
        self.yuzey_karti.goster(None)
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
        if not degisen:
            return
        c.update(yeni)
        # Yol etiketi YENI dizinle (eskiden guncellemeden once yaziliyor, bir
        # duzenleme geriden geliyordu).
        self._dizin_yolu_guncelle()
        self.degisti.emit(self.KONU)

    def _profiller_degisti(self, profiller):
        """Uygunluk profilleri -> spec["calistirma"] (editor sozlesmesi: yerinde
        yazilir, degisti(KONU) ile kirli/gecmis isler); sonuc varsa yeniden denetler."""
        if self.spec is None:
            return
        c = self.spec.setdefault("calistirma", {})
        c[rapor_uygunluk.SPEC_ANAHTARI] = list(profiller)
        self.degisti.emit(self.KONU)
        if self._son_basarili and self._dizin:
            self.uygunluk.denetle(self.spec, self._dizin)

    def _tally_ekle(self, tally):
        """Uygunluk panelinin ONAYLANMIS tally onerisi (EALF) -> spec["tallyler"]
        (editor sozlesmesi: yerinde; ayni adli GECERLI tally varsa eklenmez; ayni
        adli ama EALF icin kullanilamayan tally -- elle eklenmis -- yenisiyle degisir)."""
        from cekirdek.vv import aoa
        if self.spec is None:
            return
        liste = self.spec.setdefault("tallyler", [])
        ayni = [i for i, t in enumerate(liste) if t.get("ad") == tally.get("ad")]
        if ayni and not (tally.get("ad") == aoa.EALF_TALLY
                         and not aoa.ealf_tanimi_gecerli(liste[ayni[0]])):
            return
        for i in reversed(ayni):
            del liste[i]
        liste.append(dict(tally))
        self.degisti.emit("genel")
        self.uygunluk.d_ealf.hide()

    def _sayfaya_git(self, anahtar):
        """Uygunluk bulgusunun sayfasi (ana pencere varsa)."""
        hedef = getattr(self.window(), "sekmeye_git", None)
        if hedef is not None:
            hedef(anahtar)

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
            _log.warning("guc dagilimi uygunlugu okunamadi; harita gosteriliyor",
                         exc_info=True)
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
        self.uygunluk.setVisible(sonuc)
        tally = sonuc and sabit and bool(self.tally_metin.toPlainText())
        self.tally_baslik.setVisible(tally)
        self.tally_metin.setVisible(tally)
        self.ozet_etiket.setVisible(bool(self.ozet_etiket.text()))
        self.guc_karti.setVisible(sonuc and self._guc_var and self._guc_etkin())
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
        self.kart.cikti_yaz([])
        self.uygunluk.temizle()
        self.guc_harita.sonuc_ayarla(None, None)
        self.spektrum_karti.goster(None)
        self.yuzey_karti.goster(None)
        self.pano.temizle()
        self.keff_etiket.setText(_("koşuyor…"))
        self.durum_etiket.setStyleSheet("")
        self.durum_etiket.setText(
            _("Sabit kaynak — k-eff tanımsız; sonuç tally'lerdir.") if sabit
            else _("Koşu sürüyor; k-eff kümülatif ortalamadır."))
        self._cevrimler = []
        self._tampon = ""
        self._gunluk = []
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

        self._yaz(_("# komut: %s -s %d") % (exe, n))
        self._yaz(_("# dizin: %s") % dizin + "\n")
        self._sayac.start()
        self._surec.start(exe, ["-s", str(n)])

        self.d_calistir.setEnabled(False)
        self.d_durdur.setEnabled(True)
        self._kapi_yaz(True, _n("Koşu sürüyor (%d iş parçacığı) → %s",
                                "Koşu sürüyor (%d iş parçacığı) → %s", n) % (n, dizin))
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
            self.pano.dogrulama_ayarla(_n("%d hata", "%d hata", len(e.bulgular))
                                       % len(e.bulgular), "hata",
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
        metin = _n("Doğrulama hataları giderilmeden koşu başlatılmaz "
                   "(%d hata); önceki sonuç silinmedi.",
                   "Doğrulama hataları giderilmeden koşu başlatılmaz "
                   "(%d hata); önceki sonuç silinmedi.", len(e.bulgular)) % len(e.bulgular)
        metin += "\n\n" + "\n".join("• %s" % b_.mesaj for b_ in ilk)
        if len(e.bulgular) > len(ilk):
            kalan = len(e.bulgular) - len(ilk)
            metin += "\n" + _n("… ve %d hata daha.", "… ve %d hata daha.", kalan) % kalan
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
        self._gunluk.append(satir)
        bilgi = kosucu.cevrim_satiri(satir)
        if bilgi:
            self._cevrimler.append(bilgi)
            self.ilerleme.setValue(bilgi["cevrim"])
            if len(self._cevrimler) % _GRAFIK_ADIMI == 0:
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
        if self._tampon:                 # son satir "\n" ile bitmemis olabilir
            self._satir_isle(self._tampon.rstrip())
            self._tampon = ""
        self._grafik_guncelle()
        self._zaman = self._zamanlama(self.log.toPlainText())
        cikti.gunlugu_yaz(self._dizin, self._gunluk)    # rapor, K3, M5 bunu okur
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
        self._durum_yaz(metin, "hata")
        self.ayrinti.ac(True)            # hata: ayrintili cikti kendiliginden acilir
        self._gorunum_guncelle()
        self.sonuc_degisti.emit()
