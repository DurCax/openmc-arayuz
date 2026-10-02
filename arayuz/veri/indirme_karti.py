# -*- coding: utf-8 -*-
"""
indirme_karti.py -- Veri sayfasinin "Indir" karti: kutuphane secimi (openmc.org
katalogu; boyut, sicakliklar, kullanim/lisans notu), zincir secimi (termal /
hizli / CASL), hedef klasor, disk alani, arka planda indirme (ilerleme, iptal,
surdurme). Isi cekirdek/veri_indir.py yapar; bu kart yalniz sunar.
"""

import html
import os

from PySide6 import QtCore, QtWidgets

from arayuz import bilesenler as b
from arayuz.tasarim import tokenlar
from arayuz.veri.isci import IndirmeIscisi
from cekirdek import veri_arsiv, veri_indir, veri_yolu
from cekirdek.ceviri import _, N_
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)
A = tokenlar.ARALIK
GB = veri_arsiv.GB
_ILERLEME_OLCEGI = 1000                   # QProgressBar 0..1000 (int 32 bit sinirinin altinda)
_ASAMA_ADI = {"indirme": N_("indiriliyor"), "acma": N_("açılıyor")}


def _gb(bayt):
    return _("%.2f GB") % (bayt / GB)


class IndirmeKarti(b.Kart):
    """Kutuphane + zincir indirme karti. kuruldu: [(Oge, Kurulum)] (ayar yazildiktan sonra)."""

    kuruldu = QtCore.Signal(object)
    durum = QtCore.Signal(str, bool)          # bildirim metni, basarili mi

    def __init__(self, katalog=None, politika=None, parent=None):
        super().__init__(_("Kütüphane indir"),
                         _("openmc.org resmî listesinden seçin; indirme arka planda sürer, "
                           "iptal edilirse kaldığı yerden devam eder."), parent=parent)
        self.katalog = katalog or veri_indir.katalog_yukle()
        self.politika = politika              # None -> uretim politikasi (yalniz https)
        self._isci = None
        self._tablo_kur()
        self._zincirleri_kur()
        self._hedef_kur()
        self._kosu_kur()
        self.tablo.selectRow(self._varsayilan_satir())
        self._alan_guncelle()

    # ------------------------------------------------------------------ kurulum
    def _tablo_kur(self):
        kutup = self.katalog.kutuphaneler
        self.tablo = QtWidgets.QTableWidget(len(kutup), 3)
        self.tablo.setHorizontalHeaderLabels([_("Kütüphane"), _("Arşiv"), _("Sıcaklıklar")])
        self.tablo.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tablo.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tablo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.horizontalHeader().setStretchLastSection(True)
        for i, o in enumerate(kutup):
            for j, metin in enumerate((o.ad, _gb(o.bayt), o.sicakliklar)):
                oge = QtWidgets.QTableWidgetItem(metin)
                oge.setData(QtCore.Qt.UserRole, o.kimlik)
                oge.setToolTip(o.metin("icerik"))
                self.tablo.setItem(i, j, oge)
        self.tablo.resizeColumnsToContents()
        self.tablo.itemSelectionChanged.connect(self._secim_degisti)
        self.ekle(self.tablo)
        self.not_etiketi = QtWidgets.QLabel()
        self.not_etiketi.setObjectName("ikincil")
        self.not_etiketi.setWordWrap(True)
        self.not_etiketi.setOpenExternalLinks(True)
        self.not_etiketi.setTextFormat(QtCore.Qt.RichText)
        self.ekle(self.not_etiketi)
        self.kutuphane_de = QtWidgets.QCheckBox(_("Seçili kütüphaneyi indir"))
        self.kutuphane_de.setChecked(True)
        self.kutuphane_de.toggled.connect(self._alan_guncelle)
        self.ekle(self.kutuphane_de)

    def _zincirleri_kur(self):
        self.ekle(b.BolumBasligi(_("Tükenme zincirleri"),
                                 aciklama=_("Yalnız tükenme hesabı için gerekir.")))
        satir = QtWidgets.QWidget()
        d = QtWidgets.QHBoxLayout(satir)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(A["l"])
        self.zincir_kutulari = {}
        for o in self.katalog.zincirler:
            if not o.uygulamada_kullanilir:
                continue
            kutu = QtWidgets.QCheckBox("%s (%.0f MB)" % (o.gorunen_ad(), o.bayt / 1e6))
            kutu.setChecked(True)
            kutu.setToolTip(o.dosya_adi)
            kutu.toggled.connect(self._alan_guncelle)
            self.zincir_kutulari[o.kimlik] = kutu
            d.addWidget(kutu)
        d.addStretch(1)
        self.ekle(satir)

    def _hedef_kur(self):
        satir = QtWidgets.QWidget()
        d = QtWidgets.QHBoxLayout(satir)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(A["s"])
        d.addWidget(QtWidgets.QLabel(_("Hedef klasör:")))
        self.hedef = QtWidgets.QLineEdit(veri_yolu.varsayilan_indirme_hedefi())
        self.hedef.setAccessibleName(_("Hedef klasör"))
        self.hedef.editingFinished.connect(self._alan_guncelle)
        d.addWidget(self.hedef, 1)
        self.d_gozat = b.ikincil_dugme(_("Gözat…"), "folder-open")
        self.d_gozat.clicked.connect(self._hedef_sec)
        d.addWidget(self.d_gozat)
        self.ekle(satir)
        self.alan_etiketi = QtWidgets.QLabel()
        self.alan_etiketi.setObjectName("kucuk")
        self.alan_etiketi.setWordWrap(True)
        self.ekle(self.alan_etiketi)

    def _kosu_kur(self):
        satir = QtWidgets.QWidget()
        d = QtWidgets.QHBoxLayout(satir)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(A["s"])
        self.d_indir = b.birincil_dugme(_("İndir"), "download")
        self.d_indir.clicked.connect(self.indir)
        self.d_iptal = b.ikincil_dugme(_("İptal"), "x")
        self.d_iptal.clicked.connect(self.iptal)
        self.d_iptal.setEnabled(False)
        self.cubuk = QtWidgets.QProgressBar()
        self.cubuk.setRange(0, _ILERLEME_OLCEGI)
        self.cubuk.setProperty("metinli", True)
        self.cubuk.setTextVisible(True)
        self.cubuk.setFormat("")
        d.addWidget(self.d_indir)
        d.addWidget(self.d_iptal)
        d.addWidget(self.cubuk, 1)
        self.ekle(satir)
        self.durum_etiketi = QtWidgets.QLabel()
        self.durum_etiketi.setWordWrap(True)
        self.durum_etiketi.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.ekle(self.durum_etiketi)

    # ------------------------------------------------------------------ secim
    def _varsayilan_satir(self):
        kimlikler = [o.kimlik for o in self.katalog.kutuphaneler]
        secili = veri_yolu.ayar_oku().get("kutuphane") or veri_indir.VARSAYILAN_KUTUPHANE
        return kimlikler.index(secili) if secili in kimlikler else 0

    def secili_kutuphane(self):
        satirlar = self.tablo.selectionModel().selectedRows()
        if not satirlar:
            return None
        return self.katalog.kutuphaneler[satirlar[0].row()]

    def secili_zincirler(self):
        return [self.katalog.bul(k) for k, kutu in self.zincir_kutulari.items()
                if kutu.isChecked()]

    def isler(self):
        """Indirilecek ogeler: once zincirler (kucuk), sonra kutuphane."""
        kutup = self.secili_kutuphane() if self.kutuphane_de.isChecked() else None
        return self.secili_zincirler() + ([kutup] if kutup else [])

    def _secim_degisti(self):
        o = self.secili_kutuphane()
        if o is None:
            self.not_etiketi.setText("")
        else:
            esc = lambda s: html.escape(s or "", quote=True)  # noqa: E731
            parcalar = [esc(o.metin(a)) for a in ("icerik", "notu", "lisans_notu")]
            if not o.sha256:
                parcalar.append(esc(_("sha256 yayımlanmamış: indirmede yalnız boyut denetlenir.")))
            if o.degerlendirme_sayfasi:         # katalog yuklenirken https + izinli alan
                parcalar.append('<a href="%s">%s</a>' % (esc(o.degerlendirme_sayfasi),
                                                         esc(_("Değerlendirme sayfası"))))
            self.not_etiketi.setText("<br>".join(p for p in parcalar if p))
        self._alan_guncelle()

    def _hedef_sec(self):
        dizin = QtWidgets.QFileDialog.getExistingDirectory(self, _("Hedef klasör"),
                                                           self.hedef.text())
        if dizin:
            self.hedef.setText(dizin)
            self._alan_guncelle()

    # ------------------------------------------------------------------ alan
    def gereken_bayt(self, hedef):
        return sum(veri_indir.gereken_alan(o, self.katalog.oran, hedef) for o in self.isler())

    def _yarim_var_mi(self, hedef):
        return any(veri_indir.gereken_alan(o, 1.0, hedef) < o.bayt
                   for o in self.isler() if o.tur == "zincir") or any(
            os.path.isfile(os.path.join(hedef, veri_indir.INDIRME_DIZINI,
                                        o.kimlik + ".tar.xz" + veri_indir.PARCA_UZANTISI))
            for o in self.isler() if o.tur == "kutuphane")

    def _alan_guncelle(self, *_a):
        hedef = self.hedef.text().strip()
        if not hedef or not os.path.isabs(hedef):
            self.alan_etiketi.setText(_("Mutlak bir hedef klasör yolu girin."))
            return
        gereken = self.gereken_bayt(hedef)
        try:
            bos = veri_arsiv.bos_alan(hedef)
        except OSError as e:
            _log.warning("bos alan olculemedi: %s", hedef, exc_info=True)
            self.alan_etiketi.setText(_("Boş alan ölçülemedi: %s") % e)
            return
        tahmin = any(o.tur == "kutuphane" and not o.acik_bayt for o in self.isler())
        self.alan_etiketi.setText(
            _("Gerekli: %s (indirme + açılmış kütüphane%s) · boş: %s") % (
                _gb(gereken + veri_arsiv.DISK_PAYI),
                _("; açılmış boyut tahmini") if tahmin else "", _gb(bos)))
        if self._isci is None:
            self.d_indir.setText(_("Sürdür") if self._yarim_var_mi(hedef) else _("İndir"))

    # ------------------------------------------------------------------ indirme
    def indiriyor_mu(self):
        return self._isci is not None

    def indir(self):
        if self._isci is not None:
            return False
        isler = self.isler()
        if not isler:
            self._durum_yaz(_("İndirilecek bir şey seçilmedi."), False)
            return False
        try:
            hedef = veri_arsiv.hedef_dogrula(self.hedef.text().strip())
            veri_arsiv.disk_denetle(hedef, self.gereken_bayt(hedef))
        except veri_arsiv.VeriHatasi as e:
            self._durum_yaz(str(e), False)
            return False
        self._isci = IndirmeIscisi(isler, hedef, self.katalog.oran, politika=self.politika,
                                   parent=self)
        self._isci.ilerleme.connect(self._ilerleme)
        self._isci.basarili.connect(lambda s, h=hedef: self._basarili(s, h))
        self._isci.basarisiz.connect(lambda m: self._bitti(m, False))
        self._isci.iptal_edildi.connect(lambda: self._bitti(
            _("İptal edildi. 'Sürdür' kaldığı yerden devam eder."), False))
        self._dugmeler(True)
        self._durum_yaz(_("Başlıyor…"), True)
        self._isci.start()
        return True

    def iptal(self):
        if self._isci is not None:
            self._isci.iptal_et()
            self.d_iptal.setEnabled(False)

    def bekle(self, ms=None):
        """Isci bitene dek bekler (pencere kapanisi ve testler)."""
        if self._isci is not None:
            return self._isci.wait() if ms is None else self._isci.wait(ms)
        return True

    def _dugmeler(self, calisiyor):
        self.d_indir.setEnabled(not calisiyor)
        self.d_iptal.setEnabled(calisiyor)
        for w in (self.tablo, self.hedef, self.d_gozat, self.kutuphane_de,
                  *self.zincir_kutulari.values()):
            w.setEnabled(not calisiyor)

    def _ilerleme(self, asama, ad, alinan, toplam):
        oran = (alinan / toplam) if toplam else 0.0
        self.cubuk.setValue(int(oran * _ILERLEME_OLCEGI))
        self.cubuk.setFormat("%d%%" % int(oran * 100))
        self.durum_etiketi.setText(_("%s — %s %s / %s") % (
            ad, _(_ASAMA_ADI.get(asama, asama)), _gb(alinan), _gb(toplam)))

    def _durum_yaz(self, metin, basarili):
        self.durum_etiketi.setText(metin)
        self.durum.emit(metin, basarili)

    def _isci_birak(self):
        isci, self._isci = self._isci, None
        if isci is not None:
            isci.wait()
            isci.deleteLater()

    def _bitti(self, metin, basarili):
        self._isci_birak()
        self._dugmeler(False)
        self._alan_guncelle()
        self._durum_yaz(metin, basarili)

    def _basarili(self, sonuclar, hedef):
        try:
            veri_yolu.ayar_yaz(_ayar(sonuclar, hedef))
        except (OSError, ValueError) as e:
            _log.warning("veri ayari yazilamadi", exc_info=True)
            self._bitti(_("İndirildi ama seçim kaydedilemedi: %s") % e, False)
            return
        self.cubuk.setValue(_ILERLEME_OLCEGI)
        self.cubuk.setFormat("100%")
        etiketler = sorted({veri_indir.dogrulama_etiketi(k) for _o, k in sonuclar} - {""})
        self._bitti(_("Tamam: %s") % ", ".join(o.gorunen_ad() for o, _k in sonuclar)
                    + "".join(" · " + e for e in etiketler), True)
        self.kuruldu.emit(sonuclar)


def _ayar(sonuclar, hedef):
    """Basarili kurulumdan veri_yolu ayari (yeni sozluk)."""
    ayar = {"indirme_hedefi": hedef}
    zincirler = [k.yol for o, k in sonuclar if o.tur == "zincir"]
    if zincirler:
        varsayilan = [y for y in zincirler if os.path.basename(y) == veri_yolu.VARSAYILAN_ZINCIR]
        ayar["zincir"] = (varsayilan or zincirler)[0]
    for o, k in sonuclar:
        if o.tur == "kutuphane":
            ayar.update(cross_sections=k.yol, kutuphane=o.kimlik)
    return ayar
