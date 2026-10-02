# -*- coding: utf-8 -*-
"""
================================================================================
 guc_harita_tablo.py  --  Pin gucu tablosu (sirala, filtrele, sec, disa aktar)
================================================================================
 cekirdek/guc_tablo.pin_tablosu satirlarini gosterir; YENI hesap yapmaz
 (tablo = harita). Guc haritasi (arayuz/guc_harita.py) ve tukenme sonucu
 (arayuz/tukenme_pin_gucu.py) ayni widget'i kullanir.

   t = PinTablosu()
   t.ayarla(tablo, dagilim, spec)    # yeni satirlar (katlama secenegi yeniden sinanir)
   t.dilim_ayarla(k | None)          # 3B: "dilim" sutunlari k. dilimi gosterir
   t.sec(anahtar)                    # satiri secer, pin_secildi yayar
   t.pin_secildi                     # Signal(anahtar)
   t.kaydet_yola(yol)                # .csv ya da .xlsx (openpyxl varsa)

 Siralama ham sayiyla (UserRole), gorunen metinle degil: QSortFilterProxyModel
 sortRole = UserRole. Suzgec gorunen metinde (demet, konum, tur) arar.
 Ondalik ayirici dosyada NOKTA (guc_tablo.satirlar_csv); ekranda da nokta.
================================================================================
"""

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import guc_tablo
from cekirdek.ceviri import N_, _
from cekirdek.gunluk import kaydedici
from arayuz import tema

_log = kaydedici(__name__)

TABLO_EN_AZ = 180         # px
_ANAHTAR_ROLU = QtCore.Qt.UserRole + 1

# (kimlik, baslik, bicim | None) -- bicim None: metin
_SUTUNLAR = (
    ("demet", N_("Demet"), None),
    ("konum", N_("Konum"), None),
    ("x", "x [cm]", "%.3f"),
    ("y", "y [cm]", "%.3f"),
    ("tur", N_("Tür"), None),
    ("bagil", N_("Bağıl güç"), "%.4f"),
    ("sigma", "σ", "%.4f"),
    ("W", N_("Güç [W]"), "%.5g"),
    ("q", "q′ [W/cm]", "%.2f"),
    ("tepe_q", N_("En yüksek q′ [W/cm]"), "%.2f"),
    ("dilim_bagil", N_("Dilim bağıl"), "%.4f"),
    ("dilim_q", N_("Dilim q′ [W/cm]"), "%.2f"),
    ("uye", N_("Katlanan"), "%d"),
    ("asimetri", N_("Asimetri"), "%.2e"),
)


_DILIM_BASLIKLARI = {"dilim_bagil": N_("Dilim %d bağıl"),
                     "dilim_q": N_("Dilim %d q′ [W/cm]")}


def _gorunur_sutunlar(satirlar, katli):
    """Bu tabloda anlamli sutunlar (bos sutun gosterilmez)."""
    if not satirlar:
        return [s for s in _SUTUNLAR if s[0] in ("konum", "bagil", "sigma")]
    ilk = satirlar[0]
    uc_boyut = bool(ilk.get("dilimler"))
    mutlak = ilk.get("W") is not None
    tek = {
        "demet": any(r["demet"] for r in satirlar),
        "tur": any(r["tur"] for r in satirlar),
        "W": mutlak, "q": mutlak and ilk.get("q") is not None,
        "tepe_q": mutlak and uc_boyut and not katli,
        "dilim_bagil": uc_boyut and not katli, "dilim_q": uc_boyut and mutlak and not katli,
        "uye": katli, "asimetri": katli,
    }
    return [s for s in _SUTUNLAR if tek.get(s[0], True)]


