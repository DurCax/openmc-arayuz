# -*- coding: utf-8 -*-
"""
galeri.py -- tasarim sisteminin bilesen galerisi.

    python -m arayuz.tasarim.galeri                   # pencere (tema/vurgu secilebilir)
    python -m arayuz.tasarim.galeri --kaydet DIZIN    # galeri_{acik,koyu}.png (+ palet)

Butun bilesenler ve form ogeleri normal / odak / hata / pasif durumlariyla
yan yana durur; tasarim kararlari (vurgu, yogunluk) burada karsilastirilir.
"""

import argparse
import os
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from arayuz import bilesenler as b
from arayuz.tasarim import stil, tokenlar
from cekirdek.ceviri import _

A = tokenlar.ARALIK


def _satir(*widgetlar, bosluk=A["s"]):
    w = QtWidgets.QWidget()
    d = QtWidgets.QHBoxLayout(w)
    d.setContentsMargins(0, 0, 0, 0)
    d.setSpacing(bosluk)
    for x in widgetlar:
        d.addWidget(x)
    d.addStretch(1)
    return w


def _dugmeler_karti():
    k = b.Kart(_("Düğmeler"), aciklama=_("Birincil eylem ekranda bir tane olur."))
    k.ekle(_satir(b.birincil_dugme(_("Çalıştır"), "play"), b.ikincil_dugme(_("Kaydet"), "save"),
                  b.duz_dugme(_("İptal")), b.tehlikeli_dugme(_("Sil"), "trash")))
    pasif = b.birincil_dugme(_("Çalıştır"), "play")
    pasif.setEnabled(False)
    pasif2 = b.ikincil_dugme(_("Pasif"))
    pasif2.setEnabled(False)
    k.ekle(_satir(pasif, pasif2, b.baglanti_dugmesi(_("Belgeleri aç"))))
    k.ekle(_satir(*(b.ikon_dugmesi(ad, ipucu) for ad, ipucu in (
        ("file-plus", _("Yeni")), ("folder-open", _("Aç")), ("save", _("Kaydet")),
        ("undo-2", _("Geri al")), ("redo-2", _("Yinele")), ("search", _("Ara")),
        ("settings", _("Ayarlar")), ("panel-right", _("Önizleme"))))))
    k.ekle(b.SegmentSecici([("hizli", _("Hızlı")), ("dengeli", _("Dengeli")),
                            ("hassas", _("Hassas")), ("ozel", _("Özel"))], "dengeli"))
    return k


def _girisler_karti():
    k = b.Kart(_("Girişler"), aciklama=_("Ondalık ayırıcı nokta; birim sağda."))
    form = QtWidgets.QFormLayout()
    form.setHorizontalSpacing(A["m"])
    form.setVerticalSpacing(A["s"])
    form.addRow(_("Ad"), QtWidgets.QLineEdit("UO2 %3.20"))
    hatali = QtWidgets.QLineEdit("-0.5")
    stil.durum_ayarla(hatali, "hata", True)
    hatali.setToolTip(_("Yoğunluk pozitif olmalı"))
    form.addRow(_("Yoğunluk (hata)"), hatali)
    form.addRow(_("Adım"), b.SayiBirim(birim="cm", deger=1.26, ondalik=4))
    form.addRow(_("Yarıçap"), b.SayiBirim(birimler={"cm": 1.0, "mm": 0.1}, deger=0.4096))
    form.addRow(_("Sıcaklık"), b.SayiBirim(birim="K", deger=900, ondalik=1, en_cok=3000))
    kombo = QtWidgets.QComboBox()
    kombo.addItems([_("Özdeğer (k-eff)"), _("Sabit kaynak")])
    form.addRow(_("Koşu türü"), kombo)
    pasif = QtWidgets.QLineEdit(_("salt okunur"))
    pasif.setEnabled(False)
    form.addRow(_("Pasif"), pasif)
    k.govde.addLayout(form)
    return k


