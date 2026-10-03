# -*- coding: utf-8 -*-
"""
================================================================================
 tukenme_bolme.py  --  Tukenme sayfasi: bolge bolme sihirbazi (v3 Y5)
================================================================================
 Pinleri radyal halkalara, eksenel katmanlari dilimlere boler (Serpent `div`
 esdegeri; Gd pinleri icin). Hesap cekirdek/bolge_bol.py'dedir; bu panel
 yalniz spec["tukenme"]["bolme"] anahtarini okur/yazar ve etkisini gosterir:
   - hangi pin turleri, halka sayisi, halka turu (esit hacim / esit kalinlik /
     disa incelen), eksenel dilim sayisi
   - secili pinin bolme SONRASI kesiti (onizleme)
   - maliyet (ayri tukenme malzemesi sayisi) ve analitik hacim korunumu
 Varsayilan (bolme yok) dosyaya YAZILMAZ.
================================================================================
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from cekirdek import bolge_bol as bb
from cekirdek.ceviri import _
from cekirdek.gunluk import kaydedici
from arayuz.analiz.adlar import aciklama, form_duzeni, renk
from arayuz.ortak import sayi, tamsayi
from arayuz.tasarim import tokenlar

_log = kaydedici(__name__)
A = tokenlar.ARALIK
VARSAYILAN_HALKA = 4            # Gd pini icin makul baslangic (kullanici degistirir)
ONIZLEME_BOYUTU = 200           # px
_KENAR_PAYI = 8                 # px
_DOLGU_ACIKLIGI = 112           # halka dolgusunu birbirinden ayiran QColor.lighter faktoru (%)
_DOLGU_KOYULUGU = 100


class KesitOnizleme(QtWidgets.QWidget):
    """Bir pinin radyal bolgelerini (es merkezli daireler) cizer; bolunmus halkalar
    ayni malzeme renginin tonlari olarak ayirt edilir."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._halkalar: List[bb.Halka] = []
        self._renkler: Dict[str, Optional[tuple]] = {}
        self.setMinimumSize(ONIZLEME_BOYUTU, ONIZLEME_BOYUTU)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.setAccessibleName(_("Çubuk kesiti önizlemesi"))

    def ayarla(self, halkalar: List[bb.Halka], renkler: Dict[str, Optional[tuple]]) -> None:
        self._halkalar = list(halkalar)
        self._renkler = dict(renkler)
        self.update()

    @property
    def halkalar(self) -> List[bb.Halka]:
        return list(self._halkalar)

    def _dolgu(self, h: bb.Halka, sira: int) -> QtGui.QColor:
        rgb = self._renkler.get(h.malzeme)
        taban = QtGui.QColor(*rgb) if rgb else QtGui.QColor(renk("yuzey3"))
        if h.bolunmus and sira % 2:
            return taban.lighter(_DOLGU_ACIKLIGI + 8)
        return taban.darker(_DOLGU_KOYULUGU + 12) if h.bolunmus else taban

    def paintEvent(self, _olay: QtGui.QPaintEvent) -> None:        # noqa: N802 (Qt API)
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        sonlu = [h for h in self._halkalar if h.r_dis is not None]
        if not sonlu:
            return
        r_en_cok = max(h.r_dis for h in sonlu)
        yaricap = min(self.width(), self.height()) / 2.0 - _KENAR_PAYI
        merkez = QtCore.QPointF(self.width() / 2.0, self.height() / 2.0)
        p.setPen(QtGui.QPen(QtGui.QColor(renk("kenar_guclu")), 1))
        for sira, h in reversed(list(enumerate(sonlu))):         # distan ice
            r = yaricap * h.r_dis / r_en_cok
            p.setBrush(self._dolgu(h, sira))
            p.drawEllipse(merkez, r, r)
        p.end()


