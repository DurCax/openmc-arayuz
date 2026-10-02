# -*- coding: utf-8 -*-
"""
================================================================================
 ana_pencere.py  --  Ana uygulama penceresi (Dalga 2 kabugu)
================================================================================
 YERLESIM (maketler/kabuk_*.png)
   Ust    : menu (Dosya / Duzen / Gorunum / Yardim)
   Serit  : UstCubuk -- ikonlu hizli eylemler, model adi + tur rozeti + ozet,
            "Turu degistir…", komut arama alani (Ctrl+K) ve BIRINCIL
            "▶ Calistir" dugmesi (kosarken "Durdur"a doner).
   Sol    : KenarCubugu -- is akisi sirasinda sayfalar, gruplu (Model / Hesap /
            Sonuc). Durum isaretleri ikonlasti: ✓ tamam, ! hata, • eksik adim.
            Uygun olmayan sayfalar GIZLENIR (uygunluk.gecerli_sekmeler).
   Orta   : QStackedWidget; her sayfa bir QScrollArea'dir (pencerenin minimum
            yuksekligi en buyuk sayfaya baglanmasin diye).
   Sag    : OnizlemePaneli -- acik ve daraltilabilir (QSettings'te hatirlanir),
            yalnizca tasarim sayfalarinda (Malzemeler/Parcalar/Demet/Kor).
   Alt    : DogrulamaSeridi -- "✓ Dogrulama: hata yok", rozet (tiklayinca bulgu
            listesi), ilk bulgu + "Bulguya git", sonraki adim ipucu.
   Gecici mesajlar durum cubugunu degil BILDIRIM'i (toast) kullanir.
   Yeni model / acilis: "Ne modelliyorsun?" baslangic ekrani (baslangic.py).

 SAYFA SIRASI SABITTIR
   Sekiz sayfa da yiginda kalir; uygun olmayanlar kenar cubugunda gizlenir,
   silinmez. Sira uygunluk.SEKMELER sirasidir.

 PERFORMANS NOTLARI (olcume dayali)
   1. Model onbellegi  : ayni spec icin openmc.Model yeniden kurulmaz.
   2. Tembel sayfa yenileme : bir degisiklikte yalnizca gorunur sayfa
                         yenilenir, digerleri "kirli" isaretlenip acildiklarinda
                         guncellenir. Olculen kazanc: degisiklik basina ~34 ms.
   3. Onizleme 300 ms geciktirilir (debounce).

 GERI AL / YINELE
   Spec anlik goruntuleri 700 ms bosta kalinca yigina itilir; en fazla 50 adim.
================================================================================
"""

import os

from PySide6 import QtCore, QtGui, QtWidgets
from cekirdek import sema, uygunluk
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from arayuz.bilesenler import KenarCubugu, bildir
from arayuz.onizleme import OnizlemeWidget
from arayuz.onizleme_kapsam import PencereKapsami
from arayuz.sekme_analiz import AnalizSekmesi
from arayuz.sekme_tukenme import TukenmeSekmesi
from arayuz.sekme_ayar import AyarSekmesi
from arayuz.sekme_calistir import CalistirSekmesi
from arayuz.sekme_cubuk import CubukSekmesi
from arayuz.sekme_demet import DemetSekmesi
from arayuz.sekme_kor import KorSekmesi
from arayuz.sekme_malzeme import MalzemeSekmesi
from arayuz import baslangic, tema
from arayuz.baslangic_akis import BaslangicAkisi
from arayuz.ortak import tekerlek_korumasi_kur, tekerlek_suzgeci_askida
from arayuz.pencere import kabuk
from arayuz.tasarim import stil as _stil
from cekirdek.geometri import yoklama_arka
from arayuz.pencere.menuler import MenulerMixin
from arayuz.pencere.proje import ProjeMixin
from arayuz.pencere.gecmis import GecmisMixin
from arayuz.pencere.gezinme import GezinmeCephesi
from arayuz.veri import kayit as veri_kayit
from arayuz.pencere.dogrulama_seridi import (  # noqa: F401 -- tasindi (T2)
    _SEVIYE_ADI, DogrulamaMixin, _seviye_renk)
