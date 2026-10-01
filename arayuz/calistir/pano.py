# -*- coding: utf-8 -*-
"""
pano.py -- Sonuc panosu (maket: sonuclar_acik/koyu_*.png).

    SonucPanosu
      k-eff ± sigma (+ pcm rozeti ve hedef belirsizlik)
      Shannon entropisi (yakinsama rozeti; kapaliysa BOS DURUM metni)
      Sure (dk:sn) ve Hiz (parcacik/s)  -- gunluk_ozeti'nden
      dogrulama satiri: kosu oncesi dogrulama kapisinin (dogrula.kapi) sonucu

Kartlar bilesenler.Kart uzerine kurulur; renk, aralik ve yazi boyutu yalnizca
tasarim tokenlarindan gelir. Deger yazma islevleri spec'i ve sonucu DEGISTIRMEZ.
"""

from PySide6 import QtCore, QtWidgets

from arayuz import bilesenler as b
from arayuz.calistir import gunluk_ozeti
from arayuz.tasarim import tokenlar
from arayuz.tasarim.ikon import ikon_bagla
from arayuz.ayar.sabitler import belirsizlik_pcm
from cekirdek import kosucu, uygunluk
from cekirdek.ceviri import _, _n
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

A = tokenlar.ARALIK
BOS = "—"


class IstatistikKarti(b.Kart):
    """Kucuk etiket + buyuk sayi (+ birim) + rozet + alt aciklama."""

    def __init__(self, etiket, birim=None, parent=None):
        super().__init__(parent=parent)
        self.etiket = QtWidgets.QLabel(etiket)
        self.etiket.setObjectName("bolumEtiketi")
        self.ekle(self.etiket)
        satir = QtWidgets.QHBoxLayout()
        satir.setSpacing(A["s"])
        self.deger = QtWidgets.QLabel(BOS)
        self.deger.setObjectName("sayiBuyuk")
        self.deger.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        satir.addWidget(self.deger, 0, QtCore.Qt.AlignBaseline)
        self.birim = QtWidgets.QLabel(birim or "")
        self.birim.setObjectName("birim")
        self.birim.setVisible(bool(birim))
        satir.addWidget(self.birim, 0, QtCore.Qt.AlignBaseline)
        satir.addStretch(1)
        self.govde.addLayout(satir)
        self.rozet = b.Rozet("", "notr")
        self.rozet.setVisible(False)
        self.alt = QtWidgets.QLabel("")
        self.alt.setObjectName("kucuk")
        self.alt.setWordWrap(True)
        alt_satir = QtWidgets.QHBoxLayout()
        alt_satir.setSpacing(A["s"])
        alt_satir.addWidget(self.rozet, 0)
        alt_satir.addWidget(self.alt, 1)
        self.govde.addLayout(alt_satir)
        self.setAccessibleName(etiket)

    def yaz(self, deger=BOS, alt="", rozet=None):
        """rozet: (metin, tur) ya da None (gizlenir). Ipucu temizlenir."""
        self.setToolTip("")
        self.deger.setText(deger)
        self.alt.setText(alt or "")
        self.alt.setVisible(bool(alt))
        if rozet:
            self.rozet.tur_ayarla(rozet[1])
            self.rozet.setText(rozet[0])
        self.rozet.setVisible(bool(rozet))

    def etiket_ayarla(self, metin):
        self.etiket.setText(metin)
        self.setAccessibleName(metin)


