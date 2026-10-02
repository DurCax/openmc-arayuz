# -*- coding: utf-8 -*-
"""
sayfa.py -- "Veri ve kütüphaneler" sayfasi (v3 K2).

  Gereksinimler : OpenMC ikilisi + surumu, Python API, HDF5, tesir kesiti
                  kutuphanesi, tukenme zinciri -- tek ekranda durum
                  (cekirdek/veri_bilgi.gereksinimler).
  Klasor sec    : cross_sections.xml iceren klasor (ya da dosyanin kendisi)
                  denetlenir (nuklid / termal / foton sayisi, S(a,b), ornek
                  sicakliklar, eksik dosyalar) ve uygun ise secim kaydedilir
                  (cekirdek/veri_yolu.ayar_yaz). Zincir dosyasi ayrica secilir.
  Indir         : indirme_karti.IndirmeKarti (arka planda, iptal, surdurme).

Secim degisince `veri_degisti` yayilir; kayit.py surec ortamini gunceller ve
dogrulamayi yeniler. Ilk acilista (veri yokken) ustte bir bant ve "Başlangıç
ekranına geç" dugmesi gorunur (`baslangica_don`).
"""

import os

from PySide6 import QtCore, QtWidgets

from arayuz import bilesenler as b
from arayuz.sekme_duzen import sayfa_basligi, sayfa_duzeni
from arayuz.tasarim import tokenlar
from arayuz.veri.indirme_karti import IndirmeKarti
from arayuz.veri.isci import ArkaPlanIsi
from cekirdek import veri_bilgi, veri_yolu
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)
A = tokenlar.ARALIK
_ROZET = {"tamam": ("basari", "✓"), "uyari": ("uyari", "!"), "eksik": ("hata", "✗")}
KILAVUZ_BOLUMU = "nukleer-veri"            # arayuz.yardim.BOLUMLER (01-kurulum.md 1.3)
KAPANIS_BEKLEME_MS = 5000                  # kapanista arka plan isleri icin ust sinir
_EN_COK_SAB = 8                           # ozette gosterilen S(a,b) adi sayisi


def _satir(*widgetlar, esnek=None):
    w = QtWidgets.QWidget()
    d = QtWidgets.QHBoxLayout(w)
    d.setContentsMargins(0, 0, 0, 0)
    d.setSpacing(A["s"])
    for i, x in enumerate(widgetlar):
        d.addWidget(x, 1 if i == esnek else 0)
    return w


class GereksinimKarti(b.Kart):
    """Gereksinim tablosu: rozet + ad + deger + oneri."""

    def __init__(self, parent=None):
        self.d_yenile = b.duz_dugme(_("Yenile"), "refresh-cw")
        super().__init__(_("Gereksinimler"), _("Koşu için gerekenlerin durumu."),
                         eylem=self.d_yenile, parent=parent)
        self._izgara_w = QtWidgets.QWidget()
        self._izgara = QtWidgets.QGridLayout(self._izgara_w)
        self._izgara.setContentsMargins(0, 0, 0, 0)
        self._izgara.setHorizontalSpacing(A["m"])
        self._izgara.setVerticalSpacing(A["xs"])
        self._izgara.setColumnStretch(2, 1)
        self.ekle(self._izgara_w)
        self.durum_etiketi = QtWidgets.QLabel(_("Denetleniyor…"))
        self.durum_etiketi.setObjectName("kucuk")
        self.ekle(self.durum_etiketi)
        self.satirlar = ()
        self._is = None

    def yenile(self, tazele: bool = False) -> None:
        """Gereksinimleri ARKA PLANDA denetler (openmc --version, h5py); surum
        onbellektedir, `tazele` (Yenile dugmesi) onbellegi bosaltir."""
        if self._is is not None:
            return
        self.durum_etiketi.setText(_("Denetleniyor…"))
        self.durum_etiketi.setVisible(True)
        self._is = ArkaPlanIsi(lambda: veri_bilgi.gereksinimler(tazele=tazele), self)
        self._is.bitti.connect(self._bitti)
        self._is.basarisiz.connect(self._basarisiz)
        self._is.start()

    def _is_birak(self):
        isci, self._is = self._is, None
        if isci is not None:
            isci.wait()
            isci.deleteLater()

    def _bitti(self, satirlar):
        self._is_birak()
        self.durum_etiketi.setVisible(False)
        self.doldur(satirlar)

    def _basarisiz(self, metin):
        self._is_birak()
        self.durum_etiketi.setText(metin)

    def bekle(self, ms: int = KAPANIS_BEKLEME_MS) -> bool:
        return self._is.wait(ms) if self._is is not None else True

    def doldur(self, satirlar):
        while self._izgara.count():
            oge = self._izgara.takeAt(0)
            if oge.widget() is not None:
                oge.widget().deleteLater()
        self.satirlar = tuple(satirlar)
        for i, g in enumerate(self.satirlar):
            tur, isaret = _ROZET.get(g.durum, ("notr", "?"))
            self._izgara.addWidget(b.Rozet(isaret, tur), i, 0)
            ad = QtWidgets.QLabel(g.ad)
            ad.setObjectName("govdeVurgulu")
            self._izgara.addWidget(ad, i, 1)
            deger = QtWidgets.QLabel(g.deger + (("\n" + g.oneri) if g.oneri else ""))
            deger.setObjectName("mono" if g.durum == "tamam" else "ikincil")
            deger.setWordWrap(True)
            deger.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            self._izgara.addWidget(deger, i, 2)