from arayuz.pencere.model_islemleri import (
    EDITOR_ANAHTARI, SEKME_ADLARI, TASARIM_SEKMELERI, TUR_ADLARI,
    UYGULAMA_ADI, _KONU_BAGIMLILIK, _SABLON_ADLARI, kor_turu_degistir, model_adlari,
    model_ozet_parcalari, sekme_isaretleri, sonraki_adim,
    tur_hafizasini_esitle, yer_sekme_anahtari)


_log = kaydedici(__name__)


_EN_KUCUK = (1280, 760)
_VARSAYILAN_BOLUCU = (820, 360)      # [sayfa, onizleme] px, ilk acilis


# ============================================================================
# ana pencere
# ============================================================================

class AnaPencere(DogrulamaMixin, BaslangicAkisi, GezinmeCephesi, MenulerMixin, ProjeMixin,
                 GecmisMixin, QtWidgets.QMainWindow):

    def __init__(self, acilis_dosyasi=None):
        super().__init__()
        # Fare tekerlegi odaksiz kutulari degistirmesin (bkz. ortak.py).
        tekerlek_korumasi_kur()
        uygulama_adi = UYGULAMA_ADI        # cekirdek sabiti; etkin dilde gosterilir
        self.setWindowTitle(_(uygulama_adi))
        # H1b: kurulumda tekerlek suzgeci askida (her olayda Python'a gecis ~1.4 s
        # CPU) ve uygulama QSS'i kurulumdan SONRA bir kez uygulanir (stil.py)
        with tekerlek_suzgeci_askida(), _stil.sonradan_uygula():
            self._boyut_kur()
            self._durum_kur()
            self._sayfalari_kur()
            self._onizleme_kur()
            self.onizleme_kapsami = PencereKapsami(self)   # sayfa + secim -> onizleme kapsami (K5)
            self._menu_kur()
            self._arac_cubugu_kur()
            self._durum_cubugu_kur()
            self._yerlesim_kur()
            self._baglantilari_kur()
            self._sayaclari_kur()
            self._spec_uygula()
            self._gecmise_it(ilk=True)
        if acilis_dosyasi:
            self.proje_ac(acilis_dosyasi)
        veri_kayit.kur(self)            # K2: Veri sayfasi (kenar cubugu) + surec ortami
        self.acilis_akisi(dosya_verildi=bool(acilis_dosyasi))   # v3 K1 (+ on kancalar)

    # ------------------------------------------------------------------ kurucular
    def _boyut_kur(self):
        """Boyut EKRANA gore; en kucuk pencere 1280x800'e sigar (kabul olcutu)."""
        ekran = QtWidgets.QApplication.primaryScreen()
        alan = ekran.availableGeometry() if ekran else QtCore.QRect(0, 0, 1280, 800)
        self.resize(min(1600, int(alan.width() * 0.92)),
                    min(1000, int(alan.height() * 0.92)))
        self.setMinimumSize(960, 560)

    def _durum_kur(self):
        self.ayarlar = QtCore.QSettings("openmc_arayuz", "arayuz")
        self.spec = sema.yeni_spec(_("yeni model"))
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
        self._sonraki_ipucu = ""         # dogrulama seridindeki "sonraki adim"
        self._sag_kip = None

    def _sayfalari_kur(self):
        """Sekiz editor, kenar cubugu ogeleri ve yigindaki kaydirma alanlari."""
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
        self.kenar = KenarCubugu(baslik=_("Sayfalar"))
        self.yigin_sekme = QtWidgets.QStackedWidget()
        self._sayfalar = {}
        self._sayfa_editor = {}
        gruplar = dict(kabuk.GEZINME_GRUPLARI)
        editorler = {EDITOR_ANAHTARI[ad]: getattr(self, ad) for ad in EDITOR_ANAHTARI}
        for anahtar in uygunluk.SEKMELER:
            if anahtar in gruplar:
                self.kenar.grup_ekle(kabuk.gezinme_grup_adi(gruplar[anahtar]))
            self.kenar.ekle(anahtar, _(SEKME_ADLARI[anahtar]),
                            kabuk.GEZINME_IKONLARI[anahtar])
            sayfa = self._kaydirma(editorler[anahtar])
            self._sayfalar[anahtar] = sayfa
            self._sayfa_editor[sayfa] = editorler[anahtar]
            self.yigin_sekme.addWidget(sayfa)
        self._konu_sekme = {e.KONU: e for e in self.editorler}

    @staticmethod
    def _kaydirma(widget):
        """Her sayfa bir kaydirma alanina sarilir: yiginin minimum yuksekligi
        en buyuk sayfaya baglanmasin (ayarlar sayfasi pencereyi buyutuyordu)."""
        alan = QtWidgets.QScrollArea()
        alan.setObjectName("sayfa")
        alan.setWidgetResizable(True)
        alan.setFrameShape(QtWidgets.QFrame.NoFrame)
        alan.setWidget(widget)
        return alan

    def _onizleme_kur(self):
        self.onizleme = OnizlemeWidget()
        # matplotlib gezinme cubugu 24 px simgelerle ~51 px yer kapliyordu.
        self.onizleme.arac_cubugu.setIconSize(QtCore.QSize(18, 18))
        self.onizleme_paneli = kabuk.OnizlemePaneli(self.onizleme)
        self.onizleme_paneli.yenile_istendi.connect(self.onizleme._ciz)
        self.onizleme_paneli.daraltildi.connect(self._onizleme_daraltildi)

    def _yerlesim_kur(self):
        """Ust cubuk + (kenar | sayfa | onizleme) + dogrulama seridi."""
        self._editor = self._editor_kur()
        # Baslangic ekrani + editor: ayni pencerede, modal degil.
        self.baslangic = baslangic.BaslangicEkrani()
        self.yigin = QtWidgets.QStackedWidget()
        self.yigin.addWidget(self.baslangic)
        self.yigin.addWidget(self._editor)
        merkez = QtWidgets.QWidget()
        d = QtWidgets.QVBoxLayout(merkez)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(0)
        d.addWidget(self.ust)
        d.addWidget(self.yigin, 1)
        d.addWidget(self.serit)
        self.setCentralWidget(merkez)
        from arayuz.bilesenler.bildirim import ALT_PAYI_OZELLIGI
        self.setProperty(ALT_PAYI_OZELLIGI, kabuk.B["serit"])

    def _editor_kur(self):
        bolucu = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        bolucu.addWidget(self.yigin_sekme)
        bolucu.addWidget(self.onizleme_paneli)
        bolucu.setStretchFactor(0, 5)
        bolucu.setStretchFactor(1, 2)
        bolucu.setChildrenCollapsible(False)
        bolucu.setSizes(self._kayitli_bolucu())
        self._bolucu = bolucu
        editor = QtWidgets.QWidget()
        govde = QtWidgets.QHBoxLayout(editor)
        govde.setContentsMargins(0, 0, 0, 0)
        govde.setSpacing(0)
        govde.addWidget(self.kenar)
        govde.addWidget(bolucu, 1)
        return editor

    def _kayitli_bolucu(self):
        """QSettings'teki [sayfa, onizleme] genislikleri; gecersizse varsayilan."""
        kayitli = self.ayarlar.value(kabuk.BOLUCU_AYARI)
        if not kayitli:
            return list(_VARSAYILAN_BOLUCU)
        try:
            boyut = [int(x) for x in kayitli]
        except (TypeError, ValueError):
            _log.warning("bolucu boyutlari okunamadi: %r", kayitli)
            return list(_VARSAYILAN_BOLUCU)
        if len(boyut) != 2 or min(boyut) <= 0:
            _log.warning("bolucu boyutlari gecersiz, varsayilan kullaniliyor: %r", kayitli)
            return list(_VARSAYILAN_BOLUCU)
        return boyut

    def _bolucu_kaydet(self):
        """Yalniz ekranda yerlesmis tasarim bolucusu kaydedilir: gosterilmemis
        ya da onizlemesiz (kosu/sonuc) sayfadaki boyutlar oranti bozardi."""
        boyut = self._bolucu.sizes() if (self._bolucu.isVisible()
                                          and self.onizleme_paneli.isVisible()) \
            else getattr(self, "_bolucu_boyutlari", None)
        if boyut and len(boyut) == 2 and min(boyut) > 0:
            self.ayarlar.setValue(kabuk.BOLUCU_AYARI, list(boyut))

    def _baglantilari_kur(self):
        for e in self.editorler:
            e.degisti.connect(self._degisti)
        self.kenar.secildi.connect(self._sekme_degisti)
        self.kenar.daraltildi.connect(
            lambda dar: self.ayarlar.setValue(kabuk.KENAR_AYARI, bool(dar)))
        self.onizleme.durum.connect(self._onizleme_durum)
        self.onizleme.olcu_bulundu.connect(lambda *_a: self._ozet_guncelle())
        self.baslangic.bos_istendi.connect(self._bos_basla)
        self.baslangic.ornek_istendi.connect(self.proje_ac)
        self.baslangic.dosya_istendi.connect(self.proje_ac)
        self.baslangic.ac_istendi.connect(self._ac_diyalog)
        self.baslangic.geri_istendi.connect(self._editoru_goster)
        self.s_calistir.kapi_ayarla(self._kosu_izni)
        self.s_analiz.kapi_ayarla(self._kosu_izni)
        self.s_analiz.kinetik.kosu_kaynagi_ayarla(self.s_calistir.son_kosu_dizini)  # Y6
        self.s_tukenme.kapi_ayarla(self._kosu_izni)
        for s in (self.s_calistir, self.s_analiz, self.s_tukenme):
            s.durum.connect(self._sekme_durum_mesaji)
            s.sonuc_degisti.connect(self._isaretleri_guncelle)
        # Is parcacigi ve kosu dizini Calistir'da duzenlenir (konu "calistirma").
        self.s_calistir.degisti.connect(self._degisti)
        self.s_calistir.kosu_durumu_degisti.connect(self._kosu_durumu_degisti)
        self.s_kor.tur_degistir_istendi.connect(self._tur_menusunu_ac)
        # Geometri sayfasi (Dalga G-3): sablon secici, tek adimlik spec islemleri
        # (gelismise gecis, agac islemleri) ve onizleme <-> agac secimi.
        self.s_kor.tur_secildi.connect(self.kor_turunu_degistir)
        self.s_kor.islem_uygulayici = self.spec_islemi_uygula
        self.s_kor.dugum_secildi.connect(self.onizleme.vurgula)
        self.onizleme.dugum_secildi.connect(self.s_kor.dugum_sec)
        self._baslangic_akisini_kur()    # v3 K1: Sifirdan + adim rehberi

    def _sayaclari_kur(self):
        self._dog_sayac = QtCore.QTimer(self)
        self._dog_sayac.setSingleShot(True)
        self._dog_sayac.setInterval(250)
        self._dog_sayac.timeout.connect(lambda: self._dogrula(veri=False))
        self._gecmis_sayac = QtCore.QTimer(self)
        self._gecmis_sayac.setSingleShot(True)
        self._gecmis_sayac.setInterval(700)
        self._gecmis_sayac.timeout.connect(self._gecmise_it)
        self.kenar.daralt(str(self.ayarlar.value(kabuk.KENAR_AYARI, False)).lower()
                          in ("true", "1"))
        acik = str(self.ayarlar.value(kabuk.ONIZLEME_AYARI, True)).lower() not in ("false", "0")
        self.onizleme_paneli.daralt(not acik)

    # ==================================================================
    # bildirimler
    # ==================================================================
    def bildir_mesaj(self, metin, tur="bilgi", sure=None, eylem_metni=None, eylem=None):
        """Gecici kullanici mesaji (durum cubugu yerine bildirim/toast)."""
        return bildir(self, metin, tur, 4000 if sure is None else sure,
                      eylem_metni=eylem_metni, eylem=eylem)

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
        # Baslangic ekraninda dogrulama seridi anlamsiz (bos model "hata" sayardi).
        self.serit.setVisible(False)
        self._model_eylemleri_guncelle()
        self.baslangic.setFocus()

    def _editoru_goster(self):
        self.yigin.setCurrentWidget(self._editor)
        self.serit.setVisible(True)
        self._model_eylemleri_guncelle()
        self._durum_ipucu_guncelle()

    def _model_eylemleri_guncelle(self):
        editorde = not self.baslangic_acik_mi()
        for e in self._model_eylemleri:
            e.setEnabled(editorde)
        self.ust.model_gorunur(editorde)
        self._baslik_guncelle()

    def _bos_basla(self, anahtar):
        """Kart: 'Bos basla' -- o turun sade, calisan sablonu."""
        if not self._kaydetme_sor():
            return False
        try:
            spec = baslangic.bos_sablon(anahtar)
        except (KeyError, OSError, ValueError) as e:
            QtWidgets.QMessageBox.critical(self, _("Şablon kurulamadı"), str(e))
            return False
        self._proje_kur(spec, proje_yolu=None, ornek_kaynagi=None)
        kart = baslangic.kart(anahtar)
        self.sekmeye_git(kart.get("sekme") or "malzemeler", sessiz=True)
        baslik = kart["baslik"]
        self.bildir_mesaj(
            _("Çalışan sade bir model kuruldu ({ad}). Kaydetmek için "
              "'Farklı kaydet' kullanın.").format(ad=_(baslik)), "basari", 8000)
        return True

    # ==================================================================
    # spec yasam dongusu
    # ==================================================================
    def _proje_degisti(self):
        """
        PROJE degisti (yeni / ac / ornek / sablon): onceki projenin SONUCLARI
        silinir. Sekme degisiminde ve geri al/yinele'de CAGRILMAZ.
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
        self._model_var = True
        self._spec_uygula()
        self._gecmise_it(ilk=True)
        self._editoru_goster()

    def _spec_uygula(self):
        """
        Spec bastan yuklendi -- tum sekmeleri tazele.

        BILEREK HEVESLI (v3 H1, olculdu): bellekleme sonrasi SFR'de gizli
        editorlerin hepsi birlikte ~0.9 s (soguk) / ~0.15 s (sicak) tutar.
        Yalniz gorunur sekmeyi doldurmak denendi; gizli sayfalarin durumu
        (Kor tur satiri, Tukenme'nin onceki sonuc okumasi ve kenar cubugundaki
        ✓ isareti, kosu/okuma dizini) gozlenebilir bicimde degisti -- kazanc
        davranis degisikligine degmedi. Tembellik _degisti'dedir (konuya bagli
        sekmeler kirli; testler/test_h1_bellek.py).
        """
        self._hafizayi_esitle()
        self.s_tukenme.proje_ayarla(self.proje_yolu, self.ornek_kaynagi)
        for e in self.editorler:
            e.spec_yukle(self.spec)
        self._kirli_sekmeler.clear()
        if self._model_var:
            # Acilistaki bos spec cizilmez: baslangic ekranindayken "geometri
            # kurulamadi" hatasi uretir ve ilk modelin onizlemesine kadar kalirdi.
            self.onizleme.spec_ayarla(self.spec)
        self.s_calistir.spec_ayarla(self.spec, self.proje_yolu)
        self.s_analiz.spec_ayarla(self.spec, self.proje_yolu)
        self._sekme_gorunurlugu()
        self._dogrula(veri=False)
        self._baslik_guncelle()
        self._ozet_guncelle()

    def _degisti(self, konu="genel"):
        """
        Bir editor sekmesi spec'i degistirdi. Yalnizca konuya BAGIMLI sekmeler
        kirli isaretlenir, onlar da ancak acildiklarinda yenilenir.
        """
        self._kirli = True
        self._hafizayi_esitle()
        gorunur = self._gorunur_editor()
        for k in _KONU_BAGIMLILIK.get(konu, set()):
            e = self._konu_sekme.get(k)
            if e is None:
                continue
            if e is gorunur:
                e.spec_yukle(self.spec)
                self._kirli_sekmeler.discard(e)
            else:
                self._kirli_sekmeler.add(e)
        if konu != "calistirma":
            # Is parcacigi / kosu dizini geometriyi degistirmez.
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
        """Etkin sayfanin ICINDEKI editoru dondurur (kaydirma alanini asar)."""
        return self._sayfa_editor.get(self.yigin_sekme.currentWidget())

    def _sekme_degisti(self, anahtar):
        sayfa = self._sayfalar.get(anahtar)
        if sayfa is not None:
            self.yigin_sekme.setCurrentWidget(sayfa)
        self._sag_panel_guncelle()
        self._sayfaya_yer_ac()
        w = self._sayfa_editor.get(sayfa)
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
    # sayfalar: gorunurluk, isaretler, sag panel
    # ==================================================================
    def _gecerli_sekmeler(self):
        try:
            return list(uygunluk.gecerli_sekmeler(self.spec))
        except (KeyError, TypeError, ValueError):
            _log.warning("gecerli_sekmeler okunamadi; hicbir sayfa gizlenmiyor",
                         exc_info=True)
            return list(uygunluk.SEKMELER)     # bozuk spec: hicbir seyi gizleme

    def _sekme_gorunurlugu(self):
        """Yalnizca modele uyan sayfalar gorunur; etkin sayfa gizlenirse ilk
        gorunur sayfaya gecilir."""
        gorunur = self._gecerli_sekmeler()
        for anahtar in self._sayfalar:
            self.kenar.gorunur_yap(anahtar, anahtar in gorunur)
        simdiki = self.gecerli_sekme()
        if gorunur and simdiki not in gorunur:
            self.sekmeye_git(gorunur[0], sessiz=True)
        self._sag_panel_guncelle()

    def _isaretleri_guncelle(self):
        """Kenar cubugundaki ! • ✓ durum ikonlari ve ipuclari."""
        hata = {}
        for b in self._bulgular:
            if b.seviye == "hata":
                k = yer_sekme_anahtari(b.yer)
                if k:
                    hata[k] = hata.get(k, 0) + 1
        hata = self._adim_hatalarini_ayikla(hata)    # eksik adim "!" degil "•"
        self._isaretler = sekme_isaretleri(
            self.spec, hata,
            kosu_basarili=self.s_calistir.sonuc_var(),
            analiz_sonucu=self.s_analiz.sonuc_var(),
            tukenme_sonucu=self.s_tukenme.sonuc_var())
        for anahtar in self._sayfalar:
            isaret, aciklama = self._isaretler.get(anahtar, ("", ""))
            self.kenar.durum_ayarla(anahtar, kabuk.ISARET_DURUMU.get(isaret))
            kabuk.kenar_ipucu(self.kenar, anahtar, aciklama or _(SEKME_ADLARI[anahtar]))
        self._durum_ipucu_guncelle()

    def _durum_ipucu_guncelle(self):
        if self.baslangic_acik_mi():
            return
        hata = sum(1 for b in self._bulgular if b.seviye == "hata")
        self._serit_guncelle(sonraki_adim(self._isaretler, self._gecerli_sekmeler(),
                                          self.onizleme.cizildi_mi(), hata_toplami=hata))

    def _sag_panel_guncelle(self):
        """Onizleme yalnizca tasarim sayfalarinda; kosu/sonuc sayfalari tum
        genisligi kullanir (Hesap ayarlarinda dogrulama seridi zaten altta)."""
        anahtar = self.gecerli_sekme()
        tasarim = anahtar in TASARIM_SEKMELERI
        if self._sag_kip == "tasarim" and not tasarim and self._bolucu.isVisible():
            self._bolucu_boyutlari = self._bolucu.sizes()
        self.onizleme_paneli.setVisible(tasarim)
        if tasarim and self._sag_kip not in (None, "tasarim"):
            boyut = getattr(self, "_bolucu_boyutlari", None)
            if boyut:
                self._bolucu.setSizes(boyut)
        self._sag_kip = "tasarim" if tasarim else "yok"

    def _sayfaya_yer_ac(self):
        """Sayfa en kucuk genisligine sigmiyorsa onizlemeden (en kucuk
        genisligine kadar) yer alir: kayitli bolucu orani baska pencere
        boyutundan gelebilir ve yatay kaydirma dogururdu."""
        if not self.onizleme_paneli.isVisible() or self.onizleme_paneli.dar_mi():
            return
        sayfa = self.yigin_sekme.currentWidget()
        editor = self._sayfa_editor.get(sayfa)
        boyut = self._bolucu.sizes()
        if editor is None or len(boyut) != 2:
            return
        kaydirma = self.style().pixelMetric(QtWidgets.QStyle.PM_ScrollBarExtent)
        eksik = editor.minimumSizeHint().width() + kaydirma - boyut[0]
        ver = min(eksik, boyut[1] - self.onizleme_paneli.minimumWidth())
        if ver > 0:
            self._bolucu.setSizes([boyut[0] + ver, boyut[1] - ver])

    def resizeEvent(self, olay):                          # noqa: N802 (Qt adi)
        super().resizeEvent(olay)
        # Bolucu yeni boyutunu olay dongusunun sonraki turunda alir.
        QtCore.QTimer.singleShot(0, self, self._sayfaya_yer_ac)

    def _onizleme_daraltildi(self, dar):
        self.ayarlar.setValue(kabuk.ONIZLEME_AYARI, not bool(dar))

    # ==================================================================
    # model basligi ve kor turu
    # ==================================================================
    def _baslik_guncelle(self):
        if self.proje_yolu:
            ad = os.path.basename(self.proje_yolu)
        elif self.ornek_kaynagi:
            ad = _("adsız — örnek: {ornek}").format(
                ornek=os.path.splitext(os.path.basename(self.ornek_kaynagi))[0])
        else:
            ad = _("kaydedilmemiş")
        uygulama_adi = UYGULAMA_ADI
        self.setWindowTitle("%s — %s%s" % (_(uygulama_adi), ad, " *" if self._kirli else ""))
        editorde = not self.baslangic_acik_mi()
        self.e_geri.setEnabled(editorde and self._gecmis_ix > 0)
        self.e_yinele.setEnabled(editorde and 0 <= self._gecmis_ix < len(self._gecmis) - 1)

    def _ozet_guncelle(self):
        """
        Ust cubuktaki model kimligi. BURADA MODEL KURULMAZ -- olcu bilgisi
        onizlemeden gelir (olcu_bulundu sinyali).
        """
        try:
            p = model_ozet_parcalari(self.spec)
        except (KeyError, TypeError, ValueError):
            p = {"ad": self.spec.get("ad", ""), "tur": "?", "boyut": "?", "mod": "?"}
        esc = lambda s: (str(s).replace("&", "&amp;").replace("<", "&lt;")
                         .replace(">", "&gt;"))
        # Baglanti rengi etkin temadan (maket: ikincil metin, alti cizgisiz);
        # tema degisiminde _tema_degistir bu islevi yeniden cagirir.
        stil = "color:%s; text-decoration:none" % tema.renk("metin_ikincil")
        ozet = ("<a href='kor' style='%s'>%s</a> · <a href='mod' style='%s'>%s</a>"
                % (stil, esc(p["boyut"]), stil, esc(p["mod"])))
        self.ust.model_ayarla(
            p["ad"], p["tur"], ozet,
            _("Boyuta tıklayınca Kor sayfasına, hesap türüne tıklayınca "
              "Hesap ayarlarına gider."))
        olcu = self.onizleme.son_olcu
        self.onizleme_paneli.olcu_ayarla("%.2f × %.2f cm" % olcu if olcu else "")

    def _baslik_baglantisi(self, hedef):
        self.sekmeye_git({"mod": "ayarlar", "kor": "kor"}.get(hedef, "kor"))

    def _tur_menusunu_ac(self):
        """Kor sayfasindaki 'Türü değiştir…' baglantisi: ust cubuktaki menu."""
        if self.ust.d_tur.isVisible():
            self.ust.d_tur.showMenu()
        else:
            self._tur_menusunu_doldur()
            self._tur_menusu.exec(QtGui.QCursor.pos())

    def _tur_menusunu_doldur(self):
        self._tur_menusu.clear()
        simdiki = (self.spec.get("kor") or {}).get("tur")
        for tur in uygunluk.kor_turleri(self.spec):
            e = self._tur_menusu.addAction(_(TUR_ADLARI.get(tur, tur)))
            e.setCheckable(True)
            e.setChecked(tur == simdiki)
            e.setData(tur)
            e.triggered.connect(lambda _c=False, t=tur: self.kor_turunu_degistir(t))

    def kor_turunu_degistir(self, tur):
        """Ust cubuktaki 'Turu degistir...' -- geri alinabilir tek adim."""
        if tur not in uygunluk.kor_turleri(self.spec):
            return False
        # Bekleyen duzenleme once kendi adimi olsun.
        self._gecmis_sayac.stop()
        self._gecmise_it()
        eklenen = []
        if not kor_turu_degistir(self.spec, tur, self._tur_hafizasi, eklenen):
            return False
        # Sablon adi Turkce msgid ya da etkin dildeki karsiligi olabilir.
        sablon_adlari = set(_SABLON_ADLARI.values())
        sablon_adlari |= {_(a) for a in sablon_adlari}
        if self.spec.get("ad") in sablon_adlari and tur in _SABLON_ADLARI:
            self.spec["ad"] = _(_SABLON_ADLARI[tur])
        self._kirli = True
        self._spec_uygula()
        self._gecmise_it()
        ek = (_(" Model bu türün gerektirdiği parçayı içermiyordu; şablondan "
                "eklendi: {parca} (Parçalar/Demet sayfasında düzenleyin).")
              .format(parca=", ".join(eklenen))) if eklenen else ""
        self.bildir_mesaj(_("Kor türü: {tur} — geri almak için Ctrl+Z.{ek}").format(
            tur=_(TUR_ADLARI.get(tur, tur)), ek=ek), "basari", 10000)
        return True

    def closeEvent(self, olay):
        if self._kaydetme_sor():
            self._bolucu_kaydet()
            self.onizleme.kapat()      # openmc kutuphanesini serbest birak
            # Onceki tukenme sonucu arka planda okunuyor olabilir (~3 s).
            self.s_tukenme.bekle()
            veri_kayit.kapat(self)     # K2: suren veri indirmesi iptal + bekle
            yoklama_arka.kapat()       # H1b: nokta yoklamasi iscisi
            olay.accept()
        else:
            olay.ignore()