def _secimler_karti():
    k = b.Kart(_("Seçimler ve ilerleme"))
    c1 = QtWidgets.QCheckBox(_("Shannon entropisi"))
    c1.setChecked(True)
    c2 = QtWidgets.QCheckBox(_("Aki tally'si"))
    r1 = QtWidgets.QRadioButton(_("2B (sonsuz eksenel)"))
    r1.setChecked(True)
    r2 = QtWidgets.QRadioButton(_("3B"))
    k.ekle(_satir(c1, c2))
    k.ekle(_satir(r1, r2))
    ilerleme = QtWidgets.QProgressBar()
    ilerleme.setValue(62)
    k.ekle(ilerleme)
    kaydirici = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    kaydirici.setValue(40)
    k.ekle(kaydirici)
    return k


def _rozetler_karti():
    k = b.Kart(_("Rozetler"))
    k.ekle(_satir(b.Rozet(_("Hata yok"), "basari"), b.Rozet(_("2 uyarı"), "uyari"),
                  b.Rozet(_("1 hata"), "hata"), b.Rozet(_("2B"), "bilgi"),
                  b.Rozet(_("Özdeğer"), "notr"), b.Rozet(_("Yeni"), "vurgu")))
    k.ekle(b.BolumBasligi(_("Bölüm başlığı"), _("Kısa açıklama bir satır."),
                          b.duz_dugme(_("Tümü"))))
    return k


def _tablo_karti():
    k = b.Kart(_("Tablo ve liste"), eylem=b.ikon_dugmesi("plus", _("Satır ekle")))
    t = QtWidgets.QTableWidget(4, 3)
    t.setHorizontalHeaderLabels([_("Nüklid"), _("Oran"), _("Tür")])
    for i, (n, o, tur) in enumerate((("U235", "0.0320", "ao"), ("U238", "0.9680", "ao"),
                                     ("O16", "2.0000", "ao"), ("B10", "0.0002", "wo"))):
        for j, v in enumerate((n, o, tur)):
            t.setItem(i, j, QtWidgets.QTableWidgetItem(v))
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setStretchLastSection(True)
    t.selectRow(1)
    t.setFixedHeight(150)
    k.ekle(t)
    agac = QtWidgets.QTreeWidget()
    agac.setHeaderLabels([_("Örnek"), _("Kategori")])
    for kat, adlar in ((_("PWR"), ("PWR 17×17", "PWR pin")), (_("Kriter"), ("Godiva",))):
        ust = QtWidgets.QTreeWidgetItem([kat, ""])
        for ad in adlar:
            ust.addChild(QtWidgets.QTreeWidgetItem([ad, kat]))
        agac.addTopLevelItem(ust)
    agac.expandAll()
    agac.setFixedHeight(130)
    k.ekle(agac)
    return k


def _kenar_karti():
    from arayuz.tasarim.maket_veri import kenar_cubugu_kur
    k = b.Kart(_("Kenar çubuğu"), aciklama=_("Geniş ve dar; durum: ✓ tamam, ! hata, • eksik."))
    genis = kenar_cubugu_kur("demet")
    dar = kenar_cubugu_kur("kor")
    dar.daralt(True)
    for w in (genis, dar):
        w.setFixedHeight(420)
    k.ekle(_satir(genis, dar, bosluk=A["l"]))
    return k


def _bos_karti():
    k = b.Kart(_("Boş durum"))
    bos = b.BosDurum("chart-line", _("Henüz sonuç yok"),
                     _("Modeli çalıştırdığınızda k-eff ve yakınsama burada görünür."),
                     _("Çalıştır"), "play")
    bos.setMinimumHeight(260)
    k.ekle(bos)
    return k


