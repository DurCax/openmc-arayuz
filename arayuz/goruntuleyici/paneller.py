# -*- coding: utf-8 -*-
"""
 paneller.py  --  Goruntuleyici denetim panelleri (Qt; mantik yok, yalniz secim)

   KesitPaneli    eksen, konum, genislik, cozunurluk, renk kipi, cakisma denetimi
   TallyPaneli    Y1 mesh tally bindirmesi: tally/skor/grup, normalizasyon,
                  saydamlik, sigma maskesi
   KaynakPaneli   kaynak noktalari: model kaynagi ya da statepoint bankasi
   UcBoyutPaneli  3B golgeli gorunum: renk, kamera acilari, gizlenen malzemeler
 Her panel degisince `degisti` yayar; pencere istegi gecikmeli gonderir.
"""

from PySide6 import QtCore, QtWidgets

from cekirdek import mesh_tally as mt
from cekirdek.ceviri import _, N_
from arayuz.goruntuleyici import kamera as km, renk_kipi as rk
from arayuz.goruntuleyici import gorunum as gr
from arayuz.ortak import ipucu, sayi

COZUNURLUK = ((N_("Düşük (400)"), 400), (N_("Normal (800)"), 800),
              (N_("Yüksek (1400)"), 1400))
NORMALIZASYONLAR = ("kaynak", "hacim", "bagil")       # mutlak: Calistir > Ag haritasi
_YUZDE = 100.0
_SAYDAMLIK = 60                   # % (varsayilan bindirme opakligi)
_KONUM_SINIRI = 1.0e6             # cm (gorunum.EN_BUYUK_GENISLIK ile ayni olcek)
_KAYNAK_VARSAYILAN = 2000
_KAYNAK_EN_AZ = 10
KAYNAK_AYAR, KAYNAK_STATEPOINT = "ayar", "statepoint"


def _form(kutu):
    f = QtWidgets.QFormLayout(kutu)
    f.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
    return f


def _kutu_doldur(kutu, ogeler) -> None:
    kutu.blockSignals(True)
    eski = kutu.currentData()
    kutu.clear()
    for etiket, veri in ogeler:
        kutu.addItem(etiket, veri)
    i = kutu.findData(eski)
    kutu.setCurrentIndex(i if i >= 0 else 0)
    kutu.blockSignals(False)


class KesitPaneli(QtWidgets.QGroupBox):
    degisti = QtCore.Signal()          # kesit penceresi degisti (isciye gidilir)
    boya = QtCore.Signal()             # yalniz renk kipi / cakisma (eldeki dilim)
    sifirla = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(_("Kesit"), parent)
        self.eksen = QtWidgets.QComboBox()
        for e in gr.EKSENLER:
            self.eksen.addItem(e, e)
        self.konum = sayi(0.0, 3, -_KONUM_SINIRI, _KONUM_SINIRI, 1.0, "cm")
        self.genislik = sayi(1.0, 3, gr.EN_KUCUK_GENISLIK, gr.EN_BUYUK_GENISLIK, 1.0, "cm")
        self.cozunurluk = QtWidgets.QComboBox()
        for etiket, deger in COZUNURLUK:
            self.cozunurluk.addItem(_(etiket), deger)
        self.cozunurluk.setCurrentIndex(1)
        self.renk = QtWidgets.QComboBox()
        for veri, etiket in rk.KIPLER:
            self.renk.addItem(_(etiket), veri)
        self.cakisma = QtWidgets.QCheckBox(_("Çakışma denetimi"))
        self.tam = QtWidgets.QPushButton(_("Tüm modeli göster"))
        f = _form(self)
        f.addRow(_("Kesit ekseni:"), self.eksen)
        f.addRow(_("Kesit konumu:"), self.konum)
        f.addRow(_("Görünür genişlik:"), self.genislik)
        f.addRow(_("Çözünürlük:"), self.cozunurluk)
        f.addRow(_("Renklendirme:"), self.renk)
        f.addRow(self.cakisma)
        f.addRow(self.tam)
        f.addRow(ipucu(_("Tekerlek: yakınlaştır · sol tuşla sürükle: kaydır. Çakışma kipi "
                         "denetimi kendiliğinden açar.")))
        for w in (self.eksen, self.cozunurluk):
            w.currentIndexChanged.connect(lambda *_a: self.degisti.emit())
        for w in (self.konum, self.genislik):
            w.editingFinished.connect(self.degisti.emit)
        self.renk.currentIndexChanged.connect(lambda *_a: self.boya.emit())
        self.cakisma.toggled.connect(lambda *_a: self.boya.emit())
        self.tam.clicked.connect(self.sifirla.emit)

    def piksel(self) -> int:
        return int(self.cozunurluk.currentData())

    def cakisma_istenir(self) -> bool:
        return self.cakisma.isChecked() or self.renk.currentData() == rk.CAKISMA_KIPI

    def gorunumu_yaz(self, g: gr.Gorunum) -> None:
        """Gorunumu kutulara yazar (sinyal yaymadan)."""
        for w, deger in ((self.konum, g.konum), (self.genislik, g.genislik[0])):
            w.blockSignals(True)
            w.setValue(float(deger))
            w.blockSignals(False)
        self.eksen.blockSignals(True)
        self.eksen.setCurrentIndex(self.eksen.findData(g.eksen))
        self.eksen.blockSignals(False)


