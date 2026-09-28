# -*- coding: utf-8 -*-
"""
 arayuz/pencere/menuler.py  --  menu, arac cubugu, durum cubugu, yardim

 arayuz/ana_pencere.py'den bolundu (davranis degismedi). Eski yol
 `from arayuz import ana_pencere; ana_pencere.X` aynen calisir.
"""

from PySide6 import QtCore, QtGui, QtWidgets
from arayuz import tema
from cekirdek import ceviri
from cekirdek.ceviri import _
from arayuz.ortak import DurumRozeti
from arayuz.pencere.model_islemleri import UYGULAMA_ADI
from arayuz.pencere.proje import _ICE_AKTAR_NOTU


# ============================================================================
# yardim metni
# ============================================================================

YARDIM_HTML = """
<h2>Yardım ve terimler</h2>

<h3>Nasıl ilerlenir?</h3>
<p>Yalnızca modelinize uyan sekmeler görünür. Sekme başlığındaki işaret
durumu söyler: <b>!</b> düzeltilmesi gereken hata, <b>•</b> eksik adım,
<b>✓</b> tamam. İşaretin üzerine gelince ne yapmanız gerektiği yazar; alttaki
durum çubuğu da sıradaki adımı söyler. Kor türünü üstteki
<b>Türü değiştir…</b> düğmesiyle değiştirebilirsiniz.</p>
<p><b>Önce çiz, sonra çalıştır:</b> geometri önizlemesi başarıyla
çizilmeden ve doğrulama hataları giderilmeden koşu başlamaz; ÇALIŞTIR'a basarsanız
önce neyin eksik olduğu söylenir.</p>

<h3>Temel büyüklükler</h3>
<table cellpadding="5">
<tr><td><b>k-eff</b></td><td>Çoğalma çarpanı. Bir nötron neslinin bir sonraki
nesli ne kadar büyüttüğü. k&gt;1 güç artar, k=1 kritik, k&lt;1 söner.</td></tr>
<tr><td><b>k&infin; (k-inf)</b></td><td>Sonsuz ortam çoğalma çarpanı. Sınırlardan sızıntı
olmadığı varsayılır (yansıtıcı sınır koşulu). Gerçek bir reaktör için üst
sınırdır.</td></tr>
<tr><td><b>Reaktivite (&rho;)</b></td><td>(k-1)/k. Kritiklikten ne kadar uzak
olunduğunun ölçüsü. <b>pcm</b> = 10<sup>-5</sup> birim.</td></tr>
<tr><td><b>Dolar ($)</b></td><td>Reaktivite / &beta;<sub>eff</sub>. 1 $ üstü
geçici rejimde anlık kritiklik demektir.</td></tr>
<tr><td><b>&beta;<sub>eff</sub></b></td><td>Etkin gecikmiş nötron kesri.
Fisyon nötronlarının küçük bir kısmı (~%0.7) gecikmeli çıkar; reaktör denetimi
bu gecikmeye dayanır.</td></tr>
<tr><td><b>&Lambda;</b></td><td>Nötron üretim zamanı. Termal reaktörde ~20 &mu;s,
hızlı metal sistemde ~6 ns.</td></tr>
</table>

<h3>Reaktivite katsayıları (Analiz sekmesi)</h3>
<table cellpadding="5">
<tr><td><b>Doppler katsayısı</b></td><td>Yakıt sıcaklığı arttığında reaktivite
değişimi [pcm/K]. U-238 rezonansları genişler, yakalama artar &rarr;
<b>negatif</b> olmalı. Güvenliğin ilk savunma hattıdır: güç artarsa yakıt ısınır ve
reaktivite kendiliğinden düşer.</td></tr>
<tr><td><b>Moderatör sıcaklık katsayısı</b></td><td>Soğutucu sıcaklığı arttığında
reaktivite değişimi [pcm/K]. Sıcaklık artınca yoğunluk da düşer; ikisi birlikte
hesaplanmalıdır. Termal reaktörde <b>negatif</b> olmalı.</td></tr>
<tr><td><b>Boşluk (void) katsayısı</b></td><td>Soğutucuda boşluk oluşursa
reaktivite değişimi [pcm/%void]. Termal reaktörde negatif olmalı.</td></tr>
<tr><td><b>Bor değeri (worth)</b></td><td>Suda çözünmüş bor başına reaktivite
[pcm/ppm]. Bor nötron emicidir &rarr; negatif. Çok bor, moderatör sıcaklık
katsayısını pozitife doğru iter; bu yüzden sınırlanır.</td></tr>
</table>

<h3>Monte Carlo terimleri</h3>
<table cellpadding="5">
<tr><td><b>Çevrim (batch)</b></td><td>Bir grup nötronun izlendiği tur.</td></tr>
<tr><td><b>Pasif çevrim</b></td><td>Baştaki çevrimler. Kaynak dağılımı henüz
doğru değildir, bu yüzden istatistiğe <b>katılmaz</b>. Tipik 20–50.</td></tr>
<tr><td><b>Aktif çevrim</b></td><td>Pasif çevrimlerden sonraki çevrimler;
k-eff ve tally sonuçları yalnızca bunlardan hesaplanır.</td></tr>
<tr><td><b>Shannon entropisi</b></td><td>Kaynak dağılımının ne kadar yayıldığını
ölçer. Pasif çevrimler boyunca düzleşmelidir; hâlâ kayıyorsa pasif çevrim
sayısı yetersizdir ve k-eff <b>yanlı</b> çıkar.</td></tr>
<tr><td><b>Tally (ölçüm)</b></td><td>Sayaç. Modelin belirli bir yerinde/enerjisinde
hangi reaksiyonların kaç kez olduğunu toplar (akı, fisyon, soğurma…).</td></tr>
<tr><td><b>k-eff ve k&infin;</b></td><td>Çoğaltma katsayısı. Bütün dış sınırlar
yansıtıcı (sızıntısız) ise sonuç <b>k&infin;</b>'dur: sonsuz tekrarlanan ortamın
katsayısı. k&infin; &gt; 1 reaktörün süperkritik olduğunu değil, yakıtın reaktivite
fazlası taşıdığını söyler; sonlu bir korda sızıntı yüzünden k-eff daha küçüktür.</td></tr>
<tr><td><b>Sabit kaynak</b></td><td>Fisyon zinciri yerine dışarıdan verilen bir
kaynağın (ör. D-T füzyon, 14.1 MeV) nötronları izlenir; k-eff tanımsızdır. Kaynak
şiddeti [1/s] girilirse sonuçlar mutlak birimdedir (OpenMC şiddeti kendisi uygular).</td></tr>
<tr><td><b>Akı (flux)</b></td><td>OpenMC'nin akı tally'si hücre hacmi üzerinden
integrallidir: birimi n&middot;cm/s (ya da kaynak nötronu başına n&middot;cm).
Ortalama akı [n/cm²/s] için bölgenin hacmine bölün. Arayüz <b>doz</b> hesaplamaz;
doz için akı–doz dönüşüm katsayıları (ör. ICRP-116) gerekir.</td></tr>
<tr><td><b>F<sub>&Delta;H</sub> ve F<sub>q</sub></b></td><td>Güç tepe faktörleri:
en yüksek çubuk gücü / ortalama (radyal) ve en yüksek yerel güç yoğunluğu / ortalama
(3B). Az parçacıkla F<sub>&Delta;H</sub> istatistik gürültüsüyle <b>yukarı</b>
yanlıdır; güvenilir değer için Normal ya da Hassas hassasiyet kullanın.</td></tr>
<tr><td><b>S(&alpha;,&beta;)</b></td><td>Termal saçılma verisi. Düşük enerjide
nötron serbest bir çekirdekten değil, <b>bağlı</b> bir molekülden saçılır (sudaki
hidrojen gibi). Unutulursa termal reaktörde k yüzde mertebesinde kayar.</td></tr>
</table>

<h3>Geometri terimleri</h3>
<table cellpadding="5">
<tr><td><b>Çubuk (pin, rod)</b></td><td>Eş merkezli bölgelerden oluşan
yakıt, kontrol ya da boş kanal çubuğu: yakıt, yakıt-zarf aralığı, zarf ve
çevresindeki soğutucu.</td></tr>
<tr><td><b>Plaka elemanı</b></td><td>Araştırma reaktörlerindeki (MTR) düz
plakalı yakıt elemanı.</td></tr>
<tr><td><b>Demet (fuel assembly)</b></td><td>Çubukların kare ya da altıgen
ızgarada düzenli dizilimi (OpenMC'de kafes, <i>lattice</i>). Kare (PWR) ya da
altıgen (VVER, SFR).</td></tr>
<tr><td><b>Kor ve kor haritası</b></td><td>Demetlerin yerleşimi. Kor haritası
her konuma hangi demetin geldiğini gösterir.</td></tr>
<tr><td><b>Yansıtıcı kuşak (reflector)</b></td><td>Koru saran, kaçan
nötronları geri gönderen malzeme katmanı.</td></tr>
<tr><td><b>Kontrol tamburu</b></td><td>Yansıtıcı kuşağa gömülü, bir yüzü emici
kaplı dönen silindir. Emici kora döndükçe reaktivite düşer.</td></tr>
<tr><td><b>Eksenel katman</b></td><td>Koru yükseklik boyunca bölen katmanlar
(alt/üst yansıtıcı, örtü, farklı zenginlikte yakıt).</td></tr>
<tr><td><b>Adım (pitch)</b></td><td>Komşu iki hücre merkezi arası mesafe.</td></tr>
<tr><td><b>Universe</b></td><td>OpenMC'de tekrar kullanılabilir geometri
parçası. Her çubuk bir universe'tür; demet onu tekrarlar.</td></tr>
<tr><td><b>Sınır koşulu</b></td><td><b>Vakum (vacuum)</b>: nötron kaçar
(gerçek dış yüzey). <b>Yansıtıcı (reflective)</b>: aynadaki gibi geri yansır
(sonsuz tekrar varsayımı). <b>Beyaz (white)</b>: rastgele yönde geri döner.
<b>Periyodik (periodic)</b>: karşı yüzden geri girer.</td></tr>
</table>

<h3>Tükenme terimleri</h3>
<table cellpadding="5">
<tr><td><b>Tükenme (depletion)</b></td><td>Yakıttaki nüklidlerin zamanla
değişmesi: fisil çekirdekler azalır, fisyon ürünleri ve aktinitler birikir.</td></tr>
<tr><td><b>Yanma (burnup)</b></td><td>Birim ağır metal kütlesi başına üretilen
enerji [MWd/kg].</td></tr>
<tr><td><b>Zincir (chain)</b></td><td>Bozunma ve reaksiyon yollarını tanımlayan
veri dosyası; termal ve hızlı spektrum için ayrı zincirler vardır.</td></tr>
<tr><td><b>Güç yoğunluğu</b></td><td>Ağır metal gramı başına güç [W/gHM].</td></tr>
</table>
"""


