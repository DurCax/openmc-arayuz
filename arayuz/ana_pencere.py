# -*- coding: utf-8 -*-
"""
================================================================================
 ana_pencere.py  --  Ana uygulama penceresi
================================================================================
 Sol tarafta editor sekmeleri, sag tarafta canli geometri onizlemesi, altta
 dogrulama paneli. Butun sekmeler ayni spec sozlugu uzerinde calisir.

 PERFORMANS NOTLARI (olcume dayali)
   1. Model onbellegi  : ayni spec icin openmc.Model yeniden kurulmaz.
                         Olculen: 21.9 ms -> 0.07 ms (bkz. cekirdek/onbellek.py)
   2. Tembel sekme yenileme : bir degisiklikte TUM sekmeler yeniden kurulmuyordu;
                         artik yalnizca gorunur sekme yenilenir, digerleri
                         "kirli" isaretlenip acildiklarinda guncellenir.
                         Olculen kazanc: degisiklik basina ~34 ms.
                         Yan fayda: gorunmeyen sekmelerin secim/kaydirma
                         durumu korunur (eskiden her degisiklikte sifirlaniyordu).
   3. Onizleme 300 ms geciktirilir (debounce); hizli yazarken tek cizime duser.

 GERI AL / YINELE
   Spec anlik goruntuleri 700 ms bosta kalinca yigina itilir; ardarda tus
   basislari tek adima birlesir. En fazla 50 adim tutulur.
================================================================================
"""

import copy
import os
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import sema, dogrula, ice_aktar, kod_uret, onbellek
from arayuz.onizleme import OnizlemeWidget
from arayuz.sekme_analiz import AnalizSekmesi
from arayuz.sekme_ayar import AyarSekmesi
from arayuz.sekme_calistir import CalistirSekmesi
from arayuz.sekme_cubuk import CubukSekmesi
from arayuz.sekme_demet import DemetSekmesi
from arayuz.sekme_kor import KorSekmesi
from arayuz.sekme_malzeme import MalzemeSekmesi
from arayuz import tema

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORNEKLER = os.path.join(KOK, "ornekler")

def _seviye_renk(seviye):
    """Dogrulama seviyesi rengi -- etkin temadan gelir."""
    return tema.renk({"hata": "hata", "uyari": "uyari", "bilgi": "bilgi"}[seviye])
_GECMIS_SINIR = 50

# Dogrulama bulgusundaki "yer" onekinden sekme indeksine
# Bir konu degistiginde hangi sekmelerin tazelenmesi gerektigi.
# Amac: ayar degisikligi yuzunden kullanicinin kafes secimini sifirlamamak.
_KONU_BAGIMLILIK = {
    "malzeme": {"cubuk", "demet", "kor"},   # malzeme listeleri her yerde kullaniliyor
    "cubuk":   {"demet", "kor"},            # kafes anahtarlari ve kor secimi
    "demet":   {"kor"},                     # kor hangi demeti kullanacagini secer
    "kor":     set(),
    "ayar":    set(),
    "genel":   {"malzeme", "cubuk", "demet", "kor", "ayar"},
}

_YER_SEKME = [
    ("malzeme", 0), ("cubuk", 1), ("plaka", 1), ("demet", 2),
    ("kor", 3), ("ayarlar", 4), ("veri kutuphanesi", 4),
]

# Yeni model sihirbazi sablonlari: (baslik, aciklama, ornek dosyasi)
SABLONLAR = [
    ("PWR yakit hucresi",
     "Tek yakit cubugu, yansitici sinir. En kucuk calisir model; ogrenmek ve "
     "hizli denemeler icin. Bu ornek ayni zamanda regresyon cipasidir "
     "(k-inf = 1.3570 +/- 0.0020).", "pwr_pinhucre.json"),
    ("PWR 17x17 yakit demeti",
     "264 yakit cubugu, 24 kilavuz boru, 1 enstruman borusu. Sicak sartlar, "
     "1300 ppm bor. Termal reaktor demet hesaplari icin baslangic noktasi.",
     "pwr_17x17.json"),
    ("MTR plaka yakit elemani",
     "23 duz plaka, U3Si2-Al dispersiyon yakiti, Al-6061 zarf. Havuz tipi "
     "arastirma reaktoru elemani.", "mtr_plaka.json"),
    ("SFR altigen demet",
     "7 halkali altigen kafes, 127 U-10Mo cubuk, sivi sodyum. Hizli reaktor "
     "ve altigen kafes ornegi.", "sfr_altigen.json"),
    ("Bos model",
     "Hicbir sey tanimli degil. Malzemelerden baslayarak kendiniz kurarsiniz.",
     None),
]


