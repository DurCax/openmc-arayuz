# -*- coding: utf-8 -*-
"""
================================================================================
 sekme_malzeme.py  --  Malzeme tanimlari
================================================================================
 Iki yol:
   * Kutuphaneden ekle : hazir, dogrulanmis bilesimler. Uretim parametreleri
     (zenginlik, sicaklik, bor...) malzemeyle birlikte saklanir
     (m["kutup"], bkz. malzeme_kutup.parametrik_uret); "Duzenle" ayni formu
     acar ve malzeme o parametrelerden YENIDEN uretilir.
   * Elle tanimla      : bilesim tablosu (tur/birim acilir listeden,
     zenginlik yalnizca U elementi satirinda).
 Nadiren gereken alanlar (ham bilesim, yogunluk birimi, renk, serbest S(a,b))
 "Gelismis" bolumundedir.

 KURALLAR BURADA YAZILMAZ
   Kutuphane gruplari   : uygunluk.tek_malzeme_rolleri
   S(a,b) onerileri     : dogrula._SAB_KURALLARI (dogrulamanin uyardigi kural)
   Ad gecerliligi       : sema.malzeme_adi_sorunu
   Ad degisimi          : sema.malzeme_adini_degistir (butun referanslar)
================================================================================
"""

import copy

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import malzeme_kutup as mk
from cekirdek import sema
from arayuz.ortak import (BosDurum, GelismisBolum, RenkDugmesi, SekmeTabani,
                          baslik, ipucu, sayi)

# Spec degerleri AYNEN kalir; kullanici yalnizca okunur etiketi gorur.
TUR_SECENEKLERI = (("element", "Doğal element"), ("nuklid", "İzotop (nüklid)"))
BIRIM_SECENEKLERI = (("ao", "Atom oranı"), ("wo", "Ağırlık oranı"))
YOGUNLUK_BIRIMLERI = (("g/cm3", "g/cm³"), ("atom/b-cm", "atom/b-cm"),
                      ("kg/m3", "kg/m³"))
_YOGUNLUK_ETIKETI = dict(YOGUNLUK_BIRIMLERI)

# Kutuphane listesinin gruplari, SIRAYLA.
GRUPLAR = (("yakit", "Yakıt"), ("yapisal", "Zarf ve yapısal"),
           ("sogutucu", "Soğutucu ve moderatör"), ("emici", "Emici"),
           ("gaz", "Gaz"))
ROL_ETIKETLERI = {"yakit": "yakıt", "sogutucu": "soğutucu", "moderator": "moderatör",
                  "emici": "emici", "yapisal": "yapısal", "gaz": "gaz"}
_ROL_SIRASI = ("yakit", "emici", "gaz", "sogutucu", "moderator", "yapisal")

_KELVIN = 273.15


def rol_grubu(roller):
    """uygunluk rollerinden kutuphane grubu (GRUPLAR anahtari)."""
    roller = set(roller or ())
    if "yakit" in roller:
        return "yakit"
    if "emici" in roller:
        return "emici"
    if "gaz" in roller:
        return "gaz"
    if roller & {"sogutucu", "moderator"}:
        return "sogutucu"
    return "yapisal"


_GRUP_ONBELLEK = {}


def kutuphane_gruplari():
    """
    [(grup, etiket, [anahtar, ...]), ...] -- bos gruplar atlanir. Grup,
    kutuphanenin varsayilan malzemesinin uygunluk rollerinden turetilir;
    grup ici sira malzeme_kutup.KATALOG sirasidir (ilk: UO2).
    """
    if not _GRUP_ONBELLEK:
        from cekirdek import uygunluk
        for anahtar in mk.KATALOG:
            _GRUP_ONBELLEK[anahtar] = rol_grubu(
                uygunluk.tek_malzeme_rolleri(mk.uret(anahtar)))
    cikti = []
    for grup, etiket in GRUPLAR:
        anahtarlar = [k for k in mk.KATALOG if _GRUP_ONBELLEK.get(k) == grup]
        if anahtarlar:
            cikti.append((grup, etiket, anahtarlar))
    return cikti


def sab_onerileri(m):
    """
    Bilesime uyan S(a,b) tablolari [(ad, tanim), ...], EN DAR kural once.
    dogrula._sab_kontrol ile AYNI kural tablosu: dogrulamanin "eksik" diye
    uyardigi durumda burada oneri cikar. Gaz (< 0.1 g/cm3) icin oneri yok.
    """
    from cekirdek import dogrula, uygunluk
    try:
        yog = uygunluk._yogunluk_gcm3(m)
    except Exception:
        yog = None
    if yog is not None and yog <= dogrula._YOGUN_FAZ_ESIGI:
        return []
    elemanlar = dogrula._element_kumesi(m)
    if not elemanlar:
        return []
    eslesen = sorted((len(uygun), onerilen, tanim)
                     for uygun, zorunlu, onerilen, tanim in dogrula._SAB_KURALLARI
                     if zorunlu <= elemanlar <= uygun)
    cikti, gorulen = [], set()
    for _n, onerilen, tanim in eslesen:
        if onerilen not in gorulen:
            gorulen.add(onerilen)
            cikti.append((onerilen, tanim))
    return cikti


def sicaklik_metni(k):
    if not k:
        return "—"
    return "%.1f K (%.1f °C)" % (float(k), float(k) - _KELVIN)


def yogunluk_metni(m):
    y = m.get("yogunluk") or {}
    birim = y.get("birim") or "g/cm3"
    return "%.5g %s" % (float(y.get("deger") or 0.0), _YOGUNLUK_ETIKETI.get(birim, birim))


def bilesim_ozeti(m):
    parca = []
    for b in m.get("bilesim") or []:
        isim = b.get("isim") or "?"
        z = b.get("zenginlik")
        parca.append("%s (%%%.2f U-235)" % (isim, z) if z is not None else isim)
    return ", ".join(parca)


_PLAKA_ALANI = {"et_malzeme": "yakıt tabakası", "zarf_malzeme": "zarf",
                "sogutucu": "soğutucu", "yan_levha_malzeme": "yan levha"}
_YOL_KALIPLARI = (
    (r"cubuklar/(.+)/bolgeler/(\d+)$", lambda a, i: "‘%s’ çubuğunun %d. bölgesi" % (a, int(i) + 1)),
    (r"cubuklar/(.+)/izleyici_malzeme$", lambda a: "‘%s’ kontrol çubuğunun izleyicisi" % a),
    (r"plakalar/(.+)/(\w+)$", lambda a, k: "‘%s’ plakasının %s malzemesi"
     % (a, _PLAKA_ALANI.get(k, k))),
    (r"demetler/(.+)/dolgu_disi$", lambda a: "‘%s’ demetinin dış dolgusu" % a),
    (r"demetler/(.+)/anahtar/.+$", lambda a: "‘%s’ demet haritası" % a),
    (r"kor/yansitici$", lambda: "kor yansıtıcısı"),
    (r"kor/kabuklar/(\d+)$", lambda i: "%d. küresel kabuk" % (int(i) + 1)),
    (r"kor/tambur/govde_malzeme$", lambda: "tambur gövdesi"),
    (r"kor/tambur/emici_malzeme$", lambda: "tambur emicisi"),
    (r"kor/anahtar/.+$", lambda: "kor haritası"),
    (r"kor/dolgu$", lambda: "kor dolgusu"),
    (r"kor/eksenel/(\d+)/dolgu$", lambda i: "%d. eksenel katman" % (int(i) + 1)),
    (r"kor/eksenel/(\d+)/anahtar/.+$", lambda i: "%d. eksenel katmanın haritası" % (int(i) + 1)),
    (r"tallyler/(.+)/filtreler/\d+/adlar/\d+$", lambda a: "‘%s’ tally filtresi" % a),
    (r"tukenme/ek_malzemeler/\d+$", lambda: "tükenme ek malzemeleri"),
)


