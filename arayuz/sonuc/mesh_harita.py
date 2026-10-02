# -*- coding: utf-8 -*-
"""
================================================================================
 mesh_harita.py  --  Ag (mesh) tally haritasi: 2B dilim, sigma, VTK (v3 Y1)
================================================================================
 Calistir sayfasinda kosu sonucundan sonra gorunur (mesh tally yoksa gizli).
 Hesap cekirdek/mesh_tally'dedir (Qt'siz, test edilir); burasi yalniz secim,
 cizim ve dosya diyalogudur.

   Tally / Skor / Grup        hangi dizi (grup: tek grup ya da toplam)
   Dilim ekseni + kaydirici   sabit tutulan eksen ve dilim no
   Normalizasyon              kaynak basina, hacim basina, ortalamaya bagil,
                              mutlak (ozdegerde; toplam guc [W] gerekir)
   Gosterim                   deger, standart sapma (σ), bagil hata
   Guvenilmez hucreleri isaretle   bagil hata > esik ya da skor yok (×)
   VTK disa aktar…            ParaView icin legacy .vtk (butun skor ve gruplar)
================================================================================
"""

import math
import os
import re

import numpy as np

from PySide6 import QtCore, QtWidgets
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
from matplotlib.figure import Figure

from cekirdek import mesh_tally as mt
from cekirdek.ceviri import _, N_
from cekirdek.gunluk import kaydedici
from arayuz.analiz.tuval import Tuval
from arayuz.ortak import GelismisBolum, baslik, ipucu, sayi
from arayuz.sonuc import mesh_cizim
from arayuz.tasarim import tokenlar

_log = kaydedici(__name__)
A = tokenlar.ARALIK

GOSTERIMLER = (("deger", N_("Değer")), ("sigma", N_("Standart sapma (σ)")),
               ("bagil", N_("Bağıl hata (σ / değer)")))
_YUZDE = 100.0
_TUVAL_YUKSEKLIGI = 380


