# -*- coding: utf-8 -*-
"""
maket_kabuk.py -- Dalga 2 kabugunun STATIK maketi (islev baglanmaz).

  ┌ menu ────────────────────────────────────────────────────────────────┐
  │ ust cubuk: [yeni ac kaydet | geri yinele] Model adi · tur rozeti ·   │
  │            ozet · Turu degistir…        [⌕ Komut ara  Ctrl K] [▶ Calistir]
  ├ kenar ───┬ sayfa (kaydirilir) ───────────────────────┬ onizleme ─────┤
  │ Model    │                                           │ (daraltilir)  │
  │ Hesap    │                                           │               │
  │ Sonuc    │                                           │               │
  ├──────────┴───────────────────────────────────────────┴───────────────┤
  │ dogrulama seridi: ✓ Hata yok · 1 bilgi · sonraki adim …   veri denetle│
  └──────────────────────────────────────────────────────────────────────┘
"""

from PySide6 import QtCore, QtWidgets

from arayuz import bilesenler as b
from arayuz.tasarim import tokenlar
from arayuz.tasarim.ikon import ikon_bagla
from arayuz.tasarim.maket_cizim import PARCA_RENGI, KafesCizimi
from arayuz.tasarim.maket_veri import MODEL, kenar_cubugu_kur
from cekirdek.ceviri import _

A = tokenlar.ARALIK
B = tokenlar.BOYUT
ONIZLEME_GENISLIGI = 360
ONIZLEME_DAR = 44


def dikey_ayirici():
    f = QtWidgets.QFrame()
    f.setFrameShape(QtWidgets.QFrame.VLine)
    f.setFixedHeight(20)
    return f


def renk_kutusu(renk_hex, boyut=10):
    k = QtWidgets.QLabel()
    k.setFixedSize(boyut, boyut)
    k.setStyleSheet("background: %s; border-radius: %dpx;" % (renk_hex, tokenlar.YARICAP["kucuk"] - 1))
    return k


def ikon_etiketi(ad, renk, boyut=None):
    d = QtWidgets.QToolButton()
    d.setFocusPolicy(QtCore.Qt.NoFocus)
    d.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
    d.setStyleSheet("border: none; background: transparent; padding: 0;")
    ikon_bagla(d, ad, renk, boyut or B["ikon"])
    return d


def _menu_kur(pencere):
    for ad in (_("&Dosya"), _("Dü&zen"), _("&Görünüm"), _("&Yardım")):
        pencere.menuBar().addMenu(ad)


def ust_cubuk(model=True):
    cubuk = QtWidgets.QFrame()
    cubuk.setObjectName("ustCubuk")
    cubuk.setFixedHeight(B["ust_cubuk"])
    d = QtWidgets.QHBoxLayout(cubuk)
    d.setContentsMargins(A["m"], 0, A["m"], 0)
    d.setSpacing(A["xs"])
    for ad, ipucu in (("file-plus", _("Yeni model (Ctrl+N)")), ("folder-open", _("Aç (Ctrl+O)")),
                      ("save", _("Kaydet (Ctrl+S)"))):
        d.addWidget(b.ikon_dugmesi(ad, ipucu))
    d.addWidget(dikey_ayirici())
    for ad, ipucu in (("undo-2", _("Geri al (Ctrl+Z)")), ("redo-2", _("Yinele (Ctrl+Y)"))):
        d.addWidget(b.ikon_dugmesi(ad, ipucu))
    d.addWidget(dikey_ayirici())
    d.addSpacing(A["s"])
    if model:
        ad = QtWidgets.QLabel(MODEL["ad"])
        ad.setObjectName("altBaslik")
        d.addWidget(ad)
        d.addSpacing(A["xs"])
        d.addWidget(b.Rozet(_(MODEL["tur"]), "notr"))
        ozet = QtWidgets.QLabel(_(MODEL["ozet"]))
        ozet.setObjectName("kucuk")
        d.addSpacing(A["xs"])
        d.addWidget(ozet)
        d.addSpacing(A["xs"])
        d.addWidget(b.duz_dugme(_("Türü değiştir…")))
    else:
        ad = QtWidgets.QLabel(_("Yeni model"))
        ad.setObjectName("altBaslik")
        d.addWidget(ad)
    d.addStretch(1)
    komut = QtWidgets.QPushButton(_("Komut ara…"))
    komut.setObjectName("komutAlani")
    ikon_bagla(komut, "search", "metin_soluk")
    komut.setFixedWidth(240)
    kisayol = QtWidgets.QLabel("Ctrl K")
    kisayol.setObjectName("kucuk")
    ic = QtWidgets.QHBoxLayout(komut)
    ic.setContentsMargins(0, 0, A["s"], 0)
    ic.addStretch(1)
    ic.addWidget(kisayol)
    d.addWidget(komut)
    d.addSpacing(A["s"])
    calistir = b.birincil_dugme(_("Çalıştır"), "play", _("Modeli OpenMC ile çalıştırır (F5)"))
    calistir.setEnabled(model)
    d.addWidget(calistir)
    return cubuk


