# -*- coding: utf-8 -*-
"""
================================================================================
 onizleme.py  --  Canli geometri onizlemesi
================================================================================

 openmc.Model.plot() bir matplotlib Axes'e cizim yapabildigi icin kendi CSG
 cizicimizi yazmiyoruz.

 OLCUM (pwr_17x17, bu makinede)
   Tek seferlik cizim:   200 px -> 632 ms | 400 px -> 255 ms | 1200 px -> 387 ms
   Piksel sayisi neredeyse fark etmiyor. Sebep: Model.plot() her cagrida
   openmc kutuphanesini bastan baslatir ve tesir kesitlerini yeniden okur;
   maliyet BASLATMADA, isin izlemede degil.

   Kutuphane acik tutulursa:
   ilk baslatma 3.3 s, sonra   200 px -> 13 ms | 600 px -> 43 ms | 1200 px -> 162 ms

 BUNDAN CIKAN IKI KARAR
   1. Cozunurluk bedava sayilir -- varsayilan yuksek tutulur, dusurmenin
      anlami yok (taslak cizim denendi, kazanc yalnizca %10 oldu ve kaldirildi).
   2. "Hizli mod" istege bagli bir secenektir:
        KAPALI (varsayilan) : her cizim ~260 ms, spec degisiklikleri ucuz.
                              Model kurarken/duzenlerken dogru secim.
        ACIK                : ilk cizim ~3.3 s, sonraki cizimler ~40 ms.
                              Bitmis bir geometriyi incelerken (eksen degistirme,
                              yakinlastirma) dogru secim.
      Spec degisirse kutuphane yeniden baslatilmak zorundadir; bu yuzden
      duzenleme sirasinda hizli mod ACIK olursa her degisiklik 3.3 s surer.
      Secenegin ipucunda bu acikca yazar.

 3B MODELDE IKI KESIT YAN YANA (dalga 3)
   3B modelde varsayilan gorunum "xy + xz": ustten kesit ve eksenel kesit
   yan yana. 2B modelde yalnizca xy cizilir (xz/yz sonsuz seritlerdir) ve
   gorunum secimi gizlenir. Iki kesit TEK bir openmc.lib oturumunda cizilir
   (TemporarySession, plot kipi '-c': tesir kesiti okunmaz); ikinci kesitin
   ek maliyeti yalnizca isin izlemedir.
   OLCUM (bu makine, 700x600 px, cozunurluk 800, hizli mod kapali; _ciz() +
   tuval cizimi, 5 cizimin ortancasi):
                    tek kesit (once)   xy + xz (sonra)
     pwr_3b              637 ms            816 ms   (+%28)
     pwr_eksenel         663 ms            851 ms   (+%28)
     tamburlu_kor        622 ms            774 ms   (+%24)
     pwr_17x17 (2B)      639 ms            629 ms   (tek kesit, degismedi)
   Iki kesit ayri Model.plot() oturumlariyla ~2 kat surerdi; tek oturumla
   ek maliyet ~%25'tir (300 ms gecikmeli cizimde kabul edilebilir).
   "Hizli mod" ve cozunurluk seyrek gerektigi icin "Gelismis" altindadir.
================================================================================
"""

import atexit
import os
import tempfile
import time
import traceback

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from PySide6 import QtCore, QtWidgets

import openmc

from cekirdek import onbellek, sema
from arayuz.ortak import GelismisBolum

# Cozunurluk secenekleri -- maliyet baslatmada oldugu icin yuksek varsayilan ucuz.
# ("Hizli" adi "Hizli mod" ile karisiyordu: dusuk cozunurluk "Dusuk" oldu.)
COZUNURLUK = [("Düşük (400)", 400), ("Normal (800)", 800), ("Yüksek (1400)", 1400)]

# Gorunum secenekleri (3B modelde). Ogeler eksen adlaridir (xy, xz, yz).
IKILI = "xy + xz"
GORUNUMLER = [IKILI, "xy", "xz", "yz"]
RENKLENDIRME = [("material", "Malzeme"), ("cell", "Hücre")]