class MeshHaritaWidget(QtWidgets.QWidget):
    """Mesh tally sonuclarinin 2B haritasi ve VTK disa aktarimi."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sonuclar = []
        self.gosterilen = None          # Dilim (son cizilen)
        self.isaretli = None            # 2B bool (son cizilen)
        self.birim_metni = ""
        self._doluyor = False
        self._denetimleri_kur()
        self._yerlesim_kur()
        self.setVisible(False)

    # ------------------------------------------------------------------
    # kurulum
    # ------------------------------------------------------------------
    def _denetimleri_kur(self):
        self.tally, self.skor, self.grup = (QtWidgets.QComboBox() for _i in range(3))
        self.eksen = QtWidgets.QComboBox()
        self.dilim = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.dilim.setRange(1, 1)
        self.dilim_etiket = QtWidgets.QLabel("")
        self.normalizasyon = QtWidgets.QComboBox()
        for k in mt.NORMALIZASYONLAR:
            self.normalizasyon.addItem(_(mt.NORMALIZASYON_ADLARI[k]), k)
        self.normalizasyon.setCurrentIndex(self.normalizasyon.findData("hacim"))
        self.gosterim = QtWidgets.QComboBox()
        for k, ad in GOSTERIMLER:
            self.gosterim.addItem(_(ad), k)
        self.guc = sayi(0.0, 1, 0.0, 1e12, 1e5, "W")
        self.guc.setSpecialValueText(_("(boş)"))
        self.guc_etiket = QtWidgets.QLabel(_("Toplam güç:"))
        self.esik = sayi(mt.BAGIL_HATA_ESIGI * _YUZDE, 1, 0.1, 100.0, 1.0, "%")
        self.esik.setToolTip(_("Bağıl hata eşiği. Varsayılan %10 — ") + mt.BAGIL_HATA_KAYNAGI)
        self.isaretle = QtWidgets.QCheckBox(_("Güvenilmez hücreleri işaretle"))
        self.isaretle.setChecked(True)
        self.d_vtk = QtWidgets.QPushButton(_("VTK dışa aktar…"))
        self.d_vtk.setToolTip(_("ParaView ile açılır: bütün skorlar ve gruplar; değer, "
                                "σ ve bağıl hata alanları."))
        self.ozet = ipucu("")
        self.uyari = ipucu("")
        self.atlanan = ipucu("")        # kalici: haritada gosterilmeyen tally'ler
        self.genel_isi = {}
        self.eksenel = False
        self.figur = Figure(figsize=(6, 4), tight_layout=True)
        self.tuval = Tuval(self.figur)
        self.tuval.setMinimumHeight(_TUVAL_YUKSEKLIGI)
        self.arac = NavigationToolbar2QT(self.tuval, self)
        self.tally.currentIndexChanged.connect(self._tally_secildi)
        self.eksen.currentIndexChanged.connect(self._eksen_secildi)
        for w in (self.skor, self.grup, self.normalizasyon, self.gosterim):
            w.currentIndexChanged.connect(self._ciz)
        self.dilim.valueChanged.connect(self._ciz)
        self.guc.valueChanged.connect(self._ciz)
        self.esik.valueChanged.connect(self._ciz)
        self.isaretle.toggled.connect(self._ciz)
        self.d_vtk.clicked.connect(self._vtk_diyalogu)

    @staticmethod
    def _satir(ogeler):
        w = QtWidgets.QWidget()
        d = QtWidgets.QHBoxLayout(w)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(A["s"])
        for oge in ogeler:
            if isinstance(oge, str):
                d.addWidget(QtWidgets.QLabel(oge))
            elif isinstance(oge, QtWidgets.QLabel):
                d.addWidget(oge)
            else:
                d.addWidget(oge, 1 if isinstance(oge, QtWidgets.QSlider) else 0)
        return w

    def _yerlesim_kur(self):
        duzen = QtWidgets.QVBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.addWidget(baslik(_("Ağ (mesh) haritası")))
        aciklama = ipucu(_("Ağ tally'lerinin dilim haritası. Renk ölçeği seçilen "
                           "normalizasyondadır; × işaretli hücrelerin bağıl hatası eşiği "
                           "aşar ya da hiç skor almamıştır. 3B görünüm için VTK dosyasını "
                           "ParaView'de açın."))
        duzen.addWidget(aciklama)
        duzen.addWidget(self._satir((_("Tally:"), self.tally, _("Skor:"), self.skor,
                                     _("Enerji grubu:"), self.grup)))
        duzen.addWidget(self._satir((_("Dilim ekseni:"), self.eksen, self.dilim_etiket,
                                     self.dilim)))
        duzen.addWidget(self._satir((_("Normalizasyon:"), self.normalizasyon,
                                     self.guc_etiket, self.guc, _("Gösterim:"),
                                     self.gosterim)))
        duzen.addWidget(self._satir((self.isaretle, _("Eşik:"), self.esik, self.d_vtk)))
        duzen.addWidget(self.ozet)
        duzen.addWidget(self.uyari)
        duzen.addWidget(self.atlanan)
        duzen.addWidget(self.tuval, 1)
        self.gelismis = GelismisBolum("mesh_harita_gelismis")
        self.gelismis.ekle(self.arac)
        duzen.addWidget(self.gelismis)

    # ------------------------------------------------------------------
    # disaridan
    # ------------------------------------------------------------------
    @staticmethod
    def _model_bilgisi(spec):
        """(toplam guc [W] | None, eksenel sonsuz mu, aktif yukseklik [cm] | None)."""
        if not spec:
            return None, False, None
        guc = (spec.get("guc_dagilimi") or {}).get("toplam_guc")
        try:
            from cekirdek import geometri
            aktif = geometri.hedef_yuksekligi(spec)
        except (ValueError, KeyError, TypeError):
            _log.info("aktif yükseklik okunamadı; çizgisel güç önerilmiyor", exc_info=True)
            aktif = None
        return guc, mt.eksenel_sonsuz(spec), aktif

    def statepoint_ayarla(self, statepoint_yolu, spec=None):
        """Kosu sonucundan mesh tally'lerini okur; yol None ise temizler. Okuma
        hatasi kosu sonucunun geri kalanini engellemez (gunluk + uyari)."""
        if not statepoint_yolu:
            self.sonuclari_ayarla([])
            return
        try:
            sonuclar, atlanan = mt.oku(statepoint_yolu)
            genel = mt.genel_isi_oku(statepoint_yolu)
            guc, eksenel, aktif = self._model_bilgisi(spec)
        except Exception as e:  # noqa: BLE001 -- kosu sonucu her durumda gorunsun
            _log.warning("mesh tally'leri okunamadı: %s", statepoint_yolu, exc_info=True)
            self.sonuclari_ayarla([])
            self.uyari.setText(_("Ağ tally'leri okunamadı: %s") % e)
            self.setVisible(True)
            return
        self.sonuclari_ayarla(sonuclar, guc, genel, eksenel, aktif)
        self.atlanan.setText(_("Haritada gösterilmeyen ağ tally'si: %s") % "; ".join(
            "%s (%s)" % a for a in atlanan) if atlanan else "")
        if atlanan and not sonuclar:
            self.setVisible(True)

    def sonuclari_ayarla(self, sonuclar, toplam_guc=None, genel_isi=None,
                         eksenel_sonsuz=False, aktif_yukseklik=None):
        """MeshSonuc listesi; bos liste karti gizler. 2B (eksenel_sonsuz) modelde
        guc kutusu cizgisel guc [W/cm] ister (toplam_guc / aktif_yukseklik)."""
        self.sonuclar = list(sonuclar or [])
        self.genel_isi = dict(genel_isi or {})
        self.eksenel = bool(eksenel_sonsuz)
        self._doluyor = True
        try:
            self._guc_kutusunu_ayarla(toplam_guc, aktif_yukseklik)
            self.tally.clear()
            for s in self.sonuclar:
                self.tally.addItem("%s (%s)" % (s.ad, _(mt.MESH_TUR_ADLARI[s.tur])), s.ad)
        finally:
            self._doluyor = False
        self.uyari.setText("")
        self.atlanan.setText("")
        self.setVisible(bool(self.sonuclar))
        if self.sonuclar:
            self.tally.setCurrentIndex(0)
            self._tally_secildi()

    def _guc_kutusunu_ayarla(self, toplam_guc, aktif_yukseklik):
        """3B: Toplam guc [W] (guc.py ile ayni tanim). 2B: cizgisel guc [W/cm] =
        toplam guc / aktif yukseklik; yukseklik bilinmiyorsa BOS (kullanici girer)."""
        if self.eksenel:
            self.guc_etiket.setText(_("Çizgisel güç:"))
            self.guc.setSuffix(" W/cm")
            self.guc.setToolTip(_("2B (eksenel sonsuz) modelde mutlak normalizasyon için "
                                  "çizgisel güç [W/cm] (ör. demet gücü / aktif yükseklik)."))
            deger = (float(toplam_guc) / float(aktif_yukseklik)
                     if toplam_guc and aktif_yukseklik else 0.0)
        else:
            self.guc_etiket.setText(_("Toplam güç:"))
            self.guc.setSuffix(" W")
            self.guc.setToolTip(_("Mutlak normalizasyon için modelin kapsadığı bölgenin "
                                  "toplam gücü (Hesap ayarları > Güç dağılımı > Toplam güç)."))
            deger = float(toplam_guc or 0.0)
        self.guc.setValue(deger)

    # ------------------------------------------------------------------
    # secim
    # ------------------------------------------------------------------
    def _secili(self):
        i = self.tally.currentIndex()
        return self.sonuclar[i] if 0 <= i < len(self.sonuclar) else None

    @staticmethod
    def _kutu_doldur(kutu, ogeler, secili=None):
        eski = kutu.blockSignals(True)
        try:
            onceki = kutu.currentData() if secili is None else secili
            kutu.clear()
            for veri, ad in ogeler:
                kutu.addItem(ad, veri)
            kutu.setCurrentIndex(max(kutu.findData(onceki), 0))
        finally:
            kutu.blockSignals(eski)

    def _tally_secildi(self, *_arg):
        s = self._secili()
        if s is None or self._doluyor:
            return
        self._kutu_doldur(self.skor, [(k, k) for k in s.skorlar])
        gruplar = [(None, _("Toplam (bütün gruplar)"))]
        if s.grup_sayisi > 1 and s.enerji:
            gruplar += [(g, _("Grup %d: %.4g – %.4g eV") % (g + 1, s.enerji[g], s.enerji[g + 1]))
                        for g in range(s.grup_sayisi)]
        self._kutu_doldur(self.grup, gruplar)
        adlar = mt.EKSEN_ADLARI[s.tur]
        self._kutu_doldur(self.eksen, [(e, _("%s sabit") % adlar[e]) for e in range(3)], 2)
        self._eksen_secildi()

    def _eksen_secildi(self, *_arg):
        s = self._secili()
        if s is None:
            return
        n = s.boyut[self.eksen.currentData()]
        eski = self.dilim.blockSignals(True)
        try:
            self.dilim.setRange(1, n)
            self.dilim.setValue(n // 2 + 1 if n > 1 else 1)
        finally:
            self.dilim.blockSignals(eski)
        self.dilim.setEnabled(n > 1)
        self._ciz()

    def _kaynak_hizi(self, s, skor):
        """Mutlak kip kaynak hizi; kosul yoksa ValueError (neden metniyle)."""
        if not s.ozdeger:
            raise ValueError(_("mutlak normalizasyon yalnız özdeğer hesabında"))
        isi, _h_skoru = mt.isi_payi(self.genel_isi, skor)
        return mt.kaynak_hizi(self.guc.value(), isi)

    def _normalize(self, s, skor, o, sg):
        """(ortalama, sapma, birim); mutlak kosulu yoksa hacime duser (uyari)."""
        yontem = self.normalizasyon.currentData()
        payda, olcu_turu = mt.olcu(s, self.eksenel)
        hiz = None
        if yontem == "mutlak":
            try:
                hiz = self._kaynak_hizi(s, skor)
                if olcu_turu == "dilim2b":
                    raise ValueError(_("2B modelde ağ z kolonunun yalnız bir dilimini "
                                       "kapsıyor"))
            except ValueError as e:
                self.uyari.setText(_("Mutlak normalizasyon yapılamadı (%s); hacim "
                                     "başına gösteriliyor.") % e)
                yontem = "hacim"
        return mt.normalize(o, sg, payda, yontem, hiz, skor, s.ozdeger, olcu_turu)

    def _veri(self):
        """(sonuc, ortalama 3B, sapma 3B, birim) -- secili duruma gore."""
        s = self._secili()
        skor = self.skor.currentData()
        o, sg = mt.secim(s, skor, self.grup.currentData())
        o, sg, birim = self._normalize(s, skor, o, sg)
        return s, o, sg, birim

    # ------------------------------------------------------------------
    # cizim
    # ------------------------------------------------------------------
    def _ciz(self, *_arg):
        if self._doluyor or self._secili() is None or self.skor.currentData() is None:
            return
        self.uyari.setText("")
        try:
            s, o, sg, birim = self._veri()
        except ValueError as e:          # or. bagil kipte skorlu hucre yok
            _log.info("ağ haritası çizilemedi: %s", e)
            self.uyari.setText(_("Harita çizilemedi: %s") % e)
            self.gosterilen, self.isaretli = None, None
            mesh_cizim.bos_ciz(self.figur, _("Gösterilecek değer yok"))
            self.tuval.draw_idle()
            return
        esik = self.esik.value() / _YUZDE
        gosterim = self.gosterim.currentData()
        # Skorsuz hucre (kilavuz boru, ag disi) bos birakilir: renk olcegini 0'a
        # cekmesin; × isaretiyle yine gorunur.
        skorsuz = o == 0
        dizi = {"deger": np.where(skorsuz, np.nan, o), "sigma": np.where(skorsuz, np.nan, sg),
                "bagil": mt.bagil_hata(o, sg)}[gosterim]
        eksen, indeks = self.eksen.currentData(), self.dilim.value() - 1
        self.gosterilen = mt.dilim(s, dizi, eksen, indeks)
        maske = mt.yuksek_hata_maskesi(o, sg, esik)
        self.isaretli = mt.dilim(s, maske, eksen, indeks).deger.astype(bool)
        self.birim_metni = _("bağıl hata (oran)") if gosterim == "bagil" else birim
        self._dilim_etiketi(s, eksen, indeks)
        self._ozet_yaz(o, sg, esik)
        mesh_cizim.ciz(self.figur, self.gosterilen,
                       self.isaretli if self.isaretle.isChecked() else None,
                       "%s · %s · %s" % (s.ad, self.skor.currentData(),
                                         self.grup.currentText()), self.birim_metni)
        self.tuval.draw_idle()

    def _dilim_etiketi(self, s, eksen, indeks):
        g = s.izgaralar[eksen]
        ad = mt.EKSEN_ADLARI[s.tur][eksen]
        aci = ad in ("φ", "θ")
        a, b = (float(g[indeks]), float(g[indeks + 1]))
        if aci:
            a, b = math.degrees(a), math.degrees(b)
        self.dilim_etiket.setText(_("Dilim %d/%d: %s = %.4g … %.4g %s") % (
            indeks + 1, s.boyut[eksen], ad, a, b, "°" if aci else "cm"))

    def _ozet_yaz(self, o, sg, esik):
        oz = mt.ozet(o, sg, esik)
        en_buyuk = oz["en_buyuk_bagil"]
        metin = _(
            "{h} hücre · skorsuz {s} · bağıl hata > %{e:.0f}: {y} · en büyük bağıl hata "
            "%{m:.1f}. ± değerleri OpenMC'nin raporladığı (iyimser) sapmalardır.").format(
            h=oz["hucre"], s=oz["skorsuz"], e=esik * _YUZDE, y=oz["yuksek"],
            m=0.0 if math.isnan(en_buyuk) else en_buyuk * _YUZDE)
        s = self._secili()
        if s is not None and s.grup_sayisi > 1 and self.grup.currentData() is None:
            metin += " " + _(mt.GRUP_TOPLAMI_NOTU)
        self.ozet.setText(metin)

    # ------------------------------------------------------------------
    # VTK
    # ------------------------------------------------------------------
    def vtk_disa_aktar(self, yol):
        """Secili tally'yi secili normalizasyonla yazar. DONER True/False (uyari yazilir)."""
        s = self._secili()
        if s is None:
            return False
        yontem = self.normalizasyon.currentData()
        try:
            hiz = self._kaynak_hizi(s, self.skor.currentData()) if yontem == "mutlak" else None
            adlar = mt.vtk_yaz(s, yol, yontem=yontem, kaynak_hizi=hiz,
                               eksenel_sonsuz=self.eksenel)
        except (OSError, ValueError) as e:
            _log.warning("VTK yazılamadı: %s", yol, exc_info=True)
            self.uyari.setText(_("VTK yazılamadı: %s") % e)
            return False
        self.uyari.setText(_("VTK yazıldı: %s (%d alan)") % (yol, len(adlar)))
        return True

    @staticmethod
    def onerilen_ad(ad):
        """Dosya adina uygun oneri: yol ayiricisi ve bosluk yok."""
        temiz = re.sub(r"[^\w.-]+", "_", str(ad)).strip("._") or "mesh"
        return temiz + ".vtk"

    def _uzerine_yaz_onayi(self, yol):
        """Var olan dosyanin uzerine yazilsin mi (testte degistirilir)."""
        cevap = QtWidgets.QMessageBox.question(
            self, _("VTK dışa aktar"), _("%s zaten var. Üzerine yazılsın mı?") % yol)
        return cevap == QtWidgets.QMessageBox.Yes

    def secilen_yolu_yaz(self, yol):
        """Uzanti yoksa .vtk ekler; ekleme sonrasi dosya varsa onay ister."""
        if not yol.lower().endswith(".vtk"):
            yol += ".vtk"
            if os.path.exists(yol) and not self._uzerine_yaz_onayi(yol):
                return False
        return self.vtk_disa_aktar(yol)

    def _vtk_diyalogu(self):
        s = self._secili()
        if s is None:
            return
        d = QtWidgets.QFileDialog(self, _("VTK dışa aktar"), os.getcwd(),
                                  _("VTK dosyası (*.vtk)"))
        d.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        d.setDefaultSuffix("vtk")              # uzanti eklenince de uzerine yazma sorulur
        d.selectFile(self.onerilen_ad(s.ad))
        if d.exec() and d.selectedFiles():
            self.secilen_yolu_yaz(d.selectedFiles()[0])
