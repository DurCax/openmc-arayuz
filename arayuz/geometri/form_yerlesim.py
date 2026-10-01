# -*- coding: utf-8 -*-
"""
================================================================================
 arayuz/geometri/form_yerlesim.py  --  Yerlesim ve grup formlari (§3.8, §3.10)
================================================================================
 YerlesimFormu: ad, mod (halka / liste / kafes konumu), ornek alanlari, delik
                kesiti (dogal: tambur dairesi), "kora bakis" (merkeze / sabit /
                yok), donme grubu uyeligi ve ofset. Tambur ve kontrol kanali ayni
                mekanizmayla her geometride yerlesir.
 GrupFormu    : ad, tur (Donme / Daldirma), deger (kutu + kaydirici), uyeler.
                Deger YALNIZ grupta tutulur (tek kaynak); bir uye ayni turden en
                cok bir gruptadir (§15 karar 5: her kontrol cubugu ayri ornek,
                grup yalniz birden cok cubugu birlikte surmek icindir).
================================================================================
"""

from PySide6 import QtCore, QtWidgets

from cekirdek.ceviri import N_, _
from arayuz import bilesenler as b
from arayuz.geometri import duzenle
from arayuz.geometri.form_ortak import (FormTabani, KesitEditoru, aci, form_duzeni,
                                        kutu_doldur, sayi_yaz, uzunluk)
from arayuz.ortak import ipucu

MOD_ADLARI = {"halka": N_("Halka (eşit aralıklı)"), "liste": N_("Liste (x, y)"),
              "kafes_konumu": N_("Kafes konumu (harf)")}
_KAYDIRICI = 3600            # 0.1 derece / %0.1 adim


def _tambur_mu(spec, icerik):
    ad = (icerik or {}).get("ad") if isinstance(icerik, dict) else icerik
    return any(t.get("ad") == ad for t in spec.get("tamburlar") or [])