class TukenmeBolme(QtWidgets.QWidget):
    """Bolme sihirbazi paneli. degisti: kullanici bir ayari degistirdi."""

    degisti = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._yukleniyor = False
        self._spec: Optional[dict] = None
        self._adaylar: List[str] = []
        self._hata: Optional[str] = None
        self._kur()

    # ------------------------------------------------------------------
    def _kur(self) -> None:
        self.etkin = QtWidgets.QCheckBox(_("Yanma bölgelerini böl (halka / eksenel dilim)"))
        self.etkin.setToolTip(_(
            "Pin tek ortalama bileşimle değil, halka halka ve dilim dilim ayrı yanar. "
            "Yanabilir zehirli (Gd) pinde dış halka önce yanar; ortalama bileşim bunu "
            "kaçırır. Her parça ayrı bir tükenme malzemesidir (çubuk çubuk yanma "
            "otomatik açılır) ve süre/bellek parça sayısıyla artar."))
        self.bilgi = aciklama(_(
            "Gd pini için eşit hacimli halkalar iyi bir başlangıçtır (dış halkalar ince "
            "kalır). Halka ve dilim sayısını artırınca k(t) ve Gd eğrisi yakınsar; "
            "yakınsamayı küçük bir modelde sınayın."))
        self.tablo = QtWidgets.QTableWidget(0, 3)
        self.tablo.setHorizontalHeaderLabels([_("Çubuk"), _("Halka sayısı"), _("Halka türü")])
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.horizontalHeader().setStretchLastSection(True)
        self.tablo.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tablo.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tablo.setMaximumHeight(160)
        self.oran = sayi(bb.INCELME_ORANI, 2, bb.INCELME_ARALIGI[0], bb.INCELME_ARALIGI[1], 0.05)
        self.oran.setToolTip(_(
            "Dışa doğru incelen halkalarda her halkanın kalınlığı bir içerdekinin bu kadarıdır. "
            "Bir mühendislik tercihidir, ölçülmüş bir eşik değildir."))
        self.dilim = tamsayi(1, 1, bb.MAKS_DILIM)
        self.dilim.setToolTip(_(
            "Yanabilir katmanlar bu kadar eşit dilime bölünür (3B model gerekir). 1: bölme yok."))
        self.dilim_not = aciklama("")
        self.secili = QtWidgets.QComboBox()
        self.secili.setToolTip(_("Önizlemede gösterilen çubuk"))
        self.onizleme = KesitOnizleme()
        self.ozet = QtWidgets.QLabel("")
        self.ozet.setWordWrap(True)
        self.ozet.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        form = form_duzeni()
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow(self.etkin)
        form.addRow(self.bilgi)
        form.addRow(_("Çubuk türleri:"), self.tablo)
        form.addRow(_("İncelme oranı:"), self.oran)
        form.addRow(_("Eksenel dilim:"), self.dilim)
        form.addRow("", self.dilim_not)
        form.addRow(_("Önizleme:"), self.secili)
        form.addRow("", self.onizleme)
        form.addRow("", self.ozet)
        self.form = form
        self.setLayout(form)
        self.etkin.toggled.connect(self._degisti)
        self.oran.valueChanged.connect(self._degisti)
        self.dilim.valueChanged.connect(self._degisti)
        self.secili.currentIndexChanged.connect(self._guncelle)
        self.tablo.itemChanged.connect(self._degisti)

    # ------------------------------------------------------------------
    def _satir_ekle(self, ad: str, secili: bool, halka: int, tur: str) -> None:
        i = self.tablo.rowCount()
        self.tablo.insertRow(i)
        oge = QtWidgets.QTableWidgetItem(ad)
        oge.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        oge.setCheckState(QtCore.Qt.Checked if secili else QtCore.Qt.Unchecked)
        self.tablo.setItem(i, 0, oge)
        n = tamsayi(halka, 1, bb.MAKS_HALKA)
        n.valueChanged.connect(self._degisti)
        self.tablo.setCellWidget(i, 1, n)
        kutu = QtWidgets.QComboBox()
        for kod, metin in bb.TURLER.items():
            kutu.addItem(_(metin), kod)
        kutu.setCurrentIndex(max(kutu.findData(tur), 0))
        kutu.currentIndexChanged.connect(self._degisti)
        self.tablo.setCellWidget(i, 2, kutu)

    def doldur(self, spec: dict) -> None:
        self._yukleniyor = True
        try:
            self._spec = spec
            t = spec.get("tukenme") or {}
            try:
                bolme = bb.bolme_oku(spec)
                hata = None
            except ValueError as e:
                bolme, hata = None, str(e)
            mevcut = {h.cubuk: h for h in (bolme.cubuklar if bolme else ())}
            self._adaylar = bb.yanabilir_cubuklar(spec)
            self.tablo.setRowCount(0)
            for ad in self._adaylar:
                h = mevcut.get(ad)
                self._satir_ekle(ad, h is not None and h.halka > 1,
                                 h.halka if h else VARSAYILAN_HALKA,
                                 h.tur if h else bb.VARSAYILAN_TUR)
            self.etkin.setChecked(bool(t.get("bolme")))
            self.oran.setValue(next((h.oran for h in mevcut.values()), bb.INCELME_ORANI))
            self.dilim.setValue(bolme.eksenel_dilim if bolme else 1)
            self.secili.blockSignals(True)
            self.secili.clear()
            for ad in self._adaylar:
                self.secili.addItem(ad, ad)
            self.secili.blockSignals(False)
            self._hata = hata
        finally:
            self._yukleniyor = False
        self._guncelle()

    # ------------------------------------------------------------------
    def bolme(self) -> Optional[bb.Bolme]:
        """Arayuzdeki secimden Bolme; etkin degil ya da secim yoksa None."""
        if not self.etkin.isChecked():
            return None
        cubuklar = []
        for i, ad in enumerate(self._adaylar):
            if self.tablo.item(i, 0).checkState() != QtCore.Qt.Checked:
                continue
            cubuklar.append(bb.HalkaBolme(
                ad, self.tablo.cellWidget(i, 1).value(), self.tablo.cellWidget(i, 2).currentData(),
                None, self.oran.value()))
        b = bb.Bolme(tuple(cubuklar), self.dilim.value())
        return b if b.var else None

    def yaz(self, t: Dict[str, Any]) -> None:
        """Arayuz -> spec['tukenme'] (yerinde; sekme _kaydet'i cagirir). Bolme yoksa
        anahtar yazilmaz (varsa kaldirilir)."""
        b = self.bolme()
        if b is not None:
            t[bb.ANAHTAR] = bb.yazilacak(b)
        elif bb.ANAHTAR in t and not self._yukleniyor:
            t.pop(bb.ANAHTAR)

    def _degisti(self, *_a: Any) -> None:
        if self._yukleniyor:
            return
        self._guncelle()
        self.degisti.emit()

    # ------------------------------------------------------------------
    def _renkler(self) -> Dict[str, Optional[tuple]]:
        return {m["ad"]: tuple(m["renk"]) if m.get("renk") else None
                for m in (self._spec or {}).get("malzemeler") or []}

    def _guncelle(self, *_a: Any) -> None:
        spec = self._spec
        gorunur = spec is not None and bool(self._adaylar)
        self.setEnabled(True)
        self.tablo.setEnabled(self.etkin.isChecked() and gorunur)
        self.oran.setEnabled(self.etkin.isChecked() and any(
            self.tablo.cellWidget(i, 2).currentData() == bb.DISTA_INCELEN
            for i in range(self.tablo.rowCount())))
        agac = spec is not None and (spec.get("kor") or {}).get("tur") == "agac"
        uc_boyut = bool(spec) and not agac and bool(
            (spec["kor"].get("eksenel") or {}).get("var") or spec["kor"].get("yukseklik"))
        self.dilim.setEnabled(self.etkin.isChecked() and uc_boyut)
        self.dilim_not.setText("" if uc_boyut else (
            _("Gelişmiş (ağaç) modda bölme desteklenmiyor.") if agac
            else _("Eksenel dilim için 3B model (yükseklik ya da eksenel katmanlar) gerekir.")))
        self.etkin.setEnabled(not agac and (gorunur or uc_boyut))
        self.ozet.setStyleSheet("")
        if not self.etkin.isChecked() or spec is None:
            self.onizleme.ayarla([], {})
            self.ozet.setText("")
            return
        self._onizle_ve_ozetle(spec)

    def _bolunmus_spec(self, spec: dict) -> Optional[dict]:
        b = self.bolme()
        if b is None:
            return None
        s = copy.deepcopy(spec)
        s.setdefault("tukenme", {})[bb.ANAHTAR] = bb.yazilacak(b)
        return s

    def _onizle_ve_ozetle(self, spec: dict) -> None:
        s = self._bolunmus_spec(spec)
        if s is None:
            self.onizleme.ayarla([], {})
            self.ozet.setText(_("Bölme için en az bir çubuk türü seçin ya da eksenel dilim ≥ 2 verin."))
            return
        try:
            secili = self.secili.currentData() or (self._adaylar[0] if self._adaylar else None)
            self.onizleme.ayarla(list(bb.kesit_onizleme(s, secili)) if secili else [],
                                 self._renkler())
            once, sonra = bb.ornek_sayilari(s)
            denetim = bb.halka_hacim_denetimi(s)
            en_buyuk = max((d["goreli_hata"] for d in denetim), default=0.0)
            metin = _("Ayrı tükenme malzemesi: %d → %d (süre ve bellek buna göre artar).") % (
                once, sonra)
            if denetim:
                metin += "\n" + _("Halka hacimlerinin toplamı analitik hacme eşit (en büyük "
                                  "bağıl sapma %.1e).") % en_buyuk
            self.ozet.setText(metin)
        except ValueError as e:
            self.onizleme.ayarla([], {})
            self.ozet.setText(str(e))
            self.ozet.setStyleSheet("color: %s;" % renk("hata"))
        except Exception as e:                                   # geometri sayimi vb.
            _log.warning("bölme özeti hesaplanamadı", exc_info=True)
            self.ozet.setText(_("Özet hesaplanamadı: %s") % e)
            self.ozet.setStyleSheet("color: %s;" % renk("hata"))
