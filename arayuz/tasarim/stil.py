# -*- coding: utf-8 -*-
"""
stil.py -- tasarim tokenlarindan uygulamanin TEK stil sayfasini (QSS) uretir.

    qss = stil.uret(palet)           # palet: tokenlar.palet(tema, vurgu)
    stil.durum_ayarla(kutu, "hata", True)   # dinamik ozellik + yeniden cila

DUGME TURLERI
  QPushButton                     ikincil (varsayilan): yuzey + kenar
  objectName "birincil"           birincil: vurgu zemin (mevcut kod bu adi kullanir)
  property tur="tehlikeli"        yikici eylem
  property tur="duz"              kenarsiz (ghost)
  QToolButton property tur="ikon" kare ikon dugmesi
  property segment="bas|orta|son|tek"   segment secicinin parcalari
GIRIS DURUMU
  property hata=true              kirmizi kenar (QLineEdit/QSpinBox/QComboBox)
ROZET
  QLabel property rozet="basari|uyari|hata|bilgi|notr|vurgu"
YUZEYLER
  QFrame#yuzeyKart (Kart), #kenarCubugu, #ustCubuk, #dogrulamaSeridi,
  #bildirim, #komutPaleti, #onizlemePaneli

Ok/isaret resimleri (acilir liste, sayi kutusu, onay kutusu) Lucide
ikonlarindan tema rengiyle PNG olarak gecici dizine yazilir (1x ve @2x):
QSS `image:` yalnizca dosya yolu kabul eder.
"""

import os
import tempfile

from arayuz.tasarim import tokenlar

A = tokenlar.ARALIK
R = tokenlar.YARICAP
B = tokenlar.BOYUT
T = tokenlar.TIPOGRAFI


def _resim_dizini():
    ek = "_%s" % os.getuid() if hasattr(os, "getuid") else ""
    dizin = os.path.join(tempfile.gettempdir(), "openmc_arayuz_tasarim" + ek)
    os.makedirs(dizin, exist_ok=True)
    return dizin


def _resim(ad, renk_hex, boyut):
    """Ikonu 1x ve @2x PNG olarak yazar; 1x yolunu (ileri egik cizgi) dondurur."""
    from arayuz.tasarim.ikon import piksel
    dizin = _resim_dizini()
    kok = os.path.join(dizin, "%s_%s_%d" % (ad, renk_hex.lstrip("#"), boyut))
    for olcek, ek in ((1, ""), (2, "@2x")):
        yol = kok + ek + ".png"
        if not os.path.exists(yol):
            pm = piksel(ad, renk_hex, boyut, olcek)
            if not pm.toImage().save(yol):
                raise OSError("stil resmi yazilamadi: %s" % yol)
    return (kok + ".png").replace("\\", "/")


def resimler(p):
    return {
        "ok_asagi": _resim("chevron-down", p["metin_soluk"], 12),
        "ok_yukari": _resim("chevron-up", p["metin_soluk"], 12),
        "ok_pasif_asagi": _resim("chevron-down", p["metin_pasif"], 12),
        "ok_pasif_yukari": _resim("chevron-up", p["metin_pasif"], 12),
        "onay": _resim("check", p["vurgu_metin"], 12),
    }


def _olculer():
    return {
        "a_xs": A["xs"], "a_s": A["s"], "a_m": A["m"], "a_l": A["l"], "a_xl": A["xl"],
        "r_k": R["kucuk"], "r_o": R["orta"], "r_b": R["buyuk"], "r_kart": R["kart"],
        "f_govde": T["govde"][0], "f_kucuk": T["kucuk"][0], "f_etiket": T["etiket"][0],
        "f_baslik": T["baslik"][0], "f_alt": T["altbaslik"][0],
        "f_ekran": T["ekran_basligi"][0], "f_sayi": T["sayi_buyuk"][0],
        "h_giris": B["giris_yuksekligi"], "h_dugme": B["dugme_yuksekligi"],
    }


def uret(p, aile=None, mono=None):
    """Tam QSS metni. p: tokenlar.palet(); aile/mono: yazi ailesi adlari
    (verilmezse QSS yazi ailesi belirtmez; uygulama yazisi kullanilir)."""
    d = dict(p, **resimler(p), **_olculer())
    d["aile"] = ('font-family: "%s";' % aile) if aile else ""
    d["mono"] = ('font-family: "%s";' % mono) if mono else ""
    return "\n".join(parca % d for parca in (
        _TEMEL, _DUGMELER, _GIRISLER, _LISTELER, _CUBUKLAR, _DIGER, _BILESENLER, _ESKI))


