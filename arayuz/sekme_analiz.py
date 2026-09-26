# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_analiz.py  --  Parametre taramasi ve kritik arama (tek akisli sayfa)
================================================================================
 Tek bir k-eff sayisindan reaktor fizigine gecilen yer burasi:

   TARAMA        bir parametreyi aralikta degistirir, k(p) egrisini cikarir ve
                 egimden REAKTIVITE KATSAYISINI hesaplar.
                 (Doppler, moderator sicaklik, void, bor degeri, ...)

   KRITIK ARAMA  hedef k-eff'i (genellikle 1.0) veren parametre degerini bulur.
                 (kritik bor konsantrasyonu, kritik cubuk konumu, ...)

 YALNIZCA GECERLI SECENEKLER
   Parametre listesi uygunluk.gecerli_taramalar(spec, amac), hedef listesi
   uygunluk.gecerli_hedefler(spec, tur) ile suzulur: UO2'ye bor, yakita void,
   tambursuz modele tambur donmesi SUNULMAZ. Eski "yine de devam et" secenegi
   kaldirildi -- gecersiz bir secim baslatilamaz.

 Her nokta ayri bir OpenMC kosusudur; is arka planda bir QThread'de yurutulur,
 arayuz donmaz ve istenildigi an durdurulabilir. Proje degisince (sifirla)
 kusak artar; onceki projenin suren analizinin sonucu yeni projeye yazilmaz.
