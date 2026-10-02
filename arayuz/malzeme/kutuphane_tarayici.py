# -*- coding: utf-8 -*-
"""
 arayuz/malzeme/kutuphane_tarayici.py  --  KutuphaneTarayici: "Kütüphanem"
 (kullanicinin yerel malzeme kutuphanesi) ve PNNL-15870 ice aktarimi

 Kütüphanem : ara / projeye ekle / duzenle / sil. Dosya bozuksa liste kilitlenir
              ve acik bir uyari gosterilir; "yedekle ve yeni baslat" bozuk dosyanin
              KOPYASINI alir (cekirdek/malzeme_kullanici.bozuk_dosyayi_yedekle).
 PNNL-15870 : veri lisans geregi dagitilmaz; kullanicinin sectigi CSV okunur
              (cekirdek/malzeme_pnnl). Son dosya yolu ayarlarda hatirlanir.
 Projeye eklenen malzeme projeye_ekle sinyaliyle sekmeye gider.
"""

import os

from PySide6 import QtCore, QtWidgets

from cekirdek import malzeme_kullanici as mku
from cekirdek import malzeme_pnnl as mp
from cekirdek import sema
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from arayuz import bilesenler as b
from arayuz.ortak import ipucu
from arayuz.malzeme.turetilmis_panel import TuretilmisPanel
from arayuz.malzeme.yardimcilar import _hata_etiketi, _ozet_etiketi, bilesim_ozeti, yogunluk_metni
from arayuz.tasarim import tokenlar

_log = kaydedici(__name__)
A = tokenlar.ARALIK
_AYAR_PNNL = "malzeme/pnnl_dosyasi"


def _ayarlar():
    return QtCore.QSettings("openmc_arayuz", "arayuz")


