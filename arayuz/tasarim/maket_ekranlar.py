# -*- coding: utf-8 -*-
"""
maket_ekranlar.py -- maket sayfalari: Malzemeler (kabuk ornegi), Demet,
Hesap ayarlari, Sonuclar panosu. Baslangic ekrani maket_baslangic.py'de.
Hepsi GERCEK bilesenlerle kurulur; veri maket_veri.py'deki sabitlerdir.
"""

from PySide6 import QtCore, QtWidgets

from arayuz import bilesenler as b
from arayuz.tasarim import maket_cizim as cz
from arayuz.tasarim import tokenlar
from arayuz.tasarim.maket_kabuk import ikon_etiketi, renk_kutusu, sayfa
from arayuz.tasarim.maket_veri import (BILESIM, GUNLUK, MALZEMELER, PARCALAR, SONUC)
from cekirdek.ceviri import _

A = tokenlar.ARALIK
O = tokenlar.OKABE_ITO
_MALZEME_RENK = (O["kiremit"], None, None, O["gok"], O["mor"])


def _form(satirlar):
    f = QtWidgets.QFormLayout()
    f.setHorizontalSpacing(A["l"])
    f.setVerticalSpacing(A["s"])
    f.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
    f.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
    for etiket, w in satirlar:
        e = QtWidgets.QLabel(etiket)
        e.setObjectName("ikincil")
        f.addRow(e, w)
    return f


def _liste_satiri(renk, ad, alt, rozet=None, sag=None, secili=False):
    s = QtWidgets.QFrame()
    s.setObjectName("listeSatiri")
    s.setProperty("secili", secili)
    s.setAttribute(QtCore.Qt.WA_StyledBackground, True)
    d = QtWidgets.QHBoxLayout(s)
    d.setContentsMargins(A["s"], A["s"], A["s"], A["s"])
    d.setSpacing(A["s"])
    d.addWidget(renk_kutusu(renk, 12))
    metin = QtWidgets.QVBoxLayout()
    metin.setSpacing(0)
    a = QtWidgets.QLabel(ad)
    a.setObjectName("govdeVurgulu")
    metin.addWidget(a)
    if alt:
        k = QtWidgets.QLabel(alt)
        k.setObjectName("kucuk")
        metin.addWidget(k)
    d.addLayout(metin, 1)
    if rozet:
        d.addWidget(b.Rozet(*rozet))
    if sag:
        e = QtWidgets.QLabel(sag)
        e.setObjectName("mono")
        d.addWidget(e)
    return s


def _gri():
    from arayuz import tema
    return tema.renk("metin_soluk")


# ============================================================================
# (a) Malzemeler -- yeni kabugun icerik ornegi
# ============================================================================
def malzemeler():
    liste = b.Kart(_("Malzemeler"), eylem=b.ikon_dugmesi("plus", _("Malzeme ekle")))
    arama = QtWidgets.QLineEdit()
    arama.setPlaceholderText(_("Ara…"))
    liste.ekle(arama)
    for i, (ad, yog, sic, tur, _renk) in enumerate(MALZEMELER):
        liste.ekle(_liste_satiri(_MALZEME_RENK[i] or _gri(), ad, "%s · %s" % (yog, sic),
                                 (_(tur), "notr"), secili=(i == 0)))
    liste.setFixedWidth(320)
    ozellik = b.Kart(_("UO2 %3.20"), aciklama=_("Yakıt · 3 çubukta kullanılıyor"),
                     eylem=b.duz_dugme(_("Çoğalt"), "copy"))
    ozellik.govde.addLayout(_form((
        (_("Ad"), QtWidgets.QLineEdit("UO2 %3.20")),
        (_("Yoğunluk"), b.SayiBirim(birimler={"g/cm³": 1.0, "kg/m³": 0.001}, deger=10.257)),
        (_("Sıcaklık"), b.SayiBirim(birim="K", deger=600.0, ondalik=1, en_cok=3000)),
        (_("Zenginlik"), b.SayiBirim(birim="% U235", deger=3.2, ondalik=2, en_cok=100)))))
    bilesim = b.Kart(_("Bileşim"), aciklama=_("Atom oranı (ao); toplam 3.000000"),
                     eylem=b.SegmentSecici([("ao", "ao"), ("wo", "wo")], "ao"))
    t = QtWidgets.QTableWidget(len(BILESIM), 2)
    t.setHorizontalHeaderLabels([_("Nüklid"), _("Oran")])
    for i, (n, o) in enumerate(BILESIM):
        t.setItem(i, 0, QtWidgets.QTableWidgetItem(n))
        h = QtWidgets.QTableWidgetItem(o)
        h.setTextAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        t.setItem(i, 1, h)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setStretchLastSection(True)
    t.setAlternatingRowColors(True)
    t.setFixedHeight(40 + 32 * len(BILESIM))
    bilesim.ekle(t)
    bilesim.ekle(_satir(b.ikincil_dugme(_("Nüklid ekle"), "plus"),
                        b.duz_dugme(_("Doğal element ekle")), esnek=True))
    sag = QtWidgets.QVBoxLayout()
    sag.setSpacing(A["l"])
    sag.addWidget(ozellik)
    sag.addWidget(bilesim)
    sag.addStretch(1)
    govde = QtWidgets.QHBoxLayout()
    govde.setSpacing(A["l"])
    govde.addWidget(liste, 0, QtCore.Qt.AlignTop)
    govde.addLayout(sag, 1)
    return sayfa(_("Malzemeler"), _("Modeldeki malzemeler, yoğunluk ve bileşim."), govde,
                 [b.ikincil_dugme(_("Kütüphaneden ekle"), "download")])