class PinModeli(QtCore.QAbstractTableModel):
    """Pin satirlari (guc_tablo sozlukleri) icin salt okunur model."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._satirlar, self._sutunlar, self._dilim = [], [], None
        self.iki_boyut = False        # 2B tukenme: guc 1 cm yukseklik basina

    def ayarla(self, satirlar, katli=False):
        self.beginResetModel()
        self._satirlar = list(satirlar)
        self._sutunlar = _gorunur_sutunlar(self._satirlar, katli)
        self.endResetModel()

    def dilim_ayarla(self, k):
        self._dilim = k
        if self._sutunlar:
            self.headerDataChanged.emit(QtCore.Qt.Horizontal, 0, len(self._sutunlar) - 1)
        if self._satirlar:
            self.dataChanged.emit(self.index(0, 0),
                                  self.index(len(self._satirlar) - 1, len(self._sutunlar) - 1))

    def sutunlar(self):
        return [s[0] for s in self._sutunlar]

    def satir(self, i):
        return self._satirlar[i]

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self._satirlar)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self._sutunlar)

    def headerData(self, bolum, yon, rol=QtCore.Qt.DisplayRole):
        if rol != QtCore.Qt.DisplayRole or yon != QtCore.Qt.Horizontal:
            return None
        kimlik = self._sutunlar[bolum][0]
        if kimlik in _DILIM_BASLIKLARI and self._dilim is not None:
            return _(_DILIM_BASLIKLARI[kimlik]) % (self._dilim + 1)
        if kimlik == "W" and self.iki_boyut:
            return _("Güç [W/cm yükseklik]")
        return _(self._sutunlar[bolum][1])

    def _ham(self, r, kimlik):
        if kimlik in ("dilim_bagil", "dilim_q"):
            d = r["dilimler"]
            k = self._dilim
            if k is None or not (0 <= k < len(d)):
                return None
            return d[k]["bagil" if kimlik == "dilim_bagil" else "q"]
        if kimlik == "uye":
            return len(r.get("uyeler") or ())
        return r.get(kimlik)

    def data(self, indeks, rol=QtCore.Qt.DisplayRole):
        if not indeks.isValid():
            return None
        r = self._satirlar[indeks.row()]
        kimlik, _b, bicim = self._sutunlar[indeks.column()]
        deger = self._ham(r, kimlik)
        if rol == QtCore.Qt.UserRole:
            return deger
        if rol == _ANAHTAR_ROLU:
            return indeks.row()
        if rol == QtCore.Qt.DisplayRole:
            if deger is None:
                return "—"
            return (bicim % deger) if bicim else str(deger)
        if rol == QtCore.Qt.BackgroundRole and r.get("sicak"):
            return QtGui.QColor(tema.renk("uyari_soluk"))
        if rol == QtCore.Qt.ForegroundRole and r.get("kesik"):
            return QtGui.QColor(tema.renk("metin_pasif"))
        if rol == QtCore.Qt.FontRole and (r.get("sicak") or r.get("tepe_yakini")):
            f = QtGui.QFont()
            f.setBold(bool(r.get("sicak")))
            f.setItalic(bool(r.get("tepe_yakini")) and not r.get("sicak"))
            return f
        if rol == QtCore.Qt.ToolTipRole:
            return self._ipucu(r)
        if rol == QtCore.Qt.TextAlignmentRole and bicim:
            return int(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        return None

    @staticmethod
    def _ipucu(r):
        notlar = []
        if r.get("sicak"):
            notlar.append(_("en sıcak çubuk (F_ΔH)"))
        if r.get("tepe_yakini") and not r.get("sicak"):
            notlar.append(_("tepeden istatistik olarak ayırt edilemez (birleşik 2σ içinde)"))
        if r.get("kesik"):
            notlar.append(_("kesik çubuk — F_ΔH ve F_q dışında"))
        return "; ".join(notlar) or None


class PinTablosu(QtWidgets.QWidget):
    """Pin gucu tablosu: suzgec, ceyrek katlama, ayrinti satiri, disa aktarma."""

    pin_secildi = QtCore.Signal(object)

    def __init__(self, parent=None, dosya_adi="pin_gucu"):
        super().__init__(parent)
        self._tablo, self._katli, self._dagilim, self._spec = [], None, None, None
        self._dosya_adi = dosya_adi
        self._model = PinModeli(self)
        self._vekil = QtCore.QSortFilterProxyModel(self)
        self._vekil.setSourceModel(self._model)
        self._vekil.setSortRole(QtCore.Qt.UserRole)
        self._vekil.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self._vekil.setFilterKeyColumn(-1)
        self._kur()

    def _kur(self):
        self.suzgec = QtWidgets.QLineEdit()
        self.suzgec.setPlaceholderText(_("Süz: demet, konum ya da tür…"))
        self.suzgec.setClearButtonEnabled(True)
        self.suzgec.textChanged.connect(self._vekil.setFilterFixedString)
        self.katla = QtWidgets.QCheckBox(_("Çeyrek katla"))
        self.katla.toggled.connect(self._katla_degisti)
        self.d_kaydet = QtWidgets.QPushButton(_("Tabloyu kaydet…"))
        self.d_kaydet.setToolTip(_("CSV (ondalık nokta); openpyxl kuruluysa Excel de"))
        self.d_kaydet.clicked.connect(self._kaydet_sor)
        self.gorunum = QtWidgets.QTableView()
        self.gorunum.setModel(self._vekil)
        self.gorunum.setSortingEnabled(True)
        self.gorunum.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.gorunum.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.gorunum.verticalHeader().setVisible(False)
        self.gorunum.horizontalHeader().setStretchLastSection(True)
        self.gorunum.setMinimumHeight(TABLO_EN_AZ)
        self.gorunum.setAccessibleName(_("Pin gücü tablosu"))
        self.gorunum.selectionModel().selectionChanged.connect(self._secim_degisti)
        self.ayrinti = QtWidgets.QLabel(_("Haritada bir çubuğa tıklayın ya da tablodan seçin."))
        self.ayrinti.setObjectName("soluk")
        self.ayrinti.setWordWrap(True)
        self.ayrinti.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.notlar = QtWidgets.QLabel("")
        self.notlar.setObjectName("soluk")
        self.notlar.setWordWrap(True)
        self.notlar.setVisible(False)
        self._not_metinleri, self._katla_notu = [], ""
        ust = QtWidgets.QHBoxLayout()
        ust.setContentsMargins(0, 0, 0, 0)
        ust.addWidget(self.suzgec, 1)
        ust.addWidget(self.katla)
        ust.addWidget(self.d_kaydet)
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.addLayout(ust)
        duzen.addWidget(self.ayrinti)
        duzen.addWidget(self.notlar)
        duzen.addWidget(self.gorunum, 1)

    # ------------------------------------------------------------------
    def ayarla(self, tablo, dagilim=None, spec=None, notlar=(), iki_boyut=False):
        """Yeni pin satirlari. Ceyrek katlama yalniz simetri dogrulanirsa etkin.
        notlar: tablonun altinda gosterilecek yorum notlari (guc_tablo.yorum_notlari);
        iki_boyut: 2B tukenme (guc 1 cm yukseklik basina)."""
        self._tablo, self._dagilim, self._spec = list(tablo or []), dagilim, spec
        self._model.iki_boyut = self._iki_boyut = bool(iki_boyut)
        self._not_metinleri = list(notlar or ())
        self._katli, neden = (None, _("güç dağılımı yok"))
        if self._tablo and dagilim:
            try:
                self._katli, neden = guc_tablo.ceyrek_katla(self._tablo, dagilim, spec)
            except Exception as e:
                _log.exception("çeyrek simetri denetlenemedi")
                self._katli, neden = None, str(e)
        eski = self.katla.blockSignals(True)
        try:
            self.katla.setChecked(False)
            self.katla.setEnabled(self._katli is not None)
        finally:
            self.katla.blockSignals(eski)
        self.katla.setToolTip(
            _("Simetri doğrulandı: dört ayna görüntüsünün ortalaması (gürültü azalır)")
            if self._katli is not None else _("Çeyrek katlama yapılamaz: %s") % neden)
        self._katla_notu = neden if self._katli is not None else ""
        self._notlari_yaz()
        self._model.ayarla(self._tablo)
        self._dilim_sutunlari()
        self.gorunum.resizeColumnsToContents()
        self.d_kaydet.setEnabled(bool(self._tablo))

    def _katla_degisti(self, acik):
        self._model.ayarla(self._katli if (acik and self._katli) else self._tablo,
                           katli=bool(acik and self._katli))
        self._notlari_yaz()
        self._dilim_sutunlari()
        self.gorunum.resizeColumnsToContents()

    def _notlari_yaz(self):
        metinler = list(self._not_metinleri)
        if self.katla.isChecked() and self._katla_notu:
            metinler.append(self._katla_notu)
        self.notlar.setText("<br>".join(metinler))
        self.notlar.setVisible(bool(metinler))

    def dilim_ayarla(self, k):
        """3B: dilim sutunlari k. dilimi (0 tabanli) gosterir; None: sutunlar gizli."""
        self._model.dilim_ayarla(k)
        self._dilim_sutunlari()

    def _dilim_sutunlari(self):
        """Dilim secilmemisse dilim sutunlari gizlenir (bos "—" sutunu gosterilmez)."""
        for kimlik in _DILIM_BASLIKLARI:
            no = self.sutun_no(kimlik)
            if no is not None:
                self.gorunum.setColumnHidden(no, self._model._dilim is None)

    def satirlar(self):
        """Gosterilen satirlar (katli ya da tam)."""
        return list(self._model._satirlar)

    def sutun_no(self, kimlik):
        s = self._model.sutunlar()
        return s.index(kimlik) if kimlik in s else None

    def satir_anahtari(self, vekil_satir):
        kaynak = self._vekil.mapToSource(self._vekil.index(vekil_satir, 0))
        return self._model.satir(kaynak.row())["anahtar"]

    def _vekil_satiri(self, anahtar):
        for i in range(self._model.rowCount()):
            r = self._model.satir(i)
            if r["anahtar"] == anahtar or anahtar in (r.get("uyeler") or ()):
                v = self._vekil.mapFromSource(self._model.index(i, 0))
                return v.row() if v.isValid() else None
        return None

    def sicak_satir(self):
        for i in range(self._vekil.rowCount()):
            kaynak = self._vekil.mapToSource(self._vekil.index(i, 0))
            if self._model.satir(kaynak.row()).get("sicak"):
                return i
        return None

    def secili_anahtar(self):
        satirlar = self.gorunum.selectionModel().selectedRows()
        return self.satir_anahtari(satirlar[0].row()) if satirlar else None

    def sec(self, anahtar):
        """Anahtarin satirini secer (suzgecte gizliyse suzgec temizlenir)."""
        satir = self._vekil_satiri(anahtar)
        if satir is None and self.suzgec.text():
            self.suzgec.clear()
            satir = self._vekil_satiri(anahtar)
        if satir is None:
            return False
        self.gorunum.selectRow(satir)
        self.gorunum.scrollTo(self._vekil.index(satir, 0))
        return True

    def _secim_degisti(self, *_a):
        a = self.secili_anahtar()
        if a is None:
            return
        kaynak = self._vekil.mapToSource(self.gorunum.selectionModel().selectedRows()[0])
        self.ayrinti.setText(ayrinti_metni(self._model.satir(kaynak.row()), self._model._dilim))
        self.pin_secildi.emit(a)

    # ------------------------------------------------------------------
    def dosya_suzgeci(self):
        suzgecler = [_("CSV dosyası (*.csv)")]
        if guc_tablo.excel_var():
            suzgecler.append(_("Excel çalışma kitabı (*.xlsx)"))
        return ";;".join(suzgecler)

    def kaydet_yola(self, yol):
        """Gosterilen tabloyu (katli ya da tam) yaza; uzanti bicimi secer."""
        return guc_tablo.dosyaya_yaz(yol, guc_tablo.satirlar(self.satirlar(),
                                                             getattr(self, "_iki_boyut", False)))

    def _kaydet_sor(self):
        yol = dosya_sor(self, _("Pin gücü tablosunu kaydet"), self._dosya_adi, self.dosya_suzgeci())
        if not yol:
            return
        try:
            self.kaydet_yola(yol)
        except (OSError, ImportError) as e:
            _log.exception("pin tablosu yazılamadı: %s", yol)
            QtWidgets.QMessageBox.warning(self, _("Tablo yazılamadı"), str(e))


def _uzanti(suzgec_metni):
    return "xlsx" if "xlsx" in (suzgec_metni or "") else "csv"


def dosya_sor(ebeveyn, baslik, ad, suzgec):
    """Kayit yolu ya da None. Uzanti secili suzgecten (setDefaultSuffix): ad uzantisiz
    yazilirsa eklenir ve uzerine yazma onayi o SON ad icin sorulur (Qt). Yazim bicimi
    dosya uzantisina gore secilir (guc_tablo.dosyaya_yaz)."""
    dlg = QtWidgets.QFileDialog(ebeveyn, baslik)
    dlg.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
    dlg.setNameFilters(suzgec.split(";;"))
    dlg.setDefaultSuffix("csv")
    dlg.selectFile(ad + ".csv")
    dlg.filterSelected.connect(lambda f: dlg.setDefaultSuffix(_uzanti(f)))
    if dlg.exec() != QtWidgets.QDialog.Accepted or not dlg.selectedFiles():
        return None
    return dlg.selectedFiles()[0]


def ayrinti_metni(r, dilim=None):
    """Secili pinin tek satirlik ayrintisi."""
    p = []
    if r.get("demet"):
        p.append(_("demet %s") % r["demet"])
    p.append(_("çubuk %s") % r["konum"])
    p.append(_("bağıl güç %.4f ± %.4f") % (r["bagil"], r["sigma"]))
    if r.get("W") is not None:
        p.append("%.4g W" % r["W"])
    if r.get("q") is not None:
        p.append("q′ %.2f W/cm" % r["q"])
    d = r.get("dilimler") or []
    if dilim is not None and 0 <= dilim < len(d):
        p.append(_("dilim %d: bağıl %.4f") % (dilim + 1, d[dilim]["bagil"]))
    if r.get("uyeler"):
        p.append(_("%d konumun ortalaması") % len(r["uyeler"]))
    if r.get("sicak"):
        p.append(_("en sıcak çubuk"))
    if r.get("kesik"):
        p.append(_("kesik çubuk (F_ΔH dışı)"))
    return " · ".join(p)
