# -*- coding: utf-8 -*-
"""
================================================================================
 ana_pencere.py  --  Ana uygulama penceresi (kabuk)
================================================================================
 YERLESIM
   Ust    : menu (Dosya / Duzen / Gorunum / Yardim) + arac cubugu
   Serit  : model basligi -- "Model: ad · 17×17 yakit demeti · 2B · Ozdeger"
            + "Turu degistir..." (kor turu; yalnizca uygunluk.kor_turleri)
   Sol    : editor sekmeleri. Numarasiz; yalnizca modele UYAN sekmeler gorunur
            (cekirdek/uygunluk.gecerli_sekmeler). Sekme basligindaki isaret
            durumu soyler:  !  hata   •  eksik adim   ✓  tamam.
   Sag    : geometri onizlemesi + dogrulama listesi. YALNIZCA tasarim
            sekmelerinde (Malzemeler/Parcalar/Demet/Kor; Hesap ayarlarinda
            yalnizca dogrulama). Calistir/Analiz/Tukenme tum genisligi kullanir.
   Alt    : durum cubugu -- sonraki adim ipucu + "2 hata · 1 uyari" rozeti
            (tiklayinca bulgu listesi acilir, satir ilgili sekmeye goturur).
   Yeni model / acilis: "Ne modelliyorsun?" baslangic ekrani (baslangic.py).

 DALGA 2'DE KALDIRILANLAR
   Rehber seridi (icerigi sekme isaretlerine, ipuclarina ve durum cubuguna
   tasindi), Model menusu (F5/F6/F9 pencere kisayolu olarak kaldi), F10
   "Pencereyi buyut" (main() zaten buyutuyor), "Neden geometri ice
   aktarilamiyor?" diyalogu (ozeti ice aktarma eyleminin ipucunda), "Ornek ac"
   alt menusu (baslangic ekraninda), ayri Kisayollar diyalogu (Yardim'da).

 SEKME DIZINLERI SABITTIR
   Sekiz sekme de QTabWidget'ta kalir; uygun olmayanlar setTabVisible ile
   GIZLENIR, silinmez. Dizinler uygunluk.SEKMELER sirasidir.

 PERFORMANS NOTLARI (olcume dayali)
   1. Model onbellegi  : ayni spec icin openmc.Model yeniden kurulmaz.
                         Olculen: 21.9 ms -> 0.07 ms (bkz. cekirdek/onbellek.py)
   2. Tembel sekme yenileme : bir degisiklikte yalnizca gorunur sekme
                         yenilenir, digerleri "kirli" isaretlenip acildiklarinda
                         guncellenir. Olculen kazanc: degisiklik basina ~34 ms.
   3. Onizleme 300 ms geciktirilir (debounce); hizli yazarken tek cizime duser.

 GERI AL / YINELE
   Spec anlik goruntuleri 700 ms bosta kalinca yigina itilir; ardarda tus
   basislari tek adima birlesir. En fazla 50 adim tutulur.
================================================================================
"""

import os

from PySide6 import QtCore, QtGui, QtWidgets
from cekirdek import sema, dogrula, uygunluk
from arayuz.onizleme import OnizlemeWidget
from arayuz.sekme_analiz import AnalizSekmesi
from arayuz.sekme_tukenme import TukenmeSekmesi
from arayuz.sekme_ayar import AyarSekmesi
from arayuz.sekme_calistir import CalistirSekmesi
from arayuz.sekme_cubuk import CubukSekmesi
from arayuz.sekme_demet import DemetSekmesi
from arayuz.sekme_kor import KorSekmesi
from arayuz.sekme_malzeme import MalzemeSekmesi
from arayuz import baslangic, tema
from arayuz.ortak import DurumRozeti, cumle_basi, tekerlek_korumasi_kur
from arayuz.pencere.menuler import MenulerMixin
from arayuz.pencere.proje import ProjeMixin
from arayuz.pencere.gecmis import GecmisMixin
from arayuz.pencere.model_islemleri import (
    DOGRULAMA_SEKMELERI, EDITOR_ANAHTARI, SEKME_ADLARI, TASARIM_SEKMELERI, TUR_ADLARI,
    UYGULAMA_ADI, _KONU_BAGIMLILIK, _SABLON_ADLARI, kor_turu_degistir, model_adlari,
    model_ozet_parcalari, sekme_isaretleri, sonraki_adim, tur_hafizasini_esitle,
    yer_etiketi, yer_sekme_anahtari)


def _seviye_renk(seviye):
    """Dogrulama seviyesi rengi -- etkin temadan gelir."""
    return tema.renk({"hata": "hata", "uyari": "uyari", "bilgi": "bilgi"}.get(seviye, "bilgi"))


