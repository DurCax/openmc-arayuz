# -*- coding: utf-8 -*-
"""
 arayuz/pencere/menuler.py  --  menu, arac cubugu, durum cubugu, yardim

 arayuz/ana_pencere.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import ana_pencere; ana_pencere.X` aynen calisir.

 Kilavuz baglantilari (Dalga 3 / Ajan 12): Yardim > Kullanim kilavuzu (F1,
 baglamsal: etkin sayfanin bolumu), bulgu satirinda sag tik "Kılavuzda aç".
 Esleme arayuz/yardim_baglanti.py'dedir.
"""

from PySide6 import QtCore, QtGui, QtWidgets
from arayuz import tema, yardim_baglanti
from cekirdek import ceviri
from cekirdek.ceviri import _
from arayuz.bilesenler import KomutPaleti
from arayuz.pencere import kabuk, sekme_arayuzu
from arayuz.pencere.model_islemleri import UYGULAMA_ADI
from arayuz.pencere.proje import _ICE_AKTAR_NOTU
from arayuz.pencere.yardim_metni import YARDIM_HTML, yardim_html  # noqa: F401 (eski ad)

ONIZLEME_KISAYOLU = "F7"            # F6 onizlemeyi yeniler; gizle/goster yaninda (K5)


# ============================================================================
# bulgu acilir listesi (durum cubugu rozeti)
# ============================================================================


def _tema_adi(anahtar):
    """Temanin gorunen adi, etkin dilde ("Açık")."""
    ad = tema.TEMALAR[anahtar]["ad"]
    return _(ad)


def tema_etiketi(anahtar):
    """Gorunum menusundeki tema eyleminin metni, etkin dilde ("Açık tema")."""
    return _("{ad} tema").format(ad=_tema_adi(anahtar))


class _BulguAcilir(QtWidgets.QFrame):
    """Rozete tiklayinca acilan bulgu listesi; satir ilgili sayfaya goturur,
    sag tik "Kılavuzda aç" bulgunun kilavuz bolumunu acar."""

    def __init__(self, parent=None):
        super().__init__(parent, QtCore.Qt.Popup)
        self.setObjectName("bulguAcilir")
        self.liste = QtWidgets.QListWidget()
        self.liste.setAlternatingRowColors(True)
        self.liste.setWordWrap(True)
        self.liste.setResizeMode(QtWidgets.QListView.Adjust)
        self.liste.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.liste.customContextMenuRequested.connect(self._sag_tik)
        self.baslik = QtWidgets.QLabel(_("Doğrulama bulguları"))
        f = self.baslik.font()
        f.setBold(True)
        self.baslik.setFont(f)
        ipucu = QtWidgets.QLabel(_("Bir satıra tıklayınca ilgili sayfaya gider; "
                                   "sağ tık: kılavuzda aç."))
        ipucu.setObjectName("soluk")
        d = QtWidgets.QVBoxLayout(self)
        a = kabuk.A
        d.setContentsMargins(a["m"], a["s"], a["m"], a["m"])
        d.addWidget(self.baslik)
        d.addWidget(ipucu)
        d.addWidget(self.liste, 1)

    def goster(self, capa):
        """capa widget'inin ustunde, sag kenara hizali acar."""
        n = max(1, self.liste.count())
        self.resize(620, min(380, 90 + n * 30))
        sag_ust = capa.mapToGlobal(QtCore.QPoint(capa.width(), 0))
        self.move(sag_ust.x() - self.width(), sag_ust.y() - self.height() - 4)
        self.show()
        self.liste.setFocus()

    def kilavuz_eylemi(self, oge, sahip=None):
        """Bulgu satiri icin "Kılavuzda aç" eylemi (yer -> kilavuz bolumu)."""
        bolum = yardim_baglanti.bulgu_bolumu(oge.data(QtCore.Qt.UserRole))
        e = QtGui.QAction(_("Kılavuzda aç"), sahip or self)
        e.setData(bolum)
        e.triggered.connect(lambda _c=False: yardim_baglanti.ac(bolum, self.parentWidget()))
        return e

    def _sag_tik(self, konum):
        oge = self.liste.itemAt(konum)
        if oge is None or oge.data(QtCore.Qt.UserRole) is None:
            return
        menu = QtWidgets.QMenu(self)
        menu.addAction(self.kilavuz_eylemi(oge, menu))
        menu.exec(self.liste.viewport().mapToGlobal(konum))