def durum_ayarla(widget, ad, deger):
    """Dinamik ozellik degistirip stili yeniden uygular (QSS [ozellik] secicileri
    ancak unpolish/polish ile yeniden degerlendirilir)."""
    widget.setProperty(ad, deger)
    st = widget.style()
    st.unpolish(widget)
    st.polish(widget)
    widget.update()


# ============================================================================
# QSS parcalari (%(ad)s yer tutuculari palet + olculerdir)
# ============================================================================
_TEMEL = """
* { outline: 0; }
QWidget { color: %(metin)s; font-size: %(f_govde)spx; %(aile)s }
QMainWindow, QDialog { background: %(zemin)s; }
QWidget#sayfa, QScrollArea#sayfa > QWidget > QWidget { background: %(zemin)s; }
QLabel { background: transparent; }
QLabel:disabled { color: %(metin_pasif)s; }
QToolTip { background: %(yuzey3)s; color: %(metin)s; border: 1px solid %(kenar_guclu)s;
           padding: %(a_xs)spx %(a_s)spx; border-radius: %(r_o)spx; }
"""

_DUGMELER = """
QPushButton {
    background: %(yuzey1)s; color: %(metin)s;
    border: 1px solid %(kenar_guclu)s; border-radius: %(r_o)spx;
    padding: 0 %(a_m)spx; min-height: %(h_dugme)spx; font-weight: 500;
}
QPushButton:hover   { background: %(yuzey2)s; }
QPushButton:pressed { background: %(yuzey3)s; }
QPushButton:focus   { border: 2px solid %(odak)s; padding: 0 %(a_m)spx; }
QPushButton:disabled{ color: %(metin_pasif)s; background: %(yuzey2)s; border-color: %(kenar)s; }
QPushButton:checked { background: %(vurgu_soluk)s; color: %(vurgu)s; border-color: %(vurgu)s; }
QPushButton::menu-indicator { image: url("%(ok_asagi)s"); subcontrol-position: right center;
                              right: %(a_s)spx; }

QPushButton#birincil { background: %(vurgu)s; color: %(vurgu_metin)s;
                       border: 1px solid %(vurgu)s; font-weight: 600; }
QPushButton#birincil:hover   { background: %(vurgu_hover)s; border-color: %(vurgu_hover)s; }
QPushButton#birincil:pressed { background: %(vurgu_basili)s; }
QPushButton#birincil:focus   { border: 2px solid %(metin)s; }
QPushButton#birincil:disabled{ background: %(yuzey3)s; color: %(metin_pasif)s;
                               border-color: %(kenar)s; }

QPushButton[tur="tehlikeli"] { color: %(hata)s; border-color: %(hata)s; background: %(yuzey1)s; }
QPushButton[tur="tehlikeli"]:hover { background: %(hata_soluk)s; }
QPushButton[tur="duz"] { background: transparent; border: 1px solid transparent; color: %(metin_ikincil)s; }
QPushButton[tur="duz"]:hover { background: %(yuzey3)s; color: %(metin)s; }
QPushButton[tur="duz"]:focus { border: 2px solid %(odak)s; }
QPushButton[tur="baglanti"] { background: transparent; border: none; color: %(vurgu)s;
                              padding: 0; min-height: 0; }
QPushButton[tur="baglanti"]:hover { text-decoration: underline; }

/* segment secici */
QPushButton[segment] { border-radius: 0; margin: 0; background: %(yuzey1)s;
                       color: %(metin_ikincil)s; font-weight: 500; padding: 0 %(a_m)spx; }
QPushButton[segment="bas"] { border-top-left-radius: %(r_o)spx; border-bottom-left-radius: %(r_o)spx; }
QPushButton[segment="son"] { border-top-right-radius: %(r_o)spx; border-bottom-right-radius: %(r_o)spx; }
QPushButton[segment="tek"] { border-radius: %(r_o)spx; }
QPushButton[segment="orta"], QPushButton[segment="son"] { border-left: none; }
QPushButton[segment]:hover { background: %(yuzey2)s; color: %(metin)s; }
QPushButton[segment]:checked { background: %(vurgu_soluk)s; color: %(vurgu)s;
                               border-color: %(vurgu)s; font-weight: 600; }
QPushButton[segment="orta"]:checked, QPushButton[segment="son"]:checked { border-left: 1px solid %(vurgu)s; }
QPushButton[segment]:focus { border: 2px solid %(odak)s; }

QToolButton { background: transparent; border: 1px solid transparent; border-radius: %(r_o)spx;
              padding: %(a_xs)spx %(a_s)spx; color: %(metin)s; }
QToolButton:hover { background: %(yuzey3)s; }
QToolButton:pressed, QToolButton:checked { background: %(vurgu_soluk)s; color: %(vurgu)s; }
QToolButton:focus { border: 2px solid %(odak)s; }
QToolButton:disabled { color: %(metin_pasif)s; }
QToolButton[tur="ikon"] { padding: %(a_xs)spx; min-width: 20px; min-height: 20px; }
QToolButton::menu-indicator { image: none; }
"""