class TallyPaneli(QtWidgets.QGroupBox):
    degisti = QtCore.Signal()
    statepoint_sec = QtCore.Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(_("Ağ (mesh) tally bindirmesi"), parent)
        self.setCheckable(True)
        self.setChecked(False)
        self.sonuclar = []
        self.yol = QtWidgets.QLabel(_("(statepoint yok)"))
        self.yol.setWordWrap(True)
        self.sec = QtWidgets.QPushButton(_("Statepoint seç…"))
        self.tally, self.skor, self.grup = (QtWidgets.QComboBox() for _i in range(3))
        self.normalizasyon = QtWidgets.QComboBox()
        for k in NORMALIZASYONLAR:
            self.normalizasyon.addItem(_(mt.NORMALIZASYON_ADLARI[k]), k)
        self.normalizasyon.setCurrentIndex(1)
        self.saydamlik = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.saydamlik.setRange(0, 100)
        self.saydamlik.setValue(_SAYDAMLIK)
        self.sigma = QtWidgets.QCheckBox(_("Güvenilmez hücreleri gizle (σ maskesi)"))
        self.sigma.setChecked(True)
        self.esik = sayi(mt.BAGIL_HATA_ESIGI * _YUZDE, 1, 0.1, 100.0, 1.0, "%")
        self.esik.setToolTip(_(mt.BAGIL_HATA_KAYNAGI))
        self._yerlestir()

    def _yerlestir(self):
        f = _form(self)
        f.addRow(self.yol)
        f.addRow(self.sec)
        f.addRow(_("Tally:"), self.tally)
        f.addRow(_("Skor:"), self.skor)
        f.addRow(_("Enerji grubu:"), self.grup)
        f.addRow(_("Normalizasyon:"), self.normalizasyon)
        f.addRow(_("Opaklık:"), self.saydamlik)
        f.addRow(self.sigma)
        f.addRow(_("Bağıl hata eşiği:"), self.esik)
        self.sec.clicked.connect(self.statepoint_sec.emit)
        self.tally.currentIndexChanged.connect(self._tally_secildi)
        for w in (self.skor, self.grup, self.normalizasyon):
            w.currentIndexChanged.connect(lambda *_a: self.degisti.emit())
        self.saydamlik.valueChanged.connect(lambda *_a: self.degisti.emit())
        self.sigma.toggled.connect(lambda *_a: self.degisti.emit())
        self.esik.editingFinished.connect(self.degisti.emit)
        self.toggled.connect(lambda *_a: self.degisti.emit())

    def sonuclari_ayarla(self, yol, sonuclar) -> None:
        self.sonuclar = list(sonuclar)
        self.yol.setText(yol or _("(statepoint yok)"))
        _kutu_doldur(self.tally, [(s.ad, i) for i, s in enumerate(self.sonuclar)])
        self._tally_secildi()

    def _tally_secildi(self, *_a) -> None:
        s = self.secili()
        _kutu_doldur(self.skor, [(k, k) for k in (s.skorlar if s else ())])
        gruplar = [(_("Toplam (tüm gruplar)"), None)]
        if s is not None and s.grup_sayisi > 1:
            gruplar += [(_("Grup %d") % (g + 1), g) for g in range(s.grup_sayisi)]
        _kutu_doldur(self.grup, gruplar)
        self.degisti.emit()

    def secili(self):
        i = self.tally.currentData()
        return self.sonuclar[i] if i is not None and 0 <= i < len(self.sonuclar) else None

    def opaklik(self) -> float:
        return self.saydamlik.value() / _YUZDE

    def esik_orani(self) -> float:
        return self.esik.value() / _YUZDE