class _LibYoneticisi:
    """
    openmc.lib tek bir global orneklemedir; ayni anda yalnizca bir model
    yuklenebilir. Bu sinif hangi modelin yuklu oldugunu takip eder ve
    uygulama kapanirken duzgun kapatilmasini saglar.
    """

    def __init__(self):
        self.model = None
        self.anahtar = None
        self.dizin = None
        atexit.register(self.kapat)

    def hazirla(self, model, anahtar):
        """Verilen model icin kutuphaneyi baslatir (gerekiyorsa yeniden)."""
        if self.anahtar == anahtar and self.model is not None:
            return False                       # zaten hazir
        self.kapat()
        self.dizin = tempfile.mkdtemp(prefix="openmc_arayuz_lib_")
        eski = os.getcwd()
        try:
            os.chdir(self.dizin)
            model.init_lib(output=False)
        finally:
            os.chdir(eski)
        self.model = model
        self.anahtar = anahtar
        return True                            # yeni baslatildi

    def kapat(self):
        if self.model is not None:
            try:
                self.model.finalize_lib()
            except Exception:
                pass
        self.model = None
        self.anahtar = None
        if self.dizin:
            import shutil
            shutil.rmtree(self.dizin, ignore_errors=True)
            self.dizin = None


_LIB = _LibYoneticisi()