class KutuphaneTarayici(QtWidgets.QDialog):

    projeye_ekle = QtCore.Signal(dict)

    def __init__(self, spec=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Malzeme kütüphanem"))
        self.resize(940, 620)
        self._spec = spec if spec is not None else sema.yeni_spec()
        self._kayitlar = ()
        self._pnnl, self._pnnl_gorunen = (), ()
        sekmeler = QtWidgets.QTabWidget()
        sekmeler.addTab(self._kutuphanem_sekmesi(), _("Kütüphanem"))
        sekmeler.addTab(self._pnnl_sekmesi(), "PNNL-15870")
        kutu = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        kutu.button(QtWidgets.QDialogButtonBox.Close).setText(_("Kapat"))
        kutu.rejected.connect(self.reject)
        d = QtWidgets.QVBoxLayout(self)
        d.addWidget(sekmeler, 1)
        d.addWidget(kutu)
        self.yenile()
        self._son_pnnl_dosyasi()

    # ================================================================ Kütüphanem
    def _kutuphanem_sekmesi(self):
        w = QtWidgets.QWidget()
        self.bozuk_kutu = QtWidgets.QFrame()
        self.bozuk_kutu.setObjectName("yuzeyKart")
        self.bozuk_metin = _hata_etiketi()
        self.bozuk_metin.setVisible(True)
        self.d_yedekle = b.tehlikeli_dugme(_("Bozuk dosyanın kopyasını al ve yeni kütüphane başlat"),
                                           "save")
        self.d_yedekle.clicked.connect(self.bozugu_yedekle)
        bk = QtWidgets.QVBoxLayout(self.bozuk_kutu)
        bk.addWidget(self.bozuk_metin)
        bk.addWidget(self.d_yedekle, 0, QtCore.Qt.AlignLeft)
        self.ara = QtWidgets.QLineEdit()
        self.ara.setPlaceholderText(_("Ara…"))
        self.ara.textChanged.connect(self._listeyi_doldur)
        self.liste = QtWidgets.QListWidget()
        self.liste.currentRowChanged.connect(self._secim_degisti)
        self.liste.doubleClicked.connect(self.secileni_aktar)
        self.detay = _ozet_etiketi()
        self.panel = TuretilmisPanel()
        self.d_ekle = b.birincil_dugme(_("Projeye ekle"), "plus")
        self.d_duzenle = b.ikincil_dugme(_("Düzenle…"), "sliders-horizontal")
        self.d_sil = b.tehlikeli_dugme(_("Sil"), "trash")
        self.d_ekle.clicked.connect(self.secileni_aktar)
        self.d_duzenle.clicked.connect(self.duzenle)
        self.d_sil.clicked.connect(self.sil)
        sol = QtWidgets.QVBoxLayout()
        sol.addWidget(ipucu(_("Yalnız bu bilgisayarda saklanır: %s") % mku.varsayilan_yol()))
        self.durum = ipucu("")
        sol.addWidget(self.durum)
        sol.addWidget(self.ara)
        sol.addWidget(self.liste, 1)
        dugmeler = QtWidgets.QHBoxLayout()
        for d in (self.d_ekle, self.d_duzenle, self.d_sil):
            dugmeler.addWidget(d)
        dugmeler.addStretch(1)
        sol.addLayout(dugmeler)
        sag = QtWidgets.QVBoxLayout()
        sag.addWidget(self.detay)
        sag.addWidget(self.panel, 1)
        govde = QtWidgets.QHBoxLayout()
        govde.addLayout(sol, 1)
        govde.addLayout(sag, 1)
        d = QtWidgets.QVBoxLayout(w)
        d.addWidget(self.bozuk_kutu)
        d.addLayout(govde, 1)
        return w

    def yenile(self):
        """Kutuphaneyi diskten okur; bozuksa listeyi kilitler ve nedeni gosterir."""
        try:
            self._kayitlar = mku.yukle()
            sorun = None
        except mku.KutuphaneHatasi as e:
            self._kayitlar, sorun = (), e
            _log.warning("kullanici kutuphanesi okunamadi: %s", e)
        self.bozuk_kutu.setVisible(sorun is not None)
        if sorun is not None:
            self.bozuk_metin.setText(
                _("Kütüphane dosyası okunamadı ve değiştirilmedi:\n%s") % sorun)
        self.d_yedekle.setVisible(isinstance(sorun, mku.KutuphaneBozuk))
        self.liste.setEnabled(sorun is None)
        self.ara.setEnabled(sorun is None)
        self._listeyi_doldur()

    def _gorunen_kayitlar(self):
        q = self.ara.text().strip().casefold()
        return [k for k in self._kayitlar
                if not q or q in k["ad"].casefold() or q in (k.get("aciklama") or "").casefold()]

    def _listeyi_doldur(self, *_a):
        self.liste.blockSignals(True)
        self.liste.clear()
        for k in self._gorunen_kayitlar():
            metin = k["ad"] + (" — " + k["aciklama"] if k.get("aciklama") else "")
            oge = QtWidgets.QListWidgetItem(metin)
            oge.setData(QtCore.Qt.UserRole, k["ad"])
            self.liste.addItem(oge)
        self.liste.blockSignals(False)
        self._secim_degisti()

    def _secili_kayit(self):
        oge = self.liste.currentItem()
        if oge is None:
            return None
        ad = oge.data(QtCore.Qt.UserRole)
        return next((k for k in self._kayitlar if k["ad"] == ad), None)

    def _secim_degisti(self, *_a):
        k = self._secili_kayit()
        for d in (self.d_ekle, self.d_duzenle, self.d_sil):
            d.setEnabled(k is not None)
        if k is None:
            self.detay.setText("")
            self.panel.guncelle(None)
            return
        m = k["malzeme"]
        self.detay.setText(_("Bileşim: {b}\nYoğunluk: {y}\nKaynak: {k}   ·   Güncelleme: {g}").format(
            b=bilesim_ozeti(m), y=yogunluk_metni(m), k=k.get("kaynak") or "—",
            g=k.get("guncelleme") or "—"))
        self.panel.guncelle(m)

    def _yaz(self, kayitlar):
        try:
            mku.kaydet(kayitlar)
        except (mku.KutuphaneHatasi, ValueError) as e:
            _log.warning("kullanici kutuphanesi yazilamadi: %s", e)
            self._hata_goster(str(e))
            return False
        self._kayitlar = tuple(kayitlar)
        self._listeyi_doldur()
        return True

    def secileni_aktar(self, *_a):
        k = self._secili_kayit()
        if k is None:
            return None
        m = mku.projeye_aktar(k, self._spec)
        self.projeye_ekle.emit(m)
        return m

    def duzenle(self):
        from arayuz.malzeme.malzeme_diyalog import MalzemeDiyalog
        k = self._secili_kayit()
        if k is None:
            return False
        digerleri = dict(sema.yeni_spec(), malzemeler=[x["malzeme"] for x in self._kayitlar
                                                         if x["ad"] != k["ad"]])
        d = MalzemeDiyalog(k["malzeme"], digerleri, self)
        if not self._diyalog_calistir(d):
            return False
        m = d.sonuc()
        yeni = dict(k, ad=m["ad"], malzeme=m)
        try:
            kayitlar = mku.guncelle(self._kayitlar, k["ad"], yeni)
        except ValueError as e:
            self._hata_goster(str(e))
            return False
        return self._yaz(kayitlar)

    def sil(self):
        k = self._secili_kayit()
        if k is None or not self._soru(_("Kütüphaneden sil"),
                                       _("'%s' kütüphanenizden silinsin mi?") % k["ad"]):
            return False
        return self._yaz(mku.sil(self._kayitlar, k["ad"]))

    def bozugu_yedekle(self):
        """Bozuk dosyanin kopyasini alir, yeni bos kutuphane yazar; yedek yolu."""
        try:
            yedek = mku.bozuk_dosyayi_yedekle()
            mku.kaydet(())
        except mku.KutuphaneHatasi as e:
            self._hata_goster(str(e))
            return None
        self._bilgi(_("Bozuk dosyanın kopyası alındı:\n%s") % yedek)
        self.yenile()
        return yedek

    # ================================================================ PNNL
    def _pnnl_sekmesi(self):
        w = QtWidgets.QWidget()
        self.pnnl_bilgi = ipucu(_(
            "PNNL-15870 malzeme derlemesi açık bir lisansla yayımlanmadığı için programla "
            "dağıtılmaz. Derlemenin CSV dosyasını (Rev. 1 biçimi, ör. PyNE "
            "materials_compendium.csv) kendiniz indirip seçin; dosya yalnızca okunur."))
        self.d_pnnl_sec = b.ikincil_dugme(_("Dosya seç…"), "folder-open")
        self.d_pnnl_sec.clicked.connect(self._pnnl_dosya_sec)
        self.pnnl_ara = QtWidgets.QLineEdit()
        self.pnnl_ara.setPlaceholderText(_("Ad ya da formül ara…"))
        self.pnnl_ara.textChanged.connect(self._pnnl_doldur)
        self.pnnl_liste = QtWidgets.QListWidget()
        self.pnnl_liste.currentRowChanged.connect(self._pnnl_secim)
        self.pnnl_detay = _ozet_etiketi()
        self.pnnl_panel = TuretilmisPanel()
        self.d_pnnl_ekle = b.birincil_dugme(_("Projeye ekle"), "plus")
        self.d_pnnl_kaydet = b.ikincil_dugme(_("Kütüphaneme kaydet"), "save")
        self.d_pnnl_ekle.clicked.connect(self.pnnl_secileni_aktar)
        self.d_pnnl_kaydet.clicked.connect(self.pnnl_kutuphaneye)
        sol = QtWidgets.QVBoxLayout()
        sol.addWidget(self.pnnl_bilgi)
        sol.addWidget(self.d_pnnl_sec, 0, QtCore.Qt.AlignLeft)
        sol.addWidget(self.pnnl_ara)
        sol.addWidget(self.pnnl_liste, 1)
        dug = QtWidgets.QHBoxLayout()
        dug.addWidget(self.d_pnnl_ekle)
        dug.addWidget(self.d_pnnl_kaydet)
        dug.addStretch(1)
        sol.addLayout(dug)
        sag = QtWidgets.QVBoxLayout()
        sag.addWidget(self.pnnl_detay)
        sag.addWidget(self.pnnl_panel, 1)
        d = QtWidgets.QHBoxLayout(w)
        d.addLayout(sol, 1)
        d.addLayout(sag, 1)
        self._pnnl_secim()
        return w

    def _son_pnnl_dosyasi(self):
        yol = _ayarlar().value(_AYAR_PNNL, "", type=str)
        if yol and os.path.isfile(yol):
            self.pnnl_yukle(yol)

    def _pnnl_dosya_sec(self):
        yol, _f = QtWidgets.QFileDialog.getOpenFileName(
            self, _("PNNL-15870 CSV dosyası"), os.path.expanduser("~"), "CSV (*.csv)")
        if yol:
            self.pnnl_yukle(yol)

    def pnnl_yukle(self, yol):
        try:
            malz, sorunlar = mp.oku(yol)
        except mp.PnnlHatasi as e:            # liste korunur, neden gorunur
            _log.warning("PNNL dosyasi okunamadi: %s", e)
            self.pnnl_bilgi.setText(str(e))
            return False
        self._pnnl = malz
        _ayarlar().setValue(_AYAR_PNNL, yol)
        metin = _("%d malzeme okundu: %s") % (len(malz), yol)
        if sorunlar:
            metin += "\n" + _("%d kayıt atlandı (ayrıntı günlükte).") % len(sorunlar)
        self.pnnl_bilgi.setText(metin)
        self._pnnl_doldur()
        return True

    def _pnnl_doldur(self, *_a):
        self._pnnl_gorunen = mp.ara(self._pnnl, self.pnnl_ara.text())
        self.pnnl_liste.blockSignals(True)
        self.pnnl_liste.clear()
        for m in self._pnnl_gorunen:
            self.pnnl_liste.addItem("%d. %s%s" % (m["no"], m["ad"],
                                                 "  (%s)" % m["formul"] if m["formul"] else ""))
        self.pnnl_liste.blockSignals(False)
        self._pnnl_secim()

    def _pnnl_secili(self):
        i = self.pnnl_liste.currentRow()
        return self._pnnl_gorunen[i] if 0 <= i < len(self._pnnl_gorunen) else None

    def _pnnl_malzeme(self, k):
        from arayuz.malzeme.yardimcilar import _benzersiz_ad
        return mp.malzemeye_cevir(k, ad=_benzersiz_ad(self._spec, "pnnl_%d" % k["no"]))

    def _pnnl_secim(self, *_a):
        k = self._pnnl_secili()
        self.d_pnnl_ekle.setEnabled(k is not None)
        self.d_pnnl_kaydet.setEnabled(k is not None)
        if k is None:
            self.pnnl_detay.setText("")
            self.pnnl_panel.guncelle(None)
            return
        self.pnnl_detay.setText(_("PNNL-15870 #{no}: {ad}\nYoğunluk: {y:.6g} g/cm³\nKaynak: {k}")
                                .format(no=k["no"], ad=k["ad"], y=k["yogunluk"],
                                        k=k["kaynak"] or "—"))
        self.pnnl_panel.guncelle(self._pnnl_malzeme(k))

    def pnnl_secileni_aktar(self, *_a):
        k = self._pnnl_secili()
        if k is None:
            return None
        m = self._pnnl_malzeme(k)
        self.projeye_ekle.emit(m)
        return m

    def pnnl_kutuphaneye(self):
        k = self._pnnl_secili()
        if k is None:
            return False
        ad = mku.benzersiz_kayit_adi(self._kayitlar, "pnnl_%d" % k["no"])
        kayit = mku.kayit_olustur(mp.malzemeye_cevir(k, ad=ad), aciklama=k["ad"],
                                  kaynak="PNNL-15870 #%d" % k["no"])
        return self._yaz(mku.ekle(self._kayitlar, kayit))

    # ================================================================ kancalar
    def _diyalog_calistir(self, d):
        return d.exec() == QtWidgets.QDialog.Accepted

    def _soru(self, baslik_, metin):
        c = QtWidgets.QMessageBox.question(self, baslik_, metin)
        return c == QtWidgets.QMessageBox.Yes

    def _hata_goster(self, metin):
        QtWidgets.QMessageBox.warning(self, _("Malzeme kütüphanem"), metin)

    def _bilgi(self, metin):
        """Kalici olmayan bilgi: sekmedeki durum satiri (modal degil)."""
        _log.info("%s", metin)
        self.durum.setText(metin)