SOZLUK_HTML = """
<h2>Terim sozlugu</h2>
<p><i>Bu programda gecen terimlerin kisa aciklamalari.</i></p>

<h3>Temel buyuklukler</h3>
<table cellpadding="5">
<tr><td><b>k-eff</b></td><td>Cogalma carpani. Bir nesil notronun bir sonraki
nesli ne kadar buyuttugu. k&gt;1 guc artar, k=1 kritik, k&lt;1 soner.</td></tr>
<tr><td><b>k-inf</b></td><td>Sonsuz kafes cogalma carpani. Sinirlardan sizinti
olmadigi varsayilir (yansitici sinir kosulu). Gercek bir reaktor icin ust
sinirdir.</td></tr>
<tr><td><b>Reaktivite (&rho;)</b></td><td>(k-1)/k. Kritiklikten ne kadar uzak
oldugunun olcusu. <b>pcm</b> = 10<sup>-5</sup> birim.</td></tr>
<tr><td><b>Dolar ($)</b></td><td>Reaktivite / &beta;<sub>eff</sub>. 1 $ ustu
gecici rejimde ani kritiklik demektir.</td></tr>
<tr><td><b>&beta;<sub>eff</sub></b></td><td>Etkin gecikmis notron kesri.
Fisyon notronlarinin kucuk bir kismi (~%0.7) gecikmeli cikar; reaktor kontrolu
bu gecikmeye dayanir.</td></tr>
<tr><td><b>&Lambda;</b></td><td>Notron uretim zamani. Termal reaktorde ~20 &mu;s,
hizli metal sistemde ~6 ns.</td></tr>
</table>

<h3>Reaktivite katsayilari (7. Analiz sekmesi)</h3>
<table cellpadding="5">
<tr><td><b>Doppler katsayisi</b></td><td>Yakit sicakligi arttiginda reaktivite
degisimi [pcm/K]. U-238 rezonanslari genisler, yakalama artar &rarr; NEGATIF
olmali. Guvenligin ilk savunma hattidir: guc artarsa yakit isinir ve reaktivite
kendiliginden duser.</td></tr>
<tr><td><b>Moderator sicaklik kats.</b></td><td>Sogutucu sicakligi arttiginda
reaktivite degisimi [pcm/K]. Sicaklik artinca yogunluk da duser; ikisi birlikte
hesaplanmalidir. Termal reaktorde NEGATIF olmali.</td></tr>
<tr><td><b>Void katsayisi</b></td><td>Sogutucuda bosluk olusursa reaktivite
degisimi [pcm/%void]. Termal reaktorde negatif olmali.</td></tr>
<tr><td><b>Bor degeri (worth)</b></td><td>Suda cozunmus bor basina reaktivite
[pcm/ppm]. Bor sogurucudur &rarr; negatif. Cok bor, moderator sicaklik
katsayisini pozitife dogru iter -- bu yuzden sinirlanir.</td></tr>
</table>

<h3>Monte Carlo terimleri</h3>
<table cellpadding="5">
<tr><td><b>Cevrim (batch)</b></td><td>Bir grup notronun izlendigi tur.</td></tr>
<tr><td><b>Pasif cevrim</b></td><td>Baslangictaki cevrimler. Kaynak dagilimi
henuz dogru degildir, bu yuzden istatistige KATILMAZ. Tipik 20-50.</td></tr>
<tr><td><b>Shannon entropisi</b></td><td>Kaynak dagiliminin ne kadar yayildigini
olcer. Pasif cevrimler boyunca duzlesmelidir; hala kayiyorsa pasif cevrim
sayisi yetersizdir ve k-eff YANLI cikar.</td></tr>
<tr><td><b>Tally</b></td><td>Sayac. Modelin belirli bir yerinde/enerjisinde
hangi reaksiyonlarin kac kez oldugunu toplar (aki, fisyon, sogurma...).</td></tr>
<tr><td><b>S(&alpha;,&beta;)</b></td><td>Termal sacilma verisi. Dusuk enerjide
notron serbest bir cekirdekten degil, BAGLI bir molekulden sacilir (sudaki
hidrojen gibi). Unutulursa termal reaktorde k yuzde mertebesinde kayar.</td></tr>
</table>

<h3>Geometri terimleri</h3>
<table cellpadding="5">
<tr><td><b>Universe</b></td><td>Tekrar kullanilabilir geometri parcasi. Bir
yakit cubugu bir universe'dir; kafes onu tekrarlar.</td></tr>
<tr><td><b>Kafes (lattice)</b></td><td>Universe'lerin duzenli dizilimi. Kare
(PWR) ya da altigen (VVER, SFR).</td></tr>
<tr><td><b>Adim (pitch)</b></td><td>Komsu iki hucre merkezi arasi mesafe.</td></tr>
<tr><td><b>Sinir kosulu</b></td><td><i>vacuum</i>: notron kacar (gercek dis
yuzey). <i>reflective</i>: geri yansir (sonsuz tekrar varsayimi).</td></tr>
</table>
"""