_GIRISLER = """
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit, QTextBrowser {
    background: %(yuzey1)s; color: %(metin)s;
    border: 1px solid %(kenar_guclu)s; border-radius: %(r_o)spx;
    padding: %(a_xs)spx %(a_s)spx; min-height: 20px;
    selection-background-color: %(vurgu)s; selection-color: %(vurgu_metin)s;
}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover { border-color: %(metin_soluk)s; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
QPlainTextEdit:focus, QTextEdit:focus { border: 2px solid %(odak)s; padding: 3px 7px; }
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
    background: %(yuzey2)s; color: %(metin_pasif)s; border-color: %(kenar)s; }
QLineEdit:read-only { background: %(yuzey2)s; }
QLineEdit[hata="true"], QSpinBox[hata="true"], QDoubleSpinBox[hata="true"],
QComboBox[hata="true"] { border: 2px solid %(hata)s; padding: 3px 7px; background: %(hata_soluk)s; }
QPlainTextEdit[mono="true"], QTextBrowser[mono="true"] { %(mono)s font-size: %(f_kucuk)spx; }

QComboBox { padding-right: 26px; }
QComboBox::drop-down { subcontrol-origin: padding; subcontrol-position: center right;
                       border: none; width: 24px; }
QComboBox::down-arrow { image: url("%(ok_asagi)s"); width: 12px; height: 12px; }
QComboBox::down-arrow:disabled { image: url("%(ok_pasif_asagi)s"); }
QComboBox QAbstractItemView { background: %(yuzey1)s; border: 1px solid %(kenar_guclu)s;
    border-radius: %(r_o)spx; padding: %(a_xs)spx; outline: 0;
    selection-background-color: %(vurgu_soluk)s; selection-color: %(metin)s; }

QSpinBox, QDoubleSpinBox { padding-right: 24px; }
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border; width: 20px; border: none; background: transparent; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-position: top right;
    border-top-right-radius: %(r_o)spx; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-position: bottom right;
    border-bottom-right-radius: %(r_o)spx; }
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background: %(yuzey3)s; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: url("%(ok_yukari)s"); width: 10px; height: 10px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: url("%(ok_asagi)s"); width: 10px; height: 10px; }
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled,
QSpinBox::up-arrow:off, QDoubleSpinBox::up-arrow:off { image: url("%(ok_pasif_yukari)s"); }
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled,
QSpinBox::down-arrow:off, QDoubleSpinBox::down-arrow:off { image: url("%(ok_pasif_asagi)s"); }

QCheckBox, QRadioButton { spacing: %(a_s)spx; background: transparent; }
QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; }
QCheckBox::indicator { border: 1px solid %(kenar_guclu)s; border-radius: %(r_k)spx; background: %(yuzey1)s; }
QCheckBox::indicator:hover, QRadioButton::indicator:hover { border-color: %(vurgu)s; }
QCheckBox::indicator:checked { background: %(vurgu)s; border-color: %(vurgu)s; image: url("%(onay)s"); }
QCheckBox::indicator:disabled { background: %(yuzey2)s; border-color: %(kenar)s; }
QCheckBox:focus, QRadioButton:focus { color: %(vurgu)s; }
QRadioButton::indicator { width: 14px; height: 14px; border: 1px solid %(kenar_guclu)s;
                          border-radius: 8px; background: %(yuzey1)s; }
QRadioButton::indicator:checked { width: 6px; height: 6px; border: 5px solid %(vurgu)s;
                                  background: %(vurgu_metin)s; }
"""