def yol_okunur(yol):
    """sema.malzeme_adini_degistir yolunu okunur Turkceye cevirir."""
    import re
    for kalip, metin in _YOL_KALIPLARI:
        e = re.match(kalip, yol)
        if e:
            return metin(*e.groups())
    return yol


def _isim_duzelt(isim, tur):
    """Element/nuklid adini OpenMC yazimina getirir: "zr" -> "Zr", "u235" -> "U235"."""
    isim = (isim or "").strip()
    if not isim:
        return isim
    if tur == "nuklid":
        i = 0
        while i < len(isim) and isim[i].isalpha():
            i += 1
        harf = isim[:i]
        return harf[:1].upper() + harf[1:].lower() + isim[i:]
    return isim[:1].upper() + isim[1:].lower()


def _sayi_metni(v):
    """Float'i kayipsiz ama okunur yazar (0.0001785 -> '0.0001785')."""
    return repr(float(v))


# ============================================================================
# Kucuk girdiler
# ============================================================================

class SicaklikGirdi(QtWidgets.QWidget):
    """Kelvin kutusu + yaninda canli Celsius karsiligi."""

    degisti = QtCore.Signal(float)

    def __init__(self, deger=293.6, en_az=0.0, en_cok=5000.0, ondalik=2,
                 adim=10.0, parent=None):
        super().__init__(parent)
        self.kutu = sayi(deger if deger is not None else 293.6, ondalik,
                         en_az, en_cok, adim, "K")
        self.celsius = QtWidgets.QLabel()
        self.celsius.setObjectName("soluk")
        self.celsius.setMinimumWidth(90)
        d = QtWidgets.QHBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        d.addWidget(self.kutu)
        d.addWidget(self.celsius)
        d.addStretch(1)
        self.kutu.valueChanged.connect(self._guncelle)
        self._guncelle(self.kutu.value())

    def _guncelle(self, k):
        self.celsius.setText("= %.1f °C" % (k - _KELVIN))
        self.degisti.emit(k)

    def value(self):
        return self.kutu.value()

    def setValue(self, k):
        self.kutu.setValue(k)


class KesinSayiGirdi(QtWidgets.QLineEdit):
    """
    Pozitif ondalik sayi girisi; degeri YUVARLAMAZ. Eski spinbox 6 ondalikla
    helyumun 0.0001785 g/cm3 yogunlugunu her duzenlemede 0.000179'a
    yuvarliyordu.
    """

    def __init__(self, deger=1.0, parent=None):
        super().__init__(parent)
        v = QtGui.QDoubleValidator(self)
        v.setNotation(QtGui.QDoubleValidator.ScientificNotation)
        v.setBottom(0.0)
        v.setLocale(QtCore.QLocale.c())
        self.setValidator(v)
        self._ilk = float(deger or 0.0)
        self.setText(_sayi_metni(self._ilk))
        self._ilk_metin = self.text()
        self.setMaximumWidth(160)

    def deger(self):
        """Metin degismediyse ILK deger (kayipsiz); gecersizse None."""
        if self.text() == self._ilk_metin:
            return self._ilk
        try:
            return float(self.text().replace(",", "."))
        except ValueError:
            return None


# ============================================================================
# Parametre formu (kutuphane malzemesi)
# ============================================================================

class ParametreFormu(QtWidgets.QWidget):
    """
    Bir kutuphane malzemesinin parametre formu. Yalnizca O malzemede anlamli
    parametreler sorulur (UO2'de bor yok, suda zenginlik yok); sicaklik her
    malzemede sorulur. param() kutuphane fonksiyonunun argumanlaridir.
    """

    degisti = QtCore.Signal()

    def __init__(self, anahtar, param=None, parent=None):
        super().__init__(parent)
        self.anahtar = anahtar
        self.tanimlar = mk.parametreler(anahtar)
        degerler = mk.varsayilan_parametreler(anahtar)
        if param:
            degerler.update(param)
        # Yeni malzemede formdaki her deger spec'e yazilir (okunur JSON);
        # var olanda yalnizca kayitli ya da DEGISEN anahtarlar -- dokunulmayan
        # bir malzeme bit bit ayni kalir.
        self._yazilan = set(degerler) if param is None else set(param)
        self._ilk = dict(degerler)
        self._ilk_gosterim = {}
        self.alanlar = {}
        self.etiketler = {}

        form = QtWidgets.QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldsStayAtSizeHint)
        for p in self.tanimlar:
            ad = p["ad"]
            deger = degerler.get(ad)
            if p["tur"] == "sicaklik":
                w = SicaklikGirdi(deger, p["en_az"], p["en_cok"], p["ondalik"], p["adim"])
                w.degisti.connect(self._degisti)
            else:
                w = sayi(p["en_az"] if deger is None else deger, p["ondalik"],
                         p["en_az"], p["en_cok"], p["adim"], p["sonek"])
                if p["tur"] == "dogal_ya_da":
                    w.setSpecialValueText(p["dogal_metin"])
                w.valueChanged.connect(self._degisti)
            if p.get("ipucu"):
                w.setToolTip(p["ipucu"])
            etiket = _etiket(p["etiket"] + ":")
            form.addRow(etiket, w)
            self.alanlar[ad] = w
            self.etiketler[ad] = etiket
            self._ilk_gosterim[ad] = w.value()

        self.hesaplanan = None
        if anahtar in mk.SICAKLIKTAN_YOGUNLUK:
            self.hesaplanan = QtWidgets.QLabel()
            self.hesaplanan.setToolTip("Sıcaklıktan hesaplanır; değiştirmek için sıcaklığı değiştirin.")
            form.addRow(_etiket("Yoğunluk:"), self.hesaplanan)
        self.uyari = QtWidgets.QLabel()
        self.uyari.setWordWrap(True)
        self.uyari.setStyleSheet("color: %s;" % _tema_renk("uyari", "#a8620a"))
        form.addRow(self.uyari)
        self._degisti()

    def _degisti(self, *_):
        param = self.param()
        if self.hesaplanan is not None:
            try:
                m = mk.uret(self.anahtar, **param)
                self.hesaplanan.setText("%.4f g/cm³" % m["yogunluk"]["deger"])
            except Exception as e:           # pragma: no cover - savunma
                self.hesaplanan.setText(str(e))
        uyari = mk.parametre_uyarilari(self.anahtar, param)
        self.uyari.setText("\n".join("⚠ " + u for u in uyari))
        self.uyari.setVisible(bool(uyari))
        self.degisti.emit()

    def param(self):
        cikti = {}
        for p in self.tanimlar:
            ad = p["ad"]
            v = self.alanlar[ad].value()
            if v == self._ilk_gosterim[ad]:
                if ad in self._yazilan:
                    cikti[ad] = self._ilk.get(ad)
                continue
            if p["tur"] == "dogal_ya_da" and v <= p["en_az"]:
                v = None
            cikti[ad] = v
        return cikti

    def malzeme(self):
        return mk.parametrik_uret(self.anahtar, self.param())

    def uretim_sorunu(self):
        """Bu parametrelerle malzeme kurulamiyorsa nedeni (or. U3Si2-Al'da
        alüminyuma yer kalmamasi); kurulabiliyorsa None."""
        try:
            self.malzeme()
        except (ValueError, TypeError) as e:
            return str(e)
        return None