================================================================================
"""

import copy
import os
import time

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6 import QtCore, QtWidgets

from cekirdek import kritik_arama, sema, tarama, uygunluk
from arayuz.ortak import BosDurum, GelismisBolum, sayi, tamsayi

# Formlar okunur genislikte kalir (tam ekranda 1500 px'lik sayi kutusu okunmaz).
FORM_GENISLIGI = 760


def aciklama(metin):
    """Kisa aciklama satiri (tema: soluk metin rengi, okunur karsitlik)."""
    e = QtWidgets.QLabel(metin)
    e.setObjectName("soluk")
    e.setWordWrap(True)
    return e


def dar(duzen_ya_da_widget, genislik=FORM_GENISLIGI):
    """Bir formu en fazla 'genislik' px genislikte, sola yasli tutar."""
    if isinstance(duzen_ya_da_widget, QtWidgets.QWidget):
        w = duzen_ya_da_widget
    else:
        w = QtWidgets.QWidget()
        w.setLayout(duzen_ya_da_widget)
        duzen_ya_da_widget.setContentsMargins(0, 0, 0, 0)
    w.setMaximumWidth(genislik)
    return w


def _tema_renk(ad, vars_="#6b7785"):
    try:
        from arayuz import tema
        return tema.renk(ad)
    except Exception:
        return vars_


# ----------------------------------------------------------------------------
# Gorunen adlar. Tanimlayicilar ve fizik tarama.TURLER'dedir; burada yalnizca
# kullaniciya gosterilen ad, kisa aciklama (ipucu) ve katsayinin adi durur.
# ----------------------------------------------------------------------------
PARAMETRE_ADLARI = {
    "yakit_sicaklik": ("Yakıt sıcaklığı (Doppler)",
                       "Yakıtın sıcaklığı değişir; yoğunluğu sabit tutulur (katı yakıt)."),
    "sogutucu_sicaklik": ("Soğutucu sıcaklığı",
                          "Sıcaklıkla birlikte yoğunluk da değişir (su tablosu, Na ve "
                          "Pb-Bi korelasyonları); moderatör sıcaklık katsayısını verir."),
    "void_orani": ("Soğutucu boşluğu (void)",
                   "Soğutucu yoğunluğu boşluk oranı kadar azaltılır."),
    "bor_ppm": ("Çözünmüş bor",
                "Suya doğal bor eklenir (ppm, kütlece)."),
    "zenginlik": ("Uranyum zenginliği",
                  "U-235'in ağırlıkça yüzdesi."),
    "cubuk_daldirma": ("Kontrol çubuğu daldırma",
                       "%0 tamamen çekilmiş, %100 tamamen dalmış."),
    "tambur_donme": ("Kontrol tamburu dönmesi",
                     "0° emici kora bakar (en düşük k), 180° dışa bakar (en yüksek k)."),
    "yansitici_kalinlik": ("Yansıtıcı kuşak kalınlığı",
                           "Yansıtıcı kuşağın radyal kalınlığı."),
    "kafes_adim": ("Çubuk adımı (moderasyon oranı)",
                   "Demetteki çubuk adımı; moderatör/yakıt oranını değiştirir."),
    "kor_adim": ("Kor hücre adımı",
                 "Pin hücrede hücre adımı, tam korda demet adımı."),
    "cubuk_yaricap": ("Çubuk bölge yarıçapı",
                      "Çubuğun seçilen bölgesinin dış yarıçapı."),
    "malzeme_yogunluk": ("Malzeme yoğunluğu",
                         "Seçilen malzemenin yoğunluğu (g/cm³)."),
}

# Katsayinin adi (sonuc kartinda). Listede olmayan: "Reaktivite katsayısı".
KATSAYI_ADLARI = {
    "yakit_sicaklik": "Doppler katsayısı",
    "sogutucu_sicaklik": "Moderatör sıcaklık katsayısı",
    "void_orani": "Boşluk (void) katsayısı",
    "bor_ppm": "Bor değeri",
    "zenginlik": "Zenginlik duyarlılığı",
    "cubuk_daldirma": "Çubuk değeri (diferansiyel)",
    "tambur_donme": "Tambur değeri (diferansiyel)",
}

# Liste sirasi: en yaygin analizler basta. Tasarim etutleri (geometri ve
# yogunluk) "Gelismis" altindadir.
SIRA = ("yakit_sicaklik", "sogutucu_sicaklik", "void_orani", "bor_ppm", "zenginlik",
        "cubuk_daldirma", "tambur_donme", "yansitici_kalinlik",
        "kafes_adim", "kor_adim", "cubuk_yaricap", "malzeme_yogunluk")
GELISMIS_PARAMETRELER = ("kafes_adim", "kor_adim", "cubuk_yaricap", "malzeme_yogunluk")

_BIRIM_GORUNEN = {"g/cm3": "g/cm³", "derece": "°"}

# Makul varsayilan araliklar (bas, son, nokta). Geometri ve yogunluk
# parametrelerinde aralik modeldeki MEVCUT degerden turetilir (bkz.
# _varsayilan_aralik): sabit bir 0.35-0.45 cm yaricap araligi ic ice
# bolgeleri cakistirabiliyordu.
_VARSAYILAN = {
    "yakit_sicaklik": (600, 1200, 5), "sogutucu_sicaklik": (540, 620, 5),
    "void_orani": (0, 50, 5), "bor_ppm": (0, 2000, 5),
    "zenginlik": (2.0, 5.0, 5), "kafes_adim": (1.1, 1.5, 5),
    "malzeme_yogunluk": (0.4, 0.8, 5), "kor_adim": (1.1, 1.5, 5),
    "cubuk_yaricap": (0.35, 0.45, 5), "yansitici_kalinlik": (5, 40, 5),
    "cubuk_daldirma": (0, 100, 6), "tambur_donme": (0, 180, 5),
}


def parametre_adi(tur):
    if tur in PARAMETRE_ADLARI:
        return PARAMETRE_ADLARI[tur][0]
    return tarama.TURLER.get(tur, (tur,))[0]


def birim(tur):
    b = tarama.TURLER.get(tur, ("", "", "", ""))[2]
    return _BIRIM_GORUNEN.get(b, b)


def katsayi_birimi(tur):
    b = tarama.TURLER.get(tur, ("", "", "", ""))[3]
    for eski, yeni in _BIRIM_GORUNEN.items():
        b = b.replace(eski, yeni)
    return b


def sirali_taramalar(turler):
    """Gecerli tarama turlerini gorunen siraya dizer (bilinmeyenler sonda)."""
    turler = list(turler)
    return [t for t in SIRA if t in turler] + [t for t in turler if t not in SIRA]


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
    # Gosterilen analiz sonucu degisti (bitti / basarisiz / sifirlandi).
    sonuc_degisti = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spec = None
        self.proje_yolu = None
        self._kapi = lambda: (False, "hazır değil")
        self._isci = None
        self._sonuclar = []
        self._kusak = 0                 # proje kusagi (sifirla artirir)
        self._is_kusagi = None          # suren isin kusagi
        self._gecerli = {"katsayi": [], "kritik": []}
        self._analiz_turu = None        # son analizin turu (sonuc gosterimi icin)
        self._analiz_modu = None

        # ---------------- bos durum ----------------
        self.bos = BosDurum("Bu modelde analiz yapılamaz", "", None, "∅")

        # ---------------- mod ve parametre ----------------
        self.mod = QtWidgets.QComboBox()
        self.mod.currentIndexChanged.connect(self._mod_degisti)
        self.e_mod = QtWidgets.QLabel("Ne hesaplanacak:")

        self.tur = QtWidgets.QComboBox()
        self.tur.currentIndexChanged.connect(self._tur_degisti)

        self.gelismis = GelismisBolum("analiz_gelismis", "Gelişmiş parametreler")
        self.gelismis_ipucu = aciklama("")
        self.gelismis.ekle(self.gelismis_ipucu)
        self.gelismis.acildi.connect(self._gelismis_degisti)

        self.hedef = QtWidgets.QComboBox()
        self.hedef_etiket = QtWidgets.QLabel("Hedef:")
        self.hedef.activated.connect(self._hedef_secildi)

        self.bas = sayi(600.0, 4, -1e6, 1e6, 10.0)
        self.son = sayi(1200.0, 4, -1e6, 1e6, 10.0)
        self.adet = tamsayi(5, 2, 50, 1, "nokta")
        self.hedef_keff = sayi(1.0, 5, 0.0001, 10.0, 0.01)

        self.e_adet = QtWidgets.QLabel("Nokta sayısı:")
        self.e_hedef_keff = QtWidgets.QLabel("Hedef k-eff:")
        self.e_bas = QtWidgets.QLabel("Başlangıç:")
        self.e_son = QtWidgets.QLabel("Bitiş:")
        self.tahmin_etiket = QtWidgets.QLabel("")
        self.tahmin_etiket.setObjectName("soluk")

        form = QtWidgets.QFormLayout()
        form.addRow(self.e_mod, self.mod)
        form.addRow("Parametre:", self.tur)
        form.addRow("", self.gelismis)
        form.addRow(self.hedef_etiket, self.hedef)
        form.addRow(self.e_bas, self.bas)
        form.addRow(self.e_son, self.son)
        form.addRow(self.e_adet, self.adet)
        form.addRow(self.e_hedef_keff, self.hedef_keff)
        form.addRow("Tahmini süre:", self.tahmin_etiket)
        self.form = form

        for w in (self.bas, self.son, self.hedef_keff):
            w.valueChanged.connect(self._tahmin_guncelle)
        self.adet.valueChanged.connect(self._tahmin_guncelle)

        # ---------------- calistirma ----------------
        self.d_basla = QtWidgets.QPushButton("Taramayı başlat")
        self.d_basla.setObjectName("birincil")
        self.d_basla.setMinimumHeight(34)
        self.d_basla.setMinimumWidth(150)
        self.d_dur = QtWidgets.QPushButton("Durdur")
        self.d_dur.setMinimumHeight(34)
        self.d_dur.setEnabled(False)
        self.d_basla.clicked.connect(self._basla)
        self.d_dur.clicked.connect(self._durdur)
        self.ilerleme = QtWidgets.QProgressBar()
        self.ilerleme.setRange(0, 1)
        self.ilerleme.setValue(0)
        self.kapi_etiket = QtWidgets.QLabel("-")
        self.kapi_etiket.setWordWrap(True)

        dugme = QtWidgets.QHBoxLayout()
        dugme.addWidget(self.d_basla)
        dugme.addWidget(self.d_dur)
        dugme.addWidget(self.ilerleme, 1)

        # ---------------- sonuc ----------------
        self.sonuc_kutusu = QtWidgets.QLabel("Henüz analiz yapılmadı.")
        self.sonuc_kutusu.setWordWrap(True)
        self.sonuc_kutusu.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.sonuc_kutusu.setTextFormat(QtCore.Qt.RichText)
        self.sonuc_kutusu.setStyleSheet(
            "background: palette(base); padding: 12px; font-size: 11pt; "
            "border: 1px solid palette(mid); border-radius: 10px;")

        self.figur = Figure(figsize=(5, 2.6), tight_layout=True)
        self.tuval = FigureCanvasQTAgg(self.figur)
        self.tuval.setFixedHeight(260)
        self.eksen = self.figur.add_subplot(111)
        self._grafik_sifirla()

        self.tablo = QtWidgets.QTableWidget(0, 4)
        self.tablo.setHorizontalHeaderLabels(["Değer", "k-eff", "±", "ρ [pcm]"])
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tablo.setMinimumHeight(120)
        self.tablo.setMaximumHeight(220)

        # ---------------- yerlesim ----------------
        self.icerik = QtWidgets.QWidget()
        ic = QtWidgets.QVBoxLayout(self.icerik)
        ic.setContentsMargins(0, 0, 0, 0)
        ic.setSpacing(8)
        ic.addWidget(aciklama(
            "Bir parametreyi tarayıp eğimden reaktivite katsayısını ya da hedef k-eff'i "
            "veren değeri bulursunuz. Yalnızca bu modelde anlamlı parametreler listelenir; "
            "her nokta ayrı bir OpenMC koşusudur."))
        ic.addWidget(dar(form))
        ic.addLayout(dugme)
        ic.addWidget(self.kapi_etiket)
        ic.addWidget(self.sonuc_kutusu)
        ic.addWidget(self.tuval)
        ic.addWidget(self.tablo)
        ic.addStretch(1)

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(self.bos, 1)
        duzen.addWidget(self.icerik, 1)

        self._listeleri_doldur()

    # ==================================================================
    # disaridan
    # ==================================================================
    def kapi_ayarla(self, fonksiyon):
        self._kapi = fonksiyon

    def spec_ayarla(self, spec, proje_yolu=None):
        """
        Ana pencere bunu sekmeye HER giriste cagirir: secili mod, parametre,
        hedef ve aralik (hala gecerliyse) korunur -- eskiden "su" secip geri
        gelen kullanici "uo2" buluyordu.
        """
        self.spec = spec
        self.proje_yolu = proje_yolu
        self._listeleri_doldur()
        self.kapi_guncelle()
        self._tahmin_guncelle()

    def sonuc_var(self):
        """Bu projede en az bir basarili analiz noktasi gosteriliyor mu."""
        return any(s.get("keff") for s in self._sonuclar)

    def sifirla(self):
        """
        PROJE degisince onceki projenin analiz sonucunu siler (sekme
        degisiminde CAGRILMAZ). Kusak artar: onceki projede baslamis ve hala
        suren bir analizin noktalari/sonucu yeni projeye yazilmaz.
        """
        self._kusak += 1
        self._sonuclar = []
        self._analiz_turu = self._analiz_modu = None
        self.tablo.setRowCount(0)
        self._grafik_sifirla()
        self.sonuc_kutusu.setText("Henüz analiz yapılmadı.")
        self.tahmin_etiket.setText("")
        self.ilerleme.setRange(0, 1)
        self.ilerleme.setValue(0)
        self.hedef.clear()         # onceki projenin hedefi yeni projeye tasinmasin
        self._sonuc_gorunumu()
        self.kapi_guncelle()
        self.sonuc_degisti.emit()

    def kapi_guncelle(self):
        if self._isci is not None:
            if self._eski_is():
                self._kapi_yaz(False, "Önceki projenin analizi arka planda sürüyor; "
                                      "sonucu bu projeye yazılmayacak. Yeni analiz için "
                                      "Durdur ile sonlandırın.")
            return
        izin, mesaj = self._kapi()
        izin = izin and self.tur.count() > 0
        self.d_basla.setEnabled(izin)
        self._kapi_yaz(izin, mesaj)

    def _kapi_yaz(self, izin, mesaj):
        self.kapi_etiket.setStyleSheet(
            "color: %s;" % (_tema_renk("metin_soluk") if izin else _tema_renk("hata", "#b3261e")))
        self.kapi_etiket.setText(mesaj)

    def _eski_is(self):
        return self._is_kusagi is not None and self._is_kusagi != self._kusak

    # ==================================================================
    # listeler (uygunluk'tan)
    # ==================================================================
    def _listeleri_doldur(self):
        """Mod, parametre ve hedef listelerini modele gore kurar; secim korunur."""
        if self.spec is None:
            self._gecerli = {"katsayi": [], "kritik": []}
        else:
            try:
                self._gecerli = {"katsayi": uygunluk.gecerli_taramalar(self.spec, "katsayi"),
                                 "kritik": uygunluk.gecerli_taramalar(self.spec, "kritik")}
            except Exception:
                self._gecerli = {"katsayi": [], "kritik": []}

        # --- mod ---
        onceki = self.mod.currentData()
        self.mod.blockSignals(True)
        self.mod.clear()
        if self._gecerli["katsayi"]:
            self.mod.addItem("Reaktivite katsayısı (parametre taraması)", "tarama")
        if self._gecerli["kritik"]:
            self.mod.addItem("Kritik arama (hedef k-eff'i veren değer)", "arama")
        i = self.mod.findData(onceki)
        self.mod.setCurrentIndex(i if i >= 0 else 0)
        self.mod.blockSignals(False)
        tek_mod = self.mod.count() <= 1
        self.form.setRowVisible(self.e_mod, not tek_mod)

        # --- bos durum ---
        bos = not self._gecerli["katsayi"]
        self.bos.setVisible(bos)
        self.icerik.setVisible(not bos)
        if bos:
            self.bos.ayarla(metin=self._bos_nedeni())

        self._mod_gorunumu()
        self._turleri_doldur()

    def _bos_nedeni(self):
        if self.spec is None:
            return "Önce bir model açın."
        try:
            oz = uygunluk.model_ozeti(self.spec)
        except Exception:
            return "Model okunamadı; doğrulama listesine bakın."
        if oz.get("mod") != "eigenvalue":
            return ("Reaktivite katsayıları ve kritik arama k-eff üzerinden hesaplanır; "
                    "bu modelin hesap türü Sabit kaynak (k-eff tanımsız). Hesap "
                    "ayarları sekmesinde hesap türünü Özdeğer (k-eff) yapın.")
        if not oz.get("fisil"):
            return ("Geometride fisil (yakıt) malzeme yok; k-eff tanımsız olduğu için "
                    "reaktivite hesaplanamaz.")
        return "Bu modelde taranabilecek bir parametre bulunamadı."

    def _amac(self):
        return "kritik" if self.mod.currentData() == "arama" else "katsayi"

    def _sunulan_turler(self):
        """Parametre listesinde gosterilecek turler (Gelismis kapaliysa etutler yok)."""
        gecerli = sirali_taramalar(self._gecerli[self._amac()])
        ana = [t for t in gecerli if t not in GELISMIS_PARAMETRELER]
        ileri = [t for t in gecerli if t in GELISMIS_PARAMETRELER]
        if self.gelismis.acik_mi() or not ana:
            return ana, ileri
        return ana, []

    def _turleri_doldur(self):
        onceki = self.tur.currentData()
        ana, ileri = self._sunulan_turler()
        self.tur.blockSignals(True)
        self.tur.clear()
        for t in ana + ileri:
            self.tur.addItem("%s  [%s]" % (parametre_adi(t), birim(t)), t)
            aciklama = PARAMETRE_ADLARI.get(t, ("", ""))[1]
            if aciklama:
                self.tur.setItemData(self.tur.count() - 1, aciklama, QtCore.Qt.ToolTipRole)
        if ana and ileri:
            self.tur.insertSeparator(len(ana))
        i = self.tur.findData(onceki)
        self.tur.setCurrentIndex(i if i >= 0 else 0)
        self.tur.blockSignals(False)

        # Gelismis bolum yalnizca bu modelde gecerli bir tasarim etudu varsa
        tum_ileri = [t for t in sirali_taramalar(self._gecerli[self._amac()])
                     if t in GELISMIS_PARAMETRELER]
        self.form.setRowVisible(self.gelismis, bool(tum_ileri) and bool(ana))
        if tum_ileri:
            self.gelismis_ipucu.setText(
                "Açıkken parametre listesinde tasarım etütleri de yer alır: %s. "
                "Bunlar reaktivite katsayısı değil, tasarım duyarlılığıdır."
                % ", ".join(parametre_adi(t).lower() for t in tum_ileri))

        if self.tur.currentData() != onceki:
            self._tur_degisti()          # yeni parametre: hedefler + varsayilan aralik
        else:
            self._hedefleri_doldur(koru=True)
            self._birim_uygula()

    def _gelismis_degisti(self, _acik):
        self._turleri_doldur()
        self.kapi_guncelle()

    # ==================================================================
    def _mod_degisti(self, *_):
        self._mod_gorunumu()
        self._turleri_doldur()
        self._tahmin_guncelle()

    def _mod_gorunumu(self):
        arama = self.mod.currentData() == "arama"
        self.form.setRowVisible(self.e_adet, not arama)
        self.form.setRowVisible(self.e_hedef_keff, arama)
        self.e_bas.setText("Alt sınır:" if arama else "Başlangıç:")
        self.e_son.setText("Üst sınır:" if arama else "Bitiş:")
        self.d_basla.setText("Kritik aramayı başlat" if arama else "Taramayı başlat")

    def _tur_degisti(self, *_):
        self._hedefleri_doldur()
        self._birim_uygula()
        self._aralik_uygula()
        self._tahmin_guncelle()

    def _hedef_secildi(self, *_):
        """Kullanici hedefi degistirdi: aralik o hedefin mevcut degerine gore."""
        self._aralik_uygula()
        self._tahmin_guncelle()

    def _birim_uygula(self):
        tur = self.tur.currentData()
        sonek = (" " + birim(tur)) if tur else ""
        if sonek.strip() == "°":
            sonek = "°"
        for w in (self.bas, self.son):
            w.setSuffix(sonek)

    def _aralik_uygula(self):
        tur = self.tur.currentData()
        if tur is None:
            return
        a, b, n = self._varsayilan_aralik(tur, self.hedef.currentData())
        self.bas.setValue(a)
        self.son.setValue(b)
        self.adet.setValue(n)

    def _varsayilan_aralik(self, tur, hedef):
        """
        (bas, son, nokta). Geometri/yogunluk parametrelerinde modeldeki MEVCUT
        degerden turetilir; ic ice bolgeler cakismasin diye komsu yaricaplarla
        sinirlanir.
        """
        a, b, n = _VARSAYILAN.get(tur, (0.0, 1.0, 5))
        spec = self.spec or {}
        try:
            if tur == "cubuk_yaricap" and hedef:
                c = sema.cubuk_bul(spec, hedef[0])
                bolgeler = c["bolgeler"]
                i = int(hedef[1])
                r = float(bolgeler[i]["r"])
                r_once = float(bolgeler[i - 1]["r"]) if i > 0 else 0.0
                r_sonra = bolgeler[i + 1].get("r") if i + 1 < len(bolgeler) else None
                a = max(0.9 * r, 0.5 * (r_once + r))
                b = min(1.1 * r, 0.5 * (r + float(r_sonra))) if r_sonra else 1.05 * r
            elif tur in ("kafes_adim", "kor_adim"):
                if tur == "kafes_adim":
                    adim = float(sema.demet_bul(spec, hedef)["adim"])
                else:
                    adim = float((spec.get("kor") or {}).get("adim") or 0.0)
                if adim > 0:
                    r_en = max([float(x["r"]) for c in spec.get("cubuklar", [])
                                for x in c.get("bolgeler") or [] if x.get("r")] or [0.0])
                    if tur == "kor_adim" and (spec.get("kor") or {}).get("tur") == "kare_kafes":
                        a, b = adim, 1.05 * adim     # demetler ust uste binmesin
                    else:
                        a, b = max(0.95 * adim, 2.02 * r_en), 1.25 * adim
            elif tur == "malzeme_yogunluk" and hedef:
                rho = float(sema.malzeme_bul(spec, hedef)["yogunluk"]["deger"])
                a, b = 0.9 * rho, 1.1 * rho
            elif tur == "sogutucu_sicaklik" and hedef:
                T = float(sema.malzeme_bul(spec, hedef).get("sicaklik") or 0.0)
                if T > 0:
                    a, b = T - 40.0, T + 40.0
                    m = sema.malzeme_bul(spec, hedef)
                    from cekirdek import malzeme_kutup as mk
                    if tarama._yogunluk_korelasyonu(m)[0] is mk.su_yogunluk:
                        a, b = max(a, 280.0), min(b, 620.0)   # doymus su tablosu
            elif tur == "yansitici_kalinlik":
                k = float(((spec.get("kor") or {}).get("yansitici") or {}).get("kalinlik") or 0.0)
                if k > 0:
                    a, b = max(0.25 * k, 1.0), 2.0 * k
        except Exception:
            pass
        yuvarla = 4 if tur in ("cubuk_yaricap", "kafes_adim", "kor_adim",
                               "malzeme_yogunluk") else 1
        return round(a, yuvarla), round(b, yuvarla), n

    def _hedefleri_doldur(self, koru=False):
        """
        Parametre turune gore gecerli hedefleri listeler (uygunluk'tan).
        koru=True: onceki secim (hala listedeyse) geri secilir.
        """
        onceki = self.hedef.currentData() if koru and self.hedef.count() else None
        self._hedefleri_listele()
        if onceki is not None:
            for j in range(self.hedef.count()):
                if self.hedef.itemData(j) == onceki:
                    self.hedef.setCurrentIndex(j)
                    break

    def _hedefleri_listele(self):
        self.hedef.clear()
        tur = self.tur.currentData()
        if self.spec is None or tur is None:
            self.form.setRowVisible(self.hedef_etiket, False)
            return
        try:
            hedefler = uygunluk.gecerli_hedefler(self.spec, tur)
        except Exception:
            hedefler = []
        hedef_turu = tarama.TURLER.get(tur, (None, None, None, None))[1]
        if hedef_turu == "malzeme":
            for ad in hedefler:
                m = sema.malzeme_bul(self.spec, ad) or {"ad": ad}
                self.hedef.addItem(sema.malzeme_etiketi(m), ad)
            self.hedef_etiket.setText("Hedef malzeme:")
        elif hedef_turu == "demet":
            for ad in hedefler:
                self.hedef.addItem(ad, ad)
            self.hedef_etiket.setText("Hedef demet:")
        elif hedef_turu == "kontrol_cubugu":
            for ad in hedefler:
                c = sema.cubuk_bul(self.spec, ad) or {}
                self.hedef.addItem("%s  (şu an %%%.1f dalmış)"
                                   % (ad, c.get("daldirma") or 0.0), ad)
            self.hedef_etiket.setText("Kontrol çubuğu:")
        elif hedef_turu == "cubuk_bolge":
            for ad, i in hedefler:
                c = sema.cubuk_bul(self.spec, ad) or {}
                b = (c.get("bolgeler") or [{}] * (i + 1))[i]
                self.hedef.addItem("%s — %d. bölge (r = %.4g cm, %s)"
                                   % (ad, i + 1, b.get("r") or 0.0,
                                      "Boş (madde yok)" if b.get("malzeme") in (None, sema.BOSLUK)
                                      else b.get("malzeme")),
                                   (ad, i))
            self.hedef_etiket.setText("Hedef bölge:")
        else:
            # kor ayari: hedef secimi yok (liste [None])
            for h in hedefler:
                self.hedef.addItem("", h)
            self.hedef_etiket.setText("Hedef:")
        kor_ayari = hedefler == [None]
        self.form.setRowVisible(self.hedef_etiket, bool(hedefler) and not kor_ayari)

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
        if self._isci is not None and not self._eski_is():
            return                        # suren analiz kendi olcumunu yaziyor
        tek = self._tek_kosu_tahmini()
        tarama_modu = self.mod.currentData() != "arama"
        adet = self.adet.value() if tarama_modu else 6
        ek = "" if tarama_modu else " (arama genellikle 4–8 koşu sürer)"
        self.tahmin_etiket.setText(
            "~%s   (%d koşu × ~%s)%s"
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
    def _sonuc_gorunumu(self):
        """Sonuc karti, grafik ve tablo yalnizca bir analiz baslamissa gorunur."""
        var = bool(self._sonuclar) or (self._isci is not None and not self._eski_is()) \
            or self._analiz_turu is not None
        self.sonuc_kutusu.setVisible(var)
        self.tuval.setVisible(var)
        self.tablo.setVisible(var)

    def _grafik_sifirla(self):
        self.eksen.clear()
        self.eksen.set_xlabel("parametre", fontsize=8)
        self.eksen.set_ylabel("k-eff", fontsize=8)
        self.eksen.tick_params(labelsize=7)
        self.eksen.grid(alpha=0.3)
        self.tuval.draw_idle()

    def _grafik_guncelle(self, kats=None):
        from arayuz import tema as _t
        self.eksen.clear()
        self.eksen.grid(alpha=0.3)
        gecerli = [s for s in self._sonuclar if s.get("keff")]
        if gecerli:
            x = [s["deger"] for s in gecerli]
            y = [s["keff"] for s in gecerli]
            e = [s["sapma"] for s in gecerli]
            self.eksen.errorbar(x, y, yerr=e, fmt="o-", ms=4, lw=1.2,
                                capsize=3, color=_t.renk("vurgu"))
            if self._analiz_modu == "arama":
                self.eksen.axhline(self.hedef_keff.value(), color=_t.renk("hata"),
                                   ls="--", lw=1.0, label="hedef k")
                self.eksen.legend(fontsize=7)
            elif kats:
                # rho dogrusunu k olceginde goster: rho = 1 - 1/k -> k = 1/(1-rho)
                import numpy as np
                px = np.linspace(min(x), max(x), 50)
                rho = (kats["kesisim"] + kats["egim"] * px) / 1.0e5
                self.eksen.plot(px, 1.0 / (1.0 - rho), lw=1.0, ls="--",
                                color=_t.renk("uyari"), label="doğrusal uyum")
                self.eksen.legend(fontsize=7)
        tur = self._analiz_turu or self.tur.currentData()
        self.eksen.set_xlabel("%s [%s]" % (parametre_adi(tur), birim(tur)) if tur
                              else "parametre", fontsize=8)
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
            degerler = ["%.6g" % s["deger"], "başarısız", "—", s.get("hata", "")[:60]]
        for i, d in enumerate(degerler):
            self.tablo.setItem(satir, i, QtWidgets.QTableWidgetItem(d))
        self.tablo.scrollToBottom()

    # ==================================================================
    def _secim_gecerli(self):
        """
        Secili (tur, hedef) bu modelde gecerli mi? Listeler zaten suzuldugu icin
        normalde hep gecerlidir; model sekme acikken degistiyse yakalanir.
        Gecersiz secim BASLATILMAZ (eski "yine de devam et" secenegi yok).
        """
        if self.spec is None:
            return False, "Model yok."
        tur = self.tur.currentData()
        if tur is None:
            return False, "Bu modelde taranabilecek bir parametre yok."
        if tur not in uygunluk.gecerli_taramalar(self.spec, self._amac()):
            return False, ("'%s' bu modelde artık geçerli değil." % parametre_adi(tur))
        if self.hedef.count() == 0 or \
                self.hedef.currentData() not in uygunluk.gecerli_hedefler(self.spec, tur):
            return False, ("Seçili hedef bu parametre için geçerli değil "
                           "(model değişmiş olabilir).")
        return True, ""

    def _dizin(self, onek):
        taban = sema.kosu_tabani(self.proje_yolu)
        yol = os.path.join(taban, "%s_%s" % (onek, self.tur.currentData()))
        os.makedirs(yol, exist_ok=True)
        return yol

    def _basla(self):
        izin, mesaj = self._kapi()
        if not izin:
            QtWidgets.QMessageBox.warning(self, "Çalıştırılamaz", mesaj)
            return
        if self._isci is not None:
            return
        uygun, sebep = self._secim_gecerli()
        if not uygun:
            QtWidgets.QMessageBox.warning(
                self, "Seçim geçerli değil",
                "%s\n\nListeler modele göre yenilendi; seçimi gözden geçirin." % sebep)
            self._listeleri_doldur()
            self.kapi_guncelle()
            return

        tur = self.tur.currentData()
        hedef = self.hedef.currentData()
        # Analiz boyunca model SABIT: kullanici baska sekmede duzenleme yapsa da
        # taramanin noktalari ayni modelden turetilir.
        spec = copy.deepcopy(self.spec)
        n = int(spec.get("calistirma", {}).get("is_parcacigi", 8) or 8)
        self._is_kusagi = self._kusak
        self._analiz_turu = tur
        self._analiz_modu = self.mod.currentData()
        self._sonuclar = []
        self.tablo.setRowCount(0)
        self._grafik_sifirla()
        self.sonuc_kutusu.setText("Çalışıyor…")

        if self._analiz_modu == "tarama":
            degerler = tarama.noktalar(self.bas.value(), self.son.value(),
                                       self.adet.value())
            self.ilerleme.setRange(0, len(degerler))
            self.ilerleme.setValue(0)
            self._isci = TaramaIsci(spec, tur, hedef, degerler,
                                    self._dizin("tarama"), n, self)
            self._isci.nokta.connect(self._tarama_noktasi)
            self._isci.bitti.connect(self._tarama_bitti)
            self._isci.hata.connect(self._hata)
        else:
            self.ilerleme.setRange(0, 0)     # belirsiz
            self._isci = AramaIsci(spec, tur, hedef, self.bas.value(),
                                   self.son.value(), self.hedef_keff.value(),
                                   self._dizin("arama"), n, self)
            self._isci.adim.connect(self._arama_adimi)
            self._isci.bitti.connect(self._arama_bitti)
            self._isci.hata.connect(self._hata)

        self._isci.finished.connect(self._isci_bitti)
        self._baslangic = time.perf_counter()
        self._son_nokta_zamani = self._baslangic
        self.d_basla.setEnabled(False)
        self.d_dur.setEnabled(True)
        self._kapi_yaz(True, "Analiz sürüyor: %s — her nokta ayrı bir koşu."
                       % parametre_adi(tur))
        self._sonuc_gorunumu()
        self._isci.start()
        self.sonuc_degisti.emit()
        self.durum.emit("Analiz başladı", True)

    def _durdur(self):
        if self._isci:
            self._isci.durdur()
            self.durum.emit("Durdurma istendi — süren koşu bitince duracak", True)

    def _isci_bitti(self):
        eski = self._eski_is()
        if not eski and hasattr(self, "_baslangic"):
            self.tahmin_etiket.setText(
                "tamamlandı — toplam %s"
                % self._sure_metni(time.perf_counter() - self._baslangic))
        isci, self._isci = self._isci, None
        if isci is not None:
            isci.deleteLater()
        self._is_kusagi = None
        self.d_dur.setEnabled(False)
        self.ilerleme.setRange(0, 1)
        self.ilerleme.setValue(1 if (not eski and self._sonuclar) else 0)
        self.kapi_guncelle()
        self._sonuc_gorunumu()
        if eski:
            self._tahmin_guncelle()
            self.durum.emit("Önceki projenin analizi bitti; sonucu bu projeye yazılmadı.", True)

    def _hata(self, mesaj):
        if self._eski_is():
            return
        self.sonuc_kutusu.setText("<b>Hata:</b> %s" % mesaj)
        self.sonuc_degisti.emit()
        self.durum.emit("Analiz hatası: %s" % mesaj, False)

    # ------------------------------------------------------------------
    def _tarama_noktasi(self, i, toplam, s):
        if self._eski_is():
            return
        simdi = time.perf_counter()
        self._hizi_kalibre_et(simdi - self._son_nokta_zamani)
        self._son_nokta_zamani = simdi
        self._sonuclar.append(s)
        self._tabloya_ekle(s)
        self.ilerleme.setValue(i + 1)
        self._grafik_guncelle()
        kalan = (toplam - i - 1) * (simdi - self._baslangic) / (i + 1)
        self.tahmin_etiket.setText(
            "geçen %s  |  kalan ~%s  (ölçüme göre)"
            % (self._sure_metni(simdi - self._baslangic), self._sure_metni(kalan)))

    def _tarama_bitti(self, sonuclar, notlar):
        if self._eski_is():
            return
        self._sonuclar = sonuclar
        tur = self._analiz_turu or self.tur.currentData()
        kats = tarama.katsayi(sonuclar)
        self._grafik_guncelle(kats)
        kbirim = katsayi_birimi(tur)
        if kats:
            metin = ("<b>%s = %+.3f &plusmn; %.3f %s</b><br>"
                     "doğrusal uyum R&sup2; = %.4f, %d nokta<br><br>%s"
                     % (KATSAYI_ADLARI.get(tur, "Reaktivite katsayısı"),
                        kats["egim"], kats["egim_sapma"], kbirim,
                        kats["r2"], kats["nokta"], tarama.yorumla(tur, kats)))
        else:
            metin = "Katsayı hesaplanamadı (yeterli geçerli nokta yok)."
        if notlar:
            metin += "<br><br><i>Notlar:</i><br>" + "<br>".join("&bull; " + n for n in notlar)
        self.sonuc_kutusu.setText(metin)
        self.sonuc_degisti.emit()
        self.durum.emit("Tarama tamamlandı", True)

    def _arama_adimi(self, i, kayit):
        if self._eski_is():
            return
        simdi = time.perf_counter()
        self._hizi_kalibre_et(simdi - self._son_nokta_zamani)
        self._son_nokta_zamani = simdi
        self.tahmin_etiket.setText("geçen %s  |  %d. koşu bitti"
                                   % (self._sure_metni(simdi - self._baslangic), i + 1))
        self._sonuclar.append(kayit)
        self._tabloya_ekle(kayit)
        self._grafik_guncelle()

    def _arama_bitti(self, s):
        if self._eski_is():
            return
        self._grafik_guncelle()
        tur = self._analiz_turu or self.tur.currentData()
        if s.basarili:
            bel = ("" if s.cozum_belirsizlik is None
                   else " &plusmn; %.4g" % s.cozum_belirsizlik)
            metin = ("<b>Çözüm: %s = %.6g%s %s</b><br>"
                     "k = %.5f &plusmn; %.5f &nbsp;&nbsp; (%d koşu)<br><br>%s"
                     % (parametre_adi(tur), s.cozum, bel, birim(tur),
                        s.cozum_keff, s.cozum_sapma, len(s.adimlar), s.mesaj))
        else:
            metin = "<b>Çözüm bulunamadı.</b><br><br>%s" % s.mesaj
        self.sonuc_kutusu.setText(metin)
        self.sonuc_degisti.emit()
        self.durum.emit("Kritik arama tamamlandı", s.basarili)