_LISTELER = """
QTableWidget, QTableView, QListWidget, QListView, QTreeWidget, QTreeView {
    background: %(yuzey1)s; alternate-background-color: %(yuzey2)s;
    border: 1px solid %(kenar)s; border-radius: %(r_b)spx; gridline-color: %(kenar)s;
    selection-background-color: %(vurgu_soluk)s; selection-color: %(metin)s;
}
QTableView:focus, QListView:focus, QTreeView:focus { border-color: %(odak)s; }
QListView::item, QTreeView::item { padding: %(a_xs)spx %(a_s)spx; border: none; }
QTableView::item { padding: 0 %(a_s)spx; border: none; }
QListView::item:hover, QTreeView::item:hover { background: %(yuzey2)s; }
QListView::item:selected, QTreeView::item:selected, QTableView::item:selected {
    background: %(vurgu_soluk)s; color: %(metin)s; }
QHeaderView { background: transparent; }
QHeaderView::section {
    background: %(yuzey2)s; color: %(metin_soluk)s;
    border: none; border-bottom: 1px solid %(kenar)s; border-right: 1px solid %(kenar)s;
    padding: %(a_xs)spx %(a_s)spx; font-weight: 600; font-size: %(f_kucuk)spx;
}
QTableCornerButton::section { background: %(yuzey2)s; border: none; }
"""

_CUBUKLAR = """
QTabWidget::pane { border: none; background: %(zemin)s; }
QTabBar { background: transparent; }
QTabBar::tab { background: transparent; padding: %(a_s)spx %(a_l)spx; margin-right: 2px;
               border: none; border-bottom: 2px solid transparent; }
QTabBar::tab:hover { background: %(yuzey3)s; border-top-left-radius: %(r_o)spx;
                     border-top-right-radius: %(r_o)spx; }
QTabBar::tab:selected { font-weight: 600; border-bottom: 2px solid %(vurgu)s; }

QMenuBar { background: %(zemin)s; border-bottom: 1px solid %(kenar)s; padding: 0 %(a_xs)spx; }
QMenuBar::item { padding: %(a_xs)spx %(a_s)spx; background: transparent; border-radius: %(r_k)spx; }
QMenuBar::item:selected { background: %(yuzey3)s; }
QMenu { background: %(yuzey1)s; border: 1px solid %(kenar_guclu)s; border-radius: %(r_b)spx;
        padding: %(a_xs)spx; }
QMenu::item { padding: %(a_xs)spx %(a_xl)spx %(a_xs)spx %(a_m)spx; border-radius: %(r_k)spx; }
QMenu::item:selected { background: %(vurgu_soluk)s; color: %(metin)s; }
QMenu::item:disabled { color: %(metin_pasif)s; }
QMenu::separator { height: 1px; background: %(kenar)s; margin: %(a_xs)spx %(a_s)spx; }
QMenu::icon { padding-left: %(a_s)spx; }

QToolBar { background: %(zemin)s; border: none; border-bottom: 1px solid %(kenar)s;
           padding: 2px %(a_s)spx; spacing: 2px; }
QToolBar::separator { width: 1px; background: %(kenar)s; margin: %(a_s)spx %(a_xs)spx; }
QStatusBar { background: %(zemin)s; border-top: 1px solid %(kenar)s; color: %(metin_soluk)s; }

QScrollBar:vertical   { background: transparent; width: 10px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: %(kenar_guclu)s; border-radius: 3px; min-height: 28px; min-width: 28px; }
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover { background: %(metin_soluk)s; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QSplitter::handle { background: %(kenar)s; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }
QSplitter::handle:hover { background: %(vurgu)s; }
"""