def _tema_renk(ad, vars_):
    try:
        from arayuz import tema
        return tema.renk(ad)
    except Exception:
        return vars_


# Diyalogdaki butun form etiketleri ayni genislikte: ust "Ad" satiri,
# parametre formu ve elle formu ayri QFormLayout'lardir; hizalanmalari icin.
ETIKET_GENISLIGI = 180


def _etiket(metin):
    e = QtWidgets.QLabel(metin)
    e.setMinimumWidth(ETIKET_GENISLIGI)
    return e


def _ozet_etiketi():
    e = QtWidgets.QLabel()
    e.setWordWrap(True)
    e.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
    return e


def _hata_etiketi():
    e = QtWidgets.QLabel()
    e.setWordWrap(True)
    e.setStyleSheet("color: %s;" % _tema_renk("hata", "#b3261e"))
    e.setVisible(False)
    return e


def _benzersiz_ad(spec, taban):
    ad, i = taban, 2
    while sema.malzeme_adi_sorunu(spec, ad) is not None:
        ad = "%s_%d" % (taban, i)
        i += 1
    return ad


# ============================================================================
# Bilesim tablosu
# ============================================================================

class BilesimModeli(QtCore.QAbstractTableModel):
    """
    Malzeme bilesim satirlari. "Tur" ve "Birim" acilir listeden secilir
    (spec degerleri element/nuklid ve ao/wo AYNEN kalir). Zenginlik yalnizca
    tur=element ve isim=U satirinda duzenlenebilir: OpenMC baska bir elementte
    kosu sirasinda reddeder, nuklidde sessizce yok sayar.
    """

    BASLIKLAR = ["Tür", "İsim", "Miktar", "Birim", "Zenginlik %"]
    S_TUR, S_ISIM, S_MIKTAR, S_BIRIM, S_ZENG = range(5)

    def __init__(self, bilesim, salt_okunur=False, parent=None):
        super().__init__(parent)
        self.bilesim = copy.deepcopy(bilesim or [])
        self.salt_okunur = salt_okunur

    def yukle(self, bilesim):
        self.beginResetModel()
        self.bilesim = copy.deepcopy(bilesim or [])
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self.bilesim)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 0 if parent.isValid() else len(self.BASLIKLAR)

    def headerData(self, bolum, yon, rol=QtCore.Qt.DisplayRole):
        if rol == QtCore.Qt.DisplayRole and yon == QtCore.Qt.Horizontal:
            return self.BASLIKLAR[bolum]
        if rol == QtCore.Qt.DisplayRole and yon == QtCore.Qt.Vertical:
            return str(bolum + 1)
        return None

    def zenginlik_uygun(self, satir):
        b = self.bilesim[satir]
        return b.get("tur", "element") != "nuklid" and b.get("isim") == "U"

    def data(self, ix, rol=QtCore.Qt.DisplayRole):
        if not ix.isValid():
            return None
        b = self.bilesim[ix.row()]
        s = ix.column()
        if rol == QtCore.Qt.EditRole:
            return [b.get("tur", "element"), b.get("isim", ""), b.get("miktar", 0.0),
                    b.get("birim", "ao"), b.get("zenginlik")][s]
        if rol == QtCore.Qt.DisplayRole:
            if s == self.S_TUR:
                return dict(TUR_SECENEKLERI).get(b.get("tur", "element"), b.get("tur"))
            if s == self.S_ISIM:
                return b.get("isim", "")
            if s == self.S_MIKTAR:
                return "%.6g" % float(b.get("miktar") or 0.0)
            if s == self.S_BIRIM:
                return dict(BIRIM_SECENEKLERI).get(b.get("birim", "ao"), b.get("birim"))
            z = b.get("zenginlik")
            if z is None:
                return "doğal" if self.zenginlik_uygun(ix.row()) else ""
            return "%g" % z
        if rol == QtCore.Qt.ForegroundRole and s == self.S_ZENG:
            if b.get("zenginlik") is None or not self.zenginlik_uygun(ix.row()):
                return QtGui.QBrush(QtGui.QColor(_tema_renk("metin_soluk", "#6b7785")))
        if rol == QtCore.Qt.ToolTipRole and s == self.S_ZENG:
            if not self.zenginlik_uygun(ix.row()):
                return "Zenginlik yalnızca doğal element U satırında girilir."
            return "U-235 ağırlıkça %; boş bırakılırsa doğal uranyum."
        return None

    def _zenginlik_temizle(self, satir):
        b = self.bilesim[satir]
        if not self.zenginlik_uygun(satir) and b.get("zenginlik") is not None:
            b.pop("zenginlik", None)

    def setData(self, ix, deger, rol=QtCore.Qt.EditRole):
        if rol != QtCore.Qt.EditRole or not ix.isValid() or self.salt_okunur:
            return False
        satir, s = ix.row(), ix.column()
        b = self.bilesim[satir]
        try:
            if s == self.S_TUR:
                if deger not in dict(TUR_SECENEKLERI):
                    return False
                b["tur"] = deger
                b["isim"] = _isim_duzelt(b.get("isim"), deger)
                self._zenginlik_temizle(satir)
            elif s == self.S_ISIM:
                b["isim"] = _isim_duzelt(str(deger), b.get("tur", "element"))
                self._zenginlik_temizle(satir)
            elif s == self.S_MIKTAR:
                b["miktar"] = float(str(deger).replace(",", "."))
            elif s == self.S_BIRIM:
                if deger not in dict(BIRIM_SECENEKLERI):
                    return False
                b["birim"] = deger
            elif s == self.S_ZENG:
                metin = "" if deger is None else str(deger).strip()
                if metin in ("", "doğal"):
                    b.pop("zenginlik", None)
                elif not self.zenginlik_uygun(satir):
                    return False            # yalnizca silinebilir
                else:
                    b["zenginlik"] = float(metin.replace(",", "."))
        except ValueError:
            return False
        # satirin tamami: zenginlik hucresinin etkinligi degismis olabilir
        self.dataChanged.emit(self.index(satir, 0), self.index(satir, self.columnCount() - 1))
        return True

    def flags(self, ix):
        temel = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        if not ix.isValid() or self.salt_okunur:
            return temel
        if ix.column() == self.S_ZENG:
            if self.zenginlik_uygun(ix.row()):
                return temel | QtCore.Qt.ItemIsEditable
            if self.bilesim[ix.row()].get("zenginlik") is not None:
                # eski dosyadaki gecersiz deger: yalnizca silinebilsin
                return temel | QtCore.Qt.ItemIsEditable
            return QtCore.Qt.ItemIsSelectable          # gri, duzenlenemez
        return temel | QtCore.Qt.ItemIsEditable

    def satir_ekle(self):
        self.beginInsertRows(QtCore.QModelIndex(), len(self.bilesim), len(self.bilesim))
        self.bilesim.append({"tur": "element", "isim": "", "miktar": 1.0, "birim": "ao"})
        self.endInsertRows()

    def satir_sil(self, satir):
        if 0 <= satir < len(self.bilesim):
            self.beginRemoveRows(QtCore.QModelIndex(), satir, satir)
            self.bilesim.pop(satir)
            self.endRemoveRows()


