# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_tukenme.py  --  Yanma (tukenme) ayarlari, kosusu ve sonuclari
================================================================================
 Ayarlar spec'in "tukenme" bolumune yazilir (diger editor sekmeleri gibi).
 Kosu `python -m cekirdek.tukenme` ALT SURECI olarak QProcess ile yapilir:
 openmc.lib icindeki bir C++ terminate() tum sureci oldurur (onizlemede
 yasandi); arayuz bu kodu kendi surecinde asla calistirmaz.

 SAYFA (alt sekme YOK, yukaridan asagiya tek akis)
   acma anahtari + kisa aciklama      -- tukenme kapaliyken YALNIZCA bunlar
   guc, adim birimi, adimlar, yanan malzemeler
   Gelismis: zincir, entegrator, cubuk cubuk yanma (yakit birden fazla
             ornekse), izlenen nuklidler
   kosu cubugu, onceki sonuc/eskime isareti, grafik, tablo
   Ayrintili cikti (katlanir; hata olursa kendiliginden acilir)
 Modelde tukenme uygun degilse (uygunluk.tukenme_uygun) sekme zaten gizlidir;
 sekme yine de gosterilirse yalnizca nedenini soyleyen bos durum gorunur.

 Ilerleme olculur, tahmin edilmez: toplam transport sayisi bilinir
 ((adim x entegrator basina) + 1) ve ILK transport bittiginde kalan sure
 onun gercek suresinden hesaplanir.

 PROJE KUSAGI
   sifirla() bir kusak sayacini artirir; onceki projede baslamis bir kosunun
   ya da onceki-sonuc okumasinin sonucu YENI projeye yazilmaz.
================================================================================
"""

import copy
import json
import os
import sys
import time

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import tukenme as _tk
from arayuz.ortak import BosDurum, GelismisBolum, SekmeTabani, cumle_basi, sayi
from arayuz.sekme_analiz import aciklama, dar

ZINCIR_SECENEK = [
    ("otomatik",    "Otomatik (spektrumdan)"),
    ("termal",      "ENDF/B-VIII.0 termal (3820 nüklid)"),
    ("hizli",       "ENDF/B-VIII.0 hızlı (3820 nüklid)"),
    ("casl_termal", "CASL basit termal (228 nüklid, ~3 kat hızlı)"),
    ("casl_hizli",  "CASL basit hızlı (228 nüklid, ~3 kat hızlı)"),
]

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _tema_renk(ad, vars_="#6b7785"):
    try:
        from arayuz import tema
        return tema.renk(ad)
    except Exception:
        return vars_


def yakit_ornek_sayisi(spec):
    """Geriye uyum: sayim cekirdek/tukenme.py'de."""
    return _tk.yakit_ornek_sayisi(spec)


class _OncekiIsci(QtCore.QThread):
    """
    Onceki sonucu arka planda okur.

    Olculdu: 3.4 s -- openmc.deplete ice aktarimi (kutuphane yukleniyor,
    1.2 s) + Results() dosyadaki 3820 nuklidin hepsini ayristiriyor (2.0 s).
    Ikisi de resmi API'de kacinilmaz; OpenMC'nin ic dosya bicimini elle okumak
    surum degisince kirilirdi. Arayuzde calissa dosya acilisi 3.4 s donardi.
    """
    bitti = QtCore.Signal(object, object)      # (anahtar, sonuc | Exception)

    def __init__(self, spec, dizin, anahtar, parent=None):
        super().__init__(parent)
        self._spec = copy.deepcopy(spec)       # arayuz spec'i degistirirse yaris olmasin
        self._dizin = dizin
        self._anahtar = anahtar

    def run(self):
        try:
            self.bitti.emit(self._anahtar, _tk.onceki_sonuc(self._spec, self._dizin))
        except Exception as e:
            self.bitti.emit(self._anahtar, e)