def onizleme_paneli(dar=False):
    panel = QtWidgets.QFrame()
    panel.setObjectName("onizlemePaneli")
    panel.setAttribute(QtCore.Qt.WA_StyledBackground, True)
    if dar:
        panel.setFixedWidth(ONIZLEME_DAR)
        d = QtWidgets.QVBoxLayout(panel)
        d.setContentsMargins(A["xs"], A["s"], A["xs"], A["s"])
        d.addWidget(b.ikon_dugmesi("panel-right", _("Önizlemeyi aç")), 0, QtCore.Qt.AlignHCenter)
        d.addWidget(b.ikon_dugmesi("eye", _("Önizleme")), 0, QtCore.Qt.AlignHCenter)
        d.addStretch(1)
        return panel
    panel.setFixedWidth(ONIZLEME_GENISLIGI)
    d = QtWidgets.QVBoxLayout(panel)
    d.setContentsMargins(A["l"], A["m"], A["m"], A["m"])
    d.setSpacing(A["s"])
    ust = QtWidgets.QHBoxLayout()
    baslik = QtWidgets.QLabel(_("Önizleme"))
    baslik.setObjectName("altBaslik")
    ust.addWidget(baslik)
    ust.addStretch(1)
    ust.addWidget(b.ikon_dugmesi("refresh-cw", _("Yenile")))
    ust.addWidget(b.ikon_dugmesi("panel-right", _("Önizlemeyi daralt")))
    d.addLayout(ust)
    kontrol = QtWidgets.QHBoxLayout()
    kontrol.addWidget(b.SegmentSecici([("xy", "xy"), ("xz", "xz"), ("yz", "yz")], "xy"))
    kontrol.addStretch(1)
    renk = QtWidgets.QComboBox()
    renk.addItems([_("Malzemeye göre"), _("Hücreye göre")])
    kontrol.addWidget(renk)
    d.addLayout(kontrol)
    d.addWidget(KafesCizimi(), 1)
    gosterge = QtWidgets.QGridLayout()
    gosterge.setHorizontalSpacing(A["s"])
    for i, (anahtar, metin) in enumerate((("yakit_cubugu", _("Yakıt (UO2)")),
                                          ("kilavuz_boru", _("Kılavuz boru")),
                                          ("enstruman", _("Enstrüman")),
                                          ("su", _("Su (H2O + B)")))):
        gosterge.addWidget(renk_kutusu(PARCA_RENGI[anahtar]), i // 2, 2 * (i % 2))
        e = QtWidgets.QLabel(metin)
        e.setObjectName("kucuk")
        gosterge.addWidget(e, i // 2, 2 * (i % 2) + 1)
    gosterge.setColumnStretch(1, 1)
    gosterge.setColumnStretch(3, 1)
    d.addLayout(gosterge)
    olcu = QtWidgets.QLabel("%s · 289 %s" % (MODEL["olcu"], _("hücre")))
    olcu.setObjectName("mono")
    d.addWidget(olcu)
    return panel


def dogrulama_seridi(durum="basari"):
    serit = QtWidgets.QFrame()
    serit.setObjectName("dogrulamaSeridi")
    serit.setFixedHeight(B["serit"])
    d = QtWidgets.QHBoxLayout(serit)
    d.setContentsMargins(A["m"], 0, A["m"], 0)
    d.setSpacing(A["s"])
    if durum == "basari":
        d.addWidget(ikon_etiketi("circle-check", "basari", 14))
        d.addWidget(QtWidgets.QLabel(_("Doğrulama: hata yok")))
        d.addWidget(b.Rozet(_("1 bilgi"), "bilgi"))
    else:
        d.addWidget(ikon_etiketi("triangle-alert", "uyari", 14))
        d.addWidget(QtWidgets.QLabel(_("Doğrulama: 1 uyarı")))
        bulgu = QtWidgets.QLabel(_("Parçalar · “su” hücresi tanımlı ama ızgarada kullanılmıyor."))
        bulgu.setObjectName("kucuk")
        d.addWidget(bulgu)
        d.addWidget(b.baglanti_dugmesi(_("Bulguya git")))
    if durum == "basari":        # uyarida bulgu metni one cikar; ipucu yer kaplamasin
        d.addWidget(dikey_ayirici())
        ipucu = QtWidgets.QLabel(_("Sonraki adım: Kor sayfasında demetleri yerleştirin."))
        ipucu.setObjectName("kucuk")
        d.addWidget(ipucu)
    d.addStretch(1)
    d.addWidget(b.baglanti_dugmesi(_("Veri kütüphanesini denetle")))
    d.addWidget(dikey_ayirici())
    surum = QtWidgets.QLabel("OpenMC 0.16.0")
    surum.setObjectName("kucuk")
    d.addWidget(surum)
    return serit


def sayfa(baslik, aciklama, govde, eylemler=()):
    """Kaydirilan sayfa: baslik satiri + govde (QWidget ya da QLayout)."""
    alan = QtWidgets.QScrollArea()
    alan.setObjectName("sayfa")
    alan.setWidgetResizable(True)
    alan.setFrameShape(QtWidgets.QFrame.NoFrame)
    ic = QtWidgets.QWidget()
    ic.setObjectName("sayfa")
    d = QtWidgets.QVBoxLayout(ic)
    d.setContentsMargins(A["xl"], A["l"] + A["xs"], A["xl"], A["xl"])
    d.setSpacing(A["l"])
    ust = QtWidgets.QHBoxLayout()
    metin = QtWidgets.QVBoxLayout()
    metin.setSpacing(2)
    b_ = QtWidgets.QLabel(baslik)
    b_.setObjectName("baslik")
    metin.addWidget(b_)
    if aciklama:
        a = QtWidgets.QLabel(aciklama)
        a.setObjectName("ikincil")
        metin.addWidget(a)
    ust.addLayout(metin, 1)
    for e in eylemler:
        ust.addWidget(e, 0, QtCore.Qt.AlignBottom)
    d.addLayout(ust)
    if isinstance(govde, QtWidgets.QLayout):
        d.addLayout(govde, 1)
    else:
        d.addWidget(govde, 1)
    alan.setWidget(ic)
    return alan


class MaketKabuk(QtWidgets.QMainWindow):
    """secili: kenar cubugu anahtari; onizleme: "acik" | "dar" | "yok"."""

    def __init__(self, icerik, secili="malzemeler", onizleme="acik", kenar_dar=False,
                 serit="basari"):
        super().__init__()
        self.setWindowTitle(_("OpenMC arayüzü — maket"))
        _menu_kur(self)
        merkez = QtWidgets.QWidget()
        d = QtWidgets.QVBoxLayout(merkez)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(0)
        d.addWidget(ust_cubuk(model=True))
        govde = QtWidgets.QHBoxLayout()
        govde.setSpacing(0)
        self.kenar = kenar_cubugu_kur(secili)
        self.kenar.alt_ekle(b.ikon_dugmesi("moon", _("Koyu tema")))
        self.kenar.alt_ekle(b.ikon_dugmesi("settings", _("Tercihler")))
        self.kenar.daralt(kenar_dar)
        govde.addWidget(self.kenar)
        govde.addWidget(icerik, 1)
        if onizleme != "yok":
            govde.addWidget(onizleme_paneli(dar=(onizleme == "dar")))
        d.addLayout(govde, 1)
        d.addWidget(dogrulama_seridi(serit))
        self.setCentralWidget(merkez)
        from arayuz.bilesenler.bildirim import ALT_PAYI_OZELLIGI
        self.setProperty(ALT_PAYI_OZELLIGI, B["serit"])