class SecenekDelegesi(QtWidgets.QStyledItemDelegate):
    """Hucreyi acilir listeyle duzenler; model ANAHTARI yazar, etiketi gosterir."""

    def __init__(self, secenekler, parent=None):
        super().__init__(parent)
        self.secenekler = tuple(secenekler)

    def createEditor(self, ebeveyn, secenek, ix):
        c = QtWidgets.QComboBox(ebeveyn)
        for anahtar, etiket in self.secenekler:
            c.addItem(etiket, anahtar)
        c.activated.connect(lambda _i, c=c: (self.commitData.emit(c),
                                             self.closeEditor.emit(c)))
        return c

    def setEditorData(self, editor, ix):
        i = editor.findData(ix.data(QtCore.Qt.EditRole))
        editor.setCurrentIndex(max(i, 0))

    def setModelData(self, editor, model, ix):
        model.setData(ix, editor.currentData(), QtCore.Qt.EditRole)


def _bilesim_tablosu(model):
    t = QtWidgets.QTableView()
    t.setModel(model)
    t.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    t.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
    t.horizontalHeader().setStretchLastSection(True)
    t.verticalHeader().setDefaultSectionSize(26)
    t.setMinimumHeight(150)
    if not model.salt_okunur:
        t.setItemDelegateForColumn(model.S_TUR, SecenekDelegesi(TUR_SECENEKLERI, t))
        t.setItemDelegateForColumn(model.S_BIRIM, SecenekDelegesi(BIRIM_SECENEKLERI, t))
        t.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked
                          | QtWidgets.QAbstractItemView.SelectedClicked
                          | QtWidgets.QAbstractItemView.EditKeyPressed
                          | QtWidgets.QAbstractItemView.AnyKeyPressed)
    else:
        t.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    for s, g in ((0, 130), (1, 80), (2, 100), (3, 120)):
        t.setColumnWidth(s, g)
    return t


# ============================================================================
# Kutuphaneden ekleme
# ============================================================================

