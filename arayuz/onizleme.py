# -*- coding: utf-8 -*-
"""
================================================================================
 onizleme.py  --  Canli geometri onizlemesi (v3 H2: arka plan cizim motoru)
================================================================================

 MIMARI
   Cizim AYRI bir kalici surecte yapilir (cekirdek/cizim_sureci.py; istemci:
   arayuz/onizleme_istemci.py). Widget istegi gonderir ve HEMEN doner; isci
   openmc.lib.slice_data ile id haritasini uretir, widget onu kendi renkleriyle
   boyar (arayuz/onizleme_boyama.py) ve tuvale koyar. Ana is parcacigi yalniz
   boyama + matplotlib cizimini yapar (kesit basina onlarca ms).
     - Yeni istek eskisini iptal eder; eski istegin yaniti atilir.
     - Model degismedikce iscinin openmc.lib oturumu ACIK kalir: kesit, renk,
       cozunurluk degisimi yalniz dilimleme maliyetidir (eski "hizli mod"
       secenegi bu yuzden kalkti).
     - Kesitler tek tek gelir (isci aralarda iptali denetler); tuval tek sefer,
       son yanitta cizilir. xz yalniz gorunumde istenirse dilimlenir.
     - GIZLIYKEN CIZMEZ (panel daraltildi ya da sag panel kapali): yalniz
       "kontrol" istegi gider (kur + init), Calistir kapisi gene bilgilidir;
       gorunur olunca cizilir.
     - Isci coker ya da baslatilamazsa acik hata gosterilir, kapi kapanir,
       isci yeniden baslatilir; arayuz donmaz.

 OLCUM (xy + xz, 800 px, sicak isci; .h2_olcum/olc_sonra.py, 02.10.2026)
                  once (Model.plot, ana is parcacigi)   sonra (istek -> son, en uzun donma)
   sfr_met1000_kor        10.8 s donma                      1.6 s, 108 ms
   vver1000_kor            2.9 s donma                      1.4 s, 121 ms
   pwr_beavrs_kor          0.7 s donma                      0.5 s, 116 ms
   Renk/gosterge/gorunum degisimi eldeki dilimden yeniden boyanir (~0.15 s).
   1400 px'te tam gorunum seyreltilir (_goruntu_koy), yakinlastirinca tam.

 3B MODELDE IKI KESIT YAN YANA
   3B modelde varsayilan gorunum "xy + xz"; 2B modelde yalnizca xy cizilir
   (xz/yz sonsuz seritlerdir) ve gorunum secimi gizlenir.

 GELISMIS GEOMETRI (Dalga G-3; arayuz/onizleme_vurgu.py)
   Sol tik noktadaki hucreyi openmc.Geometry.find ile bulur; GeometriDizini onu
   agactaki dugume cevirir ve dugum_secildi(yol) yayilir. vurgula(yol): "Hucre"
   renklendirmesinde secili dugumun hucreleri vurgu, digerleri soluk; "Malzeme"
   renklendirmesinde secili olmayan bolge yari saydam soluk ortuyle ortulur ve
   sinirina vurgu kontur cizilir (iscinin id haritasi; onizleme_secim.py).
================================================================================
"""

import html
import time

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from PySide6 import QtCore, QtWidgets

from cekirdek import cizim_sureci as cs
from cekirdek import onbellek, sema
from cekirdek.ceviri import _, _n, N_
from cekirdek.gunluk import kaydedici
from arayuz import onizleme_boyama as boyama
from arayuz import tema
from arayuz.onizleme_istemci import CizimIstemcisi
from arayuz.onizleme_kapsam import KapsamMixin, TAM_MODEL, kullanilan_gosterge
from arayuz.onizleme_vurgu import VurguMixin
from arayuz.ortak import GelismisBolum
from arayuz.tasarim import tokenlar

_log = kaydedici(__name__)
A = tokenlar.ARALIK

# Etiketler yalniz isaretlenir (N_); kutuya _() ile yazilir, secim INDEKSLE okunur.
COZUNURLUK = [(N_("Düşük (400)"), 400), (N_("Normal (800)"), 800),
              (N_("Yüksek (1400)"), 1400)]