class SonucPanosu(QtWidgets.QWidget):
    """Dort istatistik karti + dogrulama satiri."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.k = IstatistikKarti("k-eff")
        self.entropi = IstatistikKarti(_("Shannon entropisi"), "bit")
        self.sure = IstatistikKarti(_("Süre"), _("dk:sn"))
        self.hiz = IstatistikKarti(_("Hız"), _("parçacık/s"))
        kartlar = QtWidgets.QHBoxLayout()
        kartlar.setContentsMargins(0, 0, 0, 0)
        kartlar.setSpacing(A["l"])
        for kart, esnek in ((self.k, 2), (self.entropi, 1), (self.sure, 1), (self.hiz, 1)):
            kartlar.addWidget(kart, esnek)
        self.dogrulama_ikonu = QtWidgets.QToolButton()
        self.dogrulama_ikonu.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.dogrulama_ikonu.setFocusPolicy(QtCore.Qt.NoFocus)
        self.dogrulama_ikonu.setAutoRaise(True)
        self.dogrulama_rozeti = b.Rozet(_("Denetlenmedi"), "notr")
        self.dogrulama_metni = QtWidgets.QLabel("")
        self.dogrulama_metni.setObjectName("kucuk")
        self.dogrulama_metni.setWordWrap(True)
        satir = QtWidgets.QHBoxLayout()
        satir.setContentsMargins(0, 0, 0, 0)
        satir.setSpacing(A["s"])
        satir.addWidget(QtWidgets.QLabel(_("Doğrulama:")))
        satir.addWidget(self.dogrulama_ikonu)
        satir.addWidget(self.dogrulama_rozeti)
        satir.addWidget(self.dogrulama_metni, 1)
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.setSpacing(A["s"])
        duzen.addLayout(kartlar)
        duzen.addLayout(satir)
        self.dogrulama_ayarla(_("Denetlenmedi"), "notr",
                              _("Çalıştır'a basınca koşu öncesi doğrulama yapılır."))
        self.temizle()

    # ------------------------------------------------------------------
    def temizle(self):
        """Sonuc alanlarini bosaltir (dogrulama satirina dokunmaz)."""
        for kart in (self.k, self.entropi, self.sure, self.hiz):
            kart.yaz()
        self.k.etiket_ayarla("k-eff")

    def dogrulama_ayarla(self, rozet_metni, tur, aciklama=""):
        """Kosu oncesi dogrulama kapisinin sonucu (tur: rozet turu)."""
        self.dogrulama_rozeti.tur_ayarla(tur)
        self.dogrulama_rozeti.setText(rozet_metni)
        self.dogrulama_metni.setText(aciklama)
        self.dogrulama_metni.setVisible(bool(aciklama))
        ikon = {"basari": "circle-check", "uyari": "triangle-alert",
                "hata": "circle-x"}.get(tur, "info")
        ikon_bagla(self.dogrulama_ikonu, ikon, tur if tur != "notr" else "metin_soluk",
                   tokenlar.BOYUT["ikon"])

    # ------------------------------------------------------------------
    def sonuc_yaz(self, sonuc, spec=None, zaman=None):
        """kosucu.sonuc_oku() ciktisini kartlara yazar; hicbirini degistirmez."""
        sonuc = sonuc or {}
        self._k_yaz(sonuc, spec or {})
        self._entropi_yaz(sonuc)
        self._zaman_yaz(sonuc, spec or {}, zaman or {})

    def _k_yaz(self, sonuc, spec):
        keff = sonuc.get("keff")
        sonsuz = False
        try:
            sonsuz = bool(spec) and uygunluk.sonsuz_ortam(spec)
        except Exception:
            _log.warning("sonsuz ortam denetlenemedi; k-eff etiketi kullanılıyor",
                         exc_info=True)
        self.k.etiket_ayarla("k∞" if sonsuz else "k-eff")
        if not keff:
            self.k.yaz(BOS, _("Sabit kaynak — k-eff tanımsız; sonuç tally'lerdir."))
            return
        pcm = keff[1] * 1e5
        hedef = self._hedef_pcm(spec)
        iyi = hedef is None or pcm <= hedef
        self.k.yaz("%.5f ± %.5f" % keff,
                   (_("hedef ≈ ±%d pcm") % round(hedef)) if hedef else "",
                   ("±%d pcm" % round(pcm), "basari" if iyi else "uyari"))

    @staticmethod
    def _hedef_pcm(spec):
        """Hesap ayarlarindan beklenen k-eff belirsizligi [pcm] (yoksa None)."""
        a = (spec or {}).get("ayarlar") or {}
        if (a.get("mod") or "eigenvalue") != "eigenvalue":
            return None
        return belirsizlik_pcm(int(a.get("parcacik") or 0), int(a.get("cevrim") or 0),
                               int(a.get("pasif") or 0))

    def _entropi_yaz(self, sonuc):
        entropi = sonuc.get("entropi") or []
        if not entropi:
            self.entropi.yaz(BOS, sonuc.get("entropi_hata")
                             or _("Shannon entropisi kapalı — kaynak yakınsaması "
                                  "doğrulanamıyor"))
            return
        yakinsadi, mesaj = kosucu.entropi_yakinsama(entropi, sonuc.get("pasif") or 0)
        rozet = {True: (_("Yakınsadı"), "basari"), False: (_("Yakınsamadı"), "uyari"),
                 None: (_("Belirsiz"), "notr")}[yakinsadi]
        # Uzun degerlendirme metni ipucunda; kartta kisa ozet (maket).
        self.entropi.yaz("%.3f" % entropi[-1],
                         _n("%d çevrimin sonuncusu", "%d çevrimin sonuncusu", len(entropi))
                         % len(entropi), rozet)
        self.entropi.setToolTip(mesaj)

    def _zaman_yaz(self, sonuc, spec, zaman):
        cevrim = int(sonuc.get("cevrim") or 0)
        pasif = int(sonuc.get("pasif") or 0)
        sure = zaman.get("sure_s")
        self.sure.yaz(gunluk_ozeti.sure_metni(sure),
                      _n("%d etkin + %d pasif çevrim", "%d etkin + %d pasif çevrim", pasif)
                      % (max(cevrim - pasif, 0), pasif))
        hiz = zaman.get("hiz")
        if hiz is None and sure and sonuc.get("parcacik"):
            hiz = float(sonuc["parcacik"]) * cevrim / sure
        n = int(((spec or {}).get("calistirma") or {}).get("is_parcacigi") or 0)
        self.hiz.yaz(gunluk_ozeti.hiz_metni(hiz),
                     (_n("%d iş parçacığı", "%d iş parçacığı", n) % n) if n else "")