class KutuphaneDiyalog(QtWidgets.QDialog):
    """Rol gruplu kutuphane listesi + secilen malzemenin parametre formu."""

    GELISMIS_ANAHTAR = "malzeme_kutuphane"

    def __init__(self, spec=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kütüphaneden malzeme ekle")
        self.resize(860, 620)
        self._spec = spec if spec is not None else sema.yeni_spec()
        self._ad_elle = False
        self.form = None

        self.liste = QtWidgets.QTreeWidget()
        self.liste.setHeaderHidden(True)
        self.liste.setRootIsDecorated(False)
        self.liste.setIndentation(12)
        self.liste.setMinimumWidth(270)
        self._ogeler = {}
        for grup, etiket, anahtarlar in kutuphane_gruplari():
            g = QtWidgets.QTreeWidgetItem([etiket])
            g.setFlags(QtCore.Qt.ItemIsEnabled)            # secilemez baslik
            g.setData(0, QtCore.Qt.UserRole + 1, grup)
            f = g.font(0)
            f.setBold(True)
            g.setFont(0, f)
            self.liste.addTopLevelItem(g)
            for k in anahtarlar:
                oge = QtWidgets.QTreeWidgetItem([mk.okunur_ad(k)])
                oge.setData(0, QtCore.Qt.UserRole, k)
                oge.setToolTip(0, mk.katalog_aciklamasi(k))
                g.addChild(oge)
                self._ogeler[k] = oge
        self.liste.expandAll()

        self.baslik_etiket = baslik("")
        self.aciklama = ipucu("")
        self.ad = QtWidgets.QLineEdit()
        self.ad.textEdited.connect(self._ad_duzenlendi)
        self.ad.textChanged.connect(self._dogrula)
        self.ad_hata = _hata_etiketi()
        ust = QtWidgets.QFormLayout()
        ust.addRow(_etiket("Ad:"), self.ad)
        ust.addRow(self.ad_hata)
        self.form_kutu = QtWidgets.QWidget()
        self._form_duzen = QtWidgets.QVBoxLayout(self.form_kutu)
        self._form_duzen.setContentsMargins(0, 0, 0, 0)
        self.ozet = _ozet_etiketi()

        self.kutu = QtWidgets.QDialogButtonBox()
        self.d_tamam = self.kutu.addButton("Ekle", QtWidgets.QDialogButtonBox.AcceptRole)
        self.kutu.addButton("Vazgeç", QtWidgets.QDialogButtonBox.RejectRole)
        self.kutu.accepted.connect(self._onayla)
        self.kutu.rejected.connect(self.reject)

        sag = QtWidgets.QVBoxLayout()
        sag.addWidget(self.baslik_etiket)
        sag.addWidget(self.aciklama)
        sag.addLayout(ust)
        sag.addWidget(self.form_kutu)
        sag.addWidget(self.ozet)
        sag.addStretch(1)
        govde = QtWidgets.QHBoxLayout()
        govde.addWidget(self.liste, 0)
        govde.addLayout(sag, 1)
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addLayout(govde, 1)
        duzen.addWidget(self.kutu)

        self.liste.currentItemChanged.connect(self._secim_degisti)
        self.sec("uo2" if "uo2" in self._ogeler else next(iter(self._ogeler)))

    # -------------------------------------------------------------- secim
    def sec(self, anahtar):
        self.liste.setCurrentItem(self._ogeler[anahtar])

    def secilen(self):
        oge = self.liste.currentItem()
        return oge.data(0, QtCore.Qt.UserRole) if oge else None

    def _secim_degisti(self, oge, _onceki=None):
        anahtar = oge.data(0, QtCore.Qt.UserRole) if oge else None
        if not anahtar:
            # grup basligi (klavyeyle) secildi: grubun ilk malzemesine gec
            if oge is not None and oge.childCount():
                self.liste.setCurrentItem(oge.child(0))
            return
        self.baslik_etiket.setText(mk.okunur_ad(anahtar))
        self.aciklama.setText(mk.katalog_aciklamasi(anahtar))
        if self.form is not None:
            # hemen gizle ve ayir: deleteLater olay dongusune kadar bekler,
            # o arada eski formun etiketleri yenisinin ustune ciziliyordu
            self._form_duzen.removeWidget(self.form)
            self.form.hide()
            self.form.setParent(None)
            self.form.deleteLater()
        self.form = ParametreFormu(anahtar)
        self.form.degisti.connect(self._ozet_guncelle)
        self._form_duzen.addWidget(self.form)
        if not self._ad_elle:
            self.ad.setText(_benzersiz_ad(self._spec, anahtar))
        self._ozet_guncelle()
        self._dogrula()

    def _ad_duzenlendi(self, _metin):
        self._ad_elle = True

    # -------------------------------------------------------------- sonuc
    def _ozet_guncelle(self):
        if self.form is None:
            return
        uretim = self.form.uretim_sorunu()
        if uretim:
            self.ozet.setText("Bu değerlerle malzeme kurulamıyor: %s" % uretim)
        else:
            m = self.form.malzeme()
            sab = ", ".join(m.get("sab") or []) or "yok"
            self.ozet.setText("Bileşim: %s   ·   S(α,β): %s\nAçıklama: %s"
                              % (bilesim_ozeti(m), sab, m.get("gorunen_ad")))
        self._dogrula()

    def _dogrula(self, *_):
        sorun = sema.malzeme_adi_sorunu(self._spec, self.ad.text())
        self.ad_hata.setText(sorun or "")
        self.ad_hata.setVisible(bool(sorun))
        uretim = self.form.uretim_sorunu() if self.form is not None else None
        self.d_tamam.setEnabled(sorun is None and uretim is None and self.secilen() is not None)
        return sorun is None and uretim is None

    def _onayla(self):
        if self._dogrula():
            self.accept()

    def sonuc(self):
        m = self.form.malzeme()
        m["ad"] = self.ad.text()
        return m

    # geriye uyumluluk (eski ad)
    uret = sonuc


# ============================================================================
# Duzenleme
# ============================================================================

class MalzemeDiyalog(QtWidgets.QDialog):
    """
    Tek bir malzemeyi duzenler.
      * kutuphane malzemesi (mk.parametrik_mi): AYNI parametre formu; sonuc
        parametrelerden yeniden uretilir. Ham bilesim Gelismis'te salt okunur;
        "Bilesimi elle duzenle" malzemeyi kutuphaneden ayirir.
      * diger (eski/elle) malzemeler: bilesim tablosu.
    Tek ad alani vardir (spec "ad"i). "gorunen_ad" kutuphane malzemesinde
    parametrelerden uretilen aciklamadir; elle malzemede eski deger korunur
    (adla ayniysa adla birlikte degisir).
    """

    GELISMIS_ANAHTAR = "malzeme_diyalog"

    def __init__(self, malzeme, spec=None, parent=None, yeni=False):
        super().__init__(parent)
        # Eski imza MalzemeDiyalog(malzeme, mevcut_adlar) de kabul edilir.
        if spec is None or isinstance(spec, (list, tuple, set)):
            adlar = list(spec or [])
            spec = sema.yeni_spec()
            spec["malzemeler"] = [{"ad": a} for a in adlar]
        self._spec = spec
        self._orijinal = copy.deepcopy(malzeme)
        self._eski_ad = malzeme.get("ad", "")
        self._parametrik = mk.parametrik_mi(malzeme)
        self._kopmus = "kutup" in malzeme and not self._parametrik
        self.setWindowTitle("Yeni malzeme" if yeni else "Malzemeyi düzenle")
        self.resize(660, 600)

        # ---- ad ----
        self.ad = QtWidgets.QLineEdit(self._eski_ad)
        self.ad.textChanged.connect(self._dogrula)
        self.ad_hata = _hata_etiketi()
        ust = QtWidgets.QFormLayout()
        ust.addRow(_etiket("Ad:"), self.ad)
        ust.addRow(self.ad_hata)

        # ---- kutuphane (parametrik) sayfasi ----
        self.param_sayfa = QtWidgets.QWidget()
        pd = QtWidgets.QVBoxLayout(self.param_sayfa)
        pd.setContentsMargins(0, 0, 0, 0)
        self.form = None
        if self._parametrik:
            k = malzeme["kutup"]
            self.tur_etiket = baslik("%s (kütüphane)" % mk.okunur_ad(k["anahtar"]))
            pd.addWidget(self.tur_etiket)
            pd.addWidget(ipucu(mk.katalog_aciklamasi(k["anahtar"])))
            self.form = ParametreFormu(k["anahtar"], k.get("param") or {})
            self.form.degisti.connect(self._param_degisti)
            pd.addWidget(self.form)

        # ---- elle sayfasi ----
        self.elle_sayfa = QtWidgets.QWidget()
        ed = QtWidgets.QVBoxLayout(self.elle_sayfa)
        ed.setContentsMargins(0, 0, 0, 0)
        self.kopuk_not = ipucu(
            "Bu malzeme kütüphaneden eklendikten sonra parametre formu dışında "
            "değiştirilmiş; bileşim tablosuyla düzenleniyor.")
        self.kopuk_not.setVisible(self._kopmus)
        ed.addWidget(self.kopuk_not)
        self.elle_form = QtWidgets.QFormLayout()
        # Elle malzemede aciklama kendiliginden yenilenmez (bilesimden okunamaz):
        # zenginligi degistiren kullanici onu burada gunceller. Eskiden alan
        # yoktu ve "UO2 %3.0" aciklamasi %4 zenginlikte de listelerde kaliyordu.
        g0 = malzeme.get("gorunen_ad") or ""
        self.aciklama = QtWidgets.QLineEdit("" if g0 == self._eski_ad else g0)
        self.aciklama.setPlaceholderText("ör. UO₂ %4.0 — listelerde adın yanında görünür")
        self.elle_form.addRow(_etiket("Açıklama:"), self.aciklama)
        yog = QtWidgets.QHBoxLayout()
        self.yogunluk = KesinSayiGirdi((malzeme.get("yogunluk") or {}).get("deger") or 1.0)
        self.yogunluk.textChanged.connect(self._elle_degisti)
        self.yogunluk_birim_etiket = QtWidgets.QLabel()
        yog.addWidget(self.yogunluk)
        yog.addWidget(self.yogunluk_birim_etiket)
        yog.addStretch(1)
        self.elle_form.addRow(_etiket("Yoğunluk:"), yog)
        self._ilk_sicaklik = malzeme.get("sicaklik")
        self.sicaklik = SicaklikGirdi(self._ilk_sicaklik or 293.6, 0.0, 5000.0, 2, 10.0)
        self._ilk_sicaklik_gosterim = self.sicaklik.value()
        self.elle_form.addRow(_etiket("Sıcaklık:"), self.sicaklik)
        self.sab_kutu = QtWidgets.QComboBox()
        self.sab_kutu.setToolTip("Bileşime uyan termal saçılma tabloları. Termal "
                                 "spektrumda eksik bırakmak k'yi yüzde mertebesinde kaydırır.")
        self.sab_kutu.activated.connect(self._sab_secildi)
        self.elle_form.addRow(_etiket("Termal saçılma S(α,β):"), self.sab_kutu)
        ed.addLayout(self.elle_form)
        ed.addWidget(baslik("Bileşim"))
        self.model = BilesimModeli(malzeme.get("bilesim"))
        self.tablo = _bilesim_tablosu(self.model)
        ed.addWidget(self.tablo, 1)
        self.d_satir_ekle = QtWidgets.QPushButton("Satır ekle")
        self.d_satir_sil = QtWidgets.QPushButton("Satırı sil")
        self.d_satir_ekle.clicked.connect(self._satir_ekle)
        self.d_satir_sil.clicked.connect(self._satir_sil)
        sd = QtWidgets.QHBoxLayout()
        sd.addWidget(self.d_satir_ekle)
        sd.addWidget(self.d_satir_sil)
        sd.addStretch(1)
        ed.addLayout(sd)
        self.tablo.selectionModel().selectionChanged.connect(self._satir_dugmeleri)
        for sinyal in (self.model.dataChanged, self.model.rowsInserted,
                       self.model.rowsRemoved, self.model.modelReset):
            sinyal.connect(self._elle_degisti)

        self.ozet = _ozet_etiketi()

        # ---- gelismis ----
        self.gelismis = GelismisBolum(self.GELISMIS_ANAHTAR)
        g_form = QtWidgets.QFormLayout()
        self.renk = RenkDugmesi(malzeme.get("renk") or (170, 170, 170))
        g_form.addRow(_etiket("Renk:"), self.renk)
        self.birim = QtWidgets.QComboBox()
        for anahtar, etiket in YOGUNLUK_BIRIMLERI:
            self.birim.addItem(etiket, anahtar)
        ilk_birim = (malzeme.get("yogunluk") or {}).get("birim") or "g/cm3"
        if self.birim.findData(ilk_birim) < 0:
            self.birim.addItem(ilk_birim, ilk_birim)
        self.birim.setCurrentIndex(self.birim.findData(ilk_birim))
        self.birim.currentIndexChanged.connect(self._elle_degisti)
        self.birim_etiket = _etiket("Yoğunluk birimi:")
        g_form.addRow(self.birim_etiket, self.birim)
        self.sab_elle = QtWidgets.QLineEdit()
        self.sab_elle.setPlaceholderText("ör. c_H_in_H2O, c_Graphite")
        self.sab_elle.setToolTip("Virgülle ayrılmış S(α,β) tablo adları. Önerilen "
                                 "listede olmayan bir tablo gerekiyorsa buraya yazın.")
        self.sab_elle.editingFinished.connect(self._sab_elle_bitti)
        self.sab_elle_etiket = _etiket("S(α,β) (elle):")
        g_form.addRow(self.sab_elle_etiket, self.sab_elle)
        self.gelismis.duzen().addLayout(g_form)
        # parametrik: ham bilesim (salt okunur) + kutuphaneden ayirma
        self.ham_kutu = QtWidgets.QWidget()
        hd = QtWidgets.QVBoxLayout(self.ham_kutu)
        hd.setContentsMargins(0, 0, 0, 0)
        hd.addWidget(QtWidgets.QLabel("Üretilen bileşim:"))
        self.ham_model = BilesimModeli([], salt_okunur=True)
        self.ham_tablo = _bilesim_tablosu(self.ham_model)
        hd.addWidget(self.ham_tablo)
        self.d_elle_gec = QtWidgets.QPushButton("Bileşimi elle düzenle")
        self.d_elle_gec.setToolTip("Malzeme kütüphane parametrelerinden ayrılır; "
                                   "zenginlik, sıcaklık gibi değerler bir daha "
                                   "otomatik hesaplanmaz.")
        self.d_elle_gec.clicked.connect(self.elle_duzenlemeye_gec)
        hd.addWidget(self.d_elle_gec, 0, QtCore.Qt.AlignLeft)
        hd.addWidget(ipucu("Elle düzenlemeye geçince malzeme kütüphane "
                           "parametrelerinden ayrılır."))
        self.gelismis.ekle(self.ham_kutu)

        # ---- dugmeler ----
        self.kutu = QtWidgets.QDialogButtonBox()
        self.d_tamam = self.kutu.addButton("Tamam", QtWidgets.QDialogButtonBox.AcceptRole)
        self.kutu.addButton("Vazgeç", QtWidgets.QDialogButtonBox.RejectRole)
        self.kutu.accepted.connect(self._onayla)
        self.kutu.rejected.connect(self.reject)
        self.hata = _hata_etiketi()

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addLayout(ust)
        duzen.addWidget(self.param_sayfa)
        duzen.addWidget(self.elle_sayfa, 1)
        duzen.addWidget(self.ozet)
        duzen.addWidget(self.gelismis)
        duzen.addStretch(0)
        duzen.addWidget(self.hata)
        duzen.addWidget(self.kutu)

        # S(a,b) durumu: tek kaynak self._sab
        self._sab = list(malzeme.get("sab") or [])
        self._oneri_vardi = bool(sab_onerileri(malzeme))
        self._kip_uygula()
        self._dogrula()
        if yeni and not self.model.bilesim and not self.parametrik_kip():
            self._satir_ekle()

    # ------------------------------------------------------------------ kip
    def parametrik_kip(self):
        return self.form is not None

    def _kip_uygula(self):
        p = self.parametrik_kip()
        self.param_sayfa.setVisible(p)
        self.elle_sayfa.setVisible(not p)
        self.ham_kutu.setVisible(p)
        for w in (self.birim_etiket, self.birim, self.sab_elle_etiket, self.sab_elle):
            w.setVisible(not p)
        if p:
            self._param_degisti()
        else:
            self._sab_kutusunu_kur()
            self._elle_degisti()
        self._satir_dugmeleri()
        # parametrik formda bilesim tablosu yok: pencere icerik kadar olsun
        self.resize(660, self.sizeHint().height() if p else 600)

    def elle_duzenlemeye_gec(self):
        """Parametrik malzemeyi kutuphaneden ayirip bilesim tablosuna gecer."""
        if self.form is None:
            return
        m = self.form.malzeme()
        m.pop("kutup", None)
        m["ad"] = self._eski_ad
        m["renk"] = list(self.renk.rgb())
        for k, v in self._orijinal.items():
            if k not in m and k != "kutup":
                m[k] = copy.deepcopy(v)
        self._orijinal = m
        self.aciklama.setText(m.get("gorunen_ad") or "")
        self.form.hide()
        self.form.setParent(None)
        self.form.deleteLater()
        self.form = None
        self.yogunluk._ilk = float(m["yogunluk"]["deger"])
        self.yogunluk.setText(_sayi_metni(self.yogunluk._ilk))
        self.yogunluk._ilk_metin = self.yogunluk.text()
        self.birim.setCurrentIndex(max(self.birim.findData(m["yogunluk"]["birim"]), 0))
        self._ilk_sicaklik = m.get("sicaklik")
        self.sicaklik.setValue(self._ilk_sicaklik or 293.6)
        self._ilk_sicaklik_gosterim = self.sicaklik.value()
        self._sab = list(m.get("sab") or [])
        self._oneri_vardi = bool(sab_onerileri(m))
        self.model.yukle(m.get("bilesim"))
        self._kip_uygula()

    # ------------------------------------------------------------ parametrik
    def _param_degisti(self):
        if self.form is None:
            return
        uretim = self.form.uretim_sorunu()
        if uretim:
            self.ozet.setText("Bu değerlerle malzeme kurulamıyor: %s" % uretim)
        else:
            m = self.form.malzeme()
            self.ham_model.yukle(m.get("bilesim"))
            sab = ", ".join(m.get("sab") or []) or "yok"
            self.ozet.setText("Bileşim: %s   ·   S(α,β): %s\nAçıklama: %s"
                              % (bilesim_ozeti(m), sab, m.get("gorunen_ad")))
        self._dogrula()

    # ----------------------------------------------------------------- elle
    def _gecici_malzeme(self):
        return {"bilesim": self.model.bilesim,
                "yogunluk": {"birim": self.birim.currentData(),
                             "deger": self.yogunluk.deger() or 0.0}}

    def _elle_degisti(self, *_):
        if self.parametrik_kip():
            return
        self.yogunluk_birim_etiket.setText(
            dict(YOGUNLUK_BIRIMLERI).get(self.birim.currentData(), self.birim.currentData()))
        oneriler = sab_onerileri(self._gecici_malzeme())
        # Bilesim su/grafit gorunumune YENI geldiyse (bu pencerede) onerilen
        # S(a,b) kendiliginden secilir; acilista var olan secim DEGISMEZ.
        if oneriler and not self._oneri_vardi and not self._sab:
            self._sab = [oneriler[0][0]]
            self.sab_elle.setText(", ".join(self._sab))
        self._oneri_vardi = bool(oneriler)
        self._sab_kutusunu_kur(oneriler)
        try:
            from cekirdek import uygunluk
            roller = uygunluk.tek_malzeme_rolleri(self._gecici_malzeme())
        except Exception:
            roller = set()
        rol = ", ".join(ROL_ETIKETLERI[r] for r in _ROL_SIRASI if r in roller)
        self.ozet.setText("Bu bileşim modelde şöyle tanınıyor: %s" % (rol or "—"))

    def _sab_kutusunu_kur(self, oneriler=None):
        if oneriler is None:
            oneriler = sab_onerileri(self._gecici_malzeme())
        self.sab_kutu.blockSignals(True)
        self.sab_kutu.clear()
        for ad, tanim in oneriler:
            self.sab_kutu.addItem("%s — %s" % (ad, tanim), [ad])
        if self._sab and self._sab not in [[a] for a, _t in oneriler]:
            self.sab_kutu.insertItem(0, "Elle girilen: %s" % ", ".join(self._sab), list(self._sab))
        self.sab_kutu.addItem("Yok (termal saçılma verisi ekleme)", [])
        for i in range(self.sab_kutu.count()):
            if self.sab_kutu.itemData(i) == self._sab:
                self.sab_kutu.setCurrentIndex(i)
                break
        self.sab_kutu.blockSignals(False)
        goster = bool(oneriler) or bool(self._sab)
        self.elle_form.setRowVisible(self.sab_kutu, goster)
        if self.sab_elle.text() != ", ".join(self._sab) and not self.sab_elle.hasFocus():
            self.sab_elle.setText(", ".join(self._sab))

    def _sab_secildi(self, i):
        self._sab = list(self.sab_kutu.itemData(i) or [])
        self.sab_elle.setText(", ".join(self._sab))
        self._elle_degisti()

    def _sab_elle_bitti(self):
        yeni = [s.strip() for s in self.sab_elle.text().replace(";", ",").split(",") if s.strip()]
        if yeni != self._sab:
            self._sab = yeni
            self._elle_degisti()

    def _satir_ekle(self):
        self.model.satir_ekle()
        ix = self.model.index(self.model.rowCount() - 1, BilesimModeli.S_ISIM)
        self.tablo.setCurrentIndex(ix)
        self.tablo.edit(ix)

    def _satir_sil(self):
        satirlar = self.tablo.selectionModel().selectedRows()
        if satirlar:
            self.model.satir_sil(satirlar[0].row())

    def _satir_dugmeleri(self, *_):
        self.d_satir_sil.setEnabled(bool(self.tablo.selectionModel().selectedRows()))

    # ---------------------------------------------------------------- onay
    def _dogrula(self, *_):
        sorun = sema.malzeme_adi_sorunu(self._spec, self.ad.text(), haric=self._eski_ad)
        self.ad_hata.setText(sorun or "")
        self.ad_hata.setVisible(bool(sorun))
        uretim = self.form.uretim_sorunu() if self.parametrik_kip() else None
        self.d_tamam.setEnabled(sorun is None and uretim is None)
        return sorun is None and uretim is None

    def icerik_sorunu(self):
        """Elle kipte kaydi engelleyen eksik; yoksa None."""
        if self.parametrik_kip():
            return None
        yog = self.yogunluk.deger()
        if yog is None or yog <= 0:
            return "Yoğunluk pozitif bir sayı olmalı."
        if not self.model.bilesim:
            return "Bileşime en az bir satır ekleyin."
        for i, b in enumerate(self.model.bilesim, start=1):
            if not (b.get("isim") or "").strip():
                return "Bileşimin %d. satırında isim boş." % i
            if float(b.get("miktar") or 0.0) <= 0:
                return "Bileşimin %d. satırında miktar pozitif olmalı." % i
        return None

    def _onayla(self):
        if not self._dogrula():
            return
        sorun = self.icerik_sorunu()
        self.hata.setText(sorun or "")
        self.hata.setVisible(bool(sorun))
        if sorun is None:
            self.accept()

    def sonuc(self):
        ad = self.ad.text()
        if self.parametrik_kip():
            m = self.form.malzeme()
            m["ad"] = ad
            m["renk"] = list(self.renk.rgb())
            for k, v in self._orijinal.items():     # bilinmeyen alanlar korunur
                if k not in m:
                    m[k] = copy.deepcopy(v)
            return m
        m = copy.deepcopy(self._orijinal)
        m.pop("kutup", None)
        m["ad"] = ad
        m["gorunen_ad"] = self.aciklama.text().strip() or ad
        m["yogunluk"] = {"birim": self.birim.currentData(), "deger": self.yogunluk.deger()}
        v = self.sicaklik.value()
        m["sicaklik"] = self._ilk_sicaklik if v == self._ilk_sicaklik_gosterim else v
        m["bilesim"] = copy.deepcopy(self.model.bilesim)
        m["sab"] = list(self._sab)
        m["renk"] = list(self.renk.rgb())
        return m


# ============================================================================
# Sekme
# ============================================================================

class MalzemeSekmesi(SekmeTabani):
    """Malzeme listesi sekmesi."""

    KONU = "malzeme"

    BASLIKLAR = ["Renk", "Ad", "Açıklama", "Rol", "Yoğunluk", "Sıcaklık",
                 "S(α,β)", "Bileşim"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._secim_adi = None

        self.tablo = QtWidgets.QTableWidget(0, len(self.BASLIKLAR))
        self.tablo.setHorizontalHeaderLabels(self.BASLIKLAR)
        self.tablo.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tablo.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tablo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.doubleClicked.connect(self._duzenle)
        self.tablo.itemSelectionChanged.connect(self._dugmeleri_guncelle)

        self.d_kutup = QtWidgets.QPushButton("Kütüphaneden ekle…")
        self.d_kutup.setObjectName("birincil")
        self.d_yeni = QtWidgets.QPushButton("Elle tanımla…")
        self.d_yeni.setToolTip("Bileşimi element/izotop satırlarıyla kendiniz girin.")
        self.d_duzenle = QtWidgets.QPushButton("Düzenle…")
        self.d_kopya = QtWidgets.QPushButton("Kopyala")
        self.d_sil = QtWidgets.QPushButton("Sil")
        self.d_kutup.clicked.connect(self._kutuphaneden)
        self.d_yeni.clicked.connect(self._yeni)
        self.d_duzenle.clicked.connect(self._duzenle)
        self.d_kopya.clicked.connect(self._kopyala)
        self.d_sil.clicked.connect(self._sil)

        # Iki satir: editor paneli dar (onizlemenin yaninda ~250 px); tek
        # satirda Duzenle/Kopyala/Sil yatay kaydirmanin arkasina dusuyordu.
        dugmeler = QtWidgets.QVBoxLayout()
        ekle_satir = QtWidgets.QHBoxLayout()
        for d in (self.d_kutup, self.d_yeni):
            ekle_satir.addWidget(d)
        ekle_satir.addStretch(1)
        islem_satir = QtWidgets.QHBoxLayout()
        for d in (self.d_duzenle, self.d_kopya, self.d_sil):
            islem_satir.addWidget(d)
        islem_satir.addStretch(1)
        dugmeler.addLayout(ekle_satir)
        dugmeler.addLayout(islem_satir)

        liste_sayfa = QtWidgets.QWidget()
        ld = QtWidgets.QVBoxLayout(liste_sayfa)
        ld.setContentsMargins(0, 0, 0, 0)
        ld.addWidget(ipucu(
            "Düzenlemek için satıra çift tıklayın. Kütüphaneden eklenen "
            "malzemelerde zenginlik, sıcaklık, bor gibi değerler sonradan "
            "değiştirilebilir. 'bosluk' ayrılmış addır: geometride Boş (madde "
            "yok) anlamına gelir, burada tanımlanmaz."))
        ld.addWidget(self.tablo, 1)
        ld.addLayout(dugmeler)

        bos_sayfa = QtWidgets.QWidget()
        bd = QtWidgets.QVBoxLayout(bos_sayfa)
        bd.setContentsMargins(0, 0, 0, 0)
        self.bos = BosDurum(
            "Henüz malzeme yok",
            "Yakıt, zarf ve soğutucuyu hazır kütüphaneden ekleyin. Zenginlik, "
            "sıcaklık ve bor gibi değerleri sonradan değiştirebilirsiniz.",
            "Kütüphaneden ekle…")
        self.bos.eylem.connect(self._kutuphaneden)
        self.d_bos_elle = QtWidgets.QToolButton()
        self.d_bos_elle.setText("ya da bileşimi elle tanımlayın")
        self.d_bos_elle.setAutoRaise(True)
        self.d_bos_elle.setCursor(QtCore.Qt.PointingHandCursor)
        self.d_bos_elle.clicked.connect(self._yeni)
        bos_duzen = self.bos.layout()
        bos_duzen.insertWidget(bos_duzen.indexOf(self.bos.dugme) + 1,
                               self.d_bos_elle, 0, QtCore.Qt.AlignHCenter)
        bd.addWidget(self.bos, 1)

        self.yigin = QtWidgets.QStackedWidget()
        self.yigin.addWidget(bos_sayfa)
        self.yigin.addWidget(liste_sayfa)

        duzen = QtWidgets.QVBoxLayout(self)
        duzen.addWidget(baslik("Malzemeler"))
        duzen.addWidget(self.yigin, 1)
        self._dugmeleri_guncelle()

    # ------------------------------------------------------------------
    def doldur(self):
        from cekirdek import uygunluk
        malzemeler = self.spec["malzemeler"]
        self.yigin.setCurrentIndex(1 if malzemeler else 0)
        try:
            roller = uygunluk.malzeme_rolleri(self.spec)
        except Exception:
            roller = {}
        self.tablo.blockSignals(True)
        self.tablo.setRowCount(0)
        for m in malzemeler:
            satir = self.tablo.rowCount()
            self.tablo.insertRow(satir)
            renk = QtWidgets.QTableWidgetItem("")
            rgb = m.get("renk") or (170, 170, 170)
            renk.setBackground(QtGui.QColor(*[int(x) for x in rgb]))
            self.tablo.setItem(satir, 0, renk)
            rol = [ROL_ETIKETLERI[r] for r in _ROL_SIRASI if r in roller.get(m.get("ad"), ())]
            aciklama = m.get("gorunen_ad") or ""
            degerler = [
                m.get("ad", ""),
                "" if aciklama == m.get("ad") else aciklama,
                ", ".join(rol),
                yogunluk_metni(m),
                sicaklik_metni(m.get("sicaklik")),
                ", ".join(m.get("sab") or []) or "—",
                bilesim_ozeti(m),
            ]
            for i, d in enumerate(degerler, start=1):
                oge = QtWidgets.QTableWidgetItem(str(d))
                if i == 1:
                    oge.setToolTip("Kütüphaneden (%s) — Düzenle parametre formunu açar"
                                   % mk.okunur_ad(m["kutup"]["anahtar"])
                                   if mk.parametrik_mi(m) else "Elle tanımlı bileşim")
                self.tablo.setItem(satir, i, oge)
        self.tablo.resizeColumnsToContents()
        # Sutun genisligi baslik metnini ("Renk") de kapsamali.
        self.tablo.setColumnWidth(0, 52)
        self.tablo.verticalHeader().setDefaultSectionSize(26)
        # secim korunur (ad ile): duzenlemeden sonra ayni satir secili kalir
        adlar = [m.get("ad") for m in malzemeler]
        self.tablo.clearSelection()
        if self._secim_adi in adlar:
            self.tablo.selectRow(adlar.index(self._secim_adi))
        self.tablo.blockSignals(False)
        self._dugmeleri_guncelle()

    def _dugmeleri_guncelle(self):
        """Duzenle / Kopyala / Sil yalnizca bir satir seciliyken etkin."""
        satir = self._secili_satir()
        for d in (self.d_duzenle, self.d_kopya, self.d_sil):
            d.setEnabled(satir >= 0)
        if self.spec is not None:
            self._secim_adi = self.spec["malzemeler"][satir]["ad"] if satir >= 0 else None

    # ------------------------------------------------------------------
    def _adlar(self):
        return [m["ad"] for m in self.spec["malzemeler"]]

    def _benzersiz(self, taban):
        return _benzersiz_ad(self.spec, taban)

    def _diyalog_calistir(self, d):
        """Diyalogu kosar; kabul edildiyse True. (Testler bunu ezer.)"""
        return d.exec() == QtWidgets.QDialog.Accepted

    def _soru(self, baslik_, metin):
        c = QtWidgets.QMessageBox.question(self, baslik_, metin)
        return c == QtWidgets.QMessageBox.Yes

    def _ekle(self, m):
        self.spec["malzemeler"].append(m)
        self._secim_adi = m["ad"]
        self.spec_yukle(self.spec)
        self.bildir()

    def _kutuphaneden(self):
        d = KutuphaneDiyalog(self.spec, self)
        if self._diyalog_calistir(d):
            self._ekle(d.sonuc())

    def _yeni(self):
        m = sema.malzeme(self._benzersiz("malzeme"), [], 1.0, renk=(170, 170, 170))
        d = MalzemeDiyalog(m, self.spec, self, yeni=True)
        if self._diyalog_calistir(d):
            self._ekle(d.sonuc())

    def _secili_satir(self):
        if not self.spec:
            return -1
        satirlar = self.tablo.selectionModel().selectedRows()
        if not satirlar:
            return -1
        s = satirlar[0].row()
        return s if 0 <= s < len(self.spec["malzemeler"]) else -1

    def _duzenle(self, *_):
        satir = self._secili_satir()
        if satir < 0:
            return
        d = MalzemeDiyalog(self.spec["malzemeler"][satir], self.spec, self)
        if self._diyalog_calistir(d):
            self.duzenlemeyi_uygula(satir, d.sonuc())

    def duzenlemeyi_uygula(self, satir, yeni):
        """
        Diyalog sonucunu 'satir'daki malzemeye yazar. Ad degistiyse spec'teki
        BUTUN referanslar da degisir (sema.malzeme_adini_degistir).
        """
        eski = self.spec["malzemeler"][satir]
        if yeni["ad"] != eski["ad"]:
            ayni = sum(1 for m in self.spec["malzemeler"] if m.get("ad") == eski["ad"])
            if ayni == 1:
                sema.malzeme_adini_degistir(self.spec, eski["ad"], yeni["ad"])
        self.spec["malzemeler"][satir] = yeni
        self._secim_adi = yeni["ad"]
        self.spec_yukle(self.spec)
        self.bildir()

    def _ad_degistir(self, eski, yeni):
        """Geriye uyumluluk: tam ad degisimi sema'dadir."""
        return sema.malzeme_adini_degistir(self.spec, eski, yeni)

    def _kopyala(self):
        satir = self._secili_satir()
        if satir < 0:
            return
        m = copy.deepcopy(self.spec["malzemeler"][satir])
        m["ad"] = self._benzersiz(m["ad"])
        if m.get("gorunen_ad") == self.spec["malzemeler"][satir]["ad"]:
            m["gorunen_ad"] = m["ad"]
        self._ekle(m)

    def _sil(self):
        satir = self._secili_satir()
        if satir < 0:
            return
        ad = self.spec["malzemeler"][satir]["ad"]
        yerler = sema.malzeme_referanslari(self.spec, ad)
        if yerler:
            okunur = []
            for y in yerler:
                o = yol_okunur(y)
                if o not in okunur:
                    okunur.append(o)
            ornek = ", ".join(okunur[:3]) + (" …" if len(okunur) > 3 else "")
            if not self._soru(
                    "Malzeme kullanımda",
                    "'%s' modelde %d yerde kullanılıyor (%s).\n"
                    "Silerseniz bu yerler tanımsız kalır ve model kurulamaz. "
                    "Yine de silinsin mi?" % (ad, len(yerler), ornek)):
                return
        self.spec["malzemeler"].pop(satir)
        self._secim_adi = None
        self.spec_yukle(self.spec)
        self.bildir()
