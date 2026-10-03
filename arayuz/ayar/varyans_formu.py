# -*- coding: utf-8 -*-
"""
 arayuz/ayar/varyans_formu.py  --  Hesap ayarlari > Gelismis: varyans azaltma (agirlik
                                   penceresi) formu (Y9)

 spec["ayarlar"]["varyans"] (cekirdek/varyans.py) alanlarini yazar. Dolduruken spec'e
 dokunulmaz; kapali ve hic yazilmamis ayar spec'e alan EKLEMEZ (onbellek kimligi korunur).
 Kapatinca ayar {"var": False, ...} olarak kalir: kullanicinin girdigi degerler kaybolmaz.
"""

import os

from PySide6 import QtCore, QtWidgets

from arayuz.ortak import ipucu, sayi, tamsayi
from cekirdek import varyans
from cekirdek.ceviri import N_, _
from cekirdek.gunluk import kaydedici

_log = kaydedici(__name__)

_MOD_ADLARI = {"uret": N_("Pencere üret (analog koşu; weight_windows.h5 yazar)"),
               "uret_uygula": N_("Üret ve aynı koşuda uygula (koşu sırasında öğrenir)"),
               "uygula": N_("Hazır pencere dosyasını uygula (.h5 ya da wwinp)")}
_AG_ADLARI = {"duzenli": N_("Düzenli (x, y, z)"), "kuresel": N_("Küresel (r, θ, φ)")}
_DOSYA_SUZGECI = N_("Ağırlık pencereleri (*.h5 *.wwinp wwinp*);;Tüm dosyalar (*)")


def _enerji_metni(deger) -> str:
    return ", ".join("%g" % float(v) for v in deger or [])