class SablonDiyalog(QtWidgets.QDialog):
    """Yeni model olustururken sablon secimi."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni model")
        self.resize(620, 400)
        self.liste = QtWidgets.QListWidget()
        for baslik, _aciklama, _dosya in SABLONLAR:
            self.liste.addItem(baslik)
        self.liste.setCurrentRow(0)
        self.aciklama = QtWidgets.QLabel()
        self.aciklama.setWordWrap(True)
        self.aciklama.setMinimumHeight(90)
        self.aciklama.setAlignment(QtCore.Qt.AlignTop)
        self.liste.currentRowChanged.connect(self._aciklama_guncelle)
        self._aciklama_guncelle(0)

        kutu = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        kutu.accepted.connect(self.accept)
        kutu.rejected.connect(self.reject)
        self.liste.doubleClicked.connect(self.accept)

        d = QtWidgets.QVBoxLayout(self)
        d.addWidget(QtWidgets.QLabel("Neyle baslamak istersiniz?"))
        d.addWidget(self.liste, 1)
        d.addWidget(self.aciklama)
        d.addWidget(kutu)

    def _aciklama_guncelle(self, satir):
        if 0 <= satir < len(SABLONLAR):
            self.aciklama.setText(SABLONLAR[satir][1])

    def secilen_dosya(self):
        satir = self.liste.currentRow()
        return SABLONLAR[satir][2] if 0 <= satir < len(SABLONLAR) else None


class AnaPencere(QtWidgets.QMainWindow):

    def __init__(self, acilis_dosyasi=None):
        super().__init__()
        self.setWindowTitle("OpenMC Reaktor Kuru Arayuzu")
        # Boyut EKRANA gore belirlenir; sabit bir deger kucuk ekranlarda
        # pencerenin bir kismini ekran disinda birakiyordu.
        ekran = QtWidgets.QApplication.primaryScreen()
        alan = ekran.availableGeometry() if ekran else QtCore.QRect(0, 0, 1280, 800)
        self.resize(min(1600, int(alan.width() * 0.92)),
                    min(1000, int(alan.height() * 0.92)))
        self.setMinimumSize(900, 560)

        self.ayarlar = QtCore.QSettings("openmc_arayuz", "arayuz")
        self.spec = sema.yeni_spec("yeni model")
        self.proje_yolu = None
        self._kirli = False
        self._bulgular = []
        self._kirli_sekmeler = set()
        self._gecmis = []
        self._gecmis_ix = -1
        self._gecmis_yaziyor = False

        # ---------------- editor sekmeleri ----------------
        self.sekmeler = QtWidgets.QTabWidget()
        self.s_malzeme = MalzemeSekmesi()
        self.s_cubuk = CubukSekmesi()
        self.s_demet = DemetSekmesi()
        self.s_kor = KorSekmesi()
        self.s_ayar = AyarSekmesi()
        self.s_calistir = CalistirSekmesi()
        self.s_analiz = AnalizSekmesi()

        self.editorler = [self.s_malzeme, self.s_cubuk, self.s_demet,
                          self.s_kor, self.s_ayar]
        # Her sekme bir kaydirma alanina sarilir.
        #
        # SEBEP: QTabWidget'in minimum yuksekligi TUM sayfalarin en buyugudur.
        # Ayarlar sekmesi buyudukce (entropi, kinetik, guc dagilimi) pencerenin
        # minimumu 1317 px'e cikmisti; ekranda 1048 px oldugu icin pencere tam
        # ekran yapilamiyor ve ALT KISMI HIC GORUNMUYORDU. Kaydirma alani bu
        # bagi koparir: sekme buyuse de pencere kucuk ekranlara sigar.
        self._sayfa_editor = {}
        for ad, w in (("1. Malzemeler", self.s_malzeme),
                      ("2. Cubuk / Plaka", self.s_cubuk),
                      ("3. Kafesler", self.s_demet),
                      ("4. Kor", self.s_kor),
                      ("5. Ayarlar & Tally", self.s_ayar),
                      ("6. Calistir", self.s_calistir),
                      ("7. Analiz", self.s_analiz)):
            kaydirma = QtWidgets.QScrollArea()
            kaydirma.setWidgetResizable(True)
            kaydirma.setFrameShape(QtWidgets.QFrame.NoFrame)
            kaydirma.setWidget(w)
            self._sayfa_editor[kaydirma] = w
            self.sekmeler.addTab(kaydirma, ad)
        for e in self.editorler:
            e.degisti.connect(self._degisti)
        self.sekmeler.currentChanged.connect(self._sekme_degisti)
        self._konu_sekme = {e.KONU: e for e in self.editorler}

        # ---------------- onizleme ----------------
        self.onizleme = OnizlemeWidget()
        self.onizleme.durum.connect(self._onizleme_durum)
        self.onizleme.olcu_bulundu.connect(lambda *_: self._ozet_guncelle())

        # ---------------- dogrulama paneli ----------------
        self.dogrulama = QtWidgets.QListWidget()
        self.dogrulama.setAlternatingRowColors(True)
        self.dogrulama.itemActivated.connect(self._bulguya_git)
        self.dogrulama.itemClicked.connect(self._bulguya_git)
        self.dogrulama_ozet = QtWidgets.QLabel("-")
        dg = QtWidgets.QWidget()
        dgd = QtWidgets.QVBoxLayout(dg)
        dgd.setContentsMargins(4, 4, 4, 4)
        ust = QtWidgets.QHBoxLayout()
        ust.addWidget(QtWidgets.QLabel("Dogrulama:"))
        ust.addWidget(self.dogrulama_ozet)
        ust.addWidget(QtWidgets.QLabel("(bir satira tiklayinca ilgili sekmeye gider)"))
        ust.addStretch(1)
        d_yenile = QtWidgets.QPushButton("Veri kutuphanesini de kontrol et")
        d_yenile.setToolTip("Modelin istedigi her nuklidin cross_sections.xml "
                            "icinde bulunup bulunmadigini kontrol eder (yavas).")
        d_yenile.clicked.connect(lambda: self._dogrula(veri=True))
        ust.addWidget(d_yenile)
        dgd.addLayout(ust)
        dgd.addWidget(self.dogrulama)

        # ---------------- yerlesim ----------------
        sag = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        sag.addWidget(self.onizleme)
        sag.addWidget(dg)
        sag.setStretchFactor(0, 3)
        sag.setStretchFactor(1, 1)

        bolucu = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        bolucu.addWidget(self.sekmeler)
        bolucu.addWidget(sag)
        # Sekme tarafi daha genis: ayarlar sekmesi iki sutunlu ve dar kalinca
        # yatay kaydirma cubugu cikiyordu.
        bolucu.setStretchFactor(0, 5)
        bolucu.setStretchFactor(1, 3)
        bolucu.setSizes([1150, 700])

        # Rehber seridi + ana bolucu
        self.rehber = QtWidgets.QLabel("")
        self.rehber.setWordWrap(True)
        self.rehber.setTextFormat(QtCore.Qt.RichText)
        self.rehber.setContentsMargins(10, 6, 10, 6)
        self.rehber_git = QtWidgets.QPushButton("Oraya git")
        self.rehber_git.setMaximumWidth(110)
        self.rehber_git.clicked.connect(self._rehbere_git)
        rehber_kutu = QtWidgets.QWidget()
        rk = QtWidgets.QHBoxLayout(rehber_kutu)
        rk.setContentsMargins(0, 0, 8, 0)
        rk.addWidget(self.rehber, 1)
        rk.addWidget(self.rehber_git)
        self._rehber_kutu = rehber_kutu

        merkez = QtWidgets.QWidget()
        md = QtWidgets.QVBoxLayout(merkez)
        md.setContentsMargins(0, 0, 0, 0)
        md.setSpacing(0)
        md.addWidget(rehber_kutu)
        md.addWidget(bolucu, 1)
        self.setCentralWidget(merkez)

        self._menu_kur()
        self._arac_cubugu_kur()
        self._rehber_kur()
        self._durum_cubugu_kur()

        self.s_calistir.kapi_ayarla(self._kosu_izni)
        self.s_calistir.durum.connect(lambda m, ok: self.statusBar().showMessage(m, 8000))
        self.s_analiz.kapi_ayarla(self._kosu_izni)
        self.s_analiz.durum.connect(lambda m, ok: self.statusBar().showMessage(m, 8000))

        self._dog_sayac = QtCore.QTimer(self); self._dog_sayac.setSingleShot(True)
        self._dog_sayac.setInterval(250)
        self._dog_sayac.timeout.connect(lambda: self._dogrula(veri=False))

        self._gecmis_sayac = QtCore.QTimer(self); self._gecmis_sayac.setSingleShot(True)
        self._gecmis_sayac.setInterval(700)
        self._gecmis_sayac.timeout.connect(self._gecmise_it)

        if acilis_dosyasi:
            self.proje_ac(acilis_dosyasi)
        else:
            self._spec_uygula()
            self._gecmise_it(ilk=True)

    # ==================================================================
    # menu / arac cubugu / durum cubugu
    # ==================================================================
    def _menu_kur(self):
        m_dosya = self.menuBar().addMenu("&Dosya")
        self.e_yeni = self._eylem(m_dosya, "Yeni...", self.proje_yeni,
                                  QtGui.QKeySequence.New, "Sablondan yeni model")
        self.e_ac = self._eylem(m_dosya, "Ac...", self._ac_diyalog,
                                QtGui.QKeySequence.Open)
        self.m_son = m_dosya.addMenu("Son kullanilanlar")
        m_ornek = m_dosya.addMenu("Ornek ac")
        for baslik, _a, dosya in SABLONLAR:
            if dosya:
                yol = os.path.join(ORNEKLER, dosya)
                e = QtGui.QAction(baslik, self)
                e.triggered.connect(lambda _c=False, y=yol: self.proje_ac(y))
                m_ornek.addAction(e)
        m_dosya.addSeparator()
        self.e_kaydet = self._eylem(m_dosya, "Kaydet", self.proje_kaydet,
                                    QtGui.QKeySequence.Save)
        self._eylem(m_dosya, "Farkli kaydet...", self.proje_farkli_kaydet,
                    QtGui.QKeySequence.SaveAs)
        m_dosya.addSeparator()
        self._eylem(m_dosya, "Malzemeleri OpenMC XML'inden ice aktar...",
                    self.malzeme_ice_aktar)
        self._eylem(m_dosya, "Neden geometri ice aktarilamiyor?",
                    self._geometri_aciklama)
        m_dosya.addSeparator()
        self._eylem(m_dosya, "Python betigi olarak disa aktar...",
                    self.betik_disa_aktar, "Ctrl+E")
        self._eylem(m_dosya, "OpenMC XML disa aktar...", self.xml_disa_aktar)
        self._eylem(m_dosya, "Onizlemeyi PNG kaydet...", self.png_kaydet)
        m_dosya.addSeparator()
        self._eylem(m_dosya, "Cikis", self.close, QtGui.QKeySequence.Quit)

        m_duzen = self.menuBar().addMenu("&Duzen")
        self.e_geri = self._eylem(m_duzen, "Geri al", self.geri_al,
                                  QtGui.QKeySequence.Undo)
        self.e_yinele = self._eylem(m_duzen, "Yinele", self.yinele,
                                    QtGui.QKeySequence.Redo)

        m_gorunum = self.menuBar().addMenu("&Gorunum")
        m_tema = m_gorunum.addMenu("Tema")
        self._tema_eylemleri = {}
        grup = QtGui.QActionGroup(self)
        grup.setExclusive(True)
        for anahtar, bilgi in tema.TEMALAR.items():
            e = QtGui.QAction(bilgi["ad"], self)
            e.setCheckable(True)
            e.setChecked(anahtar == tema.etkin())
            e.triggered.connect(lambda _c=False, a=anahtar: self._tema_degistir(a))
            grup.addAction(e)
            m_tema.addAction(e)
            self._tema_eylemleri[anahtar] = e
        m_gorunum.addSeparator()
        self._eylem(m_gorunum, "Tam ekran", self._tam_ekran, "F11")
        self._eylem(m_gorunum, "Pencereyi buyut", self._buyut, "F10")

        m_model = self.menuBar().addMenu("&Model")
        self._eylem(m_model, "Dogrulamayi yenile (veri kutuphanesi dahil)",
                    lambda: self._dogrula(veri=True), "F5")
        self._eylem(m_model, "Onizlemeyi yenile", self.onizleme._ciz, "F6")
        self.e_calistir = self._eylem(m_model, "CALISTIR", self._calistir_menuden, "F9")

        m_yardim = self.menuBar().addMenu("&Yardim")
        self._eylem(m_yardim, "Terim sozlugu", self._sozluk, "F1")
        self._eylem(m_yardim, "Kisayollar", self._kisayollar)
        self._eylem(m_yardim, "Hakkinda", self._hakkinda)
        self._son_menusu_yenile()

    def _arac_cubugu_kur(self):
        cubuk = QtWidgets.QToolBar("Ana")
        cubuk.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        cubuk.setMovable(False)
        for e in (self.e_yeni, self.e_ac, self.e_kaydet):
            cubuk.addAction(e)
        cubuk.addSeparator()
        for e in (self.e_geri, self.e_yinele):
            cubuk.addAction(e)
        cubuk.addSeparator()
        cubuk.addAction(self.e_calistir)
        bosluk = QtWidgets.QWidget()
        bosluk.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                             QtWidgets.QSizePolicy.Preferred)
        cubuk.addWidget(bosluk)
        self.model_ozet = QtWidgets.QLabel("-")
        cubuk.addWidget(self.model_ozet)
        self.addToolBar(cubuk)

    def _rehber_kur(self):
        """Rehber seridinin gorunumu (icerigi _rehber_guncelle doldurur)."""
        self._rehber_hedef = 0

    def _rehbere_git(self):
        self.sekmeler.setCurrentIndex(self._rehber_hedef)

    def _sonraki_adim(self):
        """
        Modelin durumuna bakip "simdi ne yapmalisin" sorusunu cevaplar.

        Bu, ilk kez acan bir kullanicinin en buyuk sorunudur: sekmeler numarali
        ama hangisinde ne eksik oldugu gorunmez. Burada eksik olan ilk sey
        bulunur ve dogrudan oraya yonlendirilir.
        DONER (sekme_indeksi, html_metin, seviye)   seviye: "yap" | "hata" | "hazir"
        """
        s = self.spec
        if not s["malzemeler"]:
            return (0, "<b>Basla:</b> once malzeme gerekir. "
                       "<i>1. Malzemeler</i> sekmesinde <b>Kutuphaneden ekle...</b> "
                       "dugmesiyle yakit (orn. UO2), zarf (Zircaloy-4) ve sogutucu "
                       "(su) ekleyin.", "yap")

        kor = s["kor"]
        tur = kor.get("tur")
        if tur in ("tek_cubuk",) and not s.get("cubuklar"):
            return (1, "<b>Sonraki adim:</b> <i>2. Cubuk / Plaka</i> sekmesinde "
                       "<b>+ Cubuk</b> ile bir yakit cubugu tanimlayin "
                       "(icten disa: yakit, bosluk, zarf, sogutucu).", "yap")
        if tur == "tek_plaka" and not s.get("plakalar"):
            return (1, "<b>Sonraki adim:</b> <i>2. Cubuk / Plaka</i> sekmesinde "
                       "<b>+ Plaka</b> ile bir plaka elemani tanimlayin.", "yap")
        if tur == "tek_demet" and not s.get("demetler"):
            return (2, "<b>Sonraki adim:</b> <i>3. Kafesler</i> sekmesinde bir "
                       "kafes kurun ve haritasini boyayin.", "yap")
        if tur == "kuresel" and not kor.get("kabuklar"):
            return (3, "<b>Sonraki adim:</b> <i>4. Kor</i> sekmesinde kuresel "
                       "kabuklari tanimlayin (yaricap + malzeme).", "yap")

        if dogrula.hata_var(self._bulgular):
            n = sum(1 for b in self._bulgular if b.seviye == "hata")
            ilk = next(b for b in self._bulgular if b.seviye == "hata")
            hedef = 4
            for onek, ix in _YER_SEKME:
                if ilk.yer.lower().startswith(onek):
                    hedef = ix
                    break
            return (hedef, "<b>%d hata var:</b> %s &nbsp; "
                           "<i>(sag alttaki dogrulama panelinde satira tiklayarak "
                           "da gidebilirsiniz)</i>" % (n, ilk.mesaj), "hata")

        if not self.onizleme.cizildi_mi():
            return (3, "<b>Geometri cizilmeyi bekliyor.</b> Sag ustteki onizleme "
                       "uretilince CALISTIR etkinlesir.", "yap")

        if not getattr(self.s_calistir, "_son_basarili", False):
            return (5, "<b>Hazir.</b> <i>6. Calistir</i> sekmesinden "
                       "<b>CALISTIR</b> (F9) ile k-eff hesaplayin.", "hazir")

        return (6, "<b>Kosu tamam.</b> Simdi <i>7. Analiz</i> sekmesinde "
                   "reaktivite katsayilarini (Doppler, moderator sicaklik, void, "
                   "bor degeri) hesaplayabilir ya da kritik arama yapabilirsiniz.",
                "hazir")

    def _rehber_guncelle(self):
        try:
            hedef, metin, seviye = self._sonraki_adim()
        except Exception:
            return
        self._rehber_hedef = hedef
        on = {"yap": tema.renk("vurgu"), "hata": tema.renk("hata"),
              "hazir": tema.renk("basari")}[seviye]
        self._rehber_kutu.setStyleSheet(
            "background: %s; border-bottom: 1px solid %s;"
            % (tema.renk("yuzey2"), tema.renk("kenar")))
        self.rehber.setStyleSheet("color: %s; font-size: 10pt;" % on)
        self.rehber.setText(metin)

    def _durum_cubugu_kur(self):
        self.durum_dogrulama = QtWidgets.QLabel("")
        self.statusBar().addPermanentWidget(self.durum_dogrulama)
        self.statusBar().showMessage("Hazir")

    def _eylem(self, menu, ad, islev, kisayol=None, ipucu=None):
        e = QtGui.QAction(ad, self)
        e.triggered.connect(lambda _c=False: islev())
        if kisayol:
            e.setShortcut(kisayol)
        if ipucu:
            e.setToolTip(ipucu)
        menu.addAction(e)
        return e

    def _tema_degistir(self, ad):
        """Temayi degistirir ve renge bagli panelleri tazeler."""
        tema.uygula(QtWidgets.QApplication.instance(), ad)
        for anahtar, e in self._tema_eylemleri.items():
            e.setChecked(anahtar == ad)
        self._dogrula(veri=False)          # seviye renkleri
        self._rehber_guncelle()            # rehber seridi
        self.onizleme._ciz()               # grafik paleti
        self.statusBar().showMessage("Tema: %s" % tema.TEMALAR[ad]["ad"], 4000)

    def _tam_ekran(self):
        """F11 -- tam ekran ac/kapa."""
        if self.isFullScreen():
            self.setWindowState(self.windowState() & ~QtCore.Qt.WindowFullScreen)
        else:
            self.setWindowState(self.windowState() | QtCore.Qt.WindowFullScreen)

    def _buyut(self):
        """F10 -- pencereyi ekrana sigacak sekilde buyut."""
        if self.isMaximized():
            self.setWindowState(self.windowState() & ~QtCore.Qt.WindowMaximized)
        else:
            self.setWindowState(self.windowState() | QtCore.Qt.WindowMaximized)

    def _kisayollar(self):
        QtWidgets.QMessageBox.information(self, "Kisayollar",
            "Ctrl+N   Yeni model (sablon secimi)\n"
            "Ctrl+O   Ac\n"
            "Ctrl+S   Kaydet\n"
            "Ctrl+Z   Geri al\n"
            "Ctrl+Y   Yinele\n"
            "Ctrl+E   Python betigi olarak disa aktar\n"
            "F5       Dogrulamayi yenile (veri kutuphanesi dahil)\n"
            "F6       Onizlemeyi yenile\n"
            "F9       CALISTIR\n"
            "F1       Terim sozlugu\n"
            "F10      Pencereyi buyut / eski haline dondur\n"
            "F11      Tam ekran\n\n"
            "Altigen haritada: sol tik boyar, sag tik fircayi degistirir, "
            "tekerlek yakinlastirir.")

    def _sozluk(self):
        """Ogrenciye yonelik kisa terim sozlugu."""
        d = QtWidgets.QDialog(self)
        d.setWindowTitle("Terim sozlugu")
        d.resize(760, 640)
        metin = QtWidgets.QTextBrowser()
        metin.setOpenExternalLinks(False)
        metin.setHtml(SOZLUK_HTML)
        kutu = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        kutu.rejected.connect(d.reject)
        kutu.accepted.connect(d.accept)
        duzen = QtWidgets.QVBoxLayout(d)
        duzen.addWidget(metin)
        duzen.addWidget(kutu)
        d.exec()

    def _hakkinda(self):
        QtWidgets.QMessageBox.information(
            self, "Hakkinda",
            "OpenMC Reaktor Kuru Arayuzu\n\n"
            "Model tanimi JSON 'spec' olarak tutulur; ondan hem openmc.Model\n"
            "hem de tek basina calisan Python betigi uretilir.\n\n"
            "Arayuz bir cikmaz sokak degildir: Dosya > Python betigi olarak\n"
            "disa aktar (Ctrl+E) ile modeli alip elle duzenlemeye devam\n"
            "edebilirsiniz.")

    # ==================================================================
    # spec yasam dongusu
    # ==================================================================
    def _spec_uygula(self):
        """Spec bastan yuklendi -- tum sekmeleri tazele."""
        for e in self.editorler:
            e.spec_yukle(self.spec)
        self._kirli_sekmeler.clear()
        self.onizleme.spec_ayarla(self.spec)
        self.s_calistir.spec_ayarla(self.spec, self.proje_yolu)
        self.s_analiz.spec_ayarla(self.spec, self.proje_yolu)
        self._dogrula(veri=False)
        self._baslik_guncelle()
        self._ozet_guncelle()
        self._rehber_guncelle()

    def _degisti(self, konu="genel"):
        """
        Bir editor sekmesi spec'i degistirdi.

        Eskiden burada TUM sekmeler yeniden kuruluyordu: olculen 34 ms ve --
        daha kotusu -- gorunmeyen sekmelerin secim/kaydirma durumu her
        seferinde sifirlaniyordu. Artik yalnizca konuya BAGIMLI sekmeler
        kirli isaretlenir, onlar da ancak acildiklarinda yenilenir.
        """
        self._kirli = True
        bagimli_konular = _KONU_BAGIMLILIK.get(konu, set())
        gorunur = self._gorunur_editor()
        for k in bagimli_konular:
            e = self._konu_sekme.get(k)
            if e is None:
                continue
            if e is gorunur:
                e.spec_yukle(self.spec)
                self._kirli_sekmeler.discard(e)
            else:
                self._kirli_sekmeler.add(e)

        self.onizleme.iste()
        self._dog_sayac.start()
        self._gecmis_sayac.start()
        self._baslik_guncelle()
        self._ozet_guncelle()
        self._rehber_guncelle()

    def _gorunur_editor(self):
        """Etkin sekmenin ICINDEKI editoru dondurur (kaydirma alanini asar)."""
        return self._sayfa_editor.get(self.sekmeler.currentWidget())

    def _sekme_degisti(self, indeks):
        w = self._sayfa_editor.get(self.sekmeler.widget(indeks))
        if w is None:
            return
        if w in self._kirli_sekmeler:
            w.spec_yukle(self.spec)
            self._kirli_sekmeler.discard(w)
        if w is self.s_calistir:
            self.s_calistir.spec_ayarla(self.spec, self.proje_yolu)
        elif w is self.s_analiz:
            self.s_analiz.spec_ayarla(self.spec, self.proje_yolu)

    def _baslik_guncelle(self):
        ad = os.path.basename(self.proje_yolu) if self.proje_yolu else "kaydedilmemis"
        self.setWindowTitle("OpenMC Reaktor Kuru Arayuzu  --  %s%s"
                            % (ad, " *" if self._kirli else ""))
        self.e_geri.setEnabled(self._gecmis_ix > 0)
        self.e_yinele.setEnabled(0 <= self._gecmis_ix < len(self._gecmis) - 1)

    def _ozet_guncelle(self):
        """
        Arac cubugundaki kisa ozet. BURADA MODEL KURULMAZ -- olcu bilgisi
        onizlemeden gelir (olcu_bulundu sinyali). Onceki surumde burada
        kur_onbellekli() cagriliyordu ve spec her degistiginde onbellek
        iskaladigi icin degisiklik basina ~22 ms ekliyordu.
        """
        s = self.spec
        parcalar = ["%d malzeme" % len(s["malzemeler"])]
        n_cubuk = len(s.get("cubuklar", [])) + len(s.get("plakalar", []))
        if n_cubuk:
            parcalar.append("%d cubuk/plaka" % n_cubuk)
        if s.get("demetler"):
            parcalar.append("%d kafes" % len(s["demetler"]))
        olcu = self.onizleme.son_olcu
        if olcu:
            parcalar.append("%.2f x %.2f cm" % olcu)
        self.model_ozet.setText("   |   ".join(parcalar) + "   ")

    # ==================================================================
    # geri al / yinele
    # ==================================================================
    def _gecmise_it(self, ilk=False):
        if self._gecmis_yaziyor:
            return
        anlik = copy.deepcopy(self.spec)
        if self._gecmis and self._gecmis_ix >= 0:
            if onbellek.ozet(self._gecmis[self._gecmis_ix]) == onbellek.ozet(anlik):
                return          # degisiklik yok
        del self._gecmis[self._gecmis_ix + 1:]
        self._gecmis.append(anlik)
        if len(self._gecmis) > _GECMIS_SINIR:
            self._gecmis.pop(0)
        self._gecmis_ix = len(self._gecmis) - 1
        self._baslik_guncelle()

    def _gecmisten_yukle(self, ix):
        self._gecmis_yaziyor = True
        try:
            self.spec = copy.deepcopy(self._gecmis[ix])
            self._gecmis_ix = ix
            self._spec_uygula()
            self._kirli = True
        finally:
            self._gecmis_yaziyor = False
        self._baslik_guncelle()

    def geri_al(self):
        self._gecmis_sayac.stop()
        self._gecmise_it()
        if self._gecmis_ix > 0:
            self._gecmisten_yukle(self._gecmis_ix - 1)
            self.statusBar().showMessage("Geri alindi (%d/%d)"
                                         % (self._gecmis_ix + 1, len(self._gecmis)), 3000)

    def yinele(self):
        if self._gecmis_ix < len(self._gecmis) - 1:
            self._gecmisten_yukle(self._gecmis_ix + 1)
            self.statusBar().showMessage("Yinelendi (%d/%d)"
                                         % (self._gecmis_ix + 1, len(self._gecmis)), 3000)

    # ==================================================================
    # dogrulama
    # ==================================================================
    def _dogrula(self, veri=False):
        try:
            self._bulgular = dogrula.tum_kontroller(self.spec, veri_kontrolu=veri)
        except Exception as e:
            self._bulgular = [dogrula.Bulgu("hata", "dogrulama",
                                            "dogrulama sirasinda hata: %s" % e)]
        self.dogrulama.clear()
        for b in self._bulgular:
            oge = QtWidgets.QListWidgetItem(
                "%s  %s%s" % (b.seviye.upper().ljust(5), b.yer.ljust(22), b.mesaj))
            oge.setForeground(QtGui.QColor(_seviye_renk(b.seviye)))
            oge.setData(QtCore.Qt.UserRole, b.yer)
            ipucu = b.oneri or ""
            oge.setToolTip((ipucu + "\n\n") if ipucu else "" + "Tiklayinca ilgili sekmeye gider.")
            self.dogrulama.addItem(oge)
        ozet = dogrula.ozet(self._bulgular)
        self.dogrulama_ozet.setText(ozet)
        renk = (tema.renk("hata") if dogrula.hata_var(self._bulgular)
                else tema.renk("basari"))
        self.dogrulama_ozet.setStyleSheet("color: %s; font-weight: bold;" % renk)
        self.durum_dogrulama.setText(ozet)
        self.durum_dogrulama.setStyleSheet("color: %s;" % renk)
        self.s_calistir.kapi_guncelle()
        self.s_analiz.kapi_guncelle()
        self._rehber_guncelle()

    def _bulguya_git(self, oge):
        """Dogrulama satirina tiklayinca ilgili sekmeyi ac."""
        yer = (oge.data(QtCore.Qt.UserRole) or "").lower()
        for onek, indeks in _YER_SEKME:
            if yer.startswith(onek):
                self.sekmeler.setCurrentIndex(indeks)
                return

    def _onizleme_durum(self, mesaj, basarili):
        self.statusBar().showMessage(mesaj, 6000)
        self.s_calistir.kapi_guncelle()

    def _kosu_izni(self):
        """CALISTIR kapisi: once geometri cizilmeli, sonra hata olmamali."""
        if dogrula.hata_var(self._bulgular):
            n = sum(1 for b in self._bulgular if b.seviye == "hata")
            return False, ("Dogrulamada %d hata var -- once bunlari giderin. "
                           "Sag alttaki panelde bir satira tiklayarak ilgili "
                           "sekmeye gidebilirsiniz." % n)
        if not self.onizleme.cizildi_mi():
            return False, ("Geometri onizlemesi henuz basariyla uretilmedi. "
                           "ONCE CIZ, SONRA CALISTIR: yanlis geometriyle saatlerce "
                           "kosmamak icin onizlemenin calismasi bekleniyor.")
        uyari = sum(1 for b in self._bulgular if b.seviye == "uyari")
        if uyari:
            return True, ("Calistirilabilir. %d uyari var -- sonucu etkileyebilir, "
                          "dogrulama panelini gozden gecirin." % uyari)
        return True, "Model calistirilmaya hazir."

    def _calistir_menuden(self):
        self.sekmeler.setCurrentWidget(self.s_calistir)
        self.s_calistir.spec_ayarla(self.spec, self.proje_yolu)
        self.s_calistir.calistir()

    # ==================================================================
    # son kullanilanlar
    # ==================================================================
    def _son_listesi(self):
        return [y for y in (self.ayarlar.value("son_dosyalar", []) or [])
                if isinstance(y, str) and os.path.exists(y)]

    def _sona_ekle(self, yol):
        liste = [os.path.abspath(yol)] + [y for y in self._son_listesi()
                                          if os.path.abspath(y) != os.path.abspath(yol)]
        self.ayarlar.setValue("son_dosyalar", liste[:10])
        self._son_menusu_yenile()

    def _son_menusu_yenile(self):
        self.m_son.clear()
        liste = self._son_listesi()
        if not liste:
            e = self.m_son.addAction("(bos)")
            e.setEnabled(False)
            return
        for yol in liste:
            e = QtGui.QAction(os.path.basename(yol), self)
            e.setToolTip(yol)
            e.triggered.connect(lambda _c=False, y=yol: self.proje_ac(y))
            self.m_son.addAction(e)

    # ==================================================================
    # dosya islemleri
    # ==================================================================
    def _kaydetme_sor(self):
        if not self._kirli:
            return True
        c = QtWidgets.QMessageBox.question(
            self, "Kaydedilmemis degisiklikler",
            "Degisiklikler kaydedilmedi. Kaydedilsin mi?",
            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard
            | QtWidgets.QMessageBox.Cancel)
        if c == QtWidgets.QMessageBox.Save:
            return self.proje_kaydet()
        return c == QtWidgets.QMessageBox.Discard

    def proje_yeni(self):
        if not self._kaydetme_sor():
            return
        d = SablonDiyalog(self)
        if d.exec() != QtWidgets.QDialog.Accepted:
            return
        dosya = d.secilen_dosya()
        if dosya:
            try:
                self.spec = sema.yukle(os.path.join(ORNEKLER, dosya))
                self.spec["ad"] = self.spec.get("ad", "") + " (kopya)"
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Sablon acilamadi", str(e))
                return
        else:
            self.spec = sema.yeni_spec("yeni model")
        self.proje_yolu = None
        self._kirli = bool(dosya)
        self._gecmis, self._gecmis_ix = [], -1
        self._spec_uygula()
        self._gecmise_it(ilk=True)
        self.statusBar().showMessage(
            "Yeni model olusturuldu -- 'Farkli kaydet' ile bir dosyaya baglayin", 8000)

    def _ac_diyalog(self):
        yol, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Model spec ac", ORNEKLER, "JSON model (*.json);;Tum dosyalar (*)")
        if yol:
            self.proje_ac(yol)

    def proje_ac(self, yol):
        if not self._kaydetme_sor():
            return
        try:
            self.spec = sema.yukle(yol)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Acilamadi", str(e))
            return
        self.proje_yolu = os.path.abspath(yol)
        self._kirli = False
        self._gecmis, self._gecmis_ix = [], -1
        self._spec_uygula()
        self._gecmise_it(ilk=True)
        self._sona_ekle(yol)
        self.statusBar().showMessage("Acildi: %s" % yol, 6000)

    def proje_kaydet(self):
        if self.proje_yolu is None:
            return self.proje_farkli_kaydet()
        try:
            sema.kaydet(self.spec, self.proje_yolu)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Kaydedilemedi", str(e))
            return False
        self._kirli = False
        self._baslik_guncelle()
        self._sona_ekle(self.proje_yolu)
        self.statusBar().showMessage("Kaydedildi: %s" % self.proje_yolu, 5000)
        return True

    def proje_farkli_kaydet(self):
        yol, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Model spec kaydet",
            self.proje_yolu or os.path.join(ORNEKLER, "model.json"),
            "JSON model (*.json)")
        if not yol:
            return False
        if not yol.endswith(".json"):
            yol += ".json"
        self.proje_yolu = yol
        self.s_calistir.spec_ayarla(self.spec, self.proje_yolu)
        return self.proje_kaydet()

    def malzeme_ice_aktar(self):
        yol, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Malzeme iceren OpenMC XML dosyasi",
            os.path.dirname(self.proje_yolu) if self.proje_yolu else os.getcwd(),
            "OpenMC XML (materials.xml model.xml *.xml);;Tum dosyalar (*)")
        if not yol:
            return
        try:
            yeni_malzemeler, notlar = ice_aktar.malzemeleri_oku(yol)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Okunamadi", str(e))
            return
        if not yeni_malzemeler:
            QtWidgets.QMessageBox.information(self, "Bos", "Dosyada malzeme bulunamadi.")
            return
        mevcut = {m["ad"] for m in self.spec["malzemeler"]}
        for m in yeni_malzemeler:
            ad, i = m["ad"], 2
            while ad in mevcut:
                ad = "%s_%d" % (m["ad"], i)
                i += 1
            m["ad"] = ad
            mevcut.add(ad)
            self.spec["malzemeler"].append(m)
        self._kirli = True
        self._spec_uygula()
        self._gecmise_it()
        mesaj = "%d malzeme eklendi.\n\n" % len(yeni_malzemeler)
        if notlar:
            mesaj += "Notlar:\n" + "\n".join("  - " + n for n in notlar)
        QtWidgets.QMessageBox.information(self, "Ice aktarildi", mesaj)

    def _geometri_aciklama(self):
        QtWidgets.QMessageBox.information(
            self, "Geometri ice aktarma", ice_aktar.geometri_neden_aktarilamaz())

    def betik_disa_aktar(self):
        varsayilan = os.path.splitext(self.proje_yolu or "model.json")[0] + ".py"
        yol, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Python betigi olarak disa aktar", varsayilan, "Python (*.py)")
        if not yol:
            return
        try:
            kod = kod_uret.uret(self.spec, os.path.basename(yol))
            with open(yol, "w", encoding="utf-8") as f:
                f.write(kod)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Uretilemedi", str(e))
            return
        QtWidgets.QMessageBox.information(
            self, "Disa aktarildi",
            "Betik yazildi:\n%s\n\n%d satir. Tek basina calisir; arayuze geri "
            "yuklenemez." % (yol, len(kod.splitlines())))

    def xml_disa_aktar(self):
        dizin = QtWidgets.QFileDialog.getExistingDirectory(
            self, "XML'lerin yazilacagi dizin",
            os.path.dirname(self.proje_yolu) if self.proje_yolu else os.getcwd())
        if not dizin:
            return
        try:
            model, _ = onbellek.kur_taze(self.spec)
            model.export_to_model_xml(os.path.join(dizin, "model.xml"))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Uretilemedi", str(e))
            return
        self.statusBar().showMessage("XML yazildi: %s/model.xml" % dizin, 6000)

    def png_kaydet(self):
        yol, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Onizlemeyi kaydet", "geometri.png", "PNG (*.png)")
        if yol:
            self.onizleme.kaydet(yol)
            self.statusBar().showMessage("Kaydedildi: %s" % yol, 5000)

    def closeEvent(self, olay):
        if self._kaydetme_sor():
            self.onizleme.kapat()      # openmc kutuphanesini serbest birak
            olay.accept()
        else:
            olay.ignore()


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    app = QtWidgets.QApplication(sys.argv[:1])
    app.setApplicationName("OpenMC Arayuz")
    tema.uygula(app)
    pencere = AnaPencere(argv[0] if argv else None)
    pencere.show()

    # Pencereyi buyutme:
    #   showMaximized() bu makinedeki pencere yoneticisinde yok sayiliyor,
    #   show()'dan hemen sonra setWindowState() de tutmuyor -- pencerenin
    #   once HARITALANMASI gerekiyor. Bu yuzden olay dongusu basladiktan
    #   kisa bir sure sonra uygulaniyor.
    def _buyut_gecikmeli():
        pencere.setWindowState(pencere.windowState() | QtCore.Qt.WindowMaximized)
    QtCore.QTimer.singleShot(120, _buyut_gecikmeli)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