# ============================================================================
# bulgu acilir listesi (durum cubugu rozeti)
# ============================================================================

class _BulguAcilir(QtWidgets.QFrame):
    """Rozete tiklayinca acilan bulgu listesi; satir ilgili sekmeye goturur."""

    def __init__(self, parent=None):
        super().__init__(parent, QtCore.Qt.Popup)
        self.setObjectName("bulguAcilir")
        self.liste = QtWidgets.QListWidget()
        self.liste.setAlternatingRowColors(True)
        self.liste.setWordWrap(True)
        self.liste.setResizeMode(QtWidgets.QListView.Adjust)
        self.baslik = QtWidgets.QLabel("Doğrulama bulguları")
        f = self.baslik.font()
        f.setBold(True)
        self.baslik.setFont(f)
        ipucu = QtWidgets.QLabel("Bir satıra tıklayınca ilgili sekmeye gider.")
        ipucu.setObjectName("soluk")
        d = QtWidgets.QVBoxLayout(self)
        d.setContentsMargins(10, 8, 10, 10)
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


class MenulerMixin(object):
    """Menu, arac cubugu, durum cubugu, kisayollar ve yardim diyaloglari."""

    # ==================================================================
    # menu / arac cubugu / durum cubugu
    # ==================================================================
    def _menu_kur(self):
        m_dosya = self.menuBar().addMenu("&Dosya")
        m_dosya.setToolTipsVisible(True)
        self.e_yeni = self._eylem(m_dosya, "Yeni…", self.proje_yeni,
                                  QtGui.QKeySequence.New,
                                  "Başlangıç ekranı: ne modelleyeceğini seç")
        self.e_ac = self._eylem(m_dosya, "Aç…", self._ac_diyalog, QtGui.QKeySequence.Open,
                                "Bir model dosyası (.json) aç")
        self.m_son = m_dosya.addMenu("Son kullanılanlar")
        m_dosya.addSeparator()
        self.e_kaydet = self._eylem(m_dosya, "Kaydet", self.proje_kaydet,
                                    QtGui.QKeySequence.Save)
        self.e_farkli = self._eylem(m_dosya, "Farklı kaydet…", self.proje_farkli_kaydet,
                                    QtGui.QKeySequence.SaveAs)
        m_dosya.addSeparator()
        self.e_ice_aktar = self._eylem(m_dosya, "Malzemeleri içe aktar (OpenMC XML)…",
                                       self.malzeme_ice_aktar, None, _ICE_AKTAR_NOTU)
        self.e_betik = self._eylem(m_dosya, "Python betiği olarak dışa aktar…",
                                   self.betik_disa_aktar, "Ctrl+E",
                                   "Tek başına çalışan bir Python betiği üretir")
        self.e_xml = self._eylem(m_dosya, "OpenMC XML olarak dışa aktar…", self.xml_disa_aktar)
        self.e_png = self._eylem(m_dosya, "Önizlemeyi PNG olarak kaydet…", self.png_kaydet)
        m_dosya.addSeparator()
        self._eylem(m_dosya, "Çıkış", self.close, QtGui.QKeySequence.Quit)

        m_duzen = self.menuBar().addMenu("D&üzen")
        self.e_geri = self._eylem(m_duzen, "Geri al", self.geri_al, QtGui.QKeySequence.Undo)
        self.e_yinele = self._eylem(m_duzen, "Yinele", self.yinele, QtGui.QKeySequence.Redo)

        m_gorunum = self.menuBar().addMenu("&Görünüm")
        self._tema_eylemleri = {}
        grup = QtGui.QActionGroup(self)
        grup.setExclusive(True)
        for anahtar, bilgi in tema.TEMALAR.items():
            e = QtGui.QAction("%s tema" % bilgi["ad"], self)
            e.setCheckable(True)
            e.setChecked(anahtar == tema.etkin())
            e.triggered.connect(lambda _c=False, a=anahtar: self._tema_degistir(a))
            grup.addAction(e)
            m_gorunum.addAction(e)
            self._tema_eylemleri[anahtar] = e
        m_gorunum.addSeparator()
        self._dil_menusu_kur(m_gorunum)
        m_gorunum.addSeparator()
        self._eylem(m_gorunum, "Tam ekran", self._tam_ekran, "F11")

        m_yardim = self.menuBar().addMenu("&Yardım")
        self._eylem(m_yardim, "Yardım ve terimler", self._yardim, "F1")
        self._eylem(m_yardim, "Hakkında", self._hakkinda)

        # Menude olmayan pencere kisayollari (eski Model menusu).
        self.e_dogrula = self._pencere_eylemi(
            "Doğrulamayı yenile (veri kütüphanesi dahil)",
            lambda: self._dogrula(veri=True), "F5")
        self.e_onizle = self._pencere_eylemi(
            "Önizlemeyi yenile", self.onizleme._ciz, "F6")
        self.e_calistir = self._pencere_eylemi(
            "ÇALIŞTIR", self._calistir_menuden, "F9")
        self.e_calistir.setToolTip("Modeli çalıştır (F9) — önce geometri çizilmiş ve "
                                   "doğrulama hatasız olmalı")
        # Baslangic ekraninda anlamsiz eylemler (acik model yok ya da gizli).
        self._model_eylemleri = [self.e_kaydet, self.e_farkli, self.e_ice_aktar,
                                 self.e_betik, self.e_xml, self.e_png,
                                 self.e_dogrula, self.e_onizle, self.e_calistir]
        self._son_menusu_yenile()

    def _pencere_eylemi(self, ad, islev, kisayol):
        e = QtGui.QAction(ad, self)
        e.setShortcut(kisayol)
        e.setShortcutContext(QtCore.Qt.WindowShortcut)
        e.triggered.connect(lambda _c=False: islev())
        self.addAction(e)
        return e

    def _arac_cubugu_kur(self):
        cubuk = QtWidgets.QToolBar("Ana")
        cubuk.setObjectName("anaAracCubugu")
        # Simge yok: TextBesideIcon 24 px simge yuksekligi ayiriyor, pencere
        # minimumunu bosuna buyutuyordu.
        cubuk.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        cubuk.setMovable(False)
        for e in (self.e_yeni, self.e_ac, self.e_kaydet):
            cubuk.addAction(e)
        cubuk.addSeparator()
        for e in (self.e_geri, self.e_yinele):
            cubuk.addAction(e)
        cubuk.addSeparator()
        cubuk.addAction(self.e_calistir)
        calistir = cubuk.widgetForAction(self.e_calistir)
        if calistir is not None:
            calistir.setObjectName("calistirDugmesi")
        self.addToolBar(cubuk)
        self._arac_cubugu = cubuk

    def _durum_cubugu_kur(self):
        # Sonraki adim ipucu: "normal" durum cubugu bileseni -- gecici
        # mesajlar (onizleme, kayit...) onu kisa sure ortup geri birakir.
        self.durum_ipucu = QtWidgets.QLabel("")
        self.durum_ipucu.setObjectName("soluk")
        self.statusBar().addWidget(self.durum_ipucu, 1)
        self.durum_rozeti = DurumRozeti("", "notr", tiklanabilir=True)
        self.durum_rozeti.setToolTip("Doğrulama bulgularını göster")
        self.durum_rozeti.tiklandi.connect(self._bulgu_listesini_ac)
        self.statusBar().addPermanentWidget(self.durum_rozeti)
        self.bulgu_acilir = _BulguAcilir(self)
        self.bulgu_acilir.liste.itemClicked.connect(self._acilirdan_git)
        self.bulgu_acilir.liste.itemActivated.connect(self._acilirdan_git)

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
        self.statusBar().showMessage("Tema: %s" % tema.TEMALAR[ad]["ad"], 4000)

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

    def _kisayol_html(self):
        """Kisayol tablosu -- eylemlerin GERCEK kisayollarindan uretilir."""
        satirlar = [
            (self.e_yeni, "Yeni model (başlangıç ekranı)"), (self.e_ac, "Aç"),
            (self.e_kaydet, "Kaydet"), (self.e_farkli, "Farklı kaydet"),
            (self.e_geri, "Geri al"), (self.e_yinele, "Yinele"),
            (self.e_betik, "Python betiği olarak dışa aktar"),
            (self.e_dogrula, "Doğrulamayı yenile (veri kütüphanesi dahil)"),
            (self.e_onizle, "Önizlemeyi yenile"), (self.e_calistir, "ÇALIŞTIR"),
        ]
        html = ["<h3>Klavye kısayolları</h3><table cellpadding='4'>"]
        for e, aciklama in satirlar:
            tus = e.shortcut().toString(QtGui.QKeySequence.NativeText)
            if tus:
                html.append("<tr><td><b>%s</b></td><td>%s</td></tr>" % (tus, aciklama))
        html.append("<tr><td><b>F1</b></td><td>Bu yardım</td></tr>"
                    "<tr><td><b>F11</b></td><td>Tam ekran</td></tr>"
                    "<tr><td><b>Esc</b></td><td>Başlangıç ekranında: açık modele dön</td></tr>"
                    "</table><p>Demet ve kor haritasında sol tık boyar, sağ tık o hücrenin "
                    "parçasını fırça yapar; altıgen haritada tekerlek yakınlaştırır.</p>")
        return "".join(html)

    def _yardim_diyalogu(self):
        """Yardim diyalogunu KURAR (gostermez) -- testler exec() cagirmadan inceler."""
        d = QtWidgets.QDialog(self)
        d.setWindowTitle("Yardım ve terimler")
        d.resize(760, 640)
        metin = QtWidgets.QTextBrowser()
        metin.setOpenExternalLinks(False)
        metin.setHtml(YARDIM_HTML + self._kisayol_html())
        kutu = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        kutu.button(QtWidgets.QDialogButtonBox.Close).setText("Kapat")
        kutu.rejected.connect(d.reject)
        duzen = QtWidgets.QVBoxLayout(d)
        duzen.addWidget(metin)
        duzen.addWidget(kutu)
        d.metin = metin
        return d

    def _yardim(self):
        """Ogrenciye yonelik yardim: terim sozlugu + kisayollar (F1)."""
        self._yardim_diyalogu().exec()

    def _hakkinda(self):
        QtWidgets.QMessageBox.information(
            self, "Hakkında",
            "%s\n\n"
            "Model tanımı JSON 'spec' olarak tutulur; ondan hem openmc.Model\n"
            "hem de tek başına çalışan Python betiği üretilir.\n\n"
            "Arayüz bir çıkmaz sokak değildir: Dosya > Python betiği olarak\n"
            "dışa aktar (Ctrl+E) ile modeli alıp elle düzenlemeye devam\n"
            "edebilirsiniz." % UYGULAMA_ADI)