class TukenmeSekmesi(SekmeTabani):

    KONU = "tukenme"
    durum = QtCore.Signal(str, bool)
    # Gosterilen tukenme sonucunun durumu degisti (bitti / basarisiz / okundu /
    # sifirlandi).
    sonuc_degisti = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.proje_yolu = None
        self.okuma_kaynagi = None     # kopyasi acilmis ornek (yalnizca OKUMA)
        self._kapi = lambda: (False, "hazır değil")
        self._surec = None
        self._dizin = None
        self._tampon = ""
        self._transport = 0
        self._t0 = None
        self._t_ilk = None
        self._kusak = 0               # proje kusagi (sifirla artirir)
        self._kosu_kusagi = None      # suren kosunun kusagi
        self._okuma_kusagi = None     # suren onceki-sonuc okumasinin kusagi
        self._kosu_spec = None        # kosunun baslatildigi spec (kopya)
        self._uygun = (True, "")

        # ---------------- uygun degil ----------------
        self.bos = BosDurum("Bu modelde tükenme hesabı yapılamaz", "", None, "∅")

        # ---------------- acma anahtari ----------------
        self.var = QtWidgets.QCheckBox("Tükenme (yanma) hesabını etkinleştir")
        self.aciklama = aciklama(
            "Yakıtın zamanla tükenmesini ve k-eff'in yanmayla değişimini hesaplar. "
            "Her adım en az bir OpenMC koşusudur; süre adım sayısıyla artar.")

        # ---------------- temel ayarlar ----------------
        self.guc = sayi(40.0, 3, 0.001, 10000.0, 1.0, " W/gHM")
        self.guc.setToolTip(
            "Güç yoğunluğu, ağır metalin gramı başına. Mutlak güç kullanılmaz:\n"
            "2B bir modelde 'cm başına' olmak zorunda kalırdı.\n\n"
            "Tipik: PWR 38–40, BWR ~25, SFR 50–100 W/gHM.")
        self.birim = QtWidgets.QComboBox()
        self.birim.addItem("gün", "d")
        self.birim.addItem("MWd/kg (yanma)", "MWd/kg")
        self.adimlar = QtWidgets.QLineEdit()
        self.adimlar.setPlaceholderText("ör. 0.5, 1.5, 3, 5, 10, 30")
        self.adimlar.setToolTip(
            "Adım uzunlukları, virgülle. İlk adımları kısa tutun (ör. 0.5, 1.5):\n"
            "Xe-135 ~2 günde dengeye gelir ve PWR'da birkaç bin pcm'lik hızlı\n"
            "bir düşüş yaratır; uzun bir ilk adım bunu görünmez kılar.")
        self.adim_ozet = QtWidgets.QLabel("—")
        self.adim_ozet.setObjectName("soluk")
        self.adim_ozet.setWordWrap(True)
        self.malzeme_bilgi = QtWidgets.QLabel("—")
        self.malzeme_bilgi.setWordWrap(True)
        self.malzeme_bilgi.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.malzeme_bilgi.setToolTip(
            "Fisil malzemeler ve yanabilir zehirler (Gd, Er) otomatik yanar. Hacimler "
            "analitik hesaplanır: yanlış bir hacim yanma hızını aynı oranda bozar ve "
            "k-eff'te iz bırakmaz. Testte OpenMC'nin stokastik hacim hesabıyla 1σ "
            "içinde uyuştuğu ölçüldü.")
        self.zincir_uyari = QtWidgets.QLabel("")
        self.zincir_uyari.setWordWrap(True)

        form = QtWidgets.QFormLayout()
        form.addRow("Güç yoğunluğu:", self.guc)
        form.addRow("Adım birimi:", self.birim)
        form.addRow("Adımlar:", self.adimlar)
        form.addRow("", self.adim_ozet)
        form.addRow("Yanan malzemeler:", self.malzeme_bilgi)
        form.addRow("", self.zincir_uyari)

        # ---------------- gelismis ----------------
        self.zincir = QtWidgets.QComboBox()
        for k, ad in ZINCIR_SECENEK:
            self.zincir.addItem(ad, k)
        self.zincir_bilgi = QtWidgets.QLabel("-")
        self.zincir_bilgi.setObjectName("soluk")
        self.zincir_bilgi.setWordWrap(True)
        self.entegrator = QtWidgets.QComboBox()
        self.entegrator.addItem("CECM (öngörücü-düzeltici, adım başına 2 transport)", "cecm")
        self.entegrator.addItem("Predictor (adım başına 1 transport, kaba)", "predictor")
        self.ayir = QtWidgets.QCheckBox("Çubuk çubuk yanma (her örnek ayrı malzeme — çok ağır)")
        self.ayir.setToolTip("Yakıtın her örneği (ör. demetteki her çubuk) ayrı yanar; "
                             "bellek ve süre örnek sayısıyla artar.")
        self.izlenen = QtWidgets.QLineEdit()
        self.izlenen.setToolTip("Grafikte ve tabloda izlenecek nüklidler, virgülle.")
        self.gelismis = GelismisBolum("tukenme_gelismis")
        gf = QtWidgets.QFormLayout()
        gf.setContentsMargins(0, 0, 0, 0)
        gf.addRow("Zincir:", self.zincir)
        gf.addRow("", self.zincir_bilgi)
        gf.addRow("Entegratör:", self.entegrator)
        gf.addRow("", self.ayir)
        gf.addRow("İzlenen nüklidler:", self.izlenen)
        self.gelismis_form = gf
        gk = QtWidgets.QWidget()
        gk.setLayout(gf)
        self.gelismis.ekle(gk)

        # ---------------- kosu ----------------
        self.d_baslat = QtWidgets.QPushButton("Tükenmeyi başlat")
        self.d_baslat.setObjectName("birincil")
        self.d_baslat.setMinimumHeight(34)
        self.d_baslat.setMinimumWidth(150)
        self.d_durdur = QtWidgets.QPushButton("Durdur")
        self.d_durdur.setMinimumHeight(34)
        self.d_durdur.setEnabled(False)
        self.ilerleme = QtWidgets.QProgressBar()
        self.ilerleme.setTextVisible(True)
        self.ilerleme.setRange(0, 1)
        self.ilerleme.setValue(0)
        self.kapi_etiket = QtWidgets.QLabel("-")
        self.kapi_etiket.setWordWrap(True)
        self.sure_etiket = QtWidgets.QLabel("")
        self.sure_etiket.setObjectName("soluk")
        self.onceki_etiket = QtWidgets.QLabel("")
        self.onceki_etiket.setWordWrap(True)
        self._onceki = None           # onceki_sonuc() ciktisi
        self._onceki_anahtar = None   # (h5 yolu, degisiklik zamani) -- yeniden okumayi onler
        self._isci = None
        self.d_baslat.clicked.connect(self.baslat)
        self.d_durdur.clicked.connect(self.durdur)

        self.figur = Figure(figsize=(5, 4.2), tight_layout=True)
        self.tuval = FigureCanvasQTAgg(self.figur)
        self.tuval.setFixedHeight(380)
        self.eksen_k = self.figur.add_subplot(211)
        self.eksen_n = self.figur.add_subplot(212)
        self._grafik_bos()

        self.tablo = QtWidgets.QTableWidget(0, 4)
        self.tablo.setHorizontalHeaderLabels(["gün", "MWd/kg", "k-eff", "ρ [pcm]"])
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tablo.setMinimumHeight(160)

        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        lf = self.log.font(); lf.setFamily("monospace")
        lf.setStyleHint(QtGui.QFont.StyleHint.Monospace); lf.setPointSizeF(8.5)
        self.log.setFont(lf)
        self.log.setMaximumBlockCount(4000)
        self.log.setMinimumHeight(200)
        self.ayrinti = GelismisBolum("tukenme_ayrinti", "Ayrıntılı çıktı")
        self.ayrinti.ekle(self.log)

        # ---------------- yerlesim ----------------
        self.ayar_kutusu = QtWidgets.QWidget()
        ak = QtWidgets.QVBoxLayout(self.ayar_kutusu)
        ak.setContentsMargins(0, 0, 0, 0)
        ak.addWidget(dar(form))
        ak.addWidget(dar(self.gelismis))

        self.kosu_kutusu = QtWidgets.QWidget()
        kk = QtWidgets.QVBoxLayout(self.kosu_kutusu)
        kk.setContentsMargins(0, 0, 0, 0)
        ust = QtWidgets.QHBoxLayout()
        ust.addWidget(self.d_baslat)
        ust.addWidget(self.d_durdur)
        ust.addWidget(self.ilerleme, 1)
        kk.addLayout(ust)
        kk.addWidget(self.kapi_etiket)
        kk.addWidget(self.sure_etiket)

        self.sonuc_kutusu = QtWidgets.QWidget()
        sk = QtWidgets.QVBoxLayout(self.sonuc_kutusu)
        sk.setContentsMargins(0, 0, 0, 0)
        sk.addWidget(self.onceki_etiket)
        sk.addWidget(self.tuval)
        sk.addWidget(self.tablo)

        self.icerik = QtWidgets.QWidget()
        ic = QtWidgets.QVBoxLayout(self.icerik)
        ic.setContentsMargins(0, 0, 0, 0)
        ic.setSpacing(8)
        ic.addWidget(self.var)
        ic.addWidget(self.aciklama)
        ic.addWidget(self.ayar_kutusu)
        ic.addWidget(self.kosu_kutusu)
        ic.addWidget(self.sonuc_kutusu)
        ic.addWidget(self.ayrinti)
        ic.addStretch(1)

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(self.bos, 1)
        duzen.addWidget(self.icerik, 1)

        # ---------------- sinyaller ----------------
        self.var.toggled.connect(self._kaydet)
        self.ayir.toggled.connect(self._kaydet)
        for w in (self.zincir, self.birim, self.entegrator):
            w.currentIndexChanged.connect(self._kaydet)
        self.guc.valueChanged.connect(self._kaydet)
        for w in (self.adimlar, self.izlenen):
            w.editingFinished.connect(self._kaydet)
        self._gorunum_guncelle()

    # ==================================================================
    # spec <-> arayuz
    # ==================================================================
    def doldur(self):
        t = self.spec.get("tukenme") or {}
        self.var.setChecked(bool(t.get("var")))
        i = self.zincir.findData(t.get("zincir") or "otomatik")
        self.zincir.setCurrentIndex(max(i, 0))
        self.guc.setValue(float(t.get("guc_yogunlugu") or 40.0))
        i = self.birim.findData(t.get("adim_birimi") or "d")
        self.birim.setCurrentIndex(max(i, 0))
        self.adimlar.setText(", ".join("%g" % float(a) for a in (t.get("adimlar") or [])))
        i = self.entegrator.findData(t.get("entegrator") or "cecm")
        self.entegrator.setCurrentIndex(max(i, 0))
        self.ayir.setChecked(bool(t.get("malzemeleri_ayir")))
        self.izlenen.setText(", ".join(t.get("izlenen") or []))
        self._ozet_guncelle()
        self._onceki_yukle()

    @staticmethod
    def _sayilar(metin):
        cikti = []
        for p in (metin or "").replace(";", ",").split(","):
            p = p.strip()
            if not p:
                continue
            try:
                cikti.append(float(p))
            except ValueError:
                pass
        return cikti

    def _kaydet(self, *_):
        if self._yukleniyor:
            return
        # Sozluk BASTAN YAZILMAZ: arayuzde duzenlenmeyen alanlar (ek_malzemeler)
        # korunur. Kaynak sekmesinde bu hatayi bir kez yapmistik. Gizli alanlarin
        # (or. tek ornekli modelde "cubuk cubuk yanma") degeri de korunur: kutu
        # spec'ten yuklenmistir ve kullanici degistiremez.
        t = self.spec.setdefault("tukenme", {})
        t["var"] = self.var.isChecked()
        t["zincir"] = self.zincir.currentData()
        t["guc_yogunlugu"] = self.guc.value()
        t["adim_birimi"] = self.birim.currentData()
        t["adimlar"] = self._sayilar(self.adimlar.text())
        t["entegrator"] = self.entegrator.currentData()
        t["malzemeleri_ayir"] = self.ayir.isChecked()
        t["izlenen"] = [x.strip() for x in self.izlenen.text().split(",") if x.strip()]
        self._ozet_guncelle()
        self.bildir()

    def _uygunluk_oku(self):
        if not self.spec:
            return (False, "model yok")
        try:
            from cekirdek import uygunluk
            return uygunluk.tukenme_uygun(self.spec)
        except Exception:
            return (True, "")

    def _ayirma_anlamli(self):
        try:
            from cekirdek import uygunluk
            return uygunluk.tukenme_ayirma_anlamli(self.spec)
        except Exception:
            return True                  # sayilamadi: secenegi saklama

    def _ozet_guncelle(self):
        t = (self.spec or {}).get("tukenme") or {}
        self._uygun = self._uygunluk_oku()

        # --- cubuk cubuk yanma: yalnizca yakit birden fazla ornekse ---
        self.gelismis_form.setRowVisible(self.ayir, self._ayirma_anlamli())

        # --- zincir ---
        self.zincir_uyari.setText("")
        try:
            zs = _tk.zincir_secimi(self.spec)
            from cekirdek import veri_bilgi
            tamam, mesaj, _ = veri_bilgi.zincir_kontrol(zs["yol"])
            metin = ("%s  |  fisyon verimi %s eV (%s spektrum)\n%s"
                     % (os.path.basename(zs["yol"]), "%g" % zs["verim_enerjisi"],
                        _tk.SPEKTRUM_ADLARI.get(zs["temel"], zs["temel"]),
                        cumle_basi(zs["gerekce"])))
            if not tamam:
                metin += "\n" + mesaj
                # Gelismis kapaliyken de gorulsun: kosuyu engelleyen bir sorun.
                self.zincir_uyari.setText("Zincir dosyası kullanılamıyor: %s "
                                          "(Gelişmiş › Zincir)" % mesaj)
            self.zincir_bilgi.setText(metin)
            self.zincir_bilgi.setStyleSheet(
                "" if tamam else "color: %s;" % _tema_renk("hata", "#d04437"))
        except Exception as e:
            self.zincir_bilgi.setText("zincir seçilemedi: %s" % e)
        self.zincir_uyari.setStyleSheet("color: %s;" % _tema_renk("hata", "#d04437"))

        # --- adimlar ---
        adimlar = [float(a) for a in (t.get("adimlar") or [])]
        p = float(t.get("guc_yogunlugu") or 0.0)
        if adimlar and p > 0:
            if (t.get("adim_birimi") or "d") == "d":
                gun = sum(adimlar)
                bu = _tk.yanma(gun, p)
            else:
                bu = sum(adimlar)
                gun = bu * 1000.0 / p
            self.adim_ozet.setText(
                "%d adım · toplam %.4g gün = %.4g MWd/kg · %d transport çözümü"
                % (len(adimlar), gun, bu, _tk.transport_sayisi(self.spec)))
        else:
            self.adim_ozet.setText("Adım yok — virgülle adım uzunlukları girin.")

        # --- yanabilir malzemeler ---
        try:
            hv = _tk.hacimler(self.spec)
            if not hv:
                self.malzeme_bilgi.setText("Yanabilir (fisil) malzeme bulunamadı.")
            else:
                satirlar = []
                for ad, v in hv.items():
                    satirlar.append("%s: %s  [%s]\n    %s"
                                    % (ad, ("%.6g cm³" % v["hacim"]) if v["hacim"]
                                       else "hacim yok", v["yontem"], v["ayrinti"]))
                self.malzeme_bilgi.setText("\n".join(satirlar))
        except Exception as e:
            self.malzeme_bilgi.setText("hesaplanamadı: %s" % e)
        self._onceki_durum_guncelle()
        self._gorunum_guncelle()
        self.kapi_guncelle()

    def _gorunum_guncelle(self):
        """
        Bolumlerin gorunurlugu tek yerden:
          uygun degil : yalnizca bos durum (nedeni)
          kapali      : acma anahtari + aciklama (+ varsa gosterilen sonuc)
          acik        : ayarlar, Gelismis, kosu cubugu
          kosu surerken kapatilsa da kosu cubugu gorunur kalir (Durdur)
        """
        uygun, neden = self._uygun
        acik = bool(((self.spec or {}).get("tukenme") or {}).get("var"))
        kosuyor = self._surec is not None
        self.bos.setVisible(not uygun and not kosuyor)
        if not uygun:
            self.bos.ayarla(metin=_cumle(neden or "model uygun değil"))
        self.icerik.setVisible(uygun or kosuyor)
        self.ayar_kutusu.setVisible(acik)
        self.kosu_kutusu.setVisible(acik or kosuyor)
        self.aciklama.setVisible(True)
        self.sonuc_kutusu.setVisible(self.sonuc_var() or kosuyor
                                     or bool(self.onceki_etiket.text()))
        self.ayrinti.setVisible(kosuyor or bool(self.log.toPlainText()))

    # ==================================================================
    # kosu
    # ==================================================================
    def kapi_ayarla(self, fonksiyon):
        self._kapi = fonksiyon

    def proje_ayarla(self, proje_yolu, okuma_kaynagi=None):
        """
        proje_yolu    : kaydedilmis proje dosyasi (yeni kosu buraya gore yazilir)
        okuma_kaynagi : kopyasi acilmis ornek/sablon dosyasi. Onceki sonuclar
                        yalnizca OKUMAK icin oradan aranir; yeni kosu asla
                        ornek dizinine yazilmaz.
        """
        self.proje_yolu = proje_yolu
        self.okuma_kaynagi = okuma_kaynagi

    def _okuma_dizini(self):
        """Onceki sonucun aranacagi dizin (bkz. proje_ayarla)."""
        dizin = _tk.kosu_dizini(self.spec, self.proje_yolu)
        if (self.proje_yolu is None and getattr(self, "okuma_kaynagi", None)
                and not os.path.exists(os.path.join(dizin, "depletion_results.h5"))):
            dizin = _tk.kosu_dizini(self.spec, self.okuma_kaynagi)
        return dizin

    def sonuc_var(self):
        """Bir tukenme sonucu (bu kosunun ya da onceki kosunun) gosteriliyor mu."""
        return self.tablo.rowCount() > 0

    def _eski_kosu(self):
        return self._kosu_kusagi is not None and self._kosu_kusagi != self._kusak

    def sifirla(self):
        """
        PROJE degisince onceki projenin gosterilen sonucunu siler. Kusak artar:
        onceki projede baslamis ve hala suren kosunun ciktisi/sonucu, ya da
        onceki-sonuc okumasi, yeni projeye yazilmaz.
        """
        self._kusak += 1
        self.bekle()                  # suren okuma biter; sonucu kusaktan atilir
        self._onceki = self._onceki_anahtar = None
        self.onceki_etiket.setText("")
        self.onceki_etiket.setStyleSheet("")
        self.tablo.setRowCount(0)
        self._grafik_bos()
        self.log.clear()
        self.sure_etiket.setText("")
        if self._surec is None:
            self.ilerleme.setRange(0, 1)
            self.ilerleme.setValue(0)
            self.ilerleme.resetFormat()
        else:
            self.ilerleme.setRange(0, 0)
            self.kapi_etiket.setStyleSheet("color: %s;" % _tema_renk("hata", "#b3261e"))
            self.kapi_etiket.setText(
                "Önceki projenin tükenme koşusu arka planda sürüyor; sonucu bu projeye "
                "yazılmayacak. Yeni koşu için Durdur ile sonlandırın.")
        self._gorunum_guncelle()
        self.sonuc_degisti.emit()

    def kapi_guncelle(self):
        if self._surec is not None:
            return
        uygun, neden = self._uygun
        if not uygun:
            izin, mesaj = False, "Bu modelde yapılamaz: %s" % _cumle(neden)
        elif not (self.spec or {}).get("tukenme", {}).get("var"):
            izin, mesaj = False, "Tükenme kapalı — yukarıdan etkinleştirin."
        else:
            izin, mesaj = self._kapi()
        self.d_baslat.setEnabled(izin)
        self.kapi_etiket.setStyleSheet(
            "color: %s;" % (_tema_renk("metin_soluk") if izin else _tema_renk("hata", "#b3261e")))
        self.kapi_etiket.setText(mesaj)

    def baslat(self):
        izin, mesaj = self._kapi()
        uygun, neden = self._uygunluk_oku()
        if not uygun:
            QtWidgets.QMessageBox.warning(self, "Başlatılamaz",
                                          "Bu modelde yapılamaz: %s" % _cumle(neden))
            return
        if not izin or not self.spec.get("tukenme", {}).get("var"):
            QtWidgets.QMessageBox.warning(self, "Başlatılamaz", mesaj)
            return
        if self._surec is not None:
            return
        dizin = _tk.kosu_dizini(self.spec, self.proje_yolu)
        os.makedirs(dizin, exist_ok=True)
        eski = os.path.join(dizin, "depletion_results.h5")
        if os.path.exists(eski):
            os.remove(eski)
        # Kaydedilmemis degisiklikler de kosulsun: spec kosu dizinine yazilir.
        # Sonuc da BU kopyaya gore okunur (kosu surerken spec duzenlenebilir).
        self._kosu_spec = copy.deepcopy(self.spec)
        spec_yolu = os.path.join(dizin, "tukenme_spec.json")
        with open(spec_yolu, "w", encoding="utf-8") as f:
            json.dump(self._kosu_spec, f, indent=2, ensure_ascii=False)
        self._dizin = dizin
        self._kosu_kusagi = self._kusak

        self.log.clear()
        self.onceki_etiket.setText("")
        self._onceki = self._onceki_anahtar = None
        self.tablo.setRowCount(0)
        self._tampon = ""
        self._transport = 0
        self._t0 = time.time()
        self._t_ilk = None
        toplam = _tk.transport_sayisi(self.spec)
        self.ilerleme.setRange(0, toplam)
        self.ilerleme.setValue(0)
        self.ilerleme.setFormat("%v / %m transport")
        self.sure_etiket.setText("İlk transport bekleniyor — kalan süre ondan ölçülecek.")
        self._grafik_bos()

        n = (self.spec.get("calistirma") or {}).get("is_parcacigi", 8)
        self._surec = QtCore.QProcess(self)
        self._surec.setWorkingDirectory(KOK)
        ortam = QtCore.QProcessEnvironment.systemEnvironment()
        ortam.insert("PYTHONPATH", KOK)
        ortam.insert("PYTHONUNBUFFERED", "1")
        self._surec.setProcessEnvironment(ortam)
        self._surec.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self._surec.readyReadStandardOutput.connect(self._cikti_oku)
        self._surec.finished.connect(self._bitti)
        self._surec.errorOccurred.connect(self._surec_hatasi)
        arg = ["-m", "cekirdek.tukenme", spec_yolu, "-s", str(int(n)), "--dizin", dizin]
        self.log.appendPlainText("# %s %s\n" % (sys.executable, " ".join(arg)))
        self._surec.start(sys.executable, arg)
        self.d_baslat.setEnabled(False)
        self.d_durdur.setEnabled(True)
        self.kapi_etiket.setStyleSheet("color: %s;" % _tema_renk("metin_soluk"))
        self.kapi_etiket.setText("Tükenme koşusu sürüyor → %s" % dizin)
        self._gorunum_guncelle()
        self.sonuc_degisti.emit()
        self.durum.emit("Tükenme başladı → %s" % dizin, True)

    def durdur(self):
        if self._surec is not None:
            self._surec.kill()
            if not self._eski_kosu():
                self.log.appendPlainText("\n# kullanıcı tarafından durduruldu")

    def _cikti_oku(self):
        if self._surec is None:
            return
        ham = bytes(self._surec.readAllStandardOutput()).decode("utf-8", "replace")
        if self._eski_kosu():
            return                    # onceki projenin kosusu: bu projeye yazilmaz
        self._tampon += ham
        while "\n" in self._tampon:
            satir, self._tampon = self._tampon.split("\n", 1)
            satir = satir.rstrip()
            # transport ciktisi cok uzun; yalnizca anlamli satirlar loga
            # Bizim terminal satirlarimiz TAM 2 bosluk girintili; OpenMC'nin
            # cevrim satirlari cok daha derin girintili ve logu bogar.
            bizim = satir.startswith("  ") and not satir.startswith("   ")
            if (satir.startswith("[openmc.deplete]") or bizim
                    or "Combined k-effective" in satir or "TÜKENME" in satir
                    or "Error" in satir or "HATA" in satir or "Traceback" in satir):
                self.log.appendPlainText(satir)
            # Transport basina TAM BIR KEZ yazilan satir. "Creating state point"
            # SAYILMAZ: adim basi transportu iki statepoint yazar
            # (openmc_simulation_nX.h5 + statepoint.N.h5), CECM ara transportu
            # bir -- olculdu: 17 transportta 26 satir. Onu saymak cubugu
            # tasiriyor ve kalan sure tahminini bozuyordu.
            if "Combined k-effective" in satir:
                self._transport += 1
                self.ilerleme.setValue(self._transport)
                gecen = time.time() - self._t0
                if self._t_ilk is None:
                    self._t_ilk = gecen
                kalan = (self.ilerleme.maximum() - self._transport) * gecen / self._transport
                self.sure_etiket.setText(
                    "geçen %s  |  transport başına %.0f s (ölçülen)  |  kalan ~%s"
                    % (_sure(gecen), gecen / self._transport, _sure(kalan)))

    def _surec_hatasi(self, kod):
        # Baslatilamayan surec finished() YAYMAZ: dugmeler kilitli kalirdi.
        if self._surec is not None and kod == QtCore.QProcess.FailedToStart:
            if not self._eski_kosu():
                self.log.appendPlainText("\n# Süreç başlatılamadı: %s"
                                         % self._surec.errorString())
            self._bitti(-1, None)

    def _bitti(self, cikis_kodu, _durum):
        eski = self._eski_kosu()
        surec, self._surec = self._surec, None
        if surec is not None:
            try:
                surec.deleteLater()
            except Exception:
                pass
        self._kosu_kusagi = None
        self.d_durdur.setEnabled(False)
        self.kapi_guncelle()
        if eski:
            # Onceki projenin kosusu: sonucu bu projeye YAZILMAZ; bu projenin
            # (varsa) onceki sonucu okunur.
            self.ilerleme.setRange(0, 1)
            self.ilerleme.setValue(0)
            self.ilerleme.resetFormat()
            self._gorunum_guncelle()
            self.durum.emit("Önceki projenin tükenme koşusu bitti; sonucu bu projeye "
                            "yazılmadı (dosyalar: %s)." % self._dizin, True)
            self._onceki_yukle()
            return
        h5 = os.path.join(self._dizin or "", "depletion_results.h5")
        if cikis_kodu != 0 or not os.path.exists(h5):
            self.durum.emit("Tükenme başarısız (çıkış kodu %d)" % cikis_kodu, False)
            self.sure_etiket.setText("Başarısız — ayrıntılı çıktı aşağıda açıldı.")
            self.ayrinti.ac(True)
            self._gorunum_guncelle()
            self.sonuc_degisti.emit()
            return
        try:
            s = _tk.sonuc_oku(h5, self._kosu_spec or self.spec)
        except Exception as e:
            self.durum.emit("Sonuç okunamadı: %s" % e, False)
            self.sure_etiket.setText("Sonuç okunamadı — ayrıntılı çıktıya bakın.")
            self.log.appendPlainText("\n# Sonuç okunamadı: %s" % e)
            self.ayrinti.ac(True)
            self._gorunum_guncelle()
            self.sonuc_degisti.emit()
            return
        self._sonuc_goster(s)
        self.sure_etiket.setText("Tamamlandı: %s" % _sure(time.time() - self._t0))
        self.durum.emit("Tükenme tamamlandı", True)

    # ==================================================================
    # onceki kosu
    # ==================================================================
    def _onceki_yukle(self):
        """
        Dizinde bir sonuc varsa gosterir. Dosya degismediyse tekrar okumaz:
        sekme her tazelendiginde 3.7 MB'lik sonucu okumak gereksiz.
        """
        if self._surec is not None or not self.spec:
            return
        dizin = self._okuma_dizini()
        h5 = os.path.join(dizin, "depletion_results.h5")
        if not os.path.exists(h5):
            degisti = self.sonuc_var()
            self._onceki = self._onceki_anahtar = None
            self.onceki_etiket.setText("")
            self._grafik_bos()
            self.tablo.setRowCount(0)
            self._gorunum_guncelle()
            if degisti:
                self.sonuc_degisti.emit()
            return
        anahtar = (h5, os.path.getmtime(h5))
        if anahtar == self._onceki_anahtar:
            self._onceki_durum_guncelle()
            return
        if self._isci is not None and self._isci.isRunning():
            return                              # zaten okunuyor
        self.onceki_etiket.setStyleSheet("")
        self.onceki_etiket.setText("Önceki koşunun sonucu okunuyor…")
        self._okuma_kusagi = self._kusak
        self._isci = _OncekiIsci(self.spec, dizin, anahtar, self)
        self._isci.bitti.connect(self._onceki_geldi)
        # Pencere disi bir cikis yolunda da (or. uygulama kapanirken) calisan
        # is parcacigi yok edilmesin -- Qt bu durumda sureci dusurur.
        uyg = QtWidgets.QApplication.instance()
        if uyg is not None and not getattr(self, "_cikis_bagli", False):
            uyg.aboutToQuit.connect(self.bekle)
            self._cikis_bagli = True
        self._gorunum_guncelle()
        self._isci.start()

    def _onceki_geldi(self, anahtar, sonuc):
        if self._okuma_kusagi is not None and self._okuma_kusagi != self._kusak:
            return                              # onceki projenin okumasi: atilir
        if self._surec is not None:
            return                              # bu arada yeni kosu basladi
        if isinstance(sonuc, Exception):
            self._onceki = None
            self.onceki_etiket.setText("Önceki sonuç okunamadı: %s" % sonuc)
            self._gorunum_guncelle()
            return
        if sonuc is None:
            return
        self._onceki, self._onceki_anahtar = sonuc, anahtar
        self._sonuc_goster(sonuc["sonuc"])
        self._onceki_durum_guncelle()

    def bekle(self, ms=30000):
        """Arka plandaki okuma bitene kadar bekler (testler ve kapanis icin)."""
        if self._isci is not None:
            self._isci.wait(ms)
            QtWidgets.QApplication.processEvents()

    def _onceki_durum_guncelle(self):
        """Gosterilen sonucun SU ANKI spec'e ait olup olmadigini yazar."""
        if not self._onceki or self._surec is not None:
            return
        dizin = os.path.dirname(self._onceki["h5"])
        durum, farklar = _tk.eskime(self.spec, dizin)
        tarih = time.strftime("%d.%m.%Y %H:%M", time.localtime(self._onceki["tarih"]))
        if durum == "guncel":
            metin = "Önceki koşunun sonucu (%s) — bu modele ait." % tarih
            stil = ""
        elif durum == "eski":
            metin = ("Eski sonuç (%s): model o koşudan beri değişti (%s). "
                     "Gösterilen sayılar bu modele ait değil — yeniden koşun."
                     % (tarih, _tk.fark_metni(farklar)))
            stil = "color: #d04437; font-weight: bold;"
        else:
            metin = ("Önceki koşunun sonucu (%s). Koşunun model kaydı yok; bu "
                     "modele ait olduğu doğrulanamıyor." % tarih)
            stil = "color: #c9820a;"
        self.onceki_etiket.setText(metin)
        self.onceki_etiket.setStyleSheet(stil)

    # ==================================================================
    # sonuclar
    # ==================================================================
    def _grafik_bos(self):
        for e, y in ((self.eksen_k, "k-eff"), (self.eksen_n, "atom/b-cm")):
            e.clear(); e.grid(alpha=0.3)
            e.set_ylabel(y, fontsize=8); e.tick_params(labelsize=7)
        self.eksen_n.set_xlabel("yanma [MWd/kg]", fontsize=8)
        self.tuval.draw_idle()

    def _sonuc_goster(self, s):
        from arayuz import tema as _t
        bu, k, sk = s["yanma"], s["k"], s["k_sapma"]
        self._grafik_bos()
        self.eksen_k.errorbar(bu, k, yerr=sk, fmt="o-", ms=3, lw=1.2,
                              color=_t.renk("vurgu"), capsize=2)
        self.eksen_k.axhline(1.0, color=_t.renk("metin_soluk"), lw=0.8, ls="--")
        cizgi = False
        for ad, yog in s["yogunluk"].items():
            for n, v in yog.items():
                if any(x > 0 for x in v):
                    xs = [b for b, x in zip(bu, v) if x > 0]
                    ys = [x for x in v if x > 0]
                    self.eksen_n.plot(xs, ys, "o-", ms=2, lw=1.0,
                                      label=n if len(s["yogunluk"]) == 1 else "%s (%s)" % (n, ad))
                    cizgi = True
        if cizgi:
            self.eksen_n.set_yscale("log")
            self.eksen_n.legend(fontsize=6, ncol=2, loc="best")
        self.tuval.draw_idle()

        self.tablo.setRowCount(0)
        for z, b, kk, ss in zip(s["zaman_d"], bu, k, sk):
            r = self.tablo.rowCount()
            self.tablo.insertRow(r)
            rho = (kk - 1.0) / kk * 1e5
            for c, metin in enumerate(("%.3f" % z, "%.4f" % b,
                                       "%.5f +/- %.5f" % (kk, ss), "%+.0f" % rho)):
                self.tablo.setItem(r, c, QtWidgets.QTableWidgetItem(metin))
        self.tablo.resizeColumnsToContents()
        self._gorunum_guncelle()
        self.sonuc_degisti.emit()


def _cumle(metin):
    """uygunluk'un kucuk harfle baslayan nedenini cumleye cevirir (Turkce buyuk harf)."""
    metin = (metin or "").strip()
    if not metin:
        return ""
    ilk = {"i": "İ", "ı": "I"}.get(metin[0], metin[0].upper())
    return ilk + metin[1:] + ("" if metin.endswith(".") else ".")


def _sure(s):
    s = int(max(s, 0))
    if s < 90:
        return "%d s" % s
    if s < 5400:
        return "%d dk" % round(s / 60.0)
    return "%.1f sa" % (s / 3600.0)
