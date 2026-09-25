# -*- coding: utf-8 -*-
"""
================================================================================
 tema.py  --  Gorunum temalari
================================================================================
 Qt'nin varsayilan paleti duz gri ve dusuk kontrastlidir; uzun sureli kullanimda
 yorucu olur. Burada iki tema tanimli:

   "acik"  -- serin beyaz zemin, koyu arduvaz metin, teal vurgu
   "koyu"  -- koyu lacivert-gri zemin, acik metin, turkuaz vurgu

 Tema yalnizca GORUNUMU degistirir; hicbir sayisal davranisi etkilemez.
 Secim QSettings'te saklanir ve bir sonraki aciliste hatirlanir.

 matplotlib de ayni palete uydurulur -- grafikler arayuzden kopuk gorunmesin.
================================================================================
"""

from PySide6 import QtCore, QtGui, QtWidgets

# ----------------------------------------------------------------------------
# Paletler
# ----------------------------------------------------------------------------
TEMALAR = {
    "acik": {
        "ad": "Açık",
        "zemin": "#f4f7fa",        # pencere zemini
        "yuzey": "#ffffff",        # giris alanlari, tablolar
        "yuzey2": "#eef2f7",       # alternatif satir, basliklar
        "metin": "#1f2933",
        "metin_soluk": "#6b7785",
        "kenar": "#d4dde7",
        "vurgu": "#0f766e",        # teal
        "vurgu_metin": "#ffffff",
        "vurgu_soluk": "#d6f0ec",
        "basari": "#1e7a44",
        "uyari": "#a8620a",
        "hata": "#b3261e",
        "bilgi": "#5b6673",
        "grafik_zemin": "#ffffff",
        "grafik_izgara": "#dde5ee",
    },
    "koyu": {
        "ad": "Koyu",
        "zemin": "#1b1f27",
        "yuzey": "#242a34",
        "yuzey2": "#2c333f",
        "metin": "#e4e9f0",
        "metin_soluk": "#95a1b1",
        "kenar": "#38404d",
        "vurgu": "#2dd4bf",
        "vurgu_metin": "#10241f",
        "vurgu_soluk": "#1d3b38",
        "basari": "#4ade80",
        "uyari": "#fbbf24",
        "hata": "#f87171",
        "bilgi": "#9aa5b4",
        "grafik_zemin": "#242a34",
        "grafik_izgara": "#38404d",
    },
}

_ETKIN = "acik"


def etkin():
    return _ETKIN


def renk(ad):
    """Etkin temadan bir rengi dondurur (arayuzun her yeri buradan okur)."""
    return TEMALAR[_ETKIN][ad]


# ----------------------------------------------------------------------------
def _palet(t):
    p = QtGui.QPalette()
    R = QtGui.QColor
    p.setColor(QtGui.QPalette.Window, R(t["zemin"]))
    p.setColor(QtGui.QPalette.WindowText, R(t["metin"]))
    p.setColor(QtGui.QPalette.Base, R(t["yuzey"]))
    p.setColor(QtGui.QPalette.AlternateBase, R(t["yuzey2"]))
    p.setColor(QtGui.QPalette.Text, R(t["metin"]))
    p.setColor(QtGui.QPalette.Button, R(t["yuzey2"]))
    p.setColor(QtGui.QPalette.ButtonText, R(t["metin"]))
    p.setColor(QtGui.QPalette.Highlight, R(t["vurgu"]))
    p.setColor(QtGui.QPalette.HighlightedText, R(t["vurgu_metin"]))
    p.setColor(QtGui.QPalette.ToolTipBase, R(t["yuzey"]))
    p.setColor(QtGui.QPalette.ToolTipText, R(t["metin"]))
    p.setColor(QtGui.QPalette.Mid, R(t["kenar"]))
    p.setColor(QtGui.QPalette.Dark, R(t["metin_soluk"]))
    p.setColor(QtGui.QPalette.PlaceholderText, R(t["metin_soluk"]))
    for grup in (QtGui.QPalette.Disabled,):
        p.setColor(grup, QtGui.QPalette.Text, R(t["metin_soluk"]))
        p.setColor(grup, QtGui.QPalette.ButtonText, R(t["metin_soluk"]))
        p.setColor(grup, QtGui.QPalette.WindowText, R(t["metin_soluk"]))
    return p