class KlasorKarti(b.Kart):
    """Var olan kutuphane klasorunu ve zincir dosyasini secer."""

    secildi = QtCore.Signal()
    durum = QtCore.Signal(str, bool)
    denetlendi = QtCore.Signal(object)        # KutuphaneDenetimi

    def __init__(self, parent=None):
        self._is = None
        super().__init__(_("Klasör seç"),
                         _("Bilgisayarınızda zaten bir kütüphane varsa cross_sections.xml "
                           "içeren klasörü seçin."), parent=parent)
        self.yol = QtWidgets.QLineEdit()
        self.yol.setAccessibleName(_("Kütüphane klasörü"))
        self.yol.setPlaceholderText(_("…/endfb-viii.0-hdf5"))
        self.d_gozat = b.ikincil_dugme(_("Gözat…"), "folder-open")
        self.d_gozat.clicked.connect(self._gozat)
        self.d_kullan = b.birincil_dugme(_("Denetle ve kullan"), "check")
        self.d_kullan.clicked.connect(self.kullan)
        self.yol.returnPressed.connect(self.kullan)
        self.ekle(_satir(self.yol, self.d_gozat, self.d_kullan, esnek=0))
        self.ozet = QtWidgets.QLabel()
        self.ozet.setWordWrap(True)
        self.ozet.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.ozet.setVisible(False)
        self.ekle(self.ozet)
        self.zincir = QtWidgets.QLineEdit()
        self.zincir.setAccessibleName(_("Tükenme zinciri dosyası"))
        self.zincir.setPlaceholderText(_("…/chain/chain_endfb80_thermal.xml"))
        self.d_zincir_gozat = b.ikincil_dugme(_("Gözat…"), "folder-open")
        self.d_zincir_gozat.clicked.connect(self._zincir_gozat)
        self.d_zincir = b.ikincil_dugme(_("Zinciri kullan"), "check")
        self.d_zincir.clicked.connect(self.zincir_kullan)
        self.ekle(b.BolumBasligi(_("Tükenme zinciri"),
                                 aciklama=_("Termal zincirin yanındaki hızlı ve CASL "
                                            "zincirleri aynı klasörden okunur.")))
        self.ekle(_satir(self.zincir, self.d_zincir_gozat, self.d_zincir, esnek=0))

    def yenile(self):
        xs, z = veri_yolu.cross_sections(), veri_yolu.zincir()
        if not self.yol.text() and xs.deger:
            self.yol.setText(os.path.dirname(xs.deger))
        if not self.zincir.text() and z.deger:
            self.zincir.setText(z.deger)

    def _gozat(self):
        dizin = QtWidgets.QFileDialog.getExistingDirectory(
            self, _("Kütüphane klasörü"), self.yol.text() or os.path.expanduser("~"))
        if dizin:
            self.yol.setText(dizin)
            self.kullan()

    def _zincir_gozat(self):
        yol, _s = QtWidgets.QFileDialog.getOpenFileName(
            self, _("Tükenme zinciri"), self.zincir.text() or os.path.expanduser("~"),
            _("Zincir (*.xml)"))
        if yol:
            self.zincir.setText(yol)
            self.zincir_kullan()

    @staticmethod
    def ozet_metni(d):
        if d.xml is None or d.hatalar and not d.notron:
            return "\n".join(d.hatalar)
        sic = ", ".join("%s %d–%d K" % (ad, a[0], a[1]) for ad, a in d.sicakliklar)
        sab = ", ".join(d.sab[:_EN_COK_SAB]) + (" …" if len(d.sab) > _EN_COK_SAB else "")
        satirlar = [_("%d nötron nüklidi · %d S(α,β) tablosu · %d foton elementi")
                    % (d.notron, d.termal, d.foton)]
        if sic:
            satirlar.append(_("Sıcaklıklar: %s") % sic)
        if sab:
            satirlar.append(_("S(α,β): %s") % sab)
        return "\n".join(satirlar + list(d.hatalar))

    def kullan(self) -> bool:
        """Klasoru ARKA PLANDA denetler (h5 okuma, her kaydin dosyasi); bitince
        uygunsa secim kaydedilir ve `denetlendi` yayilir. Doner: basladi mi."""
        if self._is is not None:
            return False
        yol = self.yol.text().strip()
        self.d_kullan.setEnabled(False)
        self.ozet.setText(_("Denetleniyor…"))
        self.ozet.setVisible(True)
        self._is = ArkaPlanIsi(lambda: veri_bilgi.klasor_denetle(yol), self)
        self._is.bitti.connect(self._denetim_bitti)
        self._is.basarisiz.connect(self._denetim_basarisiz)
        self._is.start()
        return True

    def _is_birak(self):
        isci, self._is = self._is, None
        self.d_kullan.setEnabled(True)
        if isci is not None:
            isci.wait()
            isci.deleteLater()

    def _denetim_basarisiz(self, metin):
        self._is_birak()
        self.ozet.setText(metin)
        self.durum.emit(metin, False)

    def bekle(self, ms: int = KAPANIS_BEKLEME_MS) -> bool:
        return self._is.wait(ms) if self._is is not None else True

    def _denetim_bitti(self, d):
        self._is_birak()
        self._uygula(d)
        self.denetlendi.emit(d)

    def _uygula(self, d):
        self.ozet.setText(self.ozet_metni(d))
        if not d.tamam:
            self.durum.emit(_("Bu klasör kullanılamaz: %s") % "; ".join(d.hatalar), False)
            return d
        try:
            # Elle secilen klasorun katalog kimligi bilinmez: eski kimlik silinir.
            veri_yolu.ayar_yaz({"cross_sections": d.xml, "kutuphane": None})
        except (OSError, ValueError) as e:
            _log.warning("kutuphane secimi yazilamadi", exc_info=True)
            self.durum.emit(_("Seçim kaydedilemedi: %s") % e, False)
            return d
        self.durum.emit(_("Kütüphane seçildi: %s") % d.xml, True)
        self.secildi.emit()
        return d

    def zincir_kullan(self):
        yol = self.zincir.text().strip()
        tamam, mesaj, _n = veri_bilgi.zincir_kontrol(yol)
        if not tamam or not os.path.isabs(yol):
            self.durum.emit(_("Zincir kullanılamaz: %s") % mesaj, False)
            return False
        try:
            veri_yolu.ayar_yaz({"zincir": os.path.abspath(yol)})
        except (OSError, ValueError) as e:
            _log.warning("zincir secimi yazilamadi", exc_info=True)
            self.durum.emit(_("Seçim kaydedilemedi: %s") % e, False)
            return False
        self.durum.emit(_("Zincir seçildi: %s") % yol, True)
        self.secildi.emit()
        return True