class YerlesimFormu(FormTabani):
    BASLIK = N_("Yerleşim")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ad = QtWidgets.QLineEdit()
        self.ad.setAccessibleName(_("yerleşim adı"))
        self.mod = QtWidgets.QComboBox()
        for k, v in MOD_ADLARI.items():
            self.mod.addItem(_(v), k)
        self.sayi = QtWidgets.QSpinBox()
        self.sayi.setRange(1, 360)
        self.merkez_r = uzunluk(10.0, 0.0, _("merkez yarıçapı"))
        self.baslangic = aci(0.0, _("başlangıç açısı"))
        self.konumlar = QtWidgets.QTableWidget(0, 2)
        self.konumlar.setHorizontalHeaderLabels([_("x [cm]"), _("y [cm]")])
        self.konumlar.horizontalHeader().setStretchLastSection(True)
        self.konumlar.verticalHeader().setVisible(False)
        self.konumlar.setMaximumHeight(8 * tokens_satir())
        self.d_konum_ekle = b.duz_dugme(_("+ Konum"), None)
        self.d_konum_sil = b.duz_dugme(_("Sil"), "trash")
        self.kafes = QtWidgets.QComboBox()
        self.harf = QtWidgets.QComboBox()
        self.dogal = QtWidgets.QCheckBox(_("Doğal kesit (tambur dairesi)"))
        self.kesit = KesitEditoru()
        self.bakis = b.SegmentSecici([("merkez", _("Merkeze")), ("sabit", _("Sabit")),
                                      ("yok", _("Yok"))], "merkez")
        self.bakis_x = uzunluk(0.0, -1e5, _("bakış merkezi x"))
        self.bakis_y = uzunluk(0.0, -1e5, _("bakış merkezi y"))
        self.bakis_aci = aci(0.0, _("sabit bakış açısı"))
        self.grup = QtWidgets.QComboBox()
        self.grup.setAccessibleName(_("dönme grubu"))
        self.ofset = aci(0.0, _("dönme ofseti"))
        self._kur()
        self._bagla()

    def _kur(self):
        f = form_duzeni(self)
        f.addRow(_("Ad"), self.ad)
        f.addRow(_("Mod"), self.mod)
        f.addRow(_("Sayı"), self.sayi)
        f.addRow(_("Merkez yarıçapı"), self.merkez_r)
        f.addRow(_("Başlangıç açısı"), self.baslangic)
        self.konum_kutusu = QtWidgets.QWidget()
        kd = QtWidgets.QVBoxLayout(self.konum_kutusu)
        kd.setContentsMargins(0, 0, 0, 0)
        kd.addWidget(self.konumlar)
        dugmeler = QtWidgets.QWidget()
        dd = QtWidgets.QHBoxLayout(dugmeler)
        dd.setContentsMargins(0, 0, 0, 0)
        dd.addWidget(self.d_konum_ekle)
        dd.addWidget(self.d_konum_sil)
        dd.addStretch(1)
        kd.addWidget(dugmeler)
        f.addRow(_("Konumlar"), self.konum_kutusu)
        f.addRow(_("Kafes"), self.kafes)
        f.addRow(_("Harf"), self.harf)
        f.addRow(b.BolumBasligi(_("Delik kesiti")))
        f.addRow(self.dogal)
        f.addRow(self.kesit)
        f.addRow(b.BolumBasligi(_("Kora bakış"),
                                _("İçeriğin ön yüzü (tamburda emici) yerel +x'tir.")))
        f.addRow(self.bakis)
        f.addRow(_("Merkez x"), self.bakis_x)
        f.addRow(_("Merkez y"), self.bakis_y)
        f.addRow(_("Açı"), self.bakis_aci)
        f.addRow(_("Grup"), self.grup)
        f.addRow(_("Ofset"), self.ofset)
        f.addRow(ipucu(_("Dönme = grup değeri + ofset. 0° emici kora bakar (daldırılmış), "
                         "180° dışa bakar (çekilmiş).")))
        self._form = f

    def _bagla(self):
        self.ad.editingFinished.connect(self._ad_degisti)
        self.mod.currentIndexChanged.connect(self._kaydet)
        self.sayi.valueChanged.connect(self._kaydet)
        for w in (self.merkez_r, self.baslangic, self.bakis_x, self.bakis_y,
                  self.bakis_aci, self.ofset):
            w.degisti.connect(self._kaydet)
        self.konumlar.itemChanged.connect(self._kaydet)
        self.d_konum_ekle.clicked.connect(self._konum_ekle)
        self.d_konum_sil.clicked.connect(self._konum_sil)
        self.kafes.currentIndexChanged.connect(self._kafes_degisti)
        self.harf.currentIndexChanged.connect(self._kaydet)
        self.dogal.toggled.connect(self._kaydet)
        self.kesit.degisti.connect(self._kaydet)
        self.bakis.secildi.connect(lambda _k: self._kaydet())
        self.grup.currentIndexChanged.connect(self._grup_degisti)

    # ------------------------------------------------------------------
    def doldur(self, y):
        self.ad.setText(y.get("ad") or "")
        kutu_doldur(self.mod, [(k, _(v)) for k, v in MOD_ADLARI.items()], y.get("mod"))
        self.sayi.setValue(int(y.get("sayi") or 1))
        sayi_yaz(self.merkez_r, y.get("merkez_yaricap") or 0.0)
        sayi_yaz(self.baslangic, y.get("baslangic_acisi") or 0.0)
        self._konumlari_doldur(y.get("konumlar") or [])
        kafesler = self._kafesler()
        kutu_doldur(self.kafes, [(k, k) for k in kafesler], y.get("kafes"))
        self._harfleri_doldur(y.get("harf"))
        tambur = _tambur_mu(self.spec, y.get("icerik"))
        self.dogal.setEnabled(tambur)
        self.dogal.setChecked(y.get("kesit") is None)
        self.kesit.ayarla(y.get("kesit") or {"sekil": "silindir", "yaricap": 1.0})
        bakis = y.get("bakis") or ({"tur": "merkez", "merkez": [0.0, 0.0]} if tambur else None)
        self.bakis.sec((bakis or {}).get("tur", "yok"), sinyal=False)
        merkez = (bakis or {}).get("merkez") or (0.0, 0.0)
        sayi_yaz(self.bakis_x, merkez[0])
        sayi_yaz(self.bakis_y, merkez[1])
        sayi_yaz(self.bakis_aci, (bakis or {}).get("aci") or 0.0)
        gruplar = [g for g in self.agac.get("gruplar") or [] if g.get("tur") == "donme"]
        uye = next((g["ad"] for g in gruplar if y.get("ad") in (g.get("uyeler") or [])), None)
        kutu_doldur(self.grup, [(None, _("(grup yok)"))] + [(g["ad"], g["ad"]) for g in gruplar],
                    uye)
        sayi_yaz(self.ofset, y.get("donme_ofset") or 0.0)
        self._gorunurluk()

    def _konumlari_doldur(self, konumlar):
        eski = self.konumlar.blockSignals(True)
        try:
            self.konumlar.setRowCount(len(konumlar))
            for i, (x, yy) in enumerate(konumlar):
                for j, v in enumerate((x, yy)):
                    self.konumlar.setItem(i, j, QtWidgets.QTableWidgetItem("%g" % float(v)))
        finally:
            self.konumlar.blockSignals(eski)

    def _kafesler(self):
        kap = duzenle.al(self.agac, duzenle.kap_yolu(self.agac, self.yol[:-2]) or ())
        adaylar = [kap.get("ic")] + [h.get("icerik") for h in (kap or {}).get("halkalar") or []] \
            if isinstance(kap, dict) else []
        cikti = []
        for a in adaylar:
            if isinstance(a, dict) and a.get("tur") == "eksenel":
                a = a.get("icerik")
            if isinstance(a, dict) and a.get("tur") == "kafes" and a.get("id"):
                cikti.append(a["id"])
        return cikti

    def _harfleri_doldur(self, secili):
        kap = duzenle.al(self.agac, duzenle.kap_yolu(self.agac, self.yol[:-2]) or ())
        harfler = []
        for a in ([kap.get("ic")] + [h.get("icerik") for h in kap.get("halkalar") or []]
                  if isinstance(kap, dict) else []):
            if isinstance(a, dict) and a.get("tur") == "eksenel":
                a = a.get("icerik")
            if isinstance(a, dict) and a.get("id") == self.kafes.currentData():
                harfler = sorted({h for s in a.get("harita") or [] for h in s if h != "."})
        eski = self.harf.blockSignals(True)
        kutu_doldur(self.harf, [(h, h) for h in harfler], secili)
        self.harf.blockSignals(eski)

    def _gorunurluk(self):
        mod = self.mod.currentData()
        bakis = self.bakis.secili()
        for w, g in ((self.sayi, mod == "halka"), (self.merkez_r, mod == "halka"),
                     (self.baslangic, mod == "halka"), (self.konum_kutusu, mod == "liste"),
                     (self.kafes, mod == "kafes_konumu"), (self.harf, mod == "kafes_konumu"),
                     (self.kesit, not (self.dogal.isChecked() and self.dogal.isEnabled())),
                     (self.bakis_x, bakis == "merkez"), (self.bakis_y, bakis == "merkez"),
                     (self.bakis_aci, bakis == "sabit")):
            self._form.setRowVisible(w, g)

    # ------------------------------------------------------------------
    def yerlesim(self):
        """Formdan YENI yerlesim sozlugu (ad ve icerik korunur)."""
        y = {k: v for k, v in (self.oge() or {}).items()
             if k in ("ad", "icerik")}
        mod = self.mod.currentData()
        y["mod"] = mod
        if mod == "halka":
            y.update(sayi=self.sayi.value(), merkez_yaricap=self.merkez_r.deger(),
                     baslangic_acisi=self.baslangic.deger())
        elif mod == "liste":
            y["konumlar"] = self._konumlar()
        else:
            y.update(kafes=self.kafes.currentData(), harf=self.harf.currentData())
        y["kesit"] = (None if self.dogal.isChecked() and self.dogal.isEnabled()
                      else self.kesit.kesit())
        bakis = self.bakis.secili()
        if bakis == "merkez":
            y["bakis"] = {"tur": "merkez", "merkez": [self.bakis_x.deger(), self.bakis_y.deger()]}
        elif bakis == "sabit":
            y["bakis"] = {"tur": "sabit", "aci": self.bakis_aci.deger()}
        if self.ofset.deger():
            y["donme_ofset"] = self.ofset.deger()
        return y

    def _konumlar(self):
        cikti = []
        for i in range(self.konumlar.rowCount()):
            try:
                cikti.append([float(self.konumlar.item(i, j).text()) for j in (0, 1)])
            except (AttributeError, ValueError):
                cikti.append([0.0, 0.0])
        return cikti

    def _kaydet(self, *_a):
        if self._yukleniyor:
            return
        self._gorunurluk()
        self.agac_yay(duzenle.yaz(self.agac, self.yol, self.yerlesim()))

    def _ad_degisti(self):
        if self._yukleniyor:
            return
        yeni = self.ad.text().strip()
        if yeni == (self.oge() or {}).get("ad"):
            return
        try:
            self.agac_yay(duzenle.yeniden_adlandir(self.agac, self.yol, yeni))
        except duzenle.DuzenlemeHatasi as e:
            self.ad.setText((self.oge() or {}).get("ad") or "")
            self.ad.setToolTip(str(e))

    def _kafes_degisti(self, *_a):
        if self._yukleniyor:
            return
        self._harfleri_doldur(None)
        self._kaydet()

    def _konum_ekle(self):
        self.konumlar.insertRow(self.konumlar.rowCount())
        for j in (0, 1):
            self.konumlar.setItem(self.konumlar.rowCount() - 1, j,
                                  QtWidgets.QTableWidgetItem("0"))
        self._kaydet()

    def _konum_sil(self):
        r = self.konumlar.currentRow()
        if r >= 0:
            self.konumlar.removeRow(r)
            self._kaydet()

    def _grup_degisti(self, *_a):
        if self._yukleniyor:
            return
        ad = (self.oge() or {}).get("ad")
        hedef = self.grup.currentData()
        yeni = duzenle.yaz(self.agac, ("gruplar",), [
            dict(g, uyeler=[u for u in g.get("uyeler") or [] if u != ad]
                 + ([ad] if g.get("ad") == hedef else []))
            if g.get("tur") == "donme" else g
            for g in self.agac.get("gruplar") or []]) if self.agac.get("gruplar") is not None \
            else self.agac
        self.agac_yay(yeni)