def _stil(t):
    return """
* { outline: 0; }

QWidget { color: %(metin)s; font-size: 10pt; }
QMainWindow, QDialog { background: %(zemin)s; }

/* ---------- sekmeler: altcizgi gostergeli, modern ----------
   Sekme YAZI RENGI burada VERILMEZ: stil sayfasindaki renk QTabBar::
   setTabTextColor'u ezer ve ana penceredeki durum isaretleri (hatali sekme
   kirmizi) gorunmezdi. Ana sekme cubugunun renklerini ana_pencere.py verir
   (secili: vurgu, digerleri: soluk, hata: kirmizi). */
QTabWidget::pane { border: none; background: %(zemin)s; }
QTabBar::tab {
    background: transparent;
    padding: 9px 16px; margin-right: 2px;
    border: none; border-bottom: 2px solid transparent;
}
QTabBar::tab:hover { background: %(yuzey2)s;
                     border-top-left-radius: 6px; border-top-right-radius: 6px; }
QTabBar::tab:selected {
    font-weight: 600;
    border-bottom: 2px solid %(vurgu)s;
}

/* ---------- dugmeler ---------- */
QPushButton {
    background: %(yuzey)s; border: 1px solid %(kenar)s; border-radius: 6px;
    padding: 6px 14px; color: %(metin)s;
}
QPushButton:hover   { border-color: %(vurgu)s; background: %(vurgu_soluk)s; }
QPushButton:pressed { background: %(vurgu)s; color: %(vurgu_metin)s; }
QPushButton:disabled{ color: %(metin_soluk)s; background: %(yuzey2)s;
                      border-color: %(kenar)s; }
QPushButton:checked { background: %(vurgu)s; color: %(vurgu_metin)s;
                      border-color: %(vurgu)s; }

/* ---------- girisler ---------- */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextBrowser {
    background: %(yuzey)s; border: 1px solid %(kenar)s; border-radius: 6px;
    padding: 5px 8px; selection-background-color: %(vurgu)s;
    selection-color: %(vurgu_metin)s;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
QPlainTextEdit:focus { border: 1px solid %(vurgu)s; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background: %(yuzey)s; border: 1px solid %(kenar)s;
    selection-background-color: %(vurgu)s; selection-color: %(vurgu_metin)s;
}

/* ---------- tablolar ve listeler ---------- */
QTableWidget, QTableView, QListWidget, QTreeView {
    background: %(yuzey)s; alternate-background-color: %(yuzey2)s;
    border: 1px solid %(kenar)s; border-radius: 6px;
    gridline-color: %(kenar)s;
    selection-background-color: %(vurgu)s; selection-color: %(vurgu_metin)s;
}
QHeaderView::section {
    background: %(yuzey2)s; color: %(metin_soluk)s;
    border: none; border-bottom: 1px solid %(kenar)s;
    padding: 6px 8px; font-weight: 600;
}

/* ---------- menu ve arac cubugu ---------- */
QMenuBar { background: %(zemin)s; border-bottom: 1px solid %(kenar)s; }
QMenuBar::item { padding: 6px 12px; background: transparent; border-radius: 5px; }
QMenuBar::item:selected { background: %(vurgu_soluk)s; color: %(vurgu)s; }
QMenu { background: %(yuzey)s; border: 1px solid %(kenar)s; border-radius: 8px;
        padding: 6px; }
QMenu::item { padding: 6px 22px; border-radius: 5px; }
QMenu::item:selected { background: %(vurgu)s; color: %(vurgu_metin)s; }
QMenu::separator { height: 1px; background: %(kenar)s; margin: 5px 8px; }

QToolBar { background: %(zemin)s; border: none;
           border-bottom: 1px solid %(kenar)s; padding: 2px 6px; spacing: 4px; }
QToolButton { background: transparent; border: 1px solid transparent;
              border-radius: 6px; padding: 3px 10px; }
QToolButton:hover { background: %(vurgu_soluk)s; border-color: %(kenar)s; }
QToolButton:disabled { color: %(metin_soluk)s; }

QStatusBar { background: %(zemin)s; border-top: 1px solid %(kenar)s;
             color: %(metin_soluk)s; }

/* ---------- gruplar, ayraclar ---------- */
QGroupBox {
    border: 1px solid %(kenar)s; border-radius: 8px;
    margin-top: 12px; padding-top: 10px; background: %(yuzey)s;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px;
                   color: %(metin_soluk)s; font-weight: 600; }
QFrame[frameShape="4"] { color: %(kenar)s; max-height: 1px; }

/* ---------- kaydirma cubuklari: ince, modern ---------- */
QScrollBar:vertical   { background: transparent; width: 11px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 11px; margin: 2px; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: %(kenar)s; border-radius: 5px; min-height: 28px; min-width: 28px;
}
QScrollBar::handle:hover { background: %(metin_soluk)s; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

/* ---------- diger ---------- */
QProgressBar { background: %(yuzey2)s; border: 1px solid %(kenar)s;
               border-radius: 6px; text-align: center; color: %(metin)s; }
QProgressBar::chunk { background: %(vurgu)s; border-radius: 5px; }
QCheckBox::indicator, QRadioButton::indicator { width: 15px; height: 15px; }
QCheckBox::indicator:unchecked { border: 1px solid %(kenar)s; border-radius: 4px;
                                 background: %(yuzey)s; }
QCheckBox::indicator:checked { border: 1px solid %(vurgu)s; border-radius: 4px;
                               background: %(vurgu)s; }
QSplitter::handle { background: %(kenar)s; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }
QSlider::groove:horizontal { height: 4px; background: %(kenar)s; border-radius: 2px; }
QSlider::handle:horizontal { background: %(vurgu)s; width: 14px; height: 14px;
                             margin: -5px 0; border-radius: 7px; }
QToolTip { background: %(yuzey)s; color: %(metin)s;
           border: 1px solid %(kenar)s; padding: 6px; border-radius: 6px; }

/* ---------- dalga 2: sade kabuk ---------- */
/* birincil eylem dugmesi (Bos basla, bos durum eylemi) */
QPushButton#birincil { background: %(vurgu)s; color: %(vurgu_metin)s;
                       border: 1px solid %(vurgu)s; font-weight: 600; }
QPushButton#birincil:hover { background: %(vurgu)s; border-color: %(metin)s; }
QPushButton#birincil:disabled { background: %(yuzey2)s; color: %(metin_soluk)s;
                                border-color: %(kenar)s; }
/* baslangic ekrani kartlari */
QFrame#kart { background: %(yuzey)s; border: 1px solid %(kenar)s;
              border-radius: 10px; }
QFrame#kart:hover { border-color: %(vurgu)s; }
QFrame#kart QLabel { background: transparent; border: none; }
QLabel#kartAciklama, QLabel#soluk { color: %(metin_soluk)s; }
QLabel#ekranBaslik { font-size: 20pt; font-weight: 700; }
QLabel#bolumBaslik { color: %(metin_soluk)s; font-weight: 600; }
/* model basligi (arac cubugunun altinda) */
QWidget#modelSeridi { background: %(yuzey2)s; border-bottom: 1px solid %(kenar)s; }
QWidget#modelSeridi QLabel { background: transparent; }
QWidget#modelSeridi QToolButton { border: 1px solid %(kenar)s; background: %(yuzey)s;
                                  padding: 3px 10px; }
QWidget#modelSeridi QToolButton:hover { border-color: %(vurgu)s; background: %(vurgu_soluk)s; }
/* katlanabilir Gelismis bolumu */
QToolButton#gelismisDugme { color: %(metin_soluk)s; font-weight: 600;
                            padding: 3px 4px; border: none; }
QToolButton#gelismisDugme:hover { color: %(vurgu)s; background: transparent; }
QToolButton#gelismisDugme:checked { color: %(metin)s; background: transparent; }
/* arac cubugunda CALISTIR one ciksin */
QToolButton#calistirDugmesi { color: %(vurgu)s; font-weight: 700; }
QToolButton#calistirDugmesi:disabled { color: %(metin_soluk)s; font-weight: 600; }
/* baslangic ekrani listeleri: satir araligi ve uzerine gelme */
QTreeView#tikListe { background: %(yuzey)s; }
QTreeView#tikListe::item { padding: 3px 4px; }
QTreeView#tikListe::item:hover { background: %(vurgu_soluk)s; }
/* bulgu acilir listesi (durum cubugu rozeti) */
QFrame#bulguAcilir { background: %(yuzey)s; border: 1px solid %(kenar)s;
                     border-radius: 8px; }
""" % t