def _satir(*ogeler, esnek=True):
    w = QtWidgets.QWidget()
    d = QtWidgets.QHBoxLayout(w)
    d.setContentsMargins(0, 0, 0, 0)
    d.setSpacing(A["s"])
    for o in ogeler:
        d.addWidget(o)
    if esnek:
        d.addStretch(1)
    return w


# ============================================================================
# (c) Demet
# ============================================================================
def demet():
    izgara = b.Kart(_("Izgara"), aciklama=_("Tıklayın ya da sürükleyin · sağ tık: parçayı seç"),
                    eylem=b.SegmentSecici([("boya", _("Boya")), ("doldur", _("Doldur")),
                                           ("sec", _("Seç"))], "boya",
                                          ikonlar={"boya": "paintbrush", "doldur": "grid-3x3",
                                                   "sec": "square"}))
    arac = _satir(b.Rozet(_("1/8 simetri"), "vurgu"), b.Rozet(_("3 hücre seçili"), "notr"))
    izgara.ekle(arac)
    izgara.ekle(cz.KafesCizimi(izgara=True), 1)
    # Ozet sag sutunda ayri kart degil, izgaranin altinda tek satir (dikey yer kazanir).
    ozet = _mono("21.420 × 21.420 cm · 289 %s · 264 YÇ / 24 KB / 1 EN" % _("hücre"))
    ozet.setObjectName("monoSoluk")
    alt = _satir(b.duz_dugme(_("Tümünü doldur")), b.duz_dugme(_("Temizle"), "x"))
    alt.layout().addWidget(ozet)
    izgara.ekle(alt)
    palet = b.Kart(_("Parça paleti"), eylem=b.ikon_dugmesi("plus", _("Parça ekle")))
    for i, (anahtar, kisa, ad, sayi, _r) in enumerate(PARCALAR[:3]):
        palet.ekle(_liste_satiri(cz.PARCA_RENGI[anahtar], _(ad), kisa, sag=str(sayi),
                                 secili=(i == 0)))
    ozellik = b.Kart(_("Demet"))
    boyut = _satir(QtWidgets.QSpinBox(), QtWidgets.QLabel("×"), QtWidgets.QSpinBox(), esnek=False)
    for s in boyut.findChildren(QtWidgets.QSpinBox):
        s.setValue(17)
    simetri = QtWidgets.QComboBox()
    simetri.addItems([_("1/8 (oktant)"), _("1/4"), _("Yok")])
    ozellik.govde.addLayout(_form((
        (_("Ad"), QtWidgets.QLineEdit("demet_17x17")),
        (_("Adım"), b.SayiBirim(birim="cm", deger=1.26, ondalik=4)),
        (_("Boyut"), boyut), (_("Simetri"), simetri))))
    sag = QtWidgets.QVBoxLayout()
    sag.setContentsMargins(0, 0, 0, 0)
    sag.setSpacing(A["l"])
    for k in (palet, ozellik):
        sag.addWidget(k)
    sag.addStretch(1)
    sag_w = QtWidgets.QWidget()
    sag_w.setLayout(sag)
    sag_w.setFixedWidth(330)
    govde = QtWidgets.QHBoxLayout()
    govde.setSpacing(A["l"])
    govde.addWidget(izgara, 1)
    govde.addWidget(sag_w)
    demetler = QtWidgets.QComboBox()
    demetler.addItems(["demet_17x17 · kare 17×17"])
    return sayfa(_("Demet"), _("Parçaları ızgaraya yerleştirin."), govde,
                 [demetler, b.ikincil_dugme(_("Yeni demet"), "plus")])


def _mono(metin):
    e = QtWidgets.QLabel(metin)
    e.setObjectName("mono")
    return e