class OnizlemeWidget(QtWidgets.QWidget):
    """Geometri kesiti gosteren matplotlib tuvali + denetimler."""

    durum = QtCore.Signal(str, bool)
    olcu_bulundu = QtCore.Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec = None
        self._son_hata = None
        self.son_olcu = None

        self._ikili_varsayilan = None     # son spec 3B miydi (gorunum varsayilani)
        self.son_sure = None              # son cizimin suresi [s]

        # --- denetim satiri ---
        self.eksen = QtWidgets.QComboBox()
        self.eksen.addItems(GORUNUMLER)
        self.eksen.setToolTip("xy: üstten kesit (z = 0) · xz: yandan kesit (y = 0) · "
                              "yz: yandan kesit (x = 0)")
        self.eksen_etiket = QtWidgets.QLabel("Kesit:")
        self.renklendirme = QtWidgets.QComboBox()
        for veri, ad in RENKLENDIRME:
            self.renklendirme.addItem(ad, veri)
        self.cozunurluk = QtWidgets.QComboBox()
        for etiket, _ in COZUNURLUK:
            self.cozunurluk.addItem(etiket)
        self.cozunurluk.setCurrentIndex(1)
        self.gosterge = QtWidgets.QCheckBox("Gösterge")
        self.gosterge.setChecked(True)
        self.hizli_mod = QtWidgets.QCheckBox("Hızlı mod (kütüphaneyi açık tut)")
        self.hizli_mod.setToolTip(
            "KAPALI : her çizim ~0,3 s; model düzenlerken doğru seçim.\n"
            "AÇIK   : ilk çizim ~3 s (tesir kesitleri belleğe yüklenir),\n"
            "         sonraki çizimler ~40 ms.\n\n"
            "Bitmiş bir geometriyi incelerken (kesit değiştirme, yakınlaştırma)\n"
            "açın. DÜZENLERKEN AÇMAYIN: her model değişikliği kütüphaneyi\n"
            "yeniden başlatır ve değişiklik başına ~3 s sürer.")
        self.yenile_dugme = QtWidgets.QPushButton("Yenile")

        ust = QtWidgets.QHBoxLayout()
        ust.setContentsMargins(4, 4, 4, 0)
        ust.addWidget(self.eksen_etiket)
        ust.addWidget(self.eksen)
        ust.addWidget(QtWidgets.QLabel("Renk:"))
        ust.addWidget(self.renklendirme)
        ust.addWidget(self.gosterge)
        ust.addStretch(1)
        ust.addWidget(self.yenile_dugme)

        # --- tuval ---
        self.figur = Figure(figsize=(5, 4), tight_layout=True)
        self.tuval = FigureCanvasQTAgg(self.figur)
        self.eksenler = self.figur.add_subplot(111)
        self.eksenler2 = None             # 3B'de ikinci (xz) kesit
        self.arac_cubugu = NavigationToolbar2QT(self.tuval, self)

        # --- gelismis: cozunurluk + hizli mod ---
        self.gelismis = GelismisBolum("onizleme_gelismis")
        gw = QtWidgets.QWidget()
        gl = QtWidgets.QHBoxLayout(gw)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.addWidget(QtWidgets.QLabel("Çözünürlük:"))
        gl.addWidget(self.cozunurluk)
        gl.addWidget(self.hizli_mod)
        gl.addStretch(1)
        self.gelismis.ekle(gw)

        alt = QtWidgets.QHBoxLayout()
        alt.setContentsMargins(0, 0, 4, 0)
        alt.addWidget(self.arac_cubugu, 1)
        alt.addWidget(self.gelismis, 0, QtCore.Qt.AlignBottom)

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.addLayout(ust)
        duzen.addWidget(self.tuval, 1)
        duzen.addLayout(alt)

        # --- gecikme sayaci ---
        self._sayac = QtCore.QTimer(self)
        self._sayac.setSingleShot(True)
        self._sayac.setInterval(300)
        self._sayac.timeout.connect(self._ciz)

        for w in (self.eksen, self.renklendirme, self.cozunurluk):
            w.currentIndexChanged.connect(lambda *_: self._ciz())
        self.gosterge.toggled.connect(lambda *_: self._ciz())
        self.hizli_mod.toggled.connect(self._hizli_mod_degisti)
        self.yenile_dugme.clicked.connect(lambda *_: self._ciz())

        self._bos_mesaj("Model bekleniyor")

    # ------------------------------------------------------------------
    @staticmethod
    def _uc_boyutlu(spec):
        """Eksenel kesit anlamli mi: 3B model (yukseklik ya da katman)."""
        return bool(sema.kor_yuksekligi(((spec or {}).get("kor")) or {}))

    def spec_ayarla(self, spec):
        self.spec = spec
        # 3B modelde xy ve xz yan yana (eksenel katmanlar xy kesitinde
        # gorunmez); 2B modelde yalnizca xy -- xz/yz sonsuz seritlerdir, secim
        # gizlenir. 2B -> 3B gecisinde gorunum "xy + xz"ye doner; kullanicinin
        # 3B icindeki secimi korunur.
        uc_b = self._uc_boyutlu(spec)
        if uc_b and self._ikili_varsayilan is not True:
            eski = self.eksen.blockSignals(True)
            self.eksen.setCurrentText(IKILI)
            self.eksen.blockSignals(eski)
        self._ikili_varsayilan = uc_b
        self.eksen.setVisible(uc_b)
        self.eksen_etiket.setVisible(uc_b)
        self.iste()

    def gorunum(self):
        """Cizilecek kesitler: ["xy"], ["xy", "xz"], ["xz"]... 2B'de daima ["xy"]."""
        if not self._uc_boyutlu(self.spec):
            return ["xy"]
        secim = self.eksen.currentText()
        return ["xy", "xz"] if secim == IKILI else [secim]

    def iste(self):
        """Cizimi gecikmeli ister; ardarda cagrilar tek cizime duser."""
        self._sayac.start()

    def _hizli_mod_degisti(self, acik):
        if not acik:
            _LIB.kapat()
            self.durum.emit("Hızlı mod kapatıldı", True)
        self._ciz()

    # ------------------------------------------------------------------
    def _bos_mesaj(self, metin, hata=False):
        self.figur.clear()
        self.figur.set_layout_engine("tight")
        self.eksenler = self.figur.add_subplot(111)
        self.eksenler2 = None
        self.eksenler.set_axis_off()
        self.eksenler.text(0.5, 0.5, metin, ha="center", va="center",
                           wrap=True, fontsize=9,
                           color="#c0392b" if hata else "#7f8c8d")
        self.tuval.draw_idle()

    def _ciz(self):
        if self.spec is None:
            self._bos_mesaj("Model bekleniyor")
            return
        # Yeniden girme korumasi: Model.plot() OpenMC kutuphanesini acip
        # kapatiyor. Cizim surerken ikinci bir cizim baslarsa ayni surecte
        # ikinci bir kutuphane oturumu acilmis olur; OpenMC C++ tarafinda bu
        # toparlanamayan bir durumdur ve surec cokebilir. Cizimi atlamak
        # zararsiz -- zamanlayici zaten yeniden tetikliyor.
        if getattr(self, "_ciziliyor", False):
            return
        self._ciziliyor = True
        t0 = time.perf_counter()
        try:
            model, bilgi = onbellek.kur_onbellekli(self.spec)
            gx, gy = bilgi["sinir_kutu"]
            # ------------------------------------------------------------------
            # CIZIM ICIN TALLY'SIZ MODEL
            #   Model.plot() geometriyi dilimlemek icin OpenMC KUTUPHANESINI
            #   baslatiyor ve bu sirada tally'leri de cozmeye calisiyor. Guc
            #   dagilimi tally'sindeki CellFilter cozulemeyince OpenMC C++
            #   tarafinda std::runtime_error atiyor; bu Python'a yakalanabilir
            #   bir istisna olarak gelmiyor, dogrudan terminate() cagrilip
            #   BUTUN UYGULAMA cokuyor (SIGABRT). Olculdu: 3/3 kosuda cokme.
            #
            #   Onizlemenin tally'lere zaten hic ihtiyaci yok: yalnizca
            #   geometri, malzemeler ve sicaklik ayarlari gerekli. Ayni
            #   nesneleri paylasan tally'siz bir kabuk model kullanmak hem bu
            #   cokmeyi hem de ileride eklenecek her tally turunun ayni riski
            #   tasimasini ortadan kaldiriyor.
            # ------------------------------------------------------------------
            if len(model.tallies) > 0:
                model = openmc.Model(geometry=model.geometry,
                                     materials=model.materials,
                                     settings=model.settings)
            piksel = COZUNURLUK[self.cozunurluk.currentIndex()][1]
            kesitler = self.gorunum()
            h = sema.kor_yuksekligi(self.spec["kor"])

            yeniden_baslatildi = False
            if self.hizli_mod.isChecked():
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
                try:
                    yeniden_baslatildi = _LIB.hazirla(model, onbellek.ozet(self.spec))
                finally:
                    QtWidgets.QApplication.restoreOverrideCursor()

            self.figur.clear()
            self.figur.set_layout_engine("tight")
            if len(kesitler) == 2:
                eksenler = [self.figur.add_subplot(1, 2, 1), self.figur.add_subplot(1, 2, 2)]
            else:
                eksenler = [self.figur.add_subplot(111)]
            self.eksenler = eksenler[0]
            self.eksenler2 = eksenler[1] if len(eksenler) > 1 else None
            renk_ver = self.renklendirme.currentData() == "material"
            gosterge_ister = self.gosterge.isChecked() and renk_ver

            # Iki kesit TEK kutuphane oturumunda: Model.plot() kendi
            # TemporarySession'ini, kutuphane zaten aciksa atlar. Hizli modda
            # kutuphane _LIB'de aciktir; bu oturum o zaman da bir sey yapmaz.
            import openmc.lib as _omc_lib
            with _omc_lib.TemporarySession(model, output=False, args=["-c"]):
                for i, (ax, eksen) in enumerate(zip(eksenler, kesitler)):
                    if eksen == "xy":
                        genislik = (gx, gy)
                    else:
                        dikey = h if h else max(gx, gy)
                        genislik = ((gx if eksen == "xz" else gy), dikey)
                    ax.set_axis_on()
                    model.plot(basis=eksen, width=genislik, pixels=(piksel, piksel),
                               color_by=self.renklendirme.currentData(),
                               colors=bilgi["renkler"] if renk_ver else None,
                               legend=gosterge_ister and i == 0,
                               axes=ax)
                    self._eksen_bicimle(ax, eksen, genislik, len(kesitler) == 2)
            if len(kesitler) == 2:
                self.figur.suptitle(self.spec.get("ad", ""), fontsize=9)
            self._gostergeyi_tasi(self.eksenler, len(kesitler) == 2)
            self.tuval.draw_idle()
            self._son_hata = None
            self.son_olcu = (gx, gy)
            self.olcu_bulundu.emit(gx, gy)
            ek = "  [hızlı mod yeniden başlatıldı]" if yeniden_baslatildi else ""
            self.son_sure = time.perf_counter() - t0
            self.durum.emit("Önizleme güncel (%s, %d piksel)%s"
                            % (" + ".join(kesitler), piksel, ek), True)
        except Exception as e:
            self._son_hata = traceback.format_exc()
            self._bos_mesaj("Geometri kurulamadı:\n\n%s" % e, hata=True)
            self.durum.emit("Önizleme başarısız: %s" % e, False)
        finally:
            self._ciziliyor = False

    def _eksen_bicimle(self, ax, eksen, genislik, ikili):
        """Baslik ve en-boy orani. Eksenel kesitte model cok ince ve uzun
        olabilir (or. 21 x 395 cm); 1:1'de okunamaz bir serit olur. Oran 3'u
        asarsa eksen gerilir ve baslikta BELIRTILIR (sessizce carpitmak
        yaniltici olurdu)."""
        oran = genislik[1] / genislik[0] if genislik[0] else 1.0
        gerildi = eksen != "xy" and (oran > 3.0 or oran < 1 / 3.0)
        if gerildi:
            ax.set_aspect("auto")
        kesim = {"xy": "z = 0", "xz": "y = 0", "yz": "x = 0"}[eksen]
        olcu = ("%.3f × %.3f cm" % genislik).replace(".", ",")
        if ikili:
            baslik_ = "%s (%s)   %s" % (eksen, kesim, olcu)
        else:
            baslik_ = "%s   %s" % (self.spec.get("ad", ""), olcu)
        ax.set_title(baslik_ + ("   [ölçek 1:1 DEĞİL]" if gerildi else ""), fontsize=8)
        ax.tick_params(labelsize=7)
        ax.xaxis.label.set_size(8)
        ax.yaxis.label.set_size(8)

    def _gostergeyi_tasi(self, ax, ikili):
        """Model.plot() gostergeyi eksenin SAGINA koyuyor; dar panelde tuvalin
        disina tasip kirpiliyordu. Yatay olarak grafigin ALTINA alinir; iki
        kesitte ikisinin ortak gostergesi figurun altindadir."""
        gosterge = ax.get_legend()
        if gosterge is None:
            return
        etiketler = [t.get_text() for t in gosterge.get_texts()]
        tutamaklar = gosterge.legend_handles
        gosterge.remove()
        ayar = dict(ncol=min(len(etiketler), 4), fontsize=7, frameon=False,
                    handlelength=1.4, columnspacing=1.2)
        if ikili:
            self.figur.legend(tutamaklar, etiketler, loc="lower center", **ayar)
            alt = 0.06 + 0.035 * ((len(etiketler) - 1) // 4)
            self.figur.set_layout_engine("tight", rect=(0, alt, 1, 0.97))
        else:
            ax.legend(tutamaklar, etiketler, loc="upper center",
                      bbox_to_anchor=(0.5, -0.09), **ayar)

    # ------------------------------------------------------------------
    def cizildi_mi(self):
        """Gecerli bir cizim yapildi mi? (CALISTIR kapisi bunu kullanir)"""
        return self.spec is not None and self._son_hata is None

    def son_hata(self):
        return self._son_hata

    def kaydet(self, yol):
        self.figur.savefig(yol, dpi=150, bbox_inches="tight")
        return yol

    def kapat(self):
        """Uygulama kapanirken openmc kutuphanesini serbest birakir."""
        _LIB.kapat()