def _matplotlib_uydur(t):
    """Grafikleri arayuz paletine uydurur."""
    import matplotlib
    matplotlib.rcParams.update({
        "figure.facecolor": t["grafik_zemin"],
        "axes.facecolor": t["grafik_zemin"],
        "savefig.facecolor": t["grafik_zemin"],
        "axes.edgecolor": t["kenar"],
        "axes.labelcolor": t["metin"],
        "axes.titlecolor": t["metin"],
        "text.color": t["metin"],
        "xtick.color": t["metin_soluk"],
        "ytick.color": t["metin_soluk"],
        "grid.color": t["grafik_izgara"],
        "legend.facecolor": t["yuzey"],
        "legend.edgecolor": t["kenar"],
        "font.size": 9,
    })


def uygula(app, ad=None):
    """Temayi uygular. ad verilmezse QSettings'ten okunur."""
    global _ETKIN
    ayar = QtCore.QSettings("openmc_arayuz", "arayuz")
    if ad is None:
        ad = ayar.value("tema", "acik")
    if ad not in TEMALAR:
        ad = "acik"
    _ETKIN = ad
    t = TEMALAR[ad]
    app.setStyle("Fusion")
    app.setPalette(_palet(t))
    app.setStyleSheet(_stil(t))
    _matplotlib_uydur(t)
    ayar.setValue("tema", ad)
    return ad