# ============================================================================
# (d) Hesap ayarlari
# ============================================================================
def hesap():
    tur = b.Kart(_("Koşu türü"))
    tur.ekle(b.SegmentSecici([("ozdeger", _("Özdeğer (k-eff)")), ("sabit", _("Sabit kaynak"))],
                             "ozdeger"))
    aciklama = QtWidgets.QLabel(_("Kritiklik hesabı: k-eff ve güç dağılımı."))
    aciklama.setObjectName("kucuk")
    tur.ekle(aciklama)
    hassas = b.Kart(_("İstatistik"), aciklama=_("Önayar parçacık ve çevrim sayısını birlikte ayarlar."))
    hassas.ekle(b.SegmentSecici([("hizli", _("Hızlı")), ("dengeli", _("Dengeli")),
                                 ("hassas", _("Hassas")), ("ozel", _("Özel"))], "dengeli"))
    tahmin = _satir(ikon_etiketi("target", "metin_soluk", 14),
                    _kucuk(_("Beklenen belirsizlik ≈ ±40 pcm · süre ≈ 3 dk (6 iş parçacığı)")))
    hassas.ekle(tahmin)
    hassas.govde.addLayout(_form((
        (_("Parçacık / çevrim"), _sayi(10000, 100, 10 ** 8)),
        (_("Etkin çevrim"), _sayi(200, 1, 10 ** 5)),
        (_("Pasif çevrim"), _sayi(50, 0, 10 ** 5)))))
    kaynak = b.Kart(_("Başlangıç kaynağı"), aciklama=_("Kutu içinde düzgün; yalnız bölünebilir."))
    kaynak.govde.addLayout(_form((
        (_("Alt köşe (x, y, z)"), _uclu(-10.71)), (_("Üst köşe (x, y, z)"), _uclu(10.71)))))
    sicaklik = b.Kart(_("Sıcaklık"), eylem=b.Rozet(_("Kütüphane: 293–1200 K"), "bilgi"))
    yontem = QtWidgets.QComboBox()
    yontem.addItems([_("En yakın"), _("Ara değer (interpolation)")])
    sicaklik.govde.addLayout(_form((
        (_("Yakıt"), b.SayiBirim(birim="K", deger=900.0, ondalik=1, en_cok=3000)),
        (_("Soğutucu / zarf"), b.SayiBirim(birim="K", deger=580.0, ondalik=1, en_cok=3000)),
        (_("Yöntem"), yontem))))
    tally = b.Kart(_("Çıktılar"))
    for metin, acik in ((_("Shannon entropisi (kaynak yakınsaması)"), True),
                        (_("Pin güç dağılımı"), True), (_("Aki spektrumu (70 grup)"), False),
                        (_("Tepkime hızları"), False)):
        c = QtWidgets.QCheckBox(metin)
        c.setChecked(acik)
        tally.ekle(c)
    gelismis = b.Kart(_("Gelişmiş"), aciklama=_("Rastgele tohum, ağırlık pencereleri, çıktı ayrıntısı"),
                      eylem=b.ikon_dugmesi("chevron-down", _("Gelişmişi aç")))
    izgara = QtWidgets.QGridLayout()
    izgara.setSpacing(A["l"])
    sol = QtWidgets.QVBoxLayout()
    sag = QtWidgets.QVBoxLayout()
    for yer, kartlar in ((sol, (tur, hassas, gelismis)), (sag, (kaynak, sicaklik, tally))):
        yer.setSpacing(A["l"])
        for k in kartlar:
            yer.addWidget(k)
        yer.addStretch(1)
    izgara.addLayout(sol, 0, 0)
    izgara.addLayout(sag, 0, 1)
    izgara.setColumnStretch(0, 1)
    izgara.setColumnStretch(1, 1)
    return sayfa(_("Hesap ayarları"), _("Monte Carlo koşusunun parametreleri."), izgara,
                 [b.duz_dugme(_("Varsayılana dön"), "refresh-cw")])


def _kucuk(metin):
    e = QtWidgets.QLabel(metin)
    e.setObjectName("kucuk")
    return e


def _sayi(deger, en_az, en_cok):
    s = QtWidgets.QSpinBox()
    s.setRange(en_az, en_cok)
    s.setValue(deger)
    s.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
    s.setGroupSeparatorShown(False)
    return s


def _uclu(deger):
    kutular = [b.SayiBirim(deger=deger if i < 2 else 0.0, en_az=-1e4, en_cok=1e4, ondalik=2)
               for i in range(3)]
    birim = QtWidgets.QLabel("cm")
    birim.setObjectName("birim")
    return _satir(*kutular, birim, esnek=False)