def tokens_satir():
    from arayuz.tasarim import tokenlar
    return tokenlar.ARALIK["xl"]


class GrupFormu(FormTabani):
    """Grup: ad, tur, deger (+ kaydirici), uyeler (onay listesi)."""

    BASLIK = N_("Grup")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ad = QtWidgets.QLineEdit()
        self.tur = b.SegmentSecici([("donme", _("Dönme")), ("daldirma", _("Daldırma"))],
                                   "donme")
        self.deger = b.SayiBirim("°", deger=0.0, en_az=-360.0, en_cok=360.0, ondalik=2,
                                 adim=5.0, erisilebilir_ad=_("grup değeri"))
        self.kaydirici = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.kaydirici.setRange(0, _KAYDIRICI)
        self.uyeler = QtWidgets.QListWidget()
        self.uyeler.setMaximumHeight(8 * tokens_satir())
        self.aciklama = ipucu("")
        f = form_duzeni(self)
        f.addRow(_("Ad"), self.ad)
        f.addRow(_("Tür"), self.tur)
        f.addRow(_("Değer"), self.deger)
        f.addRow("", self.kaydirici)
        f.addRow(_("Üyeler"), self.uyeler)
        f.addRow(self.aciklama)
        self.ad.editingFinished.connect(self._ad_degisti)
        self.tur.secildi.connect(self._tur_degisti)
        self.deger.degisti.connect(self._deger_degisti)
        self.kaydirici.valueChanged.connect(self._kaydirici_degisti)
        self.uyeler.itemChanged.connect(self._uyeler_degisti)

    def _adaylar(self, tur):
        if tur == "donme":
            return duzenle.yerlesim_adlari(self.agac)
        return [c["ad"] for c in self.spec.get("cubuklar") or [] if c.get("tur") == "kontrol"]

    def doldur(self, g):
        tur = g.get("tur", "donme")
        self.ad.setText(g.get("ad") or "")
        self.tur.sec(tur, sinyal=False)
        birim_max = 360.0 if tur == "donme" else 1.0e5
        self.deger.kutu.setRange(-birim_max if tur == "donme" else 0.0, birim_max)
        sayi_yaz(self.deger, g.get("deger") or 0.0)
        self._kaydirici_yaz(float(g.get("deger") or 0.0), tur)
        eski = self.uyeler.blockSignals(True)
        try:
            self.uyeler.clear()
            uyeler = set(g.get("uyeler") or [])
            for ad in self._adaylar(tur):
                oge = QtWidgets.QListWidgetItem(ad)
                oge.setFlags(oge.flags() | QtCore.Qt.ItemIsUserCheckable)
                oge.setCheckState(QtCore.Qt.Checked if ad in uyeler else QtCore.Qt.Unchecked)
                self.uyeler.addItem(oge)
        finally:
            self.uyeler.blockSignals(eski)
        self.aciklama.setText(
            _("Üyeler yerleşim adlarıdır; yerleşimin bütün örnekleri birlikte döner.")
            if tur == "donme" else
            _("Üyeler kontrol çubuğu tanımlarıdır; her çubuk ayrı bir örnektir, grup "
              "yalnız birlikte sürmek içindir. Değer: daldırma derinliği [cm]."))

    def _kaydirici_yaz(self, deger, tur):
        eski = self.kaydirici.blockSignals(True)
        if tur == "donme":
            self.kaydirici.setRange(0, _KAYDIRICI)
            self.kaydirici.setValue(int(round(deger * 10)) % _KAYDIRICI)
        else:
            self.kaydirici.setRange(0, 10000)
            self.kaydirici.setValue(int(round(deger * 10)))
        self.kaydirici.blockSignals(eski)

    def _ad_degisti(self):
        if self._yukleniyor or self.ad.text().strip() == (self.oge() or {}).get("ad"):
            return
        try:
            self.agac_yay(duzenle.yeniden_adlandir(self.agac, self.yol, self.ad.text()))
        except duzenle.DuzenlemeHatasi as e:
            self.ad.setText((self.oge() or {}).get("ad") or "")
            self.ad.setToolTip(str(e))

    def _tur_degisti(self, tur):
        yeni = duzenle.alan_yaz(self.agac, self.yol, "tur", tur)
        self.agac_yay(duzenle.alan_yaz(yeni, self.yol, "uyeler", []))
        self._yukleniyor = True
        try:
            self.doldur(self.oge())
        finally:
            self._yukleniyor = False

    def _deger_degisti(self, deger):
        if self._yukleniyor:
            return
        self._kaydirici_yaz(deger, self.tur.secili())
        self._degeri_yaz(float(deger))

    def _kaydirici_degisti(self, deger):
        if self._yukleniyor:
            return
        v = deger / 10.0
        sayi_yaz(self.deger, v)
        self._degeri_yaz(v)

    def _degeri_yaz(self, deger):
        """geometri.grup_degeri_yaz (duzenle uzerinden); tek geri al adimi."""
        g = self.oge() or {}
        try:
            self.agac_yay(duzenle.grup_degeri_yaz(self.agac, g.get("ad"), deger))
        except duzenle.DuzenlemeHatasi as e:
            self.aciklama.setText(str(e))

    def _uyeler_degisti(self, *_a):
        uyeler = [self.uyeler.item(i).text() for i in range(self.uyeler.count())
                  if self.uyeler.item(i).checkState() == QtCore.Qt.Checked]
        self.yaz("uyeler", uyeler)