_SEVIYE_ADI = {"hata": "Hata", "uyari": "Uyarı", "bilgi": "Bilgi"}


# ============================================================================
# ana pencere
# ============================================================================

class AnaPencere(MenulerMixin, ProjeMixin, GecmisMixin, QtWidgets.QMainWindow):

    def __init__(self, acilis_dosyasi=None):
        super().__init__()
        # Fare tekerlegi odaksiz kutulari degistirmesin (bkz. ortak.py).
        tekerlek_korumasi_kur()
        self.setWindowTitle(UYGULAMA_ADI)
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
        # Kopyasi acilmis ornek dosyasi. YALNIZCA OKUMA icin (tukenme
        # sekmesinin onceki sonuclari); kayit asla buraya yapilmaz.
        self.ornek_kaynagi = None
        self._kirli = False
        self._bulgular = []
        self._kirli_sekmeler = set()
        self._gecmis = []
        self._gecmis_ix = -1
        self._gecmis_yaziyor = False
        self._model_var = False          # baslangic ekraninda "modele don" gorunsun mu
        self._tur_hafizasi = {}          # kor turu degisiminde eski turun alanlari
        self._adlar = {}                 # model_adlari: hafizayi ad degisimine uydurmak icin
        self._isaretler = {}

        # ---------------- editor sekmeleri ----------------
        self.sekmeler = QtWidgets.QTabWidget()
        self.sekmeler.setDocumentMode(True)
        self.sekmeler.setUsesScrollButtons(True)
        self.s_malzeme = MalzemeSekmesi()
        self.s_cubuk = CubukSekmesi()
        self.s_demet = DemetSekmesi()
        self.s_kor = KorSekmesi()
        self.s_ayar = AyarSekmesi()
        self.s_calistir = CalistirSekmesi()
        self.s_analiz = AnalizSekmesi()
        self.s_tukenme = TukenmeSekmesi()

        # Tukenme sekmesi hem EDITOR (spec'in "tukenme" bolumunu yazar) hem de
        # kosu baslatir; bu yuzden editorler listesinde ve kapi/proje yolu alir.
        self.editorler = [self.s_malzeme, self.s_cubuk, self.s_demet,
                          self.s_kor, self.s_ayar, self.s_tukenme]
        # Her sekme bir kaydirma alanina sarilir.
        #
        # SEBEP: QTabWidget'in minimum yuksekligi TUM sayfalarin en buyugudur.
        # Ayarlar sekmesi buyudukce pencerenin minimumu 1317 px'e cikmisti;
        # ekranda 1048 px oldugu icin pencere tam ekran yapilamiyor ve ALT
        # KISMI HIC GORUNMUYORDU. Kaydirma alani bu bagi koparir.
        self._sayfa_editor = {}
        self._sekme_ix = {}
        editor_sirasi = {EDITOR_ANAHTARI[ad]: getattr(self, ad) for ad in EDITOR_ANAHTARI}
        for anahtar in uygunluk.SEKMELER:
            w = editor_sirasi[anahtar]
            kaydirma = QtWidgets.QScrollArea()
            kaydirma.setWidgetResizable(True)
            kaydirma.setFrameShape(QtWidgets.QFrame.NoFrame)
            kaydirma.setWidget(w)
            self._sayfa_editor[kaydirma] = w
            self._sekme_ix[anahtar] = self.sekmeler.addTab(kaydirma, SEKME_ADLARI[anahtar])
        for e in self.editorler:
            e.degisti.connect(self._degisti)
        self.sekmeler.currentChanged.connect(self._sekme_degisti)
        self._konu_sekme = {e.KONU: e for e in self.editorler}

        # ---------------- onizleme ----------------
        self.onizleme = OnizlemeWidget()
        self.onizleme.durum.connect(self._onizleme_durum)
        self.onizleme.olcu_bulundu.connect(lambda *_: self._ozet_guncelle())
        # matplotlib gezinme cubugu 24 px simgelerle ~51 px yer kapliyordu;
        # kucuk ekranda pencere minimumunu buyuten en buyuk kalem buydu.
        self.onizleme.arac_cubugu.setIconSize(QtCore.QSize(18, 18))

        # ---------------- dogrulama paneli ----------------
        self.dogrulama = QtWidgets.QListWidget()
        self.dogrulama.setAlternatingRowColors(True)
        self.dogrulama.setToolTip("Bir satıra tıklayınca ilgili sekmeye gider.")
        # Kucuk ekranda pencerenin minimum yuksekligini sismesin (bkz. test_kabuk).
        self.dogrulama.setMinimumHeight(40)
        # Uzun bulgu metni yatay kaydirma yerine satir kaydirsin.
        self.dogrulama.setWordWrap(True)
        self.dogrulama.setResizeMode(QtWidgets.QListView.Adjust)
        self.dogrulama.itemActivated.connect(self._bulguya_git)
        self.dogrulama.itemClicked.connect(self._bulguya_git)
        self.dogrulama_ozet = DurumRozeti("-", "notr")
        dg = QtWidgets.QWidget()
        dgd = QtWidgets.QVBoxLayout(dg)
        dgd.setContentsMargins(6, 4, 6, 4)
        dgd.setSpacing(4)
        ust = QtWidgets.QHBoxLayout()
        e = QtWidgets.QLabel("Doğrulama")
        f = e.font()
        f.setBold(True)
        e.setFont(f)
        ust.addWidget(e)
        ust.addWidget(self.dogrulama_ozet)
        ust.addStretch(1)
        d_yenile = QtWidgets.QToolButton()
        d_yenile.setText("Veri kütüphanesini de denetle")
        d_yenile.setAutoRaise(True)
        d_yenile.setToolTip("Modelin istediği her nüklidin cross_sections.xml "
                            "içinde bulunup bulunmadığını denetler (yavaş, F5).")
        d_yenile.clicked.connect(lambda: self._dogrula(veri=True))
        ust.addWidget(d_yenile)
        dgd.addLayout(ust)
        dgd.addWidget(self.dogrulama)
        self._dogrulama_kutu = dg

        # ---------------- yerlesim ----------------
        sag = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        sag.addWidget(self.onizleme)
        sag.addWidget(dg)
        sag.setStretchFactor(0, 3)
        sag.setStretchFactor(1, 1)
        sag.setChildrenCollapsible(False)
        self._sag = sag

        bolucu = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        bolucu.addWidget(self.sekmeler)
        bolucu.addWidget(sag)
        # Sekme tarafi daha genis: ayarlar sekmesi iki sutunlu ve dar kalinca
        # yatay kaydirma cubugu cikiyordu.
        bolucu.setStretchFactor(0, 5)
        bolucu.setStretchFactor(1, 3)
        bolucu.setSizes([1150, 700])
        bolucu.setChildrenCollapsible(False)
        self._bolucu = bolucu

        # Model basligi seridi (arac cubugunun altinda)
        self.model_seridi = QtWidgets.QWidget()
        self.model_seridi.setObjectName("modelSeridi")
        self.model_seridi.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.model_basligi = QtWidgets.QLabel("")
        self.model_basligi.setTextFormat(QtCore.Qt.RichText)
        self.model_basligi.setTextInteractionFlags(
            QtCore.Qt.LinksAccessibleByMouse | QtCore.Qt.LinksAccessibleByKeyboard)
        self.model_basligi.linkActivated.connect(self._baslik_baglantisi)
        self.model_olcu = QtWidgets.QLabel("")
        self.model_olcu.setObjectName("soluk")
        self.d_tur = QtWidgets.QToolButton()
        self.d_tur.setText("Türü değiştir…")
        self.d_tur.setToolTip("Kor türünü değiştirir (yalnızca bu modelde "
                              "kullanılabilen türler listelenir). Geri almak için Ctrl+Z.")
        self._tur_menusu = QtWidgets.QMenu(self)
        self._tur_menusu.aboutToShow.connect(self._tur_menusunu_doldur)
        self.d_tur.setMenu(self._tur_menusu)
        self.d_tur.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        sd = QtWidgets.QHBoxLayout(self.model_seridi)
        sd.setContentsMargins(12, 2, 6, 2)
        sd.setSpacing(12)
        sd.addWidget(self.model_basligi, 1)
        sd.addWidget(self.model_olcu)
        sd.addWidget(self.d_tur)

        editor = QtWidgets.QWidget()
        md = QtWidgets.QVBoxLayout(editor)
        md.setContentsMargins(0, 0, 0, 0)
        md.setSpacing(0)
        md.addWidget(self.model_seridi)
        md.addWidget(bolucu, 1)
        self._editor = editor

        # Baslangic ekrani + editor: ayni pencerede, modal degil.
        self.baslangic = baslangic.BaslangicEkrani()
        self.baslangic.bos_istendi.connect(self._bos_basla)
        self.baslangic.ornek_istendi.connect(self.proje_ac)
        self.baslangic.dosya_istendi.connect(self.proje_ac)
        self.baslangic.ac_istendi.connect(self._ac_diyalog)
        self.baslangic.geri_istendi.connect(self._editoru_goster)
        self.yigin = QtWidgets.QStackedWidget()
        self.yigin.addWidget(self.baslangic)
        self.yigin.addWidget(editor)
        self.setCentralWidget(self.yigin)

        self._menu_kur()
        self._arac_cubugu_kur()
        self._durum_cubugu_kur()

        self.s_calistir.kapi_ayarla(self._kosu_izni)
        self.s_analiz.kapi_ayarla(self._kosu_izni)
        self.s_tukenme.kapi_ayarla(self._kosu_izni)
        for s in (self.s_calistir, self.s_analiz, self.s_tukenme):
            s.durum.connect(self._sekme_durum_mesaji)
            s.sonuc_degisti.connect(self._isaretleri_guncelle)
        # Is parcacigi ve kosu dizini Calistir'da duzenlenir (konu "calistirma"):
        # proje kirlenir, geri alinabilir.
        self.s_calistir.degisti.connect(self._degisti)
        self.s_kor.tur_degistir_istendi.connect(self._tur_menusunu_ac)

        self._dog_sayac = QtCore.QTimer(self); self._dog_sayac.setSingleShot(True)
        self._dog_sayac.setInterval(250)
        self._dog_sayac.timeout.connect(lambda: self._dogrula(veri=False))

        self._gecmis_sayac = QtCore.QTimer(self); self._gecmis_sayac.setSingleShot(True)
        self._gecmis_sayac.setInterval(700)
        self._gecmis_sayac.timeout.connect(self._gecmise_it)

        self._spec_uygula()
        self._gecmise_it(ilk=True)
        if acilis_dosyasi:
            self.proje_ac(acilis_dosyasi)
        if not self._model_var:
            self.baslangici_goster()

    # ==================================================================
    # baslangic ekrani
    # ==================================================================
    def baslangic_acik_mi(self):
        return self.yigin.currentWidget() is self.baslangic

    def baslangici_goster(self):
        """"Ne modelliyorsun?" ekranini gosterir (Dosya > Yeni, acilis)."""
        self.baslangic.son_dosyalari_ayarla(self._son_listesi())
        self.baslangic.geri_gorunur(self._model_var)
        self.yigin.setCurrentWidget(self.baslangic)
        # Baslangic ekraninda dogrulama rozeti anlamsiz (bos model "hata" sayardi).
        self.durum_rozeti.setVisible(False)
        self._model_eylemleri_guncelle()
        self.baslangic.setFocus()
        self.durum_ipucu.setText("Başlamak için bir model türü seçin.")

    def _editoru_goster(self):
        self.yigin.setCurrentWidget(self._editor)
        self.durum_rozeti.setVisible(True)
        self._model_eylemleri_guncelle()
        self._durum_ipucu_guncelle()

    def _model_eylemleri_guncelle(self):
        editorde = not self.baslangic_acik_mi()
        for e in self._model_eylemleri:
            e.setEnabled(editorde)
        self._baslik_guncelle()

    def _bos_basla(self, anahtar):
        """Kart: 'Bos basla' -- o turun sade, calisan sablonu."""
        if not self._kaydetme_sor():
            return False
        try:
            spec = baslangic.bos_sablon(anahtar)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Şablon kurulamadı", str(e))
            return False
        self._proje_kur(spec, proje_yolu=None, ornek_kaynagi=None)
        kart = baslangic.kart(anahtar)
        self._sekmeye_git(kart.get("sekme") or "malzemeler", sessiz=True)
        self.statusBar().showMessage(
            "Çalışan sade bir model kuruldu (%s). Kaydetmek için 'Farklı kaydet' "
            "kullanın." % kart["baslik"], 8000)
        return True

    # ==================================================================
    # spec yasam dongusu
    # ==================================================================
    def _proje_degisti(self):
        """
        PROJE degisti (yeni / ac / ornek / sablon): onceki projenin SONUCLARI
        silinir. Sekme degisiminde ve geri al/yinele'de CAGRILMAZ -- orada ayni
        projedeyiz. Eskiden Calistir/Analiz yeni projede eski k-eff'i ve
        katsayiyi gosteriyordu.
        """
        self.s_calistir.sifirla()
        self.s_analiz.sifirla()
        self.s_tukenme.sifirla()

    def _proje_kur(self, spec, proje_yolu, ornek_kaynagi):
        """Yeni bir projeyi pencereye yukler (ac / ornek / bos sablon)."""
        self._proje_degisti()
        self.spec = spec
        self.proje_yolu = proje_yolu
        self.ornek_kaynagi = ornek_kaynagi
        self._kirli = False
        self._tur_hafizasi = {}
        self._gecmis, self._gecmis_ix = [], -1
        self._spec_uygula()
        self._gecmise_it(ilk=True)
        self._model_var = True
        self._editoru_goster()

    def _spec_uygula(self):
        """Spec bastan yuklendi -- tum sekmeleri tazele."""
        self._hafizayi_esitle()
        self.s_tukenme.proje_ayarla(self.proje_yolu, self.ornek_kaynagi)
        for e in self.editorler:
            e.spec_yukle(self.spec)
        self._kirli_sekmeler.clear()
        self.onizleme.spec_ayarla(self.spec)
        self.s_calistir.spec_ayarla(self.spec, self.proje_yolu)
        self.s_analiz.spec_ayarla(self.spec, self.proje_yolu)
        self._sekme_gorunurlugu()
        self._dogrula(veri=False)
        self._baslik_guncelle()
        self._ozet_guncelle()

    def _degisti(self, konu="genel"):
        """
        Bir editor sekmesi spec'i degistirdi.

        Yalnizca konuya BAGIMLI sekmeler kirli isaretlenir, onlar da ancak
        acildiklarinda yenilenir (olculen: tum sekmeleri kurmak 34 ms idi ve
        gorunmeyen sekmelerin secimi sifirlaniyordu).
        """
        self._kirli = True
        self._hafizayi_esitle()
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

        if konu != "calistirma":
            # Is parcacigi / kosu dizini geometriyi degistirmez; onizleme
            # onbellek anahtari tum spec'i kapsadigi icin bosuna yeniden cizerdi.
            self.onizleme.iste()
        self._dog_sayac.start()
        self._gecmis_sayac.start()
        self._sekme_gorunurlugu()
        self._baslik_guncelle()
        self._ozet_guncelle()
        self._isaretleri_guncelle()

    def _hafizayi_esitle(self):
        """Malzeme/parca adi degistiyse ya da silindiyse tur hafizasini uydur."""
        simdiki = model_adlari(self.spec)
        if self._adlar:
            tur_hafizasini_esitle(self._tur_hafizasi, self._adlar, simdiki)
        self._adlar = simdiki

    def _gorunur_editor(self):
        """Etkin sekmenin ICINDEKI editoru dondurur (kaydirma alanini asar)."""
        return self._sayfa_editor.get(self.sekmeler.currentWidget())

    def _sekme_degisti(self, indeks):
        self._sag_panel_guncelle()
        self._sekme_renkleri()
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

    # ==================================================================
    # sekmeler: gorunurluk, isaretler, sag panel
    # ==================================================================
    def _gecerli_sekmeler(self):
        try:
            return list(uygunluk.gecerli_sekmeler(self.spec))
        except Exception:
            return list(uygunluk.SEKMELER)     # bozuk spec: hicbir seyi gizleme

    def _sekme_anahtari(self, indeks=None):
        indeks = self.sekmeler.currentIndex() if indeks is None else indeks
        for anahtar, i in self._sekme_ix.items():
            if i == indeks:
                return anahtar
        return None

    def _sekme_gorunurlugu(self):
        """Yalnizca modele uyan sekmeler gorunur; etkin sekme gizlenirse ilk
        gorunur sekmeye gecilir (Qt kendiliginden komsuya atliyordu)."""
        gorunur = self._gecerli_sekmeler()
        simdiki = self._sekme_anahtari()
        if gorunur and simdiki not in gorunur:
            self.sekmeler.setCurrentIndex(self._sekme_ix[gorunur[0]])
        for anahtar, i in self._sekme_ix.items():
            acik = anahtar in gorunur
            if self.sekmeler.isTabVisible(i) != acik:
                self.sekmeler.setTabVisible(i, acik)
        self._sag_panel_guncelle()

    def _sekmeye_git(self, anahtar, sessiz=False):
        """Sekmeye gecer; sekme bu modelde gizliyse gecmez (False)."""
        i = self._sekme_ix.get(anahtar)
        if i is None:
            return False
        if not self.sekmeler.isTabVisible(i):
            if not sessiz:
                self.statusBar().showMessage(
                    "%s sekmesi bu model türünde kullanılmıyor." % SEKME_ADLARI[anahtar], 6000)
            return False
        self.sekmeler.setCurrentIndex(i)
        return True

    def _isaretleri_guncelle(self):
        """Sekme basliklarindaki ! • ✓ isaretleri ve ipuclari."""
        hata = {}
        for b in self._bulgular:
            if b.seviye == "hata":
                k = yer_sekme_anahtari(b.yer)
                if k:
                    hata[k] = hata.get(k, 0) + 1
        self._isaretler = sekme_isaretleri(
            self.spec, hata,
            kosu_basarili=self.s_calistir.sonuc_var(),
            analiz_sonucu=self.s_analiz.sonuc_var(),
            tukenme_sonucu=self.s_tukenme.sonuc_var())
        for anahtar, i in self._sekme_ix.items():
            isaret, aciklama = self._isaretler.get(anahtar, ("", ""))
            ad = SEKME_ADLARI[anahtar]
            metin = "%s  %s" % (ad, isaret) if isaret else ad
            if self.sekmeler.tabText(i) != metin:
                self.sekmeler.setTabText(i, metin)
            self.sekmeler.setTabToolTip(i, aciklama)
        self._sekme_renkleri()
        self._durum_ipucu_guncelle()

    def _sekme_renkleri(self):
        """Hatali sekmenin basligi kirmizi; digerleri secili: vurgu, degil: soluk.
        (Isaretin kendisi baslik metnindedir; renk yalnizca HATAYI one cikarir.)"""
        cubuk = self.sekmeler.tabBar()
        simdiki = self.sekmeler.currentIndex()
        for anahtar, i in self._sekme_ix.items():
            if self._isaretler.get(anahtar, ("", ""))[0] == "!":
                renk = tema.renk("hata")
            elif i == simdiki:
                renk = tema.renk("vurgu")
            else:
                renk = tema.renk("metin_soluk")
            cubuk.setTabTextColor(i, QtGui.QColor(renk))

    def _durum_ipucu_guncelle(self):
        if self.baslangic_acik_mi():
            return
        self.durum_ipucu.setText(sonraki_adim(
            self._isaretler, self._gecerli_sekmeler(), self.onizleme.cizildi_mi()))

    def _sag_panel_guncelle(self):
        """Onizleme + dogrulama yalnizca tasarim sekmelerinde; kosu/sonuc
        sekmeleri tum genisligi kullanir."""
        anahtar = self._sekme_anahtari()
        tasarim = anahtar in TASARIM_SEKMELERI
        dogrulama = anahtar in DOGRULAMA_SEKMELERI
        kip = "tasarim" if tasarim else ("dogrulama" if dogrulama else "yok")
        onceki = getattr(self, "_sag_kip", None)
        if onceki == "tasarim" and kip != "tasarim":
            self._tasarim_boyutlari = self._bolucu.sizes()
        self.onizleme.setVisible(tasarim)
        self._dogrulama_kutu.setVisible(dogrulama)
        self._sag.setVisible(tasarim or dogrulama)
        # Yalnizca dogrulama gosterilirken (Hesap ayarlari) sag panel daralir:
        # ayar formu genislik ister; liste icin ~%28 yeter. Tasarim sekmesine
        # donunce kullanicinin ayarladigi genislik geri gelir.
        toplam = sum(self._bolucu.sizes()) or self._bolucu.width()
        if kip == "dogrulama" and onceki != "dogrulama" and toplam > 0:
            sag = max(300, int(toplam * 0.28))
            self._bolucu.setSizes([toplam - sag, sag])
        elif kip == "tasarim" and onceki not in (None, "tasarim"):
            boyut = getattr(self, "_tasarim_boyutlari", None)
            if boyut:
                self._bolucu.setSizes(boyut)
        self._sag_kip = kip

    # ==================================================================
    # model basligi ve kor turu
    # ==================================================================
    def _baslik_guncelle(self):
        if self.proje_yolu:
            ad = os.path.basename(self.proje_yolu)
        elif self.ornek_kaynagi:
            ad = "adsız — örnek: %s" % os.path.splitext(
                os.path.basename(self.ornek_kaynagi))[0]
        else:
            ad = "kaydedilmemiş"
        self.setWindowTitle("%s — %s%s" % (UYGULAMA_ADI, ad, " *" if self._kirli else ""))
        editorde = not self.baslangic_acik_mi()
        self.e_geri.setEnabled(editorde and self._gecmis_ix > 0)
        self.e_yinele.setEnabled(editorde and 0 <= self._gecmis_ix < len(self._gecmis) - 1)

    def _ozet_guncelle(self):
        """
        Model basligi. BURADA MODEL KURULMAZ -- olcu bilgisi onizlemeden gelir
        (olcu_bulundu sinyali); her degisiklikte model kurmak ~22 ms ekliyordu.
        """
        try:
            p = model_ozet_parcalari(self.spec)
        except Exception:
            p = {"ad": self.spec.get("ad", ""), "tur": "?", "boyut": "?", "mod": "?"}
        vurgu = tema.renk("vurgu")
        soluk = tema.renk("metin_soluk")
        bag = ("<a href='%%s' style='color:%s; text-decoration:none;'>%%s</a>" % vurgu)
        esc = lambda s: (str(s).replace("&", "&amp;").replace("<", "&lt;")
                         .replace(">", "&gt;"))
        ayrac = " <span style='color:%s'>·</span> " % soluk
        self.model_basligi.setText(
            "<span style='color:%s'>Model:</span> <b>%s</b>" % (soluk, esc(p["ad"]))
            + ayrac + bag % ("kor", esc(p["tur"]))
            + ayrac + bag % ("kor", esc(p["boyut"]))
            + ayrac + bag % ("mod", esc(p["mod"])))
        self.model_basligi.setToolTip(
            "Kor türüne ya da boyuta tıklayınca Kor sekmesine, hesap türüne "
            "tıklayınca Hesap ayarlarına gider.")
        olcu = self.onizleme.son_olcu
        self.model_olcu.setText("%.2f × %.2f cm" % olcu if olcu else "")

    def _baslik_baglantisi(self, hedef):
        self._sekmeye_git({"mod": "ayarlar", "kor": "kor"}.get(hedef, "kor"))

    def _tur_menusunu_ac(self):
        """Kor sekmesindeki 'Türü değiştir…' baglantisi: basliktaki menu."""
        if self.d_tur.isVisible():
            self.d_tur.showMenu()
        else:
            self._tur_menusunu_doldur()
            self._tur_menusu.exec(QtGui.QCursor.pos())

    def _tur_menusunu_doldur(self):
        self._tur_menusu.clear()
        simdiki = (self.spec.get("kor") or {}).get("tur")
        for tur in uygunluk.kor_turleri(self.spec):
            e = self._tur_menusu.addAction(TUR_ADLARI.get(tur, tur))
            e.setCheckable(True)
            e.setChecked(tur == simdiki)
            e.setData(tur)
            e.triggered.connect(lambda _c=False, t=tur: self.kor_turunu_degistir(t))

    def kor_turunu_degistir(self, tur):
        """Model basligindaki 'Turu degistir...' -- geri alinabilir tek adim."""
        if tur not in uygunluk.kor_turleri(self.spec):
            return False
        # Bekleyen duzenleme once kendi adimi olsun: geri al tur degisimini
        # onceki duzenlemeyle birlikte silmesin.
        self._gecmis_sayac.stop()
        self._gecmise_it()
        eklenen = []
        if not kor_turu_degistir(self.spec, tur, self._tur_hafizasi, eklenen):
            return False
        if self.spec.get("ad") in _SABLON_ADLARI.values() and tur in _SABLON_ADLARI:
            self.spec["ad"] = _SABLON_ADLARI[tur]
        self._kirli = True
        self._spec_uygula()
        self._gecmise_it()
        ek = (" Model bu türün gerektirdiği parçayı içermiyordu; şablondan eklendi: %s "
              "(Parçalar/Demet sekmesinde düzenleyin)." % ", ".join(eklenen)) if eklenen else ""
        self.statusBar().showMessage(
            "Kor türü: %s — geri almak için Ctrl+Z.%s" % (TUR_ADLARI.get(tur, tur), ek), 10000)
        return True

    # ==================================================================
    # dogrulama
    # ==================================================================
    def _bulgu_ogeleri(self, liste):
        """Bulgulari bir QListWidget'a yazar (panel ve acilir liste ayni bicim)."""
        liste.clear()
        for b in self._bulgular:
            oge = QtWidgets.QListWidgetItem(
                "%s · %s: %s" % (_SEVIYE_ADI.get(b.seviye, b.seviye), yer_etiketi(b.yer),
                                  cumle_basi(b.mesaj)))
            oge.setForeground(QtGui.QColor(_seviye_renk(b.seviye)))
            oge.setData(QtCore.Qt.UserRole, b.yer)
            # Eskiden: (ipucu + "\n\n") if ipucu else "" + "Tiklayinca..." --
            # oncelik yuzunden oneri varken tiklama bilgisi DUSUYORDU.
            tiklama = "Tıklayınca ilgili sekmeye gider."
            oge.setToolTip((b.oneri + "\n\n" + tiklama) if b.oneri else tiklama)
            liste.addItem(oge)
        if not self._bulgular:
            # Bos kutu "calismiyor mu?" sorusunu dogurur; sonucu soyle.
            oge = QtWidgets.QListWidgetItem("✓ Bulgu yok — model tutarlı görünüyor.")
            oge.setForeground(QtGui.QColor(tema.renk("basari")))
            oge.setFlags(QtCore.Qt.ItemIsEnabled)
            liste.addItem(oge)

    def _dogrula(self, veri=False):
        try:
            self._bulgular = dogrula.tum_kontroller(self.spec, veri_kontrolu=veri)
        except Exception as e:
            self._bulgular = [dogrula.Bulgu("hata", "dogrulama",
                                            "doğrulama sırasında hata: %s" % e)]
        self._bulgu_ogeleri(self.dogrulama)
        if self.bulgu_acilir.isVisible():
            self._bulgu_ogeleri(self.bulgu_acilir.liste)
        n_hata = sum(1 for b in self._bulgular if b.seviye == "hata")
        n_uyari = sum(1 for b in self._bulgular if b.seviye == "uyari")
        n_bilgi = sum(1 for b in self._bulgular if b.seviye == "bilgi")
        if n_hata or n_uyari:
            parca = (["%d hata" % n_hata] if n_hata else []) + \
                    (["%d uyarı" % n_uyari] if n_uyari else [])
            metin, seviye = " · ".join(parca), ("hata" if n_hata else "uyari")
        else:
            metin, seviye = "Hata yok", "basari"
        self.dogrulama_ozet.ayarla(metin, seviye)
        self.dogrulama_ozet.setToolTip("%d hata, %d uyarı, %d bilgi" % (n_hata, n_uyari, n_bilgi))
        self.durum_rozeti.ayarla(metin, seviye)
        self.durum_rozeti.setToolTip("%d hata, %d uyarı, %d bilgi — listeyi açmak için tıklayın"
                                     % (n_hata, n_uyari, n_bilgi))
        self.s_calistir.kapi_guncelle()
        self.s_analiz.kapi_guncelle()
        self.s_tukenme.kapi_guncelle()
        self._isaretleri_guncelle()

    def _bulgu_listesini_ac(self):
        self._bulgu_ogeleri(self.bulgu_acilir.liste)
        self.bulgu_acilir.goster(self.durum_rozeti)

    def _acilirdan_git(self, oge):
        self.bulgu_acilir.hide()
        self._bulguya_git(oge)

    def _bulguya_git(self, oge):
        """Dogrulama satirina tiklayinca ilgili sekmeyi ac."""
        anahtar = yer_sekme_anahtari(oge.data(QtCore.Qt.UserRole))
        if anahtar is not None:
            if self.baslangic_acik_mi():
                self._editoru_goster()
            self._sekmeye_git(anahtar)

    def _sekme_indeksi(self, editor):
        """Editorun (kaydirma alanina sarili) sekme indeksi; yoksa -1."""
        for kaydirma, w in self._sayfa_editor.items():
            if w is editor:
                return self.sekmeler.indexOf(kaydirma)
        return -1

    def _yer_sekmesi(self, yer):
        """Bulgunun 'yer' alanindan sekme indeksi; eslesme yoksa None."""
        anahtar = yer_sekme_anahtari(yer)
        return self._sekme_ix.get(anahtar) if anahtar else None

    def _onizleme_durum(self, mesaj, basarili):
        # Yalnizca SORUN bildirilir: her duzenlemeden sonra gelen "onizleme
        # guncel" mesaji durum cubugundaki sonraki-adim ipucunu surekli
        # ortuyordu. Baslangic ekraninda arkadaki bos modelin cizim hatasi da
        # gosterilmez.
        if not basarili and not self.baslangic_acik_mi():
            self.statusBar().showMessage(mesaj, 8000)
        self.s_calistir.kapi_guncelle()
        self.s_tukenme.kapi_guncelle()
        self._durum_ipucu_guncelle()

    def _sekme_durum_mesaji(self, mesaj, _basarili):
        """Calistir/Analiz/Tukenme bildirimi: durum cubugu + sekme isaretleri."""
        self.statusBar().showMessage(mesaj, 8000)
        self._isaretleri_guncelle()

    def _kosu_izni(self):
        """CALISTIR kapisi: once geometri cizilmeli, sonra hata olmamali."""
        if dogrula.hata_var(self._bulgular):
            n = sum(1 for b in self._bulgular if b.seviye == "hata")
            return False, ("Doğrulamada %d hata var — önce bunları giderin. Sağ "
                           "alttaki rozete tıklayıp bir bulguyu seçince ilgili "
                           "sekmeye gidersiniz." % n)
        if not self.onizleme.cizildi_mi():
            return False, ("Geometri önizlemesi henüz çizilmedi. Önce çiz, "
                           "sonra çalıştır: yanlış geometriyle saatlerce koşmamak "
                           "için önizlemenin çizilmesi bekleniyor.")
        uyari = sum(1 for b in self._bulgular if b.seviye == "uyari")
        if uyari:
            return True, ("Çalıştırılabilir. %d uyarı var — sonucu etkileyebilir, "
                          "doğrulama listesini gözden geçirin." % uyari)
        return True, "Model çalıştırılmaya hazır."

    def _calistir_menuden(self):
        if self.baslangic_acik_mi():
            return
        self._sekmeye_git("calistir")
        self.s_calistir.spec_ayarla(self.spec, self.proje_yolu)
        self.s_calistir.calistir()

    def closeEvent(self, olay):
        if self._kaydetme_sor():
            self.onizleme.kapat()      # openmc kutuphanesini serbest birak
            # Onceki tukenme sonucu arka planda okunuyor olabilir (~3 s).
            # Calisan bir QThread yok edilirse Qt sureci DUSURUR ("QThread:
            # Destroyed while thread is still running") -- ornegi acip hemen
            # kapatan kullanici uygulamayi cokertirdi.
            self.s_tukenme.bekle()
            olay.accept()
        else:
            olay.ignore()