IKILI = "xy + xz"
GORUNUMLER = [IKILI, "xy", "xz", "yz"]
RENKLENDIRME = [("material", N_("Malzeme")), ("cell", N_("Hücre"))]   # veri, gorunen ad
_GECIKME_MS = 300                 # ardisik degisiklikler tek istege duser (v2'den)
_ISITMA_MS = 1500                 # acilistan sonra isci sicak baslatilir (ilk cizimde import yok)
_GOSTERGE_SATIRI = 3              # gosterge alaninin en cok satiri (fazlasi kaydirilir)
_GORUNUM_KATI = 2                 # tam gorunumde goruntu pikseli / ekran pikseli (en az)
_ADIM_ARASI_MS = 1                # 0 olursa Qt adimlari tek turda (araya girdi almadan) yurutur
_YERLESIM_GECIKMESI_MS = 150     # boyut degisimi durulunca yerlesim (cizimle ayni olayda degil)
_EN_BOY_SINIRI = 3.0              # bu orani asan eksenel kesit gerilir ve baslikta yazar
_KESIM = {"xy": "z = 0", "xz": "y = 0", "yz": "x = 0"}


def _model_yuksekligi(spec):
    """Sablon ve agac modunda model yuksekligi [cm]; 2B ya da okunamazsa None."""
    if not spec:
        return None
    try:
        return sema.model_yuksekligi(spec)
    except (ValueError, KeyError, TypeError):
        _log.info("model yuksekligi okunamadi", exc_info=True)
        return None


def _rgb01(ad):
    from matplotlib.colors import to_rgb
    return to_rgb(tema.renk(ad))


def _kapsam(genislik):
    """Kesit merkezi orijin (cizim_sureci.KESIT_MERKEZI): imshow extent."""
    w, h = genislik
    return (-w / 2.0, w / 2.0, -h / 2.0, h / 2.0)