# ============================================================================
# (e) Sonuclar panosu
# ============================================================================
def _istatistik(etiket, deger, alt=None, rozet=None, birim=None):
    k = b.Kart(dolgu="l")
    e = QtWidgets.QLabel(etiket)
    e.setObjectName("bolumEtiketi")
    k.ekle(e)
    satir = QtWidgets.QHBoxLayout()
    satir.setSpacing(A["s"])
    d = QtWidgets.QLabel(deger)
    d.setObjectName("sayiBuyuk")
    d.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
    satir.addWidget(d, 0, QtCore.Qt.AlignBaseline)
    if birim:
        u = QtWidgets.QLabel(birim)
        u.setObjectName("birim")
        satir.addWidget(u, 0, QtCore.Qt.AlignBaseline)
    satir.addStretch(1)
    k.govde.addLayout(satir)
    alt_satir = []
    if rozet:
        alt_satir.append(b.Rozet(*rozet))
    if alt:
        alt_satir.append(_kucuk(alt))
    if alt_satir:
        k.ekle(_satir(*alt_satir))
    return k


def sonuclar(cekmece_acik=False):
    s = SONUC
    ust = QtWidgets.QHBoxLayout()
    ust.setSpacing(A["l"])
    ust.addWidget(_istatistik("k-eff", "%s ± %s" % (s["keff"], s["sigma"]),
                              _("hedef ≤ %s pcm") % s["hedef_pcm"],
                              ("±%s pcm" % s["pcm"], "basari")), 2)
    ust.addWidget(_istatistik(_("Shannon entropisi"), s["entropi"], _("50. çevrimden beri durağan"),
                              (_("Yakınsadı"), "basari"), birim=_("bit")), 1)
    ust.addWidget(_istatistik(_("Süre"), s["sure"], _("%s etkin + 50 pasif çevrim") % "200",
                              birim=_("dk:sn")), 1)
    ust.addWidget(_istatistik(_("Hız"), s["hiz"], _("6 iş parçacığı"), birim=_("parçacık/s")), 1)
    grafik = b.Kart(_("Yakınsama"), aciklama=_("Çevrim başına k ve etkin ortalama ± 1σ"),
                    eylem=b.ikon_dugmesi("download", _("Grafiği kaydet")))
    grafik.ekle(cz.yakinsama_grafigi(), 1)
    entropi = b.Kart(_("Kaynak entropisi"))
    entropi.ekle(cz.entropi_grafigi(), 1)
    guc = b.Kart(_("Güç dağılımı"), aciklama=_("Pin başına göreli güç"),
                 eylem=b.SegmentSecici([("demet", _("Demet")), ("cubuk", _("Çubuk"))], "cubuk"))
    guc.ekle(cz.guc_haritasi_grafigi(), 1)
    guc.ekle(_guc_ozeti())
    orta = QtWidgets.QHBoxLayout()
    orta.setSpacing(A["l"])
    orta.addWidget(grafik, 5)
    orta.addWidget(entropi, 3)
    orta.addWidget(guc, 4)
    govde = QtWidgets.QVBoxLayout()
    govde.setSpacing(A["l"])
    govde.addLayout(ust)
    govde.addLayout(orta, 1)
    govde.addWidget(_cekmece(cekmece_acik))
    return sayfa(_("Sonuçlar"), _("Koşu tamamlandı · 28.09.2026 14:32 · statepoint.250.h5"), govde,
                 [b.ikincil_dugme(_("Klasörü aç"), "folder-open"),
                  b.ikincil_dugme(_("Rapor oluştur…"), "file-text")])


def _guc_ozeti():
    """Haritanin altinda: F_dH ve tepe konumu (veriden hesaplanir, metinle tutarli)."""
    _g, fdh, (satir, sutun) = cz.guc_verisi()
    f = QtWidgets.QLabel("F<sub>ΔH</sub> = %.3f" % fdh)
    f.setObjectName("mono")
    f.setTextFormat(QtCore.Qt.RichText)
    tepe = _kucuk(_("tepe: satır %d, sütun %d (kılavuz boru komşusu)") % (satir + 1, sutun + 1))
    return _satir(f, tepe)


def _cekmece(acik):
    k = b.Kart(_("Ayrıntılı çıktı"), aciklama=_("OpenMC günlüğü · 412 satır"),
               eylem=b.ikon_dugmesi("chevron-up" if acik else "chevron-down",
                                    _("Çekmeceyi kapat") if acik else _("Çekmeceyi aç")))
    if acik:
        m = QtWidgets.QPlainTextEdit("\n".join(GUNLUK))
        m.setProperty("mono", True)
        m.setReadOnly(True)
        m.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        k.ekle(m, 1)
        k.ekle(_satir(b.duz_dugme(_("Kopyala"), "copy"), b.duz_dugme(_("Terminalde aç"), "terminal")))
    return k