_DIGER = """
QGroupBox { border: 1px solid %(kenar)s; border-radius: %(r_kart)spx; background: %(yuzey1)s;
            margin-top: %(a_l)spx; padding: %(a_l)spx %(a_m)spx %(a_m)spx %(a_m)spx; }
QGroupBox::title { subcontrol-origin: margin; left: %(a_m)spx; padding: 0 %(a_xs)spx;
                   color: %(metin_soluk)s; font-weight: 600; }
QProgressBar { background: %(yuzey3)s; border: none; border-radius: 3px; max-height: 6px;
               text-align: center; color: transparent; }
QProgressBar[metinli="true"] { max-height: 18px; color: %(metin)s; border-radius: %(r_k)spx; }
QProgressBar::chunk { background: %(vurgu)s; border-radius: 3px; }
QSlider::groove:horizontal { height: 4px; background: %(yuzey3)s; border-radius: 2px; }
QSlider::sub-page:horizontal { background: %(vurgu)s; border-radius: 2px; }
QSlider::handle:horizontal { background: %(yuzey1)s; border: 2px solid %(vurgu)s; width: 12px;
                             height: 12px; margin: -6px 0; border-radius: 8px; }
QFrame[frameShape="4"], QFrame[frameShape="5"] { color: %(kenar)s; }
"""

_BILESENLER = """
/* ---- Kart ---- */
QFrame#yuzeyKart { background: %(yuzey1)s; border: 1px solid %(kenar)s; border-radius: %(r_kart)spx; }
QFrame#yuzeyKart[secili="true"] { border: 1px solid %(vurgu)s; }
QFrame#yuzeyKart[tiklanir="true"]:hover { border-color: %(kenar_guclu)s; background: %(yuzey1)s; }
QLabel#kartBaslik { font-size: %(f_alt)spx; font-weight: 600; color: %(metin)s; }
QLabel#kartAlt, QLabel#ikincil { color: %(metin_ikincil)s; }
QLabel#bolumEtiketi { color: %(metin_soluk)s; font-size: %(f_etiket)spx; font-weight: 600;
                      letter-spacing: 0.6px; }
QLabel#bolumAciklama { color: %(metin_soluk)s; font-size: %(f_kucuk)spx; }
QLabel#baslikBuyuk { font-size: %(f_ekran)spx; font-weight: 600; }
QLabel#baslik { font-size: %(f_baslik)spx; font-weight: 600; }
QLabel#altBaslik { font-size: %(f_alt)spx; font-weight: 600; }
QLabel#kucuk { font-size: %(f_kucuk)spx; color: %(metin_soluk)s; }
QLabel#mono { %(mono)s font-size: %(f_kucuk)spx; }
QLabel#sayiBuyuk { %(mono)s font-size: %(f_sayi)spx; font-weight: 500; color: %(metin)s; }
QLabel#birim { color: %(metin_soluk)s; }

QLabel#govdeVurgulu { font-weight: 500; }
QFrame#listeSatiri { background: transparent; border: 1px solid transparent; border-radius: %(r_o)spx; }
QFrame#listeSatiri:hover { background: %(yuzey2)s; }
QFrame#listeSatiri[secili="true"] { background: %(vurgu_soluk)s; border-color: %(vurgu_soluk)s; }

/* ---- Rozet ---- */
QLabel[rozet] { border-radius: %(r_k)spx; padding: 1px %(a_s)spx; font-size: %(f_kucuk)spx;
                font-weight: 600; }
QLabel[rozet="basari"] { color: %(basari)s; background: %(basari_soluk)s; }
QLabel[rozet="uyari"]  { color: %(uyari)s;  background: %(uyari_soluk)s; }
QLabel[rozet="hata"]   { color: %(hata)s;   background: %(hata_soluk)s; }
QLabel[rozet="bilgi"]  { color: %(bilgi)s;  background: %(bilgi_soluk)s; }
QLabel[rozet="vurgu"]  { color: %(vurgu)s;  background: %(vurgu_soluk)s; }
QLabel[rozet="notr"]   { color: %(metin_ikincil)s; background: %(yuzey3)s; }

/* ---- Kenar cubugu ---- */
QFrame#kenarCubugu { background: %(yuzey1)s; border: none; border-right: 1px solid %(kenar)s; }
QListWidget#kenarListesi { background: transparent; border: none; padding: %(a_xs)spx; }
QListWidget#kenarListesi::item { padding: 0; margin: 1px 0; border-radius: %(r_o)spx; }
QListWidget#kenarListesi::item:hover { background: %(yuzey3)s; }
QListWidget#kenarListesi::item:selected { background: %(vurgu_soluk)s; color: %(vurgu)s; }
QListWidget#kenarListesi:focus { border: none; }

/* ---- ust cubuk, serit, paneller ---- */
QFrame#ustCubuk { background: %(yuzey1)s; border: none; border-bottom: 1px solid %(kenar)s; }
QFrame#dogrulamaSeridi { background: %(yuzey1)s; border: none; border-top: 1px solid %(kenar)s; }
QFrame#dogrulamaSeridi QLabel { font-size: %(f_kucuk)spx; }
QFrame#onizlemePaneli { background: %(yuzey1)s; border: none; border-left: 1px solid %(kenar)s; }
QFrame#cekmece { background: %(yuzey1)s; border: 1px solid %(kenar)s; border-radius: %(r_kart)spx; }
QPushButton#komutAlani { background: %(yuzey2)s; border: 1px solid %(kenar)s; color: %(metin_soluk)s;
                         text-align: left; padding: 0 %(a_s)spx; font-weight: 400; }
QPushButton#komutAlani:hover { border-color: %(kenar_guclu)s; color: %(metin_ikincil)s; }

/* ---- Bildirim ---- */
QFrame#bildirim { background: %(yuzey1)s; border: 1px solid %(kenar_guclu)s;
                  border-radius: %(r_b)spx; }
QFrame#bildirim[tur="basari"] { border-left: 3px solid %(basari)s; }
QFrame#bildirim[tur="uyari"]  { border-left: 3px solid %(uyari)s; }
QFrame#bildirim[tur="hata"]   { border-left: 3px solid %(hata)s; }
QFrame#bildirim[tur="bilgi"]  { border-left: 3px solid %(bilgi)s; }

/* ---- Komut paleti ---- */
QFrame#komutPaleti { background: %(yuzey1)s; border: 1px solid %(kenar_guclu)s;
                     border-radius: %(r_kart)spx; }
QFrame#komutPaleti QLineEdit { border: none; border-bottom: 1px solid %(kenar)s; border-radius: 0;
    background: transparent; padding: %(a_m)spx %(a_l)spx; font-size: %(f_alt)spx; }
QFrame#komutPaleti QListWidget { border: none; background: transparent; padding: %(a_xs)spx; }
QFrame#komutPaleti QListWidget::item { padding: %(a_s)spx %(a_m)spx; border-radius: %(r_o)spx; }
QFrame#komutPaleti QListWidget::item:selected { background: %(vurgu_soluk)s; color: %(metin)s; }

/* ---- Bos durum ---- */
QLabel#bosBaslik { font-size: %(f_alt)spx; font-weight: 600; }
QLabel#bosAciklama { color: %(metin_soluk)s; }
"""