class VaryansFormu(QtWidgets.QWidget):
    """Agirlik penceresi (MAGIC) ayarlari."""

    degisti = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._spec = None
        self._yukleniyor = False
        self._alanlari_kur()
        form = QtWidgets.QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        self._form = form
        form.addRow(self.var)
        form.addRow(_("Mod:"), self.mod)
        form.addRow(_("Ağ türü:"), self.ag_turu)
        form.addRow(_("Ağ boyutu:"), self._ag_satiri())
        form.addRow(_("Parçacık:"), self.parcacik)
        form.addRow(_("Enerji sınırları [eV]:"), self.enerji)
        form.addRow(_("En çok gerçekleşme:"), self.max_gerceklesme)
        form.addRow(_("Güncelleme aralığı:"), self.aralik)
        form.addRow(_("Pencere dosyası:"), self._dosya_satiri())
        form.addRow(self.not_)
        self._sinyalleri_bagla()

    def _alanlari_kur(self):
        self.var = QtWidgets.QCheckBox(_("Varyans azaltma (ağırlık pencereleri, MAGIC)"))
        self.var.setToolTip(_(
            "Derin nüfuz problemlerinde (zırh) az sayıda parçacığın ulaştığı bölgelere "
            "ağırlık pencereleriyle yönlendirir: parçacıklar bölünür ya da öldürülür, sonuç "
            "yanlılıksız kalır. Yalnız 3B modelde."))
        self.mod = QtWidgets.QComboBox()
        for anahtar in varyans.MODLAR:
            self.mod.addItem(_(_MOD_ADLARI[anahtar]), anahtar)
        self.ag_turu = QtWidgets.QComboBox()
        for anahtar in varyans.MESH_TURLERI:
            self.ag_turu.addItem(_(_AG_ADLARI[anahtar]), anahtar)
        self.ag_turu.setToolTip(_(
            "Küresel düzenekte küresel ağ (yalnız yarıçap bölmesi) pencereyi yönden bağımsız, "
            "az gürültülü yapar; düzenli ağ her modelde çalışır."))
        self.nx, self.ny, self.nz = (tamsayi(n, 1, 2000, 1) for n in varyans.VARSAYILAN_BOYUT)
        self.parcacik = QtWidgets.QComboBox()
        for anahtar in varyans.PARCACIKLAR:
            self.parcacik.addItem(anahtar, anahtar)
        self.enerji = QtWidgets.QLineEdit()
        self.enerji.setPlaceholderText(_("boş: tek enerji grubu"))
        self.enerji.setToolTip(_("Virgülle ayrılmış artan sınırlar, ör. 0, 1e6, 2e7."))
        self.max_gerceklesme = tamsayi(varyans.VARSAYILAN_MAX_GERCEKLESME, 1, 100000, 1)
        self.max_gerceklesme.setToolTip(_(
            "Pencerelerin güncellendiği en çok çevrim (tally gerçekleşmesi) sayısı; "
            "üretim koşusunda çevrim sayısına eşitlemek en az gürültülü pencereyi verir."))
        self.aralik = tamsayi(varyans.VARSAYILAN_ARALIK, 1, 100000, 1)
        self.dosya = QtWidgets.QLineEdit()
        self.dosya.setPlaceholderText(_("yalnız 'uygula' modunda"))
        self.gozat = QtWidgets.QPushButton(_("Gözat…"))
        self.son_kosu = QtWidgets.QPushButton(_("Son koşudan al"))
        self.son_kosu.setToolTip(_("Koşu dizinindeki weight_windows.h5 dosyasını seçer."))
        self.not_ = ipucu(_(
            "Önerilen düzen: önce 'üret' ile analog bir koşu yapın (weight_windows.h5 koşu "
            "dizinine yazılır), sonra 'uygula' ile bu dosyayla koşun. Sonuç kartında "
            "verimlilik ölçütü FOM = 1 / (σ_bağıl² · T) yazılır; FOM yalnız aynı sonucu aynı "
            "belirsizlikle karşılaştırmak içindir. OpenMC 0.16 wwinp dışa aktarmaz; FW-CADIS "
            "random ray adjoint çözümü istediğinden bu sürümde yoktur."))

    def _ag_satiri(self):
        w = QtWidgets.QWidget()
        d = QtWidgets.QHBoxLayout(w)
        d.setContentsMargins(0, 0, 0, 0)
        for k in (self.nx, self.ny, self.nz):
            d.addWidget(k)
        d.addStretch(1)
        return w

    def _dosya_satiri(self):
        w = QtWidgets.QWidget()
        d = QtWidgets.QHBoxLayout(w)
        d.setContentsMargins(0, 0, 0, 0)
        d.addWidget(self.dosya, 1)
        d.addWidget(self.gozat)
        d.addWidget(self.son_kosu)
        return w

    def _sinyalleri_bagla(self):
        self.var.toggled.connect(self._kaydet)
        for c in (self.mod, self.ag_turu, self.parcacik):
            c.currentIndexChanged.connect(self._kaydet)
        for s in (self.nx, self.ny, self.nz, self.max_gerceklesme, self.aralik):
            s.valueChanged.connect(self._kaydet)
        self.enerji.editingFinished.connect(self._kaydet)
        self.dosya.editingFinished.connect(self._kaydet)
        self.gozat.clicked.connect(self._gozat)
        self.son_kosu.clicked.connect(self._son_kosudan)

    # ------------------------------------------------------------------
    def doldur(self, spec):
        """Spec'ten doldurur (sinyalsiz, spec'e yazmaz)."""
        self._spec = spec
        ham = ((spec.get("ayarlar") or {}).get("varyans"))
        ham = ham if isinstance(ham, dict) else {}
        self._yukleniyor = True
        try:
            self.var.setChecked(bool(ham.get("var")))
            self.mod.setCurrentIndex(max(self.mod.findData(ham.get("mod") or "uret"), 0))
            tur = ham.get("mesh_turu") or "duzenli"
            self.ag_turu.setCurrentIndex(max(self.ag_turu.findData(tur), 0))
            boyut = ham.get("mesh_boyut") or (varyans.VARSAYILAN_KURESEL if tur == "kuresel"
                                              else varyans.VARSAYILAN_BOYUT)
            for k, v in zip((self.nx, self.ny, self.nz), boyut):
                k.setValue(self._tam(v, 1))
            self.parcacik.setCurrentIndex(max(self.parcacik.findData(
                ham.get("parcacik") or "neutron"), 0))
            self.enerji.setText(_enerji_metni(ham.get("enerji_siniri")))
            self.max_gerceklesme.setValue(self._tam(
                ham.get("max_gerceklesme"), varyans.VARSAYILAN_MAX_GERCEKLESME))
            self.aralik.setValue(self._tam(ham.get("guncelleme_araligi"),
                                           varyans.VARSAYILAN_ARALIK))
            self.dosya.setText(ham.get("dosya") or "")
        finally:
            self._yukleniyor = False
        self._etkinlik()

    @staticmethod
    def _tam(deger, varsayilan):
        try:
            return int(deger)
        except (TypeError, ValueError):
            _log.warning("Y9 varyans ayarı sayı değil: %r", deger)
            return int(varsayilan)

    def _etkinlik(self):
        acik = self.var.isChecked()
        uygula = self.mod.currentData() == "uygula"
        for w in (self.mod, self.ag_turu, self.parcacik, self.enerji, self.max_gerceklesme,
                  self.aralik, self.nx, self.ny, self.nz):
            w.setEnabled(acik and not uygula)
        self.mod.setEnabled(acik)
        for w in (self.dosya, self.gozat, self.son_kosu):
            w.setEnabled(acik and uygula)
        kuresel = self.ag_turu.currentData() == "kuresel"
        self.ny.setEnabled(acik and not uygula)
        self.nz.setEnabled(acik and not uygula)
        self.nx.setToolTip(_("Küresel ağda yarıçap bölmesi sayısı.") if kuresel else "")

    def _enerji_oku(self):
        """Metni sayi listesine; bozuksa None (ve alan degismez; dogrulama hata gosterir)."""
        metin = self.enerji.text().replace(";", ",").strip()
        if not metin:
            return []
        try:
            return [float(p) for p in metin.split(",") if p.strip()]
        except ValueError:
            _log.info("enerji sınırları okunamadı: %r", metin)
            return None

    def _kaydet(self, *_a):
        self._etkinlik()
        if self._yukleniyor or self._spec is None:
            return
        a = self._spec["ayarlar"]
        onceki = a.get("varyans") if isinstance(a.get("varyans"), dict) else {}
        if not self.var.isChecked() and "varyans" not in a:
            return
        yeni = dict(onceki, var=self.var.isChecked(), mod=self.mod.currentData(),
                    yontem="magic", parcacik=self.parcacik.currentData(),
                    mesh_turu=self.ag_turu.currentData(),
                    mesh_boyut=[self.nx.value(), self.ny.value(), self.nz.value()],
                    max_gerceklesme=self.max_gerceklesme.value(),
                    guncelleme_araligi=self.aralik.value())
        enerji = self._enerji_oku()
        if enerji is not None:
            yeni["enerji_siniri"] = enerji
        yeni["dosya"] = self.dosya.text().strip() or None
        a["varyans"] = yeni
        self.degisti.emit()

    def _gozat(self):
        yol, _s = QtWidgets.QFileDialog.getOpenFileName(
            self, _("Ağırlık penceresi dosyası"), self.dosya.text() or "", _(_DOSYA_SUZGECI))
        if yol:
            self.dosya.setText(yol)
            self._kaydet()

    def _son_kosudan(self):
        dizin = ((self._spec or {}).get("calistirma") or {}).get("dizin")
        yol = varyans.kosu_dosyasi(dizin) if dizin else None
        if yol and os.path.isfile(yol):
            self.dosya.setText(os.path.abspath(yol))
            self._kaydet()
        else:
            self.dosya.setText("")
            self.not_.setText(_("Koşu dizininde weight_windows.h5 yok: önce 'üret' modunda koşun."))