class KaynakPaneli(QtWidgets.QGroupBox):
    degisti = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(_("Kaynak noktaları"), parent)
        self.setCheckable(True)
        self.setChecked(False)
        from cekirdek import cizim_goruntu as cg
        self.kaynak = QtWidgets.QComboBox()
        self.kaynak.addItem(_("Model kaynağı (settings.source)"), KAYNAK_AYAR)
        self.kaynak.addItem(_("Statepoint kaynak bankası"), KAYNAK_STATEPOINT)
        self.sayi = QtWidgets.QSpinBox()
        self.sayi.setRange(_KAYNAK_EN_AZ, cg.KAYNAK_EN_COK)
        self.sayi.setValue(_KAYNAK_VARSAYILAN)
        self.kalinlik = sayi(0.0, 3, 0.0, _KONUM_SINIRI, 1.0, "cm")
        self.kalinlik.setSpecialValueText(_("tümü (izdüşüm)"))
        f = _form(self)
        f.addRow(_("Kaynak:"), self.kaynak)
        f.addRow(_("Nokta sayısı:"), self.sayi)
        f.addRow(_("Dilim kalınlığı:"), self.kalinlik)
        self.kaynak.currentIndexChanged.connect(lambda *_a: self.degisti.emit())
        self.sayi.editingFinished.connect(self.degisti.emit)
        self.kalinlik.editingFinished.connect(self.degisti.emit)
        self.toggled.connect(lambda *_a: self.degisti.emit())

    def kalinlik_degeri(self):
        return self.kalinlik.value() or None


class UcBoyutPaneli(QtWidgets.QGroupBox):
    ciz = QtCore.Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(_("3B görünüm"), parent)
        varsayilan = km.Kamera()
        self.renk = QtWidgets.QComboBox()
        self.renk.addItem(_("Malzeme"), rk.MALZEME)
        self.renk.addItem(_("Hücre"), rk.HUCRE)
        self.azimut = sayi(varsayilan.azimut, 0, -180.0, 180.0, 15.0, "°")
        self.yukselti = sayi(varsayilan.yukselti, 0, -89.0, 89.0, 15.0, "°")
        self.uzaklik = sayi(varsayilan.uzaklik_kati, 2, 0.1, 10.0, 0.1, "")
        self.gorus = sayi(varsayilan.gorus, 0, 5.0, 120.0, 5.0, "°")
        self.gizli = QtWidgets.QListWidget()
        self.gizli.setMaximumHeight(120)
        self.cizdir = QtWidgets.QPushButton(_("Çiz"))
        f = _form(self)
        f.addRow(_("Renklendirme:"), self.renk)
        f.addRow(_("Azimut:"), self.azimut)
        f.addRow(_("Yükselti:"), self.yukselti)
        f.addRow(_("Uzaklık katı:"), self.uzaklik)
        f.addRow(_("Görüş açısı:"), self.gorus)
        f.addRow(_("Gizlenen malzemeler:"), self.gizli)
        f.addRow(self.cizdir)
        f.addRow(ipucu(_("2B modelde geometri eksenel sonsuzdur: 3B görünüm sonsuz prizmayı "
                         "gösterir.")))
        self.cizdir.clicked.connect(self.ciz.emit)

    def malzemeleri_ayarla(self, malzemeler) -> None:
        """[(kimlik, ad)] -- isaretli olanlar gizlenir (onceki secim korunur)."""
        eski = set(self.gizlenenler())
        self.gizli.clear()
        for kimlik, ad in malzemeler:
            oge = QtWidgets.QListWidgetItem("%s (%d)" % (ad, kimlik))
            oge.setData(QtCore.Qt.UserRole, int(kimlik))
            oge.setFlags(oge.flags() | QtCore.Qt.ItemIsUserCheckable)
            oge.setCheckState(QtCore.Qt.Checked if kimlik in eski else QtCore.Qt.Unchecked)
            self.gizli.addItem(oge)

    def gizlenenler(self) -> list:
        return [self.gizli.item(i).data(QtCore.Qt.UserRole) for i in range(self.gizli.count())
                if self.gizli.item(i).checkState() == QtCore.Qt.Checked]

    def kamera(self) -> km.Kamera:
        return km.Kamera(azimut=self.azimut.value(), yukselti=self.yukselti.value(),
                         uzaklik_kati=self.uzaklik.value(), gorus=self.gorus.value())