# Mevcut (Dalga 0) kodun objectName'leri: Dalga 2'de yeni bilesenlere gecilene
# kadar ayni gorunum anlamlarini korur.
_ESKI = """
QFrame#kart { background: %(yuzey1)s; border: 1px solid %(kenar)s; border-radius: %(r_kart)spx; }
QFrame#kart:hover { border-color: %(kenar_guclu)s; }
QFrame#kart QLabel { background: transparent; border: none; }
QLabel#kartAciklama, QLabel#soluk { color: %(metin_soluk)s; }
QLabel#ekranBaslik { font-size: %(f_ekran)spx; font-weight: 600; }
QLabel#bolumBaslik { color: %(metin_soluk)s; font-weight: 600; }
QWidget#modelSeridi { background: %(yuzey1)s; border-bottom: 1px solid %(kenar)s; }
QWidget#modelSeridi QLabel { background: transparent; }
QWidget#modelSeridi QToolButton { border: 1px solid %(kenar_guclu)s; background: %(yuzey1)s;
                                  padding: 2px %(a_s)spx; }
QWidget#modelSeridi QToolButton:hover { background: %(yuzey2)s; }
QToolButton#gelismisDugme { color: %(metin_soluk)s; font-weight: 600; padding: 2px %(a_xs)spx;
                            border: none; }
QToolButton#gelismisDugme:hover { color: %(vurgu)s; background: transparent; }
QToolButton#gelismisDugme:checked { color: %(metin)s; background: transparent; }
QToolButton#calistirDugmesi { color: %(vurgu)s; font-weight: 600; }
QToolButton#calistirDugmesi:disabled { color: %(metin_pasif)s; }
QTreeView#tikListe { background: %(yuzey1)s; }
QTreeView#tikListe::item { padding: 3px %(a_xs)spx; }
QTreeView#tikListe::item:hover { background: %(yuzey2)s; }
QFrame#bulguAcilir { background: %(yuzey1)s; border: 1px solid %(kenar_guclu)s;
                     border-radius: %(r_b)spx; }
"""