class VeriSayfasi(QtWidgets.QWidget):
    """Kenar cubugundaki "Veri" sayfasi (modul belgesi)."""

    veri_degisti = QtCore.Signal()
    baslangica_don = QtCore.Signal()
    durum = QtCore.Signal(str, bool)

    def __init__(self, katalog=None, politika=None, parent=None):
        super().__init__(parent)
        kok = sayfa_duzeni(self)
        kok.addWidget(sayfa_basligi(
            _("Veri ve kütüphaneler"),
            _("OpenMC tesir kesiti kütüphanesi ve tükenme zinciri olmadan koşu yapılamaz. "
              "Var olan bir klasörü seçin ya da openmc.org'dan indirin.")))
        self.d_kilavuz = b.baglanti_dugmesi(_("Kılavuz: Nükleer veri ve tükenme zinciri"))
        self.d_kilavuz.clicked.connect(self._kilavuz)
        kok.addWidget(self.d_kilavuz, 0, QtCore.Qt.AlignLeft)
        self.bant = self._bant_kur()
        kok.addWidget(self.bant)
        self.ortam_notu = QtWidgets.QLabel()
        self.ortam_notu.setObjectName("ikincil")
        self.ortam_notu.setWordWrap(True)
        kok.addWidget(self.ortam_notu)
        self.gereksinim = GereksinimKarti()
        self.gereksinim.d_yenile.clicked.connect(lambda: self.yenile(tazele=True))
        self.klasor = KlasorKarti()
        self.indirme = IndirmeKarti(katalog=katalog, politika=politika)
        for k in (self.gereksinim, self.klasor, self.indirme):
            kok.addWidget(k)
        kok.addStretch(1)
        self.klasor.secildi.connect(self._secim_degisti)
        self.indirme.kuruldu.connect(lambda _s: self._secim_degisti())
        self.klasor.durum.connect(self.durum)
        self.indirme.durum.connect(self.durum)
        self.yenile()

    def _bant_kur(self):
        bant = b.Kart(_("Başlamadan önce: nükleer veri"),
                      _("Bu bilgisayarda OpenMC nükleer veri kütüphanesi bulunamadı. Aşağıdan "
                        "bir klasör seçin ya da bir kütüphane indirin; sonra başlangıç "
                        "ekranından modelinizi kurun."))
        self.d_baslangic = b.ikincil_dugme(_("Başlangıç ekranına geç"), "house")
        self.d_baslangic.clicked.connect(self.baslangica_don)
        bant.eylem_ekle(self.d_baslangic)
        bant.setVisible(False)
        return bant

    def _kilavuz(self):
        from arayuz import yardim
        return yardim.ac(KILAVUZ_BOLUMU, self.window())

    def ilk_acilis_goster(self, goster=True):
        self.bant.setVisible(bool(goster))

    def yenile(self, tazele: bool = False) -> None:
        """Gereksinimler (arka planda) ve secimler yeniden okunur."""
        self.gereksinim.yenile(tazele=tazele)
        self.klasor.yenile()
        xs = veri_yolu.cross_sections()
        notlar = {
            "ortam": _("OPENMC_CROSS_SECTIONS ortam değişkeni ayarlı ve önceliklidir: burada "
                       "yapılan seçim, değişken kaldırılana dek kullanılmaz."),
            "coklu": _("Birden çok kütüphane bulundu (%s); hangisinin kullanılacağını Klasör "
                       "seç ile belirleyin.") % ", ".join(
                os.path.basename(os.path.dirname(a)) for a in xs.adaylar),
            "aday": _("Kütüphane otomatik bulundu (%s); doğruysa 'Denetle ve kullan' ile "
                      "onaylayın.") % (xs.deger or ""),
        }
        self.ortam_notu.setVisible(xs.kaynak in notlar)
        self.ortam_notu.setText(notlar.get(xs.kaynak, ""))
        if veri_yolu.veri_hazir_mi():
            self.ilk_acilis_goster(False)

    def _secim_degisti(self):
        self.yenile()
        self.veri_degisti.emit()

    def bekle(self, ms: int = KAPANIS_BEKLEME_MS) -> bool:
        """Arka plan islerini bekler (ust sinir ms)."""
        return all([self.gereksinim.bekle(ms), self.klasor.bekle(ms), self.indirme.bekle(ms)])

    def kapat(self) -> bool:
        """Pencere kapanisi / aboutToQuit: suren indirme iptal edilir (yarim
        dosya kalir, sonra surdurulur), isler en fazla KAPANIS_BEKLEME_MS
        beklenir. Doner: hepsi bitti mi (False ise log'a yazilir)."""
        self.indirme.iptal()
        bitti = self.bekle(KAPANIS_BEKLEME_MS)
        if not bitti:
            _log.warning("veri sayfasi arka plan isleri %d ms'de bitmedi", KAPANIS_BEKLEME_MS)
        return bitti