class OnizlemeWidget(KapsamMixin, VurguMixin, QtWidgets.QWidget):
    """Geometri kesiti gosteren matplotlib tuvali + denetimler."""

    durum = QtCore.Signal(str, bool)
    olcu_bulundu = QtCore.Signal(float, float)
    dugum_secildi = QtCore.Signal(object)
    cizim_bitti = QtCore.Signal(bool)            # guncel istek bitti (basarili mi)
    gorunurluk_degisti = QtCore.Signal(bool)

    def __init__(self, parent=None, istemci=None):
        super().__init__(parent)
        self.spec = None
        self._vurgu = None                # gelismis editorde secili dugum yolu
        self._son_eksenler = []           # [(eksen, ax)] son basarili cizim (tiklama)
        self._son_hata = None
        self._son_basarili = False         # gecerli spec icin son istek basarili mi (kapi)
        self._kapandi = False              # kapat() sonrasi istek gonderilmez
        self.son_olcu = None
        self._ikili_varsayilan = None     # son spec 3B miydi (gorunum varsayilani)
        self.son_sure = None              # son istegin suresi [s] (istekten sona)
        self._istek = None                # bekleyen istegin bilgisi (sozluk)
        self._meta = None                 # iscinin model bilgisi (renkler, gosterge)
        self._gorunum_kirli = False       # gizliyken degisti: gorunur olunca ciz
        self._kesit_onbellegi = None      # son dilimler: renk/gosterge degisimi isciye gitmez
        self._kapsam_kur()                # K5: kapsam secici + tam model kapi durumu
        self._denetimleri_kur()
        self._duzeni_kur()

        self._istemci = istemci or CizimIstemcisi(self)
        self._istemci.cerceve_geldi.connect(self._cerceve_geldi)
        self._istemci.coktu.connect(self._coktu)

        self._sayac = QtCore.QTimer(self)
        self._sayac.setSingleShot(True)
        self._sayac.setInterval(_GECIKME_MS)
        self._sayac.timeout.connect(self._ciz)
        self._isitma = QtCore.QTimer(self)
        self._isitma.setSingleShot(True)
        self._isitma.setInterval(_ISITMA_MS)
        self._isitma.timeout.connect(self._istemci.baslat)
        self._isitma.start()

        for w in (self.eksen, self.renklendirme, self.cozunurluk):
            w.currentIndexChanged.connect(lambda *_a: self._ciz())
        self.gosterge.toggled.connect(self.gosterge_alani.setVisible)
        self.gosterge.toggled.connect(lambda *_a: self._ciz())
        self.cakisma.toggled.connect(lambda *_a: self._ciz())
        self.yenile_dugme.clicked.connect(lambda *_a: self._ciz())
        self.tuval.mpl_connect("button_press_event", self._tiklandi)
        self._yerlesim_sayaci = QtCore.QTimer(self)
        self._yerlesim_sayaci.setSingleShot(True)
        self._yerlesim_sayaci.setInterval(_YERLESIM_GECIKMESI_MS)
        self._yerlesim_sayaci.timeout.connect(self._yeniden_yerlestir)
        self.tuval.mpl_connect("resize_event", lambda _o: self._yerlesim_sayaci.start())
        self._bos_mesaj(_("Model bekleniyor"))

    # ------------------------------------------------------------------
    def _denetimleri_kur(self):
        self.eksen = QtWidgets.QComboBox()
        self.eksen.addItems(GORUNUMLER)
        self.eksen.setToolTip(_("xy: üstten kesit (z = 0) · xz: yandan kesit (y = 0) · "
                                "yz: yandan kesit (x = 0)"))
        self.eksen_etiket = QtWidgets.QLabel(_("Kesit:"))
        self.renklendirme = QtWidgets.QComboBox()
        for veri, ad in RENKLENDIRME:
            self.renklendirme.addItem(_(ad), veri)
        self.cozunurluk = QtWidgets.QComboBox()
        for etiket, _piksel in COZUNURLUK:
            self.cozunurluk.addItem(_(etiket))
        self.cozunurluk.setCurrentIndex(1)
        self.gosterge = QtWidgets.QCheckBox(_("Gösterge"))
        self.gosterge.setChecked(True)
        self.cakisma = QtWidgets.QCheckBox(_("Çakışmaları göster"))
        self.cakisma.setToolTip(_(
            "Birden fazla hücrenin kapladığı noktaları ayrı renkle gösterir ve\n"
            "sayısını bildirir. Büyük korlarda çizimi birkaç kat yavaşlatır."))
        self.yenile_dugme = QtWidgets.QPushButton(_("Yenile"))
        self.calisiyor = QtWidgets.QLabel("")
        self.calisiyor.setObjectName("kucuk")
        self.gosterge_etiketi = QtWidgets.QLabel("")
        self.gosterge_etiketi.setObjectName("kucuk")
        self.gosterge_etiketi.setWordWrap(True)
        self.gosterge_etiketi.setTextFormat(QtCore.Qt.RichText)
        self.gosterge_etiketi.setContentsMargins(A["s"], 0, A["s"], 0)
        # Uzun malzeme listesi (SFR: 20 oge) tuvali ezmesin: en cok birkac satir, kaydirilir.
        self.gosterge_alani = QtWidgets.QScrollArea()
        self.gosterge_alani.setWidget(self.gosterge_etiketi)
        self.gosterge_alani.setWidgetResizable(True)
        self.gosterge_alani.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.gosterge_alani.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.gosterge_alani.setFixedHeight(
            self.gosterge_etiketi.fontMetrics().lineSpacing() * _GOSTERGE_SATIRI + A["s"])
        self._son_gosterge = []

    def _duzeni_kur(self):
        # Iki satir: 1280 genislikte dar panelde secim kutulari kirpilmasin.
        secim = QtWidgets.QHBoxLayout()
        secim.setSpacing(A["s"])
        secim.addWidget(self.eksen_etiket)
        secim.addWidget(self.eksen, 1)
        secim.addWidget(QtWidgets.QLabel(_("Renk:")))
        secim.addWidget(self.renklendirme, 1)
        eylem = QtWidgets.QHBoxLayout()
        eylem.setSpacing(A["s"])
        eylem.addWidget(self.gosterge)
        eylem.addWidget(self.kapsam_etiket)
        eylem.addWidget(self.kapsam)
        # Uzun kapsam adi dar panelde dugmeleri itmesin: etiket kirpilir.
        self.kapsam_bilgi.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                                        QtWidgets.QSizePolicy.Preferred)
        eylem.addWidget(self.kapsam_bilgi, 1)
        eylem.addWidget(self.calisiyor)
        eylem.addWidget(self.yenile_dugme)
        ust = QtWidgets.QVBoxLayout()
        ust.setContentsMargins(A["xs"], A["xs"], A["xs"], 0)
        ust.setSpacing(A["xs"])
        ust.addLayout(secim)
        ust.addLayout(eylem)

        self.figur = Figure(figsize=(5, 4), tight_layout=True)
        self.tuval = FigureCanvasQTAgg(self.figur)
        self.eksenler = self.figur.add_subplot(111)
        self.eksenler2 = None             # 3B'de ikinci (xz) kesit
        self.arac_cubugu = NavigationToolbar2QT(self.tuval, self)

        self.gelismis = GelismisBolum("onizleme_gelismis")
        gw = QtWidgets.QWidget()
        gl = QtWidgets.QHBoxLayout(gw)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.addWidget(QtWidgets.QLabel(_("Çözünürlük:")))
        gl.addWidget(self.cozunurluk)
        gl.addWidget(self.cakisma)
        gl.addStretch(1)
        self.gelismis.ekle(gw)

        alt = QtWidgets.QHBoxLayout()
        alt.setContentsMargins(0, 0, A["xs"], 0)
        alt.addWidget(self.arac_cubugu, 1)
        alt.addWidget(self.gelismis, 0, QtCore.Qt.AlignBottom)

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.addLayout(ust)
        duzen.addWidget(self.tuval, 1)
        duzen.addWidget(self.gosterge_alani)
        duzen.addLayout(alt)

    # ------------------------------------------------------------------
    @staticmethod
    def _uc_boyutlu(spec):
        """Eksenel kesit anlamli mi: 3B model (yukseklik ya da katman)."""
        return bool(_model_yuksekligi(spec))

    def spec_ayarla(self, spec):
        self.spec = spec
        self._son_basarili = False
        self._tam_kirli = True
        # 3B modelde xy ve xz yan yana; 2B'de yalnizca xy -- secim gizlenir.
        # 2B -> 3B gecisinde gorunum "xy + xz"ye doner; 3B icindeki secim korunur.
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
        """Cizimi gecikmeli ister; ardarda cagrilar tek istege duser. Model
        degismis olabilir: kapi tam model yeniden bilinene dek kapali (K5)."""
        if not self._kapandi:
            self._tam_kirli = True
            self._sayac.start()

    def mesgul_mu(self):
        """Bekleyen (gecikmeli ya da iscide suren) istek var mi."""
        return self._sayac.isActive() or self._istek is not None

    def bekle(self, zaman_asimi):
        """Olay dongusunu istek bitene dek dondurur (testler, ekran goruntusu
        araci). Arayuz kodu KULLANMAZ: sonuc cizim_bitti ile gelir."""
        uyg = QtWidgets.QApplication.instance()
        bitis = time.monotonic() + zaman_asimi
        while self.mesgul_mu() and time.monotonic() < bitis:
            uyg.processEvents(QtCore.QEventLoop.AllEvents, 20)
        uyg.processEvents()
        return not self.mesgul_mu()

    # ------------------------------------------------------------------
    def _gizli_mi(self):
        """Kendisi ya da bir atasi ACIKCA gizlendi mi (daraltma, sag panel).
        Hic gosterilmemis pencere gizli sayilmaz: gosterilince cizim hazir olur."""
        w = self
        while w is not None:
            if w.isHidden() and w.testAttribute(QtCore.Qt.WA_WState_ExplicitShowHide):
                return True
            w = w.parentWidget()
        return False

    def showEvent(self, olay):                    # noqa: N802 (Qt adi)
        super().showEvent(olay)
        self.gorunurluk_degisti.emit(True)
        if self._gorunum_kirli and self.spec is not None:
            self._ciz()

    def hideEvent(self, olay):                    # noqa: N802 (Qt adi)
        super().hideEvent(olay)
        self.gorunurluk_degisti.emit(False)

    def _ciz(self):
        """Hemen istek gonderir (gecikme yok); sonuc arka planda gelir."""
        self._sayac.stop()
        if self._kapandi:
            return
        if self.spec is None:
            self._bos_mesaj(_("Model bekleniyor"))
            return
        tam_ozet = onbellek.ozet(self.spec)
        self._tam_ozet_guncelle(tam_ozet)
        kontrol = self._gizli_mi()
        self._gorunum_kirli = kontrol
        # Gizliyken yalniz TAM model denetlenir (kapi); kapsam cizimde secilir (K5).
        kapsam = TAM_MODEL if kontrol else self._kapsam_coz()
        cizilen = kapsam.spec or self.spec
        if kapsam.spec is None:
            self._son_basarili = False      # tam model istegi: kapi sonucuyla acilir
        if not kontrol:
            self.etkin_kapsam = kapsam
            self._kapsam_bilgisi(kapsam)
        kesitler = [] if kontrol else self.gorunum()
        piksel = COZUNURLUK[self.cozunurluk.currentIndex()][1]
        ozet = tam_ozet if kapsam.spec is None else onbellek.ozet(cizilen)
        ist = {"kontrol": kontrol, "kesitler": kesitler, "piksel": piksel,
               "renk": self.renklendirme.currentData(), "t0": time.perf_counter(),
               "gosterge": self.gosterge.isChecked(), "eksenler": None, "cakisma": 0,
               "anahtar": (ozet, piksel, self.cakisma.isChecked()), "toplanan": {},
               "spec": cizilen, "kapsam": kapsam.spec is not None, "kapi": False,
               "tam_ozet": tam_ozet, "etiket": kapsam.etiket}
        if not kontrol and self._onbellekten_ciz(ist):
            return
        istek = {"tur": cs.ISTEK_KONTROL if kontrol else cs.ISTEK_CIZ, "spec": cizilen}
        if not kontrol:
            istek["kesitler"] = [{"eksen": e, "piksel": piksel} for e in kesitler]
            istek["cakisma"] = self.cakisma.isChecked()
        self._istek = ist
        self.calisiyor.setText("" if kontrol else _("Çiziliyor…"))
        ist["no"] = self._istemci.iste(istek)

    def _onbellekten_ciz(self, ist):
        """Ayni model + cozunurluk + cakisma secimiyle dilimlenmis kesitler
        eldeyse (renk, gosterge, vurgu, gorunum degisimi) isciye gitmeden
        yeniden boyar. Basardiysa True."""
        eldeki = self._kesit_onbellegi
        if (eldeki is None or eldeki["anahtar"] != ist["anahtar"]
                or not all(e in eldeki["kesitler"] for e in ist["kesitler"])):
            return False
        self._istemci.iptal()               # suren istek varsa yaniti artik gecersiz
        self._meta = eldeki["meta"]
        ist["no"] = None
        self._istek = ist
        adimlar = [(self._kesit_geldi, (ist, dict(b, sira=sira), geom))
                   for sira, (b, geom) in enumerate(eldeki["kesitler"][e]
                                                    for e in ist["kesitler"])]
        adimlar.append((self._son_geldi, (ist, {"durum": cs.DURUM_TAMAM})))
        self._adimlari_yurut(ist, adimlar)
        return True

    def _adimlari_yurut(self, ist, adimlar):
        """Adimlari ayri olay dongusu turlarinda yurutur (her biri < 200 ms);
        araya yeni istek girerse (self._istek degisti) zincir durur."""
        if self._istek is not ist or not adimlar:
            return
        islev, arg = adimlar[0]
        islev(*arg)
        if len(adimlar) > 1:
            self._sonra(lambda: self._adimlari_yurut(ist, adimlar[1:]))

    # ------------------------------------------------------------------
    def _cerceve_geldi(self, c):
        ist = self._istek
        if ist is None or c.baslik.get("no") != ist["no"]:
            return
        tur = c.baslik.get("tur")
        if tur == cs.YANIT_MODEL:
            if not ist["kapi"]:
                self._meta = c.baslik
            if not ist["kapsam"]:            # olcu yalniz TAM modelin (alt modelin degil)
                gx, gy = c.baslik["sinir_kutu"]
                self.son_olcu = (gx, gy)
                self.olcu_bulundu.emit(gx, gy)
        elif tur == cs.YANIT_KESIT:
            self._kesit_geldi(ist, c.baslik, c.diziler["geom"])
        elif tur == cs.YANIT_SON:
            self._son_geldi(ist, c.baslik)

    def _kesit_geldi(self, ist, b, geom):
        if ist["eksenler"] is None:
            self._figuru_hazirla(ist)
        ax = ist["eksenler"][b["sira"]]
        ax.clear()
        ax.set_axis_on()
        genislik = tuple(b["genislik"])
        self._kesit_ciz(ax, ist, b["eksen"], genislik, geom)
        ist["cakisma"] += len(b.get("cakismalar") or [])
        ist["toplanan"][b["eksen"]] = (b, geom)
        # Tuval YALNIZ sonda cizilir: matplotlib cizimi ana is parcacigindadir;
        # kesit basina tekrarlanirsa donma siniri (200 ms) asiliyordu (olculdu).

    def _figuru_hazirla(self, ist):
        self.figur.clear()
        self.figur.set_layout_engine("none")      # yerlesim sonda bir kez (_yerlesim)
        n = len(ist["kesitler"])
        eksenler = [self.figur.add_subplot(1, n, i + 1) for i in range(n)]
        ist["eksenler"] = eksenler
        self.eksenler = eksenler[0]
        self.eksenler2 = eksenler[1] if n > 1 else None
        if n == 2:
            self.figur.suptitle(ist["spec"].get("ad", ""), fontsize=9)

    def _kesit_ciz(self, ax, ist, eksen, genislik, geom):
        kapsam = _kapsam(genislik)
        cakisma_rengi = _rgb01("hata")
        if ist["renk"] == "material":
            renkler = {int(k): v for k, v in (self._meta or {}).get("renkler", {}).items()}
            img = boyama.malzeme_goruntusu(geom, renkler, cakisma_rengi)
        else:
            # Kapsamli cizimde vurgu yok: id haritasi alt modelin hucreleridir.
            renkler, soluk = (None, None) if ist["kapsam"] else self._vurgu_renkleri()
            img = boyama.hucre_goruntusu(geom, renkler, soluk, cakisma_rengi)
        self._goruntu_koy(ax, img, kapsam, len(ist["kesitler"]))
        if ist["renk"] == "material" and not ist["kapsam"]:
            self._malzeme_vurgusu(ax, geom, kapsam)
        self._eksen_bicimle(ax, eksen, genislik, len(ist["kesitler"]) == 2,
                            ist["spec"].get("ad", ""))

    def _goruntu_koy(self, ax, img, kapsam, n):
        """Tam gorunumde seyreltilmis goruntu (ekran pikselinin en az
        _GORUNUM_KATI kati), yakinlastirinca tam cozunurluk. 1400 px'te tam
        goruntunun her cizimde yeniden orneklenmesi ~230 ms suruyordu (olculdu);
        yakinlastirmada matplotlib yalniz gorunen parcayi ornekler."""
        hedef = max(1, _GORUNUM_KATI * self.tuval.width() // max(n, 1))
        adim = max(1, img.shape[0] // hedef)
        im = ax.imshow(img[::adim, ::adim] if adim > 1 else img, extent=kapsam)
        if adim == 1:
            return
        genislik = kapsam[1] - kapsam[0]

        def gorunum_degisti(eks):
            x0, x1 = eks.get_xlim()
            yakin = abs(x1 - x0) < genislik / adim
            im.set_data(img if yakin else img[::adim, ::adim])

        ax.callbacks.connect("xlim_changed", gorunum_degisti)

    def _son_geldi(self, ist, b):
        self._istek = None
        self.calisiyor.setText("")
        self.son_sure = time.perf_counter() - ist["t0"]
        # Not: isci eski istek icin "iptal" yollar; no'su guncel olmadigindan buraya gelmez.
        if ist["kapi"]:
            self._kapi_sonucu(ist, b)
            return
        if b.get("durum") != cs.DURUM_TAMAM:
            self._kesit_onbellegi = None
            self._hata_goster(b.get("hata") or "", b.get("iz") or b.get("hata") or "",
                              kapi=not ist["kapsam"])
            self._kapi_denetle()            # kapsamli cizim: kapi tam modele bakar
            return
        if not ist["kapsam"]:
            self._son_hata, self._son_basarili = None, True
            self._kapi_ozet = ist["tam_ozet"]
        if ist["toplanan"]:
            self._kesit_onbellegi = {"anahtar": ist["anahtar"], "meta": self._meta,
                                     "kesitler": dict(ist["toplanan"])}
        if ist["kontrol"]:
            self.durum.emit(_("Önizleme gizli: model denetlendi, önizleme açılınca çizilir."),
                            True)
            self.cizim_bitti.emit(True)
            return
        self._son_eksenler = list(zip(ist["kesitler"], ist["eksenler"] or []))
        self._son_kapsamli = ist["kapsam"]
        self._gosterge_goster(ist)
        self._sonra(self._yerlesim_ve_ciz)
        self._basari_bildir(ist)
        self.cizim_bitti.emit(True)
        self._kapi_denetle()

    def _basari_bildir(self, ist):
        if ist["cakisma"]:
            self.durum.emit(_n("Önizleme: %d hücre çakışması bulundu — geometriyi gözden "
                               "geçirin (kesitte ayrı renkle gösterildi).",
                               "Önizleme: %d hücre çakışması bulundu — geometriyi gözden "
                               "geçirin (kesitte ayrı renkle gösterildi).",
                               ist["cakisma"]) % ist["cakisma"], False)
            return
        piksel = ist["piksel"]
        ek = " — " + ist["etiket"] if ist["kapsam"] and ist["etiket"] else ""
        self.durum.emit(_n("Önizleme güncel ({kesit}, {n} piksel){ek}",
                           "Önizleme güncel ({kesit}, {n} piksel){ek}", piksel).format(
            kesit=" + ".join(ist["kesitler"]), n=piksel, ek=ek), True)

    def _hata_goster(self, metin, iz, kapi=True):
        """Tuvalde hata. kapi=False: kapsamli (alt model) cizim -- Calistir
        kapisi tam model sonucunda kalir (K5)."""
        from arayuz.ortak import hata_metni
        if kapi:
            self._son_hata = iz or metin
            self._son_basarili = False
            self._kapi_ozet = self._tam_ozet
        self._son_eksenler = []
        self.gosterge_etiketi.setText("")
        self._bos_mesaj(_("Geometri kurulamadı:\n\n%s") % hata_metni(RuntimeError(metin)),
                        hata=True)
        self.durum.emit((_("Önizleme başarısız: %s") if kapi else
                         _("Kapsamlı önizleme başarısız (Çalıştır kapısı tam modele bakar): %s"))
                        % metin, False)
        self.cizim_bitti.emit(False)

    def _coktu(self, mesaj):
        if self._istek is None or self._istek["no"] is None:
            # bosta coktu (ya da isciye gitmeyen onbellek boyamasi suruyor):
            # son cizim gecerli kalir, yalniz bildirilir.
            self.durum.emit(mesaj, False)
            return
        ist, self._istek = self._istek, None
        self.calisiyor.setText("")
        if ist["kapi"]:                     # tam model denetimi coktu: kapi kapali, cizim kalir
            self._kapi_sonucu(ist, {"durum": cs.DURUM_HATA, "hata": mesaj, "iz": mesaj})
            return
        self._kesit_onbellegi = None
        self._hata_goster(mesaj, mesaj, kapi=not ist["kapsam"])

    # ------------------------------------------------------------------
    def _bos_mesaj(self, metin, hata=False):
        self.figur.clear()
        self.figur.set_layout_engine("tight")
        self.eksenler = self.figur.add_subplot(111)
        self.eksenler2 = None
        self.eksenler.set_axis_off()
        self.eksenler.text(0.5, 0.5, metin, ha="center", va="center",
                           wrap=True, fontsize=9,
                           color=tema.renk("hata" if hata else "metin_soluk"))
        self.tuval.draw_idle()

    def _eksen_bicimle(self, ax, eksen, genislik, ikili, ad):
        """Baslik ve en-boy orani. Eksenel kesitte model cok ince ve uzun
        olabilir (or. 21 x 395 cm); 1:1'de okunamaz bir serit olur. Oran 3'u
        asarsa eksen gerilir ve baslikta BELIRTILIR (sessizce carpitmak
        yaniltici olurdu)."""
        oran = genislik[1] / genislik[0] if genislik[0] else 1.0
        gerildi = eksen != "xy" and (oran > _EN_BOY_SINIRI or oran < 1 / _EN_BOY_SINIRI)
        if gerildi:
            ax.set_aspect("auto")
        olcu = "%.3f × %.3f cm" % genislik
        if ikili:
            baslik_ = "%s (%s)   %s" % (eksen, _KESIM[eksen], olcu)
        else:
            baslik_ = "%s   %s" % (ad, olcu)
        # Ikili (xy + xz) gorunumde dar eksenin uzerine sigsin: not alt satirda.
        ek = (("\n" if ikili else "   ") + _("[ölçek 1:1 değil]")) if gerildi else ""
        ax.set_title(baslik_ + ek, fontsize=8)
        ax.tick_params(labelsize=7)

    def _sonra(self, islev):
        """Islevi bir sonraki olay dongusu turunda calistirir (adimlar arasina
        girdi girebilsin: yerlesim ~70 ms + cizim ~110 ms ayni turda donma olurdu)."""
        QtCore.QTimer.singleShot(_ADIM_ARASI_MS, self, islev)

    def _bosta_mi(self):
        """Cizecek istek yok mu (tam model kapi denetimi tuvali cizmez)."""
        return self._istek is None or self._istek["kapi"]

    def _yerlesim_ve_ciz(self):
        if self._bosta_mi():                # arada yeni istek geldiyse o cizer
            self._yerlesim()
            self._sonra(self.tuval.draw_idle)

    def _yeniden_yerlestir(self):
        # Suren istek varsa yerlesim + cizim zaten sonda yapilir (cift cizim donmasi).
        if self._son_eksenler and self._bosta_mi():
            self._yerlesim()
            self.tuval.draw_idle()

    def _yerlesim(self):
        """Yerlesim (tight) BIR KEZ hesaplanir, motor kapali kalir: her cizimde
        tekrari ~50 ms ana is parcacigi demekti (olculdu). Tuval boyutu
        degisince (resize_event, gecikmeli) yeniden hesaplanir."""
        if not self._son_eksenler:
            return
        try:
            self.figur.tight_layout()
        except (ValueError, RuntimeError):   # cok dar tuval: yerlesim sigmaz
            _log.info("onizleme yerlesimi hesaplanamadi", exc_info=True)
        self.figur.set_layout_engine("none")

    def _gosterge_ogeleri(self, ist):
        if ist["renk"] != "material" or not ist["gosterge"] or not self._meta:
            return []
        gosterge = self._meta.get("gosterge", [])
        if ist["kapsam"]:                   # alt model: yalniz kesitteki malzemeler
            gosterge = kullanilan_gosterge(self._meta, [g for _b, g in ist["toplanan"].values()])
        return boyama.gosterge_ogeleri(gosterge, ist["cakisma"] > 0, _rgb01("hata"))

    def _gosterge_goster(self, ist):
        """Gosterge tuvalin ALTINDA bir Qt etiketidir: matplotlib gostergesi
        (SFR: 20 oge) cizimi ~110 ms uzatiyordu (olculdu). Kaydedilen resimde
        matplotlib gostergesi olarak yer alir (kaydet)."""
        ogeler = self._gosterge_ogeleri(ist)
        self._son_gosterge = ogeler
        # Alan yuksekligi SABIT ve yalniz "Gosterge" kapatilinca gizlenir: cizim
        # sirasinda tuval boyutu degismesin (yeniden yerlesim + ikinci cizim).
        if not ogeler:
            self.gosterge_etiketi.setText(
                _("Hücre renkleri yalnız hücreleri ayırt etmek içindir.")
                if ist["renk"] == "cell" else "")
            return
        from matplotlib.colors import to_hex
        self.gosterge_etiketi.setText("&nbsp;&nbsp; ".join(
            "<span style='color:%s'>&#9632;</span>&nbsp;%s" % (to_hex(renk), html.escape(ad))
            for ad, renk in ogeler))

    # ------------------------------------------------------------------
    def cizildi_mi(self):
        """TAM model bu haliyle BASARIYLA kuruldu mu? (CALISTIR kapisi)
        Tam model istegi surerken (gecikme dahil) ya da basarisizken False:
        eszamansiz cizimde kapi, denetlenmemis modele acik kalmasin. Kapsamli
        (alt model) cizim kapiyi ne acar ne kapatir (onizleme_kapsam.py)."""
        return self.spec is not None and self._kapi_acik()

    def son_hata(self):
        return self._son_hata

    def kaydet(self, yol):
        """Tuvali resim olarak kaydeder; gosterge (Qt etiketi) resme matplotlib
        gostergesi olarak eklenir, kayittan sonra kaldirilir."""
        gosterge = None
        if self._son_gosterge and self.gosterge_alani.isVisibleTo(self):
            from matplotlib.patches import Patch
            tutamaklar = [Patch(color=renk, label=ad) for ad, renk in self._son_gosterge]
            gosterge = self.figur.legend(handles=tutamaklar, loc="upper center",
                                         bbox_to_anchor=(0.5, 0.0), frameon=False,
                                         ncol=min(len(tutamaklar), 4), fontsize=7)
        try:
            self.figur.savefig(yol, dpi=150, bbox_inches="tight")
        finally:
            if gosterge is not None:
                gosterge.remove()
        return yol

    def kapat(self):
        """Uygulama kapanirken cizim iscisini temiz sonlandirir (kalici)."""
        self._kapandi = True
        self._sayac.stop()
        self._isitma.stop()
        self._yerlesim_sayaci.stop()
        self._istek = None
        self._istemci.kapat()