class GaleriPenceresi(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(_("Tasarım galerisi"))
        kaydirma = QtWidgets.QScrollArea()
        kaydirma.setObjectName("sayfa")
        kaydirma.setWidgetResizable(True)
        kaydirma.setFrameShape(QtWidgets.QFrame.NoFrame)
        sayfa = QtWidgets.QWidget()
        sayfa.setObjectName("sayfa")
        izgara = QtWidgets.QGridLayout(sayfa)
        izgara.setContentsMargins(A["xl"], A["xl"], A["xl"], A["xl"])
        izgara.setSpacing(A["l"])
        ust = QtWidgets.QHBoxLayout()
        baslik = QtWidgets.QLabel(_("Tasarım sistemi"))
        baslik.setObjectName("baslikBuyuk")
        ust.addWidget(baslik)
        ust.addStretch(1)
        from arayuz import tema
        self.tema_secici = b.SegmentSecici([("acik", _("Açık")), ("koyu", _("Koyu"))],
                                           tema.etkin(), ikonlar={"acik": "sun", "koyu": "moon"})
        self.tema_secici.secildi.connect(self._tema)
        self.vurgu_secici = b.SegmentSecici(
            [(k, _(v["ad"])) for k, v in tokenlar.VURGULAR.items()], tema.etkin_vurgu())
        self.vurgu_secici.secildi.connect(self._vurgu)
        ust.addWidget(self.vurgu_secici)
        ust.addWidget(self.tema_secici)
        izgara.addLayout(ust, 0, 0, 1, 3)
        izgara.addWidget(_dugmeler_karti(), 1, 0)
        izgara.addWidget(_girisler_karti(), 1, 1)
        sag = QtWidgets.QVBoxLayout()
        sag.setSpacing(A["l"])
        sag.addWidget(_secimler_karti())
        sag.addWidget(_rozetler_karti())
        izgara.addLayout(sag, 1, 2)
        izgara.addWidget(_kenar_karti(), 2, 0)
        izgara.addWidget(_tablo_karti(), 2, 1)
        izgara.addWidget(_bos_karti(), 2, 2)
        izgara.setRowStretch(3, 1)
        for s in range(3):
            izgara.setColumnStretch(s, 1)
        kaydirma.setWidget(sayfa)
        self.setCentralWidget(kaydirma)
        eylemler = [QtGui.QAction(m, self) for m in (
            _("Yeni model…"), _("Aç…"), _("Kaydet"), _("Farklı kaydet…"), _("Çalıştır"),
            _("Doğrula"), _("Koyu tema"), _("Açık tema"), _("Rapor oluştur…"))]
        eylemler[2].setShortcut(QtGui.QKeySequence.Save)
        eylemler[4].setShortcut(QtGui.QKeySequence("F5"))
        self.palet = b.KomutPaleti(self, eylemler)

    def _tema(self, ad):
        from arayuz import tema
        tema.uygula(QtWidgets.QApplication.instance(), ad)

    def _vurgu(self, vurgu):
        from arayuz import tema
        tema.uygula(QtWidgets.QApplication.instance(), tema.etkin(), vurgu)

    def ornek_bildirimler(self):
        b.bildir(self, _("Model kaydedildi: pwr_17x17.json"), "basari", 0)
        b.bildir(self, _("Kılavuz boru malzemesi tanımsız."), "uyari", 0,
                 baslik=_("Doğrulama"), eylem_metni=_("Bulguya git"), eylem=lambda: None)
        b.bildir(self, _("OpenMC süreci beklenmedik biçimde sonlandı."), "hata", 0)


def kaydet(dizin, boyut=(1440, 1280), vurgu=None):
    from arayuz import tema
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    os.makedirs(dizin, exist_ok=True)
    yollar = []
    for ad in ("acik", "koyu"):
        tema.uygula(app, ad, vurgu)
        g = GaleriPenceresi()
        g.resize(*boyut)
        g.show()
        g.ornek_bildirimler()
        app.processEvents()
        yol = os.path.join(dizin, "galeri_%s.png" % ad)
        g.grab().save(yol)
        g.palet.ac()
        g.palet.arama.setText("kay")
        app.processEvents()
        yol2 = os.path.join(dizin, "galeri_palet_%s.png" % ad)
        g.grab(QtCore.QRect(0, 0, boyut[0], 640)).save(yol2)
        yollar += [yol, yol2]
        g.close()
        g.deleteLater()
        app.processEvents()
    return yollar


def main(argv=None):
    ayr = argparse.ArgumentParser(description=_("Tasarım sistemi galerisi"))
    ayr.add_argument("--kaydet", metavar="DIZIN", help=_("iki temanın PNG'sini yazar"))
    ayr.add_argument("--vurgu", choices=sorted(tokenlar.VURGULAR), default=None)
    a = ayr.parse_args(argv)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    if a.kaydet:
        for yol in kaydet(a.kaydet, vurgu=a.vurgu):
            print(yol)
        return 0
    from arayuz import tema
    tema.uygula(app, None, a.vurgu)
    g = GaleriPenceresi()
    g.resize(1440, 1000)
    g.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