class MenulerMixin(object):
    """Menu, arac cubugu, durum cubugu, kisayollar ve yardim diyaloglari."""

    # ==================================================================
    # menu / arac cubugu / durum cubugu
    # ==================================================================
    def _menu_kur(self):
        self._dosya_menusu_kur(self.menuBar().addMenu(_("&Dosya")))
        m_duzen = self.menuBar().addMenu(_("D&üzen"))
        self.e_geri = self._eylem(m_duzen, _("Geri al"), self.geri_al, QtGui.QKeySequence.Undo)
        self.e_yinele = self._eylem(m_duzen, _("Yinele"), self.yinele, QtGui.QKeySequence.Redo)
        self._gorunum_menusu_kur(self.menuBar().addMenu(_("&Görünüm")))
        m_yardim = self.menuBar().addMenu(_("&Yardım"))
        m_yardim.setToolTipsVisible(True)
        self.e_kilavuz = self._eylem(m_yardim, _("Kullanım kılavuzu"), self.kilavuzu_ac, "F1",
                                     _("Kullanım kılavuzunu etkin sayfanın bölümünde açar"))
        self.e_yardim = self._eylem(m_yardim, _("Yardım ve terimler"), self._yardim, "Shift+F1")
        self._eylem(m_yardim, _("Hakkında"), self._hakkinda)

        # Menude olmayan pencere kisayollari (eski Model menusu).
        self.e_dogrula = self._pencere_eylemi(
            _("Doğrulamayı yenile (veri kütüphanesi dahil)"),
            lambda: self._dogrula(veri=True), "F5")
        self.e_onizle = self._pencere_eylemi(
            _("Önizlemeyi yenile"), self.onizleme._ciz, "F6")
        self.e_calistir = self._pencere_eylemi(
            _("ÇALIŞTIR"), self._calistir_menuden, "F9")
        self.e_calistir.setToolTip(_("Modeli çalıştır (F9) — önce geometri çizilmiş ve "
                                     "doğrulama hatasız olmalı"))
        # Baslangic ekraninda anlamsiz eylemler (acik model yok ya da gizli).
        self._model_eylemleri = [self.e_kaydet, self.e_farkli, self.e_ice_aktar,
                                 self.e_betik, self.e_xml, self.e_png, self.e_rapor,
                                 self.e_dogrula, self.e_onizle, self.e_calistir]
        self._son_menusu_yenile()

    def _dosya_menusu_kur(self, m_dosya):
        m_dosya.setToolTipsVisible(True)
        self.e_yeni = self._eylem(m_dosya, _("Yeni…"), self.proje_yeni,
                                  QtGui.QKeySequence.New,
                                  _("Başlangıç ekranı: ne modelleyeceğini seç"))
        self.e_ac = self._eylem(m_dosya, _("Aç…"), self._ac_diyalog, QtGui.QKeySequence.Open,
                                _("Bir model dosyası (.json) aç"))
        self.m_son = m_dosya.addMenu(_("Son kullanılanlar"))
        m_dosya.addSeparator()
        self.e_kaydet = self._eylem(m_dosya, _("Kaydet"), self.proje_kaydet,
                                    QtGui.QKeySequence.Save)
        self.e_farkli = self._eylem(m_dosya, _("Farklı kaydet…"), self.proje_farkli_kaydet,
                                    QtGui.QKeySequence.SaveAs)
        m_dosya.addSeparator()
        self.e_ice_aktar = self._eylem(m_dosya, _("Malzemeleri içe aktar (OpenMC XML)…"),
                                       self.malzeme_ice_aktar, None, _(_ICE_AKTAR_NOTU))
        self.e_betik = self._eylem(m_dosya, _("Python betiği olarak dışa aktar…"),
                                   self.betik_disa_aktar, "Ctrl+E",
                                   _("Tek başına çalışan bir Python betiği üretir"))
        self.e_xml = self._eylem(m_dosya, _("OpenMC XML olarak dışa aktar…"),
                                 self.xml_disa_aktar)
        self.e_png = self._eylem(m_dosya, _("Önizlemeyi PNG olarak kaydet…"), self.png_kaydet)
        self.e_rapor = self._eylem(m_dosya, _("Rapor oluştur…"), self.rapor_olustur, "Ctrl+R",
                                   _("Model ve son koşu için HTML ya da PDF rapor yazar"))
        m_dosya.addSeparator()
        self._eylem(m_dosya, _("Çıkış"), self.close, QtGui.QKeySequence.Quit)

    def _gorunum_menusu_kur(self, m_gorunum):
        self._tema_eylemleri = {}
        grup = QtGui.QActionGroup(self)
        grup.setExclusive(True)
        for anahtar in tema.TEMALAR:
            e = QtGui.QAction(tema_etiketi(anahtar), self)
            e.setCheckable(True)
            e.setChecked(anahtar == tema.etkin())
            e.triggered.connect(lambda _c=False, a=anahtar: self._tema_degistir(a))
            grup.addAction(e)
            m_gorunum.addAction(e)
            self._tema_eylemleri[anahtar] = e
        m_gorunum.addSeparator()
        self._dil_menusu_kur(m_gorunum)
        m_gorunum.addSeparator()
        self._onizleme_eylemi_kur(m_gorunum)
        self._eylem(m_gorunum, _("Tam ekran"), self._tam_ekran, "F11")

    def _onizleme_eylemi_kur(self, m_gorunum):
        """Gorunum > Onizlemeyi goster (F7, v3 K5): paneli daraltir/acar. Durum
        panelin daraltildi sinyaliyle QSettings'e yazilir (kabuk.ONIZLEME_AYARI);
        gizliyken cizim yapilmaz, yalniz tam model denetlenir (Calistir kapisi).
        Onizleme kapsami (sayfa + secim -> alt model) burada pencereye baglanir."""
        from arayuz.onizleme_kapsam import PencereKapsami
        self.onizleme_kapsami = PencereKapsami(self)
        e = QtGui.QAction(_("Önizlemeyi göster"), self)
        e.setCheckable(True)
        e.setChecked(not self.onizleme_paneli.dar_mi())
        e.setShortcut(ONIZLEME_KISAYOLU)
        e.setToolTip(_("Önizleme panelini gizler ya da gösterir; gizliyken çizim yapılmaz "
                       "(Çalıştır kapısı için model yine denetlenir)"))
        e.triggered.connect(lambda acik: self.onizleme_paneli.daralt(not acik))
        self.onizleme_paneli.daraltildi.connect(lambda dar: e.setChecked(not dar))
        m_gorunum.addAction(e)
        self.e_onizleme_goster = e

    def _pencere_eylemi(self, ad, islev, kisayol):
        e = QtGui.QAction(ad, self)
        e.setShortcut(kisayol)
        e.setShortcutContext(QtCore.Qt.WindowShortcut)
        e.triggered.connect(lambda _c=False: islev())
        self.addAction(e)
        return e

    def _arac_cubugu_kur(self):
        """Ust cubuk (maket kabuk_*.png) + Ctrl+K komut paleti."""
        self.ust = kabuk.UstCubuk({"yeni": self.e_yeni, "ac": self.e_ac,
                                   "kaydet": self.e_kaydet, "geri": self.e_geri,
                                   "yinele": self.e_yinele}, self)
        self._tur_menusu = QtWidgets.QMenu(self)
        self._tur_menusu.aboutToShow.connect(self._tur_menusunu_doldur)
        self.ust.d_tur.setMenu(self._tur_menusu)
        self.palet = KomutPaleti(self, self.komut_eylemleri)
        self.ust.komut_istendi.connect(self.palet.ac)
        # Birincil dugme F9 eylemini tetikler (menu/palet/kisayol ile ayni yol).
        self.ust.kosu_istendi.connect(self.e_calistir.trigger)
        self.ust.durdur_istendi.connect(lambda: self.s_calistir.durdur())
        self.ust.model_ozet.linkActivated.connect(self._baslik_baglantisi)
        # Eski ad: testler ve araclar arac cubugunu bu adla ariyordu.
        self._arac_cubugu = self.ust

    def komut_eylemleri(self):
        """Ctrl+K paletinin listesi: menu eylemleri + etkin sayfanin komutlari."""
        eylemler = []
        for menu in self.menuBar().actions():
            alt = menu.menu()
            if alt is None:
                continue
            eylemler += [e for e in alt.actions() if not e.isSeparator() and e.menu() is None]
        eylemler += [self.e_dogrula, self.e_onizle, self.e_calistir]
        sekme = self.sekme_widget(self.gecerli_sekme())
        if sekme is not None:
            eylemler += list(sekme_arayuzu.komutlar(sekme))
        return eylemler

    def _durum_cubugu_kur(self):
        """Alt dogrulama seridi + bulgu acilir listesi."""
        self.serit = kabuk.DogrulamaSeridi(self)
        self.serit.setFixedHeight(kabuk.B["serit"])
        self.serit.veri_denetle.connect(lambda: self._dogrula(veri=True))
        self.serit.bulguya_git.connect(self._ilk_bulguya_git)
        self.serit.ozet_istendi.connect(self._bulgu_listesini_ac)
        self.bulgu_acilir = _BulguAcilir(self)
        self.bulgu_acilir.liste.itemClicked.connect(self._acilirdan_git)
        self.bulgu_acilir.liste.itemActivated.connect(self._acilirdan_git)
        # Dogrulama listesi artik yalnizca acilir pencerededir.
        self.dogrulama = self.bulgu_acilir.liste

    def _eylem(self, menu, ad, islev, kisayol=None, ipucu=None):
        e = QtGui.QAction(ad, self)
        e.triggered.connect(lambda _c=False: islev())
        if kisayol:
            e.setShortcut(kisayol)
        if ipucu:
            e.setToolTip(ipucu)
            e.setStatusTip(ipucu)
        menu.addAction(e)
        return e

    def _tema_degistir(self, ad):
        """Temayi degistirir ve renge bagli panelleri tazeler."""
        tema.uygula(QtWidgets.QApplication.instance(), ad)
        for anahtar, e in self._tema_eylemleri.items():
            e.setChecked(anahtar == ad)
        self._dogrula(veri=False)          # seviye renkleri, rozetler
        self._ozet_guncelle()              # baslik baglanti rengi
        self.onizleme._ciz()               # grafik paleti
        self.bildir_mesaj(_("Tema: {ad}").format(ad=_tema_adi(ad)), "bilgi")

    def _dil_menusu_kur(self, ust_menu):
        """Gorunum > Dil: secim QSettings'e yazilir, yeniden baslatinca gecerli."""
        menu = ust_menu.addMenu(ceviri.dil_menusu_basligi())
        grup = QtGui.QActionGroup(menu)
        grup.setExclusive(True)
        for kod, ad in ceviri.dil_secenekleri():
            e = menu.addAction(ad)
            e.setCheckable(True)
            e.setData(kod)
            e.setChecked(kod == ceviri.etkin_dil())
            grup.addAction(e)
        grup.triggered.connect(self._dil_secildi)
        self._dil_grubu = grup

    def _dil_secildi(self, eylem):
        self.ayarlar.setValue("gorunum/dil", eylem.data())
        QtWidgets.QMessageBox.information(
            self, _("Dil"), _("Dil değişikliği uygulama yeniden başlatılınca geçerli olur."))

    def _tam_ekran(self):
        """F11 -- tam ekran ac/kapa."""
        if self.isFullScreen():
            self.setWindowState(self.windowState() & ~QtCore.Qt.WindowFullScreen)
        else:
            self.setWindowState(self.windowState() | QtCore.Qt.WindowFullScreen)

    # ==================================================================
    # kullanim kilavuzu (arayuz/yardim sozlesmesi)
    # ==================================================================
    def kilavuz_bolumu(self):
        """Etkin ekranin kilavuz bolumu (F1): baslangic ya da etkin sayfa."""
        if self.baslangic_acik_mi():
            return yardim_baglanti.sayfa_bolumu("baslangic")
        anahtar = self.gecerli_sekme()
        gelismis = anahtar == "kor" and self.s_kor.agac_modunda_mi()
        return yardim_baglanti.sayfa_bolumu(anahtar, gelismis=gelismis)

    def kilavuzu_ac(self, bolum=None):
        """Kilavuzu verilen (yoksa etkin sayfanin) bolumunde acar."""
        return yardim_baglanti.ac(bolum or self.kilavuz_bolumu(), self)

    # ==================================================================
    # yardim diyalogu
    # ==================================================================
    def _kisayol_html(self):
        """Kisayol tablosu -- eylemlerin GERCEK kisayollarindan uretilir."""
        satirlar = [
            (self.e_yeni, _("Yeni model (başlangıç ekranı)")), (self.e_ac, _("Aç")),
            (self.e_kaydet, _("Kaydet")), (self.e_farkli, _("Farklı kaydet")),
            (self.e_geri, _("Geri al")), (self.e_yinele, _("Yinele")),
            (self.e_betik, _("Python betiği olarak dışa aktar")),
            (self.e_dogrula, _("Doğrulamayı yenile (veri kütüphanesi dahil)")),
            (self.e_onizle, _("Önizlemeyi yenile")),
            (self.e_onizleme_goster, _("Önizlemeyi gizle / göster")),
            (self.e_calistir, _("ÇALIŞTIR")),
            (self.e_kilavuz, _("Kullanım kılavuzu (etkin sayfanın bölümü)")),
            (self.e_yardim, _("Bu yardım")),
        ]
        html = ["<h3>%s</h3><table cellpadding='4'>" % _("Klavye kısayolları")]
        for e, aciklama in satirlar:
            tus = e.shortcut().toString(QtGui.QKeySequence.NativeText)
            if tus:
                html.append("<tr><td><b>%s</b></td><td>%s</td></tr>" % (tus, aciklama))
        for tus, aciklama in (("F11", _("Tam ekran")),
                              ("Esc", _("Başlangıç ekranında: açık modele dön"))):
            html.append("<tr><td><b>%s</b></td><td>%s</td></tr>" % (tus, aciklama))
        html.append("</table><p>%s</p>" % _(
            "Demet ve kor haritasında sol tık boyar, sağ tık o hücrenin parçasını fırça "
            "yapar; altıgen haritada tekerlek yakınlaştırır."))
        return "".join(html)

    def _yardim_diyalogu(self):
        """Yardim diyalogunu KURAR (gostermez) -- testler exec() cagirmadan inceler."""
        d = QtWidgets.QDialog(self)
        d.setWindowTitle(_("Yardım ve terimler"))
        d.resize(760, 640)
        metin = QtWidgets.QTextBrowser()
        metin.setOpenExternalLinks(False)
        metin.setHtml(yardim_html() + self._kisayol_html())
        kutu = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        kutu.button(QtWidgets.QDialogButtonBox.Close).setText(_("Kapat"))
        kutu.rejected.connect(d.reject)
        duzen = QtWidgets.QVBoxLayout(d)
        duzen.addWidget(metin)
        duzen.addWidget(kutu)
        d.metin = metin
        return d

    def _yardim(self):
        """Ogrenciye yonelik yardim: terim sozlugu + kisayollar (Shift+F1)."""
        self._yardim_diyalogu().exec()

    def _hakkinda(self):
        QtWidgets.QMessageBox.information(
            self, _("Hakkında"),
            _("{ad}\n\n"
              "Model tanımı JSON 'spec' olarak tutulur; ondan hem openmc.Model\n"
              "hem de tek başına çalışan Python betiği üretilir.\n\n"
              "Arayüz bir çıkmaz sokak değildir: Dosya > Python betiği olarak\n"
              "dışa aktar (Ctrl+E) ile modeli alıp elle düzenlemeye devam\n"
              "edebilirsiniz.").format(ad=_(UYGULAMA_ADI)))
